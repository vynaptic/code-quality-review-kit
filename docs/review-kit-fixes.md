# Review kit fixes

Objective: resolve the reviewed scanner, guidance, installation and fixture defects without adding a new framework.

Decisions:
- Keep one portable skill and thin tool adapters; distinguish interactive reviews from hosted bot filters.
- Profile the exact review base. Naming counts are advisory; they never suppress candidates automatically.
- Repo/API contracts determine naming semantics. Framework requirements and current operational needs are valid exceptions to defaults.
- Install without overwriting user guidance or overrides; reject conflicting assets before writing.
- Use stdlib `unittest` with real temporary Git repositories, a buildable Java fixture and independent skill scenarios.

Completed:
- Fixed both scanners; regression coverage in `tests/test_scan_names.py` and `tests/test_scan_conventions.py`.
- Added `scripts/install.py`; updated `INSTALL.md`, `README.md`, repository guidance and tool adapters.
- Added the conventions reference and calibrated canonical naming, design, Java and reporting guidance.
- Repaired the Java fixture/build, added assertions and isolated disposable Git configuration. Removed unsupported blockers from its expected review.
- Added semantic cases and result checking under `tests/`; independent final review findings were fixed and rechecked.

Verification (2026-10-19):

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -v` | 44 passed; real temporary repositories, installer conflicts/preservation, sample assertions and external Git configuration |
| Java sample `mvn validate test` with JDK 17 | Build passed; 4 tests, no failures/errors/skips |
| Independent skill evaluation | 12/12 cases passed; reasons and proposed fixes inspected |
| Independent no-skill control | 12/12 passed; no measured improvement claim |
| Package validation | Resource links and canonical/Factory skill validation passed; Claude frontmatter checked against its supported fields |
| Final diff | Independent review resolved; `git diff --check` passed |

Remaining rollout check: run the installed skill on each intended vendor surface. Local checks do not prove four-vendor discovery or hosted bot output/filter behavior. See `tests/README.md` and `INSTALL.md`.
