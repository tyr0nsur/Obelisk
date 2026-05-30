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
    "transfer-scriptstruct": (
        "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ARKTributeDino",
        "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ArkTributePlayerData",
    ),
}


def schema_targets(target_set: str, schema: str) -> set[str]:
    targets = set()
    for target in TARGET_SETS[target_set]:
        target_schema, _, short_key = target.partition(":")
        if target_schema == schema:
            targets.add(short_key)
    return targets


def expand_schema_target_sets(target_sets: list[str], schema: str) -> set[str]:
    expanded: set[str] = set()
    for target_set in target_sets:
        targets = schema_targets(target_set, schema)
        if not targets:
            raise SystemExit(f"target set {target_set!r} has no targets for schema {schema}")
        expanded.update(targets)
    return expanded
