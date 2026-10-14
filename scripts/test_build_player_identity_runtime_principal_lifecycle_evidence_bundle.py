#!/usr/bin/env python3
"""Tests for build_player_identity_runtime_principal_lifecycle_evidence_bundle.py."""

from __future__ import annotations

import json
import hashlib
import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
SAFE_OFFLINE_WORKSPACE_DIR = tempfile.TemporaryDirectory(prefix="obelisk-safe-offline-workspace-")
SAFE_OFFLINE_WORKSPACE = Path(SAFE_OFFLINE_WORKSPACE_DIR.name)
_OLD_TEST_WORKSPACE_ROOT = os.environ.get("OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE")
_OLD_ALLOW_TEST_WORKSPACES = os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES")
os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"

import prepare_player_principal_lifecycle_window_request as window_request_module

window_request_module = importlib.reload(window_request_module)

import check_player_identity_first_evidence_readiness as first_evidence_checker
import build_player_identity_runtime_principal_lifecycle_evidence_bundle as bundle_builder
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_TEXT,
    AUTHORIZATION_FLAGS,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    NON_CLAIMS,
    STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
    WINDOW_MARKERS,
    current_turn_approval_scope,
    deployment_intent,
    direct_join_plan,
    env_file_lines,
    env_lines,
    exact_target_scope,
    markdown_request,
    operator_approval_receipt_payload,
    operator_live_ops_brief,
    passive_wait_boundary,
    player_notice_action,
    player_presence_safety,
    planned_obelisk_build_identity,
    post_window_replay_contract,
    rollback_plan,
    runtime_triplet_contract,
)
if _OLD_TEST_WORKSPACE_ROOT is None:
    os.environ.pop("OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE", None)
else:
    os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = _OLD_TEST_WORKSPACE_ROOT
if _OLD_ALLOW_TEST_WORKSPACES is None:
    os.environ.pop("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES", None)
else:
    os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = _OLD_ALLOW_TEST_WORKSPACES

BUNDLE = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
LIBOBELISK_SHA = "2" * 64
WINDOW_START = (datetime.now(timezone.utc) - timedelta(minutes=20)).replace(microsecond=0)
RUN_ID = WINDOW_START.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
OFFLINE_WORKSPACE = Path("/servidor/ark/workspace-offline")
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
OTHER_TEST_COMMIT = "abcdef1234567890abcdef1234567890abcdef12"


