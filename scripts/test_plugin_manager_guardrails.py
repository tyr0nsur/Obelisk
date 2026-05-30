#!/usr/bin/env python3
"""Static guardrails for PluginManager cleanup safety."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANAGER = REPO_ROOT / "core" / "PluginManager.cpp"


class PluginManagerGuardrailTests(unittest.TestCase):
    def test_scoped_cleanup_guard_is_noexcept_and_catches(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        match = re.search(
            r"template <typename Fn>\s+class NoThrowScopeExit(?P<body>.*?)"
            r"template <typename Fn>\s+NoThrowScopeExit<Fn> MakeScopeExit",
            text,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group("body")

        self.assertRegex(body, r"~NoThrowScopeExit\(\)\s+noexcept")
        self.assertIn("try", body)
        self.assertIn("catch (const std::exception& e)", body)
        self.assertIn("catch (...)", body)
        self.assertIn("SafeLogErrorNoThrow", body)
        self.assertNotIn("OBELISK_ERROR", body)

    def test_no_throw_logging_helper_never_uses_logging_macros(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        match = re.search(
            r"void SafeLogErrorNoThrow\(.*?\)\s+noexcept(?P<body>.*?)"
            r"template <typename Fn>\s+class NoThrowScopeExit",
            text,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("Logger::IsInitialized()", body)
        self.assertIn("catch (...)", body)
        self.assertNotIn("OBELISK_ERROR", body)

    def test_make_scope_exit_uses_no_throw_guard(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            re.compile(
                r"template <typename Fn>\s+NoThrowScopeExit<Fn> MakeScopeExit\(Fn fn\)\s*"
                r"\{\s*return NoThrowScopeExit<Fn>\(std::move\(fn\)\);\s*\}",
                re.S,
            ),
        )
        self.assertNotIn("class ScopeExit", text)
        self.assertNotIn("~ScopeExit()", text)

    def test_init_failure_cleanup_keeps_each_cleanup_step_isolated(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        match = re.search(
            r"auto initCleanup = MakeScopeExit\(\[\&\]\(\) \{(?P<body>.*?)\n\s*\}\);",
            text,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group("body")

        for token in (
            "MarkPluginOwnerUnloading(pluginOwner)",
            "CallPluginShutdown(pluginName, shutdownFunc)",
            "RemoveInitializingPluginOwner(pluginOwner)",
            "RemovePluginOwnerToken(pluginOwnerToken)",
            'UnregisterPluginCallbacks(pluginName, pluginOwner, "after init failure and before dlclose")',
            "ClearPluginOwnerUnloading(pluginOwner)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, body)
        self.assertGreaterEqual(body.count("try"), 6)
        self.assertGreaterEqual(body.count("SafeLogErrorNoThrow"), 6)

    def test_unload_all_wraps_shutdown_and_library_close(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        match = re.search(r"void PluginManager::UnloadAll\(\)\s*\{(?P<body>.*?)\n\s*\}\n\}", text, re.S)
        self.assertIsNotNone(match)
        body = match.group("body")

        for token in (
            "CallPluginShutdown(plugin.name, plugin.shutdown)",
            "SafeCloseLibrary(*m_Loader, plugin.handle, plugin.name)",
        ):
            with self.subTest(token=token):
                token_index = body.find(token)
                self.assertNotEqual(token_index, -1)
                preceding = body[max(0, token_index - 120):token_index]
                following = body[token_index:token_index + 260]
                self.assertIn("try", preceding)
                self.assertIn("catch", following)
                self.assertIn("SafeLogErrorNoThrow", following)


if __name__ == "__main__":
    unittest.main()
