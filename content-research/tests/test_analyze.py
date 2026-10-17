import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import NOW, ev, sig, write_jsonl
import analyze as an
from schema_check import load_schema, validate

NOW_DT = an.parse_time(NOW)
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


class ClassifyTests(unittest.TestCase):
    def test_directions(self):
        self.assertEqual(an.classify(4, 0, 0, 4)[0], "emerging")
        self.assertEqual(an.classify(4, 0, 2, 4)[0], "growing")     # existed before the period
        self.assertEqual(an.classify(6, 2, 0, 8)[0], "growing")
        self.assertEqual(an.classify(1, 4, 1, 5)[0], "declining")
        self.assertEqual(an.classify(2, 2, 0, 4)[0], "stable")
        self.assertEqual(an.classify(3, 2, 0, 5)[0], "stable")      # ratio met, difference under 2
        self.assertEqual(an.classify(2, 1, 0, 3)[0], "unknown")     # too few dated records

    def test_reason_states_the_counts(self):
        self.assertIn("1 dated records in the recent half", an.classify(1, 4, 0, 5)[1])


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.evidence, self.signals = world()
        self.result = an.analyze(self.evidence, self.signals, labels(), 90, NOW_DT)
        self.theme = {t["topic"]: t for t in self.result["themes"]}
        self.trend = {t["topic"]: t for t in self.result["trends"]}

    def test_helper_records_match_the_schema(self):
        schema = load_schema("evidence.json")
        for record in self.evidence.values():
            self.assertEqual(validate(record, schema), [], record["evidence_id"])

    def test_theme_order_and_exclusions(self):
        self.assertEqual([t["topic"] for t in self.result["themes"]],
                         ["react-memo", "profiling", "memory-leaks", "rsc", "testing"])
        self.assertEqual(self.result["meta"]["topics_without_signals"], ["unused-topic"])

    def test_demand_tallies(self):
        demand = self.theme["profiling"]["demand"]
        self.assertEqual((demand["signals"], demand["evidence"]), (4, 4))
        self.assertEqual(demand["by_type"], {"pain_point": 2, "question": 2})
        self.assertEqual(demand["by_level"], {"advanced": 3, "intermediate": 1})
        self.assertEqual(demand["metrics_total"], {"score": 50, "comments": 12})
        self.assertEqual(demand["evidence_with_metrics"], 2)
        self.assertEqual(demand["top_statements"][0], "Hard to find unnecessary renders")  # first-seen casing
        memo = self.theme["react-memo"]["demand"]
        self.assertEqual(memo["source_types"], {"reddit": 4, "github": 1})
        self.assertEqual(memo["domains"], 2)

    def test_supply_tallies(self):
        supply = self.theme["react-memo"]["supply"]
        self.assertEqual((supply["signals"], supply["creators"]), (1, 1))
        self.assertEqual(supply["by_format"], {"explainer": 1})
        self.assertEqual(supply["by_level"], {"beginner": 1})
        testing = self.theme["testing"]
        self.assertEqual(testing["demand"]["evidence"], 0)
        self.assertEqual(testing["supply"]["by_format"], {"tutorial": 3, "case-study": 1})
        self.assertEqual(testing["supply"]["median_views_per_day"], 100.0)

    def test_dated_counts(self):
        self.assertEqual((self.theme["rsc"]["dated_evidence"], self.theme["rsc"]["undated_evidence"]), (2, 1))

    def test_trend_directions(self):
        self.assertEqual({k: v["direction"] for k, v in self.trend.items()},
                         {"profiling": "emerging", "react-memo": "declining", "memory-leaks": "stable",
                          "rsc": "unknown", "testing": "stable"})
        memo = self.trend["react-memo"]
        self.assertEqual((memo["recent"], memo["prior"], memo["outside_period"]), (1, 4, 1))
        self.assertEqual((memo["demand_recent"], memo["demand_prior"]), (1, 4))
        self.assertEqual(self.trend["rsc"]["undated"], 1)

    def test_trend_order(self):
        self.assertEqual([t["topic"] for t in self.result["trends"]],
                         ["profiling", "memory-leaks", "testing", "react-memo", "rsc"])  # ties on recent sort by name

    def test_boundaries_belong_to_the_older_half(self):
        # video 23 is published exactly at the half-way point, so it counts as prior
        testing = self.trend["testing"]
        self.assertEqual((testing["recent"], testing["prior"]), (2, 2))

    def test_engagement(self):
        engagement = self.result["engagement"]
        top = engagement["top_by_views_per_day"]
        self.assertEqual(top[0]["evidence_id"], "e-00000014")
        self.assertEqual((top[0]["views_per_day"], top[0]["age_days"], top[0]["like_rate"]), (1000.0, 5.5, 0.1))
        self.assertFalse(top[0]["low_confidence"])
        young = next(i for i in top if i["evidence_id"] == "e-0000001a")
        self.assertTrue(young["low_confidence"])
        self.assertEqual(young["views_per_day"], 50.0)
        self.assertEqual(engagement["by_source"], {"youtube": {"items": 7, "median_views_per_day": 100.0,
                                                               "max_views_per_day": 1000.0}})
        # reddit items have scores but no views, so they never get a views/day figure
        self.assertNotIn("reddit", engagement["by_source"])

    def test_competitors(self):
        block = self.result["competitors"]
        (chan,) = block["competitors"]
        self.assertEqual((chan["competitor"], chan["items"], chan["dated_items"]), ("ChanA", 6, 6))
        # 6 dated videos over the 84.5 days between the first and last publish dates
        self.assertEqual(chan["items_per_30d"], 2.1)
        self.assertFalse(chan["enough_data"])
        self.assertEqual(chan["topics"], {"testing": 4, "profiling": 1})
        self.assertEqual(chan["formats"], {"tutorial": 3, "explainer": 1, "case-study": 1})
        self.assertEqual(chan["median_views_per_day"], 100.0)
        self.assertEqual([o["evidence_id"] for o in chan["outliers"]], ["e-00000014"])
        self.assertEqual(chan["items_without_signals"], 1)
        self.assertEqual(block["topic_coverage"], {"testing": {"competitors": 1, "items": 4},
                                                   "profiling": {"competitors": 1, "items": 1}})
        self.assertEqual(block["demand_topics_no_competitor_coverage"], ["react-memo", "memory-leaks", "rsc"])

    def test_limits_mention_what_applies(self):
        text = " ".join(self.result["limits"])
        self.assertIn("2 of 24 evidence records produced no signals", text)
        self.assertIn("Fewer than 10 items for: ChanA", text)
        self.assertIn("too few dated records", text)
        self.assertIn("not been independently verified", text)
        self.assertNotIn("no publication date", text)  # only 1 of 24 is undated

    def test_undated_majority_is_flagged(self):
        evidence = {r["evidence_id"]: r for r in [ev(1), ev(2), ev(3, published="2026-10-01T00:00:00Z")]}
        signals = [sig(1, "question", "rsc"), sig(2, "question", "rsc")]
        result = an.analyze(evidence, signals, labels(), 90, NOW_DT)
        self.assertTrue(any("no publication date" in n for n in result["limits"]))
        self.assertTrue(any("one source type (reddit)" in n for n in result["limits"]))

    def test_empty_inputs_do_not_crash(self):
        result = an.analyze({}, [], labels(), 90, NOW_DT)
        self.assertEqual(result["themes"], [])
        self.assertEqual(result["limits"], ["There is no evidence."])

    def test_result_is_json_serializable_and_deterministic(self):
        first = json.dumps(self.result, sort_keys=True)
        again = an.analyze(*world(), labels(), 90, NOW_DT)
        self.assertEqual(first, json.dumps(again, sort_keys=True))


