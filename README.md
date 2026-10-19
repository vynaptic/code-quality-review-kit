# code-quality-review-kit

A shared [Agent Skills](https://agentskills.io/specification) workflow for **Claude Code, Codex, Devin CLI and Factory Droid**. It reviews correctness, security, repository conventions, naming, design, readability and Java/Spring quality. Small adapters also provide guidance to hosted PR reviewers; each bot keeps its native filters and output format.

The reviewer learns contracts and conventions before applying defaults. Findings need a location, evidence, concrete cost and fix. Detailed CLI reports include rule IDs, severity and **Conventions applied**.

- **Correctness first:** trace callers, construct a failing input or interleaving, and check relevant tests.
- **Contracts before defaults:** documented APIs, framework requirements and verified repository conventions govern naming and structure. Existing repetition never excuses a bug.
- **Practical design:** assess SOLID, simplicity and readability by current costs and benefits. Boundaries, invariants, lifecycle and operational needs can justify abstraction.
- **Java/Spring checks:** respect the compiler/runtime baseline, proxy constraints, exception and logging contracts, transactions, persistence and test stack.
- **Advisory scanners:** stdlib Python helpers produce a convention inventory and naming candidates. Counts are evidence to inspect, never automatic exemptions or confirmed findings.

## Install

From this kit's checkout, with Python 3:

```bash
python3 scripts/install.py "/path/to/your repository"
```

The installer preserves existing guidance and overrides, appends its marked guidance once, and refuses conflicting skill assets before changing files. Review the resulting diff before committing. [Install details, updates and personal setup](INSTALL.md).

| Interactive tool | Discovery | Invoke |
| --- | --- | --- |
| Claude Code | `.claude/skills/` wrapper | `/code-quality-review` |
| Codex CLI / IDE | `.agents/skills/` | `$code-quality-review` |
| Devin CLI | `.agents/skills/` | `/code-quality-review` |
| Factory Droid | `.agents/skills/` compatibility path | `/code-quality-review` |

Hosted adapters use `AGENTS.md` for Codex GitHub review, `REVIEW.md` for Devin Review, and `.factory/skills/review-guidelines/SKILL.md` for Factory code review. They do not guarantee the full CLI checklist or report; see [documented platform limits](INSTALL.md#hosted-pr-review).

## Verify

Run from **this kit's checkout**, not the installed target:

```bash
python3 -m unittest discover -s tests
bash examples/java-sample/try.sh
KEEP=1 bash examples/java-sample/try.sh
```

The fixture's [README](examples/java-sample/README.md) explains how to review the retained sample and compare it with [EXPECTED.md](examples/java-sample/EXPECTED.md). This exercises the package and reviewer workflow; it does not prove every vendor's discovery or hosted bot behavior.

## Package

```text
repo/.agents/skills/code-quality-review/   canonical workflow, references, assets and scanners
repo/.agents/review-overrides.md           optional repository exceptions
repo/.claude/skills/code-quality-review/   Claude entrypoint
repo/.factory/skills/review-guidelines/    Factory code-review adapter
repo/AGENTS.md repo/CLAUDE.md repo/REVIEW.md
scripts/install.py                       preserving repository installer
examples/java-sample/                    review fixture
```

[MIT license](LICENSE).
