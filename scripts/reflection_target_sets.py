#!/usr/bin/env python3
"""Shared named target sets for reflection snapshot tooling."""

from __future__ import annotations

import hashlib
import json
import re


SUPPORTED_TARGET_SET_SCHEMAS = frozenset(
    (
        "obelisk.ufunction-chain.snapshot.v1",
        "obelisk.scriptstruct-chain.snapshot.v1",
    )
)

TARGET_SET_REVISION_SCHEMA = "obelisk.reflection-target-set-revision.v1"
TARGET_SET_REVISION_SOURCE = "scripts/reflection_target_sets.py"
NON_AUTHORIZING_READY_SCOPE = "offline_or_fixture_readiness_alias_only_not_promotion_evidence"
NON_AUTHORIZING_READY_DOES_NOT_SATISFY = (
    "approved_runtime_evidence",
    "runtime_evidence",
    "runtime_readiness",
    "public_module_sdk",
    "public_sdk_readiness",
    "resource_handle",
    "object_identity",
    "lookup",
    "mutation",
    "return_override",
    "p0_dependency_chain",
    "complete_sdk",
    "stable_sdk",
    "v1_completion",
    "first_evidence",
    "no_users_passive_wait",
    "passive_snapshot",
    "beta_notice",
    "package_shape",
    "side_lane_artifacts",
)

PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS = (
    "ShooterGameMode.HandleNewPlayer",
    "ShooterGameMode.CheckJoinInProgress",
    "ShooterGameMode.OnLogout",
)
PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS = (
    "ShooterGameMode.HandleNewPlayer",
    "ShooterGameMode.OnLogout",
)
PLAYER_LIFECYCLE_REJECTED_START_SOURCE_TARGETS = (
    "ShooterGameMode.CheckJoinInProgress",
)
PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS = (
    "GameMode.K2_PostLogin",
)
PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS = (
    "ShooterGameMode.OnPostLogin__DelegateSignature",
    "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
)
PLAYER_LIFECYCLE_GUIDANCE_ONLY_NON_TRIPLET_TARGETS = (
    *PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS,
    *PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS,
)
PLAYER_LIFECYCLE_TARGET_SET = "players-lifecycle-anchor-candidates"
PLAYER_LIFECYCLE_EXACT_TARGETS = (
    *PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS,
    "ShooterGameMode.CheckJoinInProgress",
    "ShooterGameMode.HandleNewPlayer",
    "ShooterGameMode.OnLogout",
    *PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS,
)
PLAYER_LIFECYCLE_SOURCE_POLICY_SCOPE = "source_names_only_not_runtime_evidence"
PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS = (
    "approved_source_names_only_runtime_evidence_missing"
)
PLAYER_LIFECYCLE_GUIDANCE_ONLY_EVIDENCE_STATUS = "guidance_only_non_triplet_non_evidence"
PLAYER_LIFECYCLE_SOURCE_POLICY_NON_CLAIMS = (
    (
        "approved runtime triplet source names are role labels only and do not prove "
        "approved runtime evidence, runtime ordering, public SDK readiness, or promotion"
    ),
    (
        "GameMode.K2_PostLogin and delegate signatures are chronology/delegate guidance "
        "only, not runtime triplet sources, lifecycle anchors, public API, SDK readiness, "
        "or promotion evidence"
    ),
)

