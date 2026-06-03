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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
MAX_APPROVED_WINDOW_SECONDS = 600
MAX_REQUEST_PREPARATION_LEAD_SECONDS = 3600
MAX_OPERATOR_APPROVAL_LEAD_SECONDS = 600
APPROVAL_TEXT = "current-turn operator-approved runtime window, not standing approval"
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
    "server_operations_authorized": False,
    "runtime_work_authorized": False,
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
EVIDENCE_ROOT = Path("/servidor/ark/workspace-offline/live-validation-logs")
REQUIRED_ENV = {
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK": "1",
    "OBELISK_DISABLE_PLUGINS": "1",
    "OBELISK_WRAPPER_PROFILE": "observer-debug",
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER": "1",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT": "10",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT": "0",
    "OBELISK_PE_TRACE_LIMIT": "0",
}
OBSERVER_ENV_KEYS = (
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
    "does not promote public player identity",
    "does not claim stable principal identity",
    "does not promote permissions/admin",
    "does not promote command/chat response or commands/replies",
    "does not authorize lookup, persistence, mutation, return override, plugin delivery, runtime readiness, public SDK readiness, or v1 SDK completion",
]


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


def validate_args(args: argparse.Namespace) -> None:
    require_safe_token(args.instance, "--instance")
    require_safe_token(args.map_name, "--map")
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
    if (end - start).total_seconds() > MAX_APPROVED_WINDOW_SECONDS:
        raise SystemExit("--approved-window duration must not exceed 10 minutes")
    if args.restart_expectation not in {"none", "start", "restart"}:
        raise SystemExit(POSTURE_GUARDRAIL_TEXT)
    if args.final_posture != "stable":
        raise SystemExit(POSTURE_GUARDRAIL_TEXT)
    expected_run_id = run_id_for_window_start(start)
    if args.run_id != expected_run_id:
        raise SystemExit(f"--run-id timestamp must match --approved-window-start-utc exactly: {expected_run_id}")
    if args.user_policy == "operator_approved_beta_users" and args.notice_path == "not_applicable":
        raise SystemExit("--notice-path must name the approved notice path for beta-user windows")
    if args.notice_path != "not_applicable" and not re.fullmatch(r"[A-Za-z0-9_.:/ -]+", args.notice_path):
        raise SystemExit("--notice-path contains unsafe characters")
    if not re.fullmatch(r"[A-Za-z0-9_.@ -]+", args.rollback_owner):
        raise SystemExit("--rollback-owner contains unsafe characters")


def env_lines(args: argparse.Namespace) -> list[str]:
    values = {
        "OBELISK_INSTANCE_ID": args.instance,
        **REQUIRED_ENV,
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256": args.binary_sha256,
    }
    return [f"{key}={values[key]}" for key in OBSERVER_ENV_KEYS]


def env_file_lines(args: argparse.Namespace) -> list[str]:
    return [
        "# request-pack-only; does not authorize marker/env changes, runtime work, or server operations",
        "# request_pack_counts_as_approved_runtime_evidence=false",
        "# stable_claim_allowed=false",
        *env_lines(args),
    ]


def request_payload(args: argparse.Namespace) -> dict[str, Any]:
    evidence_dir = EVIDENCE_ROOT / args.run_id
    prepared_at_utc = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema": SCHEMA,
        "status": "candidate_only_request_pack",
        "approval_required": APPROVAL_TEXT,
        "prepared_at_utc": prepared_at_utc,
        "target": {"instance": args.instance, "map": args.map_name},
        "run_id": args.run_id,
        "ark_binary_sha256": args.binary_sha256,
        "server_binary_path": args.server_binary_path,
        "obelisk_commit": args.obelisk_commit,
        "approved_window": {
            "start_utc": args.approved_window_start_utc,
            "end_utc": args.approved_window_end_utc,
        },
        "restart_expectation": args.restart_expectation,
        "final_posture": args.final_posture,
        "authorization_flags": dict(AUTHORIZATION_FLAGS),
        "user_policy": args.user_policy,
        "notice_path": args.notice_path,
        "copied_evidence_dir": str(evidence_dir),
        "copied_log_path": str(evidence_dir / "Obelisk.log"),
        "window_manifest_path": str(evidence_dir / "window-manifest.env"),
        "observer_env_file": "observer-window.env",
        "marker_set": WINDOW_MARKERS,
        "forbidden_markers": FORBIDDEN_MARKERS,
        "rollback": {
            "owner": args.rollback_owner,
            "delta": REQUEST_ROLLBACK_DELTA,
        },
        "non_claims": NON_CLAIMS,
    }
    payload["post_window_replay_contract"] = post_window_replay_contract(payload)
    payload["operator_live_ops_brief"] = operator_live_ops_brief(payload, env_lines(args))
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


