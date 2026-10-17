import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import NOW, labels, world
import analyze as an
import score as sc


def analysis_for(*, evidence_signals=None):
    evidence, signals = evidence_signals or world()
    return an.analyze(evidence, signals, labels(), 90, an.parse_time(NOW))


def scored(analysis=None, config=None, level="advanced"):
    result = sc.score_analysis(analysis or analysis_for(), config or sc.load_config(), level)
    return result, {o["topic"]: o for o in result["opportunities"]}


class ConfigTests(unittest.TestCase):
    def load(self, mutate):
        config = sc.load_config()
        mutate(config)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "scoring.json")
            with open(path, "w") as f:
                json.dump(config, f)
            return sc.load_config(path)

    def test_defaults_load_and_weights_are_sane(self):
        config = sc.load_config()
        self.assertEqual(sorted(config["weights"]), sorted(sc.COMPONENTS))
        self.assertAlmostEqual(sum(config["weights"].values()), 1.0)

    def test_bad_configs_are_rejected_with_a_reason(self):
        cases = [
            (lambda c: c["weights"].pop("demand"), "missing required field 'demand'"),
            (lambda c: c["weights"].update({k: 0 for k in c["weights"]}), "at least one weight"),
            (lambda c: c["tiers"].reverse(), "tiers must run from high to low"),
            (lambda c: c.update(low_confidence_tier_cap="nope"), "not one of the tier names"),
            (lambda c: c["level_credit"].update(match=2), "above 1"),
            (lambda c: c.update(surprise=1), "unexpected field"),
        ]
        for mutate, message in cases:
            with self.assertRaisesRegex(sc.ConfigError, message):
                self.load(mutate)

    def test_missing_file(self):
        with self.assertRaisesRegex(sc.ConfigError, "cannot read"):
            sc.load_config("/nonexistent/scoring.json")


class HelperTests(unittest.TestCase):
    credits = {"match": 1.0, "unknown": 0.5, "adjacent": 0.25, "distant": 0.0}

    def test_level_credit(self):
        credit = lambda level, target: sc.level_credit(level, target, self.credits)  # noqa: E731
        self.assertEqual(credit("advanced", "advanced"), 1.0)
        self.assertEqual(credit("intermediate", "advanced"), 0.25)
        self.assertEqual(credit("beginner", "advanced"), 0.0)
        self.assertEqual(credit("unknown", "advanced"), 0.5)
        self.assertEqual(credit("beginner", None), 1.0)  # no target level: everything counts fully

    def test_relative(self):
        self.assertEqual(sc.relative({"a": 2, "b": 4, "c": None}), {"a": 50.0, "b": 100.0, "c": None})
        self.assertEqual(sc.relative({"a": 0, "b": 0}), {"a": 0.0, "b": 0.0})
        self.assertEqual(sc.relative({"a": 5, "b": None}, min_points=2), {"a": None, "b": None})
        self.assertEqual(sc.relative({}), {})


