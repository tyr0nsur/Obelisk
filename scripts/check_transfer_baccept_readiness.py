#!/usr/bin/env python3
"""Read-only readiness check for the internal Transfer bAccept lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import validate_offline_artifact_gate as offline_gate
from plan_obelisk_multi_surface_beta_capture import (
    CURRENT_ROUTE_BLOCKER,
    REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
)
from reflection_target_sets import NON_AUTHORIZING_READY_DOES_NOT_SATISFY, NON_AUTHORIZING_READY_SCOPE
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = Path("/home/flowcommunity-ark/obelisk-artifacts/transfer-baccept-only-policy-slice-20260530T073308Z")
DEFAULT_MANIFEST_NAME = "transfer-baccept-only-policy-slice.json"
EXPECTED_MANIFEST_SHA256 = "a2b0939189cb847b351c638141fa5e122c08ca69acadae8b5c86d894fc208f12"
REPORT_SCHEMA = "obelisk.transfer-baccept-readiness-check.v1"
POLICY_SCHEMA = offline_gate.TRANSFER_BACCEPT_ONLY_POLICY_SLICE_SCHEMA
INPUT_TARGET_SET = "transfer-ufunction-intake"
OUTPUT_TARGET_SET = "transfer-baccept-only-policy-slice"
EXPECTED_COPIED_FIELD = offline_gate.REQUIRED_TRANSFER_BACCEPT_ONLY_COPIED_FIELD
EXPECTED_COPIED_TARGET = offline_gate.REQUIRED_TRANSFER_BACCEPT_ONLY_TARGET
EXPECTED_INPUT_TARGETS = offline_gate.REQUIRED_TRANSFER_BACCEPT_ONLY_INPUT_TARGETS
EXPECTED_FORBIDDEN_FIELDS = offline_gate.REQUIRED_TRANSFER_BACCEPT_ONLY_FORBIDDEN_FIELDS
REQUIRED_NON_CLAIM_TOKENS = (
    "does not promote public SDK callbacks",
    "does not expose UE pointers",
    "does not promote runtime hook wiring",
    "public Transfer SDK",
)
REPORT_FALSE_FLAGS = {
    "approved_runtime_evidence": False,
    "approved_runtime_evidence_ready": False,
    "artifact_gate_ready": False,
    "clears_approved_runtime_evidence_missing": False,
    "complete_sdk_ready": False,
    "contributes_to_public_sdk_v1": False,
    "contributes_to_v1_completion": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_toward_complete_sdk": False,
    "counts_toward_complete_sdk_claim": False,
    "counts_toward_p0_dependency_chain_claim": False,
    "counts_toward_public_sdk": False,
    "counts_toward_public_sdk_v1": False,
    "counts_toward_runtime": False,
    "side_lane_counts_toward_sdk": False,
    "side_lane_counts_toward_p0": False,
    "sdk_p0_unlock_allowed": False,
    "counts_toward_v1_completion": False,
    "cross_map_state_public_contract_ready": False,
    "dino_payload_public_contract_ready": False,
    "dispatcher_ready": False,
    "dispatcher_wiring_ready": False,
    "downloaded_character_public_contract_ready": False,
    "identity_ready": False,
    "live_ops_ready": False,
    "mutation_ready": False,
    "ownership_ready": False,
    "player_identity_public_contract_ready": False,
    "p0_ready": False,
    "promotion_ready": False,
    "public_ready": False,
    "public_abi_ready": False,
    "public_api_ready": False,
    "public_completion_ready": False,
    "public_contract_ready": False,
    "public_header_allowed": False,
    "public_header_ready": False,
    "public_metadata_helpers_ready": False,
    "public_module_ready": False,
    "public_or_runtime_accounting_allowed": False,
    "public_release_ready": False,
    "public_sdk_ready": False,
    "public_transfer_sdk_ready": False,
    "release_candidate_ready": False,
    "replaces_player_principal_evidence": False,
    "replaces_player_principal_triplet": False,
    "resource_handle_public_contract_ready": False,
    "return_override_ready": False,
    "runtime_capture_ready": False,
    "runtime_hook_ready": False,
    "runtime_hook_wiring_ready": False,
    "runtime_ready": False,
    "runtime_validated": False,
    "runtime_validation_ready": False,
    "sdk_ready": False,
    "server_validation_ready": False,
    "stable_sdk_ready": False,
    "transfer_payload_decoding_ready": False,
    "transfer_payload_public_contract_ready": False,
    "v1_completion_evidence": False,
    "v1_completion_ready": False,
    "v1_public_sdk_ready": False,
    "v1_ready": False,
    "v1_release_ready": False,
}
REPORT_ZERO_FIELDS = {
    "complete_sdk_claim_progress_contribution": 0,
    "p0_dependency_chain_claim_progress_contribution": 0,
    "v1_completion_progress_contribution": 0,
}
REPORT_NON_CLAIMS = [
    "candidate readiness is internal offline planning evidence only",
    "does not claim runtime validation, runtime hook wiring, dispatcher wiring, live-op readiness, or server validation",
    "does not claim public Transfer SDK, public API, public ABI, public header, public contract, or public metadata helper readiness",
    "does not claim v1 completion, release readiness, stable SDK status, complete SDK status, P0 dependency-chain credit, promotion readiness, or public/runtime accounting credit",
    "does not expose transfer payloads, downloaded characters, dino payload, player identity, cross-map state, or ResourceHandle as a public contract",
    "does not replace approved player-principal lifecycle runtime evidence",
    "multi-surface beta capture pack and plan artifacts are prep only and remain non-counting before the player-principal blocker is solved",
]
TRANSFER_READINESS_ALIAS_EXACT_KEYS = {
    "artifact_gate_ready",
    "complete_sdk_ready",
    "contributes_to_public_sdk_v1",
    "contributes_to_v1_completion",
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_public_sdk_v1",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "dispatcher_ready",
    "dispatcher_wiring_ready",
    "live_ops_ready",
    "public_or_runtime_accounting_allowed",
    "release_candidate_ready",
    "runtime_validated",
    "runtime_validation_ready",
    "server_validation_ready",
    "source_accepted",
    "source_available",
    "source_label",
    "source_labels",
    "source_marker",
    "source_markers",
    "source_readiness",
    "source_ready",
    "source_stable",
    "source_status",
    "source_support",
    "source_tier",
    "source_validated",
    "source_validation",
    "stable_sdk_ready",
    *REPORT_ZERO_FIELDS,
    "v1_completion_evidence",
    "v1_public_sdk_ready",
    "v1_ready",
    "v1_release_ready",
}
TRANSFER_READINESS_ALIAS_SUBJECTS = (
    "complete_sdk",
    "cross_map_state",
    "dino_payload",
    "dispatcher",
    "downloaded_character",
    "identity",
    "live_ops",
    "ownership",
    "player_identity",
    "p0",
    "public",
    "public_abi",
    "public_api",
    "public_contract",
    "public_header",
    "public_metadata",
    "public_module",
    "public_or_runtime",
    "public_release",
    "public_sdk",
    "public_transfer_sdk",
    "release_candidate",
    "resource_handle",
    "return_override",
    "runtime",
    "runtime_capture",
    "sdk",
    "server_validation",
    "source",
    "stable_sdk",
    "transfer_payload",
    "transfer_sdk",
    "v1",
)
TRANSFER_READINESS_ALIAS_CONTEXTS = (
    "accounting",
    "allowed",
    "available",
    "claim",
    "complete",
    "completion",
    "contract",
    "counts_toward",
    "enabled",
    "exposed",
    "promot",
    "public",
    "ready",
    "readiness",
    "release",
    "runtime",
    "stable",
    "status",
    "validated",
    "validation",
)
POSITIVE_SOURCE_STATUS_VALUES = {
    "accepted",
    "active",
    "approved",
    "available",
    "complete",
    "completed",
    "enabled",
    "passed",
    "promoted",
    "public",
    "public_ready",
    "ready",
    "release_ready",
    "release_supported",
    "runtime",
    "runtime_ready",
    "sdk_ready",
    "stable",
    "stable_ready",
    "supported",
    "true",
    "validated",
    "v1_ready",
}
TRANSFER_CONTEXTUAL_STATUS_KEYS = {
    "accepted",
    "active",
    "approved",
    "complete",
    "enabled",
    "outcome",
    "passed",
    "promoted",
    "readiness",
    "ready",
    "result",
    "stable",
    "state",
    "status",
    "validated",
}
TRANSFER_CONTEXTUAL_ACCOUNTING_TERMS = (
    "contribution",
    "count",
    "counts",
    "progress",
)
TRANSFER_NEUTRAL_POSITIVE_METADATA_KEYS = {
    "copied_bool_count",
    "forbidden_field_count",
    "input_target_count",
    "source_binding_count",
    "target_count",
}
TRANSFER_NEUTRAL_POSITIVE_METADATA_SUFFIXES = (
    "_field_count",
    "_target_count",
)
TRANSFER_READINESS_CONTEXT_KEYS = {
    "candidate",
    "package_shape",
    "plugin_hub",
    "public_sdk",
    "readiness",
    "runtime",
    "support_tier",
    "target_set",
    "v1",
}
POLICY_TOP_LEVEL_ALLOWED_KEYS = {
    "copied_bool",
    "coverage",
    "forbidden_transfer_fields",
    "generated_from",
    "input_target_set",
    "missing_targets",
    "non_claims",
    "output_target_set",
    "policy_status",
    "safety_summary",
    "schema",
    "snapshot_root",
}
COVERAGE_ALLOWED_KEYS = {
    "copied_fields",
    "copied_targets",
    "forbidden_fields",
    "input_targets",
    "status",
}
COPIED_BOOL_ALLOWED_KEYS = {
    "array_dim",
    "byte_mask",
    "copied_field",
    "direction",
    "element_size",
    "evidence_status",
    "field",
    "field_mask",
    "function_flags",
    "native_bool",
    "num_parms",
    "offset",
    "offset_internal",
    "parms_size",
    "property_class",
    "property_flags",
    "return_value_offset",
    "source_snapshot",
    "source_snapshot_sha256",
    "target",
    "type",
}
FORBIDDEN_FIELD_ALLOWED_KEYS = {
    "array_dim",
    "element_size",
    "field",
    "forbidden_field",
    "offset",
    "offset_internal",
    "property_class",
    "property_flags",
    "reason",
    "source_snapshot",
    "source_snapshot_sha256",
    "target",
}
SAFETY_SUMMARY_ALLOWED_KEYS = {
    "artifact_status",
    "copied_bool_count",
    "explicitly_excluded",
    "forbidden_field_count",
    "intended_use",
    "promotion_ready",
}
GENERATED_FROM_ALLOWED_KEYS = {
    "input_snapshots",
    "snapshot_schema",
}
INPUT_SNAPSHOT_ALLOWED_KEYS = {
    "id",
    "sha256",
    "target",
}
FORBIDDEN_CLAIM_FIELD_RE = re.compile(
    r"(?:transfer_?sdk|public_?sdk|public_?abi|identity|ownership|mutation|return_?overrides?|"
    r"runtime(?:_hook)?_?wiring|runtime_(?:ready|validated|validation)|dispatcher_(?:ready|wiring)|"
    r"transfer_?payloads?|downloaded_?characters?|dino_?payload|cross_?map|resource_?handle|"
    r"public_?contract|v1(?:_completion|_complete|_stable|_ready)?|completion)",
    re.IGNORECASE,
)
POSITIVE_CLAIM_VALUE_RE = re.compile(
    r"(?:public\s+Transfer\s+SDK|Transfer\s+SDK|public\s+ABI|identity|ownership|mutation|"
    r"return\s+override|runtime\s+(?:hook\s+)?wiring|dispatcher\s+wiring|v1\s+completion)",
    re.IGNORECASE,
)
PUBLIC_CONTRACT_SURFACE_RE = re.compile(
    r"(?:transfer\s+payloads?|downloaded\s+characters?|downloaded\s+character|dino\s+payload|"
    r"player\s+identity|cross-map\s+state|cross\s+map\s+state|ResourceHandle|resource\s+handle)",
    re.IGNORECASE,
)
PUBLIC_CONTRACT_CONTEXT_RE = re.compile(
    r"(?:public\s+(?:contract|sdk|api)|contract\s+ready|ready|runtime\s+ready|promot(?:e|es|ed|ion)|"
    r"expos(?:e|es|ed)|decod(?:e|es|ed|ing)|available)",
    re.IGNORECASE,
)
NEGATIVE_CLAIM_RE = re.compile(r"\b(?:does\s+not|not\s+promote|not\s+expose|not\s+copy|excluded)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Transfer bAccept candidate readiness without promoting runtime or a public Transfer SDK."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Offline artifact root.")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Transfer bAccept policy-slice manifest. Defaults to --root/transfer-baccept-only-policy-slice.json.",
    )
    parser.add_argument(
        "--expected-manifest-sha256",
        default=EXPECTED_MANIFEST_SHA256,
        help="Expected direct manifest SHA256. Defaults to the reviewed durable artifact.",
    )
    parser.add_argument(
        "--skip-artifact-gates",
        action="store_true",
        help="Skip consume/promote gate subprocesses for hermetic policy-fixture tests.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def safe_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        append_blocker(blockers, "path_rejected", label=label, path=str(path), detail=str(exc))
        return None


def run_gate(root: Path, manifest: Path, mode: str) -> tuple[int, dict[str, Any] | None, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "validate_offline_artifact_gate.py"),
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--mode",
            mode,
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
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
    return result.returncode, payload, result.stderr.strip()


def build_multi_surface_beta_capture_guardrail() -> dict[str, Any]:
    return {
        "status": "candidate_only_non_counting",
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_first_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_ready": False,
        "clears_approved_runtime_evidence_missing": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "side_lane_counts_toward_sdk": False,
        "side_lane_counts_toward_p0": False,
        "sdk_p0_unlock_allowed": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "public_sdk_ready": False,
        "public_transfer_sdk_ready": False,
        "stable_sdk_ready": False,
        "v1_completion_ready": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "non_claim": (
            "candidate multi-surface beta capture pack/plan artifacts are prep only; "
            "they do not satisfy approved player-principal runtime evidence"
        ),
    }


def read_policy(manifest: Path, blockers: list[dict[str, Any]], expected_sha256: str) -> dict[str, Any] | None:
    try:
        with offline_gate.open_regular_file_no_symlink(manifest) as handle:
            content = handle.read()
        manifest_sha256 = hashlib.sha256(content).hexdigest()
        parsed = json.loads(content.decode("utf-8"))
    except offline_gate.SymlinkPathError as exc:
        append_blocker(
            blockers,
            "manifest_path_is_symlink",
            path=str(manifest),
            symlink_component=str(exc.component),
        )
        return None
    except OSError as exc:
        append_blocker(blockers, "manifest_unreadable", path=str(manifest), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "manifest_malformed", path=str(manifest), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        append_blocker(blockers, "manifest_not_object", path=str(manifest))
        return None
    if manifest_sha256 != expected_sha256:
        append_blocker(blockers, "manifest_sha256_mismatch", expected=expected_sha256, value=manifest_sha256)
    return parsed


def require_set(blockers: list[dict[str, Any]], *, reason: str, actual: Any, expected: set[str]) -> set[str]:
    actual_set = set(actual) if isinstance(actual, list) and all(isinstance(item, str) for item in actual) else set()
    if actual_set != expected:
        append_blocker(blockers, reason, missing=sorted(expected - actual_set), unexpected=sorted(actual_set - expected))
    return actual_set


def reject_forbidden_claim_fields(
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    mapping: dict[str, Any],
    path: str,
    allowed_keys: set[str] | None = None,
) -> None:
    for key in mapping:
        if allowed_keys is not None and key not in allowed_keys:
            append_blocker(blockers, reason, path=path, field=key, detail="unexpected_field")
        elif FORBIDDEN_CLAIM_FIELD_RE.search(key):
            append_blocker(blockers, reason, path=path, field=key, detail="forbidden_claim_field")


def reject_positive_claim_values(value: Any, blockers: list[dict[str, Any]], *, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            reject_positive_claim_values(child, blockers, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_positive_claim_values(child, blockers, path=f"{path}[{index}]")
        return
    if not isinstance(value, str) or POSITIVE_CLAIM_VALUE_RE.search(value) is None:
        return
    if path.startswith("$.non_claims[") and NEGATIVE_CLAIM_RE.search(value) is not None:
        return
    if path.startswith("$.safety_summary.explicitly_excluded["):
        return
    append_blocker(blockers, "forbidden_positive_claim_value", path=path, value=value)


def reject_public_contract_claim_values(value: Any, blockers: list[dict[str, Any]], *, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            reject_public_contract_claim_values(child, blockers, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_public_contract_claim_values(child, blockers, path=f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if path.startswith("$.non_claims[") and NEGATIVE_CLAIM_RE.search(value) is not None:
        return
    if path.startswith("$.safety_summary.explicitly_excluded["):
        return
    if PUBLIC_CONTRACT_SURFACE_RE.search(value) is None or PUBLIC_CONTRACT_CONTEXT_RE.search(value) is None:
        return
    append_blocker(blockers, "forbidden_public_contract_claim_value", path=path, value=value)


def is_transfer_readiness_alias_key(key: str) -> bool:
    normalized = offline_gate.normalized_claim_key(key)
    if normalized in TRANSFER_READINESS_ALIAS_EXACT_KEYS or normalized in REPORT_FALSE_FLAGS:
        return True
    return any(subject in normalized for subject in TRANSFER_READINESS_ALIAS_SUBJECTS) and any(
        context in normalized for context in TRANSFER_READINESS_ALIAS_CONTEXTS
    )


def normalized_trail_leaf_key(trail: str) -> str:
    leaf = trail.rsplit(".", 1)[-1]
    leaf = re.sub(r"\[\d+\]$", "", leaf)
    return offline_gate.normalized_claim_key(leaf)


def positive_source_alias_value(value: str) -> bool:
    normalized = offline_gate.normalized_claim_key(value)
    return normalized in POSITIVE_SOURCE_STATUS_VALUES or normalized.endswith("_ready")


def positive_numeric_claim(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def positive_transfer_alias_value(value: Any) -> bool:
    if value is True or positive_numeric_claim(value):
        return True
    return isinstance(value, str) and positive_source_alias_value(value)


def transfer_neutral_positive_metadata_key(key: str) -> bool:
    return key in TRANSFER_NEUTRAL_POSITIVE_METADATA_KEYS or any(
        key.endswith(suffix) for suffix in TRANSFER_NEUTRAL_POSITIVE_METADATA_SUFFIXES
    )


def transfer_accounting_alias_key(key: str) -> bool:
    return any(term in key for term in TRANSFER_CONTEXTUAL_ACCOUNTING_TERMS)


def transfer_context_key(key: str) -> bool:
    if key in {"accepted_for_internal_planning", "copied_bool_count", "forbidden_field_count"}:
        return False
    if key in TRANSFER_READINESS_CONTEXT_KEYS:
        return True
    return is_transfer_readiness_alias_key(key) or bool(
        any(subject in key for subject in TRANSFER_READINESS_ALIAS_SUBJECTS)
    )


def reject_contextual_transfer_readiness_alias_overclaims(
    value: Any,
    blockers: list[dict[str, Any]],
    *,
    path: str = "$",
    claim_context: bool = False,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            normalized_key = offline_gate.normalized_claim_key(str(key))
            child_context = claim_context or transfer_context_key(normalized_key)
            if (
                is_transfer_readiness_alias_key(normalized_key)
                and positive_transfer_alias_value(child)
                and not transfer_neutral_positive_metadata_key(normalized_key)
            ):
                append_blocker(blockers, "readiness_alias_overclaim", path=key_path, field=normalized_key)
            if (
                child_context
                and normalized_key in TRANSFER_CONTEXTUAL_STATUS_KEYS
                and positive_transfer_alias_value(child)
            ):
                append_blocker(blockers, "readiness_alias_overclaim", path=key_path, field=normalized_key, value=child)
            if (
                child_context
                and transfer_accounting_alias_key(normalized_key)
                and not transfer_neutral_positive_metadata_key(normalized_key)
                and positive_numeric_claim(child)
            ):
                append_blocker(blockers, "readiness_alias_overclaim", path=key_path, field=normalized_key, value=child)
            reject_contextual_transfer_readiness_alias_overclaims(
                child,
                blockers,
                path=key_path,
                claim_context=child_context,
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_contextual_transfer_readiness_alias_overclaims(
                child,
                blockers,
                path=f"{path}[{index}]",
                claim_context=claim_context,
            )
        return
    if claim_context and isinstance(value, str) and positive_source_alias_value(value):
        append_blocker(blockers, "readiness_alias_overclaim", path=path, value=value)


def reject_transfer_readiness_alias_overclaims(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    for trail, value in offline_gate.collect_bool_fields(policy):
        key = normalized_trail_leaf_key(trail)
        if value is True and is_transfer_readiness_alias_key(key):
            append_blocker(blockers, "readiness_alias_overclaim", path=trail, field=key)
    for trail, value in offline_gate.collect_string_fields(policy):
        key = normalized_trail_leaf_key(trail)
        if is_transfer_readiness_alias_key(key) and positive_source_alias_value(value):
            append_blocker(blockers, "readiness_alias_overclaim", path=trail, field=key, value=value)
    for trail, value in offline_gate.collect_promoted_status_overclaims(policy):
        append_blocker(blockers, "readiness_alias_overclaim", path=trail, value=value)
    reject_contextual_transfer_readiness_alias_overclaims(policy, blockers)


def validate_copied_bool(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    copied_bool = policy.get("copied_bool")
    if not isinstance(copied_bool, dict):
        append_blocker(blockers, "copied_bool_missing")
        return
    reject_forbidden_claim_fields(
        blockers,
        reason="copied_bool_unexpected_field",
        mapping=copied_bool,
        path="copied_bool",
        allowed_keys=COPIED_BOOL_ALLOWED_KEYS,
    )
    for key, expected in {
        "copied_field": EXPECTED_COPIED_FIELD,
        "target": EXPECTED_COPIED_TARGET,
        "field": "bAccept",
        "direction": "in",
        "type": "bool",
        "evidence_status": "copied-bool-only",
        "property_class": "BoolProperty",
        "offset": "0x0",
        "offset_internal": 0,
        "element_size": 1,
        "array_dim": 1,
        "byte_mask": "0x01",
        "field_mask": "0xff",
        "native_bool": False,
        "function_flags": "0x220cc0",
        "num_parms": 1,
        "parms_size": 1,
        "return_value_offset": "0xffff",
        "property_flags": "0x1040000280",
    }.items():
        if copied_bool.get(key) != expected:
            append_blocker(
                blockers,
                "copied_bool_metadata_mismatch",
                field=key,
                expected=expected,
                value=copied_bool.get(key),
            )


def validate_forbidden_transfer_fields(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    entries = policy.get("forbidden_transfer_fields")
    if not isinstance(entries, list):
        append_blocker(blockers, "forbidden_transfer_fields_missing")
        return []
    if len(entries) != len(EXPECTED_FORBIDDEN_FIELDS):
        append_blocker(blockers, "forbidden_transfer_field_count_mismatch", expected=len(EXPECTED_FORBIDDEN_FIELDS), value=len(entries))

    fields: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            append_blocker(blockers, "forbidden_transfer_field_entry_not_object", index=index)
            continue
        reject_forbidden_claim_fields(
            blockers,
            reason="forbidden_transfer_field_unexpected_field",
            mapping=entry,
            path=f"forbidden_transfer_fields[{index}]",
            allowed_keys=FORBIDDEN_FIELD_ALLOWED_KEYS,
        )
        forbidden_field = entry.get("forbidden_field")
        if isinstance(forbidden_field, str):
            fields.append(forbidden_field)
        if forbidden_field not in EXPECTED_FORBIDDEN_FIELDS:
            append_blocker(blockers, "forbidden_transfer_field_unexpected", index=index, forbidden_field=forbidden_field)
    if set(fields) != EXPECTED_FORBIDDEN_FIELDS:
        append_blocker(
            blockers,
            "forbidden_transfer_field_coverage_mismatch",
            missing=sorted(EXPECTED_FORBIDDEN_FIELDS - set(fields)),
            unexpected=sorted(set(fields) - EXPECTED_FORBIDDEN_FIELDS),
        )
    return sorted(set(fields))


def validate_generated_from(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    generated_from = policy.get("generated_from")
    if not isinstance(generated_from, dict):
        append_blocker(blockers, "generated_from_missing")
        return []
    reject_forbidden_claim_fields(
        blockers,
        reason="generated_from_unexpected_field",
        mapping=generated_from,
        path="generated_from",
        allowed_keys=GENERATED_FROM_ALLOWED_KEYS,
    )
    if generated_from.get("snapshot_schema") != offline_gate.RC_UFUNCTION_SNAPSHOT_SCHEMA:
        append_blocker(blockers, "generated_from_snapshot_schema_mismatch", value=generated_from.get("snapshot_schema"))
    snapshots = generated_from.get("input_snapshots")
    if not isinstance(snapshots, list):
        append_blocker(blockers, "generated_from_input_snapshots_missing")
        return []
    targets: list[str] = []
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            append_blocker(blockers, "input_snapshot_not_object", index=index)
            continue
        reject_forbidden_claim_fields(
            blockers,
            reason="input_snapshot_unexpected_field",
            mapping=snapshot,
            path=f"generated_from.input_snapshots[{index}]",
            allowed_keys=INPUT_SNAPSHOT_ALLOWED_KEYS,
        )
        target = snapshot.get("target")
        if isinstance(target, str):
            targets.append(target)
    require_set(blockers, reason="input_snapshot_target_coverage_mismatch", actual=targets, expected=EXPECTED_INPUT_TARGETS)
    return sorted(set(targets))


def validate_policy(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    reject_forbidden_claim_fields(
        blockers,
        reason="policy_unexpected_field",
        mapping=policy,
        path="policy",
        allowed_keys=POLICY_TOP_LEVEL_ALLOWED_KEYS,
    )
    if policy.get("schema") != POLICY_SCHEMA:
        append_blocker(blockers, "schema_mismatch", value=policy.get("schema"))
    if policy.get("input_target_set") != INPUT_TARGET_SET:
        append_blocker(blockers, "input_target_set_mismatch", value=policy.get("input_target_set"))
    if policy.get("output_target_set") != OUTPUT_TARGET_SET:
        append_blocker(blockers, "output_target_set_mismatch", value=policy.get("output_target_set"))
    if policy.get("policy_status") != "evidence-only":
        append_blocker(blockers, "policy_status_not_evidence_only", value=policy.get("policy_status"))
    if policy.get("missing_targets") != []:
        append_blocker(blockers, "missing_targets_present", value=policy.get("missing_targets"))
    if policy.get("snapshot_root") != "redacted":
        append_blocker(blockers, "snapshot_root_not_redacted", value=policy.get("snapshot_root"))

    coverage = policy.get("coverage")
    if not isinstance(coverage, dict):
        append_blocker(blockers, "coverage_missing")
        coverage = {}
    else:
        reject_forbidden_claim_fields(
            blockers,
            reason="coverage_unexpected_field",
            mapping=coverage,
            path="coverage",
            allowed_keys=COVERAGE_ALLOWED_KEYS,
        )
    if coverage.get("status") != "complete":
        append_blocker(blockers, "coverage_status_not_complete", value=coverage.get("status"))
    input_targets = require_set(
        blockers,
        reason="input_target_coverage_mismatch",
        actual=coverage.get("input_targets"),
        expected=EXPECTED_INPUT_TARGETS,
    )
    copied_targets = require_set(
        blockers,
        reason="copied_target_coverage_mismatch",
        actual=coverage.get("copied_targets"),
        expected={EXPECTED_COPIED_TARGET},
    )
    copied_fields = require_set(
        blockers,
        reason="copied_field_coverage_mismatch",
        actual=coverage.get("copied_fields"),
        expected={EXPECTED_COPIED_FIELD},
    )
    forbidden_fields = require_set(
        blockers,
        reason="forbidden_field_coverage_mismatch",
        actual=coverage.get("forbidden_fields"),
        expected=EXPECTED_FORBIDDEN_FIELDS,
    )

    validate_copied_bool(policy, blockers)
    forbidden_entry_fields = validate_forbidden_transfer_fields(policy, blockers)
    generated_input_targets = validate_generated_from(policy, blockers)

    safety = policy.get("safety_summary")
    if not isinstance(safety, dict):
        append_blocker(blockers, "safety_summary_missing")
        safety = {}
    else:
        reject_forbidden_claim_fields(
            blockers,
            reason="safety_summary_unexpected_field",
            mapping=safety,
            path="safety_summary",
            allowed_keys=SAFETY_SUMMARY_ALLOWED_KEYS,
        )
    if safety.get("artifact_status") != "evidence_only":
        append_blocker(blockers, "safety_artifact_status_invalid", value=safety.get("artifact_status"))
    if safety.get("promotion_ready") is not False:
        append_blocker(blockers, "safety_promotion_ready_not_false", value=safety.get("promotion_ready"))
    if safety.get("intended_use") != "offline_review_only":
        append_blocker(blockers, "safety_intended_use_invalid", value=safety.get("intended_use"))
    if safety.get("copied_bool_count") != 1:
        append_blocker(blockers, "safety_copied_bool_count_mismatch", value=safety.get("copied_bool_count"))
    if safety.get("forbidden_field_count") != len(EXPECTED_FORBIDDEN_FIELDS):
        append_blocker(blockers, "safety_forbidden_field_count_mismatch", value=safety.get("forbidden_field_count"))
    explicitly_excluded = safety.get("explicitly_excluded")
    if not isinstance(explicitly_excluded, list) or not {"public_sdk", "runtime_hook_wiring", "return_override", "mutation"}.issubset(
        {item for item in explicitly_excluded if isinstance(item, str)}
    ):
        append_blocker(blockers, "safety_explicit_exclusions_missing_required_boundaries")

    non_claims = policy.get("non_claims")
    if not isinstance(non_claims, list):
        append_blocker(blockers, "non_claims_missing")
        non_claims_text = ""
    else:
        non_claims_text = "\n".join(str(item) for item in non_claims)
    for token in REQUIRED_NON_CLAIM_TOKENS:
        if token not in non_claims_text:
            append_blocker(blockers, "required_non_claim_missing", token=token)

    gate_blockers = offline_gate.validate_transfer_baccept_only_policy_slice_manifest(
        policy,
        label="transfer-baccept-readiness",
        mode="consume",
    )
    for blocker in gate_blockers:
        append_blocker(
            blockers,
            str(blocker.get("reason", "offline_artifact_gate_blocker")),
            source="offline_artifact_gate",
            label=blocker.get("label"),
        )
    reject_positive_claim_values(policy, blockers, path="$")
    reject_public_contract_claim_values(policy, blockers, path="$")
    reject_transfer_readiness_alias_overclaims(policy, blockers)

    return {
        "input_targets": sorted(input_targets),
        "copied_targets": sorted(copied_targets),
        "copied_fields": sorted(copied_fields),
        "forbidden_fields": sorted(forbidden_fields),
        "forbidden_transfer_field_entries": forbidden_entry_fields,
        "generated_input_targets": generated_input_targets,
        "copied_bool_count": 1 if isinstance(policy.get("copied_bool"), dict) else 0,
    }


def build_report(
    root_arg: Path,
    manifest_arg: Path | None,
    expected_manifest_sha256: str,
    skip_artifact_gates: bool = False,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    root = safe_path(root_arg, "--root", blockers)
    manifest_path = manifest_arg if manifest_arg is not None else root_arg / DEFAULT_MANIFEST_NAME
    manifest = safe_path(manifest_path, "--manifest", blockers)

    summary: dict[str, Any] = {}
    consume_gate: dict[str, Any] = {"returncode": None, "status": None}
    promote_gate: dict[str, Any] = {"returncode": None, "status": None}
    if root is not None and manifest is not None:
        policy = read_policy(manifest, blockers, expected_manifest_sha256)
        if policy is not None:
            summary = validate_policy(policy, blockers)
        if skip_artifact_gates:
            consume_gate = {"returncode": None, "status": "skipped"}
            promote_gate = {"returncode": None, "status": "skipped", "blocker_reasons": []}
        else:
            consume_rc, consume_payload, consume_stderr = run_gate(root, manifest, "consume")
            consume_gate = {
                "returncode": consume_rc,
                "status": consume_payload.get("status") if isinstance(consume_payload, dict) else None,
                "stderr": consume_stderr,
            }
            if consume_rc != 0 or consume_gate["status"] != "accepted":
                append_blocker(blockers, "consume_gate_not_accepted", returncode=consume_rc, status=consume_gate["status"])
            promote_rc, promote_payload, promote_stderr = run_gate(root, manifest, "promote")
            promote_blockers = (
                promote_payload.get("blockers")
                if isinstance(promote_payload, dict) and isinstance(promote_payload.get("blockers"), list)
                else []
            )
            promote_reasons = sorted(
                blocker.get("reason")
                for blocker in promote_blockers
                if isinstance(blocker, dict) and isinstance(blocker.get("reason"), str)
            )
            promote_gate = {
                "returncode": promote_rc,
                "status": promote_payload.get("status") if isinstance(promote_payload, dict) else None,
                "blocker_reasons": promote_reasons,
                "stderr": promote_stderr,
            }
            required_promote_reasons = {
                "promote_mode_manifest_has_non_claims",
                "promote_mode_transfer_baccept_policy_slice_evidence_only",
            }
            if promote_rc == 0 or promote_gate["status"] != "blocked":
                append_blocker(blockers, "promote_gate_not_blocked", returncode=promote_rc, status=promote_gate["status"])
            if not required_promote_reasons.issubset(set(promote_reasons)):
                append_blocker(
                    blockers,
                    "promote_gate_missing_required_blockers",
                    missing=sorted(required_promote_reasons - set(promote_reasons)),
                )

    ready = not blockers
    beta_capture_guardrail = build_multi_surface_beta_capture_guardrail()
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "remaining_route_blockers": [CURRENT_ROUTE_BLOCKER],
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "candidate_only": True,
        "candidate_only_mode": True,
        "not_artifact_gate": True,
        "consume_only": True,
        "multi_surface_beta_capture_guardrail": beta_capture_guardrail,
        **REPORT_FALSE_FLAGS,
        **REPORT_ZERO_FIELDS,
        "root": str(root if root is not None else root_arg),
        "manifest": str(manifest if manifest is not None else manifest_path),
        "expected_manifest_sha256": expected_manifest_sha256,
        "consume_gate": consume_gate,
        "promote_gate": promote_gate,
        "summary": summary,
        "blockers": blockers,
        "non_claims": REPORT_NON_CLAIMS,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.root, args.manifest, args.expected_manifest_sha256, args.skip_artifact_gates)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
