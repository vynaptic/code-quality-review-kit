---
name: strict-code-review
description: Review code, PRs, branches or files for correctness, repository conventions, naming, design, repeated literals and Java/Spring quality. Use when asked to review code or a PR, check naming or SOLID, judge over-engineering, or enforce repo conventions. Review-only unless fixes are requested.
argument-hint: "[PR | branch | commit range | files]"
---

Read `.agents/skills/strict-code-review/SKILL.md` from the repository root and follow it. Resolve its `references/`, `assets/` and `scripts/` paths against that canonical skill directory, not this wrapper. Read active exceptions from the reviewed repository's `.agents/review-overrides.md`.

Scope: `$ARGUMENTS` (empty means the current branch against its base, including uncommitted and untracked changes). The canonical skill supplies the workflow, report format and fix safeguards.
