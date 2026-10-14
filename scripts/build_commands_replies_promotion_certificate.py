#!/usr/bin/env python3
"""Build a non-authorizing commands/replies final-gate certificate offline.

The generated certificate is hash-bound to the existing commands/replies
public-readiness checker output and to an upstream public SDK surfaces manifest
that carries a valid command/chat-response promotion certificate. It remains
blocked on the commands/replies ABI/runtime evidence package and does not
authorize public headers, API/ABI, runtime delivery, SDK/P0 progress,
publication, stable claims, or v1 completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import check_commands_replies_public_readiness as commands_readiness
import protected_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = "obelisk.commands-replies-promotion-certificate-build-report.v1"
CERTIFICATE_SCHEMA = "obelisk.commands-replies-promotion-certificate.v1"
CERTIFICATE_KEY = "commands_replies_promotion_certificate"
CERTIFICATE_EVIDENCE_KIND = (
    "commands_replies_post_command_response_abi_runtime_evidence_blocked_certificate"
)
SURFACE = commands_readiness.SURFACE
RESPONSE_PATH_SURFACE = commands_readiness.RESPONSE_PATH_SURFACE
CURRENT_ROUTE_BLOCKER = commands_readiness.CURRENT_ROUTE_BLOCKER
RUNTIME_EVIDENCE_ROUTE_BLOCKER = commands_readiness.RUNTIME_EVIDENCE_ROUTE_BLOCKER
POST_COMMAND_RESPONSE_BLOCKER = commands_readiness.POST_COMMAND_RESPONSE_BLOCKER
UPSTREAM_CHAIN_SURFACES = commands_readiness.DEPENDENCY_CHAIN[:-1]
NON_COUNTING_REASONS = (
    "commands_replies_promotion_artifact_missing",
    f"route_gate_blocker:{POST_COMMAND_RESPONSE_BLOCKER}",
    "runtime_evidence_missing",
    "public_abi_contract_missing",
)
NON_CLAIM = (
    "offline commands/replies final-gate certificate build only; the certificate "
    "does not authorize live operations, runtime capture, public header/API/ABI, "
    "command dispatch, replies, send-chat, broadcast/notices, moderation, runtime "
    "readiness, public SDK readiness, SDK/P0 progress, stable SDK claims, Plugin "
    "Hub, publication, or v1 completion"
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
    "command_route_ready",
    "route_gate_ready",
    "route_gate_unlocked",
    "route_readiness_ready",
    "route_acceptance_ready",
    "route_accepted",
    "route_accepted_for_public_abi",
    "route_accepted_for_public_reply_or_send_chat_abi",
    "route_accepted_for_public_send_chat_abi",
    "commands_replies_ready",
    "commands_replies_final_gate_ready",
    "commands_replies_final_ready",
    "command_support_ready",
    "command_chat_response_path_complete",
    "command_chat_response_path_completed",
    "command_chat_response_path_ready",
    "command_response_path_complete",
    "command_response_path_completed",
    "public_command_router_allowed",
    "public_reply_or_send_chat_abi_allowed",
    "public_send_chat_api_allowed",
    "public_broadcast_api_allowed",
    "reply_api_allowed",
    "reply_path_ready",
    "reply_ready",
    "send_chat_api_allowed",
    "broadcast_api_allowed",
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
    "commands_replies_progress_contribution",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decisions",
        type=Path,
        default=commands_readiness.DEFAULT_DECISIONS,
        help="Commands/replies public contract decisions manifest.",
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=commands_readiness.DEFAULT_SURFACES,
        help="Planning-only public SDK surfaces manifest for the readiness checker.",
    )
    parser.add_argument(
        "--upstream-public-sdk-surfaces",
        type=Path,
        help=(
            "Public SDK surfaces manifest carrying a valid hash-bound "
            "command_response_promotion_certificate. Defaults to --public-sdk-surfaces."
        ),
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=commands_readiness.DEFAULT_PUBLIC_HEADER,
        help="Public header to verify remains without commands/replies ABI.",
    )
    parser.add_argument(
        "--response-path-report",
        type=Path,
        help="Command/chat response public-readiness report consumed by the checker.",
    )
    parser.add_argument("--response-path-root", type=Path)
    parser.add_argument("--response-path-readiness", type=Path)
    parser.add_argument("--response-path-report-root", type=Path)
    parser.add_argument(
        "--output-certificate",
        type=Path,
        required=True,
        help="Repo-local output certificate JSON path.",
    )
    parser.add_argument(
        "--current-route-blocker",
        default=CURRENT_ROUTE_BLOCKER,
        choices=commands_readiness.ALLOWED_ROUTE_BLOCKERS,
        help="Parent route blocker to validate while the final gate remains non-counting.",
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


def safe_optional_input_file(path: Path | None, label: str) -> Path | None:
    if path is None:
        return None
    return safe_input_file(path, label)


def safe_optional_input_dir(path: Path | None, label: str) -> Path | None:
    if path is None:
        return None
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
    artifacts: dict[str, Path | None],
) -> list[dict[str, Any]]:
    source_hashes = readiness.get("source_artifact_hashes")
    if not isinstance(source_hashes, dict):
        return [
            {
                "reason": "commands_replies_public_readiness_source_artifact_hashes_missing",
                "label": "$.commands_replies_public_readiness.source_artifact_hashes",
            }
        ]
    blockers: list[dict[str, Any]] = []
    for key, path in artifacts.items():
        if path is None:
            continue
        expected = source_hashes.get(key)
        try:
            actual = sha256_file(path)
        except OSError as exc:
            add_builder_blocker(
                blockers,
                f"commands_replies_public_readiness_report_{key}_unreadable",
                f"$.commands_replies_public_readiness.source_artifact_hashes.{key}",
                path=repo_relative_or_resolved(path),
                detail=str(exc),
            )
            continue
        if expected != actual:
            add_builder_blocker(
                blockers,
                f"commands_replies_public_readiness_report_{key}_sha256_mismatch",
                f"$.commands_replies_public_readiness.source_artifact_hashes.{key}",
                expected=actual,
                value=expected,
                path=repo_relative_or_resolved(path),
            )
    return blockers


def surface_from_manifest(surfaces: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    return commands_readiness.surface_by_id(surfaces, surface_id)


def promotion_certificate_binding(
    surface: dict[str, Any] | None,
    surface_id: str,
) -> dict[str, Any] | None:
    if not isinstance(surface, dict):
        return None
    spec = commands_readiness.PROMOTION_CERTIFICATE_SPECS[surface_id]
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
    if {commands_readiness.normalized_key(key) for key in binding} != (
        commands_readiness.HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS
    ):
        return None
    relative = commands_readiness.repo_relative_path(binding.get("path"))
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


def surface_record_hash(surface: dict[str, Any], certificate_key: str) -> str:
    return commands_readiness.surface_record_sha256(surface, certificate_key)


def current_surface_contract_sha256(surface: dict[str, Any], certificate_key: str) -> str:
    sanitized = dict(surface)
    sanitized.pop("status", None)
    evidence = sanitized.get("evidence")
    if isinstance(evidence, dict):
        sanitized_evidence = {
            key: value for key, value in evidence.items() if key != certificate_key
        }
        if sanitized_evidence:
            sanitized["evidence"] = sanitized_evidence
        else:
            sanitized.pop("evidence", None)
    return canonical_json_sha256(sanitized)


def non_counting_route_gate_fields() -> dict[str, Any]:
    return {
        "missing_non_counting": True,
        "missing_non_counting_artifact": "commands_replies_promotion_certificate",
        "missing_non_counting_surface": SURFACE,
        "missing_non_counting_required_after_surface": RESPONSE_PATH_SURFACE,
        "non_counting_until_present": True,
        "route_gate_non_counting_blocker": POST_COMMAND_RESPONSE_BLOCKER,
        "route_gate_non_counting_blocker_label": (
            "commands_replies.public_abi_and_runtime_dispatch_evidence"
        ),
        "required_prior_certificate_schema": (
            commands_readiness.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA
        ),
        "required_prior_certificate_key": "command_response_promotion_certificate",
        "required_terminal_artifact_schema": (
            commands_readiness.COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
        ),
        "first_missing_terminal_artifact": "commands_replies_promotion_certificate",
        "required_before_counting": list(
            commands_readiness.COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT[
                "required_evidence"
            ]
        ),
        "non_counting_reasons": list(NON_COUNTING_REASONS),
        "non_counting_explanation": (
            "commands/replies remains a missing non-counting final-gate artifact until "
            "the command/chat response promotion certificate is valid and the copied "
            "command ABI plus isolated runtime dispatch evidence are present"
        ),
        "manifest_promoted_but_non_counting": False,
        "sdk_p0_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "terminal_artifact_shortcuts_count": False,
    }


def readiness_report(
    *,
    decisions_path: Path,
    surfaces_path: Path,
    public_header_path: Path,
    response_path_report_path: Path | None,
    response_path_root: Path | None,
    response_path_readiness: Path | None,
    response_path_report_root: Path | None,
    current_route_blocker: str,
) -> dict[str, Any]:
    return commands_readiness.build_report(
        decisions_path=decisions_path,
        surfaces_path=surfaces_path,
        public_header_path=public_header_path,
        response_path_report_path=response_path_report_path,
        response_path_root=response_path_root,
        response_path_readiness=response_path_readiness,
        response_path_report_root=response_path_report_root,
        current_route_blocker=current_route_blocker,
    )


def deduplicate_blockers(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for blocker in blockers:
        reason = str(blocker.get("reason", ""))
        label = str(blocker.get("label", ""))
        key = (reason, label)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(blocker)
    return deduplicated


def upstream_certificate_blockers(upstream_surfaces: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for surface_id in UPSTREAM_CHAIN_SURFACES:
        surface = surface_from_manifest(upstream_surfaces, surface_id)
        spec = commands_readiness.PROMOTION_CERTIFICATE_SPECS[surface_id]
        label = f"$.surfaces.{spec['label']}.evidence.{spec['certificate_key']}"
        valid = commands_readiness.surface_has_valid_promotion_certificate(
            surface,
            surface_id,
            blockers,
            surfaces=upstream_surfaces,
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
    return deduplicate_blockers(blockers)


def upstream_manifest_blockers(upstream_surfaces: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    commands_readiness.validate_surfaces(upstream_surfaces, blockers)
    return blockers


def upstream_chain_blockers(upstream_surfaces: dict[str, Any]) -> list[dict[str, Any]]:
    return deduplicate_blockers(
        upstream_manifest_blockers(upstream_surfaces)
        + upstream_certificate_blockers(upstream_surfaces)
    )


def current_upstream_surface_record_blockers(
    *,
    readiness_surfaces: dict[str, Any],
    upstream_surfaces: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for surface_id in UPSTREAM_CHAIN_SURFACES:
        spec = commands_readiness.PROMOTION_CERTIFICATE_SPECS[surface_id]
        current_surface = surface_from_manifest(readiness_surfaces, surface_id)
        upstream_surface = surface_from_manifest(upstream_surfaces, surface_id)
        label = f"$.upstream_public_sdk_surfaces.surfaces[{spec['label']}]"
        if not isinstance(current_surface, dict):
            add_builder_blocker(
                blockers,
                f"{spec['certificate_key']}_current_surface_missing",
                "$.public_sdk_surfaces.surfaces",
                surface=surface_id,
            )
            continue
        if not isinstance(upstream_surface, dict):
            add_builder_blocker(
                blockers,
                f"{spec['certificate_key']}_upstream_surface_missing",
                label,
                surface=surface_id,
            )
            continue
        current_hash = current_surface_contract_sha256(
            current_surface,
            str(spec["certificate_key"]),
        )
        upstream_hash = current_surface_contract_sha256(
            upstream_surface,
            str(spec["certificate_key"]),
        )
        if current_hash != upstream_hash:
            add_builder_blocker(
                blockers,
                f"{spec['certificate_key']}_current_surface_record_mismatch",
                label,
                surface=surface_id,
                expected_current_surface_contract_sha256=current_hash,
                upstream_surface_contract_sha256=upstream_hash,
            )
    return blockers


def upstream_response_certificate_valid(upstream_surfaces: dict[str, Any]) -> bool:
    return commands_readiness.surface_has_valid_promotion_certificate(
        surface_from_manifest(upstream_surfaces, RESPONSE_PATH_SURFACE),
        RESPONSE_PATH_SURFACE,
        surfaces=upstream_surfaces,
    )


def preflight_blockers(
    *,
    readiness_surfaces: dict[str, Any],
    upstream_surfaces: dict[str, Any],
    readiness: dict[str, Any],
    current_route_blocker: str,
) -> list[dict[str, Any]]:
    blockers = (
        upstream_chain_blockers(upstream_surfaces)
        + current_upstream_surface_record_blockers(
            readiness_surfaces=readiness_surfaces,
            upstream_surfaces=upstream_surfaces,
        )
    )
    if readiness.get("valid") is not True:
        for detail in readiness.get("blocker_details", []):
            if isinstance(detail, dict):
                blockers.append(detail)
    if readiness.get("accepted_for_planning") is not True:
        add_builder_blocker(
            blockers,
            "commands_replies_readiness_not_accepted_for_planning",
            "$.commands_replies_public_readiness.accepted_for_planning",
            value=readiness.get("accepted_for_planning"),
        )
    if current_route_blocker != RUNTIME_EVIDENCE_ROUTE_BLOCKER:
        add_builder_blocker(
            blockers,
            "commands_replies_parent_route_blocker_not_runtime_evidence_missing",
            "$.current_route_blocker",
            expected=RUNTIME_EVIDENCE_ROUTE_BLOCKER,
            value=current_route_blocker,
        )
    return blockers


def build_input_bindings(
    *,
    decisions_path: Path,
    surfaces_path: Path,
    upstream_surfaces_path: Path,
    public_header_path: Path,
    response_path_report_path: Path | None,
    response_path_readiness: Path | None,
    readiness: dict[str, Any],
    readiness_surfaces: dict[str, Any],
    upstream_surfaces: dict[str, Any],
) -> dict[str, Any]:
    commands_surface = surface_from_manifest(readiness_surfaces, SURFACE)
    identity_surface = surface_from_manifest(
        upstream_surfaces,
        commands_readiness.DEPENDENCY_CHAIN[0],
    )
    permissions_surface = surface_from_manifest(
        upstream_surfaces,
        commands_readiness.DEPENDENCY_CHAIN[1],
    )
    response_surface = surface_from_manifest(upstream_surfaces, RESPONSE_PATH_SURFACE)
    current_identity_surface = surface_from_manifest(
        readiness_surfaces,
        commands_readiness.DEPENDENCY_CHAIN[0],
    )
    current_permissions_surface = surface_from_manifest(
        readiness_surfaces,
        commands_readiness.DEPENDENCY_CHAIN[1],
    )
    current_response_surface = surface_from_manifest(
        readiness_surfaces,
        RESPONSE_PATH_SURFACE,
    )
    if not isinstance(commands_surface, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.commands_replies.v1")
    if not isinstance(current_identity_surface, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.player_identity.v1")
    if not isinstance(current_permissions_surface, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.permissions_admin.v1")
    if not isinstance(current_response_surface, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.command_chat_response_path.v1")
    if not isinstance(identity_surface, dict):
        raise SystemExit(
            "--upstream-public-sdk-surfaces missing obelisk.player_identity.v1"
        )
    if not isinstance(permissions_surface, dict):
        raise SystemExit(
            "--upstream-public-sdk-surfaces missing obelisk.permissions_admin.v1"
        )
    if not isinstance(response_surface, dict):
        raise SystemExit(
            "--upstream-public-sdk-surfaces missing obelisk.command_chat_response_path.v1"
        )

    bindings: dict[str, Any] = {
        "commands_replies_public_contract_decisions": artifact_binding(
            decisions_path,
            schema=commands_readiness.DECISIONS_SCHEMA,
        ),
        "public_sdk_surfaces": artifact_binding(
            surfaces_path,
            schema=commands_readiness.SURFACES_SCHEMA,
        ),
        "upstream_public_sdk_surfaces": artifact_binding(
            upstream_surfaces_path,
            schema=commands_readiness.SURFACES_SCHEMA,
        ),
        "public_header": artifact_binding(public_header_path),
        "commands_replies_surface_record_sha256": surface_record_hash(
            commands_surface,
            CERTIFICATE_KEY,
        ),
        "player_identity_surface_record_sha256": surface_record_hash(
            identity_surface,
            "player_identity_promotion_certificate",
        ),
        "permissions_admin_surface_record_sha256": surface_record_hash(
            permissions_surface,
            "permissions_admin_promotion_certificate",
        ),
        "command_response_surface_record_sha256": surface_record_hash(
            response_surface,
            "command_response_promotion_certificate",
        ),
        "current_player_identity_surface_contract_sha256": current_surface_contract_sha256(
            current_identity_surface,
            "player_identity_promotion_certificate",
        ),
        "current_permissions_admin_surface_contract_sha256": current_surface_contract_sha256(
            current_permissions_surface,
            "permissions_admin_promotion_certificate",
        ),
        "current_command_response_surface_contract_sha256": current_surface_contract_sha256(
            current_response_surface,
            "command_response_promotion_certificate",
        ),
        "upstream_player_identity_surface_contract_sha256": current_surface_contract_sha256(
            identity_surface,
            "player_identity_promotion_certificate",
        ),
        "upstream_permissions_admin_surface_contract_sha256": current_surface_contract_sha256(
            permissions_surface,
            "permissions_admin_promotion_certificate",
        ),
        "upstream_command_response_surface_contract_sha256": current_surface_contract_sha256(
            response_surface,
            "command_response_promotion_certificate",
        ),
        "player_identity_promotion_certificate": canonical_promotion_certificate_binding(
            identity_surface,
            commands_readiness.DEPENDENCY_CHAIN[0],
        ),
        "permissions_admin_promotion_certificate": canonical_promotion_certificate_binding(
            permissions_surface,
            commands_readiness.DEPENDENCY_CHAIN[1],
        ),
        "command_response_promotion_certificate": canonical_promotion_certificate_binding(
            response_surface,
            RESPONSE_PATH_SURFACE,
        ),
        "commands_replies_public_readiness_report_sha256": canonical_json_sha256(
            readiness
        ),
    }
    if response_path_report_path is not None:
        bindings["response_path_report"] = artifact_binding(
            response_path_report_path,
            schema=commands_readiness.RESPONSE_PATH_REPORT_SCHEMA,
        )
    if response_path_readiness is not None:
        bindings["response_path_readiness"] = artifact_binding(
            response_path_readiness,
            schema=commands_readiness.RESPONSE_PATH_READINESS_SCHEMA,
        )
    return bindings


def build_certificate(
    *,
    decisions_path: Path,
    surfaces_path: Path,
    upstream_surfaces_path: Path,
    public_header_path: Path,
    response_path_report_path: Path | None,
    response_path_readiness: Path | None,
    readiness: dict[str, Any],
    readiness_surfaces: dict[str, Any],
    upstream_surfaces: dict[str, Any],
) -> dict[str, Any]:
    current_route_blocker = readiness.get("current_route_blocker")
    blockers = (
        current_json_payload_blockers(
            payload=readiness_surfaces,
            path=surfaces_path,
            artifact_label="--public-sdk-surfaces",
            reason="public_sdk_surfaces_loaded_payload_stale_or_mismatched",
            label="$.public_sdk_surfaces",
        )
        + current_json_payload_blockers(
            payload=upstream_surfaces,
            path=upstream_surfaces_path,
            artifact_label="--upstream-public-sdk-surfaces",
            reason="upstream_public_sdk_surfaces_loaded_payload_stale_or_mismatched",
            label="$.upstream_public_sdk_surfaces",
        )
        + readiness_source_artifact_blockers(
            readiness=readiness,
            artifacts={
                "decisions_path": decisions_path,
                "surfaces_path": surfaces_path,
                "public_header_path": public_header_path,
                "response_path_report_path": response_path_report_path,
            },
        )
        + preflight_blockers(
            readiness_surfaces=readiness_surfaces,
            upstream_surfaces=upstream_surfaces,
            readiness=readiness,
            current_route_blocker=(
                current_route_blocker if isinstance(current_route_blocker, str) else ""
            ),
        )
    )
    if blockers:
        raise SystemExit(
            "commands/replies promotion certificate inputs failed preflight: "
            f"{blocker_summary(blockers)}"
        )

    commands_surface = surface_from_manifest(readiness_surfaces, SURFACE)
    response_surface = surface_from_manifest(upstream_surfaces, RESPONSE_PATH_SURFACE)
    if not isinstance(commands_surface, dict):
        raise SystemExit("--public-sdk-surfaces missing obelisk.commands_replies.v1")
    if not isinstance(response_surface, dict):
        raise SystemExit(
            "--upstream-public-sdk-surfaces missing obelisk.command_chat_response_path.v1"
        )

    input_bindings = build_input_bindings(
        decisions_path=decisions_path,
        surfaces_path=surfaces_path,
        upstream_surfaces_path=upstream_surfaces_path,
        public_header_path=public_header_path,
        response_path_report_path=response_path_report_path,
        response_path_readiness=response_path_readiness,
        readiness=readiness,
        readiness_surfaces=readiness_surfaces,
        upstream_surfaces=upstream_surfaces,
    )
    commands_hash = input_bindings["commands_replies_surface_record_sha256"]
    evidence = {
        "reviewed_artifact_hash": commands_hash,
        "reviewed_surface_record_sha256": commands_hash,
        "promotion_evidence_kind": CERTIFICATE_EVIDENCE_KIND,
        "input_binding_sha256": canonical_json_sha256(input_bindings),
        "upstream_promotion_chain_validated": list(UPSTREAM_CHAIN_SURFACES),
        "upstream_player_identity_certificate_validated": True,
        "upstream_permissions_admin_certificate_validated": True,
        "upstream_command_response_certificate_validated": True,
        "readiness_checker": "scripts/check_commands_replies_public_readiness.py",
        "readiness_checker_valid": True,
        "readiness_checker_accepted_for_planning": True,
        "post_command_response_blocker": POST_COMMAND_RESPONSE_BLOCKER,
        "required_actions_before_promotion": list(
            commands_readiness.POST_COMMAND_RESPONSE_REQUIRED_ACTIONS
        ),
        "required_test_artifacts_before_promotion": list(
            commands_readiness.COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT[
                "required_evidence"
            ]
        ),
        "required_fail_closed_guardrails": list(
            commands_readiness.POST_RESPONSE_FAIL_CLOSED_GUARDRAILS
        ),
        "required_runtime_owned_gate_inputs": list(
            commands_readiness.REQUIRED_RUNTIME_OWNED_GATE_INPUTS
        ),
    }
    evidence.update(non_counting_route_gate_fields())
    evidence.update({key: False for key in FALSE_KEYS})
    evidence.update({key: 0 for key in ZERO_KEYS})

    certificate = {
        "schema": CERTIFICATE_SCHEMA,
        "surface_id": SURFACE,
        "certificate_status": "built",
        "promotion_status": f"blocked_{POST_COMMAND_RESPONSE_BLOCKER}",
        "planning_only": True,
        "non_authorizing": True,
        "v1_dependency_chain": list(commands_readiness.DEPENDENCY_CHAIN),
        "v1_dependency_chain_position": 4,
        "depends_on_surfaces": list(commands_readiness.DEPENDENCY_CHAIN[:-1]),
        "required_prior_surface": RESPONSE_PATH_SURFACE,
        "required_prior_certificate_schema": (
            commands_readiness.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA
        ),
        "required_reviewed_artifact_hash": (
            commands_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH
        ),
        "reviewed_artifact_hash_policy": (
            commands_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY
        ),
        "missing_mismatched_or_stale_certificate_counts": False,
        "route_blocker_to_use": POST_COMMAND_RESPONSE_BLOCKER,
        "remaining_route_blockers": [POST_COMMAND_RESPONSE_BLOCKER],
        "unresolved_technical_blocker": {
            "reason": POST_COMMAND_RESPONSE_BLOCKER,
            "label": "commands_replies.public_abi_and_runtime_dispatch_evidence",
            "required_before_promotion": list(
                commands_readiness.COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT[
                    "required_evidence"
                ]
            ),
            "public_header_allowed": False,
            "public_abi_ready": False,
            "runtime_delivery_allowed": False,
            **non_counting_route_gate_fields(),
        },
        "input_bindings": input_bindings,
        "evidence": evidence,
        "non_counting_route_gate": non_counting_route_gate_fields(),
        "non_claim": NON_CLAIM,
    }
    certificate.update(non_counting_route_gate_fields())
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
    upstream_command_response_certificate_valid: bool,
    upstream_promotion_chain_valid: bool,
) -> dict[str, Any]:
    certificate_written = certificate is not None and certificate_path.exists()
    certificate_sha256 = sha256_file(certificate_path) if certificate_written else None
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "status": status,
        "certificate_artifact_schema": CERTIFICATE_SCHEMA,
        "certificate_path": repo_relative_or_resolved(certificate_path),
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
        "commands_replies_public_readiness_valid": readiness.get("valid") is True,
        "commands_replies_public_readiness_accepted_for_planning": (
            readiness.get("accepted_for_planning") is True
        ),
        "upstream_command_response_promotion_certificate_valid": (
            upstream_command_response_certificate_valid
        ),
        "upstream_promotion_chain_valid": upstream_promotion_chain_valid,
        "route_blocker_to_use": POST_COMMAND_RESPONSE_BLOCKER,
        "unresolved_technical_blocker": {
            "reason": POST_COMMAND_RESPONSE_BLOCKER,
            "label": "commands_replies.public_abi_and_runtime_dispatch_evidence",
            "required_before_promotion": list(
                commands_readiness.COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT[
                    "required_evidence"
                ]
            ),
        },
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_counting_route_gate": non_counting_route_gate_fields(),
        "non_claim": NON_CLAIM,
    }
    report.update(non_counting_route_gate_fields())
    report.update({key: False for key in FALSE_KEYS})
    report.update({key: 0 for key in ZERO_KEYS})
    if certificate is not None:
        report["certificate_input_binding_sha256"] = certificate["evidence"][
            "input_binding_sha256"
        ]
    return report


def main() -> int:
    args = parse_args()
    decisions_path = safe_input_file(args.decisions, "--decisions")
    surfaces_path = safe_input_file(args.public_sdk_surfaces, "--public-sdk-surfaces")
    upstream_surfaces_path = safe_input_file(
        args.upstream_public_sdk_surfaces or args.public_sdk_surfaces,
        "--upstream-public-sdk-surfaces",
    )
    public_header_path = safe_input_file(args.public_header, "--public-header")
    response_path_report_path = safe_optional_input_file(
        args.response_path_report,
        "--response-path-report",
    )
    response_path_root = safe_optional_input_dir(
        args.response_path_root,
        "--response-path-root",
    )
    response_path_readiness = safe_optional_input_file(
        args.response_path_readiness,
        "--response-path-readiness",
    )
    response_path_report_root = safe_optional_input_dir(
        args.response_path_report_root,
        "--response-path-report-root",
    )
    certificate_path = repo_local_output_file(args.output_certificate, "--output-certificate")

    readiness_surfaces = load_json_file(surfaces_path, "--public-sdk-surfaces")
    upstream_surfaces = load_json_file(
        upstream_surfaces_path,
        "--upstream-public-sdk-surfaces",
    )
    readiness = readiness_report(
        decisions_path=decisions_path,
        surfaces_path=surfaces_path,
        public_header_path=public_header_path,
        response_path_report_path=response_path_report_path,
        response_path_root=response_path_root,
        response_path_readiness=response_path_readiness,
        response_path_report_root=response_path_report_root,
        current_route_blocker=args.current_route_blocker,
    )
    blockers = (
        current_json_payload_blockers(
            payload=readiness_surfaces,
            path=surfaces_path,
            artifact_label="--public-sdk-surfaces",
            reason="public_sdk_surfaces_loaded_payload_stale_or_mismatched",
            label="$.public_sdk_surfaces",
        )
        + current_json_payload_blockers(
            payload=upstream_surfaces,
            path=upstream_surfaces_path,
            artifact_label="--upstream-public-sdk-surfaces",
            reason="upstream_public_sdk_surfaces_loaded_payload_stale_or_mismatched",
            label="$.upstream_public_sdk_surfaces",
        )
        + readiness_source_artifact_blockers(
            readiness=readiness,
            artifacts={
                "decisions_path": decisions_path,
                "surfaces_path": surfaces_path,
                "public_header_path": public_header_path,
                "response_path_report_path": response_path_report_path,
            },
        )
        + preflight_blockers(
            readiness_surfaces=readiness_surfaces,
            upstream_surfaces=upstream_surfaces,
            readiness=readiness,
            current_route_blocker=args.current_route_blocker,
        )
    )
    upstream_chain_valid = not upstream_chain_blockers(upstream_surfaces)
    upstream_response_valid = upstream_response_certificate_valid(upstream_surfaces)
    if blockers:
        report = build_non_claim_report(
            status="blocked",
            certificate_path=certificate_path,
            certificate=None,
            blockers=blockers,
            readiness=readiness,
            upstream_command_response_certificate_valid=upstream_response_valid,
            upstream_promotion_chain_valid=upstream_chain_valid,
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            for blocker in blockers:
                print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
        return 1

    certificate = build_certificate(
        decisions_path=decisions_path,
        surfaces_path=surfaces_path,
        upstream_surfaces_path=upstream_surfaces_path,
        public_header_path=public_header_path,
        response_path_report_path=response_path_report_path,
        response_path_readiness=response_path_readiness,
        readiness=readiness,
        readiness_surfaces=readiness_surfaces,
        upstream_surfaces=upstream_surfaces,
    )
    write_json(certificate_path, certificate)
    report = build_non_claim_report(
        status="built",
        certificate_path=certificate_path,
        certificate=certificate,
        blockers=[],
        readiness=readiness,
        upstream_command_response_certificate_valid=True,
        upstream_promotion_chain_valid=True,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
