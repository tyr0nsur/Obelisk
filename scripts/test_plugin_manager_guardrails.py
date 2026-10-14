#!/usr/bin/env python3
"""Static guardrails for PluginManager cleanup safety."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from native_prototype_guardrails import (
    NATIVE_PROTOTYPE_API_FIELDS,
    native_prototype_symbols_for_header,
    without_native_prototype_symbols,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANAGER = REPO_ROOT / "core" / "PluginManager.cpp"
PLUGIN_MANAGER_HEADER = REPO_ROOT / "core" / "PluginManager.h"
PLUGIN_MANAGER_TESTS = REPO_ROOT / "tests" / "core" / "PluginManagerTests.cpp"
CMAKE_LISTS = REPO_ROOT / "CMakeLists.txt"
TIMER_MANAGER = REPO_ROOT / "core" / "TimerManager.cpp"
LOGGER = REPO_ROOT / "runtime" / "Logger.cpp"
OBELISK_API_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
CORE_DIR = REPO_ROOT / "core"

INJECTED_OWNER_REGISTRIES = {
    "m_ChatDispatcher": "ChatEventDispatcher",
    "m_CommandDispatcher": "CommandDispatcher",
    "m_PlayerLifecycleDispatcher": "PlayerLifecycleDispatcher",
}

NATIVE_OWNER_UNREGISTER_APIS = {
    "PluginUnregisterCommandWithOwnerToken": "PluginOwnerCommandDispatcherLocked",
    "PluginUnregisterPlayerLifecycleWithOwnerToken": "PluginOwnerPlayerLifecycleDispatcherLocked",
}

COPIED_DISPATCHER_CLEANUP_EXCEPTIONS = {
    "MissionCopiedBoolEventDispatcher": (
        "internal/test-only non-public copied lifecycle dispatcher; not plugin-facing until "
        "a later promotion wires a public ABI registration path and PluginManager owner cleanup"
    ),
}

INTERNAL_TEST_ONLY_DISPATCHERS = {
    "MissionCopiedBoolEventDispatcher": (
        "internal/test-only non-public copied lifecycle dispatcher; not plugin-facing until "
        "a later promotion wires a public ABI registration path and PluginManager owner cleanup"
    ),
    "PlayerPrincipalEventDispatcher": (
        "internal/test-only non-public player-principal lifecycle dispatcher; not plugin-facing "
        "until a later player identity promotion wires a public ABI registration path, "
        "PluginManager owner cleanup, and SDK tests"
    ),
}

DISPATCHER_PUBLIC_NAME_ALIASES = {
    "ChatEventDispatcher": ("ChatMessage",),
    "StructureEventDispatcher": ("GameplayPolicy",),
    "InventoryPolicyEventDispatcher": ("GameplayPolicy",),
    "ItemReturnEventDispatcher": ("GameplayPolicy",),
    "PlayerPrincipalEventDispatcher": ("PlayerIdentity",),
}

COPIED_DISPATCHER_PUBLIC_ABI_TOKENS = {
    "MissionCopiedBoolEventDispatcher": (
        "MissionCopiedBool",
        "MISSION_COPIED_BOOL",
        "ObeliskMission",
        "MissionEvent",
        "OBELISK_API_CAPABILITY_MISSION",
        "RegisterMission",
        "UnregisterMission",
    ),
    "PlayerPrincipalEventDispatcher": (
        "PlayerPrincipal",
        "PLAYER_PRINCIPAL",
        "PlayerIdentity",
        "PLAYER_IDENTITY",
    ),
}

COPIED_DISPATCHER_PLUGIN_MANAGER_CLEANUP_TOKENS = {
    "ChatEventDispatcher": "m_ChatDispatcher->UnregisterCallbacksForOwner(owner, deadline)",
    "StructureEventDispatcher": "StructureEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)",
    "InventoryPolicyEventDispatcher": (
        "InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)"
    ),
    "ItemReturnEventDispatcher": "ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)",
    "PlayerPrincipalEventDispatcher": (
        "PlayerPrincipalEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)"
    ),
}

OWNER_TOKEN_HANDLE_CLEANUP_BACKSTOPS = {
    "RegisterPreProcessEventWithOwnerTokenHandle": "EventManager::Get().UnregisterCallbacksForOwner(owner, deadline)",
    "RegisterPostProcessEventWithOwnerTokenHandle": "EventManager::Get().UnregisterCallbacksForOwner(owner, deadline)",
    "RegisterPreProcessEventForNameIndexWithOwnerTokenHandle": (
        "EventManager::Get().UnregisterCallbacksForOwner(owner, deadline)"
    ),
    "RegisterPostProcessEventForNameIndexWithOwnerTokenHandle": (
        "EventManager::Get().UnregisterCallbacksForOwner(owner, deadline)"
    ),
    "RegisterGameplayPolicyEventWithOwnerTokenHandle": "UnregisterGameplayPolicyRegistrationsForOwner(owner)",
    "RegisterChatMessageEventWithOwnerTokenHandle": "UnregisterChatMessageRegistrationsForOwner(owner)",
    "RegisterTimerWithOwnerTokenHandle": "TimerManager::Get().UnregisterCallbacksForOwner(owner, deadline)",
    "RegisterCommandWithOwnerTokenHandle": "m_CommandDispatcher->UnregisterCallbacksForOwner(owner, deadline)",
    "RegisterPlayerLifecycleWithOwnerTokenHandle": "m_PlayerLifecycleDispatcher->UnregisterCallbacksForOwner(owner, deadline)",
}

LEGACY_VOID_OWNER_TOKEN_REGISTRATION_WRAPPERS = {
    "RegisterPreProcessEventWithOwnerToken": "PluginRegisterPreProcessEventWithOwnerTokenHandle(ownerToken, callback)",
    "RegisterPostProcessEventWithOwnerToken": "PluginRegisterPostProcessEventWithOwnerTokenHandle(ownerToken, callback)",
    "RegisterPreProcessEventForNameIndexWithOwnerToken": (
        "PluginRegisterPreProcessEventForNameIndexWithOwnerTokenHandle(ownerToken, nameIndex, callback)"
    ),
    "RegisterPostProcessEventForNameIndexWithOwnerToken": (
        "PluginRegisterPostProcessEventForNameIndexWithOwnerTokenHandle(ownerToken, nameIndex, callback)"
    ),
}

BLOCKED_PLUGIN_MANAGER_PUBLIC_WIRING_TOKENS = {
    "inventory-action observer": (
        "InventoryAction",
        "InventoryActionObserver",
        "ObeliskInventoryAction",
        "RegisterInventoryAction",
        "UnregisterInventoryAction",
        "ServerRequestInventoryUseItem",
        "ServerRequestInventoryUseItemWithActor",
    ),
    "player principal": (
        "ObeliskPlayerPrincipal",
        "ObeliskPrincipalId",
        "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL",
        "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
        "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS",
        "PLAYER_PRINCIPAL_EVENTS",
        "RegisterPlayerPrincipal",
        "RegisterPlayerIdentity",
        "RegisterPlayerPrincipalEvent",
        "UnregisterPlayerPrincipal",
        "UnregisterPlayerIdentity",
        "ResolvePlayerPrincipal",
        "ResolvePlayerIdentity",
    ),
    "permissions/admin": (
        "ObeliskPermissionQuery",
        "ObeliskPermissionDecision",
        "OBELISK_API_CAPABILITY_PERMISSION",
        "OBELISK_API_CAPABILITY_ADMIN",
        "RegisterAdminCommand",
        "GrantPermission",
        "RevokePermission",
    ),
    "command response": (
        "ObeliskCommandContext",
        "ObeliskCommandReply",
        "ObeliskChatResponse",
        "OBELISK_API_CAPABILITY_COMMAND",
        "RegisterCommand",
        "ReplyToCommand",
        "SendChat",
    ),
    "mutation": (
        "ObeliskMutation",
        "OBELISK_API_CAPABILITY_RESOURCE_MUTATION",
        "MutateInventory",
        "MutateItem",
        "OverrideReturn",
        "ReturnOverride",
    ),
    "transfer/buff/dino side lanes": (
        "TransferScriptStruct",
        "TransferPayload",
        "TransferBAccept",
        "ObeliskTransfer",
        "ObeliskTransferPayload",
        "ObeliskTransferScriptStruct",
        "ObeliskTransferBAccept",
        "OBELISK_API_CAPABILITY_TRANSFER",
        "OBELISK_API_CAPABILITY_TRANSFER_PAYLOAD",
        "OBELISK_API_CAPABILITY_TRANSFER_SCRIPTSTRUCT",
        "OBELISK_API_CAPABILITY_TRANSFER_BACCEPT",
        "RegisterTransfer",
        "RegisterTransferPayload",
        "RegisterTransferScriptStruct",
        "RegisterTransferBAccept",
        "UnregisterTransfer",
        "UnregisterTransferPayload",
        "UnregisterTransferScriptStruct",
        "UnregisterTransferBAccept",
        "BuffStatus",
        "ObeliskBuff",
        "ObeliskBuffStatus",
        "OBELISK_API_CAPABILITY_BUFF",
        "OBELISK_API_CAPABILITY_BUFF_STATUS",
        "RegisterBuff",
        "RegisterBuffStatus",
        "UnregisterBuff",
        "UnregisterBuffStatus",
        "DinoScalar",
        "CopiedDinoScalar",
        "ObeliskDino",
        "ObeliskDinoScalar",
        "OBELISK_API_CAPABILITY_DINO",
        "OBELISK_API_CAPABILITY_DINO_SCALAR",
        "RegisterDino",
        "RegisterDinoScalar",
        "UnregisterDino",
        "UnregisterDinoScalar",
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


def obelisk_api_function_field_names(header: str) -> list[str]:
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


def assert_cleanup_token_uses_cleanup_family(
    test_case: unittest.TestCase,
    cleanup_body: str,
    cleanup_token: str,
) -> None:
    test_case.assertIn(cleanup_token, cleanup_body)
    cleanup_index = cleanup_body.index(cleanup_token)
    cleanup_window = cleanup_body[max(0, cleanup_index - 360):cleanup_index]
    test_case.assertIn(
        "cleanupFamily(",
        cleanup_window,
        "Owner cleanup backstops must be invoked through the isolated PluginManager "
        "cleanup family wrapper so exceptions block dlclose.",
    )


def owner_cleanup_registry_classes() -> set[str]:
    registry_classes: set[str] = set()
    for header in CORE_DIR.glob("*.h"):
        header_text = header.read_text(encoding="utf-8")
        if "UnregisterCallbacksForOwner" not in header_text:
            continue
        match = re.search(r"^\s*class\s+(\w+)\b", header_text, re.MULTILINE)
        if match is None:
            raise AssertionError(f"{header} has owner cleanup but no class declaration")
        registry_classes.add(match.group(1))
    return registry_classes


def cleaned_owner_registry_classes(cleanup_body: str) -> set[str]:
    registries = set(
        re.findall(
            r"\b(\w+)::Get\(\)\.UnregisterCallbacksForOwner\(owner,\s*deadline\)",
            cleanup_body,
        )
    )
    for member, registry in INJECTED_OWNER_REGISTRIES.items():
        if f"{member}->UnregisterCallbacksForOwner(owner, deadline)" in cleanup_body:
            registries.add(registry)
    return registries


def blocked_surface_scan_text(api_header: str, plugin_manager_text: str) -> tuple[str, str]:
    # Only the complete, exactly named callback prototype is exempt. Prefix
    # exemptions would also admit blocked command/identity authority APIs.
    allowed = native_prototype_symbols_for_header(api_header)
    api_header = without_native_prototype_symbols(api_header, header_only=True)
    if allowed:
        plugin_manager_text = without_native_prototype_symbols(plugin_manager_text)
        wrappers = "|".join(re.escape(f"Plugin{field}") for field in NATIVE_PROTOTYPE_API_FIELDS)
        plugin_manager_text = re.sub(rf"\b(?:{wrappers})\b", "NativePrototypeWrapper", plugin_manager_text)
    return strip_c_comments(api_header), strip_c_comments(plugin_manager_text)


def cleaned_dispatcher_classes(cleanup_body: str) -> set[str]:
    return {name for name in cleaned_owner_registry_classes(cleanup_body) if name.endswith("EventDispatcher")}


def event_dispatcher_class_names() -> set[str]:
    dispatchers: set[str] = set()
    for header in CORE_DIR.glob("*EventDispatcher.h"):
        header_text = header.read_text(encoding="utf-8")
        match = re.search(r"class\s+(\w+EventDispatcher)\b", header_text)
        if match is None:
            raise AssertionError(f"{header} has no event dispatcher class declaration")
        dispatchers.add(match.group(1))
    return dispatchers


def dispatcher_public_name_stems(dispatcher: str) -> set[str]:
    if not dispatcher.endswith("EventDispatcher"):
        raise AssertionError(f"not an event dispatcher class name: {dispatcher}")

    base_name = dispatcher.removesuffix("EventDispatcher")
    stems = {base_name}
    if base_name.endswith("Event"):
        stems.add(base_name.removesuffix("Event"))
    stems.update(DISPATCHER_PUBLIC_NAME_ALIASES.get(dispatcher, ()))
    return stems


def public_plugin_surface_tokens(api_header: str, plugin_manager_text: str) -> set[str]:
    tokens = {
        field
        for field in obelisk_api_function_field_names(api_header)
        if field.startswith(("Register", "Unregister"))
    }
    tokens.update(
        re.findall(
            r"\b(?:uint64_t|void|bool)\s+(Plugin(?:Register|Unregister)[A-Za-z0-9_]*)\s*\(",
            plugin_manager_text,
        )
    )
    tokens.update(re.findall(r"\bOBELISK_API_CAPABILITY_[A-Z0-9_]+", api_header))
    return tokens


def public_plugin_surface_tokens_for_dispatcher(
    dispatcher: str,
    public_tokens: set[str],
) -> set[str]:
    stems = {stem.replace("_", "").lower() for stem in dispatcher_public_name_stems(dispatcher)}
    return {
        token
        for token in public_tokens
        if any(stem in token.replace("_", "").lower() for stem in stems)
    }


def validate_retirement_protocol(text: str) -> None:
    body = extract_function_body(text, r"bool PluginManager::RetirePlugin\(.*?\)")
    tokens = (
        "gate.RetireAndDrain(plugin.execution, deadline)",
        "MarkPluginOwnerUnloading(plugin.owner)",
        "UnregisterPluginCallbacks(plugin.name, plugin.owner",
        "plugin.prepareUnload()",
        "CallPluginShutdown(plugin.name, plugin.shutdown)",
        "SafeCloseLibrary(*m_Loader, plugin.handle, plugin.name)",
        "gate.Forget(plugin.execution)",
        "RemovePluginOwnerToken(plugin.ownerToken)",
    )
    try:
        positions = [body.index(token) for token in tokens]
    except ValueError as error:
        raise AssertionError("retirement operation is missing") from error
    if positions != sorted(positions):
        raise AssertionError("retirement, cleanup, plugin shutdown and close order is unsafe")
    if not re.search(r"UnregisterPluginCallbacks\(plugin.name, plugin.owner,\s*\"[^\"]*\", deadline\)", body):
        raise AssertionError("owner cleanup lost the operation deadline")
    if 'return fail("registration_cleanup_incomplete")' not in body[:positions[3]]:
        raise AssertionError("incomplete cleanup can enter plugin lifecycle code")
    if "if (plugin.shutdownFailed)" not in body[:positions[4]]:
        raise AssertionError("throwing Shutdown may be retried")
    if "if (plugin.prepareUnloadFailed)" not in body[:positions[3]]:
        raise AssertionError("throwing PrepareUnload may be retried")


class PluginManagerGuardrailTests(unittest.TestCase):
    def test_hot_plugin_retirement_protocol_rejects_unsafe_mutations(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        validate_retirement_protocol(text)
        mutations = (
            text.replace("UnregisterPluginCallbacks(plugin.name, plugin.owner", "RemovedCleanup(plugin.name, plugin.owner", 1),
            text.replace('"retired; before Shutdown and dlclose", deadline)', '"retired; before Shutdown and dlclose")', 1),
            text.replace("if (plugin.shutdownFailed)", "if (false)", 1),
            text.replace("if (plugin.prepareUnloadFailed)", "if (false)", 1),
            text.replace("CallPluginShutdown(plugin.name, plugin.shutdown)", "RemovedShutdown(plugin.name, plugin.shutdown)", 1),
        )
        for index, mutated in enumerate(mutations):
            with self.subTest(mutation=index):
                self.assertNotEqual(mutated, text)
                with self.assertRaises(AssertionError):
                    validate_retirement_protocol(mutated)

    def test_operator_control_rejects_reentry_before_mutex_and_requires_fresh_running_init(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        control = extract_function_body(text, r"nlohmann::json PluginManager::ExecuteOperation\(.*?\)")
        for token in ("g_CurrentPluginOwner", "Gate::IsInsideExecution()", "GameplayCallbackScope::Current()"):
            self.assertLess(control.index(token), control.index("control.try_lock_until(deadline)"))
        self.assertIn("loaded->lifecycleCapabilities != 1u || !loaded->prepareUnload", control)
        self.assertIn("RetirePlugin(*loaded, deadline, true, reason)", control)
        self.assertIn("LoadPluginsImpl(source.parent_path().string(), source, pluginId, deadline)", control)
        self.assertIn("p.pluginId == pluginId && p.initialized", control)
        self.assertIn("Gate::Get().Inspect(p.execution).phase == Gate::Phase::Running", control)
        for field in ("retained", "shutdown_failed", "prepare_unload_failed", "last_failure"):
            self.assertIn(f'value["{field}"]', control)
        self.assertIn("TimerManager::Get().NotifyOwnerResumed(loaded->owner)", control)

    def test_registration_gate_does_not_hold_owner_registry_mutex_while_plugin_cleanup_runs(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        for helper in ("RegisterProcessEventCallbackForOwnerToken", "RegisterProcessEventCallbackForCallbackOwner"):
            body = extract_function_body(text, rf"uint64_t {helper}\(.*?\)")
            locked_scope = re.search(r"(?=\{\s*std::lock_guard<std::mutex> lock\(PluginOwnerLifecycleMutex\(\)\))", body)
            self.assertIsNotNone(locked_scope)
            locked = extract_braced_body(body, locked_scope)
            self.assertIn("OwnerExecutionGate::Get().Capture(owner)", locked)
            self.assertNotIn("registerFn(owner)", locked)
            self.assertLess(locked_scope.start() + len(locked) + 2, body.index("OwnerExecutionGate::EnterRegistration(binding)"))
            self.assertLess(body.index("OwnerExecutionGate::EnterRegistration(binding)"), body.index("try { return registerFn(owner); }"))
            self.assertIn("catch (const std::exception& e)", body)
            self.assertIn("catch (...)", body)

    def test_generation_copy_and_lifecycle_symbols_are_mapping_specific(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        owner = extract_function_body(text, r"void\* GetSymbolOwner\(void\* handle, void\* symbol\) override")
        self.assertIn("dlinfo(handle, RTLD_DI_LINKMAP, &primary)", owner)
        self.assertIn("symbolInfo.dli_fbase == reinterpret_cast<void*>(primary->l_addr)", owner)
        self.assertIn("return nullptr", owner)
        copy = extract_function_body(text, r"fs::path CopyPluginGeneration\(.*?\)")
        for token in ('".native-lifecycle"', '"generations"', '"generation-XXXXXX"', "::mkdtemp(pattern.data())",
                      "source.filename()", "fs::copy_options::none", "fs::rename(temporary, destination)", "catch (...)"):
            self.assertIn(token, copy)
        load = extract_function_body(text, r"void PluginManager::LoadPluginsImpl\(.*?\)")
        self.assertLess(load.index("loaded.sourcePath == path"), load.index("m_Loader->Open(generationPath, loaderError)"))
        self.assertIn("!ownSymbol(shutdownFunc) || !ownSymbol(prepareUnload) || !ownSymbol(lifecycleCapabilities)", load)
        self.assertIn("!expectedPluginId.empty() && (lifecycleFlags != 1u || !prepareUnload)", load)
        self.assertLess(load.index("!expectedPluginId.empty() && (lifecycleFlags != 1u || !prepareUnload)"), load.index("initFunc(&pluginApi"))

    def test_alias_owner_cleanup_waits_for_bounded_backing_barriers_without_granular_retry(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        cleanup = extract_function_body(text, r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)")
        for member in INJECTED_OWNER_REGISTRIES:
            self.assertEqual(cleanup.count(f"{member}->UnregisterCallbacksForOwner(owner, deadline)"), 1)
        for helper in ("UnregisterChatMessageRegistrationsForOwner", "UnregisterGameplayPolicyRegistrationsForOwner"):
            aliases = extract_function_body(text, rf"size_t {helper}\(.*?\)")
            self.assertNotIn("UnregisterCallbackForOwner(", aliases)
            self.assertNotIn("UnregisterCallbacksForOwner(", aliases)
        self.assertLess(cleanup.index("m_ChatDispatcher->UnregisterCallbacksForOwner(owner, deadline)"), cleanup.index("UnregisterChatMessageRegistrationsForOwner(owner)"))
        self.assertLess(cleanup.index("ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)"), cleanup.index("UnregisterGameplayPolicyRegistrationsForOwner(owner)"))
        self.assertIn("if (!chatSucceeded) throw", cleanup)
        self.assertIn("if (!structureSucceeded || !inventorySucceeded || !itemReturnSucceeded)", cleanup)

    def test_raw_process_event_public_abi_comments_keep_debug_window_default_deny(self) -> None:
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")

        for token in (
            "OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS",
            "allow-global-process-event-callbacks",
            "OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS",
            "allow-filtered-process-event-callbacks",
            "controlled debug windows",
            "not production readiness signals",
            "live env+marker gate",
        ):
            with self.subTest(token=token):
                self.assertIn(token, api_header)

    def test_raw_process_event_capabilities_are_debug_window_default_deny(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        capabilities_body = extract_function_body(text, r"uint64_t BuildApiCapabilities\(\)")

        self.assertIn("AreGlobalProcessEventCallbacksAllowed()", capabilities_body)
        self.assertIn("OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS", capabilities_body)
        self.assertLess(
            capabilities_body.index("AreGlobalProcessEventCallbacksAllowed()"),
            capabilities_body.index("OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS"),
        )
        self.assertIn("AreFilteredProcessEventCallbacksAllowed()", capabilities_body)
        self.assertIn("OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS", capabilities_body)
        self.assertLess(
            capabilities_body.index("AreFilteredProcessEventCallbacksAllowed()"),
            capabilities_body.index("OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS"),
        )
        self.assertIn("IsCallProcessEventAllowed()", capabilities_body)
        self.assertIn("OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT", capabilities_body)
        self.assertIn("IsProcessEventBlockingAllowed()", capabilities_body)
        self.assertIn("OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING", capabilities_body)

        for pattern, capability, live_gate in (
            (
                r"bool IsGlobalProcessEventCallbackCapabilityEnabledForOwner\(.*?\)",
                "OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS",
                "AreGlobalProcessEventCallbacksAllowed()",
            ),
            (
                r"bool IsFilteredProcessEventCallbackCapabilityEnabledForOwner\(.*?\)",
                "OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS",
                "AreFilteredProcessEventCallbacksAllowed()",
            ),
        ):
            with self.subTest(pattern=pattern):
                body = extract_function_body(text, pattern)
                self.assertIn("PluginOwnerHasCapability(owner", body)
                self.assertIn(capability, body)
                self.assertIn(live_gate, body)

    def test_call_process_event_stays_init_owner_debug_escape_hatch(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        current_owner_body = extract_function_body(
            text,
            r"bool CurrentPluginOwnerHasCapability\(uint64_t capability\)",
        )
        self.assertIn("if (!g_CurrentPluginOwner)", current_owner_body)
        self.assertIn("return false", current_owner_body)
        self.assertIn("PluginOwnerHasCapabilityLocked(g_CurrentPluginOwner, capability)", current_owner_body)
        self.assertIn("!IsUnloadingPluginOwnerLocked(g_CurrentPluginOwner)", current_owner_body)

        call_process_event_body = extract_function_body(text, r"void PluginCallProcessEvent\(.*?\)")
        self.assertIn("CurrentPluginOwnerHasCapability(OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT)", call_process_event_body)
        self.assertIn("IsCallProcessEventAllowed()", call_process_event_body)
        self.assertLess(
            call_process_event_body.index("CurrentPluginOwnerHasCapability(OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT)"),
            call_process_event_body.index("Hooks::ProcessEventHook::CallOriginalProcessEvent"),
        )
        self.assertLess(
            call_process_event_body.index("IsCallProcessEventAllowed()"),
            call_process_event_body.index("Hooks::ProcessEventHook::CallOriginalProcessEvent"),
        )

    def test_current_plugin_owner_is_scoped_to_init_window(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"void PluginManager::LoadPluginsImpl\(.*?\)")
        scope = re.search(r"(?=\{\s*auto execution = OwnerExecutionGate::EnterLifecycle\(binding, OwnerExecutionGate::LifecycleEntry::Init\))", body)
        self.assertIsNotNone(scope)
        init_scope = extract_braced_body(body, scope)
        for token in ("void* previousOwner = g_CurrentPluginOwner", "g_CurrentPluginOwner = pluginOwner",
                      "auto ownerRestore = MakeScopeExit", "g_CurrentPluginOwner = previousOwner",
                      "plugin.initialized = initFunc(&pluginApi, &initContext)", "catch (...)"):
            self.assertIn(token, init_scope)
        self.assertLess(init_scope.index("auto ownerRestore"), init_scope.index("initFunc(&pluginApi"))
        self.assertNotIn("ownerRestore.Dismiss()", init_scope)
        self.assertLess(body.index("OwnerExecutionGate::Get().Bind(pluginOwner, pluginOwnerToken)"), scope.start())
        scope_end = scope.start() + len(init_scope) + 2
        self.assertLess(scope_end, body.index("OwnerExecutionGate::Get().Activate(binding)"))
        self.assertIn("plugin.initAttempted = true", init_scope)

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
            r"PluginManager::PluginManager\(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher,\s*"
            r"CommandDispatcher& commandDispatcher, PlayerLifecycleDispatcher& playerLifecycleDispatcher\)"
            r"\s*:\s*m_Loader\(&loader\)\s*,\s*m_ChatDispatcher\(&chatDispatcher\)"
            r"\s*,\s*m_CommandDispatcher\(&commandDispatcher\)"
            r"\s*,\s*m_PlayerLifecycleDispatcher\(&playerLifecycleDispatcher\)",
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

    def test_plugin_directory_validation_rejects_alias_and_symlink_components_before_discovery(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        alias_body = extract_function_body(
            text,
            r"bool ValidateNoPathAliasComponents\(.*?\)",
        )
        self.assertIn('component == "." || component == ".."', alias_body)
        self.assertIn("path alias components", alias_body)

        component_body = extract_function_body(
            text,
            r"bool ValidateExistingPathComponentsNoSymlinks\(.*?\)",
        )
        self.assertIn("ValidateNoPathAliasComponents(path, label, error)", component_body)
        self.assertIn("fs::symlink_status(current, ec)", component_body)
        self.assertIn("fs::is_symlink(status)", component_body)
        self.assertIn("path component must not be a symlink", component_body)

        load_body = extract_function_body(text, r"void PluginManager::LoadPluginsImpl\(.*?\)")
        config_validation_token = (
            'ValidateExistingPathComponentsNoSymlinks(configRoot, "OBELISK_CONFIG_DIR", '
            "configRootComponentError)"
        )
        self.assertIn(config_validation_token, load_body)
        self.assertLess(
            load_body.index(config_validation_token),
            load_body.index("ValidatePluginConfigRoot(configRoot"),
        )

        validation_token = (
            'ValidateExistingPathComponentsNoSymlinks(pluginDirectory, "Plugin directory", '
            "pluginDirectoryError)"
        )
        self.assertIn(validation_token, load_body)
        plugin_directory_status_token = (
            "fs::symlink_status(pluginDirectory, pluginDirectoryStatusError)"
        )
        self.assertLess(
            load_body.index(validation_token),
            load_body.index(plugin_directory_status_token),
        )
        self.assertLess(
            load_body.index(plugin_directory_status_token),
            load_body.index(
                "fs::directory_iterator iterator(pluginDirectory, "
                "fs::directory_options::none, directoryIteratorError)"
            ),
        )
        self.assertIn("entry.symlink_status(entryStatusError)", load_body)
        self.assertIn("fs::is_symlink(entryStatus)", load_body)
        candidate_component_validation = re.search(
            r"ValidateExistingPathComponentsNoSymlinks\(\s*path,\s*\"Plugin candidate\",\s*"
            r"candidatePathError\s*\)",
            load_body,
        )
        self.assertIsNotNone(
            candidate_component_validation,
            "Plugin candidates must revalidate the full path before open so a replaced "
            "plugin directory symlink is rejected.",
        )
        self.assertLess(
            load_body.index("fs::symlink_status(path, candidateStatusError)"),
            load_body.index("m_Loader->Open(generationPath, loaderError)"),
        )
        self.assertLess(
            candidate_component_validation.start(),
            load_body.index("m_Loader->Open(generationPath, loaderError)"),
        )

        per_plugin_config_revalidation = re.search(
            r"ValidateExistingPathComponentsNoSymlinks\(\s*configRoot,\s*\"OBELISK_CONFIG_DIR\",\s*"
            r"pluginConfigRootComponentError\s*\)",
            load_body,
        )
        self.assertIsNotNone(
            per_plugin_config_revalidation,
            "OBELISK_CONFIG_DIR must be revalidated per plugin before default config creation.",
        )
        self.assertLess(
            per_plugin_config_revalidation.start(),
            load_body.index("PreparePluginConfig(metadata"),
        )

    def test_plugin_loading_requires_safe_instance_id_before_config_or_discovery(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        load_body = extract_function_body(text, r"void PluginManager::LoadPluginsImpl\(.*?\)")

        instance_env_token = 'std::getenv("OBELISK_INSTANCE_ID")'
        safe_instance_token = "IsSafeInstanceId(instanceId)"
        config_env_token = 'std::getenv("OBELISK_CONFIG_DIR")'
        iterator_token = (
            "fs::directory_iterator iterator(pluginDirectory, "
            "fs::directory_options::none, directoryIteratorError)"
        )
        open_token = "m_Loader->Open(generationPath, loaderError)"

        for token in (instance_env_token, safe_instance_token, config_env_token, iterator_token, open_token):
            with self.subTest(token=token):
                self.assertIn(token, load_body)

        self.assertLess(load_body.index(instance_env_token), load_body.index(config_env_token))
        self.assertLess(load_body.index(safe_instance_token), load_body.index(config_env_token))
        self.assertLess(load_body.index(safe_instance_token), load_body.index(iterator_token))
        self.assertLess(load_body.index(safe_instance_token), load_body.index(open_token))

    def test_logger_rejects_unsafe_instance_id_instead_of_sanitizing_path(self) -> None:
        text = LOGGER.read_text(encoding="utf-8")
        self.assertNotIn("SanitizeIdentifier", text)

        safe_identifier_body = extract_function_body(
            text,
            r"std::string GetSafeInstanceIdentifier\(.*?\)",
        )
        self.assertIn("std::isalnum(ch) || ch == '_' || ch == '-'", safe_identifier_body)
        self.assertIn("throw std::runtime_error", safe_identifier_body)
        self.assertIn("OBELISK_INSTANCE_ID", safe_identifier_body)

        init_body = extract_function_body(text, r"void Logger::Init\(\)")
        self.assertIn(
            'GetSafeInstanceIdentifier(std::getenv("OBELISK_INSTANCE_ID"))',
            init_body,
        )
        self.assertLess(
            init_body.index("GetSafeInstanceIdentifier"),
            init_body.index("GetLogDir()"),
            "Logger must reject unsafe instance ids before creating log roots.",
        )
        self.assertIn("GetInstanceLogDir(logDir, instanceId)", init_body)

        instance_log_dir_body = extract_function_body(
            text,
            r"std::filesystem::path GetInstanceLogDir\(.*?\)",
        )
        self.assertIn("const std::string& instanceId", text)
        self.assertNotIn("std::getenv", instance_log_dir_body)

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
                    rf"(?:void|bool) {function_name}\(.*?\)",
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
        rollback = extract_function_body(text, r"auto initializationRollback = MakeScopeExit\(\[&\]\(\)")
        self.assertIn("RetirePlugin(plugin, rollbackDeadline, false, reason)", rollback)
        retirement = extract_function_body(text, r"bool PluginManager::RetirePlugin\(.*?\)")
        tokens = ("gate.RetireAndDrain(plugin.execution, deadline)", "MarkPluginOwnerUnloading(plugin.owner)",
                  "UnregisterPluginCallbacks(plugin.name, plugin.owner", "CallPluginShutdown(plugin.name, plugin.shutdown)",
                  "SafeCloseLibrary(*m_Loader, plugin.handle, plugin.name)", "RemovePluginOwnerToken(plugin.ownerToken)")
        positions = [retirement.index(token) for token in tokens]
        self.assertEqual(positions, sorted(positions), "Admission/drain and all cleanup must precede Shutdown and dlclose")
        self.assertIn('if (!cleaned)\n                return fail("registration_cleanup_incomplete")', retirement)
        cleanup = extract_function_body(text, r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)")
        self.assertIn("catch (const std::exception& e)", cleanup)
        self.assertIn("catch (...)", cleanup)
        self.assertGreaterEqual(cleanup.count("cleanupFamily("), 10)
        self.assertIn("cleanupSucceeded = false", cleanup)
        self.assertIn("return cleanupSucceeded", cleanup)

    def test_init_failure_cleanup_failure_retains_unloading_owner_for_retry(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        load = extract_function_body(text, r"void PluginManager::LoadPluginsImpl\(.*?\)")
        rollback = extract_function_body(load, r"auto initializationRollback = MakeScopeExit\(\[&\]\(\)")
        self.assertLess(load.index("m_LoadedPlugins.reserve(m_LoadedPlugins.size() + 1)"), load.index("initFunc(&pluginApi"))
        for token in ("PluginInfo plugin", "plugin.execution = binding", "plugin.prepareUnload = prepareUnload",
                      "plugin.lifecycleCapabilities = lifecycleFlags", "tokenRollback.Dismiss()", "handleCleanup.Dismiss()"):
            self.assertIn(token, load)
            self.assertLess(load.index(token), load.index("initFunc(&pluginApi"))
        self.assertIn("if (!RetirePlugin(plugin, rollbackDeadline, false, reason))", rollback)
        self.assertIn("m_LoadedPlugins.push_back(std::move(plugin))", rollback)
        self.assertIn("Retaining failed plugin generation mapped", rollback)
        self.assertIn("deadline == std::chrono::steady_clock::time_point::max()", rollback)
        self.assertIn("std::chrono::seconds(30) : deadline", rollback)
        for forbidden in ("SafeCloseLibrary", "RemovePluginOwnerToken", "ClearPluginOwnerUnloading"):
            self.assertNotIn(forbidden, rollback)

    def test_unload_all_wraps_shutdown_and_library_close(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        unload = extract_function_body(text, r"void PluginManager::UnloadAll\(\)")
        self.assertIn("RetirePlugin(plugin,", unload)
        self.assertIn("retainPluginForUnloadRetry(plugin,", unload)
        self.assertNotIn("CallPluginShutdown(", unload)
        self.assertNotIn("SafeCloseLibrary(", unload)
        retirement = extract_function_body(text, r"bool PluginManager::RetirePlugin\(.*?\)")
        shutdown_scope = re.search(r"(?=\{\s*auto execution = OwnerExecutionGate::EnterLifecycle\(plugin.execution, OwnerExecutionGate::LifecycleEntry::Shutdown\))", retirement)
        self.assertIsNotNone(shutdown_scope)
        body = extract_braced_body(retirement, shutdown_scope)
        self.assertIn("CallPluginShutdown(plugin.name, plugin.shutdown)", body)
        self.assertIn("plugin.shutdownAttempted = true", body)
        self.assertIn("plugin.shutdownFailed = true", body)
        self.assertIn('return fail("shutdown_threw")', body)
        close = "SafeCloseLibrary(*m_Loader, plugin.handle, plugin.name)"
        self.assertLess(retirement.index("CallPluginShutdown("), retirement.index(close))
        close_scope = re.search(r"(?=\{\s*auto execution = OwnerExecutionGate::EnterLifecycle\(plugin.execution, OwnerExecutionGate::LifecycleEntry::Cleanup\);\s*if \(!execution \|\| !SafeCloseLibrary)", retirement)
        self.assertIsNotNone(close_scope)
        self.assertIn('return fail("library_close_failed")', extract_braced_body(retirement, close_scope))
        self.assertLess(retirement.index(close), retirement.index("RemoveLoadedPluginOwner(plugin.owner)"))

    def test_unload_cleanup_failure_retains_plugin_without_dlclose(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        retirement = extract_function_body(text, r"bool PluginManager::RetirePlugin\(.*?\)")
        failure = re.search(r"if \(!cleaned\)\s*return fail\(\"registration_cleanup_incomplete\"\)", retirement)
        self.assertIsNotNone(failure)
        self.assertLess(failure.start(), retirement.index("CallPluginShutdown("))
        self.assertLess(failure.start(), retirement.index("SafeCloseLibrary("))
        self.assertIn("if (plugin.shutdownFailed)", retirement)
        self.assertIn('return fail("shutdown_failed_retained_mapping")', retirement)
        self.assertLess(retirement.index("if (plugin.shutdownFailed)"), retirement.index("CallPluginShutdown("))
        self.assertEqual(retirement.count("plugin.shutdownCalled = true"), 1)
        unload = extract_function_body(text, r"void PluginManager::UnloadAll\(\)")
        failure_scope = re.search(r"if \(!RetirePlugin\(plugin,.*?\)\)", unload, re.S)
        self.assertIsNotNone(failure_scope)
        body = extract_braced_body(unload, failure_scope)
        self.assertIn("retainPluginForUnloadRetry", body)
        self.assertIn("publishPartialUnloadStateAndAbort()", body)
        for forbidden in ("SafeCloseLibrary", "RemoveLoadedPluginOwner", "RemovePluginOwnerToken", "ClearPluginOwnerUnloading"):
            self.assertNotIn(forbidden, body)

    def test_partial_unload_progress_publication_does_not_allocate_retry_vector(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"void PluginManager::UnloadAll\(\)")
        match = re.search(
            r"const auto publishPartialUnloadStateAndAbort = \[\&\]\(\) noexcept",
            body,
        )
        self.assertIsNotNone(match)
        publish_body = extract_braced_body(body, match)

        self.assertIn("std::is_nothrow_move_constructible_v<PluginInfo>", publish_body)
        self.assertIn("m_LoadedPlugins.erase(it.base(), m_LoadedPlugins.end())", publish_body)
        self.assertIn("m_LoadedPlugins.insert(", publish_body)
        self.assertIn("std::make_move_iterator(retainedPlugins.rbegin())", publish_body)
        self.assertIn("std::make_move_iterator(retainedPlugins.rend())", publish_body)
        for forbidden in (
            "std::vector<PluginInfo> retryPlugins",
            "retryPlugins.reserve",
            "retryPlugins.insert",
            "m_LoadedPlugins = std::move(retryPlugins)",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, publish_body)

    def test_unloading_owner_rejects_new_registrations_but_allows_unregister(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        registration_body = extract_function_body(
            text,
            r"void\* ResolveOwnerTokenForRegistrationLocked\(.*?\)",
        )
        self.assertLess(
            registration_body.index("IsUnloadingPluginOwnerLocked(owner)"),
            registration_body.index("IsLoadedPluginOwnerLocked(owner)"),
        )
        self.assertIn("rejected callback because the plugin owner is unloading", registration_body)
        self.assertIn("return nullptr", registration_body)

        unregister_body = extract_function_body(
            text,
            r"void\* ResolveOwnerTokenForUnregister\(.*?\)",
        )
        self.assertIn("IsUnloadingPluginOwnerLocked(owner)", unregister_body)
        self.assertLess(
            unregister_body.index("IsUnloadingPluginOwnerLocked(owner)"),
            unregister_body.index("return owner"),
        )

    def test_unloading_owner_state_uses_retained_owner_api_state(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        self.assertIn("bool Unloading = false", text)
        self.assertIn(".Unloading = false", extract_function_body(text, r"uint64_t AddPluginOwnerToken\(.*?\)"))
        self.assertNotIn(
            "UnloadingPluginOwners",
            text,
            "Unloading state must live in retained owner API state so shutdown marking "
            "does not allocate or lose retry state before callback cleanup.",
        )

        mark_body = extract_function_body(text, r"void MarkPluginOwnerUnloading\(.*?\)")
        self.assertIn("PluginOwnerApiStates().find(owner)", mark_body)
        self.assertIn("it->second.Unloading = true", mark_body)
        self.assertNotIn(".insert", mark_body)

        clear_body = extract_function_body(text, r"void ClearPluginOwnerUnloading\(.*?\)")
        self.assertIn("PluginOwnerApiStates().find(owner)", clear_body)
        self.assertIn("it->second.Unloading = false", clear_body)
        self.assertNotIn(".erase", clear_body)

        is_unloading_body = extract_function_body(text, r"bool IsUnloadingPluginOwnerLocked\(.*?\)")
        self.assertIn("PluginOwnerApiStates().find(owner)", is_unloading_body)
        self.assertIn("it->second.Unloading", is_unloading_body)

    def test_plugin_owner_tokens_are_non_zero_and_snapshot_capabilities(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(text, r"uint64_t AddPluginOwnerToken\(.*?\)")

        self.assertIn("if (!owner)", body)
        self.assertIn("return 0", body[: body.index("std::lock_guard<std::mutex>")])
        self.assertIn("token = NextPluginOwnerToken().load", body)
        self.assertIn("uint64_t nextToken = token + 1", body)
        self.assertIn("if (nextToken == 0)", body)
        self.assertIn("nextToken = 1", body)
        self.assertIn("NextPluginOwnerToken().store(nextToken", body)
        self.assertIn("token == 0 || PluginOwnerTokens().find(token) != PluginOwnerTokens().end()", body)
        self.assertIn("PluginOwnerTokens()[token] = owner", body)
        self.assertIn(".Capabilities = capabilities", body)

        load_body = extract_function_body(text, r"void PluginManager::LoadPluginsImpl\(.*?\)")
        self.assertRegex(
            load_body,
            r"AddPluginOwnerToken\(pluginOwner, m_Api\.capabilities, m_ChatDispatcher,\s*"
            r"m_CommandDispatcher, m_PlayerLifecycleDispatcher\)",
        )
        for token in (".Commands = commands", ".PlayerLifecycle = playerLifecycle"):
            self.assertIn(token, body)

    def test_plugin_owner_token_removal_preserves_state_until_last_owner_token(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        helper_body = extract_function_body(
            text,
            r"bool HasPluginOwnerTokenForOwnerLocked\(.*?\)",
        )
        self.assertIn("PluginOwnerTokens().begin()", helper_body)
        self.assertIn("PluginOwnerTokens().end()", helper_body)
        self.assertIn("return item.second == owner", helper_body)

        remove_body = extract_function_body(text, r"void RemovePluginOwnerToken\(.*?\)")
        self.assertIn("void* owner = it->second", remove_body)
        self.assertIn("PluginOwnerTokens().erase(it)", remove_body)
        self.assertIn("if (!HasPluginOwnerTokenForOwnerLocked(owner))", remove_body)
        self.assertIn("PluginOwnerApiStates().erase(owner)", remove_body)
        self.assertNotIn("PluginOwnerApiStates().erase(it->second)", remove_body)
        self.assertLess(
            remove_body.index("PluginOwnerTokens().erase(it)"),
            remove_body.index("if (!HasPluginOwnerTokenForOwnerLocked(owner))"),
            "Owner API state must only be considered stale after the removed token is "
            "gone from PluginOwnerTokens.",
        )

    def test_public_plugin_manager_registration_handles_are_non_zero_and_not_live_reused(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        for function_name, next_id, registrations in (
            (
                "AllocateGameplayPolicyRegistrationIdLocked",
                "NextGameplayPolicyRegistrationId()",
                "GameplayPolicyRegistrations()",
            ),
            (
                "AllocateChatMessageRegistrationIdLocked",
                "NextChatMessageRegistrationId()",
                "ChatMessageRegistrations()",
            ),
        ):
            with self.subTest(function_name=function_name):
                body = extract_function_body(text, rf"uint64_t {function_name}\(\)")
                self.assertIn(f"id = {next_id}++", body)
                self.assertIn(f"if ({next_id} == 0)", body)
                self.assertIn(f"{next_id} = 1", body)
                self.assertIn(f"id == 0 || {registrations}.find(id) != {registrations}.end()", body)
                self.assertIn("return id", body)

    def test_public_owner_token_capability_checks_use_owner_snapshot(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        capability_helpers = {
            r"bool IsGlobalProcessEventCallbackCapabilityEnabledForOwner\(.*?\)": (
                "PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS)",
                "AreGlobalProcessEventCallbacksAllowed()",
            ),
            r"bool IsFilteredProcessEventCallbackCapabilityEnabledForOwner\(.*?\)": (
                "PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS)",
                "AreFilteredProcessEventCallbacksAllowed()",
            ),
            r"bool IsChatMessageEventCapabilityEnabledForOwner\(.*?\)": (
                "PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_CHAT_EVENTS)",
                "AreChatMessageEventsAllowed()",
            ),
            r"bool IsGameplayPolicyEventCapabilityEnabledForOwner\(.*?\)": (
                "PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS)",
            ),
        }
        for pattern, tokens in capability_helpers.items():
            with self.subTest(pattern=pattern):
                body = extract_function_body(text, pattern)
                for token in tokens:
                    self.assertIn(token, body)
                self.assertNotIn("BuildApiCapabilities()", body)
                self.assertNotIn("m_Api.capabilities", body)

        timer_body = extract_function_body(text, r"uint64_t PluginRegisterTimerWithOwnerTokenHandle\(")
        self.assertIn("PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_TIMERS)", timer_body)
        self.assertNotIn("BuildApiCapabilities()", timer_body)
        self.assertNotIn("m_Api.capabilities", timer_body)

    def test_public_timer_api_validates_duration_inputs_before_registration(self) -> None:
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        timer_body = extract_function_body(
            plugin_manager_text,
            r"uint64_t PluginRegisterTimerWithOwnerTokenHandle\(",
        )
        register_index = timer_body.index("RegisterProcessEventCallbackForOwnerToken(")

        validation_tokens = (
            "if ((flags & ~OBELISK_TIMER_FLAG_REPEATING) != 0)",
            "if (delayMs == 0)",
            "TimerManager::IsSupportedDuration(delayMs)",
            "const bool repeating = (flags & OBELISK_TIMER_FLAG_REPEATING) != 0",
            "if (repeating && intervalMs == 0)",
            "TimerManager::IsSupportedDuration(intervalMs)",
            "if (!repeating && intervalMs != 0)",
        )
        for token in validation_tokens:
            with self.subTest(token=token):
                self.assertIn(token, timer_body)
                self.assertLess(
                    timer_body.index(token),
                    register_index,
                    "Public timer ABI wrapper must reject invalid durations before owner "
                    "resolution or TimerManager registration.",
                )

        timer_manager_text = TIMER_MANAGER.read_text(encoding="utf-8")
        register_body = extract_function_body(
            timer_manager_text,
            r"uint64_t TimerManager::Register\(.*?\)",
        )
        self.assertLess(
            register_body.index("IsSupportedDuration(delayMs)"),
            register_body.index("Clock::now() + std::chrono::milliseconds(delayMs)"),
            "TimerManager must validate delay range before converting or adding it to now().",
        )
        self.assertLess(
            register_body.index("IsSupportedDuration(intervalMs)"),
            register_body.index("TimerEntry{"),
            "TimerManager must validate repeating interval range before storing it.",
        )

    def test_timer_owner_cleanup_waits_for_in_flight_callbacks_before_dlclose(self) -> None:
        timer_manager_text = TIMER_MANAGER.read_text(encoding="utf-8")
        cleanup_body = extract_function_body(
            timer_manager_text,
            r"size_t TimerManager::UnregisterCallbacksForOwner\(.*?\)",
        )

        for token in (
            "timer->Cancelled = true",
            "timer->InFlight == 0",
            "t_CurrentTimerOwner == owner",
            "state.Cv.wait_until(lock, deadline",
            "item.second->Owner == owner && item.second->InFlight != 0",
        ):
            with self.subTest(token=token):
                self.assertIn(token, cleanup_body)

        self.assertLess(
            cleanup_body.index("timer->Cancelled = true"),
            cleanup_body.index("state.Cv.wait_until(lock, deadline"),
            "Owner cleanup must cancel plugin timers before waiting for in-flight callbacks.",
        )
        self.assertLess(
            cleanup_body.index("t_CurrentTimerOwner == owner"),
            cleanup_body.index("state.Cv.wait_until(lock, deadline"),
            "Timer self-cleanup must bypass the cross-thread wait to avoid deadlock.",
        )

        self_cleanup_match = re.search(
            r"if \(t_CurrentTimerOwner == owner\)\s*\{(?P<body>.*?)\n\s*\}",
            cleanup_body,
            re.S,
        )
        self.assertIsNotNone(self_cleanup_match)
        self_cleanup_body = self_cleanup_match.group("body")
        self.assertIn("state.Cv.notify_all()", self_cleanup_body)
        self.assertIn("return removed", self_cleanup_body)
        self.assertNotIn("state.Cv.wait", self_cleanup_body)

    def test_unregister_plugin_callbacks_is_per_family_and_cleans_timers(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        body = extract_function_body(
            text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )

        self.assertIn("cleanupFamily", body)
        self.assertIn("TimerManager::Get().UnregisterCallbacksForOwner(owner, deadline)", body)
        self.assertIn("EventManager::Get().UnregisterCallbacksForOwner(owner, deadline)", body)
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
            "m_ChatDispatcher->UnregisterCallbacksForOwner(owner, deadline)",
            "StructureEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)",
            "InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)",
            "ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)",
        )
        for public_token in public_cleanup_tokens:
            with self.subTest(public_token=public_token):
                public_index = body.index(public_token)
                for direct_token in direct_dispatcher_cleanup_tokens:
                    self.assertGreater(public_index, body.index(direct_token))

        chat_unregister_body = extract_function_body(
            text,
            r"bool UnregisterChatMessageRegistrationForOwner\(.*?\)",
        )
        self.assertIn("registration.Dispatcher->UnregisterCallbackForOwner", chat_unregister_body)
        self.assertNotIn("registration.Dispatcher->Unregister(registration.InternalRegistrationId)", chat_unregister_body)

    def test_public_registration_cleanup_fallbacks_check_owner_cleanup_removed_count(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        chat_unregister_body = extract_function_body(
            text,
            r"bool UnregisterChatMessageRegistrationForOwner\(.*?\)",
        )
        self.assertNotIn(
            "(void)registration.Dispatcher->UnregisterCallbacksForOwner(owner)",
            chat_unregister_body,
            "Public chat cleanup fallback must not ignore a zero removed count.",
        )
        self.assertIn(
            "const size_t fallbackRemoved = registration.Dispatcher->UnregisterCallbacksForOwner(owner)",
            chat_unregister_body,
        )
        self.assertIn("if (fallbackRemoved == 0)\n                    return false;", chat_unregister_body)

        gameplay_unregister_body = extract_function_body(
            text,
            r"bool UnregisterGameplayPolicyRegistrationForOwner\(.*?\)",
        )
        for dispatcher, removed_flag in (
            ("StructureEventDispatcher", "structureRemoved"),
            ("InventoryPolicyEventDispatcher", "inventoryRemoved"),
            ("ItemReturnEventDispatcher", "itemReturnRemoved"),
        ):
            with self.subTest(dispatcher=dispatcher):
                self.assertNotIn(
                    f"(void){dispatcher}::Get().UnregisterCallbacksForOwner(owner)",
                    gameplay_unregister_body,
                    "Gameplay policy cleanup fallback must not ignore a zero removed count.",
                )
                self.assertRegex(
                    gameplay_unregister_body,
                    rf"const\s+size_t\s+fallbackRemoved\s*=\s*"
                    rf"{dispatcher}::Get\(\)\.UnregisterCallbacksForOwner\(owner\)",
                )
                self.assertIn(f"{removed_flag} = fallbackRemoved != 0;", gameplay_unregister_body)

    def test_public_registration_tracking_is_reconciled_after_direct_dispatcher_cleanup(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        cleanup_body = extract_function_body(
            text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )
        self.assertIn("bool gameplayPolicyCleanupSucceeded = true", cleanup_body)
        self.assertRegex(cleanup_body, r"\bpublicChatCleanupSucceeded\s*=\s*true")
        self.assertIn("&gameplayPolicyCleanupSucceeded", cleanup_body)
        self.assertIn("&publicChatCleanupSucceeded", cleanup_body)
        self.assertIn(
            "if (!publicChatCleanupSucceeded && chatSucceeded && chatRemoved != 0)",
            cleanup_body,
        )
        self.assertIn(
            "ReconcileChatMessageRegistrationsForOwnerAfterDispatcherCleanup(owner, m_ChatDispatcher)",
            cleanup_body,
        )
        self.assertIn(
            "if (!gameplayPolicyCleanupSucceeded)",
            cleanup_body,
        )
        self.assertIn(
            "ReconcileGameplayPolicyRegistrationsForOwnerAfterDispatcherCleanup(",
            cleanup_body,
        )
        self.assertLess(
            cleanup_body.index("m_ChatDispatcher->UnregisterCallbacksForOwner(owner, deadline)"),
            cleanup_body.index("ReconcileChatMessageRegistrationsForOwnerAfterDispatcherCleanup"),
        )
        self.assertLess(
            cleanup_body.index("ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)"),
            cleanup_body.index("ReconcileGameplayPolicyRegistrationsForOwnerAfterDispatcherCleanup"),
        )

        chat_reconcile_body = extract_function_body(
            text,
            r"void ReconcileChatMessageRegistrationsForOwnerAfterDispatcherCleanup\(.*?\)",
        )
        self.assertIn("it->second.Owner == owner", chat_reconcile_body)
        self.assertIn("it->second.Dispatcher == dispatcher", chat_reconcile_body)
        self.assertIn("ChatMessageRegistrations().erase(it)", chat_reconcile_body)

        gameplay_reconcile_body = extract_function_body(
            text,
            r"void ReconcileGameplayPolicyRegistrationsForOwnerAfterDispatcherCleanup\(.*?\)",
        )
        for token in (
            "it->second.StructureRegistrationId = 0",
            "it->second.InventoryRegistrationId = 0",
            "it->second.ItemReturnRegistrationId = 0",
            "GameplayPolicyRegistrations().erase(it)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, gameplay_reconcile_body)

        gameplay_unregister_body = extract_function_body(
            text,
            r"bool UnregisterGameplayPolicyRegistrationForOwner\(.*?\)",
        )
        self.assertRegex(
            gameplay_unregister_body,
            r"catch\s*\(\.\.\.\)\s*\{\s*"
            r"if\s*\(structureRemoved\s*\|\|\s*inventoryRemoved\s*\|\|\s*itemReturnRemoved\)\s*"
            r"\(void\)syncRemovedDispatcherTracking\(\);\s*"
            r"throw;\s*\}",
        )

    def test_gameplay_policy_partial_failure_retry_keeps_later_family_failure_enabled(self) -> None:
        tests_text = PLUGIN_MANAGER_TESTS.read_text(encoding="utf-8")
        body = extract_function_body(
            tests_text,
            r"void TestUnloadAllRetriesGameplayPolicyCleanupAfterPartialPublicBackingFailure\(.*?\)",
        )
        first_unload = body.index("manager.UnloadAll();")
        second_unload = body.index("manager.UnloadAll();", first_unload + len("manager.UnloadAll();"))
        clear_failure = body.index("SetPublicGameplayPolicyInventoryUnregisterFailureForTesting(false)")
        self.assertLess(
            second_unload,
            clear_failure,
            "The partial gameplay cleanup retry must prove stale public tracking is gone "
            "before clearing the injected later-family failure.",
        )
        self.assertIn(
            "gameplay-policy partial retry accepted a new owner-token callback while unloading",
            body,
        )

    def test_public_owner_token_handle_apis_have_owner_cleanup_backstops(self) -> None:
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )

        owner_token_handle_fields = {
            field
            for field in obelisk_api_field_names(api_header)
            if field.startswith("Register") and field.endswith("WithOwnerTokenHandle")
        }
        expected_fields = set(OWNER_TOKEN_HANDLE_CLEANUP_BACKSTOPS)
        self.assertEqual(
            sorted(owner_token_handle_fields - expected_fields),
            [],
            "New public owner-token handle registration APIs must declare their "
            "PluginManager owner-cleanup backstop before ABI exposure.",
        )
        self.assertEqual(sorted(expected_fields - owner_token_handle_fields), [])

        for api_field, cleanup_token in OWNER_TOKEN_HANDLE_CLEANUP_BACKSTOPS.items():
            with self.subTest(api_field=api_field):
                assert_cleanup_token_uses_cleanup_family(self, cleanup_body, cleanup_token)

    def test_public_owner_token_registration_apis_are_handle_based_or_legacy_wrappers(self) -> None:
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")

        owner_token_register_fields = {
            field
            for field in obelisk_api_function_field_names(api_header)
            if field.startswith("Register") and "WithOwnerToken" in field
        }
        expected_fields = set(OWNER_TOKEN_HANDLE_CLEANUP_BACKSTOPS) | set(
            LEGACY_VOID_OWNER_TOKEN_REGISTRATION_WRAPPERS
        )
        self.assertEqual(
            sorted(owner_token_register_fields - expected_fields),
            [],
            "New public owner-token registration APIs must be handle-returning and covered "
            "by PluginManager owner cleanup, or explicitly documented as legacy wrappers.",
        )
        self.assertEqual(sorted(expected_fields - owner_token_register_fields), [])

        for api_field, wrapper_call in LEGACY_VOID_OWNER_TOKEN_REGISTRATION_WRAPPERS.items():
            with self.subTest(api_field=api_field):
                body = extract_function_body(
                    plugin_manager_text,
                    rf"void Plugin{api_field}\(.*?\)",
                )
                self.assertIn(wrapper_call, body)
                self.assertNotIn("EventManager::Get().Register", body)

    def test_plugin_manager_uses_owner_scoped_unregister_for_event_dispatchers(self) -> None:
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        dispatcher_classes = event_dispatcher_class_names()

        # The native dispatchers intentionally name their owner-scoped method
        # Unregister(owner,id). Exempt only these two validated wrapper bodies,
        # preserving the blanket denial of bare unregister through other aliases.
        for wrapper, owner_registry in NATIVE_OWNER_UNREGISTER_APIS.items():
            body = extract_function_body(plugin_manager_text, rf"bool {wrapper}\(.*?\)")
            with self.subTest(wrapper=wrapper):
                self.assertIn("ResolveOwnerTokenForUnregister", body)
                self.assertIn("if (!owner)", body)
                self.assertIn(f"{owner_registry}(owner)", body)
                self.assertEqual(
                    re.findall(r"->\s*Unregister\s*\(([^)]*)\)", body),
                    ["owner, registrationId"],
                    "Native command/lifecycle unregister must include the resolved owner and handle.",
                )
                self.assertIn("SafeLogErrorNoThrow", body)
                self.assertIn("catch (...)", body)
            plugin_manager_text = plugin_manager_text.replace(body, "", 1)

        self.assertNotRegex(
            plugin_manager_text,
            r"->\s*Unregister\s*\(",
            "PluginManager pointer unregister calls must stay owner-scoped; this catches "
            "dispatcher aliases that would bypass EventDispatcher::UnregisterCallbackForOwner.",
        )

        for dispatcher in sorted(dispatcher_classes):
            with self.subTest(dispatcher=dispatcher):
                self.assertNotRegex(
                    plugin_manager_text,
                    rf"\b{dispatcher}::Get\(\)\.Unregister\s*\(",
                    "PluginManager must use owner-scoped dispatcher unregister so cleanup "
                    "failures stay attributable to a plugin owner.",
                )

        dispatcher_variables: set[str] = set()
        dispatcher_variables.update(
            re.findall(
                r"\b(?:const\s+)?auto\s*(?:[&*]\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
                r"(?:&\s*)?(?:\*\s*)?(?:m_ChatDispatcher|\w+EventDispatcher::Get\(\))",
                plugin_manager_text,
            )
        )
        for dispatcher in dispatcher_classes:
            dispatcher_variables.update(
                re.findall(
                    rf"\b{dispatcher}\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\b",
                    plugin_manager_text,
                )
            )
            dispatcher_variables.update(
                re.findall(
                    rf"\b{dispatcher}\s*&\s*([A-Za-z_][A-Za-z0-9_]*)\b",
                    plugin_manager_text,
                )
            )

        for variable in sorted(dispatcher_variables):
            with self.subTest(dispatcher_variable=variable):
                self.assertNotRegex(
                    plugin_manager_text,
                    rf"\b{re.escape(variable)}\s*->\s*Unregister\s*\(",
                    "PluginManager must not call bare EventDispatcher::Unregister through "
                    "dispatcher pointers.",
                )
                self.assertNotRegex(
                    plugin_manager_text,
                    rf"\b{re.escape(variable)}\s*\.\s*Unregister\s*\(",
                    "PluginManager must not call bare EventDispatcher::Unregister through "
                    "dispatcher references.",
                )

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
        self.assertIn("GameplayPolicyRegistrations().erase(it)", unregister_owner_body)
        self.assertNotIn("UnregisterGameplayPolicyRegistrationForOwner(", unregister_owner_body)
        self.assertNotIn("UnregisterCallbackForOwner(", unregister_owner_body)
        self.assertIn("throw std::runtime_error", unregister_owner_body)
        self.assertLess(
            unregister_body.index("registration.InventoryRegistrationId"),
            unregister_body.index("GameplayPolicyRegistrations().erase(it)"),
        )
        self.assertLess(
            unregister_body.index("registration.ItemReturnRegistrationId"),
            unregister_body.index("GameplayPolicyRegistrations().erase(it)"),
        )

        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )
        for token in (
            "UnregisterGameplayPolicyRegistrationsForOwner(owner)",
            "InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)",
            "ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)",
            "PlayerPrincipalEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)",
        ):
            with self.subTest(owner_cleanup_token=token):
                self.assertIn(token, cleanup_body)
        public_cleanup_index = cleanup_body.index("UnregisterGameplayPolicyRegistrationsForOwner(owner)")
        self.assertGreater(
            public_cleanup_index,
            cleanup_body.index("InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)"),
        )
        self.assertGreater(
            public_cleanup_index,
            cleanup_body.index("ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline)"),
        )

    def test_plugin_owner_cleanup_covers_each_plugin_facing_owner_registry(self) -> None:
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )

        registry_classes = owner_cleanup_registry_classes()

        cleaned_registries = cleaned_owner_registry_classes(cleanup_body)

        missing = sorted(
            registry_classes
            - cleaned_registries
            - set(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS)
        )
        self.assertEqual(
            missing,
            [],
            "New plugin-facing owner-scoped callback registries must be added to "
            "PluginManager::UnregisterPluginCallbacks, or explicitly documented in "
            "COPIED_DISPATCHER_CLEANUP_EXCEPTIONS while still internal/test-only.",
        )

        stale_exceptions = sorted(
            set(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS) - registry_classes
        )
        self.assertEqual(stale_exceptions, [])
        for dispatcher, reason in COPIED_DISPATCHER_CLEANUP_EXCEPTIONS.items():
            with self.subTest(dispatcher=dispatcher):
                self.assertIn(dispatcher, registry_classes)
                self.assertIn("internal/test-only", reason)
                self.assertIn("non-public", reason)
                self.assertIn("not plugin-facing", reason)
                self.assertIn("PluginManager owner cleanup", reason)
                self.assertNotIn(dispatcher, cleaned_registries)

    def test_new_event_dispatcher_families_require_owner_cleanup_decision(self) -> None:
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )

        dispatcher_classes = event_dispatcher_class_names()
        registry_classes = owner_cleanup_registry_classes()
        missing_owner_cleanup = sorted(dispatcher_classes - registry_classes)
        self.assertEqual(
            missing_owner_cleanup,
            [],
            "New EventDispatcher families need an owner-scoped cleanup contract before "
            "they can be treated as safe around plugin unload.",
        )

        cleaned_dispatchers = cleaned_dispatcher_classes(cleanup_body)
        undecided_dispatchers = sorted(
            dispatcher_classes - cleaned_dispatchers - set(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS)
        )
        self.assertEqual(
            undecided_dispatchers,
            [],
            "New EventDispatcher families must either be wired into "
            "PluginManager::UnregisterPluginCallbacks or listed as an explicit "
            "internal/test-only exception with blocked public ABI tokens.",
        )

    def test_current_copied_dispatcher_owner_cleanup_parity_is_explicit(self) -> None:
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )
        dispatcher_classes = event_dispatcher_class_names()
        cleaned_dispatchers = cleaned_dispatcher_classes(cleanup_body)

        implicit_cleanup_dispatchers = sorted(
            cleaned_dispatchers
            - set(COPIED_DISPATCHER_PLUGIN_MANAGER_CLEANUP_TOKENS)
            - set(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS)
        )
        self.assertEqual(
            implicit_cleanup_dispatchers,
            [],
            "Every copied dispatcher cleaned by PluginManager must be listed in "
            "COPIED_DISPATCHER_PLUGIN_MANAGER_CLEANUP_TOKENS so cleanup-family "
            "exception handling stays guarded.",
        )

        for dispatcher, cleanup_token in COPIED_DISPATCHER_PLUGIN_MANAGER_CLEANUP_TOKENS.items():
            with self.subTest(dispatcher=dispatcher, decision="PluginManager cleanup"):
                self.assertIn(dispatcher, dispatcher_classes)
                self.assertNotIn(dispatcher, COPIED_DISPATCHER_CLEANUP_EXCEPTIONS)
                assert_cleanup_token_uses_cleanup_family(self, cleanup_body, cleanup_token)

        for dispatcher in sorted(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS):
            cleanup_token = f"{dispatcher}::Get().UnregisterCallbacksForOwner(owner, deadline)"
            with self.subTest(dispatcher=dispatcher, decision="internal/test-only exception"):
                self.assertIn(dispatcher, dispatcher_classes)
                self.assertNotIn(cleanup_token, cleanup_body)

    def test_plugin_facing_event_dispatchers_require_plugin_manager_cleanup(self) -> None:
        api_header = strip_c_comments(OBELISK_API_HEADER.read_text(encoding="utf-8"))
        plugin_manager_text = strip_c_comments(PLUGIN_MANAGER.read_text(encoding="utf-8"))
        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )

        public_tokens = public_plugin_surface_tokens(api_header, plugin_manager_text)
        cleaned_dispatchers = cleaned_dispatcher_classes(cleanup_body)
        cleanup_omissions: list[str] = []
        stale_exclusions: list[str] = []

        for dispatcher in sorted(event_dispatcher_class_names()):
            matched_tokens = sorted(public_plugin_surface_tokens_for_dispatcher(dispatcher, public_tokens))
            if not matched_tokens:
                continue

            with self.subTest(dispatcher=dispatcher):
                if dispatcher not in cleaned_dispatchers:
                    cleanup_omissions.append(
                        f"{dispatcher}: public surface tokens {', '.join(matched_tokens)}"
                    )
                if dispatcher in COPIED_DISPATCHER_CLEANUP_EXCEPTIONS:
                    stale_exclusions.append(
                        f"{dispatcher}: public surface tokens {', '.join(matched_tokens)}"
                    )

        self.assertEqual(
            cleanup_omissions,
            [],
            "Any dispatcher with a public registration/capability surface must be wired "
            "through PluginManager::UnregisterPluginCallbacks.",
        )
        self.assertEqual(
            stale_exclusions,
            [],
            "A dispatcher cannot remain an internal/test-only cleanup exclusion after "
            "public registration or capability tokens appear.",
        )

    def test_internal_test_only_dispatchers_are_explicitly_non_plugin_facing(self) -> None:
        api_header = strip_c_comments(OBELISK_API_HEADER.read_text(encoding="utf-8"))
        plugin_manager_text = strip_c_comments(PLUGIN_MANAGER.read_text(encoding="utf-8"))
        public_tokens = public_plugin_surface_tokens(api_header, plugin_manager_text)

        production_files = [
            *sorted((REPO_ROOT / "core").glob("*.cpp")),
            *sorted((REPO_ROOT / "hooks").glob("*.cpp")),
            *sorted((REPO_ROOT / "ue").glob("*.cpp")),
        ]

        stale_internal_markers = sorted(set(INTERNAL_TEST_ONLY_DISPATCHERS) - event_dispatcher_class_names())
        self.assertEqual(stale_internal_markers, [])

        for dispatcher, reason in INTERNAL_TEST_ONLY_DISPATCHERS.items():
            with self.subTest(dispatcher=dispatcher):
                self.assertIn("internal/test-only", reason)
                self.assertIn("non-public", reason)
                self.assertIn("not plugin-facing", reason)
                self.assertEqual(
                    sorted(public_plugin_surface_tokens_for_dispatcher(dispatcher, public_tokens)),
                    [],
                    "Internal/test-only dispatchers must not gain public ABI fields, "
                    "PluginManager C wrappers, or capability bits.",
                )

                register_call = f"{dispatcher}::Get().Register("
                production_registrations = [
                    str(path.relative_to(REPO_ROOT))
                    for path in production_files
                    if register_call in strip_c_comments(path.read_text(encoding="utf-8"))
                ]
                self.assertEqual(
                    production_registrations,
                    [],
                    "Internal/test-only dispatchers must not gain production registration "
                    "calls until promotion adds public ABI, owner cleanup, and SDK tests.",
                )

    def test_internal_test_only_dispatcher_exceptions_are_not_public_abi_or_plugin_manager_wired(self) -> None:
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")
        plugin_manager_text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        cleanup_body = extract_function_body(
            plugin_manager_text,
            r"bool PluginManager::UnregisterPluginCallbacks\(.*?\)",
        )
        cleaned_dispatchers = cleaned_dispatcher_classes(cleanup_body)

        missing_exception_token_sets = sorted(
            set(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS) - set(COPIED_DISPATCHER_PUBLIC_ABI_TOKENS)
        )
        self.assertEqual(
            missing_exception_token_sets,
            [],
            "Every internal/test-only copied dispatcher cleanup exception must name the "
            "public ABI and PluginManager wiring tokens that stay blocked while owner "
            "cleanup is absent.",
        )

        for dispatcher in sorted(COPIED_DISPATCHER_CLEANUP_EXCEPTIONS):
            blocked_tokens = COPIED_DISPATCHER_PUBLIC_ABI_TOKENS[dispatcher]
            with self.subTest(dispatcher=dispatcher):
                self.assertNotIn(
                    dispatcher,
                    cleaned_dispatchers,
                    "Dispatcher should be removed from cleanup exceptions once PluginManager "
                    "owner cleanup covers it.",
                )
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
                            "Internal/test-only dispatcher public ABI must stay absent until the "
                            "dispatcher is covered by PluginManager owner cleanup.",
                        )
                        self.assertNotIn(
                            token,
                            plugin_manager_text,
                            "Internal/test-only dispatcher PluginManager wiring must stay absent "
                            "until dispatcher owner cleanup is explicit.",
                        )

    def test_non_promoted_copied_dispatcher_tokens_are_absent_from_public_abi(self) -> None:
        api_header = strip_c_comments(OBELISK_API_HEADER.read_text(encoding="utf-8"))

        dispatcher_classes: set[str] = set()
        for header in CORE_DIR.glob("*EventDispatcher.h"):
            header_text = header.read_text(encoding="utf-8")
            if "UnregisterCallbacksForOwner" not in header_text:
                continue
            match = re.search(r"class\s+(\w+EventDispatcher)\b", header_text)
            self.assertIsNotNone(match, f"{header} has owner cleanup but no dispatcher class")
            dispatcher_classes.add(match.group(1))

        stale_token_sets = sorted(set(COPIED_DISPATCHER_PUBLIC_ABI_TOKENS) - dispatcher_classes)
        self.assertEqual(stale_token_sets, [])

        for dispatcher, blocked_tokens in COPIED_DISPATCHER_PUBLIC_ABI_TOKENS.items():
            with self.subTest(dispatcher=dispatcher):
                for token in blocked_tokens:
                    with self.subTest(dispatcher=dispatcher, token=token):
                        self.assertNotIn(
                            token,
                            api_header,
                            "Non-promoted copied dispatcher public ABI tokens must stay absent "
                            "until promotion adds ABI, lifecycle cleanup coverage, and SDK tests.",
                        )

    def test_plugin_manager_does_not_wire_blocked_public_sdk_surfaces(self) -> None:
        api_header, plugin_manager_text = blocked_surface_scan_text(
            OBELISK_API_HEADER.read_text(encoding="utf-8"),
            PLUGIN_MANAGER.read_text(encoding="utf-8"),
        )

        offenders: list[str] = []
        for family, tokens in BLOCKED_PLUGIN_MANAGER_PUBLIC_WIRING_TOKENS.items():
            for token in tokens:
                with self.subTest(family=family, token=token):
                    if token in api_header:
                        offenders.append(f"ObeliskApi.h: {family}: {token}")
                    if token in plugin_manager_text:
                        offenders.append(f"PluginManager.cpp: {family}: {token}")

        self.assertEqual(
            offenders,
            [],
            "Blocked SDK lanes must not appear in the public API table or PluginManager "
            "C-wrapper/capability wiring until a deliberate promotion adds ABI, owner "
            "cleanup, and SDK consumer tests.",
        )

    def test_native_prototype_exemptions_require_the_complete_exact_table(self) -> None:
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")
        manager = PLUGIN_MANAGER.read_text(encoding="utf-8")
        self.assertTrue(native_prototype_symbols_for_header(api_header))
        for field in NATIVE_PROTOTYPE_API_FIELDS:
            with self.subTest(missing_exact_field=field):
                incomplete = api_header.replace(field, field + "AuthorityAlias", 1)
                self.assertFalse(native_prototype_symbols_for_header(incomplete))
                scanned_header, scanned_manager = blocked_surface_scan_text(incomplete, manager)
                self.assertIn("OBELISK_API_CAPABILITY_COMMAND_REPLIES", scanned_header)
                self.assertIn("PluginRegisterCommandWithOwnerTokenHandle", scanned_manager)

    def test_native_prototype_exemptions_preserve_blocked_authority_names(self) -> None:
        api_header = OBELISK_API_HEADER.read_text(encoding="utf-8")
        manager = PLUGIN_MANAGER.read_text(encoding="utf-8")
        blocked = ("RegisterCommandAuthority", "RegisterAdminCommand", "ResolvePlayerPrincipal")
        extra = "\n".join(f"void {name}();" for name in blocked)
        scanned_header, scanned_manager = blocked_surface_scan_text(api_header + extra, manager + extra)
        for token in blocked:
            with self.subTest(blocked_token=token):
                self.assertIn(token, scanned_header)
                self.assertIn(token, scanned_manager)

    def test_runtime_callback_scopes_precede_plugin_entry_and_restore_outer_scope(self) -> None:
        scope_header = (CORE_DIR / "GameplayCallbackScope.h").read_text(encoding="utf-8")
        self.assertIn("m_CountsDepth(mode == TrackingMode::Gameplay)", scope_header)
        self.assertRegex(scope_header, r"if \(m_CountsDepth\)\s*\+\+Depth\(m_Family\)")
        self.assertIn("CurrentStorage() = this", scope_header)
        self.assertIn("CurrentStorage() = m_Previous", scope_header)
        self.assertRegex(scope_header, r"if \(m_CountsDepth\)\s*--Depth\(m_Family\)")

        for dispatcher, family in (("CommandDispatcher", "Command"),
                                   ("PlayerLifecycleDispatcher", "PlayerLifecycle")):
            body = extract_function_body(
                (CORE_DIR / f"{dispatcher}.cpp").read_text(encoding="utf-8"),
                rf"size_t {dispatcher}::Dispatch\(.*?\)",
            )
            token = f"GameplayCallbackScope callbackScope(GameplayCallbackFamily::{family})"
            with self.subTest(dispatcher=dispatcher):
                self.assertIn(token, body)
                self.assertLess(body.index(token), body.index("registration->Callback(&event"))
        command_text = (CORE_DIR / "CommandDispatcher.cpp").read_text(encoding="utf-8")
        dispatch = extract_function_body(command_text, r"size_t CommandDispatcher::Dispatch\(.*?\)")
        self.assertLess(dispatch.index("invocation.CallbackScope = &callbackScope"),
                        dispatch.index("registration->Callback(&event"))
        for operation, use in (("Reply", "invocation->Backend("),
                               ("GetPlayer", "*out = *invocation->Player")):
            body = extract_function_body(command_text, rf"bool CommandDispatcher::{operation}\(.*?\)")
            check = "GameplayCallbackScope::Current() != invocation->CallbackScope"
            self.assertIn(check, body)
            self.assertLess(body.index(check), body.index(use))

        event_text = (CORE_DIR / "EventManager.cpp").read_text(encoding="utf-8")
        callback_bodies = [
            extract_braced_body(event_text, match)
            for match in re.finditer(r"(?:bool|void) EventManager::Trigger(?:Pre|Post)ProcessEvent\([^)]*\)", event_text)
        ]
        callback_bodies = [body for body in callback_bodies if "snapshot.callback(" in body]
        self.assertEqual(len(callback_bodies), 4)
        for body in callback_bodies:
            self.assertRegex(body, r"GameplayCallbackScope callbackScope\(GameplayCallbackFamily::ProcessEvent,\s*"
                                  r"GameplayCallbackScope::TrackingMode::CurrentOnly\)")
            self.assertLess(body.index("GameplayCallbackScope callbackScope"), body.index("snapshot.callback("))
        timer = extract_function_body(TIMER_MANAGER.read_text(encoding="utf-8"), r"void WorkerLoop\(\)")
        self.assertRegex(timer, r"GameplayCallbackScope callbackScope\(GameplayCallbackFamily::Timer,\s*"
                               r"GameplayCallbackScope::TrackingMode::CurrentOnly\)")
        self.assertLess(timer.index("GameplayCallbackScope callbackScope"), timer.index("callback(timerId, userData)"))

    def test_side_lane_names_have_no_plugin_facing_callback_fields(self) -> None:
        api_header = strip_c_comments(OBELISK_API_HEADER.read_text(encoding="utf-8"))
        plugin_manager_text = strip_c_comments(PLUGIN_MANAGER.read_text(encoding="utf-8"))
        side_lane_name_re = re.compile(
            r"(?:Transfer|ScriptStruct|Payload|BAccept|Buff|BuffStatus|Dino|DinoScalar)"
        )

        public_callback_fields = [
            field
            for field in obelisk_api_function_field_names(api_header)
            if field.startswith(("Register", "Unregister"))
        ]
        plugin_boundary_wrappers = re.findall(
            r"\b(?:uint64_t|void|bool)\s+(Plugin(?:Register|Unregister)[A-Za-z0-9_]*)\s*\(",
            plugin_manager_text,
        )
        capability_tokens = sorted(set(re.findall(r"\bOBELISK_API_CAPABILITY_[A-Z0-9_]+", api_header)))

        offenders = [
            f"ObeliskApi field: {field}"
            for field in public_callback_fields
            if side_lane_name_re.search(field)
        ]
        offenders.extend(
            f"PluginManager wrapper: {function_name}"
            for function_name in plugin_boundary_wrappers
            if side_lane_name_re.search(function_name)
        )
        offenders.extend(
            f"ObeliskApi capability: {capability}"
            for capability in capability_tokens
            if side_lane_name_re.search(capability)
        )

        self.assertEqual(
            offenders,
            [],
            "Transfer ScriptStruct/payload, Buff status, and Dino scalar side-lane names "
            "must not gain public callback fields, C wrappers, or capability bits.",
        )

    def test_player_principal_dispatcher_registration_stays_test_only_until_promotion(self) -> None:
        production_files = [
            *sorted((REPO_ROOT / "core").glob("*.cpp")),
            *sorted((REPO_ROOT / "hooks").glob("*.cpp")),
            *sorted((REPO_ROOT / "ue").glob("*.cpp")),
        ]
        offenders: list[str] = []
        for path in production_files:
            text = strip_c_comments(path.read_text(encoding="utf-8"))
            if "PlayerPrincipalEventDispatcher::Get().Register(" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(
            offenders,
            [],
            "PlayerPrincipalEventDispatcher registration is internal/test-only until "
            "player identity promotion adds public ABI, owner cleanup, and SDK tests.",
        )

    def test_event_dispatcher_owner_cleanup_failures_propagate_to_plugin_manager(self) -> None:
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")
            if "UnregisterCallbacksForOwner" not in text:
                continue
            body = extract_function_body(
                text,
                r"size_t \w+EventDispatcher::UnregisterCallbacksForOwner\(\s*void\* owner,\s*(?:OwnerExecutionGate::Clock|std::chrono::steady_clock)::time_point deadline\)",
            )
            for catch_body in re.findall(r"catch\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*\}", body, re.S):
                with self.subTest(source=source.name, catch_body=catch_body.strip()[:80]):
                    self.assertIn("throw", catch_body)
                    self.assertNotRegex(catch_body, r"\breturn\s+0\s*;")

    def test_player_principal_owner_cleanup_setup_failures_keep_retry_state(self) -> None:
        text = (CORE_DIR / "PlayerPrincipalEventDispatcher.cpp").read_text(encoding="utf-8")
        body = extract_function_body(
            text,
            r"size_t PlayerPrincipalEventDispatcher::UnregisterCallbacksForOwner\(\s*void\* owner,\s*(?:OwnerExecutionGate::Clock|std::chrono::steady_clock)::time_point deadline\)",
        )

        self.assertIn(
            "const auto retainPendingOwnerCleanupFailures",
            body,
            "PlayerPrincipalEventDispatcher owner cleanup must keep a no-loss path for "
            "pending DestroyUserData retry records if setup fails after taking them.",
        )
        retain_tokens = {
            "RetainFailedOwnerDestroySubscriptions(owner, removed, retainedFailure)": (
                "pending retry records must retain their stored failure so the next "
                "PluginManager cleanup attempt still fails visibly"
            ),
            "RetainFailedOwnerDestroySubscriptions(owner, currentRemoved)": (
                "newly removed callbacks must be retained when setup fails before "
                "DestroyUserData can run"
            ),
        }
        for token, message in retain_tokens.items():
            with self.subTest(token=token):
                self.assertIn(token, body, message)
        catch_bodies = re.findall(r"catch\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*\}", body, re.S)
        self.assertTrue(catch_bodies, "owner cleanup must keep visible catch blocks.")
        for catch_body in catch_bodies:
            with self.subTest(catch_body=catch_body.strip()[:80]):
                self.assertRegex(
                    catch_body,
                    r"retainPendingOwnerCleanupFailures\(\);|"
                    r"RetainFailedOwnerDestroySubscriptions\(owner, deferredFailures, std::current_exception\(\)\);",
                    "Every cleanup catch must retain its own pending/deferred records before rethrowing.",
                )
                self.assertIn("throw", catch_body)

    def test_plugin_manager_player_principal_retry_setup_failure_test_has_test_hooks(self) -> None:
        tests_text = PLUGIN_MANAGER_TESTS.read_text(encoding="utf-8")
        test_body = extract_function_body(
            tests_text,
            r"void TestUnloadAllRetainsPlayerPrincipalDestroyRetryAfterOwnerCleanupSetupFailure\(\)",
        )

        for token in (
            ".registerPlayerPrincipalCallback = true",
            ".failDestroyUserDataOnce = true",
            "PlayerPrincipalEventDispatcher::Get().FailNextFailedOwnerDestroyRetrySetupForTesting()",
            "playerPrincipalSubscriptionsAtClose == 0",
        ):
            with self.subTest(token=token):
                self.assertIn(token, test_body)

        self.assertIn(
            "TestUnloadAllRetainsPlayerPrincipalDestroyRetryAfterOwnerCleanupSetupFailure();",
            tests_text,
        )

        cmake_text = CMAKE_LISTS.read_text(encoding="utf-8")
        compile_definitions = re.search(
            r"target_compile_definitions\(\s*plugin_manager_tests\b(?P<body>.*?)\)",
            cmake_text,
            re.S,
        )
        self.assertIsNotNone(compile_definitions)
        self.assertIn(
            "OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS=1",
            compile_definitions.group("body"),
            "plugin_manager_tests must compile the player-principal dispatcher test hook "
            "used by the owner-cleanup setup-failure parity test.",
        )

    def test_copied_dispatcher_owner_cleanup_setup_failures_keep_retry_state(self) -> None:
        for dispatcher in (
            "ChatEventDispatcher",
            "StructureEventDispatcher",
            "MissionCopiedBoolEventDispatcher",
            "InventoryPolicyEventDispatcher",
            "ItemReturnEventDispatcher",
            "PlayerPrincipalEventDispatcher",
        ):
            with self.subTest(dispatcher=dispatcher):
                text = (CORE_DIR / f"{dispatcher}.cpp").read_text(encoding="utf-8")
                header = (CORE_DIR / f"{dispatcher}.h").read_text(encoding="utf-8")
                body = extract_function_body(
                    text,
                    rf"size_t {dispatcher}::UnregisterCallbacksForOwner\(\s*void\* owner,\s*(?:OwnerExecutionGate::Clock|std::chrono::steady_clock)::time_point deadline\)",
                )

                self.assertIn("FailNextFailedOwnerDestroyRetrySetupForTesting", header)
                self.assertIn("m_FailNextFailedOwnerDestroyRetrySetupForTesting", body)
                self.assertIn("const auto retainPendingOwnerCleanupFailures", body)
                self.assertRegex(
                    body,
                    r"RetainFailedOwnerDestroySubscriptions\(owner, removed(?:, \w+)?\)",
                )
                self.assertIn("RetainFailedOwnerDestroySubscriptions(owner, currentRemoved)", body)
                catch_bodies = re.findall(r"catch\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*\}", body, re.S)
                self.assertTrue(catch_bodies, "owner cleanup must keep visible catch blocks.")
                for catch_body in catch_bodies:
                    self.assertRegex(
                    catch_body,
                    r"retainPendingOwnerCleanupFailures\(\);|"
                    r"RetainFailedOwnerDestroySubscriptions\(owner, deferredFailures, std::current_exception\(\)\);",
                    "Every cleanup catch must retain its own pending/deferred records before rethrowing.",
                )
                    self.assertIn("throw", catch_body)

    def test_deferred_event_dispatchers_use_fallback_failure_recording(self) -> None:
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")
            if "TakeDeferredDestroyFailures" not in text:
                continue

            dispatcher = source.stem
            header = (CORE_DIR / f"{dispatcher}.h").read_text(encoding="utf-8")
            finish_body = extract_function_body(
                text,
                rf"void {dispatcher}::FinishDispatch\(\)",
            )

            with self.subTest(dispatcher=dispatcher):
                self.assertIn("m_HasFallbackDeferredDestroyFailure", header)
                self.assertIn("m_FallbackDeferredDestroyFailure", header)
                self.assertIn("ReserveDeferredDestroyFailureSlots", text)
                self.assertIn("RecordDeferredDestroyFailure", text)
                self.assertIn("RecordDeferredDestroyFailure(", finish_body)
                self.assertNotIn(
                    "std::vector<DeferredDestroyFailure> failures",
                    finish_body,
                    "deferred cleanup failures must be recorded through the fallback-aware helper",
                )

    def test_deferred_event_dispatcher_owner_cleanup_uses_batch_id(self) -> None:
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")
            if "TakeDeferredDestroyFailure" not in text and "TakeDeferredDestroyFailures" not in text:
                continue
            body = extract_function_body(
                text,
                r"size_t \w+EventDispatcher::UnregisterCallbacksForOwner\(\s*void\* owner,\s*(?:OwnerExecutionGate::Clock|std::chrono::steady_clock)::time_point deadline\)",
            )
            with self.subTest(source=source.name):
                self.assertIn("std::exception_ptr deferredFailure", body)
                self.assertIn("uint64_t cleanupBatchId = 0", body)
                self.assertIn("cleanupBatchId = m_NextCleanupBatchId++", body)
                self.assertRegex(
                    body,
                    r"QueueOrDestroyRemovedSubscriptions\((?:\w+, )?(?:removed|currentRemoved), lock, cleanupBatchId(?:, \w+)?\)",
                )
                self.assertTrue(
                    "deferredFailure = TakeDeferredDestroyFailure(cleanupBatchId)" in body or
                    "TakeDeferredDestroyFailures(cleanupBatchId, deferredFailure)" in body,
                    "owner cleanup must retrieve deferred cleanup failures",
                )
                self.assertTrue(
                    "std::rethrow_exception(deferredFailure)" in body or
                    "std::rethrow_exception(cleanupFailure)" in body,
                    "owner cleanup must rethrow retained/deferred cleanup failures",
                )

    def test_deferred_event_dispatcher_granular_cleanup_failures_are_visible(self) -> None:
        signatures = (
            r"bool \w+EventDispatcher::Unregister\(uint64_t registrationId\)",
            r"bool \w+EventDispatcher::UnregisterCallbackForOwner\(void\* owner, uint64_t registrationId\)",
        )
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")
            if "TakeDeferredDestroyFailure" not in text and "TakeDeferredDestroyFailures" not in text:
                continue
            for signature in signatures:
                try:
                    body = extract_function_body(text, signature)
                except AssertionError:
                    continue
                with self.subTest(source=source.name, signature=signature):
                    self.assertIn("std::exception_ptr deferredFailure", body)
                    self.assertIn("uint64_t cleanupBatchId = 0", body)
                    self.assertRegex(
                        body,
                        r"QueueOrDestroyRemovedSubscriptions\((?:\w+, )?removed, lock, cleanupBatchId(?:, \w+)?\)",
                    )
                    self.assertTrue(
                        "deferredFailure = TakeDeferredDestroyFailure(cleanupBatchId)" in body or
                        "TakeDeferredDestroyFailures(cleanupBatchId, deferredFailure)" in body,
                        "granular cleanup must retrieve deferred cleanup failures",
                    )
                    self.assertTrue(
                        "std::rethrow_exception(deferredFailure)" in body or
                        "std::rethrow_exception(cleanupFailure)" in body,
                        "granular cleanup must rethrow retained/deferred cleanup failures",
                    )

    def test_owner_granular_event_dispatchers_retain_cleanup_failures_for_owner_retry(self) -> None:
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")
            if "UnregisterCallbackForOwner" not in text:
                continue
            body = extract_function_body(
                text,
                r"bool \w+EventDispatcher::UnregisterCallbackForOwner\(void\* owner, uint64_t registrationId\)",
            )
            with self.subTest(source=source.name):
                self.assertIn("std::exception_ptr cleanupFailure", body)
                self.assertIn("DestroyRemovedSubscriptionsForOwner(owner, removed, cleanupFailure)", body)
                self.assertIn("RetainFailedOwnerDestroySubscriptions(owner, failed)", body)
                self.assertIn("std::rethrow_exception(cleanupFailure)", body)

    def test_deferred_event_dispatcher_finish_dispatch_does_not_throw_before_notify(self) -> None:
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")
            if "m_DeferredDestroyFailures" not in text:
                continue
            body = extract_function_body(text, r"void \w+EventDispatcher::FinishDispatch\(\)")
            with self.subTest(source=source.name):
                captures_with_bulk_vector = (
                    "failures.push_back({item.CleanupBatchId, std::current_exception()})" in body or
                    "failures.push_back({item.CleanupBatchId, item.Subscription, std::current_exception()})" in body
                )
                captures_with_record_helper = (
                    "RecordDeferredDestroyFailure(\n"
                    "                    item.CleanupBatchId,\n"
                    "                    item.Subscription,\n"
                    "                    std::current_exception())" in body
                )
                self.assertTrue(
                    captures_with_bulk_vector or captures_with_record_helper,
                    "deferred cleanup failures must be captured before notify",
                )
                if captures_with_bulk_vector:
                    self.assertIn("try\n            {\n                m_DeferredDestroyFailures.insert", body)
                else:
                    record_body = extract_function_body(
                        text,
                        r"void \w+EventDispatcher::RecordDeferredDestroyFailure\(.*?\)",
                    )
                    self.assertIn(
                        "m_DeferredDestroyFailures.push_back({cleanupBatchId, subscription, failure})",
                        record_body,
                    )
                    self.assertIn("m_FallbackDeferredDestroyFailure", record_body)
                    self.assertLess(body.index("RecordDeferredDestroyFailure("),
                                    body.index("m_DispatchCv.notify_all()"))
                self.assertLess(body.index("m_PendingDestroyInProgress -= pending.size()"),
                                body.index("m_DispatchCv.notify_all()"))

    def test_deferred_event_dispatchers_retain_each_failed_subscription(self) -> None:
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")
            if "m_DeferredDestroyFailures" not in text:
                continue
            body = extract_function_body(text, r"void \w+EventDispatcher::FinishDispatch\(\)")
            with self.subTest(source=source.name):
                self.assertNotIn(
                    "alreadyCaptured",
                    body,
                    "Deferred cleanup must retain every failed subscription in a cleanup "
                    "batch so PluginManager retry can quiesce all plugin-owned user data.",
                )
                self.assertTrue(
                    "failures.push_back({item.CleanupBatchId, item.Subscription, std::current_exception()})" in body or
                    (
                        "RecordDeferredDestroyFailure(\n"
                        "                    item.CleanupBatchId,\n"
                        "                    item.Subscription,\n"
                        "                    std::current_exception())" in body
                    ),
                    "Deferred cleanup must retain the failed subscription, not only the exception.",
                )

    def test_deferred_event_dispatcher_take_helpers_reserve_before_queue_mutation(self) -> None:
        for source in CORE_DIR.glob("*EventDispatcher.cpp"):
            text = source.read_text(encoding="utf-8")

            failed_owner_body = extract_function_body(
                text,
                r"std::vector<[^>]+> \w+EventDispatcher::TakeFailedOwnerDestroySubscriptions\(.*?\)",
            )
            with self.subTest(source=source.name, helper="TakeFailedOwnerDestroySubscriptions"):
                self.assertIn("subscriptions.reserve(", failed_owner_body)
                self.assertLess(
                    failed_owner_body.index("subscriptions.reserve("),
                    failed_owner_body.index("std::remove_if"),
                    "retained owner cleanup failures must reserve before mutating the retry queue.",
                )
                if "m_HasFallbackFailedOwnerDestroy = false" in failed_owner_body:
                    self.assertLess(
                        failed_owner_body.index("subscriptions.reserve("),
                        failed_owner_body.index("m_HasFallbackFailedOwnerDestroy = false"),
                        "fallback retained owner cleanup failure must stay queued if output allocation fails.",
                    )

            deferred_body = extract_function_body(
                text,
                r"std::vector<[^>]+> \w+EventDispatcher::TakeDeferredDestroyFailures\(.*?\)",
            )
            with self.subTest(source=source.name, helper="TakeDeferredDestroyFailures"):
                self.assertIn("failedSubscriptions.reserve(", deferred_body)
                self.assertLess(
                    deferred_body.index("failedSubscriptions.reserve("),
                    deferred_body.index("std::remove_if"),
                    "deferred cleanup failures must reserve before mutating the retry queue.",
                )
                if "m_HasFallbackDeferredDestroyFailure = false" in deferred_body:
                    self.assertLess(
                        deferred_body.index("failedSubscriptions.reserve("),
                        deferred_body.index("m_HasFallbackDeferredDestroyFailure = false"),
                        "fallback deferred cleanup failure must stay queued if output allocation fails.",
                    )

    def test_plugin_boundary_catches_use_no_throw_logging(self) -> None:
        text = PLUGIN_MANAGER.read_text(encoding="utf-8")
        for function_name in ("InvokeGameplayPolicyEventCallback", "InvokeChatMessageEventCallback"):
            with self.subTest(function_name=function_name):
                body = extract_function_body(text, rf"void {function_name}\(.*?\)")
                self.assertIn("SafeLogErrorNoThrow", body)
                self.assertNotIn("OBELISK_ERROR", body)

        for function_name in ("PluginDescribeResourceKind", "PluginDescribeGameplayPolicyEventKind"):
            with self.subTest(function_name=function_name):
                body = extract_function_body(text, rf"bool {function_name}\(.*?\)")
                self.assertIn("try", body)
                self.assertIn("catch (const std::exception& e)", body)
                self.assertIn("catch (...)", body)
                self.assertIn("SafeLogErrorNoThrow", body)

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
