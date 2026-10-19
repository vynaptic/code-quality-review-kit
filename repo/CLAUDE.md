# CLAUDE.md

Project notes for Claude Code. If this repository already has a `CLAUDE.md`, append the section below to it.

## Code review

- For any request to review code, a PR, a diff, a branch, staged changes or files — or to check naming, SOLID, design, readability, repository conventions or Java/Spring quality — use the `code-quality-review` skill (`/code-quality-review`, also auto-selected). It lives in `.agents/skills/code-quality-review/` and is exposed to Claude Code through `.claude/skills/code-quality-review/`.
- The short version of the standard is `REVIEW.md`; per-repository exceptions are in `.agents/review-overrides.md` (only uncommented lines are active).
- Review-only by default: do not change code during a review unless explicitly asked to fix findings.
- Learn the repository's own conventions before judging (packaging, exceptions, logging, naming vocabulary, tests); never flag something the codebase does deliberately and consistently, and never introduce a second way of doing a cross-cutting thing when writing code here either.
