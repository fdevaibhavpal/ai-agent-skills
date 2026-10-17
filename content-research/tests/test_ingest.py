import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import ingest  # noqa: E402
from schema_check import load_schema, validate  # noqa: E402

TOOL_OUTPUT = '''Web search results for query: "react profiler"

Links: [{"title":"React Profiler - YouTube","url":"https://www.youtube.com/watch?v=xhfvbKQNlCE"},{"title":"How To Maximize Performance In Your React Apps","url":"https://m.youtube.com/watch?pp=ygUQ&v=Qwb-Za6cBws"},{"title":"Measure react performance like a pro","url":"https://www.youtube.com/shorts/KpTzXmfmXMM"},{"title":"github.com","url":"https://github.com/hhy5277/reactopt"},{"title":"DEV Community","url":"https://dev.to/x/y"},{"title":"What to do when your React app feels slow","url":"https://itnext.io/what-to-do-when-your-react-app-feels-slow-3744c966ddf"},{"title":"Bug: Memory leak","url":"https://github.com/react/react/issues/26069"},{"title":"@fireship channel","url":"https://www.youtube.com/@fireship"}]

The search found several approaches. REMINDER: You MUST include the sources.
'''


class ParseTests(unittest.TestCase):
    def test_links_array_from_a_search_tool(self):
        pairs = ingest.parse_results(TOOL_OUTPUT)
        self.assertEqual(len(pairs), 8)
        self.assertEqual(pairs[0], ("React Profiler - YouTube", "https://www.youtube.com/watch?v=xhfvbKQNlCE"))

    def test_markdown_links_and_plain_lines(self):
        text = "- [Intro to hooks](https://example.com/hooks)\nUseful guide - https://example.org/guide.\nno link here\n"
        self.assertEqual(ingest.parse_results(text), [("Intro to hooks", "https://example.com/hooks"),
                                                      ("Useful guide -  ", "https://example.org/guide")])

    def test_repeated_urls_are_dropped(self):
        self.assertEqual(len(ingest.parse_results("a https://x.test/1\nb https://x.test/1\n")), 1)

    def test_empty_input(self):
        self.assertEqual(ingest.parse_results(""), [])


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.records, self.skipped = ingest.ingest(TOOL_OUTPUT, "react profiler")
        self.by_id = {r["id"]: r for r in self.records}

    def test_useless_titles_and_non_videos_are_skipped(self):
        self.assertEqual(len(self.records), 5)
        self.assertEqual(self.skipped, 3)        # "github.com", "DEV Community", and the channel page

    def test_sources_ids_and_urls(self):
        self.assertEqual({r["source_type"] for r in self.records}, {"youtube", "web", "github"})
        self.assertIn("youtube:xhfvbKQNlCE", self.by_id)
        self.assertIn("youtube:Qwb-Za6cBws", self.by_id)             # mobile URL with extra parameters
        self.assertIn("youtube:KpTzXmfmXMM", self.by_id)             # a short
        self.assertEqual(self.by_id["youtube:Qwb-Za6cBws"]["url"], "https://www.youtube.com/watch?v=Qwb-Za6cBws")

    def test_titles_are_cleaned_and_records_are_titles_only(self):
        self.assertEqual(self.by_id["youtube:xhfvbKQNlCE"]["title"], "React Profiler")      # " - YouTube" removed
        for record in self.records:
            self.assertEqual((record["access"], record["tier"], record["published_at"], record["text"], record["metrics"]),
                             ("snippet", 1, None, "", {}))
            self.assertEqual(record["query"], "react profiler")
            self.assertEqual(validate(record, load_schema("source.json")), [])

    def test_default_source_applies_to_other_sites(self):
        records, _ = ingest.ingest('Links: [{"title":"Release notes for v2","url":"https://example.com/notes"}]\n', "q", "news")
        self.assertEqual(records[0]["source_type"], "news")


class RoleTests(unittest.TestCase):
    TEXT = ('Links: [{"title":"How do I start sourdough? - Seasoned Advice","url":"https://cooking.stackexchange.com/questions/1234/how-do-i-start"},'
            '{"title":"Best starter recipe","url":"https://www.quora.com/Best-sourdough-starter"},'
            '{"title":"Beginner baking forum: my loaf is dense","url":"https://bakersforum.example.com/forums/threads/dense-loaf.99/"},'
            '{"title":"Sourdough for beginners - YouTube","url":"https://www.youtube.com/watch?v=abcdefghijk"},'
            '{"title":"The science of bread","url":"https://example.com/blog/bread-science"},'
            '{"title":"Can I use rye starter?","url":"https://superuser.com/questions/55/can-i"}]')

    def roles(self, **kw):
        records, _ = ingest.ingest(self.TEXT, "sourdough", **kw)
        return {r["title"][:22]: (r["source_type"], r["extra"]["role"]) for r in records}

    def test_questions_and_forums_are_demand_content_is_supply(self):
        roles = self.roles()
        self.assertEqual(roles["How do I start sourdou"], ("stackexchange", "demand"))
        self.assertEqual(roles["Best starter recipe"], ("web", "demand"))                  # Quora
        self.assertEqual(roles["Beginner baking forum:"], ("web", "demand"))               # /forums/threads/ in the path
        self.assertEqual(roles["Sourdough for beginner"], ("youtube", "supply"))
        self.assertEqual(roles["The science of bread"], ("web", "supply"))
        self.assertEqual(roles["Can I use rye starter?"][0], "stackexchange")             # another network site

    def test_forum_software_urls_are_demand(self):
        text = ('Links: [{"title":"Solo travel budget for SE asia for 8 months","url":"https://www.tripadvisor.com/ShowTopic-g1-i12357-k11747811-Solo_travel_budget.html"},'
                '{"title":"Which camera should I buy","url":"https://photo.example.org/viewtopic.php?t=12"}]')
        records, _ = ingest.ingest(text, "q")
        self.assertEqual([r["extra"]["role"] for r in records], ["demand", "demand"])

    def test_role_can_be_forced(self):
        self.assertTrue(all(role == "demand" for _, role in self.roles(role="demand").values()))
        self.assertTrue(all(role == "supply" for _, role in self.roles(role="supply").values()))

    def test_cli_role_flag(self):
        out = io.StringIO()
        ingest.main(["--query", "q", "--role", "demand"], stdin=io.StringIO(self.TEXT), out=out, err=io.StringIO())
        self.assertTrue(all('"role": "demand"' in line for line in out.getvalue().splitlines()))


class CliTests(unittest.TestCase):
    def test_cli(self):
        out, err = io.StringIO(), io.StringIO()
        code = ingest.main(["--query", "q"], stdin=io.StringIO(TOOL_OUTPUT), out=out, err=err)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.getvalue().splitlines()), 5)
        self.assertIn("5 records kept, 3 skipped", err.getvalue())

    def test_nothing_usable_exits_nonzero(self):
        self.assertEqual(ingest.main(["--query", "q"], stdin=io.StringIO("no results"), out=io.StringIO(), err=io.StringIO()), 1)


if __name__ == "__main__":
    unittest.main()
