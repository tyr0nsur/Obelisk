#!/usr/bin/env python3
"""Validate static lifecycle-anchor orientation for player identity without promotion."""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from check_player_identity_static_admin_thunks import (
    LoadSegment,
    append_blocker,
    call_target,
    parse_elf_load_segments,
    read_vma,
    segment_for_file_vma,
    segment_for_mem_vma,
    sha256_file,
)
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component
from reflection_target_sets import (
    NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS,
    PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS,
    PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS,
    player_lifecycle_anchor_source_policy,
)
from static_candidate_orientation_contract import build_contract, validate_contract


DEFAULT_BINARY = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/"
    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/"
    "ShooterGameServer"
)
REPORT_SCHEMA = "obelisk.player-identity-static-lifecycle-orientation-check.v1"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
TARGET_SET = "players-identity-lifecycle-intake"
REGISTRAR_CALL_VMA = 0x1CCC140
CLASS_SLOT_VMA = 0x58F2BD0
SCRIPT_NAME_VMA = 0x3F63B7C
GAMEMODE_NAME_VMA = 0x40E0B24


@dataclass(frozen=True)
class LifecycleAnchor:
    target: str
    role_hint: str
    ascii_name: str
    ascii_vma: int
    registration_vma: int
    registration_class_load_vma: int
    thunk_vma: int
    probable_fname_slot_vma: int


