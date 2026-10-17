#!/usr/bin/env python3
"""Tally validated signals into themes, trends, engagement and competitor coverage.

    python3 scripts/analyze.py evidence.jsonl signals.jsonl topics.json --period 90d > analysis.json

Everything here is counting and arithmetic on observed data. The thresholds are
heuristics, named at the top of this file; the report must say so. Interpretation
(why a theme matters, what to make) is the agent's job and comes after this step.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normalize import ISO_FORMAT  # noqa: E402
from signals import ConfigError, load_evidence, load_topics, read_jsonl  # noqa: E402

PERIODS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
MIN_DATED = 4                # fewer dated records than this: direction is "unknown"
GROWTH_RATIO = 1.5           # recent half must be this many times the prior half (and differ by 2+)
MIN_DELTA = 2
OUTLIER_FACTOR = 3           # views/day at least this many times the competitor's median
OUTLIER_MIN_ITEMS = 5
MIN_COMPETITOR_ITEMS = 10    # below this, do not generalize about a competitor
OFF_TOPIC_SHARE = 0.2        # a competitor with fewer on-topic items than this is not a competitor for the topic
VOLUME_MIN = 20              # source-reported items across both windows needed to classify a volume trend
VOLUME_RATIO = 1.5           # change in share of the platform baseline that counts as growing or declining
YOUNG_DAYS = 3               # views/day on very new or tiny items is noisy
LOW_VIEWS = 100
TOP_ITEMS = 10


def parse_time(text):
    return datetime.strptime(text, ISO_FORMAT).replace(tzinfo=timezone.utc)


def age_days(record, now):
    if not record["published_at"]:
        return None
    return max((now - parse_time(record["published_at"])).total_seconds() / 86400, 0.0)


def views_per_day(record, now):
    age = age_days(record, now)
    views = record["metrics"].get("views")
    if age is None or views is None:
        return None
    return views / max(age, 1.0)


def median(values):
    return statistics.median(values) if values else None


def round_or_none(value, places=1):
    return None if value is None else round(value, places)


def _ordered(ids):
    return list(dict.fromkeys(ids))


def _creator(record):
    """Who made it: the named author or channel, or the site for web pages. None when unknown, so a
    search result that names no channel does not make every YouTube video look like one creator."""
    return record["author"] or (record["domain"] if record["source_type"] in ("web", "news") else None)


# ---------------------------------------------------------------- themes


def themes(evidence, signals, labels, now):
    by_topic = defaultdict(list)
    for signal in signals:
        by_topic[signal["topic"]].append(signal)

    result = []
    for topic, items in by_topic.items():
        demand = [s for s in items if s["type"] != "coverage"]
        supply = [s for s in items if s["type"] == "coverage"]
        demand_ids = _ordered(s["evidence_id"] for s in demand)
        supply_ids = _ordered(s["evidence_id"] for s in supply)
        demand_records = [evidence[i] for i in demand_ids]
        supply_records = [evidence[i] for i in supply_ids]

        totals = Counter()
        for record in demand_records:
            totals.update(record["metrics"])
        statements = Counter(s["statement"].lower() for s in demand)
        first_seen = {}
        for s in demand:
            first_seen.setdefault(s["statement"].lower(), s["statement"])
        per_day = [v for v in (views_per_day(r, now) for r in supply_records) if v is not None]
        dated = [evidence[i] for i in _ordered(demand_ids + supply_ids) if evidence[i]["published_at"]]

        result.append({
            "topic": topic,
            "label": labels.get(topic, topic),
            "demand": {
                "signals": len(demand),
                "evidence": len(demand_ids),
                "source_types": dict(Counter(r["source_type"] for r in demand_records)),
                "domains": len({r["domain"] for r in demand_records}),
                "by_type": dict(Counter(s["type"] for s in demand)),
                "by_level": dict(Counter(s["level"] for s in demand)),
                "metrics_total": dict(totals),
                "evidence_with_metrics": sum(1 for r in demand_records if r["metrics"]),
                "evidence_with_views": sum(1 for r in demand_records if "views" in r["metrics"]),
                "top_statements": [first_seen[k] for k, _ in statements.most_common(3)],
            },
            "supply": {
                "signals": len(supply),
                "evidence": len(supply_ids),
                "creators": len({c for c in map(_creator, supply_records) if c}),
                "by_level": dict(Counter(s["level"] for s in supply)),
                "by_format": dict(Counter(s["format"] or "unspecified" for s in supply)),
                "median_views_per_day": round_or_none(median(per_day)),
            },
            "evidence_ids": {"demand": demand_ids, "supply": supply_ids},
            "dated_evidence": len(dated),
            "undated_evidence": len(_ordered(demand_ids + supply_ids)) - len(dated),
        })
    result.sort(key=lambda t: (-t["demand"]["evidence"], -t["supply"]["evidence"], t["topic"]))
    return result


# ---------------------------------------------------------------- trends


def classify(recent, prior, outside, dated):
    """Return (direction, reason). Heuristic; see the constants at the top of the file."""
    if dated < MIN_DATED:
        return "unknown", f"only {dated} dated records in the period (need {MIN_DATED})"
    counts = f"{recent} dated records in the recent half of the period vs {prior} in the prior half"
    if prior == 0 and outside == 0 and recent >= MIN_DATED:
        return "emerging", counts + ", and none earlier"
    if recent >= GROWTH_RATIO * prior and recent - prior >= MIN_DELTA:
        return "growing", counts
    if prior >= GROWTH_RATIO * recent and prior - recent >= MIN_DELTA:
        return "declining", counts
    return "stable", counts


def trends(evidence, signals, period_days, now):
    half = timedelta(days=period_days / 2)
    ids_by_topic = defaultdict(list)
    demand_ids = defaultdict(set)
    for signal in signals:
        ids_by_topic[signal["topic"]].append(signal["evidence_id"])
        if signal["type"] != "coverage":
            demand_ids[signal["topic"]].add(signal["evidence_id"])

    result = []
    for topic, ids in ids_by_topic.items():
        recent = prior = outside = undated = recent_d = prior_d = 0
        for evidence_id in _ordered(ids):
            record = evidence[evidence_id]
            if not record["published_at"]:
                undated += 1
                continue
            published = parse_time(record["published_at"])
            is_demand = evidence_id in demand_ids[topic]
            if published > now - half:
                recent += 1
                recent_d += is_demand
            elif published > now - 2 * half:
                prior += 1
                prior_d += is_demand
            else:
                outside += 1
        direction, reason = classify(recent, prior, outside, recent + prior)
        result.append({"topic": topic, "direction": direction, "reason": reason, "basis": "sample",
                       "recent": recent, "prior": prior, "outside_period": outside,
                       "undated": undated, "demand_recent": recent_d, "demand_prior": prior_d})
    return sort_trends(result)


TREND_ORDER = {"emerging": 0, "growing": 1, "stable": 2, "declining": 3, "unknown": 4}


def sort_trends(result):
    result.sort(key=lambda t: (TREND_ORDER[t["direction"]], -t["recent"], t["topic"]))
    return result


def _items(n):
    return f"{n} item" + ("" if n == 1 else "s")


def classify_volume(recent, prior, base_recent, base_prior):
    """Direction from item counts the sources themselves reported for two equal windows.

    With a platform baseline (all items on the platform in the same windows) the comparison is of
    the topic's share, so a platform-wide slump or surge is not mistaken for a topic trend.
    """
    total = recent + prior
    if total < VOLUME_MIN:
        return "unknown", f"only {_items(total)} matched across both windows (need {VOLUME_MIN})"
    if prior == 0:
        return "emerging", f"{_items(recent)} matched in the recent window and none in the prior window"
    if base_recent and base_prior:
        ratio = (recent / base_recent) / (prior / base_prior)
    else:
        ratio = recent / prior
    epsilon = 1e-9  # 0.15 / 0.10 is 1.4999999999999998 in floating point; a value on the threshold counts
    if ratio >= VOLUME_RATIO - epsilon:
        return "growing", f"share rose by a factor of {ratio:.1f}"
    if ratio <= 1 / VOLUME_RATIO + epsilon:
        return "declining", f"share fell to {ratio:.2f} of its earlier level"
    return "stable", f"share changed by a factor of {ratio:.1f}"


def apply_volume(trend_list, volume, half_days):
    """Replace a topic's direction with the volume-based one where the sources reported counts."""
    baseline = volume["meta"].get("baseline", {})
    by_topic = {t["topic"]: t for t in trend_list}
    for topic, entry in volume["topics"].items():
        trend = by_topic.get(topic)
        sources = entry.get("sources", {})
        if trend is None or not sources:
            continue
        recent = sum(c["recent"] for c in sources.values())
        prior = sum(c["prior"] for c in sources.values())
        base = [baseline.get(name) for name in sources]
        have_base = all(b and b["recent"] and b["prior"] for b in base)
        direction, why = classify_volume(recent, prior, sum(b["recent"] for b in base) if have_base else 0,
                                         sum(b["prior"] for b in base) if have_base else 0)
        trend.update(
            direction=direction, basis="volume",
            reason=(f"{_items(recent)} in the recent {half_days:g} days vs {prior} in the prior {half_days:g} days "
                    f"({', '.join(sorted(sources))}); {why}"),
            volume={"recent": recent, "prior": prior, "sources": sorted(sources), "baseline": have_base})
    return sort_trends(trend_list)


