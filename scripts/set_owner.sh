#!/usr/bin/env bash
# Replace the OWNER placeholder with your GitHub user or organisation name.
# Usage: bash scripts/set_owner.sh <github-username>
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: $0 <github-username>"; exit 1; }
cd "$(dirname "$0")/.."
grep -rl --exclude-dir=.git "OWNER" README.md scripts/templates CITATION.cff pyproject.toml presentation report 2>/dev/null \
  | xargs sed -i.bak "s/OWNER/$1/g"
find . -name "*.bak" -delete
echo "Replaced OWNER with $1"
