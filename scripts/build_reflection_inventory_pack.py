#!/usr/bin/env python3
"""Build a redacted offline reflection inventory pack from a copied core artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import scan_core_fname_tables as fname_scanner  # noqa: E402
import reflection_target_sets  # noqa: E402
import summarize_core_ufunction_inventory as ufunction_inventory  # noqa: E402
import ufunction_focal_snapshot_plan as focal_planner  # noqa: E402
from snapshot_evidence_pack import (  # noqa: E402
    CORE_DUMP_EVIDENCE_PACK_SCHEMA,
    SHA256_RE,
    evidence_pack_defaults,
    reject_protected_input_path,
    reject_protected_output_path,
    reject_symlink_component,
    require_ignored_output_path,
    safe_component,
    sha256_file,
)


PACK_SCHEMA = "obelisk.reflection-inventory-pack.v1"
PLAYER_IDENTITY_TARGET_SET = "players-identity-lifecycle-intake"
DIRECT_PLAYER_IDENTITY_GATE_TARGETS = frozenset(
    (
        "ShooterPlayerController.ServerListPlayers",
        "ShooterPlayerController.ServerKickPlayer",
    )
)
DEFAULT_MAX_OBJECTS = ufunction_inventory.DEFAULT_MAX_OBJECTS
DEFAULT_MAX_GROUPS = 20


def parse_index(value: str) -> tuple[str, int]:
    return fname_scanner.parse_index(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a candidate-only offline reflection inventory pack.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--core", type=Path, help="Copied/offline ELF core path.")
    source.add_argument("--evidence-pack-manifest", type=Path, help="Validated core evidence-pack manifest.")
    parser.add_argument("--binary", type=Path, help="Copied/offline ShooterGameServer path for direct mode identity.")
    parser.add_argument("--ark-binary-sha256", help="Expected lowercase ShooterGameServer SHA256.")
    parser.add_argument("--gobjects", type=ufunction_inventory.parse_int)
    parser.add_argument("--fname-root-slot", type=ufunction_inventory.parse_int)
    parser.add_argument("--evidence-pack-fname-root-label")
    parser.add_argument("--evidence-pack-gobjects-label")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--artifact-kind", default="offline_core")
    parser.add_argument("--capture-id")
    parser.add_argument("--evidence-pack-id")
    parser.add_argument(
        "--evidence-obelisk-commit",
        help="Reviewed Obelisk commit/id to embed in emitted focal snapshot commands.",
    )
    parser.add_argument("--max-objects", type=int, default=DEFAULT_MAX_OBJECTS)
    parser.add_argument("--max-groups", type=int, default=DEFAULT_MAX_GROUPS)
    parser.add_argument("--outer-contains")
    parser.add_argument("--name-contains")
    parser.add_argument("--family")
    parser.add_argument("--min-params", type=int)
    parser.add_argument("--max-params", type=int)
    parser.add_argument("--include-functions", action="store_true")
    parser.add_argument(
        "--target-set",
        action="append",
        choices=ufunction_inventory.UFUNCTION_TARGET_SETS,
        default=[],
        help="Report coverage against a named UFunction target set.",
    )
    parser.add_argument(
        "--plan-target",
        action="append",
        default=[],
        metavar="Outer.Name",
        help=(
            "Plan one exact ad hoc UFunction snapshot without adding a target set. "
            "Useful for second-wave candidates such as PrimalStructure.IsAllowedToBuild."
        ),
    )
    parser.add_argument(
        "--plan-snapshot-target-set",
        action="append",
        choices=ufunction_inventory.UFUNCTION_TARGET_SETS,
        default=[],
        metavar="TARGET_SET",
        help=(
            "Plan exact candidate-only UFunction snapshots for every target in a closed "
            "target set, without adding fixtures or public SDK scope."
        ),
    )
    parser.add_argument(
        "--fname-index",
        action="append",
        type=parse_index,
        default=[],
        metavar="LABEL=INDEX",
        help="FName index expected from the root slot. Defaults to known Obelisk clues.",
    )
    parser.add_argument(
        "--no-default-fname-indices",
        action="store_true",
        help="Do not use built-in FName root validation clues.",
    )
    parser.add_argument("--plan-regeneration", action="store_true", help="Include a dry-run snapshot regeneration plan.")
    parser.add_argument(
        "--snapshot-manifest",
        type=Path,
        default=ufunction_inventory.DEFAULT_SNAPSHOT_MANIFEST,
        help="Candidate-only UFunction snapshot manifest used by --plan-regeneration.",
    )
    return parser.parse_args()


def validate_binary_sha(value: str, label: str) -> str:
    if SHA256_RE.fullmatch(value) is None:
        raise SystemExit(f"{label} must be a lowercase 64-character SHA256")
    return value


def resolve_binary_sha(args: argparse.Namespace) -> str:
    if args.binary:
        binary_path = reject_protected_input_path(args.binary, "--binary")
        observed = sha256_file(binary_path)
        if args.ark_binary_sha256 and observed != args.ark_binary_sha256:
            raise SystemExit("--ark-binary-sha256 does not match --binary contents")
        return observed
    if not args.ark_binary_sha256:
        raise SystemExit("direct --core mode requires --binary or --ark-binary-sha256")
    return validate_binary_sha(args.ark_binary_sha256, "--ark-binary-sha256")


def load_evidence_defaults(args: argparse.Namespace) -> tuple[Path, int, int, str | None, str, str, str, str]:
    if args.gobjects is not None or args.fname_root_slot is not None or args.binary is not None:
        raise SystemExit("--evidence-pack-manifest reads binary/core/gobjects/fname root from manifest; do not pass overrides")
    reject_symlink_component(args.evidence_pack_manifest, "--evidence-pack-manifest")
    manifest = reject_protected_input_path(args.evidence_pack_manifest, "--evidence-pack-manifest")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    binary = payload.get("binary")
    binary_sha = binary.get("sha256") if isinstance(binary, dict) else None
    if not isinstance(binary_sha, str):
        raise SystemExit(f"{manifest}: evidence pack manifest must include binary.sha256")
    binary_sha = validate_binary_sha(binary_sha, f"{manifest}: binary.sha256")
    if args.ark_binary_sha256 and args.ark_binary_sha256 != binary_sha:
        raise SystemExit(f"{manifest}: binary.sha256 conflicts with --ark-binary-sha256")
    defaults = evidence_pack_defaults(
        manifest,
        args.evidence_pack_fname_root_label,
        args.evidence_pack_gobjects_label,
        binary_sha,
        ufunction_inventory.parse_int,
    )
    return (
        defaults.core_path,
        defaults.gobjects,
        defaults.fname_root_slot,
        binary_sha,
        defaults.artifact_kind,
        defaults.capture_id,
        defaults.evidence_pack_id,
        defaults.artifact_sha256,
    )


def reject_artifact_symlink(path: Path) -> None:
    if path.is_symlink():
        raise SystemExit(f"refusing to overwrite symlinked pack artifact: {path}")


def write_json(path: Path, payload: dict[str, object]) -> None:
    reject_artifact_symlink(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def has_inventory_filters(args: argparse.Namespace) -> bool:
    return any(
        value is not None
        for value in (args.outer_contains, args.name_contains, args.family, args.min_params, args.max_params)
    )


def player_identity_targets_from_requests(requested_targets: list[str]) -> list[str]:
    matched: set[str] = set()
    for target in requested_targets:
        _, outer, name = focal_planner.parse_exact_target(target)
        short_target = f"{outer}.{name}"
        if short_target in DIRECT_PLAYER_IDENTITY_GATE_TARGETS:
            matched.add(short_target)
    return sorted(matched)


def main() -> int:
    args = parse_args()
    direct_plan_targets = list(args.plan_target)
    plan_snapshot_targets = list(args.plan_target)
    if args.plan_snapshot_target_set:
        plan_snapshot_targets.extend(
            sorted(
                reflection_target_sets.expand_schema_target_sets(
                    args.plan_snapshot_target_set,
                    "obelisk.ufunction-chain.snapshot.v1",
                )
            )
        )
    requested_player_identity_targets = player_identity_targets_from_requests(direct_plan_targets)
    if requested_player_identity_targets:
        raise SystemExit(
            "player identity focal snapshots must be planned with "
            "scripts/plan_ufunction_focal_snapshots.py after a reviewed "
            f"{PLAYER_IDENTITY_TARGET_SET} reflection inventory pack; "
            "do not use build_reflection_inventory_pack.py --plan-target for this lane"
        )
    if PLAYER_IDENTITY_TARGET_SET in args.plan_snapshot_target_set:
        raise SystemExit(
            "player identity target-set focal snapshots must be planned with exact "
            "ShooterPlayerController.ServerListPlayers and ShooterPlayerController.ServerKickPlayer "
            "targets through scripts/plan_ufunction_focal_snapshots.py after a reviewed "
            f"{PLAYER_IDENTITY_TARGET_SET} reflection inventory pack"
        )
    if PLAYER_IDENTITY_TARGET_SET in args.target_set and not args.evidence_pack_manifest:
        raise SystemExit(
            f"--target-set {PLAYER_IDENTITY_TARGET_SET} requires --evidence-pack-manifest "
            f"with complete {CORE_DUMP_EVIDENCE_PACK_SCHEMA}; direct --core mode is not enough"
        )
    if args.max_objects < 0:
        raise SystemExit("--max-objects must be non-negative")
    if args.max_groups <= 0:
        raise SystemExit("--max-groups must be positive")
    if args.min_params is not None and args.min_params < 0:
        raise SystemExit("--min-params must be non-negative")
    if args.max_params is not None and args.max_params < 0:
        raise SystemExit("--max-params must be non-negative")
    if args.min_params is not None and args.max_params is not None and args.min_params > args.max_params:
        raise SystemExit("--min-params must be less than or equal to --max-params")
    if args.plan_regeneration and not args.target_set and not plan_snapshot_targets:
        raise SystemExit("--plan-regeneration requires at least one --target-set or --plan-target")
    target_set_plan_regeneration = args.plan_regeneration and bool(args.target_set)

    output_dir = reject_protected_output_path(args.output_dir, "--output-dir")
    require_ignored_output_path(output_dir, "--output-dir")
    if output_dir.exists() and output_dir.is_symlink():
        raise SystemExit(f"--output-dir must not be a symlink: {output_dir}")

    if args.evidence_pack_manifest:
        (
            core,
            gobjects,
            fname_root_slot,
            binary_sha,
            artifact_kind,
            capture_id,
            evidence_pack_id,
            core_sha,
        ) = load_evidence_defaults(args)
        evidence_pack_manifest = reject_protected_input_path(args.evidence_pack_manifest, "--evidence-pack-manifest")
    else:
        if args.gobjects is None or args.fname_root_slot is None:
            raise SystemExit("direct --core mode requires explicit --gobjects and --fname-root-slot")
        core = reject_protected_input_path(args.core, "--core")
        gobjects = args.gobjects
        fname_root_slot = args.fname_root_slot
        binary_sha = resolve_binary_sha(args)
        artifact_kind = safe_component(args.artifact_kind, "artifact-kind")
        if plan_snapshot_targets and artifact_kind == "offline_core" and (
            not args.capture_id or not args.evidence_pack_id
        ):
            raise SystemExit(
                "direct --core snapshot planning requires explicit --capture-id and --evidence-pack-id"
            )
        capture_id = safe_component(args.capture_id or core.stem, "capture-id")
        evidence_pack_id = safe_component(args.evidence_pack_id or "direct-core", "evidence-pack-id")
        core_sha = sha256_file(core)
        evidence_pack_manifest = None
    if plan_snapshot_targets and artifact_kind != "offline_core":
        raise SystemExit("snapshot planning only supports offline_core artifact identity")
    if plan_snapshot_targets and not args.evidence_obelisk_commit:
        raise SystemExit("snapshot planning requires explicit --evidence-obelisk-commit")

    output_dir.mkdir(parents=True, exist_ok=True)

    if target_set_plan_regeneration:
        reject_protected_input_path(args.snapshot_manifest, "--snapshot-manifest")
        snapshot_manifest = ufunction_inventory.load_snapshot_manifest(args.snapshot_manifest)
    else:
        snapshot_manifest = None

    indices = args.fname_index if (args.fname_index or args.no_default_fname_indices) else fname_scanner.DEFAULT_INDICES
    memory = fname_scanner.CoreMemory(core)
    plan_functions: list[dict[str, object]] | None = None
    try:
        root_validation = fname_scanner.validate_root_slot(memory, fname_root_slot, indices)
        root_readiness = fname_scanner.root_validation_readiness(root_validation, indices)
        filters = {
            "outer_contains": args.outer_contains,
            "name_contains": args.name_contains,
            "family": args.family,
            "min_params": args.min_params,
            "max_params": args.max_params,
        }
        inventory_payload = ufunction_inventory.build_ufunction_inventory_payload(
            memory,
            core=core,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            max_objects=args.max_objects,
            max_groups=args.max_groups,
            filters=filters,
            target_sets=args.target_set,
            include_functions=args.include_functions or bool(plan_snapshot_targets),
            redact_pointers=True,
            snapshot_manifest=snapshot_manifest,
            snapshot_manifest_path=args.snapshot_manifest if target_set_plan_regeneration else None,
            plan_regeneration=target_set_plan_regeneration,
            evidence_pack_manifest=evidence_pack_manifest,
            evidence_pack_payload=(
                {
                    "manifest": str(evidence_pack_manifest),
                    "binary_sha256": binary_sha,
                    "core_sha256": core_sha,
                }
                if evidence_pack_manifest
                else None
            ),
        )
        if plan_snapshot_targets:
            if has_inventory_filters(args):
                plan_payload = ufunction_inventory.build_ufunction_inventory_payload(
                    memory,
                    core=core,
                    gobjects=gobjects,
                    fname_root_slot=fname_root_slot,
                    max_objects=args.max_objects,
                    max_groups=args.max_groups,
                    filters={
                        "outer_contains": None,
                        "name_contains": None,
                        "family": None,
                        "min_params": None,
                        "max_params": None,
                    },
                    target_sets=[],
                    include_functions=True,
                    redact_pointers=True,
                )
                functions = plan_payload.get("functions")
            else:
                functions = inventory_payload.get("functions")
            if not isinstance(functions, list):
                raise SystemExit("--plan-target requires redacted function inventory")
            plan_functions = [item for item in functions if isinstance(item, dict)]
        fname_table = memory.read_ptr(fname_root_slot)
    finally:
        memory.close()

    if plan_snapshot_targets:
        if plan_functions is None:
            raise SystemExit("snapshot planning requires redacted function inventory")
        inventory_payload["focal_snapshot_plan"] = focal_planner.focal_snapshot_plan(
            plan_functions,
            requested_targets=plan_snapshot_targets,
            core=core,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            binary_sha=binary_sha,
            core_sha=core_sha,
            capture_id=capture_id,
            evidence_pack_id=evidence_pack_id,
            max_object_scan=args.max_objects,
            fname_root_ready=root_readiness["ready"] is True,
            fname_root_blockers=[str(item) for item in root_readiness["blockers"]],
            artifact_identity_source="evidence-pack-manifest" if evidence_pack_manifest else "direct-core-explicit",
            obelisk_commit=args.evidence_obelisk_commit,
            repo_root=SCRIPT_DIR.parent,
        )

    fname_payload = {
        "schema": fname_scanner.ROOT_VALIDATION_SCHEMA,
        "core": str(core),
        "requested_indices": [{"label": label, "index": index} for label, index in indices],
        "root_validation": root_validation,
        "manifest_readiness": root_readiness,
        "candidate_manifest": {
            "path": None,
            "schema": None,
            "evidence_status": None,
            "name_count": 0,
        },
    }
    coverage = inventory_payload.get("target_set_coverage") if isinstance(inventory_payload, dict) else None
    summary = {
        "function_count": inventory_payload["summary"]["function_count"],
        "fname_root_ready": root_readiness["ready"],
        "target_requested_count": coverage.get("requested_count", 0) if isinstance(coverage, dict) else 0,
        "target_matched_count": coverage.get("matched_count", 0) if isinstance(coverage, dict) else 0,
        "target_missing_count": coverage.get("missing_count", 0) if isinstance(coverage, dict) else 0,
        "target_ambiguous_count": coverage.get("ambiguous_count", 0) if isinstance(coverage, dict) else 0,
    }
    blockers = list(root_readiness["blockers"]) if root_readiness["ready"] is not True else []
    if summary["target_ambiguous_count"]:
        blockers.append("ambiguous_target_matches")
    manifest_payload: dict[str, object] = {
        "schema": PACK_SCHEMA,
        "source": "offline_core",
        "status": "candidate-only",
        "promotion_status": "not_promoted_candidate_only",
        "artifact_identity": {
            "artifact_kind": artifact_kind,
            "artifact_sha256": core_sha,
            "capture_id": capture_id,
            "evidence_pack_id": evidence_pack_id,
        },
        "binary": {"sha256": binary_sha},
        "core": {"path": str(core), "sha256": core_sha},
        "addresses": {
            "gobjects": f"0x{gobjects:x}",
            "fname_root_slot": f"0x{fname_root_slot:x}",
            "fname_table": f"0x{fname_table:x}" if fname_table else None,
        },
        "inputs": {
            "evidence_pack_manifest": str(evidence_pack_manifest) if evidence_pack_manifest else None,
            "target_sets": args.target_set,
            "plan_targets": args.plan_target,
            "plan_snapshot_target_sets": args.plan_snapshot_target_set,
            "max_objects": args.max_objects,
            "fname_indices": [{"label": label, "index": index} for label, index in indices],
        },
        "artifacts": {
            "ufunction_inventory": "ufunction-inventory.json",
            "fname_root_validation": "fname-root-validation.json",
        },
        "summary": summary,
        "blockers": blockers,
        "non_claims": [
            "Does not promote GObjects/GUObjectArray as runtime-stable.",
            "Does not expose UObject pointers, raw params, object identity, mutation, or return overrides.",
            "Does not prove ResourceHandle lifetime or serial reuse semantics.",
            "Does not claim portability across ARK binary hashes.",
        ],
    }

    write_json(output_dir / "ufunction-inventory.json", inventory_payload)
    write_json(output_dir / "fname-root-validation.json", fname_payload)
    write_json(output_dir / "manifest.json", manifest_payload)
    print(json.dumps(manifest_payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
