# Review overrides (optional, per repository)

Rules written here take precedence over the defaults in `.agents/skills/code-quality-review/` **and** over conventions the reviewer infers from the codebase. Reviewers (Devin, Codex, Claude Code, Factory Droid, humans) read this file before reviewing.

**Only uncommented lines are active.** Everything inside `<!-- -->` below is an example; move a line out of the comment to activate it. As shipped, no overrides are active. Overrides may adjust style rules, architecture rules, severities and scope; they cannot waive BLOCKER-level bugs or security findings.

## Conventions (tell the reviewer what the profile might misread)
<!-- Examples — uncomment and adapt:
- Logging: SLF4J via Lombok `@Slf4j`; field is `log`; use `{}` placeholders; INFO only for business events (one line per settlement batch, never per item).
- Exceptions: every domain error extends `BillingException(ErrorCode, message)`; `GlobalExceptionHandler` maps `ErrorCode` to HTTP; never throw raw `RuntimeException`/`IllegalStateException` from service code.
- Packaging: package-by-feature under `com.acme.billing.<feature>`; shared code only in `common/`; no `util` packages.
- Modules: `*-api` modules expose ports only; `*-impl` modules are never a compile dependency of another feature module.
- Nullability: JSpecify `@NullMarked` on every package; `Optional` only as a return type of `find*` methods.
- DI: constructor injection via Lombok `@RequiredArgsConstructor`; `@Autowired` is a finding.
- Tests: JUnit 5 + AssertJ; classes `*Tests`; methods `should<Outcome>When<Condition>`; Testcontainers for persistence, no H2.
- The 9 legacy `*Impl` classes under `legacy/` are grandfathered; new implementations are named by trait (`Default*`, technology).
-->

## Naming
<!-- Examples:
- DTO suffix: use `Dto` (not `Request`/`Response`) for API models.
- Domain events end in `Event` (`OrderPlacedEvent`).
- Remote reads use `fetch`; `load` is reserved for file/classpath resources; repository lookups use `find`.
- Approved domain verbs (also add them to assets/naming-rules.json): settle, chargeback, onboard.
- `check<Condition>` means "throw if invalid" in this codebase (Spring style) and is allowed.
- Swift: follow Apple's API Design Guidelines (noun phrases for side-effect-free methods).
-->

## Architecture
<!-- Examples:
- Hexagonal: domain in `core/`, adapters in `adapters/`; JPA annotations are allowed in domain entities (ADR-007).
- Use cases are named `<Verb><Noun>UseCase` and live in `application/`.
- A service layer is mandatory for every controller even for simple CRUD (team decision 2025-03); do not report pass-through services as OVER-LAYER.
-->

## Severity adjustments
<!-- Examples:
- Treat any naming violation in `api/` (public API) as MAJOR.
- Treat missing tests for `payments/` as BLOCKER.
- Treat `FetchType.EAGER` as MAJOR anywhere.
-->

## Out of scope
<!-- Examples:
- Generated code under `gen/` and database migrations under `db/migrations/`.
- Formatting: Spotless runs in CI; never comment on formatting or import order.
-->
