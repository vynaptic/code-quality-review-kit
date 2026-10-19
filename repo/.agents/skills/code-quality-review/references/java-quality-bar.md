# Java Quality Bar — Spring Framework / Apache grade

The calibration question for every Java or Kotlin change: **would this be merged into Spring Framework or an Apache Commons project as-is?** Those projects are strict about small, final, immutable classes; explicit contracts (nullability, thread-safety, exceptions); parameterized logging; Javadoc on public API; plain Java over cleverness; and consistency with the surrounding code above personal taste.

Repository conventions (`repo-conventions.md`) override the *stylistic* choices below (logger field name, `*Impl`, `this.` prefix, test suffix). They do not override correctness items.

Contents: 1. API and class design · 2. Exceptions · 3. Logging · 4. Nullability and Optional · 5. Collections, generics, streams · 6. Concurrency · 7. Spring-specific · 8. Javadoc and comments · 9. Style and structure · 10. Framework naming idioms · 11. Kotlin addendum · 12. Rule IDs

---

## 1. API and class design (JAVA-API-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| JAVA-API-ACCESS | Minimise accessibility: package-private by default; `public` only for types/members used outside the package; `protected` only on classes designed for extension | New `public` class/method with no external caller; public fields; public nested helper | Reduce visibility; one public type per file |
| JAVA-API-FINAL | Classes are `final` (or effectively so) unless designed and documented for extension; fields `final` unless mutation is required | New non-final class with no subclass and no "designed for extension" doc; mutable fields that are set once | `final` |
| JAVA-API-IMMUTABLE | Value types are immutable: all fields final, no setters, defensive copies of mutable inputs/outputs (`List.copyOf`, `new Date(d.getTime())`), no "escaping" of internal arrays/collections | Setter on a value type; constructor stores a caller's mutable list; getter returns internal `List` | Record, `List.copyOf`, unmodifiable view |
| JAVA-API-PRECONDITION | Constructors and public methods validate arguments immediately with a precise message: `Assert.notNull(x, "'x' must not be null")` (Spring), `Objects.requireNonNull(x, "x must not be null")`, `Assert.hasText`, `Assert.isTrue(amount.signum() > 0, "amount must be positive")` | Null/invalid argument discovered deep inside; silent `if (x == null) return` | Fail fast at entry; `IllegalArgumentException` for arguments, `IllegalStateException` for state |
| JAVA-API-FACTORY | Prefer static factories (`of`, `from`, `valueOf`, `create`, `with*`) when the name adds meaning, the type is a value, or instances may be cached; a builder for 4+ optional parameters; never telescoping constructors | 3+ overloaded constructors; `new X(a, null, null, true)` | Static factory / builder / records with `with` methods |
| JAVA-API-ENUM | Enums over int/String constants; `EnumSet`/`EnumMap`; no `ordinal()` persistence | `int status = 2`; `String type = "SEPA"` compared with `equals` | Enum with explicit code field |
| JAVA-API-EQUALS | `equals`/`hashCode`/`toString` on value types, consistent, using all identity fields; `compareTo` consistent with `equals`; use records when possible | Value class without `equals`; `equals` on JPA entity using mutable/generated id before persist | Record, or `Objects.equals/hash` on business key |
| JAVA-API-INTERFACE | Interface only for a real abstraction: a port at a boundary, a public extension point, or ≥2 implementations. No interface for one class in the same module "for testing" (mock the class or use the port) | `FooService` + `FooServiceImpl` with no second impl and no boundary (unless repo convention) | Collapse to class (see `OVER-INTERFACE`) |
| JAVA-API-INHERIT | Composition over inheritance; abstract classes only as `Abstract*` skeletal implementations of an interface; no inheritance for code reuse; no `protected` mutable state | `extends` to reuse helper methods; 3+ levels | Delegate; Template Method only with a stable skeleton |
| JAVA-API-SERIAL | `Serializable` only on purpose, with `serialVersionUID`; no Java native serialization for transport | `implements Serializable` cargo-culted on DTOs | Remove, or document why |
| JAVA-API-VARARGS | Varargs only for homogeneous trailing arguments; no generic varargs without `@SafeVarargs` | `method(String... args)` where a `List` is clearer | Collection parameter |
| JAVA-API-OBJECT | No `Object`-typed parameters/returns or `Map<String, Object>` across module boundaries | `Map<String, Object> payload` in service API | Typed record/DTO |
| JAVA-API-BASELINE | Use only language features available at the repo's compiler level (`maven.compiler.release`, `sourceCompatibility`, `toolchain`); use the modern feature when available (records, sealed types, pattern `switch`, text blocks, `var` for obvious types) | Java 21 syntax in a Java 17 module; hand-written POJO where a record fits (Java 16+) | Match the baseline; the profiler reports it |
| JAVA-API-STATIC | Static only for pure, stateless functions; no static mutable state; no static access to collaborators (`ServiceLocator.get`) | `static Map cache = new HashMap<>()`; static call to a repository | Instance + injection; `ConcurrentHashMap` if truly global |

