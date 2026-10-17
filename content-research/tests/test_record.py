import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from record import MAX_TEXT, make_record, write_jsonl  # noqa: E402


def base(**kw):
    args = dict(id="web:x", source_type="web", url="https://example.com/a", title="T",
                tier=1, query="q", access="snippet")
    args.update(kw)
    return make_record(**args)


class RecordTests(unittest.TestCase):
    def test_drops_unobserved_metrics(self):
        rec = base(metrics={"views": 10, "likes": None})
        self.assertEqual(rec["metrics"], {"views": 10})

    def test_keeps_zero_metrics(self):
        self.assertEqual(base(metrics={"comments": 0})["metrics"], {"comments": 0})

    def test_unknown_date_stays_null(self):
        self.assertIsNone(base()["published_at"])

    def test_truncates_text(self):
        self.assertEqual(len(base(text="x" * 5000)["text"]), MAX_TEXT)

    def test_rejects_unknown_source_type(self):
        with self.assertRaises(ValueError):
            base(source_type="tiktok")

    def test_requires_url(self):
        with self.assertRaises(ValueError):
            base(url="")

    def test_write_jsonl_one_object_per_line(self):
        out = io.StringIO()
        self.assertEqual(write_jsonl([base(), base(id="web:y")], out), 2)
        lines = out.getvalue().splitlines()
        self.assertEqual([json.loads(l)["id"] for l in lines], ["web:x", "web:y"])


if __name__ == "__main__":
    unittest.main()
