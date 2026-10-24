# Correctness, Security and Performance Checklist

Bugs come first. For every suspected bug, write down the concrete input, state or thread interleaving that triggers it. If you cannot, ask a question instead of asserting a bug. Read the callers of changed functions and the tests that cover them.

## BUG — Logic
- [ ] Off-by-one, inclusive/exclusive bounds, empty and single-element collections, first/last iteration.
- [ ] Inverted or incomplete conditions (`&&` vs `||`, `!` misplaced, missing `else`, De Morgan errors); fall-through in `switch`.
- [ ] `null`/`None`/`undefined`/`nil` paths; `Optional.get()` without check; non-null assertions (`!!`, `!`) on values that can be absent.
- [ ] Equality: `==` vs `.equals()` (Java strings/boxed numbers), `==` vs `===` (JS), reference vs value equality, `equals`/`hashCode` consistency, floating-point equality.
- [ ] Numeric: integer overflow, integer division, sign errors, unit mismatches (ms vs s, cents vs units).
- [ ] **Money**: never binary floating point (`float`/`double`/JS `number` for amounts) — use decimal types or integer minor units; explicit rounding mode; currency carried with amount; allocation of remainders (splitting 10.00 three ways); **sign and zero checks** (a negative payout must not credit the account).
- [ ] **Time**: time zones and DST, `LocalDateTime` where an instant is needed, server default zone, end-of-month/leap-year logic, clock injected for testability, timestamps stored in UTC.
- [ ] Parsing/formatting with locale-dependent defaults (decimal separators, case conversion with Turkish `i`).
- [ ] Mutation while iterating; aliasing (two references to the same mutable object); mutable default arguments (Python); shadowed variables.
- [ ] Domain invariants validated where values enter: ranges, signs, required fields, allowed enum values, string codes matched case-sensitively by accident (`"sepa"` vs `"SEPA"`) with a silent `default` branch.
- [ ] State machines: illegal transitions possible; status updated without checking the current status.
- [ ] Copy-paste errors (wrong variable in a duplicated block), unreachable code, unused results (`stream.map(...)` without terminal op, ignored return of immutable `BigDecimal.add`).

## BUG — Build and wiring
- [ ] Every referenced type, method and import resolves; the change compiles (BLOCKER if not).
- [ ] New public code is actually called. Unused new code is either a missing call site (e.g. a fee that is never charged) or dead code.
- [ ] Configuration, DI registrations, routes, migrations and feature flags needed by the change are included.

