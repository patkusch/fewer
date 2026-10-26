import contextlib, io, os, tempfile, unittest
from fewer.cli import main, report
from fewer.sources import load_all

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
NONE = os.path.join(FIX, "does-not-exist")


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(list(argv))
    return code, buf.getvalue()


class CliTest(unittest.TestCase):
    def test_report_on_fixture(self):
        out = report(load_all(FIX, NONE))
        self.assertTrue("agents" in out or "Not enough" in out)

    def test_default_runs(self):
        code, out = run("--claude", FIX, "--codex", NONE)
        self.assertEqual(code, 0)
        self.assertTrue(out.strip())

    def test_empty(self):
        self.assertIn("Not enough", report(load_all(NONE, NONE)))

    def test_html_written(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.html")
            run("--claude", FIX, "--codex", NONE, "html", "-o", path)
            self.assertIn("<html", open(path).read().lower())

    def test_waiting_runs(self):
        self.assertEqual(run("--claude", FIX, "waiting")[0], 0)

    def test_feedback(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            open(path, "w").write('{"viewed":[],"highlights":[],"answers":[]}')
            self.assertEqual(run("feedback", path)[0], 0)


if __name__ == "__main__":
    unittest.main()
