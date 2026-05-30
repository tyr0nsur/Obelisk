#!/usr/bin/env python3
"""Guardrails for fail-closed ProcessEvent hook removal."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class ProcessEventHookGuardrailTests(unittest.TestCase):
    def test_remove_preserves_trampoline_when_frames_do_not_drain(self) -> None:
        source = (REPO_ROOT / "hooks/ProcessEventHook.cpp").read_text(encoding="utf-8")
        remove_start = source.index("static bool RemoveAbsoluteHook")
        remove_end = source.index("static uint64_t GetTraceLimit", remove_start)
        remove_body = source[remove_start:remove_end]

        self.assertIn("WaitForActiveProcessEventFramesToDrain", remove_body)
        self.assertIn("hook state and trampoline preserved", remove_body)
        self.assertRegex(
            remove_body,
            r"if \(!drained \|\| s_ActiveProcessEventFrames\.load\(std::memory_order_acquire\) != 0\)\s*\{"
            r"[\s\S]*?return false;",
        )
        self.assertLess(
            remove_body.index('OBELISK_WARN("ProcessEvent hook removal deferred'),
            remove_body.index("hook = {};"),
        )

    def test_remove_allows_active_frames_to_resolve_original_while_draining(self) -> None:
        source = (REPO_ROOT / "hooks/ProcessEventHook.cpp").read_text(encoding="utf-8")
        remove_start = source.index("static bool RemoveAbsoluteHook")
        wait_index = source.index("WaitForActiveProcessEventFramesToDrain", remove_start)
        pre_wait = source[remove_start:wait_index]

        self.assertIn(
            "Let already-active frames keep resolving the\n"
            "            // trampoline while they drain",
            pre_wait,
        )
        self.assertIn("s_RemovingProcessEventHook.store(false, std::memory_order_release);", pre_wait)


if __name__ == "__main__":
    unittest.main()
