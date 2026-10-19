# Design Patterns and Code Smells

Patterns are tools, not goals. Flag a **missing** pattern only when the force it resolves is already present in the code (not hypothetically). Flag a **misused** pattern when it adds indirection without resolving a force. Name the pattern in the finding so the author can look it up, and show the target shape in a few lines.

Contents: 1. Force → pattern table · 2. Modern/enterprise patterns · 3. Pattern misuse · 4. Code smells catalogue · 5. Rule IDs

---

## 1. Force → pattern (GoF and friends)

| Force visible in the code | Pattern to suggest | Notes / prefer simpler when |
| --- | --- | --- |
| Type/enum switch that keeps growing; same switch duplicated | **Strategy**, **State**, polymorphism | A sealed type + exhaustive match is fine if the compiler enforces exhaustiveness |
| Behaviour depends on lifecycle state with guarded transitions | **State** (or explicit state machine) | An enum + transition table can be enough |
| Telescoping constructors, many optional parameters, invalid half-built objects | **Builder** (or named/default args, records + `with`) | Kotlin/Python/C# named args often remove the need |
| `new` of varying concrete types spread around; creation logic duplicated | **Factory Method** / static factory / **Abstract Factory** (families of related objects) | One product, one variant → plain constructor |
| Third-party/legacy API shape leaking into the code | **Adapter** (+ anti-corruption layer) | — |
| Add caching/retry/logging/metrics/authorization around an existing interface | **Decorator** (or middleware/interceptor) | Don't subclass to add cross-cutting behaviour |
| Complex subsystem used through many calls everywhere | **Facade** | — |
| Lazy loading, remote access, access control | **Proxy** | — |
| One-to-many notifications; modules that must not know each other | **Observer** / domain events / pub-sub | Synchronous call is simpler if there is exactly one listener that must succeed |
| Requests as objects: queueing, undo, audit, retries | **Command** | — |
| Ordered processing steps that can short-circuit (validation, middleware) | **Chain of Responsibility** / pipeline | — |
| Part-whole trees treated uniformly | **Composite** | — |
| Algorithm skeleton with varying steps | **Template Method** | Prefer Strategy/composition in new code |
| Operations over a closed set of types | **Visitor** | Modern languages: sealed types + pattern matching is usually clearer |
| Absent collaborator causing `null` checks everywhere | **Null Object** / `Optional`/`Maybe` | — |
| Many identical immutable objects in memory | **Flyweight** | Rarely needed; measure first |

## 2. Modern application and distributed-system patterns

| Force | Pattern |
| --- | --- |
| Business logic mixed with SQL/ORM calls | **Repository** (+ **Unit of Work** for transactional consistency) |
| Combinable, reusable business rules / query criteria | **Specification** |
| Expected failures modelled with exceptions or `null`s | **Result/Either** type (if the codebase uses one) |
| Same constructor-injected collaborators manually wired everywhere | **Dependency Injection** (container or manual composition root) |
| Domain depends on frameworks or I/O | **Ports and Adapters (Hexagonal)** |
| External model shapes leaking in | **Anti-Corruption Layer** |
| Read and write models diverge (different shapes/scaling) | **CQRS** (only then) |
| DB write + message publish must both happen | **Transactional Outbox** |
| Multi-service business transaction | **Saga** (orchestration/choreography) with compensations |
| Remote calls without protection | **Timeout + Retry with exponential backoff and jitter + Circuit Breaker + Bulkhead** |
| Duplicate deliveries/retries possible | **Idempotency key / Idempotent consumer** |
| Expensive repeated reads | **Cache-aside** with explicit invalidation and TTL |
| Feature rollout risk | **Feature flag** / **Branch by abstraction** |
| Immutable configuration/values passed around | **Value Object**, **Parameter Object** |

### Framework patterns to recognise (Spring / Apache)
Template Method for resource handling (`*Operations` interface + `*Template` class), `Abstract*`/`*Support` skeletal bases, `*Resolver`/`*Registrar`/`*Customizer`/`*PostProcessor` hooks, `*Aware` callbacks, Adapter at integration points, Strategy via injected collaborators, Decorator via proxies/interceptors. These are the right shapes in a Spring codebase; prefer the framework's extension point over a home-made mechanism (`OVER-WRAP`). Names: `java-quality-bar.md` §10.

