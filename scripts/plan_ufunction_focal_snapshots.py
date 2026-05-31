#!/usr/bin/env python3
"""Plan candidate-only focal UFunction snapshot commands from an inventory pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import ufunction_focal_snapshot_plan as focal_planner  # noqa: E402
from reflection_target_sets import TARGET_SETS  # noqa: E402
from snapshot_evidence_pack import (  # noqa: E402
    SHA256_RE,
    manifest_relative_path,
    reject_protected_input_path,
    reject_protected_output_path,
    reject_symlink_component,
    require_ignored_output_path,
    safe_component,
)


PACK_SCHEMA = "obelisk.reflection-inventory-pack.v1"
REDACTED_FUNCTION_KEYS = {
    "family",
    "function_flags",
    "name",
    "num_parms",
    "outer_class_name",
    "outer_name",
    "parms_size",
}
DEFAULT_MAX_OBJECT_SCAN = 30000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan candidate-only inspect_core_ufunctions.py --snapshot-json commands from "
            "an already reviewed reflection inventory pack."
        )
    )
    parser.add_argument("--inventory-pack", required=True, type=Path, help="Pack directory or manifest.json path.")
    parser.add_argument("--target", action="append", default=[], metavar="Outer.Name")
    parser.add_argument("--target-set", action="append", default=[], help="Named reflection target set to expand.")
    parser.add_argument("--target-file", action="append", type=Path, default=[], help="Newline target list.")
    parser.add_argument(
        "--evidence-obelisk-commit",
        required=True,
        help="Reviewed Obelisk commit/id to embed in emitted snapshot commands.",
    )
    parser.add_argument("--json-out", type=Path, help="Optional output JSON path. Defaults to stdout.")
    return parser.parse_args()


def parse_int_field(value: object, label: str) -> int:
    if not isinstance(value, str) or not value:
        raise SystemExit(f"{label} must be a non-empty integer string")
    try:
        return int(value, 0)
    except ValueError as exc:
        raise SystemExit(f"{label} must be parseable as an integer: {value}") from exc


def load_json(path: Path, label: str) -> dict[str, object]:
    reject_symlink_component(path, label)
    resolved = reject_protected_input_path(path, label)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} does not exist: {path}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object: {path}")
    return payload


def pack_manifest_path(pack: Path) -> Path:
    reject_symlink_component(pack, "--inventory-pack")
    resolved = reject_protected_input_path(pack, "--inventory-pack")
    if resolved.is_dir():
        return resolved / "manifest.json"
    return resolved


def pack_artifact_path(manifest_path: Path, artifact_name: str) -> Path:
    path = manifest_path.parent / artifact_name
    reject_symlink_component(path, artifact_name)
    return reject_protected_input_path(path, artifact_name)


def inventory_path_from_manifest(manifest_path: Path, manifest: dict[str, object]) -> Path:
    artifacts = manifest.get("artifacts")
    name = artifacts.get("ufunction_inventory") if isinstance(artifacts, dict) else None
    if name is None:
        name = "ufunction-inventory.json"
    if not isinstance(name, str) or not name:
        raise SystemExit(f"{manifest_path}: artifacts.ufunction_inventory must be a non-empty string")
    if Path(name).name != name:
        raise SystemExit(f"{manifest_path}: artifacts.ufunction_inventory must be manifest-local: {name}")
    return pack_artifact_path(manifest_path, name)


def require_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise SystemExit(f"{label} must be a lowercase 64-character SHA256")
    return value


def require_safe_identity(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SystemExit(f"{label} must be a non-empty string")
    return safe_component(value, label)


def validate_manifest(manifest_path: Path, manifest: dict[str, object]) -> dict[str, object]:
    if manifest.get("schema") != PACK_SCHEMA:
        raise SystemExit(f"{manifest_path}: schema must be {PACK_SCHEMA}")
    if manifest.get("status") != "candidate-only":
        raise SystemExit(f"{manifest_path}: status must be candidate-only")
    if manifest.get("promotion_status") != "not_promoted_candidate_only":
        raise SystemExit(f"{manifest_path}: promotion_status must be not_promoted_candidate_only")

    identity = manifest.get("artifact_identity")
    if not isinstance(identity, dict):
        raise SystemExit(f"{manifest_path}: missing artifact_identity")
    artifact_kind = identity.get("artifact_kind")
    if artifact_kind != "offline_core":
        raise SystemExit(f"{manifest_path}: artifact_identity.artifact_kind must be offline_core")
    artifact_sha = require_sha(identity.get("artifact_sha256"), f"{manifest_path}: artifact_identity.artifact_sha256")
    capture_id = require_safe_identity(identity.get("capture_id"), f"{manifest_path}: artifact_identity.capture_id")
    evidence_pack_id = require_safe_identity(
        identity.get("evidence_pack_id"),
        f"{manifest_path}: artifact_identity.evidence_pack_id",
    )

    binary = manifest.get("binary")
    binary_sha = require_sha(
        binary.get("sha256") if isinstance(binary, dict) else None,
        f"{manifest_path}: binary.sha256",
    )
    core = manifest.get("core")
    if not isinstance(core, dict):
        raise SystemExit(f"{manifest_path}: missing core")
    core_sha = require_sha(core.get("sha256"), f"{manifest_path}: core.sha256")
    if core_sha != artifact_sha:
        raise SystemExit(f"{manifest_path}: core.sha256 must match artifact_identity.artifact_sha256")
    core_path_raw = core.get("path")
    if not isinstance(core_path_raw, str) or not core_path_raw:
        raise SystemExit(f"{manifest_path}: core.path must be a non-empty string")
    core_path = manifest_relative_path(Path(core_path_raw), manifest_path)
    reject_symlink_component(core_path, f"{manifest_path}: core.path")
    core_path = reject_protected_input_path(core_path, f"{manifest_path}: core.path")

    addresses = manifest.get("addresses")
    if not isinstance(addresses, dict):
        raise SystemExit(f"{manifest_path}: missing addresses")
    gobjects = parse_int_field(addresses.get("gobjects"), f"{manifest_path}: addresses.gobjects")
    fname_root_slot = parse_int_field(
        addresses.get("fname_root_slot"),
        f"{manifest_path}: addresses.fname_root_slot",
    )

    summary = manifest.get("summary")
    if not isinstance(summary, dict):
        raise SystemExit(f"{manifest_path}: missing summary")
    if summary.get("fname_root_ready") is not True:
        raise SystemExit(f"{manifest_path}: summary.fname_root_ready must be true")
    blockers = manifest.get("blockers")
    if not isinstance(blockers, list):
        raise SystemExit(f"{manifest_path}: blockers must be a list")
    if blockers:
        raise SystemExit(f"{manifest_path}: blockers must be empty before focal snapshot planning")

    inputs = manifest.get("inputs")
    max_object_scan = DEFAULT_MAX_OBJECT_SCAN
    if isinstance(inputs, dict) and inputs.get("max_objects") is not None:
        raw_max_objects = inputs.get("max_objects")
        if not isinstance(raw_max_objects, int) or raw_max_objects < 0:
            raise SystemExit(f"{manifest_path}: inputs.max_objects must be a non-negative integer")
        max_object_scan = raw_max_objects

    return {
        "core": core_path,
        "gobjects": gobjects,
        "fname_root_slot": fname_root_slot,
        "binary_sha": binary_sha,
        "core_sha": core_sha,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
        "max_object_scan": max_object_scan,
    }


def load_functions(inventory_path: Path) -> list[dict[str, object]]:
    payload = load_json(inventory_path, "ufunction inventory")
    rows = payload.get("functions")
    if not isinstance(rows, list):
        raise SystemExit(f"{inventory_path}: functions must be a list")
    functions: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SystemExit(f"{inventory_path}: functions[{index}] must be an object")
        extra_keys = sorted(set(row) - REDACTED_FUNCTION_KEYS)
        missing_keys = sorted(REDACTED_FUNCTION_KEYS - set(row))
        if extra_keys:
            raise SystemExit(f"{inventory_path}: functions[{index}] has non-redacted extra keys: {extra_keys}")
        if missing_keys:
            raise SystemExit(f"{inventory_path}: functions[{index}] missing redacted keys: {missing_keys}")
        outer = row.get("outer_name")
        name = row.get("name")
        if not isinstance(outer, str) or not outer or not isinstance(name, str) or not name:
            raise SystemExit(f"{inventory_path}: functions[{index}] missing Outer.Name identity")
        functions.append(row)
    return functions


def load_targets(args: argparse.Namespace) -> tuple[list[str], dict[str, object]]:
    targets = list(args.target)
    target_sets: list[str] = []
    for target_set in args.target_set:
        if target_set not in TARGET_SETS:
            raise SystemExit(f"unknown --target-set: {target_set}")
        target_sets.append(target_set)
        targets.extend(TARGET_SETS[target_set])
    target_files: list[str] = []
    for path in args.target_file:
        reject_symlink_component(path, "--target-file")
        resolved = reject_protected_input_path(path, "--target-file")
        target_files.append(str(resolved))
        for line in resolved.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            targets.append(stripped)
    if not targets:
        raise SystemExit("at least one --target or --target-file entry is required")
    return targets, {
        "cli_target_count": len(args.target),
        "target_sets": target_sets,
        "target_files": target_files,
        "loaded_target_count": len(targets),
    }


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    manifest_path = pack_manifest_path(args.inventory_pack)
    manifest = load_json(manifest_path, "inventory pack manifest")
    inventory_path = inventory_path_from_manifest(manifest_path, manifest)
    pack_defaults = validate_manifest(manifest_path, manifest)
    functions = load_functions(inventory_path)
    targets, target_source = load_targets(args)

    payload = focal_planner.focal_snapshot_plan(
        functions,
        requested_targets=targets,
        core=pack_defaults["core"],
        gobjects=pack_defaults["gobjects"],
        fname_root_slot=pack_defaults["fname_root_slot"],
        binary_sha=pack_defaults["binary_sha"],
        core_sha=pack_defaults["core_sha"],
        capture_id=pack_defaults["capture_id"],
        evidence_pack_id=pack_defaults["evidence_pack_id"],
        max_object_scan=pack_defaults["max_object_scan"],
        fname_root_ready=True,
        fname_root_blockers=[],
        artifact_identity_source="reflection-inventory-pack",
        obelisk_commit=args.evidence_obelisk_commit,
        repo_root=SCRIPT_DIR.parent,
    )
    payload["inventory_source"] = "accepted_redacted_inventory_pack"
    payload["inventory_pack"] = {
        "manifest": str(manifest_path),
        "ufunction_inventory": str(inventory_path),
    }
    payload["target_source"] = target_source
    payload["non_claims"] = [
        "Does not reread a core, extract snapshots, execute planned commands, or touch servers.",
        "Does not add target sets, fixtures, runtime hooks, mutation, return override, or public SDK scope.",
        "Does not promote GObjects, UObject identity, raw params, or ResourceHandle lifetime.",
    ]
    return payload


def write_payload(path: Path, payload: dict[str, object]) -> None:
    reject_symlink_component(path, "--json-out")
    output = reject_protected_output_path(path, "--json-out")
    require_ignored_output_path(output, "--json-out")
    if output.exists() and output.is_symlink():
        raise SystemExit(f"--json-out must not be a symlink: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = build_plan(args)
    if args.json_out:
        write_payload(args.json_out, payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
