---
name: code-quality-review
description: Review pull requests, diffs, branches, staged changes or files for correctness, repository conventions, naming, design, readability, repeated literals and Java/Spring quality. Use when the user asks to review code or a PR, check naming or SOLID, judge whether a change is over-engineered, enforce the repository's own conventions, or wants a Spring/Java code review. Review-only unless fixes are requested.
license: MIT (LICENSE in this folder)
compatibility: Any agent that reads SKILL.md. The three optional scanners need Python 3.8+ and git; they are read-only (git diff, show, ls-files, grep), write nothing and use no network.
metadata:
  version: "2.2.0"
  author: "VM (Virendra)"
  languages: "Java and Kotlin first-class; language-neutral guidance for C#, TypeScript/JavaScript, Python, Go, Rust and Swift"
  tags: "code-review, java, spring, kotlin, naming-conventions, solid, clean-code, mybatis"
  docs_url: "https://github.com/vynaptic/code-quality-review-kit"
---

# Code Quality Review

Review changed code for correctness and maintainability using the repository's contracts. Enforce clear action+noun method names, role/context-based type names, and justified design choices. Spring and Apache projects are useful examples of disciplined engineering, not one universal style guide.

**Review-only by default.** Editing requires a request to fix findings. Posting reviews or changing external systems requires user authorization; a review request alone is not permission to publish.

## References

Paths below are relative to this skill directory, wherever installed. Resolve the target repository separately; never profile the skill's installation directory by mistake.

| Reference | Read when |
| --- | --- |
| [Repository conventions](references/repo-conventions.md) | Always first: precedence, baseline, scope and CONV-* rules |
| [Correctness](references/correctness-checklist.md) | Every review; apply relevant checks |
| [Naming](references/naming-conventions.md) | New or changed identifiers and contracts |
| [Design principles](references/design-principles.md) | Changed responsibilities, dependencies, state or interfaces |
| [Patterns and smells](references/design-patterns.md) | Pattern use, duplicated branching, object creation or integrations |
| [Simplicity and readability](references/simplicity-and-readability.md) | Changed control flow and abstractions |
| [Literals and data carriers](references/literals-and-data-carriers.md) | Repeated strings/numbers, string-typed state that should be an enum, POJOs that should be builders/records/value objects, MyBatis/JPA/Spring/Python/TypeScript literal rules |
| [Java quality](references/java-quality-bar.md) | Java/Kotlin; use other languages' own APIs and idioms elsewhere |
| [Report format](references/report-template.md) | Before reporting |
| [Naming lexicon](assets/naming-rules.json) | Scanner leads or domain-vocabulary questions |
| [Overrides template](assets/review-overrides.template.md) | When a repository has no `.agents/review-overrides.md` yet |

## Workflow

### 1. Establish scope and baseline

Use the requested PR/range/files. Otherwise resolve a merge base with the actual target branch; try `origin/main`, `origin/master`, `origin/develop`, `main`, `master`, `develop` only if no target is supplied. Inspect `git diff <base-sha>` plus non-ignored untracked files for a branch/working-tree review. For staged review use the index diff and HEAD as baseline. Do not silently substitute HEAD if a requested base is missing.

Read surrounding code, callers, tests and applicable nested instructions. Report introduced or worsened problems; label relevant pre-existing issues. For a large change prioritize high-risk paths and state exactly what was not reviewed. If scope cannot be established, report the limitation rather than a clean verdict.

### 2. Establish applicable conventions

Follow [repo-conventions.md](references/repo-conventions.md). From the target repository run:

```bash
python3 <skill-dir>/scripts/scan_conventions.py --ref <base-sha>
# Scope to the affected module when appropriate:
python3 <skill-dir>/scripts/scan_conventions.py --root services/billing --ref <base-sha>
```

Without `--ref`, the profiler describes the current tree; that is useful for orientation but is not evidence of pre-change conventions. Inspect 2–3 relevant neighbors and the governing docs/configuration. Note sampling or read failures. Record the rules that actually influenced the review and the defaults displaced by local contracts.

### 3. Gather naming and literal leads

```bash
python3 <skill-dir>/scripts/scan_names.py --base <base-sha>        # naming candidates on added lines
python3 <skill-dir>/scripts/scan_literals.py --base <base-sha>     # repeated literals, closed sets, MyBatis/JPA/SQL leads
python3 <skill-dir>/scripts/scan_names.py --staged                 # both scripts accept --staged, --files, --diff-file
```

