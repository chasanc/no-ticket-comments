## Code comments

- Never put ticket IDs, acceptance-criteria or review-finding references, or change history ("used to", "now", "v3:", "after the switch") in code, JSDoc or test comments. Ticket IDs belong only in commit messages, branch names and PR descriptions.
- Default to no comment. When one is needed, it is one short line of non-obvious *why*, written for a reader who has never seen the ticket, not notes for a future agent.
- This overrides "match the surrounding comment density": existing ticket comments in a file are debt, not a style to copy.
- The no-ticket-comments hook enforces this. If it blocks or flags an edit, drop or shorten the comment; don't work around it.
