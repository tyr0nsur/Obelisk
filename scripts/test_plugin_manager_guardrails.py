#!/usr/bin/env python3
"""Static guardrails for PluginManager cleanup safety."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANAGER = REPO_ROOT / "core" / "PluginManager.cpp"


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
        body = extract_function_body(
            text,
            r"void SafeLogErrorNoThrow\(const char\* message, const char\* detail\)\s+noexcept",
        )
        self.assertIn("Logger::IsInitialized()", body)
        self.assertIn("catch (...)", body)
        self.assertNotIn("OBELISK_ERROR", body)

    def test_plugin_log_api_uses_no_throw_logging(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        for function_name, helper_name, forbidden_macro in (
            ("PluginLogInfo", "SafeLogInfoNoThrow", "OBELISK_INFO"),
            ("PluginLogWarn", "SafeLogWarnNoThrow", "OBELISK_WARN"),
            ("PluginLogError", "SafeLogErrorNoThrow", "OBELISK_ERROR"),
        ):
            with self.subTest(function_name=function_name):
                body = extract_function_body(
                    text,
                    rf"void {function_name}\(const char\* message\)",
                )
                self.assertIn(helper_name, body)
                self.assertNotIn(forbidden_macro, body)

    def test_shutdown_and_library_close_use_no_throw_logging(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        for function_name in ("CallPluginShutdown", "SafeCloseLibrary"):
            with self.subTest(function_name=function_name):
                body = extract_function_body(
                    text,
                    rf"void {function_name}\(.*?\)",
                )
                self.assertIn("SafeLog", body)
                self.assertNotIn("OBELISK_INFO", body)
                self.assertNotIn("OBELISK_WARN", body)
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
            r"auto initCleanup = MakeScopeExit\(\[\&\]\(\)",
            text,
        )
        self.assertIsNotNone(match)
        body = extract_braced_body(text, match)

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
                following = body[token_index:token_index + 420]
                self.assertIn("try", preceding)
                self.assertIn("catch", following)
                self.assertIn("SafeLogErrorNoThrow", following)

    def test_unregister_plugin_callbacks_is_per_family_and_cleans_timers(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(
            text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )

        self.assertIn("cleanupFamily", body)
        self.assertIn("TimerManager::Get().UnregisterCallbacksForOwner(owner)", body)
        self.assertIn("EventManager::Get().UnregisterCallbacksForOwner(owner)", body)
        self.assertIn("SafeLogErrorNoThrow", body)
        self.assertNotIn("OBELISK_ERROR", body)
        self.assertGreaterEqual(body.count("cleanupFamily("), 5)

    def test_plugin_boundary_catches_use_no_throw_logging(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        for function_name in ("InvokeGameplayPolicyEventCallback", "InvokeChatMessageEventCallback"):
            with self.subTest(function_name=function_name):
                body = extract_function_body(text, rf"void {function_name}\(.*?\)")
                self.assertIn("SafeLogErrorNoThrow", body)
                self.assertNotIn("OBELISK_ERROR", body)

        extern_match = re.search(r"// C-API Wrappers for Plugins\s+extern \"C\" \{", text)
        self.assertIsNotNone(extern_match)
        extern_body = extract_braced_body(text, extern_match)
        for catch_body in re.findall(r"catch\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*\}", extern_body, re.S):
            with self.subTest(catch_body=catch_body.strip()[:80]):
                self.assertNotIn("OBELISK_ERROR", catch_body)

    def test_plugin_api_rejection_paths_use_no_throw_warnings(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        boundary_prefix = text[: text.index("void PluginManager::LoadPlugins")]

        self.assertNotIn("OBELISK_WARN", boundary_prefix)
        self.assertIn("SafeLogWarnNoThrow", boundary_prefix)

        call_process_event = extract_function_body(text, r"void PluginCallProcessEvent\(.*?\)")
        self.assertLess(call_process_event.index("try"), call_process_event.index("IsCallProcessEventAllowed()"))


if __name__ == "__main__":
    unittest.main()
