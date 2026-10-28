#!/usr/bin/env bash
# Installs the hook for Cursor at user level (~/.cursor); safe to re-run.
set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"
dest="$HOME/.cursor/hooks/no-ticket-comments"
cfg="$HOME/.cursor/hooks.json"

mkdir -p "$dest"
cp "$root/plugin/hooks/no-ticket-comments.py" "$root/plugin/hooks/RULES.md" "$dest/"
chmod +x "$dest/no-ticket-comments.py"

[ -f "$cfg" ] || echo '{"version":1,"hooks":{}}' > "$cfg"
cp "$cfg" "$cfg.bak"
jq --slurpfile add "$root/cursor/hooks.json" '
  reduce ($add[0].hooks | to_entries[]) as $e (.;
    .hooks[$e.key] = ((.hooks[$e.key] // []) | map(select(.command != $e.value[0].command))) + $e.value)
' "$cfg.bak" > "$cfg"

echo "Installed to $dest and merged into $cfg (previous version: $cfg.bak). Restart Cursor."
