# Naming Conventions (enforced)

Names are the cheapest documentation and the most common source of misunderstanding. Review every **new or renamed** identifier in the change. The approved and vague verb lists live in `../assets/naming-rules.json`; keep that file as the single source of truth when the team extends the vocabulary.

**Precedence:** an established repository convention (see `repo-conventions.md`: documented, or ≥3 existing occurrences with no stronger competitor) wins over every *stylistic* rule in this file — suffixes (`*Impl`, `*Dao`, `*Dto`), read verbs (`fetch` vs `retrieve`), `I` prefixes, test names. Only `NAME-M2` (a name that lies about behaviour) never yields, because it is a correctness problem, not a style choice. Framework idioms used by Spring and Apache projects are listed in `java-quality-bar.md` §10 and are never violations.

Contents: 1. Methods and functions · 2. Verb contracts · 3. Types (classes, interfaces, structs, enums) · 4. Variables, fields, parameters, constants · 5. Language idioms and exemptions · 6. Framework idioms · 7. Rule IDs

---

## 1. Methods and functions

### NAME-M1 — Action verb + noun
Form: `<verb><Noun>[<Qualifier>]`, in the language's casing.

| ✅ Good | ❌ Bad | Why |
| --- | --- | --- |
| `calculateInvoiceTotal()` | `invoiceTotal()` (as a computing method) | starts with a noun; reads like a field |
| `sendPaymentReminder(customer)` | `reminder(customer)` | no action |
| `findCustomerById(id)` | `customer(id)` | no action, unclear contract |
| `parseSettlementFile(path)` | `settlement(path)` | no action |
| `archiveExpiredQuotes()` | `expired()` | no action, no object |

**Receiver rule (avoid noise):** omit the noun when the receiver already *is* that noun.
`order.cancel()` ✅ — `order.cancelOrder()` ❌ (NAME-M6, redundant context).
`customerRepository.findById(id)` ✅ — `customerRepository.findCustomerById(id)` acceptable but redundant.
A **top-level / free function** has no receiver, so it always needs the noun: `validate()` ❌ → `validateIban()` ✅.

**Qualifiers** go after the noun: `findOrdersByStatus`, `calculateFeeForMerchant`, `loadConfigFromEnvironment`.

### NAME-M3 — No vague verbs
`do`, `process`, `manage`, `perform`, `handle`, `check`, `deal`, `make`, `go`, `work`, `operate`, `treat` say nothing about the outcome (authoritative list: `vague_verbs` in `../assets/naming-rules.json`).

| ❌ Vague | ✅ Intention-revealing |
| --- | --- |
| `processPayment` | `authorizePayment`, `capturePayment`, `refundPayment` (whichever it actually does) |
| `handleOrder` | `fulfilOrder`, `routeOrderToWarehouse` |
| `checkLimit` | `isWithinLimit` (returns bool) or `ensureWithinLimit` (throws) |
| `doSync` | `synchronizeLedgerEntries` |
| `manageSessions` | `expireIdleSessions` |

Allowed exceptions: `handle<EventOrCommand>` on an event/command handler (`handleOrderPlaced`), `on<Event>` for callbacks (`onPaymentFailed`), `execute`/`run` when implementing a framework contract (Command pattern, `Runnable`, job runner) or a well-known API (`executeQuery`).

Two framework idioms are also allowed: `do<Verb><Noun>` as the protected/private worker behind a public `<verb><Noun>` template method (Spring: `getBean` → `doGetBean`, `filter` → `doFilterInternal`) — acceptable only when that public method exists; and `check<Condition>` meaning "throw if the condition fails" when the repository already uses `check*` that way (Spring: `checkRequiredFields`). Otherwise `do`/`check` stay vague.

### NAME-M4 — Predicates read as questions
Boolean-returning methods start with `is`, `has`, `can`, `should`, `contains`, `exists`, `supports`, `matches`, `equals`, `needs`, `allows`, `accepts`, `was`, `will`, `are`, `does`.
`isSettled()`, `hasOpenDisputes()`, `canRefund(amount)`. Prefer positive forms: `isEnabled` not `isNotDisabled`.

