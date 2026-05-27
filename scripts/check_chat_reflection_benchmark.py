#!/usr/bin/env python3
"""Check chat_reflection_benchmark output against local regression gates."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_CASES = {
    "server_send_chat_match",
    "server_send_chat_decode_utf32",
    "hook_like_disabled",
    "hook_like_enabled_non_chat",
    "hook_like_chat_limit_zero",
    "hook_like_server_send_chat",
    "hook_like_server_send_chat_text",
}

DEFAULT_LIMITS = {
    "server_send_chat_match": {"allocations_per_iter": 0, "reader_calls_per_iter": 60},
    "server_send_chat_decode_utf32": {"allocations_per_iter": 1, "reader_calls_per_iter": 2},
    "hook_like_disabled": {"allocations_per_iter": 0, "reader_calls_per_iter": 0},
    "hook_like_enabled_non_chat": {"allocations_per_iter": 0, "reader_calls_per_iter": 1},
    "hook_like_chat_limit_zero": {"allocations_per_iter": 0, "reader_calls_per_iter": 1},
    "hook_like_server_send_chat": {"allocations_per_iter": 0, "reader_calls_per_iter": 60},
    "hook_like_server_send_chat_text": {"allocations_per_iter": 2, "reader_calls_per_iter": 65},
}

METRIC_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>[0-9]+)")


def parse_output(text: str) -> dict[str, dict[str, int]]:
    cases: dict[str, dict[str, int]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if not parts:
            continue
        name = parts[0]
        metrics = {match.group("key"): int(match.group("value")) for match in METRIC_RE.finditer(line)}
        if metrics:
            cases[name] = metrics
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
        for metric, limit in case_limits.items():
            observed = metrics.get(metric)
            if observed is None:
                errors.append(f"{case_name}: missing metric {metric}")
            elif observed > limit:
                errors.append(f"{case_name}: {metric}={observed} exceeds limit {limit}")

    for case_name in REQUIRED_CASES & cases.keys():
        accepted = cases[case_name].get("accepted")
        iterations = cases[case_name].get("iterations")
        if accepted is not None and iterations is not None and accepted != iterations:
            errors.append(f"{case_name}: accepted={accepted} differs from iterations={iterations}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate chat_reflection_benchmark output.")
    parser.add_argument("input", type=Path, help="Benchmark output file, or '-' for stdin.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = sys.stdin.read() if str(args.input) == "-" else args.input.read_text(encoding="utf-8")
    cases = parse_output(text)
    errors = check_cases(cases, DEFAULT_LIMITS)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("chat reflection benchmark gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