def future_window() -> dict[str, str]:
    start = WINDOW_START
    prepared = start - timedelta(minutes=5)
    approval = start - timedelta(minutes=4)
    actual_start = start + timedelta(minutes=1)
    actual_end = start + timedelta(minutes=9)
    end = start + timedelta(minutes=15)
    return {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prepared": prepared.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "approval": approval.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actual_start": actual_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actual_end": actual_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def log_clock(offset_minutes: int) -> str:
    return (WINDOW_START + timedelta(minutes=offset_minutes)).strftime("[%Y-%m-%dT%H:%M:%SZ]")


def log_timestamp(offset_minutes: int) -> str:
    return (WINDOW_START + timedelta(minutes=offset_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def runtime_log_lines() -> list[str]:
    return [
        "[info]  Obelisk Runtime Loaded Native (LD_PRELOAD)",
        "[info] ProcessEvent vtable-derived pattern candidates found: 1",
        "[info] ProcessEvent candidate[0] = 0x1d34e20",
        "[info] Found ProcessEvent at address: 0x1d34e20",
        "[info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x767c6aaa4000",
        "[info] ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.",
        "[warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.",
        f"{log_clock(1)} [info] PlayerPrincipalLifecycleObserver enabled binary_sha256={SHA} "
        "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
        "delivery_claim=none principal_claim=none.",
        f"{log_clock(2)} [info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
        f"{log_clock(3)} [info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
        "target=ShooterGameMode.CheckJoinInProgress post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
        "redacted_count=1 redacted_fields=NewPlayer "
        "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
        "delivery_claim=none.",
        f"{log_clock(4)} [info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
        "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
        "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
        "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
    ]


def runtime_log_lines_with_check_join_rejected_start() -> list[str]:
    return [
        (
            f"{log_clock(3)} [info] PlayerPrincipalLifecycleObserver event sequence=2 "
            "role=session_start_rejected target=ShooterGameMode.CheckJoinInProgress "
            "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
            "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
            "apply_status=session_start_rejected_noop correlation_status=not_applicable "
            "principal_id_logged=false principal_generation_logged=false delivery_claim=none."
        )
        if " role=session_start_rejected " in line
        else line
        for line in runtime_log_lines()
    ]


def runtime_log_lines_with_handle_new_player_rejected_start() -> list[str]:
    return [
        (
            f"{log_clock(3)} [info] PlayerPrincipalLifecycleObserver event sequence=2 "
            "role=session_start_rejected target=ShooterGameMode.HandleNewPlayer "
            "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
            "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
            "principal_action=none apply_status=session_start_rejected_noop "
            "correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
        if " role=session_start_rejected " in line
        else line
        for line in runtime_log_lines()
    ]


def runtime_log_lines_with_ragnarok_duplicate_start_diagnostic_missing_check_join() -> list[str]:
    lines = [
        line
        for line in runtime_log_lines()
        if " role=session_start_rejected " not in line
    ]
    duplicate_start = lines[8].replace("sequence=1", "sequence=2").replace(log_clock(2), log_clock(3))
    diagnostic = (
        f"{log_clock(3)} [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=4 "
        "target=ShooterGameMode.CheckJoinInProgress fname_index=2171 post_original=true "
        "accepted_lifecycle_target=true reflection_status=matched read_status=ok "
        "diagnostic_shape=CheckJoinInProgress copy_status=rejected "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
        "redacted_count=1 redacted_fields=NewPlayer params_logged=false "
        "identity_logged=false evidence_claim=none."
    )
    lines.insert(9, duplicate_start)
    lines.insert(10, diagnostic)
    return lines


def log_clock_seconds(offset_minutes: int, offset_seconds: int) -> str:
    return (WINDOW_START + timedelta(minutes=offset_minutes, seconds=offset_seconds)).strftime(
        "[%Y-%m-%dT%H:%M:%SZ]"
    )


def runtime_log_lines_with_duplicate_start_end_context() -> list[str]:
    lines = runtime_log_lines()
    duplicate_start = lines[8].replace("sequence=1", "sequence=2").replace(
        log_clock(2),
        log_clock_seconds(2, 30),
    )
    selected_rejected = lines[9].replace("sequence=2", "sequence=3")
    selected_end = lines[10].replace("sequence=3", "sequence=4")
    duplicate_end = selected_end.replace("sequence=4", "sequence=5").replace(
        log_clock(4),
        log_clock(5),
    )
    lines[8:11] = [lines[8], duplicate_start, selected_rejected, selected_end, duplicate_end]
    return lines


def runtime_log_lines_with_only_missing_correlation_session_end() -> list[str]:
    return [
        *runtime_log_lines()[:8],
        f"{log_clock(4)} [info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_end "
        "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
        "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
        "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=missing principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
    ]


def fixture_direct_join_plan(payload: dict) -> dict:
    return direct_join_plan(payload)


def without_lifecycle_status_proof_fields(line: str) -> str:
    return (
        line.replace(" apply_status=session_start_created correlation_status=not_applicable", "")
        .replace(" apply_status=session_start_rejected_noop correlation_status=not_applicable", "")
        .replace(" apply_status=session_end_invalidated correlation_status=matched", "")
    )


def copied_log_path(root: Path) -> Path:
    return root / "live-validation-logs" / RUN_ID / "Obelisk.log"


def write_sidecar(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ready_log_copy_payload(copied_log: Path) -> dict:
    copied_sha256 = hashlib.sha256(copied_log.read_bytes()).hexdigest()
    roles = ["session_start", "session_start_rejected", "session_end"]
    event_specs = {
        "session_start": {
            "line_number": 9,
            "sequence": 1,
            "target": "ShooterGameMode.HandleNewPlayer",
            "timestamp_prefix": log_timestamp(2),
            "copied_bool_fields": "bIsFromLogin,ReturnValue",
            "copied_bool_values": "1,1",
            "apply_status": "session_start_created",
            "correlation_status": "not_applicable",
        },
        "session_start_rejected": {
            "line_number": 10,
            "sequence": 2,
            "target": "ShooterGameMode.CheckJoinInProgress",
            "timestamp_prefix": log_timestamp(3),
            "copied_bool_fields": "bIsFromLogin,ReturnValue",
            "copied_bool_values": "1,0",
            "apply_status": "session_start_rejected_noop",
            "correlation_status": "not_applicable",
        },
        "session_end": {
            "line_number": 11,
            "sequence": 3,
            "target": "ShooterGameMode.OnLogout",
            "timestamp_prefix": log_timestamp(4),
            "copied_bool_fields": "",
            "copied_bool_values": "",
            "apply_status": "session_end_invalidated",
            "correlation_status": "matched",
        },
    }
    accepted_events = {
        role: {
            "role": role,
            **event_specs[role],
            "inside_fresh_window": True,
            "approved_copy_shape_ok": True,
            "status_proof_ok": True,
        }
        for role in roles
    }
    analysis = {
        "observer_enabled": True,
        "observer_enable_in_fresh_window": True,
        "observer_binary_sha256": SHA,
        "expected_binary_sha256": SHA,
        "binary_sha256_match": True,
        "roles_present": roles,
        "missing_roles": [],
        "accepted_role_events": accepted_events,
        "accepted_lifecycle_event_count": 3,
        "accepted_lifecycle_events": [
            {
                "role": role,
                "line_number": accepted_events[role]["line_number"],
                "sequence": accepted_events[role]["sequence"],
                "target": accepted_events[role]["target"],
                "timestamp_prefix": accepted_events[role]["timestamp_prefix"],
                "inside_fresh_window": True,
            }
            for role in roles
        ],
        "historical_accepted_role_event_count": 0,
        "historical_accepted_role_events": [],
        "rejected_or_incomplete_role_event_count": 0,
        "exact_copied_runtime_triplet": {
            "accepted": True,
            "status": "selected",
            "blockers": [],
            "required_roles": roles,
            "accepted_roles": roles,
            "missing_roles": [],
            "selected_indices": [0, 1, 2],
            "selected_sequences": [1, 2, 3],
            "selected_roles": roles,
            "copied_log_only_counts_as_approved_runtime_evidence": False,
            "passive_or_diagnostic_material_counts_as_approved_runtime_evidence": False,
        },
        "fresh_window": {
            "start_utc": log_timestamp(1),
            "end_utc": log_timestamp(9),
        },
        "ready_to_copy": True,
        "copy_readiness": "ready_complete_role_triplet",
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
    }
    return {
        "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
        "status": "copied",
        "ready": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "public_header_allowed": False,
        "promotion_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "publication_authorized": False,
        "discord_sent_by_this_report": False,
        "server_operations_authorized_by_this_report": False,
        "marker_env_changes_authorized_by_this_report": False,
        "instance": "arkserver2",
        "source_log": str(copied_log.parent / "source" / "Obelisk.log"),
        "evidence_dir": str(copied_log.parent),
        "target_log": str(copied_log),
        "execute_requested": True,
        "allow_live_log_read": True,
        "allow_evidence_dir_write": True,
        "overwrite": False,
        "fresh_window_start_utc": log_timestamp(1),
        "fresh_window_end_utc": log_timestamp(9),
        "ready_to_copy": True,
        "copy_readiness": "ready_complete_role_triplet",
        "copied": True,
        "source_sha256": copied_sha256,
        "target_existing_sha256": None,
        "target_copied_sha256": copied_sha256,
        "analysis": analysis,
        "roles_present": roles,
        "missing_roles": [],
        "blockers": [],
        "source_log_safety": {
            "accepted": True,
            "blockers": [],
            "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence": False,
            "passive_context_counts_as_approved_runtime_evidence": False,
            "unsafe_player_text_counts_as_approved_runtime_evidence": False,
        },
        "non_claims": [
            "ready-log copy is operational copy readiness only",
            "copied Obelisk.log is still not approved runtime evidence until sibling-set bundle checkers accept it",
            "this helper does not start, stop, restart, send Discord, edit markers/env, publish, or claim SDK readiness",
        ],
    }


def blocked_ragnarok_ready_log_copy_payload(copied_log: Path) -> dict:
    payload = ready_log_copy_payload(copied_log)
    blockers = [
        "source_log_contains_lifecycle_diagnostic_lines",
        "blocked_ambiguous_duplicate_lifecycle_roles",
        "exact_copied_runtime_triplet_missing_session_start_rejected",
    ]
    roles_present = ["session_start", "session_end"]
    missing_roles = ["session_start_rejected"]
    payload.update(
        {
            "status": "execute_blocked",
            "ready_to_copy": False,
            "copy_readiness": "blocked_ambiguous_duplicate_lifecycle_roles",
            "copied": False,
            "target_copied_sha256": None,
            "roles_present": roles_present,
            "missing_roles": missing_roles,
            "blockers": blockers,
            "source_log_safety": {
                "accepted": False,
                "blockers": ["source_log_contains_lifecycle_diagnostic_lines"],
                "lifecycle_diagnostic_line_count": 1,
                "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence": False,
            },
        }
    )
    payload["analysis"].update(
        {
            "ready_to_copy": False,
            "copy_readiness": "blocked_ambiguous_duplicate_lifecycle_roles",
            "roles_present": roles_present,
            "missing_roles": missing_roles,
            "duplicate_accepted_role_event_count": 1,
            "duplicate_accepted_roles": ["session_start"],
            "exact_copied_runtime_triplet": {
                "accepted": False,
                "blockers": ["exact_copied_runtime_triplet_missing_session_start_rejected"],
                "required_rejected_start_shape": {
                    "target": "ShooterGameMode.CheckJoinInProgress",
                    "copied_bool_fields": "bIsFromLogin,ReturnValue",
                    "copied_bool_values": "1,0",
                },
                "copied_log_only_counts_as_approved_runtime_evidence": False,
                "passive_or_diagnostic_material_counts_as_approved_runtime_evidence": False,
            },
        }
    )
    return payload


def blocked_player_presence_no_role_ready_log_copy_payload(copied_log: Path) -> dict:
    payload = ready_log_copy_payload(copied_log)
    blockers = [
        "source_log_contains_passive_context_metadata",
        "blocked_missing_lifecycle_roles",
        "exact_copied_runtime_triplet_missing_session_start",
        "exact_copied_runtime_triplet_missing_session_start_rejected",
        "exact_copied_runtime_triplet_missing_session_end",
        "exact_copied_runtime_triplet_not_selected",
        "player_present_but_no_lifecycle_roles",
    ]
    missing_roles = ["session_start", "session_start_rejected", "session_end"]
    presence_context = {
        "classification": "players_detected_operator_context_non_evidence",
        "context_present": True,
        "players_detected": True,
        "indicator_line_count": 1,
        "indicator_lines": [
            {
                "line": 8,
                "presence_detected": True,
                "players_current": 1,
                "target": "arkserver2:TheIsland:27016",
            }
        ],
        "targets": ["arkserver2:TheIsland:27016"],
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "player_presence_context_counts_as_runtime_evidence": False,
        "player_presence_context_counts_as_sdk_evidence": False,
    }
    source_log_not_ready = {
        "schema": "obelisk.player-principal-lifecycle-source-log-not-ready.v1",
        "classification": "observer_enabled_no_lifecycle_roles_post_window",
        "blockers": ["observer_enabled_but_no_lifecycle_roles", "player_present_but_no_lifecycle_roles"],
        "observer_only_no_role_window_detected": True,
        "active_observer_only_no_role_window": False,
        "post_window_observer_only_no_role_window": True,
        "player_present_but_no_lifecycle_roles": True,
        "player_present_no_lifecycle_roles_blocker": "player_present_but_no_lifecycle_roles",
        "player_presence_context": presence_context,
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "source_log_not_ready": True,
        "source_log_not_ready_reason": "observer_enabled_no_lifecycle_roles_post_window",
        "window_state": "post_window",
        "ready_to_copy": False,
        "copied_log_ready": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
    }
    payload.update(
        {
            "status": "execute_blocked",
            "ready_to_copy": False,
            "copy_readiness": "blocked_missing_lifecycle_roles",
            "copied": False,
            "target_copied_sha256": None,
            "roles_present": [],
            "missing_roles": missing_roles,
            "blockers": blockers,
            "source_log_not_ready": source_log_not_ready,
            "observer_only_no_role_window": source_log_not_ready,
            "observer_only_no_role_window_detected": True,
            "player_present_but_no_lifecycle_roles": True,
            "source_log_safety": {
                "accepted": False,
                "blockers": ["source_log_contains_passive_context_metadata"],
                "passive_context_line_count": 1,
                "player_presence_context": presence_context,
                "passive_context_counts_as_approved_runtime_evidence": False,
                "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence": False,
            },
        }
    )
    payload["analysis"].update(
        {
            "ready_to_copy": False,
            "copy_readiness": "blocked_missing_lifecycle_roles",
            "roles_present": [],
            "missing_roles": missing_roles,
            "accepted_lifecycle_event_count": 0,
            "accepted_lifecycle_events": [],
            "accepted_role_events": {},
            "exact_copied_runtime_triplet": {
                "accepted": False,
                "status": "missing",
                "blockers": [
                    "exact_copied_runtime_triplet_missing_session_start",
                    "exact_copied_runtime_triplet_missing_session_start_rejected",
                    "exact_copied_runtime_triplet_missing_session_end",
                    "exact_copied_runtime_triplet_not_selected",
                ],
                "required_roles": missing_roles,
                "accepted_roles": [],
                "missing_roles": missing_roles,
                "copied_log_only_counts_as_approved_runtime_evidence": False,
                "passive_or_diagnostic_material_counts_as_approved_runtime_evidence": False,
            },
        }
    )
    return payload


def blocked_session_end_missing_correlation_ready_log_copy_payload(copied_log: Path) -> dict:
    payload = ready_log_copy_payload(copied_log)
    payload["status"] = "blocked"
    payload["ready"] = False
    payload["ready_to_copy"] = False
    payload["copied"] = False
    payload["copy_readiness"] = "blocked_diagnostic_or_rejected_lifecycle_lines"
    payload["roles_present"] = ["session_end"]
    payload["missing_roles"] = ["session_start", "session_start_rejected", "session_end"]
    payload["blockers"] = ["session_end_missing_correlation_only"]
    payload["analysis"] = {
        "roles_present": ["session_end"],
        "missing_roles": ["session_start", "session_start_rejected", "session_end"],
        "accepted_lifecycle_event_count": 0,
        "rejected_or_incomplete_role_event_count": 1,
        "malformed_observer_lines": 1,
        "unsafe_lifecycle_event_reasons": {
            "session_end_correlation_status_missing": 1,
        },
        "invalid_lifecycle_event_non_evidence_reasons": {
            "session_end_correlation_status_missing": 1,
        },
        "exact_copied_runtime_triplet": {
            "accepted": False,
            "missing_roles": ["session_start", "session_start_rejected", "session_end"],
            "blockers": ["exact_copied_runtime_triplet_missing"],
        },
        "diagnostic_or_rejected_lifecycle_lines_count_as_ready_to_copy": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence": False,
    }
    payload["source_log_not_ready"] = {
        "schema": "obelisk.player-principal-lifecycle-source-log-not-ready.v1",
        "classification": "session_end_missing_correlation_only_non_evidence",
        "window_state": "post_window",
        "fresh_window": {
            "start_utc": log_timestamp(1),
            "end_utc": log_timestamp(9),
        },
        "target_hint": {"instance": "arkserver2", "map": "TheIsland"},
        "observer_enabled": True,
        "observer_enable_in_fresh_window": True,
        "observer_only_no_role_window_detected": False,
        "manual_offline_next_steps": [
            "wait for a matched session_end and the exact lifecycle triplet",
        ],
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
    }
    return payload


def stale_fresh_window_ready_log_copy_payload(copied_log: Path) -> dict:
    payload = ready_log_copy_payload(copied_log)
    payload["fresh_window_start_utc"] = log_timestamp(6)
    payload["fresh_window_end_utc"] = log_timestamp(9)
    payload["analysis"]["fresh_window"] = {
        "start_utc": payload["fresh_window_start_utc"],
        "end_utc": payload["fresh_window_end_utc"],
    }
    return payload


def write_ready_log_copy_report(copied_log: Path, payload: dict | None = None) -> Path:
    report_path = copied_log.parent / "ready-log-copy.json"
    report_path.write_text(
        json.dumps(payload or ready_log_copy_payload(copied_log), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


def preflight_payload(
    *,
    mode: str,
    instance: str,
    run_id: str,
    map_name: str,
    window_manifest_path: Path,
    copied_log_path: Path,
    env_file: Path | None = None,
    env_sha256: str | None = None,
    checked_at_utc: str,
) -> str:
    payload = {
        "schema": "obelisk.player-principal-lifecycle-preflight.v1",
        "ready": True,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "request_pack_counts_as_approved_runtime_evidence": False,
        "preflight_counts_as_approved_runtime_evidence": False,
        "window_manifest_counts_as_approved_runtime_evidence": False,
        "completed_receipt_counts_as_approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "route_ready": False,
        "observer_env_counts_as_approved_runtime_evidence": False,
        "operator_request_counts_as_approved_runtime_evidence": False,
        "copied_log_metadata_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "bundle_output_counts_as_approved_runtime_evidence": False,
        "dry_run_success_counts_as_approved_runtime_evidence": False,
        "historical_target_names_authorize_runtime": False,
        "marker_env_readiness_counts_as_approved_runtime_evidence": False,
        "player_notice_counts_as_approved_runtime_evidence": False,
        "public_reachability_counts_as_approved_runtime_evidence": False,
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "mode": mode,
        "run_id": run_id,
        "instance": instance,
        "map": map_name,
        "target": {"instance": instance, "map": map_name},
        "window_manifest_path": str(window_manifest_path),
        "copied_log_path": str(copied_log_path),
        "copied_evidence_dir": str(copied_log_path.parent),
        "server_binary": {
            "path": "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer",
            "sha256": SHA,
        },
        "obelisk_root": "/servidor/ark/obelisk",
        "installed_wrapper": {
            "path": "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh",
            "sha256": "1" * 64,
        },
        "env_file": None if env_file is None else {"path": str(env_file), "sha256": env_sha256},
        "diagnostic_candidates_enabled": False,
        "marker_dir": f"/servidor/ark/obelisk/state/instances/{instance}",
        "offline_only": False,
        "allow_stopped": False,
        "checked_at_utc": checked_at_utc,
        "posture_check": "accepted",
        "non_claim": "preflight only; not runtime approval, not approved runtime evidence, and not permission to touch servers",
    }
    return json.dumps(payload, sort_keys=True) + "\n"


def runtime_replacement_false_lines() -> list[str]:
    return [
        "server_operations_authorized=false",
        "runtime_work_authorized=false",
        "runtime_capture_authorized=false",
        "live_ops_authorized=false",
        "approved_runtime_evidence_present=false",
        "approved_runtime_evidence_ready=false",
        "runtime_evidence_ready=false",
        "counts_as_approved_runtime_evidence=false",
        "installed_libobelisk_counts_as_approved_runtime_evidence=false",
        "post_restart_preflight_counts_as_approved_runtime_evidence=false",
        "promotion_ready=false",
        "public_header_allowed=false",
        "public_abi_ready=false",
        "public_sdk_ready=false",
        "v1_completion_ready=false",
        "runtime_ready=false",
        "stable_claim_allowed=false",
    ]


def post_restart_preflight_sidecar_text(
    *,
    copied_log: Path,
    copied_log_sha256: str,
    checked_at_utc: str,
) -> str:
    return "\n".join(
        [
            "schema=obelisk.player-principal-lifecycle-post-restart-preflight.v1",
            f"run_id={RUN_ID}",
            f"copied_log_path={copied_log}",
            f"copied_log_sha256={copied_log_sha256}",
            "post_restart_preflight=true",
            "post_restart_posture=stable",
            "posture_check=accepted",
            "installed_runtime_replaced=true",
            "runtime_replaced=true",
            f"installed_libobelisk_sha256={LIBOBELISK_SHA}",
            "deleted_libobelisk_mapping_present=false",
            "mapped_libobelisk_deleted=false",
            "plugins_disabled=true",
            "scanner_disabled=true",
            "observer_env_survived=false",
            "observer_marker_survived=false",
            "sibling_marker_entries=absent",
            "sibling_observer_env=absent",
            "debug_escape_markers=absent",
            "callback_escape_markers=absent",
            "native_exec_disabled=true",
            "ptrace_disabled=true",
            f"checked_at_utc={checked_at_utc}",
            *runtime_replacement_false_lines(),
            "non_claim=post-restart preflight sidecar only; not approved runtime evidence, runtime readiness, or server authorization",
        ]
    ) + "\n"


def installed_libobelisk_sidecar_text(
    *,
    copied_log: Path,
    copied_log_sha256: str,
    post_restart_preflight: Path,
    post_restart_preflight_sha256: str,
) -> str:
    return "\n".join(
        [
            "schema=obelisk.installed-libobelisk-artifact.v1",
            f"run_id={RUN_ID}",
            f"copied_log_path={copied_log}",
            f"copied_log_sha256={copied_log_sha256}",
            "installed_libobelisk_path=/servidor/ark/obelisk/lib/libobelisk.so",
            f"installed_libobelisk_sha256={LIBOBELISK_SHA}",
            "installed_runtime_replaced=true",
            "runtime_replaced=true",
            "deleted_libobelisk_mapping_present=false",
            "mapped_libobelisk_deleted=false",
            f"post_restart_preflight_path={post_restart_preflight}",
            f"post_restart_preflight_sha256={post_restart_preflight_sha256}",
            *runtime_replacement_false_lines(),
            "non_claim=installed libobelisk binding only; not approved runtime evidence, runtime readiness, or server authorization",
        ]
    ) + "\n"


class BuildRuntimePrincipalLifecycleEvidenceBundleTests(unittest.TestCase):
    def test_negative_non_authorization_sidecar_text_is_not_an_overclaim(self) -> None:
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
        blockers: list[dict[str, object]] = []

        bundle_builder.check_json_sidecar_overclaims(payload, "window_request_json", blockers)

        self.assertEqual(blockers, [])

    def test_negative_non_authorization_context_still_rejects_nested_positive_overclaim(self) -> None:
        blockers: list[dict[str, object]] = []

        bundle_builder.check_json_sidecar_overclaims(
            {"non_authorization": {"public_sdk_ready": True}},
            "window_request_json",
            blockers,
        )

        self.assertIn(
            "json_sidecar_readiness_flag_overclaim",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertIn(
            "$.non_authorization.public_sdk_ready",
            [blocker["key_path"] for blocker in blockers],
        )

    def test_rejects_zero_count_function_fname_near_miss_summary_maps(self) -> None:
        summary = bundle_builder.approved_evidence_checker.runtime_observer_analyzer.analyze_lines(
            runtime_log_lines()
        )
        module = summary["modules"]["player_principal_lifecycle"]
        module["diagnostic_candidate_count"] = 0
        module["diagnostic_candidate_reason_counts"] = {"FunctionFNameNearMiss": 1}
        module["diagnostic_candidate_read_status_counts"] = {"ok": 1}
        module["diagnostic_candidate_target_counts"] = {
            "ShooterGameMode.CheckJoinInProgress": 1,
        }

        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_check_join_rejected_start_triplet(summary)

        self.assertIn(
            "runtime observer summary diagnostic candidates are not approved runtime evidence",
            str(raised.exception),
        )

    def temp_offline_workspace(self) -> tempfile.TemporaryDirectory[str]:
        return tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=SAFE_OFFLINE_WORKSPACE)

    def write_window_manifest(
        self,
        temp_dir: Path,
        copied_log: Path,
        *,
        standing_launch_authority: bool = False,
    ) -> Path:
        manifest = temp_dir / "live-validation-logs" / RUN_ID / "window-manifest.env"
        copied_log_sha256 = (
            hashlib.sha256(copied_log.read_bytes()).hexdigest()
            if copied_log.is_file()
            else "0000000000000000000000000000000000000000000000000000000000000000"
        )
        sidecar_dir = manifest.parent
        request_pack = sidecar_dir / "window-request.json"
        observer_env = sidecar_dir / "observer-window.env"
        operator_request = sidecar_dir / "operator-approval-request.md"
        operator_approval_receipt = sidecar_dir / "operator-approval-receipt.json"
        preflight_pre = manifest.parent / "preflight-pre.json"
        preflight_post = manifest.parent / "preflight-post.json"
        post_restart_preflight = manifest.parent / "post-restart-preflight.env"
        installed_libobelisk = manifest.parent / "installed-libobelisk.env"
        window = future_window()
        approval_text = STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT if standing_launch_authority else APPROVAL_TEXT
        request_args = type(
            "Args",
            (),
            {
                "instance": "arkserver2",
                "map_name": "TheIsland",
                "binary_sha256": EXPECTED_BINARY_SHA256,
                "obelisk_commit": TEST_COMMIT,
                "obelisk_build_artifact": None,
                "obelisk_build_artifact_sha256": None,
                "obelisk_build_artifact_label": None,
            },
        )()
        observer_env_sha256 = write_sidecar(
            observer_env,
            "\n".join(env_file_lines(request_args))
            + "\n",
        )
        request_payload = {
            "schema": "obelisk.player-principal-lifecycle-window-request.v1",
            "run_id": RUN_ID,
            "status": "candidate_only_request_pack",
            "approval_required": approval_text,
            "prepared_at_utc": window["prepared"],
            "ark_binary_sha256": EXPECTED_BINARY_SHA256,
            "server_binary_path": EXPECTED_SERVER_BINARY_PATH,
            "obelisk_commit": TEST_COMMIT,
            "planned_obelisk_build_identity": planned_obelisk_build_identity(request_args),
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            "approved_window": {
                "start_utc": window["start"],
                "end_utc": window["end"],
            },
            "restart_expectation": "restart",
            "final_posture": "stable",
            "diagnostic_candidates_enabled": False,
            "authorization_flags": dict(AUTHORIZATION_FLAGS),
            "user_policy": "no_regular_users",
            "notice_path": "not_applicable",
            "copied_evidence_dir": str(copied_log.parent),
            "copied_log_path": str(copied_log),
            "window_manifest_path": str(manifest),
            "observer_env_file": "observer-window.env",
            "marker_set": WINDOW_MARKERS,
            "forbidden_markers": FORBIDDEN_MARKERS,
            "runtime_triplet_contract": runtime_triplet_contract(),
            "non_claims": NON_CLAIMS,
        }
        request_payload["player_notice_action"] = player_notice_action(request_payload)
        request_payload["player_presence_safety"] = player_presence_safety(request_payload)
        request_payload["exact_target_scope"] = exact_target_scope(request_payload)
        request_payload["passive_wait_boundary"] = passive_wait_boundary(request_payload)
        request_payload["rollback"] = rollback_plan(request_payload["target"], "operator")
        join_plan = fixture_direct_join_plan(request_payload)
        request_payload["direct_join_plan"] = join_plan
        request_payload["post_window_replay_contract"] = post_window_replay_contract(request_payload)
        request_payload["current_turn_approval_scope"] = current_turn_approval_scope(
            request_payload,
            env_lines(request_args),
        )
        request_payload["deployment_intent"] = deployment_intent(request_payload)
        request_payload["operator_live_ops_brief"] = operator_live_ops_brief(
            request_payload,
            env_lines(request_args),
        )
        markdown_payload = {**request_payload, "direct_join_plan": join_plan}
        request_pack_sha256 = write_sidecar(
            request_pack,
            json.dumps(request_payload, sort_keys=True) + "\n",
        )
        write_sidecar(
            operator_request,
            markdown_request(markdown_payload, env_lines(request_args)),
        )
        receipt_payload = operator_approval_receipt_payload(
            markdown_payload,
            request_json_path=request_pack,
            request_md_path=operator_request,
            env_path=observer_env,
            operator_approved=True,
            operator_reference="operator",
            approved_at_utc=window["approval"],
        )
        operator_approval_receipt_sha256 = write_sidecar(
            operator_approval_receipt,
            json.dumps(receipt_payload, sort_keys=True)
            + "\n",
        )
        preflight_pre_sha256 = write_sidecar(
            preflight_pre,
            preflight_payload(
                mode="observer-window",
                instance="arkserver2",
                run_id=RUN_ID,
                map_name="TheIsland",
                window_manifest_path=manifest,
                copied_log_path=copied_log,
                env_file=observer_env,
                env_sha256=observer_env_sha256,
                checked_at_utc=window["actual_start"],
            ),
        )
        preflight_post_sha256 = write_sidecar(
            preflight_post,
            preflight_payload(
                mode="stable",
                instance="arkserver2",
                run_id=RUN_ID,
                map_name="TheIsland",
                window_manifest_path=manifest,
                copied_log_path=copied_log,
                checked_at_utc=window["end"],
            ),
        )
        post_restart_preflight_sha256 = write_sidecar(
            post_restart_preflight,
            post_restart_preflight_sidecar_text(
                copied_log=copied_log,
                copied_log_sha256=copied_log_sha256,
                checked_at_utc=window["end"],
            ),
        )
        write_sidecar(
            installed_libobelisk,
            installed_libobelisk_sidecar_text(
                copied_log=copied_log,
                copied_log_sha256=copied_log_sha256,
                post_restart_preflight=post_restart_preflight,
                post_restart_preflight_sha256=post_restart_preflight_sha256,
            ),
        )
        manifest.write_text(
            "\n".join(
                [
                    f"run_id={RUN_ID}",
                    f"obelisk_commit={TEST_COMMIT}",
                    "target=arkserver2/TheIsland",
                    f"approval={approval_text}",
                    f"approved_window_start_utc={window['start']}",
                    f"approved_window_end_utc={window['end']}",
                    f"actual_capture_start_utc={window['actual_start']}",
                    f"actual_capture_end_utc={window['actual_end']}",
                    f"copied_log_path={copied_log}",
                    f"copied_log_sha256={copied_log_sha256}",
                    f"request_pack_path={request_pack}",
                    f"request_pack_sha256={request_pack_sha256}",
                    f"observer_env_path={observer_env}",
                    f"observer_env_sha256={observer_env_sha256}",
                    f"operator_approval_receipt_path={operator_approval_receipt}",
                    f"operator_approval_receipt_sha256={operator_approval_receipt_sha256}",
                    f"preflight_pre_path={preflight_pre}",
                    f"preflight_pre_sha256={preflight_pre_sha256}",
                    f"preflight_post_path={preflight_post}",
                    f"preflight_post_sha256={preflight_post_sha256}",
                    "pre_posture=stable",
                    "post_posture=stable",
                    "pre_check=passed",
                    "post_check=passed",
                    f"rollback_start_utc={window['actual_end']}",
                    f"rollback_end_utc={window['end']}",
                    "rollback_completed=true",
                    "rollback_delta=removed_observer_env_and_markers_preserved_disable_plugins",
                    "observer_env_survived=false",
                    "observer_marker_survived=false",
                    "user_policy=no_regular_users",
                    "notice_sent=not_applicable",
                    "log_budget=10",
                    "plugins_disabled=true",
                    "scanner_disabled=true",
                    "dispatch_limit=0",
                    "wrapper_profile=observer-debug",
                    "observer_exclusivity=player_principal_lifecycle_only",
                    "sibling_marker_entries=absent",
                    "sibling_observer_env=absent",
                    "debug_escape_markers=absent",
                    "callback_escape_markers=absent",
                    "native_exec_disabled=true",
                    "ptrace_disabled=true",
                    "single_module_summary=player_principal_lifecycle",
                    "delivery_claim=none",
                    "principal_claim=none",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest

    def write_relative_window_manifest(self, temp_dir: Path, copied_log: Path) -> Path:
        manifest = self.write_window_manifest(temp_dir, copied_log)
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                f"copied_log_path={copied_log}",
                f"copied_log_path={copied_log.relative_to(manifest.parent)}",
            ),
            encoding="utf-8",
        )
        return manifest

    def run_bundle(
        self,
        copied_log: Path,
        output_dir: Path,
        *,
        window_manifest: Path | None = None,
        obelisk_commit: str = TEST_COMMIT,
    ) -> subprocess.CompletedProcess[str]:
        if window_manifest is None:
            window_manifest = self.write_window_manifest(output_dir.parent, copied_log)
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        env["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
        return subprocess.run(
            [
                sys.executable,
                str(BUNDLE),
                "--copied-log",
                str(copied_log),
                "--window-manifest",
                str(window_manifest),
                "--output-dir",
                str(output_dir),
                "--obelisk-commit",
                obelisk_commit,
                "--reviewed-by",
                "runtime-reviewer",
                "--review-note",
                "bounded redacted lifecycle observer summary accepted for consume-only review",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def run_preflight(self, evidence_dir: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        env["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
        return subprocess.run(
            [
                sys.executable,
                str(BUNDLE),
                "--preflight-only",
                "--evidence-dir",
                str(evidence_dir),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def run_evidence_dir_bundle(
        self,
        evidence_dir: Path,
        *extra_args: str,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        env["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
        return subprocess.run(
            [
                sys.executable,
                str(BUNDLE),
                "--evidence-dir",
                str(evidence_dir),
                *extra_args,
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def test_preflight_does_not_read_unapproved_window_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obelisk-test-unapproved-manifest-") as temp:
            evidence_dir = Path(temp) / "live-validation-logs" / RUN_ID
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "window-manifest.env").write_text(
                "request_pack_path=unsafe-request.json\n",
                encoding="utf-8",
            )

            with (
                mock.patch.object(
                    bundle_builder,
                    "read_manifest_fields",
                    side_effect=AssertionError("unsafe window manifest must not be parsed"),
                ),
                mock.patch.object(
                    bundle_builder,
                    "run_json_check",
                    side_effect=AssertionError("unsafe window manifest must not be checked"),
                ),
            ):
                report = bundle_builder.classify_preflight_evidence_dir(evidence_dir)

        self.assertFalse(report["ready"])
        self.assertIn("window_manifest_not_approved_offline_workspace", report["blockers"])
        self.assertFalse(report["inputs"]["window_manifest"]["approved_offline_workspace"])
        self.assertFalse(report["inputs"]["window_manifest_check"]["checked"])

    def test_preflight_does_not_read_protected_window_manifest(self) -> None:
        original_status = bundle_builder.protected_paths.protected_path_status

        with tempfile.TemporaryDirectory(prefix="obelisk-test-protected-manifest-") as temp:
            evidence_dir = Path(temp) / "live-validation-logs" / RUN_ID
            evidence_dir.mkdir(parents=True)
            manifest = evidence_dir / "window-manifest.env"
            manifest.write_text(
                "request_pack_path=unsafe-request.json\n",
                encoding="utf-8",
            )

            def fake_status(path: Path, **kwargs: object) -> object:
                expanded = Path(path).expanduser()
                if expanded == manifest:
                    return bundle_builder.protected_paths.ProtectedPathStatus(
                        expanded=expanded,
                        resolved=expanded,
                        direct_under_protected_root=True,
                        resolved_under_protected_root=False,
                        approved_offline_workspace=False,
                    )
                return original_status(path, **kwargs)

            with (
                mock.patch.object(bundle_builder.protected_paths, "protected_path_status", side_effect=fake_status),
                mock.patch.object(
                    bundle_builder,
                    "read_manifest_fields",
                    side_effect=AssertionError("protected window manifest must not be parsed"),
                ),
                mock.patch.object(
                    bundle_builder,
                    "run_json_check",
                    side_effect=AssertionError("protected window manifest must not be checked"),
                ),
            ):
                report = bundle_builder.classify_preflight_evidence_dir(evidence_dir)

        self.assertFalse(report["ready"])
        self.assertIn("window_manifest_under_protected_server_root", report["blockers"])
        self.assertTrue(report["inputs"]["window_manifest"]["protected"])
        self.assertFalse(report["inputs"]["window_manifest_check"]["checked"])

    def test_preflight_uses_canonical_sibling_sidecar_fallbacks_without_manifest(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            evidence_dir = temp_dir / "live-validation-logs" / RUN_ID
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "window-request.json").write_text("{}", encoding="utf-8")
            (evidence_dir / "observer-window.env").write_text("OBELISK_INSTANCE_ID=arkserver2\n", encoding="utf-8")
            (evidence_dir / "preflight-pre.json").write_text("{}", encoding="utf-8")
            (evidence_dir / "preflight-post.json").write_text("{}", encoding="utf-8")
            (evidence_dir / "operator-approval-receipt.json").write_text("{}", encoding="utf-8")

            result = self.run_preflight(evidence_dir)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["schema"],
            "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle-preflight.v1",
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertFalse(report["request_pack_is_runtime_evidence"])
        self.assertFalse(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "copied_log_and_window_manifest_required")
        self.assertEqual(
            [artifact["artifact"] for artifact in report["next_required_artifacts"]],
            [
                "copied_obelisk_log",
                "checked_window_manifest_env",
                "window_request_json",
                "observer_window_env",
                "operator_approval_request_md",
                "operator_approval_receipt",
                "preflight_pre_json",
                "preflight_post_json",
                "approved_runtime_principal_lifecycle_evidence_manifest",
            ],
        )
        self.assertEqual(
            [artifact["present"] for artifact in report["next_required_artifacts"]],
            [False, False, True, True, False, True, True, True, False],
        )
        self.assertIn("request_pack_check_failed", report["blockers"])
        self.assertIn("copied_log_missing", report["blockers"])
        self.assertIn("window_manifest_missing", report["blockers"])
        self.assertIn("approved_runtime_manifest_missing", report["blockers"])
        self.assertEqual(
            report["inputs"]["request_pack"]["path"],
            str(evidence_dir / "window-request.json"),
        )
        self.assertEqual(
            report["inputs"]["preflight_pre"]["path"],
            str(evidence_dir / "preflight-pre.json"),
        )
        self.assertEqual(
            report["inputs"]["preflight_post"]["path"],
            str(evidence_dir / "preflight-post.json"),
        )
        self.assertEqual(
            report["inputs"]["operator_approval_receipt"]["path"],
            str(evidence_dir / "operator-approval-receipt.json"),
        )
        self.assertNotIn("preflight-pre.txt", json.dumps(report, sort_keys=True))

    def test_preflight_accepts_builder_inputs_before_approved_manifest(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(report["ready"])
        self.assertEqual(report["ready_scope"], "bundle_builder_inputs_only")
        self.assertTrue(report["copied_log_and_window_manifest_ready"])
        self.assertTrue(report["bundle_inputs_ready"])
        self.assertTrue(report["request_pack_ready"])
        self.assertFalse(report["request_pack_is_runtime_evidence"])
        self.assertFalse(report["request_pack_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["observer_env_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["operator_request_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["copied_log_metadata_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["window_manifest_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["bundle_output_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["preflight_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["completed_receipt_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["sdk_accounting_counts_as_completed_surface"])
        self.assertFalse(report["p0_accounting_counts_as_promoted_surface"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertEqual(report["next_blocker"], "run_offline_evidence_bundle_builder")
        action = report["fastest_next_action"]
        self.assertEqual(action["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            [case["role"] for case in action["required_copied_log_lifecycle_sequence"]],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(
            action["required_copied_log_lifecycle_sequence"][1]["shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            action["required_copied_log_lifecycle_sequence"][1]["safe_status_proof"],
            {
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
        )
        self.assertIn("window-manifest.env", action["required_sibling_sidecars"])
        self.assertEqual(
            report["approved_bundle_manifest_relative_path"],
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        )
        self.assertEqual(
            report["approved_bundle_path"],
            str(copied_log.parent / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"),
        )
        self.assertEqual(report["approved_bundle_checklist"], report["next_required_artifacts"])
        self.assertEqual(
            [artifact["artifact"] for artifact in report["next_required_artifacts"]],
            [
                "copied_obelisk_log",
                "checked_window_manifest_env",
                "window_request_json",
                "observer_window_env",
                "operator_approval_request_md",
                "operator_approval_receipt",
                "preflight_pre_json",
                "preflight_post_json",
                "approved_runtime_principal_lifecycle_evidence_manifest",
            ],
        )
        self.assertEqual(
            [artifact["relative_path"] for artifact in report["approved_bundle_checklist"]],
            [
                "Obelisk.log",
                "window-manifest.env",
                "window-request.json",
                "observer-window.env",
                "operator-approval-request.md",
                "operator-approval-receipt.json",
                "preflight-pre.json",
                "preflight-post.json",
                "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            ],
        )
        self.assertEqual(
            [artifact["present"] for artifact in report["next_required_artifacts"]],
            [True, True, True, True, True, True, True, True, False],
        )
        self.assertEqual(report["approved_bundle_checklist"][-1]["status"], "missing")
        self.assertEqual(
            report["approved_bundle_checklist"][-1]["missing_blocker"],
            "approved_runtime_principal_lifecycle_evidence_manifest_missing",
        )
        self.assertTrue(
            all(
                artifact["counts_as_approved_runtime_evidence_before_checker_acceptance"] is False
                for artifact in report["approved_bundle_checklist"]
            )
        )
        self.assertFalse(report["next_required_artifacts"][-1]["satisfies_approved_runtime_evidence"])
        self.assertNotIn("request_pack_check_failed", report["blockers"])
        self.assertNotIn("copied_log_missing", report["blockers"])
        self.assertNotIn("window_manifest_missing", report["blockers"])
        self.assertIn(
            "bundle_inputs_ready requires the copied log, checked window manifest, completed receipt, preflight sidecars, and checked post-window replay request pack; it does not mean approved runtime evidence already exists",
            report["non_claims"],
        )
        self.assertFalse(report["copy_report_counts_as_approved_runtime_evidence"])
        self.assertEqual(
            report["copy_readiness_context"],
            {
                "report_present": False,
                "report_checked": False,
                "report_accepted": False,
                "copy_readiness": "not_provided",
                "ready_to_copy": False,
                "roles_present": [],
                "missing_roles": [],
                "analysis": {},
                "session_end_missing_correlation_diagnostics": None,
                "reported_blockers": [],
                "source_log_safety": {},
                "source_log_not_ready": {},
                "source_log_not_ready_reason": None,
                "source_log_not_ready_blockers": [],
                "observer_only_no_role_window_detected": False,
                "player_present_but_no_lifecycle_roles": False,
                "player_presence_context": {},
                "player_presence_context_counts_as_approved_runtime_evidence": False,
                "copy_report_counts_as_approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "blockers": [],
            },
        )

    def test_preflight_rejects_stale_window_manifest_commit_before_bundle_command(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            window_manifest.write_text(
                window_manifest.read_text(encoding="utf-8").replace(
                    f"obelisk_commit={TEST_COMMIT}",
                    f"obelisk_commit={STALE_TEST_COMMIT}",
                ),
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertEqual(report["next_blocker"], "window_manifest_obelisk_commit_must_match_current_head")
        self.assertIn("window_manifest_obelisk_commit_not_current_head", report["blockers"])
        binding = report["inputs"]["obelisk_commit_binding"]
        self.assertFalse(binding["ready"])
        self.assertEqual(binding["current_obelisk_commit"], TEST_COMMIT)
        self.assertEqual(binding["window_manifest_obelisk_commit"], STALE_TEST_COMMIT)

    def test_preflight_consumes_ready_log_copy_report_without_widening_evidence(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            write_ready_log_copy_report(copied_log)

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ready"])
        self.assertTrue(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["copy_report_counts_as_approved_runtime_evidence"])
        self.assertEqual(report["next_blocker"], "run_offline_evidence_bundle_builder")
        copy_context = report["copy_readiness_context"]
        self.assertTrue(copy_context["report_present"])
        self.assertTrue(copy_context["report_checked"])
        self.assertTrue(copy_context["report_accepted"])
        self.assertTrue(copy_context["ready_to_copy"])
        self.assertEqual(copy_context["copy_readiness"], "ready_complete_role_triplet")
        self.assertEqual(
            copy_context["roles_present"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(copy_context["missing_roles"], [])
        self.assertFalse(copy_context["copy_report_counts_as_approved_runtime_evidence"])
        self.assertTrue(copy_context["source_log_safety"]["accepted"])
        self.assertFalse(report["copy_report_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertEqual(copy_context["blockers"], [])
        self.assertEqual(
            report["inputs"]["ready_log_copy"]["path"],
            str(copied_log.parent / "ready-log-copy.json"),
        )

    def test_preflight_rejects_ready_log_copy_selected_triplet_drift(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            payload = ready_log_copy_payload(copied_log)
            payload["analysis"]["exact_copied_runtime_triplet"]["selected_sequences"] = [1, 99, 3]
            write_ready_log_copy_report(copied_log, payload)

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertIn(
            "ready_log_copy_exact_copied_runtime_triplet_selected_sequences_mismatch",
            report["blockers"],
        )
        self.assertFalse(report["copy_report_counts_as_approved_runtime_evidence"])

    def test_preflight_blocks_blocked_ready_log_copy_report_exact_ragnarok_shape(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text(
                "\n".join(runtime_log_lines_with_ragnarok_duplicate_start_diagnostic_missing_check_join()) + "\n",
                encoding="utf-8",
            )
            self.write_window_manifest(temp_dir, copied_log)
            write_ready_log_copy_report(copied_log, blocked_ragnarok_ready_log_copy_payload(copied_log))

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertIn("ready_log_copy_not_ready_to_copy", report["blockers"])
        copy_context = report["copy_readiness_context"]
        self.assertTrue(copy_context["report_present"])
        self.assertTrue(copy_context["report_checked"])
        self.assertTrue(copy_context["report_accepted"])
        self.assertFalse(copy_context["ready_to_copy"])
        self.assertEqual(copy_context["copy_readiness"], "blocked_ambiguous_duplicate_lifecycle_roles")
        self.assertEqual(copy_context["missing_roles"], ["session_start_rejected"])
        self.assertIn("source_log_contains_lifecycle_diagnostic_lines", copy_context["reported_blockers"])
        self.assertIn(
            "exact_copied_runtime_triplet_missing_session_start_rejected",
            copy_context["reported_blockers"],
        )
        self.assertEqual(copy_context["analysis"]["duplicate_accepted_roles"], ["session_start"])
        self.assertEqual(copy_context["source_log_safety"]["lifecycle_diagnostic_line_count"], 1)
        blocker = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "ready_log_copy_not_ready_to_copy"
        )
        self.assertEqual(blocker["copy_readiness"], "blocked_ambiguous_duplicate_lifecycle_roles")
        self.assertEqual(blocker["missing_roles"], ["session_start_rejected"])

    def test_preflight_reports_player_presence_without_lifecycle_roles_as_non_evidence(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text(
                "\n".join(
                    [
                        *runtime_log_lines()[:7],
                        f"{log_clock(1)} player_presence_detected instance=arkserver2 "
                        "map=TheIsland players_current=1 presence_detected=true "
                        "target_key=arkserver2:TheIsland:27016",
                        runtime_log_lines()[7],
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.write_window_manifest(temp_dir, copied_log)
            write_ready_log_copy_report(
                copied_log,
                blocked_player_presence_no_role_ready_log_copy_payload(copied_log),
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertIn("ready_log_copy_not_ready_to_copy", report["blockers"])
        self.assertIn("player_present_but_no_lifecycle_roles", report["copy_readiness_context"]["reported_blockers"])
        copy_context = report["copy_readiness_context"]
        self.assertTrue(copy_context["observer_only_no_role_window_detected"])
        self.assertTrue(copy_context["player_present_but_no_lifecycle_roles"])
        self.assertEqual(copy_context["source_log_not_ready_reason"], "observer_enabled_no_lifecycle_roles_post_window")
        self.assertIn("player_present_but_no_lifecycle_roles", copy_context["source_log_not_ready_blockers"])
        self.assertEqual(copy_context["missing_roles"], ["session_start", "session_start_rejected", "session_end"])
        self.assertTrue(copy_context["player_presence_context"]["players_detected"])
        self.assertFalse(copy_context["player_presence_context_counts_as_approved_runtime_evidence"])
        action = report["fastest_next_action"]
        diagnostics = action["observer_no_lifecycle_role_diagnostics"]
        self.assertTrue(diagnostics["player_present_but_no_lifecycle_roles"])
        self.assertIn("player_present_but_no_lifecycle_roles", diagnostics["source_log_not_ready_blockers"])
        self.assertFalse(diagnostics["approved_runtime_evidence"])
        blocker = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "ready_log_copy_not_ready_to_copy"
        )
        self.assertTrue(blocker["player_present_but_no_lifecycle_roles"])
        self.assertTrue(blocker["player_presence_context"]["players_detected"])

    def test_preflight_reports_session_end_missing_correlation_only_as_non_evidence(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text(
                "\n".join(runtime_log_lines_with_only_missing_correlation_session_end()) + "\n",
                encoding="utf-8",
            )
            self.write_window_manifest(temp_dir, copied_log)
            write_ready_log_copy_report(
                copied_log,
                blocked_session_end_missing_correlation_ready_log_copy_payload(copied_log),
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        diagnostics = report["session_end_missing_correlation_diagnostics"]
        self.assertEqual(
            diagnostics["classification"],
            "session_end_missing_correlation_only_non_evidence",
        )
        self.assertFalse(diagnostics["counts_as_approved_runtime_evidence"])
        action_diagnostics = report["fastest_next_action"]["session_end_missing_correlation_diagnostics"]
        self.assertEqual(action_diagnostics["roles_present"], ["session_end"])
        self.assertEqual(
            action_diagnostics["missing_accepted_lifecycle_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertFalse(
            action_diagnostics["required_next_material"][
                "session_end_correlation_status_missing_counts_as_evidence"
            ]
        )

    def test_preflight_rejects_ready_log_copy_report_overclaim(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            payload = ready_log_copy_payload(copied_log)
            payload["approved_runtime_evidence_present"] = True
            payload["counts_as_approved_runtime_evidence"] = True
            write_ready_log_copy_report(copied_log, payload)

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["copy_report_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["copy_readiness_context"]["report_accepted"])
        self.assertIn("ready_log_copy_approved_runtime_evidence_present_not_false", report["blockers"])
        self.assertIn("ready_log_copy_counts_as_approved_runtime_evidence_not_false", report["blockers"])
        self.assertIn("ready_log_copy_readiness_flag_overclaim", report["blockers"])

    def test_preflight_reports_stale_ready_log_copy_sha_before_evidence_acceptance(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            payload = ready_log_copy_payload(copied_log)
            expected_sha256 = hashlib.sha256(copied_log.read_bytes()).hexdigest()
            payload["target_copied_sha256"] = hashlib.sha256(b"stale-ready-log-copy").hexdigest()
            write_ready_log_copy_report(copied_log, payload)

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["copy_readiness_context"]["report_accepted"])
        self.assertIn("ready_log_copy_target_copied_sha256_mismatch", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "ready_log_copy_target_copied_sha256_mismatch"
        )
        self.assertEqual(detail["expected"], expected_sha256)
        self.assertEqual(detail["actual"], payload["target_copied_sha256"])

    def test_preflight_rejects_ready_log_copy_report_from_wrong_evidence_dir(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            payload = ready_log_copy_payload(copied_log)
            payload["evidence_dir"] = str(copied_log.parent.parent / "other-run")
            write_ready_log_copy_report(copied_log, payload)

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["copy_readiness_context"]["report_accepted"])
        self.assertIn("ready_log_copy_evidence_dir_mismatch", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "ready_log_copy_evidence_dir_mismatch"
        )
        self.assertEqual(detail["expected"], str(copied_log.parent.resolve()))
        self.assertEqual(detail["actual"], str((copied_log.parent.parent / "other-run").resolve()))

    def test_preflight_rejects_ready_log_copy_report_outside_fresh_window(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            write_ready_log_copy_report(copied_log, stale_fresh_window_ready_log_copy_payload(copied_log))

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["copy_readiness_context"]["report_accepted"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn(
            "ready_log_copy_copied_log_lifecycle_event_outside_fresh_window",
            report["blockers"],
        )
        self.assertIn(
            "ready_log_copy_ready_to_copy_without_accepted_fresh_window_triplet",
            report["blockers"],
        )

    def test_preflight_accepts_standing_launch_authority_receipt_before_approved_manifest(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log, standing_launch_authority=True)

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ready"])
        self.assertEqual(report["ready_scope"], "bundle_builder_inputs_only")
        self.assertTrue(report["bundle_inputs_ready"])
        self.assertTrue(report["request_pack_ready"])
        self.assertFalse(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["completed_receipt_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_preflight_rejects_standing_receipt_with_current_turn_contradiction(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(
                temp_dir,
                copied_log,
                standing_launch_authority=True,
            )
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            receipt = Path(fields["operator_approval_receipt_path"])
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            payload["operator_current_turn_approval_recorded"] = True
            receipt.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["operator_approval_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertIn(
            "operator_approval_receipt_current_turn_approval_not_false_for_standing_authority",
            report["blockers"],
        )
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_preflight_rejects_stale_preflight_sidecar_missing_current_false_flags(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            preflight_pre = Path(fields["preflight_pre_path"])
            payload = json.loads(preflight_pre.read_text(encoding="utf-8"))
            payload.pop("copied_log_presence_counts_as_approved_runtime_evidence", None)
            preflight_pre.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["preflight_pre_sha256"] = hashlib.sha256(preflight_pre.read_bytes()).hexdigest()
            manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertIn(
            "preflight_pre_json_copied_log_presence_counts_as_approved_runtime_evidence_not_false",
            report["blockers"],
        )

    def test_preflight_rejects_unexpected_legacy_non_evidence_json_sidecar(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "passive-snapshot.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-passive-snapshot.v1",
                        "ready": True,
                        "approved_runtime_evidence": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertIn(
            "unexpected_json_sidecar_passive_snapshot_sidecar_not_approved_runtime_evidence",
            report["blockers"],
        )

    def test_preflight_rejects_generated_receipt_template_left_beside_completed_receipt(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "operator-approval-receipt.template.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-lifecycle-operator-approval-receipt.v1",
                        "status": "generated_template",
                        "receipt_completed": False,
                        "approved_runtime_evidence_present": False,
                        "runtime_evidence_ready": False,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn(
            "unexpected_json_sidecar_approval_or_standing_authority_schema_is_not_approved_runtime_evidence",
            report["blockers"],
        )

    def test_preflight_rejects_stray_confirmed_beta_notice_sidecar(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "beta-notice.confirmed.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
                        "status": "confirmed_send",
                        "confirmed_beta_notice_completed": True,
                        "approved_runtime_evidence_present": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn(
            "unexpected_json_sidecar_notice_prep_sidecar_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn("json_sidecar_readiness_flag_overclaim", report["blockers"])

    def test_preflight_rejects_unexpected_preactivation_executor_json_sidecar(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "preactivation-executor-output.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-lifecycle-preactivation-executor-output.v1",
                        "ready": True,
                        "executor_artifact_counts_as_approved_runtime_evidence": False,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertIn(
            (
                "unexpected_json_sidecar_"
                "preactivation_or_executor_artifact_is_not_approved_runtime_evidence"
            ),
            report["blockers"],
        )

    def test_preflight_rejects_unexpected_route_status_json_sidecar_with_unknown_schema(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "route-status.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.route-status-snapshot.v1",
                        "route_ready": True,
                        "public_sdk_ready": True,
                        "approved_runtime_evidence_present": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertIn(
            "unexpected_json_sidecar_status_summary_schema_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn("json_sidecar_authorization_or_readiness_key_overclaim", report["blockers"])

    def test_preflight_rejects_unexpected_checkjoin_bool_order_sidecar(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "checkjoin-bool-order.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-checkjoin-bool-order.v1",
                        "status": "candidate_only",
                        "bool_order": "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0",
                        "approved_runtime_evidence_present": False,
                        "runtime_evidence_ready": False,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn(
            "unexpected_json_sidecar_rejected_start_candidate_schema_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "unexpected_json_sidecar_input_path_rejected_start_candidate_is_not_approved_runtime_evidence",
            report["blockers"],
        )

    def test_preflight_rejects_unexpected_lifecycle_role_alias_sidecar(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "session-start-rejected-role-alias.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-lifecycle-role-alias.v1",
                        "role_alias": {
                            "alias": "session_start_rejected",
                            "target": "ShooterGameMode.CheckJoinInProgress",
                            "counts_as_role": True,
                        },
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertIn(
            "unexpected_json_sidecar_role_alias_schema_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "unexpected_json_sidecar_input_path_role_alias_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "json_sidecar_lifecycle_role_alias_is_not_approved_runtime_evidence",
            report["blockers"],
        )

    def test_preflight_rejects_unexpected_next_action_plan_json_sidecar(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "next-action-plan.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-lifecycle-next-action-plan.v1",
                        "ready": True,
                        "next_actions": [{"id": "run_bundle_builder"}],
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertIn(
            "unexpected_json_sidecar_next_action_plan_schema_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn("json_sidecar_readiness_flag_overclaim", report["blockers"])

    def test_preflight_rejects_unexpected_contract_review_json_sidecar(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "reviewed-identity-public-contract-decision-record.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-identity-public-contract-decision-record.v1",
                        "accepted_for_contract_review": True,
                        "reviewed_hash_current_contract_review_only": True,
                        "public_sdk_ready": False,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertIn(
            "unexpected_json_sidecar_contract_review_artifact_sidecar_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "json_sidecar_authorization_or_readiness_key_overclaim",
            report["blockers"],
        )

    def test_preflight_rejects_required_sidecar_claim_aliases_before_outputs(self) -> None:
        def nested_non_claim_positive(payload: dict) -> None:
            payload["audit"] = {"non_claims": ["public SDK ready"]}

        def readiness_status_alias(payload: dict) -> None:
            payload["audit"] = {"readiness_status": "stable"}

        def p0_accounting_flag(payload: dict) -> None:
            payload["audit"] = {"p0_accounting_counts_as_promoted_surface": True}

        cases = (
            (
                "nested_non_claim_positive",
                nested_non_claim_positive,
                "json_sidecar_authorization_or_readiness_text_overclaim",
            ),
            (
                "readiness_status_alias",
                readiness_status_alias,
                "json_sidecar_authorization_or_readiness_text_overclaim",
            ),
            (
                "passive_status_accepted_alias",
                lambda payload: payload.update({"passive_status": "accepted"}),
                "json_sidecar_authorization_or_readiness_text_overclaim",
            ),
            (
                "p0_accounting_flag",
                p0_accounting_flag,
                "json_sidecar_readiness_flag_overclaim",
            ),
            (
                "public_reachability_counts_alias",
                lambda payload: payload.update({"public_reachability_counts_as_approved_runtime_evidence": True}),
                "json_sidecar_readiness_flag_overclaim",
            ),
            (
                "public_reachability_dotted_counts_alias",
                lambda payload: payload.update(
                    {"public.reachability.counts.as.approved.runtime.evidence": True}
                ),
                "json_sidecar_readiness_flag_overclaim",
            ),
            (
                "runtime_window_request_output_counts_alias",
                lambda payload: payload.update(
                    {"runtime_window_request_output_counts_as_approved_runtime_evidence": True}
                ),
                "json_sidecar_readiness_flag_overclaim",
            ),
            (
                "planning_artifact_counts_alias",
                lambda payload: payload.update({"planning_artifact_counts_as_approved_runtime_evidence": True}),
                "json_sidecar_readiness_flag_overclaim",
            ),
            (
                "support_package_positive_alias",
                lambda payload: payload.update({"supportPackage": "approved"}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "package_label_runtime_evidence_alias",
                lambda payload: payload.update({"package_label": "runtime evidence accepted"}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "accepted_bundle_source_summary_alias",
                lambda payload: payload.update({"accepted_bundle_source_summary": True}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "zero_source_overclaim_status_alias",
                lambda payload: payload.update(
                    {
                        "status": "blocked",
                        "source_overclaim_total_flag_count": 0,
                        "source_overclaim_summary": {"total": 0},
                    }
                ),
                "json_sidecar_source_overclaim_alias_is_not_approved_runtime_evidence",
            ),
            (
                "nested_evidence_approved_alias",
                lambda payload: payload.update({"evidence": {"approved": True}}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "nested_runtime_observed_alias",
                lambda payload: payload.update({"runtime": {"observed": True}}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "nested_player_session_accepted_alias",
                lambda payload: payload.update({"playerSessions": [{"accepted": True}]}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "nested_lifecycle_proof_validated_alias",
                lambda payload: payload.update({"lifecycle": {"proof": {"status": "validated"}}}),
                "json_sidecar_authorization_or_readiness_text_overclaim",
            ),
            (
                "nested_bundle_ready_alias",
                lambda payload: payload.update({"bundle": {"ready": True}}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "nested_sidecar_complete_alias",
                lambda payload: payload.update({"sidecar": {"complete": True}}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "nested_artifact_status_accepted_alias",
                lambda payload: payload.update({"artifact": {"status": "accepted"}}),
                "json_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "nested_approved_manifest_schema_without_positive_flags",
                lambda payload: payload.update(
                    {
                        "audit": [
                            {
                                "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                                "approved_runtime_evidence_present": False,
                                "runtime_evidence_ready": False,
                                "promotion_ready": False,
                                "public_sdk_ready": False,
                                "runtime_ready": False,
                            }
                        ]
                    }
                ),
                "json_sidecar_nested_approved_runtime_manifest_schema",
            ),
        )
        for name, mutate, expected_blocker in cases:
            with self.subTest(name=name):
                with self.temp_offline_workspace() as temp:
                    temp_dir = Path(temp)
                    copied_log = copied_log_path(temp_dir)
                    copied_log.parent.mkdir(parents=True, exist_ok=True)
                    copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
                    manifest = self.write_window_manifest(temp_dir, copied_log)
                    fields = dict(
                        line.split("=", 1)
                        for line in manifest.read_text(encoding="utf-8").splitlines()
                        if line and not line.startswith("#")
                    )
                    sidecar = Path(fields["preflight_pre_path"])
                    payload = json.loads(sidecar.read_text(encoding="utf-8"))
                    mutate(payload)
                    sidecar.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                    fields["preflight_pre_sha256"] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
                    manifest.write_text(
                        "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                        encoding="utf-8",
                    )

                    result = self.run_preflight(copied_log.parent)

                self.assertEqual(result.returncode, 1)
                report = json.loads(result.stdout)
                self.assertFalse(report["ready"])
                self.assertFalse(report["bundle_inputs_ready"])
                self.assertIn(expected_blocker, report["blockers"])

    def test_approved_runtime_manifest_check_rejects_indirect_evidence_aliases(self) -> None:
        cases = (
            "public_reachability_counts_as_approved_runtime_evidence",
            "runtime_window_request_output_counts_as_approved_runtime_evidence",
            "planning_artifact_counts_as_approved_runtime_evidence",
        )
        for alias in cases:
            with self.subTest(alias=alias):
                original = bundle_builder.run_json_check
                blockers: list[dict] = []

                def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
                    payload = {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                        "mode": "consume",
                        "ready_scope": "runtime_evidence_only",
                        "ready": True,
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "v1_completion_ready": False,
                        "runtime_ready": False,
                        "public_capability_bits_now": [],
                        "public_callback_abi_now": [],
                        "blockers": [],
                        "remaining_blockers": [],
                        "next_blocker": "identity_public_contract_gate_missing",
                        alias: True,
                    }
                    return 0, payload, ""

                try:
                    bundle_builder.run_json_check = fake_run_json_check
                    state = bundle_builder.approved_runtime_manifest_check_state(
                        {"exists": True, "path": Path("approved-runtime-principal-lifecycle-evidence.json")},
                        blockers,
                    )
                finally:
                    bundle_builder.run_json_check = original

                self.assertTrue(state["checked"])
                self.assertFalse(state["ready"])
                self.assertEqual(
                    state["blockers"],
                    ["approved_runtime_manifest_check_readiness_overclaim"],
                )
                self.assertIn(alias, state["readiness_overclaim"])
                self.assertIn("approved_runtime_manifest_check_failed", [blocker["reason"] for blocker in blockers])

    def test_preflight_validates_present_approved_manifest(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = copied_log.parent / "approved-bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)
            self.assertEqual(result.returncode, 0, result.stderr)

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 0)
        report = json.loads(preflight.stdout)
        self.assertTrue(report["approved_runtime_manifest_present"])
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["approved_runtime_evidence_ready"])
        self.assertIsNone(report["current_route_blocker"])
        self.assertIsNone(report["fastest_next_action"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["sdk_accounting_counts_as_completed_surface"])
        self.assertFalse(report["p0_accounting_counts_as_promoted_surface"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["inputs"]["approved_runtime_manifest_check"]["checked"])
        self.assertTrue(report["inputs"]["approved_runtime_manifest_check"]["ready"])
        self.assertEqual(report["inputs"]["approved_runtime_manifest_check"]["exit_code"], 0)
        self.assertTrue(report["inputs"]["approved_runtime_manifest_check"]["checker_ready"])
        self.assertEqual(
            report["approved_bundle_path"],
            str(copied_log.parent / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"),
        )
        self.assertEqual(
            report["approved_bundle_checklist"][-1]["status"],
            "accepted_by_approved_runtime_evidence_checker",
        )
        self.assertIsNone(report["approved_bundle_checklist"][-1]["missing_blocker"])
        self.assertTrue(report["next_required_artifacts"][-1]["satisfies_approved_runtime_evidence"])

    def test_preflight_rejects_expected_generated_bundle_report_current_turn_overclaim(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = copied_log.parent / "approved-bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)
            self.assertEqual(result.returncode, 0, result.stderr)

            bundle_report_path = output_dir / "evidence-bundle-report.json"
            bundle_report = json.loads(bundle_report_path.read_text(encoding="utf-8"))
            bundle_report["current_turn_runtime_authorized"] = True
            bundle_report.pop("bundle_report_identity", None)
            bundle_report["bundle_report_identity"] = bundle_builder.report_identity(bundle_report)
            bundle_report_path.write_text(json.dumps(bundle_report, sort_keys=True) + "\n", encoding="utf-8")

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn(
            "approved_bundle_generated_sidecar_false_flag_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "$.current_turn_runtime_authorized",
            [detail.get("key_path") for detail in report["blocker_details"]],
        )
        self.assertFalse(report["next_required_artifacts"][-1]["satisfies_approved_runtime_evidence"])

    def test_preflight_rejects_expected_generated_bundle_report_contract_review_alias(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = copied_log.parent / "approved-bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)
            self.assertEqual(result.returncode, 0, result.stderr)

            bundle_report_path = output_dir / "evidence-bundle-report.json"
            bundle_report = json.loads(bundle_report_path.read_text(encoding="utf-8"))
            bundle_report["accepted_for_contract_review"] = True
            bundle_report.pop("bundle_report_identity", None)
            bundle_report["bundle_report_identity"] = bundle_builder.report_identity(bundle_report)
            bundle_report_path.write_text(json.dumps(bundle_report, sort_keys=True) + "\n", encoding="utf-8")

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertIn(
            "approved_bundle_generated_sidecar_contract_review_alias_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "$.accepted_for_contract_review",
            [detail.get("key_path") for detail in report["blocker_details"]],
        )

    def test_preflight_rejects_expected_generated_bundle_report_acceptance_alias(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = copied_log.parent / "approved-bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)
            self.assertEqual(result.returncode, 0, result.stderr)

            bundle_report_path = output_dir / "evidence-bundle-report.json"
            bundle_report = json.loads(bundle_report_path.read_text(encoding="utf-8"))
            bundle_report["runtimeEvidenceAcceptance"] = True
            bundle_report.pop("bundle_report_identity", None)
            bundle_report["bundle_report_identity"] = bundle_builder.report_identity(bundle_report)
            bundle_report_path.write_text(json.dumps(bundle_report, sort_keys=True) + "\n", encoding="utf-8")

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertIn(
            "approved_bundle_generated_sidecar_authorization_or_readiness_alias_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "$.runtimeEvidenceAcceptance",
            [detail.get("key_path") for detail in report["blocker_details"]],
        )

    def test_preflight_rejects_extra_approved_bundle_sidecar_with_accepted_fields(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = copied_log.parent / "approved-bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)
            self.assertEqual(result.returncode, 0, result.stderr)
            canonical = output_dir / "approved-runtime-principal-lifecycle-evidence.json"
            stale = output_dir / "approved-runtime-principal-lifecycle-evidence.stale.json"
            stale_payload = json.loads(canonical.read_text(encoding="utf-8"))
            stale_payload["operational_window"]["run_id"] = "20260601T121500Z-player-principal-lifecycle"
            stale_payload["operational_window"]["target"] = {"instance": "arkserver3", "map": "Genesis2"}
            stale_payload["operational_window"]["copied_log"]["sha256"] = hashlib.sha256(b"stale-log").hexdigest()
            stale.write_text(json.dumps(stale_payload, sort_keys=True) + "\n", encoding="utf-8")

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("unexpected_approved_bundle_json_sidecar_not_exact_relative_path", report["blockers"])
        self.assertIn(
            "unexpected_approved_bundle_json_sidecar_approved_runtime_manifest_sidecar_not_checked_bundle_output",
            report["blockers"],
        )
        self.assertFalse(report["next_required_artifacts"][-1]["satisfies_approved_runtime_evidence"])

    def test_preflight_rejects_approved_manifest_at_wrong_relative_path_when_exact_path_missing(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            alternate = copied_log.parent / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.copy.json"
            alternate.parent.mkdir(parents=True, exist_ok=True)
            alternate.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                        "artifact_status": "approved_runtime_observer_summary",
                        "readiness_classification": "runtime_evidence_only",
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("approved_runtime_manifest_missing", report["blockers"])
        self.assertIn("unexpected_approved_bundle_json_sidecar_not_exact_relative_path", report["blockers"])
        self.assertEqual(
            report["approved_bundle_path"],
            str(copied_log.parent / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"),
        )

    def test_preflight_rejects_approved_manifest_copied_from_different_run(self) -> None:
        old_window_start = globals()["WINDOW_START"]
        old_run_id = globals()["RUN_ID"]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = copied_log.parent / "approved-bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)
            self.assertEqual(result.returncode, 0, result.stderr)
            approved_manifest = output_dir / "approved-runtime-principal-lifecycle-evidence.json"

            try:
                alternate_start = old_window_start + timedelta(minutes=2)
                globals()["WINDOW_START"] = alternate_start
                globals()["RUN_ID"] = alternate_start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
                alternate_log = copied_log_path(temp_dir)
                alternate_log.parent.mkdir(parents=True, exist_ok=True)
                alternate_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
                self.write_window_manifest(temp_dir, alternate_log)
                alternate_approved_dir = alternate_log.parent / "approved-bundle"
                alternate_approved_dir.mkdir(parents=True, exist_ok=True)
                (alternate_approved_dir / approved_manifest.name).write_bytes(approved_manifest.read_bytes())

                preflight = self.run_preflight(alternate_log.parent)
            finally:
                globals()["WINDOW_START"] = old_window_start
                globals()["RUN_ID"] = old_run_id

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["bundle_inputs_ready"])
        self.assertTrue(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("approved_runtime_manifest_run_id_mismatch", report["blockers"])
        self.assertIn("approved_runtime_manifest_copied_log_path_mismatch", report["blockers"])
        approved_check = report["inputs"]["approved_runtime_manifest_check"]
        self.assertTrue(approved_check["checked"])
        self.assertFalse(approved_check["ready"])
        self.assertEqual(approved_check["run_id"], old_run_id)
        self.assertEqual(approved_check["copied_log_path"], str(copied_log.resolve()))

    def test_preflight_surfaces_approved_checker_blockers_after_operator_sidecar_drift(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = copied_log.parent / "approved-bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)
            self.assertEqual(result.returncode, 0, result.stderr)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            operator_approval_receipt = Path(fields["operator_approval_receipt_path"])
            operator_approval_receipt.write_text("{not-valid-json\n", encoding="utf-8")

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("window_manifest_check_failed", report["blockers"])
        self.assertIn("approved_runtime_manifest_check_failed", report["blockers"])
        approved_check = report["inputs"]["approved_runtime_manifest_check"]
        self.assertTrue(approved_check["checked"])
        self.assertFalse(approved_check["ready"])
        self.assertEqual(approved_check["exit_code"], 1)
        self.assertIn(
            "operational_window_operator_approval_receipt_json_invalid",
            approved_check["blockers"],
        )
        self.assertIn(
            "operational_window_operator_approval_receipt_json_invalid",
            next(
                blocker["approved_runtime_check_blockers"]
                for blocker in report["blocker_details"]
                if blocker["reason"] == "approved_runtime_manifest_check_failed"
            ),
        )
        self.assertNotIn(
            "operational_window_operator_approval_receipt_json_invalid",
            report["inputs"]["window_manifest_check"]["blockers"],
        )

    def test_preflight_rejects_window_manifest_sidecar_outside_copied_log_dir(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if "=" in line
            )
            original = Path(fields["preflight_pre_path"])
            alternate = (
                copied_log.parent.parent
                / "alternate-sidecars"
                / RUN_ID
                / "preflight-pre.json"
            )
            alternate.parent.mkdir(parents=True, exist_ok=True)
            alternate.write_bytes(original.read_bytes())
            fields["preflight_pre_path"] = str(alternate)
            fields["preflight_pre_sha256"] = hashlib.sha256(alternate.read_bytes()).hexdigest()
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["ready"])
        self.assertIn("window_manifest_check_failed", report["blockers"])
        self.assertIn(
            "preflight_pre_path_not_beside_window_manifest",
            report["inputs"]["window_manifest_check"]["blockers"],
        )

    def test_preflight_rejects_invalid_present_approved_manifest(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            approved_dir = copied_log.parent / "approved-bundle"
            approved_dir.mkdir(parents=True, exist_ok=True)
            (approved_dir / "approved-runtime-principal-lifecycle-evidence.json").write_text(
                json.dumps({"schema": "not-approved"}),
                encoding="utf-8",
            )

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertTrue(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("approved_runtime_manifest_check_failed", report["blockers"])
        self.assertTrue(report["inputs"]["approved_runtime_manifest_check"]["checked"])
        self.assertEqual(report["approved_bundle_checklist"][-1]["status"], "present_but_checker_failed")
        self.assertIsNone(report["approved_bundle_checklist"][-1]["missing_blocker"])

    def test_preflight_rejects_shape_fixture_in_approved_manifest_slot(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            approved_dir = copied_log.parent / "approved-bundle"
            approved_dir.mkdir(parents=True, exist_ok=True)
            (approved_dir / "approved-runtime-principal-lifecycle-evidence.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1",
                        "artifact_status": "synthetic_redacted_fixture",
                        "readiness_classification": "shape_only_private_fixture",
                    }
                ),
                encoding="utf-8",
            )

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertTrue(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("approved_runtime_manifest_check_failed", report["blockers"])
        approved_check = report["inputs"]["approved_runtime_manifest_check"]
        self.assertTrue(approved_check["checked"])
        self.assertFalse(approved_check["ready"])
        self.assertIn(
            "synthetic_shape_fixture_is_not_approved_runtime_evidence",
            approved_check["blockers"],
        )

    def test_preflight_rejects_runtime_observer_summary_in_approved_manifest_slot(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            approved_dir = copied_log.parent / "approved-bundle"
            approved_dir.mkdir()
            (approved_dir / "approved-runtime-principal-lifecycle-evidence.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.runtime-observer-log-summary.v1",
                        "review_scope": "runtime_observer_evidence_summary",
                        "readiness_gate": "none",
                        "ready": False,
                        "evidence": {
                            "kind": "runtime-observer-log",
                            "server_paths_allowed": False,
                            "sources": [{"path": str(copied_log), "sha256": "0" * 64, "line_count": 0}],
                        },
                        "modules": {},
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertTrue(report["approved_runtime_manifest_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        approved_check = report["inputs"]["approved_runtime_manifest_check"]
        self.assertTrue(approved_check["checked"])
        self.assertFalse(approved_check["ready"])
        self.assertIn(
            "runtime_observer_summary_is_not_approved_runtime_evidence",
            approved_check["blockers"],
        )

    def test_preflight_rejects_bad_request_pack_even_with_log_and_manifest_inputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            request_pack = Path(fields["request_pack_path"])
            request_pack.write_text("{}", encoding="utf-8")
            fields["request_pack_sha256"] = hashlib.sha256(request_pack.read_bytes()).hexdigest()
            manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["copied_log_and_window_manifest_ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertEqual(report["next_blocker"], "checked_post_window_replay_sidecars_required")
        self.assertIn("request_pack_check_failed", report["blockers"])
        self.assertIn("window_manifest_check_failed", report["blockers"])

    def test_preflight_rejects_stale_request_pack_schema_even_with_log_and_manifest_inputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            request_pack = Path(fields["request_pack_path"])
            payload = json.loads(request_pack.read_text(encoding="utf-8"))
            payload.pop("player_notice_action")
            payload.pop("passive_wait_boundary")
            request_pack.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["request_pack_sha256"] = hashlib.sha256(request_pack.read_bytes()).hexdigest()
            manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertIn("request_pack_check_failed", report["blockers"])
        self.assertIn("window_manifest_check_failed", report["blockers"])
        self.assertIn(
            "request_pack_current_schema_key_missing",
            report["inputs"]["window_manifest_check"]["blockers"],
        )

    def test_preflight_rejects_copied_log_manifest_sha_mismatch_before_input_ready(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            fields["copied_log_sha256"] = hashlib.sha256(b"stale-copied-log").hexdigest()
            manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["copied_log_and_window_manifest_files_present"])
        self.assertFalse(report["copied_log_and_window_manifest_ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertEqual(report["next_blocker"], "copied_log_and_window_manifest_binding_required")
        self.assertIn("copied_log_manifest_sha256_mismatch", report["blockers"])
        self.assertIn("window_manifest_check_failed", report["blockers"])
        self.assertIn(
            "copied_log_sha256_mismatch",
            report["inputs"]["window_manifest_check"]["blockers"],
        )

    def test_preflight_bundle_inputs_ready_requires_completed_receipt(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            Path(fields["operator_approval_receipt_path"]).unlink()

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["copied_log_and_window_manifest_ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "checked_post_window_replay_sidecars_required")
        self.assertIn("operator_approval_receipt_missing", report["blockers"])
        self.assertIn("window_manifest_check_failed", report["blockers"])

    def test_preflight_bundle_inputs_ready_requires_implicit_operator_request_sibling(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            request_pack = Path(fields["request_pack_path"])
            operator_request = request_pack.parent / "operator-approval-request.md"
            operator_request.unlink()

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["copied_log_and_window_manifest_ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertFalse(report["operator_request_ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "checked_post_window_replay_sidecars_required")
        self.assertIn("operator_request_missing", report["blockers"])
        self.assertIn("request_pack_check_failed", report["blockers"])
        self.assertIn("window_manifest_check_failed", report["blockers"])
        self.assertEqual(report["inputs"]["operator_request"]["path"], str(operator_request))
        self.assertFalse(report["inputs"]["operator_request"]["exists"])
        operator_artifact = next(
            artifact
            for artifact in report["next_required_artifacts"]
            if artifact["artifact"] == "operator_approval_request_md"
        )
        self.assertEqual(operator_artifact["path"], str(operator_request))
        self.assertFalse(operator_artifact["present"])
        self.assertFalse(operator_artifact["satisfies_approved_runtime_evidence"])

    def test_preflight_reports_non_sibling_operator_request_contract_as_missing_canonical_sidecar(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            request_pack = Path(fields["request_pack_path"])
            operator_request = request_pack.parent / "operator-approval-request.md"
            alternate = (
                copied_log.parent.parent
                / "alternate-sidecars"
                / RUN_ID
                / "operator-approval-request.md"
            )
            alternate.parent.mkdir(parents=True)
            alternate.write_bytes(operator_request.read_bytes())
            operator_request.unlink()
            request_payload = json.loads(request_pack.read_text(encoding="utf-8"))
            request_payload["post_window_replay_contract"]["sidecars"]["operator_approval_request_path"] = str(alternate)
            request_pack.write_text(json.dumps(request_payload, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertFalse(report["operator_request_ready"])
        self.assertIn("operator_request_missing", report["blockers"])
        self.assertEqual(report["inputs"]["operator_request"]["path"], str(operator_request))
        self.assertNotEqual(report["inputs"]["operator_request"]["path"], str(alternate))
        self.assertIn(
            "post_window_replay_contract_operator_approval_request_path_not_exact_expected_path",
            report["inputs"]["request_pack_check"]["blockers"],
        )

    def test_preflight_rejects_operator_markdown_drift_even_with_log_and_manifest_inputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            request_pack = Path(fields["request_pack_path"])
            operator_request = request_pack.parent / "operator-approval-request.md"
            operator_request.write_text(
                operator_request.read_text(encoding="utf-8").replace("dispatch limit=0", "dispatch limit=1"),
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["copied_log_and_window_manifest_ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertEqual(report["next_blocker"], "checked_post_window_replay_sidecars_required")
        self.assertIn("request_pack_check_failed", report["blockers"])
        self.assertIn("window_manifest_check_failed", report["blockers"])

    def test_preflight_request_pack_ready_requires_valid_preflight_sidecars(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            preflight_pre = Path(fields["preflight_pre_path"])
            payload = json.loads(preflight_pre.read_text(encoding="utf-8"))
            payload["mode"] = "stable"
            preflight_pre.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["preflight_pre_sha256"] = hashlib.sha256(preflight_pre.read_bytes()).hexdigest()
            manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_preflight(copied_log.parent)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["copied_log_and_window_manifest_ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["request_pack_ready"])
        self.assertEqual(report["next_blocker"], "checked_post_window_replay_sidecars_required")
        self.assertTrue(report["inputs"]["request_pack_check"]["ready"])
        self.assertFalse(report["inputs"]["window_manifest_check"]["ready"])
        self.assertIn("window_manifest_check_failed", report["blockers"])

    def test_approved_runtime_manifest_check_state_requires_checker_ready_and_zero_exit(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                1,
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "ready": False,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "blockers": ["forced_checker_failure"],
                    "next_blocker": "approved_runtime_evidence_not_accepted",
                },
                "forced failure",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.approved_runtime_manifest_check_state(
                {"exists": True, "path": Path("approved-runtime-principal-lifecycle-evidence.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertEqual(state["exit_code"], 1)
        self.assertFalse(state["ready"])
        self.assertFalse(state["checker_ready"])
        self.assertEqual(state["blockers"], ["forced_checker_failure"])
        self.assertIn("approved_runtime_manifest_check_failed", [blocker["reason"] for blocker in blockers])

    def test_approved_runtime_manifest_check_state_forwards_partial_start_end_diagnostics(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []
        observed_shape = {
            "shape": "ShooterGameMode.CheckJoinInProgress(0,0)",
            "target": "ShooterGameMode.CheckJoinInProgress",
            "copied_bool_values": ["0", "0"],
        }

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                1,
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "consume",
                    "ready_scope": "runtime_evidence_only",
                    "ready": False,
                    "approved_runtime_evidence_present": False,
                    "runtime_evidence_ready": False,
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "v1_completion_ready": False,
                    "runtime_ready": False,
                    "public_capability_bits_now": [],
                    "public_callback_abi_now": [],
                    "blockers": ["runtime_summary_strict_rejected_start_missing"],
                    "remaining_blockers": ["approved_runtime_evidence_not_accepted"],
                    "next_blocker": "approved_runtime_evidence_not_accepted",
                    "partial_start_end_present": True,
                    "missing_strict_rejected_start": True,
                    "strict_rejected_start_expected_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
                    "strict_rejected_start_observed_shape": observed_shape,
                },
                "strict rejected start missing",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.approved_runtime_manifest_check_state(
                {"exists": True, "path": Path("approved-runtime-principal-lifecycle-evidence.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertFalse(state["ready"])
        self.assertTrue(state["partial_start_end_present"])
        self.assertTrue(state["missing_strict_rejected_start"])
        self.assertEqual(state["strict_rejected_start_observed_shape"], observed_shape)
        failure = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_manifest_check_failed"
        )
        self.assertTrue(failure["partial_start_end_present"])
        self.assertTrue(failure["missing_strict_rejected_start"])
        self.assertEqual(failure["strict_rejected_start_observed_shape"], observed_shape)

    def test_approved_runtime_manifest_check_requires_exit_zero_even_when_checker_payload_ready(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                1,
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "ready": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "blockers": [],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "nonzero exit",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.approved_runtime_manifest_check_state(
                {"exists": True, "path": Path("approved-runtime-principal-lifecycle-evidence.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertEqual(state["exit_code"], 1)
        self.assertTrue(state["checker_ready"])
        self.assertFalse(state["ready"])
        self.assertIn("approved_runtime_manifest_check_failed", [blocker["reason"] for blocker in blockers])

    def test_approved_runtime_manifest_check_does_not_accept_strict_selection_without_ready_flags(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                0,
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "consume",
                    "ready_scope": "runtime_evidence_only",
                    "ready": True,
                    "approved_runtime_evidence_present": False,
                    "runtime_evidence_ready": False,
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "v1_completion_ready": False,
                    "runtime_ready": False,
                    "public_capability_bits_now": [],
                    "public_callback_abi_now": [],
                    "blockers": [],
                    "remaining_blockers": [],
                    "next_blocker": "identity_public_contract_gate_missing",
                    "strict_lifecycle_triplet_selection": {
                        "accepted": True,
                        "status": "accepted",
                        "selected_roles": ["session_start", "session_start_rejected", "session_end"],
                    },
                },
                "",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.approved_runtime_manifest_check_state(
                {"exists": True, "path": Path("approved-runtime-principal-lifecycle-evidence.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertTrue(state["checker_ready"])
        self.assertTrue(state["strict_lifecycle_triplet_selection"]["accepted"])
        self.assertFalse(state["ready"])
        self.assertIn("approved_runtime_manifest_check_failed", [blocker["reason"] for blocker in blockers])

    def test_approved_runtime_manifest_check_rejects_public_overclaim_fields(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                0,
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "ready": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": True,
                    "v1_completion_ready": False,
                    "runtime_ready": False,
                    "public_capability_bits_now": ["OBELISK_PUBLIC_IDENTITY"],
                    "public_callback_abi_now": [],
                    "blockers": [],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.approved_runtime_manifest_check_state(
                {"exists": True, "path": Path("approved-runtime-principal-lifecycle-evidence.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertFalse(state["ready"])
        self.assertTrue(state["checker_ready"])
        self.assertIn("approved_runtime_manifest_check_failed", [blocker["reason"] for blocker in blockers])

    def test_approved_runtime_manifest_check_requires_exact_report_contract(self) -> None:
        cases = (
            ("wrong_schema", {"schema": "obelisk.wrong-check.v1"}),
            ("wrong_mode", {"mode": "public_readiness"}),
            ("wrong_ready_scope", {"ready_scope": "public_sdk"}),
        )
        for name, overrides in cases:
            with self.subTest(name=name):
                original = bundle_builder.run_json_check
                blockers: list[dict] = []

                def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
                    payload = {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                        "mode": "consume",
                        "ready_scope": "runtime_evidence_only",
                        "ready": True,
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "v1_completion_ready": False,
                        "runtime_ready": False,
                        "public_capability_bits_now": [],
                        "public_callback_abi_now": [],
                        "blockers": [],
                        "remaining_blockers": [],
                        "next_blocker": "identity_public_contract_gate_missing",
                    }
                    payload.update(overrides)
                    return 0, payload, ""

                try:
                    bundle_builder.run_json_check = fake_run_json_check
                    state = bundle_builder.approved_runtime_manifest_check_state(
                        {"exists": True, "path": Path("approved-runtime-principal-lifecycle-evidence.json")},
                        blockers,
                    )
                finally:
                    bundle_builder.run_json_check = original

                self.assertTrue(state["checked"])
                self.assertFalse(state["ready"])
                self.assertIn("approved_runtime_manifest_check_failed", [blocker["reason"] for blocker in blockers])

    def test_approved_runtime_manifest_check_rejects_contradictory_ready_report(self) -> None:
        cases = (
            ("ready_with_blockers", {"blockers": ["contradictory_ready_blocker"]}),
            ("ready_with_remaining_blockers", {"remaining_blockers": ["approved_runtime_evidence_not_accepted"]}),
            ("wrong_next_blocker", {"next_blocker": "approved_runtime_evidence_not_accepted"}),
        )
        for name, overrides in cases:
            with self.subTest(name=name):
                original = bundle_builder.run_json_check
                blockers: list[dict] = []

                def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
                    payload = {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                        "mode": "consume",
                        "ready_scope": "runtime_evidence_only",
                        "ready": True,
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "v1_completion_ready": False,
                        "runtime_ready": False,
                        "public_capability_bits_now": [],
                        "public_callback_abi_now": [],
                        "blockers": [],
                        "remaining_blockers": [],
                        "next_blocker": "identity_public_contract_gate_missing",
                    }
                    payload.update(overrides)
                    return 0, payload, ""

                try:
                    bundle_builder.run_json_check = fake_run_json_check
                    state = bundle_builder.approved_runtime_manifest_check_state(
                        {"exists": True, "path": Path("approved-runtime-principal-lifecycle-evidence.json")},
                        blockers,
                    )
                finally:
                    bundle_builder.run_json_check = original

                self.assertTrue(state["checked"])
                self.assertFalse(state["ready"])
                self.assertIn("approved_runtime_manifest_check_failed", [blocker["reason"] for blocker in blockers])

    def test_request_pack_check_requires_exit_zero_even_when_checker_payload_ready(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []
        observed_commands: list[list[str]] = []

        def fake_run_json_check(command: list[str]) -> tuple[int, dict, str]:
            observed_commands.append(command)
            return (
                1,
                {
                    "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
                    "ready": True,
                    "request_pack_ready": True,
                    "blockers": [],
                    "next_blocker": "operator_current_turn_runtime_window_approval_required",
                },
                "nonzero exit",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.request_pack_check_state(
                {"exists": True, "path": Path("player-principal-lifecycle-window-request.json")},
                {"exists": True, "path": Path("player-principal-lifecycle-observer.env")},
                {"exists": True, "path": Path("operator-approval-receipt.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertEqual(state["exit_code"], 1)
        self.assertTrue(state["checker_ready"])
        self.assertFalse(state["ready"])
        self.assertIn("request_pack_check_failed", [blocker["reason"] for blocker in blockers])
        self.assertTrue(observed_commands)
        self.assertIn("--post-window-replay", observed_commands[0])
        self.assertIn("--operator-approval-receipt", observed_commands[0])
        self.assertIn("operator-approval-receipt.json", [str(part) for part in observed_commands[0]])

    def test_request_pack_check_requires_post_window_replay_echo(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                0,
                {
                    "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
                    "ready": True,
                    "request_pack_ready": True,
                    "blockers": [],
                    "next_blocker": "operator_current_turn_runtime_window_approval_required",
                },
                "",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.request_pack_check_state(
                {"exists": True, "path": Path("player-principal-lifecycle-window-request.json")},
                {"exists": True, "path": Path("player-principal-lifecycle-observer.env")},
                {"exists": True, "path": Path("operator-approval-receipt.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertEqual(state["exit_code"], 0)
        self.assertTrue(state["checker_ready"])
        self.assertFalse(state["ready"])
        self.assertFalse(state["post_window_replay"])
        self.assertFalse(state["post_window_replay_expiry_tolerated"])
        self.assertIn("request_pack_check_failed", [blocker["reason"] for blocker in blockers])

    def test_request_pack_check_requires_expired_window_tolerance(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                0,
                {
                    "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
                    "ready": True,
                    "request_pack_ready": True,
                    "post_window_replay": True,
                    "post_window_replay_expiry_tolerated": False,
                    "blockers": [],
                    "next_blocker": "operator_current_turn_runtime_window_approval_required",
                },
                "",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.request_pack_check_state(
                {"exists": True, "path": Path("player-principal-lifecycle-window-request.json")},
                {"exists": True, "path": Path("player-principal-lifecycle-observer.env")},
                {"exists": True, "path": Path("operator-approval-receipt.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertEqual(state["exit_code"], 0)
        self.assertTrue(state["checker_ready"])
        self.assertFalse(state["ready"])
        self.assertTrue(state["post_window_replay"])
        self.assertFalse(state["post_window_replay_expiry_tolerated"])
        self.assertIn("request_pack_check_failed", [blocker["reason"] for blocker in blockers])

    def test_request_pack_check_accepts_post_window_replay_expired_only(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                0,
                {
                    "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
                    "ready": True,
                    "request_pack_ready": True,
                    "post_window_replay": True,
                    "post_window_replay_expiry_tolerated": True,
                    "blockers": [],
                    "next_blocker": "operator_current_turn_runtime_window_approval_required",
                },
                "",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.request_pack_check_state(
                {"exists": True, "path": Path("player-principal-lifecycle-window-request.json")},
                {"exists": True, "path": Path("player-principal-lifecycle-observer.env")},
                {"exists": True, "path": Path("operator-approval-receipt.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertTrue(state["ready"])
        self.assertTrue(state["post_window_replay"])
        self.assertTrue(state["post_window_replay_expiry_tolerated"])
        self.assertNotIn("request_pack_check_failed", [blocker["reason"] for blocker in blockers])

    def test_request_pack_check_rejects_post_window_replay_expired_plus_other_blocker(self) -> None:
        original = bundle_builder.run_json_check
        blockers: list[dict] = []

        def fake_run_json_check(_command: list[str]) -> tuple[int, dict, str]:
            return (
                1,
                {
                    "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
                    "ready": False,
                    "request_pack_ready": False,
                    "post_window_replay": True,
                    "post_window_replay_expiry_tolerated": False,
                    "blockers": ["approved_window_expired", "operator_request_markdown_mismatch"],
                    "next_blocker": "request_pack_not_accepted",
                },
                "blocked",
            )

        try:
            bundle_builder.run_json_check = fake_run_json_check
            state = bundle_builder.request_pack_check_state(
                {"exists": True, "path": Path("player-principal-lifecycle-window-request.json")},
                {"exists": True, "path": Path("player-principal-lifecycle-observer.env")},
                {"exists": True, "path": Path("operator-approval-receipt.json")},
                blockers,
            )
        finally:
            bundle_builder.run_json_check = original

        self.assertTrue(state["checked"])
        self.assertFalse(state["ready"])
        self.assertEqual(state["blockers"], ["approved_window_expired", "operator_request_markdown_mismatch"])
        self.assertIn("request_pack_check_failed", [blocker["reason"] for blocker in blockers])

    def test_window_manifest_check_requires_exit_zero_even_when_checker_payload_ready(self) -> None:
        original = bundle_builder.run_window_manifest_replay_check
        blockers: list[dict] = []
        observed_paths: list[Path] = []

        def fake_run_window_manifest_replay_check(path: Path) -> subprocess.CompletedProcess[str]:
            observed_paths.append(path)
            payload = {
                "schema": "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1",
                "ready": True,
                "operational_window_manifest_ready": True,
                "post_window_replay": True,
                "operator_approval_receipt": {"verified": True},
                "blockers": [],
                "next_blocker": "approved_runtime_observer_log_summary_and_manifest_missing",
            }
            return subprocess.CompletedProcess(
                ["window-manifest-replay"],
                1,
                json.dumps(payload),
                "nonzero exit",
            )

        try:
            bundle_builder.run_window_manifest_replay_check = fake_run_window_manifest_replay_check
            state = bundle_builder.window_manifest_check_state(
                {"exists": True, "path": Path("player-principal-lifecycle-window-manifest.txt")},
                blockers,
            )
        finally:
            bundle_builder.run_window_manifest_replay_check = original

        self.assertTrue(state["checked"])
        self.assertEqual(state["exit_code"], 1)
        self.assertTrue(state["checker_ready"])
        self.assertFalse(state["ready"])
        self.assertIn("window_manifest_check_failed", [blocker["reason"] for blocker in blockers])
        self.assertEqual(observed_paths, [Path("player-principal-lifecycle-window-manifest.txt")])

    def test_window_manifest_check_rejects_ready_payload_with_blockers(self) -> None:
        original = bundle_builder.run_window_manifest_replay_check
        blockers: list[dict] = []

        def fake_run_window_manifest_replay_check(_path: Path) -> subprocess.CompletedProcess[str]:
            payload = {
                "schema": "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1",
                "ready": True,
                "operational_window_manifest_ready": True,
                "post_window_replay": True,
                "operator_approval_receipt": {"verified": True},
                "blockers": ["request_pack_window_request_check_failed"],
                "remaining_blockers": [],
                "next_blocker": "approved_runtime_observer_log_summary_and_manifest_missing",
            }
            return subprocess.CompletedProcess(
                ["window-manifest-replay"],
                0,
                json.dumps(payload),
                "",
            )

        try:
            bundle_builder.run_window_manifest_replay_check = fake_run_window_manifest_replay_check
            state = bundle_builder.window_manifest_check_state(
                {"exists": True, "path": Path("player-principal-lifecycle-window-manifest.txt")},
                blockers,
            )
        finally:
            bundle_builder.run_window_manifest_replay_check = original

        self.assertTrue(state["checked"])
        self.assertEqual(state["exit_code"], 0)
        self.assertTrue(state["checker_ready"])
        self.assertFalse(state["ready"])
        self.assertIn("window_manifest_check_failed", [blocker["reason"] for blocker in blockers])
        self.assertEqual(state["blockers"], ["request_pack_window_request_check_failed"])

    def test_window_manifest_check_requires_post_window_replay_echo_and_verified_receipt(self) -> None:
        original = bundle_builder.run_window_manifest_replay_check
        blockers: list[dict] = []

        def fake_run_window_manifest_replay_check(_path: Path) -> subprocess.CompletedProcess[str]:
            payload = {
                "schema": "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1",
                "ready": True,
                "operational_window_manifest_ready": True,
                "post_window_replay": False,
                "operator_approval_receipt": {"verified": False},
                "blockers": [],
                "remaining_blockers": [],
                "next_blocker": "approved_runtime_observer_log_summary_and_manifest_missing",
            }
            return subprocess.CompletedProcess(
                ["window-manifest-replay"],
                0,
                json.dumps(payload),
                "",
            )

        try:
            bundle_builder.run_window_manifest_replay_check = fake_run_window_manifest_replay_check
            state = bundle_builder.window_manifest_check_state(
                {"exists": True, "path": Path("player-principal-lifecycle-window-manifest.txt")},
                blockers,
            )
        finally:
            bundle_builder.run_window_manifest_replay_check = original

        self.assertTrue(state["checked"])
        self.assertEqual(state["exit_code"], 0)
        self.assertTrue(state["checker_ready"])
        self.assertFalse(state["ready"])
        self.assertIn("window_manifest_check_failed", [blocker["reason"] for blocker in blockers])

    def test_builds_complete_consume_only_bundle(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "accepted")
            self.assertEqual(report["ready_scope"], "runtime_evidence_only")
            self.assertTrue(report["approved_runtime_evidence_present"])
            self.assertTrue(report["runtime_evidence_ready"])
            self.assertEqual(report["summary_modules"], ["player_principal_lifecycle"])
            self.assertEqual(
                report["observed_lifecycle_event_triplet_alternative"],
                "check_join_in_progress_rejected_start",
            )
            self.assertEqual(
                report["observed_lifecycle_event_triplet"][1]["target"],
                "ShooterGameMode.CheckJoinInProgress",
            )
            proof = report["lifecycle_correlation_proof"]
            self.assertTrue(proof["accepted"])
            self.assertTrue(proof["single_complete_sibling_set"])
            self.assertEqual(proof["selected_sequences"], [1, 2, 3])
            self.assertEqual(
                proof["selected_roles"],
                ["session_start", "session_start_rejected", "session_end"],
            )
            self.assertEqual(proof["selected_line_numbers"], [9, 10, 11])
            self.assertEqual(proof["session_end_correlation_status"], "matched")
            self.assertFalse(report["server_operations_authorized"])
            self.assertFalse(report["runtime_work_authorized"])
            self.assertFalse(report["promotion_ready"])
            self.assertFalse(report["public_header_allowed"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["public_abi_ready"])
            self.assertFalse(report["v1_completion_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertFalse(report["stable_claim_allowed"])
            self.assertFalse(report["route_ready"])
            self.assertEqual(report["remaining_blockers"], [])
            self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
            self.assertIsNone(report["current_route_blocker"])
            self.assertIsNone(report["next_required_artifact"])
            self.assertIsNone(report["missing_required_artifact"])
            self.assertEqual(report["required_artifact_status"], "accepted")
            self.assertFalse(report["request_pack_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["observer_env_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["operator_request_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["copied_log_metadata_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["preflight_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["window_manifest_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["completed_receipt_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["bundle_report_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["sdk_accounting_counts_as_completed_surface"])
            self.assertFalse(report["p0_accounting_counts_as_promoted_surface"])
            self.assertEqual(report["public_capability_bits_now"], [])
            self.assertEqual(report["public_callback_abi_now"], [])
            sibling_set = report["input_sibling_set"]
            self.assertTrue(sibling_set["ready"])
            self.assertFalse(sibling_set["server_operations_authorized"])
            self.assertFalse(sibling_set["runtime_work_authorized"])
            self.assertFalse(sibling_set["public_sdk_ready"])
            self.assertFalse(sibling_set["runtime_ready"])
            self.assertFalse(sibling_set["promotion_ready"])
            self.assertFalse(sibling_set["sdk_accounting_counts_as_completed_surface"])
            self.assertFalse(sibling_set["p0_accounting_counts_as_promoted_surface"])
            self.assertEqual(sibling_set["directory"], str(copied_log.parent.resolve()))
            self.assertEqual(
                set(sibling_set["artifacts"].keys()),
                {
                    "window_request_json",
                    "observer_window_env",
                    "operator_approval_request_md",
                    "operator_approval_receipt_json",
                    "preflight_pre_json",
                    "preflight_post_json",
                    "window_manifest_env",
                    "copied_obelisk_log",
                },
            )
            for artifact_name, filename in {
                "window_request_json": "window-request.json",
                "observer_window_env": "observer-window.env",
                "operator_approval_request_md": "operator-approval-request.md",
                "operator_approval_receipt_json": "operator-approval-receipt.json",
                "preflight_pre_json": "preflight-pre.json",
                "preflight_post_json": "preflight-post.json",
                "window_manifest_env": "window-manifest.env",
                "copied_obelisk_log": "Obelisk.log",
            }.items():
                artifact = sibling_set["artifacts"][artifact_name]
                artifact_path = copied_log.parent / filename
                self.assertEqual(artifact["path"], str(artifact_path.resolve()))
                self.assertEqual(artifact["sha256"], hashlib.sha256(artifact_path.read_bytes()).hexdigest())
            self.assertEqual(
                report["negative_readiness_checks"],
                {
                    "promote_ready": False,
                    "public_readiness_ready": False,
                    "runtime_readiness_ready": False,
                },
            )
            self.assertEqual(report["consume_gate_status"], "accepted")
            self.assertTrue((output_dir / "runtime-observer-summary.json").is_file())
            self.assertTrue((output_dir / "player-principal-lifecycle-window-manifest.check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.promote-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.public-readiness-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.runtime-readiness-check.json").is_file())
            self.assertTrue((output_dir / "approved-runtime-principal-lifecycle-evidence.consume-gate.json").is_file())
            self.assertTrue((output_dir / "evidence-bundle-report.json").is_file())
            for output_name, output in report["outputs"].items():
                output_path = Path(output["path"])
                self.assertTrue(output_path.is_file(), output_name)
                self.assertEqual(output["sha256"], hashlib.sha256(output_path.read_bytes()).hexdigest())
            identity = report["bundle_report_identity"]
            self.assertEqual(
                identity["artifact_kind"],
                "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
            )
            self.assertEqual(
                identity["capture_id"],
                RUN_ID,
            )
            self.assertTrue(report["operational_window"]["manifest_ready"])
            self.assertEqual(report["operational_window"]["obelisk_commit"], TEST_COMMIT)
            self.assertEqual(report["operational_window"]["log_budget"], "10")
            self.assertIn(
                "window manifest acceptance is operational posture only",
                report["operational_window"]["non_claims"],
            )

    def test_evidence_dir_build_derives_full_bundle_inputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)

            result = self.run_evidence_dir_bundle(copied_log.parent)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            output_dir = copied_log.parent / "approved-bundle"
            self.assertEqual(report["status"], "accepted")
            self.assertEqual(report["source_log"], str(copied_log.resolve()))
            self.assertEqual(
                report["approved_bundle_path"],
                str(output_dir / "approved-runtime-principal-lifecycle-evidence.json"),
            )
            self.assertEqual(report["operational_window"]["obelisk_commit"], TEST_COMMIT)
            self.assertTrue((output_dir / "runtime-observer-summary.json").is_file())
            self.assertTrue(
                (output_dir / "approved-runtime-principal-lifecycle-evidence.json").is_file()
            )
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 0, preflight.stderr)
        preflight_report = json.loads(preflight.stdout)
        self.assertTrue(preflight_report["approved_runtime_evidence_present"])
        self.assertTrue(preflight_report["approved_runtime_evidence_ready"])

    def test_preflight_rejects_stale_generated_runtime_summary_after_bundle_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)

            result = self.run_evidence_dir_bundle(copied_log.parent)
            self.assertEqual(result.returncode, 0, result.stderr)

            summary_path = copied_log.parent / "approved-bundle" / "runtime-observer-summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["evidence"]["sources"][0]["sha256"] = hashlib.sha256(
                b"stale-generated-summary"
            ).hexdigest()
            summary_path.write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")

            preflight = self.run_preflight(copied_log.parent)

        self.assertEqual(preflight.returncode, 1)
        report = json.loads(preflight.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["bundle_inputs_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertIn(
            "approved_bundle_generated_sidecar_source_log_sha256_mismatch",
            report["blockers"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_generated_bundle_routes_status_to_identity_contract_gate_only(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            bundle_report = json.loads(result.stdout)
            approved_check = json.loads(
                (output_dir / "approved-runtime-principal-lifecycle-evidence.check.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(bundle_report["status"], "accepted")
            self.assertTrue(approved_check["approved_runtime_evidence_present"])
            self.assertTrue(approved_check["runtime_evidence_ready"])
            self.assertEqual(approved_check["next_blocker"], "identity_public_contract_gate_missing")

            public_sdk_path = temp_dir / "public-sdk-after-runtime-evidence.json"
            header_gate_path = temp_dir / "player-identity-header-gate.json"
            public_sdk_path.write_text(
                json.dumps(
                    {
                        "ready": False,
                        "status": "blocked",
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "stable_claim_allowed": False,
                        "complete_sdk_progress_ratio": "0/12",
                        "p0_dependency_chain_progress_ratio": "0/4",
                        "approved_runtime_evidence": {
                            **approved_check,
                            "approved_runtime_evidence_accepted": True,
                            "evidence_bundle_accepted": True,
                            "approved_runtime_evidence_ready": approved_check["runtime_evidence_ready"],
                        },
                        "fastest_next_sdk_unblock": {
                            "current_route_blocker": None,
                            "required_artifacts": [],
                        },
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            header_gate_path.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-identity-public-header-gate.v1",
                        "ready": False,
                        "public_header_allowed": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "promotion_ready": False,
                        "current_blocker": "identity_public_contract_gate_missing",
                        "blockers": ["identity_public_contract_gate_missing"],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            status = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "report_obelisk_sdk_status.py"),
                    "--public-sdk-json",
                    str(public_sdk_path),
                    "--header-gate-json",
                    str(header_gate_path),
                    "--skip-discord-beta-bridge-config-check",
                    "--json",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(status.returncode, 0, status.stderr)
        status_report = json.loads(status.stdout)
        self.assertEqual(
            status_report["current_route_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            status_report["next_required_artifact"],
            "reviewed_player_identity_public_contract_decision",
        )
        self.assertEqual(status_report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(status_report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(status_report["public_sdk_ready"])
        self.assertFalse(status_report["runtime_ready"])
        self.assertFalse(status_report["stable_claim_allowed"])
        self.assertIn(
            "non_counting_false_progress_aliases",
            status_report["source_overclaimed_count_flags"],
        )
        self.assertEqual(
            status_report["source_overclaim_summary"]["components"]["report"][
                "categories"
            ]["counts"],
            ["non_counting_false_progress_aliases"],
        )

    def test_builds_bundle_with_check_join_in_progress_rejected_start(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text(
                "\n".join(runtime_log_lines_with_check_join_rejected_start()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "accepted")
            self.assertTrue(report["approved_runtime_evidence_present"])
            self.assertTrue(report["runtime_evidence_ready"])
            self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertFalse(report["bundle_report_counts_as_approved_runtime_evidence"])
            self.assertEqual(
                report["observed_lifecycle_event_triplet_alternative"],
                "check_join_in_progress_rejected_start",
            )
            self.assertEqual(
                report["input_sibling_set"]["artifacts"]["window_manifest_env"]["path"],
                str((copied_log.parent / "window-manifest.env").resolve()),
            )
            self.assertEqual(
                report["observed_runtime_cases"],
                ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
            )
            summary = json.loads((output_dir / "runtime-observer-summary.json").read_text(encoding="utf-8"))
            module = summary["modules"]["player_principal_lifecycle"]
            self.assertEqual(
                module["accepted_lifecycle_event_roles"],
                ["session_start", "session_start_rejected", "session_end"],
            )
            self.assertEqual(module["diagnostic_candidate_count"], 0)
            self.assertIn("ShooterGameMode.CheckJoinInProgress", module["functions"])

    def test_rejects_duplicate_start_end_context_before_approved_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text(
                "\n".join(runtime_log_lines_with_duplicate_start_end_context()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "runtime observer summary must contain exactly one approved "
                "CheckJoinInProgress rejected-start lifecycle triplet",
                result.stderr,
            )
            self.assertFalse((output_dir / "approved-runtime-principal-lifecycle-evidence.json").exists())

    def test_rejects_handle_new_player_rejected_start_before_approved_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text(
                "\n".join(runtime_log_lines_with_handle_new_player_rejected_start()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "runtime observer summary has quality blockers",
                result.stderr,
            )
            self.assertIn("malformed_observer_lines", result.stderr)
            self.assertFalse((output_dir / "approved-runtime-principal-lifecycle-evidence.json").exists())
            self.assertFalse((output_dir / "evidence-bundle-report.json").exists())

    def test_rejects_blocked_ragnarok_ready_log_copy_report_before_bundle_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text(
                "\n".join(runtime_log_lines_with_ragnarok_duplicate_start_diagnostic_missing_check_join()) + "\n",
                encoding="utf-8",
            )
            write_ready_log_copy_report(copied_log, blocked_ragnarok_ready_log_copy_payload(copied_log))

            result = self.run_bundle(copied_log, output_dir)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checked sibling set failed", result.stderr)
        self.assertIn("ready_log_copy_not_ready_to_copy", result.stderr)
        self.assertFalse((output_dir / "runtime-observer-summary.json").exists())
        self.assertFalse((output_dir / "approved-runtime-principal-lifecycle-evidence.json").exists())
        self.assertFalse((output_dir / "evidence-bundle-report.json").exists())

    def test_rejects_stale_ready_log_copy_fresh_window_before_bundle_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            self.write_window_manifest(temp_dir, copied_log)
            write_ready_log_copy_report(copied_log, stale_fresh_window_ready_log_copy_payload(copied_log))

            result = self.run_bundle(copied_log, output_dir)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checked sibling set failed", result.stderr)
        self.assertIn("ready_log_copy_copied_log_lifecycle_event_outside_fresh_window", result.stderr)
        self.assertFalse((output_dir / "runtime-observer-summary.json").exists())
        self.assertFalse((output_dir / "approved-runtime-principal-lifecycle-evidence.json").exists())
        self.assertFalse((output_dir / "evidence-bundle-report.json").exists())

    def test_builds_bundle_with_ready_log_copy_report_context(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            write_ready_log_copy_report(copied_log)

            result = self.run_bundle(copied_log, output_dir)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["runtime_evidence_ready"])
        self.assertFalse(report["copy_report_counts_as_approved_runtime_evidence"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["copy_readiness_context"]["report_accepted"])
        self.assertTrue(report["copy_readiness_context"]["ready_to_copy"])
        self.assertEqual(report["copy_readiness_context"]["copy_readiness"], "ready_complete_role_triplet")
        self.assertEqual(report["copy_readiness_context"]["missing_roles"], [])
        self.assertFalse(
            report["copy_readiness_context"]["copy_report_counts_as_approved_runtime_evidence"]
        )

    def test_rejects_placeholder_cli_obelisk_commit(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            result = self.run_bundle(copied_log, output_dir)
            outcomes = []
            for invalid_commit in ("test-commit", "a" * 40):
                command = list(result.args)
                command[command.index("--obelisk-commit") + 1] = invalid_commit
                outcomes.append(
                    subprocess.run(
                        command,
                        check=False,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env={
                            **os.environ,
                            "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1",
                            "OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE": str(SAFE_OFFLINE_WORKSPACE),
                        },
                    )
                )

        for outcome in outcomes:
            with self.subTest(args=outcome.args):
                self.assertNotEqual(outcome.returncode, 0)
                self.assertIn("--obelisk-commit must be a reviewed 40-character lowercase Git SHA", outcome.stderr)

    def test_rejects_stale_reviewed_commit_that_is_not_current_head(self) -> None:
        old_commit = globals()["TEST_COMMIT"]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            try:
                globals()["TEST_COMMIT"] = STALE_TEST_COMMIT
                window_manifest = self.write_window_manifest(temp_dir, copied_log)
                result = self.run_bundle(
                    copied_log,
                    output_dir,
                    window_manifest=window_manifest,
                    obelisk_commit=STALE_TEST_COMMIT,
                )
            finally:
                globals()["TEST_COMMIT"] = old_commit

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checked sibling set failed", result.stderr)
        self.assertIn("window_manifest_obelisk_commit_not_current_head", result.stderr)
        self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_builds_bundle_with_relative_window_manifest_log_path(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_relative_window_manifest(temp_dir, copied_log)

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertEqual(result.returncode, 0, result.stderr)
            window_check = json.loads(
                (output_dir / "player-principal-lifecycle-window-manifest.check.json").read_text(encoding="utf-8")
            )
            self.assertEqual(window_check["copied_log"]["path"], str(copied_log.resolve()))

    def test_generated_bundle_manifest_clears_first_evidence_runtime_blocker_only(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)
            self.assertEqual(result.returncode, 0, result.stderr)

            old_env = os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES")
            old_root = os.environ.get("OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE")
            os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
            os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
            try:
                with mock.patch.object(
                    first_evidence_checker.approved_runtime_principal_lifecycle_evidence,
                    "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                    (SAFE_OFFLINE_WORKSPACE,),
                ), mock.patch.object(
                    first_evidence_checker.approved_runtime_principal_lifecycle_evidence.window_manifest_checker,
                    "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                    (SAFE_OFFLINE_WORKSPACE,),
                ):
                    diagnosis = first_evidence_checker.approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
                        output_dir / "approved-runtime-principal-lifecycle-evidence.json"
                    )
            finally:
                if old_env is None:
                    os.environ.pop("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES", None)
                else:
                    os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = old_env
                if old_root is None:
                    os.environ.pop("OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE", None)
                else:
                    os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = old_root
            if not (
                first_evidence_checker.APPROVED_CANDIDATE_ROOT_FALLBACK.is_dir()
                and first_evidence_checker.APPROVED_LIFECYCLE_ANCHOR_CANDIDATES_FALLBACK.is_file()
                and first_evidence_checker.APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK.is_file()
            ):
                self.skipTest("approved workspace first-evidence fallbacks are not available")
            preflight = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "check_player_identity_first_evidence_readiness.py"),
                    "--json",
                    "--approved-runtime-principal-lifecycle-evidence-manifest",
                    str(output_dir / "approved-runtime-principal-lifecycle-evidence.json"),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={
                    **os.environ,
                    "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1",
                    "OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE": str(SAFE_OFFLINE_WORKSPACE),
                },
            )

        self.assertTrue(diagnosis["ready"])
        self.assertTrue(diagnosis["approved_runtime_evidence_present"])
        self.assertTrue(diagnosis["runtime_evidence_ready"])
        self.assertFalse(diagnosis["promotion_ready"])
        self.assertFalse(diagnosis["public_sdk_ready"])
        self.assertFalse(diagnosis["runtime_ready"])
        self.assertEqual(diagnosis["remaining_blockers"], [])
        self.assertEqual(
            diagnosis["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        self.assertEqual(
            diagnosis["consumer_cases"],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )
        report = json.loads(preflight.stdout)
        approved = report["first_evidence"]["approved_runtime_principal_lifecycle_evidence_manifest"]
        self.assertTrue(approved["ready"])
        self.assertTrue(approved["approved_runtime_evidence_present"])
        self.assertTrue(approved["runtime_evidence_ready"])
        self.assertEqual(approved["remaining_blockers"], [])
        self.assertNotIn("approved_runtime_evidence_missing", report["blockers"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_fails_closed_for_live_server_log_path(self) -> None:
        with self.temp_offline_workspace() as temp:
            result = self.run_bundle(
                Path("/servidor/ark/obelisk/logs/arkserver2/Obelisk.log"),
                Path(temp) / "bundle",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--copied-log must be an offline copy, not a live server path", result.stderr)

    def test_rejects_live_copied_log_before_analysis_even_with_offline_manifest(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            output_dir = temp_dir / "bundle"

            result = self.run_bundle(
                Path("/servidor/ark/obelisk/logs/arkserver2/Obelisk.log"),
                output_dir,
                window_manifest=window_manifest,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--copied-log must be an offline copy, not a live server path", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_non_sibling_window_manifest_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            original_manifest = self.write_window_manifest(temp_dir, copied_log)
            alternate_manifest = temp_dir / "alternate-window" / "window-manifest.env"
            alternate_manifest.parent.mkdir(parents=True)
            alternate_manifest.write_bytes(original_manifest.read_bytes())
            output_dir = temp_dir / "bundle"

            result = self.run_bundle(copied_log, output_dir, window_manifest=alternate_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "--window-manifest must be the exact sibling window-manifest.env beside --copied-log",
                result.stderr,
            )
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_missing_sibling_window_manifest_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            window_manifest.unlink()
            output_dir = temp_dir / "bundle"

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--window-manifest does not exist", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_missing_copied_log_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            copied_log.unlink()
            output_dir = temp_dir / "bundle"

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--copied-log does not exist", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_missing_checked_sibling_sidecar_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "observer-window.env").unlink()

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("observer_window_env_missing", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_preflight_post_alias_when_canonical_sibling_is_missing_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            original = Path(fields["preflight_post_path"])
            alternate = copied_log.parent.parent / "alternate-sidecars" / RUN_ID / "preflight-post.json"
            alternate.parent.mkdir(parents=True)
            alternate.write_bytes(original.read_bytes())
            original.unlink()
            fields["preflight_post_path"] = str(alternate)
            fields["preflight_post_sha256"] = hashlib.sha256(alternate.read_bytes()).hexdigest()
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("preflight_post_json_missing", result.stderr)
            self.assertIn("preflight_post_path_not_exact_sibling_path", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_missing_post_restart_preflight_sidecar_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            (copied_log.parent / "post-restart-preflight.env").unlink()

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("operational_window_post_restart_preflight_sidecar_missing", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_manifest_sidecar_path_drift_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            original = Path(fields["request_pack_path"])
            alternate = copied_log.parent.parent / "alternate-sidecars" / RUN_ID / "window-request.json"
            alternate.parent.mkdir(parents=True)
            alternate.write_bytes(original.read_bytes())
            fields["request_pack_path"] = str(alternate)
            fields["request_pack_sha256"] = hashlib.sha256(alternate.read_bytes()).hexdigest()
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("request_pack_path_not_exact_sibling_path", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_generated_operator_receipt_template_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            receipt = Path(fields["operator_approval_receipt_path"])
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            payload["status"] = "generated_template"
            payload["receipt_completed"] = False
            payload["operator_current_turn_approval_recorded"] = False
            payload["operator_completion"] = {
                "approval_recorded_at_utc": None,
                "approved_by_role": None,
                "approval_source": None,
                "attestation": None,
            }
            receipt.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["operator_approval_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("operator_approval_receipt_generated_template_not_completed_receipt", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_notice_prep_json_copied_as_operator_receipt_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            receipt = Path(fields["operator_approval_receipt_path"])
            payload = {
                "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
                "ready": True,
                "mode": "confirmed_send",
                "discord_sent": True,
                "counts_as_approved_runtime_evidence": False,
                "approved_runtime_evidence_ready": False,
                "non_authorization": "notice preparation only",
            }
            receipt.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["operator_approval_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn(
                "operator_approval_receipt_json_notice_prep_sidecar_not_approved_runtime_evidence",
                result.stderr,
            )
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_public_reachability_json_copied_as_operator_receipt_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            receipt = Path(fields["operator_approval_receipt_path"])
            payload = {
                "schema": "obelisk.player-principal-public-reachability-check.v1",
                "ready": True,
                "public_reachability_ready": True,
                "public_reachability_counts_as_approved_runtime_evidence": True,
            }
            receipt.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["operator_approval_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn(
                "operator_approval_receipt_json_public_reachability_sidecar_not_approved_runtime_evidence",
                result.stderr,
            )
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_completed_operator_receipt_with_extra_public_readiness_claim_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            receipt = Path(fields["operator_approval_receipt_path"])
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            payload["public_sdk_ready"] = True
            receipt.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            fields["operator_approval_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("json_sidecar_authorization_or_readiness_key_overclaim", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_active_or_passive_summary_json_copied_as_operator_receipt_before_outputs(self) -> None:
        cases = (
            (
                "passive_activity_triage",
                {
                    "schema": "obelisk.player-principal-passive-activity-triage.v1",
                    "classification": "passive_activity_triage_non_evidence",
                    "active_targets": ["arkserver:Ragnarok:27015"],
                    "candidate_targets_with_complete_observer_event_triplet_candidate": [
                        "arkserver:Ragnarok:27015"
                    ],
                    "approved_runtime_evidence": True,
                    "ready": True,
                },
                "operator_approval_receipt_json_passive_activity_triage_sidecar_not_approved_runtime_evidence",
            ),
            (
                "sdk_status_report",
                {
                    "schema": "obelisk.sdk-status-report.v1",
                    "status_report_only": True,
                    "active_player_principal_paths": {
                        "ragnarok": {
                            "path_status": "active_ragnarok_complete_passive_triplet_needs_approved_bundle"
                        }
                    },
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "operator_approval_receipt_json_sdk_status_report_sidecar_not_approved_runtime_evidence",
            ),
            (
                "sdk_status_report_blocked_zero_overclaim",
                {
                    "schema": "obelisk.sdk-status-report.v1",
                    "status_report_only": True,
                    "status": "blocked",
                    "ready": False,
                    "current_route_blocker": "approved_runtime_evidence_missing",
                    "source_overclaim_total_flag_count": 0,
                    "source_overclaim_summary": {"total": 0},
                    "complete_sdk_progress_ratio": "0/12",
                    "p0_dependency_chain_progress_ratio": "0/4",
                },
                "operator_approval_receipt_json_sdk_status_report_sidecar_not_approved_runtime_evidence",
            ),
            (
                "source_bound_fname_drift_manifest",
                {
                    "schema": "obelisk.player-principal-source-bound-fname-drift-manifest.v1",
                    "planning_only": True,
                    "source_bound_to_repo_artifact": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "operator_approval_receipt_json_source_bound_drift_manifest_is_not_approved_runtime_evidence",
            ),
        )
        for name, payload, expected_blocker in cases:
            with self.subTest(name=name):
                with self.temp_offline_workspace() as temp:
                    temp_dir = Path(temp)
                    copied_log = copied_log_path(temp_dir)
                    output_dir = temp_dir / "bundle"
                    copied_log.parent.mkdir(parents=True, exist_ok=True)
                    copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
                    window_manifest = self.write_window_manifest(temp_dir, copied_log)
                    fields = dict(
                        line.split("=", 1)
                        for line in window_manifest.read_text(encoding="utf-8").splitlines()
                        if line and not line.startswith("#")
                    )
                    receipt = Path(fields["operator_approval_receipt_path"])
                    receipt.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                    fields["operator_approval_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
                    window_manifest.write_text(
                        "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                        encoding="utf-8",
                    )

                    result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("checked sibling set failed", result.stderr)
                self.assertIn(expected_blocker, result.stderr)
                self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_notice_action_or_status_report_json_copied_as_required_json_sidecar_before_outputs(self) -> None:
        cases = (
            (
                "preflight_preactivation_executor_artifact",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.player-principal-lifecycle-preactivation-executor-output.v1",
                    "ready": True,
                    "executor_artifact_counts_as_approved_runtime_evidence": False,
                },
                (
                    "preflight_pre_json_"
                    "preactivation_or_executor_artifact_is_not_approved_runtime_evidence"
                ),
            ),
            (
                "request_pack_window_request_check",
                "request_pack_path",
                "request_pack_sha256",
                {
                    "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
                    "ready": True,
                    "request_pack_ready": True,
                    "approved_runtime_evidence_ready": False,
                },
                "window_request_json_window_request_check_sidecar_not_approved_runtime_evidence",
            ),
            (
                "request_pack_runtime_window_plan",
                "request_pack_path",
                "request_pack_sha256",
                {
                    "schema": "obelisk.player-principal-lifecycle-runtime-window-plan.v1",
                    "ready": True,
                    "next_actions": [{"id": "run_bundle_builder"}],
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "window_request_json_next_action_plan_sidecar_not_approved_runtime_evidence",
            ),
            (
                "request_pack_closure_request",
                "request_pack_path",
                "request_pack_sha256",
                {
                    "schema": "obelisk.player-principal-lifecycle-evidence-closure-request.v1",
                    "status": "accepted",
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "window_request_json_closure_request_sidecar_not_approved_runtime_evidence",
            ),
            (
                "request_pack_standing_launch_authority_artifact",
                "request_pack_path",
                "request_pack_sha256",
                {
                    "schema": "obelisk.player-principal-lifecycle-standing-launch-authority-artifact.v1",
                    "status": "accepted",
                    "standing_launch_authority_satisfies_operator_approval": True,
                    "counts_as_approved_runtime_evidence": False,
                },
                "window_request_json_approval_or_standing_authority_schema_is_not_approved_runtime_evidence",
            ),
            (
                "preflight_copied_log_status_report",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.player-principal-lifecycle-copied-log-status.v1",
                    "status": "copied",
                    "ready": True,
                    "approved_runtime_evidence_ready": False,
                },
                "preflight_pre_json_copied_status_or_report_schema_is_not_approved_runtime_evidence",
            ),
            (
                "preflight_runtime_evidence_status_report",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.player-principal-lifecycle-runtime-evidence-status.v1",
                    "status": "closure_inputs_complete_bundle_checker_required",
                    "next_actions": [{"id": "run_bundle_builder"}],
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "preflight_pre_json_runtime_evidence_status_report_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_passive_monitor_only_summary",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.player-principal-passive-monitor-only-summary.v1",
                    "classification": "monitor_only_non_evidence",
                    "passive_monitor_activity_summary": {},
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "preflight_pre_json_passive_monitor_only_summary_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_player_notice_action",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.player-principal-lifecycle-player-notice-action.v1",
                    "required": True,
                    "notice_path": "discord-beta-testers",
                    "counts_as_approved_runtime_evidence": False,
                },
                "preflight_pre_json_player_notice_action_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_discord_active_notice_state",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.discord-beta-bridge-active-notice.v1",
                    "status": "active",
                    "discord_sent": True,
                    "counts_as_approved_runtime_evidence": False,
                },
                "preflight_pre_json_discord_bridge_state_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_generic_player_notice_action",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.player-notice-action.v1",
                    "mode": "dry_run",
                    "status": "blocked",
                    "discord_sent": False,
                },
                "preflight_pre_json_player_notice_action_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_approved_evidence_check_report",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "ready": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "preflight_pre_json_approved_evidence_check_report_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_window_manifest_check_report",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1",
                    "ready": True,
                    "operational_window_manifest_ready": True,
                    "approved_runtime_evidence_ready": False,
                },
                "preflight_pre_json_window_manifest_check_report_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_bundle_report",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
                    "status": "accepted",
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "preflight_pre_json_bundle_report_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_public_sdk_completion_check",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.public-sdk-v1-completion-check.v1",
                    "status": "blocked",
                    "ready": False,
                    "approved_in_game_evidence_ready": False,
                    "sdk_completion": {"progress_ratio": "0/12"},
                },
                "preflight_pre_json_public_sdk_completion_check_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_public_sdk_completion_summary",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.public-sdk-v1-completion-summary.v1",
                    "status": "blocked",
                    "ready": False,
                    "sdk_completion": {"status": "blocked", "progress_ratio": "0/12"},
                },
                "preflight_pre_json_public_sdk_completion_summary_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_public_sdk_approved_in_game_status",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.public-sdk-v1-approved-in-game-evidence-status.v1",
                    "approved_runtime_evidence_ready": False,
                    "next_required_artifact": "approved_runtime_principal_lifecycle_evidence_bundle",
                },
                "preflight_pre_json_public_sdk_approved_in_game_evidence_status_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_public_sdk_progress_normalization_trace",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.public-sdk-v1-progress-normalization-trace.v1",
                    "status_report_only": True,
                    "status": "blocked",
                    "ready": False,
                    "complete_sdk_progress_ratio": "0/12",
                    "p0_chain_progress_ratio": "0/4",
                    "source_overclaim_total_flag_count": 0,
                },
                "preflight_pre_json_public_sdk_progress_normalization_trace_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_scoped_release_statement",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.scoped-release-statement-outcomes.v1",
                    "status": "blocked",
                    "ready": False,
                    "release_ready": False,
                },
                "preflight_pre_json_scoped_release_statement_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_installed_sdk_package_shape",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.installed-sdk-package-shape.v1",
                    "status": "package-shape-evidence-only",
                    "cmakePackagePassed": True,
                    "packageShapeCountsTowardCompletion": False,
                },
                "preflight_pre_json_installed_sdk_package_shape_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_public_contract_decision_record",
                "preflight_pre_path",
                "preflight_pre_sha256",
                {
                    "schema": "obelisk.player-identity-public-contract-decision-record.v1",
                    "accepted_for_contract_review": True,
                    "contract_review_only": True,
                    "public_sdk_ready": False,
                },
                "preflight_pre_json_contract_review_artifact_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_runtime_observer_summary",
                "preflight_pre_path",
                "preflight_pre_sha256",
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
                "preflight_pre_json_runtime_observer_summary_sidecar_not_approved_runtime_evidence",
            ),
        )
        for name, path_key, sha_key, payload, expected_blocker in cases:
            with self.subTest(name=name):
                with self.temp_offline_workspace() as temp:
                    temp_dir = Path(temp)
                    copied_log = copied_log_path(temp_dir)
                    output_dir = temp_dir / "bundle"
                    copied_log.parent.mkdir(parents=True, exist_ok=True)
                    copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
                    window_manifest = self.write_window_manifest(temp_dir, copied_log)
                    fields = dict(
                        line.split("=", 1)
                        for line in window_manifest.read_text(encoding="utf-8").splitlines()
                        if line and not line.startswith("#")
                    )
                    sidecar = Path(fields[path_key])
                    sidecar.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                    fields[sha_key] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
                    window_manifest.write_text(
                        "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                        encoding="utf-8",
                    )

                    result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("checked sibling set failed", result.stderr)
                self.assertIn(expected_blocker, result.stderr)
                self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_symlinked_checked_sibling_sidecar_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            observer_env = copied_log.parent / "observer-window.env"
            real_observer_env = copied_log.parent / "observer-window.real.env"
            real_observer_env.write_bytes(observer_env.read_bytes())
            observer_env.unlink()
            observer_env.symlink_to(real_observer_env)

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("observer_window_env_symlink_component", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_protected_manifest_sidecar_path_before_outputs(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            fields = dict(
                line.split("=", 1)
                for line in window_manifest.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            fields["preflight_pre_path"] = "/servidor/ark/obelisk/protected-preflight-pre.json"
            window_manifest.write_text(
                "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("preflight_pre_path_under_protected_server_root", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_rejects_protected_output_dir_before_writing(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)

            result = self.run_bundle(
                copied_log,
                Path("/servidor/ark/obelisk/player-principal-bundle"),
                window_manifest=window_manifest,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("OBELISK_ALLOW_SERVER_ROOT_WRITES=1", result.stderr)
            self.assertFalse((temp_dir / "runtime-observer-summary.json").exists())

    def test_rejects_symlinked_output_dir_before_writing(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            target = temp_dir / "real-output-root"
            target.mkdir()
            link = temp_dir / "linked-output-root"
            link.symlink_to(target, target_is_directory=True)

            result = self.run_bundle(copied_log, link / "bundle", window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output-dir must not be a symlink", result.stderr)
            self.assertFalse((target / "bundle" / "runtime-observer-summary.json").exists())

    def test_file_state_does_not_hash_protected_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected_root = root / "server"
            offline_root = root / "workspace-offline"
            protected_root.mkdir()
            offline_root.mkdir()
            path = protected_root / "request-pack.json"
            path.write_text("{}", encoding="utf-8")
            blockers: list[dict] = []

            with mock.patch.object(bundle_builder, "SERVER_ROOT", protected_root), mock.patch.object(
                bundle_builder,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (offline_root,),
            ), mock.patch.object(bundle_builder, "sha256_file", side_effect=AssertionError("sha256_file should not run")):
                state = bundle_builder.file_state(path, "request_pack", blockers)

        self.assertTrue(state["exists"])
        self.assertTrue(state["protected"])
        self.assertFalse(state["approved_offline_workspace"])
        self.assertIsNone(state["sha256"])
        self.assertIn("request_pack_under_protected_server_root", [blocker["reason"] for blocker in blockers])
        self.assertIn("request_pack_not_approved_offline_workspace", [blocker["reason"] for blocker in blockers])

    def test_file_state_does_not_hash_unapproved_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected_root = root / "server"
            offline_root = root / "workspace-offline"
            unapproved_root = root / "other-offline"
            protected_root.mkdir()
            offline_root.mkdir()
            unapproved_root.mkdir()
            path = unapproved_root / "request-pack.json"
            path.write_text("{}", encoding="utf-8")
            blockers: list[dict] = []

            with mock.patch.object(bundle_builder, "SERVER_ROOT", protected_root), mock.patch.object(
                bundle_builder,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (offline_root,),
            ), mock.patch.object(bundle_builder, "sha256_file", side_effect=AssertionError("sha256_file should not run")):
                state = bundle_builder.file_state(path, "request_pack", blockers)

        self.assertTrue(state["exists"])
        self.assertFalse(state["protected"])
        self.assertFalse(state["approved_offline_workspace"])
        self.assertIsNone(state["sha256"])
        self.assertEqual(["request_pack_not_approved_offline_workspace"], [blocker["reason"] for blocker in blockers])

    def test_request_pack_check_does_not_read_protected_sidecars(self) -> None:
        blockers: list[dict] = []

        with mock.patch.object(
            bundle_builder,
            "run_json_check",
            side_effect=AssertionError("protected request-pack sidecars must not be checked"),
        ):
            state = bundle_builder.request_pack_check_state(
                {
                    "exists": True,
                    "path": Path("/servidor/ark/obelisk/protected-window-request.json"),
                    "approved_offline_workspace": False,
                    "protected": True,
                },
                {
                    "exists": True,
                    "path": Path("/servidor/ark/obelisk/protected-observer-window.env"),
                    "approved_offline_workspace": False,
                    "protected": True,
                },
                {
                    "exists": True,
                    "path": Path("/servidor/ark/obelisk/protected-operator-approval-receipt.json"),
                    "approved_offline_workspace": False,
                    "protected": True,
                },
                blockers,
            )

        self.assertFalse(state["checked"])
        self.assertFalse(state["ready"])
        self.assertEqual([], blockers)

    def test_request_pack_check_does_not_read_unapproved_sidecars(self) -> None:
        blockers: list[dict] = []

        with mock.patch.object(
            bundle_builder,
            "run_json_check",
            side_effect=AssertionError("unapproved request-pack sidecars must not be checked"),
        ):
            state = bundle_builder.request_pack_check_state(
                {
                    "exists": True,
                    "path": Path("/tmp/unapproved-window-request.json"),
                    "approved_offline_workspace": False,
                    "protected": False,
                },
                {
                    "exists": True,
                    "path": Path("/tmp/unapproved-observer-window.env"),
                    "approved_offline_workspace": False,
                    "protected": False,
                },
                {
                    "exists": True,
                    "path": Path("/tmp/unapproved-operator-approval-receipt.json"),
                    "approved_offline_workspace": False,
                    "protected": False,
                },
                blockers,
            )

        self.assertFalse(state["checked"])
        self.assertFalse(state["ready"])
        self.assertEqual([], blockers)

    def test_approved_manifest_check_does_not_read_protected_manifest(self) -> None:
        blockers: list[dict] = []
        with mock.patch.object(
            bundle_builder,
            "run_json_check",
            side_effect=AssertionError("protected approved-runtime manifest must not be checked"),
        ):
            state = bundle_builder.approved_runtime_manifest_check_state(
                {
                    "exists": True,
                    "path": Path("/servidor/ark/obelisk/approved-runtime-principal-lifecycle-evidence.json"),
                    "approved_offline_workspace": False,
                    "protected": True,
                },
                blockers,
            )

        self.assertFalse(state["checked"])
        self.assertFalse(state["ready"])
        self.assertEqual([], blockers)

    def test_approved_manifest_check_does_not_read_unapproved_manifest(self) -> None:
        blockers: list[dict] = []
        with mock.patch.object(
            bundle_builder,
            "run_json_check",
            side_effect=AssertionError("unapproved approved-runtime manifest must not be checked"),
        ):
            state = bundle_builder.approved_runtime_manifest_check_state(
                {
                    "exists": True,
                    "path": Path("/tmp/approved-runtime-principal-lifecycle-evidence.json"),
                    "approved_offline_workspace": False,
                    "protected": False,
                },
                blockers,
            )

        self.assertFalse(state["checked"])
        self.assertFalse(state["ready"])
        self.assertEqual([], blockers)

    def test_preflight_manifest_parser_rejects_duplicate_and_unsafe_keys_before_using_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "window-manifest.env"
            manifest.write_text(
                "\n".join(
                    [
                        "request_pack_path=window-request.json",
                        "request_pack_path=/servidor/ark/obelisk/protected-window-request.json",
                        "observer/env/path=observer-window.env",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            blockers: list[dict] = []

            fields = bundle_builder.read_manifest_fields(manifest, blockers)

        self.assertEqual({"request_pack_path": "window-request.json"}, fields)
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("window_manifest_duplicate_key", reasons)
        self.assertIn("window_manifest_key_unsafe", reasons)

    def test_fails_closed_for_events_before_safe_gate(self) -> None:
        lines = runtime_log_lines()
        lines.insert(
            7,
            "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
            "target=ShooterGameMode.HandleNewPlayer post_original=true "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
            "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
            "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none.",
        )
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analyze_runtime_observer_log failed", result.stderr)
            self.assertIn("player_principal_event_before_safe_gate", result.stderr)

    def test_rejects_passive_monitor_metadata_even_with_complete_lifecycle_events(self) -> None:
        lines = [
            "tick utc=2026-06-04T05:00:00Z",
            "query instance=arkserver map=Ragnarok query_port=27015 status=ok players=1/70",
            "player_presence_detected instance=arkserver map=Ragnarok",
            "observer_tail instance=arkserver status=matched lines=3 scan_lines=200 limit=10",
            *runtime_log_lines(),
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analyze_runtime_observer_log failed", result.stderr)
            self.assertIn("passive_monitor_metadata_lines", result.stderr)

    def test_rejects_timestamp_prefixed_passive_monitor_metadata_even_with_complete_lifecycle_events(self) -> None:
        lines = [
            "[2026-06-04T05:00:00Z] tick utc=2026-06-04T05:00:00Z",
            "[2026-06-04T05:00:01Z] query instance=arkserver map=Ragnarok "
            "query_port=27015 status=ok players=1/70",
            "[2026-06-04T05:00:02Z] player_presence_detected instance=arkserver map=Ragnarok",
            "[2026-06-04T05:00:03Z] observer_tail instance=arkserver "
            "status=matched lines=3 scan_lines=200 limit=10",
            *runtime_log_lines(),
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source_summary_copied_log_contains_passive_monitor_metadata", result.stderr)

    def test_rejects_old_format_lifecycle_lines_without_status_proof_fields(self) -> None:
        lines = [without_lifecycle_status_proof_fields(line) for line in runtime_log_lines()]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analyze_runtime_observer_log failed", result.stderr)
            self.assertIn("malformed_observer_lines", result.stderr)

    def test_rejects_status_proof_mutated_copied_log_lifecycle_event(self) -> None:
        lines = [
            line.replace(
                "apply_status=session_end_invalidated correlation_status=matched",
                "apply_status=session_end_unresolved_noop correlation_status=missing",
            )
            for line in runtime_log_lines()
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analyze_runtime_observer_log failed", result.stderr)
            self.assertIn("malformed_observer_lines", result.stderr)

    def test_fails_closed_when_window_manifest_sha_does_not_match_log(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            text = window_manifest.read_text(encoding="utf-8")
            window_manifest.write_text(
                text.replace(
                    f"copied_log_sha256={hashlib.sha256(copied_log.read_bytes()).hexdigest()}",
                    "copied_log_sha256=0000000000000000000000000000000000000000000000000000000000000000",
                ),
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("copied_log_sha256_placeholder", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_fails_closed_when_window_manifest_commit_does_not_match_summary(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)
            text = window_manifest.read_text(encoding="utf-8")
            window_manifest.write_text(
                text.replace(f"obelisk_commit={TEST_COMMIT}", f"obelisk_commit={STALE_TEST_COMMIT}"),
                encoding="utf-8",
            )

            result = self.run_bundle(copied_log, output_dir, window_manifest=window_manifest)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checked sibling set failed", result.stderr)
            self.assertIn("window_manifest_obelisk_commit_not_current_head", result.stderr)
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_fails_closed_before_outputs_when_cli_commit_does_not_match_manifest_head(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = self.write_window_manifest(temp_dir, copied_log)

            result = self.run_bundle(
                copied_log,
                output_dir,
                window_manifest=window_manifest,
                obelisk_commit=STALE_TEST_COMMIT,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "--obelisk-commit must match window-manifest.env obelisk_commit and current repo HEAD",
                result.stderr,
            )
            self.assertFalse((output_dir / "runtime-observer-summary.json").exists())

    def test_fails_closed_when_runtime_gate_limit_does_not_match_first_window_budget(self) -> None:
        lines = [
            line.replace("limit=10 dispatch_limit=0", "limit=9 dispatch_limit=0")
            for line in runtime_log_lines()
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "runtime observer summary gate limit does not match exact first-window log budget",
                result.stderr,
            )

    def test_fails_closed_when_copied_log_does_not_confirm_plugins_disabled(self) -> None:
        lines = [
            line for line in runtime_log_lines()
            if "Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1" not in line
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "runtime observer summary plugins_disabled does not match approved copied-log posture",
                result.stderr,
            )
            self.assertFalse((output_dir / "approved-runtime-principal-lifecycle-evidence.json").exists())

    def test_fails_closed_when_copied_log_does_not_confirm_scanner_disabled(self) -> None:
        lines = [
            line for line in runtime_log_lines()
            if "ReflectionScanner disabled" not in line
        ]
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = copied_log_path(temp_dir)
            output_dir = temp_dir / "bundle"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_bundle(copied_log, output_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "runtime observer summary reflection_scanner_disabled does not match approved copied-log posture",
                result.stderr,
            )
            self.assertFalse((output_dir / "approved-runtime-principal-lifecycle-evidence.json").exists())

    def test_rejects_negative_readiness_report_that_overclaims_public_sdk(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_negative_readiness_report(
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "public_readiness",
                    "ready_scope": "runtime_evidence_only",
                    "ready": False,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_sdk_ready": True,
                    "runtime_ready": False,
                    "blockers": ["public_readiness_blocked_until_identity_public_contract_gate"],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "public-readiness approved runtime principal lifecycle evidence check",
                "public_readiness_blocked_until_identity_public_contract_gate",
            )

        self.assertIn("overclaims public_sdk_ready", str(raised.exception))

    def test_rejects_consume_report_that_overclaims_p0_accounting(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_consume_only_check_report(
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "consume",
                    "ready_scope": "runtime_evidence_only",
                    "ready": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "v1_completion_ready": False,
                    "runtime_ready": False,
                    "sdk_accounting_counts_as_completed_surface": False,
                    "p0_accounting_counts_as_promoted_surface": True,
                    "public_capability_bits_now": [],
                    "public_callback_abi_now": [],
                    "blockers": [],
                    "remaining_blockers": [],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "consume approved runtime principal lifecycle evidence check",
            )

        self.assertIn("overclaims p0_accounting_counts_as_promoted_surface", str(raised.exception))

    def test_rejects_bundle_report_with_stale_route_blocker_contract(self) -> None:
        base_report = {
            "server_operations_authorized": False,
            "runtime_work_authorized": False,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "v1_completion_ready": False,
            "runtime_ready": False,
            "stable_claim_allowed": False,
            "route_ready": False,
            "request_pack_counts_as_approved_runtime_evidence": False,
            "observer_env_counts_as_approved_runtime_evidence": False,
            "operator_request_counts_as_approved_runtime_evidence": False,
            "copied_log_metadata_counts_as_approved_runtime_evidence": False,
            "preflight_counts_as_approved_runtime_evidence": False,
            "window_manifest_counts_as_approved_runtime_evidence": False,
            "completed_receipt_counts_as_approved_runtime_evidence": False,
            "bundle_report_counts_as_approved_runtime_evidence": False,
            "sdk_accounting_counts_as_completed_surface": False,
            "p0_accounting_counts_as_promoted_surface": False,
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "negative_readiness_checks": {
                "promote_ready": False,
                "public_readiness_ready": False,
                "runtime_readiness_ready": False,
            },
            "remaining_blockers": [],
            "next_blocker": "identity_public_contract_gate_missing",
            "current_route_blocker": None,
            "next_required_artifact": None,
            "missing_required_artifact": None,
            "required_artifact_status": "accepted",
        }
        for name, overrides, expected in (
            (
                "wrong_next_blocker",
                {"next_blocker": "approved_runtime_evidence_not_accepted"},
                "did not route to the identity public contract gate",
            ),
            (
                "remaining_blockers",
                {"remaining_blockers": ["approved_runtime_evidence_not_accepted"]},
                "carried runtime evidence blockers",
            ),
            (
                "missing_artifact",
                {"missing_required_artifact": "approved_runtime_principal_lifecycle_evidence_bundle"},
                "overclaims a missing artifact",
            ),
            (
                "artifact_status",
                {"required_artifact_status": "missing_or_not_accepted"},
                "did not mark the required artifact accepted",
            ),
        ):
            with self.subTest(name=name):
                report = dict(base_report)
                report.update(overrides)
                with self.assertRaises(SystemExit) as raised:
                    bundle_builder.require_bundle_report_non_authorizing(report)
                self.assertIn(expected, str(raised.exception))

    def test_rejects_negative_readiness_report_that_overclaims_alias_key(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_negative_readiness_report(
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "public_readiness",
                    "ready_scope": "runtime_evidence_only",
                    "ready": False,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "diagnostics": {"countsTowardSdk": True},
                    "blockers": ["public_readiness_blocked_until_identity_public_contract_gate"],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "public-readiness approved runtime principal lifecycle evidence check",
                "public_readiness_blocked_until_identity_public_contract_gate",
            )

        self.assertIn("overclaims readiness alias $.diagnostics.countsTowardSdk", str(raised.exception))

    def test_rejects_readiness_reports_that_overclaim_public_abi_lists(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_consume_only_check_report(
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "consume",
                    "ready_scope": "runtime_evidence_only",
                    "ready": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "v1_completion_ready": False,
                    "runtime_ready": False,
                    "public_capability_bits_now": [],
                    "public_callback_abi_now": ["ObeliskRegisterPlayerIdentityCallback"],
                    "blockers": [],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "consume approved runtime principal lifecycle evidence check",
            )

        self.assertIn("overclaims public_callback_abi_now", str(raised.exception))

    def test_rejects_consume_report_that_overclaims_nested_alias_key(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_consume_only_check_report(
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "consume",
                    "ready_scope": "runtime_evidence_only",
                    "ready": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "v1_completion_ready": False,
                    "runtime_ready": False,
                    "public_capability_bits_now": [],
                    "public_callback_abi_now": [],
                    "nested": {"publicReady": True},
                    "blockers": [],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "consume approved runtime principal lifecycle evidence check",
            )

        self.assertIn("overclaims readiness alias $.nested.publicReady", str(raised.exception))

    def test_rejects_check_reports_with_wrong_schema_mode_or_ready_scope(self) -> None:
        base = {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
            "mode": "consume",
            "ready_scope": "runtime_evidence_only",
            "ready": True,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "v1_completion_ready": False,
            "runtime_ready": False,
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "blockers": [],
            "remaining_blockers": [],
            "next_blocker": "identity_public_contract_gate_missing",
        }
        for key, value, expected in (
            ("schema", "obelisk.wrong-check.v1", "schema mismatch"),
            ("mode", "promote", "mode mismatch"),
            ("ready_scope", "public_sdk", "ready_scope mismatch"),
        ):
            with self.subTest(key=key):
                payload = dict(base)
                payload[key] = value
                with self.assertRaises(SystemExit) as raised:
                    bundle_builder.require_consume_only_check_report(
                        payload,
                        "consume approved runtime principal lifecycle evidence check",
                    )
                self.assertIn(expected, str(raised.exception))

    def test_rejects_consume_ready_report_with_blockers_or_wrong_next_blocker(self) -> None:
        base = {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
            "mode": "consume",
            "ready_scope": "runtime_evidence_only",
            "ready": True,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "v1_completion_ready": False,
            "runtime_ready": False,
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "blockers": [],
            "remaining_blockers": [],
            "next_blocker": "identity_public_contract_gate_missing",
        }
        cases = (
            ("blockers", {"blockers": ["contradictory_ready_blocker"]}, "reported blockers"),
            (
                "remaining_blockers",
                {"remaining_blockers": ["approved_runtime_evidence_not_accepted"]},
                "reported remaining blockers",
            ),
            ("next_blocker", {"next_blocker": "approved_runtime_evidence_not_accepted"}, "did not route"),
        )
        for name, overrides, expected in cases:
            with self.subTest(name=name):
                payload = dict(base)
                payload.update(overrides)
                with self.assertRaises(SystemExit) as raised:
                    bundle_builder.require_consume_only_check_report(
                        payload,
                        "consume approved runtime principal lifecycle evidence check",
                    )
                self.assertIn(expected, str(raised.exception))

    def test_rejects_negative_check_report_with_wrong_mode_or_scope(self) -> None:
        payload = {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
            "mode": "consume",
            "ready_scope": "runtime_evidence_only",
            "ready": False,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": ["promote_blocked_until_identity_public_contract_gate"],
            "next_blocker": "identity_public_contract_gate_missing",
        }
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_negative_readiness_report(
                payload,
                "promote approved runtime principal lifecycle evidence check",
                "promote_blocked_until_identity_public_contract_gate",
            )

        self.assertIn("mode mismatch", str(raised.exception))

    def test_rejects_negative_readiness_report_with_wrong_blocker(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_negative_readiness_report(
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "promote",
                    "ready_scope": "runtime_evidence_only",
                    "ready": False,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "blockers": ["approved_runtime_evidence_not_accepted"],
                    "next_blocker": "approved_runtime_evidence_not_accepted",
                },
                "promote approved runtime principal lifecycle evidence check",
                "promote_blocked_until_identity_public_contract_gate",
            )

        self.assertIn("failed for an unexpected blocker", str(raised.exception))

    def test_rejects_negative_readiness_report_with_stale_evidence_remaining_blocker(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bundle_builder.require_negative_readiness_report(
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                    "mode": "promote",
                    "ready_scope": "runtime_evidence_only",
                    "ready": False,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "blockers": ["promote_blocked_until_identity_public_contract_gate"],
                    "remaining_blockers": ["approved_runtime_evidence_not_accepted"],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
                "promote approved runtime principal lifecycle evidence check",
                "promote_blocked_until_identity_public_contract_gate",
            )

        self.assertIn("carried runtime evidence blockers despite accepted evidence", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
