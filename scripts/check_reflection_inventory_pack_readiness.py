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
from snapshot_evidence_pack import (  # noqa: E402
    SHA256_RE,
    manifest_relative_path,
    reject_protected_input_path,
    reject_symlink_component,
)


REPORT_SCHEMA = "obelisk.reflection-inventory-pack-readiness-check.v1"
PACK_SCHEMA = "obelisk.reflection-inventory-pack.v1"
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
MANIFEST_FILENAMES = {"manifest.json", "artifact-pack.manifest.json"}


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
    return parser.parse_args()


def reason(code: str, **fields: object) -> dict[str, object]:
    return {"reason": code, **fields}


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


def load_inventory_targets(path: Path) -> tuple[set[str], list[dict[str, object]]]:
    blockers: list[dict[str, object]] = []
    try:
        reject_symlink_component(path, "ufunction inventory")
        resolved = reject_protected_input_path(path, "ufunction inventory")
    except SystemExit as exc:
        return set(), [reason("missing_ufunction_inventory", path=str(path), detail=str(exc))]
    payload, error = load_json(resolved)
    if payload is None:
        return set(), [reason("missing_ufunction_inventory", path=str(path), detail=error)]
    rows = payload.get("functions")
    if not isinstance(rows, list):
        return set(), [reason("missing_ufunction_inventory", path=str(path), detail="functions_not_list")]

    targets: set[str] = set()
    seen: set[str] = set()
    duplicates: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blockers.append(reason("missing_ufunction_inventory", path=str(path), detail=f"functions[{index}]_not_object"))
            continue
        extra = sorted(set(row) - REDACTED_FUNCTION_KEYS)
        missing = sorted(REDACTED_FUNCTION_KEYS - set(row))
        if extra or missing:
            blockers.append(
                reason(
                    "missing_ufunction_inventory",
                    path=str(path),
                    detail=f"functions[{index}]_redaction_schema_mismatch",
                    extra_keys=extra,
                    missing_keys=missing,
                )
            )
            continue
        target = target_from_row(row)
        if target is None:
            blockers.append(reason("missing_ufunction_inventory", path=str(path), detail=f"functions[{index}]_missing_target_identity"))
            continue
        if target in seen:
            duplicates.add(target)
        seen.add(target)
        targets.add(target)
    if duplicates:
        blockers.append(reason("wrong_target_scope", path=str(path), duplicate_targets=sorted(duplicates)))
    return targets, blockers


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
    if not isinstance(identity, dict) or identity.get("artifact_kind") != "offline_core":
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="artifact_identity.artifact_kind"))
    elif not isinstance(identity.get("artifact_sha256"), str) or SHA256_RE.fullmatch(str(identity.get("artifact_sha256"))) is None:
        blockers.append(reason("wrong_target_scope", path=str(manifest_path), field="artifact_identity.artifact_sha256"))
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


def evaluate_pack(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, object]:
    pack_reasons = manifest_scope_blockers(manifest_path, manifest)
    inventory_path = inventory_path_from_manifest(manifest_path, manifest)
    targets: set[str] = set()
    if inventory_path is None:
        pack_reasons.append(reason("missing_ufunction_inventory", path=str(manifest_path), detail="invalid_artifacts.ufunction_inventory"))
    else:
        targets, inventory_reasons = load_inventory_targets(inventory_path)
        pack_reasons.extend(inventory_reasons)
    missing = sorted(target for target in REQUIRED_TARGETS if target not in targets)
    if missing:
        pack_reasons.append(reason("missing_target", path=str(manifest_path), targets=missing))
    return {
        "manifest": str(manifest_path),
        "inventory": str(inventory_path) if inventory_path is not None else None,
        "ready": not pack_reasons,
        "reasons": pack_reasons,
        "matched_targets": sorted(target for target in REQUIRED_TARGETS if target in targets),
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
            "non_claims": non_claims(),
        }

    schema_mismatch_paths: list[str] = []
    candidate_packs: list[dict[str, object]] = []
    for manifest_path in manifest_paths:
        payload, error = load_json(manifest_path)
        if payload is None:
            continue
        if payload.get("schema") != PACK_SCHEMA:
            schema_mismatch_paths.append(str(manifest_path))
            continue
        candidate_packs.append(evaluate_pack(manifest_path, payload))

    accepted = next((pack for pack in candidate_packs if pack["ready"]), None)
    if accepted:
        reasons: list[dict[str, object]] = []
    elif candidate_packs:
        reasons = []
        for pack in candidate_packs:
            reasons.extend(pack["reasons"])  # type: ignore[arg-type]
    elif manifest_paths:
        reasons = [
            reason("missing_reflection_inventory_pack", root=str(root)),
            reason("schema_mismatch", scanned_paths=schema_mismatch_paths),
        ]
    else:
        reasons = [reason("missing_reflection_inventory_pack", root=str(root))]

    return {
        "schema": REPORT_SCHEMA,
        "status": "ready" if accepted else "blocked",
        "ready": accepted is not None,
        "root": str(root),
        "manifests_scanned": len(manifest_paths),
        "candidate_packs": candidate_packs,
        "accepted_pack": accepted,
        "reasons": reasons,
        "required_targets": list(REQUIRED_TARGETS),
        "non_claims": non_claims(),
    }


def non_claims() -> list[str]:
    return [
        "Read-only preflight; does not read a core, execute snapshot commands, write files, or touch servers.",
        "Does not promote player identity, command routing, permissions, mutation, return override, public SDK scope, GObjects, UObject identity, or ResourceHandle.",
    ]


def main() -> int:
    args = parse_args()
    report = build_report(args.root, args.max_depth)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
