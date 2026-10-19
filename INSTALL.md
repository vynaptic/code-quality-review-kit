# Install and use

The canonical workflow lives in `repo/.agents/skills/code-quality-review/`. Repository guidance and tool adapters route reviewers to it. Interactive agents can follow the full workflow; hosted PR bots have their own supported checks, filters and report formats.

## Repository install

Run from the kit checkout with Python 3; quote paths containing spaces:

```bash
python3 scripts/install.py "/path/to/your repository"
```

The installer creates the target if needed, copies missing skill assets, preserves `.agents/review-overrides.md`, and appends a marked section to existing `AGENTS.md`, `CLAUDE.md` and `REVIEW.md` once. Existing text and marked sections remain untouched. Identical assets are accepted on repeat runs. Differing assets, symlinks inside the destination layout, invalid path types or malformed guidance markers cause a nonzero exit before writes.

Review the target's changes and commit only the intended files. Do not copy `repo/.` over an existing repository: that overwrites guidance and local exceptions.

### Updates and conflicts

There is no automatic overwrite mode. Back up or commit the existing installation, inspect each reported conflict against the corresponding file under this kit's `repo/`, and merge the desired changes explicitly. Rerun after resolving conflicts. Review marked guidance sections separately: rerunning deliberately preserves them, including local edits. For an older unmarked installation, reconcile its existing kit guidance before adding the new section. An I/O failure during writing may leave partial additions; correct the reported problem and rerun.

## Interactive tools

| Tool | Repository discovery | Invocation |
| --- | --- | --- |
| Codex CLI / IDE | `.agents/skills/code-quality-review/SKILL.md` | `$code-quality-review review this branch against main` |
| Claude Code | `.claude/skills/code-quality-review/SKILL.md` routes to the canonical skill | `/code-quality-review` |
| Devin CLI | `.agents/skills/code-quality-review/SKILL.md` | `/code-quality-review` |
| Factory Droid | `.agents/skills/` compatibility discovery | `/code-quality-review` |

These tools also select skills by description. If the skill does not appear, inspect the tool's skill list and reload/restart as its documentation directs. The Claude repository wrapper resolves its canonical path from the repository root, even when the session starts in a subdirectory.

Official discovery references: [Codex](https://learn.chatgpt.com/docs/build-skills), [Claude Code](https://code.claude.com/docs/en/skills), [Devin CLI](https://docs.devin.ai/cli/extensibility/skills/overview), [Factory Droid](https://docs.factory.com/harness/skills).

## Hosted PR review

The repository must first be connected/enrolled with the vendor; installing files does not enable its service.

| Reviewer | Kit guidance | Trigger and limits |
| --- | --- | --- |
| Codex GitHub review | `AGENTS.md`, `## Code Review Rules` | `@codex review`; current docs describe P0/P1-only comments. |
| Devin Review | `REVIEW.md`, also `AGENTS.md` and `CLAUDE.md` | `/devin review` on supported GitHub PRs, or configured auto-review; findings use Devin's categories and posting settings. |
| Factory code review | `.factory/skills/review-guidelines/SKILL.md` | `@droid review` after workflow setup; current docs exclude stylistic concerns and architectural opinions. |

Repository guidance focuses these reviewers but cannot promise the detailed CLI severity scale, every naming/design finding, a particular verdict, or the full report template. Factory's separate security review requires `security-review-guidelines`; this kit does not configure it. Use an interactive review when you need the complete workflow.

Official behavior/setup references: [Codex GitHub](https://learn.chatgpt.com/docs/third-party/github), [Devin Review](https://docs.devin.ai/work-with-devin/devin-review), [Factory automated review](https://docs.factory.com/software-factory/code-review-ci).

## Personal install

On macOS/Linux, copy the canonical skill into your home folder and link Claude to that copy. The following runs from the kit checkout, refuses existing destinations (including broken links), and avoids the repository wrapper’s path assumption:

```bash
python3 - <<'PYCODE'
from pathlib import Path
import shutil
source = Path.cwd() / "repo/.agents/skills/code-quality-review"
if not (source / "SKILL.md").is_file():
    raise SystemExit("Run this from the kit checkout.")
canonical = Path.home() / ".agents/skills/code-quality-review"
claude = Path.home() / ".claude/skills/code-quality-review"
for destination in (canonical, claude):
    if destination.exists() or destination.is_symlink():
        raise SystemExit("Already exists; inspect before changing: " + str(destination))
canonical.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, canonical, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
claude.parent.mkdir(parents=True, exist_ok=True)
claude.symlink_to(canonical, target_is_directory=True)
PYCODE
```

For personal updates, back up and merge the home canonical copy explicitly; the Claude link follows that copy. Personal skills apply to local sessions; cloud/hosted reviewers need repository files. On systems without symlink support, use the repository installer instead. Repository exceptions still belong to the repository being reviewed, not the home skill folder.

## Verify

From **the kit checkout**, run:

```bash
python3 -m unittest discover -s tests
bash examples/java-sample/try.sh
KEEP=1 bash examples/java-sample/try.sh
```

Follow [the fixture instructions](examples/java-sample/README.md) to run an interactive review in the retained sample. Compare against [EXPECTED.md](examples/java-sample/EXPECTED.md), allowing judgment where a concrete contract or impact is required. The fixture is not copied into your installed repository.

## Customize and scan

Use `.agents/review-overrides.md` for active repository rules, severity adjustments and scope. Keep examples commented until needed. Overrides can adjust style and structure; they cannot waive concrete correctness or security risks. Edit detailed rules in the canonical skill and references; keep adapters short.

From an installed repository, choose the actual comparison base (the example assumes `origin/main`):

```bash
if review_base=$(git merge-base HEAD origin/main); then
  python3 .agents/skills/code-quality-review/scripts/scan_conventions.py --ref "$review_base" &&
  python3 .agents/skills/code-quality-review/scripts/scan_names.py --base "$review_base"
fi
python3 .agents/skills/code-quality-review/scripts/scan_names.py --staged
```

`scan_conventions.py` inventories the base revision; confirm its leads against documented rules and neighbouring code. `scan_names.py` reports candidates, including base-tree counts as advisory evidence. It does not downgrade candidates automatically or interpret Markdown overrides. The reviewer confirms actual API/framework contracts and drops false positives.

In CI, run the naming scan as an advisory report. Use formatters, linters and architecture tests for deterministic gates. `--fail-on` is an explicit opt-in threshold on raw candidates, not an enforcement of repository policy; even high-confidence candidates can be valid under the actual contract.
