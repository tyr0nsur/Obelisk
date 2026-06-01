#!/usr/bin/env python3
"""Static guardrails for PluginManager cleanup safety."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANAGER = REPO_ROOT / "core" / "PluginManager.cpp"
PLUGIN_MANAGER_HEADER = REPO_ROOT / "core" / "PluginManager.h"
OBELISK_API_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
CORE_DIR = REPO_ROOT / "core"

COPIED_DISPATCHER_CLEANUP_EXCEPTIONS = {
    "MissionCopiedBoolEventDispatcher": (
        "internal/test-only copied lifecycle dispatcher; not plugin-facing until a later "
        "promotion wires a public ABI registration path and PluginManager owner cleanup"
    ),
    "PlayerPrincipalEventDispatcher": (
        "internal/test-only copied lifecycle dispatcher; not plugin-facing until player "
        "identity promotion wires a public ABI registration path and PluginManager owner cleanup"
    ),
}

COPIED_DISPATCHER_PUBLIC_ABI_TOKENS = {
    "PlayerPrincipalEventDispatcher": (
        "PlayerPrincipal",
        "PLAYER_PRINCIPAL",
        "PlayerIdentity",
        "PLAYER_IDENTITY",
    ),
}

INVENTORY_GAMEPLAY_POLICY_EVENT_FAMILIES = {
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK": "InventoryPolicy",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK": "InventoryPolicy",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK": "ItemReturn",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK": "ItemReturn",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK": "ItemReturn",
}


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


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def obelisk_api_field_names(header: str) -> list[str]:
    match = re.search(
        r"typedef\s+struct\s+ObeliskApi\s*\{(?P<body>.*?)\}\s*ObeliskApi\s*;",
        strip_c_comments(header),
        re.DOTALL,
    )
    if match is None:
        raise AssertionError("typedef struct ObeliskApi block not found")

    fields: list[str] = []
    for declaration in match.group("body").split(";"):
        declaration = " ".join(declaration.split())
        if not declaration:
            continue
        function_pointer = re.search(r"\(\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", declaration)
        if function_pointer:
            fields.append(function_pointer.group(1))
            continue
        plain_field = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]+\])?$", declaration)
        if plain_field:
            fields.append(plain_field.group(1))
    return fields


def inventory_gameplay_policy_event_kinds(header: str) -> set[str]:
    match = re.search(
        r"typedef\s+enum\s+ObeliskGameplayPolicyEventKind\s*\{(?P<body>.*?)\}"
        r"\s*ObeliskGameplayPolicyEventKind\s*;",
        strip_c_comments(header),
        re.DOTALL,
    )
    if match is None:
        raise AssertionError("ObeliskGameplayPolicyEventKind enum not found")

    return set(
        re.findall(
            r"\b(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_[A-Z0-9_]+)\b\s*=",
            match.group("body"),
        )
    )


def gameplay_policy_event_mask_name(event_kind: str) -> str:
    return event_kind.replace(
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_",
        "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_",
        1,
    )


def assert_tokens_present(test_case: unittest.TestCase, body: str, tokens: set[str]) -> None:
    for token in sorted(tokens):
        with test_case.subTest(token=token):
            test_case.assertIn(token, body)


def cleaned_dispatcher_classes(cleanup_body: str) -> set[str]:
    dispatchers = set(
        re.findall(
            r"\b(\w+EventDispatcher)::Get\(\)\.UnregisterCallbacksForOwner\(owner\)",
            cleanup_body,
        )
    )
    if "m_ChatDispatcher->UnregisterCallbacksForOwner(owner)" in cleanup_body:
        dispatchers.add("ChatEventDispatcher")
    return dispatchers


class PluginManagerGuardrailTests(unittest.TestCase):
    def test_obelisk_api_table_is_zero_initialized_and_fully_assigned(self) -> None:
        plugin_manager_header = PLUGIN_MANAGER_HEADER.read_text(encoding="utf-8")
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")

        self.assertRegex(
            plugin_manager_header,
            r"\bObeliskApi\s+m_Api\s*\{\s*\}\s*;",
            "PluginManager must zero-initialize the public API table before assigning fields.",
        )

        constructor_body = extract_function_body(
            plugin_manager_text,
            r"PluginManager::PluginManager\(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher\)"
            r"\s*:\s*m_Loader\(&loader\)\s*,\s*m_ChatDispatcher\(&chatDispatcher\)",
        )
        assigned_fields = set(re.findall(r"\bm_Api\.([A-Za-z_][A-Za-z0-9_]*)\s*=", constructor_body))
        declared_fields = set(obelisk_api_field_names(api_header))

        self.assertEqual(
            sorted(declared_fields - assigned_fields),
            [],
            "Every ObeliskApi field needs an explicit PluginManager constructor assignment.",
        )
        self.assertEqual(
            sorted(assigned_fields - declared_fields),
            [],
            "PluginManager assigns a field that is not in the public ObeliskApi struct.",
        )

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

    def test_plugin_owner_cleanup_covers_public_v1_registration_maps(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(
            text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )

        public_cleanup_tokens = (
            "UnregisterGameplayPolicyRegistrationsForOwner(owner)",
            "UnregisterChatMessageRegistrationsForOwner(owner)",
        )
        for token in public_cleanup_tokens:
            with self.subTest(token=token):
                self.assertIn(token, body)

        direct_dispatcher_cleanup_tokens = (
            "m_ChatDispatcher->UnregisterCallbacksForOwner(owner)",
            "StructureEventDispatcher::Get().UnregisterCallbacksForOwner(owner)",
            "InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner)",
            "ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner)",
        )
        for public_token in public_cleanup_tokens:
            with self.subTest(public_token=public_token):
                public_index = body.index(public_token)
                for direct_token in direct_dispatcher_cleanup_tokens:
                    self.assertLess(public_index, body.index(direct_token))

    def test_inventory_gameplay_policy_kinds_are_wired_to_expected_dispatcher_family(self) -> None:
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        declared_inventory_kinds = inventory_gameplay_policy_event_kinds(api_header)
        expected_inventory_kinds = set(INVENTORY_GAMEPLAY_POLICY_EVENT_FAMILIES)
        self.assertEqual(
            declared_inventory_kinds,
            expected_inventory_kinds,
            "New OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_* values need an explicit "
            "dispatcher-family decision in INVENTORY_GAMEPLAY_POLICY_EVENT_FAMILIES.",
        )

        inventory_policy_kinds = {
            kind
            for kind, family in INVENTORY_GAMEPLAY_POLICY_EVENT_FAMILIES.items()
            if family == "InventoryPolicy"
        }
        item_return_kinds = {
            kind
            for kind, family in INVENTORY_GAMEPLAY_POLICY_EVENT_FAMILIES.items()
            if family == "ItemReturn"
        }
        inventory_policy_masks = {gameplay_policy_event_mask_name(kind) for kind in inventory_policy_kinds}
        item_return_masks = {gameplay_policy_event_mask_name(kind) for kind in item_return_kinds}

        describe_body = extract_function_body(
            plugin_manager_text,
            r"bool DescribeGameplayPolicyEventKind\(.*?\)",
        )
        assert_tokens_present(self, describe_body, expected_inventory_kinds)
        assert_tokens_present(self, describe_body, inventory_policy_masks | item_return_masks)
        self.assertEqual(
            describe_body.count("OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED"),
            len(expected_inventory_kinds),
        )

        inventory_kind_body = extract_function_body(
            plugin_manager_text,
            r"uint32_t ToGameplayPolicyEventKind\(InventoryPolicyEventKind kind\)",
        )
        assert_tokens_present(self, inventory_kind_body, inventory_policy_kinds)
        for token in sorted(item_return_kinds):
            with self.subTest(forbidden_item_return_token=token):
                self.assertNotIn(token, inventory_kind_body)

        item_return_kind_body = extract_function_body(
            plugin_manager_text,
            r"uint32_t ToGameplayPolicyEventKind\(ItemReturnEventKind kind\)",
        )
        assert_tokens_present(self, item_return_kind_body, item_return_kinds)
        for token in sorted(inventory_policy_kinds):
            with self.subTest(forbidden_inventory_policy_token=token):
                self.assertNotIn(token, item_return_kind_body)

        mask_body = extract_function_body(
            plugin_manager_text,
            r"uint64_t ToGameplayPolicyEventMask\(uint32_t eventKind\)",
        )
        assert_tokens_present(self, mask_body, expected_inventory_kinds)
        assert_tokens_present(self, mask_body, inventory_policy_masks | item_return_masks)

        register_body = extract_function_body(
            plugin_manager_text,
            r"uint64_t RegisterGameplayPolicyEventForOwner\(.*?\)",
        )
        assert_tokens_present(self, register_body, inventory_policy_masks | item_return_masks)
        for token in inventory_policy_masks:
            with self.subTest(registration_family=token):
                self.assertLess(register_body.index(token), register_body.index("InventoryPolicyEventDispatcher::Get().Register"))
        for token in item_return_masks:
            with self.subTest(registration_family=token):
                self.assertLess(register_body.index(token), register_body.index("ItemReturnEventDispatcher::Get().Register"))
        self.assertIn("DispatchGameplayPolicyEventFromInventory", register_body)
        self.assertIn("DispatchGameplayPolicyEventFromItemReturn", register_body)

        unregister_body = extract_function_body(
            plugin_manager_text,
            r"bool UnregisterGameplayPolicyRegistrationForOwner\(.*?\)",
        )
        self.assertIn("registration.InventoryRegistrationId", unregister_body)
        self.assertIn("InventoryPolicyEventDispatcher::Get().UnregisterCallbackForOwner", unregister_body)
        self.assertIn("registration.ItemReturnRegistrationId", unregister_body)
        self.assertIn("ItemReturnEventDispatcher::Get().UnregisterCallbackForOwner", unregister_body)

        unregister_owner_body = extract_function_body(
            plugin_manager_text,
            r"size_t UnregisterGameplayPolicyRegistrationsForOwner\(.*?\)",
        )
        self.assertIn("registration.InventoryRegistrationId", unregister_owner_body)
        self.assertIn("InventoryPolicyEventDispatcher::Get().UnregisterCallbackForOwner", unregister_owner_body)
        self.assertIn("registration.ItemReturnRegistrationId", unregister_owner_body)
        self.assertIn("ItemReturnEventDispatcher::Get().UnregisterCallbackForOwner", unregister_owner_body)

        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )
        for token in (
            "UnregisterGameplayPolicyRegistrationsForOwner(owner)",
            "InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner)",
            "ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner)",
        ):
            with self.subTest(owner_cleanup_token=token):
                self.assertIn(token, cleanup_body)
        public_cleanup_index = cleanup_body.index("UnregisterGameplayPolicyRegistrationsForOwner(owner)")
        self.assertLess(
            public_cleanup_index,
            cleanup_body.index("InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner)"),
        )
        self.assertLess(
            public_cleanup_index,
            cleanup_body.index("ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner)"),
        )

    def test_plugin_owner_cleanup_covers_each_plugin_facing_event_dispatcher(self) -> None:
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )

        dispatcher_classes: set[str] = set()
        for header in CORE_DIR.glob("*EventDispatcher.h"):
            header_text = header.read_text(encoding="utf-8")
            if "UnregisterCallbacksForOwner" not in header_text:
                continue
            match = re.search(r"class\s+(\w+EventDispatcher)\b", header_text)
            self.assertIsNotNone(match, f"{header} has owner cleanup but no dispatcher class")
            dispatcher_classes.add(match.group(1))

        cleaned_dispatchers = cleaned_dispatcher_classes(cleanup_body)

        missing = sorted(
            dispatcher_classes
            - cleaned_dispatchers
            - set(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS)
        )
        self.assertEqual(
            missing,
            [],
            "New plugin-facing copied event dispatchers must be added to "
            "PluginManager::UnregisterPluginCallbacks, or explicitly documented in "
            "COPIED_DISPATCHER_CLEANUP_EXCEPTIONS while still internal/test-only.",
        )

        stale_exceptions = sorted(
            set(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS) - dispatcher_classes
        )
        self.assertEqual(stale_exceptions, [])
        for dispatcher, reason in COPIED_DISPATCHER_CLEANUP_EXCEPTIONS.items():
            with self.subTest(dispatcher=dispatcher):
                self.assertIn(dispatcher, dispatcher_classes)
                self.assertIn("internal/test-only", reason)
                self.assertIn("not plugin-facing", reason)
                self.assertIn("PluginManager owner cleanup", reason)
                self.assertNotIn(dispatcher, cleaned_dispatchers)

    def test_internal_test_only_dispatcher_exceptions_are_not_public_abi_or_plugin_manager_wired(self) -> None:
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )
        cleaned_dispatchers = cleaned_dispatcher_classes(cleanup_body)

        for dispatcher, blocked_tokens in COPIED_DISPATCHER_PUBLIC_ABI_TOKENS.items():
            if dispatcher in cleaned_dispatchers:
                continue
            with self.subTest(dispatcher=dispatcher):
                self.assertIn(
                    dispatcher,
                    COPIED_DISPATCHER_CLEANUP_EXCEPTIONS,
                    "Dispatcher-specific public ABI tokens should be blocked only while the "
                    "dispatcher is documented as an internal/test-only cleanup exception.",
                )
                self.assertNotIn(
                    dispatcher,
                    plugin_manager_text,
                    "Internal/test-only dispatcher exceptions must not be wired through "
                    "PluginManager until owner cleanup is added.",
                )
                for token in blocked_tokens:
                    with self.subTest(dispatcher=dispatcher, token=token):
                        self.assertNotIn(
                            token,
                            api_header,
                            "Player identity/principal public ABI must stay absent until the "
                            "dispatcher is covered by PluginManager owner cleanup.",
                        )
                        self.assertNotIn(
                            token,
                            plugin_manager_text,
                            "Player identity/principal PluginManager wiring must stay absent "
                            "until dispatcher owner cleanup is explicit.",
                        )

    def test_event_dispatcher_owner_cleanup_failures_propagate_to_plugin_manager(self) -> None:
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")
            if "UnregisterCallbacksForOwner" not in text:
                continue
            body = extract_function_body(
                text,
                r"size_t \w+EventDispatcher::UnregisterCallbacksForOwner\(void\* owner\)",
            )
            for catch_body in re.findall(r"catch\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*\}", body, re.S):
                with self.subTest(source=source.name, catch_body=catch_body.strip()[:80]):
                    self.assertIn("throw", catch_body)
                    self.assertNotRegex(catch_body, r"\breturn\s+0\s*;")

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
