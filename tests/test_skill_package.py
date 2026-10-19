"""Check deployable resources and the semantic evaluator's acceptance boundaries."""
import json
from pathlib import Path
import re
import unittest

from check_review_results import evaluate


KIT = Path(__file__).resolve().parents[1]
SKILL = KIT / "repo/.agents/skills/code-quality-review"


class SkillPackageTests(unittest.TestCase):
    def test_local_skill_resources_are_available(self):
        for document in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]:
            text = document.read_text()
            links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
            resources = re.findall(r"`((?:references|scripts|assets)/[^`<>\s]+)`", text)
            for reference in links + resources:
                if "://" in reference or reference.startswith("#"):
                    continue
                with self.subTest(document=document.name, reference=reference):
                    self.assertTrue((document.parent / reference.split("#")[0]).is_file())

    def test_semantic_evaluator_rejects_missing_or_duplicate_cases(self):
        cases = [{"id": "valid", "expected": {"clean": True, "must_report_any": [], "must_not_report": []}}]
        result = {"id": "valid", "findings": []}
        self.assertTrue(evaluate(cases, []))
        self.assertEqual(evaluate(cases, [result]), [])
        self.assertTrue(evaluate(cases, [result, result]))

    def test_semantic_evaluator_detects_both_misses_and_false_positives(self):
        cases = json.loads((KIT / "tests/fixtures/review_cases.json").read_text())["cases"]
        empty_results = [{"id": case["id"], "findings": []} for case in cases]
        self.assertTrue(evaluate(cases, empty_results))  # Cannot pass by approving everything.
        valid_case = next(case for case in cases if case["id"] == "spring_proxy_exception")
        bad_advice = [{"id": valid_case["id"], "findings": [{"rule": "JAVA-API-FINAL"}]}]
        self.assertTrue(evaluate([valid_case], bad_advice))
        self.assertEqual(evaluate([valid_case], [{"id": valid_case["id"], "findings": []}]), [])


if __name__ == "__main__":
    unittest.main()
