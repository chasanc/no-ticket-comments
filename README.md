# no-ticket-comments

No ticket numbers in code comments.

AI coding agents explain a change by pasting a Jira-style ticket id (`PROJ-123`), a review finding, or a long recap into the source. Those comments go stale: the ticket is closed, the tracker gets replaced, and the next reader has no ticket open. Ticket IDs belong in commits, branches, and pull requests. A code comment is a short why, or nothing.

This repository is a hook for Claude Code and Cursor that enforces that. Ticket IDs stay allowed in commits, branches, pull requests, and Markdown.

Two parts, one script (`plugin/hooks/no-ticket-comments.py`):

- **Rule** (`plugin/hooks/RULES.md`), injected into every session at start.
- **Enforcement**: an edit that adds a comment containing a ticket ID, or a new comment block longer than 2 lines, is rejected. Only lines the edit introduces count; existing comments are left alone.

| | Claude Code | Cursor |
|---|---|---|
| Rule injected | SessionStart | sessionStart |
| Enforcement | PreToolUse: the edit is **blocked** before it is written | afterFileEdit records it; at `stop` the agent is sent back to remove it (Cursor has no pre-edit hook) |

## Install: Claude Code

From a shell:

```
claude plugin marketplace add chasanc/no-ticket-comments
claude plugin install no-ticket-comments@no-ticket-comments
```

Or from inside a session (Claude Code v2.1.275 or later):

```
/plugin install no-ticket-comments --marketplace chasanc/no-ticket-comments
```

Restart the session. On enable, Claude Code asks for ticket prefixes. `PROJ` and `TASK` are placeholders; replace them with your tracker keys. If this account already has the rule in `CLAUDE.md` or this hook in `settings.json`, remove those so it does not run twice.

To try a local checkout instead of GitHub, use `/plugin marketplace add /path/to/no-ticket-comments`.

## Install: Cursor

```
git clone https://github.com/chasanc/no-ticket-comments.git
cd no-ticket-comments
./install-cursor.sh
```

Copies the script to `~/.cursor/hooks/no-ticket-comments/` and merges `cursor/hooks.json` into `~/.cursor/hooks.json` (backup in `hooks.json.bak`). Needs `jq`. Restart Cursor; the **Hooks** output channel shows runs and errors.

Cursor has no plugin settings dialog. Set prefixes in the environment Cursor is launched with, or change the defaults at the top of the script before running the installer.

## Configure

Claude Code stores these in plugin settings (`/config`):

- `ticket_prefixes`: comma-separated ticket keys. Default `PROJ,TASK`.
- `max_comment_lines`: largest new comment block allowed. Default `2`.

The hook also reads environment variables, which is how Cursor is configured. A Claude Code plugin setting wins when both are set.

- `TICKET_PREFIXES`
- `MAX_COMMENT_LINES`

## Test

```
python3 tests/test_hook.py
```

Requires `python3` on PATH (macOS/Linux). Checked file types: JS/TS, Python, SQL, shell, YAML, Go, Java, Kotlin, C#, Rust, PHP, CSS, Vue/Svelte/Astro. Python docstrings are not checked.

## License

[MIT](LICENSE)
