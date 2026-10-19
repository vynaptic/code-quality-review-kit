# AGENTS.md

Instructions for AI coding agents working in this repository (Codex, Devin, Factory Droid, Claude Code and others that read this file). If this repository already has an `AGENTS.md`, append the sections below to it instead of replacing it.

## Skills

- `code-quality-review` (`.agents/skills/code-quality-review/SKILL.md`): the full code-review standard. Use it for any request to review code, a PR, a diff, a branch, staged changes or files; to check naming, SOLID, design, readability, repository conventions or Java/Spring quality; or before opening or merging a PR. Invoke explicitly with `$code-quality-review` (Codex) or `/code-quality-review` (Devin CLI, Factory Droid, Claude Code).
- Per-repository exceptions to the standard live in `.agents/review-overrides.md` (only uncommented lines are active).

## Code Review Rules

These rules apply to every pull request review in this repository. The full standard is `.agents/skills/code-quality-review/` (where they differ, the full standard wins; active rules in `.agents/review-overrides.md` win over both). The same text is in `REVIEW.md`.

### Precedence
User instructions > `.agents/review-overrides.md` > documented repo conventions (`CONTRIBUTING.md`, ADRs, linter configs) > conventions observed in the codebase (≥3 existing occurrences, no stronger competitor) > the standard's defaults. Conventions override *style* rules only; bugs, security, data-loss and performance findings, and names that lie about behaviour, are always reported.

### Learn the repository first
Before judging, profile what the codebase already does: package layout, module boundaries, type suffixes and read verbs, exception hierarchy and translation, logging facade/declaration/placeholder style, nullability annotations, DI style, validation, mapping, test stack and naming, Javadoc expectations, formatter/linter presence (`python3 .agents/skills/code-quality-review/scripts/scan_conventions.py`, then open 2–3 neighbouring files per changed area). Record the result as **Conventions applied** in the review summary. Never flag something the repository does deliberately and consistently.

### Bugs and security (first)
Does it compile and is new code actually called; logic errors, null handling, concurrency/races, transactions, idempotency, missing timeouts, swallowed errors, money as floating point or unchecked sign, time-zone errors, injection, missing authorization, secrets/PII in logs. For logic and concurrency bugs, state the concrete input or interleaving that breaks the code; policy violations (string-built SQL, secrets in code, floats for money) need no trigger.

### Repository conventions (enforced, `CONV-*`)
New code follows the established naming vocabulary, packaging, module dependency direction, exception hierarchy, logging style, nullability, DI, validation, mapping, test stack and documentation conventions. A change that introduces a second way of doing a cross-cutting thing (second logging facade, second exception root, second mapping style, bypassing the global error handler) is MAJOR. Every `CONV-*` finding cites existing code or a documented rule as evidence.

### Naming (enforced)
- Methods/functions are **action verb + noun** (`calculateInvoiceTotal`, `sendPaymentReminder`); omit the noun only when the receiver already is it (`order.cancel()`).
- **The verb is a contract**: `get` = cheap, no side effects; `find` = may return empty; `fetch`/`load` = I/O; `is/has/can` = boolean; `calculate` = pure; `validate` = no mutation. A name that lies about behaviour is MAJOR.
- No vague verbs (`do`, `process`, `manage`, `perform`, `check`, `handle`) outside their idioms (`handle<Event>` handlers; `do<Verb>` template-method workers behind a public `<verb>`; `check<Condition>` = throw-if-invalid when the repo uses it).
- Types are nouns named by **stereotype and context** (`Order`, `Money`, `PlaceOrderUseCase`, `OrderRepository`, `PostgresOrderRepository`, `StripePaymentGateway`, `InsufficientFundsException`). Interfaces name a role; implementations name their distinguishing trait (`Default*`, technology, added behaviour). `I` prefix only in C#.
- Grab-bag words are findings (`*Manager`, `*Helper`, `*Utils`, `*Data`, `*Info`, `*Impl` unless the repo convention). Framework idioms are not (`Abstract*`, `*Support`, `*Template`/`*Operations`, `*Resolver`, `*Registrar`, `*Customizer`, resource-lifecycle `*Manager`, single-subject static `*Utils` such as `StringUtils`).
- Booleans read as predicates, no boolean flag arguments, no abbreviations, units in names, one word per concept across the codebase.

### Design principles (enforced)
SOLID; DRY (knowledge, not text); KISS; YAGNI; deep modules; Law of Demeter; Tell-Don't-Ask; Command-Query Separation; composition over inheritance; encapsulation and immutability; fail fast at boundaries; illegal states unrepresentable; domain never depends on infrastructure; idempotent handlers and retries. Suggest a pattern only when its force is already present; flag misuse (Singleton as global state, Service Locator, speculative abstractions, deep inheritance, god services).

### Simplicity (no over-engineering, `OVER-*`)
Every new interface, layer, generic, pattern, option, event or wrapper must name the second case or boundary that justifies it now. Interface with one implementation and no I/O boundary, pass-through service layer, Strategy with one strategy, configuration nobody sets, home-made wrapper of a JDK/library type, hooks "for later": findings. Readability: top-down methods, guard clauses, readable streams, why-comments, soft limits (method ≈30 lines, class ≈300, params ≤4, nesting ≤3). Calibration: would Spring Framework / Apache maintainers merge this shape?

### Java / Spring quality bar (`JAVA-*`)
Minimal accessibility; `final`, immutable value types with defensive copies; preconditions with messages; static factories/builders; enums over constants. Exceptions unchecked by default with one root per module, cause chained, contextual message, no swallowing, narrow catches, translated at boundaries, never log-and-rethrow. Logging through the repo's facade with `{}` placeholders, throwable as last argument, correct level, no PII/entities/hot-path logs. `Optional` only as a return type; interface-typed, unmodifiable collections; JUC over `synchronized`; configured executors. Constructor injection; `@Transactional` on the service layer without self-invocation; no business logic or repository calls in controllers; DTOs at the boundary; `@ConfigurationProperties`; no `FetchType.EAGER`; after-commit events; configured HTTP clients with timeouts; one global error handler; test slices. Javadoc on public library API; language features matching the compiler baseline.

### Tests
New behaviour and bug fixes are covered with the repo's stack and naming; tests are deterministic, assert outcomes, and read as specifications.

### How to report
- Each finding: `[SEVERITY][RULE-ID] path:line — problem → concrete fix`, rule IDs from the full standard (`BUG-CONCURRENCY`, `CONV-LOG`, `NAME-M2`, `SOLID-DIP`, `OVER-INTERFACE`, `JAVA-EXC-SWALLOW`).
- Severities: **BLOCKER** (wrong behaviour, security, data loss, breaking change, does not build) · **MAJOR** (risky/costly next change, misleading name, domain→infrastructure dependency, second parallel convention, bypassed global mechanism, missing tests) · **MINOR** (rule or convention violation without immediate risk) · **NIT**.
- Naming and convention findings default to MINOR; MAJOR when the name misrepresents behaviour, the change adds a parallel way for a cross-cutting concern, or the identifier is part of a public API consumed outside its module/service.
- One issue, several rules: list all IDs, use the highest severity; grade combined issues by combined impact.
- The summary includes a **Conventions applied** section. Do not comment on what the formatter/linter already enforces; do not post taste comments without a concrete cost.
- Verdict: REQUEST CHANGES for any BLOCKER/MAJOR; APPROVE WITH COMMENTS when only MINOR/NIT remain; APPROVE when there are no findings.
