#!/usr/bin/env python3
"""Check inventory_policy_event_dispatcher_benchmark output against allocation gates."""

from __future__ import annotations

from dispatcher_benchmark_gate import DEFAULT_LIMITS, check_cases, parse_output, run_gate


def main() -> int:
    return run_gate(
        "Validate inventory_policy_event_dispatcher_benchmark output.",
        "inventory policy dispatcher benchmark gates passed",
    )


if __name__ == "__main__":
    raise SystemExit(main())
