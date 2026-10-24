# strict-code-review

A code-review skill for AI coding agents (Claude Code, Codex, Devin, Factory Droid and any other agent that reads `SKILL.md`). It reviews a pull request, branch, diff, staged change or set of files the way a strict Spring/Apache-style maintainer would:

1. **Correctness and security first**: concrete trigger, impact, location and fix for every bug.
2. **The repository's own conventions** before the skill's defaults: packaging, modules, exception hierarchy, logging, naming vocabulary, DI, tests. One codebase, one way.
3. **Naming**: methods are action verb + noun, booleans are predicates, types are named by role and context, and a name must not contradict its documented contract.
4. **Design**: SOLID, DRY/KISS/YAGNI, Law of Demeter, Tell-Don't-Ask, CQS, layering, DDD, with explicit "when not to flag" guards.
5. **Simplicity**: every new interface, layer, pattern, option or wrapper must have a current justification; speculative abstraction is a finding.
6. **Repeated literals and data carriers**: repeated strings/numbers get one owner, closed sets become enums, POJOs built field by field become records, value objects or builders; MyBatis/JPA/Spring/Python/TypeScript specifics included.
7. **Java/Spring quality bar**: API design, exceptions, logging, nullability, collections, concurrency, Spring proxies/transactions/JPA, Javadoc, Kotlin.

Every finding carries a rule ID, a severity (BLOCKER/MAJOR/MINOR/NIT), evidence and the smallest safe fix. Review-only unless you ask it to fix.

## Contents

```
SKILL.md                         workflow, precedence, severities
references/                      rulebooks loaded on demand (conventions, correctness, naming, design,
                                 patterns, simplicity, literals & data carriers, Java bar, report format)
assets/naming-rules.json         verb lexicon, type-word lists, literal thresholds (edit to extend)
assets/review-overrides.template.md   copy to <repo>/.agents/review-overrides.md for per-repo exceptions
scripts/scan_conventions.py      convention profile of a commit (what the repo already does)
scripts/scan_names.py            naming candidates on changed lines
scripts/scan_literals.py         repeated literals, closed sets, MyBatis/JPA/SQL leads
LICENSE                          MIT
```

## Using it

- Claude Code / Devin CLI / Factory Droid: `/strict-code-review` (or just ask for a review). Codex: `$strict-code-review`.
- The scripts are optional helpers the agent runs from the reviewed repository. They need Python 3.8+ and git, are **read-only** (git diff, show, ls-files, grep), write nothing and never use the network. Without them the agent reviews manually and says so.
- Per-repository exceptions (your logging facade, exception root, packaging rule, grandfathered names) go in `.agents/review-overrides.md` in the reviewed repository; start from `assets/review-overrides.template.md`. Only uncommented lines are active.

## Repository install and PR bots

To make the skill part of a repository (all tools, whole team) and to feed hosted PR reviewers (Codex GitHub review via `AGENTS.md`, Devin Review via `REVIEW.md`, Factory automated review), use the kit at https://github.com/vynaptic/code-quality-review-kit — it adds the small entry-point files and documents each tool's discovery path.

## License

MIT. See `LICENSE`.
