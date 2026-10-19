# Expected review of `change/` against `baseline/`

Use this to check that a tool has picked up the skill correctly. A good review of the sample PR produces findings equivalent to the ones below (wording may differ; rule IDs, severities and locations should match). Anything not listed here that a tool reports is either a false positive or a bonus — judge it by the rules.

**Verdict:** REQUEST CHANGES

**Conventions applied (what the reviewer must learn from `baseline/`):**
- Package-by-feature under `com.acme.billing.<feature>`; shared code only in `common` (`CONTRIBUTING.md`).
- All domain errors extend `BillingException(ErrorCode, message)`; `GlobalExceptionHandler` maps them (4 existing subclasses).
- Logging: SLF4J, `private static final Logger log`, `{}` placeholders (5 classes).
- Money is the `Money` record (`BigDecimal` + `Currency`), never `double`.
- Constructor injection everywhere (6 classes); no field `@Autowired`.
- Remote calls go through the `PaymentGateway` port with `fetch*`/`send*` verbs and are translated to `PaymentProviderUnavailableException`.
- Controllers delegate to one service and return `*Response` records; entities are never serialised.
- Tests: JUnit 5 + AssertJ + Mockito, classes `*Tests`, methods `should…`.
- Java 17 baseline; Spotless formats (no formatting comments).

## BLOCKER
| ID | Rule | Location | Problem → fix |
| --- | --- | --- | --- |
| B1 | BUG-MONEY / DP-TYPES | `controllers/RefundController.java:24-26`, `refund/RefundService.java:18`, `util/PaymentUtils.java:16-19` | Refund amounts are `double`; comparison `total.doubleValue() < amount` and JSON built from a `double` lose cents and rounding → use `Money`. |
| B2 | JAVA-EXC-SWALLOW / BUG-ERROR | `refund/RefundService.java:25-27` | `catch (Exception e) { // ignore }` around the provider call: a failed refund returns 200 and is never retried (silent money loss). Trigger: provider returns 503 → caller sees success → translate to `PaymentProviderUnavailableException` as `StripePaymentGateway` does. |
| B3 | BUG-CONCURRENCY / JAVA-CONC-UNSAFE-TYPES | `util/PaymentUtils.java:13`, `:39` | Static shared `SimpleDateFormat` used from request threads → corrupted dates under concurrency → `DateTimeFormatter`. |
| B4 | SEC-INJECTION / JAVA-COLL-STRING | `util/PaymentUtils.java:19` | JSON body built by string concatenation from `invoiceId` → request forgery with a crafted id → serialise with the repo's Jackson/`RestClient` as in `StripePaymentGateway`. |
| B5 | SEC-AUTHZ | `controllers/RefundController.java:23-24` | New money-moving endpoint has no authorization rule (the baseline has none either, but `common` conventions do not cover security yet) — ask the author; BLOCKER if the service is exposed. |

