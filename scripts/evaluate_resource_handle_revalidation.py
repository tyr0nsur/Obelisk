#!/usr/bin/env python3
"""Evaluate offline ResourceHandle revalidation readiness from redacted reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import reject_protected_input_path, reject_protected_output_path  # noqa: E402


SCHEMA = "obelisk.resource-handle-revalidation-evaluator.v1"
GOBJECTS_RECONCILIATION_SCHEMA = "obelisk.gobjects-sample-reconciliation.v1"
STATIC_GLOBAL_EVIDENCE_SCHEMA = "obelisk.static-global-promotion-evidence.v1"

STATUS_CANDIDATE_UOBJECT = "candidate-uobject"
BLOCKER_ZERO_OR_MISSING_SERIAL = "zero_or_missing_fuobjectitem_serial_candidates"
BLOCKER_UOBJECT_FLAGS = "uobject_flags_validity_semantics_unproven"
BLOCKER_MISSING_COHERENT_WINDOW = "missing_gobjects_coherent_field_window"
BLOCKER_MISSING_ARTIFACT_IDENTITY = "missing_or_partial_artifact_identity"
BLOCKER_INVALID_ARTIFACT_IDENTITY = "invalid_artifact_identity"
RESOURCE_HANDLE_NON_CLAIMS = (
    "does_not_unlock_resource_handle",
    "does_not_promote_gobjects_lookup",
    "does_not_promote_public_object_identity",
    "does_not_claim_post_callback_lookup",
    "does_not_name_ue_lifecycle_flags_publicly",
    "does_not_allow_mutation_or_return_override",
    "does_not_replace_rejected_runtime_object_samples",
)
RESOURCE_HANDLE_LIFETIME_BLOCKERS = (
    "no_public_resource_handle_contract",
    "public_resourcehandle_policy_missing",
    "no_post_callback_lifetime_contract",
    "post_callback_lifetime_policy_unproven",
    "no_serial_reuse_or_wraparound_policy",
    "no_version_matched_source_decompiler_correlation_for_public_lifecycle_names",
    "no_rejected_runtime_object_samples",
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} does not exist: {path}") from exc
    except OSError as exc:
        raise SystemExit(f"{label} is unreadable: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object: {path}")
    return payload


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def collect_identity_hashes(value: object, hashes: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in {"sha256", "artifact_sha256"} and is_sha256(child):
                hashes.add(str(child))
            elif isinstance(child, (dict, list)):
                collect_identity_hashes(child, hashes)
    elif isinstance(value, list):
        for child in value:
            collect_identity_hashes(child, hashes)


def identity_hashes(value: object) -> set[str]:
    hashes: set[str] = set()
    collect_identity_hashes(value, hashes)
    return hashes


def safe_artifact_id(value: object) -> bool:
    return isinstance(value, str) and SAFE_ARTIFACT_ID_RE.fullmatch(value) is not None and ".." not in value


def classify_artifact_identity(report: dict[str, Any]) -> tuple[str, set[str]]:
    identity = report.get("artifact_identity")
    if not isinstance(identity, dict):
        return "missing", set()

    artifact_kind = identity.get("artifact_kind")
    artifact_sha256 = identity.get("artifact_sha256")
    capture_id = identity.get("capture_id")
    evidence_pack_id = identity.get("evidence_pack_id")
    if any(value is None for value in (artifact_kind, artifact_sha256, capture_id, evidence_pack_id)):
        return "partial", set()
    if (
        not safe_artifact_id(artifact_kind)
        or not is_sha256(artifact_sha256)
        or not safe_artifact_id(capture_id)
        or not safe_artifact_id(evidence_pack_id)
    ):
        return "invalid", set()
    return "complete", {str(artifact_sha256)}


def int_value(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def reconciliation_counts(report: dict[str, Any]) -> dict[str, int]:
    samples = report.get("samples")
    if not isinstance(samples, list):
        samples = []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    sample_count = int_value(summary.get("sample_count")) if summary else None
    accepted_count = int_value(summary.get("accepted_count")) if summary else None
    rejected_count = int_value(summary.get("rejected_count")) if summary else None
    membership_pass_count = int_value(summary.get("membership_pass_count")) if summary else None

    if sample_count is None:
        sample_count = len(samples)

    accepted_samples = [sample for sample in samples if isinstance(sample, dict) and sample.get("status") == STATUS_CANDIDATE_UOBJECT]
    if accepted_count is None:
        accepted_count = len(accepted_samples)
    if rejected_count is None:
        rejected_count = max(0, sample_count - accepted_count)
    if membership_pass_count is None:
        membership_pass_count = sum(
            1
            for sample in samples
            if isinstance(sample, dict)
            and isinstance(sample.get("membership"), dict)
            and sample["membership"].get("passes") is True
        )

    serial_zero_count = 0
    serial_nonzero_count = 0
    serial_missing_count = 0
    for sample in accepted_samples:
        value = sample.get("item_dword_0x8")
        if isinstance(value, int) and not isinstance(value, bool):
            if value == 0:
                serial_zero_count += 1
            else:
                serial_nonzero_count += 1
        else:
            serial_missing_count += 1

    return {
        "sample_count": sample_count,
        "accepted_sample_count": accepted_count,
        "rejected_sample_count": rejected_count,
        "membership_pass_count": membership_pass_count,
        "serial_candidate_zero_count": serial_zero_count,
        "serial_candidate_nonzero_count": serial_nonzero_count,
        "serial_candidate_missing_count": serial_missing_count,
    }


def static_coherent_window_proven(report: dict[str, Any]) -> bool:
    candidates = report.get("candidates")
    if not isinstance(candidates, list):
        return False
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("kind") != "gobjects":
            continue
        contract = candidate.get("static_contract")
        if not isinstance(contract, dict):
            continue
        blockers = contract.get("blockers")
        if contract.get("satisfied") is True and blockers in (None, []):
            return True
        if contract.get("coherent_window") is not None and (
            not isinstance(blockers, list) or BLOCKER_MISSING_COHERENT_WINDOW not in blockers
        ):
            return True
    return False


def count_static_gobjects_candidates(report: dict[str, Any]) -> int:
    candidates = report.get("candidates")
    if not isinstance(candidates, list):
        return 0
    return sum(1 for candidate in candidates if isinstance(candidate, dict) and candidate.get("kind") == "gobjects")


def build_evaluation(
    reconciliation_reports: list[dict[str, Any]],
    static_global_evidence: dict[str, Any] | None,
    *,
    require_artifact_identity: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    collected_identity_hashes: set[str] = set()
    invalid_reconciliation_schema_count = 0
    complete_artifact_identity_report_count = 0
    missing_or_partial_artifact_identity_report_count = 0
    invalid_artifact_identity_report_count = 0

    totals = {
        "sample_count": 0,
        "accepted_sample_count": 0,
        "rejected_sample_count": 0,
        "membership_pass_count": 0,
        "serial_candidate_zero_count": 0,
        "serial_candidate_nonzero_count": 0,
        "serial_candidate_missing_count": 0,
    }
    for report in reconciliation_reports:
        report_hashes = identity_hashes(report)
        collected_identity_hashes.update(report_hashes)
        identity_status, strict_hashes = classify_artifact_identity(report)
        collected_identity_hashes.update(strict_hashes)
        if identity_status == "complete":
            complete_artifact_identity_report_count += 1
        elif identity_status == "invalid":
            invalid_artifact_identity_report_count += 1
        else:
            missing_or_partial_artifact_identity_report_count += 1
        if report.get("schema") != GOBJECTS_RECONCILIATION_SCHEMA:
            invalid_reconciliation_schema_count += 1
        counts = reconciliation_counts(report)
        for key, value in counts.items():
            totals[key] += value

    if not reconciliation_reports:
        blockers.append("missing_reconciliation_reports")
    if invalid_reconciliation_schema_count:
        blockers.append("invalid_reconciliation_report_schema")
    if totals["accepted_sample_count"] <= 0:
        blockers.append("missing_accepted_reconciliation_samples")
    if (
        totals["serial_candidate_nonzero_count"] <= 0
        or totals["serial_candidate_zero_count"] > 0
        or totals["serial_candidate_missing_count"] > 0
    ):
        blockers.append(BLOCKER_ZERO_OR_MISSING_SERIAL)

    static_report_count = 1 if static_global_evidence is not None else 0
    static_schema_valid = static_global_evidence is not None and static_global_evidence.get("schema") == STATIC_GLOBAL_EVIDENCE_SCHEMA
    coherent_window_proven = False
    static_gobjects_candidate_count = 0
    if static_global_evidence is not None:
        static_hashes = identity_hashes(static_global_evidence)
        collected_identity_hashes.update(static_hashes)
        identity_status, strict_hashes = classify_artifact_identity(static_global_evidence)
        collected_identity_hashes.update(strict_hashes)
        if identity_status == "complete":
            complete_artifact_identity_report_count += 1
        elif identity_status == "invalid":
            invalid_artifact_identity_report_count += 1
        else:
            missing_or_partial_artifact_identity_report_count += 1
        static_gobjects_candidate_count = count_static_gobjects_candidates(static_global_evidence)
        coherent_window_proven = static_coherent_window_proven(static_global_evidence)
        if not static_schema_valid:
            blockers.append("invalid_static_global_evidence_schema")
    if not coherent_window_proven:
        blockers.append(BLOCKER_MISSING_COHERENT_WINDOW)

    blockers.append(BLOCKER_UOBJECT_FLAGS)
    if require_artifact_identity and missing_or_partial_artifact_identity_report_count:
        blockers.append(BLOCKER_MISSING_ARTIFACT_IDENTITY)
    if require_artifact_identity and invalid_artifact_identity_report_count:
        blockers.append(BLOCKER_INVALID_ARTIFACT_IDENTITY)
    blockers.extend(RESOURCE_HANDLE_LIFETIME_BLOCKERS)
    blockers = sorted(set(blockers))

    required_artifact_identity_present = (
        not require_artifact_identity
        or (
            missing_or_partial_artifact_identity_report_count == 0
            and invalid_artifact_identity_report_count == 0
        )
    )

    evidence_without_lifetime_flags_ready = (
        bool(reconciliation_reports)
        and invalid_reconciliation_schema_count == 0
        and totals["accepted_sample_count"] > 0
        and totals["serial_candidate_nonzero_count"] > 0
        and totals["serial_candidate_zero_count"] == 0
        and totals["serial_candidate_missing_count"] == 0
        and coherent_window_proven
        and required_artifact_identity_present
    )

    artifact_identity: dict[str, Any] = {
        "hash_count": len(collected_identity_hashes),
        "hashes": sorted(collected_identity_hashes),
    }
    evidence_checks = {
        "accepted_reconciliation_samples_present": totals["accepted_sample_count"] > 0,
        "nonzero_serial_candidates_present": totals["serial_candidate_nonzero_count"] > 0,
        "zero_or_missing_serial_candidates_present": (
            totals["serial_candidate_zero_count"] > 0 or totals["serial_candidate_missing_count"] > 0
        ),
        "gobjects_coherent_field_window_proven": coherent_window_proven,
        "uobject_flags_validity_semantics_proven": False,
        "public_resource_handle_contract_present": False,
        "public_resourcehandle_policy_present": False,
        "post_callback_lifetime_contract_present": False,
        "post_callback_lifetime_policy_proven": False,
        "serial_reuse_or_wraparound_policy_present": False,
        "version_matched_source_decompiler_correlation_for_public_lifecycle_names_present": False,
        "rejected_runtime_object_samples_present": False,
        "evidence_without_lifetime_flags_ready": evidence_without_lifetime_flags_ready,
    }
    if require_artifact_identity:
        artifact_identity.update(
            {
                "required": True,
                "complete_input_count": complete_artifact_identity_report_count,
                "missing_or_partial_input_count": missing_or_partial_artifact_identity_report_count,
                "invalid_input_count": invalid_artifact_identity_report_count,
            }
        )
        evidence_checks["artifact_identity_present"] = bool(collected_identity_hashes)
        evidence_checks["required_artifact_identity_present"] = required_artifact_identity_present

    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "report_counts": {
            "reconciliation": len(reconciliation_reports),
            "static_global_evidence": static_report_count,
            "invalid_reconciliation_schema": invalid_reconciliation_schema_count,
            "static_global_evidence_schema_valid": static_schema_valid,
        },
        "artifact_identity": artifact_identity,
        "reconciliation_summary": totals,
        "static_global_evidence_summary": {
            "gobjects_candidate_count": static_gobjects_candidate_count,
            "coherent_field_window_proven": coherent_window_proven,
        },
        "evidence_checks": evidence_checks,
        "lifetime_blocker_summary": {
            "blockers": list(RESOURCE_HANDLE_LIFETIME_BLOCKERS),
            "public_contract_present": False,
            "post_callback_contract_present": False,
            "serial_reuse_or_wraparound_policy_present": False,
            "rejected_runtime_object_samples_present": False,
        },
        "non_claims": list(RESOURCE_HANDLE_NON_CLAIMS),
        "blockers": blockers,
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "uobject_flags_validity_semantics_proven": False,
        "promotion_gate": {
            "ready": False,
            "blockers": blockers,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reconciliation",
        action="append",
        type=Path,
        required=True,
        help="Offline gobjects reconciliation report JSON. May be repeated.",
    )
    parser.add_argument("--static-global-evidence", type=Path, help="Optional static global evidence JSON.")
    parser.add_argument("--output", type=Path, help="Optional redacted JSON output path.")
    parser.add_argument(
        "--require-artifact-identity",
        action="store_true",
        help=(
            "Add fail-closed blockers when any supplied report lacks complete sanitized "
            "artifact_identity metadata."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reconciliation_paths = [reject_protected_input_path(path, "--reconciliation") for path in args.reconciliation]
    static_path = (
        reject_protected_input_path(args.static_global_evidence, "--static-global-evidence")
        if args.static_global_evidence
        else None
    )
    output_path = reject_protected_output_path(args.output, "--output") if args.output else None

    reconciliation_reports = [
        load_json(path, "--reconciliation")
        for path in reconciliation_paths
    ]
    static_report = load_json(static_path, "--static-global-evidence") if static_path is not None else None
    evaluation = build_evaluation(
        reconciliation_reports,
        static_report,
        require_artifact_identity=args.require_artifact_identity,
    )
    text = json.dumps(evaluation, indent=2, sort_keys=True)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
