#!/usr/bin/env python3
"""Keep ticket IDs and long comment blocks out of AI-written code.

One script for both hosts, dispatched on hook_event_name:
  Claude Code  SessionStart -> inject RULES.md;  PreToolUse (Edit|Write|MultiEdit) -> deny the edit.
  Cursor       sessionStart -> inject RULES.md;  afterFileEdit -> record findings;  stop -> send the agent back to fix them.
Cursor has no documented pre-edit hook, so there the edit lands first and is cleaned up before the turn ends.
Only lines an edit introduces count; existing comments the edit merely carries along are left alone.
"""
import json
import os
import re
import sys
import tempfile

def setting(plugin_key, env_key, default):
    for key in (plugin_key, env_key):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return default


PREFIXES = [p.strip() for p in setting(
    "CLAUDE_PLUGIN_OPTION_TICKET_PREFIXES", "TICKET_PREFIXES", "PROJ,TASK").split(",") if p.strip()]
TICKET = re.compile(r"\b(?:" + "|".join(map(re.escape, PREFIXES)) + r")-\d+\b")
try:
    MAX_NEW_COMMENT_RUN = int(setting(
        "CLAUDE_PLUGIN_OPTION_MAX_COMMENT_LINES", "MAX_COMMENT_LINES", "2"))
except ValueError:
    MAX_NEW_COMMENT_RUN = 2

HERE = os.path.dirname(os.path.realpath(__file__))
STATE_DIR = os.path.join(tempfile.gettempdir(), "no-ticket-comments")
GUIDANCE = (
    "Code comments must not cite tickets, acceptance criteria, review findings or change history; "
    "those go in the commit message or PR description. A comment is at most "
    f"{MAX_NEW_COMMENT_RUN} lines of non-obvious why, written for a reader with no ticket open; usually none."
)

C_LIKE = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".cs", ".rs", ".php",
          ".css", ".scss", ".vue", ".svelte", ".astro", ".sql"}
HASH = {".py", ".sh", ".bash", ".rb", ".yml", ".yaml", ".tf", ".toml"}
HTML = {".vue", ".svelte", ".astro", ".html"}


def comment_patterns(ext):
    if ext in HASH:
        return re.compile(r"^\s*#(?!!)"), re.compile(r"\s#\s")
    starts = [r"//", r"/\*", r"\*"]
    inline = [r"(?:^|\s)//", r"(?:^|\s)/\*"]
    if ext == ".sql":
        starts.append(r"--")
        inline.append(r"\s--\s")
    if ext in HTML:
        starts.append(r"<!--")
        inline.append(r"<!--")
    return re.compile(r"^\s*(?:" + "|".join(starts) + ")"), re.compile("|".join(inline))


def inline_comment(line, inline):
    for m in inline.finditer(line):
        before = line[:m.start()]
        if all(before.count(q) % 2 == 0 for q in "\"'`"):
            return m
    return None


def violations(old, new, line_start, inline):
    old_lines = {l.strip() for l in old.splitlines()}
    found, run = [], []
    for line in new.splitlines() + [""]:
        is_new = line.strip() not in old_lines
        starts = line_start.match(line)
        if starts:
            run.append((line, is_new))
        else:
            fresh = [l for l, n in run if n]
            if len(fresh) > MAX_NEW_COMMENT_RUN:
                found.append(f"{len(fresh)}-line comment block starting: {fresh[0].strip()}")
            run = []
        if not is_new:
            continue
        m = starts or inline_comment(line, inline)
        if m and TICKET.search(line, m.start()):
            found.append(f"ticket reference in comment: {line.strip()}")
    return found


def check(path, pairs):
    ext = os.path.splitext(path)[1].lower()
    if ext not in C_LIKE | HASH:
        return []
    line_start, inline = comment_patterns(ext)
    return [f for old, new in pairs for f in violations(old, new, line_start, inline)]


def claude_pairs(tool_input, path):
    if "edits" in tool_input:
        return [(e.get("old_string", ""), e.get("new_string", "")) for e in tool_input["edits"]]
    if "content" in tool_input:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                old = f.read()
        except OSError:
            old = ""
        return [(old, tool_input["content"])]
    return [(tool_input.get("old_string", ""), tool_input.get("new_string", ""))]


def rules():
    with open(os.path.join(HERE, "RULES.md"), encoding="utf-8") as f:
        return f.read()


def state_file(data):
    return os.path.join(STATE_DIR, re.sub(r"[^\w-]", "_", data.get("conversation_id") or "default") + ".txt")


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name", "")
    out = None

    if event == "SessionStart":
        out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": rules()}}
    elif event == "sessionStart":
        out = {"additional_context": rules()}
    elif event == "PreToolUse":
        tool_input = data.get("tool_input", {})
        path = tool_input.get("file_path", "")
        found = check(path, claude_pairs(tool_input, path))
        if found:
            out = {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Blocked by no-ticket-comments hook:\n- " + "\n- ".join(found[:5])
                + "\n" + GUIDANCE + " Rewrite the edit without them.",
            }}
    elif event == "afterFileEdit":
        path = data.get("file_path", "")
        found = check(path, [(e.get("old_string", ""), e.get("new_string", "")) for e in data.get("edits", [])])
        if found:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(state_file(data), "a", encoding="utf-8") as f:
                f.writelines(f"{path}: {item}\n" for item in found)
    elif event == "stop":
        path = state_file(data)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                found = f.read().strip()
            os.remove(path)
            out = {"followup_message": "Your edits added comments that break the comment rule:\n" + found
                   + "\n" + GUIDANCE + " Remove or shorten each of them now, then stop."}

    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    main()
