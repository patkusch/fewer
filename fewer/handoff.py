"""One structured HTML hand-off page, plus a reader for the feedback it produces.

build_handoff() returns a single self-contained page (no network requests).
The reviewer reads it, taps agree / disagree / unsure, and copies a small JSON
block. parse_feedback() turns that JSON into plain-English markdown for the agent.
"""
from __future__ import annotations

import html
import json

_SECTIONS = [
    ("decisions", "Key decisions"),
    ("questions", "Open questions"),
    ("examples", "Examples"),
    ("diff", "Git diff"),
]


def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _item_text(item) -> str:
    """Items may be plain strings or dicts with 'text' (and optional 'title')."""
    if isinstance(item, dict):
        title = item.get("title") or ""
        text = item.get("text") or item.get("body") or ""
        out = ""
        if title:
            out += f"<strong>{_e(title)}</strong> "
        return out + _e(text)
    return _e(item)


def _controls(item_id: str, with_note: bool) -> str:
    buttons = "".join(
        f'<button type="button" class="choice" data-choice="{c}" aria-pressed="false">{c}</button>'
        for c in ("agree", "disagree", "unsure")
    )
    note = (
        '<textarea class="note" rows="2" placeholder="Optional note"></textarea>'
        if with_note
        else ""
    )
    return f'<div class="controls" role="group">{buttons}</div>{note}'


def _items(kind: str, items, with_note: bool) -> str:
    if not items:
        return '<p class="empty">Nothing here.</p>'
    rows = []
    for i, item in enumerate(items, 1):
        item_id = f"{kind}-{i}"
        rows.append(
            f'<li class="item" data-id="{item_id}"><div class="text">{_item_text(item)}</div>'
            f"{_controls(item_id, with_note)}</li>"
        )
    return '<ol class="items">' + "".join(rows) + "</ol>"


def _examples(examples) -> str:
    if not examples:
        return '<p class="empty">Nothing here.</p>'
    out = []
    for i, ex in enumerate(examples, 1):
        if isinstance(ex, dict):
            title = ex.get("title") or f"Example {i}"
            body = ex.get("text") or ex.get("body") or ex.get("code") or ""
        else:
            title, body = f"Example {i}", ex
        out.append(
            f'<div class="example"><div class="ex-title">{_e(title)}</div>'
            f"<pre>{_e(body)}</pre></div>"
        )
    return "".join(out)


def _diff(diff_text: str) -> str:
    if not diff_text or not diff_text.strip():
        return '<p class="empty">No changes.</p>'
    lines = []
    for line in str(diff_text).splitlines():
        if line.startswith(("+++", "---", "diff ", "index ")):
            cls = "meta"
        elif line.startswith("@@"):
            cls = "hunk"
        elif line.startswith("+"):
            cls = "add"
        elif line.startswith("-"):
            cls = "del"
        else:
            cls = "ctx"
        lines.append(f'<span class="l {cls}">{_e(line) or "&nbsp;"}</span>')
    return '<pre class="diff">' + "".join(lines) + "</pre>"


_CSS = """
:root{--bg:#fff;--fg:#1c1c1e;--muted:#6b6b70;--card:#f5f5f7;--line:#d8d8de;--accent:#2457d6;
--add-bg:#e6f6ea;--add-fg:#14532d;--del-bg:#fdeaea;--del-fg:#7f1d1d;--hunk:#5b5bd6}
@media (prefers-color-scheme:dark){:root{--bg:#121214;--fg:#ececf0;--muted:#9a9aa3;--card:#1c1c20;
--line:#33333a;--accent:#7aa2ff;--add-bg:#12301b;--add-fg:#a7f0ba;--del-bg:#3a1618;--del-fg:#ffb4b4;--hunk:#a5a5ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:16px}
h1{font-size:1.4rem;margin:.5rem 0 1rem}
h2{font-size:1.1rem;margin:0 0 .6rem}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:16px}
.items{padding-left:1.2rem;margin:0}
.item{margin-bottom:14px}
.controls{display:flex;gap:8px;margin-top:6px;flex-wrap:wrap}
.choice{font:inherit;min-height:40px;padding:0 14px;border:1px solid var(--line);border-radius:8px;
background:var(--bg);color:var(--fg);cursor:pointer}
.choice[aria-pressed=true]{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.note{width:100%;margin-top:6px;font:inherit;padding:8px;border:1px solid var(--line);border-radius:8px;
background:var(--bg);color:var(--fg)}
pre{margin:0;overflow-x:auto;font:13px/1.4 ui-monospace,monospace;white-space:pre-wrap;word-break:break-word}
.example{margin-bottom:10px}.ex-title{font-weight:600;margin-bottom:4px}
.example pre{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px}
.diff{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:6px 0}
.l{display:block;padding:0 10px}
.add{background:var(--add-bg);color:var(--add-fg)}.del{background:var(--del-bg);color:var(--del-fg)}
.hunk{color:var(--hunk)}.meta{color:var(--muted);font-weight:600}
.empty{color:var(--muted);margin:0}
.bar{position:sticky;bottom:0;background:var(--bg);border-top:1px solid var(--line);padding:10px 16px;
display:flex;gap:10px;align-items:center}
.bar button{font:inherit;min-height:44px;padding:0 18px;border-radius:8px;border:0;background:var(--accent);
color:var(--bg);cursor:pointer}
#status{color:var(--muted);font-size:.9rem}
"""

