#!/usr/bin/env python3
"""Shared named target sets for reflection snapshot tooling."""

from __future__ import annotations


TARGET_SETS = {
    "chat-message-intake": (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerSendChatMessage",
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
    "item-return-only-policy-slice": (
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowEquipItem",
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanRepair",
        "obelisk.ufunction-chain.snapshot.v1:PrimalItem.UseItemOntoItem",
    ),
    "inventory-action-compact-intake": (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestInventoryUseItem",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestInventoryUseItemWithActor",
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
    "transfer-scriptstruct": (
        "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ARKTributeDino",
        "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ArkTributePlayerData",
    ),
}


PLANNING_ONLY_TARGET_SETS = frozenset(
    (
        "mission-copied-bool-policy-slice",
        "players-identity-lifecycle-intake",
        "structure-aggregate-census-planning",
    )
)


RELEASE_READINESS_TARGET_SETS = frozenset(
    (
        "chat-message-intake",
        "item-return-only-policy-slice",
        "minimal-second-source-intake",
        "structure-observer-intake",
    )
)


INTERNAL_LAYOUT_ONLY_TARGET_SETS = frozenset(TARGET_SETS) - RELEASE_READINESS_TARGET_SETS


TARGET_SET_MODULE_LANES = {
    "buff-breadth-intake": "buff",
    "buff-compact-intake": "buff",
    "chat-message-intake": "chat",
    "dino-compact-intake": "dino",
    "inventory-action-compact-intake": "inventory",
    "item-compact-intake": "items",
    "item-return-only-policy-slice": "items",
    "minimal-second-source-intake": "core_gameplay_policy",
    "mission-compact-intake": "mission",
    "mission-copied-bool-policy-slice": "mission",
    "players-identity-lifecycle-intake": "players_identity",
    "structure-aggregate-census-planning": "structures",
    "structure-nonpin-copied-scalar-policy-slice": "structures",
    "structure-observer-intake": "structures",
    "structure-return-only-policy-slice": "structures",
    "transfer-baccept-only-policy-slice": "transfer",
    "transfer-scriptstruct": "transfer",
    "transfer-ufunction-intake": "transfer",
    "tribe-compact-intake": "tribe",
}


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
