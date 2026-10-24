# Install

Everything under `repo/` goes into the root of the repository you want reviewed. The skill itself is one folder; the rest are small entry points that tell each tool where it is.

```
repo/
├── .agents/skills/strict-code-review/        the skill (SKILL.md, README, LICENSE, references/, assets/, scripts/) — Codex, Devin, Factory read it here
├── .agents/review-overrides.md                optional per-repo exceptions (template, nothing active; same file as the skill's assets/review-overrides.template.md)
├── .claude/skills/strict-code-review/SKILL.md Claude Code entry point (points at the .agents skill)
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
cp -R repo/.agents/skills/strict-code-review "$REPO/.agents/skills/"
```

**Step 2 — copy the entry points you need** (skip tools you do not use):
```bash
cp -n repo/.agents/review-overrides.md "$REPO/.agents/"                          # optional; keep yours if it exists
mkdir -p "$REPO/.claude/skills" && cp -R repo/.claude/skills/strict-code-review "$REPO/.claude/skills/"      # Claude Code
mkdir -p "$REPO/.factory/skills" && cp -R repo/.factory/skills/review-guidelines "$REPO/.factory/skills/"      # Factory automated review
```

**Step 3 — guidance files.** For each of `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`:
- If your repository does not have the file: `cp repo/AGENTS.md "$REPO/"` (same for the other two).
- If it already exists: open `repo/<file>` in the kit, copy everything between `<!-- code-quality-review-kit:start -->` and `<!-- code-quality-review-kit:end -->` (markers included), and paste it at the end of your existing file. Keep your own text; the markers let you find and replace the block on later updates.

Minimum per tool, if you want only one:

| Tool | Copy |
| --- | --- |
| Claude Code | skill folder + `.claude/skills/strict-code-review/SKILL.md` + `CLAUDE.md` block |
| Codex CLI / IDE | skill folder + `AGENTS.md` block |
| Codex GitHub review | `AGENTS.md` block (the `## Code Review Rules` section is what it reads) |
| Devin CLI / cloud | skill folder (+ `AGENTS.md` block) |
| Devin Review (PR bot) | `REVIEW.md` block |
| Factory Droid CLI | skill folder (+ `AGENTS.md` block) |
| Factory automated review | `.factory/skills/review-guidelines/SKILL.md` |

**Step 4 — commit** the added paths (`.agents`, `.claude`, `.factory`, `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`).

**Updating later:** replace the skill folder with the new copy (`rm -rf "$REPO/.agents/skills/strict-code-review" && cp -R …`), replace the marked blocks in the three guidance files, leave `.agents/review-overrides.md` alone.

## 2. Scripted install (same result, non-destructive)

```bash
python3 scripts/install.py "/path/to/your-repo"
```
Copies missing files, appends the marked block to existing `AGENTS.md`/`CLAUDE.md`/`REVIEW.md` once, never touches an existing `.agents/review-overrides.md`, and exits without writing if a skill file already exists with different content (resolve by hand, then rerun). It never deletes or overwrites.

## 3. Personal install (your machine, every project)

```bash
mkdir -p ~/.agents/skills ~/.claude/skills
cp -R repo/.agents/skills/strict-code-review ~/.agents/skills/        # Codex, Devin CLI, Factory Droid
ln -s ~/.agents/skills/strict-code-review ~/.claude/skills/strict-code-review   # Claude Code (or cp -R, then edit the path inside its SKILL.md)
```
Cloud sessions and PR bots read repository files only; use section 1 or 2 for those. Per-repo exceptions still live in the reviewed repository's `.agents/review-overrides.md`.

## 4. How each tool finds and runs it

| Tool | Discovery | Run |
| --- | --- | --- |
| Codex CLI / IDE | `.agents/skills/` (repo root up from the working directory) | `$strict-code-review review this branch against main` |
| Codex GitHub review | `AGENTS.md` → `## Code Review Rules` | `@codex review` (docs describe P0/P1-only comments) |
| Claude Code | `.claude/skills/` + `CLAUDE.md` | `/strict-code-review` |
| Devin CLI / cloud | `.agents/skills/` | `/strict-code-review` |
| Devin Review | `REVIEW.md`, `AGENTS.md`, `CLAUDE.md` | `/devin review` or auto-review |
| Factory Droid | `.agents/skills/` (compatibility path) | `/strict-code-review` |
| Factory automated review | `.factory/skills/review-guidelines/SKILL.md` | `@droid review` (docs exclude style/architecture opinions; security review needs its own `security-review-guidelines`, not shipped here) |