---

## 2. Exceptions (JAVA-EXC-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| JAVA-EXC-UNCHECKED | Unchecked by default (Spring style); checked only when every caller can meaningfully recover | New checked exception on a service method; `throws Exception` on a public API | `extends RuntimeException` (or the repo's root) |
| JAVA-EXC-HIERARCHY | One root per module/bounded context (`BillingException`), specific subclasses only where callers handle them differently; name = problem + `Exception` (`InsufficientFundsException`) | `throw new RuntimeException("...")`; `MyException`; `CustomException`; a new root when one exists | Extend the repo root; name the problem |
| JAVA-EXC-CAUSE | Always chain the cause: `new XException(msg, e)`; never `new XException(e.getMessage())` | Cause dropped when wrapping | Pass `e` |
| JAVA-EXC-MESSAGE | Message states what failed and the identifying context, as a sentence: `"Refund " + refundId + " exceeds captured amount " + captured` (Spring: "Failed to …", "Could not …", "… must not be null"); no PII/secrets; no trailing period drift within a module | `throw new IllegalStateException("error")`; message includes card number/token | Context + no PII |
| JAVA-EXC-SWALLOW | Never swallow: empty `catch`, `catch (Exception e) { log… }` then continue as if nothing happened, `return null` on error | Empty catch; catch + log + continue in a loop over money/items | Rethrow, translate, or handle with a documented fallback and a comment |
| JAVA-EXC-NARROW | Catch the narrowest type; never `Throwable`/`Error`; `catch (Exception)` only at a top-level boundary (request handler, job runner, message consumer) | `catch (Exception e)` inside business logic | Catch the specific type |
| JAVA-EXC-FLOW | No exceptions for expected control flow (`NumberFormatException` to test numericness; `NoSuchElementException` to test presence) | try/catch around a lookup to return a default | `find*` returning `Optional`, `tryParse`, predicate |
| JAVA-EXC-TRANSLATE | Translate at layer boundaries: infrastructure exceptions (`SQLException`, `IOException`, `HttpClientErrorException`, `FeignException`) must not escape into the domain; Spring's `DataAccessException` translation is the model | Domain/service signature or catch block names an infra exception | Wrap in the module's exception at the adapter |
| JAVA-EXC-LOG-RETHROW | Do not log and rethrow; log once where the exception is finally handled | `log.error(…, e); throw e;` | Remove the log, or handle |
| JAVA-EXC-INTERRUPT | `catch (InterruptedException e)` → `Thread.currentThread().interrupt()` then rethrow/abort | Interrupt status swallowed | Restore the flag |
| JAVA-EXC-FINALLY | `finally` never returns or throws; use try-with-resources for `AutoCloseable` | `return` in `finally`; manual `close()` | try-with-resources |
| JAVA-EXC-NULL-RETURN | Do not return `null`, `-1`, empty string or a special object to signal failure | `return null` on not found/error | `Optional` (lookup), exception (failure), empty collection |
| JAVA-EXC-DOC | Public API documents thrown exceptions (`@throws`) and the conditions | New public method throws undocumented domain exception | Javadoc `@throws` |
| JAVA-EXC-CLIENT | Never expose stack traces or internal class names to clients; map to the repo's error body (`ProblemDetail`/custom) with a stable code | `return ResponseEntity.status(500).body(e.toString())` | Global handler per repo (`CONV-EXC`) |
| JAVA-EXC-STATE | Exception classes carry context as final fields (`refundId`, `errorCode`), no logic, no mutable state | Exception with setters or business methods | Immutable exception |

