import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import ev, write_jsonl
import autolabel as al
from signals import check_signals

TOPICS = [
    {"topic": "rerender-debugging", "label": "Unnecessary re-renders", "aliases": ["rerenders", "re-render"]},
    {"topic": "memoization-hooks", "label": "useMemo and useCallback", "aliases": ["usememo", "usecallback", "react.memo"]},
    {"topic": "react-compiler", "label": "React Compiler", "aliases": ["compiler"]},
    {"topic": "memory-leaks", "label": "Memory leaks", "aliases": ["leak"]},
]


def lookup():
    return {e["topic"]: e["topic"] for e in TOPICS}


def labeled(*records):
    evidence = {r["evidence_id"]: r for r in records}
    raw, matched, unmatched, _ = al.label(evidence, TOPICS)
    return raw, matched, unmatched


class MatchingTests(unittest.TestCase):
    def topics_for(self, title, source="youtube", text=""):
        raw, _, _ = labeled(ev(1, source, title=title, text=text))
        return sorted(s["topic"] for s in raw)

    def test_aliases_labels_and_slugs_match_whole_phrases(self):
        self.assertEqual(self.topics_for("Fix useMemo mistakes"), ["memoization-hooks"])
        self.assertEqual(self.topics_for("The React Compiler explained"), ["react-compiler"])
        self.assertEqual(self.topics_for("Finding memory leaks fast"), ["memory-leaks"])

    def test_spelling_variants_and_plurals(self):
        for title in ("Stop unnecessary re-renders", "Avoid rerenders in lists", "why does it re render", "Unnecessary re-render bug"):
            self.assertIn("rerender-debugging", self.topics_for(title), title)

    def test_no_partial_word_matches(self):
        self.assertEqual(self.topics_for("A compilerless approach"), [])
        self.assertEqual(self.topics_for("Leakage of data in banking"), [])

    def test_several_topics_per_record_up_to_a_cap(self):
        topics = self.topics_for("useMemo and the React Compiler: unnecessary re-renders and memory leaks")
        self.assertEqual(len(topics), al.MAX_TOPICS_PER_RECORD)

    def test_body_text_alone_needs_two_mentions_and_only_for_discussion_sources(self):
        one = "We use useMemo here and nothing else matters in this long description of a layout problem."
        two = "We tried useMemo and useCallback everywhere but the lists still re-render."
        self.assertEqual(self.topics_for("Layout broken", "stackoverflow", one), [])
        self.assertEqual(self.topics_for("Layout broken", "stackoverflow", two), ["memoization-hooks"])
        self.assertEqual(self.topics_for("Layout broken", "youtube", two), [])      # supply is judged from the title


class TypeTests(unittest.TestCase):
    def kind(self, source, title):
        raw, _, _ = labeled(ev(1, source, title=f"{title} useMemo"))
        return raw[0]["type"]

    def test_type_follows_the_source(self):
        self.assertEqual(self.kind("youtube", "A video about"), "coverage")
        self.assertEqual(self.kind("web", "An article about"), "coverage")
        self.assertEqual(self.kind("news", "Announcing"), "coverage")
        self.assertEqual(self.kind("hackernews", "A discussion of"), "interest")
        self.assertEqual(self.kind("hackernews", "Ask HN: why is"), "question")
        self.assertEqual(self.kind("github", "Bug: crash in"), "pain_point")

    def test_questions_on_discussion_sources(self):
        self.assertEqual(self.kind("stackoverflow", "How do I use"), "question")
        self.assertEqual(self.kind("stackoverflow", "When to use"), "question")
        raw, _, _ = labeled(ev(1, "stackoverflow", title="Is useMemo needed?"))
        self.assertEqual(raw[0]["type"], "question")
        self.assertEqual(self.kind("stackoverflow", "useCallback broken in"), "pain_point")


