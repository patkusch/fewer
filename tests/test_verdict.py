import math
import unittest

from fewer import verdict as _verdict_module
from fewer.verdict import MAX_AGENTS


def recommend(*args, **kwargs):
    """The original tests were written for the deterministic model."""
    kwargs.setdefault("model", "steady")
    return _verdict_module.recommend(*args, **kwargs)


class TestRecommend(unittest.TestCase):
    def test_one_agent_when_review_dominates(self):
        r = recommend(60, 600)
        self.assertEqual(r["recommended_agents"], 1)
        self.assertIn("One agent is enough", r["verdict"])

    def test_slow_agents_need_more(self):
        r = recommend(1800, 120, 30)
        self.assertGreaterEqual(r["recommended_agents"], 4)

    def test_hand_computed(self):
        # a=600 h=120 s=120: N=2 -> min(2/840, 1/240)=2/840 ; N=3 -> 3/840 ; N=7 -> limit 1/240
        r = recommend(600, 120, 120)
        t = {row["agents"]: row["tasks_per_hour"] for row in r["table"]}
        self.assertAlmostEqual(t[1], 3600 / 720)
        self.assertAlmostEqual(t[2], 3600 * 2 / 840)
        self.assertAlmostEqual(t[3], 3600 * 3 / 840)
        self.assertAlmostEqual(t[8], 3600 / 240)
        # you cap out at 15/hour; N=3 gives 12.9 (86%), N=4 gives 15
        self.assertAlmostEqual(r["best_tasks_per_hour"], 15)
        self.assertEqual(r["recommended_agents"], 4)
        self.assertGreaterEqual(r["share_of_best"], 0.9)

    def test_smallest_n_reaching_90_percent(self):
        r = recommend(600, 120, 120)
        best = r["best_tasks_per_hour"]
        n = r["recommended_agents"]
        t = {row["agents"]: row["tasks_per_hour"] for row in r["table"]}
        self.assertGreaterEqual(t[n], 0.9 * best)
        if n > 1:
            self.assertLess(t[n - 1], 0.9 * best)

    def test_switch_cost_can_make_one_best(self):
        r = recommend(30, 300, 1000)
        self.assertEqual(r["best_agents"], 1)
        self.assertEqual(r["recommended_agents"], 1)

    def test_higher_switch_cost_never_raises_recommendation_much(self):
        lo = recommend(900, 100, 0)["recommended_agents"]
        hi = recommend(900, 100, 600)["recommended_agents"]
        self.assertLessEqual(hi, lo + 1)

    def test_busy_fraction_in_range(self):
        for row in recommend(500, 90)["table"]:
            self.assertTrue(0 <= row["human_busy"] <= 1)
            self.assertTrue(0 <= row["human_switching"] <= row["human_busy"] + 1e-9)

    def test_one_agent_has_no_switching(self):
        row = recommend(500, 90)["table"][0]
        self.assertEqual(row["human_switching"], 0.0)

    def test_throughput_never_decreases_without_switch_cost(self):
        t = [x["tasks_per_hour"] for x in recommend(700, 100, 0)["table"]]
        self.assertEqual(t, sorted(t))

    def test_position_words(self):
        self.assertEqual(recommend(60, 600, current_agents=5)["position"], "too many")
        self.assertEqual(recommend(1800, 120, 30, current_agents=1)["position"], "too few")
        r = recommend(60, 600, current_agents=1)
        self.assertEqual(r["position"], "about right")
        self.assertIn("about right", r["verdict"])

    def test_too_many_verdict_text(self):
        r = recommend(60, 600, current_agents=5)
        self.assertIn("You run 5; 1 would get you", r["verdict"])
        self.assertIn("far less jumping around", r["verdict"])

    def test_too_few_verdict_text(self):
        r = recommend(1800, 120, 30, current_agents=1)
        self.assertIn("too few", r["verdict"])

    def test_current_above_table_size(self):
        r = recommend(60, 600, current_agents=20)
        self.assertEqual(r["position"], "too many")

    def test_sensitivity_faster_agents_need_fewer(self):
        s = recommend(1800, 120, 30)["sensitivity"]
        by = {x["agent_speed"]: x["recommended_agents"] for x in s}
        self.assertEqual(by[1], recommend(1800, 120, 30)["recommended_agents"])
        self.assertGreaterEqual(by[0.5], by[1])
        self.assertGreaterEqual(by[1], by[2])
        self.assertGreaterEqual(by[2], by[4])
        self.assertGreater(by[0.5], by[4])

    def test_no_jargon_in_verdict(self):
        for args in [(60, 600), (1800, 120, 30), (0, 0), (1, 0, 0)]:
            v = recommend(*args)["verdict"].lower()
            for word in ("utilisation", "utilization", "queue", "queueing", "throughput"):
                self.assertNotIn(word, v)

    def test_zero_review_time_caps_at_max(self):
        r = recommend(600, 0, 0)
        self.assertEqual(r["recommended_agents"], MAX_AGENTS)
        self.assertIn("stops at the 8", r["verdict"])

    def test_zero_agent_time_means_one(self):
        r = recommend(0, 300)
        self.assertEqual(r["recommended_agents"], 1)

    def test_all_zero(self):
        r = recommend(0, 0, 0)
        self.assertEqual(r["recommended_agents"], 1)
        self.assertIn("nothing to measure", r["verdict"])

    def test_zero_switch_cost(self):
        r = recommend(600, 120, 0)
        # human limit 1/120, agents N/720 -> N=6 hits it
        self.assertEqual(r["best_agents"], 6)
        self.assertEqual(r["recommended_agents"], 6)

    def test_huge_ratios(self):
        self.assertEqual(recommend(1e12, 1)["recommended_agents"], MAX_AGENTS)
        self.assertEqual(recommend(1, 1e12)["recommended_agents"], 1)
        self.assertEqual(recommend(1e-9, 1e9, 1e9)["recommended_agents"], 1)

    def test_integers_and_floats(self):
        self.assertEqual(recommend(600, 120)["recommended_agents"],
                         recommend(600.0, 120.0)["recommended_agents"])

    def test_bad_input(self):
        for args in [(-1, 1), (1, -1), (1, 1, -1), (math.nan, 1), (1, math.inf),
                     ("5", 1), (None, 1), (True, 1)]:
            with self.assertRaises(ValueError):
                recommend(*args)
        for bad in (0, -2, 1.5, True, "3"):
            with self.assertRaises(ValueError):
                recommend(60, 60, current_agents=bad)

    def test_default_switch_cost_is_120(self):
        self.assertEqual(recommend(600, 120), recommend(600, 120, 120))

    def test_deterministic(self):
        self.assertEqual(recommend(777, 55, 90, 4), recommend(777, 55, 90, 4))