TARGET_SETS = {
    "chat-message-intake": (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerSendChatMessage",
    ),
    # Planning/guidance only for a future command/chat response route. This is not a
    # reply/send-chat ABI, command router, public response path, or release target set.
    "command-chat-response-route-planning": (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
    ),
    "buff-compact-intake": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.AllowPostProcessEffect",
        "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BPBuffPreventUploading",
        "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BP_OnBuffLifetimeUpdated",
    ),
    "buff-breadth-intake": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BuffOverrideInventoryAccessInput",
        "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BPCustomAllowAddBuff",
        "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BPPreventAddingOtherBuff",
    ),
    "dino-compact-intake": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalDinoCharacter.AddPassenger",
        "obelisk.ufunction-chain.snapshot.v1:PrimalDinoCharacter.AllowCarryCharacter",
    ),
    "mission-compact-intake": (
        "obelisk.ufunction-chain.snapshot.v1:MissionType.AddPlayerToMission",
        "obelisk.ufunction-chain.snapshot.v1:MissionType.BPAllowPlayerToLeaveMission",
        "obelisk.ufunction-chain.snapshot.v1:MissionType.BPOnPlayerRemovedFromMission",
        "obelisk.ufunction-chain.snapshot.v1:MissionType.GetPlayerUsableItems",
    ),
    "mission-copied-bool-policy-slice": (
        "obelisk.ufunction-chain.snapshot.v1:MissionType.AddPlayerToMission",
        "obelisk.ufunction-chain.snapshot.v1:MissionType.BPAllowPlayerToLeaveMission",
        "obelisk.ufunction-chain.snapshot.v1:MissionType.BPOnPlayerRemovedFromMission",
    ),
    "minimal-second-source-intake": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowRemoteAddToInventory",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
    ),
    "item-compact-intake": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowEquipItem",
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanRepair",
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CraftBlueprint",
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.UseItemOntoItem",
    ),
    # Internal/non-completion side lane only. These copied ReturnValue bool targets can
    # support planning, but must not count as P0, complete-SDK, public Items/Inventory
    # SDK, mutation, return-override, identity, or ResourceHandle evidence.
    "item-return-only-policy-slice": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowEquipItem",
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanRepair",
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.UseItemOntoItem",
    ),
    "inventory-action-compact-intake": (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestInventoryUseItem",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestInventoryUseItemWithActor",
    ),
    # Planning/guidance only for the inventory custom-filter array side lane. This is
    # candidate-only ArrayProperty metadata, not P0, Inventory SDK, public API,
    # runtime, mutation, return-override, ResourceHandle, or release-readiness scope.
    "inventory-custom-filter-array-boundary": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalInventoryComponent.InventoryCustomFilter",
    ),
    "structure-observer-intake": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.SetVariant",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.AllowToggleActivation",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.VerifyPinCode",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructureSeating.CanSeat",
    ),
    "structure-return-only-policy-slice": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
    ),
    "structure-nonpin-copied-scalar-policy-slice": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.SetVariant",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.AllowToggleActivation",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructureSeating.CanSeat",
    ),
    # Planning/guidance only for a future aggregate/census design. This deliberately
    # reuses the current copied Structure evidence lane as a bounded seed list; it is not
    # a release/public Structure SDK target set.
    "structure-aggregate-census-planning": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.SetVariant",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.AllowToggleActivation",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.VerifyPinCode",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructureSeating.CanSeat",
    ),
    # Candidate-only offline intake for structure build-placement policy. This is a
    # planning target set only: no public/runtime SDK, mutation, enforcement, or return
    # override readiness is implied by accepting sanitized layouts.
    "structure-build-policy-offline-intake": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuild",
        "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuildEx",
    ),
    "transfer-ufunction-intake": (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerDownloadTransferredPlayer",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerTransferredPlayerConfirmationResult",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerUploadCurrentCharacterAndItems",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerUploadDino",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters",
        "obelisk.ufunction-chain.snapshot.v1:ShooterGameState.AllowDownloadDino",
        "obelisk.ufunction-chain.snapshot.v1:PrimalDinoCharacter.IsAllowedToTransfer",
    ),
    "transfer-baccept-only-policy-slice": (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerTransferredPlayerConfirmationResult",
    ),
    "tribe-compact-intake": (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestTribeLog",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.AllowTribeGroupPermission",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.IsInTribe",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientReceiveMyTribeOnlineList",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientReceiveActiveMissionTags",
    ),
    # Planning/guidance only: closed player identity lifecycle seed list from
    # docs/research/2026-05-30-player-identity-lifecycle-plan.md. This is not
    # release/public evidence and must stay out of public SDK target sets.
    "players-identity-lifecycle-intake": (
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
    # Planning/guidance only: lifecycle candidate context from closed reflection planning.
    # The all-six target set is not evidence by itself. The current approved triplet source
    # policy is HandleNewPlayer/CheckJoinInProgress/OnLogout only; K2_PostLogin is
    # chronology-only, and delegate signatures are guidance-only. Tuple order is stable
    # serialization only; it does not claim runtime lifecycle ordering.
    "players-lifecycle-anchor-candidates": (
        "obelisk.ufunction-chain.snapshot.v1:GameMode.K2_PostLogin",
        "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.CheckJoinInProgress",
        "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
        "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
        "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnPostLogin__DelegateSignature",
        "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnStartNewPlayer__DelegateSignature",
    ),
    "transfer-scriptstruct": (
        "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ARKTributeDino",
        "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ArkTributePlayerData",
    ),
}


PLANNING_ONLY_TARGET_SETS = frozenset(
    (
        "command-chat-response-route-planning",
        "inventory-custom-filter-array-boundary",
        "item-return-only-policy-slice",
        "mission-copied-bool-policy-slice",
        "players-lifecycle-anchor-candidates",
        "players-identity-lifecycle-intake",
        "structure-aggregate-census-planning",
        "structure-build-policy-offline-intake",
    )
)


RELEASE_READINESS_TARGET_SETS = frozenset(
    (
        "chat-message-intake",
        "minimal-second-source-intake",
        "structure-observer-intake",
    )
)


INTERNAL_LAYOUT_ONLY_TARGET_SETS = frozenset(TARGET_SETS) - RELEASE_READINESS_TARGET_SETS


TARGET_SET_MODULE_LANES = {
    "buff-breadth-intake": "buff",
    "buff-compact-intake": "buff",
    "chat-message-intake": "chat",
    "command-chat-response-route-planning": "command_chat_response",
    "dino-compact-intake": "dino",
    "inventory-action-compact-intake": "inventory",
    "inventory-custom-filter-array-boundary": "inventory",
    "item-compact-intake": "items",
    "item-return-only-policy-slice": "items",
    "minimal-second-source-intake": "core_gameplay_policy",
    "mission-compact-intake": "mission",
    "mission-copied-bool-policy-slice": "mission",
    "players-identity-lifecycle-intake": "players_identity",
    "players-lifecycle-anchor-candidates": "players_lifecycle",
    "structure-aggregate-census-planning": "structures",
    "structure-build-policy-offline-intake": "structures",
    "structure-nonpin-copied-scalar-policy-slice": "structures",
    "structure-observer-intake": "structures",
    "structure-return-only-policy-slice": "structures",
    "transfer-baccept-only-policy-slice": "transfer",
    "transfer-scriptstruct": "transfer",
    "transfer-ufunction-intake": "transfer",
    "tribe-compact-intake": "tribe",
}


