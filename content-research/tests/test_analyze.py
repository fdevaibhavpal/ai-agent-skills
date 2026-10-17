import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import NOW, TOPICS, ev, labels, sig, world, write_jsonl
import analyze as an
from schema_check import load_schema, validate

NOW_DT = an.parse_time(NOW)
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

    def test_creators_ignore_records_that_name_no_one(self):
        evidence, signals = world()
        extra = [ev(60 + i, "youtube", "2026-10-01T00:00:00Z") for i in range(3)]       # search results: no channel named
        extra += [ev(70, "web", "2026-10-01T00:00:00Z"), ev(71, "web", "2026-10-02T00:00:00Z")]  # same site twice
        for record in extra:
            evidence[record["evidence_id"]] = record
            signals.append(sig(int(record["evidence_id"][2:], 16), "coverage", "rsc", format="tutorial"))
        theme = {t["topic"]: t for t in an.analyze(evidence, signals, labels(), 90, NOW_DT)["themes"]}["rsc"]
        self.assertEqual((theme["supply"]["evidence"], theme["supply"]["creators"]), (5, 1))

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
        self.assertIn("too little dated data", text)
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


class OffTopicCompetitorTests(unittest.TestCase):
    """Found live: two big channels whose recent uploads had nothing to do with the topic."""

    def build(self, with_on_topic=True):
        evidence, signals = world()
        if not with_on_topic:
            evidence = {k: v for k, v in evidence.items() if not v["competitor"]}
            signals = [s for s in signals if s["evidence_id"] in evidence]
        for n in range(30, 36):
            record = ev(n, "youtube", f"2026-10-{n - 20:02d}T00:00:00Z", author="OffChan", competitor="OffChan",
                        metrics={"views": 100000}, queries=["channel feed UCxxxxxxxxxxxxxxxxxxxxxx"])
            evidence[record["evidence_id"]] = record
        return an.analyze(evidence, signals, labels(), 90, NOW_DT)

    def test_off_topic_competitor_is_flagged_and_excluded_from_coverage(self):
        block = self.build()["competitors"]
        by_name = {c["competitor"]: c for c in block["competitors"]}
        self.assertTrue(by_name["OffChan"]["off_topic"])
        self.assertEqual(by_name["OffChan"]["topical_share"], 0.0)
        self.assertFalse(by_name["ChanA"]["off_topic"])
        self.assertEqual(block["on_topic"], 1)
        self.assertEqual(block["topic_coverage"], {"testing": {"competitors": 1, "items": 4},
                                                   "profiling": {"competitors": 1, "items": 1}})
        self.assertEqual(block["demand_topics_no_competitor_coverage"], ["react-memo", "memory-leaks", "rsc"])

    def test_only_off_topic_competitors_means_no_blind_spot_claims(self):
        result = self.build(with_on_topic=False)
        self.assertEqual(result["competitors"]["on_topic"], 0)
        self.assertEqual(result["competitors"]["demand_topics_no_competitor_coverage"], [])
        import score as sc
        scored = sc.score_analysis(result, sc.load_config(), "advanced")
        self.assertTrue(all(o["competitor_blind_spot"] is None for o in scored["opportunities"]))

    def test_limits_explain_the_exclusion_and_the_feed_sample(self):
        text = " ".join(self.build()["limits"])
        self.assertIn("Off-topic competitors (OffChan)", text)
        self.assertIn("latest uploads only", text)
        self.assertNotIn("Fewer than 10 items for: ChanA, OffChan", text)   # off-topic ones are not listed as thin


class VolumeTrendTests(unittest.TestCase):
    def test_classify_volume(self):
        self.assertEqual(an.classify_volume(10, 5, 0, 0)[0], "unknown")            # under VOLUME_MIN
        self.assertEqual(an.classify_volume(30, 0, 0, 0)[0], "emerging")
        self.assertEqual(an.classify_volume(60, 30, 0, 0)[0], "growing")           # no baseline: raw ratio 2.0
        self.assertEqual(an.classify_volume(30, 60, 0, 0)[0], "declining")
        self.assertEqual(an.classify_volume(40, 36, 0, 0)[0], "stable")

    def test_a_platform_wide_slump_is_not_a_topic_decline(self):
        # topic items fell 100 -> 60, but the whole platform fell 1000 -> 400: the topic's share rose
        direction, why = an.classify_volume(60, 100, 400, 1000)
        self.assertEqual(direction, "growing")
        self.assertIn("share rose", why)

    def volume(self, **per_topic):
        return {"meta": {"baseline": {"hackernews": {"recent": 200, "prior": 200}}},
                "topics": {t: {"query": t, "sources": {"hackernews": c}} for t, c in per_topic.items()}}

    def test_apply_volume_overrides_direction_and_keeps_sample_fields(self):
        evidence, signals = world()
        base = an.analyze(evidence, signals, labels(), 90, NOW_DT)
        with_volume = an.analyze(evidence, signals, labels(), 90, NOW_DT,
                                 self.volume(rsc={"recent": 50, "prior": 20}, profiling={"recent": 3, "prior": 2}))
        before = {t["topic"]: t for t in base["trends"]}
        after = {t["topic"]: t for t in with_volume["trends"]}
        self.assertEqual(before["rsc"]["direction"], "unknown")
        self.assertEqual(after["rsc"]["direction"], "growing")
        self.assertEqual(after["rsc"]["basis"], "volume")
        self.assertIn("50 items in the recent 45 days vs 20 in the prior 45 days", after["rsc"]["reason"])
        self.assertEqual(an._items(1), "1 item")
        self.assertTrue(after["rsc"]["volume"]["baseline"])
        self.assertEqual(after["profiling"]["direction"], "unknown")               # 5 items: too few to say
        self.assertEqual(after["react-memo"]["basis"], "sample")                   # not in the volume file
        self.assertEqual(after["rsc"]["recent"], before["rsc"]["recent"])         # sample counts stay for recency
        self.assertTrue(with_volume["meta"]["volume_trends"])
        self.assertEqual(an.sort_trends(list(with_volume["trends"]))[0]["direction"], "growing")


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

    def test_volume_file_is_used_and_checked(self):
        volume = {"meta": {"baseline": {}}, "topics": {"rsc": {"query": "rsc", "sources": {"hackernews": {"recent": 60, "prior": 20}}}}}
        evidence, signals = world()
        with tempfile.TemporaryDirectory() as tmp:
            paths = [os.path.join(tmp, n) for n in ("e.jsonl", "s.jsonl", "t.json", "v.json")]
            write_jsonl(paths[0], list(evidence.values()))
            write_jsonl(paths[1], signals)
            with open(paths[2], "w") as f:
                json.dump(TOPICS, f)
            with open(paths[3], "w") as f:
                json.dump(volume, f)
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(an.main([*paths[:3], "--volume", paths[3]], out=out, err=err), 0)
            trend = {t["topic"]: t for t in json.loads(out.getvalue())["trends"]}["rsc"]
            self.assertEqual((trend["direction"], trend["basis"]), ("growing", "volume"))
            with open(paths[3], "w") as f:
                json.dump({"nope": 1}, f)
            err = io.StringIO()
            self.assertEqual(an.main([*paths[:3], "--volume", paths[3]], out=io.StringIO(), err=err), 2)
            self.assertIn("not a volume.json", err.getvalue())
            self.assertEqual(an.main([*paths[:3], "--volume", "/nonexistent.json"], out=io.StringIO(), err=io.StringIO()), 2)

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
