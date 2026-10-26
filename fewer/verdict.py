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

Two models are available, chosen with recommend(..., model=...):

  * "variable" (the default): the machine-repairman model, one person and N
    agents where agent time and review time both vary from task to task
    (exponential-ish: many short ones, a few long ones). It is a finite-source
    M/M/1//N queue. Birth-death solution: with rho = h / agent, the chance of
    n agents waiting for you is P_n = P_0 * N!/(N-n)! * rho^n, and
    throughput X(N) = (1 - P_0) / h. Exact, no randomness.
  * "steady": the deterministic model above (every task takes exactly the
    average). It is the OPTIMISTIC UPPER BOUND: with no variability, agents
    never bunch up waiting for you and you are never idle by bad luck, so it
    always shows at least as much work as the variable model.

ASSUMPTION: the 120 s switch cost is a placeholder. We found no study that
measures it for people reviewing agents. Work on attention residue (Mark et
al, Leroy) shows that switching has a cost and gives its direction, not a
number to use here. Pass your own figure, or a range, to see how much the
answer depends on it.
"""
import math

MAX_AGENTS = 8
TARGET_SHARE = 0.90
DEFAULT_SWITCH_COST = 120
SPEEDUPS = (0.5, 1, 2, 4)
MODELS = ("variable", "steady")
ASSUMPTION_NOTE = ("The %d s cost of jumping between agents is an ASSUMPTION: "
                   "we found no study measuring it for people reviewing agents. "
                   "Research on attention residue (Mark et al, Leroy) only says "
                   "the cost is real, not how big. Use your own figure if you can.")


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


def _row_variable(n, agent, human, switch):
    """Exact machine-repairman (finite-source M/M/1//N) numbers for n agents."""
    sw = switch if n > 1 else 0.0
    per_review = human + sw
    if agent + per_review == 0:
        return {"agents": n, "tasks_per_hour": 0.0, "human_busy": 0.0,
                "human_switching": 0.0}
    if per_review == 0:
        rate = n / agent  # you are never the bottleneck
    else:
        rate = None
        if agent == 0:
            rate = 1.0 / per_review  # you are always busy
        else:
            try:
                rho = per_review / agent
                term, tail = 1.0, 0.0  # tail = sum of P_n/P_0 for n >= 1
                for k in range(1, n + 1):
                    term *= (n - k + 1) * rho
                    tail += term
                # X = (1 - P0) / per_review, with 1 - P0 = tail / (1 + tail)
                rate = (tail / (1.0 + tail)) / per_review
            except OverflowError:
                rate = 1.0 / per_review
    busy = min(1.0, rate * per_review)
    jumping = min(1.0, rate * sw)
    return {"agents": n, "tasks_per_hour": rate * 3600,
            "human_busy": busy, "human_switching": jumping}


def _table(agent, human, switch, model="variable"):
    row = _row_variable if model == "variable" else _row
    return [row(n, agent, human, switch) for n in range(1, MAX_AGENTS + 1)]


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


def _range_line(recs):
    lo, hi = min(recs), max(recs)
    if lo == hi:
        return (f"{_plural(lo)}, and that holds whether jumping between agents "
                f"costs you little or a lot.")
    return (f"{lo} to {hi} agents; the answer moves with how costly jumping "
            f"is for you.")


def recommend(mean_agent_seconds, mean_human_review_seconds,
              switch_cost_seconds=DEFAULT_SWITCH_COST, current_agents=None,
              switch_cost_range=None, model="variable"):
    """Return the recommended number of agents plus the numbers behind it.

    model="variable" (default) is the exact machine-repairman model: tasks and
    reviews vary in length, so agents sometimes queue for you and you
    sometimes wait for them. model="steady" is the deterministic model where
    everything takes exactly the average; it is the optimistic upper bound
    and never shows less work than "variable".

    switch_cost_range=(low, base, high) in seconds also returns the
    recommendation at each value under "switch_cost_range", plus a plain
    sentence on how sure we are under "confidence". The default 120 s switch
    cost is an ASSUMPTION (see the module doc and "switch_cost_note").
    """
    if model not in MODELS:
        raise ValueError(f"model must be one of {MODELS}")
    if switch_cost_range is not None:
        if (not isinstance(switch_cost_range, (tuple, list))
                or len(switch_cost_range) != 3):
            raise ValueError("switch_cost_range must be (low, base, high)")
        for v in switch_cost_range:
            _check("switch_cost_range value", v)
        if not (switch_cost_range[0] <= switch_cost_range[1] <= switch_cost_range[2]):
            raise ValueError("switch_cost_range must go from low to high")
    _check("mean_agent_seconds", mean_agent_seconds)
    _check("mean_human_review_seconds", mean_human_review_seconds)
    _check("switch_cost_seconds", switch_cost_seconds)
    if current_agents is not None:
        if (isinstance(current_agents, bool) or not isinstance(current_agents, int)
                or current_agents < 1):
            raise ValueError("current_agents must be a whole number, 1 or more")

    a, h, s = float(mean_agent_seconds), float(mean_human_review_seconds), float(switch_cost_seconds)
    table = _table(a, h, s, model)
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
        r, _b = _pick(_table(a / f, h, s, model))
        sensitivity.append({"agent_speed": f, "agent_seconds": a / f,
                            "recommended_agents": r})

    sc_range = confidence = None
    if switch_cost_range is not None:
        sc_range = {}
        for name, sc in zip(("low", "base", "high"), switch_cost_range):
            r, _b = _pick(_table(a, h, float(sc), model))
            sc_range[name] = {"switch_cost_seconds": sc, "recommended_agents": r}
        confidence = _range_line([v["recommended_agents"] for v in sc_range.values()])
        verdict += " How sure are we? " + confidence

    if s == DEFAULT_SWITCH_COST:
        note = ASSUMPTION_NOTE % DEFAULT_SWITCH_COST
    else:
        note = (f"The {s:g} s cost of jumping between agents is the figure you "
                f"gave. We know of no study that measures it for reviewing agents.")

    return {
        "model": model,
        "switch_cost_range": sc_range,
        "confidence": confidence,
        "switch_cost_note": note,
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
