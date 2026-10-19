#!/usr/bin/env python3
"""Score independent agent results against semantic cases, not skill wording."""
import argparse
import json
from pathlib import Path


def evaluate(cases, results):
    expected = {case["id"]: case["expected"] for case in cases}
    seen = set()
    failures = []
    for result in results:
        case_id = result["id"]
        if case_id in seen or case_id not in expected:
            failures.append(f"unexpected or duplicate case: {case_id}")
            continue
        seen.add(case_id)
        rules = {finding["rule"] for finding in result["findings"]}
        contract = expected[case_id]
        if contract["clean"] and rules:
            failures.append(f"{case_id}: false positives {sorted(rules)}")
        for alternatives in contract["must_report_any"]:
            if rules.isdisjoint(alternatives):
                failures.append(f"{case_id}: missed violation; expected one of {alternatives}")
        forbidden = rules.intersection(contract["must_not_report"])
        if forbidden:
            failures.append(f"{case_id}: forbidden findings {sorted(forbidden)}")
    failures.extend(f"missing case: {case_id}" for case_id in sorted(expected.keys() - seen))
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="JSON array of {id, findings: [{rule, reason}]} from an independent reviewer")
    args = parser.parse_args()
    cases = json.loads((Path(__file__).parent / "fixtures/review_cases.json").read_text())["cases"]
    try:
        failures = evaluate(cases, json.loads(args.results.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(f"invalid review results: {exc}")
    for failure in failures:
        print(f"FAIL: {failure}")
    print(f"{len(cases)} cases; {len(failures)} failures")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
