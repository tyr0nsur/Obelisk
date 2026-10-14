#!/usr/bin/env python3
"""Tests for prepare_player_principal_lifecycle_evidence_closure_request.py."""

from __future__ import annotations

import json
import hashlib
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_player_principal_lifecycle_evidence_closure_request as closure_request

SCRIPT = SCRIPT_DIR / "prepare_player_principal_lifecycle_evidence_closure_request.py"
RUN_ID = "20260604T171315Z-player-principal-lifecycle"
TEST_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=SCRIPT_DIR.parents[0],
    text=True,
).strip()
STALE_TEST_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD^"],
    cwd=SCRIPT_DIR.parents[0],
    text=True,
).strip()
EXPECTED_MISSING = [
    "window-manifest.env",
    "preflight-post.json",
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
]
REQUIRED_ROLES = [
    "session_start",
    "session_start_rejected",
    "session_end",
]
ALL_SIBLINGS = [
    "Obelisk.log",
    "window-request.json",
    "observer-window.env",
    "operator-approval-request.md",
    "operator-approval-receipt.json",
    "preflight-pre.json",
    "preflight-post.json",
    "window-manifest.env",
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
]
REQUIRED_SIDECARS = [relative for relative in ALL_SIBLINGS if relative != "Obelisk.log"]


