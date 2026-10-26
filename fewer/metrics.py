"""Numbers about parallel agents. Pure functions over a Timeline."""
from datetime import datetime, timedelta

SWITCH_WINDOW = 10 * 60


def _sweep(agent):
    """agent: list of (start,end). Returns (peak, weighted_sum, active_seconds, union)."""
    ev = []
    for s, e in agent:
        if e > s:
            ev.append((s, 1))
            ev.append((e, -1))
    ev.sort(key=lambda x: (x[0], x[1]))
    n = peak = 0
    wsum = active = 0.0
    union = []
    prev = None
    for t, d in ev:
        if prev is not None and n > 0 and t > prev:
            wsum += n * (t - prev)
            active += t - prev
            if union and union[-1][1] == prev:
                union[-1][1] = t
            else:
                union.append([prev, t])
        n += d
        peak = max(peak, n)
        prev = t
    return peak, wsum, active, union


def _overlap(a, b):
    """Length of overlap between two lists of merged intervals."""
    tot = 0.0
    j = 0
    for s, e in a:
        while j < len(b) and b[j][1] <= s:
            j += 1
        k = j
        while k < len(b) and b[k][0] < e:
            tot += min(e, b[k][1]) - max(s, b[k][0])
            k += 1
    return tot


def _merge(iv):
    out = []
    for s, e in sorted(iv):
        if e <= s:
            continue
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def _switches(prompts):
    """prompts: sorted list of (time, session)."""
    n = 0
    for (t0, s0), (t1, s1) in zip(prompts, prompts[1:]):
        if s1 != s0 and t1 - t0 <= SWITCH_WINDOW:
            n += 1
    return n


def _summary(turns, prompts, whole_span=None):
    agent = [(t.start, t.end) for t in turns if t.kind == "agent"]
    human = [(t.start, t.end) for t in turns if t.kind == "human"]
    peak, wsum, active, union = _sweep(agent)
    hum = _merge(human)
    idle = sum(e - s for s, e in hum) - _overlap(hum, union)
    sw = _switches(prompts)
    hours = active / 3600.0
    return {
        "peak_concurrent_agents": peak,
        "mean_concurrent_agents": (wsum / active) if active else 0.0,
        "context_switches": sw,
        "switches_per_hour": (sw / hours) if hours else 0.0,
        "agent_wait_seconds": sum(e - s for s, e in human),
        "human_idle_seconds": idle,
        "active_seconds": active,
        "prompts": len(prompts),
    }


def _clip(turns, a, b):
    out = []
    for t in turns:
        s, e = max(t.start, a), min(t.end, b)
        if e > s or (t.kind == "agent" and a <= t.start < b):
            out.append(type(t)(t.session, t.kind, s, max(e, s)))
    return out


def _day_bounds(ts):
    d = datetime.fromtimestamp(ts).replace(hour=0, minute=0, second=0, microsecond=0)
    return d, d + timedelta(days=1)


def compute(timeline):
    turns = list(timeline.turns)
    prompts = sorted((t.start, t.session) for t in turns if t.kind == "agent")
    res = _summary(turns, prompts)
    days = []
    if turns:
        d, _ = _day_bounds(min(t.start for t in turns))
        last = max(t.end for t in turns)
        while d.timestamp() <= last:
            nd = d + timedelta(days=1)
            a, b = d.timestamp(), nd.timestamp()
            dt = _clip(turns, a, b)
            if dt:
                dp = [p for p in prompts if a <= p[0] < b]
                row = _summary(dt, dp)
                row["date"] = d.strftime("%Y-%m-%d")
                days.append(row)
            d = nd
    res["days"] = days
    return res