# ---------------------------------------------------------------- engagement


def engagement_item(record, now):
    views = record["metrics"]["views"]
    per_day = views_per_day(record, now)
    age = age_days(record, now)
    likes = record["metrics"].get("likes")
    return {
        "evidence_id": record["evidence_id"],
        "source_type": record["source_type"],
        "title": record["title"],
        "url": record["url"],
        "author": record["author"],
        "views": views,
        "views_per_day": round(per_day, 1),
        "age_days": round(age, 1),
        "like_rate": round(likes / views, 4) if likes is not None and views else None,
        "low_confidence": age < YOUNG_DAYS or views < LOW_VIEWS,
    }


def engagement(evidence, now):
    items = [engagement_item(r, now) for r in evidence.values()
             if "views" in r["metrics"] and r["published_at"]]
    items.sort(key=lambda i: (-i["views_per_day"], i["evidence_id"]))
    by_source = defaultdict(list)
    for item in items:
        by_source[item["source_type"]].append(item["views_per_day"])
    return {
        "top_by_views_per_day": items[:TOP_ITEMS],
        "by_source": {k: {"items": len(v), "median_views_per_day": round(median(v), 1), "max_views_per_day": max(v)}
                      for k, v in sorted(by_source.items())},
    }


# ---------------------------------------------------------------- competitors


