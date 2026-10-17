"""Runs the real scripts in sequence, as the pipeline doc describes, to check the stages fit together."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
SCRIPTS = os.path.join(HERE, "..", "scripts")
RAW = os.path.join(HERE, "fixtures", "raw_mixed.jsonl")


def run(script, *args):
    proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class PipelineTests(unittest.TestCase):
    def test_normalize_signals_analyze(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = lambda name: os.path.join(tmp, name)  # noqa: E731
            code, out, _ = run("normalize.py", RAW)
            self.assertEqual(code, 0)
            with open(path("evidence.jsonl"), "w") as f:
                f.write(out)
            by_url = {json.loads(l)["canonical_url"]: json.loads(l) for l in out.splitlines()}
            guide = by_url["https://example.com/react-perf?a=1&b=2"]
            thread = by_url["https://reddit.com/r/reactjs/comments/abc/thread"]

            with open(path("topics.json"), "w") as f:
                json.dump({"topics": [{"topic": "profiling", "label": "Profiling", "aliases": ["react profiler"]}]}, f)
            raw_signals = [
                {"type": "coverage", "topic": "Profiling", "statement": "A guide to profiling React apps",
                 "quote": "walks through finding unnecessary renders", "evidence_id": guide["evidence_id"],
                 "format": "tutorial", "level": "intermediate"},
                {"type": "question", "topic": "react profiler", "statement": "Why is my app slow?",
                 "quote": "Why is my app slow?", "evidence_id": thread["evidence_id"]},
                {"type": "pain_point", "topic": "profiling", "statement": "A made-up complaint",
                 "quote": "this sentence is not in the evidence", "evidence_id": thread["evidence_id"]},
            ]
            with open(path("signals.raw.jsonl"), "w") as f:
                f.write("\n".join(json.dumps(s) for s in raw_signals) + "\n")

            code, out, err = run("signals.py", path("evidence.jsonl"), path("topics.json"), path("signals.raw.jsonl"))
            self.assertEqual(code, 0)
            self.assertEqual(len(out.splitlines()), 2)
            self.assertIn("1 rejected", err)
            self.assertIn("quote does not appear", err)
            with open(path("signals.jsonl"), "w") as f:
                f.write(out)

            code, out, err = run("analyze.py", path("evidence.jsonl"), path("signals.jsonl"), path("topics.json"))
            self.assertEqual(code, 0, err)
            analysis = json.loads(out)
            (theme,) = analysis["themes"]
            self.assertEqual(theme["topic"], "profiling")
            self.assertEqual((theme["demand"]["evidence"], theme["supply"]["evidence"]), (1, 1))
            self.assertEqual(theme["supply"]["by_format"], {"tutorial": 1})
            self.assertEqual(theme["demand"]["metrics_total"], {"score": 40, "comments": 12})
            self.assertEqual(analysis["meta"]["now"], "2026-10-17T12:00:00Z")
            self.assertTrue(any("not been independently verified" in n for n in analysis["limits"]))
            with open(path("analysis.json"), "w") as f:
                f.write(out)

            # one demand record is below the minimum, so nothing is scored, and the script says so
            code, out, err = run("score.py", path("analysis.json"), "--audience-level", "advanced")
            self.assertEqual(code, 0, err)
            scores = json.loads(out)
            self.assertEqual(scores["opportunities"], [])
            self.assertEqual(scores["unscored"][0]["topic"], "profiling")
            self.assertTrue(any("No topic had enough demand" in w for w in scores["warnings"]))

    def test_scripts_report_missing_inputs_cleanly(self):
        code, out, err = run("signals.py", "nope.jsonl", "nope.json", "nope.jsonl")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("cannot read nope.jsonl", err)
        code, _, err = run("analyze.py", "nope.jsonl", "nope.jsonl", "nope.json")
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
