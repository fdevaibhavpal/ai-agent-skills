#!/usr/bin/env python3
"""Collect GitHub issues and repositories as source records.

    python3 scripts/github.py issues "memory leak" --repo facebook/react --limit 25
    python3 scripts/github.py repos "react performance" --limit 15
    python3 scripts/github.py issues "rerender" --created-after 2026-01-01 --backend api

Uses the `gh` CLI when it is installed and logged in, otherwise the public GitHub REST API
(no key; 10 searches per minute, or 30 with GITHUB_TOKEN set). Prints JSON Lines to stdout.

Search across all of GitHub returns mostly unrelated repositories. For a topic, scope issues
to the repositories that matter with --repo (repeatable).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch as fetchlib  # noqa: E402
from record import SourceError, make_record, now_iso, write_jsonl  # noqa: E402

API = "https://api.github.com/"
ISSUE_FIELDS = "number,title,body,createdAt,url,repository,commentsCount,state,labels"
REPO_FIELDS = "fullName,description,url,createdAt,updatedAt,stargazersCount,forksCount,language,owner"


def run_gh(args):
    if shutil.which("gh") is None:
        raise SourceError("GitHub CLI `gh` is not installed. Install it and run `gh auth login`, "
                          "or use --backend api for the public REST API.")
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SourceError(proc.stderr.strip() or "gh exited with an error (is it authenticated?)")
    return json.loads(proc.stdout or "[]")


# ---------------------------------------------------------------- gh CLI shape


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


def collect(kind, query, limit, created_after=None, runner=run_gh, repos=()):
    retrieved_at = now_iso()
    if kind == "issues":
        args = ["search", "issues", query, "--limit", str(limit), "--json", ISSUE_FIELDS]
        for repo in repos:
            args += ["--repo", repo]
        if created_after:
            args += ["--created", f">={created_after}"]
        return [issue_to_record(i, query, retrieved_at) for i in runner(args)]
    args = ["search", "repos", query, "--limit", str(limit), "--json", REPO_FIELDS]
    if created_after:
        args += ["--created", f">={created_after}"]
    return [repo_to_record(r, query, retrieved_at) for r in runner(args)]


# ---------------------------------------------------------------- REST API shape


def api_issue_to_record(item, query, retrieved_at):
    repo = item.get("repository_url", "").split("/repos/")[-1]
    return make_record(
        id=f"github:{repo}#{item['number']}",
        source_type="github",
        url=item["html_url"],
        title=item.get("title"),
        text=item.get("body"),
        author=None,
        published_at=item.get("created_at"),
        metrics={"comments": item.get("comments")},
        query=query,
        access="fetched",
        tier=3,
        retrieved_at=retrieved_at,
        extra={"repo": repo, "state": item.get("state"), "labels": [l.get("name") for l in item.get("labels") or []]},
    )


def api_repo_to_record(item, query, retrieved_at):
    return make_record(
        id=f"github:{item['full_name']}",
        source_type="github",
        url=item["html_url"],
        title=item["full_name"],
        text=item.get("description"),
        author=(item.get("owner") or {}).get("login"),
        published_at=item.get("created_at"),
        metrics={"stars": item.get("stargazers_count"), "forks": item.get("forks_count")},
        query=query,
        access="fetched",
        tier=3,
        retrieved_at=retrieved_at,
        extra={"language": item.get("language"), "updated_at": item.get("updated_at")},
    )


def canonical_repo(repo, fetch, headers):
    """The repository's current full name. Search only accepts the current name, not a renamed one."""
    try:
        return fetch(f"{API}repos/{repo}", headers)["full_name"]
    except (SourceError, KeyError) as error:
        raise SourceError(f"repository {repo!r} could not be found ({error})")


def collect_api(kind, query, limit, created_after=None, repos=(), fetch=fetchlib.get_json, token=None):
    retrieved_at = now_iso()
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    terms = [query]
    if kind == "issues":
        terms.append("is:issue")
        terms += [f"repo:{canonical_repo(repo, fetch, headers)}" for repo in repos]
    if created_after:
        terms.append(f"created:>={created_after}")
    endpoint = "search/issues" if kind == "issues" else "search/repositories"
    url = f"{API}{endpoint}?" + urllib.parse.urlencode({"q": " ".join(terms), "per_page": min(limit, 100)})
    data = fetch(url, headers)
    convert = api_issue_to_record if kind == "issues" else api_repo_to_record
    return [convert(item, query, retrieved_at) for item in data.get("items", [])][:limit]


def main(argv=None, runner=run_gh, out=None, fetch=fetchlib.get_json, environ=None, err=None):
    environ = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=["issues", "repos"])
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--created-after", metavar="YYYY-MM-DD")
    parser.add_argument("--repo", action="append", default=[], metavar="OWNER/NAME",
                        help="limit issues to a repository (repeatable)")
    parser.add_argument("--backend", choices=["auto", "gh", "api"], default="auto")
    args = parser.parse_args(argv)
    err = err or sys.stderr
    token = environ.get("GITHUB_TOKEN")
    backend = args.backend
    if backend == "auto":
        backend = "gh" if shutil.which("gh") else "api"
    try:
        if backend == "gh":
            records = collect(args.kind, args.query, args.limit, args.created_after, runner, args.repo)
        else:
            if token:
                fetchlib.default.intervals["api.github.com"] = 2.1  # 30 searches per minute with a token
            records = collect_api(args.kind, args.query, args.limit, args.created_after, args.repo, fetch, token)
    except SourceError as error:
        print(f"github: {error}", file=err)
        return 2
    write_jsonl(records, out)
    print(f"github: {len(records)} {args.kind} via {backend}", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