def competitors(evidence, signals, now, themes_list):
    signals_by_evidence = defaultdict(list)
    for signal in signals:
        signals_by_evidence[signal["evidence_id"]].append(signal)
    groups = defaultdict(list)
    for record in evidence.values():
        if record["competitor"]:
            groups[record["competitor"]].append(record)

    result, topic_creators, topic_items = [], defaultdict(set), Counter()
    for name, records in sorted(groups.items()):
        dated = sorted(parse_time(r["published_at"]) for r in records if r["published_at"])
        span = (dated[-1] - dated[0]).total_seconds() / 86400 if len(dated) > 1 else 0
        cadence = round(len(dated) / max(span, 30) * 30, 1) if len(dated) >= 3 else None
        topical = sum(1 for r in records if signals_by_evidence[r["evidence_id"]])
        off_topic = topical / len(records) < OFF_TOPIC_SHARE   # their recent work is about something else

        topics, formats = Counter(), Counter()
        for record in records:
            record_topics = {s["topic"] for s in signals_by_evidence[record["evidence_id"]]}
            topics.update(record_topics)
            if not off_topic:
                for topic in record_topics:
                    topic_creators[topic].add(name)
                    topic_items[topic] += 1
            formats.update(s["format"] or "unspecified" for s in signals_by_evidence[record["evidence_id"]]
                           if s["type"] == "coverage")

        with_views = [engagement_item(r, now) for r in records if "views" in r["metrics"] and r["published_at"]]
        with_views.sort(key=lambda i: (-i["views_per_day"], i["evidence_id"]))
        typical = median([i["views_per_day"] for i in with_views])
        outliers = []
        if len(with_views) >= OUTLIER_MIN_ITEMS and typical:
            outliers = [i for i in with_views if i["views_per_day"] >= OUTLIER_FACTOR * typical]

        result.append({
            "competitor": name,
            "items": len(records),
            "dated_items": len(dated),
            "items_per_30d": cadence,
            "enough_data": len(records) >= MIN_COMPETITOR_ITEMS,
            "topical_share": round(topical / len(records), 2),
            "off_topic": off_topic,
            "topics": dict(topics.most_common()),
            "formats": dict(formats),
            "median_views_per_day": round_or_none(typical),
            "top_items": with_views[:5],
            "outliers": outliers,
            "items_without_signals": len(records) - topical,
            "sampled_from_latest": any(r["queries"] and r["queries"][0].startswith("channel feed") for r in records),
        })

    on_topic = sum(1 for c in result if not c["off_topic"])
    demand_topics = [t["topic"] for t in themes_list if t["demand"]["evidence"] > 0]
    return {
        "competitors": result,
        "on_topic": on_topic,
        "topic_coverage": {t: {"competitors": len(c), "items": topic_items[t]}
                           for t, c in sorted(topic_creators.items(), key=lambda kv: (-len(kv[1]), kv[0]))},
        # with no on-topic competitor there is nothing to compare against, so no blind spot is claimed
        "demand_topics_no_competitor_coverage": ([t for t in demand_topics if t not in topic_creators]
                                                 if on_topic else []),
    }


