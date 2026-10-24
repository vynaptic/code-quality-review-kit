# Repeated Literals, Closed Sets and Data Carriers

Hard-coded values that recur, string-typed state that belongs to a closed set, and data objects built field by field are the most common sources of silent drift: a typo in one copy, a status renamed in three places out of four, a constructor call with two swapped arguments of the same type. This reference turns those into reviewable rules with evidence requirements, guards and the smallest fix. It applies to every language; framework sections name the idiomatic fix for Java/Spring, MyBatis, JPA, Python and TypeScript.

Evidence first: a finding needs the locations (file:line of each occurrence) and the concrete risk (drift, typo, swapped arguments, unvalidated state). A count alone is a lead, not a finding. `scripts/scan_literals.py` produces the leads.

Contents: 1. Repeated literals (REP-*) · 2. Framework-specific literal rules (MYB-*, JPA-*, SPRING-*, PY-*, TS-*) · 3. Data carriers: enum, builder, record, value object (MODEL-*) · 4. Rule IDs and severities

---

## 1. Repeated literals (REP-*)

Threshold: the **same non-trivial literal three or more times** in production code of one module (`assets/naming-rules.json → literals.min_occurrences`). Two occurrences are a lead only when they already drive branching.

| ID | Signal | Guard (do not flag) | Fix |
| --- | --- | --- | --- |
| REP-STRING | The same string literal (identifier-like key, code, name, path segment, header, property key) appears ≥3 times; or a raw copy of a value that already exists as a named constant | Human-readable messages and log text (different rule: REP-MESSAGE); test data; i18n keys read from a bundle; a literal that *is* the single definition (constant, enum value, annotation on the one type that owns it) | One named constant (`static final`, `const`, module-level `UPPER_SNAKE`, `Final`) in the type that owns the concept, or an enum when the values form a set (REP-CLOSED-SET) |
| REP-NUMBER | The same magic number ≥3 times (limits, timeouts, retry counts, scale, percentages, HTTP/status codes, sizes) | `0`, `1`, `-1`, `2`, array indices, obvious arithmetic (`/ 2`), test expectations | Named constant with unit in the name (`MAX_PAYOUT_RETRIES`, `CONNECT_TIMEOUT_MS`), or configuration when operators must tune it (`OVER-CONFIG` guards) |
| REP-CLOSED-SET | Several distinct literals are compared, switched on or stored under the **same key or field** (`status == "ACTIVE"` … `"CLOSED"` … `"SUSPENDED"`; `type: 'sepa' \| 'card'`; `kind = 1 / 2 / 3`); a `switch`/`when`/`match` or `if/else` chain over string or int literals | An open-ended vocabulary genuinely owned by another system (free-text tags, external codes passed through unchanged) — then wrap it in a value type, not an enum | An enum (Java `enum` with an explicit `code` field and `fromCode(...)`; Kotlin `enum class`/`sealed`; Python `Enum`/`StrEnum`/`Literal[...]`; TypeScript union or `as const` object; C# `enum`); persist by **name or code, never ordinal** |
| REP-KEY | Repeated infrastructure keys: HTTP header names, MDC/log keys, cache names, Kafka/queue topic names, feature-flag keys, config property keys, JSON field names used in hand-written parsing, metric names, path segments | A key used once at its only boundary; framework constants already exist (`HttpHeaders.AUTHORIZATION`, `MediaType.APPLICATION_JSON_VALUE`) — use those | Constants grouped by concern (`PaymentHeaders`, `BillingTopics`, `CacheNames`) or an enum when the set is closed; prefer the framework's constant over a home-made one |
| REP-REGEX-FORMAT | The same regular expression, date/number format pattern or template string repeated, or compiled inside a method on every call | — | One precompiled constant (`Pattern`, `DateTimeFormatter`, `re.compile`) owned by the type that uses it |
| REP-MESSAGE | The same user-facing or error message text repeated, or messages assembled by concatenation in several places | Log messages (debug/operations text may repeat; see `JAVA-LOG-*`); messages that intentionally differ per context | Error-code enum with the message template, message bundle (`messages.properties`, i18n), or the exception type's constructor owning the text |
| REP-QUERY | Identical or near-identical SQL/JPQL/HQL/criteria fragments across statements (column lists, joins, filters, order clauses) | Trivially short clauses; deliberate query specialisation for an index | Shared fragment: MyBatis `<sql id>` + `<include>`, JPA named query / `Specification`, repository default method, view or CTE when the database owns it |
| REP-BLOCK | The same 3+ statement block copied with only literals changed (parallel `if` branches, copy-pasted mapping code) | Incidental similarity that will evolve independently (`DP-DRY` guard) | Extract a method or table-drive it (map of key → handler/value), or an enum carrying the varying data |

Severity: **MINOR** by default. **MAJOR** when the repetition already contains a divergence (two spellings of one value, `"Active"` vs `"ACTIVE"`), when the literal drives money, authorization or state transitions, or when one copy is a user-visible contract (API field, event name) that the others must match. A string compared with a silent `default`/`else` branch that swallows unknown values is a **BUG-LOGIC** lead, not only a style finding.

Finding format: list every location, name the owner (which type should hold the constant/enum), and show the one-line target (`enum RefundStatus { PENDING, DONE, FAILED }`).

---

## 2. Framework-specific literal rules

### MyBatis XML and annotations (MYB-*)

| ID | Signal | Guard | Fix |
| --- | --- | --- | --- |
| MYB-LITERAL | Hard-coded business values inside SQL (`status = 'DONE'`, `type = 2`, `deleted = 'N'`) repeated across statements or mappers | A value that is part of the schema definition itself (a check constraint) and used once | Bind a parameter (`#{status}`) supplied from an enum through a `TypeHandler` (`EnumTypeHandler` by name, or a custom code-based handler); for fixed filters, one `<sql id="activeOnly">` fragment |
| MYB-SUBSTITUTION | `${...}` string substitution with any value that can originate from a caller (filters, sort columns, table names) | `${}` fed only from a server-side allow-list or constant, with a comment saying so | `#{}` binding; for dynamic columns/order, map the input to a fixed allow-list (`<choose>`/enum) → also report **SEC-INJECTION** |
| MYB-FRAGMENT | The same column list, join or where-block pasted into several statements | Two statements, both short | `<sql id="…">` + `<include refid="…"/>`; one `<resultMap>` reused via `extends` |
| MYB-RESULT-MAP | `resultType="map"`/`"hashmap"`/`java.util.Map`, or `List<Map<String, Object>>` returned by the mapper interface | Ad-hoc reporting query used once at a boundary that immediately maps it | Typed result class or record (`resultType="com.acme.RefundRow"`), or an explicit `<resultMap>`; `MODEL-RECORD` |
| MYB-NPLUS1 | `<collection>`/`<association>` with a nested `select=` executed per row; a mapper call inside a Java loop | Lazy loading deliberately configured and justified by access pattern | Join with a nested `<resultMap>` or a batched `IN (...)` query (`PERF-NPLUS1`) |
| MYB-FOREACH-EMPTY | `IN (<foreach …>)` without guarding the empty collection | Repo helper that guards centrally | `<if test="ids != null and !ids.isEmpty()">` around the clause, or reject empty input at the service (`DP-FAIL`) |
| MYB-ENUM-ORDINAL | Enum persisted with `EnumOrdinalTypeHandler` or compared to an int column | Legacy schema documented as ordinal-based with a frozen enum order | Name- or code-based `TypeHandler`; explicit `code` field |
| MYB-STATEMENT-NAME | Statement ids outside the repo vocabulary (`getX` for a `select`, `doUpdate`, `process`), or one mapper mixing several aggregates | Repo's documented verbs | Follow `CONV-NAME` (`selectBy…`/`find…`, `insert`, `update`, `delete`); one mapper per aggregate/table family |
| MYB-DUPLICATE-SQL | The same statement body in two mappers or in XML and an annotation | — | One statement; call it from both places |

### JPA / Spring Data (JPA-*)

| ID | Signal | Fix |
| --- | --- | --- |
| JPA-ENUM-STRING | `@Enumerated` default (ordinal) or missing on an enum column; status stored as `String` with literal comparisons | `@Enumerated(EnumType.STRING)` or `AttributeConverter` with an explicit code; enum type on the entity field |
| JPA-QUERY-DUP | Same JPQL text in several `@Query` annotations or built by string concatenation | Named query constants, `Specification`, derived query, or a default method composing existing ones; never concatenate user input (`SEC-INJECTION`) |
| JPA-COLUMN-LITERAL | Column/table names repeated in native queries and projections | Constants on the entity (`Invoice_.STATUS` metamodel, or `public static final String TABLE`) |

### Spring (SPRING-*)

| ID | Signal | Fix |
| --- | --- | --- |
| SPRING-PATH-LITERAL | Repeated path prefixes across handler methods or `WebClient` calls | Class-level `@RequestMapping`; `UriBuilder`/constants for client paths |
| SPRING-HEADER-MDC-CACHE | Repeated header names, MDC keys, cache names, topic names, `@Qualifier` strings | Constants class per concern, or enum; prefer framework constants (`HttpHeaders`, `MediaType`) |
| SPRING-PROPERTY-KEY | The same `@Value("${…}")` key in several beans | `@ConfigurationProperties` type (`JAVA-SPRING-CONFIG-PROPS`) |
| SPRING-STATUS-LITERAL | `ResponseEntity.status(409)`, `HttpStatus` by int, error codes as strings | `HttpStatus` enum; the repo's `ErrorCode` enum (`CONV-EXC`) |

### Python (PY-*)

| ID | Signal | Fix |
| --- | --- | --- |
| PY-CLOSED-SET | `if status == "active"` chains, string sets passed around, Django `choices` tuples repeated | `enum.Enum`/`StrEnum` (3.11+) or `typing.Literal`; Django `TextChoices`/`IntegerChoices` |
| PY-DICT-RECORD | Dicts with fixed keys used as records (`row["amount"]`), tuples indexed by position, `**kwargs` grab-bags | `@dataclass(frozen=True)`, `NamedTuple`, `TypedDict` for wire shapes, pydantic model at boundaries |
| PY-CONSTANT | Magic numbers/strings repeated at call sites | Module-level `UPPER_SNAKE` constants (`Final`), one per concept |
| PY-REGEX-INLINE | `re.match(r"...")` with the same pattern in several functions | Module-level `re.compile` constant |
| PY-SQL-FSTRING | f-strings or `%` formatting building SQL (`text(f"... {x}")`, raw cursor execute) | Bound parameters; SQLAlchemy `text(...).bindparams` / ORM → also **SEC-INJECTION** |
| PY-LOG-FSTRING | `logger.info(f"...")` | Lazy `%s` arguments (`logger.info("… %s", x)`) when the repo logs that way |

### TypeScript / JavaScript (TS-*)

| ID | Signal | Fix |
| --- | --- | --- |
| TS-STRING-UNION | Repeated string literals compared/switched (`kind === 'card'`) without a type | String-literal union type, `as const` object, or `enum` per repo convention; exhaustive `switch` with `never` check |
| TS-MAGIC | Repeated numbers/keys (timeouts, header names, storage keys, event names) | `const` module constants; shared `events.ts`/`storageKeys.ts` |
| TS-RECORD-SHAPE | Object literals with the same shape created in several places | `interface`/`type` + a factory or builder function; `readonly` fields |

---

## 3. Data carriers: enum, builder, record, value object (MODEL-*)

The question for every data-holding type in the diff: **who guarantees that an instance is valid and complete?** If the answer is "every caller", the type is the problem.

| ID | Signal | Guard (do not flag) | Fix |
| --- | --- | --- | --- |
| MODEL-ENUM-FIELD | A field, column or parameter typed `String`/`int` whose values form a closed set (status, type, kind, channel, currency code with business rules, role) | External codes passed through unchanged; sets that genuinely change at runtime (then a value type + registry) | Enum with explicit `code`/`label`, a `fromCode` factory that fails fast on unknown values, and `STRING`/code persistence; serialization handles unknown incoming values deliberately (`@JsonEnumDefaultValue` or reject) |
| MODEL-BUILDER | A POJO/DTO constructed through a long constructor (≥4 parameters, especially several of the same type) or a `new X()` followed by a chain of setters that are never called again; telescoping constructors; `null` passed for optional parameters | JPA entities (framework needs a no-arg constructor and mutability by design — keep but validate in factory methods); 1–3 field values (use a record/static factory); framework-bound forms where the binder sets fields | Immutable type with a builder: Lombok `@Value @Builder(toBuilder = true)` when the repo uses Lombok, otherwise a nested `Builder` with required fields in `builder(required…)` and validation in `build()`; or a record plus a builder/`with*` methods for optional fields. Named/default arguments make this moot in Kotlin, Python, C#, Swift |
| MODEL-RECORD | A class whose body is fields + constructor + getters + `equals/hashCode/toString`, on Java 16+ (Kotlin: a class that should be `data class`; Python: a plain class holding attributes) | Needs mutation by design; must extend another class; JPA entity | `record` / `data class` / `@dataclass(frozen=True)`; add compact-constructor validation and defensive copies (`List.copyOf`) |
| MODEL-MUTABLE-DTO | Setters on a type that never changes after construction; public fields; `@Data` on a value type | Framework binding requires setters and no immutable alternative exists in the repo | Immutable carrier (record/`@Value`/builder); setters removed |
| MODEL-VALUE-OBJECT | Primitives carrying rules travelling together or separately: `BigDecimal amount` + `String currency`, `String iban`, `String email`, `long customerId` interchangeable with `long orderId` | A value with no invariant and no confusion risk (`DP-TYPES` guard) | Value object/record with validation in the constructor (`Money`, `Iban`, `CustomerId`); parse at the boundary (`DP-FAIL`) |
| MODEL-CONSTANTS-HOLDER | An `interface` used only to hold constants, or a grab-bag `Constants` class mixing unrelated concerns | — | Enum for closed sets; small `final` constants class per concern (`PaymentHeaders`), named by the concern, not `Constants` |
| MODEL-FLAG-SET | Several booleans that encode one state (`isActive`, `isSuspended`, `isClosed`) or a boolean + a string that must agree | Independent, orthogonal flags | One enum/sealed state with explicit transitions (`SMELL-BOOLEAN-BLINDNESS`) |
| MODEL-OPTIONAL-FIELD | `Optional` fields or constructor parameters to express "not provided" | — | Builder with defaults, overloaded factory, or nullable field with `@Nullable` per repo (`JAVA-NULL-OPTIONAL-RETURN`) |
| MODEL-PARTIAL-INIT | Objects valid only after a second call (`init()`, `setX` before `use`), or builders that build without required fields | — | Required fields on the constructor/`builder(required…)`; `build()` validates (`SMELL-TEMPORAL-COUPLING`) |
| MODEL-SERIALIZATION-COMPAT | Adding/renaming an enum constant or field on a type that crosses a wire or is persisted, without handling old readers/writers | Internal type never serialized | Unknown-value handling, default values, versioned schema, migration note (`API-COMPAT`, `DATA-MIGRATION`) |

Severity: **MINOR** by default. **MAJOR** when the carrier crosses a module/API boundary, holds money or identifiers that can be swapped (same-typed constructor arguments), or its string-typed state is already compared in several places (combine with REP-CLOSED-SET). Never recommend a builder or record where the framework needs mutability (JPA entities, some form binders) without saying how the framework constraint is met.

---

## 4. Rule IDs and severities

`REP-STRING`, `REP-NUMBER`, `REP-CLOSED-SET`, `REP-KEY`, `REP-REGEX-FORMAT`, `REP-MESSAGE`, `REP-QUERY`, `REP-BLOCK`; `MYB-LITERAL`, `MYB-SUBSTITUTION`, `MYB-FRAGMENT`, `MYB-RESULT-MAP`, `MYB-NPLUS1`, `MYB-FOREACH-EMPTY`, `MYB-ENUM-ORDINAL`, `MYB-STATEMENT-NAME`, `MYB-DUPLICATE-SQL`; `JPA-ENUM-STRING`, `JPA-QUERY-DUP`, `JPA-COLUMN-LITERAL`; `SPRING-PATH-LITERAL`, `SPRING-HEADER-MDC-CACHE`, `SPRING-PROPERTY-KEY`, `SPRING-STATUS-LITERAL`; `PY-CLOSED-SET`, `PY-DICT-RECORD`, `PY-CONSTANT`, `PY-REGEX-INLINE`, `PY-SQL-FSTRING`, `PY-LOG-FSTRING`; `TS-STRING-UNION`, `TS-MAGIC`, `TS-RECORD-SHAPE`; `MODEL-ENUM-FIELD`, `MODEL-BUILDER`, `MODEL-RECORD`, `MODEL-MUTABLE-DTO`, `MODEL-VALUE-OBJECT`, `MODEL-CONSTANTS-HOLDER`, `MODEL-FLAG-SET`, `MODEL-OPTIONAL-FIELD`, `MODEL-PARTIAL-INIT`, `MODEL-SERIALIZATION-COMPAT`.

Pair with the general rule when one applies and use the highest severity: `MYB-SUBSTITUTION` and `PY-SQL-FSTRING` with `SEC-INJECTION` (BLOCKER when caller-controlled); `REP-CLOSED-SET` with `BUG-LOGIC` when unknown values are swallowed; `MODEL-VALUE-OBJECT` with `DP-TYPES`/`BUG-MONEY`; `REP-QUERY`/`MYB-FRAGMENT` with `DP-DRY`. Repository conventions (`repo-conventions.md`) decide the *form* of the fix (Lombok or hand-written builder, `StrEnum` or `Literal`, `TextChoices`), never whether drift-prone repetition is acceptable.
