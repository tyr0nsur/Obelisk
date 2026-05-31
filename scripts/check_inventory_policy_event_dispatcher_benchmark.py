#!/usr/bin/env python3
"""Check inventory_policy_event_dispatcher_benchmark output against allocation gates."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_CASES = {
    "invalid_event",
    "no_subscribers",
    "four_subscribers_stack_snapshot",
    "five_subscribers_heap_snapshot",
}

DEFAULT_LIMITS = {
    "invalid_event": {"allocations_per_iter": 0, "dispatched": 0},
    "no_subscribers": {"allocations_per_iter": 0, "dispatched": 0},
    "four_subscribers_stack_snapshot": {"allocations_per_iter": 0},
    "five_subscribers_heap_snapshot": {"allocations_per_iter": 1},
}

METRIC_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>[0-9]+)")
EXPECTED_METRICS = {"iterations", "ns_avg", "allocations", "allocations_per_iter", "dispatched"}


def parse_output(text: str) -> dict[str, dict[str, int]]:
    cases: dict[str, dict[str, int]] = {}
    parse_errors: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        name = parts[0]
        if name not in REQUIRED_CASES:
            parse_errors.append(f"line {line_number}: unexpected benchmark case {name!r}")
            continue
        if name in cases:
            parse_errors.append(f"line {line_number}: duplicate benchmark case {name!r}")
            continue

        metrics: dict[str, int] = {}
        for token in parts[1:]:
            match = METRIC_RE.fullmatch(token)
            if match is None:
                parse_errors.append(f"line {line_number}: malformed metric token {token!r}")
                continue
            key = match.group("key")
            if key not in EXPECTED_METRICS:
                parse_errors.append(f"line {line_number}: unexpected metric {key!r}")
                continue
            if key in metrics:
                parse_errors.append(f"line {line_number}: duplicate metric {key!r}")
                continue
            metrics[key] = int(match.group("value"))
        if not metrics:
            parse_errors.append(f"line {line_number}: missing benchmark metrics")
            continue
        cases[name] = metrics
    if parse_errors:
        raise ValueError("\n".join(parse_errors))
    return cases


def check_cases(cases: dict[str, dict[str, int]], limits: dict[str, dict[str, int]]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_CASES - cases.keys())
    if missing:
        errors.append("missing benchmark case(s): " + ", ".join(missing))

    for case_name, case_limits in limits.items():
        metrics = cases.get(case_name)
        if metrics is None:
            continue
        for metric in sorted(EXPECTED_METRICS - metrics.keys()):
            errors.append(f"{case_name}: missing metric {metric}")
        for metric, limit in case_limits.items():
            observed = metrics.get(metric)
            if observed is None:
                continue
            elif observed > limit:
                errors.append(f"{case_name}: {metric}={observed} exceeds limit {limit}")

        iterations = metrics.get("iterations")
        if iterations == 0:
            errors.append(f"{case_name}: iterations must be greater than zero")

    for case_name in {"four_subscribers_stack_snapshot", "five_subscribers_heap_snapshot"} & cases.keys():
        metrics = cases[case_name]
        iterations = metrics.get("iterations")
        dispatched = metrics.get("dispatched")
        expected_per_iter = 4 if case_name.startswith("four_") else 5
        if iterations is not None and dispatched is not None:
            expected = iterations * expected_per_iter
            if dispatched != expected:
                errors.append(f"{case_name}: dispatched={dispatched} differs from expected {expected}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate inventory_policy_event_dispatcher_benchmark output.")
    parser.add_argument("input", type=Path, help="Benchmark output file, or '-' for stdin.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = sys.stdin.read() if str(args.input) == "-" else args.input.read_text(encoding="utf-8")
    try:
        cases = parse_output(text)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    errors = check_cases(cases, DEFAULT_LIMITS)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("inventory policy dispatcher benchmark gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
