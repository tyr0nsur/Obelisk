#!/usr/bin/env python3
"""Combined preflight for the player-identity first-evidence lane."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_SCHEMA = "obelisk.player-identity-first-evidence-readiness.v1"
PLAYER_IDENTITY_TARGET_SET = "players-identity-lifecycle-intake"
MISSING_TARGET_PREFIX = "missing_required_target:"
MAX_DIAGNOSIS_ITEMS = 8


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
    coverage_result, coverage_payload = run_json_command(
        [
            str(SCRIPT_DIR / "compare_reflection_snapshots.py"),
            "--base-root",
            str(args.snapshot_root),
            "--target-set",
            PLAYER_IDENTITY_TARGET_SET,
            "--readiness-report",
            "--json",
        ]
    )
    first_evidence_result, first_evidence_payload = run_json_command(
        [
            str(SCRIPT_DIR / "build_redacted_ufunction_signatures.py"),
            "--snapshot-root",
            str(args.snapshot_root),
            "--players-identity-first-evidence",
            "--json",
        ]
    )

    inventory_ready = bool(inventory_payload and inventory_payload.get("ready") is True)
    coverage_totals = coverage_payload.get("totals", {}) if isinstance(coverage_payload, dict) else {}
    coverage_targets = coverage_totals.get("targets")
    coverage_comparable = coverage_totals.get("comparable")
    coverage_blocked = coverage_totals.get("blocked")
    second_source_missing = second_source_missing_count(coverage_payload)
    first_evidence_ready = first_evidence_result.returncode == 0 and first_evidence_payload is not None
    missing_targets = parse_missing_required_targets(first_evidence_result.stderr)
    lifecycle_diagnosis = lifecycle_anchor_diagnosis(first_evidence_payload)
    lifecycle_ready = (
        lifecycle_diagnosis["session_start_accepted"] is True
        and lifecycle_diagnosis["session_end_accepted"] is True
    )

    blockers: list[str] = []
    if not inventory_ready:
        blockers.append("missing_reflection_inventory_pack_or_core_evidence_pack")
    if coverage_result.returncode != 0 or coverage_blocked:
        blockers.append("fixture_coverage_incomplete")
    if second_source_missing:
        blockers.append("second_source_evidence_missing")
    if not first_evidence_ready:
        blockers.append("players_identity_first_evidence_not_buildable")
    if not lifecycle_ready:
        blockers.append("accepted_lifecycle_anchors_missing")

    next_step = (
        "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack"
        if not inventory_ready
        else "plan_missing_server_list_players_and_server_kick_player_snapshots"
    )
    if first_evidence_ready and (second_source_missing or not lifecycle_ready):
        next_step = "produce_distinct_second_source_and_accepted_lifecycle_anchor_evidence"
    elif first_evidence_ready:
        next_step = "validate_players_identity_first_evidence_consume_and_promote_blocked"

    return {
        "schema": REPORT_SCHEMA,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "artifact_root": str(args.artifact_root),
        "snapshot_root": str(args.snapshot_root),
        "target_set": PLAYER_IDENTITY_TARGET_SET,
        "blockers": blockers,
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
