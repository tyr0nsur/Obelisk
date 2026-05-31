#!/usr/bin/env python3
"""Build candidate-only redacted UFunction signatures from sanitized snapshots.

The output is intentionally not a public SDK contract. It preserves enough metadata for
offline reversing triage while redacting UE object/class/struct/enum identity and raw
parameter ownership details.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import protected_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
SUPPORTED_SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
OUTPUT_SCHEMA = "obelisk.redacted-ufunction-signatures.v1"
TARGET_SET_COVERAGE_SCHEMA = "obelisk.redacted-ufunction-target-set-coverage.v1"
ITEM_RETURN_ONLY_POLICY_SCHEMA = "obelisk.item-return-only-policy-slice.v1"
TRANSFER_BACCEPT_ONLY_POLICY_SCHEMA = "obelisk.transfer-baccept-only-policy-slice.v1"
MISSION_COPIED_BOOL_POLICY_SCHEMA = "obelisk.mission-copied-bool-policy-slice.v1"
STRUCTURE_RETURN_ONLY_POLICY_SCHEMA = "obelisk.structure-return-only-policy-slice.v1"
STRUCTURE_NONPIN_COPIED_SCALAR_POLICY_SCHEMA = "obelisk.structure-nonpin-copied-scalar-policy-slice.v1"
STRUCTURE_AGGREGATE_CENSUS_POLICY_SCHEMA = "obelisk.structure-aggregate-census-policy-slice.v1"
PLAYERS_IDENTITY_FIRST_EVIDENCE_SCHEMA = "obelisk.players-identity-first-evidence.v1"
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)

CPF_CONST_PARM = 0x2
CPF_PARM = 0x80
CPF_OUT_PARM = 0x100
CPF_ZERO_CONSTRUCTOR = 0x200
CPF_RETURN_PARM = 0x400
CPF_REFERENCE_PARM = 0x08000000
KNOWN_PROPERTY_FLAG_BITS = (
    CPF_CONST_PARM
    | CPF_PARM
    | CPF_OUT_PARM
    | CPF_ZERO_CONSTRUCTOR
    | CPF_RETURN_PARM
    | CPF_REFERENCE_PARM
)
CANDIDATE_UOBJECT_STATUS = "candidate-uobject"
ITEM_RETURN_ONLY_INPUT_TARGET_SET = "item-compact-intake"
ITEM_RETURN_ONLY_OUTPUT_TARGET_SET = "item-return-only-policy-slice"
TRANSFER_BACCEPT_ONLY_INPUT_TARGET_SET = "transfer-ufunction-intake"
TRANSFER_BACCEPT_ONLY_OUTPUT_TARGET_SET = "transfer-baccept-only-policy-slice"
MISSION_COPIED_BOOL_INPUT_TARGET_SET = "mission-compact-intake"
MISSION_COPIED_BOOL_OUTPUT_TARGET_SET = "mission-copied-bool-policy-slice"
STRUCTURE_RETURN_ONLY_INPUT_TARGET_SET = "structure-observer-intake"
STRUCTURE_RETURN_ONLY_OUTPUT_TARGET_SET = "structure-return-only-policy-slice"
STRUCTURE_NONPIN_COPIED_SCALAR_INPUT_TARGET_SET = "structure-nonpin-copied-scalar-policy-slice"
STRUCTURE_NONPIN_COPIED_SCALAR_OUTPUT_TARGET_SET = "structure-nonpin-copied-scalar-policy-slice"
STRUCTURE_AGGREGATE_CENSUS_INPUT_TARGET_SET = "structure-aggregate-census-planning"
STRUCTURE_AGGREGATE_CENSUS_OUTPUT_TARGET_SET = "structure-aggregate-census-policy-slice"
DINO_COMPACT_DESCRIPTOR_INPUT_TARGET_SET = "dino-compact-intake"
PLAYERS_IDENTITY_FIRST_EVIDENCE_INPUT_TARGET_SET = "players-identity-lifecycle-intake"
PLAYERS_IDENTITY_REQUIRED_TARGETS = (
    "ShooterPlayerController.ServerListPlayers",
    "ShooterPlayerController.ServerKickPlayer",
)

ITEM_RETURN_ONLY_EXPECTED_SHAPES: dict[str, dict[str, Any]] = {
    "PrimalItem.AllowEquipItem": {
        "num_parms": 2,
        "parms_size": 9,
        "return_value_offset": 0x8,
        "properties": (
            ("toInventory", "ObjectProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "PrimalItem.CanRepair": {
        "num_parms": 2,
        "parms_size": 2,
        "return_value_offset": 0x1,
        "properties": (
            ("bIgnoreInventoryRequirement", "BoolProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "PrimalItem.CraftBlueprint": {
        "num_parms": 1,
        "parms_size": 1,
        "return_value_offset": 0xFFFF,
        "properties": (("bConsumeResources", "BoolProperty"),),
    },
    "PrimalItem.UseItemOntoItem": {
        "num_parms": 3,
        "parms_size": 13,
        "return_value_offset": 0xC,
        "properties": (
            ("DestinationItem", "ObjectProperty"),
            ("AdditionalData", "IntProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
}

ITEM_RETURN_ONLY_COPIED_FIELDS = (
    "PrimalItem.AllowEquipItem.ReturnValue",
    "PrimalItem.CanRepair.ReturnValue",
    "PrimalItem.UseItemOntoItem.ReturnValue",
)

ITEM_RETURN_ONLY_DESCRIPTOR_BY_TARGET = {
    "PrimalItem.AllowEquipItem": "inventory_item.allow_equip_check",
    "PrimalItem.CanRepair": "inventory_item.can_repair_check",
    "PrimalItem.UseItemOntoItem": "inventory_item.use_onto_item_check",
}

ITEM_RETURN_ONLY_EXPECTED_DESCRIPTORS = (
    "inventory_item.allow_equip_check",
    "inventory_item.can_repair_check",
    "inventory_item.use_onto_item_check",
)

ITEM_RETURN_ONLY_EXCLUDED_REASONS = {
    "PrimalItem.AllowEquipItem.toInventory": "object_ref_excluded",
    "PrimalItem.CanRepair.bIgnoreInventoryRequirement": "non_return_bool_excluded",
    "PrimalItem.CraftBlueprint.bConsumeResources": "craftblueprint_excluded",
    "PrimalItem.UseItemOntoItem.DestinationItem": "object_ref_excluded",
    "PrimalItem.UseItemOntoItem.AdditionalData": "non_return_scalar_excluded",
}

DINO_COMPACT_DESCRIPTOR_EXPECTED_SHAPES: dict[str, dict[str, Any]] = {
    "PrimalDinoCharacter.AddPassenger": {
        "function_flags": 0x4020401,
        "num_parms": 6,
        "parms_size": 16,
        "return_value_offset": 0xF,
        "properties": (
            ("ACharacter", "ObjectProperty"),
            ("PassengerSeatIndex", "IntProperty"),
            ("bForcePassenger", "BoolProperty"),
            ("bAllowFlyersAndWaterDinos", "BoolProperty"),
            ("bSkipLineTrace", "BoolProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "PrimalDinoCharacter.AllowCarryCharacter": {
        "function_flags": 0x4020400,
        "num_parms": 2,
        "parms_size": 9,
        "return_value_offset": 0x8,
        "properties": (
            ("CanCarryPawn", "ObjectProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
}

DINO_COMPACT_COPIED_SCALAR_FIELDS = (
    "PrimalDinoCharacter.AddPassenger.PassengerSeatIndex",
    "PrimalDinoCharacter.AddPassenger.bForcePassenger",
    "PrimalDinoCharacter.AddPassenger.bAllowFlyersAndWaterDinos",
    "PrimalDinoCharacter.AddPassenger.bSkipLineTrace",
    "PrimalDinoCharacter.AddPassenger.ReturnValue",
    "PrimalDinoCharacter.AllowCarryCharacter.ReturnValue",
)

DINO_COMPACT_EXCLUDED_REASONS = {
    "PrimalDinoCharacter.AddPassenger.ACharacter": "passenger_object_ref_excluded",
    "PrimalDinoCharacter.AllowCarryCharacter.CanCarryPawn": "carry_pawn_object_ref_excluded",
}

DINO_COMPACT_DESCRIPTOR_BY_TARGET = {
    "PrimalDinoCharacter.AddPassenger": "dino_character.add_passenger",
    "PrimalDinoCharacter.AllowCarryCharacter": "dino_character.allow_carry_character",
}

DINO_COMPACT_EXPECTED_DESCRIPTORS = (
    "dino_character.add_passenger",
    "dino_character.allow_carry_character",
)

TRANSFER_BACCEPT_ONLY_EXPECTED_SHAPES: dict[str, dict[str, Any]] = {
    "ShooterPlayerController.ServerTransferredPlayerConfirmationResult": {
        "function_flags": 0x220CC0,
        "num_parms": 1,
        "parms_size": 1,
        "return_value_offset": 0xFFFF,
        "properties": (("bAccept", "BoolProperty"),),
    },
}

TRANSFER_BACCEPT_ONLY_COPIED_FIELDS = (
    "ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept",
)

TRANSFER_BACCEPT_ONLY_EXCLUDED_REASONS = {
    "PrimalDinoCharacter.IsAllowedToTransfer.WorldContextObject": "object_ref_excluded",
    "PrimalDinoCharacter.IsAllowedToTransfer.ReturnValue": "return_bool_excluded",
    "ShooterGameState.AllowDownloadDino.TheDinoClass": "class_ref_excluded",
    "ShooterGameState.AllowDownloadDino.ReturnValue": "return_bool_excluded",
    "ShooterPlayerController.ServerDownloadTransferredPlayer.SpawnPointID": "spawn_point_id_excluded",
    "ShooterPlayerController.ServerDownloadTransferredPlayer.spawnPointRegionIndex": "region_index_excluded",
    "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.IgnoreBedID": "bed_id_excluded",
    "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.PlayerDataID": "player_data_id_excluded",
    "ShooterPlayerController.ServerUploadCurrentCharacterAndItems.InventoryComp": "object_ref_excluded",
    "ShooterPlayerController.ServerUploadDino.DownloadedDino": "object_ref_excluded",
}

MISSION_COPIED_BOOL_EXPECTED_SHAPES: dict[str, dict[str, Any]] = {
    "MissionType.AddPlayerToMission": {
        "function_flags": 0x4020405,
        "num_parms": 3,
        "parms_size": 10,
        "return_value_offset": 0x9,
        "properties": (
            ("PlayerCharacter", "ObjectProperty"),
            ("bForceAdd", "BoolProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "MissionType.BPAllowPlayerToLeaveMission": {
        "function_flags": 0xC020C00,
        "num_parms": 2,
        "parms_size": 9,
        "return_value_offset": 0x8,
        "properties": (
            ("PlayerPawn", "ObjectProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "MissionType.BPOnPlayerRemovedFromMission": {
        "function_flags": 0xC020C00,
        "num_parms": 4,
        "parms_size": 18,
        "return_value_offset": 0xFFFF,
        "properties": (
            ("Player", "ObjectProperty"),
            ("Controller", "ObjectProperty"),
            ("bFromMissionCompleteEvent", "BoolProperty"),
            ("bLastPhaseSuccess", "BoolProperty"),
        ),
    },
    "MissionType.GetPlayerUsableItems": {
        "function_flags": 0x4420405,
        "num_parms": 2,
        "parms_size": 24,
        "return_value_offset": 0xFFFF,
        "properties": (
            ("Character", "ObjectProperty"),
            ("OutItemIDs", "ArrayProperty"),
        ),
    },
}

MISSION_COPIED_BOOL_FIELDS = (
    "MissionType.AddPlayerToMission.bForceAdd",
    "MissionType.AddPlayerToMission.ReturnValue",
    "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
    "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
    "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
)

MISSION_REDACTED_FIELD_REASONS = {
    "MissionType.AddPlayerToMission.PlayerCharacter": "object_ref_excluded",
    "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn": "object_ref_excluded",
    "MissionType.BPOnPlayerRemovedFromMission.Player": "object_ref_excluded",
    "MissionType.BPOnPlayerRemovedFromMission.Controller": "object_ref_excluded",
    "MissionType.GetPlayerUsableItems.Character": "object_ref_excluded",
    "MissionType.GetPlayerUsableItems.OutItemIDs": "array_payload_excluded",
}

STRUCTURE_RETURN_ONLY_EXPECTED_SHAPES: dict[str, dict[str, Any]] = {
    "PrimalStructure.AllowStructureAccess": {
        "function_flags": 0x4020400,
        "num_parms": 2,
        "parms_size": 9,
        "return_value_offset": 0x8,
        "properties": (
            ("ForPC", "ObjectProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "PrimalStructure.IsAllowedToDemolish": {
        "function_flags": 0x4020401,
        "num_parms": 2,
        "parms_size": 9,
        "return_value_offset": 0x8,
        "properties": (
            ("ForPC", "ObjectProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "PrimalStructure.SetVariant": {
        "function_flags": 0x4020401,
        "num_parms": 3,
        "parms_size": 6,
        "return_value_offset": 0x5,
        "properties": (
            ("VariantIndex", "IntProperty"),
            ("bForceSet", "BoolProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "PrimalStructureItemContainer.AllowToggleActivation": {
        "function_flags": 0x4020401,
        "num_parms": 2,
        "parms_size": 9,
        "return_value_offset": 0x8,
        "properties": (
            ("ForPC", "ObjectProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "PrimalStructureItemContainer.VerifyPinCode": {
        "function_flags": 0x54020401,
        "num_parms": 2,
        "parms_size": 5,
        "return_value_offset": 0x4,
        "properties": (
            ("pinCode", "IntProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
    "PrimalStructureSeating.CanSeat": {
        "function_flags": 0x4020400,
        "num_parms": 4,
        "parms_size": 18,
        "return_value_offset": 0x11,
        "properties": (
            ("ForPC", "ObjectProperty"),
            ("forCharacter", "ObjectProperty"),
            ("bForce", "BoolProperty"),
            ("ReturnValue", "BoolProperty"),
        ),
    },
}

STRUCTURE_RETURN_ONLY_COPIED_FIELDS = (
    "PrimalStructure.AllowStructureAccess.ReturnValue",
    "PrimalStructure.IsAllowedToDemolish.ReturnValue",
)

STRUCTURE_RETURN_ONLY_REDACTED_FIELD_REASONS = {
    "PrimalStructure.AllowStructureAccess.ForPC": "player_controller_ref_excluded",
    "PrimalStructure.IsAllowedToDemolish.ForPC": "player_controller_ref_excluded",
}

STRUCTURE_RETURN_ONLY_DEFERRED_REASONS = {
    "PrimalStructure.SetVariant": "mutation_surface_deferred",
    "PrimalStructureItemContainer.AllowToggleActivation": "activation_policy_deferred",
    "PrimalStructureItemContainer.VerifyPinCode": "pin_code_surface_deferred",
    "PrimalStructureSeating.CanSeat": "seating_policy_deferred",
}

STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS = (
    "PrimalStructure.SetVariant.VariantIndex",
    "PrimalStructure.SetVariant.bForceSet",
    "PrimalStructure.SetVariant.ReturnValue",
    "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue",
    "PrimalStructureSeating.CanSeat.bForce",
    "PrimalStructureSeating.CanSeat.ReturnValue",
)

STRUCTURE_NONPIN_REDACTED_FIELD_REASONS = {
    "PrimalStructureItemContainer.AllowToggleActivation.ForPC": "player_controller_ref_excluded",
    "PrimalStructureSeating.CanSeat.ForPC": "player_controller_ref_excluded",
    "PrimalStructureSeating.CanSeat.forCharacter": "character_ref_excluded",
}

STRUCTURE_AGGREGATE_EXCLUDED_PIN_FIELDS = (
    "PrimalStructureItemContainer.VerifyPinCode.pinCode",
    "PrimalStructureItemContainer.VerifyPinCode.ReturnValue",
)

SCALAR_TYPE_BY_CLASS = {
    "BoolProperty": "bool",
    "ByteProperty": "byte_or_enum",
    "DoubleProperty": "double",
    "EnumProperty": "enum",
    "FloatProperty": "float",
    "Int16Property": "int16",
    "Int64Property": "int64",
    "Int8Property": "int8",
    "IntProperty": "int32",
    "NameProperty": "fname",
    "UInt16Property": "uint16",
    "UInt32Property": "uint32",
    "UInt64Property": "uint64",
}

REDACTED_TYPE_BY_CLASS = {
    "ArrayProperty": "redacted_array",
    "ClassProperty": "redacted_class_ref",
    "DelegateProperty": "redacted_delegate",
    "InterfaceProperty": "redacted_interface_ref",
    "LazyObjectProperty": "redacted_uobject_ref",
    "MapProperty": "redacted_map",
    "MulticastDelegateProperty": "redacted_delegate",
    "ObjectProperty": "redacted_uobject_ref",
    "SetProperty": "redacted_set",
    "SoftClassProperty": "redacted_class_ref",
    "SoftObjectProperty": "redacted_uobject_ref",
    "StrProperty": "redacted_text",
    "StructProperty": "redacted_struct",
    "TextProperty": "redacted_text",
    "WeakObjectProperty": "redacted_uobject_ref",
}

IDENTITY_KEYS_TO_REDACT = {
    "class",
    "class_name",
    "enum",
    "enum_name",
    "inner",
    "inner_class",
    "inner_class_name",
    "object_class",
    "object_class_name",
    "property_class",
    "property_class_name",
    "struct",
    "struct_name",
}

BOOL_MASK_KEYS = (
    "byte_mask",
    "field_mask",
    "bool_byte_mask",
    "bool_field_mask",
    "bitmask",
    "mask",
)

SENSITIVE_SCALAR_NAMES = {
    "adminpassword",
    "allianceid",
    "enemytribeid",
    "eosid",
    "groupid",
    "grouprank",
    "invitecode",
    "invitetribeid",
    "lockcode",
    "newrank",
    "oldrank",
    "ownerplayerid",
    "ownertribeid",
    "passcode",
    "password",
    "platformid",
    "playerid",
    "pincode",
    "pin_code",
    "rankgroupid",
    "rankid",
    "requesterplayerid",
    "secret",
    "steamid",
    "targetingteam",
    "targetplayerid",
    "teamid",
    "token",
    "tribegrouppermission",
    "tribeid",
    "uniqueid",
    "uniquenetid",
}

IDENTITY_NAME_FRAGMENTS = (
    "account",
    "address",
    "admin",
    "character",
    "controller",
    "eos",
    "group",
    "identity",
    "ip",
    "netid",
    "owner",
    "pawn",
    "player",
    "principal",
    "profile",
    "rank",
    "sender",
    "session",
    "steam",
    "team",
    "tribe",
    "unique",
    "user",
)

FORBIDDEN_IDENTITY_COORDINATE_KEYS = (
    "array_inner_candidate",
    "class_name_index",
    "class_object_index",
    "name_index",
    "object_index",
    "outer_name_index",
    "outer_object_index",
    "property_class_name_index",
    "property_class_object_index",
    "struct_type_candidate",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert sanitized UFunction snapshots into redacted, candidate-only "
            "signature reports without reading cores or touching servers."
        )
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="Snapshot root containing manifest.json and snapshot files.",
    )
    parser.add_argument(
        "--target-set",
        action="append",
        default=[],
        help="Named UFunction target set from reflection_target_sets.py. Repeatable.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        action="append",
        default=[],
        help="Sanitized snapshot JSON to include directly. Repeatable.",
    )
    parser.add_argument(
        "--source-target-set",
        action="append",
        default=[],
        help=(
            "Named target set covered by direct --snapshot inputs. Repeatable. "
            "The emitted signatures must exactly match the declared target set union."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON. Text output is the default.",
    )
    parser.add_argument(
        "--item-return-only-policy-slice",
        action="store_true",
        help=(
            "Emit a focused evidence-only item policy slice that validates "
            "item-compact-intake and copies only AllowEquipItem/CanRepair/"
            "UseItemOntoItem ReturnValue bools."
        ),
    )
    parser.add_argument(
        "--transfer-baccept-only-policy-slice",
        action="store_true",
        help=(
            "Emit a focused evidence-only transfer policy slice that validates "
            "transfer-ufunction-intake and copies only ServerTransferredPlayerConfirmationResult.bAccept."
        ),
    )
    parser.add_argument(
        "--mission-copied-bool-policy-slice",
        action="store_true",
        help=(
            "Emit a focused evidence-only mission policy slice that validates "
            "mission-compact-intake and copies only approved mission BoolProperty fields."
        ),
    )
    parser.add_argument(
        "--structure-return-only-policy-slice",
        action="store_true",
        help=(
            "Emit a focused evidence-only structure policy slice that validates "
            "structure-observer-intake and copies only approved ReturnValue bools."
        ),
    )
    parser.add_argument(
        "--structure-nonpin-copied-scalar-policy-slice",
        action="store_true",
        help=(
            "Emit a focused evidence-only structure policy slice that validates "
            "non-PIN structure targets and copies only approved scalar fields."
        ),
    )
    parser.add_argument(
        "--structure-aggregate-census-policy-slice",
        action="store_true",
        help=(
            "Emit a consume-only structure aggregate/census policy slice with "
            "approved counters, histograms, copied fields, redactions, and PIN exclusions."
        ),
    )
    parser.add_argument(
        "--players-identity-first-evidence",
        action="store_true",
        help=(
            "Emit a candidate-only player identity first-evidence report for "
            "players-identity-lifecycle-intake with identity-like fields force-redacted."
        ),
    )
    return parser.parse_args()


def is_under_path(path: Path, root: Path) -> bool:
    return protected_paths.is_under_path(path, root)


def is_approved_offline_workspace_path(path: Path) -> bool:
    return protected_paths.is_approved_offline_workspace_path(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def reject_protected_input_path(label: str, path: Path) -> None:
    protected_paths.reject_protected_input_path(
        path,
        label,
        protected_root=PROTECTED_SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        message=f"{label} must not read from protected live-server path: {path}",
    )


def load_json_file(label: str, path: Path) -> dict[str, Any]:
    reject_protected_input_path(label, path)
    if not path.is_file():
        raise SystemExit(f"missing {label}: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must contain a JSON object: {path}")
    return payload


def file_sha256(path: Path) -> str:
    reject_protected_input_path("hash input", path)
    if not path.is_file():
        raise SystemExit(f"missing hash input: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(snapshot_root: Path) -> dict[str, Any]:
    reject_protected_input_path("snapshot root", snapshot_root)
    return load_json_file("snapshot manifest", snapshot_root / "manifest.json")


def manifest_index(manifest: dict[str, Any], snapshot_root: Path) -> dict[str, Path]:
    sha_prefix = manifest.get("sha_prefix")
    if not isinstance(sha_prefix, str) or not sha_prefix:
        raise SystemExit("snapshot manifest missing sha_prefix")

    entries = manifest.get("targets")
    if not isinstance(entries, list):
        raise SystemExit("snapshot manifest targets must be a list")

    indexed: dict[str, Path] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise SystemExit("snapshot manifest target entry must be an object")
        outer = entry.get("outer")
        name = entry.get("name")
        module = entry.get("module")
        file_name = entry.get("file")
        if not all(isinstance(value, str) and value for value in (outer, name, module, file_name)):
            raise SystemExit(f"invalid snapshot manifest entry: {entry!r}")

        target = f"{outer}.{name}"
        path = snapshot_root / sha_prefix / module / file_name
        reject_protected_input_path("snapshot", path)
        if target in indexed:
            raise SystemExit(f"duplicate snapshot manifest target: {target}")
        indexed[target] = path
    return indexed


def expand_ufunction_target_sets(target_sets: list[str]) -> dict[str, list[str]]:
    from reflection_target_sets import TARGET_SETS

    expanded: dict[str, list[str]] = {}
    for target_set in target_sets:
        if target_set in expanded:
            raise SystemExit(f"duplicate target set: {target_set}")
        entries = TARGET_SETS.get(target_set)
        if entries is None:
            raise SystemExit(f"unknown target set: {target_set}")
        targets: list[str] = []
        seen: set[str] = set()
        for entry in entries:
            schema, _, target = entry.partition(":")
            if schema != SUPPORTED_SNAPSHOT_SCHEMA:
                continue
            if target not in seen:
                targets.append(target)
                seen.add(target)
        if not targets:
            raise SystemExit(f"target set did not include UFunction snapshots: {target_set}")
        expanded[target_set] = targets
    return expanded


def expand_ufunction_targets(target_sets: list[str]) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for entries in expand_ufunction_target_sets(target_sets).values():
        for target in entries:
            if target not in seen:
                targets.append(target)
                seen.add(target)
    return targets


def parse_int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def property_flags(prop: dict[str, Any]) -> int | None:
    direct = parse_int_value(prop.get("property_flags"))
    if direct is not None:
        return direct
    direct = parse_int_value(prop.get("property_flags_hex"))
    if direct is not None:
        return direct
    low = parse_int_value(prop.get("property_flags_low"))
    high = parse_int_value(prop.get("property_flags_high"))
    if low is None and high is None:
        return None
    return ((high or 0) << 32) | (low or 0)


def has_flag(flags: int | None, flag: int) -> bool:
    return flags is not None and bool(flags & flag)


def classify_direction(prop: dict[str, Any], return_value_offset: Any) -> str:
    flags = property_flags(prop)
    offset = parse_int_value(prop.get("offset_internal"))
    return_offset = parse_int_value(return_value_offset)
    is_return = has_flag(flags, CPF_RETURN_PARM) or prop.get("name") == "ReturnValue"
    if not is_return and return_offset is not None and offset == return_offset:
        is_return = True
    if is_return:
        return "return"
    if has_flag(flags, CPF_OUT_PARM):
        return "out"
    if has_flag(flags, CPF_PARM):
        return "in"
    return "candidate_member_or_local"


def flag_labels(flags: int | None) -> list[str]:
    if flags is None:
        return ["flags_missing"]
    labels: list[str] = []
    if flags & CPF_CONST_PARM:
        labels.append("ConstParm")
    if flags & CPF_PARM:
        labels.append("Parm")
    if flags & CPF_OUT_PARM:
        labels.append("OutParm")
    if flags & CPF_ZERO_CONSTRUCTOR:
        labels.append("ZeroConstructor")
    if flags & CPF_RETURN_PARM:
        labels.append("ReturnParm")
    if flags & CPF_REFERENCE_PARM:
        labels.append("ReferenceParm")
    return labels


def append_membership_blocker(blockers: list[str], prop: dict[str, Any], key: str) -> None:
    status = prop.get(key)
    if status != CANDIDATE_UOBJECT_STATUS:
        blockers.append(f"{key}_not_candidate_uobject")


def append_nested_membership_blockers(blockers: list[str], prop: dict[str, Any], key: str) -> None:
    nested = prop.get(key)
    if nested is None:
        return
    if not isinstance(nested, dict):
        blockers.append(f"{key}_not_object")
        return
    if nested.get("membership_status") != CANDIDATE_UOBJECT_STATUS:
        blockers.append(f"{key}_membership_not_candidate_uobject")


def promotion_blockers_for_property(prop: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    flags = property_flags(prop)
    if flags is None:
        blockers.append("property_flags_missing")
    else:
        unknown = flags & ~KNOWN_PROPERTY_FLAG_BITS
        if unknown:
            blockers.append("property_flags_unknown_bits")

    append_membership_blocker(blockers, prop, "membership_status")
    append_membership_blocker(blockers, prop, "class_membership_status")
    append_membership_blocker(blockers, prop, "outer_membership_status")
    append_nested_membership_blockers(blockers, prop, "array_inner_candidate")
    append_nested_membership_blockers(blockers, prop, "struct_type_candidate")

    if prop.get("class_name") == "BoolProperty" and not bool_masks(prop) and prop.get("native_bool") is not True:
        blockers.append("bool_semantics_missing_mask_or_native_bool_marker")

    return sorted(set(blockers))


def is_valid_zero_param_signature(target_payload: dict[str, Any], property_count: int) -> bool:
    if property_count != 0:
        return False
    num_parms = parse_int_value(target_payload.get("num_parms"))
    parms_size = parse_int_value(target_payload.get("parms_size"))
    return_value_offset = parse_int_value(target_payload.get("return_value_offset"))
    property_chain = target_payload.get("property_chain")
    expected_count = None
    observed_count = None
    if isinstance(property_chain, dict):
        expected_count = parse_int_value(property_chain.get("expected_count"))
        observed_count = parse_int_value(property_chain.get("observed_count"))
    return (
        num_parms == 0
        and parms_size == 0
        and expected_count == 0
        and observed_count == 0
        and return_value_offset in (0xFFFF, -1)
    )


def promotion_blockers_for_signature(target_payload: dict[str, Any], property_count: int) -> list[str]:
    blockers = ["function_flags_not_bound_to_exact_target_gate"]
    if parse_int_value(target_payload.get("function_flags")) is None:
        blockers.append("function_flags_missing_or_unparseable")
    property_chain = target_payload.get("property_chain")
    expected_count = None
    observed_count = None
    if isinstance(property_chain, dict):
        expected_count = parse_int_value(property_chain.get("expected_count"))
        observed_count = parse_int_value(property_chain.get("observed_count"))

    if expected_count is None:
        blockers.append("property_chain_expected_count_missing")
    if observed_count is None:
        blockers.append("property_chain_observed_count_missing")
    if expected_count is not None and observed_count is not None and expected_count != observed_count:
        blockers.append("property_chain_count_mismatch")
    if observed_count is not None and observed_count != property_count:
        blockers.append("property_chain_observed_count_not_property_count")

    if property_count == 0 and not is_valid_zero_param_signature(target_payload, property_count):
        blockers.append("zero_param_shape_not_proven")
    return sorted(set(blockers))


def redacted_type(prop: dict[str, Any]) -> tuple[str, str]:
    class_name = prop.get("class_name")
    name = prop.get("name")
    if not isinstance(class_name, str) or not class_name:
        return "blocked_unknown", "missing property class"
    if isinstance(name, str) and name.lower() in SENSITIVE_SCALAR_NAMES:
        return "redacted_sensitive_scalar", "credential-like scalar redacted by name"
    if class_name in SCALAR_TYPE_BY_CLASS:
        if class_name in {"ByteProperty", "EnumProperty"}:
            return SCALAR_TYPE_BY_CLASS[class_name], "enum identity redacted"
        return SCALAR_TYPE_BY_CLASS[class_name], "copied scalar candidate"
    if class_name in REDACTED_TYPE_BY_CLASS:
        return REDACTED_TYPE_BY_CLASS[class_name], f"{class_name} identity/payload redacted"
    return "blocked_unknown", f"unsupported property class: {class_name}"


def bool_masks(prop: dict[str, Any]) -> dict[str, Any]:
    masks: dict[str, Any] = {}
    for key in BOOL_MASK_KEYS:
        value = parse_int_value(prop.get(key))
        if value is not None and 0 < value <= 0xFF:
            masks[key] = f"0x{value:02x}" if value < 0x10 else f"0x{value:x}"
    return masks


def redaction_notes(prop: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for key in sorted(IDENTITY_KEYS_TO_REDACT):
        if key in prop and prop.get(key) not in (None, "", [], {}):
            notes.append(f"{key}_redacted")
    return notes


def classify_property(prop: dict[str, Any], return_value_offset: Any) -> dict[str, Any]:
    name = prop.get("name")
    class_name = prop.get("class_name")
    if not isinstance(name, str) or not name:
        raise SystemExit(f"invalid property name: {prop!r}")
    if not isinstance(class_name, str) or not class_name:
        raise SystemExit(f"invalid property class for {name}: {prop!r}")

    flags = property_flags(prop)
    type_name, reason = redacted_type(prop)
    field: dict[str, Any] = {
        "name": name,
        "direction": classify_direction(prop, return_value_offset),
        "type": type_name,
        "source_property_class": class_name,
        "offset": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "array_dim": prop.get("array_dim"),
        "status": prop.get("status"),
        "property_flag_labels": flag_labels(flags),
        "redaction": reason,
    }
    if flags is not None:
        field["property_flags"] = f"0x{flags:x}"
    if class_name == "BoolProperty":
        masks = bool_masks(prop)
        if masks:
            field["bool_masks"] = masks
    blockers = promotion_blockers_for_property(prop)
    if blockers:
        field["promotion_blockers"] = blockers
    notes = redaction_notes(prop)
    if notes:
        field["redacted_identity_fields"] = notes
    return field


def blocked_property(prop: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "name": prop.get("name"),
        "source_property_class": prop.get("class_name"),
        "status": prop.get("status"),
        "reason": reason,
    }


def target_name(target_identity: dict[str, Any]) -> str:
    outer = target_identity.get("outer_name")
    name = target_identity.get("name")
    if not isinstance(outer, str) or not outer or not isinstance(name, str) or not name:
        raise SystemExit(f"invalid target identity: {target_identity!r}")
    return f"{outer}.{name}"


def require_snapshot_payload(payload: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    if payload.get("schema") != SUPPORTED_SNAPSHOT_SCHEMA:
        raise SystemExit(f"unsupported snapshot schema in {path}: {payload.get('schema')!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list) or not targets:
        raise SystemExit(f"snapshot must contain at least one target: {path}")
    if not all(isinstance(target, dict) for target in targets):
        raise SystemExit(f"snapshot targets must be objects: {path}")
    return targets


def build_target_signature(
    target_payload: dict[str, Any],
    path: Path,
    source_snapshot: dict[str, str] | None = None,
) -> dict[str, Any]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit(f"snapshot missing target identity or property chain: {path}")
    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"snapshot property_chain.properties must be a list: {path}")

    return_value_offset = target_payload.get("return_value_offset")
    params: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for prop in properties:
        if not isinstance(prop, dict):
            blocked.append({"name": None, "source_property_class": None, "status": None, "reason": "property entry is not an object"})
            continue
        if prop.get("status") != "candidate":
            blocked.append(blocked_property(prop, "property status is not candidate"))
            continue
        field = classify_property(prop, return_value_offset)
        if field["type"] == "blocked_unknown":
            blocked.append(blocked_property(prop, field["redaction"]))
            continue
        params.append(field)

    identity = target_name(target_identity)
    signature = {
        "target": identity,
        "outer_name": target_identity.get("outer_name"),
        "name": target_identity.get("name"),
        "function_flags": target_payload.get("function_flags"),
        "num_parms": target_payload.get("num_parms"),
        "parms_size": target_payload.get("parms_size"),
        "return_value_offset": return_value_offset,
        "signature_status": "candidate-only",
        "promotion_blockers": promotion_blockers_for_signature(target_payload, len(properties)),
        "params": params,
        "blocked_properties": blocked,
    }
    if source_snapshot is not None:
        signature["source_snapshot"] = source_snapshot["id"]
        signature["source_snapshot_sha256"] = source_snapshot["sha256"]
    return signature


def build_from_snapshot(path: Path, source_snapshot: dict[str, str]) -> list[dict[str, Any]]:
    payload = load_json_file("snapshot", path)
    return [
        build_target_signature(target, path, source_snapshot)
        for target in require_snapshot_payload(payload, path)
    ]


def scalar_summary_kind(type_name: str) -> str | None:
    if type_name == "bool":
        return "bool"
    if type_name in {"byte_or_enum", "enum"}:
        return "byte_or_enum_like"
    if type_name == "fname":
        return "name_like"
    if type_name in {"float", "double"}:
        return "float"
    if type_name in {"int8", "int16", "int32", "int64", "uint16", "uint32", "uint64"}:
        return "integer"
    return None


def redacted_summary_reason(type_name: str) -> str | None:
    if type_name == "redacted_sensitive_scalar":
        return "sensitive_scalar"
    if type_name in {"redacted_uobject_ref", "redacted_interface_ref"}:
        return "object_ref"
    if type_name == "redacted_class_ref":
        return "class_ref"
    if type_name in {"redacted_array", "redacted_map", "redacted_set"}:
        return "container"
    if type_name == "redacted_struct":
        return "struct"
    if type_name == "redacted_delegate":
        return "delegate"
    if type_name == "redacted_text":
        return "text"
    return None


def increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def safety_summary(signatures: list[dict[str, Any]], *, snapshot_count: int, target_sets: list[str], missing_targets: list[str]) -> dict[str, Any]:
    copied_scalar_by_kind: dict[str, int] = {}
    redacted_by_reason: dict[str, int] = {}
    blocked_by_reason: dict[str, int] = {}
    promotion_blockers_by_reason: dict[str, int] = {}
    direction_counts: dict[str, int] = {}
    param_count = 0
    copied_scalar_count = 0
    redacted_count = 0
    blocked_count = 0
    promotion_blocker_count = 0
    bool_masked_field_count = 0
    zero_param_signature_count = 0

    for signature in signatures:
        if not signature["params"] and not signature["blocked_properties"]:
            zero_param_signature_count += 1
        for blocker in signature.get("promotion_blockers", []):
            if isinstance(blocker, str):
                promotion_blocker_count += 1
                increment(promotion_blockers_by_reason, blocker)
        for param in signature["params"]:
            param_count += 1
            direction = param.get("direction")
            if isinstance(direction, str):
                increment(direction_counts, direction)
            type_name = param.get("type")
            if not isinstance(type_name, str):
                continue
            scalar_kind = scalar_summary_kind(type_name)
            if scalar_kind is not None:
                copied_scalar_count += 1
                increment(copied_scalar_by_kind, scalar_kind)
            redacted_reason = redacted_summary_reason(type_name)
            if redacted_reason is not None:
                redacted_count += 1
                increment(redacted_by_reason, redacted_reason)
            if "bool_masks" in param:
                bool_masked_field_count += 1
            for blocker in param.get("promotion_blockers", []):
                if isinstance(blocker, str):
                    promotion_blocker_count += 1
                    increment(promotion_blockers_by_reason, blocker)
        for blocked in signature["blocked_properties"]:
            blocked_count += 1
            reason = blocked.get("reason")
            increment(blocked_by_reason, reason if isinstance(reason, str) else "unknown")

    return {
        "artifact_status": "candidate_only",
        "promotion_ready": False,
        "intended_use": "offline_review_only",
        "evidence_scope": "redacted_ufunction_signature_metadata",
        "signature_count": len(signatures),
        "zero_param_signature_count": zero_param_signature_count,
        "snapshot_count": snapshot_count,
        "target_set_count": len(target_sets),
        "missing_target_count": len(missing_targets),
        "param_count_total": param_count,
        "copied_scalar_count_total": copied_scalar_count,
        "copied_scalar_by_kind": dict(sorted(copied_scalar_by_kind.items())),
        "redacted_count_total": redacted_count,
        "redacted_by_reason": dict(sorted(redacted_by_reason.items())),
        "blocked_count_total": blocked_count,
        "blocked_by_reason": dict(sorted(blocked_by_reason.items())),
        "promotion_blocker_count_total": promotion_blocker_count,
        "promotion_blockers_by_reason": dict(sorted(promotion_blockers_by_reason.items())),
        "direction_counts": dict(sorted(direction_counts.items())),
        "bool_masked_field_count": bool_masked_field_count,
        "unknown_or_blocked_present": blocked_count > 0,
        "direction_model": "return_out_in_order; ReferenceParm_label_only",
        "redaction_policy": "object_class_identity_sensitive_scalars_and_container_payloads_redacted",
        "not_promoted_surfaces": [
            "public_sdk",
            "object_identity",
            "class_identity",
            "lookup",
            "mutation",
            "return_override",
            "resource_handle",
            "cross_binary_portability",
        ],
    }


def snapshot_paths_from_target_sets(snapshot_root: Path, target_sets: list[str]) -> tuple[list[Path], list[str]]:
    if not target_sets:
        return [], []
    manifest = load_manifest(snapshot_root)
    indexed = manifest_index(manifest, snapshot_root)
    paths: list[Path] = []
    missing: list[str] = []
    for target in expand_ufunction_targets(target_sets):
        path = indexed.get(target)
        if path is None or not path.is_file():
            missing.append(target)
            continue
        paths.append(path)
    return paths, missing


def unique_ordered(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def target_set_coverage(
    *,
    manifest_target_sets: list[str],
    source_target_sets: list[str],
    emitted_targets: list[str],
) -> dict[str, Any]:
    if set(manifest_target_sets).intersection(source_target_sets):
        overlap = sorted(set(manifest_target_sets).intersection(source_target_sets))
        raise SystemExit(f"target set declared for both manifest and direct snapshots: {', '.join(overlap)}")

    declared: list[tuple[str, str]] = [
        *[(target_set, "manifest") for target_set in manifest_target_sets],
        *[(target_set, "snapshot") for target_set in source_target_sets],
    ]
    expanded = expand_ufunction_target_sets([target_set for target_set, _ in declared]) if declared else {}
    emitted_set = set(emitted_targets)
    expected_targets = unique_ordered(
        [
            target
            for target_set, _ in declared
            for target in expanded[target_set]
        ]
    )
    expected_set = set(expected_targets)
    missing_targets = [target for target in expected_targets if target not in emitted_set]
    unexpected_targets = [target for target in emitted_targets if target not in expected_set] if declared else []
    entries: list[dict[str, Any]] = []

    for target_set, source in declared:
        targets = expanded[target_set]
        covered = [target for target in targets if target in emitted_set]
        missing = [target for target in targets if target not in emitted_set]
        entries.append(
            {
                "name": target_set,
                "source": source,
                "expected_targets": targets,
                "covered_targets": covered,
                "missing_targets": missing,
                "complete": not missing,
            }
        )

    if declared and (missing_targets or unexpected_targets):
        detail = []
        if missing_targets:
            detail.append("missing=" + ",".join(missing_targets))
        if unexpected_targets:
            detail.append("unexpected=" + ",".join(unexpected_targets))
        raise SystemExit("target-set coverage mismatch: " + " ".join(detail))

    return {
        "schema": TARGET_SET_COVERAGE_SCHEMA,
        "status": "complete" if declared else "not_declared",
        "complete": not missing_targets and not unexpected_targets,
        "declared_target_sets": entries,
        "expected_targets": expected_targets,
        "emitted_targets": emitted_targets,
        "missing_targets": missing_targets,
        "unexpected_targets": unexpected_targets,
    }


def build_report(
    *,
    snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT,
    target_sets: list[str] | None = None,
    source_target_sets: list[str] | None = None,
    snapshots: list[Path] | None = None,
) -> dict[str, Any]:
    target_sets = target_sets or []
    source_target_sets = source_target_sets or []
    snapshots = snapshots or []
    if source_target_sets and not snapshots:
        raise SystemExit("--source-target-set requires at least one --snapshot")
    manifest_paths, missing_targets = snapshot_paths_from_target_sets(snapshot_root, target_sets)
    if missing_targets:
        raise SystemExit("target-set manifest missing targets: " + ",".join(missing_targets))
    all_paths = [*manifest_paths, *snapshots]
    if not all_paths:
        raise SystemExit("provide at least one --target-set or --snapshot")

    signatures: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    input_snapshots = [
        {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        for index, path in enumerate(all_paths, start=1)
    ]
    for path, source_snapshot in zip(all_paths, input_snapshots, strict=True):
        for signature in build_from_snapshot(path, source_snapshot):
            target = signature["target"]
            if target in seen_targets:
                raise SystemExit(f"duplicate target in signature inputs: {target}")
            signatures.append(signature)
            seen_targets.add(target)
    emitted_targets = [signature["target"] for signature in signatures]
    coverage = target_set_coverage(
        manifest_target_sets=target_sets,
        source_target_sets=source_target_sets,
        emitted_targets=emitted_targets,
    )
    all_target_sets = [*target_sets, *source_target_sets]
    descriptor_preflight = None
    if DINO_COMPACT_DESCRIPTOR_INPUT_TARGET_SET in all_target_sets:
        descriptor_preflight = build_dino_compact_descriptor_preflight_from_inputs(all_paths, input_snapshots)

    report = {
        "schema": OUTPUT_SCHEMA,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "snapshot_root": "redacted",
        "target_sets": target_sets,
        "source_target_sets": source_target_sets,
        "target_set_coverage": coverage,
        "snapshot_count": len(all_paths),
        "signature_count": len(signatures),
        "missing_targets": missing_targets,
        "safety_summary": safety_summary(
            signatures,
            snapshot_count=len(all_paths),
            target_sets=all_target_sets,
            missing_targets=missing_targets,
        ),
        "signatures": signatures,
        "non_claims": [
            "candidate-only redacted UFunction signature report",
            "does not promote public SDK callbacks or public metadata helpers",
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
        ],
    }
    if descriptor_preflight is not None:
        report["descriptor_preflight"] = descriptor_preflight
    return report


def format_hex(value: int) -> str:
    return f"0x{value:x}"


def require_int_field(payload: dict[str, Any], key: str, target: str) -> int:
    value = parse_int_value(payload.get(key))
    if value is None:
        raise SystemExit(f"{target} missing or invalid {key}")
    return value


def require_candidate_membership(prop: dict[str, Any], target: str, field: str) -> None:
    for key in ("membership_status", "class_membership_status", "outer_membership_status"):
        if prop.get(key) != CANDIDATE_UOBJECT_STATUS:
            raise SystemExit(f"{target}.{field} {key} is not {CANDIDATE_UOBJECT_STATUS}")


def require_bool_return_field(target: str, prop: dict[str, Any], return_value_offset: int) -> dict[str, Any]:
    offset = require_int_field(prop, "offset_internal", f"{target}.ReturnValue")
    element_size = require_int_field(prop, "element_size", f"{target}.ReturnValue")
    flags = property_flags(prop)
    if offset != return_value_offset:
        raise SystemExit(f"{target}.ReturnValue offset does not match ReturnValueOffset")
    if element_size != 1:
        raise SystemExit(f"{target}.ReturnValue is not a one-byte bool")
    if not has_flag(flags, CPF_RETURN_PARM):
        raise SystemExit(f"{target}.ReturnValue is not marked ReturnParm")
    field = classify_property(prop, return_value_offset)
    if field["direction"] != "return" or field["type"] != "bool":
        raise SystemExit(f"{target}.ReturnValue is not a copied bool return")
    if "bool_masks" not in field:
        raise SystemExit(f"{target}.ReturnValue lacks bool mask evidence")
    return field


def require_bool_input_field(target: str, prop: dict[str, Any], expected_name: str) -> dict[str, Any]:
    offset = require_int_field(prop, "offset_internal", f"{target}.{expected_name}")
    element_size = require_int_field(prop, "element_size", f"{target}.{expected_name}")
    array_dim = require_int_field(prop, "array_dim", f"{target}.{expected_name}")
    flags = property_flags(prop)
    if offset != 0:
        raise SystemExit(f"{target}.{expected_name} offset drifted")
    if element_size != 1:
        raise SystemExit(f"{target}.{expected_name} is not a one-byte bool")
    if array_dim != 1:
        raise SystemExit(f"{target}.{expected_name} array_dim drifted")
    if flags != 0x1040000280:
        raise SystemExit(f"{target}.{expected_name} property_flags drifted")
    if prop.get("native_bool") is not False:
        raise SystemExit(f"{target}.{expected_name} native_bool marker drifted")
    field = classify_property(prop, 0xFFFF)
    if field["direction"] != "in" or field["type"] != "bool":
        raise SystemExit(f"{target}.{expected_name} is not a copied input bool")
    masks = field.get("bool_masks")
    if not isinstance(masks, dict) or masks.get("byte_mask") != "0x01" or masks.get("field_mask") != "0xff":
        raise SystemExit(f"{target}.{expected_name} bool masks drifted")
    return field


def require_bool_tail(prop: dict[str, Any], field_key: str) -> tuple[int, int]:
    field_size = parse_int_value(prop.get("bool_field_size"))
    byte_offset = parse_int_value(prop.get("bool_byte_offset"))
    semantics = prop.get("bool_property_semantics")
    if field_size is None or byte_offset is None:
        raise SystemExit(f"{field_key} bool tail evidence missing")
    if isinstance(semantics, dict):
        semantic_field_size = parse_int_value(semantics.get("bool_field_size"))
        semantic_byte_offset = parse_int_value(semantics.get("bool_byte_offset"))
        if semantic_field_size is None or semantic_byte_offset is None:
            raise SystemExit(f"{field_key} bool_property_semantics tail evidence missing")
        if field_size != semantic_field_size or byte_offset != semantic_byte_offset:
            raise SystemExit(f"{field_key} bool tail evidence is inconsistent")
    return field_size, byte_offset


def require_item_return_only_shape(target_payload: dict[str, Any], source_snapshot: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit("item policy snapshot missing target identity or property chain")
    target = target_name(target_identity)
    expected = ITEM_RETURN_ONLY_EXPECTED_SHAPES.get(target)
    if expected is None:
        raise SystemExit(f"unexpected item policy target: {target}")
    if target_payload.get("status") != "candidate":
        raise SystemExit(f"{target} is not a candidate UFunction snapshot")
    if target_payload.get("inspection_mode") != "ufunction":
        raise SystemExit(f"{target} is not a UFunction inspection snapshot")

    if require_int_field(target_payload, "num_parms", target) != expected["num_parms"]:
        raise SystemExit(f"{target} NumParms drifted")
    if require_int_field(target_payload, "parms_size", target) != expected["parms_size"]:
        raise SystemExit(f"{target} ParmsSize drifted")
    return_value_offset = require_int_field(target_payload, "return_value_offset", target)
    if return_value_offset != expected["return_value_offset"]:
        raise SystemExit(f"{target} ReturnValueOffset drifted")

    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{target} property_chain.properties is not a list")
    if parse_int_value(property_chain.get("expected_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} expected property count drifted")
    if parse_int_value(property_chain.get("observed_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} observed property count drifted")
    if len(properties) != len(expected["properties"]):
        raise SystemExit(f"{target} property list length drifted")

    copied: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for prop, (expected_name, expected_class) in zip(properties, expected["properties"], strict=True):
        if not isinstance(prop, dict):
            raise SystemExit(f"{target} property entry is not an object")
        name = prop.get("name")
        class_name = prop.get("class_name")
        if name != expected_name or class_name != expected_class:
            raise SystemExit(f"{target} property shape drifted: expected {expected_name}:{expected_class}")
        if prop.get("status") != "candidate":
            raise SystemExit(f"{target}.{expected_name} is not a candidate property")
        require_candidate_membership(prop, target, expected_name)

        field_key = f"{target}.{expected_name}"
        if field_key in ITEM_RETURN_ONLY_COPIED_FIELDS:
            field = require_bool_return_field(target, prop, return_value_offset)
            copied.append(
                {
                    "target": target,
                    "field": expected_name,
                    "copied_field": field_key,
                    "direction": "return",
                    "type": "bool",
                    "offset": format_hex(require_int_field(prop, "offset_internal", field_key)),
                    "element_size": require_int_field(prop, "element_size", field_key),
                    "bool_masks": field["bool_masks"],
                    "source_snapshot": source_snapshot["id"],
                    "source_snapshot_sha256": source_snapshot["sha256"],
                    "evidence_status": "copied-return-bool-only",
                }
            )
        else:
            reason = ITEM_RETURN_ONLY_EXCLUDED_REASONS.get(field_key)
            if reason is None:
                raise SystemExit(f"{field_key} has no explicit exclusion reason")
            excluded.append(
                {
                    "target": target,
                    "field": expected_name,
                    "excluded_field": field_key,
                    "reason": reason,
                    "source_snapshot": source_snapshot["id"],
                }
            )
    return copied, excluded


def build_item_return_only_descriptor_preflight(copied: list[dict[str, Any]]) -> dict[str, Any]:
    descriptors: list[dict[str, Any]] = []
    for entry in copied:
        target = entry.get("target")
        descriptor = ITEM_RETURN_ONLY_DESCRIPTOR_BY_TARGET.get(target)
        if descriptor is None:
            raise SystemExit(f"item descriptor preflight has no descriptor for target: {target}")
        if entry.get("direction") != "return" or entry.get("type") != "bool":
            raise SystemExit(f"{target} descriptor preflight is not return-bool-only")
        descriptors.append(
            {
                "descriptor": descriptor,
                "target": target,
                "copied_field": entry["copied_field"],
                "field": entry["field"],
                "direction": "return",
                "type": "bool",
                "resource_kind": "INVENTORY_ITEM",
                "resource_backing": "inventory_backed",
                "payload_policy": "copied_return_value_only",
                "assigned_event_kind": None,
                "assigned_event_kind_mask": None,
                "promotion_ready": False,
                "public_promotion": False,
                "source_snapshot": entry["source_snapshot"],
                "source_snapshot_sha256": entry["source_snapshot_sha256"],
                "evidence_status": "descriptor-preflight-only",
            }
        )

    emitted = [entry["descriptor"] for entry in descriptors]
    missing = [descriptor for descriptor in ITEM_RETURN_ONLY_EXPECTED_DESCRIPTORS if descriptor not in emitted]
    unexpected = [descriptor for descriptor in emitted if descriptor not in ITEM_RETURN_ONLY_EXPECTED_DESCRIPTORS]
    if missing or unexpected:
        raise SystemExit(
            "item descriptor preflight failed closed: "
            + ",".join(
                [
                    *[f"missing_descriptor:{descriptor}" for descriptor in missing],
                    *[f"unexpected_descriptor:{descriptor}" for descriptor in unexpected],
                ]
            )
        )

    return {
        "status": "internal-evidence-only",
        "scope": "item-return-only-policy-slice",
        "descriptor_count": len(descriptors),
        "resource_kind": "INVENTORY_ITEM",
        "resource_backing": "inventory_backed",
        "payload_policy": "copied_return_value_only",
        "return_value_only": True,
        "assigned_event_kind": None,
        "assigned_event_kind_mask": None,
        "promotion_ready": False,
        "public_promotion": False,
        "public_surface": False,
        "descriptors": descriptors,
        "explicitly_not_assigned": [
            "event_kind",
            "event_kind_mask",
            "public_metadata_json",
            "runtime_dispatcher_tables",
            "plugin_callbacks",
        ],
    }


def require_dino_compact_descriptor_shape(
    target_payload: dict[str, Any],
    source_snapshot: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit("dino compact descriptor snapshot missing target identity or property chain")
    target = target_name(target_identity)
    expected = DINO_COMPACT_DESCRIPTOR_EXPECTED_SHAPES.get(target)
    if expected is None:
        raise SystemExit(f"unexpected dino compact descriptor target: {target}")
    if target_payload.get("status") != "candidate":
        raise SystemExit(f"{target} is not a candidate UFunction snapshot")
    if target_payload.get("inspection_mode") != "ufunction":
        raise SystemExit(f"{target} is not a UFunction inspection snapshot")

    if require_int_field(target_payload, "function_flags", target) != expected["function_flags"]:
        raise SystemExit(f"{target} FunctionFlags drifted")
    if require_int_field(target_payload, "num_parms", target) != expected["num_parms"]:
        raise SystemExit(f"{target} NumParms drifted")
    if require_int_field(target_payload, "parms_size", target) != expected["parms_size"]:
        raise SystemExit(f"{target} ParmsSize drifted")
    return_value_offset = require_int_field(target_payload, "return_value_offset", target)
    if return_value_offset != expected["return_value_offset"]:
        raise SystemExit(f"{target} ReturnValueOffset drifted")

    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{target} property_chain.properties is not a list")
    if parse_int_value(property_chain.get("expected_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} expected property count drifted")
    if parse_int_value(property_chain.get("observed_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} observed property count drifted")
    if len(properties) != len(expected["properties"]):
        raise SystemExit(f"{target} property list length drifted")

    copied: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for prop, (expected_name, expected_class) in zip(properties, expected["properties"], strict=True):
        if not isinstance(prop, dict):
            raise SystemExit(f"{target} property entry is not an object")
        name = prop.get("name")
        class_name = prop.get("class_name")
        if name != expected_name or class_name != expected_class:
            raise SystemExit(f"{target} property shape drifted: expected {expected_name}:{expected_class}")
        if prop.get("status") != "candidate":
            raise SystemExit(f"{target}.{expected_name} is not a candidate property")
        require_candidate_membership(prop, target, expected_name)

        field_key = f"{target}.{expected_name}"
        common = {
            "target": target,
            "field": expected_name,
            "offset": format_hex(require_int_field(prop, "offset_internal", field_key)),
            "offset_internal": require_int_field(prop, "offset_internal", field_key),
            "element_size": require_int_field(prop, "element_size", field_key),
            "array_dim": require_int_field(prop, "array_dim", field_key),
            "property_flags": format_hex(property_flags(prop) or 0),
            "property_class": expected_class,
            "function_flags": format_hex(require_int_field(target_payload, "function_flags", target)),
            "num_parms": require_int_field(target_payload, "num_parms", target),
            "parms_size": require_int_field(target_payload, "parms_size", target),
            "return_value_offset": format_hex(return_value_offset),
            "source_snapshot": source_snapshot["id"],
            "source_snapshot_sha256": source_snapshot["sha256"],
        }
        if field_key in DINO_COMPACT_COPIED_SCALAR_FIELDS:
            field = classify_property(prop, return_value_offset)
            if expected_class == "IntProperty":
                if field["type"] != "int32" or field["direction"] != "in" or common["element_size"] != 4:
                    raise SystemExit(f"{field_key} copied int32 shape drifted")
                copied.append(
                    {
                        **common,
                        "copied_field": field_key,
                        "direction": "in",
                        "type": "int32",
                        "descriptor": DINO_COMPACT_DESCRIPTOR_BY_TARGET[target],
                        "evidence_status": "descriptor-preflight-copied-scalar-only",
                    }
                )
            elif expected_class == "BoolProperty":
                bool_field_size, bool_byte_offset = require_bool_tail(prop, field_key)
                masks = field.get("bool_masks")
                if (
                    field["type"] != "bool"
                    or field["direction"] not in {"in", "return"}
                    or bool_field_size != 1
                    or bool_byte_offset != 0
                    or not isinstance(masks, dict)
                    or masks.get("byte_mask") != "0x01"
                    or masks.get("field_mask") != "0xff"
                    or prop.get("native_bool") is not False
                ):
                    raise SystemExit(f"{field_key} copied bool shape drifted")
                copied.append(
                    {
                        **common,
                        "copied_field": field_key,
                        "direction": field["direction"],
                        "type": "bool",
                        "bool_field_size": bool_field_size,
                        "bool_byte_offset": bool_byte_offset,
                        "byte_mask": masks["byte_mask"],
                        "field_mask": masks["field_mask"],
                        "native_bool": False,
                        "descriptor": DINO_COMPACT_DESCRIPTOR_BY_TARGET[target],
                        "evidence_status": "descriptor-preflight-copied-scalar-only",
                    }
                )
            else:
                raise SystemExit(f"{field_key} copied scalar class drifted")
        elif field_key in DINO_COMPACT_EXCLUDED_REASONS:
            excluded.append(
                {
                    **common,
                    "excluded_field": field_key,
                    "reason": DINO_COMPACT_EXCLUDED_REASONS[field_key],
                    "descriptor": DINO_COMPACT_DESCRIPTOR_BY_TARGET[target],
                    "evidence_status": "recognition-only-object-ref-excluded",
                }
            )
        else:
            raise SystemExit(f"{field_key} has no dino compact copy or exclusion policy")
    return copied, excluded


def build_dino_compact_descriptor_preflight_from_inputs(
    paths: list[Path],
    input_snapshots: list[dict[str, str]],
) -> dict[str, Any]:
    copied: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    expected_targets = expand_ufunction_targets([DINO_COMPACT_DESCRIPTOR_INPUT_TARGET_SET])
    expected_target_set = set(expected_targets)
    for path, source_snapshot in zip(paths, input_snapshots, strict=True):
        payload = load_json_file("snapshot", path)
        for target_payload in require_snapshot_payload(payload, path):
            target_identity = target_payload.get("target")
            if not isinstance(target_identity, dict):
                raise SystemExit(f"snapshot missing target identity: {path}")
            target = target_name(target_identity)
            if target not in expected_target_set:
                continue
            if target in seen_targets:
                raise SystemExit(f"duplicate dino compact descriptor target: {target}")
            seen_targets.add(target)
            target_copied, target_excluded = require_dino_compact_descriptor_shape(
                target_payload,
                source_snapshot,
            )
            copied.extend(target_copied)
            excluded.extend(target_excluded)

    emitted_copied_fields = [entry["copied_field"] for entry in copied]
    emitted_excluded_fields = [entry["excluded_field"] for entry in excluded]
    missing_targets = [target for target in expected_targets if target not in seen_targets]
    unexpected_targets = [target for target in seen_targets if target not in expected_target_set]
    missing_copied_fields = [
        field for field in DINO_COMPACT_COPIED_SCALAR_FIELDS if field not in emitted_copied_fields
    ]
    unexpected_copied_fields = [
        field for field in emitted_copied_fields if field not in DINO_COMPACT_COPIED_SCALAR_FIELDS
    ]
    missing_excluded_fields = [
        field for field in DINO_COMPACT_EXCLUDED_REASONS if field not in emitted_excluded_fields
    ]
    unexpected_excluded_fields = [
        field for field in emitted_excluded_fields if field not in DINO_COMPACT_EXCLUDED_REASONS
    ]
    blockers = [
        *[f"missing_target:{target}" for target in missing_targets],
        *[f"unexpected_target:{target}" for target in unexpected_targets],
        *[f"missing_copied_field:{field}" for field in missing_copied_fields],
        *[f"unexpected_copied_field:{field}" for field in unexpected_copied_fields],
        *[f"missing_excluded_field:{field}" for field in missing_excluded_fields],
        *[f"unexpected_excluded_field:{field}" for field in unexpected_excluded_fields],
    ]
    if blockers:
        raise SystemExit("dino compact descriptor preflight failed closed: " + ",".join(blockers))

    descriptors: list[dict[str, Any]] = []
    for target in expected_targets:
        descriptor = DINO_COMPACT_DESCRIPTOR_BY_TARGET.get(target)
        if descriptor is None:
            raise SystemExit(f"dino compact descriptor preflight has no descriptor for target: {target}")
        target_copied = [entry for entry in copied if entry["target"] == target]
        target_excluded = [entry for entry in excluded if entry["target"] == target]
        descriptors.append(
            {
                "descriptor": descriptor,
                "target": target,
                "copied_fields": [entry["copied_field"] for entry in target_copied],
                "excluded_object_refs": [entry["excluded_field"] for entry in target_excluded],
                "resource_scope": "dino_character_recognition_only",
                "resource_backing": "recognition_only_object_refs_excluded",
                "payload_policy": "copied_scalar_descriptor_only",
                "assigned_resource_kind": None,
                "assigned_event_kind": None,
                "assigned_event_kind_mask": None,
                "promotion_ready": False,
                "public_promotion": False,
                "public_surface": False,
                "evidence_status": "descriptor-preflight-only",
            }
        )

    emitted_descriptors = [entry["descriptor"] for entry in descriptors]
    missing_descriptors = [
        descriptor for descriptor in DINO_COMPACT_EXPECTED_DESCRIPTORS if descriptor not in emitted_descriptors
    ]
    unexpected_descriptors = [
        descriptor for descriptor in emitted_descriptors if descriptor not in DINO_COMPACT_EXPECTED_DESCRIPTORS
    ]
    if missing_descriptors or unexpected_descriptors:
        raise SystemExit(
            "dino compact descriptor preflight failed closed: "
            + ",".join(
                [
                    *[f"missing_descriptor:{descriptor}" for descriptor in missing_descriptors],
                    *[f"unexpected_descriptor:{descriptor}" for descriptor in unexpected_descriptors],
                ]
            )
        )

    return {
        "status": "internal-evidence-only",
        "scope": DINO_COMPACT_DESCRIPTOR_INPUT_TARGET_SET,
        "descriptor_count": len(descriptors),
        "resource_scope": "dino_character_recognition_only",
        "resource_backing": "recognition_only_object_refs_excluded",
        "payload_policy": "copied_scalar_descriptor_only",
        "assigned_resource_kind": None,
        "return_value_only": False,
        "assigned_event_kind": None,
        "assigned_event_kind_mask": None,
        "promotion_ready": False,
        "public_promotion": False,
        "public_surface": False,
        "descriptors": descriptors,
        "copied_scalars": copied,
        "excluded_object_refs": excluded,
        "safety_summary": {
            "artifact_status": "internal_evidence_only",
            "promotion_ready": False,
            "public_surface": False,
            "copied_scalar_count": len(copied),
            "excluded_object_ref_count": len(excluded),
            "explicitly_excluded": [
                "event_kind_assignment",
                "event_kind_mask_assignment",
                "identity",
                "lookup",
                "mutation",
                "object_refs",
                "public_sdk",
                "raw_params",
                "resource_handle",
                "return_override",
                "ue_function_calls",
            ],
        },
        "explicitly_not_assigned": [
            "event_kind",
            "event_kind_mask",
            "resource_kind",
            "public_metadata_json",
            "runtime_dispatcher_tables",
            "plugin_callbacks",
            "resource_handle",
            "identity",
            "lookup",
        ],
    }


def require_transfer_baccept_only_shape(target_payload: dict[str, Any], source_snapshot: dict[str, str]) -> list[dict[str, Any]]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit("transfer policy snapshot missing target identity or property chain")
    target = target_name(target_identity)
    expected = TRANSFER_BACCEPT_ONLY_EXPECTED_SHAPES.get(target)
    if expected is None:
        raise SystemExit(f"unexpected transfer policy target: {target}")
    if target_payload.get("status") != "candidate":
        raise SystemExit(f"{target} is not a candidate UFunction snapshot")
    if target_payload.get("inspection_mode") != "ufunction":
        raise SystemExit(f"{target} is not a UFunction inspection snapshot")

    if require_int_field(target_payload, "function_flags", target) != expected["function_flags"]:
        raise SystemExit(f"{target} FunctionFlags drifted")
    if require_int_field(target_payload, "num_parms", target) != expected["num_parms"]:
        raise SystemExit(f"{target} NumParms drifted")
    if require_int_field(target_payload, "parms_size", target) != expected["parms_size"]:
        raise SystemExit(f"{target} ParmsSize drifted")
    return_value_offset = require_int_field(target_payload, "return_value_offset", target)
    if return_value_offset != expected["return_value_offset"]:
        raise SystemExit(f"{target} ReturnValueOffset drifted")

    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{target} property_chain.properties is not a list")
    if parse_int_value(property_chain.get("expected_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} expected property count drifted")
    if parse_int_value(property_chain.get("observed_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} observed property count drifted")
    if len(properties) != len(expected["properties"]):
        raise SystemExit(f"{target} property list length drifted")

    copied: list[dict[str, Any]] = []
    for prop, (expected_name, expected_class) in zip(properties, expected["properties"], strict=True):
        if not isinstance(prop, dict):
            raise SystemExit(f"{target} property entry is not an object")
        name = prop.get("name")
        class_name = prop.get("class_name")
        if name != expected_name or class_name != expected_class:
            raise SystemExit(f"{target} property shape drifted: expected {expected_name}:{expected_class}")
        if prop.get("status") != "candidate":
            raise SystemExit(f"{target}.{expected_name} is not a candidate property")
        require_candidate_membership(prop, target, expected_name)
        field_key = f"{target}.{expected_name}"
        if field_key not in TRANSFER_BACCEPT_ONLY_COPIED_FIELDS:
            raise SystemExit(f"{field_key} has no transfer copied-field policy")
        field = require_bool_input_field(target, prop, expected_name)
        copied.append(
            {
                "target": target,
                "field": expected_name,
                "copied_field": field_key,
                "direction": "in",
                "type": "bool",
                "offset": format_hex(require_int_field(prop, "offset_internal", field_key)),
                "offset_internal": require_int_field(prop, "offset_internal", field_key),
                "element_size": require_int_field(prop, "element_size", field_key),
                "array_dim": require_int_field(prop, "array_dim", field_key),
                "byte_mask": field["bool_masks"]["byte_mask"],
                "field_mask": field["bool_masks"]["field_mask"],
                "native_bool": False,
                "function_flags": format_hex(require_int_field(target_payload, "function_flags", target)),
                "num_parms": require_int_field(target_payload, "num_parms", target),
                "parms_size": require_int_field(target_payload, "parms_size", target),
                "return_value_offset": format_hex(return_value_offset),
                "property_flags": format_hex(property_flags(prop) or 0),
                "property_class": expected_class,
                "source_snapshot": source_snapshot["id"],
                "source_snapshot_sha256": source_snapshot["sha256"],
                "evidence_status": "copied-bool-only",
            }
        )
    return copied


def require_transfer_forbidden_fields(target_payload: dict[str, Any], source_snapshot: dict[str, str]) -> list[dict[str, Any]]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit("transfer forbidden-field snapshot missing target identity or property chain")
    target = target_name(target_identity)
    if target_payload.get("status") != "candidate":
        raise SystemExit(f"{target} is not a candidate UFunction snapshot")
    if target_payload.get("inspection_mode") != "ufunction":
        raise SystemExit(f"{target} is not a UFunction inspection snapshot")

    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{target} property_chain.properties is not a list")
    observed_count = parse_int_value(property_chain.get("observed_count"))
    expected_count = parse_int_value(property_chain.get("expected_count"))
    if observed_count is None or expected_count is None or observed_count != expected_count:
        raise SystemExit(f"{target} property chain count drifted")
    if observed_count != len(properties):
        raise SystemExit(f"{target} property list length drifted")

    forbidden: list[dict[str, Any]] = []
    for prop in properties:
        if not isinstance(prop, dict):
            raise SystemExit(f"{target} property entry is not an object")
        name = prop.get("name")
        class_name = prop.get("class_name")
        if not isinstance(name, str) or not name or not isinstance(class_name, str) or not class_name:
            raise SystemExit(f"{target} property identity drifted")
        if prop.get("status") != "candidate":
            raise SystemExit(f"{target}.{name} is not a candidate property")
        require_candidate_membership(prop, target, name)
        field_key = f"{target}.{name}"
        reason = TRANSFER_BACCEPT_ONLY_EXCLUDED_REASONS.get(field_key)
        if reason is None:
            raise SystemExit(f"{field_key} has no transfer forbidden-field policy")
        forbidden.append(
            {
                "target": target,
                "field": name,
                "forbidden_field": field_key,
                "reason": reason,
                "property_class": class_name,
                "offset": format_hex(require_int_field(prop, "offset_internal", field_key)),
                "offset_internal": require_int_field(prop, "offset_internal", field_key),
                "element_size": require_int_field(prop, "element_size", field_key),
                "array_dim": require_int_field(prop, "array_dim", field_key),
                "property_flags": format_hex(property_flags(prop) or 0),
                "source_snapshot": source_snapshot["id"],
                "source_snapshot_sha256": source_snapshot["sha256"],
            }
        )
    return forbidden


def require_mission_copied_bool_shape(target_payload: dict[str, Any], source_snapshot: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit("mission policy snapshot missing target identity or property chain")
    target = target_name(target_identity)
    expected = MISSION_COPIED_BOOL_EXPECTED_SHAPES.get(target)
    if expected is None:
        raise SystemExit(f"unexpected mission policy target: {target}")
    if target_payload.get("status") != "candidate":
        raise SystemExit(f"{target} is not a candidate UFunction snapshot")
    if target_payload.get("inspection_mode") != "ufunction":
        raise SystemExit(f"{target} is not a UFunction inspection snapshot")

    if require_int_field(target_payload, "function_flags", target) != expected["function_flags"]:
        raise SystemExit(f"{target} FunctionFlags drifted")
    if require_int_field(target_payload, "num_parms", target) != expected["num_parms"]:
        raise SystemExit(f"{target} NumParms drifted")
    if require_int_field(target_payload, "parms_size", target) != expected["parms_size"]:
        raise SystemExit(f"{target} ParmsSize drifted")
    return_value_offset = require_int_field(target_payload, "return_value_offset", target)
    if return_value_offset != expected["return_value_offset"]:
        raise SystemExit(f"{target} ReturnValueOffset drifted")

    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{target} property_chain.properties is not a list")
    if parse_int_value(property_chain.get("expected_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} expected property count drifted")
    if parse_int_value(property_chain.get("observed_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} observed property count drifted")
    if len(properties) != len(expected["properties"]):
        raise SystemExit(f"{target} property list length drifted")

    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    for prop, (expected_name, expected_class) in zip(properties, expected["properties"], strict=True):
        if not isinstance(prop, dict):
            raise SystemExit(f"{target} property entry is not an object")
        name = prop.get("name")
        class_name = prop.get("class_name")
        if name != expected_name or class_name != expected_class:
            raise SystemExit(f"{target} property shape drifted: expected {expected_name}:{expected_class}")
        if prop.get("status") != "candidate":
            raise SystemExit(f"{target}.{expected_name} is not a candidate property")
        require_candidate_membership(prop, target, expected_name)
        field_key = f"{target}.{expected_name}"

        common = {
            "target": target,
            "field": expected_name,
            "offset": format_hex(require_int_field(prop, "offset_internal", field_key)),
            "offset_internal": require_int_field(prop, "offset_internal", field_key),
            "element_size": require_int_field(prop, "element_size", field_key),
            "array_dim": require_int_field(prop, "array_dim", field_key),
            "property_flags": format_hex(property_flags(prop) or 0),
            "property_class": expected_class,
            "function_flags": format_hex(require_int_field(target_payload, "function_flags", target)),
            "num_parms": require_int_field(target_payload, "num_parms", target),
            "parms_size": require_int_field(target_payload, "parms_size", target),
            "return_value_offset": format_hex(return_value_offset),
            "source_snapshot": source_snapshot["id"],
            "source_snapshot_sha256": source_snapshot["sha256"],
        }
        if field_key in MISSION_COPIED_BOOL_FIELDS:
            bool_field_size, bool_byte_offset = require_bool_tail(prop, field_key)
            field = classify_property(prop, return_value_offset)
            masks = field.get("bool_masks")
            if (
                field["type"] != "bool"
                or field["direction"] not in {"in", "return"}
                or bool_field_size != 1
                or bool_byte_offset != 0
                or not isinstance(masks, dict)
                or masks.get("byte_mask") != "0x01"
                or masks.get("field_mask") != "0xff"
                or prop.get("native_bool") is not False
            ):
                raise SystemExit(f"{field_key} copied bool shape drifted")
            copied.append(
                {
                    **common,
                    "copied_field": field_key,
                    "direction": field["direction"],
                    "type": "bool",
                    "bool_field_size": bool_field_size,
                    "bool_byte_offset": bool_byte_offset,
                    "byte_mask": masks["byte_mask"],
                    "field_mask": masks["field_mask"],
                    "native_bool": False,
                    "evidence_status": "copied-mission-bool-only",
                }
            )
        else:
            reason = MISSION_REDACTED_FIELD_REASONS.get(field_key)
            if reason is None:
                raise SystemExit(f"{field_key} has no mission redaction policy")
            redacted.append(
                {
                    **common,
                    "redacted_field": field_key,
                    "reason": reason,
                    "evidence_status": "recognition-only-redacted",
                }
            )
    return copied, redacted


def require_structure_return_only_shape(
    target_payload: dict[str, Any],
    source_snapshot: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit("structure policy snapshot missing target identity or property chain")
    target = target_name(target_identity)
    expected = STRUCTURE_RETURN_ONLY_EXPECTED_SHAPES.get(target)
    if expected is None:
        raise SystemExit(f"unexpected structure policy target: {target}")
    if target_payload.get("status") != "candidate":
        raise SystemExit(f"{target} is not a candidate UFunction snapshot")
    if target_payload.get("inspection_mode") != "ufunction":
        raise SystemExit(f"{target} is not a UFunction inspection snapshot")

    if require_int_field(target_payload, "function_flags", target) != expected["function_flags"]:
        raise SystemExit(f"{target} FunctionFlags drifted")
    if require_int_field(target_payload, "num_parms", target) != expected["num_parms"]:
        raise SystemExit(f"{target} NumParms drifted")
    if require_int_field(target_payload, "parms_size", target) != expected["parms_size"]:
        raise SystemExit(f"{target} ParmsSize drifted")
    return_value_offset = require_int_field(target_payload, "return_value_offset", target)
    if return_value_offset != expected["return_value_offset"]:
        raise SystemExit(f"{target} ReturnValueOffset drifted")

    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{target} property_chain.properties is not a list")
    if parse_int_value(property_chain.get("expected_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} expected property count drifted")
    if parse_int_value(property_chain.get("observed_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} observed property count drifted")
    if len(properties) != len(expected["properties"]):
        raise SystemExit(f"{target} property list length drifted")

    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    for prop, (expected_name, expected_class) in zip(properties, expected["properties"], strict=True):
        if not isinstance(prop, dict):
            raise SystemExit(f"{target} property entry is not an object")
        name = prop.get("name")
        class_name = prop.get("class_name")
        if name != expected_name or class_name != expected_class:
            raise SystemExit(f"{target} property shape drifted: expected {expected_name}:{expected_class}")
        if prop.get("status") != "candidate":
            raise SystemExit(f"{target}.{expected_name} is not a candidate property")
        require_candidate_membership(prop, target, expected_name)
        field_key = f"{target}.{expected_name}"

        common = {
            "target": target,
            "field": expected_name,
            "offset": format_hex(require_int_field(prop, "offset_internal", field_key)),
            "offset_internal": require_int_field(prop, "offset_internal", field_key),
            "element_size": require_int_field(prop, "element_size", field_key),
            "array_dim": require_int_field(prop, "array_dim", field_key),
            "property_flags": format_hex(property_flags(prop) or 0),
            "property_class": expected_class,
            "function_flags": format_hex(require_int_field(target_payload, "function_flags", target)),
            "num_parms": require_int_field(target_payload, "num_parms", target),
            "parms_size": require_int_field(target_payload, "parms_size", target),
            "return_value_offset": format_hex(return_value_offset),
            "source_snapshot": source_snapshot["id"],
            "source_snapshot_sha256": source_snapshot["sha256"],
        }
        if field_key in STRUCTURE_RETURN_ONLY_COPIED_FIELDS:
            bool_field_size, bool_byte_offset = require_bool_tail(prop, field_key)
            field = classify_property(prop, return_value_offset)
            masks = field.get("bool_masks")
            if (
                field["type"] != "bool"
                or field["direction"] != "return"
                or bool_field_size != 1
                or bool_byte_offset != 0
                or not isinstance(masks, dict)
                or masks.get("byte_mask") != "0x01"
                or masks.get("field_mask") != "0xff"
                or prop.get("native_bool") is not False
            ):
                raise SystemExit(f"{field_key} copied return bool shape drifted")
            copied.append(
                {
                    **common,
                    "copied_field": field_key,
                    "direction": "return",
                    "type": "bool",
                    "bool_field_size": bool_field_size,
                    "bool_byte_offset": bool_byte_offset,
                    "byte_mask": masks["byte_mask"],
                    "field_mask": masks["field_mask"],
                    "native_bool": False,
                    "evidence_status": "copied-structure-return-bool-only",
                }
            )
        elif field_key in STRUCTURE_RETURN_ONLY_REDACTED_FIELD_REASONS:
            redacted.append(
                {
                    **common,
                    "redacted_field": field_key,
                    "reason": STRUCTURE_RETURN_ONLY_REDACTED_FIELD_REASONS[field_key],
                    "evidence_status": "recognition-only-redacted",
                }
            )
        elif target not in STRUCTURE_RETURN_ONLY_DEFERRED_REASONS:
            raise SystemExit(f"{field_key} has no structure redaction or copy policy")

    deferred: list[dict[str, Any]] = []
    if target in STRUCTURE_RETURN_ONLY_DEFERRED_REASONS:
        deferred.append(
            {
                "target": target,
                "deferred_target": target,
                "reason": STRUCTURE_RETURN_ONLY_DEFERRED_REASONS[target],
                "function_flags": format_hex(require_int_field(target_payload, "function_flags", target)),
                "num_parms": require_int_field(target_payload, "num_parms", target),
                "parms_size": require_int_field(target_payload, "parms_size", target),
                "return_value_offset": format_hex(return_value_offset),
                "property_count": len(properties),
                "source_snapshot": source_snapshot["id"],
                "source_snapshot_sha256": source_snapshot["sha256"],
                "evidence_status": "explicitly-deferred-target",
            }
        )
    return copied, redacted, deferred


def require_structure_nonpin_copied_scalar_shape(
    target_payload: dict[str, Any],
    source_snapshot: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit("structure non-PIN policy snapshot missing target identity or property chain")
    target = target_name(target_identity)
    expected = STRUCTURE_RETURN_ONLY_EXPECTED_SHAPES.get(target)
    if expected is None or target == "PrimalStructureItemContainer.VerifyPinCode":
        raise SystemExit(f"unexpected structure non-PIN policy target: {target}")
    if target_payload.get("status") != "candidate":
        raise SystemExit(f"{target} is not a candidate UFunction snapshot")
    if target_payload.get("inspection_mode") != "ufunction":
        raise SystemExit(f"{target} is not a UFunction inspection snapshot")

    if require_int_field(target_payload, "function_flags", target) != expected["function_flags"]:
        raise SystemExit(f"{target} FunctionFlags drifted")
    if require_int_field(target_payload, "num_parms", target) != expected["num_parms"]:
        raise SystemExit(f"{target} NumParms drifted")
    if require_int_field(target_payload, "parms_size", target) != expected["parms_size"]:
        raise SystemExit(f"{target} ParmsSize drifted")
    return_value_offset = require_int_field(target_payload, "return_value_offset", target)
    if return_value_offset != expected["return_value_offset"]:
        raise SystemExit(f"{target} ReturnValueOffset drifted")

    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{target} property_chain.properties is not a list")
    if parse_int_value(property_chain.get("expected_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} expected property count drifted")
    if parse_int_value(property_chain.get("observed_count")) != len(expected["properties"]):
        raise SystemExit(f"{target} observed property count drifted")
    if len(properties) != len(expected["properties"]):
        raise SystemExit(f"{target} property list length drifted")

    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    for prop, (expected_name, expected_class) in zip(properties, expected["properties"], strict=True):
        if not isinstance(prop, dict):
            raise SystemExit(f"{target} property entry is not an object")
        name = prop.get("name")
        class_name = prop.get("class_name")
        if name != expected_name or class_name != expected_class:
            raise SystemExit(f"{target} property shape drifted: expected {expected_name}:{expected_class}")
        if prop.get("status") != "candidate":
            raise SystemExit(f"{target}.{expected_name} is not a candidate property")
        require_candidate_membership(prop, target, expected_name)
        field_key = f"{target}.{expected_name}"

        common = {
            "target": target,
            "field": expected_name,
            "offset": format_hex(require_int_field(prop, "offset_internal", field_key)),
            "offset_internal": require_int_field(prop, "offset_internal", field_key),
            "element_size": require_int_field(prop, "element_size", field_key),
            "array_dim": require_int_field(prop, "array_dim", field_key),
            "property_flags": format_hex(property_flags(prop) or 0),
            "property_class": expected_class,
            "function_flags": format_hex(require_int_field(target_payload, "function_flags", target)),
            "num_parms": require_int_field(target_payload, "num_parms", target),
            "parms_size": require_int_field(target_payload, "parms_size", target),
            "return_value_offset": format_hex(return_value_offset),
            "source_snapshot": source_snapshot["id"],
            "source_snapshot_sha256": source_snapshot["sha256"],
        }
        if field_key in STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS:
            field = classify_property(prop, return_value_offset)
            if expected_class == "BoolProperty":
                bool_field_size, bool_byte_offset = require_bool_tail(prop, field_key)
                masks = field.get("bool_masks")
                if (
                    field["type"] != "bool"
                    or field["direction"] not in {"in", "return"}
                    or bool_field_size != 1
                    or bool_byte_offset != 0
                    or not isinstance(masks, dict)
                    or masks.get("byte_mask") != "0x01"
                    or masks.get("field_mask") != "0xff"
                    or prop.get("native_bool") is not False
                ):
                    raise SystemExit(f"{field_key} copied bool shape drifted")
                copied.append(
                    {
                        **common,
                        "copied_field": field_key,
                        "direction": field["direction"],
                        "type": "bool",
                        "bool_field_size": bool_field_size,
                        "bool_byte_offset": bool_byte_offset,
                        "byte_mask": masks["byte_mask"],
                        "field_mask": masks["field_mask"],
                        "native_bool": False,
                        "evidence_status": "copied-structure-nonpin-scalar-only",
                    }
                )
            else:
                if field["type"] != "int32" or field["direction"] != "in" or common["element_size"] != 4:
                    raise SystemExit(f"{field_key} copied scalar shape drifted")
                copied.append(
                    {
                        **common,
                        "copied_field": field_key,
                        "direction": "in",
                        "type": "int32",
                        "evidence_status": "copied-structure-nonpin-scalar-only",
                    }
                )
        elif field_key in STRUCTURE_NONPIN_REDACTED_FIELD_REASONS:
            redacted.append(
                {
                    **common,
                    "redacted_field": field_key,
                    "reason": STRUCTURE_NONPIN_REDACTED_FIELD_REASONS[field_key],
                    "evidence_status": "recognition-only-redacted",
                }
            )
        else:
            raise SystemExit(f"{field_key} has no structure non-PIN redaction or copy policy")
    return copied, redacted


def build_item_return_only_policy_slice(*, snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    paths, missing_targets = snapshot_paths_from_target_sets(snapshot_root, [ITEM_RETURN_ONLY_INPUT_TARGET_SET])
    if missing_targets:
        raise SystemExit("item policy manifest missing targets: " + ",".join(missing_targets))

    input_snapshots = [
        {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        for index, path in enumerate(paths, start=1)
    ]
    copied: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    for path, source_snapshot in zip(paths, input_snapshots, strict=True):
        payload = load_json_file("snapshot", path)
        targets = require_snapshot_payload(payload, path)
        for target_payload in targets:
            target_identity = target_payload.get("target")
            if not isinstance(target_identity, dict):
                raise SystemExit(f"snapshot missing target identity: {path}")
            target = target_name(target_identity)
            if target in seen_targets:
                raise SystemExit(f"duplicate item policy target: {target}")
            seen_targets.add(target)
            target_copied, target_excluded = require_item_return_only_shape(target_payload, source_snapshot)
            copied.extend(target_copied)
            excluded.extend(target_excluded)

    expected_input_targets = expand_ufunction_targets([ITEM_RETURN_ONLY_INPUT_TARGET_SET])
    expected_output_targets = expand_ufunction_targets([ITEM_RETURN_ONLY_OUTPUT_TARGET_SET])
    emitted_copied_fields = [entry["copied_field"] for entry in copied]
    emitted_excluded_fields = [entry["excluded_field"] for entry in excluded]
    missing_input_targets = [target for target in expected_input_targets if target not in seen_targets]
    unexpected_input_targets = [target for target in seen_targets if target not in expected_input_targets]
    missing_copied_fields = [field for field in ITEM_RETURN_ONLY_COPIED_FIELDS if field not in emitted_copied_fields]
    unexpected_copied_fields = [field for field in emitted_copied_fields if field not in ITEM_RETURN_ONLY_COPIED_FIELDS]
    missing_excluded_fields = [
        field for field in ITEM_RETURN_ONLY_EXCLUDED_REASONS if field not in emitted_excluded_fields
    ]
    unexpected_excluded_fields = [
        field for field in emitted_excluded_fields if field not in ITEM_RETURN_ONLY_EXCLUDED_REASONS
    ]
    output_targets = [entry["target"] for entry in copied]
    missing_output_targets = [target for target in expected_output_targets if target not in output_targets]
    unexpected_output_targets = [target for target in output_targets if target not in expected_output_targets]
    blockers = [
        *[f"missing_input_target:{target}" for target in missing_input_targets],
        *[f"unexpected_input_target:{target}" for target in unexpected_input_targets],
        *[f"missing_copied_field:{field}" for field in missing_copied_fields],
        *[f"unexpected_copied_field:{field}" for field in unexpected_copied_fields],
        *[f"missing_excluded_field:{field}" for field in missing_excluded_fields],
        *[f"unexpected_excluded_field:{field}" for field in unexpected_excluded_fields],
        *[f"missing_output_target:{target}" for target in missing_output_targets],
        *[f"unexpected_output_target:{target}" for target in unexpected_output_targets],
    ]
    if blockers:
        raise SystemExit("item return-only policy slice failed closed: " + ",".join(blockers))

    return {
        "schema": ITEM_RETURN_ONLY_POLICY_SCHEMA,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "snapshot_root": "redacted",
        "input_target_set": ITEM_RETURN_ONLY_INPUT_TARGET_SET,
        "output_target_set": ITEM_RETURN_ONLY_OUTPUT_TARGET_SET,
        "policy_status": "evidence-only",
        "missing_targets": [],
        "coverage": {
            "status": "complete",
            "input_targets": expected_input_targets,
            "copied_targets": expected_output_targets,
            "copied_fields": list(ITEM_RETURN_ONLY_COPIED_FIELDS),
            "excluded_fields": list(ITEM_RETURN_ONLY_EXCLUDED_REASONS),
        },
        "copied_return_bools": copied,
        "excluded_fields": excluded,
        "descriptor_preflight": build_item_return_only_descriptor_preflight(copied),
        "safety_summary": {
            "artifact_status": "evidence_only",
            "promotion_ready": False,
            "intended_use": "offline_review_only",
            "copied_bool_count": len(copied),
            "descriptor_preflight_count": len(ITEM_RETURN_ONLY_EXPECTED_DESCRIPTORS),
            "excluded_field_count": len(excluded),
            "explicitly_excluded": [
                "CraftBlueprint",
                "CanRepair.bIgnoreInventoryRequirement",
                "CraftBlueprint.bConsumeResources",
                "toInventory",
                "DestinationItem",
                "AdditionalData",
                "event_kind_assignment",
                "event_kind_mask_assignment",
                "object_refs",
                "mutation",
                "return_override",
                "public_sdk",
            ],
        },
        "non_claims": [
            "does not promote public SDK callbacks or public metadata helpers",
            "does not assign event_kind or event_kind_mask values",
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
            "does not copy CraftBlueprint, bIgnoreInventoryRequirement, bConsumeResources, toInventory, DestinationItem, or AdditionalData",
        ],
    }


def build_transfer_baccept_only_policy_slice(*, snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    paths, missing_targets = snapshot_paths_from_target_sets(snapshot_root, [TRANSFER_BACCEPT_ONLY_INPUT_TARGET_SET])
    if missing_targets:
        raise SystemExit("transfer bAccept policy manifest missing targets: " + ",".join(missing_targets))

    input_snapshots = []
    copied: list[dict[str, Any]] = []
    forbidden: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    for index, path in enumerate(paths, start=1):
        source_snapshot = {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        payload = load_json_file("snapshot", path)
        targets = require_snapshot_payload(payload, path)
        for target_payload in targets:
            target_identity = target_payload.get("target")
            if not isinstance(target_identity, dict):
                raise SystemExit(f"snapshot missing target identity: {path}")
            target = target_name(target_identity)
            if target in seen_targets:
                raise SystemExit(f"duplicate transfer policy target: {target}")
            seen_targets.add(target)
            source_snapshot["target"] = target
            input_snapshots.append(source_snapshot)
            if target in TRANSFER_BACCEPT_ONLY_EXPECTED_SHAPES:
                copied.extend(require_transfer_baccept_only_shape(target_payload, source_snapshot))
            else:
                forbidden.extend(require_transfer_forbidden_fields(target_payload, source_snapshot))

    expected_input_targets = expand_ufunction_targets([TRANSFER_BACCEPT_ONLY_INPUT_TARGET_SET])
    expected_output_targets = expand_ufunction_targets([TRANSFER_BACCEPT_ONLY_OUTPUT_TARGET_SET])
    emitted_copied_fields = [entry["copied_field"] for entry in copied]
    emitted_forbidden_fields = [entry["forbidden_field"] for entry in forbidden]
    missing_input_targets = [target for target in expected_input_targets if target not in seen_targets]
    unexpected_input_targets = [target for target in seen_targets if target not in expected_input_targets]
    missing_copied_fields = [
        field for field in TRANSFER_BACCEPT_ONLY_COPIED_FIELDS if field not in emitted_copied_fields
    ]
    unexpected_copied_fields = [
        field for field in emitted_copied_fields if field not in TRANSFER_BACCEPT_ONLY_COPIED_FIELDS
    ]
    output_targets = [entry["target"] for entry in copied]
    missing_output_targets = [target for target in expected_output_targets if target not in output_targets]
    unexpected_output_targets = [target for target in output_targets if target not in expected_output_targets]
    missing_forbidden_fields = [
        field for field in TRANSFER_BACCEPT_ONLY_EXCLUDED_REASONS if field not in emitted_forbidden_fields
    ]
    unexpected_forbidden_fields = [
        field for field in emitted_forbidden_fields if field not in TRANSFER_BACCEPT_ONLY_EXCLUDED_REASONS
    ]
    blockers = [
        *[f"missing_input_target:{target}" for target in missing_input_targets],
        *[f"unexpected_input_target:{target}" for target in unexpected_input_targets],
        *[f"missing_copied_field:{field}" for field in missing_copied_fields],
        *[f"unexpected_copied_field:{field}" for field in unexpected_copied_fields],
        *[f"missing_forbidden_field:{field}" for field in missing_forbidden_fields],
        *[f"unexpected_forbidden_field:{field}" for field in unexpected_forbidden_fields],
        *[f"missing_output_target:{target}" for target in missing_output_targets],
        *[f"unexpected_output_target:{target}" for target in unexpected_output_targets],
    ]
    if blockers:
        raise SystemExit("transfer bAccept policy slice failed closed: " + ",".join(blockers))

    return {
        "schema": TRANSFER_BACCEPT_ONLY_POLICY_SCHEMA,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "snapshot_root": "redacted",
        "input_target_set": TRANSFER_BACCEPT_ONLY_INPUT_TARGET_SET,
        "output_target_set": TRANSFER_BACCEPT_ONLY_OUTPUT_TARGET_SET,
        "policy_status": "evidence-only",
        "missing_targets": [],
        "coverage": {
            "status": "complete",
            "input_targets": expected_input_targets,
            "copied_targets": expected_output_targets,
            "copied_fields": list(TRANSFER_BACCEPT_ONLY_COPIED_FIELDS),
            "forbidden_fields": list(TRANSFER_BACCEPT_ONLY_EXCLUDED_REASONS),
        },
        "copied_bool": copied[0],
        "forbidden_transfer_fields": forbidden,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "promotion_ready": False,
            "intended_use": "offline_review_only",
            "copied_bool_count": len(copied),
            "forbidden_field_count": len(forbidden),
            "explicitly_excluded": [
                "ARKTributeDino",
                "ArkTributePlayerData",
                "AllowDownloadDino.ReturnValue",
                "DownloadedDino",
                "InventoryComp",
                "IsAllowedToTransfer.ReturnValue",
                "ServerDownloadTransferredPlayer.SpawnPointID",
                "ServerDownloadTransferredPlayer.spawnPointRegionIndex",
                "ServerRequestSpawnPointsForDownloadedCharacters.IgnoreBedID",
                "ServerRequestSpawnPointsForDownloadedCharacters.PlayerDataID",
                "TheDinoClass",
                "WorldContextObject",
                "arrays",
                "class_refs",
                "dispatcher_wiring",
                "ids",
                "mutation",
                "object_refs",
                "public_sdk",
                "return_override",
                "runtime_hook_wiring",
                "strings",
                "tribute_structs",
            ],
        },
        "non_claims": [
            "does not promote public SDK callbacks or public metadata helpers",
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
            "does not promote runtime hook wiring, dispatcher wiring, transfer payload decoding, or public Transfer SDK",
            "does not copy spawn point ids, region indexes, player data ids, bed ids, return bools, object refs, class refs, tribute structs, arrays, strings, or ids",
        ],
    }


def build_mission_copied_bool_policy_slice(*, snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    paths, missing_targets = snapshot_paths_from_target_sets(snapshot_root, [MISSION_COPIED_BOOL_INPUT_TARGET_SET])
    if missing_targets:
        raise SystemExit("mission copied-bool policy manifest missing targets: " + ",".join(missing_targets))

    input_snapshots = []
    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    for index, path in enumerate(paths, start=1):
        source_snapshot = {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        payload = load_json_file("snapshot", path)
        targets = require_snapshot_payload(payload, path)
        for target_payload in targets:
            target_identity = target_payload.get("target")
            if not isinstance(target_identity, dict):
                raise SystemExit(f"snapshot missing target identity: {path}")
            target = target_name(target_identity)
            if target in seen_targets:
                raise SystemExit(f"duplicate mission policy target: {target}")
            seen_targets.add(target)
            source_snapshot["target"] = target
            input_snapshots.append(source_snapshot)
            target_copied, target_redacted = require_mission_copied_bool_shape(target_payload, source_snapshot)
            copied.extend(target_copied)
            redacted.extend(target_redacted)

    expected_input_targets = expand_ufunction_targets([MISSION_COPIED_BOOL_INPUT_TARGET_SET])
    expected_output_targets = expand_ufunction_targets([MISSION_COPIED_BOOL_OUTPUT_TARGET_SET])
    emitted_copied_fields = [entry["copied_field"] for entry in copied]
    emitted_redacted_fields = [entry["redacted_field"] for entry in redacted]
    missing_input_targets = [target for target in expected_input_targets if target not in seen_targets]
    unexpected_input_targets = [target for target in seen_targets if target not in expected_input_targets]
    missing_output_targets = [target for target in expected_output_targets if target not in {entry["target"] for entry in copied}]
    unexpected_output_targets = [target for target in {entry["target"] for entry in copied} if target not in expected_output_targets]
    missing_copied_fields = [field for field in MISSION_COPIED_BOOL_FIELDS if field not in emitted_copied_fields]
    unexpected_copied_fields = [field for field in emitted_copied_fields if field not in MISSION_COPIED_BOOL_FIELDS]
    missing_redacted_fields = [field for field in MISSION_REDACTED_FIELD_REASONS if field not in emitted_redacted_fields]
    unexpected_redacted_fields = [field for field in emitted_redacted_fields if field not in MISSION_REDACTED_FIELD_REASONS]
    blockers = [
        *[f"missing_input_target:{target}" for target in missing_input_targets],
        *[f"unexpected_input_target:{target}" for target in unexpected_input_targets],
        *[f"missing_output_target:{target}" for target in missing_output_targets],
        *[f"unexpected_output_target:{target}" for target in unexpected_output_targets],
        *[f"missing_copied_field:{field}" for field in missing_copied_fields],
        *[f"unexpected_copied_field:{field}" for field in unexpected_copied_fields],
        *[f"missing_redacted_field:{field}" for field in missing_redacted_fields],
        *[f"unexpected_redacted_field:{field}" for field in unexpected_redacted_fields],
    ]
    if blockers:
        raise SystemExit("mission copied-bool policy slice failed closed: " + ",".join(blockers))

    return {
        "schema": MISSION_COPIED_BOOL_POLICY_SCHEMA,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "snapshot_root": "redacted",
        "input_target_set": MISSION_COPIED_BOOL_INPUT_TARGET_SET,
        "output_target_set": MISSION_COPIED_BOOL_OUTPUT_TARGET_SET,
        "policy_status": "evidence-only",
        "missing_targets": [],
        "coverage": {
            "status": "complete",
            "input_targets": expected_input_targets,
            "copied_targets": expected_output_targets,
            "copied_fields": list(MISSION_COPIED_BOOL_FIELDS),
            "redacted_fields": list(MISSION_REDACTED_FIELD_REASONS),
        },
        "copied_bools": copied,
        "redacted_mission_fields": redacted,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "promotion_ready": False,
            "intended_use": "offline_review_only",
            "copied_bool_count": len(copied),
            "redacted_field_count": len(redacted),
            "explicitly_excluded": [
                "GetPlayerUsableItems.OutItemIDs",
                "Mission SDK",
                "arrays",
                "dispatcher_wiring",
                "hook_wiring",
                "mission_identity",
                "mutation",
                "object_refs",
                "player_identity",
                "public_sdk",
                "raw_params",
                "resource_handle",
                "return_override",
                "runtime_markers",
            ],
        },
        "non_claims": [
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
            "does not promote public SDK callbacks or public metadata helpers",
            "does not promote runtime hook wiring, dispatcher wiring, mission payload decoding, or public Mission SDK",
            "does not copy player/controller/character object refs, OutItemIDs arrays, mission identity, player identity, or ResourceHandle",
        ],
    }


def build_structure_return_only_policy_slice(*, snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    paths, missing_targets = snapshot_paths_from_target_sets(snapshot_root, [STRUCTURE_RETURN_ONLY_INPUT_TARGET_SET])
    if missing_targets:
        raise SystemExit("structure return-only policy manifest missing targets: " + ",".join(missing_targets))

    input_snapshots = []
    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    for index, path in enumerate(paths, start=1):
        source_snapshot = {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        payload = load_json_file("snapshot", path)
        targets = require_snapshot_payload(payload, path)
        for target_payload in targets:
            target_identity = target_payload.get("target")
            if not isinstance(target_identity, dict):
                raise SystemExit(f"snapshot missing target identity: {path}")
            target = target_name(target_identity)
            if target in seen_targets:
                raise SystemExit(f"duplicate structure policy target: {target}")
            seen_targets.add(target)
            source_snapshot["target"] = target
            input_snapshots.append(source_snapshot)
            target_copied, target_redacted, target_deferred = require_structure_return_only_shape(
                target_payload,
                source_snapshot,
            )
            copied.extend(target_copied)
            redacted.extend(target_redacted)
            deferred.extend(target_deferred)

    expected_input_targets = expand_ufunction_targets([STRUCTURE_RETURN_ONLY_INPUT_TARGET_SET])
    expected_output_targets = expand_ufunction_targets([STRUCTURE_RETURN_ONLY_OUTPUT_TARGET_SET])
    emitted_copied_fields = [entry["copied_field"] for entry in copied]
    emitted_redacted_fields = [entry["redacted_field"] for entry in redacted]
    emitted_deferred_targets = [entry["deferred_target"] for entry in deferred]
    missing_input_targets = [target for target in expected_input_targets if target not in seen_targets]
    unexpected_input_targets = [target for target in seen_targets if target not in expected_input_targets]
    missing_output_targets = [target for target in expected_output_targets if target not in {entry["target"] for entry in copied}]
    unexpected_output_targets = [target for target in {entry["target"] for entry in copied} if target not in expected_output_targets]
    missing_copied_fields = [field for field in STRUCTURE_RETURN_ONLY_COPIED_FIELDS if field not in emitted_copied_fields]
    unexpected_copied_fields = [field for field in emitted_copied_fields if field not in STRUCTURE_RETURN_ONLY_COPIED_FIELDS]
    missing_redacted_fields = [
        field for field in STRUCTURE_RETURN_ONLY_REDACTED_FIELD_REASONS if field not in emitted_redacted_fields
    ]
    unexpected_redacted_fields = [
        field for field in emitted_redacted_fields if field not in STRUCTURE_RETURN_ONLY_REDACTED_FIELD_REASONS
    ]
    missing_deferred_targets = [
        target for target in STRUCTURE_RETURN_ONLY_DEFERRED_REASONS if target not in emitted_deferred_targets
    ]
    unexpected_deferred_targets = [
        target for target in emitted_deferred_targets if target not in STRUCTURE_RETURN_ONLY_DEFERRED_REASONS
    ]
    blockers = [
        *[f"missing_input_target:{target}" for target in missing_input_targets],
        *[f"unexpected_input_target:{target}" for target in unexpected_input_targets],
        *[f"missing_output_target:{target}" for target in missing_output_targets],
        *[f"unexpected_output_target:{target}" for target in unexpected_output_targets],
        *[f"missing_copied_field:{field}" for field in missing_copied_fields],
        *[f"unexpected_copied_field:{field}" for field in unexpected_copied_fields],
        *[f"missing_redacted_field:{field}" for field in missing_redacted_fields],
        *[f"unexpected_redacted_field:{field}" for field in unexpected_redacted_fields],
        *[f"missing_deferred_target:{target}" for target in missing_deferred_targets],
        *[f"unexpected_deferred_target:{target}" for target in unexpected_deferred_targets],
    ]
    if blockers:
        raise SystemExit("structure return-only policy slice failed closed: " + ",".join(blockers))

    return {
        "schema": STRUCTURE_RETURN_ONLY_POLICY_SCHEMA,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "snapshot_root": "redacted",
        "input_target_set": STRUCTURE_RETURN_ONLY_INPUT_TARGET_SET,
        "output_target_set": STRUCTURE_RETURN_ONLY_OUTPUT_TARGET_SET,
        "policy_status": "evidence-only",
        "missing_targets": [],
        "coverage": {
            "status": "complete",
            "input_targets": expected_input_targets,
            "copied_targets": expected_output_targets,
            "copied_fields": list(STRUCTURE_RETURN_ONLY_COPIED_FIELDS),
            "redacted_fields": list(STRUCTURE_RETURN_ONLY_REDACTED_FIELD_REASONS),
            "deferred_targets": list(STRUCTURE_RETURN_ONLY_DEFERRED_REASONS),
        },
        "copied_return_bools": copied,
        "redacted_structure_fields": redacted,
        "deferred_structure_targets": deferred,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "promotion_ready": False,
            "intended_use": "offline_review_only",
            "copied_bool_count": len(copied),
            "redacted_field_count": len(redacted),
            "deferred_target_count": len(deferred),
            "explicitly_excluded": [
                "AllowToggleActivation",
                "CanSeat",
                "ForPC",
                "SetVariant",
                "VerifyPinCode",
                "identity",
                "lookup",
                "mutation",
                "object_refs",
                "pinCode",
                "public_sdk",
                "resource_handle",
                "return_override",
            ],
        },
        "non_claims": [
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
            "does not promote public SDK callbacks or public metadata helpers",
            "does not promote StructureEvents, identity, lookup, ResourceHandle, mutation, or return override",
            "does not copy ForPC, VerifyPinCode, AllowToggleActivation, SetVariant, CanSeat, pin codes, object refs, or structure identity",
        ],
    }


def build_structure_nonpin_copied_scalar_policy_slice(*, snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    paths, missing_targets = snapshot_paths_from_target_sets(snapshot_root, [STRUCTURE_NONPIN_COPIED_SCALAR_INPUT_TARGET_SET])
    if missing_targets:
        raise SystemExit("structure non-PIN copied-scalar policy manifest missing targets: " + ",".join(missing_targets))

    input_snapshots = []
    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    for index, path in enumerate(paths, start=1):
        source_snapshot = {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        payload = load_json_file("snapshot", path)
        targets = require_snapshot_payload(payload, path)
        for target_payload in targets:
            target_identity = target_payload.get("target")
            if not isinstance(target_identity, dict):
                raise SystemExit(f"snapshot missing target identity: {path}")
            target = target_name(target_identity)
            if target in seen_targets:
                raise SystemExit(f"duplicate structure non-PIN policy target: {target}")
            seen_targets.add(target)
            source_snapshot["target"] = target
            input_snapshots.append(source_snapshot)
            target_copied, target_redacted = require_structure_nonpin_copied_scalar_shape(
                target_payload,
                source_snapshot,
            )
            copied.extend(target_copied)
            redacted.extend(target_redacted)

    expected_targets = expand_ufunction_targets([STRUCTURE_NONPIN_COPIED_SCALAR_INPUT_TARGET_SET])
    emitted_copied_fields = [entry["copied_field"] for entry in copied]
    emitted_redacted_fields = [entry["redacted_field"] for entry in redacted]
    missing_input_targets = [target for target in expected_targets if target not in seen_targets]
    unexpected_input_targets = [target for target in seen_targets if target not in expected_targets]
    missing_copied_fields = [field for field in STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS if field not in emitted_copied_fields]
    unexpected_copied_fields = [field for field in emitted_copied_fields if field not in STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS]
    missing_redacted_fields = [
        field for field in STRUCTURE_NONPIN_REDACTED_FIELD_REASONS if field not in emitted_redacted_fields
    ]
    unexpected_redacted_fields = [
        field for field in emitted_redacted_fields if field not in STRUCTURE_NONPIN_REDACTED_FIELD_REASONS
    ]
    blockers = [
        *[f"missing_input_target:{target}" for target in missing_input_targets],
        *[f"unexpected_input_target:{target}" for target in unexpected_input_targets],
        *[f"missing_copied_field:{field}" for field in missing_copied_fields],
        *[f"unexpected_copied_field:{field}" for field in unexpected_copied_fields],
        *[f"missing_redacted_field:{field}" for field in missing_redacted_fields],
        *[f"unexpected_redacted_field:{field}" for field in unexpected_redacted_fields],
    ]
    if blockers:
        raise SystemExit("structure non-PIN copied-scalar policy slice failed closed: " + ",".join(blockers))

    return {
        "schema": STRUCTURE_NONPIN_COPIED_SCALAR_POLICY_SCHEMA,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "snapshot_root": "redacted",
        "input_target_set": STRUCTURE_NONPIN_COPIED_SCALAR_INPUT_TARGET_SET,
        "output_target_set": STRUCTURE_NONPIN_COPIED_SCALAR_OUTPUT_TARGET_SET,
        "policy_status": "evidence-only",
        "missing_targets": [],
        "coverage": {
            "status": "complete",
            "input_targets": expected_targets,
            "copied_targets": expected_targets,
            "copied_fields": list(STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS),
            "redacted_fields": list(STRUCTURE_NONPIN_REDACTED_FIELD_REASONS),
        },
        "copied_scalars": copied,
        "redacted_structure_fields": redacted,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "promotion_ready": False,
            "intended_use": "offline_review_only",
            "copied_scalar_count": len(copied),
            "redacted_field_count": len(redacted),
            "explicitly_excluded": [
                "ForPC",
                "VerifyPinCode",
                "forCharacter",
                "identity",
                "lookup",
                "mutation",
                "object_refs",
                "pinCode",
                "public_sdk",
                "resource_handle",
                "return_override",
            ],
        },
        "non_claims": [
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
            "does not promote public SDK callbacks or public metadata helpers",
            "does not promote StructureEvents, identity, lookup, ResourceHandle, mutation, or return override",
            "does not copy ForPC, forCharacter, VerifyPinCode, pin codes, object refs, or structure identity",
        ],
    }


def require_structure_aggregate_pin_exclusions(
    target_payload: dict[str, Any],
    source_snapshot: dict[str, str],
) -> list[dict[str, Any]]:
    target_identity = target_payload.get("target")
    property_chain = target_payload.get("property_chain")
    if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
        raise SystemExit("structure aggregate policy snapshot missing target identity or property chain")
    target = target_name(target_identity)
    if target != "PrimalStructureItemContainer.VerifyPinCode":
        return []

    expected = STRUCTURE_RETURN_ONLY_EXPECTED_SHAPES[target]
    return_value_offset = require_int_field(target_payload, "return_value_offset", target)
    properties = property_chain.get("properties")
    if not isinstance(properties, list):
        raise SystemExit(f"{target} property_chain.properties is not a list")

    excluded: list[dict[str, Any]] = []
    for prop, (expected_name, expected_class) in zip(properties, expected["properties"], strict=True):
        if not isinstance(prop, dict):
            raise SystemExit(f"{target} property entry is not an object")
        name = prop.get("name")
        class_name = prop.get("class_name")
        if name != expected_name or class_name != expected_class:
            raise SystemExit(f"{target} PIN property shape drifted: expected {expected_name}:{expected_class}")
        field_key = f"{target}.{expected_name}"
        if field_key not in STRUCTURE_AGGREGATE_EXCLUDED_PIN_FIELDS:
            raise SystemExit(f"{field_key} has no structure aggregate PIN exclusion policy")
        field = classify_property(prop, return_value_offset)
        common = {
            "target": target,
            "field": expected_name,
            "excluded_field": field_key,
            "offset": format_hex(require_int_field(prop, "offset_internal", field_key)),
            "offset_internal": require_int_field(prop, "offset_internal", field_key),
            "element_size": require_int_field(prop, "element_size", field_key),
            "array_dim": require_int_field(prop, "array_dim", field_key),
            "property_flags": format_hex(property_flags(prop) or 0),
            "property_class": expected_class,
            "function_flags": format_hex(require_int_field(target_payload, "function_flags", target)),
            "num_parms": require_int_field(target_payload, "num_parms", target),
            "parms_size": require_int_field(target_payload, "parms_size", target),
            "return_value_offset": format_hex(return_value_offset),
            "source_snapshot": source_snapshot["id"],
            "source_snapshot_sha256": source_snapshot["sha256"],
            "evidence_status": "explicitly-excluded-pin-code-field",
        }
        if expected_name == "pinCode":
            if expected_class != "IntProperty" or field["direction"] != "in" or common["element_size"] != 4:
                raise SystemExit(f"{field_key} PIN scalar exclusion shape drifted")
            excluded.append(
                {
                    **common,
                    "direction": "in",
                    "type": "int32",
                    "reason": "pin_code_value_excluded",
                }
            )
        else:
            bool_field_size, bool_byte_offset = require_bool_tail(prop, field_key)
            masks = field.get("bool_masks")
            if (
                field["type"] != "bool"
                or field["direction"] != "return"
                or bool_field_size != 1
                or bool_byte_offset != 0
                or not isinstance(masks, dict)
                or masks.get("byte_mask") != "0x01"
                or masks.get("field_mask") != "0xff"
                or prop.get("native_bool") is not False
            ):
                raise SystemExit(f"{field_key} PIN return exclusion shape drifted")
            excluded.append(
                {
                    **common,
                    "direction": "return",
                    "type": "bool",
                    "bool_field_size": bool_field_size,
                    "bool_byte_offset": bool_byte_offset,
                    "byte_mask": masks["byte_mask"],
                    "field_mask": masks["field_mask"],
                    "native_bool": False,
                    "reason": "pin_code_return_value_excluded",
                }
            )
    return excluded


def build_structure_aggregate_census_policy_slice(*, snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    paths, missing_targets = snapshot_paths_from_target_sets(snapshot_root, [STRUCTURE_AGGREGATE_CENSUS_INPUT_TARGET_SET])
    if missing_targets:
        raise SystemExit("structure aggregate census policy manifest missing targets: " + ",".join(missing_targets))

    input_snapshots: list[dict[str, str]] = []
    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    excluded_pin_fields: list[dict[str, Any]] = []
    property_class_histogram: Counter[str] = Counter()
    seen_targets: set[str] = set()
    for index, path in enumerate(paths, start=1):
        source_snapshot = {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        payload = load_json_file("snapshot", path)
        targets = require_snapshot_payload(payload, path)
        for target_payload in targets:
            target_identity = target_payload.get("target")
            property_chain = target_payload.get("property_chain")
            if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
                raise SystemExit(f"snapshot missing structure aggregate target identity or property chain: {path}")
            target = target_name(target_identity)
            if target in seen_targets:
                raise SystemExit(f"duplicate structure aggregate policy target: {target}")
            seen_targets.add(target)
            source_snapshot["target"] = target
            input_snapshots.append(source_snapshot)

            properties = property_chain.get("properties")
            if not isinstance(properties, list):
                raise SystemExit(f"{target} property_chain.properties is not a list")
            property_class_histogram.update(
                prop.get("class_name")
                for prop in properties
                if isinstance(prop, dict) and isinstance(prop.get("class_name"), str)
            )

            target_copied, target_redacted, _ = require_structure_return_only_shape(target_payload, source_snapshot)
            copied.extend(target_copied)
            redacted.extend(target_redacted)
            if target in {
                "PrimalStructure.SetVariant",
                "PrimalStructureItemContainer.AllowToggleActivation",
                "PrimalStructureSeating.CanSeat",
            }:
                target_copied, target_redacted = require_structure_nonpin_copied_scalar_shape(
                    target_payload,
                    source_snapshot,
                )
                copied.extend(target_copied)
                redacted.extend(target_redacted)
            excluded_pin_fields.extend(require_structure_aggregate_pin_exclusions(target_payload, source_snapshot))

    expected_input_targets = expand_ufunction_targets([STRUCTURE_AGGREGATE_CENSUS_INPUT_TARGET_SET])
    expected_copied_fields = (*STRUCTURE_RETURN_ONLY_COPIED_FIELDS, *STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS)
    expected_redacted_fields = (
        *STRUCTURE_RETURN_ONLY_REDACTED_FIELD_REASONS,
        *STRUCTURE_NONPIN_REDACTED_FIELD_REASONS,
    )
    emitted_copied_fields = [entry["copied_field"] for entry in copied]
    emitted_redacted_fields = [entry["redacted_field"] for entry in redacted]
    emitted_excluded_pin_fields = [entry["excluded_field"] for entry in excluded_pin_fields]
    blockers = [
        *[f"missing_input_target:{target}" for target in expected_input_targets if target not in seen_targets],
        *[f"unexpected_input_target:{target}" for target in seen_targets if target not in expected_input_targets],
        *[f"missing_copied_field:{field}" for field in expected_copied_fields if field not in emitted_copied_fields],
        *[f"unexpected_copied_field:{field}" for field in emitted_copied_fields if field not in expected_copied_fields],
        *[f"missing_redacted_field:{field}" for field in expected_redacted_fields if field not in emitted_redacted_fields],
        *[f"unexpected_redacted_field:{field}" for field in emitted_redacted_fields if field not in expected_redacted_fields],
        *[
            f"missing_excluded_pin_field:{field}"
            for field in STRUCTURE_AGGREGATE_EXCLUDED_PIN_FIELDS
            if field not in emitted_excluded_pin_fields
        ],
        *[
            f"unexpected_excluded_pin_field:{field}"
            for field in emitted_excluded_pin_fields
            if field not in STRUCTURE_AGGREGATE_EXCLUDED_PIN_FIELDS
        ],
    ]
    if blockers:
        raise SystemExit("structure aggregate census policy slice failed closed: " + ",".join(blockers))

    copied_direction_histogram = Counter(entry["direction"] for entry in copied)
    copied_type_histogram = Counter(entry["type"] for entry in copied)
    redaction_reason_histogram = Counter(entry["reason"] for entry in redacted)
    excluded_reason_histogram = Counter(entry["reason"] for entry in excluded_pin_fields)
    return {
        "schema": STRUCTURE_AGGREGATE_CENSUS_POLICY_SCHEMA,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "snapshot_root": "redacted",
        "input_target_set": STRUCTURE_AGGREGATE_CENSUS_INPUT_TARGET_SET,
        "output_target_set": STRUCTURE_AGGREGATE_CENSUS_OUTPUT_TARGET_SET,
        "policy_status": "evidence-only",
        "consume_only": True,
        "missing_targets": [],
        "coverage": {
            "status": "complete",
            "input_targets": expected_input_targets,
            "copied_fields_permitted": list(expected_copied_fields),
            "redacted_fields": list(expected_redacted_fields),
            "explicitly_excluded_fields": list(STRUCTURE_AGGREGATE_EXCLUDED_PIN_FIELDS),
        },
        "copied_fields_permitted": copied,
        "redacted_structure_fields": redacted,
        "explicitly_excluded_fields": excluded_pin_fields,
        "approved_counters": {
            "input_target_count": len(expected_input_targets),
            "property_count": sum(property_class_histogram.values()),
            "copied_field_count": len(copied),
            "copied_bool_count": copied_type_histogram["bool"],
            "copied_int32_count": copied_type_histogram["int32"],
            "redacted_field_count": len(redacted),
            "explicitly_excluded_field_count": len(excluded_pin_fields),
        },
        "approved_histograms": {
            "property_class": dict(sorted(property_class_histogram.items())),
            "copied_direction": dict(sorted(copied_direction_histogram.items())),
            "copied_type": dict(sorted(copied_type_histogram.items())),
            "redaction_reason": dict(sorted(redaction_reason_histogram.items())),
            "explicit_exclusion_reason": dict(sorted(excluded_reason_histogram.items())),
        },
        "safety_summary": {
            "artifact_status": "evidence_only",
            "promotion_ready": False,
            "intended_use": "offline_review_only",
            "consume_only": True,
            "copied_field_count": len(copied),
            "redacted_field_count": len(redacted),
            "explicitly_excluded_field_count": len(excluded_pin_fields),
            "explicitly_excluded": [
                "ForPC",
                "VerifyPinCode.pinCode",
                "VerifyPinCode.ReturnValue",
                "forCharacter",
                "identity",
                "lookup",
                "mutation",
                "object_refs",
                "pinCode",
                "public_sdk",
                "resource_handle",
                "return_override",
                "runtime",
            ],
        },
        "non_claims": [
            "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
            "does not promote public SDK callbacks or public metadata helpers",
            "does not promote runtime hook wiring, dispatcher wiring, StructureEvents, identity, lookup, ResourceHandle, mutation, or return override",
            "does not copy VerifyPinCode.pinCode or VerifyPinCode.ReturnValue",
        ],
    }


def player_identity_field_is_identity_like(prop: dict[str, Any]) -> bool:
    class_name = prop.get("class_name")
    name = prop.get("name")
    normalized_name = name.lower().replace("_", "") if isinstance(name, str) else ""
    if class_name in REDACTED_TYPE_BY_CLASS or class_name == "NameProperty":
        return True
    if normalized_name in SENSITIVE_SCALAR_NAMES:
        return True
    if normalized_name.endswith("id") or normalized_name.endswith("ids"):
        return True
    return any(fragment in normalized_name for fragment in IDENTITY_NAME_FRAGMENTS)


def forbidden_identity_coordinate_sources(prop: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    if any(key in prop for key in FORBIDDEN_IDENTITY_COORDINATE_KEYS):
        sources.append("fname_or_gobjects_indices")
    if prop.get("class_name") in REDACTED_TYPE_BY_CLASS or prop.get("class_name") == "NameProperty":
        sources.append("ue_pointer_or_borrowed_payload")
    sources.append("raw_process_event_params")
    return sorted(set(sources))


def player_identity_redaction_reason(prop: dict[str, Any]) -> str:
    class_name = prop.get("class_name")
    name = prop.get("name")
    normalized_name = name.lower().replace("_", "") if isinstance(name, str) else ""
    if class_name in {"ObjectProperty", "WeakObjectProperty", "LazyObjectProperty", "SoftObjectProperty", "InterfaceProperty"}:
        return "ue_object_identity_forced_redacted"
    if class_name in {"ArrayProperty", "MapProperty", "SetProperty"}:
        return "container_payload_identity_forced_redacted"
    if class_name in {"StrProperty", "TextProperty"}:
        return "text_identity_or_private_value_forced_redacted"
    if class_name in {"StructProperty"}:
        return "struct_payload_identity_forced_redacted"
    if class_name in {"ClassProperty", "SoftClassProperty"}:
        return "class_identity_forced_redacted"
    if class_name == "NameProperty":
        return "fname_identity_forced_redacted"
    if normalized_name in SENSITIVE_SCALAR_NAMES or normalized_name.endswith("id") or normalized_name.endswith("ids"):
        return "identity_like_scalar_forced_redacted"
    return "identity_context_field_forced_redacted"


def player_identity_lifecycle_anchor_role(target: str) -> str:
    if target == "ShooterPlayerController.ServerListPlayers":
        return "admin_player_listing_candidate_not_session_start"
    if target == "ShooterPlayerController.ServerKickPlayer":
        return "admin_player_kick_candidate_not_session_end"
    if target == "ShooterPlayerController.ServerSendChatMessage":
        return "chat_to_principal_boundary_non_claim"
    if target.startswith("MissionType."):
        return "mission_membership_candidate_not_identity_lifecycle"
    if "Tribe" in target:
        return "tribe_membership_candidate_not_identity_lifecycle"
    if "SpawnPointsForDownloadedCharacters" in target:
        return "transfer_spawn_candidate_not_identity_lifecycle"
    return "candidate_not_identity_lifecycle_anchor"


def target_policy_blockers(target: str, target_payload: dict[str, Any], property_count: int) -> list[str]:
    blockers = [
        *promotion_blockers_for_signature(target_payload, property_count),
        "accepted_session_start_anchor_missing",
        "accepted_session_end_anchor_missing",
        "principal_copy_policy_missing",
        "principal_invalidation_semantics_missing",
        "second_source_lifecycle_evidence_missing",
    ]
    if target == "ShooterPlayerController.ServerKickPlayer":
        blockers.append("admin_mutation_surface_not_identity_lifecycle_anchor")
    if target == "ShooterPlayerController.ServerListPlayers":
        blockers.append("admin_listing_surface_not_identity_lifecycle_anchor")
    return sorted(set(blockers))


def player_identity_field_entry(
    *,
    target: str,
    target_payload: dict[str, Any],
    prop: dict[str, Any],
    source_snapshot: dict[str, str],
) -> dict[str, Any]:
    return_value_offset = target_payload.get("return_value_offset")
    field = classify_property(prop, return_value_offset)
    field_key = f"{target}.{field['name']}"
    identity_like = player_identity_field_is_identity_like(prop)
    copied_kind = scalar_summary_kind(field["type"])
    blockers = [
        *field.get("promotion_blockers", []),
        "public_identity_policy_missing",
        "runtime_lifecycle_cleanup_not_proven",
        "public_sdk_not_promoted",
    ]

    if identity_like:
        classification = "forced_redacted"
        evidence_status = "candidate-only-redacted"
        redaction_reason = player_identity_redaction_reason(prop)
        blockers.append("identity_like_field_forced_redacted")
    elif copied_kind is not None:
        classification = "copied_candidate"
        evidence_status = "copied-candidate-only"
        redaction_reason = "non_identity_scalar_candidate_not_public"
        blockers.append("candidate_scalar_not_public_identity")
    else:
        classification = "forbidden"
        evidence_status = "forbidden"
        redaction_reason = "unsupported_or_non_scalar_identity_surface_forbidden"
        blockers.append("field_forbidden_for_identity_evidence")

    entry = {
        "field": field_key,
        "target": target,
        "name": field["name"],
        "source_property_class": field["source_property_class"],
        "direction": field["direction"],
        "offset": field["offset"],
        "element_size": field["element_size"],
        "array_dim": field["array_dim"],
        "property_flags": field.get("property_flags"),
        "classification": classification,
        "redaction_reason": redaction_reason,
        "evidence_status": evidence_status,
        "source_snapshot": source_snapshot["id"],
        "source_snapshot_sha256": source_snapshot["sha256"],
        "blockers": sorted(set(blocker for blocker in blockers if isinstance(blocker, str))),
    }
    if "bool_masks" in field:
        entry["bool_masks"] = field["bool_masks"]
    return entry


def player_identity_forbidden_field(field_entry: dict[str, Any], prop: dict[str, Any]) -> dict[str, Any]:
    return {
        "forbidden_field": field_entry["field"],
        "target": field_entry["target"],
        "name": field_entry["name"],
        "source_property_class": field_entry["source_property_class"],
        "classification": "forbidden_identity_coordinate",
        "forbidden_sources": forbidden_identity_coordinate_sources(prop),
        "redaction_reason": "pointer_ue_coordinate_fname_gobjects_and_raw_param_identity_forbidden",
        "source_snapshot": field_entry["source_snapshot"],
        "source_snapshot_sha256": field_entry["source_snapshot_sha256"],
    }


def snapshot_artifact_identity(
    *,
    manifest: dict[str, Any],
    snapshot_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    ark_hashes = []
    obelisk_commits = []
    build_types = []
    source_artifact_ids = []

    manifest_ark_hash = manifest.get("ark_binary_sha256")
    if isinstance(manifest_ark_hash, str) and manifest_ark_hash:
        ark_hashes.append(manifest_ark_hash)
    manifest_source = manifest.get("source")
    if isinstance(manifest_source, str) and manifest_source:
        build_types.append(manifest_source)

    for payload in snapshot_payloads:
        evidence = payload.get("evidence")
        if not isinstance(evidence, dict):
            continue
        for key, sink in (
            ("ark_binary_sha256", ark_hashes),
            ("obelisk_commit", obelisk_commits),
            ("artifact_kind", build_types),
        ):
            value = evidence.get(key)
            if isinstance(value, str) and value:
                sink.append(value)
        for key in ("artifact_sha256", "capture_id", "evidence_pack_id"):
            value = evidence.get(key)
            if isinstance(value, str) and value:
                source_artifact_ids.append(f"{key}:{value}")

    ark_hash_values = unique_ordered(ark_hashes)
    obelisk_commit_values = unique_ordered(obelisk_commits)
    build_type_values = unique_ordered(build_types)
    return {
        "ark_binary_sha256": ark_hash_values[0] if len(ark_hash_values) == 1 else "mixed_or_unknown",
        "obelisk_commit": obelisk_commit_values[0] if len(obelisk_commit_values) == 1 else "mixed_or_unknown",
        "build_type": build_type_values[0] if len(build_type_values) == 1 else "mixed_or_unknown",
        "target_set_revision": "reflection_target_sets.py:players-identity-lifecycle-intake",
        "source_artifact_ids": unique_ordered(source_artifact_ids),
        "path_redacted": True,
    }


def build_players_identity_first_evidence(*, snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    paths, missing_targets = snapshot_paths_from_target_sets(
        snapshot_root,
        [PLAYERS_IDENTITY_FIRST_EVIDENCE_INPUT_TARGET_SET],
    )
    if missing_targets:
        blockers = [f"missing_required_target:{target}" for target in missing_targets]
        raise SystemExit("players identity first evidence failed closed: " + ",".join(blockers))

    required_missing = [target for target in PLAYERS_IDENTITY_REQUIRED_TARGETS if target not in expand_ufunction_targets([PLAYERS_IDENTITY_FIRST_EVIDENCE_INPUT_TARGET_SET])]
    if required_missing:
        raise SystemExit(
            "players identity first evidence failed closed: "
            + ",".join(f"target_set_missing_required_target:{target}" for target in required_missing)
        )

    manifest = load_manifest(snapshot_root)
    input_snapshots: list[dict[str, str]] = []
    snapshot_payloads: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    fields: list[dict[str, Any]] = []
    copied_candidates: list[dict[str, Any]] = []
    forced_redacted_fields: list[dict[str, Any]] = []
    forbidden_fields: list[dict[str, Any]] = []
    seen_targets: set[str] = set()

    for index, path in enumerate(paths, start=1):
        source_snapshot = {"id": f"snapshot-{index:04d}", "sha256": file_sha256(path)}
        payload = load_json_file("snapshot", path)
        snapshot_payloads.append(payload)
        for target_payload in require_snapshot_payload(payload, path):
            target_identity = target_payload.get("target")
            property_chain = target_payload.get("property_chain")
            if not isinstance(target_identity, dict) or not isinstance(property_chain, dict):
                raise SystemExit(f"snapshot missing player identity target identity or property chain: {path}")
            target = target_name(target_identity)
            if target in seen_targets:
                raise SystemExit(f"duplicate player identity target: {target}")
            seen_targets.add(target)
            source_snapshot["target"] = target
            input_snapshots.append(dict(source_snapshot))

            properties = property_chain.get("properties")
            if not isinstance(properties, list):
                raise SystemExit(f"{target} property_chain.properties is not a list")
            property_order = []
            target_field_blockers: list[str] = []
            for prop in properties:
                if not isinstance(prop, dict):
                    raise SystemExit(f"{target} property entry is not an object")
                name = prop.get("name")
                if not isinstance(name, str) or not name:
                    raise SystemExit(f"{target} property missing name")
                property_order.append(name)
                if prop.get("status") != "candidate":
                    target_field_blockers.append(f"{target}.{name}:property_status_not_candidate")
                    continue
                field_entry = player_identity_field_entry(
                    target=target,
                    target_payload=target_payload,
                    prop=prop,
                    source_snapshot=source_snapshot,
                )
                fields.append(field_entry)
                forbidden_fields.append(player_identity_forbidden_field(field_entry, prop))
                if field_entry["classification"] == "forced_redacted":
                    forced_redacted_fields.append(field_entry)
                elif field_entry["classification"] == "copied_candidate":
                    copied_candidates.append(field_entry)

            targets.append(
                {
                    "target": target,
                    "source_snapshot": source_snapshot["id"],
                    "source_snapshot_sha256": source_snapshot["sha256"],
                    "function_flags": target_payload.get("function_flags"),
                    "num_parms": target_payload.get("num_parms"),
                    "parms_size": target_payload.get("parms_size"),
                    "return_value_offset": target_payload.get("return_value_offset"),
                    "property_order": property_order,
                    "status": "candidate_only",
                    "lifecycle_anchor_role": player_identity_lifecycle_anchor_role(target),
                    "blockers": sorted(
                        set(
                            [
                                *target_policy_blockers(target, target_payload, len(properties)),
                                *target_field_blockers,
                            ]
                        )
                    ),
                }
            )

    expected_targets = expand_ufunction_targets([PLAYERS_IDENTITY_FIRST_EVIDENCE_INPUT_TARGET_SET])
    for required in PLAYERS_IDENTITY_REQUIRED_TARGETS:
        if required not in seen_targets:
            raise SystemExit(f"players identity first evidence failed closed: missing_required_target:{required}")
    coverage = target_set_coverage(
        manifest_target_sets=[PLAYERS_IDENTITY_FIRST_EVIDENCE_INPUT_TARGET_SET],
        source_target_sets=[],
        emitted_targets=[entry["target"] for entry in targets],
    )

    blocker_count = sum(len(entry["blockers"]) for entry in targets) + sum(len(entry["blockers"]) for entry in fields)
    lifecycle_blockers = [
        "no accepted session-start/login/connect UFunction anchor in players-identity-lifecycle-intake",
        "no accepted session-end/logout/disconnect UFunction anchor in players-identity-lifecycle-intake",
        "ServerListPlayers and ServerKickPlayer are admin surfaces, not accepted lifecycle anchors",
        "second-source lifecycle comparison is missing",
        "principal invalidation semantics are missing",
    ]
    return {
        "schema": PLAYERS_IDENTITY_FIRST_EVIDENCE_SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "snapshot_root": "redacted",
        "input_target_set": PLAYERS_IDENTITY_FIRST_EVIDENCE_INPUT_TARGET_SET,
        "generated_from": {
            "snapshot_schema": SUPPORTED_SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "target_set_coverage": coverage,
        "artifact_identity": snapshot_artifact_identity(manifest=manifest, snapshot_payloads=snapshot_payloads),
        "targets": targets,
        "fields": fields,
        "copied_candidates": copied_candidates,
        "forced_redacted_fields": forced_redacted_fields,
        "forbidden_fields": forbidden_fields,
        "lifecycle_anchors": {
            "session_start_accepted": False,
            "session_end_accepted": False,
            "accepted_start_targets": [],
            "accepted_end_targets": [],
            "blockers": lifecycle_blockers,
        },
        "privacy_policy": {
            "public_principal_ready": False,
            "copied_public_identifier": None,
            "persistent_identifier_ready": False,
            "process_local_identifier_ready": False,
            "storage_ready": False,
            "logging_policy": "identity_values_not_logged",
        },
        "promotion_gate": {
            "ready": False,
            "ready_scope": "planning_only",
            "promotion_ready": False,
            "blockers": [
                *lifecycle_blockers,
                "identity-like fields are force-redacted",
                "forbidden FName/GObjects/UE pointer/raw-param coordinates are not public identity",
                "no public API, ABI, dispatcher, runtime hook, lookup, persistence, mutation, or return override is promoted",
            ],
        },
        "safety_summary": {
            "target_count": len(targets),
            "expected_target_count": len(expected_targets),
            "missing_target_count": 0,
            "field_count": len(fields),
            "copied_candidate_count": len(copied_candidates),
            "forced_redacted_count": len(forced_redacted_fields),
            "forbidden_count": len(forbidden_fields),
            "blocker_count": blocker_count + len(lifecycle_blockers),
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": [
                "public_api",
                "public_sdk",
                "runtime_hook_wiring",
                "dispatcher_wiring",
                "commands",
                "permissions",
                "economy",
                "player_identity",
                "persistent_identity",
                "process_local_identity",
                "lookup",
                "ResourceHandle",
                "mutation",
                "return_override",
                "raw_params",
                "ue_pointers",
                "fname_indices",
                "gobjects_indices",
                "identity_value_logging",
            ],
        },
        "non_claims": [
            "candidate-only planning evidence for players-identity-lifecycle-intake",
            "does not accept ServerListPlayers or ServerKickPlayer as login/logout lifecycle anchors",
            "does not expose copied public player identity, process-local identity, persistent identity, sender identity, permissions, commands, economy, or moderation APIs",
            "does not expose UE pointers, raw params, FName/GObjects indices, object identity, lookup, ResourceHandle, mutation, or return overrides",
            "copied chat text remains unauthenticated and does not establish a principal",
        ],
    }


def print_text(report: dict[str, Any]) -> None:
    if "signatures" not in report:
        print(f"{report.get('schema')} status={report.get('artifact_status') or report.get('policy_status')}")
        summary = report.get("safety_summary")
        if isinstance(summary, dict):
            for key in ("target_count", "field_count", "forced_redacted_count", "copied_candidate_count"):
                if key in summary:
                    print(f"  {key}={summary[key]}")
        return
    for signature in report["signatures"]:
        print(
            "{target} flags={function_flags} parms={num_parms} size={parms_size} ret={return_value_offset}".format(
                **signature
            )
        )
        for param in signature["params"]:
            flags = ",".join(param["property_flag_labels"])
            print(
                "  {direction} {name}: {type} offset={offset} size={element_size} array_dim={array_dim} flags={flags}".format(
                    flags=flags,
                    **param,
                )
            )
        for field in signature["blocked_properties"]:
            print(
                "  blocked {name} class={source_property_class} status={status} reason={reason}".format(
                    **field
                )
            )
    if report["missing_targets"]:
        print("missing targets:")
        for target in report["missing_targets"]:
            print(f"  {target}")


def main() -> int:
    args = parse_args()
    policy_modes = [
        args.item_return_only_policy_slice,
        args.transfer_baccept_only_policy_slice,
        args.mission_copied_bool_policy_slice,
        args.structure_return_only_policy_slice,
        args.structure_nonpin_copied_scalar_policy_slice,
        args.structure_aggregate_census_policy_slice,
        args.players_identity_first_evidence,
    ]
    if sum(1 for enabled in policy_modes if enabled) > 1:
        raise SystemExit("policy-slice modes cannot be combined")
    if args.item_return_only_policy_slice:
        if args.target_set or args.source_target_set or args.snapshot:
            raise SystemExit("--item-return-only-policy-slice cannot be combined with target-set or snapshot inputs")
        report = build_item_return_only_policy_slice(snapshot_root=args.snapshot_root)
    elif args.transfer_baccept_only_policy_slice:
        if args.target_set or args.source_target_set or args.snapshot:
            raise SystemExit("--transfer-baccept-only-policy-slice cannot be combined with target-set or snapshot inputs")
        report = build_transfer_baccept_only_policy_slice(snapshot_root=args.snapshot_root)
    elif args.mission_copied_bool_policy_slice:
        if args.target_set or args.source_target_set or args.snapshot:
            raise SystemExit("--mission-copied-bool-policy-slice cannot be combined with target-set or snapshot inputs")
        report = build_mission_copied_bool_policy_slice(snapshot_root=args.snapshot_root)
    elif args.structure_return_only_policy_slice:
        if args.target_set or args.source_target_set or args.snapshot:
            raise SystemExit("--structure-return-only-policy-slice cannot be combined with target-set or snapshot inputs")
        report = build_structure_return_only_policy_slice(snapshot_root=args.snapshot_root)
    elif args.structure_nonpin_copied_scalar_policy_slice:
        if args.target_set or args.source_target_set or args.snapshot:
            raise SystemExit("--structure-nonpin-copied-scalar-policy-slice cannot be combined with target-set or snapshot inputs")
        report = build_structure_nonpin_copied_scalar_policy_slice(snapshot_root=args.snapshot_root)
    elif args.structure_aggregate_census_policy_slice:
        if args.target_set or args.source_target_set or args.snapshot:
            raise SystemExit("--structure-aggregate-census-policy-slice cannot be combined with target-set or snapshot inputs")
        report = build_structure_aggregate_census_policy_slice(snapshot_root=args.snapshot_root)
    elif args.players_identity_first_evidence:
        if args.target_set or args.source_target_set or args.snapshot:
            raise SystemExit("--players-identity-first-evidence cannot be combined with target-set or snapshot inputs")
        report = build_players_identity_first_evidence(snapshot_root=args.snapshot_root)
    else:
        report = build_report(
            snapshot_root=args.snapshot_root,
            target_sets=args.target_set,
            source_target_sets=args.source_target_set,
            snapshots=args.snapshot,
        )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 1 if report.get("missing_targets") else 0


if __name__ == "__main__":
    raise SystemExit(main())