def lifecycle_log_text(*, roles: list[str] | tuple[str, ...] = tuple(REQUIRED_ROLES)) -> str:
    lines = [
        "[info] PlayerPrincipalLifecycleObserver enabled binary_sha256=test "
        "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
        "delivery_claim=none principal_claim=none.",
    ]
    if "session_start" in roles:
        lines.append(
            "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
            "target=ShooterGameMode.HandleNewPlayer post_original=true "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
            "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
            "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
    if "session_start_rejected" in roles:
        lines.append(
            "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
            "target=ShooterGameMode.CheckJoinInProgress post_original=true "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
            "redacted_count=1 redacted_fields=NewPlayer "
            "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
    if "session_end" in roles:
        lines.append(
            "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
            "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
            "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
            "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
    return "\n".join(lines) + "\n"


def lifecycle_log_text_without_status_proof_fields() -> str:
    return re.sub(r" apply_status=[^ ]+ correlation_status=[^ ]+", "", lifecycle_log_text())


def lifecycle_log_text_with_session_end_status(apply_status: str, correlation_status: str) -> str:
    return lifecycle_log_text().replace(
        "apply_status=session_end_invalidated correlation_status=matched",
        f"apply_status={apply_status} correlation_status={correlation_status}",
    )


def lifecycle_log_text_with_legacy_handle_new_player_rejected_tuple() -> str:
    return lifecycle_log_text().replace(
        "target=ShooterGameMode.CheckJoinInProgress post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
        "redacted_count=1 redacted_fields=NewPlayer",
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter",
    )


def lifecycle_log_text_with_check_join_rejected_bool_values(copied_bool_values: str) -> str:
    return lifecycle_log_text().replace(
        "target=ShooterGameMode.CheckJoinInProgress post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
        "redacted_count=1 redacted_fields=NewPlayer",
        "target=ShooterGameMode.CheckJoinInProgress post_original=true "
        f"copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values={copied_bool_values} "
        "redacted_count=1 redacted_fields=NewPlayer",
    )


def diagnostic_only_lifecycle_target_log_text() -> str:
    return "\n".join(
        [
            "[info] PlayerPrincipalLifecycleObserver enabled binary_sha256=test "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none.",
            "[info] PlayerPrincipalLifecycleObserver diagnostic target=ShooterGameMode.HandleNewPlayer "
            "diagnostic_only=true player_presence_context=players_detected.",
            "[info] PlayerPrincipalLifecycleObserver diagnostic target=GameMode.K2_PostLogin "
            "diagnostic_only=true player_presence_context=players_detected.",
        ]
    ) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_blocked_ready_log_copy_report(
    evidence_dir: Path,
    *,
    missing_roles: list[str] | tuple[str, ...] = tuple(REQUIRED_ROLES),
    observer_window_state: str | None = None,
) -> None:
    missing_role_list = list(missing_roles)
    roles_present = [role for role in REQUIRED_ROLES if role not in missing_role_list]
    blockers = [
        "blocked_missing_lifecycle_roles",
        *[f"exact_copied_runtime_triplet_missing_{role}" for role in missing_role_list],
    ]
    payload = {
        "schema": closure_request.READY_LOG_COPY_SCHEMA,
        "status": "dry_run_blocked",
        "ready": False,
        **false_sidecar_flags(),
        "instance": "arkserver3",
        "source_log": str(evidence_dir / "source" / "Obelisk.log"),
        "evidence_dir": str(evidence_dir),
        "target_log": str(evidence_dir / "Obelisk.log"),
        "execute_requested": False,
        "allow_live_log_read": False,
        "allow_evidence_dir_write": False,
        "overwrite": False,
        "ready_to_copy": False,
        "copy_readiness": "blocked_missing_lifecycle_roles",
        "copied": False,
        "source_sha256": None,
        "target_existing_sha256": None,
        "target_copied_sha256": None,
        "roles_present": roles_present,
        "missing_roles": missing_role_list,
        "blockers": blockers,
        "source_input": {
            "source_kind": "candidate_runtime_log",
            "status": "accepted_candidate_log_path",
            "counts_as_approved_runtime_evidence": False,
        },
        "source_log_safety": {
            "accepted": True,
            "blockers": [],
            "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence": False,
            "passive_context_counts_as_approved_runtime_evidence": False,
            "unsafe_player_text_counts_as_approved_runtime_evidence": False,
        },
        "analysis": {
            "observer_enabled": True,
            "binary_sha256_match": True,
            "roles_present": roles_present,
            "missing_roles": missing_role_list,
            "ready_to_copy": False,
            "copy_readiness": "blocked_missing_lifecycle_roles",
            "exact_copied_runtime_triplet": {
                "accepted": False,
                "blockers": blockers,
                "copied_log_only_counts_as_approved_runtime_evidence": False,
                "passive_or_diagnostic_material_counts_as_approved_runtime_evidence": False,
            },
        },
        "non_claims": [
            "ready-log copy is operational copy readiness only",
            "copied Obelisk.log is still not approved runtime evidence until sibling-set bundle checkers accept it",
        ],
    }
    if observer_window_state is not None:
        classifications = {
            "in_progress": "observer_enabled_no_lifecycle_roles_window_in_progress",
            "post_window": "observer_enabled_no_lifecycle_roles_post_window",
        }
        post_window = observer_window_state == "post_window"
        active = observer_window_state == "in_progress"
        source_state = {
            "schema": "obelisk.player-principal-lifecycle-source-log-not-ready.v1",
            "classification": classifications[observer_window_state],
            "observer_only_no_role_window_detected": True,
            "active_observer_only_no_role_window": active,
            "post_window_observer_only_no_role_window": post_window,
            "source_log_not_ready": True,
            "source_log_not_ready_reason": classifications[observer_window_state],
            "window_state": observer_window_state,
            "target_hint": {"instance": "arkserver3", "map": "Genesis2"},
            "ready_to_copy": False,
            "copied_log_ready": False,
            "copied_log_available_for_closure": post_window,
            "post_window_closure_action": (
                "close_observer_only_no_role_window_as_non_evidence"
                if post_window
                else None
            ),
            "manual_offline_next_steps": [
                "treat the observer-enable-only window as closed non-evidence"
                if post_window
                else "keep the observer-enable-only window open until fresh_window_end_utc",
                "do not copy or promote the source log until the exact lifecycle triplet is present",
            ],
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
        }
        payload.update(
            {
                "source_log_not_ready": source_state,
                "observer_only_no_role_window": source_state,
                "observer_only_no_role_window_detected": True,
                "observer_only_no_role_window_state": observer_window_state,
                "active_observer_only_no_role_window": active,
                "post_window_observer_only_no_role_window": post_window,
                "post_window_closure_action": source_state["post_window_closure_action"],
            }
        )
    write_json(evidence_dir / "ready-log-copy.json", payload)


def write_confirmed_beta_notice(
    path: Path,
    *,
    instance: str = "arkserver3",
    map_name: str = "Genesis2",
) -> None:
    write_json(
        path,
        {
            "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
            "ready": True,
            "mode": "confirmed_send",
            "discord_sent": True,
            "send_helper_returncode_zero": True,
            "target": {"instance": instance, "map": map_name},
            "run_id": RUN_ID,
            "notice_path": "discord://obelisk-beta-testers",
            "standing_launch_authority_recorded": True,
            "standing_launch_authority_satisfies_notice_scope": True,
            "notice_action_covered_by_standing_launch_authority": True,
        },
    )


def false_sidecar_flags() -> dict[str, bool]:
    return {
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "live_ops_authorized": False,
        "runtime_capture_authorized": False,
        "workspace_writes_authorized": False,
        "reads_live_logs": False,
        "marker_env_changes_authorized": False,
        "approved_runtime_evidence_ready": False,
        "approved_runtime_evidence_present": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "dry_run_success_counts_as_approved_runtime_evidence": False,
        "historical_target_names_authorize_runtime": False,
        "marker_env_readiness_counts_as_approved_runtime_evidence": False,
        "player_notice_counts_as_approved_runtime_evidence": False,
        "public_reachability_counts_as_approved_runtime_evidence": False,
        "request_pack_counts_as_approved_runtime_evidence": False,
        "preflight_counts_as_approved_runtime_evidence": False,
        "window_manifest_counts_as_approved_runtime_evidence": False,
        "completed_receipt_counts_as_approved_runtime_evidence": False,
        "observer_env_counts_as_approved_runtime_evidence": False,
        "operator_request_counts_as_approved_runtime_evidence": False,
        "copied_log_metadata_counts_as_approved_runtime_evidence": False,
        "bundle_output_counts_as_approved_runtime_evidence": False,
        "route_ready": False,
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "counts_toward_sdk": False,
        "counts_toward_v1_completion": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
    }


def write_valid_sidecars(evidence_dir: Path, *, instance: str, map_name: str) -> None:
    request = evidence_dir / "window-request.json"
    observer_env = evidence_dir / "observer-window.env"
    operator_request = evidence_dir / "operator-approval-request.md"
    receipt = evidence_dir / "operator-approval-receipt.json"
    preflight_pre = evidence_dir / "preflight-pre.json"
    preflight_post = evidence_dir / "preflight-post.json"
    manifest = evidence_dir / "window-manifest.env"
    approved_bundle = evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
    target = {"instance": instance, "map": map_name}

    write_json(
        request,
            {
                "schema": "obelisk.player-principal-lifecycle-window-request.v1",
                "status": "candidate_only_request_pack",
                "run_id": RUN_ID,
                "target": target,
                "approved_window": {
                    "start_utc": "2026-06-04T17:00:00Z",
                    "end_utc": "2026-06-04T17:15:00Z",
                },
                "copied_evidence_dir": str(evidence_dir),
                "copied_log_path": str(evidence_dir / "Obelisk.log"),
                "window_manifest_path": str(manifest),
            "authorization_flags": {
                "server_operations_authorized": False,
                "runtime_work_authorized": False,
                "runtime_capture_authorized": False,
            },
        },
    )
    observer_env.write_text(
        "\n".join(
            [
                "# request-pack-only; does not authorize marker/env changes, runtime work, or server operations",
                f"OBELISK_INSTANCE_ID={instance}",
                "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1",
                "OBELISK_DISABLE_PLUGINS=1",
                "OBELISK_WRAPPER_PROFILE=observer-debug",
                "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0",
                "OBELISK_PE_TRACE_LIMIT=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    operator_request.write_text(
        "Operator approval request fixture. This request does not authorize server operations.\n",
        encoding="utf-8",
    )
    bound_request_pack = {
        "run_id": RUN_ID,
        "target": target,
        "copied_evidence_dir": str(evidence_dir),
        "copied_log_path": str(evidence_dir / "Obelisk.log"),
        "window_manifest_path": str(manifest),
    }
    write_json(
        receipt,
        {
            "schema": "obelisk.player-principal-lifecycle-operator-approval-receipt.v1",
            "status": "completed_operator_receipt",
            "receipt_completed": True,
            "operator_current_turn_approval_recorded": True,
            "bound_request_pack": bound_request_pack,
            "bound_artifacts": {
                "window_request_json": {
                    "path": str(request.resolve()),
                    "sha256": sha256(request),
                    "size_bytes": request.stat().st_size,
                },
                "observer_window_env": {
                    "path": str(observer_env.resolve()),
                    "sha256": sha256(observer_env),
                    "size_bytes": observer_env.stat().st_size,
                },
                "operator_approval_request_md": {
                    "path": str(operator_request.resolve()),
                    "sha256": sha256(operator_request),
                    "size_bytes": operator_request.stat().st_size,
                },
            },
            "operator_completion": {
                "approval_recorded_at_utc": "2026-06-04T17:00:00Z",
                "approval_source": "current_turn_operator_message",
                "attestation": "APPROVE_EXACT_BOUND_PLAYER_PRINCIPAL_LIFECYCLE_WINDOW_ONLY",
            },
            "non_authorization_flags": {
                "generated_template_authorizes_runtime": False,
                "server_operations_authorized_by_template": False,
                "runtime_work_authorized_by_template": False,
                "discord_authorized": False,
                "publication_authorized": False,
                "promotion_ready": False,
                "public_abi_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "route_ready": False,
                "v1_completion_ready": False,
                "sdk_accounting_counts_as_completed_surface": False,
                "p0_accounting_counts_as_promoted_surface": False,
            },
        },
    )

    def preflight_payload(mode: str) -> dict[str, Any]:
        return {
            "schema": "obelisk.player-principal-lifecycle-preflight.v1",
            "status": "preflight_passed_no_runtime_approval_or_evidence",
            "ready": True,
            "ready_scope": "offline_preflight_checks_only",
            "preflight_passed": True,
            "current_turn_operator_approval_required": True,
            "run_id": RUN_ID,
            "mode": mode,
            "instance": instance,
            "map": map_name,
            "target": target,
            "window_manifest_path": str(manifest),
            "copied_log_path": str(evidence_dir / "Obelisk.log"),
            "copied_evidence_dir": str(evidence_dir),
            "deployment_intent": {
                "request_only": True,
                "deployment_authorized": False,
                "restart_authorized": False,
                "runtime_capture_authorized": False,
                "counts_as_approved_runtime_evidence": False,
            },
            **false_sidecar_flags(),
        }

    write_json(preflight_pre, preflight_payload("observer-window"))
    write_json(preflight_post, preflight_payload("stable"))
    manifest.write_text(
        "\n".join(
            [
                f"run_id={RUN_ID}",
                f"obelisk_commit={TEST_COMMIT}",
                "approval=current_turn_operator_message_exact_bound_player_principal_lifecycle_window",
                "approved_window_start_utc=2026-06-04T17:00:00Z",
                "approved_window_end_utc=2026-06-04T17:15:00Z",
                "actual_capture_start_utc=2026-06-04T17:00:10Z",
                "actual_capture_end_utc=2026-06-04T17:14:00Z",
                "rollback_start_utc=2026-06-04T17:14:01Z",
                "rollback_end_utc=2026-06-04T17:14:30Z",
                f"copied_log_path={evidence_dir / 'Obelisk.log'}",
                f"copied_log_sha256={sha256(evidence_dir / 'Obelisk.log')}",
                f"request_pack_path={request}",
                f"request_pack_sha256={sha256(request)}",
                f"observer_env_path={observer_env}",
                f"observer_env_sha256={sha256(observer_env)}",
                f"operator_approval_receipt_path={receipt}",
                f"operator_approval_receipt_sha256={sha256(receipt)}",
                f"preflight_pre_path={preflight_pre}",
                f"preflight_pre_sha256={sha256(preflight_pre)}",
                f"preflight_post_path={preflight_post}",
                f"preflight_post_sha256={sha256(preflight_post)}",
                "single_module_summary=player_principal_lifecycle",
                "delivery_claim=none",
                "principal_claim=none",
                "log_budget=10",
                "plugins_disabled=true",
                "scanner_disabled=true",
                "dispatch_limit=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def artifact_binding(path: Path) -> dict[str, str]:
        return {
            "path": str(path),
            "sha256": sha256(path),
        }

    write_json(
        approved_bundle,
        {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
            "artifact_status": "approved_runtime_observer_summary",
            "readiness_classification": "runtime_evidence_only",
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "approval": {
                "runtime_evidence_reviewed": True,
                "reviewed_by": "closure-request-test",
                "review_note": "fixture only",
                "runtime_work_authorized_by_this_manifest": False,
                "server_operations_authorized_by_this_manifest": False,
                "publication_authorized_by_this_manifest": False,
                "discord_authorized_by_this_manifest": False,
            },
            "operational_window": {
                "schema": "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1",
                "ready": True,
                "operational_window_manifest_ready": True,
                "run_id": RUN_ID,
                "obelisk_commit": TEST_COMMIT,
                "target": target,
                "manifest": artifact_binding(manifest),
                "copied_log": artifact_binding(evidence_dir / "Obelisk.log"),
                "request_pack": artifact_binding(request),
                "observer_env": artifact_binding(observer_env),
                "operator_approval_receipt": artifact_binding(receipt),
                "preflight": {
                    "pre": artifact_binding(preflight_pre),
                    "post": artifact_binding(preflight_post),
                },
            },
            "source_summary": {
                "schema": "obelisk.runtime-observer-log-summary.v1",
                "evidence": {
                    "kind": "runtime-observer-log",
                    "server_paths_allowed": False,
                    "obelisk_commit": TEST_COMMIT,
                    "sources": [artifact_binding(evidence_dir / "Obelisk.log")],
                },
                "modules": {
                    "player_principal_lifecycle": {},
                },
            },
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_sdk_ready": False,
            "v1_completion_ready": False,
            "runtime_ready": False,
            "stable_claim_allowed": False,
            "complete_sdk_ready": False,
        },
    )


def write_siblings(
    evidence_dir: Path,
    *,
    missing: set[str] | None = None,
    roles: list[str] | tuple[str, ...] = tuple(REQUIRED_ROLES),
    instance: str = "arkserver2",
    map_name: str = "TheIsland",
) -> None:
    missing = missing or set()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "Obelisk.log").write_text(lifecycle_log_text(roles=roles), encoding="utf-8")
    write_valid_sidecars(evidence_dir, instance=instance, map_name=map_name)
    for relative in missing:
        path = evidence_dir / relative
        if path.exists():
            path.unlink()


def bind_standing_launch_authority_receipt(
    evidence_dir: Path,
    *,
    receipt_instance: str = "arkserver2",
    receipt_map: str = "TheIsland",
) -> None:
    receipt_path = evidence_dir / "operator-approval-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["operator_current_turn_approval_recorded"] = False
    receipt["standing_launch_authority_recorded"] = True
    receipt["standing_launch_authority_satisfies_operator_approval"] = True
    receipt["approval_scope"] = {
        "scope_type": "exact_bound_player_principal_lifecycle_window",
        "standing_approval": True,
        "reusable": False,
        "future_windows_authorized": False,
    }
    receipt["operator_completion"] = {
        "approval_recorded_at_utc": "2026-06-04T17:00:00Z",
        "approval_source": "standing_launch_authority",
        "attestation": "BIND_STANDING_OBELISKSDK_LAUNCH_AUTHORITY_TO_EXACT_PLAYER_PRINCIPAL_LIFECYCLE_WINDOW",
    }
    receipt["bound_request_pack"]["target"] = {"instance": receipt_instance, "map": receipt_map}
    write_json(receipt_path, receipt)

    manifest_path = evidence_dir / "window-manifest.env"
    if not manifest_path.is_file():
        return
    manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    manifest_path.write_text(
        "\n".join(
            (
                f"approval={closure_request.STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT}"
                if line.startswith("approval=")
                else f"operator_approval_receipt_sha256={sha256(receipt_path)}"
                if line.startswith("operator_approval_receipt_sha256=")
                else line
            )
            for line in manifest_lines
        )
        + "\n",
        encoding="utf-8",
    )
    approved_bundle = (
        evidence_dir
        / "approved-bundle"
        / "approved-runtime-principal-lifecycle-evidence.json"
    )
    if approved_bundle.is_file():
        payload = json.loads(approved_bundle.read_text(encoding="utf-8"))
        operational_window = payload.get("operational_window")
        if isinstance(operational_window, dict):
            manifest_binding = operational_window.get("manifest")
            if isinstance(manifest_binding, dict):
                manifest_binding["sha256"] = sha256(manifest_path)
            receipt_binding = operational_window.get("operator_approval_receipt")
            if isinstance(receipt_binding, dict):
                receipt_binding["sha256"] = sha256(receipt_path)
        write_json(approved_bundle, payload)


def base_args(
    evidence_dir: Path,
    *,
    instance: str = "arkserver2",
    map_name: str = "TheIsland",
    query_port: str | None = None,
) -> list[str]:
    args = [
        sys.executable,
        str(SCRIPT),
        "--evidence-dir",
        str(evidence_dir),
        "--instance",
        instance,
        "--map",
        map_name,
        "--the-island-off",
        "--two-server-cap-preserved",
    ]
    if query_port is not None:
        args.extend(["--query-port", query_port])
    return args


def run_report(
    evidence_dir: Path,
    *extra: str,
    instance: str = "arkserver2",
    map_name: str = "TheIsland",
    query_port: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*base_args(evidence_dir, instance=instance, map_name=map_name, query_port=query_port), *extra],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def true_readiness_flags(value: Any, trail: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                key
                in {
                    "public_readiness_claim",
                    "public_sdk_ready",
                    "public_abi_ready",
                    "runtime_ready",
                    "approved_runtime_evidence_ready",
                    "approved_runtime_evidence",
                    "approved_runtime_evidence_present",
                    "runtime_evidence_present",
                    "runtime_evidence_ready",
                    "closure_request_ready",
                    "promotion_ready",
                    "v1_completion_ready",
                    "stable_claim_allowed",
                    "approved_runtime_evidence_accepted_by_checker",
                    "copied_bundle_checker_acceptance_recorded",
                    "sdk_p0_changes_authorized",
                    "server_operations_authorized",
                    "runtime_work_authorized",
                    "live_ops_authorized",
                    "runtime_capture_authorized",
                    "workspace_writes_authorized",
                    "reads_live_logs",
                    "counts_as_approved_runtime_evidence",
                    "counts_as_runtime_evidence",
                    "counts_as_sdk_evidence",
                    "closure_request_counts_as_approved_runtime_evidence",
                    "closure_request_counts_as_runtime_evidence",
                    "closure_request_counts_as_sdk_evidence",
                    "passive_snapshots_as_evidence",
                    "passive_snapshots_count_as_evidence",
                    "passive_snapshot_evidence_allowed",
                    "candidate_sidecars_count_as_approved_runtime_evidence",
                    "passive_complete_triplets_count_as_approved_runtime_evidence",
                    "request_pack_preflight_window_manifest_count_as_approved_runtime_evidence",
                    "status_report_paths_authorize_current_turn",
                    "status_report_paths_count_as_approved_runtime_evidence",
                    "source_material_counts_as_approved_runtime_evidence",
                    "source_material_counts_as_runtime_evidence",
                    "source_material_counts_as_sdk_evidence",
                    "counts_toward_sdk",
                    "closure_request_counts_toward_sdk",
                    "closure_request_counts_toward_p0_dependency_chain",
                    "counts_toward_v1",
                    "counts_toward_v1_completion",
                    "counts_toward_complete_sdk_claim_now",
                    "counts_toward_p0_dependency_chain_claim_now",
                }
                and child is True
            ):
                matches.append(child_trail)
            matches.extend(true_readiness_flags(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(true_readiness_flags(child, f"{trail}[{index}]"))
    return matches


def assert_ready_log_copy_sidecar_flags(test_case: unittest.TestCase, payload: dict[str, Any]) -> None:
    command = payload["command_text_not_executed"]
    for flag in closure_request.READY_LOG_COPY_POST_WINDOW_EXECUTE_FLAGS:
        test_case.assertIn(flag, command)
    test_case.assertEqual(
        payload["copy_helper_execute_sidecar_flags"],
        list(closure_request.READY_LOG_COPY_POST_WINDOW_EXECUTE_FLAGS),
    )
    test_case.assertEqual(
        payload["copy_helper_execute_sidecar_flags_scope"],
        "active_operator_followup_command_only",
    )
    test_case.assertFalse(payload["copy_helper_execute_sidecar_flags_authorize_this_report"])
    test_case.assertFalse(payload["copy_helper_execute_sidecar_flags_count_as_evidence"])
    test_case.assertFalse(payload["post_window_sidecar_generation_authorized_by_this_report"])
    test_case.assertFalse(payload["post_window_preflight_live_read_authorized_by_this_report"])
    test_case.assertFalse(payload["post_window_sidecar_generation_counts_as_approved_runtime_evidence"])
    test_case.assertFalse(payload["post_window_preflight_live_read_counts_as_approved_runtime_evidence"])


class PreparePlayerPrincipalLifecycleEvidenceClosureRequestTests(unittest.TestCase):
    def test_negative_non_authorization_sidecar_text_is_not_a_claim(self) -> None:
        payload = {
            "schema": "obelisk.player-principal-lifecycle-window-request.v1",
            "status": "request_only_not_authorized",
            "deployment_intent": {
                "status": "request_only_not_authorized",
                "non_authorization": (
                    "does not authorize deployment, runtime capture, public SDK readiness, "
                    "or server restart"
                ),
            },
            "non_authorization": (
                "does not authorize deployment, runtime capture, public SDK readiness, "
                "or server restart"
            ),
            "approved_notice_path_must_be_named": "discord-beta-testers",
        }

        self.assertEqual(closure_request.collect_forbidden_sidecar_claims(payload), [])

    def test_negative_non_authorization_context_still_rejects_nested_positive_claim(self) -> None:
        payload = {"non_authorization": {"public_sdk_ready": True}}

        self.assertEqual(
            closure_request.collect_forbidden_sidecar_claims(payload),
            ["$.non_authorization.public_sdk_ready"],
        )

    def test_complete_evidence_dir_reports_no_missing_closure_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            approved_manifest_sha = sha256(
                evidence_dir
                / "approved-bundle"
                / "approved-runtime-principal-lifecycle-evidence.json"
            )
            copied_log_sha = sha256(evidence_dir / "Obelisk.log")

            result = run_report(
                evidence_dir,
                "--reviewed-by",
                "closure-request-test",
                "--review-note",
                "consume-only runtime review",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["status"], "closure_inputs_complete_bundle_checker_required")
        self.assertEqual(report["closure_case"], "closure_inputs_complete_no_readiness")
        self.assertFalse(report["ready"])
        self.assertFalse(report["closure_request_ready"])
        self.assertTrue(report["evidence_closure_inputs_complete"])
        self.assertTrue(report["closure_inputs_complete_but_checker_required"])
        self.assertEqual(
            report["ready_scope"],
            "not_ready_closure_request_is_non_evidence_checker_required_before_any_readiness_claim",
        )
        self.assertTrue(report["complete_sibling_set_present"])
        self.assertEqual(report["required_sibling_set"], ALL_SIBLINGS)
        self.assertEqual(report["missing_expected_sibling_artifacts"], [])
        self.assertEqual(report["required_sidecars"], REQUIRED_SIDECARS)
        self.assertEqual(report["exact_missing_sidecars"], [])
        self.assertEqual(report["missing_required_artifacts"], [])
        self.assertEqual(report["missing_siblings"], [])
        self.assertEqual(
            report["approved_bundle_manifest_relative_path"],
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        )
        self.assertEqual(
            report["approved_bundle_path"],
            str(evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"),
        )
        preconditions = report["post_window_copy_bundle_preconditions"]
        self.assertEqual(preconditions["schema"], closure_request.POST_WINDOW_ACTION_CONTRACT_SCHEMA)
        self.assertTrue(preconditions["dry_run_first_required"])
        self.assertTrue(preconditions["dry_run_must_complete_before_execute"])
        self.assertEqual(preconditions["required_dry_run_artifacts"], [preconditions["dry_run_report_path"]])
        self.assertIn("Obelisk.log", preconditions["expected_sibling_set"])
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            preconditions["expected_sibling_set"],
        )
        self.assertFalse(preconditions["sidecar_generation_authorized_by_this_report"])
        self.assertFalse(preconditions["dry_run_report_authorizes_runtime"])
        self.assertFalse(preconditions["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["approved_bundle_path_checklist"], report["closure_artifact_checklist"])
        self.assertEqual(
            [item["relative_path"] for item in report["closure_artifact_checklist"]],
            ALL_SIBLINGS,
        )
        self.assertEqual(
            [item["status"] for item in report["closure_artifact_checklist"]],
            ["present"] * len(ALL_SIBLINGS),
        )
        self.assertTrue(
            all(
                item["counts_as_approved_runtime_evidence_by_this_report"] is False
                for item in report["closure_artifact_checklist"]
            )
        )
        bindings = report["artifact_hash_path_bindings"]
        self.assertTrue(bindings["copied_log_hash_path_bound"])
        self.assertTrue(bindings["required_sidecars_hash_path_bound"])
        self.assertTrue(bindings["bundle_input_artifacts_hash_path_bound"])
        self.assertTrue(bindings["complete_sibling_set_hash_path_bound"])
        self.assertEqual(bindings["missing_hash_path_bindings"], [])
        self.assertEqual(
            bindings["copied_log"]["sha256"],
            copied_log_sha,
        )
        self.assertEqual(
            bindings["by_relative_path"]["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"][
                "sha256"
            ],
            approved_manifest_sha,
        )
        self.assertFalse(report["artifact_hash_path_bindings_count_as_approved_runtime_evidence"])
        acceptance = report["runtime_evidence_acceptance_state"]
        self.assertEqual(
            acceptance["classification"],
            "accepted_ready_for_checker_not_approved_evidence",
        )
        self.assertTrue(acceptance["accepted_ready_for_checker"])
        self.assertFalse(acceptance["checker_accepted_ready"])
        self.assertFalse(acceptance["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["required_lifecycle_event_role_triplet"], REQUIRED_ROLES)
        self.assertEqual(
            report["required_copied_lifecycle_event_triplet_labels"],
            list(closure_request.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
        )
        self.assertEqual(report["missing_lifecycle_event_roles"], [])
        self.assertEqual(report["missing_copied_lifecycle_event_triplet_labels"], [])
        self.assertTrue(report["lifecycle_event_triplet_complete"])
        self.assertTrue(report["exact_copied_lifecycle_event_triplet_complete"])
        self.assertEqual(report["lifecycle_event_role_state"]["roles_seen"], REQUIRED_ROLES)
        self.assertFalse(report["partial_start_end_present"])
        checker_action = report["machine_next_actions"][0]
        manifest_path = (
            evidence_dir
            / "approved-bundle"
            / "approved-runtime-principal-lifecycle-evidence.json"
        )
        self.assertEqual(checker_action["action_kind"], "checker")
        self.assertEqual(
            checker_action["runner_command"]["argv"],
            [
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                "--json",
                str(manifest_path),
            ],
        )
        self.assertTrue(checker_action["command_path_hash_bound"])
        self.assertEqual(
            checker_action["command_path_binding"]["inputs"][0]["sha256"],
            approved_manifest_sha,
        )
        self.assertFalse(checker_action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["missing_strict_rejected_start"])
        self.assertEqual(
            report["strict_rejected_start_expected_shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            report["strict_rejected_start_observed_shape"]["shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertTrue(
            report["strict_rejected_start_observed_shape"]["accepted_as_strict_rejected_start"]
        )
        self.assertFalse(
            report[
                "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence"
            ]
        )
        self.assertFalse(
            report["strict_rejected_start_observed_shape"][
                "counts_as_approved_runtime_evidence"
            ]
        )
        self.assertEqual(
            [
                item["label"]
                for item in report["lifecycle_event_role_state"][
                    "matched_copied_lifecycle_event_triplet"
                ]
            ],
            list(closure_request.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
        )
        self.assertEqual(report["closure_requirements"]["required_sidecars"], REQUIRED_SIDECARS)
        self.assertEqual(report["closure_requirements"]["exact_missing_sidecars"], [])
        self.assertEqual(report["closure_requirements"]["required_lifecycle_event_role_triplet"], REQUIRED_ROLES)
        self.assertEqual(
            report["closure_requirements"]["required_copied_lifecycle_event_triplet_labels"],
            list(closure_request.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
        )
        self.assertEqual(report["exact_missing_operations"], [])
        self.assertEqual(report["not_executed_commands"], [])
        self.assertEqual(report["machine_next_actions_schema"], closure_request.MACHINE_NEXT_ACTIONS_SCHEMA)
        self.assertEqual(
            [action["action"] for action in report["machine_next_actions"]],
            ["run_approved_runtime_evidence_checker_on_copied_manifest"],
        )
        checker_action = report["machine_next_actions"][0]
        self.assertEqual(
            checker_action["artifact"],
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        )
        self.assertIn(
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            checker_action["command_text_not_executed"],
        )
        pipeline = report["evidence_pipeline_command_sequence"]
        self.assertEqual(
            pipeline["ordered_step_ids"],
            [
                "analyze_runtime_observer_log",
                "strict_lifecycle_triplet_selector",
                "bundle_preflight",
                "approved_runtime_evidence_checker",
            ],
        )
        self.assertEqual(checker_action["evidence_pipeline_command_sequence"], pipeline)
        commands = {item["id"]: item["command_text_not_executed"] for item in pipeline["commands"]}
        self.assertIn("scripts/analyze_runtime_observer_log.py", commands["analyze_runtime_observer_log"])
        self.assertIn(
            "scripts/build_player_identity_runtime_principal_lifecycle_approved_manifest.py",
            commands["strict_lifecycle_triplet_selector"],
        )
        self.assertIn("--preflight-only", commands["bundle_preflight"])
        self.assertIn(
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            commands["approved_runtime_evidence_checker"],
        )
        self.assertFalse(pipeline["restart_recommended"])
        self.assertTrue(pipeline["copied_bundle_checker_acceptance_required_before_sdk_p0_changes"])
        self.assertTrue(pipeline["accepted_checker_required_before_sdk_p0_changes"])
        self.assertFalse(pipeline["approved_runtime_evidence_accepted_by_checker"])
        self.assertFalse(pipeline["copied_bundle_checker_acceptance_recorded"])
        self.assertFalse(pipeline["sdk_p0_changes_authorized"])
        self.assertFalse(pipeline["raw_player_text_or_identity_allowed"])
        self.assertFalse(pipeline["authorization"]["server_operations_authorized"])
        self.assertFalse(pipeline["evidence"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(pipeline["evidence"]["approved_runtime_evidence_accepted_by_checker"])
        self.assertFalse(pipeline["evidence"]["copied_bundle_checker_acceptance_recorded"])
        self.assertFalse(pipeline["evidence"]["sdk_p0_changes_authorized"])
        checker_gate = report["copied_bundle_checker_acceptance_gate"]
        self.assertEqual(checker_gate, report["approved_runtime_evidence_checker_acceptance_gate"])
        self.assertEqual(checker_gate["status"], "checker_acceptance_required")
        self.assertEqual(checker_gate["missing_expected_sibling_artifacts"], [])
        self.assertEqual(checker_gate["missing_lifecycle_event_roles"], [])
        self.assertEqual(checker_gate["blockers"], [])
        self.assertEqual(checker_gate["checker_command_status"], "NOT EXECUTED")
        self.assertIn(
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            checker_gate["checker_command_text_not_executed"],
        )
        self.assertTrue(checker_gate["copied_bundle_checker_acceptance_required_before_sdk_p0_changes"])
        self.assertTrue(checker_gate["accepted_checker_required_before_sdk_p0_changes"])
        self.assertFalse(checker_gate["approved_runtime_evidence_accepted_by_checker"])
        self.assertFalse(checker_gate["copied_bundle_checker_acceptance_recorded"])
        self.assertFalse(checker_gate["sdk_p0_changes_authorized"])
        self.assertFalse(checker_gate["counts_as_approved_runtime_evidence"])
        self.assertFalse(checker_gate["counts_toward_sdk"])
        self.assertFalse(checker_gate["counts_toward_p0_dependency_chain"])
        self.assertTrue(report["copied_bundle_checker_acceptance_required_before_sdk_p0_changes"])
        self.assertTrue(report["accepted_checker_required_before_sdk_p0_changes"])
        self.assertFalse(report["sdk_p0_changes_authorized"])
        boundary = report["authorization_evidence_boundary"]
        self.assertTrue(boundary["authorization_is_not_evidence"])
        self.assertTrue(boundary["evidence_requires_checker_acceptance"])
        self.assertTrue(boundary["copied_bundle_checker_acceptance_required_before_sdk_p0_changes"])
        self.assertTrue(boundary["accepted_checker_required_before_sdk_p0_changes"])
        self.assertFalse(boundary["approved_runtime_evidence_accepted_by_checker"])
        self.assertFalse(boundary["copied_bundle_checker_acceptance_recorded"])
        self.assertFalse(boundary["sdk_p0_changes_authorized"])
        self.assertFalse(boundary["counts_as_approved_runtime_evidence"])
        serialized_report = json.dumps(report, sort_keys=True)
        for flag in closure_request.READY_LOG_COPY_POST_WINDOW_EXECUTE_FLAGS:
            self.assertNotIn(flag, serialized_report)
        self.assertFalse(checker_action["approved_runtime_evidence"])
        self.assertFalse(checker_action["approved_runtime_evidence_accepted_by_checker"])
        self.assertFalse(checker_action["counts_as_approved_runtime_evidence"])
        self.assertTrue(checker_action["copied_bundle_checker_acceptance_required_before_sdk_p0_changes"])
        self.assertTrue(checker_action["accepted_checker_required_before_sdk_p0_changes"])
        self.assertTrue(checker_action["recommended_before_sdk_p0_changes"])
        self.assertEqual(
            checker_action["sdk_p0_changes_blocked_until"],
            ["accepted_approved_runtime_evidence_checker_json"],
        )
        self.assertFalse(checker_action["sdk_p0_changes_authorized"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["workspace_writes_authorized"])
        self.assertFalse(report["live_ops_authorized"])
        self.assertFalse(report["runtime_capture_authorized"])
        self.assertFalse(report["reads_live_logs"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["passive_snapshots_as_evidence"])
        self.assertFalse(report["passive_snapshots_count_as_evidence"])
        self.assertFalse(report["passive_snapshot_evidence_allowed"])
        self.assertFalse(report["candidate_sidecars_count_as_approved_runtime_evidence"])
        self.assertFalse(report["passive_complete_triplets_count_as_approved_runtime_evidence"])
        self.assertFalse(report["request_pack_preflight_window_manifest_count_as_approved_runtime_evidence"])
        self.assertFalse(report["status_report_paths_authorize_current_turn"])
        self.assertFalse(report["status_report_paths_count_as_approved_runtime_evidence"])
        self.assertFalse(report["counts_toward_sdk"])
        self.assertFalse(report["counts_toward_v1"])
        self.assertTrue(report["no_readiness_claim"])
        self.assertEqual(true_readiness_flags(report), [])
        self.assertFalse(report["authorization"]["live_ops_authorized"])
        self.assertFalse(report["authorization"]["runtime_capture_authorized"])
        self.assertFalse(report["authorization"]["reads_live_logs"])
        self.assertFalse(report["authorization"]["approved_runtime_evidence"])
        self.assertFalse(report["authorization"]["passive_snapshots_as_evidence"])
        self.assertFalse(report["authorization"]["counts_toward_sdk"])
        self.assertFalse(report["authorization"]["counts_toward_v1"])
        self.assertFalse(report["lifecycle_event_role_state"]["approved_runtime_evidence"])
        self.assertFalse(report["lifecycle_event_role_state"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["lifecycle_event_role_state"]["passive_snapshots_as_evidence"])
        self.assertFalse(report["lifecycle_event_role_state"]["passive_complete_triplet_counts_as_evidence"])
        self.assertTrue(report["operational_context"]["the_island_off"])
        self.assertTrue(report["operational_context"]["two_server_cap_preserved"])
        self.assertTrue(report["operational_context"]["two_server_cap_required"])
        self.assertEqual(report["operational_context"]["two_server_cap_max_running_servers"], 2)
        self.assertTrue(report["operational_context"]["must_preserve_supplied_operational_constraints"])
        self.assertEqual(
            [item["constraint"] for item in report["operational_context"]["provided_operational_constraints"]],
            ["the_island_off", "two_server_cap"],
        )

    def test_duplicate_valid_lifecycle_role_keeps_closure_inputs_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, instance="arkserver3", map_name="Genesis2")
            lines = (evidence_dir / "Obelisk.log").read_text(encoding="utf-8").splitlines()
            lines.insert(2, lines[1].replace("sequence=1", "sequence=4"))
            (evidence_dir / "Obelisk.log").write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = run_report(
                evidence_dir,
                "--reviewed-by",
                "closure-request-test",
                "--review-note",
                "consume-only runtime review",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertEqual(report["closure_case"], "missing_lifecycle_roles")
        self.assertFalse(report["ready"])
        self.assertFalse(report["evidence_closure_inputs_complete"])
        self.assertFalse(report["lifecycle_event_triplet_complete"])
        self.assertFalse(report["exact_copied_lifecycle_event_triplet_complete"])
        role_state = report["lifecycle_event_role_state"]
        self.assertEqual(role_state["roles_seen"], REQUIRED_ROLES)
        self.assertEqual(role_state["missing_roles"], ["session_start"])
        self.assertEqual(role_state["invalid_lifecycle_event_roles"], ["session_start"])
        self.assertEqual(role_state["duplicate_accepted_role_event_count"], 1)
        self.assertEqual(role_state["duplicate_accepted_roles"], ["session_start"])
        self.assertEqual(
            role_state["duplicate_accepted_role_events"][0]["reason"],
            "copied_lifecycle_event_duplicate_role_proof",
        )
        self.assertEqual(
            role_state["lifecycle_event_ambiguity_blockers"],
            ["copied-lifecycle-triplet-ambiguous/session_start"],
        )
        self.assertEqual(report["missing_lifecycle_event_roles"], ["session_start"])
        self.assertEqual(
            report["missing_copied_lifecycle_event_triplet_labels"],
            ["HandleNewPlayer(1,1)"],
        )
        role_action = next(
            action for action in report["machine_next_actions"] if action.get("role") == "session_start"
        )
        self.assertEqual(
            role_action["lifecycle_event_ambiguity_blockers"],
            ["copied-lifecycle-triplet-ambiguous/session_start"],
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_invalid_run_id_never_counts_as_complete_closure_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = (
                Path(tmp)
                / "live-validation-logs"
                / "passive-manual-20260604T085119Z-arkserver+arkserver2-3215640"
            )
            write_siblings(evidence_dir)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_evidence_source")
        self.assertEqual(report["closure_case"], "invalid_evidence_run_id")
        self.assertFalse(report["ready"])
        self.assertFalse(report["evidence_closure_inputs_complete"])
        self.assertFalse(report["run_id_valid"])
        self.assertTrue(report["evidence_dir_parent_valid"])
        self.assertEqual(
            [blocker["reason"] for blocker in report["evidence_source_blockers"]],
            ["invalid_player_principal_lifecycle_run_id"],
        )
        blocker = report["evidence_source_blockers"][0]
        self.assertTrue(blocker["source_looks_like_passive_monitor_root"])
        self.assertEqual(
            blocker["suggested_closure_run_id"],
            "20260604T085119Z-player-principal-lifecycle",
        )
        self.assertTrue(
            blocker["copy_or_stage_into_closure_compatible_run_required_before_closure"]
        )
        guidance = report["evidence_source_state"]["closure_compatible_copy_guidance"]
        self.assertEqual(guidance["suggested_closure_run_id"], blocker["suggested_closure_run_id"])
        self.assertTrue(guidance["passive_monitor_root_must_not_be_used_as_closure_evidence_dir"])
        self.assertFalse(guidance["passive_monitor_root_accepted_as_closure_evidence_dir"])
        self.assertFalse(guidance["source_becomes_closure_root"])
        self.assertTrue(guidance["explicit_execution_write_flags_required"])
        self.assertFalse(guidance["copy_or_stage_authorized_by_this_report"])
        operation = report["exact_missing_operations"][0]
        self.assertEqual(
            operation["operation"],
            "stage_closure_compatible_player_principal_lifecycle_evidence_root",
        )
        self.assertEqual(operation["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", operation)
        self.assertIn(
            blocker["suggested_closure_run_id"],
            operation["after_manual_staging_closure_request_command_text_not_executed"],
        )
        self.assertEqual(operation["source_evidence_dir"], str(evidence_dir))
        self.assertEqual(operation["invalid_source_evidence_dir"], str(evidence_dir))
        self.assertEqual(
            operation["source_root_role"],
            "source_evidence_root_supplied_to_closure_helper",
        )
        self.assertEqual(
            operation["suggested_valid_closure_root_role"],
            "suggested_valid_closure_root_for_manual_staging",
        )
        self.assertEqual(operation["closure_compatible_evidence_dir"], guidance["suggested_closure_evidence_dir"])
        self.assertEqual(
            operation["suggested_valid_closure_evidence_dir"],
            guidance["suggested_valid_closure_evidence_dir"],
        )
        self.assertFalse(operation["source_becomes_closure_root"])
        self.assertFalse(operation["passive_monitor_root_accepted_as_closure_evidence_dir"])
        self.assertFalse(operation["machine_action_suggested_for_invalid_passive_root"])
        self.assertFalse(operation["machine_executable"])
        self.assertFalse(operation["runner_command_available"])
        self.assertTrue(operation["manual_staging_required_before_machine_actions"])
        self.assertTrue(operation["copy_or_stage_into_closure_compatible_run_required_before_closure"])
        self.assertTrue(operation["explicit_execution_write_flags_required"])
        self.assertFalse(operation["counts_as_approved_runtime_evidence"])
        machine_action = report["machine_next_actions"][0]
        self.assertEqual(machine_action["action_kind"], "invalid_evidence_source")
        self.assertEqual(machine_action["source_evidence_dir"], str(evidence_dir))
        self.assertEqual(machine_action["evidence_dir"], guidance["suggested_closure_evidence_dir"])
        self.assertEqual(machine_action["closure_compatible_evidence_dir"], guidance["suggested_closure_evidence_dir"])
        self.assertEqual(
            machine_action["suggested_valid_closure_evidence_dir"],
            guidance["suggested_valid_closure_evidence_dir"],
        )
        self.assertEqual(machine_action["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", machine_action)
        self.assertFalse(machine_action["machine_action_suggested_for_invalid_passive_root"])
        self.assertFalse(machine_action["machine_executable"])
        self.assertFalse(machine_action["runner_command_available"])
        self.assertTrue(machine_action["manual_staging_required_before_machine_actions"])
        self.assertIn(
            blocker["suggested_closure_run_id"],
            machine_action["after_manual_staging"]["closure_request_command_text_not_executed"],
        )
        self.assertFalse(machine_action["passive_monitor_root_accepted_as_closure_evidence_dir"])
        self.assertTrue(machine_action["explicit_execution_write_flags_required"])
        self.assertFalse(machine_action["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["missing_required_artifacts"], [])
        self.assertEqual(report["missing_lifecycle_event_roles"], [])
        self.assertTrue(report["lifecycle_event_triplet_complete"])
        self.assertFalse(report["source_material_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["source_material_counts_as_runtime_evidence"])
        self.assertFalse(report["source_material_counts_as_sdk_evidence"])
        self.assertTrue(report["current_turn_approval_requirements"]["required_before_missing_operations"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_postpatch_passive_monitor_root_gets_closure_compatible_copy_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = (
                Path(tmp)
                / "live-validation-logs"
                / "20260607T071833Z-postpatch-ragnarok-theisland-monitor"
            )
            write_siblings(evidence_dir)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["closure_case"], "invalid_evidence_run_id")
        blocker = report["evidence_source_blockers"][0]
        self.assertTrue(blocker["source_looks_like_passive_monitor_root"])
        self.assertEqual(
            blocker["suggested_closure_run_id"],
            "20260607T071833Z-player-principal-lifecycle",
        )
        self.assertNotIn("command_text_not_executed", report["exact_missing_operations"][0])
        self.assertIn(
            "20260607T071833Z-player-principal-lifecycle",
            report["exact_missing_operations"][0][
                "after_manual_staging_closure_request_command_text_not_executed"
            ],
        )
        guidance = report["evidence_source_state"]["closure_compatible_copy_guidance"]
        machine_action = report["machine_next_actions"][0]
        self.assertEqual(machine_action["source_evidence_dir"], str(evidence_dir))
        self.assertEqual(
            machine_action["closure_compatible_evidence_dir"],
            guidance["suggested_closure_evidence_dir"],
        )
        self.assertEqual(machine_action["evidence_dir"], guidance["suggested_closure_evidence_dir"])
        self.assertFalse(machine_action["source_becomes_closure_root"])
        self.assertFalse(machine_action["passive_monitor_root_accepted_as_closure_evidence_dir"])
        self.assertFalse(machine_action["machine_action_suggested_for_invalid_passive_root"])
        self.assertFalse(machine_action["machine_executable"])
        self.assertFalse(machine_action["runner_command_available"])
        self.assertNotIn("command_text_not_executed", machine_action)
        self.assertTrue(machine_action["copy_or_stage_into_closure_compatible_run_required_before_closure"])
        self.assertFalse(report["source_material_counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_running_zero_player_passive_monitor_root_invalid_run_id_is_manual_staging_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_dir = (
                root
                / "live-validation-logs"
                / "20260607T071833Z-postpatch-ragnarok-theisland-monitor"
            )
            evidence_dir.mkdir(parents=True)
            monitor_log = root / "post-reboot-passive-monitor.log"
            monitor_log.write_text(
                "tick utc=2026-06-07T07:18:33Z\n"
                "query instance=arkserver3 map=Genesis2 query_port=27017 status=ok "
                "current_map=Genesis2 players=0/70 target_key=arkserver3:Genesis2:27017 "
                "players_current=0 players_max=70 presence_detected=false "
                "detection_source=gamedig_ase_query\n",
                encoding="utf-8",
            )

            result = run_report(
                evidence_dir,
                "--post-reboot-monitor-log",
                str(monitor_log),
                instance="arkserver3",
                map_name="Genesis2",
                query_port="27017",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_evidence_source")
        self.assertEqual(report["closure_case"], "invalid_evidence_run_id")
        self.assertEqual(report["missing_lifecycle_event_roles"], REQUIRED_ROLES)
        self.assertEqual(set(report["missing_required_artifacts"]), set(REQUIRED_SIDECARS))
        self.assertEqual(
            [operation["operation"] for operation in report["exact_missing_operations"]],
            ["stage_closure_compatible_player_principal_lifecycle_evidence_root"],
        )
        operation = report["exact_missing_operations"][0]
        self.assertEqual(operation["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", operation)
        self.assertEqual(operation["missing_lifecycle_event_roles_at_source_root"], REQUIRED_ROLES)
        self.assertEqual(len(operation["deferred_missing_role_offline_next_steps"]), 3)
        self.assertFalse(operation["machine_action_suggested_for_invalid_passive_root"])
        self.assertTrue(operation["manual_staging_required_before_machine_actions"])
        self.assertEqual(report["not_executed_commands"], [])
        action = report["machine_next_actions"][0]
        self.assertEqual(len(report["machine_next_actions"]), 1)
        self.assertEqual(action["action_kind"], "invalid_evidence_source")
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", action)
        self.assertFalse(action["machine_action_suggested_for_invalid_passive_root"])
        self.assertFalse(action["runner_command_available"])
        self.assertEqual(
            action["suggested_valid_closure_run_id"],
            "20260607T071833Z-player-principal-lifecycle",
        )
        monitor_context = report["operational_context"]["post_reboot_monitor_context"]
        self.assertEqual(monitor_context["path"], str(monitor_log))
        self.assertTrue(monitor_context["current_passive_monitor_context_recorded"])
        self.assertFalse(monitor_context["approved_runtime_evidence"])
        self.assertFalse(monitor_context["counts_as_approved_runtime_evidence"])
        serialized = json.dumps(report, sort_keys=True)
        self.assertNotIn("monitor_ark_player_presence_passive.sh", serialized)
        self.assertEqual(true_readiness_flags(report), [])

    def test_passive_snapshot_directory_never_counts_as_complete_closure_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "passive-snapshot-on-detect" / RUN_ID
            write_siblings(evidence_dir)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_evidence_source")
        self.assertEqual(report["closure_case"], "non_live_validation_source_directory")
        self.assertFalse(report["ready"])
        self.assertFalse(report["evidence_closure_inputs_complete"])
        self.assertTrue(report["run_id_valid"])
        self.assertFalse(report["evidence_dir_parent_valid"])
        self.assertEqual(report["evidence_dir_parent"], "passive-snapshot-on-detect")
        self.assertEqual(
            [blocker["reason"] for blocker in report["evidence_source_blockers"]],
            ["evidence_dir_parent_not_live_validation_logs"],
        )
        self.assertEqual(report["missing_required_artifacts"], [])
        self.assertEqual(report["missing_lifecycle_event_roles"], [])
        self.assertTrue(report["lifecycle_event_triplet_complete"])
        self.assertFalse(report["source_material_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["source_material_counts_as_runtime_evidence"])
        self.assertFalse(report["source_material_counts_as_sdk_evidence"])
        self.assertFalse(report["evidence_source_state"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["evidence_source_state"]["counts_as_runtime_evidence"])
        self.assertFalse(report["evidence_source_state"]["counts_as_sdk_evidence"])
        self.assertTrue(report["current_turn_approval_requirements"]["required_before_missing_operations"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_old_format_lifecycle_lines_without_status_proof_do_not_complete_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            (evidence_dir / "Obelisk.log").write_text(
                lifecycle_log_text_without_status_proof_fields(),
                encoding="utf-8",
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertEqual(report["closure_case"], "missing_lifecycle_roles")
        self.assertFalse(report["ready"])
        self.assertFalse(report["lifecycle_event_triplet_complete"])
        role_state = report["lifecycle_event_role_state"]
        self.assertEqual(role_state["candidate_roles_seen"], REQUIRED_ROLES)
        self.assertEqual(role_state["roles_seen"], [])
        self.assertEqual(role_state["missing_roles"], REQUIRED_ROLES)
        self.assertEqual(role_state["invalid_lifecycle_event_roles"], REQUIRED_ROLES)
        self.assertEqual(role_state["event_line_count"], 3)
        self.assertEqual(role_state["accepted_event_line_count"], 0)
        self.assertEqual(
            [failure["reason"] for failure in role_state["status_proof_failures"]],
            ["lifecycle_event_status_proof_mismatch"] * 3,
        )
        self.assertEqual(report["missing_lifecycle_event_roles"], REQUIRED_ROLES)
        self.assertEqual([item["role"] for item in report["exact_missing_operations"]], REQUIRED_ROLES)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_diagnostic_only_target_lines_do_not_complete_copied_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            (evidence_dir / "Obelisk.log").write_text(
                diagnostic_only_lifecycle_target_log_text(),
                encoding="utf-8",
            )

            result = run_report(evidence_dir, instance="arkserver3", map_name="Genesis2")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertEqual(report["closure_case"], "active_genesis2_triplet_incomplete")
        self.assertFalse(report["ready"])
        self.assertFalse(report["lifecycle_event_triplet_complete"])
        self.assertFalse(report["exact_copied_lifecycle_event_triplet_complete"])
        role_state = report["lifecycle_event_role_state"]
        self.assertEqual(role_state["event_line_count"], 0)
        self.assertEqual(role_state["accepted_event_line_count"], 0)
        self.assertEqual(role_state["candidate_roles_seen"], [])
        self.assertEqual(role_state["roles_seen"], [])
        self.assertEqual(role_state["missing_roles"], REQUIRED_ROLES)
        first_operation = report["exact_missing_operations"][0]
        self.assertFalse(
            first_operation["non_evidence_context"][
                "diagnostic_only_handle_new_player_or_k2_post_login_lines_count_as_evidence"
            ]
        )
        self.assertFalse(
            first_operation["non_evidence_context"][
                "player_presence_context_counts_as_approved_runtime_evidence"
            ]
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_blocked_ready_log_copy_report_is_preserved_as_non_evidence_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(
                evidence_dir,
                missing={
                    "Obelisk.log",
                    "window-manifest.env",
                    "preflight-post.json",
                    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                },
                instance="arkserver3",
                map_name="Genesis2",
            )
            write_blocked_ready_log_copy_report(evidence_dir)

            result = run_report(evidence_dir, instance="arkserver3", map_name="Genesis2")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_required_artifacts_and_lifecycle_roles")
        self.assertEqual(report["closure_case"], "active_genesis2_triplet_incomplete")
        self.assertFalse(report["ready"])
        self.assertEqual(report["missing_lifecycle_event_roles"], REQUIRED_ROLES)
        self.assertEqual(report["lifecycle_event_role_state"]["missing_roles"], REQUIRED_ROLES)
        self.assertTrue(report["ready_log_copy_report_present"])
        self.assertTrue(report["blocked_ready_log_copy_report"])
        copy_report = report["ready_log_copy_report"]
        self.assertTrue(copy_report["present"])
        self.assertTrue(copy_report["checked"])
        self.assertEqual(copy_report["classification"], "blocked_ready_log_copy_report_non_evidence")
        self.assertEqual(copy_report["schema"], closure_request.READY_LOG_COPY_SCHEMA)
        self.assertEqual(copy_report["status"], "dry_run_blocked")
        self.assertFalse(copy_report["reported_ready"])
        self.assertFalse(copy_report["ready"])
        self.assertFalse(copy_report["ready_to_copy"])
        self.assertFalse(copy_report["copied"])
        self.assertEqual(copy_report["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertEqual(copy_report["roles_present"], [])
        self.assertEqual(copy_report["missing_roles"], REQUIRED_ROLES)
        self.assertIn("blocked_missing_lifecycle_roles", copy_report["reported_blockers"])
        self.assertIn("blocked_missing_lifecycle_roles", copy_report["blockers"])
        self.assertEqual(copy_report["validation_blockers"], [])
        self.assertFalse(copy_report["accepted_by_approved_sibling_set_checker"])
        self.assertFalse(copy_report["copy_report_counts_as_approved_runtime_evidence"])
        self.assertFalse(copy_report["counts_as_approved_runtime_evidence"])
        self.assertFalse(copy_report["approved_runtime_evidence"])
        self.assertFalse(copy_report["approved_runtime_evidence_present"])
        self.assertFalse(copy_report["approved_runtime_evidence_ready"])
        self.assertEqual(
            report["missing_artifacts_and_roles"]["ready_log_copy_report"]["missing_roles"],
            REQUIRED_ROLES,
        )
        self.assertEqual(
            report["closure_requirements"]["ready_log_copy_report"]["copy_readiness"],
            "blocked_missing_lifecycle_roles",
        )
        self.assertFalse(
            report["closure_requirements"][
                "ready_log_copy_report_counts_as_approved_runtime_evidence"
            ]
        )
        self.assertEqual(true_readiness_flags(report), [])

    def test_post_window_observer_only_ready_log_report_emits_no_copy_or_bundle_commands(self) -> None:
        missing_bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(
                evidence_dir,
                missing={missing_bundle},
                instance="arkserver3",
                map_name="Genesis2",
            )
            (evidence_dir / "Obelisk.log").unlink()
            write_blocked_ready_log_copy_report(
                evidence_dir,
                observer_window_state="post_window",
            )

            result = run_report(
                evidence_dir,
                "--obelisk-commit",
                TEST_COMMIT,
                "--reviewed-by",
                "closure-request-test",
                "--review-note",
                "post-window observer-only no-role fixture",
                instance="arkserver3",
                map_name="Genesis2",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        copy_report = report["ready_log_copy_report"]
        self.assertTrue(copy_report["post_window_observer_only_no_role_window"])
        self.assertFalse(copy_report["active_observer_only_no_role_window"])
        self.assertEqual(copy_report["observer_only_no_role_window_state"], "post_window")
        self.assertEqual(
            copy_report["post_window_closure_action"],
            "close_observer_only_no_role_window_as_non_evidence",
        )
        copy_operation = next(
            operation
            for operation in report["exact_missing_operations"]
            if operation["artifact"] == "Obelisk.log"
        )
        self.assertEqual(
            copy_operation["operation"],
            "close_observer_only_no_role_window_as_non_evidence",
        )
        self.assertEqual(copy_operation["command_status"], "NOT PROVIDED")
        self.assertFalse(copy_operation["runner_command_available"])
        self.assertNotIn("command_text_not_executed", copy_operation)
        self.assertTrue(copy_operation["post_window_observer_only_no_role_window"])
        self.assertFalse(copy_operation["active_observer_only_no_role_window"])
        bundle_operation = next(
            operation
            for operation in report["exact_missing_operations"]
            if operation["artifact"] == missing_bundle
        )
        self.assertEqual(bundle_operation["command_status"], "NOT PROVIDED")
        self.assertFalse(bundle_operation["runner_command_available"])
        self.assertNotIn("command_text_not_executed", bundle_operation)
        self.assertIn(
            "exact_copied_lifecycle_event_triplet_required_before_bundle_command",
            bundle_operation["bundle_command_blockers"],
        )
        serialized_commands = json.dumps(report["not_executed_commands"], sort_keys=True)
        self.assertNotIn("scripts/copy_player_principal_lifecycle_ready_log.py", serialized_commands)
        self.assertNotIn(
            "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
            serialized_commands,
        )
        copy_action = next(
            action
            for action in report["machine_next_actions"]
            if action["artifact"] == "Obelisk.log"
        )
        self.assertEqual(copy_action["command_status"], "NOT PROVIDED")
        self.assertFalse(copy_action["runner_command_available"])
        self.assertNotIn("command_text_not_executed", copy_action)
        self.assertTrue(copy_action["post_window_observer_only_no_role_window"])
        self.assertFalse(copy_action["active_observer_only_no_role_window"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_active_observer_only_ready_log_report_stays_wait_state_without_commands(self) -> None:
        missing_bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(
                evidence_dir,
                missing={missing_bundle},
                instance="arkserver2",
                map_name="TheIsland",
            )
            (evidence_dir / "Obelisk.log").unlink()
            write_blocked_ready_log_copy_report(
                evidence_dir,
                observer_window_state="in_progress",
            )

            result = run_report(
                evidence_dir,
                "--obelisk-commit",
                TEST_COMMIT,
                "--reviewed-by",
                "closure-request-test",
                "--review-note",
                "active observer-only no-role fixture",
                instance="arkserver2",
                map_name="TheIsland",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_required_artifacts_and_lifecycle_roles")
        self.assertFalse(report["ready"])
        copy_report = report["ready_log_copy_report"]
        self.assertTrue(copy_report["active_observer_only_no_role_window"])
        self.assertFalse(copy_report["post_window_observer_only_no_role_window"])
        self.assertEqual(copy_report["observer_only_no_role_window_state"], "in_progress")
        self.assertIsNone(copy_report["post_window_closure_action"])
        self.assertNotIn(
            "close_observer_only_no_role_window_as_non_evidence",
            json.dumps(report, sort_keys=True),
        )
        self.assertEqual(
            [operation["artifact"] for operation in report["exact_missing_operations"]],
            ["Obelisk.log", missing_bundle],
        )
        copy_operation = report["exact_missing_operations"][0]
        self.assertEqual(
            copy_operation["operation"],
            "wait_for_active_observer_only_no_role_window_exact_triplet_or_end",
        )
        self.assertEqual(copy_operation["command_status"], "NOT PROVIDED")
        self.assertFalse(copy_operation["runner_command_available"])
        self.assertTrue(copy_operation["active_observer_only_no_role_window"])
        self.assertFalse(copy_operation["post_window_observer_only_no_role_window"])
        self.assertTrue(copy_operation["active_window_not_closure_ready"])
        self.assertNotIn("command_text_not_executed", copy_operation)
        bundle_operation = report["exact_missing_operations"][1]
        self.assertEqual(bundle_operation["command_status"], "NOT PROVIDED")
        self.assertFalse(bundle_operation["runner_command_available"])
        self.assertNotIn("command_text_not_executed", bundle_operation)
        serialized = json.dumps(report, sort_keys=True)
        for forbidden in (
            "scripts/copy_player_principal_lifecycle_ready_log.py",
            "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
            "scripts/monitor_ark_player_presence_passive.sh",
            "scripts/check_player_principal_lifecycle_preflight.sh",
            "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(report["not_executed_commands"], [])
        action = report["machine_next_actions"][0]
        self.assertEqual(
            action["action"],
            "wait_for_active_observer_only_no_role_window_exact_triplet_or_end",
        )
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertFalse(action["runner_command_available"])
        self.assertTrue(action["active_observer_only_no_role_window"])
        self.assertTrue(action["active_window_not_closure_ready"])
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_onlogout_correlation_drift_remains_rejected_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            (evidence_dir / "Obelisk.log").write_text(
                lifecycle_log_text_with_session_end_status(
                    "session_end_invalidated",
                    "unmatched",
                ),
                encoding="utf-8",
            )

            result = run_report(evidence_dir, instance="arkserver3", map_name="Genesis2")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertFalse(report["ready"])
        role_state = report["lifecycle_event_role_state"]
        self.assertEqual(role_state["roles_seen"], ["session_start", "session_start_rejected"])
        self.assertEqual(role_state["missing_roles"], ["session_end"])
        self.assertTrue(role_state["partial_accepted_lifecycle_role_set"])
        failure = role_state["status_proof_failures"][0]
        self.assertEqual(failure["role"], "session_end")
        self.assertEqual(failure["reason"], "session_end_correlation_status_unmatched")
        self.assertFalse(failure["accepted_as_lifecycle_role"])
        self.assertFalse(failure["counts_as_approved_runtime_evidence"])
        self.assertFalse(role_state["diagnostic_or_rejected_lifecycle_lines_count_as_complete_closure_material"])
        self.assertFalse(role_state["diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence"])
        self.assertFalse(role_state["diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_legacy_handle_new_player_rejected_tuple_does_not_complete_exact_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            evidence_dir.mkdir(parents=True, exist_ok=True)
            (evidence_dir / "Obelisk.log").write_text(
                lifecycle_log_text_with_legacy_handle_new_player_rejected_tuple(),
                encoding="utf-8",
            )
            write_valid_sidecars(evidence_dir, instance="arkserver2", map_name="TheIsland")

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertFalse(report["ready"])
        self.assertFalse(report["lifecycle_event_triplet_complete"])
        self.assertFalse(report["exact_copied_lifecycle_event_triplet_complete"])
        role_state = report["lifecycle_event_role_state"]
        self.assertEqual(role_state["roles_seen"], ["session_start", "session_end"])
        self.assertEqual(role_state["candidate_roles_seen"], REQUIRED_ROLES)
        self.assertEqual(role_state["missing_roles"], ["session_start_rejected"])
        self.assertTrue(role_state["partial_start_end_present"])
        self.assertTrue(role_state["missing_strict_rejected_start"])
        self.assertEqual(
            role_state["strict_rejected_start_expected_shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            role_state["strict_rejected_start_observed_shape"]["shape"],
            "ShooterGameMode.HandleNewPlayer(0,1)",
        )
        self.assertEqual(
            role_state["strict_rejected_start_observed_shape"]["target"],
            "ShooterGameMode.HandleNewPlayer",
        )
        self.assertFalse(
            role_state["strict_rejected_start_observed_shape"]["accepted_as_strict_rejected_start"]
        )
        self.assertFalse(
            role_state["strict_rejected_start_observed_shape"][
                "counts_as_approved_runtime_evidence"
            ]
        )
        self.assertEqual(
            role_state["missing_copied_lifecycle_event_triplet_labels"],
            ["CheckJoinInProgress(1,0)"],
        )
        self.assertEqual(
            [failure["reason"] for failure in role_state["copied_lifecycle_triplet_match_failures"]],
            ["copied_lifecycle_event_target_mismatch"],
        )
        self.assertEqual(report["missing_lifecycle_event_roles"], ["session_start_rejected"])
        self.assertEqual(
            report["missing_copied_lifecycle_event_triplet_labels"],
            ["CheckJoinInProgress(1,0)"],
        )
        action = report["machine_next_actions"][0]
        self.assertEqual(action["role"], "session_start_rejected")
        self.assertEqual(
            action["required_copied_lifecycle_event_triplet_label"],
            "CheckJoinInProgress(1,0)",
        )
        self.assertFalse(action["exact_copied_lifecycle_event_triplet_matched"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_check_join_zero_zero_rejected_start_reports_observed_shape_without_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            evidence_dir.mkdir(parents=True, exist_ok=True)
            (evidence_dir / "Obelisk.log").write_text(
                lifecycle_log_text_with_check_join_rejected_bool_values("0,0"),
                encoding="utf-8",
            )
            write_valid_sidecars(evidence_dir, instance="arkserver2", map_name="TheIsland")

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertFalse(report["ready"])
        self.assertFalse(report["lifecycle_event_triplet_complete"])
        self.assertFalse(report["exact_copied_lifecycle_event_triplet_complete"])
        self.assertTrue(report["partial_start_end_present"])
        self.assertTrue(report["missing_strict_rejected_start"])
        self.assertEqual(
            report["strict_rejected_start_expected_shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        observed_shape = report["strict_rejected_start_observed_shape"]
        self.assertEqual(observed_shape["shape"], "ShooterGameMode.CheckJoinInProgress(0,0)")
        self.assertEqual(observed_shape["target"], "ShooterGameMode.CheckJoinInProgress")
        self.assertEqual(observed_shape["copied_bool_values"], ["0", "0"])
        self.assertEqual(observed_shape["reason"], "copied_lifecycle_event_bool_values_mismatch")
        self.assertFalse(observed_shape["accepted_as_lifecycle_role"])
        self.assertFalse(observed_shape["accepted_as_strict_rejected_start"])
        self.assertFalse(observed_shape["counts_as_approved_runtime_evidence"])
        self.assertFalse(
            report[
                "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence"
            ]
        )
        role_state = report["lifecycle_event_role_state"]
        self.assertEqual(role_state["roles_seen"], ["session_start", "session_end"])
        self.assertEqual(role_state["candidate_roles_seen"], REQUIRED_ROLES)
        self.assertEqual(role_state["missing_roles"], ["session_start_rejected"])
        self.assertEqual(
            [failure["reason"] for failure in role_state["copied_lifecycle_triplet_match_failures"]],
            ["copied_lifecycle_event_bool_values_mismatch"],
        )
        self.assertEqual(
            role_state["copied_lifecycle_triplet_match_failures"][0][
                "observed_copied_bool_values"
            ],
            ["0", "0"],
        )
        self.assertEqual(report["missing_lifecycle_event_roles"], ["session_start_rejected"])
        action = report["machine_next_actions"][0]
        self.assertEqual(action["role"], "session_start_rejected")
        self.assertEqual(
            action["strict_rejected_start_observed_shape"]["shape"],
            "ShooterGameMode.CheckJoinInProgress(0,0)",
        )
        self.assertFalse(
            action[
                "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence"
            ]
        )
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_principal_logging_in_copied_log_does_not_complete_exact_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            evidence_dir.mkdir(parents=True, exist_ok=True)
            (evidence_dir / "Obelisk.log").write_text(
                lifecycle_log_text().replace(
                    "principal_id_logged=false",
                    "principal_id_logged=true",
                ),
                encoding="utf-8",
            )
            write_valid_sidecars(evidence_dir, instance="arkserver2", map_name="TheIsland")

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertFalse(report["ready"])
        self.assertFalse(report["lifecycle_event_triplet_complete"])
        self.assertFalse(report["exact_copied_lifecycle_event_triplet_complete"])
        role_state = report["lifecycle_event_role_state"]
        self.assertEqual(role_state["roles_seen"], [])
        self.assertEqual(role_state["candidate_roles_seen"], REQUIRED_ROLES)
        self.assertEqual(role_state["missing_roles"], REQUIRED_ROLES)
        self.assertEqual(
            [failure["reason"] for failure in role_state["copied_lifecycle_triplet_match_failures"]],
            ["copied_lifecycle_event_principal_id_logged_mismatch"] * 3,
        )
        self.assertEqual(report["missing_lifecycle_event_roles"], REQUIRED_ROLES)
        self.assertEqual(
            report["missing_copied_lifecycle_event_triplet_labels"],
            list(closure_request.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_stale_session_end_material_keeps_role_missing_with_exact_monitor_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            evidence_dir.mkdir(parents=True, exist_ok=True)
            (evidence_dir / "Obelisk.log").write_text(
                lifecycle_log_text_with_session_end_status(
                    "session_end_stale_noop",
                    "stale",
                ),
                encoding="utf-8",
            )
            write_valid_sidecars(evidence_dir, instance="arkserver3", map_name="Genesis2")

            result = run_report(evidence_dir, instance="arkserver3", map_name="Genesis2")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertEqual(report["closure_case"], "active_genesis2_triplet_incomplete")
        self.assertFalse(report["ready"])
        role_state = report["lifecycle_event_role_state"]
        self.assertEqual(role_state["candidate_roles_seen"], REQUIRED_ROLES)
        self.assertEqual(role_state["roles_seen"], ["session_start", "session_start_rejected"])
        self.assertEqual(role_state["missing_roles"], ["session_end"])
        self.assertTrue(role_state["partial_accepted_lifecycle_role_set"])
        self.assertFalse(role_state["partial_accepted_lifecycle_roles_count_as_complete_closure_material"])
        self.assertFalse(role_state["partial_accepted_lifecycle_roles_count_as_approved_runtime_evidence"])
        self.assertFalse(role_state["diagnostic_or_rejected_lifecycle_lines_count_as_complete_closure_material"])
        self.assertFalse(role_state["diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence"])
        self.assertFalse(role_state["diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress"])
        self.assertEqual(role_state["invalid_lifecycle_event_roles"], ["session_end"])
        self.assertEqual(role_state["event_line_count"], 3)
        self.assertEqual(role_state["accepted_event_line_count"], 2)
        failure = role_state["status_proof_failures"][0]
        self.assertEqual(failure["reason"], "session_end_stale_noop_outcome")
        self.assertTrue(failure["stale_missing_role_material"])
        self.assertFalse(failure["accepted_as_lifecycle_role"])
        self.assertFalse(failure["counts_as_missing_role_material"])
        self.assertFalse(failure["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["missing_lifecycle_event_roles"], ["session_end"])
        action = report["machine_next_actions"][0]
        self.assertEqual(
            action["action"],
            "continue_or_request_passive_wait_for_missing_lifecycle_role",
        )
        self.assertEqual(action["role"], "session_end")
        self.assertIn("monitor_ark_player_presence_passive.sh", action["command_text_not_executed"])
        self.assertIn("arkserver3:Genesis2:27017", action["command_text_not_executed"])
        self.assertEqual(report["first_machine_next_action"]["action_id"], action["action_id"])
        self.assertTrue(report["exact_next_command"]["exact_command_available"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_placeholder_preflight_sidecar_never_counts_as_complete_closure_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            (evidence_dir / "preflight-post.json").write_text(
                "fixture for preflight-post.json\n",
                encoding="utf-8",
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertEqual(report["closure_case"], "invalid_or_incomplete_sidecars")
        self.assertFalse(report["ready"])
        self.assertFalse(report["evidence_closure_inputs_complete"])
        self.assertIn("preflight-post.json", report["invalid_sidecars"])
        self.assertIn(
            "sidecar_json_invalid",
            [blocker["reason"] for blocker in report["sidecar_validation_blockers"]],
        )
        self.assertEqual(true_readiness_flags(report), [])

    def test_operator_approval_receipt_template_never_counts_as_complete_closure_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            write_json(
                evidence_dir / "operator-approval-receipt.json",
                {
                    "schema": "obelisk.player-principal-lifecycle-operator-approval-receipt.v1",
                    "status": "generated_template",
                    "receipt_completed": False,
                    "operator_current_turn_approval_recorded": False,
                    "bound_request_pack": {"run_id": RUN_ID},
                    "operator_completion": {
                        "approval_recorded_at_utc": None,
                        "approval_source": None,
                        "attestation": None,
                    },
                    "non_authorization_flags": {
                        "generated_template_authorizes_runtime": False,
                        "server_operations_authorized_by_template": False,
                        "runtime_work_authorized_by_template": False,
                    },
                },
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertFalse(report["ready"])
        self.assertIn("operator-approval-receipt.json", report["invalid_sidecars"])
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("operator_approval_receipt_template_not_completed", reasons)
        self.assertIn("operator_approval_receipt_completed_not_true", reasons)
        self.assertIn("operator_approval_receipt_current_turn_not_recorded", reasons)
        self.assertEqual(true_readiness_flags(report), [])

    def test_stray_operator_receipt_template_invalidates_evidence_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            write_json(
                evidence_dir / "operator-approval-receipt.template.json",
                {
                    "schema": "obelisk.player-principal-lifecycle-operator-approval-receipt.v1",
                    "status": "generated_template",
                    "receipt_completed": False,
                    "generated_template": True,
                    "non_authorization_flags": {
                        "generated_template_authorizes_runtime": False,
                    },
                },
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("operator-approval-receipt.template.json", report["invalid_sidecars"])
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("operator_approval_receipt_template_not_evidence_input", reasons)
        self.assertIn("unexpected_json_sidecar_not_bound_to_expected_sibling_set", reasons)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_stray_beta_notice_sidecar_invalidates_evidence_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            write_json(
                evidence_dir / "beta-notice.confirmed.sidecar.json",
                {
                    "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
                    "ready": True,
                    "mode": "confirmed_send",
                    "discord_sent": True,
                    "target": {"instance": "arkserver2", "map": "TheIsland"},
                    "run_id": RUN_ID,
                    "approved_runtime_evidence": False,
                    "counts_as_approved_runtime_evidence": False,
                },
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("beta-notice.confirmed.sidecar.json", report["invalid_sidecars"])
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("stray_beta_notice_sidecar_not_evidence_input", reasons)
        self.assertIn("sidecar_schema_is_non_evidence_or_status_snapshot", reasons)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_standing_launch_authority_receipt_satisfies_operator_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            bind_standing_launch_authority_receipt(evidence_dir)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["status"], "closure_inputs_complete_bundle_checker_required")
        self.assertFalse(report["ready"])
        self.assertTrue(report["evidence_closure_inputs_complete"])
        self.assertNotIn("operator-approval-receipt.json", report["invalid_sidecars"])
        self.assertEqual(report["sidecar_validation_blockers"], [])
        approval = report["current_turn_approval_requirements"]
        self.assertEqual(report["operator_authority_requirements"], approval)
        self.assertFalse(approval["required_before_missing_operations"])
        self.assertEqual(approval["source_required"], "standing_launch_authority")
        self.assertEqual(approval["operator_authority_source_required"], "standing_launch_authority")
        self.assertFalse(approval["current_turn_operator_approval_required"])
        self.assertFalse(approval["fresh_current_turn_operator_approval_required"])
        self.assertFalse(approval["requires_bound_standing_launch_authority_receipt_before_execution"])
        self.assertTrue(approval["standing_approval_allowed"])
        self.assertTrue(approval["standing_launch_authority_covers_target_run"])
        self.assertTrue(report["standing_launch_authority_covers_target_run"])
        self.assertFalse(approval["server_authorization_granted_by_this_report"])
        self.assertFalse(approval["runtime_capture_authorization_granted_by_this_report"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_standing_launch_authority_missing_bundle_does_not_require_fresh_current_turn(self) -> None:
        missing_bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, missing={missing_bundle})
            bind_standing_launch_authority_receipt(evidence_dir)
            copied_log_sha = sha256(evidence_dir / "Obelisk.log")
            window_manifest_sha = sha256(evidence_dir / "window-manifest.env")

            result = run_report(
                evidence_dir,
                "--reviewed-by",
                "closure-request-test",
                "--review-note",
                "consume-only runtime review",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_required_artifacts")
        self.assertEqual(report["missing_required_artifacts"], [missing_bundle])
        approval = report["current_turn_approval_requirements"]
        self.assertTrue(approval["required_before_missing_operations"])
        self.assertEqual(approval["source_required"], "standing_launch_authority")
        self.assertEqual(approval["operator_authority_source_required"], "standing_launch_authority")
        self.assertFalse(approval["current_turn_operator_approval_required"])
        self.assertFalse(approval["fresh_current_turn_operator_approval_required"])
        self.assertTrue(approval["requires_bound_standing_launch_authority_receipt_before_execution"])
        self.assertTrue(approval["standing_approval_allowed"])
        self.assertTrue(approval["standing_launch_authority_covers_target_run"])
        operation = report["exact_missing_operations"][0]
        self.assertEqual(operation["artifact"], missing_bundle)
        self.assertFalse(operation["authorized_to_run_now"])
        self.assertFalse(operation["requires_current_turn_operator_approval"])
        self.assertFalse(operation["requires_fresh_current_turn_operator_approval"])
        self.assertTrue(operation["requires_operator_authority_before_execution"])
        self.assertTrue(operation["requires_bound_standing_launch_authority_receipt_before_execution"])
        self.assertEqual(operation["operator_authority_source_required"], "standing_launch_authority")
        self.assertFalse(operation["server_operations_authorized"])
        self.assertFalse(operation["runtime_capture_authorized"])
        self.assertFalse(operation["workspace_writes_authorized"])
        self.assertFalse(operation["approved_runtime_evidence"])
        self.assertFalse(operation["counts_as_approved_runtime_evidence"])
        self.assertFalse(operation["passive_snapshots_as_evidence"])
        self.assertNotIn("OBELISK_ALLOW_SERVER_ROOT_WRITES=1", operation["command_text_not_executed"])
        self.assertIn(
            "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
            operation["command_text_not_executed"],
        )
        self.assertIn(TEST_COMMIT, operation["command_text_not_executed"])
        self.assertNotIn("<reviewed-obelisk-commit>", operation["command_text_not_executed"])
        self.assertEqual(
            operation["runner_command"]["argv"][0],
            "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
        )
        self.assertTrue(operation["command_path_hash_bound"])
        self.assertEqual(
            operation["command_path_binding"]["schema"],
            closure_request.COMMAND_PATH_BINDING_SCHEMA,
        )
        binding_inputs = {
            item["relative_path"]: item for item in operation["command_path_binding"]["inputs"]
        }
        self.assertEqual(binding_inputs["Obelisk.log"]["sha256"], copied_log_sha)
        self.assertEqual(
            binding_inputs["window-manifest.env"]["sha256"],
            window_manifest_sha,
        )
        self.assertFalse(operation["command_path_binding"]["counts_as_approved_runtime_evidence"])
        self.assertTrue(operation["bundle_command_commit_binding"]["ready"])
        self.assertEqual(operation["bundle_command_commit_binding"]["command_obelisk_commit"], TEST_COMMIT)
        self.assertEqual(operation["bundle_command_blockers"], [])
        contract = operation["post_window_action_contract"]
        self.assertEqual(contract["schema"], closure_request.POST_WINDOW_ACTION_CONTRACT_SCHEMA)
        self.assertTrue(operation["dry_run_first_required"])
        self.assertTrue(operation["dry_run_must_complete_before_execute"])
        self.assertEqual(operation["required_dry_run_artifacts"], [operation["dry_run_report_path"]])
        self.assertFalse(operation["dry_run_report_authorizes_runtime"])
        self.assertFalse(operation["dry_run_report_counts_as_approved_runtime_evidence"])
        self.assertFalse(operation["sidecar_generation_required"])
        self.assertFalse(operation["sidecar_generation_authorized_by_this_report"])
        self.assertFalse(operation["sidecar_generation_counts_as_approved_runtime_evidence"])
        for relative in (
            "Obelisk.log",
            "window-request.json",
            "observer-window.env",
            "operator-approval-request.md",
            "operator-approval-receipt.json",
            "preflight-pre.json",
            "preflight-post.json",
            "window-manifest.env",
        ):
            with self.subTest(required_before_bundle=relative):
                self.assertIn(relative, operation["blocked_until"])
                self.assertIn(relative, contract["blocked_until"])
        action = report["machine_next_actions"][0]
        self.assertEqual(action["post_window_action_contract"], contract)
        self.assertEqual(action["command_path_binding"], operation["command_path_binding"])
        self.assertEqual(action["runner_command"], operation["runner_command"])
        self.assertTrue(action["command_path_hash_bound"])
        self.assertTrue(action["dry_run_first_required"])
        self.assertEqual(action["required_dry_run_artifacts"], [action["dry_run_report_path"]])
        self.assertFalse(action["dry_run_report_authorizes_runtime"])
        self.assertFalse(action["dry_run_report_counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_missing_bundle_without_review_metadata_does_not_emit_placeholder_command(self) -> None:
        missing_bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, missing={missing_bundle})
            bind_standing_launch_authority_receipt(evidence_dir)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        operation = report["exact_missing_operations"][0]
        self.assertEqual(operation["artifact"], missing_bundle)
        self.assertEqual(operation["command_status"], "NOT PROVIDED")
        self.assertTrue(operation["command_text_not_emitted"])
        self.assertFalse(operation["runner_command_available"])
        self.assertNotIn("command_text_not_executed", operation)
        self.assertEqual(
            operation["bundle_command_blockers"],
            [
                "reviewed_by_required_for_direct_bundle_command",
                "review_note_required_for_direct_bundle_command",
            ],
        )
        self.assertTrue(operation["bundle_command_commit_binding"]["ready"])
        action = report["machine_next_actions"][0]
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertFalse(action["runner_command_available"])
        self.assertNotIn("command_text_not_executed", action)
        self.assertEqual(report["not_executed_commands"], [])

    def test_missing_bundle_with_stale_manifest_commit_does_not_emit_stale_command(self) -> None:
        missing_bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, missing={missing_bundle})
            bind_standing_launch_authority_receipt(evidence_dir)
            manifest_path = evidence_dir / "window-manifest.env"
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8").replace(
                    f"obelisk_commit={TEST_COMMIT}",
                    f"obelisk_commit={STALE_TEST_COMMIT}",
                ),
                encoding="utf-8",
            )

            result = run_report(
                evidence_dir,
                "--obelisk-commit",
                TEST_COMMIT,
                "--reviewed-by",
                "closure-request-test",
                "--review-note",
                "consume-only runtime review",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        operation = report["exact_missing_operations"][0]
        self.assertEqual(operation["artifact"], missing_bundle)
        self.assertEqual(operation["command_status"], "NOT PROVIDED")
        self.assertTrue(operation["command_text_not_emitted"])
        self.assertNotIn("command_text_not_executed", operation)
        self.assertIn(
            "window_manifest_obelisk_commit_not_current_head",
            operation["bundle_command_blockers"],
        )
        self.assertIn(
            "bundle_command_obelisk_commit_argument_mismatch",
            operation["bundle_command_blockers"],
        )
        self.assertFalse(operation["bundle_command_commit_binding"]["ready"])
        self.assertEqual(
            operation["bundle_command_commit_binding"]["window_manifest_obelisk_commit"],
            STALE_TEST_COMMIT,
        )
        self.assertEqual(operation["bundle_command_commit_binding"]["current_obelisk_commit"], TEST_COMMIT)
        self.assertEqual(report["not_executed_commands"], [])

    def test_missing_copied_log_gets_explicit_ready_copy_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, missing=set(EXPECTED_MISSING))
            (evidence_dir / "Obelisk.log").unlink()
            bind_standing_launch_authority_receipt(evidence_dir)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            report["status"],
            "non_ready_missing_required_artifacts_and_lifecycle_roles",
        )
        expected_missing_sibling_artifacts = [
            "Obelisk.log",
            "preflight-post.json",
            "window-manifest.env",
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        ]
        self.assertFalse(report["complete_sibling_set_present"])
        self.assertEqual(report["required_sibling_set"], ALL_SIBLINGS)
        self.assertEqual(
            report["missing_expected_sibling_artifacts"],
            expected_missing_sibling_artifacts,
        )
        self.assertEqual(
            report["missing_artifacts_and_roles"]["missing_expected_sibling_artifacts"],
            expected_missing_sibling_artifacts,
        )
        self.assertEqual(
            report["closure_requirements"]["missing_expected_sibling_artifacts"],
            expected_missing_sibling_artifacts,
        )
        self.assertEqual(
            report["copied_bundle_checker_acceptance_gate"]["missing_expected_sibling_artifacts"],
            expected_missing_sibling_artifacts,
        )
        self.assertEqual(
            report["copied_bundle_checker_acceptance_gate"]["status"],
            "blocked_until_complete_sibling_set_exact_triplet_and_valid_sidecars",
        )
        self.assertEqual(
            report["copied_bundle_checker_acceptance_gate"]["checker_command_status"],
            "NOT PROVIDED",
        )
        self.assertIsNone(
            report["copied_bundle_checker_acceptance_gate"]["checker_command_text_not_executed"]
        )
        first_operation = report["exact_missing_operations"][0]
        self.assertEqual(first_operation["artifact"], "lifecycle-role/session_start")
        self.assertEqual(
            first_operation["operation"],
            "continue_or_request_passive_wait_for_missing_lifecycle_role",
        )
        copy_operation = next(
            operation
            for operation in report["exact_missing_operations"]
            if operation["artifact"] == "Obelisk.log"
        )
        self.assertEqual(
            copy_operation["operation"],
            "copy_ready_player_principal_lifecycle_obelisk_log",
        )
        self.assertIn(
            "scripts/copy_player_principal_lifecycle_ready_log.py",
            copy_operation["command_text_not_executed"],
        )
        self.assertTrue(copy_operation["approved_window"]["valid"])
        self.assertIn("--fresh-window-start-utc", copy_operation["command_text_not_executed"])
        self.assertIn("2026-06-04T17:00:00Z", copy_operation["command_text_not_executed"])
        self.assertIn("--fresh-window-end-utc", copy_operation["command_text_not_executed"])
        self.assertIn("2026-06-04T17:15:00Z", copy_operation["command_text_not_executed"])
        self.assertIn("--allow-live-log-read", copy_operation["command_text_not_executed"])
        self.assertIn("--allow-evidence-dir-write", copy_operation["command_text_not_executed"])
        self.assertIn("--execute", copy_operation["command_text_not_executed"])
        assert_ready_log_copy_sidecar_flags(self, copy_operation)
        copy_contract = copy_operation["post_window_action_contract"]
        self.assertEqual(copy_contract["schema"], closure_request.POST_WINDOW_ACTION_CONTRACT_SCHEMA)
        self.assertTrue(copy_operation["dry_run_first_required"])
        self.assertTrue(copy_operation["dry_run_must_complete_before_execute"])
        self.assertEqual(copy_operation["required_dry_run_artifacts"], [copy_operation["dry_run_report_path"]])
        self.assertTrue(copy_operation["sidecar_generation_required"])
        self.assertFalse(copy_operation["sidecar_generation_authorized_by_this_report"])
        self.assertFalse(copy_operation["sidecar_generation_counts_as_approved_runtime_evidence"])
        self.assertFalse(copy_operation["dry_run_report_authorizes_runtime"])
        self.assertFalse(copy_operation["dry_run_report_counts_as_approved_runtime_evidence"])
        self.assertEqual(
            copy_operation["blocked_until"],
            [
                "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
                "copied-lifecycle-triplet/CheckJoinInProgress(1,0)",
                "copied-lifecycle-triplet/OnLogout matched",
            ],
        )
        self.assertEqual(
            copy_operation["missing_copied_lifecycle_event_triplet_labels"],
            list(closure_request.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
        )
        self.assertFalse(copy_operation["exact_copied_lifecycle_event_triplet_matched"])
        self.assertFalse(copy_operation["approved_runtime_evidence"])
        self.assertFalse(copy_operation["counts_as_approved_runtime_evidence"])
        copy_command = next(
            command["command"]
            for command in report["not_executed_commands"]
            if command["artifact"] == "Obelisk.log"
        )
        for flag in closure_request.READY_LOG_COPY_POST_WINDOW_EXECUTE_FLAGS:
            self.assertIn(flag, copy_command)
        copy_action = next(
            action
            for action in report["machine_next_actions"]
            if action["artifact"] == "Obelisk.log"
        )
        assert_ready_log_copy_sidecar_flags(self, copy_action)
        self.assertEqual(copy_action["post_window_action_contract"], copy_contract)
        self.assertTrue(copy_action["dry_run_first_required"])
        self.assertEqual(copy_action["required_dry_run_artifacts"], [copy_action["dry_run_report_path"]])
        self.assertFalse(copy_action["reads_live_logs"])
        self.assertFalse(copy_action["approved_runtime_evidence"])
        self.assertFalse(copy_action["counts_as_approved_runtime_evidence"])
        first_action = report["machine_next_actions"][0]
        self.assertEqual(first_action["artifact"], "lifecycle-role/session_start")
        self.assertEqual(
            first_action["action"],
            "continue_or_request_passive_wait_for_missing_lifecycle_role",
        )
        self.assertFalse(first_action["approved_runtime_evidence"])
        self.assertFalse(first_action["reads_live_logs"])

    def test_current_turn_missing_copied_log_copy_action_includes_post_window_sidecar_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            (evidence_dir / "Obelisk.log").unlink()

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        copy_operation = next(
            operation
            for operation in report["exact_missing_operations"]
            if operation["artifact"] == "Obelisk.log"
        )
        self.assertTrue(copy_operation["requires_current_turn_operator_approval"])
        self.assertTrue(copy_operation["requires_fresh_current_turn_operator_approval"])
        self.assertFalse(copy_operation["requires_bound_standing_launch_authority_receipt_before_execution"])
        self.assertEqual(
            copy_operation["operator_authority_source_required"],
            closure_request.FRESH_CURRENT_TURN_OPERATOR_MESSAGE_SOURCE,
        )
        assert_ready_log_copy_sidecar_flags(self, copy_operation)
        self.assertFalse(copy_operation["reads_live_logs"])
        self.assertFalse(copy_operation["approved_runtime_evidence"])
        self.assertFalse(copy_operation["counts_as_approved_runtime_evidence"])
        copy_action = next(
            action
            for action in report["machine_next_actions"]
            if action["artifact"] == "Obelisk.log"
        )
        assert_ready_log_copy_sidecar_flags(self, copy_action)
        self.assertFalse(copy_action["reads_live_logs"])
        self.assertFalse(copy_action["approved_runtime_evidence"])
        self.assertFalse(copy_action["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_standing_launch_authority_markdown_names_bound_receipt_not_fresh_current_turn(self) -> None:
        missing_bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, missing={missing_bundle})
            bind_standing_launch_authority_receipt(evidence_dir)

            result = run_report(evidence_dir, "--format", "markdown")

        self.assertNotEqual(result.returncode, 0)
        markdown = result.stdout
        self.assertIn("## Operator Authority Requirements", markdown)
        self.assertNotIn("## Current-Turn Approval Requirements", markdown)
        self.assertIn("source_required=standing_launch_authority", markdown)
        self.assertIn("operator_authority_source_required=standing_launch_authority", markdown)
        self.assertIn("current_turn_operator_approval_required=false", markdown)
        self.assertIn("fresh_current_turn_operator_approval_required=false", markdown)
        self.assertIn("requires_bound_standing_launch_authority_receipt_before_execution=true", markdown)
        self.assertIn("standing_approval_allowed=true", markdown)
        self.assertNotIn("source_required=fresh_current_turn_operator_message", markdown)
        self.assertNotIn("requires_current_turn_operator_approval=true", markdown)
        self.assertIn("approved_runtime_evidence=false", markdown)
        self.assertIn("counts_as_approved_runtime_evidence=false", markdown)
        self.assertIn("no_readiness_claim=true", markdown)

    def test_standing_launch_authority_target_mismatch_falls_back_to_current_turn_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, instance="arkserver3", map_name="Genesis2")
            bind_standing_launch_authority_receipt(
                evidence_dir,
                receipt_instance="arkserver2",
                receipt_map="TheIsland",
            )

            result = run_report(evidence_dir, instance="arkserver3", map_name="Genesis2")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertFalse(report["standing_launch_authority_covers_target_run"])
        standing = report["standing_launch_authority"]
        self.assertFalse(standing["covers_target_run"])
        self.assertIn(
            "standing_launch_authority_receipt_instance_mismatch",
            [blocker["reason"] for blocker in standing["blockers"]],
        )
        self.assertIn(
            "operator_approval_receipt_instance_mismatch",
            [blocker["reason"] for blocker in report["sidecar_validation_blockers"]],
        )
        approval = report["current_turn_approval_requirements"]
        self.assertTrue(approval["required_before_missing_operations"])
        self.assertEqual(approval["source_required"], "fresh_current_turn_operator_message")
        self.assertTrue(approval["current_turn_operator_approval_required"])
        self.assertTrue(approval["fresh_current_turn_operator_approval_required"])
        self.assertFalse(approval["standing_approval_allowed"])
        self.assertFalse(approval["requires_bound_standing_launch_authority_receipt_before_execution"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_standing_launch_authority_does_not_accept_status_bundle_shortcut(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            bind_standing_launch_authority_receipt(evidence_dir)
            write_json(
                evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json",
                {
                    "schema": "obelisk.public-sdk-v1-approved-in-game-evidence-status.v1",
                    "status": "accepted",
                    "approved_runtime_evidence_ready": True,
                    "status_report_paths_authorize_current_turn": True,
                },
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertTrue(report["standing_launch_authority_covers_target_run"])
        approval = report["current_turn_approval_requirements"]
        self.assertEqual(approval["source_required"], "standing_launch_authority")
        self.assertFalse(approval["fresh_current_turn_operator_approval_required"])
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            report["invalid_sidecars"],
        )
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("sidecar_schema_is_non_evidence_or_status_snapshot", reasons)
        self.assertIn("approved_runtime_manifest_schema_mismatch", reasons)
        self.assertIn("sidecar_forbidden_authorization_or_readiness_claim", reasons)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["status_report_paths_authorize_current_turn"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_passive_snapshot_bundle_sidecar_never_counts_as_complete_closure_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            write_json(
                evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json",
                {
                    "schema": "obelisk.player-principal-passive-snapshot.v1",
                    "status": "ready",
                    "ready": True,
                    "accepted": True,
                    "counts_as_approved_runtime_evidence": True,
                },
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertFalse(report["ready"])
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            report["invalid_sidecars"],
        )
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("sidecar_schema_is_non_evidence_or_status_snapshot", reasons)
        self.assertIn("approved_runtime_manifest_schema_mismatch", reasons)
        self.assertIn("sidecar_forbidden_authorization_or_readiness_claim", reasons)
        self.assertEqual(true_readiness_flags(report), [])

    def test_notice_prep_sidecar_never_substitutes_for_approved_runtime_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            write_json(
                evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json",
                {
                    "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
                    "ready": True,
                    "mode": "confirmed_send",
                    "discord_sent": True,
                    "notice_action_counts_as_approved_runtime_evidence": False,
                },
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            report["invalid_sidecars"],
        )
        blockers = report["sidecar_validation_blockers"]
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("sidecar_schema_is_non_evidence_or_status_snapshot", reasons)
        self.assertIn("approved_runtime_manifest_schema_mismatch", reasons)
        self.assertIn("sidecar_forbidden_authorization_or_readiness_claim", reasons)
        self.assertEqual(true_readiness_flags(report), [])

    def test_public_check_or_report_sidecar_never_substitutes_for_approved_runtime_bundle(self) -> None:
        cases = (
            (
                "public_reachability",
                {
                    "schema": "obelisk.player-principal-public-reachability-check.v1",
                    "ready": True,
                    "public_reachability_ready": True,
                    "public_reachability_counts_as_approved_runtime_evidence": True,
                },
            ),
            (
                "approved_evidence_check_report",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "ready": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
            ),
            (
                "bundle_report",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
                    "status": "accepted",
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "public_sdk_ready": True,
                },
            ),
            (
                "runtime_observer_summary",
                {
                    "schema": "obelisk.runtime-observer-log-summary.v1",
                    "review_scope": "runtime_observer_evidence_summary",
                    "readiness_gate": "none",
                    "ready": False,
                    "evidence": {
                        "kind": "runtime-observer-log",
                        "server_paths_allowed": False,
                        "sources": [],
                    },
                    "modules": {},
                },
            ),
            (
                "closure_request_report",
                {
                    "schema": "obelisk.player-principal-lifecycle-evidence-closure-request.v1",
                    "status": "closure_inputs_complete",
                    "ready": True,
                    "counts_as_approved_runtime_evidence": False,
                },
            ),
            (
                "public_sdk_completion_check",
                {
                    "schema": "obelisk.public-sdk-v1-completion-check.v1",
                    "status": "blocked",
                    "ready": False,
                    "approved_in_game_evidence_ready": False,
                    "sdk_completion": {"progress_ratio": "0/12"},
                },
            ),
            (
                "public_sdk_completion_summary",
                {
                    "schema": "obelisk.public-sdk-v1-completion-summary.v1",
                    "status": "blocked",
                    "ready": False,
                    "sdk_completion": {"status": "blocked", "progress_ratio": "0/12"},
                },
            ),
            (
                "approved_in_game_evidence_status",
                {
                    "schema": "obelisk.approved-in-game-evidence-status.v1",
                    "approved_runtime_evidence_ready": False,
                    "complete_sdk_progress_ratio": "0/12",
                    "p0_dependency_chain_progress_ratio": "0/4",
                },
            ),
            (
                "public_sdk_progress_normalization_trace",
                {
                    "schema": "obelisk.public-sdk-v1-progress-normalization-trace.v1",
                    "status_report_only": True,
                    "status": "blocked",
                    "ready": False,
                    "source_overclaim_total_flag_count": 0,
                    "complete_sdk_progress_ratio": "0/12",
                    "p0_chain_progress_ratio": "0/4",
                },
            ),
            (
                "scoped_release_statement",
                {
                    "schema": "obelisk.scoped-release-statement-outcomes.v1",
                    "status": "blocked",
                    "ready": False,
                    "release_ready": False,
                },
            ),
            (
                "installed_sdk_package_shape",
                {
                    "schema": "obelisk.installed-sdk-package-shape.v1",
                    "status": "package-shape-evidence-only",
                    "cmakePackagePassed": False,
                    "packageShapeCountsTowardCompletion": False,
                },
            ),
            (
                "generic_player_notice_action",
                {
                    "schema": "obelisk.player-notice-action.v1",
                    "mode": "dry_run",
                    "status": "blocked",
                    "discord_sent": False,
                },
            ),
        )
        for name, payload in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
                    write_siblings(evidence_dir)
                    write_json(
                        evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json",
                        payload,
                    )

                    result = run_report(evidence_dir)
                    report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["status"], "non_ready_invalid_sidecars")
                self.assertIn(
                    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                    report["invalid_sidecars"],
                )
                reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
                self.assertIn("sidecar_schema_is_non_evidence_or_status_snapshot", reasons)
                self.assertIn("approved_runtime_manifest_schema_mismatch", reasons)
                if any(
                    value is True or value == "accepted"
                    for key, value in payload.items()
                    if key != "status_report_only"
                ):
                    self.assertIn("sidecar_forbidden_authorization_or_readiness_claim", reasons)
                self.assertEqual(true_readiness_flags(report), [])

    def test_handoff_and_cleanup_alias_sidecars_never_substitute_for_approved_runtime_bundle(self) -> None:
        cases = (
            (
                "compact_context_checkpoint",
                "obelisk.compact-context-checkpoint.v1",
                "handoff_or_cleanup_checkpoint_schema_is_not_approved_runtime_evidence",
            ),
            (
                "codex_cleanup_report",
                "obelisk.codex-cleanup-report.v1",
                "handoff_or_cleanup_checkpoint_schema_is_not_approved_runtime_evidence",
            ),
            (
                "package_shape_install_success",
                "obelisk.package-shape-install-success.v1",
                "package_shape_or_install_schema_is_not_approved_runtime_evidence",
            ),
            (
                "generated_approved_bundle",
                "obelisk.generated-approved-bundle.v1",
                "generated_artifact_or_bundle_schema_is_not_approved_runtime_evidence",
            ),
        )
        for name, schema, expected_reason in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
                    write_siblings(evidence_dir)
                    write_json(
                        evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json",
                        {
                            "schema": schema,
                            "status": "blocked",
                            "ready": False,
                        },
                    )

                    result = run_report(evidence_dir)
                    report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["status"], "non_ready_invalid_sidecars")
                self.assertIn(
                    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                    report["invalid_sidecars"],
                )
                reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
                self.assertIn(expected_reason, reasons)
                self.assertIn("approved_runtime_manifest_schema_mismatch", reasons)
                self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_window_request_bound_to_different_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, instance="arkserver3", map_name="Genesis2")
            request_path = evidence_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["target"] = {"instance": "arkserver", "map": "Ragnarok"}
            write_json(request_path, request)

            result = run_report(evidence_dir, instance="arkserver3", map_name="Genesis2")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("window-request.json", report["invalid_sidecars"])
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("window_request_instance_mismatch", reasons)
        self.assertIn("window_request_map_mismatch", reasons)
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_preflight_bound_to_different_copied_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            preflight_path = evidence_dir / "preflight-post.json"
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            preflight["copied_log_path"] = str(evidence_dir.parent / "other-run" / "Obelisk.log")
            write_json(preflight_path, preflight)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("preflight-post.json", report["invalid_sidecars"])
        blockers = report["sidecar_validation_blockers"]
        self.assertIn(
            "preflight_copied_log_path_mismatch",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_old_preflight_schema_as_stale_closure_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            preflight_path = evidence_dir / "preflight-pre.json"
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
            preflight["schema"] = "obelisk.player-principal-lifecycle-preflight.v0"
            write_json(preflight_path, preflight)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("preflight-pre.json", report["invalid_sidecars"])
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("preflight_schema_mismatch", reasons)
        self.assertIn("preflight_stale_schema_is_not_accepted", reasons)
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_approved_runtime_bundle_bound_to_different_copied_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            bundle_path = evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["operational_window"] = {
                "run_id": RUN_ID,
                "target": {"instance": "arkserver2", "map": "TheIsland"},
                "copied_log": {
                    "path": str(evidence_dir.parent / "other-run" / "Obelisk.log"),
                    "sha256": sha256(evidence_dir / "Obelisk.log"),
                },
            }
            write_json(bundle_path, bundle)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            report["invalid_sidecars"],
        )
        self.assertIn(
            "approved_runtime_manifest_copied_log_path_mismatch",
            [blocker["reason"] for blocker in report["sidecar_validation_blockers"]],
        )
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_approved_runtime_bundle_with_stale_copied_log_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            bundle_path = evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["operational_window"] = {
                "run_id": RUN_ID,
                "target": {"instance": "arkserver2", "map": "TheIsland"},
                "copied_log": {
                    "path": str(evidence_dir / "Obelisk.log"),
                    "sha256": hashlib.sha256(b"stale-log").hexdigest(),
                },
            }
            write_json(bundle_path, bundle)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            report["invalid_sidecars"],
        )
        self.assertIn(
            "approved_runtime_manifest_copied_log_sha256_mismatch",
            [blocker["reason"] for blocker in report["sidecar_validation_blockers"]],
        )
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_extra_approved_bundle_sidecar_even_when_exact_bundle_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            canonical = evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
            stale = evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.stale.json"
            stale_payload = json.loads(canonical.read_text(encoding="utf-8"))
            stale_payload["operational_window"] = {
                "run_id": "20260604T180000Z-player-principal-lifecycle",
                "target": {"instance": "arkserver3", "map": "Genesis2"},
                "copied_log": {
                    "path": str(evidence_dir / "Obelisk.log"),
                    "sha256": hashlib.sha256(b"stale-log").hexdigest(),
                },
            }
            write_json(stale, stale_payload)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.stale.json",
            report["invalid_sidecars"],
        )
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("unexpected_approved_bundle_sidecar_not_exact_relative_path", reasons)
        self.assertIn("approved_runtime_manifest_not_exact_approved_bundle_relative_path", reasons)
        self.assertFalse(report["ready"])
        self.assertFalse(report["evidence_closure_inputs_complete"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_approved_bundle_at_wrong_relative_path_when_exact_bundle_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(
                evidence_dir,
                missing={"approved-bundle/approved-runtime-principal-lifecycle-evidence.json"},
            )
            write_json(
                evidence_dir / "approved-runtime-principal-lifecycle-evidence.json",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                    "artifact_status": "approved_runtime_observer_summary",
                    "readiness_classification": "runtime_evidence_only",
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "approval": {
                        "runtime_evidence_reviewed": True,
                        "runtime_work_authorized_by_this_manifest": False,
                        "server_operations_authorized_by_this_manifest": False,
                        "publication_authorized_by_this_manifest": False,
                        "discord_authorized_by_this_manifest": False,
                    },
                    "operational_window": {"run_id": RUN_ID},
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_abi_ready": False,
                    "public_sdk_ready": False,
                    "v1_completion_ready": False,
                    "runtime_ready": False,
                    "stable_claim_allowed": False,
                    "complete_sdk_ready": False,
                },
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            report["exact_missing_sidecars"],
        )
        self.assertIn("approved-runtime-principal-lifecycle-evidence.json", report["invalid_sidecars"])
        reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
        self.assertIn("unexpected_json_sidecar_not_bound_to_expected_sibling_set", reasons)
        self.assertIn("approved_runtime_manifest_not_exact_approved_bundle_relative_path", reasons)
        self.assertFalse(report["ready"])
        self.assertFalse(report["evidence_closure_inputs_complete"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_mixed_valid_invalid_evidence_aliases_inside_array_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            request_path = evidence_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["evidence_candidates"] = [
                {"counts_as_approved_runtime_evidence": False},
                {"approved_runtime_evidence_present": True},
            ]
            write_json(request_path, request)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("window-request.json", report["invalid_sidecars"])
        blockers = report["sidecar_validation_blockers"]
        self.assertIn(
            "sidecar_forbidden_authorization_or_readiness_claim",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertIn(
            "$.evidence_candidates[1].approved_runtime_evidence_present",
            [blocker.get("claim_path") for blocker in blockers],
        )
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_nested_approved_manifest_schema_inside_required_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            request_path = evidence_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["audit"] = [
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                    "approved_runtime_evidence_present": False,
                    "runtime_evidence_ready": False,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                }
            ]
            write_json(request_path, request)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("window-request.json", report["invalid_sidecars"])
        blockers = report["sidecar_validation_blockers"]
        self.assertIn(
            "sidecar_nested_approved_runtime_manifest_schema",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertIn("$.audit[0].schema", [blocker.get("claim_path") for blocker in blockers])
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_camelcase_progress_sidecar_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            request_path = evidence_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["sdkProgress"] = 1
            write_json(request_path, request)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("window-request.json", report["invalid_sidecars"])
        blockers = report["sidecar_validation_blockers"]
        self.assertIn(
            "sidecar_forbidden_authorization_or_readiness_claim",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertIn("$.sdkProgress", [blocker.get("claim_path") for blocker in blockers])
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_split_sidecar_claim_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            bundle_path = evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            bundle["nested_claim"] = {
                "field": "publicSdkReady",
                "value": "yes",
            }
            bundle["nested_value_less_claim"] = {
                "name": "runtimeReady",
            }
            write_json(bundle_path, bundle)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            report["invalid_sidecars"],
        )
        blockers = report["sidecar_validation_blockers"]
        self.assertIn(
            "sidecar_forbidden_authorization_or_readiness_claim",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertIn("$.nested_claim", [blocker.get("claim_path") for blocker in blockers])
        self.assertIn("$.nested_value_less_claim", [blocker.get("claim_path") for blocker in blockers])
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_nested_approved_bundle_claim_aliases_without_exact_proof(self) -> None:
        cases = (
            ("evidence_approved", {"evidence": {"approved": True}}, "$.evidence.approved"),
            ("runtime_observed", {"runtime": {"observed": True}}, "$.runtime.observed"),
            ("player_session_accepted", {"playerSessions": [{"accepted": True}]}, "$.playerSessions[0].accepted"),
            (
                "lifecycle_proof_validated",
                {"lifecycle": {"proof": {"status": "validated"}}},
                "$.lifecycle.proof.status",
            ),
            ("bundle_ready", {"bundle": {"ready": True}}, "$.bundle.ready"),
            ("sidecar_complete", {"sidecar": {"complete": True}}, "$.sidecar.complete"),
            ("artifact_status_accepted", {"artifact": {"status": "accepted"}}, "$.artifact.status"),
        )
        for name, alias_payload, claim_path in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
                    write_siblings(evidence_dir)
                    bundle_path = (
                        evidence_dir
                        / "approved-bundle"
                        / "approved-runtime-principal-lifecycle-evidence.json"
                    )
                    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
                    bundle.update(alias_payload)
                    write_json(bundle_path, bundle)

                    result = run_report(evidence_dir)
                    report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["status"], "non_ready_invalid_sidecars")
                self.assertIn(
                    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                    report["invalid_sidecars"],
                )
                blockers = report["sidecar_validation_blockers"]
                self.assertIn(
                    "sidecar_forbidden_authorization_or_readiness_claim",
                    [blocker["reason"] for blocker in blockers],
                )
                self.assertIn(claim_path, [blocker.get("claim_path") for blocker in blockers])
                self.assertEqual(true_readiness_flags(report), [])

    def test_status_accepted_without_manifest_identity_never_accepts_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            write_json(
                evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                    "status": "accepted",
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "operational_window": {"run_id": RUN_ID},
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_abi_ready": False,
                    "public_sdk_ready": False,
                    "v1_completion_ready": False,
                    "runtime_ready": False,
                    "stable_claim_allowed": False,
                    "complete_sdk_ready": False,
                },
            )

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            report["invalid_sidecars"],
        )
        blockers = report["sidecar_validation_blockers"]
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("sidecar_forbidden_authorization_or_readiness_claim", reasons)
        self.assertIn("approved_runtime_manifest_artifact_status_mismatch", reasons)
        self.assertIn("approved_runtime_manifest_readiness_classification_mismatch", reasons)
        self.assertIn("approved_runtime_manifest_approval_missing", reasons)
        self.assertIn("$.status", [blocker.get("claim_path") for blocker in blockers])
        self.assertFalse(report["ready"])
        self.assertFalse(report["evidence_closure_inputs_complete"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_non_bundle_schema_aliases_even_with_accepted_manifest_fields(self) -> None:
        cases = (
            (
                "preactivation_executor_artifact",
                "obelisk.player-principal-lifecycle-preactivation-executor-output.v1",
                "preactivation_or_executor_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "runtime_window_executor_artifact",
                "obelisk.player-principal-lifecycle-runtime-window-executor-artifact.v1",
                "preactivation_or_executor_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "request_pack",
                "obelisk.player-principal-lifecycle-window-request.v1",
                "request_pack_or_window_request_schema_is_not_approved_runtime_evidence",
            ),
            (
                "player_notice_action",
                "obelisk.player-principal-lifecycle-player-notice-action.v1",
                "notice_action_schema_is_not_approved_runtime_evidence",
            ),
            (
                "historical_candidate",
                "obelisk.player-principal-lifecycle-historical-candidate.v1",
                "historical_or_candidate_schema_is_not_approved_runtime_evidence",
            ),
            (
                "generic_status_report",
                "obelisk.player-principal-lifecycle-generic-status-report.v1",
                "status_summary_schema_is_not_approved_runtime_evidence",
            ),
        )
        for name, schema, alias_reason in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
                    write_siblings(evidence_dir)
                    write_json(
                        evidence_dir
                        / "approved-bundle"
                        / "approved-runtime-principal-lifecycle-evidence.json",
                        {
                            "schema": schema,
                            "artifact_status": "approved_runtime_observer_summary",
                            "readiness_classification": "runtime_evidence_only",
                            "approved_runtime_evidence_present": True,
                            "runtime_evidence_ready": True,
                            "approval": {
                                "runtime_evidence_reviewed": True,
                                "runtime_work_authorized_by_this_manifest": False,
                                "server_operations_authorized_by_this_manifest": False,
                                "publication_authorized_by_this_manifest": False,
                                "discord_authorized_by_this_manifest": False,
                            },
                            "operational_window": {"run_id": RUN_ID},
                            "promotion_ready": False,
                            "public_header_allowed": False,
                            "public_abi_ready": False,
                            "public_sdk_ready": False,
                            "v1_completion_ready": False,
                            "runtime_ready": False,
                            "stable_claim_allowed": False,
                            "complete_sdk_ready": False,
                        },
                    )

                    result = run_report(evidence_dir)
                    report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["status"], "non_ready_invalid_sidecars")
                self.assertIn(
                    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                    report["invalid_sidecars"],
                )
                reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
                self.assertIn("approved_runtime_manifest_schema_mismatch", reasons)
                self.assertIn(alias_reason, reasons)
                self.assertFalse(report["ready"])
                self.assertFalse(report["evidence_closure_inputs_complete"])
                self.assertFalse(report["approved_runtime_evidence"])
                self.assertFalse(report["counts_as_approved_runtime_evidence"])
                self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_passive_notice_status_shortcut_bundle_aliases(self) -> None:
        cases = (
            (
                "passive_shortcut",
                "obelisk.player-principal-lifecycle-passive-shortcut.v1",
                "passive_or_triplet_schema_is_not_approved_runtime_evidence",
            ),
            (
                "watcher_context",
                "obelisk.player-principal-lifecycle-watcher-context.v1",
                "passive_or_triplet_schema_is_not_approved_runtime_evidence",
            ),
            (
                "notice_shortcut",
                "obelisk.player-principal-lifecycle-beta-notice-shortcut.v1",
                "notice_action_schema_is_not_approved_runtime_evidence",
            ),
            (
                "status_shortcut",
                "obelisk.player-principal-lifecycle-status-shortcut.v1",
                "status_summary_schema_is_not_approved_runtime_evidence",
            ),
        )
        for name, schema, alias_reason in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
                    write_siblings(evidence_dir)
                    write_json(
                        evidence_dir
                        / "approved-bundle"
                        / "approved-runtime-principal-lifecycle-evidence.json",
                        {
                            "schema": schema,
                            "artifact_status": "approved_runtime_observer_summary",
                            "readiness_classification": "runtime_evidence_only",
                            "approved_runtime_evidence_present": True,
                            "runtime_evidence_ready": True,
                            "approval": {
                                "runtime_evidence_reviewed": True,
                                "runtime_work_authorized_by_this_manifest": False,
                                "server_operations_authorized_by_this_manifest": False,
                                "publication_authorized_by_this_manifest": False,
                                "discord_authorized_by_this_manifest": False,
                            },
                            "operational_window": {"run_id": RUN_ID},
                            "promotion_ready": False,
                            "public_header_allowed": False,
                            "public_abi_ready": False,
                            "public_sdk_ready": False,
                            "v1_completion_ready": False,
                            "runtime_ready": False,
                            "stable_claim_allowed": False,
                            "complete_sdk_ready": False,
                        },
                    )

                    result = run_report(evidence_dir)
                    report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["status"], "non_ready_invalid_sidecars")
                self.assertIn(
                    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                    report["invalid_sidecars"],
                )
                reasons = [blocker["reason"] for blocker in report["sidecar_validation_blockers"]]
                self.assertIn("approved_runtime_manifest_schema_mismatch", reasons)
                self.assertIn(alias_reason, reasons)
                invalid_action = report["machine_next_actions"][0]
                self.assertEqual(
                    invalid_action["action"],
                    "replace_invalid_sidecar_with_exact_required_artifact",
                )
                self.assertIn(
                    "passive_snapshot_or_triplet_shortcut",
                    invalid_action["forbidden_shortcut_alias_classes"],
                )
                self.assertFalse(invalid_action["approved_runtime_evidence"])
                self.assertFalse(invalid_action["counts_as_approved_runtime_evidence"])
                self.assertEqual(true_readiness_flags(report), [])

    def test_rejects_support_package_label_sidecar_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            request_path = evidence_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["supportPackage"] = "approved"
            request["package_label"] = "runtime evidence accepted"
            write_json(request_path, request)

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_invalid_sidecars")
        self.assertIn("window-request.json", report["invalid_sidecars"])
        blockers = report["sidecar_validation_blockers"]
        self.assertIn(
            "sidecar_forbidden_authorization_or_readiness_claim",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertIn("$.supportPackage", [blocker.get("claim_path") for blocker in blockers])
        self.assertIn("$.package_label", [blocker.get("claim_path") for blocker in blockers])
        self.assertEqual(true_readiness_flags(report), [])

    def test_historical_theisland_missing_sidecars_is_non_ready_and_lists_exact_missing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, missing=set(EXPECTED_MISSING))

            result = run_report(evidence_dir)
            report = json.loads(result.stdout)

            self.assertFalse((evidence_dir / "window-manifest.env").exists())
            self.assertFalse((evidence_dir / "preflight-post.json").exists())
            self.assertFalse(
                (
                    evidence_dir
                    / "approved-bundle"
                    / "approved-runtime-principal-lifecycle-evidence.json"
                ).exists()
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_required_artifacts")
        self.assertEqual(report["closure_case"], "historical_theisland_missing_sidecars")
        self.assertFalse(report["ready"])
        self.assertEqual(report["target"]["instance"], "arkserver2")
        self.assertEqual(report["target"]["map"], "TheIsland")
        self.assertEqual(report["target"]["query_port"], "27016")
        self.assertEqual(report["target"]["target_key"], "arkserver2:TheIsland:27016")
        self.assertEqual(report["required_sidecars"], REQUIRED_SIDECARS)
        self.assertEqual(report["exact_missing_sidecars"], EXPECTED_MISSING)
        self.assertFalse(report["complete_sibling_set_present"])
        self.assertEqual(report["required_sibling_set"], ALL_SIBLINGS)
        self.assertEqual(
            report["missing_expected_sibling_artifacts"],
            ["preflight-post.json", "window-manifest.env", *EXPECTED_MISSING[2:]],
        )
        self.assertEqual(report["required_lifecycle_event_role_triplet"], REQUIRED_ROLES)
        self.assertEqual(report["missing_required_artifacts"], EXPECTED_MISSING)
        self.assertEqual(report["missing_siblings"], EXPECTED_MISSING)
        self.assertEqual(report["missing_lifecycle_event_roles"], [])
        self.assertTrue(report["lifecycle_event_triplet_complete"])
        self.assertEqual(report["missing_artifacts_and_roles"]["missing_required_artifacts"], EXPECTED_MISSING)
        self.assertEqual(report["missing_artifacts_and_roles"]["required_sidecars"], REQUIRED_SIDECARS)
        self.assertEqual(report["missing_artifacts_and_roles"]["exact_missing_sidecars"], EXPECTED_MISSING)
        self.assertEqual(report["missing_artifacts_and_roles"]["required_lifecycle_event_role_triplet"], REQUIRED_ROLES)
        self.assertEqual(report["missing_artifacts_and_roles"]["missing_lifecycle_event_roles"], [])
        self.assertEqual(report["closure_requirements"]["exact_missing_sidecars"], EXPECTED_MISSING)
        checklist_by_relative_path = {
            item["relative_path"]: item for item in report["closure_artifact_checklist"]
        }
        self.assertEqual(
            list(checklist_by_relative_path),
            ALL_SIBLINGS,
        )
        for relative_path in EXPECTED_MISSING:
            self.assertEqual(checklist_by_relative_path[relative_path]["status"], "missing")
            self.assertEqual(
                checklist_by_relative_path[relative_path]["blockers"],
                [{"reason": "required_artifact_missing", "relative_path": relative_path}],
            )
            self.assertFalse(
                checklist_by_relative_path[relative_path][
                    "counts_as_approved_runtime_evidence_by_this_report"
                ]
            )
        self.assertEqual(
            checklist_by_relative_path[
                "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
            ]["required_for"],
            "approved_runtime_principal_lifecycle_evidence_bundle_output",
        )
        self.assertEqual([item["artifact"] for item in report["exact_missing_operations"]], EXPECTED_MISSING)
        serialized_missing_operations = json.dumps(report["exact_missing_operations"], sort_keys=True)
        for flag in closure_request.READY_LOG_COPY_POST_WINDOW_EXECUTE_FLAGS:
            self.assertNotIn(flag, serialized_missing_operations)
        for operation in report["exact_missing_operations"]:
            self.assertFalse(operation["authorized_to_run_now"])
            self.assertTrue(operation["requires_current_turn_operator_approval"])
            self.assertFalse(operation["live_ops_authorized"])
            self.assertFalse(operation["runtime_capture_authorized"])
            self.assertFalse(operation["workspace_writes_authorized"])
            self.assertFalse(operation["reads_live_logs"])
            self.assertFalse(operation["approved_runtime_evidence"])
            self.assertFalse(operation["counts_as_approved_runtime_evidence"])
            self.assertFalse(operation["passive_snapshots_as_evidence"])
            self.assertFalse(operation["counts_toward_sdk"])
            self.assertFalse(operation["counts_toward_v1"])
        self.assertTrue(report["not_executed_commands"])
        for command in report["not_executed_commands"]:
            self.assertEqual(command["status"], "NOT EXECUTED")
        approval = report["current_turn_approval_requirements"]
        self.assertTrue(approval["required_before_missing_operations"])
        self.assertFalse(approval["server_authorization_granted_by_this_report"])
        self.assertFalse(approval["workspace_write_authorization_granted_by_this_report"])
        self.assertFalse(approval["live_ops_authorization_granted_by_this_report"])
        self.assertFalse(approval["runtime_capture_authorization_granted_by_this_report"])
        self.assertFalse(approval["live_log_reads_authorized_by_this_report"])
        self.assertFalse(approval["approved_runtime_evidence_granted_by_this_report"])
        self.assertFalse(approval["passive_snapshots_count_as_evidence_by_this_report"])
        self.assertFalse(approval["status_report_paths_authorize_current_turn"])
        self.assertEqual(approval["required_scope"]["missing_artifacts"], EXPECTED_MISSING)
        self.assertEqual(approval["required_scope"]["missing_sidecars"], EXPECTED_MISSING)
        self.assertEqual(approval["required_scope"]["required_lifecycle_event_role_triplet"], REQUIRED_ROLES)
        self.assertEqual(approval["required_scope"]["missing_lifecycle_event_roles"], [])
        self.assertTrue(approval["required_scope"]["must_name_exact_target"])
        self.assertTrue(approval["required_scope"]["must_preserve_two_server_cap"])
        self.assertEqual(approval["required_scope"]["two_server_cap_max_running_servers"], 2)
        self.assertTrue(approval["required_scope"]["must_preserve_the_island_off_when_supplied"])
        self.assertTrue(approval["required_scope"]["must_preserve_two_server_cap_when_supplied"])

    def test_active_genesis2_missing_session_end_is_non_ready_and_lists_missing_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(
                evidence_dir,
                roles=("session_start", "session_start_rejected"),
                instance="arkserver3",
                map_name="Genesis2",
            )

            result = run_report(evidence_dir, instance="arkserver3", map_name="Genesis2")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "non_ready_missing_lifecycle_roles")
        self.assertEqual(report["closure_case"], "active_genesis2_triplet_incomplete")
        self.assertFalse(report["ready"])
        self.assertEqual(report["target"]["instance"], "arkserver3")
        self.assertEqual(report["target"]["map"], "Genesis2")
        self.assertEqual(report["target"]["query_port"], "27017")
        self.assertEqual(report["target"]["target_key"], "arkserver3:Genesis2:27017")
        self.assertEqual(report["missing_required_artifacts"], [])
        self.assertEqual(report["missing_lifecycle_event_roles"], ["session_end"])
        self.assertFalse(report["lifecycle_event_triplet_complete"])
        self.assertEqual(
            report["lifecycle_event_role_state"]["roles_seen"],
            ["session_start", "session_start_rejected"],
        )
        self.assertTrue(report["lifecycle_event_role_state"]["partial_accepted_lifecycle_role_set"])
        self.assertFalse(
            report["lifecycle_event_role_state"][
                "partial_accepted_lifecycle_roles_count_as_complete_closure_material"
            ]
        )
        self.assertFalse(
            report["lifecycle_event_role_state"][
                "partial_accepted_lifecycle_roles_count_as_approved_runtime_evidence"
            ]
        )
        self.assertEqual(report["missing_artifacts_and_roles"]["missing_required_artifacts"], [])
        self.assertEqual(report["missing_artifacts_and_roles"]["missing_lifecycle_event_roles"], ["session_end"])
        self.assertEqual([item["role"] for item in report["exact_missing_operations"]], ["session_end"])
        operation = report["exact_missing_operations"][0]
        self.assertFalse(operation["authorized_to_run_now"])
        self.assertTrue(operation["requires_current_turn_operator_approval"])
        self.assertFalse(operation["writes_under_evidence_dir"])
        self.assertFalse(operation["writes_under_server_root"])
        self.assertFalse(operation["live_ops_authorized"])
        self.assertFalse(operation["runtime_capture_authorized"])
        self.assertFalse(operation["reads_live_logs"])
        self.assertFalse(operation["approved_runtime_evidence"])
        self.assertFalse(operation["passive_snapshots_as_evidence"])
        self.assertFalse(operation["counts_toward_sdk"])
        self.assertFalse(operation["counts_toward_v1"])
        self.assertIn("scripts/monitor_ark_player_presence_passive.sh", operation["command_text_not_executed"])
        self.assertIn("arkserver3:Genesis2:27017", operation["command_text_not_executed"])
        self.assertEqual(report["not_executed_commands"][0]["status"], "NOT EXECUTED")
        approval = report["current_turn_approval_requirements"]
        self.assertTrue(approval["required_before_missing_operations"])
        self.assertEqual(approval["required_scope"]["missing_artifacts"], [])
        self.assertEqual(approval["required_scope"]["missing_lifecycle_event_roles"], ["session_end"])
        self.assertTrue(approval["required_scope"]["must_bind_missing_roles_when_runtime_observation_is_requested"])
        self.assertTrue(approval["required_scope"]["must_preserve_two_server_cap"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["live_ops_authorized"])
        self.assertFalse(report["runtime_capture_authorized"])
        self.assertFalse(report["reads_live_logs"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["passive_snapshots_as_evidence"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_machine_next_actions_route_missing_artifact_and_role_to_exact_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(
                evidence_dir,
                missing={"preflight-post.json"},
                roles=("session_start", "session_start_rejected"),
                instance="arkserver3",
                map_name="Genesis2",
            )

            result = run_report(evidence_dir, instance="arkserver3", map_name="Genesis2")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            report["status"],
            "non_ready_missing_required_artifacts_and_lifecycle_roles",
        )
        actions_by_artifact = {
            action["artifact"]: action for action in report["machine_next_actions"]
        }
        self.assertEqual(
            set(actions_by_artifact),
            {"preflight-post.json", "lifecycle-role/session_end"},
        )
        artifact_action = actions_by_artifact["preflight-post.json"]
        self.assertEqual(artifact_action["action"], "capture_post_window_stable_preflight_json")
        self.assertEqual(artifact_action["action_kind"], "missing_artifact")
        self.assertEqual(artifact_action["command_status"], "NOT PROVIDED")
        self.assertFalse(artifact_action["runner_command_available"])
        self.assertNotIn("command_text_not_executed", artifact_action)
        self.assertIn(
            "copied-lifecycle-triplet/OnLogout matched",
            artifact_action["blocked_until"],
        )
        self.assertIn(
            "command withheld until exact copied lifecycle triplet is present",
            artifact_action["blocker"],
        )
        self.assertIn(
            "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py",
            artifact_action["after_completion"]["closure_request_command_text_not_executed"],
        )
        self.assertFalse(artifact_action["authorized_by_this_report"])
        self.assertFalse(artifact_action["approved_runtime_evidence"])
        self.assertFalse(artifact_action["counts_as_approved_runtime_evidence"])
        role_action = actions_by_artifact["lifecycle-role/session_end"]
        self.assertEqual(
            role_action["action"],
            "continue_or_request_passive_wait_for_missing_lifecycle_role",
        )
        self.assertEqual(role_action["role"], "session_end")
        self.assertIn("scripts/monitor_ark_player_presence_passive.sh", role_action["command_text_not_executed"])
        self.assertIn("arkserver3:Genesis2:27017", role_action["command_text_not_executed"])
        self.assertFalse(role_action["runtime_capture_authorized"])
        self.assertFalse(role_action["reads_live_logs"])
        self.assertFalse(role_action["approved_runtime_evidence_accepted_by_checker"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_post_reboot_context_paths_are_non_evidence_missing_action_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            evidence_dir = tmp_path / "live-validation-logs" / RUN_ID
            monitor_log = tmp_path / "passive-monitor-post-reboot.log"
            confirmed_notice = tmp_path / "beta-notice.confirmed.json"
            write_siblings(
                evidence_dir,
                roles=("session_start", "session_start_rejected"),
                instance="arkserver3",
                map_name="Genesis2",
            )

            result = run_report(
                evidence_dir,
                "--post-reboot-monitor-log",
                str(monitor_log),
                "--confirmed-beta-notice-json",
                str(confirmed_notice),
                instance="arkserver3",
                map_name="Genesis2",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([action["action"] for action in report["machine_next_actions"]], [
            "continue_or_request_passive_wait_for_missing_lifecycle_role",
        ])
        monitor_context = report["operational_context"]["post_reboot_monitor_context"]
        self.assertEqual(monitor_context["path"], str(monitor_log))
        self.assertTrue(monitor_context["path_supplied"])
        self.assertTrue(monitor_context["stale_pid_safety_context_recorded"])
        self.assertTrue(monitor_context["current_passive_monitor_context_recorded"])
        self.assertFalse(monitor_context["read_by_this_report"])
        self.assertFalse(monitor_context["server_operations_authorized"])
        self.assertFalse(monitor_context["live_ops_authorized"])
        self.assertFalse(monitor_context["runtime_capture_authorized"])
        self.assertFalse(monitor_context["approved_runtime_evidence"])
        self.assertFalse(monitor_context["counts_as_approved_runtime_evidence"])
        self.assertFalse(monitor_context["counts_as_sdk_evidence"])
        self.assertFalse(monitor_context["counts_toward_sdk"])
        self.assertFalse(monitor_context["counts_toward_p0_dependency_chain"])
        self.assertFalse(monitor_context["counts_toward_p0_dependency_chain_claim_now"])
        self.assertEqual(monitor_context["sdk_progress"], 0)
        self.assertEqual(monitor_context["p0_progress"], 0)
        notice_context = report["operational_context"]["confirmed_beta_notice_context"]
        self.assertEqual(notice_context["path"], str(confirmed_notice))
        self.assertTrue(notice_context["path_supplied"])
        self.assertTrue(notice_context["confirmed_notice_action_context_recorded"])
        self.assertTrue(notice_context["read_by_this_report"])
        self.assertTrue(notice_context["path_existence_checked_by_this_report"])
        self.assertEqual(notice_context["read_error"], "confirmed_beta_notice_json_missing")
        self.assertEqual(notice_context["notice_completion_status"], "not_confirmed_by_supplied_json")
        self.assertFalse(notice_context["notice_completion_accepted_by_this_report"])
        self.assertFalse(notice_context["activation_allowed_by_this_report"])
        self.assertFalse(notice_context["discord_authorized"])
        self.assertFalse(notice_context["approved_runtime_evidence"])
        self.assertFalse(notice_context["counts_as_approved_runtime_evidence"])
        self.assertFalse(notice_context["counts_as_sdk_evidence"])
        self.assertFalse(notice_context["counts_toward_sdk"])
        self.assertFalse(notice_context["counts_toward_p0_dependency_chain"])
        self.assertFalse(notice_context["counts_toward_p0_dependency_chain_claim_now"])
        self.assertEqual(notice_context["sdk_progress"], 0)
        self.assertEqual(notice_context["p0_progress"], 0)
        operation = report["exact_missing_operations"][0]
        self.assertEqual(operation["post_reboot_monitor_context"], monitor_context)
        self.assertEqual(operation["confirmed_beta_notice_context"], notice_context)
        action = report["machine_next_actions"][0]
        self.assertEqual(action["post_reboot_monitor_context"], monitor_context)
        self.assertEqual(action["confirmed_beta_notice_context"], notice_context)
        rerun = action["after_completion"]["closure_request_command_text_not_executed"]
        self.assertIn("--post-reboot-monitor-log", rerun)
        self.assertIn(str(monitor_log), rerun)
        self.assertIn("--confirmed-beta-notice-json", rerun)
        self.assertIn(str(confirmed_notice), rerun)
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["live_ops_authorized"])
        self.assertFalse(report["runtime_capture_authorized"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["counts_toward_sdk"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim_now"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_context_paths_preserve_copied_log_machine_action_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            evidence_dir = tmp_path / "live-validation-logs" / RUN_ID
            monitor_log = tmp_path / "passive-monitor-post-reboot.log"
            confirmed_notice = tmp_path / "beta-notice.confirmed.json"
            write_siblings(evidence_dir, missing=set(EXPECTED_MISSING))
            (evidence_dir / "Obelisk.log").unlink()
            bind_standing_launch_authority_receipt(evidence_dir)

            result = run_report(
                evidence_dir,
                "--post-reboot-monitor-log",
                str(monitor_log),
                "--confirmed-beta-notice-json",
                str(confirmed_notice),
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        first_operation = report["exact_missing_operations"][0]
        self.assertEqual(first_operation["artifact"], "lifecycle-role/session_start")
        self.assertEqual(
            first_operation["operation"],
            "continue_or_request_passive_wait_for_missing_lifecycle_role",
        )
        copy_operation = next(
            operation
            for operation in report["exact_missing_operations"]
            if operation["artifact"] == "Obelisk.log"
        )
        self.assertEqual(
            copy_operation["operation"],
            "copy_ready_player_principal_lifecycle_obelisk_log",
        )
        self.assertIn("--allow-live-log-read", copy_operation["command_text_not_executed"])
        first_action = report["machine_next_actions"][0]
        self.assertEqual(first_action["artifact"], "lifecycle-role/session_start")
        self.assertEqual(
            first_action["action"],
            "continue_or_request_passive_wait_for_missing_lifecycle_role",
        )
        self.assertFalse(first_action["approved_runtime_evidence"])
        self.assertFalse(first_action["reads_live_logs"])
        self.assertEqual(
            first_action["post_reboot_monitor_context"],
            report["operational_context"]["post_reboot_monitor_context"],
        )
        self.assertEqual(
            first_action["confirmed_beta_notice_context"],
            report["operational_context"]["confirmed_beta_notice_context"],
        )
        self.assertFalse(first_action["post_reboot_monitor_context"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(first_action["confirmed_beta_notice_context"]["counts_toward_sdk"])
        self.assertFalse(first_action["confirmed_beta_notice_context"]["counts_toward_p0_dependency_chain"])
        self.assertEqual(first_action["post_reboot_monitor_context"]["p0_progress"], 0)
        self.assertFalse(report["live_ops_authorized"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["counts_toward_sdk"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim_now"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_future_player_window_with_beta_notice_path_requires_real_notice_without_sending_discord(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(
                evidence_dir,
                roles=("session_start", "session_start_rejected"),
                instance="arkserver3",
                map_name="Genesis2",
            )

            result = run_report(
                evidence_dir,
                "--future-window-needs-players",
                "--notice-path",
                "Discord beta testers",
                instance="arkserver3",
                map_name="Genesis2",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        notice = report["player_notice_requirements"]
        self.assertTrue(notice["future_window_needs_players"])
        self.assertTrue(notice["future_window_needs_players_supplied"])
        self.assertTrue(notice["missing_lifecycle_roles_need_players"])
        self.assertEqual(notice["notice_path"], "Discord beta testers")
        self.assertTrue(notice["notice_path_named"])
        self.assertTrue(notice["beta_testers_notice_path_named"])
        self.assertTrue(notice["real_beta_testers_notice_action_required_before_activation"])
        self.assertEqual(
            notice["required_action"],
            "send_current_turn_approved_beta_testers_notice_before_activation",
        )
        self.assertTrue(notice["must_be_real_notice_not_documentation"])
        self.assertTrue(notice["must_complete_after_dry_run_before_activation"])
        self.assertFalse(notice["sent_by_this_report"])
        self.assertFalse(notice["discord_sent_by_this_report"])
        self.assertFalse(notice["discord_authorized_by_this_report"])
        self.assertFalse(notice["discord_command_emitted_by_this_report"])
        self.assertFalse(notice["server_operations_authorized_by_this_notice"])
        self.assertFalse(notice["runtime_capture_authorized_by_this_notice"])
        self.assertFalse(notice["workspace_writes_authorized_by_this_notice"])
        self.assertFalse(notice["live_log_reads_authorized_by_this_notice"])
        self.assertFalse(notice["counts_as_approved_runtime_evidence"])
        self.assertFalse(notice["counts_toward_sdk"])
        self.assertEqual(len(report["required_notice_actions"]), 1)
        notice_action = report["required_notice_actions"][0]
        self.assertEqual(notice_action["operation"], notice["required_action"])
        self.assertEqual(notice_action["notice_path"], "Discord beta testers")
        self.assertFalse(notice_action["authorized_to_run_now"])
        self.assertTrue(notice_action["requires_current_turn_operator_approval"])
        self.assertEqual(notice_action["command_status"], "NOT EMITTED")
        self.assertTrue(notice_action["command_text_not_emitted"])
        self.assertFalse(notice_action["sent_by_this_report"])
        self.assertFalse(notice_action["discord_authorized"])
        self.assertFalse(notice_action["discord_sent_by_this_report"])
        self.assertFalse(notice_action["runtime_capture_authorized"])
        self.assertFalse(notice_action["workspace_writes_authorized"])
        self.assertFalse(notice_action["reads_live_logs"])
        self.assertFalse(report["discord_authorized"])
        self.assertFalse(report["discord_sent_by_this_report"])
        self.assertFalse(report["discord_command_emitted_by_this_report"])
        approval = report["current_turn_approval_requirements"]
        self.assertEqual(approval["notice_requirements"], notice)
        self.assertEqual(approval["required_scope"]["notice_requirements"], notice)
        self.assertEqual(approval["required_notice_actions"], report["required_notice_actions"])
        self.assertEqual(approval["required_scope"]["required_notice_actions"], report["required_notice_actions"])
        self.assertFalse(approval["discord_authorization_granted_by_this_report"])
        self.assertFalse(approval["discord_sent_by_this_report"])
        self.assertIn("real beta testers notice action", "\n".join(approval["required_scope"]["context_notes"]))
        self.assertNotIn("send_discord_embed.py", json.dumps(report))
        for command in report["not_executed_commands"]:
            self.assertNotIn("discord", command["command"].lower())

    def test_confirmed_beta_notice_suppresses_repeat_notice_action_without_readiness_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            evidence_dir = tmp_path / "live-validation-logs" / RUN_ID
            confirmed_notice = tmp_path / "beta-notice.confirmed.json"
            write_siblings(
                evidence_dir,
                roles=("session_start", "session_start_rejected"),
                instance="arkserver3",
                map_name="Genesis2",
            )
            write_confirmed_beta_notice(confirmed_notice)

            result = run_report(
                evidence_dir,
                "--future-window-needs-players",
                "--notice-path",
                "Discord beta testers",
                "--confirmed-beta-notice-json",
                str(confirmed_notice),
                instance="arkserver3",
                map_name="Genesis2",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        notice = report["player_notice_requirements"]
        self.assertTrue(notice["future_window_needs_players"])
        self.assertTrue(notice["missing_lifecycle_roles_need_players"])
        self.assertTrue(notice["beta_testers_notice_path_named"])
        self.assertTrue(notice["confirmed_notice_action_completed"])
        self.assertFalse(notice["real_beta_testers_notice_action_required_before_activation"])
        self.assertIsNone(notice["required_action"])
        self.assertEqual(report["required_notice_actions"], [])
        notice_context = report["operational_context"]["confirmed_beta_notice_context"]
        self.assertTrue(notice_context["read_by_this_report"])
        self.assertTrue(notice_context["path_existence_checked_by_this_report"])
        self.assertTrue(notice_context["notice_completion_accepted_by_this_report"])
        self.assertEqual(notice_context["notice_completion_status"], "confirmed_beta_notice_completed")
        self.assertEqual(notice_context["source_schema"], "obelisk.player-principal-lifecycle-beta-notice-prep.v1")
        self.assertEqual(notice_context["source_mode"], "confirmed_send")
        self.assertTrue(notice_context["source_discord_sent"])
        self.assertFalse(notice_context["activation_allowed_by_this_report"])
        self.assertFalse(notice_context["approved_runtime_evidence"])
        self.assertFalse(notice_context["counts_as_approved_runtime_evidence"])
        self.assertFalse(notice_context["counts_toward_sdk"])
        self.assertEqual(report["machine_next_actions"][0]["action"], "continue_or_request_passive_wait_for_missing_lifecycle_role")
        self.assertEqual(report["machine_next_actions"][0]["role"], "session_end")
        self.assertNotIn(
            "send_current_turn_approved_beta_testers_notice_before_activation",
            report["machine_next_action_ids"],
        )
        self.assertFalse(report["discord_authorized"])
        self.assertFalse(report["discord_sent_by_this_report"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(true_readiness_flags(report), [])

    def test_active_genesis2_markdown_names_missing_session_end_and_not_executed_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(
                evidence_dir,
                roles=("session_start", "session_start_rejected"),
                instance="arkserver3",
                map_name="Genesis2",
            )

            result = run_report(
                evidence_dir,
                "--format",
                "markdown",
                instance="arkserver3",
                map_name="Genesis2",
            )

        self.assertNotEqual(result.returncode, 0)
        markdown = result.stdout
        self.assertIn("closure_case=active_genesis2_triplet_incomplete", markdown)
        self.assertIn("target_instance=arkserver3", markdown)
        self.assertIn("target_map=Genesis2", markdown)
        self.assertIn("target_key=arkserver3:Genesis2:27017", markdown)
        self.assertIn("## Missing Artifacts/Roles", markdown)
        self.assertIn("## Required Sidecars", markdown)
        self.assertIn("## Exact Missing Sidecars", markdown)
        self.assertIn("### Required Role Triplet", markdown)
        self.assertIn("- session_end", markdown)
        self.assertIn("## NOT EXECUTED Commands", markdown)
        self.assertIn("command_status=NOT EXECUTED", markdown)
        self.assertIn("scripts/monitor_ark_player_presence_passive.sh", markdown)
        self.assertIn("two_server_cap_required=true", markdown)
        self.assertIn("the_island_must_remain_off_without_current_turn_approval=true", markdown)
        self.assertIn("future_window_needs_players=true", markdown)
        self.assertIn("notice_path=not_applicable", markdown)
        self.assertIn("real_beta_testers_notice_action_required_before_activation=false", markdown)
        self.assertIn("notice_discord_sent_by_this_report=false", markdown)
        self.assertIn("notice_discord_authorized_by_this_report=false", markdown)

    def test_rejects_any_output_path_under_server_root_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            safe_output = Path(tmp) / "closure.json"
            write_siblings(evidence_dir)

            result = run_report(
                evidence_dir,
                "--json-output",
                str(safe_output),
                "--markdown-output",
                "/servidor/ark/workspace-offline/closure-request.md",
            )

            self.assertFalse(safe_output.exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("must not write under /servidor/ark", result.stderr)

    def test_rejects_markdown_output_symlink_component_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir)
            symlink_parent = Path(tmp) / "server-link"
            symlink_parent.symlink_to("/servidor/ark", target_is_directory=True)

            result = run_report(
                evidence_dir,
                "--markdown-output",
                str(symlink_parent / "closure-request.md"),
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("--markdown-output must not use a symlink component", result.stderr)

    def test_rejects_notice_path_url_or_webhook_label_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            safe_output = Path(tmp) / "closure.json"
            write_siblings(evidence_dir)

            result = run_report(
                evidence_dir,
                "--future-window-needs-players",
                "--notice-path",
                "beta testers webhook",
                "--json-output",
                str(safe_output),
            )

            self.assertFalse(safe_output.exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("--notice-path must be a label", result.stderr)

    def test_evidence_dir_symlink_is_not_followed_or_inspected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            real_evidence_dir = Path(tmp) / "real" / "live-validation-logs" / RUN_ID
            write_siblings(real_evidence_dir)
            symlink_dir = Path(tmp) / "linked-evidence"
            symlink_dir.symlink_to(real_evidence_dir, target_is_directory=True)

            result = run_report(symlink_dir)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["evidence_dir_exists"])
        self.assertEqual(report["evidence_dir"], str(symlink_dir.absolute()))
        self.assertEqual(report["present_siblings"], [])
        self.assertEqual(report["lifecycle_event_role_state"]["inspection_blocked_by"], "evidence_dir_not_inspected")
        self.assertEqual(report["input_blockers"][0]["reason"], "evidence_dir_symlink_component")

    def test_safe_markdown_output_writes_request_with_missing_artifact_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            markdown_output = Path(tmp) / "repo-tmp" / "closure-request.md"
            write_siblings(evidence_dir, missing=set(EXPECTED_MISSING))

            result = run_report(
                evidence_dir,
                "--format",
                "markdown",
                "--markdown-output",
                str(markdown_output),
            )

            self.assertTrue(markdown_output.is_file())
            markdown = markdown_output.read_text(encoding="utf-8")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, markdown)
        self.assertIn(f"evidence_dir={evidence_dir}", markdown)
        self.assertIn("ready=false", markdown)
        self.assertIn("closure_request_ready=false", markdown)
        self.assertIn(
            "ready_scope=not_ready_closure_request_is_non_evidence_checker_required_before_any_readiness_claim",
            markdown,
        )
        self.assertIn("copied_bundle_checker_acceptance_required_before_sdk_p0_changes=true", markdown)
        self.assertIn("sdk_p0_changes_authorized=false", markdown)
        self.assertIn("## Missing Required Artifacts", markdown)
        self.assertIn("## Missing Expected Sibling Artifacts", markdown)
        for artifact in EXPECTED_MISSING:
            self.assertIn(f"- {artifact}", markdown)
        self.assertIn("## Copied Bundle Checker Gate", markdown)
        self.assertIn(
            "status=blocked_until_complete_sibling_set_exact_triplet_and_valid_sidecars",
            markdown,
        )
        self.assertIn("checker_command_status=NOT PROVIDED", markdown)
        self.assertIn("source_required=fresh_current_turn_operator_message", markdown)
        self.assertIn(f"required_scope_evidence_dir={evidence_dir}", markdown)
        self.assertIn("required_scope_target_instance=arkserver2", markdown)
        self.assertIn("required_scope_target_map=TheIsland", markdown)
        self.assertIn("required_scope_target_key=arkserver2:TheIsland:27016", markdown)
        self.assertIn("must_name_exact_missing_file_writes=true", markdown)
        self.assertIn("command_status=NOT EXECUTED", markdown)
        self.assertIn("validation_command_status=NOT EXECUTED", markdown)
        self.assertIn("## Missing Artifacts/Roles", markdown)
        self.assertIn("## Closure Checklist", markdown)
        self.assertIn(
            f"approved_bundle_path={evidence_dir / 'approved-bundle' / 'approved-runtime-principal-lifecycle-evidence.json'}",
            markdown,
        )
        self.assertIn("relative_path=approved-bundle/approved-runtime-principal-lifecycle-evidence.json", markdown)
        self.assertIn("status=missing", markdown)
        self.assertIn("## NOT EXECUTED Commands", markdown)
        self.assertIn("This request does not authorize server operations.", markdown)

    def test_markdown_contains_no_public_readiness_claim_and_keeps_context_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_dir = Path(tmp) / "live-validation-logs" / RUN_ID
            write_siblings(evidence_dir, missing=set(EXPECTED_MISSING))

            result = run_report(evidence_dir, "--format", "markdown")

        self.assertNotEqual(result.returncode, 0)
        markdown = result.stdout
        self.assertIn("server_operations_authorized=false", markdown)
        self.assertIn("runtime_work_authorized=false", markdown)
        self.assertIn("workspace_writes_authorized=false", markdown)
        self.assertIn("live_ops_authorized=false", markdown)
        self.assertIn("runtime_capture_authorized=false", markdown)
        self.assertIn("reads_live_logs=false", markdown)
        self.assertIn("discord_authorized=false", markdown)
        self.assertIn("discord_sent_by_this_report=false", markdown)
        self.assertIn("discord_command_emitted_by_this_report=false", markdown)
        self.assertIn("approved_runtime_evidence=false", markdown)
        self.assertIn("approved_runtime_evidence_present=false", markdown)
        self.assertIn("counts_as_approved_runtime_evidence=false", markdown)
        self.assertIn("passive_snapshots_as_evidence=false", markdown)
        self.assertIn("counts_toward_sdk=false", markdown)
        self.assertIn("counts_toward_v1=false", markdown)
        self.assertIn("sdk_p0_changes_authorized=false", markdown)
        self.assertIn("status_report_paths_authorize_current_turn=false", markdown)
        self.assertIn("no_readiness_claim=true", markdown)
        self.assertIn("does_not_claim_public_runtime_v1_readiness=true", markdown)
        self.assertIn("public_abi_ready=false", markdown)
        self.assertIn("public_sdk_ready=false", markdown)
        self.assertIn("runtime_ready=false", markdown)
        self.assertIn("v1_completion_ready=false", markdown)
        self.assertIn("approved_runtime_evidence_ready=false", markdown)
        self.assertIn("promotion_ready=false", markdown)
        self.assertIn("the_island_off=true", markdown)
        self.assertIn("two_server_cap_preserved=true", markdown)
        self.assertIn("two_server_cap_required=true", markdown)
        self.assertIn("two_server_cap_max_running_servers=2", markdown)
        self.assertIn("TheIsland is off", markdown)
        self.assertIn("Two-server cap must be preserved", markdown)
        self.assertIn("does not claim public readiness", markdown)
        self.assertIn("does not claim public/runtime/v1 readiness", markdown)
        self.assertNotIn("public_abi_ready=true", markdown)
        self.assertNotIn("public_sdk_ready=true", markdown)
        self.assertNotIn("runtime_ready=true", markdown)
        self.assertNotIn("v1_completion_ready=true", markdown)
        self.assertNotIn("server_operations_authorized=true", markdown)
        self.assertNotIn("live_ops_authorized=true", markdown)
        self.assertNotIn("runtime_capture_authorized=true", markdown)
        self.assertNotIn("reads_live_logs=true", markdown)
        self.assertNotIn("discord_authorized=true", markdown)
        self.assertNotIn("discord_sent_by_this_report=true", markdown)
        self.assertNotIn("approved_runtime_evidence=true", markdown)
        self.assertNotIn("counts_as_approved_runtime_evidence=true", markdown)
        self.assertNotIn("passive_snapshots_as_evidence=true", markdown)
        self.assertNotIn("counts_toward_sdk=true", markdown)
        self.assertNotIn("counts_toward_v1=true", markdown)
        self.assertNotIn("sdk_p0_changes_authorized=true", markdown)


if __name__ == "__main__":
    unittest.main()
