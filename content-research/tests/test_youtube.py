import io
import json
import os
import sys
import unittest
import urllib.parse

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import youtube  # noqa: E402
from record import SourceError  # noqa: E402
from schema_check import load_schema, validate  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name)) as f:
        return json.load(f)


class FakeApi:
    """Stands in for the network: returns fixtures and remembers each request."""

    def __init__(self, channel_items=None):
        self.calls = []
        self.channel_items = channel_items

    def __call__(self, url):
        parsed = urllib.parse.urlparse(url)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        endpoint = parsed.path.rsplit("/", 1)[-1]
        self.calls.append((endpoint, params))
        if endpoint == "search":
            return fixture("yt_search.json")
        if endpoint == "videos":
            return fixture("yt_videos.json")
        if endpoint == "channels":
            return {"items": self.channel_items if self.channel_items is not None else [{"id": "UCresolved"}]}
        raise AssertionError(endpoint)


class YoutubeTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(youtube.parse_duration("PT1H2M3S"), 3723)
        self.assertEqual(youtube.parse_duration("PT45S"), 45)
        self.assertEqual(youtube.parse_duration("P1DT1M"), 86460)
        self.assertIsNone(youtube.parse_duration("garbage"))
        self.assertIsNone(youtube.parse_duration(None))

    def test_search_records(self):
        api = FakeApi()
        recs = youtube.search("react performance", 25, "KEY", fetch=api)
        self.assertEqual([r["id"] for r in recs], ["youtube:vid0000001", "youtube:vid0000002"])
        first, second = recs
        self.assertEqual(first["url"], "https://www.youtube.com/watch?v=vid0000001")
        self.assertEqual(first["metrics"], {"views": 120345, "likes": 4300, "comments": 212})
        self.assertEqual(first["extra"]["duration_seconds"], 3723)
        self.assertEqual(first["author"], "Some Channel")
        # hidden like/comment counts are left out, not set to 0
        self.assertEqual(second["metrics"], {"views": 900})

    def test_channel_search_resolves_handle_and_tags_competitor(self):
        api = FakeApi()
        recs = youtube.search("", 10, "KEY", channel="@somechannel", order="date", fetch=api)
        endpoints = [c[0] for c in api.calls]
        self.assertEqual(endpoints, ["channels", "search", "videos"])
        self.assertEqual(api.calls[0][1]["forHandle"], "@somechannel")
        self.assertEqual(api.calls[1][1]["channelId"], "UCresolved")
        self.assertNotIn("q", api.calls[1][1])
        self.assertEqual(recs[0]["competitor"], "@somechannel")

    def test_unknown_handle(self):
        with self.assertRaises(SourceError):
            youtube.search("", 5, "KEY", channel="@nobody", fetch=FakeApi(channel_items=[]))

    def test_needs_query_or_channel(self):
        with self.assertRaises(SourceError):
            youtube.search("", 5, "KEY", fetch=FakeApi())

    def test_missing_key_names_variable(self):
        err = io.StringIO()
        sys_err, sys.stderr = sys.stderr, err
        try:
            code = youtube.main(["search", "q"], fetch=FakeApi(), environ={})
        finally:
            sys.stderr = sys_err
        self.assertEqual(code, 2)
        self.assertIn("YOUTUBE_API_KEY", err.getvalue())

    def test_limit_is_respected(self):
        recs = youtube.search("q", 1, "KEY", fetch=FakeApi())
        self.assertEqual(len(recs), 1)

    def test_cli_prints_jsonl(self):
        out = io.StringIO()
        code = youtube.main(["search", "q"], fetch=FakeApi(), out=out, environ={"YOUTUBE_API_KEY": "KEY"})
        self.assertEqual(code, 0)
        self.assertEqual(len(out.getvalue().splitlines()), 2)


class FeedTests(unittest.TestCase):
    """Fixture is a trimmed real channel feed."""

    def feed_text(self):
        with open(os.path.join(HERE, "fixtures", "yt_feed.xml"), encoding="utf-8") as f:
            return f.read()

    def test_channel_id_forms(self):
        cid = "UCsBjURrPoezykLs9EqgamOA"
        self.assertEqual(youtube.channel_id_from(cid), cid)
        self.assertEqual(youtube.channel_id_from(f"https://www.youtube.com/channel/{cid}"), cid)

    def test_handles_are_refused_with_instructions_not_scraped(self):
        for value in ("@fireship", "https://www.youtube.com/@fireship", "fireship"):
            with self.assertRaisesRegex(SourceError, "Copy channel ID"):
                youtube.channel_id_from(value)

    def test_feed_records(self):
        recs, name = youtube.feed_to_records(self.feed_text(), "UCsBjURrPoezykLs9EqgamOA", "q", "2026-10-17T00:00:00Z")
        self.assertEqual(name, "Fireship")
        self.assertEqual(len(recs), 2)
        first = recs[0]
        self.assertRegex(first["id"], r"^youtube:[\w-]{11}$")
        self.assertEqual(first["url"], "https://www.youtube.com/watch?v=" + first["id"].split(":")[1])
        self.assertEqual((first["author"], first["competitor"], first["tier"]), ("Fireship", "Fireship", 3))
        self.assertIsInstance(first["metrics"]["views"], int)
        self.assertRegex(first["published_at"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertNotIn("likes", first["metrics"])        # the feed has no like counts: never invent them
        self.assertEqual(validate(first, load_schema("source.json")), [])

    def test_feed_cli_uses_the_right_url_and_names_the_channel(self):
        seen = []
        out, err = io.StringIO(), io.StringIO()
        code = youtube.main(["feed", "UCsBjURrPoezykLs9EqgamOA", "--limit", "1"],
                            fetch_text=lambda url: seen.append(url) or self.feed_text(), out=out, err=err, environ={})
        self.assertEqual(code, 0)
        self.assertEqual(seen, ["https://www.youtube.com/feeds/videos.xml?channel_id=UCsBjURrPoezykLs9EqgamOA"])
        self.assertEqual(len(out.getvalue().splitlines()), 1)
        self.assertIn("'Fireship'", err.getvalue())   # the user can confirm the channel is the one they meant

    def test_bad_feed(self):
        with self.assertRaisesRegex(SourceError, "not valid XML"):
            youtube.feed_to_records("<html>nope", "UCsBjURrPoezykLs9EqgamOA", "q", "2026-10-17T00:00:00Z")
        with self.assertRaisesRegex(SourceError, "no videos"):
            youtube.channel_feed("UCsBjURrPoezykLs9EqgamOA", fetch_text=lambda u: '<feed xmlns="http://www.w3.org/2005/Atom"></feed>')


if __name__ == "__main__":
    unittest.main()
