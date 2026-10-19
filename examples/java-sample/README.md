# Java sample — verify the skill in any tool

`baseline/` is a tiny Spring Boot billing service whose code **establishes conventions** (package-by-feature, `BillingException` + `ErrorCode` + `GlobalExceptionHandler`, SLF4J `log` with `{}`, `Money` value object, constructor injection, `PaymentGateway` port, `*Tests` with AssertJ). `change/` is a pull request that violates most of them and adds a few real bugs.

`EXPECTED.md` lists what an excellent review reports. Use it to check that a tool has loaded the skill and is applying the repository's conventions rather than generic advice.

## Without an AI tool (scanners only)
```bash
examples/java-sample/try.sh
```
Builds a temporary git repo (`main` = baseline + kit, `feature/refunds` = the change), prints the Convention Profile and the naming pre-scan. `KEEP=1` keeps the repo.

## With a tool
```bash
KEEP=1 examples/java-sample/try.sh      # note the printed path
cd <printed path>
```
Then:
- **Claude Code:** `claude` → `/code-quality-review` (or "review this branch against main").
- **Codex CLI:** `codex` → `$code-quality-review review the staged changes against main`.
- **Devin CLI:** `devin` → `/code-quality-review`.
- **Factory Droid:** `droid` → `/code-quality-review` or "review my branch".

Compare the report with `EXPECTED.md`. Signs the skill is **not** active: no "Conventions applied" section, `*Impl`/`Utils` generic advice without reference to the baseline, no rule IDs, formatting comments.
