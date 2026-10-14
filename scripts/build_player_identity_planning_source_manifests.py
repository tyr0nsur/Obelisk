#!/usr/bin/env python3
"""Build source-aligned player identity planning manifests offline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import bind_player_identity_planning_sources as binder
import build_redacted_ufunction_signatures
import check_player_identity_lifecycle_anchor_candidates as lifecycle_checker
import check_player_identity_principal_invalidation_policy as principal_checker
import protected_paths
from reflection_target_sets import (
    PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS,
    PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS,
    PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS,
    PLAYER_LIFECYCLE_REJECTED_START_SOURCE_TARGETS,
    PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS,
    schema_target_list,
    target_set_module_lane,
    target_set_readiness_classification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = "obelisk.player-identity-planning-source-manifests-build-report.v1"
FIRST_EVIDENCE_OUTPUT_NAME = "players-identity-first-evidence.json"
REPORT_OUTPUT_NAME = "player-identity-planning-source-manifests-report.json"
ALL_SIX_PLANNING_GAP_OUTPUT_NAME = "players-lifecycle-anchor-candidates-all-six-planning-gap.json"
FNAME_MISMATCH_OUTPUT_NAME = "players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json"
ALL_SIX_PLANNING_GAP_SCHEMA = "obelisk.players-lifecycle-anchor-candidates-all-six-planning-gap.v1"
FNAME_MISMATCH_SCHEMA = "obelisk.players-lifecycle-handle-new-player-fname-mismatch.v1"
ALL_SIX_PLANNING_GAP_TARGET_SET = "players-lifecycle-anchor-candidates"
FNAME_MISMATCH_PRIMARY_TARGET = "ShooterGameMode.HandleNewPlayer"
FNAME_MISMATCH_RELATED_TARGETS = ("ShooterGameMode.OnLogout",)
FNAME_MISMATCH_ALLOWED_TARGETS = (FNAME_MISMATCH_PRIMARY_TARGET, *FNAME_MISMATCH_RELATED_TARGETS)
ALL_SIX_REQUIRED_TARGETS = (
    "GameMode.K2_PostLogin",
    "ShooterGameMode.CheckJoinInProgress",
    "ShooterGameMode.HandleNewPlayer",
    "ShooterGameMode.OnLogout",
    "ShooterGameMode.OnPostLogin__DelegateSignature",
    "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
)
ALL_SIX_CURRENT_DURABLE_ANCHOR_TARGETS = [
    *PLAYER_LIFECYCLE_STATIC_ANCHOR_TARGETS,
]
ALL_SIX_APPROVED_TRIPLET_SOURCE_TARGETS = [
    *PLAYER_LIFECYCLE_APPROVED_TRIPLET_SOURCE_TARGETS,
]
ALL_SIX_REJECTED_START_SOURCE_TARGETS = [
    *PLAYER_LIFECYCLE_REJECTED_START_SOURCE_TARGETS,
]
ALL_SIX_CHRONOLOGY_ONLY_TARGETS = [
    *PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS,
]
ALL_SIX_GUIDANCE_ONLY_TARGETS = [
    *PLAYER_LIFECYCLE_CHRONOLOGY_ONLY_TARGETS,
    *PLAYER_LIFECYCLE_DELEGATE_GUIDANCE_ONLY_TARGETS,
]
ALL_SIX_REQUIRED_BLOCKER = "approved_runtime_evidence_missing"
ALL_SIX_TRIPLET_SOURCE_TARGETS_MEANING = (
    "source-name labels for the required runtime triplet only; not lifecycle anchor "
    "bindings, approved runtime evidence, or public SDK progress"
)
ALL_SIX_DURABLE_ANCHOR_TARGETS_MEANING = (
    "source-bound static lifecycle anchor bindings only; excludes CheckJoinInProgress "
    "and does not replace approved runtime triplet evidence"
)
ALL_SIX_HISTORICAL_ACCEPTED_TARGETS_MEANING = (
    "scratch comparison target count only; not durable second-source evidence, "
    "lifecycle anchor binding, approved runtime evidence, or public SDK progress"
)
ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY = {
    "role": "session_start_rejected",
    "target": "ShooterGameMode.CheckJoinInProgress",
    "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
    "required_copied_bool_values": ["1", "0"],
    "required_event_boundary": "post-original copied observer event accepted by analyzer/bundle/approved-checker chain",
    "disallowed_substitutes": [
        "ShooterGameMode.HandleNewPlayer rejected-start tuples",
        "passive snapshots",
        "diagnostic-only lines",
    ],
    "status": "exact_role_only",
}
ALL_SIX_FORBIDDEN_TRUE_FIELDS = frozenset(
    (
        "accepted_for_lifecycle_anchor_binding",
        "accepted_for_runtime_evidence",
        "accepted_for_second_source",
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "can_update_fixture_expectations",
        "counts_as_second_source_layout_evidence",
        "promotion_ready",
        "public_sdk_ready",
        "ready",
        "runtime_evidence_ready",
        "runtime_ready",
        "server_operations_authorized",
    )
)
FNAME_MISMATCH_FORBIDDEN_TRUE_FIELDS = frozenset(
    (
        "accepted_for_runtime_evidence",
        "accepted_for_second_source",
        "approved_runtime_evidence",
        "can_be_used_as_candidate_snapshot_root",
        "can_be_used_as_second_source_layout_evidence",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "layout_evidence_accepted",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "second_source_layout_evidence",
        "server_operations_authorized",
    )
)
DEFAULT_LIFECYCLE_STATIC_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-lifecycle-anchor-static-report.json"
)
LIFECYCLE_TARGETS = (
    ("session_start", "ShooterGameMode.HandleNewPlayer"),
    ("session_end", "ShooterGameMode.OnLogout"),
)
LIFECYCLE_TARGET_BY_NAME = {target: role for role, target in LIFECYCLE_TARGETS}
ADMIN_TARGETS_NOT_LIFECYCLE_ANCHORS = lifecycle_checker.ADMIN_SNAPSHOT_TARGETS_NOT_LIFECYCLE_PROOF
STATIC_REPORT_ARTIFACT_STATUS = "candidate_only"
STATIC_REPORT_READINESS_CLASSIFICATION = "planning_only"
STATIC_REPORT_BUILD_TYPE = "sanitized_snapshot_static_report"
STATIC_REPORT_TARGET_SET_REVISION = "reflection_target_sets.py:players-lifecycle-anchor-candidates"
STATIC_ORIENTATION_SCHEMA = "obelisk.player-identity-static-lifecycle-orientation-check.v1"
NON_CLAIMS = [
    "offline deterministic planning-manifest build only",
    "no runtime or server operation was performed",
    "no ARK process was started, stopped, restarted, attached, or observed",
    "no public player identity is promoted",
    "no permissions/admin, command response, or commands/replies surface is promoted",
    "no public SDK, public ABI, release, or v1 completion readiness is claimed",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=build_redacted_ufunction_signatures.DEFAULT_SNAPSHOT_ROOT,
        help="Sanitized UFunction snapshot root used for first-evidence and focal lifecycle snapshots.",
    )
    parser.add_argument("--output-dir", type=Path, help="Directory for generated planning manifests.")
    parser.add_argument(
        "--lifecycle-static-report",
        type=Path,
        default=DEFAULT_LIFECYCLE_STATIC_REPORT,
        help="Repo-local lifecycle-anchor static report used to bind accepted anchor provenance.",
    )
    parser.add_argument(
        "--verify-existing-dir",
        type=Path,
        help="Regenerate into a temporary directory and verify an existing planning-manifest directory is current.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the build report JSON to stdout.")
    args = parser.parse_args()
    if args.output_dir is None and args.verify_existing_dir is None:
        parser.error("one of --output-dir or --verify-existing-dir is required")
    if args.output_dir is not None and args.verify_existing_dir is not None:
        parser.error("--output-dir and --verify-existing-dir are mutually exclusive")
    return args


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duplicate_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def reject_duplicate_source_artifact_ids(source_ids: Any, *, label: str) -> None:
    if not isinstance(source_ids, list):
        return
    string_source_ids = [source_id for source_id in source_ids if isinstance(source_id, str)]
    duplicate_entries = duplicate_strings(string_source_ids)
    if duplicate_entries:
        raise SystemExit(f"{label} source_artifact_ids duplicate: " + ", ".join(duplicate_entries))

    values_by_kind: dict[str, list[str]] = {"artifact_sha256": [], "capture_id": [], "evidence_pack_id": []}
    for source_id in string_source_ids:
        key, separator, value = source_id.partition(":")
        if separator and key in values_by_kind:
            values_by_kind[key].append(value)
    for key, values in values_by_kind.items():
        duplicates = duplicate_strings(values)
        if duplicates:
            raise SystemExit(
                f"{label} source_artifact_ids duplicate {key}: "
                + ", ".join(duplicates)
            )


def load_json(path: Path, label: str) -> dict[str, Any]:
    protected_paths.reject_symlink_component(path, label)
    resolved = protected_paths.reject_protected_input_path(path, label)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{resolved}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{resolved}: top-level JSON must be an object")
    return payload


def safe_snapshot_root(path: Path) -> Path:
    protected_paths.reject_symlink_component(path, "snapshot-root")
    resolved = protected_paths.reject_protected_input_path(path, "snapshot-root")
    if not resolved.is_dir():
        raise SystemExit(f"snapshot-root is not a directory: {resolved}")
    return resolved


def safe_existing_dir(path: Path) -> Path:
    protected_paths.reject_symlink_component(path, "verify-existing-dir")
    resolved = protected_paths.reject_protected_input_path(path, "verify-existing-dir")
    if not resolved.is_dir():
        raise SystemExit(f"verify-existing-dir is not a directory: {resolved}")
    return resolved


def safe_optional_input_file(path: Path | None, label: str) -> Path | None:
    if path is None:
        return None
    protected_paths.reject_symlink_component(path, label)
    resolved = protected_paths.reject_protected_input_path(path, label)
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def manifest_target_paths(snapshot_root: Path) -> dict[str, Path]:
    manifest = load_json(snapshot_root / "manifest.json", "snapshot manifest")
    if manifest.get("schema") != "obelisk.ufunction-snapshot-manifest.v1":
        raise SystemExit("snapshot manifest schema mismatch")
    for key, expected in (("source", "offline_core"), ("status", "candidate-only")):
        if manifest.get(key) != expected:
            raise SystemExit(f"snapshot manifest {key} mismatch")
    if not isinstance(manifest.get("ark_binary_sha256"), str) or not manifest["ark_binary_sha256"]:
        raise SystemExit("snapshot manifest ark_binary_sha256 missing")
    sha_prefix = manifest.get("sha_prefix")
    targets = manifest.get("targets")
    if not isinstance(sha_prefix, str) or not sha_prefix:
        raise SystemExit("snapshot manifest sha_prefix missing")
    if not isinstance(targets, list):
        raise SystemExit("snapshot manifest targets must be a list")
    root = snapshot_root.resolve()
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
        path = snapshot_root / sha_prefix / module / file_name
        protected_paths.reject_symlink_component(path, f"snapshot-root:{target}")
        resolved = protected_paths.reject_protected_input_path(path, f"snapshot-root:{target}")
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise SystemExit(f"snapshot-root:{target} resolves outside snapshot-root: {resolved}") from exc
        result[target] = resolved
    return result


def lifecycle_static_report_hash(path: Path) -> str:
    return sha256_file(path)


def load_lifecycle_static_report(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None:
        return None, None
    payload = load_json(path, "lifecycle-static-report")
    if payload.get("schema") != "obelisk.players-identity-lifecycle-anchor-static-report.v1":
        raise SystemExit("lifecycle-static-report schema mismatch")
    if payload.get("artifact_status") != STATIC_REPORT_ARTIFACT_STATUS:
        raise SystemExit("lifecycle-static-report artifact_status mismatch")
    if payload.get("readiness_classification") != STATIC_REPORT_READINESS_CLASSIFICATION:
        raise SystemExit("lifecycle-static-report readiness classification mismatch")
    if payload.get("ready") is not True or payload.get("accepted_for_lifecycle_anchor_binding") is not True:
        raise SystemExit("lifecycle-static-report is not accepted for lifecycle anchor binding")
    if payload.get("corroboration_status") != "static_accepted":
        raise SystemExit("lifecycle-static-report corroboration status mismatch")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "runtime_work_authorized", "server_operations_authorized"):
        if payload.get(key) is not False:
            raise SystemExit(f"lifecycle-static-report {key} must be false")
    blockers = payload.get("blockers")
    if blockers != []:
        raise SystemExit("lifecycle-static-report blockers must be empty for accepted static binding")
    artifact_identity = payload.get("artifact_identity")
    if not isinstance(artifact_identity, dict):
        raise SystemExit("lifecycle-static-report artifact_identity missing")
    if artifact_identity.get("build_type") != STATIC_REPORT_BUILD_TYPE:
        raise SystemExit("lifecycle-static-report artifact_identity build_type mismatch")
    if artifact_identity.get("target_set_revision") != STATIC_REPORT_TARGET_SET_REVISION:
        raise SystemExit("lifecycle-static-report artifact_identity target_set_revision mismatch")
    if artifact_identity.get("path_redacted") is not True:
        raise SystemExit("lifecycle-static-report artifact_identity path_redacted must be true")
    if not isinstance(artifact_identity.get("ark_binary_sha256"), str) or lifecycle_checker.SHA256_RE.fullmatch(
        artifact_identity["ark_binary_sha256"]
    ) is None:
        raise SystemExit("lifecycle-static-report artifact_identity ark_binary_sha256 invalid")
    if not isinstance(artifact_identity.get("obelisk_commit"), str) or not artifact_identity["obelisk_commit"]:
        raise SystemExit("lifecycle-static-report artifact_identity obelisk_commit missing")
    source_ids = artifact_identity.get("source_artifact_ids")
    if not isinstance(source_ids, list) or not source_ids:
        raise SystemExit("lifecycle-static-report source_artifact_ids missing")
    source_id_blockers: list[dict[str, Any]] = []
    lifecycle_checker.validate_source_artifact_ids(
        source_ids,
        source_id_blockers,
        "$.artifact_identity.source_artifact_ids",
    )
    if source_id_blockers:
        raise SystemExit("lifecycle-static-report source_artifact_ids invalid")
    reject_duplicate_source_artifact_ids(source_ids, label="lifecycle-static-report")
    static_orientation = payload.get("static_orientation")
    if not isinstance(static_orientation, dict):
        raise SystemExit("lifecycle-static-report static_orientation missing")
    if static_orientation.get("provided") is not True:
        raise SystemExit("lifecycle-static-report static_orientation must be provided")
    if static_orientation.get("schema") != STATIC_ORIENTATION_SCHEMA:
        raise SystemExit("lifecycle-static-report static_orientation schema mismatch")
    if static_orientation.get("accepted_for_orientation") is not True:
        raise SystemExit("lifecycle-static-report static_orientation not accepted")
    if static_orientation.get("binary_sha256") != artifact_identity.get("ark_binary_sha256"):
        raise SystemExit("lifecycle-static-report static_orientation binary SHA mismatch")
    static_orientation_sha = static_orientation.get("sha256")
    if not isinstance(static_orientation_sha, str) or lifecycle_checker.SHA256_RE.fullmatch(static_orientation_sha) is None:
        raise SystemExit("lifecycle-static-report static_orientation sha256 invalid")
    accepted_targets = payload.get("accepted_targets")
    if not isinstance(accepted_targets, list):
        raise SystemExit("lifecycle-static-report accepted_targets must be a list")
    targets_by_name: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(accepted_targets):
        if not isinstance(entry, dict):
            raise SystemExit(f"lifecycle-static-report accepted_targets[{index}] must be an object")
        target = entry.get("target")
        if not isinstance(target, str) or not target:
            raise SystemExit(f"lifecycle-static-report accepted_targets[{index}].target missing")
        if target in targets_by_name:
            raise SystemExit(f"lifecycle-static-report duplicate accepted target: {target}")
        targets_by_name[target] = entry
    unexpected = sorted(target for target in targets_by_name if target not in LIFECYCLE_TARGET_BY_NAME)
    admin = [target for target in unexpected if target in ADMIN_TARGETS_NOT_LIFECYCLE_ANCHORS]
    if admin:
        raise SystemExit(
            "lifecycle-static-report uses admin target as lifecycle anchor: "
            + ", ".join(admin)
            + " (ServerListPlayers/ServerKickPlayer are admin targets, not lifecycle anchors)"
        )
    if unexpected:
        raise SystemExit(
            "lifecycle-static-report contains non-lifecycle accepted target: "
            + ", ".join(unexpected)
        )
    missing = [target for _, target in LIFECYCLE_TARGETS if target not in targets_by_name]
    if missing:
        raise SystemExit("lifecycle-static-report missing accepted lifecycle targets: " + ", ".join(missing))
    accepted_target_snapshot_shas: list[str] = []
    for role, target in LIFECYCLE_TARGETS:
        row = targets_by_name[target]
        expected = lifecycle_checker.LIFECYCLE_LAYOUT_CANDIDATE_TARGETS[target]
        if row.get("role") != role:
            raise SystemExit(f"lifecycle-static-report role mismatch for {target}")
        if row.get("status") != "static_accepted":
            raise SystemExit(f"lifecycle-static-report status mismatch for {target}")
        if not isinstance(row.get("source_snapshot_sha256"), str) or lifecycle_checker.SHA256_RE.fullmatch(
            row["source_snapshot_sha256"]
        ) is None:
            raise SystemExit(f"lifecycle-static-report source snapshot SHA invalid for {target}")
        accepted_target_snapshot_shas.append(row["source_snapshot_sha256"])
        if row.get("num_parms") != expected["num_parms"]:
            raise SystemExit(f"lifecycle-static-report num_parms mismatch for {target}")
        if row.get("parms_size") != expected["parms_size"]:
            raise SystemExit(f"lifecycle-static-report parms_size mismatch for {target}")
        if row.get("property_order") != [field[0] for field in expected["fields"]]:
            raise SystemExit(f"lifecycle-static-report property_order mismatch for {target}")
    duplicate_snapshot_shas = duplicate_strings(accepted_target_snapshot_shas)
    if duplicate_snapshot_shas:
        raise SystemExit(
            "lifecycle-static-report source snapshot SHA duplicate: "
            + ", ".join(duplicate_snapshot_shas)
        )
    return payload, lifecycle_static_report_hash(path)


def snapshot_target_payload(path: Path, target: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = load_json(path, f"{target} snapshot")
    if payload.get("schema") != lifecycle_checker.SNAPSHOT_SCHEMA:
        raise SystemExit(f"{target} snapshot schema mismatch")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"{target} snapshot must contain exactly one target")
    target_payload = targets[0]
    identity = target_payload.get("target")
    if not isinstance(identity, dict):
        raise SystemExit(f"{target} snapshot target identity missing")
    observed = f"{identity.get('outer_name')}.{identity.get('name')}"
    if observed != target:
        raise SystemExit(f"{target} snapshot target mismatch: observed {observed}")
    return payload, target_payload


def property_direction(name: str) -> str:
    if name == "ReturnValue":
        return "out"
    return "in"


def bool_masks(prop: dict[str, Any]) -> dict[str, str] | None:
    if prop.get("class_name") != "BoolProperty":
        return None
    byte_mask = prop.get("byte_mask", "0x1")
    field_mask = prop.get("field_mask", "0xff")
    if not isinstance(byte_mask, str) or not isinstance(field_mask, str):
        raise SystemExit("BoolProperty mask fields must be strings")
    return {"byte_mask": "0x01" if byte_mask == "0x1" else byte_mask, "field_mask": field_mask}


def lifecycle_field_from_property(prop: dict[str, Any], *, target: str, expected: tuple[Any, ...]) -> dict[str, Any]:
    expected_name, expected_class, expected_offset, expected_size = expected
    name = prop.get("name")
    property_class = prop.get("class_name")
    offset = prop.get("offset_internal")
    element_size = prop.get("element_size")
    array_dim = prop.get("array_dim")
    if name != expected_name:
        raise SystemExit(f"{target}: expected field {expected_name}, observed {name}")
    if property_class != expected_class:
        raise SystemExit(f"{target}.{name}: expected class {expected_class}, observed {property_class}")
    if offset != int(str(expected_offset), 16):
        raise SystemExit(f"{target}.{name}: expected offset {expected_offset}, observed {offset!r}")
    if element_size != expected_size:
        raise SystemExit(f"{target}.{name}: expected element_size {expected_size}, observed {element_size!r}")
    if array_dim != 1:
        raise SystemExit(f"{target}.{name}: expected array_dim 1, observed {array_dim!r}")
    if prop.get("status") != "candidate":
        raise SystemExit(f"{target}.{name}: property status must be candidate")

    entry = {
        "name": name,
        "source_property_class": property_class,
        "direction": property_direction(str(name)),
        "offset": expected_offset,
        "element_size": element_size,
        "array_dim": array_dim,
        "classification": "recognition_only" if property_class == "ObjectProperty" else "copied_candidate",
        "copied_scalar_eligibility": (
            "recognition_only_object" if property_class == "ObjectProperty" else "candidate_non_identity_scalar"
        ),
    }
    masks = bool_masks(prop)
    if masks is not None:
        entry["bool_masks"] = masks
    return entry


def lifecycle_anchor(
    *,
    role: str,
    target: str,
    snapshot_id: str,
    snapshot_path: Path,
    snapshot_payload: dict[str, Any],
    target_payload: dict[str, Any],
    static_report_sha256: str | None,
) -> dict[str, Any]:
    expected = lifecycle_checker.LIFECYCLE_LAYOUT_CANDIDATE_TARGETS[target]
    property_chain = target_payload.get("property_chain")
    properties = property_chain.get("properties") if isinstance(property_chain, dict) else None
    if not isinstance(properties, list):
        raise SystemExit(f"{target}: property_chain.properties missing")
    expected_fields = expected["fields"]
    if len(properties) != len(expected_fields):
        raise SystemExit(f"{target}: expected {len(expected_fields)} fields, observed {len(properties)}")
    if target_payload.get("num_parms") != expected["num_parms"]:
        raise SystemExit(f"{target}: num_parms mismatch")
    if target_payload.get("parms_size") != expected["parms_size"]:
        raise SystemExit(f"{target}: parms_size mismatch")

    outer, _, function = target.rpartition(".")
    evidence = snapshot_payload.get("evidence") if isinstance(snapshot_payload.get("evidence"), dict) else {}
    fields = [
        lifecycle_field_from_property(prop, target=target, expected=expected_field)
        for prop, expected_field in zip(properties, expected_fields)
    ]
    return {
        "role": role,
        "target": target,
        "outer": outer,
        "function": function,
        "acceptance_status": "layout_accepted_candidate_only",
        "accepted": True,
        "function_flags": target_payload.get("function_flags"),
        "num_parms": target_payload.get("num_parms"),
        "parms_size": target_payload.get("parms_size"),
        "return_value_offset": target_payload.get("return_value_offset", "0xffffffff"),
        "property_order": [field["name"] for field in fields],
        "fields": fields,
        "evidence": {
            "source_snapshot": snapshot_id,
            "source_snapshot_sha256": sha256_file(snapshot_path),
            "snapshot_schema": lifecycle_checker.SNAPSHOT_SCHEMA,
            "source_kind": "sanitized_snapshot",
            "binary_sha256": evidence.get("ark_binary_sha256"),
        },
        "corroboration": {
            "status": "static_accepted" if static_report_sha256 else "second_source_accepted",
            "second_source_report_sha256": None,
            "static_report_sha256": static_report_sha256,
        },
        "blockers": [],
    }


def validate_static_report_target_binding(
    *,
    lifecycle_static_report: dict[str, Any],
    role: str,
    target: str,
    snapshot_path: Path,
    snapshot_payload: dict[str, Any],
) -> None:
    accepted_targets = lifecycle_static_report.get("accepted_targets")
    rows = {
        entry.get("target"): entry for entry in accepted_targets if isinstance(entry, dict)
    } if isinstance(accepted_targets, list) else {}
    row = rows.get(target)
    if not isinstance(row, dict):
        raise SystemExit(f"lifecycle-static-report missing accepted lifecycle target: {target}")
    if row.get("role") != role or row.get("status") != "static_accepted":
        raise SystemExit(f"lifecycle-static-report target binding mismatch for {target}")
    expected_snapshot_sha = sha256_file(snapshot_path)
    if row.get("source_snapshot_sha256") != expected_snapshot_sha:
        raise SystemExit(f"lifecycle-static-report source snapshot SHA mismatch for {target}")

    static_identity = lifecycle_static_report.get("artifact_identity")
    static_binary_sha = static_identity.get("ark_binary_sha256") if isinstance(static_identity, dict) else None
    snapshot_evidence = snapshot_payload.get("evidence")
    snapshot_binary_sha = snapshot_evidence.get("ark_binary_sha256") if isinstance(snapshot_evidence, dict) else None
    if static_binary_sha != snapshot_binary_sha:
        raise SystemExit(f"lifecycle-static-report binary SHA mismatch for {target}")


def build_lifecycle_manifest(
    first_evidence: dict[str, Any],
    snapshot_root: Path,
    *,
    lifecycle_static_report: dict[str, Any] | None = None,
    lifecycle_static_report_sha256: str | None = None,
) -> dict[str, Any]:
    paths = manifest_target_paths(snapshot_root)
    anchors: list[dict[str, Any]] = []
    for index, (role, target) in enumerate(LIFECYCLE_TARGETS, start=1):
        path = paths.get(target)
        if path is None:
            raise SystemExit(f"snapshot manifest does not contain required lifecycle target: {target}")
        snapshot_payload, target_payload = snapshot_target_payload(path, target)
        if lifecycle_static_report is not None:
            validate_static_report_target_binding(
                lifecycle_static_report=lifecycle_static_report,
                role=role,
                target=target,
                snapshot_path=path,
                snapshot_payload=snapshot_payload,
            )
        anchors.append(
            lifecycle_anchor(
                role=role,
                target=target,
                snapshot_id=f"focal-snapshot-{index:04d}",
                snapshot_path=path,
                snapshot_payload=snapshot_payload,
                target_payload=target_payload,
                static_report_sha256=lifecycle_static_report_sha256,
            )
        )

    artifact = first_evidence.get("artifact_identity")
    if not isinstance(artifact, dict):
        raise SystemExit("first-evidence artifact_identity missing")
    static_identity = (
        lifecycle_static_report.get("artifact_identity")
        if isinstance(lifecycle_static_report, dict) and isinstance(lifecycle_static_report.get("artifact_identity"), dict)
        else None
    )
    source_artifact_ids = (
        list(static_identity.get("source_artifact_ids", []))
        if isinstance(static_identity, dict)
        else binder.first_evidence_readiness.first_evidence_source_artifact_ids(first_evidence)
    )
    if not source_artifact_ids:
        raise SystemExit("first-evidence artifact_identity.source_artifact_ids is empty")
    return {
        "schema": lifecycle_checker.SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "input_target_set": lifecycle_checker.TARGET_SET,
        "snapshot_root": "redacted",
        "artifact_identity": {
            "ark_binary_sha256": (
                static_identity.get("ark_binary_sha256") if isinstance(static_identity, dict) else artifact.get("ark_binary_sha256")
            ),
            "obelisk_commit": (
                static_identity.get("obelisk_commit") if isinstance(static_identity, dict) else artifact.get("obelisk_commit")
            ),
            "build_type": "sanitized_snapshot" if isinstance(static_identity, dict) else artifact.get("build_type"),
            "target_set_revision": lifecycle_checker.TARGET_SET_REVISION,
            "source_artifact_ids": source_artifact_ids,
            "path_redacted": True,
        },
        "candidate_anchors": anchors,
        "lifecycle_acceptance": {
            "session_start_accepted": True,
            "session_end_accepted": True,
            "accepted_start_targets": ["ShooterGameMode.HandleNewPlayer"],
            "accepted_end_targets": ["ShooterGameMode.OnLogout"],
            "blockers": ["principal_invalidation_semantics_unresolved"],
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
            "candidate_anchor_count": len(anchors),
            "accepted_anchor_count": len(anchors),
            "field_count": sum(len(anchor["fields"]) for anchor in anchors),
            "identity_redacted_field_count": 0,
            "copied_candidate_count": sum(
                1
                for anchor in anchors
                for field in anchor["fields"]
                if field["classification"] == "copied_candidate"
            ),
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": sorted(lifecycle_checker.REQUIRED_EXCLUSIONS),
        },
        "non_claims": sorted(lifecycle_checker.REQUIRED_NON_CLAIMS),
    }


def build_principal_manifest(lifecycle: dict[str, Any]) -> dict[str, Any]:
    source_binding = binder.expected_lifecycle_source_binding(lifecycle, {"artifact_identity": lifecycle["artifact_identity"]})
    return {
        "schema": principal_checker.SCHEMA,
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
            "source_binding": source_binding,
        },
        "principal": {
            "kind": "copied_opaque_principal",
            "copied": True,
            "ownership": "obelisk_owned_copy",
            "public_identity": "opaque_principal_only",
            "reversible": False,
            "stable_across_processes": False,
            "real_identity_source": None,
            "fields": [
                {
                    "name": "principal",
                    "type": "opaque_bytes",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "opaque_principal",
                },
                {
                    "name": "generation",
                    "type": "uint64",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "state",
                    "type": "enum",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "scope_flags",
                    "type": "uint64_flags",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "privacy_class",
                    "type": "enum",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
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
        "state": {"field": "state", "allowed": ["unknown", "active", "invalidated"], "fail_closed_states": ["unknown", "invalidated"]},
        "scope_flags": {
            "field": "scope_flags",
            "allowed_flags": ["process_local", "session_local", "not_cross_cluster"],
            "forbidden_flags": ["persistent", "cross_process", "cross_cluster"],
        },
        "privacy_class": {
            "field": "privacy_class",
            "allowed": ["opaque_principal", "internal_sensitive", "redacted"],
            "public_value": "opaque_principal",
        },
        "invalidation_cases": [
            {
                "case": "logout_or_disconnect",
                "trigger": "ShooterGameMode.OnLogout",
                "generation_action": "increment_or_retire",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "reconnect_after_invalidation",
                "trigger": "new_session_after_invalidated_principal",
                "generation_action": "allocate_new_generation",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "transfer_or_download_edge",
                "trigger": "transfer_download_without_promoted_identity_continuity",
                "generation_action": "retire_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "stale_controller_or_player_state",
                "trigger": "controller_or_player_state_replaced",
                "generation_action": "invalidate_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "duplicate_or_conflicting_identity",
                "trigger": "conflicting_candidate_identity_evidence",
                "generation_action": "invalidate_conflict_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "server_restart",
                "trigger": "process_restart_boundary",
                "generation_action": "invalidate_all_prior_generations",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "plugin_reload",
                "trigger": "plugin_owner_cleanup_or_reload",
                "generation_action": "deny_cached_plugin_values",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "trigger": "unsupported_or_malformed_identity_input",
                "generation_action": "clear_output_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
        ],
        "negative_consumer_rules": [
            {"rule": "no_real_identity_public", "forbids": ["SteamID", "EOSID", "UniqueNetId", "PlayerID", "PlayerDataID", "PlayerName", "IPAddress", "TribeID"], "fail_closed": True},
            {"rule": "no_ue_pointer_or_handle_identity", "forbids": ["ResourceHandle", "GObjects", "FNames", "UObjectPointer"], "fail_closed": True},
            {"rule": "no_lookup_or_persistence_from_principal", "forbids": ["lookup", "persistent_identity", "cross_process_identity"], "fail_closed": True},
            {"rule": "no_return_override_or_mutation_authority", "forbids": ["return_override", "mutation"], "fail_closed": True},
            {"rule": "no_commands_or_permissions_claims", "forbids": ["commands", "permissions"], "fail_closed": True},
            {"rule": "fail_closed_on_invalid_or_stale", "forbids": ["fallback_to_real_id", "best_effort_lookup"], "fail_closed": True},
        ],
        "rejected_public_identity_sources": sorted(principal_checker.REQUIRED_REJECTED_PUBLIC_IDENTITY_SOURCES),
        "evidence_policy": {
            "accepted_evidence_class": "candidate_policy_only",
            "malformed_evidence_result": "deny",
            "unsupported_evidence_result": "deny",
            "fail_closed": True,
        },
        "runtime_evidence": {
            "status": "not_approved",
            "approved": False,
            "required_for": ["promote", "public_readiness", "runtime_readiness"],
        },
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "approved_runtime_evidence_missing",
                "principal_invalidation_semantics_unresolved",
                "candidate_only_policy",
            ],
        },
        "safety_summary": {
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": sorted(principal_checker.REQUIRED_EXCLUSIONS),
        },
        "non_claims": sorted(principal_checker.REQUIRED_NON_CLAIMS),
    }


def validation_reasons(blockers: list[dict[str, Any]]) -> list[str]:
    return [str(blocker.get("reason")) for blocker in blockers]


def add_all_six_blocker(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def validate_all_six_exact_rejected_start_role_policy(
    policy: Any,
    blockers: list[dict[str, Any]],
    label: str,
) -> None:
    if policy != ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY:
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_exact_rejected_start_role_policy_mismatch",
            label,
            expected=ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY,
            actual=policy,
        )


def repo_relative_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def snapshot_target_summary(path: Path, target: str) -> dict[str, Any]:
    payload, target_payload = snapshot_target_payload(path, target)
    property_chain = target_payload.get("property_chain")
    properties = property_chain.get("properties") if isinstance(property_chain, dict) else None
    if not isinstance(properties, list):
        raise SystemExit(f"{target}: property_chain.properties missing")
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}
    return {
        "ark_binary_sha256": evidence.get("ark_binary_sha256"),
        "base_fixture_path": repo_relative_path(path),
        "base_fixture_sha256": sha256_file(path),
        "num_parms": target_payload.get("num_parms"),
        "parms_size": target_payload.get("parms_size"),
        "property_order": [prop.get("name") for prop in properties if isinstance(prop, dict)],
        "property_name_indices": [prop.get("name_index") for prop in properties if isinstance(prop, dict)],
    }


def validate_all_six_catalog_binding(blockers: list[dict[str, Any]]) -> None:
    try:
        catalog_targets = schema_target_list(ALL_SIX_PLANNING_GAP_TARGET_SET, lifecycle_checker.SNAPSHOT_SCHEMA)
    except KeyError:
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_catalog_target_set_missing",
            "$.target_set",
            target_set=ALL_SIX_PLANNING_GAP_TARGET_SET,
        )
        return

    if catalog_targets != list(ALL_SIX_REQUIRED_TARGETS):
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_catalog_targets_mismatch",
            "reflection_target_sets.py:players-lifecycle-anchor-candidates",
            expected=list(ALL_SIX_REQUIRED_TARGETS),
            actual=catalog_targets,
        )
    try:
        module_lane = target_set_module_lane(ALL_SIX_PLANNING_GAP_TARGET_SET)
    except KeyError:
        module_lane = None
    if module_lane != "players_lifecycle":
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_catalog_module_lane_mismatch",
            "reflection_target_sets.py:TARGET_SET_MODULE_LANES",
            actual=module_lane,
        )
    try:
        readiness_classification = target_set_readiness_classification(ALL_SIX_PLANNING_GAP_TARGET_SET)
    except KeyError:
        readiness_classification = None
    if readiness_classification != "planning_only":
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_catalog_readiness_classification_mismatch",
            "reflection_target_sets.py:PLANNING_ONLY_TARGET_SETS",
            actual=readiness_classification,
        )


def validate_all_six_base_fixture_binding(
    artifact: dict[str, Any],
    blockers: list[dict[str, Any]],
    snapshot_root: Path,
) -> None:
    paths = manifest_target_paths(snapshot_root)
    manifest = load_json(snapshot_root / "manifest.json", "snapshot manifest")
    identity = artifact.get("artifact_identity") if isinstance(artifact.get("artifact_identity"), dict) else {}
    manifest_binary_sha = manifest.get("ark_binary_sha256")
    if identity.get("ark_binary_sha256") != manifest_binary_sha:
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_manifest_binary_sha_mismatch",
            "$.artifact_identity.ark_binary_sha256",
            expected=manifest_binary_sha,
            actual=identity.get("ark_binary_sha256"),
        )

    targets = artifact.get("base_fixture_targets")
    if not isinstance(targets, list):
        return

    entries_by_target: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(targets):
        if not isinstance(entry, dict):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_base_fixture_target_entry_invalid",
                f"$.base_fixture_targets[{index}]",
            )
            continue
        target = entry.get("target")
        if not isinstance(target, str) or not target:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_base_fixture_target_name_missing",
                f"$.base_fixture_targets[{index}].target",
            )
            continue
        if target in entries_by_target:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_base_fixture_target_duplicate",
                f"$.base_fixture_targets[{index}].target",
                target=target,
            )
            continue
        entries_by_target[target] = entry

    for target in ALL_SIX_REQUIRED_TARGETS:
        entry = entries_by_target.get(target)
        if entry is None:
            continue
        path = paths.get(target)
        if path is None:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_base_fixture_snapshot_missing",
                f"$.base_fixture_targets[{target}]",
                target=target,
            )
            continue
        summary = snapshot_target_summary(path, target)
        for key in ("base_fixture_path", "base_fixture_sha256", "num_parms", "parms_size", "property_order"):
            if entry.get(key) != summary[key]:
                add_all_six_blocker(
                    blockers,
                    f"all_six_planning_gap_{key}_mismatch",
                    f"$.base_fixture_targets[{target}].{key}",
                    target=target,
                    expected=summary[key],
                    actual=entry.get(key),
                )
        if summary["ark_binary_sha256"] != identity.get("ark_binary_sha256"):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_base_fixture_binary_sha_mismatch",
                f"$.base_fixture_targets[{target}]",
                target=target,
                expected=identity.get("ark_binary_sha256"),
                actual=summary["ark_binary_sha256"],
            )


def all_six_planning_gap_artifact_blockers(
    artifact: dict[str, Any],
    *,
    snapshot_root: Path | None = None,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    validate_all_six_catalog_binding(blockers)

    if artifact.get("schema") != ALL_SIX_PLANNING_GAP_SCHEMA:
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_schema_mismatch",
            "$.schema",
            actual=artifact.get("schema"),
        )
    if artifact.get("artifact_status") != "planning_gap":
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_artifact_status_mismatch",
            "$.artifact_status",
            actual=artifact.get("artifact_status"),
        )
    if artifact.get("planning_only") is not True:
        add_all_six_blocker(blockers, "all_six_planning_gap_planning_only_not_true", "$.planning_only")
    if artifact.get("target_set") != ALL_SIX_PLANNING_GAP_TARGET_SET:
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_target_set_mismatch",
            "$.target_set",
            actual=artifact.get("target_set"),
        )
    if artifact.get("readiness_classification") != "planning_only":
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_readiness_classification_mismatch",
            "$.readiness_classification",
            actual=artifact.get("readiness_classification"),
        )

    operational = artifact.get("operational_consolidation")
    if not isinstance(operational, dict):
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_operational_consolidation_missing",
            "$.operational_consolidation",
        )
    else:
        triplet_policy = operational.get("approved_triplet_sources")
        if not isinstance(triplet_policy, dict):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_approved_triplet_sources_missing",
                "$.operational_consolidation.approved_triplet_sources",
            )
        else:
            expected_triplet_policy_fields = {
                "targets": ALL_SIX_APPROVED_TRIPLET_SOURCE_TARGETS,
                "targets_meaning": ALL_SIX_TRIPLET_SOURCE_TARGETS_MEANING,
                "static_lifecycle_anchor_targets": ALL_SIX_CURRENT_DURABLE_ANCHOR_TARGETS,
                "observer_rejected_start_targets": ALL_SIX_REJECTED_START_SOURCE_TARGETS,
                "chronology_only_non_anchor_targets": ALL_SIX_CHRONOLOGY_ONLY_TARGETS,
            }
            for key, expected in expected_triplet_policy_fields.items():
                if triplet_policy.get(key) != expected:
                    add_all_six_blocker(
                        blockers,
                        f"all_six_planning_gap_{key}_mismatch",
                        f"$.operational_consolidation.approved_triplet_sources.{key}",
                        expected=expected,
                        actual=triplet_policy.get(key),
                    )
            validate_all_six_exact_rejected_start_role_policy(
                triplet_policy.get("exact_rejected_start_role_policy"),
                blockers,
                "$.operational_consolidation.approved_triplet_sources.exact_rejected_start_role_policy",
            )
            if triplet_policy.get("only_these_targets_may_source_approved_triplet_roles") is not True:
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_triplet_source_exclusivity_missing",
                    "$.operational_consolidation.approved_triplet_sources.only_these_targets_may_source_approved_triplet_roles",
                )
            if triplet_policy.get("k2_postlogin_status") != "non_anchor_chronology_only_property_fname_mismatch_rejected":
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_k2_postlogin_status_mismatch",
                    "$.operational_consolidation.approved_triplet_sources.k2_postlogin_status",
                    actual=triplet_policy.get("k2_postlogin_status"),
                )
            if triplet_policy.get("all_six_planning_gap_evidence_status") != "non_evidence":
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_evidence_status_mismatch",
                    "$.operational_consolidation.approved_triplet_sources.all_six_planning_gap_evidence_status",
                    actual=triplet_policy.get("all_six_planning_gap_evidence_status"),
                )
        durable_roles = operational.get("durable_lifecycle_anchor_roles")
        if not isinstance(durable_roles, list):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_durable_lifecycle_anchor_roles_missing",
                "$.operational_consolidation.durable_lifecycle_anchor_roles",
            )
        else:
            roles_by_target = {
                entry.get("target"): entry
                for entry in durable_roles
                if isinstance(entry, dict) and isinstance(entry.get("target"), str)
            }
            handle_new_player_role = roles_by_target.get("ShooterGameMode.HandleNewPlayer")
            if not isinstance(handle_new_player_role, dict):
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_handle_new_player_lifecycle_role_missing",
                    "$.operational_consolidation.durable_lifecycle_anchor_roles",
                )
            elif handle_new_player_role.get("can_source_session_start_rejected") is not False:
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_handle_new_player_rejected_start_role_not_disallowed",
                    "$.operational_consolidation.durable_lifecycle_anchor_roles[ShooterGameMode.HandleNewPlayer].can_source_session_start_rejected",
                    actual=handle_new_player_role.get("can_source_session_start_rejected"),
                )
            for index, entry in enumerate(durable_roles):
                if (
                    isinstance(entry, dict)
                    and entry.get("target") == "ShooterGameMode.HandleNewPlayer"
                    and entry.get("role") == "session_start_rejected"
                ):
                    add_all_six_blocker(
                        blockers,
                        "all_six_planning_gap_handle_new_player_rejected_start_role_not_allowed",
                        f"$.operational_consolidation.durable_lifecycle_anchor_roles[{index}]",
                    )

        observer = operational.get("observer_only_alternative")
        if not isinstance(observer, dict):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_observer_only_alternative_missing",
                "$.operational_consolidation.observer_only_alternative",
            )
        else:
            observer_fields = {
                "role": ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY["role"],
                "target": ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY["target"],
                "required_copied_bool_fields": ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY["required_copied_bool_fields"],
                "required_copied_bool_values": ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY["required_copied_bool_values"],
                "disallowed_substitutes": ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY["disallowed_substitutes"],
            }
            for key, expected in observer_fields.items():
                if observer.get(key) != expected:
                    add_all_six_blocker(
                        blockers,
                        f"all_six_planning_gap_observer_only_{key}_mismatch",
                        f"$.operational_consolidation.observer_only_alternative.{key}",
                        expected=expected,
                        actual=observer.get(key),
                    )

    identity = artifact.get("artifact_identity")
    if not isinstance(identity, dict):
        add_all_six_blocker(blockers, "all_six_planning_gap_artifact_identity_missing", "$.artifact_identity")
    else:
        if identity.get("build_type") != "repo_fixture_planning_gap":
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_build_type_mismatch",
                "$.artifact_identity.build_type",
                actual=identity.get("build_type"),
            )
        if identity.get("target_set_revision") != STATIC_REPORT_TARGET_SET_REVISION:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_target_set_revision_mismatch",
                "$.artifact_identity.target_set_revision",
                actual=identity.get("target_set_revision"),
            )
        if identity.get("path_redacted") is not True:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_path_redacted_not_true",
                "$.artifact_identity.path_redacted",
            )
        source_id_blockers: list[dict[str, Any]] = []
        lifecycle_checker.validate_source_artifact_ids(
            identity.get("base_source_artifact_ids"),
            source_id_blockers,
            "$.artifact_identity.base_source_artifact_ids",
        )
        if source_id_blockers:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_base_source_artifact_ids_invalid",
                "$.artifact_identity.base_source_artifact_ids",
                details=source_id_blockers,
            )

    targets = artifact.get("base_fixture_targets")
    if not isinstance(targets, list):
        add_all_six_blocker(blockers, "all_six_planning_gap_base_fixture_targets_invalid", "$.base_fixture_targets")
    else:
        for index, entry in enumerate(targets):
            if not isinstance(entry, dict):
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_base_fixture_target_entry_invalid",
                    f"$.base_fixture_targets[{index}]",
                )
        target_names = [entry.get("target") for entry in targets if isinstance(entry, dict)]
        if target_names != list(ALL_SIX_REQUIRED_TARGETS):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_base_fixture_targets_mismatch",
                "$.base_fixture_targets",
                actual=target_names,
            )
        promoted = [
            entry.get("target")
            for entry in targets
            if isinstance(entry, dict) and entry.get("current_promoted_durable_source_bound_lifecycle_evidence") is True
        ]
        if promoted != ALL_SIX_CURRENT_DURABLE_ANCHOR_TARGETS:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_promoted_anchor_subset_mismatch",
                "$.base_fixture_targets",
                actual=promoted,
            )
        triplet_source_targets = sorted(
            entry.get("target")
            for entry in targets
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("target"), str)
                and entry.get("current_approved_triplet_source") is True
            )
        )
        if triplet_source_targets != sorted(ALL_SIX_APPROVED_TRIPLET_SOURCE_TARGETS):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_triplet_source_target_flags_mismatch",
                "$.base_fixture_targets",
                expected=ALL_SIX_APPROVED_TRIPLET_SOURCE_TARGETS,
                actual=triplet_source_targets,
            )
        entries_by_target = {
            entry.get("target"): entry
            for entry in targets
            if isinstance(entry, dict) and isinstance(entry.get("target"), str)
        }
        for target, entry in entries_by_target.items():
            expected_flag = target in ALL_SIX_APPROVED_TRIPLET_SOURCE_TARGETS
            if entry.get("current_approved_triplet_source") is not expected_flag:
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_triplet_source_flag_mismatch",
                    f"$.base_fixture_targets[{target}].current_approved_triplet_source",
                    target=target,
                    expected=expected_flag,
                    actual=entry.get("current_approved_triplet_source"),
                )
        k2_entry = entries_by_target.get("GameMode.K2_PostLogin")
        if not isinstance(k2_entry, dict):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_k2_postlogin_entry_missing",
                "$.base_fixture_targets",
            )
        else:
            if k2_entry.get("current_approved_triplet_source") is not False:
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_k2_postlogin_triplet_source_not_false",
                    "$.base_fixture_targets[GameMode.K2_PostLogin].current_approved_triplet_source",
                    actual=k2_entry.get("current_approved_triplet_source"),
                )
            if k2_entry.get("chronology_only_non_anchor") is not True:
                add_all_six_blocker(
                    blockers,
                    "all_six_planning_gap_k2_postlogin_not_chronology_only",
                    "$.base_fixture_targets[GameMode.K2_PostLogin].chronology_only_non_anchor",
                    actual=k2_entry.get("chronology_only_non_anchor"),
                )
        handle_new_player_entry = entries_by_target.get("ShooterGameMode.HandleNewPlayer")
        if (
            isinstance(handle_new_player_entry, dict)
            and handle_new_player_entry.get("current_rejected_start_observer_alternative") is True
        ):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_handle_new_player_rejected_start_observer_not_allowed",
                "$.base_fixture_targets[ShooterGameMode.HandleNewPlayer].current_rejected_start_observer_alternative",
            )
        check_join_entry = entries_by_target.get("ShooterGameMode.CheckJoinInProgress")
        if not isinstance(check_join_entry, dict):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_checkjoin_entry_missing",
                "$.base_fixture_targets",
            )
        elif check_join_entry.get("current_rejected_start_observer_alternative") is not True:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_checkjoin_rejected_start_observer_missing",
                "$.base_fixture_targets[ShooterGameMode.CheckJoinInProgress].current_rejected_start_observer_alternative",
                actual=check_join_entry.get("current_rejected_start_observer_alternative"),
            )

    historical = artifact.get("historical_scratch_comparison")
    if not isinstance(historical, dict):
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_historical_scratch_comparison_missing",
            "$.historical_scratch_comparison",
        )
    else:
        if historical.get("durable") is not False:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_historical_scratch_comparison_must_not_be_durable",
                "$.historical_scratch_comparison.durable",
            )
        if historical.get("status") != "scratch_triage_only":
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_historical_scratch_comparison_status_mismatch",
                "$.historical_scratch_comparison.status",
                actual=historical.get("status"),
            )
        if historical.get("accepted_targets") != len(ALL_SIX_REQUIRED_TARGETS):
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_historical_scratch_accepted_targets_count_mismatch",
                "$.historical_scratch_comparison.accepted_targets",
                expected=len(ALL_SIX_REQUIRED_TARGETS),
                actual=historical.get("accepted_targets"),
            )
        if historical.get("accepted_targets_meaning") != ALL_SIX_HISTORICAL_ACCEPTED_TARGETS_MEANING:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_historical_scratch_accepted_targets_meaning_mismatch",
                "$.historical_scratch_comparison.accepted_targets_meaning",
                expected=ALL_SIX_HISTORICAL_ACCEPTED_TARGETS_MEANING,
                actual=historical.get("accepted_targets_meaning"),
            )

    durable = artifact.get("durable_all_six_comparison")
    if not isinstance(durable, dict):
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_durable_all_six_comparison_missing",
            "$.durable_all_six_comparison",
        )
    else:
        if durable.get("provided") is not False:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_durable_all_six_comparison_must_not_be_provided",
                "$.durable_all_six_comparison.provided",
            )
        if durable.get("accepted") is not False:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_durable_all_six_comparison_must_not_be_accepted",
                "$.durable_all_six_comparison.accepted",
            )
        if durable.get("reason") != "distinct_non_tmp_candidate_snapshot_root_missing":
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_durable_all_six_comparison_reason_mismatch",
                "$.durable_all_six_comparison.reason",
                actual=durable.get("reason"),
            )

    current = artifact.get("current_durable_source_bound_lifecycle_anchor_evidence")
    if not isinstance(current, dict):
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_current_durable_anchor_evidence_missing",
            "$.current_durable_source_bound_lifecycle_anchor_evidence",
        )
    elif current.get("accepted_targets") != ALL_SIX_CURRENT_DURABLE_ANCHOR_TARGETS:
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_current_durable_anchor_targets_mismatch",
            "$.current_durable_source_bound_lifecycle_anchor_evidence.accepted_targets",
            actual=current.get("accepted_targets"),
        )
    else:
        if current.get("accepted_targets_meaning") != ALL_SIX_DURABLE_ANCHOR_TARGETS_MEANING:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_current_durable_anchor_accepted_targets_meaning_mismatch",
                "$.current_durable_source_bound_lifecycle_anchor_evidence.accepted_targets_meaning",
                expected=ALL_SIX_DURABLE_ANCHOR_TARGETS_MEANING,
                actual=current.get("accepted_targets_meaning"),
            )
        observer_alternatives = current.get("observer_only_rejected_start_alternatives")
        observer_targets = [
            entry.get("target")
            for entry in observer_alternatives
            if isinstance(entry, dict)
        ] if isinstance(observer_alternatives, list) else []
        if observer_targets != ALL_SIX_REJECTED_START_SOURCE_TARGETS:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_current_observer_rejected_start_sources_mismatch",
                "$.current_durable_source_bound_lifecycle_anchor_evidence.observer_only_rejected_start_alternatives",
                expected=ALL_SIX_REJECTED_START_SOURCE_TARGETS,
                actual=observer_targets,
            )
        if len(observer_targets) == 1 and observer_targets[0] == ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY["target"]:
            observer_entry = observer_alternatives[0] if isinstance(observer_alternatives, list) else None
            if isinstance(observer_entry, dict):
                for key in (
                    "required_copied_bool_fields",
                    "required_copied_bool_values",
                    "disallowed_substitutes",
                ):
                    expected = ALL_SIX_EXACT_REJECTED_START_ROLE_POLICY[key]
                    if observer_entry.get(key) != expected:
                        add_all_six_blocker(
                            blockers,
                            f"all_six_planning_gap_current_observer_rejected_start_{key}_mismatch",
                            f"$.current_durable_source_bound_lifecycle_anchor_evidence.observer_only_rejected_start_alternatives[0].{key}",
                            expected=expected,
                            actual=observer_entry.get(key),
                        )

    current_triplet = artifact.get("current_approved_triplet_sources")
    if not isinstance(current_triplet, dict):
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_current_triplet_sources_missing",
            "$.current_approved_triplet_sources",
        )
    else:
        current_triplet_fields = {
            "accepted_targets": ALL_SIX_APPROVED_TRIPLET_SOURCE_TARGETS,
            "accepted_targets_meaning": ALL_SIX_TRIPLET_SOURCE_TARGETS_MEANING,
            "static_lifecycle_anchor_targets": ALL_SIX_CURRENT_DURABLE_ANCHOR_TARGETS,
            "observer_rejected_start_targets": ALL_SIX_REJECTED_START_SOURCE_TARGETS,
            "chronology_only_non_anchor_targets": ALL_SIX_CHRONOLOGY_ONLY_TARGETS,
            "guidance_only_non_triplet_targets": ALL_SIX_GUIDANCE_ONLY_TARGETS,
        }
        for key, expected in current_triplet_fields.items():
            if current_triplet.get(key) != expected:
                add_all_six_blocker(
                    blockers,
                    f"all_six_planning_gap_current_triplet_{key}_mismatch",
                    f"$.current_approved_triplet_sources.{key}",
                    expected=expected,
                    actual=current_triplet.get(key),
                )
        validate_all_six_exact_rejected_start_role_policy(
            current_triplet.get("exact_rejected_start_role_policy"),
            blockers,
            "$.current_approved_triplet_sources.exact_rejected_start_role_policy",
        )
        if current_triplet.get("all_six_planning_gap_evidence_status") != "non_evidence":
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_current_triplet_all_six_status_mismatch",
                "$.current_approved_triplet_sources.all_six_planning_gap_evidence_status",
                actual=current_triplet.get("all_six_planning_gap_evidence_status"),
            )

    promotion_gate = artifact.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        add_all_six_blocker(blockers, "all_six_planning_gap_promotion_gate_missing", "$.promotion_gate")
    else:
        for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
            if promotion_gate.get(key) is not False:
                add_all_six_blocker(
                    blockers,
                    f"all_six_planning_gap_{key}_must_be_false",
                    f"$.promotion_gate.{key}",
                    actual=promotion_gate.get(key),
                )
        if promotion_gate.get("ready_scope") != "planning_only":
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_ready_scope_mismatch",
                "$.promotion_gate.ready_scope",
                actual=promotion_gate.get("ready_scope"),
            )
        gate_blockers = promotion_gate.get("blockers")
        if not isinstance(gate_blockers, list) or ALL_SIX_REQUIRED_BLOCKER not in gate_blockers:
            add_all_six_blocker(
                blockers,
                "all_six_planning_gap_approved_runtime_evidence_missing_not_preserved",
                "$.promotion_gate.blockers",
                actual=gate_blockers,
            )

    does_not_satisfy = artifact.get("does_not_satisfy_blockers")
    if not isinstance(does_not_satisfy, list) or ALL_SIX_REQUIRED_BLOCKER not in does_not_satisfy:
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_does_not_satisfy_runtime_blocker_missing",
            "$.does_not_satisfy_blockers",
            actual=does_not_satisfy,
        )

    non_claims = artifact.get("non_claims")
    required_non_claims = {
        "does not promote the all-six comparison as durable second-source evidence",
        "does not change approved lifecycle triplet sources beyond ShooterGameMode.HandleNewPlayer, ShooterGameMode.CheckJoinInProgress, and ShooterGameMode.OnLogout",
        "does not promote GameMode.K2_PostLogin beyond non-anchor chronology-only diagnostics",
        "does not clear approved_runtime_evidence_missing",
        "accepted_targets fields in this planning-gap artifact describe scoped source lists or scratch counts only; they are not approved runtime evidence",
    }
    if not isinstance(non_claims, list) or not required_non_claims.issubset(set(non_claims)):
        add_all_six_blocker(
            blockers,
            "all_six_planning_gap_non_claims_missing",
            "$.non_claims",
            required=sorted(required_non_claims),
        )

    def reject_promotional_true_fields(value: Any, trail: str = "$") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_trail = f"{trail}.{key}"
                if key in ALL_SIX_FORBIDDEN_TRUE_FIELDS and child is True:
                    add_all_six_blocker(
                        blockers,
                        "all_six_planning_gap_promotional_true_field",
                        child_trail,
                        field=key,
                    )
                reject_promotional_true_fields(child, child_trail)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                reject_promotional_true_fields(child, f"{trail}[{index}]")

    reject_promotional_true_fields(artifact)
    if snapshot_root is not None:
        validate_all_six_base_fixture_binding(artifact, blockers, snapshot_root)
    return blockers


def add_fname_mismatch_blocker(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def integer_list(value: Any) -> list[int] | None:
    if not isinstance(value, list):
        return None
    result: list[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            return None
        result.append(item)
    return result


def validate_fname_mismatch_chain(
    *,
    entry: dict[str, Any],
    summary: dict[str, Any],
    blockers: list[dict[str, Any]],
    label: str,
    target: str,
) -> None:
    expected_order = summary["property_order"]
    expected_indices = summary["property_name_indices"]
    if entry.get("fixture_property_order") != expected_order:
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_fixture_property_order_mismatch",
            f"{label}.fixture_property_order",
            target=target,
            expected=expected_order,
            actual=entry.get("fixture_property_order"),
        )

    recorded_expected = integer_list(entry.get("fixture_expected_name_indices"))
    if recorded_expected != expected_indices:
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_fixture_expected_name_indices_mismatch",
            f"{label}.fixture_expected_name_indices",
            target=target,
            expected=expected_indices,
            actual=entry.get("fixture_expected_name_indices"),
        )
    observed = integer_list(entry.get("observed_name_indices"))
    if observed is None:
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_observed_name_indices_invalid",
            f"{label}.observed_name_indices",
            target=target,
        )
        return
    if recorded_expected is None or len(observed) != len(expected_indices):
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_observed_name_indices_shape_mismatch",
            f"{label}.observed_name_indices",
            target=target,
            expected_count=len(expected_indices),
            actual_count=len(observed),
        )
        return

    expected_deltas = [observed_index - expected_index for expected_index, observed_index in zip(expected_indices, observed)]
    if entry.get("deltas") != expected_deltas:
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_deltas_mismatch",
            f"{label}.deltas",
            target=target,
            expected=expected_deltas,
            actual=entry.get("deltas"),
        )
    exact_match = observed == expected_indices
    if entry.get("exact_property_chain_match") is not exact_match:
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_exact_property_chain_match_mismatch",
            f"{label}.exact_property_chain_match",
            target=target,
            expected=exact_match,
            actual=entry.get("exact_property_chain_match"),
        )


def reject_fname_mismatch_promotional_true_fields(
    value: Any,
    blockers: list[dict[str, Any]],
    trail: str = "$",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in FNAME_MISMATCH_FORBIDDEN_TRUE_FIELDS and child is True:
                add_fname_mismatch_blocker(
                    blockers,
                    "fname_mismatch_promotional_true_field",
                    child_trail,
                    field=key,
                )
            reject_fname_mismatch_promotional_true_fields(child, blockers, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_fname_mismatch_promotional_true_fields(child, blockers, f"{trail}[{index}]")


def validate_latest_unbound_passive_context(
    context: Any,
    blockers: list[dict[str, Any]],
    summaries: dict[str, dict[str, Any]],
) -> None:
    label = "$.latest_unbound_passive_diagnostic_context"
    if not isinstance(context, dict):
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_latest_unbound_passive_context_missing",
            label,
        )
        return
    expected_fields = {
        "status": "unverified_passive_diagnostic_non_evidence",
        "source": "worker_prompt_redacted_monitor_context",
        "readiness_effect": "none",
    }
    for key, expected in expected_fields.items():
        if context.get(key) != expected:
            add_fname_mismatch_blocker(
                blockers,
                f"fname_mismatch_latest_unbound_context_{key}_mismatch",
                f"{label}.{key}",
                expected=expected,
                actual=context.get(key),
            )
    for key in (
        "approved_runtime_evidence",
        "can_update_fixture_expectations",
        "counts_as_second_source_layout_evidence",
        "runtime_ready",
        "public_sdk_ready",
    ):
        if context.get(key) is not False:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_latest_unbound_context_promotional_claim",
                f"{label}.{key}",
                field=key,
                actual=context.get(key),
            )

    observations = context.get("observations")
    if not isinstance(observations, list) or not observations:
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_latest_unbound_context_observations_invalid",
            f"{label}.observations",
        )
        return
    for index, observation in enumerate(observations):
        obs_label = f"{label}.observations[{index}]"
        if not isinstance(observation, dict):
            add_fname_mismatch_blocker(blockers, "fname_mismatch_latest_unbound_observation_invalid", obs_label)
            continue
        target = observation.get("target")
        if target not in FNAME_MISMATCH_ALLOWED_TARGETS:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_latest_unbound_observation_target_mismatch",
                f"{obs_label}.target",
                actual=target,
            )
            continue
        summary = summaries.get(str(target))
        position = observation.get("property_position")
        if not isinstance(position, int) or isinstance(position, bool):
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_latest_unbound_observation_position_invalid",
                f"{obs_label}.property_position",
                target=target,
            )
            continue
        if summary is None or position < 0 or position >= len(summary["property_name_indices"]):
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_latest_unbound_observation_position_out_of_range",
                f"{obs_label}.property_position",
                target=target,
                actual=position,
            )
            continue
        expected_name_index = observation.get("expected_name_index")
        observed_name_index = observation.get("observed_name_index")
        delta = observation.get("delta")
        expected_from_fixture = summary["property_name_indices"][position]
        if expected_name_index != expected_from_fixture:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_latest_unbound_observation_expected_index_mismatch",
                f"{obs_label}.expected_name_index",
                target=target,
                expected=expected_from_fixture,
                actual=expected_name_index,
            )
        if (
            not isinstance(observed_name_index, int)
            or isinstance(observed_name_index, bool)
            or delta != observed_name_index - expected_from_fixture
        ):
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_latest_unbound_observation_delta_mismatch",
                f"{obs_label}.delta",
                target=target,
                expected=(
                    observed_name_index - expected_from_fixture
                    if isinstance(observed_name_index, int) and not isinstance(observed_name_index, bool)
                    else None
                ),
                actual=delta,
            )
        if observation.get("complete_property_chain_available") is not False:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_latest_unbound_observation_complete_chain_overclaim",
                f"{obs_label}.complete_property_chain_available",
                target=target,
                actual=observation.get("complete_property_chain_available"),
            )
        if observation.get("source_bound_to_repo_artifact") is not False:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_latest_unbound_observation_source_bound_overclaim",
                f"{obs_label}.source_bound_to_repo_artifact",
                target=target,
                actual=observation.get("source_bound_to_repo_artifact"),
            )


def fname_mismatch_artifact_blockers(
    artifact: dict[str, Any],
    *,
    snapshot_root: Path,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if artifact.get("schema") != FNAME_MISMATCH_SCHEMA:
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_schema_mismatch",
            "$.schema",
            actual=artifact.get("schema"),
        )
    expected_top_level = {
        "artifact_status": "planning_diagnostic_unresolved",
        "planning_only": True,
        "evidence_scope": "diagnostic_fname_chain_planning_only_not_second_source",
        "artifact_role": "diagnostic_planning_only_not_second_source_input",
        "layout_evidence_status": "not_layout_evidence",
        "readiness_classification": "planning_only",
        "readiness_effect": "none",
        "second_source_layout_evidence": False,
        "can_be_used_as_second_source_layout_evidence": False,
        "can_be_used_as_candidate_snapshot_root": False,
        "second_source_status": "not_applicable",
        "not_second_source": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "target_set": ALL_SIX_PLANNING_GAP_TARGET_SET,
        "target": FNAME_MISMATCH_PRIMARY_TARGET,
    }
    for key, expected in expected_top_level.items():
        if artifact.get(key) != expected:
            add_fname_mismatch_blocker(
                blockers,
                f"fname_mismatch_{key}_mismatch",
                f"$.{key}",
                expected=expected,
                actual=artifact.get(key),
            )

    paths = manifest_target_paths(snapshot_root)
    manifest = load_json(snapshot_root / "manifest.json", "snapshot manifest")
    summaries: dict[str, dict[str, Any]] = {}
    for target in FNAME_MISMATCH_ALLOWED_TARGETS:
        path = paths.get(target)
        if path is None:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_snapshot_target_missing",
                "snapshot-root",
                target=target,
            )
            continue
        summaries[target] = snapshot_target_summary(path, target)

    identity = artifact.get("artifact_identity")
    if not isinstance(identity, dict):
        add_fname_mismatch_blocker(blockers, "fname_mismatch_artifact_identity_missing", "$.artifact_identity")
    else:
        primary_summary = summaries.get(FNAME_MISMATCH_PRIMARY_TARGET)
        identity_expected = {
            "ark_binary_sha256": manifest.get("ark_binary_sha256"),
            "base_fixture_root": repo_relative_path(snapshot_root),
            "build_type": "repo_fixture_runtime_diagnostic_planning_check",
            "target_set_revision": STATIC_REPORT_TARGET_SET_REVISION,
        }
        for key, expected in identity_expected.items():
            if identity.get(key) != expected:
                add_fname_mismatch_blocker(
                    blockers,
                    f"fname_mismatch_artifact_identity_{key}_mismatch",
                    f"$.artifact_identity.{key}",
                    expected=expected,
                    actual=identity.get(key),
                )
        if primary_summary is not None:
            for key in ("base_fixture_path", "base_fixture_sha256"):
                if identity.get(key) != primary_summary[key]:
                    add_fname_mismatch_blocker(
                        blockers,
                        f"fname_mismatch_{key}_mismatch",
                        f"$.artifact_identity.{key}",
                        expected=primary_summary[key],
                        actual=identity.get(key),
                    )

    primary_summary = summaries.get(FNAME_MISMATCH_PRIMARY_TARGET)
    if primary_summary is not None:
        validate_fname_mismatch_chain(
            entry=artifact,
            summary=primary_summary,
            blockers=blockers,
            label="$",
            target=FNAME_MISMATCH_PRIMARY_TARGET,
        )

    related = artifact.get("related_observed_fname_mismatches")
    if not isinstance(related, list):
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_related_observed_fname_mismatches_invalid",
            "$.related_observed_fname_mismatches",
        )
    else:
        related_targets = []
        for index, entry in enumerate(related):
            label = f"$.related_observed_fname_mismatches[{index}]"
            if not isinstance(entry, dict):
                add_fname_mismatch_blocker(blockers, "fname_mismatch_related_entry_invalid", label)
                continue
            target = entry.get("target")
            related_targets.append(target)
            if target not in FNAME_MISMATCH_RELATED_TARGETS:
                add_fname_mismatch_blocker(
                    blockers,
                    "fname_mismatch_related_target_mismatch",
                    f"{label}.target",
                    expected=list(FNAME_MISMATCH_RELATED_TARGETS),
                    actual=target,
                )
                continue
            summary = summaries.get(str(target))
            if summary is not None:
                validate_fname_mismatch_chain(
                    entry=entry,
                    summary=summary,
                    blockers=blockers,
                    label=label,
                    target=str(target),
                )
            expected_related_fields = {
                "current_recognizer_drift_chain_accepted_meaning": "recognizer_alternative_only_not_runtime_evidence",
                "status": "recognized_drift_chain_planning_only",
                "planning_only": True,
                "not_second_source": True,
                "readiness_effect": "none",
                "second_source_status": "not_applicable",
            }
            for key, expected in expected_related_fields.items():
                if entry.get(key) != expected:
                    add_fname_mismatch_blocker(
                        blockers,
                        f"fname_mismatch_related_{key}_mismatch",
                        f"{label}.{key}",
                        target=target,
                        expected=expected,
                        actual=entry.get(key),
                    )
        if related_targets != list(FNAME_MISMATCH_RELATED_TARGETS):
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_related_targets_mismatch",
                "$.related_observed_fname_mismatches",
                expected=list(FNAME_MISMATCH_RELATED_TARGETS),
                actual=related_targets,
            )

    runtime_snapshot = artifact.get("runtime_snapshot")
    if not isinstance(runtime_snapshot, dict):
        add_fname_mismatch_blocker(blockers, "fname_mismatch_runtime_snapshot_missing", "$.runtime_snapshot")
    else:
        if runtime_snapshot.get("approved_runtime_evidence") is not False:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_runtime_snapshot_approved_runtime_evidence_not_false",
                "$.runtime_snapshot.approved_runtime_evidence",
                actual=runtime_snapshot.get("approved_runtime_evidence"),
            )
        if runtime_snapshot.get("source") != "passive_snapshot_copied_log_analysis":
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_runtime_snapshot_source_mismatch",
                "$.runtime_snapshot.source",
                actual=runtime_snapshot.get("source"),
            )

    runtime_summary = artifact.get("runtime_observation_summary")
    if not isinstance(runtime_summary, dict):
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_runtime_observation_summary_missing",
            "$.runtime_observation_summary",
        )
    else:
        for key, expected in (
            ("accepted_count", 0),
            ("approved_runtime_evidence", False),
            ("diagnostic_only", True),
            ("readiness_effect", "none"),
            ("rejected_count", 0),
            ("source_scope", "copied_passive_snapshot_log_analysis"),
        ):
            if runtime_summary.get(key) != expected:
                add_fname_mismatch_blocker(
                    blockers,
                    f"fname_mismatch_runtime_summary_{key}_mismatch",
                    f"$.runtime_observation_summary.{key}",
                    expected=expected,
                    actual=runtime_summary.get(key),
                )
        mismatch_counts = runtime_summary.get("mismatch_counts")
        if not isinstance(mismatch_counts, list) or not mismatch_counts:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_runtime_summary_mismatch_counts_invalid",
                "$.runtime_observation_summary.mismatch_counts",
            )
        else:
            for index, entry in enumerate(mismatch_counts):
                label = f"$.runtime_observation_summary.mismatch_counts[{index}]"
                if not isinstance(entry, dict):
                    add_fname_mismatch_blocker(blockers, "fname_mismatch_runtime_summary_mismatch_count_invalid", label)
                    continue
                if entry.get("target") not in FNAME_MISMATCH_ALLOWED_TARGETS:
                    add_fname_mismatch_blocker(
                        blockers,
                        "fname_mismatch_runtime_summary_mismatch_count_target_invalid",
                        f"{label}.target",
                        actual=entry.get("target"),
                    )
                if entry.get("not_second_source") is not True or entry.get("readiness_effect") != "none":
                    add_fname_mismatch_blocker(
                        blockers,
                        "fname_mismatch_runtime_summary_mismatch_count_boundary_mismatch",
                        label,
                        actual=entry,
                    )

    if artifact.get("current_recognizer_drift_chain_accepted_meaning") != "recognizer_alternative_only_not_runtime_evidence":
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_recognizer_acceptance_meaning_mismatch",
            "$.current_recognizer_drift_chain_accepted_meaning",
            actual=artifact.get("current_recognizer_drift_chain_accepted_meaning"),
        )

    promotion_gate = artifact.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        add_fname_mismatch_blocker(blockers, "fname_mismatch_promotion_gate_missing", "$.promotion_gate")
    else:
        for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
            if promotion_gate.get(key) is not False:
                add_fname_mismatch_blocker(
                    blockers,
                    f"fname_mismatch_promotion_gate_{key}_not_false",
                    f"$.promotion_gate.{key}",
                    actual=promotion_gate.get(key),
                )
        gate_blockers = promotion_gate.get("blockers")
        if not isinstance(gate_blockers, list) or ALL_SIX_REQUIRED_BLOCKER not in gate_blockers:
            add_fname_mismatch_blocker(
                blockers,
                "fname_mismatch_approved_runtime_evidence_missing_not_preserved",
                "$.promotion_gate.blockers",
                actual=gate_blockers,
            )

    does_not_satisfy = artifact.get("does_not_satisfy_blockers")
    if not isinstance(does_not_satisfy, list) or ALL_SIX_REQUIRED_BLOCKER not in does_not_satisfy:
        add_fname_mismatch_blocker(
            blockers,
            "fname_mismatch_does_not_satisfy_runtime_blocker_missing",
            "$.does_not_satisfy_blockers",
            actual=does_not_satisfy,
        )

    validate_latest_unbound_passive_context(
        artifact.get("latest_unbound_passive_diagnostic_context"),
        blockers,
        summaries,
    )
    reject_fname_mismatch_promotional_true_fields(artifact, blockers)
    return blockers


def source_artifact_id_rows(source_artifact_ids: Any) -> list[dict[str, str]]:
    if not isinstance(source_artifact_ids, list):
        return []
    rows: list[dict[str, str]] = []
    for entry in source_artifact_ids:
        if not isinstance(entry, str) or ":" not in entry:
            continue
        field, _, value = entry.partition(":")
        rows.append({"field": field, "value": value, "entry": entry})
    return rows


def lifecycle_provenance_diagnostic(lifecycle: dict[str, Any]) -> dict[str, Any]:
    artifact_identity = lifecycle.get("artifact_identity") if isinstance(lifecycle.get("artifact_identity"), dict) else {}
    source_rows = source_artifact_id_rows(artifact_identity.get("source_artifact_ids"))
    missing_source_ids: list[dict[str, Any]] = []
    obelisk_commit = artifact_identity.get("obelisk_commit")
    if obelisk_commit in lifecycle_checker.PLACEHOLDER_OBELISK_COMMITS:
        missing_source_ids.append(
            {
                "field": "$.artifact_identity.obelisk_commit",
                "observed": obelisk_commit,
                "required": "non-placeholder reviewed Obelisk commit/source binding for accepted lifecycle anchors",
            }
        )
    for row in source_rows:
        placeholders = lifecycle_checker.PLACEHOLDER_SOURCE_ARTIFACT_IDS.get(row["field"])
        if placeholders is not None and row["value"] in placeholders:
            missing_source_ids.append(
                {
                    "field": "$.artifact_identity.source_artifact_ids",
                    "source_id_field": row["field"],
                    "observed": row["entry"],
                    "required": (
                        "non-placeholder source artifact id bound to the durable lifecycle-anchor "
                        "second-source/static report"
                    ),
                }
            )

    missing_report_hashes: list[dict[str, Any]] = []
    accepted_anchor_targets: list[str] = []
    anchors = lifecycle.get("candidate_anchors") if isinstance(lifecycle.get("candidate_anchors"), list) else []
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, dict) or anchor.get("accepted") is not True:
            continue
        target = anchor.get("target")
        if isinstance(target, str):
            accepted_anchor_targets.append(target)
        corroboration = anchor.get("corroboration") if isinstance(anchor.get("corroboration"), dict) else {}
        status = corroboration.get("status")
        if status == "second_source_accepted":
            report_sha = corroboration.get("second_source_report_sha256")
            if not isinstance(report_sha, str) or lifecycle_checker.SHA256_RE.fullmatch(report_sha) is None:
                missing_report_hashes.append(
                    {
                        "target": target,
                        "field": f"$.candidate_anchors[{index}].corroboration.second_source_report_sha256",
                        "observed": report_sha,
                        "required": "64-hex SHA256 of a reviewed durable second-source lifecycle-anchor report",
                    }
                )
        elif status == "static_accepted":
            report_sha = corroboration.get("static_report_sha256")
            if not isinstance(report_sha, str) or lifecycle_checker.SHA256_RE.fullmatch(report_sha) is None:
                missing_report_hashes.append(
                    {
                        "target": target,
                        "field": f"$.candidate_anchors[{index}].corroboration.static_report_sha256",
                        "observed": report_sha,
                        "required": "64-hex SHA256 of a reviewed durable static lifecycle-anchor report",
                    }
                )

    return {
        "current_route_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
        "accepted_anchor_targets": accepted_anchor_targets,
        "observed_source_artifact_ids": [row["entry"] for row in source_rows],
        "missing_durable_source_ids": missing_source_ids,
        "missing_durable_report_hashes": missing_report_hashes,
        "required_evidence_boundary": (
            "sanitized snapshot layout is planning-only; accepted lifecycle anchors need "
            "non-placeholder source ids and reviewed durable report hashes before route/SDK "
            "accounting can move past the provenance blocker"
        ),
    }


def lifecycle_generation_failure_report(
    *,
    snapshot_root: Path,
    output_dir: Path | None,
    verify_existing_dir: Path | None,
    lifecycle: dict[str, Any],
    lifecycle_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons = validation_reasons(lifecycle_blockers)
    accepted_targets = [
        str(anchor.get("target"))
        for anchor in lifecycle.get("candidate_anchors", [])
        if isinstance(anchor, dict) and anchor.get("accepted") is True and isinstance(anchor.get("target"), str)
    ]
    return {
        "schema": REPORT_SCHEMA,
        "mode": "verify_existing" if verify_existing_dir is not None else "build",
        "valid": False,
        "accepted_for_planning": False,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "snapshot_root": str(snapshot_root),
        "output_dir": str(output_dir) if output_dir is not None else None,
        "verify_existing_dir": str(verify_existing_dir) if verify_existing_dir is not None else None,
        "current_route_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
        "blockers": ["generated_lifecycle_anchor_candidates_invalid", *sorted(set(reasons))],
        "lifecycle_anchor_candidate_blockers": lifecycle_blockers,
        "lifecycle_anchor_candidate_blocker_reasons": reasons,
        "lifecycle_provenance_diagnostic": lifecycle_provenance_diagnostic(lifecycle),
        "accepted_lifecycle_targets": accepted_targets,
        "required_next_artifacts": [
            {
                "artifact": "lifecycle_anchor_candidates",
                "schema": lifecycle_checker.SCHEMA,
                "required": (
                    "accepted anchors must carry non-placeholder artifact_identity, non-generic "
                    "source_artifact_ids, and accepted second-source/static report hashes"
                ),
            },
            {
                "artifact": "source_bound_second_source_or_static_report",
                "required": (
                    "create or select a durable repo-local reviewed report for "
                    "ShooterGameMode.HandleNewPlayer and ShooterGameMode.OnLogout before "
                    "regenerating planning manifests"
                ),
            },
        ],
        "non_claims": NON_CLAIMS,
    }


def output_record(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256_file(path), "schema": payload.get("schema")}


def build_report(
    *,
    snapshot_root: Path,
    output_dir: Path,
    first_path: Path,
    lifecycle_path: Path,
    principal_path: Path,
    report_path: Path,
    first_evidence: dict[str, Any],
    lifecycle: dict[str, Any],
    principal: dict[str, Any],
    binder_report: dict[str, Any],
    lifecycle_snapshot_root_binding: dict[str, Any],
    lifecycle_static_report_path: Path | None,
    lifecycle_static_report_sha256: str | None,
) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "valid": binder_report.get("ready") is True,
        "accepted_for_planning": binder_report.get("ready") is True,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "snapshot_root": str(snapshot_root),
        "output_dir": str(output_dir),
        "blockers": list(binder_report.get("blockers", [])) if isinstance(binder_report.get("blockers"), list) else [],
        "outputs": {
            "first_evidence": output_record(first_path, first_evidence),
            "lifecycle_anchor_candidates": output_record(lifecycle_path, lifecycle),
            "principal_invalidation_policy": output_record(principal_path, principal),
            "report": {"path": str(report_path)},
        },
        "source_alignment": {
            "artifact_identity_source_artifact_ids": copy.deepcopy(
                lifecycle["artifact_identity"]["source_artifact_ids"]
            ),
            "principal_lifecycle_source_binding": copy.deepcopy(
                principal["lifecycle_layout_source"]["source_binding"]
            ),
            "lifecycle_snapshot_root_binding": copy.deepcopy(lifecycle_snapshot_root_binding),
            "lifecycle_static_report": {
                "path": str(lifecycle_static_report_path) if lifecycle_static_report_path is not None else None,
                "sha256": lifecycle_static_report_sha256,
                "bound": lifecycle_static_report_sha256 is not None,
            },
            "binder_ready": binder_report.get("ready") is True,
            "binder_blockers": binder_report.get("blockers", []),
        },
        "binding_report": binder_report,
        "non_claims": NON_CLAIMS,
    }


def build_into_dir(
    *,
    snapshot_root: Path,
    output_dir: Path,
    lifecycle_static_report_path: Path | None = DEFAULT_LIFECYCLE_STATIC_REPORT,
    verify_existing_dir: Path | None = None,
) -> dict[str, Any]:
    output_dir = binder.prepare_output_dir(output_dir)
    lifecycle_static_report, lifecycle_static_report_sha256 = load_lifecycle_static_report(lifecycle_static_report_path)

    first_evidence = build_redacted_ufunction_signatures.build_players_identity_first_evidence(
        snapshot_root=snapshot_root
    )
    first_blockers = binder.offline_artifact_gate.validate_players_identity_first_evidence_manifest(
        first_evidence,
        label="generated first-evidence",
        mode="consume",
    )
    if first_blockers:
        raise SystemExit("generated first-evidence failed validation: " + json.dumps(validation_reasons(first_blockers), sort_keys=True))

    lifecycle = build_lifecycle_manifest(
        first_evidence,
        snapshot_root,
        lifecycle_static_report=lifecycle_static_report,
        lifecycle_static_report_sha256=lifecycle_static_report_sha256,
    )
    lifecycle_blockers = lifecycle_checker.validate_manifest(lifecycle, promote=False)
    if lifecycle_blockers:
        return lifecycle_generation_failure_report(
            snapshot_root=snapshot_root,
            output_dir=output_dir,
            verify_existing_dir=verify_existing_dir,
            lifecycle=lifecycle,
            lifecycle_blockers=lifecycle_blockers,
        )
    lifecycle_snapshot_root_binding = binder.validate_lifecycle_anchor_snapshot_root(
        lifecycle=lifecycle,
        snapshot_root=snapshot_root,
    )

    principal = build_principal_manifest(lifecycle)
    principal_blockers = principal_checker.validate_manifest(principal, check_mode="consume").blockers
    if principal_blockers:
        raise SystemExit(
            "generated principal invalidation policy failed validation: "
            + json.dumps(validation_reasons(principal_blockers), sort_keys=True)
        )

    binder.validate_inputs(first_evidence=first_evidence, lifecycle=lifecycle, principal=principal)

    first_path = output_dir / FIRST_EVIDENCE_OUTPUT_NAME
    lifecycle_path = output_dir / binder.LIFECYCLE_OUTPUT_NAME
    principal_path = output_dir / binder.PRINCIPAL_OUTPUT_NAME
    report_path = output_dir / REPORT_OUTPUT_NAME

    binder.atomic_write_json(first_path, first_evidence)
    binder.atomic_write_json(lifecycle_path, lifecycle)
    binder.atomic_write_json(principal_path, principal)
    binder_report = binder.build_report(
        first_path=first_path,
        lifecycle_path=lifecycle_path,
        principal_path=principal_path,
        first_evidence=first_evidence,
        lifecycle_output=lifecycle_path,
        principal_output=principal_path,
        bound_lifecycle=lifecycle,
        bound_principal=principal,
    )
    report = build_report(
        snapshot_root=snapshot_root,
        output_dir=output_dir,
        first_path=first_path,
        lifecycle_path=lifecycle_path,
        principal_path=principal_path,
        report_path=report_path,
        first_evidence=first_evidence,
        lifecycle=lifecycle,
        principal=principal,
        binder_report=binder_report,
        lifecycle_snapshot_root_binding=lifecycle_snapshot_root_binding,
        lifecycle_static_report_path=lifecycle_static_report_path,
        lifecycle_static_report_sha256=lifecycle_static_report_sha256,
    )
    binder.atomic_write_json(report_path, report)
    return report


def verify_existing_dir(
    *,
    snapshot_root: Path,
    existing_dir: Path,
    lifecycle_static_report_path: Path | None = DEFAULT_LIFECYCLE_STATIC_REPORT,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="obelisk-player-identity-planning-verify-") as temp_dir:
        generated_dir = Path(temp_dir) / "generated"
        generated_report = build_into_dir(
            snapshot_root=snapshot_root,
            output_dir=generated_dir,
            lifecycle_static_report_path=lifecycle_static_report_path,
            verify_existing_dir=existing_dir,
        )
        if generated_report.get("valid") is not True:
            return generated_report

        blockers: list[dict[str, Any]] = []
        checked_outputs: dict[str, dict[str, Any]] = {}
        checked_optional_outputs: dict[str, dict[str, Any]] = {}
        for name in (
            FIRST_EVIDENCE_OUTPUT_NAME,
            binder.LIFECYCLE_OUTPUT_NAME,
            binder.PRINCIPAL_OUTPUT_NAME,
        ):
            existing_path = existing_dir / name
            generated_path = generated_dir / name
            if not existing_path.is_file():
                blockers.append({"reason": "planning_manifest_missing", "path": str(existing_path)})
                continue
            existing_sha = sha256_file(existing_path)
            generated_sha = sha256_file(generated_path)
            checked_outputs[name] = {
                "path": str(existing_path),
                "existing_sha256": existing_sha,
                "generated_sha256": generated_sha,
                "matches_generated": existing_sha == generated_sha,
            }
            if existing_sha != generated_sha:
                blockers.append(
                    {
                        "reason": "stale_or_mismatched_planning_manifest",
                        "path": str(existing_path),
                        "expected_generated_sha256": generated_sha,
                        "actual_sha256": existing_sha,
                    }
                )

        existing_report_path = existing_dir / REPORT_OUTPUT_NAME
        if not existing_report_path.is_file():
            blockers.append({"reason": "planning_manifest_build_report_missing", "path": str(existing_report_path)})
        else:
            existing_report = load_json(existing_report_path, "existing build report")
            if existing_report.get("schema") != REPORT_SCHEMA:
                blockers.append(
                    {
                        "reason": "planning_manifest_build_report_schema_mismatch",
                        "path": str(existing_report_path),
                        "actual": existing_report.get("schema"),
                    }
                )
            existing_outputs = existing_report.get("outputs") if isinstance(existing_report.get("outputs"), dict) else {}
            output_key_by_name = {
                FIRST_EVIDENCE_OUTPUT_NAME: "first_evidence",
                binder.LIFECYCLE_OUTPUT_NAME: "lifecycle_anchor_candidates",
                binder.PRINCIPAL_OUTPUT_NAME: "principal_invalidation_policy",
            }
            for file_name, output_key in output_key_by_name.items():
                record = existing_outputs.get(output_key) if isinstance(existing_outputs, dict) else None
                expected_sha = checked_outputs.get(file_name, {}).get("existing_sha256")
                actual_sha = record.get("sha256") if isinstance(record, dict) else None
                if actual_sha != expected_sha:
                    blockers.append(
                        {
                            "reason": "planning_manifest_build_report_output_hash_mismatch",
                            "path": str(existing_report_path),
                            "output": output_key,
                            "expected_sha256": expected_sha,
                            "actual_sha256": actual_sha,
                        }
                    )

        all_six_path = existing_dir / ALL_SIX_PLANNING_GAP_OUTPUT_NAME
        if all_six_path.exists():
            if not all_six_path.is_file():
                blockers.append({"reason": "all_six_planning_gap_artifact_not_file", "path": str(all_six_path)})
            else:
                all_six_artifact = load_json(all_six_path, "existing all-six planning-gap artifact")
                all_six_blockers = all_six_planning_gap_artifact_blockers(
                    all_six_artifact,
                    snapshot_root=snapshot_root,
                )
                checked_optional_outputs[ALL_SIX_PLANNING_GAP_OUTPUT_NAME] = {
                    "path": str(all_six_path),
                    "sha256": sha256_file(all_six_path),
                    "schema": all_six_artifact.get("schema"),
                    "valid": not all_six_blockers,
                }
                for blocker in all_six_blockers:
                    blockers.append(
                        {
                            "reason": "all_six_planning_gap_artifact_invalid",
                            "path": str(all_six_path),
                            "detail": blocker.get("reason"),
                            "label": blocker.get("label"),
                        }
                    )

        fname_mismatch_path = existing_dir / FNAME_MISMATCH_OUTPUT_NAME
        if fname_mismatch_path.exists():
            if not fname_mismatch_path.is_file():
                blockers.append({"reason": "fname_mismatch_artifact_not_file", "path": str(fname_mismatch_path)})
            else:
                fname_mismatch_artifact = load_json(fname_mismatch_path, "existing FName mismatch artifact")
                fname_mismatch_blockers = fname_mismatch_artifact_blockers(
                    fname_mismatch_artifact,
                    snapshot_root=snapshot_root,
                )
                checked_optional_outputs[FNAME_MISMATCH_OUTPUT_NAME] = {
                    "path": str(fname_mismatch_path),
                    "sha256": sha256_file(fname_mismatch_path),
                    "schema": fname_mismatch_artifact.get("schema"),
                    "valid": not fname_mismatch_blockers,
                }
                for blocker in fname_mismatch_blockers:
                    blockers.append(
                        {
                            "reason": "fname_mismatch_artifact_invalid",
                            "path": str(fname_mismatch_path),
                            "detail": blocker.get("reason"),
                            "label": blocker.get("label"),
                        }
                    )

        valid = not blockers and generated_report.get("valid") is True
        return {
            "schema": REPORT_SCHEMA,
            "mode": "verify_existing",
            "valid": valid,
            "accepted_for_planning": valid,
            "planning_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
            "v1_completion_ready": False,
            "server_operations_authorized": False,
            "runtime_work_authorized": False,
            "snapshot_root": str(snapshot_root),
            "verify_existing_dir": str(existing_dir),
            "blockers": blockers,
            "checked_outputs": checked_outputs,
            "checked_optional_outputs": checked_optional_outputs,
            "generated_report_valid": generated_report.get("valid") is True,
            "non_claims": NON_CLAIMS,
        }


def main() -> int:
    args = parse_args()
    snapshot_root = safe_snapshot_root(args.snapshot_root)
    lifecycle_static_report_path = safe_optional_input_file(args.lifecycle_static_report, "lifecycle-static-report")
    if args.verify_existing_dir is not None:
        report = verify_existing_dir(
            snapshot_root=snapshot_root,
            existing_dir=safe_existing_dir(args.verify_existing_dir),
            lifecycle_static_report_path=lifecycle_static_report_path,
        )
    else:
        report = build_into_dir(
            snapshot_root=snapshot_root,
            output_dir=args.output_dir,
            lifecycle_static_report_path=lifecycle_static_report_path,
        )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    if not report["valid"] and "lifecycle_anchor_candidate_blocker_reasons" in report:
        diagnostic = report.get("lifecycle_provenance_diagnostic", {})
        print(
            "generated lifecycle-anchor candidates failed validation"
            + ": "
            + json.dumps(
                {
                    "blockers": report["lifecycle_anchor_candidate_blocker_reasons"],
                    "diagnostic": diagnostic,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
