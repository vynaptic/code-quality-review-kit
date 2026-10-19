#!/usr/bin/env bash
# Builds a throwaway git repository from baseline/ + change/, installs the kit into it,
# and runs both scanners so you can see the repo-consistency logic and the Convention
# Profile without any AI tool. Then open the repo in Devin / Codex / Claude Code / Droid and
# ask for a review; compare with EXPECTED.md.
#
#   examples/java-sample/try.sh            # prints the scanner output and the temp repo path
#   KEEP=1 examples/java-sample/try.sh     # keep the temp repo for manual use
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
kit="$(cd "$here/../.." && pwd)"
work="$(mktemp -d "${TMPDIR:-/tmp}/cqr-sample.XXXXXX")"

echo "== temp repository: $work"
cp -R "$here/baseline/." "$work/"
cp -R "$kit/repo/." "$work/"
git -C "$work" init -q -b main
git -C "$work" -c user.name=sample -c user.email=sample@example.com add -A
git -C "$work" -c user.name=sample -c user.email=sample@example.com commit -q -m "baseline with conventions + review kit"
git -C "$work" checkout -q -b feature/refunds
cp -R "$here/change/." "$work/"
git -C "$work" add -A

echo
echo "== Convention Profile (scripts/scan_conventions.py)"
python3 "$work/.agents/skills/code-quality-review/scripts/scan_conventions.py" --root "$work"

echo
echo "== Naming pre-scan (scripts/scan_names.py --base main)"
(cd "$work" && python3 .agents/skills/code-quality-review/scripts/scan_names.py --base main)

echo
if [ "${KEEP:-0}" = "1" ]; then
  echo "== kept: $work  (branch feature/refunds has the change staged; base is main)"
else
  rm -rf "$work"
  echo "== temp repository removed (set KEEP=1 to keep it)"
fi
