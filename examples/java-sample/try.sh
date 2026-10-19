#!/usr/bin/env bash
# Builds a throwaway git repository from baseline/ + change/, installs the kit into it,
# and checks both scanners so you can see the repo-consistency logic and the Convention
# Profile without any AI tool. Then open the repo in Devin / Codex / Claude Code / Droid and
# ask for a review; compare with EXPECTED.md.
#
#   examples/java-sample/try.sh            # prints the scanner output and the temp repo path
#   KEEP=1 examples/java-sample/try.sh     # keep the temp repo for manual use
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
kit="$(cd "$here/../.." && pwd)"
work="$(mktemp -d "${TMPDIR:-/tmp}/cqr-sample.XXXXXX")"
cleanup() {
  if [ "${KEEP:-0}" != "1" ]; then
    rm -rf "$work"
  fi
}
trap cleanup EXIT

# Keep disposable sample setup independent of the user's Git configuration.
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0
echo "== temp repository: $work"
cp -R "$here/baseline/." "$work/"
cp -R "$kit/repo/." "$work/"
git -C "$work" init -q -b main
git -C "$work" config commit.gpgsign false
git -C "$work" config core.hooksPath /dev/null
git -C "$work" -c user.name=sample -c user.email=sample@example.com add -A
git -C "$work" -c user.name=sample -c user.email=sample@example.com commit -q -m "baseline with conventions + review kit"
git -C "$work" checkout -q -b feature/refunds
cp -R "$here/change/." "$work/"
git -C "$work" add -A

echo
echo "== Baseline Convention Profile (scripts/scan_conventions.py --ref main)"
python3 "$work/.agents/skills/code-quality-review/scripts/scan_conventions.py" --root "$work" --ref main

echo
echo "== Naming pre-scan (scripts/scan_names.py --base main)"
(cd "$work" && python3 .agents/skills/code-quality-review/scripts/scan_names.py --base main)

echo
echo "== Checking expected violations and accepted baseline names"
python3 - "$work" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
scripts = root / ".agents/skills/code-quality-review/scripts"

def run(script, *args):
    output = subprocess.check_output([sys.executable, str(scripts / script), *args, "--format", "json"], cwd=root, text=True)
    return json.loads(output)

profile = run("scan_conventions.py", "--ref", "main")
assert profile["meta"]["snapshot"] == "commit", "Profile must use the committed baseline"
assert profile["log_facades"] == {"SLF4J": 4}, profile["log_facades"]
assert profile["test_class_suffix"] == {"Tests": 2}, profile["test_class_suffix"]
assert not profile["meta"]["sample_incomplete"], profile["meta"]

findings = run("scan_names.py", "--base", "main")["findings"]
actual = {(f["rule"], f["identifier"]) for f in findings}
expected = {("NAME-M3", "processRefund"), ("NAME-M5", "processRefund"),
            ("NAME-T2", "PaymentUtils"), ("NAME-M4", "checkAmount")}
assert expected <= actual, "Missing expected scanner candidates: " + repr(sorted(expected - actual))

baseline_paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "-z", "main", "--", "src/main"], cwd=root).decode().split("\0")
baseline = run("scan_names.py", "--files", *(p for p in baseline_paths if p.endswith(".java")))["findings"]
accepted = {"PaymentGateway", "StripePaymentGateway", "fetchDailyLimit", "sendPayout", "getErrorCode", "isGreaterThan"}
unexpected = [f for f in baseline if f["identifier"] in accepted]
assert not unexpected, "Accepted baseline names were flagged: " + repr(unexpected)
print("Scanner assertions passed: expected violations present; accepted baseline names retained.")
PY

echo
if [ "${KEEP:-0}" = "1" ]; then
  echo "== kept: $work  (branch feature/refunds has the change staged; base is main)"
else
  echo "== temp repository removed (set KEEP=1 to keep it)"
fi
