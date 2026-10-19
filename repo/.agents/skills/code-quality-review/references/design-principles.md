# Design Principles (enforced)

Apply each principle only to the architecture and contracts in scope. Signals invite investigation; they are not automatic violations. Confirm the concrete cost, check guards, and choose the smallest safe fix. A design finding must cite evidence (`file:line`), name the demonstrated change or operation it makes hard, and propose a fix. "Violates SRP" alone is not a finding.

Contents: 1. SOLID · 2. Simplicity (DRY, KISS, YAGNI) · 3. Coupling and object design · 4. Architecture and boundaries · 5. Robustness · 6. Function-level hygiene · 7. Rule IDs

---

## 1. SOLID

### SOLID-SRP — Single Responsibility
A module should have one reason to change, i.e. answer to one actor/concern.
**Signals**
- One class mixes concerns owned by different people: business rules + persistence + formatting/HTTP + messaging.
- Method names span unrelated verbs and nouns (`calculateFee`, `renderPdf`, `sendEmail` in one class).
- Constructor takes more than ~5–7 dependencies; class longer than ~300–400 lines and growing in this diff.
- Name contains `And`, `Manager`, `Helper`, `Utils` (see NAME-T2).
- A method with a boolean flag that switches between two behaviours.
**Guards:** small cohesive classes with several methods are fine; a facade or use case that *orchestrates* collaborators has one responsibility (orchestration).
**Fix:** extract the second responsibility into its own class behind the existing name's real role; move formatting/persistence to adapters.

### SOLID-OCP — Open/Closed
Add behaviour by adding code, not by editing a growing conditional.
**Signals**
- `switch`/`if-else`/`when` on a type code, enum or `instanceof` that this diff **extends** with another branch, especially when the same switch is duplicated elsewhere.
- Adding a variant requires edits in several files (shotgun surgery).
**Guards:** a two-branch conditional on stable rules; exhaustive `switch` over a sealed type/enum in a language that enforces exhaustiveness (Kotlin `when`, Java 21 pattern switch, Rust `match`, TS discriminated unions with `never` check) — that is safe, compiler-checked branching.
**Fix:** polymorphism (Strategy, State), a registry/map of handlers, or a sealed hierarchy with exhaustive matching.

### SOLID-LSP — Liskov Substitution
Subtypes must honour the base type's contract.
**Signals**
- Overrides that throw `UnsupportedOperationException`/`NotImplementedError` or are no-ops.
- Subtypes that strengthen preconditions (reject inputs the base accepts) or weaken postconditions.
- Callers doing `instanceof`/type checks to special-case a subtype.
- Classic shape: `Square extends Rectangle`, `ReadOnlyList extends MutableList`.
**Guards:** optional operations explicitly permitted by the base contract (for example, an unmodifiable Java collection) do not violate LSP.
**Fix:** split the abstraction (separate read and write interfaces), use composition, or model as distinct types.

### SOLID-ISP — Interface Segregation
Clients should not depend on methods they don't use.
**Signals:** fat interfaces (≈7+ unrelated methods); implementers that stub methods; a client using one method of a large interface; "god" service interfaces injected everywhere.
**Guards:** unused methods alone are insufficient; show coupling to unrelated changes or unsupported obligations.
**Fix:** split by demonstrated client need (role interfaces): `PayoutReader`, `PayoutWriter`.

### SOLID-DIP — Dependency Inversion
High-level policy depends on abstractions it owns; details depend on those abstractions.
**Signals**
- Domain or use-case code instantiates infrastructure: `new SmtpClient()`, `new RestTemplate()`, `HttpClient.create()`, opening DB connections.
- Domain packages import framework/infrastructure packages (ORM annotations in the core domain may be an accepted local trade-off — check `AGENTS.md`/ADRs).
- Static calls to infrastructure or global singletons (`Config.get()`, `Database.instance()`), hidden time/randomness (`now()`, `random()`, `UUID.randomUUID()`) inside business logic that needs testing.
- Service Locator lookups.
**Fix:** define a port interface in the consuming layer (`Clock`, `PaymentGateway`), inject it via constructor, implement it in an adapter.

---

## 2. Simplicity

### DP-DRY — Don't Repeat Yourself (knowledge, not text)
**Signals:** the same business rule/calculation/validation/constant implemented in two or more places; copy-pasted blocks with small edits; parallel switch statements.
**Guards:** similar-looking code that represents *different* knowledge and will evolve independently (incidental duplication) — do not merge it. Apply the rule of three before abstracting test setup or trivial code.
**Fix:** extract the single source of truth (function, value object, policy, constant).

