<!-- code-quality-review-kit:start -->
## Code quality review

The full workflow is `.agents/skills/code-quality-review/SKILL.md`. Read it and its referenced checks when the review environment supports repository file access. Review-only unless fixes are requested.

- Prioritize correctness, security, compatibility and missing regression coverage. Trace callers and report a concrete trigger, impact, location and fix for bugs.
- Apply user instructions and active `.agents/review-overrides.md`, then documented contracts and verified repository conventions before default style preferences. Never suppress concrete correctness risks because similar code exists.
- Establish conventions from the base revision and neighbouring code; counts alone do not establish a contract. Judge names against the applicable API/framework contract before the skill's defaults.
- Evaluate SOLID, readability and simplicity by their concrete maintenance cost. A current boundary, invariant, lifecycle, operational need or second use can justify an abstraction or configuration option.
- Respect the project's compiler/runtime baseline, Spring proxy constraints, exception/logging contracts and test stack. Avoid formatter-enforced or taste-only comments.

For detailed CLI reviews, follow the skill's report template, severity/rule IDs and **Conventions applied** summary. Hosted bots keep their native severity filters and report format; use these rules to focus their supported review, without promising the complete CLI output.
<!-- code-quality-review-kit:end -->
