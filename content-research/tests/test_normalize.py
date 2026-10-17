import io
import json
import os
import sys
import unittest
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import normalize  # noqa: E402
from schema_check import load_schema, validate  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "raw_mixed.jsonl")
RETRIEVED = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


def run_fixture():
    with open(FIXTURE) as f:
        accepted, rejected, read = normalize.normalize_lines(f, "raw_mixed.jsonl")
    return normalize.deduplicate(accepted), accepted, rejected, read


class CanonicalUrlTests(unittest.TestCase):
    def check(self, url, expected):
        self.assertEqual(normalize.canonical_url(url), expected)

    def test_tracking_fragment_www_and_param_order(self):
        self.check("http://www.Example.com/a/?utm_source=x&b=2&a=1#top", "https://example.com/a?a=1&b=2")

    def test_keeps_meaningful_params(self):
        self.check("https://example.com/search?q=react", "https://example.com/search?q=react")

    def test_youtube_forms_collapse(self):
        want = "https://youtube.com/watch?v=abc123"
        self.check("https://youtu.be/abc123?t=30", want)
        self.check("https://www.youtube.com/watch?v=abc123&feature=share&list=x", want)
        self.check("https://m.youtube.com/shorts/abc123", want)

    def test_reddit_subdomains(self):
        self.check("https://old.reddit.com/r/a/comments/1/t/", "https://reddit.com/r/a/comments/1/t")

    def test_github_is_case_insensitive(self):
        self.check("https://github.com/Acme/WebApp/issues/1/", "https://github.com/acme/webapp/issues/1")

    def test_stackoverflow_question_urls_collapse_to_the_id(self):
        want = "https://stackoverflow.com/questions/57156582"
        self.check("https://stackoverflow.com/questions/57156582/should-i-wrap-all-functions", want)
        self.check("https://stackoverflow.com/q/57156582/1234567", want)
        self.check("https://stackoverflow.com/questions/57156582", want)

    def test_other_stack_exchange_communities_collapse_the_same_way(self):
        self.check("https://fitness.stackexchange.com/questions/24595/whats-a-good-program?rq=1", "https://fitness.stackexchange.com/questions/24595")
        self.check("https://superuser.com/q/55/12345", "https://superuser.com/questions/55")

    def test_default_port_dropped_other_kept(self):
        self.check("https://example.com:443/a", "https://example.com/a")
        self.check("https://example.com:8080/a", "https://example.com:8080/a")

    def test_root_path(self):
        self.check("https://example.com", "https://example.com/")


class DateTests(unittest.TestCase):
    def parse(self, value):
        return normalize.parse_published(value, RETRIEVED)

    def test_iso_variants(self):
        self.assertEqual(self.parse("2026-09-01"), ("2026-09-01T00:00:00Z", "day", None))
        self.assertEqual(self.parse("2026-09-01T09:00:00Z"), ("2026-09-01T09:00:00Z", "exact", None))
        self.assertEqual(self.parse("2026-09-01T09:00:00.123Z")[0], "2026-09-01T09:00:00Z")
        self.assertEqual(self.parse("2026-09-01T08:30:00+02:00")[0], "2026-09-01T06:30:00Z")
        self.assertEqual(self.parse("2026-09-01 09:00")[0], "2026-09-01T09:00:00Z")

    def test_dates_as_printed_on_pages(self):
        self.assertEqual(self.parse("Oct 7, 2025"), ("2025-10-07T00:00:00Z", "day", None))
        self.assertEqual(self.parse("October 7, 2025")[0], "2025-10-07T00:00:00Z")
        self.assertEqual(self.parse("7 Oct 2025")[0], "2025-10-07T00:00:00Z")
        self.assertEqual(self.parse("2025/10/07")[0], "2025-10-07T00:00:00Z")
        self.assertEqual(self.parse("Smarch 7, 2025"), (None, None, "date_unparseable"))

    def test_rfc2822_and_epoch(self):
        self.assertEqual(self.parse("Tue, 01 Sep 2026 09:00:00 GMT")[0], "2026-09-01T09:00:00Z")
        self.assertEqual(self.parse("1788253200")[0], "2026-09-01T09:00:00Z")
        self.assertEqual(self.parse("1788253200000")[0], "2026-09-01T09:00:00Z")

    def test_relative_is_marked_approximate(self):
        self.assertEqual(self.parse("3 days ago"), ("2026-10-14T12:00:00Z", "approx", None))
        self.assertEqual(self.parse("2 weeks ago")[0], "2026-10-03T12:00:00Z")
        self.assertEqual(self.parse("an hour ago")[0], "2026-10-17T11:00:00Z")
        self.assertEqual(self.parse("yesterday")[0], "2026-10-16T12:00:00Z")

    def test_unknown_stays_null(self):
        self.assertEqual(self.parse(None), (None, None, None))
        self.assertEqual(self.parse(""), (None, None, None))
        self.assertEqual(self.parse("sometime last spring"), (None, None, "date_unparseable"))
        self.assertEqual(self.parse("2026-13-45"), (None, None, "date_unparseable"))

    def test_future_dates_are_dropped(self):
        self.assertEqual(self.parse("2027-01-01"), (None, None, "date_in_future"))
        self.assertIsNotNone(self.parse("2026-10-18T00:00:00Z")[0])  # within one day: clock skew