def player_lifecycle_anchor_source_policy() -> dict[str, object]:
    """Return the non-authorizing player lifecycle source-role policy."""
    target_set = "players-lifecycle-anchor-candidates"
    approved = set(PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS)
    static_anchors = set(PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS)
    rejected_start = set(PLAYER_LIFECYCLE_REJECTED_START_SOURCE_TARGETS)
    chronology_only = set(PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS)
    delegate_guidance = set(PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS)

    source_roles: list[dict[str, object]] = []
    for schema_target in TARGET_SETS[target_set]:
        _, _, short_name = schema_target.partition(":")
        is_approved = short_name in approved
        roles: list[str] = []
        if short_name in static_anchors:
            roles.append("static_lifecycle_anchor_source_name")
        if short_name in rejected_start:
            roles.append("rejected_start_triplet_source_name")
        if short_name in chronology_only:
            roles.append("chronology_guidance_only_non_anchor_source_name")
        if short_name in delegate_guidance:
            roles.append("delegate_guidance_only_non_triplet_source_name")
        source_roles.append(
            {
                "target": short_name,
                "schema_qualified_target": schema_target,
                "approved_runtime_triplet_source_name": is_approved,
                "guidance_only_non_triplet_source_name": short_name
                in PLAYER_LIFECYCLE_GUIDANCE_ONLY_NON_TRIPLET_TARGETS,
                "static_lifecycle_anchor_source_name": short_name in static_anchors,
                "rejected_start_triplet_source_name": short_name in rejected_start,
                "chronology_guidance_only_non_anchor_source_name": short_name in chronology_only,
                "delegate_guidance_only_non_triplet_source_name": short_name in delegate_guidance,
                "source_roles": roles,
                "runtime_evidence_status": (
                    PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS
                    if is_approved
                    else PLAYER_LIFECYCLE_GUIDANCE_ONLY_EVIDENCE_STATUS
                ),
                "runtime_ready": False,
                "public_sdk_ready": False,
                "promotion_ready": False,
            }
        )

    return {
        "policy_scope": PLAYER_LIFECYCLE_SOURCE_POLICY_SCOPE,
        "approved_runtime_triplet_source_names": list(PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS),
        "approved_triplet_sources": list(PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS),
        "runtime_triplet_evidence_status": PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS,
        "approved_runtime_evidence_present": False,
        "static_lifecycle_anchor_source_names": list(PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS),
        "static_lifecycle_anchor_sources": list(PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS),
        "observer_rejected_start_source_names": list(PLAYER_LIFECYCLE_REJECTED_START_SOURCE_TARGETS),
        "observer_rejected_start_sources": list(PLAYER_LIFECYCLE_REJECTED_START_SOURCE_TARGETS),
        "chronology_guidance_only_source_names": list(PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS),
        "chronology_only_non_anchor_sources": list(PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS),
        "delegate_guidance_only_source_names": list(PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS),
        "delegate_guidance_only_sources": list(PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS),
        "guidance_only_non_triplet_source_names": list(PLAYER_LIFECYCLE_GUIDANCE_ONLY_NON_TRIPLET_TARGETS),
        "all_six_planning_gap_evidence_status": "non_evidence",
        "runtime_ready": False,
        "public_sdk_ready": False,
        "promotion_ready": False,
        "does_not_satisfy": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "non_claims": list(PLAYER_LIFECYCLE_SOURCE_POLICY_NON_CLAIMS),
        "source_roles": source_roles,
    }


TARGET_SET_NAME_PROMOTION_ALIAS_TOKENS = frozenset(
    (
        "abi",
        "api",
        "accounted",
        "accounting",
        "claim",
        "claims",
        "complete",
        "completion",
        "contributes",
        "contribution",
        "count",
        "counting",
        "counts",
        "credit",
        "beta",
        "mutation",
        "p0",
        "package",
        "passive",
        "promote",
        "promoted",
        "promoting",
        "promotional",
        "promotion",
        "publish",
        "published",
        "public",
        "ready",
        "readiness",
        "release",
        "runtime",
        "sdk",
        "stable",
        "support",
        "supported",
        "status",
        "v1",
    )
)
TARGET_SET_NAME_PROMOTION_ALIAS_COMPOUNDS = {
    ("gobjects", "identity"): "gobjects_identity",
    ("gobjectsidentity",): "gobjects_identity",
    ("gobjects", "lookup"): "gobjects_lookup",
    ("gobjectslookup",): "gobjects_lookup",
    ("identity", "accepted"): "identity_accepted",
    ("identity", "evidence"): "identity_evidence",
    ("identity", "lookup"): "identity_lookup",
    ("identity", "ready"): "identity_ready",
    ("identity", "readiness"): "identity_readiness",
    ("object", "identity"): "object_identity",
    ("objectidentity",): "object_identity",
    ("object", "lookup"): "object_lookup",
    ("objectlookup",): "object_lookup",
    ("public", "identity"): "public_identity",
    ("publicidentity",): "public_identity",
    ("resource", "handle"): "resource_handle",
    ("resourcehandle",): "resourcehandle",
    ("return", "override"): "return_override",
    ("returnoverride",): "return_override",
    ("runtime", "identity"): "runtime_identity",
    ("runtimeidentity",): "runtime_identity",
    ("stable", "sdk"): "stable_sdk",
    ("stablesdk",): "stable_sdk",
}