class ScoreTests(unittest.TestCase):
    """Expected values were worked out by hand from the dataset in helpers.world()."""

    def setUp(self):
        self.result, self.by_topic = scored()

    def test_ranking_scores_and_tiers(self):
        order = [(o["rank"], o["topic"], o["score"], o["tier"], o["confidence"]) for o in self.result["opportunities"]]
        self.assertEqual(order, [(1, "profiling", 77.7, "interesting", "low"),
                                 (2, "memory-leaks", 67.6, "marginal", "low"),
                                 (3, "react-memo", 67.3, "marginal", "medium"),
                                 (4, "rsc", 52.5, "ignore", "low")])

    def test_components(self):
        values = lambda topic: {k: v["value"] for k, v in self.by_topic[topic]["components"].items()}  # noqa: E731
        self.assertEqual(values("react-memo"), {"demand": 100.0, "growth": 15, "content_gap": 100.0,
                                                "engagement": None, "recency": 16.7, "audience_fit": 50.0})
        profiling = values("profiling")
        self.assertEqual((profiling["demand"], profiling["growth"], profiling["content_gap"], profiling["recency"]),
                         (64.0, 100, 64.0, 100.0))
        self.assertAlmostEqual(profiling["audience_fit"], 81.25, delta=0.06)
        self.assertEqual(values("rsc")["growth"], None)   # trend unknown: left out, not zero
        self.assertEqual(values("rsc")["recency"], None)

    def test_level_aware_gap(self):
        # beginner-only content does not serve an advanced audience, so react-memo has no effective supply
        self.assertEqual(self.by_topic["react-memo"]["supply"], {"evidence": 1, "effective": 0.0, "creators": 1})
        self.assertEqual(self.by_topic["profiling"]["supply"]["effective"], 0.25)  # intermediate is adjacent

    def test_missing_components_renormalize_weights(self):
        self.assertEqual(self.by_topic["react-memo"]["coverage"], 0.85)   # engagement is unavailable
        self.assertEqual(self.by_topic["rsc"]["coverage"], 0.55)
        # profiling: (0.3*64 + 0.2*100 + 0.2*64 + 0.1*100 + 0.05*81.25) / 0.85
        self.assertAlmostEqual(self.by_topic["profiling"]["score"], 77.72, delta=0.06)

    def test_engagement_needs_two_comparable_topics(self):
        # only one candidate topic has views/day or discussion numbers, so nothing is scaled against itself
        self.assertTrue(all(o["components"]["engagement"]["value"] is None for o in self.by_topic.values()))

    def test_unscored_and_warnings(self):
        self.assertEqual(self.result["unscored"], [{"topic": "testing", "reason": "0 demand evidence records (needs 3)"}])
        self.assertEqual(len(self.result["warnings"]), 1)
        self.assertIn("within this run only", self.result["warnings"][0])

    def test_competitor_blind_spots_and_notes(self):
        self.assertFalse(self.by_topic["profiling"]["competitor_blind_spot"])
        self.assertTrue(self.by_topic["react-memo"]["competitor_blind_spot"])
        self.assertTrue(any("1 competitor(s) cover this topic" in n for n in self.by_topic["profiling"]["notes"]))
        self.assertTrue(any("Trend direction is unknown" in n for n in self.by_topic["rsc"]["notes"]))
        self.assertTrue(any("No existing content" in n for n in self.by_topic["memory-leaks"]["notes"]))
        self.assertTrue(any("Left out of the score: engagement" in n for n in self.by_topic["react-memo"]["notes"]))

    def test_output_matches_schema_and_is_deterministic(self):
        self.assertEqual(sc.check_output(self.result), [])
        again, _ = scored()
        self.assertEqual(json.dumps(self.result, sort_keys=True), json.dumps(again, sort_keys=True))

    def test_evidence_ids_are_carried_through(self):
        self.assertEqual(len(self.by_topic["profiling"]["evidence_ids"]["demand"]), 4)
        self.assertEqual(self.by_topic["profiling"]["top_statements"][0], "Hard to find unnecessary renders")


