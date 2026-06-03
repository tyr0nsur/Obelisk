#!/usr/bin/env python3
"""Build a candidate-only serial reuse/wraparound policy artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from artifact_identity import canonical_json_bytes, complete_artifact_identity, is_safe_artifact_id  # noqa: E402
from evaluate_resource_handle_revalidation import (  # noqa: E402
    INTERNAL_UOBJECT_REVALIDATION_CANDIDATE_SCHEMA,
    INTERNAL_UOBJECT_REVALIDATION_CONTRACT,
    RESOURCE_HANDLE_LIFETIME_BLOCKERS,
    RESOURCE_HANDLE_NON_CLAIMS,
    SCHEMA as RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
)
from snapshot_evidence_pack import reject_protected_input_path, reject_protected_output_path  # noqa: E402


SCHEMA = "obelisk.internal-uobject-revalidation-serial-policy.v1"
STATUS = "accepted_internal_candidate_policy"
REMAINING_BLOCKERS = tuple(
    blocker
    for blocker in RESOURCE_HANDLE_LIFETIME_BLOCKERS
    if blocker != "no_serial_reuse_or_wraparound_policy"
) + (
    "candidate_only_serial_reuse_wraparound_policy",
    "serial_reuse_wraparound_runtime_semantics_unproven",
    "uobject_flags_validity_semantics_unproven",
)
NON_CLAIMS = tuple(RESOURCE_HANDLE_NON_CLAIMS) + (
    "does_not_promote_persistent_handles",
    "does_not_claim_serial_reuse_or_wraparound_safety",
    "does_not_claim_slot_reuse_safety_without_fresh_serial",
)
FORBIDDEN_SOURCE_CLAIM_KEYS = frozenset(
    (
        "promotion_ready",
        "public_abi_ready",
        "public_sdk_ready",
        "release_ready",
        "runtime_ready",
        "v1_sdk_ready",
        "object_identity_ready",
        "post_callback_resource_handle_ready",
        "public_object_identity_ready",
        "public_object_lookup_ready",
        "public_resource_handle_ready",
        "resource_handle_ready",
        "serial_reuse_or_wraparound_safety_proven",
    )
)
FORBIDDEN_SOURCE_ALIAS_SUBJECT_RE = re.compile(
    r"(?:resource_?handle|resourcehandle|object_?identity|object_?lookup|object_?handle|serial_?reuse|wraparound)",
    re.IGNORECASE,
)
FORBIDDEN_SOURCE_ALIAS_CONTEXT_RE = re.compile(
    r"(?:public|runtime|v1|sdk|abi|release|promot|ready|readiness|enabled|allowed|available|post_?callback|safety)",
    re.IGNORECASE,
)


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


def validate_safe_identity_args(args: argparse.Namespace) -> None:
    for field_name in ("capture_id", "evidence_pack_id"):
        value = getattr(args, field_name)
        if not is_safe_artifact_id(value):
            raise SystemExit(f"--{field_name.replace('_', '-')} must be a safe artifact id")


def source_output_identity(source: dict[str, Any]) -> dict[str, str]:
    identity, errors = complete_artifact_identity(
        source,
        container_key="output_artifact_identity",
        expected_artifact_kind=RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
    )
    if errors or identity is None:
        raise SystemExit("source evaluator output_artifact_identity is incomplete or invalid: " + ",".join(errors))
    return identity


def required_int(mapping: dict[str, Any], key: str, label: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise SystemExit(f"{label}.{key} must be an integer")
    return value


def positive_claim(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.casefold() in {"allowed", "available", "enabled", "live", "promoted", "ready", "true", "yes"}
    return False


def normalized_claim_key(key: str) -> str:
    key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return re.sub(r"[^a-zA-Z0-9]+", "_", key).strip("_").casefold()


def forbidden_positive_source_alias_key(key: str) -> bool:
    normalized = normalized_claim_key(key)
    return bool(
        normalized in FORBIDDEN_SOURCE_CLAIM_KEYS
        or (
            FORBIDDEN_SOURCE_ALIAS_SUBJECT_RE.search(normalized)
            and FORBIDDEN_SOURCE_ALIAS_CONTEXT_RE.search(normalized)
        )
    )


def reject_positive_source_aliases(value: Any, trail: str = "source") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if forbidden_positive_source_alias_key(key_text) and positive_claim(child):
                raise SystemExit(f"{trail}.{key_text} overclaims public/runtime/v1 ResourceHandle readiness")
            reject_positive_source_aliases(child, f"{trail}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_positive_source_aliases(child, f"{trail}[{index}]")


def validate_source(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    reject_positive_source_aliases(source)
    if source.get("schema") != RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA:
        raise SystemExit("source schema is not resource-handle revalidation evaluator")
    identity = source_output_identity(source)
    if source.get("promotion_ready") is not False:
        raise SystemExit("source promotion_ready must be false")
    if source.get("public_resource_handle_ready") is not False:
        raise SystemExit("source public_resource_handle_ready must be false")
    if source.get("post_callback_resource_handle_ready") is not False:
        raise SystemExit("source post_callback_resource_handle_ready must be false")

    artifact_identity = source.get("artifact_identity")
    if not isinstance(artifact_identity, dict):
        raise SystemExit("source artifact_identity summary missing")
    if artifact_identity.get("required") is not True:
        raise SystemExit("source artifact identity must have been required")
    if required_int(artifact_identity, "missing_or_partial_input_count", "source artifact_identity") != 0:
        raise SystemExit("source has missing or partial input artifact identity")
    if required_int(artifact_identity, "invalid_input_count", "source artifact_identity") != 0:
        raise SystemExit("source has invalid input artifact identity")

    counts = source.get("reconciliation_summary")
    if not isinstance(counts, dict):
        raise SystemExit("source reconciliation_summary missing")
    if required_int(counts, "accepted_sample_count", "source reconciliation_summary") <= 0:
        raise SystemExit("source has no accepted reconciliation samples")
    if required_int(counts, "serial_candidate_nonzero_count", "source reconciliation_summary") <= 0:
        raise SystemExit("source has no nonzero serial candidates")
    if required_int(counts, "serial_candidate_zero_count", "source reconciliation_summary") != 0:
        raise SystemExit("source contains zero serial candidates")
    if required_int(counts, "serial_candidate_missing_count", "source reconciliation_summary") != 0:
        raise SystemExit("source contains missing serial candidates")

    checks = source.get("evidence_checks")
    if not isinstance(checks, dict):
        raise SystemExit("source evidence_checks missing")
    if checks.get("serial_reuse_or_wraparound_policy_present") is not False:
        raise SystemExit("source already claims serial reuse/wraparound policy")

    candidate = source.get("internal_uobject_revalidation_candidate")
    if not isinstance(candidate, dict):
        raise SystemExit("source missing internal_uobject_revalidation_candidate")
    if candidate.get("schema") != INTERNAL_UOBJECT_REVALIDATION_CANDIDATE_SCHEMA:
        raise SystemExit("internal candidate schema mismatch")
    if candidate.get("accepted") is not True:
        raise SystemExit("internal candidate is not accepted")
    if candidate.get("candidate") != INTERNAL_UOBJECT_REVALIDATION_CONTRACT:
        raise SystemExit("internal candidate contract mismatch")
    if candidate.get("source_post_callback_resource_handle_ready") is not False:
        raise SystemExit("internal candidate overclaims post-callback ResourceHandle readiness")
    return candidate, identity


def serial_case_decision(
    *,
    observed_serial: int | None,
    expected_serial: int | None,
    fresh_serial_proven: bool,
    slot_reused: bool,
    wraparound_state: str,
    same_frame: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    if observed_serial is None:
        reasons.append("missing_serial")
    elif observed_serial == 0:
        reasons.append("zero_serial")
    if expected_serial is None or expected_serial == 0:
        reasons.append("missing_expected_nonzero_serial")
    if (
        isinstance(observed_serial, int)
        and isinstance(expected_serial, int)
        and observed_serial != 0
        and expected_serial != 0
        and observed_serial != expected_serial
    ):
        reasons.append("serial_mismatch")
    if wraparound_state != "fresh_nonwrapped":
        reasons.append("wraparound_unknown")
    if slot_reused and not fresh_serial_proven:
        reasons.append("slot_reuse_without_fresh_serial")
    if not fresh_serial_proven:
        reasons.append("fresh_serial_not_proven")
    if not same_frame:
        reasons.append("post_callback_or_cross_frame")

    if reasons:
        return {
            "decision": "reject",
            "fail_closed": True,
            "reasons": sorted(set(reasons)),
        }
    return {
        "decision": "allow_candidate_frame_local_only",
        "fail_closed": False,
        "reasons": [],
    }


def canonical_decision_cases() -> list[dict[str, Any]]:
    cases = [
        {
            "case": "zero_serial",
            "observed_serial": 0,
            "expected_serial": 1001,
            "fresh_serial_proven": True,
            "slot_reused": False,
            "wraparound_state": "fresh_nonwrapped",
            "same_frame": True,
        },
        {
            "case": "serial_mismatch",
            "observed_serial": 1002,
            "expected_serial": 1001,
            "fresh_serial_proven": True,
            "slot_reused": False,
            "wraparound_state": "fresh_nonwrapped",
            "same_frame": True,
        },
        {
            "case": "wraparound_unknown",
            "observed_serial": 1001,
            "expected_serial": 1001,
            "fresh_serial_proven": True,
            "slot_reused": False,
            "wraparound_state": "unknown",
            "same_frame": True,
        },
        {
            "case": "slot_reuse_without_fresh_serial",
            "observed_serial": 1001,
            "expected_serial": 1001,
            "fresh_serial_proven": False,
            "slot_reused": True,
            "wraparound_state": "fresh_nonwrapped",
            "same_frame": True,
        },
        {
            "case": "post_callback_attempt",
            "observed_serial": 1001,
            "expected_serial": 1001,
            "fresh_serial_proven": True,
            "slot_reused": False,
            "wraparound_state": "fresh_nonwrapped",
            "same_frame": False,
        },
        {
            "case": "fresh_nonzero_match_same_frame",
            "observed_serial": 1001,
            "expected_serial": 1001,
            "fresh_serial_proven": True,
            "slot_reused": False,
            "wraparound_state": "fresh_nonwrapped",
            "same_frame": True,
        },
    ]
    return [
        {
            **case,
            **serial_case_decision(
                observed_serial=case["observed_serial"],
                expected_serial=case["expected_serial"],
                fresh_serial_proven=case["fresh_serial_proven"],
                slot_reused=case["slot_reused"],
                wraparound_state=case["wraparound_state"],
                same_frame=case["same_frame"],
            ),
        }
        for case in cases
    ]


def canonical_policy_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": report.get("schema"),
        "evidence_kind": report.get("evidence_kind"),
        "status": report.get("status"),
        "source_artifacts": report.get("source_artifacts"),
        "binary_sha256": report.get("binary_sha256"),
        "internal_candidate": report.get("internal_candidate"),
        "serial_policy": report.get("serial_policy"),
        "decision_cases": report.get("decision_cases"),
        "contract_checks": report.get("contract_checks"),
        "remaining_blockers": report.get("remaining_blockers"),
        "non_claims": report.get("non_claims"),
        "promotion_ready": report.get("promotion_ready"),
        "public_resource_handle_ready": report.get("public_resource_handle_ready"),
        "post_callback_resource_handle_ready": report.get("post_callback_resource_handle_ready"),
        "promotion_gate": report.get("promotion_gate"),
    }


def add_artifact_identity(report: dict[str, Any], *, capture_id: str, evidence_pack_id: str) -> None:
    identity_without_hash = {
        "artifact_kind": SCHEMA,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": canonical_policy_report(report),
    }
    report["output_artifact_identity"] = {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(canonical_json_bytes(material)).hexdigest(),
    }


def build_policy(source: dict[str, Any], *, capture_id: str, evidence_pack_id: str) -> dict[str, Any]:
    candidate, source_identity = validate_source(source)
    source_hashes = source.get("artifact_identity", {}).get("hashes")
    if not isinstance(source_hashes, list):
        source_hashes = []
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "evidence_kind": "internal_serial_reuse_wraparound_fail_closed_policy",
        "status": STATUS,
        "source_artifacts": [
            {
                "schema": RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
                "artifact_sha256": source_identity["artifact_sha256"],
                "capture_id": source_identity["capture_id"],
                "evidence_pack_id": source_identity["evidence_pack_id"],
                "consume_gate_status": "accepted",
                "path_redacted": True,
            }
        ],
        "binary_sha256": candidate.get("binary_sha256"),
        "internal_candidate": {
            "schema": candidate.get("schema"),
            "accepted": True,
            "candidate_level": candidate.get("candidate_level"),
            "source_artifact_hashes": sorted(str(value) for value in source_hashes if isinstance(value, str)),
            "contract": INTERNAL_UOBJECT_REVALIDATION_CONTRACT,
        },
        "serial_policy": {
            "subject": "InternalUObjectRevalidationCandidate",
            "scope": "frame_local_candidate_only",
            "serial_source": "FUObjectItem+0x8_candidate",
            "fuobjectitem_dword_0xC": "unknown_record_neutrally_not_serial_evidence",
            "accepted_candidate_path": [
                "same_hook_or_callback_frame",
                "fresh_fuobjectitem_read",
                "nonzero_observed_serial",
                "expected_nonzero_serial_available",
                "observed_serial_matches_expected_serial",
                "fresh_serial_proven_for_current_slot",
                "wraparound_known_not_to_have_occurred_for_this_candidate",
                "slot_reuse_absent_or_revalidated_with_fresh_serial",
                "non_null_uobject",
                "plausible_gobjects_membership",
                "flag_policy_allows_frame_local_candidate",
            ],
            "fail_closed_rules": {
                "zero_serial": "reject",
                "missing_serial": "reject",
                "serial_mismatch": "reject",
                "wraparound_unknown": "reject",
                "slot_reuse_without_fresh_serial": "reject",
                "post_callback_or_cross_frame": "reject",
                "public_lookup_request": "reject",
            },
            "privacy": {
                "expose_uobject_pointer": False,
                "expose_gobjects_index": False,
                "expose_serial": False,
                "expose_lookup_token": False,
            },
            "output": "copied_bool_or_reason_or_obelisk_owned_copied_data_only",
            "public_api": "not_promoted",
        },
        "decision_cases": canonical_decision_cases(),
        "contract_checks": {
            "source_candidate_accepted": True,
            "source_public_resource_handle_ready": False,
            "source_post_callback_resource_handle_ready": False,
            "serial_reuse_or_wraparound_policy_present": True,
            "serial_reuse_or_wraparound_safety_proven": False,
            "zero_serial_rejected": True,
            "serial_mismatch_rejected": True,
            "wraparound_unknown_rejected": True,
            "slot_reuse_without_fresh_serial_rejected": True,
            "fresh_serial_required_for_current_slot": True,
            "frame_local_only": True,
            "public_resource_handle_contract_present": False,
            "post_callback_resource_handle_ready": False,
        },
        "remaining_blockers": list(REMAINING_BLOCKERS),
        "non_claims": list(NON_CLAIMS),
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "promotion_gate": {
            "ready": False,
            "blockers": ["candidate_only_serial_reuse_wraparound_policy"],
        },
    }
    add_artifact_identity(report, capture_id=capture_id, evidence_pack_id=evidence_pack_id)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revalidation", required=True, type=Path, help="ResourceHandle revalidation evaluator JSON.")
    parser.add_argument("--capture-id", required=True)
    parser.add_argument("--evidence-pack-id", required=True)
    parser.add_argument("--output", type=Path, help="Optional output JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_safe_identity_args(args)
    revalidation_path = reject_protected_input_path(args.revalidation, "--revalidation")
    output_path = reject_protected_output_path(args.output, "--output") if args.output else None
    report = build_policy(
        load_json(revalidation_path, "--revalidation"),
        capture_id=args.capture_id,
        evidence_pack_id=args.evidence_pack_id,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
