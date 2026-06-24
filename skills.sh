#!/usr/bin/env bash
# Install skills from this repo into ~/.claude/skills/
# Usage: bash skills.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="${HOME}/.claude/skills"
mkdir -p "$SKILLS_DIR"

count=0
for skill_dir in "$REPO_DIR"/*/; do
  skill_file="$skill_dir/SKILL.md"
  if [ ! -f "$skill_file" ]; then
    continue
  fi
  skill_name="$(basename "$skill_dir")"
  dest="$SKILLS_DIR/$skill_name.md"
  # Resolve <skill-dir> placeholder to the actual directory of this skill
  sed "s|<skill-dir>|${skill_dir%/}|g" "$skill_file" > "$dest"
  echo "✓ $skill_name"
  count=$((count + 1))
done

echo ""
echo "$count skills installed to $SKILLS_DIR"
