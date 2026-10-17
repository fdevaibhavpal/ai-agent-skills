#!/usr/bin/env python3
"""Collect YouTube videos as source records.

    python3 scripts/youtube.py search "react performance" --limit 25     # needs YOUTUBE_API_KEY
    python3 scripts/youtube.py search "" --channel @somechannel --order date
    python3 scripts/youtube.py feed UCsBjURrPoezykLs9EqgamOA             # no key needed

`search` uses the YouTube Data API v3 (a search call costs 100 quota units; videos.list and
channels.list cost 1; the default daily quota is 10,000).
`feed` reads a channel's public RSS feed: its 15 latest videos with titles, dates, views and
descriptions. It needs the channel id (UC...), which is on the channel's About page. This
script does not scrape channel pages to look ids up.
Prints JSON Lines to stdout.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import get_json, get_text  # noqa: E402
from record import SourceError, make_record, now_iso, write_jsonl  # noqa: E402

API = "https://www.googleapis.com/youtube/v3/"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id="
KEY_VAR = "YOUTUBE_API_KEY"
_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")
_CHANNEL_ID = re.compile(r"(UC[\w-]{22})")
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}


def api_get(endpoint, params, key, fetch=get_json):
    query = urllib.parse.urlencode({**params, "key": key})
    return fetch(f"{API}{endpoint}?{query}")


def parse_duration(value):
    match = _DURATION.match(value or "")
    if not match:
        return None
    days, hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def resolve_channel(channel, key, fetch=get_json):
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


def search(query, limit, key, channel=None, order="relevance", published_after=None, fetch=get_json):
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
        data = api_get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)}, key, fetch)
        by_id = {v["id"]: v for v in data.get("items", [])}
        records += [video_to_record(by_id[i], query, retrieved_at, competitor=channel)
                    for i in batch if i in by_id]
    return records


# ---------------------------------------------------------------- channel feed (no key)


def channel_id_from(text):
    """Accept a channel id or a youtube.com/channel/UC... URL. Handles need the API."""
    match = _CHANNEL_ID.search(text or "")
    if not match:
        raise SourceError(
            f"{text!r} is not a channel id. The feed needs the id (UC followed by 22 characters): on the "
            "channel's About page choose Share, then Copy channel ID. Resolving an @handle needs YOUTUBE_API_KEY "
            "(use `search --channel @handle`); this script does not scrape channel pages.")
    return match.group(1)


def feed_to_records(xml_text, channel_id, query, retrieved_at, limit=15):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        raise SourceError("the channel feed was not valid XML (is the channel id right?)")
    name = root.findtext("atom:author/atom:name", default=None, namespaces=NS)
    records = []
    for entry in root.findall("atom:entry", NS)[:limit]:
        video_id = entry.findtext("yt:videoId", namespaces=NS)
        if not video_id:
            continue
        stats = entry.find("media:group/media:community/media:statistics", NS)
        views = int(stats.get("views")) if stats is not None and stats.get("views", "").isdigit() else None
        records.append(make_record(
            id=f"youtube:{video_id}",
            source_type="youtube",
            url=f"https://www.youtube.com/watch?v={video_id}",
            title=entry.findtext("atom:title", default="", namespaces=NS),
            text=entry.findtext("media:group/media:description", default="", namespaces=NS),
            author=name,
            published_at=entry.findtext("atom:published", namespaces=NS),
            metrics={"views": views},
            query=query,
            access="fetched",
            tier=3,
            competitor=name,
            retrieved_at=retrieved_at,
            extra={"channel_id": channel_id},
        ))
    return records, name


def channel_feed(channel, limit=15, fetch_text=get_text):
    channel_id = channel_id_from(channel)
    xml_text = fetch_text(FEED + channel_id)
    records, name = feed_to_records(xml_text, channel_id, f"channel feed {channel_id}", now_iso(), limit)
    if not records:
        raise SourceError(f"the feed for {channel_id} has no videos")
    return records, name, channel_id


def main(argv=None, fetch=get_json, out=None, environ=None, fetch_text=get_text, err=None):
    environ = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    find = commands.add_parser("search", help="search videos (needs YOUTUBE_API_KEY)")
    find.add_argument("query")
    find.add_argument("--limit", type=int, default=25)
    find.add_argument("--channel", help="@handle or channel id (UC...); also tags records as that competitor")
    find.add_argument("--order", default="relevance", choices=["relevance", "date", "viewCount"])
    find.add_argument("--published-after", metavar="ISO8601")
    latest = commands.add_parser("feed", help="a channel's 15 latest videos (no key)")
    latest.add_argument("channel", help="channel id (UC...) or a youtube.com/channel/UC... URL")
    latest.add_argument("--limit", type=int, default=15)
    args = parser.parse_args(argv)
    err = err or sys.stderr

    try:
        if args.command == "feed":
            records, name, channel_id = channel_feed(args.channel, args.limit, fetch_text)
            print(f"youtube: feed for {channel_id} is channel {name!r}; check this is the creator you meant",
                  file=err)
        else:
            key = environ.get(KEY_VAR)
            if not key:
                print(f"youtube: {KEY_VAR} is not set. Set it in your environment (do not paste it into chat), "
                      "use `feed` with a channel id, or collect YouTube results through web search.", file=err)
                return 2
            records = search(args.query, args.limit, key, args.channel, args.order, args.published_after, fetch)
    except SourceError as error:
        print(f"youtube: {error}", file=err)
        return 2
    write_jsonl(records, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