def target_set_name_promotion_aliases(target_set: str) -> list[str]:
    """Return positive promotion/readiness aliases embedded in a target-set name."""
    token_list = [
        token
        for token in re.split(r"[^a-z0-9]+", target_set.casefold())
        if token
    ]
    tokens = set(token_list)
    aliases = set(tokens & TARGET_SET_NAME_PROMOTION_ALIAS_TOKENS)
    compact = "".join(token_list)
    for compound, alias in TARGET_SET_NAME_PROMOTION_ALIAS_COMPOUNDS.items():
        if len(compound) == 1:
            if compound[0] in tokens or compound[0] in compact:
                aliases.add(alias)
            continue
        if all(token in tokens for token in compound):
            aliases.add(alias)
    return sorted(aliases)


def target_set_module_lane(target_set: str) -> str:
    if target_set in TARGET_SET_MODULE_LANES:
        return TARGET_SET_MODULE_LANES[target_set]
    raise KeyError(target_set)


def target_set_readiness_classification(target_set: str) -> str:
    if target_set in RELEASE_READINESS_TARGET_SETS:
        return "release_readiness"
    if target_set in PLANNING_ONLY_TARGET_SETS:
        return "planning_only"
    if target_set in INTERNAL_LAYOUT_ONLY_TARGET_SETS:
        return "internal_layout_only"
    raise KeyError(target_set)


def target_set_revision_material(
    target_sets: list[str] | tuple[str, ...],
    *,
    schema_filter: str | None = None,
) -> dict[str, object]:
    """Return the canonical target-set catalog material used for stale-artifact checks."""
    names = sorted(set(target_sets))
    return {
        "schema": TARGET_SET_REVISION_SCHEMA,
        "source": TARGET_SET_REVISION_SOURCE,
        "target_schema_filter": schema_filter or "all",
        "target_sets": [
            {
                "name": name,
                "module_lane": target_set_module_lane(name),
                "readiness_classification": target_set_readiness_classification(name),
                "targets": [
                    target.partition(":")[2] if schema_filter is not None else target
                    for target in TARGET_SETS[name]
                    if schema_filter is None or target.partition(":")[0] == schema_filter
                ],
            }
            for name in names
        ],
    }


def target_set_revision_source_sha256(
    target_sets: list[str] | tuple[str, ...],
    *,
    schema_filter: str | None = None,
) -> str:
    material = target_set_revision_material(target_sets, schema_filter=schema_filter)
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def target_set_target_overlaps(target_sets: list[str]) -> list[dict[str, object]]:
    coverage: dict[str, list[str]] = {}
    for target_set in target_sets:
        for target in TARGET_SETS[target_set]:
            coverage.setdefault(target, []).append(target_set)
    return [
        {
            "target": target,
            "target_sets": sorted(names),
            "module_lanes": sorted({target_set_module_lane(name) for name in names}),
            "readiness_classifications": sorted({target_set_readiness_classification(name) for name in names}),
        }
        for target, names in sorted(coverage.items())
        if len(names) > 1
    ]


