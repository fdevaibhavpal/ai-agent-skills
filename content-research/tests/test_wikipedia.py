import io
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import wikipedia as wp  # noqa: E402
from record import SourceError  # noqa: E402

NOW = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)


def series(first_day_views, second_day_views, split):
    """Daily items for 2026-07-19 .. 2026-10-16: `first` views before the split date, `second` from it on."""
    from datetime import date, timedelta
    day, items = date(2026, 7, 19), []
    while day <= date(2026, 10, 16):
        items.append({"timestamp": f"{day:%Y%m%d}00", "views": first_day_views if day < split else second_day_views})
        day += timedelta(days=1)
    return {"items": items}


class WikipediaTests(unittest.TestCase):
    def test_windows_end_yesterday_and_split_in_half(self):
        from datetime import date
        calls = []

        def fetch(url):
            calls.append(url)
            return series(10, 30, date(2026, 9, 2))              # 45 prior days at 10, then 45 recent days at 30

        totals = wp.window_totals("Strength training", NOW, 90, fetch=fetch)
        self.assertEqual(totals, {"recent": 45 * 30, "prior": 45 * 10, "days_with_data": 90, "window_days": 45})
        self.assertIn("/Strength_training/daily/2026071900/2026101600", calls[0])
        self.assertIn("en.wikipedia/all-access/user", calls[0])

    def test_titles_are_encoded(self):
        urls = []
        wp.daily_views("AC/DC: live & loud", NOW, NOW, fetch=lambda url: urls.append(url) or {"items": []})
        self.assertIn("AC%2FDC%3A_live_%26_loud", urls[0])

    def test_missing_article_is_explained(self):
        def fetch(url):
            raise SourceError("wikimedia.org returned HTTP 404: Not found")
        with self.assertRaisesRegex(SourceError, "use the exact page title"):
            wp.window_totals("Not a real article", NOW, 90, fetch=fetch)

    def test_other_errors_pass_through(self):
        def fetch(url):
            raise SourceError("wikimedia.org is rate limiting or refusing requests (HTTP 429)")
        with self.assertRaisesRegex(SourceError, "rate limiting"):
            wp.window_totals("Espresso", NOW, 90, fetch=fetch)

    def test_cli_summary_and_partial_failure(self):
        from datetime import date

        def fetch(url):
            if "Missing" in url:
                raise SourceError("wikimedia.org returned HTTP 404: Not found")
            return series(10, 20, date(2026, 9, 2))
        out, err = io.StringIO(), io.StringIO()
        code = wp.main(["views", "Espresso", "Missing", "--now", "2026-10-17T12:00:00Z"], fetch=fetch, out=out, err=err)
        self.assertEqual(code, 1)                                 # one title failed: reported, the other still printed
        self.assertIn("Espresso: 900 views in the recent 45 days vs 450 in the prior 45 (+100%)", out.getvalue())
        self.assertIn("exact page title", err.getvalue())

    def test_bad_now_is_rejected(self):
        self.assertEqual(wp.main(["views", "X", "--now", "yesterday"], fetch=lambda u: {}, out=io.StringIO(), err=io.StringIO()), 2)


if __name__ == "__main__":
    unittest.main()
