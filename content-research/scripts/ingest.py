#!/usr/bin/env python3
"""Turn pasted search results into source records, so nobody hand-writes JSON.

    python3 scripts/ingest.py --query "react profiler" >> raw/youtube.jsonl <<'EOF'
    <paste the search tool's result text here>
    EOF

Accepts, in any mix: the `Links: [{"title": ..., "url": ...}]` array a search tool prints,
markdown links `[title](url)`, and plain lines containing one URL ("title - url").
The source (youtube, github, stackoverflow, a Stack Exchange community, hackernews, reddit, or web) is read
from each URL. Question-and-answer pages and forum threads are marked as audience demand (what people ask);
everything else is marked as existing content. These records are titles and URLs only, so they are marked
`snippet` with no date or numbers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normalize import canonical_url  # noqa: E402
from record import make_record, now_iso, write_jsonl  # noqa: E402

_LINKS_ARRAY = re.compile(r"Links:\s*(\[.*?\])\s*(?:\n|$)", re.S)
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_URL = re.compile(r"https?://[^\s)\]>\"']+")
_SUFFIX = re.compile(r"\s*[-|–—]\s*(YouTube|Reddit|GitHub|Stack Overflow|Hacker News)\s*$", re.I)
_USELESS_TITLES = {"dev community", "facebook pixel", "contact us", "home", "untitled", "send email copy email address"}
_DOMAINISH = re.compile(r"^(www\.)?[\w-]+(\.[\w-]+)+$")
_HOSTS = (("youtube.com", "youtube"), ("youtu.be", "youtube"), ("reddit.com", "reddit"), ("github.com", "github"),
          ("stackoverflow.com", "stackoverflow"), ("stackexchange.com", "stackexchange"), ("superuser.com", "stackexchange"),
          ("serverfault.com", "stackexchange"), ("askubuntu.com", "stackexchange"), ("mathoverflow.net", "stackexchange"),
          ("news.ycombinator.com", "hackernews"))
DEMAND_SOURCES = {"reddit", "github", "stackoverflow", "stackexchange", "hackernews"}
_FORUM_HOSTS = ("quora.com",)
_FORUM_PATH = re.compile(r"/(forums?|boards?|community|communities|threads?|discussions?|topics?|questions?|ask)(/|$)", re.I)
_FORUM_FILE = re.compile(r"showtopic|viewtopic|showthread|showflat", re.I)   # forum software URLs such as Tripadvisor's ShowTopic-...


def clean_title(title):
    title = _SUFFIX.sub("", title.strip().strip("-|–—:").strip())
    return re.sub(r"\s+", " ", title)


def informative(title):
    low = title.lower()
    return len(title) > 3 and low not in _USELESS_TITLES and not _DOMAINISH.match(low)


def parse_results(text):
    """Return [(title, url)] from pasted search output, in order, without repeats."""
    pairs = []
    match = _LINKS_ARRAY.search(text)
    if match:
        try:
            pairs += [(d.get("title", ""), d.get("url", "")) for d in json.loads(match.group(1)) if isinstance(d, dict)]
        except json.JSONDecodeError:
            pass
    if not pairs:
        for line in text.splitlines():
            links = _MARKDOWN_LINK.findall(line)
            if links:
                pairs += [(t, u) for t, u in links]
                continue
            found = _URL.search(line)
            if found:
                pairs.append((line.replace(found.group(0), " "), found.group(0).rstrip(".,;")))
    seen, unique = set(), []
    for title, url in pairs:
        if url and url not in seen:
            seen.add(url)
            unique.append((title, url))
    return unique


def source_of(url, default="web"):
    host = (urlsplit(url).hostname or "").lower()
    for suffix, name in _HOSTS:
        if host == suffix or host.endswith("." + suffix):
            return name
    return default


def video_id(url):
    parts = urlsplit(url)
    if (parts.hostname or "").endswith("youtu.be"):
        return parts.path.strip("/").split("/")[0] or None
    if parts.path.startswith(("/shorts/", "/embed/", "/live/")):
        return parts.path.split("/")[2] if len(parts.path.split("/")) > 2 else None
    return (parse_qs(parts.query).get("v") or [None])[0]


def role_of(source, url, role="auto"):
    """demand = what people ask or complain about; supply = content that already exists."""
    if role in ("demand", "supply"):
        return role
    if source in DEMAND_SOURCES:
        return "demand"
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in _FORUM_HOSTS) or _FORUM_PATH.search(parts.path) or _FORUM_FILE.search(parts.path):
        return "demand"
    return "supply"


def to_record(title, url, query, default_source, retrieved_at, role="auto"):
    source = source_of(url, default_source)
    if source == "youtube":
        vid = video_id(url)
        if not vid:
            return None                              # a channel or search page, not a video
        item_id, url = vid, f"https://www.youtube.com/watch?v={vid}"
    else:
        item_id = canonical_url(url)
    return make_record(id=f"{source}:{item_id}", source_type=source, url=url, title=title, query=query,
                       access="snippet", tier=1, retrieved_at=retrieved_at, extra={"role": role_of(source, url, role)})


def ingest(text, query, default_source="web", role="auto"):
    retrieved_at, records, skipped = now_iso(), [], 0
    for title, url in parse_results(text):
        title = clean_title(title)
        record = to_record(title, url, query, default_source, retrieved_at, role) if informative(title) else None
        if record is None:
            skipped += 1
        else:
            records.append(record)
    return records, skipped


def main(argv=None, stdin=None, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--query", required=True, help="the search query these results came from")
    parser.add_argument("--source", default="web", choices=["web", "news"],
                        help="source type for URLs that are not YouTube, GitHub, Stack Overflow, HN or Reddit")
    parser.add_argument("--role", default="auto", choices=["auto", "demand", "supply"],
                        help="demand = people asking or complaining (forums, Q&A); supply = existing content. auto reads the URL")
    args = parser.parse_args(argv)
    text = (stdin or sys.stdin).read()
    records, skipped = ingest(text, args.query, args.source, args.role)
    write_jsonl(records, out)
    print(f"ingest: {len(records)} records kept, {skipped} skipped (no usable title or not a video)", file=err or sys.stderr)
    return 0 if records else 1


if __name__ == "__main__":
    sys.exit(main())
