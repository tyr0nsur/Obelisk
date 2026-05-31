#!/usr/bin/env python3
"""Validate candidate-only player identity lifecycle anchor artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reflection_target_sets import schema_target_list


SCHEMA = "obelisk.players-identity-lifecycle-anchor-candidates.v1"
REPORT_SCHEMA = "obelisk.players-identity-lifecycle-anchor-candidates-check.v1"
TARGET_SET = "players-identity-lifecycle-intake"
TARGET_SET_REVISION = "reflection_target_sets.py:players-identity-lifecycle-intake"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
TARGET_SET_TARGETS = set(schema_target_list(TARGET_SET, SNAPSHOT_SCHEMA))
KNOWN_LIFECYCLE_ORIENTATION_TARGETS = frozenset(
    (
        "ShooterGameMode.HandleNewPlayer",
        "ShooterGameMode.OnLogout",
    )
)
ADMIN_SNAPSHOT_TARGETS_NOT_LIFECYCLE_PROOF = frozenset(
    (
        "ShooterPlayerController.ServerKickPlayer",
        "ShooterPlayerController.ServerListPlayers",
    )
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
ROLE_TO_ACCEPTANCE_KEYS = {
    "session_start": ("session_start_accepted", "accepted_start_targets"),
    "session_end": ("session_end_accepted", "accepted_end_targets"),
}
ACCEPTED_STATUSES = {"layout_accepted_non_public"}
CORROBORATED_STATUSES = {"second_source_accepted", "static_accepted"}
REQUIRED_EXCLUSIONS = {
    "public_player_identity",
    "permissions",
    "commands",
    "economy",
    "lookup",
    "ResourceHandle",
    "mutation",
    "return_override",
    "runtime_hook_wiring",
    "ue_pointers",
    "raw_params",
    "fname_indices",
    "gobjects_indices",
    "identity_value_logging",
}
REQUIRED_NON_CLAIMS = {
    "candidate-only lifecycle anchor planning evidence",
    "does not expose public player identity, permissions, commands, economy, lookup, or moderation APIs",
    "does not expose UE pointers, raw params, FName/GObjects indices, ResourceHandle, mutation, or return overrides",
    "accepted layout anchors are non-public and do not prove principal invalidation semantics",
}
IDENTITY_FIELD_TOKENS = (
    "playerid",
    "steamid",
    "eosid",
    "uniquenetid",
    "netid",
    "accountid",
)
FORBIDDEN_COORDINATE_KEYS = {
    "name_index",
    "fname_index",
    "object_index",
    "gobject_index",
    "raw_param_address",
    "ue_pointer",
    "uobject_address",
    "function_address",
}


@dataclass
class ManifestValidation:
    blockers: list[dict[str, Any]]
    accepted_by_role: dict[str, list[str]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Lifecycle anchor candidate manifest to validate.")
    parser.add_argument("--promote", action="store_true", help="Run promote-mode checks; always blocks candidate-only artifacts.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: top-level JSON must be an object")
    return payload


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def has_forbidden_coordinate(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in FORBIDDEN_COORDINATE_KEYS:
                return key, child_trail
            found = has_forbidden_coordinate(child, child_trail)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = has_forbidden_coordinate(child, f"{trail}[{index}]")
            if found:
                return found
    return None


def validate_source_artifact_ids(value: Any, blockers: list[dict[str, Any]], label: str) -> None:
    if not isinstance(value, list):
        add(blockers, "artifact_identity_source_ids_invalid", label)
        return
    parsed: dict[str, list[str]] = {"artifact_sha256": [], "capture_id": [], "evidence_pack_id": []}
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, str) or ":" not in item:
            add(blockers, "artifact_identity_source_id_invalid", item_label)
            continue
        key, _, raw = item.partition(":")
        if key not in parsed:
            add(blockers, "artifact_identity_source_id_key_unknown", item_label)
            continue
        parsed[key].append(raw)
    for key, values in parsed.items():
        if len(values) != 1:
            add(blockers, "artifact_identity_source_id_count_mismatch", label, field=key, recorded_count=len(values))
            continue
        value = values[0]
        if key == "artifact_sha256":
            if SHA256_RE.fullmatch(value) is None:
                add(blockers, "artifact_identity_source_artifact_sha_invalid", label)
        elif SAFE_ID_RE.fullmatch(value) is None:
            add(blockers, "artifact_identity_source_artifact_id_invalid", label, field=key)


def validate_artifact_identity(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    identity = payload.get("artifact_identity")
    if not isinstance(identity, dict):
        add(blockers, "artifact_identity_missing", "$.artifact_identity")
        return
    expected_keys = {
        "ark_binary_sha256",
        "obelisk_commit",
        "build_type",
        "target_set_revision",
        "source_artifact_ids",
        "path_redacted",
    }
    if set(identity) != expected_keys:
        add(blockers, "artifact_identity_fields_mismatch", "$.artifact_identity")
    if not isinstance(identity.get("ark_binary_sha256"), str) or SHA256_RE.fullmatch(identity["ark_binary_sha256"]) is None:
        add(blockers, "artifact_identity_ark_sha_invalid", "$.artifact_identity.ark_binary_sha256")
    if not isinstance(identity.get("obelisk_commit"), str) or SAFE_ID_RE.fullmatch(identity["obelisk_commit"]) is None:
        add(blockers, "artifact_identity_obelisk_commit_invalid", "$.artifact_identity.obelisk_commit")
    if identity.get("build_type") not in {"offline_core", "static_analysis", "sanitized_snapshot"}:
        add(blockers, "artifact_identity_build_type_invalid", "$.artifact_identity.build_type")
    if identity.get("target_set_revision") != TARGET_SET_REVISION:
        add(blockers, "artifact_identity_target_set_revision_mismatch", "$.artifact_identity.target_set_revision")
    if identity.get("path_redacted") is not True:
        add(blockers, "artifact_identity_path_not_redacted", "$.artifact_identity.path_redacted")
    validate_source_artifact_ids(identity.get("source_artifact_ids"), blockers, "$.artifact_identity.source_artifact_ids")


def validate_field(field: Any, blockers: list[dict[str, Any]], label: str, *, accepted_anchor: bool) -> str | None:
    if not isinstance(field, dict):
        add(blockers, "anchor_field_invalid", label)
        return None
    name = field.get("name")
    property_class = field.get("source_property_class")
    classification = field.get("classification")
    eligibility = field.get("copied_scalar_eligibility")
    if not isinstance(name, str) or not name:
        add(blockers, "anchor_field_name_missing", f"{label}.name")
    if accepted_anchor and (not isinstance(property_class, str) or not property_class):
        add(blockers, "accepted_anchor_layout_evidence_missing", f"{label}.source_property_class")
    if accepted_anchor:
        for key in ("direction", "offset", "element_size", "array_dim"):
            if field.get(key) in (None, ""):
                add(blockers, "accepted_anchor_layout_evidence_missing", f"{label}.{key}")
    lowered_name = name.casefold() if isinstance(name, str) else ""
    if any(token in lowered_name for token in IDENTITY_FIELD_TOKENS):
        if classification not in {"identity_redacted", "recognition_only", "forbidden"}:
            add(blockers, "identity_field_not_redacted", label, field=name)
        if isinstance(eligibility, str) and ("public" in eligibility or "copied" in eligibility):
            add(blockers, "identity_field_copied_public_overclaim", label, field=name)
    return name if isinstance(name, str) and name else None


def validate_anchor(anchor: Any, blockers: list[dict[str, Any]], index: int) -> tuple[str | None, str | None, bool]:
    label = f"$.candidate_anchors[{index}]"
    if not isinstance(anchor, dict):
        add(blockers, "candidate_anchor_invalid", label)
        return None, None, False
    role = anchor.get("role")
    target = anchor.get("target")
    outer = anchor.get("outer")
    function = anchor.get("function")
    accepted = anchor.get("accepted") is True or anchor.get("acceptance_status") in ACCEPTED_STATUSES
    if role not in ROLE_TO_ACCEPTANCE_KEYS:
        add(blockers, "candidate_anchor_role_invalid", f"{label}.role")
    if not all(isinstance(value, str) and value for value in (target, outer, function)):
        add(blockers, "candidate_anchor_exact_target_missing", label)
    elif target != f"{outer}.{function}":
        add(blockers, "candidate_anchor_target_mismatch", label)
    elif target not in TARGET_SET_TARGETS:
        if target in KNOWN_LIFECYCLE_ORIENTATION_TARGETS:
            add(
                blockers,
                "candidate_anchor_known_lifecycle_orientation_not_accepted",
                label,
                target=target,
                orientation_status="static_orientation_only_not_in_closed_target_set",
            )
        else:
            add(blockers, "candidate_anchor_target_outside_closed_target_set", label, target=target)
    elif accepted and target in ADMIN_SNAPSHOT_TARGETS_NOT_LIFECYCLE_PROOF:
        add(
            blockers,
            "candidate_anchor_admin_snapshot_not_lifecycle_proof",
            label,
            target=target,
            snapshot_status="admin_surface_only_not_lifecycle_anchor",
        )
        accepted = False
    if accepted:
        for key in ("num_parms", "parms_size", "property_order"):
            value = anchor.get(key)
            if key == "property_order":
                if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
                    add(blockers, "accepted_anchor_layout_evidence_missing", f"{label}.{key}")
            elif not isinstance(value, int) or value < 0:
                add(blockers, "accepted_anchor_layout_evidence_missing", f"{label}.{key}")
        corroboration = anchor.get("corroboration")
        status = corroboration.get("status") if isinstance(corroboration, dict) else None
        if status not in CORROBORATED_STATUSES:
            add(blockers, "accepted_anchor_corroboration_missing", f"{label}.corroboration.status")
    evidence = anchor.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "candidate_anchor_evidence_missing", f"{label}.evidence")
    else:
        if evidence.get("snapshot_schema") != SNAPSHOT_SCHEMA:
            add(blockers, "candidate_anchor_snapshot_schema_mismatch", f"{label}.evidence.snapshot_schema")
        if not isinstance(evidence.get("source_snapshot_sha256"), str) or SHA256_RE.fullmatch(evidence["source_snapshot_sha256"]) is None:
            add(blockers, "candidate_anchor_snapshot_sha_invalid", f"{label}.evidence.source_snapshot_sha256")
        if not isinstance(evidence.get("binary_sha256"), str) or SHA256_RE.fullmatch(evidence["binary_sha256"]) is None:
            add(blockers, "candidate_anchor_binary_sha_invalid", f"{label}.evidence.binary_sha256")
    fields = anchor.get("fields")
    if not isinstance(fields, list):
        add(blockers, "candidate_anchor_fields_not_list", f"{label}.fields")
        fields = []
    field_names = [name for offset, field in enumerate(fields) if (name := validate_field(field, blockers, f"{label}.fields[{offset}]", accepted_anchor=accepted))]
    if accepted and anchor.get("property_order") != field_names:
        add(blockers, "accepted_anchor_property_order_mismatch", f"{label}.property_order")
    return role if isinstance(role, str) else None, target if isinstance(target, str) else None, accepted


def validate_manifest_details(payload: dict[str, Any], *, promote: bool = False) -> ManifestValidation:
    blockers: list[dict[str, Any]] = []
    accepted_by_role: dict[str, list[str]] = {"session_start": [], "session_end": []}
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
        return ManifestValidation(blockers, accepted_by_role)
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "status_not_candidate_only", "$.artifact_status")
    if payload.get("readiness_classification") != "planning_only":
        add(blockers, "readiness_classification_not_planning_only", "$.readiness_classification")
    if payload.get("input_target_set") != TARGET_SET:
        add(blockers, "input_target_set_mismatch", "$.input_target_set")
    if payload.get("snapshot_root") != "redacted":
        add(blockers, "snapshot_root_not_redacted", "$.snapshot_root")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")

    validate_artifact_identity(payload, blockers)

    anchors = payload.get("candidate_anchors")
    if not isinstance(anchors, list):
        add(blockers, "candidate_anchors_not_list", "$.candidate_anchors")
        anchors = []
    for index, anchor in enumerate(anchors):
        role, target, accepted = validate_anchor(anchor, blockers, index)
        if accepted and role in accepted_by_role and target:
            accepted_by_role[role].append(target)

    lifecycle = payload.get("lifecycle_acceptance")
    if not isinstance(lifecycle, dict):
        add(blockers, "lifecycle_acceptance_missing", "$.lifecycle_acceptance")
    else:
        for role, (accepted_key, targets_key) in ROLE_TO_ACCEPTANCE_KEYS.items():
            accepted_targets = sorted(accepted_by_role[role])
            if lifecycle.get(accepted_key) is not bool(accepted_targets):
                add(blockers, "lifecycle_acceptance_summary_mismatch", f"$.lifecycle_acceptance.{accepted_key}")
            if lifecycle.get(targets_key) != accepted_targets:
                add(blockers, "lifecycle_acceptance_targets_mismatch", f"$.lifecycle_acceptance.{targets_key}")

    principal = payload.get("principal_policy")
    if not isinstance(principal, dict):
        add(blockers, "principal_policy_missing", "$.principal_policy")
    else:
        if principal.get("public_principal_ready") is not False or principal.get("copied_public_identifier") is not None:
            add(blockers, "public_principal_overclaim", "$.principal_policy")
        if principal.get("invalidation_semantics") not in {"unresolved", "not_promoted"}:
            add(blockers, "principal_invalidation_semantics_overclaim", "$.principal_policy.invalidation_semantics")
        if principal.get("logging_policy") != "identity_values_not_logged":
            add(blockers, "principal_logging_policy_mismatch", "$.principal_policy.logging_policy")

    promotion_gate = payload.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        add(blockers, "promotion_gate_missing", "$.promotion_gate")
    else:
        if promotion_gate.get("ready") is not False or promotion_gate.get("promotion_ready") is not False:
            add(blockers, "promotion_gate_ready_not_false", "$.promotion_gate")

    safety = payload.get("safety_summary")
    if not isinstance(safety, dict):
        add(blockers, "safety_summary_missing", "$.safety_summary")
    else:
        if safety.get("candidate_anchor_count") != len(anchors):
            add(blockers, "safety_candidate_anchor_count_mismatch", "$.safety_summary.candidate_anchor_count")
        if safety.get("accepted_anchor_count") != sum(len(targets) for targets in accepted_by_role.values()):
            add(blockers, "safety_accepted_anchor_count_mismatch", "$.safety_summary.accepted_anchor_count")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
            if safety.get(key) is not False:
                add(blockers, f"safety_{key}_not_false", f"$.safety_summary.{key}")
        exclusions = safety.get("explicitly_excluded")
        if not isinstance(exclusions, list) or not REQUIRED_EXCLUSIONS.issubset(set(exclusions)):
            add(blockers, "explicit_exclusions_missing_required_boundaries", "$.safety_summary.explicitly_excluded")

    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        add(blockers, "non_claims_missing_required_boundaries", "$.non_claims")

    forbidden = has_forbidden_coordinate(payload)
    if forbidden is not None:
        key, trail = forbidden
        add(blockers, "path_or_coordinate_leakage", trail, field=key)
    if promote:
        add(blockers, "promote_mode_players_identity_lifecycle_anchor_candidates_candidate_only", "$")
    return ManifestValidation(blockers, {role: sorted(targets) for role, targets in accepted_by_role.items()})


def validate_manifest(payload: dict[str, Any], *, promote: bool = False) -> list[dict[str, Any]]:
    return validate_manifest_details(payload, promote=promote).blockers


def build_report(payload: dict[str, Any], validation: ManifestValidation, *, promote: bool) -> dict[str, Any]:
    accepted_start_targets = validation.accepted_by_role["session_start"]
    accepted_end_targets = validation.accepted_by_role["session_end"]
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema"),
        "mode": "promote" if promote else "consume",
        "ready": not validation.blockers,
        "candidate_only": payload.get("artifact_status") == "candidate_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "accepted_start_targets": accepted_start_targets,
        "accepted_end_targets": accepted_end_targets,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
    }


def main() -> int:
    args = parse_args()
    payload = load_json(args.manifest)
    validation = validate_manifest_details(payload, promote=args.promote)
    blockers = validation.blockers
    report = build_report(payload, validation, promote=args.promote)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