def _duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def target_set_catalog_hygiene_issues(
    *,
    target_sets: dict[str, tuple[str, ...]] | None = None,
    module_lanes: dict[str, str] | None = None,
    planning_only: frozenset[str] | None = None,
    release_readiness: frozenset[str] | None = None,
    supported_schemas: frozenset[str] | set[str] | None = None,
) -> list[dict[str, object]]:
    """Return fail-closed hygiene issues for named snapshot/signature target sets."""
    target_sets = TARGET_SETS if target_sets is None else target_sets
    module_lanes = TARGET_SET_MODULE_LANES if module_lanes is None else module_lanes
    planning_only = PLANNING_ONLY_TARGET_SETS if planning_only is None else planning_only
    release_readiness = RELEASE_READINESS_TARGET_SETS if release_readiness is None else release_readiness
    supported_schemas = SUPPORTED_TARGET_SET_SCHEMAS if supported_schemas is None else frozenset(supported_schemas)

    issues: list[dict[str, object]] = []
    declared_names = set(target_sets)
    planning_names = set(planning_only)
    release_names = set(release_readiness)
    module_lane_names = set(module_lanes)

    for name in sorted(declared_names - module_lane_names):
        issues.append({"target_set": name, "reason": "target_set_missing_module_lane"})
    for name in sorted(module_lane_names - declared_names):
        issues.append({"target_set": name, "reason": "module_lane_for_unknown_target_set"})
    for name in sorted(planning_names - declared_names):
        issues.append({"target_set": name, "reason": "planning_classification_for_unknown_target_set"})
    for name in sorted(release_names - declared_names):
        issues.append({"target_set": name, "reason": "release_classification_for_unknown_target_set"})
    for name in sorted(planning_names & release_names):
        issues.append({"target_set": name, "reason": "target_set_in_multiple_readiness_classes"})

    for target_set in sorted(target_sets):
        promotion_aliases = target_set_name_promotion_aliases(target_set)
        if promotion_aliases:
            issues.append(
                {
                    "target_set": target_set,
                    "reason": "target_set_name_promotion_alias",
                    "aliases": promotion_aliases,
                }
            )

        targets = target_sets[target_set]
        if not isinstance(targets, (tuple, list)):
            issues.append({"target_set": target_set, "reason": "target_set_targets_not_sequence"})
            continue
        if not targets:
            issues.append({"target_set": target_set, "reason": "target_set_empty"})
            continue

        string_targets: list[str] = []
        schemas: list[str] = []
        for index, target in enumerate(targets):
            if not isinstance(target, str) or not target:
                issues.append(
                    {
                        "target_set": target_set,
                        "target_index": index,
                        "reason": "target_set_entry_not_nonempty_string",
                    }
                )
                continue

            string_targets.append(target)
            schema, separator, short_key = target.partition(":")
            if not separator or not schema or not short_key:
                issues.append(
                    {
                        "target_set": target_set,
                        "target_index": index,
                        "target": target,
                        "reason": "target_set_entry_not_schema_qualified",
                    }
                )
                continue

            schemas.append(schema)
            if schema not in supported_schemas:
                issues.append(
                    {
                        "target_set": target_set,
                        "target_index": index,
                        "target": target,
                        "reason": "target_set_entry_unsupported_schema",
                        "schema": schema,
                    }
                )

            outer, dot, name = short_key.partition(".")
            if not dot or not outer or not name:
                issues.append(
                    {
                        "target_set": target_set,
                        "target_index": index,
                        "target": target,
                        "reason": "target_set_entry_missing_outer_dot_name",
                    }
                )

        duplicate_targets = _duplicate_values(string_targets)
        if duplicate_targets:
            issues.append(
                {
                    "target_set": target_set,
                    "reason": "duplicate_target_set_entries",
                    "targets": duplicate_targets,
                    "count": len(duplicate_targets),
                }
            )

        unique_schemas = sorted(set(schemas))
        if len(unique_schemas) > 1:
            issues.append(
                {
                    "target_set": target_set,
                    "reason": "target_set_mixed_snapshot_schemas",
                    "schemas": unique_schemas,
                }
            )

        if target_set == PLAYER_LIFECYCLE_TARGET_SET:
            expected = {
                f"obelisk.ufunction-chain.snapshot.v1:{target}"
                for target in PLAYER_LIFECYCLE_EXACT_TARGETS
            }
            observed = set(string_targets)
            if observed != expected:
                issues.append(
                    {
                        "target_set": target_set,
                        "reason": "player_lifecycle_target_set_exact_mismatch",
                        "missing_targets": sorted(expected - observed),
                        "unexpected_targets": sorted(observed - expected),
                    }
                )

    return issues


def schema_targets(target_set: str, schema: str) -> set[str]:
    return set(schema_target_list(target_set, schema))


def schema_target_list(target_set: str, schema: str) -> list[str]:
    targets = set()
    ordered_targets = []
    for target in TARGET_SETS[target_set]:
        target_schema, _, short_key = target.partition(":")
        if target_schema == schema:
            if short_key not in targets:
                targets.add(short_key)
                ordered_targets.append(short_key)
    return ordered_targets


def expand_schema_target_sets(target_sets: list[str], schema: str) -> set[str]:
    expanded: set[str] = set()
    for target_set in target_sets:
        targets = schema_targets(target_set, schema)
        if not targets:
            raise SystemExit(f"target set {target_set!r} has no targets for schema {schema}")
        expanded.update(targets)
    return expanded


