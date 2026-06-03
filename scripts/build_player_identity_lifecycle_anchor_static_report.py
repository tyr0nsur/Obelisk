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


REPORT_SCHEMA = "obelisk.players-identity-lifecycle-anchor-static-report.v1"
TARGETS = (
    ("session_start", "ShooterGameMode.HandleNewPlayer"),
    ("session_end", "ShooterGameMode.OnLogout"),
)
NON_CLAIMS = [
    "repo-local static lifecycle-anchor report only",
    "does not fabricate runtime evidence or cite protected live-server paths",
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
    expected = lifecycle_checker.LIFECYCLE_LAYOUT_CANDIDATE_TARGETS[target]
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
    if payload.get("binary_sha256") != expected_binary_sha256:
        blockers.append("static_orientation_binary_sha256_mismatch")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if payload.get(key) is not False:
            blockers.append(f"static_orientation_{key}_not_false")
    checked = payload.get("checked_targets")
    checked_by_target = {row.get("target"): row for row in checked if isinstance(row, dict)} if isinstance(checked, list) else {}
    for _, target in TARGETS:
        row = checked_by_target.get(target)
        if not isinstance(row, dict):
            blockers.append(f"static_orientation_missing_target:{target}")
        elif row.get("status") != "candidate_orientation_valid":
            blockers.append(f"static_orientation_target_not_valid:{target}")
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
    for role, target in TARGETS:
        path = paths.get(target)
        if path is None:
            raise SystemExit(f"snapshot manifest does not contain required lifecycle target: {target}")
        targets.append(expected_snapshot_record(role, target, path))

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
            "num_parms": target["num_parms"],
            "parms_size": target["parms_size"],
            "property_order": target["property_order"],
        }
        for target in targets
    ]
    return {
        "schema": REPORT_SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "ready": ready,
        "accepted_for_lifecycle_anchor_binding": ready,
        "corroboration_status": "static_accepted" if ready else "blocked",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_work_authorized": False,
        "server_operations_authorized": False,
        "artifact_identity": {
            "ark_binary_sha256": binary_sha256,
            "obelisk_commit": obelisk_commit,
            "build_type": "sanitized_snapshot_static_report",
            "target_set_revision": "reflection_target_sets.py:players-lifecycle-anchor-candidates",
            "source_artifact_ids": source_ids,
            "path_redacted": True,
        },
        "accepted_targets": accepted_targets,
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
