#!/usr/bin/env python3
"""Guardrails that keep experimental gameplay modules out of the public SDK."""

from __future__ import annotations

import json
import re
import runpy
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REFLECTION_TARGET_SET_VARS = runpy.run_path(str(REPO_ROOT / "scripts" / "reflection_target_sets.py"))
TARGET_SETS = REFLECTION_TARGET_SET_VARS["TARGET_SETS"]
PLANNING_ONLY_TARGET_SETS = REFLECTION_TARGET_SET_VARS["PLANNING_ONLY_TARGET_SETS"]
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
    REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
    REPO_ROOT / "docs" / "RELEASE.md",
    REPO_ROOT / "docs" / "STATUS.md",
    REPO_ROOT / "docs" / "VERSIONING.md",
    REPO_ROOT / "docs" / "oBaseEvents.md",
    REPO_ROOT / ".github" / "pull_request_template.md",
]
PUBLIC_PLUGIN_EXAMPLE_DOC_FILES = [
    REPO_ROOT / "docs" / "oDescriptorCatalog.md",
    REPO_ROOT / "docs" / "oProcessTimer.md",
]
PUBLIC_SDK_GUIDANCE_DOC_FILES = [
    *PUBLIC_DOC_FILES,
    *PUBLIC_PLUGIN_EXAMPLE_DOC_FILES,
]
SDK_MINIMAL_PLUGIN_EXAMPLE_FILES = [
    REPO_ROOT / "examples" / "sdk_minimal_plugin" / "CMakeLists.txt",
    REPO_ROOT / "examples" / "sdk_minimal_plugin" / "README.md",
    REPO_ROOT / "examples" / "sdk_minimal_plugin" / "minimal_plugin.c",
]
PUBLIC_RELEASE_SCOPE_DOC_FILES = [
    REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
    REPO_ROOT / "docs" / "RELEASE.md",
    REPO_ROOT / "docs" / "STATUS.md",
]
CHAT_COMMAND_HELPER_ROADMAP = (
    REPO_ROOT / "docs" / "research" / "2026-05-30-chat-command-helper-roadmap.md"
)
NEXTGEN_DEMAND_BOUNDARY_FILES = [
    REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
    REPO_ROOT / "docs" / "research" / "2026-05-30-nextgenplugins-reference-inventory.md",
    REPO_ROOT / "plugins" / "README.md",
]
ARKAPI_DEMAND_BOUNDARY_FILES = [
    REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
    REPO_ROOT / "docs" / "research" / "2026-05-30-v1-core-capability-map.md",
    REPO_ROOT / "docs" / "research" / "2026-05-29-module-surface-roadmap.md",
    REPO_ROOT / "docs" / "research" / "README.md",
    REPO_ROOT / "plugins" / "README.md",
    REPO_ROOT / "docs" / "research" / "2026-05-30-nextgenplugins-reference-inventory.md",
    REPO_ROOT / "docs" / "research" / "2026-05-30-aseapi-reference-scan.md",
    REPO_ROOT / "agent-skills" / "obelisk-github-research-workflow" / "SKILL.md",
    REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md",
]
PLUGIN_HUB_V1_ROADMAP_BOUNDARY_FILES = [
    REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
    REPO_ROOT / "docs" / "research" / "2026-05-30-v1-core-capability-map.md",
    REPO_ROOT / "docs" / "research" / "2026-05-29-module-surface-roadmap.md",
    REPO_ROOT / "docs" / "research" / "README.md",
    REPO_ROOT / "plugins" / "README.md",
]
PLUGIN_HUB_PUBLIC_BOUNDARY_DOC_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
    REPO_ROOT / "plugins" / "README.md",
]
RESEARCH_MODULE_BOUNDARY_README = REPO_ROOT / "docs" / "research" / "README.md"
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
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK",
        "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
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
V010_PLUGIN_METADATA_FIELDS = [
    "abi_version",
    "struct_size",
    "plugin_id",
    "name",
    "version",
    "config_file",
    "default_config_json",
]
V010_PLUGIN_INIT_CONTEXT_FIELDS = [
    "abi_version",
    "struct_size",
    "config_dir",
    "config_path",
    "instance_id",
    "plugin_owner_token",
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
V010_GAMEPLAY_POLICY_EVENT_PAYLOAD_FIELDS = [
    "abi_version",
    "struct_size",
    "event_kind",
    "resource_kind",
    "flags",
    "field_mask",
    "bool_values",
    "int32_values",
]
V010_CHAT_MESSAGE_EVENT_PAYLOAD_FIELDS = [
    "abi_version",
    "struct_size",
    "send_mode",
    "reserved0",
    "flags",
    "sequence",
    "message",
]
V010_GAMEPLAY_POLICY_TARGET_SETS = [
    "structure-observer-intake",
    "minimal-second-source-intake",
    "item-return-only-policy-slice",
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
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
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
    "inventory_item.allow_equip_check",
    "inventory_item.can_repair_check",
    "inventory_item.use_onto_item_check",
]
CHAT_MESSAGE_EVENT_PUBLIC_CLAIM_FILES = [
    PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
    *PUBLIC_SDK_GUIDANCE_DOC_FILES,
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
GAMEPLAY_POLICY_SCOPE_FORBIDDEN_RE = re.compile(
    r"\bInventory\s+SDKs?\b|"
    r"\bStructureEvents?\s+SDKs?\b|"
    r"\bResourceHandle\b|"
    r"\b(?:object|resource|player|inventory|item|structure)\s+identity\b|"
    r"\bidentity\b|"
    r"\bmutation\b|"
    r"\breturn[- ]overrides?\b",
    re.IGNORECASE,
)
GAMEPLAY_POLICY_SCOPE_NEGATORS_RE = re.compile(
    r"\b(?:blocked|does\s+not|do\s+not|excluded|excludes|keep|keeps|must\s+not|never|no|not|"
    r"outside|redacted|remain|remains|without)\b",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*")
MODULE_AGGREGATE_CENSUS_PUBLIC_CLAIM_FILES = [
    PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
    *PUBLIC_SDK_GUIDANCE_DOC_FILES,
    REPO_ROOT / "plugins" / "README.md",
]
MODULE_AGGREGATE_CENSUS_TERM_RE = re.compile(
    r"\b(?:structures?|dinos?|buffs?)[- ](?:aggregates?|aggregation|census|counts?|proximity)\b|"
    r"\b(?:aggregates?|aggregation|census|counts?|proximity)[- ](?:structures?|dinos?|buffs?)\b|"
    r"\baggregate\s+(?:structures?|dinos?|buffs?)\s+counts?\b",
    re.IGNORECASE,
)
MODULE_AGGREGATE_CENSUS_SURFACE_RE = re.compile(
    r"\b(?:SDKs?|APIs?|surfaces?|queries?|snapshots?|modules?|callbacks?)\b",
    re.IGNORECASE,
)
MODULE_AGGREGATE_CENSUS_POSITIVE_RE = re.compile(
    r"\b(?:public|promoted|production[- ]ready|production[- ]supported|stable|supported|"
    r"available|included|exposed|published|shipped)\b|"
    r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|"
    r"publish|publishes|published|support|supports|supported|include|includes|included|"
    r"provide|provides|provided)\b",
    re.IGNORECASE,
)
MODULE_AGGREGATE_CENSUS_NEGATED_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|must\s+not|not|no|never|without|blocked|"
    r"candidate[- ]only|guidance[- ]only|internal[- ]only|planning[- ]only|"
    r"research[- ]only|rejected|redacted)\b",
    re.IGNORECASE,
)
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
    "PlayerIdentity",
    "PlayerLookup",
    "ObeliskPlayerId",
    "ObeliskPlayerHandle",
    "ObeliskPlayerIdentity",
    "ObeliskPlayerLookup",
    "RegisterCommand",
    "RegisterAdminCommand",
    "RegisterPlayerCommand",
    "RegisterPlayerLookup",
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
    "ResolvePlayerIdentity",
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
PUBLIC_SDK_OPTIONAL_API_CONSUMERS = [
    REPO_ROOT / "tests" / "sdk_consumer" / "MinimalPlugin.cpp",
    REPO_ROOT / "tests" / "sdk_consumer" / "CAbiPlugin.c",
    REPO_ROOT / "tests" / "sdk_installed_consumer" / "consumer_plugin.cpp",
    REPO_ROOT / "tests" / "sdk_installed_consumer" / "c_abi_plugin.c",
    REPO_ROOT / "tests" / "sdk_installed_consumer" / "descriptor_catalog_plugin.cpp",
]
FIRST_PARTY_CPP_EXAMPLE_PLUGINS = [
    REPO_ROOT / "plugins" / "oBaseEvents" / "oBaseEvents.cpp",
    REPO_ROOT / "plugins" / "oProcessTimer" / "oProcessTimer.cpp",
    REPO_ROOT / "plugins" / "oDescriptorCatalog" / "oDescriptorCatalog.cpp",
]
PUBLIC_SDK_OPTIONAL_API_SURFACES = [
    {
        "name": "ProcessEvent owner-token handles",
        "trigger": "RegisterPreProcessEventForNameIndexWithOwnerTokenHandle",
        "capabilities": [
            "OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS",
            "OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES",
            "OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS",
        ],
        "terminal_slot": "UnregisterProcessEventCallbackWithOwnerToken",
        "required_slots": [
            "RegisterPreProcessEventForNameIndexWithOwnerTokenHandle",
            "UnregisterProcessEventCallbackWithOwnerToken",
        ],
    },
    {
        "name": "GameplayPolicyEvent callbacks",
        "trigger": "RegisterGameplayPolicyEventWithOwnerTokenHandle",
        "capabilities": ["OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS"],
        "terminal_slot": "UnregisterGameplayPolicyEventWithOwnerToken",
        "required_slots": [
            "RegisterGameplayPolicyEventWithOwnerTokenHandle",
            "UnregisterGameplayPolicyEventWithOwnerToken",
        ],
    },
    {
        "name": "resource kind descriptors",
        "trigger": "DescribeResourceKind",
        "capabilities": ["OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS"],
        "terminal_slot": "DescribeResourceKind",
        "required_slots": ["DescribeResourceKind"],
    },
    {
        "name": "gameplay policy event descriptors",
        "trigger": "DescribeGameplayPolicyEventKind",
        "capabilities": ["OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS"],
        "terminal_slot": "DescribeGameplayPolicyEventKind",
        "required_slots": ["DescribeGameplayPolicyEventKind"],
    },
    {
        "name": "ChatMessageEvent callbacks",
        "trigger": "RegisterChatMessageEventWithOwnerTokenHandle",
        "capabilities": ["OBELISK_API_CAPABILITY_CHAT_EVENTS"],
        "terminal_slot": "UnregisterChatMessageEventWithOwnerToken",
        "required_slots": [
            "RegisterChatMessageEventWithOwnerTokenHandle",
            "UnregisterChatMessageEventWithOwnerToken",
        ],
    },
    {
        "name": "timers",
        "trigger": "RegisterTimerWithOwnerTokenHandle",
        "capabilities": ["OBELISK_API_CAPABILITY_TIMERS"],
        "terminal_slot": "UnregisterTimerWithOwnerToken",
        "required_slots": [
            "RegisterTimerWithOwnerTokenHandle",
            "UnregisterTimerWithOwnerToken",
        ],
        "terminal_slot_alias": "OBELISK_CONCAT(Unregister, TimerWithOwnerToken)",
    },
]


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


def public_abi_version_macros(header: str) -> list[tuple[str, str]]:
    return re.findall(
        r"^\s*#define\s+(OBELISK_[A-Z0-9_]*ABI_VERSION)\s+([0-9]+)u\s*$",
        header,
        re.MULTILINE,
    )


def cmake_abi_version_sets(cmake: str) -> list[tuple[str, str]]:
    return re.findall(
        r"^\s*set\((OBELISK_[A-Z0-9_]*ABI_VERSION)\s+([0-9]+)\)\s*$",
        cmake,
        re.MULTILINE,
    )


def cmake_abi_version_derivations(cmake: str) -> list[str]:
    return re.findall(
        r"^\s*obelisk_read_public_abi_version\((OBELISK_[A-Z0-9_]*ABI_VERSION)\)\s*$",
        cmake,
        re.MULTILINE,
    )


def package_config_abi_version_sets(package_config: str) -> list[tuple[str, str]]:
    return re.findall(
        r"^\s*set\((Obelisk_[A-Z0-9_]*ABI_VERSION)\s+@(OBELISK_[A-Z0-9_]*ABI_VERSION)@\)\s*$",
        package_config,
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


def public_struct_field_names(header: str, struct_name: str) -> list[str]:
    match = re.search(
        rf"typedef\s+struct\s+{re.escape(struct_name)}\s*\{{(?P<body>.*?)\}}\s*"
        rf"{re.escape(struct_name)}\s*;",
        strip_c_comments(header),
        re.DOTALL,
    )
    if not match:
        raise AssertionError(f"typedef struct {struct_name} block not found")

    fields: list[str] = []
    for declaration in match.group("body").split(";"):
        declaration = " ".join(declaration.split())
        if not declaration:
            continue
        field = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]+\])?$", declaration)
        if field:
            fields.append(field.group(1))
    return fields


