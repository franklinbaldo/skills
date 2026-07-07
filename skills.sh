#!/usr/bin/env bash
# Install skills from this repo into ~/.claude/skills/
# Usage: bash skills.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="${SKILLS_DIR:-${HOME}/.claude/skills}"
mkdir -p "$SKILLS_DIR"

count=0
for skill_dir in "$REPO_DIR"/*/; do
  skill_file="$skill_dir/SKILL.md"
  if [ ! -f "$skill_file" ]; then
    continue
  fi
  skill_name="$(basename "$skill_dir")"
  dest="$SKILLS_DIR/$skill_name"

  # Remove legacy flat install from the old scheme, if present
  rm -f "$SKILLS_DIR/$skill_name.md"

  # Replace any previous directory install with a fresh copy of the
  # whole skill directory (SKILL.md, references/, scripts/, etc.)
  rm -rf "$dest"
  cp -R "${skill_dir%/}" "$dest"

  # Resolve <skill-dir> placeholder to the installed directory,
  # since bundled files now live there. Avoid `sed -i` (GNU and BSD
  # sed take incompatible flags for it); redirect to a temp file instead.
  sed "s|<skill-dir>|${dest}|g" "$dest/SKILL.md" > "$dest/SKILL.md.tmp"
  mv "$dest/SKILL.md.tmp" "$dest/SKILL.md"

  echo "✓ $skill_name"
  count=$((count + 1))
done

echo ""
echo "$count skills installed to $SKILLS_DIR"
