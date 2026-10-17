import io
import json
import os
import sys
import tempfile
import unittest
import urllib.parse
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import volume as vol  # noqa: E402
from record import SourceError  # noqa: E402

NOW = datetime(2026, 10, 17, tzinfo=timezone.utc)
TOPICS = [{"topic": "memory-leaks", "label": "Memory leaks", "queries": ["react memory leak"]},
          {"topic": "profiling", "label": "Profiling tools"}]


RECENT_START = int(datetime(2026, 9, 2, tzinfo=timezone.utc).timestamp())   # NOW minus 45 days


class FakeApi:
    """Answers count requests: a topic has 10 items in the recent window and 5 in the prior one; a baseline 100 and 80."""

    def __init__(self):
        self.requests = []

    def __call__(self, url, headers=None):
        parts = urllib.parse.urlsplit(url)
        params = dict(urllib.parse.parse_qsl(parts.query))
        self.requests.append((parts.netloc, parts.path, params))
        recent = self._starts_in_recent_window(params)
        if "stackexchange" in parts.netloc:
            topical = bool(params.get("q"))
            return {"total": (10 if recent else 5) if topical else (100 if recent else 80)}
        if "algolia" in parts.netloc:
            topical = params["query"] != "react"
            return {"nbHits": (10 if recent else 5) if topical else (100 if recent else 80)}
        topical = "memory" in params["q"] or "Profiling" in params["q"]
        return {"total_count": (10 if recent else 5) if topical else (100 if recent else 80)}

    @staticmethod
    def _starts_in_recent_window(params):
        if "fromdate" in params:                                   # Stack Overflow
            return int(params["fromdate"]) > RECENT_START
        if "numericFilters" in params:                             # Hacker News: created_at_i>START,created_at_i<=END
            return int(params["numericFilters"].split(">")[1].split(",")[0]) >= RECENT_START
        first_day = params["q"].split("created:")[1][:10]          # GitHub: created:FIRST..LAST
        return first_day >= "2026-09-03"