class RoleTests(unittest.TestCase):
    def test_a_web_page_marked_as_demand_is_labeled_as_a_question_not_as_content(self):
        forum = ev(1, "web", title="How do I stop useMemo from re-running?", extra={"role": "demand"})
        article = ev(2, "web", title="How useMemo works", extra={"role": "supply"})
        plain = ev(3, "web", title="Guide to useMemo")                               # no role recorded: judged by its source
        raw, _, _, _ = al.label({r["evidence_id"]: r for r in (forum, article, plain)}, TOPICS)
        kinds = {s["evidence_id"]: s["type"] for s in raw}
        self.assertEqual((kinds[forum["evidence_id"]], kinds[article["evidence_id"]], kinds[plain["evidence_id"]]),
                         ("question", "coverage", "coverage"))


class FormatAndLevelTests(unittest.TestCase):
    def signal(self, title):
        raw, _, _ = labeled(ev(1, "youtube", title=title + " useMemo"))
        return raw[0]

    def test_format_words(self):
        self.assertEqual(self.signal("Step by step tutorial").get("format"), "tutorial")
        self.assertEqual(self.signal("What is").get("format"), "explainer")
        self.assertEqual(self.signal("A real world case study of").get("format"), "case-study")
        self.assertEqual(self.signal("Conference keynote on").get("format"), "talk")

    def test_unstated_format_stays_unset_instead_of_guessed(self):
        self.assertNotIn("format", self.signal("Memoization"))

    def test_levels(self):
        self.assertEqual(self.signal("Advanced").get("level"), "advanced")
        self.assertEqual(self.signal("For beginners:").get("level"), "beginner")
        self.assertEqual(self.signal("Memoization").get("level"), "unknown")

    def test_words_must_be_whole_words(self):
        self.assertNotIn("format", self.signal("Prefixing"))          # "fix" inside "Prefixing"
        self.assertNotIn("format", self.signal("Canvas"))             # "vs" inside "Canvas"


class PromotionTests(unittest.TestCase):
    def test_show_hn_posts_are_not_audience_demand(self):
        show, ask = ev(1, "hackernews", title="Show HN: a useMemo debugger"), ev(2, "hackernews", title="Ask HN: is useMemo worth it")
        raw, matched, unmatched, promotional = al.label({r["evidence_id"]: r for r in (show, ask)}, TOPICS)
        self.assertEqual([s["evidence_id"] for s in raw], [ask["evidence_id"]])
        self.assertEqual(promotional, [show])
        self.assertNotIn(show, unmatched)


class OutputTests(unittest.TestCase):
    def test_every_signal_passes_the_quote_check(self):
        records = [ev(1, "stackoverflow", title="Why does useMemo not help?"), ev(2, "youtube", title="Fix memory leaks in React"),
                   ev(3, "hackernews", title="React Compiler playground thread"), ev(4, "web", title="Nothing relevant here")]
        evidence = {r["evidence_id"]: r for r in records}
        raw, matched, unmatched, _ = al.label(evidence, TOPICS)
        signals, rejected, dups, _ = check_signals([(n, json.dumps(s)) for n, s in enumerate(raw, 1)], evidence, lookup())
        self.assertEqual((len(signals), rejected, dups), (len(raw), [], 0))
        self.assertEqual(matched, 3)
        self.assertEqual([r["title"] for r in unmatched], ["Nothing relevant here"])

    def test_demand_statement_is_the_title_and_coverage_is_generic(self):
        raw, _, _ = labeled(ev(1, "stackoverflow", title="Why does useMemo not help?"), ev(2, "youtube", title="Fix memory leaks"))
        by_type = {s["type"]: s for s in raw}
        self.assertEqual(by_type["question"]["statement"], "Why does useMemo not help?")
        self.assertEqual(by_type["coverage"]["statement"], "Existing tutorial about Memory leaks")

    def test_short_titles_are_padded_not_rejected_and_tiny_ones_skipped(self):
        raw, _, _ = labeled(ev(1, "youtube", title="Compiler"), ev(2, "youtube", title="Leak"))
        self.assertEqual(len(raw), 1)                                  # a quote must be 8+ characters
        self.assertGreaterEqual(len(raw[0]["statement"]), 8)


