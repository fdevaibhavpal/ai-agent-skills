import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import NOW, labels, world
import analyze as an
import render
import score as sc


def analysis():
    ev, sg = world()
    return an.analyze(ev, sg, labels(), 90, an.parse_time(NOW))


def scored():
    return sc.score_analysis(analysis(), sc.load_config(), "advanced")


class BarTests(unittest.TestCase):
    def test_bar_widths_and_values(self):
        self.assertEqual(render.bar(100), "█" * 20 + " 100.0")
        self.assertEqual(render.bar(0), "░" * 20 + "   0.0")
        self.assertEqual(render.bar(50), "█" * 10 + "░" * 10 + "  50.0")
        self.assertEqual(render.bar(None), "n/a (not measured)")
        self.assertEqual(len(render.bar(37.3).split(" ")[0]), 20)

    def test_out_of_range_values_do_not_break_the_bar(self):
        self.assertEqual(render.bar(140).count("█"), 20)
        self.assertEqual(render.bar(-5).count("█"), 0)

    def test_cells_are_escaped(self):
        self.assertEqual(render.cell("a|b\nc"), "a\\|b c")


class GapRenderTests(unittest.TestCase):
    def setUp(self):
        self.result = scored()
        self.text = render.render_gaps(self.result, top=2)

    def test_table_lists_every_scored_topic_in_rank_order(self):
        rows = [l for l in self.text.splitlines() if l.startswith("| ") and not l.startswith("| #")]
        self.assertEqual(len(rows), len(self.result["opportunities"]))
        self.assertIn("| 1 | Profiling | 77.7 | interesting | low |", rows[0])

    def test_numbers_are_copied_from_the_data(self):
        first = self.result["opportunities"][0]
        self.assertIn(f"{first['score']:.1f}", self.text)
        for key in ("demand", "supply", "gap"):
            self.assertIn(render.bar(first["indices"][key]), self.text)

    def test_bars_only_for_the_top_n(self):
        self.assertEqual(self.text.count("```\n"), 2 * 2)       # opening and closing fence per topic
        self.assertIn("**Profiling**", self.text)
        self.assertNotIn("**Rsc**", self.text)

    def test_not_measured_and_unscored_are_stated(self):
        evidence, signals = world()
        signals = [s for s in signals if s["type"] != "coverage"]       # no supply found: the gap is unmeasured
        result = sc.score_analysis(an.analyze(evidence, signals, labels(), 90, an.parse_time(NOW)), sc.load_config(), "advanced")
        text = render.render_gaps(result)
        self.assertIn("gap    n/a (not measured)", text)
        self.assertIn("supply n/a (not measured)", text)          # unmeasured is not zero
        self.assertNotIn("supply ░░░░░░░░░░░░░░░░░░░░   0.0", text)
        self.assertIn("Not scored: testing (0 demand evidence records (needs 3))", render.render_gaps(scored()))

    def test_empty(self):
        self.assertIn("No topic had enough demand", render.render_gaps({"opportunities": [], "unscored": []}))


class TrendAndCompetitorRenderTests(unittest.TestCase):
    def test_trends_grouped_in_order(self):
        text = render.render_trends(analysis())
        self.assertLess(text.index("**Emerging**"), text.index("**Stable**"))
        self.assertLess(text.index("**Stable**"), text.index("**Declining**"))
        self.assertLess(text.index("**Declining**"), text.index("**Unknown**"))
        self.assertIn("| profiling | sample |", text)
        self.assertIn("Directions are heuristic", text)

    def test_competitors(self):
        text = render.render_competitors(analysis())
        self.assertIn("| ChanA | 6 | 2.1 | 83% | on-topic | 100 | 1 |", text)
        self.assertIn("react-memo, memory-leaks, rsc", text)
        self.assertIn("**Top items: ChanA**", text)

    def test_off_topic_only(self):
        data = analysis()
        data["competitors"].update(on_topic=0, demand_topics_no_competitor_coverage=[], topic_coverage={})
        data["competitors"]["competitors"][0].update(off_topic=True)
        text = render.render_competitors(data)
        self.assertIn("off-topic", text)
        self.assertIn("blind spot is claimed", text)
        self.assertNotIn("Top items", text)

    def test_no_competitors(self):
        data = analysis()
        data["competitors"] = {"competitors": [], "on_topic": 0, "topic_coverage": {}, "demand_topics_no_competitor_coverage": []}
        self.assertIn("No competitor content", render.render_competitors(data))


class CliTests(unittest.TestCase):
    def run_cli(self, view, data, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "in.json")
            with open(path, "w") as f:
                json.dump(data, f)
            out, err = io.StringIO(), io.StringIO()
            code = render.main([view, path, *extra], out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def test_views(self):
        self.assertEqual(self.run_cli("gaps", scored(), ["--top", "1"])[0], 0)
        self.assertEqual(self.run_cli("trends", analysis())[0], 0)
        self.assertEqual(self.run_cli("competitors", analysis())[0], 0)

    def test_wrong_file_kind_is_explained(self):
        code, out, err = self.run_cli("gaps", analysis())
        self.assertEqual((code, out), (2, ""))
        self.assertIn("not the right kind of file", err)

    def test_missing_file(self):
        err = io.StringIO()
        self.assertEqual(render.main(["gaps", "/nonexistent.json"], out=io.StringIO(), err=err), 2)
        self.assertIn("cannot read", err.getvalue())


if __name__ == "__main__":
    unittest.main()
