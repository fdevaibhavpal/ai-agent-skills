#!/usr/bin/env python3
"""Count how much each topic was discussed in two equal time windows, as the sources report it.

    python3 scripts/volume.py topics.json --period 90d --tagged reactjs --baseline-query react > volume.json
    python3 scripts/volume.py topics.json --sources stackoverflow,hackernews,github --repo react/react

For every topic (its first `queries` entry, or its label) and every source, this asks the source
how many items match in the recent half and in the prior half of the period. Those are the
sources' own totals, not a count of what a search happened to return, so they make a sturdier
trend signal. A platform baseline is counted for the same windows, so a platform-wide slump is
not mistaken for a topic trend. No API keys are needed; requests are throttled by fetch.py.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch as fetchlib  # noqa: E402
from record import SourceError  # noqa: E402
from signals import ConfigError, load_topics  # noqa: E402

PERIODS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
SOURCES = ("stackoverflow", "hackernews", "github")   # plus se:<community> for any Stack Exchange community


def source_ok(source):
    return source in SOURCES or (source.startswith("se:") and len(source) > 3)
ISO = "%Y-%m-%dT%H:%M:%SZ"


def windows(now, period_days):
    """(recent, prior) as (start, end] pairs of datetimes."""
    half = timedelta(days=period_days / 2)
    return (now - half, now), (now - 2 * half, now - half)


def _epoch(moment):
    return int(moment.timestamp())


def count_stackoverflow(query, window, tagged, fetch, site="stackoverflow"):
    params = {"site": site, "filter": "total", "fromdate": _epoch(window[0]) + 1, "todate": _epoch(window[1])}
    if tagged:
        params["tagged"] = tagged
    if query:
        params["q"] = query
    data = fetch("https://api.stackexchange.com/2.3/search/advanced?" + urllib.parse.urlencode(params))
    if "total" not in data:
        raise SourceError(f"Stack Exchange API: {data.get('error_message') or 'no total in the response'}")
    return data["total"]


def count_hackernews(query, window, fetch):
    params = {"query": query, "tags": "story", "hitsPerPage": 0,
              "numericFilters": f"created_at_i>{_epoch(window[0])},created_at_i<={_epoch(window[1])}"}
    data = fetch("https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(params))
    if "nbHits" not in data:
        raise SourceError("Hacker News search: no nbHits in the response")
    return data["nbHits"]


def count_github(query, window, repo, fetch, headers):
    day = lambda moment: moment.strftime("%Y-%m-%d")  # noqa: E731
    first = window[0] + timedelta(days=1)             # GitHub dates are whole days: (start, end] becomes start+1..end
    terms = [query, "is:issue", f"repo:{repo}", f"created:{day(first)}..{day(window[1])}"]
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode({"q": " ".join(t for t in terms if t), "per_page": 1})
    data = fetch(url, headers)
    if "total_count" not in data:
        raise SourceError("GitHub search: no total_count in the response")
    return data["total_count"]


def collect(topics, period_days, now, sources, tagged=None, baseline_query=None, repo=None,
            fetch=fetchlib.get_json, token=None):
    recent, prior = windows(now, period_days)
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    errors, active = [], []

    def count(source, query, window):
        if source == "stackoverflow" or source.startswith("se:"):
            return count_stackoverflow(query, window, tagged, fetch, "stackoverflow" if source == "stackoverflow" else source[3:])
        if source == "hackernews":
            return count_hackernews(query, window, fetch)
        return count_github(query, window, repo, fetch, headers)

    baseline = {}
    for source in sources:
        if source == "github" and not repo:
            errors.append("github: needs --repo, skipped")
            continue
        if source == "hackernews" and not baseline_query:
            errors.append("hackernews: needs --baseline-query so volumes can be compared with the platform, skipped")
            continue
        try:
            baseline[source] = {"recent": count(source, baseline_query if source == "hackernews" else None, recent),
                                "prior": count(source, baseline_query if source == "hackernews" else None, prior)}
            active.append(source)
        except SourceError as error:
            errors.append(f"{source}: {error}")

    result = {}
    for topic in topics:
        query = (topic.get("queries") or [topic["label"]])[0]
        counts = {}
        for source in list(active):
            try:
                counts[source] = {"recent": count(source, query, recent), "prior": count(source, query, prior)}
            except SourceError as error:
                errors.append(f"{source} ({topic['topic']}): {error}")
                if "rate limiting" in str(error) or "budget" in str(error):
                    active.remove(source)   # do not keep asking a source that has said stop
        result[topic["topic"]] = {"query": query, "sources": counts}
    return {
        "meta": {"now": now.strftime(ISO), "period_days": period_days,
                 "recent_from": recent[0].strftime(ISO), "prior_from": prior[0].strftime(ISO),
                 "sources": active, "baseline": {s: baseline[s] for s in active}, "baseline_query": baseline_query,
                 "tagged": tagged, "repo": repo},
        "topics": result,
        "errors": errors,
    }


def main(argv=None, fetch=fetchlib.get_json, out=None, err=None, environ=None):
    environ = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("topics", help="topics.json")
    parser.add_argument("--period", default="90d", choices=sorted(PERIODS))
    parser.add_argument("--sources", default="stackoverflow,hackernews",
                        help="comma-separated: se:<community>, stackoverflow, hackernews, github (default: stackoverflow,hackernews)")
    parser.add_argument("--tagged", help="tag that bounds the subject on Stack Exchange sources (optional)")
    parser.add_argument("--baseline-query", help="a broad query for the subject (HN baseline), for example react")
    parser.add_argument("--repo", help="GitHub repository for issue volume, for example react/react")
    parser.add_argument("--now", metavar="ISO8601", help="end of the windows (default: now, UTC)")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    bad = [s for s in sources if not source_ok(s)]
    if bad:
        print(f"volume: unknown source(s) {', '.join(bad)}; use se:<community>, {', '.join(SOURCES)}", file=err)
        return 2
    try:
        load_topics(args.topics)                      # validates the vocabulary
        with open(args.topics, encoding="utf-8") as handle:
            topics = json.load(handle)["topics"]
        now = datetime.strptime(args.now, ISO).replace(tzinfo=timezone.utc) if args.now else datetime.now(timezone.utc)
        token = environ.get("GITHUB_TOKEN")
        if token:
            fetchlib.default.intervals["api.github.com"] = 2.1
        result = collect(topics, PERIODS[args.period], now, sources, args.tagged, args.baseline_query, args.repo,
                         fetch, token)
    except ConfigError as error:
        print(f"volume: {error}", file=err)
        return 2
    except ValueError:
        print(f"volume: --now must look like 2026-10-17T00:00:00Z", file=err)
        return 2
    json.dump(result, out, indent=2)
    out.write("\n")
    used = ", ".join(result["meta"]["sources"]) or "none"
    print(f"volume: {len(result['topics'])} topics from {used}", file=err)
    for message in result["errors"]:
        print(f"  {message}", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
