import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import run  # noqa: E402

TOPICS = {"topics": [
    {"topic": "profiling-tools", "label": "Profiling tools", "aliases": ["profiler", "profiling"]},
    {"topic": "memoization", "label": "Memoization", "aliases": ["usememo", "usecallback"]},
    {"topic": "memory-leaks", "label": "Memory leaks", "aliases": ["leak"]},
]}


def record(source, title, n, **kw):
    base = {"id": f"{source}:{n}", "source_type": source, "url": f"https://{source}.test/{n}", "title": title,
            "retrieved_at": "2026-10-17T12:00:00Z", "query": "q", "access": "snippet", "tier": 1}
    base.update(kw)
    return base


def workspace(tmp):
    raw = os.path.join(tmp, "raw")
    os.makedirs(raw)
    questions = [record("stackoverflow", f"How do I use useMemo here {i}?", i, access="fetched", published_at="2026-09-01",
                        text="useMemo and useCallback do not help", metrics={"views": 1000 * i, "answers": 1}) for i in range(1, 5)]
    questions += [record("stackoverflow", f"Memory leak when unmounting {i}", 10 + i, access="fetched",
                         published_at="2026-09-02") for i in range(1, 4)]
    videos = [record("youtube", title, 20 + i) for i, title in enumerate(
        ["React Profiler tutorial", "Profiling React apps explained", "Fix a memory leak in React",
         "useMemo and useCallback explained", "Totally unrelated cooking video"])]
    with open(os.path.join(raw, "stackoverflow.jsonl"), "w") as handle:
        handle.writelines(json.dumps(r) + "\n" for r in questions)
    with open(os.path.join(raw, "youtube.jsonl"), "w") as handle:
        handle.writelines(json.dumps(r) + "\n" for r in videos)
    topics = os.path.join(tmp, "topics.json")
    with open(topics, "w") as handle:
        json.dump(TOPICS, handle)
    return raw, topics, os.path.join(tmp, "out")


def go(*extra, with_topics=True):
    with tempfile.TemporaryDirectory() as tmp:
        raw, topics, out_dir = workspace(tmp)
        argv = ["--raw", raw, "--out", out_dir, *(["--topics", topics] if with_topics else []), *extra]
        out, err = io.StringIO(), io.StringIO()
        code = run.main(argv, out=out, err=err)
        files = sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []
        results = {}
        for name in files:
            if name.endswith(".json"):
                with open(os.path.join(out_dir, name)) as handle:
                    results[name] = json.load(handle)
        return code, out.getvalue(), err.getvalue(), files, results


class RunTests(unittest.TestCase):
    def test_full_run_writes_all_files(self):
        code, out, err, files, results = go("--level", "intermediate")
        self.assertEqual(code, 0, err)
        self.assertEqual(files, ["analysis.json", "blocks.md", "evidence.jsonl", "opportunities.json", "signals.jsonl"])
        self.assertEqual(results["analysis.json"]["meta"]["evidence"], 12)
        self.assertTrue(results["opportunities.json"]["opportunities"])

    def test_summary_shows_the_table_unmatched_records_spot_check_and_limits(self):
        _, out, _, _, _ = go("--level", "intermediate")
        self.assertIn("normalize: 12 read, 0 rejected", out)
        self.assertIn("| # | Topic | Score |", out)
        self.assertIn("Totally unrelated cooking video", out)               # listed as unmatched
        self.assertIn("Spot-check:", out)
        self.assertIn("d: How do I use useMemo here", out)
        self.assertIn("! ", out)                                           # limits are always shown

    def test_suggest_topics_stops_before_labeling(self):
        code, out, _, files, _ = go("--suggest-topics")
        self.assertEqual(code, 0)
        self.assertIn("Frequent phrases in titles", out)
        self.assertEqual(files, ["evidence.jsonl"])

    def test_without_a_topics_file_it_suggests_topics(self):
        code, out, _, _, _ = go(with_topics=False)
        self.assertEqual(code, 0)
        self.assertIn("Frequent phrases", out)

    def test_no_raw_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            self.assertEqual(run.main(["--raw", tmp, "--out", os.path.join(tmp, "o")], out=io.StringIO(), err=err), 2)
            self.assertIn("collect first", err.getvalue())

    def test_bad_records_are_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, topics, out_dir = workspace(tmp)
            with open(os.path.join(raw, "bad.jsonl"), "w") as handle:
                handle.write("{not json\n" + json.dumps({"id": "web:1", "source_type": "web"}) + "\n")
            out = io.StringIO()
            code = run.main(["--raw", raw, "--topics", topics, "--out", out_dir], out=out, err=io.StringIO())
            self.assertEqual(code, 0)
            self.assertIn("2 rejected", out.getvalue())

    def test_no_matching_topics_stops_with_a_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, _, out_dir = workspace(tmp)
            topics = os.path.join(tmp, "t2.json")
            with open(topics, "w") as handle:
                json.dump({"topics": [{"topic": "zebra-crossings", "label": "Zebra crossings"}]}, handle)
            err = io.StringIO()
            self.assertEqual(run.main(["--raw", raw, "--topics", topics, "--out", out_dir], out=io.StringIO(), err=err), 2)
            self.assertIn("check the topic aliases", err.getvalue())

    def test_bad_topics_file_stops_and_a_missing_volume_file_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, topics, out_dir = workspace(tmp)
            self.assertEqual(run.main(["--raw", raw, "--topics", "/nonexistent.json", "--out", out_dir],
                                      out=io.StringIO(), err=io.StringIO()), 2)
            err = io.StringIO()
            code = run.main(["--raw", raw, "--topics", topics, "--out", out_dir, "--volume", "/nonexistent.json"],
                            out=io.StringIO(), err=err)
            self.assertEqual(code, 0)                                       # an optional input being absent is not fatal
            self.assertIn("continuing without it", err.getvalue())

    def test_extra_hand_written_signals_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, topics, out_dir = workspace(tmp)
            extra = os.path.join(tmp, "x.jsonl")
            with open(extra, "w") as handle:
                handle.write(json.dumps({"type": "pain_point", "topic": "memory-leaks", "statement": "Unknown record claimed",
                                         "quote": "Totally unrelated cooking video", "evidence_id": "e-ffffffff"}) + "\n")
            out = io.StringIO()
            run.main(["--raw", raw, "--topics", topics, "--out", out_dir, "--extra", extra], out=out, err=io.StringIO())
            self.assertIn("1 rejected", out.getvalue())                     # unknown evidence id: rejected, not trusted


if __name__ == "__main__":
    unittest.main()
