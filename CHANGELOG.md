# Changelog

All notable changes to this project are listed here, newest first.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `fewer --version` prints the version.

## [0.1.0] - 2026-10-26

First version. It answers "are you running too many agents?" from your own Claude Code sessions.

- Reads your transcripts into a timeline and works out how many agents ran at once and how often you switched between them.
- Recommends how many agents to run, and shows how the answer changes if the agents are faster or slower.
- A range for the cost of each switch (30 seconds, 2 minutes or 5 minutes), because the 2-minute figure is an assumption, not a measurement.
- Shows which agents are waiting on you, and for how long.
- A one-page HTML report with the verdict, daily charts, weekly switches and a what-if table, and a one-page hand-off you can send with a feedback tracker.
- A short write-up of what already exists and what is missing (`RESEARCH.md`).
