# Contributing

- Package by feature: `com.acme.billing.<feature>` holds that feature's controller, service, repository, DTOs and exceptions. Shared code goes in `common` only.
- Every domain error extends `BillingException` with an `ErrorCode`; `GlobalExceptionHandler` turns it into a problem body. Never throw raw `RuntimeException` from service code.
- Logging: SLF4J, `private static final Logger log`, `{}` placeholders, INFO only for business events.
- Read names in this module: `get*` is a cheap local read; `fetch*` performs remote I/O. Judge names against these contracts, not a universal ban on remote `get*` names.
- Interfaces and configuration need a current benefit: a real boundary, invariant, test seam or operational requirement. `PaymentGateway` isolates provider I/O; one implementation is enough for that boundary.
- Money is always the `Money` value object, never `double`/`BigDecimal` on its own.
- Tests: JUnit 5 + AssertJ + Mockito; classes end in `Tests`; methods read `should<Outcome>…`.
- Spotless is declared as a formatter example; this fixture has no formatter configuration or CI gate. Do not turn formatting taste into review findings.