LIFECYCLE_ANCHORS = (
    LifecycleAnchor(
        target="ShooterGameMode.CheckJoinInProgress",
        role_hint="session_start_rejected",
        ascii_name="CheckJoinInProgress",
        ascii_vma=0x416FF3A,
        registration_vma=0x13CBC8F,
        registration_class_load_vma=0x13CBC88,
        thunk_vma=0x15CE900,
        probable_fname_slot_vma=0x58ED3C0,
    ),
    LifecycleAnchor(
        target="ShooterGameMode.HandleNewPlayer",
        role_hint="session_start",
        ascii_name="HandleNewPlayer",
        ascii_vma=0x4170122,
        registration_vma=0x13CC20A,
        registration_class_load_vma=0x13CC203,
        thunk_vma=0x15D04C0,
        probable_fname_slot_vma=0x58ED3D0,
    ),
    LifecycleAnchor(
        target="ShooterGameMode.OnLogout",
        role_hint="session_end",
        ascii_name="OnLogout",
        ascii_vma=0x417024F,
        registration_vma=0x13CC560,
        registration_class_load_vma=0x13CC559,
        thunk_vma=0x15D1500,
        probable_fname_slot_vma=0x58ED3E0,
    ),
)
LIFECYCLE_TARGETS = tuple(anchor.target for anchor in LIFECYCLE_ANCHORS)
RUNTIME_TRIPLET_REQUIREMENT_BY_ROLE: dict[str, dict[str, Any]] = {
    "session_start": {
        "required_runtime_shape": "ShooterGameMode.HandleNewPlayer(1,1)",
        "required_source_target": "ShooterGameMode.HandleNewPlayer",
        "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
        "required_copied_bool_values": ["1", "1"],
    },
    "session_start_rejected": {
        "required_runtime_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
        "required_source_target": "ShooterGameMode.CheckJoinInProgress",
        "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
        "required_copied_bool_values": ["1", "0"],
        "rejected_aliases": [
            "ShooterGameMode.CheckJoinInProgress",
            "CheckJoinInProgress",
        ],
    },
    "session_end": {
        "required_runtime_shape": "ShooterGameMode.OnLogout(matched)",
        "required_source_target": "ShooterGameMode.OnLogout",
        "required_correlation_status": "matched",
    },
}
APPROVED_RUNTIME_TRIPLET_REQUIREMENT: dict[str, Any] = {
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "static_evidence_can_replace_runtime_triplet": False,
    "required_exact_triplet": [
        RUNTIME_TRIPLET_REQUIREMENT_BY_ROLE["session_start"],
        RUNTIME_TRIPLET_REQUIREMENT_BY_ROLE["session_start_rejected"],
        RUNTIME_TRIPLET_REQUIREMENT_BY_ROLE["session_end"],
    ],
    "non_claim": (
        "static source orientation identifies source UFunctions only; approved runtime "
        "evidence still requires one copied session_start, exact CheckJoinInProgress(1,0) "
        "session_start_rejected, and matched session_end sibling set"
    ),
}
SOURCE_NAME_ONLY_STATUS = "source_name_only_not_runtime_evidence"
STATIC_ANCHOR_BINDING_STATUS = "static_anchor_source_name_only_not_runtime_evidence"
CHECKJOIN_REJECTED_START_BINDING_STATUS = "observer_only_rejected_start_source_not_anchor"
ALL_SIX_PLANNING_GAP_POLICY: dict[str, Any] = {
    "target_set": "players-lifecycle-anchor-candidates",
    "all_six_planning_gap_evidence_status": "non_evidence",
    "planning_gap_records_count_as_runtime_proof": False,
    "accepted_targets_fields_count_as_runtime_proof": False,
    "approved_runtime_evidence_present": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "promotion_ready": False,
    "does_not_satisfy": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
}
DIAGNOSTIC_REFLECTION_NOTE_GUARDRAILS: tuple[dict[str, Any], ...] = (
    {
        "source_phrase": "CheckJoinInProgressDiagnostic",
        "classification": "diagnostic_reflection_note_only",
        "approved_runtime_lifecycle_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_lifecycle_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_lifecycle_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "public_readiness_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
    },
    {
        "source_phrase": "FName drift notes",
        "classification": "reflection_drift_note_only",
        "approved_runtime_lifecycle_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_lifecycle_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_lifecycle_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "public_readiness_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Byte-check HandleNewPlayer/OnLogout static lifecycle-anchor orientation "
            "against an offline ShooterGameServer binary."
        )
    )
    parser.add_argument(
        "binary",
        nargs="?",
        type=Path,
        default=DEFAULT_BINARY,
        help="Offline ShooterGameServer path.",
    )
    parser.add_argument(
        "--expected-binary-sha256",
        default=EXPECTED_BINARY_SHA256,
        help="Expected SHA256 for the offline binary.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def check_load_segments(segments: list[LoadSegment], blockers: list[dict[str, Any]]) -> None:
    required_rx_vmas = [
        *(anchor.registration_class_load_vma for anchor in LIFECYCLE_ANCHORS),
        *(anchor.registration_vma for anchor in LIFECYCLE_ANCHORS),
        *(anchor.thunk_vma for anchor in LIFECYCLE_ANCHORS),
    ]
    required_ro_vmas = [
        SCRIPT_NAME_VMA,
        GAMEMODE_NAME_VMA,
        *(anchor.ascii_vma for anchor in LIFECYCLE_ANCHORS),
    ]
    required_bss_vmas = [CLASS_SLOT_VMA, *(anchor.probable_fname_slot_vma for anchor in LIFECYCLE_ANCHORS)]

    for vma in required_rx_vmas:
        segment = segment_for_file_vma(segments, vma)
        if segment is None or not segment.is_rx:
            append_blocker(blockers, "required_text_vma_not_in_rx_load", vma=hex(vma))
    for vma in required_ro_vmas:
        segment = segment_for_file_vma(segments, vma)
        if segment is None or not segment.is_readable:
            append_blocker(blockers, "required_rodata_vma_not_file_readable", vma=hex(vma))
    for vma in required_bss_vmas:
        segment = segment_for_mem_vma(segments, vma, 8)
        if segment is None or not segment.is_rw:
            append_blocker(blockers, "required_bss_slot_not_in_rw_load", vma=hex(vma))
            continue
        if segment.contains_file_vma(vma, 8):
            append_blocker(blockers, "required_bss_slot_is_file_backed", vma=hex(vma))


def check_ascii_string(
    data: bytes,
    segments: list[LoadSegment],
    anchor: LifecycleAnchor,
    blockers: list[dict[str, Any]],
) -> None:
    expected = anchor.ascii_name.encode("ascii") + b"\x00"
    actual = read_vma(data, segments, anchor.ascii_vma, len(expected))
    if actual != expected:
        append_blocker(
            blockers,
            "lifecycle_ascii_name_mismatch",
            target=anchor.target,
            vma=hex(anchor.ascii_vma),
        )


def check_class_load(
    data: bytes,
    segments: list[LoadSegment],
    anchor: LifecycleAnchor,
    blockers: list[dict[str, Any]],
) -> None:
    raw = read_vma(data, segments, anchor.registration_class_load_vma, 7)
    if raw is None or raw[:3] != b"\x48\x8b\x3d":
        append_blocker(
            blockers,
            "registration_class_load_opcode_mismatch",
            target=anchor.target,
            vma=hex(anchor.registration_class_load_vma),
        )
        return
    disp = struct.unpack("<i", raw[3:])[0]
    target = anchor.registration_class_load_vma + 7 + disp
    if target != CLASS_SLOT_VMA:
        append_blocker(
            blockers,
            "registration_class_slot_mismatch",
            target=anchor.target,
            expected=hex(CLASS_SLOT_VMA),
            value=hex(target),
        )


def check_registration(
    data: bytes,
    segments: list[LoadSegment],
    anchor: LifecycleAnchor,
    blockers: list[dict[str, Any]],
) -> None:
    raw = read_vma(data, segments, anchor.registration_vma, 17)
    if raw is None:
        append_blocker(blockers, "registration_window_unreadable", target=anchor.target)
        return
    if raw[0] != 0xBE or struct.unpack("<I", raw[1:5])[0] != anchor.ascii_vma:
        append_blocker(
            blockers,
            "registration_name_immediate_mismatch",
            target=anchor.target,
            expected=hex(anchor.ascii_vma),
        )
    if raw[5] != 0xBA or struct.unpack("<I", raw[6:10])[0] != anchor.thunk_vma:
        append_blocker(
            blockers,
            "registration_thunk_immediate_mismatch",
            target=anchor.target,
            expected=hex(anchor.thunk_vma),
        )
    if raw[10:12] != b"\x31\xc9":
        append_blocker(blockers, "registration_zero_flags_opcode_mismatch", target=anchor.target)
    if raw[12] != 0xE8:
        append_blocker(blockers, "registration_call_opcode_mismatch", target=anchor.target)
    elif call_target(data, segments, anchor.registration_vma + 12) != REGISTRAR_CALL_VMA:
        append_blocker(
            blockers,
            "registration_call_target_mismatch",
            target=anchor.target,
            expected=hex(REGISTRAR_CALL_VMA),
        )


def check_shared_names(data: bytes, segments: list[LoadSegment], blockers: list[dict[str, Any]]) -> None:
    expected_script = "/Script/ShooterGame".encode("utf-32-le") + b"\x00\x00\x00\x00"
    script = read_vma(data, segments, SCRIPT_NAME_VMA, len(expected_script))
    if script != expected_script:
        append_blocker(blockers, "script_name_utf32_mismatch", vma=hex(SCRIPT_NAME_VMA))
    expected_gamemode = "ShooterGameMode".encode("utf-32-le") + b"\x00\x00\x00\x00"
    gamemode = read_vma(data, segments, GAMEMODE_NAME_VMA, len(expected_gamemode))
    if gamemode != expected_gamemode:
        append_blocker(blockers, "gamemode_name_utf32_mismatch", vma=hex(GAMEMODE_NAME_VMA))


def runtime_triplet_requirement_for(anchor: LifecycleAnchor) -> dict[str, Any]:
    requirement = dict(RUNTIME_TRIPLET_REQUIREMENT_BY_ROLE[anchor.role_hint])
    requirement["source_name_only"] = True
    requirement["bare_source_alias_counts_as_runtime_evidence"] = False
    requirement["static_evidence_can_replace_runtime_triplet"] = False
    return requirement


def source_role_policy_for(anchor: LifecycleAnchor) -> dict[str, Any]:
    static_anchor = anchor.target in PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS
    rejected_start = anchor.role_hint == "session_start_rejected"
    return {
        "source_policy_scope": "source_names_only_not_runtime_evidence",
        "runtime_evidence_status": PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS,
        "accepted_runtime_triplet_source_name": anchor.target
        in PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS,
        "static_lifecycle_anchor_source_name": static_anchor,
        "rejected_start_triplet_source_name": rejected_start,
        "anchor_binding_status": CHECKJOIN_REJECTED_START_BINDING_STATUS
        if rejected_start
        else STATIC_ANCHOR_BINDING_STATUS,
        "accepted_target_name_scope": SOURCE_NAME_ONLY_STATUS,
        "anchor_binding_label_scope": SOURCE_NAME_ONLY_STATUS,
        "accepted_target_name_counts_as_runtime_proof": False,
        "anchor_binding_label_counts_as_runtime_proof": False,
        "counts_as_approved_runtime_lifecycle_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_lifecycle_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "promotion_ready": False,
    }


def validate_binary(path: Path, expected_sha256: str) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    resolved: Path | None = None
    binary_sha256: str | None = None
    checked_targets: list[dict[str, Any]] = []

    try:
        reject_symlink_component(path, "binary")
        resolved = reject_protected_input_path(path, "binary")
    except SystemExit as exc:
        append_blocker(blockers, "binary_path_rejected", path=str(path), detail=str(exc))
    else:
        try:
            data = resolved.read_bytes()
            binary_sha256 = sha256_file(resolved)
        except OSError as exc:
            append_blocker(blockers, "binary_unreadable", path=str(resolved), detail=str(exc))
            data = b""

        if binary_sha256 is not None and binary_sha256 != expected_sha256:
            append_blocker(
                blockers,
                "binary_sha256_mismatch",
                expected=expected_sha256,
                value=binary_sha256,
            )

        if data:
            segments = parse_elf_load_segments(data, blockers)
            check_load_segments(segments, blockers)
            check_shared_names(data, segments, blockers)
            for anchor in LIFECYCLE_ANCHORS:
                before = len(blockers)
                check_ascii_string(data, segments, anchor, blockers)
                check_class_load(data, segments, anchor, blockers)
                check_registration(data, segments, anchor, blockers)
                checked_targets.append(
                    {
                        "target": anchor.target,
                        "role_hint": anchor.role_hint,
                        **runtime_triplet_requirement_for(anchor),
                        **source_role_policy_for(anchor),
                        "status": "candidate_orientation_valid" if len(blockers) == before else "blocked",
                        "target_set_status": "known_lifecycle_orientation_not_in_closed_target_set",
                        "ascii_name_vma": hex(anchor.ascii_vma),
                        "registration_vma": hex(anchor.registration_vma),
                        "thunk_vma": hex(anchor.thunk_vma),
                        "class_slot_vma": hex(CLASS_SLOT_VMA),
                        "class_name_utf32_vma": hex(GAMEMODE_NAME_VMA),
                        "probable_fname_slot_vma": hex(anchor.probable_fname_slot_vma),
                    }
                )

    non_claims = [
        "valid static lifecycle orientation is bounded byte evidence for this offline binary only",
        "does not add HandleNewPlayer, CheckJoinInProgress, or OnLogout to the closed players-identity-lifecycle-intake target set",
        "CheckJoinInProgress is rejected-start orientation only and does not prove an accepted copied runtime event",
        "does not prove accepted session-start, rejected-start, or session-end lifecycle anchors",
        "CheckJoinInProgressDiagnostic wording is diagnostic/reflection-level wording only and does not prove approved runtime lifecycle evidence, SDK/P0 progress, or public readiness",
        "FName drift notes are reflection drift notes only and do not prove approved runtime lifecycle evidence, SDK/P0 progress, or public readiness",
        "does not prove UFunction object identity, FName indices, UProperty chains, parameter offsets, property order, field classes, or ParmsSize",
        "does not prove login/logout order, public principal validity, privacy-safe identity, or invalidation semantics",
        "does not replace core evidence, reflection inventory, sanitized snapshots, second-source evidence, runtime observation, or invalidation policy",
        "does not promote public identity, economy, runtime hooks, object lookup, ResourceHandle, or SDK surface",
        "does not promote permissions or commands",
        "does not promote mutation or return override",
        "does not accept HandleNewPlayer, CheckJoinInProgress, or OnLogout as lifecycle anchors without reviewed layout evidence",
    ]
    promotion_blockers = [
        "known_lifecycle_orientation_targets_not_in_closed_target_set",
        "requires_lifecycle_anchor_schema_update",
        "requires_reviewed_target_set_update_before_anchor_acceptance",
        "requires_sanitized_snapshots_for_lifecycle_targets",
        "requires_exact_outer_function_parms_size_property_order_and_field_classes",
        "requires_second_source_or_static_corroboration_for_layout",
        "requires_principal_privacy_and_invalidation_policy_before_public_sdk_promotion",
        "requires_non_protected_core_evidence_pack",
        "requires_full_reflection_inventory_pack_for_players_identity_lifecycle_intake",
        "check_join_in_progress_diagnostic_wording_is_not_approved_runtime_lifecycle_evidence",
        "fname_drift_notes_are_not_approved_runtime_lifecycle_evidence",
        "diagnostic_reflection_notes_do_not_count_toward_sdk_or_p0_progress",
        "diagnostic_reflection_notes_do_not_clear_public_readiness",
    ]
    static_contract = build_contract(
        topic="player_identity_lifecycle_orientation",
        binary_sha256=binary_sha256,
        target_set=TARGET_SET,
        expected_targets=LIFECYCLE_TARGETS,
        address_convention="non-PIE ELF VMA for this ARK Linux ShooterGameServer binary",
        subjects=[
            {
                "target": target.get("target"),
                "role_hint": target.get("role_hint"),
                "kind": "lifecycle_anchor_static_orientation",
                "status": "candidate_only"
                if target.get("status") == "candidate_orientation_valid"
                else target.get("status"),
                "ascii_name_vma": target.get("ascii_name_vma"),
                "registration_vma": target.get("registration_vma"),
                "thunk_vma": target.get("thunk_vma"),
                "class_slot_vma": target.get("class_slot_vma"),
                "class_name_utf32_vma": target.get("class_name_utf32_vma"),
                "probable_fname_slot_vma": target.get("probable_fname_slot_vma"),
                "target_set_status": target.get("target_set_status"),
            }
            for target in checked_targets
        ],
        non_claims=non_claims,
        blockers=promotion_blockers,
    )
    blockers.extend(validate_contract(static_contract))

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "valid" if valid else "blocked",
        "valid": valid,
        "accepted_for_orientation": valid,
        "accepted_lifecycle_anchors": False,
        "not_artifact_gate": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "approved_runtime_lifecycle_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_lifecycle_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_lifecycle_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "public_readiness_ready": False,
        "binary": str(resolved if resolved is not None else path),
        "binary_sha256": binary_sha256,
        "expected_binary_sha256": expected_sha256,
        "target_set": TARGET_SET,
        "checked_targets": checked_targets,
        "approved_runtime_triplet_requirement": APPROVED_RUNTIME_TRIPLET_REQUIREMENT,
        "lifecycle_source_policy": player_lifecycle_anchor_source_policy(),
        "all_six_planning_gap_policy": ALL_SIX_PLANNING_GAP_POLICY,
        "diagnostic_reflection_note_guardrails": list(DIAGNOSTIC_REFLECTION_NOTE_GUARDRAILS),
        "static_candidate_orientation_contract": static_contract,
        "blockers": blockers,
        "promotion_blockers": promotion_blockers,
        "non_claims": non_claims,
    }


def main() -> int:
    args = parse_args()
    report = validate_binary(args.binary, args.expected_binary_sha256)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