def public_callback_typedefs(header: str) -> list[str]:
    return re.findall(
        r"typedef\s+[^;(){}]+?\(\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\(",
        strip_c_comments(header),
    )


def exported_shutdown_body(source: str) -> str:
    marker = "ObeliskPlugin_Shutdown"
    marker_index = source.find(marker)
    if marker_index < 0:
        raise AssertionError("ObeliskPlugin_Shutdown not found")

    open_brace = source.find("{", marker_index)
    if open_brace < 0:
        raise AssertionError("ObeliskPlugin_Shutdown body not found")

    depth = 0
    for index in range(open_brace, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace + 1:index]

    raise AssertionError("ObeliskPlugin_Shutdown body is incomplete")


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


def positive_module_aggregate_census_claims(text: str, relative_path: str) -> list[str]:
    offenders: list[str] = []

    for segment_start, segment in sentence_like_segments(text):
        if not MODULE_AGGREGATE_CENSUS_TERM_RE.search(segment):
            continue
        if not (
            MODULE_AGGREGATE_CENSUS_SURFACE_RE.search(segment)
            and MODULE_AGGREGATE_CENSUS_POSITIVE_RE.search(segment)
        ):
            continue
        if MODULE_AGGREGATE_CENSUS_NEGATED_RE.search(segment):
            continue

        line = text.count("\n", 0, segment_start) + 1
        offenders.append(f"{relative_path}:{line}: {normalized(segment)}")

    return offenders


