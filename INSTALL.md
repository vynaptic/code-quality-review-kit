# Code Quality Review kit — install guide (v2.0)

One review standard, packaged as an open **Agent Skills** (`SKILL.md`) skill plus thin per-tool entry points, so the same files work in **Devin**, **Factory Droid**, **Claude Code** and **Codex** — interactive CLIs and PR bots alike.

What the review enforces, in priority order: bugs and security → the repository's **own established conventions** (packaging, modules, exceptions, logging, naming vocabulary, DI, tests…) → naming (methods = action verb + noun; types named by stereotype and context; verb contracts that must not lie) → SOLID and modern design principles and patterns → a **simplicity guard** against over-engineering and unwanted abstraction → a **Spring Framework / Apache-grade Java quality bar** (exceptions, logging, API design, nullability, immutability, concurrency, Javadoc) → tests. Every finding has a rule ID, a severity, evidence and a concrete fix.

```
repo/                                              ← copy the CONTENTS of this folder into your repository root
├── .agents/
│   ├── skills/code-quality-review/                ← THE skill (Codex, Devin and Factory Droid all discover this path)
│   │   ├── SKILL.md                               ← workflow, precedence, passes, severities, verdict rules
│   │   ├── references/
│   │   │   ├── repo-conventions.md                ← precedence + Convention Profile procedure + CONV-* rules
│   │   │   ├── correctness-checklist.md           ← bugs, security, performance, compatibility, tests
│   │   │   ├── naming-conventions.md              ← verb+noun methods, verb contracts, stereotype type names, framework idioms
│   │   │   ├── design-principles.md               ← SOLID, DRY/KISS/YAGNI, deep modules, LoD, CQS, layering, DDD, robustness
│   │   │   ├── design-patterns.md                 ← force→pattern table, framework patterns, misuse, code smells
│   │   │   ├── simplicity-and-readability.md      ← OVER-* over-engineering guard, READ-* readability, the "Spring test"
│   │   │   ├── java-quality-bar.md                ← JAVA-* Spring/Apache-grade rules (API, exceptions, logging, Spring, Javadoc, Kotlin)
│   │   │   └── report-template.md                 ← exact output format (with mandatory "Conventions applied")
│   │   ├── assets/naming-rules.json               ← verb lexicon, banned words, framework idioms, repo-consistency thresholds
│   │   └── scripts/
│   │       ├── scan_conventions.py                ← Convention Profile draft for a repository (Python 3.8+, stdlib)
│   │       └── scan_names.py                      ← naming pre-scan of a diff, downgrades what the repo already does
│   └── review-overrides.md                        ← optional per-repo exceptions (template; nothing active as shipped)
├── .claude/skills/code-quality-review/SKILL.md    ← Claude Code entry point (points at the .agents skill; no duplicated rules)
├── .factory/skills/review-guidelines/SKILL.md     ← injected by Factory's automated PR review (droid-action)
├── AGENTS.md                                      ← Codex ("## Code Review Rules" is what Codex code review reads); also read by Devin and Droid
├── CLAUDE.md                                      ← Claude Code project notes (also read by Devin Review)
└── REVIEW.md                                      ← Devin Review (PR bot); the short version of the standard
examples/java-sample/                              ← fixture to verify a tool picked the skill up (see its README.md)
```

## 1. Install in a repository (recommended — all four tools, whole team)

```bash
cp -R repo/. /path/to/your-repo/
cd /path/to/your-repo
git add .agents .claude .factory AGENTS.md CLAUDE.md REVIEW.md
git commit -m "Add code-quality-review skill and review guidelines"
```

If your repository already has `AGENTS.md` or `CLAUDE.md`, append the sections from the kit's files instead of overwriting (`AGENTS.md` needs the `## Skills` and `## Code Review Rules` sections; `CLAUDE.md` needs `## Code review`).