---

## 3. Logging (JAVA-LOG-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| JAVA-LOG-FACADE | One facade per codebase (default SLF4J); logger per class, declared as the repo does (`private static final Logger log = LoggerFactory.getLogger(X.class)`, or `@Slf4j`) | JUL, `System.out`, `printStackTrace`, Log4j API in an SLF4J repo; logger named after another class; non-static instance logger (unless repo style) | Repo facade and declaration |
| JAVA-LOG-CONCAT | Parameterized messages: `log.debug("Loaded {} rates for {}", count, currency)`; never string concatenation or `String.format` inside a log call | `log.info("Refund " + id + " done")`; `log.debug(String.format(…))` | `{}` placeholders |
| JAVA-LOG-EXCEPTION | Pass the exception as the **last** argument, not `e.getMessage()` or `e.toString()`: `log.error("Failed to settle payout {}", payoutId, e)` | Stack trace lost; `log.error(e)`; `log.error("x: " + e)` | Throwable as last arg |
| JAVA-LOG-LEVEL | **ERROR** = operation failed and someone must act; **WARN** = unexpected but handled/degraded (retry, fallback); **INFO** = significant lifecycle or business event, low volume (started, settled batch of N); **DEBUG** = developer diagnostics; **TRACE** = per-item/payload detail | INFO per request/loop item; ERROR for a client's 400; DEBUG for a failed payout | Correct level |
| JAVA-LOG-HOT | No logging inside tight loops or per-element at INFO+; guard expensive argument construction with `isDebugEnabled()` or fluent/`Supplier` API | `for (…) log.info(…)`; `log.debug("…{}", toJson(bigObject))` unguarded | Aggregate; guard |
| JAVA-LOG-SIDE-EFFECT | Log arguments have no side effects and cannot throw (`entity.getLazyCollection().size()` inside a log call) | Method calls with side effects or lazy-load in args | Compute before, or guard |
| JAVA-LOG-PII | No secrets, tokens, passwords, full card numbers, IBANs, emails, personal data in logs; mask (`****1234`) | Logging request/response bodies, headers, entities with PII | Mask/omit; structured fields |
| JAVA-LOG-CONTEXT | Include identifiers needed to correlate (orderId, tenantId, correlationId via MDC per repo); messages are actionable sentences, consistent style within the module | `log.warn("failed")` with no id; inconsistent capitalisation/punctuation | Add ids, follow neighbours |
| JAVA-LOG-ONCE | Log an error once, where it is handled; no log-and-rethrow; no duplicate logs across layers for one failure | Same failure logged in adapter, service and controller | Log at the handler |
| JAVA-LOG-ENTITY | Do not log whole entities/collections via `toString` (size, PII, lazy loading) | `log.info("Saved {}", order)` | Log ids and counts |
| JAVA-LOG-STRUCTURED | If the repo uses structured logging (key-value, `StructuredArguments`, `MDC` keys), use the same keys | New ad-hoc key names | Reuse keys |

---

