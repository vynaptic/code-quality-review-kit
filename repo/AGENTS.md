<!-- code-quality-review-kit:start -->
## Skills

Use `.agents/skills/code-quality-review/SKILL.md` for requested code, PR, branch, diff or file reviews. Codex invokes it with `$code-quality-review`; Devin CLI and Factory Droid use `/code-quality-review`. Review-only unless fixes are requested.

## Code Review Rules

- Follow the full skill when available. Apply user instructions, active `.agents/review-overrides.md`, documented contracts, then verified repository conventions before default style rules. Defaults never override a framework/API contract; established style never excuses a concrete bug.
- Review correctness, security, compatibility and tests first. Trace affected callers; give a concrete trigger and impact for each bug. Assess names against their actual documented or observed contract.
- Learn conventions from the base revision and neighbouring code. Scanner counts are leads, not proof that a convention is valid or dominant. Cite evidence for convention findings.
- Require a current benefit for abstractions and configuration: a real boundary, invariant, lifecycle, operational need or second use. Respect the Java baseline and Spring proxy requirements when suggesting changes.
- Report actionable findings with location, evidence and fix. For detailed CLI reviews, use the skill's rule IDs, severity and **Conventions applied** summary. Hosted review bots retain their own severity filters and output format; do not claim they produced the complete CLI report.
<!-- code-quality-review-kit:end -->