class SuggestTests(unittest.TestCase):
    def test_frequent_phrases_without_stop_word_edges(self):
        evidence = {r["evidence_id"]: r for r in [ev(n, "youtube", title=t) for n, t in enumerate(
            ["React memory leaks explained", "Fix React memory leaks", "Finding memory leaks in React", "The best way to cook"], 1)]}
        phrases = dict(al.suggest(evidence, minimum=3, max_share=0.9))
        self.assertEqual(phrases.get("memory leaks"), 3)
        self.assertNotIn("the best", phrases)
        self.assertNotIn("memory", phrases)


class SuggestSubjectTests(unittest.TestCase):
    def test_the_subject_itself_and_single_topic_words_are_handled(self):
        titles = ["Southeast Asia budget guide", "Southeast Asia scams to avoid", "Southeast Asia packing list", "Southeast Asia visa rules",
                  "Backpacking budget tips for beginners", "Cheap budget hostels", "Packing list mistakes", "Common scams and tips", "Visa on arrival scams"]
        evidence = {r["evidence_id"]: r for r in [ev(n, "youtube", title=t) for n, t in enumerate(titles, 1)]}
        found = dict(al.suggest(evidence, minimum=3))
        self.assertEqual(found.get("southeast asia"), 4)          # in 4 of 9 titles (44%): still a candidate
        self.assertIn("budget", found)
        self.assertIn("scams", found)
        self.assertEqual(found["budget"], 3)
        subject_heavy = {r["evidence_id"]: r for r in [ev(n, "youtube", title="Southeast Asia " + w) for n, w in enumerate(
            ["budget", "scams", "packing", "visa", "budget guide", "scams guide"], 1)]}
        self.assertNotIn("southeast asia", dict(al.suggest(subject_heavy, minimum=3)))   # in every title: the subject, not a topic


class CliTests(unittest.TestCase):
    def run_cli(self, args_fn):
        records = [ev(1, "stackoverflow", title="Why does useMemo not help?"), ev(2, "youtube", title="Fix memory leaks in React")]
        with tempfile.TemporaryDirectory() as tmp:
            e, t = os.path.join(tmp, "e.jsonl"), os.path.join(tmp, "t.json")
            write_jsonl(e, records)
            with open(t, "w") as f:
                json.dump({"topics": TOPICS}, f)
            out, err = io.StringIO(), io.StringIO()
            code = al.main(args_fn(e, t), out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_label(self):
        code, out, err = self.run_cli(lambda e, t: [e, t])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 2)
        self.assertIn("2 of 2 records matched a topic", err)

    def test_extra_hand_written_signals_are_checked_and_added(self):
        def args(e, t):
            extra = os.path.join(os.path.dirname(e), "x.jsonl")
            write_jsonl(extra, [{"type": "pain_point", "topic": "memory-leaks", "statement": "Memory keeps growing",
                                 "quote": "Why does useMemo not help?", "evidence_id": "e-00000001"},
                                {"type": "pain_point", "topic": "memory-leaks", "statement": "A fabricated claim here",
                                 "quote": "this text is not in the record", "evidence_id": "e-00000001"}])
            return [e, t, "--extra", extra]
        code, out, err = self.run_cli(args)
        self.assertEqual(len(out.splitlines()), 3)
        self.assertIn("(1 rejected", err)

    def test_suggest_and_usage_errors(self):
        code, out, _ = self.run_cli(lambda e, t: [e, "--suggest"])
        self.assertEqual(code, 0)
        code, _, err = self.run_cli(lambda e, t: [e])
        self.assertEqual(code, 2)
        self.assertIn("give topics.json", err)


if __name__ == "__main__":
    unittest.main()
