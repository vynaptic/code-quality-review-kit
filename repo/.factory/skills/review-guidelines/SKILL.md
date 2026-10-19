---
name: review-guidelines
description: Repository guidance for Factory automated code review. For a detailed interactive review, invoke code-quality-review instead.
---

Follow the repository's `REVIEW.md`, active `.agents/review-overrides.md` and, when repository file access permits, `.agents/skills/code-quality-review/SKILL.md`.

Prioritize concrete correctness, security, compatibility and test failures. Cite the trigger, location, evidence and fix. Judge naming and design against actual API/framework contracts and verified repository conventions; scanner counts alone are not proof. Current boundary, invariant, lifecycle or operational needs can justify abstractions. Respect the Java baseline and Spring proxy requirements.

Keep Factory's native review format and filters. This entrypoint configures code review; Factory's separate security review uses `security-review-guidelines` and is not configured by this kit. Do not edit code during a review unless fixes are requested.
