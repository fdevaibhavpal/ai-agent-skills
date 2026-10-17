import io
import json
import os
import sys
import unittest
import urllib.parse

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import stackexchange as se  # noqa: E402
from record import SourceError  # noqa: E402
from schema_check import load_schema, validate  # noqa: E402


def fixture(**overrides):
    """The real response, trimmed to two questions. has_more is forced off unless a test turns it on."""
    with open(os.path.join(HERE, "fixtures", "so_search.json"), encoding="utf-8") as f:
        return {**json.load(f), "has_more": False, **overrides}


class StackExchangeTests(unittest.TestCase):
    def test_records_from_a_real_response(self):
        recs, quota = se.search("useCallback", 10, fetch=lambda url: fixture(), defer=lambda *a: None)
        self.assertEqual(len(recs), 2)
        first = recs[0]
        self.assertRegex(first["id"], r"^stackoverflow:\d+$")
        self.assertTrue(first["url"].startswith("https://stackoverflow.com/questions/"))
        self.assertEqual(first["source_type"], "stackoverflow")
        self.assertEqual(set(first["metrics"]), {"score", "views", "answers"})
        self.assertIsNone(first["author"])
        self.assertNotIn("<", first["text"])                   # HTML is stripped
        self.assertRegex(first["published_at"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertIsInstance(first["extra"]["tags"], list)
        for rec in recs:
            self.assertEqual(validate(rec, load_schema("source.json")), [])

    def test_negative_scores_are_not_recorded_as_counts(self):
        item = dict(fixture()["items"][0], score=-3)
        rec = se.question_to_record(item, "q", "2026-10-17T00:00:00Z")
        self.assertNotIn("score", rec["metrics"])

    def test_request_parameters(self):
        urls = []
        se.search("react rerender", 5, tagged="reactjs", sort="creation", from_date="2025-01-01",
                  fetch=lambda url: urls.append(url) or {"items": []}, defer=lambda *a: None)
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(urls[0]).query))
        self.assertEqual((params["site"], params["tagged"], params["sort"], params["q"]),
                         ("stackoverflow", "reactjs", "creation", "react rerender"))
        self.assertEqual(params["fromdate"], "1735689600")
        self.assertEqual(params["pagesize"], "5")

    def test_paging_stops_at_the_limit(self):
        pages = []

        def fetch(url):
            pages.append(url)
            return fixture(has_more=True)
        recs, _ = se.search("q", 3, fetch=fetch, defer=lambda *a: None)
        self.assertEqual(len(recs), 3)
        self.assertEqual(len(pages), 2)

    def test_backoff_is_deferred_and_stops_paging(self):
        deferred = []
        data = fixture(has_more=True, backoff=10)
        recs, _ = se.search("q", 50, fetch=lambda url: data, defer=lambda host, s: deferred.append((host, s)))
        self.assertEqual(deferred, [("api.stackexchange.com", 10)])
        self.assertEqual(len(recs), 2)

    def test_an_empty_page_ends_paging_even_if_more_is_claimed(self):
        pages = []
        recs, _ = se.search("q", 50, fetch=lambda url: pages.append(url) or {"items": [], "has_more": True},
                            defer=lambda *a: None)
        self.assertEqual((recs, len(pages)), ([], 1))

    def test_api_errors_become_messages(self):
        with self.assertRaisesRegex(SourceError, "Stack Exchange API: too many requests"):
            se.search("q", 5, fetch=lambda url: {"error_message": "too many requests"}, defer=lambda *a: None)

    def test_other_communities_get_their_own_source_type_and_id(self):
        recs, _ = se.search("beginner strength training", 5, fetch=lambda url: fixture(), defer=lambda *a: None, site="fitness")
        first = recs[0]
        self.assertEqual(first["source_type"], "stackexchange")
        self.assertRegex(first["id"], r"^stackexchange:fitness:\d+$")
        self.assertEqual(first["extra"]["site"], "fitness")
        self.assertEqual(validate(first, load_schema("source.json")), [])

    def test_site_is_sent_and_a_bad_community_is_explained(self):
        urls = []
        se.search("q", 5, fetch=lambda url: urls.append(url) or {"items": []}, defer=lambda *a: None, site="cooking")
        self.assertIn("site=cooking", urls[0])
        with self.assertRaisesRegex(SourceError, "is 'nope' a community"):
            se.search("q", 5, fetch=lambda url: {"error_message": "No site found for name `nope`"}, defer=lambda *a: None, site="nope")

    def test_find_communities_by_name(self):
        data = {"items": [{"api_site_parameter": "cooking", "name": "Seasoned Advice", "audience": "professional and amateur chefs"},
                          {"api_site_parameter": "fitness", "name": "Physical Fitness", "audience": "athletes &amp; trainers"},
                          {"api_site_parameter": "travel", "name": "Travel", "audience": "frequent travelers"}]}
        self.assertEqual(se.find_sites("chef", lambda url: data), [("cooking", "Seasoned Advice", "professional and amateur chefs")])
        self.assertEqual([m[0] for m in se.find_sites("FIT", lambda url: data)], ["fitness"])        # case-insensitive
        self.assertEqual(se.find_sites("zzz", lambda url: data), [])
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(se.main(["sites", "travel"], fetch=lambda url: data, out=out, err=err), 0)
        self.assertIn("travel", out.getvalue())
        self.assertEqual(se.main(["sites", "zzz"], fetch=lambda url: data, out=io.StringIO(), err=err), 1)

    def test_cli(self):
        out, err = io.StringIO(), io.StringIO()
        data = fixture(quota_remaining=250)
        code = se.main(["search", "q"], fetch=lambda url: data, out=out, err=err, defer=lambda *a: None)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.getvalue().splitlines()), 2)
        self.assertIn("quota remaining today: 250", err.getvalue())
        err = io.StringIO()
        self.assertEqual(se.main(["search", "q", "--from-date", "yesterday"], fetch=lambda u: data, err=err,
                                 defer=lambda *a: None), 2)
        self.assertIn("YYYY-MM-DD", err.getvalue())


if __name__ == "__main__":
    unittest.main()
