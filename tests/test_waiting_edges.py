import json
import tempfile
import unittest
from pathlib import Path

from fewer import waiting

NOW = 1_800_000_000.0


def iso(seconds_ago):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(NOW - seconds_ago, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def assistant(ago, content, stop_reason="end_turn", **extra):
    return {"type": "assistant", "sessionId": "s1", "timestamp": iso(ago), "cwd": "/work/proj",
            "message": {"content": content, "stop_reason": stop_reason}, **extra}


def run(*events, name="s1.jsonl", sub=None):
    with tempfile.TemporaryDirectory() as d:
        folder = Path(d) / sub if sub else Path(d)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text("\n".join(json.dumps(e) if not isinstance(e, str) else e for e in events) + "\n", encoding="utf-8")
        return waiting.waiting([str(Path(d))], now=NOW)


class Text(unittest.TestCase):
    def test_text_is_taken_from_text_blocks_only_and_joined(self):
        self.assertEqual(waiting._text_of("plain"), "plain")
        content = [{"type": "text", "text": "one"}, {"type": "tool_use", "name": "X"}, {"type": "text", "text": "two"}, {"type": "text"}, "junk"]
        self.assertEqual(waiting._text_of(content), "one two")
        self.assertEqual(waiting._text_of(None), "")
        self.assertEqual(waiting._text_of(7), "")

    def test_a_long_message_is_squeezed_onto_one_line_and_cut_with_dots(self):
        self.assertEqual(waiting._snippet("a\n\n  b\tc"), "a b c")
        long = waiting._snippet("word " * 100)
        self.assertEqual(len(long), waiting.SNIPPET)
        self.assertTrue(long.endswith("..."))
        exactly = "x" * waiting.SNIPPET
        self.assertEqual(waiting._snippet(exactly), exactly)


class Classify(unittest.TestCase):
    def test_a_person_message_is_never_a_wait(self):
        self.assertIsNone(waiting._classify({"type": "user", "message": {"content": "hi"}}, 100))

    def test_asking_the_user_a_question_tool_counts_at_once_with_no_grace(self):
        d = assistant(1, [{"type": "text", "text": "Which one?"}, {"type": "tool_use", "name": "AskUserQuestion"}], stop_reason="tool_use")
        self.assertEqual(waiting._classify(d, 1), ("asked a question", "Which one?"))

    def test_other_tools_wait_for_permission_only_after_the_grace_period(self):
        d = assistant(0, [{"type": "tool_use", "name": "Bash"}], stop_reason="tool_use")
        self.assertIsNone(waiting._classify(d, waiting.PERMISSION_GRACE - 1))
        self.assertEqual(waiting._classify(d, waiting.PERMISSION_GRACE)[0], "needs permission")

    def test_a_finished_message_is_a_question_when_it_ends_with_one_and_finished_otherwise(self):
        q = assistant(0, [{"type": "text", "text": "Shall I go on?  "}])
        self.assertEqual(waiting._classify(q, 5)[0], "asked a question")
        done = assistant(0, [{"type": "text", "text": "All done."}])
        self.assertEqual(waiting._classify(done, 5), ("finished", "All done."))

    def test_a_message_with_no_stop_reason_but_some_text_counts_as_finished(self):
        d = assistant(0, "Here you go.", stop_reason=None)
        self.assertEqual(waiting._classify(d, 5), ("finished", "Here you go."))

    def test_an_agent_still_working_is_not_waiting(self):
        self.assertIsNone(waiting._classify(assistant(0, [{"type": "text", "text": "thinking"}], stop_reason="max_tokens"), 5))
        self.assertIsNone(waiting._classify(assistant(0, [], stop_reason=None), 5))
        self.assertIsNone(waiting._classify({"type": "assistant", "message": "odd"}, 5))


class Scan(unittest.TestCase):
    def test_the_last_real_message_decides_and_side_chains_and_bad_lines_are_ignored(self):
        rows = run(
            "garbage",
            assistant(300, [{"type": "text", "text": "first"}]),
            assistant(100, [{"type": "text", "text": "side work"}], isSidechain=True),
            {"type": "assistant", "sessionId": "s1", "timestamp": "garbage", "message": {"content": "x"}},
            {"type": "summary"},
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["waiting_seconds"], 300)
        self.assertEqual(rows[0]["last_agent_text_snippet"], "first")

    def test_the_project_is_the_last_folder_of_the_working_directory(self):
        self.assertEqual(run(assistant(60, [{"type": "text", "text": "done"}]))[0]["project"], "proj")
        e = assistant(60, [{"type": "text", "text": "done"}])
        e["cwd"] = "/work/trailing/"
        self.assertEqual(run(e)[0]["project"], "trailing")

    def test_without_a_working_directory_the_folder_the_file_sits_in_is_used_and_the_file_name_is_the_session(self):
        e = assistant(60, [{"type": "text", "text": "done"}])
        del e["cwd"], e["sessionId"]
        row = run(e, name="abc-123.jsonl", sub="my-project")[0]
        self.assertEqual(row["project"], "my-project")
        self.assertEqual(row["session"], "abc-123")

    def test_a_file_with_nothing_usable_in_it_is_skipped(self):
        self.assertEqual(run("junk", {"type": "summary"}), [])
        self.assertIsNone(waiting._scan("/does/not/exist.jsonl"))

    def test_sessions_older_than_six_hours_and_ones_from_the_future_are_left_out(self):
        self.assertEqual(run(assistant(waiting.RECENT + 1, [{"type": "text", "text": "old"}])), [])
        self.assertEqual(run(assistant(-60, [{"type": "text", "text": "clock skew"}])), [])
        self.assertEqual(len(run(assistant(waiting.RECENT - 1, [{"type": "text", "text": "ok"}]))), 1)

    def test_only_jsonl_files_are_read(self):
        self.assertEqual(run(assistant(60, [{"type": "text", "text": "done"}]), name="notes.txt"), [])


class Wording(unittest.TestCase):
    def test_durations_read_naturally(self):
        self.assertEqual(waiting._dur(5), "under a minute")
        self.assertEqual(waiting._dur(60), "1 min")
        self.assertEqual(waiting._dur(59 * 60), "59 min")
        self.assertEqual(waiting._dur(3600), "1 h 0 min")
        self.assertEqual(waiting._dur(3600 * 2 + 60 * 5), "2 h 5 min")

    def test_the_summary_names_how_many_and_the_longest_wait(self):
        self.assertEqual(waiting.format_waiting([]), ["No agents are waiting for you."])
        one = [{"waiting_seconds": 120, "project": "api", "reason": "finished"}]
        self.assertEqual(waiting.format_waiting(one), ["1 agent is waiting for you. Longest: 2 min, in api: finished."])
        two = one + [{"waiting_seconds": 30, "project": "web", "reason": "needs permission"}]
        self.assertTrue(waiting.format_waiting(two)[0].startswith("2 agents are waiting for you."))


if __name__ == "__main__":
    unittest.main()
