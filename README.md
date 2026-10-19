# code-quality-review-kit

One strict code-review standard, packaged as an open [Agent Skills](https://agentskills.io) skill, that works unchanged in **Claude Code**, **Codex**, **Devin** and **Factory Droid** — interactive CLIs and PR bots.

It reviews the way a Spring Framework or Apache project maintainer would: bugs and security first, then the **repository's own conventions**, naming (methods = action verb + noun, types named by stereotype and context, verbs that must not lie), SOLID and modern design principles, a **simplicity guard** against over-engineering, and a Spring/Apache-grade **Java quality bar**. Every finding carries a rule ID, a severity, evidence and a concrete fix.

```
[MAJOR][CONV-EXC / JAVA-EXC-HIERARCHY] src/main/java/com/acme/billing/refund/RefundService.java:64
  throw new RuntimeException("refund exceeds captured amount") bypasses the repo's error contract
  (all 23 domain errors extend BillingException(ErrorCode, …); GlobalExceptionHandler maps the code)
  → throw new RefundExceedsCaptureException(refundId, captured)
```

## What makes it different

- **Learns the repo before judging.** A profiler (`scan_conventions.py`) and a mandatory *Convention Profile* step capture how the codebase already does packaging, modules, exceptions, logging, naming vocabulary, DI, validation, tests and docs. New code is held to *that*, and the review records which defaults it did **not** apply because the repo does it differently. One codebase, one way.
- **Explicit precedence.** User instructions > `.agents/review-overrides.md` > documented conventions > observed conventions (≥3 occurrences) > skill defaults. Style yields to convention; bugs, security, data loss and lying names never do.
- **Naming is enforced, not suggested.** Verb contracts (`get` cheap, `find` may be empty, `fetch`/`load` do I/O, `calculate` pure), stereotype-based type names, banned grab-bag words — with the Spring/Apache idioms (`Abstract*`, `*Support`, `*Template`, `Default*`, `TransactionManager`, `StringUtils`, `do*` workers) explicitly allowed.
- **Over-engineering is a finding.** Every new interface, layer, generic, pattern, option, event or wrapper must name the second case or boundary that justifies it now (`OVER-*` rules; deep vs shallow modules; "would Spring maintainers merge this?").
- **Java/Kotlin get a real bar.** `JAVA-*` rules distilled from Spring Framework and Apache practice and Effective Java: API design, exceptions, logging, nullability/`Optional`, collections/streams, concurrency, Spring specifics (`@Transactional` placement, DTO boundary, JPA fetching, after-commit events, test slices), Javadoc, Kotlin addendum. Other languages get everything else.
- **Deterministic helpers.** `scan_names.py` pre-scans a diff for naming candidates in 8 languages and downgrades anything the base tree already does (`*Impl` ×38 → repo convention wins). Both scripts are stdlib Python, read-only, CI-friendly.
- **A fixture to prove the install.** `examples/java-sample/` is a tiny Spring service with established conventions plus a PR that breaks them; `EXPECTED.md` lists what a correct review reports.

## Install

```bash
cp -R repo/. /path/to/your-repo/ && cd /path/to/your-repo
git add .agents .claude .factory AGENTS.md CLAUDE.md REVIEW.md && git commit -m "Add code-quality-review skill"
```

| Tool | Finds it via | Run |
| --- | --- | --- |
| Claude Code | `.claude/skills/` pointer + `CLAUDE.md` | `/code-quality-review` |
| Codex CLI / IDE | `.agents/skills/` | `$code-quality-review` |
| Codex code review (GitHub) | `AGENTS.md` → `## Code Review Rules` | `@codex review` |
| Devin CLI / cloud | `.agents/skills/` | `/code-quality-review` |
| Devin Review (PR bot) | `REVIEW.md`, `AGENTS.md`, `CLAUDE.md` | `/devin review` |
| Factory Droid | `.agents/skills/` (compat) | `/code-quality-review` |
| Factory automated review | `.factory/skills/review-guidelines/SKILL.md` | `@droid review` |

Full details, personal install, customisation and CI gate: [INSTALL.md](INSTALL.md). Verify any install with `examples/java-sample/try.sh`.

## Layout

```
repo/.agents/skills/code-quality-review/   the skill: SKILL.md, references/, assets/naming-rules.json, scripts/
repo/.agents/review-overrides.md           per-repo exceptions (template)
repo/.claude/ repo/.factory/               thin entry points (no duplicated rules)
repo/AGENTS.md repo/CLAUDE.md repo/REVIEW.md
examples/java-sample/                      verification fixture + EXPECTED.md
```

References inside the skill: `repo-conventions.md`, `correctness-checklist.md`, `naming-conventions.md`, `design-principles.md`, `design-patterns.md`, `simplicity-and-readability.md`, `java-quality-bar.md`, `report-template.md`.

## Rule families

`BUG-*` `SEC-*` `PERF-*` `API-*` `DATA-*` `TEST-*` `OBS-*` · `CONV-*` · `NAME-*` · `SOLID-*` `DP-*` `PAT-*` `SMELL-*` · `OVER-*` `READ-*` · `JAVA-*` (incl. `JAVA-SPRING-*`, `JAVA-KT-*`)

Severities: **BLOCKER** · **MAJOR** · **MINOR** · **NIT**. Verdict: `REQUEST CHANGES` on any BLOCKER/MAJOR, `APPROVE WITH COMMENTS` on MINOR/NIT only, `APPROVE` when clean.

## License

MIT — see [LICENSE](LICENSE).