def json_string_values(value: object, path: str) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        values: list[tuple[str, str]] = []
        for key, child in value.items():
            values.extend(json_string_values(child, f"{path}.{key}"))
        return values
    if isinstance(value, list):
        values = []
        for index, child in enumerate(value):
            values.extend(json_string_values(child, f"{path}[{index}]"))
        return values
    if isinstance(value, str):
        return [(path, value)]
    return []


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
            r"\bpromot(?:e|ed|es|ing)\s+(?:a\s+)?(?:public\s+)?(?:structure\s+)?build[- ]policy\s+(?:APIs?|SDKs?|surfaces?)\b",
            r"\bpublic\s+(?:structure\s+)?build[- ]policy\s+(?:APIs?|SDKs?|surfaces?)\b",
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

    def test_gameplay_policy_structure_inventory_claims_do_not_become_module_sdks_or_authority(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        sources: list[tuple[str, str]] = []

        for path, value in json_string_values(manifest, "manifest"):
            sources.append((f"{PUBLIC_GAMEPLAY_EVENTS_MANIFEST.relative_to(REPO_ROOT)}:{path}", value))
        for path in PUBLIC_SDK_GUIDANCE_DOC_FILES:
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(REPO_ROOT)
            for line, segment in sentence_like_segments(text):
                sources.append((f"{relative}:{line}", segment))

        offenders: list[str] = []
        for source, segment in sources:
            if "GameplayPolicyEvent" not in segment:
                continue
            if not re.search(
                r"\b(?:inventory|inventory-backed|structure|structure-backed|StructureEvents?)\b",
                segment,
                flags=re.IGNORECASE,
            ):
                continue
            if not GAMEPLAY_POLICY_SCOPE_FORBIDDEN_RE.search(segment):
                continue
            if GAMEPLAY_POLICY_SCOPE_NEGATORS_RE.search(segment):
                continue
            offenders.append(f"{source}: {normalized(segment)}")

        self.assertEqual(offenders, [])

    def test_contributor_docs_do_not_promote_blocked_sdk_surfaces_or_authority(self) -> None:
        forbidden_positive_claims = (
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:a\s+)?(?:public\s+)?Inventory\s+SDKs?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:a\s+)?(?:public\s+)?StructureEvents?(?:\s+(?:SDKs?|APIs?|surfaces?))?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:a\s+)?(?:public\s+)?structure\s+(?:aggregate|census|counts?|proximity)(?:\s+(?:SDKs?|APIs?|surfaces?|snapshots?|queries?))?\b",
            r"\bstructure\s+(?:aggregate|census|counts?|proximity)(?:\s+(?:SDKs?|APIs?|surfaces?|snapshots?|queries?))?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\baggregate\s+structure\s+counts?(?:\s+(?:SDKs?|APIs?|surfaces?|snapshots?|queries?))?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:a\s+)?(?:public\s+)?(?:structure\s+)?build[- ]policy\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:a\s+)?(?:public\s+)?ResourceHandle(?:\s+(?:SDKs?|APIs?|surfaces?))?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:public\s+)?(?:resource|object|player|sender|inventory|item|structure|tribe|UE|game\s+object)\s+identity(?:\s+(?:APIs?|surfaces?|authority))?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:public\s+)?(?:gameplay\s+)?mutation(?:\s+(?:APIs?|SDKs?|surfaces?|authority))?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:public\s+)?return[- ]overrides?(?:\s+(?:APIs?|SDKs?|surfaces?|authority))?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported|include|includes|included|provide|provides|provided)\s+(?:a\s+)?(?:public\s+)?(?:storage|database|webhook)\s+(?:SDKs?|APIs?|services?|surfaces?)\b",
            r"\b(?:storage|database|webhook)\s+(?:SDKs?|APIs?|services?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bInventory\s+SDKs?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bStructureEvents?(?:\s+(?:SDKs?|APIs?|surfaces?))?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\b(?:structure\s+)?build[- ]policy\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bResourceHandle(?:\s+(?:SDKs?|APIs?|surfaces?))?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\b(?:resource|object|player|sender|inventory|item|structure|tribe|UE|game\s+object)\s+identity(?:\s+(?:APIs?|surfaces?|authority))?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\b(?:gameplay\s+)?mutation(?:\s+(?:APIs?|SDKs?|surfaces?|authority))?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\breturn[- ]overrides?(?:\s+(?:APIs?|SDKs?|surfaces?|authority))?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
        )
        negated_claim_context = re.compile(
            r"\b(?:does\s+not|do\s+not|must\s+not|not|no|never|without|blocked|excludes?|outside|rejected|redacted|remain|remains)\b",
            re.IGNORECASE,
        )
        offenders: list[str] = []

        for path in PUBLIC_SDK_GUIDANCE_DOC_FILES:
            text = path.read_text(encoding="utf-8")
            for line, segment in sentence_like_segments(text):
                context_start = max(0, line - 160)
                negation_context = text[context_start:line + len(segment)]
                for pattern in forbidden_positive_claims:
                    if (
                        re.search(pattern, segment, flags=re.IGNORECASE) and
                        not negated_claim_context.search(negation_context)
                    ):
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{line}: {normalized(segment)}")
                        break

        self.assertEqual(offenders, [])

    def test_structure_aggregate_census_public_docs_stay_planning_or_blocked(self) -> None:
        guarded_terms = re.compile(
            r"\b(?:structure[- ]aggregate|structure[- ]census|structure[- ]proximity|"
            r"structure[- ]counts?|aggregate\s+structure\s+counts?)\b",
            re.IGNORECASE,
        )
        allowed_context = re.compile(
            r"\b(?:blocked|does\s+not|do\s+not|future|guidance\s+only|no\s+public|"
            r"no\s+sdk|not\s+public|not\s+ready|planning[- ]only|redacted|remain|"
            r"requires?|still\s+needs)\b",
            re.IGNORECASE,
        )
        offenders: list[str] = []

        for path in PUBLIC_SDK_GUIDANCE_DOC_FILES:
            text = path.read_text(encoding="utf-8")
            for paragraph in re.split(r"\n\s*\n", text):
                if not guarded_terms.search(paragraph):
                    continue
                if not allowed_context.search(normalized(paragraph)):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {normalized(paragraph)}")

        self.assertEqual(offenders, [])

    def test_module_aggregate_census_positive_claim_detector_covers_structure_dino_and_buff(self) -> None:
        forbidden = [
            "The future public structure-census API is available.",
            "Obelisk ships public dino census snapshots.",
            "Buff aggregate SDK is supported.",
            "Aggregate dino counts API is promoted.",
            "Buff aggregate SDK remains available.",
        ]
        allowed = [
            "Structure aggregate census planning-only evidence stays internal.",
            "No public buff aggregate API is promoted.",
            "Dino census API requires a promotion gate before use.",
            "Buff aggregate SDK remains blocked.",
        ]

        for text in forbidden:
            with self.subTest(kind="forbidden", text=text):
                self.assertNotEqual(
                    positive_module_aggregate_census_claims(text, "synthetic.md"),
                    [],
                )
        for text in allowed:
            with self.subTest(kind="allowed", text=text):
                self.assertEqual(
                    positive_module_aggregate_census_claims(text, "synthetic.md"),
                    [],
                )

    def test_public_material_does_not_claim_structure_dino_or_buff_aggregate_census_sdk_or_api(self) -> None:
        offenders: list[str] = []

        for path in MODULE_AGGREGATE_CENSUS_PUBLIC_CLAIM_FILES:
            text = path.read_text(encoding="utf-8")
            if path == PUBLIC_GAMEPLAY_EVENTS_MANIFEST:
                text = json.dumps(json.loads(text), sort_keys=True, indent=2)
            offenders.extend(
                positive_module_aggregate_census_claims(
                    text,
                    str(path.relative_to(REPO_ROOT)),
                )
            )

        self.assertEqual(offenders, [])

    def test_research_index_defines_module_layout_terms_as_non_public_non_callable(self) -> None:
        readme = RESEARCH_MODULE_BOUNDARY_README.read_text(encoding="utf-8")
        compact = normalized(readme)

        required = (
            "`promotion_gate.ready=true`, `accepted targets`, and `candidate` in\n"
            "module-specific notes mean offline evidence readiness for the named layout or artifact\n"
            "gate only",
            "They do not make the named UE functions callable or usable plugin functions",
            "they do not authorize public SDK surfaces",
            "They are not public SDK module names, ABI commitments,\n"
            "runtime hooks, callback families",
        )

        for text in required:
            with self.subTest(text=text):
                self.assertIn(normalized(text), compact)

        for term in (
            "Current v1 research lane snapshot from the current notes",
            "Treat chat as one small copied notification lane, not the v1 module center.",
            "Inventory lane",
            "Structures lane",
            "Items lane",
            "Mission lane",
            "Dino lane",
            "Buff lane",
            "Tribe lane",
            "Transfer lane",
            "Admin/permissions lane",
            "Keep structure target sets layout-only unless a strict readiness note promotes a named copied surface",
            "Keep transfer as offline/internal until copied payload ownership, privacy/redaction, lifecycle, second-source/static evidence, ABI tests, installed SDK consumer coverage, and approved runtime validation all pass.",
            "admin, permissions, RCON, economy, storage",
        ):
            with self.subTest(term=term):
                self.assertIn(term, compact)

    def test_plugin_hub_planning_uses_arkapi_sources_as_demand_dictionary_only(self) -> None:
        texts = {
            path.relative_to(REPO_ROOT).as_posix(): path.read_text(encoding="utf-8")
            for path in ARKAPI_DEMAND_BOUNDARY_FILES
        }

        for text, required in (
            (texts["docs/PLUGIN_HUB_FOUNDATION_V1.md"], "does not promise ArkApi/AseApi\ncompatibility"),
            (texts["docs/PLUGIN_HUB_FOUNDATION_V1.md"], "demand dictionaries only"),
            (texts["docs/PLUGIN_HUB_FOUNDATION_V1.md"], "rebuilt through Obelisk\nreflection"),
            (texts["docs/PLUGIN_HUB_CAPABILITY_MATRIX.md"], "not as\nportable behavior, source, ABI, constants, schemas, command parsers, or implementation\npatterns"),
            (texts["docs/PLUGIN_HUB_CAPABILITY_MATRIX.md"], "Rebuild every promoted surface through Obelisk reflection"),
            (texts["docs/PLUGIN_HUB_CAPABILITY_MATRIX.md"], "provenance for\n"
             "demand analysis only"),
            (texts["docs/PLUGIN_HUB_CAPABILITY_MATRIX.md"], "not license clearance, runtime evidence, an ArkApi\n"
             "compatibility target, or an ABI reference"),
            (texts["docs/research/2026-05-30-v1-core-capability-map.md"], "ArkServerApi/AseApi is a demand dictionary only"),
            (texts["docs/research/2026-05-30-v1-core-capability-map.md"], "this is not ArkApi source, ABI, behavior, or\n  plugin compatibility"),
            (texts["docs/research/2026-05-30-v1-core-capability-map.md"], "Obelisk-native Linux plugins for common ArkApi-style modding\nneeds"),
            (texts["docs/research/README.md"], "ArkApi/AseApi material remains a names/demand dictionary only"),
            (texts["plugins/README.md"], "names/demand signals only"),
            (texts["plugins/README.md"], "not a\n"
             "compatibility target, source reference, ABI reference, schema, command parser, or\n"
             "implementation pattern"),
            (texts["docs/research/2026-05-30-nextgenplugins-reference-inventory.md"], "Use this clone as a names/demand dictionary"),
            (texts["docs/research/2026-05-30-nextgenplugins-reference-inventory.md"], "not as source code to port"),
            (texts["docs/research/2026-05-30-nextgenplugins-reference-inventory.md"], "Do not trust `DECLARE_HOOK` declarations as Linux ABI"),
            (texts["docs/research/2026-05-30-nextgenplugins-reference-inventory.md"], "not runtime evidence and do not authorize copied implementation"),
            (texts["docs/research/2026-05-30-aseapi-reference-scan.md"], "only as a names and demand dictionary"),
            (texts["docs/research/2026-05-30-aseapi-reference-scan.md"], "not a behavior map,\ncompatibility target, implementation guide, or evidence source"),
            (texts["docs/research/2026-05-30-aseapi-reference-scan.md"], "Candidate name discovery only"),
            (texts["docs/research/2026-05-30-aseapi-reference-scan.md"], "Behavior parity, control flow, command parsers, schemas, constants, return semantics"),
            (texts["agent-skills/obelisk-github-research-workflow/SKILL.md"], "Local NextGenPlugins clones are names and demand\nsignals only"),
            (texts["agent-skills/obelisk-github-research-workflow/SKILL.md"], "Obelisk must not copy ArkServerApi/AseApi,\nNextGenPlugins"),
            (texts["docs/agent-handoff/CURRENT.md"], "ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand dictionaries\n  only"),
            (texts["docs/agent-handoff/CURRENT.md"], "Do not copy code, offsets, layouts, vtables, ABI assumptions"),
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

        forbidden_positive_claims = (
            r"\b(?:ArkApi|ArkServerApi|AseApi|ARK-Server-API|ASE-Plugins|NextGenPlugins)[- ]compatible\b",
            r"\b(?:drop[- ]in\s+compatible|API\s+parity)\b",
            r"\bport(?:s|ed|ing)?\s+(?:ArkApi|ArkServerApi|AseApi|ARK-Server-API|ASE-Plugins|NextGenPlugins)\b",
            r"\bcopy(?:ing|ied)?\s+(?:ArkApi|ArkServerApi|AseApi|ARK-Server-API|ASE-Plugins|NextGenPlugins)\s+(?:code|implementations?)\b",
            r"\b(?:reuse|mirror)\s+(?:ArkApi|ArkServerApi|AseApi|ARK-Server-API|ASE-Plugins|NextGenPlugins)\s+(?:implementation|ABI)\b",
            r"\b(?:Windows|MSVC)\s+ABI\s+(?:reference|target|support|surface)\b",
            r"\buse\s+`?DECLARE_HOOK`?\s+(?:as|for)\s+(?:Linux\s+)?ABI\b",
        )
        negated_context = re.compile(
            r"\b(?:do\s+not|does\s+not|must\s+not|not|no|never|without|forbids?|forbidden|"
            r"does\s+not\s+authorize)\b",
            re.IGNORECASE,
        )

        offenders: list[str] = []
        for name, text in texts.items():
            for line_no, line in enumerate(text.splitlines(), start=1):
                for pattern in forbidden_positive_claims:
                    if re.search(pattern, line, flags=re.IGNORECASE) and not negated_context.search(line):
                        offenders.append(f"{name}:{line_no}: {line.strip()}")

        self.assertEqual(offenders, [])

    def test_plugin_hub_foundation_v1_stays_minimal_and_non_authoritative(self) -> None:
        foundation = (REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md").read_text(encoding="utf-8")
        compact = normalized(foundation)

        required = (
            "post-RC contributor seed for the current ABI, not a change to the published `v0.1.0-rc.2` tag",
            "Post-RC production-supported seed work is limited to lifecycle/config/logging skeletons",
            "Copied `ChatMessageEvent` parsing and copied `GameplayPolicyEvent` auditing remain experimental seed patterns only",
            "not production Plugin Hub modules, command/chat SDKs, policy-enforcement SDKs, or evidence of a new ABI",
            "does not add public symbols, structs, callbacks, capabilities, or gameplay modules",
            "raw `ProcessEvent` callbacks only as debug-gated runtime plumbing, not as Plugin Hub API",
            "optional calls require the capability bit, sufficient `struct_size`, and a non-null function pointer",
            "Any callback or timer registration must use a non-null owner token",
            "Registration returns handle `0` on failure",
            "Individual unregister calls cancel future delivery but are not a quiescence barrier",
            "Event payloads are callback-scope",
            "must not be persisted or shared across maps, processes, or clusters",
            "copied `ChatMessageEvent` text parsers without sender identity, replies, moderation, or a command SDK",
            "Foundation V1 does not provide or imply",
            "`ResourceHandle`, object identity, resource identity, player identity",
            "public Inventory SDK, Items SDK, StructureEvents SDK, command SDK",
            "public storage SDK, database service",
            "gameplay mutation, inventory mutation",
            "return override authority",
            "persistent or cross-cluster handles",
        )

        for item in required:
            with self.subTest(item=item):
                self.assertIn(normalized(item), compact)

    def test_docs_index_keeps_plugin_author_creation_boundary_visible(self) -> None:
        docs_index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        compact = normalized(docs_index)

        required = (
            "what a plugin can honestly build today",
            "current production-supported seeds are lifecycle/config/logging, descriptor/catalog consumers, and process-local timers",
            "Copied chat parsers and `GameplayPolicyEvent` auditors are experimental pattern examples only",
            "not production command/chat/policy SDKs",
            "identity, lookup, mutation, replies/send-chat, permissions, storage, RCON, inventory/item APIs, or structure enforcement stays blocked until promoted",
        )
        for item in required:
            with self.subTest(item=item):
                self.assertIn(normalized(item), compact)

    def test_first_party_examples_stay_on_fastest_honest_creator_path(self) -> None:
        plugins_readme = (REPO_ROOT / "plugins" / "README.md").read_text(encoding="utf-8")
        foundation = (REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md").read_text(encoding="utf-8")
        matrix = (REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md").read_text(encoding="utf-8")
        obase_doc = (REPO_ROOT / "docs" / "oBaseEvents.md").read_text(encoding="utf-8")
        descriptor_doc = (REPO_ROOT / "docs" / "oDescriptorCatalog.md").read_text(encoding="utf-8")
        timer_doc = (REPO_ROOT / "docs" / "oProcessTimer.md").read_text(encoding="utf-8")
        policy_source = (REPO_ROOT / "plugins" / "oPolicyAudit" / "oPolicyAudit.cpp").read_text(
            encoding="utf-8"
        )

        for name in ("oBaseEvents", "oDescriptorCatalog", "oProcessTimer", "oPolicyAudit"):
            with self.subTest(name=name):
                self.assertIn(name, plugins_readme)

        for text, required in (
            (foundation, "## Fastest Honest Creator Path"),
            (foundation, "Add descriptor reads"),
            (foundation, "Add process-local timers"),
            (foundation, "Keep passive copied chat parsing experimental and plugin-local only"),
            (foundation, "Keep copied policy auditors experimental"),
            (foundation, "Only lifecycle/config/logging, descriptor/catalog, and process-local timer examples are\nproduction-supported seeds after the RC"),
            (foundation, "Copied chat parsers and copied policy auditors\nmay demonstrate patterns, but they remain experimental"),
            (matrix, "## Post-v0.1 Creator Ladder"),
            (matrix, "Production-supported seed lanes"),
            (matrix, "Experimental pattern examples only"),
            (matrix, "Descriptor consumers"),
            (matrix, "Passive chat text parsers"),
            (matrix, "Timer utilities"),
            (matrix, "Copied policy auditors"),
            (matrix, "## Post-RC Support Boundary"),
            (matrix, "Post-RC production-supported Plugin Hub seed work is limited to lifecycle/config/logging"),
            (matrix, "Copied `ChatMessageEvent` parsing and\ncopied `GameplayPolicyEvent` auditing may remain useful experimental seed examples"),
            (matrix, "Those three are seed examples only, not production Plugin Hub modules"),
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

        for text, required in (
            (obase_doc, "filtered raw `ProcessEvent` callback when the runtime explicitly advertises the filtered debug capability"),
            (obase_doc, "optional plugin-local chat command helper layered on copied `ChatMessageEvent`"),
            (descriptor_doc, "metadata-only SDK discovery"),
            (descriptor_doc, "does not register callbacks, timers, chat handlers"),
            (timer_doc, "process-local timers"),
            (timer_doc, "does not use or imply UE timers, gameplay timers, `ProcessEvent`"),
            (plugins_readme, "Production-supported seed examples are limited to lifecycle/config/logging, descriptor\nreaders, and process-local timer utilities"),
            (plugins_readme, "Those production-supported seeds still must\nkeep the shared safe default config posture"),
            (plugins_readme, "raw `ProcessEvent` callbacks\n  require explicit debug gates"),
            (plugins_readme, "`oPolicyAudit` demonstrates the promoted `GameplayPolicyEvent` callback family"),
            (plugins_readme, "storage/database services, webhooks, inventory/item mutation"),
            (plugins_readme, "until the matching public surface is promoted in the\npublic ABI, recorded in the capability matrix"),
        ):
            with self.subTest(required=required):
                self.assertIn(normalized(required), normalized(text))

        self.assertNotIn("Seed examples are production-ready only when", plugins_readme)

        for required in (
            "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
            "RegisterGameplayPolicyEventWithOwnerTokenHandle",
            "UnregisterGameplayPolicyEventWithOwnerToken",
            "DescribeResourceKind",
            "DescribeGameplayPolicyEventKind",
        ):
            with self.subTest(policy_required=required):
                self.assertIn(required, policy_source)

        for forbidden in (
            "CallProcessEvent",
            "RegisterPreProcessEvent",
            "RegisterPostProcessEvent",
            "ChatMessageEvent",
            "RegisterTimer",
        ):
            with self.subTest(policy_forbidden=forbidden):
                self.assertNotIn(forbidden, policy_source)

    def test_plugin_hub_direction_does_not_promise_category_graduation(self) -> None:
        matrix = (REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md").read_text(encoding="utf-8")
        compact_matrix = normalized(matrix)

        for required in (
            "passive copied chat auditing/parsing is a candidate for promotion review before copied policy auditing, not a promised graduation path",
            "The first useful Plugin Hub seed examples should be built from surfaces that already exist",
            "Those are the production-supported seed lanes",
            "Copied `GameplayPolicyEvent` auditors and\ncopied `ChatMessageEvent` parsers may still be useful experimental pattern examples",
            "must not claim policy enforcement, general chat,\ncommands, identity, replies, moderation, send-chat, or production Plugin Hub availability",
        ):
            with self.subTest(required=required):
                self.assertIn(normalized(required), compact_matrix)

        forbidden_patterns = (
            r"\bnext\s+(?:category|module|SDK)\s+to\s+graduate\b",
            r"\b(?:category|module|SDK)\s+to\s+graduate\s+is\b",
            r"\bfirst\s+useful\s+Plugin\s+Hub\s+categories\s+should\s+be\s+built\b",
        )
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, matrix, flags=re.IGNORECASE))

    def test_experimental_plugin_targets_and_tests_stay_flag_gated(self) -> None:
        root_cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        sdk_consumer_cmake = (REPO_ROOT / "tests" / "sdk_consumer" / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        experimental_plugins = {
            "oPolicyAudit": "plugins/oPolicyAudit",
            "oChatLogger": "plugins/oChatLogger",
            "oChatAudit": "plugins/oChatAudit",
        }

        self.assertRegex(
            root_cmake,
            r"option\s*\(\s*OBELISK_BUILD_EXPERIMENTAL_PLUGINS\b[^\)]*\bOFF\s*\)",
        )
        root_block_match = re.search(
            r"if\s*\(\s*OBELISK_BUILD_EXPERIMENTAL_PLUGINS\s*\)(?P<body>.*?)endif\s*\(\s*\)",
            root_cmake,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(root_block_match)
        if root_block_match is None:
            return

        root_block = root_block_match.group("body")
        root_without_experimental_block = (
            root_cmake[: root_block_match.start()] + root_cmake[root_block_match.end() :]
        )
        sdk_consumer_index = root_cmake.index("add_subdirectory(tests/sdk_consumer)")
        for target, path in experimental_plugins.items():
            add_subdirectory = f"add_subdirectory({path})"
            with self.subTest(target=target, cmake="root"):
                self.assertEqual(root_cmake.count(add_subdirectory), 1)
                self.assertIn(add_subdirectory, root_block)
                self.assertLess(root_cmake.index(add_subdirectory), sdk_consumer_index)
                self.assertNotIn(add_subdirectory, root_without_experimental_block)
                self.assertIsNone(
                    re.search(rf"install\s*\(\s*TARGETS[^\)]*\b{re.escape(target)}\b", root_cmake, re.DOTALL)
                )

        sdk_without_experimental_blocks = sdk_consumer_cmake
        for target in experimental_plugins:
            block_match = re.search(
                rf"if\s*\(\s*TARGET\s+{re.escape(target)}\s*\)(?P<body>.*?)endif\s*\(\s*\)",
                sdk_without_experimental_blocks,
                flags=re.DOTALL,
            )
            with self.subTest(target=target, cmake="sdk_consumer"):
                self.assertIsNotNone(block_match)
                if block_match is None:
                    continue
                self.assertIn(f"$<TARGET_FILE:{target}>", block_match.group("body"))
            sdk_without_experimental_blocks = (
                sdk_without_experimental_blocks[: block_match.start()]
                + sdk_without_experimental_blocks[block_match.end() :]
            )

        for target in experimental_plugins:
            with self.subTest(target=target, cmake="sdk_consumer_default"):
                self.assertNotIn(target, sdk_without_experimental_blocks)

    def test_sdk_install_layout_publishes_only_allowlisted_public_header(self) -> None:
        root_cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        installer = (REPO_ROOT / "scripts" / "install_obelisk.sh").read_text(encoding="utf-8")
        install_doc = (REPO_ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        public_headers = sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in (REPO_ROOT / "include").rglob("*")
            if path.is_file()
        )

        self.assertEqual(public_headers, ["include/obelisk/ObeliskApi.h"])
        self.assertNotRegex(root_cmake, r"install\s*\(\s*DIRECTORY\s+include/?\b")
        self.assertRegex(
            root_cmake,
            r"install\s*\(\s*FILES\s+include/obelisk/ObeliskApi\.h\s+"
            r"DESTINATION\s+\$\{CMAKE_INSTALL_INCLUDEDIR\}/obelisk\s+COMPONENT\s+SDK\s*\)",
        )
        self.assertIn('"include/obelisk/ObeliskApi.h"', installer)
        self.assertIn("include/obelisk/ObeliskApi.h", install_doc)
        self.assertIn('"lib/cmake/Obelisk/ObeliskConfig.cmake"', installer)
        self.assertIn('"lib/cmake/Obelisk/ObeliskConfigVersion.cmake"', installer)
        self.assertIn('"lib/cmake/Obelisk/ObeliskTargets.cmake"', installer)
        self.assertIn("lib/cmake/Obelisk/ObeliskConfig.cmake", install_doc)
        self.assertIn("lib/cmake/Obelisk/ObeliskConfigVersion.cmake", install_doc)
        self.assertIn("lib/cmake/Obelisk/ObeliskTargets.cmake", install_doc)
        for managed_subpath in (
            "include/obelisk",
            "lib/cmake",
            "lib/cmake/Obelisk",
        ):
            with self.subTest(managed_subpath=managed_subpath):
                self.assertIn(f'"{managed_subpath}"', installer)
                self.assertIn(f"`{managed_subpath}`", install_doc)
        self.assertNotIn("include/obelisk/*.h", install_doc)

    def test_nextgenplugins_absolute_path_stays_out_of_public_docs_and_skills(self) -> None:
        offenders: list[str] = []

        for root in (REPO_ROOT / "agent-skills",):
            for path in root.rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                if "/home/flowcommunity-ark/NextGenPlugins" in text:
                    offenders.append(str(path.relative_to(REPO_ROOT)))

        for path in PUBLIC_SDK_GUIDANCE_DOC_FILES:
            text = path.read_text(encoding="utf-8")
            if "/home/flowcommunity-ark/NextGenPlugins" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(offenders, [])

    def test_nextgenplugins_inventory_mentions_existing_public_matrix(self) -> None:
        inventory = (
            REPO_ROOT / "docs" / "research" / "2026-05-30-nextgenplugins-reference-inventory.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Use the existing\n`docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`", inventory)
        self.assertIn("research/provenance note records exact source commits", inventory)
        self.assertNotIn("use it later to build a\n`Plugin Hub capability matrix`", inventory)
        self.assertNotIn("Plugin Hub\nmatrix records exact source commits", inventory)
        self.assertNotIn("The matrix should stay in\n`docs/research/`", inventory)

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

    def test_chat_command_helper_roadmap_stays_plugin_local_and_unbranded(self) -> None:
        roadmap = CHAT_COMMAND_HELPER_ROADMAP.read_text(encoding="utf-8")
        compact = normalized(roadmap)
        offenders: list[str] = []

        for required in (
            "documentation-only design guidance",
            "not a request to change `include/obelisk/ObeliskApi.h`",
            "It should not be promoted as a runtime service",
            "No command registration in `ObeliskApi`",
            "No public command SDK claim for v0.1",
            "No sender/player identity or per-player permission checks",
            "No chat send, reply, moderation, block, mutation, or return override",
            "A real command module remains blocked",
            "Do not add a first-party `oCommand*` plugin, installed helper target, packaged helper, "
            "or command-branded public example until command identity and permissions are designed",
            "keep it uninstalled, non-command-branded, and guarded as local parsing only",
        ):
            with self.subTest(required=required):
                self.assertIn(normalized(required), compact)

        forbidden_positive_claims = (
            r"\bpublic\s+command\s+SDK\b",
            r"\bpromoted\s+(?:runtime\s+)?command\s+(?:service|module|API|SDK)\b",
            r"\bproduction\s+Plugin\s+Hub\s+command\s+module\b",
            r"\bfirst-party\s+`?oCommand\*?`?\s+plugin\s+(?:is|as|for)\s+(?:available|ready|promoted|installed)\b",
            r"\binstalled\s+command\s+helper\s+target\b",
        )
        negated_context = re.compile(
            r"\b(?:do\s+not|does\s+not|must\s+not|not|no|never|without|blocked|until)\b",
            re.IGNORECASE,
        )

        for line_no, line in enumerate(roadmap.splitlines(), start=1):
            for pattern in forbidden_positive_claims:
                if re.search(pattern, line, flags=re.IGNORECASE) and not negated_context.search(line):
                    relative = CHAT_COMMAND_HELPER_ROADMAP.relative_to(REPO_ROOT)
                    offenders.append(f"{relative}:{line_no}: {line.strip()}")

        self.assertEqual(offenders, [])

    def test_public_sdk_core_api_surface_matches_v010_allowlist(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")

        self.assertEqual(public_api_capability_defines(header), V010_CORE_API_CAPABILITY_ALLOWLIST)
        self.assertEqual(obelisk_api_field_names(header), V010_CORE_OBELISK_API_FIELD_ALLOWLIST)
        self.assertEqual(public_struct_typedefs(header), V010_PUBLIC_STRUCT_ALLOWLIST)
        self.assertEqual(public_enum_typedefs(header), V010_PUBLIC_ENUM_ALLOWLIST)
        self.assertEqual(public_enum_definitions(header), V010_PUBLIC_ENUM_VALUE_ALLOWLIST)
        self.assertEqual(public_callback_typedefs(header), V010_PUBLIC_CALLBACK_TYPEDEF_ALLOWLIST)
        self.assertEqual(public_struct_field_names(header, "ObeliskPluginMetadata"), V010_PLUGIN_METADATA_FIELDS)
        self.assertEqual(
            public_struct_field_names(header, "ObeliskPluginInitContext"),
            V010_PLUGIN_INIT_CONTEXT_FIELDS,
        )
        self.assertEqual(V010_PLUGIN_INIT_CONTEXT_FIELDS[-1], "plugin_owner_token")

    def test_gameplay_policy_event_payload_stays_minimal_copied_pod(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")

        self.assertEqual(
            public_struct_field_names(header, "ObeliskGameplayPolicyEvent"),
            V010_GAMEPLAY_POLICY_EVENT_PAYLOAD_FIELDS,
        )

        forbidden_payload_fields = (
            "inventory",
            "item",
            "structure",
            "player",
            "tribe",
            "identity",
            "id",
            "handle",
            "object",
            "uobject",
            "function",
            "fname",
            "gname",
            "gobject",
            "lookup",
            "resolve",
            "mutat",
            "override",
            "return_override",
            "pin",
            "secret",
        )
        for field in public_struct_field_names(header, "ObeliskGameplayPolicyEvent"):
            lowered = field.lower()
            with self.subTest(field=field):
                for forbidden in forbidden_payload_fields:
                    self.assertNotIn(forbidden, lowered)

    def test_chat_message_event_payload_stays_minimal_copied_notification(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")

        self.assertEqual(
            public_struct_field_names(header, "ObeliskChatMessageEvent"),
            V010_CHAT_MESSAGE_EVENT_PAYLOAD_FIELDS,
        )

        forbidden_payload_fields = (
            "sender",
            "player",
            "tribe",
            "identity",
            "id",
            "handle",
            "resource",
            "object",
            "uobject",
            "function",
            "fname",
            "gname",
            "gobject",
            "lookup",
            "resolve",
            "mutat",
            "override",
            "return_override",
            "route",
            "reply",
            "moderation",
            "command",
        )
        for field in public_struct_field_names(header, "ObeliskChatMessageEvent"):
            lowered = field.lower()
            with self.subTest(field=field):
                for forbidden in forbidden_payload_fields:
                    self.assertNotIn(forbidden, lowered)

    def test_copied_event_callback_contracts_remain_void_observational_and_callback_scope(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")
        comment_terms = (
            "Gameplay policy event data is callback-scope",
            "plugins may read the copied POD\n// payload during the callback only",
            "Chat message event data is callback-scope",
            "plugins may read the copied UTF-8\n// payload during the callback only",
            "provides no identity, lookup, mutation, return\n// override, or raw UE pointer access",
        )
        stripped_header = strip_c_comments(header)

        for term in comment_terms:
            self.assertIn(term, header)
        for callback_name, event_type in (
            ("ObeliskGameplayPolicyEventCallback", "ObeliskGameplayPolicyEvent"),
            ("ObeliskChatMessageEventCallback", "ObeliskChatMessageEvent"),
        ):
            with self.subTest(callback=callback_name):
                self.assertRegex(
                    stripped_header,
                    rf"typedef\s+void\s+\(\*\s*{callback_name}\s*\)"
                    rf"\s*\(\s*const\s+{event_type}\s*\*\s*event\s*,\s*void\s*\*\s*user_data\s*\)\s*;",
                )

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

    def test_installed_sdk_layout_keeps_release_scope_examples_on_installed_package(self) -> None:
        consumer_cmake = (REPO_ROOT / "tests/sdk_installed_consumer/CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        layout_script = (REPO_ROOT / "scripts/test_install_obelisk_layout.sh").read_text(encoding="utf-8")

        self.assertIn("find_package(Obelisk 0.1.0 CONFIG REQUIRED)", consumer_cmake)
        self.assertIn("target_link_libraries(${target_name} PRIVATE Obelisk::obelisk_sdk)", consumer_cmake)
        self.assertIn("-DOBELISK_RELEASE_SCOPE_PLUGIN_SOURCE_ROOT=\"${REPO_DIR}/plugins\"", layout_script)
        self.assertIn("-DOBELISK_RELEASE_SCOPE_EXTERN_ROOT=\"${REPO_DIR}/extern\"", layout_script)
        self.assertIn("if grep -F \"${REPO_DIR}/include\"", layout_script)

        for target_name, source_path, output_variable, output_path in (
            (
                "release_scope_oBaseEvents",
                "oBaseEvents/oBaseEvents.cpp",
                "RELEASE_BASE_EVENTS_PLUGIN_PATH",
                "oBaseEvents.so",
            ),
            (
                "release_scope_oProcessTimer",
                "oProcessTimer/oProcessTimer.cpp",
                "RELEASE_TIMER_PLUGIN_PATH",
                "oProcessTimer.so",
            ),
            (
                "release_scope_oDescriptorCatalog",
                "oDescriptorCatalog/oDescriptorCatalog.cpp",
                "RELEASE_DESCRIPTOR_PLUGIN_PATH",
                "oDescriptorCatalog.so",
            ),
        ):
            with self.subTest(target=target_name):
                self.assertIn(target_name, consumer_cmake)
                self.assertIn(source_path, consumer_cmake)
                self.assertIn(output_variable, layout_script)
                self.assertIn(output_path, layout_script)

    def test_sdk_minimal_plugin_example_stays_installed_sdk_only(self) -> None:
        examples_readme = (REPO_ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        minimal_readme = (REPO_ROOT / "examples" / "sdk_minimal_plugin" / "README.md").read_text(
            encoding="utf-8"
        )
        minimal_cmake = (REPO_ROOT / "examples" / "sdk_minimal_plugin" / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        minimal_source = (REPO_ROOT / "examples" / "sdk_minimal_plugin" / "minimal_plugin.c").read_text(
            encoding="utf-8"
        )

        for path in SDK_MINIMAL_PLUGIN_EXAMPLE_FILES:
            with self.subTest(path=path.relative_to(REPO_ROOT), token="example file"):
                self.assertTrue(path.exists())

        for text, relative in (
            (examples_readme, "examples/README.md"),
            (minimal_readme, "examples/sdk_minimal_plugin/README.md"),
            (minimal_cmake, "examples/sdk_minimal_plugin/CMakeLists.txt"),
        ):
            normalized_text = re.sub(r"\s+", " ", text)
            with self.subTest(path=relative, token="find_package"):
                self.assertIn("find_package(Obelisk 0.1.0 CONFIG REQUIRED)", normalized_text)
            with self.subTest(path=relative, token="sdk target"):
                self.assertIn("Obelisk::obelisk_sdk", text)

        for text, relative in (
            (examples_readme, "examples/README.md"),
            (minimal_readme, "examples/sdk_minimal_plugin/README.md"),
        ):
            for token in (
                "private",
                "UE pointers",
                "new gameplay APIs",
                "chat replies/send-chat",
            ):
                with self.subTest(path=relative, token=token):
                    self.assertIn(token, text)

        self.assertIn("#include <obelisk/ObeliskApi.h>", minimal_source)
        for token in (
            '#include "',
            "#include <core/",
            "#include <hooks/",
            "#include <plugins/",
            "UObject",
            "UFunction",
            "FString",
            "ProcessEvent",
            "CallProcessEvent",
            "RegisterGameplay",
            "RegisterChat",
            "ChatMessageEvent",
            "SendChat",
            "Reply",
            "ArkApi",
        ):
            with self.subTest(path="examples/sdk_minimal_plugin/minimal_plugin.c", forbidden=token):
                self.assertNotIn(token, minimal_source)

    def test_obaseevents_chat_helper_cleanup_guardrail_stays_in_release_tests(self) -> None:
        cmake = (REPO_ROOT / "tests/sdk_consumer/CMakeLists.txt").read_text(encoding="utf-8")
        fixture = (REPO_ROOT / "tests/sdk_consumer/SdkConsumerFixture.cpp").read_text(encoding="utf-8")
        obase = (REPO_ROOT / "plugins/oBaseEvents/oBaseEvents.cpp").read_text(encoding="utf-8")

        for token in (
            "SdkConsumerFixtureOBaseEventsChatCommandHelper",
            "SdkConsumerFixtureOBaseEventsChatCommandHelperNoCapability",
            "SdkConsumerFixtureOBaseEventsChatPostRegistrationFailureCleanup",
            "SdkConsumerFixtureOBaseEventsRejectsInvalidChatCommandConfig",
        ):
            with self.subTest(file="tests/sdk_consumer/CMakeLists.txt", token=token):
                self.assertIn(token, cmake)

        for token in (
            "throw-log-after-chat-message-registration",
            "plugin did not unregister chat message callback after injected log failure",
            "chat command helper callback survived shutdown unregister",
            "chat command helper user data survived shutdown unregister",
            "chat command helper registered without chat capability",
        ):
            with self.subTest(file="tests/sdk_consumer/SdkConsumerFixture.cpp", token=token):
                self.assertIn(token, fixture)

        for token in (
            "UnregisterChatCommand();",
            "UnregisterProcessEvent();",
            "ResetState();",
            "RegisterChatMessageEventWithOwnerTokenHandle",
            "UnregisterChatMessageEventWithOwnerToken",
        ):
            with self.subTest(file="plugins/oBaseEvents/oBaseEvents.cpp", token=token):
                self.assertIn(token, obase)

    def test_public_sdk_consumers_guard_append_only_api_slots(self) -> None:
        metadata_guard = "api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities)"

        for path in PUBLIC_SDK_OPTIONAL_API_CONSUMERS:
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(REPO_ROOT).as_posix()

            self.assertIn("api->abi_version != OBELISK_API_ABI_VERSION", text)
            self.assertIn(metadata_guard, text)

            if "memcpy(&g_Api" in text or "std::memcpy(&g_Api" in text:
                self.assertIn("api->struct_size < sizeof(g_Api) ? api->struct_size : sizeof(g_Api)", text)

            for surface in PUBLIC_SDK_OPTIONAL_API_SURFACES:
                trigger = surface["trigger"]
                if trigger not in text:
                    continue

                with self.subTest(file=relative, surface=surface["name"]):
                    for capability in surface["capabilities"]:
                        self.assertIn(capability, text)

                    terminal_slot = surface["terminal_slot"]
                    terminal_slot_alias = surface.get("terminal_slot_alias", terminal_slot)
                    terminal_offset_tokens = {
                        f"offsetof(ObeliskApi, {terminal_slot})",
                        f"offsetof(ObeliskApi, {terminal_slot_alias})",
                    }
                    terminal_size_tokens = {
                        f"sizeof(api->{terminal_slot})",
                        f"sizeof(api->{terminal_slot_alias})",
                    }
                    self.assertTrue(
                        any(token in text for token in terminal_offset_tokens),
                        f"{relative} must struct_size-gate {surface['name']} with offsetof",
                    )
                    self.assertTrue(
                        any(token in text for token in terminal_size_tokens),
                        f"{relative} must include terminal slot size for {surface['name']}",
                    )

                    for slot in surface["required_slots"]:
                        slot_alias = "OBELISK_CONCAT(Unregister, TimerWithOwnerToken)" \
                            if slot == "UnregisterTimerWithOwnerToken" else slot
                        self.assertTrue(
                            f"api->{slot}" in text or f"api->{slot_alias}" in text,
                            f"{relative} must null-check/use {slot} for {surface['name']}",
                        )

    def test_public_sdk_consumers_keep_owner_token_registrations_owner_scoped(self) -> None:
        owner_token_surfaces = [
            surface for surface in PUBLIC_SDK_OPTIONAL_API_SURFACES
            if "WithOwnerToken" in surface["trigger"] or surface["name"] == "timers"
        ]

        for path in PUBLIC_SDK_OPTIONAL_API_CONSUMERS:
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(REPO_ROOT).as_posix()
            owner_token_triggers = [
                surface["trigger"] for surface in owner_token_surfaces
                if surface["trigger"] in text
            ]
            if not owner_token_triggers:
                continue

            with self.subTest(file=relative, check="context-token-required"):
                self.assertRegex(
                    text,
                    r"context->plugin_owner_token\s*(?:!=|==)\s*0",
                    f"{relative} must validate a nonzero plugin_owner_token before registration",
                )

            with self.subTest(file=relative, check="captured-owner-token"):
                self.assertIn(
                    "g_OwnerToken = context->plugin_owner_token",
                    text,
                    f"{relative} must capture the init owner token for matching unregister",
                )

            forbidden_zero_owner_calls = re.findall(
                r"(?:Register|Unregister)[A-Za-z0-9_]*WithOwnerToken[A-Za-z0-9_]*\s*\(\s*0\s*,",
                text,
            )
            with self.subTest(file=relative, check="no-zero-owner-calls"):
                self.assertEqual(forbidden_zero_owner_calls, [])

            for surface in owner_token_surfaces:
                trigger = surface["trigger"]
                if trigger not in text:
                    continue
                unregister_slot = surface["terminal_slot"]
                unregister_alias = surface.get("terminal_slot_alias", unregister_slot)
                trigger_alias = "OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle)" \
                    if trigger == "RegisterTimerWithOwnerTokenHandle" else trigger

                with self.subTest(file=relative, surface=surface["name"], call="register-owner"):
                    self.assertRegex(
                        text,
                        rf"{re.escape(trigger_alias)}\s*\(\s*g_OwnerToken\s*,",
                        f"{relative} must register {surface['name']} with the captured owner token",
                    )

                with self.subTest(file=relative, surface=surface["name"], call="unregister-owner"):
                    self.assertRegex(
                        text,
                        rf"{re.escape(unregister_alias)}\s*\(\s*g_OwnerToken\s*,",
                        f"{relative} must unregister {surface['name']} with the same captured owner token",
                    )

    def test_public_sdk_optional_api_consumers_export_shutdown(self) -> None:
        for path in PUBLIC_SDK_OPTIONAL_API_CONSUMERS:
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(REPO_ROOT).as_posix()
            self.assertIn(
                "ObeliskPlugin_Shutdown",
                text,
                f"{relative} consumes optional SDK state and must expose idempotent shutdown cleanup",
            )

    def test_first_party_cpp_example_shutdown_exports_catch_exceptions(self) -> None:
        for path in FIRST_PARTY_CPP_EXAMPLE_PLUGINS:
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(REPO_ROOT).as_posix()
            shutdown_body = exported_shutdown_body(text)
            with self.subTest(file=relative):
                self.assertIn("try", shutdown_body)
                self.assertIn("catch (...)", shutdown_body)

    def test_public_sdk_consumers_treat_v1_descriptors_as_fixed_size(self) -> None:
        forbidden_checks = (
            "descriptor.struct_size >= sizeof(ObeliskResourceKindDescriptor)",
            "descriptor.struct_size >= sizeof(ObeliskGameplayPolicyEventDescriptor)",
        )
        required_checks = (
            "descriptor.struct_size == sizeof(ObeliskResourceKindDescriptor)",
            "descriptor.struct_size == sizeof(ObeliskGameplayPolicyEventDescriptor)",
        )

        for path in PUBLIC_SDK_OPTIONAL_API_CONSUMERS:
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(REPO_ROOT).as_posix()
            if "DescribeResourceKind" not in text and "DescribeGameplayPolicyEventKind" not in text:
                continue

            for token in forbidden_checks:
                with self.subTest(file=relative, forbidden=token):
                    self.assertNotIn(token, text)
            for token in required_checks:
                with self.subTest(file=relative, required=token):
                    self.assertIn(token, text)

    def test_public_abi_layout_freeze_tests_cover_repo_and_installed_consumers(self) -> None:
        root_cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        c_layout = (REPO_ROOT / "tests" / "abi" / "CAbiLayoutTests.c").read_text(encoding="utf-8")
        cpp_layout = (REPO_ROOT / "tests" / "abi" / "AbiLayoutTests.cpp").read_text(encoding="utf-8")
        installed_c_consumer = (
            REPO_ROOT / "tests" / "sdk_installed_consumer" / "c_abi_plugin.c"
        ).read_text(encoding="utf-8")

        for test_name in ("AbiLayoutTests", "CAbiLayoutTests"):
            with self.subTest(cmake_test=test_name):
                self.assertIn(f"add_test(NAME {test_name}", root_cmake)

        required_layout_tokens = (
            "ASSERT_SIZE(ObeliskApi, 216)",
            "ASSERT_OFFSET(ObeliskApi, RegisterTimerWithOwnerTokenHandle, 200)",
            "ASSERT_OFFSET(ObeliskApi, UnregisterTimerWithOwnerToken, 208)",
            "ASSERT_SIZE(ObeliskPluginMetadata, 48)",
            "ASSERT_SIZE(ObeliskPluginInitContext, 40)",
            "ASSERT_SIZE(ObeliskGameplayPolicyEvent, 64)",
            "ASSERT_SIZE(ObeliskChatMessageEvent, 48)",
            "ASSERT_SIZE(ObeliskResourceKindDescriptor, 136)",
            "ASSERT_SIZE(ObeliskGameplayPolicyEventDescriptor, 152)",
        )
        for token in required_layout_tokens:
            with self.subTest(file="tests/abi/CAbiLayoutTests.c", token=token):
                self.assertIn(token, c_layout)
            installed_token = token
            if token == "ASSERT_OFFSET(ObeliskApi, RegisterTimerWithOwnerTokenHandle, 200)":
                installed_token = "ASSERT_OFFSET(ObeliskApi, OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle), 200)"
            elif token == "ASSERT_OFFSET(ObeliskApi, UnregisterTimerWithOwnerToken, 208)":
                installed_token = "ASSERT_OFFSET(ObeliskApi, OBELISK_CONCAT(Unregister, TimerWithOwnerToken), 208)"
            with self.subTest(file="tests/sdk_installed_consumer/c_abi_plugin.c", token=installed_token):
                self.assertIn(installed_token, installed_c_consumer)

        for token in (
            "static_assert(sizeof(ObeliskApi) == 216)",
            "static_assert(offsetof(ObeliskApi, RegisterTimerWithOwnerTokenHandle) == 200)",
            "static_assert(offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) == 208)",
            "AssertAbiType<ObeliskGameplayPolicyEvent>()",
            "AssertAbiType<ObeliskChatMessageEvent>()",
        ):
            with self.subTest(file="tests/abi/AbiLayoutTests.cpp", token=token):
                self.assertIn(token, cpp_layout)

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

    def test_versioning_policy_distinguishes_cmake_variables_from_c_header_macros(self) -> None:
        versioning = (REPO_ROOT / "docs" / "VERSIONING.md").read_text(encoding="utf-8")
        installed_consumer_cmake = (
            REPO_ROOT / "tests" / "sdk_installed_consumer" / "CMakeLists.txt"
        ).read_text(encoding="utf-8")
        root_cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        package_config = (REPO_ROOT / "cmake" / "ObeliskConfig.cmake.in").read_text(encoding="utf-8")
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")

        self.assertIn("installed CMake package variables", versioning)
        self.assertIn("not C preprocessor macros", versioning)
        self.assertIn("mirror the `OBELISK_*` header macros", versioning)
        self.assertIn("derived from the public header", normalized(versioning))

        header_abi_macros = public_abi_version_macros(header)
        expected_package_sets = [
            (macro.replace("OBELISK_", "Obelisk_", 1), macro)
            for macro, _version in header_abi_macros
        ]
        expected_cmake_variables = [cmake_variable for cmake_variable, _macro in expected_package_sets]
        expected_c_macros = [macro for _cmake_variable, macro in expected_package_sets]

        self.assertGreater(len(header_abi_macros), 0)
        self.assertEqual(cmake_abi_version_sets(root_cmake), [])
        self.assertEqual(cmake_abi_version_derivations(root_cmake), expected_c_macros)
        self.assertEqual(package_config_abi_version_sets(package_config), expected_package_sets)
        self.assertEqual(
            re.findall(r"`(Obelisk_[A-Z0-9_]*ABI_VERSION)`", versioning),
            expected_cmake_variables,
        )
        self.assertEqual(
            re.findall(r"`(OBELISK_[A-Z0-9_]*ABI_VERSION)`", versioning),
            expected_c_macros,
        )

        for c_macro, version in header_abi_macros:
            cmake_variable = c_macro.replace("OBELISK_", "Obelisk_", 1)
            with self.subTest(cmake_variable=cmake_variable, c_macro=c_macro):
                self.assertIn(cmake_variable, versioning)
                self.assertIn(c_macro, root_cmake)
                self.assertIn(cmake_variable, package_config)
                self.assertIn(cmake_variable, installed_consumer_cmake)
                self.assertIn(c_macro, versioning)
                self.assertRegex(header, re.compile(rf"^#define\s+{re.escape(c_macro)}\s+{version}u$", re.M))

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

    def test_describe_resource_kind_runtime_impl_stays_category_only_no_identity_no_lookup(self) -> None:
        source = strip_c_comments((REPO_ROOT / "core" / "PluginManager.cpp").read_text(encoding="utf-8"))
        match = re.search(
            r"bool\s+DescribeResourceKind\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*bool\s+DescribeGameplayPolicyEventKind",
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "DescribeResourceKind implementation not found")
        body = match.group("body")

        for flag in (
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
        ):
            self.assertIn(flag, body)
        for forbidden in (
            "ObeliskResourceHandle",
            "GetResource",
            "ResolveResource",
            "GObjects",
            "GUObjectArray",
        ):
            self.assertNotIn(forbidden, body)

    def test_no_real_resourcehandle_lookup_symbols_outside_guardrails_or_docs(self) -> None:
        scanned_roots = [
            REPO_ROOT / "include",
            REPO_ROOT / "core",
            REPO_ROOT / "ue",
            REPO_ROOT / "hooks",
        ]
        forbidden = (
            "ObeliskResourceHandle",
            "GetResource",
            "ResolveResource",
            "RegisterResourceHandle",
            "ResolveUObjectHandle",
        )
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".c", ".cpp", ".h", ".hpp"}:
                    continue
                text = strip_c_comments(path.read_text(encoding="utf-8"))
                literals = "\n".join(c_like_string_literals(text))
                text_without_literals = re.sub(r'"(?:\\.|[^"\\])*"', '""', text, flags=re.DOTALL)
                for token in forbidden:
                    if token in text_without_literals:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
                    if token in literals and path.relative_to(REPO_ROOT).as_posix() != "include/obelisk/ObeliskApi.h":
                        offenders.append(f"{path.relative_to(REPO_ROOT)} string: {token}")

        self.assertEqual(offenders, [])

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
                self.assertEqual(
                    len(event_kinds),
                    len(V010_PUBLIC_GAMEPLAY_POLICY_EVENT_TOKENS),
                    f"{event.get('event_id')} event kind count drifted",
                )
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
                self.assertIn("not promoted", event.get("item_module_sdk", ""))
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
                    self.assertEqual(event.get("item_return_backing_target_set"), "item-return-only-policy-slice")
                    self.assertIn(
                        "docs/research/2026-05-30-item-return-only-policy-slice.md",
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
                    if target_set == "item-return-only-policy-slice":
                        scope = item["scope"]
                        for required_scope_term in (
                            "ReturnValue-only",
                            "AllowEquipItem",
                            "CanRepair",
                            "UseItemOntoItem",
                            "no standalone item or inventory module surface",
                            "no identity",
                            "no lookup",
                            "no mutation",
                            "no return override",
                            "ResourceHandle",
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
                    self.assertIn("not promoted", event.get("item_module_sdk", ""))

    def test_public_gameplay_policy_manifest_redacts_structure_and_inventory_backing_identity_and_authority(self) -> None:
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
        self.assertIn("not promoted", gameplay_policy.get("item_module_sdk", ""))

        redacted_fields = gameplay_policy.get("redacted_fields")
        self.assertIsInstance(redacted_fields, list)
        for redacted in (
            "UObject pointers",
            "UFunction pointers",
            "FName/GObjects indices",
            "raw parameter buffers",
            "player identity",
            "structure object identity",
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
        self.assertIn("structure", minimal_scope)
        self.assertIn("inventory", minimal_scope)

        structure_intake = next(
            (
                evidence for evidence in target_set_evidence
                if isinstance(evidence, dict) and evidence.get("target_set") == "structure-observer-intake"
            ),
            None,
        )
        self.assertIsNotNone(structure_intake)
        structure_scope = structure_intake.get("scope", "")
        for required_scope_term in (
            "copied-redacted",
            "no identity",
            "no lookup",
            "no mutation",
            "no return override",
            "ResourceHandle",
        ):
            self.assertIn(required_scope_term, structure_scope)

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

        for path in PUBLIC_SDK_GUIDANCE_DOC_FILES:
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
            *PUBLIC_SDK_GUIDANCE_DOC_FILES,
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
            "OBELISK_API_CAPABILITY_STRUCTURE_BUILD_POLICY",
            "ObeliskStructureEvent",
            "ObeliskStructureBuildPolicy",
            "ObeliskBuildPolicy",
            "ObeliskStructureEventSubscription",
            "ObeliskStructureBuildPolicySubscription",
            "ObeliskOnStructureEventCallback",
            "ObeliskOnStructureBuildPolicyCallback",
            "RegisterOnStructureEvent",
            "RegisterOnStructureEvents",
            "RegisterOnStructureBuildPolicy",
            "RegisterStructureBuildPolicy",
            "OnStructureEvent",
            "OnStructureEvents",
            "OnStructureBuildPolicy",
            "UnregisterStructureEvent",
            "UnregisterStructureEvents",
            "UnregisterStructureBuildPolicy",
            "StructureEventView",
            "StructureBuildPolicyView",
            "StructureScalarValue",
            "StructureEventCallback",
            "StructureBuildPolicyCallback",
            "StructureEventSubscription",
            "StructureBuildPolicySubscription",
            "StructureEventDispatcher",
            "StructureBuildPolicyDispatcher",
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
                relative = path.relative_to(REPO_ROOT).as_posix()
                if relative.startswith("plugins/oProcessTimer/") and token in CORE_TIMER_EXAMPLE_TOKENS:
                    continue
                if relative.startswith("plugins/oChatAudit/") and token in CORE_TIMER_PUBLIC_TOKENS:
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
                relative = path.relative_to(REPO_ROOT).as_posix()
                if relative.startswith("plugins/oProcessTimer/") and token in CORE_TIMER_EXAMPLE_TOKENS:
                    continue
                if relative.startswith("plugins/oChatAudit/") and token in CORE_TIMER_PUBLIC_TOKENS:
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

    def test_mission_copied_bool_dispatcher_is_not_public_sdk_or_descriptor_surface(self) -> None:
        forbidden_tokens = [
            "MissionCopiedBoolEventDispatcher",
            "MissionCopiedBoolEventDispatcherTests",
            "ObeliskMissionCopiedBool",
            "OBELISK_API_CAPABILITY_MISSION_COPIED_BOOL",
            "RegisterMissionCopiedBool",
            "UnregisterMissionCopiedBool",
            "obelisk.mission_copied_bool",
            "obelisk.mission-copied-bool",
            "mission_copied_bool",
            "MissionCopiedBool",
            "mission-copied-bool-events",
        ]
        scanned_paths = [
            PUBLIC_API_HEADER,
            PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
            *PUBLIC_SDK_GUIDANCE_DOC_FILES,
        ]
        scanned_roots = [
            REPO_ROOT / "plugins",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
        ]

        offenders: list[str] = []
        for path in scanned_paths:
            text = path.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
        for root in scanned_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".c", ".cpp", ".h", ".hpp", ".md", ".json"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for token in forbidden_tokens:
                    if token in text:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_transfer_baccept_dispatcher_is_not_public_sdk_or_descriptor_surface(self) -> None:
        forbidden_tokens = [
            "TransferBAcceptEventDispatcher",
            "TransferBAcceptEventDispatcherTests",
            "TransferCopiedBoolEventDispatcher",
            "TransferCopiedBoolEventDispatcherTests",
            "ObeliskTransferBAccept",
            "OBELISK_API_CAPABILITY_TRANSFER_BACCEPT",
            "RegisterTransferBAccept",
            "UnregisterTransferBAccept",
            "obelisk.transfer_baccept",
            "obelisk.transfer-baccept",
            "transfer_baccept",
            "TransferBAccept",
            "transfer-baccept-events",
        ]
        scanned_paths = [
            PUBLIC_API_HEADER,
            PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
            *PUBLIC_SDK_GUIDANCE_DOC_FILES,
        ]
        scanned_roots = [
            REPO_ROOT / "plugins",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
        ]

        offenders: list[str] = []
        for path in scanned_paths:
            text = path.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
        for root in scanned_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".c", ".cpp", ".h", ".hpp", ".md", ".json"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for token in forbidden_tokens:
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
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?Items?\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?Missions?\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?Dinos?\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?Buffs?\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?Transfers?\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?Structures?\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?StructureEvents?\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?(?:structure\s+)?build[- ]policy\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?ResourceHandle\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:public\s+)?(?:gameplay\s+)?mutation\s+(?:SDKs?|APIs?|surfaces?|authority)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:public\s+)?return[- ]overrides?\s+(?:SDKs?|APIs?|surfaces?|authority)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:public\s+)?richer\s+chat\s+(?:SDKs?|APIs?|surfaces?|events?)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:public\s+)?commands?\s+(?:SDKs?|APIs?|surfaces?)\b",
            r"\bInventory\s+SDKs?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bItems?\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bMissions?\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bDinos?\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bBuffs?\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bTransfers?\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bStructures?\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\bStructureEvents?\s+(?:SDKs?|APIs?|surfaces?)?\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
            r"\b(?:structure\s+)?build[- ]policy\s+(?:SDKs?|APIs?|surfaces?)\s+(?:is|are)\s+(?:public|promoted|supported|available|included)\b",
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
                relative = path.relative_to(REPO_ROOT).as_posix()
                if relative.startswith("plugins/oProcessTimer/") and token in CORE_TIMER_EXAMPLE_TOKENS:
                    continue
                if relative.startswith("plugins/oChatAudit/") and token in CORE_TIMER_PUBLIC_TOKENS:
                    continue
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
            for pattern in forbidden_positive_claims:
                for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                    context = text[max(0, match.start() - 80):match.start()]
                    if not negated_claim_context.search(context):
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {pattern}")

        self.assertEqual(offenders, [])

    def test_nextgen_demand_inventory_stays_non_roadmap_and_non_compatibility(self) -> None:
        offenders: list[str] = []
        forbidden_phrases = (
            "Recommended v1 ordering",
            "NextGenPlugins compatibility",
        )
        research_only_forbidden_phrases = (
            "## Prioritized Demand Map",
            "Status labels:",
            "| Priority | Demand category | Seen in local dictionary | Obelisk capability needed | Status |",
            "`available`: a narrow Obelisk-native variant can be built from current public surfaces.",
        )
        required_research_phrases = (
            "Non-roadmap candidate pressure order",
            "This list is not a v1 delivery sequence, compatibility plan, or Plugin Hub roadmap.",
            "without claiming a command, moderation, or reply/send-chat SDK",
            "`oChatLogger`, `oChatAudit`, and `oPolicyAudit` may teach\n  copied chat/policy audit patterns, but they are not production Plugin Hub modules",
            "remain investigation/internal unless",
            "The capability matrix is the single public-facing status table",
        )

        for path in NEXTGEN_DEMAND_BOUNDARY_FILES:
            text = path.read_text(encoding="utf-8")
            for phrase in forbidden_phrases:
                if phrase in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {phrase}")

        research_note = (
            REPO_ROOT / "docs" / "research" / "2026-05-30-nextgenplugins-reference-inventory.md"
        ).read_text(encoding="utf-8")
        for phrase in research_only_forbidden_phrases:
            if phrase in research_note:
                offenders.append(
                    "docs/research/2026-05-30-nextgenplugins-reference-inventory.md: "
                    f"research note must not duplicate matrix status table phrase {phrase}"
                )
        for phrase in required_research_phrases:
            if phrase not in research_note:
                offenders.append(
                    "docs/research/2026-05-30-nextgenplugins-reference-inventory.md: "
                    f"missing {phrase}"
                )

        self.assertEqual(offenders, [])

    def test_plugin_hub_matrix_keeps_general_demand_spectrum_visible(self) -> None:
        matrix = (REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md").read_text(
            encoding="utf-8"
        )
        compact = normalized(matrix)
        compact_lower = compact.lower()

        for required in (
            "Permissions/admin groups",
            "RCON/operator I/O",
            "Economy, shops, kits, rewards",
            "Homes, teleport, safe zones",
            "Structure counts, placement, ownership",
            "Dino colors, carry rules",
            "Tribe MOTD, tribe-facing notices",
            "Engrams, inventory, item give/remove flows",
            "Shared persistence, database-backed state, webhook services",
            "Commands, permissions, economy, kits, shops, RCON",
            "Persistent storage, databases, webhooks",
            "Players, tribes, dinos, missions, transfers",
        ):
            with self.subTest(required=required):
                self.assertIn(required, compact)

        for required in (
            "structures",
            "dinos",
            "tribes",
            "inventory",
            "items",
            "permissions",
            "commands",
            "RCON",
            "economy",
            "homes",
        ):
            with self.subTest(surface=required):
                self.assertIn(required.lower(), compact_lower)

        self.assertIn(
            "Current attention on passive chat, `ResourceHandle` blockers, or structure build-placement "
            "triage must not turn those lanes into the Plugin Hub center",
            compact,
        )

    def test_plugin_hub_support_tiers_match_nextgen_demand_snapshot(self) -> None:
        matrix = (REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md").read_text(
            encoding="utf-8"
        )
        compact = normalized(matrix)
        rows: dict[str, str] = {}
        in_snapshot_table = False
        for line in matrix.splitlines():
            if line.startswith("| Priority | Category | Post-RC support tier | Safe interpretation |"):
                in_snapshot_table = True
                continue
            if in_snapshot_table and not line.startswith("|"):
                break
            if not in_snapshot_table:
                continue
            columns = [column.strip() for column in line.strip().strip("|").split("|")]
            if len(columns) != 4 or columns[0] == "---":
                continue
            rows[columns[1]] = columns[2]

        expected_tiers = {
            "Lifecycle, descriptors, logging, config, local timers": "production seed available",
            "Passive chat parsing and plugin-local text routing": "experimental seed only",
            "Copied structure/item policy auditing": "experimental seed only",
            "Timed notices and chat broadcasts": "blocked",
            "Permissions/admin groups": "blocked",
            "RCON/operator I/O and Unicode text": "blocked",
            "Economy, shops, kits, rewards, stats": "blocked",
            "Homes, teleport, safe zones, area policy": "blocked",
            "Structure counts, placement, ownership, collision policy": (
                "blocked except experimental auditing"
            ),
            "Dino colors, carry rules, spawn/cosmetic policy": "blocked",
            "Tribe MOTD, tribe-facing notices, and tribe policy": "blocked",
            "Engrams, inventory, item give/remove flows": "blocked",
            "Shared persistence, database-backed state, webhook services": "blocked",
        }

        self.assertEqual(rows, expected_tiers)
        for required in (
            "## Support Tier Legend",
            "`production seed available`: supported for narrow Obelisk-native examples",
            "`experimental seed only`: allowed for explicitly labeled pattern examples",
            "not supported as production Plugin Hub modules or as general chat, command, policy, structure, inventory, identity, mutation, or enforcement SDKs",
            "`blocked` and `blocked except experimental auditing`: backlog demand only",
            "## Dictionary-To-Primitive Rule",
            "does not map a popular plugin family to a rebuildable Plugin Hub module",
            "Names from ArkApi/AseApi or local `NextGenPlugins` can corroborate demand",
            "they do not widen a row's support tier",
            "It does not promote plugin watchdogs, hot reload, process restart, server recovery, or operator reload commands",
            "Timed notices map to process-local timers only when no chat send, broadcast, command, permission, persistence, or cross-process scheduling behavior is implied",
            "it does not promise ArkApi plugin compatibility",
            "Neither tier means the corresponding ArkApi plugin family can be ported",
            "not as portable behavior, source, ABI, constants, schemas, command parsers, or implementation patterns",
            "Promoted copied-data ABI surface; experimental Plugin Hub seed",
            "it does not turn copied chat/policy examples into production Plugin Hub modules",
        ):
            with self.subTest(required=required):
                self.assertIn(required, compact)

    def test_plugin_hub_v1_contributor_intake_boundary_is_consistent(self) -> None:
        docs = {
            "foundation": REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
            "matrix": REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
            "roadmap": REPO_ROOT / "docs" / "research" / "2026-05-29-module-surface-roadmap.md",
            "research_readme": REPO_ROOT / "docs" / "research" / "README.md",
        }
        texts = {name: path.read_text(encoding="utf-8") for name, path in docs.items()}
        compacts = {name: normalized(text) for name, text in texts.items()}

        required = {
            "foundation": (
                "## Contributor Intake Checklist",
                "Production seed now",
                "Experimental pattern only",
                "Blocked backlog",
                "ArkApi/AseApi/NextGenPlugins demand can justify keeping a blocked idea visible",
                "but it cannot reclassify that idea as a production seed or experimental pattern",
            ),
            "matrix": (
                "## Foundation-To-Roadmap Alignment",
                "`hub foundation` means production seed work",
                "`gameplay policy backing` means preserving evidence and tests for already promoted",
                "`internal recognizer planning` means docs, fixtures, and offline copied-bool planning",
                "only a named promotion gate can move a row's support tier",
            ),
            "roadmap": (
                "Roadmap-to-Plugin-Hub alignment for contributors",
                "`hub foundation` is the only production seed lane now",
                "`gameplay policy backing` protects the existing copied/redacted `GameplayPolicyEvent`",
                "`internal recognizer planning` stays offline/test-only",
                "append-only ABI/consumer-test plan",
            ),
            "research_readme": (
                "Plugin Hub contributor intake uses the same three buckets as the public matrix",
                "production seed now for lifecycle/config/logging, descriptor/catalog, timer, packaging",
                "experimental pattern only for passive copied chat or copied policy examples",
                "blocked backlog for commands, identity, persistence, operator ingress, mutation",
                "cannot change the support tier without a named promotion gate",
            ),
        }

        for name, phrases in required.items():
            for phrase in phrases:
                with self.subTest(file=name, phrase=phrase):
                    self.assertIn(normalized(phrase), compacts[name])

        blocked_dependency_terms = (
            "identity",
            "lookup",
            "mutation",
            "return override",
            "ResourceHandle",
            "raw UE",
        )
        for name in ("foundation", "matrix", "roadmap", "research_readme"):
            compact = compacts[name]
            with self.subTest(file=name, item="blocked dependency vocabulary"):
                for term in blocked_dependency_terms:
                    self.assertIn(term.lower(), compact.lower())

    def test_public_contributor_docs_route_plugin_hub_through_foundation_and_matrix(self) -> None:
        required_phrases = {
            REPO_ROOT / "README.md": (
                "Plugin Hub work starts with",
                "docs/PLUGIN_HUB_FOUNDATION_V1.md",
                "docs/PLUGIN_HUB_CAPABILITY_MATRIX.md",
                "NextGenPlugins are held to the same demand-dictionary boundary",
            ),
            REPO_ROOT / "CONTRIBUTING.md": (
                "Start Plugin Hub work from",
                "docs/PLUGIN_HUB_FOUNDATION_V1.md",
                "docs/PLUGIN_HUB_CAPABILITY_MATRIX.md",
                "ArkServerApi, AseApi, and NextGenPlugins are names and demand dictionaries only",
                "not sources for code, offsets, control flow, parsers, schemas, or implementation behavior",
            ),
        }

        for path, phrases in required_phrases.items():
            compact = normalized(path.read_text(encoding="utf-8"))
            for phrase in phrases:
                with self.subTest(file=path.relative_to(REPO_ROOT), phrase=phrase):
                    self.assertIn(normalized(phrase), compact)

    def test_plugin_hub_public_docs_keep_foundation_matrix_and_experimental_split(self) -> None:
        required_phrases = {
            REPO_ROOT / "README.md": (
                "v0.1-rc public C ABI slices",
                "Plugin Hub work starts with",
                "define the current supported seed boundary before any new public SDK surface is proposed",
                "Harden the small production-supported Plugin Hub seed set",
                "Keep copied event examples explicitly experimental",
            ),
            REPO_ROOT / "CONTRIBUTING.md": (
                "Start Plugin Hub work from",
                "ArkServerApi, AseApi, and NextGenPlugins are names and demand dictionaries only",
                "not sources for code, offsets, control flow, parsers, schemas, or implementation behavior",
            ),
            REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md": (
                "Post-RC production-supported seed work is limited to lifecycle/config/logging skeletons",
                "Copied `ChatMessageEvent` parsing and copied `GameplayPolicyEvent` auditing remain experimental seed patterns only",
                "Foundation V1 is enough for small, honest Plugin Hub seeds when the support tier is explicit",
                "Production-supported seeds:",
                "process-local timer utilities",
                "This list names ABI primitives, not Plugin Hub module tiers",
                "Experimental pattern examples only:",
                "copied `GameplayPolicyEvent` auditors",
                "Keep passive copied chat parsing experimental and plugin-local only",
                "Keep copied policy auditors experimental",
                "Foundation V1 does not provide or imply",
            ),
            REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md": (
                "Post-RC production-supported Plugin Hub seed work is limited to lifecycle/config/logging",
                "`experimental seed only`: allowed for explicitly labeled pattern examples",
                "not supported as production Plugin Hub modules",
                "keep the support tier explicit",
                "Production-supported seed lanes",
                "Experimental pattern examples only",
            ),
            REPO_ROOT / "plugins" / "README.md": (
                "The production-supported additions after `v0.1` are descriptor readers and process-local timer utilities",
                "Passive copied-chat parsers and copied policy auditors are experimental pattern examples only",
                "promoted in the public ABI, recorded in the capability matrix, and documented with its own evidence gate",
                "These examples observe copied data only",
                "not policy enforcement, command/chat authority, storage/webhook, or public module SDK examples",
            ),
        }

        offenders: list[str] = []
        for path, phrases in required_phrases.items():
            compact = normalized(path.read_text(encoding="utf-8"))
            for phrase in phrases:
                if normalized(phrase) not in compact:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: missing {phrase}")

        forbidden_phrases = (
            "v0.1-rc SDK surfaces",
            "small SDK seed set for production contributors",
        )
        forbidden_production_experimental_mix = re.compile(
            r"\bproduction-supported\b[^.!?\n;]*(?:copied[- ]chat|copied\s+policy|"
            r"ChatMessageEvent|GameplayPolicyEvent|policy\s+auditors?|chat\s+parsers?)",
            re.IGNORECASE,
        )
        negated_or_split_context = re.compile(
            r"\b(?:not|experimental|only\s+patterns?|remain|remains|may\s+demonstrate)\b",
            re.IGNORECASE,
        )

        for path in PLUGIN_HUB_PUBLIC_BOUNDARY_DOC_FILES:
            text = path.read_text(encoding="utf-8")
            for phrase in forbidden_phrases:
                if phrase in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: forbidden phrase {phrase}")
            for segment_start, segment in sentence_like_segments(text):
                if forbidden_production_experimental_mix.search(segment) and not (
                    negated_or_split_context.search(segment)
                ):
                    line_no = text.count("\n", 0, segment_start) + 1
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT)}:{line_no}: {normalized(segment)}"
                    )

        self.assertEqual(offenders, [])

    def test_mission_plugin_hub_boundary_stays_planning_only(self) -> None:
        foundation = (REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md").read_text(
            encoding="utf-8"
        )
        matrix = (REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md").read_text(
            encoding="utf-8"
        )
        inventory = (
            REPO_ROOT / "docs" / "research" / "2026-05-30-nextgenplugins-reference-inventory.md"
        ).read_text(encoding="utf-8")
        compact_foundation = normalized(foundation)
        compact_matrix = normalized(matrix)
        compact_inventory = normalized(inventory)

        for required in (
            "Mission copied-bool planning and mission demand",
            "Internal/test-only research notes",
            "Planning-only",
            "Production Plugin Hub mission module",
            "ArkApi mission compatibility",
            "command SDK dependency",
        ):
            with self.subTest(required=required):
                self.assertIn(required, compact_matrix)

        for text, required in (
            (compact_foundation, "mission, transfer, storage/database, webhook, or structure modules"),
            (compact_foundation, "public Inventory SDK, Items SDK, StructureEvents SDK, command SDK"),
            (compact_inventory, "transfers, and missions remain investigation/internal unless"),
            (compact_inventory, "This list is not a v1 delivery sequence, compatibility plan, or Plugin Hub roadmap."),
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

        forbidden_positive_claims = (
            r"\bproduction\s+Plugin\s+Hub\s+mission\s+module\b",
            r"\bArkApi\s+mission\s+compatibility\b",
            r"\bmission\s+(?:command\s+)?SDK\b",
        )
        negated_or_boundary_context = re.compile(
            r"\b(?:do\s+not|does\s+not|must\s+not|not|no|never|without|blocked|planning-only|"
            r"demand/research\s+notes\s+only)\b",
            re.IGNORECASE,
        )
        offenders: list[str] = []
        for name, text in (
            ("docs/PLUGIN_HUB_FOUNDATION_V1.md", foundation),
            ("docs/PLUGIN_HUB_CAPABILITY_MATRIX.md", matrix),
            ("docs/research/2026-05-30-nextgenplugins-reference-inventory.md", inventory),
        ):
            for line_no, line in enumerate(text.splitlines(), start=1):
                for pattern in forbidden_positive_claims:
                    if re.search(
                        pattern,
                        line,
                        flags=re.IGNORECASE,
                    ) and not negated_or_boundary_context.search(line):
                        offenders.append(f"{name}:{line_no}: {line.strip()}")

        self.assertEqual(offenders, [])

    def test_v1_modding_route_keeps_broad_surface_without_sdk_promise(self) -> None:
        v1_map = (
            REPO_ROOT / "docs" / "research" / "2026-05-30-v1-core-capability-map.md"
        ).read_text(encoding="utf-8")
        research_readme = (REPO_ROOT / "docs" / "research" / "README.md").read_text(
            encoding="utf-8"
        )
        matrix = (REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md").read_text(
            encoding="utf-8"
        )

        broad_surface_terms = (
            "players",
            "tribes",
            "dinos",
            "items",
            "structures",
            "permissions",
            "commands",
            "admin",
            "transfers",
            "missions",
            "timers",
            "storage",
        )
        focused_lane_terms = (
            "chat",
            "ResourceHandle",
            "APrimalStructure.IsAllowedToBuild",
        )

        for path, text in (
            ("docs/research/2026-05-30-v1-core-capability-map.md", v1_map),
            ("docs/research/README.md", research_readme),
            ("docs/PLUGIN_HUB_CAPABILITY_MATRIX.md", matrix),
        ):
            compact = normalized(text)
            compact_lower = compact.lower()
            with self.subTest(file=path, item="broad surface terms"):
                for term in broad_surface_terms:
                    self.assertIn(term, compact_lower)
            with self.subTest(file=path, item="focused lanes are not center"):
                for term in focused_lane_terms:
                    self.assertIn(term, compact)
                self.assertRegex(
                    compact_lower,
                    r"not (?:a )?(?:narrowed )?(?:v1 product )?center|not narrow|not turn .* center",
                )
            with self.subTest(file=path, item="no SDK promise from breadth"):
                self.assertRegex(
                    compact_lower,
                    r"not (?:a )?(?:delivery |sdk )?promise|not .* sdk promise|no public sdk|not ready",
                )

    def test_plugin_hub_blocked_module_families_stay_unpromoted(self) -> None:
        v1_map = (
            REPO_ROOT / "docs" / "research" / "2026-05-30-v1-core-capability-map.md"
        ).read_text(encoding="utf-8")
        compact_v1_map = normalized(v1_map)

        for required in (
            "Promotion gate before any v1 surface",
            "records hypotheses and required evidence, not production support for permissions, RCON, economy, storage, tribes, dinos, transfers, inventory, commands",
        ):
            with self.subTest(required=required):
                self.assertIn(normalized(required), compact_v1_map)
        self.assertNotIn("v1 core need", compact_v1_map)

        blocked_family = (
            r"permissions?|RCON|economy|shops?|kits?|storage|database|webhook|"
            r"tribes?|dinos?|transfers?|inventory|items?"
        )
        surface_noun = r"modules?|SDKs?|APIs?|services?|surfaces?"
        forbidden_positive_claims = (
            rf"\b(?:production[- ]supported|production|stable|supported|promoted|public|available)\s+"
            rf"(?:Plugin\s+Hub\s+)?(?:{blocked_family})\s+(?:{surface_noun})\b",
            rf"\b(?:{blocked_family})\s+(?:{surface_noun})\s+"
            rf"(?:is|are|as)\s+(?:production[- ]supported|production|stable|supported|promoted|public|available)\b",
        )
        negated_or_boundary_context = re.compile(
            r"\b(?:do\s+not|does\s+not|must\s+not|not|no|never|without|blocked|"
            r"planning-only|future\s+work|experimental|internal|candidate|hypotheses?|"
            r"required\s+evidence|demand\s+signals?|does\s+not\s+promote)\b",
            re.IGNORECASE,
        )

        offenders: list[str] = []
        for path in PLUGIN_HUB_V1_ROADMAP_BOUNDARY_FILES:
            text = path.read_text(encoding="utf-8")
            for segment_start, segment in sentence_like_segments(text):
                context_start = max(0, segment_start - 800)
                context = text[context_start:segment_start + len(segment)]
                for pattern in forbidden_positive_claims:
                    if re.search(pattern, segment, flags=re.IGNORECASE) and not (
                        negated_or_boundary_context.search(context)
                    ):
                        line_no = text.count("\n", 0, segment_start) + 1
                        offenders.append(
                            f"{path.relative_to(REPO_ROOT)}:{line_no}: {normalized(segment)}"
                        )

        self.assertEqual(offenders, [])

    def test_resource_handle_serial_policy_tooling_stays_internal_candidate_only(self) -> None:
        script = (REPO_ROOT / "scripts" / "build_resource_handle_serial_policy.py").read_text(
            encoding="utf-8"
        )
        release = (REPO_ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        status = (REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
        current = (REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md").read_text(
            encoding="utf-8"
        )
        research_note = (
            REPO_ROOT / "docs" / "research" / "2026-05-30-post-rc-offline-resourcehandle-priority.md"
        ).read_text(encoding="utf-8")
        compact_research = normalized(research_note)

        for item in (
            '"""Build a candidate-only serial reuse/wraparound policy artifact."""',
            'SCHEMA = "obelisk.internal-uobject-revalidation-serial-policy.v1"',
            '"evidence_kind": "internal_serial_reuse_wraparound_fail_closed_policy"',
            '"scope": "frame_local_candidate_only"',
            '"public_api": "not_promoted"',
            '"public_lookup_request": "reject"',
            '"promotion_ready": False',
            '"public_resource_handle_ready": False',
            '"post_callback_resource_handle_ready": False',
            '"does_not_promote_persistent_handles"',
            '"does_not_claim_serial_reuse_or_wraparound_safety"',
            '"does_not_claim_slot_reuse_safety_without_fresh_serial"',
            'raise SystemExit("source promotion_ready must be false")',
            'raise SystemExit("source public_resource_handle_ready must be false")',
            'raise SystemExit("source post_callback_resource_handle_ready must be false")',
            'raise SystemExit("source already claims serial reuse/wraparound policy")',
        ):
            with self.subTest(file="scripts/build_resource_handle_serial_policy.py", item=item):
                self.assertIn(item, script)

        for item in (
            "This artifact is a policy contract, not runtime proof.",
            "It does not read cores, rerun scanners, or use server paths.",
            "Only a fresh nonzero serial match in the same hook/callback frame can reach "
            "`allow_candidate_frame_local_only`",
            "The report keeps `promotion_ready=false`, `public_resource_handle_ready=false`, "
            "`post_callback_resource_handle_ready=false`, and `promotion_gate.ready=false`.",
            "does not prove runtime reuse semantics or public lookup safety",
        ):
            with self.subTest(file="docs/research/2026-05-30-post-rc-offline-resourcehandle-priority.md", item=item):
                self.assertIn(normalized(item), compact_research)

        for path, text in (
            ("docs/RELEASE.md", release),
            ("docs/STATUS.md", status),
            ("docs/agent-handoff/CURRENT.md", current),
        ):
            compact = normalized(text)
            compact_lower = compact.lower()
            with self.subTest(file=path, item="strict serial policy remains candidate-only"):
                self.assertIn("strict serial", compact_lower)
                self.assertRegex(compact, r"candidate-only|candidate only")
            with self.subTest(file=path, item="ResourceHandle stays unpromoted"):
                self.assertIn("ResourceHandle", compact)
                self.assertRegex(compact, r"does not (?:unlock|prove)|remain blocked|blocks it")
                self.assertIn("public lookup", compact)

        forbidden_public_markers = (
            "build_resource_handle_serial_policy.py",
            "obelisk.internal-uobject-revalidation-serial-policy.v1",
            "allow_candidate_frame_local_only",
        )
        offenders: list[str] = []
        for path in (
            PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
            *PUBLIC_SDK_GUIDANCE_DOC_FILES,
            REPO_ROOT / "plugins" / "README.md",
        ):
            text = path.read_text(encoding="utf-8")
            for marker in forbidden_public_markers:
                if marker in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {marker}")

        self.assertEqual(offenders, [])

    def test_player_identity_lifecycle_plan_stays_offline_candidate_only(self) -> None:
        plan_path = REPO_ROOT / "docs" / "research" / "2026-05-30-player-identity-lifecycle-plan.md"
        v1_map_path = REPO_ROOT / "docs" / "research" / "2026-05-30-v1-core-capability-map.md"
        readme_path = REPO_ROOT / "docs" / "research" / "README.md"

        plan = plan_path.read_text(encoding="utf-8")
        compact = normalized(plan)
        compact_lower = compact.lower()
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        target_set_name = "players-identity-lifecycle-intake"
        target_set = TARGET_SETS.get(target_set_name)

        for phrase in (
            "candidate-only",
            "copied/redacted fields",
            "no ResourceHandle",
            "no lookup",
            "no SDK",
            "no runtime",
            "no mutation",
            "no return override",
            "promotion_gate.ready=false",
            "promotion_ready=false",
            "no `/servidor/ark` reads/writes",
        ):
            with self.subTest(item=phrase):
                self.assertIn(normalized(phrase), compact)

        for target in (
            "ShooterPlayerController.ServerSendChatMessage",
            "ShooterPlayerController.ServerListPlayers",
            "ShooterPlayerController.ServerKickPlayer",
            "ShooterPlayerController.IsInTribe",
            "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters",
            "MissionType.BPOnPlayerRemovedFromMission",
        ):
            with self.subTest(target=target):
                self.assertIn(target, plan)

        self.assertIn(target_set_name, TARGET_SETS)
        self.assertIn(target_set_name, PLANNING_ONLY_TARGET_SETS)
        self.assertEqual(
            target_set,
            (
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerListPlayers",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerKickPlayer",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerSendChatMessage",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestTribeLog",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.AllowTribeGroupPermission",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.IsInTribe",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientReceiveMyTribeOnlineList",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientReceiveActiveMissionTags",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.AddPlayerToMission",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.BPAllowPlayerToLeaveMission",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.BPOnPlayerRemovedFromMission",
            ),
        )
        self.assertIn("guidance index", compact)
        self.assertIn("not a release/readiness target", compact)
        self.assertIn("not a public target-set", compact)
        self.assertIn("not evidence that fixtures or second-source layouts exist", compact)
        for target in target_set:
            with self.subTest(target_set_target=target):
                self.assertTrue(target.startswith("obelisk.ufunction-chain.snapshot.v1:"))
                self.assertIn(target.rpartition(":")[2], plan)
                self.assertNotRegex(target, r"\b(?:Login|Logout|PostLogin)\b")

        public_manifest_sets = [
            target_set
            for section in ("promoted_events", "rc_events")
            for event in manifest.get(section, [])
            for target_set in event.get("target_sets", [])
        ]
        self.assertNotIn(target_set_name, V010_GAMEPLAY_POLICY_TARGET_SETS)
        self.assertNotIn(target_set_name, V010_CHAT_MESSAGE_TARGET_SETS)
        self.assertNotIn(target_set_name, public_manifest_sets)

        self.assertIn("docs do not establish an exact accepted login/logout target", compact_lower)

        for path in (v1_map_path, readme_path):
            with self.subTest(file=path.relative_to(REPO_ROOT).as_posix()):
                self.assertIn(plan_path.name, path.read_text(encoding="utf-8"))

    def test_planning_only_target_sets_do_not_back_public_sdk_surface(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        public_manifest_sets = {
            target_set
            for section in ("promoted_events", "rc_events")
            for event in manifest.get(section, [])
            for target_set in event.get("target_sets", [])
        }
        public_target_sets = set(V010_GAMEPLAY_POLICY_TARGET_SETS + V010_CHAT_MESSAGE_TARGET_SETS)

        self.assertIn("mission-copied-bool-policy-slice", PLANNING_ONLY_TARGET_SETS)
        self.assertIn("structure-aggregate-census-planning", PLANNING_ONLY_TARGET_SETS)
        self.assertEqual(sorted(set(PLANNING_ONLY_TARGET_SETS) & public_manifest_sets), [])
        self.assertEqual(sorted(set(PLANNING_ONLY_TARGET_SETS) & public_target_sets), [])

        mention_context_re = re.compile(
            r"\b(?:blocked|candidate-only|guidance-only|internal|not\s+(?:a\s+)?public|planning-only|rejected)\b",
            re.IGNORECASE,
        )
        offenders: list[str] = []
        for path in PUBLIC_SDK_GUIDANCE_DOC_FILES:
            for paragraph in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
                if not any(
                    target_set in paragraph
                    for target_set in (
                        "mission-copied-bool-policy-slice",
                        "structure-aggregate-census-planning",
                    )
                ):
                    continue
                if not mention_context_re.search(normalized(paragraph)):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {normalized(paragraph)}")

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
