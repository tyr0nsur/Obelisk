#!/usr/bin/env python3
"""Static guardrails for process-local owner-token timer safety."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TIMER_MANAGER = REPO_ROOT / "core" / "TimerManager.cpp"
PLUGIN_MANAGER = REPO_ROOT / "core" / "PluginManager.cpp"
OBELISK_API_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"


def extract_braced_body(text: str, match: re.Match[str]) -> str:
    start = text.find("{", match.end())
    if start == -1:
        raise AssertionError("matched function has no body")

    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:index]
    raise AssertionError("matched function body is not balanced")


def extract_function_body(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.S)
    if match is None:
        raise AssertionError(f"function pattern not found: {pattern}")
    return extract_braced_body(text, match)


class TimerManagerGuardrailTests(unittest.TestCase):
    def test_timer_manager_uses_process_lifetime_singletons(self) -> None:
        text = TIMER_MANAGER.read_text(encoding="utf-8")

        state_body = extract_function_body(text, r"TimerState& State\(\)")
        manager_body = extract_function_body(text, r"TimerManager& TimerManager::Get\(\)")

        self.assertIn("static auto* state = new TimerState();", state_body)
        self.assertIn("static auto* manager = new TimerManager();", manager_body)
        self.assertNotIn("static TimerState state", state_body)
        self.assertNotIn("static TimerManager manager", manager_body)

    def test_timer_ids_are_non_zero_and_not_reused_while_live(self) -> None:
        text = TIMER_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"uint64_t AllocateTimerIdLocked\(TimerState& state\)")

        self.assertIn("state.NextId++", body)
        self.assertIn("if (state.NextId == 0)", body)
        self.assertIn("state.NextId = 1", body)
        self.assertIn("id != 0", body)
        self.assertIn("state.Timers.find(id) == state.Timers.end()", body)

    def test_register_validates_inputs_before_scheduling(self) -> None:
        text = TIMER_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(
            text,
            r"uint64_t TimerManager::Register\(void\* owner,\s*uint64_t delayMs,\s*uint64_t intervalMs,"
            r"\s*bool repeating,\s*TimerCallback callback,\s*void\* userData\)",
        )

        validation_index = body.index("if (!owner || !callback || !IsSupportedDuration(delayMs)")
        scheduling_index = body.index("Clock::now() + std::chrono::milliseconds(delayMs)")
        self.assertLess(validation_index, scheduling_index)
        self.assertIn("(repeating && !IsSupportedDuration(intervalMs))", body)
        self.assertIn("(!repeating && intervalMs != 0)", body)
        self.assertIn("return 0", body[:scheduling_index])

    def test_owner_cleanup_waits_for_inflight_callbacks_except_same_owner_callback(self) -> None:
        text = TIMER_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"size_t TimerManager::UnregisterCallbacksForOwner\(void\* owner\)")

        self.assertIn("if (!owner)", body)
        self.assertIn("timer->Owner != owner", body)
        self.assertIn("timer->Cancelled = true", body)
        self.assertIn("if (t_CurrentTimerOwner == owner)", body)
        self.assertIn("return removed", body)
        self.assertIn("state.Cv.wait(lock", body)
        self.assertIn("item.second->Owner == owner && item.second->InFlight != 0", body)
        self.assertLess(body.index("if (t_CurrentTimerOwner == owner)"), body.index("state.Cv.wait(lock"))

    def test_plugin_timer_registration_validates_abi_inputs_before_register(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"uint64_t PluginRegisterTimerWithOwnerTokenHandle\(")

        register_index = body.index("TimerManager::Get().Register")
        for token in (
            "ValidateTimerCallback",
            "(flags & ~OBELISK_TIMER_FLAG_REPEATING) != 0",
            "delayMs == 0",
            "!TimerManager::IsSupportedDuration(delayMs)",
            "repeating && intervalMs == 0",
            "repeating && !TimerManager::IsSupportedDuration(intervalMs)",
            "!repeating && intervalMs != 0",
            "PluginOwnerHasCapabilityLocked(owner, OBELISK_API_CAPABILITY_TIMERS)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, body)
                self.assertLess(body.index(token), register_index)

    def test_plugin_owner_cleanup_includes_timer_callbacks(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)")

        self.assertIn('cleanupFamily("timer"', body)
        self.assertIn("TimerManager::Get().UnregisterCallbacksForOwner(owner)", body)

    def test_public_timer_abi_remains_owner_token_scoped(self) -> None:
        header = OBELISK_API_HEADER.read_text(encoding="utf-8")

        self.assertIn("OBELISK_API_CAPABILITY_TIMERS", header)
        self.assertIn("RegisterTimerWithOwnerTokenHandle", header)
        self.assertIn("UnregisterTimerWithOwnerToken", header)
        self.assertIn("plugin_owner_token", header)
        self.assertNotIn("RegisterTimer(", header)


if __name__ == "__main__":
    unittest.main()