class VolumeTests(unittest.TestCase):
    def test_windows_are_equal_halves(self):
        recent, prior = vol.windows(NOW, 90)
        self.assertEqual((recent[1] - recent[0]).days, 45)
        self.assertEqual(recent[0], prior[1])
        self.assertEqual((prior[1] - prior[0]).days, 45)

    def test_collects_counts_and_baselines(self):
        api = FakeApi()
        result = vol.collect(TOPICS, 90, NOW, ["stackoverflow", "hackernews"], tagged="reactjs",
                             baseline_query="react", fetch=api)
        self.assertEqual(result["meta"]["baseline"], {"stackoverflow": {"recent": 100, "prior": 80},
                                                      "hackernews": {"recent": 100, "prior": 80}})
        self.assertEqual(result["topics"]["memory-leaks"]["query"], "react memory leak")
        self.assertEqual(result["topics"]["profiling"]["query"], "Profiling tools")     # falls back to the label
        self.assertEqual(result["topics"]["memory-leaks"]["sources"]["hackernews"], {"recent": 10, "prior": 5})
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["meta"]["recent_from"], "2026-09-02T00:00:00Z")

    def test_request_shapes(self):
        api = FakeApi()
        vol.collect(TOPICS[:1], 90, NOW, ["stackoverflow", "hackernews"], tagged="reactjs", baseline_query="react", fetch=api)
        so = [r for r in api.requests if "stackexchange" in r[0]]
        self.assertTrue(all(r[2]["filter"] == "total" and r[2]["tagged"] == "reactjs" for r in so))
        self.assertTrue(any("q" not in r[2] for r in so))                 # the baseline has no query
        hn = [r for r in api.requests if "algolia" in r[0]]
        self.assertTrue(all(r[2]["hitsPerPage"] == "0" and r[2]["tags"] == "story" for r in hn))
        self.assertIn("created_at_i>", hn[0][2]["numericFilters"])

    def test_github_needs_a_repo_and_uses_whole_day_ranges(self):
        api = FakeApi()
        result = vol.collect(TOPICS[:1], 90, NOW, ["github"], repo="react/react", fetch=api)
        query = api.requests[0][2]["q"]
        self.assertIn("repo:react/react", query)
        self.assertIn("is:issue", query)
        self.assertRegex(query, r"created:\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2}")
        self.assertEqual(result["meta"]["sources"], ["github"])
        skipped = vol.collect(TOPICS[:1], 90, NOW, ["github"], fetch=api)
        self.assertIn("needs --repo", skipped["errors"][0])
        self.assertEqual(skipped["meta"]["sources"], [])

    def test_hackernews_without_a_baseline_query_is_skipped_not_guessed(self):
        result = vol.collect(TOPICS[:1], 90, NOW, ["hackernews"], fetch=FakeApi())
        self.assertIn("needs --baseline-query", result["errors"][0])
        self.assertEqual(result["topics"]["memory-leaks"]["sources"], {})

    def test_a_failing_source_is_reported_and_others_continue(self):
        api = FakeApi()

        def flaky(url, headers=None):
            if "algolia" in url:
                raise SourceError("hn.algolia.com is rate limiting or refusing requests (HTTP 429)")
            return api(url, headers)
        result = vol.collect(TOPICS, 90, NOW, ["stackoverflow", "hackernews"], tagged="reactjs", baseline_query="react", fetch=flaky)
        self.assertEqual(result["meta"]["sources"], ["stackoverflow"])
        self.assertTrue(any("hackernews" in e and "rate limiting" in e for e in result["errors"]))
        self.assertIn("stackoverflow", result["topics"]["profiling"]["sources"])

    def test_a_source_that_says_stop_is_not_asked_again(self):
        calls = {"n": 0}
        api = FakeApi()

        def limited(url, headers=None):
            if "algolia" in url and "react" != dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)).get("query"):
                calls["n"] += 1
                raise SourceError("hn.algolia.com is rate limiting or refusing requests (HTTP 429)")
            return api(url, headers)
        vol.collect(TOPICS, 90, NOW, ["hackernews"], baseline_query="react", fetch=limited)
        self.assertEqual(calls["n"], 1)                                   # one refusal, then no more requests

    def test_any_stack_exchange_community_can_be_counted(self):
        api = FakeApi()
        result = vol.collect(TOPICS[:1], 90, NOW, ["se:fitness"], fetch=api)
        self.assertEqual(result["meta"]["sources"], ["se:fitness"])
        self.assertEqual(result["topics"]["memory-leaks"]["sources"]["se:fitness"], {"recent": 10, "prior": 5})
        self.assertTrue(all(r[2]["site"] == "fitness" for r in api.requests))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "topics.json")
            with open(path, "w") as f:
                json.dump({"topics": TOPICS}, f)
            out, err = io.StringIO(), io.StringIO()
            code = vol.main([path, "--tagged", "reactjs", "--baseline-query", "react", "--now", "2026-10-17T00:00:00Z"],
                            fetch=FakeApi(), out=out, err=err, environ={})
            self.assertEqual(code, 0)
            data = json.loads(out.getvalue())
            self.assertEqual(set(data["topics"]), {"memory-leaks", "profiling"})
            self.assertIn("2 topics from stackoverflow, hackernews", err.getvalue())
            err = io.StringIO()
            self.assertEqual(vol.main([path, "--sources", "reddit"], fetch=FakeApi(), out=io.StringIO(), err=err, environ={}), 2)
            self.assertIn("unknown source", err.getvalue())
            self.assertEqual(vol.main([path, "--now", "yesterday"], fetch=FakeApi(), out=io.StringIO(), err=io.StringIO(), environ={}), 2)
            self.assertEqual(vol.main(["/nonexistent.json"], fetch=FakeApi(), out=io.StringIO(), err=io.StringIO(), environ={}), 2)


if __name__ == "__main__":
    unittest.main()
