# fewer

Are you running too many agents?

A recent post, [ETOOMANYTHINGS? Run Fewer Agents](https://blog.exe.dev/etoomanythings), argues that people start extra agents just to fill the time while one is slow, and that juggling them wears out the person in the middle. `fewer` checks that against your own work.

## What it does

It reads your Claude Code session history on your machine (nothing is sent anywhere) and tells you:

- how many agents you really run at once,
- how often you jump from one to another,
- how long an agent works versus how long you take to answer it,
- how many agents would get you nearly all the work with the least jumping.

```
python3 -m fewer.cli --since 2026-10-01          # the answer
python3 -m fewer.cli html -o report.html          # a one-page report with charts
python3 -m fewer.cli waiting                      # agents waiting on you, longest first
python3 -m fewer.cli feedback copied.json         # review-page feedback -> note for the agent
```

It reads Claude Code logs, and Codex logs too if they are there (the Codex format is only partly checked, see RESEARCH.md).

Example output:

```
Most agents at once: 2 (usually 1.0)
Jumps between agents: 20 (1.8 per active hour)
Average agent task: 3.5 min. Average time you take to respond: 6.0 min.

You run 1, which gets you only 84% of the work you could get. 2 agents would fix that. You are running too few.
```

## How the answer is worked out

One person can only review one thing at a time, and every jump costs a couple of minutes of focus. So extra agents only help while the person is not already the slow part. `fewer` picks the smallest number of agents that gets within 90% of the best possible work. If your agents get twice as fast, that number drops (`verdict.recommend` prints the table), which is the post's point.

## The one-page review (`fewer/handoff.py`)

The post's other idea: instead of chatting back and forth, the agent hands you one page with decisions, open questions and the changes. The page notes what you read, what you agreed with and what you highlighted, and turns it into a short note the agent can read. It is not tested in a browser yet.

## Limits

- The timings are guesses from timestamps: a gap of over 10 minutes counts as you walking away.
- It only sees Claude Code sessions.
- The answer is shown as a range (jumps costing 30 s, 2 min or 5 min) because the 2-minute figure is an assumption, not a measurement. The 90% target and the cap of 8 agents are plain constants in `fewer/verdict.py`.

Tests: `python3 -m unittest discover -s tests`

What already exists and what is missing: [RESEARCH.md](RESEARCH.md).
