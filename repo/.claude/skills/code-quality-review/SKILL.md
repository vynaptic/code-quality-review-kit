---
name: code-quality-review
description: Strict, evidence-based code review for pull requests, diffs, branches, staged changes or files. Finds bugs and security issues first, then enforces the repository's own established conventions (naming, packaging, modules, exceptions, logging, tests, DI), naming rules (methods = action verb + noun, types named by stereotype and context, verb contracts that must not lie), SOLID and modern design principles and patterns, a simplicity guard against over-engineering, and a Spring Framework / Apache-grade Java quality bar. Use when asked to review code, check naming, SOLID, design, readability, conventions or Java/Spring quality, or before opening or merging a PR. Review-only unless the user asks for fixes.
argument-hint: "[PR number | branch | commit range | files] (default: current branch vs base)"
---

# Code Quality Review (Claude Code entry point)

This folder is a thin entry point so Claude Code discovers the skill. The skill itself is maintained once, in the cross-tool location:

**`.agents/skills/code-quality-review/SKILL.md`** (repository root; the same files serve Codex, Devin and Factory Droid).

Do this now:
1. Read `.agents/skills/code-quality-review/SKILL.md` in full and follow it exactly — its workflow, passes, precedence rules, severities, report template and fix-mode rules.
2. Every relative path inside it (`references/…`, `assets/…`, `scripts/…`) resolves against `.agents/skills/code-quality-review/`. Use that as `<skill-dir>` in the commands it shows, e.g. `python3 .agents/skills/code-quality-review/scripts/scan_conventions.py`.
3. Scope for this run: `$ARGUMENTS` (empty = the current branch against its base, including uncommitted and untracked work).
4. Repository-specific exceptions are in `.agents/review-overrides.md`; only uncommented lines are active.

Do not duplicate or paraphrase the standard here — if this file and the real skill ever differ, the real skill wins.
