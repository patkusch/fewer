import os, unittest
from fewer.cli import main, report
from fewer.transcripts import load_timeline

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


class CliTest(unittest.TestCase):
    def test_report_on_fixture(self):
        out = report(load_timeline(FIX))
        self.assertTrue("agents" in out or "Not enough" in out)

    def test_main_runs(self):
        self.assertEqual(main([FIX]), 0)

    def test_empty(self):
        self.assertIn("Not enough", report(load_timeline([])))


if __name__ == "__main__":
    unittest.main()
