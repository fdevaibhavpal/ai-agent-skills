import io
import json
import os
import sys
import unittest
import urllib.parse

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import hackernews as hn  # noqa: E402
from record import SourceError  # noqa: E402
from schema_check import load_schema, validate  # noqa: E402


def fixture(**overrides):
    """The real response, trimmed to three hits and limited to one page."""
    with open(os.path.join(HERE, "fixtures", "hn_search.json"), encoding="utf-8") as f:
        return {**json.load(f), "nbPages": 1, **overrides}


class HackerNewsTests(unittest.TestCase):
    def test_records_from_a_real_response(self):
        recs = hn.search("react compiler", 10, fetch=lambda url: fixture())
        self.assertEqual(len(recs), 3)
        first = recs[0]
        self.assertRegex(first["id"], r"^hackernews:\d+$")
        self.assertEqual(first["url"], "https://news.ycombinator.com/item?id=" + first["id"].split(":")[1])
        self.assertEqual(first["tier"], 3)
        self.assertIsNone(first["author"])
        self.assertTrue(set(first["metrics"]) <= {"score", "comments"})
        for rec in recs:
            self.assertEqual(validate(rec, load_schema("source.json")), [])

    def test_comment_hits_and_missing_counts(self):
        hit = {"objectID": "1", "_tags": ["comment"], "comment_text": "<p>It&#x27;s <b>slow</b></p>",
               "story_title": "A story", "created_at": "2026-01-01T00:00:00Z"}
        rec = hn.hit_to_record(hit, "q", "2026-10-17T00:00:00Z")
        self.assertEqual((rec["title"], rec["text"]), ("A story", "It's slow"))
        self.assertEqual(rec["metrics"], {})                   # comments have no points: never recorded as 0
        self.assertEqual(rec["extra"]["kind"], "comment")

    def test_request_parameters(self):
        urls = []
        hn.search("react", 5, tags="ask_hn", since="2026-01-01", by_date=True,
                  fetch=lambda url: urls.append(url) or {"hits": [], "nbPages": 0})
        self.assertIn("/search_by_date?", urls[0])
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(urls[0]).query))
        self.assertEqual((params["tags"], params["hitsPerPage"]), ("ask_hn", "5"))
        self.assertEqual(params["numericFilters"], "created_at_i>1767225600")

    def test_unexpected_response(self):
        with self.assertRaisesRegex(SourceError, "Hacker News search: nope"):
            hn.search("q", 5, fetch=lambda url: {"message": "nope"})

    def test_cli(self):
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(hn.main(["search", "q", "--limit", "2"], fetch=lambda u: fixture(), out=out, err=err), 0)
        self.assertEqual(len(out.getvalue().splitlines()), 2)
        err = io.StringIO()
        self.assertEqual(hn.main(["search", "q", "--since", "soon"], fetch=lambda u: {}, err=err), 2)


if __name__ == "__main__":
    unittest.main()