### NAME-M5 — No boolean flag arguments
`createUser(data, true)` hides intent at the call site and usually means the method does two things (SRP).
Fix: split (`createActiveUser`, `createPendingUser`), use an enum (`createUser(data, ActivationMode.PENDING)`), or named/keyword arguments where the language supports them (`create_user(data, send_welcome_email=True)` is acceptable in Python/Kotlin/C#/Swift).
Exempt: setters and toggles (`setEnabled(boolean)`, `withRetries(boolean)`).

### NAME-M6 — No redundant context
Don't repeat the class, module or package name: `Order.cancelOrder()` → `Order.cancel()`; `billing.BillingInvoice` → `billing.Invoice`; Go `user.UserService` → `user.Service`.

### NAME-M7 — Consistent async naming
C#: async methods end in `Async` (`LoadOrderAsync`). Other languages: no suffix; the type (`Promise`, `suspend`, `Future`) carries it. Never mix both styles in one codebase.

---

## 2. Verb contracts (NAME-M2) — the name must not lie

A name that promises one behaviour and does another is a **MAJOR** finding, because callers will rely on the promise.

| Verb | Contract the caller can rely on | Typical lie to flag |
| --- | --- | --- |
| `get` | Returns an existing value; cheap; no side effects; no remote I/O | `getUser()` that calls an API, writes a cache, or creates the user if missing |
| `find` | Lookup that may return nothing (`Optional`/`null`/`None`/empty) | `findX` that throws on not-found |
| `fetch`, `load`, `read` | Performs I/O (network, DB, disk); may be slow or fail | — (good: signals cost) |
| `list` | Returns a collection (possibly empty), never `null` | returns `null` |
| `search`, `query` | Criteria-based retrieval, possibly paged | — |
| `count` | Returns a number, no materialisation of entities | loads all rows then `.size()` |
| `create`, `new`, `build`, `generate` | Returns a new object/resource | mutates and returns an existing one |
| `calculate`, `compute`, `derive`, `estimate` | Pure derivation from inputs; no side effects | persists or logs business events |
| `is`, `has`, `can`, … | Returns boolean; no side effects | returns a result object, or mutates state |
| `validate`, `verify` | Checks; does not mutate the subject; returns result or throws (be consistent) | "validate" that also normalises/saves |
| `ensure`, `require` | Throws if the condition fails | silently returns `false` |
| `to`, `as`, `convert`, `map`, `parse`, `format`, `serialize`, `encode` | Transformation; input unchanged | mutates the input |
| `set`, `update`, `add`, `remove`, `delete`, `clear`, `reset`, `mark`, `assign`, `apply` | Mutation | `remove` that only flags (call it `markRemoved`/`archive`) |
| `delete` vs `archive`/`deactivate` | `delete` is permanent | soft-delete named `delete` without that being the codebase's documented convention |
| `save`, `persist`, `store` | Durable write | only updates an in-memory map |
| `send`, `publish`, `emit`, `notify`, `dispatch` | Outbound communication / event | — |
| `try` prefix | Returns success indicator instead of throwing (`tryParseAmount`) | throws anyway |

---

## 3. Types: classes, interfaces, structs, enums, records

### NAME-T1 — Name by stereotype (object type) and context
A type name is a **noun or noun phrase** that tells the reader what *kind* of object it is and which *context* it belongs to.

| Stereotype | Pattern | ✅ Examples | ❌ Avoid |
| --- | --- | --- | --- |
| Entity / aggregate root | Singular domain noun | `Order`, `Merchant`, `Payout` | `OrderData`, `OrderObject`, `OrderInfo` |
| Value object | Domain noun for the concept | `Money`, `Iban`, `DateRange`, `EmailAddress` | `String` everywhere (primitive obsession) |
| Persistence model (when separate from domain) | Domain noun + technology/role | `OrderJpaEntity`, `OrderRecord`, `OrderRow` | `OrderEntity2` |
| DTO / API model | Noun + `Request`/`Response`/`Dto` (one convention per codebase) | `CreatePayoutRequest`, `PayoutResponse` | `PayoutDataDTO` |
| Command / query (CQRS) | Imperative verb phrase + `Command`/`Query` | `PlaceOrderCommand`, `GetOrderSummaryQuery` | `OrderCmd` |
| Domain event | Past-tense fact (+ `Event` if that is the convention) | `OrderPlaced`, `PaymentCaptured` | `PlaceOrderEvent`, `OrderEvent` |
| Use case / application service | Verb phrase + `UseCase`/`Handler`/`Service` | `PlaceOrderUseCase`, `RefundPaymentHandler` | `OrderManager` |
| Domain service | Capability noun + `Service`/`Policy`/`Calculator` | `FeeCalculator`, `FraudScreeningService`, `SettlementPolicy` | `FeeHelper` |
| Repository (port) | Aggregate + `Repository` | `OrderRepository` | `OrderDao` mixed with `UserRepository` |
| Repository (adapter) | Technology + aggregate + `Repository` | `PostgresOrderRepository`, `InMemoryOrderRepository` | `OrderRepositoryImpl` |
| Gateway / client to external system | System + role | `StripePaymentGateway`, `KycProviderClient` | `ApiHelper` |
| Controller / endpoint | Resource + `Controller`/`Resource`/`Endpoint` | `PayoutController` | `MainController` |
| Factory | Product + `Factory` | `InvoiceFactory` | `InvoiceCreator` (unless it is not a factory) |
| Builder | Product + `Builder` | `PaymentRequestBuilder` | — |
| Strategy | Variant + role; role is the interface | `ShippingCostCalculator` → `FlatRateShippingCostCalculator`, `ZoneBasedShippingCostCalculator` | `ShippingStrategy1` |
| Decorator | Added behaviour + component | `CachingProductCatalog`, `RetryingHttpClient`, `LoggingPaymentGateway` | `ProductCatalogWrapper` |
| Adapter | Adaptee/technology + target role | `SoapCustomerDirectoryAdapter` | `Adapter` |
| Mapper / converter | Source + `Mapper`, or `XToYMapper` | `OrderMapper`, `OrderToInvoiceMapper` | `Converter` |
| Validator / specification | Subject + `Validator`; rule + `Specification`/`Policy` | `IbanValidator`, `OverdueInvoiceSpecification` | `CheckUtil` |
| Listener / handler | Event + `Listener`/`Handler` | `OrderPlacedListener` | `EventHandler` |
| Exception / error | Problem + `Exception` (Java/C#/Kotlin) or `Error` (Python/Swift/TS/Rust types); Go: `ErrX` vars, `XError` types | `InsufficientFundsException`, `ErrCardExpired` | `MyException`, `CustomError` |
| Configuration | Area + `Config`/`Properties`/`Options`/`Settings` | `PaymentRetryConfig` | `Config2` |
| Enum | Singular noun for the set | `PaymentStatus`, `Currency` | `PaymentStatuses`, `StatusEnum` |

### NAME-T2 — Banned / suspicious type words
Authoritative lists: `banned_type_suffixes` and `banned_type_prefixes` in `../assets/naming-rules.json`.
| Word | Severity | Why / what to use instead |
| --- | --- | --- |
| `Helper`, `Helpers`, `Utility`, `Utilities`, `Util` | MINOR (MAJOR above ~300 lines or 7 dependencies) | Magnet for unrelated code → SRP violation. Name the real responsibility: `SlugFormatter`, `CurrencyConverter`, `SessionExpiryScheduler`. |
| `Utils` | MINOR, **not flagged** when it is the Spring/Apache static-holder form | Acceptable only as `final` class + private constructor + all static + stateless + no dependencies + **one subject** in the prefix (`StringUtils`, `CollectionUtils`). `PaymentUtils` mixing formatting, validation and HTTP calls is a finding (also `JAVA-STYLE-UTILS`, `SOLID-SRP`). |
| `Manager` | MINOR, **not flagged** for resource-lifecycle managers | Acceptable when the type owns the lifecycle of a resource or set of resources (`TransactionManager`, `CacheManager`, `ConnectionManager`, `EntityManager`). `OrderManager`/`UserManager` holding assorted business logic is the grab-bag case: name the responsibility (`OrderPlacementService`, `OrderFulfilmentPolicy`). |
| `Data`, `Info`, `Object`, `Thing`, `Stuff`, `Misc` (suffix); `Common`, `General`, `Misc`, `My` (prefix) | MINOR | Says nothing; use the domain noun. |
| `Processor`, `Wrapper`, `Handler` (outside event/command handlers and framework hooks such as `BeanPostProcessor`) | MINOR | Name what it produces or adds. |
| `*Impl` | MINOR — **yields to repo convention** | Name the implementation by its distinguishing trait (`JdbcOrderRepository`, `DefaultFeeCalculator`). Do not flag when the repository already uses `*Impl` consistently (profile it); do flag a *new* `*Impl` when the repo names implementations by trait. |
| `Base*` on a concrete class | MINOR | Abstract bases may be `Abstract*`/`Base*` by local convention; concrete classes must not. |
| Numbered or versioned names (`OrderService2`, `NewOrderService`) | MAJOR | Indicates parallel implementations; use a feature flag or a meaningful distinction. |

### NAME-T3 — Interfaces name roles and capabilities
- Name what the client needs, not how it is done: `PaymentGateway`, `Clock`, `Notifier`, `ExchangeRateProvider`.
- Capability interfaces may use `-able`/`-ible` adjectives: `Refundable`, `Auditable`, `Comparable`.
- `I` prefix: **required** in C# (`IPaymentGateway`); **forbidden** in Java, Kotlin, TypeScript, Swift, Go, Rust, Python (no Hungarian notation).
- Go: single-method interfaces use the `-er` form (`Reader`, `Notifier`, `RateFetcher`); keep interfaces small and define them where they are consumed.
- Swift protocols: nouns for what something *is* (`Collection`), `-able`/`-ible` for capabilities, `-ing` for capability where natural (`ProgressReporting`).
- Python: `Protocol`/`ABC` classes follow the same role-naming rule.

### NAME-T4 — Implementations distinguish themselves
If an interface has several implementations, each name must say how it differs: `SystemClock` / `FixedClock`; `SmtpEmailNotifier` / `SlackNotifier`; `StripePaymentGateway` / `AdyenPaymentGateway`. The default implementation may be `Default<Role>`/`Simple<Role>` and the skeletal base `Abstract<Role>` (Spring idiom). If there is only one implementation and none is expected, question whether the interface is needed (`OVER-INTERFACE`) — unless it is a port at an architecture boundary, which is legitimate.

### NAME-T5 — Verb-named types
A type whose name starts with a verb (`ProcessPayment`, `CalculateTax`) is wrong unless it is a command, query, use case, request or handler (`ProcessPaymentCommand`, `CalculateTaxUseCase`). Otherwise rename to the noun for what it is (`TaxCalculator`).

### NAME-T6 — Context and stutter
Don't repeat the package/module/namespace in the type name (`payments.PaymentsClient` → `payments.Client` in Go; in Java/C# prefer the shortest unambiguous domain name). Do add context when two bounded contexts use the same word and meet in one file (`billing.Customer` vs `crm.Customer` → disambiguate at the boundary, e.g. `BillingAccount`).

---

## 4. Variables, fields, parameters, constants

| Rule | ✅ | ❌ |
| --- | --- | --- |
| **NAME-V1** Nouns that state the content; plural for collections; `xByY` for maps | `pendingPayouts`, `merchantsById` | `list`, `data`, `map2`, `tmp` |
| Units and encodings in the name when the type does not carry them | `timeoutMs`, `amountMinorUnits`, `createdAtUtc` | `timeout`, `amount` (as a raw number) |
| **NAME-V2** Booleans read as predicates | `isRetryable`, `hasConsent`, `shouldNotify` | `flag`, `status` (bool), `retry` |
| **NAME-V3** No abbreviations or type encodings, except universally known ones (`id`, `url`, `http`, `io`, `db`, `api`, `dto`) | `customerAddress`, `transactionCount` | `custAddr`, `txnCnt`, `strName`, `m_name`, `iCount` |
| Scope-proportional length: 1-letter names only for loop indices and tiny lambdas | `for (i …)`, `x -> x.amount()` | `p` as a field |
| **NAME-V4** One word per concept, consistent with the codebase | the codebase uses `fetch` for remote reads → `fetchRates` | mixing `get`/`fetch`/`retrieve`/`load` for the same kind of operation |
| **NAME-C1** Constants: language casing; named for meaning, not value | `MAX_PAYOUT_RETRIES = 5` | `FIVE = 5`, inline magic number `5` |

---

## 5. Language idioms and exemptions (do not flag these)

**Casing**
| Language | Methods/functions | Types | Constants |
| --- | --- | --- | --- |
| Java, Kotlin, TypeScript/JavaScript, Swift | `lowerCamelCase` | `PascalCase` | `UPPER_SNAKE` (TS/JS/Swift: `lowerCamel` or `UPPER_SNAKE` by codebase convention) |
| C# | `PascalCase` | `PascalCase` | `PascalCase` |
| Go | `MixedCaps`; exported = leading capital | `MixedCaps` | `MixedCaps` |
| Python, Rust | `snake_case` | `PascalCase` (`CapWords`) | `UPPER_SNAKE` |

**Exempt from the verb+noun rule**
- Framework/language contract overrides: `toString`, `equals`, `hashCode`, `compareTo`, `main`, `run`, `call`, `apply`, `invoke`, `close`, `dispose`, `iterator`, `__init__` and other dunders, `String()`/`Error()` in Go, `fmt`/`from`/`into`/`drop` trait methods in Rust, Android/iOS/Angular/React lifecycle methods (`onCreate`, `viewDidLoad`, `ngOnInit`, `componentDidMount`, `render`).
- **Property accessors are nouns**: Kotlin/C#/Swift properties, Python `@property`, TS/JS `get total()`, Java record accessors (`amount()`), Go getters (`Owner()`, never `GetOwner()`), Rust getters (`fn owner(&self)`, no `get_` prefix).
- **Static factories and conversions**: `of`, `from`, `valueOf`, `parse`, `copyOf`, `newX`/`NewX` (Go), `new`/`with_capacity` (Rust), `toX`/`asX`/`intoX`, `aToB` conversions (`intToBytes`, `timestamp_to_datetime`), builder `withX`.
- **Third-person verb forms** of approved verbs are fine (`loads`, `dumps`, `matches`), as are single-word predicates (`supports(type)`, `contains(x)`).
- **Implementations of an interface you don't own** (framework callbacks, `http.Handler.ServeHTTP`, Spring `Validator.supports`) keep the required name — flag the interface, not the implementer.
- **Swift note:** Apple's API Design Guidelines name side-effect-free methods as noun phrases (`x.distance(to: y)`). This team rule still asks for verb+noun; if a project prefers the Apple idiom, record that in `.agents/review-overrides.md` and the reviewer will follow it.
- **Fluent DSLs and builders**: `.where(...)`, `.limit(...)`, `.retries(3)` inside an established fluent API.
- **Tests**: behaviour-style names (`should_reject_expired_card`, `givenExpiredCard_whenAuthorize_thenDeclined`, Go `TestAuthorize_ExpiredCard`) — check them for describing behaviour instead.
- **React**: components are `PascalCase` nouns (`PayoutTable`); hooks are `useX`; event props `onX`; handlers `handleX`.
- Generated code, migrations, vendored code.

---

## 6. Framework idioms (never violations)

Spring, Spring Boot and Apache projects use a stable vocabulary; new code in such a codebase should use it too. Full table in `java-quality-bar.md` §10. Highlights:

| Idiom | Example | Note |
| --- | --- | --- |
| `Abstract<Role>`, `<Role>Support` | `AbstractPaymentGateway`, `PaymentGatewaySupport` | skeletal / convenience base classes |
| `Default<Role>`, `Simple<Role>`, `Standard<Role>` | `DefaultFeeCalculator` | the default implementation (instead of `*Impl`) |
| `<Role>Operations` + `<Role>Template` | `JdbcOperations` / `JdbcTemplate` | interface + resource-handling implementation |
| `<Thing>Resolver`, `<Thing>Registrar`, `<Thing>Registry`, `<Thing>Customizer`, `<Thing>PostProcessor`, `<Thing>Aware`, `<Thing>Interceptor`, `<Thing>Advisor` | `TenantResolver`, `WebClientCustomizer` | framework roles |
| `<Resource>Manager` | `TransactionManager`, `CacheManager` | lifecycle of a resource — not a grab-bag |
| `<Subject>Utils` (static holder) | `StringUtils` | final, static, stateless, one subject |
| `do<Verb><Noun>` | `doGetBean` behind `getBean` | template-method worker |
| `determine<Thing>`, `obtain<Thing>`, `resolve<Thing>`, `supports(..)`, `afterPropertiesSet()`, `postProcess<Thing>`, `customize(..)`, `initialize()`, `destroy()`, `refresh()` | — | standard verbs |
| `<Problem>Exception` | `NoSuchBeanDefinitionException` | never `<Verb><Noun>Exception` |
| Test classes `*Tests` (Spring) or `*Test` (Apache/Maven default) | `RefundServiceTests` | follow the repo |

---

## 7. Rule IDs (use in findings)

| ID | Rule |
| --- | --- |
| NAME-M1 | Method/function must be action verb + noun (noun optional if receiver supplies it) |
| NAME-M2 | Verb contract: name must not misrepresent behaviour (MAJOR) |
| NAME-M3 | Vague verb |
| NAME-M4 | Boolean-returning method must read as a predicate |
| NAME-M5 | Boolean flag argument |
| NAME-M6 | Redundant context in method name |
| NAME-M7 | Inconsistent async naming |
| NAME-T1 | Type must be a noun named by stereotype and context |
| NAME-T2 | Banned/suspicious type word |
| NAME-T3 | Interface naming (role/capability; `I` prefix per language) |
| NAME-T4 | Implementation must name its distinguishing trait (no `Impl`) |
| NAME-T5 | Verb-named type that is not a command/query/use case |
| NAME-T6 | Package/module stutter or missing bounded-context disambiguation |
| NAME-V1…V4 | Variable naming: content nouns & units; boolean predicates; no abbreviations/encodings; one word per concept |
| NAME-C1 | Constant naming / magic values |
| NAME-CASE | Casing does not follow the language convention |
