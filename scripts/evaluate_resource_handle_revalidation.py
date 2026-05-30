#!/usr/bin/env python3
"""Evaluate offline ResourceHandle revalidation readiness from redacted reports."""

from __future__ import annotations

import argparse
import copy
import hashlib
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
UOBJECT_FLAG_POLICY_REPORT_SCHEMA = "obelisk.uobject-flag-policy-report.v1"
INTERNAL_UOBJECT_REVALIDATION_CANDIDATE_SCHEMA = "obelisk.internal-uobject-revalidation-candidate.v1"

STATUS_CANDIDATE_UOBJECT = "candidate-uobject"
BLOCKER_ZERO_OR_MISSING_SERIAL = "zero_or_missing_fuobjectitem_serial_candidates"
BLOCKER_UOBJECT_FLAGS = "uobject_flags_validity_semantics_unproven"
BLOCKER_MISSING_COHERENT_WINDOW = "missing_gobjects_coherent_field_window"
BLOCKER_MISSING_ARTIFACT_IDENTITY = "missing_or_partial_artifact_identity"
BLOCKER_INVALID_ARTIFACT_IDENTITY = "invalid_artifact_identity"
BLOCKER_INVALID_UOBJECT_FLAG_POLICY_CANDIDATE = "invalid_uobject_flag_policy_candidate"
UOBJECT_FLAG_POLICY_REMAINING_BLOCKERS = (
    "static_only_evidence",
    "no_rejected_runtime_object_samples",
    "no_named_lifecycle_semantics",
    "public_resourcehandle_policy_missing",
    "post_callback_lifetime_policy_unproven",
)
UOBJECT_FLAG_POLICY_NON_CLAIMS = (
    "does_not_promote_resourcehandle",
    "does_not_promote_post_callback_lookup",
    "does_not_claim_mutation_or_return_override_safety",
    "does_not_assign_public_ue_lifecycle_flag_names",
    "does_not_prove_public_sdk_object_identity",
    "does_not_replace_rejected_runtime_object_samples",
)
INTERNAL_UOBJECT_REVALIDATION_CONTRACT = {
    "name": "InternalUObjectRevalidationCandidate",
    "lifetime": "frame_local_only",
    "post_callback_lookup": "rejected",
    "flag_policy": {
        "0x100": "reject",
        "0x4000": "reject_by_default",
    },
    "output": "copied_bool_or_obelisk_owned_data_only",
    "public_api": "not_promoted",
}
EXPECTED_UOBJECT_FLAG_POLICY_CANDIDATES = {
    "0x100": {
        "candidate": "hard_invalid_static_negative_equivalent",
        "support": {
            "weak_helper_flag_policy_candidate_null_always",
            "gc_static_0x100_support",
        },
    },
    "0x4000": {
        "candidate": "strict_invalid_static_negative_equivalent",
        "support": {
            "weak_helper_flag_policy_candidate_null_when_mode_zero",
            "strict_0x4000_behavior",
            "gobjects_backed_0x4000_skip",
        },
    },
}
EXPECTED_UOBJECT_FLAG_RULES = [
    {"mask": "0x100", "result": "null_always"},
    {"mask": "0x4000", "result": "null_when_sil_zero"},
]
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
SAFE_ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PLACEHOLDER_ARTIFACT_ID_PREFIXES = ("unspecified-", "static-global-default-")


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


