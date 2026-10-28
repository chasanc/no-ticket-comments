# no-ticket-comments

AI coding agents paste ticket ids, review findings, and long recaps into code comments. Those notes go stale, and the next reader has no ticket open. Ticket IDs belong in commits, branches, and pull requests. A code comment is a short why, or nothing.

This hook enforces that in Claude Code and Cursor. It injects `hooks/RULES.md` at session start. An edit that adds a comment containing a configured ticket ID, or a new comment block longer than the configured limit, is rejected. Only lines the edit introduces count.

On Claude Code the edit is blocked before it is written. On Cursor the edit lands, then the agent is sent back to remove it before the turn ends.

## Install

```
/plugin install no-ticket-comments --marketplace chasanc/no-ticket-comments
```

## Configure

Claude Code asks for these when the plugin is enabled. Change them later in `/config`.

- `ticket_prefixes`: comma-separated tracker keys, such as `ENG,OPS`. The default `PROJ,TASK` is a placeholder.
- `max_comment_lines`: largest new comment block allowed. Default `2`.

Cursor reads the same values from the environment: `TICKET_PREFIXES` and `MAX_COMMENT_LINES`. When a Claude Code plugin setting is present, it wins.
