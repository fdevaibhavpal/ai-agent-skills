import gzip
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from email.message import Message

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fetch import Fetcher  # noqa: E402
from record import SourceError  # noqa: E402


class Clock:
    def __init__(self):
        self.t, self.sleeps = 1000.0, []

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.t += seconds


class Response:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code, headers=None, body=b""):
    message = Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return urllib.error.HTTPError("https://x.test/a?key=SECRET", code, "reason", message, io.BytesIO(body))


class ScriptedOpener:
    """Returns or raises the next scripted outcome for each request."""

    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), 0

    def __call__(self, request, timeout=None):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return Response(outcome)


class FetcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clock = Clock()

    def fetcher(self, *outcomes, **kw):
        opener = ScriptedOpener(*(outcomes or (b"ok",)))
        kw.setdefault("state_dir", os.path.join(self.tmp.name, "state"))
        return Fetcher(opener=opener, sleep=self.clock.sleep, now=self.clock.now, **kw), opener

    def test_throttle_spaces_requests_to_one_host_and_not_others(self):
        f, _ = self.fetcher(intervals={"a.test": 2.0})
        f.get_text("https://a.test/1")
        f.get_text("https://a.test/2")
        self.assertEqual(self.clock.sleeps, [2.0])
        f.get_text("https://b.test/1")          # different host: no wait
        self.assertEqual(self.clock.sleeps, [2.0])

    def test_throttle_is_remembered_by_a_new_fetcher(self):
        # each script run is a new process; the timestamp file carries the wait over
        first, _ = self.fetcher(intervals={"a.test": 5.0})
        first.get_text("https://a.test/1")
        second, _ = self.fetcher(intervals={"a.test": 5.0})
        second.get_text("https://a.test/2")
        self.assertEqual(self.clock.sleeps, [5.0])

    def test_defer_delays_the_next_request(self):
        f, _ = self.fetcher(intervals={"a.test": 1.0})
        f.defer("a.test", 30)
        f.get_text("https://a.test/1")
        self.assertEqual(self.clock.sleeps, [30.0])

    def test_retry_after_is_honored_then_succeeds(self):
        f, opener = self.fetcher(http_error(429, {"Retry-After": "2"}), b"fine")
        self.assertEqual(f.get_text("https://a.test/x"), "fine")
        self.assertEqual(opener.calls, 2)
        self.assertIn(2, self.clock.sleeps)

    def test_exponential_backoff_without_retry_after(self):
        f, opener = self.fetcher(http_error(503), http_error(503), b"fine")
        f.get_text("https://a.test/x")
        self.assertEqual(opener.calls, 3)
        self.assertEqual([s for s in self.clock.sleeps if s >= 2], [2, 4])

    def test_a_long_retry_after_means_stop(self):
        f, opener = self.fetcher(http_error(429, {"Retry-After": "3600"}))
        with self.assertRaises(SourceError) as ctx:
            f.get_text("https://a.test/x?key=SECRET")
        self.assertEqual(opener.calls, 1)
        message = str(ctx.exception)
        self.assertIn("rate limiting", message)
        self.assertIn("3600", message)
        self.assertIn("Not retrying", message)
        self.assertNotIn("SECRET", message)      # keys in URLs never reach messages

    def test_gives_up_after_the_retry_limit(self):
        f, opener = self.fetcher(http_error(429, {"Retry-After": "1"}))
        with self.assertRaises(SourceError):
            f.get_text("https://a.test/x")
        self.assertEqual(opener.calls, 4)         # first try plus three retries

    def test_github_style_403_rate_limit_is_retried_but_other_403_is_not(self):
        limited = http_error(403, {"X-RateLimit-Remaining": "0"}, b'{"message": "API rate limit exceeded"}')
        f, opener = self.fetcher(limited, b"fine")
        self.assertEqual(f.get_text("https://a.test/x"), "fine")
        forbidden = http_error(403, {}, b'{"message": "Forbidden"}')
        f2, opener2 = self.fetcher(forbidden)
        with self.assertRaisesRegex(SourceError, "refusing requests"):
            f2.get_text("https://a.test/y")
        self.assertEqual(opener2.calls, 1)        # a refusal is respected, not worked around

    def test_other_errors_are_not_retried_and_use_the_api_message(self):
        f, opener = self.fetcher(http_error(400, {}, b'{"error_message": "bad filter"}'))
        with self.assertRaisesRegex(SourceError, "HTTP 400: bad filter"):
            f.get_text("https://a.test/x")
        self.assertEqual(opener.calls, 1)

    def test_network_errors(self):
        f, _ = self.fetcher(urllib.error.URLError("no route"))
        with self.assertRaisesRegex(SourceError, "could not reach a.test: no route"):
            f.get_text("https://a.test/x")
        f, _ = self.fetcher(TimeoutError())
        with self.assertRaisesRegex(SourceError, "did not respond"):
            f.get_text("https://a.test/x")

    def test_request_budget(self):
        f, opener = self.fetcher(max_requests=2, intervals={"a.test": 0})
        f.get_text("https://a.test/1")
        f.get_text("https://a.test/2")
        with self.assertRaisesRegex(SourceError, "request budget of 2"):
            f.get_text("https://a.test/3")
        self.assertEqual(opener.calls, 2)

    def test_cache_serves_repeat_requests_until_it_expires(self):
        cache = os.path.join(self.tmp.name, "cache")
        f, opener = self.fetcher(b"one", cache_dir=cache, cache_ttl=100)
        self.assertEqual(f.get_text("https://a.test/x"), "one")
        self.assertEqual(f.get_text("https://a.test/x"), "one")
        self.assertEqual(opener.calls, 1)
        self.clock.t += 101
        f.get_text("https://a.test/x")
        self.assertEqual(opener.calls, 2)

    def test_failures_are_not_cached(self):
        cache = os.path.join(self.tmp.name, "cache")
        f, opener = self.fetcher(http_error(500), b"ok", cache_dir=cache)
        with self.assertRaises(SourceError):
            f.get_text("https://a.test/x")
        self.assertEqual(f.get_text("https://a.test/x"), "ok")

    def test_gzip_and_json(self):
        f, _ = self.fetcher(gzip.compress(json.dumps({"a": 1}).encode()))
        self.assertEqual(f.get_json("https://a.test/x"), {"a": 1})
        f, _ = self.fetcher(b"<html>")
        with self.assertRaisesRegex(SourceError, "did not return JSON"):
            f.get_json("https://a.test/x")

    def test_requests_identify_honestly(self):
        seen = []

        def opener(request, timeout=None):
            seen.append(request.get_header("User-agent"))
            return Response(b"ok")
        f = Fetcher(opener=opener, sleep=self.clock.sleep, now=self.clock.now, state_dir=os.path.join(self.tmp.name, "s"))
        f.get_text("https://a.test/x")
        self.assertIn("ai-agent-skills-content-research", seen[0])
        self.assertNotIn("Mozilla", seen[0])


if __name__ == "__main__":
    unittest.main()
