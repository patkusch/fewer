import os
import unittest
from datetime import datetime

from fewer.waiting import waiting, format_waiting

FX = os.path.join(os.path.dirname(__file__), "fixtures")
P = lambda n: os.path.join(FX, f"waiting_{n}.jsonl")
T = lambda m: datetime.fromisoformat(f"2026-01-01T10:{m:02d}:00+00:00").timestamp()


class WaitingTests(unittest.TestCase):
    def test_finished(self):
        r = waiting([P("finished")], now=T(19))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["reason"], "finished")
        self.assertEqual(r[0]["waiting_seconds"], 14 * 60)
        self.assertEqual(r[0]["project"], "alpha")
        self.assertLessEqual(len(r[0]["last_agent_text_snippet"]), 120)

    def test_question_with_bad_line(self):
        r = waiting([P("asked")], now=T(3))
        self.assertEqual(r[0]["reason"], "asked a question")

    def test_permission_only_after_grace(self):
        self.assertEqual(waiting([P("permission")], now=T(1) + 5), [])
        r = waiting([P("permission")], now=T(3))
        self.assertEqual(r[0]["reason"], "needs permission")

    def test_working_not_waiting(self):
        self.assertEqual(waiting([P("working")], now=T(12)), [])

    def test_old_sessions_dropped(self):
        self.assertEqual(waiting([P("finished")], now=T(5) + 7 * 3600), [])

    def test_sorted_and_format(self):
        r = waiting(FX, now=T(19))
        secs = [x["waiting_seconds"] for x in r]
        self.assertEqual(secs, sorted(secs, reverse=True))
        self.assertEqual(format_waiting(r)[0],
                         "3 agents are waiting for you. Longest: 18 min, in gamma: needs permission.")
        self.assertEqual(format_waiting([]), ["No agents are waiting for you."])


if __name__ == "__main__":
    unittest.main()
