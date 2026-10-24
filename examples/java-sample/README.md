# Java sample — verify the skill in any tool

`baseline/` is a compilable Spring billing module with documented conventions (package-by-feature, `BillingException` + `ErrorCode` + `GlobalExceptionHandler`, SLF4J `log` with `{}`, `Money`, constructor injection, `PaymentGateway`, `*Tests` with AssertJ). `change/` deliberately violates several contracts and adds bugs, including a MyBatis mapper XML (`${}` substitution, hard-coded status literals, map results) dropped into a Spring Data JPA module. The module has no application bootstrap or runtime wiring; its four unit tests are runnable with Java 17+ and Maven:

```bash
mvn -f examples/java-sample/baseline/pom.xml validate test
```

The pinned Spring Boot parent manages dependencies and test plugins. Downloads require Maven Central access. The intentionally faulty change is a review fixture, not part of the baseline test suite.

`EXPECTED.md` lists what an excellent review reports. Use it to check that a tool has loaded the skill and is applying the repository's conventions rather than generic advice.

## Without an AI tool (scanners only)
```bash
examples/java-sample/try.sh
```
Builds a temporary Git repo (`main` = baseline + kit, `feature/refunds` = staged change), profiles committed `main` with `--ref main`, and checks expected naming and literal candidates plus accepted baseline names. A missing expected candidate or flagged accepted name fails the command. `KEEP=1` keeps the repo, including on failure.

Counts are advisory: they do not establish contracts or suppress findings. Confirm documented and module-local behavior manually. Here `get*` is explicitly local and `fetch*` remote; another repository may define `get*` differently. A single implementation can justify a useful I/O boundary such as `PaymentGateway`. The scanner can still emit a low-confidence `handleBillingException` candidate; its `@ExceptionHandler` role makes it acceptable on review. Outside a diff review, omit `--ref` for a draft of the current working tree; its local edits are not baseline evidence.

## With a tool
```bash
KEEP=1 examples/java-sample/try.sh      # note the printed path
cd <printed path>
```
Then:
- **Claude Code:** `claude` → `/strict-code-review` (or "review this branch against main").
- **Codex CLI:** `codex` → `$strict-code-review review the staged changes against main`.
- **Devin CLI:** `devin` → `/strict-code-review`.
- **Factory Droid:** `droid` → `/strict-code-review` or "review my branch".

Compare the report with `EXPECTED.md`. Signs the skill is **not** active: no "Conventions applied" section, `*Impl`/`Utils` generic advice without reference to the baseline, no rule IDs, formatting comments.