class TestVariableModelAndRange(unittest.TestCase):
    def rec(self, *a, **k):
        return _verdict_module.recommend(*a, **k)

    def test_variable_is_default(self):
        self.assertEqual(self.rec(600, 120)["model"], "variable")
        self.assertEqual(self.rec(600, 120), self.rec(600, 120, model="variable"))
        self.assertEqual(self.rec(600, 120, model="steady")["model"], "steady")

    def test_bad_model(self):
        with self.assertRaises(ValueError):
            self.rec(600, 120, model="fast")

    def test_hand_computed_two_agents(self):
        # a=600, review=100, N=2 (s=0): rho=1/6. weights 1, 2/6, 2/36
        # P0 = 1/(1+1/3+1/18) = 18/25 -> X = (7/25)/100 per second
        r = self.rec(600, 100, 0)
        t = {x["agents"]: x["tasks_per_hour"] for x in r["table"]}
        self.assertAlmostEqual(t[2], 3600 * (7 / 25) / 100)
        self.assertAlmostEqual(t[1], 3600 * (1 / 7) / 100)  # rho/(1+rho)

    def test_variable_never_beats_steady(self):
        for a, h, s in [(600, 120, 120), (1800, 120, 30), (60, 600, 0),
                        (300, 300, 300), (5, 1, 0), (1e6, 3, 7)]:
            v = self.rec(a, h, s, model="variable")["table"]
            d = self.rec(a, h, s, model="steady")["table"]
            for rv, rd in zip(v, d):
                self.assertLessEqual(rv["tasks_per_hour"], rd["tasks_per_hour"] + 1e-9)
                self.assertTrue(0 <= rv["human_busy"] <= 1)
                self.assertLessEqual(rv["human_switching"], rv["human_busy"] + 1e-9)

    def test_variable_grows_with_agents_without_switch_cost(self):
        t = [x["tasks_per_hour"] for x in self.rec(700, 100, 0)["table"]]
        self.assertEqual(t, sorted(t))

    def test_variable_needs_at_least_as_many_agents(self):
        for a, h, s in [(600, 120, 120), (1800, 120, 30), (900, 100, 0)]:
            self.assertGreaterEqual(self.rec(a, h, s)["recommended_agents"],
                                    self.rec(a, h, s, model="steady")["recommended_agents"])

    def test_variable_edge_cases(self):
        self.assertEqual(self.rec(0, 0, 0)["recommended_agents"], 1)
        self.assertEqual(self.rec(0, 300)["recommended_agents"], 1)
        self.assertEqual(self.rec(1e12, 1)["recommended_agents"], MAX_AGENTS)
        self.assertEqual(self.rec(1, 1e12)["recommended_agents"], 1)
        self.assertEqual(self.rec(600, 0, 0)["recommended_agents"], MAX_AGENTS)

    def test_range_returns_three_answers(self):
        r = self.rec(1200, 100, switch_cost_range=(30, 120, 300))
        sc = r["switch_cost_range"]
        self.assertEqual(list(sc), ["low", "base", "high"])
        self.assertEqual([sc[k]["switch_cost_seconds"] for k in sc], [30, 120, 300])
        self.assertEqual(sc["base"]["recommended_agents"], r["recommended_agents"])
        self.assertGreaterEqual(sc["low"]["recommended_agents"],
                                sc["high"]["recommended_agents"])
        self.assertIn("How sure are we?", r["verdict"])
        self.assertIn("jumping", r["confidence"])

    def test_range_sentence_when_answer_moves(self):
        r = self.rec(1200, 100, switch_cost_range=(0, 120, 600))
        sc = r["switch_cost_range"]
        lo, hi = sc["high"]["recommended_agents"], sc["low"]["recommended_agents"]
        self.assertLess(lo, hi)
        self.assertIn(f"{lo} to {hi} agents; the answer moves with how costly "
                      f"jumping is for you", r["confidence"])

    def test_range_sentence_when_answer_holds(self):
        r = self.rec(60, 600, switch_cost_range=(30, 120, 300))
        self.assertIn("1 agent", r["confidence"])
        self.assertIn("holds", r["confidence"])

    def test_no_range_by_default(self):
        r = self.rec(600, 120)
        self.assertIsNone(r["switch_cost_range"])
        self.assertIsNone(r["confidence"])

    def test_bad_range(self):
        for bad in ((30, 120), (300, 120, 30), (-1, 2, 3), "abc", (1, 2, "3"), 5):
            with self.assertRaises(ValueError):
                self.rec(600, 120, switch_cost_range=bad)

    def test_assumption_labelled(self):
        note = self.rec(600, 120)["switch_cost_note"]
        self.assertIn("ASSUMPTION", note)
        self.assertNotIn("ASSUMPTION", self.rec(600, 120, 45)["switch_cost_note"])

    def test_no_jargon_in_new_text(self):
        r = self.rec(1200, 100, switch_cost_range=(30, 120, 300))
        text = (r["verdict"] + r["confidence"]).lower()
        for word in ("utilisation", "utilization", "queue", "queueing",
                     "throughput", "m/m/1", "exponential"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
