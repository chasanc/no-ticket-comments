#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "plugin", "hooks", "no-ticket-comments.py")


def run(payload, **env):
    out = subprocess.run([HOOK], input=json.dumps(payload), capture_output=True, text=True, check=True,
                         env={**os.environ, **env}).stdout
    return json.loads(out) if out.strip() else None


def edit(path, old, new):
    return {"hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": path, "old_string": old, "new_string": new}}


def denied(out):
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


class ClaudeCode(unittest.TestCase):
    def test_ticket_comment_denied(self):
        self.assertTrue(denied(run(edit("a.ts", "x", "// PROJ-12: why\nx"))))
        self.assertTrue(denied(run(edit("a.ts", "x", "x; // TASK-3 fix"))))
        self.assertTrue(denied(run(edit("a.py", "x", "x = 1  # PROJ-77 sync"))))

    def test_long_block_denied(self):
        self.assertTrue(denied(run(edit("a.ts", "x", "/**\n * a\n * b\n */\nx"))))

    def test_allowed(self):
        old = "// PROJ-1 old note\n// line two\n// line three\nx"
        new = old + "\ny; // capped at 200\nconst u = 'https://example.test/PROJ-9';\nclass C { #c = 1 }"
        self.assertIsNone(run(edit("a.ts", old, new)))
        self.assertIsNone(run(edit("CLAUDE.md", "", "## Roles (PROJ-1352)")))

    def test_marker_inside_string_allowed(self):
        self.assertIsNone(run(edit("a.py", "x", 'payload = "x = 1  # PROJ-77 sync"')))
        self.assertIsNone(run(edit("a.ts", "x", "const s = 'a // PROJ-1 b';")))

    def test_prefix_override(self):
        self.assertIsNone(run(edit("a.ts", "x", "// PROJ-12\nx"), TICKET_PREFIXES="ABC"))
        self.assertTrue(denied(run(edit("a.ts", "x", "// ABC-12\nx"), TICKET_PREFIXES="ABC")))

    def test_plugin_option_wins_over_env(self):
        self.assertTrue(denied(run(
            edit("a.ts", "x", "// ABC-12\nx"),
            TICKET_PREFIXES="PROJ", CLAUDE_PLUGIN_OPTION_TICKET_PREFIXES="ABC")))

    def test_session_start_injects_rules(self):
        out = run({"hook_event_name": "SessionStart"})
        self.assertIn("Code comments", out["hookSpecificOutput"]["additionalContext"])


class Cursor(unittest.TestCase):
    def test_after_edit_then_stop_asks_for_fix_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = {"conversation_id": "c1"}
            run({**base, "hook_event_name": "afterFileEdit", "file_path": "/w/a.ts",
                 "edits": [{"old_string": "x", "new_string": "// PROJ-5 note\nx"}]}, TMPDIR=tmp)
            out = run({**base, "hook_event_name": "stop", "status": "completed"}, TMPDIR=tmp)
            self.assertIn("/w/a.ts: ticket reference", out["followup_message"])
            self.assertIsNone(run({**base, "hook_event_name": "stop", "status": "completed"}, TMPDIR=tmp))

    def test_clean_edit_stops_quietly(self):
        with tempfile.TemporaryDirectory() as tmp:
            run({"conversation_id": "c2", "hook_event_name": "afterFileEdit", "file_path": "/w/a.ts",
                 "edits": [{"old_string": "x", "new_string": "y"}]}, TMPDIR=tmp)
            self.assertIsNone(run({"conversation_id": "c2", "hook_event_name": "stop"}, TMPDIR=tmp))

    def test_session_start_injects_rules(self):
        self.assertIn("Code comments", run({"hook_event_name": "sessionStart"})["additional_context"])


if __name__ == "__main__":
    unittest.main()
