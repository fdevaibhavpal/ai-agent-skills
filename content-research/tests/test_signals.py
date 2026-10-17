import io
import json
import os
import tempfile
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import ev, write_jsonl
import signals as sg
from schema_check import load_schema, validate

TOPICS = {"topics": [
    {"topic": "react-memo", "label": "React.memo", "aliases": ["memo", "memoization"]},
    {"topic": "profiling", "label": "Profiling", "aliases": ["react profiler"]},
]}
REDDIT_TEXT = "Our app re-renders constantly and I cannot tell which components are wasting time. Any profiling workflow?"


def make_world():
    evidence = {r["evidence_id"]: r for r in [
        ev(1, "reddit", "2026-10-10T00:00:00Z", text=REDDIT_TEXT, title="Why is my app slow?"),
        ev(2, "youtube", "2026-10-01T00:00:00Z", title="React.memo explained", text="A walkthrough of when memo helps."),
    ]}
    lookup = {}
    for entry in TOPICS["topics"]:
        for name in [entry["topic"], entry["label"], *entry["aliases"]]:
            lookup[name.lower()] = entry["topic"]
    return evidence, lookup


def raw(n=1, **kw):
    base = {"type": "pain_point", "topic": "profiling", "statement": "Cannot tell which components waste time",
            "quote": "I cannot tell which components are wasting time", "evidence_id": f"e-{n:08x}"}
    base.update(kw)
    return base


def check(raw_signal):
    evidence, lookup = make_world()
    return sg.check_signal(raw_signal, evidence, lookup, load_schema("signal.json"))


class TopicTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "topics.json")
            with open(path, "w") as f:
                json.dump(data, f)
            return sg.load_topics(path)

    def test_aliases_labels_and_slugs_resolve_case_insensitively(self):
        lookup, labels = self.load(TOPICS)
        self.assertEqual(sg.resolve_topic("REACT.MEMO", lookup), "react-memo")
        self.assertEqual(sg.resolve_topic("Memoization", lookup), "react-memo")
        self.assertEqual(sg.resolve_topic("react memo", lookup), "react-memo")  # slugified
        self.assertIsNone(sg.resolve_topic("redux", lookup))
        self.assertEqual(labels["profiling"], "Profiling")

    def test_conflicting_alias(self):
        data = {"topics": [{"topic": "a", "label": "A", "aliases": ["x"]}, {"topic": "b", "label": "B", "aliases": ["X"]}]}
        with self.assertRaisesRegex(sg.ConfigError, "belongs to both"):
            self.load(data)

    def test_duplicate_slug_bad_slug_and_empty(self):
        with self.assertRaisesRegex(sg.ConfigError, "defined twice"):
            self.load({"topics": [{"topic": "a", "label": "A"}, {"topic": "a", "label": "Again"}]})
        with self.assertRaises(sg.ConfigError):
            self.load({"topics": [{"topic": "Not A Slug", "label": "x"}]})
        with self.assertRaisesRegex(sg.ConfigError, "at least one"):
            self.load({"topics": []})

    def test_missing_file(self):
        with self.assertRaisesRegex(sg.ConfigError, "cannot read"):
            sg.load_topics("/nonexistent/topics.json")


class QuoteTests(unittest.TestCase):
    evidence = ev(1, text="The   React team says: “don’t memoize everything” — measure first.", title="Memo advice")

    def test_matches_ignoring_case_whitespace_and_curly_quotes(self):
        self.assertTrue(sg.quote_in("DON'T memoize everything", self.evidence))
        self.assertTrue(sg.quote_in("react team says", self.evidence))

    def test_title_counts(self):
        self.assertTrue(sg.quote_in("Memo advice", self.evidence))

    def test_ellipsis_fragments_must_appear_in_order(self):
        self.assertTrue(sg.quote_in("The React team says ... measure first", self.evidence))
        self.assertTrue(sg.quote_in("The React team says … measure first", self.evidence))
        self.assertFalse(sg.quote_in("measure first ... The React team says", self.evidence))

    def test_fabricated_or_too_short(self):
        self.assertFalse(sg.quote_in("memoize nothing at all ever", self.evidence))
        self.assertFalse(sg.quote_in("...", self.evidence))
        self.assertFalse(sg.quote_in("React", self.evidence))  # under 8 characters