# ---------------------------------------------------------------- limits


def limits(evidence, signals, trend_list, competitor_block):
    notes = []
    total = len(evidence)
    if not total:
        return ["There is no evidence."]
    undated = sum(1 for r in evidence.values() if not r["published_at"])
    if undated / total > 0.25:
        notes.append(f"{undated} of {total} evidence records have no publication date, so trend directions "
                     "and views per day cover only the dated part.")
    unlabeled = total - len({s["evidence_id"] for s in signals})
    if unlabeled:
        notes.append(f"{unlabeled} of {total} evidence records produced no signals and are not in any tally.")
    kinds = {r["source_type"] for r in evidence.values()}
    if len(kinds) == 1:
        notes.append(f"All evidence comes from one source type ({next(iter(kinds))}); results reflect that source only.")
    unknown = sum(1 for t in trend_list if t["direction"] == "unknown")
    if unknown:
        notes.append(f"{unknown} of {len(trend_list)} topics have too little dated data to classify a trend.")
    off = [c["competitor"] for c in competitor_block["competitors"] if c["off_topic"]]
    if off:
        notes.append(f"Off-topic competitors ({', '.join(off)}): fewer than {OFF_TOPIC_SHARE:.0%} of their sampled items "
                     "match any topic, so they are left out of topic coverage and blind-spot claims.")
    if any(c["sampled_from_latest"] for c in competitor_block["competitors"]):
        notes.append("Competitor items come from each channel's latest uploads only (a feed holds about 15 videos), "
                     "so absence from a feed does not mean a creator has never covered a topic.")
    basis_sample = sum(1 for t in trend_list if t["basis"] == "sample" and t["direction"] != "unknown")
    if basis_sample:
        notes.append(f"{basis_sample} trend direction(s) rest on counts of collected items, which depend on how many "
                     "items each query returned; volume counts from the sources (scripts/volume.py) are sturdier.")
    thin = [c["competitor"] for c in competitor_block["competitors"] if not c["enough_data"] and not c["off_topic"]]
    if thin:
        notes.append(f"Fewer than {MIN_COMPETITOR_ITEMS} items for: {', '.join(thin)}. Do not generalize about them.")
    notes.append("Counts reflect what the searches returned, not the whole web. Trend directions and outliers use "
                 "fixed heuristic thresholds. Claims have not been independently verified.")
    return notes


