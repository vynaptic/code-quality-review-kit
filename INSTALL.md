# Install

Everything under `repo/` goes into the root of the repository you want reviewed. The skill itself is one folder; the rest are small entry points that tell each tool where it is.

```
repo/
├── .agents/skills/code-quality-review/        the skill (SKILL.md, references/, assets/, scripts/) — Codex, Devin, Factory read it here
├── .agents/review-overrides.md                optional per-repo exceptions (template, nothing active)
├── .claude/skills/code-quality-review/SKILL.md Claude Code entry point (points at the .agents skill)
├── .factory/skills/review-guidelines/SKILL.md  Factory automated PR review guidance
├── AGENTS.md                                  Codex (CLI + GitHub review: "## Code Review Rules"); also read by Devin and Droid
├── CLAUDE.md                                  Claude Code project notes; also read by Devin Review
└── REVIEW.md                                  Devin Review (PR bot) guidance
```

## 1. Manual install (copy and paste)

From the kit checkout, with `REPO=/path/to/your-repo`:

**Step 1 — copy the skill folder** (required for every tool):
```bash
find repo -name __pycache__ -prune -exec rm -rf {} + -o -name .DS_Store -delete   # clean local leftovers first
mkdir -p "$REPO/.agents/skills"
cp -R repo/.agents/skills/code-quality-review "$REPO/.agents/skills/"
```

**Step 2 — copy the entry points you need** (skip tools you do not use):
```bash
cp -n repo/.agents/review-overrides.md "$REPO/.agents/"                          # optional; keep yours if it exists
mkdir -p "$REPO/.claude/skills" && cp -R repo/.claude/skills/code-quality-review "$REPO/.claude/skills/"      # Claude Code
mkdir -p "$REPO/.factory/skills" && cp -R repo/.factory/skills/review-guidelines "$REPO/.factory/skills/"      # Factory automated review
```

**Step 3 — guidance files.** For each of `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`:
- If your repository does not have the file: `cp repo/AGENTS.md "$REPO/"` (same for the other two).
- If it already exists: open `repo/<file>` in the kit, copy everything between `<!-- code-quality-review-kit:start -->` and `<!-- code-quality-review-kit:end -->` (markers included), and paste it at the end of your existing file. Keep your own text; the markers let you find and replace the block on later updates.

Minimum per tool, if you want only one:

| Tool | Copy |
| --- | --- |
| Claude Code | skill folder + `.claude/skills/code-quality-review/SKILL.md` + `CLAUDE.md` block |
| Codex CLI / IDE | skill folder + `AGENTS.md` block |
| Codex GitHub review | `AGENTS.md` block (the `## Code Review Rules` section is what it reads) |
| Devin CLI / cloud | skill folder (+ `AGENTS.md` block) |
| Devin Review (PR bot) | `REVIEW.md` block |
| Factory Droid CLI | skill folder (+ `AGENTS.md` block) |
| Factory automated review | `.factory/skills/review-guidelines/SKILL.md` |

**Step 4 — commit** the added paths (`.agents`, `.claude`, `.factory`, `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`).

**Updating later:** replace the skill folder with the new copy (`rm -rf "$REPO/.agents/skills/code-quality-review" && cp -R …`), replace the marked blocks in the three guidance files, leave `.agents/review-overrides.md` alone.

## 2. Scripted install (same result, non-destructive)

```bash
python3 scripts/install.py "/path/to/your-repo"
```
Copies missing files, appends the marked block to existing `AGENTS.md`/`CLAUDE.md`/`REVIEW.md` once, never touches an existing `.agents/review-overrides.md`, and exits without writing if a skill file already exists with different content (resolve by hand, then rerun). It never deletes or overwrites.

## 3. Personal install (your machine, every project)

```bash
mkdir -p ~/.agents/skills ~/.claude/skills
cp -R repo/.agents/skills/code-quality-review ~/.agents/skills/        # Codex, Devin CLI, Factory Droid
ln -s ~/.agents/skills/code-quality-review ~/.claude/skills/code-quality-review   # Claude Code (or cp -R, then edit the path inside its SKILL.md)
```
Cloud sessions and PR bots read repository files only; use section 1 or 2 for those. Per-repo exceptions still live in the reviewed repository's `.agents/review-overrides.md`.

## 4. How each tool finds and runs it

| Tool | Discovery | Run |
| --- | --- | --- |
| Codex CLI / IDE | `.agents/skills/` (repo root up from the working directory) | `$code-quality-review review this branch against main` |
| Codex GitHub review | `AGENTS.md` → `## Code Review Rules` | `@codex review` (docs describe P0/P1-only comments) |
| Claude Code | `.claude/skills/` + `CLAUDE.md` | `/code-quality-review` |
| Devin CLI / cloud | `.agents/skills/` | `/code-quality-review` |
| Devin Review | `REVIEW.md`, `AGENTS.md`, `CLAUDE.md` | `/devin review` or auto-review |
| Factory Droid | `.agents/skills/` (compatibility path) | `/code-quality-review` |
| Factory automated review | `.factory/skills/review-guidelines/SKILL.md` | `@droid review` (docs exclude style/architecture opinions; security review needs its own `security-review-guidelines`, not shipped here) |

Hosted bots keep their own filters and output formats; the full report (rule IDs, severities, **Conventions applied**) comes from the interactive tools. Vendor docs: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Codex GitHub](https://learn.chatgpt.com/docs/third-party/github), [Claude Code](https://code.claude.com/docs/en/skills), [Devin CLI](https://docs.devin.ai/cli/extensibility/skills/overview), [Devin Review](https://docs.devin.ai/work-with-devin/devin-review), [Factory skills](https://docs.factory.com/harness/skills), [Factory review](https://docs.factory.com/software-factory/code-review-ci).

## 5. Verify

```bash
bash examples/java-sample/try.sh          # throwaway repo: profiles the baseline, scans the sample PR, asserts expected candidates
KEEP=1 bash examples/java-sample/try.sh   # keep it, open it in a tool, ask for a review, compare with examples/java-sample/EXPECTED.md
```

## 6. Customise and scan

- `.agents/review-overrides.md`: active (uncommented) rules win over the skill's defaults and inferred conventions; they adjust style, architecture, severity and scope, never correctness or security findings.
- Domain verbs: `assets/naming-rules.json → approved_verbs`.
- Scanners, from an installed repository (both read-only, stdlib Python, git only):
  ```bash
  base=$(git merge-base HEAD origin/main)
  python3 .agents/skills/code-quality-review/scripts/scan_conventions.py --ref "$base"   # convention profile of the base commit
  python3 .agents/skills/code-quality-review/scripts/scan_names.py --base "$base"        # naming candidates in the diff
  python3 .agents/skills/code-quality-review/scripts/scan_names.py --staged
  ```
  Candidates and counts are leads for the reviewer, not verdicts. `--fail-on high` is an optional CI threshold on raw candidates; a nonzero exit code also signals scanner errors (exit 2).
