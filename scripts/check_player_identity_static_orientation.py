#!/usr/bin/env python3
"""Validate player-identity static orientation without promoting it as evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from reflection_target_sets import TARGET_SETS
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ORIENTATION = (
    REPO_ROOT / "docs" / "research" / "2026-05-31-player-identity-static-target-orientation.json"
)
REPORT_SCHEMA = "obelisk.player-identity-static-orientation-check.v1"
ORIENTATION_SCHEMA = "obelisk.player-identity-static-target-orientation.v1"
PLAYER_IDENTITY_TARGET_SET = "players-identity-lifecycle-intake"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
EXPECTED_REGISTRAR_CALL_VMA = "0x1ccc140"
HEX_RE = re.compile(r"^0x[0-9a-f]+$")
FORBIDDEN_PROMOTION_RE = re.compile(
    r"\b(?:accepted|callback|identity_resolved|mutation|promoted|public_sdk|"
    r"resource_handle|return_override|runtime_observed)\b",
    re.IGNORECASE,
)
REQUIRED_NON_CLAIMS = {
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
}
REQUIRED_BLOCKERS = {
    "requires_non_protected_core_evidence_pack",
    "requires_full_reflection_inventory_pack_for_players_identity_lifecycle_intake",
    "requires_exact_focal_snapshots_for_ServerListPlayers_and_ServerKickPlayer",
    "requires_principal_privacy_and_invalidation_policy_before_public_sdk_promotion",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate candidate-only player identity static orientation JSON."
    )
    parser.add_argument(
        "orientation_json",
        nargs="?",
        type=Path,
        default=DEFAULT_ORIENTATION,
        help="Path to player-identity static orientation JSON.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def expected_targets() -> set[str]:
    return {
        target.split(":", 1)[1]
        for target in TARGET_SETS[PLAYER_IDENTITY_TARGET_SET]
    }


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def read_payload(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]], Path | None]:
    blockers: list[dict[str, Any]] = []
    try:
        reject_symlink_component(path, "orientation_json")
        resolved = reject_protected_input_path(path, "orientation_json")
    except SystemExit as exc:
        append_blocker(blockers, "orientation_path_rejected", detail=str(exc), path=str(path))
        return None, blockers, None

    try:
        parsed = json.loads(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        append_blocker(blockers, "orientation_json_unreadable", detail=str(exc), path=str(resolved))
        return None, blockers, resolved
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "orientation_json_malformed", detail=str(exc), path=str(resolved))
        return None, blockers, resolved

    if not isinstance(parsed, dict):
        append_blocker(blockers, "orientation_json_not_object", path=str(resolved))
        return None, blockers, resolved
    return parsed, blockers, resolved


def validate_candidate(candidate: dict[str, Any], expected: set[str], blockers: list[dict[str, Any]]) -> None:
    target = candidate.get("target")
    if not isinstance(target, str) or target not in expected:
        append_blocker(blockers, "unexpected_candidate_target", target=target)
    if candidate.get("kind") != "ufunction_static_orientation":
        append_blocker(blockers, "candidate_kind_invalid", target=target, value=candidate.get("kind"))
    if candidate.get("status") != "candidate_only":
        append_blocker(blockers, "candidate_status_not_candidate_only", target=target, value=candidate.get("status"))
    if candidate.get("confidence") not in {"candidate", "clue"}:
        append_blocker(blockers, "candidate_confidence_invalid", target=target, value=candidate.get("confidence"))
    if candidate.get("registrar_call_vma") != EXPECTED_REGISTRAR_CALL_VMA:
        append_blocker(blockers, "candidate_registrar_call_vma_invalid", target=target, value=candidate.get("registrar_call_vma"))

    for key in ("class_slot", "string_file_offset", "string_vma", "registration_vma"):
        value = candidate.get(key)
        if not isinstance(value, str) or not HEX_RE.match(value):
            append_blocker(blockers, "candidate_hex_field_invalid", target=target, field=key, value=value)

    for key in ("xref_vmas", "thunk_candidates"):
        values = candidate.get(key)
        if not isinstance(values, list) or not values:
            append_blocker(blockers, "candidate_hex_list_missing", target=target, field=key)
            continue
        for value in values:
            if not isinstance(value, str) or not HEX_RE.match(value):
                append_blocker(blockers, "candidate_hex_list_value_invalid", target=target, field=key, value=value)

    registration_vma = candidate.get("registration_vma")
    xref_vmas = candidate.get("xref_vmas")
    if isinstance(registration_vma, str) and isinstance(xref_vmas, list) and registration_vma not in xref_vmas:
        append_blocker(blockers, "candidate_registration_vma_not_in_xrefs", target=target)

    if FORBIDDEN_PROMOTION_RE.search(json.dumps(candidate, sort_keys=True)):
        append_blocker(blockers, "candidate_contains_promotion_token", target=target)


def build_report(path: Path) -> dict[str, Any]:
    payload, blockers, resolved = read_payload(path)
    if payload is not None:
        if payload.get("schema") != ORIENTATION_SCHEMA:
            append_blocker(blockers, "schema_mismatch", value=payload.get("schema"))

        artifact_identity = payload.get("artifact_identity")
        if not isinstance(artifact_identity, dict):
            append_blocker(blockers, "artifact_identity_missing")
        else:
            source_note = artifact_identity.get("source_note")
            source_note_sha256 = artifact_identity.get("source_note_sha256")
            note_path = REPO_ROOT / source_note if isinstance(source_note, str) else None
            if note_path is None or not note_path.exists():
                append_blocker(blockers, "source_note_missing", value=source_note)
            else:
                digest = hashlib.sha256(note_path.read_bytes()).hexdigest()
                if source_note_sha256 != digest:
                    append_blocker(blockers, "source_note_sha256_mismatch", expected=digest, value=source_note_sha256)

        gate = payload.get("gate")
        if not isinstance(gate, dict):
            append_blocker(blockers, "gate_missing")
        else:
            if gate.get("mode") != "consume":
                append_blocker(blockers, "gate_mode_invalid", value=gate.get("mode"))
            if gate.get("status") != "candidate_blocked":
                append_blocker(blockers, "gate_status_invalid", value=gate.get("status"))
            if gate.get("promotion_ready") is not False:
                append_blocker(blockers, "gate_promotion_ready_not_false", value=gate.get("promotion_ready"))

        scope = payload.get("scope")
        if not isinstance(scope, dict):
            append_blocker(blockers, "scope_missing")
        else:
            if scope.get("binary_sha256") != EXPECTED_BINARY_SHA256:
                append_blocker(blockers, "binary_sha256_mismatch", value=scope.get("binary_sha256"))
            if scope.get("target_set") != PLAYER_IDENTITY_TARGET_SET:
                append_blocker(blockers, "target_set_mismatch", value=scope.get("target_set"))
            if not isinstance(scope.get("address_convention"), str):
                append_blocker(blockers, "address_convention_missing")

        expected = expected_targets()
        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            append_blocker(blockers, "candidates_missing")
        else:
            observed = {candidate.get("target") for candidate in candidates if isinstance(candidate, dict)}
            if observed != expected:
                append_blocker(
                    blockers,
                    "candidate_target_coverage_mismatch",
                    missing=sorted(expected - observed),
                    unexpected=sorted(target for target in observed - expected if isinstance(target, str)),
                )
            for candidate in candidates:
                if isinstance(candidate, dict):
                    validate_candidate(candidate, expected, blockers)
                else:
                    append_blocker(blockers, "candidate_not_object")

        non_claims = payload.get("non_claims")
        if not isinstance(non_claims, list):
            append_blocker(blockers, "non_claims_missing")
        else:
            missing = sorted(REQUIRED_NON_CLAIMS - set(non_claims))
            if missing:
                append_blocker(blockers, "required_non_claims_missing", missing=missing)

        blocker_values = payload.get("blockers")
        if not isinstance(blocker_values, list):
            append_blocker(blockers, "required_blockers_missing")
        else:
            missing = sorted(REQUIRED_BLOCKERS - set(blocker_values))
            if missing:
                append_blocker(blockers, "required_blockers_missing", missing=missing)

        if "public_sdk_ready" in payload or "runtime_ready" in payload:
            append_blocker(blockers, "orientation_payload_contains_readiness_overclaim")

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "valid" if valid else "blocked",
        "valid": valid,
        "accepted_for_orientation": valid,
        "not_artifact_gate": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "orientation_json": str(resolved if resolved is not None else path),
        "target_set": PLAYER_IDENTITY_TARGET_SET,
        "binary_sha256": EXPECTED_BINARY_SHA256,
        "blockers": blockers,
        "non_claims": [
            "valid orientation is candidate-only navigation evidence",
            "does not promote public identity, principal mapping, permissions, commands, runtime hooks, object lookup, mutation, return override, or SDK surface",
            "does not replace core evidence pack, reflection inventory pack, focal snapshots, second-source evidence, or lifecycle anchors",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.orientation_json)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
