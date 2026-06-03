#!/usr/bin/env python3
"""Tests for validate_offline_artifact_gate.py."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_offline_artifact_gate as gate
import normalize_artifact_pack as artifact_pack
import build_resource_handle_serial_policy as serial_policy_builder
from test_check_permissions_admin_query_failclosed_contract import (
    manifest as permissions_admin_query_failclosed_manifest,
)
from test_check_player_identity_runtime_principal_lifecycle_evidence import (
    manifest as runtime_principal_lifecycle_evidence_manifest,
)
from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (
    manifest as approved_runtime_principal_lifecycle_evidence_manifest,
    safe_test_env as approved_runtime_safe_test_env,
)


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


def command_chat_response_route_readiness(root: Path) -> dict:
    target_details = [
        {
            "target": target,
            "path": str(root / "base-snapshots" / gate.COMMAND_CHAT_RESPONSE_ROUTE_SNAPSHOT_FILENAMES[target.rsplit(":", 1)[1]]),
            "comparable": True,
            "second_source_status": "accepted",
            "block_reasons": [],
        }
        for target in sorted(gate.COMMAND_CHAT_RESPONSE_ROUTE_TARGETS)
    ]
    return {
        "schema": gate.READINESS_REPORT_SCHEMA,
        "evidence_scope": "second_source_layout_evidence_only",
        "gate_mode": "planning_layout_intake",
        "source_root": str(root),
        "producer": {
            "script": "scripts/compare_reflection_snapshots.py",
            "argv": [
                "scripts/compare_reflection_snapshots.py",
                "--base-root",
                str(root),
                "--candidate-root",
                str(root / "vanilla-gdb-snapshots"),
                "--target-set",
                gate.COMMAND_CHAT_RESPONSE_ROUTE_TARGET_SET,
                "--readiness-report",
                "--json",
            ],
            "output_name": "command-chat-response-route-planning-readiness.json",
        },
        "second_source_status": "compared",
        "strict_identity_indices": False,
        "target_sets": [gate.COMMAND_CHAT_RESPONSE_ROUTE_TARGET_SET],
        "target_filters": sorted(gate.COMMAND_CHAT_RESPONSE_ROUTE_TARGETS),
        "totals": {
            "targets": 3,
            "comparable": 3,
            "blocked": 0,
            "second_source_accepted": 3,
            "second_source_inconclusive": 0,
            "second_source_missing": 0,
            "second_source_rejected": 0,
        },
        "modules": [
            {
                "module": "base-snapshots",
                "schema": "ufunction",
                "targets": 3,
                "comparable": 3,
                "blocked": 0,
                "block_reasons": {},
                "second_source": {"accepted": 3, "inconclusive": 0, "missing": 0, "rejected": 0},
                "target_details": target_details,
            }
        ],
        "planning_layout_gate": {
            "ready": True,
            "ready_scope": "planning_only",
            "layout_ready": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [],
        },
        "promotion_gate": {
            "ready": False,
            "ready_scope": "planning_only",
            "layout_ready": True,
            "promotion_ready": False,
            "blockers": [{"reason": "planning_layout_intake_not_promotion_gate", "count": 1}],
        },
        "target_set_guidance": [
            {
                "target_set": gate.COMMAND_CHAT_RESPONSE_ROUTE_TARGET_SET,
                "classification": "command_chat_response_route_guidance_only_candidate",
                "why_blocked": sorted(gate.command_chat_response_public_readiness.REQUIRED_GUIDANCE_BLOCKERS),
                "snapshot_prep_checks": list(gate.command_chat_response_public_readiness.REQUIRED_REDACTION_GUIDANCE_FRAGMENTS),
                "non_claim": "does not promote command/chat response path, public reply/send-chat ABI, command router, permissions, player identity, raw FString access, mutation, return override, runtime hooks, or release readiness",
            }
        ],
        "non_claims": ["accepted second-source readiness is layout evidence only"],
        "not_promoted_surfaces": sorted(gate.REQUIRED_READINESS_NON_PROMOTED_SURFACES),
    }


def command_chat_response_route_manifest(*, binary_sha256: str = BINARY_SHA) -> dict:
    return {
        "schema": gate.COMMAND_CHAT_RESPONSE_ROUTE_PLANNING_SECOND_SOURCE_SCHEMA,
        "status": "candidate-only",
        "target_set": gate.COMMAND_CHAT_RESPONSE_ROUTE_TARGET_SET,
        "target_count": 3,
        "created_date": "2026-06-01",
        "obelisk_commit": "test",
        "ark_binary_sha256": binary_sha256,
        "gobjects": "0x595b7e0",
        "fname_root_slot": "0x5956f30",
        "base": {
            "root": "base-snapshots",
            "core_artifact_sha256": "b" * 64,
            "capture_id": "base-capture",
            "evidence_pack_id": "base-pack",
        },
        "candidate": {
            "root": "vanilla-gdb-snapshots",
            "core_artifact_sha256": "c" * 64,
            "capture_id": "candidate-capture",
            "evidence_pack_id": "candidate-pack",
        },
        "readiness_report": gate.command_chat_response_public_readiness.DEFAULT_READINESS_NAME,
        "readiness_summary": {
            "second_source_accepted": 3,
            "second_source_inconclusive": 0,
            "planning_layout_gate_ready": True,
            "ready_scope": "planning_only",
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "non_claims": sorted(gate.REQUIRED_COMMAND_CHAT_RESPONSE_ROUTE_NON_CLAIMS),
    }


def command_chat_response_route_snapshot_payload(filename: str) -> dict:
    target_name = filename.removesuffix(".snapshot.json").rsplit(".", 1)[1]
    return {
        "schema": SNAPSHOT_SCHEMA,
        "evidence": {
            "artifact_sha256": "d" * 64,
            "capture_id": "unit-test-command-response",
            "evidence_pack_id": "unit-test-command-response-pack",
            "source": "unit-test",
            "status": "candidate-only",
        },
        "targets": [
            {
                "target": {"name": target_name},
                "property_chain": {
                    "properties": [
                        {"name": "UnitTestProperty", "status": "candidate-only"},
                    ]
                },
            }
        ],
    }


def write_command_chat_response_route_fixture(
    workspace: Path,
    *,
    manifest_payload: dict | None = None,
    readiness_payload: dict | None = None,
) -> Path:
    root = workspace / "command-chat-response-route-planning-distinct-second-source-20260601"
    for snapshot_root in ("base-snapshots", "vanilla-gdb-snapshots"):
        for filename in gate.COMMAND_CHAT_RESPONSE_ROUTE_SNAPSHOT_FILENAMES.values():
            write_json(root / snapshot_root / filename, command_chat_response_route_snapshot_payload(filename))
    write_json(
        root / gate.command_chat_response_public_readiness.DEFAULT_READINESS_NAME,
        readiness_payload if readiness_payload is not None else command_chat_response_route_readiness(root),
    )
    write_json(root / "manifest.json", manifest_payload if manifest_payload is not None else command_chat_response_route_manifest())
    return root / "manifest.json"


def item_return_only_policy_slice_manifest(
    *,
    policy_status: str = "evidence-only",
    promotion_ready: bool = False,
    copied_bool_count: int = 3,
    descriptor_preflight_count: int = 3,
    excluded_field_count: int = 5,
    missing_targets: list[str] | None = None,
    non_claims: list[str] | None = None,
    include_descriptor_preflight: bool = True,
) -> dict:
    copied_fields = sorted(gate.REQUIRED_ITEM_RETURN_ONLY_COPIED_FIELDS)
    excluded_fields = sorted(gate.REQUIRED_ITEM_RETURN_ONLY_EXCLUDED_FIELDS)
    if missing_targets is None:
        missing_targets = []
    if non_claims is None:
        non_claims = sorted(gate.REQUIRED_ITEM_RETURN_ONLY_NON_CLAIMS) + [
            "does not copy CraftBlueprint, bIgnoreInventoryRequirement, bConsumeResources, toInventory, DestinationItem, or AdditionalData"
        ]
    input_snapshots = [
        {
            "id": f"snapshot-{index:04d}",
            "sha256": f"{index}" * 64,
            "target": target,
        }
        for index, target in enumerate(
            [
                "PrimalItem.AllowEquipItem",
                "PrimalItem.CanRepair",
                "PrimalItem.CraftBlueprint",
                "PrimalItem.UseItemOntoItem",
            ],
            start=1,
        )
    ]
    source_by_target = {snapshot["target"]: snapshot for snapshot in input_snapshots}
    excluded_source_by_target = {
        snapshot["target"]: snapshot["id"]
        for snapshot in input_snapshots
    }
    copied_return_bools = [
        {
            "target": target,
            "field": "ReturnValue",
            "copied_field": field,
            "direction": "return",
            "type": "bool",
            "element_size": 1,
            "evidence_status": "copied-return-bool-only",
            "source_snapshot": source_by_target[target]["id"],
            "source_snapshot_sha256": source_by_target[target]["sha256"],
        }
        for field in copied_fields
        for target in [field.rsplit(".", 1)[0]]
    ]
    payload = {
        "schema": gate.ITEM_RETURN_ONLY_POLICY_SLICE_SCHEMA,
        "snapshot_root": "redacted",
        "input_target_set": "item-compact-intake",
        "output_target_set": "item-return-only-policy-slice",
        "policy_status": policy_status,
        "missing_targets": missing_targets,
        "generated_from": {
            "snapshot_schema": SNAPSHOT_SCHEMA,
            "input_snapshots": input_snapshots,
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
        "copied_return_bools": copied_return_bools,
        "excluded_fields": [
            {
                "target": field.rsplit(".", 1)[0],
                "field": field.rsplit(".", 1)[1],
                "excluded_field": field,
                "reason": "unit_test_excluded",
                "source_snapshot": excluded_source_by_target[field.rsplit(".", 1)[0]],
            }
            for field in excluded_fields
        ],
        "non_claims": non_claims,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": promotion_ready,
            "copied_bool_count": copied_bool_count,
            "descriptor_preflight_count": descriptor_preflight_count,
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
    if include_descriptor_preflight:
        payload["descriptor_preflight"] = {
            "status": "internal-evidence-only",
            "scope": "item-return-only-policy-slice",
            "descriptor_count": 3,
            "resource_kind": "INVENTORY_ITEM",
            "resource_backing": "inventory_backed",
            "payload_policy": "copied_return_value_only",
            "return_value_only": True,
            "assigned_event_kind": None,
            "assigned_event_kind_mask": None,
            "promotion_ready": False,
            "public_promotion": False,
            "public_surface": False,
            "descriptors": [
                {
                    "descriptor": gate.ITEM_RETURN_ONLY_DESCRIPTOR_BY_TARGET[entry["target"]],
                    "target": entry["target"],
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
                for entry in copied_return_bools
            ],
            "explicitly_not_assigned": [
                "event_kind",
                "event_kind_mask",
                "public_metadata_json",
                "runtime_dispatcher_tables",
                "plugin_callbacks",
            ],
        }
    return payload


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


def structure_aggregate_census_policy_slice_manifest(
    *,
    policy_status: str = "evidence-only",
    promotion_ready: bool = False,
    consume_only: bool = True,
    counters: dict | None = None,
    histograms: dict | None = None,
    non_claims: list[str] | None = None,
) -> dict:
    copied_fields = [
        "PrimalStructure.AllowStructureAccess.ReturnValue",
        "PrimalStructure.IsAllowedToDemolish.ReturnValue",
        "PrimalStructure.SetVariant.VariantIndex",
        "PrimalStructure.SetVariant.bForceSet",
        "PrimalStructure.SetVariant.ReturnValue",
        "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue",
        "PrimalStructureSeating.CanSeat.bForce",
        "PrimalStructureSeating.CanSeat.ReturnValue",
    ]
    redacted_fields = [
        "PrimalStructure.AllowStructureAccess.ForPC",
        "PrimalStructure.IsAllowedToDemolish.ForPC",
        "PrimalStructureItemContainer.AllowToggleActivation.ForPC",
        "PrimalStructureSeating.CanSeat.ForPC",
        "PrimalStructureSeating.CanSeat.forCharacter",
    ]
    excluded_fields = [
        "PrimalStructureItemContainer.VerifyPinCode.pinCode",
        "PrimalStructureItemContainer.VerifyPinCode.ReturnValue",
    ]
    if counters is None:
        counters = dict(gate.REQUIRED_STRUCTURE_AGGREGATE_COUNTERS)
    if histograms is None:
        histograms = dict(gate.REQUIRED_STRUCTURE_AGGREGATE_HISTOGRAMS)
    if non_claims is None:
        non_claims = sorted(gate.REQUIRED_STRUCTURE_AGGREGATE_NON_CLAIMS)
    input_snapshots = [
        {"id": f"snapshot-{index:04d}", "sha256": f"{index}" * 64, "target": target}
        for index, target in enumerate(sorted(gate.REQUIRED_STRUCTURE_AGGREGATE_INPUT_TARGETS), start=1)
    ]
    source_by_target = {snapshot["target"]: snapshot for snapshot in input_snapshots}
    copied_shapes = {
        "PrimalStructure.AllowStructureAccess.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "offset": "0x8", "offset_internal": 8},
        "PrimalStructure.IsAllowedToDemolish.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "offset": "0x8", "offset_internal": 8},
        "PrimalStructure.SetVariant.VariantIndex": {"field": "VariantIndex", "direction": "in", "type": "int32", "offset": "0x0", "offset_internal": 0},
        "PrimalStructure.SetVariant.bForceSet": {"field": "bForceSet", "direction": "in", "type": "bool", "offset": "0x4", "offset_internal": 4},
        "PrimalStructure.SetVariant.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "offset": "0x5", "offset_internal": 5},
        "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "offset": "0x8", "offset_internal": 8},
        "PrimalStructureSeating.CanSeat.bForce": {"field": "bForce", "direction": "in", "type": "bool", "offset": "0x10", "offset_internal": 16},
        "PrimalStructureSeating.CanSeat.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "offset": "0x11", "offset_internal": 17},
    }
    excluded_shapes = {
        "PrimalStructureItemContainer.VerifyPinCode.pinCode": {"field": "pinCode", "direction": "in", "type": "int32", "property_class": "IntProperty", "offset": "0x0", "offset_internal": 0, "reason": "pin_code_value_excluded"},
        "PrimalStructureItemContainer.VerifyPinCode.ReturnValue": {"field": "ReturnValue", "direction": "return", "type": "bool", "property_class": "BoolProperty", "offset": "0x4", "offset_internal": 4, "reason": "pin_code_return_value_excluded"},
    }
    return {
        "schema": gate.STRUCTURE_AGGREGATE_CENSUS_POLICY_SLICE_SCHEMA,
        "snapshot_root": "redacted",
        "input_target_set": "structure-aggregate-census-planning",
        "output_target_set": "structure-aggregate-census-policy-slice",
        "policy_status": policy_status,
        "consume_only": consume_only,
        "missing_targets": [],
        "generated_from": {"snapshot_schema": SNAPSHOT_SCHEMA, "input_snapshots": input_snapshots},
        "coverage": {
            "status": "complete",
            "input_targets": sorted(gate.REQUIRED_STRUCTURE_AGGREGATE_INPUT_TARGETS),
            "copied_fields_permitted": copied_fields,
            "redacted_fields": redacted_fields,
            "explicitly_excluded_fields": excluded_fields,
        },
        "copied_fields_permitted": [
            {
                "target": field.rsplit(".", 1)[0],
                "copied_field": field,
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
                "reason": "character_ref_excluded" if field.endswith("forCharacter") else "player_controller_ref_excluded",
            }
            for field in redacted_fields
        ],
        "explicitly_excluded_fields": [
            {
                "target": "PrimalStructureItemContainer.VerifyPinCode",
                "excluded_field": field,
                "evidence_status": "explicitly-excluded-pin-code-field",
                **excluded_shapes[field],
            }
            for field in excluded_fields
        ],
        "approved_counters": counters,
        "approved_histograms": histograms,
        "non_claims": non_claims,
        "safety_summary": {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": promotion_ready,
            "consume_only": consume_only,
            "copied_field_count": len(copied_fields),
            "redacted_field_count": len(redacted_fields),
            "explicitly_excluded_field_count": len(excluded_fields),
            "explicitly_excluded": sorted(gate.REQUIRED_STRUCTURE_AGGREGATE_EXPLICIT_EXCLUSIONS),
        },
    }


def structure_build_policy_offline_attestation_manifest() -> dict:
    checker_report = {
        "schema": gate.STRUCTURE_BUILD_POLICY_OFFLINE_INTAKE_CHECK_SCHEMA,
        "target_set": gate.STRUCTURE_BUILD_POLICY_TARGET_SET,
        "status": "accepted_planning_only",
        "ready": True,
        "accepted_for_offline_planning": True,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "enforcement_ready": False,
        "expected_status": gate.STRUCTURE_BUILD_POLICY_EXPECTED_STATUS,
        "expected_totals": dict(gate.STRUCTURE_BUILD_POLICY_EXPECTED_TOTALS),
        "readiness_path": "/tmp/obelisk-structure-build-policy-readiness.json",
        "readiness_sha256": gate.STRUCTURE_BUILD_POLICY_READINESS_SHA256,
        "non_claim": gate.STRUCTURE_BUILD_POLICY_EXPECTED_NON_CLAIM,
        "readiness_flags": {
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "enforcement_ready": False,
        },
        "non_claim_matrix": {
            "public_structure_events_sdk": "not_claimed",
            "structure_sdk": "not_claimed",
            "build_policy_sdk": "not_claimed",
            "enforcement": "not_claimed",
            "identity_lookup": "not_claimed",
            "mutation": "not_claimed",
            "return_override": "not_claimed",
            "runtime_hooks": "not_claimed",
            "v1_completion": "not_claimed",
        },
        "field_shape_contract": {
            target: {
                "num_parms": len(fields),
                "parms_size": 1,
                "properties": [
                    {
                        "name": field,
                        "class_name": "ObjectProperty" if field == "PC" else "IntProperty",
                        "offset_internal": index,
                        "element_size": 1,
                        "struct_type": None,
                        "redaction": gate.STRUCTURE_BUILD_POLICY_FIELD_REDACTION_POLICY[field],
                    }
                    for index, field in enumerate(fields)
                ],
            }
            for target, fields in gate.STRUCTURE_BUILD_POLICY_EXPECTED_TARGETS.items()
        },
        "field_redaction": {
            "public_payload": "not_claimed",
            "payload_exposure": "none",
            "runtime_param_read": "not_claimed",
            "return_override": "not_claimed",
            "policy": dict(gate.STRUCTURE_BUILD_POLICY_FIELD_REDACTION_POLICY),
        },
        "blockers": [],
    }
    return {
        "schema": gate.STRUCTURE_BUILD_POLICY_OFFLINE_ATTESTATION_SCHEMA,
        "artifact_status": "evidence-only",
        "target_set": gate.STRUCTURE_BUILD_POLICY_TARGET_SET,
        "readiness_sha256": gate.STRUCTURE_BUILD_POLICY_READINESS_SHA256,
        "checker_report": checker_report,
        "consume_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "enforcement_ready": False,
        "snapshot_sources": {
            "base": {
                "id": "base-structure-build-policy-fixture",
                "target_set": gate.STRUCTURE_BUILD_POLICY_TARGET_SET,
                "sha256": "a" * 64,
            },
            "candidate": {
                "id": "candidate-structure-build-policy-fixture",
                "target_set": gate.STRUCTURE_BUILD_POLICY_TARGET_SET,
                "sha256": "b" * 64,
            },
        },
        "redaction_policy": {
            "redacted_fields": [
                "PC",
                "location",
                "rotation",
                "OutPlacementData",
                "PlayerViewRotation",
            ],
        },
        "promotion_gate": {
            "ready": False,
            "blockers": ["planning_layout_only_no_public_build_policy_sdk"],
        },
        "non_claims": sorted(gate.REQUIRED_STRUCTURE_BUILD_POLICY_NON_CLAIMS),
    }


def players_identity_first_evidence_manifest(
    *,
    artifact_status: str = "candidate_only",
    promotion_ready: bool = False,
    public_sdk_ready: bool = False,
    runtime_ready: bool = False,
) -> dict:
    targets = gate.known_ufunction_target_set_targets("players-identity-lifecycle-intake")
    input_snapshots = [
        {
            "id": f"snapshot-{index:04d}",
            "sha256": hashlib.sha256(target.encode("utf-8")).hexdigest(),
            "target": target,
        }
        for index, target in enumerate(targets, start=1)
    ]
    target_entries = [
        {
            "target": target,
            "source_snapshot": f"snapshot-{index:04d}",
            "source_snapshot_sha256": hashlib.sha256(target.encode("utf-8")).hexdigest(),
            "property_order": ["PlayerLikeField"],
            "status": "candidate_only",
            "lifecycle_anchor_role": "not_accepted",
            "blockers": ["identity-like fields are force-redacted"],
        }
        for index, target in enumerate(targets, start=1)
    ]
    forced_redacted_fields = [
        {
            "target": target,
            "field": f"{target}.PlayerLikeField",
            "classification": "forced_redacted",
            "blockers": ["identity-like field is not public identity"],
        }
        for target in targets
    ]
    forbidden_fields = [
        {
            "target": target,
            "forbidden_field": f"{target}.PlayerLikeField",
            "reason": "identity-like field",
        }
        for target in targets
    ]
    return {
        "schema": gate.PLAYERS_IDENTITY_FIRST_EVIDENCE_SCHEMA,
        "artifact_status": artifact_status,
        "readiness_classification": "planning_only",
        "promotion_ready": promotion_ready,
        "public_sdk_ready": public_sdk_ready,
        "runtime_ready": runtime_ready,
        "snapshot_root": "redacted",
        "input_target_set": "players-identity-lifecycle-intake",
        "generated_from": {"snapshot_schema": SNAPSHOT_SCHEMA, "input_snapshots": input_snapshots},
        "target_set_coverage": {
            "schema": gate.TARGET_SET_COVERAGE_SCHEMA,
            "status": "complete",
            "complete": True,
            "declared_target_sets": [
                {
                    "name": "players-identity-lifecycle-intake",
                    "source": "manifest",
                    "expected_targets": targets,
                    "covered_targets": targets,
                    "missing_targets": [],
                    "complete": True,
                }
            ],
            "expected_targets": targets,
            "emitted_targets": targets,
            "missing_targets": [],
            "unexpected_targets": [],
        },
        "artifact_identity": {
            "ark_binary_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
            "obelisk_commit": "5ad06ff",
            "build_type": "offline_core",
            "target_set_revision": "reflection_target_sets.py:players-identity-lifecycle-intake",
            "source_artifact_ids": [
                "artifact_sha256:1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e",
                "capture_id:primary_core_20260527T031311Z",
                "evidence_pack_id:primary_core_pack_20260527T031311Z",
            ],
            "path_redacted": True,
        },
        "targets": target_entries,
        "fields": forced_redacted_fields,
        "copied_candidates": [],
        "forced_redacted_fields": forced_redacted_fields,
        "forbidden_fields": forbidden_fields,
        "lifecycle_anchors": {
            "session_start_accepted": False,
            "session_end_accepted": False,
            "accepted_start_targets": [],
            "accepted_end_targets": [],
            "blockers": [
                "no accepted session-start/login/connect UFunction anchor in players-identity-lifecycle-intake",
                "no accepted session-end/logout/disconnect UFunction anchor in players-identity-lifecycle-intake",
            ],
        },
        "privacy_policy": {
            "public_principal_ready": False,
            "copied_public_identifier": None,
            "persistent_identifier_ready": False,
            "process_local_identifier_ready": False,
        },
        "promotion_gate": {"ready": False, "promotion_ready": False, "blockers": ["identity remains planning-only"]},
        "safety_summary": {
            "target_count": len(gate.REQUIRED_PLAYERS_IDENTITY_INPUT_TARGETS),
            "expected_target_count": len(gate.REQUIRED_PLAYERS_IDENTITY_INPUT_TARGETS),
            "missing_target_count": 0,
            "field_count": len(forced_redacted_fields),
            "copied_candidate_count": 0,
            "forced_redacted_count": len(forced_redacted_fields),
            "forbidden_count": len(forbidden_fields),
            "promotion_ready": promotion_ready,
            "public_sdk_ready": public_sdk_ready,
            "runtime_ready": runtime_ready,
            "explicitly_excluded": sorted(gate.REQUIRED_PLAYERS_IDENTITY_EXPLICIT_EXCLUSIONS),
        },
        "non_claims": [
            "candidate-only planning evidence for players-identity-lifecycle-intake",
            "does not accept ServerListPlayers or ServerKickPlayer as login/logout lifecycle anchors",
            "does not expose copied public player identity, process-local identity, persistent identity, sender identity, permissions, commands, economy, or moderation APIs",
            "does not expose UE pointers, raw params, FName/GObjects indices, object identity, lookup, ResourceHandle, mutation, or return overrides",
            "copied chat text remains unauthenticated and does not establish a principal",
        ],
    }


def players_identity_lifecycle_anchor_candidates_manifest() -> dict:
    anchor = {
        "role": "session_start",
        "target": "MissionType.AddPlayerToMission",
        "outer": "MissionType",
        "function": "AddPlayerToMission",
        "acceptance_status": "candidate_recorded",
        "accepted": False,
        "function_flags": "0x00000000",
        "num_parms": 1,
        "parms_size": 1,
        "return_value_offset": "0xffffffff",
        "property_order": ["bWasSuccessful"],
        "fields": [
            {
                "name": "bWasSuccessful",
                "source_property_class": "BoolProperty",
                "direction": "out",
                "offset": "0x0",
                "element_size": 1,
                "array_dim": 1,
                "classification": "copied_candidate",
                "copied_scalar_eligibility": "candidate_non_identity_scalar",
                "bool_masks": {"byte_mask": "0x01", "field_mask": "0xff"},
            }
        ],
        "evidence": {
            "source_snapshot": "snapshot-0001",
            "source_snapshot_sha256": "a" * 64,
            "snapshot_schema": SNAPSHOT_SCHEMA,
            "source_kind": "sanitized_snapshot",
            "binary_sha256": BINARY_SHA,
        },
        "corroboration": {
            "status": "missing",
            "second_source_report_sha256": None,
            "static_report_sha256": None,
        },
        "blockers": ["layout_not_accepted"],
    }
    return {
        "schema": gate.PLAYERS_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES_SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "input_target_set": "players-identity-lifecycle-intake",
        "snapshot_root": "redacted",
        "artifact_identity": {
            "ark_binary_sha256": BINARY_SHA,
            "obelisk_commit": "reviewed-commit",
            "build_type": "sanitized_snapshot",
            "target_set_revision": "reflection_target_sets.py:players-identity-lifecycle-intake",
            "source_artifact_ids": [
                f"artifact_sha256:{'b' * 64}",
                "capture_id:player-lifecycle-candidates",
                "evidence_pack_id:player-lifecycle-pack",
            ],
            "path_redacted": True,
        },
        "candidate_anchors": [anchor],
        "lifecycle_acceptance": {
            "session_start_accepted": False,
            "session_end_accepted": False,
            "accepted_start_targets": [],
            "accepted_end_targets": [],
            "blockers": ["layout_not_accepted"],
        },
        "principal_policy": {
            "public_principal_ready": False,
            "copied_public_identifier": None,
            "principal_copy_policy": "unresolved",
            "privacy_policy": "unresolved",
            "invalidation_semantics": "unresolved",
            "logging_policy": "identity_values_not_logged",
        },
        "promotion_gate": {
            "ready": False,
            "ready_scope": "planning_only",
            "promotion_ready": False,
            "blockers": ["public_principal_policy_unresolved"],
        },
        "safety_summary": {
            "candidate_anchor_count": 1,
            "accepted_anchor_count": 0,
            "field_count": 1,
            "identity_redacted_field_count": 0,
            "copied_candidate_count": 1,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": sorted(gate.lifecycle_anchor_candidates.REQUIRED_EXCLUSIONS),
        },
        "non_claims": sorted(gate.lifecycle_anchor_candidates.REQUIRED_NON_CLAIMS),
    }


def players_identity_principal_invalidation_policy_manifest() -> dict:
    principal_fields = [
        ("principal", "opaque_token"),
        ("generation", "uint64"),
        ("state", "enum"),
        ("scope_flags", "uint64_flags"),
        ("privacy_class", "enum"),
    ]
    rejected_sources = sorted(gate.principal_invalidation_policy.REQUIRED_REJECTED_PUBLIC_IDENTITY_SOURCES)
    return {
        "schema": gate.PLAYERS_IDENTITY_PRINCIPAL_INVALIDATION_POLICY_SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "lifecycle_layout_source": {
            "status": "candidate_layout_consumable",
            "accepted_layout_only": True,
            "start_anchor": "ShooterGameMode.HandleNewPlayer",
            "end_anchor": "ShooterGameMode.OnLogout",
            "principal_invalidation_evidence": "candidate_policy_only",
        },
        "principal": {
            "kind": "copied_opaque_principal",
            "copied": True,
            "ownership": "obelisk_owned_copy",
            "public_identity": "opaque_principal",
            "reversible": False,
            "stable_across_processes": False,
            "real_identity_source": None,
            "fields": [
                {
                    "name": name,
                    "type": field_type,
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "opaque_principal",
                }
                for name, field_type in principal_fields
            ],
        },
        "generation": {
            "field": "generation",
            "zero_invalid": True,
            "increments_on": [
                "session_start",
                "logout_or_disconnect_invalidation",
                "reconnect_after_invalidation",
                "transfer_or_download_edge",
                "duplicate_or_conflicting_identity",
                "server_restart",
                "plugin_reload",
            ],
        },
        "state": {
            "field": "state",
            "allowed": ["unknown", "active", "invalidated"],
            "fail_closed_states": ["unknown", "invalidated"],
        },
        "scope_flags": {
            "field": "scope_flags",
            "allowed_flags": ["process_local", "session_local", "not_cross_cluster"],
            "forbidden_flags": ["persistent", "cross_process", "cross_cluster"],
        },
        "privacy_class": {
            "field": "privacy_class",
            "allowed": ["opaque_principal"],
            "public_value": "opaque_principal",
        },
        "invalidation_cases": [
            {
                "case": name,
                "fail_closed": True,
                "consumer_result": "deny",
                "generation_action": "invalidate_or_increment_generation",
                "trigger": f"{name}_trigger",
            }
            for name in sorted(gate.principal_invalidation_policy.REQUIRED_INVALIDATION_CASES)
        ],
        "negative_consumer_rules": [
            {
                "rule": name,
                "fail_closed": True,
                "forbids": sorted(
                    set(rejected_sources)
                    | gate.principal_invalidation_policy.REQUIRED_FORBIDDEN_CAPABILITY_CLAIMS
                ),
            }
            for name in sorted(gate.principal_invalidation_policy.REQUIRED_NEGATIVE_RULES)
        ],
        "runtime_evidence": {
            "approved": False,
            "status": "missing",
            "required_for": ["promote", "public_readiness", "runtime_readiness"],
        },
        "evidence_policy": {
            "accepted_evidence_class": "candidate_policy_only",
            "malformed_evidence_result": "deny",
            "unsupported_evidence_result": "deny",
            "fail_closed": True,
        },
        "rejected_public_identity_sources": rejected_sources,
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "approved_runtime_evidence_missing",
                "principal_invalidation_semantics_unresolved",
            ],
        },
        "safety_summary": {
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": sorted(gate.principal_invalidation_policy.REQUIRED_EXCLUSIONS),
        },
        "non_claims": sorted(gate.principal_invalidation_policy.REQUIRED_NON_CLAIMS),
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


def fuobjectarray_field_window_redacted_manifest() -> dict:
    return {
        "schema": gate.FUOBJECTARRAY_FIELD_WINDOW_REDACTED_SCHEMA,
        "status": "accepted_internal_static_evidence",
        "binary": {
            "sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
            "path_redacted": True,
        },
        "candidate": {
            "label": "gobjects",
            "kind": "gobjects",
            "address_redacted": True,
            "address_sha256": "1" * 64,
        },
        "redaction": {
            "absolute_addresses": "omitted",
            "raw_disassembly": "omitted",
            "raw_decompiler_text": "omitted",
            "absolute_paths": "omitted",
        },
        "sources": {
            "ghidra_stdout": {
                "artifact_sha256": "2" * 64,
                "tool": "ghidra",
                "version": "12.1",
            },
            "r2_windows": {
                "artifact_sha256": "3" * 64,
                "tool": "radare2",
                "version": "5.5.0",
            },
        },
        "fuobjectarray_window": {
            "same_base_flow": {
                "proven": True,
                "evidence": [
                    "candidate_passed_to_constructor_helper",
                    "same_candidate_registered_with_finalizer",
                    "constructor_writes_relative_fields",
                    "serial_accessors_use_same_field_family",
                ],
            },
            "required_fields": {
                "root": {"present": True, "basis": "candidate_base"},
                "chunks": {"present": True, "relative_offset": "base+0x10"},
                "count": {"present": True, "relative_offset": "base+0x24"},
                "serial": {"present": True, "relative_offset": "base+0x58"},
            },
            "windows": [
                {"id": "static_init_caller", "ghidra_seen": True, "r2_seen": True},
                {"id": "ctor_helper", "ghidra_seen": True, "r2_seen": True},
                {"id": "serial_accessor", "ghidra_seen": True, "r2_seen": True},
            ],
        },
        "builder_contract": {
            "candidate_static_contract_blocker_to_clear": "missing_gobjects_coherent_field_window",
            "promotion_gate_ready": False,
            "remaining_blockers": ["static_only_evidence"],
            "consumption_scope": "internal_static_research_only",
        },
    }


def resource_handle_revalidation_evaluator_manifest(*, ready: bool = False) -> dict:
    payload = {
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
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": ready,
        "uobject_flags_validity_semantics_proven": ready,
        "evidence_checks": {
            "evidence_without_lifetime_flags_ready": True,
            "public_resource_handle_contract_present": False,
            "public_resourcehandle_policy_present": False,
            "post_callback_lifetime_contract_present": False,
            "post_callback_lifetime_policy_proven": False,
            "serial_reuse_or_wraparound_policy_present": False,
            "runtime_rejection_samples_present": False,
            "runtime_serial_semantics_present": False,
            "runtime_resourcehandle_promotion_evidence_complete": False,
            "zero_serial_negative_samples_satisfy_runtime_rejection_samples": False,
            "zero_serial_negative_samples_satisfy_runtime_serial_semantics": False,
            "version_matched_source_decompiler_correlation_for_public_lifecycle_names_present": False,
            "rejected_runtime_object_samples_present": False,
        },
        "offline_zero_serial_negative_samples_summary": {
            "candidate_only": True,
            "does_not_satisfy_runtime_requirements": [
                {
                    "offline_schema": gate.RESOURCE_HANDLE_ZERO_SERIAL_NEGATIVE_SAMPLES_SCHEMA,
                    "required_runtime_schema": gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA,
                    "blocker": "no_rejected_runtime_object_samples",
                    "satisfied": False,
                },
                {
                    "offline_schema": gate.RESOURCE_HANDLE_ZERO_SERIAL_NEGATIVE_SAMPLES_SCHEMA,
                    "required_runtime_schema": gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
                    "blocker": "no_serial_reuse_or_wraparound_policy",
                    "satisfied": False,
                },
            ],
        },
        "blockers": [] if ready else ["uobject_flags_validity_semantics_unproven"],
        "promotion_gate": {
            "ready": ready,
            "blockers": [] if ready else ["uobject_flags_validity_semantics_unproven"],
        },
    }
    identity_without_hash = {
        "artifact_kind": gate.RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
        "capture_id": "resourcehandle-revalidation-test",
        "evidence_pack_id": "resourcehandle-revalidation-pack",
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": payload,
    }
    payload["output_artifact_identity"] = {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(gate.canonical_json_bytes(material)).hexdigest(),
    }
    return payload


def refresh_resource_handle_revalidation_output_identity(payload: dict) -> None:
    identity = payload["output_artifact_identity"]
    identity_without_hash = {
        "artifact_kind": identity["artifact_kind"],
        "capture_id": identity["capture_id"],
        "evidence_pack_id": identity["evidence_pack_id"],
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": {
            key: value
            for key, value in payload.items()
            if key != "output_artifact_identity"
        },
    }
    identity["artifact_sha256"] = hashlib.sha256(gate.canonical_json_bytes(material)).hexdigest()


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


def runtime_evidence_preflight(*, paired_runtime_schema: str) -> dict:
    return {
        "scope": gate.RUNTIME_EVIDENCE_PREFLIGHT_SCOPE,
        "completion_rule": gate.RUNTIME_EVIDENCE_PREFLIGHT_COMPLETION_RULE,
        "paired_runtime_schema": paired_runtime_schema,
        "approved_debug_window_recorded": True,
        "bounded_allowlist_recorded": True,
        "source_serial_policy_consume_gate_accepted": True,
        "raw_disclosure_redaction_checked": True,
        "runtime_capture_paths_redacted": True,
        "offline_zero_serial_non_substitution_acknowledged": True,
        "promotion_claims_disabled": True,
        "public_api_unchanged": True,
        "no_broad_tracing_or_scanner_or_core_capture": True,
        "paired_runtime_manifest_required": True,
        "promotion_evidence_complete": False,
        "authorizes_runtime_work": False,
        "public_resource_handle_ready": False,
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
        "runtime_evidence_preflight": runtime_evidence_preflight(
            paired_runtime_schema=gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA
        ),
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
        "runtime_evidence_preflight": runtime_evidence_preflight(
            paired_runtime_schema=gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA
        ),
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
        "summary": {
            "fresh_frame_local_allow_rows": 1,
            "negative_reject_rows": 1,
        },
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
            "does_not_promote_gobjects_lookup",
            "does_not_promote_public_object_identity",
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


def attach_zero_serial_output_identity(payload: dict, *, capture_id: str, evidence_pack_id: str) -> None:
    identity_without_hash = {
        "artifact_kind": gate.RESOURCE_HANDLE_ZERO_SERIAL_NEGATIVE_SAMPLES_SCHEMA,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": gate.resource_handle_zero_serial_negative_samples_canonical_report(payload),
    }
    payload["output_artifact_identity"] = {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(gate.canonical_json_bytes(material)).hexdigest(),
    }


def zero_serial_negative_samples_manifest() -> dict:
    payload = {
        "schema": gate.RESOURCE_HANDLE_ZERO_SERIAL_NEGATIVE_SAMPLES_SCHEMA,
        "status": "candidate_blocked",
        "evidence_kind": "internal_offline_zero_serial_negative_samples",
        "deterministic_negative_cohort": True,
        "sources": [
            {
                "source_label": "primary",
                "core_path_redacted": True,
                "core_sha256": "a" * 64,
                "core_sha256_verified": True,
                "metadata": {
                    "gobjects": "0x595b7e0",
                    "fname_root_slot": "0x5956f30",
                    "fname_table": "0x5a94660",
                    "chunks": "0x600000",
                    "object_count": 50835,
                    "anchor_index": 50834,
                    "max_scan_index": 50834,
                    "name_resolution": "enabled",
                },
                "scan_totals": {
                    "indices_scanned": 50835,
                    "nonnull_items_seen": 50835,
                    "candidate_uobjects_seen": 50835,
                },
                "zero_serial_negative_samples": [
                    {
                        "index": 0,
                        "address": "0x100000",
                        "class_name": "Package",
                        "name": "CoreUObject",
                        "flags": 129,
                        "fuobject_item": "0x200000",
                        "item_dword_0x8": 0,
                        "item_dword_0xC": 1,
                        "internal_index": 0,
                        "internal_index_matches": True,
                        "membership": "candidate-uobject",
                        "membership_pass": True,
                    }
                ],
                "positive_anchor": {
                    "index": 50834,
                    "address": "0x110000",
                    "class_name": "LinkerLoad",
                    "name": "LinkerLoad",
                    "flags": 129,
                    "fuobject_item": "0x210000",
                    "item_dword_0x8": 1001,
                    "item_dword_0xC": 116,
                    "internal_index": 50834,
                    "internal_index_matches": True,
                    "membership": "candidate-uobject",
                    "membership_pass": True,
                },
                "deterministic_negative_cohort": True,
                "blockers": [],
            }
        ],
        "serial_candidate_field": {
            "offset": "FUObjectItem+0x8",
            "width": "uint32",
            "accepted_positive_anchor": "index 50834 nonzero serial",
        },
        "non_claims": [
            "candidate-only offline evidence",
            "does not prove runtime reuse, wraparound, UObject flag validity, lookup, mutation, or public ResourceHandle",
        ],
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "promotion_gate": {
            "ready": False,
            "blockers": ["candidate_only_zero_serial_negative_samples"],
        },
    }
    attach_zero_serial_output_identity(
        payload,
        capture_id="zero-serial-test",
        evidence_pack_id="zero-serial-pack",
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


def core_dump_evidence_pack_manifest(
    workspace: Path,
    *,
    binary_sha256: str = BINARY_SHA,
    evidence_status: dict | None = None,
    core_path: str | None = None,
    core_sha256: str = "c" * 64,
) -> dict:
    return {
        "schema": gate.CORE_DUMP_EVIDENCE_PACK_SCHEMA,
        "binary": {"sha256": binary_sha256},
        "evidence_status": evidence_status
        if evidence_status is not None
        else {"status": "complete", "gdb_core_failed": False},
        "core": {"path": core_path if core_path is not None else str(workspace / "core"), "sha256": core_sha256},
    }


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


def reflection_inventory_comparison_manifest(workspace: Path) -> dict:
    return {
        "schema": gate.REFLECTION_INVENTORY_PACK_COMPARISON_SCHEMA,
        "status": "accepted",
        "promotion_status": "not_promoted_candidate_only",
        "base": {
            "pack": str(workspace / "base-pack"),
            "artifact_identity": {
                "artifact_kind": "offline-core",
                "artifact_sha256": "b" * 64,
                "capture_id": "base-capture",
                "evidence_pack_id": "base-pack",
            },
            "binary_sha256": BINARY_SHA,
            "summary": {"fname_root_ready": True},
        },
        "candidate": {
            "pack": str(workspace / "candidate-pack"),
            "artifact_identity": {
                "artifact_kind": "offline-core",
                "artifact_sha256": "c" * 64,
                "capture_id": "candidate-capture",
                "evidence_pack_id": "candidate-pack",
            },
            "binary_sha256": BINARY_SHA,
            "summary": {"fname_root_ready": True},
        },
        "function_comparison": {
            "base_function_count": 2,
            "candidate_function_count": 2,
            "shared_function_count": 2,
            "missing_in_candidate": [],
            "new_in_candidate": [],
            "changed_functions": [],
        },
        "blockers": [],
        "non_claims": sorted(gate.REQUIRED_REFLECTION_INVENTORY_COMPARISON_NON_CLAIMS),
    }


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
            "type": "redacted_transfer_payload_bool",
            "source_property_class": "BoolProperty",
            "offset": offset,
            "element_size": 1,
            "array_dim": 1,
            "status": "candidate",
            "redaction": "Transfer ScriptStruct bool-tail metadata only; payload bool not promoted",
            "property_flags": "0x10001040002200",
            "bool_field_size": 1,
            "bool_byte_offset": 0,
            "byte_mask": "0x01",
            "field_mask": "0xff",
            "native_bool": False,
            "promotion_blockers": [
                "no_public_transfer_sdk",
                "scriptstruct_payload_not_runtime_observed",
                "transfer_scriptstruct_payload_decode_blocked",
            ],
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
            "copied_scalar_count_total": 0,
            "copied_scalar_by_kind": {},
            "redacted_count_total": 4,
            "redacted_by_reason": {"text": 1, "transfer_payload_bool": 3},
            "promotion_blocker_count_total": 0,
            "promotion_blockers_by_reason": {},
            "not_promoted_surfaces": sorted(gate.REQUIRED_REDACTED_SCRIPTSTRUCT_NOT_PROMOTED_SURFACES),
        },
        "signatures": [
            {
                "target": "PrimalLocalProfile.ARKTributeDino",
                "property_count": 1,
                "promotion_blockers": [
                    "no_public_transfer_sdk",
                    "scriptstruct_layout_candidate_only",
                    "transfer_scriptstruct_payload_decode_blocked",
                ],
                "fields": [
                    {
                        "name": "DinoClassName",
                        "type": "redacted_text",
                        "source_property_class": "StrProperty",
                        "promotion_blockers": [
                            "no_public_transfer_sdk",
                            "scriptstruct_payload_not_runtime_observed",
                            "transfer_scriptstruct_payload_decode_blocked",
                        ],
                    }
                ],
            },
            {
                "target": "PrimalLocalProfile.ArkTributePlayerData",
                "property_count": 3,
                "promotion_blockers": [
                    "no_public_transfer_sdk",
                    "scriptstruct_layout_candidate_only",
                    "transfer_scriptstruct_payload_decode_blocked",
                ],
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
    def test_accepts_reflection_inventory_comparison_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            write_json(manifest, reflection_inventory_comparison_manifest(workspace))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["status"], "accepted")
        self.assertEqual([], result["blockers"])

    def test_blocks_reflection_inventory_comparison_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            write_json(manifest, reflection_inventory_comparison_manifest(workspace))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_reflection_inventory_comparison_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_reflection_inventory_comparison_with_function_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            payload = reflection_inventory_comparison_manifest(workspace)
            payload["status"] = "blocked"
            payload["function_comparison"]["missing_in_candidate"] = ["ShooterPlayerController.ServerKickPlayer"]
            payload["blockers"] = ["missing_functions_in_candidate"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("reflection_inventory_comparison_status_not_accepted", reasons)
        self.assertIn("reflection_inventory_comparison_blockers_present", reasons)
        self.assertIn("reflection_inventory_comparison_missing_in_candidate_present", reasons)

    def test_blocks_reflection_inventory_comparison_reused_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            payload = reflection_inventory_comparison_manifest(workspace)
            payload["candidate"]["artifact_identity"] = dict(payload["base"]["artifact_identity"])
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("reflection_inventory_comparison_artifact_identity_not_distinct_artifact_sha256", reasons)
        self.assertIn("reflection_inventory_comparison_artifact_identity_not_distinct_capture_id", reasons)
        self.assertIn("reflection_inventory_comparison_artifact_identity_not_distinct_evidence_pack_id", reasons)

    def test_blocks_reflection_inventory_comparison_reused_pack_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            payload = reflection_inventory_comparison_manifest(workspace)
            payload["candidate"]["pack"] = payload["base"]["pack"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "reflection_inventory_comparison_pack_path_not_distinct",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_reflection_inventory_comparison_unready_side_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            payload = reflection_inventory_comparison_manifest(workspace)
            payload["candidate"]["summary"] = {"fname_root_ready": False}
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "reflection_inventory_comparison_candidate_fname_root_not_ready",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_reflection_inventory_comparison_incoherent_function_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            payload = reflection_inventory_comparison_manifest(workspace)
            payload["function_comparison"]["candidate_function_count"] = 3
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "reflection_inventory_comparison_function_count_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_reflection_inventory_comparison_protected_pack_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            payload = reflection_inventory_comparison_manifest(workspace)
            payload["base"]["pack"] = str(protected / "live-pack")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("reflection_inventory_comparison_base_path_text_under_protected_root", reasons)
        self.assertIn("reflection_inventory_comparison_base_path_not_textually_under_workspace_root", reasons)

    def test_blocks_reflection_inventory_comparison_missing_non_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "reflection-comparison" / "manifest.json"
            payload = reflection_inventory_comparison_manifest(workspace)
            payload["non_claims"] = []
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "reflection_inventory_comparison_non_claims_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

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

    def test_blocks_redacted_transfer_scriptstruct_copied_scalar_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            payload = redacted_scriptstruct_signature_manifest()
            field = payload["signatures"][1]["fields"][0]
            field["type"] = "bool"
            field["redaction"] = "copied scalar candidate"
            field["promotion_blockers"] = ["scriptstruct_payload_not_runtime_observed"]
            payload["safety_summary"]["copied_scalar_count_total"] = 1
            payload["safety_summary"]["copied_scalar_by_kind"] = {"bool": 1}
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_signature_transfer_copied_scalar_count_nonzero", reasons)
        self.assertIn("scriptstruct_signature_transfer_copied_scalar_by_kind_nonempty", reasons)
        self.assertIn("scriptstruct_signature_transfer_copied_scalar_field_claim", reasons)
        self.assertIn("scriptstruct_signature_transfer_scalar_type_not_redacted_payload", reasons)
        self.assertIn("scriptstruct_signature_transfer_field_blockers_missing", reasons)

    def test_blocks_redacted_transfer_scriptstruct_nonscalar_missing_field_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            payload = redacted_scriptstruct_signature_manifest()
            payload["signatures"][0]["fields"][0].pop("promotion_blockers")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_signature_transfer_field_blockers_missing", reasons)

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
            payload["signatures"] = [
                {
                    "target": "MissionType.MissionRewardEntry",
                    "property_count": 1,
                    "fields": [{"name": "RewardName", "type": "redacted_text"}],
                }
            ]
            payload["signature_count"] = 1
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["status"], "accepted")
        self.assertEqual([], result["blockers"])

    def test_blocks_redacted_transfer_scriptstruct_dino_only_even_without_target_set_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "scriptstruct-signatures" / "manifest.json"
            payload = redacted_scriptstruct_signature_manifest()
            payload["target_sets"] = []
            payload["source_target_sets"] = []
            payload["signatures"] = payload["signatures"][:1]
            payload["signature_count"] = 1
            payload["target_set_coverage"]["declared_target_sets"] = []
            payload["target_set_coverage"]["expected_targets"] = ["PrimalLocalProfile.ARKTributeDino"]
            payload["target_set_coverage"]["observed_targets"] = ["PrimalLocalProfile.ARKTributeDino"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("scriptstruct_signature_transfer_target_set_coverage_expected_targets_incomplete", reasons)
        self.assertIn("scriptstruct_signature_transfer_struct_missing", reasons)

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

    def test_accepts_relative_roots_after_absolute_path_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = Path.cwd()
            os.chdir(tmp)
            try:
                protected = Path("server")
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
            finally:
                os.chdir(previous_cwd)

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertTrue(result["artifacts"][0]["provenance_verified"])

    def test_rejects_relative_provenance_path_from_relative_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = Path.cwd()
            os.chdir(tmp)
            try:
                protected = Path("server")
                workspace = protected / "workspace-offline"
                artifact = workspace / "pack" / "artifact.txt"
                artifact.parent.mkdir(parents=True)
                artifact.write_text("offline evidence\n", encoding="utf-8")
                write_json(
                    Path(f"{artifact}.provenance.json"),
                    {
                        "schema": gate.PROVENANCE_SCHEMA,
                        "verified": True,
                        "artifact_kind": "objdump",
                        "producer": "test",
                        "tool": "objdump",
                        "binary_sha256": BINARY_SHA,
                        "artifact_sha256": gate.sha256_file(artifact),
                        "source_path": "../../live/objdump.txt",
                    },
                )

                result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("objdump", artifact)]))
            finally:
                os.chdir(previous_cwd)

        self.assertEqual("blocked", result["status"])
        self.assertIn("path_resolves_under_protected_root", {b["reason"] for b in result["blockers"]})

    def test_rejects_symlinked_workspace_root_even_when_it_resolves_to_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            linked_workspace = root / "workspace-link"
            linked_workspace.symlink_to(workspace, target_is_directory=True)

            result = gate.build_result(args(root=linked_workspace, protected_root=protected))

        blockers = result["blockers"]
        self.assertEqual("blocked", result["status"])
        self.assertIn("path_is_symlink", {blocker["reason"] for blocker in blockers})
        self.assertTrue(
            any(
                blocker.get("label") == "root"
                and blocker.get("symlink_component") == str(linked_workspace)
                for blocker in blockers
            )
        )

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

    def test_rejects_workspace_artifact_symlink_even_when_it_resolves_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            target = workspace / "artifact.txt"
            target.parent.mkdir(parents=True)
            target.write_text("offline evidence\n", encoding="utf-8")
            link = workspace / "artifact-link.txt"
            link.symlink_to(target)

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("linked", link)]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("path_is_symlink", reasons)

    def test_rejects_workspace_manifest_symlink_even_when_it_resolves_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            target = workspace / "pack" / "manifest.json"
            target.parent.mkdir(parents=True)
            write_json(target, readiness_report_manifest())
            link = workspace / "manifest-link.json"
            link.symlink_to(target)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[link]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("path_is_symlink", reasons)

    def test_rejects_manifest_symlink_swap_after_path_precheck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            live_manifest = protected / "live" / "manifest.json"
            write_json(manifest, readiness_report_manifest())
            write_json(live_manifest, readiness_report_manifest())

            original_path_blockers = gate.path_blockers
            swapped = False

            def race_path_blockers(path: Path, **kwargs: object) -> list[dict]:
                nonlocal swapped
                if path == manifest and not swapped:
                    swapped = True
                    manifest.unlink()
                    manifest.symlink_to(live_manifest)
                    return []
                return original_path_blockers(path, **kwargs)

            with mock.patch.object(gate, "path_blockers", side_effect=race_path_blockers):
                result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("json_path_is_symlink", reasons)

    def test_rejects_provenance_sidecar_symlink_swap_after_path_precheck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            artifact = workspace / "pack" / "artifact.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("offline evidence\n", encoding="utf-8")
            artifact_sha = gate.sha256_file(artifact)
            sidecar = Path(f"{artifact}.provenance.json")
            live_sidecar = protected / "live" / "artifact.txt.provenance.json"
            sidecar_payload = {
                "schema": gate.PROVENANCE_SCHEMA,
                "verified": True,
                "artifact_kind": "objdump",
                "producer": "test",
                "tool": "objdump",
                "binary_sha256": BINARY_SHA,
                "artifact_sha256": artifact_sha,
                "source_provenance": {},
            }
            write_json(sidecar, sidecar_payload)
            write_json(live_sidecar, sidecar_payload)

            original_path_blockers = gate.path_blockers
            swapped = False

            def race_path_blockers(path: Path, **kwargs: object) -> list[dict]:
                nonlocal swapped
                if path == sidecar and not swapped:
                    swapped = True
                    sidecar.unlink()
                    sidecar.symlink_to(live_sidecar)
                    return []
                return original_path_blockers(path, **kwargs)

            with mock.patch.object(gate, "path_blockers", side_effect=race_path_blockers):
                result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("objdump", artifact)]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("json_path_is_symlink", reasons)

    def test_rejects_workspace_manifest_under_symlinked_directory_even_when_it_resolves_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            target = workspace / "pack" / "manifest.json"
            target.parent.mkdir(parents=True)
            write_json(target, readiness_report_manifest())
            link_dir = workspace / "pack-link"
            link_dir.symlink_to(target.parent, target_is_directory=True)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[link_dir / "manifest.json"]))

        blockers = result["blockers"]
        self.assertEqual("blocked", result["status"])
        self.assertIn("path_is_symlink", {blocker["reason"] for blocker in blockers})
        self.assertTrue(any(str(link_dir) == blocker.get("symlink_component") for blocker in blockers))

    def test_rejects_workspace_artifact_under_symlinked_directory_even_when_it_resolves_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            target = workspace / "pack" / "artifact.txt"
            target.parent.mkdir(parents=True)
            target.write_text("offline evidence\n", encoding="utf-8")
            link_dir = workspace / "pack-link"
            link_dir.symlink_to(target.parent, target_is_directory=True)

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("objdump", link_dir / "artifact.txt")]))

        blockers = result["blockers"]
        self.assertEqual("blocked", result["status"])
        self.assertIn("path_is_symlink", {blocker["reason"] for blocker in blockers})
        self.assertTrue(any(str(link_dir) == blocker.get("symlink_component") for blocker in blockers))

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

    def test_rejects_relative_provenance_path_resolving_to_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            artifact = workspace / "pack" / "artifact.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("offline evidence\n", encoding="utf-8")
            write_json(
                Path(f"{artifact}.provenance.json"),
                {
                    "schema": gate.PROVENANCE_SCHEMA,
                    "verified": True,
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": gate.sha256_file(artifact),
                    "source_path": "../../live/objdump.txt",
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("objdump", artifact)]))

        self.assertIn("path_resolves_under_protected_root", {b["reason"] for b in result["blockers"]})

    def test_rejects_relative_provenance_source_artifacts_list_resolving_to_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            artifact = workspace / "pack" / "artifact.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("offline evidence\n", encoding="utf-8")
            write_json(
                Path(f"{artifact}.provenance.json"),
                {
                    "schema": gate.PROVENANCE_SCHEMA,
                    "verified": True,
                    "binary_sha256": BINARY_SHA,
                    "artifact_sha256": gate.sha256_file(artifact),
                    "source_artifacts": ["../../live/raw-objdump.txt"],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, artifacts=[("objdump", artifact)]))

        self.assertIn("path_resolves_under_protected_root", {b["reason"] for b in result["blockers"]})

    def test_accepts_complete_core_manifest_and_blocks_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            write_json(manifest, core_dump_evidence_pack_manifest(workspace))
            accepted = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))
            partial_payload = core_dump_evidence_pack_manifest(
                workspace,
                evidence_status={"status": "partial-gdb-failed", "gdb_core_failed": True},
            )
            write_json(manifest, partial_payload)
            blocked = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", accepted["status"])
        blocked_reasons = {b["reason"] for b in blocked["blockers"]}
        self.assertIn("evidence_pack_not_complete", blocked_reasons)
        self.assertIn("evidence_pack_gdb_core_failed", blocked_reasons)

    def test_blocks_core_manifest_missing_fail_closed_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            payload = core_dump_evidence_pack_manifest(workspace)
            payload.pop("evidence_status")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn("evidence_pack_missing_evidence_status", {b["reason"] for b in result["blockers"]})

    def test_blocks_core_manifest_shape_and_expected_binary_mismatch(self) -> None:
        cases = [
            ("binary", "evidence_pack_binary_sha256_invalid"),
            ("core", "evidence_pack_core_missing"),
            ("core_sha256", "evidence_pack_core_sha256_invalid"),
            ("core_path", "evidence_pack_core_path_invalid"),
        ]
        for field, reason in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                protected = Path(tmp) / "server"
                workspace = protected / "workspace-offline"
                manifest = workspace / "pack" / "manifest.json"
                payload = core_dump_evidence_pack_manifest(workspace)
                if field == "binary":
                    payload["binary"] = {"sha256": "not-a-sha"}
                elif field == "core":
                    payload.pop("core")
                elif field == "core_sha256":
                    payload["core"]["sha256"] = "not-a-sha"
                elif field == "core_path":
                    payload["core"]["path"] = ""
                write_json(manifest, payload)

                result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

                self.assertIn(reason, {b["reason"] for b in result["blockers"]})

        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "pack" / "manifest.json"
            write_json(manifest, core_dump_evidence_pack_manifest(workspace, binary_sha256="b" * 64))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn("evidence_pack_binary_sha256_mismatch", {b["reason"] for b in result["blockers"]})

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

    def test_accepts_command_chat_response_route_planning_manifest_for_consume_mode(self) -> None:
        self.assertIn(gate.COMMAND_CHAT_RESPONSE_ROUTE_PLANNING_SECOND_SOURCE_SCHEMA, gate.SUPPORTED_MANIFEST_SCHEMAS)

        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = write_command_chat_response_route_fixture(workspace)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertEqual(gate.COMMAND_CHAT_RESPONSE_ROUTE_PLANNING_SECOND_SOURCE_SCHEMA, result["manifests"][0]["schema"])

    def test_blocks_command_chat_response_route_planning_manifest_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = write_command_chat_response_route_fixture(workspace)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("promote_mode_command_chat_response_route_planning_candidate_only", reasons)

    def test_command_chat_response_route_manifest_fails_closed_on_overclaims_and_bad_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            root = workspace / "command-chat-response-route-planning-distinct-second-source-20260601"
            manifest_payload = command_chat_response_route_manifest()
            manifest_payload["candidate"]["core_artifact_sha256"] = manifest_payload["base"]["core_artifact_sha256"]
            manifest_payload["readiness_summary"]["public_sdk_ready"] = True
            readiness_payload = command_chat_response_route_readiness(root)
            readiness_payload["target_filters"] = readiness_payload["target_filters"][:-1]
            manifest = write_command_chat_response_route_fixture(
                workspace,
                manifest_payload=manifest_payload,
                readiness_payload=readiness_payload,
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("command_chat_response_route_identity_not_distinct_core_artifact_sha256", reasons)
        self.assertIn("command_chat_response_route_readiness_summary_public_sdk_ready_mismatch", reasons)
        self.assertIn("command_chat_response_route_readiness_overclaim", reasons)
        self.assertIn("command_chat_response_route_target_filters_mismatch", reasons)

    def test_command_chat_response_static_orientation_is_not_an_artifact_gate_schema(self) -> None:
        orientation_schema = "obelisk.command-chat-response-static-orientation-check.v1"
        self.assertNotIn(orientation_schema, gate.SUPPORTED_MANIFEST_SCHEMAS)

        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "command-chat-response-static-orientation" / "manifest.json"
            write_json(
                manifest,
                {
                    "schema": orientation_schema,
                    "status": "valid",
                    "accepted_for_orientation": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "non_claims": [
                        "valid static orientation is candidate-only planning evidence",
                    ],
                },
            )

            consume_result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))
            promote_result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote")
            )

        for result in (consume_result, promote_result):
            with self.subTest(mode=result["mode"]):
                self.assertEqual(result["status"], "blocked")
                reasons = {blocker["reason"] for blocker in result["blockers"]}
                self.assertIn("unsupported_manifest_schema", reasons)

    def test_static_orientation_reports_cannot_be_accepted_as_artifacts(self) -> None:
        orientation_schemas = [
            "obelisk.command-chat-response-static-orientation-check.v1",
            "obelisk.radare2-static-orientation-windows.v1",
            "obelisk.static-candidate-orientation-contract.v1",
            "obelisk.player-identity-static-orientation-check.v1",
            "obelisk.player-identity-static-target-orientation.v1",
            "obelisk.player-identity-static-lifecycle-orientation-check.v1",
            "obelisk.player-identity-static-admin-thunks-check.v1",
        ]
        for schema in orientation_schemas:
            self.assertNotIn(schema, gate.SUPPORTED_MANIFEST_SCHEMAS)

        for schema in orientation_schemas:
            for mode in ("intake", "consume", "promote"):
                with self.subTest(schema=schema, mode=mode), tempfile.TemporaryDirectory() as tmp:
                    protected = Path(tmp) / "server"
                    workspace = protected / "workspace-offline"
                    artifact = workspace / "static-orientation" / "report.json"
                    write_json(
                        artifact,
                        {
                            "schema": schema,
                            "status": "valid",
                            "accepted_for_orientation": True,
                            "promotion_ready": False,
                            "public_sdk_ready": False,
                            "runtime_ready": False,
                            "non_claims": [
                                "valid static orientation is candidate-only planning evidence",
                            ],
                        },
                    )
                    artifact_sha = gate.sha256_file(artifact)
                    write_json(
                        Path(f"{artifact}.provenance.json"),
                        {
                            "schema": gate.PROVENANCE_SCHEMA,
                            "verified": True,
                            "artifact_kind": "static-orientation",
                            "producer": "test",
                            "tool": "fixture",
                            "binary_sha256": BINARY_SHA,
                            "artifact_sha256": artifact_sha,
                            "source_provenance": {},
                        },
                    )

                    result = gate.build_result(
                        args(
                            root=workspace,
                            protected_root=protected,
                            artifacts=[("static-orientation", artifact)],
                            mode=mode,
                        )
                    )

                    self.assertEqual("blocked", result["status"])
                    self.assertIn(
                        "static_orientation_report_not_artifact_gate",
                        {blocker["reason"] for blocker in result["blockers"]},
                    )

    def test_static_orientation_reports_cannot_be_accepted_as_manifests(self) -> None:
        for schema in sorted(gate.STATIC_ORIENTATION_REPORT_SCHEMAS):
            self.assertNotIn(schema, gate.SUPPORTED_MANIFEST_SCHEMAS)

        for schema in sorted(gate.STATIC_ORIENTATION_REPORT_SCHEMAS):
            for mode in ("intake", "consume", "promote"):
                with self.subTest(schema=schema, mode=mode), tempfile.TemporaryDirectory() as tmp:
                    protected = Path(tmp) / "server"
                    workspace = protected / "workspace-offline"
                    manifest = workspace / "static-orientation" / "manifest.json"
                    write_json(
                        manifest,
                        {
                            "schema": schema,
                            "status": "valid",
                            "accepted_for_orientation": True,
                            "promotion_ready": False,
                            "public_sdk_ready": False,
                            "runtime_ready": False,
                            "non_claims": [
                                "valid static orientation is candidate-only planning evidence",
                            ],
                        },
                    )
                    manifest_sha = gate.sha256_file(manifest)
                    write_json(
                        Path(f"{manifest}.provenance.json"),
                        {
                            "schema": gate.PROVENANCE_SCHEMA,
                            "verified": True,
                            "artifact_kind": "static-orientation",
                            "producer": "test",
                            "tool": "fixture",
                            "binary_sha256": BINARY_SHA,
                            "artifact_sha256": manifest_sha,
                            "source_provenance": {},
                        },
                    )

                    result = gate.build_result(
                        args(root=workspace, protected_root=protected, manifests=[manifest], mode=mode)
                    )

                    reasons = {blocker["reason"] for blocker in result["blockers"]}
                    self.assertEqual("blocked", result["status"])
                    self.assertIn("static_orientation_report_not_artifact_gate", reasons)
                    self.assertIn("unsupported_manifest_schema", reasons)

    def test_static_orientation_manifests_block_readiness_and_input_address_overclaims(self) -> None:
        schema = "obelisk.native-ufunction-registration-static-discovery.v1"
        self.assertIn(schema, gate.STATIC_ORIENTATION_REPORT_SCHEMAS)
        self.assertNotIn(schema, gate.SUPPORTED_MANIFEST_SCHEMAS)

        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "static-orientation" / "manifest.json"
            write_json(
                manifest,
                {
                    "schema": schema,
                    "status": "candidate",
                    "artifact_gate_eligible": False,
                    "not_artifact_gate": True,
                    "promotion_ready": True,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "inputs": {
                        "target_names": ["ShooterPlayerController.ServerListPlayers"],
                        "input_addresses": ["0x1547450"],
                    },
                    "non_claims": [
                        "does_not_promote_public_sdk",
                        "does_not_promote_ufunction_abi",
                    ],
                },
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("static_orientation_report_not_artifact_gate", reasons)
        self.assertIn("unsupported_manifest_schema", reasons)
        self.assertIn("static_orientation_report_readiness_overclaim", reasons)
        self.assertIn("static_orientation_report_input_addresses_overclaim", reasons)

    def test_accepts_normalized_artifact_pack_manifest_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "item-return-only-policy-slice-20260530T072255Z"
            pack.mkdir(parents=True)
            (pack / "consume-gate.json").write_text('{"status":"accepted"}\n', encoding="utf-8")
            (pack / "report.json").write_text('{"schema":"fixture"}\n', encoding="utf-8")
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[pack / artifact_pack.MANIFEST_NAME],
                    expected_binary_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                )
            )

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertEqual(gate.ARTIFACT_PACK_MANIFEST_SCHEMA, result["manifests"][0]["schema"])

    def test_artifact_pack_revalidates_item_return_excluded_field_source_snapshot_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "item-return-only-policy-slice-20260530T072255Z"
            pack.mkdir(parents=True)
            payload = item_return_only_policy_slice_manifest()
            payload["excluded_fields"][0]["source_snapshot"] = "unknown-snapshot"
            write_json(pack / "item-return-policy.json", payload)
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[pack / artifact_pack.MANIFEST_NAME],
                    expected_binary_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                )
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("item_return_policy_excluded_field_source_snapshot_unknown", reasons)

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

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[pack / artifact_pack.MANIFEST_NAME],
                    expected_binary_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                )
            )

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

    def test_artifact_pack_accepts_players_identity_lifecycle_anchor_child_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            write_json(pack / "players-identity-lifecycle-candidates.json", players_identity_lifecycle_anchor_candidates_manifest())
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_artifact_pack_revalidates_players_identity_lifecycle_anchor_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            child = players_identity_lifecycle_anchor_candidates_manifest()
            child["principal_policy"]["public_principal_ready"] = True
            child["candidate_anchors"][0]["notes"] = "public SDK ready and runtime ready"
            child["candidate_anchors"][0]["nested_claim"] = {"runtime_ready": True, "lookup_ready": True}
            write_json(pack / "players-identity-lifecycle-candidates.json", child)
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertNotIn("unsupported_manifest_schema", reasons)
        self.assertIn("public_principal_overclaim", reasons)
        self.assertIn("players_identity_lifecycle_anchor_candidates_readiness_overclaim", reasons)
        self.assertIn("players_identity_lifecycle_anchor_candidates_public_overclaim_public_sdk", reasons)
        self.assertIn("players_identity_lifecycle_anchor_candidates_public_overclaim_runtime_ready", reasons)

    def test_artifact_pack_accepts_players_identity_principal_invalidation_child_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            write_json(
                pack / "players-identity-principal-invalidation-policy.json",
                players_identity_principal_invalidation_policy_manifest(),
            )
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_artifact_pack_revalidates_players_identity_principal_invalidation_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            child = players_identity_principal_invalidation_policy_manifest()
            child["principal"]["kind"] = "public_player_identity"
            child["principal"]["notes"] = "public SDK ready with ResourceHandle lookup permissions commands mutation return override promoted"
            child["principal"]["nested_claim"] = {"runtime_ready": True, "lookup_ready": True, "promoted": True}
            write_json(pack / "players-identity-principal-invalidation-policy.json", child)
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertNotIn("unsupported_manifest_schema", reasons)
        self.assertIn("principal_kind_not_copied_opaque", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_readiness_overclaim", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_public_sdk", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_runtime_ready", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_promoted", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_lookup", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_resourcehandle", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_permissions", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_commands", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_mutation", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_return_override", reasons)

    def test_artifact_pack_revalidates_core_child_fail_closed_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            child = core_dump_evidence_pack_manifest(workspace, core_path="core")
            child.pop("evidence_status")
            write_json(pack / "core-evidence.json", child)
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertIn("evidence_pack_missing_evidence_status", {blocker["reason"] for blocker in result["blockers"]})

    def test_artifact_pack_core_child_blockers_are_not_duplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "artifact-pack-20260530T072255Z"
            pack.mkdir(parents=True)
            child = core_dump_evidence_pack_manifest(
                workspace,
                binary_sha256="b" * 64,
                evidence_status={"status": "partial-gdb-failed", "gdb_core_failed": True},
                core_path=str(protected / "live" / "core"),
            )
            write_json(pack / "core-evidence.json", child)
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        reason_counts = {reason: 0 for reason in {blocker["reason"] for blocker in result["blockers"]}}
        for blocker in result["blockers"]:
            reason_counts[blocker["reason"]] += 1
        self.assertEqual(1, reason_counts["evidence_pack_not_complete"])
        self.assertEqual(1, reason_counts["evidence_pack_gdb_core_failed"])
        self.assertEqual(1, reason_counts["evidence_pack_binary_sha256_mismatch"])
        self.assertEqual(1, reason_counts["path_text_under_protected_root"])
        self.assertEqual(1, reason_counts["path_resolves_under_protected_root"])

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

    def test_blocks_duplicate_redacted_signature_target_sets_even_with_matching_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            target = "SyntheticOfflineArtifact.Target"
            target_set = "offline-artifact-hygiene-intake"
            report = redacted_signature_manifest(
                target=target,
                target_sets=[target_set, target_set],
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
                    },
                    {
                        "name": target_set,
                        "source": "manifest",
                        "expected_targets": [target],
                        "covered_targets": [target],
                        "missing_targets": [],
                        "complete": True,
                    },
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

        self.assertIn(
            "signature_manifest_duplicate_target_sets",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_duplicate_redacted_signature_source_target_sets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest(
                artifact_hygiene=historical_missing_coverage_marker(),
                safety_overrides={"target_set_count": 2},
            )
            payload["source_target_sets"] = ["item-compact-intake", "item-compact-intake"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "signature_manifest_duplicate_source_target_sets",
            {blocker["reason"] for blocker in result["blockers"]},
        )

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

    def test_consume_blocks_incomplete_named_signature_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            target_set = "item-compact-intake"
            emitted_target = "PrimalItem.AllowEquipItem"
            expected_targets = gate.known_ufunction_target_set_targets(target_set)
            self.assertIsNotNone(expected_targets)
            expected_targets = list(expected_targets)
            missing_targets = [target for target in expected_targets if target != emitted_target]
            payload = redacted_signature_manifest(target=emitted_target, target_sets=[target_set])
            payload["target_set_coverage"] = {
                "schema": gate.TARGET_SET_COVERAGE_SCHEMA,
                "status": "incomplete",
                "complete": False,
                "declared_target_sets": [
                    {
                        "name": target_set,
                        "source": "manifest",
                        "expected_targets": expected_targets,
                        "covered_targets": [emitted_target],
                        "missing_targets": missing_targets,
                        "complete": False,
                    }
                ],
                "expected_targets": expected_targets,
                "emitted_targets": [emitted_target],
                "missing_targets": missing_targets,
                "unexpected_targets": [],
            }
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("signature_manifest_target_set_coverage_incomplete", reasons)
        self.assertIn("signature_manifest_target_set_coverage_status_mismatch", reasons)
        self.assertIn("signature_manifest_target_set_coverage_not_complete", reasons)

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

    def test_consume_blocks_item_return_signature_manifest_missing_descriptor_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest(
                target_sets=["item-return-only-policy-slice"],
                artifact_hygiene=historical_missing_coverage_marker(),
                safety_overrides={"target_set_count": 1},
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "item_return_descriptor_preflight_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_consume_accepts_item_return_signature_manifest_descriptor_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest(
                target_sets=["item-return-only-policy-slice"],
                artifact_hygiene=historical_missing_coverage_marker(),
                safety_overrides={"target_set_count": 1},
            )
            payload["descriptor_preflight"] = item_return_only_policy_slice_manifest()["descriptor_preflight"]
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

    def test_blocks_generic_public_runtime_v1_claim_aliases_in_candidate_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "signatures" / "signatures.json"
            payload = redacted_signature_manifest()
            payload["public_sdk_ready"] = True
            payload["claim_aliases"] = {
                "runtime_ready": True,
                "v1_complete": True,
                "complete_sdk": True,
            }
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        labels = {
            blocker["label"]
            for blocker in result["blockers"]
            if blocker["reason"] == "manifest_forbidden_true_claim_overclaim"
        }
        self.assertTrue(any(label.endswith("$.public_sdk_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.claim_aliases.runtime_ready") for label in labels))
        self.assertTrue(any(label.endswith("$.claim_aliases.v1_complete") for label in labels))
        self.assertTrue(any(label.endswith("$.claim_aliases.complete_sdk") for label in labels))

    def test_accepts_layout_only_readiness_report_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(manifest, readiness_report_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_not_ready_readiness_report_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(manifest, readiness_report_manifest(ready=False))

            result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote")
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("promote_mode_readiness_report_layout_only", reasons)

    def test_blocks_not_ready_readiness_report_with_promotion_ready_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            payload = readiness_report_manifest(ready=False)
            payload["promotion_gate"]["promotion_ready"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("readiness_report_promotion_ready_not_false", reasons)

    def test_blocks_not_ready_readiness_report_with_runtime_or_public_sdk_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            payload = readiness_report_manifest(ready=False)
            payload["promotion_gate"]["public_sdk_ready"] = True
            payload["promotion_gate"]["runtime_ready"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("readiness_report_public_sdk_ready_not_false", reasons)
        self.assertIn("readiness_report_runtime_ready_not_false", reasons)

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

    def test_blocks_readiness_report_duplicate_target_sets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(
                manifest,
                readiness_report_manifest(
                    ready=False,
                    target_sets=["minimal-second-source-intake", "minimal-second-source-intake"],
                ),
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("readiness_report_duplicate_target_sets", reasons)

    def test_blocks_readiness_report_unknown_target_sets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(manifest, readiness_report_manifest(ready=False, target_sets=["not-a-target-set"]))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("readiness_report_unknown_target_sets", reasons)

    def test_blocks_readiness_report_ambiguous_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "readiness.json"
            write_json(
                manifest,
                readiness_report_manifest(
                    ready=False,
                    target_sets=["minimal-second-source-intake", "structure-observer-intake"],
                ),
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        blockers = result["blockers"]
        reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn("readiness_report_ambiguous_target_set_coverage", reasons)
        blocker = next(
            blocker for blocker in blockers if blocker["reason"] == "readiness_report_ambiguous_target_set_coverage"
        )
        self.assertEqual(
            [item["target"] for item in blocker["overlaps"]],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
            ],
        )

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
                descriptor_preflight_count=4,
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
        self.assertIn("item_return_policy_descriptor_preflight_count_not_three", reasons)
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

    def test_blocks_item_return_only_policy_slice_source_snapshot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "item-return-policy.json"
            payload = item_return_only_policy_slice_manifest()
            payload["copied_return_bools"][0]["source_snapshot"] = "unknown-snapshot"
            payload["copied_return_bools"][1]["source_snapshot_sha256"] = "7" * 64
            payload["generated_from"]["input_snapshots"][3]["target"] = "PrimalItem.WrongTarget"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("item_return_policy_copied_bool_source_snapshot_unknown", reasons)
        self.assertIn("item_return_policy_copied_bool_source_snapshot_sha256_mismatch", reasons)
        self.assertIn("item_return_policy_copied_bool_source_snapshot_target_mismatch", reasons)

    def test_blocks_item_return_only_policy_slice_missing_descriptor_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "item-return-policy.json"
            write_json(manifest, item_return_only_policy_slice_manifest(include_descriptor_preflight=False))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "item_return_descriptor_preflight_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_item_return_descriptor_preflight_inventory_use_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "item-return-policy.json"
            payload = item_return_only_policy_slice_manifest()
            payload["descriptor_preflight"]["assigned_event_kind"] = "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK"
            payload["descriptor_preflight"]["descriptors"][0]["assigned_event_kind_mask"] = (
                "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK"
            )
            payload["descriptor_preflight"]["descriptors"][0]["field_mask"] = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("item_return_descriptor_preflight_shape_mismatch", reasons)
        self.assertIn("item_return_descriptor_preflight_descriptor_shape_mismatch", reasons)
        self.assertIn("item_return_descriptor_preflight_event_kind_drift", reasons)

    def test_blocks_item_return_descriptor_preflight_unassigned_structural_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "item-return-policy.json"
            payload = item_return_only_policy_slice_manifest()
            payload["descriptor_preflight"]["public_metadata_json"] = {}
            payload["descriptor_preflight"]["descriptors"][0]["field_mask"] = [
                "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE"
            ]
            payload["descriptor_preflight"]["descriptors"][1]["public_abi_ready"] = False
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        blockers = [
            blocker
            for blocker in result["blockers"]
            if blocker["reason"] == "item_return_descriptor_preflight_forbidden_assignment_key"
        ]
        self.assertEqual(
            ["field_mask", "public_abi_ready", "public_metadata_json"],
            sorted(blocker["key"] for blocker in blockers),
        )

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

        self.assertEqual("accepted", result["status"])
        self.assertEqual("consume", result["mode"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_mission_copied_bool_policy_slice_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "mission-copied-bool-policy.json"
            write_json(manifest, mission_copied_bool_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertEqual("blocked", result["status"])
        self.assertEqual("promote", result["mode"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_mission_copied_bool_policy_slice_evidence_only", reasons)

    def test_blocks_mission_copied_bool_policy_slice_if_get_player_usable_items_is_copied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "mission-copied-bool-policy.json"
            payload = mission_copied_bool_policy_slice_manifest()
            get_items_snapshot = next(
                snapshot
                for snapshot in payload["generated_from"]["input_snapshots"]
                if snapshot["target"] == "MissionType.GetPlayerUsableItems"
            )
            payload["copied_bools"][0].update(
                {
                    "target": "MissionType.GetPlayerUsableItems",
                    "field": "ReturnValue",
                    "copied_field": "MissionType.GetPlayerUsableItems.ReturnValue",
                    "direction": "return",
                    "offset": "0x18",
                    "offset_internal": 24,
                    "return_value_offset": "0x18",
                    "source_snapshot": get_items_snapshot["id"],
                    "source_snapshot_sha256": get_items_snapshot["sha256"],
                }
            )
            payload["coverage"]["copied_fields"] = [
                entry["copied_field"]
                for entry in payload["copied_bools"]
            ]
            payload["coverage"]["copied_targets"] = sorted(
                {entry["target"] for entry in payload["copied_bools"]}
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("mission_copied_bool_policy_copied_fields_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_copied_bool_shape_unknown", reasons)
        self.assertIn("mission_copied_bool_policy_coverage_copied_fields_mismatch", reasons)
        self.assertIn("mission_copied_bool_policy_coverage_copied_targets_mismatch", reasons)

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
            payload["mission_identity_ready"] = True
            payload["player_authority_ready"] = True
            payload["claim"] = "public Mission SDK ready"
            payload["runtime_claim"] = "runtime ready"
            payload["identity_claim"] = "mission identity established"
            payload["authority_claim"] = "player authority promoted"
            payload["input_target_set"] = "mission-public-sdk-intake"
            payload["generated_from"]["input_snapshots"] = payload["generated_from"]["input_snapshots"][:2]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("mission_copied_bool_policy_readiness_overclaim", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_public_sdk", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_runtime_ready", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_mission_identity", reasons)
        self.assertIn("mission_copied_bool_policy_public_overclaim_player_authority", reasons)
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

    def test_blocks_structure_policy_slices_promotion_gate_ready_in_consume_mode(self) -> None:
        cases = [
            (
                "structure-return-policy.json",
                structure_return_only_policy_slice_manifest,
                "structure_return_policy_readiness_overclaim",
            ),
            (
                "structure-nonpin-policy.json",
                structure_nonpin_copied_scalar_policy_slice_manifest,
                "structure_nonpin_policy_readiness_overclaim",
            ),
        ]
        for filename, payload_factory, expected_reason in cases:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as tmp:
                    protected = Path(tmp) / "server"
                    workspace = protected / "workspace-offline"
                    manifest = workspace / filename
                    payload = payload_factory()
                    payload["promotion_gate"] = {"ready": True, "blockers": []}
                    write_json(manifest, payload)

                    result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

                self.assertIn(expected_reason, {blocker["reason"] for blocker in result["blockers"]})

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

    def test_blocks_structure_nonpin_copied_scalar_policy_slice_public_structure_events_boolean_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-nonpin-policy.json"
            payload = structure_nonpin_copied_scalar_policy_slice_manifest()
            payload["public_structure_events_ready"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn("structure_nonpin_policy_readiness_overclaim", {blocker["reason"] for blocker in result["blockers"]})

    def test_accepts_structure_aggregate_census_policy_slice_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-aggregate-policy.json"
            write_json(manifest, structure_aggregate_census_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_structure_aggregate_census_policy_slice_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-aggregate-policy.json"
            write_json(manifest, structure_aggregate_census_policy_slice_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_structure_aggregate_census_policy_slice_consume_only", reasons)

    def test_blocks_structure_aggregate_census_policy_slice_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-aggregate-policy.json"
            payload = structure_aggregate_census_policy_slice_manifest(
                policy_status="accepted",
                promotion_ready=True,
                consume_only=False,
                non_claims=["does not copy VerifyPinCode"],
            )
            payload["approved_counters"]["copied_field_count"] = 7
            payload["approved_histograms"]["copied_type"] = {"bool": 8}
            payload["coverage"]["copied_fields_permitted"] = payload["coverage"]["copied_fields_permitted"][:-1]
            payload["coverage"]["explicitly_excluded_fields"] = payload["coverage"]["explicitly_excluded_fields"][:-1]
            payload["copied_fields_permitted"] = payload["copied_fields_permitted"][:-1]
            payload["redacted_structure_fields"] = payload["redacted_structure_fields"][:-1]
            payload["explicitly_excluded_fields"] = payload["explicitly_excluded_fields"][:-1]
            payload["safety_summary"]["explicitly_excluded"] = ["pinCode"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_aggregate_policy_status_not_evidence_only", reasons)
        self.assertIn("structure_aggregate_policy_not_consume_only", reasons)
        self.assertIn("structure_aggregate_policy_promotion_ready_not_false", reasons)
        self.assertIn("structure_aggregate_policy_counters_mismatch", reasons)
        self.assertIn("structure_aggregate_policy_histograms_mismatch", reasons)
        self.assertIn("structure_aggregate_policy_coverage_copied_fields_mismatch", reasons)
        self.assertIn("structure_aggregate_policy_coverage_excluded_fields_mismatch", reasons)
        self.assertIn("structure_aggregate_policy_copied_fields_count_mismatch", reasons)
        self.assertIn("structure_aggregate_policy_redacted_fields_count_mismatch", reasons)
        self.assertIn("structure_aggregate_policy_excluded_fields_count_mismatch", reasons)
        self.assertIn("structure_aggregate_policy_non_claims_missing_required_boundaries", reasons)
        self.assertIn("structure_aggregate_policy_explicit_exclusions_missing_internal_boundaries", reasons)

    def test_blocks_structure_aggregate_census_policy_slice_verify_pin_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-aggregate-policy.json"
            payload = structure_aggregate_census_policy_slice_manifest()
            payload["copied_fields_permitted"][0]["copied_field"] = "PrimalStructureItemContainer.VerifyPinCode.ReturnValue"
            payload["runtime_ready"] = True
            payload["claim"] = "public StructureEvents ready"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_aggregate_policy_copied_fields_mismatch", reasons)
        self.assertIn("structure_aggregate_policy_contains_verify_pin_code_copied_field", reasons)
        self.assertIn("structure_aggregate_policy_readiness_overclaim", reasons)
        self.assertIn("structure_aggregate_policy_public_overclaim_public_structure_events", reasons)

    def test_blocks_structure_aggregate_census_policy_slice_no_core_surface_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-aggregate-policy.json"
            payload = structure_aggregate_census_policy_slice_manifest()
            payload["claims"] = {
                "sdk": "StructureEvents SDK is ready",
                "identity": "structure identity and structure lookup are usable",
                "ownership": "structure ownership lookup is accepted",
                "build": "build placement and no-collision policy are ready",
                "mutation": "mutation allowed and return override allowed",
                "runtime": "runtime hooks and ProcessEvent hook wiring are active",
            }
            payload["non_claims"].append("v1 complete")
            payload["ownership_ready"] = True
            payload["build_placement_policy_ready"] = True
            payload["runtime_hooks_ready"] = True
            payload["v1_complete"] = True
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_aggregate_policy_public_overclaim_public_structure_events", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_structure_identity", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_structure_lookup", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_structure_ownership", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_build_placement_policy", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_no_collision_policy", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_mutation", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_return_override", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_runtime_hooks", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_v1_completion", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_ownership_ready", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_build_placement_policy_ready", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_runtime_hooks_ready", reasons)
        self.assertIn("structure_aggregate_policy_surface_overclaim_v1_complete", reasons)

    def test_blocks_structure_aggregate_census_policy_slice_promoted_status_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-aggregate-policy.json"
            payload = structure_aggregate_census_policy_slice_manifest()
            payload["promotion_status"] = "promoted"
            payload["nested_claim"] = {"readiness_status": "ready"}
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_aggregate_policy_promotion_status_overclaim", reasons)

    def test_accepts_structure_build_policy_offline_attestation_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-build-policy-attestation.json"
            write_json(manifest, structure_build_policy_offline_attestation_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_structure_build_policy_attestation_without_checker_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-build-policy-attestation.json"
            payload = structure_build_policy_offline_attestation_manifest()
            del payload["checker_report"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_build_policy_attestation_checker_report_missing", reasons)

    def test_accepts_structure_build_policy_offline_intake_check_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-build-policy-check.json"
            payload = structure_build_policy_offline_attestation_manifest()["checker_report"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_structure_build_policy_check_missing_real_checker_output_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-build-policy-check.json"
            payload = structure_build_policy_offline_attestation_manifest()["checker_report"]
            for key in (
                "blockers",
                "field_shape_contract",
                "field_redaction",
                "expected_totals",
                "expected_status",
                "readiness_path",
                "non_claim",
            ):
                del payload[key]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_build_policy_check_blockers_not_empty", reasons)
        self.assertIn("structure_build_policy_check_field_shape_contract_missing", reasons)
        self.assertIn("structure_build_policy_check_field_redaction_missing", reasons)
        self.assertIn("structure_build_policy_check_expected_totals_mismatch", reasons)
        self.assertIn("structure_build_policy_check_expected_status_mismatch", reasons)
        self.assertIn("structure_build_policy_check_readiness_path_missing", reasons)
        self.assertIn("structure_build_policy_check_non_claim_mismatch", reasons)

    def test_blocks_structure_build_policy_offline_intake_check_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-build-policy-check.json"
            payload = structure_build_policy_offline_attestation_manifest()["checker_report"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_structure_build_policy_check_planning_only", reasons)

    def test_blocks_structure_build_policy_offline_attestation_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-build-policy-attestation.json"
            write_json(manifest, structure_build_policy_offline_attestation_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_structure_build_policy_attestation_consume_only", reasons)

    def test_blocks_structure_build_policy_offline_attestation_drift_and_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "structure-build-policy-attestation.json"
            payload = structure_build_policy_offline_attestation_manifest()
            payload["readiness_sha256"] = "c" * 64
            payload["public_sdk_ready"] = True
            payload["promotion_gate"] = {"ready": True, "blockers": []}
            payload["snapshot_sources"]["candidate"]["sha256"] = payload["snapshot_sources"]["base"]["sha256"]
            payload["redaction_policy"]["redacted_fields"] = ["PC"]
            payload["claim"] = "public SDK ready"
            payload["promotion_status"] = "promoted"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("structure_build_policy_attestation_readiness_sha256_mismatch", reasons)
        self.assertIn("structure_build_policy_attestation_public_sdk_ready_not_false", reasons)
        self.assertIn("structure_build_policy_attestation_promotion_gate_not_false", reasons)
        self.assertIn("structure_build_policy_attestation_snapshot_sources_not_distinct", reasons)
        self.assertIn("structure_build_policy_attestation_redacted_fields_missing", reasons)
        self.assertIn("structure_build_policy_attestation_readiness_overclaim", reasons)
        self.assertIn("structure_build_policy_attestation_public_overclaim_public_sdk", reasons)
        self.assertIn("structure_build_policy_attestation_promotion_status_overclaim", reasons)

    def test_accepts_players_identity_first_evidence_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            write_json(manifest, players_identity_first_evidence_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_players_identity_first_evidence_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            write_json(manifest, players_identity_first_evidence_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_players_identity_first_evidence_candidate_only", reasons)

    def test_accepts_players_identity_lifecycle_anchor_candidates_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-lifecycle-candidates.json"
            write_json(manifest, players_identity_lifecycle_anchor_candidates_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_players_identity_lifecycle_anchor_candidates_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-lifecycle-candidates.json"
            write_json(manifest, players_identity_lifecycle_anchor_candidates_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_players_identity_lifecycle_anchor_candidates_candidate_only", reasons)

    def test_blocks_players_identity_lifecycle_anchor_candidate_public_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-lifecycle-candidates.json"
            payload = players_identity_lifecycle_anchor_candidates_manifest()
            payload["principal_policy"]["public_principal_ready"] = True
            payload["candidate_anchors"][0]["notes"] = "public SDK ready and runtime ready"
            payload["candidate_anchors"][0]["nested_claim"] = {"runtime_ready": True, "lookup_ready": True, "promoted": True}
            payload["candidate_anchors"][0]["fields"][0]["name"] = "SteamID"
            payload["candidate_anchors"][0]["fields"][0]["copied_scalar_eligibility"] = "candidate_copied_public_identifier"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("public_principal_overclaim", reasons)
        self.assertIn("players_identity_lifecycle_anchor_candidates_readiness_overclaim", reasons)
        self.assertIn("players_identity_lifecycle_anchor_candidates_public_overclaim_public_sdk", reasons)
        self.assertIn("players_identity_lifecycle_anchor_candidates_public_overclaim_runtime_ready", reasons)
        self.assertIn("identity_field_not_redacted", reasons)
        self.assertIn("identity_field_copied_public_overclaim", reasons)

    def test_accepts_players_identity_principal_invalidation_policy_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-principal-invalidation-policy.json"
            write_json(manifest, players_identity_principal_invalidation_policy_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_players_identity_principal_invalidation_policy_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-principal-invalidation-policy.json"
            write_json(manifest, players_identity_principal_invalidation_policy_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_players_identity_principal_invalidation_policy_candidate_only", reasons)

    def test_accepts_players_identity_runtime_principal_lifecycle_shape_fixture_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-runtime-principal-lifecycle-evidence.json"
            write_json(manifest, runtime_principal_lifecycle_evidence_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_players_identity_runtime_principal_lifecycle_shape_fixture_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-runtime-principal-lifecycle-evidence.json"
            write_json(manifest, runtime_principal_lifecycle_evidence_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_mode_players_identity_runtime_principal_lifecycle_evidence_not_readiness", reasons)

    def test_blocks_players_identity_runtime_principal_lifecycle_shape_fixture_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-runtime-principal-lifecycle-evidence.json"
            payload = runtime_principal_lifecycle_evidence_manifest()
            payload["runtime_ready"] = True
            payload["observations"][0]["uobject_address"] = "0x1234"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("runtime_ready_not_false", reasons)
        self.assertIn("ue_coordinate_or_pointer_leakage", reasons)
        self.assertIn("players_identity_runtime_principal_lifecycle_evidence_readiness_overclaim", reasons)

    def test_accepts_players_identity_runtime_principal_lifecycle_approved_evidence_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, approved_runtime_safe_test_env()):
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-runtime-principal-lifecycle-approved-evidence.json"
            write_json(manifest, approved_runtime_principal_lifecycle_evidence_manifest())

            with mock.patch.object(
                gate.approved_runtime_principal_lifecycle_evidence,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (Path(os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"]),),
            ), mock.patch.object(
                gate.approved_runtime_principal_lifecycle_evidence.window_manifest_checker,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (Path(os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"]),),
            ):
                result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_players_identity_runtime_principal_lifecycle_approved_evidence_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, approved_runtime_safe_test_env()):
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-runtime-principal-lifecycle-approved-evidence.json"
            write_json(manifest, approved_runtime_principal_lifecycle_evidence_manifest())

            with mock.patch.object(
                gate.approved_runtime_principal_lifecycle_evidence,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (Path(os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"]),),
            ), mock.patch.object(
                gate.approved_runtime_principal_lifecycle_evidence.window_manifest_checker,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (Path(os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"]),),
            ):
                result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_blocked_until_identity_public_contract_gate", reasons)

    def test_accepts_permissions_admin_query_failclosed_contract_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "permissions-admin-query-failclosed.json"
            write_json(manifest, permissions_admin_query_failclosed_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_permissions_admin_query_failclosed_contract_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "permissions-admin-query-failclosed.json"
            write_json(manifest, permissions_admin_query_failclosed_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("promote_blocked_for_candidate_only_pre_abi_contract", reasons)
        self.assertIn("candidate_only_permissions_admin_query_contract_not_readiness_evidence", reasons)

    def test_blocks_permissions_admin_query_failclosed_contract_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "permissions-admin-query-failclosed.json"
            payload = permissions_admin_query_failclosed_manifest()
            payload["public_sdk_ready"] = True
            payload["runtime_ready"] = True
            payload["nested_claim"] = {
                "public_sdk_ready": True,
                "runtime_ready": True,
                "promotion_ready": True,
                "promoted": True,
            }
            payload["claim_text"] = "public SDK ready runtime ready promoted"
            payload["future_public_surface"] = {
                "permission_groups": ["admin"],
                "command_router": "registered",
            }
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("public_sdk_ready_not_false", reasons)
        self.assertIn("runtime_ready_not_false", reasons)
        self.assertIn("public_sdk_ready_overclaim", reasons)
        self.assertIn("runtime_ready_overclaim", reasons)
        self.assertIn("promotion_ready_overclaim", reasons)
        self.assertIn("promoted_overclaim", reasons)
        self.assertIn("promoted_string_overclaim", reasons)
        self.assertIn("forbidden_surface_claim", reasons)

    def test_artifact_pack_revalidates_permissions_admin_query_nested_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "pack"
            pack.mkdir(parents=True)
            child = permissions_admin_query_failclosed_manifest()
            child["nested_claim"] = {"public_sdk_ready": True, "runtime_ready": True, "promoted": True}
            child["claim_text"] = "public SDK ready runtime ready promoted"
            write_json(pack / "permissions-admin-query-failclosed.json", child)
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-30T07:22:55Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("public_sdk_ready_overclaim", reasons)
        self.assertIn("runtime_ready_overclaim", reasons)
        self.assertIn("promoted_overclaim", reasons)
        self.assertIn("promoted_string_overclaim", reasons)

    def test_blocks_players_identity_principal_invalidation_policy_child_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-principal-invalidation-policy.json"
            payload = players_identity_principal_invalidation_policy_manifest()
            payload["principal"]["kind"] = "public_player_identity"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("principal_kind_not_copied_opaque", reasons)

    def test_blocks_players_identity_principal_invalidation_policy_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-principal-invalidation-policy.json"
            payload = players_identity_principal_invalidation_policy_manifest()
            payload["claim"] = "public SDK ready with runtime ready ResourceHandle lookup permissions commands mutation return override promoted"
            payload["nested_claim"] = {
                "public_sdk_ready": True,
                "runtime_ready": True,
                "lookup_ready": True,
                "promoted": True,
                "permissions_ready": True,
                "commands_ready": True,
                "mutation_ready": True,
                "return_override_ready": True,
            }
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("players_identity_principal_invalidation_policy_readiness_overclaim", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_public_sdk", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_runtime_ready", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_promoted", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_lookup", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_resourcehandle", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_permissions", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_commands", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_mutation", reasons)
        self.assertIn("players_identity_principal_invalidation_policy_public_overclaim_return_override", reasons)

    def test_blocks_players_identity_first_evidence_weak_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            payload = players_identity_first_evidence_manifest()
            payload["artifact_identity"] = {"path_redacted": True}
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("players_identity_first_evidence_artifact_identity_ark_sha_invalid", reasons)
        self.assertIn("players_identity_first_evidence_artifact_identity_obelisk_commit_invalid", reasons)
        self.assertIn("players_identity_first_evidence_artifact_identity_build_type_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_artifact_identity_source_ids_invalid", reasons)

    def test_blocks_players_identity_first_evidence_extra_artifact_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            payload = players_identity_first_evidence_manifest()
            payload["artifact_identity"].update(
                {
                    "artifact_kind": gate.PLAYERS_IDENTITY_FIRST_EVIDENCE_SCHEMA,
                    "artifact_sha256": "0" * 64,
                    "capture_id": "unspecified-capture",
                    "evidence_pack_id": "static-global-default-pack",
                }
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("players_identity_first_evidence_artifact_identity_fields_mismatch", reasons)

    def test_accepts_players_identity_first_evidence_multiple_complete_source_artifact_id_triples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            payload = players_identity_first_evidence_manifest()
            payload["artifact_identity"]["source_artifact_ids"] = [
                f"artifact_sha256:{'1' * 64}",
                "capture_id:primary-core",
                "evidence_pack_id:primary-pack",
                f"artifact_sha256:{'2' * 64}",
                "capture_id:admin-core",
                "evidence_pack_id:admin-pack",
            ]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

    def test_blocks_players_identity_first_evidence_mismatched_source_artifact_id_triples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            payload = players_identity_first_evidence_manifest()
            payload["artifact_identity"]["source_artifact_ids"].append(f"artifact_sha256:{'3' * 64}")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("blocked", result["status"])
        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("players_identity_first_evidence_artifact_identity_source_id_count_mismatch", reasons)

    def test_blocks_players_identity_first_evidence_overclaims_or_target_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            payload = players_identity_first_evidence_manifest(
                artifact_status="accepted",
                promotion_ready=True,
                public_sdk_ready=True,
                runtime_ready=True,
            )
            payload["readiness_classification"] = "release_readiness"
            payload["snapshot_root"] = str(workspace / "ufunction_snapshots")
            payload["generated_from"]["input_snapshots"] = payload["generated_from"]["input_snapshots"][:-1]
            payload["target_set_coverage"]["status"] = "partial"
            payload["lifecycle_anchors"]["session_start_accepted"] = True
            payload["lifecycle_anchors"]["accepted_start_targets"] = ["ShooterPlayerController.ServerListPlayers"]
            payload["privacy_policy"]["public_principal_ready"] = True
            payload["privacy_policy"]["copied_public_identifier"] = "SteamID"
            payload["promotion_gate"]["ready"] = True
            payload["promotion_gate"]["promotion_ready"] = True
            payload["safety_summary"]["target_count"] = 11
            payload["safety_summary"]["missing_target_count"] = 1
            payload["safety_summary"]["explicitly_excluded"] = ["raw_params"]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("players_identity_first_evidence_status_not_candidate_only", reasons)
        self.assertIn("players_identity_first_evidence_not_planning_only", reasons)
        self.assertIn("players_identity_first_evidence_promotion_ready_not_false", reasons)
        self.assertIn("players_identity_first_evidence_public_sdk_ready_not_false", reasons)
        self.assertIn("players_identity_first_evidence_runtime_ready_not_false", reasons)
        self.assertIn("players_identity_first_evidence_snapshot_root_not_redacted", reasons)
        self.assertIn("players_identity_first_evidence_input_snapshot_count_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_target_set_coverage_not_complete", reasons)
        self.assertIn("players_identity_first_evidence_lifecycle_anchor_overclaim", reasons)
        self.assertIn("players_identity_first_evidence_accepted_lifecycle_targets_present", reasons)
        self.assertIn("players_identity_first_evidence_public_principal_overclaim", reasons)
        self.assertIn("players_identity_first_evidence_promotion_gate_ready_not_false", reasons)
        self.assertIn("players_identity_first_evidence_target_count_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_missing_target_count_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_explicit_exclusions_missing_boundaries", reasons)

    def test_blocks_players_identity_first_evidence_empty_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            payload = players_identity_first_evidence_manifest()
            payload["targets"] = []
            payload["fields"] = []
            payload["copied_candidates"] = []
            payload["forced_redacted_fields"] = []
            payload["forbidden_fields"] = []
            payload["safety_summary"]["field_count"] = 0
            payload["safety_summary"]["forced_redacted_count"] = 0
            payload["safety_summary"]["forbidden_count"] = 0
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("players_identity_first_evidence_targets_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_field_count_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_forced_redacted_count_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_forbidden_count_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_target_set_emitted_targets_mismatch", reasons)

    def test_blocks_players_identity_first_evidence_status_only_coverage_and_nested_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            payload = players_identity_first_evidence_manifest()
            payload["target_set_coverage"] = {"status": "complete"}
            payload["privacy_policy"]["lookup_ready"] = True
            payload["promotion_gate"]["claim"] = "public SDK ready"
            payload["promotion_gate"]["blockers"].append("public API ready")
            payload["non_claims"] = payload["non_claims"][:-1]
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("players_identity_first_evidence_target_set_coverage_schema_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_readiness_overclaim", reasons)
        self.assertIn("players_identity_first_evidence_public_overclaim_public_sdk", reasons)
        self.assertIn("players_identity_first_evidence_public_overclaim_public_api", reasons)
        self.assertIn("players_identity_first_evidence_non_claims_missing_required_boundaries", reasons)

    def test_blocks_players_identity_first_evidence_declared_coverage_drift_and_nested_public_sdk_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "players-identity-first-evidence.json"
            payload = players_identity_first_evidence_manifest()
            declared = payload["target_set_coverage"]["declared_target_sets"][0]
            declared["source"] = "summary"
            declared["expected_targets"] = declared["expected_targets"][:-1]
            declared["covered_targets"] = declared["covered_targets"][:-1]
            declared["missing_targets"] = ["MissionType.BPOnPlayerRemovedFromMission"]
            declared["complete"] = False
            payload["target_set_coverage"]["complete"] = False
            payload["metadata"] = {"public_sdk_ready": True}
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("players_identity_first_evidence_declared_target_set_source_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_declared_target_set_expected_targets_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_declared_target_set_covered_targets_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_declared_target_set_missing_targets_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_declared_target_set_complete_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_target_set_coverage_complete_mismatch", reasons)
        self.assertIn("players_identity_first_evidence_readiness_overclaim", reasons)

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

    def test_accepts_fuobjectarray_field_window_redacted_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "field-window.json"
            write_json(manifest, fuobjectarray_field_window_redacted_manifest())

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[manifest],
                    expected_binary_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                )
            )

        self.assertEqual(result["blockers"], [])

    def test_blocks_fuobjectarray_field_window_redacted_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "field-window.json"
            write_json(manifest, fuobjectarray_field_window_redacted_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn("promote_mode_fuobjectarray_field_window_static_only", {blocker["reason"] for blocker in result["blockers"]})

    def test_blocks_fuobjectarray_field_window_redacted_shape_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "field-window.json"
            payload = fuobjectarray_field_window_redacted_manifest()
            payload["status"] = "accepted_public_gobjects"
            payload["binary"]["sha256"] = "0" * 64
            payload["binary"]["path_redacted"] = False
            payload["candidate"]["kind"] = "fname_root"
            payload["candidate"]["address_redacted"] = False
            payload["redaction"]["raw_disassembly"] = "included"
            payload["sources"]["ghidra_stdout"]["artifact_sha256"] = "not-a-sha"
            payload["fuobjectarray_window"]["same_base_flow"]["proven"] = False
            payload["fuobjectarray_window"]["required_fields"]["serial"]["relative_offset"] = "base+0x5c"
            payload["fuobjectarray_window"]["windows"] = [{"id": "static_init_caller"}]
            payload["builder_contract"]["candidate_static_contract_blocker_to_clear"] = "other"
            payload["builder_contract"]["promotion_gate_ready"] = True
            payload["builder_contract"]["consumption_scope"] = "public_sdk"
            write_json(manifest, payload)

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[manifest],
                    expected_binary_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                )
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("fuobjectarray_field_window_status_not_internal_static_evidence", reasons)
        self.assertIn("fuobjectarray_field_window_binary_sha256_mismatch", reasons)
        self.assertIn("fuobjectarray_field_window_binary_path_not_redacted", reasons)
        self.assertIn("fuobjectarray_field_window_candidate_not_gobjects", reasons)
        self.assertIn("fuobjectarray_field_window_candidate_address_not_redacted", reasons)
        self.assertIn("fuobjectarray_field_window_redaction_contract_mismatch", reasons)
        self.assertIn("fuobjectarray_field_window_source_sha256_invalid", reasons)
        self.assertIn("fuobjectarray_field_window_same_base_not_proven", reasons)
        self.assertIn("fuobjectarray_field_window_required_field_mismatch", reasons)
        self.assertIn("fuobjectarray_field_window_required_windows_missing", reasons)
        self.assertIn("fuobjectarray_field_window_blocker_contract_mismatch", reasons)
        self.assertIn("fuobjectarray_field_window_promotion_gate_ready_not_false", reasons)
        self.assertIn("fuobjectarray_field_window_consumption_scope_mismatch", reasons)

    def test_blocks_fuobjectarray_field_window_absolute_path_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "field-window.json"
            payload = fuobjectarray_field_window_redacted_manifest()
            payload["note"] = "/tmp/copied-field-window.json"
            write_json(manifest, payload)

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[manifest],
                    expected_binary_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                )
            )

        self.assertIn("fuobjectarray_field_window_absolute_path_string", {blocker["reason"] for blocker in result["blockers"]})

    def test_normalized_pack_accepts_static_field_window_child_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "static-field-window-pack-20260531T090000Z"
            pack.mkdir(parents=True)
            write_json(pack / "fuobjectarray-field-window.redacted.json", fuobjectarray_field_window_redacted_manifest())
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-31T09:00:00Z")

            result = gate.build_result(
                args(
                    root=workspace,
                    protected_root=protected,
                    manifests=[pack / artifact_pack.MANIFEST_NAME],
                    expected_binary_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                )
            )

        self.assertEqual(result["blockers"], [])

    def test_normalized_pack_blocks_gate_result_and_static_provenance_children(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "static-field-window-pack-20260531T090000Z"
            pack.mkdir(parents=True)
            write_json(
                pack / "static-global.consume-gate.json",
                {
                    "schema": gate.SCHEMA,
                    "root": "<offline-workspace>",
                    "protected_root": "<redacted>",
                    "mode": "consume",
                    "status": "accepted",
                    "manifests": [],
                    "artifacts": [],
                    "blockers": [],
                },
            )
            write_json(
                pack / "ShooterGameServer.objdump.provenance.json",
                {
                    "schema": gate.STATIC_ARTIFACT_PROVENANCE_SCHEMA,
                    "verified": True,
                    "path_redacted": True,
                    "binary_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    "artifact_sha256": "4" * 64,
                    "sidecar_sha256": "5" * 64,
                },
            )
            artifact_pack.normalize_pack(pack, pack.name, "2026-05-31T09:00:00Z")

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[pack / artifact_pack.MANIFEST_NAME]))

        reasons = [blocker["reason"] for blocker in result["blockers"]]
        self.assertEqual(2, reasons.count("unsupported_manifest_schema"))

    def test_accepts_resource_handle_revalidation_evaluator_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle.json"
            write_json(manifest, resource_handle_revalidation_evaluator_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_resource_handle_revalidation_missing_output_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle.json"
            payload = resource_handle_revalidation_evaluator_manifest()
            payload.pop("output_artifact_identity")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_revalidation_output_artifact_identity_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_revalidation_hashes_not_bound_to_output_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle.json"
            payload = resource_handle_revalidation_evaluator_manifest()
            payload["artifact_identity"]["hashes"].append("c" * 64)
            payload["artifact_identity"]["hash_count"] = 3
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "resource_handle_revalidation_output_artifact_identity_hash_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_resource_handle_revalidation_consume_ready_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "resource-handle.json"
            payload = resource_handle_revalidation_evaluator_manifest()
            payload["promotion_ready"] = True
            payload["public_resource_handle_ready"] = True
            payload["post_callback_resource_handle_ready"] = True
            payload["uobject_flags_validity_semantics_proven"] = True
            payload["evidence_checks"]["public_resource_handle_contract_present"] = True
            payload["evidence_checks"]["public_resourcehandle_policy_present"] = True
            payload["evidence_checks"]["runtime_rejection_samples_present"] = True
            payload["evidence_checks"]["runtime_serial_semantics_present"] = True
            payload["evidence_checks"]["runtime_resourcehandle_promotion_evidence_complete"] = True
            payload["evidence_checks"]["zero_serial_negative_samples_satisfy_runtime_rejection_samples"] = True
            payload["evidence_checks"]["zero_serial_negative_samples_satisfy_runtime_serial_semantics"] = True
            payload["offline_zero_serial_negative_samples_summary"]["candidate_only"] = False
            payload["offline_zero_serial_negative_samples_summary"]["does_not_satisfy_runtime_requirements"][0]["satisfied"] = True
            payload["promotion_gate"]["ready"] = True
            refresh_resource_handle_revalidation_output_identity(payload)
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("resource_handle_revalidation_consume_promotion_ready_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_consume_public_resourcehandle_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_consume_post_callback_ready_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_consume_flag_semantics_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_public_contract_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_public_policy_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_runtime_rejection_samples_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_runtime_serial_semantics_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_runtime_promotion_evidence_overclaim", reasons)
        self.assertIn("resource_handle_revalidation_zero_serial_runtime_rejection_substitution", reasons)
        self.assertIn("resource_handle_revalidation_zero_serial_runtime_serial_substitution", reasons)
        self.assertIn("resource_handle_revalidation_candidate_evidence_counted_as_public_lookup", reasons)
        self.assertIn("resource_handle_revalidation_zero_serial_summary_not_candidate_only", reasons)
        self.assertIn("resource_handle_revalidation_zero_serial_runtime_substitution", reasons)
        self.assertIn("resource_handle_revalidation_consume_promotion_gate_not_false", reasons)
        self.assertNotIn("resource_handle_revalidation_output_artifact_identity_hash_mismatch", reasons)

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
            paired_manifest = workspace / "runtime-serial-semantics.json"
            write_json(manifest, runtime_rejection_samples_manifest())
            write_json(paired_manifest, runtime_serial_semantics_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest, paired_manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_runtime_evidence_pair_half_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            write_json(manifest, runtime_rejection_samples_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        blockers = result["blockers"]
        self.assertIn("runtime_evidence_pair_missing", {blocker["reason"] for blocker in blockers})
        pair_blocker = next(blocker for blocker in blockers if blocker["reason"] == "runtime_evidence_pair_missing")
        self.assertEqual(
            pair_blocker["missing_schemas"],
            [gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA],
        )

    def test_blocks_runtime_evidence_pair_run_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            rejection_manifest = workspace / "runtime-rejection-samples.json"
            serial_manifest = workspace / "runtime-serial-semantics.json"
            rejection_payload = runtime_rejection_samples_manifest()
            serial_payload = runtime_serial_semantics_manifest()
            serial_payload["redacted_run_identity"]["marker_profile"] = "different-redacted-marker"
            serial_payload["redacted_run_identity"]["allowlist_label"] = "different-allowlist"
            attach_runtime_output_identity(
                serial_payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
                capture_id="runtime-serial-test",
                evidence_pack_id="runtime-serial-pack",
            )
            write_json(rejection_manifest, rejection_payload)
            write_json(serial_manifest, serial_payload)

            result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[rejection_manifest, serial_manifest])
            )

        pair_blocker = next(
            blocker for blocker in result["blockers"] if blocker["reason"] == "runtime_evidence_pair_run_identity_mismatch"
        )
        self.assertEqual(["allowlist_label", "marker_profile"], pair_blocker["fields"])

    def test_blocks_runtime_evidence_pair_source_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            rejection_manifest = workspace / "runtime-rejection-samples.json"
            serial_manifest = workspace / "runtime-serial-semantics.json"
            rejection_payload = runtime_rejection_samples_manifest()
            serial_payload = runtime_serial_semantics_manifest()
            serial_payload["source_artifacts"][0]["capture_id"] = "different-serial-policy-capture"
            serial_payload["source_artifacts"][0]["evidence_pack_id"] = "different-serial-policy-pack"
            attach_runtime_output_identity(
                serial_payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
                capture_id="runtime-serial-test",
                evidence_pack_id="runtime-serial-pack",
            )
            write_json(rejection_manifest, rejection_payload)
            write_json(serial_manifest, serial_payload)

            result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[rejection_manifest, serial_manifest])
            )

        pair_blocker = next(
            blocker for blocker in result["blockers"] if blocker["reason"] == "runtime_evidence_pair_source_identity_mismatch"
        )
        self.assertEqual(["capture_id", "evidence_pack_id"], pair_blocker["fields"])

    def test_blocks_runtime_evidence_pair_duplicate_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            rejection_manifest_a = workspace / "runtime-rejection-samples-a.json"
            rejection_manifest_b = workspace / "runtime-rejection-samples-b.json"
            serial_manifest = workspace / "runtime-serial-semantics.json"
            rejection_payload_b = runtime_rejection_samples_manifest()
            rejection_payload_b["rows"][0]["row_id"] = "reject-row-duplicate"
            attach_runtime_output_identity(
                rejection_payload_b,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA,
                capture_id="runtime-rejection-test",
                evidence_pack_id="runtime-rejection-pack",
            )
            write_json(rejection_manifest_a, runtime_rejection_samples_manifest())
            write_json(rejection_manifest_b, rejection_payload_b)
            write_json(serial_manifest, runtime_serial_semantics_manifest())

            result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[rejection_manifest_a, rejection_manifest_b, serial_manifest])
            )

        duplicate_blocker = next(
            blocker for blocker in result["blockers"] if blocker["reason"] == "runtime_evidence_pair_duplicate_schema"
        )
        self.assertEqual(gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA, duplicate_blocker["schema"])
        self.assertEqual(2, duplicate_blocker["count"])

    def test_blocks_runtime_evidence_pair_binary_sha256_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            rejection_manifest = workspace / "runtime-rejection-samples.json"
            serial_manifest = workspace / "runtime-serial-semantics.json"
            serial_payload = runtime_serial_semantics_manifest()
            serial_payload["binary_sha256"] = "f" * 64
            attach_runtime_output_identity(
                serial_payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
                capture_id="runtime-serial-test",
                evidence_pack_id="runtime-serial-pack",
            )
            write_json(rejection_manifest, runtime_rejection_samples_manifest())
            write_json(serial_manifest, serial_payload)

            result = gate.build_result(
                args(root=workspace, protected_root=protected, manifests=[rejection_manifest, serial_manifest])
            )

        self.assertIn(
            "runtime_evidence_pair_binary_sha256_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

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

    def test_blocks_runtime_rejection_samples_summary_acceptance_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            payload = runtime_rejection_samples_manifest()
            payload["summary"]["object_present_reject_rows"] = 2
            payload["summary"]["accepted_rows"] = 1
            attach_runtime_output_identity(
                payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA,
                capture_id="runtime-rejection-test",
                evidence_pack_id="runtime-rejection-pack",
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("runtime_rejection_samples_summary_object_present_reject_rows_mismatch", reasons)
        self.assertIn("runtime_rejection_samples_summary_accepted_rows_not_zero", reasons)

    def test_blocks_runtime_rejection_samples_unknown_top_level_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            payload = runtime_rejection_samples_manifest()
            payload["canonical_gap_note"] = "aggregate-only extension"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        blockers = result["blockers"]
        self.assertIn("runtime_rejection_samples_unexpected_top_level_field", {blocker["reason"] for blocker in blockers})
        blocker = next(blocker for blocker in blockers if blocker["reason"] == "runtime_rejection_samples_unexpected_top_level_field")
        self.assertEqual(blocker["fields"], ["canonical_gap_note"])

    def test_blocks_runtime_rejection_samples_incomplete_source_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            payload = runtime_rejection_samples_manifest()
            payload["source_artifacts"][0].pop("capture_id")
            payload["source_artifacts"][0]["evidence_pack_id"] = "../unsafe"
            payload["source_artifacts"][0]["operator_note"] = "not allowed"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("runtime_rejection_samples_source_capture_id_invalid", reasons)
        self.assertIn("runtime_rejection_samples_source_evidence_pack_id_invalid", reasons)
        self.assertIn("runtime_rejection_samples_source_unexpected_fields", reasons)

    def test_blocks_runtime_rejection_samples_missing_or_promoting_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            payload = runtime_rejection_samples_manifest()
            payload["runtime_evidence_preflight"]["promotion_evidence_complete"] = True
            payload["runtime_evidence_preflight"]["authorizes_runtime_work"] = True
            payload["runtime_evidence_preflight"]["paired_runtime_schema"] = gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA
            payload["runtime_evidence_preflight"]["offline_zero_serial_non_substitution_acknowledged"] = False
            attach_runtime_output_identity(
                payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA,
                capture_id="runtime-rejection-test",
                evidence_pack_id="runtime-rejection-pack",
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("runtime_rejection_samples_preflight_promotion_evidence_complete_not_false", reasons)
        self.assertIn("runtime_rejection_samples_preflight_authorizes_runtime_work_not_false", reasons)
        self.assertIn("runtime_rejection_samples_preflight_paired_runtime_schema_mismatch", reasons)
        self.assertIn("runtime_rejection_samples_preflight_offline_zero_serial_non_substitution_acknowledged_not_true", reasons)

    def test_blocks_runtime_rejection_samples_without_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-rejection-samples.json"
            payload = runtime_rejection_samples_manifest()
            payload.pop("runtime_evidence_preflight")
            attach_runtime_output_identity(
                payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_REJECTION_SAMPLES_SCHEMA,
                capture_id="runtime-rejection-test",
                evidence_pack_id="runtime-rejection-pack",
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "runtime_rejection_samples_preflight_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_accepts_runtime_serial_semantics_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            paired_manifest = workspace / "runtime-rejection-samples.json"
            manifest = workspace / "runtime-serial-semantics.json"
            write_json(paired_manifest, runtime_rejection_samples_manifest())
            write_json(manifest, runtime_serial_semantics_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[paired_manifest, manifest]))

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

    def test_blocks_runtime_serial_semantics_missing_lookup_identity_non_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-serial-semantics.json"
            payload = runtime_serial_semantics_manifest()
            payload["non_claims"].remove("does_not_promote_gobjects_lookup")
            payload["non_claims"].remove("does_not_promote_public_object_identity")
            attach_runtime_output_identity(
                payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
                capture_id="runtime-serial-test",
                evidence_pack_id="runtime-serial-pack",
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "runtime_serial_semantics_non_claims_missing",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_runtime_serial_semantics_unknown_top_level_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-serial-semantics.json"
            payload = runtime_serial_semantics_manifest()
            payload["canonical_gap_note"] = "aggregate-only extension"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        blockers = result["blockers"]
        self.assertIn("runtime_serial_semantics_unexpected_top_level_field", {blocker["reason"] for blocker in blockers})
        blocker = next(blocker for blocker in blockers if blocker["reason"] == "runtime_serial_semantics_unexpected_top_level_field")
        self.assertEqual(blocker["fields"], ["canonical_gap_note"])

    def test_blocks_runtime_serial_semantics_incomplete_source_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-serial-semantics.json"
            payload = runtime_serial_semantics_manifest()
            payload["source_artifacts"][0]["capture_id"] = "unsafe/path"
            payload["source_artifacts"][0].pop("evidence_pack_id")
            payload["source_artifacts"][0]["debug_path"] = "/tmp/source.json"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("runtime_serial_semantics_source_capture_id_invalid", reasons)
        self.assertIn("runtime_serial_semantics_source_evidence_pack_id_invalid", reasons)
        self.assertIn("runtime_serial_semantics_source_unexpected_fields", reasons)

    def test_blocks_runtime_serial_semantics_incomplete_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-serial-semantics.json"
            payload = runtime_serial_semantics_manifest()
            payload["runtime_evidence_preflight"]["scope"] = "promotion"
            payload["runtime_evidence_preflight"]["completion_rule"] = "single_manifest_complete"
            payload["runtime_evidence_preflight"]["paired_runtime_manifest_required"] = False
            payload["runtime_evidence_preflight"]["public_resource_handle_ready"] = True
            attach_runtime_output_identity(
                payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
                capture_id="runtime-serial-test",
                evidence_pack_id="runtime-serial-pack",
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("runtime_serial_semantics_preflight_scope_mismatch", reasons)
        self.assertIn("runtime_serial_semantics_preflight_completion_rule_mismatch", reasons)
        self.assertIn("runtime_serial_semantics_preflight_paired_runtime_manifest_required_not_true", reasons)
        self.assertIn("runtime_serial_semantics_preflight_public_resource_handle_ready_not_false", reasons)

    def test_blocks_runtime_serial_semantics_summary_negative_reject_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "runtime-serial-semantics.json"
            payload = runtime_serial_semantics_manifest()
            payload["summary"]["negative_reject_rows"] = 2
            attach_runtime_output_identity(
                payload,
                schema=gate.INTERNAL_UOBJECT_RUNTIME_SERIAL_SEMANTICS_SCHEMA,
                capture_id="runtime-serial-test",
                evidence_pack_id="runtime-serial-pack",
            )
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "runtime_serial_semantics_summary_negative_reject_rows_mismatch",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_accepts_zero_serial_negative_samples_for_consume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "zero-serial-negative-samples.json"
            write_json(manifest, zero_serial_negative_samples_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual(result["blockers"], [])

    def test_blocks_zero_serial_negative_samples_in_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "zero-serial-negative-samples.json"
            write_json(manifest, zero_serial_negative_samples_manifest())

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest], mode="promote"))

        self.assertIn(
            "promote_mode_zero_serial_negative_samples_candidate_only",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_blocks_zero_serial_negative_samples_path_leak_and_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "zero-serial-negative-samples.json"
            payload = zero_serial_negative_samples_manifest()
            payload["public_resource_handle_ready"] = True
            payload["sources"][0]["core_path_redacted"] = False
            payload["sources"][0]["core_path"] = "/servidor/ark/workspace-offline/core"
            payload["sources"][0]["zero_serial_negative_samples"][0]["item_dword_0x8"] = 17
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("zero_serial_negative_samples_public_resourcehandle_overclaim", reasons)
        self.assertIn("zero_serial_negative_samples_core_path_not_redacted", reasons)
        self.assertIn("zero_serial_negative_samples_source_unexpected_field", reasons)
        self.assertIn("zero_serial_negative_samples_core_path_field_present", reasons)
        self.assertIn("zero_serial_negative_samples_protected_path_string", reasons)
        self.assertIn("zero_serial_negative_samples_row_serial_not_zero", reasons)
        self.assertIn("zero_serial_negative_samples_output_artifact_identity_hash_mismatch", reasons)

    def test_blocks_zero_serial_negative_samples_nested_metadata_readiness_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "zero-serial-negative-samples.json"
            payload = zero_serial_negative_samples_manifest()
            payload["sources"][0]["metadata"]["publicResourceHandleReady"] = True
            payload["sources"][0]["metadata"]["lookup_note"] = "ResourceHandle lookup ready for public SDK"
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("zero_serial_negative_samples_metadata_ready_overclaim", reasons)
        self.assertIn("zero_serial_negative_samples_metadata_public_overclaim_resourcehandle", reasons)
        self.assertIn("zero_serial_negative_samples_output_artifact_identity_hash_mismatch", reasons)

    def test_blocks_zero_serial_negative_samples_missing_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            manifest = workspace / "zero-serial-negative-samples.json"
            payload = zero_serial_negative_samples_manifest()
            payload.pop("output_artifact_identity")
            write_json(manifest, payload)

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertIn(
            "zero_serial_negative_samples_output_artifact_identity_invalid",
            {blocker["reason"] for blocker in result["blockers"]},
        )

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

    def test_accepts_resource_handle_serial_scan_core_path_relative_to_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            pack = workspace / "serial-scan-pack"
            core = pack / "copied-core"
            core.parent.mkdir(parents=True)
            core.write_bytes(b"offline copied core fixture\n")
            manifest = pack / "resource-handle-serial-scan.json"
            write_json(
                manifest,
                resource_handle_serial_scan_manifest(
                    core_path="copied-core",
                    core_sha256=gate.sha256_file(core),
                ),
            )

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])

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
            "path_resolves_under_protected_root",
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

    def test_blocks_resource_handle_serial_scan_core_path_symlink_inside_workspace_without_hashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            target = workspace / "copied-core"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"offline copied core fixture\n")
            link = workspace / "core-link"
            link.symlink_to(target)
            manifest = workspace / "resource-handle-serial-scan.json"
            write_json(manifest, resource_handle_serial_scan_manifest(core_path=str(link), core_sha256="b" * 64))

            result = gate.build_result(args(root=workspace, protected_root=protected, manifests=[manifest]))

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("path_is_symlink", reasons)
        self.assertNotIn("resource_handle_serial_scan_core_sha256_mismatch", reasons)

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
