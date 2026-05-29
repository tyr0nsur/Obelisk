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

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
) -> dict[str, Any]:
    blockers: list[str] = []
    identity_hashes: set[str] = set()
    invalid_reconciliation_schema_count = 0

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
        collect_identity_hashes(report, identity_hashes)
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
        collect_identity_hashes(static_global_evidence, identity_hashes)
        static_gobjects_candidate_count = count_static_gobjects_candidates(static_global_evidence)
        coherent_window_proven = static_coherent_window_proven(static_global_evidence)
        if not static_schema_valid:
            blockers.append("invalid_static_global_evidence_schema")
    if not coherent_window_proven:
        blockers.append(BLOCKER_MISSING_COHERENT_WINDOW)

    blockers.append(BLOCKER_UOBJECT_FLAGS)
    blockers = sorted(set(blockers))

    evidence_without_lifetime_flags_ready = (
        bool(reconciliation_reports)
        and invalid_reconciliation_schema_count == 0
        and totals["accepted_sample_count"] > 0
        and totals["serial_candidate_nonzero_count"] > 0
        and totals["serial_candidate_zero_count"] == 0
        and totals["serial_candidate_missing_count"] == 0
        and coherent_window_proven
    )

    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "report_counts": {
            "reconciliation": len(reconciliation_reports),
            "static_global_evidence": static_report_count,
            "invalid_reconciliation_schema": invalid_reconciliation_schema_count,
            "static_global_evidence_schema_valid": static_schema_valid,
        },
        "artifact_identity": {
            "hash_count": len(identity_hashes),
            "hashes": sorted(identity_hashes),
        },
        "reconciliation_summary": totals,
        "static_global_evidence_summary": {
            "gobjects_candidate_count": static_gobjects_candidate_count,
            "coherent_field_window_proven": coherent_window_proven,
        },
        "evidence_checks": {
            "accepted_reconciliation_samples_present": totals["accepted_sample_count"] > 0,
            "nonzero_serial_candidates_present": totals["serial_candidate_nonzero_count"] > 0,
            "zero_or_missing_serial_candidates_present": (
                totals["serial_candidate_zero_count"] > 0 or totals["serial_candidate_missing_count"] > 0
            ),
            "gobjects_coherent_field_window_proven": coherent_window_proven,
            "uobject_flags_validity_semantics_proven": False,
            "evidence_without_lifetime_flags_ready": evidence_without_lifetime_flags_ready,
        },
        "blockers": blockers,
        "post_callback_resource_handle_ready": False,
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
    evaluation = build_evaluation(reconciliation_reports, static_report)
    text = json.dumps(evaluation, indent=2, sort_keys=True)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