## 4. Nullability and Optional (JAVA-NULL-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| JAVA-NULL-ANNOTATE | Follow the repo's nullability annotations (JSpecify `@Nullable`/`@NullMarked`, Spring `@Nullable`, JSR-305); non-null is the default; annotate the exceptions | New public API that can return/accept null without annotation in an annotated codebase | Annotate; or redesign to not return null |
| JAVA-NULL-OPTIONAL-RETURN | `Optional` only as a return type for lookups that may legitimately find nothing; never for fields, parameters, collection elements, or to wrap collections (return empty collection) | `Optional<List<X>>`; `Optional` field; `Optional` parameter | Empty collection; overloads; nullable annotation |
| JAVA-NULL-OPTIONAL-USE | No `isPresent()` + `get()`; no `Optional.get()` without a prior check; use `map`/`flatMap`/`orElse*`/`ifPresentOrElse`; do not use `Optional` for control flow gymnastics | `if (o.isPresent()) { o.get()… }`; `.get()` | `orElseThrow(() -> new NotFoundException(id))` |
| JAVA-NULL-DEFENSIVE | Validate at the boundary and trust internally; no `if (x != null)` sprinkled on values that are never null by contract | Redundant null checks that hide the real contract | Precondition at entry (JAVA-API-PRECONDITION) |
| JAVA-NULL-COLLECTION | Never return `null` for a collection, array or map | `return null` where `List` expected | `List.of()` / `Collections.emptyList()` |

---

## 5. Collections, generics and streams (JAVA-COLL-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| JAVA-COLL-INTERFACE | Declare with the interface (`List`, `Map`, `Set`), not the implementation (`ArrayList`, `HashMap`) in fields, parameters and returns | `ArrayList<X> getItems()` | Interface type |
| JAVA-COLL-UNMODIFIABLE | Do not expose internal mutable collections; return `List.copyOf`/unmodifiable views; use `List.of`, `Map.of` for literals | Getter returns the field; caller can mutate state | Copy or unmodifiable view |
| JAVA-COLL-TYPE | Right structure: `Set` for membership, `EnumSet`/`EnumMap` for enums, `Map` for lookup; no repeated `list.contains` in loops; no `LinkedList` without reason | O(n²) via `List.contains` in a loop | `Set`/`Map` |
| JAVA-COLL-RAW | No raw types; bounded wildcards in APIs (PECS: `? extends` for producers, `? super` for consumers); no unchecked casts without `@SuppressWarnings` + comment | `List list = …`; `(List<String>) obj` | Generics |
| JAVA-COLL-STREAM | Streams only when they read better than a loop: no side effects in lambdas, no nested streams beyond one level, no multi-line lambdas (extract a method), no `forEach` with mutation of outer state, no `stream().count() > 0` (`anyMatch`), no `findFirst().isPresent()` (`anyMatch`), no `collect(Collectors.toList())` when `toList()` (Java 16+) fits, no `Collectors.toList()` relied on as mutable | A 15-line stream pipeline; `forEach(list::add)` | Loop or extracted methods |
| JAVA-COLL-ITERATE | Iterate `entrySet()` not `keySet()` + `get`; no modification while iterating; `removeIf` over manual iterator removal | `for (k : map.keySet()) map.get(k)` | `entrySet()` |
| JAVA-COLL-STRING | Use `StringBuilder` in loops, text blocks for multi-line literals, `String.join`/`Collectors.joining`; `isEmpty()`/`isBlank()` not `length() == 0`/`equals("")`; `equalsIgnoreCase` not `toLowerCase().equals` | `s += x` in a loop | Builder |
| JAVA-COLL-ARRAY | Prefer collections to arrays in APIs; never return internal arrays | `byte[]` field exposed | Copy or wrap |

---