class VariationTests(unittest.TestCase):
    def test_without_audience_level(self):
        result, by_topic = scored(level=None)
        self.assertIsNone(by_topic["profiling"]["components"]["audience_fit"]["value"])
        # every piece of content counts fully: demand/(supply+1)
        self.assertEqual(by_topic["memory-leaks"]["components"]["content_gap"]["value"], 100.0)
        self.assertEqual(by_topic["react-memo"]["components"]["content_gap"]["value"], 62.5)
        self.assertTrue(any("No audience level" in w for w in result["warnings"]))

    def test_invalid_audience_level(self):
        with self.assertRaises(sc.ConfigError):
            sc.score_analysis(analysis_for(), sc.load_config(), "expert")

    def test_thin_supply_leaves_out_the_content_gap(self):
        evidence, signals = world()
        signals = [s for s in signals if s["type"] != "coverage"]
        result, by_topic = scored(analysis_for(evidence_signals=(evidence, signals)))
        self.assertTrue(all(o["components"]["content_gap"]["value"] is None for o in by_topic.values()))
        self.assertTrue(any("could not be measured" in w for w in result["warnings"]))
        self.assertFalse(any("No existing content" in n for o in by_topic.values() for n in o["notes"]))

    def test_single_candidate_is_low_confidence(self):
        analysis = analysis_for()
        analysis["themes"] = [t for t in analysis["themes"] if t["topic"] in ("profiling", "testing")]
        result, by_topic = scored(analysis)
        self.assertEqual(by_topic["profiling"]["confidence"], "low")
        self.assertTrue(any("Only one topic" in w for w in result["warnings"]))

    def test_no_candidates(self):
        analysis = analysis_for()
        analysis["themes"] = [t for t in analysis["themes"] if t["topic"] == "testing"]
        result, _ = scored(analysis)
        self.assertEqual(result["opportunities"], [])
        self.assertTrue(any("No topic had enough demand" in w for w in result["warnings"]))

    def test_low_confidence_caps_the_tier(self):
        config = sc.load_config()
        config["tiers"] = [{"name": n, "min": m} for n, m in
                           (("exceptional", 50), ("strong", 40), ("interesting", 30), ("marginal", 20), ("ignore", 0))]
        _, by_topic = scored(config=config)
        self.assertEqual(by_topic["react-memo"]["tier"], "exceptional")   # medium confidence keeps it
        self.assertEqual(by_topic["profiling"]["tier"], "interesting")    # low confidence is capped

    def test_low_coverage_is_unrated_and_sorted_last(self):
        config = sc.load_config()
        config["min_coverage"] = 0.6
        result, by_topic = scored(config=config)
        self.assertEqual(by_topic["rsc"]["tier"], "unrated")
        self.assertEqual(result["opportunities"][-1]["topic"], "rsc")
        self.assertNotEqual(by_topic["profiling"]["tier"], "unrated")

    def test_gap_details_need_enough_supply(self):
        analysis = analysis_for()
        theme = next(t for t in analysis["themes"] if t["topic"] == "profiling")
        theme["supply"].update(signals=4, evidence=4, by_level={"beginner": 3, "intermediate": 1},
                               by_format={"tutorial": 4})
        _, by_topic = scored(analysis)
        details = by_topic["profiling"]["gap_details"]
        self.assertEqual(details["supply_pieces"], 4)
        self.assertEqual(details["levels_missing"], ["advanced"])
        self.assertEqual(details["formats_missing"], ["explainer", "case-study", "talk", "reference"])
        self.assertEqual(details["target_level_share"], 0.0)
        thin = by_topic["react-memo"]["gap_details"]
        self.assertEqual((thin["levels_missing"], thin["formats_missing"]), (None, None))

    def test_no_competitor_analysis_means_no_blind_spot_claims(self):
        analysis = analysis_for()
        analysis["competitors"] = {"competitors": [], "topic_coverage": {}, "demand_topics_no_competitor_coverage": []}
        _, by_topic = scored(analysis)
        self.assertTrue(all(o["competitor_blind_spot"] is None for o in by_topic.values()))


class CliTests(unittest.TestCase):
    def run_cli(self, argv, analysis=None, raw_text=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "analysis.json")
            with open(path, "w") as f:
                f.write(raw_text if raw_text is not None else json.dumps(analysis or analysis_for()))
            out, err = io.StringIO(), io.StringIO()
            code = sc.main([path, *argv], out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_end_to_end(self):
        code, out, err = self.run_cli(["--audience-level", "advanced"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["meta"]["audience_level"], "advanced")
        self.assertEqual(data["opportunities"][0]["topic"], "profiling")
        self.assertIn("4 topics scored, 1 unscored", err)
        self.assertIn("1. Profiling: 77.7 (interesting, low confidence)", err)

    def test_bad_inputs(self):
        self.assertEqual(self.run_cli([], raw_text="{nope")[0], 2)
        code, _, err = self.run_cli([], raw_text='{"hello": 1}')
        self.assertEqual(code, 2)
        self.assertIn("not an analysis.json", err)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_cli(["--audience-level", "expert"])

    def test_missing_analysis_file(self):
        err = io.StringIO()
        code = sc.main(["/nonexistent/analysis.json"], out=io.StringIO(), err=err)
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err.getvalue())


if __name__ == "__main__":
    unittest.main()
