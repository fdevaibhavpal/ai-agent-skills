#!/usr/bin/env python3
"""Rank topics by content opportunity: audience demand against existing content.

    python3 scripts/score.py analysis.json --audience-level advanced > opportunities.json

Reads the output of scripts/analyze.py. The score is a weighted mean of six components
(weights and thresholds in config/scoring.json). A component the data cannot support is
left out and the remaining weights are renormalized, so a missing signal never counts as
zero or as a guess. Scores rank topics within this run only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema_check import load_schema, validate  # noqa: E402

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "scoring.json")
COMPONENTS = ("demand", "growth", "content_gap", "engagement", "recency", "audience_fit")
LEVELS = ("beginner", "intermediate", "advanced")
FORMATS = ("tutorial", "explainer", "case-study", "talk", "reference")
MIN_PIECES_FOR_DETAILS = 3   # fewer pieces of supply: do not claim a level or format is missing
MIN_POINTS = 2               # a relative score needs at least this many topics with data


class ConfigError(Exception):
    """The configuration or input is unusable. The message is safe to show."""


def load_config(path=None):
    path = path or CONFIG_PATH
    try:
        with open(path, encoding="utf-8") as handle:
            config = json.load(handle)
    except OSError as err:
        raise ConfigError(f"cannot read {path}: {err.strerror}")
    except json.JSONDecodeError as err:
        raise ConfigError(f"{path} is not valid JSON: {err.msg}")
    errors = validate(config, load_schema("scoring.json"))
    if errors:
        raise ConfigError(f"{path}: " + "; ".join(errors))
    if sum(config["weights"].values()) <= 0:
        raise ConfigError(f"{path}: at least one weight must be above zero")
    tiers = config["tiers"]
    if not tiers or tiers[-1]["min"] != 0 or any(a["min"] <= b["min"] for a, b in zip(tiers, tiers[1:])):
        raise ConfigError(f"{path}: tiers must run from high to low and end at min 0")
    if config["low_confidence_tier_cap"] not in [t["name"] for t in tiers]:
        raise ConfigError(f"{path}: low_confidence_tier_cap is not one of the tier names")
    return config


# ---------------------------------------------------------------- helpers


def level_credit(level, target, credits):
    """How much a piece at `level` counts as serving an audience at `target`."""
    if target is None:
        return 1.0
    if level == "unknown":
        return credits["unknown"]
    if level == target:
        return credits["match"]
    if abs(LEVELS.index(level) - LEVELS.index(target)) == 1:
        return credits["adjacent"]
    return credits["distant"]


def relative(raw, min_points=1):
    """Scale raw values to 0-100 against the largest. None stays None."""
    present = [v for v in raw.values() if v is not None]
    if len(present) < min_points:
        return {k: None for k in raw}
    top = max(present)
    return {k: None if v is None else (v / top * 100 if top > 0 else 0.0) for k, v in raw.items()}


def mean(values):
    return sum(values) / len(values) if values else None


def round_or_none(value, places=1):
    return None if value is None else round(value, places)


def effective_supply(theme, target, credits):
    return sum(count * level_credit(level, target, credits) for level, count in theme["supply"]["by_level"].items())


def gap_details(theme, target):
    supply = theme["supply"]
    pieces = supply["signals"]
    if pieces < MIN_PIECES_FOR_DETAILS:
        return {"supply_pieces": pieces, "levels_missing": None, "formats_missing": None, "target_level_share": None}
    by_level, by_format = supply["by_level"], supply["by_format"]
    share = None
    if target:
        share = round(by_level.get(target, 0) / pieces, 2)
    return {
        "supply_pieces": pieces,
        "levels_missing": [lv for lv in LEVELS if by_level.get(lv, 0) == 0],
        "formats_missing": [f for f in FORMATS if by_format.get(f, 0) == 0],
        "target_level_share": share,
    }


# ---------------------------------------------------------------- components


def component_values(candidates, trends, config, target, supply_total, min_dated):
    """Return ({component: {topic: value or None}}, {component: {topic: basis text}})."""
    values = {name: {} for name in COMPONENTS}
    basis = {name: {} for name in COMPONENTS}
    bonus = config["source_diversity_bonus"]

    demand_raw = {t["topic"]: t["demand"]["evidence"] * (1 + bonus * (len(t["demand"]["source_types"]) - 1))
                  for t in candidates}
    for topic, value in relative(demand_raw).items():
        values["demand"][topic] = value
    for t in candidates:
        d = t["demand"]
        basis["demand"][t["topic"]] = (f"{d['evidence']} evidence records from {len(d['source_types'])} "
                                       f"source type(s), scaled to the strongest topic")

    supply_known = supply_total >= config["min_supply_evidence_total"]
    ratio_raw = {}
    for t in candidates:
        effective = effective_supply(t, target, config["level_credit"])
        ratio_raw[t["topic"]] = (t["demand"]["evidence"] / (effective + 1)) if supply_known else None
        basis["content_gap"][t["topic"]] = (
            f"{t['demand']['evidence']} demand records vs {effective:.2f} effective supply"
            if supply_known else "not scored: too little content found to measure supply")
    values["content_gap"] = relative(ratio_raw)

    perf_raw, talk_raw = {}, {}
    for t in candidates:
        perf_raw[t["topic"]] = t["supply"]["median_views_per_day"]
        d = t["demand"]
        has_counts = d["evidence_with_metrics"] > 0 and ("score" in d["metrics_total"] or "comments" in d["metrics_total"])
        talk_raw[t["topic"]] = ((d["metrics_total"].get("score", 0) + d["metrics_total"].get("comments", 0))
                                / d["evidence_with_metrics"]) if has_counts else None
    perf, talk = relative(perf_raw, MIN_POINTS), relative(talk_raw, MIN_POINTS)
    for t in candidates:
        parts = [v for v in (perf[t["topic"]], talk[t["topic"]]) if v is not None]
        values["engagement"][t["topic"]] = mean(parts)
        basis["engagement"][t["topic"]] = (
            f"mean of {len(parts)} measure(s): views per day of existing content, discussion score and comments"
            if parts else "not scored: no comparable engagement numbers")

    by_trend = {t["topic"]: t for t in trends}
    for t in candidates:
        topic = t["topic"]
        trend = by_trend.get(topic, {"direction": "unknown", "reason": "no trend data"})
        values["growth"][topic] = config["growth_scores"].get(trend["direction"])
        basis["growth"][topic] = f"{trend['direction']}: {trend['reason']}"
        dated = trend.get("recent", 0) + trend.get("prior", 0)
        if "recent" in trend and dated >= min_dated:
            total = dated + trend["outside_period"]
            values["recency"][topic] = trend["recent"] / total * 100
            basis["recency"][topic] = f"{trend['recent']} of {total} dated records fall in the recent half of the window"
        else:
            values["recency"][topic] = None
            basis["recency"][topic] = f"not scored: fewer than {min_dated} dated records"

        if target:
            d = t["demand"]
            total_signals = sum(d["by_level"].values())
            fit = (sum(c * level_credit(lv, target, config["level_credit"]) for lv, c in d["by_level"].items())
                   / total_signals * 100) if total_signals else None
            values["audience_fit"][topic] = fit
            basis["audience_fit"][topic] = f"how well the demand signals' levels match a {target} audience"
        else:
            values["audience_fit"][topic] = None
            basis["audience_fit"][topic] = "not scored: no audience level given"
    return values, basis


# ---------------------------------------------------------------- scoring


def confidence_level(theme, coverage, config, single_candidate):
    if single_candidate:
        return "low"
    cfg, d = config["confidence"], theme["demand"]
    for name in ("high", "medium"):
        need = cfg[name]
        if (d["evidence"] >= need["demand_evidence"] and len(d["source_types"]) >= need["source_types"]
                and coverage >= need["coverage"]):
            return name
    return "low"


def tier_for(score, confidence, coverage, config):
    if coverage < config["min_coverage"]:
        return "unrated"
    names = [t["name"] for t in config["tiers"]]
    tier = next(t["name"] for t in config["tiers"] if score >= t["min"])
    if confidence == "low":
        cap = names.index(config["low_confidence_tier_cap"])
        if names.index(tier) < cap:
            tier = names[cap]
    return tier


def score_analysis(analysis, config, target=None):
    if target is not None and target not in LEVELS:
        raise ConfigError(f"audience level must be one of {', '.join(LEVELS)}")
    min_dated = analysis["meta"].get("thresholds", {}).get("min_dated", 4)
    themes, trends = analysis["themes"], analysis["trends"]
    candidates = [t for t in themes if t["demand"]["evidence"] >= config["min_demand_evidence"]]
    unscored = [{"topic": t["topic"], "reason": f"{t['demand']['evidence']} demand evidence records "
                 f"(needs {config['min_demand_evidence']})"} for t in themes if t not in candidates]
    warnings = ["Scores rank topics within this run only; they are not comparable across runs, and the "
                "weights and thresholds are heuristics."]
    supply_total = sum(t["supply"]["evidence"] for t in themes)
    if candidates and supply_total < config["min_supply_evidence_total"]:
        warnings.append(f"Only {supply_total} pieces of existing content were found (need "
                        f"{config['min_supply_evidence_total']}), so the content gap could not be measured and is "
                        "left out of every score. Collect more supply sources (YouTube, web) before relying on gaps.")
    if len(candidates) == 1:
        warnings.append("Only one topic had enough demand evidence, so relative components are not meaningful.")
    if not candidates:
        warnings.append("No topic had enough demand evidence to score.")
        return {"meta": meta(config, target, analysis, 0, len(unscored)), "opportunities": [],
                "unscored": unscored, "warnings": warnings}
    if target is None:
        warnings.append("No audience level was given, so existing content was not weighted by level "
                        "and audience fit was left out.")

    values, basis = component_values(candidates, trends, config, target, supply_total, min_dated)
    weights = config["weights"]
    total_weight = sum(weights.values())
    blind = set(analysis["competitors"]["demand_topics_no_competitor_coverage"])
    has_competitors = bool(analysis["competitors"]["competitors"])
    coverage_by_topic = analysis["competitors"]["topic_coverage"]

    results = []
    for theme in candidates:
        topic = theme["topic"]
        used = {name: values[name][topic] for name in COMPONENTS if values[name][topic] is not None}
        weight_used = sum(weights[name] for name in used)
        score = (sum(weights[name] * v for name, v in used.items()) / weight_used) if weight_used > 0 else 0.0
        coverage = weight_used / total_weight
        confidence = confidence_level(theme, coverage, config, len(candidates) == 1)
        trend = next((t for t in trends if t["topic"] == topic), {"direction": "unknown", "reason": "no trend data"})
        effective = effective_supply(theme, target, config["level_credit"])
        notes = []
        if theme["supply"]["evidence"] == 0 and supply_total >= config["min_supply_evidence_total"]:
            notes.append("No existing content on this topic was found in the collected sources.")
        if trend["direction"] == "unknown":
            notes.append("Trend direction is unknown (too few dated records), so growth was left out.")
        missing = [name for name in COMPONENTS if name not in used]
        if missing:
            notes.append("Left out of the score: " + ", ".join(missing) + ".")
        results.append({
            "topic": topic,
            "label": theme["label"],
            "score": round(score, 1),
            "tier": tier_for(score, confidence, coverage, config),
            "confidence": confidence,
            "coverage": round(coverage, 2),
            "components": {name: {"value": round_or_none(values[name][topic]), "weight": weights[name],
                                  "basis": basis[name][topic]} for name in COMPONENTS},
            "demand": {"evidence": theme["demand"]["evidence"], "signals": theme["demand"]["signals"],
                       "source_types": theme["demand"]["source_types"]},
            "supply": {"evidence": theme["supply"]["evidence"], "effective": round(effective, 2),
                       "creators": theme["supply"]["creators"]},
            "growth": {"direction": trend["direction"], "reason": trend["reason"]},
            "competitor_blind_spot": (topic in blind) if has_competitors else None,
            "gap_details": gap_details(theme, target),
            "top_statements": theme["demand"]["top_statements"],
            "evidence_ids": theme["evidence_ids"],
            "notes": notes,
        })
        if has_competitors and topic in coverage_by_topic:
            results[-1]["notes"].append(f"{coverage_by_topic[topic]['competitors']} competitor(s) cover this topic "
                                        f"({coverage_by_topic[topic]['items']} items).")

    results.sort(key=lambda r: (r["tier"] == "unrated", -r["score"], -r["demand"]["evidence"], r["topic"]))
    for rank, result in enumerate(results, 1):
        result["rank"] = rank
    return {"meta": meta(config, target, analysis, len(results), len(unscored)),
            "opportunities": results, "unscored": unscored, "warnings": warnings}


def meta(config, target, analysis, scored, unscored):
    return {"audience_level": target, "weights": config["weights"], "topics_scored": scored,
            "topics_unscored": unscored, "analysis_now": analysis["meta"]["now"],
            "period_days": analysis["meta"]["period_days"]}


def check_output(result):
    schema = load_schema("opportunity.json")
    problems = []
    for item in result["opportunities"]:
        problems += validate(item, schema, f"$.{item['topic']}")
    return problems


def main(argv=None, out=None, err=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("analysis", help="analysis.json from scripts/analyze.py")
    parser.add_argument("--config", help="scoring config (default: config/scoring.json)")
    parser.add_argument("--audience-level", choices=LEVELS, help="level of the target audience, if it is clear")
    args = parser.parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        config = load_config(args.config)
        with open(args.analysis, encoding="utf-8") as handle:
            analysis = json.load(handle)
        if not all(k in analysis for k in ("meta", "themes", "trends", "competitors")):
            raise ConfigError(f"{args.analysis} is not an analysis.json from scripts/analyze.py")
        result = score_analysis(analysis, config, args.audience_level)
    except OSError as error:
        print(f"score: cannot read {error.filename}: {error.strerror}", file=err)
        return 2
    except json.JSONDecodeError as error:
        print(f"score: {args.analysis} is not valid JSON: {error.msg}", file=err)
        return 2
    except ConfigError as error:
        print(f"score: {error}", file=err)
        return 2
    problems = check_output(result)
    if problems:
        print("score: internal error, output does not match schemas/opportunity.json: " + "; ".join(problems), file=err)
        return 1
    json.dump(result, out, indent=2, ensure_ascii=False)
    out.write("\n")
    lines = [f"score: {result['meta']['topics_scored']} topics scored, {result['meta']['topics_unscored']} unscored"]
    lines += [f"  {o['rank']}. {o['label']}: {o['score']} ({o['tier']}, {o['confidence']} confidence)"
              for o in result["opportunities"][:5]]
    lines += [f"  warning: {w}" for w in result["warnings"][1:]]
    print("\n".join(lines), file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
