import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import github  # noqa: E402
from record import SourceError  # noqa: E402


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
        code = github.main(["issues", "q"], runner=lambda a: fixture("gh_issues.json"), out=out)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.getvalue().splitlines()), 2)

    def test_missing_gh_exits_with_message(self):
        def boom(args):
            raise SourceError("GitHub CLI `gh` is not installed.")
        self.assertEqual(github.main(["issues", "q"], runner=boom), 2)


if __name__ == "__main__":
    unittest.main()
