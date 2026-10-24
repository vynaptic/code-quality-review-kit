# Repository conventions

A convention finding must identify the applicable rule and how the change diverges. Evidence from another module, generated code or the proposed change does not establish a local standard.

## 1. Precedence

1. User instructions and authorized review scope.
2. Active `.agents/review-overrides.md` rules (HTML comments are examples).
3. Applicable repository instructions, CONTRIBUTING, ADRs, API contracts, build/lint configuration and architecture tests; more specific scope wins.
4. Consistent existing code in the affected module, language and role.
5. Skill defaults.

Conventions choose style and architecture; they cannot make an actual bug safe. Conversely, a default is not a correctness contract: a documented remote `getX`, soft `delete`, checked exception or framework callback may be correct. `NAME-M2` requires behavior that contradicts the applicable contract or clearly misleads its callers.

If authoritative rules conflict, state the conflict and ask a focused question; do not invent a rule. An intentional, documented migration may introduce a new convention. Confirm its scope and compatibility rather than suppressing it as inconsistency.

## 2. Evidence and baseline

- Resolve one base commit for both the diff and `scan_conventions.py --ref <base-sha>`. Staged review uses HEAD. For files without a base, label current-tree evidence explicitly.
- Read governing documents plus 2–3 neighboring examples with the same role. Learn vocabulary, package/module direction, exception translation, logging, nullability, DI, validation/mapping, test naming/stack, language/runtime baseline and tooling.
- Prefer the affected module. At least three independent, relevant occurrences can support an inference only if no stronger competing pattern exists. Counts are leads, not votes; legacy exceptions, samples, comments, tests and generated/vendor files are not production convention evidence.
- Check whether proposed instructions/overrides change the policy itself. Review that change explicitly; do not let it retroactively excuse a defect in the same diff.
- Profiler output is a draft. Document its commit/scope and any sampling, skipped files or failures. Confirm relevant examples manually; do not claim a repository-wide convention from a partial scan.

## 3. Profile and findings

In **Conventions applied**, record only rules that affected the review, with source locations. Include justified departures from skill defaults. Example: “Implementations use `*Impl` in billing (CONTRIBUTING §2 and three neighboring repositories); NAME-T4 default not applied.” If evidence is insufficient, say so and use language idioms/defaults cautiously.

| Rule | Check |
| --- | --- |
| CONV-NAME | Domain vocabulary, verb semantics, role suffixes and local naming style |
| CONV-PKG / CONV-MODULE | Package placement, ownership, exported/internal APIs and dependency direction |
| CONV-EXC | Existing error contracts, translation boundaries and client mapping |
| CONV-LOG | Logging facade, declaration, structured keys, placeholders and ownership |
| CONV-NULL / CONV-DI | Nullability and dependency injection contracts |
| CONV-VALIDATION / CONV-MAP | Invariant enforcement and boundary mapping conventions |
| CONV-TEST / CONV-DOC | Test stack/naming and documentation expectations |
| CONV-DEP / CONV-STYLE | Reuse existing libraries and non-tool-enforced style |

State the evidence, concrete cost and compatible fix. Severity follows impact, not the number of differences. Existing unsafe behavior remains a correctness concern; do not demand a repo-wide cleanup when reviewing a local change.
