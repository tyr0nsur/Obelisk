#!/usr/bin/env python3
"""Build a repo-local lifecycle-anchor static report without runtime evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import artifact_identity
import check_player_identity_lifecycle_anchor_candidates as lifecycle_checker
import check_player_identity_static_lifecycle_orientation as static_orientation
import protected_paths
from reflection_target_sets import (
    NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS,
    PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS,
    PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS,
    PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS,
    PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS,
    player_lifecycle_anchor_source_policy,
)


REPORT_SCHEMA = "obelisk.players-identity-lifecycle-anchor-static-report.v1"
ANCHOR_BINDING_TARGET_SET = lifecycle_checker.TARGET_SET
ANCHOR_BINDING_TARGET_SET_REVISION = lifecycle_checker.TARGET_SET_REVISION
TRIPLET_SOURCE_TARGET_SET = "players-lifecycle-anchor-candidates"
TRIPLET_SOURCE_TARGET_SET_REVISION = f"reflection_target_sets.py:{TRIPLET_SOURCE_TARGET_SET}"
TARGETS = (
    ("session_start", "ShooterGameMode.HandleNewPlayer"),
    ("session_end", "ShooterGameMode.OnLogout"),
)
TRIPLET_SOURCE_TARGETS = (
    ("session_start", "ShooterGameMode.HandleNewPlayer"),
    ("session_start_rejected", "ShooterGameMode.CheckJoinInProgress"),
    ("session_end", "ShooterGameMode.OnLogout"),
)
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
    "target_set": TRIPLET_SOURCE_TARGET_SET,
    "all_six_planning_gap_evidence_status": "non_evidence",
    "planning_gap_records_count_as_runtime_proof": False,
    "accepted_targets_fields_count_as_runtime_proof": False,
    "approved_runtime_evidence_present": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "promotion_ready": False,
    "does_not_satisfy": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
}
LOCAL_LAYOUT_CANDIDATE_TARGETS = {
    **lifecycle_checker.LIFECYCLE_LAYOUT_CANDIDATE_TARGETS,
    "ShooterGameMode.CheckJoinInProgress": {
        "role": "session_start_rejected",
        "num_parms": 3,
        "parms_size": 17,
        "fields": (
            ("bIsFromLogin", "BoolProperty", "0x0", 1),
            ("NewPlayer", "ObjectProperty", "0x8", 8),
            ("ReturnValue", "BoolProperty", "0x10", 1),
        ),
    },
}
NON_CLAIMS = [
    "repo-local static lifecycle-anchor report only",
    "does not fabricate runtime evidence or cite protected live-server paths",
    "CheckJoinInProgress is recorded only as the rejected-start triplet source, not as a lifecycle anchor binding",
    "bare CheckJoinInProgress without copied bool values bIsFromLogin,ReturnValue=1,0 is an alias and is not approved runtime triplet evidence",
    "does not prove runtime login/logout ordering, principal validity, or principal invalidation semantics",
    "does not expose public player identity, permissions, commands, economy, lookup, or moderation APIs",
    "does not expose UE pointers, raw params, FName/GObjects indices, ResourceHandle, mutation, or return overrides",
    "does not promote runtime readiness, public SDK readiness, release readiness, or v1 completion",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=Path("tests/fixtures/ufunction_snapshots"),
        help="Repo-local sanitized UFunction snapshot root.",
    )
    parser.add_argument(
        "--static-orientation-report",
        type=Path,
        help="Optional existing static orientation JSON report to hash and validate.",
    )
    parser.add_argument(
        "--static-binary",
        type=Path,
        help="Optional non-protected ShooterGameServer binary for bounded static orientation checks.",
    )
    parser.add_argument(
        "--expected-binary-sha256",
        default=static_orientation.EXPECTED_BINARY_SHA256,
        help="Expected ShooterGameServer SHA256 for --static-binary.",
    )
    parser.add_argument("--output", type=Path, help="Write the report to this path.")
    parser.add_argument("--json", action="store_true", help="Emit the report JSON to stdout.")
    return parser.parse_args()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_any_server_path(path: Path, label: str, *, output: bool = False) -> Path:
    protected_paths.reject_symlink_component(path, label)
    reject = protected_paths.reject_protected_output_path if output else protected_paths.reject_protected_input_path
    return reject(path, label, approved_roots=())


def load_json(path: Path, label: str) -> dict[str, Any]:
    resolved = reject_any_server_path(path, label)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{resolved}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{resolved}: top-level JSON must be an object")
    return payload


def snapshot_paths(snapshot_root: Path) -> dict[str, Path]:
    root = reject_any_server_path(snapshot_root, "snapshot-root")
    if not root.is_dir():
        raise SystemExit(f"snapshot-root is not a directory: {root}")
    manifest = load_json(root / "manifest.json", "snapshot manifest")
    if manifest.get("schema") != "obelisk.ufunction-snapshot-manifest.v1":
        raise SystemExit("snapshot manifest schema mismatch")
    sha_prefix = manifest.get("sha_prefix")
    targets = manifest.get("targets")
    if not isinstance(sha_prefix, str) or not sha_prefix:
        raise SystemExit("snapshot manifest sha_prefix missing")
    if not isinstance(targets, list):
        raise SystemExit("snapshot manifest targets must be a list")

    result: dict[str, Path] = {}
    for entry in targets:
        if not isinstance(entry, dict):
            continue
        outer = entry.get("outer")
        name = entry.get("name")
        module = entry.get("module")
        file_name = entry.get("file")
        if not all(isinstance(value, str) and value for value in (outer, name, module, file_name)):
            continue
        target = f"{outer}.{name}"
        if target in result:
            raise SystemExit(f"duplicate snapshot manifest target: {target}")
        path = reject_any_server_path(root / sha_prefix / module / file_name, f"snapshot:{target}")
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise SystemExit(f"snapshot:{target} resolves outside snapshot-root: {path}") from exc
        result[target] = path
    return result


def source_ids_from_evidence(evidence: dict[str, Any]) -> list[str]:
    source_ids: list[str] = []
    for key in ("artifact_sha256", "capture_id", "evidence_pack_id"):
        value = evidence.get(key)
        if not isinstance(value, str) or not value:
            raise SystemExit(f"snapshot evidence missing {key}")
        source_ids.append(f"{key}:{value}")
    return source_ids


def runtime_triplet_requirement_for_role(role: str) -> dict[str, Any]:
    requirement = dict(RUNTIME_TRIPLET_REQUIREMENT_BY_ROLE[role])
    requirement["source_name_only"] = True
    requirement["bare_source_alias_counts_as_runtime_evidence"] = False
    requirement["static_evidence_can_replace_runtime_triplet"] = False
    return requirement


def anchor_binding_status_for_role(role: str) -> str:
    if role == "session_start_rejected":
        return CHECKJOIN_REJECTED_START_BINDING_STATUS
    return STATIC_ANCHOR_BINDING_STATUS


def source_role_policy_for_target(role: str, target: str) -> dict[str, Any]:
    return {
        "source_policy_scope": "source_names_only_not_runtime_evidence",
        "runtime_evidence_status": PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS,
        "approved_runtime_triplet_source_name": target
        in PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS,
        "static_lifecycle_anchor_source_name": target in PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS,
        "rejected_start_triplet_source_name": role == "session_start_rejected",
        "chronology_guidance_only_non_anchor_source_name": target
        in PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS,
        "delegate_guidance_only_non_triplet_source_name": target
        in PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS,
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


def target_payload(snapshot: dict[str, Any], target: str) -> dict[str, Any]:
    if snapshot.get("schema") != lifecycle_checker.SNAPSHOT_SCHEMA:
        raise SystemExit(f"{target} snapshot schema mismatch")
    targets = snapshot.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"{target} snapshot must contain exactly one target")
    payload = targets[0]
    identity = payload.get("target")
    if not isinstance(identity, dict):
        raise SystemExit(f"{target} snapshot target identity missing")
    observed = f"{identity.get('outer_name')}.{identity.get('name')}"
    if observed != target:
        raise SystemExit(f"{target} snapshot target mismatch: observed {observed}")
    return payload


def expected_snapshot_record(role: str, target: str, path: Path) -> dict[str, Any]:
    snapshot = load_json(path, f"snapshot:{target}")
    payload = target_payload(snapshot, target)
    expected = LOCAL_LAYOUT_CANDIDATE_TARGETS[target]
    if payload.get("num_parms") != expected["num_parms"]:
        raise SystemExit(f"{target}: num_parms mismatch")
    if payload.get("parms_size") != expected["parms_size"]:
        raise SystemExit(f"{target}: parms_size mismatch")
    chain = payload.get("property_chain")
    properties = chain.get("properties") if isinstance(chain, dict) else None
    if not isinstance(properties, list):
        raise SystemExit(f"{target}: property chain missing")
    expected_fields = expected["fields"]
    if len(properties) != len(expected_fields):
        raise SystemExit(f"{target}: property count mismatch")

    fields: list[dict[str, Any]] = []
    for prop, expected_field in zip(properties, expected_fields):
        if not isinstance(prop, dict):
            raise SystemExit(f"{target}: property row malformed")
        expected_name, expected_class, expected_offset, expected_size = expected_field
        if prop.get("name") != expected_name:
            raise SystemExit(f"{target}: expected field {expected_name}, observed {prop.get('name')}")
        if prop.get("class_name") != expected_class:
            raise SystemExit(f"{target}.{expected_name}: property class mismatch")
        if prop.get("offset_internal") != int(str(expected_offset), 16):
            raise SystemExit(f"{target}.{expected_name}: offset mismatch")
        if prop.get("element_size") != expected_size:
            raise SystemExit(f"{target}.{expected_name}: element size mismatch")
        if prop.get("array_dim") != 1:
            raise SystemExit(f"{target}.{expected_name}: array_dim mismatch")
        if prop.get("membership_status") != "candidate-uobject":
            raise SystemExit(f"{target}.{expected_name}: membership status mismatch")
        fields.append(
            {
                "name": expected_name,
                "source_property_class": expected_class,
                "offset": expected_offset,
                "element_size": expected_size,
                "array_dim": 1,
                "classification": "recognition_only" if expected_class == "ObjectProperty" else "copied_candidate",
            }
        )

    evidence = snapshot.get("evidence")
    if not isinstance(evidence, dict):
        raise SystemExit(f"{target}: snapshot evidence missing")
    return {
        "target": target,
        "role": role,
        **runtime_triplet_requirement_for_role(role),
        **source_role_policy_for_target(role, target),
        "snapshot_sha256": sha256_file(path),
        "binary_sha256": evidence.get("ark_binary_sha256"),
        "snapshot_obelisk_commit": evidence.get("obelisk_commit"),
        "source_artifact_ids": source_ids_from_evidence(evidence),
        "num_parms": payload.get("num_parms"),
        "parms_size": payload.get("parms_size"),
        "property_order": [field["name"] for field in fields],
        "fields": fields,
        "acceptance_status": "layout_accepted_candidate_only",
    }


def validate_static_report(payload: dict[str, Any], *, expected_binary_sha256: str) -> list[str]:
    blockers: list[str] = []
    if payload.get("schema") != static_orientation.REPORT_SCHEMA:
        blockers.append("static_orientation_schema_mismatch")
    if payload.get("valid") is not True or payload.get("accepted_for_orientation") is not True:
        blockers.append("static_orientation_not_valid")
    if payload.get("accepted_lifecycle_anchors") is not False:
        blockers.append("static_orientation_accepted_lifecycle_anchors_not_false")
    if payload.get("not_artifact_gate") is not True:
        blockers.append("static_orientation_not_artifact_gate_not_true")
    if payload.get("binary_sha256") != expected_binary_sha256:
        blockers.append("static_orientation_binary_sha256_mismatch")
    if payload.get("target_set") != ANCHOR_BINDING_TARGET_SET:
        blockers.append("static_orientation_target_set_mismatch")
    for key in (
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "approved_runtime_lifecycle_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_lifecycle_evidence",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_lifecycle_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "counts_toward_complete_sdk_claim",
        "counts_toward_p0_dependency_chain",
        "counts_toward_p0_dependency_chain_claim",
        "public_readiness_ready",
    ):
        if payload.get(key) is not False:
            blockers.append(f"static_orientation_{key}_not_false")
    source_policy = payload.get("lifecycle_source_policy")
    if not isinstance(source_policy, dict):
        blockers.append("static_orientation_lifecycle_source_policy_missing")
    else:
        if source_policy.get("policy_scope") != "source_names_only_not_runtime_evidence":
            blockers.append("static_orientation_source_policy_scope_mismatch")
        if source_policy.get("runtime_triplet_evidence_status") != PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS:
            blockers.append("static_orientation_source_policy_runtime_status_mismatch")
        if source_policy.get("all_six_planning_gap_evidence_status") != "non_evidence":
            blockers.append("static_orientation_all_six_planning_gap_status_mismatch")
        for key in ("approved_runtime_evidence_present", "runtime_ready", "public_sdk_ready", "promotion_ready"):
            if source_policy.get(key) is not False:
                blockers.append(f"static_orientation_source_policy_{key}_not_false")
        if source_policy.get("static_lifecycle_anchor_sources") != list(PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS):
            blockers.append("static_orientation_source_policy_static_anchor_sources_mismatch")
        if source_policy.get("observer_rejected_start_sources") != ["ShooterGameMode.CheckJoinInProgress"]:
            blockers.append("static_orientation_source_policy_rejected_start_sources_mismatch")
    all_six_policy = payload.get("all_six_planning_gap_policy")
    if not isinstance(all_six_policy, dict):
        blockers.append("static_orientation_all_six_planning_gap_policy_missing")
    else:
        if all_six_policy.get("all_six_planning_gap_evidence_status") != "non_evidence":
            blockers.append("static_orientation_all_six_planning_gap_policy_status_mismatch")
        for key in (
            "planning_gap_records_count_as_runtime_proof",
            "accepted_targets_fields_count_as_runtime_proof",
            "approved_runtime_evidence_present",
            "runtime_ready",
            "public_sdk_ready",
            "promotion_ready",
        ):
            if all_six_policy.get(key) is not False:
                blockers.append(f"static_orientation_all_six_policy_{key}_not_false")
    checked = payload.get("checked_targets")
    checked_by_target = {row.get("target"): row for row in checked if isinstance(row, dict)} if isinstance(checked, list) else {}
    for role, target in TRIPLET_SOURCE_TARGETS:
        row = checked_by_target.get(target)
        required = RUNTIME_TRIPLET_REQUIREMENT_BY_ROLE[role]
        if not isinstance(row, dict):
            blockers.append(f"static_orientation_missing_target:{target}")
        elif row.get("status") != "candidate_orientation_valid":
            blockers.append(f"static_orientation_target_not_valid:{target}")
        else:
            if row.get("role_hint") != role:
                blockers.append(f"static_orientation_role_mismatch:{target}")
            if row.get("required_runtime_shape") != required["required_runtime_shape"]:
                blockers.append(f"static_orientation_required_runtime_shape_mismatch:{target}")
            if row.get("required_source_target") != target:
                blockers.append(f"static_orientation_required_source_target_mismatch:{target}")
            if row.get("static_evidence_can_replace_runtime_triplet") is not False:
                blockers.append(f"static_orientation_static_evidence_replaces_runtime_triplet:{target}")
            if row.get("bare_source_alias_counts_as_runtime_evidence") is not False:
                blockers.append(f"static_orientation_bare_alias_counts_as_runtime:{target}")
            if row.get("target_set_status") != "known_lifecycle_orientation_not_in_closed_target_set":
                blockers.append(f"static_orientation_target_set_status_mismatch:{target}")
            if row.get("source_policy_scope") != "source_names_only_not_runtime_evidence":
                blockers.append(f"static_orientation_source_policy_scope_mismatch:{target}")
            if row.get("runtime_evidence_status") != PLAYER_LIFECYCLE_RUNTIME_TRIPLET_EVIDENCE_STATUS:
                blockers.append(f"static_orientation_runtime_evidence_status_mismatch:{target}")
            if row.get("accepted_target_name_scope") != SOURCE_NAME_ONLY_STATUS:
                blockers.append(f"static_orientation_accepted_target_name_scope_mismatch:{target}")
            if row.get("anchor_binding_label_scope") != SOURCE_NAME_ONLY_STATUS:
                blockers.append(f"static_orientation_anchor_binding_label_scope_mismatch:{target}")
            for key in (
                "accepted_target_name_counts_as_runtime_proof",
                "anchor_binding_label_counts_as_runtime_proof",
                "counts_as_approved_runtime_lifecycle_evidence",
                "counts_as_approved_runtime_evidence",
                "counts_as_runtime_lifecycle_evidence",
                "counts_as_runtime_evidence",
                "counts_as_sdk_progress",
                "runtime_ready",
                "public_sdk_ready",
                "promotion_ready",
            ):
                if row.get(key) is not False:
                    blockers.append(f"static_orientation_row_{key}_not_false:{target}")
            if row.get("static_lifecycle_anchor_source_name") != (role != "session_start_rejected"):
                blockers.append(f"static_orientation_static_anchor_source_role_mismatch:{target}")
            if row.get("rejected_start_triplet_source_name") != (role == "session_start_rejected"):
                blockers.append(f"static_orientation_rejected_start_source_role_mismatch:{target}")
            expected_binding_status = anchor_binding_status_for_role(role)
            if row.get("anchor_binding_status") != expected_binding_status:
                blockers.append(f"static_orientation_anchor_binding_status_mismatch:{target}")
            if role == "session_start_rejected":
                if row.get("required_copied_bool_fields") != ["bIsFromLogin", "ReturnValue"]:
                    blockers.append("static_orientation_rejected_start_copied_bool_fields_mismatch")
                if row.get("required_copied_bool_values") != ["1", "0"]:
                    blockers.append("static_orientation_rejected_start_copied_bool_values_mismatch")
    triplet_requirement = payload.get("approved_runtime_triplet_requirement")
    if triplet_requirement != APPROVED_RUNTIME_TRIPLET_REQUIREMENT:
        blockers.append("static_orientation_approved_runtime_triplet_requirement_mismatch")
    return blockers


def static_evidence(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    if args.static_orientation_report is not None and args.static_binary is not None:
        raise SystemExit("--static-orientation-report and --static-binary are mutually exclusive")
    if args.static_orientation_report is not None:
        path = reject_any_server_path(args.static_orientation_report, "static-orientation-report")
        payload = load_json(path, "static-orientation-report")
        return payload, sha256_file(path), validate_static_report(payload, expected_binary_sha256=args.expected_binary_sha256)
    if args.static_binary is not None:
        binary = reject_any_server_path(args.static_binary, "static-binary")
        payload = static_orientation.validate_binary(binary, args.expected_binary_sha256)
        encoded = artifact_identity.canonical_json_bytes(payload)
        return payload, sha256_bytes(encoded), validate_static_report(payload, expected_binary_sha256=args.expected_binary_sha256)
    return None, None, ["static_orientation_report_missing"]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    paths = snapshot_paths(args.snapshot_root)
    targets: list[dict[str, Any]] = []
    for role, target in TRIPLET_SOURCE_TARGETS:
        path = paths.get(target)
        if path is None:
            raise SystemExit(f"snapshot manifest does not contain required lifecycle triplet source: {target}")
        targets.append(expected_snapshot_record(role, target, path))
    targets_by_name = {target["target"]: target for target in targets}

    static_payload, static_sha256, static_blockers = static_evidence(args)
    source_ids = targets[0]["source_artifact_ids"]
    source_id_mismatch = any(target["source_artifact_ids"] != source_ids for target in targets)
    binary_sha256 = targets[0]["binary_sha256"]
    binary_mismatch = any(target["binary_sha256"] != binary_sha256 for target in targets)
    obelisk_commit = targets[0]["snapshot_obelisk_commit"]
    commit_mismatch = any(target["snapshot_obelisk_commit"] != obelisk_commit for target in targets)

    blockers = list(static_blockers)
    if source_id_mismatch:
        blockers.append("snapshot_source_artifact_ids_mismatch")
    if binary_mismatch:
        blockers.append("snapshot_binary_sha256_mismatch")
    if commit_mismatch:
        blockers.append("snapshot_obelisk_commit_mismatch")
    if obelisk_commit in lifecycle_checker.PLACEHOLDER_OBELISK_COMMITS:
        blockers.append("snapshot_obelisk_commit_placeholder")

    ready = not blockers
    accepted_targets = [
        {
            "target": target["target"],
            "role": target["role"],
            "status": "static_accepted" if ready else "blocked",
            "source_snapshot_sha256": target["snapshot_sha256"],
            "source_binary_sha256": target["binary_sha256"],
            "source_artifact_ids": target["source_artifact_ids"],
            "num_parms": target["num_parms"],
            "parms_size": target["parms_size"],
            "property_order": target["property_order"],
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
            "static_evidence_can_replace_runtime_triplet": False,
        }
        for _, target_name in TARGETS
        for target in (targets_by_name[target_name],)
    ]
    accepted_triplet_sources = [
        {
            "target": target["target"],
            "role": target["role"],
            "status": "static_accepted_candidate_only" if ready else "blocked",
            "source_snapshot_sha256": target["snapshot_sha256"],
            "source_binary_sha256": target["binary_sha256"],
            "source_artifact_ids": target["source_artifact_ids"],
            "num_parms": target["num_parms"],
            "parms_size": target["parms_size"],
            "property_order": target["property_order"],
            "required_runtime_shape": target["required_runtime_shape"],
            "required_source_target": target["required_source_target"],
            "required_copied_bool_fields": target.get("required_copied_bool_fields", []),
            "required_copied_bool_values": target.get("required_copied_bool_values", []),
            "required_correlation_status": target.get("required_correlation_status"),
            "source_name_only": True,
            "bare_source_alias_counts_as_runtime_evidence": False,
            "static_evidence_can_replace_runtime_triplet": False,
            "target_set": TRIPLET_SOURCE_TARGET_SET,
            "anchor_binding_status": anchor_binding_status_for_role(target["role"]),
            **source_role_policy_for_target(target["role"], target["target"]),
        }
        for target in targets
    ]
    return {
        "schema": REPORT_SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "anchor_binding_target_set": ANCHOR_BINDING_TARGET_SET,
        "anchor_binding_target_set_revision": ANCHOR_BINDING_TARGET_SET_REVISION,
        "triplet_source_target_set": TRIPLET_SOURCE_TARGET_SET,
        "triplet_source_target_set_revision": TRIPLET_SOURCE_TARGET_SET_REVISION,
        "ready": ready,
        "accepted_for_lifecycle_anchor_binding": ready,
        "accepted_for_lifecycle_anchor_binding_scope": "static_source_binding_only_not_runtime_proof",
        "accepted_for_lifecycle_anchor_binding_counts_as_runtime_proof": False,
        "accepted_target_names_meaning": (
            "source-bound static labels only; not approved runtime evidence, SDK progress, "
            "or public readiness"
        ),
        "accepted_target_names_count_as_runtime_proof": False,
        "anchor_binding_labels_count_as_runtime_proof": False,
        "corroboration_status": "static_accepted" if ready else "blocked",
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
        "runtime_work_authorized": False,
        "server_operations_authorized": False,
        "artifact_identity": {
            "ark_binary_sha256": binary_sha256,
            "obelisk_commit": obelisk_commit,
            "build_type": "sanitized_snapshot_static_report",
            "target_set_revision": TRIPLET_SOURCE_TARGET_SET_REVISION,
            "anchor_binding_target_set": ANCHOR_BINDING_TARGET_SET,
            "anchor_binding_target_set_revision": ANCHOR_BINDING_TARGET_SET_REVISION,
            "triplet_source_target_set": TRIPLET_SOURCE_TARGET_SET,
            "triplet_source_target_set_revision": TRIPLET_SOURCE_TARGET_SET_REVISION,
            "source_artifact_ids": source_ids,
            "path_redacted": True,
        },
        "accepted_targets": accepted_targets,
        "accepted_triplet_sources": accepted_triplet_sources,
        "lifecycle_source_policy": player_lifecycle_anchor_source_policy(),
        "all_six_planning_gap_policy": ALL_SIX_PLANNING_GAP_POLICY,
        "required_runtime_triplet_sources": {
            "session_start": "ShooterGameMode.HandleNewPlayer",
            "session_start_rejected": "ShooterGameMode.CheckJoinInProgress(1,0)",
            "session_start_rejected_source": "ShooterGameMode.CheckJoinInProgress",
            "session_end": "ShooterGameMode.OnLogout",
            "evidence_boundary": "runtime copied sibling-set checker still required",
            "approved_runtime_evidence": False,
            "runtime_evidence_ready": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "bare_check_join_in_progress_alias_accepted": False,
            "static_evidence_can_replace_runtime_triplet": False,
        },
        "approved_runtime_triplet_requirement": APPROVED_RUNTIME_TRIPLET_REQUIREMENT,
        "static_orientation": {
            "provided": static_payload is not None,
            "schema": static_payload.get("schema") if isinstance(static_payload, dict) else None,
            "sha256": static_sha256,
            "accepted_for_orientation": static_payload.get("accepted_for_orientation") if isinstance(static_payload, dict) else False,
            "binary_sha256": static_payload.get("binary_sha256") if isinstance(static_payload, dict) else None,
        },
        "second_source_readiness": {
            "provided": False,
            "accepted": False,
            "reason": "not_supplied_for_this_static_report",
        },
        "blockers": sorted(set(blockers)),
        "non_claims": NON_CLAIMS,
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    resolved = reject_any_server_path(path, "output", output=True)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    protected_paths.reject_symlink_component(resolved.parent, "output parent")
    encoded = artifact_identity.canonical_json_bytes(payload) + b"\n"
    with tempfile.NamedTemporaryFile("wb", prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent, delete=False) as handle:
        temp_name = Path(handle.name)
        handle.write(encoded)
    temp_name.replace(resolved)


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.output is not None:
        atomic_write_json(args.output, report)
    if args.json or args.output is None:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