### DP-KISS — Keep It Simple
**Signals:** clever one-liners that need a comment to decode; needless indirection layers; generic frameworks for one use; reflection/metaprogramming where plain code works.
**Fix:** the most direct readable version. Use the specific `READ-*` IDs from `simplicity-and-readability.md` when one fits (`READ-CLEVER`, `READ-SHALLOW`, `READ-GUARD`).

### DP-YAGNI — You Aren't Gonna Need It
**Signals:** interfaces with one implementation and no boundary reason; options with no current variation or operational/compatibility requirement; extension points, abstract factories, plugin systems, or generic type parameters "for the future"; unused parameters, dead code, commented-out code.
**Guards:** boundaries, invariants, published extension/compatibility contracts and current operational needs can justify structure with one implementation; see the simplicity reference.
**Fix:** remove unjustified structure; retain the smallest abstraction that serves a current requirement. Use the specific `OVER-*` IDs from `simplicity-and-readability.md` (`OVER-INTERFACE`, `OVER-LAYER`, `OVER-GENERIC`, `OVER-CONFIG`, `OVER-FUTURE`, `OVER-WRAP`) — they name the missing force, which makes the finding actionable.

### DP-DEEP — Deep modules, information hiding
A good module has a small interface and a large implementation (Ousterhout). **Signals:** pass-through layers, classes whose public surface mirrors their internals, interfaces as wide as the class behind them, implementation details (ORM types, HTTP codes, JSON annotations) leaking through an API. **Fix:** collapse shallow layers; hide the details behind a smaller role interface (`READ-SHALLOW`, `READ-LEAK`).

---

## 3. Coupling and object design

### DP-LOD — Law of Demeter (talk to friends, not strangers)
**Signals:** train wrecks reaching through objects: `order.getCustomer().getAddress().getCountry().getCode()`.
**Guards:** fluent APIs, builders, stream/LINQ pipelines, and plain data structures/DTOs are fine.
**Fix:** ask the nearest object for what you need (`order.shippingCountryCode()`), or pass the needed value in.

### DP-TDA — Tell, Don't Ask
**Signals:** callers pull state out of an object, decide, and push state back (`if (account.getBalance() >= amt) account.setBalance(account.getBalance() - amt)`).
**Fix:** move the behaviour to the object that owns the data (`account.withdraw(amt)`) — the Information Expert.

### DP-CQS — Command-Query Separation
A method either changes state (command) or returns data (query), not both.
**Signals:** getters/predicates with side effects; `validate()` that also saves; methods returning a value *and* mutating hidden state.
**Guards:** well-known idioms (`stack.pop()`, `iterator.next()`, `map.putIfAbsent`, atomic `getAndIncrement`, create-and-return-id).
**Fix:** split into a command and a query, or rename to reveal the side effect (NAME-M2).

### DP-COMP — Composition over inheritance
**Signals:** inheritance used for code reuse rather than a true is-a relationship; hierarchies deeper than 2–3 levels; subclasses overriding to disable behaviour; protected mutable state shared down the hierarchy; Template Method chains that are hard to follow.
**Fix:** inject collaborators (Strategy, Decorator); prefer interfaces + delegation; close types only when framework proxies, persistence and extension contracts permit it.

### DP-ENC — Encapsulation
**Signals:** public mutable fields; getters and setters for every field (anemic objects) where invariants exist; returning internal mutable collections; setters that bypass validation; invariants enforced by callers instead of the object.
**Fix:** expose behaviour, not state; return unmodifiable views/copies; validate in constructors/factories.

### DP-COH — High cohesion, low coupling
**Signals:** a change in one module forces changes in many (shotgun surgery); a class that uses another class's data more than its own (feature envy); bidirectional dependencies; package cycles.
**Fix:** move behaviour to where the data lives; introduce an interface to break a cycle; regroup by feature.

### DP-GRASP — Responsibility assignment
Information Expert (behaviour lives with the data), Creator (the aggregate creates its parts), Controller (a thin coordinator for a use case), Pure Fabrication (a service when no domain object fits), Indirection/Protected Variations (an interface around what is likely to change), Polymorphism (instead of type switches). Use these names to justify "move this method to X" findings.

---

## 4. Architecture and boundaries

