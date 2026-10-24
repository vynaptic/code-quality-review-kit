# Expected review of `change/` against `baseline/`

Use this to calibrate a review against the committed baseline. Findings below still require evidence and severity assessment; `try.sh` checks only the naming and literal-scanner subset and the baseline acceptance cases. Scanner counts are advisory and cannot establish a convention or suppress a behavior defect.

**Verdict:** REQUEST CHANGES

**Conventions applied (what the reviewer must learn from `baseline/`):**
- Package-by-feature under `com.acme.billing.<feature>`; shared code only in `common` (`CONTRIBUTING.md`).
- All domain errors extend `BillingException(ErrorCode, message)`; `GlobalExceptionHandler` maps them (4 existing subclasses).
- Logging: SLF4J, `private static final Logger log`, `{}` placeholders (4 classes).
- Money is the `Money` record (`BigDecimal` + `Currency`), never `double`.
- Component dependencies use constructor injection; no field `@Autowired`.
- Remote calls go through the `PaymentGateway` port with `fetch*`/`send*` verbs and are translated to `PaymentProviderUnavailableException`.
- Controllers delegate to one service and return `*Response` records; entities are never serialised.
- Tests: JUnit 5 + AssertJ + Mockito, classes `*Tests`, methods `should…`.
- Persistence is Spring Data JPA (`InvoiceRepository extends JpaRepository`); `pom.xml` has no MyBatis dependency and no mapper XML.
- `RefundStatus` is already an enum (`RefundService.RefundStatus`); the repo persists enums by name, never as free strings.
- Java 17 baseline; Spotless is declared but has no configured execution. Avoid formatting taste comments.
- `CONTRIBUTING.md` defines this module's `get*` as local reads and `fetch*` as remote reads. A repository that documents remote `get*` would not justify M6 on I/O alone.
- Keep useful boundaries and operational controls with one implementation/value. `PaymentGateway` is justified by provider I/O; m5 requires absence of a current benefit, not merely an implementation count.

**Accepted cases:** `PaymentGateway`, `fetchDailyLimit`, `sendPayout`, `getErrorCode`, and `isGreaterThan`; `handleBillingException` is a valid framework handler despite a possible low-confidence scanner lead. Service classes requiring Spring subclass proxies may remain non-final. These do not become findings merely by matching a generic rule.

## BLOCKER
| ID | Rule | Location | Problem → fix |
| --- | --- | --- | --- |
| B1 | BUG-MONEY / DP-TYPES | `controllers/RefundController.java:24-26`, `refund/RefundService.java:18`, `util/PaymentUtils.java:16-19` | Refund amounts are `double`; comparison `total.doubleValue() < amount` and JSON built from a `double` lose cents and rounding → use `Money`. |
| B2 | JAVA-EXC-SWALLOW / BUG-ERROR | `refund/RefundService.java:25-27`, `util/PaymentUtils.java:21` | Provider failures appear successful: a transport exception is swallowed, and an HTTP 503 body is returned without checking its status → validate the response and translate failures to `PaymentProviderUnavailableException`. |
| B3 | SEC-INJECTION / JAVA-COLL-STRING | `util/PaymentUtils.java:19` | JSON body built by string concatenation from `invoiceId` → request forgery with a crafted id → serialise with the repo's Jackson/`RestClient` as in `StripePaymentGateway`. |
| B4 | SEC-INJECTION / MYB-SUBSTITUTION | `resources/mappers/RefundMapper.xml:9` | `ORDER BY ${sortColumn}` splices a caller-supplied string into SQL → `sortColumn = "1; DROP TABLE refund"`-class injection → map the input to an allow-list/enum of sortable columns, or `#{}` with a fixed `<choose>`. |

## MAJOR
| ID | Rule | Location | Problem → fix |
| --- | --- | --- | --- |
| M1 | CONV-EXC / JAVA-EXC-HIERARCHY | `controllers/RefundController.java:27`, `util/PaymentUtils.java:24` | `throw new RuntimeException(...)` bypasses `BillingException`/`ErrorCode` → clients get 500 without a code → `RefundExceedsInvoiceTotalException extends BillingException`; `PaymentProviderUnavailableException("stripe", e)` in the adapter. |
| M2 | JAVA-EXC-CAUSE | `util/PaymentUtils.java:24` | `new RuntimeException(e.getMessage())` drops the cause. |
| M3 | CONV-LOG / JAVA-LOG-FACADE / JAVA-LOG-CONCAT | `refund/RefundService.java:10`, `:22` | JUL logger named `LOGGER`, instance field, string concatenation — the repo uses SLF4J `private static final Logger log` with `{}` (4 classes). |
| M4 | JAVA-SPRING-NO-LOGIC-IN-CONTROLLER / CONV-PKG | `controllers/RefundController.java:25-29` | Controller loads the entity, applies the refund rule and calls the service; repository injected into a controller → move the rule to `RefundService`, return a `RefundResponse`. |
| M5 | JAVA-SPRING-DTO-BOUNDARY | `controllers/RefundController.java:24`, `:30` | Returns the `Invoice` entity as the HTTP response; the repo returns `*Response` records. |
| M6 | NAME-M2 | `refund/RefundService.java:30` | `getRefund` performs a remote HTTP call contrary to the module's documented local-read contract for `get*` → `fetchRefundStatus`. |
| M7 | SOLID-DIP / DP-LAYER / CONV-MODULE | `refund/RefundService.java:21`, `util/PaymentUtils.java:15-25` | Service calls Stripe through a static HTTP helper instead of the `PaymentGateway` port; a second HTTP client (`java.net.http`) next to the configured `RestClient` → add `sendRefund` to `PaymentGateway`, implement in `StripePaymentGateway`. |
| M8 | JAVA-NULL-OPTIONAL-USE / BUG-NULL | `controllers/RefundController.java:25` | `findById(...).get()` throws `NoSuchElementException` (500) for an unknown invoice → `orElseThrow(() -> new InvoiceNotFoundException(invoiceId))`. |
| M9 | TEST-MISSING | `refund/RefundService.java` | No test for the refund rule, the provider failure path or the controller. |
| M10 | NAME-T2 / SOLID-SRP / JAVA-STYLE-UTILS | `util/PaymentUtils.java:11` | `PaymentUtils` mixes HTTP calls, JSON parsing, date formatting and validation; not a single-subject static holder, and it holds state (`CLIENT`, `DATE_FORMAT`) → delete; HTTP goes to the gateway adapter, parsing to the adapter, date formatting nowhere (unused). |
| M11 | CONV-DEP / CONV-DATA / BUG-WIRING | `resources/mappers/RefundMapper.xml:1-27` | A MyBatis mapper in a Spring Data JPA module: no MyBatis dependency in `pom.xml`, no `RefundMapper` interface, nothing loads the XML → either dead or a second persistence stack → a `RefundRepository extends JpaRepository` (or document the migration as an ADR). |
| M12 | REP-CLOSED-SET / MODEL-ENUM-FIELD / MYB-LITERAL | `resources/mappers/RefundMapper.xml:8`, `:13`, `:19`, `:24`; `util/PaymentUtils.java:29-32` | `'DONE'`, `'FAILED'`, `'PENDING'` hard-coded five times in SQL plus `"done"`/`"failed"` substring parsing in Java while `RefundStatus` already exists → bind `#{status}` from the enum (name-based `TypeHandler`/`EnumType.STRING`), parse with `RefundStatus.valueOf` and fail fast on unknown values. MAJOR because the lowercase Java copies already diverge from the uppercase SQL copies. |

