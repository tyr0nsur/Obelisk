#!/usr/bin/env python3
"""Static guardrails for raw ProcessEvent callback lifecycle safety."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EVENT_MANAGER = REPO_ROOT / "core" / "EventManager.cpp"
EVENT_MANAGER_HEADER = REPO_ROOT / "core" / "EventManager.h"


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


class EventManagerGuardrailTests(unittest.TestCase):
    def test_event_manager_uses_process_lifetime_singleton_state(self) -> None:
        text = EVENT_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"EventManager& EventManager::Get\(\)")

        self.assertIn("static auto* instance = new EventManager();", body)
        self.assertNotIn("static EventManager instance", body)

    def test_registration_ids_are_non_zero_and_not_reused_while_live(self) -> None:
        text = EVENT_MANAGER.read_text(encoding="utf-8")
        allocation_body = extract_function_body(text, r"uint64_t EventManager::AllocateRegistrationId\(\)")
        active_body = extract_function_body(text, r"bool EventManager::IsRegistrationActive\(.*?\)")

        self.assertIn("m_NextRegistrationId++", allocation_body)
        self.assertIn("if (m_NextRegistrationId == 0)", allocation_body)
        self.assertIn("m_NextRegistrationId = 1", allocation_body)
        self.assertIn("id == 0 || HasRegistrationId(id)", allocation_body)
        self.assertIn("registrationId != 0", active_body)
        self.assertIn("HasRegistrationId(registrationId)", active_body)

    def test_owner_cleanup_removes_all_raw_process_event_families_under_dispatch_lock(self) -> None:
        text = EVENT_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"size_t EventManager::UnregisterCallbacksForOwner\(void\* owner\)")

        self.assertLess(
            body.index("std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex)"),
            body.index("std::lock_guard<std::mutex> lock(m_Mutex)"),
        )
        for token in (
            "m_PreProcessEventCallbacks",
            "m_PostProcessEventCallbacks",
            "m_FilteredPreProcessEventCallbacks",
            "m_FilteredPostProcessEventCallbacks",
        ):
            with self.subTest(token=token):
                self.assertIn(token, body)
        self.assertNotIn("catch", body)
        self.assertNotRegex(body, r"\breturn\s+0\s*;\s*//")

    def test_dispatch_snapshots_ids_and_skips_removed_callbacks(self) -> None:
        text = EVENT_MANAGER.read_text(encoding="utf-8")
        header = EVENT_MANAGER_HEADER.read_text(encoding="utf-8")

        self.assertIn("uint64_t generation;", header)
        self.assertIn("uint64_t id;", header)

        for pattern, vector_name in (
            (r"bool EventManager::TriggerPreProcessEvent\(void\* caller, void\* function, void\* parms, bool\* setupFailed\)",
             "m_PreProcessEventCallbacks"),
            (r"bool EventManager::TriggerPreProcessEvent\(int32_t nameIndex, void\* caller, void\* function, void\* parms\)",
             "m_FilteredPreProcessEventCallbacks"),
            (r"void EventManager::TriggerPostProcessEvent\(void\* caller, void\* function, void\* parms, bool\* setupFailed\)",
             "m_PostProcessEventCallbacks"),
            (r"void EventManager::TriggerPostProcessEvent\(int32_t nameIndex, void\* caller, void\* function, void\* parms\)",
             "m_FilteredPostProcessEventCallbacks"),
        ):
            with self.subTest(vector_name=vector_name):
                body = extract_function_body(text, pattern)
                self.assertIn("std::vector<CallbackSnapshot> callbacks", body)
                self.assertIn(vector_name, body)
                self.assertIn("item.generation == snapshot.generation", body)
                self.assertIn("item.callback == snapshot.callback", body)
                self.assertIn("if (!isSnapshotActive(snapshot))", body)
                callback_invocation = re.search(r"\bsnapshot\.callback\s*\(", body)
                self.assertIsNotNone(callback_invocation)
                self.assertLess(body.index("if (!isSnapshotActive(snapshot))"), callback_invocation.start())

    def test_preprocess_blocking_requires_registration_and_live_gate(self) -> None:
        text = EVENT_MANAGER.read_text(encoding="utf-8")
        gate_body = extract_function_body(text, r"bool IsProcessEventBlockingAllowed\(\)")

        self.assertIn("g_ProcessEventBlockingCapabilityAdvertised", gate_body)
        self.assertIn("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING", gate_body)
        self.assertIn("allow-process-event-blocking", gate_body)

        for pattern in (
            r"bool EventManager::TriggerPreProcessEvent\(void\* caller, void\* function, void\* parms, bool\* setupFailed\)",
            r"bool EventManager::TriggerPreProcessEvent\(int32_t nameIndex, void\* caller, void\* function, void\* parms\)",
        ):
            with self.subTest(pattern=pattern):
                body = extract_function_body(text, pattern)
                self.assertIn("snapshot.allowProcessEventBlocking && IsProcessEventBlockingAllowed()", body)
                self.assertIn("return false", body)
                self.assertIn("continuing original event", body)

    def test_dispatch_catches_plugin_and_internal_exceptions(self) -> None:
        text = EVENT_MANAGER.read_text(encoding="utf-8")

        pre_body = extract_function_body(
            text,
            r"bool EventManager::TriggerPreProcessEvent\(void\* caller, void\* function, void\* parms, bool\* setupFailed\)",
        )
        self.assertIn("catch (const std::exception& e)", pre_body)
        self.assertIn("catch (...)", pre_body)
        self.assertIn("PreProcessEvent callback threw", pre_body)
        self.assertIn("dispatch failed internally; continuing original event", pre_body)
        self.assertRegex(pre_body, r"catch\s*\([^)]*\)\s*\{[\s\S]*?return true;")

        filtered_pre_body = extract_function_body(
            text,
            r"bool EventManager::TriggerPreProcessEvent\(int32_t nameIndex, void\* caller, void\* function, void\* parms\)",
        )
        self.assertIn("Filtered PreProcessEvent callback threw", filtered_pre_body)
        self.assertIn("dispatch failed internally; continuing original event", filtered_pre_body)
        self.assertRegex(filtered_pre_body, r"catch\s*\([^)]*\)\s*\{[\s\S]*?return true;")

        for pattern, callback_log, internal_log in (
            (
                r"void EventManager::TriggerPostProcessEvent\(void\* caller, void\* function, void\* parms, bool\* setupFailed\)",
                "PostProcessEvent callback threw",
                "PostProcessEvent dispatch failed internally",
            ),
            (
                r"void EventManager::TriggerPostProcessEvent\(int32_t nameIndex, void\* caller, void\* function, void\* parms\)",
                "Filtered PostProcessEvent callback threw",
                "Filtered PostProcessEvent dispatch failed internally",
            ),
        ):
            with self.subTest(pattern=pattern):
                body = extract_function_body(text, pattern)
                self.assertIn("catch (const std::exception& e)", body)
                self.assertIn("catch (...)", body)
                self.assertIn(callback_log, body)
                self.assertIn(internal_log, body)
                self.assertNotIn("throw;", body)


if __name__ == "__main__":
    unittest.main()