### DP-LAYER — Dependency rule (Clean / Hexagonal / Onion)
Dependencies point inward: adapters → application → domain. The domain knows nothing about HTTP, SQL, queues, frameworks or UI.
**Signals:** domain imports web/ORM/messaging packages; controllers containing business rules; repositories containing business rules; domain objects serialised directly as API responses (leaks internals, couples API to model); cross-module access to another module's internals or tables.
**Guards:** respect the project's documented architecture (ADRs, `AGENTS.md`); small CRUD services may deliberately be layered more thinly — flag only when the code mixes the levels it already has.
**Fix:** move the rule to the domain/use case; introduce DTO + mapper at the boundary; add a port.

### DP-DDD — Domain modelling (when the codebase is domain-driven)
- Aggregates protect invariants; modify only through the root; one aggregate per transaction where possible; reference other aggregates by ID.
- Value objects are immutable and validated on creation (`Money`, `Iban`).
- Ubiquitous language: names in code match the business terms used in tickets/docs.
- Anemic-model findings require a DDD contract and a concrete invariant/cohesion cost. Transaction-script or data-centric architectures are valid; do not request DDD solely as a preference.
- Anti-corruption layer translates external models; external DTOs must not leak into the domain.

### DP-API — Public contracts
Backward-compatible API/schema/message changes; versioning when breaking; explicit nullability; no leaking of internal types across module boundaries.

---

## 5. Robustness

### DP-FAIL — Fail fast, validate at the boundary
Validate inputs where they enter (controller, message consumer, public method) and reject invalid state immediately with a precise error; don't let `null`/invalid values travel deep. **Parse, don't validate:** convert raw input into a type that cannot be invalid (`Iban.parse(raw)`).

### DP-TYPES — Make illegal states unrepresentable
**Signals:** primitive obsession (money as `double`, IDs as raw `String`/`long` that can be swapped, status as free `String`); data clumps (`street, city, zip` passed together); boolean blindness (`isActive, isSuspended, isClosed` that can contradict each other).
**Guards:** a primitive is acceptable when it carries no independent invariant or demonstrated confusion risk. Avoid wrapping every identifier mechanically.
**Fix:** value objects, enums/sealed types, a single state field with explicit transitions.

### DP-IMM — Immutability by default
Prefer immutable value objects, `final`/`val`/`readonly`/`const`, and pure functions; isolate mutation; never share mutable state across threads without synchronization.

### DP-IDEM — Idempotency and side-effect safety
Message handlers, webhooks, retries and payment operations must be idempotent (idempotency key, dedupe, upsert). Side effects (emails, events, external calls) must not happen inside a transaction that may roll back — use an outbox or after-commit hooks.

### DP-POLA — Least astonishment
Behaviour matches what the name, signature and conventions suggest (see NAME-M2); no hidden global state changes; consistent error-handling style (exceptions vs result types) within a module.

---

## 6. Function-level hygiene (DP-FUNC)

Soft limits — flag when exceeded **and** readability suffers, not mechanically:
- Length ≈ 30 lines (excluding declarations); one level of abstraction per function (DP-SLAP: don't mix high-level steps with low-level byte fiddling).
- Parameters ≤ 3–4; more → parameter object or builder. No output parameters.
- Nesting ≤ 3 levels; use guard clauses / early returns.
- Cyclomatic complexity ≈ ≤ 10.
- No hidden side effects; no magic numbers/strings (NAME-C1).
- Comments explain *why*, not *what*; no commented-out code; TODOs reference a ticket.

---

## 7. Rule IDs

SOLID-SRP, SOLID-OCP, SOLID-LSP, SOLID-ISP, SOLID-DIP, DP-DRY, DP-KISS, DP-YAGNI, DP-DEEP, DP-LOD, DP-TDA, DP-CQS, DP-COMP, DP-ENC, DP-COH, DP-GRASP, DP-LAYER, DP-DDD, DP-API, DP-FAIL, DP-TYPES, DP-IMM, DP-IDEM, DP-POLA, DP-SLAP, DP-FUNC.

**Simplicity tie-breaker:** a principle is never a licence for more structure than the diff needs (SRP ≠ one method per class; DIP ≠ interface everything; OCP ≠ a Strategy for every `if`). When a SOLID fix adds cost without a present requirement, protected invariant or boundary benefit, do not propose it; see `simplicity-and-readability.md` §5.

Severity follows concrete impact: materially risky changes → **MAJOR**; contained maintenance costs → **MINOR**. Core/shared location alone does not raise severity. When the same issue also maps to a PAT-*/SMELL-* ID, report all IDs and use the highest severity. DP-LAYER and SOLID-DIP violations that put infrastructure inside the domain → **MAJOR**. DP-IDEM issues in payment/money paths → **BLOCKER** if a retry can double-charge or double-pay.