class CliTests(unittest.TestCase):
    def run_cli(self, mutate=None, extra=()):
        evidence, signals = world()
        records = list(evidence.values())
        if mutate:
            records, signals = mutate(records, signals)
        with tempfile.TemporaryDirectory() as tmp:
            paths = [os.path.join(tmp, n) for n in ("e.jsonl", "s.jsonl", "t.json")]
            write_jsonl(paths[0], records)
            write_jsonl(paths[1], signals)
            with open(paths[2], "w") as f:
                json.dump(TOPICS, f)
            out, err = io.StringIO(), io.StringIO()
            code = an.main([*paths, *extra], out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_end_to_end(self):
        code, out, err = self.run_cli()
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["meta"]["now"], NOW)  # defaults to the latest retrieved_at
        self.assertEqual(data["meta"]["period_days"], 90)
        self.assertIn("5 themes, 5 trends, 1 competitors from 24 evidence records", err)

    def test_period_changes_the_window(self):
        data = json.loads(self.run_cli(extra=["--period", "7d"])[1])
        self.assertEqual(data["meta"]["period_days"], 7)
        self.assertTrue(all(t["direction"] == "unknown" for t in data["trends"]))

    def test_signals_for_unknown_evidence_fail(self):
        code, out, err = self.run_cli(lambda r, s: (r, s + [sig(999, "question", "rsc")]))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("run scripts/signals.py first", err)

    def test_empty_evidence_fails(self):
        code, out, err = self.run_cli(lambda r, s: ([], []))
        self.assertEqual(code, 2)
        self.assertIn("empty", err)


if __name__ == "__main__":
    unittest.main()
