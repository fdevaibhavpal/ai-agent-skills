#!/usr/bin/env python3
"""Collect from the keyless sources you choose, in one call, in parallel.

    python3 scripts/collect.py --sources se:fitness,hackernews --queries "beginner strength training" "squat form" --out raw/
    python3 scripts/collect.py --sources se:cooking --queries "sourdough starter" --since 2026-07-19 --suffix _period --out raw/
    python3 scripts/collect.py --sources stackoverflow,github --queries "memory leak" --tagged reactjs --repo react/react --out raw/

Sources: `se:<community>` (any Stack Exchange community: fitness, cooking, money, travel, diy,
gardening, pets, photo, ... find one with `stackexchange.py sites <word>`), `stackoverflow`,
`hackernews`, `github` (needs --repo). Choose the ones that fit the subject; there is no default.
Runs them at the same time, one worker per source. Each source still waits politely between its own requests (scripts/fetch.py), so a
whole run takes about as long as the slowest source, not the sum. Writes one JSON Lines file
per source into --out and prints a short summary. A source that fails is reported and skipped.
"""
from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch as fetchlib  # noqa: E402
import github  # noqa: E402
import hackernews  # noqa: E402
import stackexchange  # noqa: E402
from record import SourceError, write_jsonl  # noqa: E402

KNOWN_SOURCES = ("stackoverflow", "hackernews", "github")


def source_ok(source):
    return source in KNOWN_SOURCES or (source.startswith("se:") and len(source) > 3)


def output_name(source):
    return "stackexchange_" + source[3:] if source.startswith("se:") else source


def collect_source(source, queries, limit, tagged, repo, since, fetch, token):
    """Return (records, errors) for one source across all queries."""
    records, errors = [], []
    for query in queries:
        try:
            if source == "stackoverflow" or source.startswith("se:"):
                site = "stackoverflow" if source == "stackoverflow" else source[3:]
                found, _ = stackexchange.search(query, limit, tagged, "relevance", since, fetch, site=site)
            elif source == "hackernews":
                found = hackernews.search(query, limit, since=since, fetch=fetch)
            else:
                found = github.collect_api("issues", query, limit, since, [repo], fetch, token)
            records += found
        except SourceError as error:
            errors.append(f"{source} ({query!r}): {error}")
            if "rate limiting" in str(error) or "budget" in str(error):
                break                                    # the source said stop; do not keep asking
    return records, errors


def collect(queries, sources, limit=8, tagged=None, repo=None, since=None, fetch=fetchlib.get_json, token=None):
    """Return ({source: records}, [errors], [skipped notes])."""
    notes = []
    active = []
    for source in sources:
        if source == "github" and not repo:
            notes.append("github skipped: give --repo owner/name (a GitHub-wide search returns mostly unrelated projects)")
        else:
            active.append(source)
    if not active:
        return {}, [], notes
    with ThreadPoolExecutor(max_workers=len(active)) as pool:
        jobs = {s: pool.submit(collect_source, s, queries, limit, tagged, repo, since, fetch, token) for s in active}
        results = {s: job.result() for s, job in jobs.items()}
    return ({s: r for s, (r, _) in results.items()},
            [e for _, errs in results.values() for e in errs], notes)


def main(argv=None, fetch=fetchlib.get_json, environ=None, err=None):
    environ = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--queries", nargs="+", required=True, help="search phrases; include the subject word")
    parser.add_argument("--sources", required=True,
                        help="comma-separated: se:<community>, stackoverflow, hackernews, github. Choose for the subject")
    parser.add_argument("--limit", type=int, default=8, help="results per query per source")
    parser.add_argument("--tagged", help="tag that bounds the subject in the Stack Exchange sources (optional)")
    parser.add_argument("--repo", help="GitHub repository for issues, for example react/react")
    parser.add_argument("--since", metavar="YYYY-MM-DD", help="only items created on or after this date (the period pass)")
    parser.add_argument("--suffix", default="", help="file name suffix, for example _period")
    parser.add_argument("--out", default="raw", help="directory for the .jsonl files")
    args = parser.parse_args(argv)
    err = err or sys.stderr
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    bad = [s for s in sources if not source_ok(s)]
    if bad:
        print(f"collect: unknown source(s) {', '.join(bad)}; use se:<community>, stackoverflow, hackernews or github", file=err)
        return 2
    token = environ.get("GITHUB_TOKEN")
    if token:
        fetchlib.default.intervals["api.github.com"] = 2.1
    try:
        found, errors, notes = collect(args.queries, sources, args.limit, args.tagged, args.repo, args.since, fetch, token)
    except SourceError as error:
        print(f"collect: {error}", file=err)
        return 2
    os.makedirs(args.out, exist_ok=True)
    lines = []
    for source, records in found.items():
        path = os.path.join(args.out, f"{output_name(source)}{args.suffix}.jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            write_jsonl(records, handle)
        lines.append(f"  {source}: {len(records)} records -> {path}")
    print("collect: " + (f"{sum(len(r) for r in found.values())} records from {len(found)} sources" if found else "nothing collected"),
          file=err)
    for line in lines + [f"  {n}" for n in notes] + [f"  {e}" for e in errors]:
        print(line, file=err)
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
