import contextlib
import io
import unittest

from fewer.cli import main


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class CommandLine(unittest.TestCase):
    def test_help_exits_cleanly_and_names_the_tool(self):
        code, out, _ = run(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("fewer", out)

    def test_an_unknown_option_is_refused_and_nothing_runs(self):
        code, out, err = run(["--nope"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--nope", err)


if __name__ == "__main__":
    unittest.main()
