#!/usr/bin/env python3
"""Build a reviewed player-identity public-contract decision record offline.

The generated record is a post-runtime-evidence contract-review input only. It does not
promote public headers, ABI, runtime readiness, SDK readiness, P0 progress, or v1
completion.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_runtime_checker
import check_player_identity_public_contract_decision_record as decision_checker
import protected_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_player_identity_public_contract_decision_record.py"
STRICT_APPROVED_RUNTIME_CHECKER = REPO_ROOT / decision_checker.STRICT_APPROVED_RUNTIME_CHECKER
REPORT_SCHEMA = "obelisk.player-identity-public-contract-decision-record-build-report.v1"
NON_CLAIM = (
    "offline reviewed decision-record build only; does not authorize live operations, "
    "runtime capture, public header/API/ABI, runtime readiness, public SDK readiness, "
    "P0 progress, stable SDK claims, Plugin Hub, publication, or v1 completion"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--approved-runtime-evidence",
        type=Path,
        required=True,
        help="Accepted approved runtime lifecycle evidence manifest JSON.",
    )
    parser.add_argument(
        "--strict-approved-runtime-check-report",
        type=Path,
        required=True,
        help="Strict consume-mode checker report JSON that accepted the runtime evidence.",
    )
    parser.add_argument(
        "--base-record",
        type=Path,
        default=REPO_ROOT / decision_checker.DEFAULT_RECORD,
        help="Base reviewed decision record template.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output decision-record JSON path.")
    parser.add_argument("--json", action="store_true", help="Emit a build report JSON.")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_input_file(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    resolved = protected_paths.reject_protected_input_path(path, label)
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def safe_output_file(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    parent = path.expanduser().parent
    protected_paths.reject_symlink_component(parent, f"{label} parent")
    resolved_parent = protected_paths.reject_protected_output_path(parent, f"{label} parent")
    resolved_parent.mkdir(parents=True, exist_ok=True)
    resolved = protected_paths.reject_protected_output_path(path, label)
    return resolved


def load_json_file(path: Path, label: str) -> dict[str, Any]:
    resolved = safe_input_file(path, label)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object: {resolved}")
    return payload


def source_artifacts() -> dict[str, dict[str, str]]:
    artifacts: dict[str, dict[str, str]] = {}
    for label, spec in decision_checker.EXPECTED_SOURCE_ARTIFACTS.items():
        path = REPO_ROOT / spec["path"]
        resolved = safe_input_file(path, f"source_artifacts.{label}")
        artifacts[label] = {
            "path": spec["path"],
            "sha256": sha256_file(resolved),
            "role": spec["role"],
            "counting_scope": decision_checker.REVIEW_ROUTE,
        }
    return artifacts


def strict_check_report_ref(path: Path) -> dict[str, str]:
    return {
        "schema": decision_checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_REF_SCHEMA,
        "checker": decision_checker.STRICT_APPROVED_RUNTIME_CHECKER,
        "path": str(path),
        "sha256": sha256_file(path),
        "mode": "consume",
        "required_report_schema": decision_checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        "non_claim": decision_checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_NON_CLAIM,
    }


def approved_runtime_evidence_manifest_ref(path: Path) -> dict[str, str]:
    return decision_checker.approved_runtime_evidence_manifest_ref(path)


def blocker_summary(blockers: list[dict[str, Any]]) -> str:
    return ", ".join(
        f"{blocker['reason']}:{blocker['label']}" for blocker in blockers[:8]
    )


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def first_report_mismatches(
    *,
    expected: Any,
    observed: Any,
    label: str = "$",
    limit: int = 8,
) -> list[str]:
    if limit <= 0:
        return []
    if isinstance(expected, dict) and isinstance(observed, dict):
        mismatches: list[str] = []
        expected_keys = set(expected)
        observed_keys = set(observed)
        for key in sorted(expected_keys - observed_keys):
            mismatches.append(f"{label}.{key}:missing")
            if len(mismatches) >= limit:
                return mismatches
        for key in sorted(observed_keys - expected_keys):
            mismatches.append(f"{label}.{key}:unexpected")
            if len(mismatches) >= limit:
                return mismatches
        for key in sorted(expected_keys & observed_keys):
            mismatches.extend(
                first_report_mismatches(
                    expected=expected[key],
                    observed=observed[key],
                    label=f"{label}.{key}",
                    limit=limit - len(mismatches),
                )
            )
            if len(mismatches) >= limit:
                return mismatches
        return mismatches
    if isinstance(expected, list) and isinstance(observed, list):
        mismatches = []
        if len(expected) != len(observed):
            mismatches.append(f"{label}:length expected={len(expected)} observed={len(observed)}")
            if len(mismatches) >= limit:
                return mismatches
        for index, (expected_item, observed_item) in enumerate(zip(expected, observed)):
            mismatches.extend(
                first_report_mismatches(
                    expected=expected_item,
                    observed=observed_item,
                    label=f"{label}[{index}]",
                    limit=limit - len(mismatches),
                )
            )
            if len(mismatches) >= limit:
                return mismatches
        return mismatches
    if expected != observed:
        return [f"{label}:value_mismatch"]
    return []


def strict_report_from_manifest(
    *,
    approved_runtime_evidence: dict[str, Any],
    approved_runtime_path: Path,
) -> dict[str, Any]:
    validation = approved_runtime_checker.validate_manifest(
        approved_runtime_evidence,
        check_mode="consume",
        input_path=approved_runtime_path,
    )
    report = approved_runtime_checker.build_report(
        approved_runtime_evidence,
        validation,
        check_mode="consume",
    )
    if validation.blockers:
        raise SystemExit(
            "--approved-runtime-evidence failed strict approved-runtime checker: "
            f"{blocker_summary(validation.blockers)}"
        )
    blockers: list[dict[str, Any]] = []
    decision_checker.validate_strict_check_report_payload(report, blockers)
    if blockers:
        raise SystemExit(
            "generated strict approved-runtime checker report failed public-contract "
            f"compatibility: {blocker_summary(blockers)}"
        )
    return report


def validate_strict_report_bound_to_manifest(
    *,
    supplied_report: dict[str, Any],
    approved_runtime_evidence: dict[str, Any],
    approved_runtime_path: Path,
) -> None:
    blockers: list[dict[str, Any]] = []
    decision_checker.validate_strict_check_report_payload(supplied_report, blockers)
    if blockers:
        raise SystemExit(
            "--strict-approved-runtime-check-report failed strict report contract: "
            f"{blocker_summary(blockers)}"
        )
    expected_report = strict_report_from_manifest(
        approved_runtime_evidence=approved_runtime_evidence,
        approved_runtime_path=approved_runtime_path,
    )
    if canonical_json(supplied_report) != canonical_json(expected_report):
        mismatches = first_report_mismatches(
            expected=expected_report,
            observed=supplied_report,
        )
        raise SystemExit(
            "strict_approved_runtime_checker_contract_report_runtime_input_mismatch: "
            "supplied strict report is not the consume-mode report for "
            f"{approved_runtime_path}; mismatches={mismatches}"
        )


def build_record(
    *,
    base_record: dict[str, Any],
    approved_runtime_evidence: dict[str, Any],
    approved_runtime_path: Path,
    strict_report_path: Path,
) -> dict[str, Any]:
    record = copy.deepcopy(base_record)
    record["schema"] = decision_checker.SCHEMA
    record["artifact_id"] = decision_checker.ARTIFACT_ID
    record["surface"] = decision_checker.SURFACE
    record["active_after_resolved_input"] = decision_checker.ACTIVE_AFTER_RESOLVED_INPUT
    record["route"] = copy.deepcopy(decision_checker.REQUIRED_ROUTE)
    record["post_runtime_identity_contract_gate"] = copy.deepcopy(
        decision_checker.REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_GATE
    )
    record["post_runtime_identity_contract_next_step"] = copy.deepcopy(
        decision_checker.REQUIRED_NEXT_STEP_CHECK
    )
    record["runtime_evidence_contract_review_currentness"] = copy.deepcopy(
        decision_checker.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC
    )
    record["review_status"] = "reviewed"
    record["accepted_for_contract_review"] = True
    record["source_artifact_hash_policy"] = decision_checker.SOURCE_ARTIFACT_HASH_POLICY
    record["source_artifacts"] = source_artifacts()
    record[decision_checker.APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD] = (
        decision_checker.approved_runtime_evidence_binding_from_manifest(approved_runtime_evidence)
    )
    record[decision_checker.APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD] = (
        approved_runtime_evidence_manifest_ref(approved_runtime_path)
    )
    record[decision_checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD] = strict_check_report_ref(
        strict_report_path
    )
    return record


def validate_generated_record(record: dict[str, Any]) -> dict[str, Any]:
    blockers = decision_checker.validate_record(record, check_mode="consume")
    report = decision_checker.build_report(record, blockers, check_mode="consume")
    if blockers:
        reasons = ", ".join(
            f"{blocker['reason']}:{blocker['label']}" for blocker in blockers[:8]
        )
        raise SystemExit(f"generated decision record failed validation: {reasons}")
    return report


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    approved_runtime_path = safe_input_file(
        args.approved_runtime_evidence,
        "--approved-runtime-evidence",
    )
    strict_report_path = safe_input_file(
        args.strict_approved_runtime_check_report,
        "--strict-approved-runtime-check-report",
    )
    output = safe_output_file(args.output, "--output")
    base_record = load_json_file(args.base_record, "--base-record")
    approved_runtime_evidence = load_json_file(approved_runtime_path, "--approved-runtime-evidence")
    if approved_runtime_evidence.get("schema") != decision_checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND:
        raise SystemExit(
            "--approved-runtime-evidence schema mismatch: "
            f"expected {decision_checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND}, "
            f"got {approved_runtime_evidence.get('schema')}"
        )
    supplied_strict_report = load_json_file(
        strict_report_path,
        "--strict-approved-runtime-check-report",
    )
    validate_strict_report_bound_to_manifest(
        supplied_report=supplied_strict_report,
        approved_runtime_evidence=approved_runtime_evidence,
        approved_runtime_path=approved_runtime_path,
    )
    record = build_record(
        base_record=base_record,
        approved_runtime_evidence=approved_runtime_evidence,
        approved_runtime_path=approved_runtime_path,
        strict_report_path=strict_report_path,
    )
    validation_report = validate_generated_record(record)
    write_json(output, record)
    build_report = {
        "schema": REPORT_SCHEMA,
        "status": "built",
        "record_path": str(output),
        "record_sha256": sha256_file(output),
        "checker": str(CHECKER.relative_to(REPO_ROOT)),
        "strict_approved_runtime_checker": str(STRICT_APPROVED_RUNTIME_CHECKER.relative_to(REPO_ROOT)),
        "strict_approved_runtime_check_report_bound_to_input": True,
        "checker_report": validation_report,
        "accepted_for_contract_review": validation_report.get("accepted_for_contract_review") is True,
        "record_valid_scope": validation_report.get("record_valid_scope"),
        "ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_sdk_ready": False,
        "sdk_progress": 0,
        "p0_progress": 0,
        "non_claim": NON_CLAIM,
    }
    if args.json:
        print(json.dumps(build_report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
