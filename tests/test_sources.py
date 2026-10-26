import os
import shutil
import tempfile
import unittest
from fewer.sources import load_all

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        self.cdx = os.path.join(self.d, "codex", "2026", "01", "06")
        os.makedirs(self.cdx)
        for f in os.listdir(FIX):
            if f.startswith("codex_"):
                shutil.copy(os.path.join(FIX, f), os.path.join(self.cdx, f[len("codex_"):]))
        self.cl = os.path.join(self.d, "claude")
        os.makedirs(self.cl)
        shutil.copy(os.path.join(FIX, "sample.jsonl"), self.cl)
        self.codex_root = os.path.join(self.d, "codex")

    def test_merges_both(self):
        tl = load_all(self.cl, self.codex_root)
        sess = {t.session for t in tl.turns}
        self.assertIn("A", sess)
        self.assertIn("codex:cx1", sess)
        starts = [t.start for t in tl.turns]
        self.assertEqual(starts, sorted(starts))

    def test_codex_turns(self):
        tl = load_all(os.path.join(self.d, "none"), self.codex_root)
        a = [t for t in tl.turns if t.session == "codex:cx1" and t.kind == "agent"]
        self.assertEqual([t.end - t.start for t in a], [120, 30])
        h = [t for t in tl.turns if t.session == "codex:cx1" and t.kind == "human"]
        self.assertEqual(h[0].end - h[0].start, 240)    # 09:02:10 -> 09:06:10

    def test_gap_capped_and_filename_id(self):
        tl = load_all(os.path.join(self.d, "none"), self.codex_root)
        a = [t for t in tl.turns if t.session == "codex:bbbbbbbb-0000-0000-0000-000000000002"]
        self.assertEqual([t.end - t.start for t in a], [600])   # 50 min gap ends the turn

    def test_missing_folders(self):
        self.assertEqual(load_all(os.path.join(self.d, "a"), os.path.join(self.d, "b")).turns, [])
        self.assertTrue(load_all(self.cl, os.path.join(self.d, "b")).turns)

    def test_since(self):
        tl = load_all(self.cl, self.codex_root, since="2026-01-06T09:05:00Z")
        self.assertFalse([t for t in tl.turns if t.session == "A"])
        self.assertTrue([t for t in tl.turns if t.session == "codex:cx1"])
