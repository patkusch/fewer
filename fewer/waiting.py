"""Which agent sessions are waiting on the human right now, and for how long."""
import json
import os
import time

from .transcripts import _expand, _ts

RECENT = 6 * 3600        # only sessions touched in the last 6 hours
PERMISSION_GRACE = 20    # a tool call unanswered this long is waiting for approval
SNIPPET = 120


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                        and isinstance(c.get("text"), str))
    return ""


def _snippet(text):
    text = " ".join(text.split())
    return text if len(text) <= SNIPPET else text[:SNIPPET - 3] + "..."


def _scan(path):
    """Return (session, project, last_event_time, last_event_dict) or None."""
    last = last_t = sid = cwd = None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(d, dict):
                    continue
                if isinstance(d.get("cwd"), str) and d["cwd"]:
                    cwd = d["cwd"]
                if d.get("type") not in ("user", "assistant") or d.get("isSidechain"):
                    continue
                t = _ts(d.get("timestamp"))
                if t is None:
                    continue
                if isinstance(d.get("sessionId"), str):
                    sid = d["sessionId"]
                last, last_t = d, t
    except OSError:
        return None
    if last is None:
        return None
    sid = sid or os.path.splitext(os.path.basename(path))[0]
    folder = os.path.basename(cwd.rstrip("/\\")) if cwd else os.path.basename(os.path.dirname(path))
    return sid, folder, last_t, last


def _classify(d, age):
    """Return (reason, text) if the human is being waited on, else None."""
    if d.get("type") != "assistant":
        return None
    msg = d.get("message") if isinstance(d.get("message"), dict) else {}
    content = msg.get("content")
    text = _text_of(content)
    tools = [c for c in content if isinstance(c, dict) and c.get("type") == "tool_use"] \
        if isinstance(content, list) else []
    if tools:
        if any(c.get("name") == "AskUserQuestion" for c in tools):
            return "asked a question", text
        if age >= PERMISSION_GRACE:
            return "needs permission", text
        return None
    if msg.get("stop_reason") == "end_turn" or (text and msg.get("stop_reason") is None):
        if msg.get("stop_reason") not in (None, "end_turn"):
            return None
        if text.rstrip().endswith("?"):
            return "asked a question", text
        return "finished", text
    return None


def waiting(paths, now=None):
    now = time.time() if now is None else now
    rows = []
    for f in _expand(paths):
        if not f.endswith(".jsonl"):
            continue
        got = _scan(f)
        if got is None:
            continue
        sid, project, t, d = got
        age = now - t
        if age < 0 or age > RECENT:
            continue
        hit = _classify(d, age)
        if hit is None:
            continue
        reason, text = hit
        rows.append({"session": sid, "project": project, "waiting_seconds": int(age),
                     "reason": reason, "last_agent_text_snippet": _snippet(text)})
    rows.sort(key=lambda r: -r["waiting_seconds"])
    return rows


def _dur(s):
    if s < 60:
        return "under a minute"
    m = s // 60
    if m < 60:
        return f"{m} min"
    return f"{m // 60} h {m % 60} min"


def format_waiting(rows):
    if not rows:
        return ["No agents are waiting for you."]
    n = len(rows)
    top = rows[0]
    who = "1 agent is" if n == 1 else f"{n} agents are"
    return [f"{who} waiting for you. Longest: {_dur(top['waiting_seconds'])}, "
            f"in {top['project']}: {top['reason']}."]