class SignalTests(unittest.TestCase):
    def test_valid_signal_is_normalized(self):
        signal, reason = check(raw(topic="React Profiler"))
        self.assertIsNone(reason)
        self.assertEqual(signal["topic"], "profiling")
        self.assertEqual((signal["level"], signal["format"]), ("unknown", None))
        self.assertRegex(signal["signal_id"], r"^s-[0-9a-f]{8}$")
        self.assertEqual(validate(signal, load_schema("signal.json")), [])

    def test_signal_id_is_stable(self):
        self.assertEqual(check(raw())[0]["signal_id"], check(raw())[0]["signal_id"])

    def rejects(self, raw_signal, fragment):
        signal, reason = check(raw_signal)
        self.assertIsNone(signal)
        self.assertIn(fragment, reason)

    def test_rejections(self):
        self.rejects(raw(evidence_id="e-0000ffff"), "not in the evidence set")
        self.rejects(raw(topic="redux"), "unknown topic")
        self.rejects(raw(quote="I definitely never said this"), "quote does not appear")
        self.rejects(raw(type="rant"), "is not one of")
        self.rejects(raw(statement="short"), "too short")
        self.rejects(raw(evidence_id="1"), "does not match")
        self.rejects(raw(extra_field=1), "unexpected field")

    def test_coverage_needs_content_sources(self):
        self.rejects(raw(type="coverage"), "coverage signals need web, youtube or news")
        signal, reason = check(raw(2, type="coverage", topic="memo", quote="when memo helps", format="explainer", level="advanced"))
        self.assertIsNone(reason)
        self.assertEqual((signal["topic"], signal["format"], signal["level"]), ("react-memo", "explainer", "advanced"))

    def test_check_signals_collects_rejections_and_drops_duplicates(self):
        evidence, lookup = make_world()
        lines = [(1, json.dumps(raw())), (2, json.dumps(raw(statement="Same item, same topic, other words"))),
                 (3, json.dumps(raw(topic="redux"))), (4, "{oops")]
        signals, rejected, duplicates, read = sg.check_signals(lines, evidence, lookup)
        self.assertEqual((len(signals), duplicates, read), (1, 1, 4))
        self.assertEqual([n for n, _ in rejected], [3, 4])
        self.assertIn("invalid JSON", rejected[1][1])


class CliTests(unittest.TestCase):
    def run_cli(self, signal_lines, extra=(), topics=TOPICS):
        evidence, _ = make_world()
        with tempfile.TemporaryDirectory() as tmp:
            paths = [os.path.join(tmp, n) for n in ("evidence.jsonl", "topics.json", "signals.jsonl")]
            write_jsonl(paths[0], list(evidence.values()))
            with open(paths[1], "w") as f:
                json.dump(topics, f)
            write_jsonl(paths[2], signal_lines)
            out, err = io.StringIO(), io.StringIO()
            code = sg.main([*paths, *extra], out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_writes_valid_signals_and_summary(self):
        code, out, err = self.run_cli([raw(), raw(topic="redux")])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertIn("2 read, 1 rejected", err)
        self.assertIn("evidence with at least one signal: 1 of 2", err)
        self.assertIn("rejected line 2: unknown topic", err)

    def test_strict(self):
        self.assertEqual(self.run_cli([raw(topic="redux")], ["--strict"])[0], 1)

    def test_bad_topics_file_exits_2(self):
        code, out, err = self.run_cli([raw()], topics={"topics": []})
        self.assertEqual((code, out), (2, ""))
        self.assertIn("at least one topic", err)


if __name__ == "__main__":
    unittest.main()
