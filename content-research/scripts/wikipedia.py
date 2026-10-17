#!/usr/bin/env python3
"""Wikipedia article pageviews: a keyless interest signal for almost any topic.

    python3 scripts/wikipedia.py views "Strength training" "Espresso" --period 90d

Pageviews are the official, open Wikimedia statistics (human traffic, daily). For each article
this compares the recent half of the period with the prior half. It measures public curiosity
about a subject, not content demand, and only exists for topics that have an article. Wikipedia's
own search is poor for fuzzy phrases, so name the article yourself (the exact page title).
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import get_json  # noqa: E402
from record import SourceError  # noqa: E402

API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
PERIODS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}


def daily_views(title, start, end, project="en.wikipedia", fetch=get_json):
    """[(date, views)] for an article between two dates (inclusive)."""
    article = urllib.parse.quote(title.strip().replace(" ", "_"), safe="")
    url = f"{API}/{project}/all-access/user/{article}/daily/{start:%Y%m%d}00/{end:%Y%m%d}00"
    try:
        data = fetch(url)
    except SourceError as error:
        if "404" in str(error):
            raise SourceError(f"no Wikipedia article titled {title!r} with pageview data; use the exact page title")
        raise
    return [(datetime.strptime(item["timestamp"][:8], "%Y%m%d").date(), item["views"]) for item in data.get("items", [])]


def window_totals(title, now, period_days, project="en.wikipedia", fetch=get_json):
    """Views in the recent half and the prior half of the period, ending yesterday (today's data is incomplete)."""
    end = (now - timedelta(days=1)).date()
    half = period_days // 2
    start = end - timedelta(days=2 * half - 1)
    days = daily_views(title, datetime.combine(start, datetime.min.time()), datetime.combine(end, datetime.min.time()), project, fetch)
    boundary = end - timedelta(days=half)           # days after this date are the recent half
    recent = sum(v for d, v in days if d > boundary)
    prior = sum(v for d, v in days if d <= boundary)
    return {"recent": recent, "prior": prior, "days_with_data": len(days), "window_days": half}


def main(argv=None, fetch=get_json, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    views = commands.add_parser("views", help="compare the recent and prior half of a period")
    views.add_argument("titles", nargs="+", help="exact Wikipedia page titles")
    views.add_argument("--period", default="90d", choices=sorted(PERIODS))
    views.add_argument("--lang", default="en", help="Wikipedia language edition (default en)")
    views.add_argument("--now", metavar="ISO8601", help="end of the window (default: now, UTC)")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        now = datetime.strptime(args.now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if args.now else datetime.now(timezone.utc)
    except ValueError:
        print("wikipedia: --now must look like 2026-10-17T00:00:00Z", file=err)
        return 2
    status = 0
    for title in args.titles:
        try:
            totals = window_totals(title, now, PERIODS[args.period], f"{args.lang}.wikipedia", fetch)
        except SourceError as error:
            print(f"wikipedia: {error}", file=err)
            status = 1
            continue
        change = (f"{(totals['recent'] / totals['prior'] - 1):+.0%}" if totals["prior"] else "n/a")
        print(f"{title}: {totals['recent']} views in the recent {totals['window_days']} days vs "
              f"{totals['prior']} in the prior {totals['window_days']} ({change})", file=out)
    return status


if __name__ == "__main__":
    sys.exit(main())
