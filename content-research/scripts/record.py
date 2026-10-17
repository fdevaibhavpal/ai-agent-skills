"""Shared record shape for collected source items. See sources/_contract.md."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

SOURCE_TYPES = ("web", "reddit", "youtube", "github", "news")
MAX_TEXT = 2000


class SourceError(Exception):
    """A source could not be queried. The message is safe to show to the user."""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_record(*, id, source_type, url, title, tier, query, access,
                text="", author=None, published_at=None, metrics=None,
                competitor=None, extra=None, retrieved_at=None) -> dict:
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"unknown source_type: {source_type!r}")
    if not url:
        raise ValueError("a record needs the URL it was retrieved from")
    # Keep only metrics that were observed (not None).
    observed = {k: v for k, v in (metrics or {}).items() if v is not None}
    return {
        "id": id,
        "source_type": source_type,
        "url": url,
        "title": title or "",
        "author": author,
        "published_at": published_at,
        "retrieved_at": retrieved_at or now_iso(),
        "text": (text or "")[:MAX_TEXT],
        "metrics": observed,
        "query": query,
        "access": access,
        "tier": tier,
        "competitor": competitor,
        "extra": extra or {},
    }


def write_jsonl(records, stream=None) -> int:
    stream = stream or sys.stdout
    count = 0
    for record in records:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        count += 1
    return count
