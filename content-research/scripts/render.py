#!/usr/bin/env python3
"""Turn analysis output into Markdown tables and bars, so numbers in a report are copied, not retyped.

    python3 scripts/render.py gaps opportunities.json --top 5
    python3 scripts/render.py trends analysis.json
    python3 scripts/render.py competitors analysis.json

The agent writes the prose around these blocks and pastes them unchanged.
"""
from __future__ import annotations

import argparse
import json
import sys

BAR_WIDTH = 20
FULL, EMPTY = "\u2588", "\u2591"


def bar(value):
    if value is None:
        return "n/a (not measured)"
    filled = max(0, min(BAR_WIDTH, round(value / 100 * BAR_WIDTH)))
    return f"{FULL * filled}{EMPTY * (BAR_WIDTH - filled)} {value:5.1f}"


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def number(value):
    return "n/a" if value is None else f"{value:g}"


def table(headers, rows, right=()):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---:" if h in right else "---" for h in headers) + "|"]
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def render_gaps(result, top=5):
    items = result["opportunities"]
    if not items:
        return "_No topic had enough demand evidence to score._\n"
    rows = [[o["rank"], o["label"], f"{o['score']:.1f}", o["tier"], o["confidence"], o["growth"]["direction"],
             number(o["indices"]["demand"]), number(o["indices"]["supply"]), number(o["indices"]["gap"])]
            for o in items]
    out = [table(["#", "Topic", "Score", "Tier", "Confidence", "Growth", "Demand", "Supply", "Gap"], rows,
                 right=("Score", "Demand", "Supply", "Gap")), "",
           "Demand, supply and gap are 0 to 100 and relative to the strongest topic in this run. "
           "Supply counts existing content at the audience's level more than content at other levels.", ""]
    for o in items[:top]:
        out += [f"**{o['label']}**", "```",
                f"demand {bar(o['indices']['demand'])}", f"supply {bar(o['indices']['supply'])}",
                f"gap    {bar(o['indices']['gap'])}", "```", ""]
    if result["unscored"]:
        out += ["Not scored: " + "; ".join(f"{u['label'] if 'label' in u else u['topic']} ({u['reason']})"
                                          for u in result["unscored"]), ""]
    return "\n".join(out)


def render_trends(analysis):
    groups = {}
    for t in analysis["trends"]:
        groups.setdefault(t["direction"], []).append(t)
    out = []
    for direction in ("emerging", "growing", "stable", "declining", "unknown"):
        items = groups.get(direction, [])
        if not items:
            continue
        out += [f"**{direction.capitalize()}**", "",
                table(["Topic", "Basis", "Why"], [[t["topic"], t["basis"], t["reason"]] for t in items]), ""]
    thresholds = analysis["meta"]["thresholds"]
    out.append(f"Directions are heuristic. Sample trends need {thresholds['min_dated']} dated records; volume trends need "
               f"{thresholds['volume_min']} source-reported items and a {thresholds['volume_ratio']}x change in share.")
    return "\n".join(out) + "\n"


def render_competitors(analysis):
    block = analysis["competitors"]
    if not block["competitors"]:
        return "_No competitor content was collected._\n"
    rows = []
    for c in block["competitors"]:
        rows.append([c["competitor"], c["items"], number(c["items_per_30d"]), f"{c['topical_share']:.0%}",
                     "off-topic" if c["off_topic"] else "on-topic", number(c["median_views_per_day"]),
                     len(c["outliers"])])
    out = [table(["Competitor", "Items", "Per 30 days", "On-topic share", "Relevance", "Median views/day", "Outliers"],
                 rows, right=("Items", "Per 30 days", "Median views/day", "Outliers")), ""]
    if block["topic_coverage"]:
        out += ["**Topics covered by on-topic competitors**", "",
                table(["Topic", "Competitors", "Items"], [[t, c["competitors"], c["items"]]
                                                           for t, c in block["topic_coverage"].items()]), ""]
    if block["on_topic"] and block["demand_topics_no_competitor_coverage"]:
        out += ["Topics with audience demand and no on-topic competitor coverage in the sampled items: "
                + ", ".join(block["demand_topics_no_competitor_coverage"]), ""]
    if not block["on_topic"]:
        out += ["_No sampled competitor was on-topic, so no competitor coverage or blind spot is claimed._", ""]
    for c in block["competitors"]:
        if c["top_items"] and not c["off_topic"]:
            out += [f"**Top items: {c['competitor']}**", "",
                    table(["Title", "Views/day", "Age (days)", "Note"],
                          [[i["title"][:80], f"{i['views_per_day']:g}", f"{i['age_days']:g}",
                            "low confidence" if i["low_confidence"] else ""] for i in c["top_items"]],
                          right=("Views/day", "Age (days)")), ""]
    return "\n".join(out)


def main(argv=None, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("view", choices=["gaps", "trends", "competitors"])
    parser.add_argument("file", help="opportunities.json for gaps; analysis.json for trends and competitors")
    parser.add_argument("--top", type=int, default=5, help="topics to draw bars for (gaps)")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        with open(args.file, encoding="utf-8") as handle:
            data = json.load(handle)
        text = {"gaps": lambda: render_gaps(data, args.top), "trends": lambda: render_trends(data),
                "competitors": lambda: render_competitors(data)}[args.view]()
    except OSError as error:
        print(f"render: cannot read {error.filename}: {error.strerror}", file=err)
        return 2
    except (json.JSONDecodeError, KeyError, TypeError):
        print(f"render: {args.file} is not the right kind of file for `{args.view}` "
              "(gaps needs opportunities.json from score.py; the others need analysis.json from analyze.py)", file=err)
        return 2
    out.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