## MAJOR
| ID | Rule | Location | Problem → fix |
| --- | --- | --- | --- |
| M1 | CONV-EXC / JAVA-EXC-HIERARCHY | `controllers/RefundController.java:27`, `util/PaymentUtils.java:24` | `throw new RuntimeException(...)` bypasses `BillingException`/`ErrorCode` → clients get 500 without a code → `RefundExceedsInvoiceTotalException extends BillingException`; `PaymentProviderUnavailableException("stripe", e)` in the adapter. |
| M2 | JAVA-EXC-CAUSE | `util/PaymentUtils.java:24` | `new RuntimeException(e.getMessage())` drops the cause. |
| M3 | CONV-LOG / JAVA-LOG-FACADE / JAVA-LOG-CONCAT | `refund/RefundService.java:10`, `:22` | JUL logger named `LOGGER`, instance field, string concatenation — the repo uses SLF4J `private static final Logger log` with `{}` (5 classes). |
| M4 | JAVA-SPRING-NO-LOGIC-IN-CONTROLLER / CONV-PKG | `controllers/RefundController.java:25-29` | Controller loads the entity, applies the refund rule and calls the service; repository injected into a controller → move the rule to `RefundService`, return a `RefundResponse`. |
| M5 | JAVA-SPRING-DTO-BOUNDARY | `controllers/RefundController.java:24`, `:30` | Returns the `Invoice` entity as the HTTP response; the repo returns `*Response` records. |
| M6 | NAME-M2 | `refund/RefundService.java:30` | `getRefund` performs a remote HTTP call; `get` promises a cheap local read → `fetchRefundStatus`. |
| M7 | SOLID-DIP / DP-LAYER / CONV-MODULE | `refund/RefundService.java:21`, `util/PaymentUtils.java:15-25` | Service calls Stripe through a static HTTP helper instead of the `PaymentGateway` port; a second HTTP client (`java.net.http`) next to the configured `RestClient` → add `sendRefund` to `PaymentGateway`, implement in `StripePaymentGateway`. |
| M8 | JAVA-NULL-OPTIONAL-USE / BUG-NULL | `controllers/RefundController.java:25` | `findById(...).get()` throws `NoSuchElementException` (500) for an unknown invoice → `orElseThrow(() -> new InvoiceNotFoundException(invoiceId))`. |
| M9 | TEST-MISSING | `refund/RefundService.java` | No test for the refund rule, the provider failure path or the controller. |
| M10 | NAME-T2 / SOLID-SRP / JAVA-STYLE-UTILS | `util/PaymentUtils.java:11` | `PaymentUtils` mixes HTTP calls, JSON parsing, date formatting and validation; not a single-subject static holder, and it holds state (`CLIENT`, `DATE_FORMAT`) → delete; HTTP goes to the gateway adapter, parsing to the adapter, date formatting nowhere (unused). |

## MINOR
| ID | Rule | Location | Problem → fix |
| --- | --- | --- | --- |
| m1 | CONV-PKG | `controllers/RefundController.java:1`, `util/PaymentUtils.java:1` | New `controllers` and `util` packages in a package-by-feature repo → `com.acme.billing.refund`. |
| m2 | CONV-DI / JAVA-SPRING-CTOR-INJECT | `controllers/RefundController.java:17-21` | Field `@Autowired`; the repo uses constructor injection (6 classes). |
| m3 | NAME-M3 | `controllers/RefundController.java:24`, `refund/RefundService.java:18` | `processRefund` says nothing about the outcome → `issueRefund` / `refundInvoice`. |
| m4 | NAME-M5 | `controllers/RefundController.java:24`, `refund/RefundService.java:18` | Boolean flag `partial` → `RefundKind.PARTIAL/FULL` or derive from the amount. |
| m5 | OVER-INTERFACE | `refund/RefundPolicy.java:3`, `refund/DefaultRefundPolicy.java:6` | Interface with one implementation, no I/O boundary, one consumer → keep a class `RefundPolicy` (or inline the two-line check). |
| m6 | NAME-M4 / NAME-M3 | `util/PaymentUtils.java:42` | `checkAmount` returns boolean → `isPositiveAmount`; unused anyway (`OVER-FUTURE`). |
| m7 | CONV-TEST / TEST-QUALITY | `test/.../RefundServiceTest.java:5-12` | Hamcrest in an AssertJ repo; class `*Test` instead of `*Tests`; method `test1` → `shouldRefundOpenInvoice…`. The test also tests `DefaultRefundPolicy`, not `RefundService`. |
| m8 | CONV-NAME / NAME-V4 | `refund/RefundService.java:21` | `callProvider` for a remote write; the repo vocabulary is `send*` for outbound and `fetch*` for remote reads. |
| m9 | OVER-FUTURE / SMELL-DEAD-CODE | `util/PaymentUtils.java:38-44` | `formatDate` and `checkAmount` have no callers. |
| m10 | JAVA-LOG-LEVEL | `refund/RefundService.java:22` | INFO per refund with the amount is fine as a business event, but the message is in the swallowed-exception block and logs on partial failure too → log after the gateway confirms, as `StripePaymentGateway` does. |

## NIT
| ID | Rule | Location | Note |
| --- | --- | --- | --- |
| n1 | JAVA-STYLE-CONSTANTS | `refund/RefundService.java:10` | `LOGGER` → `log` (repo style). |

## Questions for the author
- Is a refund allowed after the invoice is `PAID` only, or also for `OPEN` invoices? The controller's check does not look at status.
- Should partial refunds be tracked on the invoice (new state), or is this fire-and-forget to the provider?
