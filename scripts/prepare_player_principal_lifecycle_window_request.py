#!/usr/bin/env python3
"""Prepare an offline request pack for a future player-principal lifecycle window.

This tool writes only secret-free planning artifacts. It does not authorize or perform
server operations, marker edits, restarts, Discord notices, runtime capture, or SDK
promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import protected_paths
from protected_paths import reject_protected_output_path
from player_principal_commit_validation import is_reviewed_obelisk_commit
from snapshot_evidence_pack import reject_symlink_component


SCHEMA = "obelisk.player-principal-lifecycle-window-request.v1"
APPROVAL_RECEIPT_SCHEMA = "obelisk.player-principal-lifecycle-operator-approval-receipt.v1"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
EXPECTED_SERVER_BINARY_PATH = "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer"
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$")
RUN_ID_SUFFIX = "-player-principal-lifecycle"
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
MIN_APPROVED_WINDOW_SECONDS = 900
DEFAULT_APPROVED_WINDOW_SECONDS = 900
MAX_APPROVED_WINDOW_SECONDS = 7200
MAX_REQUEST_PREPARATION_LEAD_SECONDS = 3600
MAX_OPERATOR_APPROVAL_LEAD_SECONDS = 600
ROLLBACK_MARKER_STATE_ROOT = "/servidor/ark/obelisk/state/instances"
FORBIDDEN_EXACT_TARGET_ALIASES = frozenset(
    (
        "active",
        "all",
        "any",
        "auto",
        "both",
        "current",
        "default",
        "either",
        "latest",
        "live",
        "prod",
        "production",
        "public",
        "public_identity",
        "publicidentity",
        "public_sdk",
        "publicsdk",
        "sdk_ready",
        "sdkready",
    )
)
PUBLIC_SDK_READY_ALIAS_RE = re.compile(
    r"(?:public[_ .-]?(?:identity|sdk)|sdk[_ .-]?ready|complete[_ .-]?sdk|"
    r"v1[_ .-]?sdk[_ .-]?(?:ready|complete|completion)|identity[_ .-]?ready)",
    re.IGNORECASE,
)
APPROVAL_TEXT = "current-turn operator-approved runtime window, not standing approval"
STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT = (
    "operator runtime authority must be bound by completed receipt; standing launch authority source allowed"
)
APPROVAL_SCOPE_SCHEMA = "obelisk.player-principal-lifecycle-current-turn-approval-scope.v1"
APPROVAL_SCOPE_STATUS = "requires_exact_current_turn_operator_approval"
APPROVAL_SCOPE_SOURCE_REQUIRED = "current_turn_operator_message"
APPROVAL_SCOPE_STATUS_STANDING_LAUNCH_AUTHORITY = (
    "requires_recorded_standing_launch_authority_bound_to_exact_window"
)
APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY = "standing_launch_authority"
APPROVAL_SCOPE_NON_AUTHORIZATION = (
    "approval scope checklist only; does not authorize deployment, server operations, "
    "marker/env changes, restart, runtime capture, approved runtime evidence, public readiness, "
    "or SDK completion"
)
APPROVAL_SOURCE_CURRENT_TURN = "current_turn_operator_message"
APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY = "standing_launch_authority"
APPROVAL_ATTESTATION_CURRENT_TURN = "APPROVE_EXACT_BOUND_PLAYER_PRINCIPAL_LIFECYCLE_WINDOW_ONLY"
APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY = (
    "BIND_STANDING_OBELISKSDK_LAUNCH_AUTHORITY_TO_EXACT_PLAYER_PRINCIPAL_LIFECYCLE_WINDOW"
)
STANDING_LAUNCH_AUTHORITY_REFERENCE_DEFAULT = "operator"
OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS = [
    "generated receipt template only; does not record operator approval",
    "completed receipt binds one exact request pack and runtime window only",
    "receipt does not authorize future windows, reusable standing scope, Discord, GitHub publication, public SDK readiness, runtime readiness, or v1 completion",
    "receipt does not promote public player identity, permissions/admin, command response, lookup, mutation, return override, or ResourceHandle",
]
CURRENT_TURN_APPROVAL_REQUIRED_FIELDS = [
    "target",
    "exact_target_instance_map",
    "marker_env_gates",
    "restart_window",
    "player_presence_safety",
    "player_notice_action",
    "direct_join_plan",
    "rollback",
    "evidence_paths",
    "runtime_triplet_contract",
    "passive_wait_boundary",
    "final_posture",
]
EXACT_TARGET_SCOPE_SCHEMA = "obelisk.player-principal-lifecycle-exact-target-scope.v1"
EXACT_TARGET_SCOPE_NON_AUTHORIZATION = (
    "exact target binding only; aliases do not satisfy instance or map scope; does not "
    "authorize deployment, server operations, marker/env changes, restart, runtime capture, "
    "or readiness claims"
)
PASSIVE_WAIT_BOUNDARY_SCHEMA = "obelisk.player-principal-lifecycle-passive-wait-boundary.v1"
PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION = (
    "wait-only/passive is not approval; passive monitor ticks, player-presence detections, "
    "snapshots, and diagnostic summaries are watch-only; the requested organic wait window "
    "is checked only as a bounded parameter from 900 to 7200 seconds; do not authorize "
    "deployment; "
    "do not authorize marker/env changes; do not authorize starts, stops, or restarts; "
    "do not authorize runtime capture; do not count as approved runtime evidence; "
    "do not promote player identity; do not claim SDK readiness"
)
DIRECT_JOIN_PLAN_SCHEMA = "obelisk.player-principal-lifecycle-direct-join-plan.v1"
DIRECT_JOIN_PLAN_NON_AUTHORIZATION = (
    "direct-join plan only; does not authorize Discord/community notices, broad Discord, "
    "server operations, marker/env changes, starts, restarts, stops, cluster transfer, a third "
    "ARK server, runtime capture, approved runtime evidence, public readiness, SDK completion, "
    "or P0 progress"
)
BETA_RUNTIME_CHOREOGRAPHY_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-runtime-choreography.v1"
)
BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION = (
    "beta runtime choreography checklist only; does not authorize Discord/community notices, "
    "player contact, tester actions, server operations, marker/env changes, starts, restarts, "
    "stops, cluster transfer, reconnects, logout requests, runtime capture, approved runtime "
    "evidence, public readiness, SDK completion, or P0 progress"
)
CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-checkjoin-stimulus-boundary.v1"
)
CHECKJOIN_STIMULUS_BOUNDARY_NON_AUTHORIZATION = (
    "CheckJoin stimulus boundary only; stale, diagnostic, or unpaired exact CheckJoin lines "
    "are stimulus clues only; does not authorize runtime work; does not promote evidence; "
    "does not claim readiness"
)
PLAYER_NOTICE_ACTION_SCHEMA = "obelisk.player-principal-lifecycle-player-notice-action.v1"
APPROVED_BETA_NOTICE_PATH = "discord-beta-testers"
PLAYER_NOTICE_ACTION_NON_AUTHORIZATION = (
    "player notice checklist only; request pack acceptance does not authorize Discord/community "
    "notices or player-facing validation. For scoped beta-user evidence windows, the approved "
    "notice path must be dry-run checked and sent as a real beta-test notice before activation."
)
PLAYER_PRESENCE_SAFETY_SCHEMA = "obelisk.player-principal-lifecycle-player-presence-safety.v1"
PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION = (
    "player-presence safety checklist only; request pack acceptance does not authorize player "
    "queries, RCON/admin-console broadcasts, server operations, marker/env changes, restart, "
    "runtime capture, approved runtime evidence, public readiness, or SDK completion"
)
DRIFT_FIX_DEPLOYMENT_INTENT_TYPE = "lifecycle_anchor_drift_fix_deploy_request_only"
DRIFT_FIX_DEPLOYMENT_INTENT_NON_AUTHORIZATION = (
    "drift-fix deployment intent only; does not authorize deployment, server operations, "
    "marker/env changes, restart, runtime capture, approved runtime evidence, public readiness, "
    "or SDK completion"
)
PLANNED_OBELISK_BUILD_IDENTITY_SCHEMA = "obelisk.player-principal-lifecycle-planned-obelisk-build-identity.v1"
PLANNED_OBELISK_BUILD_ARTIFACT_KIND = "obelisk_runtime_build_artifact"
PLANNED_OBELISK_BUILD_IDENTITY_NON_AUTHORIZATION = (
    "planned Obelisk commit/build artifact identity only; does not claim public readiness; "
    "does not claim SDK readiness; does not claim authorization; does not authorize deployment, "
    "server operations, marker/env changes, restart, runtime capture, or publication"
)
REPLAY_NON_AUTHORIZATION = (
    "post-window replay contract only; does not authorize runtime work, server operations, "
    "marker/env changes, starts, restarts, or stops"
)
BRIEF_NON_AUTHORIZATION = (
    "brief only; request-pack acceptance does not authorize server operations, marker/env "
    "changes, starts, restarts, stops, or runtime capture"
)
ARTIFACT_BINDING_NON_AUTHORIZATION = (
    "artifact binding only; does not authorize runtime work, server operations, "
    "marker/env changes, public readiness, or promotion"
)
AUTHORIZATION_FLAGS = {
    "current_turn_approval_recorded": False,
    "current_turn_scope_authorized": False,
    "discord_authorized": False,
    "discord_send_authorized": False,
    "discord_sent": False,
    "marker_env_changes_authorized": False,
    "server_operations_authorized": False,
    "runtime_work_authorized": False,
    "runtime_capture_authorized": False,
    "runtime_window_authorized": False,
    "read_live_logs": False,
    "reads_live_logs": False,
    "live_log_reads_authorized": False,
    "live_log_permission_granted": False,
    "request_pack_counts_as_approved_runtime_evidence": False,
    "observer_env_counts_as_approved_runtime_evidence": False,
    "operator_request_counts_as_approved_runtime_evidence": False,
    "copied_log_metadata_counts_as_approved_runtime_evidence": False,
    "bundle_output_counts_as_approved_runtime_evidence": False,
    "publication_authorized": False,
    "promotion_ready": False,
    "public_abi_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
    "route_ready": False,
    "v1_completion_ready": False,
    "stable_claim_allowed": False,
    "sdk_accounting_counts_as_completed_surface": False,
    "p0_accounting_counts_as_promoted_surface": False,
}
REQUEST_ROLLBACK_DELTA = "remove observer env and markers, preserve stable enable-process-event-hook and disable-plugins"
POSTURE_GUARDRAIL_TEXT = (
    "player-principal lifecycle request packs require --final-posture stable; "
    "stopped/stop-after-window is not supported because downstream manifest and "
    "approved evidence checks require stable post posture"
)
APPROVED_OFFLINE_WORKSPACE_ROOTS = protected_paths.approved_offline_workspace_roots()
EVIDENCE_ROOT = APPROVED_OFFLINE_WORKSPACE_ROOTS[0] / "live-validation-logs"
REQUIRED_ENV = {
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK": "1",
    "OBELISK_DISABLE_PLUGINS": "1",
    "OBELISK_WRAPPER_PROFILE": "observer-debug",
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER": "1",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT": "10",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT": "0",
    "OBELISK_PE_TRACE_LIMIT": "0",
}
DIAGNOSTIC_CANDIDATES_ENV_KEY = "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES"
OBSERVER_ENV_KEYS_BASE = (
    "OBELISK_INSTANCE_ID",
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK",
    "OBELISK_DISABLE_PLUGINS",
    "OBELISK_WRAPPER_PROFILE",
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT",
    "OBELISK_PE_TRACE_LIMIT",
)
OBSERVER_ENV_KEYS = OBSERVER_ENV_KEYS_BASE
WINDOW_MARKERS = [
    "enable-process-event-hook",
    "disable-plugins",
    "allow-observer-debug-window",
    "allow-experimental-observers",
    "enable-player-principal-lifecycle-observer",
]
FORBIDDEN_MARKERS = [
    "allow-ptrace",
    "enable-debug-control",
    "enable-reflection-scanner",
    "enable-native-exec-probes",
    "allow-global-process-event-callbacks",
    "allow-filtered-process-event-callbacks",
    "allow-call-process-event",
    "allow-process-event-blocking",
    "request-static-fname-probe",
    "enable-chat-events",
    "enable-chat-reflection",
    "enable-chat-route-observer",
    "enable-inventory-reflection",
    "enable-inventory-action-redacted-observer",
    "enable-structure-reflection",
    "enable-item-return-events",
]
NON_CLAIMS = [
    "does not authorize server operations",
    "does not authorize marker/env changes",
    "does not authorize starts, restarts, or stops",
    "does not authorize Discord/community notices",
    "does not claim public readiness",
    "does not claim SDK readiness",
    "does not claim operator approval or authorization",
    "does not promote public player identity",
    "does not claim stable principal identity",
    "does not promote permissions/admin",
    "does not promote command/chat response or commands/replies",
    "diagnostic candidate lines do not count as approved runtime evidence",
    "does not authorize lookup, persistence, mutation, return override, plugin delivery, runtime readiness, public SDK readiness, or v1 SDK completion",
]
RUNTIME_TRIPLET_CONTRACT_SCHEMA = "obelisk.player-principal-lifecycle-runtime-triplet-contract.v1"
SESSION_START_REJECTED_REQUIRED_FUNCTION = "CheckJoinInProgress"
SESSION_START_REJECTED_REQUIRED_ARGUMENTS = [1, 0]
SESSION_START_REJECTED_REQUIRED_CALL = "CheckJoinInProgress(1,0)"
SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS = ["bIsFromLogin", "ReturnValue"]
SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES = ["1", "0"]
HANDLE_NEW_PLAYER_FUNCTION = "HandleNewPlayer"
RUNTIME_TRIPLET_CONTRACT_NON_AUTHORIZATION = (
    "runtime triplet contract for offline/post-window checking only; does not authorize "
    "runtime capture, does not count any tuple by itself, and does not permit "
    "HandleNewPlayer rejected tuples as session_start_rejected alternatives"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True, help="Target Obelisk instance id.")
    parser.add_argument("--map", required=True, dest="map_name", help="Target ARK map name.")
    parser.add_argument("--run-id", required=True, help="YYYYMMDDThhmmssZ-player-principal-lifecycle.")
    parser.add_argument("--obelisk-commit", required=True, help="Reviewed Obelisk commit/build id.")
    parser.add_argument("--approved-window-start-utc", required=True, help="Approved UTC start, YYYY-MM-DDThh:mm:ssZ.")
    parser.add_argument("--approved-window-end-utc", required=True, help="Approved UTC end, YYYY-MM-DDThh:mm:ssZ.")
    parser.add_argument(
        "--binary-sha256",
        default=EXPECTED_BINARY_SHA256,
        help="Expected ShooterGameServer SHA256.",
    )
    parser.add_argument(
        "--server-binary-path",
        default=EXPECTED_SERVER_BINARY_PATH,
        help="Exact ShooterGameServer path for the future approved window; recorded only, not read.",
    )
    parser.add_argument(
        "--restart-expectation",
        required=True,
        metavar="{none,start,restart}",
        help="Expected server lifecycle action; stop-after-window is not supported for this evidence chain.",
    )
    parser.add_argument(
        "--final-posture",
        required=True,
        metavar="{stable}",
        help="Required post-window posture; stopped is not supported for this evidence chain.",
    )
    parser.add_argument(
        "--user-policy",
        required=True,
        choices=("no_regular_users", "operator_approved_beta_users"),
    )
    parser.add_argument("--notice-path", default="not_applicable", help="Notice path label or not_applicable.")
    parser.add_argument("--rollback-owner", required=True, help="Operator/person responsible for rollback.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Offline output directory for request pack.")
    parser.add_argument(
        "--diagnostic-candidates",
        action="store_true",
        help="Include candidate-only diagnostic env for a non-evidence observer-debug diagnostic window.",
    )
    parser.add_argument(
        "--obelisk-build-artifact",
        type=Path,
        help="Optional offline planned Obelisk build artifact to hash and bind into the request pack.",
    )
    parser.add_argument(
        "--obelisk-build-artifact-sha256",
        help="Optional lowercase SHA256 for a planned Obelisk build artifact when the file is unavailable.",
    )
    parser.add_argument(
        "--obelisk-build-artifact-label",
        help="Optional safe label/name for the planned Obelisk build artifact identity.",
    )
    parser.add_argument(
        "--standing-launch-authority",
        action="store_true",
        help=(
            "Write a completed operator-approval-receipt.json that binds the recorded standing "
            "ObeliskSDK launch authority to this exact request pack and window."
        ),
    )
    parser.add_argument(
        "--standing-launch-authority-reference",
        default=STANDING_LAUNCH_AUTHORITY_REFERENCE_DEFAULT,
        help="Safe reference label for the recorded standing launch authority.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args()


def parse_utc(value: str, label: str) -> datetime:
    if not UTC_RE.fullmatch(value):
        raise SystemExit(f"{label} must be UTC YYYY-MM-DDThh:mm:ssZ")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def run_id_for_window_start(start: datetime) -> str:
    return start.strftime("%Y%m%dT%H%M%SZ") + RUN_ID_SUFFIX


def require_safe_token(value: str, label: str) -> None:
    if not SAFE_TOKEN_RE.fullmatch(value):
        raise SystemExit(f"{label} contains unsafe characters: {value}")


def normalized_alias_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def contains_forbidden_public_sdk_alias(value: str) -> bool:
    return PUBLIC_SDK_READY_ALIAS_RE.search(value) is not None


def is_forbidden_exact_target_alias(value: str) -> bool:
    normalized = normalized_alias_token(value)
    return normalized in FORBIDDEN_EXACT_TARGET_ALIASES or contains_forbidden_public_sdk_alias(value)


def require_no_public_sdk_alias(value: str, label: str) -> None:
    if contains_forbidden_public_sdk_alias(value):
        raise SystemExit(f"{label} must not use SDK-ready/public-identity aliases: {value}")


def require_exact_target_token(value: str, label: str) -> None:
    require_safe_token(value, label)
    if is_forbidden_exact_target_alias(value):
        raise SystemExit(f"{label} must name an exact instance/map, not an alias: {value}")


def validate_args(args: argparse.Namespace) -> None:
    require_exact_target_token(args.instance, "--instance")
    require_exact_target_token(args.map_name, "--map")
    if not RUN_ID_RE.fullmatch(args.run_id):
        raise SystemExit("--run-id must match YYYYMMDDThhmmssZ-player-principal-lifecycle")
    if not re.fullmatch(r"[0-9a-f]{64}", args.binary_sha256):
        raise SystemExit("--binary-sha256 must be lowercase SHA256 hex")
    if args.binary_sha256 != EXPECTED_BINARY_SHA256:
        raise SystemExit(f"--binary-sha256 must match reviewed ARK SHA256 {EXPECTED_BINARY_SHA256}")
    if args.server_binary_path != EXPECTED_SERVER_BINARY_PATH:
        raise SystemExit(f"--server-binary-path must match reviewed ARK path {EXPECTED_SERVER_BINARY_PATH}")
    if not is_reviewed_obelisk_commit(args.obelisk_commit):
        raise SystemExit("--obelisk-commit must be a reviewed 40-character lowercase Git SHA")
    start = parse_utc(args.approved_window_start_utc, "--approved-window-start-utc")
    end = parse_utc(args.approved_window_end_utc, "--approved-window-end-utc")
    if not start < end:
        raise SystemExit("--approved-window-start-utc must be before --approved-window-end-utc")
    now = datetime.now(timezone.utc)
    if start <= now:
        raise SystemExit("--approved-window-start-utc must be in the future")
    if end <= now:
        raise SystemExit("--approved-window-end-utc must be in the future")
    if (start - now).total_seconds() > MAX_REQUEST_PREPARATION_LEAD_SECONDS:
        raise SystemExit("--approved-window-start-utc must be within 1 hour of request preparation")
    duration_seconds = int((end - start).total_seconds())
    if duration_seconds < MIN_APPROVED_WINDOW_SECONDS:
        raise SystemExit(
            "--approved-window duration must be at least 15 minutes (900 seconds)"
        )
    if duration_seconds > MAX_APPROVED_WINDOW_SECONDS:
        raise SystemExit(
            "--approved-window duration must not exceed 120 minutes (7200 seconds)"
        )
    if args.restart_expectation not in {"none", "start", "restart"}:
        raise SystemExit(POSTURE_GUARDRAIL_TEXT)
    if args.final_posture != "stable":
        raise SystemExit(POSTURE_GUARDRAIL_TEXT)
    expected_run_id = run_id_for_window_start(start)
    if args.run_id != expected_run_id:
        raise SystemExit(f"--run-id timestamp must match --approved-window-start-utc exactly: {expected_run_id}")
    if args.user_policy == "operator_approved_beta_users" and args.notice_path != APPROVED_BETA_NOTICE_PATH:
        raise SystemExit(f"--notice-path must be {APPROVED_BETA_NOTICE_PATH} for beta-user windows")
    if args.user_policy == "no_regular_users" and args.notice_path != "not_applicable":
        raise SystemExit("--notice-path must be not_applicable when --user-policy=no_regular_users")
    if args.notice_path != "not_applicable" and not re.fullmatch(r"[A-Za-z0-9_.:/ -]+", args.notice_path):
        raise SystemExit("--notice-path contains unsafe characters")
    if not re.fullmatch(r"[A-Za-z0-9_.@ -]+", args.rollback_owner):
        raise SystemExit("--rollback-owner contains unsafe characters")
    if args.obelisk_build_artifact_sha256 is not None and not re.fullmatch(
        r"[0-9a-f]{64}", args.obelisk_build_artifact_sha256
    ):
        raise SystemExit("--obelisk-build-artifact-sha256 must be lowercase SHA256 hex")
    if args.obelisk_build_artifact_label is not None:
        require_safe_token(args.obelisk_build_artifact_label, "--obelisk-build-artifact-label")
        require_no_public_sdk_alias(args.obelisk_build_artifact_label, "--obelisk-build-artifact-label")
    if args.obelisk_build_artifact is None and args.obelisk_build_artifact_sha256 is None and args.obelisk_build_artifact_label is not None:
        raise SystemExit("--obelisk-build-artifact-label requires --obelisk-build-artifact or --obelisk-build-artifact-sha256")
    require_safe_token(args.standing_launch_authority_reference, "--standing-launch-authority-reference")
    if not args.standing_launch_authority and args.standing_launch_authority_reference != STANDING_LAUNCH_AUTHORITY_REFERENCE_DEFAULT:
        raise SystemExit("--standing-launch-authority-reference requires --standing-launch-authority")


def diagnostic_candidates_enabled(args: argparse.Namespace | dict[str, Any]) -> bool:
    if isinstance(args, dict):
        return bool(args.get("diagnostic_candidates_enabled", False))
    return bool(getattr(args, "diagnostic_candidates", False) or getattr(args, "diagnostic_candidates_enabled", False))


def standing_launch_authority_enabled(args: argparse.Namespace | dict[str, Any]) -> bool:
    if isinstance(args, dict):
        return args.get("approval_required") == STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT
    return bool(getattr(args, "standing_launch_authority", False))


def approval_required_text(args: argparse.Namespace | dict[str, Any]) -> str:
    if standing_launch_authority_enabled(args):
        return STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT
    return APPROVAL_TEXT


def approval_scope_status(args: argparse.Namespace | dict[str, Any]) -> str:
    if standing_launch_authority_enabled(args):
        return APPROVAL_SCOPE_STATUS_STANDING_LAUNCH_AUTHORITY
    return APPROVAL_SCOPE_STATUS


def approval_scope_source_required(args: argparse.Namespace | dict[str, Any]) -> str:
    if standing_launch_authority_enabled(args):
        return APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY
    return APPROVAL_SCOPE_SOURCE_REQUIRED


def approval_scope_standing_allowed(args: argparse.Namespace | dict[str, Any]) -> bool:
    return standing_launch_authority_enabled(args)


def observer_env_keys(args: argparse.Namespace | dict[str, Any]) -> tuple[str, ...]:
    if diagnostic_candidates_enabled(args):
        return (*OBSERVER_ENV_KEYS_BASE, DIAGNOSTIC_CANDIDATES_ENV_KEY)
    return OBSERVER_ENV_KEYS_BASE


def env_lines(args: argparse.Namespace) -> list[str]:
    values = {
        "OBELISK_INSTANCE_ID": args.instance,
        **REQUIRED_ENV,
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256": args.binary_sha256,
    }
    if diagnostic_candidates_enabled(args):
        values[DIAGNOSTIC_CANDIDATES_ENV_KEY] = "1"
    return [f"{key}={values[key]}" for key in observer_env_keys(args)]


def env_file_lines(args: argparse.Namespace) -> list[str]:
    return [
        "# request-pack-only; does not authorize marker/env changes, runtime work, or server operations",
        "# request_pack_counts_as_approved_runtime_evidence=false",
        "# stable_claim_allowed=false",
        "# public_readiness_claim=false",
        "# sdk_readiness_claim=false",
        "# operator_approval_or_authorization_claim=false",
        *env_lines(args),
    ]


def approved_offline_workspace_roots() -> tuple[Path, ...]:
    return protected_paths.approved_offline_workspace_roots()


def evidence_root() -> Path:
    return approved_offline_workspace_roots()[0] / "live-validation-logs"


def planned_obelisk_build_artifact_identity(args: argparse.Namespace) -> dict[str, Any]:
    source = "not_provided"
    artifact_sha256 = args.obelisk_build_artifact_sha256
    artifact_name = args.obelisk_build_artifact_label
    size_bytes: int | None = None
    if args.obelisk_build_artifact is not None:
        reject_symlink_component(args.obelisk_build_artifact, "--obelisk-build-artifact")
        resolved = protected_paths.reject_protected_input_path(
            args.obelisk_build_artifact.expanduser(),
            "--obelisk-build-artifact",
            approved_roots=approved_offline_workspace_roots(),
        )
        if not resolved.is_file():
            raise SystemExit(f"--obelisk-build-artifact must be a regular file: {resolved}")
        data = resolved.read_bytes()
        calculated_sha256 = hashlib.sha256(data).hexdigest()
        if artifact_sha256 is not None and artifact_sha256 != calculated_sha256:
            raise SystemExit("--obelisk-build-artifact-sha256 must match --obelisk-build-artifact")
        artifact_sha256 = calculated_sha256
        artifact_name = artifact_name or resolved.name
        size_bytes = len(data)
        source = "path_sha256"
    elif artifact_sha256 is not None:
        artifact_name = artifact_name or "operator_supplied_obelisk_build_artifact"
        source = "operator_supplied_sha256"
    if artifact_sha256 is None:
        return {
            "available": False,
            "source": source,
            "artifact_kind": None,
            "artifact_name": None,
            "artifact_sha256": None,
            "size_bytes": None,
        }
    require_safe_token(artifact_name, "--obelisk-build-artifact-label")
    require_no_public_sdk_alias(artifact_name, "--obelisk-build-artifact-label")
    return {
        "available": True,
        "source": source,
        "artifact_kind": PLANNED_OBELISK_BUILD_ARTIFACT_KIND,
        "artifact_name": artifact_name,
        "artifact_sha256": artifact_sha256,
        "size_bytes": size_bytes,
    }


def planned_obelisk_build_identity(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema": PLANNED_OBELISK_BUILD_IDENTITY_SCHEMA,
        "obelisk_commit": args.obelisk_commit,
        "build_artifact": planned_obelisk_build_artifact_identity(args),
        "non_authorization": PLANNED_OBELISK_BUILD_IDENTITY_NON_AUTHORIZATION,
    }


def marker_path(instance: str, marker: str) -> str:
    return f"{ROLLBACK_MARKER_STATE_ROOT}/{instance}/{marker}"


def rollback_plan(target: dict[str, str], owner: str) -> dict[str, Any]:
    instance = target["instance"]
    return {
        "owner": owner,
        "delta": REQUEST_ROLLBACK_DELTA,
        "marker_state_dir": f"{ROLLBACK_MARKER_STATE_ROOT}/{instance}",
        "stable_marker_paths": {
            "enable_process_event_hook": marker_path(instance, "enable-process-event-hook"),
            "disable_plugins": marker_path(instance, "disable-plugins"),
        },
        "observer_marker_paths": {
            "allow_observer_debug_window": marker_path(instance, "allow-observer-debug-window"),
            "allow_experimental_observers": marker_path(instance, "allow-experimental-observers"),
            "enable_player_principal_lifecycle_observer": marker_path(
                instance,
                "enable-player-principal-lifecycle-observer",
            ),
        },
    }


def rollback_plan_with_marker_paths(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("rollback")
    if not isinstance(source, dict):
        source = {}
    fallback = rollback_plan(payload["target"], str(source.get("owner", payload.get("owner", "unknown"))))
    normalized = {**fallback, **source}
    for key in ("stable_marker_paths", "observer_marker_paths"):
        source_paths = source.get(key)
        if isinstance(source_paths, dict):
            normalized[key] = {**fallback[key], **source_paths}
        else:
            normalized[key] = fallback[key]
    return normalized


def exact_target_scope(payload: dict[str, Any]) -> dict[str, Any]:
    target = payload["target"]
    return {
        "schema": EXACT_TARGET_SCOPE_SCHEMA,
        "instance": target["instance"],
        "map": target["map"],
        "instance_alias_allowed": False,
        "map_alias_allowed": False,
        "approval_must_name_exact_instance_and_map": True,
        "target_matches_request_target": True,
        "non_authorization": EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
    }


def requested_wait_window_seconds(payload: dict[str, Any]) -> int | None:
    window = payload.get("approved_window")
    if not isinstance(window, dict):
        return None
    start = window.get("start_utc")
    end = window.get("end_utc")
    if not isinstance(start, str) or not isinstance(end, str):
        return None
    try:
        start_dt = parse_utc(start, "approved_window.start_utc")
        end_dt = parse_utc(end, "approved_window.end_utc")
    except SystemExit:
        return None
    return int((end_dt - start_dt).total_seconds())


def runtime_triplet_contract() -> dict[str, Any]:
    return {
        "schema": RUNTIME_TRIPLET_CONTRACT_SCHEMA,
        "planning_only": True,
        "session_start_rejected": {
            "event": "session_start_rejected",
            "required_function": SESSION_START_REJECTED_REQUIRED_FUNCTION,
            "required_argument_tuple": SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
            "required_call": SESSION_START_REJECTED_REQUIRED_CALL,
            "required_copied_bool_fields": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
            "required_copied_bool_values": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
            "handle_new_player_rejected_tuple_allowed": False,
            "handle_new_player_rejected_tuple_alternative_allowed": False,
        },
        "handle_new_player_rejected_tuples": {
            "function": HANDLE_NEW_PLAYER_FUNCTION,
            "allowed_for_session_start_rejected": False,
            "alternative_for_session_start_rejected": False,
            "classification": "stale_rejected_start_rule_only",
        },
        "non_authorization": RUNTIME_TRIPLET_CONTRACT_NON_AUTHORIZATION,
    }


def payload_runtime_triplet_contract(payload: dict[str, Any]) -> dict[str, Any]:
    contract = payload.get("runtime_triplet_contract")
    if isinstance(contract, dict):
        return contract
    return runtime_triplet_contract()


def passive_wait_boundary(payload: dict[str, Any]) -> dict[str, Any]:
    wait_seconds = requested_wait_window_seconds(payload)
    standing_authority = standing_launch_authority_enabled(payload)
    return {
        "schema": PASSIVE_WAIT_BOUNDARY_SCHEMA,
        "target": payload["target"],
        "requested_wait_window_seconds": wait_seconds,
        "max_requested_wait_window_seconds": MAX_APPROVED_WINDOW_SECONDS,
        "requested_wait_window_seconds_checked_only": True,
        "requested_wait_window_authorizes_current_turn_approval": False,
        "requested_wait_window_authorizes_deploy_or_restart": False,
        "requested_wait_window_authorizes_runtime_capture": False,
        "requested_wait_window_counts_as_approved_runtime_evidence": False,
        "wait_only_or_passive_monitor_authorizes_deploy_or_restart": False,
        "passive_monitor_ticks_authorize_runtime_capture": False,
        "player_presence_detection_authorizes_followup": False,
        "snapshots_or_diagnostics_count_as_approved_runtime_evidence": False,
        "active_followup_requires_fresh_exact_current_turn_scope": not standing_authority,
        "active_followup_requires_recorded_standing_launch_authority": standing_authority,
        "non_authorization": PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION,
    }


def checkjoin_stimulus_boundary() -> dict[str, Any]:
    return {
        "schema": CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA,
        "classification": "stale_or_diagnostic_exact_checkjoin_is_stimulus_only",
        "exact_call": "ShooterGameMode.CheckJoinInProgress(1,0)",
        "accepted_observer_line_without_current_window_sibling_set_is_promotable": False,
        "diagnostic_tail_without_approved_sibling_set_is_promotable": False,
        "stale_or_order_mismatched_line_is_promotable": False,
        "stimulus_clue_for_future_choreography": True,
        "approved_sibling_set_required": True,
        "approved_sibling_set_roles_required": [
            "session_start",
            "session_start_rejected",
            "session_end",
        ],
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": CHECKJOIN_STIMULUS_BOUNDARY_NON_AUTHORIZATION,
    }


def beta_runtime_choreography(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": BETA_RUNTIME_CHOREOGRAPHY_SCHEMA,
        "classification": "single_tester_direct_join_choreography_non_authorizing",
        "target": payload["target"],
        "tester_count_required": 1,
        "exactly_one_tester_required": True,
        "single_tester_only": True,
        "direct_target_join_required": True,
        "direct_join_route": "direct_join_exact_server_map",
        "cluster_transfer_required": False,
        "cluster_transfer_allowed": False,
        "extra_transfer_server_required": False,
        "reconnect_before_exact_checkjoin_allowed": False,
        "logout_before_exact_checkjoin_allowed": False,
        "wait_for_exact_checkjoin_before_logout_required": True,
        "logout_or_cluster_transfer_or_reconnect_before_exact_checkjoin_allowed": False,
        "logout_cluster_transfer_reconnect_before_exact_checkjoin_or_window_close_allowed": False,
        "mixed_transfer_reconnect_same_approved_window_allowed": False,
        "approved_window_must_not_mix_direct_join_transfer_or_reconnect": True,
        "observer_gate_required_before_logout": "ShooterGameMode.CheckJoinInProgress(1,0)",
        "observer_gate": {
            "required_role": "session_start_rejected",
            "required_function": "ShooterGameMode.CheckJoinInProgress",
            "required_call": "CheckJoinInProgress(1,0)",
            "required_copied_bool_fields": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
            "required_copied_bool_values": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
            "wait_until_observer_sees_exact_checkjoin_or_window_closes": True,
            "logout_before_observer_gate_or_window_close_allowed": False,
        },
        "tester_instruction": (
            "one tester direct-joins the exact target, waits in that session until the "
            "observer reports exact CheckJoinInProgress(1,0) or the approved window closes, "
            "then logs out once only when told"
        ),
        "forbidden_same_window_actions": [
            "second_tester_join",
            "cluster_transfer",
            "logout_before_exact_checkjoin_or_window_close",
            "reconnect_before_exact_checkjoin_or_window_close",
            "mixed_transfer_and_reconnect_flow",
        ],
        "stale_or_diagnostic_exact_checkjoin_boundary": checkjoin_stimulus_boundary(),
        "choreography_authorizes_discord": False,
        "choreography_authorizes_runtime_capture": False,
        "choreography_authorizes_server_operations": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION,
    }


def direct_join_plan(payload: dict[str, Any]) -> dict[str, Any]:
    target = payload["target"]
    wait_seconds = requested_wait_window_seconds(payload)
    return {
        "schema": DIRECT_JOIN_PLAN_SCHEMA,
        "target": target,
        "route": "direct_join_exact_server_map",
        "target_instance": target["instance"],
        "target_map": target["map"],
        "target_map_is_theisland": target["map"] == "TheIsland",
        "fastest_clean_theisland_direct_join": target["map"] == "TheIsland",
        "direct_join_required": True,
        "cluster_transfer_required": False,
        "extra_transfer_server_required": False,
        "third_ark_server_allowed": False,
        "max_running_ark_servers": 2,
        "broad_discord_or_community_notice_allowed": False,
        "approved_notice_path": payload["notice_path"],
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "secret_or_webhook_output_allowed": False,
        "diagnostic_candidates_allowed_for_approved_evidence": False,
        "beta_runtime_choreography": beta_runtime_choreography(payload),
        "organic_wait_window_seconds": wait_seconds,
        "max_organic_wait_window_seconds": MAX_APPROVED_WINDOW_SECONDS,
        "organic_wait_window_authorizes_current_turn_approval": False,
        "organic_wait_window_authorizes_deploy_or_restart": False,
        "organic_wait_window_authorizes_runtime_capture": False,
        "organic_wait_window_counts_as_approved_runtime_evidence": False,
        "receipt_before_activation_required": True,
        "post_window_replay_requires_receipt": True,
        "non_authorization": DIRECT_JOIN_PLAN_NON_AUTHORIZATION,
    }


def player_notice_action(payload: dict[str, Any]) -> dict[str, Any]:
    required = payload["user_policy"] == "operator_approved_beta_users"
    return {
        "schema": PLAYER_NOTICE_ACTION_SCHEMA,
        "required": required,
        "notice_path": payload["notice_path"],
        "approved_notice_path_must_be_named": required,
        "dry_run_required_before_send": required,
        "real_notice_send_required_before_activation": required,
        "send_performed_by_request_pack": False,
        "request_pack_authorizes_discord": False,
        "activation_allowed_before_notice_sent": not required,
        "evidence_required": "dry_run_output_and_send_confirmation_reference" if required else "not_applicable",
        "activation_blocker": (
            "approved_dry_run_checked_beta_testers_notice_sent"
            if required
            else "no_player_notice_required"
        ),
        "non_authorization": PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    }


def player_presence_safety(payload: dict[str, Any]) -> dict[str, Any]:
    restart_requested = payload["restart_expectation"] == "restart"
    return {
        "schema": PLAYER_PRESENCE_SAFETY_SCHEMA,
        "target": payload["target"],
        "restart_expectation": payload["restart_expectation"],
        "connected_player_check_required_before_restart": restart_requested,
        "rcon_broadcast_required_if_players_connected": restart_requested,
        "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected": restart_requested,
        "passive_wait_preferred_after_activation": True,
        "linuxgsm_monitor_forbidden": True,
        "player_check_or_broadcast_authorized_by_request_pack": False,
        "non_authorization": PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
    }


def request_payload(args: argparse.Namespace) -> dict[str, Any]:
    evidence_dir = evidence_root() / args.run_id
    prepared_at_utc = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    env = env_lines(args)
    build_identity = planned_obelisk_build_identity(args)
    payload = {
        "schema": SCHEMA,
        "status": "candidate_only_request_pack",
        "approval_required": approval_required_text(args),
        "prepared_at_utc": prepared_at_utc,
        "target": {"instance": args.instance, "map": args.map_name},
        "run_id": args.run_id,
        "ark_binary_sha256": args.binary_sha256,
        "server_binary_path": args.server_binary_path,
        "obelisk_commit": args.obelisk_commit,
        "planned_obelisk_build_identity": build_identity,
        "approved_window": {
            "start_utc": args.approved_window_start_utc,
            "end_utc": args.approved_window_end_utc,
        },
        "restart_expectation": args.restart_expectation,
        "final_posture": args.final_posture,
        "diagnostic_candidates_enabled": diagnostic_candidates_enabled(args),
        "authorization_flags": dict(AUTHORIZATION_FLAGS),
        "user_policy": args.user_policy,
        "notice_path": args.notice_path,
        "copied_evidence_dir": str(evidence_dir),
        "copied_log_path": str(evidence_dir / "Obelisk.log"),
        "window_manifest_path": str(evidence_dir / "window-manifest.env"),
        "observer_env_file": "observer-window.env",
        "runtime_triplet_contract": runtime_triplet_contract(),
        "marker_set": WINDOW_MARKERS,
        "forbidden_markers": FORBIDDEN_MARKERS,
        "non_claims": NON_CLAIMS,
    }
    payload["exact_target_scope"] = exact_target_scope(payload)
    payload["passive_wait_boundary"] = passive_wait_boundary(payload)
    payload["direct_join_plan"] = direct_join_plan(payload)
    payload["player_notice_action"] = player_notice_action(payload)
    payload["player_presence_safety"] = player_presence_safety(payload)
    payload["rollback"] = rollback_plan(payload["target"], args.rollback_owner)
    payload["post_window_replay_contract"] = post_window_replay_contract(payload)
    payload["current_turn_approval_scope"] = current_turn_approval_scope(payload, env)
    payload["deployment_intent"] = deployment_intent(payload)
    payload["operator_live_ops_brief"] = operator_live_ops_brief(payload, env)
    return payload


def post_window_replay_contract(
    payload: dict[str, Any],
) -> dict[str, Any]:
    evidence_dir = Path(payload["copied_evidence_dir"])
    return {
        "required": True,
        "offline_only": True,
        "sidecars": {
            "request_pack_path": str(evidence_dir / "window-request.json"),
            "observer_env_path": str(evidence_dir / "observer-window.env"),
            "operator_approval_request_path": str(evidence_dir / "operator-approval-request.md"),
            "operator_approval_receipt_path": str(evidence_dir / "operator-approval-receipt.json"),
            "preflight_pre_path": str(evidence_dir / "preflight-pre.json"),
            "preflight_post_path": str(evidence_dir / "preflight-post.json"),
            "window_manifest_path": str(evidence_dir / "window-manifest.env"),
            "copied_log_path": str(evidence_dir / "Obelisk.log"),
        },
        "checks": {
            "window_manifest_replay": [
                "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
                "--json",
                "--post-window-replay",
                str(evidence_dir / "window-manifest.env"),
            ],
        },
        "non_authorization": REPLAY_NON_AUTHORIZATION,
    }


def artifact_binding(payload: dict[str, Any]) -> dict[str, Any]:
    replay_contract = payload.get("post_window_replay_contract")
    if not isinstance(replay_contract, dict):
        replay_contract = post_window_replay_contract(payload)
    sidecars = replay_contract["sidecars"]
    return {
        "run_id": payload["run_id"],
        "copied_evidence_dir": payload["copied_evidence_dir"],
        "copied_log_path": payload["copied_log_path"],
        "window_manifest_path": payload["window_manifest_path"],
        "required_sidecars": {
            "window_request_json": sidecars["request_pack_path"],
            "observer_window_env": sidecars["observer_env_path"],
            "operator_approval_request_md": sidecars["operator_approval_request_path"],
            "operator_approval_receipt_json": sidecars["operator_approval_receipt_path"],
            "preflight_pre_json": sidecars["preflight_pre_path"],
            "preflight_post_json": sidecars["preflight_post_path"],
            "window_manifest_env": sidecars["window_manifest_path"],
            "copied_obelisk_log": sidecars["copied_log_path"],
        },
        "binding_claim": "exact_run_id_window_artifacts_only",
        "non_authorization": ARTIFACT_BINDING_NON_AUTHORIZATION,
    }


def current_turn_approval_scope(payload: dict[str, Any], env: list[str]) -> dict[str, Any]:
    window = payload["approved_window"]
    target_scope = payload.get("exact_target_scope")
    if not isinstance(target_scope, dict):
        target_scope = exact_target_scope(payload)
    passive_boundary = payload.get("passive_wait_boundary")
    if not isinstance(passive_boundary, dict):
        passive_boundary = passive_wait_boundary(payload)
    notice_action = payload.get("player_notice_action")
    if not isinstance(notice_action, dict):
        notice_action = player_notice_action(payload)
    player_safety = payload.get("player_presence_safety")
    if not isinstance(player_safety, dict):
        player_safety = player_presence_safety(payload)
    join_plan = payload.get("direct_join_plan")
    if not isinstance(join_plan, dict):
        join_plan = direct_join_plan(payload)
    return {
        "schema": APPROVAL_SCOPE_SCHEMA,
        "status": approval_scope_status(payload),
        "source_required": approval_scope_source_required(payload),
        "standing_approval_allowed": approval_scope_standing_allowed(payload),
        "request_pack_authorizes_deploy_or_runtime": False,
        "missing_or_ambiguous_scope_blocks_window": True,
        "required_operator_approval_fields": CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
        "required_named_scope": {
            "target": payload["target"],
            "exact_target_instance_map": target_scope,
            "marker_env_gates": {
                "markers": payload["marker_set"],
                "env_snapshot": env,
            },
            "restart_window": {
                "start_utc": window["start_utc"],
                "end_utc": window["end_utc"],
                "expectation": payload["restart_expectation"],
            },
            "player_presence_safety": player_safety,
            "player_notice_action": notice_action,
            "direct_join_plan": join_plan,
            "rollback": payload["rollback"],
            "evidence_paths": artifact_binding(payload)["required_sidecars"],
            "runtime_triplet_contract": payload_runtime_triplet_contract(payload),
            "passive_wait_boundary": passive_boundary,
            "final_posture": payload["final_posture"],
        },
        "non_authorization": APPROVAL_SCOPE_NON_AUTHORIZATION,
    }


def deployment_intent(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent_type": DRIFT_FIX_DEPLOYMENT_INTENT_TYPE,
        "status": "request_only_not_authorized",
        "planned_obelisk_commit": payload["obelisk_commit"],
        "planned_obelisk_build_identity": payload["planned_obelisk_build_identity"],
        "target": payload["target"],
        "request_only": True,
        "deployment_authorized": False,
        "restart_authorized": False,
        "runtime_capture_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "non_authorization": DRIFT_FIX_DEPLOYMENT_INTENT_NON_AUTHORIZATION,
    }


def operator_live_ops_brief(payload: dict[str, Any], env: list[str]) -> dict[str, Any]:
    window = payload["approved_window"]
    replay_contract = payload.get("post_window_replay_contract")
    if not isinstance(replay_contract, dict):
        replay_contract = post_window_replay_contract(payload)
    target_scope = payload.get("exact_target_scope")
    if not isinstance(target_scope, dict):
        target_scope = exact_target_scope(payload)
    passive_boundary = payload.get("passive_wait_boundary")
    if not isinstance(passive_boundary, dict):
        passive_boundary = passive_wait_boundary(payload)
    notice_action = payload.get("player_notice_action")
    if not isinstance(notice_action, dict):
        notice_action = player_notice_action(payload)
    player_safety = payload.get("player_presence_safety")
    if not isinstance(player_safety, dict):
        player_safety = player_presence_safety(payload)
    join_plan = payload.get("direct_join_plan")
    if not isinstance(join_plan, dict):
        join_plan = direct_join_plan(payload)
    return {
        "target": payload["target"],
        "exact_target_scope": target_scope,
        "feature_gates": {
            "observer": "player_principal_lifecycle_only",
            "plugins_disabled": True,
            "process_event_hook": True,
            "dispatch_limit": 0,
            "log_limit": 10,
            "candidate_diagnostics": "candidate_only_non_evidence"
            if payload.get("diagnostic_candidates_enabled")
            else False,
            "scanner_debug_and_callback_escape_gates": "forbidden",
        },
        "server_binary": {
            "path": payload["server_binary_path"],
            "sha256": payload["ark_binary_sha256"],
        },
        "marker_changes": {
            "set": payload["marker_set"],
            "forbidden": payload["forbidden_markers"],
        },
        "env_snapshot": env,
        "start_restart_stop_window": {
            "start_utc": window["start_utc"],
            "end_utc": window["end_utc"],
            "expectation": payload["restart_expectation"],
            "final_posture": payload["final_posture"],
        },
        "notice_path": payload["notice_path"],
        "player_notice_action": notice_action,
        "direct_join_plan": join_plan,
        "player_presence_safety": player_safety,
        "user_policy": payload["user_policy"],
        "evidence_capture": {
            "request_pack_path": replay_contract["sidecars"]["request_pack_path"],
            "copied_evidence_dir": payload["copied_evidence_dir"],
            "copied_log_path": payload["copied_log_path"],
            "window_manifest_path": payload["window_manifest_path"],
            "observer_env_file": payload["observer_env_file"],
            "observer_env_path": replay_contract["sidecars"]["observer_env_path"],
            "operator_approval_request_path": replay_contract["sidecars"]["operator_approval_request_path"],
            "operator_approval_receipt_path": replay_contract["sidecars"]["operator_approval_receipt_path"],
            "operator_approval_receipt_required": "completed_operator_receipt",
            "preflight_pre_path": replay_contract["sidecars"]["preflight_pre_path"],
            "preflight_post_path": replay_contract["sidecars"]["preflight_post_path"],
            "single_module_summary": "player_principal_lifecycle",
            "copied_log_only": True,
        },
        "artifact_binding": artifact_binding(payload),
        "deployment_intent": deployment_intent(payload),
        "runtime_triplet_contract": payload_runtime_triplet_contract(payload),
        "passive_wait_boundary": passive_boundary,
        "rollback": payload["rollback"],
        "post_run_stable_posture": {
            "required": True,
            "expected": payload["final_posture"],
            "stable_markers_preserved": ["enable-process-event-hook", "disable-plugins"],
            "observer_markers_removed": True,
            "verification_commands": post_run_verification_commands(payload),
        },
        "approval_boundary": payload["approval_required"],
        "non_authorization": BRIEF_NON_AUTHORIZATION,
    }


def post_run_verification_commands(payload: dict[str, Any]) -> list[list[str]]:
    target = payload["target"]
    preflight = [
        "scripts/check_player_principal_lifecycle_preflight.sh",
        "--instance",
        target["instance"],
        "--map",
        target["map"],
        "--mode",
        "stable",
        "--expected-binary-sha256",
        payload["ark_binary_sha256"],
    ]
    return [
        preflight,
        [
            "scripts/check_obelisk_server_posture.sh",
            "--expect-stable",
            "--map",
            target["map"],
            "--instance",
            target["instance"],
        ],
    ]


def evidence_sidecar_command_lines(payload: dict[str, Any]) -> list[str]:
    target = payload["target"]
    evidence_dir = Path(payload["copied_evidence_dir"])
    common_binding = [
        "--run-id",
        payload["run_id"],
        "--window-manifest",
        str(evidence_dir / "window-manifest.env"),
        "--copied-log",
        str(evidence_dir / "Obelisk.log"),
        "--evidence-dir",
        str(evidence_dir),
    ]
    diagnostic_preflight_flags: list[str] = []
    if payload.get("diagnostic_candidates_enabled"):
        diagnostic_preflight_flags.append("--allow-diagnostic-candidates")
    preflight_pre = [
        "scripts/check_player_principal_lifecycle_preflight.sh",
        "--instance",
        target["instance"],
        "--target-map",
        target["map"],
        "--mode",
        "observer-window",
        "--env-file",
        str(evidence_dir / "observer-window.env"),
        "--expected-binary-sha256",
        payload["ark_binary_sha256"],
        *common_binding,
        *diagnostic_preflight_flags,
        "--json",
    ]
    preflight_post = [
        "scripts/check_player_principal_lifecycle_preflight.sh",
        "--instance",
        target["instance"],
        "--map",
        target["map"],
        "--mode",
        "stable",
        "--expected-binary-sha256",
        payload["ark_binary_sha256"],
        *common_binding,
        "--json",
    ]
    copy_ready_log = [
        "scripts/copy_player_principal_lifecycle_ready_log.py",
        "--instance",
        target["instance"],
        "--evidence-dir",
        str(evidence_dir),
        "--expected-binary-sha256",
        payload["ark_binary_sha256"],
        "--fresh-window-start-utc",
        payload["approved_window"]["start_utc"],
        "--fresh-window-end-utc",
        payload["approved_window"]["end_utc"],
        "--allow-live-log-read",
        "--allow-evidence-dir-write",
        "--allow-post-window-sidecar-generation",
        "--allow-post-window-preflight-live-read",
        "--execute",
        "--json",
    ]
    return [
        " ".join(preflight_pre) + f" > {evidence_dir / 'preflight-pre.json'}",
        "# The ready-log copy helper copies Obelisk.log and generates/checks preflight-post.json plus window-manifest.env.",
        " ".join(copy_ready_log),
        "# Manual stable preflight fallback if the copy helper is not used:",
        " ".join(preflight_post) + f" > {evidence_dir / 'preflight-post.json'}",
    ]


def markdown_request(payload: dict[str, Any], env: list[str]) -> str:
    target = payload["target"]
    window = payload["approved_window"]
    approval_scope = payload["current_turn_approval_scope"]
    deployment = payload["deployment_intent"]
    build_identity = payload["planned_obelisk_build_identity"]
    build_artifact = build_identity["build_artifact"]
    beta_choreography = payload["direct_join_plan"]["beta_runtime_choreography"]
    observer_gate = beta_choreography["observer_gate"]
    replay_sidecars = payload["post_window_replay_contract"]["sidecars"]
    artifact_sidecars = artifact_binding(payload)["required_sidecars"]
    rollback = rollback_plan_with_marker_paths(payload)
    triplet_contract = payload_runtime_triplet_contract(payload)
    standing_allowed = approval_scope["standing_approval_allowed"]
    followup_scope_text = (
        "active follow-up requires completed receipt binding standing launch authority to this exact window"
        if standing_allowed
        else "active follow-up requires fresh exact current-turn scope"
    )
    command_approval_line = (
        "requires_bound_standing_launch_authority_receipt_before_execution=true"
        if standing_allowed
        else "requires_current_turn_operator_approval_before_execution=true"
    )
    lines = [
        "# Player Principal Lifecycle Window Request",
        "",
        "This is a request pack only. It does not authorize server operations.",
        "Wait-only/passive monitoring is not approval and does not authorize deploy or restart.",
        "",
        "Approve one consume-only PlayerPrincipalLifecycleObserver runtime evidence window:",
        "",
        "```text",
        f"target instance={target['instance']}",
        f"target map={target['map']}",
        "target exact instance/map required=true",
        "target aliases allowed=false",
        f"run_id={payload['run_id']}",
        f"prepared_at_utc={payload['prepared_at_utc']}",
        f"ARK binary SHA256={payload['ark_binary_sha256']}",
        f"ARK binary path={payload['server_binary_path']}",
        f"Obelisk commit/build={payload['obelisk_commit']}",
        f"planned Obelisk build artifact available={str(build_artifact['available']).lower()}",
        f"planned Obelisk build artifact source={build_artifact['source']}",
        f"planned Obelisk build artifact name={build_artifact['artifact_name']}",
        f"planned Obelisk build artifact SHA256={build_artifact['artifact_sha256']}",
        f"planned Obelisk build artifact size bytes={build_artifact['size_bytes']}",
        f"requested UTC window={window['start_utc']}/{window['end_utc']}",
        f"restart expectation={payload['restart_expectation']}",
        f"final posture={payload['final_posture']}",
        f"diagnostic candidates enabled={str(diagnostic_candidates_enabled(payload)).lower()}",
        f"connected-user policy={payload['user_policy']}",
        f"notice path={payload['notice_path']}",
        f"player notice required={str(payload['player_notice_action']['required']).lower()}",
        f"player notice dry-run required={str(payload['player_notice_action']['dry_run_required_before_send']).lower()}",
        f"player notice real send required before activation={str(payload['player_notice_action']['real_notice_send_required_before_activation']).lower()}",
        f"player notice activation allowed before sent={str(payload['player_notice_action']['activation_allowed_before_notice_sent']).lower()}",
        f"player notice action blocker={payload['player_notice_action']['activation_blocker']}",
        f"direct join route={payload['direct_join_plan']['route']}",
        f"direct join target instance={payload['direct_join_plan']['target_instance']}",
        f"direct join target map={payload['direct_join_plan']['target_map']}",
        f"fastest clean TheIsland direct join={str(payload['direct_join_plan']['fastest_clean_theisland_direct_join']).lower()}",
        "direct join cluster transfer required=false",
        "direct join extra transfer server required=false",
        "third ARK server allowed=false",
        "broad Discord/community notice allowed=false",
        f"beta runtime choreography single tester only={str(beta_choreography['single_tester_only']).lower()}",
        f"beta runtime choreography direct target join required={str(beta_choreography['direct_target_join_required']).lower()}",
        f"beta runtime choreography observer gate={beta_choreography['observer_gate_required_before_logout']}",
        f"beta runtime choreography waits for exact checkjoin or window close={str(observer_gate['wait_until_observer_sees_exact_checkjoin_or_window_closes']).lower()}",
        "beta runtime choreography logout once when asked after gate/window close=true",
        "beta runtime choreography cluster transfer allowed=false",
        "beta runtime choreography reconnect before exact checkjoin allowed=false",
        "beta runtime choreography logout before exact checkjoin allowed=false",
        "beta runtime choreography mixed transfer/reconnect same approved window allowed=false",
        "beta runtime choreography counts as approved runtime evidence=false",
        f"connected player check before restart required={str(payload['player_presence_safety']['connected_player_check_required_before_restart']).lower()}",
        f"RCON broadcast if players connected required={str(payload['player_presence_safety']['rcon_broadcast_required_if_players_connected']).lower()}",
        f"restart cancel/reschedule if players remain connected={str(payload['player_presence_safety']['restart_must_be_cancelled_or_rescheduled_if_players_remain_connected']).lower()}",
        "player presence check or broadcast authorized by request pack=false",
        f"copied evidence dir={payload['copied_evidence_dir']}/",
        f"rollback owner={rollback['owner']}",
        f"rollback delta={rollback['delta']}",
        f"rollback marker_state_dir={rollback['marker_state_dir']}",
        *[
            f"rollback stable_marker_path.{key}={rollback['stable_marker_paths'][key]}"
            for key in sorted(rollback["stable_marker_paths"])
        ],
        *[
            f"rollback observer_marker_path.{key}={rollback['observer_marker_paths'][key]}"
            for key in sorted(rollback["observer_marker_paths"])
        ],
        "passive wait boundary=wait-only/passive is not approval",
        f"requested organic wait window seconds={payload['passive_wait_boundary']['requested_wait_window_seconds']}",
        f"requested organic wait window max seconds={payload['passive_wait_boundary']['max_requested_wait_window_seconds']}",
        "requested organic wait window checked only=true",
        "requested organic wait window authorizes current-turn approval=false",
        "passive wait authorizes deploy/restart=false",
        "passive monitor ticks authorize runtime capture=false",
        "player presence detection authorizes follow-up=false",
        "snapshots or diagnostics count as approved runtime evidence=false",
        "plugins disabled=true",
        "dispatch limit=0",
        "log limit=10",
        "diagnostic candidate lines are non-evidence",
        f"session_start_rejected required call={triplet_contract['session_start_rejected']['required_call']}",
        "session_start_rejected copied bools=bIsFromLogin,ReturnValue=1,0",
        "HandleNewPlayer rejected tuples allowed as session_start_rejected alternatives=false",
        "```",
        "",
        "Exact approval scope required before any deploy or runtime evidence:",
        "",
        "```text",
        f"scope_status={approval_scope['status']}",
        f"source_required={approval_scope['source_required']}",
        f"standing_approval_allowed={str(standing_allowed).lower()}",
        "request_pack_authorizes_deploy_or_runtime=false",
        "missing_or_ambiguous_scope_blocks_window=true",
        "required_operator_approval_fields="
        + ",".join(approval_scope["required_operator_approval_fields"]),
        f"target={target['instance']}/{target['map']}",
        f"exact_target_instance_map={target['instance']}/{target['map']} aliases_allowed=false",
        "marker_env_gates=exact marker set plus exact observer env snapshot",
        f"restart_window={window['start_utc']}/{window['end_utc']} expectation={payload['restart_expectation']}",
        f"player_presence_safety=restart_check_required:{str(payload['player_presence_safety']['connected_player_check_required_before_restart']).lower()} broadcast_if_players:{str(payload['player_presence_safety']['rcon_broadcast_required_if_players_connected']).lower()} request_pack_authorizes:false",
        f"player_notice_action={payload['player_notice_action']['activation_blocker']} path={payload['notice_path']}",
        f"direct_join_plan={payload['direct_join_plan']['route']} target={target['instance']}/{target['map']} third_server_allowed=false organic_wait_seconds={payload['direct_join_plan']['organic_wait_window_seconds']}",
        "beta_runtime_choreography=single_tester_direct_join "
        f"observer_gate={beta_choreography['observer_gate_required_before_logout']} "
        "mixed_transfer_reconnect_same_window_allowed=false "
        "counts_as_approved_runtime_evidence=false",
        f"rollback={rollback['owner']} {rollback['delta']}",
        f"rollback_marker_state_dir={rollback['marker_state_dir']}",
        *[f"evidence_path.{key}={value}" for key, value in artifact_sidecars.items()],
        f"runtime_triplet_contract.session_start_rejected={triplet_contract['session_start_rejected']['required_call']}",
        "runtime_triplet_contract.session_start_rejected.copied_bools=bIsFromLogin,ReturnValue=1,0",
        "runtime_triplet_contract.HandleNewPlayer_rejected_alternative=false",
        f"passive_wait_boundary=wait-only/passive is not approval; requested wait window checked only; {followup_scope_text}",
        f"final_posture={payload['final_posture']}",
        approval_scope["non_authorization"],
        "```",
        "",
        "Drift-fix deployment intent:",
        "",
        "```text",
        f"intent_type={deployment['intent_type']}",
        f"planned_obelisk_commit={deployment['planned_obelisk_commit']}",
        f"planned_obelisk_build_identity_schema={build_identity['schema']}",
        f"planned_obelisk_build_artifact_available={str(build_artifact['available']).lower()}",
        f"planned_obelisk_build_artifact_source={build_artifact['source']}",
        f"planned_obelisk_build_artifact_name={build_artifact['artifact_name']}",
        f"planned_obelisk_build_artifact_sha256={build_artifact['artifact_sha256']}",
        "request_only=true",
        "deployment_authorized=false",
        "restart_authorized=false",
        "runtime_capture_authorized=false",
        "counts_as_approved_runtime_evidence=false",
        deployment["non_authorization"],
        "```",
        "",
        "Post-run verification commands:",
        "",
        "```text",
        command_approval_line,
        "commands_authorize_runtime_or_public_readiness=false",
        *[" ".join(command) for command in post_run_verification_commands(payload)],
        "```",
        "",
        "Required evidence sidecar commands:",
        "",
        "```text",
        command_approval_line,
        "commands_authorize_runtime_or_public_readiness=false",
        *evidence_sidecar_command_lines(payload),
        "```",
        "",
        "Post-window replay contract:",
        "",
        "```text",
        *[
            f"{key}={replay_sidecars[key]}"
            for key in (
                "request_pack_path",
                "observer_env_path",
                "operator_approval_request_path",
                "operator_approval_receipt_path",
                "preflight_pre_path",
                "preflight_post_path",
                "window_manifest_path",
                "copied_log_path",
            )
        ],
        "operator_approval_receipt_requirement=completed operator-approval-receipt.json; generated template is not replay evidence",
        " ".join(payload["post_window_replay_contract"]["checks"]["window_manifest_replay"]),
        payload["post_window_replay_contract"]["non_authorization"],
        "```",
        "",
        "Exact observer env snapshot:",
        "",
        "```text",
        *env,
        "```",
        "",
        "Exact instance markers:",
        "",
        "```text",
        *payload["marker_set"],
        "```",
        "",
        "Non-claims:",
        "",
        *[f"- {item}" for item in payload["non_claims"]],
        "",
    ]
    return "\n".join(lines)


def artifact(path: Path) -> dict[str, str]:
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def bound_artifact(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def request_pack_digest(
    *,
    request_json_path: Path,
    request_md_path: Path,
    env_path: Path,
) -> dict[str, str]:
    domain = b"obelisk.player-principal-lifecycle.request-pack.v1"
    material = b"\0".join(
        (
            domain,
            b"window-request.json",
            request_json_path.read_bytes(),
            b"observer-window.env",
            env_path.read_bytes(),
            b"operator-approval-request.md",
            request_md_path.read_bytes(),
        )
    )
    return {
        "algorithm": "sha256",
        "domain": domain.decode("ascii"),
        "sha256": hashlib.sha256(material).hexdigest(),
    }


def operator_approval_receipt_payload(
    payload: dict[str, Any],
    *,
    request_json_path: Path,
    request_md_path: Path,
    env_path: Path,
    operator_approved: bool = False,
    operator_reference: str = "pending_operator_completion",
    approved_at_utc: str = "pending_operator_completion",
) -> dict[str, Any]:
    status = "completed_operator_receipt" if operator_approved else "generated_template"
    standing_launch_authority = operator_approved and standing_launch_authority_enabled(payload)
    approval_source = (
        APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
        if standing_launch_authority
        else APPROVAL_SOURCE_CURRENT_TURN
    )
    attestation = (
        APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
        if standing_launch_authority
        else APPROVAL_ATTESTATION_CURRENT_TURN
    )
    target_scope = payload.get("exact_target_scope")
    if not isinstance(target_scope, dict):
        target_scope = exact_target_scope(payload)
    passive_boundary = payload.get("passive_wait_boundary")
    if not isinstance(passive_boundary, dict):
        passive_boundary = passive_wait_boundary(payload)
    player_safety = payload.get("player_presence_safety")
    if not isinstance(player_safety, dict):
        player_safety = player_presence_safety(payload)
    rollback = rollback_plan_with_marker_paths(payload)
    return {
        "schema": APPROVAL_RECEIPT_SCHEMA,
        "status": status,
        "receipt_completed": operator_approved,
        "operator_current_turn_approval_recorded": operator_approved and not standing_launch_authority,
        "standing_launch_authority_recorded": standing_launch_authority,
        "standing_launch_authority_satisfies_operator_approval": standing_launch_authority,
        "approval_scope": {
            "scope_type": "exact_bound_player_principal_lifecycle_window_only",
            "standing_approval": standing_launch_authority,
            "reusable": False,
            "future_windows_authorized": False,
            "scope_expansion_authorized": False,
            "unbound_artifacts_authorized": False,
        },
        "bound_request_pack": {
            "run_id": payload["run_id"],
            "prepared_at_utc": payload["prepared_at_utc"],
            "target": payload["target"],
            "exact_target_scope": target_scope,
            "approved_window": payload["approved_window"],
            "obelisk_commit": payload["obelisk_commit"],
            "planned_obelisk_build_identity": payload["planned_obelisk_build_identity"],
            "ark_binary_sha256": payload["ark_binary_sha256"],
            "server_binary_path": payload["server_binary_path"],
            "restart_expectation": payload["restart_expectation"],
            "final_posture": payload["final_posture"],
            "user_policy": payload["user_policy"],
            "notice_path": payload["notice_path"],
            "player_notice_action": payload["player_notice_action"],
            "direct_join_plan": payload["direct_join_plan"],
            "player_presence_safety": player_safety,
            "copied_evidence_dir": payload["copied_evidence_dir"],
            "copied_log_path": payload["copied_log_path"],
            "window_manifest_path": payload["window_manifest_path"],
            "rollback": rollback,
            "passive_wait_boundary": passive_boundary,
            "runtime_triplet_contract": payload_runtime_triplet_contract(payload),
            "current_turn_approval_scope": payload["current_turn_approval_scope"],
            "deployment_intent": payload["deployment_intent"],
        },
        "bound_artifacts": {
            "window_request_json": bound_artifact(request_json_path),
            "observer_window_env": bound_artifact(env_path),
            "operator_approval_request_md": bound_artifact(request_md_path),
        },
        "request_pack_digest": request_pack_digest(
            request_json_path=request_json_path,
            request_md_path=request_md_path,
            env_path=env_path,
        ),
        "operator_completion": {
            "approval_recorded_at_utc": approved_at_utc if operator_approved else None,
            "approved_by_role": operator_reference if operator_approved else None,
            "approval_source": approval_source if operator_approved else None,
            "attestation": attestation if operator_approved else None,
        },
        "non_authorization_flags": {
            "request_pack_acceptance_authorizes_runtime": False,
            "generated_template_authorizes_runtime": False,
            "server_operations_authorized_by_template": False,
            "runtime_work_authorized_by_template": False,
            "discord_authorized": False,
            "discord_send_authorized": False,
            "current_turn_scope_authorized": False,
            "marker_env_changes_authorized": False,
            "runtime_capture_authorized": False,
            "runtime_window_authorized": False,
            "github_publication_authorized": False,
            "publication_authorized": False,
            "promotion_ready": False,
            "public_abi_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "route_ready": False,
            "v1_completion_ready": False,
            "sdk_accounting_counts_as_completed_surface": False,
            "p0_accounting_counts_as_promoted_surface": False,
            "secrets_included": False,
            "player_private_data_included": False,
        },
        "non_claims": OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS,
    }


def bound_receipt_recorded_at_utc(payload: dict[str, Any]) -> str:
    prepared_at = parse_utc(payload["prepared_at_utc"], "prepared_at_utc")
    return (prepared_at + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    args = parse_args()
    validate_args(args)
    reject_symlink_component(args.output_dir, "--output-dir")
    protected_paths.reject_server_root_write_without_opt_in(args.output_dir.expanduser(), "--output-dir")
    output_dir = reject_protected_output_path(args.output_dir.expanduser(), "--output-dir")

    env = env_lines(args)
    payload = request_payload(args)
    output_dir.mkdir(parents=True, exist_ok=True)
    env_path = output_dir / "observer-window.env"
    request_json_path = output_dir / "window-request.json"
    request_md_path = output_dir / "operator-approval-request.md"
    receipt_template_path = output_dir / "operator-approval-receipt.template.json"
    receipt_path = output_dir / "operator-approval-receipt.json"

    env_path.write_text("\n".join(env_file_lines(args)) + "\n", encoding="utf-8")
    request_json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    request_md_path.write_text(markdown_request(payload, env), encoding="utf-8")
    receipt_template_path.write_text(
        json.dumps(
            operator_approval_receipt_payload(
                payload,
                request_json_path=request_json_path,
                request_md_path=request_md_path,
                env_path=env_path,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    completed_receipt_artifact: dict[str, Any] | None = None
    if args.standing_launch_authority:
        receipt_path.write_text(
            json.dumps(
                operator_approval_receipt_payload(
                    payload,
                    request_json_path=request_json_path,
                    request_md_path=request_md_path,
                    env_path=env_path,
                    operator_approved=True,
                    operator_reference=args.standing_launch_authority_reference,
                    approved_at_utc=bound_receipt_recorded_at_utc(payload),
                ),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        completed_receipt_artifact = artifact(receipt_path)

    report = {
        "schema": SCHEMA,
        "status": "prepared",
        "ready_scope": "offline_request_pack_generation_only",
        "current_turn_operator_approval_required": not bool(args.standing_launch_authority),
        "current_turn_approval_recorded": False,
        "request_pack_records_current_turn_approval": False,
        "standing_launch_authority_recorded": bool(args.standing_launch_authority),
        "standing_launch_authority_satisfies_operator_approval": bool(
            args.standing_launch_authority
        ),
        "operator_approval_receipt_written": bool(args.standing_launch_authority),
        "operator_runtime_authority_source": (
            APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
            if args.standing_launch_authority
            else APPROVAL_SOURCE_CURRENT_TURN
        ),
        "authorization_source": "none_request_pack_only",
        "approved_runtime_evidence_source": "none_request_pack_only",
        "planning_only": True,
        "approval_required": payload["approval_required"],
        "exact_target_scope": payload["exact_target_scope"],
        "runtime_triplet_contract": payload_runtime_triplet_contract(payload),
        "passive_wait_boundary": payload["passive_wait_boundary"],
        "direct_join_plan": payload["direct_join_plan"],
        "requested_wait_window_seconds": payload["passive_wait_boundary"]["requested_wait_window_seconds"],
        "max_requested_wait_window_seconds": MAX_APPROVED_WINDOW_SECONDS,
        "requested_wait_window_seconds_checked_only": True,
        "requested_wait_window_authorizes_current_turn_approval": False,
        "requested_wait_window_authorizes_runtime_capture": False,
        "passive_wait_or_watch_only_authorizes_deploy_or_restart": False,
        "discord_authorized": False,
        "discord_send_authorized": False,
        "discord_sent": False,
        "marker_env_changes_authorized": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "runtime_capture_authorized": False,
        "runtime_window_authorized": False,
        "read_live_logs": False,
        "reads_live_logs": False,
        "live_log_reads_authorized": False,
        "live_log_permission_granted": False,
        "publication_authorized": False,
        "promotion_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "request_pack_counts_as_approved_runtime_evidence": False,
        "observer_env_counts_as_approved_runtime_evidence": False,
        "operator_request_counts_as_approved_runtime_evidence": False,
        "copied_log_metadata_counts_as_approved_runtime_evidence": False,
        "bundle_output_counts_as_approved_runtime_evidence": False,
        "preflight_counts_as_approved_runtime_evidence": False,
        "window_manifest_counts_as_approved_runtime_evidence": False,
        "completed_receipt_counts_as_approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "route_ready": False,
        "diagnostic_candidates_enabled": diagnostic_candidates_enabled(args),
        "current_turn_approval_required_fields": CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
        "current_turn_approval_scope_status": approval_scope_status(payload),
        "deployment_intent": deployment_intent(payload),
        "planned_obelisk_build_identity": payload["planned_obelisk_build_identity"],
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "next_blocker": (
            "runtime_window_preflight_required"
            if args.standing_launch_authority
            else "operator_current_turn_runtime_window_approval_required"
        ),
        "outputs": {
            "observer_env": artifact(env_path),
            "request_json": artifact(request_json_path),
            "operator_request": artifact(request_md_path),
            "operator_approval_receipt_template": artifact(receipt_template_path),
            "operator_approval_receipt": completed_receipt_artifact,
        },
        "target": payload["target"],
        "run_id": args.run_id,
        "non_claim": "request pack only; no server operation, marker/env change, runtime capture, public SDK readiness, or v1 completion",
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"player_principal_lifecycle_window_request=prepared output_dir={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
