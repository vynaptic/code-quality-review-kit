# Report Template

Use this structure exactly. Omit empty severity sections. Keep each finding to the point: one problem, its cost, one fix.

````markdown
## Code Quality Review — <branch / PR title>

**Verdict:** REQUEST CHANGES | APPROVE WITH COMMENTS | APPROVE
**Scope:** <base>..<head> <(+ working tree) if uncommitted/untracked changes were included>, <N> files, +<added>/-<removed> lines <(+ what was not reviewed, if anything)>
**Summary:** <2–3 sentences: what the change does, overall quality, the most important issue>

| BLOCKER | MAJOR | MINOR | NIT |
|:-:|:-:|:-:|:-:|
| 0 | 2 | 5 | 1 |

### Conventions applied
<3–8 bullets from the Convention Profile that influenced this review, each with evidence; include defaults that were NOT applied because the repo does it differently>
- Logging: SLF4J, `private static final Logger log`, `{}` placeholders (41 classes) — enforced as CONV-LOG.
- Exceptions: all domain errors extend `BillingException(ErrorCode, …)`; mapped by `GlobalExceptionHandler` — enforced as CONV-EXC.
- Packaging: package-by-feature under `com.acme.billing.<feature>` (`CONTRIBUTING.md` §3).
- Naming: repo uses `*Impl` for implementations (38 types) — NAME-T4 not applied.
- Tests: JUnit 5 + AssertJ, classes `*Tests`, methods `should…`.
- Java baseline: 17 (records yes, pattern switch no).

### BLOCKER
#### B1 · BUG-CONCURRENCY · `src/payouts/PayoutService.kt:88`
**Problem:** Balance is read, checked and written in three statements without locking; two concurrent payouts can both pass the check.
**Trigger:** Two requests for 60.00 against a 100.00 balance arrive together → both succeed, balance −20.00.
**Fix:** Use an atomic conditional update (`UPDATE … SET balance = balance - :amt WHERE id = :id AND balance >= :amt`) and check the affected row count, or optimistic locking with a version column.

### MAJOR
#### M1 · NAME-M2 (verb contract) · `src/fx/RateService.ts:42`
**Problem:** `getExchangeRate()` performs an HTTP call and writes to the cache; `get` promises a cheap, side-effect-free read.
**Fix:** Rename to `fetchExchangeRate()`; keep a separate `getCachedExchangeRate()` if a cheap read is needed.

#### M2 · SOLID-DIP / DP-LAYER · `src/domain/Invoice.java:15`
**Problem:** Domain class instantiates `new SmtpMailer()`; the domain now depends on infrastructure and cannot be unit-tested without SMTP.
**Cost:** Switching mail provider or adding SMS notifications requires editing the domain model.
**Fix:** Introduce `InvoiceNotifier` port in the domain, inject it, implement `SmtpInvoiceNotifier` in the infrastructure layer.

#### M3 · CONV-EXC / JAVA-EXC-HIERARCHY · `src/main/java/com/acme/billing/refund/RefundService.java:64`
**Problem:** `throw new RuntimeException("refund exceeds captured amount")` bypasses the repo's error contract: every domain error extends `BillingException(ErrorCode, …)` and `GlobalExceptionHandler` maps the code to an HTTP status (`BillingException.java:12`, 23 existing subclasses). Clients will get a 500 with no error code.
**Fix:** `throw new RefundExceedsCaptureException(refundId, captured)` extending `BillingException` with `ErrorCode.REFUND_EXCEEDS_CAPTURE`.

### MINOR
#### m1 · NAME-T2 · `src/util/PaymentHelper.py:1`
**Problem:** `PaymentHelper` groups refund calculation and IBAN formatting (two responsibilities, vague name).
**Fix:** Split into `RefundCalculator` and `IbanFormatter`.

#### m2 · OVER-INTERFACE · `src/main/java/com/acme/billing/refund/RefundPolicy.java:1`
**Problem:** New interface `RefundPolicy` has exactly one implementation (`DefaultRefundPolicy`), no second variant in this PR or the backlog, and it is not an I/O boundary; the only consumer is `RefundService`.
**Cost:** Two files and an indirection for every reader, with nothing hidden.
**Fix:** Keep the class `RefundPolicy` and inject it directly; extract the interface when a second policy exists.

#### m3 · CONV-LOG / JAVA-LOG-CONCAT · `src/main/java/com/acme/billing/refund/RefundService.java:71`
**Problem:** `log.info("Refund " + id + " done")` — the repo uses `{}` placeholders everywhere (41 classes) and this message builds the string even when INFO is off.
**Fix:** `log.info("Refund {} completed", id)`.

### NIT
#### n1 · NAME-V1 · `src/report/export.go:23` — `res` → `settlementRows`.

### Rename & signature table
| Location | Current | Proposed | Rule |
|---|---|---|---|
| `src/fx/RateService.ts:42` | `getExchangeRate` | `fetchExchangeRate` | NAME-M2 |
| `src/util/PaymentHelper.py:1` | `PaymentHelper` | `RefundCalculator`, `IbanFormatter` | NAME-T2 |
| `src/payout/Payouts.java:14` | `pay(String id, double amt, boolean instant)` | `payOutMerchant(MerchantId id, Money amount, PayoutScheme scheme)` | NAME-M5, DP-TYPES |

### Tests
<missing or weak tests, each with the case that should be covered>

### Questions for the author
<only genuine uncertainties; each phrased so it can be answered yes/no or with a fact>

### What's good
<1–3 bullets, specific — optional, never padding>
````

## Conventions
- IDs: `B#` blocker, `M#` major, `m#` minor, `n#` nit.
- Heading: `#### <ID> · <RULE-ID>[ / <RULE-ID>…] · <location>`; add ` · pre-existing` when the problem predates the change.
- Required fields: **Problem** and **Fix** always; **Trigger** for BUG-*/SEC-*/PERF-* findings; **Cost** for design findings (SOLID-*, DP-*, PAT-*, SMELL-*, OVER-*, READ-*); **evidence of the convention** (file:line of existing code, or the documented rule, plus the profile count) inside **Problem** for CONV-* findings; the **missing second case** inside **Problem** for OVER-* findings. Optional **Related:** `B3, B4` when findings share a root cause; give the shared fix once and write `Fix: see B4` in the others.
- **Conventions applied** is mandatory (write "none established; skill defaults applied" for a new or tiny repo). It is where a default that the repo overrides is recorded, so nobody asks "why wasn't `*Impl` flagged?".
- Missing tests for new logic are a numbered finding (TEST-MISSING, MAJOR); the **Tests** section lists the concrete cases.
- Locations are `path:line` (or `path:start-end`) on the **new** side of the diff; list all locations when one root cause appears in several places.
- Code in fixes is short and shows the target shape, not a full rewrite.
- For PR platforms: post each finding inline as `[SEVERITY][RULE-ID] path:line — <problem> → <fix>`, and the header + counts + rename table as the summary comment.
