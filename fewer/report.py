"""One self-contained HTML page about your agents. No scripts, no outside requests."""
from datetime import date
from html import escape
from statistics import mean

from .metrics import compute
from .verdict import recommend

W, H, PAD = 640, 220, 36


def _e(x):
    return escape(str(x), quote=True)


def _mins(sec):
    return f"{sec / 60:.0f} min" if sec < 5400 else f"{sec / 3600:.1f} h"


def _short(day):
    return day[5:]


def _bars(days, series, title, desc):
    """series: list of (label, class, [values]). Grouped bars, one group per day."""
    top = max([v for _l, _c, vs in series for v in vs] + [0]) or 1
    n = max(len(days), 1)
    gw = (W - 2 * PAD) / n
    bw = max(2.0, min(24.0, gw * 0.8 / len(series)))
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="t-{_e(title)} d-{_e(title)}" '
           f'class="chart"><title id="t-{_e(title)}">{_e(title)}</title>'
           f'<desc id="d-{_e(title)}">{_e(desc)}</desc>',
           f'<line x1="{PAD}" y1="{H - PAD}" x2="{W - PAD}" y2="{H - PAD}" class="axis"/>',
           f'<text x="4" y="{PAD - 8}" class="tick">{top:.3g}</text>',
           f'<text x="4" y="{H - PAD}" class="tick">0</text>']
    for i, d in enumerate(days):
        x0 = PAD + i * gw + (gw - bw * len(series)) / 2
        for j, (_l, cls, vs) in enumerate(series):
            h = (H - 2 * PAD) * vs[i] / top
            out.append(f'<rect x="{x0 + j * bw:.1f}" y="{H - PAD - h:.1f}" width="{bw:.1f}" '
                       f'height="{h:.1f}" class="{cls}"/>')
        if n <= 12 or i % max(1, n // 8) == 0:
            out.append(f'<text x="{PAD + i * gw + gw / 2:.1f}" y="{H - 12}" class="tick mid">'
                       f'{_e(_short(d))}</text>')
    out.append("</svg>")
    leg = "".join(f'<span><i class="sw {c}"></i>{_e(l)}</span>' for l, c, _v in series)
    return "".join(out) + f'<p class="legend">{leg}</p>'


def _line(points, title, desc):
    top = max([v for _l, v in points] + [0]) or 1
    n = len(points)
    step = (W - 2 * PAD) / max(n - 1, 1)
    xy = [(PAD + i * step if n > 1 else W / 2, H - PAD - (H - 2 * PAD) * v / top)
          for i, (_l, v) in enumerate(points)]
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="t-{_e(title)} d-{_e(title)}" '
           f'class="chart"><title id="t-{_e(title)}">{_e(title)}</title>'
           f'<desc id="d-{_e(title)}">{_e(desc)}</desc>',
           f'<line x1="{PAD}" y1="{H - PAD}" x2="{W - PAD}" y2="{H - PAD}" class="axis"/>',
           f'<text x="4" y="{PAD - 8}" class="tick">{top:.3g}</text>',
           f'<text x="4" y="{H - PAD}" class="tick">0</text>']
    if n > 1:
        out.append('<polyline fill="none" class="line" points="%s"/>'
                   % " ".join(f"{x:.1f},{y:.1f}" for x, y in xy))
    for (x, y), (l, _v) in zip(xy, points):
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" class="dot"/>')
    for i, (l, _v) in enumerate(points):
        if n <= 10 or i % max(1, n // 8) == 0:
            out.append(f'<text x="{xy[i][0]:.1f}" y="{H - 12}" class="tick mid">{_e(_short(l))}</text>')
    out.append("</svg>")
    return "".join(out)


def _weeks(days):
    wk = {}
    for d in days:
        y, w, _ = date.fromisoformat(d["date"]).isocalendar()
        s = wk.setdefault((y, w), [d["date"], 0, 0.0])
        s[0] = min(s[0], d["date"])
        s[1] += d["context_switches"]
        s[2] += d["active_seconds"]
    return [(v[0], (v[1] / (v[2] / 3600.0)) if v[2] else 0.0) for _k, v in sorted(wk.items())]


def _table(caption, head, rows):
    th = "".join(f"<th scope=\"col\">{_e(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="scroll"><table><caption>{_e(caption)}</caption>'
            f"<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>")


CSS = """
:root{--bg:#fbfaf8;--fg:#1d1d1f;--mut:#5f6368;--card:#fff;--line:#d9d6d0;--a:#0b6bcb;--b:#c2410c;--c:#2f7d4f}
@media(prefers-color-scheme:dark){:root{--bg:#16171a;--fg:#eceae6;--mut:#a1a5ab;--card:#1f2125;--line:#3a3d43;--a:#6cb2ff;--b:#ff9a62;--c:#6fcf97}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:720px;margin:0 auto;padding:16px}h1{font-size:1.5rem;margin:.6em 0 .3em}h2{font-size:1.15rem;margin:0 0 .3em}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:14px 0}
p{margin:.4em 0}.mut{color:var(--mut);font-size:.92rem}.verdict{font-size:1.2rem;font-weight:600}
.chart{width:100%;height:auto}.axis{stroke:var(--line);stroke-width:1}.tick{fill:var(--mut);font-size:10px}.mid{text-anchor:middle}
.wait-agent{fill:var(--a)}.wait-you{fill:var(--b)}.agents{fill:var(--c)}.line{stroke:var(--a);stroke-width:2}.dot{fill:var(--a)}
.legend span{margin-right:14px;font-size:.9rem}.sw{display:inline-block;width:12px;height:12px;margin-right:5px;border-radius:2px;vertical-align:-1px}
.sw.wait-agent{background:var(--a)}.sw.wait-you{background:var(--b)}.sw.agents{background:var(--c)}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.9rem}
caption{text-align:left;color:var(--mut);padding:6px 0}th,td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--line)}
details{margin-top:8px}summary{cursor:pointer;color:var(--mut)}
"""


def build_report(timeline):
    turns = list(timeline.turns)
    m = compute(timeline)
    agent = [t.end - t.start for t in turns if t.kind == "agent"]
    human = [t.end - t.start for t in turns if t.kind == "human"]
    parts = [f"<h1>Are you running too many agents?</h1>"]
    if not agent or not human or not m["days"]:
        parts.append('<section><p class="verdict">Not enough sessions to say anything yet.</p>'
                     '<p class="mut">Come back after a few days of normal work.</p></section>')
        return _page("".join(parts))

    r = recommend(mean(agent), mean(human), current_agents=max(1, round(m["mean_concurrent_agents"])))
    days = m["days"]
    names = [d["date"] for d in days]
    parts.append(f'<section><p class="verdict">{_e(r["verdict"])}</p>'
                 f'<p class="mut">You usually run {m["mean_concurrent_agents"]:.1f} at once '
                 f'and at most {m["peak_concurrent_agents"]}. Agent tasks last {_mins(mean(agent))} on average; '
                 f'you take {_mins(mean(human))} to answer.</p></section>')

    mean_c = [d["mean_concurrent_agents"] for d in days]
    parts.append('<section><h2>Agents at once, day by day</h2>'
                 '<p class="mut">How many agents were working side by side, on average, while any were working.</p>'
                 + _bars(names, [("Agents at once (average)", "agents", mean_c)],
                         "Agents at once by day", "Bars show the average number of agents working together each day.")
                 + _table("Agents at once, per day", ["Day", "Average", "Most"],
                          [(d["date"], f'{d["mean_concurrent_agents"]:.1f}', d["peak_concurrent_agents"]) for d in days])
                 + "</section>")

    wa = [d["agent_wait_seconds"] / 60 for d in days]
    yw = [max(0.0, d["active_seconds"] - (d["agent_wait_seconds"] - d["human_idle_seconds"])) / 60 for d in days]
    parts.append('<section><h2>Who waits for whom</h2>'
                 '<p class="mut">Blue is time an agent sat waiting for you to read and answer. '
                 'Orange is time you sat with nothing to do while agents worked. '
                 'If blue is much bigger, you are the slow part and extra agents will not help.</p>'
                 + _bars(names, [("Agent waiting for you (minutes)", "wait-agent", wa),
                                 ("You waiting for agents (minutes)", "wait-you", yw)],
                         "Waiting time by day",
                         "Minutes per day an agent waited for you, next to minutes you waited for agents.")
                 + _table("Waiting time, per day", ["Day", "Agent waiting for you (min)", "You waiting for agents (min)"],
                          [(d, f"{a:.0f}", f"{y:.0f}") for d, a, y in zip(names, wa, yw)])
                 + "</section>")

    wk = _weeks(days)
    parts.append('<section><h2>Jumping between agents, by week</h2>'
                 '<p class="mut">Each point is how many times per working hour you switched from one agent to another. '
                 'Lower means calmer days.</p>'
                 + _line(wk, "Jumps per hour by week", "Line of jumps between agents per active hour, one point per week.")
                 + _table("Jumps per hour, per week", ["Week starting", "Jumps per hour"],
                          [(l, f"{v:.1f}") for l, v in wk])
                 + "</section>")

    rows = [(f'{s["agent_speed"]:g}x' + (" (today)" if s["agent_speed"] == 1 else ""),
             _mins(s["agent_seconds"]), s["recommended_agents"]) for s in r["sensitivity"]]
    parts.append('<section><h2>What if agents got faster?</h2>'
                 '<p class="mut">The faster an agent finishes, the less time you spend with nothing to do, '
                 'so the number of agents worth running goes down.</p>'
                 + _table("Recommended agents by agent speed", ["Agent speed", "Average task", "Agents to run"], rows)
                 + "</section>")
    return _page("".join(parts))


def _page(body):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="light dark"><title>fewer report</title>'
            f"<style>{CSS}</style></head><body><main>{body}</main></body></html>")
