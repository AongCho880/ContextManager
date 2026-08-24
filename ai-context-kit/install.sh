#!/usr/bin/env bash
# Install the AI context kit into a project.
#
#   ./install.sh /path/to/project
#   ./install.sh /path/to/project --no-stubs    # skip CLAUDE.md / GEMINI.md / copilot stubs
#
# Never overwrites an existing file. Anything already there is reported and left alone — a re-run
# must never wipe live state.

set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-}"
STUBS=yes
[[ "${2:-}" == "--no-stubs" ]] && STUBS=no

if [[ -z "$TARGET" ]]; then
  echo "usage: $0 /path/to/project [--no-stubs]" >&2
  exit 1
fi
[[ -d "$TARGET" ]] || { echo "not a directory: $TARGET" >&2; exit 1; }
[[ "$(cd "$TARGET" && pwd)" == "$KIT" ]] && { echo "refusing to install the kit into itself" >&2; exit 1; }

added=(); kept=()

place() {  # place <src> <dst>
  local src="$KIT/$1" dst="$TARGET/$2"
  if [[ -e "$dst" ]]; then kept+=("$2"); return; fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  added+=("$2")
}

place "START-HERE.md"                "START-HERE.md"
place "AGENTS.md"                    "AGENTS.md"
place "context/current-state.md"     "context/current-state.md"
place "context/handoff.md"           "context/handoff.md"
place "context/decisions.md"         "context/decisions.md"
place "context/session-log.md"       "context/session-log.md"
place "context/verified-facts.md"    "context/verified-facts.md"
place "context/tools/ctx_check.py"   "context/tools/ctx_check.py"
mkdir -p "$TARGET/context/archive"
chmod +x "$TARGET/context/tools/ctx_check.py" 2>/dev/null || true

if [[ "$STUBS" == yes ]]; then
  place "CLAUDE.md"                       "CLAUDE.md"
  place "GEMINI.md"                       "GEMINI.md"
  place ".github/copilot-instructions.md" ".github/copilot-instructions.md"
fi

# Keep transient files out of version control, where git is in play.
if [[ -d "$TARGET/.git" || -f "$TARGET/.gitignore" ]]; then
  if ! grep -qs "^\.ctx_check_state\.json$" "$TARGET/.gitignore"; then
    printf '\n# AI context kit\ncontext/.lock\n.ctx_check_state.json\n' >> "$TARGET/.gitignore"
    added+=(".gitignore (appended)")
  fi
fi

echo "Installed into $TARGET"
if [[ ${#added[@]} -gt 0 ]]; then printf '  added  %s\n' "${added[@]}"; fi
if [[ ${#kept[@]}  -gt 0 ]]; then printf '  kept   %s (already existed, not touched)\n' "${kept[@]}"; fi

cat <<'EOF'

Now open any AI in this project and say:

    Read START-HERE.md and follow it.

It will ask you for a scan level, then take it from there.

First time here? Fill in the project name, working language, and build/test commands in AGENTS.md
first — or let the AI ask you for them. And if this project is not in git yet, `git init` it;
most of what can go wrong is recoverable with history and painful without it.
EOF
