#!/usr/bin/env python3
"""Tests for validate_offline_artifact_gate.py."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_offline_artifact_gate as gate
import normalize_artifact_pack as artifact_pack
import build_resource_handle_serial_policy as serial_policy_builder


BINARY_SHA = "a" * 64
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"


def weak_helper_address_sha(address: str) -> str:
    return hashlib.sha256(
        f"obelisk.weak-helper-caller-mode:{gate.WEAK_HELPER_BINARY_SHA256}:{address}".encode("ascii")
    ).hexdigest()


def weak_helper_caller_mode_manifest() -> dict:
    return {
        "schema": gate.WEAK_HELPER_CALLER_MODE_SCHEMA,
        "status": "accepted_internal_static_evidence",
        "binary": {
            "sha256": gate.WEAK_HELPER_BINARY_SHA256,
            "path_redacted": True,
        },
        "direct_call_coverage": {
            "0x1d56b60": {"expected": 4, "observed": 4},
            "0x1d56c70": {"expected": 6, "observed": 6},
        },
        "builder_contract": {
            "promotion_gate_ready": False,
            "consumption_scope": "internal_static_research_only",
            "remaining_blockers": ["static_only_evidence"],
            "not_promoted": ["ResourceHandle"],
        },
        "sources": {
            "direct_call_counts": {
                "artifact_sha256": "b" * 64,
                "tool": "objdump-or-radare2",
                "version": "5.5.0",
                "provenance": {
                    "schema": "obelisk.offline-artifact-provenance.v1",
                    "verified": True,
                    "path_redacted": True,
                    "binary_sha256": gate.WEAK_HELPER_BINARY_SHA256,
                    "artifact_sha256": "b" * 64,
                    "sidecar_sha256": "e" * 64,
                },
            },
            "ghidra_stdout": {
                "artifact_sha256": "c" * 64,
                "tool": "ghidra",
                "version": "12.1",
                "provenance": {
                    "schema": "obelisk.offline-artifact-provenance.v1",
                    "verified": True,
                    "path_redacted": True,
                    "binary_sha256": gate.WEAK_HELPER_BINARY_SHA256,
                    "artifact_sha256": "c" * 64,
                    "sidecar_sha256": "f" * 64,
                },
            },
            "r2_windows": {
                "artifact_sha256": "d" * 64,
                "tool": "radare2",
                "version": "5.5.0",
                "provenance": {
                    "schema": "obelisk.offline-artifact-provenance.v1",
                    "verified": True,
                    "path_redacted": True,
                    "binary_sha256": gate.WEAK_HELPER_BINARY_SHA256,
                    "artifact_sha256": "d" * 64,
                    "sidecar_sha256": "a" * 64,
                },
            },
        },
        "required_evidence": [
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
        ],
        "helpers": {
            "0x1d56b60": {
                "return_kind": "boolean_like",
                "mode_args": ["sil", "dl"],
            },
            "0x1d56c70": {
                "return_kind": "uobject_pointer_or_null",
                "mode_args": ["sil"],
            },
        },
        "callers": [
            {
                "helper": "0x1d56c70",
                "caller_window_count": 6,
                "mode_args": {"sil": {"source": "const", "value": 1}},
                "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
            },
            {
                "helper": "0x1d56b60",
                "caller_window_count": 2,
                "mode_args": {"sil": {"source": "const", "value": 0}, "dl": {"source": "const", "value": 1}},
                "return_use": {"kind": "pairwise_boolean_comparison"},
            },
        ],
        "caller_rows": [
            {
                "helper": "0x1d56c70",
                "helper_address_sha256": weak_helper_address_sha("0x1d56c70"),
                "caller_address_sha256": weak_helper_address_sha(caller),
                "mode_args": {"sil": {"source": "const", "value": 1}},
                "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
                "source_count": 2,
                "evidence": ["ghidra", "radare2"],
                "policy_observation": {
                    "0x100": "null_always",
                    "0x4000": "not_rejected_in_observed_sil_1_callers",
                },
                "claim_level": "static_caller_mode_candidate",
                "path_redacted": True,
                "lifecycle_names": "not_promoted",
            }
            for caller in (
                "0x83a340",
                "0x83a720",
                "0x83cde0",
                "0x9f80f0",
                "0x1d299b0",
                "0x1d29a20",
            )
        ],
    }


def redacted_signature_manifest(
    *,
    target: str = "PrimalItem.AllowEquipItem",
    signature_count: int = 1,
    safety_overrides: dict | None = None,
    target_sets: list[str] | None = None,
    artifact_hygiene: dict | None = None,
) -> dict:
    target_sets = target_sets or []
    safety = {
        "artifact_status": "candidate_only",
        "intended_use": "offline_review_only",
        "evidence_scope": "redacted_ufunction_signature_metadata",
        "promotion_ready": False,
        "signature_count": 1,
        "zero_param_signature_count": 0,
        "snapshot_count": 1,
        "target_set_count": len(target_sets),
        "missing_target_count": 0,
        "param_count_total": 2,
        "copied_scalar_count_total": 1,
        "copied_scalar_by_kind": {"bool": 1},
        "redacted_count_total": 1,
        "redacted_by_reason": {"object_ref": 1},
        "blocked_count_total": 0,
        "blocked_by_reason": {},
        "promotion_blocker_count_total": 2,
        "promotion_blockers_by_reason": {
            "function_flags_not_bound_to_exact_target_gate": 1,
            "property_flags_unknown_bits": 1,
        },
        "direction_counts": {"in": 1, "return": 1},
        "bool_masked_field_count": 0,
        "unknown_or_blocked_present": False,
        "not_promoted_surfaces": sorted(gate.REQUIRED_REDACTED_SIGNATURE_NON_PROMOTED_SURFACES),
    }
    if safety_overrides:
        safety.update(safety_overrides)
    payload = {
        "schema": gate.REDACTED_UFUNCTION_SIGNATURE_SCHEMA,
        "snapshot_root": "redacted",
        "signature_count": signature_count,
        "snapshot_count": 1,
        "target_sets": target_sets,
        "generated_from": {
            "snapshot_schema": SNAPSHOT_SCHEMA,
            "input_snapshots": [{"id": "snapshot-0001", "sha256": "d" * 64}],
        },
        "missing_targets": [],
        "non_claims": sorted(gate.REQUIRED_REDACTED_SIGNATURE_NON_CLAIMS),
        "safety_summary": safety,
        "signatures": [
            {
                "target": target,
                "source_snapshot": "snapshot-0001",
                "source_snapshot_sha256": "d" * 64,
                "signature_status": "candidate-only",
                "runtime_ready": False,
                "params": [
                    {
                        "name": "toInventory",
                        "direction": "in",
                        "type": "redacted_uobject_ref",
                    },
                    {
                        "name": "ReturnValue",
                        "direction": "return",
                        "type": "bool",
                        "promotion_blockers": ["property_flags_unknown_bits"],
                    },
                ],
                "blocked_properties": [],
                "promotion_blockers": ["function_flags_not_bound_to_exact_target_gate"],
            }
        ],
    }
    if artifact_hygiene is not None:
        payload["artifact_hygiene"] = artifact_hygiene
    return payload


def historical_missing_coverage_marker() -> dict:
    return {
        "schema": gate.REDACTED_UFUNCTION_ARTIFACT_HYGIENE_SCHEMA,
        "classification": "historical",
        "promotion_hygienic": False,
        "consume_mode_allowed": True,
        "reason": "missing_target_set_coverage_pre_strict_gate",
    }


def readiness_report_manifest(
    *,
    ready: bool = True,
    include_boundaries: bool = True,
    gate_mode: str = "second_source_promotion",
    target_sets: list[str] | None = None,
) -> dict:
    if target_sets is None:
        target_sets = ["minimal-second-source-intake"]
    payload = {
        "schema": gate.READINESS_REPORT_SCHEMA,
        "gate_mode": gate_mode,
        "promotion_gate": {
            "ready": ready,
            "ready_scope": "layout_only" if ready else "not_ready",
            "layout_ready": ready,
            "promotion_ready": False,
            "blockers": [],
        },
        "totals": {"targets": 1},
        "target_sets": target_sets,
    }
    if include_boundaries:
        payload.update(
            {
                "evidence_scope": "second_source_layout_evidence_only",
                "not_promoted_surfaces": sorted(gate.REQUIRED_READINESS_NON_PROMOTED_SURFACES),
                "non_claims": ["accepted second-source readiness is layout evidence only"],
            }
        )
    return payload


def item_return_only_policy_slice_manifest(
    *,
    policy_status: str = "evidence-only",
    promotion_ready: bool = False,
    copied_bool_count: int = 3,
    excluded_field_count: int = 5,
    missing_targets: list[str] | None = None,
    non_claims: list[str] | None = None,
) -> dict:
    copied_fields = sorted(gate.REQUIRED_ITEM_RETURN_ONLY_COPIED_FIELDS)
    excluded_fields = sorted(gate.REQUIRED_ITEM_RETURN_ONLY_EXCLUDED_FIELDS)
    if missing_targets is None:
        missing_targets = []
    if non_claims is None:
        non_claims = sorted(gate.REQUIRED_ITEM_RETURN_ONLY_NON_CLAIMS) + [
            "does not copy CraftBlueprint, bIgnoreInventoryRequirement, bConsumeResources, toInventory, DestinationItem, or AdditionalData"
        ]
    return {
        "schema": gate.ITEM_RETURN_ONLY_POLICY_SLICE_SCHEMA,
        "snapshot_root": "redacted",
        "input_target_set": "item-compact-intake",
        "output_target_set": "item-return-only-policy-slice",
        "policy_status": policy_status,
        "missing_targets": missing_targets,
        "generated_from": {
            "snapshot_schema": SNAPSHOT_SCHEMA,
            "input_snapshots": [{"id": f"snapshot-{index:04d}", "sha256": f"{index}" * 64} for index in range(1, 5)],
        },
        "coverage": {
            "status": "complete",
            "copied_fields": copied_fields,
            "copied_targets": [
                "PrimalItem.AllowEquipItem",
                "PrimalItem.CanRepair",
                "PrimalItem.UseItemOntoItem",
            ],
            "excluded_fields": excluded_fields,
            "input_targets": [
                "PrimalItem.AllowEquipItem",
                "PrimalItem.CanRepair",
                "PrimalItem.CraftBlueprint",
                "PrimalItem.UseItemOntoItem",
            ],
        },
        "copied_return_bools": [
            {
                "target": field.rsplit(".", 1)[0],
                "field": "ReturnValue",
                "copied_field": field,
                "direction": "return",
                "type": "bool",
                "element_size": 1,
                "evidence_status": "copied-return-bool-only",
                "source_snapshot": f"snapshot-{index:04d}",
                "source_snapshot_sha256": f"{index}" * 64,
            }
            for index, field in enumerate(copied_fields, start=1)
        ],
        "excluded_fields": [
            {
                "target": field.rsplit(".", 1)[0],
                "field": field.rsplit(".", 1)[1],
                "excluded_field": field,
                "reason": "unit_test_excluded",
                "source_snapshot": f"snapshot-{index:04d}",
            }
            for index, field in enumerate(excluded_fields, start=1)
        ],
        "non_claims": non_claims,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": promotion_ready,
            "copied_bool_count": copied_bool_count,
            "excluded_field_count": excluded_field_count,
            "explicitly_excluded": [
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
            ],
        },
    }


def transfer_baccept_only_policy_slice_manifest(
    *,
    policy_status: str = "evidence-only",
    promotion_ready: bool = False,
    copied_bool_count: int = 1,
    forbidden_field_count: int | None = None,
    missing_targets: list[str] | None = None,
    non_claims: list[str] | None = None,
) -> dict:
    copied_field = gate.REQUIRED_TRANSFER_BACCEPT_ONLY_COPIED_FIELD
    forbidden_fields = sorted(gate.REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS)
    if forbidden_field_count is None:
        forbidden_field_count = len(forbidden_fields)
    if missing_targets is None:
        missing_targets = []
    if non_claims is None:
        non_claims = sorted(gate.REQUIRED_TRANSFER_BACCEPT_ONLY_NON_CLAIMS) + [
            "does not copy spawn point ids, region indexes, player data ids, bed ids, return bools, object refs, class refs, tribute structs, arrays, strings, or ids"
        ]
    input_snapshots = [
        {"id": f"snapshot-{index:04d}", "sha256": f"{index}" * 64, "target": target}
        for index, target in enumerate(sorted(gate.REQUIRED_TRANSFER_BACCEPT_ONLY_INPUT_TARGETS), start=1)
    ]
    source_by_target = {
        snapshot["target"]: snapshot
        for snapshot in input_snapshots
    }
    forbidden_shapes = {
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
    }
    copied_source = source_by_target[gate.REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET]
    return {
        "schema": gate.TRANSFER_BACCEPT_ONLY_POLICY_SLICE_SCHEMA,
        "snapshot_root": "redacted",
        "input_target_set": "transfer-ufunction-intake",
        "output_target_set": "transfer-baccept-only-policy-slice",
        "policy_status": policy_status,
        "missing_targets": missing_targets,
        "generated_from": {
            "snapshot_schema": SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "coverage": {
            "status": "complete",
            "copied_fields": [copied_field],
            "copied_targets": [gate.REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET],
            "forbidden_fields": forbidden_fields,
            "input_targets": sorted(gate.REQUIRED_TRANSFER_BACCEPT_ONLY_INPUT_TARGETS),
        },
        "copied_bool": {
            "target": gate.REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET,
            "field": "bAccept",
            "copied_field": copied_field,
            "direction": "in",
            "type": "bool",
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
            "evidence_status": "copied-bool-only",
            "source_snapshot": copied_source["id"],
            "source_snapshot_sha256": copied_source["sha256"],
        },
        "forbidden_transfer_fields": [
            {
                "target": field.rsplit(".", 1)[0],
                "field": field.rsplit(".", 1)[1],
                "forbidden_field": field,
                "reason": "not_in_baccept_only_slice",
                **forbidden_shapes[field],
                "source_snapshot": source_by_target[field.rsplit(".", 1)[0]]["id"],
                "source_snapshot_sha256": source_by_target[field.rsplit(".", 1)[0]]["sha256"],
            }
            for field in forbidden_fields
        ],
        "non_claims": non_claims,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": promotion_ready,
            "copied_bool_count": copied_bool_count,
            "forbidden_field_count": forbidden_field_count,
            "explicitly_excluded": sorted(gate.REQUIRED_TRANSFER_BACCEPT_ONLY_EXPLICIT_EXCLUSIONS),
        },
    }


def mission_copied_bool_policy_slice_manifest(
    *,
    policy_status: str = "evidence-only",
    promotion_ready: bool = False,
    copied_bool_count: int = 5,
    redacted_field_count: int = 6,
    missing_targets: list[str] | None = None,
    non_claims: list[str] | None = None,
) -> dict:
    copied_fields = sorted(gate.REQUIRED_MISSION_COPIED_BOOL_FIELDS)
    redacted_fields = sorted(gate.REQUIRED_MISSION_COPIED_BOOL_REDACTED_FIELDS)
    if missing_targets is None:
        missing_targets = []
    if non_claims is None:
        non_claims = sorted(gate.REQUIRED_MISSION_COPIED_BOOL_NON_CLAIMS)
    input_snapshots = [
        {"id": f"snapshot-{index:04d}", "sha256": f"{index}" * 64, "target": target}
        for index, target in enumerate(sorted(gate.REQUIRED_MISSION_COPIED_BOOL_INPUT_TARGETS), start=1)
    ]
    source_by_target = {snapshot["target"]: snapshot for snapshot in input_snapshots}
    copied_shapes = {
        "MissionType.AddPlayerToMission.bForceAdd": {"field": "bForceAdd", "direction": "in", "offset": "0x8", "offset_internal": 8, "property_flags": "0x1040000280", "return_value_offset": "0x9"},
        "MissionType.AddPlayerToMission.ReturnValue": {"field": "ReturnValue", "direction": "return", "offset": "0x9", "offset_internal": 9, "property_flags": "0x1040000780", "return_value_offset": "0x9"},
        "MissionType.BPAllowPlayerToLeaveMission.ReturnValue": {"field": "ReturnValue", "direction": "return", "offset": "0x8", "offset_internal": 8, "property_flags": "0x1040000780", "return_value_offset": "0x8"},
        "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent": {"field": "bFromMissionCompleteEvent", "direction": "in", "offset": "0x10", "offset_internal": 16, "property_flags": "0x1040000280", "return_value_offset": "0xffff"},
        "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess": {"field": "bLastPhaseSuccess", "direction": "in", "offset": "0x11", "offset_internal": 17, "property_flags": "0x1040000280", "return_value_offset": "0xffff"},
    }
    redacted_shapes = {
        "MissionType.AddPlayerToMission.PlayerCharacter": {"field": "PlayerCharacter", "property_class": "ObjectProperty", "offset": "0x0", "offset_internal": 0, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn": {"field": "PlayerPawn", "property_class": "ObjectProperty", "offset": "0x0", "offset_internal": 0, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.BPOnPlayerRemovedFromMission.Controller": {"field": "Controller", "property_class": "ObjectProperty", "offset": "0x8", "offset_internal": 8, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.BPOnPlayerRemovedFromMission.Player": {"field": "Player", "property_class": "ObjectProperty", "offset": "0x0", "offset_internal": 0, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.GetPlayerUsableItems.Character": {"field": "Character", "property_class": "ObjectProperty", "offset": "0x0", "offset_internal": 0, "element_size": 8, "array_dim": 1, "property_flags": "0x1040000280"},
        "MissionType.GetPlayerUsableItems.OutItemIDs": {"field": "OutItemIDs", "property_class": "ArrayProperty", "offset": "0x8", "offset_internal": 8, "element_size": 16, "array_dim": 1, "property_flags": "0x380"},
    }
    return {
        "schema": gate.MISSION_COPIED_BOOL_POLICY_SLICE_SCHEMA,
        "snapshot_root": "redacted",
        "input_target_set": "mission-compact-intake",
        "output_target_set": "mission-copied-bool-policy-slice",
        "policy_status": policy_status,
        "missing_targets": missing_targets,
        "generated_from": {
            "snapshot_schema": SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "coverage": {
            "status": "complete",
            "copied_fields": copied_fields,
            "copied_targets": sorted(gate.REQUIRED_MISSION_COPIED_BOOL_COPIED_TARGETS),
            "redacted_fields": redacted_fields,
            "input_targets": sorted(gate.REQUIRED_MISSION_COPIED_BOOL_INPUT_TARGETS),
        },
        "copied_bools": [
            {
                "target": field.rsplit(".", 1)[0],
                "copied_field": field,
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
                "source_snapshot": source_by_target[field.rsplit(".", 1)[0]]["id"],
                "source_snapshot_sha256": source_by_target[field.rsplit(".", 1)[0]]["sha256"],
                **copied_shapes[field],
            }
            for field in copied_fields
        ],
        "redacted_mission_fields": [
            {
                "target": field.rsplit(".", 1)[0],
                "redacted_field": field,
                "reason": "unit_test_redacted",
                "evidence_status": "recognition-only-redacted",
                "source_snapshot": source_by_target[field.rsplit(".", 1)[0]]["id"],
                "source_snapshot_sha256": source_by_target[field.rsplit(".", 1)[0]]["sha256"],
                **redacted_shapes[field],
            }
            for field in redacted_fields
        ],
        "non_claims": non_claims,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": promotion_ready,
            "copied_bool_count": copied_bool_count,
            "redacted_field_count": redacted_field_count,
            "explicitly_excluded": sorted(gate.REQUIRED_MISSION_COPIED_BOOL_EXPLICIT_EXCLUSIONS),
        },
    }


def structure_return_only_policy_slice_manifest(
    *,
    policy_status: str = "evidence-only",
    promotion_ready: bool = False,
    copied_bool_count: int = 2,
    redacted_field_count: int = 2,
    deferred_target_count: int = 4,
    missing_targets: list[str] | None = None,
    non_claims: list[str] | None = None,
) -> dict:
    copied_fields = sorted(gate.REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_FIELDS)
    redacted_fields = sorted(gate.REQUIRED_STRUCTURE_RETURN_ONLY_REDACTED_FIELDS)
    deferred_targets = sorted(gate.REQUIRED_STRUCTURE_RETURN_ONLY_DEFERRED_TARGETS)
    if missing_targets is None:
        missing_targets = []
    if non_claims is None:
        non_claims = sorted(gate.REQUIRED_STRUCTURE_RETURN_ONLY_NON_CLAIMS)
    input_snapshots = [
        {"id": f"snapshot-{index:04d}", "sha256": f"{index}" * 64, "target": target}
        for index, target in enumerate(sorted(gate.REQUIRED_STRUCTURE_RETURN_ONLY_INPUT_TARGETS), start=1)
    ]
    source_by_target = {snapshot["target"]: snapshot for snapshot in input_snapshots}
    copied_shapes = {
        "PrimalStructure.AllowStructureAccess.ReturnValue": {"field": "ReturnValue", "function_flags": "0x4020400"},
        "PrimalStructure.IsAllowedToDemolish.ReturnValue": {"field": "ReturnValue", "function_flags": "0x4020401"},
    }
    redacted_shapes = {
        "PrimalStructure.AllowStructureAccess.ForPC": {"field": "ForPC", "function_flags": "0x4020400"},
        "PrimalStructure.IsAllowedToDemolish.ForPC": {"field": "ForPC", "function_flags": "0x4020401"},
    }
    deferred_shapes = {
        "PrimalStructure.SetVariant": {"function_flags": "0x4020401", "num_parms": 3, "parms_size": 6, "return_value_offset": "0x5", "property_count": 3},
        "PrimalStructureItemContainer.AllowToggleActivation": {"function_flags": "0x4020401", "num_parms": 2, "parms_size": 9, "return_value_offset": "0x8", "property_count": 2},
        "PrimalStructureItemContainer.VerifyPinCode": {"function_flags": "0x54020401", "num_parms": 2, "parms_size": 5, "return_value_offset": "0x4", "property_count": 2},
        "PrimalStructureSeating.CanSeat": {"function_flags": "0x4020400", "num_parms": 4, "parms_size": 18, "return_value_offset": "0x11", "property_count": 4},
    }
    return {
        "schema": gate.STRUCTURE_RETURN_ONLY_POLICY_SLICE_SCHEMA,
        "snapshot_root": "redacted",
        "input_target_set": "structure-observer-intake",
        "output_target_set": "structure-return-only-policy-slice",
        "policy_status": policy_status,
        "missing_targets": missing_targets,
        "generated_from": {
            "snapshot_schema": SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
        },
        "coverage": {
            "status": "complete",
            "copied_fields": copied_fields,
            "copied_targets": sorted(gate.REQUIRED_STRUCTURE_RETURN_ONLY_COPIED_TARGETS),
            "redacted_fields": redacted_fields,
            "deferred_targets": deferred_targets,
            "input_targets": sorted(gate.REQUIRED_STRUCTURE_RETURN_ONLY_INPUT_TARGETS),
        },
        "copied_return_bools": [
            {
                "target": field.rsplit(".", 1)[0],
                "copied_field": field,
                "direction": "return",
                "type": "bool",
                "property_class": "BoolProperty",
                "bool_field_size": 1,
                "bool_byte_offset": 0,
                "offset": "0x8",
                "offset_internal": 8,
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
                "source_snapshot": source_by_target[field.rsplit(".", 1)[0]]["id"],
                "source_snapshot_sha256": source_by_target[field.rsplit(".", 1)[0]]["sha256"],
                **copied_shapes[field],
            }
            for field in copied_fields
        ],
        "redacted_structure_fields": [
            {
                "target": field.rsplit(".", 1)[0],
                "redacted_field": field,
                "reason": "unit_test_redacted",
                "property_class": "ObjectProperty",
                "offset": "0x0",
                "offset_internal": 0,
                "element_size": 8,
                "array_dim": 1,
                "num_parms": 2,
                "parms_size": 9,
                "return_value_offset": "0x8",
                "property_flags": "0x1040000280",
                "evidence_status": "recognition-only-redacted",
                "source_snapshot": source_by_target[field.rsplit(".", 1)[0]]["id"],
                "source_snapshot_sha256": source_by_target[field.rsplit(".", 1)[0]]["sha256"],
                **redacted_shapes[field],
            }
            for field in redacted_fields
        ],
        "deferred_structure_targets": [
            {
                "target": target,
                "deferred_target": target,
                "reason": "unit_test_deferred",
                "evidence_status": "explicitly-deferred-target",
                "source_snapshot": source_by_target[target]["id"],
                "source_snapshot_sha256": source_by_target[target]["sha256"],
                **deferred_shapes[target],
            }
            for target in deferred_targets
        ],
        "non_claims": non_claims,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": promotion_ready,
            "copied_bool_count": copied_bool_count,
            "redacted_field_count": redacted_field_count,
            "deferred_target_count": deferred_target_count,
            "explicitly_excluded": sorted(gate.REQUIRED_STRUCTURE_RETURN_ONLY_EXPLICIT_EXCLUSIONS),
        },
    }


def structure_nonpin_copied_scalar_policy_slice_manifest(
    *,
    policy_status: str = "evidence-only",
    promotion_ready: bool = False,
    copied_scalar_count: int = 6,
    redacted_field_count: int = 3,
    missing_targets: list[str] | None = None,
    non_claims: list[str] | None = None,
) -> dict:
    copied_fields = [
        "PrimalStructure.SetVariant.VariantIndex",
        "PrimalStructure.SetVariant.bForceSet",
        "PrimalStructure.SetVariant.ReturnValue",
        "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue",
        "PrimalStructureSeating.CanSeat.bForce",
        "PrimalStructureSeating.CanSeat.ReturnValue",
    ]
    redacted_fields = [
        "PrimalStructureItemContainer.AllowToggleActivation.ForPC",
        "PrimalStructureSeating.CanSeat.ForPC",
        "PrimalStructureSeating.CanSeat.forCharacter",
    ]
    if missing_targets is None:
        missing_targets = []
    if non_claims is None:
        non_claims = sorted(gate.REQUIRED_STRUCTURE_NONPIN_NON_CLAIMS)
    input_snapshots = [
        {"id": f"snapshot-{index:04d}", "sha256": f"{index}" * 64, "target": target}
        for index, target in enumerate(sorted(gate.REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS), start=1)
    ]
    source_by_target = {snapshot["target"]: snapshot for snapshot in input_snapshots}
    copied_shapes = {
        "PrimalStructure.SetVariant.VariantIndex": {"field": "VariantIndex", "direction": "in", "type": "int32", "property_class": "IntProperty", "offset": "0x0", "offset_internal": 0, "element_size": 4},
        "PrimalStructure.SetVariant.bForceSet": {"field": "bForceSet", "direction": "in", "type": "bool", "property_class": "BoolProperty", "offset": "0x4", "offset_internal": 4, "element_size": 1},
        "PrimalStructure.SetVariant.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "property_class": "BoolProperty", "offset": "0x5", "offset_internal": 5, "element_size": 1},
        "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "property_class": "BoolProperty", "offset": "0x8", "offset_internal": 8, "element_size": 1},
        "PrimalStructureSeating.CanSeat.bForce": {"field": "bForce", "direction": "in", "type": "bool", "property_class": "BoolProperty", "offset": "0x10", "offset_internal": 16, "element_size": 1},
        "PrimalStructureSeating.CanSeat.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "property_class": "BoolProperty", "offset": "0x11", "offset_internal": 17, "element_size": 1},
    }
    target_shapes = {
        "PrimalStructure.SetVariant": {"function_flags": "0x4020401", "num_parms": 3, "parms_size": 6, "return_value_offset": "0x5"},
        "PrimalStructureItemContainer.AllowToggleActivation": {"function_flags": "0x4020401", "num_parms": 2, "parms_size": 9, "return_value_offset": "0x8"},
        "PrimalStructureSeating.CanSeat": {"function_flags": "0x4020400", "num_parms": 4, "parms_size": 18, "return_value_offset": "0x11"},
    }
    redacted_shapes = {
        "PrimalStructureItemContainer.AllowToggleActivation.ForPC": {"field": "ForPC", "offset": "0x0", "offset_internal": 0},
        "PrimalStructureSeating.CanSeat.ForPC": {"field": "ForPC", "offset": "0x0", "offset_internal": 0},
        "PrimalStructureSeating.CanSeat.forCharacter": {"field": "forCharacter", "offset": "0x8", "offset_internal": 8},
    }
    return {
        "schema": gate.STRUCTURE_NONPIN_COPIED_SCALAR_POLICY_SLICE_SCHEMA,
        "snapshot_root": "redacted",
        "input_target_set": "structure-nonpin-copied-scalar-policy-slice",
        "output_target_set": "structure-nonpin-copied-scalar-policy-slice",
        "policy_status": policy_status,
        "missing_targets": missing_targets,
        "generated_from": {"snapshot_schema": SNAPSHOT_SCHEMA, "input_snapshots": input_snapshots},
        "coverage": {
            "status": "complete",
            "copied_fields": copied_fields,
            "copied_targets": sorted(gate.REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS),
            "redacted_fields": redacted_fields,
            "input_targets": sorted(gate.REQUIRED_STRUCTURE_NONPIN_INPUT_TARGETS),
        },
        "copied_scalars": [
            {
                "target": field.rsplit(".", 1)[0],
                "copied_field": field,
                "array_dim": 1,
                "property_flags": "0x1040000780" if field.endswith("ReturnValue") else "0x1040000280",
                "evidence_status": "copied-structure-nonpin-scalar-only",
                "source_snapshot": source_by_target[field.rsplit(".", 1)[0]]["id"],
                "source_snapshot_sha256": source_by_target[field.rsplit(".", 1)[0]]["sha256"],
                **target_shapes[field.rsplit(".", 1)[0]],
                **copied_shapes[field],
                **(
                    {
                        "bool_field_size": 1,
                        "bool_byte_offset": 0,
                        "byte_mask": "0x01",
                        "field_mask": "0xff",
                        "native_bool": False,
                    }
                    if copied_shapes[field]["type"] == "bool"
                    else {}
                ),
            }
            for field in copied_fields
        ],
        "redacted_structure_fields": [
            {
                "target": field.rsplit(".", 1)[0],
                "redacted_field": field,
                "reason": "unit_test_redacted",
                "property_class": "ObjectProperty",
                "element_size": 8,
                "array_dim": 1,
                "property_flags": "0x1040000280",
                "evidence_status": "recognition-only-redacted",
                "source_snapshot": source_by_target[field.rsplit(".", 1)[0]]["id"],
                "source_snapshot_sha256": source_by_target[field.rsplit(".", 1)[0]]["sha256"],
                **target_shapes[field.rsplit(".", 1)[0]],
                **redacted_shapes[field],
            }
            for field in redacted_fields
        ],
        "non_claims": non_claims,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": promotion_ready,
            "copied_scalar_count": copied_scalar_count,
            "redacted_field_count": redacted_field_count,
            "explicitly_excluded": sorted(gate.REQUIRED_STRUCTURE_NONPIN_EXPLICIT_EXCLUSIONS),
        },
    }


def rc_ufunction_second_source_root_manifest(root: Path) -> dict:
    expected_sources = gate.expected_rc_ufunction_target_sources()
    assert expected_sources is not None
    snapshots = []
    for index, target in enumerate(sorted(expected_sources)):
        relative_path = f"snapshots/{index:02d}.snapshot.json"
        snapshot_path = root / relative_path
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps({"schema": SNAPSHOT_SCHEMA, "target": target}) + "\n", encoding="utf-8")
        snapshots.append(
            {
                "target": target,
                "relative_path": relative_path,
                "snapshot_sha256": gate.sha256_file(snapshot_path),
                "source_target_sets": sorted(expected_sources[target]),
                "evidence": {
                    "ark_binary_sha256": BINARY_SHA,
                    "artifact_sha256": "d" * 64,
                    "status": "accepted",
                },
            }
        )
    return {
        "schema": gate.RC_UFUNCTION_SECOND_SOURCE_ROOT_SCHEMA,
        "snapshot_schema": gate.RC_UFUNCTION_SNAPSHOT_SCHEMA,
        "target_sets": list(gate.RC_UFUNCTION_TARGET_SETS),
        "target_count": len(snapshots),
        "snapshots": snapshots,
        "path_redacted": True,
        "non_claims": sorted(gate.REQUIRED_RC_UFUNCTION_NON_CLAIMS),
    }


def static_global_promotion_evidence_manifest(*, ready: bool = False) -> dict:
    payload = {
        "schema": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
        "binary": {
            "sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
        },
        "static_xrefs_sha256": "8" * 64,
        "commands": {
            "objdump": {
                "stdout_sha256": "9" * 64,
                "returncode": 0,
                "provenance": {
                    "verified": True,
                    "reason": "generated_from_binary",
                    "binary_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    "artifact_sha256": "9" * 64,
                    "tool": "objdump",
                },
            },
        },
        "artifacts": {
            "static_xrefs": "static-global-xrefs.json",
        },
        "candidates": [
            {
                "label": "gobjects",
                "kind": "gobjects",
                "address": "0x595b7e0",
                "static_contract": {
                    "satisfied": False,
                    "blockers": ["missing_gobjects_coherent_field_window"],
                    "coherent_window": None,
                    "redacted_field_window_evidence": None,
                },
            },
            {
                "label": "fname_root",
                "kind": "fname_root",
                "address": "0x5956f30",
                "static_contract": {
                    "satisfied": True,
                    "blockers": [],
                },
            },
        ],
        "promotion_gate": {
            "ready": ready,
            "blockers": [] if ready else ["static_only_evidence"],
        },
        "remaining_blockers": [] if ready else ["static_only_evidence"],
        "non_claims": ["static_only_evidence"],
    }
    payload["artifact_identity"] = gate.static_global_artifact_identity(
        payload,
        capture_id="static-global-test-capture",
        evidence_pack_id="static-global-test-pack",
    )
    return payload


def resource_handle_revalidation_evaluator_manifest(*, ready: bool = False) -> dict:
    return {
        "schema": gate.RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
        "artifact_identity": {
            "required": True,
            "hash_count": 2,
            "hashes": ["a" * 64, "b" * 64],
            "complete_input_count": 2,
            "missing_or_partial_input_count": 0,
            "invalid_input_count": 0,
        },
        "accepted_sample_count": 32,
        "post_callback_resource_handle_ready": ready,
        "uobject_flags_validity_semantics_proven": ready,
        "blockers": [] if ready else ["uobject_flags_validity_semantics_unproven"],
        "promotion_gate": {
            "ready": ready,
            "blockers": [] if ready else ["uobject_flags_validity_semantics_unproven"],
        },
    }


def internal_uobject_post_callback_contract_manifest(*, overclaim: bool = False) -> dict:
    payload = {
        "schema": gate.INTERNAL_UOBJECT_POST_CALLBACK_CONTRACT_SCHEMA,
        "evidence_kind": "internal_post_callback_rejection_contract",
        "status": "accepted_internal_rejection_contract",
        "source_artifacts": [
            {
                "schema": gate.RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
                "artifact_sha256": "c" * 64,
                "capture_id": "source-capture",
                "evidence_pack_id": "source-pack",
                "consume_gate_status": "accepted",
                "path_redacted": True,
            }
        ],
        "binary_sha256": BINARY_SHA,
        "internal_candidate": {
            "schema": "obelisk.internal-uobject-revalidation-candidate.v1",
            "accepted": True,
            "candidate_level": "internal_static_candidate",
            "source_artifact_hashes": ["a" * 64, "b" * 64],
            "contract": {
                "name": "InternalUObjectRevalidationCandidate",
                "lifetime": "frame_local_only",
                "post_callback_lookup": "rejected",
                "output": "copied_bool_or_obelisk_owned_data_only",
                "public_api": "not_promoted",
                "flag_policy": {
                    "0x100": "reject",
                    "0x4000": "reject_by_default",
                },
            },
        },
        "contract": {
            "subject": "InternalUObjectRevalidationCandidate",
            "lifetime": "frame_local_only",
            "validity_scope": "same_hook_or_callback_frame_only",
            "post_callback_lookup": "allowed" if overclaim else "rejected",
            "post_callback_use": "rejected",
            "resource_handle": "not_promoted",
            "gobjects_lookup": "not_promoted",
            "object_identity": "not_promoted",
            "inputs": [
                "internal_index_serial_evidence",
                "binary_sha256",
                "complete_consumed_artifact_identity",
            ],
            "acceptance_checks_frame_local_only": [
                "supported_binary_sha256",
                "accepted_consume_gate",
                "coherent_gobjects_evidence",
                "in_bounds_chunk_and_item",
                "readable_fuobjectitem",
                "nonzero_serial",
                "serial_match_at_current_candidate_slot",
                "non_null_uobject",
                "plausible_membership",
            ],
            "flag_policy": {
                "UObject+0x8&0x100": "reject",
                "UObject+0x8&0x4000": "reject_by_default",
                "0x4000_exception": "allowed_only_inside_a_reviewed_helper_mode_before_callback_return",
            },
            "post_callback_behavior": {
                "stored_token": "invalid",
                "lookup_attempt": "fail_closed",
                "return_value": "not_found_or_invalid",
                "ue_pointer_return": "forbidden",
                "raw_identity_return": "forbidden",
            },
            "output": "copied_bool_or_reason_or_obelisk_owned_copied_data_only",
            "forbidden_outputs": [
                "UObject_pointer",
                "GObjects_index",
                "FUObjectItem_address",
                "serial",
                "InternalIndex",
                "persistent_handle",
                "lookup_token",
                "mutation_path",
                "return_override",
            ],
            "public_api": "not_promoted",
        },
        "contract_checks": {
            "source_candidate_accepted": True,
            "source_post_callback_resource_handle_ready": False,
            "frame_local_lifetime_required": True,
            "post_callback_lookup_rejected": True,
            "public_resource_handle_contract_present": False,
            "public_resourcehandle_policy_present": False,
            "post_callback_lifetime_contract_present": True,
            "post_callback_lifetime_policy_proven": True,
            "runtime_object_samples_present": False,
            "serial_reuse_or_wraparound_policy_present": False,
        },
        "remaining_blockers": [
            "candidate_only_post_callback_rejection_contract",
            "no_public_resource_handle_contract",
            "public_resourcehandle_policy_missing",
            "post_callback_lifetime_policy_unproven",
            "no_serial_reuse_or_wraparound_policy",
            "no_rejected_runtime_object_samples",
            "uobject_flags_validity_semantics_unproven",
        ],
        "non_claims": [
            "does_not_unlock_resource_handle",
            "does_not_promote_gobjects_lookup",
            "does_not_promote_public_object_identity",
            "does_not_claim_post_callback_lookup",
            "does_not_allow_mutation_or_return_override",
            "does_not_replace_rejected_runtime_object_samples",
        ],
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": overclaim,
        "post_callback_lookup_ready": False,
        "promotion_gate": {
            "ready": False,
            "blockers": ["candidate_only_post_callback_rejection_contract"],
        },
    }
    identity_without_hash = {
        "artifact_kind": gate.INTERNAL_UOBJECT_POST_CALLBACK_CONTRACT_SCHEMA,
        "capture_id": "post-callback-contract-test",
        "evidence_pack_id": "post-callback-contract-pack",
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": {
            "schema": payload["schema"],
            "evidence_kind": payload["evidence_kind"],
            "status": payload["status"],
            "source_artifacts": payload["source_artifacts"],
            "binary_sha256": payload["binary_sha256"],
            "internal_candidate": payload["internal_candidate"],
            "contract": payload["contract"],
            "contract_checks": payload["contract_checks"],
            "remaining_blockers": payload["remaining_blockers"],
            "non_claims": payload["non_claims"],
            "promotion_ready": payload["promotion_ready"],
            "public_resource_handle_ready": payload["public_resource_handle_ready"],
            "post_callback_resource_handle_ready": payload["post_callback_resource_handle_ready"],
            "post_callback_lookup_ready": payload["post_callback_lookup_ready"],
            "promotion_gate": payload["promotion_gate"],
        },
    }
    payload["output_artifact_identity"] = {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(gate.canonical_json_bytes(material)).hexdigest(),
    }
    return payload


def internal_uobject_serial_policy_manifest() -> dict:
    return serial_policy_builder.build_policy(
        {
            "schema": serial_policy_builder.RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
            "output_artifact_identity": {
                "artifact_kind": serial_policy_builder.RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
                "artifact_sha256": "c" * 64,
                "capture_id": "source-capture",
                "evidence_pack_id": "source-pack",
            },
            "artifact_identity": {
                "required": True,
                "hash_count": 2,
                "hashes": ["a" * 64, "b" * 64],
                "complete_input_count": 2,
                "missing_or_partial_input_count": 0,
                "invalid_input_count": 0,
            },
            "reconciliation_summary": {
                "sample_count": 44,
                "accepted_sample_count": 44,
                "rejected_sample_count": 0,
                "membership_pass_count": 44,
                "serial_candidate_zero_count": 0,
                "serial_candidate_nonzero_count": 44,
                "serial_candidate_missing_count": 0,
            },
            "evidence_checks": {
                "serial_reuse_or_wraparound_policy_present": False,
            },
            "promotion_ready": False,
            "public_resource_handle_ready": False,
            "post_callback_resource_handle_ready": False,
            "internal_uobject_revalidation_candidate": {
                "schema": serial_policy_builder.INTERNAL_UOBJECT_REVALIDATION_CANDIDATE_SCHEMA,
                "accepted": True,
                "candidate_level": "internal_static_candidate",
                "binary_sha256": BINARY_SHA,
                "source_post_callback_resource_handle_ready": False,
                "candidate": serial_policy_builder.INTERNAL_UOBJECT_REVALIDATION_CONTRACT,
            },
        },
        capture_id="serial-policy-test",
        evidence_pack_id="serial-policy-pack",
    )


def runtime_artifact_source_serial_policy() -> dict:
    return {
        "schema": gate.INTERNAL_UOBJECT_REVALIDATION_SERIAL_POLICY_SCHEMA,
        "artifact_sha256": "d" * 64,
        "capture_id": "serial-policy-source",
        "evidence_pack_id": "serial-policy-pack",
        "consume_gate_status": "accepted",
        "path_redacted": True,
    }


def runtime_redacted_run_identity() -> dict:
    return {
        "redacted": True,
        "approved_debug_window": True,
        "target_instance_redacted": True,
        "map_redacted": True,
        "binary_sha256": BINARY_SHA,
        "obelisk_commit": "unit-test-commit",
        "marker_profile": "approved-runtime-observation",
        "allowlist_label": "unit-test-allowlist",
        "broad_tracing": False,
        "reflection_scanner": False,
        "ptrace_or_gcore": False,
    }


def runtime_privacy_contract() -> dict:
    return {
        "raw_ue_pointers": False,
        "object_indices": False,
        "serial_values": False,
        "class_name_outer_paths": False,
        "player_or_gameplay_payloads": False,
        "persistent_lookup_tokens": False,
        "broad_tracing_evidence": False,
        "fuobjectitem_0xC_as_serial": False,
    }


def attach_runtime_output_identity(payload: dict, *, schema: str, capture_id: str, evidence_pack_id: str) -> None:
    identity_without_hash = {
        "artifact_kind": schema,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
    }
    if schema == gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA:
        report = gate.internal_uobject_runtime_rejection_samples_canonical_report(payload)
    elif schema == gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA:
        report = gate.internal_uobject_runtime_serial_semantics_canonical_report(payload)
    else:
        raise AssertionError(f"unexpected runtime schema: {schema}")
    material = {
        "artifact_identity": identity_without_hash,
        "report": report,
    }
    payload["output_artifact_identity"] = {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(gate.canonical_json_bytes(material)).hexdigest(),
    }


def runtime_rejection_samples_manifest() -> dict:
    payload = {
        "schema": gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA,
        "evidence_kind": "internal_runtime_rejection_samples_candidate",
        "status": "accepted_internal_candidate_samples",
        "redacted_run_identity": runtime_redacted_run_identity(),
        "source_artifacts": [runtime_artifact_source_serial_policy()],
        "binary_sha256": BINARY_SHA,
        "rows": [
            {
                "row_id": "reject-row-1",
                "allowlist_label": "unit-test-allowlist",
                "candidate_slot_in_bounds": True,
                "fuobjectitem_readable": True,
                "object_present": True,
                "fuobjectitem_dword_0x8_match": "nonzero_match",
                "fuobjectitem_dword_0xC": "observed_unknown_dword_present",
                "uobject_0x8_candidate_reject_bits": {
                    "bit_0x100": True,
                    "bit_0x4000": False,
                },
                "decision": "reject",
                "reject_reason": "flag_policy_0x100",
                "copied_output": "reason_category_only",
            }
        ],
        "summary": {
            "object_present_reject_rows": 1,
            "accepted_rows": 0,
        },
        "privacy": runtime_privacy_contract(),
        "remaining_blockers": [
            "candidate_only_runtime_rejection_samples",
            "public_resourcehandle_policy_missing",
            "no_public_resource_handle_contract",
        ],
        "non_claims": [
            "does_not_unlock_resource_handle",
            "does_not_promote_gobjects_lookup",
            "does_not_promote_public_object_identity",
            "does_not_allow_mutation_or_return_override",
            "does_not_promote_persistent_handles",
            "does_not_replace_runtime_serial_semantics",
        ],
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "promotion_gate": {
            "ready": False,
            "blockers": ["candidate_only_runtime_rejection_samples"],
        },
    }
    attach_runtime_output_identity(
        payload,
        schema=gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA,
        capture_id="runtime-rejection-test",
        evidence_pack_id="runtime-rejection-pack",
    )
    return payload


def runtime_serial_semantics_manifest() -> dict:
    payload = {
        "schema": gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
        "evidence_kind": "internal_runtime_serial_semantics_candidate",
        "status": "accepted_internal_candidate_semantics",
        "redacted_run_identity": runtime_redacted_run_identity(),
        "source_artifacts": [runtime_artifact_source_serial_policy()],
        "binary_sha256": BINARY_SHA,
        "rows": [
            {
                "row_id": "fresh-row",
                "allowlist_label": "unit-test-allowlist",
                "case": "fresh_nonzero_match_same_frame",
                "same_frame": True,
                "fuobjectitem_dword_0x8_status": "fresh_nonzero_match",
                "fuobjectitem_dword_0xC": "observed_unknown_dword_present",
                "decision": "allow_candidate_frame_local_only",
                "copied_output": "reason_category_only",
            },
            {
                "row_id": "reject-row",
                "allowlist_label": "unit-test-allowlist",
                "case": "same_frame_mismatch",
                "same_frame": True,
                "fuobjectitem_dword_0x8_status": "mismatch",
                "fuobjectitem_dword_0xC": "observed_unknown_dword_present",
                "decision": "reject",
                "reject_reason": "serial_mismatch",
                "copied_output": "reason_category_only",
            },
        ],
        "serial_semantics": {
            "unknown_wraparound_reject": True,
            "cross_frame_lookup": "reject",
            "fuobjectitem_dword_0xC": "unknown_not_serial_evidence",
        },
        "privacy": runtime_privacy_contract(),
        "remaining_blockers": [
            "candidate_only_runtime_serial_semantics",
            "public_resourcehandle_policy_missing",
            "no_public_resource_handle_contract",
        ],
        "non_claims": [
            "does_not_unlock_resource_handle",
            "does_not_promote_persistent_handles",
            "does_not_claim_wraparound_safety",
            "does_not_allow_cross_frame_lookup",
            "does_not_allow_mutation_or_return_override",
        ],
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "promotion_gate": {
            "ready": False,
            "blockers": ["candidate_only_runtime_serial_semantics"],
        },
    }
    attach_runtime_output_identity(
        payload,
        schema=gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
        capture_id="runtime-serial-test",
        evidence_pack_id="runtime-serial-pack",
    )
    return payload


def resource_handle_serial_scan_manifest(
    *,
    include_candidate: bool = True,
    candidate_flags: int = 0x100,
    core_path: str = "/tmp/copied-core",
    core_sha256: str = "b" * 64,
) -> dict:
    expected_allow4000 = "reject" if candidate_flags & (0x100 | 0x8000) else "allow_candidate"
    return {
        "schema": gate.RESOURCE_HANDLE_SERIAL_SCAN_SCHEMA,
        "status": "candidate_blocked",
        "evidence_kind": "internal_offline_scan_candidate",
        "source_label": "unit-test",
        "core_path": core_path,
        "core_sha256": core_sha256,
        "core_sha256_verified": True,
        "binary_sha256": BINARY_SHA,
        "gobjects": "0x595b7e0",
        "fname_root_slot": "0x5956f30",
        "scan_limit": 1024,
        "provenance": {
            "schema": gate.RESOURCE_HANDLE_SERIAL_SCAN_PROVENANCE_SCHEMA,
            "producer": "scan_resource_handle_serials.py",
            "tool_path": "scripts/scan_resource_handle_serials.py",
            "verified": True,
            "path_redacted": True,
            "argv": ["scripts/scan_resource_handle_serials.py", "--core", "<redacted-path>"],
            "obelisk_commit": "unit-test",
            "core_sha256_verified": True,
            "core_sha256": core_sha256,
            "binary_sha256": BINARY_SHA,
            "gobjects": "0x595b7e0",
            "fname_root_slot": "0x5956f30",
            "scan_limit": 1024,
        },
        "metadata": {},
        "totals": {
            "objects_read": 1,
            "serial_nonzero": 1,
            "membership_pass_count": 1,
            "flags_any": 1,
        },
        "flag_rejection_candidate_samples": [
            {
                "index": 0,
                "serial": 1001,
                "object_ptr_present": True,
                "gobjects_membership_pass": True,
                "flags": candidate_flags,
                "has_0x100": bool(candidate_flags & 0x100),
                "has_0x4000": bool(candidate_flags & 0x4000),
                "has_0x8000": bool(candidate_flags & 0x8000),
                "policy_result_strict": "reject",
                "policy_result_allow4000": expected_allow4000,
            }
        ]
        if include_candidate
        else [],
        "interpretation": {
            "item_dword_0x8": "nonzero samples support serial-backed FUObjectItem+0x8 for internal tooling",
            "uobject_flags_masks": "coherent 0x100/0x4000/0x8000 candidate rejection samples found; semantics still require classification",
            "public_resource_handle_ready": False,
        },
        "consume_gate_expectation": {
            "schema": gate.RESOURCE_HANDLE_SERIAL_SCAN_CONSUME_GATE_SCHEMA,
            "consume_ready": True,
            "promote_ready": False,
            "blockers": [],
            "non_claims": sorted(gate.REQUIRED_RESOURCE_HANDLE_SERIAL_SCAN_NON_CLAIMS),
        },
    }


def resource_handle_serial_scan_manifest_with_core(workspace: Path, **overrides: object) -> dict:
    core = workspace / "copied-core"
    core.parent.mkdir(parents=True, exist_ok=True)
    core.write_bytes(b"offline copied core fixture\n")
    return resource_handle_serial_scan_manifest(
        core_path=str(core),
        core_sha256=gate.sha256_file(core),
        **overrides,
    )


def uobject_flag_policy_report_manifest(*, promotion_ready: bool = False, include_artifact_identity: bool = True) -> dict:
    payload = {
        "schema": gate.UOBJECT_FLAG_POLICY_REPORT_SCHEMA,
        "evidence_kind": "static_negative_equivalent_candidate",
        "status": "candidate_blocked",
        "binary": {
            "sha256": BINARY_SHA,
            "path_redacted": True,
        },
        "promotion_ready": promotion_ready,
        "post_callback_resource_handle_ready": False,
        "windows_summary": {
            "required": sorted(gate.REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS),
            "observed": [
                {
                    "name": name,
                    "artifact_sha256": "b" * 64,
                    "byte_count": 128,
                    "matched_patterns": sorted(gate.REQUIRED_UOBJECT_FLAG_POLICY_WINDOW_PATTERNS[name]),
                    "path_redacted": True,
                    "provenance": {
                        "schema": "obelisk.offline-artifact-provenance.v1",
                        "binary_sha256": BINARY_SHA,
                        "artifact_sha256": "b" * 64,
                        "sidecar_sha256": "d" * 64,
                        "verified": True,
                        "path_redacted": True,
                    },
                }
                for name in sorted(gate.REQUIRED_UOBJECT_FLAG_POLICY_WINDOWS)
            ],
            "all_required_present": True,
            "all_required_patterns_present": True,
        },
        "weak_helper_caller_mode": {
            "schema": gate.WEAK_HELPER_CALLER_MODE_SCHEMA,
            "artifact_sha256": "e" * 64,
            "promotion_gate_ready": False,
            "direct_call_coverage": {
                gate.UOBJECT_FLAG_POLICY_PUBLIC_HELPER_ID: {
                    "expected": 6,
                    "observed": 6,
                },
            },
            "flag_rules": [
                {"mask": "0x100", "result": "null_always"},
                {"mask": "0x4000", "result": "null_when_sil_zero"},
            ],
            "caller_rows_summary": {
                "helper": gate.UOBJECT_FLAG_POLICY_PUBLIC_HELPER_ID,
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
                "caller_rows_sha256": "f" * 64,
            },
            "caller_rows_source": {
                "schema": gate.WEAK_HELPER_CALLER_MODE_SCHEMA,
                "source_artifact_sha256": "e" * 64,
                "binary_sha256": BINARY_SHA,
                "caller_rows_sha256": "f" * 64,
                "path_redacted": True,
            },
        },
        "policy_candidates": [
            {
                "mask": "0x100",
                "candidate": "hard_invalid_static_negative_equivalent",
                "support": sorted(gate.REQUIRED_UOBJECT_FLAG_POLICY_CANDIDATES["0x100"]["support"]),
                "ue_lifecycle_name": "not_promoted",
            },
            {
                "mask": "0x4000",
                "candidate": "strict_invalid_static_negative_equivalent",
                "support": sorted(gate.REQUIRED_UOBJECT_FLAG_POLICY_CANDIDATES["0x4000"]["support"]),
                "ue_lifecycle_name": "not_promoted",
            },
        ],
        "internal_revalidation_contract": json.loads(
            json.dumps(gate.REQUIRED_UOBJECT_FLAG_POLICY_INTERNAL_REVALIDATION_CONTRACT)
        ),
        "remaining_blockers": sorted(gate.REQUIRED_UOBJECT_FLAG_POLICY_BLOCKERS),
        "non_claims": sorted(gate.REQUIRED_UOBJECT_FLAG_POLICY_NON_CLAIMS),
    }
    if include_artifact_identity:
        payload["artifact_identity"] = gate.uobject_flag_policy_artifact_identity(
            payload,
            artifact_kind=gate.UOBJECT_FLAG_POLICY_REPORT_SCHEMA,
            capture_id="uobject-flag-policy-capture",
            evidence_pack_id="uobject-flag-policy-pack",
        )
    return payload


def uobject_flag_policy_report_manifest_with_legacy_caller_mode() -> dict:
    payload = uobject_flag_policy_report_manifest()
    weak_helper = payload["weak_helper_caller_mode"]
    weak_helper.pop("caller_rows_summary")
    weak_helper.pop("caller_rows_source")
    weak_helper["caller_mode_summary"] = {
        "helper": gate.UOBJECT_FLAG_POLICY_PUBLIC_HELPER_ID,
        "source_detail": "legacy_redacted_aggregate",
        "row_count": 6,
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
        "aggregate_source_sha256": "f" * 64,
    }
    weak_helper["caller_mode_source"] = {
        "schema": gate.WEAK_HELPER_CALLER_MODE_SCHEMA,
        "source_artifact_sha256": "e" * 64,
        "binary_sha256": BINARY_SHA,
        "aggregate_source_sha256": "f" * 64,
        "path_redacted": True,
    }
    return payload


def uobject_flag_transition_matrix_manifest(*, promotion_ready: bool = False) -> dict:
    required_windows = sorted(gate.REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOWS)
    return {
        "schema": gate.UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA,
        "evidence_kind": "static_uobject_plus_0x8_flag_transition_candidate",
        "status": "candidate_blocked",
        "binary": {
            "sha256": BINARY_SHA,
            "path_redacted": True,
        },
        "builder_contract": {
            "input_kind": "precut_objdump_windows",
            "matrix_kind": "semantic_helper_windows",
            "fail_closed": True,
            "requires_live_server": False,
            "promotion_ready": promotion_ready,
            "resource_handle_claim": False,
            "public_lifecycle_names_assigned": False,
        },
        "windows_summary": {
            "required": required_windows,
            "optional": ["uobject_100_clear_1d637c8_1d63888"],
            "observed": [
                {
                    "name": name,
                    "artifact_sha256": "c" * 64,
                    "byte_count": 128,
                    "matched_patterns": sorted(gate.REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOW_PATTERNS[name]),
                    "path_redacted": True,
                    "provenance": {
                        "schema": "obelisk.offline-artifact-provenance.v1",
                        "binary_sha256": BINARY_SHA,
                        "artifact_sha256": "c" * 64,
                        "sidecar_sha256": "d" * 64,
                        "verified": True,
                        "path_redacted": True,
                    },
                }
                for name in required_windows
            ],
            "all_required_present": True,
            "all_required_patterns_present": True,
            "groups": {
                "predicate_windows": ["weak_validity_mode_a30_1d56a30_1d56ae0"],
                "caller_mode_windows": ["weak_publish_from_uobject_1d56970_1d56a30"],
                "mutation_windows": ["gc_mark_100_8000_1d18a90_1d18c70"],
            },
        },
        "transition_matrix": {
            "0x100": {
                "candidate_only": True,
                "public_lifecycle_name_assigned": False,
                "promotion_ready": False,
                "mask": "0x100",
                "predicate_windows": ["weak_validity_mode_a30_1d56a30_1d56ae0"],
                "mutation_windows": ["gc_mark_100_8000_1d18a90_1d18c70"],
                "remaining_blocker": "candidate_requires_independent_lifecycle_validation",
            },
            "0x4000": {
                "candidate_only": True,
                "public_lifecycle_name_assigned": False,
                "promotion_ready": False,
                "mask": "0x4000",
                "predicate_windows": ["weak_lookup_strict_c00_1d56c00_1d56c70"],
                "mutation_windows": ["gobjects_4000_skip_mark_2982920_2982b60"],
                "remaining_blocker": "candidate_requires_independent_lifecycle_validation",
            },
            "0x8000": {
                "candidate_only": True,
                "public_lifecycle_name_assigned": False,
                "promotion_ready": False,
                "mask": "0x8000",
                "predicate_windows": [],
                "mutation_windows": ["gc_mark_100_8000_1d18a90_1d18c70"],
                "remaining_blocker": "candidate_requires_independent_lifecycle_validation",
            },
        },
        "remaining_blockers": sorted(gate.REQUIRED_UOBJECT_FLAG_TRANSITION_BLOCKERS),
        "non_claims": sorted(gate.REQUIRED_UOBJECT_FLAG_TRANSITION_NON_CLAIMS),
    }


def uobject_flag_sample_report_manifest(*, promotion_ready: bool = False) -> dict:
    return {
        "schema": gate.UOBJECT_FLAG_SAMPLE_REPORT_SCHEMA,
        "status": "candidate_blocked",
        "promotion_ready": promotion_ready,
        "resource_handle_claim": False,
        "post_callback_resource_handle_ready": False,
        "binary": {
            "sha256": BINARY_SHA,
            "path_redacted": True,
        },
        "source_artifacts": [
            {
                "schema": gate.UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA,
                "artifact_sha256": "b" * 64,
                "binary_sha256": BINARY_SHA,
                "path_redacted": True,
                "consume_gate": {
                    "schema": gate.SCHEMA,
                    "status": "accepted",
                    "mode": "consume",
                    "gate_sha256": "d" * 64,
                    "artifact_sha256": "b" * 64,
                    "binary_sha256": BINARY_SHA,
                    "blocker_count": 0,
                    "path_redacted": True,
                },
            },
            {
                "schema": gate.UOBJECT_FLAG_POLICY_REPORT_SCHEMA,
                "artifact_sha256": "c" * 64,
                "binary_sha256": BINARY_SHA,
                "path_redacted": True,
                "consume_gate": {
                    "schema": gate.SCHEMA,
                    "status": "accepted",
                    "mode": "consume",
                    "gate_sha256": "e" * 64,
                    "artifact_sha256": "c" * 64,
                    "binary_sha256": BINARY_SHA,
                    "blocker_count": 0,
                    "path_redacted": True,
                },
            },
        ],
        "flag_samples": [
            {
                "mask": "0x100",
                "uobject_field": "+0x8",
                "sample_kind": "static_policy_and_transition_candidate",
                "public_lifecycle_name_assigned": False,
                "promotion_ready": False,
                "support": ["weak_validity_mode_a30_1d56a30_1d56ae0"],
            },
            {
                "mask": "0x4000",
                "uobject_field": "+0x8",
                "sample_kind": "static_policy_and_transition_candidate",
                "public_lifecycle_name_assigned": False,
                "promotion_ready": False,
                "support": ["weak_lookup_strict_c00_1d56c00_1d56c70"],
            },
            {
                "mask": "0x8000",
                "uobject_field": "+0x8",
                "sample_kind": "static_transition_candidate",
                "public_lifecycle_name_assigned": False,
                "promotion_ready": False,
                "support": ["gc_mark_100_8000_1d18a90_1d18c70"],
            },
        ],
        "non_claims": sorted(gate.REQUIRED_UOBJECT_FLAG_SAMPLE_NON_CLAIMS),
        "remaining_blockers": sorted(gate.REQUIRED_UOBJECT_FLAG_SAMPLE_BLOCKERS),
        "redaction": {
            "paths": "redacted",
            "raw_snippets": "omitted",
            "addresses": "omitted_or_source_artifact_only",
        },
    }


def uobject_flag_semantic_correlation_manifest(*, promotion_ready: bool = False) -> dict:
    return {
        "schema": gate.UOBJECT_FLAG_SEMANTIC_CORRELATION_SCHEMA,
        "evidence_kind": "static_uobject_flag_semantic_correlation_candidate",
        "status": "candidate_blocked",
        "promotion_ready": promotion_ready,
        "binary": {
            "sha256": BINARY_SHA,
            "path_redacted": True,
        },
        "builder_contract": {
            "fail_closed": True,
            "requires_live_server": False,
            "promotion_ready": promotion_ready,
            "resource_handle_claim": False,
            "public_lifecycle_names_assigned": False,
            "lookup_promotion": False,
            "mutation_promotion": False,
            "return_override_promotion": False,
        },
        "source_pack": {
            "id": "uobject-flag-semantic-decompiler-20260529T155658Z",
            "sha256": "e" * 64,
            "path_redacted": True,
        },
        "inputs": {
            "weak_helper_predicates.txt": {
                "bytes": 128,
                "sha256": "c" * 64,
                "path_redacted": True,
                "provenance": {
                    "schema": "obelisk.offline-artifact-provenance.v1",
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": "c" * 64,
                    "sidecar_sha256": "d" * 64,
                    "verified": True,
                    "path_redacted": True,
                },
            }
        },
        "observations": [
            {
                "id": "weak_helper_reject_predicates",
                "claim_level": "static_observation",
            }
        ],
        "remaining_blockers": sorted(gate.REQUIRED_UOBJECT_FLAG_SEMANTIC_BLOCKERS),
        "non_claims": sorted(gate.REQUIRED_UOBJECT_FLAG_SEMANTIC_NON_CLAIMS),
    }


def weak_helper_static_polarity_manifest(*, promotion_ready: bool = False) -> dict:
    return {
        "schema": gate.WEAK_HELPER_STATIC_POLARITY_REPORT_SCHEMA,
        "evidence_kind": "static_weak_helper_polarity_candidate",
        "status": "candidate_blocked",
        "promotion_ready": promotion_ready,
        "binary": {
            "sha256": BINARY_SHA,
            "path_redacted": True,
        },
        "builder_contract": {
            "fail_closed": True,
            "requires_live_server": False,
            "promotion_ready": promotion_ready,
            "resource_handle_claim": False,
            "public_lifecycle_names_assigned": False,
            "lookup_promotion": False,
            "mutation_promotion": False,
            "return_override_promotion": False,
        },
        "source_pack": {
            "id": "weak-helper-static-polarity-20260529T170000Z",
            "sha256": "e" * 64,
            "path_redacted": True,
            "provenance": {
                "schema": "obelisk.offline-artifact-provenance.v1",
                "binary_sha256": BINARY_SHA,
                "artifact_sha256": "e" * 64,
                "sidecar_sha256": "f" * 64,
                "verified": True,
                "path_redacted": True,
            },
        },
        "inputs": {
            "weak_helper_polarity_windows.txt": {
                "bytes": 128,
                "sha256": "c" * 64,
                "path_redacted": True,
                "provenance": {
                    "schema": "obelisk.static-artifact-provenance.v1",
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": "c" * 64,
                    "sidecar_sha256": "d" * 64,
                    "verified": True,
                    "path_redacted": True,
                },
            }
        },
        "remaining_blockers": sorted(gate.REQUIRED_WEAK_HELPER_STATIC_POLARITY_BLOCKERS),
        "non_claims": sorted(gate.REQUIRED_WEAK_HELPER_STATIC_POLARITY_NON_CLAIMS),
    }


def weak_helper_polarity_caller_mode_manifest() -> dict:
    return {
        "schema": gate.WEAK_HELPER_POLARITY_CALLER_MODE_REPORT_SCHEMA,
        "status": "candidate_blocked",
        "consumption_scope": "internal_static_research_only",
        "binary": {
            "sha256": BINARY_SHA,
            "path_redacted": True,
        },
        "source_artifacts": {
            "prior_caller_mode_redacted": {
                "sha256": "a" * 64,
                "path_redacted": True,
            },
            "semantic_correlation": {
                "sha256": "b" * 64,
                "path_redacted": True,
            },
            "transition_matrix": {
                "sha256": "c" * 64,
                "path_redacted": True,
            },
        },
        "helpers": {
            "0x1d56a30": {
                "window": "weak_validity_mode_a30_1d56a30_1d56ae0.txt",
                "return_kind": "boolean_like_inverted_at_exit",
                "mode_args": ["sil", "dl"],
                "flag_rules": [
                    {"mask": "0x100", "result": "true_before_final_xor_then_inverted_return"},
                    {"mask": "0x4000", "result": "mode_dependent_when_sil_zero"},
                ],
            }
        },
        "remaining_blockers": sorted(gate.REQUIRED_WEAK_HELPER_POLARITY_CALLER_MODE_BLOCKERS),
        "non_claims": sorted(gate.REQUIRED_WEAK_HELPER_POLARITY_CALLER_MODE_NON_CLAIMS),
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def gobjects_two_core_manifest() -> dict:
    sample_set = [
        {"label": "package", "index": 0},
        {"label": "server_chat", "index": 25447},
    ]
    core_summary = {
        "schema": "obelisk.gobjects-sample-reconciliation.v1",
        "sample_count": len(sample_set),
        "accepted_count": len(sample_set),
        "rejected_count": 0,
        "membership_pass_count": len(sample_set),
        "promotion_status": "internal-only-single-artifact",
    }
    payload = {
        "schema": gate.GOBJECTS_TWO_CORE_MANIFEST_SCHEMA,
        "binary_sha256": BINARY_SHA,
        "gobjects_candidate": "0x595b7e0",
        "fname_root_slot": "0x5956f30",
        "sample_set": sample_set,
        "core_count": 2,
        "cores": [
            {"role": "primary", **core_summary},
            {"role": "second", **core_summary},
        ],
        "offline_only": True,
        "ufunction_inventory_input_ready": True,
        "public_gobjects_promotion_ready": False,
        "blocked_contracts": sorted(gate.REQUIRED_GOBJECTS_TWO_CORE_BLOCKED_CONTRACTS),
        "non_claims": [
            "This manifest is an offline input readiness artifact.",
            "It does not promote GObjects/GUObjectArray as runtime-stable.",
            "It does not expose UObject pointers, raw params, object identity, mutation, or return overrides.",
        ],
    }
    payload["artifact_identity"] = gate.gobjects_two_core_artifact_identity(
        payload,
        capture_id="gobjects-two-core-capture",
        evidence_pack_id="gobjects-two-core-pack",
    )
    return payload


def scriptstruct_inventory_child_payload(count: int = 2, *, include_scriptstructs: bool = False) -> dict:
    payload = {
        "schema": "obelisk.scriptstruct-inventory.v1",
        "status": "offline-inventory",
        "source": "offline_core",
        "promotion_status": "not_promoted_candidate_only",
        "metadata": {"object_count": 30000, "max_object_scan": 30000},
        "filters": {"target_sets": ["transfer-scriptstruct"], "targets": []},
        "summary": {
            "scriptstruct_count": count,
            "candidate_count": count,
            "rejected_count": 0,
            "top_outers": [{"outer": "PrimalLocalProfile", "count": count}],
            "top_property_classes": [],
        },
        "target_set_coverage": {
            "schema": "obelisk.scriptstruct-inventory-target-set-coverage.v1",
            "target_sets": ["transfer-scriptstruct"],
            "requested_count": count,
            "matched_count": count,
            "missing_count": 0,
            "missing_targets": [],
            "ambiguous_count": 0,
            "ambiguous_targets": [],
            "matched_targets": {},
        },
    }
    if include_scriptstructs:
        payload["scriptstructs"] = [
            {
                "outer_name": "PrimalLocalProfile",
                "name": "ARKTributeDino",
                "properties": [],
            },
            {
                "outer_name": "PrimalLocalProfile",
                "name": "ArkTributePlayerData",
                "properties": [
                    {
                        "name": "bWasAllowDPCUpload",
                        "class_name": "BoolProperty",
                        "offset_internal": 272,
                        "element_size": 1,
                        "array_dim": 1,
                        "bool_field_size": 1,
                        "bool_byte_offset": 0,
                        "byte_mask": "0x1",
                        "field_mask": "0xff",
                        "native_bool": False,
                        "bool_property_semantics": {
                            "status": "candidate",
                            "reject_reasons": [],
                            "bool_field_size": 1,
                            "bool_byte_offset": 0,
                        },
                    },
                    {
                        "name": "bWithItems",
                        "class_name": "BoolProperty",
                        "offset_internal": 273,
                        "element_size": 1,
                        "array_dim": 1,
                        "bool_field_size": 1,
                        "bool_byte_offset": 0,
                        "byte_mask": "0x01",
                        "field_mask": "0xff",
                        "native_bool": False,
                        "bool_property_semantics": {
                            "status": "candidate",
                            "reject_reasons": [],
                            "bool_field_size": 1,
                            "bool_byte_offset": 0,
                        },
                    },
                    {
                        "name": "bForServerTransfer",
                        "class_name": "BoolProperty",
                        "offset_internal": 280,
                        "element_size": 1,
                        "array_dim": 1,
                        "bool_field_size": 1,
                        "bool_byte_offset": 0,
                        "byte_mask": "0x1",
                        "field_mask": "0xff",
                        "native_bool": False,
                        "bool_property_semantics": {
                            "status": "candidate",
                            "reject_reasons": [],
                            "bool_field_size": 1,
                            "bool_byte_offset": 0,
                        },
                    },
                ],
            }
        ]
    return payload


def fname_root_validation_child_payload() -> dict:
    return {
        "schema": "obelisk.core-fname-root-validation.v1",
        "requested_indices": [{"label": "None", "index": 0}],
        "root_validation": [],
        "manifest_readiness": {
            "ready": True,
            "requested_count": 1,
            "exact_match_count": 1,
            "failed_indices": [],
            "blockers": [],
        },
        "candidate_manifest": {"path": None, "schema": None, "evidence_status": None, "name_count": 0},
    }


def write_scriptstruct_inventory_children(
    root: Path,
    *,
    count: int = 2,
    include_scriptstructs: bool = False,
) -> tuple[str, str]:
    inventory = root / "scriptstruct-inventory.json"
    fname = root / "fname-root-validation.json"
    write_json(inventory, scriptstruct_inventory_child_payload(count, include_scriptstructs=include_scriptstructs))
    write_json(fname, fname_root_validation_child_payload())
    return gate.sha256_file(inventory), gate.sha256_file(fname)


def scriptstruct_inventory_pack_manifest(workspace: Path, *, inventory_sha: str, fname_sha: str) -> dict:
    return {
        "schema": gate.SCRIPTSTRUCT_INVENTORY_PACK_SCHEMA,
        "source": "offline_core",
        "status": "candidate-only",
        "promotion_status": "not_promoted_candidate_only",
        "artifact_identity": {
            "artifact_kind": "offline_core",
            "artifact_sha256": "b" * 64,
            "capture_id": "test-core",
            "evidence_pack_id": "test-pack",
        },
        "binary": {"sha256": BINARY_SHA},
        "core": {"path": str(workspace / "cores" / "core"), "sha256": "b" * 64},
        "addresses": {
            "gobjects": "0x595b7e0",
            "fname_root_slot": "0x5956f30",
            "fname_table": "0x5a94660",
        },
        "inputs": {
            "evidence_pack_manifest": None,
            "target_sets": ["transfer-scriptstruct"],
            "targets": [],
            "max_objects": 30000,
            "fname_indices": [{"label": "None", "index": 0}],
        },
        "artifacts": {
            "scriptstruct_inventory": {
                "path": "scriptstruct-inventory.json",
                "sha256": inventory_sha,
            },
            "fname_root_validation": {
                "path": "fname-root-validation.json",
                "sha256": fname_sha,
            },
        },
        "summary": {
            "scriptstruct_count": 2,
            "fname_root_ready": True,
            "target_requested_count": 2,
            "target_matched_count": 2,
            "target_missing_count": 0,
            "target_ambiguous_count": 0,
        },
        "blockers": [],
        "non_claims": sorted(gate.REQUIRED_SCRIPTSTRUCT_INVENTORY_NON_CLAIMS)
        + [
            "Does not decode transfer, item, inventory, player, actor, dino, tribe, or structure identity.",
            "Does not claim portability across ARK binary hashes.",
        ],
    }


def redacted_scriptstruct_signature_manifest() -> dict:
    def transfer_bool_field(name: str, offset: int) -> dict:
        return {
            "name": name,
            "type": "bool",
            "source_property_class": "BoolProperty",
            "offset": offset,
            "element_size": 1,
            "array_dim": 1,
            "status": "candidate",
            "redaction": "copied scalar candidate",
            "property_flags": "0x10001040002200",
            "bool_field_size": 1,
            "bool_byte_offset": 0,
            "byte_mask": "0x01",
            "field_mask": "0xff",
            "native_bool": False,
            "promotion_blockers": ["scriptstruct_payload_not_runtime_observed"],
        }

    return {
        "schema": gate.REDACTED_SCRIPTSTRUCT_SIGNATURE_SCHEMA,
        "snapshot_root": "redacted",
        "target_sets": ["transfer-scriptstruct"],
        "source_target_sets": [],
        "snapshot_count": 2,
        "signature_count": 2,
        "missing_targets": [],
        "target_set_coverage": {
            "schema": gate.REDACTED_SCRIPTSTRUCT_TARGET_SET_COVERAGE_SCHEMA,
            "status": "complete",
            "complete": True,
            "source": "manifest",
            "declared_target_sets": ["transfer-scriptstruct"],
            "expected_targets": [
                "PrimalLocalProfile.ARKTributeDino",
                "PrimalLocalProfile.ArkTributePlayerData",
            ],
            "observed_targets": [
                "PrimalLocalProfile.ARKTributeDino",
                "PrimalLocalProfile.ArkTributePlayerData",
            ],
            "missing_targets": [],
            "unexpected_targets": [],
        },
        "generated_from": {
            "snapshot_schema": "obelisk.scriptstruct-chain.snapshot.v1",
            "input_snapshots": [
                {"id": "snapshot-0001", "sha256": "c" * 64},
                {"id": "snapshot-0002", "sha256": "d" * 64},
            ],
        },
        "safety_summary": {
            "artifact_status": "candidate_only",
            "promotion_ready": False,
            "intended_use": "offline_review_only",
            "field_count_total": 4,
            "copied_scalar_count_total": 3,
            "copied_scalar_by_kind": {"bool": 3},
            "redacted_count_total": 1,
            "redacted_by_reason": {"text": 1},
            "promotion_blocker_count_total": 0,
            "promotion_blockers_by_reason": {},
            "not_promoted_surfaces": sorted(gate.REQUIRED_REDACTED_SCRIPTSTRUCT_NOT_PROMOTED_SURFACES),
        },
        "signatures": [
            {
                "target": "PrimalLocalProfile.ARKTributeDino",
                "property_count": 1,
                "fields": [{"name": "DinoClassName", "type": "redacted_text"}],
            },
            {
                "target": "PrimalLocalProfile.ArkTributePlayerData",
                "property_count": 3,
                "fields": [
                    transfer_bool_field("bWasAllowDPCUpload", 272),
                    transfer_bool_field("bWithItems", 273),
                    transfer_bool_field("bForServerTransfer", 280),
                ],
            }
        ],
        "non_claims": sorted(gate.REQUIRED_REDACTED_SCRIPTSTRUCT_NON_CLAIMS),
    }


def args(
    *,
    root: Path,
    protected_root: Path,
    manifests: list[Path] | None = None,
    artifacts: list[tuple[str, Path]] | None = None,
    mode: str = "consume",
    expected_binary_sha256: str | None = BINARY_SHA,
    strict_target_set_coverage: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        root=root,
        protected_root=protected_root,
        manifest=manifests or [],
        artifact=artifacts or [],
        expected_binary_sha256=expected_binary_sha256,
        mode=mode,
        strict_target_set_coverage=strict_target_set_coverage,
        json=True,
    )


class ValidateOfflineArtifactGateTests(unittest.TestCase):
    def test_accepts_scriptstruct_inventory_pack_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(manifest.parent, include_scriptstructs=True)
            write_json(manifest, scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["status"], "accepted")
        self.assertEqual([], result["blockers"])

    def test_blocks_scriptstruct_inventory_pack_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(manifest.parent, include_scriptstructs=True)
            write_json(manifest, scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_scriptstruct_inventory_candidate_only", reasons)

    def test_blocks_scriptstruct_inventory_pack_binary_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(manifest.parent, include_scriptstructs=True)
            write_json(manifest, scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha))

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[manifest],
                    expected_binary_sha256="f" * 64,
                )
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_inventory_binary_sha256_mismatch", reasons)

    def test_blocks_scriptstruct_inventory_pack_missing_child_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(manifest.parent)
            (manifest.parent / "scriptstruct-inventory.json").unlink()
            write_json(manifest, scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_inventory_artifact_not_file", reasons)

    def test_blocks_transfer_scriptstruct_inventory_without_scriptstructs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(manifest.parent)
            write_json(manifest, scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_inventory_transfer_scriptstructs_missing", reasons)

    def test_non_transfer_scriptstruct_inventory_does_not_require_transfer_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(manifest.parent)
            payload = scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha)
            payload["inputs"]["target_sets"] = ["mission-scriptstruct"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["status"], "accepted")
        self.assertEqual([], result["blockers"])

    def test_blocks_scriptstruct_inventory_pack_child_schema_and_summary_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(manifest.parent, count=1, include_scriptstructs=True)
            payload = scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha)
            child = json.loads((manifest.parent / "scriptstruct-inventory.json").read_text(encoding="utf-8"))
            child["schema"] = "wrong.schema"
            write_json(manifest.parent / "scriptstruct-inventory.json", child)
            payload["artifacts"]["scriptstruct_inventory"]["sha256"] = gate.sha256_file(manifest.parent / "scriptstruct-inventory.json")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_inventory_artifact_schema_mismatch", reasons)
        self.assertIn("scriptstruct_inventory_artifact_summary_mismatch", reasons)

    def test_blocks_scriptstruct_inventory_pack_bool_tail_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(
                manifest.parent,
                include_scriptstructs=True,
            )
            inventory_path = manifest.parent / "scriptstruct-inventory.json"
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            bool_prop = inventory["scriptstructs"][1]["properties"][0]
            bool_prop.pop("bool_field_size")
            bool_prop.pop("bool_byte_offset")
            bool_prop["bool_property_semantics"].pop("bool_field_size")
            bool_prop["bool_property_semantics"].pop("bool_byte_offset")
            write_json(inventory_path, inventory)
            inventory_sha = gate.sha256_file(inventory_path)
            write_json(manifest, scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_inventory_bool_bool_field_size_mismatch", reasons)
        self.assertIn("scriptstruct_inventory_bool_bool_byte_offset_mismatch", reasons)
        self.assertIn("scriptstruct_inventory_bool_property_semantics_bool_field_size_mismatch", reasons)
        self.assertIn("scriptstruct_inventory_bool_property_semantics_bool_byte_offset_mismatch", reasons)

    def test_blocks_transfer_scriptstruct_inventory_missing_expected_bool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-pack" / "manifest.json"
            inventory_sha, fname_sha = write_scriptstruct_inventory_children(
                manifest.parent,
                include_scriptstructs=True,
            )
            inventory_path = manifest.parent / "scriptstruct-inventory.json"
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            player_data = inventory["scriptstructs"][1]
            player_data["properties"] = [
                prop for prop in player_data["properties"] if prop["name"] != "bForServerTransfer"
            ]
            write_json(inventory_path, inventory)
            inventory_sha = gate.sha256_file(inventory_path)
            write_json(manifest, scriptstruct_inventory_pack_manifest(workspace, inventory_sha=inventory_sha, fname_sha=fname_sha))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_inventory_transfer_bool_missing", reasons)

    def test_accepts_redacted_scriptstruct_signatures_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            write_json(manifest, redacted_scriptstruct_signature_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["status"], "accepted")
        self.assertEqual([], result["blockers"])

    def test_blocks_redacted_transfer_scriptstruct_missing_expected_bool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            payload = redacted_scriptstruct_signature_manifest()
            player_data = payload["signatures"][1]
            player_data["fields"] = [
                field for field in player_data["fields"] if field["name"] != "bForServerTransfer"
            ]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_signature_transfer_bool_missing", reasons)

    def test_blocks_redacted_transfer_scriptstruct_missing_bool_even_without_target_set_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            payload = redacted_scriptstruct_signature_manifest()
            payload["target_sets"] = []
            payload["source_target_sets"] = []
            player_data = payload["signatures"][1]
            player_data["fields"] = [
                field for field in player_data["fields"] if field["name"] != "bForServerTransfer"
            ]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_signature_transfer_bool_missing", reasons)

    def test_blocks_redacted_transfer_scriptstruct_bool_tail_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            payload = redacted_scriptstruct_signature_manifest()
            payload["source_target_sets"] = ["transfer-scriptstruct"]
            payload["target_sets"] = []
            payload["signatures"][1]["fields"][1]["bool_field_size"] = 4
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_signature_transfer_bool_bool_field_size_mismatch", reasons)

    def test_blocks_redacted_transfer_scriptstruct_incomplete_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            payload = redacted_scriptstruct_signature_manifest()
            payload["target_set_coverage"]["status"] = "incomplete"
            payload["target_set_coverage"]["complete"] = False
            payload["target_set_coverage"]["missing_targets"] = [
                "PrimalLocalProfile.ArkTributePlayerData"
            ]
            payload["target_set_coverage"]["observed_targets"] = [
                "PrimalLocalProfile.ARKTributeDino"
            ]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_signature_transfer_target_set_coverage_status_mismatch", reasons)
        self.assertIn("scriptstruct_signature_transfer_target_set_coverage_incomplete", reasons)
        self.assertIn("scriptstruct_signature_transfer_target_set_coverage_missing_targets", reasons)
        self.assertIn("scriptstruct_signature_transfer_target_set_coverage_observed_targets_mismatch", reasons)

    def test_non_transfer_redacted_scriptstruct_does_not_require_transfer_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            payload = redacted_scriptstruct_signature_manifest()
            payload["target_sets"] = ["mission-scriptstruct"]
            payload["source_target_sets"] = []
            payload["signatures"] = payload["signatures"][:1]
            payload["signature_count"] = 1
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["status"], "accepted")
        self.assertEqual([], result["blockers"])

    def test_blocks_redacted_scriptstruct_signatures_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            write_json(manifest, redacted_scriptstruct_signature_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_scriptstruct_signature_candidate_only", reasons)

    def test_accepts_artifact_with_verified_sidecar_under_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            artifact = workspace / "pack" / "artifact.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("offline evidence\n", encoding="utf-8")
            artifact_sha = gate.sha256_file(artifact)
            write_json(
                Path(f"{artifact}.provenance.json"),
                {
                    "schema": gate.PROVENANCE_SCHEMA,
                    "verified": True,
                    "artifact_kind": "objdump",
                    "producer": "test",
                    "tool": "objdump",
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": artifact_sha,
                    "source_provenance": {},
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("objdump", artifact)]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertTrue(result["artifacts"][0]["provenance_verified"])
        self.assertEqual(artifact_sha, result["artifacts"][0]["sha256"])

    def test_rejects_direct_protected_dump_path_before_existence_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            dump = protected / "obelisk" / "dumps" / "core"

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("core", dump)]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("path_text_under_protected_root", reasons)

    def test_rejects_workspace_symlink_resolving_to_live_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            live = protected / "live"
            live.mkdir(parents=True)
            workspace.mkdir(parents=True)
            link = workspace / "linked-live"
            link.symlink_to(live)

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("linked", link)]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("path_not_resolved_under_workspace_root", reasons)

    def test_rejects_live_symlink_even_when_it_resolves_into_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            artifact = workspace / "artifact.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("offline evidence\n", encoding="utf-8")
            live_link = protected / "live-link"
            live_link.symlink_to(artifact)

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("linked", live_link)]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("path_text_under_protected_root", reasons)

    def test_allows_similar_prefix_outside_protected_but_not_as_workspace_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            similar = Path(tmp) / "server-not-live" / "artifact.txt"
            similar.parent.mkdir(parents=True)
            similar.write_text("not protected prefix\n", encoding="utf-8")

            path_only = gate.path_blockers(
                similar,
                label="similar",
                workspace_root=workspace,
                protected_root=protected,
                require_workspace=False,
            )
            artifact_result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("similar", similar)]))

        self.assertEqual([], path_only)
        self.assertIn("path_not_textually_under_workspace_root", {b["reason"] for b in artifact_result["blockers"]})

    def test_rejects_missing_malformed_unverified_and_hash_mismatch_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            artifact = workspace / "artifact.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("offline evidence\n", encoding="utf-8")

            missing = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("missing", artifact)]))
            Path(f"{artifact}.provenance.json").write_text("{", encoding="utf-8")
            malformed = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("bad", artifact)]))
            write_json(
                Path(f"{artifact}.provenance.json"),
                {
                    "schema": gate.PROVENANCE_SCHEMA,
                    "verified": False,
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": "b" * 64,
                },
            )
            bad = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("bad", artifact)]))

        self.assertIn("missing_provenance_sidecar", {b["reason"] for b in missing["blockers"]})
        self.assertIn("malformed_json", {b["reason"] for b in malformed["blockers"]})
        bad_reasons = {b["reason"] for b in bad["blockers"]}
        self.assertIn("provenance_not_verified", bad_reasons)
        self.assertIn("provenance_artifact_sha256_mismatch", bad_reasons)

    def test_rejects_nested_protected_path_in_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            artifact = workspace / "artifact.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("offline evidence\n", encoding="utf-8")
            write_json(
                Path(f"{artifact}.provenance.json"),
                {
                    "schema": gate.PROVENANCE_SCHEMA,
                    "verified": True,
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": gate.sha256_file(artifact),
                    "source_provenance": {"nested": {"source_path": str(protected / "live" / "objdump.txt")}},
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("objdump", artifact)]))

        self.assertIn("path_text_under_protected_root", {b["reason"] for b in result["blockers"]})

    def test_rejects_protected_path_list_in_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            artifact = workspace / "artifact.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("offline evidence\n", encoding="utf-8")
            write_json(
                Path(f"{artifact}.provenance.json"),
                {
                    "schema": gate.PROVENANCE_SCHEMA,
                    "verified": True,
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": gate.sha256_file(artifact),
                    "source": [str(protected / "live" / "objdump.txt")],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("objdump", artifact)]))

        self.assertIn("path_text_under_protected_root", {b["reason"] for b in result["blockers"]})

    def test_accepts_complete_core_manifest_and_blocks_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            write_json(
                manifest,
                {
                    "schema": "obelisk.core-dump-evidence-pack.v1",
                    "binary": {"sha256": BINARY_SHA},
                    "evidence_status": {"status": "complete", "gdb_core_failed": False},
                    "core": {"path": str(workspace / "core"), "sha256": "c" * 64},
                },
            )
            accepted = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))
            write_json(
                manifest,
                {
                    "schema": "obelisk.core-dump-evidence-pack.v1",
                    "binary": {"sha256": BINARY_SHA},
                    "evidence_status": {"status": "partial-gdb-failed", "gdb_core_failed": True},
                },
            )
            blocked = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", accepted["status"])
        blocked_reasons = {b["reason"] for b in blocked["blockers"]}
        self.assertIn("evidence_pack_not_complete", blocked_reasons)
        self.assertIn("evidence_pack_gdb_core_failed", blocked_reasons)

    def test_blocks_unknown_manifest_schema_before_generic_claims_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            write_json(
                manifest,
                {
                    "schema": "obelisk.future-unreviewed-artifact.v1",
                    "promotion_ready": False,
                    "hidden_live_input": str(protected / "live" / "core"),
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("unsupported_manifest_schema", reasons)

    def test_accepts_normalized_artifact_pack_manifest_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "item-return-only-policy-slice-20260530T072255Z"
            pack.mkdir(parents=True)
            (pack / "consume-gate.json").write_text('{"status":"accepted"}\n', encoding="utf-8")
            (pack / "report.json").write_text('{"schema":"fixture"}\n', encoding="utf-8")
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertEqual(gate.ARTIFACT_PACK_MANIFEST_SCHEMA, result["manifests"][0]["schema"])

    def test_artifact_pack_scans_unsupported_child_json_for_generic_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            write_json(
                pack / "unsupported.json",
                {
                    "schema": "fixture",
                    "promotion_ready": True,
                    "notes": str(protected / "live" / "core"),
                },
            )
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promotion_ready_overclaim", reasons)
        self.assertIn("manifest_string_under_protected_root", reasons)

    def test_artifact_pack_blocks_unknown_obelisk_child_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            write_json(pack / "future.json", {"schema": "obelisk.future-unreviewed-artifact.v1"})
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertIn("unsupported_manifest_schema", {blocker["reason"] for blocker in result["blockers"]})

    def test_artifact_pack_blocks_zero_byte_normalizer_summary_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            (pack / "normalize-artifact-pack.json").write_bytes(b"")
            (pack / "report.json").write_text('{"schema":"fixture"}\n', encoding="utf-8")
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertIn("malformed_json", {blocker["reason"] for blocker in result["blockers"]})

    def test_blocks_legacy_artifact_pack_schema_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            write_json(
                pack / artifact_pack.MANIFEST_NAME,
                {
                    "schema": "obelisk.artifact_pack.manifest.v1",
                    "artifact_id": pack.name,
                    "generated_utc": "2026-05-30T07:22:55Z",
                    "files": [],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("unsupported_manifest_schema", reasons)

    def test_protected_root_string_workspace_exception_is_component_aware(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            allowed = workspace / "pack" / "allowed.json"
            blocked = workspace / "pack" / "blocked.json"
            write_json(
                allowed,
                {
                    "schema": "obelisk.core-dump-evidence-pack.v1",
                    "binary": {"sha256": BINARY_SHA},
                    "evidence_status": {"status": "complete", "gdb_core_failed": False},
                    "core": {"path": str(workspace / "core"), "sha256": "c" * 64},
                    "note": str(workspace / "core"),
                },
            )
            write_json(
                blocked,
                {
                    "schema": "obelisk.core-dump-evidence-pack.v1",
                    "binary": {"sha256": BINARY_SHA},
                    "evidence_status": {"status": "complete", "gdb_core_failed": False},
                    "core": {"path": str(workspace / "core"), "sha256": "c" * 64},
                    "note": str(protected / "workspace-offline-old" / "core"),
                },
            )

            allowed_result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[allowed]))
            blocked_result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[blocked]))

        self.assertEqual("accepted", allowed_result["status"])
        self.assertIn("manifest_string_under_protected_root", {blocker["reason"] for blocker in blocked_result["blockers"]})

    def test_blocks_artifact_pack_manifest_when_payload_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            payload = pack / "report.json"
            payload.write_text('{"before":true}\n', encoding="utf-8")
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")
            payload.write_text('{"after":true}\n', encoding="utf-8")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertIn("artifact_pack_not_normalized", {blocker["reason"] for blocker in result["blockers"]})

    def test_blocks_artifact_pack_manifest_with_missing_sha256sums(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            (pack / "report.json").write_text('{"schema":"fixture"}\n', encoding="utf-8")
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")
            (pack / artifact_pack.SHA256SUMS_NAME).unlink()

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertIn("artifact_pack_missing_sha256sums", {blocker["reason"] for blocker in result["blockers"]})

    def test_blocks_artifact_pack_manifest_with_symlinked_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            target = workspace / "outside-report.json"
            target.write_text("{}\n", encoding="utf-8")
            (pack / "report.json").symlink_to(target)
            write_json(
                pack / artifact_pack.MANIFEST_NAME,
                {
                    "schema": gate.ARTIFACT_PACK_MANIFEST_SCHEMA,
                    "artifact_id": pack.name,
                    "generated_utc": "2026-05-30T07:22:55Z",
                    "files": [],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertIn("artifact_pack_symlinked_entry", {blocker["reason"] for blocker in result["blockers"]})

    def test_artifact_pack_preserves_child_promote_mode_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "gobjects-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            write_json(pack / "gobjects-two-core.json", gobjects_two_core_manifest())
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME], mode="promote")
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_artifact_pack_manifest_container_only", reasons)
        self.assertIn("gobjects_two_core_manifest_promote_mode_blocked", reasons)
        self.assertIn("promote_mode_manifest_has_non_claims", reasons)

    def test_artifact_pack_manifest_passed_as_artifact_does_not_validate_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            (pack / "report.json").write_text('{"schema":"fixture"}\n', encoding="utf-8")
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    artifacts=[("pack", pack / artifact_pack.MANIFEST_NAME)],
                )
            )

        self.assertEqual([], result["manifests"])
        self.assertIn("missing_provenance_sidecar", {blocker["reason"] for blocker in result["blockers"]})

    def test_artifact_pack_accepts_serial_policy_child_for_consume_and_blocks_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "serial-policy-pack-20260530T190642Z"
            pack.mkdir(parents=True)
            write_json(pack / "serial-policy.json", internal_uobject_serial_policy_manifest())
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T19:06:42Z")

            consume = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))
            promote = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME], mode="promote")
            )

        self.assertEqual("accepted", consume["status"])
        self.assertEqual([], consume["blockers"])
        reasons = {blocker["reason"] for blocker in promote["blockers"]}
        self.assertIn("promote_mode_artifact_pack_manifest_container_only", reasons)
        self.assertIn("promote_mode_serial_policy_candidate_only", reasons)
        self.assertIn("promote_mode_manifest_has_non_claims", reasons)

    def test_accepts_rc_ufunction_second_source_root_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            root = workspace / "rc-root"
            manifest = root / "manifest.json"
            write_json(manifest, rc_ufunction_second_source_root_manifest(root))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertEqual(gate.RC_UFUNCTION_SECOND_SOURCE_ROOT_SCHEMA, result["manifests"][0]["schema"])

    def test_blocks_rc_ufunction_second_source_root_manifest_hygiene_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            root = workspace / "rc-root"
            manifest = root / "manifest.json"
            payload = rc_ufunction_second_source_root_manifest(root)
            payload["target_sets"] = ["minimal-second-source-intake"]
            payload["target_count"] = payload["target_count"] - 1
            payload["non_claims"] = []
            payload["note"] = "copied from /tmp/raw-rc-root"
            payload["snapshots"][0]["snapshot_sha256"] = "f" * 64
            payload["snapshots"][1]["relative_path"] = "/tmp/leaked.snapshot.json"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("rc_ufunction_manifest_target_sets_mismatch", reasons)
        self.assertIn("rc_ufunction_manifest_target_count_mismatch", reasons)
        self.assertIn("rc_ufunction_manifest_non_claims_missing", reasons)
        self.assertIn("rc_ufunction_manifest_snapshot_sha256_mismatch", reasons)
        self.assertIn("rc_ufunction_manifest_snapshot_relative_path_invalid", reasons)
        self.assertIn("rc_ufunction_manifest_absolute_or_sensitive_path_string", reasons)

    def test_blocks_supported_manifest_hidden_live_path_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-policy-report.json"
            payload = uobject_flag_policy_report_manifest()
            payload["note"] = str(protected / "live" / "core")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "manifest_string_under_protected_root",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_supported_manifest_mixed_workspace_and_live_path_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-policy-report.json"
            payload = uobject_flag_policy_report_manifest()
            payload["note"] = f"workspace={workspace / 'artifact'} live={protected / 'serverfiles' / 'core'}"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "manifest_string_under_protected_root",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_promotion_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            write_json(
                manifest,
                {
                    "schema": "obelisk.gobjects-two-core-manifest.v1",
                    "public_gobjects_promotion_ready": True,
                    "promotion_ready": True,
                    "blockers": ["identity blocked"],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("public_gobjects_promotion_overclaim", reasons)
        self.assertIn("promotion_ready_with_blockers", reasons)

    def test_accepts_gobjects_two_core_manifest_as_candidate_input_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            write_json(manifest, gobjects_two_core_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_blocks_gobjects_two_core_manifest_placeholder_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            payload = gobjects_two_core_manifest()
            payload["artifact_identity"]["capture_id"] = "unspecified-capture"
            payload["artifact_identity"]["evidence_pack_id"] = "unspecified-evidence-pack"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("gobjects_two_core_manifest_artifact_identity_capture_id_invalid", reasons)
        self.assertIn("gobjects_two_core_manifest_artifact_identity_evidence_pack_id_invalid", reasons)

    def test_blocks_gobjects_two_core_manifest_artifact_identity_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            payload = gobjects_two_core_manifest()
            payload["artifact_identity"]["artifact_sha256"] = "0" * 64
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("gobjects_two_core_manifest_artifact_identity_hash_mismatch", reasons)

    def test_blocks_gobjects_two_core_manifest_weak_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            payload = gobjects_two_core_manifest()
            payload["core_count"] = 1
            payload["cores"][1]["accepted_count"] = 1
            payload["blocked_contracts"] = ["ResourceHandle"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("gobjects_two_core_manifest_core_count_invalid", reasons)
        self.assertIn("gobjects_two_core_manifest_core_count_mismatch", reasons)
        self.assertIn("gobjects_two_core_manifest_core_summary_mismatch", reasons)
        self.assertIn("gobjects_two_core_manifest_missing_blocked_contracts", reasons)

    def test_blocks_gobjects_two_core_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            write_json(manifest, gobjects_two_core_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("gobjects_two_core_manifest_promote_mode_blocked", reasons)
        self.assertIn("promote_mode_manifest_has_non_claims", reasons)
        self.assertIn("promote_mode_manifest_has_blocked_contracts", reasons)

    def test_blocks_signature_manifest_unredacted_snapshot_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            write_json(
                manifest,
                {
                    "schema": gate.REDACTED_UFUNCTION_SIGNATURE_SCHEMA,
                    "snapshot_root": str(protected / "live" / "snapshots"),
                    "signatures": [],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("signature_manifest_unredacted_snapshot_root", reasons)
        self.assertIn("path_text_under_protected_root", reasons)

    def test_accepts_redacted_signature_manifest_candidate_only_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            write_json(manifest, redacted_signature_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_strict_accepts_builder_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            target = "SyntheticOfflineArtifact.Target"
            target_set = "offline-artifact-hygiene-intake"
            report = redacted_signature_manifest(
                target=target,
                target_sets=[target_set],
            )
            report["target_set_coverage"] = {
                "schema": gate.TARGET_SET_COVERAGE_SCHEMA,
                "status": "complete",
                "complete": True,
                "declared_target_sets": [
                    {
                        "name": target_set,
                        "source": "manifest",
                        "expected_targets": [target],
                        "covered_targets": [target],
                        "missing_targets": [],
                        "complete": True,
                    }
                ],
                "expected_targets": [target],
                "emitted_targets": [target],
                "missing_targets": [],
                "unexpected_targets": [],
            }
            write_json(manifest, report)

            with mock.patch.object(
                gate,
                "known_ufunction_target_set_targets",
                return_value=[target],
            ):
                result = gate.build_result(
                    args(
                        root=workspace,
                        protected_root=protected,
                        manifests=[manifest],
                        strict_target_set_coverage=True,
                    )
                )

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_strict_blocks_redacted_signature_manifest_missing_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            write_json(manifest, redacted_signature_manifest())

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[manifest],
                    strict_target_set_coverage=True,
                )
            )

        self.assertIn(
            "signature_manifest_missing_target_set_coverage",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_consume_blocks_named_signature_manifest_missing_coverage_without_historical_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest(target_sets=["item-compact-intake"])
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "signature_manifest_missing_target_set_coverage_without_historical_marker",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_consume_accepts_historical_named_signature_manifest_missing_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest(
                target_sets=["item-compact-intake"],
                artifact_hygiene=historical_missing_coverage_marker(),
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_strict_blocks_historical_named_signature_manifest_missing_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest(
                target_sets=["item-compact-intake"],
                artifact_hygiene=historical_missing_coverage_marker(),
            )
            write_json(manifest, payload)

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[manifest],
                    strict_target_set_coverage=True,
                )
            )

        self.assertIn(
            "signature_manifest_missing_target_set_coverage",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_strict_blocks_unknown_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest(safety_overrides={"target_set_count": 1})
            payload["source_target_sets"] = ["not-a-target-set"]
            payload["target_set_coverage"] = {
                "schema": gate.TARGET_SET_COVERAGE_SCHEMA,
                "status": "complete",
                "complete": True,
                "declared_target_sets": [
                    {
                        "name": "not-a-target-set",
                        "source": "snapshot",
                        "expected_targets": ["PrimalItem.AllowEquipItem"],
                        "covered_targets": ["PrimalItem.AllowEquipItem"],
                        "missing_targets": [],
                        "complete": True,
                    }
                ],
                "expected_targets": ["PrimalItem.AllowEquipItem"],
                "emitted_targets": ["PrimalItem.AllowEquipItem"],
                "missing_targets": [],
                "unexpected_targets": [],
            }
            write_json(manifest, payload)

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[manifest],
                    strict_target_set_coverage=True,
                )
            )

        self.assertIn(
            "signature_manifest_unknown_target_set",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_redacted_signature_manifest_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            write_json(manifest, redacted_signature_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn("promote_mode_signature_manifest_candidate_only", {blocker["reason"] for blocker in result["blockers"]})

    def test_blocks_redacted_signature_manifest_summary_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            write_json(manifest, redacted_signature_manifest(safety_overrides={"copied_scalar_by_kind": {}}))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "signature_manifest_safety_summary_count_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_redacted_signature_manifest_top_level_snapshot_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest()
            payload["snapshot_count"] = 2
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "signature_manifest_snapshot_count_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_redacted_signature_manifest_target_set_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest()
            payload["target_sets"] = ["item-compact-intake"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "signature_manifest_safety_summary_count_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_redacted_signature_manifest_invalid_target_sets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest()
            payload["target_sets"] = ["item-compact-intake", ""]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "signature_manifest_target_sets_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_redacted_signature_manifest_source_snapshot_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest()
            payload["signatures"][0]["source_snapshot_sha256"] = "e" * 64
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "signature_manifest_source_snapshot_sha256_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_accepts_weak_helper_caller_mode_internal_static_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper" / "weak-helper.json"
            write_json(
                manifest,
                {
                    "schema": gate.WEAK_HELPER_CALLER_MODE_SCHEMA,
                    "status": "accepted_internal_static_evidence",
                    "binary": {
                        "sha256": gate.WEAK_HELPER_BINARY_SHA256,
                        "path_redacted": True,
                    },
                    "direct_call_coverage": {
                        "0x1d56b60": {"expected": 4, "observed": 4},
                        "0x1d56c70": {"expected": 6, "observed": 6},
                    },
                    "builder_contract": {
                        "promotion_gate_ready": False,
                        "consumption_scope": "internal_static_research_only",
                        "remaining_blockers": ["static_only_evidence"],
                        "not_promoted": ["ResourceHandle"],
                    },
                    "sources": {
                        "direct_call_counts": {
                            "artifact_sha256": "b" * 64,
                            "tool": "objdump-or-radare2",
                            "version": "5.5.0",
                            "provenance": {
                                "schema": "obelisk.offline-artifact-provenance.v1",
                                "verified": True,
                                "path_redacted": True,
                                "binary_sha256": gate.WEAK_HELPER_BINARY_SHA256,
                                "artifact_sha256": "b" * 64,
                                "sidecar_sha256": "e" * 64,
                            },
                        },
                        "ghidra_stdout": {
                            "artifact_sha256": "c" * 64,
                            "tool": "ghidra",
                            "version": "12.1",
                            "provenance": {
                                "schema": "obelisk.offline-artifact-provenance.v1",
                                "verified": True,
                                "path_redacted": True,
                                "binary_sha256": gate.WEAK_HELPER_BINARY_SHA256,
                                "artifact_sha256": "c" * 64,
                                "sidecar_sha256": "f" * 64,
                            },
                        },
                        "r2_windows": {
                            "artifact_sha256": "d" * 64,
                            "tool": "radare2",
                            "version": "5.5.0",
                            "provenance": {
                                "schema": "obelisk.offline-artifact-provenance.v1",
                                "verified": True,
                                "path_redacted": True,
                                "binary_sha256": gate.WEAK_HELPER_BINARY_SHA256,
                                "artifact_sha256": "d" * 64,
                                "sidecar_sha256": "a" * 64,
                            },
                        },
                    },
                    "required_evidence": [
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
                    ],
                    "helpers": {
                        "0x1d56b60": {
                            "return_kind": "boolean_like",
                            "mode_args": ["sil", "dl"],
                        },
                        "0x1d56c70": {
                            "return_kind": "uobject_pointer_or_null",
                            "mode_args": ["sil"],
                        },
                    },
                    "callers": [
                        {
                            "helper": "0x1d56c70",
                            "caller_window_count": 6,
                            "mode_args": {"sil": {"source": "const", "value": 1}},
                            "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
                        },
                        {
                            "helper": "0x1d56b60",
                            "caller_window_count": 2,
                            "mode_args": {"sil": {"source": "const", "value": 0}, "dl": {"source": "const", "value": 1}},
                            "return_use": {"kind": "pairwise_boolean_comparison"},
                        },
                    ],
                    "caller_rows": [
                        {
                            "helper": "0x1d56c70",
                            "helper_address_sha256": weak_helper_address_sha("0x1d56c70"),
                            "caller_address_sha256": weak_helper_address_sha(caller),
                            "mode_args": {"sil": {"source": "const", "value": 1}},
                            "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
                            "source_count": 2,
                            "evidence": ["ghidra", "radare2"],
                            "policy_observation": {
                                "0x100": "null_always",
                                "0x4000": "not_rejected_in_observed_sil_1_callers",
                            },
                            "claim_level": "static_caller_mode_candidate",
                            "path_redacted": True,
                            "lifecycle_names": "not_promoted",
                        }
                        for caller in (
                            "0x83a340",
                            "0x83a720",
                            "0x83cde0",
                            "0x9f80f0",
                            "0x1d299b0",
                            "0x1d29a20",
                        )
                    ],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_blocks_weak_helper_caller_mode_missing_source_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper" / "weak-helper.json"
            write_json(
                manifest,
                {
                    "schema": gate.WEAK_HELPER_CALLER_MODE_SCHEMA,
                    "status": "accepted_internal_static_evidence",
                    "binary": {
                        "sha256": gate.WEAK_HELPER_BINARY_SHA256,
                        "path_redacted": True,
                    },
                    "direct_call_coverage": {
                        "0x1d56b60": {"expected": 4, "observed": 4},
                        "0x1d56c70": {"expected": 6, "observed": 6},
                    },
                    "builder_contract": {
                        "promotion_gate_ready": False,
                        "consumption_scope": "internal_static_research_only",
                        "remaining_blockers": ["static_only_evidence"],
                        "not_promoted": ["ResourceHandle"],
                    },
                    "sources": {
                        "direct_call_counts": {
                            "artifact_sha256": "b" * 64,
                            "tool": "objdump-or-radare2",
                            "version": "5.5.0",
                        },
                        "ghidra_stdout": {
                            "artifact_sha256": "c" * 64,
                            "tool": "ghidra",
                            "version": "12.1",
                        },
                        "r2_windows": {
                            "artifact_sha256": "d" * 64,
                            "tool": "radare2",
                            "version": "5.5.0",
                        },
                    },
                    "required_evidence": [
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
                    ],
                    "helpers": {
                        "0x1d56b60": {
                            "return_kind": "boolean_like",
                            "mode_args": ["sil", "dl"],
                        },
                        "0x1d56c70": {
                            "return_kind": "uobject_pointer_or_null",
                            "mode_args": ["sil"],
                        },
                    },
                    "callers": [
                        {
                            "helper": "0x1d56c70",
                            "caller_window_count": 6,
                            "mode_args": {"sil": {"source": "const", "value": 1}},
                            "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
                        },
                        {
                            "helper": "0x1d56b60",
                            "caller_window_count": 2,
                            "mode_args": {"sil": {"source": "const", "value": 0}, "dl": {"source": "const", "value": 1}},
                            "return_use": {"kind": "pairwise_boolean_comparison"},
                        },
                    ],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn("weak_helper_source_ghidra_stdout_provenance_missing", {blocker["reason"] for blocker in result["blockers"]})

    def test_blocks_weak_helper_caller_mode_bad_caller_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper" / "weak-helper.json"
            payload = weak_helper_caller_mode_manifest()
            row = {
                "helper": "0x1d56b60",
                "helper_address_sha256": "not-a-sha",
                "caller_address_sha256": "c" * 64,
                "mode_args": {"sil": {"source": "const", "value": 0}},
                "return_use": {"register": "rax", "nonzero_path": "ResourceHandle lookup ready"},
                "source_count": 1,
                "evidence": ["ghidra"],
                "policy_observation": {"0x100": "pending-kill"},
                "claim_level": "public_sdk_ready",
                "path_redacted": False,
                "lifecycle_names": "destroyed",
                "source_path": str(workspace / "raw.txt"),
            }
            payload["caller_rows"] = [dict(row) for _ in range(6)]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("weak_helper_caller_row_path_present", reasons)
        self.assertIn("weak_helper_caller_row_helper_mismatch", reasons)
        self.assertIn("weak_helper_caller_row_helper_sha256_mismatch", reasons)
        self.assertIn("weak_helper_caller_row_caller_sha256_duplicate", reasons)
        self.assertIn("weak_helper_caller_row_mode_args_mismatch", reasons)
        self.assertIn("weak_helper_caller_row_return_use_mismatch", reasons)
        self.assertIn("weak_helper_caller_row_source_evidence_mismatch", reasons)
        self.assertIn("weak_helper_caller_row_policy_observation_mismatch", reasons)
        self.assertIn("weak_helper_caller_row_claim_level_mismatch", reasons)
        self.assertIn("weak_helper_caller_row_boundary_mismatch", reasons)
        self.assertIn("weak_helper_caller_row_public_overclaim_resourcehandle", reasons)
        self.assertIn("weak_helper_caller_row_public_overclaim_lookup_ready", reasons)
        self.assertIn("weak_helper_ue_lifecycle_name_overclaim", reasons)

    def test_blocks_weak_helper_caller_mode_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper" / "weak-helper.json"
            write_json(
                manifest,
                {
                    "schema": gate.WEAK_HELPER_CALLER_MODE_SCHEMA,
                    "status": "accepted_internal_static_evidence",
                    "binary": {
                        "sha256": gate.WEAK_HELPER_BINARY_SHA256,
                        "path_redacted": True,
                    },
                    "direct_call_coverage": {
                        "0x1d56b60": {"expected": 4, "observed": 4},
                        "0x1d56c70": {"expected": 6, "observed": 6},
                    },
                    "builder_contract": {
                        "promotion_gate_ready": False,
                        "consumption_scope": "internal_static_research_only",
                        "remaining_blockers": ["static_only_evidence"],
                        "not_promoted": ["ResourceHandle"],
                    },
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn("promote_mode_weak_helper_internal_static_only", {blocker["reason"] for blocker in result["blockers"]})

    def test_blocks_weak_helper_caller_mode_promotion_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper" / "weak-helper.json"
            write_json(
                manifest,
                {
                    "schema": gate.WEAK_HELPER_CALLER_MODE_SCHEMA,
                    "status": "accepted_internal_static_evidence",
                    "binary": {
                        "sha256": gate.WEAK_HELPER_BINARY_SHA256,
                        "path_redacted": False,
                    },
                    "direct_call_coverage": {
                        "0x1d56b60": {"expected": 4, "observed": 3},
                        "0x1d56c70": {"expected": 6, "observed": 6},
                    },
                    "helpers": {"note": "pending-kill"},
                    "builder_contract": {
                        "promotion_gate_ready": True,
                        "consumption_scope": "runtime_ready",
                        "remaining_blockers": [],
                        "not_promoted": [],
                    },
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("weak_helper_binary_path_not_redacted", reasons)
        self.assertIn("weak_helper_direct_call_coverage_incomplete", reasons)
        self.assertIn("weak_helper_promotion_ready_overclaim", reasons)
        self.assertIn("weak_helper_consumption_scope_not_internal_static", reasons)
        self.assertIn("weak_helper_missing_remaining_blockers", reasons)
        self.assertIn("weak_helper_missing_resourcehandle_nonclaim", reasons)
        self.assertIn("weak_helper_ue_lifecycle_name_overclaim", reasons)

    def test_blocks_signature_manifest_legacy_absolute_path_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            write_json(
                manifest,
                {
                    "schema": gate.REDACTED_UFUNCTION_SIGNATURE_SCHEMA,
                    "snapshot_root": "redacted",
                    "signatures": [
                        {
                            "target": "Synthetic.Target",
                            "source_snapshot": str(protected / "live" / "Target.snapshot.json"),
                        }
                    ],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn("path_text_under_protected_root", {blocker["reason"] for blocker in result["blockers"]})

    def test_blocks_signature_manifest_promotion_ready_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            write_json(
                manifest,
                {
                    "schema": gate.REDACTED_UFUNCTION_SIGNATURE_SCHEMA,
                    "snapshot_root": "redacted",
                    "safety_summary": {
                        "artifact_status": "candidate_only",
                        "intended_use": "offline_review_only",
                        "promotion_ready": True,
                    },
                    "signatures": [
                        {
                            "target": "Synthetic.Target",
                            "source_snapshot": "snapshot-0001",
                            "signature_status": "candidate-only",
                        }
                    ],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "signature_manifest_promotion_ready_overclaim",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_signature_manifest_signature_status_and_runtime_ready_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            write_json(
                manifest,
                {
                    "schema": gate.REDACTED_UFUNCTION_SIGNATURE_SCHEMA,
                    "snapshot_root": "redacted",
                    "safety_summary": {
                        "artifact_status": "candidate_only",
                        "intended_use": "offline_review_only",
                        "promotion_ready": False,
                    },
                    "signatures": [
                        {
                            "target": "Synthetic.Target",
                            "source_snapshot": "snapshot-0001",
                            "signature_status": "promoted",
                            "runtime_ready": True,
                        }
                    ],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("signature_manifest_signature_status_not_candidate_only", reasons)
        self.assertIn("signature_manifest_signature_readiness_overclaim", reasons)

    def test_accepts_layout_only_readiness_report_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(manifest, readiness_report_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_ready_readiness_report_without_layout_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(manifest, readiness_report_manifest(include_boundaries=False))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("readiness_report_evidence_scope_not_layout_only", reasons)
        self.assertIn("readiness_report_missing_non_promoted_surfaces", reasons)

    def test_blocks_ready_readiness_report_with_reduced_non_promoted_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            payload = readiness_report_manifest()
            payload["not_promoted_surfaces"] = ["mutation", "object_identity", "public_sdk"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("readiness_report_missing_non_promoted_surfaces", reasons)

    def test_blocks_ready_readiness_report_without_explicit_promotion_ready_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            payload = readiness_report_manifest()
            del payload["promotion_gate"]["promotion_ready"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("readiness_report_promotion_ready_not_false", reasons)

    def test_blocks_readiness_report_without_second_source_gate_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(manifest, readiness_report_manifest(ready=False, gate_mode="informational_gap_report"))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("readiness_report_gate_mode_not_second_source_promotion", reasons)

    def test_blocks_readiness_report_without_named_target_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(manifest, readiness_report_manifest(ready=False, target_sets=[]))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("readiness_report_missing_target_sets", reasons)

    def test_blocks_readiness_report_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(manifest, readiness_report_manifest())

            result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote")
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_readiness_report_layout_only", reasons)

    def test_accepts_item_return_only_policy_slice_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "item-return-policy.json"
            write_json(manifest, item_return_only_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_item_return_only_policy_slice_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "item-return-policy.json"
            write_json(manifest, item_return_only_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_item_return_policy_slice_evidence_only", reasons)

    def test_blocks_item_return_only_policy_slice_with_overclaims_or_bad_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "item-return-policy.json"
            payload = item_return_only_policy_slice_manifest(
                policy_status="accepted",
                promotion_ready=True,
                copied_bool_count=4,
                excluded_field_count=4,
                missing_targets=["PrimalItem.CanRepair"],
                non_claims=["does not copy the excluded fields"],
            )
            payload["copied_return_bools"] = payload["copied_return_bools"][:-1]
            payload["excluded_fields"] = payload["excluded_fields"][:-1]
            payload["coverage"]["copied_fields"] = payload["coverage"]["copied_fields"][:-1]
            payload["coverage"]["excluded_fields"] = payload["coverage"]["excluded_fields"][:-1]
            payload["safety_summary"]["explicitly_excluded"] = ["CraftBlueprint"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("item_return_policy_status_not_evidence_only", reasons)
        self.assertIn("item_return_policy_missing_targets_present", reasons)
        self.assertIn("item_return_policy_promotion_ready_not_false", reasons)
        self.assertIn("item_return_policy_copied_bool_count_not_three", reasons)
        self.assertIn("item_return_policy_excluded_field_count_not_five", reasons)
        self.assertIn("item_return_policy_copied_return_bools_count_mismatch", reasons)
        self.assertIn("item_return_policy_excluded_fields_count_mismatch", reasons)
        self.assertIn("item_return_policy_coverage_copied_fields_mismatch", reasons)
        self.assertIn("item_return_policy_coverage_excluded_fields_mismatch", reasons)
        self.assertIn("item_return_policy_non_claims_missing_required_boundaries", reasons)
        self.assertIn("item_return_policy_explicit_exclusions_missing_internal_boundaries", reasons)

    def test_blocks_item_return_only_policy_slice_public_runtime_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "item-return-policy.json"
            payload = item_return_only_policy_slice_manifest()
            payload["runtime_ready"] = True
            payload["public_sdk_ready"] = True
            payload["claim"] = "public SDK ready"
            payload["runtime_claim"] = "runtime ready"
            payload["input_target_set"] = "item-public-sdk-intake"
            payload["coverage"]["copied_targets"] = ["PrimalItem.AllowEquipItem"]
            payload["coverage"]["input_targets"] = [
                "PrimalItem.AllowEquipItem",
                "PrimalItem.CanRepair",
                "PrimalItem.UseItemOntoItem",
            ]
            payload["generated_from"]["input_snapshots"] = payload["generated_from"]["input_snapshots"][:3]
            payload["copied_return_bools"][0]["target"] = "PublicSdk.PrimalItem"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("item_return_policy_readiness_overclaim", reasons)
        self.assertIn("item_return_policy_public_overclaim_public_sdk", reasons)
        self.assertIn("item_return_policy_public_overclaim_runtime_ready", reasons)
        self.assertIn("item_return_policy_input_target_set_mismatch", reasons)
        self.assertIn("item_return_policy_coverage_copied_targets_mismatch", reasons)
        self.assertIn("item_return_policy_coverage_input_targets_mismatch", reasons)
        self.assertIn("item_return_policy_input_snapshot_count_mismatch", reasons)
        self.assertIn("item_return_policy_copied_bool_target_mismatch", reasons)

    def test_accepts_transfer_baccept_only_policy_slice_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "transfer-baccept-policy.json"
            write_json(manifest, transfer_baccept_only_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_transfer_baccept_only_policy_slice_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "transfer-baccept-policy.json"
            write_json(manifest, transfer_baccept_only_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_transfer_baccept_policy_slice_evidence_only", reasons)

    def test_blocks_transfer_baccept_only_policy_slice_with_bad_counts_or_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "transfer-baccept-policy.json"
            payload = transfer_baccept_only_policy_slice_manifest(
                policy_status="accepted",
                promotion_ready=True,
                copied_bool_count=2,
                forbidden_field_count=1,
                missing_targets=[gate.REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET],
                non_claims=["does not copy other transfer fields"],
            )
            payload["copied_bool"]["copied_field"] = "ShooterPlayerController.ServerTransferredPlayerConfirmationResult.ReturnValue"
            payload["copied_bool"]["target"] = "ShooterPlayerController.ServerDownloadTransferredPlayer"
            payload["copied_bool"]["direction"] = "return"
            payload["copied_bool"]["function_flags"] = "0x0"
            payload["copied_bool"]["native_bool"] = True
            payload["forbidden_transfer_fields"] = payload["forbidden_transfer_fields"][:-1]
            payload["coverage"]["copied_fields"] = []
            payload["coverage"]["copied_targets"] = []
            payload["coverage"]["forbidden_fields"] = payload["coverage"]["forbidden_fields"][:-1]
            payload["coverage"]["input_targets"] = [gate.REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET]
            payload["safety_summary"]["explicitly_excluded"] = ["mutation"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("transfer_baccept_policy_status_not_evidence_only", reasons)
        self.assertIn("transfer_baccept_policy_missing_targets_present", reasons)
        self.assertIn("transfer_baccept_policy_promotion_ready_not_false", reasons)
        self.assertIn("transfer_baccept_policy_copied_bool_count_not_one", reasons)
        self.assertIn("transfer_baccept_policy_forbidden_field_count_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_copied_field_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_copied_bool_target_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_copied_bool_not_input_bool", reasons)
        self.assertIn("transfer_baccept_policy_copied_bool_shape_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_forbidden_fields_count_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_coverage_copied_fields_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_coverage_copied_targets_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_coverage_forbidden_fields_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_coverage_input_targets_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_non_claims_missing_required_boundaries", reasons)
        self.assertIn("transfer_baccept_policy_explicit_exclusions_missing_internal_boundaries", reasons)

    def test_blocks_transfer_baccept_only_policy_slice_with_tampered_shape_or_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "transfer-baccept-policy.json"
            payload = transfer_baccept_only_policy_slice_manifest()
            payload["copied_bool"]["property_flags"] = "0x80"
            payload["copied_bool"]["offset"] = "0x4"
            payload["copied_bool"]["source_snapshot_sha256"] = "7" * 64
            payload["generated_from"]["input_snapshots"][0]["target"] = "ShooterPlayerController.ServerDownloadTransferredPlayer"
            payload["forbidden_transfer_fields"][0]["source_snapshot"] = "unknown-snapshot"
            payload["forbidden_transfer_fields"][1]["source_snapshot_sha256"] = "8" * 64
            payload["forbidden_transfer_fields"][2]["offset"] = "0x40"
            payload["forbidden_transfer_fields"][3]["source_snapshot"] = payload["copied_bool"]["source_snapshot"]
            payload["forbidden_transfer_fields"][3]["source_snapshot_sha256"] = next(
                snapshot["sha256"]
                for snapshot in payload["generated_from"]["input_snapshots"]
                if snapshot["id"] == payload["copied_bool"]["source_snapshot"]
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("transfer_baccept_policy_copied_bool_shape_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_copied_bool_source_snapshot_sha256_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_input_snapshot_targets_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_forbidden_field_source_snapshot_unknown", reasons)
        self.assertIn("transfer_baccept_policy_forbidden_field_source_snapshot_sha256_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_forbidden_field_shape_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_forbidden_field_source_snapshot_target_mismatch", reasons)

    def test_blocks_transfer_baccept_only_policy_slice_public_runtime_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "transfer-baccept-policy.json"
            payload = transfer_baccept_only_policy_slice_manifest()
            payload["runtime_ready"] = True
            payload["public_sdk_ready"] = True
            payload["claim"] = "public SDK ready"
            payload["runtime_claim"] = "runtime ready"
            payload["input_target_set"] = "transfer-public-sdk-intake"
            payload["generated_from"]["input_snapshots"] = [
                {"id": "snapshot-0001", "sha256": "1" * 64},
                {"id": "snapshot-0002", "sha256": "2" * 64},
            ]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("transfer_baccept_policy_readiness_overclaim", reasons)
        self.assertIn("transfer_baccept_policy_public_overclaim_public_sdk", reasons)
        self.assertIn("transfer_baccept_policy_public_overclaim_runtime_ready", reasons)
        self.assertIn("transfer_baccept_policy_input_target_set_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_input_snapshot_count_mismatch", reasons)

    def test_accepts_mission_copied_bool_policy_slice_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "mission-copied-bool-policy.json"
            write_json(manifest, mission_copied_bool_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_mission_copied_bool_policy_slice_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "mission-copied-bool-policy.json"
            write_json(manifest, mission_copied_bool_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_mission_copied_bool_policy_slice_evidence_only", reasons)

    def test_blocks_mission_copied_bool_policy_slice_with_bad_counts_or_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "mission-copied-bool-policy.json"
            payload = mission_copied_bool_policy_slice_manifest(
                policy_status="accepted",
                promotion_ready=True,
                copied_bool_count=4,
                redacted_field_count=5,
                missing_targets=["MissionType.GetPlayerUsableItems"],
                non_claims=["does not copy some mission fields"],
            )
            payload["copied_bools"] = payload["copied_bools"][:-1]
            payload["redacted_mission_fields"] = payload["redacted_mission_fields"][:-1]
            payload["coverage"]["copied_fields"] = payload["coverage"]["copied_fields"][:-1]
            payload["coverage"]["redacted_fields"] = payload["coverage"]["redacted_fields"][:-1]
            payload["coverage"]["input_targets"] = ["MissionType.AddPlayerToMission"]
            payload["coverage"]["copied_targets"] = ["MissionType.AddPlayerToMission"]
            payload["safety_summary"]["explicitly_excluded"] = ["mutation"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("mission_copied_bool_policy_status_not_evidence_only", reasons)
        self.assertIn("mission_copied_bool_policy_missing_targets_present", reasons)
        self.assertIn("mission_copied_bool_policy_promotion_ready_not_false", reasons)
        self.assertIn("mission_copied_bool_policy_copied_bool_count_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_redacted_field_count_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_copied_bools_count_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_redacted_fields_count_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_coverage_input_targets_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_coverage_copied_targets_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_coverage_copied_fields_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_coverage_redacted_fields_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_non_claims_missing_required_boundaries", reasons)
        self.assertIn("mission_copied_bool_policy_explicit_exclusions_missing_internal_boundaries", reasons)

    def test_blocks_mission_copied_bool_policy_slice_with_tampered_shape_or_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "mission-copied-bool-policy.json"
            payload = mission_copied_bool_policy_slice_manifest()
            payload["copied_bools"][0]["property_flags"] = "0x80"
            payload["copied_bools"][0]["bool_byte_offset"] = 1
            payload["copied_bools"][0]["source_snapshot_sha256"] = "7" * 64
            payload["redacted_mission_fields"][0]["offset"] = "0x40"
            payload["redacted_mission_fields"][1]["source_snapshot"] = payload["copied_bools"][0]["source_snapshot"]
            payload["redacted_mission_fields"][1]["source_snapshot_sha256"] = next(
                snapshot["sha256"]
                for snapshot in payload["generated_from"]["input_snapshots"]
                if snapshot["id"] == payload["copied_bools"][0]["source_snapshot"]
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("mission_copied_bool_policy_copied_bool_shape_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_copied_bool_source_snapshot_sha256_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_redacted_field_shape_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_redacted_field_source_snapshot_target_mismatch", reasons)

    def test_blocks_mission_copied_bool_policy_slice_public_runtime_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "mission-copied-bool-policy.json"
            payload = mission_copied_bool_policy_slice_manifest()
            payload["runtime_ready"] = True
            payload["public_mission_sdk_ready"] = True
            payload["claim"] = "public Mission SDK ready"
            payload["runtime_claim"] = "runtime ready"
            payload["input_target_set"] = "mission-public-sdk-intake"
            payload["generated_from"]["input_snapshots"] = payload["generated_from"]["input_snapshots"][:2]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("mission_copied_bool_policy_readiness_overclaim", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_public_sdk", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_runtime_ready", reasons)
        self.assertIn("mission_copied_bool_policy_input_target_set_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_input_snapshot_count_mismatch", reasons)

    def test_accepts_structure_return_only_policy_slice_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-return-policy.json"
            write_json(manifest, structure_return_only_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_structure_return_only_policy_slice_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-return-policy.json"
            write_json(manifest, structure_return_only_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_structure_return_policy_slice_evidence_only", reasons)

    def test_blocks_structure_return_only_policy_slice_with_bad_counts_or_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-return-policy.json"
            payload = structure_return_only_policy_slice_manifest(
                policy_status="accepted",
                promotion_ready=True,
                copied_bool_count=1,
                redacted_field_count=1,
                deferred_target_count=3,
                missing_targets=["PrimalStructureItemContainer.VerifyPinCode"],
                non_claims=["does not copy ForPC"],
            )
            payload["copied_return_bools"] = payload["copied_return_bools"][:-1]
            payload["redacted_structure_fields"] = payload["redacted_structure_fields"][:-1]
            payload["deferred_structure_targets"] = payload["deferred_structure_targets"][:-1]
            payload["coverage"]["copied_fields"] = payload["coverage"]["copied_fields"][:-1]
            payload["coverage"]["redacted_fields"] = payload["coverage"]["redacted_fields"][:-1]
            payload["coverage"]["deferred_targets"] = payload["coverage"]["deferred_targets"][:-1]
            payload["coverage"]["input_targets"] = ["PrimalStructure.AllowStructureAccess"]
            payload["coverage"]["copied_targets"] = ["PrimalStructure.AllowStructureAccess"]
            payload["safety_summary"]["explicitly_excluded"] = ["ForPC"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_return_policy_status_not_evidence_only", reasons)
        self.assertIn("structure_return_policy_missing_targets_present", reasons)
        self.assertIn("structure_return_policy_promotion_ready_not_false", reasons)
        self.assertIn("structure_return_policy_copied_bool_count_mismatch", reasons)
        self.assertIn("structure_return_policy_redacted_field_count_mismatch", reasons)
        self.assertIn("structure_return_policy_deferred_target_count_mismatch", reasons)
        self.assertIn("structure_return_policy_copied_return_bools_count_mismatch", reasons)
        self.assertIn("structure_return_policy_redacted_fields_count_mismatch", reasons)
        self.assertIn("structure_return_policy_deferred_targets_count_mismatch", reasons)
        self.assertIn("structure_return_policy_coverage_input_targets_mismatch", reasons)
        self.assertIn("structure_return_policy_coverage_copied_targets_mismatch", reasons)
        self.assertIn("structure_return_policy_coverage_copied_fields_mismatch", reasons)
        self.assertIn("structure_return_policy_coverage_redacted_fields_mismatch", reasons)
        self.assertIn("structure_return_policy_coverage_deferred_targets_mismatch", reasons)
        self.assertIn("structure_return_policy_non_claims_missing_required_boundaries", reasons)
        self.assertIn("structure_return_policy_explicit_exclusions_missing_internal_boundaries", reasons)

    def test_blocks_structure_return_only_policy_slice_with_tampered_shape_or_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-return-policy.json"
            payload = structure_return_only_policy_slice_manifest()
            payload["copied_return_bools"][0]["property_flags"] = "0x80"
            payload["copied_return_bools"][0]["bool_byte_offset"] = 1
            payload["copied_return_bools"][0]["source_snapshot_sha256"] = "7" * 64
            payload["redacted_structure_fields"][0]["offset"] = "0x40"
            payload["deferred_structure_targets"][0]["property_count"] = 99
            payload["deferred_structure_targets"][1]["source_snapshot"] = payload["copied_return_bools"][0]["source_snapshot"]
            payload["deferred_structure_targets"][1]["source_snapshot_sha256"] = next(
                snapshot["sha256"]
                for snapshot in payload["generated_from"]["input_snapshots"]
                if snapshot["id"] == payload["copied_return_bools"][0]["source_snapshot"]
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_return_policy_copied_bool_shape_mismatch", reasons)
        self.assertIn("structure_return_policy_copied_bool_source_snapshot_sha256_mismatch", reasons)
        self.assertIn("structure_return_policy_redacted_field_shape_mismatch", reasons)
        self.assertIn("structure_return_policy_deferred_target_shape_mismatch", reasons)
        self.assertIn("structure_return_policy_deferred_target_source_snapshot_target_mismatch", reasons)

    def test_blocks_structure_return_only_policy_slice_public_runtime_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-return-policy.json"
            payload = structure_return_only_policy_slice_manifest()
            payload["runtime_ready"] = True
            payload["public_structure_events_ready"] = True
            payload["claim"] = "public SDK ready"
            payload["structure_claim"] = "public StructureEvents ready"
            payload["runtime_claim"] = "runtime ready"
            payload["input_target_set"] = "structure-public-events-intake"
            payload["generated_from"]["input_snapshots"] = payload["generated_from"]["input_snapshots"][:2]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_return_policy_readiness_overclaim", reasons)
        self.assertIn("structure_return_policy_public_overclaim_public_sdk", reasons)
        self.assertIn("structure_return_policy_public_overclaim_public_structure_events", reasons)
        self.assertIn("structure_return_policy_public_overclaim_runtime_ready", reasons)
        self.assertIn("structure_return_policy_input_target_set_mismatch", reasons)
        self.assertIn("structure_return_policy_input_snapshot_count_mismatch", reasons)

    def test_accepts_structure_nonpin_copied_scalar_policy_slice_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-nonpin-policy.json"
            write_json(manifest, structure_nonpin_copied_scalar_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_structure_nonpin_copied_scalar_policy_slice_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-nonpin-policy.json"
            write_json(manifest, structure_nonpin_copied_scalar_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_structure_nonpin_copied_scalar_policy_slice_evidence_only", reasons)

    def test_blocks_structure_nonpin_copied_scalar_policy_slice_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-nonpin-policy.json"
            payload = structure_nonpin_copied_scalar_policy_slice_manifest(
                policy_status="accepted",
                promotion_ready=True,
                copied_scalar_count=5,
                redacted_field_count=2,
                missing_targets=["PrimalStructureItemContainer.VerifyPinCode"],
                non_claims=["does not copy ForPC"],
            )
            payload["copied_scalars"][0]["offset"] = "0x4"
            payload["copied_scalars"][1]["byte_mask"] = "0x02"
            payload["copied_scalars"][1]["source_snapshot_sha256"] = "7" * 64
            payload["copied_scalars"] = payload["copied_scalars"][:-1]
            payload["redacted_structure_fields"] = payload["redacted_structure_fields"][:-1]
            payload["coverage"]["copied_fields"] = payload["coverage"]["copied_fields"][:-1]
            payload["coverage"]["redacted_fields"] = payload["coverage"]["redacted_fields"][:-1]
            payload["coverage"]["input_targets"] = ["PrimalStructure.SetVariant"]
            payload["coverage"]["copied_targets"] = ["PrimalStructure.SetVariant"]
            payload["safety_summary"]["explicitly_excluded"] = ["ForPC"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_nonpin_policy_status_not_evidence_only", reasons)
        self.assertIn("structure_nonpin_policy_missing_targets_present", reasons)
        self.assertIn("structure_nonpin_policy_promotion_ready_not_false", reasons)
        self.assertIn("structure_nonpin_policy_copied_scalar_count_mismatch", reasons)
        self.assertIn("structure_nonpin_policy_redacted_field_count_mismatch", reasons)
        self.assertIn("structure_nonpin_policy_copied_scalars_count_mismatch", reasons)
        self.assertIn("structure_nonpin_policy_redacted_fields_count_mismatch", reasons)
        self.assertIn("structure_nonpin_policy_coverage_input_targets_mismatch", reasons)
        self.assertIn("structure_nonpin_policy_coverage_copied_targets_mismatch", reasons)
        self.assertIn("structure_nonpin_policy_coverage_copied_fields_mismatch", reasons)
        self.assertIn("structure_nonpin_policy_coverage_redacted_fields_mismatch", reasons)
        self.assertIn("structure_nonpin_policy_non_claims_missing_required_boundaries", reasons)
        self.assertIn("structure_nonpin_policy_explicit_exclusions_missing_internal_boundaries", reasons)

    def test_blocks_structure_nonpin_copied_scalar_policy_slice_verify_pin_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-nonpin-policy.json"
            payload = structure_nonpin_copied_scalar_policy_slice_manifest()
            payload["coverage"]["input_targets"].append("PrimalStructureItemContainer.VerifyPinCode")
            payload["runtime_ready"] = True
            payload["claim"] = "public StructureEvents ready"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_nonpin_policy_contains_verify_pin_code_payload", reasons)
        self.assertIn("structure_nonpin_policy_readiness_overclaim", reasons)
        self.assertIn("structure_nonpin_policy_public_overclaim_public_structure_events", reasons)

    def test_accepts_static_global_promotion_evidence_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "static-global.json"
            write_json(manifest, static_global_promotion_evidence_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_static_global_promotion_evidence_with_skeletal_consume_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "static-global.json"
            write_json(
                manifest,
                {
                    "schema": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
                    "promotion_gate": {
                        "ready": False,
                        "blockers": ["static_only_evidence"],
                    },
                    "remaining_blockers": ["static_only_evidence"],
                    "non_claims": ["static_only_evidence"],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("static_global_missing_binary_sha256", reasons)
        self.assertIn("static_global_missing_commands", reasons)
        self.assertIn("static_global_missing_artifacts", reasons)
        self.assertIn("static_global_missing_candidates", reasons)

    def test_blocks_static_global_gobjects_without_field_window_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "static-global.json"
            payload = static_global_promotion_evidence_manifest()
            payload["candidates"][0]["static_contract"]["blockers"] = ["missing_rip_relative_xref"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("static_global_gobjects_missing_field_window_status", reasons)

    def test_blocks_static_global_promotion_evidence_missing_or_bad_identity(self) -> None:
        cases = {
            "missing": (None, "static_global_missing_artifact_identity"),
            "partial": ({"artifact_kind": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA}, "static_global_artifact_identity_fields_mismatch"),
            "bad_capture": (
                {
                    "artifact_kind": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
                    "artifact_sha256": "a" * 64,
                    "capture_id": "../bad",
                    "evidence_pack_id": "static-global-test-pack",
                },
                "static_global_artifact_identity_capture_id_invalid",
            ),
            "bad_hash": (
                {
                    "artifact_kind": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
                    "artifact_sha256": "not-a-sha",
                    "capture_id": "static-global-test-capture",
                    "evidence_pack_id": "static-global-test-pack",
                },
                "static_global_artifact_identity_sha_invalid",
            ),
            "placeholder_capture": (
                {
                    "artifact_kind": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
                    "artifact_sha256": "a" * 64,
                    "capture_id": "unspecified-capture",
                    "evidence_pack_id": "static-global-test-pack",
                },
                "static_global_artifact_identity_capture_id_invalid",
            ),
            "placeholder_pack": (
                {
                    "artifact_kind": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
                    "artifact_sha256": "a" * 64,
                    "capture_id": "static-global-test-capture",
                    "evidence_pack_id": "unspecified-evidence-pack",
                },
                "static_global_artifact_identity_evidence_pack_id_invalid",
            ),
            "default_capture": (
                {
                    "artifact_kind": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
                    "artifact_sha256": "a" * 64,
                    "capture_id": "static-global-default-capture",
                    "evidence_pack_id": "static-global-test-pack",
                },
                "static_global_artifact_identity_capture_id_invalid",
            ),
            "default_pack": (
                {
                    "artifact_kind": gate.STATIC_GLOBAL_PROMOTION_EVIDENCE_SCHEMA,
                    "artifact_sha256": "a" * 64,
                    "capture_id": "static-global-test-capture",
                    "evidence_pack_id": "static-global-default-pack",
                },
                "static_global_artifact_identity_evidence_pack_id_invalid",
            ),
        }
        for name, (identity, expected_reason) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                protected = Path(tmp) / "server"
                workspace = protected / "workspace-offline"
                manifest = workspace / "static-global.json"
                payload = static_global_promotion_evidence_manifest()
                if identity is None:
                    payload.pop("artifact_identity")
                else:
                    payload["artifact_identity"] = identity
                write_json(manifest, payload)

                result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

                reasons = {blocker["reason"] for blocker in result["blockers"]}
                self.assertIn(expected_reason, reasons)

    def test_blocks_static_global_promotion_evidence_identity_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "static-global.json"
            payload = static_global_promotion_evidence_manifest()
            payload["candidates"][0]["address"] = "0x595b7f0"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("static_global_artifact_identity_hash_mismatch", reasons)

    def test_static_global_identity_ignores_paths_and_timestamps(self) -> None:
        payload_a = static_global_promotion_evidence_manifest()
        payload_b = static_global_promotion_evidence_manifest()
        payload_b["generated_at_utc"] = "2099-01-01T00:00:00Z"
        payload_b["binary"] = {**payload_b["binary"], "path": "/tmp/other/ShooterGameServer"}
        payload_b["commands"]["objdump"]["output_provenance"] = "/tmp/other/objdump.provenance.json"
        payload_b["artifacts"]["static_xrefs"] = "/tmp/other/static-global-xrefs.json"

        self.assertEqual(
            gate.static_global_artifact_identity(
                payload_a,
                capture_id=payload_a["artifact_identity"]["capture_id"],
                evidence_pack_id=payload_a["artifact_identity"]["evidence_pack_id"],
            ),
            gate.static_global_artifact_identity(
                payload_b,
                capture_id=payload_b["artifact_identity"]["capture_id"],
                evidence_pack_id=payload_b["artifact_identity"]["evidence_pack_id"],
            ),
        )

    def test_blocks_static_global_promotion_evidence_in_promote_mode_when_static_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "static-global.json"
            write_json(manifest, static_global_promotion_evidence_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_static_global_promotion_gate_not_ready", reasons)
        self.assertIn("promote_mode_static_global_has_blockers", reasons)
        self.assertIn("promote_mode_static_global_has_remaining_blockers", reasons)
        self.assertIn("promote_mode_static_global_static_only_evidence", reasons)

    def test_accepts_resource_handle_revalidation_evaluator_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle.json"
            write_json(manifest, resource_handle_revalidation_evaluator_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_resource_handle_revalidation_evaluator_in_promote_mode_when_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle.json"
            write_json(manifest, resource_handle_revalidation_evaluator_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_resource_handle_post_callback_not_ready", reasons)
        self.assertIn("promote_mode_resource_handle_flag_semantics_unproven", reasons)
        self.assertIn("promote_mode_resource_handle_manifest_has_blockers", reasons)
        self.assertIn("promote_mode_resource_handle_promotion_gate_not_ready", reasons)
        self.assertIn("promote_mode_resource_handle_promotion_gate_has_blockers", reasons)

    def test_blocks_resource_handle_revalidation_placeholder_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle.json"
            payload = resource_handle_revalidation_evaluator_manifest()
            payload["artifact_identity"]["hashes"].append("unspecified-input")
            payload["artifact_identity"]["hash_count"] = 3
            payload["artifact_identity"]["invalid_input_count"] = 1
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_revalidation_artifact_identity_placeholder_id", reasons)
        self.assertIn("resource_handle_revalidation_artifact_identity_invalid_inputs", reasons)

    def test_accepts_internal_uobject_post_callback_contract_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "post-callback-contract.json"
            write_json(manifest, internal_uobject_post_callback_contract_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_internal_uobject_post_callback_contract_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "post-callback-contract.json"
            write_json(manifest, internal_uobject_post_callback_contract_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_post_callback_contract_candidate_only", reasons)

    def test_blocks_internal_uobject_post_callback_contract_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "post-callback-contract.json"
            payload = internal_uobject_post_callback_contract_manifest(overclaim=True)
            payload["contract_checks"]["post_callback_lookup_rejected"] = False
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("post_callback_contract_post_callback_resourcehandle_overclaim", reasons)
        self.assertIn("post_callback_contract_post_callback_lookup_mismatch", reasons)
        self.assertIn("post_callback_contract_check_post_callback_lookup_rejected_mismatch", reasons)

    def test_blocks_internal_uobject_post_callback_contract_identity_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "post-callback-contract.json"
            payload = internal_uobject_post_callback_contract_manifest()
            payload["output_artifact_identity"]["artifact_sha256"] = "0" * 64
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("post_callback_contract_output_artifact_identity_hash_mismatch", reasons)

    def test_accepts_internal_uobject_serial_policy_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "serial-policy.json"
            write_json(manifest, internal_uobject_serial_policy_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_internal_uobject_serial_policy_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "serial-policy.json"
            write_json(manifest, internal_uobject_serial_policy_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_serial_policy_candidate_only", reasons)

    def test_blocks_internal_uobject_serial_policy_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "serial-policy.json"
            payload = internal_uobject_serial_policy_manifest()
            payload["public_resource_handle_ready"] = True
            payload["serial_policy"]["fail_closed_rules"]["public_lookup_request"] = "allow"
            payload["contract_checks"]["serial_reuse_or_wraparound_safety_proven"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("serial_policy_public_resourcehandle_overclaim", reasons)
        self.assertIn("serial_policy_fail_closed_public_lookup_request_not_reject", reasons)
        self.assertIn("serial_policy_check_serial_reuse_or_wraparound_safety_proven_mismatch", reasons)

    def test_blocks_internal_uobject_serial_policy_identity_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "serial-policy.json"
            payload = internal_uobject_serial_policy_manifest()
            payload["output_artifact_identity"]["artifact_sha256"] = "0" * 64
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("serial_policy_output_artifact_identity_hash_mismatch", reasons)

    def test_accepts_runtime_rejection_samples_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            write_json(manifest, runtime_rejection_samples_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_runtime_rejection_samples_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            write_json(manifest, runtime_rejection_samples_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_runtime_rejection_samples_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_runtime_rejection_samples_raw_disclosures_and_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            payload = runtime_rejection_samples_manifest()
            payload["public_resource_handle_ready"] = True
            payload["privacy"]["raw_ue_pointers"] = True
            payload["redacted_run_identity"]["broad_tracing"] = True
            payload["rows"][0]["uobject_pointer"] = "0x12345678"
            payload["summary"]["operator_note"] = "/servidor/ark/live-capture"
            payload["summary"]["serial_value"] = 17
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("runtime_rejection_samples_public_resourcehandle_overclaim", reasons)
        self.assertIn("runtime_rejection_samples_privacy_raw_ue_pointers_not_false", reasons)
        self.assertIn("runtime_rejection_samples_run_identity_broad_tracing_not_false", reasons)
        self.assertIn("runtime_rejection_samples_row_unexpected_field", reasons)
        self.assertIn("runtime_rejection_samples_forbidden_disclosure_field", reasons)
        self.assertIn("runtime_rejection_samples_raw_address_string", reasons)
        self.assertIn("runtime_rejection_samples_protected_path_string", reasons)

    def test_accepts_runtime_serial_semantics_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-serial-semantics.json"
            write_json(manifest, runtime_serial_semantics_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_runtime_serial_semantics_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-serial-semantics.json"
            write_json(manifest, runtime_serial_semantics_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_runtime_serial_semantics_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_runtime_serial_semantics_cross_frame_and_serial_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-serial-semantics.json"
            payload = runtime_serial_semantics_manifest()
            payload["post_callback_resource_handle_ready"] = True
            payload["serial_semantics"]["unknown_wraparound_reject"] = False
            payload["serial_semantics"]["cross_frame_lookup"] = "allow"
            payload["serial_semantics"]["fuobjectitem_dword_0xC"] = "serial"
            payload["rows"][0]["same_frame"] = False
            payload["rows"][0]["decision"] = "allow_cross_frame"
            payload["rows"][0]["serial_value"] = 17
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("runtime_serial_semantics_post_callback_resourcehandle_overclaim", reasons)
        self.assertIn("runtime_serial_semantics_unknown_wraparound_not_reject", reasons)
        self.assertIn("runtime_serial_semantics_cross_frame_not_reject", reasons)
        self.assertIn("runtime_serial_semantics_fuobjectitem_0xC_not_unknown", reasons)
        self.assertIn("runtime_serial_semantics_row_unexpected_field", reasons)
        self.assertIn("runtime_serial_semantics_forbidden_disclosure_field", reasons)
        self.assertIn("runtime_serial_semantics_fresh_case_not_frame_local_only", reasons)

    def test_accepts_resource_handle_serial_scan_with_rejection_candidate_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest_with_core(workspace))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_resource_handle_serial_scan_missing_candidate_status_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload.pop("status")
            payload.pop("evidence_kind")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_serial_scan_status_overclaim", reasons)
        self.assertIn("resource_handle_serial_scan_evidence_kind_overclaim", reasons)

    def test_blocks_resource_handle_serial_scan_missing_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload.pop("provenance")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_provenance_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_bad_provenance_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["provenance"].update(
                {
                    "schema": "wrong.schema",
                    "producer": "other.py",
                    "tool_path": "scripts/other.py",
                    "verified": False,
                    "path_redacted": False,
                    "argv": "not-a-list",
                    "core_sha256_verified": False,
                    "core_sha256": "c" * 64,
                    "binary_sha256": "d" * 64,
                    "gobjects": "0x1",
                    "fname_root_slot": "0x2",
                    "scan_limit": 7,
                }
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_serial_scan_provenance_schema_mismatch", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_not_verified", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_path_not_redacted", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_producer_mismatch", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_tool_path_mismatch", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_argv_invalid", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_core_sha256_not_verified", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_core_sha256_mismatch", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_binary_sha256_mismatch", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_address_mismatch", reasons)
        self.assertIn("resource_handle_serial_scan_provenance_scan_limit_mismatch", reasons)

    def test_blocks_resource_handle_serial_scan_missing_consume_gate_expectation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload.pop("consume_gate_expectation")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_consume_gate_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_bad_consume_gate_expectation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["consume_gate_expectation"] = {
                "schema": "wrong.schema",
                "consume_ready": False,
                "promote_ready": True,
                "blockers": ["still_blocked"],
                "non_claims": [],
            }
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_serial_scan_consume_gate_schema_mismatch", reasons)
        self.assertIn("resource_handle_serial_scan_consume_gate_not_ready", reasons)
        self.assertIn("resource_handle_serial_scan_consume_gate_promote_overclaim", reasons)
        self.assertIn("resource_handle_serial_scan_consume_gate_has_blockers", reasons)
        self.assertIn("resource_handle_serial_scan_consume_gate_non_claims_missing", reasons)

    def test_accepts_resource_handle_serial_scan_0x4000_allow_candidate_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest_with_core(workspace, candidate_flags=0x4000))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_accepts_resource_handle_serial_scan_in_temp_with_core_under_approved_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            approved_workspace = protected / "workspace-offline"
            report_root = Path(tmp) / "reports"
            report_root.mkdir()
            manifest = report_root / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(approved_workspace, candidate_flags=0x4000)
            write_json(manifest, payload)

            with mock.patch.object(gate, "DEFAULT_WORKSPACE_ROOT", approved_workspace):
                result = gate.build_result(args(root=report_root, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_accepts_resource_handle_serial_scan_0x8000_reject_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest_with_core(workspace, candidate_flags=0x8000))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_resource_handle_serial_scan_0x4000_reject_policy_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest(candidate_flags=0x4000)
            payload["flag_rejection_candidate_samples"][0]["policy_result_allow4000"] = "reject"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_candidate_allow4000_policy_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_public_handle_ready_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest()
            payload["interpretation"]["public_resource_handle_ready"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_public_handle_overclaim",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_ready_overclaims_anywhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest(core_path=str(workspace / "copied-core"))
            payload["resource_handle_ready"] = True
            payload["metadata"]["public_resource_handle_ready"] = True
            payload["interpretation"]["resource_handle_ready"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        labels = {blocker["label"] for blocker in result["blockers"] if blocker["reason"] == "resource_handle_serial_scan_ready_overclaim"}
        self.assertTrue(any(label.endswith("$.resource_handle_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.metadata.public_resource_handle_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.interpretation.resource_handle_ready") for label in labels))

    def test_blocks_resource_handle_serial_scan_missing_binary_sha256_when_expected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest()
            payload.pop("binary_sha256")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_binary_sha256_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_missing_binary_sha256_without_expected_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest(core_path=str(workspace / "copied-core"))
            payload.pop("binary_sha256")
            write_json(manifest, payload)

            result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[manifest], expected_binary_sha256=None)
            )

        self.assertIn(
            "resource_handle_serial_scan_binary_sha256_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_core_hash_self_assertion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            core = workspace / "copied-core"
            core.parent.mkdir(parents=True)
            core.write_bytes(b"different core bytes\n")
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(
                manifest,
                resource_handle_serial_scan_manifest(core_path=str(core), core_sha256="b" * 64),
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_core_sha256_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_unreadable_core_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest(core_path=str(workspace / "missing-core")))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_core_path_unreadable",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_core_path_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest(core_path=str(Path(tmp) / "copied-core")))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "path_not_textually_under_workspace_root",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_core_path_relative_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest(core_path="../obelisk/dumps/core"))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_core_path_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_core_path_symlink_to_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            outside = protected / "obelisk" / "dumps"
            outside.mkdir(parents=True)
            link = workspace / "core-link"
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(outside / "core")
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest(core_path=str(link)))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "path_not_resolved_under_workspace_root",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_totals_contradict_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest(core_path=str(workspace / "copied-core"))
            payload["totals"] = {
                "objects_read": 0,
                "serial_nonzero": 0,
                "membership_pass_count": 0,
                "flags_any": 0,
            }
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_total_contradicts_candidates",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_boolean_numeric_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest(core_path=str(workspace / "copied-core"))
            payload["totals"]["objects_read"] = True
            candidate = payload["flag_rejection_candidate_samples"][0]
            candidate["index"] = True
            candidate["serial"] = True
            candidate["flags"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_serial_scan_total_invalid", reasons)
        self.assertIn("resource_handle_serial_scan_candidate_index_invalid", reasons)
        self.assertIn("resource_handle_serial_scan_candidate_serial_invalid", reasons)
        self.assertIn("resource_handle_serial_scan_candidate_flags_invalid", reasons)

    def test_blocks_resource_handle_serial_scan_nested_ready_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["consume_gate_expectation"] = {"promote_ready": False}
            payload["consume_gate_expectation"]["promote_ready"] = True
            payload["metadata"]["promotion_ready"] = True
            payload["metadata"]["runtime_ready"] = True
            payload["interpretation"]["lookup_ready"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        labels = {blocker["label"] for blocker in result["blockers"] if blocker["reason"] == "resource_handle_serial_scan_ready_overclaim"}
        self.assertTrue(any(label.endswith("$.consume_gate_expectation.promote_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.metadata.promotion_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.metadata.runtime_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.interpretation.lookup_ready") for label in labels))

    def test_blocks_resource_handle_serial_scan_promoted_status_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["status"] = "promoted"
            payload["evidence_kind"] = "public_resource_handle_evidence"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_serial_scan_status_overclaim", reasons)
        self.assertIn("resource_handle_serial_scan_evidence_kind_overclaim", reasons)

    def test_blocks_resource_handle_serial_scan_hidden_protected_path_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["metadata"]["live_input"] = "/servidor/ark/obelisk/dumps/core"
            payload["interpretation"]["note"] = "../obelisk/dumps/core"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_protected_path_string",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_impossible_totals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["totals"] = {
                "objects_read": 1,
                "serial_nonzero": 2,
                "membership_pass_count": 2,
                "flags_any": 2,
            }
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_total_impossible",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_missing_scan_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload.pop("scan_limit")
            payload["provenance"].pop("scan_limit")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_scan_limit_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_objects_read_exceeds_scan_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["scan_limit"] = 1
            payload["provenance"]["scan_limit"] = 1
            payload["totals"]["objects_read"] = 2
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_objects_read_exceeds_scan_limit",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_sample_index_outside_scan_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["flag_rejection_candidate_samples"][0]["index"] = payload["scan_limit"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_candidate_index_out_of_range",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_accepts_resource_handle_serial_scan_sparse_candidate_index_below_scan_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace, candidate_flags=0x4000)
            payload["totals"]["objects_read"] = 1
            payload["scan_limit"] = 1024
            payload["provenance"]["scan_limit"] = 1024
            payload["flag_rejection_candidate_samples"][0]["index"] = 1000
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_resource_handle_serial_scan_duplicate_candidate_indices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            payload["totals"]["objects_read"] = 2
            payload["flag_rejection_candidate_samples"].append(dict(payload["flag_rejection_candidate_samples"][0]))
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_candidate_index_duplicate",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_flags_outside_u32(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest_with_core(workspace)
            candidate = payload["flag_rejection_candidate_samples"][0]
            candidate["flags"] = 0x1_0000_0100
            candidate["has_0x100"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_candidate_flags_outside_u32",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_without_rejection_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest(include_candidate=False))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_serial_scan_missing_rejection_candidates",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_serial_scan_malformed_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest()
            candidate = payload["flag_rejection_candidate_samples"][0]
            candidate["serial"] = 0
            candidate["gobjects_membership_pass"] = False
            candidate["has_0x100"] = False
            candidate["policy_result_strict"] = "allow_candidate"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_serial_scan_candidate_serial_invalid", reasons)
        self.assertIn("resource_handle_serial_scan_candidate_membership_failed", reasons)
        self.assertIn("resource_handle_serial_scan_candidate_mask_mismatch", reasons)
        self.assertIn("resource_handle_serial_scan_candidate_strict_policy_not_reject", reasons)

    def test_blocks_resource_handle_serial_scan_binary_sha256_mismatch_without_confusing_core_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            payload = resource_handle_serial_scan_manifest()
            payload["binary_sha256"] = "c" * 64
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_serial_scan_binary_sha256_mismatch", reasons)
        self.assertNotIn("resource_handle_serial_scan_core_sha256_mismatch", reasons)

    def test_blocks_resource_handle_serial_scan_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_resource_handle_serial_scan_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_accepts_uobject_flag_policy_candidate_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            write_json(manifest, uobject_flag_policy_report_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_uobject_flag_policy_missing_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            write_json(manifest, uobject_flag_policy_report_manifest(include_artifact_identity=False))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_missing_artifact_identity",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_invalid_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["artifact_identity"]["capture_id"] = "../bad"
            payload["artifact_identity"]["artifact_sha256"] = "ABC"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_artifact_identity_capture_id_invalid", reasons)
        self.assertIn("uobject_flag_policy_artifact_identity_sha_invalid", reasons)

    def test_blocks_uobject_flag_policy_partial_artifact_identity_fields_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["artifact_identity"].pop("evidence_pack_id")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_artifact_identity_fields_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_artifact_identity_kind_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["artifact_identity"]["artifact_kind"] = gate.UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_artifact_identity_kind_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_artifact_identity_evidence_pack_id_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["artifact_identity"]["evidence_pack_id"] = "../bad"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_artifact_identity_evidence_pack_id_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_placeholder_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["artifact_identity"]["capture_id"] = "unspecified-capture"
            payload["artifact_identity"]["evidence_pack_id"] = "unspecified-evidence-pack"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_artifact_identity_capture_id_invalid", reasons)
        self.assertIn("uobject_flag_policy_artifact_identity_evidence_pack_id_invalid", reasons)

    def test_blocks_uobject_flag_policy_artifact_identity_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["artifact_identity"]["artifact_sha256"] = "0" * 64
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_artifact_identity_hash_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_legacy_redacted_caller_mode_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            write_json(manifest, uobject_flag_policy_report_manifest_with_legacy_caller_mode())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_legacy_caller_mode_not_consume_ready", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_summary_missing", reasons)

    def test_blocks_uobject_flag_policy_candidate_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            write_json(manifest, uobject_flag_policy_report_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_uobject_flag_policy_candidate_only", reasons)

    def test_blocks_uobject_flag_policy_overclaims_and_missing_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest(promotion_ready=True)
            payload["post_callback_resource_handle_ready"] = True
            payload["windows_summary"]["observed"] = payload["windows_summary"]["observed"][:-1]
            payload["remaining_blockers"] = []
            payload["non_claims"] = []
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_promotion_ready_overclaim", reasons)
        self.assertIn("uobject_flag_policy_post_callback_resourcehandle_overclaim", reasons)
        self.assertIn("uobject_flag_policy_required_windows_mismatch", reasons)
        self.assertIn("uobject_flag_policy_remaining_blockers_missing", reasons)
        self.assertIn("uobject_flag_policy_non_claims_missing", reasons)

    def test_blocks_uobject_flag_policy_incomplete_matched_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["windows_summary"]["observed"][0]["matched_patterns"] = ["gobjects_count_ref"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_window_required_patterns_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_extra_matched_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["windows_summary"]["observed"][0]["matched_patterns"].append("legacy_static_negative_marker")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        blockers = result["blockers"]
        self.assertIn(
            "uobject_flag_policy_window_required_patterns_mismatch",
            {blocker["reason"] for blocker in blockers},
        )
        pattern_blocker = next(
            blocker for blocker in blockers if blocker["reason"] == "uobject_flag_policy_window_required_patterns_mismatch"
        )
        self.assertIn("legacy_static_negative_marker", pattern_blocker.get("unexpected", []))

    def test_blocks_uobject_flag_policy_non_candidate_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["status"] = "accepted"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_status_not_candidate_blocked",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_resourcehandle_ready_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["resource_handle_ready"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_readiness_overclaim",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_missing_weak_helper_caller_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            del payload["weak_helper_caller_mode"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_missing_weak_helper_caller_mode",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_public_identifier_leaks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["weak_helper_caller_mode"]["caller_rows_summary"]["helper"] = "0x1d56c70"
            payload["weak_helper_caller_mode"]["direct_call_coverage"] = {"0x1d56c70": {"expected": 6, "observed": 6}}
            payload["policy_candidates"][0]["source_index"] = 7
            payload["policy_candidates"][1]["support"].append("raw_pointer_window")
            payload["note"] = "serial evidence remains private"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_public_address_string_leak", reasons)
        self.assertIn("uobject_flag_policy_public_identifier_key_leak", reasons)
        self.assertIn("uobject_flag_policy_public_identifier_string_leak", reasons)
        self.assertIn("uobject_flag_policy_direct_call_coverage_mismatch", reasons)

    def test_blocks_uobject_flag_policy_missing_candidate_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            del payload["policy_candidates"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_candidates_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_relaxed_internal_revalidation_contract(self) -> None:
        mutations = {
            "name": lambda contract: contract.__setitem__("name", "ResourceHandleCandidate"),
            "lifetime": lambda contract: contract.__setitem__("lifetime", "post_callback"),
            "post_callback_lookup": lambda contract: contract.__setitem__("post_callback_lookup", "allowed"),
            "flag_0x100": lambda contract: contract["flag_policy"].__setitem__("0x100", "allow"),
            "flag_0x4000": lambda contract: contract["flag_policy"].__setitem__("0x4000", "allow_by_default"),
            "output": lambda contract: contract.__setitem__("output", "resourcehandle_lookup"),
            "public_api": lambda contract: contract.__setitem__("public_api", "promoted"),
            "extra_key": lambda contract: contract.__setitem__("lookup", "ready"),
        }

        for case, mutate in mutations.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                protected = Path(tmp) / "server"
                workspace = protected / "workspace-offline"
                manifest = workspace / "uobject-flags.json"
                payload = uobject_flag_policy_report_manifest()
                mutate(payload["internal_revalidation_contract"])
                write_json(manifest, payload)

                result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

            self.assertIn(
                "uobject_flag_policy_internal_revalidation_contract_mismatch",
                {blocker["reason"] for blocker in result["blockers"]},
            )

    def test_blocks_uobject_flag_policy_missing_internal_revalidation_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            del payload["internal_revalidation_contract"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_internal_revalidation_contract_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_weak_helper_contract_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["weak_helper_caller_mode"]["promotion_gate_ready"] = True
            payload["weak_helper_caller_mode"]["flag_rules"][0]["result"] = "allow"
            payload["weak_helper_caller_mode"]["schema"] = "obsolete"
            payload["weak_helper_caller_mode"]["public_api"] = "ResourceHandle lookup ready"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_weak_helper_promotion_gate_overclaim", reasons)
        self.assertIn("uobject_flag_policy_weak_helper_flag_rules_mismatch", reasons)
        self.assertIn("uobject_flag_policy_weak_helper_schema_mismatch", reasons)
        self.assertIn("uobject_flag_policy_weak_helper_unexpected_fields", reasons)

    def test_blocks_uobject_flag_policy_payload_public_overclaims_in_extra_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["policy_candidates"][0]["public_api"] = "ResourceHandle lookup ready"
            payload["remaining_blockers"].append("ResourceHandle runtime promotion")
            payload["non_claims"].append("ResourceHandle lookup ready")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_candidate_unexpected_fields", reasons)
        self.assertIn("uobject_flag_policy_candidate_public_overclaim_resourcehandle", reasons)
        self.assertIn("uobject_flag_policy_remaining_blockers_public_overclaim_resourcehandle", reasons)
        self.assertIn("uobject_flag_policy_non_claims_public_overclaim_resourcehandle", reasons)

    def test_blocks_uobject_flag_policy_bad_caller_rows_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            summary = payload["weak_helper_caller_mode"]["caller_rows_summary"]
            source = payload["weak_helper_caller_mode"]["caller_rows_source"]
            summary["row_count"] = 5
            summary["return_use"] = {"register": "rax", "nonzero_path": "ResourceHandle lookup ready"}
            summary["lifecycle_names"] = "pending-kill"
            summary["source_path"] = "/tmp/raw-ghidra.txt"
            source["source_artifact_sha256"] = "0" * 64
            source["caller_rows_sha256"] = "1" * 64
            source["binary_sha256"] = "2" * 64
            source["artifact_path"] = "/tmp/weak-helper.json"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_caller_rows_summary_unexpected_fields", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_summary_row_count_mismatch", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_summary_return_use_mismatch", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_summary_lifecycle_names_mismatch", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_summary_public_overclaim_resourcehandle", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_summary_public_overclaim_lookup_ready", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_source_unexpected_fields", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_source_artifact_mismatch", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_source_binary_mismatch", reasons)
        self.assertIn("uobject_flag_policy_caller_rows_source_digest_mismatch", reasons)
        self.assertIn("uobject_flag_policy_ue_lifecycle_name_overclaim", reasons)

    def test_blocks_uobject_flag_policy_duplicate_observed_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["windows_summary"]["observed"].append(payload["windows_summary"]["observed"][0])
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_observed_window_count_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_missing_window_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            payload["windows_summary"]["observed"][0].pop("provenance")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_policy_window_provenance_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_policy_incomplete_provenance_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flags.json"
            payload = uobject_flag_policy_report_manifest()
            provenance = payload["windows_summary"]["observed"][0]["provenance"]
            provenance["schema"] = "wrong.schema"
            provenance["artifact_sha256"] = "e" * 64
            provenance["binary_sha256"] = "f" * 64
            provenance["sidecar_sha256"] = "not-a-sha"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_policy_window_provenance_schema_mismatch", reasons)
        self.assertIn("uobject_flag_policy_window_provenance_artifact_sha256_mismatch", reasons)
        self.assertIn("uobject_flag_policy_window_provenance_binary_sha256_mismatch", reasons)
        self.assertIn("uobject_flag_policy_window_provenance_sidecar_sha256_invalid", reasons)

    def test_accepts_uobject_flag_transition_matrix_candidate_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            write_json(manifest, uobject_flag_transition_matrix_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_accepts_uobject_flag_transition_matrix_with_optional_clear_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            payload = uobject_flag_transition_matrix_manifest()
            optional_window = {
                "name": "uobject_100_clear_1d637c8_1d63888",
                "artifact_sha256": "e" * 64,
                "byte_count": 128,
                "matched_patterns": sorted(
                    gate.REQUIRED_UOBJECT_FLAG_TRANSITION_WINDOW_PATTERNS[
                        "uobject_100_clear_1d637c8_1d63888"
                    ]
                ),
                "path_redacted": True,
                "provenance": {
                    "schema": "obelisk.offline-artifact-provenance.v1",
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": "e" * 64,
                    "sidecar_sha256": "f" * 64,
                    "verified": True,
                    "path_redacted": True,
                },
            }
            payload["windows_summary"]["observed"].append(optional_window)
            payload["windows_summary"]["groups"]["mutation_windows"].append("uobject_100_clear_1d637c8_1d63888")
            payload["transition_matrix"]["0x100"]["mutation_windows"].append("uobject_100_clear_1d637c8_1d63888")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_uobject_flag_transition_optional_window_reference_without_observed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            payload = uobject_flag_transition_matrix_manifest()
            payload["transition_matrix"]["0x100"]["mutation_windows"].append("uobject_100_clear_1d637c8_1d63888")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_transition_matrix_window_not_observed",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_transition_optional_window_with_incomplete_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            payload = uobject_flag_transition_matrix_manifest()
            optional_window = {
                "name": "uobject_100_clear_1d637c8_1d63888",
                "artifact_sha256": "e" * 64,
                "byte_count": 128,
                "matched_patterns": ["uobject_plus_0x8_operand"],
                "path_redacted": True,
                "provenance": {
                    "schema": "obelisk.offline-artifact-provenance.v1",
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": "e" * 64,
                    "sidecar_sha256": "f" * 64,
                    "verified": True,
                    "path_redacted": True,
                },
            }
            payload["windows_summary"]["observed"].append(optional_window)
            payload["windows_summary"]["groups"]["mutation_windows"].append("uobject_100_clear_1d637c8_1d63888")
            payload["transition_matrix"]["0x100"]["mutation_windows"].append("uobject_100_clear_1d637c8_1d63888")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_transition_window_required_patterns_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_transition_unknown_and_duplicate_observed_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            payload = uobject_flag_transition_matrix_manifest()
            payload["windows_summary"]["observed"].append(dict(payload["windows_summary"]["observed"][0]))
            unknown = dict(payload["windows_summary"]["observed"][0])
            unknown["name"] = "unknown_window"
            payload["windows_summary"]["observed"].append(unknown)
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_transition_observed_window_duplicate", reasons)
        self.assertIn("uobject_flag_transition_observed_window_unknown", reasons)

    def test_blocks_uobject_flag_transition_matrix_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            write_json(manifest, uobject_flag_transition_matrix_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_uobject_flag_transition_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_transition_overclaims_and_missing_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            payload = uobject_flag_transition_matrix_manifest(promotion_ready=True)
            payload["builder_contract"]["resource_handle_claim"] = True
            payload["windows_summary"]["observed"] = payload["windows_summary"]["observed"][:-1]
            payload["windows_summary"]["groups"]["mutation_windows"] = []
            payload["transition_matrix"]["0x8000"]["predicate_windows"] = ["gc_mark_100_8000_1d18a90_1d18c70"]
            payload["remaining_blockers"] = []
            payload["non_claims"] = []
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_transition_promotion_ready_overclaim", reasons)
        self.assertIn("uobject_flag_transition_resourcehandle_overclaim", reasons)
        self.assertIn("uobject_flag_transition_required_windows_mismatch", reasons)
        self.assertIn("uobject_flag_transition_window_group_empty", reasons)
        self.assertIn("uobject_flag_transition_8000_predicate_overclaim", reasons)
        self.assertIn("uobject_flag_transition_remaining_blockers_missing", reasons)
        self.assertIn("uobject_flag_transition_non_claims_missing", reasons)

    def test_blocks_uobject_flag_transition_lifecycle_name_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            payload = uobject_flag_transition_matrix_manifest()
            payload["transition_matrix"]["0x100"]["hypothesis"] = "pending-kill lifecycle name"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_transition_ue_lifecycle_name_overclaim",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_transition_incomplete_matched_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            payload = uobject_flag_transition_matrix_manifest()
            payload["windows_summary"]["observed"][0]["matched_patterns"] = ["uobject_plus_0x8_operand"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_transition_window_required_patterns_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_transition_incomplete_provenance_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-transition.json"
            payload = uobject_flag_transition_matrix_manifest()
            provenance = payload["windows_summary"]["observed"][0]["provenance"]
            provenance["schema"] = "wrong.schema"
            provenance["artifact_sha256"] = "e" * 64
            provenance["binary_sha256"] = "f" * 64
            provenance["sidecar_sha256"] = "not-a-sha"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_transition_window_provenance_schema_mismatch", reasons)
        self.assertIn("uobject_flag_transition_window_provenance_artifact_sha256_mismatch", reasons)
        self.assertIn("uobject_flag_transition_window_provenance_binary_sha256_mismatch", reasons)
        self.assertIn("uobject_flag_transition_window_provenance_sidecar_sha256_invalid", reasons)

    def test_accepts_uobject_flag_sample_report_candidate_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            write_json(manifest, uobject_flag_sample_report_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_uobject_flag_sample_missing_consume_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            payload = uobject_flag_sample_report_manifest()
            payload["source_artifacts"][0].pop("consume_gate")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_sample_source_consume_gate_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_sample_incomplete_consume_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            payload = uobject_flag_sample_report_manifest()
            consume_gate = payload["source_artifacts"][0]["consume_gate"]
            consume_gate["schema"] = "wrong.schema"
            consume_gate["status"] = "blocked"
            consume_gate["mode"] = "promote"
            consume_gate["blocker_count"] = 1
            consume_gate["gate_sha256"] = "not-a-sha"
            consume_gate["path_redacted"] = False
            consume_gate["artifact_sha256"] = "e" * 64
            consume_gate["binary_sha256"] = "f" * 64
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_sample_source_consume_gate_schema_mismatch", reasons)
        self.assertIn("uobject_flag_sample_source_consume_gate_status_not_accepted", reasons)
        self.assertIn("uobject_flag_sample_source_consume_gate_mode_not_consume", reasons)
        self.assertIn("uobject_flag_sample_source_consume_gate_has_blockers", reasons)
        self.assertIn("uobject_flag_sample_source_consume_gate_sha256_invalid", reasons)
        self.assertIn("uobject_flag_sample_source_consume_gate_path_not_redacted", reasons)
        self.assertIn("uobject_flag_sample_source_consume_gate_artifact_sha256_mismatch", reasons)
        self.assertIn("uobject_flag_sample_source_consume_gate_binary_sha256_mismatch", reasons)

    def test_blocks_uobject_flag_sample_report_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            write_json(manifest, uobject_flag_sample_report_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_uobject_flag_sample_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_sample_report_overclaims_and_missing_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            payload = uobject_flag_sample_report_manifest(promotion_ready=True)
            payload["resource_handle_claim"] = True
            payload["post_callback_resource_handle_ready"] = True
            payload["source_artifacts"][0]["source_path"] = "/tmp/static-window.txt"
            payload["source_artifacts"][0]["path_redacted"] = False
            payload["flag_samples"] = payload["flag_samples"][:-1]
            payload["flag_samples"][0]["sample_kind"] = "runtime_rejected_object"
            payload["flag_samples"][0]["support"] = ["bad/path"]
            payload["flag_samples"][0]["public_lifecycle_name_assigned"] = True
            payload["non_claims"] = []
            payload["remaining_blockers"] = []
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_sample_promotion_ready_overclaim", reasons)
        self.assertIn("uobject_flag_sample_resourcehandle_overclaim", reasons)
        self.assertIn("uobject_flag_sample_post_callback_ready_overclaim", reasons)
        self.assertIn("uobject_flag_sample_source_artifact_path_present", reasons)
        self.assertIn("uobject_flag_sample_source_path_not_redacted", reasons)
        self.assertIn("uobject_flag_sample_required_masks_missing", reasons)
        self.assertIn("uobject_flag_sample_kind_invalid", reasons)
        self.assertIn("uobject_flag_sample_support_invalid", reasons)
        self.assertIn("uobject_flag_sample_lifecycle_name_overclaim", reasons)
        self.assertIn("uobject_flag_sample_non_claims_missing", reasons)
        self.assertIn("uobject_flag_sample_remaining_blockers_missing", reasons)

    def test_blocks_uobject_flag_sample_missing_source_schema_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            payload = uobject_flag_sample_report_manifest()
            payload["source_artifacts"] = [
                source
                for source in payload["source_artifacts"]
                if source["schema"] == gate.UOBJECT_FLAG_TRANSITION_MATRIX_SCHEMA
            ]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_sample_source_schema_coverage_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_sample_duplicate_mask_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            payload = uobject_flag_sample_report_manifest()
            payload["flag_samples"].append(dict(payload["flag_samples"][0]))
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_sample_mask_cardinality_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_sample_report_lifecycle_name_text_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            payload = uobject_flag_sample_report_manifest()
            payload["flag_samples"][0]["hypothesis"] = "RF_TagGarbageTemp lifecycle name"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_sample_ue_lifecycle_name_overclaim",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_sample_absolute_paths_in_neutral_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-samples.json"
            payload = uobject_flag_sample_report_manifest()
            payload["flag_samples"][0]["note"] = "/tmp/static-window.txt"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_sample_absolute_path_string",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_accepts_uobject_flag_semantic_correlation_candidate_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            write_json(manifest, uobject_flag_semantic_correlation_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_accepts_uobject_flag_semantic_correlation_from_workspace_outside_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = Path(tmp) / "offline-artifacts"
            manifest = workspace / "uobject-flag-semantic.json"
            write_json(manifest, uobject_flag_semantic_correlation_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_blocks_uobject_flag_semantic_correlation_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            write_json(manifest, uobject_flag_semantic_correlation_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_uobject_flag_semantic_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_semantic_correlation_overclaims_and_missing_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = uobject_flag_semantic_correlation_manifest(promotion_ready=True)
            payload["builder_contract"]["resource_handle_claim"] = True
            payload["builder_contract"]["lookup_promotion"] = True
            payload["source_pack"] = str(workspace / "semantic-pack")
            payload["inputs"]["weak_helper_predicates.txt"]["path_redacted"] = False
            payload["inputs"]["weak_helper_predicates.txt"]["provenance"] = {"verified": False}
            payload["remaining_blockers"] = []
            payload["non_claims"] = []
            payload["observations"][0]["hypothesis"] = "pending-kill lifecycle name"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_semantic_promotion_ready_overclaim", reasons)
        self.assertIn("uobject_flag_semantic_contract_promotion_ready_overclaim", reasons)
        self.assertIn("uobject_flag_semantic_resourcehandle_overclaim", reasons)
        self.assertIn("uobject_flag_semantic_lookup_overclaim", reasons)
        self.assertIn("uobject_flag_semantic_source_pack_not_redacted", reasons)
        self.assertIn("uobject_flag_semantic_input_path_not_redacted", reasons)
        self.assertIn("uobject_flag_semantic_input_provenance_missing", reasons)
        self.assertIn("uobject_flag_semantic_remaining_blockers_missing", reasons)
        self.assertIn("uobject_flag_semantic_non_claims_missing", reasons)
        self.assertIn("uobject_flag_semantic_ue_lifecycle_name_overclaim", reasons)

    def test_blocks_uobject_flag_semantic_source_pack_path_even_outside_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = uobject_flag_semantic_correlation_manifest()
            payload["source_pack"]["path"] = str(Path(tmp) / "outside-protected" / "semantic-pack")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_semantic_source_pack_path_present", reasons)

    def test_blocks_uobject_flag_semantic_source_pack_id_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = uobject_flag_semantic_correlation_manifest()
            payload["source_pack"]["id"] = "../semantic-pack"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "uobject_flag_semantic_source_pack_id_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_uobject_flag_semantic_input_names_that_are_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = uobject_flag_semantic_correlation_manifest()
            payload["inputs"]["../weak_helper_predicates.txt"] = payload["inputs"].pop("weak_helper_predicates.txt")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_semantic_input_name_invalid", reasons)

    def test_blocks_uobject_flag_semantic_input_record_path_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = uobject_flag_semantic_correlation_manifest()
            payload["inputs"]["weak_helper_predicates.txt"]["source_file"] = str(workspace / "raw.txt")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_semantic_input_path_present", reasons)

    def test_blocks_uobject_flag_semantic_input_provenance_path_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = uobject_flag_semantic_correlation_manifest()
            payload["inputs"]["weak_helper_predicates.txt"]["provenance"]["artifact_path"] = str(workspace / "raw.txt")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_semantic_input_provenance_path_present", reasons)

    def test_blocks_uobject_flag_semantic_additional_builder_contract_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = uobject_flag_semantic_correlation_manifest()
            payload["builder_contract"]["requires_live_server"] = True
            payload["builder_contract"]["public_lifecycle_names_assigned"] = True
            payload["builder_contract"]["mutation_promotion"] = True
            payload["builder_contract"]["return_override_promotion"] = True
            payload["builder_contract"]["fail_closed"] = False
            payload["observations"][0]["runtime_ready"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_semantic_requires_live_server_overclaim", reasons)
        self.assertIn("uobject_flag_semantic_lifecycle_name_overclaim", reasons)
        self.assertIn("uobject_flag_semantic_mutation_overclaim", reasons)
        self.assertIn("uobject_flag_semantic_return_override_overclaim", reasons)
        self.assertIn("uobject_flag_semantic_not_fail_closed", reasons)
        self.assertIn("uobject_flag_semantic_readiness_overclaim", reasons)

    def test_blocks_uobject_flag_semantic_public_overclaims_outside_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = uobject_flag_semantic_correlation_manifest()
            payload["observations"][0]["claim"] = "ResourceHandle lookup safe for public SDK"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_semantic_public_overclaim_resourcehandle", reasons)
        self.assertIn("uobject_flag_semantic_public_overclaim_lookup_safe", reasons)
        self.assertIn("uobject_flag_semantic_public_overclaim_public_sdk", reasons)

    def test_blocks_current_style_uobject_flag_semantic_correlation_generic_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "uobject-flag-semantic.json"
            payload = {
                "schema": gate.UOBJECT_FLAG_SEMANTIC_CORRELATION_SCHEMA,
                "binary": {"sha256": BINARY_SHA, "source": "offline copied ShooterGameServer artifact"},
                "source_pack": str(workspace / "semantic-pack"),
                "inputs": {"weak_helper_predicates.txt": {"bytes": 128, "sha256": "c" * 64}},
                "blockers_remaining": ["no coherent runtime negative sample"],
                "non_claims": sorted(gate.REQUIRED_UOBJECT_FLAG_SEMANTIC_NON_CLAIMS),
            }
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("uobject_flag_semantic_evidence_kind_mismatch", reasons)
        self.assertIn("uobject_flag_semantic_status_not_candidate_blocked", reasons)
        self.assertIn("uobject_flag_semantic_missing_builder_contract", reasons)
        self.assertIn("uobject_flag_semantic_binary_path_not_redacted", reasons)
        self.assertIn("uobject_flag_semantic_source_pack_not_redacted", reasons)
        self.assertIn("uobject_flag_semantic_input_path_not_redacted", reasons)
        self.assertIn("uobject_flag_semantic_input_provenance_missing", reasons)
        self.assertIn("uobject_flag_semantic_remaining_blockers_missing", reasons)

    def test_accepts_weak_helper_static_polarity_candidate_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-static-polarity.json"
            write_json(manifest, weak_helper_static_polarity_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_weak_helper_static_polarity_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-static-polarity.json"
            write_json(manifest, weak_helper_static_polarity_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_weak_helper_static_polarity_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_weak_helper_static_polarity_overclaims_and_missing_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-static-polarity.json"
            payload = weak_helper_static_polarity_manifest(promotion_ready=True)
            payload["builder_contract"]["resource_handle_claim"] = True
            payload["builder_contract"]["lookup_promotion"] = True
            payload["source_pack"]["path"] = str(workspace / "source-pack")
            payload["inputs"]["weak_helper_polarity_windows.txt"]["path_redacted"] = False
            payload["inputs"]["weak_helper_polarity_windows.txt"]["provenance"] = {"verified": False}
            payload["remaining_blockers"] = []
            payload["non_claims"] = []
            payload["observations"] = [{"hypothesis": "pending-kill lifecycle name"}]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("weak_helper_static_polarity_promotion_ready_overclaim", reasons)
        self.assertIn("weak_helper_static_polarity_contract_promotion_ready_overclaim", reasons)
        self.assertIn("weak_helper_static_polarity_resourcehandle_overclaim", reasons)
        self.assertIn("weak_helper_static_polarity_lookup_overclaim", reasons)
        self.assertIn("weak_helper_static_polarity_source_pack_path_present", reasons)
        self.assertIn("weak_helper_static_polarity_input_path_not_redacted", reasons)
        self.assertIn("weak_helper_static_polarity_input_provenance_missing", reasons)
        self.assertIn("weak_helper_static_polarity_remaining_blockers_missing", reasons)
        self.assertIn("weak_helper_static_polarity_non_claims_missing", reasons)
        self.assertIn("weak_helper_static_polarity_ue_lifecycle_name_overclaim", reasons)

    def test_blocks_weak_helper_static_polarity_source_pack_id_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-static-polarity.json"
            payload = weak_helper_static_polarity_manifest()
            payload["source_pack"]["id"] = str(protected / "live" / "source-pack")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "weak_helper_static_polarity_source_pack_id_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_weak_helper_static_polarity_source_and_input_provenance_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-static-polarity.json"
            payload = weak_helper_static_polarity_manifest()
            payload["source_pack"]["provenance"]["artifact_sha256"] = "a" * 64
            payload["inputs"]["weak_helper_polarity_windows.txt"]["provenance"]["binary_sha256"] = "b" * 64
            payload["inputs"]["weak_helper_polarity_windows.txt"]["provenance"]["sidecar_sha256"] = "not-a-sha"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("weak_helper_static_polarity_source_pack_provenance_artifact_sha256_mismatch", reasons)
        self.assertIn("weak_helper_static_polarity_input_provenance_binary_sha256_mismatch", reasons)
        self.assertIn("weak_helper_static_polarity_input_provenance_sidecar_sha256_invalid", reasons)

    def test_accepts_weak_helper_static_polarity_bundled_provenance_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-static-polarity.json"
            payload = weak_helper_static_polarity_manifest()
            payload["source_pack"]["provenance"]["schema"] = "obelisk.weak-helper-bundled-artifact-provenance.v1"
            payload["inputs"]["weak_helper_polarity_windows.txt"]["provenance"][
                "schema"
            ] = "obelisk.weak-helper-bundled-artifact-provenance.v1"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_accepts_weak_helper_polarity_caller_mode_candidate_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-polarity-caller-mode.json"
            write_json(manifest, weak_helper_polarity_caller_mode_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_blocks_weak_helper_polarity_caller_mode_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-polarity-caller-mode.json"
            write_json(manifest, weak_helper_polarity_caller_mode_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_weak_helper_polarity_caller_mode_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_weak_helper_polarity_caller_mode_source_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-polarity-caller-mode.json"
            payload = weak_helper_polarity_caller_mode_manifest()
            payload["source_artifacts"]["semantic_correlation"].pop("path_redacted")
            payload["source_artifacts"]["semantic_correlation"]["path"] = str(workspace / "semantic.json")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("weak_helper_polarity_caller_mode_source_artifact_path_present", reasons)
        self.assertIn("weak_helper_polarity_caller_mode_source_artifact_path_not_redacted", reasons)

    def test_blocks_weak_helper_polarity_caller_mode_missing_candidate_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-polarity-caller-mode.json"
            payload = weak_helper_polarity_caller_mode_manifest()
            payload["status"] = "ready"
            payload["consumption_scope"] = "public_resource_handle"
            payload["remaining_blockers"] = []
            payload["non_claims"] = []
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("weak_helper_polarity_caller_mode_status_not_candidate_blocked", reasons)
        self.assertIn("weak_helper_polarity_caller_mode_scope_mismatch", reasons)
        self.assertIn("weak_helper_polarity_caller_mode_remaining_blockers_missing", reasons)
        self.assertIn("weak_helper_polarity_caller_mode_non_claims_missing", reasons)

    def test_blocks_weak_helper_polarity_caller_mode_public_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-polarity-caller-mode.json"
            payload = weak_helper_polarity_caller_mode_manifest()
            payload["helpers"]["0x1d56a30"]["claim"] = "ResourceHandle lookup ready"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("weak_helper_polarity_caller_mode_public_overclaim_resourcehandle", reasons)
        self.assertIn("weak_helper_polarity_caller_mode_public_overclaim_lookup_ready", reasons)

    def test_blocks_weak_helper_static_polarity_missing_second_source_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "weak-helper-static-polarity.json"
            payload = weak_helper_static_polarity_manifest()
            payload["remaining_blockers"] = [
                blocker
                for blocker in payload["remaining_blockers"]
                if blocker != "no_second_source_lifecycle_semantics"
            ]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "weak_helper_static_polarity_remaining_blockers_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )


if __name__ == "__main__":
    unittest.main()
