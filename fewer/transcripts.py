"""Read Claude Code transcripts (jsonl) into a Timeline of agent and human turns."""
import json
import os
from datetime import datetime, timezone

from .model import Timeline, Turn

AGENT_GAP_CAP = 30 * 60   # an idle gap longer than this ends the agent turn
HUMAN_CAP = 10 * 60       # a human turn is never counted longer than this


def _ts(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _to_epoch(since):
    if since is None:
        return None
    if isinstance(since, (int, float)):
        return float(since)
    if isinstance(since, datetime):
        if since.tzinfo is None:
            return since.timestamp()
        return since.astimezone(timezone.utc).timestamp()
    return _ts(since)


def _is_human_prompt(d):
    if d.get("type") != "user" or d.get("isSidechain"):
        return False
    kind = (d.get("origin") or {}).get("kind")
    if kind is not None:
        return kind == "human"
    content = (d.get("message") or {}).get("content") if isinstance(d.get("message"), dict) else None
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(isinstance(c, dict) and c.get("type") == "text" for c in content) and not any(
            isinstance(c, dict) and c.get("type") == "tool_result" for c in content)
    return False


def read_events(path):
    """Yield (session, time, is_prompt) from one file, skipping bad lines."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict) or d.get("type") not in ("user", "assistant"):
                continue
            if d.get("isSidechain"):
                continue
            t = _ts(d.get("timestamp"))
            sid = d.get("sessionId")
            if t is None or not isinstance(sid, str):
                continue
            yield sid, t, _is_human_prompt(d)


def turns_from_events(events):
    """events: iterable of (session, time, is_prompt) -> list[Turn] sorted by start."""
    by_session = {}
    for sid, t, p in events:
        by_session.setdefault(sid, []).append((t, p))
    turns = []
    for sid, evs in by_session.items():
        evs.sort(key=lambda e: e[0])
        cur_start = None
        last = None
        closed = []   # (start, end)

        def close():
            if cur_start is not None:
                closed.append((cur_start, max(last, cur_start)))

        for t, p in evs:
            if p:
                close()
                cur_start, last = t, t
            elif cur_start is not None:
                if t - last > AGENT_GAP_CAP:
                    close()
                    cur_start = None
                else:
                    last = t
        close()
        prompts = sorted(t for t, p in evs if p)
        for s, e in closed:
            turns.append(Turn(sid, "agent", s, e))
        for s, e in closed:
            nxt = next((p for p in prompts if p > s), None)
            if nxt is None or nxt <= e:
                continue
            turns.append(Turn(sid, "human", e, min(nxt, e + HUMAN_CAP)))
    turns.sort(key=lambda x: (x.start, x.end))
    return turns


def _expand(paths):
    if isinstance(paths, (str, os.PathLike)):
        paths = [paths]
    out = []
    for p in paths:
        p = os.fspath(p)
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                out += [os.path.join(root, f) for f in files if f.endswith(".jsonl")]
        else:
            out.append(p)
    return sorted(out)


def load_timeline(paths, since=None):
    """Build a Timeline from files or directories. since: epoch, datetime or ISO string."""
    cut = _to_epoch(since)
    events = []
    for f in _expand(paths):
        try:
            events.extend(read_events(f))
        except OSError:
            continue
    if cut is not None:
        events = [e for e in events if e[1] >= cut]
    return Timeline(turns_from_events(events))
