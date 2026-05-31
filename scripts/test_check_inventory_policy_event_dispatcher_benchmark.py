#!/usr/bin/env python3
"""Tests for check_inventory_policy_event_dispatcher_benchmark.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import check_inventory_policy_event_dispatcher_benchmark as checker


VALID_OUTPUT = """
invalid_event iterations=10000 ns_avg=2 allocations=0 allocations_per_iter=0 dispatched=0
no_subscribers iterations=10000 ns_avg=5 allocations=0 allocations_per_iter=0 dispatched=0
four_subscribers_stack_snapshot iterations=10000 ns_avg=100 allocations=0 allocations_per_iter=0 dispatched=40000
five_subscribers_heap_snapshot iterations=10000 ns_avg=150 allocations=10000 allocations_per_iter=1 dispatched=50000
"""


class CheckInventoryPolicyEventDispatcherBenchmarkTests(unittest.TestCase):
    def test_accepts_valid_output(self) -> None:
        cases = checker.parse_output(VALID_OUTPUT)
        self.assertEqual(checker.check_cases(cases, checker.DEFAULT_LIMITS), [])

    def test_rejects_missing_case(self) -> None:
        cases = checker.parse_output("\n".join(VALID_OUTPUT.splitlines()[:-1]))
        errors = checker.check_cases(cases, checker.DEFAULT_LIMITS)
        self.assertIn("missing benchmark case(s): five_subscribers_heap_snapshot", errors)

    def test_rejects_stack_snapshot_allocation_regression(self) -> None:
        text = VALID_OUTPUT.replace(
            "four_subscribers_stack_snapshot iterations=10000 ns_avg=100 allocations=0 allocations_per_iter=0",
            "four_subscribers_stack_snapshot iterations=10000 ns_avg=100 allocations=10000 allocations_per_iter=1",
        )
        errors = checker.check_cases(checker.parse_output(text), checker.DEFAULT_LIMITS)
        self.assertIn(
            "four_subscribers_stack_snapshot: allocations_per_iter=1 exceeds limit 0",
            errors,
        )

    def test_rejects_no_subscriber_allocation_regression(self) -> None:
        text = VALID_OUTPUT.replace(
            "no_subscribers iterations=10000 ns_avg=5 allocations=0 allocations_per_iter=0",
            "no_subscribers iterations=10000 ns_avg=5 allocations=10000 allocations_per_iter=1",
        )
        errors = checker.check_cases(checker.parse_output(text), checker.DEFAULT_LIMITS)
        self.assertIn("no_subscribers: allocations_per_iter=1 exceeds limit 0", errors)

    def test_rejects_wrong_dispatch_count(self) -> None:
        text = VALID_OUTPUT.replace("dispatched=40000", "dispatched=39999")
        errors = checker.check_cases(checker.parse_output(text), checker.DEFAULT_LIMITS)
        self.assertIn(
            "four_subscribers_stack_snapshot: dispatched=39999 differs from expected 40000",
            errors,
        )

    def test_rejects_malformed_metric_token(self) -> None:
        text = VALID_OUTPUT.replace("ns_avg=100", "ns_avg=100ms")
        with self.assertRaisesRegex(ValueError, "malformed metric token 'ns_avg=100ms'"):
            checker.parse_output(text)

    def test_rejects_unexpected_case(self) -> None:
        text = (
            VALID_OUTPUT
            + "summary iterations=10000 ns_avg=1 allocations=0 allocations_per_iter=0 dispatched=0\n"
        )
        with self.assertRaisesRegex(ValueError, "unexpected benchmark case 'summary'"):
            checker.parse_output(text)

    def test_rejects_unexpected_metric(self) -> None:
        text = VALID_OUTPUT.replace(
            "four_subscribers_stack_snapshot iterations=10000",
            "four_subscribers_stack_snapshot extra=1 iterations=10000",
        )
        with self.assertRaisesRegex(ValueError, "unexpected metric 'extra'"):
            checker.parse_output(text)

    def test_rejects_missing_dispatch_metric(self) -> None:
        text = VALID_OUTPUT.replace(" dispatched=40000", "")
        errors = checker.check_cases(checker.parse_output(text), checker.DEFAULT_LIMITS)
        self.assertIn("four_subscribers_stack_snapshot: missing metric dispatched", errors)

    def test_rejects_zero_iterations(self) -> None:
        text = VALID_OUTPUT.replace("invalid_event iterations=10000", "invalid_event iterations=0")
        errors = checker.check_cases(checker.parse_output(text), checker.DEFAULT_LIMITS)
        self.assertIn("invalid_event: iterations must be greater than zero", errors)


if __name__ == "__main__":
    unittest.main()
