#!/usr/bin/env python3
"""Collect Hacker News stories and comments as source records. No API key needed.

    python3 scripts/hackernews.py search "react performance" --limit 25
    python3 scripts/hackernews.py search "react compiler" --since 2026-01-01 --sort date

Uses the public HN Search API (hn.algolia.com). Discussion volume and points show what a
technical audience argues about. Prints JSON Lines to stdout.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import date_to_epoch, get_json  # noqa: E402
from record import SourceError, make_record, now_iso, write_jsonl  # noqa: E402

API = "https://hn.algolia.com/api/v1/"
_TAGS = re.compile(r"<[^>]+>")


def strip_html(value):
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", value or ""))).strip()


def hit_to_record(hit, query, retrieved_at):
    object_id = hit["objectID"]
    kind = "comment" if "comment" in hit.get("_tags", []) else "story"
    return make_record(
        id=f"hackernews:{object_id}",
        source_type="hackernews",
        url=f"https://news.ycombinator.com/item?id={object_id}",
        title=hit.get("title") or hit.get("story_title") or "",
        text=strip_html(hit.get("story_text") or hit.get("comment_text")),
        author=None,  # individual commenters are not needed for the analysis
        published_at=hit.get("created_at"),
        metrics={"score": hit.get("points"), "comments": hit.get("num_comments")},
        query=query,
        access="fetched",
        tier=3,
        retrieved_at=retrieved_at,
        extra={"kind": kind, "external_url": hit.get("url") or hit.get("story_url")},
    )


def search(query, limit, tags="story", since=None, by_date=False, fetch=get_json):
    params = {"query": query, "tags": tags}
    if since:
        params["numericFilters"] = f"created_at_i>{date_to_epoch(since)}"
    endpoint = "search_by_date" if by_date else "search"

    retrieved_at, records, page = now_iso(), [], 0
    while len(records) < limit:
        query_string = urllib.parse.urlencode({**params, "hitsPerPage": min(100, limit - len(records)), "page": page})
        data = fetch(f"{API}{endpoint}?{query_string}")
        if "hits" not in data:
            raise SourceError(f"Hacker News search: {data.get('message') or 'unexpected response'}")
        records += [hit_to_record(h, query, retrieved_at) for h in data["hits"]]
        page += 1
        if not data["hits"] or page >= data.get("nbPages", 0):
            break
    return records[:limit]


def main(argv=None, fetch=get_json, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["search"])
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--tags", default="story", help="story, ask_hn, show_hn or comment (default story)")
    parser.add_argument("--since", metavar="YYYY-MM-DD", help="only items created after this date")
    parser.add_argument("--sort", choices=["relevance", "date"], default="relevance")
    args = parser.parse_args(argv)
    err = err or sys.stderr
    try:
        records = search(args.query, args.limit, args.tags, args.since, args.sort == "date", fetch)
    except SourceError as error:
        print(f"hackernews: {error}", file=err)
        return 2
    write_jsonl(records, out)
    print(f"hackernews: {len(records)} items", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