def operator_live_ops_brief(payload: dict[str, Any], env: list[str]) -> dict[str, Any]:
    window = payload["approved_window"]
    replay_contract = payload.get("post_window_replay_contract")
    if not isinstance(replay_contract, dict):
        replay_contract = post_window_replay_contract(payload)
    return {
        "target": payload["target"],
        "feature_gates": {
            "observer": "player_principal_lifecycle_only",
            "plugins_disabled": True,
            "process_event_hook": True,
            "dispatch_limit": 0,
            "log_limit": 10,
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
        "rollback": payload["rollback"],
        "post_run_stable_posture": {
            "required": True,
            "expected": payload["final_posture"],
            "stable_markers_preserved": ["enable-process-event-hook", "disable-plugins"],
            "observer_markers_removed": True,
            "verification_commands": post_run_verification_commands(payload),
        },
        "approval_boundary": APPROVAL_TEXT,
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
    return [
        " ".join(preflight_pre) + f" > {evidence_dir / 'preflight-pre.json'}",
        " ".join(preflight_post) + f" > {evidence_dir / 'preflight-post.json'}",
    ]


def markdown_request(payload: dict[str, Any], env: list[str]) -> str:
    target = payload["target"]
    window = payload["approved_window"]
    replay_sidecars = payload["post_window_replay_contract"]["sidecars"]
    lines = [
        "# Player Principal Lifecycle Window Request",
        "",
        "This is a request pack only. It does not authorize server operations.",
        "",
        "Approve one consume-only PlayerPrincipalLifecycleObserver runtime evidence window:",
        "",
        "```text",
        f"target instance={target['instance']}",
        f"target map={target['map']}",
        f"run_id={payload['run_id']}",
        f"prepared_at_utc={payload['prepared_at_utc']}",
        f"ARK binary SHA256={payload['ark_binary_sha256']}",
        f"ARK binary path={payload['server_binary_path']}",
        f"Obelisk commit/build={payload['obelisk_commit']}",
        f"approved UTC window={window['start_utc']}/{window['end_utc']}",
        f"restart expectation={payload['restart_expectation']}",
        f"final posture={payload['final_posture']}",
        f"connected-user policy={payload['user_policy']}",
        f"notice path={payload['notice_path']}",
        f"copied evidence dir={payload['copied_evidence_dir']}/",
        f"rollback owner={payload['rollback']['owner']}",
        f"rollback delta={payload['rollback']['delta']}",
        "plugins disabled=true",
        "dispatch limit=0",
        "log limit=10",
        "```",
        "",
        "Post-run verification commands:",
        "",
        "```text",
        "requires_current_turn_operator_approval_before_execution=true",
        "commands_authorize_runtime_or_public_readiness=false",
        *[" ".join(command) for command in post_run_verification_commands(payload)],
        "```",
        "",
        "Required evidence sidecar commands:",
        "",
        "```text",
        "requires_current_turn_operator_approval_before_execution=true",
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
    return {
        "schema": APPROVAL_RECEIPT_SCHEMA,
        "status": status,
        "receipt_completed": operator_approved,
        "operator_current_turn_approval_recorded": operator_approved,
        "approval_scope": {
            "scope_type": "exact_bound_player_principal_lifecycle_window_only",
            "standing_approval": False,
            "reusable": False,
            "future_windows_authorized": False,
            "scope_expansion_authorized": False,
            "unbound_artifacts_authorized": False,
        },
        "bound_request_pack": {
            "run_id": payload["run_id"],
            "prepared_at_utc": payload["prepared_at_utc"],
            "target": payload["target"],
            "approved_window": payload["approved_window"],
            "obelisk_commit": payload["obelisk_commit"],
            "ark_binary_sha256": payload["ark_binary_sha256"],
            "server_binary_path": payload["server_binary_path"],
            "restart_expectation": payload["restart_expectation"],
            "final_posture": payload["final_posture"],
            "user_policy": payload["user_policy"],
            "notice_path": payload["notice_path"],
            "copied_evidence_dir": payload["copied_evidence_dir"],
            "copied_log_path": payload["copied_log_path"],
            "window_manifest_path": payload["window_manifest_path"],
            "rollback": payload["rollback"],
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
            "approval_source": "current_turn_operator_message" if operator_approved else None,
            "attestation": "APPROVE_EXACT_BOUND_PLAYER_PRINCIPAL_LIFECYCLE_WINDOW_ONLY" if operator_approved else None,
        },
        "non_authorization_flags": {
            "request_pack_acceptance_authorizes_runtime": False,
            "generated_template_authorizes_runtime": False,
            "server_operations_authorized_by_template": False,
            "runtime_work_authorized_by_template": False,
            "discord_authorized": False,
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
        "non_claims": [
            "generated receipt template only; does not record operator approval",
            "completed receipt binds one current-turn request pack only",
            "receipt does not authorize future windows, standing approval, Discord, GitHub publication, public SDK readiness, runtime readiness, or v1 completion",
            "receipt does not promote public player identity, permissions/admin, command response, lookup, mutation, return override, or ResourceHandle",
        ],
    }


def main() -> int:
    args = parse_args()
    validate_args(args)
    reject_symlink_component(args.output_dir, "--output-dir")
    output_dir = reject_protected_output_path(args.output_dir.expanduser(), "--output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)

    env = env_lines(args)
    payload = request_payload(args)
    env_path = output_dir / "observer-window.env"
    request_json_path = output_dir / "window-request.json"
    request_md_path = output_dir / "operator-approval-request.md"
    receipt_template_path = output_dir / "operator-approval-receipt.template.json"

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

    report = {
        "schema": SCHEMA,
        "status": "prepared",
        "planning_only": True,
        "approval_required": APPROVAL_TEXT,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
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
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "next_blocker": "operator_current_turn_runtime_window_approval_required",
        "outputs": {
            "observer_env": artifact(env_path),
            "request_json": artifact(request_json_path),
            "operator_request": artifact(request_md_path),
            "operator_approval_receipt_template": artifact(receipt_template_path),
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
