"""fewer: are you running too many agents?"""
import argparse
import os
import sys
from statistics import mean

from .metrics import compute
from .transcripts import load_timeline
from .verdict import recommend


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
    p.add_argument("path", nargs="?", default=os.path.expanduser("~/.claude/projects"),
                   help="folder of Claude Code transcripts (default: ~/.claude/projects)")
    p.add_argument("--since", help="only look at sessions after this date, e.g. 2026-10-01")
    a = p.parse_args(argv)
    print(report(load_timeline(a.path, since=a.since)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