SIDE_LANE_SOURCE_OVERCLAIM_KEYS = frozenset(
    (
        "source_overclaim_component_count",
        "source_overclaim_summary",
        "source_overclaim_total_flag_count",
        "source_overclaimed_count_flags",
        "source_overclaimed_progress_flags",
        "source_overclaimed_readiness_flags",
        "side_lane_source_overclaim_count",
        "side_lane_source_overclaim_total_flag_count",
        "side_lane_source_overclaims",
    )
)
SIDE_LANE_TARGET_ALIAS_KEYS = frozenset(
    (
        "declared_target_sets",
        "input_target_set",
        "input_target_sets",
        "source_target_set",
        "source_target_sets",
        "target_set",
        "target_set_alias",
        "target_set_aliases",
        "target_sets",
    )
)
SIDE_LANE_PASSIVE_SOURCE_KEY_RE = re.compile(
    r"(?:^|_)(?:no_users_passive_wait|passive_monitor|passive_player_presence|passive_snapshot|passive_snapshots)(?:_|$)"
)
SIDE_LANE_START_END_SOURCE_KEY_RE = re.compile(
    r"(?:^|_)(?:principal_start_end_runtime_evidence|runtime_lifecycle_start_end_evidence|lifecycle_start_end_evidence|start_end_runtime_evidence)(?:_|$)"
)
SIDE_LANE_START_END_SOURCE_VALUES = frozenset(
    (
        "principal_start_end_runtime_evidence",
        "principal_start_end_runtime_evidence_only",
        "runtime_lifecycle_start_end_evidence",
    )
)
SIDE_LANE_RUNTIME_EVIDENCE_MISSING_TRUE_KEYS = frozenset(
    (
        "approved_runtime_evidence_missing",
        "approved_player_principal_runtime_evidence_missing",
        "approved_runtime_principal_lifecycle_evidence_missing",
        "player_principal_lifecycle_runtime_evidence_missing",
        "player_principal_runtime_evidence_missing",
        "runtime_evidence_missing",
    )
)
SIDE_LANE_RUNTIME_EVIDENCE_CLEARANCE_KEYS = frozenset(
    (
        "approved_runtime_evidence_missing_cleared",
        "approved_runtime_evidence_missing_resolved",
        "clears_approved_runtime_evidence_missing",
        "resolves_approved_runtime_evidence_missing",
    )
)
SIDE_LANE_RUNTIME_EVIDENCE_BLOCKER_KEYS = frozenset(
    (
        "active_completion_blocker",
        "current_blocker",
        "current_route_blocker",
        "primary_blocker",
        "required_blocker",
        "route_current_blocker",
    )
)
SIDE_LANE_RUNTIME_EVIDENCE_BLOCKER_LIST_KEYS = frozenset(
    (
        "remaining_route_blockers",
        "route_remaining_blockers",
    )
)
SIDE_LANE_RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KEYS = frozenset(
    (
        "next_required_artifact",
        "required_artifact",
        "required_first_artifact",
        "required_next_artifact",
    )
)
SIDE_LANE_REQUIRED_RUNTIME_EVIDENCE_ARTIFACT = "approved_runtime_principal_lifecycle_evidence_bundle"
SIDE_LANE_POSITIVE_STATUS_VALUES = frozenset(
    (
        "accepted",
        "active",
        "approved",
        "available",
        "allowed",
        "complete",
        "completed",
        "cleared",
        "done",
        "enabled",
        "go",
        "green",
        "live",
        "ok",
        "operational",
        "pass",
        "passed",
        "promoted",
        "public",
        "public_ready",
        "published",
        "ready",
        "release_ready",
        "release_supported",
        "runtime",
        "runtime_ready",
        "sdk_ready",
        "satisfied",
        "ship",
        "shipped",
        "stable",
        "stable_ready",
        "supported",
        "true",
        "unblocked",
        "unlocked",
        "resolved",
        "valid",
        "validated",
        "verified",
        "v1_ready",
        "yes",
    )
)
SIDE_LANE_NEGATIVE_STATUS_VALUE_RE = re.compile(
    r"(?:candidate[_ -]?only|non[_ -]?counting|non[_ -]?evidence|planning[_ -]?only|"
    r"consume[_ -]?only|internal[_ -]?evidence[_ -]?only|offline[_ -]?only|"
    r"future[_ -]?capture[_ -]?targets[_ -]?only|blocked|excluded|false|not[_ -]?ready|"
    r"does[_ -]?not|must[_ -]?not|no[_ -]?(?:public|runtime|sdk|evidence))"
)
SIDE_LANE_BETA_PROOF_KEY_RE = re.compile(
    r"(?:^|_)(?:multi_surface_beta|beta|debug|candidate)_.*"
    r"(?:accepted|approved|capture_ready|claim|clears|counts|enabled|evidence|progress|"
    r"ready|readiness|runtime|sdk|unlock|validated)(?:_|$)"
)
SIDE_LANE_PACKAGE_ALIAS_KEY_RE = re.compile(
    r"(?:^|_)(?:package_shape|plugin_hub|support_tier)(?:_|$)"
)
SIDE_LANE_PUBLIC_READINESS_ALIAS_KEY_RE = re.compile(
    r"(?:^|_)(?:public(?:_.*)?(?:ready|readiness|enabled|accepted|approved|status)|"
    r"public_sdk|stable_sdk|v1(?:_.*)?(?:ready|completion|complete)|"
    r"runtime(?:_.*)?(?:ready|readiness|validated|validation|status)|"
    r"complete_sdk(?:_claim)?|p0_dependency_chain)(?:_|$)"
)
SIDE_LANE_STATUS_ALIAS_KEYS = frozenset(
    (
        "accepted",
        "approved",
        "complete",
        "enabled",
        "outcome",
        "passed",
        "promoted",
        "readiness",
        "ready",
        "result",
        "stable",
        "state",
        "status",
        "unblocked",
        "unlocked",
        "validated",
        "validation",
    )
)
SIDE_LANE_STATUS_CONTEXT_KEY_RE = re.compile(
    r"(?:approved_runtime|beta|capture|complete|evidence_bundle|package_shape|plugin_hub|"
    r"public|readiness|runtime|sdk|source|stable|support_tier|v1|p0)"
)
SIDE_LANE_SDK_P0_PROGRESS_KEY_RE = re.compile(
    r"(?:sdk|p0|complete|v1|public|runtime).*(?:progress|contribution|credit|credits|"
    r"counts|counting|counts_toward|counts_as|unlock|surface_count)"
)
SIDE_LANE_BOOL_PAYLOAD_VALUE_KEY_RE = re.compile(
    r"(?:^|_)(?:"
    r"bool_(?:payload|payload_byte|payload_bytes|value|values|byte_value|byte_values|"
    r"observed_value|observed_values|sample_value|sample_values)|"
    r"(?:copied|observed|sample|runtime|payload)_bool_(?:payload|payload_byte|"
    r"payload_bytes|value|values|byte|bytes|byte_value|byte_values)"
    r")(?:_|$)"
)


