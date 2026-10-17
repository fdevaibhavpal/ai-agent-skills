#!/usr/bin/env python3
"""Collect GitHub issues and repositories as source records, using the `gh` CLI.

    python3 scripts/github.py issues "react memory leak" --limit 25
    python3 scripts/github.py repos "react performance" --limit 15

Requires `gh` installed and authenticated. Prints JSON Lines to stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from record import SourceError, make_record, now_iso, write_jsonl  # noqa: E402

ISSUE_FIELDS = "number,title,body,createdAt,url,repository,commentsCount,state,labels"
REPO_FIELDS = "fullName,description,url,createdAt,updatedAt,stargazersCount,forksCount,language,owner"


def run_gh(args):
    if shutil.which("gh") is None:
        raise SourceError("GitHub CLI `gh` is not installed. Install it and run `gh auth login`, "
                          "or collect GitHub results through web search.")
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SourceError(proc.stderr.strip() or "gh exited with an error (is it authenticated?)")
    return json.loads(proc.stdout or "[]")


def issue_to_record(item, query, retrieved_at):
    repo = (item.get("repository") or {}).get("nameWithOwner", "")
    return make_record(
        id=f"github:{repo}#{item['number']}",
        source_type="github",
        url=item["url"],
        title=item.get("title"),
        text=item.get("body"),
        author=None,  # individual reporters are not needed for the analysis
        published_at=item.get("createdAt"),
        metrics={"comments": item.get("commentsCount")},
        query=query,
        access="fetched",
        tier=2,
        retrieved_at=retrieved_at,
        extra={
            "repo": repo,
            "state": (item.get("state") or "").lower(),
            "labels": [l.get("name") for l in item.get("labels") or []],
        },
    )


def repo_to_record(item, query, retrieved_at):
    return make_record(
        id=f"github:{item['fullName']}",
        source_type="github",
        url=item["url"],
        title=item["fullName"],
        text=item.get("description"),
        author=(item.get("owner") or {}).get("login"),
        published_at=item.get("createdAt"),
        metrics={"stars": item.get("stargazersCount"), "forks": item.get("forksCount")},
        query=query,
        access="fetched",
        tier=2,
        retrieved_at=retrieved_at,
        extra={"language": item.get("language"), "updated_at": item.get("updatedAt")},
    )


def collect(kind, query, limit, created_after=None, runner=run_gh):
    retrieved_at = now_iso()
    if kind == "issues":
        args = ["search", "issues", query, "--limit", str(limit), "--json", ISSUE_FIELDS]
        if created_after:
            args += ["--created", f">={created_after}"]
        return [issue_to_record(i, query, retrieved_at) for i in runner(args)]
    args = ["search", "repos", query, "--limit", str(limit), "--json", REPO_FIELDS]
    if created_after:
        args += ["--created", f">={created_after}"]
    return [repo_to_record(r, query, retrieved_at) for r in runner(args)]


def main(argv=None, runner=run_gh, out=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=["issues", "repos"])
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--created-after", metavar="YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        records = collect(args.kind, args.query, args.limit, args.created_after, runner)
    except SourceError as err:
        print(f"github: {err}", file=sys.stderr)
        return 2
    write_jsonl(records, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
