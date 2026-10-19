# Verification

From the kit checkout:

```bash
python3 -m unittest discover -s tests -v
bash examples/java-sample/try.sh
mvn -B -f examples/java-sample/baseline/pom.xml test
```

The Python suite uses real temporary repositories/files to check scanner inputs, snapshot isolation, naming exceptions, installer preservation and sample assertions. Java tests require JDK 17+ and Maven; first use may download dependencies.

## Skill behavior

`fixtures/review_cases.json` contains isolated changes plus expected findings/valid exceptions. It covers documented remote reads, misleading predicates, Spring proxies, operational versus speculative options, justified versus unnecessary interfaces, JDK-specific synchronization, thread-safe randomness, repository naming and aggregate invariants.

1. Give an independent reviewer the top-level instructions and each case's `id`, `context`, `code`; withhold `expected`.
2. Ask it to apply the installed skill and return a JSON array of `{id, findings: [{rule, reason}]}`. Run a no-skill control separately when changing guidance.
3. Save the response and run `python3 tests/check_review_results.py /path/to/results.json`.
4. Inspect every finding and proposed fix. Passing IDs alone do not prove sound reasoning. Repeat on each intended CLI/hosted surface; bot filters can hide low-priority findings.

This is a semantic evaluation, not an automated LLM service. The local suite does not prove that Devin, Factory Droid, Claude and Codex produce identical reviews. Record the tool/version, scenario results and limitations for rollout.
