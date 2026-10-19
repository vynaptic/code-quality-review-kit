# Review report

Use the host's required schema when present. Otherwise use the compact structure below; omit empty sections. Preserve evidence and honest severity in either format. A hosted bot's filtered output does not prove a complete naming/design review.

```markdown
**Verdict:** REQUEST CHANGES | APPROVE WITH COMMENTS | APPROVE | INCOMPLETE
**Scope:** base/head or files, working-tree/index inclusion, and material coverage gaps.

**Conventions applied:** relevant rules with source locations; include defaults displaced by repository/API contracts. Say when no convention is established.

1. **[MAJOR][NAME-M2 / DP-CQS] path:line — Eligibility query reserves stock.**
   Contract/evidence: the documented pure query is called repeatedly by preview rendering.
   Impact/trigger: opening the preview reserves stock without an order being submitted.
   Fix: keep eligibility pure and reserve only in the authorized order command.

**Checks:** commands actually run, results, and checks blocked or omitted.
**Questions:** unresolved facts that change a finding; omit speculation.
```

Each finding contains severity, rule IDs, a verified location, evidence/impact, and the smallest safe fix. Add a concrete input/state/interleaving for correctness/security/performance claims. For design findings name the current cost and account for applicable boundaries, invariants, compatibility and operational needs. For `CONV-*` cite the scoped rule or relevant existing code. Counts alone prove neither a rule nor its violation.

Merge duplicate root causes and list affected locations together. Use a rename table only when several related renames are easier to review that way. Do not repeat the same findings in a separate tests or summary section.

Missing tests for new business logic are actionable only with concrete uncovered cases (`TEST-MISSING`). Do not claim a run succeeded without output evidence. Use INCOMPLETE when material scope could not be reviewed; retain confirmed findings without implying approval of the rest.

External posting requires authorization. If authorized, use inline locations on the correct diff side and a short summary of verdict, conventions, checks and limitations. Never raise severity to bypass a bot's priority filter.
