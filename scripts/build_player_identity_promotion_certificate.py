#!/usr/bin/env python3
"""Build the post-runtime player-identity promotion certificate offline.

The generated certificate is a hash-bound input for the next permissions/admin
planning gate. The builder report itself is non-authorizing and does not claim public
SDK readiness, runtime readiness, P0 progress, v1 completion, or publication.
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
import check_permissions_admin_public_readiness as permissions_readiness
import check_player_identity_public_contract_decision_record as decision_checker
import protected_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = "obelisk.player-identity-promotion-certificate-build-report.v1"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
CERTIFICATE_SCHEMA = permissions_readiness.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
IDENTITY_SURFACE = permissions_readiness.IDENTITY_SURFACE
APPROVED_RUNTIME_SCHEMA = permissions_readiness.PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA
IDENTITY_SDK_CONSUMER_TESTS = ["tests/sdk_consumer/player_identity_plugin.cpp"]
DECISION_RUNTIME_BINDING_DIGEST_SCHEMA = (
    "obelisk.player-identity-promotion-certificate-decision-runtime-binding-digest.v1"
)
DECISION_RUNTIME_BINDING_DIGEST_POLICY = "same-binding-digest-required"
DECISION_RECORD_ARTIFACT_BINDING_SCHEMA = (
    "obelisk.player-identity-promotion-certificate-decision-record-artifact-binding.v1"
)
DECISION_RECORD_ARTIFACT_BINDING_POLICY = "current-hash-required"
POST_RUNTIME_BRIDGE_CONSTRAINT_SCHEMA = (
    "obelisk.player-identity-post-runtime-bridge-constraints.v1"
)
POST_RUNTIME_BRIDGE_SCOPE = "hash_bound_review_bridge_only"
POST_RUNTIME_BRIDGE_CONSTRAINTS = {
    "schema": POST_RUNTIME_BRIDGE_CONSTRAINT_SCHEMA,
    "scope": POST_RUNTIME_BRIDGE_SCOPE,
    "runtime_bundle_resolved_input": decision_checker.ACTIVE_AFTER_RESOLVED_INPUT,
    "runtime_bundle_next_blocker": (
        decision_checker.NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE
    ),
    "runtime_bundle_review_scope": POST_RUNTIME_BRIDGE_SCOPE,
    "public_header_api_abi_sdk_runtime_shortcut_allowed": False,
    "accepted_runtime_evidence_counts_as_reviewed_public_identity_contract": False,
    "accepted_for_public_header_review": False,
    "accepted_for_public_api_review": False,
    "accepted_for_public_abi_review": False,
    "public_header_gate_missing_after_runtime_evidence": False,
    "public_api_gate_missing_after_runtime_evidence": False,
    "public_abi_gate_missing_after_runtime_evidence": False,
    "public_sdk_readiness_after_runtime_evidence": False,
    "runtime_readiness_after_runtime_evidence": False,
    "v1_completion_after_runtime_evidence": False,
    "terminal_certificate": False,
    "terminal_status_certificate": False,
    "terminal_readiness_certificate": False,
    "package_shape_ready": False,
    "installed_sdk_package_shape_ready": False,
    "support_package_ready": False,
    "support_tier_ready": False,
    "support_tier_activation_allowed": False,
    "beta_notice_ready": False,
    "beta_capture_ready": False,
    "runtime_evidence_status_report_ready": False,
    "status_report_ready": False,
    "scoped_release_row_ready": False,
    "counts_toward_public_sdk": False,
    "counts_toward_p0_dependency_chain_claim": False,
    "sdk_progress": 0,
    "p0_progress": 0,
}
NON_CLAIM = (
    "offline player-identity promotion-certificate build only; the builder report does "
    "not authorize live operations, runtime capture, public header/API/ABI, runtime "
    "readiness, public SDK readiness, SDK/P0 progress, stable SDK claims, Plugin Hub, "
    "publication, or v1 completion"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=SURFACES,
        help="Base public SDK surfaces manifest.",
    )
    parser.add_argument(
        "--approved-runtime-evidence",
        type=Path,
        required=True,
        help="Accepted approved runtime lifecycle evidence manifest JSON.",
    )
    parser.add_argument(
        "--identity-public-contract-decision-record",
        type=Path,
        required=True,
        help="Reviewed identity public-contract decision record JSON.",
    )
    parser.add_argument(
        "--output-certificate",
        type=Path,
        required=True,
        help="Repo-local output certificate JSON path.",
    )
    parser.add_argument(
        "--output-surfaces",
        type=Path,
        help="Optional output public-sdk-surfaces JSON with the certificate binding attached.",
    )
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
    try:
        resolved_parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(
            f"{label} parent could not be created: {resolved_parent}: {exc}"
        ) from exc
    if not resolved_parent.is_dir():
        raise SystemExit(f"{label} parent is not a directory: {resolved_parent}")
    return protected_paths.reject_protected_output_path(path, label)


def repo_local_output_file(path: Path, label: str) -> Path:
    resolved = safe_output_file(path, label)
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise SystemExit(
            f"{label} must be under the Obelisk repo root so downstream checkers can "
            f"consume a repo-relative path: {resolved}"
        ) from exc
    return resolved


def repo_relative_binding(path: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "sha256": sha256_file(path),
    }


def decision_record_artifact_binding(
    *,
    decision_record: dict[str, Any],
    decision_record_path: Path,
) -> dict[str, str]:
    resolved = safe_input_file(
        decision_record_path,
        "--identity-public-contract-decision-record",
    )
    validate_current_json_payload(
        payload=decision_record,
        path=resolved,
        label="--identity-public-contract-decision-record",
    )
    return {
        "schema": DECISION_RECORD_ARTIFACT_BINDING_SCHEMA,
        "policy": DECISION_RECORD_ARTIFACT_BINDING_POLICY,
        "sha256": sha256_file(resolved),
        "canonical_payload_sha256": permissions_readiness.canonical_json_sha256(
            decision_record
        ),
    }


def load_json_file(path: Path, label: str) -> dict[str, Any]:
    resolved = safe_input_file(path, label)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object: {resolved}")
    return payload


def validate_current_json_payload(
    *,
    payload: dict[str, Any],
    path: Path | None,
    label: str,
) -> None:
    if path is None:
        return
    current_payload = load_json_file(path, label)
    if (
        permissions_readiness.canonical_json_sha256(payload)
        != permissions_readiness.canonical_json_sha256(current_payload)
    ):
        raise SystemExit(
            f"{label} payload is stale or mismatched with the current file: {path}"
        )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def blocker_summary(blockers: list[dict[str, Any]], *, limit: int = 8) -> str:
    return ", ".join(
        f"{blocker.get('reason')}:{blocker.get('label')}" for blocker in blockers[:limit]
    )


def validate_decision_record(record: dict[str, Any]) -> dict[str, Any]:
    blockers = decision_checker.validate_record(record, check_mode="consume")
    report = decision_checker.build_report(record, blockers, check_mode="consume")
    if blockers:
        reasons = ", ".join(
            f"{blocker['reason']}:{blocker['label']}" for blocker in blockers[:8]
        )
        raise SystemExit(f"identity public-contract decision record failed validation: {reasons}")
    return report


def validate_strict_approved_runtime_evidence(
    approved_runtime_evidence: dict[str, Any],
    *,
    approved_runtime_path: Path | None = None,
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
    report_blockers: list[dict[str, Any]] = []
    decision_checker.validate_strict_check_report_payload(report, report_blockers)
    if report_blockers:
        raise SystemExit(
            "strict approved-runtime checker report failed public-contract compatibility: "
            f"{blocker_summary(report_blockers)}"
        )
    return report


def compact_value(value: Any) -> str:
    rendered = repr(value)
    if len(rendered) > 120:
        return rendered[:117] + "..."
    return rendered


def first_binding_mismatches(
    *,
    expected: Any,
    actual: Any,
    label: str = "$.approved_runtime_evidence_binding",
    limit: int = 8,
) -> list[str]:
    if limit <= 0 or expected == actual:
        return []
    if type(expected) is not type(actual):
        return [
            f"{label}: expected {type(expected).__name__}, got {type(actual).__name__}"
        ]
    if isinstance(expected, dict):
        mismatches: list[str] = []
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            mismatches.append(f"{label}.{key}: missing")
            if len(mismatches) >= limit:
                return mismatches
        for key in sorted(actual_keys - expected_keys):
            mismatches.append(f"{label}.{key}: unexpected")
            if len(mismatches) >= limit:
                return mismatches
        for key in sorted(expected_keys & actual_keys):
            mismatches.extend(
                first_binding_mismatches(
                    expected=expected[key],
                    actual=actual[key],
                    label=f"{label}.{key}",
                    limit=limit - len(mismatches),
                )
            )
            if len(mismatches) >= limit:
                return mismatches
        return mismatches
    if isinstance(expected, list):
        mismatches = []
        if len(expected) != len(actual):
            mismatches.append(
                f"{label}: expected list length {len(expected)}, got {len(actual)}"
            )
            if len(mismatches) >= limit:
                return mismatches
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            mismatches.extend(
                first_binding_mismatches(
                    expected=expected_item,
                    actual=actual_item,
                    label=f"{label}[{index}]",
                    limit=limit - len(mismatches),
                )
            )
            if len(mismatches) >= limit:
                return mismatches
        return mismatches
    return [f"{label}: expected {compact_value(expected)}, got {compact_value(actual)}"]


def decision_record_runtime_binding_digest(
    *,
    decision_record: dict[str, Any],
    approved_runtime_evidence: dict[str, Any],
) -> dict[str, str]:
    decision_binding = decision_record.get(
        decision_checker.APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD
    )
    if not isinstance(decision_binding, dict):
        raise SystemExit(
            "identity public-contract decision record missing approved runtime "
            "evidence binding"
        )
    runtime_binding = decision_checker.approved_runtime_evidence_binding_from_manifest(
        approved_runtime_evidence
    )
    return {
        "schema": DECISION_RUNTIME_BINDING_DIGEST_SCHEMA,
        "policy": DECISION_RUNTIME_BINDING_DIGEST_POLICY,
        "decision_record_approved_runtime_evidence_binding_sha256": (
            permissions_readiness.canonical_json_sha256(decision_binding)
        ),
        "approved_runtime_evidence_binding_sha256": (
            permissions_readiness.canonical_json_sha256(runtime_binding)
        ),
    }


def validate_decision_record_runtime_binding(
    *,
    decision_record: dict[str, Any],
    approved_runtime_evidence: dict[str, Any],
) -> dict[str, str]:
    decision_binding = decision_record.get(
        decision_checker.APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD
    )
    if not isinstance(decision_binding, dict):
        raise SystemExit(
            "identity public-contract decision record missing approved runtime "
            "evidence binding"
        )
    runtime_binding = decision_checker.approved_runtime_evidence_binding_from_manifest(
        approved_runtime_evidence
    )
    mismatches = first_binding_mismatches(
        expected=runtime_binding,
        actual=decision_binding,
    )
    if mismatches:
        raise SystemExit(
            "identity public-contract decision record is not hash-bound to "
            "--approved-runtime-evidence: "
            + "; ".join(mismatches)
        )
    digest = decision_record_runtime_binding_digest(
        decision_record=decision_record,
        approved_runtime_evidence=approved_runtime_evidence,
    )
    if (
        digest["decision_record_approved_runtime_evidence_binding_sha256"]
        != digest["approved_runtime_evidence_binding_sha256"]
    ):
        raise SystemExit(
            "identity public-contract decision record approved runtime binding digest "
            "mismatch"
        )
    return digest


def validate_decision_record_runtime_manifest_ref(
    *,
    decision_record: dict[str, Any],
    approved_runtime_path: Path | None,
) -> None:
    if approved_runtime_path is None:
        return
    manifest_ref = decision_record.get(
        decision_checker.APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD
    )
    if not isinstance(manifest_ref, dict):
        raise SystemExit(
            "identity public-contract decision record missing approved runtime "
            "evidence manifest ref"
        )
    ref_path = manifest_ref.get("path")
    if not isinstance(ref_path, str) or not ref_path:
        raise SystemExit(
            "identity public-contract decision record approved runtime evidence "
            "manifest ref path is missing"
        )
    expected_path = safe_input_file(approved_runtime_path, "--approved-runtime-evidence")
    observed_path = Path(ref_path).expanduser()
    if not observed_path.is_absolute():
        observed_path = REPO_ROOT / observed_path
    observed_path = safe_input_file(
        observed_path,
        "--identity-public-contract-decision-record approved runtime evidence manifest ref",
    )
    if observed_path != expected_path:
        raise SystemExit(
            "identity public-contract decision record approved runtime evidence "
            "manifest ref does not match --approved-runtime-evidence: "
            f"expected {expected_path}, got {observed_path}"
        )
    expected_sha256 = sha256_file(expected_path)
    observed_sha256 = manifest_ref.get("sha256")
    if observed_sha256 != expected_sha256:
        raise SystemExit(
            "identity public-contract decision record approved runtime evidence "
            "manifest ref hash does not match --approved-runtime-evidence"
        )


def post_runtime_bridge_constraints() -> dict[str, Any]:
    return copy.deepcopy(POST_RUNTIME_BRIDGE_CONSTRAINTS)


def validate_post_runtime_bridge_constraints(
    payload: dict[str, Any],
    *,
    label: str,
) -> None:
    observed = payload.get("post_runtime_bridge_constraints")
    if observed != POST_RUNTIME_BRIDGE_CONSTRAINTS:
        mismatches = first_binding_mismatches(
            expected=POST_RUNTIME_BRIDGE_CONSTRAINTS,
            actual=observed,
            label=f"{label}.post_runtime_bridge_constraints",
        )
        raise SystemExit(
            "post-runtime bridge constraints mismatch: " + "; ".join(mismatches)
        )


def validate_identity_surface_post_runtime_bridge_constraints(
    identity_surface: dict[str, Any],
) -> None:
    validate_post_runtime_bridge_constraints(
        identity_surface,
        label="$.identity_surface",
    )
    evidence = identity_surface.get("evidence")
    if not isinstance(evidence, dict):
        raise SystemExit("$.identity_surface.evidence missing evidence object")
    validate_post_runtime_bridge_constraints(
        evidence,
        label="$.identity_surface.evidence",
    )


def runtime_evidence_summary(approved_runtime_evidence: dict[str, Any]) -> dict[str, str]:
    if approved_runtime_evidence.get("schema") != APPROVED_RUNTIME_SCHEMA:
        raise SystemExit(
            "--approved-runtime-evidence schema mismatch: "
            f"expected {APPROVED_RUNTIME_SCHEMA}, got {approved_runtime_evidence.get('schema')}"
        )
    return {
        "schema": APPROVED_RUNTIME_SCHEMA,
        "result": "approved runtime principal lifecycle evidence",
        "next_blocker": permissions_readiness.IDENTITY_CONTRACT_ROUTE_BLOCKER,
    }


def accepted_runtime_evidence_record(approved_runtime_evidence: dict[str, Any]) -> dict[str, Any]:
    summary = runtime_evidence_summary(approved_runtime_evidence)
    binding = dict(permissions_readiness.APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES)
    binding.update(
        {key: False for key in permissions_readiness.APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS}
    )
    binding["non_claim"] = (
        "approved runtime evidence is a contract-review input only and cannot unlock "
        "public header, API, ABI, SDK, runtime, stable, Plugin Hub, publication, or P0 claims"
    )
    return {
        **summary,
        "approved_runtime_evidence_binding_required": True,
        "approved_runtime_evidence_binding": binding,
    }


def identity_surface_from_manifest(surfaces: dict[str, Any]) -> dict[str, Any]:
    entries = surfaces.get("surfaces")
    if not isinstance(entries, list):
        raise SystemExit("--public-sdk-surfaces must contain a surfaces list")
    for surface in entries:
        if isinstance(surface, dict) and surface.get("id") == IDENTITY_SURFACE:
            return surface
    raise SystemExit(f"--public-sdk-surfaces missing {IDENTITY_SURFACE}")


def reviewed_contract_record_for_certificate(
    *,
    source_record: dict[str, Any],
    reviewed_surface_hash: str,
) -> dict[str, Any]:
    record = {
        "schema": permissions_readiness.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
        "artifact_id": permissions_readiness.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
        "surface": IDENTITY_SURFACE,
        "active_after_resolved_input": (
            permissions_readiness.PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT
        ),
        "review_status": "reviewed",
        "accepted_for_contract_review": True,
        "next_blocker": permissions_readiness.PUBLIC_HEADER_ROUTE_BLOCKER,
        "reviewed_surface_record_sha256": reviewed_surface_hash,
        "resolved_decision_keys": list(
            permissions_readiness.REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS
        ),
    }
    for key in permissions_readiness.REQUIRED_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS:
        record[key] = False
    for key, expected in permissions_readiness.REQUIRED_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS.items():
        record[key] = expected
    source_artifacts = source_record.get("source_artifacts")
    if isinstance(source_artifacts, dict):
        record["source_artifact_sha256"] = permissions_readiness.canonical_json_sha256(
            source_artifacts
        )
    return record


def promote_identity_surface_for_certificate(
    *,
    surfaces: dict[str, Any],
    approved_runtime_evidence: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    promoted_surfaces = copy.deepcopy(surfaces)
    identity = identity_surface_from_manifest(promoted_surfaces)
    identity["status"] = "promoted"
    identity["support_tier"] = "release-supported copied principal"
    identity["capabilities"] = sorted(permissions_readiness.REQUIRED_IDENTITY_CAPABILITIES)
    identity["public_contract"] = sorted(permissions_readiness.REQUIRED_IDENTITY_PUBLIC_CONTRACT)
    identity["public_fields"] = sorted(
        {"abi_version", "struct_size", *permissions_readiness.REQUIRED_IDENTITY_PUBLIC_FIELDS}
    )
    identity["abi_contract"] = sorted(permissions_readiness.REQUIRED_IDENTITY_PUBLIC_ABI_CONTRACT)
    identity["lifecycle_contract"] = sorted(permissions_readiness.REQUIRED_IDENTITY_LIFECYCLE_CONTRACT)
    evidence = identity.setdefault("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
        identity["evidence"] = evidence
    evidence["accepted_runtime_evidence"] = accepted_runtime_evidence_record(
        approved_runtime_evidence
    )
    evidence["sdk_consumer_tests"] = list(IDENTITY_SDK_CONSUMER_TESTS)
    evidence["post_runtime_bridge_constraints"] = post_runtime_bridge_constraints()
    identity["post_runtime_bridge_constraints"] = post_runtime_bridge_constraints()
    decision_contract = identity.setdefault("v1_decision_contract", {})
    if not isinstance(decision_contract, dict):
        decision_contract = {}
        identity["v1_decision_contract"] = decision_contract
    decision_contract["current_decision"] = "promoted_public_contract"
    decision_contract["must_remain_without_public_contract_until_promotion"] = False
    blockers = identity.get("blockers")
    if isinstance(blockers, list):
        identity["blockers"] = [
            blocker
            for blocker in blockers
            if blocker != "No approved runtime principal lifecycle evidence."
        ]
    return promoted_surfaces, identity


def build_certificate(
    *,
    identity_surface: dict[str, Any],
    approved_runtime_evidence: dict[str, Any],
    approved_runtime_path: Path | None = None,
    decision_record: dict[str, Any],
    decision_record_path: Path | None = None,
) -> dict[str, Any]:
    if decision_record_path is None:
        raise SystemExit(
            "player identity promotion certificate requires a current "
            "--identity-public-contract-decision-record file binding"
        )
    validate_current_json_payload(
        payload=approved_runtime_evidence,
        path=approved_runtime_path,
        label="--approved-runtime-evidence",
    )
    validate_current_json_payload(
        payload=decision_record,
        path=decision_record_path,
        label="--identity-public-contract-decision-record",
    )
    validate_identity_surface_post_runtime_bridge_constraints(identity_surface)
    runtime_evidence_summary(approved_runtime_evidence)
    validate_strict_approved_runtime_evidence(
        approved_runtime_evidence,
        approved_runtime_path=approved_runtime_path,
    )
    validate_decision_record(decision_record)
    runtime_binding_digest = validate_decision_record_runtime_binding(
        decision_record=decision_record,
        approved_runtime_evidence=approved_runtime_evidence,
    )
    validate_decision_record_runtime_manifest_ref(
        decision_record=decision_record,
        approved_runtime_path=approved_runtime_path,
    )
    decision_record_binding = decision_record_artifact_binding(
        decision_record=decision_record,
        decision_record_path=decision_record_path,
    )
    reviewed_surface_hash = permissions_readiness.player_identity_surface_record_sha256(
        identity_surface
    )
    review_record = reviewed_contract_record_for_certificate(
        source_record=decision_record,
        reviewed_surface_hash=reviewed_surface_hash,
    )
    evidence = {
        "reviewed_artifact_hash": reviewed_surface_hash,
        "reviewed_surface_record_sha256": reviewed_surface_hash,
        "promotion_evidence_kind": permissions_readiness.REQUIRED_CERTIFICATE_PROMOTION_EVIDENCE_KIND,
        "post_runtime_bridge_constraints": post_runtime_bridge_constraints(),
        "approved_runtime_evidence": runtime_evidence_summary(approved_runtime_evidence),
        "public_contract": sorted(permissions_readiness.REQUIRED_IDENTITY_PUBLIC_CONTRACT),
        "capabilities": sorted(permissions_readiness.REQUIRED_IDENTITY_CAPABILITIES),
        "public_fields": sorted(
            {"abi_version", "struct_size", *permissions_readiness.REQUIRED_IDENTITY_PUBLIC_FIELDS}
        ),
        "abi_contract": sorted(permissions_readiness.REQUIRED_IDENTITY_PUBLIC_ABI_CONTRACT),
        "lifecycle_contract": sorted(permissions_readiness.REQUIRED_IDENTITY_LIFECYCLE_CONTRACT),
        "sdk_consumer_tests": list(IDENTITY_SDK_CONSUMER_TESTS),
        "semantic_proofs": sorted(permissions_readiness.REQUIRED_CERTIFICATE_SEMANTIC_PROOFS),
        "identity_public_contract_decision_record": review_record,
        "identity_public_contract_decision_record_sha256": (
            permissions_readiness.canonical_json_sha256(review_record)
        ),
        "identity_public_contract_decision_record_artifact": decision_record_binding,
        "identity_public_contract_decision_record_payload_sha256": (
            decision_record_binding["canonical_payload_sha256"]
        ),
        "identity_public_contract_decision_record_runtime_binding": runtime_binding_digest,
    }
    for key in permissions_readiness.REQUIRED_CERTIFICATE_FALSE_KEYS:
        evidence[key] = False
    return {
        "schema": CERTIFICATE_SCHEMA,
        "surface_id": IDENTITY_SURFACE,
        "promotion_status": "promoted",
        "post_runtime_bridge_constraints": post_runtime_bridge_constraints(),
        "v1_dependency_chain": list(permissions_readiness.REQUIRED_P0_CHAIN),
        "chain_position": 1,
        "v1_dependency_chain_position": 1,
        "required_by_surface": permissions_readiness.SURFACE,
        "required_by_chain_position": 2,
        "required_by_v1_dependency_chain_position": 2,
        **permissions_readiness.REQUIRED_PLAYER_IDENTITY_CERTIFICATE_BINDING_POLICY,
        "evidence": evidence,
    }


def validate_certificate_binding(identity_surface: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    valid = permissions_readiness.player_identity_has_promotion_certificate(
        identity_surface,
        blockers,
    )
    return valid, blockers


def main() -> int:
    args = parse_args()
    surfaces = load_json_file(args.public_sdk_surfaces, "--public-sdk-surfaces")
    approved_runtime_path = safe_input_file(
        args.approved_runtime_evidence,
        "--approved-runtime-evidence",
    )
    approved_runtime_evidence = load_json_file(
        approved_runtime_path,
        "--approved-runtime-evidence",
    )
    decision_record = load_json_file(
        args.identity_public_contract_decision_record,
        "--identity-public-contract-decision-record",
    )

    certificate_path = repo_local_output_file(args.output_certificate, "--output-certificate")
    surfaces_output = (
        safe_output_file(args.output_surfaces, "--output-surfaces")
        if args.output_surfaces is not None
        else None
    )
    promoted_surfaces, identity_surface = promote_identity_surface_for_certificate(
        surfaces=surfaces,
        approved_runtime_evidence=approved_runtime_evidence,
    )
    certificate = build_certificate(
        identity_surface=identity_surface,
        approved_runtime_evidence=approved_runtime_evidence,
        approved_runtime_path=approved_runtime_path,
        decision_record=decision_record,
        decision_record_path=args.identity_public_contract_decision_record,
    )
    write_json(certificate_path, certificate)
    binding = repo_relative_binding(certificate_path)
    identity_surface.setdefault("evidence", {})["player_identity_promotion_certificate"] = binding
    binding_valid, binding_blockers = validate_certificate_binding(identity_surface)
    if not binding_valid:
        raise SystemExit(
            "generated player identity promotion certificate failed validation: "
            + ", ".join(blocker["reason"] for blocker in binding_blockers[:8])
        )
    if surfaces_output is not None:
        write_json(surfaces_output, promoted_surfaces)
    build_report = {
        "schema": REPORT_SCHEMA,
        "status": "built",
        "certificate_artifact_schema": CERTIFICATE_SCHEMA,
        "certificate_path": str(certificate_path),
        "certificate_sha256": sha256_file(certificate_path),
        "certificate_binding": binding,
        "output_surfaces_path": str(surfaces_output) if surfaces_output is not None else None,
        "identity_surface_certificate_binding_valid": binding_valid,
        "identity_surface_certificate_binding_blockers": binding_blockers,
        "ready": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_sdk_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "sdk_progress": 0,
        "p0_progress": 0,
        "non_claim": NON_CLAIM,
        "post_runtime_bridge_constraints": post_runtime_bridge_constraints(),
    }
    if args.json:
        print(json.dumps(build_report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