Choose the mode matching the review. These are regex candidates, not verdicts. Counts are advisory, never automatic waivers; confirm language, module, stereotype and exceptions. Check semantic naming and other identifiers manually. A failed scanner is incomplete evidence, not an approval; continue manually where possible and disclose the gap. An optional candidate failure threshold is not a convention-aware CI gate.

### 4. Review in risk order

- **Correctness/security:** trace concrete inputs, states or interleavings through callers. Check builds, resources, authorization, data integrity, concurrency and compatibility. Before flagging wiring, account for framework discovery, reflection and external library consumers. Run applicable repo checks when feasible; distinguish introduced failures from baseline/environment failures.
- **Repo standards and naming:** enforce the scoped vocabulary, packaging/modules, errors, logging, DI, tests and documentation. Default to action+noun methods (receiver may supply the noun), predicates for booleans, and types named by domain/role and distinguishing implementation trait. Judge `NAME-M2` against the actual API/repo contract, not a prefix alone. A documented remote `getX` is valid; a supposedly pure predicate that writes state is not.
- **Design:** apply SOLID, composition, DRY/KISS/YAGNI, LoD, Tell-Don't-Ask, CQS, encapsulation, illegal-state prevention, layering and DDD where applicable. Name the concrete cost and smallest safe fix. Use the pattern table only when its problem is present.
- **Simplicity:** ask what current benefit an interface, layer, generic, option, wrapper or pattern provides. Variation, a boundary, invariant protection, compatibility, an extension contract or an operational requirement can justify it. One implementation or one deployed value alone proves nothing. Do not replace a justified boundary with duplicated or unsafe code.
- **Repetition and data carriers:** follow [literals-and-data-carriers.md](references/literals-and-data-carriers.md). A literal repeated three or more times (in Java, Python, MyBatis XML, SQL, TypeScript…) gets one named owner; several literals compared under one key are a closed set and become an enum persisted by name/code; a POJO built through a long constructor or a chain of setters becomes an immutable record/value object or a builder when fields are optional. Name the owner type and the drift risk; respect framework needs (JPA entities, binders) and the repository's idiom (Lombok, `StrEnum`, `TextChoices`). `${}` in MyBatis and f-string SQL are injection leads first.
- **Language/framework:** apply version-appropriate rules. Preserve Spring proxying and ORM requirements before recommending `final`, reduced visibility or records. Check the deployed JDK, not just compiler syntax level, for concurrency advice.
- **Tests:** require meaningful coverage of new behavior and regressions, including valid exceptions and error paths. Follow the repository's test stack and naming; do not request tests that merely mirror implementation.

### 5. Confirm and report

Reopen cited lines. For every finding confirm applicability, evidence, concrete impact, exceptions and the smallest safe fix. Merge duplicate root causes. Do not repeat formatting/lint diagnostics as manual findings. A count, size threshold, pattern name or personal preference alone is not sufficient evidence.

Use [report-template.md](references/report-template.md). Every finding includes severity, rule ID, location, evidence/impact and fix. Questions remain questions; incomplete coverage is explicit. Apply the platform's required output schema when present, preserving the same evidence and honest severity. Hosted PR bots may filter low-priority design/style feedback; do not inflate severity to bypass them.

| Severity | Use when |
| --- | --- |
| BLOCKER | Confirmed security hole, data corruption, crash, incompatible break or introduced build failure |
| MAJOR | Demonstrable contract breach, materially risky design, missing tests for new business logic, or misleading behavior with consequential caller impact |
| MINOR | Actionable naming/convention/design deviation with a concrete maintenance cost and no immediate risk |
| NIT | Optional wording or cosmetic improvement; normally omit |

`REQUEST CHANGES` for BLOCKER/MAJOR; `APPROVE WITH COMMENTS` for MINOR/NIT only; `APPROVE` when the scoped review is clean. Do not approve unreviewed scope. A public modifier, core-package location or rule count alone does not raise severity.

## Fix mode

Fix requested findings using the established conventions. Before renaming externally consumed APIs, serialized fields or schema elements, explain compatibility impact and follow the user's authorized migration scope. Preserve behavior when refactoring; keep unrelated changes out. Run the relevant tests/build/linters, then review the final diff. Report checks actually run and remaining limitations.
