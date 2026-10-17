import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import github  # noqa: E402
from record import SourceError  # noqa: E402
from schema_check import load_schema, validate  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name)) as f:
        return json.load(f)


class GithubTests(unittest.TestCase):
    def test_issue_records(self):
        recs = github.collect("issues", "memory leak", 25, runner=lambda a: fixture("gh_issues.json"))
        first, second = recs
        self.assertEqual(first["id"], "github:acme/webapp#4821")
        self.assertEqual(first["metrics"], {"comments": 14})
        self.assertEqual(first["extra"]["labels"], ["performance", "bug"])
        self.assertIsNone(first["author"])
        self.assertEqual(first["tier"], 2)
        # no commentsCount in the source -> no comments metric, not 0
        self.assertEqual(second["metrics"], {})
        self.assertEqual(second["extra"]["state"], "closed")
        self.assertEqual(second["text"], "")

    def test_repo_records(self):
        recs = github.collect("repos", "profiler", 5, runner=lambda a: fixture("gh_repos.json"))
        self.assertEqual(recs[0]["metrics"], {"stars": 1520, "forks": 88})
        self.assertEqual(recs[0]["author"], "acme")

    def test_builds_gh_arguments(self):
        seen = []
        github.collect("issues", "q", 7, created_after="2026-07-01",
                       runner=lambda a: seen.append(a) or [])
        args = seen[0]
        self.assertEqual(args[:3], ["search", "issues", "q"])
        self.assertIn("2026-07-01", " ".join(args))
        self.assertEqual(args[args.index("--limit") + 1], "7")

    def test_cli_prints_jsonl(self):
        out = io.StringIO()
        code = github.main(["issues", "q", "--backend", "gh"], runner=lambda a: fixture("gh_issues.json"), out=out)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.getvalue().splitlines()), 2)

    def test_missing_gh_exits_with_message(self):
        def boom(args):
            raise SourceError("GitHub CLI `gh` is not installed.")
        self.assertEqual(github.main(["issues", "q", "--backend", "gh"], runner=boom), 2)


class RestTests(unittest.TestCase):
    """The public REST API path, used when `gh` is not installed. Fixture is a trimmed real response."""

    def make_fetch(self, repo_name="react/react"):
        calls = []

        def fetch(url, headers=None):
            calls.append((url, headers))
            if "/repos/" in url and "search" not in url:
                return {"full_name": repo_name}
            return fixture("gh_rest_issues.json")
        return fetch, calls

    def test_issue_records(self):
        fetch, _ = self.make_fetch()
        recs = github.collect_api("issues", "useMemo", 10, fetch=fetch)
        self.assertEqual(len(recs), 2)
        first = recs[0]
        self.assertTrue(first["id"].startswith("github:react/react#"))
        self.assertTrue(first["url"].startswith("https://github.com/react/react/issues/"))
        self.assertEqual(first["tier"], 3)
        self.assertIsNone(first["author"])
        self.assertIn("comments", first["metrics"])
        self.assertEqual(validate(first, load_schema("source.json")), [])

    def test_query_is_scoped_to_the_canonical_repo_name(self):
        # facebook/react was renamed to react/react; search only accepts the current name
        fetch, calls = self.make_fetch("react/react")
        github.collect_api("issues", "useMemo", 5, created_after="2026-01-01", repos=["facebook/react"], fetch=fetch)
        search_url = calls[-1][0]
        self.assertIn("repo%3Areact%2Freact", search_url)
        self.assertNotIn("facebook", search_url)
        self.assertIn("created%3A%3E%3D2026-01-01", search_url)
        self.assertIn("is%3Aissue", search_url)

    def test_unknown_repo(self):
        def fetch(url, headers=None):
            raise SourceError("api.github.com returned HTTP 404: Not Found")
        with self.assertRaisesRegex(SourceError, "could not be found"):
            github.collect_api("issues", "q", 5, repos=["nobody/nothing"], fetch=fetch)

    def test_token_is_sent_only_when_set(self):
        fetch, calls = self.make_fetch()
        github.collect_api("issues", "q", 5, fetch=fetch)
        self.assertNotIn("Authorization", calls[-1][1])
        github.collect_api("issues", "q", 5, fetch=fetch, token="TOKEN")
        self.assertEqual(calls[-1][1]["Authorization"], "Bearer TOKEN")

    def test_cli_api_backend_and_errors(self):
        fetch, _ = self.make_fetch()
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(github.main(["issues", "q", "--backend", "api"], fetch=fetch, out=out, err=err, environ={}), 0)
        self.assertEqual(len(out.getvalue().splitlines()), 2)
        self.assertIn("via api", err.getvalue())

        def limited(url, headers=None):
            raise SourceError("api.github.com is rate limiting or refusing requests (HTTP 403)")
        err = io.StringIO()
        self.assertEqual(github.main(["issues", "q", "--backend", "api"], fetch=limited, err=err, environ={}), 2)
        self.assertIn("rate limiting", err.getvalue())


if __name__ == "__main__":
    unittest.main()
