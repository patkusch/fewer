import os
import unittest
from fewer.transcripts import load_timeline

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


class T(unittest.TestCase):
    def setUp(self):
        self.tl = load_timeline(FIX)

    def test_agent_turns(self):
        a = [t for t in self.tl.turns if t.kind == "agent" and t.session == "A"]
        self.assertEqual(len(a), 3)
        self.assertEqual(a[0].end - a[0].start, 120)     # tool result counts as activity
        self.assertEqual(a[2].end - a[2].start, 0)       # idle gap > 30 min ends the turn at the prompt

    def test_human_turn_capped(self):
        h = [t for t in self.tl.turns if t.kind == "human" and t.session == "A"]
        self.assertEqual(h[0].end - h[0].start, 240)     # 10:02 -> 10:06
        self.assertTrue(all(t.end - t.start <= 600 for t in h))

    def test_skips_bad_lines_and_sorted(self):
        starts = [t.start for t in self.tl.turns]
        self.assertEqual(starts, sorted(starts))

    def test_since(self):
        tl = load_timeline(FIX, since="2026-01-05T10:04:00Z")
        self.assertFalse([t for t in tl.turns if t.session == "B"])

    def test_single_file(self):
        self.assertTrue(load_timeline(os.path.join(FIX, "sample.jsonl")).turns)


if __name__ == "__main__":
    unittest.main()
