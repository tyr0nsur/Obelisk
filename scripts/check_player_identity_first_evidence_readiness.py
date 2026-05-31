#!/usr/bin/env python3
"""Combined preflight for the player-identity first-evidence lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_SCHEMA = "obelisk.player-identity-first-evidence-readiness.v1"
PLAYER_IDENTITY_TARGET_SET = "players-identity-lifecycle-intake"
MISSING_TARGET_PREFIX = "missing_required_target:"
MAX_DIAGNOSIS_ITEMS = 8
EXPECTED_SHOOTERGAME_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
REQUIRED_ADMIN_TARGETS = [
    "ShooterPlayerController.ServerKickPlayer",
    "ShooterPlayerController.ServerListPlayers",
]
CORE_EVIDENCE_MANIFEST_PATTERN = (
    "player-identity-offline-<run-id>/core-evidence-pack/manifest.json"
)
REFLECTION_INVENTORY_MANIFEST_PATTERN = (
    "player-identity-offline-<run-id>/reflection-inventory-pack/manifest.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the read-only player-identity preflight: reflection-inventory pack "
            "readiness, committed fixture coverage, and first-evidence fail-closed build."
        )
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("/home/flowcommunity-ark/obelisk-artifacts"),
        help="Non-protected artifact root to scan for reflection inventory packs.",
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
        help="Sanitized UFunction snapshot root used for fixture coverage and first-evidence build.",
    )
    parser.add_argument(
        "--candidate-root",
        type=Path,
        help="Optional distinct sanitized second-source snapshot root for layout comparison.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Compatibility flag; output is always JSON.",
    )
    return parser.parse_args()


def run_json_command(args: list[str], *, check: bool = False) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]:
    result = subprocess.run(
        [sys.executable, *args],
        check=False,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    payload: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return result, payload


def parse_missing_required_targets(stderr: str) -> list[str]:
    missing: list[str] = []
    for token in stderr.replace(",", " ").split():
        if token.startswith(MISSING_TARGET_PREFIX):
            target = token.removeprefix(MISSING_TARGET_PREFIX)
            if target:
                missing.append(target)
    return sorted(set(missing))


def bounded_values(values: list[Any]) -> dict[str, Any]:
    if len(values) <= MAX_DIAGNOSIS_ITEMS:
        return {"items": values}
    return {
        "items": values[:MAX_DIAGNOSIS_ITEMS],
        "total_count": len(values),
        "omitted_count": len(values) - MAX_DIAGNOSIS_ITEMS,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bounded_artifact_file_scan(root: Path, *, max_depth: int = 6) -> dict[str, Any]:
    try:
        reject_symlink_component(root, "--artifact-root")
        resolved = reject_protected_input_path(root, "--artifact-root")
    except SystemExit as exc:
        return {
            "status": "artifact_root_rejected",
            "artifact_root_only": True,
            "error": str(exc),
            "server_root_excluded": "/servidor/ark",
            "shooter_game_server_candidates": [],
            "core_like_candidates": [],
            "ready_to_build_core_evidence_pack": False,
        }
    if not resolved.exists():
        return {
            "status": "artifact_root_missing",
            "artifact_root_only": True,
            "resolved_root": str(resolved),
            "server_root_excluded": "/servidor/ark",
            "shooter_game_server_candidates": [],
            "core_like_candidates": [],
            "ready_to_build_core_evidence_pack": False,
        }
    if not resolved.is_dir():
        return {
            "status": "artifact_root_not_directory",
            "artifact_root_only": True,
            "resolved_root": str(resolved),
            "server_root_excluded": "/servidor/ark",
            "shooter_game_server_candidates": [],
            "core_like_candidates": [],
            "ready_to_build_core_evidence_pack": False,
        }

    shooter_candidates: list[dict[str, Any]] = []
    core_candidates: list[dict[str, Any]] = []
    omitted_shooter = 0
    omitted_core = 0
    root_depth = len(resolved.parts)
    for directory, dirnames, filenames in os.walk(resolved, followlinks=False):
        current = Path(directory)
        depth = len(current.parts) - root_depth
        dirnames[:] = [name for name in dirnames if not (current / name).is_symlink()]
        if depth >= max_depth:
            dirnames[:] = []
        for filename in filenames:
            path = current / filename
            if path.is_symlink():
                continue
            lower_name = filename.lower()
            is_shooter = filename == "ShooterGameServer"
            is_core_like = lower_name == "core" or lower_name.startswith("core.") or lower_name.endswith(".core")
            if not is_shooter and not is_core_like:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if is_shooter:
                if len(shooter_candidates) < MAX_DIAGNOSIS_ITEMS:
                    try:
                        digest = sha256_file(path)
                    except OSError as exc:
                        digest = f"unreadable:{exc}"
                    shooter_candidates.append(
                        {
                            "path": str(path),
                            "size_bytes": stat.st_size,
                            "sha256": digest,
                            "matches_current_binary": digest == EXPECTED_SHOOTERGAME_SHA256,
                        }
                    )
                else:
                    omitted_shooter += 1
            if is_core_like:
                if len(core_candidates) < MAX_DIAGNOSIS_ITEMS:
                    core_candidates.append(
                        {
                            "path": str(path),
                            "size_bytes": stat.st_size,
                        }
                    )
                else:
                    omitted_core += 1

    has_matching_binary = any(candidate.get("matches_current_binary") is True for candidate in shooter_candidates)
    has_core_like = bool(core_candidates)
    if has_matching_binary and has_core_like:
        status = "offline_binary_and_core_like_inputs_present"
    elif has_matching_binary:
        status = "offline_binary_present_core_like_input_missing"
    elif shooter_candidates:
        status = "offline_binary_present_hash_mismatch"
    elif has_core_like:
        status = "core_like_input_present_offline_binary_missing"
    else:
        status = "offline_binary_and_core_like_inputs_missing"

    return {
        "status": status,
        "artifact_root_only": True,
        "resolved_root": str(resolved),
        "server_root_excluded": "/servidor/ark",
        "expected_shooter_game_server_sha256": EXPECTED_SHOOTERGAME_SHA256,
        "shooter_game_server_candidates": shooter_candidates,
        "omitted_shooter_game_server_candidates": omitted_shooter,
        "core_like_candidates": core_candidates,
        "omitted_core_like_candidates": omitted_core,
        "ready_to_build_core_evidence_pack": has_matching_binary and has_core_like,
        "non_claims": [
            "file presence only; core-like filenames are not accepted core evidence packs",
            "does not read /servidor/ark, attach to processes, execute scanners, or validate runtime state",
        ],
    }


def artifact_root_diagnosis(inventory_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not inventory_payload:
        return {
            "status": "inventory_readiness_output_missing_or_malformed",
            "candidate_pack_count": None,
            "reason_counts": {},
            "next_useful_command": "rerun_check_reflection_inventory_pack_readiness_with_json_stdout",
        }

    candidate_packs = inventory_payload.get("candidate_packs")
    if not isinstance(candidate_packs, list):
        candidate_packs = []
    reasons = inventory_payload.get("reasons")
    if not isinstance(reasons, list):
        reasons = []

    reason_counts: dict[str, int] = {}
    reason_examples: dict[str, dict[str, Any]] = {}
    for reason in reasons:
        if not isinstance(reason, dict):
            continue
        code = reason.get("reason")
        if not isinstance(code, str):
            continue
        reason_counts[code] = reason_counts.get(code, 0) + 1
        if code not in reason_examples:
            example: dict[str, Any] = {}
            if isinstance(reason.get("path"), str):
                example["path"] = reason["path"]
            if isinstance(reason.get("field"), str):
                example["field"] = reason["field"]
            if isinstance(reason.get("detail"), str):
                example["detail"] = reason["detail"]
            scanned_paths = reason.get("scanned_paths")
            if isinstance(scanned_paths, list):
                example["scanned_paths"] = bounded_values(scanned_paths)
            targets = reason.get("targets")
            if isinstance(targets, list):
                example["targets"] = bounded_values(targets)
            if example:
                reason_examples[code] = example

    blocked_candidate_summaries: list[dict[str, Any]] = []
    for pack in candidate_packs[:MAX_DIAGNOSIS_ITEMS]:
        if not isinstance(pack, dict):
            continue
        pack_reasons = pack.get("reasons")
        if not isinstance(pack_reasons, list):
            pack_reasons = []
        fields: list[str] = []
        codes: list[str] = []
        for reason in pack_reasons:
            if not isinstance(reason, dict):
                continue
            code = reason.get("reason")
            field = reason.get("field")
            if isinstance(code, str) and code not in codes:
                codes.append(code)
            if isinstance(field, str) and field not in fields:
                fields.append(field)
        blocked_candidate_summaries.append(
            {
                "manifest": pack.get("manifest"),
                "ready": pack.get("ready"),
                "reason_codes": codes[:MAX_DIAGNOSIS_ITEMS],
                "blocking_fields": fields[:MAX_DIAGNOSIS_ITEMS],
                "matched_targets": pack.get("matched_targets"),
            }
        )

    accepted_pack = inventory_payload.get("accepted_pack")
    if isinstance(accepted_pack, dict):
        status = "accepted_reflection_inventory_pack"
    elif not inventory_payload.get("manifests_scanned"):
        status = "no_manifest_files_found"
    elif not candidate_packs:
        status = "no_obelisk_reflection_inventory_pack_manifests_found"
    elif "missing_core_evidence_pack" in reason_counts:
        status = "reflection_inventory_pack_missing_complete_core_evidence_pack"
    elif "missing_target" in reason_counts:
        status = "reflection_inventory_pack_missing_required_admin_targets"
    elif "wrong_target_scope" in reason_counts:
        status = "reflection_inventory_pack_wrong_scope_or_candidate_status"
    else:
        status = "reflection_inventory_pack_blocked"

    return {
        "status": status,
        "candidate_pack_count": len(candidate_packs),
        "accepted_manifest": accepted_pack.get("manifest") if isinstance(accepted_pack, dict) else None,
        "reason_counts": reason_counts,
        "reason_examples": reason_examples,
        "blocked_candidate_packs": blocked_candidate_summaries,
        "next_useful_command": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_reflection_inventory_pack_readiness.py "
            "--root <artifact-root>"
        ),
    }


def second_source_missing_count(coverage_payload: dict[str, Any] | None) -> int | None:
    if not isinstance(coverage_payload, dict):
        return None
    totals = coverage_payload.get("totals")
    if not isinstance(totals, dict):
        return None
    value = totals.get("second_source_missing")
    return value if isinstance(value, int) else None


def second_source_total(coverage_payload: dict[str, Any] | None, key: str) -> int | None:
    if not isinstance(coverage_payload, dict):
        return None
    totals = coverage_payload.get("totals")
    if not isinstance(totals, dict):
        return None
    value = totals.get(key)
    return value if isinstance(value, int) else None


def lifecycle_anchor_diagnosis(first_evidence_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(first_evidence_payload, dict):
        return {
            "session_start_accepted": False,
            "session_end_accepted": False,
            "accepted_start_targets": [],
            "accepted_end_targets": [],
            "blockers": [
                "players_identity_first_evidence_not_buildable",
                "accepted_session_start_anchor_missing",
                "accepted_session_end_anchor_missing",
            ],
        }
    anchors = first_evidence_payload.get("lifecycle_anchors")
    if not isinstance(anchors, dict):
        return {
            "session_start_accepted": False,
            "session_end_accepted": False,
            "accepted_start_targets": [],
            "accepted_end_targets": [],
            "blockers": [
                "lifecycle_anchors_missing_from_first_evidence",
                "accepted_session_start_anchor_missing",
                "accepted_session_end_anchor_missing",
            ],
        }
    blockers = anchors.get("blockers")
    accepted_start_targets = anchors.get("accepted_start_targets")
    accepted_end_targets = anchors.get("accepted_end_targets")
    return {
        "session_start_accepted": anchors.get("session_start_accepted") is True,
        "session_end_accepted": anchors.get("session_end_accepted") is True,
        "accepted_start_targets": accepted_start_targets if isinstance(accepted_start_targets, list) else [],
        "accepted_end_targets": accepted_end_targets if isinstance(accepted_end_targets, list) else [],
        "blockers": blockers if isinstance(blockers, list) else [],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inventory_result, inventory_payload = run_json_command(
        [
            str(SCRIPT_DIR / "check_reflection_inventory_pack_readiness.py"),
            "--root",
            str(args.artifact_root),
        ]
    )
    coverage_command = [
        str(SCRIPT_DIR / "compare_reflection_snapshots.py"),
        "--base-root",
        str(args.snapshot_root),
        "--target-set",
        PLAYER_IDENTITY_TARGET_SET,
        "--readiness-report",
        "--json",
    ]
    if args.candidate_root:
        coverage_command.extend(["--candidate-root", str(args.candidate_root)])
    coverage_result, coverage_payload = run_json_command(coverage_command)
    first_evidence_result, first_evidence_payload = run_json_command(
        [
            str(SCRIPT_DIR / "build_redacted_ufunction_signatures.py"),
            "--snapshot-root",
            str(args.snapshot_root),
            "--players-identity-first-evidence",
            "--json",
        ]
    )
    orientation_result, orientation_payload = run_json_command(
        [
            str(SCRIPT_DIR / "check_player_identity_static_orientation.py"),
            "--json",
        ]
    )

    inventory_ready = bool(inventory_payload and inventory_payload.get("ready") is True)
    coverage_totals = coverage_payload.get("totals", {}) if isinstance(coverage_payload, dict) else {}
    coverage_targets = coverage_totals.get("targets")
    coverage_comparable = coverage_totals.get("comparable")
    coverage_blocked = coverage_totals.get("blocked")
    second_source_missing = second_source_missing_count(coverage_payload)
    second_source_inconclusive = second_source_total(coverage_payload, "second_source_inconclusive")
    second_source_rejected = second_source_total(coverage_payload, "second_source_rejected")
    first_evidence_ready = first_evidence_result.returncode == 0 and first_evidence_payload is not None
    missing_targets = parse_missing_required_targets(first_evidence_result.stderr)
    lifecycle_diagnosis = lifecycle_anchor_diagnosis(first_evidence_payload)
    lifecycle_ready = (
        lifecycle_diagnosis["session_start_accepted"] is True
        and lifecycle_diagnosis["session_end_accepted"] is True
    )
    offline_inputs = bounded_artifact_file_scan(args.artifact_root)

    downstream_blockers: list[str] = []
    if not inventory_ready:
        blockers = ["missing_reflection_inventory_pack_or_core_evidence_pack"]
    else:
        blockers = []
    if coverage_result.returncode != 0 or coverage_blocked:
        downstream_blockers.append("fixture_coverage_incomplete")
    if second_source_missing:
        downstream_blockers.append("second_source_evidence_missing")
    if second_source_inconclusive or second_source_rejected:
        downstream_blockers.append("second_source_evidence_not_accepted")
    if not first_evidence_ready:
        downstream_blockers.append("players_identity_first_evidence_not_buildable")
    if not lifecycle_ready:
        downstream_blockers.append("accepted_lifecycle_anchors_missing")
    if inventory_ready:
        blockers.extend(downstream_blockers)

    next_step = (
        "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack"
        if not inventory_ready
        else "plan_missing_server_list_players_and_server_kick_player_snapshots"
    )
    if inventory_ready:
        if first_evidence_ready and (second_source_missing or not lifecycle_ready):
            next_step = "produce_distinct_second_source_and_accepted_lifecycle_anchor_evidence"
        elif first_evidence_ready:
            next_step = "validate_players_identity_first_evidence_consume_and_promote_blocked"

    core_manifest_pattern = args.artifact_root / CORE_EVIDENCE_MANIFEST_PATTERN
    reflection_inventory_pattern = args.artifact_root / REFLECTION_INVENTORY_MANIFEST_PATTERN
    raw_binary_pattern = args.artifact_root / "player-identity-offline-<run-id>" / "raw" / "ShooterGameServer"
    raw_core_pattern = args.artifact_root / "player-identity-offline-<run-id>" / "raw" / "core"
    next_operator_recipe = {
        "blocked_until": "accepted_reflection_inventory_pack",
        "build_core_evidence_pack": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_core_dump_evidence_pack.py "
            f"--binary {raw_binary_pattern} "
            f"--core {raw_core_pattern} "
            f"--output-dir {core_manifest_pattern.parent} "
            "--obelisk-commit <reviewed-obelisk-id> "
            "--no-default-candidates "
            "--no-default-fname-roots "
            "--no-default-fname-indices "
            "--fname-root-slot verified_fname_root_slot=0x5956f30 "
            "--fname-index None=0 "
            "--fname-index ClientMessage=4884 "
            "--fname-index ServerChat=9619 "
            "--fname-index SetActiveMissionDebugFlags=9622 "
            "--gobjects-candidate gobjects=0x595b7e0 "
            "--gobjects-sample-index 0 "
            "--gobjects-sample-index 1 "
            "--gobjects-sample-index 25447"
        ),
        "build_reflection_inventory_pack": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_reflection_inventory_pack.py "
            f"--evidence-pack-manifest {core_manifest_pattern} "
            "--evidence-pack-fname-root-label verified_fname_root_slot "
            "--evidence-pack-gobjects-label gobjects "
            f"--target-set {PLAYER_IDENTITY_TARGET_SET} "
            f"--include-functions --output-dir {reflection_inventory_pattern.parent}"
        ),
        "check_reflection_inventory_pack": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_reflection_inventory_pack_readiness.py "
            f"--root {reflection_inventory_pattern.parent}"
        ),
        "plan_admin_focal_snapshots": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/plan_ufunction_focal_snapshots.py "
            f"--inventory-pack {reflection_inventory_pattern} "
            "--target ShooterPlayerController.ServerListPlayers "
            "--target ShooterPlayerController.ServerKickPlayer "
            "--evidence-obelisk-commit <reviewed-obelisk-id> "
            "--json-out <ignored-output-path>/player-identity-admin-focal-plan.json"
        ),
        "forbidden_next_commands": [
            "do not read from or write to /servidor/ark for this preflight recipe",
            "do not use --target-set players-identity-lifecycle-intake with plan_ufunction_focal_snapshots.py",
            "do not use direct --core mode for players-identity-lifecycle-intake",
            "do not use --skip-core-sha256 or --allow-partial-gdb for player identity evidence packs",
        ],
        "non_claims": [
            "recipe only; this report does not execute commands, read cores, write artifacts, or touch servers",
            "planned admin focal snapshots remain candidate-only and do not promote public identity, permissions, commands, runtime hooks, mutation, lookup, return override, or SDK surface",
        ],
    }

    return {
        "schema": REPORT_SCHEMA,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "artifact_root": str(args.artifact_root),
        "snapshot_root": str(args.snapshot_root),
        "candidate_root": str(args.candidate_root) if args.candidate_root else None,
        "target_set": PLAYER_IDENTITY_TARGET_SET,
        "blockers": blockers,
        "deferred_until_reflection_inventory_ready": [] if inventory_ready else downstream_blockers,
        "next_required_artifacts": [] if inventory_ready else [
            {
                "schema": "obelisk.core-dump-evidence-pack.v1",
                "path_pattern": str(core_manifest_pattern),
                "purpose": "non_protected_complete_core_evidence",
            },
            {
                "schema": "obelisk.reflection-inventory-pack.v1",
                "path_pattern": str(reflection_inventory_pattern),
                "purpose": "reviewed_target_inventory_for_player_identity_lifecycle_intake",
            },
        ],
        "next_operator_recipe": next_operator_recipe,
        "artifact_chain": {
            "core_evidence_pack_required": True,
            "reflection_inventory_pack_required": True,
            "accepted_reflection_inventory_pack": artifact_root_diagnosis(inventory_payload)["accepted_manifest"],
            "required_admin_targets": REQUIRED_ADMIN_TARGETS,
            "blocked_before_focal_planning": not inventory_ready,
            "ready_to_plan_admin_snapshots": inventory_ready,
            "offline_inputs": offline_inputs,
        },
        "static_orientation": {
            "returncode": orientation_result.returncode,
            "valid": (
                orientation_payload.get("valid")
                if isinstance(orientation_payload, dict)
                else False
            ),
            "accepted_for_orientation": (
                orientation_payload.get("accepted_for_orientation")
                if isinstance(orientation_payload, dict)
                else False
            ),
            "not_artifact_gate": (
                orientation_payload.get("not_artifact_gate")
                if isinstance(orientation_payload, dict)
                else True
            ),
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": (
                orientation_payload.get("blockers")
                if isinstance(orientation_payload, dict)
                else [{"reason": "static_orientation_check_output_missing_or_malformed"}]
            ),
            "non_claims": (
                orientation_payload.get("non_claims")
                if isinstance(orientation_payload, dict)
                else ["static orientation is candidate-only navigation evidence"]
            ),
        },
        "public_sdk_ready": False,
        "runtime_ready": False,
        "reflection_inventory": {
            "returncode": inventory_result.returncode,
            "ready": inventory_ready,
            "status": inventory_payload.get("status") if inventory_payload else None,
            "manifests_scanned": inventory_payload.get("manifests_scanned") if inventory_payload else None,
            "reason_codes": [
                reason.get("reason")
                for reason in (inventory_payload.get("reasons", []) if inventory_payload else [])
                if isinstance(reason, dict)
            ],
            "artifact_root_diagnosis": artifact_root_diagnosis(inventory_payload),
        },
        "fixture_coverage": {
            "returncode": coverage_result.returncode,
            "targets": coverage_targets,
            "comparable": coverage_comparable,
            "blocked": coverage_blocked,
            "promotion_ready": (
                coverage_payload.get("promotion_gate", {}).get("promotion_ready")
                if isinstance(coverage_payload, dict)
                else None
            ),
            "second_source_status": coverage_payload.get("second_source_status") if coverage_payload else None,
            "second_source_missing": second_source_missing,
            "second_source_inconclusive": second_source_inconclusive,
            "second_source_rejected": second_source_rejected,
        },
        "first_evidence": {
            "returncode": first_evidence_result.returncode,
            "ready": first_evidence_ready,
            "schema": first_evidence_payload.get("schema") if first_evidence_payload else None,
            "missing_required_targets": missing_targets,
            "lifecycle_anchors": lifecycle_diagnosis,
            "stderr": first_evidence_result.stderr.strip(),
        },
        "next_step": next_step,
        "non_claims": [
            "read-only preflight; does not touch servers, execute scanners, write artifacts, or promote public SDK",
            "success here would be candidate-only planning evidence, not public identity, permissions, commands, runtime hooks, mutation, return override, lookup, or ResourceHandle",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
