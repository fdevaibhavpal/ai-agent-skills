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


if __name__ == "__main__":
    unittest.main()