## 3. Pattern misuse (flag these)

| ID | Misuse | Why it hurts | Fix |
| --- | --- | --- | --- |
| PAT-SINGLETON | Singleton holding global mutable state or accessed statically | Hidden dependency, untestable, thread-safety risk | DI-managed single instance, injected |
| PAT-LOCATOR | Service Locator (`ServiceLocator.get(X.class)`, `container.resolve` inside business code) | Hidden dependencies, runtime failures | Constructor injection |
| PAT-SPECULATIVE | Abstract Factory/Strategy/plugin system with one implementation and no current variation | Indirection without benefit (YAGNI) | Inline until the second case exists (prefer the specific `OVER-PATTERN`/`OVER-INTERFACE` ID) |
| PAT-DEEP-INHERITANCE | 3+ levels, or inheritance for reuse | Fragile base class | Composition / Strategy / Decorator |
| PAT-ANEMIC | Entities as data bags + "service" classes holding all rules (in a DDD codebase) | Invariants scattered, duplicated | Move behaviour into aggregates/value objects |
| PAT-GOD-SERVICE | One service/controller orchestrating everything | SRP, merge conflicts, untestable | Split by use case |
| PAT-OBSERVER-ABUSE | Events used for synchronous request/response, or event chains that hide control flow | Debuggability, ordering bugs | Direct call, or explicit saga |
| PAT-REPO-LEAK | Repository returning ORM query builders/entities with lazy proxies to upper layers | Leaky abstraction, N+1 | Return domain objects / projections |
| PAT-EXCEPTION-FLOW | Exceptions for normal control flow | Cost and readability | Result type / Optional / guard |

## 4. Code smells catalogue (SMELL-*)

| ID | Smell | Typical fix |
| --- | --- | --- |
| SMELL-LONG-METHOD | Long method / mixed abstraction levels | Extract method; compose method |
| SMELL-LARGE-CLASS | God object | Extract class by responsibility |
| SMELL-LONG-PARAMS | Long parameter list | Parameter object / builder |
| SMELL-DATA-CLUMPS | Same group of values passed together | Value object |
| SMELL-PRIMITIVE-OBSESSION | Money/IDs/status as primitives | Value objects / enums |
| SMELL-FEATURE-ENVY | Method uses another class's data more than its own | Move method |
| SMELL-SHOTGUN-SURGERY | One change → many files | Consolidate the responsibility |
| SMELL-DIVERGENT-CHANGE | One class changes for many reasons | Split class (SRP) |
| SMELL-SWITCH | Repeated type switches | Polymorphism |
| SMELL-MESSAGE-CHAIN | `a.b().c().d()` | Hide delegate (LoD) |
| SMELL-MIDDLE-MAN | Class that only delegates | Inline it |
| SMELL-INTIMACY | Classes reaching into each other's internals | Move behaviour / narrow interface |
| SMELL-REFUSED-BEQUEST | Subclass ignores inherited behaviour | Replace inheritance with delegation |
| SMELL-TEMPORAL-COUPLING | Methods must be called in a hidden order (`init()` before `use()`) | Constructor/builder enforces order |
| SMELL-BOOLEAN-BLINDNESS | Several booleans encoding one state | Enum / sealed state |
| SMELL-MAGIC-VALUES | Unnamed literals | Named constants / config |
| SMELL-DEAD-CODE | Unused code, commented-out code, unreachable branches | Delete |
| SMELL-SPECULATIVE-GENERALITY | Hooks/params for imagined futures | Delete (YAGNI) |
| SMELL-INAPPROPRIATE-STATIC | Static methods with side effects or hidden state | Instance + injection |

## 5. Rule IDs
`PAT-MISSING-<PATTERN>` (e.g. `PAT-MISSING-STRATEGY`), the PAT-* misuse IDs above, and SMELL-* IDs. Default severity MINOR; MAJOR when the smell is introduced in core/shared code and the diff already shows the cost (e.g. this PR had to touch 5 files to add one variant). If the same issue is also a SOLID/DP violation, report both IDs and use the higher severity.
