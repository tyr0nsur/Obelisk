#!/usr/bin/env python3
"""Run or preflight normalized player-principal lifecycle next actions.

Default mode is dry-run. Execution is intentionally narrow: only structured
`runner_command` argv payloads, or simple allow-listed repo script command text, can run.
This tool never turns planning actions into runtime evidence or SDK readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths


SCHEMA = "obelisk.player-principal-lifecycle-next-action-runner.v1"
PLAN_SCHEMA = "obelisk.player-principal-lifecycle-next-action-plan.v1"
SERVER_ROOT = Path("/servidor/ark")
REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_OFFLINE_PARALLEL_LANE_IDS = (
    "runtime_evidence_closure_status",
    "single_player_multi_surface_candidate_pack",
    "post_runtime_identity_public_contract_gate",
    "post_identity_p0_chain_certificates",
)
CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA = (
    "obelisk.player-principal-lifecycle-current-live-diagnostic-blockers.v1"
)

FALSE_FLAGS = {
    "approved_runtime_evidence": False,
    "approved_in_game": False,
    "approved_in_game_evidence": False,
    "approved_in_game_evidence_ready": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "counts_toward_p0_dependency_chain": False,
    "counts_toward_sdk": False,
    "counts_toward_v1_completion": False,
    "discord_authorized": False,
    "discord_sent_by_this_report": False,
    "live_log_reads_authorized": False,
    "live_ops_authorized": False,
    "marker_env_changes_authorized": False,
    "post_window_preflight_live_read_authorized_by_this_report": False,
    "post_window_preflight_live_read_counts_as_approved_runtime_evidence": False,
    "post_window_sidecar_generation_authorized_by_this_report": False,
    "post_window_sidecar_generation_counts_as_approved_runtime_evidence": False,
    "public_sdk_ready": False,
    "publication_authorized": False,
    "runtime_capture_authorized": False,
    "runtime_evidence_present": False,
    "runtime_evidence_ready": False,
    "runtime_ready": False,
    "runtime_work_authorized": False,
    "server_operations_authorized": False,
    "stable_claim_allowed": False,
    "stable_sdk_ready": False,
    "v1_completion_ready": False,
    "workspace_writes_authorized": False,
}
FORBIDDEN_TRUE_KEYS = set(FALSE_FLAGS) | {
    "accepted_runtime_evidence",
    "accepted_in_game_evidence",
    "approved_in_game",
    "approved_in_game_evidence",
    "approved_in_game_evidence_ready",
    "approved_runtime_evidence_accepted",
    "authorizes_runtime_work",
    "authorizes_server_operations",
    "complete_sdk_ready",
    "public_abi_ready",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_window_authorized",
    "server_operations_authorized_by_this_report",
    "post_window_preflight_live_read_authorized_by_this_report",
    "post_window_preflight_live_read_counts_as_approved_runtime_evidence",
    "post_window_sidecar_generation_authorized_by_this_report",
    "post_window_sidecar_generation_counts_as_approved_runtime_evidence",
    "standing_authority_authorizes_runner",
    "standing_authority_counts_as_approved_runtime_evidence",
    "standing_authority_counts_as_runtime_evidence",
    "standing_authority_counts_as_sdk_evidence",
    "standing_authority_counts_toward_p0_dependency_chain",
    "standing_authority_counts_toward_sdk",
    "standing_launch_authority_authorizes_runner",
    "standing_launch_authority_counts_as_approved_runtime_evidence",
    "standing_launch_authority_counts_as_runtime_evidence",
    "standing_launch_authority_counts_as_sdk_evidence",
    "standing_launch_authority_counts_toward_complete_sdk_claim",
    "standing_launch_authority_counts_toward_p0_dependency_chain",
    "standing_launch_authority_counts_toward_sdk",
}
FORBIDDEN_PROGRESS_KEYS = {
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_progress",
    "progress",
    "public_sdk_progress_contribution",
    "runtime_progress",
    "runtime_progress_contribution",
    "sdk_progress",
    "v1_completion_contribution",
    "v1_progress",
}
NON_AUTHORIZATION = (
    "next-action runner report only; this report does not authorize Discord, ARK server "
    "operations, live log reads, marker/env changes, runtime capture, approved runtime "
    "evidence, public SDK readiness, stable SDK claims, publication, Plugin Hub, or P0 progress"
)
INPUT_FLAGS = {
    "--copied-log",
    "--window-manifest",
    "--post-window-replay",
    "--request-json",
    "--request-check-json",
    "--notice-report-json",
    "--route-gate-json",
}
OUTPUT_FLAGS = {
    "--emit-template",
    "--output",
    "--output-dir",
    "--json-output",
}
SAFE_REPO_SCRIPT_RE = re.compile(r"^scripts/[A-Za-z0-9_.-]+(?:\.py|\.sh)$")
OFFLINE_RUNNER_ALLOWED_SCRIPTS = {
    "scripts/report_obelisk_sdk_status.py",
    "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py",
    "scripts/report_player_principal_lifecycle_runtime_evidence_status.py",
    "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
    "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
}
LIVE_OPERATION_SCRIPT_BLOCKERS = {
    "scripts/monitor_ark_player_presence_passive.sh": "live_monitor_action_not_started_by_runner",
    "scripts/copy_player_principal_lifecycle_ready_log.py": "live_log_copy_not_started_by_runner",
    "scripts/send_discord_embed.py": "discord_send_not_started_by_runner",
    "scripts/prepare_player_principal_lifecycle_runtime_window_execution.py": (
        "runtime_window_execution_not_started_by_runner"
    ),
    "scripts/check_obelisk_server_posture.sh": "server_posture_live_check_not_started_by_runner",
    "scripts/check_player_principal_lifecycle_preflight.sh": (
        "preflight_server_posture_check_not_started_by_runner"
    ),
    "scripts/install_obelisk.sh": "install_or_server_layout_action_not_started_by_runner",
    "scripts/obelisk.py": "operator_cli_action_not_started_by_runner",
}
LIVE_OR_PRIVILEGED_FLAGS = {
    "--allow-live-log-read": "live_log_read_flag_not_allowed_by_runner",
    "--allow-live-procfs-read": "live_procfs_read_flag_not_allowed_by_runner",
    "--allow-post-window-preflight-live-read": "post_window_preflight_live_read_flag_not_allowed_by_runner",
    "--allow-post-window-sidecar-generation": "post_window_sidecar_generation_flag_not_allowed_by_runner",
    "--allow-protected-root": "protected_server_root_read_flag_not_allowed_by_runner",
    "--allow-server-operation": "server_operation_flag_not_allowed_by_runner",
    "--allow-server-operations": "server_operation_flag_not_allowed_by_runner",
    "--allow-live-ops": "live_ops_flag_not_allowed_by_runner",
}
STRUCTURED_ARGV_SHELL_TOKENS = ("|", ";", "&&", "||", "`", "$(", "<", ">")
SHELL_EXECUTABLE_NAMES = {"bash", "dash", "fish", "sh", "zsh"}
KNOWN_CLOSURE_ARTIFACTS = {
    "Obelisk.log",
    "window-manifest.env",
    "preflight-post.json",
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
}
APPROVED_RUNTIME_EVIDENCE_JSON = (
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
)
ARTIFACT_BLOCKER_EXPLANATIONS = {
    "Obelisk.log": "copied Obelisk.log is missing from the lifecycle evidence run",
    "window-manifest.env": "window-manifest.env is missing or unavailable",
    "preflight-post.json": "preflight-post.json is missing or unavailable",
    APPROVED_RUNTIME_EVIDENCE_JSON: (
        "approved runtime principal lifecycle evidence JSON is missing"
    ),
}
RUNNER_BOUNDARIES_SCHEMA = (
    "obelisk.player-principal-lifecycle-next-action-runner-boundaries.v1"
)
RUNNER_SOURCE_ROOT_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-next-action-source-root-boundary.v1"
)
RUNNER_STANDING_AUTHORITY_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-runner-standing-authority-boundary.v1"
)
RUNNER_CHECKER_REPLAY_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-runner-checker-replay-boundary.v1"
)
COMMAND_PATH_BINDING_SCHEMA = (
    "obelisk.player-principal-lifecycle-command-path-binding.v1"
)
RUN_ID_TEXT_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[A-Za-z0-9_.-]+")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PASSIVE_MONITOR_ROOT_RE = re.compile(
    r"(?:passive(?:[_ .:-]?monitor)?|monitor|post[_ .:-]?reboot|postpatch|"
    r"no[_ .:-]?(?:users?|testers?)|wait[_ .:-]?only)",
    re.IGNORECASE,
)
STALE_SOURCE_ROOT_RE = re.compile(
    r"(?:stale|historical|previous|prior|old[_ .:-]?window|postpatch)",
    re.IGNORECASE,
)
RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-stale-prevention.v1"
)
BETA_RUNTIME_CHOREOGRAPHY_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-runtime-choreography.v1"
)
CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-checkjoin-stimulus-boundary.v1"
)
PLAYER_PRINCIPAL_EVIDENCE_SPLIT_RUNNER_SCHEMA = (
    "obelisk.player-principal-lifecycle-evidence-split-runner.v1"
)
BOUND_RUNTIME_EVIDENCE_HELPER_SCRIPTS = {
    "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
    "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
}
MIN_RUNTIME_WINDOW_LEAD_SECONDS = 300
STANDING_AUTHORITY_SOURCES = {
    "recorded_standing_debug_authority",
    "recorded_standing_launch_authority",
    "standing_launch_authority",
}
FRESH_OPERATOR_AUTHORITY_SOURCES = {
    "fresh_current_turn_operator_message",
    "fresh_current_turn_operator_scope",
}
SPLIT_CLAIM_NAME_KEYS = {"alias", "claim", "field", "flag", "key", "name", "property"}
SPLIT_CLAIM_VALUE_KEYS = {
    "allowed",
    "classification",
    "enabled",
    "label",
    "ready",
    "result",
    "state",
    "status",
    "support",
    "tier",
    "value",
}
SPLIT_POSITIVE_VALUE_TOKENS = {
    "accepted",
    "allowed",
    "approved",
    "authorized",
    "complete",
    "completed",
    "enabled",
    "present",
    "ready",
    "supported",
    "true",
    "unlocked",
    "yes",
}
SPLIT_NEGATIVE_VALUE_TOKENS = {
    "blocked",
    "candidate",
    "false",
    "missing",
    "no",
    "non",
    "none",
    "not",
    "only",
    "rejected",
    "required",
    "requires",
    "unsupported",
}
SPLIT_FORBIDDEN_CLAIM_TOKENS = {
    "approved",
    "authorize",
    "authorized",
    "authorizes",
    "complete",
    "completion",
    "evidence",
    "progress",
    "public",
    "ready",
    "readiness",
    "runtime",
    "sdk",
    "stable",
    "v1",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-json", required=True, type=Path)
    parser.add_argument("--execute", action="store_true", help="Execute eligible actions.")
    parser.add_argument(
        "--allow-evidence-dir-writes",
        action="store_true",
        help="Allow eligible actions that write under approved evidence directories.",
    )
    parser.add_argument("--action-id", action="append", help="Limit to one or more action ids.")
    parser.add_argument("--json-output", type=Path, help="Optional output file. Use '-' for stdout.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def normalized_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def nested_dict(value: Any, *keys: str) -> dict[str, Any]:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def approved_window_from_run_id(run_id: str | None) -> dict[str, Any] | None:
    # Run ids encode only the window start. The approved duration must be supplied by
    # explicit approved_window metadata because passive windows are bounded from
    # 900 to 7200 seconds.
    return None


def action_approved_window(
    action: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any] | None:
    for candidate in (
        action.get("approved_window"),
        nested_dict(action, "runtime_window_stale_prevention", "approved_window"),
        nested_dict(action, "runner_contract", "approved_window"),
        nested_dict(action, "beta_notice_sequence_enforcement", "approved_window"),
        plan.get("approved_window"),
        nested_dict(plan, "runtime_window_stale_prevention", "approved_window"),
    ):
        if isinstance(candidate, dict):
            start = candidate.get("start_utc")
            end = candidate.get("end_utc")
            if isinstance(start, str) and isinstance(end, str):
                return {
                    "start_utc": start,
                    "end_utc": end,
                    **{
                        key: value
                        for key, value in candidate.items()
                        if key not in {"start_utc", "end_utc"}
                    },
                }
    return approved_window_from_run_id(
        action.get("run_id") if isinstance(action.get("run_id"), str) else plan.get("run_id")
    )


def action_requires_current_runtime_window(
    action: dict[str, Any],
    argv: list[str] | None,
) -> bool:
    if action.get("action_kind") in {
        "expired_runtime_window_non_evidence_closure",
        "active_runtime_window_waiting_for_exact_triplet",
    }:
        return False
    text_parts = [
        action.get("id"),
        action.get("action"),
        action.get("action_kind"),
        action.get("phase"),
        action.get("side_effect_domain"),
        action.get("command_text_not_executed"),
        nested_dict(action, "runner_contract").get("phase"),
        nested_dict(action, "runner_contract").get("operation_kind"),
        nested_dict(action, "runner_contract").get("side_effect_domain"),
        nested_dict(action, "runner_operation").get("kind"),
    ]
    if argv:
        text_parts.extend(argv)
    text = " ".join(str(part) for part in text_parts if isinstance(part, str)).casefold()
    terms = (
        "active_observation",
        "activation_precondition",
        "confirmed_beta_notice",
        "guarded_beta_notice",
        "marker_env_runtime_observation",
        "monitor_ark_player_presence_passive",
        "player_presence_restart_safety",
        "runtime_window",
        "safe_restart",
    )
    return any(term in text for term in terms)


def runtime_window_stale_prevention_for_action(
    action: dict[str, Any],
    plan: dict[str, Any],
    argv: list[str] | None,
) -> dict[str, Any]:
    applies = action_requires_current_runtime_window(action, argv)
    window = action_approved_window(action, plan)
    if window is None:
        blockers = ["runtime_window_approved_window_missing_for_action"] if applies else []
        return {
            "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
            "applies_to_action": applies,
            "approved_window": None,
            "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "enough_future_lead_time": False,
            "window_start_in_future": False,
            "window_end_in_future": False,
            "stale_request_window": applies,
            "request_window_stale_or_too_late": bool(blockers),
            "blockers": blockers,
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        }
    start = parse_utc(window.get("start_utc"))
    end = parse_utc(window.get("end_utc"))
    if start is None or end is None:
        blockers = ["runtime_window_approved_window_time_invalid_for_action"] if applies else []
        return {
            "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
            "applies_to_action": applies,
            "approved_window": window,
            "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "enough_future_lead_time": False,
            "window_start_in_future": False,
            "window_end_in_future": False,
            "stale_request_window": applies,
            "request_window_stale_or_too_late": bool(blockers),
            "blockers": blockers,
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        }
    now = datetime.now(timezone.utc).replace(microsecond=0)
    seconds_until_start = int((start - now).total_seconds())
    seconds_until_end = int((end - now).total_seconds())
    enough_lead = seconds_until_start >= MIN_RUNTIME_WINDOW_LEAD_SECONDS
    blockers: list[str] = []
    if start <= now:
        blockers.append("runtime_window_start_already_passed_prepare_fresh_window")
    if end <= now:
        blockers.append("runtime_window_end_already_passed_prepare_fresh_window")
    if start > now and not enough_lead:
        blockers.append("runtime_window_insufficient_future_lead_for_notice_and_activation")
    action_blockers = blockers if applies else []
    return {
        "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
        "applies_to_action": applies,
        "checked_at_utc": format_utc(now),
        "approved_window": window,
        "start_utc": format_utc(start),
        "end_utc": format_utc(end),
        "seconds_until_start": seconds_until_start,
        "seconds_until_end": seconds_until_end,
        "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
        "enough_future_lead_time": enough_lead,
        "window_start_in_future": start > now,
        "window_end_in_future": end > now,
        "stale_request_window": bool(action_blockers and (start <= now or end <= now)),
        "request_window_stale_or_too_late": bool(action_blockers),
        "blockers": action_blockers,
        "beta_notice_dry_run_required_before_activation": True,
        "confirmed_beta_notice_required_before_activation": True,
        "confirmed_send_must_complete_before_window_start": True,
        "activation_preconditions_required_before_activation_or_restart": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "fresh_current_window_required_when_blocked": bool(action_blockers),
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


NORMALIZED_FORBIDDEN_TRUE_KEYS = {normalized_key(key) for key in FORBIDDEN_TRUE_KEYS}
NORMALIZED_FORBIDDEN_PROGRESS_KEYS = {
    normalized_key(key) for key in FORBIDDEN_PROGRESS_KEYS
}


def positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        tokens = {token for token in re.split(r"[^A-Za-z0-9]+", value.casefold()) if token}
        if tokens & {"false", "missing", "no", "non", "none", "not", "only", "required"}:
            return False
        return bool(tokens & {"accepted", "approved", "authorized", "complete", "ready", "true", "yes"})
    if isinstance(value, dict):
        return any(positive_claim_value(child) for child in value.values())
    if isinstance(value, list):
        return any(positive_claim_value(child) for child in value)
    return False


def zero_progress_value(value: Any) -> bool:
    if value in (0, 0.0):
        return True
    if isinstance(value, str):
        return value.strip().casefold() in {
            "0",
            "0.0",
            "0/4",
            "0/12",
            "false",
            "no",
            "none",
            "not_applicable",
        }
    return False


def collect_claim_aliases(value: Any, trail: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}" if trail != "$" else f"$.{key}"
            if normalized_key(key) in NORMALIZED_FORBIDDEN_TRUE_KEYS and positive_claim_value(child):
                matches.append(child_trail)
            if (
                normalized_key(key) in NORMALIZED_FORBIDDEN_PROGRESS_KEYS
                and not zero_progress_value(child)
            ):
                matches.append(child_trail)
            matches.extend(collect_claim_aliases(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(collect_claim_aliases(child, f"{trail}[{index}]"))
    return matches


def offline_parallel_lane_misconfiguration_paths(
    value: Any,
    trail: str = "$.offline_parallel_evidence_lanes",
) -> list[str]:
    if not isinstance(value, dict) or value.get("present") is not True:
        return []
    paths: list[str] = []
    if value.get("runner_command_available") is not False:
        paths.append(f"{trail}.runner_command_available")
    if value.get("runner_must_not_execute_lanes") is not True:
        paths.append(f"{trail}.runner_must_not_execute_lanes")
    for key in (
        "approved_runtime_evidence",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "counts_toward_sdk",
        "counts_toward_p0_dependency_chain",
        "runtime_ready",
        "public_sdk_ready",
        "stable_claim_allowed",
    ):
        if value.get(key) is not False:
            paths.append(f"{trail}.{key}")
    for key in ("sdk_progress", "p0_progress", "runtime_progress"):
        if not zero_progress_value(value.get(key, 0)):
            paths.append(f"{trail}.{key}")
    lanes = value.get("lanes")
    if not isinstance(lanes, list):
        paths.append(f"{trail}.lanes")
        return paths
    for index, lane in enumerate(lanes):
        lane_trail = f"{trail}.lanes[{index}]"
        if not isinstance(lane, dict):
            paths.append(lane_trail)
            continue
        if not isinstance(lane.get("id"), str):
            paths.append(f"{lane_trail}.id")
        if lane.get("runner_command_available") is not False:
            paths.append(f"{lane_trail}.runner_command_available")
        if lane.get("runner_must_not_execute_lane") is not True:
            paths.append(f"{lane_trail}.runner_must_not_execute_lane")
        for key in (
            "counts_as_approved_runtime_evidence",
            "counts_as_runtime_evidence",
            "counts_as_sdk_evidence",
            "counts_toward_sdk",
            "counts_toward_p0_dependency_chain",
            "runtime_ready",
            "public_sdk_ready",
            "stable_claim_allowed",
        ):
            if lane.get(key) is not False:
                paths.append(f"{lane_trail}.{key}")
        for key in ("sdk_progress", "p0_progress", "runtime_progress"):
            if not zero_progress_value(lane.get(key, 0)):
                paths.append(f"{lane_trail}.{key}")
    return paths


def reject_protected_input(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    return protected_paths.reject_protected_input_path(
        path.expanduser(),
        label,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )


def reject_protected_output(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    return protected_paths.reject_protected_output_path(
        path.expanduser(),
        label,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )


def load_plan(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = reject_protected_input(path, "--plan-json")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("--plan-json must contain a JSON object")
    if payload.get("schema") != PLAN_SCHEMA:
        raise SystemExit(f"--plan-json schema mismatch: {payload.get('schema')!r}")
    aliases = collect_claim_aliases(payload)
    if aliases:
        raise SystemExit(
            "--plan-json contains positive runtime/readiness shortcut aliases: "
            + ", ".join(aliases[:8])
        )
    return resolved, payload


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def current_live_diagnostic_blockers_context() -> dict[str, Any]:
    false_claims = {
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "live_ops_authorized": False,
        "reads_live_logs": False,
        "discord_authorized": False,
        "publication_authorized": False,
        "sdk_progress": 0,
        "p0_progress": 0,
        "runtime_progress": 0,
    }
    source_bound_non_actions = {
        "source_bound_blocker": True,
        "route_to_drift_or_source_bound_blocker": True,
        "blind_wait_recommended": False,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "wait_or_restart_or_logout_instruction_allowed": False,
        "logout_or_reconnect_instruction_allowed": False,
        "player_logout_instruction_allowed_now": False,
        "runner_action_allowed": False,
        "accepted_events_required_before_progress": True,
    }
    blockers = [
        {
            "id": "theisland_active_player_observer_only_no_accepted_lifecycle_event",
            "blocker": "active_player_observer_only_no_accepted_lifecycle_event",
            "source_bound_blocker_kind": (
                "active_player_observer_enabled_no_accepted_lifecycle_events"
            ),
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            "player_count_current": 1,
            "players_detected": True,
            "observer_enabled": True,
            "observer_only": True,
            "accepted_lifecycle_event_count": 0,
            "accepted_lifecycle_roles": [],
            "next_status_input_needed": (
                "source-bound drift resolution or same-window accepted lifecycle "
                "event triplet after the source blocker clears; otherwise "
                "window-end non-evidence classification"
            ),
            **source_bound_non_actions,
            **false_claims,
        },
        {
            "id": "ragnarok_diagnostic_fname_drift_blocks_accepted_events",
            "blocker": "diagnostic_fname_drift_blocks_accepted_events",
            "source_bound_blocker_kind": "diagnostic_fname_drift",
            "target": {"instance": "arkserver", "map": "Ragnarok"},
            "diagnostic_fname_mismatch_lines_present": True,
            "diagnostic_fname_drift": True,
            "accepted_lifecycle_event_count": 0,
            "accepted_lifecycle_roles": [],
            "next_status_input_needed": (
                "resolve or avoid diagnostic FName drift before treating lifecycle "
                "lines as accepted copied observer events"
            ),
            **source_bound_non_actions,
            **false_claims,
        },
    ]
    return {
        "schema": CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA,
        "status": "blocked_approved_runtime_evidence_missing",
        "classification": "source_bound_drift_blockers_non_evidence",
        "source": "operator_supplied_current_redacted_state",
        "source_freshness": "stale_operator_supplied",
        "stale_operator_supplied_context": True,
        "stale_operator_supplied_blockers_suppressed": True,
        "planner_did_not_read_live_logs": True,
        "status_report_only": True,
        "blocker_context_only": True,
        "diagnostic_non_evidence": True,
        "source_bound_blocker": True,
        "route_to_drift_or_source_bound_blocker": True,
        "current_source_bound_route_blocker": "source_bound_drift_blocks_accepted_lifecycle_events",
        "blind_wait_recommended": False,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "wait_or_restart_or_logout_instruction_allowed": False,
        "logout_or_reconnect_instruction_allowed": False,
        "player_logout_instruction_allowed_now": False,
        "runner_action_allowed": False,
        "active_ark_server_count": 2,
        "active_server_targets": [
            {"instance": "arkserver2", "map": "TheIsland"},
            {"instance": "arkserver", "map": "Ragnarok"},
        ],
        "inactive_or_unknown_targets": [
            {
                "instance": "arkserver3",
                "map": "Genesis2",
                "state": "inactive_or_unknown",
                "counted_in_active_ark_server_count": False,
            }
        ],
        "current_route_blocker": "approved_runtime_evidence_missing",
        "next_blockers": blockers,
        "next_blocker_ids": [str(blocker["id"]) for blocker in blockers],
        "stale_operator_supplied_next_blockers": blockers,
        "stale_operator_supplied_next_blocker_ids": [
            str(blocker["id"]) for blocker in blockers
        ],
        "primary_next_blocker": blockers[0]["blocker"],
        "secondary_next_blocker": blockers[1]["blocker"],
        "approved_runtime_evidence_unlocks_after": (
            "checker-accepted copied runtime principal lifecycle evidence bundle"
        ),
        "non_claim": (
            "Current redacted live state is blocker context only and does not "
            "authorize runner execution or add SDK/P0 progress."
        ),
        **source_bound_non_actions,
        **false_claims,
    }


def plan_current_live_diagnostic_blockers(plan: dict[str, Any]) -> dict[str, Any]:
    context = plan.get("current_live_diagnostic_blockers")
    if not isinstance(context, dict):
        context = nested_dict(plan, "action_plan", "current_live_diagnostic_blockers")
    if not isinstance(context, dict):
        return current_live_diagnostic_blockers_context()
    normalized = {**current_live_diagnostic_blockers_context(), **context}
    normalized.update(
        {
            "schema": CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA,
            "status_report_only": True,
            "blocker_context_only": True,
            "diagnostic_non_evidence": True,
            "source_bound_blocker": True,
            "route_to_drift_or_source_bound_blocker": True,
            "current_source_bound_route_blocker": "source_bound_drift_blocks_accepted_lifecycle_events",
            "blind_wait_recommended": False,
            "restart_recommended": False,
            "start_or_restart_recommended": False,
            "wait_or_restart_or_logout_instruction_allowed": False,
            "logout_or_reconnect_instruction_allowed": False,
            "player_logout_instruction_allowed_now": False,
            "runner_action_allowed": False,
            "active_ark_server_count": 2,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "sdk_progress": 0,
            "p0_progress": 0,
        }
    )
    return normalized


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
        "non_authorization": NON_AUTHORIZATION,
    }


def default_beta_runtime_choreography(target: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": BETA_RUNTIME_CHOREOGRAPHY_SCHEMA,
        "classification": "single_tester_direct_join_choreography_non_authorizing",
        "target": target,
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
            "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
            "required_copied_bool_values": ["1", "0"],
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
        "source_bound_blockers_must_be_clear_before_choreography": True,
        "choreography_is_candidate_only_until_source_bound_blockers_clear": True,
        "blind_wait_instruction": False,
        "logout_instruction_allowed_now": False,
        "choreography_authorizes_discord": False,
        "choreography_authorizes_runtime_capture": False,
        "choreography_authorizes_server_operations": False,
        "choreography_authorizes_runner": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def beta_runtime_choreography_for_action(
    action: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    action_choreography = action.get("beta_runtime_choreography")
    if isinstance(action_choreography, dict):
        return {
            **action_choreography,
            "source_bound_blockers_must_be_clear_before_choreography": True,
            "choreography_is_candidate_only_until_source_bound_blockers_clear": True,
            "blind_wait_instruction": False,
            "logout_instruction_allowed_now": False,
            "choreography_authorizes_runner": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": action_choreography.get("non_authorization", NON_AUTHORIZATION),
        }
    plan_choreography = plan.get("beta_runtime_choreography")
    if isinstance(plan_choreography, dict):
        return {
            **plan_choreography,
            "source_bound_blockers_must_be_clear_before_choreography": True,
            "choreography_is_candidate_only_until_source_bound_blockers_clear": True,
            "blind_wait_instruction": False,
            "logout_instruction_allowed_now": False,
            "choreography_authorizes_runner": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": plan_choreography.get("non_authorization", NON_AUTHORIZATION),
        }
    target = action.get("target") if isinstance(action.get("target"), dict) else None
    return default_beta_runtime_choreography(target)


def dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def split_alias_tokens(value: object) -> set[str]:
    return {token for token in normalized_key(value).split("_") if token}


def split_alias_value_is_positive(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        tokens = split_alias_tokens(value)
        if tokens & SPLIT_NEGATIVE_VALUE_TOKENS:
            return False
        return bool(tokens & SPLIT_POSITIVE_VALUE_TOKENS)
    if isinstance(value, dict):
        return any(split_alias_value_is_positive(child) for child in value.values())
    if isinstance(value, list):
        return any(split_alias_value_is_positive(child) for child in value)
    return False


def split_alias_claim_paths(value: Any, trail: str = "$") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        names = [
            child
            for key, child in value.items()
            if normalized_key(key) in SPLIT_CLAIM_NAME_KEYS and isinstance(child, str)
        ]
        values = [
            child
            for key, child in value.items()
            if normalized_key(key) in SPLIT_CLAIM_VALUE_KEYS
        ]
        positive_value_present = not values or any(
            split_alias_value_is_positive(child) for child in values
        )
        if names and positive_value_present:
            for name in names:
                if split_alias_tokens(name) & SPLIT_FORBIDDEN_CLAIM_TOKENS:
                    paths.append(trail)
                    break
        for key, child in value.items():
            child_trail = f"{trail}.{key}" if trail != "$" else f"$.{key}"
            paths.extend(split_alias_claim_paths(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(split_alias_claim_paths(child, f"{trail}[{index}]"))
    return sorted(set(paths))


def normalized_player_principal_evidence_split(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "schema": PLAYER_PRINCIPAL_EVIDENCE_SPLIT_RUNNER_SCHEMA,
            "present": False,
            "classification": "no_player_principal_evidence_split_context",
            "runner_accepts_split_as_evidence": False,
            "split_authorizes_runner": False,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
        }
    positive_alias_paths = split_alias_claim_paths(value)
    blockers = string_list(value.get("blockers"))
    if positive_alias_paths:
        blockers.append("player_principal_evidence_split_positive_alias_claim")
    return {
        "schema": PLAYER_PRINCIPAL_EVIDENCE_SPLIT_RUNNER_SCHEMA,
        "present": True,
        "classification": value.get("classification")
        if isinstance(value.get("classification"), str)
        else "player_principal_evidence_split_context_non_evidence",
        "source_schema": value.get("source_schema") or value.get("schema"),
        "source_status": value.get("source_status") or value.get("status"),
        "start_end_contract_input_present": (
            value.get("start_end_contract_input_present") is True
        ),
        "start_end_contract_input_accepted": (
            value.get("start_end_contract_input_accepted") is True
        ),
        "session_start_rejected_required": (
            value.get("session_start_rejected_required") is not False
        ),
        "session_start_rejected_missing": (
            value.get("session_start_rejected_missing") is not False
        ),
        "strict_approved_runtime_evidence_bundle_required": (
            value.get("strict_approved_runtime_evidence_bundle_required") is not False
        ),
        "strict_approved_runtime_evidence_bundle_missing": (
            value.get("strict_approved_runtime_evidence_bundle_missing") is not False
        ),
        "positive_alias_claim_paths": positive_alias_paths,
        "blockers": sorted(set(blockers)),
        "next_actions": dict_list(value.get("next_actions")),
        "components": value.get("components") if isinstance(value.get("components"), dict) else {},
        "runner_accepts_split_as_evidence": False,
        "runner_accepts_start_end_as_approved_runtime_evidence": False,
        "split_authorizes_runner": False,
        "split_authorizes_runtime_capture": False,
        "split_counts_as_approved_runtime_evidence": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "sdk_progress": 0,
        "p0_progress": 0,
        "non_authorization": NON_AUTHORIZATION,
    }


def player_principal_evidence_split_for_action(
    action: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    for candidate in (
        action.get("player_principal_evidence_split"),
        action.get("player_principal_lifecycle_evidence_split"),
        action.get("evidence_split"),
        plan.get("player_principal_evidence_split"),
        plan.get("player_principal_lifecycle_evidence_split"),
        nested_dict(plan, "action_plan", "player_principal_evidence_split"),
    ):
        if isinstance(candidate, dict) and candidate:
            return normalized_player_principal_evidence_split(candidate)
    if str(action.get("action_kind") or "").startswith("player_principal_evidence_split"):
        return normalized_player_principal_evidence_split(
            {
                "classification": "player_principal_evidence_split_action_without_context",
                "next_actions": [action],
            }
        )
    return normalized_player_principal_evidence_split(None)


def selected_actions(plan: dict[str, Any], action_ids: list[str] | None) -> list[dict[str, Any]]:
    actions = plan.get("next_action_sequence")
    if not isinstance(actions, list):
        return []
    output = [action for action in actions if isinstance(action, dict)]
    if action_ids:
        wanted = set(action_ids)
        output = [action for action in output if action.get("id") in wanted]
    return output


def path_under_server_root(path: Path) -> bool:
    expanded = path.expanduser()
    try:
        if expanded.is_absolute() and protected_paths.is_under_path(expanded, SERVER_ROOT):
            return True
        return protected_paths.is_under_path(expanded.resolve(), SERVER_ROOT.resolve())
    except OSError:
        return False


def token_path_under_server_root(token: str) -> Path | None:
    if not (token.startswith("/") or token.startswith("~")):
        return None
    path = Path(token)
    if path_under_server_root(path):
        return path.expanduser().resolve()
    return None


def validate_offline_runner_argv(argv: list[str], *, structured: bool) -> list[str]:
    blockers: list[str] = []
    if not argv:
        return ["command_argv_empty"]
    script = argv[0]
    if structured and any(any(marker in token for marker in STRUCTURED_ARGV_SHELL_TOKENS) for token in argv):
        blockers.append("structured_runner_command_shell_token_blocked")
    if structured and Path(script).name in SHELL_EXECUTABLE_NAMES:
        blockers.append("structured_runner_command_shell_executable_blocked")
    if not SAFE_REPO_SCRIPT_RE.fullmatch(script):
        return [*blockers, "command_not_allowlisted_repo_script"]
    script_blocker = LIVE_OPERATION_SCRIPT_BLOCKERS.get(script)
    if script_blocker:
        blockers.append(script_blocker)
    elif script not in OFFLINE_RUNNER_ALLOWED_SCRIPTS:
        blockers.append(f"command_not_offline_runner_allowlisted:{script}")
    for token in argv:
        flag_blocker = LIVE_OR_PRIVILEGED_FLAGS.get(token)
        if flag_blocker:
            blockers.append(flag_blocker)
        server_path = token_path_under_server_root(token)
        if server_path is not None:
            blockers.append(f"argv_references_forbidden_server_root:{server_path}")
    return blockers


def command_from_action(action: dict[str, Any]) -> tuple[list[str] | None, str | None, list[str]]:
    blockers: list[str] = []
    runner_command = action.get("runner_command")
    if isinstance(runner_command, dict) and isinstance(runner_command.get("argv"), list):
        if any(not isinstance(item, str) for item in runner_command["argv"]):
            blockers.append("structured_runner_command_non_string_arg_blocked")
        argv = [item for item in runner_command["argv"] if isinstance(item, str)]
        if argv:
            blockers.extend(validate_offline_runner_argv(argv, structured=True))
            return (
                argv,
                runner_command.get("redirect_stdout")
                if isinstance(runner_command.get("redirect_stdout"), str)
                else None,
                blockers,
            )
    command_text = action.get("command_text_not_executed")
    if not isinstance(command_text, str) or not command_text.strip():
        return None, None, ["command_metadata_missing"]
    if any(token in command_text for token in ("|", ";", "&&", "||", "`", "$(")):
        return None, None, ["unstructured_shell_command_blocked"]
    try:
        tokens = shlex.split(command_text)
    except ValueError as exc:
        return None, None, [f"command_parse_failed:{exc}"]
    if not tokens:
        return None, None, ["command_argv_empty"]
    if any("<" in token for token in tokens):
        return None, None, ["placeholder_or_stdin_redirection_command_blocked"]
    redirect_stdout: str | None = None
    redirection_tokens = [token for token in tokens if ">" in token]
    if redirection_tokens:
        if redirection_tokens != [">"]:
            return None, None, ["unsafe_or_compound_redirection_command_blocked"]
        redirect_index = tokens.index(">")
        if redirect_index == 0 or redirect_index + 2 != len(tokens):
            return None, None, ["unsafe_or_compound_redirection_command_blocked"]
        redirect_stdout = tokens[redirect_index + 1]
        argv = tokens[:redirect_index]
    else:
        argv = tokens
    if not argv:
        return None, None, ["command_argv_empty"]
    blockers.extend(validate_offline_runner_argv(argv, structured=False))
    return argv, redirect_stdout, blockers


def existing_path_for_flag(argv: list[str], flag: str) -> Path | None:
    try:
        index = argv.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(argv):
        return Path("<missing-flag-value>")
    return Path(argv[index + 1])


def missing_required_inputs(argv: list[str]) -> list[str]:
    missing: list[str] = []
    for flag in INPUT_FLAGS:
        path = existing_path_for_flag(argv, flag)
        if path is None:
            continue
        if str(path) == "<missing-flag-value>":
            missing.append(f"{flag}:missing_value")
            continue
        if path_under_server_root(path):
            missing.append(f"{flag}_under_forbidden_server_root:{path.expanduser().resolve()}")
            continue
        if not path.exists():
            missing.append(f"{flag}:{path}")
    return missing


def action_evidence_dir(action: dict[str, Any], argv: list[str] | None) -> Path | None:
    for key in ("evidence_dir", "copied_evidence_dir"):
        value = action.get(key)
        if isinstance(value, str) and value:
            return Path(value)
    if argv is None:
        return None
    copied_log = existing_path_for_flag(argv, "--copied-log")
    if copied_log is not None and copied_log.name == "Obelisk.log":
        return copied_log.parent
    evidence_dir = existing_path_for_flag(argv, "--evidence-dir")
    if evidence_dir is not None:
        return evidence_dir
    manifest = existing_path_for_flag(argv, "--window-manifest")
    if manifest is not None and manifest.name == "window-manifest.env":
        return manifest.parent
    post_replay = existing_path_for_flag(argv, "--post-window-replay")
    if post_replay is not None and post_replay.name == "window-manifest.env":
        return post_replay.parent
    output_dir = existing_path_for_flag(argv, "--output-dir")
    if output_dir is not None and output_dir.name == "approved-bundle":
        return output_dir.parent
    return None


def relative_artifact_path(value: str) -> Path | None:
    if value in KNOWN_CLOSURE_ARTIFACTS or "/" in value or Path(value).suffix:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            return None
        return path
    return None


def blocked_until_blockers(
    action: dict[str, Any],
    argv: list[str] | None,
) -> tuple[list[str], list[str]]:
    items = string_list(action.get("blocked_until"))
    if not items:
        return [], []
    evidence_dir = action_evidence_dir(action, argv)
    blockers: list[str] = []
    missing: list[str] = []
    unresolved: list[str] = []
    for item in items:
        if item.startswith("lifecycle-role/"):
            continue
        relative = relative_artifact_path(item)
        if relative is None:
            unresolved.append(item)
            continue
        if evidence_dir is None:
            unresolved.append(item)
            continue
        path = evidence_dir / relative
        if path_under_server_root(path):
            blockers.append(f"blocked_until_under_forbidden_server_root:{item}:{path.expanduser().resolve()}")
            continue
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
        if status.protected:
            blockers.append(f"blocked_until_under_protected_server_root:{item}:{status.resolved}")
        elif not status.resolved.exists():
            missing.append(item)
    if unresolved:
        blockers.append("blocked_until_unresolved:" + ",".join(unresolved))
    blockers.extend(f"blocked_until_missing:{item}" for item in missing)
    return blockers, missing


def dry_run_first_required(action: dict[str, Any]) -> bool:
    return (
        action.get("dry_run_first_required") is True
        or action.get("dry_run_must_complete_before_execute") is True
    )


def dry_run_artifact_paths(action: dict[str, Any]) -> list[str]:
    paths = string_list(action.get("required_dry_run_artifacts"))
    dry_run_report = action.get("dry_run_report_path")
    if isinstance(dry_run_report, str) and dry_run_report and dry_run_report not in paths:
        paths.append(dry_run_report)
    return paths


def resolve_action_relative_path(action: dict[str, Any], argv: list[str] | None, value: str) -> Path | None:
    path = Path(value)
    if path.is_absolute():
        return path
    if ".." in path.parts:
        return None
    evidence_dir = action_evidence_dir(action, argv)
    if evidence_dir is None:
        return None
    return evidence_dir / path


def dry_run_first_blockers(
    action: dict[str, Any],
    argv: list[str] | None,
    *,
    execute_requested: bool,
) -> tuple[list[str], list[str]]:
    if not execute_requested or not dry_run_first_required(action):
        return [], []
    artifact_values = dry_run_artifact_paths(action)
    if not artifact_values:
        return ["dry_run_first_required_artifact_unspecified"], []
    blockers: list[str] = []
    missing: list[str] = []
    for value in artifact_values:
        path = resolve_action_relative_path(action, argv, value)
        if path is None:
            blockers.append(f"dry_run_first_required_artifact_unresolved:{value}")
            continue
        if path_under_server_root(path):
            blockers.append(
                "dry_run_first_required_artifact_under_forbidden_server_root:"
                f"{path.expanduser().resolve()}"
            )
            continue
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
        if status.protected:
            blockers.append(
                "dry_run_first_required_artifact_under_protected_server_root:"
                f"{status.resolved}"
            )
        elif not status.resolved.exists():
            missing.append(str(path))
    blockers.extend(f"dry_run_first_required_artifact_missing:{path}" for path in missing)
    return blockers, missing


def output_paths(argv: list[str], redirect_stdout: str | None) -> list[Path]:
    paths: list[Path] = []
    if redirect_stdout:
        paths.append(Path(redirect_stdout))
    for flag in OUTPUT_FLAGS:
        path = existing_path_for_flag(argv, flag)
        if path is not None and str(path) != "<missing-flag-value>":
            paths.append(path)
    return paths


def missing_output_values(argv: list[str]) -> list[str]:
    missing: list[str] = []
    for flag in OUTPUT_FLAGS:
        path = existing_path_for_flag(argv, flag)
        if path is not None and str(path) == "<missing-flag-value>":
            missing.append(f"{flag}:missing_value")
    return missing


def output_write_blockers(paths: list[Path], allow_evidence_dir_writes: bool) -> list[str]:
    blockers: list[str] = []
    for path in paths:
        if path_under_server_root(path):
            blockers.append(f"output_under_forbidden_server_root:{path.expanduser().resolve()}")
            continue
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
        if status.protected:
            blockers.append(f"output_under_protected_server_root:{status.resolved}")
        elif status.approved_offline_workspace and not allow_evidence_dir_writes:
            blockers.append(f"evidence_dir_write_requires_explicit_flag:{status.resolved}")
    return blockers


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    return Path(value)


def argv_path_for_binding(
    artifact: dict[str, Any],
    argv: list[str],
    redirect_stdout: str | None,
) -> tuple[Path | None, list[str]]:
    blockers: list[str] = []
    if artifact.get("redirect_stdout") is True:
        if redirect_stdout is None:
            blockers.append("command_path_binding_redirect_stdout_missing")
        else:
            return Path(redirect_stdout), blockers
    flags = string_list(artifact.get("argv_flags"))
    for flag in flags:
        observed = existing_path_for_flag(argv, flag)
        if observed is None:
            blockers.append(f"command_path_binding_flag_missing:{flag}")
            continue
        if str(observed) == "<missing-flag-value>":
            blockers.append(f"command_path_binding_flag_value_missing:{flag}")
            continue
        return observed, blockers
    position = artifact.get("argv_position")
    if isinstance(position, int):
        if position < 0 or position >= len(argv):
            blockers.append(f"command_path_binding_argv_position_missing:{position}")
        else:
            return Path(argv[position]), blockers
    return None, blockers


def command_path_binding_blockers(
    action: dict[str, Any],
    argv: list[str] | None,
    redirect_stdout: str | None,
) -> list[str]:
    binding = action.get("command_path_binding")
    blockers: list[str] = []
    script = argv[0] if argv else None
    if script in BOUND_RUNTIME_EVIDENCE_HELPER_SCRIPTS and not isinstance(binding, dict):
        blockers.append("command_path_binding_required_for_runtime_evidence_helper")
        return blockers
    if not isinstance(binding, dict):
        return blockers
    if argv is None:
        return ["command_path_binding_without_command_argv"]
    if binding.get("schema") != COMMAND_PATH_BINDING_SCHEMA:
        blockers.append("command_path_binding_schema_mismatch")
    for collection_key in ("inputs", "outputs"):
        collection = binding.get(collection_key)
        if collection is None:
            continue
        if not isinstance(collection, list):
            blockers.append(f"command_path_binding_{collection_key}_not_list")
            continue
        for index, artifact in enumerate(collection):
            if not isinstance(artifact, dict):
                blockers.append(f"command_path_binding_{collection_key}_{index}_not_object")
                continue
            declared_path = binding_path(artifact.get("path"))
            label = str(artifact.get("relative_path") or artifact.get("path") or f"{collection_key}[{index}]")
            if declared_path is None:
                blockers.append(f"command_path_binding_path_missing:{label}")
                continue
            symlink = protected_paths.first_symlink_component(declared_path)
            if symlink is not None:
                blockers.append(f"command_path_binding_symlink_component:{label}:{symlink}")
                continue
            if path_under_server_root(declared_path):
                blockers.append(
                    f"command_path_binding_under_forbidden_server_root:{label}:{declared_path.expanduser().resolve()}"
                )
                continue
            argv_path, argv_blockers = argv_path_for_binding(artifact, argv, redirect_stdout)
            blockers.extend(f"{blocker}:{label}" for blocker in argv_blockers)
            if argv_path is not None:
                if path_under_server_root(argv_path):
                    blockers.append(
                        f"command_path_binding_argv_under_forbidden_server_root:{label}:{argv_path.expanduser().resolve()}"
                    )
                    continue
                if argv_path.expanduser().resolve() != declared_path.expanduser().resolve():
                    blockers.append(
                        "command_path_binding_argv_path_mismatch:"
                        f"{label}:{declared_path.expanduser().resolve()}:{argv_path.expanduser().resolve()}"
                    )
                    continue
            role = str(artifact.get("role") or "")
            expects_dir = role.endswith("_dir")
            must_exist = artifact.get("must_exist")
            if must_exist is None:
                must_exist = collection_key == "inputs"
            exists = declared_path.is_dir() if expects_dir else declared_path.is_file()
            if must_exist is True and not exists:
                blockers.append(f"command_path_binding_required_path_missing:{label}:{declared_path}")
                continue
            expected_sha = artifact.get("sha256")
            if expected_sha is None:
                continue
            if not isinstance(expected_sha, str) or SHA256_RE.fullmatch(expected_sha) is None:
                blockers.append(f"command_path_binding_sha256_invalid:{label}")
                continue
            if expects_dir:
                blockers.append(f"command_path_binding_sha256_on_directory:{label}")
                continue
            if not declared_path.is_file():
                blockers.append(f"command_path_binding_sha256_path_missing:{label}:{declared_path}")
                continue
            actual_sha = sha256_file(declared_path)
            if actual_sha != expected_sha:
                blockers.append(
                    f"command_path_binding_sha256_mismatch:{label}:expected={expected_sha}:actual={actual_sha}"
                )
    return blockers


def exact_triplet_blockers(action: dict[str, Any]) -> list[str]:
    if action.get("exact_copied_lifecycle_event_triplet_required_before_actionable") is not True:
        return []
    blockers: list[str] = []
    missing_labels = string_list(action.get("missing_copied_lifecycle_event_triplet_labels"))
    missing_cases = dict_list(action.get("missing_copied_lifecycle_event_triplet"))
    match_failures = dict_list(action.get("copied_lifecycle_triplet_match_failures"))
    source_blockers = dict_list(action.get("exact_copied_lifecycle_event_triplet_blockers"))
    if missing_labels:
        blockers.append("exact_copied_lifecycle_event_triplet_missing:" + ",".join(missing_labels))
    elif missing_cases:
        blockers.append(f"exact_copied_lifecycle_event_triplet_missing_cases:{len(missing_cases)}")
    if match_failures:
        blockers.append(f"exact_copied_lifecycle_event_triplet_match_failures_present:{len(match_failures)}")
    if source_blockers:
        blockers.append(f"exact_copied_lifecycle_event_triplet_blockers_present:{len(source_blockers)}")
    if action.get("exact_copied_lifecycle_event_triplet_matched") is False:
        blockers.append("exact_copied_lifecycle_event_triplet_not_matched")
    if action.get("exact_copied_lifecycle_event_triplet_complete") is False:
        blockers.append("exact_copied_lifecycle_event_triplet_source_incomplete")
    return blockers


def source_root_text_values(value: Any) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, Path):
        return [str(value)]
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            output.extend(source_root_text_values(item))
        return output
    if isinstance(value, dict):
        output: list[str] = []
        for key in (
            "path",
            "source_path",
            "source_evidence_dir",
            "invalid_source_evidence_dir",
            "source_run_id",
            "source_root_role",
            "suggested_valid_closure_run_id",
            "suggested_valid_closure_evidence_dir",
        ):
            output.extend(source_root_text_values(value.get(key)))
        return output
    return []


def source_root_values_for_action(action: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "source_evidence_dir",
        "invalid_source_evidence_dir",
        "source_run_id",
        "source_root_role",
    ):
        values.extend(source_root_text_values(action.get(key)))
    if (
        action.get("missing_kind") == "invalid_evidence_source"
        or action.get("action_kind") == "invalid_evidence_source"
    ):
        values.extend(source_root_text_values(action.get("artifact")))
        values.extend(source_root_text_values(action.get("items")))
    guidance = action.get("closure_compatible_copy_guidance")
    if isinstance(guidance, dict):
        values.extend(source_root_text_values(guidance))
    return values


def source_root_boundary(action: dict[str, Any]) -> dict[str, Any]:
    values = source_root_values_for_action(action)
    source_text = " ".join(values)
    run_ids: list[str] = []
    seen: set[str] = set()
    for value in values:
        for run_id in RUN_ID_TEXT_RE.findall(value):
            if run_id in seen:
                continue
            seen.add(run_id)
            run_ids.append(run_id)
    guidance = action.get("closure_compatible_copy_guidance")
    if not isinstance(guidance, dict):
        guidance = {}
    invalid_source = (
        action.get("missing_kind") == "invalid_evidence_source"
        or action.get("action_kind") == "invalid_evidence_source"
        or action.get("source_root_valid_for_closure") is False
    )
    passive_monitor_root = bool(
        action.get("source_looks_like_passive_monitor_root") is True
        or guidance.get("source_looks_like_passive_monitor_root") is True
        or action.get("passive_monitor_root_accepted_as_closure_evidence_dir") is False
        and action.get("copy_or_stage_into_closure_compatible_run_required_before_closure")
        is True
        or PASSIVE_MONITOR_ROOT_RE.search(source_text)
    )
    stale_source = bool(
        action.get("stale_source_root") is True
        or action.get("source_root_stale") is True
        or STALE_SOURCE_ROOT_RE.search(source_text)
    )
    source_only = bool(invalid_source or passive_monitor_root or stale_source)
    if invalid_source and passive_monitor_root:
        classification = "invalid_passive_monitor_root_source_only_non_evidence"
    elif invalid_source:
        classification = "invalid_source_root_source_only_non_evidence"
    elif stale_source and passive_monitor_root:
        classification = "stale_passive_monitor_root_source_only_non_evidence"
    elif stale_source:
        classification = "stale_source_root_source_only_non_evidence"
    elif passive_monitor_root:
        classification = "passive_monitor_root_source_only_non_evidence"
    else:
        classification = "source_root_not_flagged"
    return {
        "schema": RUNNER_SOURCE_ROOT_BOUNDARY_SCHEMA,
        "classification": classification,
        "source_values": values,
        "source_run_ids": run_ids,
        "source_only_non_evidence": source_only,
        "source_is_invalid": invalid_source,
        "source_looks_like_passive_monitor_root": passive_monitor_root,
        "source_is_stale": stale_source,
        "source_accepted_as_closure_evidence_dir": False if source_only else None,
        "source_becomes_runner_action": False if source_only else None,
        "source_authorizes_runner": False,
        "source_counts_as_approved_runtime_evidence": False,
        "manual_staging_required_before_machine_actions": (
            action.get("manual_staging_required_before_machine_actions") is True
            or source_only
        ),
        "runner_command_available": (
            False if source_only else action.get("runner_command_available")
        ),
        "non_authorization": NON_AUTHORIZATION,
    }


def action_is_invalid_passive_root_staging(action: dict[str, Any]) -> bool:
    boundary = source_root_boundary(action)
    if boundary["source_looks_like_passive_monitor_root"] and boundary["source_only_non_evidence"]:
        return True
    if action.get("machine_action_suggested_for_invalid_passive_root") is False:
        return True
    guidance = action.get("closure_compatible_copy_guidance")
    if isinstance(guidance, dict) and guidance.get("source_looks_like_passive_monitor_root") is True:
        return True
    return bool(action.get("source_looks_like_passive_monitor_root") is True)


def executable_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv
    if argv[0].endswith(".py"):
        return [sys.executable, *argv]
    if argv[0].endswith(".sh"):
        return ["bash", *argv]
    return argv


def context_string(context: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def action_context_summary(action: dict[str, Any]) -> dict[str, Any]:
    operator_context = action.get("operator_context")
    if isinstance(operator_context, dict):
        monitor_path = context_string(
            operator_context,
            "post_reboot_monitor_path",
            "post_reboot_passive_monitor_log_path",
            "passive_monitor_log_path",
            "monitor_log_path",
        )
        allowed_operator_context = (
            operator_context.get("allowed_operator_context_under_recorded_standing_authority") is True
            or action.get("allowed_operator_context_under_recorded_standing_authority") is True
            or operator_context.get("allowed_under_recorded_standing_authority") is True
            or operator_context.get("allowed_under_recorded_standing_debug_authority") is True
            or action.get("allowed_under_recorded_standing_authority") is True
            or action.get("allowed_under_recorded_standing_debug_authority") is True
        )
        allowed_under_standing = (
            operator_context.get("allowed_under_recorded_standing_authority") is True
            or operator_context.get("allowed_under_recorded_standing_debug_authority") is True
            or action.get("allowed_under_recorded_standing_authority") is True
            or action.get("allowed_under_recorded_standing_debug_authority") is True
        )
        return {
            "post_reboot_monitor_context_present": (
                operator_context.get("post_reboot_monitor_context_present") is True
                or operator_context.get("post_reboot_passive_monitor_log_supplied") is True
                or bool(monitor_path)
            ),
            "post_reboot_monitor_path": monitor_path,
            "post_reboot_passive_monitor_log_path": monitor_path,
            "confirmed_beta_notice_context_present": (
                operator_context.get("confirmed_beta_notice_context_present") is True
            ),
            "confirmed_beta_notice_path": operator_context.get("confirmed_beta_notice_path"),
            "confirmed_beta_notice_completed": (
                operator_context.get("confirmed_beta_notice_completed") is True
            ),
            "confirmed_beta_notice_standing_launch_authority_recorded": (
                operator_context.get("confirmed_beta_notice_standing_launch_authority_recorded") is True
            ),
            "recorded_standing_authority_observed": (
                operator_context.get("recorded_standing_authority_observed") is True
                or operator_context.get("recorded_standing_debug_authority_observed") is True
                or action.get("recorded_standing_authority_observed") is True
                or action.get("recorded_standing_debug_authority_observed") is True
            ),
            "allowed_operator_context_under_recorded_standing_authority": allowed_operator_context,
            "allowed_under_recorded_standing_authority": allowed_under_standing,
            "standing_authority_is_operator_context_only": True,
            "standing_authority_authorizes_runner": False,
            "runner_execution_authorized_by_recorded_standing_authority": False,
            "standing_authority_counts_as_approved_runtime_evidence": False,
            "player_presence_context_present": (
                operator_context.get("player_presence_context_present") is True
            ),
            "player_presence_targets": string_list(operator_context.get("player_presence_targets")),
            "player_presence_players_detected": (
                operator_context.get("player_presence_players_detected") is True
            ),
            "player_presence_context_authorizes_runner": False,
            "player_presence_context_counts_as_approved_runtime_evidence": False,
            "context_inputs_are_non_evidence": True,
            "context_inputs_authorize_runner": False,
        }
    monitor = action.get("post_reboot_monitor_context")
    if not isinstance(monitor, dict):
        monitor = action.get("post_reboot_passive_monitor")
    if not isinstance(monitor, dict):
        monitor = action.get("passive_monitor_context")
    notice = action.get("confirmed_beta_notice_context")
    presence = action.get("player_presence_context")
    if not isinstance(presence, dict):
        presence = action.get("passive_player_presence")
    monitor_path = (
        context_string(monitor, "path", "source_path", "log_path", "monitor_log_path")
        if isinstance(monitor, dict)
        else None
    )
    notice_path = context_string(notice, "path", "source_path") if isinstance(notice, dict) else None
    presence_targets: list[str] = []
    presence_present = False
    presence_players = False
    if isinstance(presence, dict):
        presence_present = (
            presence.get("present") is True
            or presence.get("players_detected") is True
            or presence.get("presence_detected") is True
            or presence.get("no_players_currently_detected") is True
            or isinstance(presence.get("classification"), str)
        )
        targets = presence.get("targets_with_players_detected")
        if isinstance(targets, list):
            presence_targets.extend(item for item in targets if isinstance(item, str))
            presence_players = bool(presence_targets)
        counts = presence.get("known_player_counts_by_target")
        if not isinstance(counts, dict):
            counts = presence.get("players_current_by_target")
        if isinstance(counts, dict):
            for target, count in counts.items():
                target_text = str(target)
                if target_text and target_text not in presence_targets:
                    presence_targets.append(target_text)
                if isinstance(count, int) and not isinstance(count, bool) and count > 0:
                    presence_players = True
            presence_present = presence_present or bool(counts)
        presence_players = (
            presence_players
            or presence.get("players_detected") is True
            or presence.get("presence_detected") is True
        )
    allowed_operator_context = (
        action.get("allowed_operator_context_under_recorded_standing_authority") is True
        or action.get("allowed_under_recorded_standing_authority") is True
        or action.get("allowed_under_recorded_standing_debug_authority") is True
    )
    allowed_under_standing = (
        action.get("allowed_under_recorded_standing_authority") is True
        or action.get("allowed_under_recorded_standing_debug_authority") is True
    )
    return {
        "post_reboot_monitor_context_present": bool(monitor_path),
        "post_reboot_monitor_path": monitor_path,
        "post_reboot_passive_monitor_log_path": monitor_path,
        "confirmed_beta_notice_context_present": bool(notice_path),
        "confirmed_beta_notice_path": notice_path,
        "confirmed_beta_notice_completed": notice.get("completed") is True if isinstance(notice, dict) else False,
        "confirmed_beta_notice_standing_launch_authority_recorded": (
            notice.get("standing_launch_authority_recorded") is True
            if isinstance(notice, dict)
            else False
        ),
        "recorded_standing_authority_observed": (
            action.get("recorded_standing_authority_observed") is True
            or action.get("recorded_standing_debug_authority_observed") is True
        ),
        "allowed_operator_context_under_recorded_standing_authority": allowed_operator_context,
        "allowed_under_recorded_standing_authority": allowed_under_standing,
        "standing_authority_is_operator_context_only": True,
        "standing_authority_authorizes_runner": False,
        "runner_execution_authorized_by_recorded_standing_authority": False,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "player_presence_context_present": presence_present,
        "player_presence_targets": sorted(presence_targets),
        "player_presence_players_detected": presence_players,
        "player_presence_context_authorizes_runner": False,
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "context_inputs_are_non_evidence": True,
        "context_inputs_authorize_runner": False,
    }


def context_blockers_for_live_action(action: dict[str, Any]) -> list[str]:
    context = action_context_summary(action)
    blockers: list[str] = []
    if context["post_reboot_monitor_context_present"]:
        blockers.append("post_reboot_monitor_context_is_non_evidence_operator_context")
    if context["confirmed_beta_notice_context_present"]:
        blockers.append("confirmed_beta_notice_context_does_not_authorize_runner")
    if context["player_presence_context_present"]:
        blockers.append("player_presence_context_is_non_evidence_operator_context")
    return blockers


def operator_authority_blockers(action: dict[str, Any]) -> list[str]:
    if action.get("requires_operator_authority_before_execution") is not True:
        return []
    source_required = action.get("operator_authority_source_required")
    if source_required in (None, "not_applicable"):
        return []
    if source_required in STANDING_AUTHORITY_SOURCES:
        return [
            "standing_authority_metadata_only_not_runner_execution_authority:"
            f"{source_required}"
        ]
    standing_scope_satisfied = bool(
        source_required in STANDING_AUTHORITY_SOURCES
        and (
            action.get("allowed_under_recorded_standing_authority") is True
            or action.get("allowed_under_recorded_standing_debug_authority") is True
            or action.get("standing_launch_authority_covers_target_run") is True
            or action.get("recorded_standing_launch_authority_satisfies_scope") is True
            or action.get("recorded_standing_debug_authority_satisfies_scope") is True
        )
    )
    if standing_scope_satisfied:
        return []
    if (
        source_required in FRESH_OPERATOR_AUTHORITY_SOURCES
        or action.get("requires_current_turn_operator_approval") is True
        or action.get("requires_fresh_current_turn_operator_approval") is True
    ):
        return [f"operator_authority_required_before_runner_execution:{source_required}"]
    return [f"operator_authority_scope_not_represented_for_runner:{source_required}"]


def artifact_explanation_from_blocker(blocker: str) -> str | None:
    if blocker.startswith("--copied-log"):
        return ARTIFACT_BLOCKER_EXPLANATIONS["Obelisk.log"]
    if blocker.startswith("--window-manifest") or blocker.startswith("--post-window-replay"):
        return ARTIFACT_BLOCKER_EXPLANATIONS["window-manifest.env"]
    for artifact, explanation in ARTIFACT_BLOCKER_EXPLANATIONS.items():
        if artifact in blocker:
            return explanation
    return None


def blocker_explanation(blocker: str) -> str:
    artifact_explanation = artifact_explanation_from_blocker(blocker)
    if artifact_explanation is not None:
        return artifact_explanation
    if blocker.startswith("--"):
        return "required offline input path is missing or unavailable"
    if blocker.startswith("blocked_until_missing:"):
        return "an expected sibling artifact is still missing"
    if blocker.startswith("dry_run_first_required_artifact_missing:"):
        return "this action requires a prior runner dry-run report before --execute"
    if blocker.startswith("dry_run_first_required_artifact_under_forbidden_server_root:"):
        return "the dry-run report path would require reading under /servidor/ark"
    if blocker.startswith("dry_run_first_required_artifact_under_protected_server_root:"):
        return "the dry-run report path is under a protected root"
    if blocker.startswith("dry_run_first_required_artifact_unresolved:"):
        return "the dry-run report path could not be resolved relative to the evidence directory"
    if blocker == "dry_run_first_required_artifact_unspecified":
        return "dry-run-first is declared but no dry-run report path was supplied"
    if blocker.startswith("blocked_until_under_forbidden_server_root:"):
        return "blocked_until artifact would require reading under /servidor/ark"
    if blocker.startswith("argv_references_forbidden_server_root:"):
        return "command argv references /servidor/ark, which this runner scope forbids"
    if blocker.startswith("output_under_forbidden_server_root:"):
        return "command output would write under /servidor/ark"
    if blocker == "writes_under_server_root_not_allowed":
        return "source action declares a server-root write, which this runner forbids"
    if blocker.startswith("exact_copied_lifecycle_event_triplet_"):
        return "exact copied lifecycle event triplet blockers remain unresolved"
    if blocker == "observer_only_no_role_window_requires_manual_close_not_runner":
        return "observer-enable-only source logs close as non-evidence and cannot be made ready by the runner"
    if blocker == "expired_runtime_window_non_evidence_requires_manual_close_not_runner":
        return "expired observer-gate or diagnostic-only windows must be classified as non-evidence outside the runner"
    if blocker == "active_runtime_window_waiting_for_exact_triplet_not_runner":
        return "active runtime windows remain waiting for the exact triplet or window end and are not runner actions"
    if blocker == "stale_passive_complete_role_triplet_non_evidence_not_runner":
        return "stale/passive complete-role triplets are source-only non-evidence and cannot drive checker or bundle actions"
    if blocker == "current_live_diagnostic_context_not_runner_action":
        return "current live diagnostic blocker context is report-only and cannot be executed by the runner"
    if blocker.startswith("evidence_dir_write_requires_explicit_flag"):
        return "offline evidence-directory writes require --allow-evidence-dir-writes"
    if blocker == "command_path_binding_required_for_runtime_evidence_helper":
        return "runtime evidence helper commands require exact path/hash binding metadata"
    if blocker.startswith("command_path_binding_"):
        return "command path/hash binding failed closed before runner eligibility"
    if blocker.startswith("operator_authority_required_before_runner_execution:"):
        return "the action still requires a fresh/current operator authority message before runner execution"
    if blocker.startswith("operator_authority_scope_not_represented_for_runner:"):
        return "recorded standing authority was not bound to this action's exact scope"
    if blocker.startswith("standing_authority_metadata_only_not_runner_execution_authority:"):
        return "recorded standing authority is preserved as metadata, not runner execution authority"
    if blocker.startswith("runtime_window_"):
        return "the runtime window is stale, too close to start, or missing exact approved-window metadata"
    if blocker == "invalid_passive_root_requires_manual_offline_staging_not_runner":
        return "invalid passive monitor roots require manual offline staging into a valid closure root before any runner action"
    if blocker == "source_root_source_only_non_evidence_not_runner_action":
        return "stale/passive/invalid source roots are source-only non-evidence and cannot drive a runner action"
    if blocker == "player_principal_evidence_split_positive_alias_claim_not_runner_authority":
        return "player-principal evidence split metadata contains a positive readiness/authority alias and remains non-evidence"
    if blocker == "player_principal_evidence_split_requires_manual_offline_resolution":
        return "player-principal evidence split actions require manual offline resolution, not runner execution"
    if blocker == "offline_parallel_evidence_lanes_are_planning_only_not_runner":
        return "parallel offline lanes are planning metadata only and are not runner-executable actions"
    if blocker == "offline_parallel_evidence_lanes_misconfigured_not_runner":
        return "parallel offline lane metadata drifted from the non-executable zero-progress contract"
    if blocker in LIVE_OPERATION_SCRIPT_BLOCKERS.values() or blocker in LIVE_OR_PRIVILEGED_FLAGS.values():
        return "live/log/server/Discord operation is outside this offline runner"
    if blocker in {
        "live_wait_action_not_started_by_runner",
        "post_reboot_monitor_context_is_non_evidence_operator_context",
        "confirmed_beta_notice_context_does_not_authorize_runner",
        "player_presence_context_is_non_evidence_operator_context",
    }:
        return "operator context is preserved, but it is not execution authority"
    if blocker.startswith("command_not_offline_runner_allowlisted:"):
        return "script is not in the runner's exact offline helper allowlist"
    if blocker.startswith("command_") or blocker.startswith("structured_runner_command_"):
        return "command metadata is not safe argv for no-shell execution"
    return "action is blocked by source metadata or missing prerequisites"


def eligibility_class(blockers: list[str], argv: list[str] | None) -> str:
    if not blockers and argv is not None:
        return "eligible_offline_helper"
    if any(
        blocker in LIVE_OPERATION_SCRIPT_BLOCKERS.values()
        or blocker in LIVE_OR_PRIVILEGED_FLAGS.values()
        or blocker == "live_wait_action_not_started_by_runner"
        or blocker == "writes_under_server_root_not_allowed"
        or blocker.startswith("argv_references_forbidden_server_root:")
        or blocker.startswith("output_under_forbidden_server_root:")
        or blocker.startswith("blocked_until_under_forbidden_server_root:")
        or blocker.startswith("dry_run_first_required_artifact_under_forbidden_server_root:")
        or blocker.startswith("runtime_window_")
        for blocker in blockers
    ):
        return "blocked_live_or_server_action"
    if any(
        blocker.startswith("--")
        or blocker.startswith("blocked_until_missing:")
        or blocker.startswith("dry_run_first_required_artifact_")
        or blocker.startswith("exact_copied_lifecycle_event_triplet_")
        for blocker in blockers
    ):
        return "blocked_missing_inputs_or_artifacts"
    if any(blocker.startswith("evidence_dir_write_requires_explicit_flag") for blocker in blockers):
        return "blocked_requires_evidence_write_opt_in"
    if any(
        blocker.startswith("operator_authority_required_before_runner_execution:")
        or blocker.startswith("operator_authority_scope_not_represented_for_runner:")
        or blocker.startswith("standing_authority_metadata_only_not_runner_execution_authority:")
        for blocker in blockers
    ):
        return "blocked_requires_operator_authority"
    if any(
        blocker.startswith("command_")
        or blocker.startswith("structured_runner_command_")
        or blocker.startswith("unstructured_shell_command")
        or blocker.startswith("unsafe_or_compound_redirection")
        or blocker.startswith("placeholder_or_stdin_redirection")
        or blocker == "invalid_passive_root_requires_manual_offline_staging_not_runner"
        or blocker == "observer_only_no_role_window_requires_manual_close_not_runner"
        or blocker == "expired_runtime_window_non_evidence_requires_manual_close_not_runner"
        or blocker == "active_runtime_window_waiting_for_exact_triplet_not_runner"
        or blocker == "stale_passive_complete_role_triplet_non_evidence_not_runner"
        or blocker == "current_live_diagnostic_context_not_runner_action"
        or blocker == "source_root_source_only_non_evidence_not_runner_action"
        or blocker.startswith("player_principal_evidence_split_")
        for blocker in blockers
    ):
        return "blocked_unsafe_or_unavailable_command"
    return "blocked_by_action_metadata"


def action_result(action: dict[str, Any], args: argparse.Namespace, plan: dict[str, Any]) -> dict[str, Any]:
    action_id = str(action.get("id") or "<missing>")
    argv, redirect_stdout, command_blockers = command_from_action(action)
    blockers = list(command_blockers)
    stale_prevention = runtime_window_stale_prevention_for_action(action, plan, argv)
    choreography = beta_runtime_choreography_for_action(action, plan)
    split_context = player_principal_evidence_split_for_action(action, plan)
    blockers.extend(string_list(stale_prevention.get("blockers")))
    root_boundary = source_root_boundary(action)
    blocked_until = string_list(action.get("blocked_until"))
    blocked_until_missing: list[str] = []
    if blocked_until:
        blocked_until_extra, blocked_until_missing = blocked_until_blockers(action, argv)
        blockers.extend(blocked_until_extra)
    dry_run_missing: list[str] = []
    dry_run_extra, dry_run_missing = dry_run_first_blockers(
        action,
        argv,
        execute_requested=args.execute,
    )
    blockers.extend(dry_run_extra)
    if action.get("authorized_by_this_report") is not False:
        blockers.append("action_authorization_flag_not_false")
    if action.get("counts_as_approved_runtime_evidence") is not False:
        blockers.append("action_evidence_flag_not_false")
    if action.get("writes_under_server_root") is True:
        blockers.append("writes_under_server_root_not_allowed")
    if action_is_invalid_passive_root_staging(action):
        blockers.append("invalid_passive_root_requires_manual_offline_staging_not_runner")
    if (
        action.get("action_kind") == "observer_only_no_role_window_closure"
        or nested_dict(action, "source_log_not_ready").get(
            "active_observer_only_no_role_window"
        )
        is True
    ):
        blockers.append("observer_only_no_role_window_requires_manual_close_not_runner")
    runtime_lifecycle = action.get("runtime_window_lifecycle")
    if not isinstance(runtime_lifecycle, dict):
        runtime_lifecycle = {}
    if (
        action.get("action_kind") == "expired_runtime_window_non_evidence_closure"
        or action.get("expired_runtime_window_non_evidence") is True
        or runtime_lifecycle.get("close_or_classify_as_non_evidence") is True
    ):
        blockers.append("expired_runtime_window_non_evidence_requires_manual_close_not_runner")
    if (
        action.get("action_kind") == "active_runtime_window_waiting_for_exact_triplet"
        or action.get("active_runtime_window_waiting_for_exact_triplet") is True
        or runtime_lifecycle.get("active_waiting_not_closure_ready") is True
    ):
        blockers.append("active_runtime_window_waiting_for_exact_triplet_not_runner")
    if (
        action.get("action_kind") == "stale_passive_complete_role_triplet_non_evidence"
        or action.get("stale_or_passive_complete_role_triplet_non_evidence") is True
        or runtime_lifecycle.get("stale_or_passive_complete_role_triplet_non_evidence") is True
    ):
        blockers.append("stale_passive_complete_role_triplet_non_evidence_not_runner")
    if (
        action.get("action_kind") == "current_live_diagnostic_context"
        or action.get("blocker")
        in {
            "active_player_observer_only_no_accepted_lifecycle_event",
            "diagnostic_fname_drift_blocks_accepted_events",
        }
    ):
        blockers.append("current_live_diagnostic_context_not_runner_action")
    if root_boundary["source_only_non_evidence"]:
        blockers.append("source_root_source_only_non_evidence_not_runner_action")
    if split_context.get("present") is True:
        if split_context.get("positive_alias_claim_paths"):
            blockers.append("player_principal_evidence_split_positive_alias_claim_not_runner_authority")
        if str(action.get("action_kind") or "").startswith("player_principal_evidence_split"):
            blockers.append("player_principal_evidence_split_requires_manual_offline_resolution")
    offline_lanes = action.get("offline_parallel_evidence_lanes")
    offline_lane_misconfiguration_paths = offline_parallel_lane_misconfiguration_paths(
        offline_lanes
    )
    if isinstance(offline_lanes, dict) and offline_lanes.get("present") is True:
        blockers.append("offline_parallel_evidence_lanes_are_planning_only_not_runner")
        if offline_lane_misconfiguration_paths:
            blockers.append("offline_parallel_evidence_lanes_misconfigured_not_runner")
    if action.get("writes_under_evidence_dir") is True and not args.allow_evidence_dir_writes:
        evidence_dir = action_evidence_dir(action, argv)
        blockers.append(
            "evidence_dir_write_requires_explicit_flag"
            + (f":{evidence_dir}" if evidence_dir is not None else "")
        )
    blockers.extend(operator_authority_blockers(action))
    if argv is not None:
        blockers.extend(missing_required_inputs(argv))
        blockers.extend(missing_output_values(argv))
        blockers.extend(output_write_blockers(output_paths(argv, redirect_stdout), args.allow_evidence_dir_writes))
    command_binding_blockers = command_path_binding_blockers(action, argv, redirect_stdout)
    blockers.extend(command_binding_blockers)
    blockers.extend(exact_triplet_blockers(action))
    live_wait = action.get("action") == "continue_or_request_passive_wait_for_missing_lifecycle_role"
    if live_wait:
        blockers.append("live_wait_action_not_started_by_runner")
        blockers.extend(context_blockers_for_live_action(action))

    eligible = not blockers and argv is not None
    eligibility = eligibility_class(blockers, argv)
    operator_context = action_context_summary(action)
    result: dict[str, Any] = {
        "action_id": action_id,
        "action": action.get("action"),
        "action_kind": action.get("action_kind"),
        "artifact": action.get("artifact"),
        "role": action.get("role"),
        "items": string_list(action.get("items")),
        "missing_artifact_blocker": action.get("missing_artifact_blocker")
        if isinstance(action.get("missing_artifact_blocker"), dict)
        else {},
        "missing_artifact_blockers": [
            item
            for item in action.get("missing_artifact_blockers", [])
            if isinstance(item, dict)
        ]
        if isinstance(action.get("missing_artifact_blockers"), list)
        else [],
        "missing_artifact_reasons": string_list(action.get("missing_artifact_reasons")),
        "missing_artifact_blocker_reason": action.get("missing_artifact_blocker_reason"),
        "first_missing_artifact": action.get("first_missing_artifact"),
        "runtime_evidence_artifact_blockers": action.get("runtime_evidence_artifact_blockers")
        if isinstance(action.get("runtime_evidence_artifact_blockers"), dict)
        else {},
        "exact_triplet_bundle_route": action.get("exact_triplet_bundle_route")
        if isinstance(action.get("exact_triplet_bundle_route"), dict)
        else {},
        "next_action_target": action.get("next_action_target"),
        "first_missing_runtime_evidence_path": action.get(
            "first_missing_runtime_evidence_path"
        ),
        "fastest_exact_path_from_fresh_copied_lifecycle_window": [
            item
            for item in action.get(
                "fastest_exact_path_from_fresh_copied_lifecycle_window",
                [],
            )
            if isinstance(item, dict)
        ]
        if isinstance(action.get("fastest_exact_path_from_fresh_copied_lifecycle_window"), list)
        else [],
        "fastest_missing_role_artifact_path": [
            item
            for item in action.get("fastest_missing_role_artifact_path", [])
            if isinstance(item, dict)
        ]
        if isinstance(action.get("fastest_missing_role_artifact_path"), list)
        else [],
        "required_script": action.get("required_script"),
        "copied_log_path": action.get("copied_log_path"),
        "window_manifest_path": action.get("window_manifest_path"),
        "preflight_post_path": action.get("preflight_post_path"),
        "approved_runtime_evidence_json_path": action.get("approved_runtime_evidence_json_path"),
        "approved_runtime_principal_lifecycle_evidence_bundle_json": action.get(
            "approved_runtime_principal_lifecycle_evidence_bundle_json"
        ),
        "execute_requested": args.execute,
        "eligible_for_execution": eligible,
        "eligibility": eligibility,
        "executed": False,
        "status": "eligible_dry_run" if eligible and not args.execute else "blocked",
        "blockers": blockers,
        "blocker_explanations": [blocker_explanation(blocker) for blocker in blockers],
        "argv": argv,
        "execution_argv": executable_argv(argv) if argv is not None else None,
        "redirect_stdout": redirect_stdout,
        "command_path_binding": action.get("command_path_binding")
        if isinstance(action.get("command_path_binding"), dict)
        else {},
        "command_path_hash_bound": action.get("command_path_hash_bound") is True,
        "command_path_binding_blockers": command_binding_blockers,
        "blocked_until": blocked_until,
        "blocked_until_missing": blocked_until_missing,
        "runtime_window_stale_prevention": stale_prevention,
        "runtime_window_stale_or_too_late": stale_prevention.get("request_window_stale_or_too_late") is True,
        "runtime_window_stale_blockers": string_list(stale_prevention.get("blockers")),
        "beta_runtime_choreography": choreography,
        "checkjoin_stimulus_boundary": choreography.get(
            "stale_or_diagnostic_exact_checkjoin_boundary",
            checkjoin_stimulus_boundary(),
        ),
        "choreography_authorizes_runner": False,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "dry_run_first_required": dry_run_first_required(action),
        "dry_run_must_complete_before_execute": (
            action.get("dry_run_must_complete_before_execute") is True
        ),
        "required_dry_run_artifacts": dry_run_artifact_paths(action),
        "dry_run_missing_artifacts": dry_run_missing,
        "dry_run_report_path": action.get("dry_run_report_path"),
        "evidence_dir": str(action_evidence_dir(action, argv)) if action_evidence_dir(action, argv) else None,
        "source_evidence_dir": action.get("source_evidence_dir"),
        "invalid_source_evidence_dir": action.get("invalid_source_evidence_dir"),
        "suggested_valid_closure_evidence_dir": action.get("suggested_valid_closure_evidence_dir"),
        "closure_compatible_evidence_dir": action.get("closure_compatible_evidence_dir"),
        "source_log_not_ready": action.get("source_log_not_ready")
        if isinstance(action.get("source_log_not_ready"), dict)
        else {},
        "observer_only_no_role_window": action.get("observer_only_no_role_window")
        if isinstance(action.get("observer_only_no_role_window"), dict)
        else {},
        "copy_ready_log_context": action.get("copy_ready_log_context")
        if isinstance(action.get("copy_ready_log_context"), dict)
        else {},
        "runtime_window_lifecycle": runtime_lifecycle,
        "copy_ready_source_boundary": action.get("copy_ready_source_boundary")
        if isinstance(action.get("copy_ready_source_boundary"), dict)
        else runtime_lifecycle.get("copy_ready_source_boundary", {}),
        "fresh_player_backed_window": action.get("fresh_player_backed_window")
        if isinstance(action.get("fresh_player_backed_window"), dict)
        else {},
        "current_live_diagnostic_blockers": action.get("current_live_diagnostic_blockers")
        if isinstance(action.get("current_live_diagnostic_blockers"), dict)
        else {},
        "player_principal_evidence_split": split_context,
        "player_principal_evidence_split_present": split_context.get("present") is True,
        "player_principal_evidence_split_authorizes_runner": False,
        "player_principal_evidence_split_counts_as_approved_runtime_evidence": False,
        "offline_parallel_evidence_lanes": offline_lanes if isinstance(offline_lanes, dict) else {},
        "offline_parallel_evidence_lanes_present": (
            isinstance(offline_lanes, dict) and offline_lanes.get("present") is True
        ),
        "offline_parallel_evidence_lanes_authorize_runner": False,
        "offline_parallel_evidence_lanes_count_as_approved_runtime_evidence": False,
        "offline_parallel_evidence_lanes_misconfiguration_paths": (
            offline_lane_misconfiguration_paths
        ),
        "next_player_backed_window": action.get("next_player_backed_window")
        if isinstance(action.get("next_player_backed_window"), dict)
        else {},
        "manual_offline_next_steps": string_list(action.get("manual_offline_next_steps")),
        "deferred_missing_artifact_actions": string_list(
            action.get("deferred_missing_artifact_actions")
        ),
        "sibling_artifact_generation_deferred_until_source_log_ready": (
            action.get("sibling_artifact_generation_deferred_until_source_log_ready") is True
        ),
        "copy_ready_log_is_operational_only": action.get("copy_ready_log_is_operational_only")
        is True,
        "source_log_ready_to_copy": action.get("source_log_ready_to_copy") is True,
        "source_log_closure_counts_as_evidence": False,
        "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "stale_passive_tail_counts_as_approved_runtime_evidence": False,
        "direct_discord_send_counts_as_approved_runtime_evidence": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "diagnostic_samples_count_as_approved_runtime_evidence": False,
        "expired_runtime_window_non_evidence": (
            action.get("expired_runtime_window_non_evidence") is True
            or runtime_lifecycle.get("close_or_classify_as_non_evidence") is True
        ),
        "stale_or_passive_complete_role_triplet_non_evidence": (
            action.get("stale_or_passive_complete_role_triplet_non_evidence") is True
            or runtime_lifecycle.get("stale_or_passive_complete_role_triplet_non_evidence")
            is True
        ),
        "active_runtime_window_waiting_for_exact_triplet": (
            action.get("active_runtime_window_waiting_for_exact_triplet") is True
            or runtime_lifecycle.get("active_waiting_not_closure_ready") is True
        ),
        "active_window_not_closure_ready": (
            action.get("active_window_not_closure_ready") is True
            or runtime_lifecycle.get("active_waiting_not_closure_ready") is True
        ),
        "prepare_fresh_player_backed_window_required": (
            action.get("prepare_fresh_player_backed_window_required") is True
            or runtime_lifecycle.get("fresh_player_backed_window_required") is True
        ),
        "copy_bundle_commands_suppressed_until_exact_triplet": (
            action.get("copy_bundle_commands_suppressed_until_exact_triplet") is True
            or runtime_lifecycle.get("copy_bundle_commands_suppressed_until_exact_triplet") is True
        ),
        "copy_bundle_commands_allowed_before_exact_triplet": (
            action.get("copy_bundle_commands_allowed_before_exact_triplet") is True
        ),
        "machine_action_suggested_for_invalid_passive_root": action.get(
            "machine_action_suggested_for_invalid_passive_root"
        ),
        "runner_command_available": action.get("runner_command_available"),
        "manual_staging_required_before_machine_actions": action.get(
            "manual_staging_required_before_machine_actions"
        ),
        "source_root_boundary": root_boundary,
        "source_only_non_evidence": root_boundary["source_only_non_evidence"],
        "source_root_classification": root_boundary["classification"],
        "source_root_authorizes_runner": False,
        "source_root_counts_as_approved_runtime_evidence": False,
        "operator_context": operator_context,
        "authorized_by_this_report": False,
        "server_operations_authorized_by_this_report": False,
        "runtime_work_authorized_by_this_report": False,
        "post_window_sidecar_generation_authorized_by_this_report": False,
        "post_window_preflight_live_read_authorized_by_this_report": False,
        "post_window_sidecar_generation_counts_as_approved_runtime_evidence": False,
        "post_window_preflight_live_read_counts_as_approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "recorded_standing_authority_observed": operator_context["recorded_standing_authority_observed"],
        "allowed_operator_context_under_recorded_standing_authority": operator_context[
            "allowed_operator_context_under_recorded_standing_authority"
        ],
        "allowed_under_recorded_standing_authority": operator_context["allowed_under_recorded_standing_authority"],
        "standing_authority_is_operator_context_only": operator_context[
            "standing_authority_is_operator_context_only"
        ],
        "standing_authority_authorizes_runner": False,
        "runner_execution_authorized_by_recorded_standing_authority": False,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "non_authorization": NON_AUTHORIZATION,
    }
    if not args.execute or not eligible:
        return result

    env = os.environ.copy()
    completed: subprocess.CompletedProcess[str]
    run_argv = executable_argv(argv)
    if redirect_stdout:
        output = reject_protected_output(Path(redirect_stdout), "runner redirect_stdout")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle:
            completed = subprocess.run(
                run_argv,
                cwd=REPO_ROOT,
                text=True,
                stdout=handle,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
        stdout_text = None
    else:
        completed = subprocess.run(
            run_argv,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        stdout_text = completed.stdout
    result.update(
        {
            "executed": True,
            "returncode": completed.returncode,
            "status": "executed_success" if completed.returncode == 0 else "executed_failed",
            "stdout": stdout_text,
            "stderr": completed.stderr,
        }
    )
    return result


def result_ids(results: list[dict[str, Any]], predicate: Any) -> list[str]:
    return [
        str(result.get("action_id"))
        for result in results
        if isinstance(result.get("action_id"), str) and predicate(result)
    ]


def offline_parallel_lane_runner_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    action_ids: list[str] = []
    lane_ids: list[str] = []
    misconfiguration_paths: list[str] = []
    for result in results:
        present = (
            result.get("offline_parallel_evidence_lanes_present") is True
            or "offline_parallel_evidence_lanes_are_planning_only_not_runner"
            in result.get("blockers", [])
        )
        if not present or not isinstance(result.get("action_id"), str):
            continue
        action_id = str(result["action_id"])
        if action_id not in action_ids:
            action_ids.append(action_id)
        for path in result.get("offline_parallel_evidence_lanes_misconfiguration_paths", []):
            if isinstance(path, str) and path not in misconfiguration_paths:
                misconfiguration_paths.append(path)
        lanes = result.get("offline_parallel_evidence_lanes")
        if not isinstance(lanes, dict):
            continue
        for lane in lanes.get("lanes", []):
            if not isinstance(lane, dict):
                continue
            lane_id = lane.get("id")
            if isinstance(lane_id, str) and lane_id not in lane_ids:
                lane_ids.append(lane_id)
    expected = list(EXPECTED_OFFLINE_PARALLEL_LANE_IDS)
    return {
        "action_ids": action_ids,
        "lane_ids": lane_ids,
        "lane_count": len(lane_ids),
        "expected_lane_ids": expected,
        "expected_lane_count": len(expected),
        "missing_expected_lane_ids": [
            lane_id for lane_id in expected if action_ids and lane_id not in lane_ids
        ],
        "unexpected_lane_ids": [
            lane_id for lane_id in lane_ids if lane_id not in EXPECTED_OFFLINE_PARALLEL_LANE_IDS
        ],
        "lane_misconfiguration_paths": misconfiguration_paths,
    }


def runner_boundaries(results: list[dict[str, Any]]) -> dict[str, Any]:
    source_only_ids = result_ids(results, lambda result: result.get("source_only_non_evidence") is True)
    dry_run_first_ids = result_ids(
        results,
        lambda result: result.get("dry_run_first_required") is True,
    )
    passive_wait_ids = result_ids(
        results,
        lambda result: "live_wait_action_not_started_by_runner" in result.get("blockers", [])
        or "passive_wait" in str(result.get("action_kind") or result.get("action") or ""),
    )
    observer_only_no_role_ids = result_ids(
        results,
        lambda result: "observer_only_no_role_window_requires_manual_close_not_runner"
        in result.get("blockers", [])
        or nested_dict(result, "source_log_not_ready").get(
            "active_observer_only_no_role_window"
        )
        is True,
    )
    expired_non_evidence_window_ids = result_ids(
        results,
        lambda result: "expired_runtime_window_non_evidence_requires_manual_close_not_runner"
        in result.get("blockers", [])
        or result.get("expired_runtime_window_non_evidence") is True,
    )
    active_waiting_window_ids = result_ids(
        results,
        lambda result: "active_runtime_window_waiting_for_exact_triplet_not_runner"
        in result.get("blockers", [])
        or result.get("active_runtime_window_waiting_for_exact_triplet") is True,
    )
    live_or_human_ids = result_ids(
        results,
        lambda result: result.get("eligibility")
        in {
            "blocked_live_or_server_action",
            "blocked_requires_operator_authority",
        },
    )
    checker_ids = result_ids(
        results,
        lambda result: (
            isinstance(result.get("argv"), list)
            and any(
                token
                in {
                    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                    "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
                }
                for token in result["argv"]
            )
        ),
    )
    checker_executed_count = sum(
        1
        for result in results
        if result.get("executed") is True and result.get("action_id") in checker_ids
    )
    standing_ids = result_ids(
        results,
        lambda result: result.get("recorded_standing_authority_observed") is True
        or result.get("allowed_under_recorded_standing_authority") is True
        or any(
            str(blocker).startswith(
                "standing_authority_metadata_only_not_runner_execution_authority:"
            )
            for blocker in result.get("blockers", [])
        ),
    )
    stale_window_ids = result_ids(
        results,
        lambda result: result.get("runtime_window_stale_or_too_late") is True,
    )
    current_live_context_ids = result_ids(
        results,
        lambda result: "current_live_diagnostic_context_not_runner_action"
        in result.get("blockers", [])
        or isinstance(result.get("current_live_diagnostic_blockers"), dict)
        and bool(result.get("current_live_diagnostic_blockers")),
    )
    split_context_ids = result_ids(
        results,
        lambda result: nested_dict(result, "player_principal_evidence_split").get("present")
        is True,
    )
    split_overclaim_ids = result_ids(
        results,
        lambda result: "player_principal_evidence_split_positive_alias_claim_not_runner_authority"
        in result.get("blockers", []),
    )
    offline_lane_summary = offline_parallel_lane_runner_summary(results)
    offline_lane_ids = offline_lane_summary["action_ids"]
    return {
        "schema": RUNNER_BOUNDARIES_SCHEMA,
        "classification": "next_action_runner_boundaries_no_automatic_side_effects",
        "prepared_artifacts": {
            "classification": "runner_accounting_only",
            "eligible_offline_helper_action_ids": result_ids(
                results,
                lambda result: result.get("eligible_for_execution") is True,
            ),
            "dry_run_first_required_action_ids": dry_run_first_ids,
            "runner_dry_run_report_authorizes_execution": False,
            "prepared_artifacts_authorize_machine_actions": False,
            "prepared_artifacts_count_as_approved_runtime_evidence": False,
        },
        "human_lead_actions": {
            "classification": "human_or_lead_actions_not_automatic",
            "action_ids": live_or_human_ids,
            "automatic_start_or_restart_allowed": False,
            "automatic_discord_send_allowed": False,
            "automatic_marker_env_changes_allowed": False,
            "automatic_live_log_reads_allowed": False,
            "server_operations_performed_by_runner": False,
            "discord_send_performed_by_runner": False,
        },
        "standing_authority_metadata": {
            "schema": RUNNER_STANDING_AUTHORITY_BOUNDARY_SCHEMA,
            "classification": "standing_authority_metadata_only",
            "action_ids": standing_ids,
            "standing_authority_authorizes_runner_execution": False,
            "standing_authority_converted_to_machine_action": False,
            "standing_authority_counts_as_approved_runtime_evidence": False,
            "standing_authority_counts_as_sdk_progress": False,
        },
        "passive_waits": {
            "classification": "passive_wait_source_only_non_evidence",
            "action_ids": passive_wait_ids,
            "passive_waits_started_by_runner": False,
            "passive_wait_counts_as_approved_runtime_evidence": False,
            "passive_wait_authorizes_runtime_capture": False,
        },
        "observer_only_no_role_windows": {
            "classification": "manual_close_as_non_evidence",
            "action_ids": observer_only_no_role_ids,
            "runner_closes_window": False,
            "runner_copies_source_log": False,
            "runner_generates_sidecars_for_no_role_window": False,
            "observer_enable_only_counts_as_approved_runtime_evidence": False,
            "source_log_ready_to_copy": False,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        },
        "runtime_window_lifecycle": {
            "schema": "obelisk.player-principal-lifecycle-runtime-window-lifecycle-runner.v1",
            "classification": (
                "expired_non_evidence_windows_blocked_prepare_fresh_player_backed_window"
                if expired_non_evidence_window_ids
                else "active_windows_waiting_not_runner_actions"
                if active_waiting_window_ids
                else "no_runtime_window_lifecycle_actions"
            ),
            "expired_non_evidence_action_ids": expired_non_evidence_window_ids,
            "active_waiting_action_ids": active_waiting_window_ids,
            "runner_closes_expired_windows": False,
            "runner_copies_source_log": False,
            "runner_builds_bundle": False,
            "runner_runs_checker": False,
            "copy_bundle_commands_suppressed_until_exact_triplet": bool(
                expired_non_evidence_window_ids or active_waiting_window_ids
            ),
            "fresh_player_backed_window_required": bool(expired_non_evidence_window_ids),
            "active_windows_remain_waiting": bool(active_waiting_window_ids),
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        },
        "source_only_monitor_roots": {
            "classification": "stale_passive_invalid_roots_source_only_non_evidence",
            "action_ids": source_only_ids,
            "source_roots_accepted_as_closure_evidence_dir": False,
            "source_roots_authorize_runner": False,
            "source_roots_count_as_approved_runtime_evidence": False,
        },
        "runtime_window_stale_prevention": {
            "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
            "classification": "stale_or_too_late_runtime_window_actions_blocked",
            "action_ids": stale_window_ids,
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "runner_converts_stale_window_to_live_action": False,
            "prepared_artifacts_count_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        },
        "current_live_diagnostic_blockers": {
            **current_live_diagnostic_blockers_context(),
            "classification": "current_live_source_bound_drift_context_not_runner_authority",
            "action_ids": current_live_context_ids,
            "runner_converts_context_to_execution": False,
            "runner_accepts_context_as_evidence": False,
            "runner_starts_blind_wait": False,
            "runner_starts_restart": False,
            "runner_issues_logout_instruction": False,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "sdk_progress": 0,
            "p0_progress": 0,
            "non_authorization": NON_AUTHORIZATION,
        },
        "player_principal_evidence_split": {
            "schema": PLAYER_PRINCIPAL_EVIDENCE_SPLIT_RUNNER_SCHEMA,
            "classification": "player_principal_evidence_split_context_non_authorizing",
            "present": bool(split_context_ids),
            "action_ids": split_context_ids,
            "overclaim_action_ids": split_overclaim_ids,
            "runner_accepts_split_as_evidence": False,
            "runner_accepts_start_end_as_approved_runtime_evidence": False,
            "split_authorizes_runner": False,
            "split_authorizes_runtime_capture": False,
            "split_counts_as_approved_runtime_evidence": False,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "sdk_progress": 0,
            "p0_progress": 0,
            "non_authorization": NON_AUTHORIZATION,
        },
        "offline_parallel_evidence_lanes": {
            "schema": "obelisk.player-principal-lifecycle-offline-parallel-evidence-lanes-runner.v1",
            "classification": (
                "parallel_offline_lanes_blocked_as_planning_metadata"
                if offline_lane_ids
                else "no_parallel_offline_lanes"
            ),
            "present": bool(offline_lane_ids),
            "action_ids": offline_lane_ids,
            "lane_ids": offline_lane_summary["lane_ids"],
            "lane_count": offline_lane_summary["lane_count"],
            "expected_lane_ids": offline_lane_summary["expected_lane_ids"],
            "expected_lane_count": offline_lane_summary["expected_lane_count"],
            "missing_expected_lane_ids": offline_lane_summary[
                "missing_expected_lane_ids"
            ],
            "unexpected_lane_ids": offline_lane_summary["unexpected_lane_ids"],
            "lane_misconfiguration_paths": offline_lane_summary[
                "lane_misconfiguration_paths"
            ],
            "runner_executes_parallel_lanes": False,
            "runner_converts_lanes_to_live_ops": False,
            "lanes_authorize_runner": False,
            "lanes_authorize_runtime_capture": False,
            "lanes_count_as_approved_runtime_evidence": False,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "sdk_progress": 0,
            "p0_progress": 0,
            "non_authorization": NON_AUTHORIZATION,
        },
        "beta_runtime_choreography": {
            "schema": BETA_RUNTIME_CHOREOGRAPHY_SCHEMA,
            "classification": "runner_preserves_single_tester_choreography_without_authority",
            "action_ids": result_ids(
                results,
                lambda result: isinstance(result.get("beta_runtime_choreography"), dict),
            ),
            "one_tester_direct_join_required": True,
            "wait_for_exact_checkjoin_before_logout_required": False,
            "wait_for_exact_checkjoin_before_logout_candidate_only_after_blocker_clear": True,
            "source_bound_blockers_must_be_clear_before_choreography": True,
            "blind_wait_instruction": False,
            "logout_instruction_allowed_now": False,
            "mixed_transfer_reconnect_same_approved_window_allowed": False,
            "stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only": True,
            "runner_converts_choreography_to_live_action": False,
            "choreography_authorizes_runner": False,
            "choreography_counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        },
        "checker_required_post_window_replay": {
            "schema": RUNNER_CHECKER_REPLAY_BOUNDARY_SCHEMA,
            "classification": "checker_output_required_before_evidence_acceptance",
            "action_ids": checker_ids,
            "checker_actions_executed_by_runner_count": checker_executed_count,
            "runner_accepts_evidence": False,
            "approved_evidence_bundle_checker_accepted_by_runner": False,
            "post_window_replay_required_before_readiness": True,
            "clears_approved_runtime_evidence_missing": False,
        },
        "automatic_start_or_restart_allowed": False,
        "automatic_discord_send_allowed": False,
        "automatic_evidence_acceptance_allowed": False,
        "standing_authority_converted_to_machine_action": False,
        "approved_runtime_evidence_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def runtime_evidence_artifact_runner_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    action_ids: list[str] = []
    for result in results:
        action_id = str(result.get("action_id"))
        direct = result.get("missing_artifact_blocker")
        if isinstance(direct, dict) and direct:
            blockers.append({**direct, "action_id": action_id})
            action_ids.append(action_id)
        nested = result.get("missing_artifact_blockers")
        if isinstance(nested, list):
            for item in nested:
                if isinstance(item, dict):
                    blockers.append({**item, "action_id": action_id})
                    if action_id not in action_ids:
                        action_ids.append(action_id)
    first = blockers[0] if blockers else None
    return {
        "schema": "obelisk.player-principal-lifecycle-runtime-evidence-artifact-runner.v1",
        "present": bool(blockers),
        "action_ids": action_ids,
        "first_missing_artifact": first.get("artifact") if first else None,
        "first_blocker_reason": first.get("reason") if first else None,
        "missing_artifact_reasons": [
            str(blocker.get("reason"))
            for blocker in blockers
            if isinstance(blocker.get("reason"), str)
        ],
        "missing_artifact_blockers": blockers,
        "runner_accepts_artifact_as_evidence": False,
        "runner_accepts_approved_bundle_as_evidence": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def exact_triplet_bundle_runner_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    routes = [
        result["exact_triplet_bundle_route"]
        for result in results
        if isinstance(result.get("exact_triplet_bundle_route"), dict)
        and result["exact_triplet_bundle_route"]
    ]
    first = routes[0] if routes else {}
    return {
        "schema": "obelisk.player-principal-lifecycle-exact-triplet-bundle-runner.v1",
        "present": bool(routes),
        "action_ids": [
            str(result.get("action_id"))
            for result in results
            if isinstance(result.get("exact_triplet_bundle_route"), dict)
            and result["exact_triplet_bundle_route"]
        ],
        "route_name": first.get("route_name"),
        "next_action_target": first.get("next_action_target"),
        "first_missing_kind": first.get("first_missing_kind"),
        "first_missing_role": first.get("first_missing_role"),
        "first_missing_runtime_evidence_path": first.get(
            "first_missing_runtime_evidence_path"
        ),
        "missing_lifecycle_event_roles": first.get("missing_lifecycle_event_roles", []),
        "missing_required_artifacts": first.get("missing_required_artifacts", []),
        "runner_accepts_partial_lifecycle_material_as_evidence": False,
        "runner_accepts_copied_log_presence_as_evidence": False,
        "runner_accepts_stale_passive_tail_as_evidence": False,
        "runner_accepts_direct_discord_send_as_evidence": False,
        "runner_accepts_active_notice_state_as_evidence": False,
        "runner_accepts_diagnostic_samples_as_evidence": False,
        "helper_command_authorized_by_runner": False,
        "runner_accepts_route_as_evidence": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    plan_path, plan = load_plan(args.plan_json)
    actions = selected_actions(plan, args.action_id)
    results = [action_result(action, args, plan) for action in actions]
    executed = [result for result in results if result["executed"]]
    blocked = [result for result in results if result["blockers"]]
    first_eligible = next((result for result in results if result["eligible_for_execution"]), None)
    eligibility_counts: dict[str, int] = {}
    for result in results:
        key = str(result.get("eligibility") or "unknown")
        eligibility_counts[key] = eligibility_counts.get(key, 0) + 1
    missing_role_actions = [
        result
        for result in results
        if result.get("role")
        and any("live_wait_action_not_started_by_runner" == blocker for blocker in result["blockers"])
    ]
    missing_input_blockers = [
        blocker
        for result in results
        for blocker in result["blockers"]
        if (
            blocker.startswith("--")
            or blocker.startswith("blocked_until_missing:")
            or blocker.startswith("dry_run_first_required_artifact_missing:")
        )
    ]
    stale_or_too_late = [
        result for result in results if result.get("runtime_window_stale_or_too_late") is True
    ]
    boundaries = runner_boundaries(results)
    artifact_summary = runtime_evidence_artifact_runner_summary(results)
    triplet_bundle_summary = exact_triplet_bundle_runner_summary(results)
    current_live_blockers = plan_current_live_diagnostic_blockers(plan)
    plan_split_payload = (
        plan.get("player_principal_evidence_split")
        if isinstance(plan.get("player_principal_evidence_split"), dict)
        else nested_dict(plan, "action_plan", "player_principal_evidence_split")
    )
    plan_split_context = normalized_player_principal_evidence_split(
        plan_split_payload if plan_split_payload else None
    )
    plan_choreography = (
        plan.get("beta_runtime_choreography")
        if isinstance(plan.get("beta_runtime_choreography"), dict)
        else default_beta_runtime_choreography(None)
    )
    return {
        "schema": SCHEMA,
        "status": (
            "executed_with_failures"
            if any(result.get("returncode") not in (None, 0) for result in executed)
            else "executed"
            if executed
            else "dry_run"
            if not args.execute
            else "execute_blocked"
        ),
        "ready": False,
        **FALSE_FLAGS,
        "plan_json": str(plan_path),
        "plan_schema": plan.get("schema"),
        "source_action_count": len(actions),
        "execute_requested": args.execute,
        "allow_evidence_dir_writes": args.allow_evidence_dir_writes,
        "executed_count": len(executed),
        "blocked_count": len(blocked),
        "eligible_count": sum(1 for result in results if result["eligible_for_execution"]),
        "stale_or_too_late_action_count": len(stale_or_too_late),
        "stale_or_too_late_action_ids": [
            str(result.get("action_id"))
            for result in stale_or_too_late
            if isinstance(result.get("action_id"), str)
        ],
        "eligibility_counts": eligibility_counts,
        "first_eligible_action_id": first_eligible["action_id"] if first_eligible else None,
        "first_eligible_action": first_eligible.get("action") if first_eligible else None,
        "missing_role_action_count": len(missing_role_actions),
        "missing_input_or_artifact_blocker_count": len(missing_input_blockers),
        "results": results,
        "execution_boundaries": boundaries,
        "runtime_evidence_artifact_runner_summary": artifact_summary,
        "exact_triplet_bundle_runner_summary": triplet_bundle_summary,
        "current_live_diagnostic_blockers": current_live_blockers,
        "prepared_artifacts": boundaries["prepared_artifacts"],
        "human_lead_actions": boundaries["human_lead_actions"],
        "standing_authority_metadata": boundaries["standing_authority_metadata"],
        "passive_waits": boundaries["passive_waits"],
        "observer_only_no_role_windows": boundaries["observer_only_no_role_windows"],
        "runtime_window_lifecycle": boundaries["runtime_window_lifecycle"],
        "source_only_monitor_roots": boundaries["source_only_monitor_roots"],
        "runtime_window_stale_prevention": boundaries["runtime_window_stale_prevention"],
        "current_live_diagnostic_blocker_boundaries": boundaries[
            "current_live_diagnostic_blockers"
        ],
        "player_principal_evidence_split": plan_split_context
        if plan_split_context.get("present") is True
        else boundaries["player_principal_evidence_split"],
        "player_principal_evidence_split_runner_summary": boundaries[
            "player_principal_evidence_split"
        ],
        "player_principal_evidence_split_counts_as_approved_runtime_evidence": False,
        "offline_parallel_evidence_lanes": boundaries["offline_parallel_evidence_lanes"],
        "offline_parallel_evidence_lanes_count_as_approved_runtime_evidence": False,
        "beta_runtime_choreography": {
            **plan_choreography,
            "source_bound_blockers_must_be_clear_before_choreography": True,
            "choreography_is_candidate_only_until_source_bound_blockers_clear": True,
            "blind_wait_instruction": False,
            "logout_instruction_allowed_now": False,
            "choreography_authorizes_runner": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": plan_choreography.get("non_authorization", NON_AUTHORIZATION),
        },
        "checkjoin_stimulus_boundary": checkjoin_stimulus_boundary(),
        "runtime_choreography_boundary": boundaries["beta_runtime_choreography"],
        "checker_required_post_window_replay": boundaries[
            "checker_required_post_window_replay"
        ],
        "exact_triplet_bundle_route": triplet_bundle_summary,
        "non_claims": [
            "runner output is operational planning/execution accounting only",
            "approved runtime evidence remains false until approved bundle checkers accept copied evidence",
            "live wait actions are not started by this runner",
            "server operations, Discord, marker/env changes, and live log reads are not authorized by this report",
            "current live diagnostic blockers are preserved as context only and are not runner execution authority or SDK/P0 progress",
        ],
        "non_authorization": NON_AUTHORIZATION,
    }


def emit_report(report: dict[str, Any], args: argparse.Namespace) -> None:
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output is not None and str(args.json_output) != "-":
        output = reject_protected_output(args.json_output, "--json-output")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    if args.json or args.json_output is None or str(args.json_output) == "-":
        print(text)
    elif args.json_output is not None:
        print(
            "player_principal_lifecycle_next_action_runner_status="
            f"{report['status']} executed_count={report['executed_count']} "
            "approved_runtime_evidence=false"
        )


def main() -> int:
    args = parse_args()
    report = build_report(args)
    emit_report(report, args)
    if args.execute and report["executed_count"] == 0:
        return 1
    if report["status"] == "executed_with_failures":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
