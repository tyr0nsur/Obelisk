#!/usr/bin/env python3
"""Fail-closed checker for Structure build-policy offline intake accounting."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
REPORT_SCHEMA = "obelisk.structure-build-policy-offline-intake-check.v1"
READINESS_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
SURFACE_ID = "obelisk.structure_census.v1"
TARGET_SET = "structure-build-policy-offline-intake"
EXPECTED_STATUS = "planning-layout-second-source-accepted"
EXPECTED_TOTALS = {
    "targets": 3,
    "comparable": 3,
    "second_source_accepted": 3,
    "blocked": 0,
}
EXPECTED_ZERO_TOTALS = {
    "second_source_rejected": 0,
    "second_source_inconclusive": 0,
    "second_source_missing": 0,
}
EXPECTED_READINESS_FLAGS = {
    "promotion_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
}
EXPECTED_TARGET_FILTERS = {
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuild",
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuildEx",
}
EXPECTED_NON_CLAIM = (
    "planning-layout evidence only; does not promote StructureEvents, Structure SDK, "
    "build-policy SDK, enforcement, identity, lookup, mutation, return override, "
    "runtime hooks, or v1 completion"
)
REQUIRED_NON_CLAIM_TOKENS = (
    "planning-layout evidence only",
    "does not promote",
    "StructureEvents",
    "Structure SDK",
    "build-policy SDK",
    "enforcement",
    "identity",
    "lookup",
    "mutation",
    "return override",
    "runtime hooks",
    "v1 completion",
)
REQUIRED_BOUNDARIES = (
    "candidate-only",
    "sanitized UFunction layout comparison only",
    "no public StructureEvents SDK",
    "no build-policy SDK or enforcement",
    "no structure identity or lookup",
    "no mutation or return override",
    "public_sdk_ready=false",
)
FORBIDDEN_TRUE_READY_KEYS = {
    "build_policy_ready",
    "build_policy_sdk_ready",
    "enforcement_ready",
    "identity_ready",
    "lookup_ready",
    "mutation_ready",
    "promotion_ready",
    "public_sdk_ready",
    "return_override_ready",
    "runtime_ready",
    "structure_events_ready",
    "structure_sdk_ready",
    "v1_complete",
    "v1_completion",
    "v1_ready",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the Structure build-policy offline readiness report referenced by "
            "docs/public_sdk_surfaces.json without promoting public SDK or runtime readiness."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="public_sdk_surfaces.json path.")
    parser.add_argument(
        "--readiness",
        type=Path,
        help="Override readiness report path. The manifest entry is still validated.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def read_json(path: Path, blockers: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, f"{label}_unreadable", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_malformed", path=str(path), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        add(blockers, f"{label}_not_object", path=str(path))
        return None
    return parsed


def sha256_file(path: Path, blockers: list[dict[str, Any]]) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        add(blockers, "readiness_unreadable_for_sha256", path=str(path), detail=str(exc))
        return None


def find_surface(manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        add(blockers, "manifest_surfaces_missing")
        return None
    matches = [surface for surface in surfaces if isinstance(surface, dict) and surface.get("id") == SURFACE_ID]
    if len(matches) != 1:
        add(blockers, "surface_id_match_count_mismatch", expected=1, value=len(matches), surface=SURFACE_ID)
        return None
    return matches[0]


def find_report_entry(surface: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    evidence = surface.get("evidence")
    reports = evidence.get("offline_readiness_reports") if isinstance(evidence, dict) else None
    if not isinstance(reports, list):
        add(blockers, "offline_readiness_reports_missing", surface=SURFACE_ID)
        return None
    matches = [report for report in reports if isinstance(report, dict) and report.get("target_set") == TARGET_SET]
    if not matches and len(reports) == 1 and isinstance(reports[0], dict):
        add(
            blockers,
            "manifest_report_target_set_mismatch",
            expected=TARGET_SET,
            value=reports[0].get("target_set"),
        )
        return reports[0]
    if len(matches) != 1:
        add(blockers, "offline_readiness_report_match_count_mismatch", expected=1, value=len(matches))
        return None
    return matches[0]


def missing_tokens(text: str, tokens: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [token for token in tokens if token.lower() not in lowered]


def validate_manifest_entry(entry: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    expected_values = {
        "target_set": TARGET_SET,
        "schema": READINESS_SCHEMA,
        "status": EXPECTED_STATUS,
        "non_claim": EXPECTED_NON_CLAIM,
    }
    for key, expected in expected_values.items():
        if entry.get(key) != expected:
            add(blockers, f"manifest_report_{key}_mismatch", expected=expected, value=entry.get(key))

    totals = entry.get("totals")
    if totals != EXPECTED_TOTALS:
        add(blockers, "manifest_report_totals_mismatch", expected=EXPECTED_TOTALS, value=totals)

    flags = entry.get("readiness_flags")
    if flags != EXPECTED_READINESS_FLAGS:
        add(blockers, "manifest_report_readiness_flags_mismatch", expected=EXPECTED_READINESS_FLAGS, value=flags)

    non_claim = entry.get("non_claim")
    if isinstance(non_claim, str):
        missing = missing_tokens(non_claim, REQUIRED_NON_CLAIM_TOKENS)
        if missing:
            add(blockers, "manifest_report_non_claim_missing_tokens", missing=missing)
    else:
        add(blockers, "manifest_report_non_claim_not_string", value=non_claim)


def validate_candidate_manifest(surface: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    candidate = surface.get("build_policy_offline_intake_candidate")
    if not isinstance(candidate, dict):
        add(blockers, "build_policy_offline_intake_candidate_missing")
        return
    expected_values = {
        "status": "candidate-only",
        "scope": "offline structure build-policy planning-layout audit only",
        "target_set": TARGET_SET,
        "target_count": 3,
        "target_names_redacted": True,
        "public_sdk_ready": False,
        "promotion_ready": False,
        "runtime_ready": False,
        "enforcement_ready": False,
        "must_remain_planning_only": True,
    }
    for key, expected in expected_values.items():
        if candidate.get(key) != expected:
            add(blockers, f"candidate_{key}_mismatch", expected=expected, value=candidate.get(key))

    boundaries = candidate.get("required_boundaries")
    if not isinstance(boundaries, list):
        add(blockers, "candidate_required_boundaries_missing")
        return
    missing = [boundary for boundary in REQUIRED_BOUNDARIES if boundary not in boundaries]
    if missing:
        add(blockers, "candidate_required_boundaries_missing_values", missing=missing)


def validate_referenced_sha(entry: dict[str, Any], readiness_path: Path, blockers: list[dict[str, Any]]) -> str | None:
    expected_sha = entry.get("sha256")
    actual_sha = sha256_file(readiness_path, blockers)
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        add(blockers, "manifest_report_sha256_missing_or_invalid", value=expected_sha)
    elif actual_sha is not None and actual_sha != expected_sha:
        add(blockers, "manifest_report_sha256_mismatch", expected=expected_sha, value=actual_sha)
    return actual_sha


def validate_readiness(readiness: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if readiness.get("schema") != READINESS_SCHEMA:
        add(blockers, "readiness_schema_mismatch", expected=READINESS_SCHEMA, value=readiness.get("schema"))
    if readiness.get("gate_mode") != "planning_layout_intake":
        add(blockers, "readiness_gate_mode_mismatch", expected="planning_layout_intake", value=readiness.get("gate_mode"))
    if readiness.get("second_source_status") != "compared":
        add(blockers, "readiness_second_source_status_mismatch", expected="compared", value=readiness.get("second_source_status"))

    target_sets = readiness.get("target_sets")
    if target_sets != [TARGET_SET]:
        add(blockers, "readiness_target_sets_mismatch", expected=[TARGET_SET], value=target_sets)

    target_filters = readiness.get("target_filters")
    actual_filters = set(target_filters) if isinstance(target_filters, list) else set()
    if actual_filters != EXPECTED_TARGET_FILTERS:
        add(
            blockers,
            "readiness_target_filters_mismatch",
            missing=sorted(EXPECTED_TARGET_FILTERS - actual_filters),
            unexpected=sorted(actual_filters - EXPECTED_TARGET_FILTERS),
        )

    totals = readiness.get("totals")
    if not isinstance(totals, dict):
        add(blockers, "readiness_totals_missing")
    else:
        for key, expected in {**EXPECTED_TOTALS, **EXPECTED_ZERO_TOTALS}.items():
            if totals.get(key) != expected:
                add(blockers, "readiness_total_mismatch", key=key, expected=expected, value=totals.get(key))

    planning_gate = readiness.get("planning_layout_gate")
    if not isinstance(planning_gate, dict):
        add(blockers, "planning_layout_gate_missing")
    else:
        expected_gate_values = {
            "ready": True,
            "layout_ready": True,
            "ready_scope": "planning_only",
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [],
        }
        for key, expected in expected_gate_values.items():
            if planning_gate.get(key) != expected:
                add(blockers, f"planning_layout_gate_{key}_mismatch", expected=expected, value=planning_gate.get(key))

    promotion_gate = readiness.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        add(blockers, "promotion_gate_missing")
    else:
        expected_promotion_values = {
            "ready": False,
            "layout_ready": True,
            "promotion_ready": False,
            "ready_scope": "planning_only",
        }
        for key, expected in expected_promotion_values.items():
            if promotion_gate.get(key) != expected:
                add(blockers, f"promotion_gate_{key}_mismatch", expected=expected, value=promotion_gate.get(key))
        blocker_reasons = {
            blocker.get("reason")
            for blocker in promotion_gate.get("blockers", [])
            if isinstance(blocker, dict)
        }
        if "planning_layout_intake_not_promotion_gate" not in blocker_reasons:
            add(blockers, "promotion_gate_blocker_missing", expected="planning_layout_intake_not_promotion_gate")

    non_claims = readiness.get("non_claims")
    if not isinstance(non_claims, list) or not all(isinstance(item, str) for item in non_claims):
        add(blockers, "readiness_non_claims_missing")
    else:
        joined = " ".join(non_claims)
        for token in (
            "layout evidence only",
            "does not promote public SDK",
            "Structure SDK",
            "StructureEvents",
            "object identity",
            "lookup",
            "mutation",
            "return override",
            "runtime hooks",
        ):
            if token.lower() not in joined.lower():
                add(blockers, "readiness_non_claims_missing_token", token=token)


def scan_for_forbidden_true_ready(payload: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_TRUE_READY_KEYS and value is True:
                add(blockers, "forbidden_readiness_true", path=child_path, key=key)
            scan_for_forbidden_true_ready(value, blockers, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            scan_for_forbidden_true_ready(value, blockers, f"{path}[{index}]")


def build_report(
    blockers: list[dict[str, Any]],
    *,
    readiness_path: Path | None,
    readiness_sha256: str | None,
) -> dict[str, Any]:
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "target_set": TARGET_SET,
        "status": "accepted_planning_only" if ready else "blocked",
        "ready": ready,
        "accepted_for_offline_planning": ready,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "enforcement_ready": False,
        "readiness_flags": {
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "enforcement_ready": False,
        },
        "expected_status": EXPECTED_STATUS,
        "expected_totals": EXPECTED_TOTALS,
        "readiness_path": str(readiness_path) if readiness_path is not None else None,
        "readiness_sha256": readiness_sha256,
        "non_claim": EXPECTED_NON_CLAIM,
        "non_claim_matrix": {
            "public_structure_events_sdk": "not_claimed",
            "structure_sdk": "not_claimed",
            "build_policy_sdk": "not_claimed",
            "enforcement": "not_claimed",
            "identity_lookup": "not_claimed",
            "mutation": "not_claimed",
            "return_override": "not_claimed",
            "runtime_hooks": "not_claimed",
            "v1_completion": "not_claimed",
        },
        "blockers": blockers,
    }


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []

    manifest = read_json(args.manifest, blockers, "manifest")
    surface: dict[str, Any] | None = None
    entry: dict[str, Any] | None = None
    readiness_path: Path | None = None
    readiness_sha256: str | None = None

    if manifest is not None:
        surface = find_surface(manifest, blockers)
    if surface is not None:
        entry = find_report_entry(surface, blockers)
        validate_candidate_manifest(surface, blockers)
    if entry is not None:
        validate_manifest_entry(entry, blockers)
        entry_path = entry.get("path")
        if not isinstance(entry_path, str) or not entry_path:
            add(blockers, "manifest_report_path_missing", value=entry_path)
        readiness_path = args.readiness if args.readiness is not None else Path(entry_path) if isinstance(entry_path, str) else None

    readiness: dict[str, Any] | None = None
    if entry is not None and readiness_path is not None:
        readiness_sha256 = validate_referenced_sha(entry, readiness_path, blockers)
        readiness = read_json(readiness_path, blockers, "readiness")
    if readiness is not None:
        validate_readiness(readiness, blockers)
        scan_for_forbidden_true_ready(readiness, blockers, "$.readiness")
    if manifest is not None:
        scan_for_forbidden_true_ready(manifest, blockers, "$.manifest")

    report = build_report(blockers, readiness_path=readiness_path, readiness_sha256=readiness_sha256)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
