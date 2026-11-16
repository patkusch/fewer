import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fewer import sources, transcripts

T0 = "2026-11-10T10:00:00Z"
EPOCH0 = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc).timestamp()


def write_lines(folder, name, lines):
    p = Path(folder) / name
    p.write_text("\n".join(l if isinstance(l, str) else json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    return str(p)


class Times(unittest.TestCase):
    def test_a_timestamp_is_read_with_or_without_the_Z_and_anything_else_is_nothing(self):
        self.assertEqual(transcripts._ts(T0), EPOCH0)
        self.assertEqual(transcripts._ts("2026-11-10T10:00:00+00:00"), EPOCH0)
        self.assertIsNone(transcripts._ts("yesterday"))
        self.assertIsNone(transcripts._ts(None))
        self.assertIsNone(transcripts._ts(12345))

    def test_a_cut_off_can_be_given_as_nothing_a_number_a_date_or_text(self):
        self.assertIsNone(transcripts._to_epoch(None))
        self.assertEqual(transcripts._to_epoch(100), 100.0)
        self.assertEqual(transcripts._to_epoch(1.5), 1.5)
        aware = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(transcripts._to_epoch(aware), EPOCH0)
        naive = datetime(2026, 11, 10, 10, 0)
        self.assertEqual(transcripts._to_epoch(naive), naive.timestamp(), "a date with no zone is read as local time")
        self.assertEqual(transcripts._to_epoch(T0), EPOCH0)
        self.assertIsNone(transcripts._to_epoch("not a date"))


class WhoTyped(unittest.TestCase):
    def test_only_a_person_typing_counts_as_a_prompt(self):
        human = transcripts._is_human_prompt
        self.assertTrue(human({"type": "user", "message": {"content": "do the thing"}}))
        self.assertTrue(human({"type": "user", "message": {"content": [{"type": "text", "text": "hi"}]}}))
        self.assertFalse(human({"type": "assistant", "message": {"content": "hi"}}))
        self.assertFalse(human({"type": "user", "isSidechain": True, "message": {"content": "hi"}}))

    def test_a_tool_result_is_the_agent_talking_to_itself_not_a_person(self):
        human = transcripts._is_human_prompt
        result = {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}
        self.assertFalse(human(result))
        mixed = {"type": "user", "message": {"content": [{"type": "text", "text": "x"}, {"type": "tool_result"}]}}
        self.assertFalse(human(mixed))

    def test_when_the_file_says_who_sent_it_that_wins(self):
        human = transcripts._is_human_prompt
        self.assertTrue(human({"type": "user", "origin": {"kind": "human"}, "message": {"content": [{"type": "tool_result"}]}}))
        self.assertFalse(human({"type": "user", "origin": {"kind": "task-notification"}, "message": {"content": "looks typed"}}))

    def test_odd_shapes_are_not_prompts_and_do_not_crash(self):
        human = transcripts._is_human_prompt
        self.assertFalse(human({"type": "user"}))
        self.assertFalse(human({"type": "user", "message": "plain string"}))
        self.assertFalse(human({"type": "user", "message": {"content": 5}}))
        self.assertFalse(human({"type": "user", "message": {"content": ["text", None]}}))


class ClaudeFile(unittest.TestCase):
    def test_bad_lines_side_chains_and_incomplete_records_are_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            path = write_lines(d, "s.jsonl", [
                "not json at all",
                "[1, 2]",
                {"type": "system", "sessionId": "a", "timestamp": T0},
                {"type": "user", "sessionId": "a", "timestamp": T0, "isSidechain": True},
                {"type": "user", "sessionId": "a", "timestamp": "garbage"},
                {"type": "user", "timestamp": T0, "message": {"content": "no session"}},
                {"type": "user", "sessionId": 7, "timestamp": T0},
                {"type": "user", "sessionId": "a", "timestamp": T0, "message": {"content": "hello"}},
                {"type": "assistant", "sessionId": "a", "timestamp": "2026-11-10T10:00:05Z"},
            ])
            events = list(transcripts.read_events(path))
        self.assertEqual(events, [("a", EPOCH0, True), ("a", EPOCH0 + 5, False)])

    def test_bytes_that_are_not_valid_text_do_not_stop_the_reading(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.jsonl"
            good = json.dumps({"type": "user", "sessionId": "a", "timestamp": T0, "message": {"content": "hi"}})
            p.write_bytes(b"\xff\xfe broken\n" + good.encode() + b"\n")
            self.assertEqual(list(transcripts.read_events(str(p))), [("a", EPOCH0, True)])


class CodexFile(unittest.TestCase):
    UUID = "0123abcd-0123-4abc-8def-0123456789ab"

    def test_the_session_name_comes_from_the_file_name_until_the_file_names_itself(self):
        with tempfile.TemporaryDirectory() as d:
            named = write_lines(d, f"rollout-2026-11-10T10-00-00-{self.UUID}.jsonl", [
                {"type": "event_msg", "timestamp": T0, "payload": {"type": "user_message"}},
            ])
            self.assertEqual(list(sources.read_codex_events(named)), [(f"codex:{self.UUID}", EPOCH0, True)])
            unnamed = write_lines(d, "rollout-odd.jsonl", [{"type": "event_msg", "timestamp": T0, "payload": {"type": "agent_message"}}])
            self.assertEqual(list(sources.read_codex_events(unnamed)), [("codex:rollout-odd.jsonl", EPOCH0, False)])
            renamed = write_lines(d, "rollout-x.jsonl", [
                {"type": "session_meta", "timestamp": T0, "payload": {"id": "inner-id"}},
                {"type": "event_msg", "timestamp": T0, "payload": {"type": "user_message"}},
            ])
            self.assertEqual(list(sources.read_codex_events(renamed)), [("codex:inner-id", EPOCH0, True)])

    def test_setup_records_and_unreadable_lines_are_not_activity(self):
        with tempfile.TemporaryDirectory() as d:
            path = write_lines(d, "rollout-a.jsonl", [
                "junk",
                [1],
                {"timestamp": T0},
                {"type": "turn_context", "timestamp": T0},
                {"type": 5, "timestamp": T0},
                {"type": "event_msg", "timestamp": "garbage", "payload": {"type": "user_message"}},
                {"type": "response_item", "timestamp": T0},
                {"type": "event_msg", "timestamp": T0, "payload": "not a dict"},
            ])
            events = list(sources.read_codex_events(path))
        self.assertEqual([(e[1], e[2]) for e in events], [(EPOCH0, False), (EPOCH0, False)])

    def test_only_rollout_files_are_read_and_a_cut_off_date_drops_older_activity(self):
        with tempfile.TemporaryDirectory() as d:
            write_lines(d, "rollout-a.jsonl", [
                {"type": "event_msg", "timestamp": T0, "payload": {"type": "user_message"}},
                {"type": "event_msg", "timestamp": "2026-11-12T10:00:00Z", "payload": {"type": "user_message"}},
            ])
            write_lines(d, "notes.jsonl", [{"type": "event_msg", "timestamp": T0, "payload": {"type": "user_message"}}])
            everything = sources.load_codex(d)
            recent = sources.load_codex(d, since="2026-11-11T00:00:00Z")
        starts = lambda tl: sorted(t.start for t in tl.turns)
        self.assertEqual(starts(everything)[0], EPOCH0)
        self.assertTrue(all(t.session.startswith("codex:rollout-a") for t in everything.turns), "notes.jsonl is not read")
        self.assertGreater(len(everything.turns), len(recent.turns))
        self.assertTrue(all(t.start >= datetime(2026, 11, 11, tzinfo=timezone.utc).timestamp() for t in recent.turns))


if __name__ == "__main__":
    unittest.main()
