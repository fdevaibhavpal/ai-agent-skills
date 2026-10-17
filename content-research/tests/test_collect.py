import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import collect  # noqa: E402
from record import SourceError  # noqa: E402


def fixture(name, **overrides):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return {**json.load(f), **overrides}


class FakeApis:
    """Routes by host, like the real APIs, and remembers what was asked and from which thread."""

    def __init__(self, delay=0.0, fail_hosts=()):
        self.requests, self.threads, self.delay, self.fail_hosts = [], set(), delay, set(fail_hosts)

    def __call__(self, url, headers=None):
        host = url.split("/")[2]
        self.requests.append(url)
        self.threads.add(threading.get_ident())
        time.sleep(self.delay)
        if host in self.fail_hosts:
            raise SourceError(f"{host} is rate limiting or refusing requests (HTTP 429)")
        if "stackexchange" in host:
            return fixture("so_search.json", has_more=False)
        if "algolia" in host:
            return fixture("hn_search.json", nbPages=1)
        if "/repos/" in url:
            return {"full_name": "react/react"}
        return fixture("gh_rest_issues.json")


class CollectTests(unittest.TestCase):
    def test_collects_each_source_for_every_query(self):
        api = FakeApis()
        found, errors, notes = collect.collect(["q one", "q two"], ["stackoverflow", "hackernews", "github"],
                                               tagged="reactjs", repo="facebook/react", fetch=api)
        self.assertEqual(set(found), {"stackoverflow", "hackernews", "github"})
        self.assertEqual((len(found["stackoverflow"]), len(found["hackernews"]), len(found["github"])), (4, 6, 4))
        self.assertEqual((errors, notes), ([], []))

    def test_sources_run_in_parallel(self):
        api = FakeApis(delay=0.2)
        started = time.time()
        collect.collect(["a"], ["stackoverflow", "hackernews", "github"], repo="react/react", fetch=api)
        elapsed = time.time() - started
        # github makes two requests (repo lookup + search), the others one; run one after another this is 0.8s
        self.assertLess(elapsed, 0.7)
        self.assertGreaterEqual(len(api.threads), 3)

    def test_github_without_a_repo_is_skipped_with_a_reason(self):
        found, errors, notes = collect.collect(["q"], ["stackoverflow", "github"], fetch=FakeApis())
        self.assertEqual(set(found), {"stackoverflow"})
        self.assertIn("give --repo", notes[0])

    def test_one_failing_source_does_not_stop_the_others(self):
        api = FakeApis(fail_hosts={"hn.algolia.com"})
        found, errors, _ = collect.collect(["q1", "q2"], ["stackoverflow", "hackernews"], fetch=api)
        self.assertEqual(len(found["hackernews"]), 0)
        self.assertGreater(len(found["stackoverflow"]), 0)
        self.assertEqual(len(errors), 1)                       # one refusal, then it stopped asking
        self.assertIn("rate limiting", errors[0])
        self.assertEqual(sum("algolia" in u for u in api.requests), 1)

    def test_since_is_passed_to_every_source(self):
        api = FakeApis()
        collect.collect(["q"], ["stackoverflow", "hackernews", "github"], since="2026-07-19", repo="react/react", fetch=api)
        joined = " ".join(api.requests)
        self.assertIn("fromdate=", joined)
        self.assertIn("numericFilters=", joined)
        self.assertIn("created%3A%3E%3D2026-07-19", joined)


class CliTests(unittest.TestCase):
    def run_cli(self, argv, fetch):
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            code = collect.main([*argv, "--out", tmp], fetch=fetch, environ={}, err=err)
            files = sorted(os.listdir(tmp))
            first = []
            if files:
                with open(os.path.join(tmp, files[0])) as handle:
                    first = handle.read().splitlines()
        return code, files, first, err.getvalue()

    def test_writes_one_file_per_source_and_summarizes(self):
        code, files, first, err = self.run_cli(["--queries", "q", "--tagged", "reactjs", "--sources", "stackoverflow,hackernews"], FakeApis())
        self.assertEqual((code, files), (0, ["hackernews.jsonl", "stackoverflow.jsonl"]))
        self.assertTrue(all(json.loads(line)["source_type"] for line in first))
        self.assertIn("5 records from 2 sources", err)

    def test_suffix_for_a_second_pass(self):
        _, files, _, _ = self.run_cli(["--queries", "q", "--sources", "hackernews", "--suffix", "_period", "--since", "2026-07-19"], FakeApis())
        self.assertEqual(files, ["hackernews_period.jsonl"])

    def test_any_stack_exchange_community_and_its_file_name(self):
        api = FakeApis()
        code, files, first, err = self.run_cli(["--queries", "q", "--sources", "se:fitness,hackernews"], api)
        self.assertEqual((code, files), (0, ["hackernews.jsonl", "stackexchange_fitness.jsonl"]))
        self.assertTrue(any("site=fitness" in url for url in api.requests))

    def test_sources_must_be_chosen(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            collect.main(["--queries", "q"], fetch=FakeApis(), environ={}, err=io.StringIO())

    def test_bad_source_and_total_failure(self):
        code, _, _, err = self.run_cli(["--queries", "q", "--sources", "reddit"], FakeApis())
        self.assertEqual(code, 2)
        self.assertIn("unknown source", err)
        code, files, _, err = self.run_cli(["--queries", "q", "--sources", "hackernews"], FakeApis(fail_hosts={"hn.algolia.com"}))
        self.assertEqual(code, 0)                              # the source ran and failed: reported, file is empty
        self.assertIn("rate limiting", err)


if __name__ == "__main__":
    unittest.main()