class MirrorTests(unittest.TestCase):
    def merged(self, *specs):
        schema = load_schema("source.json")
        records = []
        for n, (source, url, title) in enumerate(specs):
            raw = {"id": f"{source}:{n}", "source_type": source, "url": url, "title": title,
                   "retrieved_at": "2026-10-17T12:00:00Z", "query": "q", "access": "snippet", "tier": 1}
            record, errors = normalize.normalize_record(raw, schema)
            self.assertIsNone(errors)
            records.append(record)
        return normalize.deduplicate(records)

    def test_registrable_domain(self):
        self.assertEqual(normalize.registrable_domain("app.atatus.com"), "atatus.com")
        self.assertEqual(normalize.registrable_domain("www.bbc.co.uk"), "bbc.co.uk")
        self.assertEqual(normalize.registrable_domain("example.com"), "example.com")

    def test_same_title_across_one_sites_hostnames_is_one_page(self):
        title = "Improve React app performance"
        out = self.merged(("web", "https://app.atatus.com/guides/x", title),
                          ("web", "https://www.atatus.com/guides/x/", title),
                          ("web", "https://api.atatus.com/guides/x/", title))
        self.assertEqual((len(out), out[0]["merged_count"]), (1, 3))

    def test_same_title_on_different_sites_stays_separate(self):
        title = "React performance optimization guide"
        self.assertEqual(len(self.merged(("web", "https://a.com/x", title), ("web", "https://b.com/x", title))), 2)

    def test_short_titles_and_other_source_types_never_mirror(self):
        self.assertEqual(len(self.merged(("web", "https://www.a.com/1", "Blog"), ("web", "https://app.a.com/2", "Blog"))), 2)
        title = "How to prevent unnecessary renders in React"
        self.assertEqual(len(self.merged(("stackoverflow", "https://stackoverflow.com/questions/1/a", title),
                                         ("stackoverflow", "https://stackoverflow.com/questions/2/b", title))), 2)


class TextTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(normalize.clean_text("<b>Hello</b> &amp;\n  welcome​ "), "Hello & welcome")
        self.assertEqual(normalize.clean_text(None), "")

    def test_short_text_is_not_hashed(self):
        self.assertIsNone(normalize.content_hash("t", "short"))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.evidence, self.accepted, self.rejected, self.read = run_fixture()
        self.by_url = {r["canonical_url"]: r for r in self.evidence}

    def test_counts(self):
        self.assertEqual(self.read, 16)
        self.assertEqual(len(self.rejected), 3)
        self.assertEqual(len(self.accepted), 13)
        self.assertEqual(len(self.evidence), 8)

    def test_rejections_say_why(self):
        reasons = {where.split(":")[1]: " ".join(errs) for where, errs in self.rejected}
        self.assertIn("missing required field 'url'", reasons["12"])
        self.assertIn("prefix does not match", reasons["13"])
        self.assertIn("invalid JSON", reasons["14"])

    def test_url_and_syndicated_duplicates_merge_keeping_best_record(self):
        merged = self.by_url["https://example.com/react-perf?a=1&b=2"]
        self.assertEqual(merged["merged_count"], 3)
        self.assertEqual(merged["access"], "fetched")
        self.assertEqual(merged["url"], "https://example.com/react-perf?a=1&b=2")  # a real retrieved URL
        self.assertEqual(sorted(merged["queries"]), ["react performance", "react slow"])
        self.assertIn("https://blog.other.org/copy", merged["duplicate_urls"])
        self.assertEqual(merged["published_at"], "2026-09-01T06:30:00Z")

    def test_youtube_forms_merge_and_metrics_fill_without_overwrite(self):
        video = self.by_url["https://youtube.com/watch?v=vid0000001"]
        self.assertEqual(video["merged_count"], 2)
        self.assertEqual(video["metrics"], {"views": 100, "likes": 5})  # views from the dated record wins

    def test_reddit_merge_takes_date_from_other_record(self):
        thread = self.by_url["https://reddit.com/r/reactjs/comments/abc/thread"]
        self.assertEqual(thread["access"], "fetched")
        self.assertEqual(thread["published_at"], "2026-10-14T12:00:00Z")
        self.assertEqual(thread["date_precision"], "approx")
        self.assertEqual(thread["published_at_raw"], "3 days ago")
        self.assertEqual(thread["metrics"], {"score": 40, "comments": 12})

    def test_warnings(self):
        self.assertIn("date_unparseable", self.by_url["https://news.example.net/b"]["warnings"])
        future = self.by_url["https://example.com/future"]
        self.assertIn("date_in_future", future["warnings"])
        self.assertIsNone(future["published_at"])
        self.assertEqual(future["published_at_raw"], "2027-01-01")
        nodate = self.by_url["https://example.com/nodate"]
        self.assertIn("no_text", nodate["warnings"])
        self.assertEqual(nodate["title"], "Hello & welcome")
        self.assertFalse(nodate["quality"]["dated"])
        self.assertIsNone(nodate["quality"]["age_days"])

    def test_quality_age(self):
        news = self.by_url["https://news.example.net/a"]
        self.assertEqual(news["quality"]["age_days"], 46)

    def test_github_case_variants_merge(self):
        issue = self.by_url["https://github.com/acme/webapp/issues/1"]
        self.assertEqual(issue["merged_count"], 2)

    def test_evidence_ids_are_stable_and_unique(self):
        again, *_ = run_fixture()
        self.assertEqual([r["evidence_id"] for r in again], [r["evidence_id"] for r in self.evidence])
        self.assertEqual(len({r["evidence_id"] for r in self.evidence}), len(self.evidence))

    def test_output_matches_evidence_schema(self):
        schema = load_schema("evidence.json")
        for record in self.evidence:
            self.assertEqual(validate(record, schema), [], record["url"])

    def test_unobserved_metrics_are_never_added(self):
        self.assertEqual(self.by_url["https://news.example.net/a"]["metrics"], {})

    def test_first_seen_order(self):
        self.assertEqual(self.evidence[0]["canonical_url"], "https://example.com/react-perf?a=1&b=2")


class CliTests(unittest.TestCase):
    def run_cli(self, argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        code = normalize.main(argv, stdin=io.StringIO(stdin), out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_files_to_jsonl_and_summary(self):
        code, out, err = self.run_cli([FIXTURE])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 8)
        self.assertIn("16 read, 3 rejected, 5 duplicates merged -> 8 evidence records", err)
        self.assertIn("rejected raw_mixed.jsonl:12", err)

    def test_stdin(self):
        with open(FIXTURE) as f:
            code, out, _ = self.run_cli([], f.read())
        self.assertEqual((code, len(out.splitlines())), (0, 8))

    def test_strict_fails_on_rejects(self):
        self.assertEqual(self.run_cli([FIXTURE, "--strict"])[0], 1)

    def test_missing_file(self):
        code, out, err = self.run_cli(["nope.jsonl"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read nope.jsonl", err)

    def test_empty_input(self):
        code, out, err = self.run_cli([], "")
        self.assertEqual((code, out), (0, ""))
        self.assertIn("0 read", err)


if __name__ == "__main__":
    unittest.main()
