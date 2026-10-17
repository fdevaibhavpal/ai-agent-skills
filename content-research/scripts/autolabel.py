#!/usr/bin/env python3
"""Label evidence with topics by rule, so the model does not write a signal per record.

    python3 scripts/autolabel.py evidence.jsonl topics.json > signals.jsonl      # label
    python3 scripts/autolabel.py evidence.jsonl --suggest                        # help choose topics

The model supplies the topic list (slugs, labels, aliases). This script matches those terms in each
record's title (and, for discussion sources, the start of its text) and assigns a signal type from
the source: questions and pain points from Stack Overflow, Reddit and GitHub; interest from Hacker
News; coverage from YouTube, web and news. The quote is always the record's own title, so every
signal passes the same quote check as hand-written ones. Level and format come from title words
and are left unknown otherwise. Rules are cruder than reading, so the output lists what matched
nothing: add aliases for those and run it again.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals import ConfigError, check_signals, load_evidence, load_topics  # noqa: E402

TEXT_CHARS = 400            # how much of the text counts for discussion sources
MIN_TEXT_HITS = 2           # a topic named only in the body needs this many terms there (one passing mention is not the subject)
MAX_TOPICS_PER_RECORD = 3
COVERAGE_SOURCES = ("youtube", "web", "news")   # supply unless the record says it is a forum or Q&A page
QUESTION_WORDS = ("how", "why", "what", "when", "which", "should", "can", "is", "does", "do", "are", "will")
FORMAT_WORDS = (
    ("case-study", ("case study", "real world", "real code", "benchmark", "lessons learned", "post mortem", "we rebuilt")),
    ("talk", ("talk", "keynote", "conference", "podcast", "episode", "interview", "panel", "meetup", "webinar")),
    ("reference", ("reference", "cheat sheet", "cheatsheet", "docs", "documentation", "api guide")),
    ("news", ("announcing", "announcement", "release", "released", "now available", "changelog", "what's new")),
    ("tutorial", ("tutorial", "how to", "course", "guide", "step by step", "build a", "let's build", "walkthrough", "fix", "tips")),
    ("explainer", ("explained", "what is", "why", "understanding", "deep dive", "introduction", "intro to", "vs", "myths")),
)
LEVEL_WORDS = (
    ("beginner", ("beginner", "beginners", "basics", "101", "for dummies", "getting started", "what is", "introduction", "intro to")),
    ("advanced", ("advanced", "deep dive", "senior", "expert", "internals", "under the hood", "in production")),
    ("intermediate", ("intermediate",)),
)
_STOP = set("a an and are as at be by do does for from has have how i in into is it its my of on or so that the their there this to was what when where which who why will with you your about after all also any can could get just like make more most new not now one only other out over should some than then them these they use used using way we were would vs via".split())


def _stem(token):
    return token[:-1] if len(token) > 3 and token.endswith("s") and not token.endswith("ss") else token


def tokens(text):
    return [_stem(t) for t in re.sub(r"[^a-z0-9]+", " ", text.lower()).split()]


def term_matcher(term):
    """A function that says whether a phrase appears in a token list, tolerating re-render / rerender."""
    words = tokens(term)
    compact = "".join(words)
    if not words:
        return lambda toks, joined: False

    def match(toks, joined):
        n = len(words)
        if any(toks[i:i + n] == words for i in range(len(toks) - n + 1)):
            return True
        return len(words) > 1 and compact in joined          # "re render" also matches "rerender"
    return match


def build_matchers(topics):
    matchers = {}
    for entry in topics:
        terms = {entry["topic"].replace("-", " "), entry["label"], *entry.get("aliases", [])}
        terms = [t for t in terms if len(tokens(t)) > 0 and not (len(tokens(t)) == 1 and tokens(t)[0] in _STOP)]
        matchers[entry["topic"]] = [term_matcher(t) for t in terms]
    return matchers


def hits(matchers, text):
    toks = tokens(text)
    joined = set(toks) | {a + b for a, b in zip(toks, toks[1:])}
    return sum(1 for m in matchers if m(toks, joined))


def pick(words_by_value, title):
    """The first value whose words appear (as whole words or phrases) in the title."""
    low = title.lower()
    for value, words in words_by_value:
        if any(re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", low) for w in words):
            return value
    return None


def is_promotion(record):
    """A creator announcing their own project ("Show HN: ...") is supply, not audience demand."""
    return record["source_type"] == "hackernews" and record["title"].lower().startswith("show hn")


def signal_type(record):
    source, title = record["source_type"], record["title"].strip()
    role = (record.get("extra") or {}).get("role")
    if role == "supply" or (role is None and source in COVERAGE_SOURCES):
        return "coverage"
    if source == "hackernews":
        return "question" if title.lower().startswith("ask hn") else "interest"
    first = title.lower().split(" ", 1)[0].strip(",:")
    if title.endswith("?") or first in QUESTION_WORDS:
        return "question"
    return "pain_point"


def label(evidence, topics):
    """Return (raw signals, matched count, unmatched records, promotional records skipped) for a list of topics."""
    matchers = build_matchers(topics)
    signals, unmatched, matched, promotional = [], [], 0, []
    for record in evidence.values():
        if is_promotion(record):
            promotional.append(record)
            continue
        kind = signal_type(record)
        scored = []
        for topic, ms in matchers.items():
            title_hits = hits(ms, record["title"])
            text_hits = 0 if kind == "coverage" else hits(ms, record["text"][:TEXT_CHARS])
            weight = 2 * title_hits + text_hits
            if title_hits or (kind != "coverage" and text_hits >= MIN_TEXT_HITS):
                scored.append((weight, topic))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        if not scored:
            unmatched.append(record)
            continue
        matched += 1
        fmt = pick(FORMAT_WORDS, record["title"]) if kind == "coverage" else None
        level = pick(LEVEL_WORDS, record["title"]) or "unknown"
        label_of = {t["topic"]: t["label"] for t in topics}
        for _, topic in scored[:MAX_TOPICS_PER_RECORD]:
            statement = (f"Existing {fmt or 'content'} about {label_of[topic]}" if kind == "coverage"
                         else record["title"][:140])
            signal = {"type": kind, "topic": topic, "statement": statement if len(statement) >= 8 else statement + " (topic)",
                      "quote": record["title"], "evidence_id": record["evidence_id"], "level": level}
            if fmt:
                signal["format"] = fmt
            if len(signal["quote"]) >= 8:
                signals.append(signal)
    return signals, matched, unmatched, promotional


def suggest(evidence, top=30, minimum=3, max_share=0.5):
    """Frequent words and phrases in titles, to help choose topics without reading every title.

    Words and phrases found in more than `max_share` of the titles are the subject itself, not a
    topic within it, so they are left out.
    """
    counts, total = Counter(), len(evidence)
    for record in evidence.values():
        words = re.sub(r"[^a-z0-9]+", " ", record["title"].lower()).split()
        seen = set()
        for n in (1, 2, 3):
            for i in range(len(words) - n + 1):
                gram = words[i:i + n]
                if gram[0] in _STOP or gram[-1] in _STOP:
                    continue
                phrase = " ".join(gram)
                if len(phrase) >= (5 if n == 1 else 7):
                    seen.add(phrase)
        counts.update(seen)
    ranked = [(g, c) for g, c in counts.most_common() if c >= minimum and c <= max_share * total]
    # drop a phrase that is only a piece of a longer, equally frequent one
    kept = [(g, c) for g, c in ranked if not any(g != h and g in h and d >= c for h, d in ranked)]
    return kept[:top]


def main(argv=None, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("evidence")
    parser.add_argument("topics", nargs="?", help="topics.json (not needed with --suggest)")
    parser.add_argument("--suggest", action="store_true", help="print frequent title phrases to help choose topics")
    parser.add_argument("--extra", help="hand-written signals JSONL to add (checked like the rest)")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        evidence = load_evidence(args.evidence)
        if args.suggest:
            for gram, count in suggest(evidence):
                print(f"{count:3}  {gram}", file=out)
            return 0
        if not args.topics:
            print("autolabel: give topics.json, or use --suggest", file=err)
            return 2
        lookup, _ = load_topics(args.topics)
        with open(args.topics, encoding="utf-8") as handle:
            topics = json.load(handle)["topics"]
    except ConfigError as error:
        print(f"autolabel: {error}", file=err)
        return 2
    raw, matched, unmatched, promotional = label(evidence, topics)
    lines = [(n, json.dumps(s)) for n, s in enumerate(raw, 1)]
    if args.extra:
        with open(args.extra, encoding="utf-8") as handle:
            lines += [(len(lines) + n, line) for n, line in enumerate(handle, 1) if line.strip()]
    signals, rejected, duplicates, _ = check_signals(lines, evidence, lookup)
    for signal in signals:
        out.write(json.dumps(signal, ensure_ascii=False) + "\n")
    print(f"autolabel: {matched} of {len(evidence)} records matched a topic -> {len(signals)} signals "
          f"({len(rejected)} rejected, {duplicates} duplicates, {len(promotional)} Show HN posts skipped)", file=err)
    for record in unmatched[:10]:
        print(f"  unmatched: {record['title'][:90]}", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
