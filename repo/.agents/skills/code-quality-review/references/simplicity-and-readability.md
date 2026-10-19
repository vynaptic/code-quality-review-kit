# Simplicity and Readability — the over-engineering guard

Code must be as simple as the problem, not simpler and not more general. SOLID and patterns are tools for managing complexity that **exists**; applied to complexity that is only imagined, they *are* the complexity. For every new abstraction in a diff, ask two questions:

1. **What concrete second case, or which architectural boundary, justifies this now?** If the answer is "a future requirement", it is a finding.
2. **Is the interface simpler than the implementation it hides?** A module is *deep* when a small interface hides a lot of work (`list.sort()`, `JdbcTemplate.query(...)`). It is *shallow* when the interface is as complex as the code behind it (a service whose every method forwards to a repository). Shallow modules add cost without hiding anything.

Readability is judged from the reader's side: a competent engineer new to the module should follow the change top-down without opening other files or decoding tricks.

Contents: 1. Abstraction budget (OVER-*) · 2. Deep modules and information hiding · 3. Readability (READ-*) · 4. The Spring test · 5. When principles collide with simplicity · 6. Rule IDs

---

## 1. Abstraction budget (OVER-*)

| ID | Signal in the diff | Guard (do not flag when) | Fix |
| --- | --- | --- | --- |
| OVER-INTERFACE | Interface with exactly one implementation in the same module, introduced in this diff | It is a port at a boundary (I/O, external system, clock, randomness), a published extension point, or the repo convention mandates it | Use the class; extract the interface when the second implementation arrives |
| OVER-LAYER | A layer that only forwards calls (`service.findX(id)` → `repository.findX(id)` with nothing added); "manager calls helper calls util"; a use case class per trivial CRUD read | The repo's architecture mandates the layer uniformly (then it is `CONV-*`-consistent; note the cost once under Questions) | Collapse; call the lower layer directly |
| OVER-GENERIC | Type parameters, generic "engines", reflection-driven registries, plugin mechanisms, annotation processors for one concrete case | The genericity is already exercised by ≥2 real type arguments in the diff or codebase | Concrete types |
| OVER-PATTERN | GoF pattern without its force: Factory for one product, Builder for 2 fields, Strategy with one strategy, Observer with one synchronous listener, Visitor over two types, Command objects for one direct call, Decorator that adds nothing | The force is present (see `design-patterns.md` force table) | Direct code |
| OVER-CONFIG | Configuration keys, feature flags, constructor options, or parameters for things nobody varies; "configurable" constants; decisions pushed to the caller ("let the user choose the retry count") | A second deployment/tenant/test actually sets the value | Hard-code the sensible value; expose when needed |
| OVER-INDIRECTION | Events, callbacks, async or queues where a direct synchronous call is correct and simpler; DI for trivially constructible values (`new ArrayList<>()`, `Clock.systemUTC()` is fine to inject); mapping between two identically-shaped types that are not at a boundary | Cross-module decoupling that is already needed, or a transactional/out-of-process boundary | Direct call; single type |
| OVER-SPLIT | One idea fragmented across many tiny classes/files; 3-line private methods used once that force the reader to jump; "shallow classes" whose public surface equals their implementation | Extraction that names a concept, removes duplication, or isolates a side effect | Inline; keep an idea in one place |
| OVER-FUTURE | Unused parameters, hooks "for later", abstract base with one subclass, `v2` of an API with no `v1` consumer difference, `enabled` flags defaulting to the only used value, `TODO: make pluggable` | Nothing — this is YAGNI by definition | Delete; add when needed |
| OVER-WRAP | Wrapping well-known types in home-made equivalents (own `Result`, own `Optional`, own `Pair`, own HTTP/JSON client wrapper) without adding behaviour; re-implementing utilities that exist in the JDK or an already-present library (`StringUtils`, `Objects`, `Collectors`, Guava, Commons) | The wrapper is the repo's documented anti-corruption layer, or the behaviour genuinely differs | Use the existing type/utility (`CONV-DEP`) |
| OVER-DEFENSIVE | Null checks, try/catch, validation and logging repeated at every layer for the same value; "just in case" fallbacks that hide bugs | Trust boundary (external input) | Validate once at the boundary (`DP-FAIL`), trust inside |

