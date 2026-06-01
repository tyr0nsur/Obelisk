#!/usr/bin/env python3
"""Fail-closed checker for the Obelisk v1.0 complete-SDK claim."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
DEFAULT_CONTRACT_DECISIONS_DIR = REPO_ROOT / "docs"
CANONICAL_SURFACE_IDS = {
    "obelisk.arkapi_compatibility.v1",
    "obelisk.chat.local_routing.v1",
    "obelisk.chat_message.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
    "obelisk.debug_raw_process_event.v1",
    "obelisk.descriptors.v1",
    "obelisk.gameplay_policy_event.v1",
    "obelisk.gameplay_tick_callbacks.v1",
    "obelisk.inventory_item_copied_signals.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_config_logging.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.object_identity_resource_handle.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.player_identity.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.process_local_timers.v1",
    "obelisk.structure_census.v1",
}
CANONICAL_V1_COMPLETION_BLOCKERS = {
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.commands_replies.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.structure_census.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.object_identity_resource_handle.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.gameplay_tick_callbacks.v1",
}
CANONICAL_V1_DEPENDENCY_SEQUENCE = (
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
)
CANONICAL_EXPERIMENTAL_SURFACE_IDS = {
    "obelisk.gameplay_policy_event.v1",
    "obelisk.chat_message.v1",
    "obelisk.chat.local_routing.v1",
    "obelisk.inventory_item_copied_signals.v1",
}
CANONICAL_EXPERIMENTAL_RELEASE_STATEMENT_TEXT = {
    "obelisk.gameplay_policy_event.v1": ("GameplayPolicyEvent", "not included in v1"),
    "obelisk.chat_message.v1": ("ChatMessageEvent", "not included in v1"),
    "obelisk.chat.local_routing.v1": ("chat routing", "not included in v1"),
    "obelisk.inventory_item_copied_signals.v1": ("inventory copied signals", "not included in v1"),
}
CANONICAL_STABLE_RELEASE_CLAIM_REQUIRES = (
    "v1_completion_required is true in this manifest",
    "every v1_sdk_completion_blocker is promoted or explicitly named as excluded/post-v1 in the v1 release statement",
    "minimum promoted demand families are promoted or satisfied by explicit completion equivalents before complete/full/production SDK wording",
    "no promoted-experimental-only surface remains unresolved",
    "the release ships a reviewed SDK compatibility statement based on docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json",
)
CANONICAL_STABLE_RELEASE_NOT_SUFFICIENT = (
    "runtime/core-first RC readiness",
    "internal runtime stability",
    "Foundation/Plugin Hub seed package shape",
    "GameplayPolicyEvent, ChatMessageEvent, and inventory item copied-signal seeds",
)
SCOPED_RELEASE_STATEMENT_ALLOWED_BLOCKERS = {
    "complete_sdk_claim_requires_promoted_demand_families",
    "stable_release_contract_claim_not_allowed",
    "v1_completion_required_false",
    "promoted_experimental_surfaces_unresolved",
    "v1_sdk_completion_blockers_unresolved",
    "planning_surfaces_unresolved_for_v1_claim",
    "top_level_planning_surfaces_unresolved_for_v1_claim",
}
STRICT_PROMOTION_EVIDENCE_SURFACE_IDS = CANONICAL_V1_COMPLETION_BLOCKERS | CANONICAL_EXPERIMENTAL_SURFACE_IDS
PROMOTION_EVIDENCE_REQUIRED_TERMS = {
    "obelisk.player_identity.v1": (
        "obelisk.core-dump-evidence-pack.v1",
        "obelisk.reflection-inventory-pack.v1",
        "ServerListPlayers",
        "ServerKickPlayer",
        "approved runtime principal lifecycle evidence",
        "accepted login/logout lifecycle ordering and principal invalidation semantics",
        "principal privacy, invalidation, and cross-instance semantics",
        "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
    ),
    "obelisk.permissions_admin.v1": (
        "query-only fail-closed permission checks over copied principals",
        "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
        "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
        "promoted copied principal semantics",
    ),
}
REQUIRED_PROMOTED_SURFACE_DEPENDENCIES = {
    "obelisk.permissions_admin.v1": (
        "obelisk.player_identity.v1",
    ),
    "obelisk.command_chat_response_path.v1": (
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
    ),
    "obelisk.commands_replies.v1": (
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
        "obelisk.command_chat_response_path.v1",
    ),
    "obelisk.player_services_economy_mobility.v1": (
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
        "obelisk.command_chat_response_path.v1",
        "obelisk.operator_ingress_storage.v1",
    ),
}
PROMOTION_EVIDENCE_NEGATIVE_CONTEXT_KEYS = {
    "blockers",
    "candidate",
    "missing",
    "non_claim",
    "non_claims",
    "planning",
    "requires",
    "todo",
    "todos",
    "unresolved",
}
PROMOTION_EVIDENCE_NEGATIVE_TERM_CONTEXT = re.compile(
    r"\b(?:blocked|candidate(?:-only)?|insufficient|missing|needs?|no|not|planning|requires?|todo|unresolved|without)\b",
    re.IGNORECASE,
)
STRICT_PROMOTION_EVIDENCE_PATH_DENY_MARKERS = (
    "candidate",
    "admin_thunk",
    "admin_thunks",
    "chat_message_event_seed",
    "chat_seed",
    "copied_data",
    "core_first",
    "descriptor_catalog",
    "descriptor_preflight",
    "event_seed",
    "gameplay_policy_event_seed",
    "inventory_policy_event",
    "item_return",
    "item_return_event",
    "package_shape",
    "planning",
    "plugin_hub",
    "pluginhub",
    "plugin_hub_seed",
    "orientation",
    "preflight",
    "readiness",
    "static_candidate",
    "static_target",
    "return_only",
    "consume-only",
    "consume_only",
    "evidence-only",
    "evidence_only",
)
STRICT_PROMOTION_EVIDENCE_SCHEMA_KEYS = {
    "artifact_schema",
    "descriptor_preflight",
    "evidence_kind",
    "evidence_kinds",
    "evidence_terms",
    "input_target_set",
    "output_target_set",
    "pack",
    "packs",
    "promotion_terms",
    "release_readiness_target_sets",
    "contract_kind",
    "schema",
    "schemas",
    "source_kind",
    "source_kinds",
    "status",
    "source_target_sets",
    "target_set",
    "target_sets",
    "terms",
}
STRICT_PROMOTION_EVIDENCE_SCHEMA_DENY_MARKERS = re.compile(
    r"(?:candidate|planning|plugin[-_ ]?hub|package[-_ ]?shape|core[-_ ]?first|"
    r"players?[-_ ]?identity[-_ ]?principal[-_ ]?invalidation[-_ ]?policy|"
    r"principal[-_ ]?invalidation[-_ ]?policy|"
    r"copied[-_ ]?data|(?:chat[-_ ]?message|gameplay[-_ ]?policy[-_ ]?event|event|chat)[-_ ]?seeds?|"
    r"static[-_ ]?(?:orientation|candidate|target|discovery)|native[-_ ]?ufunction[-_ ]?registration[-_ ]?static[-_ ]?discovery|"
    r"admin[-_ ]?thunks?|orientation|preflight|readiness|"
    r"item[-_ ]?return[-_ ]?only|return[-_ ]?only|descriptor[-_ ]?preflight|"
    r"descriptor[-_ ]?catalog|consume[-_ ]?only|evidence[-_ ]?only)",
    re.IGNORECASE,
)
CANONICAL_DEBUG_ONLY_SURFACE_IDS = {
    "obelisk.debug_raw_process_event.v1",
}
MANIFEST_BACKED_BLOCKED_HEADER_SURFACE_IDS = {
    "obelisk.gameplay_tick_callbacks.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.object_identity_resource_handle.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.structure_census.v1",
}
ALLOWED_GENERIC_EVIDENCE_DIRS = {
    "tests/sdk_consumer",
    "tests/sdk_installed_consumer",
}
PROMOTION_EVIDENCE_ALLOWED_PREFIXES = (
    "tests/abi/",
    "tests/core/",
    "tests/sdk_consumer/",
    "tests/sdk_installed_consumer/",
    "scripts/test_",
)
GENERIC_SCRIPT_EVIDENCE_DENYLIST = {
    "scripts/check_release_readiness.sh",
    "scripts/check_public_sdk_v1_completion.py",
}
AFFIRMATIVE_RELEASE_CLAIM_PATTERNS = (
    r"\b(?:complete|full|production|stable)\s+(?:[a-z0-9_/+-]+\s+){0,5}(?:sdk|api|support)\b",
    r"\b(?:sdk|api|surface|capability|support)\s+"
    r"(?:is|are|remains?|stays?)\s+"
    r"(?:complete|full|production|stable|available|ready|supported|included|shipped|"
    r"public|promoted)\b",
    r"\b[a-z0-9_ /+-]{2,80}\s+(?:is|are)\s+"
    r"(?:available|ready|supported|included|shipped|public|promoted)\s+in\s+v1\b",
)
FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_PATTERNS = (
    r"\bv1(?:\.0)?\s+stable(?:\s+(?:sdk|api|support|release|claim|approval|wording))?\b",
    r"\b(?:this|statement|release)\s+"
    r"(?:is|declares?|approves?|allows?|authorizes?)\s+"
    r"(?:a\s+)?v1(?:\.0)?\s+stable(?:\s+(?:sdk|api|support|release|claim))?\b",
    r"\b(?:player[-_ ]?identity|player[-_ ]?principal|playeridentity|"
    r"permissions?/admin|permissions?[-_ ]?admin|permissionsadmin|permissions?|admin|"
    r"command[-_ ]?(?:chat[-_ ]?)?responses?|commandresponse|"
    r"commands?/replies|commands?[-_ ]?replies|command[-_ ]?router|"
    r"inventory[-_ ]?(?:identity|lookup|mutation)|item[-_ ]?(?:identity|lookup|mutation|handles?)|"
    r"give[-_ ]?item|remove[-_ ]?item|object[-_ ]?identity|uobject[-_ ]?identity|"
    r"object[-_ ]?lookup|resource[-_ ]?handles?|resourcehandle|missions?|"
    r"buff(?:/status|[-_ ]?status)?|buffstatus|buffs?)\s+"
    r"(?:sdk|api|surface|support)\b.{0,80}"
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b",
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|"
    r"shipped|stable|supported|public|promoted)\b.{0,80}"
    r"\b(?:player[-_ ]?identity|player[-_ ]?principal|playeridentity|"
    r"permissions?/admin|permissions?[-_ ]?admin|permissionsadmin|permissions?|admin|"
    r"command[-_ ]?(?:chat[-_ ]?)?responses?|commandresponse|"
    r"commands?/replies|commands?[-_ ]?replies|command[-_ ]?router|"
    r"inventory[-_ ]?(?:identity|lookup|mutation)|item[-_ ]?(?:identity|lookup|mutation|handles?)|"
    r"give[-_ ]?item|remove[-_ ]?item|object[-_ ]?identity|uobject[-_ ]?identity|"
    r"object[-_ ]?lookup|resource[-_ ]?handles?|resourcehandle|missions?|"
    r"buff(?:/status|[-_ ]?status)?|buffstatus|buffs?)\s+"
    r"(?:sdk|api|surface|support)\b",
    r"\b(?:inventory\s+sdk|items\s+sdk)\b.{0,80}"
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|shipped|stable|supported|public|promoted)\b",
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|shipped|stable|supported|public|promoted)\b"
    r".{0,80}\b(?:inventory\s+sdk|items\s+sdk)\b",
    r"\b(?:resourcehandle|resource[- ]?handle|object[- ]?identity|object[- ]?lookup)\s+"
    r"(?:sdk|api|surface|support)?\b.{0,80}"
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|shipped|stable|supported|public|promoted)\b",
    r"\b(?:available|complete|full|included|production[- ]?ready|ready|released|shipped|stable|supported|public|promoted)\b"
    r".{0,80}\b(?:resourcehandle|resource[- ]?handle|object[- ]?identity|object[- ]?lookup)\s+"
    r"(?:sdk|api|surface|support)?\b",
    r"\b(?:plugin\s+hub|pluginhub)\b.{0,80}"
    r"\b(?:available|complete|full|production[- ]?ready|ready|released|shipped|stable|supported)\b",
    r"\b(?:available|complete|full|production[- ]?ready|ready|released|shipped|stable|supported)\b"
    r".{0,80}\b(?:plugin\s+hub|pluginhub)\b",
    r"\b(?:candidate(?:[- ]?only)?|planning(?:[- ]?only)?|orientation(?:[- ]?only)?|"
    r"consume[- ]?only|evidence[- ]?only|preflight|readiness|foundation|package[- ]?shape|"
    r"static[- ]?orientation)\b.{0,100}"
    r"\b(?:available|complete|full|included|production[- ]?ready|public|ready|released|"
    r"shipped|stable|supported|promoted)\b.{0,40}"
    r"\b(?:v1(?:\.0)?|sdk|api|surface|support|claim|release)\b",
    r"\b(?:v1(?:\.0)?|sdk|api|surface|support|claim|release)\b.{0,40}"
    r"\b(?:available|complete|full|included|production[- ]?ready|public|ready|released|"
    r"shipped|stable|supported|promoted)\b.{0,100}"
    r"\b(?:candidate(?:[- ]?only)?|planning(?:[- ]?only)?|orientation(?:[- ]?only)?|"
    r"consume[- ]?only|evidence[- ]?only|preflight|readiness|foundation|package[- ]?shape|"
    r"static[- ]?orientation)\b",
    r"\b(?:candidate(?:[- ]?only)?|planning(?:[- ]?only)?|orientation(?:[- ]?only)?|"
    r"consume[- ]?only|evidence[- ]?only|preflight|readiness|foundation|package[- ]?shape|"
    r"static[- ]?orientation)\b.{0,100}"
    r"\b(?:proves?|validates?|unlocks?|satisf(?:y|ies)|enables?)\b.{0,60}"
    r"\b(?:v1(?:\.0)?\s+stable|complete\s+(?:sdk|api)|full\s+(?:sdk|api)|"
    r"production[- ]?ready\s+(?:sdk|api|support)|production\s+(?:sdk|api|support))\b",
)
FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS = re.compile(
    r"\b(?:blocked|cannot|does\s+not|do\s+not|excluded|insufficient|limited|"
    r"must\s+not|no|not|post-v1|post v1)\b",
    re.IGNORECASE,
)
FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATED_REMAINDER = re.compile(
    r"^\s*(?:(?:is|are|remains?|stays?)\s+)?"
    r"(?:blocked|cannot|disabled|forbidden|not\s+(?:allowed|approved|authorized|ready)|"
    r"must\s+not)\b",
    re.IGNORECASE,
)
CLAUSE_START_PATTERN = re.compile(r"[.;\n]|(?:\s+-\s+)")
BLOCKED_CONTRACT_HEADER_SYMBOL_PATTERNS = {
    "obelisk.player_identity.v1": (
        re.compile(
            r"(?:PlayerIdentity|PlayerPrincipal|PlayerLookup|PlayerHandle|PlayerId|PlayerID|"
            r"SteamId|SteamID|EOSId|EOSID|PlatformAccountId|PlatformAccountID|"
            r"PlayerName|TribeId|TribeID|NetworkAddress|"
            r"PrincipalHandle|PrincipalGeneration|PrincipalScope|ObeliskPrincipal|"
            r"PlayerSession)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PLAYER_IDENTITY|PLAYER_PRINCIPAL|PLAYER_LOOKUP|"
            r"PLAYER_ID|STEAM_ID|EOS_ID|PLATFORM_ACCOUNT_ID|PLAYER_NAME|TRIBE_ID|"
            r"NETWORK_ADDRESS|PRINCIPAL_HANDLE|PRINCIPAL_GENERATION|"
            r"PRINCIPAL_SCOPE|PLAYER_SESSION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:player_identity|player_principal|player_lookup|principal_handle|"
            r"principal_generation|principal_scope|steam_id|eos_id|platform_account_id|"
            r"player_name|tribe_id|network_address|role_id|player_session)(?:_|$)"
        ),
    ),
    "obelisk.permissions_admin.v1": (
        re.compile(
            r"(?:Permission|Permissions|Admin|Authorization|Authorize|Authz|AuthZ|ACL|Acl|"
            r"Moderation|Moderator|BanPlayer|KickPlayer|Grant|Revoke|RoleId|RoleID)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PERMISSION|ADMIN|AUTHORIZATION|MODERATION|"
            r"AUTHZ|ACL|BAN|KICK|GRANT|REVOKE|ROLE_ID)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:permission|permissions|admin|authorization|authority_kind|"
            r"authz|acl|policy_epoch|ban_player|kick_player|grant|revoke|role_id)(?:_|$)"
        ),
    ),
    "obelisk.command_chat_response_path.v1": (
        re.compile(
            r"(?:Command|Reply|Replies|Response|Respond|SendChat|Broadcast|Notice|Moderation)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:COMMAND|REPLY|RESPONSE|SEND_CHAT|BROADCAST|"
            r"NOTICE|MODERATION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:command|reply|replies|response|response_handle|response_kind|"
            r"send_chat|broadcast|notice|moderation|delivery_scope|delivery_flags)(?:_|$)"
        ),
    ),
    "obelisk.commands_replies.v1": (
        re.compile(
            r"(?:Command|Commands|Reply|Replies|CommandRouter|CommandCallback|"
            r"CommandPayload|CommandRegistration|SendChat|Broadcast|Notice|Moderation)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:COMMAND|COMMANDS|REPLY|REPLIES|SEND_CHAT|"
            r"BROADCAST|NOTICE|MODERATION)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:command|commands|command_router|command_callback|command_payload|"
            r"command_registration|reply|replies|send_chat|broadcast|notice|moderation)(?:_|$)"
        ),
    ),
    "obelisk.inventory_items_mutation.v1": (
        re.compile(
            r"(?:InventorySdk|ItemsSdk|InventoryLookup|ItemLookup|ItemHandle|GiveItem|"
            r"RemoveItem|GrantItem|InventoryMutation|ItemMutation|Kit|Kits|Reward|Rewards|"
            r"Engram|Progression|ResourceHandle|InventoryComp|InventoryID|InventoryId|"
            r"ItemID|ItemId|ItemNetId|ItemNetID|ItemStack|ItemStackID|ItemStackId|"
            r"CraftBlueprint|AdditionalData)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:INVENTORY_SDK|ITEMS_SDK|INVENTORY_LOOKUP|"
            r"ITEM_LOOKUP|ITEM_HANDLE|GIVE_ITEM|REMOVE_ITEM|GRANT_ITEM|INVENTORY_MUTATION|"
            r"ITEM_MUTATION|KIT|KITS|REWARD|REWARDS|ENGRAM|PROGRESSION|"
            r"RESOURCE_HANDLE|INVENTORY_COMP|INVENTORY_ID|ITEM_ID|ITEM_NET_ID|"
            r"ITEM_STACK|ITEM_STACK_ID|CRAFT_BLUEPRINT|ADDITIONAL_DATA)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:inventory_sdk|items_sdk|inventory_lookup|item_lookup|item_handle|"
            r"give_item|remove_item|grant_item|inventory_mutation|item_mutation|kits?|"
            r"rewards?|engram|progression|resource_handle|inventory_comp|item_net_id|"
            r"inventory_id|item_id|item_stack|item_stack_id|craft_blueprint|additional_data)(?:_|$)"
        ),
    ),
    "obelisk.object_identity_resource_handle.v1": (
        re.compile(
            r"(?:ObjectIdentity|UObjectIdentity|ObjectLookup|ResourceHandle|ObjectHandle|"
            r"PostCallbackObject|StructureHandle|ItemHandle|InventoryHandle|DinoHandle|"
            r"TribeHandle|BuffStatusHandle|MissionTransferHandle|AreaPolicyObjectHandle|"
            r"PersistentHandle|SerialHandle|EconomyHandle|MobilityHandle|ObjectID|ObjectId|"
            r"UObjectID|UObjectId|ResourceID|ResourceId)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:OBJECT_IDENTITY|UOBJECT_IDENTITY|OBJECT_LOOKUP|"
            r"RESOURCE_HANDLE|OBJECT_HANDLE|POST_CALLBACK_OBJECT|STRUCTURE_HANDLE|"
            r"ITEM_HANDLE|INVENTORY_HANDLE|DINO_HANDLE|TRIBE_HANDLE|BUFF_STATUS_HANDLE|"
            r"MISSION_TRANSFER_HANDLE|AREA_POLICY_OBJECT_HANDLE|PERSISTENT_HANDLE|"
            r"SERIAL_HANDLE|ECONOMY_HANDLE|MOBILITY_HANDLE|OBJECT_ID|UOBJECT_ID|"
            r"RESOURCE_ID)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:object_identity|uobject_identity|object_lookup|resource_handle|"
            r"object_handle|post_callback_object|structure_handle|item_handle|"
            r"inventory_handle|dino_handle|tribe_handle|buff_status_handle|"
            r"mission_transfer_handle|area_policy_object_handle|persistent_handle|"
            r"serial_handle|serial_reuse|economy_handle|mobility_handle|object_id|"
            r"uobject_id|resource_id)(?:_|$)"
        ),
    ),
    "obelisk.lifecycle_ops_recovery.v1": (
        re.compile(
            r"(?:PluginWatchdog|CrashRecovery|HotPluginReload|ObeliskHotReload|"
            r"RestartOrchestration|ServerRecovery|OperatorReloadCommand|"
            r"DetachedWorkerIngress|RestartStateRecovery)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PLUGIN_WATCHDOG|CRASH_RECOVERY|HOT_PLUGIN_RELOAD|"
            r"OBELISK_HOT_RELOAD|RESTART_ORCHESTRATION|SERVER_RECOVERY|"
            r"OPERATOR_RELOAD_COMMAND|DETACHED_WORKER_INGRESS|RESTART_STATE_RECOVERY)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:plugin_watchdog|crash_recovery|hot_plugin_reload|obelisk_hot_reload|"
            r"restart_orchestration|server_recovery|operator_reload_command|"
            r"detached_worker_ingress|restart_state_recovery)(?:_|$)"
        ),
    ),
    "obelisk.structure_census.v1": (
        re.compile(
            r"(?:StructureEvents|StructureCensus|StructureAggregate|StructureIdentity|"
            r"StructureLookup|StructureHandle|OwnershipLookup|BuildPlacement|"
            r"NoCollision|PinOutcome)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:STRUCTURE_EVENTS|STRUCTURE_CENSUS|"
            r"STRUCTURE_AGGREGATE|STRUCTURE_IDENTITY|STRUCTURE_LOOKUP|STRUCTURE_HANDLE|"
            r"OWNERSHIP_LOOKUP|BUILD_PLACEMENT|NO_COLLISION|PIN_OUTCOME)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:structure_events|structure_census|structure_aggregate|"
            r"structure_identity|structure_lookup|structure_handle|ownership_lookup|"
            r"build_placement|no_collision|pin_outcome)(?:_|$)"
        ),
    ),
    "obelisk.mission_transfer_dino_tribe.v1": (
        re.compile(
            r"(?:MissionSdk|TransferSdk|DinoSdk|TribeSdk|BuffStatusSdk|BuffSdk|"
            r"Mission|Transfer|Dino|Tribe|BuffStatus|DinoColors|DinoCosmetics|DinoCarryRules|"
            r"TribeMotd|TribeNotice|TribePolicy|TeleportSpawn|CrossMapCorrelation|"
            r"OwnershipLookup|Teleport|Spawn)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:MISSION_SDK|TRANSFER_SDK|DINO_SDK|TRIBE_SDK|"
            r"BUFF_STATUS_SDK|BUFF_SDK|MISSION|TRANSFER|DINO|BUFF_STATUS|DINO_COLORS|"
            r"DINO_COSMETICS|DINO_CARRY_RULES|TRIBE_MOTD|TRIBE_NOTICE|TRIBE_POLICY|"
            r"TELEPORT_SPAWN|CROSS_MAP_CORRELATION|OWNERSHIP_LOOKUP|TELEPORT|"
            r"SPAWN)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:mission_sdk|transfer_sdk|dino_sdk|tribe_sdk|buff_status_sdk|"
            r"buff_sdk|mission|transfer|dino|buff_status|dino_colors|dino_cosmetics|"
            r"dino_carry_rules|tribe_motd|tribe_notice|tribe_policy|teleport_spawn|"
            r"cross_map_correlation|ownership_lookup|teleport|spawn)(?:_|$)"
        ),
    ),
    "obelisk.player_services_economy_mobility.v1": (
        re.compile(
            r"(?:PlayerServices|Economy|Shop|Shops|Reward|Rewards|Kit|Kits|Stats|"
            r"Homes|HomeTeleport|Teleport|SafeZone|AreaPolicy|TimedNotice|"
            r"CrossInstancePersistence|Mobility)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:PLAYER_SERVICES|ECONOMY|SHOP|SHOPS|REWARD|"
            r"REWARDS|KIT|KITS|STATS|HOMES|HOME_TELEPORT|TELEPORT|SAFE_ZONE|"
            r"AREA_POLICY|TIMED_NOTICE|CROSS_INSTANCE_PERSISTENCE|MOBILITY)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:player_services|economy|shops?|rewards?|kits?|stats|homes|"
            r"home_teleport|teleport|safe_zone|area_policy|timed_notice|"
            r"cross_instance_persistence|mobility)(?:_|$)"
        ),
    ),
    "obelisk.operator_ingress_storage.v1": (
        re.compile(
            r"(?:Rcon|RCON|OperatorReload|OperatorCommand|Webhook|Database|StorageSchema|"
            r"StorageMigration|SecretManager|ExternalIngress|CrossInstanceStorage|"
            r"QueueDrain|PoisonMessage|Storage)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:RCON|OPERATOR_RELOAD|OPERATOR_COMMAND|WEBHOOK|"
            r"DATABASE|STORAGE_SCHEMA|STORAGE_MIGRATION|SECRET_MANAGER|"
            r"EXTERNAL_INGRESS|CROSS_INSTANCE_STORAGE|QUEUE_DRAIN|"
            r"POISON_MESSAGE|STORAGE)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:rcon|operator_reload|operator_command|webhook|database|"
            r"storage_schema|storage_migration|secret_manager|external_ingress|"
            r"cross_instance_storage|queue_drain|poison_message|storage)(?:_|$)"
        ),
    ),
    "obelisk.gameplay_tick_callbacks.v1": (
        re.compile(
            r"(?:ServerTick|GameplayTick|ModuleTick|PerFrameHook|FrameHook|"
            r"GameplayTimer|GameplayTimers|TickCallback|TickCallbacks)"
        ),
        re.compile(
            r"^OBELISK_[A-Z0-9_]*(?:SERVER_TICK|GAMEPLAY_TICK|MODULE_TICK|"
            r"PER_FRAME_HOOK|FRAME_HOOK|GAMEPLAY_TIMER|GAMEPLAY_TIMERS|"
            r"TICK_CALLBACK|TICK_CALLBACKS)[A-Z0-9_]*$"
        ),
        re.compile(
            r"(?:^|_)(?:server_tick|gameplay_tick|module_tick|per_frame_hook|"
            r"frame_hook|gameplay_timers?|tick_callbacks?)(?:_|$)"
        ),
    ),
}
PUBLIC_CONTRACT_DECISIONS_GLOB = "*_public_contract_decisions.json"
REQUIRED_PUBLIC_CONTRACT_DECISION_MANIFESTS = {
    "obelisk.player_identity.v1": "player_identity_public_contract_decisions.json",
    "obelisk.inventory_item_copied_signals.v1": "inventory_item_copied_signals_public_contract_decisions.json",
    "obelisk.permissions_admin.v1": "permissions_admin_public_contract_decisions.json",
    "obelisk.command_chat_response_path.v1": "command_chat_response_public_contract_decisions.json",
    "obelisk.commands_replies.v1": "commands_replies_public_contract_decisions.json",
}
REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS = {
    "obelisk.command_principal_authz_response_bridge.v1": "command_principal_authz_response_bridge_decisions.json",
}
CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES = CANONICAL_V1_COMPLETION_BLOCKERS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that public_sdk_surfaces.json allows a complete v1 SDK claim."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to docs/public_sdk_surfaces.json.",
    )
    parser.add_argument(
        "--release-statement",
        type=Path,
        help="Reviewed v1 SDK release statement that names excluded/post-v1 blockers.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=DEFAULT_PUBLIC_HEADER,
        help="Public C ABI header checked against blocked public contract decision manifests.",
    )
    parser.add_argument(
        "--contract-decisions-dir",
        type=Path,
        default=DEFAULT_CONTRACT_DECISIONS_DIR,
        help="Directory containing *_public_contract_decisions.json manifests.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the full readiness report as JSON.")
    parser.add_argument(
        "--validate-release-statement-scope",
        action="store_true",
        help=(
            "Validate the supplied release statement's scoped outcome wording without "
            "allowing a complete v1 SDK claim while manifest blockers remain unresolved."
        ),
    )
    return parser.parse_args()


def load_manifest(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"manifest_load_failed:{exc}"]
    if not isinstance(payload, dict):
        return None, ["manifest_not_object"]
    return payload, []


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def as_string_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, list[str]] = {}
    for key, raw_values in value.items():
        if not isinstance(key, str):
            continue
        if isinstance(raw_values, str):
            result[key] = [raw_values]
        else:
            result[key] = as_string_list(raw_values)
    return result


def load_release_statement(path: Path | None) -> tuple[str | None, list[str]]:
    if path is None:
        return None, []
    try:
        return path.read_text(encoding="utf-8"), []
    except OSError as exc:
        return None, [f"release_statement_load_failed:{exc}"]


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def load_public_header_symbols(path: Path) -> tuple[set[str], list[str]]:
    try:
        text = strip_c_comments(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return set(), [f"public_header_load_failed:{exc}"]
    symbols: set[str] = set()
    symbols.update(re.findall(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\b", text, flags=re.MULTILINE))
    symbols.update(re.findall(r"\btypedef\s+(?:struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b", text))
    symbols.update(re.findall(r"\btypedef\b[^;{]*\(\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", text))
    symbols.update(re.findall(r"\(\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", text))
    symbols.update(re.findall(r"\b(OBELISK_[A-Z0-9_]+)\b", text))
    symbols.update(
        re.findall(
            r"\b(?:uint(?:32|64)_t|int(?:32|64)_t|size_t|bool|char|void|const\s+char\*)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)(?:\[[^\]]+\])?\s*;",
            text,
        )
    )
    return symbols, []


def contract_decision_paths(decisions_dir: Path) -> list[Path]:
    try:
        paths = set(decisions_dir.glob(PUBLIC_CONTRACT_DECISIONS_GLOB))
        for filename in REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS.values():
            path = decisions_dir / filename
            if path.exists():
                paths.add(path)
        return sorted(paths)
    except OSError:
        return []


def missing_required_contract_decision_manifests(decisions_dir: Path) -> dict[str, str]:
    try:
        if decisions_dir.resolve() != DEFAULT_CONTRACT_DECISIONS_DIR.resolve():
            return {}
    except OSError:
        return {
            **REQUIRED_PUBLIC_CONTRACT_DECISION_MANIFESTS,
            **REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS,
        }

    missing: dict[str, str] = {}
    required_manifests = {
        **REQUIRED_PUBLIC_CONTRACT_DECISION_MANIFESTS,
        **REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS,
    }
    for surface_id, filename in required_manifests.items():
        path = decisions_dir / filename
        payload, blockers = load_manifest(path)
        if blockers or payload is None or payload.get("surface") != surface_id:
            missing[surface_id] = filename
    return missing


def public_header_matches_contract(path: Path, raw_contract_header: Any) -> bool:
    if not isinstance(raw_contract_header, str) or not raw_contract_header:
        return True
    contract_header = Path(raw_contract_header)
    if contract_header.is_absolute():
        try:
            return contract_header.resolve() == path.resolve()
        except OSError:
            return False
    try:
        return (REPO_ROOT / contract_header).resolve() == path.resolve()
    except OSError:
        return False


def contract_symbol_patterns(surface_id: Any) -> tuple[re.Pattern[str], ...]:
    if not isinstance(surface_id, str):
        return ()
    return BLOCKED_CONTRACT_HEADER_SYMBOL_PATTERNS.get(surface_id, ())


def public_contract_decision_surfaces_for_header(
    public_header_path: Path,
    decisions_dir: Path,
) -> set[str]:
    surfaces: set[str] = set()
    for decision_path in contract_decision_paths(decisions_dir):
        payload, load_blockers = load_manifest(decision_path)
        if load_blockers or payload is None:
            continue
        if not public_header_matches_contract(public_header_path, payload.get("public_header")):
            continue
        surface_id = payload.get("surface")
        if isinstance(surface_id, str):
            surfaces.add(surface_id)
    return surfaces


def symbol_matches_blocked_contract(symbol: str, surface_id: str) -> bool:
    return any(pattern.search(symbol) for pattern in contract_symbol_patterns(surface_id))


def symbol_matches_contract_forbidden_tokens(symbol: str, payload: dict[str, Any]) -> bool:
    return symbol in set(as_string_list(payload.get("public_header_forbidden_tokens")))


def blocked_contract_public_header_symbol_drift(
    public_header_path: Path,
    decisions_dir: Path,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    public_symbols, blockers = load_public_header_symbols(public_header_path)
    drift: dict[str, dict[str, Any]] = {}
    for decision_path in contract_decision_paths(decisions_dir):
        payload, load_blockers = load_manifest(decision_path)
        if load_blockers:
            blockers.extend(f"public_contract_decision_load_failed:{decision_path}:{item}" for item in load_blockers)
            continue
        if payload is None:
            continue
        if not public_header_matches_contract(public_header_path, payload.get("public_header")):
            continue
        public_header_allowed = payload.get("public_header_allowed")
        raw_declared_symbols = payload.get("public_header_symbols_now")
        declared_symbols = set(as_string_list(raw_declared_symbols))
        if public_header_allowed is not False and raw_declared_symbols != []:
            continue
        surface_id = payload.get("surface")
        if not isinstance(surface_id, str):
            continue
        matching_symbols = sorted(
            symbol
            for symbol in public_symbols
            if symbol not in declared_symbols
            and (
                symbol_matches_blocked_contract(symbol, surface_id)
                or symbol_matches_contract_forbidden_tokens(symbol, payload)
            )
        )
        if matching_symbols:
            drift[str(decision_path)] = {
                "surface": surface_id,
                "public_header_allowed": public_header_allowed,
                "undeclared_symbols": matching_symbols,
            }
    return drift, blockers


def surface_blocks_public_header_symbols(surface: dict[str, Any]) -> bool:
    surface_id = surface.get("id")
    if not isinstance(surface_id, str) or not contract_symbol_patterns(surface_id):
        return False
    if surface_id not in MANIFEST_BACKED_BLOCKED_HEADER_SURFACE_IDS:
        return False
    if surface.get("status") == "promoted":
        return False
    contract = surface.get("v1_decision_contract")
    return (
        isinstance(contract, dict)
        and contract.get("must_remain_without_public_contract_until_promotion") is True
    )


def manifest_public_header_symbol_drift(
    public_header_path: Path,
    manifest_path: Path,
    surfaces_by_id: dict[str, dict[str, Any]],
    decision_backed_surface_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    public_symbols, blockers = load_public_header_symbols(public_header_path)
    drift: dict[str, dict[str, Any]] = {}
    if blockers:
        return drift, blockers
    for surface_id, surface in sorted(surfaces_by_id.items()):
        if surface_id in decision_backed_surface_ids:
            continue
        if not surface_blocks_public_header_symbols(surface):
            continue
        matching_symbols = sorted(
            symbol for symbol in public_symbols if symbol_matches_blocked_contract(symbol, surface_id)
        )
        if matching_symbols:
            drift[f"{manifest_path}#{surface_id}"] = {
                "surface": surface_id,
                "public_header_allowed": False,
                "undeclared_symbols": matching_symbols,
            }
    return drift, blockers


def release_statement_names_outcome(text: str, surface_id: str, status: str) -> bool:
    return release_statement_surface_record(text, surface_id, status) is not None


def release_statement_surface_records(text: str, surface_id: str, status: str | None = None) -> list[tuple[str, str]]:
    pattern = re.compile(
        rf"^\s*{re.escape(surface_id)}\s*:\s*(?P<status>promoted|excluded|post-v1)(?:\s+-\s*(?P<details>.+)|\s*)$",
        re.IGNORECASE,
    )
    records: list[tuple[str, str]] = []
    for line in text.splitlines():
        match = pattern.fullmatch(line)
        if not match:
            continue
        found_status = match.group("status").lower()
        if status is None or found_status == status.lower():
            records.append((found_status, line.strip()))
    return records


def release_statement_surface_record(text: str, surface_id: str, status: str) -> str | None:
    records = release_statement_surface_records(text, surface_id, status)
    if len(records) != 1:
        return None
    return records[0][1]


def release_statement_recorded_outcome(text: str | None, surface_id: str) -> str | None:
    if text is None:
        return None
    records = release_statement_surface_records(text, surface_id)
    if len(records) > 1:
        return "duplicate-or-mixed"
    if not records:
        return None
    return records[0][0]


def release_statement_duplicate_or_mixed_records(text: str, surface_id: str) -> bool:
    records = release_statement_surface_records(text, surface_id)
    if len(records) > 1:
        return True
    return False


def required_release_statement_text(requirement: str) -> str | None:
    lowered = requirement.lower()
    marker = "the v1 release statement states that "
    if lowered.startswith(marker):
        return requirement[len(marker) :]
    if lowered.startswith("the v1 release statement names "):
        return None
    if "v1_completion_required changes only" in lowered:
        return None
    return requirement


def required_release_statement_outcomes(surface: dict[str, Any]) -> set[str]:
    contract = surface.get("v1_decision_contract")
    if not isinstance(contract, dict):
        status = surface.get("status")
        return {status} if status in {"excluded", "post-v1"} else set()
    required = as_string_list(contract.get("exclusion_requires"))
    outcomes: set[str] = set()
    surface_id = surface.get("id")
    if not isinstance(surface_id, str):
        return outcomes
    prefix = f"the v1 release statement names {surface_id} as "
    for requirement in required:
        lowered = requirement.lower()
        if not lowered.startswith(prefix.lower()):
            continue
        suffix = lowered[len(prefix) :]
        if "post-v1" in suffix:
            outcomes.add("post-v1")
        if "excluded" in suffix:
            outcomes.add("excluded")
    if outcomes:
        return outcomes
    status = surface.get("status")
    return {status} if status in {"excluded", "post-v1"} else set()


def text_has_affirmative_release_claim(text: str) -> bool:
    lowered = text.lower()
    for pattern in AFFIRMATIVE_RELEASE_CLAIM_PATTERNS:
        for match in re.finditer(pattern, lowered):
            prefix = lowered[: match.start()]
            clause_start = 0
            for boundary in CLAUSE_START_PATTERN.finditer(prefix):
                clause_start = boundary.end()
            claim_prefix = lowered[clause_start : match.start()]
            if re.search(r"\b(?:no|not|never|excluded|post-v1|post v1)\b", claim_prefix):
                continue
            claim_clause = lowered[clause_start : match.end()]
            if re.match(r"\s*(?:no|not|never|excluded|post-v1|post v1)\b", claim_clause):
                continue
            claim_match = lowered[match.start() : match.end()]
            if re.match(r"\s*(?:no|not|never|excluded|post-v1|post v1)\b", claim_match):
                continue
            return True
    return False


def release_statement_forbidden_broad_claims(text: str) -> list[str]:
    offenders: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        for pattern in FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                prefix = lowered[: match.start()]
                clause_start = 0
                for boundary in CLAUSE_START_PATTERN.finditer(prefix):
                    clause_start = boundary.end()
                clause_end = len(lowered)
                for boundary in CLAUSE_START_PATTERN.finditer(lowered, match.end()):
                    clause_end = boundary.start()
                    break
                claim_prefix = lowered[clause_start : match.start()]
                claim_clause = lowered[clause_start : match.end()]
                claim_remainder = lowered[match.end() : clause_end]
                if FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_prefix):
                    continue
                if FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATORS.search(claim_clause):
                    continue
                if FORBIDDEN_RELEASE_STATEMENT_BROAD_CLAIM_NEGATED_REMAINDER.search(claim_remainder):
                    continue
                if re.match(
                    r"\s*(?:blocked|cannot|does\s+not|do\s+not|excluded|insufficient|"
                    r"limited|must\s+not|no|not|post-v1|post v1)\b",
                    claim_clause,
                ):
                    continue
                offenders.append(f"line {line_number}: {line.strip()}")
                break
            else:
                continue
            break
    return offenders


def release_statement_record_has_contradiction(record: str) -> bool:
    lowered = record.lower()
    if re.search(
        r"\b(?:not true that|false that|it is not the case that|not the case that|"
        r"actually included|included despite|contradict)\b",
        lowered,
    ):
        return True
    if re.search(
        r"\b(?:except|other than|unless|but|however)\b[^.;\n]*"
        r"\b(?:included|available|supported|shipped)\b",
        lowered,
    ):
        return True
    return text_has_affirmative_release_claim(record)


def surface_exclusion_claim_terms(surface: dict[str, Any]) -> set[str]:
    terms = set(as_string_list(surface.get("exclusions")))
    terms.update(as_string_list(surface.get("audit_units")))
    if isinstance(surface.get("public_name"), str):
        terms.add(surface["public_name"])
    contract = surface.get("v1_decision_contract")
    if isinstance(contract, dict):
        for requirement in as_string_list(contract.get("exclusion_requires")):
            required_text = required_release_statement_text(requirement)
            if required_text is None:
                continue
            body = re.sub(r"^\s*no\s+", "", required_text, flags=re.IGNORECASE)
            body = re.sub(r"\s+(?:api\s+)?is included in v1\s*$", "", body, flags=re.IGNORECASE)
            for term in re.split(r"\s*,\s*|\s+\bor\b\s+|\s+\band\b\s+", body):
                term = term.strip(" .")
                if len(term) >= 4:
                    terms.add(term)
    return {term.lower() for term in terms if term}


def release_statement_has_surface_claim_contradiction(text: str, surface: dict[str, Any]) -> bool:
    terms = surface_exclusion_claim_terms(surface)
    if not terms:
        return False
    for line in text.splitlines():
        lowered = line.lower()
        if any(term in lowered for term in terms) and text_has_affirmative_release_claim(line):
            return True
    return False


def release_statement_satisfies_exclusion_contract(text: str, surface: dict[str, Any]) -> bool:
    contract = surface.get("v1_decision_contract")
    if not isinstance(contract, dict):
        return False
    required = as_string_list(contract.get("exclusion_requires"))
    if not required:
        return False
    surface_id = surface.get("id")
    status = surface.get("status")
    if not isinstance(surface_id, str) or status not in {"excluded", "post-v1"}:
        return False
    expected = "post-v1" if status == "post-v1" else "excluded"
    record = release_statement_surface_record(text, surface_id, expected)
    if record is None:
        return False
    lowered = record.lower()
    if release_statement_record_has_contradiction(record):
        return False
    if release_statement_has_surface_claim_contradiction(text, surface):
        return False
    required_text = [item for item in (required_release_statement_text(item) for item in required) if item]
    return all(item.lower() in lowered for item in required_text)


def release_statement_satisfies_experimental_outcome(text: str, surface_id: str, status: str) -> bool:
    record = release_statement_surface_record(text, surface_id, status)
    if record is None or release_statement_record_has_contradiction(record):
        return False
    if status == "promoted":
        return True
    required_terms = CANONICAL_EXPERIMENTAL_RELEASE_STATEMENT_TEXT.get(surface_id, ())
    lowered = record.lower()
    return all(term.lower() in lowered for term in required_terms)


def repo_relative_evidence_path(raw_path: str) -> Path | None:
    path = Path(raw_path)
    if path.is_absolute():
        try:
            path.relative_to(REPO_ROOT)
        except ValueError:
            return None
    else:
        path = REPO_ROOT / path
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except (OSError, ValueError):
        return None


def evidence_path_is_specific(raw_path: str, surface_id: str) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False
    relative_text = relative.as_posix()
    if surface_id in STRICT_PROMOTION_EVIDENCE_SURFACE_IDS and relative_text.startswith("scripts/test_"):
        return False
    if relative_text in GENERIC_SCRIPT_EVIDENCE_DENYLIST:
        return False
    if not relative_text.startswith(PROMOTION_EVIDENCE_ALLOWED_PREFIXES):
        return False
    surface_tokens = [
        token
        for token in surface_id.removeprefix("obelisk.").removesuffix(".v1").replace(".", "_").split("_")
        if token
    ]
    lowered = relative_text.lower()
    return any(token.lower() in lowered for token in surface_tokens)


def evidence_path_has_non_promotional_marker(raw_path: str) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False

    def normalized_marker_text(text: str) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
        return re.sub(r"[^a-z0-9]+", "_", separated.lower()).strip("_")

    normalized_parts = [
        normalized_marker_text(part)
        for part in relative.with_suffix("").parts
    ]
    for part in normalized_parts:
        collapsed_part = part.replace("_", "")
        for marker in STRICT_PROMOTION_EVIDENCE_PATH_DENY_MARKERS:
            normalized_marker = normalized_marker_text(marker)
            collapsed_marker = normalized_marker.replace("_", "")
            if normalized_marker in part or collapsed_marker in collapsed_part:
                return True
    return False


def evidence_path_exists(raw_path: str, *, allow_generic_dirs: bool) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False
    path = REPO_ROOT / relative
    if not path.exists():
        return False
    if path.is_dir():
        return allow_generic_dirs and relative.as_posix() in ALLOWED_GENERIC_EVIDENCE_DIRS
    return path.is_file()


def evidence_has_non_promotional_schema_marker(
    value: Any,
    *,
    parent_key: str | None = None,
) -> bool:
    normalized_key = parent_key.lower().replace("-", "_") if isinstance(parent_key, str) else None
    if normalized_key in STRICT_PROMOTION_EVIDENCE_SCHEMA_KEYS:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
        if STRICT_PROMOTION_EVIDENCE_SCHEMA_DENY_MARKERS.search(text):
            return True
    if isinstance(value, dict):
        for key, item in value.items():
            next_key = key if isinstance(key, str) else None
            if evidence_has_non_promotional_schema_marker(item, parent_key=next_key):
                return True
    if isinstance(value, list):
        return any(
            evidence_has_non_promotional_schema_marker(item, parent_key=parent_key)
            for item in value
        )
    return False


def surface_has_promotion_evidence(surface: dict[str, Any]) -> bool:
    evidence = surface.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        return False
    surface_id = surface.get("id")
    if not isinstance(surface_id, str):
        return False
    allow_generic_dirs = surface_id not in STRICT_PROMOTION_EVIDENCE_SURFACE_IDS
    if not allow_generic_dirs:
        if evidence.get("surface_id") != surface_id:
            return False
        if evidence.get("promotion_status") != "promoted":
            return False
        if evidence.get("public_sdk_ready") is not True:
            return False
        if evidence_has_non_promotional_schema_marker(evidence):
            return False
        if not isinstance(evidence.get("abi_tests"), list) or not evidence["abi_tests"]:
            return False
        if not isinstance(evidence.get("sdk_consumer_tests"), list) or not evidence["sdk_consumer_tests"]:
            return False
    def evidence_value_valid(value: Any, *, evidence_key: str | None = None) -> bool:
        def item_valid(item: str) -> bool:
            relative = repo_relative_evidence_path(item)
            if relative is None:
                return False
            relative_text = relative.as_posix()
            if not allow_generic_dirs and evidence_key in {"sdk_consumer_tests", "installed_sdk_consumer_tests"}:
                if not (
                    relative_text == "tests/sdk_consumer"
                    or relative_text.startswith("tests/sdk_consumer/")
                    or relative_text == "tests/sdk_installed_consumer"
                    or relative_text.startswith("tests/sdk_installed_consumer/")
                ):
                    return False
            if not allow_generic_dirs and evidence_key == "abi_tests":
                if not (relative_text.startswith("tests/abi/") or relative_text.startswith("tests/core/")):
                    return False
            if not allow_generic_dirs and evidence_path_has_non_promotional_marker(item):
                return False
            return evidence_path_exists(item, allow_generic_dirs=allow_generic_dirs) and (
                allow_generic_dirs or evidence_path_is_specific(item, surface_id)
            )

        if isinstance(value, list) and value:
            return all(isinstance(item, str) and item_valid(item) for item in value)
        return isinstance(value, str) and item_valid(value)

    if not allow_generic_dirs and not (
        evidence_value_valid(evidence.get("abi_tests"), evidence_key="abi_tests")
        and evidence_value_valid(evidence.get("sdk_consumer_tests"), evidence_key="sdk_consumer_tests")
    ):
        return False

    machine_keys = (
        "abi_tests",
        "sdk_consumer_tests",
        "installed_sdk_consumer_tests",
        "tests",
        "install_gate",
    )
    for key in machine_keys:
        if evidence_value_valid(evidence.get(key), evidence_key=key):
            return True
    return False


def surface_declares_completion_equivalent(surface: dict[str, Any], blocker_id: str) -> bool:
    equivalents = as_string_list(surface.get("v1_completion_equivalent_for"))
    equivalents.extend(as_string_list(surface.get("completion_equivalent_for")))
    return blocker_id in equivalents


def explicit_completion_equivalent_satisfies(
    blocker_id: str,
    equivalent_surface_ids: list[str],
    surfaces_by_id: dict[str, dict[str, Any]],
) -> str | None:
    for equivalent_id in equivalent_surface_ids:
        equivalent_surface = surfaces_by_id.get(equivalent_id)
        if not equivalent_surface:
            continue
        if equivalent_surface.get("status") != "promoted":
            continue
        if not surface_declares_completion_equivalent(equivalent_surface, blocker_id):
            continue
        if not surface_has_promotion_evidence(equivalent_surface):
            continue
        return equivalent_id
    return None


def complete_sdk_minimum_promoted_demand_family_gaps(
    surfaces_by_id: dict[str, dict[str, Any]],
    stable_contract: dict[str, Any] | None,
) -> tuple[list[str], dict[str, str]]:
    explicit_equivalents = as_string_map(
        stable_contract.get("promoted_demand_family_equivalents") if stable_contract else None
    )
    gaps: list[str] = []
    satisfied_by: dict[str, str] = {}
    for blocker_id in sorted(CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES):
        surface = surfaces_by_id.get(blocker_id)
        if surface and surface.get("status") == "promoted":
            continue
        equivalent_id = explicit_completion_equivalent_satisfies(
            blocker_id,
            explicit_equivalents.get(blocker_id, []),
            surfaces_by_id,
        )
        if equivalent_id is not None:
            satisfied_by[blocker_id] = equivalent_id
            continue
        gaps.append(blocker_id)
    return gaps, satisfied_by


def promotion_evidence_key_is_negative_context(parent_key: str | None) -> bool:
    if parent_key is None:
        return False
    normalized = parent_key.lower().replace("-", "_")
    return any(marker in normalized for marker in PROMOTION_EVIDENCE_NEGATIVE_CONTEXT_KEYS)


def evidence_value_contains_positive_term(
    value: Any,
    term: str,
    *,
    parent_key: str | None = None,
) -> bool:
    if promotion_evidence_key_is_negative_context(parent_key):
        return False
    if isinstance(value, dict):
        for key, item in value.items():
            next_key = key if isinstance(key, str) else None
            if evidence_value_contains_positive_term(item, term, parent_key=next_key):
                return True
        return False
    if isinstance(value, list):
        return any(
            evidence_value_contains_positive_term(item, term, parent_key=parent_key) for item in value
        )
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = str(value)
    else:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
    if term.lower() not in text.lower():
        return False
    return PROMOTION_EVIDENCE_NEGATIVE_TERM_CONTEXT.search(text) is None


def surface_missing_required_promotion_evidence(surface: dict[str, Any]) -> list[str]:
    surface_id = surface.get("id")
    if not isinstance(surface_id, str) or surface.get("status") != "promoted":
        return []
    required_terms = PROMOTION_EVIDENCE_REQUIRED_TERMS.get(surface_id, ())
    if not required_terms:
        return []
    evidence = surface.get("evidence", {})
    return [term for term in required_terms if not evidence_value_contains_positive_term(evidence, term)]


def unresolved_promoted_surface_dependencies(
    surface: dict[str, Any],
    surfaces_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    if surface.get("status") != "promoted" and surface.get("public_abi") is not True:
        return []
    unresolved: list[str] = []
    dependency_ids = as_string_list(surface.get("depends_on"))
    surface_id = surface.get("id")
    if isinstance(surface_id, str):
        for required_dependency_id in REQUIRED_PROMOTED_SURFACE_DEPENDENCIES.get(surface_id, ()):
            if required_dependency_id not in dependency_ids:
                dependency_ids.append(required_dependency_id)
    for dependency_id in dependency_ids:
        dependency = surfaces_by_id.get(dependency_id)
        if not isinstance(dependency, dict) or dependency.get("status") != "promoted":
            unresolved.append(dependency_id)
    return unresolved


def missing_required_dependency_declarations(
    surfaces_by_id: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for surface_id, required_dependency_ids in REQUIRED_PROMOTED_SURFACE_DEPENDENCIES.items():
        surface = surfaces_by_id.get(surface_id)
        if not isinstance(surface, dict):
            continue
        declared_dependency_ids = set(as_string_list(surface.get("depends_on")))
        missing_dependencies = [
            dependency_id
            for dependency_id in required_dependency_ids
            if dependency_id not in declared_dependency_ids
        ]
        if missing_dependencies:
            missing[surface_id] = missing_dependencies
    return missing


def v1_dependency_sequence_mismatches(
    manifest: dict[str, Any],
    surfaces_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    mismatches: list[str] = []
    declared_sequence = as_string_list(manifest.get("v1_dependency_sequence"))
    chain_surfaces_present = all(surface_id in surfaces_by_id for surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE)

    if declared_sequence or chain_surfaces_present:
        if declared_sequence != list(CANONICAL_V1_DEPENDENCY_SEQUENCE):
            mismatches.append("v1_dependency_sequence")

    completion_blockers = as_string_list(manifest.get("v1_sdk_completion_blockers"))
    completion_blocker_positions = {
        surface_id: index for index, surface_id in enumerate(completion_blockers)
    }
    if all(surface_id in completion_blocker_positions for surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE):
        ordered_positions = [
            completion_blocker_positions[surface_id]
            for surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE
        ]
        if ordered_positions != sorted(ordered_positions):
            mismatches.append("v1_sdk_completion_blockers")

    return mismatches


def blocker_outcome_next_action(
    *,
    surface_id: str,
    status: str,
    manifest_outcome: str | None,
    release_statement_outcome: str | None,
    release_statement_contract_satisfied: bool,
    promotion_evidence_satisfied: bool,
) -> str:
    if status == "promoted":
        if not promotion_evidence_satisfied:
            return "keep blocked; promoted status lacks acceptable ABI and SDK-consumer evidence"
        if release_statement_outcome != "promoted":
            return "add one release-statement promoted record after reviewing evidence"
        return "promoted accounting complete; this still does not allow the stable SDK claim by itself"
    if manifest_outcome in {"post-v1", "excluded"}:
        if release_statement_contract_satisfied:
            return "release-statement outcome accounted; remaining SDK claim still depends on all blockers"
        expected = "post-v1 or excluded"
        return f"add one reviewed {expected} release-statement record satisfying this surface's exclusion contract"
    if status == "missing":
        return "restore the canonical blocker row in docs/public_sdk_surfaces.json"
    if surface_id in CANONICAL_V1_DEPENDENCY_SEQUENCE:
        return "priority dependency-chain blocker: promote with evidence or explicitly exclude before downstream permissions/commands can count"
    return "choose a reviewed v1 outcome: promote with evidence or explicitly exclude/post-v1 where the contract allows it"


def completion_blocker_outcome_rows(
    completion_blockers: list[str],
    surfaces_by_id: dict[str, dict[str, Any]],
    post_v1_or_excluded: set[str],
    release_statement_text: str | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, surface_id in enumerate(completion_blockers, start=1):
        surface = surfaces_by_id.get(surface_id, {})
        status = surface.get("status", "missing")
        status = status if isinstance(status, str) else "invalid"
        manifest_outcome = status if status in {"promoted", "post-v1", "excluded"} else None
        release_statement_outcome = release_statement_recorded_outcome(release_statement_text, surface_id)
        promotion_evidence_satisfied = bool(surface) and status == "promoted" and surface_has_promotion_evidence(surface)
        release_statement_contract_satisfied = False
        if status == "promoted":
            release_statement_contract_satisfied = release_statement_outcome == "promoted"
        elif status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            release_statement_contract_satisfied = (
                release_statement_text is not None
                and release_statement_outcome == status
                and release_statement_satisfies_exclusion_contract(release_statement_text, surface)
            )
        required_outcomes = sorted(required_release_statement_outcomes(surface)) if surface else []
        rows.append(
            {
                "surface": surface_id,
                "position": index,
                "status": status,
                "support_tier": surface.get("support_tier") if surface else None,
                "manifest_outcome": manifest_outcome,
                "release_statement_outcome": release_statement_outcome,
                "release_statement_contract_satisfied": release_statement_contract_satisfied,
                "required_release_statement_outcomes": required_outcomes,
                "promotion_evidence_satisfied": promotion_evidence_satisfied,
                "unresolved_for_complete_sdk_claim": not (
                    promotion_evidence_satisfied
                    and release_statement_contract_satisfied
                    and manifest_outcome == "promoted"
                ),
                "next_action": blocker_outcome_next_action(
                    surface_id=surface_id,
                    status=status,
                    manifest_outcome=manifest_outcome,
                    release_statement_outcome=release_statement_outcome,
                    release_statement_contract_satisfied=release_statement_contract_satisfied,
                    promotion_evidence_satisfied=promotion_evidence_satisfied,
                ),
                "non_claim": "Accounting row only; it does not authorize complete/full/production/stable SDK wording.",
            }
        )
    return rows


def completion_blocker_outcome_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    manifest_outcome_missing = [
        row["surface"] for row in rows if row.get("manifest_outcome") is None
    ]
    release_statement_outcome_missing = [
        row["surface"]
        for row in rows
        if row.get("manifest_outcome") in {"promoted", "post-v1", "excluded"}
        and row.get("release_statement_contract_satisfied") is not True
    ]
    dependency_chain_remaining = [
        row["surface"]
        for row in rows
        if row["surface"] in CANONICAL_V1_DEPENDENCY_SEQUENCE
        and row.get("manifest_outcome") != "promoted"
    ]
    return {
        "total": len(rows),
        "manifest_outcome_missing_count": len(manifest_outcome_missing),
        "release_statement_outcome_missing_count": len(release_statement_outcome_missing),
        "manifest_outcome_missing": manifest_outcome_missing,
        "release_statement_outcome_missing": release_statement_outcome_missing,
        "dependency_chain_remaining": dependency_chain_remaining,
        "dependency_chain_remaining_count": len(dependency_chain_remaining),
        "non_claim": "This summary ranks accounting gaps only; stable SDK claim approval still requires the full checker to pass.",
    }


def categorized_v1_report_sections(
    *,
    manifest: dict[str, Any],
    blockers: list[str],
    promoted_surfaces: set[str],
    experimental_surfaces: set[str],
    release_statement_text: str | None,
    release_statement_missing_blockers: list[str],
    release_statement_missing_contracts: list[str],
    release_statement_missing_experimental_outcomes: list[str],
    release_statement_duplicate_records: list[str],
    release_statement_forbidden_claims: list[str],
    completion_blockers_with_post_v1_or_excluded_outcome: list[str],
    completion_blockers_with_release_statement_post_v1_or_excluded_outcome: list[str],
    minimum_promoted_demand_family_gaps: list[str],
    minimum_promoted_demand_family_equivalents: dict[str, str],
    blocker_outcome_summary: dict[str, Any],
    unresolved_completion_blockers: list[str],
    unresolved_experimental: list[str],
    unresolved_planning_surfaces: list[str],
    promoted_without_evidence: list[str],
    promoted_missing_required_evidence_terms: dict[str, list[str]],
    promoted_dependency_failures: dict[str, list[str]],
    blocked_contract_header_symbols: dict[str, Any],
    stable_claim_allowed: bool,
    manifest_stable_claim_allowed: bool,
) -> dict[str, Any]:
    """Group the JSON report by release-accounting concern without changing gates."""

    installed_shape = manifest.get("installed_sdk_package_shape")
    package_shape_status = None
    if isinstance(installed_shape, dict):
        package_shape_status = installed_shape.get("status")

    manifest_outcome_missing = blocker_outcome_summary.get("manifest_outcome_missing", [])
    dependency_chain_remaining = blocker_outcome_summary.get("dependency_chain_remaining", [])
    if dependency_chain_remaining:
        recommended_next_action = (
            "resolve the player identity/principal critical path first, starting with "
            "approved copied runtime principal lifecycle evidence before any public "
            "identity, permissions/admin, command response, or commands/replies ABI"
        )
    elif manifest_outcome_missing:
        recommended_next_action = (
            "choose reviewed v1 outcomes for planning blockers before counting them "
            "toward a complete SDK release statement"
        )
    elif release_statement_missing_blockers:
        recommended_next_action = (
            "add reviewed scoped release-statement records for manifest post-v1 or "
            "excluded blockers without treating bookkeeping as promoted SDK support"
        )
    else:
        recommended_next_action = (
            "promote remaining demand-family surfaces with evidence or explicitly keep "
            "them out of the complete SDK claim"
        )

    runtime_blocker_codes = [
        blocker
        for blocker in blockers
        if blocker
        in {
            "blocked_public_contract_header_symbols_detected",
            "canonical_surface_id_missing",
            "canonical_v1_completion_blocker_missing",
            "debug_only_surface_promoted",
            "non_promoted_surface_has_public_abi",
            "non_promoted_surface_has_public_contract",
            "planning_surfaces_unresolved_for_v1_claim",
            "promoted_experimental_surfaces_unresolved",
            "promoted_surface_dependency_unresolved",
            "promoted_surface_evidence_missing",
            "promoted_surface_required_evidence_terms_missing",
            "required_surface_dependency_declaration_missing",
            "surface_id_missing",
            "top_level_planning_surfaces_unresolved_for_v1_claim",
            "v1_dependency_sequence_mismatch",
            "v1_sdk_completion_blockers_unresolved",
        }
    ]

    return {
        "no_live_progress": {
            "live_server_required_for_this_report": False,
            "promoted_foundation_surfaces": sorted(promoted_surfaces),
            "experimental_copied_data_seeds": sorted(experimental_surfaces),
            "package_shape_evidence_status": package_shape_status,
            "stable_claim_allowed": stable_claim_allowed,
            "stable_release_contract_claim_allowed": manifest_stable_claim_allowed,
            "non_claim": (
                "These are no-live inventory/package-shape progress signals only; they do not "
                "satisfy runtime gameplay promotion evidence or authorize complete/full/"
                "production/stable SDK wording."
            ),
        },
        "release_statement_bookkeeping": {
            "release_statement_present": release_statement_text is not None,
            "manifest_post_v1_or_excluded_outcomes": (
                completion_blockers_with_post_v1_or_excluded_outcome
            ),
            "release_statement_post_v1_or_excluded_outcomes": (
                completion_blockers_with_release_statement_post_v1_or_excluded_outcome
            ),
            "missing_blocker_outcomes": sorted(set(release_statement_missing_blockers)),
            "missing_exclusion_contracts": sorted(set(release_statement_missing_contracts)),
            "missing_experimental_outcomes": sorted(
                set(release_statement_missing_experimental_outcomes)
            ),
            "duplicate_or_mixed_records": sorted(set(release_statement_duplicate_records)),
            "forbidden_broad_claims": release_statement_forbidden_claims,
            "non_claim": (
                "Release-statement rows record reviewed promoted/excluded/post-v1 outcomes; "
                "bookkeeping alone never approves the stable SDK claim."
            ),
        },
        "promoted_demand_gaps": {
            "minimum_promoted_demand_family_count": len(
                CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
            ),
            "minimum_promoted_demand_family_gaps": minimum_promoted_demand_family_gaps,
            "minimum_promoted_demand_family_equivalents": (
                minimum_promoted_demand_family_equivalents
            ),
            "all_minimum_demand_families_promoted_or_equivalent": not minimum_promoted_demand_family_gaps,
            "claim_blocker_active": "complete_sdk_claim_requires_promoted_demand_families"
            in blockers,
            "non_claim": (
                "Excluded/post-v1 outcomes do not satisfy promoted-demand requirements; "
                "demand families need promoted surfaces or explicit promoted equivalents."
            ),
        },
        "runtime_required_blockers": {
            "blocker_codes": sorted(set(runtime_blocker_codes)),
            "dependency_chain_remaining": blocker_outcome_summary.get(
                "dependency_chain_remaining",
                [],
            ),
            "manifest_outcome_missing": blocker_outcome_summary.get(
                "manifest_outcome_missing",
                [],
            ),
            "unresolved_completion_blockers": sorted(set(unresolved_completion_blockers)),
            "unresolved_experimental_surfaces": sorted(set(unresolved_experimental)),
            "unresolved_planning_surfaces": sorted(set(unresolved_planning_surfaces)),
            "promoted_surfaces_without_evidence": sorted(set(promoted_without_evidence)),
            "promoted_surfaces_missing_required_evidence_terms": {
                surface_id: sorted(set(terms))
                for surface_id, terms in sorted(promoted_missing_required_evidence_terms.items())
            },
            "promoted_surfaces_with_unresolved_dependencies": {
                surface_id: sorted(set(dependencies))
                for surface_id, dependencies in sorted(promoted_dependency_failures.items())
            },
            "blocked_public_contract_header_symbol_surfaces": sorted(
                {
                    drift.get("surface")
                    for drift in blocked_contract_header_symbols.values()
                    if isinstance(drift, dict) and isinstance(drift.get("surface"), str)
                }
            ),
            "non_claim": (
                "These are SDK/runtime promotion blockers and header-drift guardrails; they "
                "must be resolved by promotion evidence or reviewed non-promoted outcomes "
                "before stable SDK wording is possible."
            ),
        },
        "next_v1_work": {
            "critical_path": list(dependency_chain_remaining),
            "release_statement_bookkeeping_required": sorted(set(release_statement_missing_blockers)),
            "product_decision_required": list(manifest_outcome_missing),
            "runtime_or_promotion_required": sorted(
                set(unresolved_completion_blockers)
                | set(dependency_chain_remaining)
                | set(minimum_promoted_demand_family_gaps)
            ),
            "experimental_outcome_required": sorted(set(unresolved_experimental)),
            "recommended_next_action": recommended_next_action,
            "non_claim": (
                "This section prioritizes work only; it does not change readiness, "
                "promote ABI, or authorize complete/full/production/stable SDK wording."
            ),
        },
    }


def build_report(
    manifest_path: Path,
    release_statement_path: Path | None = None,
    public_header_path: Path = DEFAULT_PUBLIC_HEADER,
    contract_decisions_dir: Path = DEFAULT_CONTRACT_DECISIONS_DIR,
) -> dict[str, Any]:
    manifest, blockers = load_manifest(manifest_path)
    release_statement_text, release_statement_blockers = load_release_statement(release_statement_path)
    blockers.extend(release_statement_blockers)
    blocked_contract_header_symbols, contract_symbol_blockers = blocked_contract_public_header_symbol_drift(
        public_header_path,
        contract_decisions_dir,
    )
    blockers.extend(contract_symbol_blockers)
    missing_required_contract_decisions = missing_required_contract_decision_manifests(contract_decisions_dir)
    if missing_required_contract_decisions:
        blockers.append("required_public_contract_decision_manifest_missing")
    if manifest is None:
        return {
            "schema": "obelisk.public-sdk-v1-completion-check.v1",
            "status": "blocked",
            "ready": False,
            "manifest": str(manifest_path),
            "release_statement": str(release_statement_path) if release_statement_path else None,
            "public_header": str(public_header_path),
            "contract_decisions_dir": str(contract_decisions_dir),
            "blocked_public_contract_header_symbols": blocked_contract_header_symbols,
            "missing_required_public_contract_decision_manifests": missing_required_contract_decisions,
            "blockers": blockers,
        }

    surfaces = manifest.get("surfaces")
    surface_rows = surfaces if isinstance(surfaces, list) else []
    seen_surface_ids: set[str] = set()
    duplicate_surface_ids: list[str] = []
    for surface in surface_rows:
        if not isinstance(surface, dict) or not isinstance(surface.get("id"), str):
            continue
        surface_id = surface["id"]
        if surface_id in seen_surface_ids:
            duplicate_surface_ids.append(surface_id)
        seen_surface_ids.add(surface_id)
    surfaces_by_id = {
        surface.get("id"): surface
        for surface in surface_rows
        if isinstance(surface, dict) and isinstance(surface.get("id"), str)
    }
    decision_backed_surface_ids = public_contract_decision_surfaces_for_header(
        public_header_path,
        contract_decisions_dir,
    )
    manifest_contract_header_symbols, manifest_symbol_blockers = manifest_public_header_symbol_drift(
        public_header_path,
        manifest_path,
        surfaces_by_id,
        decision_backed_surface_ids,
    )
    blocked_contract_header_symbols.update(manifest_contract_header_symbols)
    blockers.extend(manifest_symbol_blockers)

    if manifest.get("schema") != "obelisk.public-sdk-surfaces.v1":
        blockers.append("schema_mismatch")
    if manifest.get("sdk_version") != "v1.0":
        blockers.append("sdk_version_not_v1")

    stable_contract = manifest.get("stable_release_contract")
    if not isinstance(stable_contract, dict):
        blockers.append("stable_release_contract_missing")
        manifest_stable_claim_allowed = False
        missing_stable_claim_requires = list(CANONICAL_STABLE_RELEASE_CLAIM_REQUIRES)
        missing_stable_not_sufficient = list(CANONICAL_STABLE_RELEASE_NOT_SUFFICIENT)
    else:
        manifest_stable_claim_allowed = stable_contract.get("claim_allowed") is True
        if not manifest_stable_claim_allowed:
            blockers.append("stable_release_contract_claim_not_allowed")
        stable_claim_requires = set(as_string_list(stable_contract.get("claim_requires")))
        missing_stable_claim_requires = [
            requirement
            for requirement in CANONICAL_STABLE_RELEASE_CLAIM_REQUIRES
            if requirement not in stable_claim_requires
        ]
        stable_not_sufficient = set(as_string_list(stable_contract.get("not_sufficient")))
        missing_stable_not_sufficient = [
            item
            for item in CANONICAL_STABLE_RELEASE_NOT_SUFFICIENT
            if item not in stable_not_sufficient
        ]
    if missing_stable_claim_requires:
        blockers.append("stable_release_contract_claim_requires_incomplete")
    if missing_stable_not_sufficient:
        blockers.append("stable_release_contract_not_sufficient_incomplete")

    if manifest.get("v1_completion_required") is not True:
        blockers.append("v1_completion_required_false")

    minimum_promoted_demand_family_gaps, minimum_promoted_demand_family_equivalents = (
        complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract if isinstance(stable_contract, dict) else None,
        )
    )
    missing_dependency_declarations = missing_required_dependency_declarations(surfaces_by_id)
    dependency_sequence_mismatches = v1_dependency_sequence_mismatches(manifest, surfaces_by_id)

    promoted_surfaces = set(as_string_list(manifest.get("promoted_surfaces")))
    experimental_surfaces = set(as_string_list(manifest.get("experimental_surfaces")))
    planning_surfaces = set(as_string_list(manifest.get("planning_surfaces")))
    status_experimental_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") == "promoted-experimental-only"
    }
    status_planning_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") == "planning"
    }
    completion_blockers = as_string_list(manifest.get("v1_sdk_completion_blockers"))
    completion_blocker_set = set(completion_blockers)
    post_v1_or_excluded = set(as_string_list(manifest.get("post_v1_or_excluded_surfaces")))
    status_post_v1_or_excluded_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") in {"post-v1", "excluded"}
    }
    debug_only_surfaces = set(as_string_list(manifest.get("debug_only_surfaces")))
    canonical_debug_only_present = CANONICAL_DEBUG_ONLY_SURFACE_IDS & set(surfaces_by_id)

    unresolved_experimental: list[str] = []
    unresolved_completion_blockers: list[str] = []
    unresolved_planning_surfaces: list[str] = []
    missing_surfaces: list[str] = []
    missing_canonical_surfaces = sorted(CANONICAL_SURFACE_IDS - set(surfaces_by_id))
    missing_canonical_completion_blockers = sorted(CANONICAL_V1_COMPLETION_BLOCKERS - completion_blocker_set)
    promoted_without_contract: list[str] = []
    promoted_without_evidence: list[str] = []
    non_promoted_with_contract: list[str] = []
    promoted_list_mismatches: list[str] = []
    experimental_list_mismatches: list[str] = []
    planning_list_mismatches: list[str] = []
    post_v1_or_excluded_list_mismatches: list[str] = []
    release_statement_missing_blockers: list[str] = []
    release_statement_missing_contracts: list[str] = []
    release_statement_missing_experimental_outcomes: list[str] = []
    release_statement_duplicate_records: list[str] = []
    release_statement_forbidden_claims: list[str] = []
    missing_completion_blocker_exclusion_contracts: list[str] = []
    debug_only_promoted: list[str] = []
    promoted_dependency_failures: dict[str, list[str]] = {}
    promoted_missing_required_evidence_terms: dict[str, list[str]] = {}
    non_promoted_with_public_abi: list[str] = []

    if manifest_stable_claim_allowed and manifest.get("v1_completion_required") is True and release_statement_text is None:
        blockers.append("release_statement_required_for_v1_completion")

    if not canonical_debug_only_present.issubset(debug_only_surfaces):
        blockers.append("debug_only_surface_list_missing_canonical_ids")

    if experimental_surfaces != status_experimental_surfaces:
        experimental_list_mismatches = sorted(experimental_surfaces ^ status_experimental_surfaces)
    if planning_surfaces != status_planning_surfaces:
        planning_list_mismatches = sorted(planning_surfaces ^ status_planning_surfaces)
    if post_v1_or_excluded != status_post_v1_or_excluded_surfaces:
        post_v1_or_excluded_list_mismatches = sorted(
            post_v1_or_excluded ^ status_post_v1_or_excluded_surfaces
        )

    experimental_outcome_surface_ids = (
        experimental_surfaces
        | status_experimental_surfaces
        | (CANONICAL_EXPERIMENTAL_SURFACE_IDS & set(surfaces_by_id))
    )
    for surface_id in sorted(experimental_outcome_surface_ids):
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
            unresolved_experimental.append(surface_id)
            continue
        status = surface.get("status")
        if status == "promoted":
            if release_statement_text is None:
                release_statement_missing_experimental_outcomes.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_satisfies_experimental_outcome(release_statement_text, surface_id, status):
                release_statement_missing_experimental_outcomes.append(surface_id)
            continue
        if status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            if release_statement_text is None:
                release_statement_missing_experimental_outcomes.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_satisfies_experimental_outcome(release_statement_text, surface_id, status):
                release_statement_missing_experimental_outcomes.append(surface_id)
            continue
        unresolved_experimental.append(surface_id)

    for surface_id in completion_blockers:
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
            unresolved_completion_blockers.append(surface_id)
            continue
        status = surface.get("status")
        if status == "promoted":
            if not surface_has_promotion_evidence(surface):
                promoted_without_evidence.append(surface_id)
            if release_statement_text is None:
                release_statement_missing_blockers.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_names_outcome(release_statement_text, surface_id, status):
                release_statement_missing_blockers.append(surface_id)
            continue
        if status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            if surface_id in CANONICAL_V1_COMPLETION_BLOCKERS:
                contract = surface.get("v1_decision_contract")
                if not isinstance(contract, dict) or not as_string_list(contract.get("exclusion_requires")):
                    missing_completion_blocker_exclusion_contracts.append(surface_id)
                    continue
                allowed_outcomes = required_release_statement_outcomes(surface)
                if status not in allowed_outcomes:
                    release_statement_missing_contracts.append(surface_id)
                    continue
            if release_statement_text is None:
                release_statement_missing_blockers.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_names_outcome(release_statement_text, surface_id, status):
                release_statement_missing_blockers.append(surface_id)
            elif not release_statement_satisfies_exclusion_contract(release_statement_text, surface):
                release_statement_missing_contracts.append(surface_id)
            continue
        if surface_id in CANONICAL_V1_COMPLETION_BLOCKERS:
            contract = surface.get("v1_decision_contract")
            if not isinstance(contract, dict) or not as_string_list(contract.get("exclusion_requires")):
                missing_completion_blocker_exclusion_contracts.append(surface_id)
        unresolved_completion_blockers.append(surface_id)

    for surface_id, surface in surfaces_by_id.items():
        status = surface.get("status")
        contract = surface.get("public_contract")
        contract_items = contract if isinstance(contract, list) else []
        if surface_id in debug_only_surfaces or surface_id in CANONICAL_DEBUG_ONLY_SURFACE_IDS:
            if status == "promoted" or surface_id in promoted_surfaces:
                debug_only_promoted.append(surface_id)
        if status == "promoted":
            if surface_id not in promoted_surfaces:
                promoted_list_mismatches.append(surface_id)
            if not contract_items:
                promoted_without_contract.append(surface_id)
            if not surface_has_promotion_evidence(surface):
                promoted_without_evidence.append(surface_id)
            missing_required_terms = surface_missing_required_promotion_evidence(surface)
            if missing_required_terms:
                promoted_missing_required_evidence_terms[surface_id] = missing_required_terms
        elif status == "planning":
            unresolved_planning_surfaces.append(surface_id)
        elif status != "promoted-experimental-only" and contract_items:
            non_promoted_with_contract.append(surface_id)
        if status != "promoted" and surface.get("public_abi") is True:
            non_promoted_with_public_abi.append(surface_id)
        unresolved_dependencies = unresolved_promoted_surface_dependencies(surface, surfaces_by_id)
        if unresolved_dependencies:
            promoted_dependency_failures[surface_id] = unresolved_dependencies

    for surface_id in sorted(promoted_surfaces):
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
        elif surface.get("status") != "promoted":
            promoted_list_mismatches.append(surface_id)

    missing_surfaces.extend(missing_canonical_surfaces)
    unresolved_completion_blockers.extend(missing_canonical_completion_blockers)

    if missing_surfaces:
        blockers.append("surface_id_missing")
    if duplicate_surface_ids:
        blockers.append("duplicate_surface_id")
    if missing_canonical_surfaces:
        blockers.append("canonical_surface_id_missing")
    if missing_canonical_completion_blockers:
        blockers.append("canonical_v1_completion_blocker_missing")
    if (
        manifest_stable_claim_allowed
        and manifest.get("v1_completion_required") is True
        and minimum_promoted_demand_family_gaps
    ):
        blockers.append("complete_sdk_claim_requires_promoted_demand_families")
    if unresolved_experimental:
        blockers.append("promoted_experimental_surfaces_unresolved")
    if unresolved_completion_blockers:
        blockers.append("v1_sdk_completion_blockers_unresolved")
    if unresolved_planning_surfaces:
        blockers.append("planning_surfaces_unresolved_for_v1_claim")
    if planning_surfaces:
        blockers.append("top_level_planning_surfaces_unresolved_for_v1_claim")
    if missing_completion_blocker_exclusion_contracts:
        blockers.append("completion_blocker_exclusion_contract_missing")
    if debug_only_promoted:
        blockers.append("debug_only_surface_promoted")
    if promoted_without_contract:
        blockers.append("promoted_surface_public_contract_missing")
    if promoted_without_evidence:
        blockers.append("promoted_surface_evidence_missing")
    if promoted_missing_required_evidence_terms:
        blockers.append("promoted_surface_required_evidence_terms_missing")
    if promoted_dependency_failures:
        blockers.append("promoted_surface_dependency_unresolved")
    if missing_dependency_declarations:
        blockers.append("required_surface_dependency_declaration_missing")
    if dependency_sequence_mismatches:
        blockers.append("v1_dependency_sequence_mismatch")
    if non_promoted_with_contract:
        blockers.append("non_promoted_surface_has_public_contract")
    if non_promoted_with_public_abi:
        blockers.append("non_promoted_surface_has_public_abi")
    if promoted_list_mismatches:
        blockers.append("promoted_surface_list_mismatch")
    if experimental_list_mismatches:
        blockers.append("experimental_surface_list_mismatch")
    if planning_list_mismatches:
        blockers.append("planning_surface_list_mismatch")
    if post_v1_or_excluded_list_mismatches:
        blockers.append("post_v1_or_excluded_surface_list_mismatch")
    if release_statement_missing_blockers:
        blockers.append("release_statement_missing_non_promoted_blocker_outcomes")
    if release_statement_missing_contracts:
        blockers.append("release_statement_missing_exclusion_contract")
    if release_statement_missing_experimental_outcomes:
        blockers.append("release_statement_missing_experimental_outcomes")
    if release_statement_duplicate_records:
        blockers.append("release_statement_duplicate_or_mixed_surface_records")
    if release_statement_text is not None:
        release_statement_forbidden_claims = release_statement_forbidden_broad_claims(
            release_statement_text
        )
        if release_statement_forbidden_claims:
            blockers.append("release_statement_forbidden_broad_claims")
        if "docs/sdk_v1_compatibility.md" not in release_statement_text.lower():
            blockers.append("release_statement_missing_sdk_compatibility_reference")
        if "docs/public_sdk_surfaces.json" not in release_statement_text.lower():
            blockers.append("release_statement_missing_public_sdk_surfaces_reference")
    if blocked_contract_header_symbols:
        blockers.append("blocked_public_contract_header_symbols_detected")

    completion_blocker_statuses = {
        surface_id: surfaces_by_id.get(surface_id, {}).get("status", "missing")
        for surface_id in completion_blockers
    }
    completion_blockers_with_promoted_outcome = sorted(
        surface_id
        for surface_id, status in completion_blocker_statuses.items()
        if status == "promoted"
    )
    completion_blockers_with_post_v1_or_excluded_outcome = sorted(
        surface_id
        for surface_id, status in completion_blocker_statuses.items()
        if status in {"post-v1", "excluded"}
    )
    completion_blockers_with_release_statement_post_v1_or_excluded_outcome = sorted(
        surface_id
        for surface_id in completion_blockers_with_post_v1_or_excluded_outcome
        if release_statement_text is not None
        and surface_id in post_v1_or_excluded
        and not release_statement_duplicate_or_mixed_records(release_statement_text, surface_id)
        and release_statement_satisfies_exclusion_contract(
            release_statement_text,
            surfaces_by_id.get(surface_id, {}),
        )
    )
    completion_blockers_without_manifest_outcome = sorted(
        surface_id
        for surface_id, status in completion_blocker_statuses.items()
        if status not in {"promoted", "post-v1", "excluded"}
    )
    completion_blocker_total = len(completion_blockers)
    blocker_outcome_rows = completion_blocker_outcome_rows(
        completion_blockers,
        surfaces_by_id,
        post_v1_or_excluded,
        release_statement_text,
    )
    blocker_outcome_summary = completion_blocker_outcome_summary(blocker_outcome_rows)
    ready = not blockers
    stable_claim_allowed = manifest_stable_claim_allowed and ready
    report_sections = categorized_v1_report_sections(
        manifest=manifest,
        blockers=blockers,
        promoted_surfaces=promoted_surfaces,
        experimental_surfaces=experimental_surfaces,
        release_statement_text=release_statement_text,
        release_statement_missing_blockers=release_statement_missing_blockers,
        release_statement_missing_contracts=release_statement_missing_contracts,
        release_statement_missing_experimental_outcomes=release_statement_missing_experimental_outcomes,
        release_statement_duplicate_records=release_statement_duplicate_records,
        release_statement_forbidden_claims=release_statement_forbidden_claims,
        completion_blockers_with_post_v1_or_excluded_outcome=(
            completion_blockers_with_post_v1_or_excluded_outcome
        ),
        completion_blockers_with_release_statement_post_v1_or_excluded_outcome=(
            completion_blockers_with_release_statement_post_v1_or_excluded_outcome
        ),
        minimum_promoted_demand_family_gaps=minimum_promoted_demand_family_gaps,
        minimum_promoted_demand_family_equivalents=minimum_promoted_demand_family_equivalents,
        blocker_outcome_summary=blocker_outcome_summary,
        unresolved_completion_blockers=unresolved_completion_blockers,
        unresolved_experimental=unresolved_experimental,
        unresolved_planning_surfaces=unresolved_planning_surfaces,
        promoted_without_evidence=promoted_without_evidence,
        promoted_missing_required_evidence_terms=promoted_missing_required_evidence_terms,
        promoted_dependency_failures=promoted_dependency_failures,
        blocked_contract_header_symbols=blocked_contract_header_symbols,
        stable_claim_allowed=stable_claim_allowed,
        manifest_stable_claim_allowed=manifest_stable_claim_allowed,
    )

    return {
        "schema": "obelisk.public-sdk-v1-completion-check.v1",
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "manifest": str(manifest_path),
        "release_statement": str(release_statement_path) if release_statement_path else None,
        "public_header": str(public_header_path),
        "contract_decisions_dir": str(contract_decisions_dir),
        "missing_required_public_contract_decision_manifests": missing_required_contract_decisions,
        "sdk_version": manifest.get("sdk_version"),
        "v1_completion_required": manifest.get("v1_completion_required"),
        "stable_claim_allowed": stable_claim_allowed,
        "stable_release_contract_claim_allowed": manifest_stable_claim_allowed,
        "stable_release_contract_missing_claim_requires": missing_stable_claim_requires,
        "stable_release_contract_missing_not_sufficient": missing_stable_not_sufficient,
        "minimum_promoted_demand_families": sorted(CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES),
        "minimum_promoted_demand_family_gaps": minimum_promoted_demand_family_gaps,
        "minimum_promoted_demand_family_equivalents": minimum_promoted_demand_family_equivalents,
        "blockers": blockers,
        "unresolved_experimental_surfaces": sorted(set(unresolved_experimental)),
        "unresolved_completion_blockers": sorted(set(unresolved_completion_blockers)),
        "unresolved_planning_surfaces": sorted(set(unresolved_planning_surfaces)),
        "top_level_planning_surfaces": sorted(planning_surfaces),
        "planning_list_mismatches": planning_list_mismatches,
        "post_v1_or_excluded_list_mismatches": post_v1_or_excluded_list_mismatches,
        "debug_only_promoted_surfaces": sorted(set(debug_only_promoted)),
        "missing_completion_blocker_exclusion_contracts": sorted(
            set(missing_completion_blocker_exclusion_contracts)
        ),
        "missing_surfaces": sorted(set(missing_surfaces)),
        "duplicate_surface_ids": sorted(set(duplicate_surface_ids)),
        "promoted_without_public_contract": sorted(set(promoted_without_contract)),
        "missing_canonical_surfaces": missing_canonical_surfaces,
        "missing_canonical_completion_blockers": missing_canonical_completion_blockers,
        "promoted_surfaces_without_evidence": sorted(set(promoted_without_evidence)),
        "promoted_surfaces_missing_required_evidence_terms": {
            surface_id: sorted(set(terms))
            for surface_id, terms in sorted(promoted_missing_required_evidence_terms.items())
        },
        "promoted_surfaces_with_unresolved_dependencies": {
            surface_id: sorted(set(dependencies))
            for surface_id, dependencies in sorted(promoted_dependency_failures.items())
        },
        "surfaces_missing_required_dependency_declarations": {
            surface_id: sorted(set(dependencies))
            for surface_id, dependencies in sorted(missing_dependency_declarations.items())
        },
        "v1_dependency_sequence": as_string_list(manifest.get("v1_dependency_sequence")),
        "v1_dependency_sequence_expected": list(CANONICAL_V1_DEPENDENCY_SEQUENCE),
        "v1_dependency_sequence_mismatches": sorted(set(dependency_sequence_mismatches)),
        "promoted_blockers_without_evidence": sorted(set(promoted_without_evidence) & completion_blocker_set),
        "non_promoted_with_public_contract": sorted(set(non_promoted_with_contract)),
        "non_promoted_with_public_abi": sorted(set(non_promoted_with_public_abi)),
        "promoted_list_mismatches": sorted(set(promoted_list_mismatches)),
        "experimental_list_mismatches": sorted(set(experimental_list_mismatches)),
        "release_statement_missing_blocker_outcomes": sorted(set(release_statement_missing_blockers)),
        "release_statement_missing_exclusion_contracts": sorted(set(release_statement_missing_contracts)),
        "release_statement_missing_experimental_outcomes": sorted(set(release_statement_missing_experimental_outcomes)),
        "release_statement_duplicate_or_mixed_records": sorted(set(release_statement_duplicate_records)),
        "release_statement_forbidden_broad_claims": release_statement_forbidden_claims,
        "blocked_public_contract_header_symbols": blocked_contract_header_symbols,
        "v1_sdk_blocker_outcomes": blocker_outcome_rows,
        "v1_sdk_blocker_outcome_summary": blocker_outcome_summary,
        "v1_sdk_report_sections": report_sections,
        "v1_sdk_progress": {
            "completion_blocker_total": completion_blocker_total,
            "completion_blockers_with_promoted_outcome": completion_blockers_with_promoted_outcome,
            "completion_blockers_with_post_v1_or_excluded_outcome": (
                completion_blockers_with_post_v1_or_excluded_outcome
            ),
            "completion_blockers_with_manifest_post_v1_or_excluded_outcome": (
                completion_blockers_with_post_v1_or_excluded_outcome
            ),
            "completion_blockers_with_release_statement_post_v1_or_excluded_outcome": (
                completion_blockers_with_release_statement_post_v1_or_excluded_outcome
            ),
            "completion_blockers_with_release_statement_post_v1_or_excluded_outcome_count": len(
                completion_blockers_with_release_statement_post_v1_or_excluded_outcome
            ),
            "completion_blockers_without_manifest_outcome": completion_blockers_without_manifest_outcome,
            "completion_blockers_without_manifest_outcome_count": len(
                completion_blockers_without_manifest_outcome
            ),
            "unresolved_completion_blocker_count": len(set(unresolved_completion_blockers)),
            "unresolved_experimental_surface_count": len(set(unresolved_experimental)),
            "minimum_promoted_demand_family_gap_count": len(minimum_promoted_demand_family_gaps),
            "manifest_outcome_missing_count": blocker_outcome_summary["manifest_outcome_missing_count"],
            "release_statement_outcome_missing_count": (
                blocker_outcome_summary["release_statement_outcome_missing_count"]
            ),
            "dependency_chain_remaining_count": blocker_outcome_summary[
                "dependency_chain_remaining_count"
            ],
            "release_statement_required_for_completion_claim": release_statement_text is None,
            "stable_claim_allowed": stable_claim_allowed,
            "stable_release_contract_claim_allowed": manifest_stable_claim_allowed,
            "outcome_accounting_note": (
                "Manifest post-v1/excluded outcomes are only status accounting; release statement "
                "outcomes are counted separately after exact statement wording and exclusion-contract "
                "validation."
            ),
            "non_claim": (
                "This is accounting only; it does not authorize broad stable SDK release wording."
            ),
        },
        "non_claims": [
            "core-first release readiness, install layout, and package-shape checks do not satisfy this v1 SDK completion gate",
            "post-v1 or excluded surfaces must be named in the manifest and release statement before a stable v1 SDK claim",
        ],
    }


def add_scoped_release_statement_result(report: dict[str, Any]) -> dict[str, Any]:
    blocking_report_blockers = [
        blocker
        for blocker in report.get("blockers", [])
        if blocker not in SCOPED_RELEASE_STATEMENT_ALLOWED_BLOCKERS
    ]
    if report.get("release_statement") is None:
        blocking_report_blockers.append("scoped_release_statement_path_required")
    scoped_ready = not blocking_report_blockers
    report["scoped_release_statement"] = {
        "ready": scoped_ready,
        "stable_v1_sdk_claim_allowed": False,
        "blocking_report_blockers": sorted(set(blocking_report_blockers)),
        "allowed_remaining_blockers": sorted(
            set(report.get("blockers", [])) & SCOPED_RELEASE_STATEMENT_ALLOWED_BLOCKERS
        ),
        "non_claim": (
            "A scoped release statement records reviewed exclusions/post-v1 outcomes only; "
            "it does not authorize v1.0 stable, complete SDK, full SDK, or production SDK wording."
        ),
    }
    return report


def format_human_list(items: Any, *, limit: int = 12) -> str:
    if not isinstance(items, list) or not items:
        return "none"
    rendered = [str(item) for item in items[:limit]]
    if len(items) > limit:
        rendered.append(f"... {len(items) - limit} more")
    return ", ".join(rendered)


def blocker_guidance(report: dict[str, Any], blocker: str) -> list[str]:
    guidance: dict[str, list[str]] = {
        "stable_release_contract_claim_not_allowed": [
            "stable_release_contract.claim_allowed is not true; keep stable SDK release wording blocked.",
            "Action: leave the claim off until the manifest, blocker outcomes, and release statement all pass.",
        ],
        "v1_completion_required_false": [
            "v1_completion_required is not true.",
            "Action: do not describe this tree as a complete v1.0 SDK; finish or explicitly exclude blockers first.",
        ],
        "stable_release_contract_claim_requires_incomplete": [
            "stable_release_contract.claim_requires is missing required guardrail text.",
            f"Missing: {format_human_list(report.get('stable_release_contract_missing_claim_requires'))}.",
        ],
        "stable_release_contract_not_sufficient_incomplete": [
            "stable_release_contract.not_sufficient is missing non-claim boundaries.",
            f"Missing: {format_human_list(report.get('stable_release_contract_missing_not_sufficient'))}.",
        ],
        "promoted_experimental_surfaces_unresolved": [
            "Experimental copied-data seeds still need an explicit v1 outcome.",
            f"Surfaces: {format_human_list(report.get('unresolved_experimental_surfaces'))}.",
            "Action: promote with evidence, exclude, or mark post-v1 and name each in the release statement.",
        ],
        "v1_sdk_completion_blockers_unresolved": [
            "High-demand v1 completion blockers are still unresolved.",
            f"Surfaces: {format_human_list(report.get('unresolved_completion_blockers'))}.",
            "Action: promote with copied C ABI evidence or deliberately exclude/post-v1 where the contract allows it.",
        ],
        "complete_sdk_claim_requires_promoted_demand_families": [
            "The complete/full/production SDK claim requires promoted demand families, not only excluded or post-v1 outcomes.",
            f"Gaps: {format_human_list(report.get('minimum_promoted_demand_family_gaps'))}.",
            "Action: use scoped/foundation wording, or promote these families with evidence or explicit promoted equivalents.",
        ],
        "planning_surfaces_unresolved_for_v1_claim": [
            "Planning surfaces remain in the surface table.",
            f"Surfaces: {format_human_list(report.get('unresolved_planning_surfaces'))}.",
            "Action: convert each to promoted, excluded, or post-v1 before any complete SDK claim.",
        ],
        "top_level_planning_surfaces_unresolved_for_v1_claim": [
            "The top-level planning_surfaces list is not empty.",
            f"Surfaces: {format_human_list(report.get('top_level_planning_surfaces'))}.",
            "Action: keep v1 blocked until those entries have reviewed outcomes.",
        ],
        "completion_blocker_exclusion_contract_missing": [
            "A non-promoted completion blocker lacks a v1_decision_contract.exclusion_requires checklist.",
            f"Surfaces: {format_human_list(report.get('missing_completion_blocker_exclusion_contracts'))}.",
        ],
        "promoted_surface_public_contract_missing": [
            "Promoted surfaces are missing public_contract entries.",
            f"Surfaces: {format_human_list(report.get('promoted_without_public_contract'))}.",
        ],
        "promoted_surface_evidence_missing": [
            "Promoted surfaces lack acceptable ABI and SDK-consumer promotion evidence.",
            f"Surfaces: {format_human_list(report.get('promoted_surfaces_without_evidence'))}.",
            f"Completion blockers: {format_human_list(report.get('promoted_blockers_without_evidence'))}.",
        ],
        "promoted_surface_required_evidence_terms_missing": [
            "Promoted surfaces are missing required named evidence terms.",
            "Action: add the required terms to the manifest evidence or keep the surface non-promoted.",
        ],
        "promoted_surface_dependency_unresolved": [
            "A public ABI surface is promoted while required dependency surfaces are not promoted.",
            "Action: promote the dependencies first, or keep the dependent surface non-promoted.",
        ],
        "required_surface_dependency_declaration_missing": [
            "A permissions/admin or command surface row is missing a required depends_on declaration.",
            f"Surfaces: {format_human_list(sorted(report.get('surfaces_missing_required_dependency_declarations', {}).keys()))}.",
            "Action: keep identity/principal before permissions/admin, and keep command/chat response before commands/replies.",
        ],
        "v1_dependency_sequence_mismatch": [
            "The manifest v1 dependency sequence no longer matches identity -> permissions -> command/chat response -> commands/replies.",
            f"Mismatches: {format_human_list(report.get('v1_dependency_sequence_mismatches'))}.",
            "Action: restore v1_dependency_sequence and v1_sdk_completion_blockers to the canonical dependency order.",
        ],
        "non_promoted_surface_has_public_contract": [
            "A non-promoted surface still lists public_contract entries.",
            f"Surfaces: {format_human_list(report.get('non_promoted_with_public_contract'))}.",
            "Action: remove the public contract entries or promote the surface with evidence.",
        ],
        "non_promoted_surface_has_public_abi": [
            "A non-promoted surface is marked public_abi=true.",
            f"Surfaces: {format_human_list(report.get('non_promoted_with_public_abi'))}.",
            "Action: remove public_abi or promote the surface with dependencies and evidence.",
        ],
        "release_statement_required_for_v1_completion": [
            "The manifest is trying to allow a v1 completion claim without a reviewed release statement.",
            "Action: pass --release-statement with the reviewed v1 SDK compatibility statement.",
        ],
        "release_statement_missing_non_promoted_blocker_outcomes": [
            "The release statement is missing required outcome records for non-promoted blockers.",
            f"Surfaces: {format_human_list(report.get('release_statement_missing_blocker_outcomes'))}.",
            "Action: add one exact record per surface: '<surface-id>: excluded - ...' or '<surface-id>: post-v1 - ...'.",
        ],
        "release_statement_missing_exclusion_contract": [
            "The release statement outcome text does not satisfy the surface exclusion contract.",
            f"Surfaces: {format_human_list(report.get('release_statement_missing_exclusion_contracts'))}.",
            "Action: include the required exclusion wording from each surface v1_decision_contract.",
        ],
        "release_statement_missing_experimental_outcomes": [
            "The release statement is missing required outcome records for experimental copied-data seeds.",
            f"Surfaces: {format_human_list(report.get('release_statement_missing_experimental_outcomes'))}.",
            "Action: name the seed and state whether it is promoted, excluded, or post-v1.",
        ],
        "release_statement_duplicate_or_mixed_surface_records": [
            "The release statement has duplicate or mixed outcome records for a surface.",
            f"Surfaces: {format_human_list(report.get('release_statement_duplicate_or_mixed_records'))}.",
            "Action: keep exactly one promoted/excluded/post-v1 record per surface.",
        ],
        "release_statement_forbidden_broad_claims": [
            "The release statement contains broad SDK/support claims that conflict with blocked surfaces.",
            f"Claims: {format_human_list(report.get('release_statement_forbidden_broad_claims'), limit=4)}.",
        ],
        "release_statement_missing_sdk_compatibility_reference": [
            "The release statement does not reference docs/SDK_V1_COMPATIBILITY.md.",
        ],
        "release_statement_missing_public_sdk_surfaces_reference": [
            "The release statement does not reference docs/public_sdk_surfaces.json.",
        ],
        "blocked_public_contract_header_symbols_detected": [
            "The public header contains symbols that look like blocked public contract surface drift.",
            "Action: remove those symbols or update the reviewed public contract decisions before claiming v1.",
        ],
        "schema_mismatch": [
            "The manifest schema is not obelisk.public-sdk-surfaces.v1.",
        ],
        "sdk_version_not_v1": [
            "The manifest sdk_version is not v1.0.",
        ],
        "stable_release_contract_missing": [
            "The manifest is missing stable_release_contract.",
        ],
        "surface_id_missing": [
            f"Missing surfaces: {format_human_list(report.get('missing_surfaces'))}.",
        ],
        "canonical_surface_id_missing": [
            f"Missing canonical surfaces: {format_human_list(report.get('missing_canonical_surfaces'))}.",
        ],
        "canonical_v1_completion_blocker_missing": [
            f"Missing canonical blockers: {format_human_list(report.get('missing_canonical_completion_blockers'))}.",
        ],
        "duplicate_surface_id": [
            f"Duplicate surface IDs: {format_human_list(report.get('duplicate_surface_ids'))}.",
        ],
        "debug_only_surface_promoted": [
            "Debug-only surfaces cannot count as promoted public SDK surfaces.",
            f"Surfaces: {format_human_list(report.get('debug_only_promoted_surfaces'))}.",
        ],
        "promoted_surface_list_mismatch": [
            f"Promoted surface list mismatches: {format_human_list(report.get('promoted_list_mismatches'))}.",
        ],
        "experimental_surface_list_mismatch": [
            f"Experimental surface list mismatches: {format_human_list(report.get('experimental_list_mismatches'))}.",
        ],
        "planning_surface_list_mismatch": [
            f"Planning surface list mismatches: {format_human_list(report.get('planning_list_mismatches'))}.",
        ],
        "post_v1_or_excluded_surface_list_mismatch": [
            "post_v1_or_excluded_surfaces does not match surface statuses.",
            f"Surfaces: {format_human_list(report.get('post_v1_or_excluded_list_mismatches'))}.",
        ],
    }
    return guidance.get(blocker, ["Action: inspect the JSON report for this blocker with --json."])


def print_human_report(report: dict[str, Any]) -> None:
    if report["ready"]:
        print("Public SDK v1 completion gate passed.")
        return
    print("Public SDK v1 completion gate blocked.")
    print("The stable v1 SDK claim remains disabled; this is not a v1.0 complete SDK approval.")
    outcome_summary = report.get("v1_sdk_blocker_outcome_summary", {})
    if isinstance(outcome_summary, dict):
        print(
            "12-blocker outcome accounting: "
            f"{outcome_summary.get('manifest_outcome_missing_count', 0)} need manifest outcomes; "
            f"{outcome_summary.get('release_statement_outcome_missing_count', 0)} need release-statement outcomes; "
            f"{outcome_summary.get('dependency_chain_remaining_count', 0)} dependency-chain blockers remain."
        )
    print("Blockers:")
    for blocker in report["blockers"]:
        print(f"- {blocker}")
        for detail in blocker_guidance(report, blocker):
            print(f"  {detail}")
    print("Use --json for the full machine-readable report.")


def print_scoped_release_statement_report(report: dict[str, Any]) -> None:
    scoped = report["scoped_release_statement"]
    if scoped["ready"]:
        print("Scoped v1 SDK release statement check passed.")
        print("This does not allow a v1.0 stable or complete-SDK claim.")
        print(f"Remaining full-gate blockers: {format_human_list(scoped['allowed_remaining_blockers'])}.")
        return
    print("Scoped v1 SDK release statement check blocked.")
    print("Blocking statement-scope issues:")
    for blocker in scoped["blocking_report_blockers"]:
        print(f"- {blocker}")
        for detail in blocker_guidance(report, blocker):
            print(f"  {detail}")


def main() -> int:
    args = parse_args()
    report = build_report(
        args.manifest,
        args.release_statement,
        args.public_header,
        args.contract_decisions_dir,
    )
    if args.validate_release_statement_scope:
        report = add_scoped_release_statement_result(report)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_scoped_release_statement_report(report)
        return 0 if report["scoped_release_statement"]["ready"] else 1
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human_report(report)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