def placeholder_artifact_id(value: object) -> bool:
    return isinstance(value, str) and value.casefold().startswith(PLACEHOLDER_ARTIFACT_ID_PREFIXES)


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def validate_artifact_identity_value(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not safe_artifact_id(value):
        raise SystemExit(f"{field_name} must be a safe artifact id")
    if placeholder_artifact_id(value):
        raise SystemExit(f"{field_name} must not use a placeholder artifact id")
    return value


def validate_output_artifact_identity_args(args: argparse.Namespace) -> dict[str, str] | None:
    artifact_kind = validate_artifact_identity_value(args.artifact_kind, "--artifact-kind")
    capture_id = validate_artifact_identity_value(args.capture_id, "--capture-id")
    evidence_pack_id = validate_artifact_identity_value(args.evidence_pack_id, "--evidence-pack-id")
    supplied = [value is not None for value in (artifact_kind, capture_id, evidence_pack_id)]
    if args.require_output_artifact_identity and not all(supplied):
        raise SystemExit(
            "--require-output-artifact-identity requires --artifact-kind, --capture-id, and --evidence-pack-id"
        )
    if any(supplied) and not all(supplied):
        raise SystemExit(
            "output artifact identity requires --artifact-kind, --capture-id, and --evidence-pack-id together"
        )
    if not all(supplied):
        return None
    assert artifact_kind is not None
    assert capture_id is not None
    assert evidence_pack_id is not None
    if artifact_kind != SCHEMA:
        raise SystemExit(f"--artifact-kind must be {SCHEMA}")
    return {
        "artifact_kind": artifact_kind,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
    }


def add_output_artifact_identity(evaluation: dict[str, Any], identity: dict[str, str]) -> dict[str, Any]:
    report = copy.deepcopy(evaluation)
    report.pop("output_artifact_identity", None)
    material = {
        "artifact_identity": identity,
        "report": report,
    }
    evaluation["output_artifact_identity"] = {
        **identity,
        "artifact_sha256": hashlib.sha256(canonical_json_bytes(material)).hexdigest(),
    }
    return evaluation


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
        or placeholder_artifact_id(artifact_kind)
        or placeholder_artifact_id(capture_id)
        or placeholder_artifact_id(evidence_pack_id)
    ):
        return "invalid", set()
    return "complete", {str(artifact_sha256)}


def artifact_identity_issue(identity_status: str) -> str | None:
    if identity_status in {"missing", "partial"}:
        return BLOCKER_MISSING_ARTIFACT_IDENTITY
    if identity_status == "invalid":
        return BLOCKER_INVALID_ARTIFACT_IDENTITY
    return None


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


def validate_policy_candidates(candidates: object) -> tuple[dict[str, str], list[str]]:
    issues: list[str] = []
    if not isinstance(candidates, list):
        return {}, ["missing_policy_candidates"]

    observed: dict[str, str] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            issues.append("policy_candidate_not_object")
            continue
        mask = candidate.get("mask")
        if not isinstance(mask, str):
            issues.append("policy_candidate_mask_invalid")
            continue
        expected = EXPECTED_UOBJECT_FLAG_POLICY_CANDIDATES.get(mask)
        if expected is None:
            issues.append("policy_candidate_mask_unexpected")
            continue
        observed[mask] = str(candidate.get("candidate"))
        if candidate.get("candidate") != expected["candidate"]:
            issues.append(f"policy_candidate_{mask}_kind_mismatch")
        support = candidate.get("support")
        if not isinstance(support, list) or set(support) != expected["support"]:
            issues.append(f"policy_candidate_{mask}_support_mismatch")
        if candidate.get("ue_lifecycle_name") != "not_promoted":
            issues.append(f"policy_candidate_{mask}_lifecycle_name_promoted")

    if set(observed) != set(EXPECTED_UOBJECT_FLAG_POLICY_CANDIDATES):
        issues.append("policy_candidate_masks_mismatch")
    return observed, issues


