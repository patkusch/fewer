import unittest
from datetime import datetime
from fewer.model import Timeline, Turn
from fewer.metrics import compute

B = datetime(2026, 1, 5, 10, 0).timestamp()


def A(s, a, b): return Turn(s, "agent", B + a, B + b)
def H(s, a, b): return Turn(s, "human", B + a, B + b)


class M(unittest.TestCase):
    def test_empty(self):
        r = compute(Timeline())
        self.assertEqual(r["peak_concurrent_agents"], 0)
        self.assertEqual(r["days"], [])

    def test_concurrency(self):
        r = compute(Timeline([A("a", 0, 100), A("b", 50, 150)]))
        self.assertEqual(r["peak_concurrent_agents"], 2)
        self.assertAlmostEqual(r["mean_concurrent_agents"], 200 / 150)

    def test_switches(self):
        tl = Timeline([A("a", 0, 10), A("b", 60, 70), A("a", 120, 130), A("a", 140, 150), A("b", 5000, 5010)])
        r = compute(tl)
        self.assertEqual(r["context_switches"], 2)   # last one is >10 min after previous
        self.assertEqual(r["prompts"], 5)

    def test_wait_and_idle(self):
        tl = Timeline([A("a", 0, 100), H("a", 100, 400), A("b", 200, 300)])
        r = compute(tl)
        self.assertEqual(r["agent_wait_seconds"], 300)
        self.assertEqual(r["human_idle_seconds"], 200)   # 100-200 and 300-400

    def test_days(self):
        r = compute(Timeline([A("a", 0, 60), A("a", 86400, 86460)]))
        self.assertEqual([d["date"] for d in r["days"]], ["2026-01-05", "2026-01-06"])
        self.assertEqual(r["days"][0]["prompts"], 1)


if __name__ == "__main__":
    unittest.main()
