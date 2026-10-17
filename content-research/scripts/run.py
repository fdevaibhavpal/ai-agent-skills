#!/usr/bin/env python3
"""Run the whole deterministic part in one call: raw records in, report blocks out.

    python3 scripts/run.py --raw raw/ --out out/ --suggest-topics            # help choose topics
    python3 scripts/run.py --raw raw/ --topics topics.json --out out/ --level intermediate --period 90d

Steps: normalize every raw/*.jsonl -> label by rule (scripts/autolabel.py) -> check the signals ->
analyze -> score -> render. Writes evidence.jsonl, signals.jsonl, analysis.json, opportunities.json
and blocks.md into --out, and prints a short summary plus the ranked table. Takes seconds.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as analyze_mod  # noqa: E402
import autolabel  # noqa: E402
import normalize  # noqa: E402
import render  # noqa: E402
import score as score_mod  # noqa: E402
from signals import ConfigError, check_signals, load_topics  # noqa: E402


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv=None, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", default="raw", help="directory of collected .jsonl files")
    parser.add_argument("--out", default="out", help="directory for the results")
    parser.add_argument("--topics", help="topics.json; leave out with --suggest-topics")
    parser.add_argument("--suggest-topics", action="store_true", help="print frequent title phrases and stop")
    parser.add_argument("--level", choices=score_mod.LEVELS, help="audience level; leave out for mixed or unknown")
    parser.add_argument("--period", default="90d", choices=sorted(analyze_mod.PERIODS))
    parser.add_argument("--volume", help="volume.json from scripts/volume.py (optional, for sturdier trends)")
    parser.add_argument("--extra", help="hand-written signals JSONL to add to the automatic ones")
    parser.add_argument("--top", type=int, default=3, help="topics to draw bars for")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr

    files = sorted(glob.glob(os.path.join(args.raw, "*.jsonl")))
    if not files:
        print(f"run: no .jsonl files in {args.raw}/ (collect first)", file=err)
        return 2
    lines = []
    for path in files:
        with open(path, encoding="utf-8") as handle:
            lines += [(f"{os.path.basename(path)}:{n}", line) for n, line in enumerate(handle, 1)]
    accepted, rejected, read = [], [], 0
    schema = normalize.load_schema("source.json")
    for where, line in lines:
        if not line.strip():
            continue
        read += 1
        try:
            record, errors = normalize.normalize_record(json.loads(line), schema)
        except json.JSONDecodeError as error:
            record, errors = None, [f"invalid JSON: {error.msg}"]
        (accepted if record else rejected).append(record if record else (where, errors))
    evidence_list = normalize.deduplicate(accepted)
    evidence = {r["evidence_id"]: r for r in evidence_list}
    os.makedirs(args.out, exist_ok=True)
    write_jsonl(os.path.join(args.out, "evidence.jsonl"), evidence_list)
    print(normalize.summarize(read, rejected, accepted, evidence_list), file=out)
    if not evidence:
        print("run: no usable evidence; stopping", file=err)
        return 2

    if args.suggest_topics or not args.topics:
        print("\nFrequent phrases in titles (count, phrase). Use them to choose 6 to 12 topics:", file=out)
        for gram, count in autolabel.suggest(evidence):
            print(f"  {count:3}  {gram}", file=out)
        return 0

    try:
        lookup, labels = load_topics(args.topics)
        with open(args.topics, encoding="utf-8") as handle:
            topics = json.load(handle)["topics"]
    except (ConfigError, OSError) as error:
        print(f"run: {error}", file=err)
        return 2
    raw_signals, matched, unmatched, promotional = autolabel.label(evidence, topics)
    signal_lines = [(n, json.dumps(s)) for n, s in enumerate(raw_signals, 1)]
    if args.extra:
        with open(args.extra, encoding="utf-8") as handle:
            signal_lines += [(len(signal_lines) + n, l) for n, l in enumerate(handle, 1) if l.strip()]
    signals, bad_signals, duplicates, _ = check_signals(signal_lines, evidence, lookup)
    write_jsonl(os.path.join(args.out, "signals.jsonl"), signals)
    print(f"\nLabeled {matched} of {len(evidence)} records -> {len(signals)} signals "
          f"({len(bad_signals)} rejected, {duplicates} duplicates; {len(promotional)} Show HN posts skipped as promotion). "
          "Unmatched records (add aliases if they matter):", file=out)
    for record in unmatched[:8]:
        print(f"  - {record['title'][:90]}", file=out)
    if len(unmatched) > 8:
        print(f"  ... and {len(unmatched) - 8} more", file=out)
    if not signals:
        print("run: no signals; check the topic aliases against the titles above", file=err)
        return 2

    volume = None
    if args.volume:
        try:
            with open(args.volume, encoding="utf-8") as handle:
                volume = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            print(f"run: cannot use --volume ({error}); continuing without it", file=err)
    now = max(analyze_mod.parse_time(r["retrieved_at"]) for r in evidence.values())
    analysis = analyze_mod.analyze(evidence, signals, labels, analyze_mod.PERIODS[args.period], now, volume)
    with open(os.path.join(args.out, "analysis.json"), "w", encoding="utf-8") as handle:
        json.dump(analysis, handle, indent=2, ensure_ascii=False)
    result = score_mod.score_analysis(analysis, score_mod.load_config(), args.level)
    with open(os.path.join(args.out, "opportunities.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    gaps, trends, competitors = (render.render_gaps(result, args.top), render.render_trends(analysis),
                                 render.render_competitors(analysis))
    with open(os.path.join(args.out, "blocks.md"), "w", encoding="utf-8") as handle:
        handle.write(f"## Ranked opportunities\n\n{gaps}\n## Trends\n\n{trends}\n## Competitors\n\n{competitors}")

    by_source = {}
    for r in evidence.values():
        by_source[r["source_type"]] = by_source.get(r["source_type"], 0) + 1
    print("\nSources: " + ", ".join(f"{k} {v}" for k, v in sorted(by_source.items())), file=out)
    print("\n" + gaps, file=out)
    print("Spot-check: labels are assigned by rule from titles and aliases. Do these belong to their topic?", file=out)
    for item in result["opportunities"][:args.top]:
        print(f"  {item['label']}", file=out)
        for side in ("demand", "supply"):
            for evidence_id in item["evidence_ids"][side][:3]:
                print(f"    {side[0]}: {evidence[evidence_id]['title'][:85]} [{evidence_id}]", file=out)
    print(file=out)
    for warning in result["warnings"][1:] + analysis["limits"]:
        print(f"! {warning}", file=out)
    print(f"\nFiles in {args.out}/: evidence.jsonl signals.jsonl analysis.json opportunities.json blocks.md "
          "(trends and competitors tables are in blocks.md)", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