Default severity **MINOR**. **MAJOR** when the abstraction lives in shared/core code, forces the next change to touch more files, or hides the behaviour behind indirection a reader cannot follow (events, reflection, dynamic registries).

Finding format: name the missing force explicitly — "no second implementation exists or is planned in this PR; the only consumer is `RefundService`".

---

## 2. Deep modules and information hiding

| ID | Signal | Fix |
| --- | --- | --- |
| READ-SHALLOW | Pass-through methods (same signature in, same call out); classes exposing every internal as a getter; "decorators" that call through unchanged; one-method-per-step classes where a single method would read as a list of steps | Merge into a deep module with a small interface; keep the steps as private methods in one class |
| READ-LEAK | Implementation details in the interface: a use case depending on `JpaOrderRepositoryImpl`; HTTP status codes in the domain; JSON annotations on domain objects; `Pageable` leaking into the domain API | Depend on the role; translate at the boundary |
| READ-CHANGE-AMPLIFICATION | The diff touches many files to make one conceptual change (a new field needs DTO + mapper + entity + validator + builder + test fixture edits) | Note the amplification and the abstraction causing it; propose consolidating (records, fewer layers) |
| READ-COGNITIVE-LOAD | To understand one method the reader must hold several unrelated concepts, flags, or hidden states in mind (global mutable state, action at a distance, magic defaults) | Localise state; make inputs explicit |

A deep module is the goal of both SOLID and simplicity. "Single responsibility" means one *reason to change*, not one method; "dependency inversion" means depending on a role at a boundary, not interfacing everything.

---

## 3. Readability (READ-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| READ-INTENT | A method reads top-down as its name promises; its body is the story at one level of abstraction (`DP-SLAP`); complex conditions get an explanatory variable or predicate method | A reader needs a comment or a debugger to follow the control flow; `if (a && (b \|\| !c) && d.size() > 1)` inline | Extract `isEligibleForInstantRefund(...)` |
| READ-GUARD | Guard clauses and early returns; no `else` after `return`; nesting ≤ 3; positive conditions (`if (isValid)` not `if (!isInvalid)`); no `!(a && b)` | Arrow-shaped code | Invert and return early |
| READ-STREAM | Streams/lambdas only when they read better than a loop; one pipeline, one idea | A pipeline with `flatMap` + `collect(groupingBy(..., mapping(...)))` that needs 30 seconds to parse | Loop, or named intermediate steps |
| READ-CLEVER | No cleverness: nested ternaries, bit tricks, regex monsters, reflection hacks, side effects in expressions, `Optional` gymnastics, operator overloading surprises | Code that invites a "neat trick" comment | The plain version |
| READ-SIZE | Soft limits: method ≈ 30 lines (excluding signature), class ≈ 300 lines, parameters ≤ 4, nesting ≤ 3, cyclomatic ≈ 10 — flag only when reading actually suffers | A 120-line method; a 9-parameter constructor | Extract by concept; parameter object |
| READ-COMMENT | Comments say *why*; a wrong comment is a bug; no commented-out code; no narration of the obvious | `// loop over items`; comment contradicts code | Fix or delete |
| READ-CONSISTENT | Same thing looks the same: parameter order (`from, to`), symmetrical pairs (`open/close`, `add/remove`), member order, naming across siblings | `save(entity, user)` here, `save(user, entity)` there | Align with neighbours (`CONV-STYLE`) |
| READ-LOCALITY | Declare variables near use; related code adjacent; behaviour visible where it is invoked (no hidden listeners, aspects, or static hooks changing what a call does) | A field declared 200 lines above its only use; an aspect silently retrying | Move; make explicit |
| READ-NAMES | Names carry the meaning so the code needs no comment (see `naming-conventions.md`); no abbreviations; units in names | `calc(d, r)` | `calculateDiscount(price, rate)` |
| READ-DIFF | The PR is one coherent change: no drive-by reformatting, mass renames or unrelated refactors mixed with behaviour changes; large renames go in their own commit | A 40-file "fix typo + migrate logger + add feature" PR | Split (request as a Question, not a finding, unless review is impossible) |
| READ-MAGIC | No magic literals; named constants or enums (`NAME-C1`) | `if (retries > 5)` | `MAX_PAYOUT_RETRIES` |
| READ-ERROR-PATH | The happy path is visible; error handling does not dominate the method; failures are handled in one place | Try/catch around every statement | Extract; translate once |
| READ-TEST | Tests read as specifications: arrange/act/assert visible, one behaviour per test, no logic in tests, fixtures/builders for setup | A test with loops, ifs, and 6 mocks | Builder + focused test |

