# What already exists, and what is missing

Checked on 2026-10-26 with GitHub search and a read of each README. I did not run or read the code of any of these, so feature claims are what the READMEs say. Star counts are live numbers and will drift.

## Tools that look at your agent sessions

| Tool | Stars | What it tells you | Says anything about your time or focus? |
|---|---|---|---|
| [ccusage](https://github.com/ccusage/ccusage) | 19.2k | Tokens and cost per day, week, month, session | No |
| [codeburn](https://github.com/getagentseal/codeburn) | 11.6k | Cost across 37 tools, spend per pull request | No |
| [agentsview](https://github.com/kenn-io/agentsview) | 6.3k | Session search, length, cost, a "concurrency" and "active time" view | Partly. The README does not say how concurrency is worked out, so I could not check it |
| [claude-devtools](https://github.com/matt1398/claude-devtools) | 4.0k | Opens up one session: tool calls, sub-agents, cost | No |
| [Claude-Code-Agent-Monitor](https://github.com/hoangsonww/Claude-Code-Agent-Monitor) | 1.1k | Live dashboard of sub-agents | No (its concurrency means sub-agents) |
| [splitrail](https://github.com/Piebald-AI/splitrail) | 225 | Cost, plus "active time" (gaps under 5 min) | Closest. One session at a time |

## Tools that run many agents at once

vibe-kanban (28.5k, now winding down), claude-squad (8.7k), agent-kanban (493), grasp (362), octomux (25). They help you manage many agents: boards, one inbox for permission prompts, review screens. None of them measures whether the person in the middle is overloaded, and none helps you run fewer.

## The best of them, and why

For measuring: **agentsview** is the closest, because it already shows concurrency and active time across sessions. For handling many agents: **octomux** is the closest, because it sends you to whichever agent is blocked.

## What nobody has

1. **An answer to "how many agents should I run?"** Every tool counts what happened. None says what to do about it.
2. **Your time as the thing measured.** They count tokens and money. The post's problem is your attention.
3. **Jumps between agents.** Not counted anywhere I found.
4. **A what-if for faster agents.** The post says better models will need fewer agents. No tool shows how the answer changes.
5. **One view over several agent products.** A person running Claude Code and Codex together is the overload case.

## How fewer covers them

| Gap | fewer |
|---|---|
| Advice, not just counts | `fewer` gives a recommended number in plain English |
| Your time | Measures how long agents wait for you and you for them |
| Jumps | Counts them per active hour |
| What-if | Table of the answer at 2x and 4x faster agents |
| Several products | Claude Code and Codex logs merged (see below for what is verified) |
| Who needs me now | `fewer waiting` lists agents waiting on you, longest first |

## What is not proven

- The two-minute cost of a jump is a guess. No study I found measures it for people reviewing agents. Research on interruptions (Gloria Mark, Sophie Leroy) points the same way but gives no number for this. `fewer` shows the answer across 30 s, 2 min and 5 min.
- The METR "19% slower" result is about one assistant on familiar code, not parallel agents. I only saw it second-hand.
- I found no published data on people supervising several agents at once.
- I did not test the post's other ideas: the fast front-desk model and voice or screen recording.
