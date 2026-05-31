#!/usr/bin/env python3
"""Read-only preflight for player-identity reflection inventory packs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from reflection_target_sets import schema_target_list  # noqa: E402
from snapshot_evidence_pack import (  # noqa: E402
    CORE_DUMP_EVIDENCE_PACK_SCHEMA,
    SHA256_RE,
    manifest_relative_path,
    reject_protected_input_path,
    reject_symlink_component,
)


REPORT_SCHEMA = "obelisk.reflection-inventory-pack-readiness-check.v1"
PACK_SCHEMA = "obelisk.reflection-inventory-pack.v1"
REFLECTION_INVENTORY_COMPARISON_SCHEMA = "obelisk.reflection-inventory-pack-comparison.v1"
SCRIPTSTRUCT_PACK_SCHEMA = "obelisk.scriptstruct-inventory-pack.v1"
PLAYER_IDENTITY_TARGET_SET = "players-identity-lifecycle-intake"
PLAYER_IDENTITY_TARGETS = tuple(
    schema_target_list(PLAYER_IDENTITY_TARGET_SET, "obelisk.ufunction-chain.snapshot.v1")
)
REQUIRED_TARGETS = (
    "ShooterPlayerController.ServerListPlayers",
    "ShooterPlayerController.ServerKickPlayer",
)
REDACTED_FUNCTION_KEYS = {
    "family",
    "function_flags",
    "name",
    "num_parms",
    "outer_class_name",
    "outer_name",
    "parms_size",
}
ARTIFACT_PACK_MANIFEST_FILENAME = "artifact-pack.manifest.json"
MANIFEST_FILENAMES = {"manifest.json", ARTIFACT_PACK_MANIFEST_FILENAME}
MAX_REASON_ITEMS = 20
MAX_INVENTORY_ROW_BLOCKERS = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search a non-protected artifact root for a candidate-only "
            "obelisk.reflection-inventory-pack.v1 usable to plan ServerListPlayers "
            "and ServerKickPlayer focal snapshots."
        )
    )
    parser.add_argument("--root", required=True, type=Path, help="Non-protected root to search.")
    parser.add_argument("--max-depth", type=int, default=6, help="Maximum directory depth below --root.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Compatibility flag; output is JSON with or without this option.",
    )
    return parser.parse_args()


def reason(code: str, **fields: object) -> dict[str, object]:
    return {"reason": code, **fields}


def bounded_list_fields(field: str, values: list[Any]) -> dict[str, object]:
    if len(values) <= MAX_REASON_ITEMS:
        return {field: values}
    return {
        field: values[:MAX_REASON_ITEMS],
        f"{field}_count": len(values),
        f"omitted_{field}_count": len(values) - MAX_REASON_ITEMS,
    }


def player_identity_target_set_expectation_fields() -> dict[str, object]:
    return {
        "target_set": PLAYER_IDENTITY_TARGET_SET,
        "expected_target_count": len(PLAYER_IDENTITY_TARGETS),
        "expected_targets": list(PLAYER_IDENTITY_TARGETS),
    }


def string_list(value: object) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return None
    return value


def append_inventory_row_blocker(
    blockers: list[dict[str, object]],
    entry: dict[str, object],
    emitted_count: int,
    omitted_count: int,
) -> tuple[int, int]:
    if emitted_count < MAX_INVENTORY_ROW_BLOCKERS:
        blockers.append(entry)
        return emitted_count + 1, omitted_count
    return emitted_count, omitted_count + 1


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing"
    except OSError as exc:
        return None, f"unreadable:{exc}"
    except json.JSONDecodeError as exc:
        return None, f"malformed_json:{exc}"
    if not isinstance(payload, dict):
        return None, "not_object"
    return payload, None


def is_manifest_filename(path: Path) -> bool:
    return path.name in MANIFEST_FILENAMES or (path.suffix == ".json" and "manifest" in path.name)


def candidate_manifest_paths(root: Path, max_depth: int) -> list[Path]:
    if max_depth < 0:
        raise SystemExit("--max-depth must be non-negative")
    reject_symlink_component(root, "--root")
    resolved = reject_protected_input_path(root, "--root")
    if resolved.is_file():
        return [resolved] if is_manifest_filename(resolved) else []
    if not resolved.is_dir():
        return []

    manifest_paths: list[Path] = []
    root_depth = len(resolved.parts)
    for directory, dirnames, filenames in os.walk(resolved, followlinks=False):
        current = Path(directory)
        depth = len(current.parts) - root_depth
        dirnames[:] = [name for name in dirnames if not (current / name).is_symlink()]
        if depth >= max_depth:
            dirnames[:] = []
        for filename in filenames:
            path = current / filename
            if is_manifest_filename(path) and not path.is_symlink():
                manifest_paths.append(path)
    return sorted(manifest_paths)


def inventory_path_from_manifest(manifest_path: Path, manifest: dict[str, Any]) -> Path | None:
    artifacts = manifest.get("artifacts")
    name = artifacts.get("ufunction_inventory") if isinstance(artifacts, dict) else None
    if name is None:
        name = "ufunction-inventory.json"
    if not isinstance(name, str) or not name or Path(name).name != name:
        return None
    return manifest_path.parent / name


def target_from_row(row: dict[str, Any]) -> str | None:
    outer = row.get("outer_name")
    name = row.get("name")
    if not isinstance(outer, str) or not outer or not isinstance(name, str) or not name:
        return None
    return f"{outer}.{name}"


def load_inventory_targets(path: Path) -> tuple[set[str], list[dict[str, object]], dict[str, Any] | None]:
    blockers: list[dict[str, object]] = []
    try:
        reject_symlink_component(path, "ufunction inventory")
        resolved = reject_protected_input_path(path, "ufunction inventory")
    except SystemExit as exc:
        return set(), [reason("missing_ufunction_inventory", path=str(path), detail=str(exc))], None
    payload, error = load_json(resolved)
    if payload is None:
        return set(), [reason("missing_ufunction_inventory", path=str(path), detail=error)], None
    rows = payload.get("functions")
    if not isinstance(rows, list):
        return set(), [reason("missing_ufunction_inventory", path=str(path), detail="functions_not_list")], payload

    targets: set[str] = set()
    seen: set[str] = set()
    duplicates: set[str] = set()
    row_blockers_emitted = 0
    row_blockers_omitted = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            row_blockers_emitted, row_blockers_omitted = append_inventory_row_blocker(
                blockers,
                reason("missing_ufunction_inventory", path=str(path), detail=f"functions[{index}]_not_object"),
                row_blockers_emitted,
                row_blockers_omitted,
            )
            continue
        extra = sorted(set(row) - REDACTED_FUNCTION_KEYS)
        missing = sorted(REDACTED_FUNCTION_KEYS - set(row))
        if extra or missing:
            row_blockers_emitted, row_blockers_omitted = append_inventory_row_blocker(
                blockers,
                reason(
                    "missing_ufunction_inventory",
                    path=str(path),
                    detail=f"functions[{index}]_redaction_schema_mismatch",
                    **bounded_list_fields("extra_keys", extra),
                    **bounded_list_fields("missing_keys", missing),
                ),
                row_blockers_emitted,
                row_blockers_omitted,
            )
            continue
        target = target_from_row(row)
        if target is None:
            row_blockers_emitted, row_blockers_omitted = append_inventory_row_blocker(
                blockers,
                reason("missing_ufunction_inventory", path=str(path), detail=f"functions[{index}]_missing_target_identity"),
                row_blockers_emitted,
                row_blockers_omitted,
            )
            continue
        if target in seen:
            duplicates.add(target)
        seen.add(target)
        targets.add(target)
    if row_blockers_omitted:
        blockers.append(
            reason(
                "missing_ufunction_inventory",
                path=str(path),
                detail="inventory_row_errors_omitted",
                omitted_count=row_blockers_omitted,
            )
        )
    if duplicates:
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(path),
                **bounded_list_fields("duplicate_targets", sorted(duplicates)),
            )
        )
    return targets, blockers, payload


def player_identity_target_set_scope_blockers(
    manifest_path: Path,
    manifest: dict[str, Any],
    inventory_path: Path,
    inventory: dict[str, Any] | None,
) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    inputs = manifest.get("inputs")
    manifest_target_sets = inputs.get("target_sets") if isinstance(inputs, dict) else None
    if not isinstance(manifest_target_sets, list) or PLAYER_IDENTITY_TARGET_SET not in manifest_target_sets:
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(manifest_path),
                field="inputs.target_sets",
                required=PLAYER_IDENTITY_TARGET_SET,
                recorded=manifest_target_sets,
            )
        )
    manifest_target_set_values = string_list(manifest_target_sets)
    if isinstance(manifest_target_sets, list) and manifest_target_set_values is None:
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(manifest_path),
                field="inputs.target_sets",
                detail="must_be_non_empty_string_list",
                recorded=manifest_target_sets,
            )
        )

    coverage = inventory.get("target_set_coverage") if isinstance(inventory, dict) else None
    if not isinstance(coverage, dict):
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(inventory_path),
                field="target_set_coverage",
                required=PLAYER_IDENTITY_TARGET_SET,
                **player_identity_target_set_expectation_fields(),
            )
        )
        return blockers

    coverage_target_sets = coverage.get("target_sets")
    if not isinstance(coverage_target_sets, list) or PLAYER_IDENTITY_TARGET_SET not in coverage_target_sets:
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(inventory_path),
                field="target_set_coverage.target_sets",
                required=PLAYER_IDENTITY_TARGET_SET,
                recorded=coverage_target_sets,
                **player_identity_target_set_expectation_fields(),
            )
        )
    coverage_target_set_values = string_list(coverage_target_sets)
    if isinstance(coverage_target_sets, list) and coverage_target_set_values is None:
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(inventory_path),
                field="target_set_coverage.target_sets",
                detail="must_be_non_empty_string_list",
                recorded=coverage_target_sets,
                **player_identity_target_set_expectation_fields(),
            )
        )
    if (
        manifest_target_set_values is not None
        and coverage_target_set_values is not None
        and sorted(manifest_target_set_values) != sorted(coverage_target_set_values)
    ):
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(inventory_path),
                field="target_set_coverage.target_sets",
                detail="does_not_match_manifest_inputs",
                recorded=coverage_target_set_values,
                manifest_target_sets=manifest_target_set_values,
                **player_identity_target_set_expectation_fields(),
            )
        )

    requested_targets = coverage.get("requested_targets")
    if not isinstance(requested_targets, list):
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(inventory_path),
                field="target_set_coverage.requested_targets",
                required=list(PLAYER_IDENTITY_TARGETS),
                **player_identity_target_set_expectation_fields(),
            )
        )
    else:
        missing = [target for target in PLAYER_IDENTITY_TARGETS if target not in requested_targets]
        if missing:
            blockers.append(
                reason(
                    "wrong_target_scope",
                    path=str(inventory_path),
                    field="target_set_coverage.requested_targets",
                    requested_target_count=len(requested_targets),
                    missing_count=len(missing),
                    missing_targets=missing,
                    **player_identity_target_set_expectation_fields(),
                )
            )
    return blockers


def manifest_scope_blockers(manifest_path: Path, manifest: dict[str, Any]) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    if manifest.get("status") != "candidate-only":
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="status", recorded=manifest.get("status")))
    if manifest.get("promotion_status") != "not_promoted_candidate_only":
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(manifest_path),
                field="promotion_status",
                recorded=manifest.get("promotion_status"),
            )
        )

    identity = manifest.get("artifact_identity")
    artifact_sha: str | None = None
    if not isinstance(identity, dict) or identity.get("artifact_kind") != "offline_core":
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="artifact_identity.artifact_kind"))
    else:
        raw_artifact_sha = identity.get("artifact_sha256")
        if not isinstance(raw_artifact_sha, str) or SHA256_RE.fullmatch(raw_artifact_sha) is None:
            blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="artifact_identity.artifact_sha256"))
        else:
            artifact_sha = raw_artifact_sha
    for field in ("capture_id", "evidence_pack_id"):
        if not isinstance(identity, dict) or not isinstance(identity.get(field), str) or not identity.get(field):
            blockers.append(reason("wrong_target_scope", path=str(manifest_path), field=f"artifact_identity.{field}"))

    binary = manifest.get("binary")
    binary_sha = binary.get("sha256") if isinstance(binary, dict) else None
    if not isinstance(binary_sha, str) or SHA256_RE.fullmatch(binary_sha) is None:
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="binary.sha256"))

    summary = manifest.get("summary")
    if not isinstance(summary, dict) or summary.get("fname_root_ready") is not True:
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="summary.fname_root_ready"))
    pack_blockers = manifest.get("blockers")
    if not isinstance(pack_blockers, list) or pack_blockers:
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="blockers", recorded=pack_blockers))

    core = manifest.get("core")
    core_sha = core.get("sha256") if isinstance(core, dict) else None
    if not isinstance(core_sha, str) or SHA256_RE.fullmatch(core_sha) is None:
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="core.sha256"))
    elif artifact_sha is not None and core_sha != artifact_sha:
        blockers.append(
            reason(
                "wrong_target_scope",
                path=str(manifest_path),
                field="core.sha256",
                recorded=core_sha,
                expected=artifact_sha,
                detail="does_not_match_artifact_identity",
            )
        )
    core_path_raw = core.get("path") if isinstance(core, dict) else None
    if not isinstance(core_path_raw, str) or not core_path_raw:
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="core.path"))
    else:
        core_path = manifest_relative_path(Path(core_path_raw), manifest_path)
        try:
            reject_symlink_component(core_path, f"{manifest_path}: core.path")
            reject_protected_input_path(core_path, f"{manifest_path}: core.path")
        except SystemExit as exc:
            blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="core.path", detail=str(exc)))
    return blockers


def core_evidence_pack_blockers(manifest_path: Path, manifest: dict[str, Any]) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    inputs = manifest.get("inputs")
    evidence_pack_raw = inputs.get("evidence_pack_manifest") if isinstance(inputs, dict) else None
    if not isinstance(evidence_pack_raw, str) or not evidence_pack_raw:
        return [
            reason(
                "missing_core_evidence_pack",
                path=str(manifest_path),
                field="inputs.evidence_pack_manifest",
                required_schema=CORE_DUMP_EVIDENCE_PACK_SCHEMA,
            )
        ]

    evidence_pack_path = manifest_relative_path(Path(evidence_pack_raw), manifest_path)
    try:
        reject_symlink_component(evidence_pack_path, f"{manifest_path}: inputs.evidence_pack_manifest")
        evidence_pack_path = reject_protected_input_path(
            evidence_pack_path,
            f"{manifest_path}: inputs.evidence_pack_manifest",
        )
    except SystemExit as exc:
        return [
            reason(
                "missing_core_evidence_pack",
                path=str(manifest_path),
                field="inputs.evidence_pack_manifest",
                detail=str(exc),
                required_schema=CORE_DUMP_EVIDENCE_PACK_SCHEMA,
            )
        ]

    evidence_pack, error = load_json(evidence_pack_path)
    if evidence_pack is None:
        return [
            reason(
                "missing_core_evidence_pack",
                path=str(evidence_pack_path),
                detail=error,
                required_schema=CORE_DUMP_EVIDENCE_PACK_SCHEMA,
            )
        ]
    if evidence_pack.get("schema") != CORE_DUMP_EVIDENCE_PACK_SCHEMA:
        blockers.append(
            reason(
                "missing_core_evidence_pack",
                path=str(evidence_pack_path),
                field="schema",
                recorded=evidence_pack.get("schema"),
                required_schema=CORE_DUMP_EVIDENCE_PACK_SCHEMA,
            )
        )

    pack_binary = manifest.get("binary")
    pack_binary_sha = pack_binary.get("sha256") if isinstance(pack_binary, dict) else None
    evidence_binary = evidence_pack.get("binary")
    evidence_binary_sha = evidence_binary.get("sha256") if isinstance(evidence_binary, dict) else None
    if not isinstance(evidence_binary_sha, str) or SHA256_RE.fullmatch(evidence_binary_sha) is None:
        blockers.append(reason("missing_core_evidence_pack", path=str(evidence_pack_path), field="binary.sha256"))
    elif isinstance(pack_binary_sha, str) and evidence_binary_sha != pack_binary_sha:
        blockers.append(
            reason(
                "missing_core_evidence_pack",
                path=str(evidence_pack_path),
                field="binary.sha256",
                recorded=evidence_binary_sha,
                expected=pack_binary_sha,
            )
        )

    evidence_status = evidence_pack.get("evidence_status")
    status = evidence_status.get("status") if isinstance(evidence_status, dict) else None
    gdb_core_failed = evidence_status.get("gdb_core_failed") if isinstance(evidence_status, dict) else None
    if status != "complete":
        blockers.append(
            reason("missing_core_evidence_pack", path=str(evidence_pack_path), field="evidence_status.status", recorded=status)
        )
    if gdb_core_failed is not False:
        blockers.append(
            reason(
                "missing_core_evidence_pack",
                path=str(evidence_pack_path),
                field="evidence_status.gdb_core_failed",
                recorded=gdb_core_failed,
            )
        )

    pack_core = manifest.get("core")
    pack_core_sha = pack_core.get("sha256") if isinstance(pack_core, dict) else None
    evidence_core = evidence_pack.get("core")
    evidence_core_sha = evidence_core.get("sha256") if isinstance(evidence_core, dict) else None
    if not isinstance(evidence_core, dict):
        blockers.append(reason("missing_core_evidence_pack", path=str(evidence_pack_path), field="core"))
        return blockers
    if not isinstance(evidence_core_sha, str) or SHA256_RE.fullmatch(evidence_core_sha) is None:
        blockers.append(reason("missing_core_evidence_pack", path=str(evidence_pack_path), field="core.sha256"))
    elif isinstance(pack_core_sha, str) and evidence_core_sha != pack_core_sha:
        blockers.append(
            reason(
                "missing_core_evidence_pack",
                path=str(evidence_pack_path),
                field="core.sha256",
                recorded=evidence_core_sha,
                expected=pack_core_sha,
            )
        )
    evidence_core_path_raw = evidence_core.get("path")
    if not isinstance(evidence_core_path_raw, str) or not evidence_core_path_raw:
        blockers.append(reason("missing_core_evidence_pack", path=str(evidence_pack_path), field="core.path"))
    else:
        evidence_core_path = manifest_relative_path(Path(evidence_core_path_raw), evidence_pack_path)
        try:
            reject_symlink_component(evidence_core_path, f"{evidence_pack_path}: core.path")
            reject_protected_input_path(evidence_core_path, f"{evidence_pack_path}: core.path")
        except SystemExit as exc:
            blockers.append(
                reason(
                    "missing_core_evidence_pack",
                    path=str(evidence_pack_path),
                    field="core.path",
                    detail=str(exc),
                )
            )
    return blockers


def evaluate_pack(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, object]:
    pack_reasons = manifest_scope_blockers(manifest_path, manifest)
    pack_reasons.extend(core_evidence_pack_blockers(manifest_path, manifest))
    inventory_path = inventory_path_from_manifest(manifest_path, manifest)
    targets: set[str] = set()
    if inventory_path is None:
        pack_reasons.append(reason("missing_ufunction_inventory", path=str(manifest_path), detail="invalid_artifacts.ufunction_inventory"))
    else:
        targets, inventory_reasons, inventory = load_inventory_targets(inventory_path)
        pack_reasons.extend(inventory_reasons)
        pack_reasons.extend(
            player_identity_target_set_scope_blockers(manifest_path, manifest, inventory_path, inventory)
        )
    missing = sorted(target for target in PLAYER_IDENTITY_TARGETS if target not in targets)
    if missing:
        pack_reasons.append(
            reason(
                "missing_target",
                path=str(manifest_path),
                targets=missing,
                required_target_count=len(PLAYER_IDENTITY_TARGETS),
                missing_count=len(missing),
            )
        )
    return {
        "manifest": str(manifest_path),
        "schema": manifest.get("schema"),
        "status": manifest.get("status"),
        "promotion_status": manifest.get("promotion_status"),
        "inputs": manifest.get("inputs") if isinstance(manifest.get("inputs"), dict) else {},
        "target_set_coverage": inventory.get("target_set_coverage") if isinstance(inventory, dict) else {},
        "summary": manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {},
        "blockers": manifest.get("blockers") if isinstance(manifest.get("blockers"), list) else [],
        "inventory": str(inventory_path) if inventory_path is not None else None,
        "ready": not pack_reasons,
        "reasons": pack_reasons,
        "matched_targets": sorted(target for target in PLAYER_IDENTITY_TARGETS if target in targets),
        "required_target_set": player_identity_target_set_expectation_fields(),
    }


def build_report(root: Path, max_depth: int) -> dict[str, object]:
    try:
        manifest_paths = candidate_manifest_paths(root, max_depth)
    except SystemExit as exc:
        return {
            "schema": REPORT_SCHEMA,
            "status": "blocked",
            "ready": False,
            "root": str(root),
            "manifests_scanned": 0,
            "candidate_packs": [],
            "accepted_pack": None,
            "reasons": [reason("wrong_target_scope", path=str(root), detail=str(exc))],
            "required_targets": list(REQUIRED_TARGETS),
            "required_target_set": player_identity_target_set_expectation_fields(),
            "accepted_for_candidate_planning": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "next_step": "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack",
            "operator_next_step": operator_next_step(None),
            "non_claims": non_claims(),
        }

    artifact_pack_container_paths: list[str] = []
    scriptstruct_pack_paths: list[str] = []
    reflection_inventory_comparison_paths: list[str] = []
    schema_mismatch_paths: list[str] = []
    candidate_packs: list[dict[str, object]] = []
    for manifest_path in manifest_paths:
        payload, error = load_json(manifest_path)
        if payload is None:
            continue
        if manifest_path.name == ARTIFACT_PACK_MANIFEST_FILENAME:
            artifact_pack_container_paths.append(str(manifest_path))
            continue
        if payload.get("schema") == SCRIPTSTRUCT_PACK_SCHEMA:
            scriptstruct_pack_paths.append(str(manifest_path))
            continue
        if payload.get("schema") == REFLECTION_INVENTORY_COMPARISON_SCHEMA:
            reflection_inventory_comparison_paths.append(str(manifest_path))
            continue
        if payload.get("schema") != PACK_SCHEMA:
            schema_mismatch_paths.append(str(manifest_path))
            continue
        candidate_packs.append(evaluate_pack(manifest_path, payload))

    non_candidate_reasons: list[dict[str, object]] = []
    if artifact_pack_container_paths:
        non_candidate_reasons.append(
            reason(
                "artifact_pack_container_not_reflection_inventory",
                **bounded_list_fields("scanned_paths", artifact_pack_container_paths),
            )
        )
    if scriptstruct_pack_paths:
        non_candidate_reasons.append(
            reason(
                "scriptstruct_pack_not_reflection_inventory",
                **bounded_list_fields("scanned_paths", scriptstruct_pack_paths),
            )
        )
    if reflection_inventory_comparison_paths:
        non_candidate_reasons.append(
            reason(
                "reflection_inventory_comparison_not_reflection_inventory_pack",
                **bounded_list_fields("scanned_paths", reflection_inventory_comparison_paths),
            )
        )
    if schema_mismatch_paths:
        non_candidate_reasons.append(
            reason("schema_mismatch", **bounded_list_fields("scanned_paths", schema_mismatch_paths))
        )

    accepted = next((pack for pack in candidate_packs if pack["ready"]), None)
    if accepted:
        reasons: list[dict[str, object]] = []
    elif candidate_packs:
        reasons = list(non_candidate_reasons)
        for pack in candidate_packs:
            reasons.extend(pack["reasons"])  # type: ignore[arg-type]
    elif manifest_paths:
        reasons = [reason("missing_reflection_inventory_pack", root=str(root)), *non_candidate_reasons]
    else:
        reasons = [reason("missing_reflection_inventory_pack", root=str(root))]

    return {
        "schema": REPORT_SCHEMA,
        "status": "ready" if accepted else "blocked",
        "ready": accepted is not None,
        "accepted_for_candidate_planning": accepted is not None,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "root": str(root),
        "manifests_scanned": len(manifest_paths),
        "candidate_packs": candidate_packs,
        "accepted_pack": accepted,
        "reasons": reasons,
        "required_targets": list(REQUIRED_TARGETS),
        "required_target_set": player_identity_target_set_expectation_fields(),
        "next_step": (
            "plan_candidate_only_server_list_players_and_server_kick_player_snapshots"
            if accepted
            else "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack"
        ),
        "operator_next_step": operator_next_step(accepted),
        "non_claims": non_claims(),
    }


def operator_next_step(accepted: dict[str, object] | None) -> dict[str, object]:
    if accepted is None:
        return {
            "status": "blocked_before_planning",
            "scope": "offline_candidate_only",
            "server_access_required": False,
            "next_step": "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack",
            "summary": (
                "No accepted reflection inventory pack is available; focal snapshot planning remains blocked "
                "until a reviewed non-protected candidate-only inventory pack is accepted."
            ),
        }
    return {
        "status": "accepted_for_candidate_only_planning",
        "scope": "offline_candidate_only",
        "server_access_required": False,
        "next_step": "plan_candidate_only_server_list_players_and_server_kick_player_snapshots",
        "summary": (
            "Accepted reflection inventory only enables candidate-only focal snapshot planning; it does not "
            "promote player identity, Inventory SDK, public SDK, runtime identity, lookup, or ResourceHandle."
        ),
    }


def non_claims() -> list[str]:
    return [
        "Read-only preflight; does not read a core, execute snapshot commands, write files, or touch servers.",
        "An offline ShooterGameServer binary alone is insufficient; player-identity planning requires a non-protected complete core evidence pack and a reviewed UFunction reflection-inventory pack.",
        "Accepted reflection inventory means candidate-only snapshot planning, not player identity, Inventory SDK, public SDK, runtime identity, lookup, GObjects, UObject identity, or ResourceHandle promotion.",
        "Does not promote player identity, command routing, permissions, mutation, return override, public SDK scope, GObjects, UObject identity, or ResourceHandle.",
    ]


def main() -> int:
    args = parse_args()
    report = build_report(args.root, args.max_depth)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
