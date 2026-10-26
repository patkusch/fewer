"""How many agents should you run? A small, exact model, no randomness.

One person serves N agents. Each agent works for `agent` seconds, then needs
`human` seconds of your review. Every time you move from one agent to another
it costs `switch_cost` seconds to get your head back into that task.
With one agent there is nothing to switch between, so no switch cost.

Per review you spend h = human + switch_cost seconds (just `human` if N = 1).
Two limits decide the speed:
  * the agents: N agents, each taking agent + h seconds per round, give
    N / (agent + h) finished tasks per second;
  * you: you can only finish 1 / h reviews per second, however many agents wait.
Throughput is whichever limit is lower. That is exact for this model.
"""
import math

MAX_AGENTS = 8
TARGET_SHARE = 0.90
DEFAULT_SWITCH_COST = 120
SPEEDUPS = (0.5, 1, 2, 4)


def _check(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if math.isnan(value) or math.isinf(value) or value < 0:
        raise ValueError(f"{name} must be zero or more, and a real number")


def _row(n, agent, human, switch):
    """Throughput (tasks/hour) and how busy you are, for n agents."""
    per_review = human + (switch if n > 1 else 0.0)
    cycle = agent + per_review
    if cycle == 0:
        return {"agents": n, "tasks_per_hour": 0.0, "human_busy": 0.0,
                "human_switching": 0.0}
    agent_limit = n / cycle
    human_limit = math.inf if per_review == 0 else 1.0 / per_review
    rate = min(agent_limit, human_limit)
    busy = min(1.0, rate * per_review)
    jumping = min(1.0, rate * (switch if n > 1 else 0.0))
    return {"agents": n, "tasks_per_hour": rate * 3600,
            "human_busy": busy, "human_switching": jumping}


def _table(agent, human, switch):
    return [_row(n, agent, human, switch) for n in range(1, MAX_AGENTS + 1)]


def _pick(table):
    best = max(r["tasks_per_hour"] for r in table)
    if best <= 0:
        return 1, 0.0
    for r in table:
        if r["tasks_per_hour"] >= TARGET_SHARE * best - 1e-12:
            return r["agents"], best
    return table[-1]["agents"], best  # unreachable, kept for safety


def _plural(n, word="agent"):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _verdict(rec, share, capped):
    pct = round(share * 100)
    if rec == 1:
        text = ("One agent is enough. More agents would not get you much more "
                "done, and you would spend your day jumping between them.")
    else:
        text = (f"Run {_plural(rec)}. That gets you {pct}% of the most work you "
                f"could get, and a bigger crowd would mostly add jumping around.")
    if capped:
        text += (f" Reviews are so quick that more agents would keep helping, "
                 f"so this stops at the {MAX_AGENTS} we checked.")
    return text


def recommend(mean_agent_seconds, mean_human_review_seconds,
              switch_cost_seconds=DEFAULT_SWITCH_COST, current_agents=None):
    """Return the recommended number of agents plus the numbers behind it."""
    _check("mean_agent_seconds", mean_agent_seconds)
    _check("mean_human_review_seconds", mean_human_review_seconds)
    _check("switch_cost_seconds", switch_cost_seconds)
    if current_agents is not None:
        if (isinstance(current_agents, bool) or not isinstance(current_agents, int)
                or current_agents < 1):
            raise ValueError("current_agents must be a whole number, 1 or more")

    a, h, s = float(mean_agent_seconds), float(mean_human_review_seconds), float(switch_cost_seconds)
    table = _table(a, h, s)
    rec, best = _pick(table)
    rec_rate = table[rec - 1]["tasks_per_hour"]
    share = (rec_rate / best) if best > 0 else 1.0
    best_n = max(table, key=lambda r: (r["tasks_per_hour"], -r["agents"]))["agents"]
    capped = (rec == MAX_AGENTS and best > 0)

    verdict = _verdict(rec, share, capped) if best > 0 else (
        "There is nothing to measure: no agent time and no review time.")
    if current_agents is not None and best > 0:
        cur_row = table[min(current_agents, MAX_AGENTS) - 1]
        cur_share = cur_row["tasks_per_hour"] / best
        if current_agents > rec:
            verdict = (f"You run {current_agents}; {rec} would get you "
                       f"{round(share * 100)}% of the work with far less jumping around. "
                       f"You are running too many.")
        elif current_agents < rec:
            verdict = (f"You run {current_agents}, which gets you only {round(cur_share * 100)}% "
                       f"of the work you could get. {_plural(rec)} would fix that. "
                       f"You are running too few.")
        else:
            verdict = (f"You run {current_agents}, which is about right. "
                       f"It gets you {round(share * 100)}% of the most work you could get.")

    if current_agents is None:
        position = None
    elif current_agents > rec:
        position = "too many"
    elif current_agents < rec:
        position = "too few"
    else:
        position = "about right"

    sensitivity = []
    for f in SPEEDUPS:
        r, _b = _pick(_table(a / f, h, s))
        sensitivity.append({"agent_speed": f, "agent_seconds": a / f,
                            "recommended_agents": r})

    return {
        "recommended_agents": rec,
        "best_agents": best_n,
        "share_of_best": share,
        "tasks_per_hour": rec_rate,
        "best_tasks_per_hour": best,
        "position": position,
        "verdict": verdict,
        "table": table,
        "sensitivity": sensitivity,
    }
