import json
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from schema_check import load_schema, validate  # noqa: E402


class ValidatorTests(unittest.TestCase):
    schema = {
        "type": "object", "required": ["a"], "additionalProperties": False,
        "properties": {
            "a": {"type": "string", "minLength": 1, "pattern": "^x"},
            "n": {"type": "integer", "minimum": 1, "maximum": 3},
            "o": {"type": ["string", "null"], "enum": ["p", None]},
            "list": {"type": "array", "items": {"type": "integer"}},
            "m": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0}},
        },
    }

    def errors(self, value):
        return validate(value, self.schema)

    def test_valid(self):
        self.assertEqual(self.errors({"a": "xy", "n": 2, "o": None, "list": [1], "m": {"v": 0}}), [])

    def test_required_and_unexpected(self):
        msgs = " ".join(self.errors({"z": 1}))
        self.assertIn("missing required field 'a'", msgs)
        self.assertIn("unexpected field 'z'", msgs)

    def test_types_reject_bool_as_number(self):
        self.assertTrue(self.errors({"a": "x", "n": True}))

    def test_bounds_pattern_enum(self):
        self.assertTrue(self.errors({"a": "y"}))
        self.assertTrue(self.errors({"a": "x", "n": 4}))
        self.assertTrue(self.errors({"a": "x", "o": "q"}))

    def test_nested_paths(self):
        msgs = self.errors({"a": "x", "list": [1, "s"], "m": {"v": -1}})
        self.assertTrue(any("$.list[1]" in m for m in msgs))
        self.assertTrue(any("$.m.v" in m for m in msgs))


class RepoSchemaTests(unittest.TestCase):
    def test_evidence_schema_covers_source_fields(self):
        source, evidence = load_schema("source.json"), load_schema("evidence.json")
        for name, spec in source["properties"].items():
            if name == "query":
                continue  # becomes `queries`
            self.assertIn(name, evidence["properties"], name)
            self.assertEqual(spec.get("type"), evidence["properties"][name].get("type"), name)

    def test_required_fields_are_declared(self):
        for name in ("source.json", "evidence.json"):
            schema = load_schema(name)
            for field in schema["required"]:
                self.assertIn(field, schema["properties"], f"{name}: {field}")

    def test_collector_output_matches_source_schema(self):
        import github
        import youtube
        schema = load_schema("source.json")
        def fixture(name):
            with open(os.path.join(HERE, "fixtures", name)) as f:
                return json.load(f)
        records = github.collect("issues", "q", 5, runner=lambda a: fixture("gh_issues.json"))
        records += github.collect("repos", "q", 5, runner=lambda a: fixture("gh_repos.json"))
        for rec in records:
            self.assertEqual(validate(rec, schema), [], rec["id"])
        video = {"id": "vid1", "snippet": {"title": "t", "channelTitle": "c", "publishedAt": "2026-09-01T00:00:00Z"},
                 "statistics": {"viewCount": "5"}, "contentDetails": {"duration": "PT5S"}}
        self.assertEqual(validate(youtube.video_to_record(video, "q", "2026-10-17T00:00:00Z"), schema), [])


if __name__ == "__main__":
    unittest.main()
