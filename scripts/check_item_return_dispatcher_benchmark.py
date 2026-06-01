#!/usr/bin/env python3
"""Check item_return_event_dispatcher_benchmark output against local regression gates."""

from __future__ import annotations

from dispatcher_benchmark_gate import DEFAULT_LIMITS, check_cases, parse_output, run_gate


def main() -> int:
    return run_gate(
        "Validate item_return_event_dispatcher_benchmark output.",
        "item return dispatcher benchmark gates passed",
    )


if __name__ == "__main__":
    raise SystemExit(main())
