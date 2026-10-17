"""Builders shared by the tests."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import normalize  # noqa: E402

DOMAINS = {"reddit": "reddit.com", "github": "github.com", "youtube": "youtube.com",
           "web": "example.com", "news": "news.example.net"}
NOW = "2026-10-17T12:00:00Z"


def ev(n, source_type="reddit", published=None, **overrides):
    """A valid evidence record. `published` is an ISO string or None (undated)."""
    domain = DOMAINS[source_type]
    record = {
        "evidence_id": f"e-{n:08x}",
        "id": f"{source_type}:{n}",
        "source_type": source_type,
        "url": f"https://{domain}/{n}",
        "canonical_url": f"https://{domain}/{n}",
        "domain": domain,
        "title": f"Item {n}",
        "author": None,
        "published_at": published,
        "published_at_raw": None,
        "date_precision": "exact" if published else None,
        "retrieved_at": NOW,
        "text": "",
        "metrics": {},
        "queries": ["q"],
        "access": "fetched",
        "tier": 1,
        "competitor": None,
        "extra": {},
        "duplicate_urls": [],
        "merged_count": 1,
        "warnings": [],
    }
    record.update(overrides)
    record["quality"] = normalize.quality(record)
    return record


def sig(n, type_, topic, statement="Something specific is going on here", **overrides):
    """A validated signal (the shape scripts/signals.py writes)."""
    signal = {"signal_id": f"s-{abs(hash((n, type_, topic, statement))) % 16**8:08x}", "type": type_,
              "topic": topic, "statement": statement, "quote": "a quote from the item",
              "evidence_id": f"e-{n:08x}", "level": "unknown", "format": None}
    signal.update(overrides)
    return signal


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write((record if isinstance(record, str) else json.dumps(record)) + "\n")
