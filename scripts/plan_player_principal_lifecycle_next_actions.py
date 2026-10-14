#!/usr/bin/env python3
"""Normalize player-principal lifecycle next actions from offline reports.

This coordinator consumes already-produced JSON reports and emits one deterministic
action queue for the lead/runtime runner. It does not send Discord, touch ARK, read
live logs, edit markers/env, copy evidence, build approved bundles, or claim SDK
readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths


SCHEMA = "obelisk.player-principal-lifecycle-next-action-plan.v1"
SERVER_ROOT = Path("/servidor/ark")

RUNTIME_EXECUTION_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-execution.v1"
ACTIVATION_PRECONDITIONS_SCHEMA = "obelisk.player-principal-lifecycle-activation-preconditions.v1"
BETA_NOTICE_SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-prep.v1"
RUNTIME_EVIDENCE_STATUS_SCHEMA = "obelisk.player-principal-lifecycle-runtime-evidence-status.v1"
CLOSURE_REQUEST_SCHEMA = "obelisk.player-principal-lifecycle-evidence-closure-request.v1"
OBSERVER_LOG_SUMMARY_SCHEMA = "obelisk.runtime-observer-log-summary.v1"
CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA = (
    "obelisk.player-principal-lifecycle-current-live-diagnostic-blockers.v1"
)

SUPPORTED_SCHEMAS = {
    RUNTIME_EXECUTION_SCHEMA,
    ACTIVATION_PRECONDITIONS_SCHEMA,
    BETA_NOTICE_SCHEMA,
    RUNTIME_EVIDENCE_STATUS_SCHEMA,
    CLOSURE_REQUEST_SCHEMA,
    OBSERVER_LOG_SUMMARY_SCHEMA,
}

FALSE_FLAGS = {
    "activation_allowed": False,
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
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_sdk": False,
    "counts_toward_v1_completion": False,
    "discord_authorized": False,
    "discord_sent_by_this_report": False,
    "live_log_reads_authorized": False,
    "live_ops_authorized": False,
    "marker_env_changes_authorized": False,
    "public_sdk_ready": False,
    "publication_authorized": False,
    "runtime_capture_authorized": False,
    "runtime_evidence_present": False,
    "runtime_evidence_ready": False,
    "runtime_ready": False,
    "runtime_window_authorized": False,
    "runtime_work_authorized": False,
    "server_operations_authorized": False,
    "stable_claim_allowed": False,
    "stable_sdk_ready": False,
    "v1_completion_ready": False,
    "workspace_writes_authorized": False,
}
ZERO_PROGRESS_FLAGS = {
    "sdk_progress": 0,
    "p0_progress": 0,
    "runtime_progress": 0,
    "standing_authority_sdk_progress": 0,
    "standing_authority_p0_progress": 0,
}

FORBIDDEN_TRUE_CLAIM_KEYS = {
    "accepted_runtime_evidence",
    "accepted_in_game_evidence",
    "approved_in_game",
    "approved_in_game_evidence",
    "approved_in_game_evidence_ready",
    "activation_allowed",
    "activation_authorized_by_this_report",
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "authorizes_discord",
    "authorizes_runtime_work",
    "authorizes_server_operations",
    "authorizes_workspace_writes",
    "complete_sdk_claim_allowed",
    "complete_sdk_ready",
    "confirmed_send_authorizes_activation",
    "confirmed_send_authorizes_runtime_capture",
    "confirmed_send_authorizes_server_operations",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_toward_p0_dependency_chain",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "discord_authorized",
    "discord_authorized_by_this_report",
    "discord_send_authorized",
    "discord_sent",
    "discord_sent_by_this_report",
    "live_log_reads_authorized",
    "live_ops_authorized",
    "marker_env_changes_authorized",
    "operator_may_activate_by_this_report",
    "publication_authorized",
    "public_abi_ready",
    "public_header_allowed",
    "public_sdk_ready",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_capture_authorized",
    "runtime_ready",
    "runtime_window_authorized",
    "runtime_work_authorized",
    "sdk_evidence_ready",
    "server_operations_authorized",
    "server_operations_authorized_by_this_report",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "v1_completion_ready",
    "workspace_writes_authorized",
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

POSITIVE_TOKENS = {
    "accepted",
    "allowed",
    "approved",
    "authorized",
    "complete",
    "completed",
    "enabled",
    "present",
    "ready",
    "sent",
    "supported",
    "true",
    "unlocked",
    "yes",
}
NEGATIVE_TOKENS = {
    "blocked",
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

NON_AUTHORIZATION = (
    "next-action planning only; this report does not authorize Discord, ARK server "
    "operations, marker/env changes, live log reads, runtime capture, approved runtime "
    "evidence, public readiness, SDK completion, Plugin Hub, publication, or P0 progress"
)
STANDING_AUTHORITY_SOURCES = {
    "recorded_standing_debug_authority",
    "recorded_standing_launch_authority",
    "standing_launch_authority",
}
FRESH_OPERATOR_AUTHORITY_SOURCES = {
    "fresh_current_turn_operator_message",
    "fresh_current_turn_operator_scope",
}

ROUTE_AUDIT_SCHEMA = "obelisk.player-principal-lifecycle-offline-route-audit.v1"
RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-stale-prevention.v1"
)
OFFLINE_PARALLEL_EVIDENCE_LANES_SCHEMA = (
    "obelisk.player-principal-lifecycle-offline-parallel-evidence-lanes.v1"
)
BETA_NOTICE_SEQUENCE_ENFORCEMENT_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-notice-sequence-enforcement.v1"
)
BETA_RUNTIME_CHOREOGRAPHY_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-runtime-choreography.v1"
)
CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-checkjoin-stimulus-boundary.v1"
)
ROUTE_SAMPLE_ANALYSIS_SCHEMA = (
    "obelisk.player-principal-lifecycle-route-sample-analysis.v1"
)
PLAYER_PRINCIPAL_LIFECYCLE_MODULE = "player_principal_lifecycle"
MIN_RUNTIME_WINDOW_LEAD_SECONDS = 300
CURRENT_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE = (
    "approved_runtime_principal_lifecycle_evidence_bundle"
)

ROUTE_SAMPLE_KNOWN_FNAME_TARGETS = {
    "1845": "ShooterGameMode.CheckJoinInProgress",
    "2170": "ShooterGameMode.HandleNewPlayer",
    "2384": "ShooterGameMode.OnLogout",
    "4943": "GameMode.K2_PostLogin",
}

CONTEXT_FALSE_FLAGS = {
    "authorized_by_this_plan": False,
    "server_operations_authorized_by_this_plan": False,
    "runtime_work_authorized_by_this_plan": False,
    "live_ops_authorized_by_this_plan": False,
    "runtime_capture_authorized_by_this_plan": False,
    "live_log_reads_authorized_by_this_plan": False,
    "discord_authorized_by_this_plan": False,
    "activation_allowed_by_this_plan": False,
    "approved_runtime_evidence": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "counts_toward_sdk": False,
    "counts_toward_p0_dependency_chain": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "player_presence_context_authorizes_runner": False,
    "player_presence_context_counts_as_approved_runtime_evidence": False,
}

POST_REBOOT_MONITOR_CONTEXT_KEYS = (
    ("operational_context", "post_reboot_monitor_context"),
    ("current_turn_approval_requirements", "post_reboot_monitor_context"),
    ("operator_authority_requirements", "post_reboot_monitor_context"),
    ("post_reboot_passive_monitor",),
    ("post_reboot_monitor_context",),
)
CONFIRMED_BETA_NOTICE_CONTEXT_KEYS = (
    ("operational_context", "confirmed_beta_notice_context"),
    ("current_turn_approval_requirements", "confirmed_beta_notice_context"),
    ("operator_authority_requirements", "confirmed_beta_notice_context"),
    ("confirmed_beta_notice",),
    ("confirmed_beta_notice_context",),
)
PLAYER_PRESENCE_CONTEXT_KEYS = (
    ("operational_context", "player_presence_context"),
    ("current_turn_approval_requirements", "player_presence_context"),
    ("operator_authority_requirements", "player_presence_context"),
    ("runtime_player_availability",),
    ("player_presence_context",),
    ("passive_player_presence",),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-json",
        action="append",
        required=True,
        type=Path,
        help="Offline JSON report to consume. Repeat to merge sources in order.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional output file. Use '-' or omit for stdout.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
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


def approved_window_from_run_id(run_id: str | None) -> dict[str, Any] | None:
    # Run ids encode only the window start. The approved duration must be supplied by
    # explicit approved_window metadata because passive windows are bounded from
    # 900 to 7200 seconds.
    return None


def action_approved_window(
    *,
    action: dict[str, Any],
    source_payload: dict[str, Any],
    source_run_id_value: str | None,
) -> dict[str, Any] | None:
    for candidate in (
        action.get("approved_window"),
        nested_dict(action, "runner_contract", "approved_window"),
        nested_dict(action, "beta_notice_sequence_enforcement", "approved_window"),
        nested_dict(action, "runtime_window_stale_prevention"),
        source_payload.get("approved_window"),
        nested_dict(source_payload, "beta_notice_sequence_enforcement", "approved_window"),
    ):
        if isinstance(candidate, dict):
            start = candidate.get("start_utc")
            end = candidate.get("end_utc")
            if isinstance(start, str) and isinstance(end, str):
                return {"start_utc": start, "end_utc": end, **{
                    key: value
                    for key, value in candidate.items()
                    if key not in {"start_utc", "end_utc"}
                }}
    return approved_window_from_run_id(source_run_id_value)


def action_requires_current_runtime_window(action: dict[str, Any]) -> bool:
    if action.get("action_kind") in {
        "expired_runtime_window_non_evidence_closure",
        "active_runtime_window_waiting_for_exact_triplet",
    }:
        return False
    text_parts = [
        action.get("id"),
        action.get("action_id"),
        action.get("action"),
        action.get("operation"),
        action.get("action_kind"),
        action.get("phase"),
        action.get("side_effect_domain"),
        nested_dict(action, "runner_contract").get("phase"),
        nested_dict(action, "runner_contract").get("operation_kind"),
        nested_dict(action, "runner_contract").get("side_effect_domain"),
        nested_dict(action, "runner_operation").get("kind"),
    ]
    text = " ".join(str(part) for part in text_parts if isinstance(part, str)).casefold()
    current_window_terms = (
        "active_observation",
        "activation_precondition",
        "confirmed_beta_notice",
        "guarded_beta_notice",
        "marker_env_runtime_observation",
        "player_presence_restart_safety",
        "runtime_window",
        "safe_restart",
    )
    return any(term in text for term in current_window_terms)


def runtime_window_stale_prevention_for_action(
    *,
    action: dict[str, Any],
    source_payload: dict[str, Any],
    source_run_id_value: str | None,
) -> dict[str, Any]:
    applies = action_requires_current_runtime_window(action)
    window = action_approved_window(
        action=action,
        source_payload=source_payload,
        source_run_id_value=source_run_id_value,
    )
    blockers: list[str] = []
    if window is None:
        blockers.append("runtime_window_approved_window_missing_for_action")
        return {
            "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
            "applies_to_action": applies,
            "approved_window": None,
            "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "enough_future_lead_time": False,
            "window_start_in_future": False,
            "window_end_in_future": False,
            "stale_request_window": applies,
            "request_window_stale_or_too_late": applies,
            "blockers": blockers if applies else [],
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
        blockers.append("runtime_window_approved_window_time_invalid_for_action")
        return {
            "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
            "applies_to_action": applies,
            "approved_window": window,
            "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "enough_future_lead_time": False,
            "window_start_in_future": False,
            "window_end_in_future": False,
            "stale_request_window": applies,
            "request_window_stale_or_too_late": applies,
            "blockers": blockers if applies else [],
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


def beta_notice_sequence_enforcement_for_action(
    *,
    action: dict[str, Any],
    stale_prevention: dict[str, Any],
) -> dict[str, Any]:
    existing = action.get("beta_notice_sequence_enforcement")
    if isinstance(existing, dict):
        return {
            **existing,
            "runtime_window_stale_prevention": existing.get(
                "runtime_window_stale_prevention",
                stale_prevention,
            ),
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
        }
    return {
        "schema": BETA_NOTICE_SEQUENCE_ENFORCEMENT_SCHEMA,
        "runtime_window_stale_prevention": stale_prevention,
        "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
        "beta_notice_dry_run_required_before_confirmed_send": True,
        "beta_notice_dry_run_required_before_activation": True,
        "confirmed_beta_notice_required_before_activation": True,
        "confirmed_send_must_complete_before_window_start": True,
        "activation_preconditions_required_before_activation_or_restart": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "dry_run_or_confirmed_send_counts_as_approved_runtime_evidence": False,
        "confirmed_notice_counts_as_approved_runtime_evidence": False,
        "confirmed_notice_grants_readiness": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


NORMALIZED_FORBIDDEN_TRUE_CLAIM_KEYS = {
    normalized_key(key) for key in FORBIDDEN_TRUE_CLAIM_KEYS
}
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
        if tokens & NEGATIVE_TOKENS and not (tokens & POSITIVE_TOKENS):
            return False
        if {"not", "authorized"}.issubset(tokens):
            return False
        return bool(tokens & POSITIVE_TOKENS)
    if isinstance(value, dict):
        return any(positive_claim_value(child) for child in value.values())
    if isinstance(value, list):
        return any(positive_claim_value(child) for child in value)
    return False


def zero_progress_value(value: Any) -> bool:
    if value in (0, 0.0):
        return True
    if isinstance(value, str):
        return value.strip() in {"0", "0.0", "none", "no", "false", "not_applicable"}
    return False


def collect_shortcut_aliases(value: Any, trail: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}" if trail != "$" else f"$.{key}"
            normalized = normalized_key(key)
            if normalized in NORMALIZED_FORBIDDEN_TRUE_CLAIM_KEYS and positive_claim_value(child):
                matches.append(child_trail)
            if normalized in NORMALIZED_FORBIDDEN_PROGRESS_KEYS and not zero_progress_value(child):
                matches.append(child_trail)
            matches.extend(collect_shortcut_aliases(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(collect_shortcut_aliases(child, f"{trail}[{index}]"))
    return matches


def resolved_input(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    return protected_paths.reject_protected_input_path(
        path.expanduser(),
        label,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )


def resolved_output(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    return protected_paths.reject_protected_output_path(
        path.expanduser(),
        label,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )


def load_json(path: Path, label: str) -> tuple[Path, dict[str, Any], str]:
    resolved = resolved_input(path, label)
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise SystemExit(f"{label} is unreadable: {exc}") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must contain a JSON object")
    return resolved, payload, hashlib.sha256(raw).hexdigest()


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def int_value(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def route_sample_module(payload: dict[str, Any]) -> dict[str, Any]:
    modules = payload.get("modules")
    if not isinstance(modules, dict):
        return {}
    module = modules.get(PLAYER_PRINCIPAL_LIFECYCLE_MODULE)
    return module if isinstance(module, dict) else {}


def route_sample_analysis_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("schema") != OBSERVER_LOG_SUMMARY_SCHEMA:
        return None
    module = route_sample_module(payload)
    sample_count = int_value(module.get("diagnostic_route_sample_count"))
    fname_counts_raw = module.get("diagnostic_route_sample_fname_index_counts")
    fname_counts: dict[str, int] = {}
    if isinstance(fname_counts_raw, dict):
        for key, value in fname_counts_raw.items():
            count = int_value(value)
            if count > 0:
                fname_counts[str(key)] = count
    if sample_count <= 0 and not fname_counts:
        return None

    known_targets = [
        {
            "fname_index": fname_index,
            "target": target,
            "count": fname_counts[fname_index],
        }
        for fname_index, target in ROUTE_SAMPLE_KNOWN_FNAME_TARGETS.items()
        if fname_index in fname_counts
    ]
    known_indices = {entry["fname_index"] for entry in known_targets}
    unknown_counts = {
        fname_index: count
        for fname_index, count in sorted(fname_counts.items())
        if fname_index not in known_indices
    }
    return {
        "schema": ROUTE_SAMPLE_ANALYSIS_SCHEMA,
        "status": "diagnostic_route_samples_present_non_evidence",
        "classification": "diagnostic_route_sample_planning_context_only",
        "source_schema": OBSERVER_LOG_SUMMARY_SCHEMA,
        "module": PLAYER_PRINCIPAL_LIFECYCLE_MODULE,
        "sample_count": sample_count,
        "max_sequence": module.get("diagnostic_route_sample_max_sequence"),
        "sample_limits": [
            item
            for item in module.get("diagnostic_route_sample_limits", [])
            if isinstance(item, int) and not isinstance(item, bool)
        ],
        "budget_reached": module.get("diagnostic_route_sample_budget_reached") is True,
        "observed_fname_index_counts": dict(sorted(fname_counts.items())),
        "observed_fname_indices": sorted(fname_counts),
        "observed_known_lifecycle_targets": known_targets,
        "observed_known_lifecycle_target_count": len(known_targets),
        "unknown_fname_index_counts": unknown_counts,
        "accepted_lifecycle_event_roles": string_list(
            module.get("accepted_lifecycle_event_roles")
        ),
        "missing_lifecycle_event_roles": string_list(
            module.get("missing_lifecycle_event_roles")
        ),
        "recommended_next_action": (
            "source-bind observed known lifecycle functions and inspect bounded "
            "near-miss/reflection diagnostics before the next approved evidence window"
            if known_targets
            else "use the bounded route-sample histogram to choose the next explicit "
            "diagnostic target set before any approved evidence window"
        ),
        "route_samples_are_promotable": False,
        "route_samples_count_as_approved_runtime_evidence": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def route_sample_next_actions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = route_sample_analysis_from_payload(payload)
    if not analysis:
        return []
    return [
        {
            "id": "review_player_principal_lifecycle_route_samples",
            "owner": "lead",
            "status": "manual_offline_review_not_executed_by_source",
            "action": analysis["recommended_next_action"],
            "action_kind": "diagnostic_route_sample_review",
            "items": ["diagnostic-route-samples/player_principal_lifecycle"],
            "diagnostic_route_sample_analysis": analysis,
            "requires_operator_authority_before_execution": False,
            "requires_current_turn_operator_approval": False,
            "server_operations_authorized": False,
            "runtime_capture_authorized": False,
            "authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        }
    ]


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
        **ZERO_PROGRESS_FLAGS,
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
            "missing_accepted_lifecycle_roles": [
                "session_start",
                "session_start_rejected",
                "session_end",
            ],
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
            "Current redacted live state is blocker context only: TheIsland has an "
            "active player but observer-only/no accepted lifecycle roles; Ragnarok "
            "has diagnostic FName drift that blocks accepted events; Genesis2 is "
            "inactive or unknown. None of this is SDK/P0 progress or approved "
            "runtime evidence."
        ),
        **source_bound_non_actions,
        **false_claims,
    }


def beta_runtime_choreography(target: dict[str, Any] | None = None) -> dict[str, Any]:
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


def route_audit_summary() -> dict[str, Any]:
    choreography = beta_runtime_choreography({"instance": "arkserver2", "map": "TheIsland"})
    current_live_blockers = current_live_diagnostic_blockers_context()
    return {
        "schema": ROUTE_AUDIT_SCHEMA,
        "status": "route_blocked_approved_runtime_evidence_missing",
        "current_blocker": "approved_runtime_evidence_missing",
        "current_source_bound_route_blocker": "source_bound_drift_blocks_accepted_lifecycle_events",
        "current_live_diagnostic_blockers": current_live_blockers,
        "source_bound_drift_blocker_is_primary_route": True,
        "waiting_for_exact_check_join_in_progress_1_0_is_fastest_valid_route": False,
        "blind_wait_or_restart_or_logout_instruction_allowed": False,
        "recommended_next_action": (
            "blocker-first: resolve or source-bind the TheIsland accepted-events=0 "
            "state and avoid Ragnarok diagnostic FName drift before requesting any "
            "candidate clean non-diagnostic fresh window"
        ),
        "candidate_only_next_action": {
            "id": "clean_theisland_fresh_window_without_diagnostics",
            "status": "candidate_only_non_evidence",
            "target_hint": {"instance": "arkserver2", "map": "TheIsland"},
            "diagnostic_candidates": "disabled",
            "blocked_by_current_source_bound_drift_context": True,
            "blind_wait_or_restart_or_logout_instruction_allowed": False,
            "beta_runtime_choreography": choreography,
            "window_requirement": (
                "fresh copied post-original sibling-set window with exact "
                "CheckJoinInProgress(1,0), one direct-join tester, no transfer/reconnect "
                "mix, not a stale/order-mismatched replay"
            ),
            "why_fastest_hypothesis": (
                "The latest clean TheIsland window emitted start/end only and still lacks "
                "the exact CheckJoinInProgress(1,0) sibling; a later Ragnarok diagnostic "
                "tail showed the exact tuple can be accepted, but that line is "
                "non-promotable stimulus only because it is not an approved sibling-set"
            ),
            "requires_separate_current_turn_operator_scope": True,
            "authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
        },
        "latest_runtime_gap_from_logs": {
            "schema": "obelisk.player-principal-lifecycle-checkjoin-runtime-gap.v1",
            "status": "blocked_no_approved_runtime_evidence",
            "planner_did_not_read_live_logs": True,
            "observations": [
                {
                    "id": "theisland_active_player_observer_only_no_accepted_lifecycle_event",
                    "target_hint": {"instance": "arkserver2", "map": "TheIsland"},
                    "players_current": 1,
                    "observer_only": True,
                    "accepted_lifecycle_event_count": 0,
                    "fresh_window": True,
                    "rejection_reason": (
                        "active player context has no accepted lifecycle roles and "
                        "cannot be promoted"
                    ),
                    "approved_runtime_evidence": False,
                    "counts_as_approved_runtime_evidence": False,
                },
                {
                    "id": "ragnarok_diagnostic_fname_drift_blocks_accepted_events",
                    "target_hint": {"instance": "arkserver", "map": "Ragnarok"},
                    "diagnostic_fname_mismatch_lines_present": True,
                    "diagnostic_fname_drift": True,
                    "rejection_reason": (
                        "diagnostic FName mismatch lines block accepted lifecycle "
                        "event classification"
                    ),
                    "approved_runtime_evidence": False,
                    "counts_as_approved_runtime_evidence": False,
                },
                {
                    "id": "theisland_clean_window_start_end_only_missing_checkjoin",
                    "target_hint": {"instance": "arkserver2", "map": "TheIsland"},
                    "observed_shapes": ["session_start", "session_end"],
                    "fresh_window": True,
                    "rejection_reason": "missing exact CheckJoinInProgress(1,0) session_start_rejected sibling",
                    "approved_runtime_evidence": False,
                    "counts_as_approved_runtime_evidence": False,
                },
                {
                    "id": "ragnarok_diagnostic_tail_exact_checkjoin_1_0_stimulus_only",
                    "target_hint": {"instance": "arkserver", "map": "Ragnarok"},
                    "observed_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
                    "fresh_window": False,
                    "diagnostic_or_tail_context": True,
                    "approved_sibling_set": False,
                    "rejection_reason": "diagnostic_non_promotable_not_approved_sibling_set",
                    "stimulus_clue_only": True,
                    "approved_runtime_evidence": False,
                    "counts_as_approved_runtime_evidence": False,
                },
                {
                    "id": "stale_or_order_mismatched_exact_checkjoin_1_0_stimulus_only",
                    "observed_shape": "CheckJoinInProgress(1,0)",
                    "fresh_window": False,
                    "approved_sibling_set": False,
                    "rejection_reason": "stale_or_order_mismatched_with_required_sibling_roles",
                    "stimulus_clue_only": True,
                    "approved_runtime_evidence": False,
                    "counts_as_approved_runtime_evidence": False,
                },
                {
                    "id": "ragnarok_fresh_window_diagnostics_checkjoin_0_0",
                    "target_hint": {"instance": "arkserver", "map": "Ragnarok"},
                    "observed_shapes": [
                        "session_start",
                        "session_end",
                        "duplicate_session_start",
                        "diagnostic_candidates",
                        "CheckJoinInProgress(0,0)",
                    ],
                    "fresh_window": True,
                    "rejection_reason": (
                        "missing exact CheckJoinInProgress(1,0) accepted observer event; "
                        "diagnostic and 0,0 material is non-evidence"
                    ),
                    "approved_runtime_evidence": False,
                    "counts_as_approved_runtime_evidence": False,
                },
            ],
            "rejected_hypotheses": [
                "active player count or observer-enable-only output can satisfy accepted lifecycle events",
                "diagnostic FName mismatch lines can be treated as accepted lifecycle events",
                "stale/order-mismatched exact CheckJoinInProgress(1,0) can be reused",
                "diagnostic/non-promotable Ragnarok exact CheckJoinInProgress(1,0) can be promoted",
                "Ragnarok fresh CheckJoinInProgress(0,0) can satisfy the rejected-start role",
                "diagnostic candidate lines can substitute for accepted copied observer events",
                "duplicate start/end-only windows can clear approved_runtime_evidence_missing",
                "mixed transfer/reconnect/logout churn in one approved window can satisfy the sibling-set",
            ],
            "candidate_only_fastest_hypothesis": "clean_theisland_fresh_window_without_diagnostics",
            "stale_or_diagnostic_exact_checkjoin_boundary": checkjoin_stimulus_boundary(),
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
        },
        "primary_missing_runtime_shape": {
            "role": "session_start_rejected",
            "target": "ShooterGameMode.CheckJoinInProgress",
            "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
            "copied_bool_values": ["1", "0"],
            "principal_action": "none",
            "apply_status": "session_start_rejected_noop",
            "correlation_status": "not_applicable",
        },
        "required_ordered_roles": [
            {
                "role": "session_start",
                "target": "ShooterGameMode.HandleNewPlayer",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "1"],
            },
            {
                "role": "session_start_rejected",
                "target": "ShooterGameMode.CheckJoinInProgress",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "principal_action": "none",
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
            {
                "role": "session_end",
                "target": "ShooterGameMode.OnLogout",
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            },
        ],
        "extra_diagnostic_shape_logging_should_be_primary_next_action": False,
        "different_map_or_tester_flow_should_be_primary_next_action": False,
        "offline_layout_or_static_discovery_should_be_primary_next_action": False,
        "clean_theisland_non_diagnostic_window_is_candidate_only_next_action": True,
        "diagnostic_candidates_should_be_disabled_for_fastest_candidate": True,
        "beta_runtime_choreography": choreography,
        "one_tester_direct_join_wait_for_exact_checkjoin_required": False,
        "one_tester_direct_join_wait_for_exact_checkjoin_candidate_only_after_blocker_clear": True,
        "mixed_transfer_reconnect_same_approved_window_allowed": False,
        "stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only": True,
        "active_player_observer_only_no_accepted_lifecycle_event_is_next_blocker": True,
        "diagnostic_fname_drift_blocks_accepted_events": True,
        "offline_planning_change_needed_for_evidence": False,
        "offline_planning_change_applied_by_this_report": (
            "route-audit metadata only; no runtime authority or evidence state changes"
        ),
        "copied_observation_rejection_is_not_evidence": True,
        "passive_or_diagnostic_material_counts_as_evidence": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def nested_dict(value: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def first_nested_dict(value: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> dict[str, Any]:
    for path in paths:
        candidate = nested_dict(value, *path)
        if candidate:
            return candidate
    return {}


def context_path(context: dict[str, Any]) -> str | None:
    for key in ("path", "source_path"):
        value = context.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def context_present(context: dict[str, Any]) -> bool:
    return bool(
        context.get("path_supplied") is True
        or context.get("present") is True
        or context_path(context)
    )


def confirmed_beta_notice_completed(context: dict[str, Any]) -> bool:
    guarded = context.get("guarded_beta_notice_action")
    guarded_dict = guarded if isinstance(guarded, dict) else {}
    return bool(
        context.get("completed") is True
        or context.get("notice_completion_accepted_by_this_report") is True
        or guarded_dict.get("real_beta_test_notice_action_completed") is True
        or (
            (context.get("mode") == "confirmed_send" or context.get("source_mode") == "confirmed_send")
            and (
                context.get("discord_sent") is True
                or context.get("source_discord_sent") is True
            )
        )
    )


def confirmed_beta_notice_standing_recorded(context: dict[str, Any]) -> bool:
    guarded = context.get("guarded_beta_notice_action")
    guarded_dict = guarded if isinstance(guarded, dict) else {}
    boundary = context.get("notice_authority_boundary")
    boundary_dict = boundary if isinstance(boundary, dict) else {}
    return bool(
        context.get("standing_launch_authority_recorded") is True
        or context.get("standing_launch_authority_satisfies_notice_scope") is True
        or guarded_dict.get("standing_launch_authority_recorded") is True
        or guarded_dict.get("standing_launch_authority_satisfies_notice_scope") is True
        or boundary_dict.get("standing_launch_authority_recorded") is True
        or boundary_dict.get("standing_launch_authority_satisfies_notice_scope") is True
    )


def player_presence_context_present(context: dict[str, Any]) -> bool:
    if not context:
        return False
    if context.get("present") is True:
        return True
    if context.get("players_detected") is True:
        return True
    if context.get("presence_detected") is True:
        return True
    if context.get("no_players_currently_detected") is True:
        return True
    for key in (
        "targets_with_players_detected",
        "known_zero_player_targets",
        "unknown_player_count_targets",
    ):
        value = context.get(key)
        if isinstance(value, list) and value:
            return True
    for key in ("known_player_counts_by_target", "players_current_by_target"):
        value = context.get(key)
        if isinstance(value, dict) and value:
            return True
    return isinstance(context.get("classification"), str)


def player_presence_targets(context: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    for key in (
        "targets_with_players_detected",
        "known_zero_player_targets",
        "unknown_player_count_targets",
    ):
        value = context.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str) and item and item not in targets:
                targets.append(item)
    for key in ("known_player_counts_by_target", "players_current_by_target"):
        value = context.get(key)
        if not isinstance(value, dict):
            continue
        for target in value:
            target_text = str(target)
            if target_text and target_text not in targets:
                targets.append(target_text)
    return sorted(targets)


def player_presence_players_detected(context: dict[str, Any]) -> bool:
    if context.get("players_detected") is True or context.get("presence_detected") is True:
        return True
    targets = context.get("targets_with_players_detected")
    if isinstance(targets, list) and targets:
        return True
    counts = context.get("known_player_counts_by_target")
    if not isinstance(counts, dict):
        counts = context.get("players_current_by_target")
    if isinstance(counts, dict):
        return any(
            isinstance(value, int) and not isinstance(value, bool) and value > 0
            for value in counts.values()
        )
    return False


def operator_context_summary(
    *,
    monitor_context: dict[str, Any],
    beta_notice_context: dict[str, Any],
    player_presence_context: dict[str, Any],
) -> dict[str, Any]:
    monitor_present = context_present(monitor_context)
    beta_present = context_present(beta_notice_context)
    player_presence_present = player_presence_context_present(player_presence_context)
    return {
        "schema": "obelisk.player-principal-lifecycle-next-action-operator-context.v1",
        "post_reboot_monitor_context_present": monitor_present,
        "post_reboot_monitor_path": context_path(monitor_context),
        "post_reboot_monitor_classification": monitor_context.get("classification")
        if isinstance(monitor_context.get("classification"), str)
        else monitor_context.get("context_kind"),
        "post_reboot_monitor_read_by_source_report": monitor_context.get("read_by_this_report")
        is True,
        "confirmed_beta_notice_context_present": beta_present,
        "confirmed_beta_notice_path": context_path(beta_notice_context),
        "confirmed_beta_notice_completed": confirmed_beta_notice_completed(beta_notice_context),
        "confirmed_beta_notice_standing_launch_authority_recorded": confirmed_beta_notice_standing_recorded(
            beta_notice_context
        ),
        "player_presence_context_present": player_presence_present,
        "player_presence_context_classification": player_presence_context.get("classification")
        if isinstance(player_presence_context.get("classification"), str)
        else player_presence_context.get("context_kind"),
        "player_presence_targets": player_presence_targets(player_presence_context),
        "player_presence_players_detected": player_presence_players_detected(player_presence_context),
        "player_presence_context_is_operator_context_only": player_presence_present,
        "player_presence_context_authorizes_runner": False,
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "context_inputs_are_operator_context_only": monitor_present or beta_present or player_presence_present,
        "context_inputs_are_non_evidence": True,
        "context_inputs_authorize_runner": False,
        **CONTEXT_FALSE_FLAGS,
    }


def payload_operator_context(payload: dict[str, Any]) -> dict[str, Any]:
    return operator_context_summary(
        monitor_context=first_nested_dict(payload, POST_REBOOT_MONITOR_CONTEXT_KEYS),
        beta_notice_context=first_nested_dict(payload, CONFIRMED_BETA_NOTICE_CONTEXT_KEYS),
        player_presence_context=first_nested_dict(payload, PLAYER_PRESENCE_CONTEXT_KEYS),
    )


def action_operator_context(action: dict[str, Any]) -> dict[str, Any]:
    monitor_context = action.get("post_reboot_monitor_context")
    beta_notice_context = action.get("confirmed_beta_notice_context")
    player_presence_context = action.get("player_presence_context")
    if not isinstance(player_presence_context, dict):
        player_presence_context = action.get("passive_player_presence")
    if not isinstance(player_presence_context, dict):
        player_presence_context = action.get("runtime_player_availability")
    return operator_context_summary(
        monitor_context=monitor_context if isinstance(monitor_context, dict) else {},
        beta_notice_context=beta_notice_context if isinstance(beta_notice_context, dict) else {},
        player_presence_context=player_presence_context if isinstance(player_presence_context, dict) else {},
    )


def combined_operator_context(
    *,
    sources: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    monitor_paths: list[str] = []
    beta_paths: list[str] = []
    player_presence_targets_seen: list[str] = []
    beta_completed = False
    beta_standing_recorded = False
    player_presence_present = False
    player_presence_players = False

    def absorb(summary: dict[str, Any]) -> None:
        nonlocal beta_completed, beta_standing_recorded, player_presence_present, player_presence_players
        monitor_path = summary.get("post_reboot_monitor_path")
        if isinstance(monitor_path, str) and monitor_path and monitor_path not in monitor_paths:
            monitor_paths.append(monitor_path)
        beta_path = summary.get("confirmed_beta_notice_path")
        if isinstance(beta_path, str) and beta_path and beta_path not in beta_paths:
            beta_paths.append(beta_path)
        beta_completed = beta_completed or summary.get("confirmed_beta_notice_completed") is True
        beta_standing_recorded = (
            beta_standing_recorded
            or summary.get("confirmed_beta_notice_standing_launch_authority_recorded") is True
        )
        player_presence_present = (
            player_presence_present
            or summary.get("player_presence_context_present") is True
        )
        player_presence_players = (
            player_presence_players
            or summary.get("player_presence_players_detected") is True
        )
        targets = summary.get("player_presence_targets")
        if isinstance(targets, list):
            for target in targets:
                if isinstance(target, str) and target and target not in player_presence_targets_seen:
                    player_presence_targets_seen.append(target)

    for source in sources:
        context = source.get("operator_context")
        if isinstance(context, dict):
            absorb(context)
    for action in actions:
        context = action.get("operator_context")
        if isinstance(context, dict):
            absorb(context)

    return {
        "schema": "obelisk.player-principal-lifecycle-next-action-context-summary.v1",
        "post_reboot_monitor_context_present": bool(monitor_paths),
        "post_reboot_monitor_paths": monitor_paths,
        "confirmed_beta_notice_context_present": bool(beta_paths),
        "confirmed_beta_notice_paths": beta_paths,
        "confirmed_beta_notice_completed": beta_completed,
        "confirmed_beta_notice_standing_launch_authority_recorded": beta_standing_recorded,
        "player_presence_context_present": player_presence_present,
        "player_presence_targets": sorted(player_presence_targets_seen),
        "player_presence_players_detected": player_presence_players,
        "player_presence_context_authorizes_runner": False,
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "context_inputs_are_operator_context_only": bool(
            monitor_paths or beta_paths or player_presence_present
        ),
        "context_inputs_are_non_evidence": True,
        "context_inputs_authorize_runner": False,
        **CONTEXT_FALSE_FLAGS,
    }


def source_standing_authority(payload: dict[str, Any]) -> bool:
    if payload.get("standing_launch_authority_recorded") is True:
        return True
    if payload.get("standing_debug_authority_recorded") is True:
        return True
    if nested_dict(payload, "standing_launch_authority").get("recorded") is True:
        return True
    if nested_dict(payload, "external_execution_authority").get("standing_launch_authority_recorded") is True:
        return True
    if nested_dict(payload, "notice_authority_boundary").get("standing_launch_authority_recorded") is True:
        return True
    if nested_dict(payload, "authority_boundary").get("standing_launch_authority_recorded") is True:
        return True
    if (
        nested_dict(payload, "operator_action_summary", "recorded_standing_debug_authority").get("recorded")
        is True
    ):
        return True
    return False


def action_requires_fresh_operator_authority(action: dict[str, Any]) -> bool:
    source_required = action.get("operator_authority_source_required")
    return bool(
        action.get("requires_current_turn_operator_approval") is True
        or action.get("requires_fresh_current_turn_operator_approval") is True
        or source_required in FRESH_OPERATOR_AUTHORITY_SOURCES
    )


def action_has_exact_standing_scope(action: dict[str, Any]) -> bool:
    source_required = action.get("operator_authority_source_required")
    authority_source = action.get("authority_source")
    if source_required in STANDING_AUTHORITY_SOURCES:
        return True
    if authority_source in STANDING_AUTHORITY_SOURCES and action.get("separate_operator_authorization_required") is False:
        return True
    if (
        action.get("standing_launch_authority_covers_target_run") is True
        and action.get("standing_launch_authority_satisfies_operator_approval") is not False
    ):
        return True
    if action.get("recorded_standing_launch_authority_satisfies_scope") is True:
        return True
    if action.get("recorded_standing_debug_authority_satisfies_scope") is True:
        return True
    if action.get("consumable_under_recorded_standing_launch_authority") is True:
        return True
    if (
        (
            action.get("allowed_under_recorded_standing_authority") is True
            or action.get("allowed_under_recorded_standing_debug_authority") is True
        )
        and action.get("requires_exact_run_target_and_recorded_safety_limits") is True
    ):
        return True
    return False


def source_target(payload: dict[str, Any]) -> dict[str, Any] | None:
    target = payload.get("target")
    return target if isinstance(target, dict) else None


def source_run_id(payload: dict[str, Any]) -> str | None:
    run_id = payload.get("run_id")
    if isinstance(run_id, str) and run_id:
        return run_id
    summary = payload.get("operator_action_summary")
    if isinstance(summary, dict):
        candidate = summary.get("run_id")
        if isinstance(candidate, str) and candidate:
            return candidate
    evidence_dir = payload.get("evidence_dir")
    if isinstance(evidence_dir, str) and evidence_dir:
        return Path(evidence_dir).name
    return None


def action_items_for_payload(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    schema = payload.get("schema")
    if schema == RUNTIME_EXECUTION_SCHEMA:
        return "next_action_sequence", list_of_dicts(payload.get("next_action_sequence"))
    if schema == ACTIVATION_PRECONDITIONS_SCHEMA:
        actions = list_of_dicts(payload.get("activation_next_action_sequence"))
        if not actions:
            actions = list_of_dicts(payload.get("next_action_sequence"))
        return "activation_next_action_sequence", actions
    if schema == BETA_NOTICE_SCHEMA:
        return "next_action_sequence", list_of_dicts(payload.get("next_action_sequence"))
    if schema == RUNTIME_EVIDENCE_STATUS_SCHEMA:
        machine_actions = list_of_dicts(payload.get("machine_next_actions"))
        if machine_actions:
            return "machine_next_actions", machine_actions
        summary_actions = list_of_dicts(
            nested_dict(payload, "operator_action_summary").get(
                "actions_allowed_under_recorded_standing_debug_authority"
            )
        )
        if summary_actions:
            return "operator_action_summary.actions_allowed_under_recorded_standing_debug_authority", summary_actions
        return "next_actions", list_of_dicts(payload.get("next_actions"))
    if schema == CLOSURE_REQUEST_SCHEMA:
        machine_actions = list_of_dicts(payload.get("machine_next_actions"))
        if machine_actions:
            return "machine_next_actions", machine_actions
        return "exact_missing_operations", list_of_dicts(payload.get("exact_missing_operations"))
    if schema == OBSERVER_LOG_SUMMARY_SCHEMA:
        return "diagnostic_route_sample_next_actions", route_sample_next_actions(payload)
    raise SystemExit(f"unsupported source schema {schema!r}")


def list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def normalized_action_id(raw: Any, fallback: str) -> str:
    if isinstance(raw, str) and raw:
        normalized = normalized_key(raw)
        if normalized:
            return normalized
    return fallback


def normalized_status(action: dict[str, Any]) -> str:
    status = action.get("status")
    if isinstance(status, str) and status:
        return status
    if action.get("authorized_by_this_report") is False:
        return "manual_external_not_executed_by_source"
    return "manual_external_not_executed_by_source"


def normalize_action(
    *,
    action: dict[str, Any],
    source_payload: dict[str, Any],
    source_index: int,
    source_path: Path,
    source_sha256: str,
    source_schema: str,
    source_action_key: str,
    source_run_id_value: str | None,
    source_target_value: dict[str, Any] | None,
    source_standing_recorded: bool,
    source_order: int,
    global_order: int,
) -> dict[str, Any]:
    raw_id = action.get("id") or action.get("action_id") or action.get("action") or action.get("operation")
    action_text = action.get("action") or action.get("operation") or action.get("description") or raw_id
    if not isinstance(action_text, str) or not action_text:
        action_text = "review_source_next_action"

    stale_prevention = runtime_window_stale_prevention_for_action(
        action=action,
        source_payload=source_payload,
        source_run_id_value=source_run_id_value,
    )
    stale_action_blocked = stale_prevention.get("request_window_stale_or_too_late") is True
    notice_sequence = beta_notice_sequence_enforcement_for_action(
        action=action,
        stale_prevention=stale_prevention,
    )
    fresh_authority_required = action_requires_fresh_operator_authority(action)
    standing_scope_represented = action_has_exact_standing_scope(action)
    allowed_under_standing_authority = (
        source_standing_recorded
        and standing_scope_represented
        and not fresh_authority_required
        and not stale_action_blocked
    )
    separate_auth = action.get("separate_operator_authorization_required")
    if stale_action_blocked:
        separate_auth = True
    elif fresh_authority_required and not allowed_under_standing_authority:
        separate_auth = True
    elif isinstance(separate_auth, bool):
        separate_auth = separate_auth
    elif action.get("requires_operator_authority_before_execution") is False:
        separate_auth = False
    elif allowed_under_standing_authority:
        separate_auth = False
    else:
        separate_auth = True
    command_text = action.get("command_text_not_executed")
    validation_command_text = action.get("validation_command_text_not_executed")
    runner_command = action.get("runner_command")
    runner_operation = action.get("runner_operation")
    blocked_until = action.get("blocked_until")
    operator_context = action_operator_context(action)

    normalized = {
        "order": global_order,
        "id": normalized_action_id(raw_id, f"source_{source_index}_action_{source_order}"),
        "owner": action.get("owner") if isinstance(action.get("owner"), str) else "lead",
        "status": normalized_status(action),
        "action": action_text,
        "items": string_list(action.get("items")),
        "target": action.get("target") if isinstance(action.get("target"), dict) else source_target_value,
        "run_id": source_run_id_value,
        "source": {
            "index": source_index,
            "path": str(source_path),
            "sha256": source_sha256,
            "schema": source_schema,
            "action_key": source_action_key,
            "source_order": action.get("order") if isinstance(action.get("order"), int) else source_order,
        },
        "source_json_path": str(source_path),
        "source_json_sha256": source_sha256,
        "authority_source": (
            action.get("authority_source")
            if isinstance(action.get("authority_source"), str)
            else (
                "recorded_standing_launch_authority"
                if source_standing_recorded
                else "fresh_current_turn_operator_scope"
            )
        ),
        "recorded_standing_authority_observed": source_standing_recorded,
        "standing_authority_scope_represented_for_action": standing_scope_represented,
        "standing_authority_fresh_message_still_required_for_action": fresh_authority_required,
        "allowed_operator_context_under_recorded_standing_authority": (
            source_standing_recorded and standing_scope_represented and not stale_action_blocked
        ),
        "allowed_under_recorded_standing_authority": allowed_under_standing_authority,
        "standing_authority_is_operator_context_only": source_standing_recorded,
        "standing_authority_authorizes_this_plan": False,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "standing_authority_counts_as_runtime_evidence": False,
        "standing_authority_counts_as_sdk_evidence": False,
        "standing_authority_counts_toward_sdk": False,
        "standing_authority_counts_toward_p0_dependency_chain": False,
        "separate_operator_authorization_required": separate_auth,
        "authorized_by_this_report": False,
        "server_operations_authorized_by_this_report": False,
        "runtime_work_authorized_by_this_report": False,
        "marker_env_changes_authorized_by_this_report": False,
        "workspace_writes_authorized_by_this_report": False,
        "discord_authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "grants_readiness_claims": False,
        **ZERO_PROGRESS_FLAGS,
        "approved_window": stale_prevention.get("approved_window"),
        "runtime_window_stale_prevention": stale_prevention,
        "runtime_window_stale_or_too_late": stale_action_blocked,
        "runtime_window_stale_blockers": string_list(stale_prevention.get("blockers")),
        "beta_notice_sequence_enforcement": notice_sequence,
        "beta_runtime_choreography": beta_runtime_choreography(
            action.get("target") if isinstance(action.get("target"), dict) else source_target_value
        ),
        "beta_notice_dry_run_required_before_activation": True,
        "confirmed_beta_notice_required_before_activation": True,
        "confirmed_send_must_complete_before_window_start": True,
        "activation_preconditions_required_before_activation_or_restart": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "non_authorization": NON_AUTHORIZATION,
    }
    for key in (
        "artifact",
        "role",
        "action_kind",
        "missing_kind",
        "blocker",
        "missing_artifact_blocker_reason",
        "command_status",
        "validation_command_status",
        "next_status_input_needed",
        "status_report_source",
        "accepted_input_only",
        "notice_path",
        "operator_authority_source_required",
        "standing_launch_authority_receipt_path",
        "process_control",
        "restart_expectation",
        "user_policy",
        "source_evidence_dir",
        "invalid_source_evidence_dir",
        "source_root_role",
        "source_run_id",
        "closure_compatible_evidence_dir",
        "suggested_closure_evidence_dir",
        "suggested_valid_closure_run_id",
        "suggested_valid_closure_evidence_dir",
        "suggested_valid_closure_root_role",
        "required_script",
        "copied_log_path",
        "window_manifest_path",
        "preflight_post_path",
        "approved_runtime_evidence_json_path",
        "approved_runtime_principal_lifecycle_evidence_bundle_json",
        "first_missing_artifact",
        "first_missing_runtime_evidence_path",
        "next_action_target",
        "command_text_not_emitted",
    ):
        if isinstance(action.get(key), str):
            normalized[key] = action[key]
    if isinstance(action.get("source"), str):
        normalized["source_action_origin"] = action["source"]
    if isinstance(action.get("blocking"), bool):
        normalized["blocking"] = action["blocking"]
    if isinstance(action.get("notes"), list):
        normalized["notes"] = [item for item in action["notes"] if isinstance(item, str)]
    for key in (
        "post_reboot_monitor_context",
        "confirmed_beta_notice_context",
        "after_completion",
        "runner_contract",
        "non_evidence_context",
        "source_log_not_ready",
        "observer_only_no_role_window",
        "copy_ready_log_context",
        "runtime_window_lifecycle",
        "fresh_player_backed_window",
        "diagnostic_candidates",
        "no_users_passive_wait",
        "passive_player_presence",
        "player_presence_context",
        "next_player_backed_window",
        "player_warning_broadcast_recommendation",
        "passive_wait_boundary",
        "player_presence_safety",
        "closure_compatible_copy_guidance",
        "after_manual_staging",
        "invalid_source_boundary",
        "runtime_evidence_artifact_blockers",
        "missing_artifact_blocker",
        "exact_triplet_bundle_route",
        "current_live_diagnostic_blockers",
        "diagnostic_route_sample_analysis",
        "command_path_binding",
        "validation_command_path_binding",
    ):
        if isinstance(action.get(key), dict):
            normalized[key] = action[key]
    for key in (
        "manual_offline_next_steps",
        "deferred_missing_role_offline_next_steps",
        "parallel_offline_next_steps",
        "deferred_missing_artifact_actions",
        "missing_artifact_reasons",
        "blocked_until",
    ):
        if isinstance(action.get(key), list):
            normalized[key] = [item for item in action[key] if isinstance(item, str)]
    for key in (
        "missing_artifact_blockers",
        "fastest_exact_path_from_fresh_copied_lifecycle_window",
        "fastest_missing_role_artifact_path",
    ):
        if isinstance(action.get(key), list):
            normalized[key] = [item for item in action[key] if isinstance(item, dict)]
    if (
        operator_context["post_reboot_monitor_context_present"]
        or operator_context["confirmed_beta_notice_context_present"]
        or operator_context["player_presence_context_present"]
    ):
        normalized["operator_context"] = operator_context
    for key in (
        "evidence_dir",
        "copied_evidence_dir",
        "copied_log_path",
        "manifest_path",
        "approved_bundle_path",
    ):
        if isinstance(action.get(key), str):
            normalized[key] = action[key]
    if isinstance(command_text, str) and command_text:
        normalized["command_text_not_executed"] = command_text
    if isinstance(validation_command_text, str) and validation_command_text:
        normalized["validation_command_text_not_executed"] = validation_command_text
    if isinstance(runner_command, dict):
        normalized["runner_command"] = runner_command
    if isinstance(runner_operation, dict):
        normalized["runner_operation"] = runner_operation
    if isinstance(action.get("validation_runner_command"), dict):
        normalized["validation_runner_command"] = action["validation_runner_command"]
    for key in (
        "writes_under_evidence_dir",
        "writes_under_server_root",
        "requires_operator_authority_before_execution",
        "requires_current_turn_operator_approval",
        "requires_fresh_current_turn_operator_approval",
        "requires_bound_standing_launch_authority_receipt_before_execution",
        "standing_launch_authority_covers_target_run",
        "standing_launch_authority_satisfies_operator_approval",
        "accepted_checker_required_before_status_claim",
        "required_before_activation",
        "must_be_real_notice_not_documentation",
        "reads_live_logs",
        "runtime_capture_authorized",
        "no_users_detected",
        "passive_wait_preferred",
        "repeated_restart_for_no_users_forbidden",
        "restart_recommended",
        "start_or_restart_recommended",
        "diagnostic_candidates_recommended",
        "should_enable_diagnostic_candidates_in_next_request_pack",
        "broadcast_recommended_if_players_connected",
        "cancel_or_reschedule_if_players_remain_connected",
        "source_root_valid_for_closure",
        "source_looks_like_passive_monitor_root",
        "source_accepted_as_closure_evidence_dir",
        "source_becomes_closure_root",
        "passive_monitor_root_accepted_as_closure_evidence_dir",
        "copy_or_stage_into_closure_compatible_run_required_before_closure",
        "explicit_execution_write_flags_required",
        "machine_action_suggested_for_invalid_passive_root",
        "machine_executable",
        "runner_command_available",
        "manual_staging_required_before_machine_actions",
        "sibling_artifact_generation_deferred_until_source_log_ready",
        "copy_ready_log_is_operational_only",
        "source_log_ready_to_copy",
        "source_log_closure_counts_as_evidence",
        "expired_runtime_window_non_evidence",
        "active_runtime_window_waiting_for_exact_triplet",
        "active_window_not_closure_ready",
        "prepare_fresh_player_backed_window_required",
        "copy_bundle_commands_suppressed_until_exact_triplet",
        "copy_bundle_commands_allowed_before_exact_triplet",
        "exact_accepted_triplet_required_before_copy_bundle",
        "partial_lifecycle_material_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "stale_passive_tail_counts_as_approved_runtime_evidence",
        "direct_discord_send_counts_as_approved_runtime_evidence",
        "active_notice_state_counts_as_approved_runtime_evidence",
        "diagnostic_samples_count_as_approved_runtime_evidence",
        "command_path_hash_bound",
    ):
        if isinstance(action.get(key), bool):
            normalized[key] = action[key]
    fanout = offline_parallel_evidence_lanes_for_action(normalized)
    if fanout["present"]:
        normalized["offline_parallel_evidence_lanes"] = fanout
    return normalized


def offline_parallel_lane(
    *,
    lane_id: str,
    status: str,
    scripts: list[str],
    waits_for: list[str] | None = None,
    surfaces: list[str] | None = None,
) -> dict[str, Any]:
    lane: dict[str, Any] = {
        "id": lane_id,
        "status": status,
        "scripts": scripts,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        **ZERO_PROGRESS_FLAGS,
        "runner_command_available": False,
        "runner_must_not_execute_lane": True,
        "non_authorization": NON_AUTHORIZATION,
    }
    if waits_for is not None:
        lane["waits_for"] = waits_for
    if surfaces is not None:
        lane["surfaces"] = surfaces
    return lane


def offline_parallel_evidence_lanes_for_action(action: dict[str, Any]) -> dict[str, Any]:
    runtime_lifecycle = nested_dict(action, "runtime_window_lifecycle")
    expired = (
        action.get("expired_runtime_window_non_evidence") is True
        or action.get("action_kind") == "expired_runtime_window_non_evidence_closure"
        or runtime_lifecycle.get("close_or_classify_as_non_evidence") is True
    )
    active = (
        action.get("active_runtime_window_waiting_for_exact_triplet") is True
        or action.get("action_kind") == "active_runtime_window_waiting_for_exact_triplet"
        or runtime_lifecycle.get("active_waiting_not_closure_ready") is True
    )
    present = expired or active
    lanes = [
        offline_parallel_lane(
            lane_id="runtime_evidence_closure_status",
            status="prepared_offline_after_copied_log_only",
            scripts=[
                "scripts/report_player_principal_lifecycle_runtime_evidence_status.py",
                "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py",
            ],
            waits_for=["copied Obelisk.log", "same-window sibling sidecars"],
        ),
        offline_parallel_lane(
            lane_id="single_player_multi_surface_candidate_pack",
            status="prepared_candidate_only_same_window",
            scripts=[
                "scripts/plan_obelisk_multi_surface_beta_capture.py",
                "scripts/prepare_obelisk_multi_surface_beta_capture_pack.py",
            ],
            surfaces=[
                "player_principal_lifecycle",
                "permissions_admin",
                "command_chat_response",
                "commands_replies",
                "dino_scalar",
                "tribe_scalar",
                "buff_status",
                "inventory",
                "item",
                "transfer",
                "mission",
            ],
        ),
        offline_parallel_lane(
            lane_id="post_runtime_identity_public_contract_gate",
            status="pre_hardened_waiting_for_approved_runtime_evidence",
            scripts=[
                "scripts/check_player_identity_public_contract_gap_report.py",
                "scripts/check_player_identity_public_contract_readiness.py",
            ],
            waits_for=["approved_runtime_principal_lifecycle_evidence_bundle"],
        ),
        offline_parallel_lane(
            lane_id="post_identity_p0_chain_certificates",
            status="pre_hardened_waiting_for_identity_public_contract",
            scripts=[
                "scripts/build_permissions_admin_promotion_certificate.py",
                "scripts/build_command_chat_response_promotion_certificate.py",
                "scripts/build_commands_replies_promotion_certificate.py",
            ],
            waits_for=["obelisk.player_identity.v1"],
        ),
    ]
    return {
        "schema": OFFLINE_PARALLEL_EVIDENCE_LANES_SCHEMA,
        "present": present,
        "classification": (
            "post_window_non_evidence_fanout_prepare_fresh_player_backed_window"
            if expired
            else "active_window_parallel_offline_preparation_waiting_for_exact_triplet"
            if active
            else "no_runtime_window_parallel_offline_lanes"
        ),
        "runtime_window_state": "expired_non_evidence" if expired else "active_waiting" if active else "none",
        "primary_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_primary_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "parallel_lane_count": len(lanes) if present else 0,
        "lanes": lanes if present else [],
        "runner_command_available": False,
        "runner_must_not_execute_lanes": True,
        "live_ops_authorized_by_this_plan": False,
        "discord_authorized_by_this_plan": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        **ZERO_PROGRESS_FLAGS,
        "non_authorization": NON_AUTHORIZATION,
    }


def source_summary(
    *,
    index: int,
    path: Path,
    sha256: str,
    payload: dict[str, Any],
    action_key: str,
    action_count: int,
    standing_recorded: bool,
) -> dict[str, Any]:
    return {
        "index": index,
        "path": str(path),
        "sha256": sha256,
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "ready": payload.get("ready") is True,
        "run_id": source_run_id(payload),
        "target": source_target(payload),
        "next_blocker": payload.get("next_blocker"),
        "action_key": action_key,
        "action_count": action_count,
        "recorded_standing_authority_observed": standing_recorded,
        "operator_context": payload_operator_context(payload),
    }


def observer_only_no_role_plan_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    no_role_actions = [
        action
        for action in actions
        if action.get("action_kind") == "observer_only_no_role_window_closure"
        or nested_dict(action, "source_log_not_ready").get(
            "active_observer_only_no_role_window"
        )
        is True
    ]
    active_ids = [
        str(action.get("id"))
        for action in no_role_actions
        if action.get("action_kind") == "active_runtime_window_waiting_for_exact_triplet"
        or action.get("active_runtime_window_waiting_for_exact_triplet") is True
    ]
    expired_ids = [
        str(action.get("id"))
        for action in no_role_actions
        if action.get("action_kind") == "expired_runtime_window_non_evidence_closure"
        or action.get("expired_runtime_window_non_evidence") is True
    ]
    return {
        "schema": "obelisk.player-principal-lifecycle-observer-only-no-role-plan.v1",
        "present": bool(no_role_actions),
        "action_ids": [str(action.get("id")) for action in no_role_actions],
        "classification": (
            "active_observer_only_no_role_window_waiting_not_closure_ready"
            if active_ids
            else "close_observer_only_no_role_window_as_non_evidence"
            if expired_ids or no_role_actions
            else "no_observer_only_no_role_window_action"
        ),
        "active_window_action_ids": active_ids,
        "expired_window_action_ids": expired_ids,
        "target_hints": [
            action["target"]
            for action in no_role_actions
            if isinstance(action.get("target"), dict)
        ],
        "manual_offline_next_steps": (
            no_role_actions[0].get("manual_offline_next_steps", [])
            if no_role_actions
            else []
        ),
        "sibling_artifact_generation_deferred_until_source_log_ready": any(
            action.get("sibling_artifact_generation_deferred_until_source_log_ready") is True
            for action in no_role_actions
        ),
        "planner_keeps_copied_log_readiness_operational_only": True,
        "authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
    }


def runtime_window_lifecycle_plan_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    lifecycle_actions = [
        action
        for action in actions
        if action.get("action_kind")
        in {
            "expired_runtime_window_non_evidence_closure",
            "active_runtime_window_waiting_for_exact_triplet",
        }
        or isinstance(action.get("runtime_window_lifecycle"), dict)
    ]
    expired_ids = [
        str(action.get("id"))
        for action in lifecycle_actions
        if action.get("expired_runtime_window_non_evidence") is True
        or action.get("action_kind") == "expired_runtime_window_non_evidence_closure"
        or nested_dict(action, "runtime_window_lifecycle").get(
            "close_or_classify_as_non_evidence"
        )
        is True
    ]
    active_ids = [
        str(action.get("id"))
        for action in lifecycle_actions
        if action.get("active_runtime_window_waiting_for_exact_triplet") is True
        or action.get("action_kind") == "active_runtime_window_waiting_for_exact_triplet"
        or nested_dict(action, "runtime_window_lifecycle").get(
            "active_waiting_not_closure_ready"
        )
        is True
    ]
    return {
        "schema": "obelisk.player-principal-lifecycle-runtime-window-lifecycle-plan.v1",
        "present": bool(lifecycle_actions),
        "classification": (
            "expired_non_evidence_windows_prepare_fresh_player_backed_window"
            if expired_ids
            else "active_windows_waiting_not_closure_ready"
            if active_ids
            else "no_runtime_window_lifecycle_action"
        ),
        "action_ids": [str(action.get("id")) for action in lifecycle_actions],
        "expired_non_evidence_action_ids": expired_ids,
        "active_waiting_action_ids": active_ids,
        "copy_bundle_commands_suppressed_until_exact_triplet": any(
            action.get("copy_bundle_commands_suppressed_until_exact_triplet") is True
            or nested_dict(action, "runtime_window_lifecycle").get(
                "copy_bundle_commands_suppressed_until_exact_triplet"
            )
            is True
            for action in lifecycle_actions
        ),
        "fresh_player_backed_window_required": bool(expired_ids),
        "active_windows_remain_waiting": bool(active_ids),
        "runner_command_available": False,
        "authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
    }


def offline_parallel_evidence_lanes_plan_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    lane_actions = [
        action
        for action in actions
        if nested_dict(action, "offline_parallel_evidence_lanes").get("present") is True
    ]
    lane_ids: list[str] = []
    classifications: list[str] = []
    for action in lane_actions:
        lanes = nested_dict(action, "offline_parallel_evidence_lanes")
        classification = lanes.get("classification")
        if isinstance(classification, str) and classification not in classifications:
            classifications.append(classification)
        for lane in lanes.get("lanes", []):
            if isinstance(lane, dict) and isinstance(lane.get("id"), str):
                lane_id = lane["id"]
                if lane_id not in lane_ids:
                    lane_ids.append(lane_id)
    return {
        "schema": OFFLINE_PARALLEL_EVIDENCE_LANES_SCHEMA,
        "present": bool(lane_actions),
        "classification": (
            "parallel_offline_lanes_prepared_no_runtime_evidence"
            if lane_actions
            else "no_parallel_offline_lanes"
        ),
        "action_ids": [str(action.get("id")) for action in lane_actions],
        "lane_ids": lane_ids,
        "lane_classifications": classifications,
        "primary_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_primary_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "runner_command_available": False,
        "runner_must_not_execute_lanes": True,
        "live_ops_authorized_by_this_plan": False,
        "discord_authorized_by_this_plan": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **ZERO_PROGRESS_FLAGS,
        "non_authorization": NON_AUTHORIZATION,
    }


def runtime_evidence_artifact_plan_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    action_ids: list[str] = []
    for action in actions:
        action_id = str(action.get("id"))
        direct = action.get("missing_artifact_blocker")
        if isinstance(direct, dict):
            blockers.append({**direct, "action_id": action_id})
            action_ids.append(action_id)
        nested = action.get("missing_artifact_blockers")
        if isinstance(nested, list):
            for item in nested:
                if isinstance(item, dict):
                    blockers.append({**item, "action_id": action_id})
                    if action_id not in action_ids:
                        action_ids.append(action_id)
    first = blockers[0] if blockers else None
    return {
        "schema": "obelisk.player-principal-lifecycle-runtime-evidence-artifact-plan.v1",
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
        "approved_runtime_principal_lifecycle_evidence_bundle_ready": False,
        "authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **ZERO_PROGRESS_FLAGS,
        "non_authorization": NON_AUTHORIZATION,
    }


def exact_triplet_bundle_plan_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    routes = [
        action["exact_triplet_bundle_route"]
        for action in actions
        if isinstance(action.get("exact_triplet_bundle_route"), dict)
        and action["exact_triplet_bundle_route"]
    ]
    first = routes[0] if routes else {}
    return {
        "schema": "obelisk.player-principal-lifecycle-exact-triplet-bundle-plan.v1",
        "present": bool(routes),
        "action_ids": [
            str(action.get("id"))
            for action in actions
            if isinstance(action.get("exact_triplet_bundle_route"), dict)
            and action["exact_triplet_bundle_route"]
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
        "planner_accepts_partial_lifecycle_material_as_evidence": False,
        "planner_accepts_copied_log_presence_as_evidence": False,
        "planner_accepts_stale_passive_tail_as_evidence": False,
        "planner_accepts_direct_discord_send_as_evidence": False,
        "planner_accepts_active_notice_state_as_evidence": False,
        "planner_accepts_diagnostic_samples_as_evidence": False,
        "helper_command_authorized_by_plan": False,
        "authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **ZERO_PROGRESS_FLAGS,
        "non_authorization": NON_AUTHORIZATION,
    }


def route_sample_plan_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    analyses = [
        action["diagnostic_route_sample_analysis"]
        for action in actions
        if isinstance(action.get("diagnostic_route_sample_analysis"), dict)
    ]
    known_targets: list[dict[str, Any]] = []
    known_target_names: list[str] = []
    unknown_counts: dict[str, int] = {}
    total_samples = 0
    budget_reached = False
    missing_roles: list[str] = []
    for analysis in analyses:
        total_samples += int_value(analysis.get("sample_count"))
        budget_reached = budget_reached or analysis.get("budget_reached") is True
        for target in analysis.get("observed_known_lifecycle_targets", []):
            if not isinstance(target, dict):
                continue
            known_targets.append(target)
            target_name = target.get("target")
            if isinstance(target_name, str) and target_name not in known_target_names:
                known_target_names.append(target_name)
        counts = analysis.get("unknown_fname_index_counts")
        if isinstance(counts, dict):
            for fname_index, count in counts.items():
                numeric_count = int_value(count)
                if numeric_count > 0:
                    unknown_counts[str(fname_index)] = (
                        unknown_counts.get(str(fname_index), 0) + numeric_count
                    )
        for role in string_list(analysis.get("missing_lifecycle_event_roles")):
            if role not in missing_roles:
                missing_roles.append(role)

    return {
        "schema": "obelisk.player-principal-lifecycle-route-sample-plan.v1",
        "present": bool(analyses),
        "classification": (
            "diagnostic_route_samples_present_non_evidence"
            if analyses
            else "no_diagnostic_route_samples"
        ),
        "action_ids": [
            str(action.get("id"))
            for action in actions
            if isinstance(action.get("diagnostic_route_sample_analysis"), dict)
        ],
        "sample_count": total_samples,
        "budget_reached": budget_reached,
        "observed_known_lifecycle_targets": known_targets,
        "observed_known_lifecycle_target_names": sorted(known_target_names),
        "unknown_fname_index_counts": dict(sorted(unknown_counts.items())),
        "missing_lifecycle_event_roles": missing_roles,
        "recommended_next_action": (
            "review diagnostic route samples offline, then choose a bounded "
            "near-miss/reflection diagnostic target before any approved evidence window"
            if analyses
            else "none"
        ),
        "route_samples_are_promotable": False,
        "authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **ZERO_PROGRESS_FLAGS,
        "non_authorization": NON_AUTHORIZATION,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    normalized_actions: list[dict[str, Any]] = []
    blockers: list[str] = []
    standing_observed = False
    current_live_blockers = current_live_diagnostic_blockers_context()

    for source_index, source_arg in enumerate(args.source_json, start=1):
        path, payload, sha256 = load_json(source_arg, f"--source-json[{source_index}]")
        schema = payload.get("schema")
        if schema not in SUPPORTED_SCHEMAS:
            raise SystemExit(
                f"--source-json[{source_index}] has unsupported schema {schema!r}; "
                "supply executor, activation, beta notice, runtime evidence status, or closure JSON"
            )
        shortcut_matches = collect_shortcut_aliases(payload)
        if shortcut_matches:
            preview = ", ".join(shortcut_matches[:8])
            if len(shortcut_matches) > 8:
                preview = f"{preview}, ..."
            raise SystemExit(
                f"--source-json[{source_index}] contains runtime-evidence/readiness shortcut aliases: "
                f"{preview}"
            )

        source_current_live_blockers = payload.get("current_live_diagnostic_blockers")
        if isinstance(source_current_live_blockers, dict):
            current_live_blockers = {
                **current_live_diagnostic_blockers_context(),
                **source_current_live_blockers,
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
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                **ZERO_PROGRESS_FLAGS,
            }

        standing_recorded = source_standing_authority(payload)
        standing_observed = standing_observed or standing_recorded
        action_key, actions = action_items_for_payload(payload)
        sources.append(
            source_summary(
                index=source_index,
                path=path,
                sha256=sha256,
                payload=payload,
                action_key=action_key,
                action_count=len(actions),
                standing_recorded=standing_recorded,
            )
        )
        if not actions:
            blockers.append(f"source_{source_index}_has_no_next_actions")
        for source_order, action in enumerate(actions, start=1):
            normalized_actions.append(
                normalize_action(
                    action=action,
                    source_payload=payload,
                    source_index=source_index,
                    source_path=path,
                    source_sha256=sha256,
                    source_schema=str(schema),
                    source_action_key=action_key,
                    source_run_id_value=source_run_id(payload),
                    source_target_value=source_target(payload),
                    source_standing_recorded=standing_recorded,
                    source_order=source_order,
                    global_order=len(normalized_actions) + 1,
                )
            )

    if not normalized_actions and not blockers:
        blockers.append("no_next_actions_found")

    first_action = normalized_actions[0] if normalized_actions else None
    context_summary = combined_operator_context(sources=sources, actions=normalized_actions)
    observer_only_summary = observer_only_no_role_plan_summary(normalized_actions)
    runtime_window_lifecycle_summary = runtime_window_lifecycle_plan_summary(normalized_actions)
    offline_lanes_summary = offline_parallel_evidence_lanes_plan_summary(normalized_actions)
    artifact_summary = runtime_evidence_artifact_plan_summary(normalized_actions)
    triplet_bundle_summary = exact_triplet_bundle_plan_summary(normalized_actions)
    route_sample_summary = route_sample_plan_summary(normalized_actions)
    route_audit = route_audit_summary()
    route_audit["current_live_diagnostic_blockers"] = current_live_blockers
    route_audit["route_sample_plan_summary"] = route_sample_summary
    choreography_target = (
        first_action.get("target")
        if isinstance(first_action, dict) and isinstance(first_action.get("target"), dict)
        else None
    )
    choreography = beta_runtime_choreography(choreography_target)
    actions_allowed_under_standing = [
        action
        for action in normalized_actions
        if action.get("allowed_under_recorded_standing_authority") is True
    ]
    stale_or_too_late_actions = [
        action
        for action in normalized_actions
        if action.get("runtime_window_stale_or_too_late") is True
    ]
    stale_action_ids = [str(action.get("id")) for action in stale_or_too_late_actions]
    return {
        "schema": SCHEMA,
        "status": "next_actions_planned" if normalized_actions else "blocked_no_supported_next_actions",
        "ready": False,
        **FALSE_FLAGS,
        **ZERO_PROGRESS_FLAGS,
        "route_audit": route_audit,
        "current_live_diagnostic_blockers": current_live_blockers,
        "beta_runtime_choreography": choreography,
        "checkjoin_stimulus_boundary": checkjoin_stimulus_boundary(),
        "source_count": len(sources),
        "sources": sources,
        "blockers": blockers,
        "action_count": len(normalized_actions),
        "stale_or_too_late_action_count": len(stale_or_too_late_actions),
        "stale_or_too_late_action_ids": stale_action_ids,
        "runtime_window_stale_prevention_summary": {
            "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
            "classification": "stale_or_too_late_actions_blocked_for_activation_restart",
            "action_ids": stale_action_ids,
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "prepared_actions_count_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        },
        "observer_only_no_role_window_summary": observer_only_summary,
        "runtime_window_lifecycle_summary": runtime_window_lifecycle_summary,
        "offline_parallel_evidence_lanes_summary": offline_lanes_summary,
        "runtime_evidence_artifact_plan_summary": artifact_summary,
        "exact_triplet_bundle_plan_summary": triplet_bundle_summary,
        "route_sample_plan_summary": route_sample_summary,
        "first_action_id": first_action.get("id") if first_action else None,
        "next_action_sequence": normalized_actions,
        "operator_context_summary": context_summary,
        "action_plan": {
            "schema": "obelisk.player-principal-lifecycle-normalized-action-queue.v1",
            "source_count": len(sources),
            "action_count": len(normalized_actions),
            "next_blocker": first_action.get("id") if first_action else "no_next_actions_found",
            "recorded_standing_authority_observed": standing_observed,
            "recorded_standing_authority_is_operator_context_only": standing_observed,
            "external_actions_may_use_recorded_authority_for_exact_scope": bool(
                actions_allowed_under_standing
            ),
            "external_action_count_with_exact_standing_scope": len(actions_allowed_under_standing),
            "stale_or_too_late_action_count": len(stale_or_too_late_actions),
            "stale_or_too_late_action_ids": stale_action_ids,
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "separate_operator_authorization_required": (
                any(action["separate_operator_authorization_required"] for action in normalized_actions)
                if normalized_actions
                else not standing_observed
            ),
            "authorized_by_this_report": False,
            "server_operations_authorized_by_this_report": False,
            "runtime_work_authorized_by_this_report": False,
            "marker_env_changes_authorized_by_this_report": False,
            "workspace_writes_authorized_by_this_report": False,
            "discord_authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "grants_readiness_claims": False,
            **ZERO_PROGRESS_FLAGS,
            "route_audit": route_audit,
            "current_live_diagnostic_blockers": current_live_blockers,
            "beta_runtime_choreography": choreography,
            "checkjoin_stimulus_boundary": checkjoin_stimulus_boundary(),
            "operator_context_summary": context_summary,
            "observer_only_no_role_window_summary": observer_only_summary,
            "runtime_window_lifecycle_summary": runtime_window_lifecycle_summary,
            "offline_parallel_evidence_lanes_summary": offline_lanes_summary,
            "runtime_evidence_artifact_plan_summary": artifact_summary,
            "exact_triplet_bundle_plan_summary": triplet_bundle_summary,
            "route_sample_plan_summary": route_sample_summary,
            "actions": normalized_actions,
        },
        "non_claims": [
            "normalized next actions are planning metadata only",
            "recorded standing authority is preserved only as external exact-scope context",
            "this report does not send Discord, touch ARK, edit markers/env, read live logs, or copy evidence",
            "only approved runtime evidence checkers can change approved_runtime_evidence state",
            "current live diagnostic blockers are non-evidence context only and do not add SDK/P0 progress",
            "diagnostic route samples are bounded planning metadata only and do not add SDK/P0 progress",
            "parallel offline lanes keep SDK work moving while runtime evidence is missing but do not authorize live work or add SDK/P0 progress",
            "no SDK, stable, public, Plugin Hub, publication, or P0 progress claim is made",
        ],
        "non_authorization": NON_AUTHORIZATION,
    }


def emit_report(report: dict[str, Any], args: argparse.Namespace) -> None:
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output is not None and str(args.json_output) != "-":
        output = resolved_output(args.json_output, "--json-output")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    if args.json or args.json_output is None or str(args.json_output) == "-":
        print(text)
    elif args.json_output is not None:
        print(
            "player_principal_lifecycle_next_actions_planned=true "
            f"action_count={report['action_count']} "
            "authorized_by_this_report=false "
            "approved_runtime_evidence=false"
        )


def main() -> int:
    args = parse_args()
    report = build_report(args)
    emit_report(report, args)
    return 0 if report["next_action_sequence"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
