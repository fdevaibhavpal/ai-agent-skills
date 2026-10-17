#!/usr/bin/env python3
"""Collect YouTube videos as source records, using the YouTube Data API v3.

    python3 scripts/youtube.py search "react performance" --limit 25
    python3 scripts/youtube.py search "" --channel @somechannel --order date

Requires YOUTUBE_API_KEY in the environment. Prints JSON Lines to stdout.
A search call costs 100 quota units; videos.list and channels.list cost 1.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from record import SourceError, make_record, now_iso, write_jsonl  # noqa: E402

API = "https://www.googleapis.com/youtube/v3/"
KEY_VAR = "YOUTUBE_API_KEY"
_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def http_fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        # The URL contains the key, so report only the API's own message.
        try:
            message = json.load(err)["error"]["message"]
        except Exception:
            message = err.reason
        raise SourceError(f"YouTube API error {err.code}: {message}")
    except urllib.error.URLError as err:
        raise SourceError(f"could not reach the YouTube API: {err.reason}")


def api_get(endpoint, params, key, fetch=http_fetch):
    query = urllib.parse.urlencode({**params, "key": key})
    return fetch(f"{API}{endpoint}?{query}")


def parse_duration(value):
    match = _DURATION.match(value or "")
    if not match:
        return None
    days, hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def resolve_channel(channel, key, fetch=http_fetch):
    if channel.startswith("UC"):
        return channel
    handle = channel if channel.startswith("@") else f"@{channel}"
    data = api_get("channels", {"part": "id", "forHandle": handle}, key, fetch)
    items = data.get("items") or []
    if not items:
        raise SourceError(f"no YouTube channel found for {handle}")
    return items[0]["id"]


def video_to_record(video, query, retrieved_at, competitor=None):
    snippet = video.get("snippet", {})
    stats = video.get("statistics", {})

    def count(name):
        return int(stats[name]) if name in stats else None  # hidden counts are absent

    return make_record(
        id=f"youtube:{video['id']}",
        source_type="youtube",
        url=f"https://www.youtube.com/watch?v={video['id']}",
        title=snippet.get("title"),
        text=snippet.get("description"),
        author=snippet.get("channelTitle"),
        published_at=snippet.get("publishedAt"),
        metrics={"views": count("viewCount"), "likes": count("likeCount"),
                 "comments": count("commentCount")},
        query=query,
        access="fetched",
        tier=3,
        competitor=competitor,
        retrieved_at=retrieved_at,
        extra={"channel_id": snippet.get("channelId"),
               "duration_seconds": parse_duration(video.get("contentDetails", {}).get("duration"))},
    )


def search(query, limit, key, channel=None, order="relevance", published_after=None,
           fetch=http_fetch):
    if not query and not channel:
        raise SourceError("give a search query, or --channel to list a channel's videos")
    params = {"part": "id", "type": "video", "order": order}
    if query:
        params["q"] = query
    if channel:
        params["channelId"] = resolve_channel(channel, key, fetch)
    if published_after:
        params["publishedAfter"] = published_after

    ids, token = [], None
    while len(ids) < limit:
        page = dict(params, maxResults=min(50, limit - len(ids)))
        if token:
            page["pageToken"] = token
        data = api_get("search", page, key, fetch)
        ids += [i["id"]["videoId"] for i in data.get("items", []) if "videoId" in i.get("id", {})]
        token = data.get("nextPageToken")
        if not token:
            break
    ids = ids[:limit]

    retrieved_at, records = now_iso(), []
    for start in range(0, len(ids), 50):
        batch = ids[start:start + 50]
        data = api_get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)},
                       key, fetch)
        by_id = {v["id"]: v for v in data.get("items", [])}
        records += [video_to_record(by_id[i], query, retrieved_at, competitor=channel)
                    for i in batch if i in by_id]
    return records


def main(argv=None, fetch=http_fetch, out=None, environ=None):
    environ = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["search"])
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--channel", help="@handle or channel id (UC...); also tags records as that competitor")
    parser.add_argument("--order", default="relevance", choices=["relevance", "date", "viewCount"])
    parser.add_argument("--published-after", metavar="ISO8601")
    args = parser.parse_args(argv)

    key = environ.get(KEY_VAR)
    if not key:
        print(f"youtube: {KEY_VAR} is not set. Set it in your environment (do not paste it into chat), "
              "or collect YouTube results through web search.", file=sys.stderr)
        return 2
    try:
        records = search(args.query, args.limit, key, args.channel, args.order,
                         args.published_after, fetch)
    except SourceError as err:
        print(f"youtube: {err}", file=sys.stderr)
        return 2
    write_jsonl(records, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
