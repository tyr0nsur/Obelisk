#!/usr/bin/env python3
"""Build a fail-closed post-callback ResourceHandle rejection contract."""

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


SCHEMA = "obelisk.internal-uobject-revalidation-post-callback-contract.v1"
STATUS = "accepted_internal_rejection_contract"
REMAINING_BLOCKERS = tuple(
    blocker
    for blocker in RESOURCE_HANDLE_LIFETIME_BLOCKERS
    if blocker not in {"no_post_callback_lifetime_contract"}
) + (
    "candidate_only_post_callback_rejection_contract",
    "uobject_flags_validity_semantics_unproven",
)
NON_CLAIMS = tuple(RESOURCE_HANDLE_NON_CLAIMS) + (
    "does_not_promote_post_callback_handles",
    "does_not_claim_runtime_object_samples",
    "does_not_claim_serial_reuse_or_wraparound_safety",
)
FORBIDDEN_SOURCE_CLAIM_KEYS = frozenset(
    (
        "promotion_ready",
        "public_abi_ready",
        "public_sdk_ready",
        "release_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "v1_sdk_ready",
        "object_identity_ready",
        "post_callback_resource_handle_ready",
        "public_object_identity_ready",
        "public_object_lookup_ready",
        "public_resource_handle_ready",
        "resource_handle_ready",
        "runtime_object_samples_present",
        "serial_reuse_or_wraparound_safety_proven",
    )
)
FORBIDDEN_SOURCE_ALIAS_SUBJECT_RE = re.compile(
    r"(?:resource_?handle|resourcehandle|resource_?lookup|object_?identity|object_?lookup|object_?handle|"
    r"runtime_?object|serial_?reuse|wraparound)",
    re.IGNORECASE,
)
FORBIDDEN_SOURCE_ALIAS_CONTEXT_RE = re.compile(
    r"(?:public|runtime|v1|sdk|abi|release|promot|ready|readiness|enabled|allowed|available|post_?callback|samples?|safety)",
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


def canonical_contract_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": report.get("schema"),
        "evidence_kind": report.get("evidence_kind"),
        "status": report.get("status"),
        "source_artifacts": report.get("source_artifacts"),
        "binary_sha256": report.get("binary_sha256"),
        "internal_candidate": report.get("internal_candidate"),
        "contract": report.get("contract"),
        "contract_checks": report.get("contract_checks"),
        "remaining_blockers": report.get("remaining_blockers"),
        "non_claims": report.get("non_claims"),
        "promotion_ready": report.get("promotion_ready"),
        "public_resource_handle_ready": report.get("public_resource_handle_ready"),
        "post_callback_resource_handle_ready": report.get("post_callback_resource_handle_ready"),
        "post_callback_lookup_ready": report.get("post_callback_lookup_ready"),
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
        "report": canonical_contract_report(report),
    }
    report["output_artifact_identity"] = {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(canonical_json_bytes(material)).hexdigest(),
    }


def build_contract(source: dict[str, Any], *, capture_id: str, evidence_pack_id: str) -> dict[str, Any]:
    candidate, source_identity = validate_source(source)
    source_hashes = source.get("artifact_identity", {}).get("hashes")
    if not isinstance(source_hashes, list):
        source_hashes = []
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "evidence_kind": "internal_post_callback_rejection_contract",
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
        "contract": {
            "subject": "InternalUObjectRevalidationCandidate",
            "lifetime": "frame_local_only",
            "validity_scope": "same_hook_or_callback_frame_only",
            "post_callback_lookup": "rejected",
            "post_callback_use": "rejected",
            "resource_handle": "not_promoted",
            "gobjects_lookup": "not_promoted",
            "object_identity": "not_promoted",
            "inputs": [
                "internal_index_serial_evidence",
                "binary_sha256",
                "complete_consumed_artifact_identity",
            ],
            "acceptance_checks_frame_local_only": [
                "supported_binary_sha256",
                "accepted_consume_gate",
                "coherent_gobjects_evidence",
                "in_bounds_chunk_and_item",
                "readable_fuobjectitem",
                "nonzero_serial",
                "serial_match_at_current_candidate_slot",
                "non_null_uobject",
                "plausible_membership",
            ],
            "flag_policy": {
                "UObject+0x8&0x100": "reject",
                "UObject+0x8&0x4000": "reject_by_default",
                "0x4000_exception": "allowed_only_inside_a_reviewed_helper_mode_before_callback_return",
            },
            "post_callback_behavior": {
                "stored_token": "invalid",
                "lookup_attempt": "fail_closed",
                "return_value": "not_found_or_invalid",
                "ue_pointer_return": "forbidden",
                "raw_identity_return": "forbidden",
            },
            "output": "copied_bool_or_reason_or_obelisk_owned_copied_data_only",
            "forbidden_outputs": [
                "UObject_pointer",
                "GObjects_index",
                "FUObjectItem_address",
                "serial",
                "InternalIndex",
                "class_name_outer",
                "FName_or_GObjects_indices",
                "persistent_handle",
                "lookup_token",
                "mutation_path",
                "return_override",
            ],
            "public_api": "not_promoted",
        },
        "contract_checks": {
            "source_candidate_accepted": True,
            "source_post_callback_resource_handle_ready": False,
            "frame_local_lifetime_required": True,
            "post_callback_lookup_rejected": True,
            "public_resource_handle_contract_present": False,
            "public_resourcehandle_policy_present": False,
            "post_callback_lifetime_contract_present": True,
            "post_callback_lifetime_policy_proven": True,
            "runtime_object_samples_present": False,
            "serial_reuse_or_wraparound_policy_present": False,
        },
        "remaining_blockers": list(REMAINING_BLOCKERS),
        "non_claims": list(NON_CLAIMS),
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "post_callback_lookup_ready": False,
        "promotion_gate": {
            "ready": False,
            "blockers": ["candidate_only_post_callback_rejection_contract"],
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
    report = build_contract(
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
