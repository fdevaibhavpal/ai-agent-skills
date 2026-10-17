#!/usr/bin/env python3
"""Check agent-extracted signals against the evidence set and the topic vocabulary.

    python3 scripts/signals.py evidence.jsonl topics.json signals.raw.jsonl > signals.jsonl

Every signal must point at a real evidence record, use a topic from the vocabulary,
and carry a quote that actually appears in that record. Anything else is rejected
(with the reason on stderr) rather than repaired, so the analysis only counts
signals the evidence supports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema_check import load_schema, validate  # noqa: E402

COVERAGE_SOURCES = ("web", "youtube", "news")  # forum and issue threads are demand, not supply
_QUOTE_FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                             "–": "-", "—": "-", " ": " "})


class ConfigError(Exception):
    """The evidence or topic file is unusable. The message is safe to show."""


def read_jsonl(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return [(n, line) for n, line in enumerate(handle, 1) if line.strip()]
    except OSError as err:
        raise ConfigError(f"cannot read {path}: {err.strerror}")


def load_evidence(path):
    records = {}
    for number, line in read_jsonl(path):
        try:
            record = json.loads(line)
            records[record["evidence_id"]] = record
        except (json.JSONDecodeError, KeyError, TypeError):
            raise ConfigError(f"{path}:{number} is not an evidence record (run scripts/normalize.py first)")
    return records


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_topics(path):
    """Return (lookup, labels): lookup maps slug, label and aliases (lowercased) to the slug."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as err:
        raise ConfigError(f"cannot read {path}: {err.strerror}")
    except json.JSONDecodeError as err:
        raise ConfigError(f"{path} is not valid JSON: {err.msg}")
    errors = validate(data, load_schema("topics.json"))
    if errors:
        raise ConfigError(f"{path}: " + "; ".join(errors))
    if not data["topics"]:
        raise ConfigError(f"{path}: define at least one topic")
    lookup, labels = {}, {}
    for entry in data["topics"]:
        slug = entry["topic"]
        if slug in labels:
            raise ConfigError(f"{path}: topic {slug!r} is defined twice")
        labels[slug] = entry["label"]
        for name in [slug, entry["label"], *entry.get("aliases", [])]:
            key = name.strip().lower()
            if lookup.setdefault(key, slug) != slug:
                raise ConfigError(f"{path}: {name!r} belongs to both {lookup[key]!r} and {slug!r}")
    return lookup, labels


def resolve_topic(name, lookup):
    key = name.strip().lower()
    return lookup.get(key) or lookup.get(slugify(key))


def _fold(text):
    return re.sub(r"\s+", " ", text.translate(_QUOTE_FOLD)).strip().lower()


def quote_in(quote, evidence):
    """True if the quote's fragments (split on '...') appear, in order, in the title or text."""
    haystack = _fold(f"{evidence['title']} {evidence['text']}")
    fragments = [_fold(f) for f in re.split(r"\.\.\.|…", quote) if f.strip()]
    if sum(len(f) for f in fragments) < 8:
        return False
    position = 0
    for fragment in fragments:
        found = haystack.find(fragment, position)
        if found < 0:
            return False
        position = found + len(fragment)
    return True


def check_signal(raw, evidence, lookup, schema):
    """Return (signal, None) or (None, reason)."""
    errors = validate(raw, schema)
    if errors:
        return None, "; ".join(errors)
    record = evidence.get(raw["evidence_id"])
    if record is None:
        return None, f"evidence_id {raw['evidence_id']} is not in the evidence set"
    topic = resolve_topic(raw["topic"], lookup)
    if topic is None:
        return None, f"unknown topic {raw['topic']!r} (use a topic from topics.json)"
    if raw["type"] == "coverage" and record["source_type"] not in COVERAGE_SOURCES:
        return None, f"coverage signals need web, youtube or news evidence, not {record['source_type']}"
    if not quote_in(raw["quote"], record):
        return None, "quote does not appear in the evidence text"
    signal = {
        "type": raw["type"],
        "topic": topic,
        "statement": raw["statement"].strip(),
        "quote": raw["quote"].strip(),
        "evidence_id": raw["evidence_id"],
        "level": raw.get("level", "unknown"),
        "format": raw.get("format"),
    }
    basis = f"{signal['evidence_id']}|{signal['type']}|{topic}|{signal['statement'].lower()}"
    signal["signal_id"] = "s-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:8]
    return signal, None


def check_signals(lines, evidence, lookup):
    """Return (signals, rejected [(line number, reason)], duplicates dropped, lines read)."""
    schema = load_schema("signal.json")
    signals, rejected, seen, duplicates, read = [], [], set(), 0, 0
    for number, line in lines:
        read += 1
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as err:
            rejected.append((number, f"invalid JSON: {err.msg}"))
            continue
        signal, reason = check_signal(raw, evidence, lookup, schema)
        if reason:
            rejected.append((number, reason))
            continue
        key = (signal["evidence_id"], signal["type"], signal["topic"])
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        signals.append(signal)
    return signals, rejected, duplicates, read


def summarize(read, rejected, duplicates, signals, evidence):
    by_type = Counter(s["type"] for s in signals)
    covered = len({s["evidence_id"] for s in signals})
    lines = [f"signals: {read} read, {len(rejected)} rejected, {duplicates} duplicates dropped "
             f"-> {len(signals)} signals",
             "  by type: " + (", ".join(f"{k} {v}" for k, v in sorted(by_type.items())) or "none"),
             f"  evidence with at least one signal: {covered} of {len(evidence)}"]
    lines += [f"  rejected line {n}: {reason}" for n, reason in rejected]
    return "\n".join(lines)


def main(argv=None, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("evidence", help="evidence.jsonl from normalize.py")
    parser.add_argument("topics", help="topics.json vocabulary")
    parser.add_argument("signals", help="raw signals JSONL written by the agent")
    parser.add_argument("--strict", action="store_true", help="exit 1 if any signal was rejected")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        evidence = load_evidence(args.evidence)
        lookup, _ = load_topics(args.topics)
        lines = read_jsonl(args.signals)
    except ConfigError as error:
        print(f"signals: {error}", file=err)
        return 2
    signals, rejected, duplicates, read = check_signals(lines, evidence, lookup)
    for signal in signals:
        out.write(json.dumps(signal, ensure_ascii=False) + "\n")
    print(summarize(read, rejected, duplicates, signals, evidence), file=err)
    return 1 if (args.strict and rejected) else 0


if __name__ == "__main__":
    sys.exit(main())
