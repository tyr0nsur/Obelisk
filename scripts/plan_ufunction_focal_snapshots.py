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
from artifact_identity import is_safe_artifact_id  # noqa: E402
from reflection_target_sets import TARGET_SETS, schema_target_list  # noqa: E402
from snapshot_evidence_pack import (  # noqa: E402
    CORE_DUMP_EVIDENCE_PACK_SCHEMA,
    SHA256_RE,
    manifest_relative_path,
    reject_protected_input_path,
    reject_protected_output_path,
    reject_symlink_component,
    require_ignored_output_path,
    safe_component,
)


PACK_SCHEMA = "obelisk.reflection-inventory-pack.v1"
PLAYER_IDENTITY_TARGET_SET = "players-identity-lifecycle-intake"
PLAYER_IDENTITY_TARGETS = tuple(
    schema_target_list(PLAYER_IDENTITY_TARGET_SET, "obelisk.ufunction-chain.snapshot.v1")
)
DIRECT_PLAYER_IDENTITY_GATE_TARGETS = frozenset(
    (
        "ShooterPlayerController.ServerListPlayers",
        "ShooterPlayerController.ServerKickPlayer",
    )
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
    if not is_safe_artifact_id(value):
        raise SystemExit(f"{label} must be a safe artifact identity id")
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


def load_functions(inventory_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
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
    return functions, payload


def require_player_identity_target_set_scope(
    manifest_path: Path,
    manifest: dict[str, object],
    inventory_path: Path,
    inventory: dict[str, object],
    requested_target_sets: list[str],
    requested_targets: list[str],
) -> None:
    requested_player_identity_targets = player_identity_target_set_targets_from_requests(requested_targets)
    if PLAYER_IDENTITY_TARGET_SET not in requested_target_sets and not requested_player_identity_targets:
        return
    broad_player_identity_targets = sorted(requested_player_identity_targets - DIRECT_PLAYER_IDENTITY_GATE_TARGETS)
    if PLAYER_IDENTITY_TARGET_SET in requested_target_sets or broad_player_identity_targets:
        raise SystemExit(
            f"refusing to plan broad {PLAYER_IDENTITY_TARGET_SET} focal snapshots by default; "
            "first player identity planning must "
            "target only ShooterPlayerController.ServerListPlayers and "
            "ShooterPlayerController.ServerKickPlayer after a complete reflection inventory pack. "
            f"(full_target_count={len(PLAYER_IDENTITY_TARGETS)} "
            f"unexpected_targets={','.join(broad_player_identity_targets)})"
        )
    requested_short_targets = short_targets_from_requests(requested_targets)
    unexpected_mixed_targets = sorted(requested_short_targets - DIRECT_PLAYER_IDENTITY_GATE_TARGETS)
    if requested_player_identity_targets and unexpected_mixed_targets:
        raise SystemExit(
            "player identity focal planning must request only "
            "ShooterPlayerController.ServerListPlayers and "
            "ShooterPlayerController.ServerKickPlayer "
            f"(unexpected_targets={','.join(unexpected_mixed_targets)})"
        )

    require_player_identity_core_evidence_pack(manifest_path, manifest)

    inputs = manifest.get("inputs")
    manifest_target_sets = inputs.get("target_sets") if isinstance(inputs, dict) else None
    if not isinstance(manifest_target_sets, list) or PLAYER_IDENTITY_TARGET_SET not in manifest_target_sets:
        raise SystemExit(
            f"{manifest_path}: inputs.target_sets must include {PLAYER_IDENTITY_TARGET_SET} "
            "before planning player identity snapshots"
        )
    if not all(isinstance(item, str) and item for item in manifest_target_sets):
        raise SystemExit(f"{manifest_path}: inputs.target_sets must be a list of non-empty strings")

    coverage = inventory.get("target_set_coverage")
    if not isinstance(coverage, dict):
        raise SystemExit(
            f"{inventory_path}: target_set_coverage for {PLAYER_IDENTITY_TARGET_SET} is required "
            "before planning player identity snapshots"
        )
    coverage_target_sets = coverage.get("target_sets")
    if not isinstance(coverage_target_sets, list) or PLAYER_IDENTITY_TARGET_SET not in coverage_target_sets:
        raise SystemExit(
            f"{inventory_path}: target_set_coverage.target_sets must include {PLAYER_IDENTITY_TARGET_SET} "
            "before planning player identity snapshots"
        )
    if not all(isinstance(item, str) and item for item in coverage_target_sets):
        raise SystemExit(f"{inventory_path}: target_set_coverage.target_sets must be a list of non-empty strings")
    if sorted(manifest_target_sets) != sorted(coverage_target_sets):
        raise SystemExit(
            f"{inventory_path}: target_set_coverage.target_sets must exactly match "
            f"{manifest_path}: inputs.target_sets before planning player identity snapshots "
            f"(manifest_target_sets={','.join(manifest_target_sets)} "
            f"coverage_target_sets={','.join(coverage_target_sets)})"
        )
    requested_targets = coverage.get("requested_targets")
    if not isinstance(requested_targets, list):
        missing_targets = list(PLAYER_IDENTITY_TARGETS)
        requested_target_count = 0
    else:
        missing_targets = [target for target in PLAYER_IDENTITY_TARGETS if target not in requested_targets]
        requested_target_count = len(requested_targets)
    if missing_targets:
        raise SystemExit(
            f"{inventory_path}: target_set_coverage.requested_targets must include the complete "
            f"{PLAYER_IDENTITY_TARGET_SET} target list before planning player identity snapshots "
            f"(expected_target_count={len(PLAYER_IDENTITY_TARGETS)} "
            f"requested_target_count={requested_target_count} "
            f"missing_count={len(missing_targets)} "
            f"missing_targets={','.join(missing_targets)} "
            f"expected_targets={','.join(PLAYER_IDENTITY_TARGETS)})"
        )
    matched_targets = coverage.get("matched_targets")
    if not isinstance(matched_targets, dict):
        raise SystemExit(
            f"{inventory_path}: target_set_coverage.matched_targets must record exact rows for "
            "the complete player identity target set before planning player identity snapshots"
        )
    missing_count = coverage.get("missing_count")
    ambiguous_count = coverage.get("ambiguous_count")
    matched_count = coverage.get("matched_count")
    if missing_count != 0 or ambiguous_count != 0 or matched_count != len(PLAYER_IDENTITY_TARGETS):
        raise SystemExit(
            f"{inventory_path}: target_set_coverage must have full matched player identity coverage "
            f"before planning player identity snapshots (expected_matched_count={len(PLAYER_IDENTITY_TARGETS)} "
            f"matched_count={matched_count} missing_count={missing_count} ambiguous_count={ambiguous_count})"
        )
    admin_targets_without_rows = [
        target
        for target in sorted(DIRECT_PLAYER_IDENTITY_GATE_TARGETS)
        if not isinstance(matched_targets.get(target), dict)
    ]
    if admin_targets_without_rows:
        raise SystemExit(
            f"{inventory_path}: target_set_coverage.matched_targets must include exact admin rows before "
            "planning player identity snapshots "
            f"(missing_admin_targets={','.join(admin_targets_without_rows)})"
        )


def player_identity_target_set_targets_from_requests(requested_targets: list[str]) -> set[str]:
    return short_targets_from_requests(requested_targets) & set(PLAYER_IDENTITY_TARGETS)


def short_targets_from_requests(requested_targets: list[str]) -> set[str]:
    matched: set[str] = set()
    for target in requested_targets:
        _, outer, name = focal_planner.parse_exact_target(target)
        short_target = f"{outer}.{name}"
        matched.add(short_target)
    return matched


def require_player_identity_core_evidence_pack(manifest_path: Path, manifest: dict[str, object]) -> None:
    inputs = manifest.get("inputs")
    evidence_pack_raw = inputs.get("evidence_pack_manifest") if isinstance(inputs, dict) else None
    if not isinstance(evidence_pack_raw, str) or not evidence_pack_raw:
        raise SystemExit(
            f"{manifest_path}: inputs.evidence_pack_manifest must reference a complete "
            f"{CORE_DUMP_EVIDENCE_PACK_SCHEMA} before planning player identity snapshots"
        )

    evidence_pack_path = manifest_relative_path(Path(evidence_pack_raw), manifest_path)
    reject_symlink_component(evidence_pack_path, f"{manifest_path}: inputs.evidence_pack_manifest")
    evidence_pack_path = reject_protected_input_path(
        evidence_pack_path,
        f"{manifest_path}: inputs.evidence_pack_manifest",
    )
    evidence_pack = load_json(evidence_pack_path, "core evidence pack manifest")
    if evidence_pack.get("schema") != CORE_DUMP_EVIDENCE_PACK_SCHEMA:
        raise SystemExit(
            f"{evidence_pack_path}: schema must be {CORE_DUMP_EVIDENCE_PACK_SCHEMA} "
            "before planning player identity snapshots"
        )

    pack_binary = manifest.get("binary")
    pack_binary_sha = pack_binary.get("sha256") if isinstance(pack_binary, dict) else None
    evidence_binary = evidence_pack.get("binary")
    evidence_binary_sha = evidence_binary.get("sha256") if isinstance(evidence_binary, dict) else None
    if not isinstance(evidence_binary_sha, str) or SHA256_RE.fullmatch(evidence_binary_sha) is None:
        raise SystemExit(f"{evidence_pack_path}: binary.sha256 must be a lowercase 64-character SHA256")
    if isinstance(pack_binary_sha, str) and evidence_binary_sha != pack_binary_sha:
        raise SystemExit(
            f"{evidence_pack_path}: binary.sha256 must match {manifest_path}: binary.sha256 "
            "before planning player identity snapshots"
        )

    evidence_status = evidence_pack.get("evidence_status")
    status = evidence_status.get("status") if isinstance(evidence_status, dict) else None
    gdb_core_failed = evidence_status.get("gdb_core_failed") if isinstance(evidence_status, dict) else None
    if status != "complete":
        raise SystemExit(f"{evidence_pack_path}: evidence_status.status must be complete")
    if gdb_core_failed is not False:
        raise SystemExit(f"{evidence_pack_path}: evidence_status.gdb_core_failed must be false")

    pack_core = manifest.get("core")
    pack_core_sha = pack_core.get("sha256") if isinstance(pack_core, dict) else None
    evidence_core = evidence_pack.get("core")
    if not isinstance(evidence_core, dict):
        raise SystemExit(f"{evidence_pack_path}: missing core")
    evidence_core_sha = evidence_core.get("sha256")
    if not isinstance(evidence_core_sha, str) or SHA256_RE.fullmatch(evidence_core_sha) is None:
        raise SystemExit(f"{evidence_pack_path}: core.sha256 must be a lowercase 64-character SHA256")
    if isinstance(pack_core_sha, str) and evidence_core_sha != pack_core_sha:
        raise SystemExit(
            f"{evidence_pack_path}: core.sha256 must match {manifest_path}: core.sha256 "
            "before planning player identity snapshots"
        )
    evidence_core_path_raw = evidence_core.get("path")
    if not isinstance(evidence_core_path_raw, str) or not evidence_core_path_raw:
        raise SystemExit(f"{evidence_pack_path}: core.path must be a non-empty string")
    evidence_core_path = manifest_relative_path(Path(evidence_core_path_raw), evidence_pack_path)
    reject_symlink_component(evidence_core_path, f"{evidence_pack_path}: core.path")
    reject_protected_input_path(evidence_core_path, f"{evidence_pack_path}: core.path")


def load_targets(args: argparse.Namespace) -> tuple[list[str], dict[str, object]]:
    targets = list(args.target)
    target_sets: list[str] = []
    for target_set in args.target_set:
        if target_set not in TARGET_SETS:
            raise SystemExit(f"unknown --target-set: {target_set}")
        if target_set == PLAYER_IDENTITY_TARGET_SET:
            raise SystemExit(
                f"--target-set {PLAYER_IDENTITY_TARGET_SET} expands the full "
                f"{len(PLAYER_IDENTITY_TARGETS)}-target planning set. The current player identity "
                "gap route should plan exact focal snapshots with "
                "--target ShooterPlayerController.ServerListPlayers and "
                "--target ShooterPlayerController.ServerKickPlayer."
            )
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
    functions, inventory = load_functions(inventory_path)
    targets, target_source = load_targets(args)
    require_player_identity_target_set_scope(
        manifest_path,
        manifest,
        inventory_path,
        inventory,
        target_source["target_sets"],  # type: ignore[arg-type]
        targets,
    )

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
