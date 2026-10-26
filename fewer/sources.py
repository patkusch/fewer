"""Merge Claude Code and Codex CLI activity into one Timeline.

Format notes for the Codex reader.
VERIFIED (openai/codex source, codex-rs/rollout recorder.rs + protocol.rs, read via gh api 2026-10-26):
  - rollouts live under ~/.codex/sessions/ and are named rollout-<timestamp>-<id>.jsonl
    (the docs example is flat; newer builds nest YYYY/MM/DD, so we walk the whole tree);
  - every line is written with a "timestamp" string plus the flattened rollout item;
  - the event names user_message and agent_message exist, and user_message carries "message".
ASSUMED (not seen on this machine, ~/.codex/sessions does not exist here; no real logs checked):
  - the item shape is {"timestamp", "type", "payload"} with type in session_meta /
    response_item / event_msg / turn_context, and payload["type"] naming the event
    (user_message, agent_message, function_call, function_call_output, reasoning, ...);
  - session_meta payload carries "id"; if absent we use the uuid from the file name.
A human prompt is an event_msg/user_message. Any other event or response item counts as
agent activity, except the session header and turn_context (they are written at startup).
Turn rules are the same as fewer.transcripts (gap cap, human cap).
"""
import json
import os
import re

from .model import Timeline
from .transcripts import _expand, _to_epoch, _ts, load_timeline, turns_from_events

_NOT_ACTIVITY = ("session_meta", "turn_context")
_UUID = re.compile(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\.jsonl$")


def read_codex_events(path):
    """Yield (session, time, is_prompt) from one Codex rollout file, skipping bad lines."""
    m = _UUID.search(os.path.basename(path))
    sid = "codex:" + (m.group(1) if m else os.path.basename(path))
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            kind = d.get("type")
            payload = d.get("payload") if isinstance(d.get("payload"), dict) else {}
            if kind == "session_meta":
                if isinstance(payload.get("id"), str):
                    sid = "codex:" + payload["id"]
                continue
            if kind in _NOT_ACTIVITY or not isinstance(kind, str):
                continue
            t = _ts(d.get("timestamp"))
            if t is None:
                continue
            yield sid, t, (kind == "event_msg" and payload.get("type") == "user_message")


def load_codex(root, since=None):
    cut = _to_epoch(since)
    events = []
    for f in _expand(root):
        if not os.path.basename(f).startswith("rollout-"):
            continue
        try:
            events.extend(read_codex_events(f))
        except OSError:
            continue
    if cut is not None:
        events = [e for e in events if e[1] >= cut]
    return Timeline(turns_from_events(events))


def load_all(root_claude="~/.claude/projects", root_codex="~/.codex/sessions", since=None):
    """Claude Code + Codex CLI on one Timeline. Missing folders are skipped."""
    turns = []
    if root_claude:
        turns += load_timeline(os.path.expanduser(os.fspath(root_claude)), since).turns
    if root_codex:
        turns += load_codex(os.path.expanduser(os.fspath(root_codex)), since).turns
    turns.sort(key=lambda x: (x.start, x.end))
    return Timeline(turns)