def normalized_side_lane_source_key(value: object) -> str:
    camel_spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", str(value))
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_spaced)
    return re.sub(r"[^a-z0-9]+", "_", camel_spaced.casefold()).strip("_")


def side_lane_positive_status_alias_value(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    if not isinstance(value, str):
        return False
    normalized = normalized_side_lane_source_key(value)
    if SIDE_LANE_NEGATIVE_STATUS_VALUE_RE.search(normalized):
        return False
    return normalized in SIDE_LANE_POSITIVE_STATUS_VALUES or normalized.endswith("_ready")


def side_lane_positive_progress_value(value: object) -> bool:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    if not isinstance(value, str):
        return value is True
    normalized = value.strip()
    return bool(re.fullmatch(r"[1-9]\d*(?:\s*/\s*[1-9]\d*)?", normalized))


def side_lane_contains_positive_alias_value(value: object) -> bool:
    if side_lane_positive_status_alias_value(value):
        return True
    if isinstance(value, dict):
        return any(side_lane_contains_positive_alias_value(child) for child in value.values())
    if isinstance(value, list):
        return any(side_lane_contains_positive_alias_value(child) for child in value)
    return False


def side_lane_bool_payload_leaf_is_canonical(value: object) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return value in (0, 1)
    if isinstance(value, float):
        return value in (0.0, 1.0)
    if not isinstance(value, str):
        return False
    normalized = value.strip().casefold()
    if normalized in {"false", "true", "0", "1"}:
        return True
    try:
        return int(normalized, 0) in (0, 1)
    except ValueError:
        return False


def side_lane_noncanonical_bool_payload_issues(
    value: object,
    *,
    path: str = "$",
) -> list[dict[str, object]]:
    """Return blockers for forged concrete bool payload bytes outside canonical 0/1."""
    issues: list[dict[str, object]] = []

    def visit(node: object, current_path: str, *, bool_payload_context: bool = False) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if isinstance(key, str) and key.startswith("_"):
                    continue
                key_text = str(key)
                child_path = f"{current_path}.{key_text}"
                normalized_key = normalized_side_lane_source_key(key_text)
                child_bool_payload_context = bool_payload_context or bool(
                    SIDE_LANE_BOOL_PAYLOAD_VALUE_KEY_RE.search(normalized_key)
                )
                visit(child, child_path, bool_payload_context=child_bool_payload_context)
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{current_path}[{index}]", bool_payload_context=bool_payload_context)
            return
        if bool_payload_context and not side_lane_bool_payload_leaf_is_canonical(node):
            issues.append(
                {
                    "reason": "noncanonical_bool_payload",
                    "path": current_path,
                    "value": node,
                }
            )

    visit(value, path)
    return issues


def side_lane_runtime_missing_value_preserved(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return normalized_side_lane_source_key(value) == "approved_runtime_evidence_missing"
    return False


def side_lane_runtime_blocker_value_preserved(value: object) -> bool:
    if isinstance(value, str):
        return normalized_side_lane_source_key(value) == "approved_runtime_evidence_missing"
    if isinstance(value, list):
        return any(side_lane_runtime_blocker_value_preserved(item) for item in value)
    return False


def side_lane_required_artifact_preserved(value: object) -> bool:
    return (
        isinstance(value, str)
        and normalized_side_lane_source_key(value) == SIDE_LANE_REQUIRED_RUNTIME_EVIDENCE_ARTIFACT
    )


def side_lane_status_alias_context(normalized_key: str, current_path: str) -> bool:
    normalized_path = normalized_side_lane_source_key(current_path)
    if "target_set_coverage" in normalized_path:
        return False
    if normalized_key.startswith(("target_set_", "target_sets_", "source_target_set_")) and normalized_key.endswith(
        (
            "_accepted",
            "_approved",
            "_outcome",
            "_passed",
            "_readiness",
            "_ready",
            "_result",
            "_status",
            "_unblocked",
            "_validated",
            "_validation",
        )
    ):
        return True
    if normalized_key.startswith("second_source_"):
        return False
    if normalized_key in SIDE_LANE_STATUS_ALIAS_KEYS and SIDE_LANE_STATUS_CONTEXT_KEY_RE.search(normalized_path):
        return True
    return (
        normalized_key.startswith("source_")
        and normalized_key.endswith(("_status", "_result", "_readiness", "_ready", "_validation", "_validated"))
    )


def side_lane_sdk_p0_progress_key(normalized_key: str) -> bool:
    tokens = {token for token in normalized_key.split("_") if token}
    scope_tokens = {"sdk", "p0", "complete", "completion", "v1", "public", "runtime"}
    progress_tokens = {
        "contribution",
        "count",
        "counting",
        "counts",
        "credit",
        "credits",
        "progress",
        "ratio",
        "unlock",
        "unlocks",
    }
    target_set_progress_tokens = progress_tokens - {"count", "counting"}
    if (
        normalized_key.startswith(("target_set_", "target_sets_", "source_target_set_"))
        and tokens & target_set_progress_tokens
    ):
        return True
    return bool(tokens & scope_tokens and tokens & progress_tokens) or bool(
        normalized_key.startswith(("counts_as_", "counts_toward_", "contributes_to_"))
        and tokens & scope_tokens
    )


def _target_alias_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        aliases: list[str] = []
        for key in ("name", "target_set", "targetSet", "target_set_alias", "targetSetAlias"):
            child = value.get(key)
            if isinstance(child, str):
                aliases.append(child)
        return aliases
    if isinstance(value, list):
        aliases: list[str] = []
        for item in value:
            aliases.extend(_target_alias_values(item))
        return aliases
    return []


def side_lane_fail_closed_source_artifact_issues(
    value: object,
    *,
    expected_target_sets: set[str] | frozenset[str] | tuple[str, ...] | list[str],
    path: str = "$",
) -> list[dict[str, object]]:
    """Return blockers for non-authorizing artifacts embedded in side-lane inputs."""
    expected = set(expected_target_sets)
    issues: list[dict[str, object]] = []

    def visit(node: object, current_path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if isinstance(key, str) and key.startswith("_"):
                    continue
                key_text = str(key)
                normalized_key = normalized_side_lane_source_key(key_text)
                child_path = f"{current_path}.{key_text}"

                if (
                    normalized_key in SIDE_LANE_SOURCE_OVERCLAIM_KEYS
                    or normalized_key.startswith("source_overclaim")
                    or normalized_key.startswith("side_lane_source_overclaim")
                ):
                    issues.append(
                        {
                            "reason": "source_overclaim_zero_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if SIDE_LANE_PASSIVE_SOURCE_KEY_RE.search(normalized_key):
                    issues.append(
                        {
                            "reason": "passive_snapshot_source_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if SIDE_LANE_START_END_SOURCE_KEY_RE.search(normalized_key):
                    issues.append(
                        {
                            "reason": "copied_start_end_player_evidence_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if (
                    normalized_key in SIDE_LANE_RUNTIME_EVIDENCE_MISSING_TRUE_KEYS
                    and not side_lane_runtime_missing_value_preserved(child)
                ):
                    issues.append(
                        {
                            "reason": "approved_runtime_evidence_missing_not_preserved",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if (
                    normalized_key in SIDE_LANE_RUNTIME_EVIDENCE_CLEARANCE_KEYS
                    and side_lane_positive_status_alias_value(child)
                ):
                    issues.append(
                        {
                            "reason": "approved_runtime_evidence_missing_clearance_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if (
                    normalized_key in SIDE_LANE_RUNTIME_EVIDENCE_BLOCKER_KEYS
                    and not side_lane_runtime_blocker_value_preserved(child)
                ):
                    issues.append(
                        {
                            "reason": "approved_runtime_evidence_missing_not_preserved",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if (
                    normalized_key in SIDE_LANE_RUNTIME_EVIDENCE_BLOCKER_LIST_KEYS
                    and not side_lane_runtime_blocker_value_preserved(child)
                ):
                    issues.append(
                        {
                            "reason": "approved_runtime_evidence_missing_not_preserved",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if (
                    normalized_key in SIDE_LANE_RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KEYS
                    and not side_lane_required_artifact_preserved(child)
                ):
                    issues.append(
                        {
                            "reason": "required_runtime_evidence_artifact_mismatch",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if SIDE_LANE_BETA_PROOF_KEY_RE.search(normalized_key) and side_lane_positive_status_alias_value(child):
                    issues.append(
                        {
                            "reason": "beta_capture_source_alias_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if SIDE_LANE_PACKAGE_ALIAS_KEY_RE.search(normalized_key) and side_lane_contains_positive_alias_value(child):
                    issues.append(
                        {
                            "reason": "package_shape_source_alias_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if (
                    SIDE_LANE_PUBLIC_READINESS_ALIAS_KEY_RE.search(normalized_key)
                    and side_lane_contains_positive_alias_value(child)
                ):
                    issues.append(
                        {
                            "reason": "public_readiness_source_alias_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if side_lane_status_alias_context(normalized_key, child_path) and side_lane_positive_status_alias_value(child):
                    issues.append(
                        {
                            "reason": "positive_status_alias_source_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if (
                    (
                        SIDE_LANE_SDK_P0_PROGRESS_KEY_RE.search(normalized_key)
                        or side_lane_sdk_p0_progress_key(normalized_key)
                    )
                    and side_lane_positive_progress_value(child)
                ):
                    issues.append(
                        {
                            "reason": "sdk_p0_progress_source_alias_not_allowed",
                            "path": child_path,
                            "value": child,
                        }
                    )
                if normalized_key in SIDE_LANE_TARGET_ALIAS_KEYS:
                    aliases = _target_alias_values(child)
                    unexpected = sorted(alias for alias in aliases if alias not in expected)
                    if unexpected:
                        issues.append(
                            {
                                "reason": "non_current_target_alias",
                                "path": child_path,
                                "expected_target_sets": sorted(expected),
                                "value": aliases,
                                "unexpected": unexpected,
                            }
                        )
                visit(child, child_path)
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{current_path}[{index}]")
            return
        if isinstance(node, str):
            normalized_value = normalized_side_lane_source_key(node)
            if normalized_value in SIDE_LANE_START_END_SOURCE_VALUES:
                issues.append(
                    {
                        "reason": "copied_start_end_player_evidence_not_allowed",
                        "path": current_path,
                        "value": node,
                    }
                )

    visit(value, path)
    return issues
