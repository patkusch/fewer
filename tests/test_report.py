import re
import unittest
from datetime import datetime
from fewer.model import Timeline, Turn
from fewer.report import build_report

B = datetime(2026, 1, 5, 10, 0).timestamp()
DAY = 86400


def day_turns(k, sess="s"):
    o = B + k * DAY
    return [Turn(sess, "agent", o, o + 600), Turn(sess + "2", "agent", o + 300, o + 900),
            Turn(sess, "human", o + 600, o + 900), Turn(sess + "2", "agent", o + 1000, o + 1300),
            Turn(sess + "2", "human", o + 1300, o + 1500)]


class R(unittest.TestCase):
    def test_empty(self):
        h = build_report(Timeline())
        self.assertIn("Not enough sessions", h)
        self.assertNotIn("<svg", h)

    def test_one_day(self):
        h = build_report(Timeline(day_turns(0)))
        self.assertIn("<svg", h)
        self.assertIn("<table>", h)
        self.assertIn("2026-01-05", h)
        self.assertIn("What if agents got faster", h)

    def test_many_days(self):
        tl = Timeline([t for k in range(30) for t in day_turns(k)])
        h = build_report(tl)
        self.assertEqual(h.count("<svg"), 3)
        self.assertGreaterEqual(h.count("<tr><td>2026-01-"), 30)

    def test_self_contained_and_themed(self):
        h = build_report(Timeline(day_turns(0)))
        self.assertIn("prefers-color-scheme:dark", h)
        self.assertIn("viewport", h)
        self.assertNotRegex(h, r"(src|href)=|https?://|<script|@import|url\(")

    def test_escapes_session_names(self):
        evil = '<script>alert(1)</script>"><img src=x onerror=alert(1)>'
        h = build_report(Timeline(day_turns(0, evil)))
        self.assertNotIn("<script", h)
        self.assertNotIn("<img", h)

    def test_what_if_has_four_speeds(self):
        h = build_report(Timeline(day_turns(0)))
        for s in ("0.5x", "1x (today)", "2x", "4x"):
            self.assertIn(s, h)


if __name__ == "__main__":
    unittest.main()
