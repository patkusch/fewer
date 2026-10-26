"""fewer: are you running too many agents?"""
import argparse
import os
import sys
from statistics import mean

from .handoff import parse_feedback
from .metrics import compute
from .report import build_report
from .sources import load_all
from .verdict import recommend
from .waiting import format_waiting, waiting

CLAUDE = os.path.expanduser("~/.claude/projects")
CODEX = os.path.expanduser("~/.codex/sessions")


def report(timeline):
    m = compute(timeline)
    agent = [t.end - t.start for t in timeline.turns if t.kind == "agent"]
    human = [t.end - t.start for t in timeline.turns if t.kind == "human"]
    if not agent or not human:
        return "Not enough sessions to say anything yet."
    r = recommend(mean(agent), mean(human), current_agents=max(1, round(m["mean_concurrent_agents"])))
    return "\n".join([
        f"Most agents at once: {m['peak_concurrent_agents']} (usually {m['mean_concurrent_agents']:.1f})",
        f"Jumps between agents: {m['context_switches']} ({m['switches_per_hour']:.1f} per active hour)",
        f"Average agent task: {mean(agent) / 60:.1f} min. Average time you take to respond: {mean(human) / 60:.1f} min.",
        "",
        r["verdict"],
    ])


def main(argv=None):
    p = argparse.ArgumentParser(prog="fewer", description=__doc__)
    p.add_argument("--claude", default=CLAUDE, help="Claude Code transcripts folder")
    p.add_argument("--codex", default=CODEX, help="Codex sessions folder (optional)")
    p.add_argument("--since", help="only look at sessions after this date, e.g. 2026-10-01")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("report", help="print the answer (default)")
    h = sub.add_parser("html", help="write a one-page report you can open in a browser")
    h.add_argument("-o", "--out", default="fewer-report.html")
    sub.add_parser("waiting", help="list agents waiting on you, longest first")
    f = sub.add_parser("feedback", help="turn a review page's copied feedback into a note for the agent")
    f.add_argument("file", help="file holding the copied feedback (JSON)")
    a = p.parse_args(argv)

    if a.cmd == "waiting":
        lines = format_waiting(waiting(a.claude))
        print(lines if isinstance(lines, str) else "\n".join(lines))
    elif a.cmd == "feedback":
        with open(a.file) as fh:
            print(parse_feedback(fh.read()))
    elif a.cmd == "html":
        with open(a.out, "w") as fh:
            fh.write(build_report(load_all(a.claude, a.codex, since=a.since)))
        print(f"Wrote {a.out}")
    else:
        print(report(load_all(a.claude, a.codex, since=a.since)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