Default severity **MINOR**; **NIT** for cosmetic items; **MAJOR** only when readability hides a behaviour the reviewer could not verify (then it is also a question for the author).

---

## 4. The Spring test (calibration)

Imagine the diff as a PR to Spring Framework, Spring Boot, or an Apache Commons/Kafka/Camel module. Maintainers there favour:

- **Plain Java**: small final classes, explicit constructors, records for values, no clever generics.
- **Well-known patterns only where the force is present**: Template Method for resource handling, Strategy for real variants, Adapter at integration points — never a plugin system for one case.
- **Contracts stated**: nullability, thread-safety, exceptions, immutability in Javadoc and types.
- **Consistency with the surrounding code** above personal taste.
- **Reviewable size**: one concept per PR.

Complexity you may add in a PR without a second case: a port interface at an I/O boundary; a value object replacing a primitive that already has rules; a named constant; a private method that names a step; a record for a data clump.

Complexity you may **not** add without a second case: an interface for a service class; a generic base class; a strategy registry; an event bus; a configuration option; a `Utils` class; a new layer; a new module; a new framework or library.

---

## 5. When principles collide with simplicity

| Principle | Not a licence for | Tie-breaker |
| --- | --- | --- |
| SRP | One class per method | One *reason to change*; a cohesive 200-line class is fine |
| OCP | A Strategy for every `if` | Polymorphism when the `switch` is already duplicated or growing in this diff (`SOLID-OCP` guards) |
| DIP | An interface for every class | Depend on roles at boundaries; inside a module depend on classes |
| DRY | Abstracting two similar-looking blocks | Rule of three; prefer duplication over the wrong abstraction when the knowledge differs |
| LoD | A delegate method for every access | Only when the chain reaches through mutable collaborators |
| Patterns | Showing the catalogue | Name the force first; the simplest structure that resolves it |
| Testability | Interfaces and injection everywhere | Constructor injection of real collaborators; mock only at process boundaries |

Rule: **prefer the simpler code until the second case arrives**. Refactoring simple, tested code later is cheap; unwinding a speculative abstraction is not.

---

## 6. Rule IDs

`OVER-INTERFACE`, `OVER-LAYER`, `OVER-GENERIC`, `OVER-PATTERN`, `OVER-CONFIG`, `OVER-INDIRECTION`, `OVER-SPLIT`, `OVER-FUTURE`, `OVER-WRAP`, `OVER-DEFENSIVE`, `READ-SHALLOW`, `READ-LEAK`, `READ-CHANGE-AMPLIFICATION`, `READ-COGNITIVE-LOAD`, `READ-INTENT`, `READ-GUARD`, `READ-STREAM`, `READ-CLEVER`, `READ-SIZE`, `READ-COMMENT`, `READ-CONSISTENT`, `READ-LOCALITY`, `READ-NAMES`, `READ-DIFF`, `READ-MAGIC`, `READ-ERROR-PATH`, `READ-TEST`.

`OVER-*` findings replace the older `DP-YAGNI`/`DP-KISS`/`PAT-SPECULATIVE` wording when more specific; list both IDs when a design rule also applies and use the highest severity.