def build_internal_uobject_revalidation_candidate(report: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    source_hashes = identity_hashes(report)

    if report.get("schema") != UOBJECT_FLAG_POLICY_REPORT_SCHEMA:
        issues.append("uobject_flag_policy_schema_mismatch")
    if report.get("evidence_kind") != "static_negative_equivalent_candidate":
        issues.append("uobject_flag_policy_evidence_kind_mismatch")
    if report.get("status") != "candidate_blocked":
        issues.append("uobject_flag_policy_status_not_candidate_blocked")
    if report.get("promotion_ready") is not False:
        issues.append("uobject_flag_policy_promotion_ready_overclaim")
    if report.get("post_callback_resource_handle_ready") is not False:
        issues.append("uobject_flag_policy_post_callback_resourcehandle_overclaim")

    binary = report.get("binary")
    binary_sha256: str | None = None
    if not isinstance(binary, dict):
        issues.append("uobject_flag_policy_binary_missing")
    else:
        if binary.get("path_redacted") is not True:
            issues.append("uobject_flag_policy_binary_path_not_redacted")
        if is_sha256(binary.get("sha256")):
            binary_sha256 = str(binary["sha256"])
        else:
            issues.append("uobject_flag_policy_binary_sha256_invalid")

    redaction = report.get("redaction")
    if isinstance(redaction, dict):
        if redaction.get("paths") != "redacted":
            issues.append("uobject_flag_policy_paths_not_redacted")
        if redaction.get("addresses") != "redacted":
            issues.append("uobject_flag_policy_addresses_not_redacted")
        if redaction.get("raw_snippets") != "omitted":
            issues.append("uobject_flag_policy_raw_snippets_not_omitted")

    weak_helper = report.get("weak_helper_caller_mode")
    weak_helper_summary: dict[str, Any] = {
        "present": isinstance(weak_helper, dict),
        "direct_call_coverage_complete": False,
        "caller_rows_summary_present": False,
    }
    if not isinstance(weak_helper, dict):
        issues.append("uobject_flag_policy_weak_helper_missing")
    else:
        if weak_helper.get("promotion_gate_ready") is not False:
            issues.append("uobject_flag_policy_weak_helper_promotion_gate_overclaim")
        if weak_helper.get("flag_rules") != EXPECTED_UOBJECT_FLAG_RULES:
            issues.append("uobject_flag_policy_weak_helper_flag_rules_mismatch")
        coverage = weak_helper.get("direct_call_coverage")
        coverage_entry = coverage.get("weak_helper_flag_policy_candidate") if isinstance(coverage, dict) else None
        if isinstance(coverage_entry, dict):
            expected_calls = int_value(coverage_entry.get("expected"))
            observed_calls = int_value(coverage_entry.get("observed"))
            weak_helper_summary["direct_call_coverage"] = {
                "expected": expected_calls,
                "observed": observed_calls,
            }
            weak_helper_summary["direct_call_coverage_complete"] = (
                expected_calls == 6 and observed_calls == 6
            )
        if not weak_helper_summary["direct_call_coverage_complete"]:
            issues.append("uobject_flag_policy_direct_call_coverage_incomplete")

        caller_rows = weak_helper.get("caller_rows_summary")
        if isinstance(caller_rows, dict):
            weak_helper_summary["caller_rows_summary_present"] = True
            weak_helper_summary["caller_rows"] = {
                "row_count": int_value(caller_rows.get("row_count")),
                "unique_caller_hash_count": int_value(caller_rows.get("unique_caller_hash_count")),
                "source_count": int_value(caller_rows.get("source_count")),
                "claim_level": caller_rows.get("claim_level") if isinstance(caller_rows.get("claim_level"), str) else None,
                "lifecycle_names": caller_rows.get("lifecycle_names") if isinstance(caller_rows.get("lifecycle_names"), str) else None,
                "path_redacted": caller_rows.get("path_redacted") is True,
            }
            if caller_rows.get("claim_level") != "internal_static_caller_mode_candidate":
                issues.append("uobject_flag_policy_caller_rows_claim_level_mismatch")
            if caller_rows.get("lifecycle_names") != "not_promoted":
                issues.append("uobject_flag_policy_caller_rows_lifecycle_names_promoted")
            if caller_rows.get("path_redacted") is not True:
                issues.append("uobject_flag_policy_caller_rows_path_not_redacted")

    observed_candidates, candidate_issues = validate_policy_candidates(report.get("policy_candidates"))
    issues.extend(candidate_issues)

    windows = report.get("windows_summary")
    windows_summary = {
        "present": isinstance(windows, dict),
        "required_count": 0,
        "observed_count": 0,
        "all_required_present": False,
        "all_required_patterns_present": False,
    }
    if not isinstance(windows, dict):
        issues.append("uobject_flag_policy_windows_summary_missing")
    else:
        required = windows.get("required")
        observed = windows.get("observed")
        windows_summary = {
            "present": True,
            "required_count": len(required) if isinstance(required, list) else 0,
            "observed_count": len(observed) if isinstance(observed, list) else 0,
            "all_required_present": windows.get("all_required_present") is True,
            "all_required_patterns_present": windows.get("all_required_patterns_present") is True,
        }
        if not windows_summary["all_required_present"]:
            issues.append("uobject_flag_policy_required_windows_not_present")
        if not windows_summary["all_required_patterns_present"]:
            issues.append("uobject_flag_policy_required_patterns_not_present")
        if isinstance(observed, list) and any(
            not isinstance(window, dict) or window.get("path_redacted") is not True
            for window in observed
        ):
            issues.append("uobject_flag_policy_window_path_not_redacted")

    embedded_contract = report.get("internal_revalidation_contract")
    contract_source = "derived_from_policy_candidates"
    if isinstance(embedded_contract, dict):
        contract_source = "embedded"
        if embedded_contract != INTERNAL_UOBJECT_REVALIDATION_CONTRACT:
            issues.append("internal_uobject_revalidation_contract_mismatch")

    remaining_blockers = report.get("remaining_blockers")
    if not isinstance(remaining_blockers, list) or not set(UOBJECT_FLAG_POLICY_REMAINING_BLOCKERS).issubset(set(remaining_blockers)):
        issues.append("uobject_flag_policy_remaining_blockers_missing")
    non_claims = report.get("non_claims")
    if not isinstance(non_claims, list) or not set(UOBJECT_FLAG_POLICY_NON_CLAIMS).issubset(set(non_claims)):
        issues.append("uobject_flag_policy_non_claims_missing")

    accepted = not issues
    return (
        {
            "schema": INTERNAL_UOBJECT_REVALIDATION_CANDIDATE_SCHEMA,
            "accepted": accepted,
            "candidate_level": "internal_static_candidate",
            "contract_source": contract_source,
            "source_schema": report.get("schema") if isinstance(report.get("schema"), str) else None,
            "source_status": report.get("status") if isinstance(report.get("status"), str) else None,
            "source_candidate_blocked": report.get("status") == "candidate_blocked",
            "source_promotion_ready": False,
            "source_post_callback_resource_handle_ready": False,
            "binary_sha256": binary_sha256,
            "source_artifact_hashes": sorted(source_hashes),
            "policy_candidate_masks": sorted(observed_candidates),
            "candidate": INTERNAL_UOBJECT_REVALIDATION_CONTRACT,
            "evidence_summary": {
                "policy_candidate_count": len(observed_candidates),
                "weak_helper_caller_mode": weak_helper_summary,
                "windows": windows_summary,
            },
            "non_claims": list(UOBJECT_FLAG_POLICY_NON_CLAIMS),
            "remaining_blockers": list(UOBJECT_FLAG_POLICY_REMAINING_BLOCKERS),
            "issues": sorted(set(issues)),
        },
        sorted(set(issues)),
    )


def build_evaluation(
    reconciliation_reports: list[dict[str, Any]],
    static_global_evidence: dict[str, Any] | None,
    *,
    require_artifact_identity: bool = False,
    uobject_flag_policy: dict[str, Any] | None = None,
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

    internal_uobject_revalidation_candidate: dict[str, Any] | None = None
    uobject_flag_policy_report_count = 1 if uobject_flag_policy is not None else 0
    if uobject_flag_policy is not None:
        policy_hashes = identity_hashes(uobject_flag_policy)
        collected_identity_hashes.update(policy_hashes)
        identity_status, strict_hashes = classify_artifact_identity(uobject_flag_policy)
        collected_identity_hashes.update(strict_hashes)
        if identity_status == "complete":
            complete_artifact_identity_report_count += 1
        elif identity_status == "invalid":
            invalid_artifact_identity_report_count += 1
        else:
            missing_or_partial_artifact_identity_report_count += 1
        internal_uobject_revalidation_candidate, policy_issues = build_internal_uobject_revalidation_candidate(
            uobject_flag_policy
        )
        if require_artifact_identity:
            identity_issue = artifact_identity_issue(identity_status)
            if identity_issue is not None:
                internal_uobject_revalidation_candidate["accepted"] = False
                internal_uobject_revalidation_candidate["issues"] = sorted(
                    set(internal_uobject_revalidation_candidate["issues"]) | {identity_issue}
                )
        if policy_issues:
            blockers.append(BLOCKER_INVALID_UOBJECT_FLAG_POLICY_CANDIDATE)

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
        "internal_uobject_revalidation_candidate_present": (
            internal_uobject_revalidation_candidate is not None
            and internal_uobject_revalidation_candidate["accepted"] is True
        ),
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

    evaluation = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "report_counts": {
            "reconciliation": len(reconciliation_reports),
            "static_global_evidence": static_report_count,
            "uobject_flag_policy": uobject_flag_policy_report_count,
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
    if internal_uobject_revalidation_candidate is not None:
        evaluation["internal_uobject_revalidation_candidate"] = internal_uobject_revalidation_candidate
    return evaluation


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
    parser.add_argument(
        "--uobject-flag-policy",
        type=Path,
        help="Optional redacted UObject flag-policy candidate report JSON.",
    )
    parser.add_argument("--output", type=Path, help="Optional redacted JSON output path.")
    parser.add_argument(
        "--require-artifact-identity",
        action="store_true",
        help=(
            "Add fail-closed blockers when any supplied report lacks complete sanitized "
            "artifact_identity metadata."
        ),
    )
    parser.add_argument(
        "--artifact-kind",
        help="Safe kind for the output artifact identity. Must be supplied with --capture-id and --evidence-pack-id.",
    )
    parser.add_argument(
        "--capture-id",
        help="Safe capture id for the output artifact identity. Must be supplied with --artifact-kind and --evidence-pack-id.",
    )
    parser.add_argument(
        "--evidence-pack-id",
        help="Safe evidence pack id for the output artifact identity. Must be supplied with --artifact-kind and --capture-id.",
    )
    parser.add_argument(
        "--require-output-artifact-identity",
        action="store_true",
        help="Require the emitted evaluator report to include a complete output_artifact_identity block.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_identity_args = validate_output_artifact_identity_args(args)
    reconciliation_paths = [reject_protected_input_path(path, "--reconciliation") for path in args.reconciliation]
    static_path = (
        reject_protected_input_path(args.static_global_evidence, "--static-global-evidence")
        if args.static_global_evidence
        else None
    )
    uobject_flag_policy_path = (
        reject_protected_input_path(args.uobject_flag_policy, "--uobject-flag-policy")
        if args.uobject_flag_policy
        else None
    )
    output_path = reject_protected_output_path(args.output, "--output") if args.output else None

    reconciliation_reports = [
        load_json(path, "--reconciliation")
        for path in reconciliation_paths
    ]
    static_report = load_json(static_path, "--static-global-evidence") if static_path is not None else None
    uobject_flag_policy_report = (
        load_json(uobject_flag_policy_path, "--uobject-flag-policy")
        if uobject_flag_policy_path is not None
        else None
    )
    evaluation = build_evaluation(
        reconciliation_reports,
        static_report,
        require_artifact_identity=args.require_artifact_identity,
        uobject_flag_policy=uobject_flag_policy_report,
    )
    if output_identity_args is not None:
        add_output_artifact_identity(evaluation, output_identity_args)
    text = json.dumps(evaluation, indent=2, sort_keys=True)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