Hosted bots keep their own filters and output formats; the full report (rule IDs, severities, **Conventions applied**) comes from the interactive tools. Vendor docs: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Codex GitHub](https://learn.chatgpt.com/docs/third-party/github), [Claude Code](https://code.claude.com/docs/en/skills), [Devin CLI](https://docs.devin.ai/cli/extensibility/skills/overview), [Devin Review](https://docs.devin.ai/work-with-devin/devin-review), [Factory skills](https://docs.factory.com/harness/skills), [Factory review](https://docs.factory.com/software-factory/code-review-ci).

## 5. Verify

```bash
bash examples/java-sample/try.sh          # throwaway repo: profiles the baseline, scans the sample PR, asserts expected candidates
KEEP=1 bash examples/java-sample/try.sh   # keep it, open it in a tool, ask for a review, compare with examples/java-sample/EXPECTED.md
```

## 6. Customise and scan

- `.agents/review-overrides.md`: active (uncommented) rules win over the skill's defaults and inferred conventions; they adjust style, architecture, severity and scope, never correctness or security findings.
- Domain verbs: `assets/naming-rules.json → approved_verbs`; literal thresholds: `assets/naming-rules.json → literals`.
- Scanners, from an installed repository (all read-only, stdlib Python, git only):
  ```bash
  base=$(git merge-base HEAD origin/main)
  python3 .agents/skills/strict-code-review/scripts/scan_conventions.py --ref "$base"   # convention profile of the base commit
  python3 .agents/skills/strict-code-review/scripts/scan_names.py --base "$base"        # naming candidates in the diff
  python3 .agents/skills/strict-code-review/scripts/scan_literals.py --base "$base"     # repeated literals, closed sets (enum candidates), MyBatis/JPA/SQL leads
  python3 .agents/skills/strict-code-review/scripts/scan_names.py --staged              # all three accept --staged, --files, --diff-file
  ```
  Candidates and counts are leads for the reviewer, not verdicts. `--fail-on high` is an optional CI threshold on raw candidates; a nonzero exit code also signals scanner errors (exit 2).

## 7. Publish to a skill marketplace (Agensi and others)

[Agensi](https://www.agensi.io/skills) and most catalogues take a zip of **one top-level folder named after the skill, with `SKILL.md` at that folder's root**. That folder is exactly `repo/.agents/skills/strict-code-review/`; it is self-contained (`README.md`, `LICENSE`, `references/`, `assets/`, `scripts/`). The entry-point files (`AGENTS.md`, `.claude/…`, `.factory/…`, `REVIEW.md`) are repository plumbing for PR bots and are not part of the package.

```bash
find repo -name __pycache__ -prune -exec rm -rf {} + -o -name .DS_Store -delete
uvx --from "git+https://github.com/agentskills/agentskills#subdirectory=skills-ref" skills-ref validate "$PWD/repo/.agents/skills/strict-code-review"   # optional: open-standard validator
mkdir -p dist && rm -f dist/strict-code-review.zip
(cd repo/.agents/skills && zip -r ../../../dist/strict-code-review.zip strict-code-review -x "*.DS_Store" "*__pycache__*" "*.pyc")
unzip -l dist/strict-code-review.zip
```

Then: Agensi dashboard → Creator Mode → **Submit a Skill** → upload `dist/strict-code-review.zip`, add tags and the listing text (the form pre-fills `name` and `description`; the version, tags and docs link are in `metadata` because the open standard allows only `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools` at the top level, and strict agents reject anything else — type them into the form), choose free or a price. Submissions pass an 8-check automated scan (file structure, file types, dangerous commands, secrets, environment harvesting, network access, obfuscation, prompt injection), an AI review and a human approval, usually within a day. For updates, upload a new zip; the platform bumps the version and blocks an identical zip.

What the scan will see in this skill, and why it passes: text files only, no symlinks, no binaries; scripts call `git` through `subprocess.run([...])` without `shell=True`, read files, write nothing, use no network and read no environment variables; no credentials; no instructions that override agent safety rules. If a reviewer asks about `subprocess`, point at the `compatibility` field and the docstring at the top of each script. Marketplace installs place the skill folder where the agent looks for skills (e.g. `~/.claude/skills/`), so the repository entry points are not needed there; buyers who want PR-bot coverage follow sections 1–2 of this guide.
