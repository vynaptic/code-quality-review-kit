# Contributing

- Package by feature: `com.acme.billing.<feature>` holds that feature's controller, service, repository, DTOs and exceptions. Shared code goes in `common` only.
- Every domain error extends `BillingException` with an `ErrorCode`; `GlobalExceptionHandler` turns it into a problem body. Never throw raw `RuntimeException` from service code.
- Logging: SLF4J, `private static final Logger log`, `{}` placeholders, INFO only for business events.
- Money is always the `Money` value object, never `double`/`BigDecimal` on its own.
- Tests: JUnit 5 + AssertJ + Mockito; classes end in `Tests`; methods read `should<Outcome>…`.
- Spotless formats the code in CI; do not discuss formatting in reviews.
