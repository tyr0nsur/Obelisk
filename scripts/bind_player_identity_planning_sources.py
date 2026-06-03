#!/usr/bin/env python3
"""Bind player-identity planning artifacts to first-evidence provenance."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import artifact_identity
import check_player_identity_first_evidence_readiness as first_evidence_readiness
import check_player_identity_lifecycle_anchor_candidates as lifecycle_anchor_candidates
import check_player_identity_principal_invalidation_policy as principal_invalidation_policy
import validate_offline_artifact_gate as offline_artifact_gate
from protected_paths import reject_protected_input_path, reject_protected_output_path, reject_symlink_component


REPORT_SCHEMA = "obelisk.player-identity-planning-source-binding-report.v1"
LIFECYCLE_OUTPUT_NAME = "players-identity-lifecycle-anchor-candidates.json"
PRINCIPAL_OUTPUT_NAME = "players-identity-principal-invalidation-policy.json"
REPORT_OUTPUT_NAME = "player-identity-planning-source-binding-report.json"
REQUIRED_LIFECYCLE_SNAPSHOT_TARGETS = (
    "ShooterGameMode.HandleNewPlayer",
    "ShooterGameMode.OnLogout",
)
NON_CLAIMS = [
    "no runtime or server operation was performed",
    "no ARK process was started, stopped, restarted, attached, or observed",
    "no public player identity is promoted",
    "no permissions/admin, command response, or commands/replies surface is promoted",
    "no public SDK, public ABI, release, or v1 completion readiness is claimed",
    "no Discord or GitHub publication is authorized",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-evidence", type=Path, required=True, help="players-identity first-evidence JSON.")
    parser.add_argument(
        "--lifecycle-anchor-candidates",
        type=Path,
        required=True,
        help="Consume-only lifecycle-anchor candidates JSON to bind.",
    )
    parser.add_argument(
        "--principal-invalidation-policy",
        type=Path,
        required=True,
        help="Consume-only principal invalidation policy JSON to bind.",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for bound planning artifacts.")
    parser.add_argument("--json", action="store_true", help="Emit the binding report JSON to stdout.")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> tuple[dict[str, Any], Path]:
    reject_symlink_component(path, label)
    resolved = reject_protected_input_path(path, label)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{resolved}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{resolved}: top-level JSON must be an object")
    return payload, resolved


def prepare_output_dir(path: Path) -> Path:
    reject_symlink_component(path, "output-dir")
    resolved = reject_protected_output_path(path, "output-dir")
    resolved.mkdir(parents=True, exist_ok=True)
    reject_symlink_component(resolved, "output-dir")
    if not resolved.is_dir():
        raise SystemExit(f"output-dir is not a directory: {resolved}")
    return resolved


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    reject_symlink_component(path.parent, f"{path.name} parent")
    if path.exists() or path.is_symlink():
        reject_symlink_component(path, path.name)
        if path.is_symlink():
            raise SystemExit(f"{path.name} must not be a symlink: {path}")
    reject_protected_output_path(path, path.name)
    encoded = artifact_identity.canonical_json_bytes(payload) + b"\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def first_evidence_snapshot_by_target(first_evidence: dict[str, Any]) -> dict[str, dict[str, str]]:
    generated_from = first_evidence.get("generated_from")
    snapshots = (
        generated_from.get("input_snapshots")
        if isinstance(generated_from, dict) and isinstance(generated_from.get("input_snapshots"), list)
        else []
    )
    result: dict[str, dict[str, str]] = {}
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue
        target = snapshot.get("target")
        snapshot_id = snapshot.get("id")
        snapshot_sha256 = snapshot.get("sha256")
        if isinstance(target, str) and isinstance(snapshot_id, str) and isinstance(snapshot_sha256, str):
            result[target] = {"id": snapshot_id, "sha256": snapshot_sha256}
    return result


def snapshot_manifest_target_paths(snapshot_root: Path) -> dict[str, Path]:
    manifest_payload, manifest_path = load_json(snapshot_root / "manifest.json", "snapshot manifest")
    if manifest_payload.get("schema") != "obelisk.ufunction-snapshot-manifest.v1":
        raise SystemExit("snapshot manifest schema mismatch")
    for key, expected in (("source", "offline_core"), ("status", "candidate-only")):
        if manifest_payload.get(key) != expected:
            raise SystemExit(f"snapshot manifest {key} mismatch")
    if not isinstance(manifest_payload.get("ark_binary_sha256"), str) or not manifest_payload["ark_binary_sha256"]:
        raise SystemExit("snapshot manifest ark_binary_sha256 missing")
    sha_prefix = manifest_payload.get("sha_prefix")
    targets = manifest_payload.get("targets")
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
            raise SystemExit(f"snapshot manifest contains duplicate target: {target}")
        path = manifest_path.parent / sha_prefix / module / file_name
        reject_symlink_component(path, f"snapshot-root:{target}")
        resolved = reject_protected_input_path(path, f"snapshot-root:{target}")
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise SystemExit(f"snapshot-root:{target} resolves outside snapshot-root: {resolved}") from exc
        result[target] = resolved
    return result


def validate_snapshot_file_identity(path: Path, target: str) -> None:
    payload, _ = load_json(path, f"snapshot-root:{target}")
    if payload.get("schema") != "obelisk.ufunction-chain.snapshot.v1":
        raise SystemExit(f"snapshot-root:{target} schema mismatch")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"snapshot-root:{target} must contain exactly one target")
    identity = targets[0].get("target")
    if not isinstance(identity, dict):
        raise SystemExit(f"snapshot-root:{target} target identity missing")
    observed = f"{identity.get('outer_name')}.{identity.get('name')}"
    if observed != target:
        raise SystemExit(f"snapshot-root:{target} target mismatch: observed {observed}")


def lifecycle_anchor_snapshot_root_diagnosis(
    *,
    lifecycle: dict[str, Any],
    snapshot_root: Path,
) -> dict[str, Any]:
    blockers: list[str] = []
    expected_by_target: dict[str, str] = {}
    try:
        paths_by_target = snapshot_manifest_target_paths(snapshot_root)
    except SystemExit:
        raise
    anchors = lifecycle.get("candidate_anchors")
    anchors_by_target = {
        anchor.get("target"): anchor
        for anchor in anchors
        if isinstance(anchor, dict) and anchor.get("accepted") is True and isinstance(anchor.get("target"), str)
    } if isinstance(anchors, list) else {}

    for target in REQUIRED_LIFECYCLE_SNAPSHOT_TARGETS:
        snapshot_path = paths_by_target.get(target)
        if snapshot_path is None:
            blockers.append("lifecycle_anchor_snapshot_root_manifest_target_missing")
            continue
        if not snapshot_path.is_file():
            blockers.append("lifecycle_anchor_snapshot_root_file_missing")
            continue
        validate_snapshot_file_identity(snapshot_path, target)
        expected_sha256 = sha256_file(snapshot_path)
        expected_by_target[target] = expected_sha256
        anchor = anchors_by_target.get(target)
        evidence = anchor.get("evidence") if isinstance(anchor, dict) else None
        observed_sha256 = evidence.get("source_snapshot_sha256") if isinstance(evidence, dict) else None
        if not isinstance(observed_sha256, str) or not observed_sha256:
            blockers.append("lifecycle_anchor_source_snapshot_evidence_missing")
        elif observed_sha256 != expected_sha256:
            blockers.append("lifecycle_anchor_source_snapshot_root_mismatch")

    return {
        "ready": not blockers,
        "blockers": sorted(set(blockers)),
        "required_targets": list(REQUIRED_LIFECYCLE_SNAPSHOT_TARGETS),
        "expected_snapshot_sha256_by_target": expected_by_target,
    }


def validate_lifecycle_anchor_snapshot_root(
    *,
    lifecycle: dict[str, Any],
    snapshot_root: Path,
) -> dict[str, Any]:
    diagnosis = lifecycle_anchor_snapshot_root_diagnosis(lifecycle=lifecycle, snapshot_root=snapshot_root)
    if diagnosis["blockers"]:
        raise SystemExit(
            "player identity planning source binding failed snapshot-root provenance: "
            + json.dumps({"lifecycle_anchor_candidates": diagnosis["blockers"]}, sort_keys=True)
        )
    return diagnosis


def validation_reasons(blockers: list[dict[str, Any]]) -> list[str]:
    return [str(blocker.get("reason")) for blocker in blockers]


def lifecycle_has_bound_static_anchor_provenance(lifecycle: dict[str, Any]) -> bool:
    anchors = lifecycle.get("candidate_anchors")
    if not isinstance(anchors, list):
        return False
    required = set(REQUIRED_LIFECYCLE_SNAPSHOT_TARGETS)
    seen: set[str] = set()
    report_hashes: set[str] = set()
    for anchor in anchors:
        if not isinstance(anchor, dict) or anchor.get("accepted") is not True:
            continue
        target = anchor.get("target")
        if target not in required:
            continue
        corroboration = anchor.get("corroboration")
        if not isinstance(corroboration, dict) or corroboration.get("status") != "static_accepted":
            return False
        report_hash = corroboration.get("static_report_sha256")
        if not isinstance(report_hash, str) or lifecycle_anchor_candidates.SHA256_RE.fullmatch(report_hash) is None:
            return False
        seen.add(str(target))
        report_hashes.add(report_hash)
    if seen != required or len(report_hashes) != 1:
        return False

    artifact = lifecycle.get("artifact_identity")
    source_ids = artifact.get("source_artifact_ids") if isinstance(artifact, dict) else None
    parsed_source_ids = lifecycle_anchor_candidates.parse_source_artifact_ids(source_ids, [], "$.artifact_identity.source_artifact_ids")
    for key, placeholders in lifecycle_anchor_candidates.PLACEHOLDER_SOURCE_ARTIFACT_IDS.items():
        if any(value in placeholders for value in parsed_source_ids.get(key, [])):
            return False
    return True


def expected_lifecycle_source_binding(
    lifecycle: dict[str, Any],
    first_evidence: dict[str, Any],
) -> dict[str, Any]:
    artifact = lifecycle.get("artifact_identity")
    acceptance = lifecycle.get("lifecycle_acceptance")
    source_ids = first_evidence_readiness.first_evidence_source_artifact_ids(first_evidence)
    return {
        "lifecycle_manifest_schema": lifecycle.get("schema"),
        "artifact_identity_source_artifact_ids": list(
            artifact.get("source_artifact_ids", []) if isinstance(artifact, dict) else []
        )
        if isinstance(artifact, dict)
        else list(source_ids),
        "accepted_start_targets": list(acceptance.get("accepted_start_targets", []))
        if isinstance(acceptance, dict)
        else [],
        "accepted_end_targets": list(acceptance.get("accepted_end_targets", []))
        if isinstance(acceptance, dict)
        else [],
    }


def validate_prebind_provenance(
    *,
    first_evidence: dict[str, Any],
    lifecycle: dict[str, Any],
    principal: dict[str, Any],
) -> None:
    source_ids = first_evidence_readiness.first_evidence_source_artifact_ids(first_evidence)
    if not source_ids:
        raise SystemExit("first-evidence artifact_identity.source_artifact_ids is empty")
    lifecycle_artifact = lifecycle.get("artifact_identity")
    lifecycle_source_ids = (
        lifecycle_artifact.get("source_artifact_ids") if isinstance(lifecycle_artifact, dict) else None
    )
    if list(lifecycle_source_ids or []) != list(source_ids) and not lifecycle_has_bound_static_anchor_provenance(lifecycle):
        raise SystemExit(
            "player identity planning source binding failed prebind provenance: "
            + json.dumps(
                {
                    "lifecycle_anchor_candidates": [
                        "lifecycle_anchor_source_artifact_ids_mismatch"
                    ]
                },
                sort_keys=True,
            )
        )

    acceptance = lifecycle.get("lifecycle_acceptance")
    accepted_start_targets = (
        acceptance.get("accepted_start_targets") if isinstance(acceptance, dict) else []
    )
    accepted_end_targets = acceptance.get("accepted_end_targets") if isinstance(acceptance, dict) else []
    source = principal.get("lifecycle_layout_source")
    if not isinstance(source, dict):
        raise SystemExit(
            "player identity planning source binding failed prebind provenance: "
            + json.dumps({"principal_invalidation_policy": ["lifecycle_layout_source_missing"]}, sort_keys=True)
        )
    principal_errors: list[str] = []
    if source.get("start_anchor") not in accepted_start_targets:
        principal_errors.append("principal_start_anchor_not_accepted_by_lifecycle")
    if source.get("end_anchor") not in accepted_end_targets:
        principal_errors.append("principal_end_anchor_not_accepted_by_lifecycle")
    expected_binding = expected_lifecycle_source_binding(lifecycle, first_evidence)
    existing_binding = source.get("source_binding")
    if existing_binding is not None and existing_binding != expected_binding:
        principal_errors.append("principal_lifecycle_source_binding_mismatch")
    if principal_errors:
        raise SystemExit(
            "player identity planning source binding failed prebind provenance: "
            + json.dumps({"principal_invalidation_policy": principal_errors}, sort_keys=True)
        )


def validate_inputs(
    *,
    first_evidence: dict[str, Any],
    lifecycle: dict[str, Any],
    principal: dict[str, Any],
) -> None:
    first_blockers = offline_artifact_gate.validate_players_identity_first_evidence_manifest(
        first_evidence,
        label="first-evidence",
        mode="consume",
    )
    lifecycle_blockers = lifecycle_anchor_candidates.validate_manifest(lifecycle, promote=False)
    principal_blockers = principal_invalidation_policy.validate_manifest(principal, check_mode="consume").blockers
    blockers = {
        "first_evidence": validation_reasons(first_blockers),
        "lifecycle_anchor_candidates": validation_reasons(lifecycle_blockers),
        "principal_invalidation_policy": validation_reasons(principal_blockers),
    }
    failed = {key: values for key, values in blockers.items() if values}
    if failed:
        raise SystemExit("player identity planning source binding failed validation: " + json.dumps(failed, sort_keys=True))
    validate_prebind_provenance(first_evidence=first_evidence, lifecycle=lifecycle, principal=principal)


def bind_lifecycle_to_first_evidence(
    lifecycle: dict[str, Any],
    first_evidence: dict[str, Any],
) -> dict[str, Any]:
    bound = copy.deepcopy(lifecycle)
    source_ids = first_evidence_readiness.first_evidence_source_artifact_ids(first_evidence)
    if not source_ids:
        raise SystemExit("first-evidence artifact_identity.source_artifact_ids is empty")
    artifact = bound.get("artifact_identity")
    if not isinstance(artifact, dict):
        raise SystemExit("lifecycle-anchor candidates artifact_identity missing")
    if not lifecycle_has_bound_static_anchor_provenance(lifecycle):
        artifact["source_artifact_ids"] = list(source_ids)

    snapshots_by_target = first_evidence_snapshot_by_target(first_evidence)
    anchors = bound.get("candidate_anchors")
    if not isinstance(anchors, list):
        raise SystemExit("lifecycle-anchor candidates candidate_anchors missing")
    for anchor in anchors:
        if not isinstance(anchor, dict) or anchor.get("accepted") is not True:
            continue
        target = anchor.get("target")
        evidence = anchor.get("evidence")
        snapshot = snapshots_by_target.get(target) if isinstance(target, str) else None
        if snapshot is None or not isinstance(evidence, dict):
            continue
        evidence["source_snapshot"] = snapshot["id"]
        evidence["source_snapshot_sha256"] = snapshot["sha256"]
    return bound


def bind_principal_to_lifecycle(principal: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    bound = copy.deepcopy(principal)
    source = bound.get("lifecycle_layout_source")
    if not isinstance(source, dict):
        raise SystemExit("principal invalidation policy lifecycle_layout_source missing")
    artifact = lifecycle.get("artifact_identity")
    acceptance = lifecycle.get("lifecycle_acceptance")
    if not isinstance(artifact, dict) or not isinstance(acceptance, dict):
        raise SystemExit("bound lifecycle manifest is missing artifact_identity or lifecycle_acceptance")
    source["source_binding"] = expected_lifecycle_source_binding(lifecycle, {"artifact_identity": artifact})
    return bound


def source_record(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(path),
        "resolved_path": str(path.resolve()),
        "sha256": sha256_file(path),
        "schema": payload.get("schema"),
    }


def build_report(
    *,
    first_path: Path,
    lifecycle_path: Path,
    principal_path: Path,
    first_evidence: dict[str, Any],
    lifecycle_output: Path,
    principal_output: Path,
    bound_lifecycle: dict[str, Any],
    bound_principal: dict[str, Any],
) -> dict[str, Any]:
    lifecycle_diagnosis = first_evidence_readiness.lifecycle_anchor_candidate_manifest_diagnosis(lifecycle_output)
    principal_diagnosis = first_evidence_readiness.principal_invalidation_policy_diagnosis(principal_output)
    blockers = first_evidence_readiness.planning_provenance_blockers(
        first_evidence_payload=first_evidence,
        lifecycle_candidate_diagnosis=lifecycle_diagnosis,
        principal_policy_diagnosis=principal_diagnosis,
    )
    return {
        "schema": REPORT_SCHEMA,
        "ready": not blockers,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "blockers": blockers,
        "sources": {
            "first_evidence": source_record(first_path, first_evidence),
            "lifecycle_anchor_candidates": source_record(lifecycle_path, bound_lifecycle),
            "principal_invalidation_policy": source_record(principal_path, bound_principal),
        },
        "outputs": {
            "lifecycle_anchor_candidates": {
                "path": str(lifecycle_output),
                "sha256": sha256_file(lifecycle_output),
                "schema": bound_lifecycle.get("schema"),
            },
            "principal_invalidation_policy": {
                "path": str(principal_output),
                "sha256": sha256_file(principal_output),
                "schema": bound_principal.get("schema"),
            },
        },
        "planning_provenance": {
            "ready": not blockers,
            "blockers": blockers,
            "lifecycle_anchor_candidates": lifecycle_diagnosis,
            "principal_invalidation_policy": principal_diagnosis,
        },
        "non_claims": NON_CLAIMS,
    }


def main() -> int:
    args = parse_args()
    first_evidence, first_path = load_json(args.first_evidence, "first-evidence")
    lifecycle, lifecycle_path = load_json(args.lifecycle_anchor_candidates, "lifecycle-anchor-candidates")
    principal, principal_path = load_json(args.principal_invalidation_policy, "principal-invalidation-policy")
    validate_inputs(first_evidence=first_evidence, lifecycle=lifecycle, principal=principal)

    output_dir = prepare_output_dir(args.output_dir)
    lifecycle_output = output_dir / LIFECYCLE_OUTPUT_NAME
    principal_output = output_dir / PRINCIPAL_OUTPUT_NAME
    report_output = output_dir / REPORT_OUTPUT_NAME

    bound_lifecycle = bind_lifecycle_to_first_evidence(lifecycle, first_evidence)
    lifecycle_bound_blockers = lifecycle_anchor_candidates.validate_manifest(bound_lifecycle, promote=False)
    if lifecycle_bound_blockers:
        raise SystemExit(
            "bound lifecycle-anchor candidates failed validation: "
            + json.dumps(validation_reasons(lifecycle_bound_blockers), sort_keys=True)
        )

    bound_principal = bind_principal_to_lifecycle(principal, bound_lifecycle)
    principal_bound_blockers = principal_invalidation_policy.validate_manifest(
        bound_principal,
        check_mode="consume",
    ).blockers
    if principal_bound_blockers:
        raise SystemExit(
            "bound principal invalidation policy failed validation: "
            + json.dumps(validation_reasons(principal_bound_blockers), sort_keys=True)
        )

    atomic_write_json(lifecycle_output, bound_lifecycle)
    atomic_write_json(principal_output, bound_principal)
    report = build_report(
        first_path=first_path,
        lifecycle_path=lifecycle_path,
        principal_path=principal_path,
        first_evidence=first_evidence,
        lifecycle_output=lifecycle_output,
        principal_output=principal_output,
        bound_lifecycle=bound_lifecycle,
        bound_principal=bound_principal,
    )
    atomic_write_json(report_output, report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
