#!/usr/bin/env python3
"""Guardrails that keep experimental gameplay modules out of the public SDK."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_GAMEPLAY_EVENTS_MANIFEST = REPO_ROOT / "docs" / "public_gameplay_events.json"
PUBLIC_API_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
PUBLIC_DOC_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / "docs" / "ARCHITECTURE.md",
    REPO_ROOT / "docs" / "INSTALL.md",
    REPO_ROOT / "docs" / "OPERATOR_CLI.md",
    REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
    REPO_ROOT / "docs" / "RELEASE.md",
    REPO_ROOT / "docs" / "STATUS.md",
    REPO_ROOT / "docs" / "VERSIONING.md",
    REPO_ROOT / "docs" / "oBaseEvents.md",
    REPO_ROOT / ".github" / "pull_request_template.md",
]
PUBLIC_RELEASE_SCOPE_DOC_FILES = [
    REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
    REPO_ROOT / "docs" / "RELEASE.md",
    REPO_ROOT / "docs" / "STATUS.md",
]
V010_CORE_API_CAPABILITY_ALLOWLIST = [
    "OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS",
    "OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS",
    "OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS",
    "OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES",
    "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT",
    "OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING",
    "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
    "OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS",
    "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS",
    "OBELISK_API_CAPABILITY_CHAT_EVENTS",
    "OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS",
    "OBELISK_API_CAPABILITY_TIMERS",
]
V010_CORE_OBELISK_API_FIELD_ALLOWLIST = [
    "LogInfo",
    "LogWarn",
    "LogError",
    "RegisterPreProcessEvent",
    "RegisterPostProcessEvent",
    "RegisterPreProcessEventForNameIndex",
    "RegisterPostProcessEventForNameIndex",
    "CallProcessEvent",
    "abi_version",
    "struct_size",
    "capabilities",
    "RegisterPreProcessEventWithOwnerToken",
    "RegisterPostProcessEventWithOwnerToken",
    "RegisterPreProcessEventForNameIndexWithOwnerToken",
    "RegisterPostProcessEventForNameIndexWithOwnerToken",
    "RegisterPreProcessEventWithOwnerTokenHandle",
    "RegisterPostProcessEventWithOwnerTokenHandle",
    "RegisterPreProcessEventForNameIndexWithOwnerTokenHandle",
    "RegisterPostProcessEventForNameIndexWithOwnerTokenHandle",
    "UnregisterProcessEventCallbackWithOwnerToken",
    "RegisterGameplayPolicyEventWithOwnerTokenHandle",
    "UnregisterGameplayPolicyEventWithOwnerToken",
    "DescribeResourceKind",
    "DescribeGameplayPolicyEventKind",
    "RegisterChatMessageEventWithOwnerTokenHandle",
    "UnregisterChatMessageEventWithOwnerToken",
    "RegisterTimerWithOwnerTokenHandle",
    "UnregisterTimerWithOwnerToken",
]
V010_PUBLIC_STRUCT_ALLOWLIST = [
    "ObeliskStringView",
    "ObeliskChatMessageEvent",
    "ObeliskGameplayPolicyEvent",
    "ObeliskResourceKindDescriptor",
    "ObeliskGameplayPolicyEventDescriptor",
    "ObeliskPluginMetadata",
    "ObeliskPluginInitContext",
    "ObeliskApi",
]
V010_PUBLIC_ENUM_ALLOWLIST = [
    "ObeliskChatSendMode",
    "ObeliskGameplayPolicyEventKind",
    "ObeliskGameplayPolicyResourceKind",
    "ObeliskGameplayPolicyField",
]
V010_PUBLIC_ENUM_VALUE_ALLOWLIST = {
    "ObeliskChatSendMode": [
        "OBELISK_CHAT_SEND_MODE_GLOBAL",
        "OBELISK_CHAT_SEND_MODE_TRIBE",
        "OBELISK_CHAT_SEND_MODE_LOCAL",
        "OBELISK_CHAT_SEND_MODE_ALLIANCE",
    ],
    "ObeliskGameplayPolicyEventKind": [
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK",
    ],
    "ObeliskGameplayPolicyResourceKind": [
        "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_UNKNOWN",
        "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE",
        "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
    ],
    "ObeliskGameplayPolicyField": [
        "OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE",
        "OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX",
        "OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET",
        "OBELISK_GAMEPLAY_POLICY_FIELD_FORCE",
        "OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER",
        "OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN",
        "OBELISK_GAMEPLAY_POLICY_FIELD_COUNT",
    ],
}
V010_PUBLIC_CALLBACK_TYPEDEF_ALLOWLIST = [
    "OnProcessEventCallback",
    "ObeliskGameplayPolicyEventCallback",
    "ObeliskChatMessageEventCallback",
    "ObeliskTimerCallback",
]
CORE_TIMER_PUBLIC_TOKENS = {
    "ObeliskTimer",
    "UnregisterTimer",
}
CORE_TIMER_EXAMPLE_TOKENS = CORE_TIMER_PUBLIC_TOKENS | {
    "OnTimer",
}
V010_PUBLIC_MANIFEST_METADATA_SURFACE_IDS = [
    "obelisk.resource_kind_descriptors.v1",
    "obelisk.gameplay_policy_event_descriptors.v1",
]
V010_PUBLIC_MANIFEST_PROMOTED_EVENT_IDS = [
    "obelisk.gameplay_policy.v1",
]
V010_PUBLIC_MANIFEST_RC_EVENT_IDS = [
    "obelisk.chat_message.v1",
]
V010_RESOURCE_KIND_DESCRIPTOR_FIELDS = [
    "abi_version",
    "struct_size",
    "resource_kind",
    "reserved0",
    "flags",
    "supported_gameplay_policy_event_mask",
    "supported_gameplay_policy_field_mask",
    "stable_name",
    "display_name",
]
V010_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_FIELDS = [
    "abi_version",
    "struct_size",
    "event_kind",
    "resource_kind",
    "flags",
    "event_kind_mask",
    "field_mask",
    "stable_name",
    "display_name",
]
V010_GAMEPLAY_POLICY_TARGET_SETS = [
    "structure-observer-intake",
    "minimal-second-source-intake",
]
V010_GAMEPLAY_POLICY_RESOURCE_KINDS = [
    "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE",
    "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
]
V010_GAMEPLAY_POLICY_EVENT_KIND_MASKS = [
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
]
V010_CHAT_MESSAGE_TARGET_SETS = [
    "chat-message-intake",
]
V010_PUBLIC_GAMEPLAY_POLICY_EVENT_TOKENS = [
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK",
]
V010_PUBLIC_GAMEPLAY_POLICY_STABLE_NAMES = [
    "structure.access_check",
    "structure.demolish_check",
    "structure.variant_change",
    "structure.activation_toggle",
    "structure.pin_code_check",
    "structure.seat_check",
    "inventory.remote_add_check",
    "inventory.use_check",
]
CHAT_MESSAGE_EVENT_PUBLIC_CLAIM_FILES = [
    PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
    *PUBLIC_DOC_FILES,
    REPO_ROOT / "plugins" / "README.md",
]
CHAT_MESSAGE_EVENT_POSITIVE_CLAIM_WINDOW = 8
CHAT_MESSAGE_EVENT_POSITIVE_CLAIM_WORDS = {
    "promote",
    "promotes",
    "promoted",
    "promoting",
    "stable",
    "production-ready",
}
CHAT_MESSAGE_EVENT_POSITIVE_CLAIM_NEGATORS = {
    "blocked",
    "blocks",
    "beyond",
    "exclude",
    "excluded",
    "excludes",
    "excluding",
    "never",
    "no",
    "not",
    "outside",
    "without",
}
CHAT_MESSAGE_EVENT_RELATION_BREAKERS = {
    "but",
    "whereas",
    "while",
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*")
UNPROMOTED_GAMEPLAY_SURFACES = (
    "Player",
    "Tribe",
    "Buff",
    "Inventory",
    "Item",
    "Dino",
    "Structure",
    "Mission",
    "Transfer",
    "Permission",
    "Timer",
    "Admin",
    "Command",
)
UNPROMOTED_IDENTITY_SURFACE_TOKENS = (
    "ObeliskResourceHandle",
    "ResourceHandle",
    "GetResource",
    "ResolveResource",
    "GObject",
    "GObjects",
    "GUObjectArray",
    "GName",
    "GNames",
)
UNPROMOTED_COMMAND_ADMIN_PLAYER_API_TOKENS = (
    "OBELISK_API_CAPABILITY_COMMANDS",
    "OBELISK_API_CAPABILITY_ADMIN_COMMANDS",
    "OBELISK_API_CAPABILITY_PLAYER_COMMANDS",
    "ObeliskCommandContext",
    "ObeliskAdminCommand",
    "ObeliskPlayerCommand",
    "ObeliskPlayerId",
    "ObeliskPlayerHandle",
    "ObeliskPlayerIdentity",
    "RegisterCommand",
    "RegisterAdminCommand",
    "RegisterPlayerCommand",
    "UnregisterCommand",
    "UnregisterAdminCommand",
    "UnregisterPlayerCommand",
    "ExecuteCommand",
    "ExecuteAdminCommand",
    "SendServerCommand",
    "SendAdminCommand",
    "ConsoleCommand",
    "KickPlayer",
    "BanPlayer",
    "TeleportPlayer",
    "FindPlayer",
    "ResolvePlayer",
)
ROADMAP_COMMAND_HELPER_PROMOTION_TOKENS = (
    "Command",
    "Permission",
    "PlayerSnapshot",
    "ParameterData",
)
PROMOTED_RUNTIME_PAYLOAD_FILES = (
    REPO_ROOT / "core" / "ChatEventDispatcher.h",
    REPO_ROOT / "core" / "ChatEventDispatcher.cpp",
    REPO_ROOT / "core" / "StructureEventDispatcher.h",
    REPO_ROOT / "core" / "StructureEventDispatcher.cpp",
    REPO_ROOT / "core" / "InventoryPolicyEventDispatcher.h",
    REPO_ROOT / "core" / "InventoryPolicyEventDispatcher.cpp",
    REPO_ROOT / "core" / "PluginManager.cpp",
    REPO_ROOT / "hooks" / "ProcessEventChatReflection.h",
    REPO_ROOT / "hooks" / "ProcessEventChatReflection.cpp",
    REPO_ROOT / "hooks" / "ProcessEventStructureReflection.h",
    REPO_ROOT / "hooks" / "ProcessEventStructureReflection.cpp",
    REPO_ROOT / "hooks" / "ProcessEventInventoryReflection.h",
    REPO_ROOT / "hooks" / "ProcessEventInventoryReflection.cpp",
    REPO_ROOT / "plugins" / "oChatLogger" / "oChatLogger.c",
    REPO_ROOT / "plugins" / "oPolicyAudit" / "oPolicyAudit.cpp",
)
RUNTIME_LOG_SCAN_ROOTS = (
    REPO_ROOT / "core",
    REPO_ROOT / "hooks",
    REPO_ROOT / "plugins",
)
RUNTIME_LOG_SCAN_SUFFIXES = {".c", ".cpp", ".h", ".hpp"}
UNPROMOTED_SDK_CONSUMER_API_TOKENS = (
    "OBELISK_API_CAPABILITY_INVENTORY_EVENTS",
    "OBELISK_API_CAPABILITY_INVENTORY_POLICY_EVENTS",
    "OBELISK_API_CAPABILITY_ITEM_EVENTS",
    "OBELISK_API_CAPABILITY_ITEM_POLICY_EVENTS",
    "OBELISK_API_CAPABILITY_STRUCTURE_EVENTS",
    "OBELISK_API_CAPABILITY_RESOURCE_HANDLES",
    "OBELISK_API_CAPABILITY_RESOURCE_MUTATION",
    "OBELISK_API_CAPABILITY_RETURN_OVERRIDES",
    "ObeliskInventoryEvent",
    "ObeliskInventoryPolicyEvent",
    "ObeliskInventory",
    "ObeliskInventoryItem",
    "RegisterInventoryEvent",
    "RegisterInventoryPolicyEvent",
    "RegisterOnInventoryEvent",
    "RegisterOnInventoryPolicyEvent",
    "UnregisterInventoryEvent",
    "UnregisterInventoryPolicyEvent",
    "ObeliskItemEvent",
    "ObeliskItemPolicyEvent",
    "ObeliskItem",
    "ObeliskItemStack",
    "RegisterItemEvent",
    "RegisterItemPolicyEvent",
    "RegisterOnItemEvent",
    "RegisterOnItemPolicyEvent",
    "UnregisterItemEvent",
    "UnregisterItemPolicyEvent",
    "ObeliskStructureEvent",
    "ObeliskStructureEvents",
    "RegisterStructureEvent",
    "RegisterOnStructureEvent",
    "RegisterOnStructureEvents",
    "UnregisterStructureEvent",
    "UnregisterStructureEvents",
    "ObeliskResourceHandle",
    "ResourceHandle",
    "GetResource",
    "ResolveResource",
    "GetInventory",
    "ResolveInventory",
    "GetItem",
    "ResolveItem",
    "ObeliskInventoryId",
    "ObeliskItemId",
    "ObeliskResourceId",
    "inventory_id",
    "item_id",
    "resource_id",
    "object_id",
    "ObeliskMutation",
    "ObeliskMutationContext",
    "MutateResource",
    "MutateInventory",
    "MutateItem",
    "SetResource",
    "SetInventory",
    "SetItem",
    "OverrideInventory",
    "OverrideItem",
    "OverrideReturn",
    "ReturnOverride",
    "ObeliskReturnOverride",
    "SetReturnOverride",
    "return_override",
    *UNPROMOTED_COMMAND_ADMIN_PLAYER_API_TOKENS,
)


def unpromoted_gameplay_tokens() -> list[str]:
    tokens: list[str] = []
    for singular in UNPROMOTED_GAMEPLAY_SURFACES:
        plural = f"{singular}s"
        for term in (singular, plural):
            tokens.extend(
                [
                    f"OBELISK_API_CAPABILITY_{term.upper()}_EVENTS",
                    f"Obelisk{term}",
                    f"RegisterOn{term}",
                    f"Unregister{term}",
                    f"On{term}",
                ]
            )
    return tokens


def unpromoted_sdk_consumer_tokens() -> list[str]:
    tokens = list(UNPROMOTED_SDK_CONSUMER_API_TOKENS)
    for singular in UNPROMOTED_GAMEPLAY_SURFACES:
        plural = f"{singular}s"
        for term in (singular, plural):
            tokens.extend(
                [
                    f"OBELISK_API_CAPABILITY_{term.upper()}_EVENTS",
                    f"OBELISK_API_CAPABILITY_{term.upper()}_POLICY_EVENTS",
                    f"Obelisk{term}Event",
                    f"Obelisk{term}PolicyEvent",
                    f"{term}EventCallback",
                    f"{term}PolicyEventCallback",
                    f"{term}EventSubscription",
                    f"{term}PolicyEventSubscription",
                    f"Register{term}Event",
                    f"Register{term}PolicyEvent",
                    f"RegisterOn{term}Event",
                    f"RegisterOn{term}PolicyEvent",
                    f"Unregister{term}Event",
                    f"Unregister{term}PolicyEvent",
                ]
            )

    return list(dict.fromkeys(tokens))


def public_api_capability_defines(header: str) -> list[str]:
    return re.findall(
        r"^\s*#define\s+(OBELISK_API_CAPABILITY_[A-Z0-9_]+)\b",
        header,
        re.MULTILINE,
    )


def obelisk_api_struct_body(header: str) -> str:
    match = re.search(
        r"typedef\s+struct\s+ObeliskApi\s*\{(?P<body>.*?)\}\s*ObeliskApi\s*;",
        header,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("typedef struct ObeliskApi block not found")
    return match.group("body")


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def c_like_string_literals(text: str) -> list[str]:
    return re.findall(r'"(?:\\.|[^"\\])*"', strip_c_comments(text), flags=re.DOTALL)


def normalized(text: str) -> str:
    return " ".join(text.split())


def assert_explicit_category_only_resource_contract(
    testcase: unittest.TestCase,
    text: str,
    *,
    require_kind_only: bool = False,
) -> None:
    compact_text = normalized(text)
    if require_kind_only:
        testcase.assertIn("kind-only", compact_text)
    for term in (
        "no identity",
        "no lookup",
        "no cross-event correlation",
    ):
        testcase.assertIn(term, compact_text)


def obelisk_api_field_names(header: str) -> list[str]:
    body = strip_c_comments(obelisk_api_struct_body(header))
    fields: list[str] = []
    for declaration in body.split(";"):
        declaration = " ".join(declaration.split())
        if not declaration:
            continue
        function_pointer = re.search(r"\(\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", declaration)
        if function_pointer:
            fields.append(function_pointer.group(1))
            continue
        plain_field = re.search(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]+\])?$",
            declaration,
        )
        if plain_field:
            fields.append(plain_field.group(1))
    return fields


def public_struct_typedefs(header: str) -> list[str]:
    return [
        match.group("alias")
        for match in re.finditer(
            r"typedef\s+struct(?:\s+[A-Za-z_][A-Za-z0-9_]*)?\s*\{.*?\}\s*"
            r"(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\s*;",
            strip_c_comments(header),
            re.DOTALL,
        )
    ]


def public_enum_typedefs(header: str) -> list[str]:
    return list(public_enum_definitions(header))


def public_enum_definitions(header: str) -> dict[str, list[str]]:
    definitions: dict[str, list[str]] = {}
    for match in re.finditer(
        r"typedef\s+enum(?:\s+[A-Za-z_][A-Za-z0-9_]*)?\s*\{(?P<body>.*?)\}\s*"
        r"(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\s*;",
        strip_c_comments(header),
        re.DOTALL,
    ):
        members: list[str] = []
        for item in match.group("body").split(","):
            member = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\b", item)
            if member:
                members.append(member.group(1))
        definitions[match.group("alias")] = members
    return definitions


def public_callback_typedefs(header: str) -> list[str]:
    return re.findall(
        r"typedef\s+[^;(){}]+?\(\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\(",
        strip_c_comments(header),
    )


def sentence_like_segments(text: str) -> list[tuple[int, str]]:
    return [
        (match.start(), match.group(0))
        for match in re.finditer(r"[^.!?;\n]+(?:[.!?;]|\n|$)", text)
        if match.group(0).strip()
    ]


def positive_chat_message_event_claims(text: str, relative_path: str) -> list[str]:
    offenders: list[str] = []

    for segment_start, segment in sentence_like_segments(text):
        tokens = [match.group(0).lower() for match in TOKEN_RE.finditer(segment)]
        if "chatmessageevent" not in tokens:
            continue

        positive_indices: list[int] = []
        for index, token in enumerate(tokens):
            if token in CHAT_MESSAGE_EVENT_POSITIVE_CLAIM_WORDS:
                positive_indices.append(index)
            elif (
                token == "production"
                and index + 1 < len(tokens)
                and tokens[index + 1] == "ready"
            ):
                positive_indices.append(index)

        if not positive_indices:
            continue

        chat_indices = [index for index, token in enumerate(tokens) if token == "chatmessageevent"]
        for chat_index in chat_indices:
            for positive_index in positive_indices:
                if abs(chat_index - positive_index) > CHAT_MESSAGE_EVENT_POSITIVE_CLAIM_WINDOW:
                    continue

                start = min(chat_index, positive_index)
                end = max(chat_index, positive_index)
                relation_tokens = tokens[start : end + 1]
                negation_tokens = tokens[max(0, start - 4) : end + 1]
                if CHAT_MESSAGE_EVENT_RELATION_BREAKERS.intersection(relation_tokens):
                    continue
                if CHAT_MESSAGE_EVENT_POSITIVE_CLAIM_NEGATORS.intersection(negation_tokens):
                    continue

                line = text.count("\n", 0, segment_start) + 1
                compact_segment = " ".join(segment.split())
                offenders.append(f"{relative_path}:{line}: {compact_segment}")
                break

    return offenders


class PublicSdkGuardrailTests(unittest.TestCase):
    def test_public_gameplay_event_manifest_contains_no_server_paths(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        offenders: list[str] = []

        def visit(value: object, path: str) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    visit(child, f"{path}.{key}")
                return
            if isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, f"{path}[{index}]")
                return
            if isinstance(value, str) and "/servidor/ark" in value:
                offenders.append(path)

        visit(manifest, "manifest")
        self.assertEqual(offenders, [])

    def test_public_gameplay_event_manifest_does_not_promote_out_of_scope_surfaces(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        forbidden_patterns = (
            r"\bpromot(?:e|ed|es|ing)\s+(?:a\s+)?(?:public\s+)?Inventory\s+SDK\b",
            r"\bpublic\s+Inventory\s+SDKs?\b",
            r"\bInventory\s+(?:Events?|Callbacks?|APIs?|SDKs?)\b",
            r"\bpromot(?:e|ed|es|ing)\s+(?:a\s+)?(?:public\s+)?StructureEvents?\b",
            r"\bpublic\s+StructureEvents?\b",
            r"\bStructureEvents?\s+(?:APIs?|SDKs?)\b",
            r"\bpromot(?:e|ed|es|ing)\s+(?:a\s+)?(?:public\s+)?Structure\s+(?:APIs?|SDKs?)\b",
            r"\bpublic\s+Structure\s+(?:APIs?|SDKs?)\b",
            r"\bpublic\s+Items?\b",
            r"\bItems?\s+SDKs?\b",
            r"\bItems?\s+Events?\b",
            r"\bpublic\s+Mission\b",
            r"\bMission\s+SDKs?\b",
            r"\bMission\s+Events?\b",
            r"\bpublic\s+ResourceHandle\b",
            r"\bpromoted\s+ResourceHandle\b",
            r"\bResourceHandle\s+SDKs?\b",
            r"\bResourceHandle\s+APIs?\b",
            r"\bricher\s+chat\s+(?:APIs?|SDKs?|surfaces?|events?)\b",
            r"\bpromot(?:e|ed|es|ing)\s+(?:richer\s+chat|chat\s+send|chat\s+moderation|command\s+SDK)\b",
            r"\bpromot(?:e|ed|es|ing)\s+(?:public\s+)?(?:command|admin|player)\s+(?:APIs?|SDKs?|surfaces?)\b",
            r"\bpublic\s+(?:command|admin|player)\s+(?:APIs?|SDKs?|surfaces?)\b",
            r"\b(?:admin|player)\s+commands?\s+(?:APIs?|SDKs?|surfaces?)\b",
            r"\bpromot(?:e|ed|es|ing)\s+(?:gameplay\s+)?mutation\b",
            r"\bpublic\s+mutation\s+(?:APIs?|SDKs?|surfaces?|authority)\b",
            r"\bpromot(?:e|ed|es|ing)\s+(?:a\s+)?(?:return[- ]override|return\s+override)\b",
            r"\bpublic\s+(?:return[- ]override|return\s+override)\s+(?:APIs?|SDKs?|surfaces?|authority)\b",
            r"\bpromot(?:e|ed|es|ing)\s+(?:public\s+)?CallProcessEvent\b",
            r"\bpublic\s+CallProcessEvent(?:\s+(?:APIs?|SDKs?|surfaces?|authority|behavior))?\b",
            r"\bCallProcessEvent[- ]based\s+(?:plugin\s+)?(?:APIs?|SDKs?|surfaces?|behavior)\b",
        )
        offenders: list[str] = []

        def visit(value: object, path: str) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    visit(child, f"{path}.{key}")
                return
            if isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, f"{path}[{index}]")
                return
            if not isinstance(value, str):
                return
            for pattern in forbidden_patterns:
                if re.search(pattern, value, flags=re.IGNORECASE):
                    offenders.append(f"{path}: {pattern}")

        visit(manifest, "manifest")
        self.assertEqual(offenders, [])

    def test_public_manifest_does_not_use_static_resource_or_command_evidence_for_rc_surfaces(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        evidence_keys = {
            "target_set",
            "target_sets",
            "backing_target_set",
            "inventory_backing_target_set",
            "second_source_reports",
            "live_debug_delivery_evidence",
            "abi_tests",
            "sdk_consumer_tests",
            "lifecycle_tests",
            "docs",
        }
        forbidden_evidence_markers = (
            "admin",
            "artifact-gate",
            "artifact_gate",
            "build_static_global",
            "command",
            "gobjects",
            "gnames",
            "player",
            "resource-handle",
            "resource_handle",
            "static-global",
            "static_global",
            "transfer",
            "uobject-flag",
            "uobject_flag",
            "validate_offline_artifact_gate",
        )
        offenders: list[str] = []

        def visit(value: object, path: str, parent_key: str | None = None) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    visit(child, f"{path}.{key}", key)
                return
            if isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, f"{path}[{index}]", parent_key)
                return
            if not isinstance(value, str) or parent_key not in evidence_keys:
                return
            lowered = value.lower()
            for marker in forbidden_evidence_markers:
                if marker in lowered:
                    offenders.append(f"{path}: {marker}")

        visit(manifest, "manifest")
        self.assertEqual(offenders, [])

    def test_command_helper_roadmap_terms_stay_out_of_public_payloads_and_runtime_logs(self) -> None:
        public_surfaces = (
            PUBLIC_API_HEADER,
            PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
            *PROMOTED_RUNTIME_PAYLOAD_FILES,
        )
        offenders: list[str] = []

        for path in public_surfaces:
            text = path.read_text(encoding="utf-8")
            for token in ROADMAP_COMMAND_HELPER_PROMOTION_TOKENS:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: public/payload token {token}")

        for root in RUNTIME_LOG_SCAN_ROOTS:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in RUNTIME_LOG_SCAN_SUFFIXES:
                    continue
                for literal in c_like_string_literals(path.read_text(encoding="utf-8")):
                    for token in ROADMAP_COMMAND_HELPER_PROMOTION_TOKENS:
                        if token in literal:
                            offenders.append(f"{path.relative_to(REPO_ROOT)}: runtime log/string token {token}")

        self.assertEqual(offenders, [])

    def test_public_sdk_core_api_surface_matches_v010_allowlist(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")

        self.assertEqual(public_api_capability_defines(header), V010_CORE_API_CAPABILITY_ALLOWLIST)
        self.assertEqual(obelisk_api_field_names(header), V010_CORE_OBELISK_API_FIELD_ALLOWLIST)
        self.assertEqual(public_struct_typedefs(header), V010_PUBLIC_STRUCT_ALLOWLIST)
        self.assertEqual(public_enum_typedefs(header), V010_PUBLIC_ENUM_ALLOWLIST)
        self.assertEqual(public_enum_definitions(header), V010_PUBLIC_ENUM_VALUE_ALLOWLIST)
        self.assertEqual(public_callback_typedefs(header), V010_PUBLIC_CALLBACK_TYPEDEF_ALLOWLIST)

    def test_public_sdk_surface_parsers_include_anonymous_and_non_void_callback_typedefs(self) -> None:
        header = """
        typedef struct {
            uint32_t value;
        } ObeliskSyntheticStruct;

        typedef enum {
            OBELISK_SYNTHETIC_UNKNOWN = 0,
            OBELISK_SYNTHETIC_READY = 1,
        } ObeliskSyntheticEnum;

        typedef uint64_t (*ObeliskSyntheticCallback)(void* user_data);
        """

        self.assertEqual(public_struct_typedefs(header), ["ObeliskSyntheticStruct"])
        self.assertEqual(public_enum_typedefs(header), ["ObeliskSyntheticEnum"])
        self.assertEqual(
            public_enum_definitions(header),
            {
                "ObeliskSyntheticEnum": [
                    "OBELISK_SYNTHETIC_UNKNOWN",
                    "OBELISK_SYNTHETIC_READY",
                ],
            },
        )
        self.assertEqual(public_callback_typedefs(header), ["ObeliskSyntheticCallback"])

    def test_chat_message_event_positive_claim_detector_is_order_independent(self) -> None:
        forbidden = [
            "`ChatMessageEvent` is stable.",
            "`ChatMessageEvent` is a promoted public SDK surface.",
            "Production-ready `ChatMessageEvent` callback ABI.",
            "The promoted minimal `ChatMessageEvent` API ships.",
            "`ChatMessageEvent` production ready API ships.",
        ]
        allowed = [
            "`ChatMessageEvent` is a minimal v0.1-rc SDK ABI surface.",
            "This PR does not promote chat beyond minimal `ChatMessageEvent`.",
            "Outside the promoted `GameplayPolicyEvent` surface and the minimal `ChatMessageEvent` RC notification surface, richer chat remains blocked.",
            "`GameplayPolicyEvent` is stable, while `ChatMessageEvent` is minimal and RC.",
        ]

        for text in forbidden:
            with self.subTest(kind="forbidden", text=text):
                self.assertNotEqual(positive_chat_message_event_claims(text, "synthetic.md"), [])
        for text in allowed:
            with self.subTest(kind="allowed", text=text):
                self.assertEqual(positive_chat_message_event_claims(text, "synthetic.md"), [])

    def test_public_material_does_not_claim_chat_message_event_is_stable_promoted_or_production_ready(self) -> None:
        offenders: list[str] = []

        for path in CHAT_MESSAGE_EVENT_PUBLIC_CLAIM_FILES:
            text = path.read_text(encoding="utf-8")
            if path == PUBLIC_GAMEPLAY_EVENTS_MANIFEST:
                text = json.dumps(json.loads(text), sort_keys=True, indent=2)
            offenders.extend(
                positive_chat_message_event_claims(
                    text,
                    str(path.relative_to(REPO_ROOT)),
                )
            )

        self.assertEqual(offenders, [])

    def test_cpp_public_sdk_examples_catch_exceptions_at_entry_points(self) -> None:
        files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "tests/sdk_consumer/MinimalPlugin.cpp",
            REPO_ROOT / "tests/sdk_consumer/MinimalNoShutdownPlugin.cpp",
            REPO_ROOT / "tests/sdk_installed_consumer/consumer_plugin.cpp",
            REPO_ROOT / "tests/sdk_installed_consumer/no_shutdown_plugin.cpp",
        ]
        for path in files:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertIn("catch (...)", text)

    def test_installed_cpp_consumer_covers_gameplay_policy_and_chat_events(self) -> None:
        consumer = (REPO_ROOT / "tests/sdk_installed_consumer/consumer_plugin.cpp").read_text(encoding="utf-8")
        fixture = (REPO_ROOT / "tests/sdk_installed_consumer/consumer_fixture.cpp").read_text(encoding="utf-8")

        for token in [
            "RegisterGameplayPolicyEventWithOwnerTokenHandle",
            "UnregisterGameplayPolicyEventWithOwnerToken",
            "InstallLayoutConsumer_GameplayPolicyEventSeen",
            "InstallLayoutConsumer_GameplayPolicyEventAccepted",
            "RegisterChatMessageEventWithOwnerTokenHandle",
            "InstallLayoutConsumer_ChatMessageEventSeen",
        ]:
            with self.subTest(file="consumer_plugin.cpp", token=token):
                self.assertIn(token, consumer)

        for token in [
            "DispatchAllValidGameplayPolicyEvents",
            "DispatchValidStructureGameplayPolicyEvent",
            "DispatchValidInventoryGameplayPolicyEvent",
            "DispatchValidChatMessageEvent",
        ]:
            with self.subTest(file="consumer_fixture.cpp", token=token):
                self.assertIn(token, fixture)

        for token in V010_PUBLIC_GAMEPLAY_POLICY_EVENT_TOKENS:
            with self.subTest(file="consumer_plugin.cpp", event_kind=token):
                self.assertIn(token, consumer)
            with self.subTest(file="consumer_fixture.cpp", event_kind=token):
                self.assertIn(token, fixture)

        for stable_name in V010_PUBLIC_GAMEPLAY_POLICY_STABLE_NAMES:
            with self.subTest(file="consumer_plugin.cpp", stable_name=stable_name):
                self.assertIn(stable_name, consumer)
            with self.subTest(file="consumer_fixture.cpp", stable_name=stable_name):
                self.assertIn(stable_name, fixture)

        for token in [
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET",
            "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE",
            "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
        ]:
            with self.subTest(file="consumer_plugin.cpp", required_field_or_resource=token):
                self.assertIn(token, consumer)
            with self.subTest(file="consumer_fixture.cpp", required_field_or_resource=token):
                self.assertIn(token, fixture)

    def test_rc_layout_smoke_tracks_public_rc_target_sets(self) -> None:
        smoke = (REPO_ROOT / "scripts" / "check_rc_layout_evidence_smoke.sh").read_text(encoding="utf-8")
        self.assertIn("--candidate-root", smoke)
        self.assertIn("--fail-on-readiness-gaps", smoke)
        self.assertNotIn("--fail-on-base-readiness-gaps", smoke)
        for target_set in sorted(set(V010_GAMEPLAY_POLICY_TARGET_SETS + V010_CHAT_MESSAGE_TARGET_SETS)):
            with self.subTest(target_set=target_set):
                self.assertIn(f"--target-set {target_set}", smoke)

    def test_handle_callback_guidance_requires_owner_token_capability(self) -> None:
        files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs/oBaseEvents.md",
            REPO_ROOT / "tests/sdk_consumer/MinimalPlugin.cpp",
            REPO_ROOT / "plugins/oBaseEvents/oBaseEvents.cpp",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            if "OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES" in text:
                self.assertIn(
                    "OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS",
                    text,
                    f"{path.relative_to(REPO_ROOT)} documents handle callbacks without owner-token capability",
                )

    def test_public_sdk_guidance_keeps_multi_instance_runtime_state_process_local(self) -> None:
        docs = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/PLUGIN_ARCHITECTURE.md",
        ]
        required_terms = (
            "process-local",
            "owner tokens",
            "worker threads",
            "sockets",
            "caches",
            "mutable",
            "cross-process",
            "locking",
        )

        for path in docs:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                for term in required_terms:
                    self.assertIn(term, text)

    def test_plugin_architecture_defines_public_gameplay_event_promotion_gate(self) -> None:
        text = (REPO_ROOT / "docs/PLUGIN_ARCHITECTURE.md").read_text(encoding="utf-8")
        normalized_text = normalized(text)

        required_terms = (
            "Gameplay Event Promotion Gate",
            "accepted, distinct second-source",
            "promotion_gate.ready=true",
            "copied into Obelisk-owned POD storage",
            "no `UObject`",
            "`UFunction`",
            "`FString`",
            "raw parameter buffer",
            "append-only in `ObeliskApi`",
            "capability bit",
            "owner-token unregister path",
            "plugin-owner cleanup",
            "SDK consumer tests",
            "runtime-observer log summaries",
            "not a public gameplay event API",
        )

        for term in required_terms:
            self.assertIn(normalized(term), normalized_text)

    def test_release_docs_define_public_gameplay_event_sdk_gate(self) -> None:
        text = (REPO_ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")

        required_terms = (
            "docs/public_gameplay_events.json",
            "accepted distinct second-source evidence",
            "copied Obelisk-owned payload storage",
            "no\n`UObject`, `UFunction`, `FString`, raw parameter buffer",
            "append-only ABI fields",
            "capability bit",
            "owner-token handle\nregistration",
            "owner-scoped unregister",
            "plugin-owner cleanup",
            "ABI layout tests",
            "installed SDK consumer tests",
            "Runtime-observer summaries do not satisfy this SDK contract gate",
        )

        for term in required_terms:
            self.assertIn(term, text)

    def test_release_scope_docs_keep_inventory_reflection_boundary_explicit(self) -> None:
        required_terms = (
            "GameplayPolicyEvent",
            "Inventory SDK",
            "ResourceHandle",
            "GNames",
            "GObjects",
            "identity",
            "mutation",
            "return override",
        )

        for path in PUBLIC_RELEASE_SCOPE_DOC_FILES:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                for term in required_terms:
                    self.assertIn(term, text)

    def test_public_sdk_headers_have_no_inventory_identity_mutation_or_override_api(self) -> None:
        forbidden = (
            "OBELISK_API_CAPABILITY_INVENTORY_EVENTS",
            "OBELISK_API_CAPABILITY_INVENTORY_POLICY_EVENTS",
            "OBELISK_API_CAPABILITY_ITEM_EVENTS",
            "OBELISK_API_CAPABILITY_ITEM_POLICY_EVENTS",
            "OBELISK_API_CAPABILITY_RESOURCE_HANDLES",
            "ObeliskInventory",
            "ObeliskInventoryItem",
            "ObeliskItemEvent",
            "ObeliskItemPolicyEvent",
            "ObeliskItem",
            "ObeliskItemStack",
            "ObeliskResourceHandle",
            "ResourceHandle",
            "GetResource",
            "ResolveResource",
            "GetInventory",
            "ResolveInventory",
            "GetItem",
            "ResolveItem",
            "MutateInventory",
            "MutateItem",
            "SetInventory",
            "SetItem",
            "OverrideInventory",
            "OverrideItem",
            "OverrideReturn",
            "ReturnOverride",
            "GObject",
            "GObjects",
            "GUObjectArray",
            "GName",
            "GNames",
        )
        offenders: list[str] = []

        for path in (REPO_ROOT / "include" / "obelisk").rglob("*"):
            if not path.is_file() or path.suffix not in {".h", ".hpp"}:
                continue
            text = strip_c_comments(path.read_text(encoding="utf-8"))
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_gameplay_event_manifest_has_no_undeclared_public_event_capabilities(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        header = (REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h").read_text(encoding="utf-8")

        self.assertEqual(manifest.get("schema"), "obelisk.public-gameplay-events.v1")
        metadata_surfaces = manifest.get("metadata_surfaces")
        self.assertIsInstance(metadata_surfaces, list)
        promoted_events = manifest.get("promoted_events")
        self.assertIsInstance(promoted_events, list)
        rc_events = manifest.get("rc_events")
        self.assertIsInstance(rc_events, list)

        self.assertEqual(
            [surface.get("surface_id") for surface in metadata_surfaces],
            V010_PUBLIC_MANIFEST_METADATA_SURFACE_IDS,
        )
        self.assertEqual(
            [event.get("event_id") for event in promoted_events],
            V010_PUBLIC_MANIFEST_PROMOTED_EVENT_IDS,
        )
        self.assertEqual(
            [event.get("event_id") for event in rc_events],
            V010_PUBLIC_MANIFEST_RC_EVENT_IDS,
        )

        declared_capabilities = {
            event.get("capability") for section in ("promoted_events", "rc_events")
            for event in manifest.get(section, []) if isinstance(event, dict)
        }
        public_event_capabilities = {
            match.group(0)
            for match in re.finditer(r"OBELISK_API_CAPABILITY_[A-Z0-9_]+_EVENTS\b", header)
        }

        self.assertEqual(public_event_capabilities - declared_capabilities, set())
        self.assertEqual(
            public_event_capabilities,
            {
                "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
                "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            },
        )

    def test_public_metadata_manifest_declares_resource_kind_descriptor_surface(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        header = (REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h").read_text(encoding="utf-8")

        metadata_surfaces = manifest.get("metadata_surfaces")
        self.assertIsInstance(metadata_surfaces, list)
        resource_surface = next(
            (
                surface for surface in metadata_surfaces
                if isinstance(surface, dict) and surface.get("surface_id") == "obelisk.resource_kind_descriptors.v1"
            ),
            None,
        )
        self.assertIsNotNone(resource_surface)

        self.assertIn("#define OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS", header)
        self.assertIn("typedef struct ObeliskResourceKindDescriptor", header)
        self.assertIn("DescribeResourceKind", header)
        self.assertEqual(resource_surface.get("public_name"), "DescribeResourceKind")
        self.assertEqual(resource_surface.get("capability"), "OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS")
        self.assertEqual(resource_surface.get("descriptor_struct"), "ObeliskResourceKindDescriptor")
        self.assertEqual(resource_surface.get("descriptor"), "DescribeResourceKind")
        for field in (
            "abi_version",
            "struct_size",
            "resource_kind",
            "flags",
            "supported_gameplay_policy_event_mask",
            "supported_gameplay_policy_field_mask",
            "stable_name",
            "display_name",
        ):
            self.assertIn(field, resource_surface.get("descriptor_fields", []))
        self.assertEqual(resource_surface.get("descriptor_fields"), V010_RESOURCE_KIND_DESCRIPTOR_FIELDS)
        for flag in (
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
        ):
            self.assertIn(flag, resource_surface.get("flags", []))
        self.assertEqual(
            resource_surface.get("flags"),
            [
                "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
                "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
                "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
            ],
        )
        kinds = {item.get("kind"): item for item in resource_surface.get("resource_kinds", [])}
        self.assertIn("OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE", kinds)
        self.assertIn("OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM", kinds)
        self.assertEqual(
            kinds["OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE"].get("supported_gameplay_policy_event_mask"),
            "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES",
        )
        self.assertEqual(
            kinds["OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM"].get("supported_gameplay_policy_event_mask"),
            "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
        )
        for excluded in (
            "ResourceHandle",
            "object identity",
            "lookup",
            "cross-event correlation",
            "UE pointers",
            "mutation",
            "return override",
        ):
            self.assertIn(excluded, resource_surface.get("not_promoted", []))

    def test_public_metadata_manifest_declares_gameplay_policy_event_descriptor_surface(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        header = (REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h").read_text(encoding="utf-8")

        metadata_surfaces = manifest.get("metadata_surfaces")
        self.assertIsInstance(metadata_surfaces, list)
        event_surface = next(
            (
                surface for surface in metadata_surfaces
                if isinstance(surface, dict) and
                surface.get("surface_id") == "obelisk.gameplay_policy_event_descriptors.v1"
            ),
            None,
        )
        self.assertIsNotNone(event_surface)

        self.assertIn("#define OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS", header)
        self.assertIn("typedef struct ObeliskGameplayPolicyEventDescriptor", header)
        self.assertIn("DescribeGameplayPolicyEventKind", header)
        self.assertEqual(event_surface.get("public_name"), "DescribeGameplayPolicyEventKind")
        self.assertEqual(event_surface.get("capability"), "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS")
        self.assertEqual(event_surface.get("descriptor_struct"), "ObeliskGameplayPolicyEventDescriptor")
        self.assertEqual(event_surface.get("descriptor"), "DescribeGameplayPolicyEventKind")
        self.assertEqual(event_surface.get("described_event"), "obelisk.gameplay_policy.v1")
        for field in (
            "abi_version",
            "struct_size",
            "event_kind",
            "resource_kind",
            "flags",
            "event_kind_mask",
            "field_mask",
            "stable_name",
            "display_name",
        ):
            self.assertIn(field, event_surface.get("descriptor_fields", []))
        self.assertEqual(
            event_surface.get("descriptor_fields"),
            V010_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_FIELDS,
        )
        for flag in (
            "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
            "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED",
            "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
        ):
            self.assertIn(flag, event_surface.get("flags", []))
        for excluded in (
            "module-specific SDK",
            "ResourceHandle",
            "persistent handles",
            "object identity",
            "lookup",
            "cross-event correlation",
            "UE pointers",
            "mutation",
            "return override",
        ):
            self.assertIn(excluded, event_surface.get("not_promoted", []))

    def test_public_resource_programming_manifest_stays_category_only_without_identity_or_lookup(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))

        resource_surface = next(
            (
                surface for surface in manifest.get("metadata_surfaces", [])
                if isinstance(surface, dict) and surface.get("surface_id") == "obelisk.resource_kind_descriptors.v1"
            ),
            None,
        )
        event_surface = next(
            (
                surface for surface in manifest.get("metadata_surfaces", [])
                if isinstance(surface, dict) and
                surface.get("surface_id") == "obelisk.gameplay_policy_event_descriptors.v1"
            ),
            None,
        )
        gameplay_policy = next(
            (
                event for event in manifest.get("promoted_events", [])
                if isinstance(event, dict) and event.get("event_id") == "obelisk.gameplay_policy.v1"
            ),
            None,
        )
        self.assertIsNotNone(resource_surface)
        self.assertIsNotNone(event_surface)
        self.assertIsNotNone(gameplay_policy)

        self.assertEqual(resource_surface.get("descriptor_fields"), V010_RESOURCE_KIND_DESCRIPTOR_FIELDS)
        self.assertEqual(
            resource_surface.get("flags"),
            [
                "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
                "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
                "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
            ],
        )
        self.assertEqual(
            event_surface.get("descriptor_fields"),
            V010_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_FIELDS,
        )
        assert_explicit_category_only_resource_contract(
            self,
            gameplay_policy.get("resource_contract", ""),
            require_kind_only=True,
        )
        self.assertIn("no persistent handle", normalized(gameplay_policy.get("resource_contract", "")))

        for path, text in (
            ("metadata_surfaces.resource.scope", resource_surface.get("scope", "")),
            ("metadata_surfaces.event.scope", event_surface.get("scope", "")),
            ("promoted_events.gameplay_policy.resource_contract", gameplay_policy.get("resource_contract", "")),
        ):
            with self.subTest(path=path):
                assert_explicit_category_only_resource_contract(self, text)

        for resource_kind in resource_surface.get("resource_kinds", []):
            with self.subTest(kind=resource_kind.get("kind", "<missing>")):
                self.assertEqual(
                    set(resource_kind),
                    {
                        "kind",
                        "stable_name",
                        "supported_gameplay_policy_event_mask",
                        "supported_gameplay_policy_field_mask",
                    },
                )

        for event_kind in gameplay_policy.get("event_kinds", []):
            with self.subTest(event_kind=event_kind.get("kind", "<missing>")):
                self.assertEqual(
                    set(event_kind),
                    {
                        "kind",
                        "stable_name",
                        "resource_kind",
                        "event_kind_mask",
                        "field_mask",
                    },
                )

        forbidden_public_field_names = {
            "handle",
            "resource_handle",
            "resource_id",
            "object_id",
            "player_id",
            "tribe_id",
            "inventory_id",
            "item_id",
            "lookup_key",
            "uobject",
            "gobject",
            "gobjects",
            "fname_index",
            "coordinates",
            "location",
        }
        public_field_lists = [
            resource_surface.get("descriptor_fields", []),
            event_surface.get("descriptor_fields", []),
            gameplay_policy.get("public_fields", []),
            gameplay_policy.get("descriptor_fields", []),
        ]
        offenders = [
            field
            for fields in public_field_lists
            for field in fields
            if field in forbidden_public_field_names
        ]
        self.assertEqual(offenders, [])

    def test_public_gameplay_event_capability_regex_matches_event_defines(self) -> None:
        header = "#define OBELISK_API_CAPABILITY_STRUCTURE_EVENTS (1ull << 42)\n"
        public_event_capabilities = {
            match.group(0)
            for match in re.finditer(r"OBELISK_API_CAPABILITY_[A-Z0-9_]+_EVENTS\b", header)
        }

        self.assertEqual(public_event_capabilities, {"OBELISK_API_CAPABILITY_STRUCTURE_EVENTS"})

    def test_promoted_public_gameplay_events_declare_required_evidence(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        promoted_events = manifest.get("promoted_events")
        self.assertIsInstance(promoted_events, list)

        required_boolean_flags = (
            "second_source_ready",
            "copied_obelisk_owned_payload",
            "no_ue_internals_in_public_abi",
            "append_only_abi",
            "capability_gated",
            "owner_token_handle_registration",
            "owner_scoped_unregister",
            "plugin_owner_cleanup",
        )
        required_path_lists = (
            "second_source_reports",
            "abi_tests",
            "sdk_consumer_tests",
            "lifecycle_tests",
            "docs",
        )

        for event in promoted_events:
            with self.subTest(event=event.get("event_id", "<missing>")):
                self.assertIsInstance(event.get("event_id"), str)
                self.assertIsInstance(event.get("capability"), str)
                self.assertRegex(event["capability"], r"^OBELISK_API_CAPABILITY_[A-Z0-9_]+_EVENTS$")
                target_sets = event.get("target_sets")
                self.assertIsInstance(target_sets, list, f"{event.get('event_id')} missing list target_sets")
                self.assertEqual(
                    target_sets,
                    V010_GAMEPLAY_POLICY_TARGET_SETS,
                    f"{event.get('event_id')} target_sets widened the v0.1-rc public scope",
                )
                self.assertGreater(len(target_sets), 0, f"{event.get('event_id')} has no target_sets")
                for target_set in target_sets:
                    self.assertIsInstance(target_set, str)
                    self.assertNotEqual(target_set.strip(), "")
                    self.assertNotIn("/", target_set)
                backing_target_set = event.get("backing_target_set")
                self.assertIsInstance(backing_target_set, str)
                self.assertIn(backing_target_set, target_sets)
                for flag in required_boolean_flags:
                    self.assertIs(event.get(flag), True, f"{event.get('event_id')} missing {flag}=true")
                public_fields = event.get("public_fields")
                self.assertIsInstance(public_fields, list, f"{event.get('event_id')} missing public_fields")
                self.assertEqual(
                    public_fields,
                    [
                        "abi_version",
                        "struct_size",
                        "event_kind",
                        "resource_kind",
                        "flags",
                        "field_mask",
                        "bool_values",
                        "int32_values",
                    ],
                    f"{event.get('event_id')} public_fields widened the minimal copied POD contract",
                )
                self.assertEqual(
                    event.get("resource_kinds"),
                    V010_GAMEPLAY_POLICY_RESOURCE_KINDS,
                    f"{event.get('event_id')} resource_kinds widened the public resource contract",
                )
                self.assertEqual(
                    event.get("event_kind_masks"),
                    V010_GAMEPLAY_POLICY_EVENT_KIND_MASKS,
                    f"{event.get('event_id')} event_kind_masks widened the public event contract",
                )
                event_kinds = event.get("event_kinds")
                self.assertIsInstance(event_kinds, list, f"{event.get('event_id')} missing event_kinds")
                self.assertEqual(len(event_kinds), 8, f"{event.get('event_id')} event kind count drifted")
                for event_kind in event_kinds:
                    self.assertIsInstance(event_kind, dict)
                    self.assertRegex(
                        event_kind.get("kind", ""),
                        r"^OBELISK_GAMEPLAY_POLICY_EVENT_KIND_[A-Z0-9_]+$",
                    )
                    self.assertIsInstance(event_kind.get("stable_name"), str)
                    self.assertIn(event_kind.get("resource_kind"), event.get("resource_kinds", []))
                    self.assertRegex(
                        event_kind.get("event_kind_mask", ""),
                        r"^OBELISK_GAMEPLAY_POLICY_EVENT_MASK_[A-Z0-9_]+$",
                    )
                    self.assertIsInstance(event_kind.get("field_mask"), list)
                    self.assertGreater(len(event_kind["field_mask"]), 0)
                self.assertIn("not promoted", event.get("inventory_sdk", ""))
                target_set_evidence = event.get("target_set_evidence")
                self.assertIsInstance(
                    target_set_evidence,
                    list,
                    f"{event.get('event_id')} missing target_set_evidence",
                )
                evidence_by_target_set = {
                    item.get("target_set"): item
                    for item in target_set_evidence
                    if isinstance(item, dict)
                }
                self.assertEqual(set(evidence_by_target_set), set(target_sets))
                if event.get("event_id") == "obelisk.gameplay_policy.v1":
                    self.assertIn(
                        "docs/research/2026-05-29-structure-observer-intake-refresh.md",
                        event.get("second_source_reports", []),
                    )
                    for sdk_path in (
                        "tests/sdk_installed_consumer/consumer_plugin.cpp",
                        "tests/sdk_installed_consumer/consumer_fixture.cpp",
                        "tests/sdk_installed_consumer/c_abi_plugin.c",
                    ):
                        self.assertIn(sdk_path, event.get("sdk_consumer_tests", []))
                    self.assertIn(
                        "docs/research/2026-05-29-structure-observer-intake-refresh.md",
                        evidence_by_target_set["structure-observer-intake"].get("reports", []),
                    )
                for target_set, item in evidence_by_target_set.items():
                    self.assertIsInstance(target_set, str)
                    self.assertIsInstance(item.get("scope"), str)
                    if target_set == "minimal-second-source-intake":
                        scope = item["scope"]
                        for required_scope_term in (
                            "layout-only",
                            "no standalone",
                            "module-specific",
                            "inventory",
                        ):
                            self.assertIn(required_scope_term, scope)
                    reports = item.get("reports")
                    self.assertIsInstance(reports, list)
                    self.assertGreater(len(reports), 0)
                    for report in reports:
                        self.assertIsInstance(report, str)
                        self.assertNotIn("/servidor/ark", report)
                        self.assertTrue((REPO_ROOT / report).exists(), f"missing target-set evidence path {report}")
                excluded_target_sets = event.get("excluded_target_sets", [])
                self.assertIsInstance(excluded_target_sets, list)
                excluded_names = {
                    item.get("target_set")
                    for item in excluded_target_sets
                    if isinstance(item, dict)
                }
                self.assertIn("inventory-action-compact-intake", excluded_names)
                self.assertNotIn("inventory-action-compact-intake", target_sets)
                for field in required_path_lists:
                    entries = event.get(field)
                    self.assertIsInstance(entries, list, f"{event.get('event_id')} missing list {field}")
                    self.assertGreater(len(entries), 0, f"{event.get('event_id')} has no {field}")
                    for entry in entries:
                        self.assertIsInstance(entry, str)
                        self.assertNotIn("/servidor/ark", entry)
                        self.assertTrue((REPO_ROOT / entry).exists(), f"missing evidence path {entry}")

    def test_public_gameplay_event_readiness_audit_documents_gameplay_policy_event_promotion(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-29-public-gameplay-event-readiness-audit.md"
        text = note.read_text(encoding="utf-8")

        required_terms = (
            "GameplayPolicyEvent",
            "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
            "structure-observer-intake",
            "minimal-second-source-intake",
            "promotion_gate.ready=true",
            "copied Obelisk-owned POD",
            "no UE internals in the ABI",
            "Inventory-backed policy signals are now promoted only through `GameplayPolicyEvent`",
            "pinCode",
            "FName/GObjects",
            "docs/public_gameplay_events.json",
            "`minimal-second-source-intake` is not a standalone public gameplay API",
            "No public Inventory SDK",
            "`InventoryPolicyEvent` ABI",
        )

        for term in required_terms:
            self.assertIn(term, text)

    def test_public_gameplay_event_manifest_allows_minimal_intake_only_for_gameplay_policy_inventory(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        promoted_events = manifest.get("promoted_events")
        self.assertIsInstance(promoted_events, list)

        for event in promoted_events:
            with self.subTest(event=event.get("event_id", "<missing>")):
                self.assertNotEqual(event.get("backing_target_set"), "minimal-second-source-intake")
                if "minimal-second-source-intake" in event.get("target_sets", []):
                    self.assertEqual(event.get("event_id"), "obelisk.gameplay_policy.v1")
                    self.assertEqual(event.get("inventory_backing_target_set"), "minimal-second-source-intake")
                    self.assertEqual(
                        event.get("resource_kinds"),
                        V010_GAMEPLAY_POLICY_RESOURCE_KINDS,
                    )
                    self.assertEqual(
                        event.get("event_kind_masks"),
                        V010_GAMEPLAY_POLICY_EVENT_KIND_MASKS,
                    )
                    self.assertIn("not promoted", event.get("inventory_sdk", ""))

    def test_public_gameplay_policy_manifest_redacts_inventory_backing_identity_and_authority(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        gameplay_policy = next(
            (
                event for event in manifest.get("promoted_events", [])
                if isinstance(event, dict) and event.get("event_id") == "obelisk.gameplay_policy.v1"
            ),
            None,
        )
        self.assertIsNotNone(gameplay_policy)

        resource_contract = gameplay_policy.get("resource_contract", "")
        assert_explicit_category_only_resource_contract(
            self,
            resource_contract,
            require_kind_only=True,
        )
        self.assertIn("no persistent handle", normalized(resource_contract))
        self.assertEqual(gameplay_policy.get("payload"), "copied POD scalar fields only")
        self.assertIn("not promoted", gameplay_policy.get("inventory_sdk", ""))

        redacted_fields = gameplay_policy.get("redacted_fields")
        self.assertIsInstance(redacted_fields, list)
        for redacted in (
            "UObject pointers",
            "UFunction pointers",
            "FName/GObjects indices",
            "raw parameter buffers",
            "player identity",
            "inventory object identity",
            "item identity",
            "mutation or return override authority",
            "pinCode",
        ):
            self.assertIn(redacted, redacted_fields)

        target_set_evidence = gameplay_policy.get("target_set_evidence")
        self.assertIsInstance(target_set_evidence, list)
        minimal_intake = next(
            (
                evidence for evidence in target_set_evidence
                if isinstance(evidence, dict) and evidence.get("target_set") == "minimal-second-source-intake"
            ),
            None,
        )
        self.assertIsNotNone(minimal_intake)
        minimal_scope = minimal_intake.get("scope", "")
        self.assertIn("layout-only", minimal_scope)
        self.assertIn("no standalone", minimal_scope)
        self.assertIn("inventory", minimal_scope)

    def test_obasevents_documents_binary_scoped_fname_resolution(self) -> None:
        text = (REPO_ROOT / "docs/oBaseEvents.md").read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())

        self.assertIn("validate_fname_index_manifest.py", text)
        self.assertIn("--ark-binary /path/to/offline/ShooterGameServer", text)
        self.assertIn("--ark-binary-sha256", text)
        self.assertIn("--resolve-name ServerChat", text)
        self.assertIn(
            "Candidate-only manifests are rejected for name resolution by default",
            normalized_text,
        )
        self.assertIn(
            "rejects `--ark-binary` paths under protected live-server roots",
            normalized_text,
        )
        self.assertIn("including symlinked live-server paths", normalized_text)
        self.assertIn("copy the binary to an offline artifact location first", normalized_text)
        self.assertIn("--allow-candidate", text)
        self.assertIn("generated_for_ark_binary_sha256", text)

    def test_public_docs_do_not_publish_local_server_paths_or_internal_coordination(self) -> None:
        forbidden = (
            "/servidor/ark",
            "agent handoff",
            "external-agent",
            "queue task",
            "goal tool",
            "CURRENT.md",
        )
        offenders: list[str] = []

        for path in PUBLIC_DOC_FILES:
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            for token in forbidden:
                haystack = lowered if token == token.lower() else text
                if token in haystack:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_chat_route_observer_plan_stays_internal_only(self) -> None:
        public_files = [
            PUBLIC_API_HEADER,
            PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
            *PUBLIC_DOC_FILES,
        ]
        forbidden = (
            "enable-chat-route-observer",
            "OBELISK_ENABLE_CHAT_ROUTE_OBSERVER",
            "ChatRouteObserver",
            "--require-route-send-modes",
            "accepted_route_send_modes",
            "missing_required_route_send_modes",
        )

        offenders: list[str] = []
        for path in public_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
        self.assertEqual(offenders, [])

        plan = (REPO_ROOT / "docs/research/2026-05-29-chat-route-observer-plan.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(plan.split())
        for required in (
            "default-off internal route observer",
            "never dispatch a plugin callback",
            "Do not set `OBELISK_API_CAPABILITY_CHAT_EVENTS`",
            "change `ObeliskApi`",
            "delivery_claim=none",
            "not plugin-facing `ChatMessageEvent` delivery evidence",
        ):
            self.assertIn(required, normalized)

    def test_public_header_exposes_only_minimal_chat_message_event_api(self) -> None:
        header = (REPO_ROOT / "include/obelisk/ObeliskApi.h").read_text(encoding="utf-8")
        required = [
            "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            "OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION",
            "OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD",
            "ObeliskStringView",
            "ObeliskChatMessageEvent",
            "ObeliskChatSendMode",
            "ObeliskChatMessageEventCallback",
            "RegisterChatMessageEventWithOwnerTokenHandle",
            "UnregisterChatMessageEventWithOwnerToken",
        ]
        forbidden = [
            "ObeliskChatMessageSubscription",
            "ObeliskOnChatMessageCallback",
            "RegisterOnChatMessage",
            "ObeliskOnChatMessageCallback",
            "sender_name",
            "sender_platform",
            "sender_name_index",
            "UObject*",
            "UFunction*",
        ]

        for token in required:
            self.assertIn(token, header)
        offenders = [token for token in forbidden if token in header]
        self.assertEqual(offenders, [])

    def test_public_sdk_surface_has_no_structure_api_until_promotion(self) -> None:
        scanned_roots = [
            REPO_ROOT / "include" / "obelisk",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
            REPO_ROOT / "plugins",
        ]
        scanned_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs" / "oBaseEvents.md",
        ]
        forbidden = (
            "OBELISK_API_CAPABILITY_STRUCTURE_EVENTS",
            "ObeliskStructureEvent",
            "ObeliskStructureEventSubscription",
            "ObeliskOnStructureEventCallback",
            "RegisterOnStructureEvent",
            "RegisterOnStructureEvents",
            "OnStructureEvent",
            "OnStructureEvents",
            "UnregisterStructureEvent",
            "UnregisterStructureEvents",
            "StructureEventView",
            "StructureScalarValue",
            "StructureEventCallback",
            "StructureEventSubscription",
            "StructureEventDispatcher",
            "StructureReflection",
            "ProcessEventStructureReflection",
        )
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".c", ".cpp", ".h", ".hpp", ".md", ".txt"}:
                    scanned_files.append(path)

        for path in scanned_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if path.relative_to(REPO_ROOT).as_posix().startswith("plugins/oProcessTimer/") and token in CORE_TIMER_EXAMPLE_TOKENS:
                    continue
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_sdk_surface_has_no_inventory_policy_api_until_promotion(self) -> None:
        scanned_roots = [
            REPO_ROOT / "include" / "obelisk",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
            REPO_ROOT / "plugins",
        ]
        scanned_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs" / "oBaseEvents.md",
        ]
        forbidden = (
            "OBELISK_API_CAPABILITY_INVENTORY_POLICY_EVENTS",
            "ObeliskInventoryPolicyEvent",
            "ObeliskInventoryPolicyEventSubscription",
            "ObeliskOnInventoryPolicyEventCallback",
            "RegisterInventoryPolicyEvent",
            "RegisterOnInventoryPolicyEvent",
            "OnInventoryPolicyEvent",
            "UnregisterInventoryPolicyEvent",
            "InventoryPolicyEventView",
            "InventoryPolicyScalarValue",
            "InventoryPolicyEventCallback",
            "InventoryPolicyEventSubscription",
            "InventoryPolicyEventDispatcher",
            "ProcessEventInventoryReflection",
        )
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".c", ".cpp", ".h", ".hpp", ".md", ".txt"}:
                    scanned_files.append(path)

        for path in scanned_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if path.relative_to(REPO_ROOT).as_posix().startswith("plugins/oProcessTimer/") and token in CORE_TIMER_EXAMPLE_TOKENS:
                    continue
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_sdk_consumers_cover_minimal_chat_message_event_api(self) -> None:
        scanned_roots = [
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
        ]
        required = {
            "OBELISK_API_CAPABILITY_CHAT_EVENTS": False,
            "ObeliskChatMessageEvent": False,
            "RegisterChatMessageEventWithOwnerTokenHandle": False,
            "UnregisterChatMessageEventWithOwnerToken": False,
            "OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD": False,
        }
        forbidden = ("RegisterOnChatMessage", "ObeliskChatMessageSubscription")

        for root in scanned_roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".c", ".cpp", ".h", ".hpp", ".txt"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for token in required:
                    if token in text:
                        required[token] = True
                offenders = [token for token in forbidden if token in text]
                self.assertEqual(offenders, [], f"{path.relative_to(REPO_ROOT)} used deprecated chat API names")

        self.assertEqual([token for token, seen in required.items() if not seen], [])

    def test_public_manifest_declares_chat_message_rc_surface(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        rc_events = manifest.get("rc_events")
        self.assertIsInstance(rc_events, list)
        chat = next(
            (event for event in rc_events if event.get("event_id") == "obelisk.chat_message.v1"),
            None,
        )
        self.assertIsNotNone(chat)
        self.assertEqual(chat.get("capability"), "OBELISK_API_CAPABILITY_CHAT_EVENTS")
        self.assertEqual(chat.get("abi_struct"), "ObeliskChatMessageEvent")
        self.assertEqual(chat.get("registration"), "RegisterChatMessageEventWithOwnerTokenHandle")
        self.assertEqual(chat.get("unregister"), "UnregisterChatMessageEventWithOwnerToken")
        self.assertEqual(chat.get("target_sets"), V010_CHAT_MESSAGE_TARGET_SETS)
        self.assertEqual(
            chat.get("public_fields"),
            [
                "abi_version",
                "struct_size",
                "send_mode",
                "reserved0",
                "flags",
                "sequence",
                "message",
            ],
        )
        self.assertEqual(
            chat.get("live_debug_validated_send_modes"),
            [
                "OBELISK_CHAT_SEND_MODE_GLOBAL",
                "OBELISK_CHAT_SEND_MODE_TRIBE",
                "OBELISK_CHAT_SEND_MODE_LOCAL",
                "OBELISK_CHAT_SEND_MODE_ALLIANCE",
            ],
        )
        self.assertEqual(chat.get("live_debug_unvalidated_send_modes"), [])
        self.assertIn("all four known chat send modes", chat.get("mode_coverage_note", ""))
        self.assertIn("does not promote identity", chat.get("mode_coverage_note", ""))
        self.assertIn("no sender identity", chat.get("scope", ""))
        self.assertIs(chat.get("copied_obelisk_owned_payload"), True)
        self.assertIs(chat.get("no_ue_internals_in_public_abi"), True)
        self.assertIs(chat.get("append_only_abi"), True)
        self.assertIs(chat.get("capability_gated"), True)
        self.assertIs(chat.get("owner_token_handle_registration"), True)
        self.assertIs(chat.get("owner_scoped_unregister"), True)
        self.assertIs(chat.get("plugin_owner_cleanup"), True)
        self.assertIs(chat.get("second_source_ready"), True)
        self.assertIs(chat.get("runtime_producer_gate_implemented"), True)
        self.assertIs(chat.get("live_debug_delivery_pending"), False)
        self.assertIs(chat.get("live_debug_delivery_validated"), True)
        self.assertEqual(chat.get("live_debug_delivery_accepted_event_count"), 18)
        live_debug_delivery_evidence = chat.get("live_debug_delivery_evidence")
        self.assertEqual(
            live_debug_delivery_evidence,
            "docs/research/2026-05-29-chat-message-second-source-readiness.md",
        )
        self.assertNotIn("/servidor/ark", live_debug_delivery_evidence)
        self.assertTrue(
            (REPO_ROOT / live_debug_delivery_evidence).exists(),
            f"missing chat live-debug evidence path {live_debug_delivery_evidence}",
        )
        reports = chat.get("second_source_reports")
        self.assertIsInstance(reports, list)
        self.assertGreater(len(reports), 0)
        for report in reports:
            self.assertIsInstance(report, str)
            self.assertNotIn("/servidor/ark", report)
            self.assertTrue((REPO_ROOT / report).exists(), f"missing chat second-source report path {report}")
        for field in ("abi_tests", "sdk_consumer_tests", "lifecycle_tests", "docs"):
            entries = chat.get(field)
            self.assertIsInstance(entries, list)
            self.assertGreater(len(entries), 0)
            for entry in entries:
                self.assertTrue((REPO_ROOT / entry).exists(), f"missing chat RC evidence path {entry}")
        for sdk_path in (
            "tests/sdk_installed_consumer/consumer_plugin.cpp",
            "tests/sdk_installed_consumer/consumer_fixture.cpp",
            "tests/sdk_installed_consumer/c_abi_plugin.c",
        ):
            self.assertIn(sdk_path, chat.get("sdk_consumer_tests", []))

    def test_public_sdk_has_no_deprecated_or_experimental_chat_api_names(self) -> None:
        scanned_roots = [
            REPO_ROOT / "include" / "obelisk",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
            REPO_ROOT / "plugins",
        ]
        forbidden_substrings = (
            "ObeliskChatMessageSubscription",
            "ObeliskOnChatMessageCallback",
            "RegisterOnChatMessage",
            "sender_name_index",
            "sender_platform",
        )
        forbidden_regexes = (
            r"\bOnChatMessage\s*\(",
            r"\bUnregisterChatMessage\s*\(",
        )
        offenders: list[str] = []
        for root in scanned_roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".c", ".cpp", ".h", ".hpp", ".txt"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for token in forbidden_substrings:
                    if token in text:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
                for pattern in forbidden_regexes:
                    if re.search(pattern, text):
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {pattern}")

        self.assertEqual(offenders, [])

    def test_sdk_consumer_does_not_depend_on_experimental_chat_reflection(self) -> None:
        sdk_dir = REPO_ROOT / "tests/sdk_consumer"
        offenders: list[str] = []
        for path in sdk_dir.rglob("*"):
            if not path.is_file() or path.suffix not in {".cpp", ".h", ".hpp", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            for token in ("OBELISK_ENABLE_CHAT_REFLECTION", "ProcessEventChatReflection", "ChatReflection"):
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_examples_do_not_use_call_process_event_escape_hatch(self) -> None:
        scanned_roots = [
            REPO_ROOT / "plugins",
            REPO_ROOT / "tests" / "sdk_consumer",
        ]
        allowed_fixture_files = {
            REPO_ROOT / "tests" / "sdk_consumer" / "SdkConsumerFixture.cpp",
        }
        forbidden = (
            "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT",
            ".CallProcessEvent",
            "->CallProcessEvent",
        )
        offenders: list[str] = []
        for root in scanned_roots:
            for path in root.rglob("*"):
                if path in allowed_fixture_files:
                    continue
                if not path.is_file() or path.suffix not in {".cpp", ".h", ".hpp", ".c"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    if token in text:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_unpromoted_gameplay_token_list_covers_documented_examples(self) -> None:
        tokens = set(unpromoted_gameplay_tokens())
        sdk_consumer_tokens = set(unpromoted_sdk_consumer_tokens())

        for token in (
            "ObeliskCommand",
            "RegisterOnTimer",
            "OBELISK_API_CAPABILITY_PERMISSION_EVENTS",
            "ObeliskPlayers",
            "OBELISK_API_CAPABILITY_BUFF_EVENTS",
            "ObeliskBuff",
            "RegisterOnBuff",
            "UnregisterCommands",
        ):
            self.assertIn(token, tokens)

        for token in (
            "OBELISK_API_CAPABILITY_MISSION_EVENTS",
            "OBELISK_API_CAPABILITY_MISSION_POLICY_EVENTS",
            "ObeliskMissionEvent",
            "ObeliskMissionPolicyEvent",
            "MissionEventCallback",
            "MissionEventSubscription",
            "RegisterMissionEvent",
            "RegisterMissionPolicyEvent",
            "RegisterOnMissionEvent",
            "UnregisterMissionEvent",
        ):
            self.assertIn(token, sdk_consumer_tokens)

    def test_public_sdk_headers_have_no_gameplay_module_api_until_promotion(self) -> None:
        offenders: list[str] = []
        forbidden = unpromoted_gameplay_tokens()
        for path in (REPO_ROOT / "include" / "obelisk").rglob("*"):
            if not path.is_file() or path.suffix not in {".h", ".hpp"}:
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in CORE_TIMER_PUBLIC_TOKENS:
                    continue
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_sdk_headers_have_no_resource_identity_or_ue_global_api_until_promotion(self) -> None:
        offenders: list[str] = []
        for path in (REPO_ROOT / "include" / "obelisk").rglob("*"):
            if not path.is_file() or path.suffix not in {".h", ".hpp"}:
                continue
            text = strip_c_comments(path.read_text(encoding="utf-8"))
            for token in UNPROMOTED_IDENTITY_SURFACE_TOKENS:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_sdk_does_not_expose_command_admin_or_player_api_names(self) -> None:
        scanned_roots = [
            REPO_ROOT / "include" / "obelisk",
            REPO_ROOT / "plugins",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
        ]
        scanned_files = [
            PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs" / "RELEASE.md",
            REPO_ROOT / "docs" / "STATUS.md",
            REPO_ROOT / "docs" / "oBaseEvents.md",
        ]
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".c", ".cpp", ".h", ".hpp", ".md", ".txt"}:
                    scanned_files.append(path)

        for path in scanned_files:
            text = strip_c_comments(path.read_text(encoding="utf-8"))
            for token in UNPROMOTED_COMMAND_ADMIN_PLAYER_API_TOKENS:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_sdk_consumers_do_not_compile_against_blocked_v010_rc_surfaces(self) -> None:
        scanned_roots = [
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
        ]
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".c", ".cpp", ".h", ".hpp", ".txt"}:
                    continue
                text = strip_c_comments(path.read_text(encoding="utf-8"))
                for token in unpromoted_sdk_consumer_tokens():
                    if token in text:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_docs_and_examples_do_not_advertise_unpromoted_gameplay_api(self) -> None:
        scanned_roots = [
            REPO_ROOT / "plugins",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
        ]
        scanned_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs" / "RELEASE.md",
            REPO_ROOT / "docs" / "STATUS.md",
            REPO_ROOT / "docs" / "oBaseEvents.md",
        ]
        forbidden = unpromoted_gameplay_tokens()
        forbidden_positive_claims = (
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?Inventory\s+SDKs?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?StructureEvents?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?ResourceHandle\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:public\s+)?(?:gameplay\s+)?mutation\s+(?:SDKs?|APIs?|surfaces?|authority)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:public\s+)?return[- ]overrides?\s+(?:SDKs?|APIs?|surfaces?|authority)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:public\s+)?richer\s+chat\s+(?:SDKs?|APIs?|surfaces?|events?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:public\s+)?commands?\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\bInventory\s+SDKs?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bStructureEvents?\s+(?:SDKs?|APIs?|surfaces?)?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bResourceHandle\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\b(?:gameplay\s+)?mutation\s+(?:SDKs?|APIs?|surfaces?|authority)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\breturn[- ]overrides?\s+(?:SDKs?|APIs?|surfaces?|authority)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bricher\s+chat\s+(?:SDKs?|APIs?|surfaces?|events?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bcommands?\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
        )
        negated_claim_context = re.compile(
            r"\b(?:does\s+not|do\s+not|must\s+not|not|no|never|without|blocked|excludes?|outside)\b",
            re.IGNORECASE,
        )
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".c", ".cpp", ".h", ".hpp", ".md", ".txt"}:
                    scanned_files.append(path)

        for path in scanned_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if path.relative_to(REPO_ROOT).as_posix().startswith("plugins/oProcessTimer/") and token in CORE_TIMER_EXAMPLE_TOKENS:
                    continue
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
            for pattern in forbidden_positive_claims:
                for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                    context = text[max(0, match.start() - 80):match.start()]
                    if not negated_claim_context.search(context):
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {pattern}")

        self.assertEqual(offenders, [])

    def test_scalar_candidate_tooling_is_not_public_sdk_promotion(self) -> None:
        fixture_readme = (REPO_ROOT / "tests/fixtures/ufunction_snapshots/README.md").read_text(
            encoding="utf-8"
        )
        status = (REPO_ROOT / "docs/STATUS.md").read_text(encoding="utf-8")

        self.assertIn("scripts/summarize_reflection_scalar_candidates.py", fixture_readme)
        self.assertIn("--target-set mission-compact-intake", fixture_readme)
        self.assertIn("This helper is a review aid only", fixture_readme)
        self.assertIn(
            "does not replace\nsecond-source readiness reports or promote public SDK callbacks",
            fixture_readme,
        )
        self.assertIn("not a release\nreadiness gate, not RC scope", fixture_readme)
        self.assertIn("`mission-compact-intake` example remains\ncandidate-only", fixture_readme)
        self.assertIn("missions", status)
        self.assertIn("remain roadmap items", status)

    def test_offline_snapshot_fixtures_remain_candidate_only_not_public_sdk(self) -> None:
        fixture_roots = {
            REPO_ROOT / "tests/fixtures/ufunction_snapshots": (
                "obelisk.ufunction-chain.snapshot.v1",
                (
                    "candidate-only",
                    "does not replace\nsecond-source readiness reports or promote public SDK callbacks",
                    "not RC scope",
                ),
            ),
            REPO_ROOT / "tests/fixtures/scriptstruct_snapshots": (
                "obelisk.scriptstruct-chain.snapshot.v1",
                (
                    "candidate-only",
                    "not public decoding or runtime dispatch contracts",
                ),
            ),
        }

        for root, (expected_snapshot_schema, required_readme_terms) in fixture_roots.items():
            with self.subTest(root=root.relative_to(REPO_ROOT)):
                manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
                readme = (root / "README.md").read_text(encoding="utf-8")

                self.assertEqual(manifest.get("source"), "offline_core")
                self.assertEqual(manifest.get("status"), "candidate-only")
                self.assertNotIn("/servidor/ark", json.dumps(manifest, sort_keys=True))
                for term in required_readme_terms:
                    self.assertIn(term, readme)

                sha_prefix = manifest.get("sha_prefix")
                self.assertIsInstance(sha_prefix, str)
                targets = manifest.get("targets")
                self.assertIsInstance(targets, list)
                self.assertGreater(len(targets), 0)
                for target in targets:
                    self.assertIsInstance(target, dict)
                    snapshot_path = root / sha_prefix / target.get("module", "") / target.get("file", "")
                    self.assertTrue(snapshot_path.exists(), f"missing snapshot {snapshot_path}")
                    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
                    self.assertEqual(snapshot.get("schema"), expected_snapshot_schema)
                    self.assertEqual(snapshot.get("evidence", {}).get("source"), "offline_core")
                    self.assertEqual(snapshot.get("evidence", {}).get("status"), "candidate-only")
                    self.assertEqual(snapshot.get("interpretation", {}).get("status"), "candidate-only")
                    self.assertNotIn("/servidor/ark", json.dumps(snapshot, sort_keys=True))

    def test_chat_abi_preflight_documents_future_shapes(self) -> None:
        note = (REPO_ROOT / "docs/research/2026-05-27-chat-sdk-abi-preflight.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "ObeliskStringView",
            "ObeliskChatMessage",
            "ObeliskChatMessageSubscription",
            "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            "RegisterOnChatMessage",
            "Evidence-pack mode",
        ):
            self.assertIn(token, note)


if __name__ == "__main__":
    unittest.main()
