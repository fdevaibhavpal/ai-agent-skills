#!/usr/bin/env python3
"""Collect questions from any Stack Exchange community as source records. No API key needed.

    python3 scripts/stackexchange.py search "beginner strength training" --site fitness
    python3 scripts/stackexchange.py search "unnecessary re-renders" --site stackoverflow --tagged reactjs
    python3 scripts/stackexchange.py sites cooking          # find a community by name

Stack Exchange is not only programming: there are communities for cooking, fitness, personal
finance, travel, DIY, gardening, pets, parenting, photography, music and many more, all behind
the same public API (unauthenticated quota: 300 requests per day per IP). Questions show what
people are stuck on; view counts and scores measure sustained interest. Prints JSON Lines.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import date_to_epoch, defer, epoch_to_iso, get_json  # noqa: E402
from record import SourceError, make_record, now_iso, write_jsonl  # noqa: E402

API = "https://api.stackexchange.com/2.3/"
_TAGS = re.compile(r"<[^>]+>")


def strip_html(value):
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", value or ""))).strip()


def question_to_record(item, query, retrieved_at, site="stackoverflow"):
    def count(name):
        value = item.get(name)
        return value if isinstance(value, int) and value >= 0 else None  # a negative score is not a count

    if site == "stackoverflow":
        source_type, item_id = "stackoverflow", f"stackoverflow:{item['question_id']}"
    else:
        source_type, item_id = "stackexchange", f"stackexchange:{site}:{item['question_id']}"
    return make_record(
        id=item_id,
        source_type=source_type,
        url=item["link"],
        title=html.unescape(item.get("title", "")),
        text=strip_html(item.get("body")),
        author=None,  # individual askers are not needed for the analysis
        published_at=epoch_to_iso(item["creation_date"]) if "creation_date" in item else None,
        metrics={"score": count("score"), "views": count("view_count"), "answers": count("answer_count")},
        query=query,
        access="fetched",
        tier=3,
        retrieved_at=retrieved_at,
        extra={"site": site, "tags": item.get("tags", []), "answered": bool(item.get("is_answered")),
               "has_accepted_answer": "accepted_answer_id" in item},
    )


def search(query, limit, tagged=None, sort="relevance", from_date=None, fetch=get_json, defer=defer,
           site="stackoverflow"):
    params = {"order": "desc", "sort": sort, "q": query, "site": site, "filter": "withbody"}
    if tagged:
        params["tagged"] = tagged
    if from_date:
        params["fromdate"] = date_to_epoch(from_date)

    retrieved_at, records, page = now_iso(), [], 1
    while len(records) < limit:
        query_string = urllib.parse.urlencode({**params, "pagesize": min(100, limit - len(records)), "page": page})
        data = fetch(f"{API}search/advanced?{query_string}")
        if "error_message" in data:
            raise SourceError(f"Stack Exchange API: {data['error_message']} (is {site!r} a community? try `sites`)")
        records += [question_to_record(i, query, retrieved_at, site) for i in data.get("items", [])]
        if data.get("backoff"):  # the API asks us to pause; later runs honor it too
            defer("api.stackexchange.com", data["backoff"])
            break
        if not data.get("has_more") or not data.get("items"):
            break
        page += 1
    return records[:limit], data.get("quota_remaining")


def find_sites(text, fetch=get_json, limit=15):
    """Communities whose name or address contains `text`: [(site parameter, name, audience blurb)]."""
    data = fetch(f"{API}sites?pagesize=500")
    needle = text.lower()
    found = []
    for item in data.get("items", []):
        blob = f"{item.get('api_site_parameter', '')} {item.get('name', '')} {item.get('audience', '')}".lower()
        if needle in blob:
            found.append((item["api_site_parameter"], html.unescape(item["name"]), html.unescape(item.get("audience", ""))))
    return found[:limit]


def main(argv=None, fetch=get_json, out=None, err=None, defer=defer):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    find = commands.add_parser("search", help="search questions in one community")
    find.add_argument("query")
    find.add_argument("--site", default="stackoverflow", help="community, for example fitness, cooking, money, travel, diy")
    find.add_argument("--limit", type=int, default=25)
    find.add_argument("--tagged", help="tag filter; use ';' for several (all must match)")
    find.add_argument("--sort", default="relevance", choices=["relevance", "votes", "creation", "activity"])
    find.add_argument("--from-date", metavar="YYYY-MM-DD", help="only questions created on or after this date")
    listing = commands.add_parser("sites", help="find a community by name")
    listing.add_argument("text", help="part of a community's name, address or audience description")
    args = parser.parse_args(argv)
    err = err or sys.stderr
    try:
        if args.command == "sites":
            matches = find_sites(args.text, fetch)
            for site, name, audience in matches:
                print(f"{site:20} {name} - {audience[:70]}", file=out or sys.stdout)
            if not matches:
                print(f"stackexchange: no community matches {args.text!r}", file=err)
            return 0 if matches else 1
        records, quota = search(args.query, args.limit, args.tagged, args.sort, args.from_date, fetch, defer, args.site)
    except SourceError as error:
        print(f"stackexchange: {error}", file=err)
        return 2
    write_jsonl(records, out)
    note = f" (quota remaining today: {quota})" if quota is not None else ""
    print(f"stackexchange: {len(records)} questions from {args.site}{note}", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
