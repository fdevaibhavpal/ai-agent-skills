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


TOPICS = {"topics": [{"topic": t, "label": t.title()} for t in
                     ("profiling", "react-memo", "memory-leaks", "rsc", "testing", "unused-topic")]}


def world():
    """Hand-built dataset; the expected numbers in the tests below are worked out from it.

    now = 2026-10-17T12:00Z, period 90d: recent half is after 09-02T12:00, prior half is
    07-19T12:00 to 09-02T12:00.
    """
    records, signals = [], []

    def add(n, source, published, sigs=(), **kw):
        records.append(ev(n, source, published, **kw))
        signals.extend(sigs)

    add(1, "reddit", "2026-10-10T00:00:00Z", [sig(1, "pain_point", "profiling", "Hard to find unnecessary renders", level="advanced")], metrics={"score": 40, "comments": 12})
    add(2, "reddit", "2026-10-01T00:00:00Z", [sig(2, "question", "profiling", "Which tool shows wasted renders?", level="advanced")], metrics={"score": 10})
    add(3, "reddit", "2026-09-20T00:00:00Z", [sig(3, "question", "profiling", "How do I read the flame graph?", level="intermediate")])
    add(4, "reddit", "2026-09-10T00:00:00Z", [sig(4, "pain_point", "profiling", "hard to find unnecessary renders", level="advanced")])
    for n, day in ((5, "09-01"), (6, "08-20"), (7, "08-10"), (8, "07-25")):
        add(n, "reddit", f"2026-{day}T00:00:00Z", [sig(n, "question", "react-memo")])
    add(9, "github", "2026-10-01T00:00:00Z", [sig(9, "pain_point", "react-memo")])
    add(10, "youtube", "2026-06-01T00:00:00Z", [sig(10, "coverage", "react-memo", format="explainer", level="beginner")], author="SomeChan")
    add(11, "github", "2026-10-05T00:00:00Z", [sig(11, "pain_point", "memory-leaks")])
    add(12, "reddit", "2026-09-20T00:00:00Z", [sig(12, "pain_point", "memory-leaks")])
    add(13, "reddit", "2026-08-15T00:00:00Z", [sig(13, "pain_point", "memory-leaks")])
    add(14, "reddit", "2026-08-01T00:00:00Z", [sig(14, "pain_point", "memory-leaks")])
    add(15, "reddit", "2026-10-09T00:00:00Z", [sig(15, "controversy", "rsc")])
    add(16, "reddit", "2026-10-03T00:00:00Z", [sig(16, "misconception", "rsc")])
    add(17, "reddit", None, [sig(17, "request", "rsc")])
    # ChanA: six videos, one of which is an outlier (1000 views/day vs 100 for the rest)
    videos = [(20, "2026-10-12T00:00:00Z", 5500, "testing", "tutorial", "advanced"),
              (21, "2026-10-02T12:00:00Z", 1500, "profiling", "explainer", "intermediate"),
              (22, "2026-09-17T12:00:00Z", 3000, "testing", "tutorial", "intermediate"),
              (23, "2026-09-02T12:00:00Z", 4500, "testing", "case-study", "advanced"),
              (24, "2026-08-18T12:00:00Z", 6000, "testing", "tutorial", "beginner"),
              (25, "2026-07-19T12:00:00Z", 9000, None, None, None)]
    for n, published, views, topic, fmt, level in videos:
        metrics = {"views": views, **({"likes": 550} if n == 20 else {})}
        sigs = [sig(n, "coverage", topic, format=fmt, level=level)] if topic else []
        add(n, "youtube", published, sigs, metrics=metrics, author="ChanA", competitor="ChanA")
    add(26, "youtube", "2026-10-16T12:00:00Z", [], metrics={"views": 50}, author="Other")
    return {r["evidence_id"]: r for r in records}, signals


def labels():
    return {t["topic"]: t["label"] for t in TOPICS["topics"]}