## BUG — Error handling
(Java/Kotlin: the detailed exception and logging contracts are `JAVA-EXC-*` and `JAVA-LOG-*` in `java-quality-bar.md`; the repo's own hierarchy and facade are `CONV-EXC`/`CONV-LOG`.)
- [ ] Swallowed exceptions (empty `catch`, `except: pass`, ignored Go `err`, unhandled promise rejections).
- [ ] Catch-all that hides programming errors; lost cause/stack trace when wrapping.
- [ ] Log-and-rethrow duplication; logging without context; wrong log level.
- [ ] Partial failure: what happens if step 2 of 3 fails? Is state left inconsistent? Is there a compensation?
- [ ] Retries without idempotency; retrying non-retryable errors (4xx, validation).
- [ ] `finally` blocks that override returns or throw.
- [ ] Error messages leaking secrets/PII or internal details to clients.

## BUG — Resources and lifecycle
- [ ] Streams, files, sockets, DB connections, locks closed on all paths (`try-with-resources`, `using`, `with`, `defer`, `use`).
- [ ] **Timeouts on every remote call** (HTTP, DB, queue); connection pool sizing.
- [ ] Unbounded growth: caches without eviction, queues, in-memory lists of all rows, listeners never removed.
- [ ] Background tasks/threads/goroutines without shutdown or cancellation.

## BUG — Concurrency and transactions
- [ ] Shared mutable state without synchronization; non-thread-safe types shared (`SimpleDateFormat`, `HashMap`, Python lists in threads without locks).
- [ ] Check-then-act races (`if (!exists) create()`), lost updates (read-modify-write without optimistic locking/version column or atomic update).
- [ ] Deadlock risk: inconsistent lock ordering, holding locks while doing I/O.
- [ ] Async: missing `await`, fire-and-forget promises/tasks, blocking calls on event loop/UI thread, `async void` (C#), `runBlocking` in coroutines on request threads, unstructured concurrency.
- [ ] Transaction boundaries: side effects (emails, events, HTTP) inside a transaction that may roll back; transactions spanning remote calls; self-invocation bypassing transactional proxies (Spring).
- [ ] Message consumers: at-least-once delivery handled (idempotent), ordering assumptions, poison messages.

## SEC — Security (OWASP-oriented)
- [ ] Injection: SQL/NoSQL/LDAP/OS command/template — parameterised queries only; no string-built queries with user input.
- [ ] XSS: output encoding; no `innerHTML`/`dangerouslySetInnerHTML`/`v-html` with untrusted data.
- [ ] Authorization on every endpoint and object access (IDOR: can user A read user B's resource by changing an ID?); tenant isolation.
- [ ] Authentication/session: token validation, expiry, secure cookie flags, CSRF protection for cookie-based auth.
- [ ] Secrets: none in code, config committed to git, logs, error messages or URLs.
- [ ] PII/payment data: not logged; masked (PAN, IBAN, email); encrypted at rest where required; data minimisation.
- [ ] Input validation at trust boundaries: size limits, types, allow-lists; file upload type/size checks; path traversal (`../`); SSRF (user-controlled URLs fetched server-side).
- [ ] Unsafe deserialization (Java native serialization, `pickle`, YAML `load`), XML external entities.
- [ ] Crypto: no home-grown crypto; secure random for tokens; modern algorithms; constant-time comparison for secrets/signatures (webhook signature checks).
- [ ] Dependencies: new libraries are maintained, pinned, licence-compatible, and not duplicating an existing library.

## PERF — Performance
- [ ] N+1 queries (lazy loading in loops, a query per item); missing batching.
- [ ] O(n²) or worse on collections that can be large; repeated linear search where a map/set fits.
- [ ] Loading whole tables/files into memory; missing pagination/streaming.
- [ ] New queries without supporting indexes; `SELECT *` on wide tables in hot paths.
- [ ] Expensive work in loops (regex compilation, object mapping setup, logging string building).
- [ ] Chatty remote calls that could be batched; missing caching for hot, stable reads (and stale-cache risk when added).

## API / DATA — Compatibility
- [ ] Public API, event/message schema, and serialized field changes are backward compatible or versioned.
- [ ] DB migrations are backward compatible with the running version (expand → migrate → contract), reversible, and safe on large tables (no long locks).
- [ ] Nullability/optionality changes are reflected in contracts and clients.
- [ ] Defaults changed silently (timeouts, limits, feature flags).

## TEST — Tests
- [ ] New behaviour and changed branches are tested at the right level (unit for rules, integration for persistence/HTTP wiring).
- [ ] Bug fixes include a regression test that fails without the fix.
- [ ] Tests assert outcomes (not just "no exception"); no assertions on implementation details or excessive mocking of types you don't own.
- [ ] Deterministic: no real time, randomness, network, sleep-based waits, or test-order dependence.
- [ ] Edge cases from this checklist covered (empty, null, boundary, error paths, concurrency where relevant).
- [ ] Test names describe behaviour (`should_decline_expired_card`), not methods (`testAuthorize2`).

## OBS — Observability
- [ ] Meaningful structured logs at decision points and failures, with correlation/request IDs; no noisy logs in hot loops.
- [ ] Metrics/alerts for new critical paths (payments, settlements, external integrations).
- [ ] No sensitive data in logs, traces or metrics labels.

## Rule IDs
BUG-BUILD, BUG-WIRING, BUG-LOGIC, BUG-NULL, BUG-EQUALITY, BUG-NUMERIC, BUG-MONEY, BUG-TIME, BUG-ERROR, BUG-RESOURCE, BUG-TIMEOUT, BUG-CONCURRENCY, BUG-ASYNC, BUG-TX, SEC-INJECTION, SEC-XSS, SEC-AUTHZ, SEC-AUTHN, SEC-SECRETS, SEC-PII, SEC-INPUT, SEC-DESERIALIZATION, SEC-CRYPTO, SEC-DEPENDENCY, PERF-NPLUS1, PERF-COMPLEXITY, PERF-MEMORY, PERF-QUERY, API-COMPAT, DATA-MIGRATION, TEST-MISSING, TEST-QUALITY, TEST-FLAKY, OBS-LOGGING.
