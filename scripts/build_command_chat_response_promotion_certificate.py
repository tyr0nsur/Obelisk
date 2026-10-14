#!/usr/bin/env python3
"""Build a non-authorizing command/chat response bridge certificate offline.

The generated certificate is hash-bound to a command/chat response planning
readiness report, public SDK surfaces manifest, and valid upstream player
identity plus permissions/admin promotion certificates. It remains blocked on
approved command response runtime evidence and does not authorize public
headers, API/ABI, runtime delivery, SDK/P0 progress, publication, stable claims,
or v1 completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import check_command_principal_authz_response_bridge as bridge_checker
import check_command_chat_response_public_readiness as response_readiness
import protected_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = "obelisk.command-chat-response-path-promotion-certificate-build-report.v1"
CERTIFICATE_SCHEMA = response_readiness.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA
CERTIFICATE_KEY = "command_response_promotion_certificate"
CERTIFICATE_EVIDENCE_KIND = (
    "command_chat_response_path_post_permissions_runtime_evidence_blocked_certificate"
)
BRIDGE_PROOF_SCHEMA = bridge_checker.REPORT_SCHEMA
BRIDGE_PROOF_KEY = "command_principal_authz_response_bridge_proof"
SURFACE = response_readiness.SURFACE
IDENTITY_SURFACE = response_readiness.IDENTITY_SURFACE
PERMISSIONS_SURFACE = response_readiness.PERMISSIONS_SURFACE
COMMANDS_REPLIES_SURFACE = response_readiness.COMMANDS_REPLIES_SURFACE
CURRENT_ROUTE_BLOCKER = response_readiness.CURRENT_ROUTE_BLOCKER
RUNTIME_EVIDENCE_ROUTE_BLOCKER = response_readiness.RUNTIME_EVIDENCE_ROUTE_BLOCKER
NON_CLAIM = (
    "offline command/chat response bridge certificate build only; the certificate "
    "does not authorize live operations, runtime capture, public header/API/ABI, "
    "reply/send-chat delivery, command routing, runtime readiness, public SDK "
    "readiness, SDK/P0 progress, stable SDK claims, Plugin Hub, publication, or "
    "v1 completion"
)
FALSE_KEYS = (
    "ready",
    "promotion_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "public_readiness_ready",
    "runtime_ready",
    "runtime_delivery_allowed",
    "authz_bridge_ready",
    "authz_ready",
    "authz_response_ready",
    "authorization_ready",
    "stable_claim_allowed",
    "stable_readiness_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "publication_ready",
    "v1_completion_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "public_or_runtime_accounting_allowed",
    "final_artifact_accepted",
    "final_artifact_ready",
    "final_certificate_accepted",
    "final_certificate_metadata_ready",
    "final_certificate_ready",
    "final_certificate_status_ready",
    "final_gate_accepted",
    "final_gate_ready",
    "final_gate_unlocked",
    "route_ready",
    "public_route_ready",
    "command_chat_response_route_ready",
    "command_chat_response_path_complete",
    "command_chat_response_path_completed",
    "command_chat_response_path_ready",
    "command_response_path_complete",
    "command_response_path_completed",
    "public_command_router_allowed",
    "public_reply_or_send_chat_abi_allowed",
    "public_send_chat_api_allowed",
    "public_broadcast_api_allowed",
    "commands_replies_final_gate_ready",
    "commands_replies_final_ready",
    "commands_replies_ready",
    "reply_api_allowed",
    "reply_path_ready",
    "reply_ready",
    "send_chat_api_allowed",
    "command_support_ready",
    "accepted_runtime_evidence",
    "approved_runtime_evidence",
    "live_ops_authorized",
    "server_operations_authorized",
    "runtime_capture_authorized",
    "bridge_ready",
    "bridge_unlocked",
    "response_bridge_ready",
    "response_bridge_unlocked",
    "package_shape",
    "package_shape_accepted",
    "package_shape_evidence_ready",
    "package_shape_install_ready",
    "response_status",
    "response_status_report",
    "response_status_report_accepted",
    "response_status_report_ready",
    "response_complete",
    "response_completed",
    "response_path_complete",
    "response_path_completed",
    "response_path_ready",
    "route_cleared",
    "route_cleared_for_public_abi",
    "route_cleared_for_public_reply_or_send_chat_abi",
    "route_cleared_for_public_send_chat_abi",
    "scoped_release_statement_ready",
    "scoped_release_statement_counts_toward_completion",
    "scoped_release_statement_counts_toward_complete_sdk_claim",
    "scoped_release_statement_outcomes_satisfy_completion",
    "scoped_statement_ready",
    "scoped_statement_counts_toward_completion",
    "scoped_statement_counts_toward_complete_sdk_claim",
    "scoped_statement_outcomes_satisfy_completion",
    "support_tier",
    "support_tier_readiness",
    "support_tier_report",
    "support_tier_report_ready",
    "support_tier_package_ready",
    "support_tier_package_shape",
    "support_tier_package_shape_ready",
    "terminal_certificate",
    "terminal_certificate_accepted",
    "terminal_certificate_metadata",
    "terminal_certificate_metadata_accepted",
    "terminal_certificate_metadata_ready",
    "terminal_certificate_ready",
    "terminal_certificate_status",
    "terminal_certificate_status_ready",
)
ZERO_KEYS = (
    "sdk_progress",
    "p0_progress",
    "public_sdk_progress",
    "runtime_progress",
    "v1_completion_progress",
    "publication_progress",
    "complete_sdk_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=response_readiness.DEFAULT_ROOT,
        help="Second-source planning layout root.",
    )
    parser.add_argument(
        "--readiness",
        type=Path,
        help=(
            "Command/chat response planning readiness JSON. Defaults to "
            "--root/command-chat-response-route-planning-readiness.json."
        ),
    )
    parser.add_argument(
        "--command-decisions",
        type=Path,
        default=response_readiness.DEFAULT_DECISIONS,
        help="Command/chat response public contract decisions manifest.",
    )
    parser.add_argument(
        "--bridge-decisions",
        type=Path,
        default=bridge_checker.DEFAULT_DECISIONS,
        help="Command/principal/authz/response bridge decisions manifest used to prove the bridge remains planning-only.",
    )
    parser.add_argument(
        "--player-identity-decisions",
        type=Path,
        default=bridge_checker.DEFAULT_PLAYER_IDENTITY,
        help="Player identity public contract decisions manifest consumed by the bridge proof.",
    )
    parser.add_argument(
        "--permissions-admin-decisions",
        type=Path,
        default=bridge_checker.DEFAULT_PERMISSIONS_ADMIN,
        help="Permissions/admin public contract decisions manifest consumed by the bridge proof.",
    )
    parser.add_argument(
        "--commands-replies-decisions",
        type=Path,
        default=bridge_checker.DEFAULT_COMMANDS_REPLIES,
        help="Commands/replies public contract decisions manifest consumed by the bridge proof.",
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=response_readiness.DEFAULT_SURFACES,
        help="Public SDK surfaces manifest with valid upstream promotion certificate bindings.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=response_readiness.DEFAULT_PUBLIC_HEADER,
        help="Public header to verify remains without response-path ABI.",
    )
    parser.add_argument(
        "--output-certificate",
        type=Path,
        required=True,
        help="Repo-local output certificate JSON path.",
    )
    parser.add_argument(
        "--current-route-blocker",
        default=CURRENT_ROUTE_BLOCKER,
        choices=response_readiness.ALLOWED_ROUTE_BLOCKERS,
        help="Route blocker to validate for the command/chat response bridge.",
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


def safe_input_dir(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    resolved = protected_paths.reject_protected_input_path(path, label)
    if not resolved.is_dir():
        raise SystemExit(f"{label} is not a directory: {resolved}")
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


def bridge_source_paths(
    *,
    command_decisions_path: Path,
    player_identity_decisions_path: Path,
    permissions_admin_decisions_path: Path,
    commands_replies_decisions_path: Path,
) -> dict[str, tuple[str, Path]]:
    return {
        "player_identity": (IDENTITY_SURFACE, player_identity_decisions_path),
        "permissions_admin": (PERMISSIONS_SURFACE, permissions_admin_decisions_path),
        "command_response": (SURFACE, command_decisions_path),
        "commands_replies": (COMMANDS_REPLIES_SURFACE, commands_replies_decisions_path),
    }


def bridge_source_artifact_hashes(
    *,
    bridge_decisions_path: Path,
    command_decisions_path: Path,
    player_identity_decisions_path: Path,
    permissions_admin_decisions_path: Path,
    commands_replies_decisions_path: Path,
    public_header_path: Path,
) -> dict[str, str]:
    return {
        "bridge_decisions_path": sha256_file(bridge_decisions_path),
        "public_header_path": sha256_file(public_header_path),
        "player_identity_decisions_path": sha256_file(player_identity_decisions_path),
        "permissions_admin_decisions_path": sha256_file(permissions_admin_decisions_path),
        "command_response_decisions_path": sha256_file(command_decisions_path),
        "commands_replies_decisions_path": sha256_file(commands_replies_decisions_path),
    }


def command_principal_authz_response_bridge_proof(
    *,
    bridge_decisions_path: Path,
    command_decisions_path: Path,
    player_identity_decisions_path: Path,
    permissions_admin_decisions_path: Path,
    commands_replies_decisions_path: Path,
    public_header_path: Path,
) -> dict[str, Any]:
    return bridge_checker.build_report(
        decisions_path=bridge_decisions_path,
        source_paths=bridge_source_paths(
            command_decisions_path=command_decisions_path,
            player_identity_decisions_path=player_identity_decisions_path,
            permissions_admin_decisions_path=permissions_admin_decisions_path,
            commands_replies_decisions_path=commands_replies_decisions_path,
        ),
        public_header_path=public_header_path,
    )


def canonical_json_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(data).hexdigest()


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
    if canonical_json_sha256(payload) == canonical_json_sha256(current_payload):
        return []
    return [
        {
            "reason": reason,
            "label": label,
            "path": repo_relative_or_resolved(path),
            "expected_current_sha256": canonical_json_sha256(current_payload),
            "value_sha256": canonical_json_sha256(payload),
        }
    ]


def readiness_source_artifact_blockers(
    *,
    readiness: dict[str, Any],
    artifacts: dict[str, Path],
) -> list[dict[str, Any]]:
    source_hashes = readiness.get("source_artifact_hashes")
    if not isinstance(source_hashes, dict):
        return [
            {
                "reason": "command_chat_response_public_readiness_source_artifact_hashes_missing",
                "label": "$.command_chat_response_public_readiness.source_artifact_hashes",
            }
        ]
    blockers: list[dict[str, Any]] = []
    for key, path in artifacts.items():
        expected = source_hashes.get(key)
        try:
            actual = sha256_file(path)
        except OSError as exc:
            add_builder_blocker(
                blockers,
                f"command_chat_response_public_readiness_report_{key}_unreadable",
                f"$.command_chat_response_public_readiness.source_artifact_hashes.{key}",
                path=repo_relative_or_resolved(path),
                detail=str(exc),
            )
            continue
        if expected != actual:
            add_builder_blocker(
                blockers,
                f"command_chat_response_public_readiness_report_{key}_sha256_mismatch",
                f"$.command_chat_response_public_readiness.source_artifact_hashes.{key}",
                expected=actual,
                value=expected,
                path=repo_relative_or_resolved(path),
            )
    return blockers


def bridge_proof_blockers(
    *,
    bridge_proof: dict[str, Any] | None,
    expected_source_artifact_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if not isinstance(bridge_proof, dict):
        add_builder_blocker(
            blockers,
            "command_principal_authz_response_bridge_proof_missing",
            "$.command_principal_authz_response_bridge_proof",
        )
        return blockers
    if bridge_proof.get("schema") != BRIDGE_PROOF_SCHEMA:
        add_builder_blocker(
            blockers,
            "command_principal_authz_response_bridge_proof_schema_mismatch",
            "$.command_principal_authz_response_bridge_proof.schema",
            expected=BRIDGE_PROOF_SCHEMA,
            value=bridge_proof.get("schema"),
        )
    for key, expected in (
        ("valid", True),
        ("accepted_for_planning", True),
        ("planning_only", True),
    ):
        if bridge_proof.get(key) is not expected:
            add_builder_blocker(
                blockers,
                f"command_principal_authz_response_bridge_proof_{key}_mismatch",
                f"$.command_principal_authz_response_bridge_proof.{key}",
                expected=expected,
                value=bridge_proof.get(key),
            )
    for key in (
        "promotion_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "runtime_ready",
        "public_header_allowed",
        "runtime_wiring_allowed",
        "server_validation_allowed",
        "bridge_claims_allowed",
    ):
        if bridge_proof.get(key) is not False:
            add_builder_blocker(
                blockers,
                f"command_principal_authz_response_bridge_proof_{key}_not_false",
                f"$.command_principal_authz_response_bridge_proof.{key}",
                value=bridge_proof.get(key),
            )
    for key in ("public_capability_bits_now", "public_response_abi_now"):
        if bridge_proof.get(key) != []:
            add_builder_blocker(
                blockers,
                f"command_principal_authz_response_bridge_proof_{key}_not_empty",
                f"$.command_principal_authz_response_bridge_proof.{key}",
                value=bridge_proof.get(key),
            )
    observed_hashes = bridge_proof.get("source_artifact_hashes")
    if observed_hashes != expected_source_artifact_hashes:
        add_builder_blocker(
            blockers,
            "command_principal_authz_response_bridge_proof_source_artifact_hashes_mismatch",
            "$.command_principal_authz_response_bridge_proof.source_artifact_hashes",
            expected=expected_source_artifact_hashes,
            value=observed_hashes,
        )
    for detail in bridge_proof.get("blocker_details", []):
        if not isinstance(detail, dict):
            continue
        add_builder_blocker(
            blockers,
            "command_principal_authz_response_bridge_proof_child_blocker",
            str(detail.get("label", "$.command_principal_authz_response_bridge_proof")),
            child_reason=detail.get("reason"),
            child_detail=detail,
        )
    return blockers


def surface_from_manifest(surfaces: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    return response_readiness.surface_by_id(surfaces, surface_id)


def promotion_certificate_binding(
    surface: dict[str, Any] | None,
    surface_id: str,
) -> dict[str, Any] | None:
    if not isinstance(surface, dict):
        return None
    spec = response_readiness.PROMOTION_CERTIFICATE_SPECS[surface_id]
    evidence = surface.get("evidence")
    binding = evidence.get(spec["certificate_key"]) if isinstance(evidence, dict) else None
    return binding if isinstance(binding, dict) else None


def canonical_promotion_certificate_binding(
    surface: dict[str, Any] | None,
    surface_id: str,
) -> dict[str, str] | None:
    binding = promotion_certificate_binding(surface, surface_id)
    if not isinstance(binding, dict):
        return None
    if {response_readiness.normalized_key(key) for key in binding} != (
        response_readiness.HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS
    ):
        return None
    relative = response_readiness.repo_relative_path(binding.get("path"))
    if relative is None:
        return None
    path = REPO_ROOT / relative
    protected_paths.reject_symlink_component(path, "promotion certificate binding")
    resolved = protected_paths.reject_protected_input_path(
        path,
        "promotion certificate binding",
    )
    return {
        "path": str(relative),
        "sha256": sha256_file(resolved),
    }


def response_surface_record_hash(surface: dict[str, Any]) -> str:
    return response_readiness.surface_record_sha256(surface, CERTIFICATE_KEY)


def readiness_root_and_path(args: argparse.Namespace) -> tuple[Path, Path]:
    root = args.root
    if args.readiness is not None and args.root == response_readiness.DEFAULT_ROOT:
        root = args.readiness.parent
    resolved_root = safe_input_dir(root, "--root")
    readiness_path = args.readiness if args.readiness is not None else resolved_root / response_readiness.DEFAULT_READINESS_NAME
    return resolved_root, safe_input_file(readiness_path, "--readiness")


def readiness_report(
    *,
    root: Path,
    readiness_path: Path,
    decisions_path: Path,
    public_header_path: Path,
    surfaces_path: Path,
    current_route_blocker: str,
) -> dict[str, Any]:
    return response_readiness.build_report(
        root,
        readiness_path,
        decisions_path,
        public_header_path,
        surfaces_path,
        current_route_blocker=current_route_blocker,
    )


def upstream_certificate_blockers(surfaces: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for surface_id in (IDENTITY_SURFACE, PERMISSIONS_SURFACE):
        spec = response_readiness.PROMOTION_CERTIFICATE_SPECS[surface_id]
        surface = surface_from_manifest(surfaces, surface_id)
        label = f"$.surfaces.{spec['label']}.evidence.{spec['certificate_key']}"
        valid = response_readiness.surface_has_valid_promotion_certificate(
            surface,
            surface_id,
            blockers,
            surfaces=surfaces,
        )
        if valid:
            continue
        if not isinstance(surface, dict):
            add_builder_blocker(blockers, f"{spec['label']}_surface_missing", "$.surfaces")
            continue
        if surface.get("status") != "promoted":
            add_builder_blocker(
                blockers,
                f"{spec['certificate_key']}_surface_not_promoted",
                f"$.surfaces.{spec['label']}.status",
                value=surface.get("status"),
            )
        add_builder_blocker(
            blockers,
            f"{spec['certificate_key']}_missing_or_invalid",
            label,
            required_schema=spec["schema"],
        )
    return blockers


def preflight_blockers(
    *,
    surfaces: dict[str, Any],
    readiness: dict[str, Any],
    current_route_blocker: str,
    bridge_proof: dict[str, Any] | None,
    expected_bridge_source_artifact_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    blockers = (
        upstream_certificate_blockers(surfaces)
        + bridge_proof_blockers(
            bridge_proof=bridge_proof,
            expected_source_artifact_hashes=expected_bridge_source_artifact_hashes,
        )
    )
    response_readiness.validate_surfaces(surfaces, blockers)
    response = surface_from_manifest(surfaces, SURFACE)
    if not isinstance(response, dict):
        add_builder_blocker(blockers, "command_chat_response_surface_missing", "$.surfaces")

    if readiness.get("valid") is not True:
        for detail in readiness.get("blocker_details", []):
            if isinstance(detail, dict):
                blockers.append(detail)
    if readiness.get("accepted_for_planning") is not True:
        add_builder_blocker(
            blockers,
            "command_chat_response_readiness_not_accepted_for_planning",
            "$.command_chat_response_public_readiness.accepted_for_planning",
            value=readiness.get("accepted_for_planning"),
        )
    if current_route_blocker != RUNTIME_EVIDENCE_ROUTE_BLOCKER:
        add_builder_blocker(
            blockers,
            "command_chat_response_route_blocker_not_runtime_evidence_missing",
            "$.current_route_blocker",
            expected=RUNTIME_EVIDENCE_ROUTE_BLOCKER,
            value=current_route_blocker,
        )

    diagnostic = readiness.get("post_identity_permissions_gap_diagnostic")
    upstream_satisfied = (
        isinstance(diagnostic, dict)
        and diagnostic.get("upstream_promotions_satisfied") is True
    )
    if not upstream_satisfied:
        add_builder_blocker(
            blockers,
            "upstream_identity_permissions_promotions_not_satisfied",
            "$.command_chat_response_public_readiness.post_identity_permissions_gap_diagnostic",
            upstream_missing_surfaces=(
                diagnostic.get("upstream_missing_surfaces")
                if isinstance(diagnostic, dict)
                else None
            ),
        )
    return blockers


def build_certificate(
    *,
    surfaces: dict[str, Any],
    surfaces_path: Path,
    readiness_path: Path,
    decisions_path: Path,
    public_header_path: Path,
    readiness: dict[str, Any],
    bridge_decisions_path: Path = bridge_checker.DEFAULT_DECISIONS,
    player_identity_decisions_path: Path = bridge_checker.DEFAULT_PLAYER_IDENTITY,
    permissions_admin_decisions_path: Path = bridge_checker.DEFAULT_PERMISSIONS_ADMIN,
    commands_replies_decisions_path: Path = bridge_checker.DEFAULT_COMMANDS_REPLIES,
) -> dict[str, Any]:
    current_route_blocker = readiness.get("current_route_blocker")
    bridge_proof = command_principal_authz_response_bridge_proof(
        bridge_decisions_path=bridge_decisions_path,
        command_decisions_path=decisions_path,
        player_identity_decisions_path=player_identity_decisions_path,
        permissions_admin_decisions_path=permissions_admin_decisions_path,
        commands_replies_decisions_path=commands_replies_decisions_path,
        public_header_path=public_header_path,
    )
    expected_bridge_hashes = bridge_source_artifact_hashes(
        bridge_decisions_path=bridge_decisions_path,
        command_decisions_path=decisions_path,
        player_identity_decisions_path=player_identity_decisions_path,
        permissions_admin_decisions_path=permissions_admin_decisions_path,
        commands_replies_decisions_path=commands_replies_decisions_path,
        public_header_path=public_header_path,
    )
    blockers = (
        current_json_payload_blockers(
            payload=surfaces,
            path=surfaces_path,
            artifact_label="--public-sdk-surfaces",
            reason="public_sdk_surfaces_loaded_payload_stale_or_mismatched",
            label="$.public_sdk_surfaces",
        )
        + readiness_source_artifact_blockers(
            readiness=readiness,
            artifacts={
                "readiness_path": readiness_path,
                "decisions_path": decisions_path,
                "surfaces_path": surfaces_path,
                "public_header_path": public_header_path,
            },
        )
        + preflight_blockers(
            surfaces=surfaces,
            readiness=readiness,
            current_route_blocker=(
                current_route_blocker if isinstance(current_route_blocker, str) else ""
            ),
            bridge_proof=bridge_proof,
            expected_bridge_source_artifact_hashes=expected_bridge_hashes,
        )
    )
    if blockers:
        raise SystemExit(
            "command/chat response promotion certificate inputs failed preflight: "
            f"{blocker_summary(blockers)}"
        )

    response = surface_from_manifest(surfaces, SURFACE)
    identity = surface_from_manifest(surfaces, IDENTITY_SURFACE)
    permissions = surface_from_manifest(surfaces, PERMISSIONS_SURFACE)
    if not isinstance(response, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.command_chat_response_path.v1")
    if not isinstance(identity, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.player_identity.v1")
    if not isinstance(permissions, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.permissions_admin.v1")

    response_hash = response_surface_record_hash(response)
    permissions_hash = response_readiness.surface_record_sha256(
        permissions,
        "permissions_admin_promotion_certificate",
    )
    identity_hash = response_readiness.surface_record_sha256(
        identity,
        "player_identity_promotion_certificate",
    )
    identity_binding = canonical_promotion_certificate_binding(identity, IDENTITY_SURFACE)
    permissions_binding = canonical_promotion_certificate_binding(
        permissions,
        PERMISSIONS_SURFACE,
    )
    if identity_binding is None or permissions_binding is None:
        raise SystemExit(
            "--public-sdk-surfaces upstream promotion certificate binding is not "
            "hash-bound to a repo-local artifact"
        )
    input_bindings: dict[str, Any] = {
        "public_sdk_surfaces": artifact_binding(
            surfaces_path,
            schema=response_readiness.SURFACES_SCHEMA,
        ),
        "command_chat_response_public_readiness": artifact_binding(
            readiness_path,
            schema=response_readiness.READINESS_SCHEMA,
        ),
        "command_chat_response_public_contract_decisions": artifact_binding(
            decisions_path,
            schema=response_readiness.DECISIONS_SCHEMA,
        ),
        "public_header": artifact_binding(public_header_path),
        "command_chat_response_surface_record_sha256": response_hash,
        "permissions_admin_surface_record_sha256": permissions_hash,
        "player_identity_surface_record_sha256": identity_hash,
        "player_identity_promotion_certificate": identity_binding,
        "permissions_admin_promotion_certificate": permissions_binding,
        "command_chat_response_public_readiness_report_sha256": canonical_json_sha256(
            readiness
        ),
        BRIDGE_PROOF_KEY: {
            "schema": BRIDGE_PROOF_SCHEMA,
            "report_sha256": canonical_json_sha256(bridge_proof),
            "source_artifact_hashes": expected_bridge_hashes,
        },
        "command_principal_authz_response_bridge_decisions": artifact_binding(
            bridge_decisions_path,
            schema=bridge_checker.DECISIONS_SCHEMA,
        ),
        "player_identity_public_contract_decisions": artifact_binding(
            player_identity_decisions_path,
            schema=bridge_checker.SOURCE_SCHEMAS["player_identity"],
        ),
        "permissions_admin_public_contract_decisions": artifact_binding(
            permissions_admin_decisions_path,
            schema=bridge_checker.SOURCE_SCHEMAS["permissions_admin"],
        ),
        "commands_replies_public_contract_decisions": artifact_binding(
            commands_replies_decisions_path,
            schema=bridge_checker.SOURCE_SCHEMAS["commands_replies"],
        ),
    }
    evidence = {
        "reviewed_artifact_hash": response_hash,
        "reviewed_surface_record_sha256": response_hash,
        "promotion_evidence_kind": CERTIFICATE_EVIDENCE_KIND,
        "input_binding_sha256": canonical_json_sha256(input_bindings),
        "upstream_player_identity_certificate_validated": True,
        "upstream_permissions_admin_certificate_validated": True,
        "command_principal_authz_response_bridge_proof_validated": True,
        "command_principal_authz_response_bridge_proof_sha256": canonical_json_sha256(
            bridge_proof
        ),
        "readiness_checker": "scripts/check_command_chat_response_public_readiness.py",
        "readiness_checker_valid": True,
        "readiness_checker_accepted_for_planning": True,
        "missing_after_valid_upstream_promotions": (
            readiness.get("post_identity_permissions_gap_diagnostic", {}).get(
                "missing_after_valid_upstream_promotions",
                [],
            )
            if isinstance(readiness.get("post_identity_permissions_gap_diagnostic"), dict)
            else []
        ),
        "required_fail_closed_guardrails": list(
            response_readiness.POST_PERMISSIONS_FAIL_CLOSED_GUARDRAILS
        ),
        "required_runtime_owned_inputs": list(
            response_readiness.POST_PERMISSIONS_REQUIRED_RUNTIME_INPUTS
        ),
    }
    evidence.update({key: False for key in FALSE_KEYS})
    evidence.update({key: 0 for key in ZERO_KEYS})

    certificate = {
        "schema": CERTIFICATE_SCHEMA,
        "surface_id": SURFACE,
        "certificate_status": "built",
        "promotion_status": f"blocked_{RUNTIME_EVIDENCE_ROUTE_BLOCKER}",
        "planning_only": True,
        "non_authorizing": True,
        "v1_dependency_chain": list(response_readiness.DEPENDENCY_CHAIN),
        "v1_dependency_chain_position": 3,
        "depends_on_surfaces": [IDENTITY_SURFACE, PERMISSIONS_SURFACE],
        "required_by_surface": COMMANDS_REPLIES_SURFACE,
        "required_by_v1_dependency_chain_position": 4,
        "required_reviewed_artifact_hash": (
            response_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH
        ),
        "reviewed_artifact_hash_policy": (
            response_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY
        ),
        "missing_mismatched_or_stale_certificate_counts": False,
        "route_blocker_to_use": RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        "remaining_route_blockers": [RUNTIME_EVIDENCE_ROUTE_BLOCKER],
        "unresolved_technical_blocker": {
            "reason": RUNTIME_EVIDENCE_ROUTE_BLOCKER,
            "label": "command_chat_response_path.runtime_delivery_evidence",
            "required_before_promotion": list(
                response_readiness.POST_PERMISSIONS_REQUIRED_EVIDENCE
            ),
            "public_header_allowed": False,
            "public_abi_ready": False,
            "runtime_delivery_allowed": False,
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
    readiness: dict[str, Any],
    bridge_proof: dict[str, Any] | None,
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
        "certificate_binding": (
            {
                "path": repo_relative_or_resolved(certificate_path),
                "sha256": certificate_sha256,
            }
            if certificate_sha256 is not None
            else None
        ),
        "command_chat_response_public_readiness_valid": readiness.get("valid") is True,
        "command_chat_response_public_readiness_accepted_for_planning": (
            readiness.get("accepted_for_planning") is True
        ),
        "command_principal_authz_response_bridge_proof_valid": (
            isinstance(bridge_proof, dict) and bridge_proof.get("valid") is True
        ),
        "command_principal_authz_response_bridge_proof_sha256": (
            canonical_json_sha256(bridge_proof) if isinstance(bridge_proof, dict) else None
        ),
        "route_blocker_to_use": RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        "unresolved_technical_blocker": {
            "reason": RUNTIME_EVIDENCE_ROUTE_BLOCKER,
            "label": "command_chat_response_path.runtime_delivery_evidence",
            "required_before_promotion": list(
                response_readiness.POST_PERMISSIONS_REQUIRED_EVIDENCE
            ),
        },
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claim": NON_CLAIM,
    }
    report.update({key: False for key in FALSE_KEYS})
    report.update({key: 0 for key in ZERO_KEYS})
    if certificate is not None:
        report["certificate_input_binding_sha256"] = certificate["evidence"][
            "input_binding_sha256"
        ]
    return report


def main() -> int:
    args = parse_args()
    root, readiness_path = readiness_root_and_path(args)
    decisions_path = safe_input_file(args.command_decisions, "--command-decisions")
    bridge_decisions_path = safe_input_file(args.bridge_decisions, "--bridge-decisions")
    player_identity_decisions_path = safe_input_file(
        args.player_identity_decisions,
        "--player-identity-decisions",
    )
    permissions_admin_decisions_path = safe_input_file(
        args.permissions_admin_decisions,
        "--permissions-admin-decisions",
    )
    commands_replies_decisions_path = safe_input_file(
        args.commands_replies_decisions,
        "--commands-replies-decisions",
    )
    surfaces_path = safe_input_file(args.public_sdk_surfaces, "--public-sdk-surfaces")
    public_header_path = safe_input_file(args.public_header, "--public-header")
    certificate_path = repo_local_output_file(args.output_certificate, "--output-certificate")

    surfaces = load_json_file(surfaces_path, "--public-sdk-surfaces")
    readiness = readiness_report(
        root=root,
        readiness_path=readiness_path,
        decisions_path=decisions_path,
        public_header_path=public_header_path,
        surfaces_path=surfaces_path,
        current_route_blocker=args.current_route_blocker,
    )
    bridge_proof = command_principal_authz_response_bridge_proof(
        bridge_decisions_path=bridge_decisions_path,
        command_decisions_path=decisions_path,
        player_identity_decisions_path=player_identity_decisions_path,
        permissions_admin_decisions_path=permissions_admin_decisions_path,
        commands_replies_decisions_path=commands_replies_decisions_path,
        public_header_path=public_header_path,
    )
    expected_bridge_hashes = bridge_source_artifact_hashes(
        bridge_decisions_path=bridge_decisions_path,
        command_decisions_path=decisions_path,
        player_identity_decisions_path=player_identity_decisions_path,
        permissions_admin_decisions_path=permissions_admin_decisions_path,
        commands_replies_decisions_path=commands_replies_decisions_path,
        public_header_path=public_header_path,
    )
    blockers = (
        current_json_payload_blockers(
            payload=surfaces,
            path=surfaces_path,
            artifact_label="--public-sdk-surfaces",
            reason="public_sdk_surfaces_loaded_payload_stale_or_mismatched",
            label="$.public_sdk_surfaces",
        )
        + readiness_source_artifact_blockers(
            readiness=readiness,
            artifacts={
                "readiness_path": readiness_path,
                "decisions_path": decisions_path,
                "surfaces_path": surfaces_path,
                "public_header_path": public_header_path,
            },
        )
        + preflight_blockers(
            surfaces=surfaces,
            readiness=readiness,
            current_route_blocker=args.current_route_blocker,
            bridge_proof=bridge_proof,
            expected_bridge_source_artifact_hashes=expected_bridge_hashes,
        )
    )
    if blockers:
        report = build_non_claim_report(
            status="blocked",
            certificate_path=certificate_path,
            certificate=None,
            blockers=blockers,
            readiness=readiness,
            bridge_proof=bridge_proof,
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
        readiness_path=readiness_path,
        decisions_path=decisions_path,
        public_header_path=public_header_path,
        readiness=readiness,
        bridge_decisions_path=bridge_decisions_path,
        player_identity_decisions_path=player_identity_decisions_path,
        permissions_admin_decisions_path=permissions_admin_decisions_path,
        commands_replies_decisions_path=commands_replies_decisions_path,
    )
    write_json(certificate_path, certificate)
    report = build_non_claim_report(
        status="built",
        certificate_path=certificate_path,
        certificate=certificate,
        blockers=[],
        readiness=readiness,
        bridge_proof=bridge_proof,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
