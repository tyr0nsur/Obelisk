#!/usr/bin/env python3
"""Tests for check_chat_reflection_benchmark.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import check_chat_reflection_benchmark as checker


VALID_OUTPUT = """
hook_like_disabled iterations=100 ns_avg=35 reader_calls_per_iter=0 allocations=0 allocations_per_iter=0 accepted=100
hook_like_enabled_non_chat iterations=100 ns_avg=33 reader_calls_per_iter=1 allocations=0 allocations_per_iter=0 accepted=100
hook_like_server_send_chat iterations=100 ns_avg=459 reader_calls_per_iter=54 allocations=300 allocations_per_iter=3 accepted=100
hook_like_server_send_chat_text iterations=100 ns_avg=904 reader_calls_per_iter=55 allocations=700 allocations_per_iter=7 accepted=100
"""


class CheckChatReflectionBenchmarkTests(unittest.TestCase):
    def test_accepts_valid_output(self) -> None:
        cases = checker.parse_output(VALID_OUTPUT)
        self.assertEqual(checker.check_cases(cases, checker.DEFAULT_LIMITS), [])

    def test_rejects_missing_case(self) -> None:
        cases = checker.parse_output("\n".join(VALID_OUTPUT.splitlines()[:-1]))
        errors = checker.check_cases(cases, checker.DEFAULT_LIMITS)
        self.assertIn("missing benchmark case(s): hook_like_server_send_chat_text", errors)

    def test_rejects_non_chat_allocation_regression(self) -> None:
        text = VALID_OUTPUT.replace(
            "hook_like_enabled_non_chat iterations=100 ns_avg=33 reader_calls_per_iter=1 allocations=0 allocations_per_iter=0",
            "hook_like_enabled_non_chat iterations=100 ns_avg=33 reader_calls_per_iter=1 allocations=100 allocations_per_iter=1",
        )
        errors = checker.check_cases(checker.parse_output(text), checker.DEFAULT_LIMITS)
        self.assertIn(
            "hook_like_enabled_non_chat: allocations_per_iter=1 exceeds limit 0",
            errors,
        )

    def test_rejects_partial_acceptance(self) -> None:
        text = VALID_OUTPUT.replace("accepted=100", "accepted=99", 1)
        errors = checker.check_cases(checker.parse_output(text), checker.DEFAULT_LIMITS)
        self.assertIn("hook_like_disabled: accepted=99 differs from iterations=100", errors)


if __name__ == "__main__":
    unittest.main()