| Tool | Where it finds the standard (verified against each vendor's docs, Oct 2026) | How to run a review |
| --- | --- | --- |
| **Codex CLI / IDE** | `.agents/skills/code-quality-review/SKILL.md` — Codex scans `.agents/skills` from the working directory up to the repo root; implicit selection by description, explicit with `$` | `$code-quality-review review this branch against main` (or just ask for a review) |
| **Codex code review (GitHub)** | Root `AGENTS.md`, section `## Code Review Rules` (nested `AGENTS.md` files apply to their subtree) | Comment `@codex review` on the PR, or turn on *Automatic review* in Codex settings |
| **Claude Code** | `.claude/skills/code-quality-review/SKILL.md` (a pointer to the `.agents` skill) + `CLAUDE.md`; auto-selected or `/code-quality-review` | `/code-quality-review` or "review my branch" |
| **Devin (cloud sessions)** | `.agents/skills/<name>/SKILL.md` of connected/cloned repos | "use the code-quality-review skill to review this branch" |
| **Devin CLI** | `.agents/skills/` (also `.devin/skills/`) | `/code-quality-review` |
| **Devin Review (PR bot)** | `**/REVIEW.md`, `**/AGENTS.md`, `**/CLAUDE.md`, `CONTRIBUTING.md` | Automatic on enrolled repos, or comment `/devin review` |
| **Factory Droid CLI** | `.factory/skills/` and the compatibility path `.agents/skills/**/SKILL.md`; also `AGENTS.md` | `/code-quality-review` or "review my branch" (Droid auto-selects matching skills) |
| **Factory automated review (droid-action)** | `.factory/skills/review-guidelines/SKILL.md` (same text as `REVIEW.md`) | `@droid review` on the PR, or the review workflow generated by `/install-code-review` |

Why the skill lives in `.agents/skills/` and the others are pointers: Codex, Devin and Droid all read that path natively; Claude Code reads only `.claude/skills/`, so its `SKILL.md` tells it to load the `.agents` one. One copy of the rules, no drift. (A symlink `.claude/skills/code-quality-review → ../../.agents/skills/code-quality-review` also works on macOS/Linux if you prefer; the pointer file is used because it survives Windows checkouts and zip downloads.)

## 2. Install for yourself only (CLIs, all projects on your machine)

```bash
mkdir -p ~/.agents/skills ~/.claude/skills
cp -R repo/.agents/skills/code-quality-review ~/.agents/skills/          # Codex, Devin CLI, Factory Droid
cp -R repo/.claude/skills/code-quality-review ~/.claude/skills/          # Claude Code (pointer)
```
For the personal Claude Code copy, edit `~/.claude/skills/code-quality-review/SKILL.md` and replace `.agents/skills/code-quality-review/` with `~/.agents/skills/code-quality-review/` (the pointer assumes a repository install). Devin **cloud** sessions and all PR bots only read repository files, so use option 1 for those.

## 3. Verify the install (two minutes)

```bash
examples/java-sample/try.sh          # builds a throwaway repo, prints the Convention Profile and the naming pre-scan
KEEP=1 examples/java-sample/try.sh   # keep it, then open it in any tool and ask for a review
```
Compare the tool's report with `examples/java-sample/EXPECTED.md`. A correctly loaded skill produces a **Conventions applied** section, rule IDs on every finding, and findings such as `CONV-EXC` (raw `RuntimeException` bypassing `BillingException`), `CONV-LOG` (JUL + string concatenation in an SLF4J repo), `NAME-M2` (`getRefund` doing HTTP), `OVER-INTERFACE` (`RefundPolicy` with one implementation) and `BUG-MONEY` (`double` amounts).

## 4. Customise

- **Repo exceptions and clarifications:** `.agents/review-overrides.md` — tell the reviewer what the profiler might misread (your logging facade, exception root, packaging rule, grandfathered `*Impl` classes, mandatory service layer…), add severity bumps or out-of-scope paths. Only uncommented lines are active. Overrides beat the skill's defaults *and* inferred conventions; they cannot waive BLOCKER-level bugs or security findings.
- **Domain verbs** (`settle`, `onboard`, `chargeback`): add to `assets/naming-rules.json → approved_verbs`.
- **Repo-consistency threshold:** `assets/naming-rules.json → repo_consistency.min_occurrences` (default 3) and the suffix/verb lists the scanner checks against the base tree.
- **Keep the three guideline copies in sync:** `REVIEW.md`, `AGENTS.md` (`## Code Review Rules`) and `.factory/skills/review-guidelines/SKILL.md` carry the same short text on purpose (each bot reads a different file). Edit `REVIEW.md`, then paste the body into the other two.
- **Language scope:** Java and Kotlin get the full bar (`java-quality-bar.md`). Other languages get everything else (conventions, naming, design, simplicity, correctness) plus the exception/logging/API sections by analogy.

## 5. The scanners on their own

```bash
python3 .agents/skills/code-quality-review/scripts/scan_conventions.py                  # Convention Profile of the repo (markdown)
python3 .agents/skills/code-quality-review/scripts/scan_conventions.py --root services/billing --format json

python3 .agents/skills/code-quality-review/scripts/scan_names.py                        # branch vs base (+ uncommitted + untracked)
python3 .agents/skills/code-quality-review/scripts/scan_names.py --staged
python3 .agents/skills/code-quality-review/scripts/scan_names.py --files src/Foo.java
python3 .agents/skills/code-quality-review/scripts/scan_names.py --min-confidence medium --format json
python3 .agents/skills/code-quality-review/scripts/scan_names.py --ignore-repo-conventions  # raw defaults, no downgrade
```
`scan_names.py` reports *candidates* (high/medium/low) for Java, Kotlin, C#, TypeScript/JavaScript, Python, Go, Rust and Swift, and downgrades to `low` anything the base tree already does ≥3 times (`*Impl`, `I*` interfaces, `check*` methods…), printing which conventions it detected. The agent confirms or drops each candidate during the review.

### Optional CI gate (GitHub Actions)
```yaml
- uses: actions/checkout@v5
  with: { fetch-depth: 0 }
- run: python3 .agents/skills/code-quality-review/scripts/scan_names.py --base origin/${{ github.base_ref }} --min-confidence high --fail-on high
```
Start with `--fail-on high` (casing, `*Helper`/`*Util`, C# interface prefix, lying `get…`/`is…`); tighten later. Repo-consistency downgrades apply in CI too, so an established convention never fails the gate.

## What changed in 2.0
- **Repository conventions first:** a mandatory Convention Profile (`scan_conventions.py` + neighbouring files) and `CONV-*` rules; an explicit precedence chain (user > overrides > documented conventions > observed conventions > defaults); correctness never yields.
- **Simplicity guard:** `OVER-*` rules that require naming the second case or boundary for every new abstraction; `READ-*` readability rules; deep-vs-shallow modules; the "would Spring/Apache maintainers merge this?" calibration.
- **Java quality bar:** `JAVA-*` rules distilled from Spring Framework / Apache practice and Effective Java — API design, exceptions, logging, nullability/`Optional`, collections/streams, concurrency, Spring specifics, Javadoc, style, framework naming idioms, Kotlin addendum.
- **Naming nuances:** `Default*`/`Simple*`/`Abstract*`/`*Support`/`*Template` idioms; single-subject static `*Utils` and resource-lifecycle `*Manager` allowed; `do*` template workers; `*Impl` and read verbs yield to the repo.
- **Scanner:** repo-consistency downgrades (base-tree counts), `do*` idiom, Spring verbs in the lexicon.
- **Four tools:** Claude Code pointer skill + `CLAUDE.md`; Codex `AGENTS.md` with `## Code Review Rules`; verified discovery paths for all four.
- **Sample fixture** with expected findings to validate any install.

## Sources (vendor docs used for the paths above)
- Codex skills: https://developers.openai.com/codex/skills · Codex code review on GitHub: https://developers.openai.com/codex/integrations/github
- Claude Code skills: https://code.claude.com/docs/en/skills
- Devin CLI skills: https://docs.devin.ai/cli/extensibility/skills/overview · Devin Review: https://docs.devin.ai/work-with-devin/devin-review
- Factory Droid skills: https://docs.factory.ai/cli/configuration/skills · Factory automated code review: https://docs.factory.ai/software-factory/code-review-ci
