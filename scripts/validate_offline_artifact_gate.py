#!/usr/bin/env python3
"""Validate offline artifact paths, provenance sidecars, and promotion claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import SHA256_RE, SERVER_ROOT, sha256_file  # noqa: E402


SCHEMA = "obelisk.offline-artifact-gate-result.v1"
PROVENANCE_SCHEMA = "obelisk.offline-artifact-provenance.v1"
CORE_DUMP_EVIDENCE_PACK_SCHEMA = "obelisk.core-dump-evidence-pack.v1"
GOBJECTS_TWO_CORE_MANIFEST_SCHEMA = "obelisk.gobjects-two-core-manifest.v1"
REDACTED_UFUNCTION_SIGNATURE_SCHEMA = "obelisk.redacted-ufunction-signatures.v1"
REDACTED_SCRIPTSTRUCT_SIGNATURE_SCHEMA = "obelisk.redacted-scriptstruct-signatures.v1"
SCRIPTSTRUCT_INVENTORY_PACK_SCHEMA = "obelisk.scriptstruct-inventory-pack.v1"
TARGET_SET_COVERAGE_SCHEMA = "obelisk.redacted-ufunction-target-set-coverage.v1"
REDACTED_UFUNCTION_ARTIFACT_HYGIENE_SCHEMA = "obelisk.redacted-ufunction-artifact-hygiene.v1"
RC_UFUNCTION_SECOND_SOURCE_ROOT_SCHEMA = "obelisk.rc-ufunction-second-source-root-manifest.v1"
RC_UFUNCTION_SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
WEAK_HELPER_CALLER_MODE_SCHEMA = "obelisk.weak-helper-caller-mode-redacted.v1"
STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA = "obelisk.static-global-promotion-evidence.v1"
RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA = "obelisk.resource-handle-revalidation-evaluator.v1"
RESOURCE_HANDLE_SERIAL_SCAN_SCHEMA = "obelisk.resource-handle-serial-scan.v1"
RESOURCE_HANDLE_SERIAL_SCAN_PROVENANCE_SCHEMA = "obelisk.resource-handle-serial-scan.v1.provenance.v1"
RESOURCE_HANDLE_SERIAL_SCAN_CONSUME_GATE_SCHEMA = "obelisk.resource-handle-serial-scan.v1.consume-gate-expectation.v1"
READINESS_REPORT_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
UOBJECT_FLAG_POLICY_REPORT_SCHEMA = "obelisk.uobject-flag-policy-report.v1"
UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA = "obelisk.uobject-flag-transition-matrix.v1"
UOBJECT_FLAG_SAMPLE_REPORT_SCHEMA = "obelisk.uobject-flag-sample-report.v1"
UOBJECT_FLAG_SEMANTIC_CORRELATION_SCHEMA = "obelisk.uobject-flag-semantic-correlation.v1"
WEAK_HELPER_STATIC_POLARITY_REPORT_SCHEMA = "obelisk.weak-helper-static-polarity-report.v1"
WEAK_HELPER_POLARITY_CALLER_MODE_REPORT_SCHEMA = "obelisk.weak-helper-polarity-caller-mode-report.v1"
ITEM_RETURN_ONLY_POLICY_SLICE_SCHEMA = "obelisk.item-return-only-policy-slice.v1"
TRANSFER_BACCEPT_ONLY_POLICY_SLICE_SCHEMA = "obelisk.transfer-baccept-only-policy-slice.v1"
MISSION_COPIED_BOOL_POLICY_SLICE_SCHEMA = "obelisk.mission-copied-bool-policy-slice.v1"
STRUCTURE_RETURN_ONLY_POLICY_SLICE_SCHEMA = "obelisk.structure-return-only-policy-slice.v1"
STRUCTURE_NONPIN_COPIED_SCALAR_POLICY_SLICE_SCHEMA = "obelisk.structure-nonpin-copied-scalar-policy-slice.v1"
SUPPORTED_MANIFEST_SCHEMAS = {
    CORE_DUMP_EVIDENCE_PACK_SCHEMA,
    GOBJECTS_TWO_CORE_MANIFEST_SCHEMA,
    REDACTED_UFUNCTION_SIGNATURE_SCHEMA,
    REDACTED_SCRIPTSTRUCT_SIGNATURE_SCHEMA,
    SCRIPTSTRUCT_INVENTORY_PACK_SCHEMA,
    RC_UFUNCTION_SECOND_SOURCE_ROOT_SCHEMA,
    WEAK_HELPER_CALLER_MODE_SCHEMA,
    STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
    RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
    RESOURCE_HANDLE_SERIAL_SCAN_SCHEMA,
    READINESS_REPORT_SCHEMA,
    UOBJECT_FLAG_POLICY_REPORT_SCHEMA,
    UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA,
    UOBJECT_FLAG_SAMPLE_REPORT_SCHEMA,
    UOBJECT_FLAG_SEMANTIC_CORRELATION_SCHEMA,
    WEAK_HELPER_STATIC_POLARITY_REPORT_SCHEMA,
    WEAK_HELPER_POLARITY_CALLER_MODE_REPORT_SCHEMA,
    ITEM_RETURN_ONLY_POLICY_SLICE_SCHEMA,
    TRANSFER_BACCEPT_ONLY_POLICY_SLICE_SCHEMA,
    MISSION_COPIED_BOOL_POLICY_SLICE_SCHEMA,
    STRUCTURE_RETURN_ONLY_POLICY_SLICE_SCHEMA,
    STRUCTURE_NONPIN_COPIED_SCALAR_POLICY_SLICE_SCHEMA,
}
UOBJECT_FLAG_TRANSITION_PROVENANCE_SCHEMAS = {
    "obelisk.offline-artifact-provenance.v1",
    "obelisk.static-artifact-provenance.v1",
}
WEAK_HELPER_STATIC_POLARITY_PROVENANCE_SCHEMAS = UOBJECT_FLAG_TRANSITION_PROVENANCE_SCHEMAS | {
    "obelisk.weak-helper-bundled-artifact-provenance.v1",
}
WEAK_HELPER_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
DEFAULT_WORKSPACE_ROOT = Path("/servidor/ark/workspace-offline")
PATH_KEY_RE = re.compile(r"(?:^|_)(path|file|source|artifact|binary|core|stdout|stderr|copied_to)$")
SEMANTIC_INPUT_NAME_MAX_LENGTH = 128
REQUIRED_REDACTED_SIGNATURE_NON_PROMOTED_SURFACES = {
    "class_identity",
    "cross_binary_portability",
    "lookup",
    "mutation",
    "object_identity",
    "public_sdk",
    "resource_handle",
    "return_override",
}
READY_OVERCLAIM_KEYS = {
    "cross_binary_portability_ready",
    "lookup_ready",
    "mutation_ready",
    "promote_ready",
    "promotion_ready",
    "public_resource_handle_ready",
    "post_callback_resource_handle_ready",
    "resource_handle_ready",
    "return_override_ready",
    "runtime_ready",
}
RC_UFUNCTION_TARGET_SETS = (
    "minimal-second-source-intake",
    "structure-observer-intake",
    "chat-message-intake",
)
REQUIRED_RC_UFUNCTION_NON_CLAIMS = {
    "assembled root only; does not regenerate snapshots",
    "does not promote ResourceHandle, object identity, mutation, or return override",
}
REQUIRED_REDACTED_SIGNATURE_NON_CLAIMS = {
    "candidate-only redacted UFunction signature report",
    "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
    "does not promote public SDK callbacks or public metadata helpers",
}
REQUIRED_REDACTED_SCRIPTSTRUCT_NON_CLAIMS = {
    "candidate-only ScriptStruct layout summary",
    "does not promote public ScriptStruct or Transfer SDK callbacks",
    "does not decode transfer payloads or expose UE pointers, identity, raw params, mutation, or return overrides",
}
REQUIRED_REDACTED_SCRIPTSTRUCT_NOT_PROMOTED_SURFACES = {
    "mutation",
    "object_identity",
    "public_scriptstruct_sdk",
    "raw_ue_params",
    "resource_handle",
    "return_override",
    "transfer_payload_decoding",
}
REQUIRED_SCRIPTSTRUCT_INVENTORY_NON_CLAIMS = {
    "Does not promote a public ScriptStruct SDK.",
    "Does not promote Inventory, Transfer, Items, or Resources SDK callbacks.",
    "Does not expose UObject pointers, raw UE params, FName/GObjects indices, object identity, lookup, or ResourceHandle.",
    "Does not authorize mutation, return override, ProcessEvent blocking, or UE call replay.",
}
REQUIRED_READINESS_NON_PROMOTED_SURFACES = {
    "class_identity",
    "cross_binary_portability",
    "inventory_identity",
    "item_identity",
    "lookup",
    "mutation",
    "object_identity",
    "public_sdk",
    "raw_params",
    "resource_handle",
    "return_override",
    "runtime_hooks",
}
REQUIRED_ITEM_RETURN_ONLY_COPIED_FIELDS = {
    "PrimalItem.AllowEquipItem.ReturnValue",
    "PrimalItem.CanRepair.ReturnValue",
    "PrimalItem.UseItemOntoItem.ReturnValue",
}
REQUIRED_ITEM_RETURN_ONLY_EXCLUDED_FIELDS = {
    "PrimalItem.AllowEquipItem.toInventory",
    "PrimalItem.CanRepair.bIgnoreInventoryRequirement",
    "PrimalItem.CraftBlueprint.bConsumeResources",
    "PrimalItem.UseItemOntoItem.DestinationItem",
    "PrimalItem.UseItemOntoItem.AdditionalData",
}
REQUIRED_ITEM_RETURN_ONLY_COPIED_TARGETS = {
    "PrimalItem.AllowEquipItem",
    "PrimalItem.CanRepair",
    "PrimalItem.UseItemOntoItem",
}
REQUIRED_ITEM_RETURN_ONLY_INPUT_TARGETS = REQUIRED_ITEM_RETURN_ONLY_COPIED_TARGETS | {
    "PrimalItem.CraftBlueprint",
}
REQUIRED_ITEM_RETURN_ONLY_NON_CLAIMS = {
    "does not promote public SDK callbacks or public metadata helpers",
    "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
}
REQUIRED_ITEM_RETURN_ONLY_EXPLICIT_EXCLUSIONS = {
    "CraftBlueprint",
    "CanRepair.bIgnoreInventoryRequirement",
    "CraftBlueprint.bConsumeResources",
    "toInventory",
    "DestinationItem",
    "AdditionalData",
    "object_refs",
    "mutation",
    "return_override",
    "public_sdk",
}
REQUIRED_TRANSFER_BACCEPT_ONLY_COPIED_FIELD = "ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept"
REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET = "ShooterPlayerController.ServerTransferredPlayerConfirmationResult"
REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS = {
    "PrimalDinoCharacter.IsAllowedToTransfer.ReturnValue",
    "PrimalDinoCharacter.IsAllowedToTransfer.WorldContextObject",
    "ShooterGameState.AllowDownloadDino.ReturnValue",
    "ShooterGameState.AllowDownloadDino.TheDinoClass",
    "ShooterPlayerController.ServerDownloadTransferredPlayer.SpawnPointID",
    "ShooterPlayerController.ServerDownloadTransferredPlayer.spawnPointRegionIndex",
    "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.IgnoreBedID",
    "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.PlayerDataID",
    "ShooterPlayerController.ServerUploadCurrentCharacterAndItems.InventoryComp",
    "ShooterPlayerController.ServerUploadDino.DownloadedDino",
}
REQUIRED_TRANSFER_BACCEPT_ONLY_INPUT_TARGETS = {
    REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET,
    "PrimalDinoCharacter.IsAllowedToTransfer",
    "ShooterGameState.AllowDownloadDino",
    "ShooterPlayerController.ServerDownloadTransferredPlayer",
    "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters",
    "ShooterPlayerController.ServerUploadCurrentCharacterAndItems",
    "ShooterPlayerController.ServerUploadDino",
}
REQUIRED_TRANSFER_BACCEPT_ONLY_NON_CLAIMS = {
    "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
    "does not promote public SDK callbacks or public metadata helpers",
    "does not promote runtime hook wiring, dispatcher wiring, transfer payload decoding, or public Transfer SDK",
}
REQUIRED_TRANSFER_BACCEPT_ONLY_EXPLICIT_EXCLUSIONS = {
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
}
REQUIRED_MISSION_COPIED_BOOL_FIELDS = {
    "MissionType.AddPlayerToMission.ReturnValue",
    "MissionType.AddPlayerToMission.bForceAdd",
    "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
    "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
    "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
}
REQUIRED_MISSION_COPIED_BOOL_REDACTED_FIELDS = {
    "MissionType.AddPlayerToMission.PlayerCharacter",
    "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn",
    "MissionType.BPOnPlayerRemovedFromMission.Controller",
    "MissionType.BPOnPlayerRemovedFromMission.Player",
    "MissionType.GetPlayerUsableItems.Character",
    "MissionType.GetPlayerUsableItems.OutItemIDs",
}
REQUIRED_MISSION_COPIED_BOOL_INPUT_TARGETS = {
    "MissionType.AddPlayerToMission",
    "MissionType.BPAllowPlayerToLeaveMission",
    "MissionType.BPOnPlayerRemovedFromMission",
    "MissionType.GetPlayerUsableItems",
}
REQUIRED_MISSION_COPIED_BOOL_COPIED_TARGETS = {
    "MissionType.AddPlayerToMission",
    "MissionType.BPAllowPlayerToLeaveMission",
    "MissionType.BPOnPlayerRemovedFromMission",
}
REQUIRED_MISSION_COPIED_BOOL_NON_CLAIMS = {
    "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
    "does not promote public SDK callbacks or public metadata helpers",
    "does not promote runtime hook wiring, dispatcher wiring, mission payload decoding, or public Mission SDK",
    "does not copy player/controller/character object refs, OutItemIDs arrays, mission identity, player identity, or ResourceHandle",
}
REQUIRED_MISSION_COPIED_BOOL_EXPLICIT_EXCLUSIONS = {
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
}
REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_FIELDS = {
    "PrimalStructure.AllowStructureAccess.ReturnValue",
    "PrimalStructure.IsAllowedToDemolish.ReturnValue",
}
REQUIRED_STRUCTURE_RETURN_ONLY_REDACTED_FIELDS = {
    "PrimalStructure.AllowStructureAccess.ForPC",
    "PrimalStructure.IsAllowedToDemolish.ForPC",
}
REQUIRED_STRUCTURE_RETURN_ONLY_INPUT_TARGETS = {
    "PrimalStructure.AllowStructureAccess",
    "PrimalStructure.IsAllowedToDemolish",
    "PrimalStructure.SetVariant",
    "PrimalStructureItemContainer.AllowToggleActivation",
    "PrimalStructureItemContainer.VerifyPinCode",
    "PrimalStructureSeating.CanSeat",
}
REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_TARGETS = {
    "PrimalStructure.AllowStructureAccess",
    "PrimalStructure.IsAllowedToDemolish",
}
REQUIRED_STRUCTURE_RETURN_ONLY_DEFERRED_TARGETS = {
    "PrimalStructure.SetVariant",
    "PrimalStructureItemContainer.AllowToggleActivation",
    "PrimalStructureItemContainer.VerifyPinCode",
    "PrimalStructureSeating.CanSeat",
}
REQUIRED_STRUCTURE_RETURN_ONLY_NON_CLAIMS = {
    "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
    "does not promote public SDK callbacks or public metadata helpers",
    "does not promote StructureEvents, identity, lookup, ResourceHandle, mutation, or return override",
    "does not copy ForPC, VerifyPinCode, AllowToggleActivation, SetVariant, CanSeat, pin codes, object refs, or structure identity",
}
REQUIRED_STRUCTURE_RETURN_ONLY_EXPLICIT_EXCLUSIONS = {
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
}
REQUIRED_STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS = {
    "PrimalStructure.SetVariant.VariantIndex",
    "PrimalStructure.SetVariant.bForceSet",
    "PrimalStructure.SetVariant.ReturnValue",
    "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue",
    "PrimalStructureSeating.CanSeat.bForce",
    "PrimalStructureSeating.CanSeat.ReturnValue",
}
REQUIRED_STRUCTURE_NONPIN_REDACTED_FIELDS = {
    "PrimalStructureItemContainer.AllowToggleActivation.ForPC",
    "PrimalStructureSeating.CanSeat.ForPC",
    "PrimalStructureSeating.CanSeat.forCharacter",
}
REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS = {
    "PrimalStructure.SetVariant",
    "PrimalStructureItemContainer.AllowToggleActivation",
    "PrimalStructureSeating.CanSeat",
}
REQUIRED_STRUCTURE_NONPIN_NON_CLAIMS = {
    "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
    "does not promote public SDK callbacks or public metadata helpers",
    "does not promote StructureEvents, identity, lookup, ResourceHandle, mutation, or return override",
    "does not copy ForPC, forCharacter, VerifyPinCode, pin codes, object refs, or structure identity",
}
REQUIRED_STRUCTURE_NONPIN_EXPLICIT_EXCLUSIONS = {
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
}
REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS = {
    "weak_helper_reject_0x100",
    "strict_0x4000_behavior",
    "gobjects_backed_0x4000_skip",
    "gc_static_0x100_support",
}
REQUIRED_UOBJECT_FLAG_POLICY_WINDOW_PATTERNS = {
    "weak_helper_reject_0x100": {
        "gobjects_count_ref",
        "gobjects_chunk_ref",
        "uobject_flags_load",
        "mask_0x100",
        "null_return_branch",
    },
    "strict_0x4000_behavior": {
        "strict_mode_guard",
        "mask_0x4000",
        "null_return_branch",
    },
    "gobjects_backed_0x4000_skip": {
        "gobjects_count_ref",
        "gobjects_chunk_ref",
        "fuobjectitem_load",
        "uobject_load",
        "mask_0x4000",
        "skip_branch",
    },
    "gc_static_0x100_support": {
        "gc_window_start",
        "gobjects_count_ref",
        "gobjects_chunk_ref",
        "fuobjectitem_iteration",
        "uobject_load",
        "set_0x100",
    },
}
REQUIRED_UOBJECT_FLAG_POLICY_BLOCKERS = {
    "static_only_evidence",
    "no_rejected_runtime_object_samples",
    "no_named_lifecycle_semantics",
    "public_resourcehandle_policy_missing",
    "post_callback_lifetime_policy_unproven",
}
REQUIRED_UOBJECT_FLAG_POLICY_NON_CLAIMS = {
    "does_not_promote_resourcehandle",
    "does_not_promote_post_callback_lookup",
    "does_not_claim_mutation_or_return_override_safety",
    "does_not_assign_public_ue_lifecycle_flag_names",
    "does_not_prove_public_sdk_object_identity",
    "does_not_replace_rejected_runtime_object_samples",
}
UOBJECT_FLAG_POLICY_CALLER_ROWS_SUMMARY_KEYS = {
    "helper",
    "row_count",
    "unique_caller_hash_count",
    "mode_args",
    "return_use",
    "source_count",
    "evidence",
    "policy_observation",
    "claim_level",
    "lifecycle_names",
    "path_redacted",
    "caller_rows_sha256",
}
UOBJECT_FLAG_POLICY_CALLER_ROWS_SOURCE_KEYS = {
    "schema",
    "source_artifact_sha256",
    "binary_sha256",
    "caller_rows_sha256",
    "path_redacted",
}
UOBJECT_FLAG_POLICY_WEAK_HELPER_KEYS = {
    "schema",
    "artifact_sha256",
    "promotion_gate_ready",
    "direct_call_coverage",
    "flag_rules",
    "caller_rows_summary",
    "caller_rows_source",
}
UOBJECT_FLAG_POLICY_WEAK_HELPER_FLAG_RULES = [
    {"mask": "0x100", "result": "null_always"},
    {"mask": "0x4000", "result": "null_when_sil_zero"},
]
UOBJECT_FLAG_POLICY_PUBLIC_HELPER_ID = "weak_helper_flag_policy_candidate"
REQUIRED_UOBJECT_FLAG_POLICY_CANDIDATES = {
    "0x100": {
        "candidate": "hard_invalid_static_negative_equivalent",
        "support": {
            "weak_helper_flag_policy_candidate_null_always",
            "gc_static_0x100_support",
        },
    },
    "0x4000": {
        "candidate": "strict_invalid_static_negative_equivalent",
        "support": {
            "weak_helper_flag_policy_candidate_null_when_mode_zero",
            "strict_0x4000_behavior",
            "gobjects_backed_0x4000_skip",
        },
    },
}
UOBJECT_FLAG_POLICY_ALLOWED_HEX_STRINGS = {"0x100", "0x4000"}
STATIC_GLOBAL_CANDIDATE_KINDS = {"gobjects", "fname_root"}
STATIC_GLOBAL_GOBJECTS_FIELD_WINDOW_BLOCKER = "missing_gobjects_coherent_field_window"
STATIC_GLOBAL_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
UOBJECT_FLAG_POLICY_PUBLIC_FORBIDDEN_KEY_RE = re.compile(r"(?:^|_)(address|index|indices|serial|pointer|ptr)(?:_|$)", re.IGNORECASE)
UOBJECT_FLAG_POLICY_PUBLIC_FORBIDDEN_VALUE_RE = re.compile(r"(?:^|[_\W])(address|index|indices|serial|pointer|ptr)(?:[_\W]|$)", re.IGNORECASE)
UOBJECT_FLAG_POLICY_PUBLIC_ADDRESS_RE = re.compile(r"\b0x[0-9a-f]{5,}\b", re.IGNORECASE)
REQUIRED_UOBJECT_FLAG_POLICY_INTERNAL_REVALIDATION_CONTRACT = {
    "name": "InternalUObjectRevalidationCandidate",
    "lifetime": "frame_local_only",
    "post_callback_lookup": "rejected",
    "flag_policy": {
        "0x100": "reject",
        "0x4000": "reject_by_default",
    },
    "output": "copied_bool_or_obelisk_owned_data_only",
    "public_api": "not_promoted",
}
REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOWS = {
    "weak_publish_from_uobject_1d56970_1d56a30",
    "weak_validity_mode_a30_1d56a30_1d56ae0",
    "weak_validity_strict_ae0_1d56ae0_1d56b60",
    "weak_stale_mode_b60_1d56b60_1d56c00",
    "weak_lookup_strict_c00_1d56c00_1d56c70",
    "weak_lookup_allow4000_c70_1d56c70_1d56d00",
    "weak_lookup_raw_d00_1d56d00_1d56d60",
    "weak_refresh_from_object_d60_1d56d60_1d56ed0",
    "gc_mark_100_8000_1d18a90_1d18c70",
    "gobjects_4000_skip_mark_2982920_2982b60",
    "holder_4000_skip_mark_11ee120_11ee270",
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def static_global_safe_id(value: object) -> bool:
    return isinstance(value, str) and ".." not in value and "/" not in value and "\\" not in value and STATIC_GLOBAL_SAFE_ID_RE.fullmatch(value) is not None


def static_global_canonical_command_record(record: dict[str, Any]) -> dict[str, Any]:
    provenance = record.get("provenance")
    provenance_summary: dict[str, Any] = {}
    if isinstance(provenance, dict):
        for key in (
            "verified",
            "reason",
            "artifact_kind",
            "binary_sha256",
            "artifact_sha256",
            "source_artifact_sha256",
            "tool",
        ):
            if key in provenance:
                provenance_summary[key] = provenance[key]
    return {
        "source_sha256": record.get("source_sha256"),
        "copied_sha256": record.get("copied_sha256"),
        "stdout_sha256": record.get("stdout_sha256"),
        "returncode": record.get("returncode"),
        "provenance": provenance_summary,
    }


def static_global_sanitize_identity_value(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: static_global_sanitize_identity_value(child)
            for key, child in sorted(value.items())
            if key not in {"path", "source", "copied_to", "output_provenance"}
        }
    if isinstance(value, list):
        return [static_global_sanitize_identity_value(item) for item in value]
    return value


def static_global_canonical_report(payload: dict[str, Any]) -> dict[str, Any]:
    binary = payload.get("binary")
    commands = payload.get("commands")
    return {
        "schema": payload.get("schema"),
        "binary_sha256": binary.get("sha256") if isinstance(binary, dict) else None,
        "static_xrefs_sha256": payload.get("static_xrefs_sha256"),
        "commands": {
            name: static_global_canonical_command_record(record)
            for name, record in sorted((commands or {}).items())
            if isinstance(name, str) and isinstance(record, dict)
        }
        if isinstance(commands, dict)
        else {},
        "candidates": static_global_sanitize_identity_value(payload.get("candidates")),
        "promotion_gate": payload.get("promotion_gate"),
    }


def static_global_artifact_identity(payload: dict[str, Any], *, capture_id: str, evidence_pack_id: str) -> dict[str, str]:
    identity_without_hash = {
        "artifact_kind": STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": static_global_canonical_report(payload),
    }
    return {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(canonical_json_bytes(material)).hexdigest(),
    }
OPTIONAL_UOBJECT_FLAG_TRANSITION_WINDOWS = {
    "uobject_100_clear_1d637c8_1d63888",
    "uobject_4000_set_call_clear_251f970_251f986",
}
REQUIRED_UOBJECT_FLAG_TRANSITION_GROUPS = {
    "predicate_windows",
    "caller_mode_windows",
    "mutation_windows",
}
REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOW_PATTERNS = {
    "weak_publish_from_uobject_1d56970_1d56a30": {"uobject_plus_0x8_serial_or_flags_operand"},
    "weak_validity_mode_a30_1d56a30_1d56ae0": {
        "uobject_plus_0x8_operand",
        "tests_0x100",
        "mentions_0x4000_mode",
    },
    "weak_validity_strict_ae0_1d56ae0_1d56b60": {
        "uobject_plus_0x8_operand",
        "tests_0x100",
        "tests_0x4000",
        "preserves_null_edge_case",
    },
    "weak_stale_mode_b60_1d56b60_1d56c00": {
        "uobject_plus_0x8_operand",
        "tests_0x100",
        "mentions_0x4000_mode",
    },
    "weak_lookup_strict_c00_1d56c00_1d56c70": {
        "uobject_plus_0x8_operand",
        "tests_0x100",
        "tests_0x4000",
    },
    "weak_lookup_allow4000_c70_1d56c70_1d56d00": {
        "uobject_plus_0x8_operand",
        "tests_0x100",
        "mode_register_controls_0x4000",
    },
    "weak_lookup_raw_d00_1d56d00_1d56d60": {"gobjects_or_index_operand"},
    "weak_refresh_from_object_d60_1d56d60_1d56ed0": {
        "uobject_plus_0x8_operand",
        "tests_0x100",
    },
    "gc_mark_100_8000_1d18a90_1d18c70": {
        "uobject_plus_0x8_operand",
        "sets_or_tests_0x100",
        "sets_0x8000_register_then_store",
    },
    "gobjects_4000_skip_mark_2982920_2982b60": {
        "uobject_plus_0x8_operand",
        "tests_or_sets_0x4000",
    },
    "holder_4000_skip_mark_11ee120_11ee270": {
        "uobject_plus_0x8_operand",
        "tests_or_sets_0x4000",
    },
    "uobject_100_clear_1d637c8_1d63888": {
        "uobject_plus_0x8_operand",
        "clears_0x100_from_uobject_plus_0x8",
    },
    "uobject_4000_set_call_clear_251f970_251f986": {
        "uobject_plus_0x8_operand",
        "mentions_0x4000",
    },
}
REQUIRED_UOBJECT_FLAG_TRANSITION_BLOCKERS = {
    "static_objdump_windows_only",
    "no_runtime_object_samples",
    "no_second_source_lifecycle_semantics",
    "no_public_resource_handle_contract",
    "no_post_callback_lifetime_contract",
}
REQUIRED_UOBJECT_FLAG_TRANSITION_NON_CLAIMS = {
    "does_not_promote_runtime_offsets",
    "does_not_claim_resource_handle_identity",
    "does_not_claim_post_callback_object_lifetime",
    "does_not_assign_public_lifecycle_names",
    "does_not_claim_mutation_or_return_override_safety",
}
REQUIRED_UOBJECT_FLAG_SAMPLE_MASKS = {"0x100", "0x4000", "0x8000"}
REQUIRED_UOBJECT_FLAG_SAMPLE_KINDS = {
    "static_policy_candidate",
    "static_policy_and_transition_candidate",
    "static_transition_candidate",
}
REQUIRED_UOBJECT_FLAG_SAMPLE_BLOCKERS = {
    "static_only_evidence",
    "no_runtime_object_samples",
    "no_rejected_runtime_object_samples",
    "no_public_resource_handle_contract",
    "no_post_callback_lifetime_contract",
}
REQUIRED_RESOURCE_HANDLE_SERIAL_SCAN_NON_CLAIMS = {
    "internal offline scan only",
    "does not promote ResourceHandle, object identity, lookup, mutation, or return override",
}
REQUIRED_UOBJECT_FLAG_SAMPLE_NON_CLAIMS = {
    "does_not_promote_resourcehandle",
    "does_not_claim_post_callback_lookup",
    "does_not_assign_public_lifecycle_flag_names",
    "does_not_claim_mutation_or_return_override_safety",
}
FORBIDDEN_UOBJECT_FLAG_LIFECYCLE_STRINGS = {
    "pending-kill",
    "pending kill",
    "destroyed",
    "unreachable",
    "rf_taggarbagetemp",
    "taggarbagetemp",
    "garbage",
}
REQUIRED_UOBJECT_FLAG_SEMANTIC_BLOCKERS = {
    "no_version_matched_source_decompiler_correlation_for_public_lifecycle_names",
    "no_rejected_runtime_object_samples",
    "no_post_callback_lifetime_contract",
    "no_serial_reuse_or_wraparound_policy",
}
REQUIRED_UOBJECT_FLAG_SEMANTIC_NON_CLAIMS = {
    "does_not_unlock_resource_handle",
    "does_not_promote_gobjects_lookup",
    "does_not_promote_public_object_identity",
    "does_not_allow_mutation_or_return_override",
    "does_not_name_ue_lifecycle_flags_publicly",
}
REQUIRED_WEAK_HELPER_STATIC_POLARITY_BLOCKERS = {
    "static_only_evidence",
    "no_runtime_negative_samples",
    "no_second_source_lifecycle_semantics",
    "no_public_resource_handle_contract",
    "no_post_callback_lifetime_contract",
    "no_public_lifecycle_names",
    "no_lookup_contract",
    "no_mutation_contract",
    "no_return_override_contract",
}
REQUIRED_WEAK_HELPER_STATIC_POLARITY_NON_CLAIMS = {
    "does_not_unlock_resource_handle",
    "does_not_promote_post_callback_lookup",
    "does_not_assign_public_lifecycle_names",
    "does_not_claim_lookup_safety",
    "does_not_claim_mutation_or_return_override_safety",
}
REQUIRED_WEAK_HELPER_POLARITY_CALLER_MODE_BLOCKERS = {
    "no_runtime_negative_sample",
    "no_public_lifecycle_names",
    "no_post_callback_lookup_contract",
    "no_serial_reuse_policy",
    "no_promote_mode_artifact_gate_for_this_schema",
}
REQUIRED_WEAK_HELPER_POLARITY_CALLER_MODE_NON_CLAIMS = {
    "ResourceHandle",
    "public object lookup",
    "public object identity",
    "mutation",
    "return override",
    "UE lifecycle flag names",
}
REQUIRED_GOBJECTS_TWO_CORE_BLOCKED_CONTRACTS = {
    "runtime-stable object identity",
    "ResourceHandle",
    "raw UObject exposure",
    "lookup API",
    "mutation",
    "return override",
    "serial reuse/invalidation semantics",
}


def is_historical_missing_target_set_coverage_marker(payload: dict[str, Any]) -> bool:
    hygiene = payload.get("artifact_hygiene")
    if not isinstance(hygiene, dict):
        return False
    return (
        hygiene.get("schema") == REDACTED_UFUNCTION_ARTIFACT_HYGIENE_SCHEMA
        and hygiene.get("classification") == "historical"
        and hygiene.get("promotion_hygienic") is False
        and hygiene.get("consume_mode_allowed") is True
        and hygiene.get("reason") == "missing_target_set_coverage_pre_strict_gate"
    )


def parse_label_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--artifact must use LABEL=PATH")
    label, raw_path = value.split("=", 1)
    label = label.strip()
    if not label:
        raise argparse.ArgumentTypeError("--artifact label must not be empty")
    if not raw_path.strip():
        raise argparse.ArgumentTypeError("--artifact path must not be empty")
    return label, Path(raw_path)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def normalized_root(path: Path) -> Path:
    return path.expanduser().resolve()


def path_state(path: Path, *, workspace_root: Path, protected_root: Path) -> dict[str, Any]:
    expanded = path.expanduser()
    direct = expanded.absolute() if not expanded.is_absolute() else expanded
    resolved = expanded.resolve(strict=False)
    workspace = normalized_root(workspace_root)
    default_workspace = normalized_root(DEFAULT_WORKSPACE_ROOT)
    protected = normalized_root(protected_root)
    direct_under_workspace = expanded.is_absolute() and (
        is_relative_to(direct, workspace_root) or is_relative_to(direct, default_workspace)
    )
    resolved_under_workspace = is_relative_to(resolved, workspace) or is_relative_to(resolved, default_workspace)
    return {
        "path": str(path),
        "direct": str(direct),
        "resolved": str(resolved),
        "direct_under_workspace": direct_under_workspace,
        "resolved_under_workspace": resolved_under_workspace,
        "direct_under_protected": expanded.is_absolute() and is_relative_to(direct, protected_root),
        "resolved_under_protected": is_relative_to(resolved, protected),
    }


def path_blockers(path: Path, *, label: str, workspace_root: Path, protected_root: Path, require_workspace: bool) -> list[dict[str, Any]]:
    state = path_state(path, workspace_root=workspace_root, protected_root=protected_root)
    blockers: list[dict[str, Any]] = []
    if state["direct_under_protected"] and not state["direct_under_workspace"]:
        blockers.append({"reason": "path_text_under_protected_root", "label": label, **state})
    if state["resolved_under_protected"] and not state["resolved_under_workspace"]:
        blockers.append({"reason": "path_resolves_under_protected_root", "label": label, **state})
    if require_workspace and not state["direct_under_workspace"]:
        blockers.append({"reason": "path_not_textually_under_workspace_root", "label": label, **state})
    if require_workspace and not state["resolved_under_workspace"]:
        blockers.append({"reason": "path_not_resolved_under_workspace_root", "label": label, **state})
    return blockers


def is_json_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def sha256_file_or_blocker(path: Path, *, label: str, expected_sha256: str) -> list[dict[str, Any]]:
    try:
        actual_sha256 = sha256_file(path)
    except SystemExit as exc:
        return [{"reason": "resource_handle_serial_scan_core_path_unreadable", "label": label, "detail": str(exc)}]
    if actual_sha256 != expected_sha256:
        return [
            {
                "reason": "resource_handle_serial_scan_core_sha256_mismatch",
                "label": label,
                "expected_core_sha256": expected_sha256,
                "observed_core_sha256": actual_sha256,
            }
        ]
    return []


def key_names_path(key: object) -> bool:
    text = str(key).casefold()
    return bool(PATH_KEY_RE.search(text)) or text.endswith("_path") or text.endswith("_file")


def collect_path_fields(value: object, *, trail: str = "$", path_context: bool = False) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            child_path_context = key_names_path(key)
            if isinstance(child, str) and child_path_context:
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_path_fields(child, trail=child_trail, path_context=child_path_context))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_trail = f"{trail}[{index}]"
            if isinstance(child, str) and path_context:
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_path_fields(child, trail=child_trail, path_context=path_context))
    return found


def collect_string_fields(value: object, *, trail: str = "$") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if isinstance(child, str):
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_string_fields(child, trail=child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_trail = f"{trail}[{index}]"
            if isinstance(child, str):
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_string_fields(child, trail=child_trail))
    return found


def collect_key_names(value: object, *, trail: str = "$") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            found.append((child_trail, str(key)))
            if isinstance(child, (dict, list)):
                found.extend(collect_key_names(child, trail=child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.extend(collect_key_names(child, trail=f"{trail}[{index}]"))
    return found


def collect_bool_fields(value: object, *, trail: str = "$") -> list[tuple[str, bool]]:
    found: list[tuple[str, bool]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if isinstance(child, bool):
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_bool_fields(child, trail=child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.extend(collect_bool_fields(child, trail=f"{trail}[{index}]"))
    return found


def collect_ready_overclaims(value: object, *, trail: str = "$") -> list[tuple[str, bool]]:
    return [
        (child_trail, child)
        for child_trail, child in collect_bool_fields(value, trail=trail)
        if child is True and child_trail.rsplit(".", 1)[-1] in READY_OVERCLAIM_KEYS
    ]


def collect_candidate_public_overclaims(
    value: object,
    *,
    allowed_prefixes: tuple[str, ...] = (),
) -> list[tuple[str, str, str]]:
    forbidden = {
        "resourcehandle": "resourcehandle",
        "resource handle": "resource_handle",
        "public api": "public_api",
        "public sdk": "public_sdk",
        "item sdk": "public_sdk",
        "items sdk": "public_sdk",
        "mission sdk": "public_sdk",
        "missions sdk": "public_sdk",
        "transfer sdk": "public_sdk",
        "transfers sdk": "public_sdk",
        "lookup safe": "lookup_safe",
        "lookup ready": "lookup_ready",
        "post-callback lookup ready": "post_callback_lookup_ready",
        "post callback lookup ready": "post_callback_lookup_ready",
        "public object identity": "public_object_identity",
        "public callback": "public_callback",
        "runtime ready": "runtime_ready",
        "runtime promotion": "runtime_promotion",
        "runtime hook ready": "runtime_hook_ready",
    }
    found: list[tuple[str, str, str]] = []
    for trail, raw_value in collect_string_fields(value):
        if any(trail.startswith(prefix) for prefix in allowed_prefixes):
            continue
        text = raw_value.casefold()
        for needle, reason in forbidden.items():
            if needle in text:
                found.append((trail, raw_value, reason))
    return found


def is_safe_semantic_input_name(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if len(value) > SEMANTIC_INPUT_NAME_MAX_LENGTH:
        return False
    if value in {".", ".."}:
        return False
    if any(ord(char) < 32 for char in value):
        return False
    return "/" not in value and "\\" not in value and ":" not in value


def load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [{"reason": "malformed_json", "path": str(path), "detail": str(exc)}]
    except OSError as exc:
        return None, [{"reason": "unreadable_json", "path": str(path), "detail": str(exc)}]
    if not isinstance(payload, dict):
        return None, [{"reason": "json_not_object", "path": str(path), "recorded_type": type(payload).__name__}]
    return payload, []


def validate_json_path_fields(
    payload: dict[str, Any],
    *,
    source_label: str,
    workspace_root: Path,
    protected_root: Path,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for trail, raw_path in collect_path_fields(payload):
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            continue
        blockers.extend(
            path_blockers(
                candidate,
                label=f"{source_label}:{trail}",
                workspace_root=workspace_root,
                protected_root=protected_root,
                require_workspace=False,
            )
        )
    return blockers


def validate_json_protected_root_strings(
    payload: dict[str, Any],
    *,
    source_label: str,
    workspace_root: Path,
    protected_root: Path,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    protected_text = str(protected_root)
    workspace_texts = {str(workspace_root), str(DEFAULT_WORKSPACE_ROOT)}
    for trail, raw_value in collect_string_fields(payload):
        protected_offsets = [match.start() for match in re.finditer(re.escape(protected_text), raw_value)]
        if not protected_offsets:
            continue
        if all(any(raw_value.startswith(workspace_text, offset) for workspace_text in workspace_texts) for offset in protected_offsets):
            continue
        blockers.append(
            {
                "reason": "manifest_string_under_protected_root",
                "label": f"{source_label}:{trail}",
                "value": raw_value,
                "protected_root": protected_text,
                "workspace_root": str(workspace_root),
            }
        )
    return blockers


def copied_scalar_kind(type_name: str) -> str | None:
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


def compare_summary_field(
    blockers: list[dict[str, Any]],
    *,
    source_label: str,
    safety_summary: dict[str, Any],
    key: str,
    expected: object,
) -> None:
    if safety_summary.get(key) != expected:
        blockers.append(
            {
                "reason": "signature_manifest_safety_summary_count_mismatch",
                "label": f"{source_label}:$.safety_summary.{key}",
                "expected": expected,
                "recorded": safety_summary.get(key),
            }
        )


def unique_ordered(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def known_ufunction_target_set_targets(target_set: str) -> list[str] | None:
    try:
        from reflection_target_sets import TARGET_SETS
    except ImportError:
        return None

    entries = TARGET_SETS.get(target_set)
    if entries is None:
        return None
    targets: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, str):
            continue
        schema, _, target = entry.partition(":")
        if schema != "obelisk.ufunction-chain.snapshot.v1":
            continue
        if target not in seen:
            targets.append(target)
            seen.add(target)
    return targets


def expected_rc_ufunction_target_sources() -> dict[str, list[str]] | None:
    try:
        from reflection_target_sets import TARGET_SETS
    except ImportError:
        return None

    expected: dict[str, list[str]] = {}
    for target_set in RC_UFUNCTION_TARGET_SETS:
        entries = TARGET_SETS.get(target_set)
        if not isinstance(entries, (list, tuple)):
            return None
        for entry in entries:
            if not isinstance(entry, str) or not entry.startswith(f"{RC_UFUNCTION_SNAPSHOT_SCHEMA}:"):
                continue
            expected.setdefault(entry, []).append(target_set)
    return expected


def rc_manifest_relative_path_blockers(value: object, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, str) or not value:
        return [{"reason": "rc_ufunction_manifest_snapshot_relative_path_invalid", "label": label, "recorded": value}]
    if value.startswith("/") or "\\" in value or re.match(r"^[A-Za-z]:[\\/]", value):
        return [{"reason": "rc_ufunction_manifest_snapshot_relative_path_invalid", "label": label, "recorded": value}]
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return [{"reason": "rc_ufunction_manifest_snapshot_relative_path_invalid", "label": label, "recorded": value}]
    return []


def validate_rc_manifest_no_absolute_strings(payload: dict[str, Any], *, label: str) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    unix_absolute_fragment = re.compile(r"(^|[\s='\":])/(?!/)")
    windows_absolute_fragment = re.compile(r"(^|[\s='\":])[A-Za-z]:[\\/]")
    for trail, raw_value in collect_string_fields(payload):
        if raw_value == "redacted":
            continue
        if (
            "/servidor/ark" in raw_value
            or unix_absolute_fragment.search(raw_value) is not None
            or windows_absolute_fragment.search(raw_value) is not None
        ):
            blockers.append(
                {
                    "reason": "rc_ufunction_manifest_absolute_or_sensitive_path_string",
                    "label": f"{label}:{trail}",
                    "value": raw_value,
                }
            )
    return blockers


def validate_rc_ufunction_second_source_root_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    manifest_path: Path,
    workspace_root: Path,
    protected_root: Path,
    mode: str,
) -> list[dict[str, Any]]:
    if payload.get("schema") != RC_UFUNCTION_SECOND_SOURCE_ROOT_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    if payload.get("snapshot_schema") != RC_UFUNCTION_SNAPSHOT_SCHEMA:
        blockers.append(
            {
                "reason": "rc_ufunction_manifest_snapshot_schema_mismatch",
                "label": f"{label}:$.snapshot_schema",
                "recorded_schema": payload.get("snapshot_schema"),
            }
        )
    if payload.get("path_redacted") is not True:
        blockers.append({"reason": "rc_ufunction_manifest_path_not_redacted", "label": f"{label}:$.path_redacted"})
    if payload.get("target_sets") != list(RC_UFUNCTION_TARGET_SETS):
        blockers.append(
            {
                "reason": "rc_ufunction_manifest_target_sets_mismatch",
                "label": f"{label}:$.target_sets",
                "expected": list(RC_UFUNCTION_TARGET_SETS),
                "recorded": payload.get("target_sets"),
            }
        )
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_RC_UFUNCTION_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "rc_ufunction_manifest_non_claims_missing",
                "label": f"{label}:$.non_claims",
                "required": sorted(REQUIRED_RC_UFUNCTION_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    if mode == "promote":
        blockers.append({"reason": "promote_mode_rc_ufunction_manifest_candidate_only", "label": label})

    expected_sources = expected_rc_ufunction_target_sources()
    if expected_sources is None:
        blockers.append({"reason": "rc_ufunction_manifest_target_sets_unavailable", "label": f"{label}:$.target_sets"})
        expected_sources = {}
    expected_targets = sorted(expected_sources)
    target_count = payload.get("target_count")
    if not is_json_int(target_count):
        blockers.append({"reason": "rc_ufunction_manifest_target_count_invalid", "label": f"{label}:$.target_count"})
    elif target_count != len(expected_targets):
        blockers.append(
            {
                "reason": "rc_ufunction_manifest_target_count_mismatch",
                "label": f"{label}:$.target_count",
                "expected": len(expected_targets),
                "recorded": target_count,
            }
        )

    snapshots = payload.get("snapshots")
    emitted_targets: list[str] = []
    used_relative_paths: dict[str, str] = {}
    if not isinstance(snapshots, list):
        blockers.append({"reason": "rc_ufunction_manifest_snapshots_not_list", "label": f"{label}:$.snapshots"})
    else:
        if is_json_int(target_count) and len(snapshots) != target_count:
            blockers.append(
                {
                    "reason": "rc_ufunction_manifest_snapshot_count_mismatch",
                    "label": f"{label}:$.snapshots",
                    "expected": target_count,
                    "recorded": len(snapshots),
                }
            )
        for index, snapshot in enumerate(snapshots):
            snapshot_label = f"{label}:$.snapshots[{index}]"
            if not isinstance(snapshot, dict):
                blockers.append({"reason": "rc_ufunction_manifest_snapshot_not_object", "label": snapshot_label})
                continue
            target = snapshot.get("target")
            if not isinstance(target, str) or not target:
                blockers.append({"reason": "rc_ufunction_manifest_snapshot_target_invalid", "label": f"{snapshot_label}.target"})
            else:
                emitted_targets.append(target)
                if target not in expected_sources:
                    blockers.append(
                        {
                            "reason": "rc_ufunction_manifest_unexpected_snapshot_target",
                            "label": f"{snapshot_label}.target",
                            "target": target,
                        }
                    )
            source_target_sets = snapshot.get("source_target_sets")
            expected_source_sets = sorted(expected_sources.get(str(target), []))
            if not isinstance(source_target_sets, list) or any(not isinstance(item, str) for item in source_target_sets):
                blockers.append(
                    {
                        "reason": "rc_ufunction_manifest_snapshot_source_target_sets_invalid",
                        "label": f"{snapshot_label}.source_target_sets",
                    }
                )
            elif sorted(source_target_sets) != expected_source_sets:
                blockers.append(
                    {
                        "reason": "rc_ufunction_manifest_snapshot_source_target_sets_mismatch",
                        "label": f"{snapshot_label}.source_target_sets",
                        "expected": expected_source_sets,
                        "recorded": source_target_sets,
                    }
                )

            relative_path = snapshot.get("relative_path")
            relative_path_blockers = rc_manifest_relative_path_blockers(relative_path, label=f"{snapshot_label}.relative_path")
            blockers.extend(relative_path_blockers)
            snapshot_path: Path | None = None
            if not relative_path_blockers and isinstance(relative_path, str):
                previous_target = used_relative_paths.get(relative_path)
                if previous_target is not None and previous_target != target:
                    blockers.append(
                        {
                            "reason": "rc_ufunction_manifest_snapshot_relative_path_collision",
                            "label": f"{snapshot_label}.relative_path",
                            "relative_path": relative_path,
                            "first_target": previous_target,
                            "target": target,
                        }
                    )
                used_relative_paths[relative_path] = str(target)
                snapshot_path = manifest_path.parent / relative_path
                blockers.extend(
                    path_blockers(
                        snapshot_path,
                        label=f"{snapshot_label}.relative_path",
                        workspace_root=workspace_root,
                        protected_root=protected_root,
                        require_workspace=True,
                    )
                )
                if not snapshot_path.is_file():
                    blockers.append(
                        {
                            "reason": "rc_ufunction_manifest_snapshot_file_missing",
                            "label": f"{snapshot_label}.relative_path",
                            "relative_path": relative_path,
                        }
                    )
            snapshot_sha256 = snapshot.get("snapshot_sha256")
            if not isinstance(snapshot_sha256, str) or SHA256_RE.fullmatch(snapshot_sha256) is None:
                blockers.append(
                    {
                        "reason": "rc_ufunction_manifest_snapshot_sha256_invalid",
                        "label": f"{snapshot_label}.snapshot_sha256",
                    }
                )
            elif snapshot_path is not None and snapshot_path.is_file():
                actual_sha256 = sha256_file(snapshot_path)
                if actual_sha256 != snapshot_sha256:
                    blockers.append(
                        {
                            "reason": "rc_ufunction_manifest_snapshot_sha256_mismatch",
                            "label": f"{snapshot_label}.snapshot_sha256",
                            "expected": actual_sha256,
                            "recorded": snapshot_sha256,
                        }
                    )
            evidence = snapshot.get("evidence")
            if not isinstance(evidence, dict):
                blockers.append({"reason": "rc_ufunction_manifest_snapshot_evidence_not_object", "label": f"{snapshot_label}.evidence"})

    counts = Counter(emitted_targets)
    duplicate_targets = sorted(target for target, count in counts.items() if count > 1)
    if duplicate_targets:
        blockers.append({"reason": "rc_ufunction_manifest_duplicate_snapshot_targets", "label": f"{label}:$.snapshots", "targets": duplicate_targets})
    missing_targets = [target for target in expected_targets if target not in counts]
    unexpected_targets = sorted(target for target in counts if target not in expected_sources)
    if missing_targets or unexpected_targets:
        blockers.append(
            {
                "reason": "rc_ufunction_manifest_target_coverage_mismatch",
                "label": f"{label}:$.snapshots",
                "missing_targets": missing_targets,
                "unexpected_targets": unexpected_targets,
            }
        )
    blockers.extend(validate_rc_manifest_no_absolute_strings(payload, label=label))
    return blockers


def validate_target_set_coverage(
    payload: dict[str, Any],
    *,
    source_label: str,
    target_sets: list[str],
    source_target_sets: list[str],
    signature_targets: list[str],
    strict: bool,
) -> list[dict[str, Any]]:
    coverage = payload.get("target_set_coverage")
    if coverage is None:
        if strict:
            return [{"reason": "signature_manifest_missing_target_set_coverage", "label": f"{source_label}:$.target_set_coverage"}]
        if (target_sets or source_target_sets) and not is_historical_missing_target_set_coverage_marker(payload):
            return [
                {
                    "reason": "signature_manifest_missing_target_set_coverage_without_historical_marker",
                    "label": f"{source_label}:$.target_set_coverage",
                }
            ]
        return []

    blockers: list[dict[str, Any]] = []
    if not isinstance(coverage, dict):
        return [{"reason": "signature_manifest_target_set_coverage_not_object", "label": f"{source_label}:$.target_set_coverage"}]
    if coverage.get("schema") != TARGET_SET_COVERAGE_SCHEMA:
        blockers.append(
            {
                "reason": "signature_manifest_target_set_coverage_schema_mismatch",
                "label": f"{source_label}:$.target_set_coverage.schema",
                "recorded_schema": coverage.get("schema"),
            }
        )
    if not strict:
        return blockers

    declared = [(target_set, "manifest") for target_set in target_sets] + [
        (target_set, "snapshot") for target_set in source_target_sets
    ]
    expanded: dict[str, list[str]] = {}
    for target_set, _ in declared:
        targets = known_ufunction_target_set_targets(target_set)
        if not targets:
            blockers.append(
                {
                    "reason": "signature_manifest_unknown_target_set",
                    "label": f"{source_label}:$.target_set_coverage",
                    "target_set": target_set,
                }
            )
            continue
        expanded[target_set] = targets

    expected_targets = unique_ordered(
        [
            target
            for target_set, _ in declared
            for target in expanded.get(target_set, [])
        ]
    )
    expected_set = set(expected_targets)
    emitted_set = set(signature_targets)
    if len(signature_targets) != len(emitted_set):
        blockers.append({"reason": "signature_manifest_duplicate_signature_targets", "label": f"{source_label}:$.signatures"})

    missing_targets = [target for target in expected_targets if target not in emitted_set]
    unexpected_targets = [target for target in signature_targets if declared and target not in expected_set]
    recorded_expected = coverage.get("expected_targets")
    recorded_emitted = coverage.get("emitted_targets")
    recorded_missing = coverage.get("missing_targets")
    recorded_unexpected = coverage.get("unexpected_targets")

    if recorded_expected != expected_targets:
        blockers.append(
            {
                "reason": "signature_manifest_target_set_expected_targets_mismatch",
                "label": f"{source_label}:$.target_set_coverage.expected_targets",
                "expected": expected_targets,
                "recorded": recorded_expected,
            }
        )
    if recorded_emitted != signature_targets:
        blockers.append(
            {
                "reason": "signature_manifest_target_set_emitted_targets_mismatch",
                "label": f"{source_label}:$.target_set_coverage.emitted_targets",
                "expected": signature_targets,
                "recorded": recorded_emitted,
            }
        )
    if recorded_missing != missing_targets:
        blockers.append(
            {
                "reason": "signature_manifest_target_set_missing_targets_mismatch",
                "label": f"{source_label}:$.target_set_coverage.missing_targets",
                "expected": missing_targets,
                "recorded": recorded_missing,
            }
        )
    if recorded_unexpected != unexpected_targets:
        blockers.append(
            {
                "reason": "signature_manifest_target_set_unexpected_targets_mismatch",
                "label": f"{source_label}:$.target_set_coverage.unexpected_targets",
                "expected": unexpected_targets,
                "recorded": recorded_unexpected,
            }
        )
    if declared and (missing_targets or unexpected_targets):
        blockers.append(
            {
                "reason": "signature_manifest_target_set_coverage_incomplete",
                "label": f"{source_label}:$.target_set_coverage",
                "missing_targets": missing_targets,
                "unexpected_targets": unexpected_targets,
            }
        )

    expected_status = "complete" if declared else "not_declared"
    if coverage.get("status") != expected_status:
        blockers.append(
            {
                "reason": "signature_manifest_target_set_coverage_status_mismatch",
                "label": f"{source_label}:$.target_set_coverage.status",
                "expected": expected_status,
                "recorded": coverage.get("status"),
            }
        )
    if coverage.get("complete") is not True:
        blockers.append(
            {
                "reason": "signature_manifest_target_set_coverage_not_complete",
                "label": f"{source_label}:$.target_set_coverage.complete",
                "recorded": coverage.get("complete"),
            }
        )

    entries = coverage.get("declared_target_sets")
    if not isinstance(entries, list):
        blockers.append({"reason": "signature_manifest_declared_target_sets_not_list", "label": f"{source_label}:$.target_set_coverage.declared_target_sets"})
        return blockers
    if len(entries) != len(declared):
        blockers.append(
            {
                "reason": "signature_manifest_declared_target_set_count_mismatch",
                "label": f"{source_label}:$.target_set_coverage.declared_target_sets",
                "expected": len(declared),
                "recorded": len(entries),
            }
        )
    for index, entry in enumerate(entries):
        entry_label = f"{source_label}:$.target_set_coverage.declared_target_sets[{index}]"
        if not isinstance(entry, dict):
            blockers.append({"reason": "signature_manifest_declared_target_set_not_object", "label": entry_label})
            continue
        expected_name, expected_source = declared[index] if index < len(declared) else (None, None)
        if entry.get("name") != expected_name or entry.get("source") != expected_source:
            blockers.append(
                {
                    "reason": "signature_manifest_declared_target_set_identity_mismatch",
                    "label": entry_label,
                    "expected": {"name": expected_name, "source": expected_source},
                    "recorded": {"name": entry.get("name"), "source": entry.get("source")},
                }
            )
        targets = expanded.get(str(entry.get("name")), [])
        covered = [target for target in targets if target in emitted_set]
        missing = [target for target in targets if target not in emitted_set]
        if entry.get("expected_targets") != targets:
            blockers.append({"reason": "signature_manifest_declared_target_set_targets_mismatch", "label": f"{entry_label}.expected_targets"})
        if entry.get("covered_targets") != covered:
            blockers.append({"reason": "signature_manifest_declared_target_set_covered_targets_mismatch", "label": f"{entry_label}.covered_targets"})
        if entry.get("missing_targets") != missing:
            blockers.append({"reason": "signature_manifest_declared_target_set_missing_targets_mismatch", "label": f"{entry_label}.missing_targets"})
        if entry.get("complete") != (not missing):
            blockers.append({"reason": "signature_manifest_declared_target_set_complete_mismatch", "label": f"{entry_label}.complete"})
    return blockers


def validate_redacted_signature_manifest(
    payload: dict[str, Any],
    *,
    source_label: str,
    workspace_root: Path,
    protected_root: Path,
    mode: str,
    strict_target_set_coverage: bool,
) -> list[dict[str, Any]]:
    if payload.get("schema") != REDACTED_UFUNCTION_SIGNATURE_SCHEMA:
        return []
    blockers: list[dict[str, Any]] = []
    snapshot_root = payload.get("snapshot_root")
    if snapshot_root not in (None, "redacted"):
        blockers.append(
            {
                "reason": "signature_manifest_unredacted_snapshot_root",
                "label": f"{source_label}:$.snapshot_root",
                "recorded_snapshot_root": snapshot_root,
            }
        )
    safety_summary = payload.get("safety_summary")
    input_snapshot_count = 0
    generated_from = payload.get("generated_from")
    generated_snapshot_ids: dict[str, str] = {}
    if not isinstance(generated_from, dict):
        blockers.append({"reason": "signature_manifest_missing_generated_from", "label": f"{source_label}:$.generated_from"})
    else:
        if generated_from.get("snapshot_schema") != "obelisk.ufunction-chain.snapshot.v1":
            blockers.append(
                {
                    "reason": "signature_manifest_snapshot_schema_mismatch",
                    "label": f"{source_label}:$.generated_from.snapshot_schema",
                    "recorded_schema": generated_from.get("snapshot_schema"),
                }
            )
        input_snapshots = generated_from.get("input_snapshots")
        if not isinstance(input_snapshots, list):
            blockers.append(
                {"reason": "signature_manifest_input_snapshots_not_list", "label": f"{source_label}:$.generated_from.input_snapshots"}
            )
        else:
            input_snapshot_count = len(input_snapshots)
            for index, snapshot in enumerate(input_snapshots):
                snapshot_label = f"{source_label}:$.generated_from.input_snapshots[{index}]"
                if not isinstance(snapshot, dict):
                    blockers.append({"reason": "signature_manifest_input_snapshot_not_object", "label": snapshot_label})
                    continue
                snapshot_id = snapshot.get("id")
                sha256 = snapshot.get("sha256")
                if not isinstance(snapshot_id, str) or not snapshot_id:
                    blockers.append({"reason": "signature_manifest_input_snapshot_id_invalid", "label": f"{snapshot_label}.id"})
                if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
                    blockers.append(
                        {
                            "reason": "signature_manifest_input_snapshot_sha256_invalid",
                            "label": f"{snapshot_label}.sha256",
                            "recorded_sha256": sha256,
                        }
                    )
                if isinstance(snapshot_id, str) and isinstance(sha256, str):
                    generated_snapshot_ids[snapshot_id] = sha256
    missing_targets = payload.get("missing_targets")
    missing_target_count = len(missing_targets) if isinstance(missing_targets, list) else 0
    if missing_targets is not None and not isinstance(missing_targets, list):
        blockers.append({"reason": "signature_manifest_missing_targets_not_list", "label": f"{source_label}:$.missing_targets"})
    target_sets = payload.get("target_sets", [])
    target_set_count = 0
    if not isinstance(target_sets, list) or any(not isinstance(item, str) or not item for item in target_sets):
        blockers.append({"reason": "signature_manifest_target_sets_invalid", "label": f"{source_label}:$.target_sets"})
    else:
        target_set_count = len(target_sets)
    source_target_sets = payload.get("source_target_sets", [])
    source_target_set_count = 0
    if not isinstance(source_target_sets, list) or any(not isinstance(item, str) or not item for item in source_target_sets):
        blockers.append({"reason": "signature_manifest_source_target_sets_invalid", "label": f"{source_label}:$.source_target_sets"})
    else:
        source_target_set_count = len(source_target_sets)
    recorded_snapshot_count = payload.get("snapshot_count")
    if recorded_snapshot_count != input_snapshot_count:
        blockers.append(
            {
                "reason": "signature_manifest_snapshot_count_mismatch",
                "label": f"{source_label}:$.snapshot_count",
                "expected": input_snapshot_count,
                "recorded": recorded_snapshot_count,
            }
        )
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_REDACTED_SIGNATURE_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "signature_manifest_non_claims_missing",
                "label": f"{source_label}:$.non_claims",
                "expected": sorted(REQUIRED_REDACTED_SIGNATURE_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    if not isinstance(safety_summary, dict):
        blockers.append({"reason": "signature_manifest_missing_safety_summary", "label": f"{source_label}:$.safety_summary"})
    else:
        if safety_summary.get("artifact_status") != "candidate_only":
            blockers.append(
                {
                    "reason": "signature_manifest_artifact_status_not_candidate_only",
                    "label": f"{source_label}:$.safety_summary.artifact_status",
                    "recorded_status": safety_summary.get("artifact_status"),
                }
            )
        if safety_summary.get("intended_use") != "offline_review_only":
            blockers.append(
                {
                    "reason": "signature_manifest_intended_use_not_offline_review_only",
                    "label": f"{source_label}:$.safety_summary.intended_use",
                    "recorded_intended_use": safety_summary.get("intended_use"),
                }
            )
        if safety_summary.get("promotion_ready") is not False:
            blockers.append(
                {
                    "reason": "signature_manifest_promotion_ready_overclaim",
                    "label": f"{source_label}:$.safety_summary.promotion_ready",
                    "recorded_promotion_ready": safety_summary.get("promotion_ready"),
                }
            )
        if safety_summary.get("evidence_scope") != "redacted_ufunction_signature_metadata":
            blockers.append(
                {
                    "reason": "signature_manifest_evidence_scope_mismatch",
                    "label": f"{source_label}:$.safety_summary.evidence_scope",
                    "recorded_scope": safety_summary.get("evidence_scope"),
                }
            )
        not_promoted = safety_summary.get("not_promoted_surfaces")
        if not isinstance(not_promoted, list) or set(not_promoted) != REQUIRED_REDACTED_SIGNATURE_NON_PROMOTED_SURFACES:
            blockers.append(
                {
                    "reason": "signature_manifest_not_promoted_surfaces_mismatch",
                    "label": f"{source_label}:$.safety_summary.not_promoted_surfaces",
                    "expected": sorted(REQUIRED_REDACTED_SIGNATURE_NON_PROMOTED_SURFACES),
                    "recorded": not_promoted,
                }
            )
        if mode == "promote":
            blockers.append(
                {
                    "reason": "promote_mode_signature_manifest_candidate_only",
                    "label": f"{source_label}:$.safety_summary",
                }
            )
    signatures = payload.get("signatures")
    signatures_list: list[dict[str, Any]] = []
    copied_scalar_by_kind: Counter[str] = Counter()
    redacted_by_reason: Counter[str] = Counter()
    blocked_by_reason: Counter[str] = Counter()
    promotion_blockers_by_reason: Counter[str] = Counter()
    direction_counts: Counter[str] = Counter()
    if not isinstance(signatures, list):
        blockers.append({"reason": "signature_manifest_signatures_not_list", "label": f"{source_label}:$.signatures"})
    else:
        for index, signature in enumerate(signatures):
            signature_label = f"{source_label}:$.signatures[{index}]"
            if not isinstance(signature, dict):
                blockers.append({"reason": "signature_manifest_signature_not_object", "label": signature_label})
                continue
            signatures_list.append(signature)
            if signature.get("signature_status") != "candidate-only":
                blockers.append(
                    {
                        "reason": "signature_manifest_signature_status_not_candidate_only",
                        "label": f"{signature_label}.signature_status",
                        "recorded_status": signature.get("signature_status"),
                    }
                )
            promotion_blockers = signature.get("promotion_blockers")
            if (
                not isinstance(promotion_blockers, list)
                or "function_flags_not_bound_to_exact_target_gate" not in promotion_blockers
            ):
                blockers.append(
                    {
                        "reason": "signature_manifest_missing_function_flag_blocker",
                        "label": f"{signature_label}.promotion_blockers",
                        "recorded": promotion_blockers,
                    }
                )
            if isinstance(promotion_blockers, list):
                promotion_blockers_by_reason.update(blocker for blocker in promotion_blockers if isinstance(blocker, str))
            source_snapshot = signature.get("source_snapshot")
            source_sha256 = signature.get("source_snapshot_sha256")
            if not isinstance(source_snapshot, str) or source_snapshot not in generated_snapshot_ids:
                blockers.append(
                    {
                        "reason": "signature_manifest_source_snapshot_not_declared",
                        "label": f"{signature_label}.source_snapshot",
                        "recorded_source_snapshot": source_snapshot,
                    }
                )
            if not isinstance(source_sha256, str) or SHA256_RE.fullmatch(source_sha256) is None:
                blockers.append(
                    {
                        "reason": "signature_manifest_source_snapshot_sha256_invalid",
                        "label": f"{signature_label}.source_snapshot_sha256",
                        "recorded_sha256": source_sha256,
                    }
                )
            elif isinstance(source_snapshot, str) and generated_snapshot_ids.get(source_snapshot) != source_sha256:
                blockers.append(
                    {
                        "reason": "signature_manifest_source_snapshot_sha256_mismatch",
                        "label": f"{signature_label}.source_snapshot_sha256",
                        "expected_sha256": generated_snapshot_ids.get(source_snapshot),
                        "recorded_sha256": source_sha256,
                    }
                )
            for trail, raw_value in collect_bool_fields(signature, trail=f"$.signatures[{index}]"):
                key = trail.rsplit(".", 1)[-1]
                if raw_value is True and key in READY_OVERCLAIM_KEYS:
                    blockers.append(
                        {
                            "reason": "signature_manifest_signature_readiness_overclaim",
                            "label": f"{source_label}:{trail}",
                        }
                    )
            params = signature.get("params", [])
            if isinstance(params, list):
                for param in params:
                    if not isinstance(param, dict):
                        continue
                    direction = param.get("direction")
                    if isinstance(direction, str):
                        direction_counts[direction] += 1
                    type_name = param.get("type")
                    if isinstance(type_name, str):
                        scalar_kind = copied_scalar_kind(type_name)
                        if scalar_kind is not None:
                            copied_scalar_by_kind[scalar_kind] += 1
                        redacted_reason = redacted_summary_reason(type_name)
                        if redacted_reason is not None:
                            redacted_by_reason[redacted_reason] += 1
                    param_blockers = param.get("promotion_blockers", [])
                    if isinstance(param_blockers, list):
                        promotion_blockers_by_reason.update(blocker for blocker in param_blockers if isinstance(blocker, str))
            blocked_properties = signature.get("blocked_properties", [])
            if isinstance(blocked_properties, list):
                for blocked_property in blocked_properties:
                    if isinstance(blocked_property, dict):
                        reason = blocked_property.get("reason")
                        blocked_by_reason[reason if isinstance(reason, str) else "unknown"] += 1
    signature_targets = [
        signature.get("target")
        for signature in signatures_list
        if isinstance(signature.get("target"), str)
    ]
    blockers.extend(
        validate_target_set_coverage(
            payload,
            source_label=source_label,
            target_sets=target_sets if isinstance(target_sets, list) else [],
            source_target_sets=source_target_sets if isinstance(source_target_sets, list) else [],
            signature_targets=signature_targets,
            strict=strict_target_set_coverage,
        )
    )
    if isinstance(safety_summary, dict):
        actual_counts = {
            "blocked_count_total": sum(
                len(signature.get("blocked_properties", []))
                for signature in signatures_list
                if isinstance(signature.get("blocked_properties", []), list)
            ),
            "bool_masked_field_count": sum(
                1
                for signature in signatures_list
                for param in signature.get("params", [])
                if isinstance(param, dict) and "bool_masks" in param
            ),
            "missing_target_count": missing_target_count,
            "param_count_total": sum(
                len(signature.get("params", []))
                for signature in signatures_list
                if isinstance(signature.get("params", []), list)
            ),
            "promotion_blocker_count_total": sum(
                len(signature.get("promotion_blockers", []))
                for signature in signatures_list
                if isinstance(signature.get("promotion_blockers", []), list)
            )
            + sum(
                len(param.get("promotion_blockers", []))
                for signature in signatures_list
                for param in signature.get("params", [])
                if isinstance(param, dict) and isinstance(param.get("promotion_blockers", []), list)
            ),
            "redacted_count_total": sum(
                1
                for signature in signatures_list
                for param in signature.get("params", [])
                if isinstance(param, dict) and isinstance(param.get("type"), str) and param["type"].startswith("redacted_")
            ),
            "signature_count": len(signatures_list),
            "snapshot_count": input_snapshot_count,
            "target_set_count": target_set_count + source_target_set_count,
            "zero_param_signature_count": sum(
                1
                for signature in signatures_list
                if signature.get("params") == [] and signature.get("blocked_properties") == []
            ),
        }
        actual_counts["copied_scalar_count_total"] = actual_counts["param_count_total"] - actual_counts["redacted_count_total"]
        if payload.get("signature_count") != len(signatures_list):
            blockers.append(
                {
                    "reason": "signature_manifest_signature_count_mismatch",
                    "label": f"{source_label}:$.signature_count",
                    "expected": len(signatures_list),
                    "recorded": payload.get("signature_count"),
                }
            )
        for key, expected in actual_counts.items():
            compare_summary_field(
                blockers,
                source_label=source_label,
                safety_summary=safety_summary,
                key=key,
                expected=expected,
            )
        for key, expected_counter in {
            "blocked_by_reason": blocked_by_reason,
            "copied_scalar_by_kind": copied_scalar_by_kind,
            "direction_counts": direction_counts,
            "promotion_blockers_by_reason": promotion_blockers_by_reason,
            "redacted_by_reason": redacted_by_reason,
        }.items():
            compare_summary_field(
                blockers,
                source_label=source_label,
                safety_summary=safety_summary,
                key=key,
                expected=dict(sorted(expected_counter.items())),
            )
        compare_summary_field(
            blockers,
            source_label=source_label,
            safety_summary=safety_summary,
            key="unknown_or_blocked_present",
            expected=actual_counts["blocked_count_total"] > 0,
        )
        for trail, raw_value in collect_bool_fields(safety_summary, trail="$.safety_summary"):
            key = trail.rsplit(".", 1)[-1]
            if raw_value is True and key in READY_OVERCLAIM_KEYS:
                blockers.append(
                    {
                        "reason": "signature_manifest_safety_summary_readiness_overclaim",
                        "label": f"{source_label}:{trail}",
                    }
                )
    for trail, raw_value in collect_string_fields(payload):
        if raw_value == "redacted":
            continue
        candidate = Path(raw_value)
        if not candidate.is_absolute():
            continue
        blockers.extend(
            path_blockers(
                candidate,
                label=f"{source_label}:{trail}",
                workspace_root=workspace_root,
                protected_root=protected_root,
                require_workspace=False,
            )
        )
    return blockers


def validate_weak_helper_caller_mode_manifest(
    payload: dict[str, Any],
    *,
    source_label: str,
    workspace_root: Path,
    protected_root: Path,
    mode: str,
) -> list[dict[str, Any]]:
    if payload.get("schema") != WEAK_HELPER_CALLER_MODE_SCHEMA:
        return []
    blockers: list[dict[str, Any]] = []
    if payload.get("status") != "accepted_internal_static_evidence":
        blockers.append(
            {
                "reason": "weak_helper_status_not_internal_static_evidence",
                "label": f"{source_label}:$.status",
                "recorded_status": payload.get("status"),
            }
        )
    binary = payload.get("binary")
    if not isinstance(binary, dict):
        blockers.append({"reason": "weak_helper_missing_binary", "label": f"{source_label}:$.binary"})
    else:
        if binary.get("sha256") != WEAK_HELPER_BINARY_SHA256:
            blockers.append(
                {
                    "reason": "weak_helper_binary_sha256_mismatch",
                    "label": f"{source_label}:$.binary.sha256",
                    "recorded_sha256": binary.get("sha256"),
                }
            )
        if binary.get("path_redacted") is not True:
            blockers.append({"reason": "weak_helper_binary_path_not_redacted", "label": f"{source_label}:$.binary.path_redacted"})
    coverage = payload.get("direct_call_coverage")
    if not isinstance(coverage, dict):
        blockers.append({"reason": "weak_helper_missing_direct_call_coverage", "label": f"{source_label}:$.direct_call_coverage"})
    else:
        for helper, expected in {"0x1d56b60": 4, "0x1d56c70": 6}.items():
            entry = coverage.get(helper)
            if not isinstance(entry, dict) or entry.get("expected") != expected or entry.get("observed") != expected:
                blockers.append(
                    {
                        "reason": "weak_helper_direct_call_coverage_incomplete",
                        "label": f"{source_label}:$.direct_call_coverage.{helper}",
                        "expected": expected,
                        "recorded": entry,
                    }
                )
    builder_contract = payload.get("builder_contract")
    if not isinstance(builder_contract, dict):
        blockers.append({"reason": "weak_helper_missing_builder_contract", "label": f"{source_label}:$.builder_contract"})
    else:
        if builder_contract.get("promotion_gate_ready") is not False:
            blockers.append(
                {
                    "reason": "weak_helper_promotion_ready_overclaim",
                    "label": f"{source_label}:$.builder_contract.promotion_gate_ready",
                    "recorded_promotion_gate_ready": builder_contract.get("promotion_gate_ready"),
                }
            )
        if builder_contract.get("consumption_scope") != "internal_static_research_only":
            blockers.append(
                {
                    "reason": "weak_helper_consumption_scope_not_internal_static",
                    "label": f"{source_label}:$.builder_contract.consumption_scope",
                    "recorded_scope": builder_contract.get("consumption_scope"),
                }
            )
        if mode == "promote":
            blockers.append(
                {
                    "reason": "promote_mode_weak_helper_internal_static_only",
                    "label": f"{source_label}:$.builder_contract",
                }
            )
        blockers_value = builder_contract.get("remaining_blockers")
        if not isinstance(blockers_value, list) or not blockers_value:
            blockers.append({"reason": "weak_helper_missing_remaining_blockers", "label": f"{source_label}:$.builder_contract.remaining_blockers"})
        not_promoted = builder_contract.get("not_promoted")
        if not isinstance(not_promoted, list) or "ResourceHandle" not in not_promoted:
            blockers.append({"reason": "weak_helper_missing_resourcehandle_nonclaim", "label": f"{source_label}:$.builder_contract.not_promoted"})
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        blockers.append({"reason": "weak_helper_missing_sources", "label": f"{source_label}:$.sources"})
    else:
        expected_sources = {
            "direct_call_counts": "objdump-or-radare2",
            "ghidra_stdout": "ghidra",
            "r2_windows": "radare2",
        }
        for key, expected_tool in expected_sources.items():
            entry = sources.get(key)
            if not isinstance(entry, dict):
                blockers.append({"reason": "weak_helper_missing_source_entry", "label": f"{source_label}:$.sources.{key}"})
                continue
            if SHA256_RE.fullmatch(str(entry.get("artifact_sha256", ""))) is None:
                blockers.append(
                    {
                        "reason": "weak_helper_source_sha256_invalid",
                        "label": f"{source_label}:$.sources.{key}.artifact_sha256",
                        "recorded_sha256": entry.get("artifact_sha256"),
                    }
                )
                artifact_sha256 = None
            else:
                artifact_sha256 = str(entry.get("artifact_sha256"))
            if entry.get("tool") != expected_tool:
                blockers.append(
                    {
                        "reason": "weak_helper_source_tool_mismatch",
                        "label": f"{source_label}:$.sources.{key}.tool",
                        "expected_tool": expected_tool,
                        "recorded_tool": entry.get("tool"),
                    }
                )
            blockers.extend(
                validate_embedded_static_provenance(
                    entry.get("provenance"),
                    label=f"{source_label}:$.sources.{key}.provenance",
                    expected_artifact_sha256=artifact_sha256,
                    expected_binary_sha256=WEAK_HELPER_BINARY_SHA256,
                    reason_prefix=f"weak_helper_source_{key}",
                )
            )
    required_evidence = payload.get("required_evidence")
    expected_evidence = {
        "all_c70_callers_set_allow4000_and_use_nonnull",
        "b60_callers_are_pairwise_not_validity",
        "direct_call_count_1d56b60_complete",
        "direct_call_count_1d56c70_complete",
        "maybe_pending_ghidra_mode_logic",
        "maybe_pending_helper_window_present",
        "r2_has_maybe_pending_flag_logic",
        "r2_has_stale_flag_logic",
        "stale_ghidra_pairwise_mode_logic",
        "stale_helper_window_present",
    }
    if not isinstance(required_evidence, list) or set(required_evidence) != expected_evidence:
        blockers.append(
            {
                "reason": "weak_helper_required_evidence_mismatch",
                "label": f"{source_label}:$.required_evidence",
                "expected": sorted(expected_evidence),
                "recorded": required_evidence,
            }
        )
    helpers = payload.get("helpers")
    if not isinstance(helpers, dict):
        blockers.append({"reason": "weak_helper_missing_helpers", "label": f"{source_label}:$.helpers"})
    else:
        expected_helpers = {
            "0x1d56b60": {"return_kind": "boolean_like", "mode_args": ["sil", "dl"]},
            "0x1d56c70": {"return_kind": "uobject_pointer_or_null", "mode_args": ["sil"]},
        }
        for helper, expected in expected_helpers.items():
            entry = helpers.get(helper)
            if not isinstance(entry, dict):
                blockers.append({"reason": "weak_helper_missing_helper_entry", "label": f"{source_label}:$.helpers.{helper}"})
                continue
            if entry.get("return_kind") != expected["return_kind"] or entry.get("mode_args") != expected["mode_args"]:
                blockers.append(
                    {
                        "reason": "weak_helper_helper_shape_mismatch",
                        "label": f"{source_label}:$.helpers.{helper}",
                        "expected": expected,
                        "recorded": {
                            "return_kind": entry.get("return_kind"),
                            "mode_args": entry.get("mode_args"),
                        },
                    }
                )
    callers = payload.get("callers")
    if not isinstance(callers, list) or len(callers) != 2:
        blockers.append({"reason": "weak_helper_callers_shape_mismatch", "label": f"{source_label}:$.callers"})
    else:
        caller_helpers = {caller.get("helper") for caller in callers if isinstance(caller, dict)}
        if caller_helpers != {"0x1d56b60", "0x1d56c70"}:
            blockers.append(
                {
                    "reason": "weak_helper_callers_helper_set_mismatch",
                    "label": f"{source_label}:$.callers",
                    "recorded_helpers": sorted(str(value) for value in caller_helpers),
                }
            )
        for index, caller in enumerate(callers):
            if not isinstance(caller, dict):
                blockers.append({"reason": "weak_helper_caller_not_object", "label": f"{source_label}:$.callers[{index}]"})
                continue
            if not isinstance(caller.get("mode_args"), dict) or not isinstance(caller.get("return_use"), dict):
                blockers.append({"reason": "weak_helper_caller_mode_shape_mismatch", "label": f"{source_label}:$.callers[{index}]"})
    caller_rows = payload.get("caller_rows")
    if caller_rows is not None:
        expected_helper_sha = hashlib.sha256(
            f"obelisk.weak-helper-caller-mode:{WEAK_HELPER_BINARY_SHA256}:0x1d56c70".encode("ascii")
        ).hexdigest()
        if not isinstance(caller_rows, list) or len(caller_rows) != 6:
            blockers.append({"reason": "weak_helper_caller_rows_shape_mismatch", "label": f"{source_label}:$.caller_rows"})
        else:
            caller_hashes: set[str] = set()
            for index, row in enumerate(caller_rows):
                row_label = f"{source_label}:$.caller_rows[{index}]"
                if not isinstance(row, dict):
                    blockers.append({"reason": "weak_helper_caller_row_not_object", "label": row_label})
                    continue
                allowed_path_key_trails = {
                    f"$.caller_rows[{index}].mode_args.sil.source",
                    f"$.caller_rows[{index}].return_use.nonzero_path",
                }
                for trail, _ in collect_path_fields(row, trail=f"$.caller_rows[{index}]"):
                    if trail not in allowed_path_key_trails:
                        blockers.append({"reason": "weak_helper_caller_row_path_present", "label": f"{source_label}:{trail}"})
                if row.get("helper") != "0x1d56c70":
                    blockers.append({"reason": "weak_helper_caller_row_helper_mismatch", "label": f"{row_label}.helper"})
                if row.get("helper_address_sha256") != expected_helper_sha:
                    blockers.append({"reason": "weak_helper_caller_row_helper_sha256_mismatch", "label": f"{row_label}.helper_address_sha256"})
                caller_sha = row.get("caller_address_sha256")
                if not isinstance(caller_sha, str) or SHA256_RE.fullmatch(caller_sha) is None:
                    blockers.append({"reason": "weak_helper_caller_row_caller_sha256_invalid", "label": f"{row_label}.caller_address_sha256"})
                elif caller_sha in caller_hashes:
                    blockers.append({"reason": "weak_helper_caller_row_caller_sha256_duplicate", "label": f"{row_label}.caller_address_sha256"})
                else:
                    caller_hashes.add(caller_sha)
                if row.get("mode_args") != {"sil": {"source": "const", "value": 1}}:
                    blockers.append({"reason": "weak_helper_caller_row_mode_args_mismatch", "label": f"{row_label}.mode_args"})
                if row.get("return_use") != {"register": "rax", "nonzero_path": "kept_or_valid"}:
                    blockers.append({"reason": "weak_helper_caller_row_return_use_mismatch", "label": f"{row_label}.return_use"})
                if row.get("source_count") != 2 or row.get("evidence") != ["ghidra", "radare2"]:
                    blockers.append({"reason": "weak_helper_caller_row_source_evidence_mismatch", "label": row_label})
                if row.get("policy_observation") != {
                    "0x100": "null_always",
                    "0x4000": "not_rejected_in_observed_sil_1_callers",
                }:
                    blockers.append({"reason": "weak_helper_caller_row_policy_observation_mismatch", "label": f"{row_label}.policy_observation"})
                if row.get("claim_level") != "static_caller_mode_candidate":
                    blockers.append({"reason": "weak_helper_caller_row_claim_level_mismatch", "label": f"{row_label}.claim_level"})
                if row.get("path_redacted") is not True or row.get("lifecycle_names") != "not_promoted":
                    blockers.append({"reason": "weak_helper_caller_row_boundary_mismatch", "label": row_label})
                for trail, _, reason in collect_candidate_public_overclaims(row):
                    blockers.append({"reason": f"weak_helper_caller_row_public_overclaim_{reason}", "label": f"{source_label}:$.caller_rows[{index}].{trail.lstrip('$.')}"})
    for trail, raw_value in collect_string_fields(payload):
        if raw_value == "redacted":
            continue
        candidate = Path(raw_value)
        if not candidate.is_absolute():
            continue
        blockers.extend(
            path_blockers(
                candidate,
                label=f"{source_label}:{trail}",
                workspace_root=workspace_root,
                protected_root=protected_root,
                require_workspace=False,
            )
        )
    lower_strings = [value.casefold() for _, value in collect_string_fields(payload)]
    for forbidden in ("pending-kill", "destroyed", "unreachable"):
        if any(forbidden in value for value in lower_strings):
            blockers.append({"reason": "weak_helper_ue_lifecycle_name_overclaim", "label": source_label, "forbidden": forbidden})
    return blockers


def validate_redacted_scriptstruct_signature_manifest(
    payload: dict[str, Any],
    *,
    source_label: str,
    mode: str,
) -> list[dict[str, Any]]:
    if payload.get("schema") != REDACTED_SCRIPTSTRUCT_SIGNATURE_SCHEMA:
        return []
    blockers: list[dict[str, Any]] = []
    if payload.get("snapshot_root") != "redacted":
        blockers.append({"reason": "scriptstruct_signature_snapshot_root_not_redacted", "label": f"{source_label}:$.snapshot_root"})
    generated_from = payload.get("generated_from")
    if not isinstance(generated_from, dict):
        blockers.append({"reason": "scriptstruct_signature_missing_generated_from", "label": f"{source_label}:$.generated_from"})
    elif generated_from.get("snapshot_schema") != "obelisk.scriptstruct-chain.snapshot.v1":
        blockers.append(
            {
                "reason": "scriptstruct_signature_snapshot_schema_mismatch",
                "label": f"{source_label}:$.generated_from.snapshot_schema",
                "recorded_schema": generated_from.get("snapshot_schema"),
            }
        )
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_REDACTED_SCRIPTSTRUCT_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "scriptstruct_signature_non_claims_missing",
                "label": f"{source_label}:$.non_claims",
                "expected": sorted(REQUIRED_REDACTED_SCRIPTSTRUCT_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    safety_summary = payload.get("safety_summary")
    if not isinstance(safety_summary, dict):
        blockers.append({"reason": "scriptstruct_signature_missing_safety_summary", "label": f"{source_label}:$.safety_summary"})
    else:
        if safety_summary.get("artifact_status") != "candidate_only":
            blockers.append({"reason": "scriptstruct_signature_status_not_candidate_only", "label": f"{source_label}:$.safety_summary.artifact_status"})
        if safety_summary.get("promotion_ready") is not False:
            blockers.append({"reason": "scriptstruct_signature_promotion_ready_overclaim", "label": f"{source_label}:$.safety_summary.promotion_ready"})
        if safety_summary.get("intended_use") != "offline_review_only":
            blockers.append({"reason": "scriptstruct_signature_intended_use_not_offline_review_only", "label": f"{source_label}:$.safety_summary.intended_use"})
        not_promoted = safety_summary.get("not_promoted_surfaces")
        if not isinstance(not_promoted, list) or set(not_promoted) != REQUIRED_REDACTED_SCRIPTSTRUCT_NOT_PROMOTED_SURFACES:
            blockers.append(
                {
                    "reason": "scriptstruct_signature_not_promoted_surfaces_mismatch",
                    "label": f"{source_label}:$.safety_summary.not_promoted_surfaces",
                    "expected": sorted(REQUIRED_REDACTED_SCRIPTSTRUCT_NOT_PROMOTED_SURFACES),
                    "recorded": not_promoted,
                }
            )
        if mode == "promote":
            blockers.append({"reason": "promote_mode_scriptstruct_signature_candidate_only", "label": f"{source_label}:$.safety_summary"})
    signatures = payload.get("signatures")
    if not isinstance(signatures, list):
        blockers.append({"reason": "scriptstruct_signature_signatures_not_list", "label": f"{source_label}:$.signatures"})
    return blockers


def validate_claims(payload: dict[str, Any], *, label: str, mode: str) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    blockers_value = payload.get("blockers")
    blockers_present = isinstance(blockers_value, list) and len(blockers_value) > 0
    if payload.get("public_gobjects_promotion_ready") is True:
        blockers.append({"reason": "public_gobjects_promotion_overclaim", "label": label})
    if payload.get("promotion_ready") is True:
        blockers.append({"reason": "promotion_ready_overclaim", "label": label})
        if blockers_present:
            blockers.append({"reason": "promotion_ready_with_blockers", "label": label})
    if payload.get("status") == "research-candidate" and payload.get("runtime_ready") is True:
        blockers.append({"reason": "research_candidate_marked_runtime_ready", "label": label})

    evidence_status = payload.get("evidence_status")
    if isinstance(evidence_status, dict):
        if evidence_status.get("status") != "complete" and mode in {"consume", "promote"}:
            blockers.append(
                {
                    "reason": "evidence_pack_not_complete",
                    "label": label,
                    "status": evidence_status.get("status"),
                }
            )
        if evidence_status.get("gdb_core_failed") is not False and mode in {"consume", "promote"}:
            blockers.append({"reason": "evidence_pack_gdb_core_failed", "label": label})
    if mode == "promote":
        non_claims = payload.get("non_claims")
        blocked_contracts = payload.get("blocked_contracts")
        if isinstance(non_claims, list) and non_claims:
            blockers.append({"reason": "promote_mode_manifest_has_non_claims", "label": label})
        if isinstance(blocked_contracts, list) and blocked_contracts:
            blockers.append({"reason": "promote_mode_manifest_has_blocked_contracts", "label": label})
    return blockers


def validate_scriptstruct_inventory_child_artifact(
    artifacts: dict[str, Any],
    key: str,
    *,
    label: str,
    manifest_path: Path,
    workspace_root: Path,
    protected_root: Path,
    expected_schema: str,
    summary_count: int | None = None,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    artifact = artifacts.get(key)
    artifact_label = f"{label}:$.artifacts.{key}"
    if not isinstance(artifact, dict):
        return [{"reason": "scriptstruct_inventory_artifact_entry_invalid", "label": artifact_label}]
    relative_path = artifact.get("path")
    expected_sha256 = artifact.get("sha256")
    if not isinstance(relative_path, str) or not relative_path or PurePosixPath(relative_path).is_absolute() or ".." in PurePosixPath(relative_path).parts:
        blockers.append({"reason": "scriptstruct_inventory_artifact_path_invalid", "label": f"{artifact_label}.path"})
        return blockers
    if not isinstance(expected_sha256, str) or SHA256_RE.fullmatch(expected_sha256) is None:
        blockers.append({"reason": "scriptstruct_inventory_artifact_sha256_invalid", "label": f"{artifact_label}.sha256"})
    path = manifest_path.parent / relative_path
    blockers.extend(path_blockers(path, label=artifact_label, workspace_root=workspace_root, protected_root=protected_root, require_workspace=True))
    if blockers:
        return blockers
    if not path.is_file():
        blockers.append({"reason": "scriptstruct_inventory_artifact_not_file", "label": artifact_label, "path": str(path)})
        return blockers
    observed_sha256 = sha256_file(path)
    if isinstance(expected_sha256, str) and observed_sha256 != expected_sha256:
        blockers.append(
            {
                "reason": "scriptstruct_inventory_artifact_sha256_mismatch",
                "label": f"{artifact_label}.sha256",
                "expected": expected_sha256,
                "observed": observed_sha256,
            }
        )
    child_payload, load_blockers = load_json(path)
    if child_payload is None:
        blockers.extend(load_blockers)
        return blockers
    blockers.extend(
        validate_json_path_fields(
            child_payload,
            source_label=str(path),
            workspace_root=workspace_root,
            protected_root=protected_root,
        )
    )
    blockers.extend(
        validate_json_protected_root_strings(
            child_payload,
            source_label=str(path),
            workspace_root=workspace_root,
            protected_root=protected_root,
        )
    )
    if child_payload.get("schema") != expected_schema:
        blockers.append(
            {
                "reason": "scriptstruct_inventory_artifact_schema_mismatch",
                "label": f"{artifact_label}.schema",
                "expected": expected_schema,
                "recorded": child_payload.get("schema"),
            }
        )
    if summary_count is not None and key == "scriptstruct_inventory":
        summary = child_payload.get("summary")
        if not isinstance(summary, dict) or summary.get("scriptstruct_count") != summary_count:
            blockers.append(
                {
                    "reason": "scriptstruct_inventory_artifact_summary_mismatch",
                    "label": f"{artifact_label}.summary.scriptstruct_count",
                    "expected": summary_count,
                    "recorded": summary.get("scriptstruct_count") if isinstance(summary, dict) else None,
                }
            )
    return blockers


def validate_scriptstruct_inventory_pack_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    manifest_path: Path,
    workspace_root: Path,
    protected_root: Path,
    mode: str,
    expected_binary_sha256: str | None,
) -> list[dict[str, Any]]:
    if payload.get("schema") != SCRIPTSTRUCT_INVENTORY_PACK_SCHEMA:
        return []
    blockers: list[dict[str, Any]] = []
    if payload.get("status") != "candidate-only":
        blockers.append({"reason": "scriptstruct_inventory_status_not_candidate_only", "label": f"{label}:$.status"})
    if payload.get("promotion_status") != "not_promoted_candidate_only":
        blockers.append({"reason": "scriptstruct_inventory_promotion_status_mismatch", "label": f"{label}:$.promotion_status"})
    binary = payload.get("binary")
    if not isinstance(binary, dict) or not isinstance(binary.get("sha256"), str) or SHA256_RE.fullmatch(binary["sha256"]) is None:
        blockers.append({"reason": "scriptstruct_inventory_binary_sha256_invalid", "label": f"{label}:$.binary.sha256"})
    elif expected_binary_sha256 is not None and binary["sha256"] != expected_binary_sha256:
        blockers.append(
            {
                "reason": "scriptstruct_inventory_binary_sha256_mismatch",
                "label": f"{label}:$.binary.sha256",
                "expected": expected_binary_sha256,
                "recorded": binary["sha256"],
            }
        )
    core = payload.get("core")
    if not isinstance(core, dict) or not isinstance(core.get("sha256"), str) or SHA256_RE.fullmatch(core["sha256"]) is None:
        blockers.append({"reason": "scriptstruct_inventory_core_sha256_invalid", "label": f"{label}:$.core.sha256"})
    artifact_identity = payload.get("artifact_identity")
    if not isinstance(artifact_identity, dict) or artifact_identity.get("artifact_sha256") != (core or {}).get("sha256"):
        blockers.append({"reason": "scriptstruct_inventory_artifact_identity_mismatch", "label": f"{label}:$.artifact_identity"})
    artifacts = payload.get("artifacts")
    summary = payload.get("summary")
    if not isinstance(summary, dict) or not is_json_int(summary.get("scriptstruct_count")):
        blockers.append({"reason": "scriptstruct_inventory_summary_invalid", "label": f"{label}:$.summary.scriptstruct_count"})
        summary_count = None
    else:
        summary_count = int(summary["scriptstruct_count"])
    if not isinstance(artifacts, dict):
        blockers.append({"reason": "scriptstruct_inventory_artifacts_missing", "label": f"{label}:$.artifacts"})
    else:
        blockers.extend(
            validate_scriptstruct_inventory_child_artifact(
                artifacts,
                "scriptstruct_inventory",
                label=label,
                manifest_path=manifest_path,
                workspace_root=workspace_root,
                protected_root=protected_root,
                expected_schema="obelisk.scriptstruct-inventory.v1",
                summary_count=summary_count,
            )
        )
        blockers.extend(
            validate_scriptstruct_inventory_child_artifact(
                artifacts,
                "fname_root_validation",
                label=label,
                manifest_path=manifest_path,
                workspace_root=workspace_root,
                protected_root=protected_root,
                expected_schema="obelisk.core-fname-root-validation.v1",
            )
        )
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_SCRIPTSTRUCT_INVENTORY_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "scriptstruct_inventory_non_claims_missing",
                "label": f"{label}:$.non_claims",
                "expected": sorted(REQUIRED_SCRIPTSTRUCT_INVENTORY_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    if mode == "promote":
        blockers.append({"reason": "promote_mode_scriptstruct_inventory_candidate_only", "label": label})
    return blockers


def validate_gobjects_two_core_manifest(payload: dict[str, Any], *, label: str, mode: str) -> list[dict[str, Any]]:
    if payload.get("schema") != GOBJECTS_TWO_CORE_MANIFEST_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    core_count = payload.get("core_count")
    cores = payload.get("cores")
    sample_set = payload.get("sample_set")
    blocked_contracts = payload.get("blocked_contracts")
    non_claims = payload.get("non_claims")

    if not is_json_int(core_count) or core_count < 2:
        blockers.append({"reason": "gobjects_two_core_manifest_core_count_invalid", "label": label})
    if not isinstance(cores, list) or not cores:
        blockers.append({"reason": "gobjects_two_core_manifest_missing_cores", "label": label})
        cores = []
    elif isinstance(core_count, int) and not isinstance(core_count, bool) and len(cores) != core_count:
        blockers.append({"reason": "gobjects_two_core_manifest_core_count_mismatch", "label": label})

    if not isinstance(sample_set, list) or not sample_set:
        blockers.append({"reason": "gobjects_two_core_manifest_missing_sample_set", "label": label})
        expected_sample_count = None
    else:
        expected_sample_count = len(sample_set)
        for index, sample in enumerate(sample_set):
            if not isinstance(sample, dict) or not isinstance(sample.get("label"), str) or not is_json_int(sample.get("index")):
                blockers.append(
                    {
                        "reason": "gobjects_two_core_manifest_sample_set_entry_invalid",
                        "label": f"{label}:$.sample_set[{index}]",
                    }
                )

    seen_roles: set[str] = set()
    for index, core in enumerate(cores):
        core_label = f"{label}:$.cores[{index}]"
        if not isinstance(core, dict):
            blockers.append({"reason": "gobjects_two_core_manifest_core_entry_invalid", "label": core_label})
            continue
        role = core.get("role")
        if not isinstance(role, str) or not role:
            blockers.append({"reason": "gobjects_two_core_manifest_core_role_invalid", "label": core_label})
        elif role in seen_roles:
            blockers.append({"reason": "gobjects_two_core_manifest_duplicate_core_role", "label": core_label})
        else:
            seen_roles.add(role)
        if expected_sample_count is not None:
            expected_values = {
                "sample_count": expected_sample_count,
                "accepted_count": expected_sample_count,
                "membership_pass_count": expected_sample_count,
                "rejected_count": 0,
            }
            for key, expected in expected_values.items():
                if core.get(key) != expected:
                    blockers.append(
                        {
                            "reason": "gobjects_two_core_manifest_core_summary_mismatch",
                            "label": f"{core_label}.{key}",
                            "expected": expected,
                            "observed": core.get(key),
                        }
                    )

    if payload.get("offline_only") is not True:
        blockers.append({"reason": "gobjects_two_core_manifest_not_offline_only", "label": label})
    if payload.get("ufunction_inventory_input_ready") is not True:
        blockers.append({"reason": "gobjects_two_core_manifest_not_input_ready", "label": label})
    if payload.get("public_gobjects_promotion_ready") is not False:
        blockers.append({"reason": "gobjects_two_core_manifest_public_promotion_not_false", "label": label})
    if not isinstance(blocked_contracts, list) or not REQUIRED_GOBJECTS_TWO_CORE_BLOCKED_CONTRACTS.issubset(set(blocked_contracts)):
        blockers.append({"reason": "gobjects_two_core_manifest_missing_blocked_contracts", "label": label})
    if not isinstance(non_claims, list) or len(non_claims) < 3:
        blockers.append({"reason": "gobjects_two_core_manifest_missing_non_claims", "label": label})
    if mode == "promote":
        blockers.append({"reason": "gobjects_two_core_manifest_promote_mode_blocked", "label": label})

    return blockers


def validate_readiness_report_manifest(payload: dict[str, Any], *, label: str, mode: str) -> list[dict[str, Any]]:
    if payload.get("schema") != READINESS_REPORT_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    promotion_gate = payload.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        blockers.append({"reason": "readiness_report_missing_promotion_gate", "label": label})
        return blockers

    if payload.get("gate_mode") != "second_source_promotion":
        blockers.append({"reason": "readiness_report_gate_mode_not_second_source_promotion", "label": label})
    target_sets = payload.get("target_sets")
    if not isinstance(target_sets, list) or any(not isinstance(item, str) or not item for item in target_sets):
        blockers.append({"reason": "readiness_report_target_sets_invalid", "label": f"{label}:$.target_sets"})
    elif not target_sets:
        blockers.append({"reason": "readiness_report_missing_target_sets", "label": f"{label}:$.target_sets"})

    if promotion_gate.get("ready") is True:
        if promotion_gate.get("ready_scope") != "layout_only":
            blockers.append({"reason": "readiness_report_ready_scope_not_layout_only", "label": label})
        if promotion_gate.get("layout_ready") is not True:
            blockers.append({"reason": "readiness_report_layout_ready_not_true", "label": label})
        if promotion_gate.get("promotion_ready") is not False:
            blockers.append({"reason": "readiness_report_promotion_ready_not_false", "label": label})
        if payload.get("evidence_scope") != "second_source_layout_evidence_only":
            blockers.append({"reason": "readiness_report_evidence_scope_not_layout_only", "label": label})
        surfaces = payload.get("not_promoted_surfaces")
        if not isinstance(surfaces, list) or set(surfaces) != REQUIRED_READINESS_NON_PROMOTED_SURFACES:
            blockers.append({"reason": "readiness_report_missing_non_promoted_surfaces", "label": label})
        if mode == "promote":
            blockers.append({"reason": "promote_mode_readiness_report_layout_only", "label": label})
    return blockers


def validate_item_return_only_policy_slice_manifest(payload: dict[str, Any], *, label: str, mode: str) -> list[dict[str, Any]]:
    if payload.get("schema") != ITEM_RETURN_ONLY_POLICY_SLICE_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    safety_summary = payload.get("safety_summary")
    if not isinstance(safety_summary, dict):
        blockers.append({"reason": "item_return_policy_safety_summary_missing", "label": f"{label}:$.safety_summary"})
        return blockers

    if payload.get("policy_status") != "evidence-only":
        blockers.append({"reason": "item_return_policy_status_not_evidence_only", "label": f"{label}:$.policy_status"})
    if payload.get("snapshot_root") != "redacted":
        blockers.append({"reason": "item_return_policy_snapshot_root_not_redacted", "label": f"{label}:$.snapshot_root"})
    if payload.get("input_target_set") != "item-compact-intake":
        blockers.append({"reason": "item_return_policy_input_target_set_mismatch", "label": f"{label}:$.input_target_set"})
    if payload.get("output_target_set") != "item-return-only-policy-slice":
        blockers.append({"reason": "item_return_policy_output_target_set_mismatch", "label": f"{label}:$.output_target_set"})
    if payload.get("missing_targets") != []:
        blockers.append({"reason": "item_return_policy_missing_targets_present", "label": f"{label}:$.missing_targets"})

    generated_from = payload.get("generated_from")
    if not isinstance(generated_from, dict):
        blockers.append({"reason": "item_return_policy_generated_from_missing", "label": f"{label}:$.generated_from"})
    else:
        if generated_from.get("snapshot_schema") != RC_UFUNCTION_SNAPSHOT_SCHEMA:
            blockers.append({"reason": "item_return_policy_snapshot_schema_mismatch", "label": f"{label}:$.generated_from.snapshot_schema"})
        input_snapshots = generated_from.get("input_snapshots")
        if not isinstance(input_snapshots, list) or len(input_snapshots) != 4:
            blockers.append({"reason": "item_return_policy_input_snapshot_count_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})
        else:
            seen_snapshot_ids: set[str] = set()
            for index, snapshot in enumerate(input_snapshots):
                snapshot_label = f"{label}:$.generated_from.input_snapshots[{index}]"
                if not isinstance(snapshot, dict):
                    blockers.append({"reason": "item_return_policy_input_snapshot_entry_invalid", "label": snapshot_label})
                    continue
                snapshot_id = snapshot.get("id")
                snapshot_sha256 = snapshot.get("sha256")
                if not isinstance(snapshot_id, str) or not snapshot_id or snapshot_id in seen_snapshot_ids:
                    blockers.append({"reason": "item_return_policy_input_snapshot_id_invalid", "label": f"{snapshot_label}.id"})
                else:
                    seen_snapshot_ids.add(snapshot_id)
                if not isinstance(snapshot_sha256, str) or SHA256_RE.fullmatch(snapshot_sha256) is None:
                    blockers.append({"reason": "item_return_policy_input_snapshot_sha256_invalid", "label": f"{snapshot_label}.sha256"})

    if safety_summary.get("artifact_status") != "evidence_only":
        blockers.append({"reason": "item_return_policy_artifact_status_not_evidence_only", "label": f"{label}:$.safety_summary.artifact_status"})
    if safety_summary.get("intended_use") != "offline_review_only":
        blockers.append({"reason": "item_return_policy_intended_use_not_offline_review_only", "label": f"{label}:$.safety_summary.intended_use"})
    if safety_summary.get("promotion_ready") is not False:
        blockers.append({"reason": "item_return_policy_promotion_ready_not_false", "label": f"{label}:$.safety_summary.promotion_ready"})
    if safety_summary.get("copied_bool_count") != 3:
        blockers.append({"reason": "item_return_policy_copied_bool_count_not_three", "label": f"{label}:$.safety_summary.copied_bool_count"})
    if safety_summary.get("excluded_field_count") != 5:
        blockers.append({"reason": "item_return_policy_excluded_field_count_not_five", "label": f"{label}:$.safety_summary.excluded_field_count"})

    copied_bools = payload.get("copied_return_bools")
    if not isinstance(copied_bools, list) or len(copied_bools) != 3:
        blockers.append({"reason": "item_return_policy_copied_return_bools_count_mismatch", "label": f"{label}:$.copied_return_bools"})
    else:
        copied_field_values = [entry.get("copied_field") for entry in copied_bools if isinstance(entry, dict)]
        copied_fields = {field for field in copied_field_values if isinstance(field, str)}
        if copied_fields != REQUIRED_ITEM_RETURN_ONLY_COPIED_FIELDS:
            blockers.append(
                {
                    "reason": "item_return_policy_copied_fields_mismatch",
                    "label": f"{label}:$.copied_return_bools",
                    "expected": sorted(REQUIRED_ITEM_RETURN_ONLY_COPIED_FIELDS),
                    "recorded": sorted(field for field in copied_fields if isinstance(field, str)),
                }
            )
        for index, entry in enumerate(copied_bools):
            entry_label = f"{label}:$.copied_return_bools[{index}]"
            if not isinstance(entry, dict):
                blockers.append({"reason": "item_return_policy_copied_bool_entry_invalid", "label": entry_label})
                continue
            copied_field = entry.get("copied_field")
            expected_target = copied_field.rsplit(".", 1)[0] if isinstance(copied_field, str) and "." in copied_field else None
            if entry.get("target") != expected_target:
                blockers.append({"reason": "item_return_policy_copied_bool_target_mismatch", "label": entry_label})
            if entry.get("field") != "ReturnValue" or entry.get("direction") != "return" or entry.get("type") != "bool":
                blockers.append({"reason": "item_return_policy_copied_bool_not_return_bool", "label": entry_label})
            if entry.get("evidence_status") != "copied-return-bool-only":
                blockers.append({"reason": "item_return_policy_copied_bool_evidence_status_mismatch", "label": entry_label})

    excluded_entries = payload.get("excluded_fields")
    if not isinstance(excluded_entries, list) or len(excluded_entries) != 5:
        blockers.append({"reason": "item_return_policy_excluded_fields_count_mismatch", "label": f"{label}:$.excluded_fields"})
    else:
        excluded_field_values = [entry.get("excluded_field") for entry in excluded_entries if isinstance(entry, dict)]
        excluded_fields = {field for field in excluded_field_values if isinstance(field, str)}
        if excluded_fields != REQUIRED_ITEM_RETURN_ONLY_EXCLUDED_FIELDS:
            blockers.append(
                {
                    "reason": "item_return_policy_excluded_fields_mismatch",
                    "label": f"{label}:$.excluded_fields",
                    "expected": sorted(REQUIRED_ITEM_RETURN_ONLY_EXCLUDED_FIELDS),
                    "recorded": sorted(field for field in excluded_fields if isinstance(field, str)),
                }
            )

    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        blockers.append({"reason": "item_return_policy_coverage_missing", "label": f"{label}:$.coverage"})
    else:
        if coverage.get("status") != "complete":
            blockers.append({"reason": "item_return_policy_coverage_not_complete", "label": f"{label}:$.coverage.status"})
        coverage_copied_fields = coverage.get("copied_fields")
        if (
            not isinstance(coverage_copied_fields, list)
            or any(not isinstance(field, str) for field in coverage_copied_fields)
            or set(coverage_copied_fields) != REQUIRED_ITEM_RETURN_ONLY_COPIED_FIELDS
        ):
            blockers.append({"reason": "item_return_policy_coverage_copied_fields_mismatch", "label": f"{label}:$.coverage.copied_fields"})
        coverage_copied_targets = coverage.get("copied_targets")
        if (
            not isinstance(coverage_copied_targets, list)
            or any(not isinstance(target, str) for target in coverage_copied_targets)
            or set(coverage_copied_targets) != REQUIRED_ITEM_RETURN_ONLY_COPIED_TARGETS
        ):
            blockers.append({"reason": "item_return_policy_coverage_copied_targets_mismatch", "label": f"{label}:$.coverage.copied_targets"})
        coverage_excluded_fields = coverage.get("excluded_fields")
        if (
            not isinstance(coverage_excluded_fields, list)
            or any(not isinstance(field, str) for field in coverage_excluded_fields)
            or set(coverage_excluded_fields) != REQUIRED_ITEM_RETURN_ONLY_EXCLUDED_FIELDS
        ):
            blockers.append({"reason": "item_return_policy_coverage_excluded_fields_mismatch", "label": f"{label}:$.coverage.excluded_fields"})
        coverage_input_targets = coverage.get("input_targets")
        if (
            not isinstance(coverage_input_targets, list)
            or any(not isinstance(target, str) for target in coverage_input_targets)
            or set(coverage_input_targets) != REQUIRED_ITEM_RETURN_ONLY_INPUT_TARGETS
        ):
            blockers.append({"reason": "item_return_policy_coverage_input_targets_mismatch", "label": f"{label}:$.coverage.input_targets"})

    non_claims = payload.get("non_claims")
    if (
        not isinstance(non_claims, list)
        or any(not isinstance(non_claim, str) for non_claim in non_claims)
        or not REQUIRED_ITEM_RETURN_ONLY_NON_CLAIMS.issubset(set(non_claims))
    ):
        blockers.append(
            {
                "reason": "item_return_policy_non_claims_missing_required_boundaries",
                "label": f"{label}:$.non_claims",
                "expected": sorted(REQUIRED_ITEM_RETURN_ONLY_NON_CLAIMS),
            }
        )

    explicitly_excluded = safety_summary.get("explicitly_excluded")
    if (
        not isinstance(explicitly_excluded, list)
        or any(not isinstance(exclusion, str) for exclusion in explicitly_excluded)
        or not REQUIRED_ITEM_RETURN_ONLY_EXPLICIT_EXCLUSIONS.issubset(set(explicitly_excluded))
    ):
        blockers.append(
            {
                "reason": "item_return_policy_explicit_exclusions_missing_internal_boundaries",
                "label": f"{label}:$.safety_summary.explicitly_excluded",
                "expected": sorted(REQUIRED_ITEM_RETURN_ONLY_EXPLICIT_EXCLUSIONS),
            }
        )

    if mode == "promote":
        blockers.append({"reason": "promote_mode_item_return_policy_slice_evidence_only", "label": label})
    for trail, _ in collect_ready_overclaims(payload):
        blockers.append({"reason": "item_return_policy_readiness_overclaim", "label": f"{label}:{trail}"})
    for trail, _, reason in collect_candidate_public_overclaims(
        payload,
        allowed_prefixes=(
            "$.non_claims",
            "$.safety_summary.explicitly_excluded",
        ),
    ):
        blockers.append({"reason": f"item_return_policy_public_overclaim_{reason}", "label": f"{label}:{trail}"})

    return blockers


def validate_transfer_baccept_only_policy_slice_manifest(payload: dict[str, Any], *, label: str, mode: str) -> list[dict[str, Any]]:
    if payload.get("schema") != TRANSFER_BACCEPT_ONLY_POLICY_SLICE_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    safety_summary = payload.get("safety_summary")
    if not isinstance(safety_summary, dict):
        blockers.append({"reason": "transfer_baccept_policy_safety_summary_missing", "label": f"{label}:$.safety_summary"})
        return blockers

    if payload.get("policy_status") != "evidence-only":
        blockers.append({"reason": "transfer_baccept_policy_status_not_evidence_only", "label": f"{label}:$.policy_status"})
    if payload.get("snapshot_root") != "redacted":
        blockers.append({"reason": "transfer_baccept_policy_snapshot_root_not_redacted", "label": f"{label}:$.snapshot_root"})
    if payload.get("input_target_set") != "transfer-ufunction-intake":
        blockers.append({"reason": "transfer_baccept_policy_input_target_set_mismatch", "label": f"{label}:$.input_target_set"})
    if payload.get("output_target_set") != "transfer-baccept-only-policy-slice":
        blockers.append({"reason": "transfer_baccept_policy_output_target_set_mismatch", "label": f"{label}:$.output_target_set"})
    if payload.get("missing_targets") != []:
        blockers.append({"reason": "transfer_baccept_policy_missing_targets_present", "label": f"{label}:$.missing_targets"})

    input_snapshot_sources: dict[str, dict[str, str]] = {}
    generated_from = payload.get("generated_from")
    if not isinstance(generated_from, dict):
        blockers.append({"reason": "transfer_baccept_policy_generated_from_missing", "label": f"{label}:$.generated_from"})
    else:
        if generated_from.get("snapshot_schema") != RC_UFUNCTION_SNAPSHOT_SCHEMA:
            blockers.append({"reason": "transfer_baccept_policy_snapshot_schema_mismatch", "label": f"{label}:$.generated_from.snapshot_schema"})
        input_snapshots = generated_from.get("input_snapshots")
        if not isinstance(input_snapshots, list) or len(input_snapshots) != len(REQUIRED_TRANSFER_BACCEPT_ONLY_INPUT_TARGETS):
            blockers.append({"reason": "transfer_baccept_policy_input_snapshot_count_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})
        else:
            for index, snapshot in enumerate(input_snapshots):
                snapshot_label = f"{label}:$.generated_from.input_snapshots[{index}]"
                if not isinstance(snapshot, dict):
                    blockers.append({"reason": "transfer_baccept_policy_input_snapshot_entry_invalid", "label": snapshot_label})
                    continue
                snapshot_id = snapshot.get("id")
                snapshot_sha256 = snapshot.get("sha256")
                if not isinstance(snapshot_id, str) or not snapshot_id:
                    blockers.append({"reason": "transfer_baccept_policy_input_snapshot_id_invalid", "label": f"{snapshot_label}.id"})
                    continue
                if snapshot_id in input_snapshot_sources:
                    blockers.append({"reason": "transfer_baccept_policy_input_snapshot_id_duplicate", "label": f"{snapshot_label}.id"})
                if not isinstance(snapshot_sha256, str) or SHA256_RE.fullmatch(snapshot_sha256) is None:
                    blockers.append({"reason": "transfer_baccept_policy_input_snapshot_sha256_invalid", "label": f"{snapshot_label}.sha256"})
                    continue
                snapshot_target = snapshot.get("target")
                if not isinstance(snapshot_target, str) or snapshot_target not in REQUIRED_TRANSFER_BACCEPT_ONLY_INPUT_TARGETS:
                    blockers.append({"reason": "transfer_baccept_policy_input_snapshot_target_invalid", "label": f"{snapshot_label}.target"})
                    continue
                input_snapshot_sources[snapshot_id] = {"sha256": snapshot_sha256, "target": snapshot_target}
            if {entry["target"] for entry in input_snapshot_sources.values()} != REQUIRED_TRANSFER_BACCEPT_ONLY_INPUT_TARGETS:
                blockers.append({"reason": "transfer_baccept_policy_input_snapshot_targets_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})

    if safety_summary.get("artifact_status") != "evidence_only":
        blockers.append({"reason": "transfer_baccept_policy_artifact_status_not_evidence_only", "label": f"{label}:$.safety_summary.artifact_status"})
    if safety_summary.get("intended_use") != "offline_review_only":
        blockers.append({"reason": "transfer_baccept_policy_intended_use_not_offline_review_only", "label": f"{label}:$.safety_summary.intended_use"})
    if safety_summary.get("promotion_ready") is not False:
        blockers.append({"reason": "transfer_baccept_policy_promotion_ready_not_false", "label": f"{label}:$.safety_summary.promotion_ready"})
    if safety_summary.get("copied_bool_count") != 1:
        blockers.append({"reason": "transfer_baccept_policy_copied_bool_count_not_one", "label": f"{label}:$.safety_summary.copied_bool_count"})
    if safety_summary.get("forbidden_field_count") != len(REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS):
        blockers.append({"reason": "transfer_baccept_policy_forbidden_field_count_mismatch", "label": f"{label}:$.safety_summary.forbidden_field_count"})

    copied_bool = payload.get("copied_bool")
    if not isinstance(copied_bool, dict):
        blockers.append({"reason": "transfer_baccept_policy_copied_bool_missing", "label": f"{label}:$.copied_bool"})
    else:
        copied_field = copied_bool.get("copied_field")
        if copied_field != REQUIRED_TRANSFER_BACCEPT_ONLY_COPIED_FIELD:
            blockers.append(
                {
                    "reason": "transfer_baccept_policy_copied_field_mismatch",
                    "label": f"{label}:$.copied_bool.copied_field",
                    "expected": REQUIRED_TRANSFER_BACCEPT_ONLY_COPIED_FIELD,
                    "recorded": copied_field,
                }
            )
        if copied_bool.get("target") != REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET:
            blockers.append({"reason": "transfer_baccept_policy_copied_bool_target_mismatch", "label": f"{label}:$.copied_bool.target"})
        if copied_bool.get("field") != "bAccept" or copied_bool.get("direction") != "in" or copied_bool.get("type") != "bool":
            blockers.append({"reason": "transfer_baccept_policy_copied_bool_not_input_bool", "label": f"{label}:$.copied_bool"})
        if copied_bool.get("evidence_status") != "copied-bool-only":
            blockers.append({"reason": "transfer_baccept_policy_copied_bool_evidence_status_mismatch", "label": f"{label}:$.copied_bool.evidence_status"})
        expected_shape = {
            "function_flags": "0x220cc0",
            "num_parms": 1,
            "parms_size": 1,
            "return_value_offset": "0xffff",
            "property_class": "BoolProperty",
            "offset": "0x0",
            "offset_internal": 0,
            "element_size": 1,
            "array_dim": 1,
            "byte_mask": "0x01",
            "field_mask": "0xff",
            "native_bool": False,
            "property_flags": "0x1040000280",
        }
        for key, expected in expected_shape.items():
            if copied_bool.get(key) != expected:
                blockers.append(
                    {
                        "reason": "transfer_baccept_policy_copied_bool_shape_mismatch",
                        "label": f"{label}:$.copied_bool.{key}",
                        "expected": expected,
                        "recorded": copied_bool.get(key),
                    }
                )
        source_snapshot = copied_bool.get("source_snapshot")
        source_snapshot_sha256 = copied_bool.get("source_snapshot_sha256")
        if not isinstance(source_snapshot, str) or source_snapshot not in input_snapshot_sources:
            blockers.append({"reason": "transfer_baccept_policy_copied_bool_source_snapshot_unknown", "label": f"{label}:$.copied_bool.source_snapshot"})
        elif source_snapshot_sha256 != input_snapshot_sources[source_snapshot]["sha256"]:
            blockers.append(
                {
                    "reason": "transfer_baccept_policy_copied_bool_source_snapshot_sha256_mismatch",
                    "label": f"{label}:$.copied_bool.source_snapshot_sha256",
                    "expected": input_snapshot_sources[source_snapshot]["sha256"],
                    "recorded": source_snapshot_sha256,
                }
            )
        elif copied_bool.get("target") != input_snapshot_sources[source_snapshot]["target"]:
            blockers.append({"reason": "transfer_baccept_policy_copied_bool_source_snapshot_target_mismatch", "label": f"{label}:$.copied_bool.source_snapshot"})

    forbidden_entries = payload.get("forbidden_transfer_fields")
    if not isinstance(forbidden_entries, list) or len(forbidden_entries) != len(REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS):
        blockers.append({"reason": "transfer_baccept_policy_forbidden_fields_count_mismatch", "label": f"{label}:$.forbidden_transfer_fields"})
    else:
        forbidden_field_values = [entry.get("forbidden_field") for entry in forbidden_entries if isinstance(entry, dict)]
        forbidden_fields = {field for field in forbidden_field_values if isinstance(field, str)}
        if forbidden_fields != REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS:
            blockers.append(
                {
                    "reason": "transfer_baccept_policy_forbidden_fields_mismatch",
                    "label": f"{label}:$.forbidden_transfer_fields",
                    "expected": sorted(REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS),
                    "recorded": sorted(field for field in forbidden_fields if isinstance(field, str)),
                }
            )
        for index, entry in enumerate(forbidden_entries):
            entry_label = f"{label}:$.forbidden_transfer_fields[{index}]"
            if not isinstance(entry, dict):
                blockers.append({"reason": "transfer_baccept_policy_forbidden_field_entry_invalid", "label": entry_label})
                continue
            forbidden_field = entry.get("forbidden_field")
            target = entry.get("target")
            field = entry.get("field")
            if (
                not isinstance(forbidden_field, str)
                or forbidden_field not in REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS
                or not isinstance(target, str)
                or not isinstance(field, str)
                or forbidden_field != f"{target}.{field}"
            ):
                blockers.append({"reason": "transfer_baccept_policy_forbidden_field_identity_mismatch", "label": entry_label})
            if not isinstance(entry.get("reason"), str) or not entry.get("reason"):
                blockers.append({"reason": "transfer_baccept_policy_forbidden_field_reason_invalid", "label": f"{entry_label}.reason"})
            forbidden_expected_shape = {
                "PrimalDinoCharacter.IsAllowedToTransfer.WorldContextObject": {
                    "property_class": "ObjectProperty",
                    "offset": "0x0",
                    "offset_internal": 0,
                    "element_size": 8,
                    "array_dim": 1,
                    "property_flags": "0x1040000280",
                },
                "PrimalDinoCharacter.IsAllowedToTransfer.ReturnValue": {
                    "property_class": "BoolProperty",
                    "offset": "0x8",
                    "offset_internal": 8,
                    "element_size": 1,
                    "array_dim": 1,
                    "property_flags": "0x1040000780",
                },
                "ShooterGameState.AllowDownloadDino.TheDinoClass": {
                    "property_class": "ClassProperty",
                    "offset": "0x0",
                    "offset_internal": 0,
                    "element_size": 8,
                    "array_dim": 1,
                    "property_flags": "0x1040000280",
                },
                "ShooterGameState.AllowDownloadDino.ReturnValue": {
                    "property_class": "BoolProperty",
                    "offset": "0x8",
                    "offset_internal": 8,
                    "element_size": 1,
                    "array_dim": 1,
                    "property_flags": "0x1040000780",
                },
                "ShooterPlayerController.ServerDownloadTransferredPlayer.SpawnPointID": {
                    "property_class": "IntProperty",
                    "offset": "0x0",
                    "offset_internal": 0,
                    "element_size": 4,
                    "array_dim": 1,
                    "property_flags": "0x1040000280",
                },
                "ShooterPlayerController.ServerDownloadTransferredPlayer.spawnPointRegionIndex": {
                    "property_class": "IntProperty",
                    "offset": "0x4",
                    "offset_internal": 4,
                    "element_size": 4,
                    "array_dim": 1,
                    "property_flags": "0x1040000280",
                },
                "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.IgnoreBedID": {
                    "property_class": "IntProperty",
                    "offset": "0x8",
                    "offset_internal": 8,
                    "element_size": 4,
                    "array_dim": 1,
                    "property_flags": "0x1040000280",
                },
                "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.PlayerDataID": {
                    "property_class": "UInt64Property",
                    "offset": "0x0",
                    "offset_internal": 0,
                    "element_size": 8,
                    "array_dim": 1,
                    "property_flags": "0x1040000280",
                },
                "ShooterPlayerController.ServerUploadCurrentCharacterAndItems.InventoryComp": {
                    "property_class": "ObjectProperty",
                    "offset": "0x0",
                    "offset_internal": 0,
                    "element_size": 8,
                    "array_dim": 1,
                    "property_flags": "0x1044080280",
                },
                "ShooterPlayerController.ServerUploadDino.DownloadedDino": {
                    "property_class": "ObjectProperty",
                    "offset": "0x0",
                    "offset_internal": 0,
                    "element_size": 8,
                    "array_dim": 1,
                    "property_flags": "0x1040000280",
                },
            }.get(forbidden_field)
            if forbidden_expected_shape is None:
                blockers.append({"reason": "transfer_baccept_policy_forbidden_field_shape_unknown", "label": entry_label})
            else:
                for key, expected in forbidden_expected_shape.items():
                    if entry.get(key) != expected:
                        blockers.append(
                            {
                                "reason": "transfer_baccept_policy_forbidden_field_shape_mismatch",
                                "label": f"{entry_label}.{key}",
                                "expected": expected,
                                "recorded": entry.get(key),
                            }
                        )
            source_snapshot = entry.get("source_snapshot")
            source_snapshot_sha256 = entry.get("source_snapshot_sha256")
            if not isinstance(source_snapshot, str) or source_snapshot not in input_snapshot_sources:
                blockers.append({"reason": "transfer_baccept_policy_forbidden_field_source_snapshot_unknown", "label": f"{entry_label}.source_snapshot"})
            elif source_snapshot_sha256 != input_snapshot_sources[source_snapshot]["sha256"]:
                blockers.append(
                    {
                        "reason": "transfer_baccept_policy_forbidden_field_source_snapshot_sha256_mismatch",
                        "label": f"{entry_label}.source_snapshot_sha256",
                        "expected": input_snapshot_sources[source_snapshot]["sha256"],
                        "recorded": source_snapshot_sha256,
                    }
                )
            elif target != input_snapshot_sources[source_snapshot]["target"]:
                blockers.append({"reason": "transfer_baccept_policy_forbidden_field_source_snapshot_target_mismatch", "label": f"{entry_label}.source_snapshot"})

    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        blockers.append({"reason": "transfer_baccept_policy_coverage_missing", "label": f"{label}:$.coverage"})
    else:
        if coverage.get("status") != "complete":
            blockers.append({"reason": "transfer_baccept_policy_coverage_not_complete", "label": f"{label}:$.coverage.status"})
        coverage_copied_fields = coverage.get("copied_fields")
        if (
            not isinstance(coverage_copied_fields, list)
            or any(not isinstance(field, str) for field in coverage_copied_fields)
            or set(coverage_copied_fields) != {REQUIRED_TRANSFER_BACCEPT_ONLY_COPIED_FIELD}
        ):
            blockers.append({"reason": "transfer_baccept_policy_coverage_copied_fields_mismatch", "label": f"{label}:$.coverage.copied_fields"})
        coverage_copied_targets = coverage.get("copied_targets")
        if (
            not isinstance(coverage_copied_targets, list)
            or any(not isinstance(target, str) for target in coverage_copied_targets)
            or set(coverage_copied_targets) != {REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET}
        ):
            blockers.append({"reason": "transfer_baccept_policy_coverage_copied_targets_mismatch", "label": f"{label}:$.coverage.copied_targets"})
        coverage_forbidden_fields = coverage.get("forbidden_fields")
        if (
            not isinstance(coverage_forbidden_fields, list)
            or any(not isinstance(field, str) for field in coverage_forbidden_fields)
            or set(coverage_forbidden_fields) != REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS
        ):
            blockers.append({"reason": "transfer_baccept_policy_coverage_forbidden_fields_mismatch", "label": f"{label}:$.coverage.forbidden_fields"})
        coverage_input_targets = coverage.get("input_targets")
        if (
            not isinstance(coverage_input_targets, list)
            or any(not isinstance(target, str) for target in coverage_input_targets)
            or set(coverage_input_targets) != REQUIRED_TRANSFER_BACCEPT_ONLY_INPUT_TARGETS
        ):
            blockers.append({"reason": "transfer_baccept_policy_coverage_input_targets_mismatch", "label": f"{label}:$.coverage.input_targets"})

    non_claims = payload.get("non_claims")
    if (
        not isinstance(non_claims, list)
        or any(not isinstance(non_claim, str) for non_claim in non_claims)
        or not REQUIRED_TRANSFER_BACCEPT_ONLY_NON_CLAIMS.issubset(set(non_claims))
    ):
        blockers.append(
            {
                "reason": "transfer_baccept_policy_non_claims_missing_required_boundaries",
                "label": f"{label}:$.non_claims",
                "expected": sorted(REQUIRED_TRANSFER_BACCEPT_ONLY_NON_CLAIMS),
            }
        )

    explicitly_excluded = safety_summary.get("explicitly_excluded")
    if (
        not isinstance(explicitly_excluded, list)
        or any(not isinstance(exclusion, str) for exclusion in explicitly_excluded)
        or not REQUIRED_TRANSFER_BACCEPT_ONLY_EXPLICIT_EXCLUSIONS.issubset(set(explicitly_excluded))
    ):
        blockers.append(
            {
                "reason": "transfer_baccept_policy_explicit_exclusions_missing_internal_boundaries",
                "label": f"{label}:$.safety_summary.explicitly_excluded",
                "expected": sorted(REQUIRED_TRANSFER_BACCEPT_ONLY_EXPLICIT_EXCLUSIONS),
            }
        )

    if mode == "promote":
        blockers.append({"reason": "promote_mode_transfer_baccept_policy_slice_evidence_only", "label": label})
    for trail, _ in collect_ready_overclaims(payload):
        blockers.append({"reason": "transfer_baccept_policy_readiness_overclaim", "label": f"{label}:{trail}"})
    transfer_public_runtime_bool_overclaim_keys = {
        "dispatcher_ready",
        "public_api_ready",
        "public_sdk_ready",
        "public_transfer_sdk_ready",
        "runtime_hook_ready",
        "transfer_payload_decoding_ready",
    }
    for trail, value in collect_bool_fields(payload):
        if value is True and trail.rsplit(".", 1)[-1] in transfer_public_runtime_bool_overclaim_keys:
            blockers.append({"reason": "transfer_baccept_policy_readiness_overclaim", "label": f"{label}:{trail}"})
    for trail, _, reason in collect_candidate_public_overclaims(
        payload,
        allowed_prefixes=(
            "$.non_claims",
            "$.safety_summary.explicitly_excluded",
        ),
    ):
        blockers.append({"reason": f"transfer_baccept_policy_public_overclaim_{reason}", "label": f"{label}:{trail}"})

    return blockers


def validate_mission_copied_bool_policy_slice_manifest(payload: dict[str, Any], *, label: str, mode: str) -> list[dict[str, Any]]:
    if payload.get("schema") != MISSION_COPIED_BOOL_POLICY_SLICE_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    safety_summary = payload.get("safety_summary")
    if not isinstance(safety_summary, dict):
        blockers.append({"reason": "mission_copied_bool_policy_safety_summary_missing", "label": f"{label}:$.safety_summary"})
        return blockers

    if payload.get("policy_status") != "evidence-only":
        blockers.append({"reason": "mission_copied_bool_policy_status_not_evidence_only", "label": f"{label}:$.policy_status"})
    if payload.get("snapshot_root") != "redacted":
        blockers.append({"reason": "mission_copied_bool_policy_snapshot_root_not_redacted", "label": f"{label}:$.snapshot_root"})
    if payload.get("input_target_set") != "mission-compact-intake":
        blockers.append({"reason": "mission_copied_bool_policy_input_target_set_mismatch", "label": f"{label}:$.input_target_set"})
    if payload.get("output_target_set") != "mission-copied-bool-policy-slice":
        blockers.append({"reason": "mission_copied_bool_policy_output_target_set_mismatch", "label": f"{label}:$.output_target_set"})
    if payload.get("missing_targets") != []:
        blockers.append({"reason": "mission_copied_bool_policy_missing_targets_present", "label": f"{label}:$.missing_targets"})

    input_snapshot_sources: dict[str, dict[str, str]] = {}
    generated_from = payload.get("generated_from")
    if not isinstance(generated_from, dict):
        blockers.append({"reason": "mission_copied_bool_policy_generated_from_missing", "label": f"{label}:$.generated_from"})
    else:
        if generated_from.get("snapshot_schema") != RC_UFUNCTION_SNAPSHOT_SCHEMA:
            blockers.append({"reason": "mission_copied_bool_policy_snapshot_schema_mismatch", "label": f"{label}:$.generated_from.snapshot_schema"})
        input_snapshots = generated_from.get("input_snapshots")
        if not isinstance(input_snapshots, list) or len(input_snapshots) != len(REQUIRED_MISSION_COPIED_BOOL_INPUT_TARGETS):
            blockers.append({"reason": "mission_copied_bool_policy_input_snapshot_count_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})
        else:
            for index, snapshot in enumerate(input_snapshots):
                snapshot_label = f"{label}:$.generated_from.input_snapshots[{index}]"
                if not isinstance(snapshot, dict):
                    blockers.append({"reason": "mission_copied_bool_policy_input_snapshot_entry_invalid", "label": snapshot_label})
                    continue
                snapshot_id = snapshot.get("id")
                snapshot_sha256 = snapshot.get("sha256")
                snapshot_target = snapshot.get("target")
                if not isinstance(snapshot_id, str) or not snapshot_id:
                    blockers.append({"reason": "mission_copied_bool_policy_input_snapshot_id_invalid", "label": f"{snapshot_label}.id"})
                    continue
                if snapshot_id in input_snapshot_sources:
                    blockers.append({"reason": "mission_copied_bool_policy_input_snapshot_id_duplicate", "label": f"{snapshot_label}.id"})
                if not isinstance(snapshot_sha256, str) or SHA256_RE.fullmatch(snapshot_sha256) is None:
                    blockers.append({"reason": "mission_copied_bool_policy_input_snapshot_sha256_invalid", "label": f"{snapshot_label}.sha256"})
                    continue
                if not isinstance(snapshot_target, str) or snapshot_target not in REQUIRED_MISSION_COPIED_BOOL_INPUT_TARGETS:
                    blockers.append({"reason": "mission_copied_bool_policy_input_snapshot_target_invalid", "label": f"{snapshot_label}.target"})
                    continue
                input_snapshot_sources[snapshot_id] = {"sha256": snapshot_sha256, "target": snapshot_target}
            if {entry["target"] for entry in input_snapshot_sources.values()} != REQUIRED_MISSION_COPIED_BOOL_INPUT_TARGETS:
                blockers.append({"reason": "mission_copied_bool_policy_input_snapshot_targets_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})

    if safety_summary.get("artifact_status") != "evidence_only":
        blockers.append({"reason": "mission_copied_bool_policy_artifact_status_not_evidence_only", "label": f"{label}:$.safety_summary.artifact_status"})
    if safety_summary.get("intended_use") != "offline_review_only":
        blockers.append({"reason": "mission_copied_bool_policy_intended_use_not_offline_review_only", "label": f"{label}:$.safety_summary.intended_use"})
    if safety_summary.get("promotion_ready") is not False:
        blockers.append({"reason": "mission_copied_bool_policy_promotion_ready_not_false", "label": f"{label}:$.safety_summary.promotion_ready"})
    if safety_summary.get("copied_bool_count") != len(REQUIRED_MISSION_COPIED_BOOL_FIELDS):
        blockers.append({"reason": "mission_copied_bool_policy_copied_bool_count_mismatch", "label": f"{label}:$.safety_summary.copied_bool_count"})
    if safety_summary.get("redacted_field_count") != len(REQUIRED_MISSION_COPIED_BOOL_REDACTED_FIELDS):
        blockers.append({"reason": "mission_copied_bool_policy_redacted_field_count_mismatch", "label": f"{label}:$.safety_summary.redacted_field_count"})

    copied_expected_shapes = {
        "MissionType.AddPlayerToMission.bForceAdd": {"target": "MissionType.AddPlayerToMission", "field": "bForceAdd", "direction": "in", "offset": "0x8", "offset_internal": 8, "property_flags": "0x1040000280", "return_value_offset": "0x9"},
        "MissionType.AddPlayerToMission.ReturnValue": {"target": "MissionType.AddPlayerToMission", "field": "ReturnValue", "direction": "return", "offset": "0x9", "offset_internal": 9, "property_flags": "0x1040000780", "return_value_offset": "0x9"},
        "MissionType.BPAllowPlayerToLeaveMission.ReturnValue": {"target": "MissionType.BPAllowPlayerToLeaveMission", "field": "ReturnValue", "direction": "return", "offset": "0x8", "offset_internal": 8, "property_flags": "0x1040000780", "return_value_offset": "0x8"},
        "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent": {"target": "MissionType.BPOnPlayerRemovedFromMission", "field": "bFromMissionCompleteEvent", "direction": "in", "offset": "0x10", "offset_internal": 16, "property_flags": "0x1040000280", "return_value_offset": "0xffff"},
        "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess": {"target": "MissionType.BPOnPlayerRemovedFromMission", "field": "bLastPhaseSuccess", "direction": "in", "offset": "0x11", "offset_internal": 17, "property_flags": "0x1040000280", "return_value_offset": "0xffff"},
    }
    copied_bools = payload.get("copied_bools")
    if not isinstance(copied_bools, list) or len(copied_bools) != len(REQUIRED_MISSION_COPIED_BOOL_FIELDS):
        blockers.append({"reason": "mission_copied_bool_policy_copied_bools_count_mismatch", "label": f"{label}:$.copied_bools"})
    else:
        copied_fields = {entry.get("copied_field") for entry in copied_bools if isinstance(entry, dict)}
        if copied_fields != REQUIRED_MISSION_COPIED_BOOL_FIELDS:
            blockers.append({"reason": "mission_copied_bool_policy_copied_fields_mismatch", "label": f"{label}:$.copied_bools"})
        for index, entry in enumerate(copied_bools):
            entry_label = f"{label}:$.copied_bools[{index}]"
            if not isinstance(entry, dict):
                blockers.append({"reason": "mission_copied_bool_policy_copied_bool_entry_invalid", "label": entry_label})
                continue
            copied_field = entry.get("copied_field")
            expected_shape = copied_expected_shapes.get(copied_field)
            if expected_shape is None:
                blockers.append({"reason": "mission_copied_bool_policy_copied_bool_shape_unknown", "label": entry_label})
            else:
                expected_common = {
                    **expected_shape,
                    "type": "bool",
                    "property_class": "BoolProperty",
                    "bool_field_size": 1,
                    "bool_byte_offset": 0,
                    "element_size": 1,
                    "array_dim": 1,
                    "byte_mask": "0x01",
                    "field_mask": "0xff",
                    "native_bool": False,
                    "evidence_status": "copied-mission-bool-only",
                }
                for key, expected in expected_common.items():
                    if entry.get(key) != expected:
                        blockers.append({"reason": "mission_copied_bool_policy_copied_bool_shape_mismatch", "label": f"{entry_label}.{key}", "expected": expected, "recorded": entry.get(key)})
            source_snapshot = entry.get("source_snapshot")
            source_snapshot_sha256 = entry.get("source_snapshot_sha256")
            if not isinstance(source_snapshot, str) or source_snapshot not in input_snapshot_sources:
                blockers.append({"reason": "mission_copied_bool_policy_copied_bool_source_snapshot_unknown", "label": f"{entry_label}.source_snapshot"})
            elif source_snapshot_sha256 != input_snapshot_sources[source_snapshot]["sha256"]:
                blockers.append({"reason": "mission_copied_bool_policy_copied_bool_source_snapshot_sha256_mismatch", "label": f"{entry_label}.source_snapshot_sha256"})
            elif entry.get("target") != input_snapshot_sources[source_snapshot]["target"]:
                blockers.append({"reason": "mission_copied_bool_policy_copied_bool_source_snapshot_target_mismatch", "label": f"{entry_label}.source_snapshot"})

    redacted_expected_shapes = {
        "MissionType.AddPlayerToMission.PlayerCharacter": {"target": "MissionType.AddPlayerToMission", "field": "PlayerCharacter", "property_class": "ObjectProperty", "offset": "0x0", "offset_internal": 0, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn": {"target": "MissionType.BPAllowPlayerToLeaveMission", "field": "PlayerPawn", "property_class": "ObjectProperty", "offset": "0x0", "offset_internal": 0, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.BPOnPlayerRemovedFromMission.Player": {"target": "MissionType.BPOnPlayerRemovedFromMission", "field": "Player", "property_class": "ObjectProperty", "offset": "0x0", "offset_internal": 0, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.BPOnPlayerRemovedFromMission.Controller": {"target": "MissionType.BPOnPlayerRemovedFromMission", "field": "Controller", "property_class": "ObjectProperty", "offset": "0x8", "offset_internal": 8, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.GetPlayerUsableItems.Character": {"target": "MissionType.GetPlayerUsableItems", "field": "Character", "property_class": "ObjectProperty", "offset": "0x0", "offset_internal": 0, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.GetPlayerUsableItems.OutItemIDs": {"target": "MissionType.GetPlayerUsableItems", "field": "OutItemIDs", "property_class": "ArrayProperty", "offset": "0x8", "offset_internal": 8, "element_size": 16, "array_dim": 1, "property_flags": "0x380"},
    }
    redacted_entries = payload.get("redacted_mission_fields")
    if not isinstance(redacted_entries, list) or len(redacted_entries) != len(REQUIRED_MISSION_COPIED_BOOL_REDACTED_FIELDS):
        blockers.append({"reason": "mission_copied_bool_policy_redacted_fields_count_mismatch", "label": f"{label}:$.redacted_mission_fields"})
    else:
        redacted_fields = {entry.get("redacted_field") for entry in redacted_entries if isinstance(entry, dict)}
        if redacted_fields != REQUIRED_MISSION_COPIED_BOOL_REDACTED_FIELDS:
            blockers.append({"reason": "mission_copied_bool_policy_redacted_fields_mismatch", "label": f"{label}:$.redacted_mission_fields"})
        for index, entry in enumerate(redacted_entries):
            entry_label = f"{label}:$.redacted_mission_fields[{index}]"
            if not isinstance(entry, dict):
                blockers.append({"reason": "mission_copied_bool_policy_redacted_field_entry_invalid", "label": entry_label})
                continue
            redacted_field = entry.get("redacted_field")
            expected_shape = redacted_expected_shapes.get(redacted_field)
            if expected_shape is None:
                blockers.append({"reason": "mission_copied_bool_policy_redacted_field_shape_unknown", "label": entry_label})
            else:
                for key, expected in expected_shape.items():
                    if entry.get(key) != expected:
                        blockers.append({"reason": "mission_copied_bool_policy_redacted_field_shape_mismatch", "label": f"{entry_label}.{key}", "expected": expected, "recorded": entry.get(key)})
            if entry.get("evidence_status") != "recognition-only-redacted":
                blockers.append({"reason": "mission_copied_bool_policy_redacted_field_evidence_status_mismatch", "label": f"{entry_label}.evidence_status"})
            source_snapshot = entry.get("source_snapshot")
            source_snapshot_sha256 = entry.get("source_snapshot_sha256")
            if not isinstance(source_snapshot, str) or source_snapshot not in input_snapshot_sources:
                blockers.append({"reason": "mission_copied_bool_policy_redacted_field_source_snapshot_unknown", "label": f"{entry_label}.source_snapshot"})
            elif source_snapshot_sha256 != input_snapshot_sources[source_snapshot]["sha256"]:
                blockers.append({"reason": "mission_copied_bool_policy_redacted_field_source_snapshot_sha256_mismatch", "label": f"{entry_label}.source_snapshot_sha256"})
            elif entry.get("target") != input_snapshot_sources[source_snapshot]["target"]:
                blockers.append({"reason": "mission_copied_bool_policy_redacted_field_source_snapshot_target_mismatch", "label": f"{entry_label}.source_snapshot"})

    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        blockers.append({"reason": "mission_copied_bool_policy_coverage_missing", "label": f"{label}:$.coverage"})
    else:
        if coverage.get("status") != "complete":
            blockers.append({"reason": "mission_copied_bool_policy_coverage_not_complete", "label": f"{label}:$.coverage.status"})
        if set(coverage.get("input_targets") or []) != REQUIRED_MISSION_COPIED_BOOL_INPUT_TARGETS:
            blockers.append({"reason": "mission_copied_bool_policy_coverage_input_targets_mismatch", "label": f"{label}:$.coverage.input_targets"})
        if set(coverage.get("copied_targets") or []) != REQUIRED_MISSION_COPIED_BOOL_COPIED_TARGETS:
            blockers.append({"reason": "mission_copied_bool_policy_coverage_copied_targets_mismatch", "label": f"{label}:$.coverage.copied_targets"})
        if set(coverage.get("copied_fields") or []) != REQUIRED_MISSION_COPIED_BOOL_FIELDS:
            blockers.append({"reason": "mission_copied_bool_policy_coverage_copied_fields_mismatch", "label": f"{label}:$.coverage.copied_fields"})
        if set(coverage.get("redacted_fields") or []) != REQUIRED_MISSION_COPIED_BOOL_REDACTED_FIELDS:
            blockers.append({"reason": "mission_copied_bool_policy_coverage_redacted_fields_mismatch", "label": f"{label}:$.coverage.redacted_fields"})

    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_MISSION_COPIED_BOOL_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append({"reason": "mission_copied_bool_policy_non_claims_missing_required_boundaries", "label": f"{label}:$.non_claims"})
    explicitly_excluded = safety_summary.get("explicitly_excluded")
    if not isinstance(explicitly_excluded, list) or not REQUIRED_MISSION_COPIED_BOOL_EXPLICIT_EXCLUSIONS.issubset(set(explicitly_excluded)):
        blockers.append({"reason": "mission_copied_bool_policy_explicit_exclusions_missing_internal_boundaries", "label": f"{label}:$.safety_summary.explicitly_excluded"})

    if mode == "promote":
        blockers.append({"reason": "promote_mode_mission_copied_bool_policy_slice_evidence_only", "label": label})
    for trail, _ in collect_ready_overclaims(payload):
        blockers.append({"reason": "mission_copied_bool_policy_readiness_overclaim", "label": f"{label}:{trail}"})
    for trail, value in collect_bool_fields(payload):
        if value is True and trail.rsplit(".", 1)[-1] in {
            "dispatcher_ready",
            "mission_payload_decoding_ready",
            "public_api_ready",
            "public_mission_sdk_ready",
            "public_sdk_ready",
            "runtime_hook_ready",
        }:
            blockers.append({"reason": "mission_copied_bool_policy_readiness_overclaim", "label": f"{label}:{trail}"})
    for trail, _, reason in collect_candidate_public_overclaims(
        payload,
        allowed_prefixes=(
            "$.non_claims",
            "$.safety_summary.explicitly_excluded",
        ),
    ):
        blockers.append({"reason": f"mission_copied_bool_policy_public_overclaim_{reason}", "label": f"{label}:{trail}"})

    return blockers


def validate_structure_return_only_policy_slice_manifest(payload: dict[str, Any], *, label: str, mode: str) -> list[dict[str, Any]]:
    if payload.get("schema") != STRUCTURE_RETURN_ONLY_POLICY_SLICE_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    safety_summary = payload.get("safety_summary")
    if not isinstance(safety_summary, dict):
        blockers.append({"reason": "structure_return_policy_safety_summary_missing", "label": f"{label}:$.safety_summary"})
        return blockers

    if payload.get("policy_status") != "evidence-only":
        blockers.append({"reason": "structure_return_policy_status_not_evidence_only", "label": f"{label}:$.policy_status"})
    if payload.get("snapshot_root") != "redacted":
        blockers.append({"reason": "structure_return_policy_snapshot_root_not_redacted", "label": f"{label}:$.snapshot_root"})
    if payload.get("input_target_set") != "structure-observer-intake":
        blockers.append({"reason": "structure_return_policy_input_target_set_mismatch", "label": f"{label}:$.input_target_set"})
    if payload.get("output_target_set") != "structure-return-only-policy-slice":
        blockers.append({"reason": "structure_return_policy_output_target_set_mismatch", "label": f"{label}:$.output_target_set"})
    if payload.get("missing_targets") != []:
        blockers.append({"reason": "structure_return_policy_missing_targets_present", "label": f"{label}:$.missing_targets"})

    input_snapshot_sources: dict[str, dict[str, str]] = {}
    generated_from = payload.get("generated_from")
    if not isinstance(generated_from, dict):
        blockers.append({"reason": "structure_return_policy_generated_from_missing", "label": f"{label}:$.generated_from"})
    else:
        if generated_from.get("snapshot_schema") != RC_UFUNCTION_SNAPSHOT_SCHEMA:
            blockers.append({"reason": "structure_return_policy_snapshot_schema_mismatch", "label": f"{label}:$.generated_from.snapshot_schema"})
        input_snapshots = generated_from.get("input_snapshots")
        if not isinstance(input_snapshots, list) or len(input_snapshots) != len(REQUIRED_STRUCTURE_RETURN_ONLY_INPUT_TARGETS):
            blockers.append({"reason": "structure_return_policy_input_snapshot_count_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})
        else:
            for index, snapshot in enumerate(input_snapshots):
                snapshot_label = f"{label}:$.generated_from.input_snapshots[{index}]"
                if not isinstance(snapshot, dict):
                    blockers.append({"reason": "structure_return_policy_input_snapshot_entry_invalid", "label": snapshot_label})
                    continue
                snapshot_id = snapshot.get("id")
                snapshot_sha256 = snapshot.get("sha256")
                snapshot_target = snapshot.get("target")
                if not isinstance(snapshot_id, str) or not snapshot_id:
                    blockers.append({"reason": "structure_return_policy_input_snapshot_id_invalid", "label": f"{snapshot_label}.id"})
                    continue
                if snapshot_id in input_snapshot_sources:
                    blockers.append({"reason": "structure_return_policy_input_snapshot_id_duplicate", "label": f"{snapshot_label}.id"})
                if not isinstance(snapshot_sha256, str) or SHA256_RE.fullmatch(snapshot_sha256) is None:
                    blockers.append({"reason": "structure_return_policy_input_snapshot_sha256_invalid", "label": f"{snapshot_label}.sha256"})
                    continue
                if not isinstance(snapshot_target, str) or snapshot_target not in REQUIRED_STRUCTURE_RETURN_ONLY_INPUT_TARGETS:
                    blockers.append({"reason": "structure_return_policy_input_snapshot_target_invalid", "label": f"{snapshot_label}.target"})
                    continue
                input_snapshot_sources[snapshot_id] = {"sha256": snapshot_sha256, "target": snapshot_target}
            if {entry["target"] for entry in input_snapshot_sources.values()} != REQUIRED_STRUCTURE_RETURN_ONLY_INPUT_TARGETS:
                blockers.append({"reason": "structure_return_policy_input_snapshot_targets_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})

    if safety_summary.get("artifact_status") != "evidence_only":
        blockers.append({"reason": "structure_return_policy_artifact_status_not_evidence_only", "label": f"{label}:$.safety_summary.artifact_status"})
    if safety_summary.get("intended_use") != "offline_review_only":
        blockers.append({"reason": "structure_return_policy_intended_use_not_offline_review_only", "label": f"{label}:$.safety_summary.intended_use"})
    if safety_summary.get("promotion_ready") is not False:
        blockers.append({"reason": "structure_return_policy_promotion_ready_not_false", "label": f"{label}:$.safety_summary.promotion_ready"})
    if safety_summary.get("copied_bool_count") != len(REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_FIELDS):
        blockers.append({"reason": "structure_return_policy_copied_bool_count_mismatch", "label": f"{label}:$.safety_summary.copied_bool_count"})
    if safety_summary.get("redacted_field_count") != len(REQUIRED_STRUCTURE_RETURN_ONLY_REDACTED_FIELDS):
        blockers.append({"reason": "structure_return_policy_redacted_field_count_mismatch", "label": f"{label}:$.safety_summary.redacted_field_count"})
    if safety_summary.get("deferred_target_count") != len(REQUIRED_STRUCTURE_RETURN_ONLY_DEFERRED_TARGETS):
        blockers.append({"reason": "structure_return_policy_deferred_target_count_mismatch", "label": f"{label}:$.safety_summary.deferred_target_count"})

    copied_expected_shapes = {
        "PrimalStructure.AllowStructureAccess.ReturnValue": {"target": "PrimalStructure.AllowStructureAccess", "field": "ReturnValue", "offset": "0x8", "offset_internal": 8, "function_flags": "0x4020400"},
        "PrimalStructure.IsAllowedToDemolish.ReturnValue": {"target": "PrimalStructure.IsAllowedToDemolish", "field": "ReturnValue", "offset": "0x8", "offset_internal": 8, "function_flags": "0x4020401"},
    }
    copied_bools = payload.get("copied_return_bools")
    if not isinstance(copied_bools, list) or len(copied_bools) != len(REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_FIELDS):
        blockers.append({"reason": "structure_return_policy_copied_return_bools_count_mismatch", "label": f"{label}:$.copied_return_bools"})
    else:
        copied_fields = {entry.get("copied_field") for entry in copied_bools if isinstance(entry, dict)}
        if copied_fields != REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_FIELDS:
            blockers.append({"reason": "structure_return_policy_copied_fields_mismatch", "label": f"{label}:$.copied_return_bools"})
        for index, entry in enumerate(copied_bools):
            entry_label = f"{label}:$.copied_return_bools[{index}]"
            if not isinstance(entry, dict):
                blockers.append({"reason": "structure_return_policy_copied_bool_entry_invalid", "label": entry_label})
                continue
            copied_field = entry.get("copied_field")
            expected_shape = copied_expected_shapes.get(copied_field)
            if expected_shape is None:
                blockers.append({"reason": "structure_return_policy_copied_bool_shape_unknown", "label": entry_label})
            else:
                expected_common = {
                    **expected_shape,
                    "direction": "return",
                    "type": "bool",
                    "property_class": "BoolProperty",
                    "bool_field_size": 1,
                    "bool_byte_offset": 0,
                    "element_size": 1,
                    "array_dim": 1,
                    "byte_mask": "0x01",
                    "field_mask": "0xff",
                    "native_bool": False,
                    "num_parms": 2,
                    "parms_size": 9,
                    "return_value_offset": "0x8",
                    "property_flags": "0x1040000780",
                    "evidence_status": "copied-structure-return-bool-only",
                }
                for key, expected in expected_common.items():
                    if entry.get(key) != expected:
                        blockers.append({"reason": "structure_return_policy_copied_bool_shape_mismatch", "label": f"{entry_label}.{key}", "expected": expected, "recorded": entry.get(key)})
            source_snapshot = entry.get("source_snapshot")
            source_snapshot_sha256 = entry.get("source_snapshot_sha256")
            if not isinstance(source_snapshot, str) or source_snapshot not in input_snapshot_sources:
                blockers.append({"reason": "structure_return_policy_copied_bool_source_snapshot_unknown", "label": f"{entry_label}.source_snapshot"})
            elif source_snapshot_sha256 != input_snapshot_sources[source_snapshot]["sha256"]:
                blockers.append({"reason": "structure_return_policy_copied_bool_source_snapshot_sha256_mismatch", "label": f"{entry_label}.source_snapshot_sha256"})
            elif entry.get("target") != input_snapshot_sources[source_snapshot]["target"]:
                blockers.append({"reason": "structure_return_policy_copied_bool_source_snapshot_target_mismatch", "label": f"{entry_label}.source_snapshot"})

    redacted_expected_shapes = {
        "PrimalStructure.AllowStructureAccess.ForPC": {"target": "PrimalStructure.AllowStructureAccess", "field": "ForPC", "function_flags": "0x4020400"},
        "PrimalStructure.IsAllowedToDemolish.ForPC": {"target": "PrimalStructure.IsAllowedToDemolish", "field": "ForPC", "function_flags": "0x4020401"},
    }
    redacted_entries = payload.get("redacted_structure_fields")
    if not isinstance(redacted_entries, list) or len(redacted_entries) != len(REQUIRED_STRUCTURE_RETURN_ONLY_REDACTED_FIELDS):
        blockers.append({"reason": "structure_return_policy_redacted_fields_count_mismatch", "label": f"{label}:$.redacted_structure_fields"})
    else:
        redacted_fields = {entry.get("redacted_field") for entry in redacted_entries if isinstance(entry, dict)}
        if redacted_fields != REQUIRED_STRUCTURE_RETURN_ONLY_REDACTED_FIELDS:
            blockers.append({"reason": "structure_return_policy_redacted_fields_mismatch", "label": f"{label}:$.redacted_structure_fields"})
        for index, entry in enumerate(redacted_entries):
            entry_label = f"{label}:$.redacted_structure_fields[{index}]"
            if not isinstance(entry, dict):
                blockers.append({"reason": "structure_return_policy_redacted_field_entry_invalid", "label": entry_label})
                continue
            redacted_field = entry.get("redacted_field")
            expected_shape = redacted_expected_shapes.get(redacted_field)
            expected_common = {
                **(expected_shape or {}),
                "property_class": "ObjectProperty",
                "offset": "0x0",
                "offset_internal": 0,
                "element_size": 8,
                "array_dim": 1,
                "num_parms": 2,
                "parms_size": 9,
                "return_value_offset": "0x8",
                "property_flags": "0x1040000280",
            }
            if expected_shape is None:
                blockers.append({"reason": "structure_return_policy_redacted_field_shape_unknown", "label": entry_label})
            else:
                for key, expected in expected_common.items():
                    if entry.get(key) != expected:
                        blockers.append({"reason": "structure_return_policy_redacted_field_shape_mismatch", "label": f"{entry_label}.{key}", "expected": expected, "recorded": entry.get(key)})
            if entry.get("evidence_status") != "recognition-only-redacted":
                blockers.append({"reason": "structure_return_policy_redacted_field_evidence_status_mismatch", "label": f"{entry_label}.evidence_status"})
            source_snapshot = entry.get("source_snapshot")
            source_snapshot_sha256 = entry.get("source_snapshot_sha256")
            if not isinstance(source_snapshot, str) or source_snapshot not in input_snapshot_sources:
                blockers.append({"reason": "structure_return_policy_redacted_field_source_snapshot_unknown", "label": f"{entry_label}.source_snapshot"})
            elif source_snapshot_sha256 != input_snapshot_sources[source_snapshot]["sha256"]:
                blockers.append({"reason": "structure_return_policy_redacted_field_source_snapshot_sha256_mismatch", "label": f"{entry_label}.source_snapshot_sha256"})
            elif entry.get("target") != input_snapshot_sources[source_snapshot]["target"]:
                blockers.append({"reason": "structure_return_policy_redacted_field_source_snapshot_target_mismatch", "label": f"{entry_label}.source_snapshot"})

    deferred_expected_shapes = {
        "PrimalStructure.SetVariant": {"function_flags": "0x4020401", "num_parms": 3, "parms_size": 6, "return_value_offset": "0x5", "property_count": 3},
        "PrimalStructureItemContainer.AllowToggleActivation": {"function_flags": "0x4020401", "num_parms": 2, "parms_size": 9, "return_value_offset": "0x8", "property_count": 2},
        "PrimalStructureItemContainer.VerifyPinCode": {"function_flags": "0x54020401", "num_parms": 2, "parms_size": 5, "return_value_offset": "0x4", "property_count": 2},
        "PrimalStructureSeating.CanSeat": {"function_flags": "0x4020400", "num_parms": 4, "parms_size": 18, "return_value_offset": "0x11", "property_count": 4},
    }
    deferred_entries = payload.get("deferred_structure_targets")
    if not isinstance(deferred_entries, list) or len(deferred_entries) != len(REQUIRED_STRUCTURE_RETURN_ONLY_DEFERRED_TARGETS):
        blockers.append({"reason": "structure_return_policy_deferred_targets_count_mismatch", "label": f"{label}:$.deferred_structure_targets"})
    else:
        deferred_targets = {entry.get("deferred_target") for entry in deferred_entries if isinstance(entry, dict)}
        if deferred_targets != REQUIRED_STRUCTURE_RETURN_ONLY_DEFERRED_TARGETS:
            blockers.append({"reason": "structure_return_policy_deferred_targets_mismatch", "label": f"{label}:$.deferred_structure_targets"})
        for index, entry in enumerate(deferred_entries):
            entry_label = f"{label}:$.deferred_structure_targets[{index}]"
            if not isinstance(entry, dict):
                blockers.append({"reason": "structure_return_policy_deferred_target_entry_invalid", "label": entry_label})
                continue
            deferred_target = entry.get("deferred_target")
            expected_shape = deferred_expected_shapes.get(deferred_target)
            if expected_shape is None:
                blockers.append({"reason": "structure_return_policy_deferred_target_shape_unknown", "label": entry_label})
            else:
                if entry.get("target") != deferred_target:
                    blockers.append({"reason": "structure_return_policy_deferred_target_mismatch", "label": f"{entry_label}.target"})
                for key, expected in expected_shape.items():
                    if entry.get(key) != expected:
                        blockers.append({"reason": "structure_return_policy_deferred_target_shape_mismatch", "label": f"{entry_label}.{key}", "expected": expected, "recorded": entry.get(key)})
            if entry.get("evidence_status") != "explicitly-deferred-target":
                blockers.append({"reason": "structure_return_policy_deferred_target_evidence_status_mismatch", "label": f"{entry_label}.evidence_status"})
            source_snapshot = entry.get("source_snapshot")
            source_snapshot_sha256 = entry.get("source_snapshot_sha256")
            if not isinstance(source_snapshot, str) or source_snapshot not in input_snapshot_sources:
                blockers.append({"reason": "structure_return_policy_deferred_target_source_snapshot_unknown", "label": f"{entry_label}.source_snapshot"})
            elif source_snapshot_sha256 != input_snapshot_sources[source_snapshot]["sha256"]:
                blockers.append({"reason": "structure_return_policy_deferred_target_source_snapshot_sha256_mismatch", "label": f"{entry_label}.source_snapshot_sha256"})
            elif entry.get("target") != input_snapshot_sources[source_snapshot]["target"]:
                blockers.append({"reason": "structure_return_policy_deferred_target_source_snapshot_target_mismatch", "label": f"{entry_label}.source_snapshot"})

    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        blockers.append({"reason": "structure_return_policy_coverage_missing", "label": f"{label}:$.coverage"})
    else:
        if coverage.get("status") != "complete":
            blockers.append({"reason": "structure_return_policy_coverage_not_complete", "label": f"{label}:$.coverage.status"})
        if set(coverage.get("input_targets") or []) != REQUIRED_STRUCTURE_RETURN_ONLY_INPUT_TARGETS:
            blockers.append({"reason": "structure_return_policy_coverage_input_targets_mismatch", "label": f"{label}:$.coverage.input_targets"})
        if set(coverage.get("copied_targets") or []) != REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_TARGETS:
            blockers.append({"reason": "structure_return_policy_coverage_copied_targets_mismatch", "label": f"{label}:$.coverage.copied_targets"})
        if set(coverage.get("copied_fields") or []) != REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_FIELDS:
            blockers.append({"reason": "structure_return_policy_coverage_copied_fields_mismatch", "label": f"{label}:$.coverage.copied_fields"})
        if set(coverage.get("redacted_fields") or []) != REQUIRED_STRUCTURE_RETURN_ONLY_REDACTED_FIELDS:
            blockers.append({"reason": "structure_return_policy_coverage_redacted_fields_mismatch", "label": f"{label}:$.coverage.redacted_fields"})
        if set(coverage.get("deferred_targets") or []) != REQUIRED_STRUCTURE_RETURN_ONLY_DEFERRED_TARGETS:
            blockers.append({"reason": "structure_return_policy_coverage_deferred_targets_mismatch", "label": f"{label}:$.coverage.deferred_targets"})

    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_STRUCTURE_RETURN_ONLY_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append({"reason": "structure_return_policy_non_claims_missing_required_boundaries", "label": f"{label}:$.non_claims"})
    explicitly_excluded = safety_summary.get("explicitly_excluded")
    if not isinstance(explicitly_excluded, list) or not REQUIRED_STRUCTURE_RETURN_ONLY_EXPLICIT_EXCLUSIONS.issubset(set(explicitly_excluded)):
        blockers.append({"reason": "structure_return_policy_explicit_exclusions_missing_internal_boundaries", "label": f"{label}:$.safety_summary.explicitly_excluded"})

    if mode == "promote":
        blockers.append({"reason": "promote_mode_structure_return_policy_slice_evidence_only", "label": label})
    for trail, _ in collect_ready_overclaims(payload):
        blockers.append({"reason": "structure_return_policy_readiness_overclaim", "label": f"{label}:{trail}"})
    for trail, value in collect_bool_fields(payload):
        if value is True and trail.rsplit(".", 1)[-1] in {
            "dispatcher_ready",
            "identity_ready",
            "lookup_ready",
            "mutation_ready",
            "public_api_ready",
            "public_sdk_ready",
            "public_structure_events_ready",
            "resource_handle_ready",
            "return_override_ready",
            "runtime_hook_ready",
            "structure_events_ready",
        }:
            blockers.append({"reason": "structure_return_policy_readiness_overclaim", "label": f"{label}:{trail}"})
    for trail, _, reason in collect_candidate_public_overclaims(
        payload,
        allowed_prefixes=(
            "$.non_claims",
            "$.safety_summary.explicitly_excluded",
        ),
    ):
        blockers.append({"reason": f"structure_return_policy_public_overclaim_{reason}", "label": f"{label}:{trail}"})
    for trail, raw_value in collect_string_fields(payload):
        if trail.startswith("$.non_claims") or trail.startswith("$.safety_summary.explicitly_excluded"):
            continue
        text = raw_value.casefold()
        if "structureevents" in text or "structure events" in text:
            blockers.append({"reason": "structure_return_policy_public_overclaim_public_structure_events", "label": f"{label}:{trail}"})

    return blockers


def validate_structure_nonpin_copied_scalar_policy_slice_manifest(payload: dict[str, Any], *, label: str, mode: str) -> list[dict[str, Any]]:
    if payload.get("schema") != STRUCTURE_NONPIN_COPIED_SCALAR_POLICY_SLICE_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    safety_summary = payload.get("safety_summary")
    if not isinstance(safety_summary, dict):
        blockers.append({"reason": "structure_nonpin_policy_safety_summary_missing", "label": f"{label}:$.safety_summary"})
        return blockers

    if payload.get("policy_status") != "evidence-only":
        blockers.append({"reason": "structure_nonpin_policy_status_not_evidence_only", "label": f"{label}:$.policy_status"})
    if payload.get("snapshot_root") != "redacted":
        blockers.append({"reason": "structure_nonpin_policy_snapshot_root_not_redacted", "label": f"{label}:$.snapshot_root"})
    if payload.get("input_target_set") != "structure-nonpin-copied-scalar-policy-slice":
        blockers.append({"reason": "structure_nonpin_policy_input_target_set_mismatch", "label": f"{label}:$.input_target_set"})
    if payload.get("output_target_set") != "structure-nonpin-copied-scalar-policy-slice":
        blockers.append({"reason": "structure_nonpin_policy_output_target_set_mismatch", "label": f"{label}:$.output_target_set"})
    if payload.get("missing_targets") != []:
        blockers.append({"reason": "structure_nonpin_policy_missing_targets_present", "label": f"{label}:$.missing_targets"})

    generated_from = payload.get("generated_from")
    input_snapshot_sources: dict[str, dict[str, str]] = {}
    if not isinstance(generated_from, dict):
        blockers.append({"reason": "structure_nonpin_policy_generated_from_missing", "label": f"{label}:$.generated_from"})
    else:
        if generated_from.get("snapshot_schema") != RC_UFUNCTION_SNAPSHOT_SCHEMA:
            blockers.append({"reason": "structure_nonpin_policy_snapshot_schema_mismatch", "label": f"{label}:$.generated_from.snapshot_schema"})
        input_snapshots = generated_from.get("input_snapshots")
        if not isinstance(input_snapshots, list) or len(input_snapshots) != len(REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS):
            blockers.append({"reason": "structure_nonpin_policy_input_snapshot_count_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})
        else:
            for index, snapshot in enumerate(input_snapshots):
                snapshot_label = f"{label}:$.generated_from.input_snapshots[{index}]"
                if not isinstance(snapshot, dict):
                    blockers.append({"reason": "structure_nonpin_policy_input_snapshot_entry_invalid", "label": snapshot_label})
                    continue
                snapshot_id = snapshot.get("id")
                snapshot_sha256 = snapshot.get("sha256")
                snapshot_target = snapshot.get("target")
                if not isinstance(snapshot_id, str) or not snapshot_id:
                    blockers.append({"reason": "structure_nonpin_policy_input_snapshot_id_invalid", "label": f"{snapshot_label}.id"})
                    continue
                if snapshot_id in input_snapshot_sources:
                    blockers.append({"reason": "structure_nonpin_policy_input_snapshot_id_duplicate", "label": f"{snapshot_label}.id"})
                if not isinstance(snapshot_sha256, str) or SHA256_RE.fullmatch(snapshot_sha256) is None:
                    blockers.append({"reason": "structure_nonpin_policy_input_snapshot_sha256_invalid", "label": f"{snapshot_label}.sha256"})
                    continue
                if not isinstance(snapshot_target, str) or snapshot_target not in REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS:
                    blockers.append({"reason": "structure_nonpin_policy_input_snapshot_target_invalid", "label": f"{snapshot_label}.target"})
                    continue
                input_snapshot_sources[snapshot_id] = {"sha256": snapshot_sha256, "target": snapshot_target}
            if {entry["target"] for entry in input_snapshot_sources.values()} != REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS:
                blockers.append({"reason": "structure_nonpin_policy_input_snapshot_targets_mismatch", "label": f"{label}:$.generated_from.input_snapshots"})

    if safety_summary.get("artifact_status") != "evidence_only":
        blockers.append({"reason": "structure_nonpin_policy_artifact_status_not_evidence_only", "label": f"{label}:$.safety_summary.artifact_status"})
    if safety_summary.get("intended_use") != "offline_review_only":
        blockers.append({"reason": "structure_nonpin_policy_intended_use_not_offline_review_only", "label": f"{label}:$.safety_summary.intended_use"})
    if safety_summary.get("promotion_ready") is not False:
        blockers.append({"reason": "structure_nonpin_policy_promotion_ready_not_false", "label": f"{label}:$.safety_summary.promotion_ready"})
    if safety_summary.get("copied_scalar_count") != len(REQUIRED_STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS):
        blockers.append({"reason": "structure_nonpin_policy_copied_scalar_count_mismatch", "label": f"{label}:$.safety_summary.copied_scalar_count"})
    if safety_summary.get("redacted_field_count") != len(REQUIRED_STRUCTURE_NONPIN_REDACTED_FIELDS):
        blockers.append({"reason": "structure_nonpin_policy_redacted_field_count_mismatch", "label": f"{label}:$.safety_summary.redacted_field_count"})

    copied_scalars = payload.get("copied_scalars")
    if not isinstance(copied_scalars, list) or len(copied_scalars) != len(REQUIRED_STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS):
        blockers.append({"reason": "structure_nonpin_policy_copied_scalars_count_mismatch", "label": f"{label}:$.copied_scalars"})
    else:
        copied_fields = {entry.get("copied_field") for entry in copied_scalars if isinstance(entry, dict)}
        if copied_fields != REQUIRED_STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS:
            blockers.append({"reason": "structure_nonpin_policy_copied_fields_mismatch", "label": f"{label}:$.copied_scalars"})
        expected_offsets = {
            "PrimalStructure.SetVariant.VariantIndex": ("in", "int32", "0x0", 0, 4),
            "PrimalStructure.SetVariant.bForceSet": ("in", "bool", "0x4", 4, 1),
            "PrimalStructure.SetVariant.ReturnValue": ("return", "bool", "0x5", 5, 1),
            "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue": ("return", "bool", "0x8", 8, 1),
            "PrimalStructureSeating.CanSeat.bForce": ("in", "bool", "0x10", 16, 1),
            "PrimalStructureSeating.CanSeat.ReturnValue": ("return", "bool", "0x11", 17, 1),
        }
        for index, entry in enumerate(copied_scalars):
            entry_label = f"{label}:$.copied_scalars[{index}]"
            if not isinstance(entry, dict):
                blockers.append({"reason": "structure_nonpin_policy_copied_scalar_entry_invalid", "label": entry_label})
                continue
            copied_field = entry.get("copied_field")
            expected = expected_offsets.get(copied_field)
            if expected is None:
                blockers.append({"reason": "structure_nonpin_policy_copied_scalar_shape_unknown", "label": entry_label})
                continue
            direction, type_name, offset, offset_internal, element_size = expected
            expected_values = {
                "direction": direction,
                "type": type_name,
                "offset": offset,
                "offset_internal": offset_internal,
                "element_size": element_size,
                "array_dim": 1,
                "evidence_status": "copied-structure-nonpin-scalar-only",
            }
            if type_name == "bool":
                expected_values.update({"bool_field_size": 1, "bool_byte_offset": 0, "byte_mask": "0x01", "field_mask": "0xff", "native_bool": False})
            for key, value in expected_values.items():
                if entry.get(key) != value:
                    blockers.append({"reason": "structure_nonpin_policy_copied_scalar_shape_mismatch", "label": f"{entry_label}.{key}", "expected": value, "recorded": entry.get(key)})
            source_snapshot = entry.get("source_snapshot")
            if not isinstance(source_snapshot, str) or source_snapshot not in input_snapshot_sources:
                blockers.append({"reason": "structure_nonpin_policy_copied_scalar_source_snapshot_unknown", "label": f"{entry_label}.source_snapshot"})
            elif entry.get("source_snapshot_sha256") != input_snapshot_sources[source_snapshot]["sha256"]:
                blockers.append({"reason": "structure_nonpin_policy_copied_scalar_source_snapshot_sha256_mismatch", "label": f"{entry_label}.source_snapshot_sha256"})
            elif entry.get("target") != input_snapshot_sources[source_snapshot]["target"]:
                blockers.append({"reason": "structure_nonpin_policy_copied_scalar_source_snapshot_target_mismatch", "label": f"{entry_label}.source_snapshot"})

    redacted_entries = payload.get("redacted_structure_fields")
    if not isinstance(redacted_entries, list) or len(redacted_entries) != len(REQUIRED_STRUCTURE_NONPIN_REDACTED_FIELDS):
        blockers.append({"reason": "structure_nonpin_policy_redacted_fields_count_mismatch", "label": f"{label}:$.redacted_structure_fields"})
    else:
        redacted_fields = {entry.get("redacted_field") for entry in redacted_entries if isinstance(entry, dict)}
        if redacted_fields != REQUIRED_STRUCTURE_NONPIN_REDACTED_FIELDS:
            blockers.append({"reason": "structure_nonpin_policy_redacted_fields_mismatch", "label": f"{label}:$.redacted_structure_fields"})

    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        blockers.append({"reason": "structure_nonpin_policy_coverage_missing", "label": f"{label}:$.coverage"})
    else:
        if coverage.get("status") != "complete":
            blockers.append({"reason": "structure_nonpin_policy_coverage_not_complete", "label": f"{label}:$.coverage.status"})
        if set(coverage.get("input_targets") or []) != REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS:
            blockers.append({"reason": "structure_nonpin_policy_coverage_input_targets_mismatch", "label": f"{label}:$.coverage.input_targets"})
        if set(coverage.get("copied_targets") or []) != REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS:
            blockers.append({"reason": "structure_nonpin_policy_coverage_copied_targets_mismatch", "label": f"{label}:$.coverage.copied_targets"})
        if set(coverage.get("copied_fields") or []) != REQUIRED_STRUCTURE_NONPIN_COPIED_SCALAR_FIELDS:
            blockers.append({"reason": "structure_nonpin_policy_coverage_copied_fields_mismatch", "label": f"{label}:$.coverage.copied_fields"})
        if set(coverage.get("redacted_fields") or []) != REQUIRED_STRUCTURE_NONPIN_REDACTED_FIELDS:
            blockers.append({"reason": "structure_nonpin_policy_coverage_redacted_fields_mismatch", "label": f"{label}:$.coverage.redacted_fields"})

    if not isinstance(payload.get("non_claims"), list) or not REQUIRED_STRUCTURE_NONPIN_NON_CLAIMS.issubset(set(payload["non_claims"])):
        blockers.append({"reason": "structure_nonpin_policy_non_claims_missing_required_boundaries", "label": f"{label}:$.non_claims"})
    if not isinstance(safety_summary.get("explicitly_excluded"), list) or not REQUIRED_STRUCTURE_NONPIN_EXPLICIT_EXCLUSIONS.issubset(set(safety_summary["explicitly_excluded"])):
        blockers.append({"reason": "structure_nonpin_policy_explicit_exclusions_missing_internal_boundaries", "label": f"{label}:$.safety_summary.explicitly_excluded"})
    payload_without_boundaries = {key: value for key, value in payload.items() if key not in {"non_claims", "safety_summary"}}
    if "VerifyPinCode" in json.dumps(payload_without_boundaries, sort_keys=True):
        blockers.append({"reason": "structure_nonpin_policy_contains_verify_pin_code_payload", "label": label})
    if mode == "promote":
        blockers.append({"reason": "promote_mode_structure_nonpin_copied_scalar_policy_slice_evidence_only", "label": label})
    for trail, _ in collect_ready_overclaims(payload):
        blockers.append({"reason": "structure_nonpin_policy_readiness_overclaim", "label": f"{label}:{trail}"})
    for trail, _, reason in collect_candidate_public_overclaims(
        payload,
        allowed_prefixes=("$.non_claims", "$.safety_summary.explicitly_excluded"),
    ):
        blockers.append({"reason": f"structure_nonpin_policy_public_overclaim_{reason}", "label": f"{label}:{trail}"})
    for trail, raw_value in collect_string_fields(payload):
        if trail.startswith("$.non_claims") or trail.startswith("$.safety_summary.explicitly_excluded"):
            continue
        text = raw_value.casefold()
        if "structureevents" in text or "structure events" in text:
            blockers.append({"reason": "structure_nonpin_policy_public_overclaim_public_structure_events", "label": f"{label}:{trail}"})
    return blockers


def validate_static_global_promotion_evidence_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
) -> list[dict[str, Any]]:
    if payload.get("schema") != STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    promotion_gate = payload.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        blockers.append({"reason": "static_global_missing_promotion_gate", "label": f"{label}:$.promotion_gate"})
        return blockers

    artifact_identity = payload.get("artifact_identity")
    identity_ready_for_hash = False
    if not isinstance(artifact_identity, dict):
        blockers.append({"reason": "static_global_missing_artifact_identity", "label": f"{label}:$.artifact_identity"})
    else:
        expected_keys = {"artifact_kind", "artifact_sha256", "capture_id", "evidence_pack_id"}
        if set(artifact_identity) != expected_keys:
            blockers.append({"reason": "static_global_artifact_identity_fields_mismatch", "label": f"{label}:$.artifact_identity"})
        if artifact_identity.get("artifact_kind") != STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA:
            blockers.append({"reason": "static_global_artifact_identity_kind_mismatch", "label": f"{label}:$.artifact_identity.artifact_kind"})
        artifact_sha256 = artifact_identity.get("artifact_sha256")
        if not isinstance(artifact_sha256, str) or SHA256_RE.fullmatch(artifact_sha256) is None:
            blockers.append({"reason": "static_global_artifact_identity_sha_invalid", "label": f"{label}:$.artifact_identity.artifact_sha256"})
        capture_id = artifact_identity.get("capture_id")
        evidence_pack_id = artifact_identity.get("evidence_pack_id")
        if not static_global_safe_id(capture_id):
            blockers.append({"reason": "static_global_artifact_identity_capture_id_invalid", "label": f"{label}:$.artifact_identity.capture_id"})
        if not static_global_safe_id(evidence_pack_id):
            blockers.append({"reason": "static_global_artifact_identity_evidence_pack_id_invalid", "label": f"{label}:$.artifact_identity.evidence_pack_id"})
        identity_ready_for_hash = (
            artifact_identity.get("artifact_kind") == STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA
            and isinstance(artifact_sha256, str)
            and SHA256_RE.fullmatch(artifact_sha256) is not None
            and static_global_safe_id(capture_id)
            and static_global_safe_id(evidence_pack_id)
        )

    binary = payload.get("binary")
    if not isinstance(binary, dict) or not isinstance(binary.get("sha256"), str) or SHA256_RE.fullmatch(binary["sha256"]) is None:
        blockers.append({"reason": "static_global_missing_binary_sha256", "label": f"{label}:$.binary.sha256"})

    static_xrefs_sha256 = payload.get("static_xrefs_sha256")
    if not isinstance(static_xrefs_sha256, str) or SHA256_RE.fullmatch(static_xrefs_sha256) is None:
        blockers.append({"reason": "static_global_static_xrefs_sha256_invalid", "label": f"{label}:$.static_xrefs_sha256"})
    elif identity_ready_for_hash and isinstance(artifact_identity, dict):
        expected_identity = static_global_artifact_identity(
            payload,
            capture_id=str(artifact_identity["capture_id"]),
            evidence_pack_id=str(artifact_identity["evidence_pack_id"]),
        )
        if artifact_identity.get("artifact_sha256") != expected_identity["artifact_sha256"]:
            blockers.append(
                {
                    "reason": "static_global_artifact_identity_hash_mismatch",
                    "label": f"{label}:$.artifact_identity.artifact_sha256",
                    "expected": expected_identity["artifact_sha256"],
                    "recorded": artifact_identity.get("artifact_sha256"),
                }
            )

    commands = payload.get("commands")
    if not isinstance(commands, dict) or not commands:
        blockers.append({"reason": "static_global_missing_commands", "label": f"{label}:$.commands"})

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        blockers.append({"reason": "static_global_missing_artifacts", "label": f"{label}:$.artifacts"})

    if mode != "promote" and promotion_gate.get("ready") is not False:
        blockers.append({"reason": "static_global_consume_promotion_gate_not_false", "label": f"{label}:$.promotion_gate.ready"})

    claims = [value.casefold() for _, value in collect_string_fields(payload)]
    if not any("static_only_evidence" in value for value in claims):
        blockers.append({"reason": "static_global_missing_static_only_evidence_claim", "label": label})

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        blockers.append({"reason": "static_global_missing_candidates", "label": f"{label}:$.candidates"})
    else:
        for index, candidate in enumerate(candidates):
            candidate_label = f"{label}:$.candidates[{index}]"
            if not isinstance(candidate, dict):
                blockers.append({"reason": "static_global_candidate_invalid", "label": candidate_label})
                continue
            kind = candidate.get("kind")
            if kind not in STATIC_GLOBAL_CANDIDATE_KINDS:
                blockers.append({"reason": "static_global_candidate_kind_invalid", "label": f"{candidate_label}.kind"})
            address = candidate.get("address")
            if not isinstance(address, str) or re.fullmatch(r"0x[0-9a-f]+", address) is None:
                blockers.append({"reason": "static_global_candidate_address_invalid", "label": f"{candidate_label}.address"})
            static_contract = candidate.get("static_contract")
            if not isinstance(static_contract, dict):
                blockers.append({"reason": "static_global_candidate_missing_static_contract", "label": f"{candidate_label}.static_contract"})
                continue
            if kind == "gobjects":
                contract_blockers = static_contract.get("blockers")
                has_field_window_blocker = (
                    isinstance(contract_blockers, list)
                    and STATIC_GLOBAL_GOBJECTS_FIELD_WINDOW_BLOCKER in contract_blockers
                )
                has_coherent_window = isinstance(static_contract.get("coherent_window"), dict)
                redacted_evidence = static_contract.get("redacted_field_window_evidence")
                has_redacted_evidence = (
                    isinstance(redacted_evidence, dict)
                    and redacted_evidence.get("status") == "accepted_internal_static_evidence"
                    and redacted_evidence.get("clears_blocker") == STATIC_GLOBAL_GOBJECTS_FIELD_WINDOW_BLOCKER
                )
                if not (has_coherent_window or has_field_window_blocker or has_redacted_evidence):
                    blockers.append(
                        {
                            "reason": "static_global_gobjects_missing_field_window_status",
                            "label": f"{candidate_label}.static_contract",
                        }
                    )

    if mode == "promote":
        if promotion_gate.get("ready") is not True:
            blockers.append({"reason": "promote_mode_static_global_promotion_gate_not_ready", "label": f"{label}:$.promotion_gate.ready"})
        if isinstance(promotion_gate.get("blockers"), list) and promotion_gate["blockers"]:
            blockers.append({"reason": "promote_mode_static_global_has_blockers", "label": f"{label}:$.promotion_gate.blockers"})
        remaining_blockers = payload.get("remaining_blockers")
        if isinstance(remaining_blockers, list) and remaining_blockers:
            blockers.append({"reason": "promote_mode_static_global_has_remaining_blockers", "label": f"{label}:$.remaining_blockers"})
        if any("static_only_evidence" in value for value in claims):
            blockers.append({"reason": "promote_mode_static_global_static_only_evidence", "label": label})
    for trail, _, reason in collect_candidate_public_overclaims(
        payload,
        allowed_prefixes=(),
    ):
        blockers.append({"reason": f"static_global_public_overclaim_{reason}", "label": f"{label}:{trail}"})
    return blockers


def validate_resource_handle_revalidation_evaluator_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
) -> list[dict[str, Any]]:
    if payload.get("schema") != RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    if mode != "promote":
        return blockers

    if payload.get("post_callback_resource_handle_ready") is not True:
        blockers.append(
            {
                "reason": "promote_mode_resource_handle_post_callback_not_ready",
                "label": f"{label}:$.post_callback_resource_handle_ready",
            }
        )
    if payload.get("uobject_flags_validity_semantics_proven") is not True:
        blockers.append(
            {
                "reason": "promote_mode_resource_handle_flag_semantics_unproven",
                "label": f"{label}:$.uobject_flags_validity_semantics_proven",
            }
        )
    manifest_blockers = payload.get("blockers")
    if isinstance(manifest_blockers, list) and manifest_blockers:
        blockers.append({"reason": "promote_mode_resource_handle_manifest_has_blockers", "label": f"{label}:$.blockers"})
    promotion_gate = payload.get("promotion_gate")
    if isinstance(promotion_gate, dict):
        if promotion_gate.get("ready") is not True:
            blockers.append({"reason": "promote_mode_resource_handle_promotion_gate_not_ready", "label": f"{label}:$.promotion_gate.ready"})
        if isinstance(promotion_gate.get("blockers"), list) and promotion_gate["blockers"]:
            blockers.append({"reason": "promote_mode_resource_handle_promotion_gate_has_blockers", "label": f"{label}:$.promotion_gate.blockers"})
    return blockers


def validate_resource_handle_serial_scan_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
    expected_binary_sha256: str | None,
    workspace_root: Path,
    protected_root: Path,
) -> list[dict[str, Any]]:
    if payload.get("schema") != RESOURCE_HANDLE_SERIAL_SCAN_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    core_sha256 = payload.get("core_sha256")
    if not isinstance(core_sha256, str) or SHA256_RE.fullmatch(core_sha256) is None:
        blockers.append({"reason": "resource_handle_serial_scan_core_sha256_invalid", "label": f"{label}:$.core_sha256"})
    if payload.get("core_sha256_verified") is not True:
        blockers.append({"reason": "resource_handle_serial_scan_core_sha256_not_verified", "label": f"{label}:$.core_sha256_verified"})
    core_path = payload.get("core_path")
    if not isinstance(core_path, str) or not Path(core_path).expanduser().is_absolute():
        blockers.append({"reason": "resource_handle_serial_scan_core_path_invalid", "label": f"{label}:$.core_path"})
    else:
        resolved_core_path = Path(core_path).expanduser().resolve(strict=False)
        blockers.extend(
            path_blockers(
                Path(core_path),
                label=f"{label}:$.core_path",
                workspace_root=workspace_root,
                protected_root=protected_root,
                require_workspace=True,
            )
        )
        if isinstance(core_sha256, str) and SHA256_RE.fullmatch(core_sha256) is not None:
            blockers.extend(
                sha256_file_or_blocker(
                    resolved_core_path,
                    label=f"{label}:$.core_path",
                    expected_sha256=core_sha256,
                )
            )
    binary_sha256 = payload.get("binary_sha256")
    if not isinstance(binary_sha256, str) or SHA256_RE.fullmatch(binary_sha256) is None:
        blockers.append({"reason": "resource_handle_serial_scan_binary_sha256_invalid", "label": f"{label}:$.binary_sha256"})
    elif expected_binary_sha256 is not None and binary_sha256 != expected_binary_sha256:
        blockers.append(
            {
                "reason": "resource_handle_serial_scan_binary_sha256_mismatch",
                "label": f"{label}:$.binary_sha256",
                "expected_binary_sha256": expected_binary_sha256,
                "recorded_binary_sha256": binary_sha256,
            }
        )

    for required_key in ("gobjects", "fname_root_slot"):
        if not isinstance(payload.get(required_key), str) or re.fullmatch(r"0x[0-9a-f]+", payload.get(required_key, "")) is None:
            blockers.append({"reason": "resource_handle_serial_scan_address_invalid", "label": f"{label}:$.{required_key}"})

    scan_limit = payload.get("scan_limit")
    if not is_json_int(scan_limit) or scan_limit < 0:
        blockers.append({"reason": "resource_handle_serial_scan_scan_limit_invalid", "label": f"{label}:$.scan_limit"})

    totals = payload.get("totals")
    if not isinstance(totals, dict):
        blockers.append({"reason": "resource_handle_serial_scan_totals_missing", "label": f"{label}:$.totals"})
    else:
        for key in ("objects_read", "serial_nonzero", "membership_pass_count", "flags_any"):
            if not is_json_int(totals.get(key)) or totals[key] < 0:
                blockers.append({"reason": "resource_handle_serial_scan_total_invalid", "label": f"{label}:$.totals.{key}"})
        if is_json_int(totals.get("objects_read")):
            for key in ("serial_nonzero", "membership_pass_count", "flags_any"):
                if is_json_int(totals.get(key)) and totals[key] > totals["objects_read"]:
                    blockers.append({"reason": "resource_handle_serial_scan_total_impossible", "label": f"{label}:$.totals.{key}"})
            if is_json_int(scan_limit) and totals["objects_read"] > scan_limit:
                blockers.append(
                    {
                        "reason": "resource_handle_serial_scan_objects_read_exceeds_scan_limit",
                        "label": f"{label}:$.totals.objects_read",
                    }
                )

    interpretation = payload.get("interpretation")
    if not isinstance(interpretation, dict):
        blockers.append({"reason": "resource_handle_serial_scan_interpretation_missing", "label": f"{label}:$.interpretation"})
    elif interpretation.get("public_resource_handle_ready") is not False:
        blockers.append({"reason": "resource_handle_serial_scan_public_handle_overclaim", "label": f"{label}:$.interpretation.public_resource_handle_ready"})
    for trail, _value in collect_ready_overclaims(payload):
        blockers.append({"reason": "resource_handle_serial_scan_ready_overclaim", "label": f"{label}:{trail}"})
    if payload.get("status") != "candidate_blocked":
        blockers.append({"reason": "resource_handle_serial_scan_status_overclaim", "label": f"{label}:$.status"})
    if payload.get("evidence_kind") != "internal_offline_scan_candidate":
        blockers.append({"reason": "resource_handle_serial_scan_evidence_kind_overclaim", "label": f"{label}:$.evidence_kind"})
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        blockers.append({"reason": "resource_handle_serial_scan_provenance_missing", "label": f"{label}:$.provenance"})
    else:
        if provenance.get("schema") != RESOURCE_HANDLE_SERIAL_SCAN_PROVENANCE_SCHEMA:
            blockers.append({"reason": "resource_handle_serial_scan_provenance_schema_mismatch", "label": f"{label}:$.provenance.schema"})
        if provenance.get("verified") is not True:
            blockers.append({"reason": "resource_handle_serial_scan_provenance_not_verified", "label": f"{label}:$.provenance.verified"})
        if provenance.get("path_redacted") is not True:
            blockers.append({"reason": "resource_handle_serial_scan_provenance_path_not_redacted", "label": f"{label}:$.provenance.path_redacted"})
        if provenance.get("producer") != "scan_resource_handle_serials.py":
            blockers.append({"reason": "resource_handle_serial_scan_provenance_producer_mismatch", "label": f"{label}:$.provenance.producer"})
        if provenance.get("tool_path") != "scripts/scan_resource_handle_serials.py":
            blockers.append({"reason": "resource_handle_serial_scan_provenance_tool_path_mismatch", "label": f"{label}:$.provenance.tool_path"})
        argv = provenance.get("argv")
        if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
            blockers.append({"reason": "resource_handle_serial_scan_provenance_argv_invalid", "label": f"{label}:$.provenance.argv"})
        if provenance.get("core_sha256_verified") is not True:
            blockers.append({"reason": "resource_handle_serial_scan_provenance_core_sha256_not_verified", "label": f"{label}:$.provenance.core_sha256_verified"})
        if core_sha256 is not None and provenance.get("core_sha256") != core_sha256:
            blockers.append({"reason": "resource_handle_serial_scan_provenance_core_sha256_mismatch", "label": f"{label}:$.provenance.core_sha256"})
        if binary_sha256 is not None and provenance.get("binary_sha256") != binary_sha256:
            blockers.append({"reason": "resource_handle_serial_scan_provenance_binary_sha256_mismatch", "label": f"{label}:$.provenance.binary_sha256"})
        for key in ("gobjects", "fname_root_slot"):
            if provenance.get(key) != payload.get(key):
                blockers.append({"reason": "resource_handle_serial_scan_provenance_address_mismatch", "label": f"{label}:$.provenance.{key}"})
        if provenance.get("scan_limit") != payload.get("scan_limit"):
            blockers.append({"reason": "resource_handle_serial_scan_provenance_scan_limit_mismatch", "label": f"{label}:$.provenance.scan_limit"})

    consume_gate = payload.get("consume_gate_expectation")
    if not isinstance(consume_gate, dict):
        blockers.append({"reason": "resource_handle_serial_scan_consume_gate_missing", "label": f"{label}:$.consume_gate_expectation"})
    else:
        if consume_gate.get("schema") != RESOURCE_HANDLE_SERIAL_SCAN_CONSUME_GATE_SCHEMA:
            blockers.append({"reason": "resource_handle_serial_scan_consume_gate_schema_mismatch", "label": f"{label}:$.consume_gate_expectation.schema"})
        if consume_gate.get("consume_ready") is not True:
            blockers.append({"reason": "resource_handle_serial_scan_consume_gate_not_ready", "label": f"{label}:$.consume_gate_expectation.consume_ready"})
        if consume_gate.get("promote_ready") is not False:
            blockers.append({"reason": "resource_handle_serial_scan_consume_gate_promote_overclaim", "label": f"{label}:$.consume_gate_expectation.promote_ready"})
        if consume_gate.get("blockers") != []:
            blockers.append({"reason": "resource_handle_serial_scan_consume_gate_has_blockers", "label": f"{label}:$.consume_gate_expectation.blockers"})
        non_claims = consume_gate.get("non_claims")
        if not isinstance(non_claims, list) or not REQUIRED_RESOURCE_HANDLE_SERIAL_SCAN_NON_CLAIMS.issubset(set(non_claims)):
            blockers.append({"reason": "resource_handle_serial_scan_consume_gate_non_claims_missing", "label": f"{label}:$.consume_gate_expectation.non_claims"})
    for trail, value in collect_string_fields(payload):
        if trail == "$.core_path":
            continue
        if str(SERVER_ROOT) in value or "../obelisk/dumps" in value or "..\\obelisk\\dumps" in value:
            blockers.append({"reason": "resource_handle_serial_scan_protected_path_string", "label": f"{label}:{trail}"})

    samples = payload.get("flag_rejection_candidate_samples")
    if not isinstance(samples, list) or not samples:
        blockers.append({"reason": "resource_handle_serial_scan_missing_rejection_candidates", "label": f"{label}:$.flag_rejection_candidate_samples"})
    else:
        coherent_sample_count = 0
        candidate_indices: set[int] = set()
        for index, sample in enumerate(samples):
            sample_label = f"{label}:$.flag_rejection_candidate_samples[{index}]"
            if not isinstance(sample, dict):
                blockers.append({"reason": "resource_handle_serial_scan_candidate_not_object", "label": sample_label})
                continue
            serial = sample.get("serial")
            flags = sample.get("flags")
            if not is_json_int(sample.get("index")) or sample["index"] < 0:
                blockers.append({"reason": "resource_handle_serial_scan_candidate_index_invalid", "label": f"{sample_label}.index"})
            else:
                if sample["index"] in candidate_indices:
                    blockers.append({"reason": "resource_handle_serial_scan_candidate_index_duplicate", "label": f"{sample_label}.index"})
                candidate_indices.add(sample["index"])
                if is_json_int(scan_limit) and sample["index"] >= scan_limit:
                    blockers.append({"reason": "resource_handle_serial_scan_candidate_index_out_of_range", "label": f"{sample_label}.index"})
            if not is_json_int(serial) or serial <= 0:
                blockers.append({"reason": "resource_handle_serial_scan_candidate_serial_invalid", "label": f"{sample_label}.serial"})
            if sample.get("object_ptr_present") is not True:
                blockers.append({"reason": "resource_handle_serial_scan_candidate_object_ptr_missing", "label": f"{sample_label}.object_ptr_present"})
            if sample.get("gobjects_membership_pass") is not True:
                blockers.append({"reason": "resource_handle_serial_scan_candidate_membership_failed", "label": f"{sample_label}.gobjects_membership_pass"})
            if not is_json_int(flags) or flags < 0:
                blockers.append({"reason": "resource_handle_serial_scan_candidate_flags_invalid", "label": f"{sample_label}.flags"})
                flags = 0
            elif flags > 0xFFFFFFFF:
                blockers.append({"reason": "resource_handle_serial_scan_candidate_flags_outside_u32", "label": f"{sample_label}.flags"})
            expected_has = {
                "has_0x100": bool(flags & 0x100),
                "has_0x4000": bool(flags & 0x4000),
                "has_0x8000": bool(flags & 0x8000),
            }
            if not any(expected_has.values()):
                blockers.append({"reason": "resource_handle_serial_scan_candidate_no_validity_mask", "label": sample_label})
            for key, expected in expected_has.items():
                if sample.get(key) is not expected:
                    blockers.append({"reason": "resource_handle_serial_scan_candidate_mask_mismatch", "label": f"{sample_label}.{key}"})
            if sample.get("policy_result_strict") != "reject":
                blockers.append({"reason": "resource_handle_serial_scan_candidate_strict_policy_not_reject", "label": f"{sample_label}.policy_result_strict"})
            expected_allow4000 = "reject" if flags & (0x100 | 0x8000) else "allow_candidate"
            if sample.get("policy_result_allow4000") != expected_allow4000:
                blockers.append({"reason": "resource_handle_serial_scan_candidate_allow4000_policy_mismatch", "label": f"{sample_label}.policy_result_allow4000"})
            if (
                is_json_int(serial)
                and serial > 0
                and sample.get("object_ptr_present") is True
                and sample.get("gobjects_membership_pass") is True
                and any(expected_has.values())
            ):
                coherent_sample_count += 1

        if isinstance(totals, dict) and coherent_sample_count:
            minimum_totals = {
                "objects_read": coherent_sample_count,
                "serial_nonzero": coherent_sample_count,
                "membership_pass_count": coherent_sample_count,
                "flags_any": coherent_sample_count,
            }
            for key, minimum in minimum_totals.items():
                if is_json_int(totals.get(key)) and totals[key] < minimum:
                    blockers.append({"reason": "resource_handle_serial_scan_total_contradicts_candidates", "label": f"{label}:$.totals.{key}"})

    if mode == "promote":
        blockers.append({"reason": "promote_mode_resource_handle_serial_scan_candidate_only", "label": label})
    return blockers


def validate_uobject_flag_policy_public_redaction(payload: dict[str, Any], *, label: str) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for trail, key in collect_key_names(payload):
        if UOBJECT_FLAG_POLICY_PUBLIC_FORBIDDEN_KEY_RE.search(key):
            blockers.append(
                {
                    "reason": "uobject_flag_policy_public_identifier_key_leak",
                    "label": f"{label}:{trail}",
                    "key": key,
                }
            )
    for trail, raw_value in collect_string_fields(payload):
        if raw_value in UOBJECT_FLAG_POLICY_ALLOWED_HEX_STRINGS:
            continue
        if UOBJECT_FLAG_POLICY_PUBLIC_ADDRESS_RE.search(raw_value):
            blockers.append(
                {
                    "reason": "uobject_flag_policy_public_address_string_leak",
                    "label": f"{label}:{trail}",
                }
            )
        if UOBJECT_FLAG_POLICY_PUBLIC_FORBIDDEN_VALUE_RE.search(raw_value):
            blockers.append(
                {
                    "reason": "uobject_flag_policy_public_identifier_string_leak",
                    "label": f"{label}:{trail}",
                }
            )
    return blockers


def validate_uobject_flag_policy_report_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
    expected_binary_sha256: str | None,
) -> list[dict[str, Any]]:
    if payload.get("schema") != UOBJECT_FLAG_POLICY_REPORT_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    blockers.extend(validate_uobject_flag_policy_public_redaction(payload, label=label))
    if payload.get("evidence_kind") != "static_negative_equivalent_candidate":
        blockers.append({"reason": "uobject_flag_policy_evidence_kind_mismatch", "label": f"{label}:$.evidence_kind"})
    if payload.get("status") != "candidate_blocked":
        blockers.append({"reason": "uobject_flag_policy_status_not_candidate_blocked", "label": f"{label}:$.status"})
    if payload.get("promotion_ready") is not False:
        blockers.append({"reason": "uobject_flag_policy_promotion_ready_overclaim", "label": f"{label}:$.promotion_ready"})
    if payload.get("post_callback_resource_handle_ready") is not False:
        blockers.append(
            {
                "reason": "uobject_flag_policy_post_callback_resourcehandle_overclaim",
                "label": f"{label}:$.post_callback_resource_handle_ready",
            }
        )
    for trail, raw_value in collect_bool_fields(payload):
        key = trail.rsplit(".", 1)[-1]
        if raw_value is True and key in READY_OVERCLAIM_KEYS:
            blockers.append({"reason": "uobject_flag_policy_readiness_overclaim", "label": f"{label}:{trail}"})

    binary = payload.get("binary")
    recorded_sha: object | None = None
    if not isinstance(binary, dict):
        blockers.append({"reason": "uobject_flag_policy_missing_binary", "label": f"{label}:$.binary"})
    else:
        recorded_sha = binary.get("sha256")
        if not isinstance(recorded_sha, str) or SHA256_RE.fullmatch(recorded_sha) is None:
            blockers.append({"reason": "uobject_flag_policy_binary_sha256_invalid", "label": f"{label}:$.binary.sha256"})
        if expected_binary_sha256 is not None and recorded_sha != expected_binary_sha256:
            blockers.append(
                {
                    "reason": "uobject_flag_policy_binary_sha256_mismatch",
                    "label": f"{label}:$.binary.sha256",
                    "expected_binary_sha256": expected_binary_sha256,
                    "recorded_binary_sha256": recorded_sha,
                }
            )
        if binary.get("path_redacted") is not True:
            blockers.append({"reason": "uobject_flag_policy_binary_path_not_redacted", "label": f"{label}:$.binary.path_redacted"})

    weak_helper = payload.get("weak_helper_caller_mode")
    if not isinstance(weak_helper, dict):
        blockers.append({"reason": "uobject_flag_policy_missing_weak_helper_caller_mode", "label": f"{label}:$.weak_helper_caller_mode"})
    else:
        weak_helper_label = f"{label}:$.weak_helper_caller_mode"
        if set(weak_helper) != UOBJECT_FLAG_POLICY_WEAK_HELPER_KEYS:
            blockers.append({"reason": "uobject_flag_policy_weak_helper_unexpected_fields", "label": weak_helper_label})
        if weak_helper.get("schema") != WEAK_HELPER_CALLER_MODE_SCHEMA:
            blockers.append({"reason": "uobject_flag_policy_weak_helper_schema_mismatch", "label": f"{weak_helper_label}.schema"})
        if weak_helper.get("promotion_gate_ready") is not False:
            blockers.append({"reason": "uobject_flag_policy_weak_helper_promotion_gate_overclaim", "label": f"{weak_helper_label}.promotion_gate_ready"})
        if weak_helper.get("flag_rules") != UOBJECT_FLAG_POLICY_WEAK_HELPER_FLAG_RULES:
            blockers.append({"reason": "uobject_flag_policy_weak_helper_flag_rules_mismatch", "label": f"{weak_helper_label}.flag_rules"})
        artifact_sha = weak_helper.get("artifact_sha256")
        coverage = weak_helper.get("direct_call_coverage")
        coverage_entry = coverage.get(UOBJECT_FLAG_POLICY_PUBLIC_HELPER_ID) if isinstance(coverage, dict) else None
        if not isinstance(coverage_entry, dict) or coverage_entry.get("expected") != 6 or coverage_entry.get("observed") != 6:
            blockers.append(
                {
                    "reason": "uobject_flag_policy_direct_call_coverage_mismatch",
                    "label": f"{label}:$.weak_helper_caller_mode.direct_call_coverage",
                }
            )
        summary = weak_helper.get("caller_rows_summary")
        source = weak_helper.get("caller_rows_source")
        mode_summary = weak_helper.get("caller_mode_summary")
        mode_source = weak_helper.get("caller_mode_source")
        has_rows_summary = isinstance(summary, dict)
        has_mode_summary = isinstance(mode_summary, dict)
        if has_mode_summary or mode_source is not None:
            blockers.append({"reason": "uobject_flag_policy_legacy_caller_mode_not_consume_ready", "label": f"{label}:$.weak_helper_caller_mode"})
        if not has_rows_summary:
            blockers.append({"reason": "uobject_flag_policy_caller_rows_summary_missing", "label": f"{label}:$.weak_helper_caller_mode"})
        if has_rows_summary:
            summary_label = f"{label}:$.weak_helper_caller_mode.caller_rows_summary"
            if set(summary) != UOBJECT_FLAG_POLICY_CALLER_ROWS_SUMMARY_KEYS:
                blockers.append({"reason": "uobject_flag_policy_caller_rows_summary_unexpected_fields", "label": summary_label})
            expected_summary = {
                "helper": UOBJECT_FLAG_POLICY_PUBLIC_HELPER_ID,
                "row_count": 6,
                "unique_caller_hash_count": 6,
                "mode_args": {"sil": {"source": "const", "value": 1}},
                "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
                "source_count": 2,
                "evidence": ["ghidra", "radare2"],
                "policy_observation": {
                    "0x100": "null_always",
                    "0x4000": "not_rejected_in_observed_sil_1_callers",
                },
                "claim_level": "internal_static_caller_mode_candidate",
                "lifecycle_names": "not_promoted",
                "path_redacted": True,
            }
            for key, expected in expected_summary.items():
                if summary.get(key) != expected:
                    blockers.append({"reason": f"uobject_flag_policy_caller_rows_summary_{key}_mismatch", "label": f"{summary_label}.{key}"})
            if not isinstance(summary.get("caller_rows_sha256"), str) or SHA256_RE.fullmatch(summary["caller_rows_sha256"]) is None:
                blockers.append({"reason": "uobject_flag_policy_caller_rows_summary_sha256_invalid", "label": f"{summary_label}.caller_rows_sha256"})
            for trail, _, reason in collect_candidate_public_overclaims(summary):
                blockers.append({"reason": f"uobject_flag_policy_caller_rows_summary_public_overclaim_{reason}", "label": f"{summary_label}:{trail}"})
        if has_rows_summary and not isinstance(source, dict):
            blockers.append({"reason": "uobject_flag_policy_caller_rows_source_missing", "label": f"{label}:$.weak_helper_caller_mode.caller_rows_source"})
        elif has_rows_summary:
            source_label = f"{label}:$.weak_helper_caller_mode.caller_rows_source"
            if set(source) != UOBJECT_FLAG_POLICY_CALLER_ROWS_SOURCE_KEYS:
                blockers.append({"reason": "uobject_flag_policy_caller_rows_source_unexpected_fields", "label": source_label})
            if source.get("schema") != WEAK_HELPER_CALLER_MODE_SCHEMA:
                blockers.append({"reason": "uobject_flag_policy_caller_rows_source_schema_mismatch", "label": f"{source_label}.schema"})
            if not isinstance(artifact_sha, str) or SHA256_RE.fullmatch(artifact_sha) is None:
                blockers.append({"reason": "uobject_flag_policy_weak_helper_artifact_sha256_invalid", "label": f"{label}:$.weak_helper_caller_mode.artifact_sha256"})
            if source.get("source_artifact_sha256") != artifact_sha:
                blockers.append({"reason": "uobject_flag_policy_caller_rows_source_artifact_mismatch", "label": f"{source_label}.source_artifact_sha256"})
            if source.get("binary_sha256") != recorded_sha:
                blockers.append({"reason": "uobject_flag_policy_caller_rows_source_binary_mismatch", "label": f"{source_label}.binary_sha256"})
            if isinstance(summary, dict) and source.get("caller_rows_sha256") != summary.get("caller_rows_sha256"):
                blockers.append({"reason": "uobject_flag_policy_caller_rows_source_digest_mismatch", "label": f"{source_label}.caller_rows_sha256"})
            if source.get("path_redacted") is not True:
                blockers.append({"reason": "uobject_flag_policy_caller_rows_source_path_not_redacted", "label": f"{source_label}.path_redacted"})
            for trail, _, reason in collect_candidate_public_overclaims(source):
                blockers.append({"reason": f"uobject_flag_policy_caller_rows_source_public_overclaim_{reason}", "label": f"{source_label}:{trail}"})
    candidates = payload.get("policy_candidates")
    if not isinstance(candidates, list):
        blockers.append({"reason": "uobject_flag_policy_candidates_missing", "label": f"{label}:$.policy_candidates"})
    else:
        observed_masks: set[str] = set()
        for index, candidate in enumerate(candidates):
            candidate_label = f"{label}:$.policy_candidates[{index}]"
            if not isinstance(candidate, dict):
                blockers.append({"reason": "uobject_flag_policy_candidate_not_object", "label": candidate_label})
                continue
            if set(candidate) != {"mask", "candidate", "support", "ue_lifecycle_name"}:
                blockers.append({"reason": "uobject_flag_policy_candidate_unexpected_fields", "label": candidate_label})
            for trail, _, reason in collect_candidate_public_overclaims(candidate):
                blockers.append({"reason": f"uobject_flag_policy_candidate_public_overclaim_{reason}", "label": f"{candidate_label}:{trail}"})
            mask = candidate.get("mask")
            if isinstance(mask, str):
                observed_masks.add(mask)
            expected = REQUIRED_UOBJECT_FLAG_POLICY_CANDIDATES.get(mask) if isinstance(mask, str) else None
            if expected is None:
                blockers.append({"reason": "uobject_flag_policy_candidate_mask_unexpected", "label": f"{candidate_label}.mask"})
                continue
            if candidate.get("candidate") != expected["candidate"]:
                blockers.append({"reason": "uobject_flag_policy_candidate_kind_mismatch", "label": f"{candidate_label}.candidate"})
            support = candidate.get("support")
            if not isinstance(support, list) or set(support) != expected["support"]:
                blockers.append(
                    {
                        "reason": "uobject_flag_policy_candidate_support_mismatch",
                        "label": f"{candidate_label}.support",
                        "expected": sorted(expected["support"]),
                        "recorded": support,
                    }
                )
            if candidate.get("ue_lifecycle_name") != "not_promoted":
                blockers.append({"reason": "uobject_flag_policy_candidate_lifecycle_name_mismatch", "label": f"{candidate_label}.ue_lifecycle_name"})
        if observed_masks != set(REQUIRED_UOBJECT_FLAG_POLICY_CANDIDATES):
            blockers.append(
                {
                    "reason": "uobject_flag_policy_candidate_masks_mismatch",
                    "label": f"{label}:$.policy_candidates",
                    "expected": sorted(REQUIRED_UOBJECT_FLAG_POLICY_CANDIDATES),
                    "recorded": sorted(observed_masks),
                }
            )

    contract = payload.get("internal_revalidation_contract")
    if not isinstance(contract, dict):
        blockers.append(
            {
                "reason": "uobject_flag_policy_internal_revalidation_contract_missing",
                "label": f"{label}:$.internal_revalidation_contract",
            }
        )
    elif contract != REQUIRED_UOBJECT_FLAG_POLICY_INTERNAL_REVALIDATION_CONTRACT:
        blockers.append(
            {
                "reason": "uobject_flag_policy_internal_revalidation_contract_mismatch",
                "label": f"{label}:$.internal_revalidation_contract",
            }
        )

    windows = payload.get("windows_summary")
    if not isinstance(windows, dict):
        blockers.append({"reason": "uobject_flag_policy_missing_windows_summary", "label": f"{label}:$.windows_summary"})
    else:
        if windows.get("all_required_present") is not True:
            blockers.append({"reason": "uobject_flag_policy_required_windows_not_present", "label": f"{label}:$.windows_summary"})
        if windows.get("all_required_patterns_present") is not True:
            blockers.append({"reason": "uobject_flag_policy_required_patterns_not_present", "label": f"{label}:$.windows_summary"})
        required = windows.get("required")
        if (
            not isinstance(required, list)
            or any(not isinstance(name, str) for name in required)
            or set(required) != REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS
            or len(required) != len(REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS)
        ):
            blockers.append(
                {
                    "reason": "uobject_flag_policy_required_windows_field_mismatch",
                    "label": f"{label}:$.windows_summary.required",
                    "expected": sorted(REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS),
                    "recorded": required,
                }
            )
        observed = windows.get("observed")
        observed_names: set[str] = set()
        if not isinstance(observed, list):
            blockers.append({"reason": "uobject_flag_policy_observed_windows_not_list", "label": f"{label}:$.windows_summary.observed"})
        else:
            for index, window in enumerate(observed):
                window_label = f"{label}:$.windows_summary.observed[{index}]"
                if not isinstance(window, dict):
                    blockers.append({"reason": "uobject_flag_policy_observed_window_not_object", "label": window_label})
                    continue
                name = window.get("name")
                if isinstance(name, str):
                    observed_names.add(name)
                else:
                    blockers.append({"reason": "uobject_flag_policy_window_name_invalid", "label": f"{window_label}.name"})
                if not isinstance(window.get("artifact_sha256"), str) or SHA256_RE.fullmatch(window["artifact_sha256"]) is None:
                    blockers.append({"reason": "uobject_flag_policy_window_sha256_invalid", "label": f"{window_label}.artifact_sha256"})
                byte_count = window.get("byte_count")
                if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
                    blockers.append({"reason": "uobject_flag_policy_window_byte_count_invalid", "label": f"{window_label}.byte_count"})
                if window.get("path_redacted") is not True:
                    blockers.append({"reason": "uobject_flag_policy_window_path_not_redacted", "label": f"{window_label}.path_redacted"})
                matched = window.get("matched_patterns")
                if not isinstance(matched, list) or not matched or any(not isinstance(pattern, str) for pattern in matched):
                    blockers.append({"reason": "uobject_flag_policy_window_patterns_missing", "label": f"{window_label}.matched_patterns"})
                elif isinstance(name, str) and name in REQUIRED_UOBJECT_FLAG_POLICY_WINDOW_PATTERNS:
                    expected_patterns = REQUIRED_UOBJECT_FLAG_POLICY_WINDOW_PATTERNS[name]
                    recorded_patterns = set(matched)
                    missing_patterns = sorted(expected_patterns - recorded_patterns)
                    unexpected_patterns = sorted(recorded_patterns - expected_patterns)
                    if missing_patterns or unexpected_patterns:
                        blockers.append(
                            {
                                "reason": "uobject_flag_policy_window_required_patterns_mismatch",
                                "label": f"{window_label}.matched_patterns",
                                "expected": sorted(expected_patterns),
                                "missing": missing_patterns,
                                "unexpected": unexpected_patterns,
                                "recorded": matched,
                            }
                        )
                provenance = window.get("provenance")
                if not isinstance(provenance, dict) or provenance.get("verified") is not True or provenance.get("path_redacted") is not True:
                    blockers.append({"reason": "uobject_flag_policy_window_provenance_missing", "label": f"{window_label}.provenance"})
                else:
                    if provenance.get("schema") not in UOBJECT_FLAG_TRANSITION_PROVENANCE_SCHEMAS:
                        blockers.append(
                            {
                                "reason": "uobject_flag_policy_window_provenance_schema_mismatch",
                                "label": f"{window_label}.provenance.schema",
                                "recorded_schema": provenance.get("schema"),
                            }
                        )
                    if provenance.get("artifact_sha256") != window.get("artifact_sha256"):
                        blockers.append(
                            {
                                "reason": "uobject_flag_policy_window_provenance_artifact_sha256_mismatch",
                                "label": f"{window_label}.provenance.artifact_sha256",
                                "expected_artifact_sha256": window.get("artifact_sha256"),
                                "recorded_artifact_sha256": provenance.get("artifact_sha256"),
                            }
                        )
                    if isinstance(recorded_sha, str) and provenance.get("binary_sha256") != recorded_sha:
                        blockers.append(
                            {
                                "reason": "uobject_flag_policy_window_provenance_binary_sha256_mismatch",
                                "label": f"{window_label}.provenance.binary_sha256",
                                "expected_binary_sha256": recorded_sha,
                                "recorded_binary_sha256": provenance.get("binary_sha256"),
                            }
                        )
                    if not isinstance(provenance.get("sidecar_sha256"), str) or SHA256_RE.fullmatch(provenance["sidecar_sha256"]) is None:
                        blockers.append(
                            {
                                "reason": "uobject_flag_policy_window_provenance_sidecar_sha256_invalid",
                                "label": f"{window_label}.provenance.sidecar_sha256",
                                "recorded_sidecar_sha256": provenance.get("sidecar_sha256"),
                            }
                        )
        if observed_names != REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS:
            blockers.append(
                {
                    "reason": "uobject_flag_policy_required_windows_mismatch",
                    "label": f"{label}:$.windows_summary.observed",
                    "expected": sorted(REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS),
                    "recorded": sorted(observed_names),
                }
            )
        if isinstance(observed, list) and len(observed) != len(REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS):
            blockers.append(
                {
                    "reason": "uobject_flag_policy_observed_window_count_mismatch",
                    "label": f"{label}:$.windows_summary.observed",
                    "expected": len(REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS),
                    "recorded": len(observed),
                }
            )

    blockers_list = payload.get("remaining_blockers")
    if not isinstance(blockers_list, list) or not REQUIRED_UOBJECT_FLAG_POLICY_BLOCKERS.issubset(set(blockers_list)):
        blockers.append(
            {
                "reason": "uobject_flag_policy_remaining_blockers_missing",
                "label": f"{label}:$.remaining_blockers",
                "expected": sorted(REQUIRED_UOBJECT_FLAG_POLICY_BLOCKERS),
                "recorded": blockers_list,
            }
        )
    elif any(not isinstance(blocker, str) for blocker in blockers_list):
        blockers.append({"reason": "uobject_flag_policy_remaining_blockers_invalid", "label": f"{label}:$.remaining_blockers"})
    else:
        extra_blockers = [blocker for blocker in blockers_list if blocker not in REQUIRED_UOBJECT_FLAG_POLICY_BLOCKERS]
        for trail, _, reason in collect_candidate_public_overclaims(extra_blockers, allowed_prefixes=()):
            blockers.append({"reason": f"uobject_flag_policy_remaining_blockers_public_overclaim_{reason}", "label": f"{label}:$.remaining_blockers:{trail}"})
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_UOBJECT_FLAG_POLICY_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "uobject_flag_policy_non_claims_missing",
                "label": f"{label}:$.non_claims",
                "expected": sorted(REQUIRED_UOBJECT_FLAG_POLICY_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    elif any(not isinstance(non_claim, str) for non_claim in non_claims):
        blockers.append({"reason": "uobject_flag_policy_non_claims_invalid", "label": f"{label}:$.non_claims"})
    else:
        extra_non_claims = [non_claim for non_claim in non_claims if non_claim not in REQUIRED_UOBJECT_FLAG_POLICY_NON_CLAIMS]
        for trail, _, reason in collect_candidate_public_overclaims(extra_non_claims, allowed_prefixes=()):
            blockers.append({"reason": f"uobject_flag_policy_non_claims_public_overclaim_{reason}", "label": f"{label}:$.non_claims:{trail}"})
    if mode == "promote":
        blockers.append({"reason": "promote_mode_uobject_flag_policy_candidate_only", "label": label})
    lower_strings = [value.casefold() for _, value in collect_string_fields(payload)]
    for forbidden in ("pending-kill", "pending kill", "destroyed", "unreachable"):
        if any(forbidden in value for value in lower_strings):
            blockers.append({"reason": "uobject_flag_policy_ue_lifecycle_name_overclaim", "label": label, "forbidden": forbidden})
    return blockers


def validate_uobject_flag_transition_matrix_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
    expected_binary_sha256: str | None,
) -> list[dict[str, Any]]:
    if payload.get("schema") != UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    if payload.get("evidence_kind") != "static_uobject_plus_0x8_flag_transition_candidate":
        blockers.append({"reason": "uobject_flag_transition_evidence_kind_mismatch", "label": f"{label}:$.evidence_kind"})
    if payload.get("status") != "candidate_blocked":
        blockers.append({"reason": "uobject_flag_transition_status_not_candidate_blocked", "label": f"{label}:$.status"})

    contract = payload.get("builder_contract")
    if not isinstance(contract, dict):
        blockers.append({"reason": "uobject_flag_transition_missing_builder_contract", "label": f"{label}:$.builder_contract"})
    else:
        expected_false = {
            "requires_live_server": "uobject_flag_transition_requires_live_server_overclaim",
            "promotion_ready": "uobject_flag_transition_promotion_ready_overclaim",
            "resource_handle_claim": "uobject_flag_transition_resourcehandle_overclaim",
            "public_lifecycle_names_assigned": "uobject_flag_transition_lifecycle_name_overclaim",
        }
        for key, reason in expected_false.items():
            if contract.get(key) is not False:
                blockers.append({"reason": reason, "label": f"{label}:$.builder_contract.{key}"})
        if contract.get("fail_closed") is not True:
            blockers.append({"reason": "uobject_flag_transition_not_fail_closed", "label": f"{label}:$.builder_contract.fail_closed"})
        if contract.get("matrix_kind") != "semantic_helper_windows":
            blockers.append({"reason": "uobject_flag_transition_matrix_kind_mismatch", "label": f"{label}:$.builder_contract.matrix_kind"})

    for trail, raw_value in collect_bool_fields(payload):
        key = trail.rsplit(".", 1)[-1]
        if raw_value is True and key in READY_OVERCLAIM_KEYS:
            blockers.append({"reason": "uobject_flag_transition_readiness_overclaim", "label": f"{label}:{trail}"})

    binary = payload.get("binary")
    recorded_binary_sha256: str | None = None
    if not isinstance(binary, dict):
        blockers.append({"reason": "uobject_flag_transition_missing_binary", "label": f"{label}:$.binary"})
    else:
        recorded_sha = binary.get("sha256")
        if not isinstance(recorded_sha, str) or SHA256_RE.fullmatch(recorded_sha) is None:
            blockers.append({"reason": "uobject_flag_transition_binary_sha256_invalid", "label": f"{label}:$.binary.sha256"})
        else:
            recorded_binary_sha256 = recorded_sha
        if expected_binary_sha256 is not None and recorded_sha != expected_binary_sha256:
            blockers.append(
                {
                    "reason": "uobject_flag_transition_binary_sha256_mismatch",
                    "label": f"{label}:$.binary.sha256",
                    "expected_binary_sha256": expected_binary_sha256,
                    "recorded_binary_sha256": recorded_sha,
                }
            )
        if binary.get("path_redacted") is not True:
            blockers.append({"reason": "uobject_flag_transition_binary_path_not_redacted", "label": f"{label}:$.binary.path_redacted"})

    windows = payload.get("windows_summary")
    observed_names: set[str] = set()
    if not isinstance(windows, dict):
        blockers.append({"reason": "uobject_flag_transition_missing_windows_summary", "label": f"{label}:$.windows_summary"})
    else:
        if windows.get("all_required_present") is not True:
            blockers.append({"reason": "uobject_flag_transition_required_windows_not_present", "label": f"{label}:$.windows_summary"})
        if windows.get("all_required_patterns_present") is not True:
            blockers.append({"reason": "uobject_flag_transition_required_patterns_not_present", "label": f"{label}:$.windows_summary"})
        required = windows.get("required")
        if (
            not isinstance(required, list)
            or any(not isinstance(name, str) for name in required)
            or set(required) != REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOWS
            or len(required) != len(REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOWS)
        ):
            blockers.append(
                {
                    "reason": "uobject_flag_transition_required_windows_field_mismatch",
                    "label": f"{label}:$.windows_summary.required",
                    "expected": sorted(REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOWS),
                    "recorded": required,
                }
            )
        optional = windows.get("optional")
        if (
            not isinstance(optional, list)
            or any(not isinstance(name, str) for name in optional)
            or not set(optional).issubset(OPTIONAL_UOBJECT_FLAG_TRANSITION_WINDOWS)
            or len(optional) != len(set(optional))
        ):
            blockers.append(
                {
                    "reason": "uobject_flag_transition_optional_windows_field_mismatch",
                    "label": f"{label}:$.windows_summary.optional",
                    "expected_allowed": sorted(OPTIONAL_UOBJECT_FLAG_TRANSITION_WINDOWS),
                    "recorded": optional,
                }
            )
        groups = windows.get("groups")
        if not isinstance(groups, dict) or not REQUIRED_UOBJECT_FLAG_TRANSITION_GROUPS.issubset(set(groups)):
            blockers.append({"reason": "uobject_flag_transition_window_groups_missing", "label": f"{label}:$.windows_summary.groups"})
        elif not all(isinstance(groups.get(group), list) and groups.get(group) for group in REQUIRED_UOBJECT_FLAG_TRANSITION_GROUPS):
            blockers.append({"reason": "uobject_flag_transition_window_group_empty", "label": f"{label}:$.windows_summary.groups"})
        observed = windows.get("observed")
        allowed_observed_windows = REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOWS | OPTIONAL_UOBJECT_FLAG_TRANSITION_WINDOWS
        if not isinstance(observed, list):
            blockers.append({"reason": "uobject_flag_transition_observed_windows_not_list", "label": f"{label}:$.windows_summary.observed"})
        else:
            for index, window in enumerate(observed):
                window_label = f"{label}:$.windows_summary.observed[{index}]"
                if not isinstance(window, dict):
                    blockers.append({"reason": "uobject_flag_transition_observed_window_not_object", "label": window_label})
                    continue
                name = window.get("name")
                if isinstance(name, str):
                    if name in observed_names:
                        blockers.append({"reason": "uobject_flag_transition_observed_window_duplicate", "label": f"{window_label}.name"})
                    observed_names.add(name)
                    if name not in allowed_observed_windows:
                        blockers.append({"reason": "uobject_flag_transition_observed_window_unknown", "label": f"{window_label}.name", "recorded": name})
                else:
                    blockers.append({"reason": "uobject_flag_transition_window_name_invalid", "label": f"{window_label}.name"})
                if not isinstance(window.get("artifact_sha256"), str) or SHA256_RE.fullmatch(window["artifact_sha256"]) is None:
                    blockers.append({"reason": "uobject_flag_transition_window_sha256_invalid", "label": f"{window_label}.artifact_sha256"})
                byte_count = window.get("byte_count")
                if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
                    blockers.append({"reason": "uobject_flag_transition_window_byte_count_invalid", "label": f"{window_label}.byte_count"})
                if window.get("path_redacted") is not True:
                    blockers.append({"reason": "uobject_flag_transition_window_path_not_redacted", "label": f"{window_label}.path_redacted"})
                matched = window.get("matched_patterns")
                if not isinstance(matched, list) or not matched or any(not isinstance(pattern, str) for pattern in matched):
                    blockers.append({"reason": "uobject_flag_transition_window_patterns_missing", "label": f"{window_label}.matched_patterns"})
                elif isinstance(name, str) and name in REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOW_PATTERNS:
                    expected_patterns = REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOW_PATTERNS[name]
                    missing_patterns = sorted(expected_patterns - set(matched))
                    if missing_patterns:
                        blockers.append(
                            {
                                "reason": "uobject_flag_transition_window_required_patterns_mismatch",
                                "label": f"{window_label}.matched_patterns",
                                "expected": sorted(expected_patterns),
                                "missing": missing_patterns,
                                "recorded": matched,
                            }
                        )
                provenance = window.get("provenance")
                if not isinstance(provenance, dict) or provenance.get("verified") is not True or provenance.get("path_redacted") is not True:
                    blockers.append({"reason": "uobject_flag_transition_window_provenance_missing", "label": f"{window_label}.provenance"})
                elif isinstance(name, str):
                    if provenance.get("schema") not in UOBJECT_FLAG_TRANSITION_PROVENANCE_SCHEMAS:
                        blockers.append(
                            {
                                "reason": "uobject_flag_transition_window_provenance_schema_mismatch",
                                "label": f"{window_label}.provenance.schema",
                                "recorded_schema": provenance.get("schema"),
                            }
                        )
                    if provenance.get("artifact_sha256") != window.get("artifact_sha256"):
                        blockers.append(
                            {
                                "reason": "uobject_flag_transition_window_provenance_artifact_sha256_mismatch",
                                "label": f"{window_label}.provenance.artifact_sha256",
                                "expected_artifact_sha256": window.get("artifact_sha256"),
                                "recorded_artifact_sha256": provenance.get("artifact_sha256"),
                            }
                        )
                    if recorded_binary_sha256 is not None and provenance.get("binary_sha256") != recorded_binary_sha256:
                        blockers.append(
                            {
                                "reason": "uobject_flag_transition_window_provenance_binary_sha256_mismatch",
                                "label": f"{window_label}.provenance.binary_sha256",
                                "expected_binary_sha256": recorded_binary_sha256,
                                "recorded_binary_sha256": provenance.get("binary_sha256"),
                            }
                        )
                    if not isinstance(provenance.get("sidecar_sha256"), str) or SHA256_RE.fullmatch(provenance["sidecar_sha256"]) is None:
                        blockers.append(
                            {
                                "reason": "uobject_flag_transition_window_provenance_sidecar_sha256_invalid",
                                "label": f"{window_label}.provenance.sidecar_sha256",
                                "recorded_sidecar_sha256": provenance.get("sidecar_sha256"),
                            }
                        )
        if not REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOWS.issubset(observed_names):
            blockers.append(
                {
                    "reason": "uobject_flag_transition_required_windows_mismatch",
                    "label": f"{label}:$.windows_summary.observed",
                    "expected": sorted(REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOWS),
                    "recorded": sorted(observed_names),
                }
            )
        for group_name in REQUIRED_UOBJECT_FLAG_TRANSITION_GROUPS:
            if isinstance(groups, dict) and isinstance(groups.get(group_name), list):
                unknown_group_windows = sorted(set(groups[group_name]) - observed_names)
                if unknown_group_windows:
                    blockers.append(
                        {
                            "reason": "uobject_flag_transition_group_window_not_observed",
                            "label": f"{label}:$.windows_summary.groups.{group_name}",
                            "recorded": unknown_group_windows,
                        }
                    )

    matrix = payload.get("transition_matrix")
    if not isinstance(matrix, dict) or set(matrix) != {"0x100", "0x4000", "0x8000"}:
        blockers.append({"reason": "uobject_flag_transition_matrix_keys_mismatch", "label": f"{label}:$.transition_matrix"})
    else:
        cited_windows: set[str] = set()
        for mask, entry in matrix.items():
            entry_label = f"{label}:$.transition_matrix.{mask}"
            if not isinstance(entry, dict):
                blockers.append({"reason": "uobject_flag_transition_matrix_entry_not_object", "label": entry_label})
                continue
            for key in ("predicate_windows", "mutation_windows"):
                value = entry.get(key)
                if not isinstance(value, list) or any(not isinstance(name, str) for name in value):
                    blockers.append({"reason": "uobject_flag_transition_matrix_windows_invalid", "label": f"{entry_label}.{key}"})
                    continue
                cited_windows.update(value)
            if mask == "0x8000" and entry.get("predicate_windows") != []:
                blockers.append({"reason": "uobject_flag_transition_8000_predicate_overclaim", "label": entry_label})
        unobserved_cited_windows = sorted(cited_windows - observed_names)
        if unobserved_cited_windows:
            blockers.append(
                {
                    "reason": "uobject_flag_transition_matrix_window_not_observed",
                    "label": f"{label}:$.transition_matrix",
                    "recorded": unobserved_cited_windows,
                }
            )

    blockers_list = payload.get("remaining_blockers")
    if not isinstance(blockers_list, list) or not REQUIRED_UOBJECT_FLAG_TRANSITION_BLOCKERS.issubset(set(blockers_list)):
        blockers.append(
            {
                "reason": "uobject_flag_transition_remaining_blockers_missing",
                "label": f"{label}:$.remaining_blockers",
                "expected": sorted(REQUIRED_UOBJECT_FLAG_TRANSITION_BLOCKERS),
                "recorded": blockers_list,
            }
        )
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_UOBJECT_FLAG_TRANSITION_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "uobject_flag_transition_non_claims_missing",
                "label": f"{label}:$.non_claims",
                "expected": sorted(REQUIRED_UOBJECT_FLAG_TRANSITION_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    if mode == "promote":
        blockers.append({"reason": "promote_mode_uobject_flag_transition_candidate_only", "label": label})
    lower_strings = [value.casefold() for _, value in collect_string_fields(payload)]
    for forbidden in ("pending-kill", "pending kill", "destroyed", "unreachable"):
        if any(forbidden in value for value in lower_strings):
            blockers.append({"reason": "uobject_flag_transition_ue_lifecycle_name_overclaim", "label": label, "forbidden": forbidden})
    return blockers


def validate_uobject_flag_sample_report_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
    expected_binary_sha256: str | None,
) -> list[dict[str, Any]]:
    if payload.get("schema") != UOBJECT_FLAG_SAMPLE_REPORT_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    if payload.get("status") != "candidate_blocked":
        blockers.append({"reason": "uobject_flag_sample_status_not_candidate_blocked", "label": f"{label}:$.status"})
    if payload.get("promotion_ready") is not False:
        blockers.append({"reason": "uobject_flag_sample_promotion_ready_overclaim", "label": f"{label}:$.promotion_ready"})
    if payload.get("resource_handle_claim") is not False:
        blockers.append({"reason": "uobject_flag_sample_resourcehandle_overclaim", "label": f"{label}:$.resource_handle_claim"})
    if payload.get("post_callback_resource_handle_ready") is not False:
        blockers.append({"reason": "uobject_flag_sample_post_callback_ready_overclaim", "label": f"{label}:$.post_callback_resource_handle_ready"})

    binary = payload.get("binary")
    recorded_binary_sha256: str | None = None
    if not isinstance(binary, dict):
        blockers.append({"reason": "uobject_flag_sample_missing_binary", "label": f"{label}:$.binary"})
    else:
        for trail, _ in collect_path_fields(binary, trail="$.binary"):
            blockers.append({"reason": "uobject_flag_sample_binary_path_present", "label": f"{label}:{trail}"})
        recorded_sha = binary.get("sha256")
        if not isinstance(recorded_sha, str) or SHA256_RE.fullmatch(recorded_sha) is None:
            blockers.append({"reason": "uobject_flag_sample_binary_sha256_invalid", "label": f"{label}:$.binary.sha256"})
        else:
            recorded_binary_sha256 = recorded_sha
        if expected_binary_sha256 is not None and recorded_sha != expected_binary_sha256:
            blockers.append(
                {
                    "reason": "uobject_flag_sample_binary_sha256_mismatch",
                    "label": f"{label}:$.binary.sha256",
                    "expected_binary_sha256": expected_binary_sha256,
                    "recorded_binary_sha256": recorded_sha,
                }
            )
        if binary.get("path_redacted") is not True:
            blockers.append({"reason": "uobject_flag_sample_binary_path_not_redacted", "label": f"{label}:$.binary.path_redacted"})

    sources = payload.get("source_artifacts")
    observed_source_schemas: set[str] = set()
    if not isinstance(sources, list) or not sources:
        blockers.append({"reason": "uobject_flag_sample_source_artifacts_missing", "label": f"{label}:$.source_artifacts"})
    else:
        for index, source in enumerate(sources):
            source_label = f"{label}:$.source_artifacts[{index}]"
            if not isinstance(source, dict):
                blockers.append({"reason": "uobject_flag_sample_source_artifact_not_object", "label": source_label})
                continue
            for trail, _ in collect_path_fields(source, trail=f"$.source_artifacts[{index}]"):
                blockers.append({"reason": "uobject_flag_sample_source_artifact_path_present", "label": f"{label}:{trail}"})
            if source.get("schema") not in {UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA, UOBJECT_FLAG_POLICY_REPORT_SCHEMA}:
                blockers.append({"reason": "uobject_flag_sample_source_schema_mismatch", "label": f"{source_label}.schema"})
            else:
                observed_source_schemas.add(source["schema"])
            if source.get("path_redacted") is not True:
                blockers.append({"reason": "uobject_flag_sample_source_path_not_redacted", "label": f"{source_label}.path_redacted"})
            if not isinstance(source.get("artifact_sha256"), str) or SHA256_RE.fullmatch(source["artifact_sha256"]) is None:
                blockers.append({"reason": "uobject_flag_sample_source_artifact_sha256_invalid", "label": f"{source_label}.artifact_sha256"})
            if recorded_binary_sha256 is not None and source.get("binary_sha256") != recorded_binary_sha256:
                blockers.append({"reason": "uobject_flag_sample_source_binary_sha256_mismatch", "label": f"{source_label}.binary_sha256"})
            consume_gate = source.get("consume_gate")
            if not isinstance(consume_gate, dict):
                blockers.append({"reason": "uobject_flag_sample_source_consume_gate_missing", "label": f"{source_label}.consume_gate"})
            else:
                if consume_gate.get("schema") != SCHEMA:
                    blockers.append({"reason": "uobject_flag_sample_source_consume_gate_schema_mismatch", "label": f"{source_label}.consume_gate.schema"})
                if consume_gate.get("status") != "accepted":
                    blockers.append({"reason": "uobject_flag_sample_source_consume_gate_status_not_accepted", "label": f"{source_label}.consume_gate.status"})
                if consume_gate.get("mode") != "consume":
                    blockers.append({"reason": "uobject_flag_sample_source_consume_gate_mode_not_consume", "label": f"{source_label}.consume_gate.mode"})
                if consume_gate.get("blocker_count") != 0:
                    blockers.append({"reason": "uobject_flag_sample_source_consume_gate_has_blockers", "label": f"{source_label}.consume_gate.blocker_count"})
                if not isinstance(consume_gate.get("gate_sha256"), str) or SHA256_RE.fullmatch(consume_gate["gate_sha256"]) is None:
                    blockers.append({"reason": "uobject_flag_sample_source_consume_gate_sha256_invalid", "label": f"{source_label}.consume_gate.gate_sha256"})
                if consume_gate.get("path_redacted") is not True:
                    blockers.append({"reason": "uobject_flag_sample_source_consume_gate_path_not_redacted", "label": f"{source_label}.consume_gate.path_redacted"})
                if consume_gate.get("artifact_sha256") != source.get("artifact_sha256"):
                    blockers.append(
                        {
                            "reason": "uobject_flag_sample_source_consume_gate_artifact_sha256_mismatch",
                            "label": f"{source_label}.consume_gate.artifact_sha256",
                            "expected_artifact_sha256": source.get("artifact_sha256"),
                            "recorded_artifact_sha256": consume_gate.get("artifact_sha256"),
                        }
                    )
                if recorded_binary_sha256 is not None and consume_gate.get("binary_sha256") != recorded_binary_sha256:
                    blockers.append(
                        {
                            "reason": "uobject_flag_sample_source_consume_gate_binary_sha256_mismatch",
                            "label": f"{source_label}.consume_gate.binary_sha256",
                            "expected_binary_sha256": recorded_binary_sha256,
                            "recorded_binary_sha256": consume_gate.get("binary_sha256"),
                        }
                    )
    required_source_schemas = {UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA, UOBJECT_FLAG_POLICY_REPORT_SCHEMA}
    if observed_source_schemas != required_source_schemas:
        blockers.append(
            {
                "reason": "uobject_flag_sample_source_schema_coverage_missing",
                "label": f"{label}:$.source_artifacts",
                "expected": sorted(required_source_schemas),
                "recorded": sorted(observed_source_schemas),
            }
        )

    samples = payload.get("flag_samples")
    observed_masks: list[str] = []
    if not isinstance(samples, list) or not samples:
        blockers.append({"reason": "uobject_flag_sample_flag_samples_missing", "label": f"{label}:$.flag_samples"})
    else:
        for index, sample in enumerate(samples):
            sample_label = f"{label}:$.flag_samples[{index}]"
            if not isinstance(sample, dict):
                blockers.append({"reason": "uobject_flag_sample_not_object", "label": sample_label})
                continue
            for trail, _ in collect_path_fields(sample, trail=f"$.flag_samples[{index}]"):
                blockers.append({"reason": "uobject_flag_sample_path_present", "label": f"{label}:{trail}"})
            mask = sample.get("mask")
            if mask not in REQUIRED_UOBJECT_FLAG_SAMPLE_MASKS:
                blockers.append({"reason": "uobject_flag_sample_mask_invalid", "label": f"{sample_label}.mask", "recorded_mask": mask})
            else:
                observed_masks.append(mask)
            if sample.get("uobject_field") != "+0x8":
                blockers.append({"reason": "uobject_flag_sample_uobject_field_mismatch", "label": f"{sample_label}.uobject_field"})
            if sample.get("sample_kind") not in REQUIRED_UOBJECT_FLAG_SAMPLE_KINDS:
                blockers.append({"reason": "uobject_flag_sample_kind_invalid", "label": f"{sample_label}.sample_kind"})
            if sample.get("promotion_ready") is not False:
                blockers.append({"reason": "uobject_flag_sample_entry_promotion_ready_overclaim", "label": f"{sample_label}.promotion_ready"})
            if sample.get("public_lifecycle_name_assigned") is not False:
                blockers.append({"reason": "uobject_flag_sample_lifecycle_name_overclaim", "label": f"{sample_label}.public_lifecycle_name_assigned"})
            support = sample.get("support")
            if not isinstance(support, list) or not support or any(not is_safe_semantic_input_name(item) for item in support):
                blockers.append({"reason": "uobject_flag_sample_support_invalid", "label": f"{sample_label}.support"})
    observed_mask_counts = Counter(observed_masks)
    if set(observed_masks) != REQUIRED_UOBJECT_FLAG_SAMPLE_MASKS:
        blockers.append({"reason": "uobject_flag_sample_required_masks_missing", "label": f"{label}:$.flag_samples", "recorded_masks": sorted(set(observed_masks))})
    if len(observed_masks) != len(REQUIRED_UOBJECT_FLAG_SAMPLE_MASKS) or any(count != 1 for count in observed_mask_counts.values()):
        blockers.append({"reason": "uobject_flag_sample_mask_cardinality_mismatch", "label": f"{label}:$.flag_samples", "recorded_counts": dict(sorted(observed_mask_counts.items()))})

    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_UOBJECT_FLAG_SAMPLE_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append({"reason": "uobject_flag_sample_non_claims_missing", "label": f"{label}:$.non_claims"})
    remaining_blockers = payload.get("remaining_blockers")
    if not isinstance(remaining_blockers, list) or not REQUIRED_UOBJECT_FLAG_SAMPLE_BLOCKERS.issubset(set(remaining_blockers)):
        blockers.append({"reason": "uobject_flag_sample_remaining_blockers_missing", "label": f"{label}:$.remaining_blockers"})
    if mode == "promote":
        blockers.append({"reason": "promote_mode_uobject_flag_sample_candidate_only", "label": label})
    string_fields = collect_string_fields(payload)
    for trail, raw_value in string_fields:
        if raw_value != "redacted" and Path(raw_value).is_absolute():
            blockers.append({"reason": "uobject_flag_sample_absolute_path_string", "label": f"{label}:{trail}"})
    lower_strings = [value.casefold() for _, value in string_fields]
    for forbidden in FORBIDDEN_UOBJECT_FLAG_LIFECYCLE_STRINGS:
        if any(forbidden in value for value in lower_strings):
            blockers.append({"reason": "uobject_flag_sample_ue_lifecycle_name_overclaim", "label": label, "forbidden": forbidden})
    return blockers


def validate_uobject_flag_semantic_correlation_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
    expected_binary_sha256: str | None,
) -> list[dict[str, Any]]:
    if payload.get("schema") != UOBJECT_FLAG_SEMANTIC_CORRELATION_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    if payload.get("evidence_kind") != "static_uobject_flag_semantic_correlation_candidate":
        blockers.append({"reason": "uobject_flag_semantic_evidence_kind_mismatch", "label": f"{label}:$.evidence_kind"})
    if payload.get("status") != "candidate_blocked":
        blockers.append({"reason": "uobject_flag_semantic_status_not_candidate_blocked", "label": f"{label}:$.status"})
    if payload.get("promotion_ready") is not False:
        blockers.append({"reason": "uobject_flag_semantic_promotion_ready_overclaim", "label": f"{label}:$.promotion_ready"})

    contract = payload.get("builder_contract")
    if not isinstance(contract, dict):
        blockers.append({"reason": "uobject_flag_semantic_missing_builder_contract", "label": f"{label}:$.builder_contract"})
    else:
        expected_false = {
            "requires_live_server": "uobject_flag_semantic_requires_live_server_overclaim",
            "promotion_ready": "uobject_flag_semantic_contract_promotion_ready_overclaim",
            "resource_handle_claim": "uobject_flag_semantic_resourcehandle_overclaim",
            "public_lifecycle_names_assigned": "uobject_flag_semantic_lifecycle_name_overclaim",
            "lookup_promotion": "uobject_flag_semantic_lookup_overclaim",
            "mutation_promotion": "uobject_flag_semantic_mutation_overclaim",
            "return_override_promotion": "uobject_flag_semantic_return_override_overclaim",
        }
        for key, reason in expected_false.items():
            if contract.get(key) is not False:
                blockers.append({"reason": reason, "label": f"{label}:$.builder_contract.{key}"})
        if contract.get("fail_closed") is not True:
            blockers.append({"reason": "uobject_flag_semantic_not_fail_closed", "label": f"{label}:$.builder_contract.fail_closed"})

    for trail, raw_value in collect_bool_fields(payload):
        key = trail.rsplit(".", 1)[-1]
        if raw_value is True and key in READY_OVERCLAIM_KEYS:
            blockers.append({"reason": "uobject_flag_semantic_readiness_overclaim", "label": f"{label}:{trail}"})

    binary = payload.get("binary")
    recorded_binary_sha256: str | None = None
    if not isinstance(binary, dict):
        blockers.append({"reason": "uobject_flag_semantic_missing_binary", "label": f"{label}:$.binary"})
    else:
        for trail, _ in collect_path_fields(binary, trail="$.binary"):
            blockers.append({"reason": "uobject_flag_semantic_binary_path_present", "label": f"{label}:{trail}"})
        recorded_sha = binary.get("sha256")
        if not isinstance(recorded_sha, str) or SHA256_RE.fullmatch(recorded_sha) is None:
            blockers.append({"reason": "uobject_flag_semantic_binary_sha256_invalid", "label": f"{label}:$.binary.sha256"})
        else:
            recorded_binary_sha256 = recorded_sha
        if expected_binary_sha256 is not None and recorded_sha != expected_binary_sha256:
            blockers.append(
                {
                    "reason": "uobject_flag_semantic_binary_sha256_mismatch",
                    "label": f"{label}:$.binary.sha256",
                    "expected_binary_sha256": expected_binary_sha256,
                    "recorded_binary_sha256": recorded_sha,
                }
            )
        if binary.get("path_redacted") is not True:
            blockers.append({"reason": "uobject_flag_semantic_binary_path_not_redacted", "label": f"{label}:$.binary.path_redacted"})

    source_pack = payload.get("source_pack")
    if not isinstance(source_pack, dict) or source_pack.get("path_redacted") is not True:
        blockers.append({"reason": "uobject_flag_semantic_source_pack_not_redacted", "label": f"{label}:$.source_pack"})
    else:
        if not is_safe_semantic_input_name(source_pack.get("id")):
            blockers.append({"reason": "uobject_flag_semantic_source_pack_id_invalid", "label": f"{label}:$.source_pack.id"})
        for trail, _ in collect_path_fields(source_pack, trail="$.source_pack"):
            blockers.append({"reason": "uobject_flag_semantic_source_pack_path_present", "label": f"{label}:{trail}"})
        if not isinstance(source_pack.get("sha256"), str) or SHA256_RE.fullmatch(source_pack["sha256"]) is None:
            blockers.append({"reason": "uobject_flag_semantic_source_pack_sha256_invalid", "label": f"{label}:$.source_pack.sha256"})

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        blockers.append({"reason": "uobject_flag_semantic_inputs_missing", "label": f"{label}:$.inputs"})
    else:
        for input_name, input_record in inputs.items():
            input_label = f"{label}:$.inputs.{input_name}"
            if not is_safe_semantic_input_name(input_name):
                blockers.append({"reason": "uobject_flag_semantic_input_name_invalid", "label": f"{label}:$.inputs"})
                continue
            if not isinstance(input_record, dict):
                blockers.append({"reason": "uobject_flag_semantic_input_not_object", "label": input_label})
                continue
            for trail, _ in collect_path_fields(input_record, trail=f"$.inputs.{input_name}"):
                blockers.append({"reason": "uobject_flag_semantic_input_path_present", "label": f"{label}:{trail}"})
            if not isinstance(input_record.get("sha256"), str) or SHA256_RE.fullmatch(input_record["sha256"]) is None:
                blockers.append({"reason": "uobject_flag_semantic_input_sha256_invalid", "label": f"{input_label}.sha256"})
            byte_count = input_record.get("bytes")
            if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
                blockers.append({"reason": "uobject_flag_semantic_input_byte_count_invalid", "label": f"{input_label}.bytes"})
            if input_record.get("path_redacted") is not True:
                blockers.append({"reason": "uobject_flag_semantic_input_path_not_redacted", "label": f"{input_label}.path_redacted"})
            provenance = input_record.get("provenance")
            if not isinstance(provenance, dict) or provenance.get("verified") is not True or provenance.get("path_redacted") is not True:
                blockers.append({"reason": "uobject_flag_semantic_input_provenance_missing", "label": f"{input_label}.provenance"})
                continue
            for trail, _ in collect_path_fields(provenance, trail=f"$.inputs.{input_name}.provenance"):
                blockers.append({"reason": "uobject_flag_semantic_input_provenance_path_present", "label": f"{label}:{trail}"})
            if provenance.get("schema") not in UOBJECT_FLAG_TRANSITION_PROVENANCE_SCHEMAS:
                blockers.append(
                    {
                        "reason": "uobject_flag_semantic_input_provenance_schema_mismatch",
                        "label": f"{input_label}.provenance.schema",
                        "recorded_schema": provenance.get("schema"),
                    }
                )
            if provenance.get("artifact_sha256") != input_record.get("sha256"):
                blockers.append(
                    {
                        "reason": "uobject_flag_semantic_input_provenance_artifact_sha256_mismatch",
                        "label": f"{input_label}.provenance.artifact_sha256",
                        "expected_artifact_sha256": input_record.get("sha256"),
                        "recorded_artifact_sha256": provenance.get("artifact_sha256"),
                    }
                )
            if recorded_binary_sha256 is not None and provenance.get("binary_sha256") != recorded_binary_sha256:
                blockers.append(
                    {
                        "reason": "uobject_flag_semantic_input_provenance_binary_sha256_mismatch",
                        "label": f"{input_label}.provenance.binary_sha256",
                        "expected_binary_sha256": recorded_binary_sha256,
                        "recorded_binary_sha256": provenance.get("binary_sha256"),
                    }
                )
            if not isinstance(provenance.get("sidecar_sha256"), str) or SHA256_RE.fullmatch(provenance["sidecar_sha256"]) is None:
                blockers.append(
                    {
                        "reason": "uobject_flag_semantic_input_provenance_sidecar_sha256_invalid",
                        "label": f"{input_label}.provenance.sidecar_sha256",
                        "recorded_sidecar_sha256": provenance.get("sidecar_sha256"),
                    }
                )

    remaining_blockers = payload.get("remaining_blockers")
    if not isinstance(remaining_blockers, list) or not REQUIRED_UOBJECT_FLAG_SEMANTIC_BLOCKERS.issubset(set(remaining_blockers)):
        blockers.append(
            {
                "reason": "uobject_flag_semantic_remaining_blockers_missing",
                "label": f"{label}:$.remaining_blockers",
                "expected": sorted(REQUIRED_UOBJECT_FLAG_SEMANTIC_BLOCKERS),
                "recorded": remaining_blockers,
            }
        )
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_UOBJECT_FLAG_SEMANTIC_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "uobject_flag_semantic_non_claims_missing",
                "label": f"{label}:$.non_claims",
                "expected": sorted(REQUIRED_UOBJECT_FLAG_SEMANTIC_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    if mode == "promote":
        blockers.append({"reason": "promote_mode_uobject_flag_semantic_candidate_only", "label": label})
    for trail, _, reason in collect_candidate_public_overclaims(
        payload,
        allowed_prefixes=(
            "$.builder_contract",
            "$.remaining_blockers",
            "$.non_claims",
        ),
    ):
        blockers.append({"reason": f"uobject_flag_semantic_public_overclaim_{reason}", "label": f"{label}:{trail}"})
    lower_strings = [value.casefold() for _, value in collect_string_fields(payload)]
    for forbidden in ("pending-kill", "pending kill", "destroyed", "unreachable"):
        if any(forbidden in value for value in lower_strings):
            blockers.append({"reason": "uobject_flag_semantic_ue_lifecycle_name_overclaim", "label": label, "forbidden": forbidden})
    return blockers


def validate_embedded_static_provenance(
    provenance: object,
    *,
    label: str,
    expected_artifact_sha256: str | None,
    expected_binary_sha256: str | None,
    reason_prefix: str,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if not isinstance(provenance, dict) or provenance.get("verified") is not True or provenance.get("path_redacted") is not True:
        return [{"reason": f"{reason_prefix}_provenance_missing", "label": label}]

    for trail, _ in collect_path_fields(provenance, trail=label):
        blockers.append({"reason": f"{reason_prefix}_provenance_path_present", "label": trail})
    if provenance.get("schema") not in WEAK_HELPER_STATIC_POLARITY_PROVENANCE_SCHEMAS:
        blockers.append(
            {
                "reason": f"{reason_prefix}_provenance_schema_mismatch",
                "label": f"{label}.schema",
                "recorded_schema": provenance.get("schema"),
            }
        )
    if expected_artifact_sha256 is not None and provenance.get("artifact_sha256") != expected_artifact_sha256:
        blockers.append(
            {
                "reason": f"{reason_prefix}_provenance_artifact_sha256_mismatch",
                "label": f"{label}.artifact_sha256",
                "expected_artifact_sha256": expected_artifact_sha256,
                "recorded_artifact_sha256": provenance.get("artifact_sha256"),
            }
        )
    if expected_binary_sha256 is not None and provenance.get("binary_sha256") != expected_binary_sha256:
        blockers.append(
            {
                "reason": f"{reason_prefix}_provenance_binary_sha256_mismatch",
                "label": f"{label}.binary_sha256",
                "expected_binary_sha256": expected_binary_sha256,
                "recorded_binary_sha256": provenance.get("binary_sha256"),
            }
        )
    if not isinstance(provenance.get("sidecar_sha256"), str) or SHA256_RE.fullmatch(provenance["sidecar_sha256"]) is None:
        blockers.append(
            {
                "reason": f"{reason_prefix}_provenance_sidecar_sha256_invalid",
                "label": f"{label}.sidecar_sha256",
                "recorded_sidecar_sha256": provenance.get("sidecar_sha256"),
            }
        )
    return blockers


def validate_weak_helper_static_polarity_report_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
    expected_binary_sha256: str | None,
) -> list[dict[str, Any]]:
    if payload.get("schema") != WEAK_HELPER_STATIC_POLARITY_REPORT_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    if payload.get("evidence_kind") != "static_weak_helper_polarity_candidate":
        blockers.append({"reason": "weak_helper_static_polarity_evidence_kind_mismatch", "label": f"{label}:$.evidence_kind"})
    if payload.get("status") != "candidate_blocked":
        blockers.append({"reason": "weak_helper_static_polarity_status_not_candidate_blocked", "label": f"{label}:$.status"})
    if payload.get("promotion_ready") is not False:
        blockers.append({"reason": "weak_helper_static_polarity_promotion_ready_overclaim", "label": f"{label}:$.promotion_ready"})

    contract = payload.get("builder_contract")
    if not isinstance(contract, dict):
        blockers.append({"reason": "weak_helper_static_polarity_missing_builder_contract", "label": f"{label}:$.builder_contract"})
    else:
        expected_false = {
            "requires_live_server": "weak_helper_static_polarity_requires_live_server_overclaim",
            "promotion_ready": "weak_helper_static_polarity_contract_promotion_ready_overclaim",
            "resource_handle_claim": "weak_helper_static_polarity_resourcehandle_overclaim",
            "public_lifecycle_names_assigned": "weak_helper_static_polarity_lifecycle_name_overclaim",
            "lookup_promotion": "weak_helper_static_polarity_lookup_overclaim",
            "mutation_promotion": "weak_helper_static_polarity_mutation_overclaim",
            "return_override_promotion": "weak_helper_static_polarity_return_override_overclaim",
        }
        for key, reason in expected_false.items():
            if contract.get(key) is not False:
                blockers.append({"reason": reason, "label": f"{label}:$.builder_contract.{key}"})
        if contract.get("fail_closed") is not True:
            blockers.append({"reason": "weak_helper_static_polarity_not_fail_closed", "label": f"{label}:$.builder_contract.fail_closed"})

    for trail, raw_value in collect_bool_fields(payload):
        key = trail.rsplit(".", 1)[-1]
        if raw_value is True and key in READY_OVERCLAIM_KEYS:
            blockers.append({"reason": "weak_helper_static_polarity_readiness_overclaim", "label": f"{label}:{trail}"})

    binary = payload.get("binary")
    recorded_binary_sha256: str | None = None
    if not isinstance(binary, dict):
        blockers.append({"reason": "weak_helper_static_polarity_missing_binary", "label": f"{label}:$.binary"})
    else:
        for trail, _ in collect_path_fields(binary, trail="$.binary"):
            blockers.append({"reason": "weak_helper_static_polarity_binary_path_present", "label": f"{label}:{trail}"})
        recorded_sha = binary.get("sha256")
        if not isinstance(recorded_sha, str) or SHA256_RE.fullmatch(recorded_sha) is None:
            blockers.append({"reason": "weak_helper_static_polarity_binary_sha256_invalid", "label": f"{label}:$.binary.sha256"})
        else:
            recorded_binary_sha256 = recorded_sha
        if expected_binary_sha256 is not None and recorded_sha != expected_binary_sha256:
            blockers.append(
                {
                    "reason": "weak_helper_static_polarity_binary_sha256_mismatch",
                    "label": f"{label}:$.binary.sha256",
                    "expected_binary_sha256": expected_binary_sha256,
                    "recorded_binary_sha256": recorded_sha,
                }
            )
        if binary.get("path_redacted") is not True:
            blockers.append({"reason": "weak_helper_static_polarity_binary_path_not_redacted", "label": f"{label}:$.binary.path_redacted"})

    source_pack = payload.get("source_pack")
    if not isinstance(source_pack, dict) or source_pack.get("path_redacted") is not True:
        blockers.append({"reason": "weak_helper_static_polarity_source_pack_not_redacted", "label": f"{label}:$.source_pack"})
    else:
        if not is_safe_semantic_input_name(source_pack.get("id")):
            blockers.append({"reason": "weak_helper_static_polarity_source_pack_id_invalid", "label": f"{label}:$.source_pack.id"})
        for trail, _ in collect_path_fields(source_pack, trail="$.source_pack"):
            blockers.append({"reason": "weak_helper_static_polarity_source_pack_path_present", "label": f"{label}:{trail}"})
        source_pack_sha256 = source_pack.get("sha256")
        if not isinstance(source_pack_sha256, str) or SHA256_RE.fullmatch(source_pack_sha256) is None:
            blockers.append({"reason": "weak_helper_static_polarity_source_pack_sha256_invalid", "label": f"{label}:$.source_pack.sha256"})
            source_pack_sha256 = None
        blockers.extend(
            validate_embedded_static_provenance(
                source_pack.get("provenance"),
                label=f"{label}:$.source_pack.provenance",
                expected_artifact_sha256=source_pack_sha256,
                expected_binary_sha256=recorded_binary_sha256,
                reason_prefix="weak_helper_static_polarity_source_pack",
            )
        )

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        blockers.append({"reason": "weak_helper_static_polarity_inputs_missing", "label": f"{label}:$.inputs"})
    else:
        for input_name, input_record in inputs.items():
            input_label = f"{label}:$.inputs.{input_name}"
            if not is_safe_semantic_input_name(input_name):
                blockers.append({"reason": "weak_helper_static_polarity_input_name_invalid", "label": f"{label}:$.inputs"})
                continue
            if not isinstance(input_record, dict):
                blockers.append({"reason": "weak_helper_static_polarity_input_not_object", "label": input_label})
                continue
            for trail, _ in collect_path_fields(input_record, trail=f"$.inputs.{input_name}"):
                blockers.append({"reason": "weak_helper_static_polarity_input_path_present", "label": f"{label}:{trail}"})
            input_sha256 = input_record.get("sha256")
            if not isinstance(input_sha256, str) or SHA256_RE.fullmatch(input_sha256) is None:
                blockers.append({"reason": "weak_helper_static_polarity_input_sha256_invalid", "label": f"{input_label}.sha256"})
                input_sha256 = None
            byte_count = input_record.get("bytes")
            if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
                blockers.append({"reason": "weak_helper_static_polarity_input_byte_count_invalid", "label": f"{input_label}.bytes"})
            if input_record.get("path_redacted") is not True:
                blockers.append({"reason": "weak_helper_static_polarity_input_path_not_redacted", "label": f"{input_label}.path_redacted"})
            blockers.extend(
                validate_embedded_static_provenance(
                    input_record.get("provenance"),
                    label=f"{input_label}.provenance",
                    expected_artifact_sha256=input_sha256,
                    expected_binary_sha256=recorded_binary_sha256,
                    reason_prefix="weak_helper_static_polarity_input",
                )
            )

    remaining_blockers = payload.get("remaining_blockers")
    if not isinstance(remaining_blockers, list) or not REQUIRED_WEAK_HELPER_STATIC_POLARITY_BLOCKERS.issubset(set(remaining_blockers)):
        blockers.append(
            {
                "reason": "weak_helper_static_polarity_remaining_blockers_missing",
                "label": f"{label}:$.remaining_blockers",
                "expected": sorted(REQUIRED_WEAK_HELPER_STATIC_POLARITY_BLOCKERS),
                "recorded": remaining_blockers,
            }
        )
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_WEAK_HELPER_STATIC_POLARITY_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "weak_helper_static_polarity_non_claims_missing",
                "label": f"{label}:$.non_claims",
                "expected": sorted(REQUIRED_WEAK_HELPER_STATIC_POLARITY_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    if mode == "promote":
        blockers.append({"reason": "promote_mode_weak_helper_static_polarity_candidate_only", "label": label})
    lower_strings = [value.casefold() for _, value in collect_string_fields(payload)]
    for forbidden in ("pending-kill", "pending kill", "destroyed", "unreachable"):
        if any(forbidden in value for value in lower_strings):
            blockers.append({"reason": "weak_helper_static_polarity_ue_lifecycle_name_overclaim", "label": label, "forbidden": forbidden})
    return blockers


def validate_weak_helper_polarity_caller_mode_report_manifest(
    payload: dict[str, Any],
    *,
    label: str,
    mode: str,
    expected_binary_sha256: str | None,
) -> list[dict[str, Any]]:
    if payload.get("schema") != WEAK_HELPER_POLARITY_CALLER_MODE_REPORT_SCHEMA:
        return []

    blockers: list[dict[str, Any]] = []
    if payload.get("status") != "candidate_blocked":
        blockers.append({"reason": "weak_helper_polarity_caller_mode_status_not_candidate_blocked", "label": f"{label}:$.status"})
    if payload.get("consumption_scope") != "internal_static_research_only":
        blockers.append({"reason": "weak_helper_polarity_caller_mode_scope_mismatch", "label": f"{label}:$.consumption_scope"})

    binary = payload.get("binary")
    if not isinstance(binary, dict):
        blockers.append({"reason": "weak_helper_polarity_caller_mode_missing_binary", "label": f"{label}:$.binary"})
    else:
        for trail, _ in collect_path_fields(binary, trail="$.binary"):
            blockers.append({"reason": "weak_helper_polarity_caller_mode_binary_path_present", "label": f"{label}:{trail}"})
        recorded_sha = binary.get("sha256")
        if not isinstance(recorded_sha, str) or SHA256_RE.fullmatch(recorded_sha) is None:
            blockers.append({"reason": "weak_helper_polarity_caller_mode_binary_sha256_invalid", "label": f"{label}:$.binary.sha256"})
        elif expected_binary_sha256 is not None and recorded_sha != expected_binary_sha256:
            blockers.append(
                {
                    "reason": "weak_helper_polarity_caller_mode_binary_sha256_mismatch",
                    "label": f"{label}:$.binary.sha256",
                    "expected_binary_sha256": expected_binary_sha256,
                    "recorded_binary_sha256": recorded_sha,
                }
            )
        if binary.get("path_redacted") is not True:
            blockers.append({"reason": "weak_helper_polarity_caller_mode_binary_path_not_redacted", "label": f"{label}:$.binary.path_redacted"})

    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, dict) or not source_artifacts:
        blockers.append({"reason": "weak_helper_polarity_caller_mode_source_artifacts_missing", "label": f"{label}:$.source_artifacts"})
    else:
        for artifact_name, artifact in source_artifacts.items():
            artifact_label = f"{label}:$.source_artifacts.{artifact_name}"
            if not is_safe_semantic_input_name(artifact_name):
                blockers.append({"reason": "weak_helper_polarity_caller_mode_source_artifact_name_invalid", "label": f"{label}:$.source_artifacts"})
                continue
            if not isinstance(artifact, dict):
                blockers.append({"reason": "weak_helper_polarity_caller_mode_source_artifact_not_object", "label": artifact_label})
                continue
            for trail, _ in collect_path_fields(artifact, trail=f"$.source_artifacts.{artifact_name}"):
                blockers.append({"reason": "weak_helper_polarity_caller_mode_source_artifact_path_present", "label": f"{label}:{trail}"})
            if artifact.get("path_redacted") is not True:
                blockers.append({"reason": "weak_helper_polarity_caller_mode_source_artifact_path_not_redacted", "label": f"{artifact_label}.path_redacted"})
            if not isinstance(artifact.get("sha256"), str) or SHA256_RE.fullmatch(artifact["sha256"]) is None:
                blockers.append({"reason": "weak_helper_polarity_caller_mode_source_artifact_sha256_invalid", "label": f"{artifact_label}.sha256"})

    helpers = payload.get("helpers")
    if not isinstance(helpers, dict) or not helpers:
        blockers.append({"reason": "weak_helper_polarity_caller_mode_helpers_missing", "label": f"{label}:$.helpers"})
    else:
        for helper_id, helper in helpers.items():
            helper_label = f"{label}:$.helpers.{helper_id}"
            if not isinstance(helper_id, str) or re.fullmatch(r"0x[0-9a-fA-F]+", helper_id) is None:
                blockers.append({"reason": "weak_helper_polarity_caller_mode_helper_id_invalid", "label": f"{label}:$.helpers"})
                continue
            if not isinstance(helper, dict):
                blockers.append({"reason": "weak_helper_polarity_caller_mode_helper_not_object", "label": helper_label})
                continue
            for trail, _ in collect_path_fields(helper, trail=f"$.helpers.{helper_id}"):
                blockers.append({"reason": "weak_helper_polarity_caller_mode_helper_path_present", "label": f"{label}:{trail}"})
            if not isinstance(helper.get("window"), str) or "/" in helper["window"] or "\\" in helper["window"]:
                blockers.append({"reason": "weak_helper_polarity_caller_mode_helper_window_invalid", "label": f"{helper_label}.window"})
            if helper.get("return_kind") not in {
                "boolean_like_inverted_at_exit",
                "boolean_like_strict_validity",
                "boolean_like",
                "uobject_pointer_or_null_strict",
                "uobject_pointer_or_null_mode_dependent",
            }:
                blockers.append({"reason": "weak_helper_polarity_caller_mode_helper_return_kind_invalid", "label": f"{helper_label}.return_kind"})

    remaining_blockers = payload.get("remaining_blockers")
    if not isinstance(remaining_blockers, list) or not REQUIRED_WEAK_HELPER_POLARITY_CALLER_MODE_BLOCKERS.issubset(set(remaining_blockers)):
        blockers.append(
            {
                "reason": "weak_helper_polarity_caller_mode_remaining_blockers_missing",
                "label": f"{label}:$.remaining_blockers",
                "expected": sorted(REQUIRED_WEAK_HELPER_POLARITY_CALLER_MODE_BLOCKERS),
                "recorded": remaining_blockers,
            }
        )
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_WEAK_HELPER_POLARITY_CALLER_MODE_NON_CLAIMS.issubset(set(non_claims)):
        blockers.append(
            {
                "reason": "weak_helper_polarity_caller_mode_non_claims_missing",
                "label": f"{label}:$.non_claims",
                "expected": sorted(REQUIRED_WEAK_HELPER_POLARITY_CALLER_MODE_NON_CLAIMS),
                "recorded": non_claims,
            }
        )
    if mode == "promote":
        blockers.append({"reason": "promote_mode_weak_helper_polarity_caller_mode_candidate_only", "label": label})
    for trail, _, reason in collect_candidate_public_overclaims(
        payload,
        allowed_prefixes=(
            "$.remaining_blockers",
            "$.non_claims",
        ),
    ):
        blockers.append({"reason": f"weak_helper_polarity_caller_mode_public_overclaim_{reason}", "label": f"{label}:{trail}"})
    lower_strings = [value.casefold() for _, value in collect_string_fields(payload)]
    for forbidden in ("pending-kill", "pending kill", "destroyed", "unreachable"):
        if any(forbidden in value for value in lower_strings):
            blockers.append({"reason": "weak_helper_polarity_caller_mode_ue_lifecycle_name_overclaim", "label": label, "forbidden": forbidden})
    return blockers


def validate_provenance(
    *,
    artifact_path: Path,
    artifact_sha256: str,
    expected_binary_sha256: str | None,
    workspace_root: Path,
    protected_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    provenance_path = Path(f"{artifact_path}.provenance.json")
    blockers = path_blockers(
        provenance_path,
        label=f"{artifact_path}:provenance",
        workspace_root=workspace_root,
        protected_root=protected_root,
        require_workspace=True,
    )
    if blockers:
        return {"path": str(provenance_path), "verified": False}, blockers
    if not provenance_path.is_file():
        return {"path": str(provenance_path), "verified": False}, [
            {"reason": "missing_provenance_sidecar", "path": str(provenance_path)}
        ]

    payload, load_blockers = load_json(provenance_path)
    if payload is None:
        return {"path": str(provenance_path), "verified": False}, load_blockers

    blockers.extend(
        validate_json_path_fields(
            payload,
            source_label=str(provenance_path),
            workspace_root=workspace_root,
            protected_root=protected_root,
        )
    )
    if payload.get("schema") != PROVENANCE_SCHEMA:
        blockers.append(
            {
                "reason": "provenance_schema_mismatch",
                "path": str(provenance_path),
                "recorded_schema": payload.get("schema"),
            }
        )
    if payload.get("verified") is not True:
        blockers.append({"reason": "provenance_not_verified", "path": str(provenance_path)})
    if payload.get("artifact_sha256") != artifact_sha256:
        blockers.append(
            {
                "reason": "provenance_artifact_sha256_mismatch",
                "path": str(provenance_path),
                "expected_artifact_sha256": artifact_sha256,
                "recorded_artifact_sha256": payload.get("artifact_sha256"),
            }
        )
    if expected_binary_sha256 is not None and payload.get("binary_sha256") != expected_binary_sha256:
        blockers.append(
            {
                "reason": "provenance_binary_sha256_mismatch",
                "path": str(provenance_path),
                "expected_binary_sha256": expected_binary_sha256,
                "recorded_binary_sha256": payload.get("binary_sha256"),
            }
        )
    return {
        "path": str(provenance_path),
        "verified": not blockers,
        "schema": payload.get("schema"),
        "producer": payload.get("producer"),
        "tool": payload.get("tool"),
        "binary_sha256": payload.get("binary_sha256"),
        "artifact_sha256": payload.get("artifact_sha256"),
    }, blockers


def validate_artifact(
    label: str,
    path: Path,
    *,
    workspace_root: Path,
    protected_root: Path,
    expected_binary_sha256: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blockers = path_blockers(path, label=label, workspace_root=workspace_root, protected_root=protected_root, require_workspace=True)
    state = path_state(path, workspace_root=workspace_root, protected_root=protected_root)
    record: dict[str, Any] = {
        "label": label,
        "path": str(path),
        "resolved_path": state["resolved"],
        "sha256": None,
        "provenance_verified": False,
    }
    if blockers:
        return record, blockers
    resolved = Path(state["resolved"])
    if not resolved.is_file():
        return record, [{"reason": "artifact_not_file", "label": label, "path": str(path)}]
    artifact_sha256 = sha256_file(resolved)
    provenance, provenance_blockers = validate_provenance(
        artifact_path=resolved,
        artifact_sha256=artifact_sha256,
        expected_binary_sha256=expected_binary_sha256,
        workspace_root=workspace_root,
        protected_root=protected_root,
    )
    record.update({"sha256": artifact_sha256, "provenance": provenance, "provenance_verified": not provenance_blockers})
    return record, provenance_blockers


def validate_manifest(
    path: Path,
    *,
    workspace_root: Path,
    protected_root: Path,
    mode: str,
    strict_target_set_coverage: bool,
    expected_binary_sha256: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blockers = path_blockers(path, label="manifest", workspace_root=workspace_root, protected_root=protected_root, require_workspace=True)
    state = path_state(path, workspace_root=workspace_root, protected_root=protected_root)
    record: dict[str, Any] = {"path": str(path), "resolved_path": state["resolved"], "schema": None, "sha256": None}
    if blockers:
        return record, blockers
    resolved = Path(state["resolved"])
    if not resolved.is_file():
        return record, [{"reason": "manifest_not_file", "path": str(path)}]
    payload, load_blockers = load_json(resolved)
    if payload is None:
        return record, load_blockers
    record["schema"] = payload.get("schema")
    record["sha256"] = sha256_file(resolved)
    if payload.get("schema") not in SUPPORTED_MANIFEST_SCHEMAS:
        blockers.append(
            {
                "reason": "unsupported_manifest_schema",
                "label": f"{resolved}:$.schema",
                "recorded_schema": payload.get("schema"),
                "supported_schemas": sorted(SUPPORTED_MANIFEST_SCHEMAS),
            }
        )
    blockers.extend(
        validate_json_path_fields(
            payload,
            source_label=str(resolved),
            workspace_root=workspace_root,
            protected_root=protected_root,
        )
    )
    blockers.extend(
        validate_json_protected_root_strings(
            payload,
            source_label=str(resolved),
            workspace_root=workspace_root,
            protected_root=protected_root,
        )
    )
    blockers.extend(
        validate_redacted_signature_manifest(
            payload,
            source_label=str(resolved),
            workspace_root=workspace_root,
            protected_root=protected_root,
            mode=mode,
            strict_target_set_coverage=strict_target_set_coverage,
        )
    )
    blockers.extend(validate_redacted_scriptstruct_signature_manifest(payload, source_label=str(resolved), mode=mode))
    blockers.extend(
        validate_scriptstruct_inventory_pack_manifest(
            payload,
            label=str(resolved),
            manifest_path=resolved,
            workspace_root=workspace_root,
            protected_root=protected_root,
            mode=mode,
            expected_binary_sha256=expected_binary_sha256,
        )
    )
    blockers.extend(
        validate_rc_ufunction_second_source_root_manifest(
            payload,
            label=str(resolved),
            manifest_path=resolved,
            workspace_root=workspace_root,
            protected_root=protected_root,
            mode=mode,
        )
    )
    blockers.extend(
        validate_weak_helper_caller_mode_manifest(
            payload,
            source_label=str(resolved),
            workspace_root=workspace_root,
            protected_root=protected_root,
            mode=mode,
        )
    )
    blockers.extend(validate_readiness_report_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(validate_item_return_only_policy_slice_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(validate_transfer_baccept_only_policy_slice_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(validate_mission_copied_bool_policy_slice_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(validate_structure_return_only_policy_slice_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(validate_structure_nonpin_copied_scalar_policy_slice_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(validate_gobjects_two_core_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(validate_static_global_promotion_evidence_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(validate_resource_handle_revalidation_evaluator_manifest(payload, label=str(resolved), mode=mode))
    blockers.extend(
        validate_resource_handle_serial_scan_manifest(
            payload,
            label=str(resolved),
            mode=mode,
            expected_binary_sha256=expected_binary_sha256,
            workspace_root=workspace_root,
            protected_root=protected_root,
        )
    )
    blockers.extend(
        validate_uobject_flag_policy_report_manifest(
            payload,
            label=str(resolved),
            mode=mode,
            expected_binary_sha256=expected_binary_sha256,
        )
    )
    blockers.extend(
        validate_uobject_flag_transition_matrix_manifest(
            payload,
            label=str(resolved),
            mode=mode,
            expected_binary_sha256=expected_binary_sha256,
        )
    )
    blockers.extend(
        validate_uobject_flag_sample_report_manifest(
            payload,
            label=str(resolved),
            mode=mode,
            expected_binary_sha256=expected_binary_sha256,
        )
    )
    blockers.extend(
        validate_uobject_flag_semantic_correlation_manifest(
            payload,
            label=str(resolved),
            mode=mode,
            expected_binary_sha256=expected_binary_sha256,
        )
    )
    blockers.extend(
        validate_weak_helper_static_polarity_report_manifest(
            payload,
            label=str(resolved),
            mode=mode,
            expected_binary_sha256=expected_binary_sha256,
        )
    )
    blockers.extend(
        validate_weak_helper_polarity_caller_mode_report_manifest(
            payload,
            label=str(resolved),
            mode=mode,
            expected_binary_sha256=expected_binary_sha256,
        )
    )
    blockers.extend(validate_claims(payload, label=str(resolved), mode=mode))
    return record, blockers


def validate_expected_sha(value: str | None) -> str | None:
    if value is None:
        return None
    if SHA256_RE.fullmatch(value) is None:
        raise SystemExit("--expected-binary-sha256 must be a lowercase 64-character SHA256")
    return value


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    workspace_root = args.root.expanduser()
    protected_root = args.protected_root.expanduser()
    expected_binary_sha256 = validate_expected_sha(args.expected_binary_sha256)
    all_blockers: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []

    for path in args.manifest:
        record, blockers = validate_manifest(
            path,
            workspace_root=workspace_root,
            protected_root=protected_root,
            mode=args.mode,
            strict_target_set_coverage=getattr(args, "strict_target_set_coverage", False),
            expected_binary_sha256=expected_binary_sha256,
        )
        manifests.append(record)
        all_blockers.extend(blockers)

    for label, path in args.artifact:
        record, blockers = validate_artifact(
            label,
            path,
            workspace_root=workspace_root,
            protected_root=protected_root,
            expected_binary_sha256=expected_binary_sha256,
        )
        artifacts.append(record)
        all_blockers.extend(blockers)

    if args.mode == "promote" and not args.manifest and not args.artifact:
        all_blockers.append({"reason": "promote_mode_requires_input"})

    return {
        "schema": SCHEMA,
        "root": str(workspace_root),
        "protected_root": str(protected_root),
        "mode": args.mode,
        "binary_sha256": expected_binary_sha256,
        "status": "blocked" if all_blockers else "accepted",
        "manifests": manifests,
        "artifacts": artifacts,
        "blockers": all_blockers,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate offline artifact path/provenance gates.")
    parser.add_argument("--root", type=Path, default=DEFAULT_WORKSPACE_ROOT, help="Approved offline workspace root.")
    parser.add_argument("--protected-root", type=Path, default=SERVER_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--manifest", type=Path, action="append", default=[], help="Manifest or evidence JSON to validate.")
    parser.add_argument("--artifact", type=parse_label_path, action="append", default=[], metavar="LABEL=PATH")
    parser.add_argument("--expected-binary-sha256")
    parser.add_argument("--mode", choices=("intake", "consume", "promote"), default="consume")
    parser.add_argument(
        "--strict-target-set-coverage",
        action="store_true",
        help="Require redacted UFunction manifests to carry complete target-set coverage metadata.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']} mode={result['mode']} blockers={len(result['blockers'])}")
        for blocker in result["blockers"]:
            print(f"- {blocker['reason']}: {blocker.get('label') or blocker.get('path') or ''}")
    if result["status"] == "accepted":
        return 0
    if any("promotion" in blocker.get("reason", "") or "promote" in blocker.get("reason", "") for blocker in result["blockers"]):
        return 3
    if any("json" in blocker.get("reason", "") or "schema" in blocker.get("reason", "") for blocker in result["blockers"]):
        return 4
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