## 6. Concurrency (JAVA-CONC-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| JAVA-CONC-IMMUTABLE | Shared state is immutable or confined; document thread-safety in the class Javadoc ("This class is thread-safe" / "not thread-safe") when it matters (Spring does) | New stateful singleton bean with mutable fields | Immutable, or confine, or document |
| JAVA-CONC-JUC | `java.util.concurrent` over `synchronized`/`wait`/`notify`: `ConcurrentHashMap`, `AtomicLong`, `LongAdder`, `ReentrantLock`, `CountDownLatch` | `synchronized (this)` in a public API; `HashMap` shared across threads; double-checked locking without `volatile` | JUC types; `computeIfAbsent` |
| JAVA-CONC-EXECUTOR | Executors come from the repo's configured pools (Spring `TaskExecutor`, named thread factory); never `new Thread`, never `Executors.newCachedThreadPool()` unbounded in prod code; executors shut down | Ad-hoc executor in a service; unnamed threads | Inject the executor; bounded pool |
| JAVA-CONC-FUTURE | `CompletableFuture` chains handle exceptions (`exceptionally`/`handle`/`whenComplete`); no `.get()` without timeout; no `join()` on request threads without reason | Fire-and-forget future; `.get()` blocking | Handle + timeout |
| JAVA-CONC-SLEEP | No `Thread.sleep` or busy-wait in production logic; use scheduling/backoff utilities | `Thread.sleep(1000)` retry loop | Retry with backoff (repo's library) |
| JAVA-CONC-THREADLOCAL | `ThreadLocal` cleared in `finally`; never with pooled threads unless removed | `ThreadLocal.set` without `remove` | try/finally remove |
| JAVA-CONC-UNSAFE-TYPES | No shared `SimpleDateFormat`, `DecimalFormat`, `Random`, `MessageDigest`, `Matcher`; use `DateTimeFormatter`, `ThreadLocalRandom`/`SecureRandom`, local instances | Static `SimpleDateFormat` | Thread-safe alternatives |
| JAVA-CONC-VOLATILE | Flags read by other threads are `volatile`/`Atomic*`; no non-atomic compound updates (`count++`) on shared fields | `boolean running` without volatile | `AtomicBoolean` |
| JAVA-CONC-VIRTUAL | With virtual threads (Java 21+): no `synchronized` around I/O (pinning); use `ReentrantLock` | `synchronized` + blocking call in a virtual-thread app | `ReentrantLock` |

---

## 7. Spring-specific (JAVA-SPRING-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| JAVA-SPRING-CTOR-INJECT | Constructor injection with `final` fields; no `@Autowired` on fields or setters; a single constructor needs no annotation; Lombok `@RequiredArgsConstructor` if the repo uses it | Field injection in new code (unless repo convention) | Constructor |
| JAVA-SPRING-TX-PLACEMENT | `@Transactional` on service-layer public methods (or the repo's documented layer); not on controllers; `readOnly = true` for reads; no self-invocation (proxy bypass); no checked exceptions that silently skip rollback; no remote calls inside a transaction | `@Transactional` on a controller or private method; `this.doWork()` from a transactional method | Move/extract |
| JAVA-SPRING-NO-LOGIC-IN-CONTROLLER | Controllers translate HTTP ↔ use case: bind, validate (`@Valid`), call one service, map response. No business rules, no repository calls, no transactions | `if (order.getTotal() > limit)` in a controller; repository injected into controller | Move to service/use case |
| JAVA-SPRING-DTO-BOUNDARY | Entities never serialised directly as responses or bound from requests; DTOs/records at the boundary; map explicitly or with the repo's mapper | `@RequestBody Order order` (entity); returning an entity | DTO + mapper |
| JAVA-SPRING-CONFIG-PROPS | `@ConfigurationProperties` records/classes with validation over scattered `@Value`; properties in kebab-case; defaults explicit; no secrets in properties files | 4+ `@Value` in one class; `@Value("${x}")` without default on an optional property | Properties class |
| JAVA-SPRING-BEANS | Stereotypes match roles (`@Service`, `@Repository`, `@Component`); `@Repository` for exception translation; no `@Lazy`/`@DependsOn` to hide cycles; no circular dependencies | New bean cycle; `@Lazy` workaround | Restructure |
| JAVA-SPRING-JPA | No `FetchType.EAGER` on collections; lazy associations loaded inside the transaction or via fetch joins/`@EntityGraph`; `spring.jpa.open-in-view=false` respected; `equals`/`hashCode` on entities by business key or stable id; no N+1 in loops; projections for read models; no `findAll()` on big tables | New `EAGER`; loop with `findById`; entity `@Data` | Fetch join; batch; projection |
| JAVA-SPRING-EVENTS | Side effects after commit via `@TransactionalEventListener(phase = AFTER_COMMIT)` or outbox; events are past-tense immutable records | Email/HTTP call inside `@Transactional` | After-commit / outbox |
| JAVA-SPRING-HTTP-CLIENT | Use the repo's client (`RestClient`/`WebClient`/Feign) via injected, configured instances with connect/read timeouts; never `new RestTemplate()` in a service; no blocking in reactive chains | Client instantiated inline; no timeout | Configured bean |
| JAVA-SPRING-VALIDATION | Bean Validation at the boundary (`@Valid`, `@Validated` groups); domain invariants in constructors/factories, not only annotations | Request accepted without `@Valid`; validation only in controller for a domain rule | Both layers per repo |
| JAVA-SPRING-ERROR-HANDLING | One `@RestControllerAdvice` (or repo's) mapping exceptions to the error body; controllers do not try/catch | try/catch in controller returning ad-hoc bodies | Global handler |
| JAVA-SPRING-SCHEDULED | `@Scheduled` jobs are idempotent, locked across instances (ShedLock or repo's), and use the configured scheduler | New job without locking in a multi-instance service | Lock + idempotency |
| JAVA-SPRING-TEST-SLICE | Prefer `@WebMvcTest`/`@DataJpaTest`/`@JsonTest` slices and plain unit tests; `@SpringBootTest` only for wiring; `@MockitoBean`/`@MockBean` sparingly (context cache churn); Testcontainers per repo | `@SpringBootTest` for a pure rule; 6 mocks in one test | Slice / unit |
| JAVA-SPRING-ASYNC | `@Async` methods return `void`/`CompletableFuture`, run on a named executor, are public and called from another bean (proxy) | `@Async` private/self-invoked | Fix wiring |
| JAVA-SPRING-SECURITY | Authorization on every endpoint (`@PreAuthorize` or security config), method security for service-level rules; no `permitAll` drift | New endpoint with no rule | Add rule |

---

## 8. Javadoc and comments (JAVA-DOC-*)

| ID | Rule | Flag when | Fix |
| --- | --- | --- | --- |
| JAVA-DOC-PUBLIC-API | Public types and public/protected members of a library, module API or shared starter have Javadoc: one-sentence summary ending with a period, `@param`, `@return`, `@throws`, `{@code}`/`{@link}`; `@since` in libraries; thread-safety, nullability and immutability stated in the class Javadoc (Spring style) | New public API type with no Javadoc in a documented codebase | Write it |
| JAVA-DOC-NOISE | No Javadoc that restates the signature (`/** Gets the name. @return the name */`) unless the repo requires it; no `@author` unless the repo uses it | Generated-looking Javadoc on internal code | Delete or say something useful |
| JAVA-DOC-WHY | Implementation comments explain *why* (constraints, trade-offs, links to tickets/specs), not *what*; a comment that is wrong is a bug | `// increment i`; stale comment contradicting the code | Fix or delete |
| JAVA-DOC-DEAD | No commented-out code; `TODO`/`FIXME` carry an owner or ticket per repo | `// old implementation…` | Delete (git remembers) |
| JAVA-DOC-DEPRECATE | `@Deprecated(since = "…", forRemoval = …)` **and** `@deprecated` Javadoc naming the replacement | `@Deprecated` alone | Both |
| JAVA-DOC-SUPPRESS | `@SuppressWarnings` is narrow (one warning, smallest scope) and justified in a comment | Class-level `@SuppressWarnings("all")` | Narrow + comment |

---

## 9. Style and structure (JAVA-STYLE-*) — only where no formatter/linter enforces it

| ID | Rule |
| --- | --- |
| JAVA-STYLE-FILE | One top-level type per file; file name = type name; package matches directory; package names lowercase, no underscores |
| JAVA-STYLE-ORDER | Member order per repo (typical: constants, static fields, instance fields, constructors, static factories, public methods, protected, private, nested types); keep related methods adjacent; callers above callees (newspaper order) |
| JAVA-STYLE-IMPORTS | No wildcard imports (Spring forbids); no unused imports; no fully-qualified names in code when an import works; static imports only for assertions/well-known factories |
| JAVA-STYLE-OVERRIDE | `@Override` on every override; `@FunctionalInterface` on functional interfaces |
| JAVA-STYLE-BRACES | Braces on every block; no single-line `if (x) return;` without braces unless the repo does it |
| JAVA-STYLE-THIS | `this.` prefix only if the repo uses it consistently (Spring does); otherwise none — never a mix in one class |
| JAVA-STYLE-CONSTANTS | `private static final` `UPPER_SNAKE_CASE`; group at the top; no magic numbers/strings (NAME-C1); no `interface` used to hold constants |
| JAVA-STYLE-UTILS | A `*Utils`/`*Support` holder (Spring `StringUtils`, Apache `ArrayUtils`) is acceptable only when: `final` class, private constructor, all static, stateless, no injected dependencies, **one subject** named in the prefix. Anything else is a `NAME-T2`/`SOLID-SRP` finding |
| JAVA-STYLE-LOMBOK | If the repo uses Lombok: `@Value`/`@Builder` for immutables, `@RequiredArgsConstructor` for injection; never `@Data` on entities or on types with invariants; no `@Setter` on value types; never `@SneakyThrows` in production code |
| JAVA-STYLE-VAR | `var` only when the type is obvious from the right-hand side (`var order = new Order(...)`), never for method-call results whose type the reader must guess |
| JAVA-STYLE-TERNARY | No nested ternaries; no ternary with side effects |
| JAVA-STYLE-SWITCH | Exhaustive `switch` on enums/sealed types (no silent `default` that hides a new case); arrow form (Java 14+) when the baseline allows |

---

## 10. Framework naming idioms (accepted, not violations)

These are the names Spring and Apache projects use; do not flag them, and prefer them when the repo does.

| Pattern | Meaning | Example |
| --- | --- | --- |
| `Abstract<Role>` | Skeletal implementation of an interface, designed for extension | `AbstractPaymentGateway` |
| `<Role>Support` | Convenience base class with helper state for implementers | `PaymentGatewaySupport`, `ApplicationObjectSupport` |
| `Default<Role>` / `Simple<Role>` / `Standard<Role>` | The default or simplest implementation of an interface | `DefaultFeeCalculator`, `SimpleAsyncTaskExecutor` |
| `<Role>Operations` + `<Role>Template` | Interface + implementation that encapsulates resource handling (Template Method) | `JdbcOperations`/`JdbcTemplate`, `PaymentOperations`/`PaymentTemplate` |
| `<Thing>Resolver` | Resolves one thing from context | `HandlerMethodArgumentResolver`, `TenantResolver` |
| `<Thing>Registrar` / `<Thing>Registry` | Registers / holds registrations | `ImportBeanDefinitionRegistrar`, `ListenerRegistry` |
| `<Thing>Customizer` | Callback to customise a builder/config | `WebClientCustomizer` |
| `<Thing>PostProcessor` / `<Thing>Processor` (framework hook) | Lifecycle hook | `BeanPostProcessor` |
| `<Thing>Aware` | Callback interface injecting a framework object | `ApplicationContextAware` |
| `<Thing>Manager` (resource lifecycle) | Owns the lifecycle of a resource or a set of them | `TransactionManager`, `CacheManager`, `EntityManager` — acceptable; `OrderManager` (grab-bag) is not |
| `<Subject>Utils` (static holder) | See JAVA-STYLE-UTILS | `StringUtils`, `CollectionUtils` |
| `<Role>Factory`, `<Role>Builder`, `<Role>Adapter`, `<Role>Interceptor`, `<Role>Advisor`, `<Role>Listener`, `<Role>Handler` (event/request) | GoF / framework roles | `BeanFactory`, `RequestInterceptor` |
| `do<Verb><Noun>` (protected/private) | Internal worker behind a public template method of the same name | `getBean` → `doGetBean`; `filter` → `doFilterInternal` — acceptable only when the public `<verb><Noun>` exists |
| `determine<Thing>`, `obtain<Thing>`, `resolve<Thing>`, `supports(...)`, `afterPropertiesSet`, `postProcess<Thing>`, `customize`, `initialize`, `destroy`, `refresh` | Standard Spring verbs | — |
| `<Verb><Noun>Exception` is wrong; `<Problem>Exception` is right | e.g. `NoSuchBeanDefinitionException`, `TransactionTimedOutException` | — |

---

## 11. Kotlin addendum (JAVA-KT-*)

| ID | Rule |
| --- | --- |
| JAVA-KT-NULL | Non-null types by default; `!!` is a finding unless justified; `?.let`/`?:` over null checks; platform types from Java annotated at the boundary |
| JAVA-KT-DATA | `data class` for values (immutable `val`), `sealed` for closed hierarchies with exhaustive `when`; no `lateinit` for injectable dependencies (constructor injection) |
| JAVA-KT-COROUTINES | Structured concurrency (`coroutineScope`, injected `CoroutineDispatcher`); no `GlobalScope`; no `runBlocking` on request threads; `suspend` functions have no `Async` suffix |
| JAVA-KT-EXTENSIONS | Extension functions for small, discoverable helpers on a type; not a dumping ground replacing `*Utils` (same single-subject rule) |
| JAVA-KT-OBJECT | `object` singletons only for stateless helpers/constants; `companion object` for factories; no mutable global state |
| JAVA-KT-IDIOM | `when` over `if-else` chains; expression bodies for one-liners; named arguments for booleans; `require`/`check`/`error` for preconditions; scope functions not nested deeper than one level |
| JAVA-KT-EXC | Same exception rules as Java; Kotlin has no checked exceptions — annotate `@Throws` only on Java-facing APIs |
| JAVA-KT-LOG | Repo's logger pattern (`private val log = KotlinLogging.logger {}` / companion SLF4J); lazy message lambdas instead of string templates at DEBUG |

---

## 12. Rule IDs and severities

Families: `JAVA-API-*`, `JAVA-EXC-*`, `JAVA-LOG-*`, `JAVA-NULL-*`, `JAVA-COLL-*`, `JAVA-CONC-*`, `JAVA-SPRING-*`, `JAVA-DOC-*`, `JAVA-STYLE-*`, `JAVA-KT-*`.

Default severities:
- **BLOCKER**: anything that also matches a `BUG-*`/`SEC-*` rule (swallowed exception that loses a payment, shared `SimpleDateFormat`, unbounded executor in a hot path, side effect inside a transaction that can roll back, missing authorization).
- **MAJOR**: `JAVA-EXC-HIERARCHY`/`TRANSLATE`/`CAUSE`/`SWALLOW` in service or domain code; `JAVA-LOG-PII`; `JAVA-LOG-FACADE` (second facade); `JAVA-SPRING-TX-PLACEMENT`; `JAVA-SPRING-NO-LOGIC-IN-CONTROLLER`; `JAVA-SPRING-DTO-BOUNDARY` on public APIs; `JAVA-API-IMMUTABLE` on shared value types; `JAVA-CONC-*` on shared state; `JAVA-DOC-PUBLIC-API` on a published library.
- **MINOR**: the rest.
- **NIT**: `JAVA-STYLE-*` not covered by a formatter, `JAVA-DOC-NOISE`.

When a `JAVA-*` rule and a `CONV-*`/`NAME-*`/`DP-*` rule both apply, list all IDs and use the highest severity. Style items yield to repo conventions; correctness items do not.
