#!/usr/bin/env python3
"""Build a non-authorizing permissions/admin post-identity certificate offline.

The generated certificate is hash-bound to a public SDK surfaces manifest that
already carries a valid player-identity promotion certificate, the
permissions/admin decisions manifest, and the candidate-only query fail-closed
contract. It does not open public headers/API/ABI and does not count toward SDK,
runtime, P0, stable, publication, or v1 completion claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import check_permissions_admin_public_readiness as permissions_readiness
import check_permissions_admin_query_failclosed_contract as query_contract
import protected_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
QUERY_FAILCLOSED_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REPORT_SCHEMA = "obelisk.permissions-admin-promotion-certificate-build-report.v1"
CERTIFICATE_SCHEMA = "obelisk.permissions-admin-promotion-certificate.v1"
CERTIFICATE_EVIDENCE_KIND = "permissions_admin_post_identity_query_only_certificate"
SURFACE = permissions_readiness.SURFACE
IDENTITY_SURFACE = permissions_readiness.IDENTITY_SURFACE
COMMAND_RESPONSE_SURFACE = permissions_readiness.COMMAND_RESPONSE_SURFACE
PUBLIC_HEADER_ROUTE_BLOCKER = permissions_readiness.PUBLIC_HEADER_ROUTE_BLOCKER
HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS = frozenset(("path", "sha256"))
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH = (
    permissions_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH
)
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY = (
    permissions_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY
)
NON_CLAIM = (
    "offline permissions/admin post-identity certificate build only; the certificate "
    "does not authorize live operations, runtime capture, public header/API/ABI, "
    "runtime readiness, public SDK readiness, SDK/P0 progress, stable SDK claims, "
    "Plugin Hub, publication, or v1 completion"
)
FALSE_KEYS = (
    "ready",
    "approved_runtime_evidence",
    "promotion_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk",
    "public_sdk_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "stable_sdk",
    "stable_sdk_ready",
    "complete_sdk",
    "p0",
    "support_tier",
    "plugin_hub",
    "plugin_hub_ready",
    "package_shape",
    "beta",
    "discord",
    "passive_snapshot",
    "scoped_release_statement",
    "publication_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "public_or_runtime_accounting_allowed",
    "route_ready",
    "public_route_ready",
    "permissions_admin_route_ready",
    "counts_toward_permissions_admin",
    "permissions_admin_unlock_allowed",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
)
ZERO_KEYS = (
    "sdk_progress",
    "p0_progress",
    "complete_sdk_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=SURFACES,
        help="Public SDK surfaces manifest that already includes the identity certificate binding.",
    )
    parser.add_argument(
        "--permissions-decisions",
        type=Path,
        default=DECISIONS,
        help="Permissions/admin public contract decisions manifest.",
    )
    parser.add_argument(
        "--query-failclosed-contract",
        type=Path,
        default=QUERY_FAILCLOSED_CONTRACT,
        help="Candidate-only permissions/admin query fail-closed contract.",
    )
    parser.add_argument(
        "--output-certificate",
        type=Path,
        required=True,
        help="Repo-local output certificate JSON path.",
    )
    parser.add_argument(
        "--current-route-blocker",
        default=PUBLIC_HEADER_ROUTE_BLOCKER,
        choices=permissions_readiness.ALLOWED_ROUTE_BLOCKERS,
        help="Route blocker to validate for this post-identity builder.",
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
            f"{label} must be under the Obelisk repo root so downstream offline "
            f"checkers can consume a repo-relative path: {resolved}"
        ) from exc
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def blocker_summary(blockers: list[dict[str, Any]], *, limit: int = 8) -> str:
    return ", ".join(
        f"{blocker.get('reason')}:{blocker.get('label')}" for blocker in blockers[:limit]
    )


def repo_relative_or_resolved(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def artifact_binding(path: Path, *, schema: str | None = None) -> dict[str, str]:
    binding = {
        "path": repo_relative_or_resolved(path),
        "sha256": sha256_file(path),
    }
    if schema is not None:
        binding["schema"] = schema
    return binding


def canonical_query_failclosed_contract_binding() -> dict[str, str]:
    return artifact_binding(
        QUERY_FAILCLOSED_CONTRACT,
        schema=query_contract.SCHEMA,
    )


def query_failclosed_contract_currentness_blockers(query_path: Path) -> list[dict[str, Any]]:
    value_binding = artifact_binding(query_path, schema=query_contract.SCHEMA)
    current_binding = canonical_query_failclosed_contract_binding()
    if value_binding == current_binding:
        return []
    return [
        {
            "reason": "permissions_admin_query_failclosed_contract_not_current",
            "label": "$.query_failclosed_contract",
            "expected": current_binding,
            "value": value_binding,
        }
    ]


def hash_bound_certificate_binding_keys(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        {permissions_readiness.normalized_key(key) for key in value}
        == HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS
    )


def canonical_player_identity_certificate_binding(
    identity_surface: dict[str, Any],
) -> dict[str, str] | None:
    if not permissions_readiness.player_identity_has_promotion_certificate(identity_surface):
        return None
    evidence = identity_surface.get("evidence")
    binding = (
        evidence.get("player_identity_promotion_certificate")
        if isinstance(evidence, dict)
        else None
    )
    if not isinstance(binding, dict):
        return None
    if not hash_bound_certificate_binding_keys(binding):
        return None
    relative = permissions_readiness.repo_relative_path(binding.get("path"))
    if relative is None:
        return None
    path = REPO_ROOT / relative
    protected_paths.reject_symlink_component(path, "player identity promotion certificate")
    resolved = protected_paths.reject_protected_input_path(
        path,
        "player identity promotion certificate",
    )
    return {
        "path": str(relative),
        "sha256": sha256_file(resolved),
    }


def surface_record_hash(surface: dict[str, Any]) -> str:
    return permissions_readiness.canonical_json_sha256(surface)


def add_builder_blocker(
    blockers: list[dict[str, Any]],
    reason: str,
    label: str,
    **extra: Any,
) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def current_json_payload_blockers(
    *,
    payload: dict[str, Any],
    path: Path,
    artifact_label: str,
    reason: str,
    label: str,
) -> list[dict[str, Any]]:
    current_payload = load_json_file(path, artifact_label)
    if (
        permissions_readiness.canonical_json_sha256(payload)
        == permissions_readiness.canonical_json_sha256(current_payload)
    ):
        return []
    return [
        {
            "reason": reason,
            "label": label,
            "path": repo_relative_or_resolved(path),
            "expected_current_sha256": permissions_readiness.canonical_json_sha256(
                current_payload
            ),
            "value_sha256": permissions_readiness.canonical_json_sha256(payload),
        }
    ]


def readiness_currentness_blockers(
    *,
    readiness: dict[str, Any],
    surfaces_path: Path,
    decisions_path: Path,
    query_path: Path,
) -> list[dict[str, Any]]:
    current_route_blocker = readiness.get("current_route_blocker")
    if not isinstance(current_route_blocker, str):
        return [
            {
                "reason": "permissions_admin_public_readiness_report_current_route_blocker_missing",
                "label": "$.permissions_admin_public_readiness.current_route_blocker",
                "value": current_route_blocker,
            }
        ]
    current_readiness = readiness_report(
        surfaces_path=surfaces_path,
        decisions_path=decisions_path,
        query_path=query_path,
        current_route_blocker=current_route_blocker,
    )
    if (
        permissions_readiness.canonical_json_sha256(readiness)
        == permissions_readiness.canonical_json_sha256(current_readiness)
    ):
        return []
    return [
        {
            "reason": "permissions_admin_public_readiness_report_stale_or_mismatched",
            "label": "$.permissions_admin_public_readiness",
            "expected_current_sha256": permissions_readiness.canonical_json_sha256(
                current_readiness
            ),
            "value_sha256": permissions_readiness.canonical_json_sha256(readiness),
        }
    ]


def permissions_surface_from_manifest(surfaces: dict[str, Any]) -> dict[str, Any] | None:
    return permissions_readiness.surface_by_id(surfaces, SURFACE)


def identity_surface_from_manifest(surfaces: dict[str, Any]) -> dict[str, Any] | None:
    return permissions_readiness.surface_by_id(surfaces, IDENTITY_SURFACE)


def query_validation_report(query_payload: dict[str, Any]) -> dict[str, Any]:
    validation = query_contract.validate_manifest(query_payload, check_mode="consume")
    return query_contract.build_report(query_payload, validation, check_mode="consume")


def readiness_report(
    *,
    surfaces_path: Path,
    decisions_path: Path,
    query_path: Path,
    current_route_blocker: str,
) -> dict[str, Any]:
    return permissions_readiness.build_report(
        argparse.Namespace(
            decisions=decisions_path,
            surfaces=surfaces_path,
            public_header=PUBLIC_HEADER,
            query_failclosed_artifact=query_path,
            beta_capture_artifact=None,
            current_route_blocker=current_route_blocker,
        )
    )


def preflight_blockers(
    *,
    surfaces: dict[str, Any],
    query_report: dict[str, Any],
    readiness: dict[str, Any],
    public_header_path: Path = PUBLIC_HEADER,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    permissions_readiness.validate_surfaces(surfaces, blockers, public_header_path)
    identity = identity_surface_from_manifest(surfaces)
    if not isinstance(identity, dict):
        add_builder_blocker(blockers, "player_identity_surface_missing", "$.surfaces")
    else:
        evidence = identity.get("evidence")
        binding = (
            evidence.get("player_identity_promotion_certificate")
            if isinstance(evidence, dict)
            else None
        )
        binding_keys_valid = True
        if isinstance(binding, dict) and not hash_bound_certificate_binding_keys(binding):
            binding_keys_valid = False
            add_builder_blocker(
                blockers,
                "player_identity_promotion_certificate_binding_keys_mismatch",
                "$.surfaces[player_identity].evidence.player_identity_promotion_certificate",
                expected=sorted(HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS),
                value=sorted(str(key) for key in binding),
            )
        identity_certificate_blockers: list[dict[str, Any]] = []
        identity_promoted = (
            binding_keys_valid
            and identity.get("status") == "promoted"
            and permissions_readiness.player_identity_has_promoted_public_contract(
                identity,
                identity_certificate_blockers,
            )
        )
        if not identity_promoted:
            if identity_certificate_blockers:
                blockers.extend(identity_certificate_blockers)
            else:
                add_builder_blocker(
                    blockers,
                    "player_identity_promotion_certificate_missing_or_invalid",
                    "$.surfaces[player_identity].evidence.player_identity_promotion_certificate",
                )

    if query_report.get("valid") is not True:
        for detail in query_report.get("blocker_details", []):
            if isinstance(detail, dict):
                blockers.append(
                    {
                        "reason": "query_failclosed_contract_invalid",
                        "label": detail.get("label", "$.query_failclosed_contract"),
                        "source_reason": detail.get("reason"),
                    }
                )

    if readiness.get("valid") is not True:
        for detail in readiness.get("blocker_details", []):
            if isinstance(detail, dict):
                blockers.append(detail)
    if readiness.get("accepted_for_planning") is not True:
        add_builder_blocker(
            blockers,
            "permissions_admin_readiness_not_accepted_for_planning",
            "$.permissions_admin_public_readiness.accepted_for_planning",
            value=readiness.get("accepted_for_planning"),
            required_query_failclosed_schema=query_contract.SCHEMA,
        )
    if readiness.get("query_failclosed_artifact_schema") != query_contract.SCHEMA:
        add_builder_blocker(
            blockers,
            "permissions_admin_readiness_query_failclosed_artifact_not_accepted",
            "$.permissions_admin_public_readiness.query_failclosed_artifact_schema",
            value=readiness.get("query_failclosed_artifact_schema"),
            expected=query_contract.SCHEMA,
        )

    return blockers


def build_certificate(
    *,
    surfaces: dict[str, Any],
    surfaces_path: Path,
    decisions_path: Path,
    query_path: Path,
    query_report: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    blockers = (
        current_json_payload_blockers(
            payload=surfaces,
            path=surfaces_path,
            artifact_label="--public-sdk-surfaces",
            reason="public_sdk_surfaces_loaded_payload_stale_or_mismatched",
            label="$.public_sdk_surfaces",
        )
        + query_failclosed_contract_currentness_blockers(query_path)
        + readiness_currentness_blockers(
            readiness=readiness,
            surfaces_path=surfaces_path,
            decisions_path=decisions_path,
            query_path=query_path,
        )
        + preflight_blockers(
            surfaces=surfaces,
            query_report=query_report,
            readiness=readiness,
            public_header_path=PUBLIC_HEADER,
        )
    )
    if blockers:
        raise SystemExit(
            "permissions/admin promotion certificate inputs failed preflight: "
            f"{blocker_summary(blockers)}"
        )

    permissions_surface = permissions_surface_from_manifest(surfaces)
    identity_surface = identity_surface_from_manifest(surfaces)
    if not isinstance(permissions_surface, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.permissions_admin.v1")
    if not isinstance(identity_surface, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.player_identity.v1")

    identity_certificate_binding = canonical_player_identity_certificate_binding(identity_surface)
    if identity_certificate_binding is None:
        raise SystemExit(
            "--public-sdk-surfaces player_identity promotion certificate binding is "
            "not hash-bound to a repo-local artifact"
        )
    input_bindings: dict[str, Any] = {
        "public_sdk_surfaces": artifact_binding(
            surfaces_path,
            schema=permissions_readiness.SURFACES_SCHEMA,
        ),
        "permissions_admin_surface_record_sha256": surface_record_hash(permissions_surface),
        "player_identity_surface_record_sha256": (
            permissions_readiness.player_identity_surface_record_sha256(identity_surface)
        ),
        "player_identity_promotion_certificate": identity_certificate_binding,
        "permissions_admin_public_contract_decisions": artifact_binding(
            decisions_path,
            schema=permissions_readiness.DECISIONS_SCHEMA,
        ),
        "permissions_admin_query_failclosed_contract": artifact_binding(
            query_path,
            schema=query_contract.SCHEMA,
        ),
        "permissions_admin_public_readiness_report_sha256": (
            permissions_readiness.canonical_json_sha256(readiness)
        ),
        "query_failclosed_contract_report_sha256": (
            permissions_readiness.canonical_json_sha256(query_report)
        ),
    }

    evidence = {
        "promotion_evidence_kind": CERTIFICATE_EVIDENCE_KIND,
        "input_binding_sha256": permissions_readiness.canonical_json_sha256(input_bindings),
        "player_identity_certificate_validated": True,
        "permissions_decisions_validated": True,
        "query_failclosed_contract_validated": True,
        "query_failclosed_contract_accepted_for_planning": True,
        "readiness_checker_valid": True,
        "readiness_checker_accepted_for_planning": readiness.get("accepted_for_planning") is True,
        "query_fields": query_report.get("query_fields", []),
        "decision_fields": query_report.get("decision_fields", []),
        "decisions": query_report.get("decisions", []),
        "policy_provenance_fields": query_report.get("provenance_fields", []),
        "fail_closed_cases": query_report.get("fail_closed_cases", []),
        "recognized_authority_kinds": query_report.get("recognized_authority_kinds", []),
        "allow_capable_authority_kinds": query_report.get("allow_capable_authority_kinds", []),
    }
    evidence.update({key: False for key in FALSE_KEYS})
    evidence.update({key: 0 for key in ZERO_KEYS})

    certificate = {
        "schema": CERTIFICATE_SCHEMA,
        "surface_id": SURFACE,
        "certificate_status": "built",
        "promotion_status": "blocked_public_header_gate_missing",
        "planning_only": True,
        "non_authorizing": True,
        "dependency_chain": list(permissions_readiness.REQUIRED_P0_CHAIN),
        "v1_dependency_chain_position": 2,
        "depends_on_surface": IDENTITY_SURFACE,
        "route_blocker_to_use": PUBLIC_HEADER_ROUTE_BLOCKER,
        "remaining_route_blockers": [PUBLIC_HEADER_ROUTE_BLOCKER],
        "unresolved_technical_blocker": {
            "reason": PUBLIC_HEADER_ROUTE_BLOCKER,
            "label": "include/obelisk/ObeliskApi.h",
            "next_requirement": permissions_readiness.REQUIRED_POST_IDENTITY_NEXT_REQUIREMENT_ID,
            "required_public_surface": (
                permissions_readiness.REQUIRED_ALLOWED_PUBLIC_SURFACE_AFTER_IDENTITY
            ),
            "public_header_allowed": False,
            "public_abi_ready": False,
        },
        "input_bindings": input_bindings,
        "evidence": evidence,
        "non_claim": NON_CLAIM,
    }
    certificate.update({key: False for key in FALSE_KEYS})
    certificate.update({key: 0 for key in ZERO_KEYS})
    return certificate


def build_non_claim_report(
    *,
    status: str,
    certificate_path: Path,
    certificate: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
    query_report: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    certificate_written = certificate is not None and certificate_path.exists()
    certificate_sha256 = sha256_file(certificate_path) if certificate_written else None
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "status": status,
        "certificate_artifact_schema": CERTIFICATE_SCHEMA,
        "certificate_path": str(certificate_path),
        "certificate_written": certificate_written,
        "certificate_sha256": certificate_sha256,
        "query_failclosed_contract_valid": query_report.get("valid") is True,
        "readiness_checker_valid": readiness.get("valid") is True,
        "readiness_checker_accepted_for_planning": readiness.get("accepted_for_planning") is True,
        "route_blocker_to_use": PUBLIC_HEADER_ROUTE_BLOCKER,
        "unresolved_technical_blocker": {
            "reason": PUBLIC_HEADER_ROUTE_BLOCKER,
            "label": "include/obelisk/ObeliskApi.h",
            "next_requirement": permissions_readiness.REQUIRED_POST_IDENTITY_NEXT_REQUIREMENT_ID,
        },
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claim": NON_CLAIM,
    }
    report.update({key: False for key in FALSE_KEYS})
    report.update({key: 0 for key in ZERO_KEYS})
    if certificate is not None:
        report["certificate_input_binding_sha256"] = certificate["evidence"]["input_binding_sha256"]
    return report


def main() -> int:
    args = parse_args()
    surfaces_path = safe_input_file(args.public_sdk_surfaces, "--public-sdk-surfaces")
    decisions_path = safe_input_file(args.permissions_decisions, "--permissions-decisions")
    query_path = safe_input_file(args.query_failclosed_contract, "--query-failclosed-contract")
    certificate_path = repo_local_output_file(args.output_certificate, "--output-certificate")

    surfaces = load_json_file(surfaces_path, "--public-sdk-surfaces")
    query_payload = load_json_file(query_path, "--query-failclosed-contract")
    query_report = query_validation_report(query_payload)
    readiness = readiness_report(
        surfaces_path=surfaces_path,
        decisions_path=decisions_path,
        query_path=query_path,
        current_route_blocker=args.current_route_blocker,
    )
    blockers = (
        current_json_payload_blockers(
            payload=surfaces,
            path=surfaces_path,
            artifact_label="--public-sdk-surfaces",
            reason="public_sdk_surfaces_loaded_payload_stale_or_mismatched",
            label="$.public_sdk_surfaces",
        )
        + query_failclosed_contract_currentness_blockers(query_path)
        + readiness_currentness_blockers(
            readiness=readiness,
            surfaces_path=surfaces_path,
            decisions_path=decisions_path,
            query_path=query_path,
        )
        + preflight_blockers(
            surfaces=surfaces,
            query_report=query_report,
            readiness=readiness,
            public_header_path=PUBLIC_HEADER,
        )
    )
    if blockers:
        report = build_non_claim_report(
            status="blocked",
            certificate_path=certificate_path,
            certificate=None,
            blockers=blockers,
            query_report=query_report,
            readiness=readiness,
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            for blocker in blockers:
                print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
        return 1

    certificate = build_certificate(
        surfaces=surfaces,
        surfaces_path=surfaces_path,
        decisions_path=decisions_path,
        query_path=query_path,
        query_report=query_report,
        readiness=readiness,
    )
    write_json(certificate_path, certificate)
    report = build_non_claim_report(
        status="built",
        certificate_path=certificate_path,
        certificate=certificate,
        blockers=[],
        query_report=query_report,
        readiness=readiness,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