## MINOR
| ID | Rule | Location | Problem → fix |
| --- | --- | --- | --- |
| m1 | CONV-PKG | `controllers/RefundController.java:1`, `util/PaymentUtils.java:1` | New `controllers` and `util` packages in a package-by-feature repo → `com.acme.billing.refund`. |
| m2 | CONV-DI / JAVA-SPRING-CTOR-INJECT | `controllers/RefundController.java:17-21` | Field `@Autowired`; existing components use constructor injection. |
| m3 | NAME-M3 | `controllers/RefundController.java:24`, `refund/RefundService.java:18` | `processRefund` says nothing about the outcome → `issueRefund` / `refundInvoice`. |
| m4 | NAME-M5 | `controllers/RefundController.java:24`, `refund/RefundService.java:18` | Boolean flag `partial` → `RefundKind.PARTIAL/FULL` or derive from the amount. |
| m5 | OVER-INTERFACE | `refund/RefundPolicy.java:3`, `refund/DefaultRefundPolicy.java:6` | No distinct responsibility, invariant, useful test seam or operational/boundary benefit is shown for this interface → keep a class `RefundPolicy` (or inline the two-line check). One implementation alone is not a finding. |
| m6 | NAME-M4 / NAME-M3 | `util/PaymentUtils.java:42` | `checkAmount` returns boolean → `isPositiveAmount`; unused anyway (`OVER-FUTURE`). |
| m7 | CONV-TEST / TEST-QUALITY | `test/.../RefundServiceTest.java:5-12` | Hamcrest in an AssertJ repo; class `*Test` instead of `*Tests`; method `test1` → `shouldRefundOpenInvoice…`. The test also tests `DefaultRefundPolicy`, not `RefundService`. |
| m8 | CONV-NAME / NAME-V4 | `refund/RefundService.java:21` | `callProvider` for a remote write; the repo vocabulary is `send*` for outbound and `fetch*` for remote reads. |
| m9 | OVER-FUTURE / SMELL-DEAD-CODE | `util/PaymentUtils.java:38-44` | `formatDate` and `checkAmount` have no callers; remove them. The unused formatter does not demonstrate a concurrent execution defect. |
| m10 | MYB-RESULT-MAP / MODEL-RECORD | `resources/mappers/RefundMapper.xml:5`, `:16` | `resultType="map"` returns untyped `Map<String, Object>` rows → a `RefundRow` record (or `<resultMap>`). |
| m11 | MYB-FOREACH-EMPTY / BUG-LOGIC | `resources/mappers/RefundMapper.xml:19-20` | `invoice_id IN (<foreach>)` with an empty `invoiceIds` produces `IN ()` → SQL error at runtime → guard with `<if test="invoiceIds != null and !invoiceIds.isEmpty()">` or reject empty input in the service. |
| m12 | MYB-FRAGMENT / REP-QUERY | `resources/mappers/RefundMapper.xml:5-6`, `:16-17` | Same column list in two statements → `<sql id="refundColumns">` + `<include>`. |
| m13 | MYB-STATEMENT-NAME / CONV-NAME | `resources/mappers/RefundMapper.xml:5`, `:12`, `:16` | `getDoneRefunds`/`getFailedRefunds` use `get` for a query in a repo whose lookups are `find*`; the status belongs in a parameter, not the statement name → `findByStatus`. |

## Questions for the author
- Where is access to the refund endpoint authorized? This fixture has no runtime wiring; confirm exposure and any external enforcement before reporting `SEC-AUTHZ` as a blocker.
- Is a refund allowed after the invoice is `PAID` only, or also for `OPEN` invoices? The controller's check does not look at status.
- Should partial refunds be tracked on the invoice (new state), or is this fire-and-forget to the provider?
