#!/usr/bin/env python3
"""Guardrails that keep experimental gameplay modules out of the public SDK."""

from __future__ import annotations

import hashlib
import json
import re
import runpy
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REFLECTION_TARGET_SET_VARS = runpy.run_path(str(REPO_ROOT / "scripts" / "reflection_target_sets.py"))
TARGET_SETS = REFLECTION_TARGET_SET_VARS["TARGET_SETS"]
PLANNING_ONLY_TARGET_SETS = REFLECTION_TARGET_SET_VARS["PLANNING_ONLY_TARGET_SETS"]
RELEASE_READINESS_TARGET_SETS = REFLECTION_TARGET_SET_VARS["RELEASE_READINESS_TARGET_SETS"]
PUBLIC_GAMEPLAY_EVENTS_MANIFEST = REPO_ROOT / "docs" / "public_gameplay_events.json"
PUBLIC_SDK_SURFACES_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISIONS = (
    REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
)
COMMAND_CHAT_RESPONSE_PUBLIC_CONTRACT_DECISIONS = (
    REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
)
PUBLIC_SDK_V1_COMPATIBILITY_DOC = REPO_ROOT / "docs" / "SDK_V1_COMPATIBILITY.md"
PLUGIN_HUB_PACKAGE_TEMPLATE_DOC = REPO_ROOT / "docs" / "PLUGIN_HUB_PACKAGE_TEMPLATE.md"
PUBLIC_API_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
PUBLIC_DOC_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / "docs" / "README.md",
    REPO_ROOT / "docs" / "ARCHITECTURE.md",
    REPO_ROOT / "docs" / "INSTALL.md",
    REPO_ROOT / "docs" / "OPERATOR_CLI.md",
    REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CONTRIBUTOR_PATH.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_SEED_BOUNDARY.md",
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
SDK_TIMER_PLUGIN_EXAMPLE_FILES = [
    REPO_ROOT / "examples" / "sdk_timer_plugin" / "CMakeLists.txt",
    REPO_ROOT / "examples" / "sdk_timer_plugin" / "README.md",
    REPO_ROOT / "examples" / "sdk_timer_plugin" / "timer_plugin.c",
]
SDK_DESCRIPTOR_CATALOG_EXAMPLE_FILES = [
    REPO_ROOT / "examples" / "sdk_descriptor_catalog" / "CMakeLists.txt",
    REPO_ROOT / "examples" / "sdk_descriptor_catalog" / "README.md",
    REPO_ROOT / "examples" / "sdk_descriptor_catalog" / "descriptor_catalog_plugin.c",
]
SDK_INVENTORY_POLICY_AUDIT_EXAMPLE_FILES = [
    REPO_ROOT / "examples" / "sdk_inventory_policy_audit" / "CMakeLists.txt",
    REPO_ROOT / "examples" / "sdk_inventory_policy_audit" / "README.md",
    REPO_ROOT
    / "examples"
    / "sdk_inventory_policy_audit"
    / "inventory_policy_audit_plugin.c",
]
INSTALLED_SDK_EXAMPLE_SUPPORT_TIERS = {
    "sdk_minimal_plugin": "release-supported seed",
    "sdk_descriptor_catalog": "release-supported seed",
    "sdk_timer_plugin": "release-supported seed",
    "sdk_inventory_policy_audit": "experimental pattern",
}
PUBLIC_RELEASE_SCOPE_DOC_FILES = [
    REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
    REPO_ROOT / "docs" / "RELEASE.md",
    REPO_ROOT / "docs" / "STATUS.md",
]
CHAT_COMMAND_HELPER_ROADMAP = (
    REPO_ROOT / "docs" / "research" / "2026-05-30-chat-command-helper-roadmap.md"
)
CHAT_COMMAND_READINESS_AUDIT = (
    REPO_ROOT / "docs" / "research" / "2026-05-31-chat-command-readiness.md"
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
    REPO_ROOT / "docs" / "PLUGIN_HUB_CONTRIBUTOR_PATH.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
    REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
    PLUGIN_HUB_PACKAGE_TEMPLATE_DOC,
    REPO_ROOT / "docs" / "PLUGIN_HUB_SEED_BOUNDARY.md",
    REPO_ROOT / "plugins" / "README.md",
]
PLUGIN_HUB_PUBLIC_SEED_DOC_FILES = [
    REPO_ROOT / "docs" / "oBaseEvents.md",
    REPO_ROOT / "docs" / "oDescriptorCatalog.md",
    REPO_ROOT / "docs" / "oProcessTimer.md",
]
RESEARCH_MODULE_BOUNDARY_README = REPO_ROOT / "docs" / "research" / "README.md"
LATEST_V1_SDK_ROUND_RESEARCH_NOTE = (
    REPO_ROOT / "docs" / "research" / "2026-05-31-v1-sdk-round-identity-static-demand-audit.md"
)
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
UNPROMOTED_CHAT_COMMAND_RESPONSE_API_TOKENS = (
    "OBELISK_API_CAPABILITY_CHAT_COMMANDS",
    "OBELISK_API_CAPABILITY_CHAT_RESPONSES",
    "OBELISK_API_CAPABILITY_SEND_CHAT",
    "OBELISK_API_CAPABILITY_CHAT_MODERATION",
    "OBELISK_API_CAPABILITY_COMMAND_REPLIES",
    "OBELISK_API_CAPABILITY_PERMISSION_CHECKS",
    "ObeliskChatCommand",
    "ObeliskChatCommandEvent",
    "ObeliskChatCommandContext",
    "ObeliskChatCommandReply",
    "ObeliskChatResponse",
    "ObeliskChatModeration",
    "ObeliskPermissionQuery",
    "RegisterChatCommand",
    "RegisterCommand",
    "RegisterCommandHandler",
    "RegisterChatRoute",
    "RegisterChatResponse",
    "RegisterChatModeration",
    "UnregisterChatCommand",
    "UnregisterCommand",
    "UnregisterCommandHandler",
    "ReplyToCommand",
    "ReplyToChat",
    "SendChat",
    "SendChatMessage",
    "BroadcastChat",
    "ModerateChat",
)
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
    PUBLIC_API_HEADER,
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
EXPERIMENTAL_COPIED_EVENT_TOKENS = {
    "chatmessageevent",
    "gameplaypolicyevent",
}
EXPERIMENTAL_EVENT_V1_COMPLETION_NEGATORS = {
    "blocked",
    "blocks",
    "downgraded",
    "exclude",
    "excluded",
    "excludes",
    "excluding",
    "experimental",
    "never",
    "no",
    "not",
    "only",
    "outside",
    "post-v1",
    "promoted-experimental-only",
    "until",
    "without",
}
EXPERIMENTAL_EVENT_V1_COMPLETION_BREAKERS = {
    "but",
    "unless",
    "until",
    "whereas",
    "while",
}
EXPERIMENTAL_EVENT_V1_COMPLETION_WINDOW = 14
BROAD_V1_COMPLETION_CLAIM_FILES = [
    PUBLIC_API_HEADER,
    *PUBLIC_SDK_GUIDANCE_DOC_FILES,
    PUBLIC_SDK_V1_COMPATIBILITY_DOC,
    REPO_ROOT / "examples" / "README.md",
    REPO_ROOT / "examples" / "sdk_minimal_plugin" / "README.md",
    REPO_ROOT / "examples" / "sdk_timer_plugin" / "README.md",
    REPO_ROOT / "agent-skills" / "obelisk-github-research-workflow" / "SKILL.md",
]
BROAD_V1_COMPLETION_POSITIVE_RE = re.compile(
    r"\b(?:"
    r"(?:v1(?:\.0)?\s+stable|v1[- ]?0\s+stable).{0,80}"
    r"(?:available|complete|delivered|for\s+production|production[- ]ready|ready|released|shipped|supported)|"
    r"(?:complete|full|production[- ]ready)[- ]+(?:public[- ]+|plugin[- ]+)?SDK|"
    r"(?:complete|full|production[- ]ready)[- ]+(?:public[- ]+|plugin[- ]+)?SDK.{0,80}"
    r"(?:available|delivered|production[- ]ready|ready|released|shipped|supported|today|use)|"
    r"(?:available|delivered|ready|released|shipped|supported|use).{0,80}"
    r"(?:complete|full|production[- ]ready)[- ]+(?:public[- ]+)?SDK|"
    r"(?:stable[- ]?(?:v1|v1-0|1-0|1\.0)|(?:v1|v1-0|1-0|1\.0)[- ]?stable).{0,24}(?:public[- ]+|plugin[- ]+)?SDK|"
    r"(?:v1|v1-0|1-0|1\.0)\s+(?:public[- ]+|plugin[- ]+)?SDK.{0,48}"
    r"(?:available|complete|production[- ]ready|ready|released|shipped|supported)|"
    r"(?:SDK|public[- ]+SDK|plugin[- ]+SDK).{0,24}(?:v1|v1-0|1-0|1\.0).{0,48}"
    r"(?:available|complete|production[- ]ready|ready|released|shipped|stable|supported)|"
    r"GA\s+(?:public[- ]+|plugin[- ]+)?SDK|"
    r"all\s+v1\s+(?:SDK\s+)?surfaces\s+are\s+available"
    r")\b",
    re.IGNORECASE,
)
BROAD_V1_COMPLETION_NEGATED_RE = re.compile(
    r"\b(?:"
    r"blocked|candidate|candidate-only|definition|does\s+not|do\s+not|foundation|"
    r"intended|must\s+mean|must\s+not|no|not|planning|post-v1|prevent|prevents|rc|scanned|toward|track|unless|until|without"
    r")\b",
    re.IGNORECASE,
)
PRE_V1_RC_COMPLETE_SDK_POSITIVE_RE = re.compile(
    r"\b(?:v0(?:\.1(?:\.\d+)?)?|0\.1(?:\.\d+)?|pre[- ]v1|rc|release\s+candidate|post[- ]rc)\b"
    r".{0,80}\b(?:complete|full|production[- ]ready)[- ]+(?:public[- ]+|plugin[- ]+)?SDK\b|"
    r"\b(?:complete|full|production[- ]ready)[- ]+(?:public[- ]+|plugin[- ]+)?SDK\b"
    r".{0,80}\b(?:v0(?:\.1(?:\.\d+)?)?|0\.1(?:\.\d+)?|pre[- ]v1|rc|release\s+candidate|post[- ]rc)\b|"
    r"\b(?:v0(?:\.1(?:\.\d+)?)?|0\.1(?:\.\d+)?|pre[- ]v1|rc|release\s+candidate|post[- ]rc)\b"
    r".{0,80}\b(?:SDK|public[- ]+SDK|plugin[- ]+SDK)\b.{0,48}"
    r"\b(?:complete|full|production[- ]ready)\b|"
    r"\b(?:SDK|public[- ]+SDK|plugin[- ]+SDK)\b.{0,48}\b(?:complete|full|production[- ]ready)\b"
    r".{0,80}\b(?:v0(?:\.1(?:\.\d+)?)?|0\.1(?:\.\d+)?|pre[- ]v1|rc|release\s+candidate|post[- ]rc)\b",
    re.IGNORECASE,
)
PRE_V1_RC_COMPLETE_SDK_NEGATED_RE = re.compile(
    r"\b(?:"
    r"blocked|cannot|does\s+not|do\s+not|insufficient|must\s+not|no|not|planning|prevent|prevents|toward|unless|until|without"
    r")\b",
    re.IGNORECASE,
)
SCOPE_EXPANSION_NEGATOR_RE = re.compile(r"\bnot\s+(?:just|only|merely|simply)\b", re.IGNORECASE)
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
PLUGIN_HUB_SUPPORT_TIERS = (
    "release-supported seed",
    "experimental pattern",
    "blocked backlog",
)
PLUGIN_HUB_SUPPORT_TIER_DECLARATION_RE = re.compile(
    r"[\"'`]*\b(?:declared\s+)?support[_ -]tier\b[\"'`]*\s*[:=]\s*[\"'`]*"
    r"(release-supported seed|experimental pattern|blocked backlog)"
    r"[\"'`]*\b",
    re.IGNORECASE,
)
PLUGIN_HUB_SEED_PACKAGE_METADATA_NAMES = {
    "manifest.json",
    "obelisk-plugin.json",
    "package.json",
    "package.toml",
    "plugin.json",
    "plugin.toml",
}
PLUGIN_HUB_SEED_CLAIM_SUPPORT_RE = (
    r"(?:available|compatib(?:le|ility)|exposes?|implements?|production[- ]ready|"
    r"production[- ]supported|promotes?|promoted|provides?|public|ready|released|"
    r"ships?|shipped|stable|supported|supports?)"
)
PLUGIN_HUB_SEED_FORBIDDEN_TERM_RE = (
    r"(?:"
    r"v1(?:\.0)?(?:[- ]?(?:stable|SDK|complete))?|"
    r"ArkApi|AseApi|"
    r"commands?|command[- ]?(?:SDK|router|routing|surface)|"
    r"permissions?|permissions?[- ]?(?:SDK|surface)|"
    r"(?:player|sender|resource|object|inventory|item|structure)?[- ]?identity|"
    r"send[- ]?chat|repl(?:y|ies)|"
    r"mutation|mutations|mutate|"
    r"storage|database|webhooks?|economy|shops?|kits?|homes?|"
    r"Inventory[- ]?SDK|inventory(?:/item)?|"
    r"StructureEvents?|structures?"
    r")"
)
PLUGIN_HUB_SEED_FORBIDDEN_CLAIM_RE = re.compile(
    rf"\b{PLUGIN_HUB_SEED_FORBIDDEN_TERM_RE}\b.{{0,96}}\b{PLUGIN_HUB_SEED_CLAIM_SUPPORT_RE}\b|"
    rf"\b{PLUGIN_HUB_SEED_CLAIM_SUPPORT_RE}\b.{{0,96}}\b{PLUGIN_HUB_SEED_FORBIDDEN_TERM_RE}\b",
    re.IGNORECASE,
)
PLUGIN_HUB_SEED_FORBIDDEN_NEGATED_RE = re.compile(
    r"\b(?:blocked|cannot|does\s+not|do\s+not|excluded|excludes?|fail[- ]closed|"
    r"future|not|no|never|only|outside|planning|planning-only|reject|rejected|"
    r"remain|remains|until|without)\b",
    re.IGNORECASE,
)
PLUGIN_HUB_SEED_LOCAL_BOUNDARY_RE = re.compile(
    r"\b(?:callback-scope|copied\s+metadata|diagnostic|plugin-local|process-local|"
    r"safe-disabled)\b",
    re.IGNORECASE,
)
PLUGIN_HUB_PUBLIC_DOC_CLAIM_SUPPORT_RE = (
    r"(?:available|compatib(?:le|ility)|exposes?|implements?|production[- ]ready|"
    r"production[- ]supported|provides?|ready|released|ships?|shipped|stable|complete(?:d|s)?|"
    r"supported|supports?)"
)
PLUGIN_HUB_PUBLIC_DOC_CLAIM_RE = re.compile(
    rf"\b{PLUGIN_HUB_SEED_FORBIDDEN_TERM_RE}\b.{{0,96}}\b{PLUGIN_HUB_PUBLIC_DOC_CLAIM_SUPPORT_RE}\b|"
    rf"\b{PLUGIN_HUB_PUBLIC_DOC_CLAIM_SUPPORT_RE}\b.{{0,96}}\b{PLUGIN_HUB_SEED_FORBIDDEN_TERM_RE}\b",
    re.IGNORECASE,
)
PLUGIN_HUB_PUBLIC_DOC_NEGATED_RE = re.compile(
    r"\b(?:blocked|cannot|does\s+not|do\s+not|excluded|excludes?|fail|future|"
    r"must\s+not|need|needs|not|no|never|only|outside|planning|planning-only|"
    r"reject|rejected|remain|remains|requires?|until|without)\b",
    re.IGNORECASE,
)
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
UNPROMOTED_PUBLIC_MODULE_FAMILIES = (
    "INVENTORY",
    "ITEM",
    "DINO",
    "STRUCTURE",
    "MISSION",
    "TRANSFER",
    "BUFF",
    "TRIBE",
    "PLAYER",
    "PERMISSION",
    "ADMIN",
    "COMMAND",
)
V010_PUBLIC_MODULE_SYMBOL_EXCEPTIONS = {
    "OBELISK_CHAT_SEND_MODE_TRIBE",
    "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED",
    "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES",
    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
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
    "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE",
    "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
    "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER",
    "OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER",
}
V010_LEGACY_REGISTER_FIELD_EXCEPTIONS = {
    "RegisterPreProcessEvent",
    "RegisterPostProcessEvent",
    "RegisterPreProcessEventForNameIndex",
    "RegisterPostProcessEventForNameIndex",
    "RegisterPreProcessEventWithOwnerToken",
    "RegisterPostProcessEventWithOwnerToken",
    "RegisterPreProcessEventForNameIndexWithOwnerToken",
    "RegisterPostProcessEventForNameIndexWithOwnerToken",
}
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
    "ObeliskPlayerPrincipal",
    "ObeliskPrincipalId",
    "ObeliskPlayerLifecycleEvent",
    "ObeliskPlayerPrincipalLifecycle",
    "ObeliskPlayerPrincipalLifecycleEvent",
    "ObeliskPrincipalLifecycleEvent",
    "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
    "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL",
    "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE",
    "OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE",
    "OBELISK_API_CAPABILITY_PRINCIPAL_LIFECYCLE",
    "PlayerPrincipalLifecycleEventCallback",
    "ObeliskPlayerPrincipalLifecycleCallback",
    "RegisterPlayerPrincipalLifecycle",
    "RegisterPlayerPrincipalLifecycleEvent",
    "RegisterPlayerPrincipalLifecycleWithOwnerTokenHandle",
    "RegisterPlayerLifecycle",
    "RegisterPlayerIdentityEvent",
    "UnregisterPlayerPrincipalLifecycle",
    "UnregisterPlayerPrincipalLifecycleEvent",
    "PlayerPrincipal",
    "PrincipalLookup",
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
PLAYER_PRINCIPAL_INTERNAL_PUBLIC_ABI_TOKENS = (
    "PlayerPrincipalEventDispatcher",
    "PlayerPrincipalEventView",
    "PlayerPrincipalEventSubscription",
    "PlayerPrincipalEventCallback",
    "PlayerPrincipalEventKind",
    "PlayerPrincipalAction",
    "PlayerPrincipalBoolField",
    "PlayerPrincipalBoolValue",
    "ObeliskPlayerPrincipal",
    "ObeliskPrincipal",
    "ObeliskPrincipalId",
    "ObeliskPlayerPrincipalEvent",
    "ObeliskPlayerPrincipalEventCallback",
    "ObeliskPlayerPrincipalSubscription",
    "ObeliskPlayerPrincipalLifecycle",
    "ObeliskPlayerPrincipalLifecycleEvent",
    "ObeliskPrincipalLifecycleEvent",
    "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
    "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL",
    "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS",
    "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE",
    "OBELISK_API_CAPABILITY_PRINCIPAL_EVENTS",
    "OBELISK_API_CAPABILITY_PRINCIPAL_LIFECYCLE",
    "RegisterPlayerPrincipal",
    "RegisterPlayerPrincipalEvent",
    "RegisterPlayerPrincipalWithOwnerToken",
    "RegisterPlayerPrincipalWithOwnerTokenHandle",
    "RegisterPlayerPrincipalLifecycle",
    "RegisterPlayerPrincipalLifecycleEvent",
    "RegisterPlayerPrincipalLifecycleWithOwnerToken",
    "RegisterPlayerPrincipalLifecycleWithOwnerTokenHandle",
    "UnregisterPlayerPrincipal",
    "UnregisterPlayerPrincipalEvent",
    "UnregisterPlayerPrincipalWithOwnerToken",
    "UnregisterPlayerPrincipalLifecycle",
    "UnregisterPlayerPrincipalLifecycleEvent",
    "UnregisterPlayerPrincipalLifecycleWithOwnerToken",
    "DescribePlayerPrincipal",
    "DescribePlayerIdentity",
    "ResolvePlayerPrincipal",
    "ResolvePlayerIdentity",
    "LookupPlayerPrincipal",
    "LookupPlayerIdentity",
    "FindPlayerPrincipal",
    "FindPlayerIdentity",
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
    *UNPROMOTED_CHAT_COMMAND_RESPONSE_API_TOKENS,
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
        "public_register_slots": [
            "RegisterPreProcessEventWithOwnerTokenHandle",
            "RegisterPostProcessEventWithOwnerTokenHandle",
            "RegisterPreProcessEventForNameIndexWithOwnerTokenHandle",
            "RegisterPostProcessEventForNameIndexWithOwnerTokenHandle",
        ],
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
        "owner_cleanup_token": "EventManager::Get().UnregisterCallbacksForOwner(owner)",
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
        "owner_cleanup_token": "UnregisterGameplayPolicyRegistrationsForOwner(owner)",
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
        "owner_cleanup_token": "UnregisterChatMessageRegistrationsForOwner(owner)",
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
        "owner_cleanup_token": "TimerManager::Get().UnregisterCallbacksForOwner(owner)",
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


def public_obelisk_macro_defines(header: str) -> list[str]:
    return re.findall(
        r"^\s*#define\s+(OBELISK_[A-Z0-9_]+)\b",
        strip_c_comments(header),
        re.MULTILINE,
    )


def module_family_hits(symbol: str) -> set[str]:
    parts = set(symbol.upper().split("_"))
    hits: set[str] = set()
    for family in UNPROMOTED_PUBLIC_MODULE_FAMILIES:
        variants = {family, f"{family}S"}
        if family.endswith("Y"):
            variants.add(f"{family[:-1]}IES")
        if parts.intersection(variants):
            hits.add(family)
    return hits


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


def c_like_includes(source: str) -> list[str]:
    return [
        match.group("header")
        for match in re.finditer(
            r"^\s*#\s*include\s*[<\"](?P<header>[^>\"]+)[>\"]",
            strip_c_comments(source),
            re.MULTILINE,
        )
    ]


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


def experimental_event_v1_completion_claims(text: str, relative_path: str) -> list[str]:
    offenders: list[str] = []
    scan_text = re.sub(r"\bv1\.0\b", "v1-0", text)

    for segment_start, segment in sentence_like_segments(scan_text):
        tokens = [match.group(0).lower() for match in TOKEN_RE.finditer(segment)]
        event_indices = [
            index
            for index, token in enumerate(tokens)
            if token in EXPERIMENTAL_COPIED_EVENT_TOKENS
        ]
        if not event_indices:
            continue

        v1_indices = [
            index
            for index, token in enumerate(tokens)
            if token in {"v1", "v1-0", "v1-complete", "v1_completion_required"}
        ]
        completion_indices = [
            index
            for index, token in enumerate(tokens)
            if token in {"complete", "completed", "completes", "completion", "complete-sdk"}
        ]
        stable_indices = [
            index
            for index, token in enumerate(tokens)
            if token in {"stable", "v1-stable"}
        ]

        claim_indices = [
            index
            for index in sorted(set(completion_indices + stable_indices + v1_indices))
            if (
                tokens[index] in {"v1-complete", "v1-stable"}
                or (
                    v1_indices
                    and (
                        completion_indices
                        or stable_indices
                        or "v1_completion_required" in tokens
                    )
                )
            )
        ]
        if not claim_indices:
            continue

        for event_index in event_indices:
            for claim_index in claim_indices:
                if abs(event_index - claim_index) > EXPERIMENTAL_EVENT_V1_COMPLETION_WINDOW:
                    continue

                start = min(event_index, claim_index)
                end = max(event_index, claim_index)
                relation_tokens = tokens[start : end + 1]
                negation_tokens = tokens[max(0, start - 6) : end + 1]
                if EXPERIMENTAL_EVENT_V1_COMPLETION_BREAKERS.intersection(relation_tokens):
                    continue
                if EXPERIMENTAL_EVENT_V1_COMPLETION_NEGATORS.intersection(negation_tokens):
                    continue

                line = scan_text.count("\n", 0, segment_start) + 1
                compact_segment = " ".join(segment.split())
                offenders.append(f"{relative_path}:{line}: {compact_segment}")
                break

    return offenders


def broad_v1_completion_claims(text: str, relative_path: str) -> list[str]:
    offenders: list[str] = []
    scan_text = re.sub(r"\bv1\.0\b", "v1-0", text)
    scan_text = re.sub(r"\b1\.0\b", "1-0", scan_text)
    scan_text = re.sub(r"(?<!\n)\n(?!\n)", " ", scan_text)

    for segment_start, segment in sentence_like_segments(scan_text):
        negation_scan_segment = SCOPE_EXPANSION_NEGATOR_RE.sub(
            "scope expansion",
            segment,
        )
        pre_v1_rc_complete_sdk_claim = PRE_V1_RC_COMPLETE_SDK_POSITIVE_RE.search(segment)
        if (
            pre_v1_rc_complete_sdk_claim
            and not PRE_V1_RC_COMPLETE_SDK_NEGATED_RE.search(negation_scan_segment)
        ):
            line = scan_text.count("\n", 0, segment_start) + 1
            offenders.append(f"{relative_path}:{line}: {normalized(segment)}")
            continue

        if not BROAD_V1_COMPLETION_POSITIVE_RE.search(segment):
            continue
        if BROAD_V1_COMPLETION_NEGATED_RE.search(segment):
            continue

        line = scan_text.count("\n", 0, segment_start) + 1
        offenders.append(f"{relative_path}:{line}: {normalized(segment)}")

    return offenders


def plugin_hub_seed_review_files() -> list[Path]:
    paths = {PLUGIN_HUB_PACKAGE_TEMPLATE_DOC, *PLUGIN_HUB_PUBLIC_SEED_DOC_FILES}

    for root_name in ("examples", "plugins"):
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for child in root.iterdir():
            if not child.is_dir():
                continue
            readme = child / "README.md"
            if readme.is_file():
                paths.add(readme)
            for package_file in child.rglob("*"):
                if package_file.is_file() and package_file.name in PLUGIN_HUB_SEED_PACKAGE_METADATA_NAMES:
                    paths.add(package_file)

    return sorted(paths)


def plugin_hub_support_tier_declarations(text: str) -> list[str]:
    return [
        match.group(1).lower()
        for match in PLUGIN_HUB_SUPPORT_TIER_DECLARATION_RE.finditer(text)
    ]


def plugin_hub_seed_forbidden_claims(
    text: str,
    relative_path: str,
    support_tier: str,
) -> list[str]:
    offenders = broad_v1_completion_claims(text, relative_path)

    for segment_start, segment in sentence_like_segments(text):
        for match in PLUGIN_HUB_SEED_FORBIDDEN_CLAIM_RE.finditer(segment):
            absolute_match_start = segment_start + match.start()
            absolute_match_end = segment_start + match.end()
            context = text[max(0, absolute_match_start - 160): absolute_match_end + 80]
            if PLUGIN_HUB_SEED_FORBIDDEN_NEGATED_RE.search(context):
                continue
            if (
                support_tier == "experimental pattern"
                and PLUGIN_HUB_SEED_LOCAL_BOUNDARY_RE.search(context)
            ):
                continue

            line = text.count("\n", 0, segment_start) + 1
            offenders.append(
                f"{relative_path}:{line}: {support_tier}: {normalized(segment)}"
            )
            break

    return offenders


def plugin_hub_public_doc_forbidden_claims(text: str, relative_path: str) -> list[str]:
    offenders = broad_v1_completion_claims(text, relative_path)

    for segment_start, segment in sentence_like_segments(text):
        for match in PLUGIN_HUB_PUBLIC_DOC_CLAIM_RE.finditer(segment):
            absolute_match_start = segment_start + match.start()
            absolute_match_end = segment_start + match.end()
            context = text[max(0, absolute_match_start - 240): absolute_match_end + 120]
            if PLUGIN_HUB_PUBLIC_DOC_NEGATED_RE.search(context):
                continue

            line = text.count("\n", 0, segment_start) + 1
            offenders.append(f"{relative_path}:{line}: {normalized(segment)}")
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


def evidence_target_set_values(value: object, path: str = "evidence") -> list[tuple[str, str]]:
    target_sets: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in {"target_set", "target_sets", "planning_target_sets", "release_readiness_target_sets"}:
                if isinstance(child, str):
                    target_sets.append((child_path, child))
                elif isinstance(child, list):
                    for index, item in enumerate(child):
                        if isinstance(item, str):
                            target_sets.append((f"{child_path}[{index}]", item))
                continue
            target_sets.extend(evidence_target_set_values(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            target_sets.extend(evidence_target_set_values(child, f"{path}[{index}]"))
    return target_sets


class PublicSdkGuardrailTests(unittest.TestCase):
    def test_player_identity_public_contract_decisions_block_public_header_until_evidence_complete(self) -> None:
        decisions = json.loads(PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISIONS.read_text(encoding="utf-8"))

        self.assertEqual(decisions["schema"], "obelisk.player-identity-public-contract-decisions.v1")
        self.assertEqual(decisions["surface"], "obelisk.player_identity.v1")
        self.assertEqual(decisions["status"], "blocked")
        self.assertEqual(decisions["planning_stage"], "identity_public_contract_gate")
        self.assertEqual(decisions["decision_gate"]["id"], "identity_public_contract_gate")
        self.assertEqual(decisions["decision_gate"]["status"], "blocked/planning")
        self.assertIs(decisions["public_header_allowed"], False)
        self.assertEqual(decisions["public_header"], "include/obelisk/ObeliskApi.h")
        self.assertEqual(decisions["public_header_symbols_now"], [])
        self.assertEqual(decisions["public_capability_bits_now"], [])
        self.assertEqual(decisions["public_callback_abi_now"], [])

        forbidden_contract = set(decisions.get("forbidden_public_contract", []))
        self.assertTrue(
            {
                "UE pointers",
                "raw params",
                "FName/GObjects indices",
                "ResourceHandle",
                "pointer-derived identity",
                "lookup",
                "mutation",
                "return override",
            }.issubset(forbidden_contract)
        )

        requirements = decisions.get("required_before_public_header")
        self.assertIsInstance(requirements, list)
        requirement_ids = {item.get("id") for item in requirements if isinstance(item, dict)}
        self.assertTrue(
            {
                "evidence.complete_non_protected_pack",
                "evidence.accepted_session_start_anchor",
                "evidence.accepted_session_end_anchor",
                "evidence.second_source_anchor_layout",
                "privacy.public_identifier_form",
                "privacy.redacted_identifier_fields",
                "privacy.logging_and_storage_policy",
                "lifetime.principal_scope",
                "lifetime.invalidation_events",
                "lifetime.reconnect_duplicate_stale_policy",
                "abi.payload_shape",
                "abi.capability_bits",
                "abi.owner_token_registration",
                "abi.append_only_layout_tests",
                "separation.no_commands_permissions_persistence",
            }.issubset(requirement_ids)
        )
        self.assertTrue(
            all(
                isinstance(item, dict) and item.get("status") == "unresolved"
                for item in requirements
            )
        )

    def test_player_identity_public_contract_gate_records_pod_proposal_and_runtime_evidence_limit(self) -> None:
        decisions = json.loads(PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISIONS.read_text(encoding="utf-8"))

        runtime_limit = decisions["approved_runtime_evidence_not_sufficient"]
        self.assertIn("necessary evidence", runtime_limit["decision"])
        self.assertIn("not sufficient", runtime_limit["decision"])
        for reason in (
            "runtime evidence can prove a candidate lifecycle route was observed; it does not define a stable C ABI",
            "runtime evidence does not provide ABI layout tests, SDK consumer tests, or append-only compatibility rules",
            "runtime evidence does not authorize permissions/admin, command/chat response, player lookup, persistence, mutation, return override, or cross-process identity claims",
        ):
            self.assertIn(reason, runtime_limit["why"])

        proposal = decisions["proposed_public_pod_abi_candidate"]
        self.assertEqual(proposal["status"], "proposal_only_not_public")
        self.assertFalse(proposal["public_header_allowed"])
        for field in (
            "abi_version",
            "struct_size",
            "principal_handle",
            "principal_generation",
            "principal_scope_flags",
            "invalidation_reason_flags",
        ):
            self.assertIn(field, proposal["candidate_event_payload_fields_or_equivalent"])
        for property_name in (
            "POD C ABI only",
            "front-loaded abi_version and struct_size",
            "append-only fields after promotion",
            "copied Obelisk-owned storage",
            "no UE pointers",
            "no FName/GObjects indices",
            "no lookup handle",
            "no mutation or return override authority",
        ):
            self.assertIn(property_name, proposal["required_payload_properties"])

        non_claims = set(decisions["non_claims"])
        self.assertIn("This manifest does not add public header symbols.", non_claims)
        self.assertIn("This manifest does not make approved runtime evidence sufficient by itself.", non_claims)
        self.assertIn("This manifest does not promote permissions/admin.", non_claims)
        self.assertIn("This manifest does not promote command/chat response or commands/replies.", non_claims)

        required_test_ids = {
            item["id"]
            for item in decisions["required_tests_before_public_header"]
        }
        self.assertEqual(
            required_test_ids,
            {
                "manifest.guardrails",
                "abi.layout",
                "sdk.consumer",
                "lifecycle.owner_cleanup",
                "identity.fail_closed",
                "privacy.redaction",
                "runtime.evidence_intake",
            },
        )

    def test_player_principal_dispatcher_stays_internal_until_identity_promotion(self) -> None:
        header = strip_c_comments(PUBLIC_API_HEADER.read_text(encoding="utf-8"))
        public_header_texts = {
            path.relative_to(REPO_ROOT).as_posix(): strip_c_comments(path.read_text(encoding="utf-8"))
            for path in sorted((REPO_ROOT / "include" / "obelisk").rglob("*"))
            if path.is_file() and path.suffix in {".h", ".hpp"}
        }
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        player_identity = surfaces["obelisk.player_identity.v1"]

        self.assertEqual(player_identity["status"], "planning")
        self.assertEqual(player_identity["public_contract"], [])
        self.assertNotIn("obelisk.player_identity.v1", manifest["promoted_surfaces"])
        self.assertEqual(player_identity["evidence"].get("public_header_symbols_now", []), [])
        self.assertEqual(player_identity["evidence"].get("public_capability_bits_now", []), [])

        public_abi_tokens = set(public_api_capability_defines(header))
        public_abi_tokens.update(obelisk_api_field_names(header))
        public_abi_tokens.update(public_struct_typedefs(header))
        public_abi_tokens.update(public_enum_typedefs(header))
        public_abi_tokens.update(public_callback_typedefs(header))

        leaked_tokens = []
        for token in PLAYER_PRINCIPAL_INTERNAL_PUBLIC_ABI_TOKENS:
            if token in public_abi_tokens:
                leaked_tokens.append(f"include/obelisk/ObeliskApi.h ABI: {token}")
                continue
            for relative, text in public_header_texts.items():
                if token in text:
                    leaked_tokens.append(f"{relative}: {token}")
        leaked_tokens.sort()
        self.assertEqual(leaked_tokens, [])

    def test_command_chat_response_public_contract_decisions_block_public_header(self) -> None:
        decisions = json.loads(COMMAND_CHAT_RESPONSE_PUBLIC_CONTRACT_DECISIONS.read_text(encoding="utf-8"))

        self.assertEqual(decisions["schema"], "obelisk.command-chat-response-public-contract-decisions.v1")
        self.assertEqual(decisions["surface"], "obelisk.command_chat_response_path.v1")
        self.assertEqual(decisions["status"], "blocked")
        self.assertIs(decisions["public_header_allowed"], False)
        self.assertEqual(decisions["public_header_symbols_now"], [])
        self.assertIs(decisions["legacy_call_process_event_public_response_allowed"], False)

        forbidden_contract = set(decisions.get("forbidden_public_contract", []))
        self.assertTrue(
            {
                "public CallProcessEvent response path",
                "raw UE pointers",
                "raw ProcessEvent params",
                "raw FString storage",
                "FName/GObjects indices",
                "reply API",
                "send-chat API",
                "broadcast/notices API",
                "moderation API",
                "player lookup",
                "mutation",
                "return override",
            }.issubset(forbidden_contract)
        )

        requirements = decisions.get("required_before_public_header")
        self.assertIsInstance(requirements, list)
        requirement_ids = {item.get("id") for item in requirements if isinstance(item, dict)}
        self.assertTrue(
            {
                "dependency.promoted_player_identity",
                "dependency.promoted_permissions_admin",
                "abi.copied_response_payload",
                "abi.capability_and_owner_token",
                "lifecycle.owner_scoped_unregister_and_drain",
                "privacy.redaction_and_targeting",
                "abuse.rate_limit_and_audit",
                "separation.no_commands_router_or_moderation",
                "evidence.layout_runtime_sdk_coverage",
            }.issubset(requirement_ids)
        )

        evidence = {
            item["id"]: item
            for item in requirements
            if isinstance(item, dict)
        }["evidence.layout_runtime_sdk_coverage"]
        for insufficient in (
            "static thunk orientation",
            "candidate vtable slots",
            "passive ChatMessageEvent parsing",
            "legacy CallProcessEvent debug gate",
            "raw ProcessEvent callbacks",
        ):
            self.assertIn(insufficient, evidence["not_sufficient"])

    def test_public_sdk_surfaces_manifest_defines_v1_contract_without_claiming_completion(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "obelisk.public-sdk-surfaces.v1")
        self.assertEqual(manifest["sdk_version"], "v1.0")
        self.assertEqual(manifest["status"], "planning-contract")
        self.assertFalse(manifest["v1_completion_required"])
        self.assertEqual(manifest["public_header"], "include/obelisk/ObeliskApi.h")

        required_top_level = (
            "compatibility_statement",
            "stable_release_contract",
            "promoted_surfaces",
            "experimental_surfaces",
            "planning_surfaces",
            "v1_sdk_completion_blockers",
            "post_v1_or_excluded_surfaces",
            "debug_only_surfaces",
            "promotion_requirements",
            "release_guardrails",
        )
        for key in required_top_level:
            self.assertIn(key, manifest)

        serialized = json.dumps(manifest, sort_keys=True)
        self.assertNotIn("/servidor/ark", serialized)
        self.assertIn("v1.0 stable", manifest["compatibility_statement"])
        self.assertIn("complete public SDK contract", manifest["compatibility_statement"])
        self.assertIn("not a runtime/core-first RC", manifest["compatibility_statement"])

        stable_contract = manifest["stable_release_contract"]
        self.assertEqual(
            stable_contract["meaning"],
            "v1.0 stable is the complete public SDK contract for plugin authors.",
        )
        self.assertFalse(stable_contract["claim_allowed"])
        self.assertIn(
            "v1_completion_required is true in this manifest",
            stable_contract["claim_requires"],
        )
        self.assertIn(
            "every v1_sdk_completion_blocker is promoted or explicitly named as excluded/post-v1 in the v1 release statement",
            stable_contract["claim_requires"],
        )
        self.assertIn(
            "no promoted-experimental-only surface remains unresolved",
            stable_contract["claim_requires"],
        )
        for non_signal in (
            "runtime/core-first RC readiness",
            "internal runtime stability",
            "Foundation/Plugin Hub seed package shape",
            "GameplayPolicyEvent and ChatMessageEvent copied-data seeds",
        ):
            self.assertIn(non_signal, stable_contract["not_sufficient"])

    def test_public_sdk_surfaces_manifest_classifies_expected_surfaces(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        self.assertEqual(len(surfaces), len(manifest["surfaces"]))

        required_ids = {
            "obelisk.lifecycle_config_logging.v1",
            "obelisk.descriptors.v1",
            "obelisk.process_local_timers.v1",
            "obelisk.gameplay_policy_event.v1",
            "obelisk.chat_message.v1",
            "obelisk.chat.local_routing.v1",
            "obelisk.player_identity.v1",
            "obelisk.inventory_item_copied_signals.v1",
            "obelisk.inventory_items_mutation.v1",
            "obelisk.lifecycle_ops_recovery.v1",
            "obelisk.structure_census.v1",
            "obelisk.mission_transfer_dino_tribe.v1",
            "obelisk.player_services_economy_mobility.v1",
            "obelisk.commands_replies.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.arkapi_compatibility.v1",
            "obelisk.operator_ingress_storage.v1",
            "obelisk.gameplay_tick_callbacks.v1",
            "obelisk.debug_raw_process_event.v1",
        }
        self.assertTrue(required_ids.issubset(surfaces))

        allowed_statuses = set(manifest["status_values"])
        for surface in manifest["surfaces"]:
            with self.subTest(surface=surface["id"]):
                self.assertRegex(surface["id"], r"^obelisk\.[a-z0-9_.]+\.v1$")
                self.assertIn(surface["status"], allowed_statuses)

        promoted = set(manifest["promoted_surfaces"])
        experimental = set(manifest["experimental_surfaces"])
        planning = set(manifest["planning_surfaces"])
        post_or_excluded = set(manifest["post_v1_or_excluded_surfaces"])
        debug_only = set(manifest["debug_only_surfaces"])
        v1_blockers = set(manifest["v1_sdk_completion_blockers"])

        self.assertEqual(promoted, {
            surface["id"] for surface in manifest["surfaces"] if surface["status"] == "promoted"
        })
        self.assertEqual(experimental, {
            surface["id"]
            for surface in manifest["surfaces"]
            if surface["status"] == "promoted-experimental-only"
        })
        self.assertEqual(planning, {
            surface["id"] for surface in manifest["surfaces"] if surface["status"] == "planning"
        })
        self.assertEqual(post_or_excluded, {
            surface["id"]
            for surface in manifest["surfaces"]
            if surface["status"] in {"post-v1", "excluded"}
        })
        self.assertEqual(debug_only, {
            surface["id"] for surface in manifest["surfaces"] if surface["status"] == "debug-only"
        })

        for surface_id in promoted:
            self.assertEqual(surfaces[surface_id]["status"], "promoted")

        self.assertEqual(
            v1_blockers,
            {
                "obelisk.player_identity.v1",
                "obelisk.commands_replies.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.inventory_items_mutation.v1",
                "obelisk.lifecycle_ops_recovery.v1",
                "obelisk.structure_census.v1",
                "obelisk.mission_transfer_dino_tribe.v1",
                "obelisk.player_services_economy_mobility.v1",
                "obelisk.operator_ingress_storage.v1",
                "obelisk.gameplay_tick_callbacks.v1",
            },
        )
        self.assertTrue(v1_blockers.issubset(planning | post_or_excluded))
        release_guardrails = " ".join(manifest["release_guardrails"])
        self.assertIn(
            "A v1.0 stable claim must mean the complete public SDK contract for plugin authors, "
            "not runtime/core-first RC readiness or internal runtime stability alone.",
            release_guardrails,
        )
        self.assertIn(
            "stable_release_contract.claim_allowed must stay false while v1_completion_required is false.",
            release_guardrails,
        )
        self.assertIn(
            "Lifecycle/config/logging foundation does not satisfy lifecycle ops recovery demand; "
            "plugin watchdogs, hot reload, process restart orchestration, server recovery, "
            "operator reload commands, and restart-state semantics must be promoted separately "
            "or explicitly excluded/post-v1.",
            release_guardrails,
        )
        self.assertIn(
            "Umbrella blockers do not imply broad module coverage; dino, tribe, buff/status, "
            "chat send/broadcast, player progression/engrams, economy, mobility, and operator "
            "ingress/storage must each be promoted as narrow copied C ABI surfaces or explicitly "
            "excluded by name in the v1 release statement.",
            release_guardrails,
        )
        self.assertIn("Every v1_sdk_completion_blocker", release_guardrails)
        self.assertIn("before v1_completion_required can become true", release_guardrails)
        self.assertIn("Every promoted-experimental-only surface", release_guardrails)
        self.assertIn(
            "Plugin Hub seed docs and installed examples must not be used as v1 completion evidence.",
            release_guardrails,
        )

        non_public_statuses = {"planning", "post-v1", "excluded", "debug-only"}
        for surface in manifest["surfaces"]:
            if surface["status"] in non_public_statuses:
                with self.subTest(non_public_surface=surface["id"]):
                    self.assertEqual(surface.get("public_contract", []), [])

    def test_v1_sdk_completion_blockers_have_explicit_contract_outcome(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        post_or_excluded = set(manifest["post_v1_or_excluded_surfaces"])

        for surface_id in manifest["v1_sdk_completion_blockers"]:
            surface = surfaces[surface_id]
            status = surface["status"]
            with self.subTest(surface=surface_id, status=status):
                if status == "promoted":
                    self.assertTrue(surface.get("public_contract"))
                    self.assertTrue(surface.get("evidence"))
                    continue

                self.assertEqual(surface.get("public_contract", []), [])
                if status in {"post-v1", "excluded"}:
                    self.assertIn(surface_id, post_or_excluded)
                    if status == "post-v1":
                        self.assertTrue(surface.get("blockers"))
                    self.assertTrue(surface.get("exclusions"))
                    continue

                self.assertEqual(surface.get("support_tier"), "blocked")
                decision = surface.get("v1_decision_contract")
                self.assertIsInstance(decision, dict)
                self.assertEqual(
                    decision.get("current_decision"),
                    "blocked_until_promoted_or_explicitly_excluded",
                )
                self.assertTrue(decision.get("must_remain_without_public_contract_until_promotion"))
                self.assertTrue(decision.get("promotion_requires"))
                self.assertTrue(decision.get("exclusion_requires"))

    def test_public_sdk_lifecycle_surface_declares_init_scope_ownership(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        lifecycle = surfaces["obelisk.lifecycle_config_logging.v1"]
        compatibility = normalized(PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8"))

        self.assertEqual(lifecycle["status"], "promoted")
        self.assertEqual(
            lifecycle.get("ownership_contract"),
            [
                "ObeliskPluginMetadata string fields must remain valid until dlclose",
                "ObeliskApi pointer is borrowed for ObeliskPlugin_Init only",
                "ObeliskPluginInitContext string fields are borrowed for ObeliskPlugin_Init only",
                "plugins must copy API slots and context values needed by shutdown, worker threads, or later callbacks",
            ],
        )

        for term in (
            "Lifecycle ownership is part of the promoted foundation contract",
            "metadata string pointers must remain valid until the plugin shared object is closed",
            "`ObeliskApi*` and `ObeliskPluginInitContext` borrowed strings are init-scope only",
            "must copy those values into plugin-owned storage during init",
        ):
            self.assertIn(normalized(term), compatibility)

    def test_public_sdk_manifest_tracks_raw_process_event_slots_as_debug_only(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        debug_surface = surfaces["obelisk.debug_raw_process_event.v1"]
        compatibility = normalized(PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8"))

        self.assertEqual(debug_surface["status"], "debug-only")
        self.assertEqual(debug_surface.get("public_contract", []), [])
        self.assertNotIn("obelisk.debug_raw_process_event.v1", manifest["promoted_surfaces"])
        self.assertIn("obelisk.debug_raw_process_event.v1", manifest["debug_only_surfaces"])

        for slot in (
            "RegisterPreProcessEvent",
            "RegisterPostProcessEvent",
            "RegisterPreProcessEventForNameIndex",
            "RegisterPostProcessEventForNameIndex",
            "CallProcessEvent",
            "RegisterPreProcessEventWithOwnerToken",
            "RegisterPostProcessEventWithOwnerToken",
            "RegisterPreProcessEventForNameIndexWithOwnerToken",
            "RegisterPostProcessEventForNameIndexWithOwnerToken",
            "RegisterPreProcessEventWithOwnerTokenHandle",
            "RegisterPostProcessEventWithOwnerTokenHandle",
            "RegisterPreProcessEventForNameIndexWithOwnerTokenHandle",
            "RegisterPostProcessEventForNameIndexWithOwnerTokenHandle",
            "UnregisterProcessEventCallbackWithOwnerToken",
        ):
            with self.subTest(slot=slot):
                self.assertIn(slot, debug_surface["legacy_abi_slots"])
                self.assertIn(slot, V010_CORE_OBELISK_API_FIELD_ALLOWLIST)

        for capability in (
            "OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS",
            "OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS",
            "OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS",
            "OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES",
            "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT",
            "OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING",
        ):
            with self.subTest(capability=capability):
                self.assertIn(capability, debug_surface["capability_gates"])

        for guardrail in (
            "legacy slots remain append-only ABI compatibility entries only",
            "callbacks expose borrowed UE pointers and raw parameter buffers",
            "global and filtered callbacks require explicit debug env plus per-instance marker gates",
            "CallProcessEvent is limited to the plugin init debug window and must fail closed post-init",
            "no raw ProcessEvent slot may be used as v1 SDK completion evidence",
        ):
            with self.subTest(guardrail=guardrail):
                self.assertIn(guardrail, debug_surface["guardrails"])

        for doc_term in (
            "Legacy raw `ProcessEvent` ABI slots remain header compatibility entries only",
            "inventoried as `obelisk.debug_raw_process_event.v1`",
            "cannot count as promoted v1 SDK surface or completion evidence",
        ):
            self.assertIn(normalized(doc_term), compatibility)

    def test_pre_identity_plugin_hub_production_seeds_stay_limited_to_core_primitives(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        production_seed_ids = {
            "obelisk.lifecycle_config_logging.v1",
            "obelisk.descriptors.v1",
            "obelisk.process_local_timers.v1",
        }
        experimental_ids = {
            "obelisk.chat_message.v1",
            "obelisk.chat.local_routing.v1",
            "obelisk.gameplay_policy_event.v1",
            "obelisk.inventory_item_copied_signals.v1",
        }

        self.assertEqual(set(manifest["promoted_surfaces"]), production_seed_ids)
        self.assertEqual(
            {
                surface["id"]
                for surface in manifest["surfaces"]
                if surface.get("support_tier") == "release-supported seed"
            },
            production_seed_ids,
        )
        self.assertIn("obelisk.player_identity.v1", manifest["v1_sdk_completion_blockers"])
        self.assertNotIn("obelisk.player_identity.v1", manifest["promoted_surfaces"])
        for surface_id in production_seed_ids:
            with self.subTest(surface=surface_id):
                self.assertEqual(surfaces[surface_id]["status"], "promoted")
        for surface_id in experimental_ids:
            with self.subTest(surface=surface_id):
                self.assertEqual(surfaces[surface_id]["status"], "promoted-experimental-only")
                self.assertNotIn(surface_id, manifest["promoted_surfaces"])

        release_guardrails = normalized(" ".join(manifest["release_guardrails"]))
        for term in (
            "Installed-SDK foundation examples before identity/principal are limited to lifecycle/config/logging, descriptors, and process-local timers",
            "Plugin Hub seed/package publication remains post-SDK-complete, and neither these examples nor passive chat routing are enough for v1 completion",
            "passive chat parsing and plugin-local routing remain promoted-experimental-only",
            "GameplayPolicyEvent and ChatMessageEvent are copied-data seeds only; separately or together they must not be described as v1-complete, v1.0 stable, or sufficient to turn on v1_completion_required",
        ):
            self.assertIn(normalized(term), release_guardrails)

    def test_public_sdk_surfaces_manifest_keeps_descriptors_metadata_only_not_module_promotion(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        descriptors = surfaces["obelisk.descriptors.v1"]

        self.assertEqual(descriptors["category"], "metadata")
        self.assertEqual(descriptors["status"], "promoted")
        self.assertEqual(descriptors["support_tier"], "release-supported seed")
        self.assertEqual(
            descriptors["public_contract"],
            [
                "DescribeResourceKind",
                "DescribeGameplayPolicyEventKind",
                "ObeliskResourceKindDescriptor",
                "ObeliskGameplayPolicyEventDescriptor",
            ],
        )
        self.assertNotIn("obelisk.descriptors.v1", manifest["v1_sdk_completion_blockers"])
        for exclusion in (
            "resource identity",
            "object lookup",
            "persistent handles",
            "ResourceHandle",
            "cross-event correlation",
            "mutation",
            "return override",
        ):
            self.assertIn(exclusion, descriptors["exclusions"])

        descriptor_terms = (
            "obelisk.descriptors.v1",
            "DescribeResourceKind",
            "DescribeGameplayPolicyEventKind",
            "ObeliskResourceKindDescriptor",
            "ObeliskGameplayPolicyEventDescriptor",
            "descriptor_catalog_plugin.cpp",
            "oDescriptorCatalog",
        )
        module_blockers = (
            "obelisk.inventory_items_mutation.v1",
            "obelisk.structure_census.v1",
            "obelisk.mission_transfer_dino_tribe.v1",
        )
        for surface_id in module_blockers:
            surface_text = json.dumps(surfaces[surface_id], sort_keys=True)
            with self.subTest(surface=surface_id):
                self.assertEqual(surfaces[surface_id].get("public_contract", []), [])
                self.assertNotIn(surface_id, manifest["promoted_surfaces"])
                for term in descriptor_terms:
                    self.assertNotIn(term, surface_text)

    def test_public_sdk_surfaces_manifest_keeps_chat_and_gameplay_experimental_bounds(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}

        chat = surfaces["obelisk.chat_message.v1"]
        self.assertEqual(chat["status"], "promoted-experimental-only")
        for token in (
            "ObeliskChatMessageEvent",
            "RegisterChatMessageEventWithOwnerTokenHandle",
            "UnregisterChatMessageEventWithOwnerToken",
            "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            "chat-message-intake",
            "abi_version",
            "struct_size",
            "send_mode",
            "sequence",
            "message",
        ):
            self.assertIn(token, json.dumps(chat))
        for exclusion in (
            "public command SDK/router",
            "sender identity",
            "permissions",
            "replies",
            "send-chat",
            "mutation",
            "return override",
            "raw FString storage",
        ):
            self.assertIn(exclusion, chat["exclusions"])

        gameplay = surfaces["obelisk.gameplay_policy_event.v1"]
        self.assertEqual(gameplay["status"], "promoted-experimental-only")
        self.assertEqual(gameplay["evidence"]["manifest"], "docs/public_gameplay_events.json")
        for exclusion in (
            "Inventory SDK",
            "Items SDK",
            "StructureEvents SDK",
            "ResourceHandle",
            "mutation",
            "return override",
        ):
            self.assertIn(exclusion, gameplay["exclusions"])

        inventory_signals = surfaces["obelisk.inventory_item_copied_signals.v1"]
        self.assertEqual(inventory_signals["status"], "promoted-experimental-only")
        self.assertEqual(inventory_signals["depends_on"], ["obelisk.gameplay_policy_event.v1"])
        inventory_serialized = json.dumps(inventory_signals)
        for token in (
            "inventory.remote_add_check",
            "inventory.use_check",
            "inventory_item.allow_equip_check",
            "inventory_item.can_repair_check",
            "inventory_item.use_onto_item_check",
            "item-return-only-policy-slice",
        ):
            self.assertIn(token, inventory_serialized)
        for forbidden in (
            "inventory-action-compact-intake",
            "ServerRequestInventoryUseItem",
            "ServerRequestInventoryUseItemWithActor",
            "AdditionalData int32",
            "ItemId redacted_struct",
            "ItemID1 redacted_struct",
        ):
            self.assertNotIn(forbidden, inventory_serialized)
        public_contract_text = json.dumps(
            {
                surface["id"]: {
                    "public_contract": surface.get("public_contract", []),
                    "payload_contract": surface.get("payload_contract", []),
                }
                for surface in surfaces.values()
            },
            sort_keys=True,
        )
        for forbidden in (
            "ItemId",
            "ItemID1",
            "AdditionalData",
            "ServerRequestInventoryUseItem",
            "ServerRequestInventoryUseItemWithActor",
            "inventory-action-compact-intake",
        ):
            self.assertNotIn(forbidden, public_contract_text)
        for exclusion in (
            "Inventory SDK",
            "Items SDK",
            "item identity",
            "inventory identity",
            "lookup",
            "mutation",
            "return override",
            "ResourceHandle",
        ):
            self.assertIn(exclusion, inventory_signals["exclusions"])

        action_note = (
            REPO_ROOT / "docs" / "research" / "2026-05-29-inventory-action-redacted-signature-readiness.md"
        ).read_text(encoding="utf-8")
        for term in (
            "Fixture-Only Mutation Blocker Check",
            "--snapshot-root tests/fixtures/ufunction_snapshots",
            "`safety_summary.artifact_status=candidate_only`",
            "`safety_summary.promotion_ready=false`",
            "ItemId` stays\n  `redacted_struct`",
            "ItemID1` stays\n  `redacted_struct`",
            "AdditionalData` stays\n  an `int32` copied scalar candidate only",
            "no Inventory SDK, Items SDK, `ItemNetID` identity",
            "lookup, mutation, return override, raw params, public callback, runtime hook, or\n  `ResourceHandle`",
        ):
            with self.subTest(note="inventory-action-boundary", term=term):
                self.assertIn(term, action_note)

    def test_public_sdk_surfaces_manifest_keeps_player_identity_planning_only_blocked(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        player_identity = surfaces["obelisk.player_identity.v1"]

        self.assertEqual(player_identity["status"], "planning")
        self.assertEqual(player_identity["support_tier"], "blocked")
        self.assertEqual(player_identity["public_contract"], [])
        self.assertEqual(
            player_identity["evidence"]["target_set"],
            "players-identity-lifecycle-intake",
        )
        self.assertEqual(
            player_identity["evidence"]["requires"],
            [
                "non-protected complete obelisk.core-dump-evidence-pack.v1 manifest",
                "reviewed UFunction obelisk.reflection-inventory-pack.v1 manifest",
                "reflection inventory target_set_coverage for the full players-identity-lifecycle-intake target set",
                "reflection inventory containing ShooterPlayerController.ServerListPlayers and ShooterPlayerController.ServerKickPlayer",
            ],
        )
        for non_claim in (
            "offline ShooterGameServer binary alone is insufficient",
            "copied core or direct core/bin planning alone is insufficient",
            "manual FName/GObjects roots alone are insufficient",
            "private player-principal lifecycle observer wiring, marker/env-gated runtime observations, and internal lifecycle-anchor logs are promotion inputs only; they do not add public header symbols, plugin callback dispatch, player lookup, principal identifiers, permissions/admin, command/chat response, v1 SDK completion, or support-tier changes",
        ):
            self.assertIn(non_claim, player_identity["evidence"]["non_claims"])
        self.assertIn("obelisk.player_identity.v1", manifest["planning_surfaces"])
        self.assertNotIn("obelisk.player_identity.v1", manifest["promoted_surfaces"])
        self.assertNotIn("players-identity-lifecycle-intake", json.dumps(manifest["promoted_surfaces"]))
        self.assertNotIn("players-identity-lifecycle-intake", json.dumps(manifest["experimental_surfaces"]))

        for blocker in (
            "No approved runtime principal lifecycle evidence.",
            "No accepted login/logout lifecycle ordering or principal invalidation semantics.",
            "No principal privacy, invalidation, or cross-instance scope contract.",
        ):
            self.assertIn(blocker, player_identity["blockers"])

        for exclusion in (
            "player lookup",
            "permissions",
            "moderation",
            "economy identity",
            "send-chat identity",
        ):
            self.assertIn(exclusion, player_identity["exclusions"])

    def test_public_sdk_surfaces_manifest_keeps_commands_replies_blocked_on_identity_permissions_and_safe_response(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        commands = surfaces["obelisk.commands_replies.v1"]

        self.assertEqual(commands["status"], "post-v1")
        self.assertEqual(commands["support_tier"], "blocked")
        self.assertEqual(commands["public_contract"], [])
        self.assertEqual(
            commands["depends_on"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ],
        )
        self.assertIn("obelisk.commands_replies.v1", manifest["v1_sdk_completion_blockers"])
        self.assertIn("obelisk.commands_replies.v1", manifest["post_v1_or_excluded_surfaces"])
        self.assertNotIn("obelisk.commands_replies.v1", manifest["promoted_surfaces"])

        for blocker in (
            "Needs promoted player identity/principal semantics.",
            "Needs promoted permission/authority model.",
            "Needs obelisk.command_chat_response_path.v1 promoted before replies/send-chat can be claimed; this blocker must be promoted or explicitly excluded/post-v1 before v1_completion_required can change.",
            "Send-chat, broadcast, scheduled notices, and moderation are separate response/authority surfaces, not implied by passive copied chat parsing.",
            "Needs command lifecycle and abuse boundaries.",
        ):
            self.assertIn(blocker, commands["blockers"])

        for audit_unit in (
            "command router",
            "replies/send-chat",
            "broadcast/notices",
            "moderation/admin command authority",
        ):
            self.assertIn(audit_unit, commands["audit_units"])

        for exclusion in (
            "public command SDK/router",
            "admin command API",
            "player command API",
            "chat replies",
            "send-chat",
            "broadcast/notices API",
            "moderation",
        ):
            self.assertIn(exclusion, commands["exclusions"])

    def test_public_sdk_surfaces_manifest_keeps_permissions_admin_query_only_after_identity(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        permissions = surfaces["obelisk.permissions_admin.v1"]

        self.assertEqual(permissions["status"], "post-v1")
        self.assertEqual(permissions["support_tier"], "blocked")
        self.assertEqual(permissions["public_contract"], [])
        self.assertEqual(permissions["depends_on"], ["obelisk.player_identity.v1"])

        for blocker in (
            "No promoted player identity or authority model.",
            "First public slice must be query-only permission checks over a copied principal, not groups/grants/admin actions.",
            "No fail-closed policy source, abuse controls, owner-token/capability/struct_size ABI tests, or SDK consumer coverage.",
        ):
            self.assertIn(blocker, permissions["blockers"])

        promotion_requires = " ".join(permissions["v1_decision_contract"]["promotion_requires"])
        for term in (
            "principal_generation",
            "principal_scope_flags",
            "stale principal",
            "scope mismatch",
            "query-only fail-closed permission checks",
        ):
            self.assertIn(term, promotion_requires)

        self.assertIn(
            "candidate-only permissions/admin query fail-closed contract",
            permissions["v1_decision_contract"]["not_sufficient_evidence"],
        )
        release_guardrails = " ".join(manifest["release_guardrails"])
        self.assertIn(
            "obelisk.permissions-admin-query-failclosed-contract.v1 is a candidate-only pre-ABI permissions/admin artifact; "
            "consume-mode acceptance is not public permissions/admin ABI, public SDK readiness, runtime readiness, or v1 SDK completion evidence.",
            release_guardrails,
        )

        for exclusion in (
            "permission groups",
            "admin groups",
            "grant/revoke API",
            "storage/persistence",
            "operator ingress",
            "command router",
            "replies/send-chat",
            "moderation authority",
            "ban/kick API",
        ):
            self.assertIn(exclusion, permissions["exclusions"])

    def test_public_sdk_surfaces_manifest_keeps_command_chat_response_path_post_v1(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        response = surfaces["obelisk.command_chat_response_path.v1"]
        commands = surfaces["obelisk.commands_replies.v1"]

        self.assertEqual(response["status"], "post-v1")
        self.assertEqual(response["support_tier"], "blocked")
        self.assertFalse(response["public_abi"])
        self.assertFalse(response["adds_obelisk_api"])
        self.assertEqual(response["public_contract"], [])
        self.assertIn("obelisk.command_chat_response_path.v1", manifest["post_v1_or_excluded_surfaces"])
        self.assertNotIn("obelisk.command_chat_response_path.v1", manifest["promoted_surfaces"])
        self.assertIn("obelisk.command_chat_response_path.v1", commands["depends_on"])
        self.assertEqual(
            response["v1_decision_contract"]["decision_manifest"],
            "docs/command_chat_response_public_contract_decisions.json",
        )

        response_text = json.dumps(response, sort_keys=True)
        for term in (
            "no public CallProcessEvent path",
            "no raw UE pointers",
            "raw ProcessEvent params",
            "raw FString storage",
            "No reply, send-chat, broadcast/notices, or moderation API is available until this surface is separately promoted.",
            "named capability bit",
            "nonzero plugin_owner_token",
            "owner-token handles",
            "plugin-owner cleanup",
            "privacy",
        ):
            self.assertIn(term, response_text)

        for exclusion in (
            "public CallProcessEvent path",
            "raw UE pointers",
            "raw ProcessEvent params",
            "raw FString storage",
            "chat reply API",
            "send-chat API",
            "broadcast/notices API",
            "moderation API",
        ):
            self.assertIn(exclusion, response["exclusions"])

    def test_public_header_does_not_expose_blocked_v1_sdk_surface_tokens(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}

        for surface_id in (
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
            "obelisk.inventory_items_mutation.v1",
        ):
            with self.subTest(surface=surface_id):
                self.assertIn(surfaces[surface_id]["status"], {"post-v1", "planning", "excluded"})
                self.assertEqual(surfaces[surface_id].get("public_contract", []), [])

        forbidden_public_header_tokens = (
            "OBELISK_API_CAPABILITY_PERMISSION_CHECKS",
            "OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN",
            "OBELISK_API_CAPABILITY_COMMANDS",
            "OBELISK_API_CAPABILITY_COMMAND_REPLIES",
            "OBELISK_API_CAPABILITY_CHAT_RESPONSES",
            "OBELISK_API_CAPABILITY_INVENTORY_MUTATION",
            "OBELISK_API_CAPABILITY_ITEM_MUTATION",
            "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
            "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE",
            "ObeliskPermissionQuery",
            "ObeliskPermissionDecision",
            "ObeliskCommand",
            "ObeliskCommandContext",
            "ObeliskCommandReply",
            "ObeliskChatResponse",
            "ObeliskInventoryMutation",
            "ObeliskItemMutation",
            "ObeliskPlayerPrincipalLifecycleEvent",
            "RegisterCommand",
            "RegisterPlayerPrincipalLifecycleEvent",
            "UnregisterCommand",
            "UnregisterPlayerPrincipalLifecycleEvent",
            "ReplyToCommand",
            "SendChat",
            "GrantPermission",
            "RevokePermission",
            "GiveItem",
            "RemoveItem",
            "SetItemQuantity",
            *UNPROMOTED_CHAT_COMMAND_RESPONSE_API_TOKENS,
        )
        for token in forbidden_public_header_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, header)

    def test_public_sdk_surfaces_manifest_keeps_inventory_items_mutation_blocked_until_identity_promotion(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        inventory = surfaces["obelisk.inventory_items_mutation.v1"]

        self.assertEqual(inventory["status"], "post-v1")
        self.assertEqual(inventory["support_tier"], "blocked")
        self.assertEqual(inventory["public_contract"], [])
        self.assertIn("obelisk.inventory_items_mutation.v1", manifest["v1_sdk_completion_blockers"])
        self.assertIn("obelisk.inventory_items_mutation.v1", manifest["post_v1_or_excluded_surfaces"])
        self.assertNotIn("obelisk.inventory_items_mutation.v1", manifest["promoted_surfaces"])

        decision = inventory["v1_decision_contract"]
        self.assertEqual(
            decision["current_decision"],
            "blocked_until_promoted_or_explicitly_excluded",
        )
        self.assertTrue(decision["must_remain_without_public_contract_until_promotion"])
        promotion_requires = " ".join(decision["promotion_requires"])
        for term in (
            "promoted player, inventory, and item identity semantics needed by that unit",
            "rollback, privacy, and abuse controls for grants/removals/progression",
            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
        ):
            self.assertIn(term, promotion_requires)

        exclusion_requires = " ".join(decision["exclusion_requires"])
        self.assertIn(
            "no Inventory SDK, Items SDK, give item API, remove item API, kits/rewards API, "
            "engram/progression API, inventory lookup, item handles, item mutation, return "
            "override, or ResourceHandle API is included in v1",
            exclusion_requires,
        )

        for blocker in (
            "No item/inventory identity.",
            "No lookup or mutation contract.",
            "No rollback/privacy policy for item grants or removals.",
            "No player progression, engram unlock, kit grant, or item reward contract.",
        ):
            self.assertIn(blocker, inventory["blockers"])

        for exclusion in (
            "Inventory SDK",
            "Items SDK",
            "give item",
            "remove item",
            "kits/rewards",
            "engram/progression API",
            "inventory lookup",
            "item handles",
            "item mutation",
            "return override",
            "ResourceHandle",
        ):
            self.assertIn(exclusion, inventory["exclusions"])

    def test_inventory_copied_signals_cannot_stand_in_for_inventory_sdk_or_identity_completion(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        copied_signals = surfaces["obelisk.inventory_item_copied_signals.v1"]
        inventory_mutation = surfaces["obelisk.inventory_items_mutation.v1"]
        player_identity = surfaces["obelisk.player_identity.v1"]
        compatibility = normalized(PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8"))

        self.assertFalse(manifest["v1_completion_required"])
        self.assertEqual(copied_signals["status"], "promoted-experimental-only")
        self.assertEqual(copied_signals["support_tier"], "experimental Plugin Hub seed")
        self.assertIn(copied_signals["id"], manifest["experimental_surfaces"])
        self.assertNotIn(copied_signals["id"], manifest["promoted_surfaces"])
        self.assertNotIn(copied_signals["id"], manifest["v1_sdk_completion_blockers"])

        copied_signal_contract = normalized(
            json.dumps(
                {
                    "public_contract": copied_signals.get("public_contract", []),
                    "payload_contract": copied_signals.get("payload_contract", []),
                },
                sort_keys=True,
            )
        )
        for forbidden in (
            "Inventory SDK",
            "Items SDK",
            "item identity",
            "inventory identity",
            "ItemNetID identity",
            "lookup",
            "mutation",
            "return override",
            "ResourceHandle",
            "grant/remove",
        ):
            with self.subTest(scope="copied signal contract", forbidden=forbidden):
                self.assertNotIn(normalized(forbidden), copied_signal_contract)

        for required_exclusion in (
            "Inventory SDK",
            "Items SDK",
            "item identity",
            "inventory identity",
            "ItemNetID identity",
            "lookup",
            "mutation",
            "return override",
            "ResourceHandle",
        ):
            with self.subTest(scope="copied signal exclusions", exclusion=required_exclusion):
                self.assertIn(required_exclusion, copied_signals["exclusions"])

        self.assertEqual(inventory_mutation["status"], "post-v1")
        self.assertEqual(inventory_mutation["public_contract"], [])
        self.assertIn(inventory_mutation["id"], manifest["v1_sdk_completion_blockers"])
        self.assertIn(inventory_mutation["id"], manifest["post_v1_or_excluded_surfaces"])
        self.assertNotIn(inventory_mutation["id"], manifest["promoted_surfaces"])
        self.assertEqual(player_identity["status"], "planning")
        self.assertIn(player_identity["id"], manifest["v1_sdk_completion_blockers"])
        self.assertNotIn(player_identity["id"], manifest["promoted_surfaces"])

        for doc_phrase in (
            "It is not an\nInventory SDK, Items SDK, StructureEvents SDK, identity API, lookup API, mutation API, or\nreturn-override API",
            "These remain post-original copied signals,\nnot item identity, inventory lookup, mutation, `ResourceHandle`, rollback, or grant/remove\nauthority",
        ):
            with self.subTest(scope="compatibility doc", phrase=doc_phrase):
                self.assertIn(normalized(doc_phrase), compatibility)

    def test_public_sdk_surfaces_manifest_names_high_demand_umbrella_audit_units(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        gameplay = surfaces["obelisk.mission_transfer_dino_tribe.v1"]
        inventory = surfaces["obelisk.inventory_items_mutation.v1"]
        services = surfaces["obelisk.player_services_economy_mobility.v1"]
        ticks = surfaces["obelisk.gameplay_tick_callbacks.v1"]
        commands = surfaces["obelisk.commands_replies.v1"]
        timers = surfaces["obelisk.process_local_timers.v1"]

        for audit_unit in (
            "dino policy/cosmetics/carry restrictions",
            "tribe identity/notices/policy",
            "buff/status policy",
        ):
            self.assertIn(audit_unit, gameplay["audit_units"])

        for exclusion in ("Dino SDK", "Tribe SDK", "Buff/status SDK"):
            self.assertIn(exclusion, gameplay["exclusions"])

        for audit_unit in (
            "inventory/item lookup",
            "item grant/remove mutation",
            "kits/rewards",
            "player progression/engrams",
        ):
            self.assertIn(audit_unit, inventory["audit_units"])

        for exclusion in ("kits/rewards", "engram/progression API"):
            self.assertIn(exclusion, inventory["exclusions"])

        for audit_unit in (
            "economy/shops/rewards/kits/stats",
            "mobility/homes/teleport",
            "safe-zone/area policy",
            "broadcast/timed notices",
        ):
            self.assertIn(audit_unit, services["audit_units"])

        self.assertIn("obelisk.gameplay_tick_callbacks.v1", manifest["v1_sdk_completion_blockers"])
        self.assertIn("obelisk.gameplay_tick_callbacks.v1", manifest["post_v1_or_excluded_surfaces"])
        self.assertEqual(ticks["status"], "post-v1")
        self.assertEqual(ticks["public_contract"], [])
        for blocker in (
            "Process-local timers are not server tick, UE gameplay tick, or module tick callbacks.",
            "No tick cadence, budget, threading, hitch/backpressure, lifecycle, or shutdown contract.",
        ):
            self.assertIn(blocker, ticks["blockers"])
        for exclusion in (
            "server tick callbacks",
            "UE gameplay tick callbacks",
            "module tick callbacks",
            "per-frame hook callbacks",
        ):
            self.assertIn(exclusion, timers["exclusions"])
        for audit_unit in ("console command routing", "RCON command routing"):
            self.assertIn(audit_unit, commands["audit_units"])
        for exclusion in ("console command API", "RCON command API"):
            self.assertIn(exclusion, commands["exclusions"])

    def test_sdk_v1_compatibility_doc_tracks_manifest_and_exclusions(self) -> None:
        text = PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8")
        compact = normalized(text)
        required_terms = (
            "public_sdk_surfaces.json",
            "`v1.0 stable` must mean for plugin authors",
            "the complete public SDK contract",
            "not a runtime/core-first RC",
            "not just proof that the internal runtime is stable",
            "v1.0",
            "SDK contract",
            "v1_sdk_completion_blockers",
            "`stable_release_contract.claim_allowed` field",
            "machine-readable release switch",
            "must remain `false` while\n`v1_completion_required` is `false`",
            "installed SDK package shape",
            "player identity, permissions/admin,\ncommand/chat response path, commands/replies",
            "before `v1_completion_required` can become true",
            "Plugin Hub seed/package publication remains post-SDK-complete",
            "No Foundation/Plugin Hub seed, descriptor/timer example, installed SDK package shape, or\ncopied event example is an ArkApi/AseApi/ArkServerApi compatibility layer",
            "API parity\nclaim, portable plugin path, or evidence that ArkApi plugin families can be ported",
            "structure census/build policy",
            "gameplay modules including buffs",
            "Gameplay/server tick callbacks",
            "player services/economy/mobility/areas",
            "process-local timers",
            "Experimental Copied Event Patterns",
            "promoted-experimental-only",
            "must be promoted, downgraded to planning/post-v1, or explicitly excluded",
            "GameplayPolicyEvent",
            "ChatMessageEvent",
            "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            "principal=unknown",
            "Commands/replies is a blocked v1 completion surface",
            "depends on a promoted player identity/principal contract",
            "a promoted permission/authority model",
            "blocked `obelisk.command_chat_response_path.v1` planning dependency",
            "The command/chat response path is a named planning dependency only, not a promoted\nsurface",
            "no public `CallProcessEvent`\nresponse path",
            "raw `ProcessEvent` parameter response API",
            "reply API, send-chat API, broadcast/notices API, or\nmoderation API",
            "Inventory SDK",
            "StructureEvents SDK",
            "ResourceHandle",
            "buff module SDKs",
            "economy, shops, rewards, kits, stats, player progression/engrams, homes, teleport, safe zones, area policy",
            "gameplay/server tick callbacks",
            "console/RCON command routing",
            "chat send/broadcast",
            "dino policy/cosmetics/carry restrictions",
            "tribe identity/notices/policy",
            "buff/status",
            "command router, replies/send-chat, broadcast/notices",
            "inventory/item lookup, item grants/removal, kits/rewards, and player progression/engrams",
            "Umbrella names do not imply coverage",
            "operator ingress/storage each need a\nnarrow copied C ABI surface or an explicit named exclusion",
            "ArkApi",
            "post-v1",
            "Player identity is planning-only",
            "obelisk.players-identity-first-evidence.v1",
            "candidate-only",
            "consume-only/promote-blocked",
            "not public SDK or runtime readiness",
            "admin-mutation-not-public-identity",
            "`ServerListPlayers` and `ServerKickPlayer` snapshots",
            "reviewed non-protected complete `obelisk.core-dump-evidence-pack.v1`",
            "reviewed UFunction\n`obelisk.reflection-inventory-pack.v1`",
            "An offline\n`ShooterGameServer` binary, copied core, manual FName/GObjects roots, or direct\ncore/bin planning alone is insufficient",
            "accepted lifecycle anchors",
            "principal privacy/invalidation semantics",
            "independent second-source evidence",
            "Promote the smallest copied `player_identity`/principal lifecycle contract",
            "Build a fail-closed permissions/admin query layer",
            "Promote the command/chat response path, then promote commands/replies as a new\n   owner-token copied callback/response surface",
            "not as a parser-only extension to `ChatMessageEvent`",
            "preventing them from being mistaken for a complete Obelisk SDK",
            "## v1 Release Statement Checklist",
            "must have exactly one outcome record for every unresolved `.v1` blocker",
            "surface-id: promoted -",
            "surface-id: excluded -",
            "surface-id: post-v1 -",
            "Duplicate records, mixed `promoted`/`excluded`/`post-v1` records for the same surface",
            "surface-specific ABI evidence",
            "SDK-consumer evidence",
            "`obelisk.player_identity.v1`",
            "`obelisk.operator_ingress_storage.v1`",
            "`obelisk.gameplay_tick_callbacks.v1`",
            "`obelisk.lifecycle_ops_recovery.v1`",
            "Lifecycle ops recovery is tracked as `obelisk.lifecycle_ops_recovery.v1`",
            "plugin watchdogs, hot plugin reload, Obelisk hot reload, process restart, server recovery API, operator reload commands, detached-worker ingress, and restart-state recovery are excluded or post-v1",
            "Passing runtime/core-first RC gates",
            "pre-identity installed-SDK foundation usefulness is insufficient for `v1.0 stable`",
            "blocker list is promoted or explicitly named as excluded/post-v1",
            "mutation",
            "return override",
        )
        for term in required_terms:
            self.assertIn(normalized(term), compact)
        self.assertNotIn("promoted-minimal", text)

    def test_handoff_resume_docs_do_not_redefine_v1_as_runtime_core(self) -> None:
        paths = (
            REPO_ROOT / "docs" / "agent-handoff" / "COMPACT_CONTEXT.md",
            REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md",
            PUBLIC_SDK_V1_COMPATIBILITY_DOC,
            REPO_ROOT / "README.md",
            REPO_ROOT / "CHANGELOG.md",
        )
        forbidden_re = re.compile(r"v1\.0[^\n.]{0,80}production core|production core[^\n.]{0,80}v1\.0", re.IGNORECASE)

        for path in paths:
            text = path.read_text(encoding="utf-8")
            compact = normalized(text)
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix(), check="forbidden-core-claim"):
                self.assertIsNone(forbidden_re.search(text))
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix(), check="sdk-complete-wording"):
                self.assertRegex(compact, r"v1\.0|v1")
                self.assertRegex(compact.lower(), r"complete sdk|sdk completo|sdk contract|complete, documented sdk")

    def test_public_sdk_v1_completion_blocks_unresolved_experimental_surfaces(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        release_guardrails = " ".join(manifest["release_guardrails"])
        experimental = set(manifest["experimental_surfaces"])

        self.assertTrue(experimental)
        self.assertFalse(manifest["v1_completion_required"])
        self.assertIn(
            "Every promoted-experimental-only surface must be promoted, downgraded to planning/post-v1, "
            "or explicitly excluded before v1_completion_required can become true.",
            release_guardrails,
        )
        self.assertIn("promoted, downgraded to planning/post-v1, or explicitly excluded", PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(
            encoding="utf-8"
        ))

    def test_public_sdk_v1_completion_stays_false_while_command_dependency_chain_is_blocked(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        identity_note = (
            REPO_ROOT / "docs" / "research" / "2026-05-31-player-identity-first-evidence.md"
        ).read_text(encoding="utf-8")
        critical_chain = (
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        )
        blocker_order = manifest["v1_sdk_completion_blockers"]
        unresolved_statuses = {"planning", "post-v1", "promoted-experimental-only", "debug-only"}
        unresolved = [
            surface_id
            for surface_id in critical_chain
            if surfaces[surface_id]["status"] in unresolved_statuses
            or surfaces[surface_id].get("support_tier") == "blocked"
        ]

        self.assertEqual(
            surfaces["obelisk.commands_replies.v1"]["depends_on"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ],
        )
        self.assertEqual(
            surfaces["obelisk.permissions_admin.v1"]["depends_on"],
            ["obelisk.player_identity.v1"],
        )
        self.assertTrue(unresolved)
        self.assertTrue(set(unresolved).issubset(set(manifest["v1_sdk_completion_blockers"])))
        self.assertLess(
            blocker_order.index("obelisk.player_identity.v1"),
            blocker_order.index("obelisk.permissions_admin.v1"),
        )
        self.assertLess(
            blocker_order.index("obelisk.permissions_admin.v1"),
            blocker_order.index("obelisk.command_chat_response_path.v1"),
        )
        self.assertLess(
            blocker_order.index("obelisk.command_chat_response_path.v1"),
            blocker_order.index("obelisk.commands_replies.v1"),
        )
        self.assertFalse(
            manifest["v1_completion_required"],
            "v1 completion cannot be claimed while the command dependency chain is blocked",
        )

        release_guardrails = " ".join(manifest["release_guardrails"])
        for term in (
            "Identity/principal, permissions/admin, command/chat response path, and commands/replies are an ordered v1 dependency chain",
            "if any of those surfaces remains blocked, planning, or post-v1",
            "v1_completion_required must stay false",
            "must not be documented as permissions/admin being the immediate next public slice",
            "groups, grants, admin actions, and mutation authority remain excluded",
        ):
            self.assertIn(term, release_guardrails)

        self.assertIn(
            "Only after identity exists can a permission/admin service be designed on a real\n"
            "   principal.",
            identity_note,
        )
        self.assertIn(
            "Only after identity, permissions, and `obelisk.command_chat_response_path.v1` exist\n"
            "   can command routing with replies be designed.",
            identity_note,
        )
        self.assertNotIn(
            "Only after identity plus command routing exists can a permission service be designed.",
            identity_note,
        )

        compatibility = normalized(PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8"))
        for term in (
            "Identity/principal, permissions/admin, command/chat response path, and commands/replies are an ordered v1 dependency chain",
            "if any of those surfaces remains blocked, planning, or post-v1",
            "no complete v1 SDK claim is valid",
            "The completion checker must also reject any promoted permissions/admin,\ncommand/chat response path, or commands/replies surface whose dependency rows are not\nalready promoted",
            "not a declaration that permissions/admin is the immediate next public slice",
            "groups, grants, admin actions, and mutation authority remain excluded",
            "The command/chat response path is a named planning dependency only, not a promoted surface",
        ):
            self.assertIn(normalized(term), compatibility)

    def test_public_sdk_v1_completion_checker_rejects_promoted_commands_before_dependencies(self) -> None:
        checker = runpy.run_path(
            str(REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"),
            run_name="__not_main__",
        )
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.commands_replies.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["synthetic command router contract"]
                surface["evidence"] = {
                    "surface_id": "obelisk.commands_replies.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/CommandsRepliesTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/commands_replies_plugin.cpp"],
                }
                break

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = checker["build_report"](manifest_path)

        self.assertIn("promoted_surface_dependency_unresolved", report["blockers"])
        self.assertEqual(
            report["promoted_surfaces_with_unresolved_dependencies"]["obelisk.commands_replies.v1"],
            [
                "obelisk.command_chat_response_path.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
            ],
        )

    def test_public_sdk_v1_completion_checker_rejects_commands_when_response_dependency_absent(self) -> None:
        checker = runpy.run_path(
            str(REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"),
            run_name="__not_main__",
        )
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.commands_replies.v1":
                surface["status"] = "promoted"
                surface["depends_on"] = [
                    "obelisk.player_identity.v1",
                    "obelisk.permissions_admin.v1",
                ]
                surface["public_contract"] = ["synthetic command router contract"]
                surface["evidence"] = {
                    "surface_id": "obelisk.commands_replies.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/CommandsRepliesTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/commands_replies_plugin.cpp"],
                }
            elif surface["id"] in {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}:
                surface["status"] = "promoted"
                surface["public_contract"] = [f"synthetic {surface['id']} contract"]
                surface["evidence"] = {
                    "surface_id": surface["id"],
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/SyntheticDependencyTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/synthetic_dependency_plugin.cpp"],
                    "notes": (
                        "obelisk.core-dump-evidence-pack.v1 and "
                        "obelisk.reflection-inventory-pack.v1 accepted for "
                        "ServerListPlayers and ServerKickPlayer"
                    ),
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = checker["build_report"](manifest_path)

        self.assertFalse(report["ready"])
        self.assertIn("promoted_surface_dependency_unresolved", report["blockers"])
        self.assertIn(
            "obelisk.command_chat_response_path.v1",
            report["promoted_surfaces_with_unresolved_dependencies"]["obelisk.commands_replies.v1"],
        )

    def test_public_sdk_v1_completion_checker_rejects_commands_when_response_dependency_not_promoted(self) -> None:
        checker = runpy.run_path(
            str(REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"),
            run_name="__not_main__",
        )
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.commands_replies.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["synthetic command router contract"]
                surface["evidence"] = {
                    "surface_id": "obelisk.commands_replies.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/CommandsRepliesTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/commands_replies_plugin.cpp"],
                }
            elif surface["id"] in {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}:
                surface["status"] = "promoted"
                surface["public_contract"] = [f"synthetic {surface['id']} contract"]
                surface["evidence"] = {
                    "surface_id": surface["id"],
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/SyntheticDependencyTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/synthetic_dependency_plugin.cpp"],
                    "notes": (
                        "obelisk.core-dump-evidence-pack.v1 and "
                        "obelisk.reflection-inventory-pack.v1 accepted for "
                        "ServerListPlayers and ServerKickPlayer"
                    ),
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = checker["build_report"](manifest_path)

        self.assertFalse(report["ready"])
        self.assertIn("promoted_surface_dependency_unresolved", report["blockers"])
        self.assertIn(
            "obelisk.command_chat_response_path.v1",
            report["promoted_surfaces_with_unresolved_dependencies"]["obelisk.commands_replies.v1"],
        )

    def test_public_sdk_v1_completion_checker_rejects_response_path_before_dependencies(self) -> None:
        checker = runpy.run_path(
            str(REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"),
            run_name="__not_main__",
        )
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.command_chat_response_path.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["synthetic copied response contract"]
                surface["evidence"] = {
                    "surface_id": "obelisk.command_chat_response_path.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/CommandChatResponsePathTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/command_chat_response_path_plugin.cpp"],
                }
                break

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = checker["build_report"](manifest_path)

        self.assertFalse(report["ready"])
        self.assertIn("promoted_surface_dependency_unresolved", report["blockers"])
        self.assertEqual(
            report["promoted_surfaces_with_unresolved_dependencies"][
                "obelisk.command_chat_response_path.v1"
            ],
            [
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
            ],
        )

    def test_public_sdk_docs_do_not_imply_command_chat_response_path_promotion(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        self.assertEqual(surfaces["obelisk.command_chat_response_path.v1"]["status"], "post-v1")

        scan_text = "\n".join(
            [
                PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8"),
                json.dumps(manifest, indent=2, sort_keys=True),
            ]
        )
        self.assertIn(
            normalized("The command/chat response path is a named planning dependency only, not a promoted surface."),
            normalized(scan_text),
        )
        forbidden = re.compile(
            r"\b(?:promoted|available|included|supported)\s+"
            r"(?:obelisk\.command_chat_response_path\.v1|command/chat response path)\b|"
            r"\b(?:obelisk\.command_chat_response_path\.v1|command/chat response path)\s+"
            r"(?:is|are|as|becomes?)\s+(?:promoted|available|included|supported)\b",
            re.IGNORECASE,
        )
        offenders = [
            normalized(line)
            for line in scan_text.splitlines()
            if forbidden.search(line)
            and "not a promoted surface" not in line
            and "is included in v1" not in line
        ]
        self.assertEqual(offenders, [])

    def test_public_sdk_v1_completion_checker_rejects_promoted_permissions_before_identity(self) -> None:
        checker = runpy.run_path(
            str(REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"),
            run_name="__not_main__",
        )
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.permissions_admin.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["synthetic fail-closed permissions query contract"]
                surface["evidence"] = {
                    "surface_id": "obelisk.permissions_admin.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/PermissionsAdminTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/permissions_admin_plugin.cpp"],
                }
                break

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = checker["build_report"](manifest_path)

        self.assertIn("promoted_surface_dependency_unresolved", report["blockers"])
        self.assertEqual(
            report["promoted_surfaces_with_unresolved_dependencies"]["obelisk.permissions_admin.v1"],
            ["obelisk.player_identity.v1"],
        )

    def test_public_sdk_v1_completion_checker_requires_identity_core_reflection_evidence(self) -> None:
        checker = runpy.run_path(
            str(REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"),
            run_name="__not_main__",
        )
        missing_terms = checker["surface_missing_required_promotion_evidence"](
            {
                "id": "obelisk.player_identity.v1",
                "status": "promoted",
                "evidence": {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/PlayerIdentityTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_plugin.cpp"],
                },
            }
        )

        self.assertEqual(
            missing_terms,
            [
                "obelisk.core-dump-evidence-pack.v1",
                "obelisk.reflection-inventory-pack.v1",
                "ServerListPlayers",
                "ServerKickPlayer",
                "approved runtime principal lifecycle evidence",
                "accepted login/logout lifecycle ordering and principal invalidation semantics",
                "principal privacy, invalidation, and cross-instance semantics",
                "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
            ],
        )

        planning_only_terms = checker["surface_missing_required_promotion_evidence"](
            {
                "id": "obelisk.player_identity.v1",
                "status": "promoted",
                "evidence": {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/PlayerIdentityTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_plugin.cpp"],
                    "requires": [
                        "non-protected complete obelisk.core-dump-evidence-pack.v1 manifest",
                        "reviewed UFunction obelisk.reflection-inventory-pack.v1 manifest",
                        "reflection inventory containing ServerListPlayers and ServerKickPlayer",
                    ],
                    "non_claims": [
                        "ServerListPlayers and ServerKickPlayer are not accepted promotion evidence yet",
                    ],
                },
            }
        )

        self.assertEqual(
            planning_only_terms,
            [
                "obelisk.core-dump-evidence-pack.v1",
                "obelisk.reflection-inventory-pack.v1",
                "ServerListPlayers",
                "ServerKickPlayer",
                "approved runtime principal lifecycle evidence",
                "accepted login/logout lifecycle ordering and principal invalidation semantics",
                "principal privacy, invalidation, and cross-instance semantics",
                "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
            ],
        )

        negated_positive_field_terms = checker["surface_missing_required_promotion_evidence"](
            {
                "id": "obelisk.player_identity.v1",
                "status": "promoted",
                "evidence": {
                    "core_pack": "missing obelisk.core-dump-evidence-pack.v1",
                    "reflection_pack": "obelisk.reflection-inventory-pack.v1 is not reviewed",
                    "targets": [
                        "ServerListPlayers is still unresolved",
                        "ServerKickPlayer needs validation",
                    ],
                },
            }
        )

        self.assertEqual(
            negated_positive_field_terms,
            [
                "obelisk.core-dump-evidence-pack.v1",
                "obelisk.reflection-inventory-pack.v1",
                "ServerListPlayers",
                "ServerKickPlayer",
                "approved runtime principal lifecycle evidence",
                "accepted login/logout lifecycle ordering and principal invalidation semantics",
                "principal privacy, invalidation, and cross-instance semantics",
                "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
            ],
        )

        complete_terms = checker["surface_missing_required_promotion_evidence"](
            {
                "id": "obelisk.player_identity.v1",
                "status": "promoted",
                "evidence": {
                    "core_pack": "accepted non-protected obelisk.core-dump-evidence-pack.v1",
                    "reflection_pack": "reviewed obelisk.reflection-inventory-pack.v1",
                    "targets": [
                        "ShooterPlayerController.ServerListPlayers",
                        "ShooterPlayerController.ServerKickPlayer",
                    ],
                    "runtime_evidence": "approved runtime principal lifecycle evidence",
                    "lifecycle_ordering": "accepted login/logout lifecycle ordering and principal invalidation semantics",
                    "privacy_scope": "principal privacy, invalidation, and cross-instance semantics",
                    "abi_contract": "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                },
            }
        )

        self.assertEqual(complete_terms, [])

    def test_public_docs_record_player_identity_pack_gate_without_direct_core_shortcut(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        release_guardrails = normalized(" ".join(manifest["release_guardrails"]))
        public_docs = {
            "sdk_compatibility": PUBLIC_SDK_V1_COMPATIBILITY_DOC,
            "status": REPO_ROOT / "docs" / "STATUS.md",
            "plugin_hub_foundation": REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
        }

        for term in (
            "non-protected complete core evidence pack",
            "reviewed UFunction reflection-inventory pack",
            "direct core/bin planning alone is not public SDK or promotion evidence",
        ):
            with self.subTest(doc="manifest_guardrails", term=term):
                self.assertIn(normalized(term), release_guardrails)

        for name, path in public_docs.items():
            compact = normalized(path.read_text(encoding="utf-8"))
            for term in (
                "obelisk.core-dump-evidence-pack.v1",
                "obelisk.reflection-inventory-pack.v1",
                "ShooterGameServer",
            ):
                with self.subTest(doc=name, term=term):
                    self.assertIn(normalized(term), compact)
            with self.subTest(doc=name, term="direct shortcut blocked"):
                self.assertRegex(
                    compact,
                    r"(?:direct core/bin planning alone is insufficient|"
                    r"direct core/bin planning alone is not release-readiness|"
                    r"not unlocked by direct binary/core access)",
                )

    def test_v1_blocker_evidence_cannot_shortcut_completion_through_target_sets_or_candidate_artifacts(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        completion_claim_re = re.compile(
            r"\b(?:"
            r"v1[_ -]?completion[_ -]?ready|"
            r"public[_ -]?sdk[_ -]?ready|"
            r"runtime[_ -]?readiness\s*[:=]\s*true|"
            r"promotion[_ -]?ready\s*[:=]\s*true|"
            r"promote[_ -]?mode\s*[:=]\s*(?:accepted|ready)|"
            r"candidate\s+artifact\s+(?:completes|satisfies|unlocks)"
            r")\b",
            re.IGNORECASE,
        )

        self.assertFalse(manifest["v1_completion_required"])
        for surface_id in manifest["v1_sdk_completion_blockers"]:
            surface = surfaces[surface_id]
            evidence = surface.get("evidence", {})
            target_set_refs = evidence_target_set_values(evidence)
            unknown_refs = [
                f"{surface_id}:{path}={target_set}"
                for path, target_set in target_set_refs
                if target_set not in TARGET_SETS
            ]
            release_ready_refs = [
                f"{surface_id}:{path}={target_set}"
                for path, target_set in target_set_refs
                if path.endswith(".release_readiness_target_sets")
                or ".release_readiness_target_sets[" in path
                or target_set in RELEASE_READINESS_TARGET_SETS
            ]
            completion_claims = [
                f"{surface_id}:{path}: {value}"
                for path, value in json_string_values(evidence, "evidence")
                if completion_claim_re.search(value)
            ]

            with self.subTest(surface=surface_id, check="blocked status"):
                self.assertIn(surface["status"], {"planning", "post-v1", "excluded"})
                self.assertEqual(surface.get("support_tier"), "blocked")
                self.assertEqual(surface.get("public_contract", []), [])
            with self.subTest(surface=surface_id, check="known target-set refs"):
                self.assertEqual(unknown_refs, [])
            with self.subTest(surface=surface_id, check="no release-readiness target-set refs"):
                self.assertEqual(release_ready_refs, [])
            with self.subTest(surface=surface_id, check="no candidate-artifact completion claims"):
                self.assertEqual(completion_claims, [])

    def test_public_sdk_surfaces_manifest_blocks_player_services_until_identity_permissions_and_storage(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        services = surfaces["obelisk.player_services_economy_mobility.v1"]

        self.assertEqual(services["status"], "post-v1")
        self.assertEqual(services["support_tier"], "blocked")
        self.assertEqual(
            services["public_name"],
            "Blocked umbrella for player services, economy, mobility, and area policy",
        )
        self.assertEqual(services["public_contract"], [])
        self.assertEqual(
            services["depends_on"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.operator_ingress_storage.v1",
            ],
        )
        self.assertIn("obelisk.player_services_economy_mobility.v1", manifest["v1_sdk_completion_blockers"])
        self.assertIn("obelisk.player_services_economy_mobility.v1", manifest["post_v1_or_excluded_surfaces"])

        for blocker in (
            "Umbrella blocker only; future promoted surfaces should split player services, economy/shops/rewards, mobility/homes/teleport, and area policy.",
            "No promoted player/principal identity or permission model.",
            "Economy and mobility require promoted player identity/principal, permissions/admin, and storage/persistence; identity alone is insufficient.",
            "No persistence, migration, or cross-instance consistency contract.",
            "No abuse, rate-limit, rollback, audit, or privacy policy for economy and mobility actions.",
            "No safe runtime action surface for teleport, homes, rewards, kits, stats, safe zones, or timed notices.",
        ):
            self.assertIn(blocker, services["blockers"])

        for exclusion in (
            "economy API",
            "shop API",
            "rewards API",
            "kits API",
            "stats API",
            "homes API",
            "teleport API",
            "safe-zone API",
            "area policy API",
            "broadcast/timed notice service",
            "cross-instance persistence",
        ):
            self.assertIn(exclusion, services["exclusions"])

        self.assertEqual(
            services["audit_units"],
            [
                "player services",
                "economy/shops/rewards/kits/stats",
                "mobility/homes/teleport",
                "safe-zone/area policy",
                "broadcast/timed notices",
            ],
        )
        self.assertIn(
            "Each audit unit must be promoted as its own copied C ABI surface or explicitly excluded in the v1 release statement.",
            services["release_bar"],
        )

    def test_public_sdk_surfaces_manifest_keeps_operator_ingress_storage_independent_from_identity(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        operator_storage = surfaces["obelisk.operator_ingress_storage.v1"]
        decision_contract = operator_storage["v1_decision_contract"]
        offline_profile = operator_storage["offline_validation_profile"]
        release_guardrails = " ".join(manifest["release_guardrails"])

        self.assertEqual(operator_storage["status"], "post-v1")
        self.assertEqual(operator_storage["support_tier"], "blocked")
        self.assertEqual(operator_storage["public_contract"], [])
        self.assertNotIn("depends_on", operator_storage)
        self.assertIn("obelisk.operator_ingress_storage.v1", manifest["v1_sdk_completion_blockers"])
        self.assertIn("obelisk.operator_ingress_storage.v1", manifest["post_v1_or_excluded_surfaces"])
        self.assertNotIn("obelisk.operator_ingress_storage.v1", manifest["promoted_surfaces"])

        self.assertEqual(
            decision_contract["current_decision"],
            "blocked_until_promoted_or_explicitly_excluded",
        )
        self.assertTrue(decision_contract["must_remain_without_public_contract_until_promotion"])
        self.assertEqual(decision_contract["not_unlocked_by"], ["obelisk.player_identity.v1"])
        self.assertEqual(offline_profile["status"], "planning_only_no_public_abi")
        self.assertEqual(
            offline_profile["artifact"],
            "docs/research/2026-05-31-operator-ingress-storage-blocker-brief.md",
        )
        self.assertIn(
            "none; this profile is planning evidence only",
            offline_profile["promotion_effect"],
        )
        for lane in (
            "ingress contract matrix",
            "storage migration plan",
            "queue lifecycle model",
            "text and audit policy",
            "multi-instance/lifecycle proof",
        ):
            self.assertIn(lane, offline_profile["required_lanes"])
        for forbidden_runtime_dependency in (
            "public header symbols",
            "server process",
            "RCON service",
            "database/storage service",
            "webhook client",
            "secret manager",
        ):
            self.assertIn(forbidden_runtime_dependency, offline_profile["must_not_require"])
        for requirement in (
            "secret-safe ingress transport, trust-boundary, authorization, rate-limit, and backpressure contract",
            "storage schema/versioning, migration, rollback, retention, corruption-handling, and per-instance isolation contract",
            "queue durability, retry, poison-message, shutdown drain, unload drain, restart recovery, and maximum drain-time contract",
            "audit, redaction, UTF-8 validation/normalization, log escaping, and lifecycle policy",
            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer or integration tests",
        ):
            self.assertIn(requirement, decision_contract["promotion_requires"])

        for requirement in (
            "the v1 release statement names obelisk.operator_ingress_storage.v1 as post-v1 or excluded",
            "the v1 release statement states that no RCON, operator reload command API, Unicode/operator text encoding API, webhook, database/storage, secret manager, external ingress, or cross-instance storage API is included in v1",
            "v1_completion_required changes only after this blocker is promoted or that explicit exclusion is recorded",
        ):
            self.assertIn(requirement, decision_contract["exclusion_requires"])

        for blocker in (
            "Player identity/principal evidence does not unlock operator ingress/storage.",
            "No secret-safe ingress contract.",
            "No storage schema/migration contract.",
            "No queue drain, audit, encoding, or lifecycle policy for sockets/RCON/webhooks.",
        ):
            self.assertIn(blocker, operator_storage["blockers"])

        for exclusion in (
            "RCON service",
            "operator reload command API",
            "Unicode/operator text encoding API",
            "external operator command lifecycle",
            "database service",
            "webhook client",
            "secret manager",
            "cross-instance storage API",
        ):
            self.assertIn(exclusion, operator_storage["exclusions"])

        self.assertIn(
            "Player identity/principal evidence does not unlock operator ingress/storage",
            release_guardrails,
        )

    def test_public_sdk_surfaces_manifest_keeps_structure_and_buff_scope_blocked(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        structure = surfaces["obelisk.structure_census.v1"]
        modules = surfaces["obelisk.mission_transfer_dino_tribe.v1"]

        self.assertEqual(structure["depends_on"], ["obelisk.player_identity.v1"])

        for token in (
            "No ownership, placement/build-policy, no-collision, or admin-exception contract.",
            "ownership lookup",
            "build placement policy",
            "no-collision policy",
        ):
            self.assertIn(token, json.dumps(structure))

        self.assertEqual(
            structure["audit_units"],
            [
                "structure aggregate/census snapshots",
                "structure ownership/access identity",
                "placement/build-policy/no-collision",
                "admin exceptions",
            ],
        )

        self.assertIn("buff-compact-intake", modules["evidence"]["planning_target_sets"])
        for token in (
            "No public Buff SDK or class/object redaction contract.",
            "Buff/status SDK",
        ):
            self.assertIn(token, json.dumps(modules))
        self.assertEqual(
            modules["audit_units"],
            [
                "mission",
                "transfer",
                "dino policy/cosmetics/carry restrictions",
                "tribe identity/notices/policy",
                "buff/status policy",
            ],
        )
        for requirement in (
            "buff class/object redaction contract",
            "buff lifecycle, stacking, and invalidation semantics",
            "no buff aggregate, proximity, count, or mutation API until promoted",
        ):
            self.assertIn(requirement, modules["buff_audit_requirements"])

    def test_structure_census_readiness_checker_candidate_stays_non_public_and_scalar_only(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        structure = surfaces["obelisk.structure_census.v1"]
        candidate = structure["readiness_checker_candidate"]

        self.assertEqual(structure["status"], "planning")
        self.assertEqual(structure["support_tier"], "blocked")
        self.assertEqual(structure["public_contract"], [])
        self.assertEqual(candidate["status"], "candidate-only")
        self.assertEqual(candidate["scope"], "offline structure aggregate/census policy audit only")
        self.assertEqual(candidate["target_set"], "structure-aggregate-census-planning")
        self.assertEqual(candidate["artifact_schema"], "obelisk.structure-aggregate-census-policy-slice.v1")
        self.assertIs(candidate["copied_scalar_only"], True)
        self.assertIs(candidate["public_sdk_ready"], False)
        self.assertIs(candidate["promotion_ready"], False)
        self.assertIs(candidate["runtime_ready"], False)
        self.assertIs(candidate["must_remain_consume_only"], True)
        self.assertIs(candidate["must_block_promote_mode"], True)
        self.assertEqual(
            candidate["required_manifest_flags"],
            [
                "policy_status=evidence-only",
                "consume_only=true",
                "safety_summary.consume_only=true",
                "safety_summary.promotion_ready=false",
            ],
        )
        for boundary in (
            "candidate-only",
            "copied scalar event views only",
            "no public StructureEvents SDK",
            "no structure identity or lookup",
            "no mutation or return override",
            "public_sdk_ready=false",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, candidate["required_boundaries"])

    def test_structure_build_policy_targets_stay_research_only_not_public_or_runtime(self) -> None:
        forbidden_targets = (
            "PrimalStructure.IsAllowedToBuild",
            "APrimalStructure.IsAllowedToBuild",
        )
        forbidden_abi_tokens = (
            "IS_ALLOWED_TO_BUILD",
            "ALLOWED_TO_BUILD",
            "BUILD_PLACEMENT",
            "BUILD_POLICY",
            "NO_COLLISION",
            "StructureBuildPolicy",
            "BuildPolicy",
        )

        structure = next(
            surface
            for surface in json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))["surfaces"]
            if surface["id"] == "obelisk.structure_census.v1"
        )
        self.assertEqual(structure["status"], "planning")
        self.assertEqual(structure["support_tier"], "blocked")
        self.assertEqual(structure["public_contract"], [])
        self.assertEqual(
            structure["readiness_checker_candidate"]["target_set"],
            "structure-aggregate-census-planning",
        )
        self.assertIn("structure-aggregate-census-planning", PLANNING_ONLY_TARGET_SETS)
        self.assertNotIn("structure-aggregate-census-planning", RELEASE_READINESS_TARGET_SETS)

        target_set_offenders = [
            f"{target_set}: {target}"
            for target_set, targets in TARGET_SETS.items()
            for target in targets
            if any(forbidden in target for forbidden in forbidden_targets)
        ]
        self.assertEqual(target_set_offenders, [])

        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")
        for token in (*forbidden_targets, *forbidden_abi_tokens):
            with self.subTest(surface="public_header", token=token):
                self.assertNotIn(token, header)

        descriptor_files = (
            PUBLIC_GAMEPLAY_EVENTS_MANIFEST,
            PUBLIC_SDK_SURFACES_MANIFEST,
        )
        for path in descriptor_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden_targets:
                with self.subTest(surface=path.relative_to(REPO_ROOT), token=token):
                    self.assertNotIn(token, text)

        public_doc_files = (
            *PUBLIC_SDK_GUIDANCE_DOC_FILES,
            REPO_ROOT / "plugins" / "README.md",
            REPO_ROOT / "examples" / "README.md",
        )
        for path in public_doc_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden_targets:
                with self.subTest(surface=path.relative_to(REPO_ROOT), token=token):
                    self.assertNotIn(token, text)

        runtime_dispatcher_files = (
            *PROMOTED_RUNTIME_PAYLOAD_FILES,
            REPO_ROOT / "core" / "EventManager.cpp",
            REPO_ROOT / "core" / "EventManager.h",
            REPO_ROOT / "core" / "PluginManager.cpp",
            REPO_ROOT / "core" / "PluginManager.h",
        )
        for path in runtime_dispatcher_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden_targets:
                with self.subTest(surface=path.relative_to(REPO_ROOT), token=token):
                    self.assertNotIn(token, text)

    def test_future_command_principal_routing_requires_new_owner_scoped_lifecycle_surface(self) -> None:
        docs = {
            "sdk_compatibility": PUBLIC_SDK_V1_COMPATIBILITY_DOC,
            "plugin_hub_matrix": REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
        }
        shared_required_terms = (
            "lifecycle and callback-ownership",
            "new copied C ABI",
            "named capability bit captured",
            "nonzero `plugin_owner_token`",
            "owner-token handle registration",
            "owner-scoped unregister",
            "plugin-owner cleanup on init failure or unload before `dlclose`",
            "callback-scope copied payloads",
            "principal privacy/invalidation",
            "ownerless",
            "process-global capability state",
            "debug gates",
        )

        for name, path in docs.items():
            compact = normalized(path.read_text(encoding="utf-8"))
            for term in shared_required_terms:
                with self.subTest(doc=name, term=term):
                    self.assertIn(normalized(term), compact)

        sdk = normalized(PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8"))
        for term in (
            "not a parser-only extension to `ChatMessageEvent` or plugin-local routing",
            "plugin's init-time `ObeliskApi` table",
            "must not authorize routing from process-global capability state or debug gates "
            "that were not advertised to that plugin at init",
        ):
            with self.subTest(doc="sdk_compatibility", term=term):
                self.assertIn(normalized(term), sdk)

        matrix = normalized((REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md").read_text(
            encoding="utf-8"
        ))
        for term in (
            "not just a missing parser",
            "named capability bit captured at plugin init",
            "Do not route command/principal callbacks through ownerless registrations",
            "raw `ProcessEvent`",
            "experimental plugin-local `ChatMessageEvent` parsing lane",
        ):
            with self.subTest(doc="plugin_hub_matrix", term=term):
                self.assertIn(normalized(term), matrix)

    def test_chat_command_readiness_audit_keeps_local_parsing_narrow(self) -> None:
        note = CHAT_COMMAND_READINESS_AUDIT.read_text(encoding="utf-8")
        compact = normalized(note)

        for term in (
            "The current surface is enough for plugin-local command parsing tests.",
            "principal=unknown",
            "This is not enough for a public command SDK",
            "It does not provide sender/player identity, permissions, replies, chat send",
            "Runtime code should wait until a concrete test gap is identified",
            "this note does not create that approval",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compact)

        for required_scope in (
            "ABI version",
            "minimum struct size",
            "send mode",
            "copied flag",
            "sequence",
            "message text",
            "result type containing only `name`",
        ):
            with self.subTest(required_scope=required_scope):
                self.assertIn(normalized(required_scope), compact)

        for boundary in (
            "sender/player identity",
            "permissions",
            "replies",
            "chat send",
            "moderation",
            "blocking",
            "mutation",
            "return override",
            "UE lookup",
            "raw `FString`",
            "`UObject`",
            "`UFunction`",
            "raw params",
            "FName/GObjects indices",
            "persistent identity",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(normalized(boundary), compact)

        self.assertIn("docs/tests, not runtime code", compact)
        self.assertIn("not an approved live test", compact)

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
            (texts["docs/PLUGIN_HUB_FOUNDATION_V1.md"], "conceptual architecture, and migration-ergonomics references"),
            (texts["docs/PLUGIN_HUB_FOUNDATION_V1.md"], "surface must be rebuilt through Obelisk reflection"),
            (texts["docs/PLUGIN_HUB_CAPABILITY_MATRIX.md"], "not as portable behavior, source, ABI, constants, schemas, command parsers, or\nimplementation patterns"),
            (texts["docs/PLUGIN_HUB_CAPABILITY_MATRIX.md"], "Rebuild every promoted surface through Obelisk\nreflection"),
            (texts["docs/PLUGIN_HUB_CAPABILITY_MATRIX.md"], "provenance for\n"
             "demand analysis only"),
            (texts["docs/PLUGIN_HUB_CAPABILITY_MATRIX.md"], "not license clearance, runtime evidence, an ArkApi\n"
             "compatibility target, or an ABI reference"),
            (texts["docs/research/2026-05-30-v1-core-capability-map.md"], "ArkServerApi/AseApi is a names, demand, conceptual architecture"),
            (texts["docs/research/2026-05-30-v1-core-capability-map.md"], "this is not ArkApi source, ABI, behavior, or\n  plugin compatibility"),
            (texts["docs/research/2026-05-30-v1-core-capability-map.md"], "Obelisk-native Linux plugins for common ArkApi-style modding\nneeds"),
            (texts["docs/research/README.md"], "ArkApi/AseApi material remains a names/demand/architecture\n  reference only"),
            (texts["plugins/README.md"], "names, demand, conceptual architecture, and\nmigration-ergonomics signals only"),
            (texts["plugins/README.md"], "not a compatibility target, source reference, ABI\n"
             "reference, schema, command parser, or "
             "implementation pattern"),
            (texts["docs/research/2026-05-30-nextgenplugins-reference-inventory.md"], "Use this clone as a names/demand/architecture reference"),
            (texts["docs/research/2026-05-30-nextgenplugins-reference-inventory.md"], "not as source code to port"),
            (texts["docs/research/2026-05-30-nextgenplugins-reference-inventory.md"], "Do not trust `DECLARE_HOOK` declarations as Linux ABI"),
            (texts["docs/research/2026-05-30-nextgenplugins-reference-inventory.md"], "not runtime evidence and do not authorize copied implementation"),
            (texts["docs/research/2026-05-30-aseapi-reference-scan.md"], "only as a names and demand dictionary"),
            (texts["docs/research/2026-05-30-aseapi-reference-scan.md"], "not a behavior map,\ncompatibility target, implementation guide, or evidence source"),
            (texts["docs/research/2026-05-30-aseapi-reference-scan.md"], "Candidate name discovery only"),
            (texts["docs/research/2026-05-30-aseapi-reference-scan.md"], "Behavior parity, control flow, command parsers, schemas, constants, return semantics"),
            (texts["agent-skills/obelisk-github-research-workflow/SKILL.md"], "Local\nNextGenPlugins clones are names, demand, conceptual architecture"),
            (texts["agent-skills/obelisk-github-research-workflow/SKILL.md"], "Obelisk must not copy ArkServerApi/AseApi,\nNextGenPlugins"),
            (texts["docs/agent-handoff/CURRENT.md"], "ArkServerApi/AseApi and local `NextGenPlugins` clones are names, demand, conceptual\n  architecture"),
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
            "In this document, `V1` means the first reviewed Plugin Hub foundation/intake contract revision",
            "It is not Obelisk SDK v1, not `v1.0 stable`, and not a Plugin Hub completion claim",
            "This foundation is post-SDK planning, not a change to the published `v0.1.0-rc.2` tag",
            "When Plugin Hub resumes after SDK completion, release-supported seed work can start with lifecycle/config/logging skeletons",
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
            "The pre-v1 Plugin Hub package contract is an intake boundary",
            "not a registry implementation, a machine-readable manifest\nschema, a compatibility promise, or v1 completion evidence",
            "`plugin_id`, display name, plugin version, minimum Obelisk SDK\nline, exactly one `Support tier: <tier>` declaration",
            "Review must fail if README, package metadata, or public seed docs claim v1 readiness",
            "Acceptance for a release-supported seed requires building against an installed SDK",
            "`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`",
            "hidden default symbol visibility, no private Obelisk headers",
            "fail-closed `struct_size` and\ncapability checks, safe-disabled config defaults, owner-token cleanup, and idempotent\nshutdown",
            "Reject or keep in backlog any package that depends on unpromoted gameplay surfaces",
            "send-chat/replies, permissions, identity, storage services, mutation, or\nreturn overrides",
        )

        for item in required:
            with self.subTest(item=item):
                self.assertIn(normalized(item), compact)

    def test_docs_index_keeps_plugin_author_creation_boundary_visible(self) -> None:
        docs_index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        compact = normalized(docs_index)

        required = (
            "what a plugin can honestly build today",
            "current installed-SDK foundation examples, not active Plugin Hub work, are lifecycle/config/logging, descriptor/catalog consumers, and process-local timers",
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
            (foundation, "Copied chat parsers and copied policy\nauditors may demonstrate patterns, but they remain experimental"),
            (matrix, "## Post-v0.1 Creator Ladder"),
            (matrix, "Release-supported seed lanes"),
            (matrix, "Experimental pattern examples only"),
            (matrix, "Descriptor consumers"),
            (matrix, "Passive chat text parsers"),
            (matrix, "Timer utilities"),
            (matrix, "Copied policy auditors"),
            (matrix, "## Deferred Support Boundary"),
            (matrix, "Plugin Hub seed work resumes after SDK completion"),
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
            (descriptor_doc, "safe-disabled config before requiring the optional descriptor API slots"),
            (descriptor_doc, "`ObeliskApi::struct_size` through `DescribeGameplayPolicyEventKind`"),
            (descriptor_doc, "fail closed without registering callbacks or timers"),
            (descriptor_doc, "no owner-token runtime state because it does not register\ncallbacks or timers"),
            (descriptor_doc, "`FName`, `GNames`, `GObjects`,\n`UObject`, or raw UE pointer access"),
            (timer_doc, "process-local timers"),
            (timer_doc, "does not use or imply UE timers, gameplay timers, `ProcessEvent`"),
            (timer_doc, "`ObeliskApi::struct_size` through `UnregisterTimerWithOwnerToken`"),
            (timer_doc, "non-null timer\nregister/unregister function pointers"),
            (timer_doc, "non-zero `plugin_owner_token` before any\nregistration"),
            (plugins_readme, "Release-supported seed examples are limited to lifecycle/config/logging, descriptor\nreaders, and process-local timer utilities"),
            (plugins_readme, "Those release-supported seeds still must\nkeep the shared safe default config posture"),
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
            "Those are the release-supported seed lanes",
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
        compatibility_doc = PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8")
        surfaces = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        public_headers = sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in (REPO_ROOT / "include").rglob("*")
            if path.is_file()
        )
        sdk_package_shape = surfaces["installed_sdk_package_shape"]
        expected_sdk_files = [
            "include/obelisk/ObeliskApi.h",
            "lib/cmake/Obelisk/ObeliskConfig.cmake",
            "lib/cmake/Obelisk/ObeliskConfigVersion.cmake",
            "lib/cmake/Obelisk/ObeliskTargets.cmake",
        ]

        self.assertEqual(public_headers, ["include/obelisk/ObeliskApi.h"])
        self.assertEqual(sdk_package_shape["component"], "SDK")
        self.assertEqual(sdk_package_shape["status"], "package-shape-evidence-only")
        self.assertEqual(sdk_package_shape["installed_files"], expected_sdk_files)
        self.assertIn("v1_completion_required", sdk_package_shape["not_sufficient_for"])
        self.assertIn(
            "stable_release_contract.claim_allowed",
            sdk_package_shape["not_sufficient_for"],
        )
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
        for sdk_file in expected_sdk_files:
            with self.subTest(sdk_file=sdk_file):
                self.assertIn(f'"{sdk_file}"', installer)
                self.assertIn(sdk_file, install_doc)
                self.assertIn(sdk_file, compatibility_doc)
        for managed_subpath in (
            "include/obelisk",
            "lib/cmake",
            "lib/cmake/Obelisk",
        ):
            with self.subTest(managed_subpath=managed_subpath):
                self.assertIn(f'"{managed_subpath}"', installer)
                self.assertIn(f"`{managed_subpath}`", install_doc)
        self.assertNotIn("include/obelisk/*.h", install_doc)

    def test_installed_sdk_target_exports_only_public_header_include_dir(self) -> None:
        root_cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        package_config = (REPO_ROOT / "cmake" / "ObeliskConfig.cmake.in").read_text(encoding="utf-8")
        offenders: list[str] = []

        self.assertIn("add_library(obelisk_sdk INTERFACE)", root_cmake)
        self.assertRegex(
            root_cmake,
            r"target_include_directories\s*\(\s*obelisk_sdk\s+INTERFACE\s+"
            r"\$<BUILD_INTERFACE:\$\{CMAKE_CURRENT_SOURCE_DIR\}/include>\s+"
            r"\$<INSTALL_INTERFACE:\$\{CMAKE_INSTALL_INCLUDEDIR\}>\s*\)",
        )

        for match in re.finditer(
            r"target_link_libraries\s*\(\s*obelisk_sdk\b(?P<body>.*?)\)",
            root_cmake,
            flags=re.DOTALL,
        ):
            offenders.append(
                "CMakeLists.txt: obelisk_sdk must not export link dependencies: "
                f"{normalized(match.group('body'))}"
            )

        sdk_include_match = re.search(
            r"target_include_directories\s*\(\s*obelisk_sdk\b(?P<body>.*?)\)",
            root_cmake,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(sdk_include_match)
        if sdk_include_match is not None:
            body = sdk_include_match.group("body")
            for forbidden in (
                "${CMAKE_CURRENT_SOURCE_DIR}/core",
                "${CMAKE_CURRENT_SOURCE_DIR}/hooks",
                "${CMAKE_CURRENT_SOURCE_DIR}/ue",
                "${CMAKE_CURRENT_SOURCE_DIR}/runtime",
                "${CMAKE_CURRENT_SOURCE_DIR}/api",
                "${CMAKE_CURRENT_SOURCE_DIR}/extern",
                "fmt",
                "spdlog",
                "subhook",
                "nlohmann",
            ):
                if forbidden in body:
                    offenders.append(f"CMakeLists.txt: obelisk_sdk include leak {forbidden}")

        for forbidden in ("find_dependency", "fmt", "spdlog", "subhook", "nlohmann", "core/", "hooks/", "ue/"):
            if forbidden in package_config:
                offenders.append(f"cmake/ObeliskConfig.cmake.in: package dependency leak {forbidden}")

        self.assertIn("set(Obelisk_SDK_FOUND TRUE)", package_config)
        self.assertEqual(offenders, [])

    def test_creator_facing_sdk_examples_do_not_depend_on_private_headers_or_repo_deps(self) -> None:
        forbidden_include_prefixes = (
            "api/",
            "core/",
            "hooks/",
            "plugins/",
            "runtime/",
            "ue/",
            "fmt/",
            "spdlog/",
            "subhook/",
            "nlohmann/",
        )
        forbidden_include_names = {
            "subhook.h",
            "nlohmann/json.hpp",
        }
        forbidden_cmake_tokens = (
            "target_include_directories",
            "include_directories",
            "add_subdirectory",
            "FetchContent",
            "fmt::",
            "spdlog::",
            "subhook",
            "nlohmann",
            "${CMAKE_CURRENT_SOURCE_DIR}/..",
            "${PROJECT_SOURCE_DIR}/..",
        )
        offenders: list[str] = []

        for path in sorted((REPO_ROOT / "examples").rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(REPO_ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            if path.suffix in {".c", ".cpp", ".h", ".hpp"}:
                for header in c_like_includes(text):
                    if header in forbidden_include_names or header.startswith(forbidden_include_prefixes):
                        offenders.append(f"{relative}: forbidden include {header}")
            if path.name == "CMakeLists.txt":
                self.assertIn(
                    "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)",
                    re.sub(r"\s+", " ", text),
                    f"{relative} must consume the installed Obelisk SDK component",
                )
                self.assertIn("Obelisk::obelisk_sdk", text, f"{relative} must link the public SDK target")
                for token in forbidden_cmake_tokens:
                    if token in text:
                        offenders.append(f"{relative}: forbidden CMake token {token}")
                for match in re.finditer(
                    r"target_link_libraries\s*\((?P<body>.*?)\)",
                    text,
                    flags=re.DOTALL,
                ):
                    body = normalized(match.group("body"))
                    for token in ("fmt", "spdlog", "subhook", "nlohmann", "dl", "pthread"):
                        if re.search(rf"\b{re.escape(token)}\b", body):
                            offenders.append(f"{relative}: example links non-SDK dependency {token}")

        self.assertEqual(offenders, [])

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

    def test_public_header_has_no_unpromoted_module_macros_or_capabilities(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")
        symbols = set(public_obelisk_macro_defines(header))
        for enum_members in public_enum_definitions(header).values():
            symbols.update(enum_members)

        offenders = []
        for symbol in sorted(symbols):
            families = module_family_hits(symbol)
            if not families or symbol in V010_PUBLIC_MODULE_SYMBOL_EXCEPTIONS:
                continue
            offenders.append(f"{symbol}: {', '.join(sorted(families))}")

        self.assertEqual(
            offenders,
            [],
            "Public module-family macros/enums need a deliberate allowlist update after promotion.",
        )

        capability_offenders = [
            capability
            for capability in public_api_capability_defines(header)
            if module_family_hits(capability)
        ]
        self.assertEqual(
            capability_offenders,
            [],
            "New public module capabilities require promotion evidence before entering ObeliskApi.h.",
        )

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

    def test_public_chat_abi_stays_notification_only_without_command_response_symbols(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")
        stripped_header = strip_c_comments(header)

        self.assertEqual(
            [name for name in public_api_capability_defines(header) if "CHAT" in name],
            ["OBELISK_API_CAPABILITY_CHAT_EVENTS"],
        )
        self.assertEqual(
            [name for name in public_struct_typedefs(header) if "Chat" in name],
            ["ObeliskChatMessageEvent"],
        )
        self.assertEqual(
            [name for name in public_enum_typedefs(header) if "Chat" in name],
            ["ObeliskChatSendMode"],
        )
        self.assertEqual(
            [name for name in public_callback_typedefs(header) if "Chat" in name],
            ["ObeliskChatMessageEventCallback"],
        )
        self.assertEqual(
            [name for name in obelisk_api_field_names(header) if "Chat" in name],
            [
                "RegisterChatMessageEventWithOwnerTokenHandle",
                "UnregisterChatMessageEventWithOwnerToken",
            ],
        )

        for token in UNPROMOTED_CHAT_COMMAND_RESPONSE_API_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, stripped_header)

    def test_player_identity_must_remain_a_separate_future_surface_not_event_extension(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")
        stripped_header = strip_c_comments(header)
        manifest = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        player_identity = surfaces["obelisk.player_identity.v1"]

        self.assertEqual(player_identity["status"], "planning")
        self.assertEqual(player_identity["public_contract"], [])
        self.assertIn("obelisk.player_identity.v1", manifest["v1_sdk_completion_blockers"])
        self.assertNotIn("obelisk.player_identity.v1", manifest["promoted_surfaces"])

        forbidden_public_identity_tokens = (
            "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
            "OBELISK_API_CAPABILITY_PRINCIPALS",
            "OBELISK_API_CAPABILITY_IDENTITY",
            "ObeliskPlayerIdentity",
            "ObeliskPlayerPrincipal",
            "ObeliskPrincipal",
            "ObeliskPlayerId",
            "ObeliskPlayerHandle",
            "ObeliskPlayerLookup",
            "ObeliskSteamId",
            "ObeliskEOSId",
            "ObeliskUniqueNetId",
            "ObeliskIdentity",
            "RegisterPlayerIdentity",
            "RegisterPlayerPrincipal",
            "RegisterIdentity",
            "DescribePlayerIdentity",
            "ResolvePlayerIdentity",
            "ResolvePlayer",
            "FindPlayer",
            "LookupPlayer",
            "player_id",
            "principal_id",
            "sender_identity",
        )
        for token in forbidden_public_identity_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, stripped_header)

        for struct_name in ("ObeliskChatMessageEvent", "ObeliskGameplayPolicyEvent"):
            for field in public_struct_field_names(header, struct_name):
                lowered = field.lower()
                with self.subTest(struct=struct_name, field=field):
                    self.assertNotIn("principal", lowered)
                    self.assertNotIn("identity", lowered)
                    self.assertNotIn("player", lowered)

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
            "`GameplayPolicyEvent` has v0.1 release-readiness evidence, while `ChatMessageEvent` is minimal and RC.",
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

    def test_experimental_copied_event_v1_completion_claim_detector_is_order_independent(self) -> None:
        forbidden = [
            "`GameplayPolicyEvent` is v1-complete.",
            "`ChatMessageEvent` completes the v1 SDK.",
            "`GameplayPolicyEvent` and `ChatMessageEvent` are sufficient for v1_completion_required.",
            "The complete v1 SDK is available through `GameplayPolicyEvent`.",
            "`ChatMessageEvent` makes Obelisk v1.0 stable.",
        ]
        allowed = [
            "`GameplayPolicyEvent` remains promoted-experimental-only until the full SDK completion bar is met.",
            "`ChatMessageEvent` is not a v1 completion claim.",
            "`GameplayPolicyEvent` and `ChatMessageEvent` are copied-data seeds only, not v1-complete.",
            "A complete v1 SDK requires promoted blockers; `GameplayPolicyEvent` remains a copied-data seed.",
        ]

        for text in forbidden:
            with self.subTest(kind="forbidden", text=text):
                self.assertNotEqual(
                    experimental_event_v1_completion_claims(text, "synthetic.md"),
                    [],
                )
        for text in allowed:
            with self.subTest(kind="allowed", text=text):
                self.assertEqual(
                    experimental_event_v1_completion_claims(text, "synthetic.md"),
                    [],
                )

    def test_public_material_does_not_claim_copied_events_complete_v1_sdk(self) -> None:
        offenders: list[str] = []

        for path in CHAT_MESSAGE_EVENT_PUBLIC_CLAIM_FILES + [PUBLIC_SDK_SURFACES_MANIFEST]:
            text = path.read_text(encoding="utf-8")
            if path in {PUBLIC_GAMEPLAY_EVENTS_MANIFEST, PUBLIC_SDK_SURFACES_MANIFEST}:
                text = json.dumps(json.loads(text), sort_keys=True, indent=2)
            offenders.extend(
                experimental_event_v1_completion_claims(
                    text,
                    str(path.relative_to(REPO_ROOT)),
                )
            )

        self.assertEqual(offenders, [])

    def test_public_header_marks_copied_event_seeds_as_not_v1_complete(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")
        raw_callback_section = header[
            header.index("Raw ProcessEvent callback registration") :
            header.index("Filtered registrations are rejected")
        ]

        self.assertIn("copied v0.1", raw_callback_section)
        self.assertIn("GameplayPolicyEvent", raw_callback_section)
        self.assertIn("ChatMessageEvent", raw_callback_section)
        self.assertIn("promoted-experimental-only", raw_callback_section)
        self.assertIn("not a v1-complete", raw_callback_section)

    def test_broad_v1_completion_claim_detector_allows_scoped_language_only(self) -> None:
        forbidden = [
            "Obelisk v1.0 stable is ready for production.",
            "The complete SDK is available to plugin authors.",
            "The full SDK has shipped.",
            "The production-ready public SDK is released.",
            "The v0.1 RC ships the complete SDK for plugin authors.",
            "This release candidate includes the full plugin SDK.",
            "Post-RC foundation work means the production-ready SDK is available.",
            "Server owners can use the complete public SDK today.",
            "Obelisk stable v1 SDK is ready.",
            "Obelisk v1 SDK is complete.",
            "SDK v1 is production-ready.",
            "The GA SDK is published.",
            "The 1.0 stable SDK is ready.",
            "The full plugin SDK is supported.",
            "All v1 surfaces are available.",
            "SDK v1.0: stable.",
            "The stable-v1 SDK is available.",
            "This is a production ready SDK.",
            "We claim the complete SDK is available.",
            "Release notes claim the full plugin SDK has shipped.",
            "The v0.1 RC ships the complete-SDK for plugin authors.",
            "The v0.1 RC SDK is complete.",
            "The v0.1 RC ships the complete SDK, not just runtime fixes.",
            "This release candidate includes the full-plugin SDK, not only examples.",
        ]
        allowed = [
            "Obelisk is moving toward a complete SDK.",
            "The intended v1.0 stable milestone must mean the complete public SDK contract.",
            "This is not a complete SDK claim.",
            "The complete SDK remains blocked until the v1 checker allows the claim.",
            "This RC foundation is not v1.0 stable.",
            "The v0.1 RC does not ship the complete SDK.",
            "Post-RC foundation work moves toward a complete SDK.",
            "Policy docs must not claim `complete SDK` before the gate passes.",
            "The v1 SDK complete route remains planning-only.",
        ]

        for text in forbidden:
            with self.subTest(kind="forbidden", text=text):
                self.assertNotEqual(broad_v1_completion_claims(text, "synthetic.md"), [])
        for text in allowed:
            with self.subTest(kind="allowed", text=text):
                self.assertEqual(broad_v1_completion_claims(text, "synthetic.md"), [])

    def test_public_material_does_not_claim_broad_v1_completion_before_gate(self) -> None:
        completion_report = runpy.run_path(
            str(REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"),
            run_name="__not_main__",
        )
        report = completion_report["build_report"](PUBLIC_SDK_SURFACES_MANIFEST)

        if report["stable_claim_allowed"]:
            return

        offenders: list[str] = []
        for path in BROAD_V1_COMPLETION_CLAIM_FILES:
            offenders.extend(
                broad_v1_completion_claims(
                    path.read_text(encoding="utf-8"),
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

    def test_installed_descriptor_catalog_consumer_covers_promoted_descriptor_limits(self) -> None:
        descriptor_consumer = (
            REPO_ROOT / "tests" / "sdk_installed_consumer" / "descriptor_catalog_plugin.cpp"
        ).read_text(encoding="utf-8")

        for token in [
            "kExpectedPromotedResourceKindDescriptors",
            "kExpectedPromotedGameplayPolicyEventDescriptors",
            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN",
            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX",
            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_COUNT",
            "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES",
            "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
            "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL",
            "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM + 1u",
        ]:
            with self.subTest(token=token):
                self.assertIn(token, descriptor_consumer)

        for token in V010_PUBLIC_GAMEPLAY_POLICY_EVENT_TOKENS:
            with self.subTest(event_kind=token):
                self.assertIn(token, descriptor_consumer)

        for stable_name in V010_PUBLIC_GAMEPLAY_POLICY_STABLE_NAMES:
            with self.subTest(stable_name=stable_name):
                self.assertIn(stable_name, descriptor_consumer)

    def test_installed_sdk_layout_keeps_release_scope_examples_on_installed_package(self) -> None:
        consumer_cmake = (REPO_ROOT / "tests/sdk_installed_consumer/CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        layout_script = (REPO_ROOT / "scripts/test_install_obelisk_layout.sh").read_text(encoding="utf-8")

        self.assertIn("find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)", consumer_cmake)
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
        install_layout_script = (REPO_ROOT / "scripts" / "test_install_obelisk_layout.sh").read_text(
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
                self.assertIn(
                    "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)",
                    normalized_text,
                )
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

        examples_readme_normalized = re.sub(r"\s+", " ", examples_readme)
        for token in (
            "callback handles, timer handles, copied event sequence values, and descriptor cache state as process-local only",
            "never persists them in config/shared storage or reuses them after restart, map transfer, or another ARK server process",
            "recreates registrations during `ObeliskPlugin_Init` and releases them in `ObeliskPlugin_Shutdown`",
        ):
            with self.subTest(path="examples/README.md", token=token):
                self.assertIn(token, examples_readme_normalized)

        minimal_readme_normalized = re.sub(r"\s+", " ", minimal_readme)
        for token in (
            "the runtime evaluates the plugin activation envelope before calling `ObeliskPlugin_Init`",
            "minimal example does not parse config itself",
            "must not be copied as the activation model for feature plugins",
            "enforcing `struct_size` gates before reading appended API slots",
            "validating `plugin_owner_token`",
            "unregistering owned runtime state",
        ):
            with self.subTest(path="examples/sdk_minimal_plugin/README.md", token=token):
                self.assertIn(token, minimal_readme_normalized)

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

        for token in (
            "SDK_MINIMAL_EXAMPLE_PLUGIN_PATH",
            "SDK_TIMER_EXAMPLE_PLUGIN_PATH",
            '"${WORK_DIR}/build/consumer_fixture"',
            '"obelisk_sdk_minimal_plugin"',
            '"obelisk_sdk_timer_plugin"',
        ):
            with self.subTest(path="scripts/test_install_obelisk_layout.sh", token=token):
                self.assertIn(token, install_layout_script)

    def test_sdk_timer_plugin_example_stays_installed_sdk_only(self) -> None:
        examples_readme = (REPO_ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        timer_readme = (REPO_ROOT / "examples" / "sdk_timer_plugin" / "README.md").read_text(
            encoding="utf-8"
        )
        timer_cmake = (REPO_ROOT / "examples" / "sdk_timer_plugin" / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        timer_source = (REPO_ROOT / "examples" / "sdk_timer_plugin" / "timer_plugin.c").read_text(
            encoding="utf-8"
        )

        for path in SDK_TIMER_PLUGIN_EXAMPLE_FILES:
            with self.subTest(path=path.relative_to(REPO_ROOT), token="example file"):
                self.assertTrue(path.exists())

        for text, relative in (
            (examples_readme, "examples/README.md"),
            (timer_readme, "examples/sdk_timer_plugin/README.md"),
            (timer_cmake, "examples/sdk_timer_plugin/CMakeLists.txt"),
        ):
            normalized_text = re.sub(r"\s+", " ", text)
            with self.subTest(path=relative, token="find_package"):
                self.assertIn(
                    "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)",
                    normalized_text,
                )
            with self.subTest(path=relative, token="sdk target"):
                self.assertIn("Obelisk::obelisk_sdk", text)

        for token in (
            "OBELISK_API_CAPABILITY_TIMERS",
            "RegisterTimerWithOwnerTokenHandle",
            "UnregisterTimerWithOwnerToken",
            "plugin_owner_token != 0",
            "InstallLayoutConsumer_ScheduledCallbackSeen",
            "OBELISK_PLUGIN_EXPORT",
            "atomic_load(&g_timer_id)",
            "atomic_exchange(&g_timer_id, 0)",
        ):
            with self.subTest(path="examples/sdk_timer_plugin/timer_plugin.c", token=token):
                self.assertIn(token, timer_source)
        self.assertNotIn("__attribute__((visibility(\"default\")))\nbool", timer_source)
        self.assertIn("OBELISK_SDK_TIMER_PLUGIN_TEST_PROBES", timer_source)
        self.assertIn("OBELISK_SDK_TIMER_PLUGIN_TEST_PROBES", timer_cmake)

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
            with self.subTest(path="examples/sdk_timer_plugin/timer_plugin.c", forbidden=token):
                self.assertNotIn(token, timer_source)

    def test_sdk_descriptor_catalog_example_stays_installed_sdk_only(self) -> None:
        examples_readme = (REPO_ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        descriptor_readme = (
            REPO_ROOT / "examples" / "sdk_descriptor_catalog" / "README.md"
        ).read_text(encoding="utf-8")
        descriptor_cmake = (
            REPO_ROOT / "examples" / "sdk_descriptor_catalog" / "CMakeLists.txt"
        ).read_text(encoding="utf-8")
        descriptor_source = (
            REPO_ROOT / "examples" / "sdk_descriptor_catalog" / "descriptor_catalog_plugin.c"
        ).read_text(encoding="utf-8")

        for path in SDK_DESCRIPTOR_CATALOG_EXAMPLE_FILES:
            with self.subTest(path=path.relative_to(REPO_ROOT), token="example file"):
                self.assertTrue(path.exists())

        for text, relative in (
            (examples_readme, "examples/README.md"),
            (descriptor_readme, "examples/sdk_descriptor_catalog/README.md"),
            (descriptor_cmake, "examples/sdk_descriptor_catalog/CMakeLists.txt"),
        ):
            normalized_text = re.sub(r"\s+", " ", text)
            with self.subTest(path=relative, token="find_package"):
                self.assertIn(
                    "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)",
                    normalized_text,
                )
            with self.subTest(path=relative, token="sdk target"):
                self.assertIn("Obelisk::obelisk_sdk", text)

        self.assertIn("Support tier: release-supported seed.", descriptor_readme)
        descriptor_readme_normalized = re.sub(r"\s+", " ", descriptor_readme)
        for token in (
            "metadata-only descriptor discovery",
            "Resource descriptors are category data only",
            "not identity, lookup handles, persistent IDs, mutable resources",
            "do not expose raw UE state, return override authority, mutation, or object lookup",
            "does not use private headers, raw UE pointers, `ProcessEvent`",
            "identity, lookup, mutation, return overrides, chat replies/send-chat, ArkApi",
        ):
            with self.subTest(path="examples/sdk_descriptor_catalog/README.md", token=token):
                self.assertIn(token, descriptor_readme_normalized)

        self.assertEqual(c_like_includes(descriptor_source)[0], "obelisk/ObeliskApi.h")
        self.assertIn("#include <obelisk/ObeliskApi.h>", descriptor_source)
        self.assertIn("C_VISIBILITY_PRESET hidden", descriptor_cmake)
        self.assertIn("OBELISK_SDK_DESCRIPTOR_CATALOG_TEST_PROBES", descriptor_cmake)
        self.assertIn("#ifdef OBELISK_SDK_DESCRIPTOR_CATALOG_TEST_PROBES", descriptor_source)
        self.assertIn("InstallLayoutConsumer_DescriptorCatalogValidated", descriptor_source)

        exported_functions = re.findall(
            r"OBELISK_PLUGIN_EXPORT\s+bool\s+(ObeliskPlugin_[A-Za-z0-9_]+)\s*\(",
            descriptor_source,
        )
        self.assertEqual(exported_functions, ["ObeliskPlugin_GetInfo", "ObeliskPlugin_Init"])
        self.assertIn("OBELISK_PLUGIN_EXPORT\nvoid ObeliskPlugin_Shutdown(void)", descriptor_source)
        self.assertNotIn("__attribute__((visibility(\"default\")))\nbool", descriptor_source)

        for token in (
            '\\"enabled\\": false',
            '\\"allow_all_instances\\": false',
            '\\"instance_allowlist\\": []',
            'out->default_config_json = kDefaultConfig',
        ):
            with self.subTest(path="examples/sdk_descriptor_catalog/descriptor_catalog_plugin.c", token=token):
                self.assertIn(token, descriptor_source)

        for token in (
            "api->abi_version == OBELISK_API_ABI_VERSION",
            "api->struct_size >= offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +",
            "OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS",
            "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS",
            "api->DescribeResourceKind != NULL",
            "api->DescribeGameplayPolicyEventKind != NULL",
            "context->abi_version == OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION",
            "context->struct_size >= offsetof(ObeliskPluginInitContext, instance_id) +",
            "out->struct_size == sizeof(*out)",
            "descriptor catalog did not cover all promoted event kinds",
        ):
            with self.subTest(path="examples/sdk_descriptor_catalog/descriptor_catalog_plugin.c", token=token):
                self.assertIn(token, descriptor_source)

        for token in (
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
            "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN",
            "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX",
            "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL",
        ):
            with self.subTest(path="examples/sdk_descriptor_catalog/descriptor_catalog_plugin.c", token=token):
                self.assertIn(token, descriptor_source)

        for text, relative in (
            (descriptor_readme, "examples/sdk_descriptor_catalog/README.md"),
            (descriptor_cmake, "examples/sdk_descriptor_catalog/CMakeLists.txt"),
            (descriptor_source, "examples/sdk_descriptor_catalog/descriptor_catalog_plugin.c"),
        ):
            with self.subTest(path=relative, check="no-broad-v1-completion-claim"):
                self.assertEqual(broad_v1_completion_claims(text, relative), [])

        self.assertEqual(
            plugin_hub_seed_forbidden_claims(
                descriptor_readme,
                "examples/sdk_descriptor_catalog/README.md",
                "release-supported seed",
            ),
            [],
        )
        install_layout_script = (
            REPO_ROOT / "scripts" / "test_install_obelisk_layout.sh"
        ).read_text(encoding="utf-8")
        for token in (
            "SDK_DESCRIPTOR_EXAMPLE_PLUGIN_PATH",
            "examples/sdk_descriptor_catalog",
            "obelisk_sdk_descriptor_catalog.so",
            '"obelisk_sdk_descriptor_catalog"',
        ):
            with self.subTest(path="scripts/test_install_obelisk_layout.sh", token=token):
                self.assertIn(token, install_layout_script)

        for text, relative in (
            (descriptor_cmake, "examples/sdk_descriptor_catalog/CMakeLists.txt"),
            (descriptor_source, "examples/sdk_descriptor_catalog/descriptor_catalog_plugin.c"),
        ):
            for token in (
                '#include "',
                "#include <api/",
                "#include <core/",
                "#include <hooks/",
                "#include <plugins/",
                "#include <runtime/",
                "#include <ue/",
                "UObject",
                "UFunction",
                "FString",
                "ProcessEvent",
                "CallProcessEvent",
                "RegisterPreProcessEvent",
                "RegisterPostProcessEvent",
                "RegisterGameplayPolicyEvent",
                "RegisterChat",
                "ChatMessageEvent",
                "SendChat",
                "Reply",
                "ArkApi",
                "AseApi",
                "ResourceHandle",
                "GetResource",
                "ResolveResource",
                "player identity",
                "object identity",
                "resource identity",
                "return_override",
            ):
                with self.subTest(path=relative, forbidden=token):
                    self.assertNotIn(token, text)

    def test_sdk_inventory_policy_audit_example_stays_experimental_installed_sdk_only(self) -> None:
        examples_readme = (REPO_ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        audit_readme = (
            REPO_ROOT / "examples" / "sdk_inventory_policy_audit" / "README.md"
        ).read_text(encoding="utf-8")
        audit_cmake = (
            REPO_ROOT / "examples" / "sdk_inventory_policy_audit" / "CMakeLists.txt"
        ).read_text(encoding="utf-8")
        audit_source = (
            REPO_ROOT
            / "examples"
            / "sdk_inventory_policy_audit"
            / "inventory_policy_audit_plugin.c"
        ).read_text(encoding="utf-8")

        for path in SDK_INVENTORY_POLICY_AUDIT_EXAMPLE_FILES:
            with self.subTest(path=path.relative_to(REPO_ROOT), token="example file"):
                self.assertTrue(path.exists())

        for text, relative in (
            (examples_readme, "examples/README.md"),
            (audit_readme, "examples/sdk_inventory_policy_audit/README.md"),
            (audit_cmake, "examples/sdk_inventory_policy_audit/CMakeLists.txt"),
        ):
            normalized_text = re.sub(r"\s+", " ", text)
            with self.subTest(path=relative, token="find_package"):
                self.assertIn(
                    "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)",
                    normalized_text,
                )
            with self.subTest(path=relative, token="sdk target"):
                self.assertIn("Obelisk::obelisk_sdk", text)

        examples_readme_normalized = re.sub(r"\s+", " ", examples_readme)
        for token in (
            "not built by the top-level Obelisk CMake project",
            "not installed by `scripts/install_obelisk.sh`",
            "not part of the release-supported install layout",
        ):
            with self.subTest(path="examples/README.md", token=token):
                self.assertIn(token, examples_readme_normalized)

        self.assertIn("Support tier: experimental pattern.", audit_readme)
        audit_readme_normalized = re.sub(r"\s+", " ", audit_readme)
        for token in (
            "experimental copied-data pattern",
            "copied inventory-backed `GameplayPolicyEvent` categories",
            "callback-scope scalar fields",
            "process-local aggregate counts",
            "does not provide an Inventory SDK, Items SDK, identity, lookup, mutation",
            "return override, commands, permissions, chat replies/send-chat, storage, ArkApi",
            "does not make policy decisions",
            "does not retain callback payloads",
        ):
            with self.subTest(path="examples/sdk_inventory_policy_audit/README.md", token=token):
                self.assertIn(token, audit_readme_normalized)

        self.assertEqual(c_like_includes(audit_source)[0], "obelisk/ObeliskApi.h")
        self.assertIn("#include <obelisk/ObeliskApi.h>", audit_source)
        self.assertIn("C_VISIBILITY_PRESET hidden", audit_cmake)
        self.assertIn("OBELISK_SDK_INVENTORY_POLICY_AUDIT_TEST_PROBES", audit_cmake)
        self.assertIn("#ifdef OBELISK_SDK_INVENTORY_POLICY_AUDIT_TEST_PROBES", audit_source)
        self.assertIn("InstallLayoutConsumer_InventoryPolicyAuditRegistered", audit_source)
        self.assertIn("InstallLayoutConsumer_InventoryPolicyAuditEventCount", audit_source)

        exported_functions = re.findall(
            r"OBELISK_PLUGIN_EXPORT\s+bool\s+(ObeliskPlugin_[A-Za-z0-9_]+)\s*\(",
            audit_source,
        )
        self.assertEqual(exported_functions, ["ObeliskPlugin_GetInfo", "ObeliskPlugin_Init"])
        self.assertIn("OBELISK_PLUGIN_EXPORT\nvoid ObeliskPlugin_Shutdown(void)", audit_source)
        self.assertNotIn("__attribute__((visibility(\"default\")))\nbool", audit_source)

        for token in (
            '\\"enabled\\": false',
            '\\"allow_all_instances\\": false',
            '\\"instance_allowlist\\": []',
            'out->default_config_json = kDefaultConfig',
        ):
            with self.subTest(
                path="examples/sdk_inventory_policy_audit/inventory_policy_audit_plugin.c",
                token=token,
            ):
                self.assertIn(token, audit_source)

        for token in (
            "api->abi_version == OBELISK_API_ABI_VERSION",
            "api->struct_size >= offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +",
            "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
            "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS",
            "api->RegisterGameplayPolicyEventWithOwnerTokenHandle != NULL",
            "api->UnregisterGameplayPolicyEventWithOwnerToken != NULL",
            "api->DescribeGameplayPolicyEventKind != NULL",
            "context->struct_size >= offsetof(ObeliskPluginInitContext, plugin_owner_token) +",
            "context->plugin_owner_token != 0",
            "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
            "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
            "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
            "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
            "RegisterGameplayPolicyEventWithOwnerTokenHandle",
            "UnregisterGameplayPolicyEventWithOwnerToken",
            "atomic_exchange(&g_registration_id, 0)",
        ):
            with self.subTest(
                path="examples/sdk_inventory_policy_audit/inventory_policy_audit_plugin.c",
                token=token,
            ):
                self.assertIn(token, audit_source)

        for text, relative in (
            (audit_readme, "examples/sdk_inventory_policy_audit/README.md"),
            (audit_cmake, "examples/sdk_inventory_policy_audit/CMakeLists.txt"),
            (audit_source, "examples/sdk_inventory_policy_audit/inventory_policy_audit_plugin.c"),
        ):
            with self.subTest(path=relative, check="no-broad-v1-completion-claim"):
                self.assertEqual(broad_v1_completion_claims(text, relative), [])

        self.assertEqual(
            plugin_hub_seed_forbidden_claims(
                audit_readme,
                "examples/sdk_inventory_policy_audit/README.md",
                "experimental pattern",
            ),
            [],
        )

        release_layout_script = (
            REPO_ROOT / "scripts" / "test_install_obelisk_layout.sh"
        ).read_text(encoding="utf-8")
        self.assertNotIn("SDK_INVENTORY_POLICY_AUDIT_EXAMPLE_PLUGIN_PATH", release_layout_script)
        self.assertNotIn("examples/sdk_inventory_policy_audit", release_layout_script)

        for text, relative in (
            (audit_cmake, "examples/sdk_inventory_policy_audit/CMakeLists.txt"),
            (audit_source, "examples/sdk_inventory_policy_audit/inventory_policy_audit_plugin.c"),
        ):
            for token in (
                '#include "',
                "#include <api/",
                "#include <core/",
                "#include <hooks/",
                "#include <plugins/",
                "#include <runtime/",
                "#include <ue/",
                "UObject",
                "UFunction",
                "FString",
                "ProcessEvent",
                "CallProcessEvent",
                "RegisterPreProcessEvent",
                "RegisterPostProcessEvent",
                "RegisterChat",
                "ChatMessageEvent",
                "SendChat",
                "Reply",
                "ArkApi",
                "AseApi",
                "ResourceHandle",
                "GetResource",
                "ResolveResource",
                "player identity",
                "object identity",
                "resource identity",
                "return_override",
            ):
                with self.subTest(path=relative, forbidden=token):
                    self.assertNotIn(token, text)

    def test_sdk_inventory_policy_audit_example_is_not_release_packaged(self) -> None:
        root_cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        installer = (REPO_ROOT / "scripts" / "install_obelisk.sh").read_text(encoding="utf-8")
        release_layout_script = (
            REPO_ROOT / "scripts" / "test_install_obelisk_layout.sh"
        ).read_text(encoding="utf-8")
        audit_cmake = (
            REPO_ROOT / "examples" / "sdk_inventory_policy_audit" / "CMakeLists.txt"
        ).read_text(encoding="utf-8")

        for token in (
            "add_subdirectory(examples/sdk_inventory_policy_audit)",
            "obelisk_sdk_inventory_policy_audit",
            "sdk_inventory_policy_audit",
        ):
            with self.subTest(path="CMakeLists.txt", forbidden=token):
                self.assertNotIn(token, root_cmake)

        for token in (
            "examples/sdk_inventory_policy_audit",
            "obelisk_sdk_inventory_policy_audit",
            "sdk_inventory_policy_audit",
            "SDK_INVENTORY_POLICY_AUDIT_EXAMPLE_PLUGIN_PATH",
        ):
            with self.subTest(path="scripts/install_obelisk.sh", forbidden=token):
                self.assertNotIn(token, installer)
            with self.subTest(path="scripts/test_install_obelisk_layout.sh", forbidden=token):
                self.assertNotIn(token, release_layout_script)

        with self.subTest(path="examples/sdk_inventory_policy_audit/CMakeLists.txt"):
            self.assertNotRegex(audit_cmake, r"\binstall\s*\(")

    def test_installed_sdk_examples_label_package_version_as_prerelease_floor(self) -> None:
        for path in (
            REPO_ROOT / "examples" / "sdk_minimal_plugin" / "README.md",
            REPO_ROOT / "examples" / "sdk_descriptor_catalog" / "README.md",
            REPO_ROOT / "examples" / "sdk_timer_plugin" / "README.md",
            REPO_ROOT / "examples" / "sdk_inventory_policy_audit" / "README.md",
        ):
            compact = normalized(path.read_text(encoding="utf-8"))
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertIn("compatibility floor for the current pre-release SDK line", compact)
                self.assertIn("not a complete SDK claim", compact)
                self.assertIn("not a claim that a stable `v0.1.0` release tag exists", compact)
                self.assertIn("foundation/contributor-readiness sample", compact)
                self.assertIn("not ArkApi portability", compact)
                self.assertIn("not Obelisk SDK v1 evidence", compact)

    def test_installed_sdk_example_support_tiers_are_explicit_and_stable(self) -> None:
        examples_index = (REPO_ROOT / "examples" / "README.md").read_text(encoding="utf-8")

        for example_name, expected_tier in INSTALLED_SDK_EXAMPLE_SUPPORT_TIERS.items():
            readme_path = REPO_ROOT / "examples" / example_name / "README.md"
            readme = readme_path.read_text(encoding="utf-8")
            declarations = plugin_hub_support_tier_declarations(readme)

            with self.subTest(path=readme_path.relative_to(REPO_ROOT), check="single tier"):
                self.assertEqual(declarations, [expected_tier])

            index_row = f"| `{example_name}/` | {expected_tier} |"
            with self.subTest(path="examples/README.md", row=index_row):
                self.assertIn(index_row, examples_index)

        release_supported = {
            name
            for name, tier in INSTALLED_SDK_EXAMPLE_SUPPORT_TIERS.items()
            if tier == "release-supported seed"
        }
        self.assertEqual(
            release_supported,
            {"sdk_minimal_plugin", "sdk_descriptor_catalog", "sdk_timer_plugin"},
        )
        self.assertEqual(
            INSTALLED_SDK_EXAMPLE_SUPPORT_TIERS["sdk_inventory_policy_audit"],
            "experimental pattern",
        )

    def test_installed_sdk_templates_name_current_three_and_no_promises(self) -> None:
        docs = {
            "docs/PLUGIN_HUB_FOUNDATION_V1.md": (
                REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md"
            ).read_text(encoding="utf-8"),
            "docs/PLUGIN_HUB_CAPABILITY_MATRIX.md": (
                REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md"
            ).read_text(encoding="utf-8"),
            "examples/README.md": (REPO_ROOT / "examples" / "README.md").read_text(
                encoding="utf-8"
            ),
        }

        required_phrases = (
            "starter template",
            "descriptor catalog template",
            "owner-token timer template",
            "do not promise",
            "identity",
            "command routing",
            "permissions/admin",
            "replies/send-chat/broadcast",
            "storage",
            "mutation",
            "return override",
            "ArkApi/AseApi",
            "SDK v1 completion",
        )
        for relative, text in docs.items():
            compact = normalized(text)
            with self.subTest(path=relative, check="current templates"):
                self.assertIn("sdk_minimal_plugin", text)
                self.assertIn("sdk_descriptor_catalog", text)
                self.assertIn("sdk_timer_plugin", text)
            for phrase in required_phrases:
                with self.subTest(path=relative, phrase=phrase):
                    self.assertIn(normalized(phrase), compact)

        examples_index = docs["examples/README.md"]
        for example_name, expected_tier in INSTALLED_SDK_EXAMPLE_SUPPORT_TIERS.items():
            with self.subTest(path="examples/README.md", example=example_name):
                self.assertIn(f"| `{example_name}/` | {expected_tier} |", examples_index)

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
            "chat command helper unexpectedly registered ProcessEvent callback",
            "DispatchValidChatMessageEventWithText(\"!help\")",
            "DispatchValidChatMessageEventWithText(\"/help raw-secret\")",
            "Local chat command matched principal=unknown command=help",
            "Local chat command rejected reason=unknown-command principal=unknown command=unknown",
            "chat command helper logged raw command arguments",
            "chat command helper did not reject malformed chat message events",
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

    def test_obaseevents_raw_process_event_guardrail_stays_in_release_tests(self) -> None:
        cmake = (REPO_ROOT / "tests" / "sdk_consumer" / "CMakeLists.txt").read_text(encoding="utf-8")
        fixture = (REPO_ROOT / "tests" / "sdk_consumer" / "SdkConsumerFixture.cpp").read_text(
            encoding="utf-8"
        )

        for token in (
            "SdkConsumerFixtureOBaseEventsActiveProcessEventNoFilteredCapability",
            "SdkConsumerFixtureOBaseEventsActiveProcessEventShortApi",
        ):
            with self.subTest(file="tests/sdk_consumer/CMakeLists.txt", token=token):
                self.assertIn(token, cmake)

        for token in (
            "active-process-event-no-filtered-capability",
            "active-process-event-short-api-before-process-event-handles",
            "oBaseEvents accepted unavailable filtered ProcessEvent handle API",
            "oBaseEvents registered ProcessEvent with unavailable API",
        ):
            with self.subTest(file="tests/sdk_consumer/SdkConsumerFixture.cpp", token=token):
                self.assertIn(token, fixture)

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

    def test_public_register_api_slots_require_owner_token_handle_unregister_and_cleanup(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")
        plugin_manager = (REPO_ROOT / "core" / "PluginManager.cpp").read_text(encoding="utf-8")
        public_fields = obelisk_api_field_names(header)
        public_register_fields = [field for field in public_fields if field.startswith("Register")]
        public_unregister_fields = [field for field in public_fields if field.startswith("Unregister")]

        managed_register_slots: dict[str, dict[str, object]] = {}
        for surface in PUBLIC_SDK_OPTIONAL_API_SURFACES:
            trigger = str(surface["trigger"])
            if not trigger.startswith("Register"):
                continue
            for slot in surface.get("public_register_slots", [trigger]):
                managed_register_slots[str(slot)] = surface

        unmanaged_register_fields = sorted(
            set(public_register_fields)
            - V010_LEGACY_REGISTER_FIELD_EXCEPTIONS
            - set(managed_register_slots)
        )
        self.assertEqual(
            unmanaged_register_fields,
            [],
            "New public Register* slots must be owner-token handle registrations with "
            "an owner-scoped unregister and owner-cleanup guardrail entry.",
        )

        for slot, surface in sorted(managed_register_slots.items()):
            with self.subTest(slot=slot, check="register-slot"):
                self.assertIn(slot, public_fields)
                self.assertIn("WithOwnerTokenHandle", slot)

            unregister_slot = str(surface["terminal_slot"])
            with self.subTest(slot=slot, check="unregister-slot"):
                self.assertIn(unregister_slot, public_fields)
                self.assertIn("WithOwnerToken", unregister_slot)

            cleanup_token = str(surface["owner_cleanup_token"])
            with self.subTest(slot=slot, check="owner-cleanup"):
                self.assertIn(cleanup_token, plugin_manager)

        for field in public_unregister_fields:
            with self.subTest(field=field, check="owner-scoped-unregister"):
                self.assertIn("WithOwnerToken", field)

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

    def test_public_sdk_headers_have_no_raw_ue_public_abi_types(self) -> None:
        forbidden = (
            "UObject",
            "UClass",
            "UFunction",
            "UProperty",
            "FProperty",
            "FName",
            "FString",
            "GNames",
            "GObjects",
            "GUObjectArray",
            "FUObjectArray",
        )
        offenders: list[str] = []

        for path in (REPO_ROOT / "include" / "obelisk").rglob("*"):
            if not path.is_file() or path.suffix not in {".h", ".hpp"}:
                continue
            text = strip_c_comments(path.read_text(encoding="utf-8"))
            for token in forbidden:
                if re.search(rf"\b{re.escape(token)}\b", text):
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

    def test_inventory_copied_signal_field_masks_stay_notification_only(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        gameplay_policy = next(
            (
                event for event in manifest.get("promoted_events", [])
                if isinstance(event, dict) and event.get("event_id") == "obelisk.gameplay_policy.v1"
            ),
            None,
        )
        self.assertIsNotNone(gameplay_policy)
        self.assertEqual(
            gameplay_policy.get("inventory_sdk"),
            "not promoted; inventory-backed policy signals are exposed only through GameplayPolicyEvent",
        )
        self.assertEqual(
            gameplay_policy.get("item_module_sdk"),
            "not promoted; item-return-backed policy signals are exposed only through GameplayPolicyEvent",
        )

        inventory_events = {
            event.get("stable_name"): event
            for event in gameplay_policy.get("event_kinds", [])
            if isinstance(event, dict)
            and event.get("resource_kind") == "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM"
        }
        self.assertEqual(
            inventory_events,
            {
                "inventory.remote_add_check": {
                    "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK",
                    "stable_name": "inventory.remote_add_check",
                    "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                    "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK",
                    "field_mask": [
                        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER",
                    ],
                },
                "inventory.use_check": {
                    "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK",
                    "stable_name": "inventory.use_check",
                    "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                    "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK",
                    "field_mask": [
                        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN",
                    ],
                },
                "inventory_item.allow_equip_check": {
                    "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
                    "stable_name": "inventory_item.allow_equip_check",
                    "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                    "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
                    "field_mask": [
                        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                    ],
                },
                "inventory_item.can_repair_check": {
                    "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK",
                    "stable_name": "inventory_item.can_repair_check",
                    "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                    "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK",
                    "field_mask": [
                        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                    ],
                },
                "inventory_item.use_onto_item_check": {
                    "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
                    "stable_name": "inventory_item.use_onto_item_check",
                    "resource_kind": "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                    "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
                    "field_mask": [
                        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                    ],
                },
            },
        )

        redacted_fields = gameplay_policy.get("redacted_fields", [])
        for redacted in (
            "player identity",
            "inventory object identity",
            "item identity",
            "mutation or return override authority",
        ):
            self.assertIn(redacted, redacted_fields)

    def test_inventory_policy_and_item_return_descriptors_stay_distinct(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        gameplay_policy = next(
            (
                event for event in manifest.get("promoted_events", [])
                if isinstance(event, dict) and event.get("event_id") == "obelisk.gameplay_policy.v1"
            ),
            None,
        )
        self.assertIsNotNone(gameplay_policy)

        inventory_events = {
            event.get("stable_name"): event
            for event in gameplay_policy.get("event_kinds", [])
            if isinstance(event, dict)
            and event.get("resource_kind") == "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM"
        }
        inventory_policy_names = {
            stable_name
            for stable_name in inventory_events
            if isinstance(stable_name, str) and stable_name.startswith("inventory.")
        }
        item_return_names = {
            stable_name
            for stable_name in inventory_events
            if isinstance(stable_name, str) and stable_name.startswith("inventory_item.")
        }

        self.assertEqual(
            inventory_policy_names,
            {
                "inventory.remote_add_check",
                "inventory.use_check",
            },
        )
        self.assertEqual(
            item_return_names,
            {
                "inventory_item.allow_equip_check",
                "inventory_item.can_repair_check",
                "inventory_item.use_onto_item_check",
            },
        )
        self.assertEqual(set(inventory_events), inventory_policy_names | item_return_names)

        self.assertEqual(
            inventory_events["inventory.remote_add_check"].get("field_mask"),
            [
                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER",
            ],
        )
        self.assertEqual(
            inventory_events["inventory.use_check"].get("field_mask"),
            [
                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN",
            ],
        )
        for stable_name in sorted(item_return_names):
            with self.subTest(stable_name=stable_name):
                self.assertEqual(
                    inventory_events[stable_name].get("field_mask"),
                    ["OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE"],
                )

        self.assertEqual(
            gameplay_policy.get("inventory_backing_target_set"),
            "minimal-second-source-intake",
        )
        self.assertEqual(
            gameplay_policy.get("item_return_backing_target_set"),
            "item-return-only-policy-slice",
        )
        self.assertEqual(
            gameplay_policy.get("inventory_sdk"),
            "not promoted; inventory-backed policy signals are exposed only through GameplayPolicyEvent",
        )
        self.assertEqual(
            gameplay_policy.get("item_module_sdk"),
            "not promoted; item-return-backed policy signals are exposed only through GameplayPolicyEvent",
        )

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
                if relative.startswith("tests/sdk_installed_consumer/descriptor_timer_plugin.cpp") and token in CORE_TIMER_EXAMPLE_TOKENS:
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
                if (
                    relative == "tests/sdk_installed_consumer/descriptor_timer_plugin.cpp"
                    and token in CORE_TIMER_EXAMPLE_TOKENS
                ):
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
                if (
                    relative == "tests/sdk_installed_consumer/descriptor_timer_plugin.cpp"
                    and token in CORE_TIMER_EXAMPLE_TOKENS
                ):
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
            "Permissions/admin query checks",
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
            "Lifecycle, descriptors, logging, config, local timers": "parked release-supported seed after SDK completion",
            "Passive chat parsing and plugin-local text routing": "experimental seed only",
            "Copied structure/item policy auditing": "experimental seed only",
            "Timed notices and chat broadcasts": "blocked",
            "Permissions/admin query checks": "blocked",
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
            "The `Foundation V1` label means the first reviewed foundation/intake contract revision for contributor readiness",
            "it is not Obelisk SDK v1, `v1.0 stable`, or a Plugin Hub completion claim",
            "`parked release-supported seed after SDK completion`: future support tier for scoped Obelisk-native examples",
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
            "v0.1 copied-data ABI surface; experimental Plugin Hub seed, not v1-complete",
            "it does not turn copied chat/policy examples into production Plugin Hub modules",
            "Dependency-order note only, not an immediate next public slice",
            "groups, grants, admin actions, storage, RCON, and operator reload stay excluded",
        ):
            with self.subTest(required=required):
                self.assertIn(required, compact)

    def test_plugin_hub_release_seed_and_blocked_dependency_boundary_is_explicit(self) -> None:
        docs = {
            "contributor_path": REPO_ROOT / "docs" / "PLUGIN_HUB_CONTRIBUTOR_PATH.md",
            "foundation": REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
            "matrix": REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
        }
        compacts = {
            name: normalized(path.read_text(encoding="utf-8")) for name, path in docs.items()
        }

        shared_required = (
            "lifecycle/config/logging",
            "descriptor/catalog",
            "process-local timer",
            "Passive copied chat parsing",
            "copied policy auditing",
            "experimental examples only",
            "Permissions/admin",
            "commands/replies/send-chat/broadcast",
            "economy, kits, homes, teleport, and item grants",
            "identity/principal",
            "permissions/admin",
            "command routing",
            "response path",
            "persistence/storage",
            "safe mutation/grant surfaces",
        )
        for name, compact in compacts.items():
            for phrase in shared_required:
                with self.subTest(file=name, phrase=phrase):
                    self.assertIn(normalized(phrase), compact)

        matrix = compacts["matrix"]
        for required in (
            "Owner-token timers exist, but public response path, send-chat/broadcast policy, command routing, permissions/admin, persistence, and cross-process scheduling are not promoted",
            "query-only authorization requires copied identity/principal plus permissions/admin policy first",
            "Needs identity/principal, permissions/admin, command routing, response path, persistence/storage, item grant/mutation, and event evidence",
            "Needs location/area data, identity/principal, permissions/admin, command routing, response path",
            "Needs player/inventory/item identity, permissions/admin where gated, command routing and response path where user-triggered, item grant/mutation APIs",
            "The common blocked chain is identity/principal -> permissions/admin -> command routing -> response path",
        ):
            with self.subTest(matrix_required=required):
                self.assertIn(normalized(required), matrix)

    def test_plugin_hub_v1_contributor_intake_boundary_is_consistent(self) -> None:
        docs = {
            "contributor_path": REPO_ROOT / "docs" / "PLUGIN_HUB_CONTRIBUTOR_PATH.md",
            "foundation": REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
            "matrix": REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
            "roadmap": REPO_ROOT / "docs" / "research" / "2026-05-29-module-surface-roadmap.md",
            "research_readme": REPO_ROOT / "docs" / "research" / "README.md",
        }
        texts = {name: path.read_text(encoding="utf-8") for name, path in docs.items()}
        compacts = {name: normalized(text) for name, text in texts.items()}

        required = {
            "contributor_path": (
                "## 1. Decide The Tier",
                "`release-supported seed`",
                "`experimental pattern`",
                "`blocked backlog`",
                "Names from ArkApi, AseApi, or popular plugin families can justify demand notes",
                "they do not change the tier and must not be copied as implementation patterns",
            ),
            "foundation": (
                "## Contributor Intake Checklist",
                "Parked release-supported seed after SDK completion",
                "Experimental pattern only",
                "Blocked backlog",
                "ArkApi/AseApi/NextGenPlugins demand can justify keeping a blocked idea visible",
                "but it cannot reclassify that idea as a release-supported seed or experimental pattern",
            ),
            "matrix": (
                "## Foundation-To-Roadmap Alignment",
                "`hub foundation` means release-supported seed work",
                "`gameplay policy backing` means preserving evidence and tests for already promoted",
                "`internal recognizer planning` means docs, fixtures, and offline copied-bool planning",
                "only a named promotion gate can move a row's support tier",
            ),
            "roadmap": (
                "Roadmap-to-Plugin-Hub alignment for contributors",
                "`hub foundation` is the only release-supported seed lane now",
                "`gameplay policy backing` protects the existing copied/redacted `GameplayPolicyEvent`",
                "`internal recognizer planning` stays offline/test-only",
                "append-only ABI/consumer-test plan",
            ),
            "research_readme": (
                "Plugin Hub contributor intake uses the same three buckets as the public matrix",
                "release-supported seed now for lifecycle/config/logging, descriptor/catalog, timer, packaging",
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
        for name in ("contributor_path", "foundation", "matrix", "roadmap", "research_readme"):
            compact = compacts[name]
            with self.subTest(file=name, item="blocked dependency vocabulary"):
                for term in blocked_dependency_terms:
                    self.assertIn(term.lower(), compact.lower())

    def test_public_contributor_docs_route_plugin_hub_through_foundation_and_matrix(self) -> None:
        required_phrases = {
            REPO_ROOT / "README.md": (
                "Plugin Hub work is deferred until the complete SDK contract is closed",
                "docs/PLUGIN_HUB_FOUNDATION_V1.md",
                "docs/PLUGIN_HUB_CAPABILITY_MATRIX.md",
                "Finish the SDK blocker chain first",
            ),
            REPO_ROOT / "CONTRIBUTING.md": (
                "Treat Plugin Hub as post-SDK-complete planning",
                "Do not start new Plugin Hub examples",
                "ArkServerApi,\n  AseApi, and NextGenPlugins are names, demand, conceptual architecture, and migration",
                "not sources for code, offsets, control flow, parsers,\n  schemas, or implementation behavior",
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
                "Plugin Hub work is deferred until the complete SDK contract is closed",
                "post-SDK planning boundaries",
                "They must not drive current prioritization",
                "Finish the SDK blocker chain first",
            ),
            REPO_ROOT / "CONTRIBUTING.md": (
                "Treat Plugin Hub as post-SDK-complete planning",
                "Do not start new Plugin Hub examples",
                "ArkServerApi,\n  AseApi, and NextGenPlugins are names, demand, conceptual architecture, and migration",
                "not sources for code, offsets, control flow, parsers,\n  schemas, or implementation behavior",
            ),
            REPO_ROOT / "docs" / "PLUGIN_HUB_CONTRIBUTOR_PATH.md": (
                "Status: post-SDK-complete planning only",
                "This path is parked until Obelisk has a complete SDK contract",
                "`release-supported seed`: lifecycle/config/logging, descriptor/catalog reads, or\n  process-local timers",
                "`experimental pattern`: passive copied `ChatMessageEvent` parsing or copied\n  `GameplayPolicyEvent` auditing",
                "`blocked backlog`: anything that needs commands, replies, send-chat, permissions,\n  identity",
                "Do not start from `plugins/` when writing the starter external package",
                "Stop at experimental pattern when the example passively observes copied chat or policy\ndata",
                "Plugin Hub foundation examples help contributors learn the current C ABI",
                "They do not\ndeclare a complete v1 SDK",
            ),
            REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md": (
                "Status: post-SDK-complete planning only",
                "Do not treat this document as active roadmap work",
                "When Plugin Hub resumes after SDK completion",
                "Copied `ChatMessageEvent` parsing and copied `GameplayPolicyEvent` auditing remain experimental seed patterns only",
                "Foundation V1 defines honest future Plugin Hub seeds after the SDK blocker chain is\nclosed",
                "process-local timer utilities",
                "This list names ABI primitives, not Plugin Hub module tiers",
                "Experimental pattern examples only:",
                "copied `GameplayPolicyEvent` auditors",
                "Keep passive copied chat parsing experimental and plugin-local only",
                "Keep copied policy auditors experimental",
                "Foundation V1 does not provide or imply",
            ),
            REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md": (
                "Status: post-SDK-complete planning only",
                "Plugin Hub seed work resumes after SDK completion",
                "`experimental seed only`: allowed for explicitly labeled pattern examples",
                "not supported as production Plugin Hub modules",
                "keep the support tier explicit",
                "Release-supported seed lanes",
                "Experimental pattern examples only",
            ),
            REPO_ROOT / "plugins" / "README.md": (
                "The release-supported additions after `v0.1` are descriptor readers and process-local timer utilities",
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
            r"\brelease-supported\b[^.!?\n;]*(?:copied[- ]chat|copied\s+policy|"
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

    def test_plugin_hub_public_docs_do_not_claim_blocked_surfaces_or_v1_completion(self) -> None:
        docs = (
            REPO_ROOT / "docs" / "PLUGIN_HUB_CONTRIBUTOR_PATH.md",
            REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md",
            REPO_ROOT / "docs" / "PLUGIN_HUB_CAPABILITY_MATRIX.md",
        )

        offenders: list[str] = []
        for path in docs:
            offenders.extend(
                plugin_hub_public_doc_forbidden_claims(
                    path.read_text(encoding="utf-8"),
                    path.relative_to(REPO_ROOT).as_posix(),
                )
            )

        self.assertEqual(offenders, [])

        bad_claims = """
        Plugin Hub supports ArkApi compatible command routing and permissions.
        The Inventory SDK is available with sender identity, storage, and economy support.
        Foundation examples provide a complete v1 SDK.
        """
        bad_offenders = plugin_hub_public_doc_forbidden_claims(
            bad_claims,
            "docs/PLUGIN_HUB_FOUNDATION_V1.md",
        )

        self.assertGreaterEqual(len(bad_offenders), 3)
        self.assertTrue(any("ArkApi compatible command routing" in offender for offender in bad_offenders))
        self.assertTrue(any("Inventory SDK is available" in offender for offender in bad_offenders))
        self.assertTrue(any("complete v1 SDK" in offender for offender in bad_offenders))

    def test_plugin_hub_seed_review_files_declare_one_tier_and_no_blocked_claims(self) -> None:
        offenders: list[str] = []

        for path in plugin_hub_seed_review_files():
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(REPO_ROOT).as_posix()
            if path == PLUGIN_HUB_PACKAGE_TEMPLATE_DOC:
                expected_placeholder = (
                    "Support tier: <release-supported seed | experimental pattern | blocked backlog>"
                )
                if expected_placeholder not in text:
                    offenders.append(f"{relative}: missing Plugin Hub support tier placeholder")
                    continue
                offenders.extend(
                    plugin_hub_seed_forbidden_claims(
                        text,
                        relative,
                        "release-supported seed",
                    )
                )
                continue

            declarations = plugin_hub_support_tier_declarations(text)
            if len(declarations) != 1:
                offenders.append(
                    f"{relative}: expected exactly one Support tier declaration, got {declarations}"
                )
                continue
            if declarations[0] not in PLUGIN_HUB_SUPPORT_TIERS:
                offenders.append(f"{relative}: unsupported Plugin Hub support tier {declarations[0]}")
                continue

            offenders.extend(
                plugin_hub_seed_forbidden_claims(
                    text,
                    relative,
                    declarations[0],
                )
            )

        self.assertEqual(offenders, [])

    def test_plugin_hub_seed_review_guardrail_catches_bad_tiers_and_claims(self) -> None:
        bad_tiers = """
        Support tier: release-supported seed.
        support_tier = "experimental pattern"
        """
        self.assertEqual(
            plugin_hub_support_tier_declarations(bad_tiers),
            ["release-supported seed", "experimental pattern"],
        )

        bad_claims = """
        Support tier: release-supported seed.
        This package supports v1 SDK compatibility for plugin authors.
        It is ArkApi compatible and provides command routing with permissions.
        It exposes sender identity, send-chat replies, mutation, storage, inventory,
        and structure support.
        """
        offenders = plugin_hub_seed_forbidden_claims(
            bad_claims,
            "candidate/README.md",
            "release-supported seed",
        )

        self.assertGreaterEqual(len(offenders), 3)
        self.assertTrue(any("v1 SDK compatibility" in offender for offender in offenders))
        self.assertTrue(any("ArkApi compatible" in offender for offender in offenders))
        self.assertTrue(any("structure support" in offender for offender in offenders))

    def test_plugin_hub_seed_review_discovers_package_metadata_without_readme(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "examples",
            prefix="plugin_hub_metadata_guardrail_",
        ) as temp_dir:
            metadata_path = Path(temp_dir) / "plugin.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "plugin_id": "example.metadata_only_seed",
                        "support_tier": "release-supported seed",
                        "description": "Supports ArkApi compatible command routing.",
                    }
                ),
                encoding="utf-8",
            )

            review_paths = {path.resolve() for path in plugin_hub_seed_review_files()}
            self.assertIn(metadata_path.resolve(), review_paths)

            text = metadata_path.read_text(encoding="utf-8")
            declarations = plugin_hub_support_tier_declarations(text)
            self.assertEqual(declarations, ["release-supported seed"])
            offenders = plugin_hub_seed_forbidden_claims(
                text,
                metadata_path.relative_to(REPO_ROOT).as_posix(),
                declarations[0],
            )

        self.assertTrue(any("ArkApi compatible command routing" in offender for offender in offenders))

    def test_plugin_hub_descriptor_catalog_seed_wording_stays_scaffolded_not_prebuilt(self) -> None:
        contributor_path = (
            REPO_ROOT / "docs" / "PLUGIN_HUB_CONTRIBUTOR_PATH.md"
        ).read_text(encoding="utf-8")
        foundation = (REPO_ROOT / "docs" / "PLUGIN_HUB_FOUNDATION_V1.md").read_text(
            encoding="utf-8"
        )
        minimal_readme = (
            REPO_ROOT / "examples" / "sdk_minimal_plugin" / "README.md"
        ).read_text(encoding="utf-8")
        timer_readme = (
            REPO_ROOT / "examples" / "sdk_timer_plugin" / "README.md"
        ).read_text(encoding="utf-8")
        descriptor_readme = (
            REPO_ROOT / "examples" / "sdk_descriptor_catalog" / "README.md"
        ).read_text(encoding="utf-8")

        for text, required in (
            (
                contributor_path,
                "copy `examples/sdk_descriptor_catalog` for descriptor/catalog readers",
            ),
            (
                contributor_path,
                "Use `plugins/oDescriptorCatalog` as a behavior reference for descriptor validation and\nbounded logging, not as the external package scaffold",
            ),
            (
                contributor_path,
                "Do not start from `plugins/` when writing the starter external package",
            ),
            (
                foundation,
                "First-party runtime reference plugins live under\n`plugins/` and may use repository-local build/test wiring",
            ),
            (
                foundation,
                "This list names ABI primitives, not Plugin Hub module tiers",
            ),
        ):
            with self.subTest(required=required):
                self.assertIn(normalized(required), normalized(text))

        combined_examples = f"{minimal_readme}\n{timer_readme}"
        for forbidden in (
            "Descriptor Catalog SDK Plugin",
            "DescribeResourceKind",
            "DescribeGameplayPolicyEventKind",
            "oDescriptorCatalog",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, combined_examples)

        for required in (
            "Support tier: release-supported seed.",
            "DescribeResourceKind",
            "DescribeGameplayPolicyEventKind",
            "metadata-only descriptor discovery",
            "not identity, lookup handles",
            "does not use private headers, raw UE pointers, `ProcessEvent`",
        ):
            with self.subTest(required=required):
                self.assertIn(normalized(required), normalized(descriptor_readme))

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
            "economy",
            "homes",
            "teleport",
            "safe zones",
            "mobility",
        )
        focused_lane_terms = (
            "chat",
            "ResourceHandle",
            "APrimalStructure.IsAllowedToBuild",
        )

        for path, text in (
            ("docs/research/2026-05-30-v1-core-capability-map.md", v1_map),
            ("docs/research/README.md", research_readme),
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
        matrix_compact = normalized(matrix)
        matrix_lower = matrix_compact.lower()
        with self.subTest(file="docs/PLUGIN_HUB_CAPABILITY_MATRIX.md", item="broad surface terms"):
            for term in broad_surface_terms:
                self.assertIn(term, matrix_lower)
        with self.subTest(file="docs/PLUGIN_HUB_CAPABILITY_MATRIX.md", item="generic build placement lane"):
            self.assertIn("Structure build placement policy", matrix_compact)
            self.assertIn("Ark-style build placement compatibility", matrix_compact)
            self.assertNotIn("PrimalStructure.IsAllowedToBuild", matrix_compact)
            self.assertNotIn("APrimalStructure.IsAllowedToBuild", matrix_compact)
        with self.subTest(file="docs/PLUGIN_HUB_CAPABILITY_MATRIX.md", item="no SDK promise from breadth"):
            self.assertRegex(
                matrix_lower,
                r"not (?:a )?(?:delivery |sdk )?promise|not .* sdk promise|no public sdk|not ready",
            )

    def test_plugin_hub_blocked_module_families_stay_unpromoted(self) -> None:
        v1_map = (
            REPO_ROOT / "docs" / "research" / "2026-05-30-v1-core-capability-map.md"
        ).read_text(encoding="utf-8")
        compact_v1_map = normalized(v1_map)

        for required in (
            "Promotion gate before any v1 surface",
            "records hypotheses and required evidence, not production support for permissions, RCON, economy, homes, teleport, safe zones, mobility, storage, tribes, dinos, transfers, inventory, commands",
        ):
            with self.subTest(required=required):
                self.assertIn(normalized(required), compact_v1_map)
        self.assertNotIn("v1 core need", compact_v1_map)

        blocked_family = (
            r"permissions?|RCON|economy|shops?|kits?|storage|database|webhook|"
            r"rewards?|stats|homes?|teleports?|safe[- ]zones?|area\s+polic(?:y|ies)|"
            r"mobility|player\s+services?|broadcasts?|timed\s+notices?|"
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

    def test_player_identity_static_orientation_json_stays_candidate_blocked(self) -> None:
        note_path = REPO_ROOT / "docs" / "research" / "2026-05-31-player-identity-static-target-orientation.md"
        manifest_path = REPO_ROOT / "docs" / "research" / "2026-05-31-player-identity-static-target-orientation.json"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema"], "obelisk.player-identity-static-target-orientation.v1")
        self.assertEqual(payload["artifact_identity"]["source_note"], str(note_path.relative_to(REPO_ROOT)))
        self.assertEqual(
            payload["artifact_identity"]["source_note_sha256"],
            hashlib.sha256(note_path.read_bytes()).hexdigest(),
        )
        self.assertRegex(payload["scope"]["binary_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("address_convention", payload["scope"])
        self.assertEqual(payload["scope"]["target_set"], "players-identity-lifecycle-intake")
        self.assertEqual(payload["gate"]["mode"], "consume")
        self.assertEqual(payload["gate"]["status"], "candidate_blocked")
        self.assertIs(payload["gate"]["promotion_ready"], False)

        expected_targets = {
            target.split(":", 1)[1]
            for target in TARGET_SETS["players-identity-lifecycle-intake"]
        }
        observed_targets = {candidate["target"] for candidate in payload["candidates"]}
        self.assertEqual(observed_targets, expected_targets)
        forbidden_tokens = re.compile(
            r"\b(?:accepted|callback|identity_resolved|mutation|promoted|public_sdk|"
            r"resource_handle|return_override|runtime_observed)\b",
            re.IGNORECASE,
        )
        for candidate in payload["candidates"]:
            with self.subTest(target=candidate["target"]):
                self.assertEqual(candidate["kind"], "ufunction_static_orientation")
                self.assertEqual(candidate["status"], "candidate_only")
                self.assertIn(candidate["confidence"], {"candidate", "clue"})
                self.assertRegex(candidate["class_slot"], r"^0x[0-9a-f]+$")
                self.assertEqual(candidate["registrar_call_vma"], "0x1ccc140")
                self.assertRegex(candidate["registration_vma"], r"^0x[0-9a-f]+$")
                self.assertIn(candidate["registration_vma"], candidate["xref_vmas"])
                self.assertRegex(candidate["string_vma"], r"^0x[0-9a-f]+$")
                self.assertGreaterEqual(len(candidate["xref_vmas"]), 1)
                self.assertGreaterEqual(len(candidate["thunk_candidates"]), 1)
                self.assertIsNone(forbidden_tokens.search(json.dumps(candidate, sort_keys=True)))

        for non_claim in (
            "does_not_prove_ufunction_object_identity",
            "does_not_prove_property_chain_or_param_offsets",
            "does_not_promote_public_sdk",
            "does_not_promote_public_callbacks_or_observers",
            "does_not_authorize_runtime_observation_or_server_probe",
            "does_not_promote_runtime_identity",
            "does_not_promote_permissions_or_commands",
            "does_not_prove_player_principal_mapping",
            "does_not_prove_controller_or_playerstate_lifetime",
            "does_not_prove_privacy_safe_identity_surface",
            "does_not_promote_object_lookup_or_raw_ue_pointer_exposure",
            "does_not_promote_lifecycle_anchor_acceptance",
            "does_not_promote_resource_handle",
            "does_not_promote_mutation",
            "does_not_promote_return_override",
            "does_not_claim_login_logout_lifecycle",
            "does_not_satisfy_core_evidence_pack_or_reflection_inventory_pack",
        ):
            with self.subTest(non_claim=non_claim):
                self.assertIn(non_claim, payload["non_claims"])

        for blocker in (
            "requires_non_protected_core_evidence_pack",
            "requires_full_reflection_inventory_pack_for_players_identity_lifecycle_intake",
            "requires_exact_focal_snapshots_for_ServerListPlayers_and_ServerKickPlayer",
            "requires_principal_privacy_and_invalidation_policy_before_public_sdk_promotion",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, payload["blockers"])

    def test_static_orientation_and_command_chat_schemas_are_not_artifact_gate_or_v1_promotion_evidence(self) -> None:
        scripts_dir = REPO_ROOT / "scripts"
        original_sys_path = list(sys.path)
        sys.path.insert(0, str(scripts_dir))
        try:
            gate = runpy.run_path(
                str(scripts_dir / "validate_offline_artifact_gate.py"),
                run_name="__not_main__",
            )
        finally:
            sys.path[:] = original_sys_path
        checker = runpy.run_path(
            str(scripts_dir / "check_public_sdk_v1_completion.py"),
            run_name="__not_main__",
        )

        schemas = (
            "obelisk.command-chat-response-static-orientation-check.v1",
            "obelisk.radare2-static-orientation-windows.v1",
            "obelisk.player-identity-static-target-orientation.v1",
            "obelisk.player-identity-static-orientation-check.v1",
            "obelisk.player-identity-static-lifecycle-orientation-check.v1",
            "obelisk.player-identity-static-admin-thunks-check.v1",
            "obelisk.static-candidate-orientation-contract.v1",
            "obelisk.native-ufunction-registration-static-discovery.v1",
        )
        for schema in schemas:
            with self.subTest(schema=schema, gate="offline artifact"):
                self.assertNotIn(schema, gate["SUPPORTED_MANIFEST_SCHEMAS"])
            with self.subTest(schema=schema, gate="public sdk v1 promotion evidence"):
                self.assertTrue(
                    checker["evidence_has_non_promotional_schema_marker"](
                        {
                            "schemas": [schema],
                            "promotion_status": "promoted",
                            "public_sdk_ready": True,
                        }
                    )
                )
        self.assertIn(
            "obelisk.players-identity-principal-invalidation-policy.v1",
            gate["SUPPORTED_MANIFEST_SCHEMAS"],
        )
        self.assertTrue(
            checker["evidence_has_non_promotional_schema_marker"](
                {
                    "schemas": ["obelisk.players-identity-principal-invalidation-policy.v1"],
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                }
            )
        )

        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="CommandChatResponsePathPromotion",
            ) as command_core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="command_chat_response_path_promotion",
            ) as command_sdk_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as identity_core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as identity_sdk_dir,
        ):
            command_core_test = Path(command_core_dir) / "CommandChatResponsePathPromotionTests.cpp"
            command_sdk_test = Path(command_sdk_dir) / "command_chat_response_path_promotion_plugin.c"
            identity_core_test = Path(identity_core_dir) / "PlayerIdentityPromotionTests.cpp"
            identity_sdk_test = Path(identity_sdk_dir) / "player_identity_promotion_plugin.c"
            for path in (command_core_test, command_sdk_test, identity_core_test, identity_sdk_test):
                path.write_text("// synthetic promotion evidence fixture\n", encoding="utf-8")

            base_evidence_by_surface = {
                "obelisk.command_chat_response_path.v1": {
                    "surface_id": "obelisk.command_chat_response_path.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": [str(command_core_test.relative_to(REPO_ROOT))],
                    "sdk_consumer_tests": [str(command_sdk_test.relative_to(REPO_ROOT))],
                },
                "obelisk.player_identity.v1": {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": [str(identity_core_test.relative_to(REPO_ROOT))],
                    "sdk_consumer_tests": [str(identity_sdk_test.relative_to(REPO_ROOT))],
                },
            }
            for surface_id, base_evidence in base_evidence_by_surface.items():
                with self.subTest(surface=surface_id, schema="none"):
                    self.assertTrue(
                        checker["surface_has_promotion_evidence"](
                            {"id": surface_id, "evidence": base_evidence}
                        )
                    )
                for schema in schemas:
                    evidence = {**base_evidence, "schemas": [schema]}
                    with self.subTest(surface=surface_id, schema=schema):
                        self.assertFalse(
                            checker["surface_has_promotion_evidence"](
                                {"id": surface_id, "evidence": evidence}
                            )
                        )

    def test_latest_v1_sdk_round_note_does_not_imply_public_or_runtime_promotion(self) -> None:
        note = LATEST_V1_SDK_ROUND_RESEARCH_NOTE.read_text(encoding="utf-8")
        readme = RESEARCH_MODULE_BOUNDARY_README.read_text(encoding="utf-8")
        compact = normalized(note)

        self.assertIn(LATEST_V1_SDK_ROUND_RESEARCH_NOTE.name, readme)
        self.assertEqual(
            broad_v1_completion_claims(
                note,
                str(LATEST_V1_SDK_ROUND_RESEARCH_NOTE.relative_to(REPO_ROOT)),
            ),
            [],
        )
        self.assertEqual(
            experimental_event_v1_completion_claims(
                note,
                str(LATEST_V1_SDK_ROUND_RESEARCH_NOTE.relative_to(REPO_ROOT)),
            ),
            [],
        )
        self.assertEqual(
            positive_chat_message_event_claims(
                note,
                str(LATEST_V1_SDK_ROUND_RESEARCH_NOTE.relative_to(REPO_ROOT)),
            ),
            [],
        )

        required_boundaries = (
            "v1 completion gate remains blocked by design",
            "copied `GameplayPolicyEvent` plus `ChatMessageEvent` seeds do\nnot satisfy a complete SDK claim",
            "No agent touched `/servidor/ark`, Discord, GitHub publication, or live servers",
            "`promotion_ready`,\n  `public_sdk_ready`, and `runtime_ready` must stay false",
            "Fail closed if any input resolves under `/servidor/ark`",
            "any player identifier/raw UE/FName/GObjects/pointer\nfield is copied into public or logged output",
            "These names are not evidence of SDK readiness or runtime safety",
        )
        for boundary in required_boundaries:
            with self.subTest(boundary=boundary):
                self.assertIn(normalized(boundary), compact)

        forbidden_positive_claims = (
            r"\bpublic\s+player\s+identity\s+(?:is|are|has\s+been)\s+"
            r"(?:available|promoted|ready|supported)\b",
            r"\b(?:promote|promoted|promotes|ship|shipped|ships|support|supported|supports)\s+"
            r"(?:public\s+)?player\s+identity\b",
            r"\b(?:public\s+)?commands?\s+(?:SDKs?|APIs?|routers?|surfaces?)\s+"
            r"(?:is|are|has\s+been)\s+(?:available|promoted|public|ready|supported)\b",
            r"\b(?:promote|promoted|promotes|ship|shipped|ships|support|supported|supports)\s+"
            r"(?:public\s+)?commands?\s+(?:SDKs?|APIs?|routers?|surfaces?)\b",
            r"\bResourceHandle(?:\s+(?:SDKs?|APIs?|surfaces?))?\s+"
            r"(?:is|are|has\s+been)\s+(?:available|promoted|public|ready|supported)\b",
            r"\b(?:promote|promoted|promotes|ship|shipped|ships|support|supported|supports)\s+"
            r"(?:public\s+)?ResourceHandle(?:\s+(?:SDKs?|APIs?|surfaces?))?\b",
            r"\b(?:runtime|live[- ]server|server[- ]backed)\s+"
            r"(?:approval|observation|validation|work)\s+(?:is|was|has\s+been)\s+"
            r"(?:approved|authorized|available|ready)\b",
        )
        offenders: list[str] = []
        for line, segment in sentence_like_segments(note):
            for pattern in forbidden_positive_claims:
                if re.search(pattern, segment, flags=re.IGNORECASE):
                    offenders.append(
                        f"{LATEST_V1_SDK_ROUND_RESEARCH_NOTE.relative_to(REPO_ROOT)}:{line}: "
                        f"{normalized(segment)}"
                    )
                    break

        self.assertEqual(offenders, [])

    def test_route_confidence_readiness_checkers_are_covered_by_run_script_tests(self) -> None:
        run_script_tests = (REPO_ROOT / "scripts" / "run_script_tests.sh").read_text(encoding="utf-8")
        self.assertIn("list_repo_files 'scripts/test_*.py'", run_script_tests)
        self.assertIn('for test_path in "${python_tests[@]}"; do', run_script_tests)
        self.assertIn('python3 "${test_path}"', run_script_tests)

        scripts_dir = REPO_ROOT / "scripts"
        readiness_checkers = sorted(scripts_dir.glob("check_*readiness*.py"))
        readiness_adjacent_checkers = [
            scripts_dir / "check_player_identity_static_orientation.py",
            scripts_dir / "check_player_identity_static_lifecycle_orientation.py",
        ]
        required_checkers = readiness_checkers + readiness_adjacent_checkers
        self.assertIn(scripts_dir / "check_player_identity_first_evidence_readiness.py", required_checkers)
        self.assertIn(scripts_dir / "check_player_identity_static_orientation.py", required_checkers)
        self.assertIn(scripts_dir / "check_player_identity_static_lifecycle_orientation.py", required_checkers)

        test_files = {path.name for path in scripts_dir.glob("test_*.py")}
        missing_tests = [
            f"{checker.name} -> test_{checker.name}"
            for checker in required_checkers
            if f"test_{checker.name}" not in test_files
        ]
        self.assertEqual(missing_tests, [])

    def test_player_identity_current_route_records_completed_admin_snapshots_and_remaining_blockers(self) -> None:
        current_path = REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md"
        readme_path = REPO_ROOT / "docs" / "research" / "README.md"
        preflight_path = (
            REPO_ROOT
            / "docs"
            / "research"
            / "2026-05-31-player-identity-offline-pack-preflight.md"
        )
        docs = {
            "handoff": normalized(current_path.read_text(encoding="utf-8")),
            "research_readme": normalized(readme_path.read_text(encoding="utf-8")),
            "preflight": normalized(preflight_path.read_text(encoding="utf-8")),
        }

        shared_terms = (
            "obelisk.reflection-inventory-pack.v1",
            "non-protected",
            "ShooterPlayerController.ServerListPlayers",
            "ShooterPlayerController.ServerKickPlayer",
        )
        for name, text in docs.items():
            for term in shared_terms:
                with self.subTest(doc=name, term=term):
                    self.assertIn(normalized(term), text)

        for term in (
            "lifecycle-anchor schema/target-set and principal\n  invalidation policy still need a reviewed gate",
            "complete `obelisk.core-dump-evidence-pack.v1`",
            "accepted `obelisk.reflection-inventory-pack.v1`",
            "12/12 candidate fixtures",
            "accepted distinct second-source layout\n  evidence from the vanilla-gdb core",
            "Do not rerun the completed admin snapshot, second-source layout, or lifecycle layout routes",
        ):
            with self.subTest(doc="handoff", term=term):
                self.assertIn(normalized(term), docs["handoff"])

        for term in (
            "completed admin snapshot route",
            "target_set_coverage` for the full 12-target `players-identity-lifecycle-intake` set",
            "Do not treat ScriptStruct inventory, standalone snapshots, redacted signatures, static thunks, or a two-function-only inventory as satisfying this lane",
        ):
            with self.subTest(doc="preflight", term=term):
                self.assertIn(normalized(term), docs["preflight"])

    def test_mission_copied_bool_priority_records_offline_blockers_not_public_sdk(self) -> None:
        note = (REPO_ROOT / "docs" / "research" / "2026-05-31-v02-module-priority.md").read_text(
            encoding="utf-8"
        )
        compact = normalized(note)
        docs = {
            "handoff": normalized(
                (REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md").read_text(
                    encoding="utf-8"
                )
            ),
            "preflight": normalized(
                (
                    REPO_ROOT
                    / "docs"
                    / "research"
                    / "2026-05-31-player-identity-offline-pack-preflight.md"
                ).read_text(encoding="utf-8")
            ),
        }

        for term in (
            "Offline Evidence Refresh",
            "`targets=3`",
            "`comparable=3`",
            "`second_source_missing=3`",
            "`promotion_gate.ready=false`",
            "`signature_count=3`",
            "`copied_scalar_count_total=5`",
            "`redacted_count_total=4`",
            "`redacted_by_reason.object_ref=4`",
            "not ready\nfor release readiness, public Mission SDK, runtime observer wiring, or installed SDK\nconsumer exposure",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compact)

        for term in (
            "lifecycle-anchor and principal-invalidation candidate manifests can now be consumed together",
            "the next blocker is approved runtime principal lifecycle evidence",
            "Do not\n  rerun the completed admin snapshot, second-source layout, or lifecycle layout routes",
            "Current recipe:\n  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`",
        ):
            with self.subTest(doc="handoff", term=term):
                self.assertIn(normalized(term), docs["handoff"])

        for term in (
            "does not reread a core",
            "execute snapshot commands",
            "promote identity",
            "authorize runtime work",
            "create a public SDK surface",
            "artifact_pack_container_not_reflection_inventory",
            "scriptstruct_pack_not_reflection_inventory",
            "does not currently contain a non-protected `obelisk.core-dump-evidence-pack.v1` manifest",
            "safe inventory-build route",
            "full 12-target\n`players-identity-lifecycle-intake` set",
            "Do not build a two-function-only reflection\ninventory pack",
            "`second_source_evidence_missing`",
            "`accepted_lifecycle_anchors_missing`",
            "fixture\ncoverage cannot be mistaken for player identity readiness",
            "check_player_identity_first_evidence_readiness.py",
            "fixture_coverage.comparable=12",
            "fixture_coverage.second_source_missing=0",
            "second_source_accepted=12",
            "planning_layout_gate.ready=true",
            "first_evidence.ready=false",
            "primary_blocker=accepted_lifecycle_anchor_evidence_missing",
            "candidate anchors from static orientation are `ShooterGameMode.HandleNewPlayer`",
            "Even with the admin snapshots now present",
            "completed admin snapshots close only the admin-surface fixture gap",
        ):
            with self.subTest(doc="preflight", term=term):
                self.assertIn(normalized(term), docs["preflight"])

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
        self.assertIn("command-chat-response-route-planning", PLANNING_ONLY_TARGET_SETS)
        self.assertIn("players-identity-lifecycle-intake", PLANNING_ONLY_TARGET_SETS)
        self.assertIn("structure-aggregate-census-planning", PLANNING_ONLY_TARGET_SETS)
        self.assertEqual(sorted(set(PLANNING_ONLY_TARGET_SETS) & public_manifest_sets), [])
        self.assertEqual(sorted(set(PLANNING_ONLY_TARGET_SETS) & public_target_sets), [])

        mention_context_re = re.compile(
            r"\b(?:blocked|candidate-only|guidance-only|internal|not\s+(?:a\s+)?public|planning-only|rejected)\b",
            re.IGNORECASE,
        )
        offenders: list[str] = []
        planning_only_target_sets = sorted(PLANNING_ONLY_TARGET_SETS)
        for path in PUBLIC_SDK_GUIDANCE_DOC_FILES:
            for paragraph in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
                if not any(target_set in paragraph for target_set in planning_only_target_sets):
                    continue
                if not mention_context_re.search(normalized(paragraph)):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {normalized(paragraph)}")

        self.assertEqual(offenders, [])

    def test_command_chat_response_route_planning_stays_out_of_release_and_public_claims(self) -> None:
        target_set = "command-chat-response-route-planning"

        self.assertIn(target_set, TARGET_SETS)
        self.assertIn(target_set, PLANNING_ONLY_TARGET_SETS)
        self.assertNotIn(target_set, RELEASE_READINESS_TARGET_SETS)

        public_gameplay_events = PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8")
        self.assertNotIn(target_set, public_gameplay_events)

        release_claim_sinks = [
            REPO_ROOT / "CHANGELOG.md",
            REPO_ROOT / "docs" / "RELEASE.md",
            REPO_ROOT / "docs" / "STATUS.md",
            REPO_ROOT / ".github" / "pull_request_template.md",
        ]
        public_sdk_claim_sinks = [
            REPO_ROOT / "README.md",
            PUBLIC_SDK_V1_COMPATIBILITY_DOC,
            PUBLIC_SDK_SURFACES_MANIFEST,
        ]
        for path in release_claim_sinks + public_sdk_claim_sinks:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertNotIn(target_set, path.read_text(encoding="utf-8"))

    def test_planning_only_artifact_packs_are_not_release_or_public_sdk_claims(self) -> None:
        curation = (
            REPO_ROOT / "docs" / "research" / "2026-05-31-offline-artifact-curation.md"
        ).read_text(encoding="utf-8")
        compact = normalized(curation)

        required_boundary = normalized(
            "Planning-only target-set artifact packs are consume-mode planning evidence only. "
            "The planning-only target sets are `command-chat-response-route-planning`, "
            "`mission-copied-bool-policy-slice`, "
            "`players-identity-lifecycle-intake`, `players-lifecycle-anchor-candidates`, "
            "and `structure-aggregate-census-planning`; "
            "their packs, container manifests, and child evidence must not be cited as "
            "release-readiness roots, public SDK promotion evidence, or `v1.0` completion signals."
        )
        self.assertIn(required_boundary, compact)
        self.assertIn(
            normalized(
                "The `players-lifecycle-anchor-candidates` target set is layout-planning only "
                "and carries no runtime lifecycle ordering claim."
            ),
            compact,
        )
        for target_set in sorted(PLANNING_ONLY_TARGET_SETS):
            with self.subTest(target_set=target_set):
                self.assertIn(target_set, curation)

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

    def test_status_tracks_v1_as_complete_sdk_not_runtime_only(self) -> None:
        status = (REPO_ROOT / "docs/STATUS.md").read_text(encoding="utf-8")
        compact = normalized(status)

        for term in (
            "`v1.0` SDK planning track",
            "This track is not a\nruntime-only stability track",
            "complete Obelisk SDK milestone, not just a\nstable loader/runtime milestone",
            "umbrella blockers such as gameplay modules, player services, and operator/storage",
            "dino, tribe, buff/status, chat send/broadcast,\n  player progression/engrams, economy, mobility, and operator ingress/storage",
            "narrow copied C ABI surface or an explicit named exclusion",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compact)

        self.assertNotIn("v1.0` core-stability track", status)
        self.assertNotIn("`v1.0` complete-SDK track", status)

    def test_release_gate_docs_do_not_make_core_first_gate_a_v1_completion_gate(self) -> None:
        release = (REPO_ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")
        compact = normalized(release)

        for term in (
            "This core-first gate is necessary package/readiness evidence for `v0.1.x` RC/stable candidates",
            "it is not a `v1.0` complete-SDK gate",
            "`SDK_V1_COMPATIBILITY.md`",
            "`public_sdk_surfaces.json`",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compact)

    def test_field_window_components_sdk_and_seeds_are_not_v1_completion_signals(self) -> None:
        handoff = (REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md").read_text(
            encoding="utf-8"
        )
        status = (REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
        compatibility = PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8")
        surfaces = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        compact = normalized("\n".join([handoff, status, compatibility]))
        guardrails = normalized("\n".join(surfaces.get("release_guardrails", [])))

        for term in (
            "field-window packaging blocker",
            "not a `v1.0` SDK blocker, route shortcut, or completion signal",
            "CMake package target are present",
            "package-shape evidence only, not a `v1.0` completion marker",
            "do not gain priority, support tier, public SDK scope, or `v1.0`\n  completion weight while complete-SDK blockers remain open",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compact)

        self.assertIn(
            normalized(
                "Installed SDK package/component validation, including CMake COMPONENTS SDK, "
                "is package-shape evidence only and is not a v1.0 completion marker."
            ),
            guardrails,
        )

    def test_inventory_copied_signals_side_lane_does_not_displace_identity_route(self) -> None:
        current = (REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md").read_text(
            encoding="utf-8"
        )
        compact_context = (
            REPO_ROOT / "docs" / "agent-handoff" / "COMPACT_CONTEXT.md"
        ).read_text(encoding="utf-8")
        compatibility = PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8")
        surfaces = json.loads(PUBLIC_SDK_SURFACES_MANIFEST.read_text(encoding="utf-8"))
        compact_docs = normalized("\n".join([current, compact_context, compatibility]))
        guardrails = normalized("\n".join(surfaces.get("release_guardrails", [])))

        for term in (
            "While identity waits on copied core evidence",
            "inventory copied signals are the higher-value side lane",
            "structure census remains useful offline planning/consume-only work",
            "Neither side lane displaces\nidentity -> permissions/admin -> commands/replies",
            "Prefer inventory copied-signal hygiene over structure\ncensus when choosing one side lane",
            "treat inventory/item copied signals as\nthe higher-value side lane than structure census",
            "Keep that work experimental and non-completion",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compact_docs)

        self.assertIn(
            normalized(
                "While player identity waits on copied core/reflection evidence, "
                "inventory_item_copied_signals may be treated as the higher-value "
                "near-term side lane than structure_census because it rides "
                "promoted-experimental copied GameplayPolicyEvent signals; this must "
                "not reorder the identity/principal -> permissions/admin -> "
                "commands/replies dependency chain, promote inventory "
                "mutation/identity/lookup, or promote structure_census beyond "
                "planning/consume-only."
            ),
            guardrails,
        )

    def test_inventory_named_gameplay_policy_event_kinds_are_not_inventory_sdk(self) -> None:
        compatibility = normalized(PUBLIC_SDK_V1_COMPATIBILITY_DOC.read_text(encoding="utf-8"))

        for term in (
            "Inventory-named `GameplayPolicyEvent` kinds are promoted only as copied event kinds inside\nthe gameplay-policy surface",
            "they are not an Inventory SDK or Items SDK",
            "do not expose\ninventory/item identity, lookup, mutation, item handles, grant/remove, rollback, or\n`ResourceHandle`",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compatibility)

    def test_player_identity_preflight_keeps_admin_snapshots_separate_from_principal_promotion(self) -> None:
        note = (REPO_ROOT / "docs" / "research" / "2026-05-31-player-identity-offline-pack-preflight.md").read_text(
            encoding="utf-8"
        )
        compact = normalized(note)

        for term in (
            "ROOT=/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>",
            "--obelisk-commit \"${COMMIT}\"",
            "--fname-root-slot verified_fname_root_slot=0x5956f30",
            "--gobjects-candidate gobjects=0x595b7e0",
            "Always pass the reviewed `--ark-binary-sha256` shown above so the inventory\nbuilder fails closed if the core evidence-pack manifest is paired with a different ARK\nbinary",
            "Do not use `--skip-core-sha256`",
            "do not use `--allow-partial-gdb`",
            "at least one real session-start anchor and one real\nsession-end anchor",
            "Even with the admin snapshots now present",
            "completed admin snapshots close only the admin-surface fixture gap",
            "`ChatMessageEvent` must continue to treat `principal=unknown`",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compact)

    def test_offline_artifact_pack_docs_define_static_field_window_child_boundary(self) -> None:
        packs = (REPO_ROOT / "docs" / "OFFLINE_ARTIFACT_PACKS.md").read_text(encoding="utf-8")
        route = (REPO_ROOT / "docs" / "research" / "2026-05-31-fname-gobjects-offline-route.md").read_text(
            encoding="utf-8"
        )
        current = (REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md").read_text(encoding="utf-8")
        compact = normalized(packs + "\n" + route + "\n" + current)

        for term in (
            "unknown `obelisk.*` child schema\nis a blocker",
            "Strict static FUObjectArray field-window evidence may now be stored as an authoritative\nchild manifest",
            "`obelisk.fuobjectarray-field-window-redacted.v1` and passes that schema's consume-mode\ngate",
            "`promotion_gate_ready=false`, and no absolute path strings",
            "This is internal static\nresearch evidence only; promote mode remains blocked",
            "`obelisk.fuobjectarray-field-window-redacted.v1`",
            "`obelisk.offline-artifact-gate-result.v1`",
            "`obelisk.static-artifact-provenance.v1`",
            "`unsupported_manifest_schema`",
            "supports `obelisk.fuobjectarray-field-window-redacted.v1` as a durable normalized\nartifact-pack child manifest in consume mode only",
            "clears only the static coherent field-window packaging blocker",
            "Normalizing a directory also does not rewrite absolute paths inside\nchild manifests",
            "that blocker is cleared only for the\nFUObjectArray redacted field-window schema",
            "gate-result and\nprovenance child manifests remain blocked with `unsupported_manifest_schema`",
            "Local artifact directories are not current release or v1 identity/structure evidence by\nlocation",
            "`obelisk.offline-artifact-gate-result.v1` JSON is gate output, not an authoritative child\nmanifest",
            "placing it inside a pack must not bypass child-manifest validation or convert\narchival identity/structure packs into current evidence",
            "For archival local packs, do\nnot cite gate-result JSON, child-manifest filenames, or container presence as evidence of\ncurrent v1 player identity, structure aggregate/census",
        ):
            with self.subTest(term=term):
                self.assertIn(normalized(term), compact)

        self.assertNotIn("it remains tmp-only until a supported normalized artifact-pack shape exists", compact)

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