# ---------------------------------------------------------------- main


def analyze(evidence, signals, labels, period_days, now, volume=None):
    theme_list = themes(evidence, signals, labels, now)
    trend_list = trends(evidence, signals, period_days, now)
    if volume:
        trend_list = apply_volume(trend_list, volume, period_days / 2)
    competitor_block = competitors(evidence, signals, now, theme_list)
    return {
        "meta": {
            "now": now.strftime(ISO_FORMAT),
            "period_days": period_days,
            "evidence": len(evidence),
            "signals": len(signals),
            "topics_defined": len(labels),
            "topics_without_signals": sorted(set(labels) - {t["topic"] for t in theme_list}),
            "volume_trends": bool(volume),
            "thresholds": {"min_dated": MIN_DATED, "growth_ratio": GROWTH_RATIO, "min_delta": MIN_DELTA,
                           "volume_min": VOLUME_MIN, "volume_ratio": VOLUME_RATIO,
                           "outlier_factor": OUTLIER_FACTOR, "min_competitor_items": MIN_COMPETITOR_ITEMS},
        },
        "themes": theme_list,
        "trends": trend_list,
        "engagement": engagement(evidence, now),
        "competitors": competitor_block,
        "limits": limits(evidence, signals, trend_list, competitor_block),
    }


def main(argv=None, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("evidence")
    parser.add_argument("signals", help="validated signals from scripts/signals.py")
    parser.add_argument("topics")
    parser.add_argument("--period", default="90d", choices=sorted(PERIODS), help="trend window (default 90d)")
    parser.add_argument("--now", metavar="ISO8601", help="end of the window; default is the latest retrieved_at")
    parser.add_argument("--volume", metavar="volume.json", help="source-reported counts from scripts/volume.py, for sturdier trends")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        evidence = load_evidence(args.evidence)
        _, labels = load_topics(args.topics)
        signals = [json.loads(line) for _, line in read_jsonl(args.signals)]
        volume = None
        if args.volume:
            with open(args.volume, encoding="utf-8") as handle:
                volume = json.load(handle)
            if "topics" not in volume or "meta" not in volume:
                raise ConfigError(f"{args.volume} is not a volume.json from scripts/volume.py")
    except OSError as error:
        print(f"analyze: cannot read {error.filename}: {error.strerror}", file=err)
        return 2
    except ConfigError as error:
        print(f"analyze: {error}", file=err)
        return 2
    except json.JSONDecodeError as error:
        print(f"analyze: signals file is not valid JSON Lines: {error.msg}", file=err)
        return 2
    unknown = {s["evidence_id"] for s in signals} - set(evidence)
    if unknown:
        print(f"analyze: signals refer to evidence not in {args.evidence}; run scripts/signals.py first", file=err)
        return 2
    if not evidence:
        print("analyze: the evidence file is empty", file=err)
        return 2
    now = parse_time(args.now) if args.now else max(parse_time(r["retrieved_at"]) for r in evidence.values())
    result = analyze(evidence, signals, labels, PERIODS[args.period], now, volume)
    json.dump(result, out, indent=2, ensure_ascii=False)
    out.write("\n")
    print(f"analyze: {len(result['themes'])} themes, {len(result['trends'])} trends, "
          f"{len(result['competitors']['competitors'])} competitors from {len(evidence)} evidence records", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