_JS = r"""
(function(){
  var seconds = {}, visible = {}, last = Date.now();
  var highlights = [], answers = {};
  function tick(){
    var now = Date.now(), dt = (now - last) / 1000; last = now;
    Object.keys(visible).forEach(function(k){ if(visible[k]) seconds[k] = (seconds[k]||0) + dt; });
  }
  var secs = document.querySelectorAll('section[data-section]');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function(entries){
      tick();
      entries.forEach(function(en){ visible[en.target.getAttribute('data-name')] = en.isIntersecting; });
    }, {threshold: 0.4});
    secs.forEach(function(s){ io.observe(s); });
  }
  setInterval(tick, 1000);
  document.addEventListener('visibilitychange', function(){
    tick(); if (document.hidden) visible = {};
  });
  document.addEventListener('selectionchange', function(){
    var t = String(window.getSelection() || '').trim();
    if (t.length > 2 && highlights.indexOf(t) < 0) highlights.push(t.slice(0, 500));
  });
  function entry(id){ return answers[id] || (answers[id] = {id: id, choice: '', note: ''}); }
  document.querySelectorAll('.item').forEach(function(item){
    var id = item.getAttribute('data-id');
    item.querySelectorAll('.choice').forEach(function(b){
      b.addEventListener('click', function(){
        entry(id).choice = b.getAttribute('data-choice');
        item.querySelectorAll('.choice').forEach(function(o){
          o.setAttribute('aria-pressed', o === b ? 'true' : 'false');
        });
      });
    });
    var n = item.querySelector('.note');
    if (n) n.addEventListener('input', function(){ entry(id).note = n.value; });
  });
  function build(){
    tick();
    var viewed = Object.keys(seconds).map(function(k){
      return {section: k, seconds: Math.round(seconds[k])};
    });
    var out = Object.keys(answers).map(function(k){ return answers[k]; })
      .filter(function(a){ return a.choice || a.note; });
    return JSON.stringify({viewed: viewed, highlights: highlights, answers: out}, null, 2);
  }
  document.getElementById('copy').addEventListener('click', function(){
    var text = build(), st = document.getElementById('status');
    function done(ok){ st.textContent = ok ? 'Copied. Paste it to the agent.' : 'Copy failed: select the text below.'; 
      if(!ok){ var ta = document.getElementById('fallback'); ta.hidden = false; ta.value = text; ta.select(); } }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function(){ done(true); }, function(){ done(false); });
    } else { done(false); }
  });
  window.__fewerFeedback = build;
})();
"""


def build_handoff(title, decisions, questions, examples, diff_text) -> str:
    """Return one self-contained HTML page. Every input is escaped."""
    bodies = {
        "decisions": _items("decision", decisions, with_note=False),
        "questions": _items("question", questions, with_note=True),
        "examples": _examples(examples),
        "diff": _diff(diff_text),
    }
    sections = "".join(
        f'<section data-section="{key}" data-name="{_e(name)}"><h2>{_e(name)}</h2>{bodies[key]}</section>'
        for key, name in _SECTIONS
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light dark">'
        f"<title>{_e(title)}</title><style>{_CSS}</style></head><body><main>"
        f"<h1>{_e(title)}</h1>{sections}"
        '<textarea id="fallback" class="note" rows="8" hidden></textarea></main>'
        '<div class="bar"><button type="button" id="copy">Copy feedback</button>'
        '<span id="status"></span></div>'
        f"<script>{_JS}</script></body></html>"
    )


def _clean(value) -> str:
    return " ".join(str(value).split())


def _label(item_id: str) -> str:
    kind, _, num = str(item_id).rpartition("-")
    return f"{kind} {num}" if kind and num else _clean(item_id)


def parse_feedback(json_str: str) -> str:
    """Turn the copied feedback JSON into plain-English markdown for an agent."""
    try:
        data = json.loads(json_str)
    except (TypeError, ValueError):
        return "Feedback could not be read: it was not valid JSON."
    if not isinstance(data, dict):
        return "Feedback could not be read: expected a JSON object."

    lines = ["# Reviewer feedback", ""]

    viewed = [v for v in data.get("viewed") or [] if isinstance(v, dict)]
    viewed.sort(key=lambda v: -(v.get("seconds") or 0) if isinstance(v.get("seconds"), (int, float)) else 0)
    if viewed:
        top = viewed[0]
        lines.append(
            f"Spent longest on {_clean(top.get('section', '?'))} "
            f"({_clean(top.get('seconds', 0))} seconds)."
        )
        rest = [f"{_clean(v.get('section', '?'))} {_clean(v.get('seconds', 0))}s" for v in viewed[1:]]
        if rest:
            lines.append("Time elsewhere: " + ", ".join(rest) + ".")
    else:
        lines.append("No reading time was recorded.")
    lines.append("")

    answers = [a for a in data.get("answers") or [] if isinstance(a, dict)]
    groups = {"disagree": [], "unsure": [], "agree": [], "": []}
    for a in answers:
        choice = _clean(a.get("choice", "")).lower()
        groups.setdefault(choice, groups[""]).append(a)

    def fmt(a, verb):
        s = f"- {verb} {_label(a.get('id', '?'))}"
        note = _clean(a.get("note", ""))
        return s + (f": {note}" if note else "")

    lines.append("## Answers")
    shown = False
    for choice, verb in (("disagree", "Disagreed with"), ("unsure", "Unsure about"), ("agree", "Agreed with")):
        for a in groups[choice]:
            lines.append(fmt(a, verb))
            shown = True
    for a in groups[""]:
        if _clean(a.get("note", "")):
            lines.append(fmt(a, "Note on"))
            shown = True
    if not shown:
        lines.append("- No answers given.")
    lines.append("")

    highlights = [_clean(h) for h in data.get("highlights") or [] if _clean(h)]
    if highlights:
        lines.append("## Highlighted text")
        lines.extend(f'- "{h}"' for h in highlights)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
