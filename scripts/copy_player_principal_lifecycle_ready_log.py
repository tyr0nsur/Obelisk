#!/usr/bin/env python3
"""Copy a live player-principal lifecycle log only after role readiness is present.

This helper is operational glue, not an evidence checker. It refuses to copy until the
source log has the observer enable line and all required lifecycle roles with the
status proof fields expected by the approved evidence path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths


SCHEMA = "obelisk.player-principal-lifecycle-ready-log-copy.v1"
READY_LOG_EVIDENCE_SPLIT_SCHEMA = (
    "obelisk.player-principal-lifecycle-ready-log-copy-evidence-split.v1"
)
READY_LOG_ARTIFACT_BINDINGS_SCHEMA = (
    "obelisk.player-principal-lifecycle-copied-artifact-bindings.v1"
)
READY_LOG_COPY_REPORT_NAME = "ready-log-copy.json"
CURRENT_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
APPROVED_RUNTIME_EVIDENCE_CHECKER = (
    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
)
APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER = (
    "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
)
RUNTIME_OBSERVER_ANALYZER = "scripts/analyze_runtime_observer_log.py"
APPROVED_RUNTIME_MANIFEST_BUILDER = (
    "scripts/build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
)
REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = Path("/servidor/ark")
DEFAULT_LOG_ROOT = Path("/servidor/ark/obelisk/logs")
DEFAULT_PREFLIGHT_HELPER = REPO_ROOT / "scripts" / "check_player_principal_lifecycle_preflight.sh"
DEFAULT_WINDOW_MANIFEST_HELPER = (
    REPO_ROOT / "scripts" / "check_player_identity_runtime_principal_lifecycle_window_manifest.py"
)
DEFAULT_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
DEFAULT_REVIEWED_BY = "lead"
DEFAULT_REVIEW_NOTE = "ready-log copy consume-only runtime lifecycle evidence bundle candidate"
EXPECTED_SERVER_BINARY_PATH = "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer"
PLAYER_PRINCIPAL_LIFECYCLE_MODULE = "player_principal_lifecycle"
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
OBELISK_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$")
ANY_LOG_PREFIX_RE = re.compile(r"^\[(?P<prefix>[^\]]+)\]\s+")
UTC_TIMESTAMP_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z"
UTC_TIMESTAMP_RE = re.compile(r"^" + UTC_TIMESTAMP_PATTERN + r"$")
UTC_LOG_PREFIX_RE = re.compile(r"^\[(?P<timestamp>" + UTC_TIMESTAMP_PATTERN + r")\]\s+")
PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE = re.compile(
    r"PlayerPrincipalLifecycleObserver event sequence=(?P<sequence>\d+) "
    r"role=(?P<role>session_start|session_start_rejected|session_end)\b"
)
OBSERVER_ENABLED_RE = re.compile(
    r"PlayerPrincipalLifecycleObserver enabled\b.*\bbinary_sha256=(?P<sha>[A-Fa-f0-9]{64})\b"
)
LOG_KEY_VALUE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=([^ \t]+)")
PLAYER_PRESENCE_CONTEXT_RE = re.compile(
    r"\b(?:player_presence_context|player_presence_detected|presence_detected|"
    r"players_current|players_detected|players=)\b",
    re.IGNORECASE,
)
COPIED_LOG_PASSIVE_CONTEXT_METADATA_RE = re.compile(
    r"^(?:\[[^\]]+\]\s+)*(?:passive_monitor_session\b|tick utc=|query(?:_warning)? instance=|"
    r"linuxgsm_skipped instance=|rcon_listplayers instance=|player_presence_context\b|"
    r"player_presence_detected instance=|observer_tail instance=|observer instance=|"
    r"player_presence_linger_(?:start|extend|complete)\b|"
    r"passive_snapshot_(?:captured|failed)\b|runtime_window(?:_|\b)|"
    r"(?:player_)?notice(?:_|\b)|beta_notice(?:_|\b)|confirmed_(?:beta_)?notice(?:_|\b))"
)
COPIED_LOG_UNSAFE_TEXT_RE = re.compile(
    r"\b(?:steam(?:id|[_ -]?id)|eos[_ -]?id|unique[_ -]?net[_ -]?id|"
    r"player[_ -]?(?:id|name)|ip(?:v4|v6)?[_ -]?(?:address)?|tribe[_ -]?id|"
    r"chat[_ -]?(?:text|message|payload)|command[_ -]?(?:text|message|payload)|"
    r"permission[_ -]?state|admin[_ -]?state|resourcehandle|"
    r"uobject|ue[_ -]?pointer|raw[_ -]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_ -]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_ -]?hash|"
    r"hashed[_ -]?(?:private|identity|identifier|player))\b",
    re.IGNORECASE,
)
COPIED_LOG_UNSAFE_KEY_RE = re.compile(
    r"^(?:steam(?:id|[_-]?id)?|eos(?:[_-]?id)?|unique[_-]?net[_-]?id|"
    r"player[_-]?(?:id|name|data)|ip(?:v4|v6)?(?:[_-]?address)?|tribe[_-]?id|"
    r"platform[_-]?ids?|transfer[_-]?ids?|private[_-]?(?:identifier|user[_-]?data)|"
    r"chat[_-]?(?:text|message|payload)|command[_-]?(?:text|message|payload)|"
    r"permission[_-]?state|admin[_-]?state|resourcehandle|"
    r"gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_-]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_-]?hash|"
    r"hashed[_-]?(?:private|identity|identifier|player))$",
    re.IGNORECASE,
)
COPIED_LOG_ALLOWED_PRIVACY_KEYS = frozenset(
    (
        "principal_id_logged",
        "principal_generation_logged",
        "redacted_fields",
        "redacted_count",
    )
)
COPIED_LOG_REFLECTED_MODULE_RE = re.compile(
    r"(?:\[[^\]]+\]\s+)*Reflected (?P<module>[A-Za-z0-9_]+)\b"
)
COPIED_LOG_EXPERIMENTAL_MODULE_RE = re.compile(
    r"(?:\[[^\]]+\]\s+)*Experimental (?P<module>[A-Za-z0-9_]+) reflection enabled\b"
)
COPIED_LOG_ITEM_RETURN_GATE_RE = re.compile(
    r"(?:\[[^\]]+\]\s+)*Experimental item return event producer enabled\b"
)
REQUIRED_LIFECYCLE_EVENT_ROLES = (
    "session_start",
    "session_start_rejected",
    "session_end",
)
COPIED_EVIDENCE_ARTIFACT_RELATIVE_PATHS = (
    "Obelisk.log",
    "window-request.json",
    "observer-window.env",
    "operator-approval-request.md",
    "operator-approval-receipt.json",
    "preflight-pre.json",
    "preflight-post.json",
    "window-manifest.env",
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
)
COPIED_EVIDENCE_SIDECAR_RELATIVE_PATHS = tuple(
    rel for rel in COPIED_EVIDENCE_ARTIFACT_RELATIVE_PATHS if rel != "Obelisk.log"
)
COPIED_EVIDENCE_BUNDLE_INPUT_RELATIVE_PATHS = tuple(
    rel
    for rel in COPIED_EVIDENCE_ARTIFACT_RELATIVE_PATHS
    if rel != "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
)
EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER = REQUIRED_LIFECYCLE_EVENT_ROLES
INSTANCE_MAP_HINTS = {
    "arkserver2": "TheIsland",
    "arkserver3": "Genesis2",
    "arkserver": "Ragnarok",
}
ALLOWED_DUPLICATE_CONTEXT_ROLES = frozenset(("session_start", "session_end"))
PREFLIGHT_SCHEMA = "obelisk.player-principal-lifecycle-preflight.v1"
WINDOW_MANIFEST_CHECK_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1"
EXPECTED_PREFLIGHT_NON_CLAIM = (
    "preflight only; not runtime approval, not approved runtime evidence, "
    "and not permission to touch servers"
)
EXPECTED_WINDOW_MANIFEST_NEXT_BLOCKER = "approved_runtime_observer_log_summary_and_manifest_missing"
EXPECTED_WINDOW_MANIFEST_NEXT_REQUIRED_ARTIFACT = "approved_runtime_principal_lifecycle_evidence_bundle"
EXPECTED_WINDOW_MANIFEST_REQUIRED_ARTIFACT_STATUS = "missing_or_not_accepted"
EXPECTED_WINDOW_MANIFEST_NON_CLAIMS = (
    "window manifest acceptance is operational posture only",
    "does not promote player identity, lookup, permissions, commands, ResourceHandle, mutation, return override, plugin delivery, public SDK, or runtime readiness",
    "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
)
EXPECTED_ROLLBACK_DELTA = "removed_observer_env_and_markers_preserved_disable_plugins"
NON_EVIDENCE_SOURCE_JSON_SCHEMA_REASONS = {
    SCHEMA: "source_log_is_ready_log_copy_report_not_obelisk_log",
    PREFLIGHT_SCHEMA: "source_log_is_preflight_report_not_obelisk_log",
    WINDOW_MANIFEST_CHECK_SCHEMA: "source_log_is_window_manifest_check_report_not_obelisk_log",
    "obelisk.sdk-status-report.v1": "source_log_is_sdk_status_report_not_obelisk_log",
    "obelisk.player-principal-lifecycle-runtime-evidence-status.v1": (
        "source_log_is_runtime_evidence_status_report_not_obelisk_log"
    ),
    "obelisk.player-principal-lifecycle-runtime-evidence-status-machine-next-actions.v1": (
        "source_log_is_runtime_evidence_status_report_not_obelisk_log"
    ),
    "obelisk.player-principal-passive-snapshot.v1": "source_log_is_passive_snapshot_not_obelisk_log",
    "obelisk.player-principal-passive-monitor-only-summary.v1": (
        "source_log_is_passive_monitor_report_not_obelisk_log"
    ),
    "obelisk.player-principal-lifecycle-watcher-context.v1": (
        "source_log_is_watcher_monitor_context_not_obelisk_log"
    ),
    "obelisk.player-principal-lifecycle-monitor-context.v1": (
        "source_log_is_watcher_monitor_context_not_obelisk_log"
    ),
    "obelisk.player-principal-lifecycle-beta-notice-prep.v1": (
        "source_log_is_beta_notice_report_not_obelisk_log"
    ),
    "obelisk.discord-beta-bridge-active-notice.v1": (
        "source_log_is_discord_bridge_state_not_obelisk_log"
    ),
    "obelisk.discord-beta-bridge-bot-notice.v1": (
        "source_log_is_discord_bridge_state_not_obelisk_log"
    ),
    "obelisk.discord-beta-bridge-dry-run-receipt.v1": (
        "source_log_is_discord_bridge_state_not_obelisk_log"
    ),
    "obelisk.discord-beta-bridge-event-summary.v1": (
        "source_log_is_discord_bridge_state_not_obelisk_log"
    ),
    "obelisk.discord-beta-bridge-tester-status-summary.v1": (
        "source_log_is_discord_bridge_state_not_obelisk_log"
    ),
    "obelisk.player-principal-lifecycle-window-request.v1": (
        "source_log_is_window_request_not_obelisk_log"
    ),
}
REQUIRED_LIFECYCLE_EVENT_SHAPES = {
    "session_start": {
        "target": "ShooterGameMode.HandleNewPlayer",
        "post_original": "true",
        "copied_bool_fields": "bIsFromLogin,ReturnValue",
        "copied_bool_values": "1,1",
        "redacted_count": "3",
        "redacted_fields": "NewPlayer,PlayerData,PlayerCharacter",
        "principal_action": "candidate_created",
        "apply_status": "session_start_created",
        "correlation_status": "not_applicable",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
    "session_start_rejected": {
        "target": "ShooterGameMode.CheckJoinInProgress",
        "post_original": "true",
        "copied_bool_fields": "bIsFromLogin,ReturnValue",
        "copied_bool_values": "1,0",
        "redacted_count": "1",
        "redacted_fields": "NewPlayer",
        "principal_action": "none",
        "apply_status": "session_start_rejected_noop",
        "correlation_status": "not_applicable",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
    "session_end": {
        "target": "ShooterGameMode.OnLogout",
        "post_original": "true",
        "copied_bool_fields": "",
        "copied_bool_values": "",
        "redacted_count": "1",
        "redacted_fields": "Exiting",
        "principal_action": "candidate_invalidated",
        "apply_status": "session_end_invalidated",
        "correlation_status": "matched",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
}
FALSE_FLAGS = {
    "approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "v1_completion_ready": False,
    "stable_claim_allowed": False,
    "publication_authorized": False,
    "discord_sent_by_this_report": False,
    "server_operations_authorized_by_this_report": False,
    "marker_env_changes_authorized_by_this_report": False,
    "copied_log_only_counts_as_approved_runtime_evidence": False,
    "copied_log_only_counts_as_runtime_evidence": False,
    "ready_to_copy_counts_as_approved_runtime_evidence": False,
    "post_window_sidecars_count_as_approved_runtime_evidence": False,
    "checker_ready_counts_as_approved_runtime_evidence": False,
    "start_end_only_counts_as_approved_runtime_evidence": False,
    "start_end_only_counts_as_runtime_evidence": False,
    "counts_toward_sdk": False,
    "counts_toward_v1_completion": False,
    "counts_toward_complete_sdk_claim_now": False,
    "counts_toward_p0_dependency_chain": False,
    "counts_toward_p0_dependency_chain_claim_now": False,
    "sdk_progress": 0,
    "p0_progress": 0,
}


def target_hint(instance: str) -> dict[str, str]:
    hint = {"instance": instance}
    map_name = INSTANCE_MAP_HINTS.get(instance)
    if map_name:
        hint["map"] = map_name
    return hint


def no_role_window_manual_steps(
    detected: bool,
    *,
    window_state: str,
    map_name: str | None,
) -> list[str]:
    if not detected:
        return []
    if window_state == "in_progress":
        return [
            "keep the observer-enable-only window open until fresh_window_end_utc",
            "rerun the dry-run against the fresh source log if lifecycle events arrive before the window ends",
            "do not copy or promote the source log until the exact lifecycle triplet is present",
        ]
    target_map = map_name or "the target map"
    return [
        "treat the observer-enable-only window as closed non-evidence",
        "do not copy or promote the source log until the exact lifecycle triplet is present",
        f"prepare a fresh player-backed {target_map} window under separate current-turn scope if evidence is still needed",
    ]


def observer_only_no_role_window_state(
    instance: str,
    analysis: dict[str, Any],
    *,
    player_presence_context: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    presence_context = player_presence_context if isinstance(player_presence_context, dict) else {}
    roles_present = [
        role
        for role in REQUIRED_LIFECYCLE_EVENT_ROLES
        if role in set(str(item) for item in analysis.get("roles_present", []))
    ]
    missing_roles = [
        role
        for role in REQUIRED_LIFECYCLE_EVENT_ROLES
        if role in set(str(item) for item in analysis.get("missing_roles", []))
    ]
    detected = (
        analysis.get("observer_enabled") is True
        and analysis.get("observer_enable_in_fresh_window") is True
        and analysis.get("binary_sha256_match") is True
        and not roles_present
        and missing_roles == list(REQUIRED_LIFECYCLE_EVENT_ROLES)
        and analysis.get("accepted_lifecycle_event_count") == 0
        and analysis.get("copy_readiness") == "blocked_missing_lifecycle_roles"
    )
    fresh_window = analysis.get("fresh_window", {})
    fresh_window_start = None
    fresh_window_end = None
    if isinstance(fresh_window, dict):
        start_value = fresh_window.get("start_utc")
        end_value = fresh_window.get("end_utc")
        fresh_window_start = parse_utc_timestamp(start_value) if isinstance(start_value, str) else None
        fresh_window_end = parse_utc_timestamp(end_value) if isinstance(end_value, str) else None
    observed_now = now or datetime.now(timezone.utc)
    if not detected:
        window_state = "not_detected"
    elif fresh_window_start is None or fresh_window_end is None:
        window_state = "timing_unknown"
    elif observed_now < fresh_window_start:
        window_state = "pre_window"
    elif observed_now <= fresh_window_end:
        window_state = "in_progress"
    else:
        window_state = "post_window"
    classification = {
        "not_detected": "not_observer_only_no_role_window",
        "pre_window": "observer_enabled_no_lifecycle_roles_window_not_started",
        "in_progress": "observer_enabled_no_lifecycle_roles_window_in_progress",
        "post_window": "observer_enabled_no_lifecycle_roles_post_window",
        "timing_unknown": "observer_enabled_no_lifecycle_roles_timing_unknown",
    }[window_state]
    hint = target_hint(instance)
    active_in_progress = detected and window_state == "in_progress"
    post_window = detected and window_state == "post_window"
    expired_no_evidence = post_window
    players_detected = presence_context.get("players_detected") is True
    player_present_but_no_lifecycle_roles = detected and players_detected
    source_blockers = ["observer_enabled_but_no_lifecycle_roles"] if detected else []
    if player_present_but_no_lifecycle_roles:
        source_blockers.append("player_present_but_no_lifecycle_roles")
    return {
        "schema": "obelisk.player-principal-lifecycle-source-log-not-ready.v1",
        "classification": classification,
        "blockers": source_blockers,
        "observer_only_no_role_window_detected": detected,
        "active_observer_only_no_role_window": active_in_progress,
        "post_window_observer_only_no_role_window": post_window,
        "player_present_but_no_lifecycle_roles": player_present_but_no_lifecycle_roles,
        "player_present_no_lifecycle_roles_blocker": (
            "player_present_but_no_lifecycle_roles"
            if player_present_but_no_lifecycle_roles
            else None
        ),
        "player_presence_context": presence_context,
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "source_log_not_ready": detected,
        "source_log_not_ready_reason": classification if detected else None,
        "window_state": window_state,
        "now_utc": observed_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_hint": hint,
        "fresh_window": fresh_window,
        "observer_enabled": analysis.get("observer_enabled") is True,
        "observer_enable_in_fresh_window": analysis.get("observer_enable_in_fresh_window") is True,
        "binary_sha256_match": analysis.get("binary_sha256_match") is True,
        "accepted_lifecycle_event_count": int(analysis.get("accepted_lifecycle_event_count") or 0),
        "roles_present": roles_present,
        "missing_roles": missing_roles,
        "copy_readiness": analysis.get("copy_readiness"),
        "ready_to_copy": False,
        "copied_log_ready": False,
        "accepted_ready": False,
        "accepted_ready_for_evidence_closure": False,
        "accepted_ready_counts_as_approved_runtime_evidence": False,
        "expired_no_evidence": expired_no_evidence,
        "expired_no_evidence_reason": classification if expired_no_evidence else None,
        "copied_log_available_for_closure": post_window,
        "copied_log_available_for_non_evidence_closure": post_window,
        "copied_log_available_for_evidence_closure": False,
        "post_window_closure_action": (
            "close_observer_only_no_role_window_as_non_evidence" if post_window else None
        ),
        "next_status_input_needed": (
            "fresh_source_log_with_exact_lifecycle_triplet"
            if detected
            else "copy_ready_report_with_source_analysis"
        ),
        "manual_offline_next_steps": no_role_window_manual_steps(
            detected,
            window_state=window_state,
            map_name=hint.get("map"),
        ),
        "copied_log_readiness_is_operational_only": True,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True, help="Instance id used for default source log path.")
    parser.add_argument("--source-log", type=Path, help="Source Obelisk.log. Defaults to live instance log.")
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--expected-binary-sha256", default=DEFAULT_BINARY_SHA256)
    parser.add_argument(
        "--fresh-window-start-utc",
        "--window-start-utc",
        dest="fresh_window_start_utc",
        help="Inclusive UTC ISO start for source-log lifecycle readiness, e.g. 2026-06-06T13:55:00Z.",
    )
    parser.add_argument(
        "--fresh-window-end-utc",
        "--window-end-utc",
        dest="fresh_window_end_utc",
        help="Inclusive UTC ISO end for source-log lifecycle readiness, e.g. 2026-06-06T14:10:00Z.",
    )
    parser.add_argument(
        "--now-utc",
        help="UTC timestamp override for fixture-only dry-run state classification.",
    )
    parser.add_argument("--allow-live-log-read", action="store_true")
    parser.add_argument("--allow-evidence-dir-write", action="store_true")
    parser.add_argument(
        "--allow-post-window-sidecar-generation",
        action="store_true",
        help=(
            "When --execute copies a ready log, also require preflight-pre.json and "
            "write/check preflight-post.json plus window-manifest.env."
        ),
    )
    parser.add_argument(
        "--allow-post-window-preflight-live-read",
        action="store_true",
        help=(
            "Permit the post-window stable preflight helper to read live/procfs posture. "
            "This is separate from --allow-live-log-read."
        ),
    )
    parser.add_argument("--preflight-helper", type=Path, default=DEFAULT_PREFLIGHT_HELPER)
    parser.add_argument("--window-manifest-helper", type=Path, default=DEFAULT_WINDOW_MANIFEST_HELPER)
    parser.add_argument("--reviewed-by", default=DEFAULT_REVIEWED_BY)
    parser.add_argument("--review-note", default=DEFAULT_REVIEW_NOTE)
    parser.add_argument("--execute", action="store_true", help="Actually copy when ready.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing copied Obelisk.log.")
    parser.add_argument("--json-output", type=Path, help="Optional output path. Use '-' for stdout.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolved_path_text(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def artifact_hash_path_binding(evidence_dir: Path, relative_path: str) -> dict[str, Any]:
    path = evidence_dir / relative_path
    symlink = protected_paths.first_symlink_component(path)
    present = symlink is None and path.is_file()
    binding: dict[str, Any] = {
        "relative_path": relative_path,
        "path": str(path),
        "resolved_path": resolved_path_text(path),
        "present": present,
        "symlink_component": None if symlink is None else str(symlink),
        "sha256": None,
        "size_bytes": None,
        "hash_path_bound": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
    }
    if present:
        binding.update(
            {
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "hash_path_bound": True,
            }
        )
    return binding


def copied_artifact_binding_report(evidence_dir: Path) -> dict[str, Any]:
    bindings = [
        artifact_hash_path_binding(evidence_dir, relative_path)
        for relative_path in COPIED_EVIDENCE_ARTIFACT_RELATIVE_PATHS
    ]
    by_relative_path = {
        str(binding["relative_path"]): binding for binding in bindings
    }
    sidecar_bindings = [
        by_relative_path[relative_path]
        for relative_path in COPIED_EVIDENCE_SIDECAR_RELATIVE_PATHS
    ]
    bundle_input_bindings = [
        by_relative_path[relative_path]
        for relative_path in COPIED_EVIDENCE_BUNDLE_INPUT_RELATIVE_PATHS
    ]
    copied_log = by_relative_path["Obelisk.log"]
    approved_bundle = by_relative_path[
        "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
    ]
    missing = [
        str(binding["relative_path"])
        for binding in bindings
        if binding["hash_path_bound"] is not True
    ]
    return {
        "schema": READY_LOG_ARTIFACT_BINDINGS_SCHEMA,
        "evidence_dir": str(evidence_dir),
        "copied_log": copied_log,
        "sibling_sidecars": sidecar_bindings,
        "bundle_input_artifacts": bundle_input_bindings,
        "approved_runtime_manifest": approved_bundle,
        "all_artifacts": bindings,
        "by_relative_path": by_relative_path,
        "copied_log_hash_path_bound": copied_log["hash_path_bound"] is True,
        "sibling_sidecars_hash_path_bound": all(
            binding["hash_path_bound"] is True for binding in sidecar_bindings
        ),
        "bundle_input_artifacts_hash_path_bound": all(
            binding["hash_path_bound"] is True for binding in bundle_input_bindings
        ),
        "complete_sibling_set_hash_path_bound": all(
            binding["hash_path_bound"] is True for binding in bindings
        ),
        "missing_hash_path_bindings": missing,
        "hash_path_binding_counts_as_approved_runtime_evidence": False,
        "hash_path_binding_counts_as_runtime_evidence": False,
        "hash_path_binding_counts_as_sdk_evidence": False,
    }


def default_source_log(instance: str) -> Path:
    if SAFE_COMPONENT_RE.fullmatch(instance) is None:
        raise SystemExit("--instance contains unsafe characters")
    return DEFAULT_LOG_ROOT / instance / "Obelisk.log"


def path_status(path: Path) -> protected_paths.ProtectedPathStatus:
    protected_paths.reject_symlink_component(path, str(path))
    return protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )


def resolve_source(path: Path, *, allow_live_log_read: bool) -> tuple[Path, list[str]]:
    blockers: list[str] = []
    status = path_status(path)
    if status.protected and not allow_live_log_read:
        blockers.append(f"live_log_read_requires_explicit_flag:{status.resolved}")
    if not status.resolved.is_file():
        blockers.append(f"source_log_missing:{status.resolved}")
    return status.resolved, blockers


def resolve_evidence_dir(path: Path) -> tuple[Path, list[str]]:
    blockers: list[str] = []
    status = path_status(path)
    if status.protected:
        blockers.append(f"evidence_dir_under_protected_server_root:{status.resolved}")
    if status.resolved.exists() and not status.resolved.is_dir():
        blockers.append(f"evidence_dir_not_directory:{status.resolved}")
    return status.resolved, blockers


def parse_key_values(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for token in line.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            values[key] = value.rstrip(".")
    return values


def parse_nonnegative_int(value: str | None) -> int | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"^(\d+)(?:/\d+)?$", value)
    if match is None:
        return None
    return int(match.group(1))


def truthy_text(value: str | None) -> bool:
    return isinstance(value, str) and value.rstrip(".").casefold() in {
        "1",
        "true",
        "yes",
        "players_detected",
        "detected",
    }


def player_presence_context_state(text: str) -> dict[str, Any]:
    lines: list[dict[str, Any]] = []
    targets: set[str] = set()
    players_detected = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if PLAYER_PRESENCE_CONTEXT_RE.search(line) is None:
            continue
        values = parse_key_values(line)
        players_current = parse_nonnegative_int(values.get("players_current"))
        if players_current is None:
            players_current = parse_nonnegative_int(values.get("players"))
        presence_detected = (
            truthy_text(values.get("presence_detected"))
            or truthy_text(values.get("player_presence_context"))
            or truthy_text(values.get("status"))
            or "player_presence_detected" in line
            or "players_detected" in line
            or (players_current is not None and players_current > 0)
        )
        players_detected = players_detected or presence_detected
        target = values.get("target_key")
        if not target:
            instance = values.get("instance")
            map_name = values.get("map")
            query_port = values.get("query_port")
            if instance and map_name and query_port:
                target = f"{instance}:{map_name}:{query_port}"
            elif instance and map_name:
                target = f"{instance}:{map_name}"
        if target:
            targets.add(target.rstrip("."))
        line_state: dict[str, Any] = {
            "line": line_number,
            "presence_detected": presence_detected,
        }
        if players_current is not None:
            line_state["players_current"] = players_current
        if target:
            line_state["target"] = target.rstrip(".")
        lines.append(line_state)

    return {
        "classification": (
            "players_detected_operator_context_non_evidence"
            if players_detected
            else "player_presence_context_absent"
            if not lines
            else "player_presence_context_without_players_non_evidence"
        ),
        "context_present": bool(lines),
        "players_detected": players_detected,
        "indicator_line_count": len(lines),
        "indicator_lines": lines[:10],
        "targets": sorted(targets),
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "player_presence_context_counts_as_runtime_evidence": False,
        "player_presence_context_counts_as_sdk_evidence": False,
    }


def copied_log_safety_state(text: str) -> dict[str, Any]:
    passive_lines: list[dict[str, Any]] = []
    unsafe_lines: list[dict[str, Any]] = []
    diagnostic_lifecycle_lines: list[dict[str, Any]] = []
    non_lifecycle_observer_lines: list[dict[str, Any]] = []
    unexpected_observer_modules: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if COPIED_LOG_PASSIVE_CONTEXT_METADATA_RE.match(stripped):
            passive_lines.append(
                {
                    "line": line_number,
                    "prefix": stripped.split(" ", 1)[0],
                }
            )
        unsafe_keys = sorted(
            {
                key
                for key, _value in LOG_KEY_VALUE_RE.findall(line)
                if key not in COPIED_LOG_ALLOWED_PRIVACY_KEYS
                and COPIED_LOG_UNSAFE_KEY_RE.fullmatch(key)
            }
        )
        text_match = COPIED_LOG_UNSAFE_TEXT_RE.search(line)
        if unsafe_keys or text_match is not None:
            line_detail: dict[str, Any] = {"line": line_number}
            if unsafe_keys:
                line_detail["unsafe_keys"] = unsafe_keys
            if text_match is not None:
                line_detail["unsafe_text_indicator"] = text_match.group(0)
            unsafe_lines.append(line_detail)
        if (
            "PlayerPrincipalLifecycleDiagnostic " in stripped
            or "PlayerPrincipalLifecycleObserver diagnostic" in stripped
        ):
            diagnostic_values = parse_key_values(line)
            diagnostic_detail: dict[str, Any] = {"line": line_number}
            for key in (
                "target",
                "diagnostic_shape",
                "copy_status",
                "read_status",
                "accepted_lifecycle_target",
            ):
                value = diagnostic_values.get(key)
                if value is not None:
                    diagnostic_detail[key] = value
            diagnostic_lifecycle_lines.append(diagnostic_detail)
        if match := COPIED_LOG_EXPERIMENTAL_MODULE_RE.match(stripped):
            module = match.group("module")
            if module != PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
                unexpected_observer_modules.add(module)
            else:
                non_lifecycle_observer_lines.append({"line": line_number, "kind": "experimental_gate"})
        if COPIED_LOG_ITEM_RETURN_GATE_RE.match(stripped):
            unexpected_observer_modules.add("item_return")
        if match := COPIED_LOG_REFLECTED_MODULE_RE.match(stripped):
            module = match.group("module")
            if module == PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
                non_lifecycle_observer_lines.append({"line": line_number, "kind": "reflected_lifecycle"})
            else:
                unexpected_observer_modules.add(module)

    blockers: list[str] = []
    if passive_lines:
        blockers.append("source_log_contains_passive_context_metadata")
    if unsafe_lines:
        blockers.append("source_log_contains_unsafe_player_text")
    if diagnostic_lifecycle_lines:
        blockers.append("source_log_contains_lifecycle_diagnostic_lines")
    if non_lifecycle_observer_lines:
        blockers.append("source_log_contains_non_lifecycle_observer_lines")
    if unexpected_observer_modules:
        blockers.append("source_log_contains_unexpected_observer_modules")
    player_presence_context = player_presence_context_state(text)
    return {
        "accepted": not blockers,
        "blockers": blockers,
        "passive_context_line_count": len(passive_lines),
        "passive_context_lines": passive_lines[:10],
        "unsafe_player_text_line_count": len(unsafe_lines),
        "unsafe_player_text_lines": unsafe_lines[:10],
        "lifecycle_diagnostic_line_count": len(diagnostic_lifecycle_lines),
        "lifecycle_diagnostic_lines": diagnostic_lifecycle_lines[:10],
        "non_lifecycle_observer_line_count": len(non_lifecycle_observer_lines),
        "non_lifecycle_observer_lines": non_lifecycle_observer_lines[:10],
        "unexpected_observer_modules": sorted(unexpected_observer_modules),
        "player_presence_context": player_presence_context,
        "passive_context_counts_as_approved_runtime_evidence": False,
        "unsafe_player_text_counts_as_approved_runtime_evidence": False,
        "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence": False,
    }


def source_input_state(text: str) -> dict[str, Any]:
    stripped = text.lstrip()
    state: dict[str, Any] = {
        "accepted": True,
        "classification": "obelisk_log_text_candidate",
        "schema": None,
        "json_top_level_keys": [],
        "blockers": [],
        "source_input_counts_as_approved_runtime_evidence": False,
        "source_input_counts_as_runtime_evidence": False,
        "source_input_counts_as_sdk_evidence": False,
    }
    if not stripped.startswith("{"):
        return state
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        state["classification"] = "json_like_text_not_parsed_as_report"
        return state
    if not isinstance(payload, dict):
        state["classification"] = "json_non_object_not_obelisk_log"
        state["accepted"] = False
        state["blockers"] = ["source_log_is_json_report_not_obelisk_log"]
        return state

    schema = payload.get("schema")
    schema_text = schema if isinstance(schema, str) else None
    blocker = NON_EVIDENCE_SOURCE_JSON_SCHEMA_REASONS.get(
        schema_text,
        "source_log_is_json_report_not_obelisk_log",
    )
    state.update(
        {
            "accepted": False,
            "classification": "non_evidence_json_report"
            if schema_text in NON_EVIDENCE_SOURCE_JSON_SCHEMA_REASONS
            else "json_report_not_obelisk_log",
            "schema": schema_text,
            "json_top_level_keys": sorted(str(key) for key in payload.keys())[:20],
            "blockers": [blocker, "source_log_is_not_copied_obelisk_log_text"],
        }
    )
    return state


def validate_json_output_path(args: argparse.Namespace, evidence_dir: Path) -> dict[str, Any]:
    state: dict[str, Any] = {
        "requested": args.json_output is not None,
        "path": str(args.json_output) if args.json_output is not None else None,
        "resolved_path": None,
        "accepted": True,
        "expected_execute_report_path": None,
        "blockers": [],
        "report_counts_as_approved_runtime_evidence": False,
        "report_counts_as_runtime_evidence": False,
        "report_counts_as_sdk_evidence": False,
    }
    if args.json_output is None or str(args.json_output) == "-":
        return state

    output_path = args.json_output.expanduser()
    symlink = protected_paths.first_symlink_component(output_path)
    if symlink is not None:
        state["accepted"] = False
        state["blockers"].append(f"json_output_path_symlink_component:{symlink}")

    status = protected_paths.protected_path_status(
        output_path,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )
    state["resolved_path"] = str(status.resolved)
    if status.protected:
        state["accepted"] = False
        state["blockers"].append(f"json_output_under_protected_server_root:{status.resolved}")
    if status.resolved.exists() and status.resolved.is_dir():
        state["accepted"] = False
        state["blockers"].append(f"json_output_is_directory:{status.resolved}")

    if args.execute:
        expected_status = protected_paths.protected_path_status(
            evidence_dir / READY_LOG_COPY_REPORT_NAME,
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
        expected = expected_status.resolved
        state["expected_execute_report_path"] = str(expected)
        if status.resolved != expected:
            state["accepted"] = False
            state["blockers"].append(
                "json_output_not_bound_to_evidence_dir_ready_log_copy_report:"
                f"{status.resolved}"
            )
    return state


def parse_utc_timestamp(value: str) -> datetime | None:
    if UTC_TIMESTAMP_RE.fullmatch(value) is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_fresh_window(args: argparse.Namespace) -> tuple[datetime | None, datetime | None, list[str]]:
    blockers: list[str] = []
    start_value = args.fresh_window_start_utc
    end_value = args.fresh_window_end_utc

    start = parse_utc_timestamp(start_value) if isinstance(start_value, str) else None
    end = parse_utc_timestamp(end_value) if isinstance(end_value, str) else None

    if not start_value:
        blockers.append("fresh_window_start_utc_required")
    elif start is None:
        blockers.append("fresh_window_start_utc_invalid")
    if not end_value:
        blockers.append("fresh_window_end_utc_required")
    elif end is None:
        blockers.append("fresh_window_end_utc_invalid")
    if start is not None and end is not None and start >= end:
        blockers.append("fresh_window_not_forward")

    return start, end, blockers


def relevant_observer_line_kind(line: str) -> str | None:
    if "PlayerPrincipalLifecycleObserver enabled" in line:
        return "observer_enabled"
    if "PlayerPrincipalLifecycleObserver event" in line:
        return "lifecycle_event"
    return None


def simplified_lifecycle_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": event.get("role"),
        "line_number": event.get("line_number"),
        "sequence": event.get("sequence"),
        "target": event.get("target"),
        "timestamp_prefix": event.get("timestamp_prefix"),
        "inside_fresh_window": event.get("inside_fresh_window"),
    }


def lifecycle_triplet_order_state(events_by_role: dict[str, dict[str, Any]]) -> dict[str, Any]:
    missing_roles = [
        role for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER if role not in events_by_role
    ]
    observed_roles_by_line = [
        event.get("role")
        for event in sorted(
            events_by_role.values(),
            key=lambda event: int(event.get("line_number", 0)),
        )
    ]
    if missing_roles:
        return {
            "status": "incomplete",
            "expected_roles": list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER),
            "observed_roles_by_line": observed_roles_by_line,
            "sequence_by_role": {
                role: events_by_role[role].get("sequence")
                for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
                if role in events_by_role
            },
            "timestamp_by_role": {
                role: events_by_role[role].get("timestamp_prefix")
                for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
                if role in events_by_role
            },
            "blockers": [],
            "missing_roles": missing_roles,
        }

    ordered_events = [events_by_role[role] for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER]
    sequences = [int(event["sequence"]) for event in ordered_events]
    parsed_timestamps = [
        parse_utc_timestamp(str(event.get("timestamp_prefix"))) for event in ordered_events
    ]
    blockers: list[str] = []
    if observed_roles_by_line != list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER):
        blockers.append("accepted_lifecycle_role_line_order_mismatch")
    if any(current <= previous for previous, current in zip(sequences, sequences[1:])):
        blockers.append("accepted_lifecycle_sequence_order_mismatch")
    if any(timestamp is None for timestamp in parsed_timestamps):
        blockers.append("accepted_lifecycle_timestamp_order_unavailable")
    else:
        ordered_timestamps = [timestamp for timestamp in parsed_timestamps if timestamp is not None]
        if any(current < previous for previous, current in zip(ordered_timestamps, ordered_timestamps[1:])):
            blockers.append("accepted_lifecycle_timestamp_order_mismatch")

    return {
        "status": "matched" if not blockers else "mismatch",
        "expected_roles": list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER),
        "observed_roles_by_line": observed_roles_by_line,
        "sequence_by_role": {
            role: events_by_role[role].get("sequence")
            for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
        },
        "timestamp_by_role": {
            role: events_by_role[role].get("timestamp_prefix")
            for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
        },
        "blockers": blockers,
    }


def strict_lifecycle_triplet_selection(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_role: dict[str, list[dict[str, Any]]] = {
        role: [] for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
    }
    for index, event in enumerate(events):
        role = event.get("role")
        if (
            isinstance(role, str)
            and role in by_role
            and event.get("approved_copy_shape_ok") is True
            and event.get("inside_fresh_window") is True
        ):
            by_role[role].append({**event, "index": index})

    def ordered(candidate: list[dict[str, Any]]) -> bool:
        for key in ("sequence", "line_number"):
            values = [event.get(key) for event in candidate]
            if not all(isinstance(value, int) for value in values):
                return False
            if any(current <= previous for previous, current in zip(values, values[1:])):
                return False
        return True

    candidates: list[list[dict[str, Any]]] = []
    for start in by_role["session_start"]:
        for rejected in by_role["session_start_rejected"]:
            for end in by_role["session_end"]:
                candidate = [start, rejected, end]
                if ordered(candidate):
                    candidates.append(candidate)

    missing_roles = [
        role for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER if not by_role[role]
    ]
    duplicate_roles = [
        role for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER if len(by_role[role]) > 1
    ]
    selected: list[dict[str, Any]] | None = None
    status = "selected"
    forced_ambiguous = len(by_role["session_start_rejected"]) > 1
    if forced_ambiguous:
        selected = None
    elif len(candidates) == 1:
        selected = candidates[0]
    elif candidates and set(duplicate_roles).issubset(ALLOWED_DUPLICATE_CONTEXT_ROLES):
        selected = min(
            candidates,
            key=lambda candidate: (
                candidate[1]["sequence"],
                candidate[1]["line_number"],
                -candidate[0]["sequence"],
                -candidate[0]["line_number"],
                candidate[2]["sequence"],
                candidate[2]["line_number"],
            ),
        )
        status = "selected_with_duplicate_start_end_context"

    if selected is None:
        return {
            "status": "ambiguous" if forced_ambiguous or len(candidates) > 1 else "missing",
            "selected": False,
            "accepted": False,
            "candidate_count": len(candidates),
            "selected_indices": [],
            "selected_sequences": [],
            "selected_lines": [],
            "selected_roles": [],
            "missing_roles": missing_roles,
            "non_counting_context_event_count": len(events),
            "non_counting_context_roles": duplicate_roles,
            "candidate_triplets": [
                [
                    {
                        "role": event.get("role"),
                        "sequence": event.get("sequence"),
                        "line_number": event.get("line_number"),
                        "timestamp_prefix": event.get("timestamp_prefix"),
                    }
                    for event in candidate
                ]
                for candidate in candidates[:5]
            ],
        }

    selected_indices = {event["index"] for event in selected}
    context_events = [
        event for index, event in enumerate(events) if index not in selected_indices
    ]
    return {
        "status": status,
        "selected": True,
        "accepted": status == "selected",
        "selected_context_only": status != "selected",
        "candidate_count": len(candidates),
        "selected_indices": [event["index"] for event in selected],
        "selected_sequences": [event.get("sequence") for event in selected],
        "selected_lines": [event.get("line_number") for event in selected],
        "selected_roles": [event.get("role") for event in selected],
        "missing_roles": [],
        "non_counting_context_event_count": len(context_events),
        "non_counting_context_roles": [
            role
            for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
            if any(event.get("role") == role for event in context_events)
        ],
        "candidate_triplets": [
            [
                {
                    "role": event.get("role"),
                    "sequence": event.get("sequence"),
                    "line_number": event.get("line_number"),
                    "timestamp_prefix": event.get("timestamp_prefix"),
                }
                for event in selected
            ]
        ],
    }


def selected_lifecycle_triplet_order_state(
    events: list[dict[str, Any]],
    selection: dict[str, Any],
) -> dict[str, Any]:
    observed_roles_by_line = [
        event.get("role")
        for event in sorted(events, key=lambda event: int(event.get("line_number", 0)))
    ]
    if selection.get("accepted") is not True and selection.get("selected") is not True:
        missing_roles = selection.get("missing_roles", [])
        status = (
            "ambiguous"
            if selection.get("status") == "ambiguous"
            else "incomplete"
            if missing_roles
            else "mismatch"
        )
        blockers = (
            ["accepted_lifecycle_strict_triplet_ambiguous"]
            if status == "ambiguous"
            else []
            if missing_roles
            else [
                *(
                    ["accepted_lifecycle_role_line_order_mismatch"]
                    if observed_roles_by_line != list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER)
                    else []
                ),
                "accepted_lifecycle_strict_triplet_order_mismatch",
            ]
        )
        return {
            "status": status,
            "expected_roles": list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER),
            "observed_roles_by_line": observed_roles_by_line,
            "sequence_by_role": {},
            "timestamp_by_role": {},
            "blockers": blockers,
            "missing_roles": missing_roles,
        }

    selected_indices = set(selection.get("selected_indices", []))
    selected_events = [
        event for index, event in enumerate(events) if index in selected_indices
    ]
    selected_events.sort(key=lambda event: int(event.get("line_number", 0)))
    return {
        "status": "matched",
        "expected_roles": list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER),
        "observed_roles_by_line": [event.get("role") for event in selected_events],
        "sequence_by_role": {
            str(event.get("role")): event.get("sequence") for event in selected_events
        },
        "timestamp_by_role": {
            str(event.get("role")): event.get("timestamp_prefix") for event in selected_events
        },
        "blockers": [],
    }


def accepted_lifecycle_context_quality_blockers(events: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    ordered = sorted(events, key=lambda event: int(event.get("line_number", 0)))
    sequences = [event.get("sequence") for event in ordered]
    if any(not isinstance(sequence, int) for sequence in sequences):
        blockers.append("accepted_lifecycle_context_sequence_unavailable")
    elif any(current <= previous for previous, current in zip(sequences, sequences[1:])):
        blockers.append("accepted_lifecycle_context_sequence_order_mismatch")

    timestamps: list[datetime] = []
    for event in ordered:
        timestamp = event.get("timestamp_prefix")
        parsed = parse_utc_timestamp(str(timestamp)) if isinstance(timestamp, str) else None
        if parsed is None:
            blockers.append("accepted_lifecycle_context_timestamp_order_unavailable")
            break
        timestamps.append(parsed)
    if timestamps and any(current < previous for previous, current in zip(timestamps, timestamps[1:])):
        blockers.append("accepted_lifecycle_context_timestamp_order_mismatch")
    return blockers


def exact_copied_runtime_triplet_state(
    accepted_events: list[dict[str, Any]],
    triplet_order: dict[str, Any],
    selection: dict[str, Any],
    context_quality_blockers: list[str],
) -> dict[str, Any]:
    blockers: list[str] = []
    accepted_roles = [
        role
        for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
        if any(event.get("role") == role for event in accepted_events)
    ]
    accepted_role_set = set(accepted_roles)
    missing_roles = [
        role for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER if role not in accepted_role_set
    ]
    selected_indices = set(selection.get("selected_indices", []))
    selected_by_role = {
        str(event.get("role")): event
        for index, event in enumerate(accepted_events)
        if index in selected_indices
    }
    for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER:
        event = selected_by_role.get(role)
        if role not in accepted_role_set:
            blockers.append(f"exact_copied_runtime_triplet_missing_{role}")
            continue
        if not isinstance(event, dict):
            if selection.get("accepted") is True:
                blockers.append(f"exact_copied_runtime_triplet_{role}_not_selected")
            continue
        if event.get("approved_copy_shape_ok") is not True:
            blockers.append(f"exact_copied_runtime_triplet_{role}_shape_not_accepted")
        if event.get("inside_fresh_window") is not True:
            blockers.append(f"exact_copied_runtime_triplet_{role}_outside_fresh_window")

    rejected = selected_by_role.get("session_start_rejected")
    if isinstance(rejected, dict):
        required = REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]
        for key in ("target", "copied_bool_fields", "copied_bool_values"):
            if rejected.get(key) != required[key]:
                blockers.append(f"exact_copied_runtime_triplet_rejected_start_{key}_mismatch")
    if selection.get("status") != "selected":
        blockers.append("exact_copied_runtime_triplet_selection_status_not_exact")
    if selection.get("candidate_count") != 1:
        blockers.append("exact_copied_runtime_triplet_candidate_count_not_one")
    if selection.get("non_counting_context_event_count") != 0:
        blockers.append("exact_copied_runtime_triplet_non_counting_context_present")
    if selection.get("status") == "ambiguous":
        blockers.append("exact_copied_runtime_triplet_ambiguous")
    elif selection.get("accepted") is not True:
        blockers.append("exact_copied_runtime_triplet_not_selected")
    blockers.extend(
        f"exact_copied_runtime_triplet_{blocker}"
        for blocker in context_quality_blockers
    )

    order_blockers = triplet_order.get("blockers")
    if isinstance(order_blockers, list):
        blockers.extend(
            f"exact_copied_runtime_triplet_{blocker}"
            for blocker in order_blockers
            if isinstance(blocker, str)
        )

    start_end_only = (
        any(event.get("role") == "session_start" for event in accepted_events)
        and any(event.get("role") == "session_end" for event in accepted_events)
        and not any(event.get("role") == "session_start_rejected" for event in accepted_events)
    )
    return {
        "accepted": not blockers,
        "status": selection.get("status"),
        "blockers": blockers,
        "required_roles": list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER),
        "accepted_roles": accepted_roles,
        "missing_roles": missing_roles,
        "selected_indices": selection.get("selected_indices", []),
        "selected_sequences": selection.get("selected_sequences", []),
        "selected_lines": selection.get("selected_lines", []),
        "non_counting_context_event_count": selection.get("non_counting_context_event_count", 0),
        "non_counting_context_roles": selection.get("non_counting_context_roles", []),
        "candidate_count": selection.get("candidate_count", 0),
        "context_quality_blockers": context_quality_blockers,
        "required_rejected_start_shape": {
            "target": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["target"],
            "copied_bool_fields": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["copied_bool_fields"],
            "copied_bool_values": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["copied_bool_values"],
        },
        "start_end_only_detected": start_end_only,
        "copied_log_only_counts_as_approved_runtime_evidence": False,
        "copied_log_only_counts_as_runtime_evidence": False,
        "start_end_only_counts_as_approved_runtime_evidence": False,
        "start_end_only_counts_as_runtime_evidence": False,
        "passive_or_diagnostic_material_counts_as_approved_runtime_evidence": False,
    }


def timestamp_status(line: str) -> tuple[str, str | None, datetime | None]:
    timestamp_match = UTC_LOG_PREFIX_RE.match(line)
    if timestamp_match:
        prefix = timestamp_match.group("timestamp")
        return "utc", prefix, parse_utc_timestamp(prefix)
    prefix_match = ANY_LOG_PREFIX_RE.match(line)
    if prefix_match:
        return "not_utc", prefix_match.group("prefix"), None
    return "missing", None, None


def initial_analysis(
    args: argparse.Namespace,
    *,
    copy_readiness: str = "blocked_before_source_analysis",
) -> dict[str, Any]:
    return {
        "observer_enabled": False,
        "observer_enable_in_fresh_window": False,
        "binary_sha256_match": False,
        "roles_present": [],
        "missing_roles": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "lifecycle_triplet_order": {
            "status": "not_analyzed",
            "expected_roles": list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER),
            "observed_roles_by_line": [],
            "sequence_by_role": {},
            "timestamp_by_role": {},
            "blockers": [],
        },
        "exact_copied_runtime_triplet": {
            "accepted": False,
            "blockers": ["exact_copied_runtime_triplet_not_analyzed"],
            "required_roles": list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER),
            "accepted_roles": [],
            "missing_roles": list(EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER),
            "required_rejected_start_shape": {
                "target": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["target"],
                "copied_bool_fields": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["copied_bool_fields"],
                "copied_bool_values": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["copied_bool_values"],
            },
            "start_end_only_detected": False,
            "copied_log_only_counts_as_approved_runtime_evidence": False,
            "copied_log_only_counts_as_runtime_evidence": False,
            "start_end_only_counts_as_approved_runtime_evidence": False,
            "start_end_only_counts_as_runtime_evidence": False,
            "passive_or_diagnostic_material_counts_as_approved_runtime_evidence": False,
        },
        "ready_to_copy": False,
        "copy_readiness": copy_readiness,
        "historical_accepted_role_event_count": 0,
        "historical_accepted_role_events": [],
        "fresh_window": {
            "start_utc": args.fresh_window_start_utc,
            "end_utc": args.fresh_window_end_utc,
        },
        "timestamp_violation_count": 0,
        "timestamp_violations": [],
        "partial_accepted_lifecycle_role_set": False,
        "partial_accepted_lifecycle_roles_count_as_ready_to_copy": False,
        "partial_accepted_lifecycle_roles_count_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_ready_to_copy": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "copied_log_only_counts_as_approved_runtime_evidence": False,
        "copied_log_only_counts_as_runtime_evidence": False,
        "start_end_only_counts_as_approved_runtime_evidence": False,
        "start_end_only_counts_as_runtime_evidence": False,
    }


def analyze_log_text(
    text: str,
    expected_binary_sha256: str,
    *,
    fresh_window_start: datetime,
    fresh_window_end: datetime,
    fresh_window_start_utc: str,
    fresh_window_end_utc: str,
) -> dict[str, Any]:
    observer_enable_lines: list[dict[str, Any]] = []
    timestamp_violations: list[dict[str, Any]] = []
    events_by_role: dict[str, dict[str, Any]] = {}
    accepted_role_events: list[dict[str, Any]] = []
    duplicate_accepted_role_events: list[dict[str, Any]] = []
    rejected_events: list[dict[str, Any]] = []
    historical_roles: set[str] = set()
    historical_accepted_role_events: list[dict[str, Any]] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        kind = relevant_observer_line_kind(line)
        timestamp_state = "not_relevant"
        timestamp_prefix: str | None = None
        inside_fresh_window = False
        if kind is not None:
            timestamp_state, timestamp_prefix, observed_at = timestamp_status(line)
            inside_fresh_window = (
                timestamp_state == "utc"
                and observed_at is not None
                and fresh_window_start <= observed_at <= fresh_window_end
            )
            if timestamp_state != "utc":
                timestamp_violations.append(
                    {
                        "line_number": line_number,
                        "line_kind": kind,
                        "timestamp_status": timestamp_state,
                        "timestamp_prefix": timestamp_prefix,
                    }
                )

        enabled_match = OBSERVER_ENABLED_RE.search(line)
        if enabled_match:
            observer_enable_lines.append(
                {
                    "line_number": line_number,
                    "binary_sha256": enabled_match.group("sha").lower(),
                    "timestamp_status": timestamp_state,
                    "timestamp_prefix": timestamp_prefix,
                    "inside_fresh_window": inside_fresh_window,
                }
            )
        event_match = PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE.search(line)
        if not event_match:
            continue
        role = event_match.group("role")
        values = parse_key_values(line)
        required = REQUIRED_LIFECYCLE_EVENT_SHAPES[role]
        shape_mismatches = [
            key for key, expected in required.items() if values.get(key) != expected
        ]
        proof_ok = not shape_mismatches
        event_summary = {
            "role": role,
            "line_number": line_number,
            "sequence": int(event_match.group("sequence")),
            "target": values.get("target"),
            "post_original": values.get("post_original"),
            "copied_bool_fields": values.get("copied_bool_fields"),
            "copied_bool_values": values.get("copied_bool_values"),
            "redacted_count": values.get("redacted_count"),
            "redacted_fields": values.get("redacted_fields"),
            "principal_action": values.get("principal_action"),
            "apply_status": values.get("apply_status"),
            "correlation_status": values.get("correlation_status"),
            "principal_id_logged": values.get("principal_id_logged"),
            "principal_generation_logged": values.get("principal_generation_logged"),
            "delivery_claim": values.get("delivery_claim"),
            "status_proof_ok": proof_ok,
            "approved_copy_shape_ok": proof_ok,
            "approved_copy_shape_mismatches": shape_mismatches,
            "timestamp_status": timestamp_state,
            "timestamp_prefix": timestamp_prefix,
            "inside_fresh_window": inside_fresh_window,
        }
        if proof_ok and timestamp_state == "utc" and not inside_fresh_window:
            historical_roles.add(role)
            historical_accepted_role_events.append(simplified_lifecycle_event(event_summary))
            continue
        if proof_ok and timestamp_state == "utc" and inside_fresh_window:
            accepted_role_events.append(event_summary)
            if role not in events_by_role:
                events_by_role[role] = event_summary
            else:
                duplicate_accepted_role_events.append(event_summary)
            continue
        else:
            rejected_events.append(event_summary)

    roles_present = [
        role for role in REQUIRED_LIFECYCLE_EVENT_ROLES if role in events_by_role
    ]
    missing_roles = [
        role for role in REQUIRED_LIFECYCLE_EVENT_ROLES if role not in events_by_role
    ]
    observer_enabled = bool(observer_enable_lines)
    observer_enable_in_fresh_window = any(
        line["inside_fresh_window"] for line in observer_enable_lines
    )
    expected_sha = expected_binary_sha256.lower()
    binary_sha_match = any(
        line["inside_fresh_window"] and line["binary_sha256"] == expected_sha
        for line in observer_enable_lines
    )
    observer_sha = next(
        (
            line["binary_sha256"]
            for line in observer_enable_lines
            if line["inside_fresh_window"]
        ),
        observer_enable_lines[-1]["binary_sha256"] if observer_enable_lines else None,
    )
    missing_roles_with_historical_only = [
        role for role in missing_roles if role in historical_roles
    ]
    missing_roles_with_unapproved_shape = [
        role
        for role in missing_roles
        if any(
            event.get("role") == role
            and event.get("timestamp_status") == "utc"
            and event.get("inside_fresh_window") is True
            and event.get("approved_copy_shape_ok") is False
            for event in rejected_events
        )
    ]
    triplet_selection = strict_lifecycle_triplet_selection(accepted_role_events)
    triplet_order = selected_lifecycle_triplet_order_state(
        accepted_role_events,
        triplet_selection,
    )
    context_quality_blockers = accepted_lifecycle_context_quality_blockers(
        accepted_role_events,
    )
    exact_triplet = exact_copied_runtime_triplet_state(
        accepted_role_events,
        triplet_order,
        triplet_selection,
        context_quality_blockers,
    )
    triplet_order_mismatch = bool(
        triplet_order.get("blockers", [])
        or (
            exact_triplet.get("blockers")
            and exact_triplet.get("status") not in {"missing", "ambiguous"}
        )
    )
    ready_to_copy = (
        not timestamp_violations
        and observer_enabled
        and observer_enable_in_fresh_window
        and binary_sha_match
        and exact_triplet["accepted"]
        and not rejected_events
        and not historical_accepted_role_events
    )
    if ready_to_copy:
        copy_readiness = "ready_complete_role_triplet"
    elif timestamp_violations:
        copy_readiness = "blocked_observer_lifecycle_timestamp_not_utc"
    elif not observer_enabled:
        copy_readiness = "blocked_missing_observer_enable"
    elif missing_roles_with_historical_only:
        copy_readiness = "blocked_lifecycle_roles_outside_fresh_window"
    elif not observer_enable_in_fresh_window:
        copy_readiness = "blocked_observer_enable_outside_fresh_window"
    elif not binary_sha_match:
        copy_readiness = "blocked_binary_sha256_mismatch"
    elif exact_triplet.get("status") == "ambiguous":
        copy_readiness = "blocked_ambiguous_duplicate_lifecycle_roles"
    elif rejected_events:
        copy_readiness = "blocked_diagnostic_or_rejected_lifecycle_lines"
    elif historical_accepted_role_events:
        copy_readiness = "blocked_lifecycle_events_outside_fresh_window"
    elif triplet_order_mismatch:
        copy_readiness = "blocked_lifecycle_triplet_order_mismatch"
    else:
        copy_readiness = "blocked_missing_lifecycle_roles"
    duplicate_roles = [
        role
        for role in REQUIRED_LIFECYCLE_EVENT_ROLES
        if any(event["role"] == role for event in duplicate_accepted_role_events)
    ]
    partial_accepted_role_set = bool(roles_present) and bool(missing_roles)
    return {
        "observer_enabled": observer_enabled,
        "observer_enable_in_fresh_window": observer_enable_in_fresh_window,
        "observer_binary_sha256": observer_sha,
        "observer_enable_lines": observer_enable_lines,
        "expected_binary_sha256": expected_sha,
        "binary_sha256_match": binary_sha_match,
        "roles_present": roles_present,
        "missing_roles": missing_roles,
        "accepted_role_events": events_by_role,
        "accepted_lifecycle_event_count": len(accepted_role_events),
        "accepted_lifecycle_events": [
            simplified_lifecycle_event(event) for event in accepted_role_events
        ],
        "lifecycle_triplet_order": triplet_order,
        "exact_copied_runtime_triplet": exact_triplet,
        "duplicate_accepted_role_event_count": len(duplicate_accepted_role_events),
        "duplicate_accepted_roles": duplicate_roles,
        "duplicate_accepted_role_events": duplicate_accepted_role_events,
        "rejected_or_incomplete_role_event_count": len(rejected_events),
        "rejected_or_incomplete_role_events": rejected_events,
        "historical_roles_present": [
            role for role in REQUIRED_LIFECYCLE_EVENT_ROLES if role in historical_roles
        ],
        "historical_accepted_role_event_count": len(historical_accepted_role_events),
        "historical_accepted_role_events": historical_accepted_role_events,
        "missing_roles_with_historical_only": missing_roles_with_historical_only,
        "missing_roles_with_unapproved_shape": missing_roles_with_unapproved_shape,
        "timestamp_violation_count": len(timestamp_violations),
        "timestamp_violations": timestamp_violations,
        "fresh_window": {
            "start_utc": fresh_window_start_utc,
            "end_utc": fresh_window_end_utc,
        },
        "ready_to_copy": ready_to_copy,
        "copy_readiness": copy_readiness,
        "partial_accepted_lifecycle_role_set": partial_accepted_role_set,
        "partial_accepted_lifecycle_roles_count_as_ready_to_copy": False,
        "partial_accepted_lifecycle_roles_count_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_ready_to_copy": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "copied_log_only_counts_as_approved_runtime_evidence": False,
        "copied_log_only_counts_as_runtime_evidence": False,
        "start_end_only_counts_as_approved_runtime_evidence": False,
        "start_end_only_counts_as_runtime_evidence": False,
    }


def ready_log_evidence_split_state(
    analysis: dict[str, Any],
    source_log_safety: dict[str, Any],
) -> dict[str, Any]:
    exact_triplet = analysis.get("exact_copied_runtime_triplet", {})
    if not isinstance(exact_triplet, dict):
        exact_triplet = {}
    accepted_roles = [
        role
        for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
        if role in set(str(item) for item in analysis.get("roles_present", []))
    ]
    missing_exact_roles = [
        role
        for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
        if role in set(str(item) for item in exact_triplet.get("missing_roles", []))
    ]
    exact_blockers = [
        str(blocker)
        for blocker in exact_triplet.get("blockers", [])
        if isinstance(blocker, str)
    ]
    rejected_events = [
        event
        for event in analysis.get("rejected_or_incomplete_role_events", [])
        if isinstance(event, dict)
    ]
    rejected_event_summaries = [
        {
            "role": event.get("role"),
            "line_number": event.get("line_number"),
            "target": event.get("target"),
            "copied_bool_values": event.get("copied_bool_values"),
            "approved_copy_shape_mismatches": event.get("approved_copy_shape_mismatches", []),
            "timestamp_status": event.get("timestamp_status"),
            "inside_fresh_window": event.get("inside_fresh_window"),
        }
        for event in rejected_events[:10]
    ]
    rejected_start_candidates = [
        event
        for event in rejected_events
        if event.get("role") == "session_start_rejected"
    ]
    exact_check_join_blockers = {
        "exact_copied_runtime_triplet_missing_session_start_rejected",
        "exact_copied_runtime_triplet_rejected_start_target_mismatch",
        "exact_copied_runtime_triplet_rejected_start_copied_bool_fields_mismatch",
        "exact_copied_runtime_triplet_rejected_start_copied_bool_values_mismatch",
        "exact_copied_runtime_triplet_session_start_rejected_shape_not_accepted",
        "exact_copied_runtime_triplet_session_start_rejected_not_selected",
    }
    missing_exact_check_join = (
        "session_start_rejected" in missing_exact_roles
        or any(blocker in exact_check_join_blockers for blocker in exact_blockers)
    )
    diagnostic_lines = source_log_safety.get("lifecycle_diagnostic_lines", [])
    if not isinstance(diagnostic_lines, list):
        diagnostic_lines = []
    diagnostic_copy_rejected = [
        line
        for line in diagnostic_lines
        if isinstance(line, dict) and line.get("copy_status") == "rejected"
    ]
    check_join_candidates = [
        event
        for event in rejected_start_candidates
        if event.get("target") == REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["target"]
    ]
    check_join_diagnostics = [
        line
        for line in diagnostic_lines
        if isinstance(line, dict)
        and line.get("target") == REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["target"]
    ]
    unapproved_shape_roles = [
        role
        for role in EXPECTED_LIFECYCLE_EVENT_ROLE_ORDER
        if role in set(str(item) for item in analysis.get("missing_roles_with_unapproved_shape", []))
    ]
    if exact_triplet.get("accepted") is True:
        classification = "exact_triplet_present_copy_gate_ready"
    elif missing_exact_check_join and (check_join_candidates or check_join_diagnostics):
        classification = "check_join_in_progress_candidate_not_approved_exact_1_0"
    elif unapproved_shape_roles:
        classification = "observer_events_seen_but_shape_unapproved"
    elif exact_triplet.get("start_end_only_detected") is True:
        classification = "start_end_only_missing_exact_check_join_in_progress_1_0"
    elif accepted_roles:
        classification = "partial_accepted_lifecycle_roles"
    elif diagnostic_lines:
        classification = "diagnostic_only_no_accepted_lifecycle_roles"
    else:
        classification = str(analysis.get("copy_readiness", "blocked_before_source_analysis"))

    next_required_role = (
        "session_start_rejected"
        if missing_exact_check_join
        else missing_exact_roles[0]
        if missing_exact_roles
        else None
    )
    return {
        "schema": READY_LOG_EVIDENCE_SPLIT_SCHEMA,
        "classification": classification,
        "copy_readiness": analysis.get("copy_readiness"),
        "copy_gate_ready": bool(analysis.get("ready_to_copy")),
        "exact_triplet_accepted": exact_triplet.get("accepted") is True,
        "accepted_observer_event_count": int(analysis.get("accepted_lifecycle_event_count") or 0),
        "accepted_observer_event_roles": accepted_roles,
        "rejected_or_incomplete_observer_event_count": int(
            analysis.get("rejected_or_incomplete_role_event_count") or 0
        ),
        "rejected_or_incomplete_observer_events": rejected_event_summaries,
        "diagnostic_lifecycle_line_count": int(
            source_log_safety.get("lifecycle_diagnostic_line_count") or 0
        ),
        "diagnostic_lifecycle_lines": diagnostic_lines[:10],
        "diagnostic_copy_status_rejected_count": len(diagnostic_copy_rejected),
        "missing_exact_roles": missing_exact_roles,
        "missing_exact_check_join_in_progress_1_0": missing_exact_check_join,
        "check_join_in_progress_candidate_count": len(check_join_candidates)
        + len(check_join_diagnostics),
        "unapproved_shape_roles": unapproved_shape_roles,
        "exact_triplet_blockers": exact_blockers,
        "start_end_only_detected": exact_triplet.get("start_end_only_detected") is True,
        "next_required_role": next_required_role,
        "next_required_observer_event": (
            {
                "role": "session_start_rejected",
                "target": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"]["target"],
                "copied_bool_fields": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"][
                    "copied_bool_fields"
                ],
                "copied_bool_values": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"][
                    "copied_bool_values"
                ],
                "apply_status": REQUIRED_LIFECYCLE_EVENT_SHAPES["session_start_rejected"][
                    "apply_status"
                ],
            }
            if missing_exact_check_join
            else None
        ),
        "copy_ready_split_counts_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_material_counts_as_approved_runtime_evidence": False,
        "partial_roles_count_as_approved_runtime_evidence": False,
        "partial_roles_count_as_sdk_or_p0_progress": False,
    }


def write_json_report(report: dict[str, Any], args: argparse.Namespace) -> None:
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output is not None and str(args.json_output) != "-":
        output_state = report.get("json_output")
        if not isinstance(output_state, dict) or output_state.get("accepted") is not True:
            print(text)
            return
        resolved_path = output_state.get("resolved_path")
        output = Path(resolved_path) if isinstance(resolved_path, str) else args.json_output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    if args.json or args.json_output is None or str(args.json_output) == "-":
        print(text)
    elif args.json_output is not None:
        print(
            "player_principal_lifecycle_ready_log_copy_status="
            f"{report['status']} ready_to_copy={str(report['ready_to_copy']).lower()} "
            "approved_runtime_evidence=false"
        )


def copy_log(source: Path, target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    try:
        tmp.write_bytes(data)
        shutil.copystat(source, tmp, follow_symlinks=True)
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink()


def helper_argv(helper: Path) -> list[str]:
    if helper.suffix == ".py":
        return [sys.executable, str(helper)]
    return [str(helper)]


def load_json_sidecar(path: Path, *, label: str, blockers: list[str]) -> dict[str, Any] | None:
    status = path_status(path)
    if status.protected:
        blockers.append(f"{label}_under_protected_server_root:{status.resolved}")
        return None
    if not status.resolved.is_file():
        blockers.append(f"{label}_missing:{status.resolved}")
        return None
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        blockers.append(f"{label}_json_invalid:{status.resolved}")
        return None
    if not isinstance(payload, dict):
        blockers.append(f"{label}_not_object:{status.resolved}")
        return None
    return payload


def run_id_from_evidence_dir(evidence_dir: Path, blockers: list[str]) -> str | None:
    run_id = evidence_dir.name
    if RUN_ID_RE.fullmatch(run_id) is None:
        blockers.append(f"evidence_dir_run_id_invalid:{run_id}")
        return None
    parent = evidence_dir.parent.name
    if parent != "live-validation-logs":
        blockers.append(f"evidence_dir_not_live_validation_logs:{evidence_dir}")
    return run_id


def parse_request_context(
    evidence_dir: Path,
    *,
    expected_run_id: str | None,
    expected_instance: str | None = None,
    expected_window_start_utc: str | None = None,
    expected_window_end_utc: str | None = None,
    blockers: list[str],
) -> dict[str, Any] | None:
    payload = load_json_sidecar(evidence_dir / "window-request.json", label="window_request", blockers=blockers)
    if payload is None:
        return None
    target = payload.get("target")
    window = payload.get("approved_window")
    if payload.get("schema") != "obelisk.player-principal-lifecycle-window-request.v1":
        blockers.append("window_request_schema_mismatch")
    if expected_run_id is not None and payload.get("run_id") != expected_run_id:
        blockers.append("window_request_run_id_mismatch")
    if not isinstance(target, dict) or not isinstance(target.get("instance"), str) or not isinstance(target.get("map"), str):
        blockers.append("window_request_target_invalid")
        return None
    if expected_instance is not None and target.get("instance") != expected_instance:
        blockers.append("window_request_instance_mismatch")
    if not isinstance(window, dict):
        blockers.append("window_request_approved_window_invalid")
        return None
    for key in ("start_utc", "end_utc"):
        if parse_utc_timestamp(str(window.get(key))) is None:
            blockers.append(f"window_request_approved_window_{key}_invalid")
    if expected_window_start_utc is not None and window.get("start_utc") != expected_window_start_utc:
        blockers.append("window_request_approved_window_start_utc_mismatch")
    if expected_window_end_utc is not None and window.get("end_utc") != expected_window_end_utc:
        blockers.append("window_request_approved_window_end_utc_mismatch")

    path_expectations = {
        "copied_evidence_dir": evidence_dir,
        "copied_log_path": evidence_dir / "Obelisk.log",
        "window_manifest_path": evidence_dir / "window-manifest.env",
    }
    replay_sidecar_expectations = {
        "request_pack_path": evidence_dir / "window-request.json",
        "observer_env_path": evidence_dir / "observer-window.env",
        "operator_approval_request_path": evidence_dir / "operator-approval-request.md",
        "operator_approval_receipt_path": evidence_dir / "operator-approval-receipt.json",
        "preflight_pre_path": evidence_dir / "preflight-pre.json",
        "preflight_post_path": evidence_dir / "preflight-post.json",
        "window_manifest_path": evidence_dir / "window-manifest.env",
        "copied_log_path": evidence_dir / "Obelisk.log",
    }
    for key, expected_path in path_expectations.items():
        expected = str(
            protected_paths.protected_path_status(
                expected_path,
                protected_root=SERVER_ROOT,
                approved_roots=protected_paths.approved_offline_workspace_roots(),
            ).resolved
        )
        if payload.get(key) != expected:
            blockers.append(f"window_request_{key}_mismatch")
    replay_contract = payload.get("post_window_replay_contract")
    if isinstance(replay_contract, dict):
        sidecars = replay_contract.get("sidecars")
        if not isinstance(sidecars, dict):
            blockers.append("window_request_replay_contract_sidecars_missing")
        else:
            for key, expected_path in replay_sidecar_expectations.items():
                expected = str(
                    protected_paths.protected_path_status(
                        expected_path,
                        protected_root=SERVER_ROOT,
                        approved_roots=protected_paths.approved_offline_workspace_roots(),
                    ).resolved
                )
                if sidecars.get(key) != expected:
                    blockers.append(f"window_request_replay_contract_{key}_mismatch")
    return {
        "payload": payload,
        "instance": target["instance"],
        "map": target["map"],
        "run_id": payload.get("run_id"),
        "approved_window": window,
        "obelisk_commit": payload.get("obelisk_commit"),
        "approval": payload.get("approval_required"),
        "user_policy": payload.get("user_policy"),
    }


def bundle_command_metadata(
    args: argparse.Namespace,
    request: dict[str, Any] | None,
) -> dict[str, Any]:
    blockers: list[str] = []
    commit = request.get("obelisk_commit") if isinstance(request, dict) else None
    if not isinstance(commit, str) or not commit:
        blockers.append("bundle_command_obelisk_commit_from_request_missing")
        commit = "<window-manifest-obelisk_commit>"
    elif OBELISK_COMMIT_RE.fullmatch(commit) is None:
        blockers.append("bundle_command_obelisk_commit_from_request_invalid")

    reviewed_by = args.reviewed_by
    if not isinstance(reviewed_by, str) or not reviewed_by.strip():
        blockers.append("reviewed_by_required_for_direct_bundle_command")
        reviewed_by = "<reviewer>"

    review_note = args.review_note
    if not isinstance(review_note, str) or not review_note.strip():
        blockers.append("review_note_required_for_direct_bundle_command")
        review_note = "<consume-only-review-note>"

    return {
        "schema": "obelisk.player-principal-lifecycle-bundle-command-metadata.v1",
        "metadata_source": "window_request_bound_to_window_manifest"
        if not blockers
        else "missing_or_invalid_metadata",
        "obelisk_commit": commit,
        "reviewed_by": reviewed_by,
        "review_note": review_note,
        "metadata_resolved": not blockers,
        "blockers": blockers,
        "metadata_counts_as_approved_runtime_evidence": False,
        "metadata_counts_as_runtime_evidence": False,
        "metadata_counts_toward_sdk": False,
        "metadata_counts_toward_p0_dependency_chain": False,
    }


def preflight_false_flags() -> tuple[str, ...]:
    return (
        "server_operations_authorized",
        "runtime_work_authorized",
        "request_pack_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "runtime_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "promotion_ready",
        "public_header_allowed",
        "v1_completion_ready",
        "stable_claim_allowed",
        "route_ready",
    )


def validate_preflight_payload(
    payload: dict[str, Any] | None,
    *,
    label: str,
    expected_mode: str,
    request: dict[str, Any],
    evidence_dir: Path,
    copied_log: Path,
    expected_binary_sha256: str,
    blockers: list[str],
) -> dict[str, Any]:
    if payload is None:
        return {"accepted": False, "checked_at_utc": None, "blockers": [f"{label}_missing"]}
    local_blockers: list[str] = []
    run_id = request.get("run_id")
    expected_instance = request.get("instance")
    expected_map = request.get("map")
    manifest_path = evidence_dir / "window-manifest.env"
    expected_values: dict[str, Any] = {
        "schema": PREFLIGHT_SCHEMA,
        "ready": True,
        "mode": expected_mode,
        "run_id": run_id,
        "instance": expected_instance,
        "map": expected_map,
        "window_manifest_path": str(path_status(manifest_path).resolved),
        "copied_log_path": str(path_status(copied_log).resolved),
        "copied_evidence_dir": str(path_status(evidence_dir).resolved),
        "posture_check": "accepted",
        "offline_only": False,
        "allow_stopped": False,
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            local_blockers.append(f"{label}_{key}_mismatch")
    target = payload.get("target")
    if not isinstance(target, dict):
        local_blockers.append(f"{label}_target_missing")
    else:
        if target.get("instance") != expected_instance:
            local_blockers.append(f"{label}_target_instance_mismatch")
        if target.get("map") != expected_map:
            local_blockers.append(f"{label}_target_map_mismatch")
    checked_at_utc = payload.get("checked_at_utc")
    if not isinstance(checked_at_utc, str) or parse_utc_timestamp(checked_at_utc) is None:
        local_blockers.append(f"{label}_checked_at_utc_invalid")
    server_binary = payload.get("server_binary")
    if not isinstance(server_binary, dict) or server_binary.get("sha256") != expected_binary_sha256:
        local_blockers.append(f"{label}_binary_sha256_mismatch")
    elif server_binary.get("path") != EXPECTED_SERVER_BINARY_PATH:
        local_blockers.append(f"{label}_binary_path_mismatch")
    for key in preflight_false_flags():
        if payload.get(key) is not False:
            local_blockers.append(f"{label}_{key}_not_false")
    if payload.get("non_claim") != EXPECTED_PREFLIGHT_NON_CLAIM:
        local_blockers.append(f"{label}_non_claim_mismatch")
    blockers.extend(local_blockers)
    return {
        "accepted": not local_blockers,
        "checked_at_utc": checked_at_utc if isinstance(checked_at_utc, str) else None,
        "blockers": local_blockers,
    }


def window_manifest_check_false_flags() -> tuple[str, ...]:
    return (
        "server_operations_authorized",
        "runtime_work_authorized",
        "promotion_ready",
        "public_header_allowed",
        "public_sdk_ready",
        "public_abi_ready",
        "v1_completion_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "request_pack_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "route_ready",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
    )


def window_manifest_check_machine_false_flags() -> tuple[str, ...]:
    return (
        "authorized_by_this_report",
        "server_operations_authorized",
        "runtime_work_authorized",
        "discord_authorized",
        "marker_env_changes_authorized",
        "runtime_capture_authorized",
        "approved_runtime_evidence",
        "approved_runtime_evidence_ready",
        "public_sdk_ready",
        "v1_completion_ready",
    )


def validate_window_manifest_check_report(
    report: dict[str, Any] | None,
    *,
    result_returncode: int,
) -> list[str]:
    if report is None:
        return ["window_manifest_check_json_invalid"]
    blockers: list[str] = []
    if result_returncode != 0:
        blockers.append(f"window_manifest_check_failed:{result_returncode}")
    if report.get("schema") != WINDOW_MANIFEST_CHECK_SCHEMA:
        blockers.append("window_manifest_check_schema_mismatch")
    if report.get("ready") is not True or report.get("operational_window_manifest_ready") is not True:
        blockers.append("window_manifest_check_not_ready")
    for key in window_manifest_check_false_flags():
        if report.get(key) is not False:
            blockers.append(f"window_manifest_check_{key}_not_false")

    machine_next_step = report.get("machine_next_step")
    if not isinstance(machine_next_step, dict):
        blockers.append("window_manifest_check_machine_next_step_missing")
    else:
        for key in window_manifest_check_machine_false_flags():
            if machine_next_step.get(key) is not False:
                blockers.append(f"window_manifest_check_machine_next_step_{key}_not_false")

    if report.get("next_blocker") != EXPECTED_WINDOW_MANIFEST_NEXT_BLOCKER:
        blockers.append("window_manifest_check_next_blocker_not_evidence_bundle_blocker")
    if report.get("next_required_artifact") != EXPECTED_WINDOW_MANIFEST_NEXT_REQUIRED_ARTIFACT:
        blockers.append("window_manifest_check_next_required_artifact_not_evidence_bundle")
    if report.get("required_artifact_status") != EXPECTED_WINDOW_MANIFEST_REQUIRED_ARTIFACT_STATUS:
        blockers.append("window_manifest_check_required_artifact_status_not_missing")

    claims = report.get("claims")
    if not isinstance(claims, dict):
        blockers.append("window_manifest_check_claims_missing")
    else:
        if claims.get("delivery_claim") != "none":
            blockers.append("window_manifest_check_delivery_claim_not_none")
        if claims.get("principal_claim") != "none":
            blockers.append("window_manifest_check_principal_claim_not_none")

    non_claims = report.get("non_claims")
    if not isinstance(non_claims, list) or any(claim not in non_claims for claim in EXPECTED_WINDOW_MANIFEST_NON_CLAIMS):
        blockers.append("window_manifest_check_non_claims_mismatch")
    return blockers


def max_accepted_event_timestamp(analysis: dict[str, Any]) -> str | None:
    parsed: list[datetime] = []
    events: list[Any] = []
    accepted_lifecycle_events = analysis.get("accepted_lifecycle_events")
    if isinstance(accepted_lifecycle_events, list):
        events.extend(accepted_lifecycle_events)
    accepted_role_events = analysis.get("accepted_role_events")
    if isinstance(accepted_role_events, dict):
        events.extend(accepted_role_events.values())
    if not events:
        return None
    for event in events:
        if not isinstance(event, dict):
            continue
        timestamp = event.get("timestamp_prefix")
        if not isinstance(timestamp, str):
            continue
        parsed_timestamp = parse_utc_timestamp(timestamp)
        if parsed_timestamp is not None:
            parsed.append(parsed_timestamp)
    if not parsed:
        return None
    return max(parsed).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_post_preflight(
    args: argparse.Namespace,
    *,
    request: dict[str, Any],
    evidence_dir: Path,
    copied_log: Path,
    blockers: list[str],
) -> dict[str, Any] | None:
    output = evidence_dir / "preflight-post.json"
    if not args.allow_post_window_preflight_live_read:
        blockers.append("post_window_preflight_live_read_requires_explicit_flag")
        return None
    command = [
        *helper_argv(args.preflight_helper),
        "--instance",
        str(request["instance"]),
        "--map",
        str(request["map"]),
        "--mode",
        "stable",
        "--expected-binary-sha256",
        args.expected_binary_sha256,
        "--run-id",
        str(request["run_id"]),
        "--window-manifest",
        str(evidence_dir / "window-manifest.env"),
        "--copied-log",
        str(copied_log),
        "--evidence-dir",
        str(evidence_dir),
        "--allow-live-procfs-read",
        "--allow-protected-root",
        "--json",
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        blockers.append(f"preflight_post_helper_failed:{result.returncode}")
        return {
            "path": str(output),
            "command": command,
            "returncode": result.returncode,
            "stderr": result.stderr,
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        blockers.append("preflight_post_helper_json_invalid")
        return {
            "path": str(output),
            "command": command,
            "returncode": result.returncode,
            "stderr": result.stderr,
        }
    if not isinstance(payload, dict):
        blockers.append("preflight_post_helper_json_not_object")
        return {
            "path": str(output),
            "command": command,
            "returncode": result.returncode,
            "stderr": result.stderr,
        }
    tmp = output.with_name(f".{output.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(output)
    validation = validate_preflight_payload(
        payload,
        label="preflight_post",
        expected_mode="stable",
        request=request,
        evidence_dir=evidence_dir,
        copied_log=copied_log,
        expected_binary_sha256=args.expected_binary_sha256,
        blockers=blockers,
    )
    return {
        "path": str(output),
        "command": command,
        "returncode": result.returncode,
        "accepted": validation["accepted"],
        "checked_at_utc": validation["checked_at_utc"],
        "blockers": validation["blockers"],
    }


def write_window_manifest(
    *,
    evidence_dir: Path,
    copied_log: Path,
    request: dict[str, Any],
    analysis: dict[str, Any],
    preflight_pre: dict[str, Any],
    preflight_post: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    manifest = evidence_dir / "window-manifest.env"
    capture_start = preflight_pre.get("checked_at_utc")
    capture_end = max_accepted_event_timestamp(analysis)
    rollback_at = preflight_post.get("checked_at_utc")
    if not isinstance(capture_start, str):
        blockers.append("window_manifest_capture_start_missing")
    if not isinstance(capture_end, str):
        blockers.append("window_manifest_capture_end_missing")
    if not isinstance(rollback_at, str):
        blockers.append("window_manifest_rollback_timestamp_missing")
    if not isinstance(capture_start, str) or not isinstance(capture_end, str) or not isinstance(rollback_at, str):
        return {"path": str(manifest), "written": False}

    window = request["approved_window"]
    user_policy = request.get("user_policy")
    fields = {
        "run_id": str(request["run_id"]),
        "obelisk_commit": str(request.get("obelisk_commit") or ""),
        "target": f"{request['instance']}/{request['map']}",
        "approval": str(request.get("approval") or ""),
        "approved_window_start_utc": str(window.get("start_utc") or ""),
        "approved_window_end_utc": str(window.get("end_utc") or ""),
        "actual_capture_start_utc": capture_start,
        "actual_capture_end_utc": capture_end,
        "copied_log_path": str(copied_log),
        "copied_log_sha256": sha256_file(copied_log),
        "request_pack_path": str(evidence_dir / "window-request.json"),
        "request_pack_sha256": sha256_file(evidence_dir / "window-request.json"),
        "observer_env_path": str(evidence_dir / "observer-window.env"),
        "observer_env_sha256": sha256_file(evidence_dir / "observer-window.env"),
        "operator_approval_receipt_path": str(evidence_dir / "operator-approval-receipt.json"),
        "operator_approval_receipt_sha256": sha256_file(evidence_dir / "operator-approval-receipt.json"),
        "preflight_pre_path": str(evidence_dir / "preflight-pre.json"),
        "preflight_pre_sha256": sha256_file(evidence_dir / "preflight-pre.json"),
        "preflight_post_path": str(evidence_dir / "preflight-post.json"),
        "preflight_post_sha256": sha256_file(evidence_dir / "preflight-post.json"),
        "pre_posture": "stable",
        "post_posture": "stable",
        "pre_check": "passed",
        "post_check": "passed",
        "rollback_start_utc": rollback_at,
        "rollback_end_utc": rollback_at,
        "rollback_completed": "true",
        "rollback_delta": EXPECTED_ROLLBACK_DELTA,
        "observer_env_survived": "false",
        "observer_marker_survived": "false",
        "sibling_marker_entries": "absent",
        "sibling_observer_env": "absent",
        "user_policy": str(user_policy or ""),
        "notice_sent": "true" if user_policy == "operator_approved_beta_users" else "not_applicable",
        "log_budget": "10",
        "plugins_disabled": "true",
        "scanner_disabled": "true",
        "dispatch_limit": "0",
        "wrapper_profile": "observer-debug",
        "observer_exclusivity": "player_principal_lifecycle_only",
        "debug_escape_markers": "absent",
        "callback_escape_markers": "absent",
        "native_exec_disabled": "true",
        "ptrace_disabled": "true",
        "single_module_summary": "player_principal_lifecycle",
        "delivery_claim": "none",
        "principal_claim": "none",
    }
    tmp = manifest.with_name(f".{manifest.name}.tmp.{os.getpid()}")
    tmp.write_text(
        "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
        encoding="utf-8",
    )
    tmp.replace(manifest)
    return {
        "path": str(manifest),
        "written": True,
        "sha256": sha256_file(manifest),
    }


def check_window_manifest(
    args: argparse.Namespace,
    *,
    manifest: Path,
    blockers: list[str],
) -> dict[str, Any]:
    command = [
        *helper_argv(args.window_manifest_helper),
        "--json",
        "--post-window-replay",
        str(manifest),
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    report: dict[str, Any] | None = None
    if result.stdout:
        try:
            loaded = json.loads(result.stdout)
            if isinstance(loaded, dict):
                report = loaded
        except json.JSONDecodeError:
            report = None
    local_blockers = validate_window_manifest_check_report(
        report,
        result_returncode=result.returncode,
    )
    blockers.extend(local_blockers)
    return {
        "command": command,
        "returncode": result.returncode,
        "ready": bool(
            report
            and report.get("ready") is True
            and report.get("operational_window_manifest_ready") is True
            and result.returncode == 0
            and not local_blockers
        ),
        "blockers": local_blockers,
        "checker_report_blockers": report.get("blockers", []) if isinstance(report, dict) else [],
        "report_false_flags": {
            key: report.get(key) if isinstance(report, dict) else None
            for key in window_manifest_check_false_flags()
        },
        "machine_next_step_false_flags": {
            key: report.get("machine_next_step", {}).get(key)
            if isinstance(report, dict) and isinstance(report.get("machine_next_step"), dict)
            else None
            for key in window_manifest_check_machine_false_flags()
        },
        "report_next_blocker": report.get("next_blocker") if isinstance(report, dict) else None,
        "report_next_required_artifact": report.get("next_required_artifact") if isinstance(report, dict) else None,
        "report_required_artifact_status": report.get("required_artifact_status") if isinstance(report, dict) else None,
        "report_non_claims": report.get("non_claims") if isinstance(report, dict) else None,
        "stderr": result.stderr,
    }


def next_action_commands(
    args: argparse.Namespace,
    *,
    source_path: Path,
    evidence_dir: Path,
    target_log: Path,
    request: dict[str, Any] | None,
    ready_to_copy: bool,
    copied: bool,
    post_window_sidecars: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    ready_log_copy_json = evidence_dir / READY_LOG_COPY_REPORT_NAME
    approved_bundle_dir = evidence_dir / "approved-bundle"
    approved_manifest = approved_bundle_dir / "approved-runtime-principal-lifecycle-evidence.json"
    summary_path = approved_bundle_dir / "runtime-observer-summary.json"
    window_manifest_check_path = (
        approved_bundle_dir / "player-principal-lifecycle-window-manifest.check.json"
    )
    copy_command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "copy_player_principal_lifecycle_ready_log.py"),
        "--instance",
        args.instance,
        "--source-log",
        str(source_path),
        "--evidence-dir",
        str(evidence_dir),
        "--fresh-window-start-utc",
        str(args.fresh_window_start_utc or "<fresh-window-start-utc>"),
        "--fresh-window-end-utc",
        str(args.fresh_window_end_utc or "<fresh-window-end-utc>"),
        "--execute",
        "--allow-evidence-dir-write",
        "--allow-post-window-sidecar-generation",
        "--allow-post-window-preflight-live-read",
        "--reviewed-by",
        str(args.reviewed_by),
        "--review-note",
        str(args.review_note),
        "--json-output",
        str(ready_log_copy_json),
    ]
    if args.allow_live_log_read:
        copy_command.append("--allow-live-log-read")
    if args.overwrite:
        copy_command.append("--overwrite")
    if args.preflight_helper != DEFAULT_PREFLIGHT_HELPER:
        copy_command.extend(["--preflight-helper", str(args.preflight_helper)])
    if args.window_manifest_helper != DEFAULT_WINDOW_MANIFEST_HELPER:
        copy_command.extend(["--window-manifest-helper", str(args.window_manifest_helper)])

    build_blockers: list[str] = []

    def add_build_blocker(blocker: object) -> None:
        blocker_text = str(blocker)
        if blocker_text and blocker_text not in build_blockers:
            build_blockers.append(blocker_text)

    if not copied:
        add_build_blocker("copied_log_not_written")
    if not post_window_sidecars.get("ready"):
        add_build_blocker("post_window_sidecars_not_ready")
    for blocker in post_window_sidecars.get("blockers", []):
        add_build_blocker(blocker)
    for blocker in blockers:
        add_build_blocker(blocker)
    metadata = bundle_command_metadata(args, request)
    for blocker in metadata["blockers"]:
        add_build_blocker(blocker)
    build_available = bool(copied and post_window_sidecars.get("ready") and not build_blockers)
    analyzer_command = [
        sys.executable,
        str(REPO_ROOT / RUNTIME_OBSERVER_ANALYZER),
        "--obelisk-commit",
        str(metadata["obelisk_commit"]),
        "--fail-on-quality-blockers",
        str(target_log),
    ]
    strict_selector_command = [
        sys.executable,
        str(REPO_ROOT / APPROVED_RUNTIME_MANIFEST_BUILDER),
        "--source-summary",
        str(summary_path),
        "--window-manifest-check",
        str(window_manifest_check_path),
        "--output",
        str(approved_manifest),
        "--reviewed-by",
        str(metadata["reviewed_by"]),
        "--review-note",
        str(metadata["review_note"]),
    ]
    direct_bundle_command = [
        sys.executable,
        str(REPO_ROOT / APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER),
        "--copied-log",
        str(target_log),
        "--window-manifest",
        str(evidence_dir / "window-manifest.env"),
        "--output-dir",
        str(approved_bundle_dir),
        "--obelisk-commit",
        str(metadata["obelisk_commit"]),
        "--reviewed-by",
        str(metadata["reviewed_by"]),
        "--review-note",
        str(metadata["review_note"]),
    ]
    bundle_preflight_command = [
        sys.executable,
        str(REPO_ROOT / APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER),
        "--preflight-only",
        "--evidence-dir",
        str(evidence_dir),
    ]
    checker_command = [
        sys.executable,
        str(REPO_ROOT / APPROVED_RUNTIME_EVIDENCE_CHECKER),
        "--json",
        str(approved_manifest),
    ]
    evidence_pipeline_command_sequence = {
        "schema": "obelisk.player-principal-lifecycle-evidence-command-sequence.v1",
        "status": "not_executed",
        "ordered_step_ids": [
            "analyze_runtime_observer_log",
            "strict_lifecycle_triplet_selector",
            "bundle_preflight",
            "approved_runtime_evidence_checker",
        ],
        "commands": [
            {
                "order": 1,
                "id": "analyze_runtime_observer_log",
                "kind": "analyzer",
                "argv": analyzer_command,
                "stdout_path": str(summary_path),
                "command_text_not_executed": f"{shlex.join(analyzer_command)} > {shlex.quote(str(summary_path))}",
            },
            {
                "order": 2,
                "id": "strict_lifecycle_triplet_selector",
                "kind": "strict_selector",
                "argv": strict_selector_command,
                "command_text_not_executed": shlex.join(strict_selector_command),
                "requires_window_manifest_check": str(window_manifest_check_path),
                "required_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
            },
            {
                "order": 3,
                "id": "bundle_preflight",
                "kind": "preflight",
                "argv": bundle_preflight_command,
                "command_text_not_executed": shlex.join(bundle_preflight_command),
            },
            {
                "order": 4,
                "id": "approved_runtime_evidence_checker",
                "kind": "checker",
                "argv": checker_command,
                "command_text_not_executed": shlex.join(checker_command),
                "manifest": str(approved_manifest),
            },
        ],
        "available_after_copy_and_sidecars": build_available,
        "blockers": build_blockers,
        "bundle_command_metadata": metadata,
        "direct_bundle_builder_command_available": build_available,
        "direct_bundle_builder_command": {
            "argv": direct_bundle_command,
            "command_text_not_executed": shlex.join(direct_bundle_command),
            "execution_mode": "no_shell_offline_helper",
            "writes_under_evidence_dir": True,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        }
        if build_available
        else None,
        "restart_policy": "no_restart_unless_concrete_deploy_or_gate_change_requires_it",
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "authorization": {
            "server_operations_authorized_by_this_report": False,
            "runtime_capture_authorized_by_this_report": False,
            "marker_env_changes_authorized_by_this_report": False,
            "discord_sent_by_this_report": False,
        },
        "evidence": {
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
        },
        "non_authorization": (
            "ordered commands are offline follow-up guidance only; this report does not "
            "authorize server operations, restarts, live-log reads, Discord sends, "
            "marker/env changes, evidence acceptance, SDK progress, or readiness claims"
        ),
    }

    return {
        "schema": "obelisk.player-principal-lifecycle-ready-log-copy-next-actions.v1",
        "status_report_only": True,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_complete_sdk_claim_now": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim_now": False,
        "server_operations_authorized_by_this_report": False,
        "discord_sent_by_this_report": False,
        "marker_env_changes_authorized_by_this_report": False,
        "copy_ready_execute": {
            "available": bool(ready_to_copy and not copied),
            "command": copy_command,
            "json_output": str(ready_log_copy_json),
            "blockers": [] if ready_to_copy and not copied else list(blockers),
        },
        "bundle_preflight": {
            "available": True,
            "command": [
                sys.executable,
                str(REPO_ROOT / APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER),
                "--preflight-only",
                "--evidence-dir",
                str(evidence_dir),
            ],
            "non_claim": "classifies the sibling set only; it does not approve evidence",
        },
        "build_approved_bundle": {
            "available": build_available,
            "command": direct_bundle_command if build_available else None,
            "command_template": direct_bundle_command,
            "command_metadata_resolved": bool(metadata["metadata_resolved"]),
            "bundle_command_metadata": metadata,
            "blockers": build_blockers,
        },
        "check_approved_bundle": {
            "available": build_available,
            "command_template": [
                sys.executable,
                str(REPO_ROOT / APPROVED_RUNTIME_EVIDENCE_CHECKER),
                str(approved_manifest),
                "--json",
            ],
            "manifest": str(approved_manifest),
            "blockers": build_blockers,
        },
        "evidence_pipeline_command_sequence": evidence_pipeline_command_sequence,
        "ordered_runtime_evidence_commands": evidence_pipeline_command_sequence["commands"],
        "non_claim": (
            "next-action commands are operational guidance only; they do not authorize "
            "server work, Discord, marker/env changes, runtime capture, approved runtime "
            "evidence, SDK/P0 progress, public readiness, stable readiness, Plugin Hub, "
            "or publication"
        ),
    }


def generate_post_window_sidecars(
    args: argparse.Namespace,
    *,
    evidence_dir: Path,
    target_log: Path,
    analysis: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    sidecar_report: dict[str, Any] = {
        "requested": args.allow_post_window_sidecar_generation,
        **FALSE_FLAGS,
        "exact_copied_runtime_triplet": analysis.get(
            "exact_copied_runtime_triplet",
            initial_analysis(args)["exact_copied_runtime_triplet"],
        ),
        "preflight_pre": {"path": str(evidence_dir / "preflight-pre.json"), "accepted": False},
        "preflight_post": {"path": str(evidence_dir / "preflight-post.json"), "accepted": False},
        "window_manifest": {"path": str(evidence_dir / "window-manifest.env"), "written": False},
        "window_manifest_check": {"ready": False},
        "blockers": [],
    }
    exact_triplet = sidecar_report["exact_copied_runtime_triplet"]
    if not isinstance(exact_triplet, dict) or exact_triplet.get("accepted") is not True:
        exact_blockers = (
            exact_triplet.get("blockers", ["exact_copied_runtime_triplet_missing"])
            if isinstance(exact_triplet, dict)
            else ["exact_copied_runtime_triplet_missing"]
        )
        blockers.extend(str(blocker) for blocker in exact_blockers)
        sidecar_report["blockers"] = list(blockers)
        return sidecar_report
    if not args.allow_post_window_sidecar_generation:
        blockers.append("post_window_sidecar_generation_requires_explicit_flag")
        sidecar_report["blockers"].append("post_window_sidecar_generation_requires_explicit_flag")
        return sidecar_report
    run_id = run_id_from_evidence_dir(evidence_dir, blockers)
    request = parse_request_context(
        evidence_dir,
        expected_run_id=run_id,
        expected_instance=args.instance,
        expected_window_start_utc=args.fresh_window_start_utc,
        expected_window_end_utc=args.fresh_window_end_utc,
        blockers=blockers,
    )
    if request is None:
        sidecar_report["blockers"] = list(blockers)
        return sidecar_report
    for required_name in (
        "observer-window.env",
        "operator-approval-request.md",
        "operator-approval-receipt.json",
    ):
        required_path = evidence_dir / required_name
        if not required_path.is_file():
            blockers.append(f"{required_name}_missing:{required_path}")
    preflight_pre_payload = load_json_sidecar(
        evidence_dir / "preflight-pre.json",
        label="preflight_pre",
        blockers=blockers,
    )
    preflight_pre = validate_preflight_payload(
        preflight_pre_payload,
        label="preflight_pre",
        expected_mode="observer-window",
        request=request,
        evidence_dir=evidence_dir,
        copied_log=target_log,
        expected_binary_sha256=args.expected_binary_sha256,
        blockers=blockers,
    )
    sidecar_report["preflight_pre"].update(preflight_pre)
    if blockers:
        sidecar_report["blockers"] = list(blockers)
        return sidecar_report
    preflight_post = run_post_preflight(
        args,
        request=request,
        evidence_dir=evidence_dir,
        copied_log=target_log,
        blockers=blockers,
    )
    if preflight_post is not None:
        sidecar_report["preflight_post"].update(preflight_post)
    if blockers:
        sidecar_report["blockers"] = list(blockers)
        return sidecar_report
    preflight_post_payload = load_json_sidecar(
        evidence_dir / "preflight-post.json",
        label="preflight_post",
        blockers=blockers,
    )
    preflight_post_validation = validate_preflight_payload(
        preflight_post_payload,
        label="preflight_post",
        expected_mode="stable",
        request=request,
        evidence_dir=evidence_dir,
        copied_log=target_log,
        expected_binary_sha256=args.expected_binary_sha256,
        blockers=blockers,
    )
    sidecar_report["preflight_post"].update(preflight_post_validation)
    if blockers:
        sidecar_report["blockers"] = list(blockers)
        return sidecar_report
    manifest_state = write_window_manifest(
        evidence_dir=evidence_dir,
        copied_log=target_log,
        request=request,
        analysis=analysis,
        preflight_pre=preflight_pre,
        preflight_post=preflight_post_validation,
        blockers=blockers,
    )
    sidecar_report["window_manifest"].update(manifest_state)
    if blockers:
        sidecar_report["blockers"] = list(blockers)
        return sidecar_report
    manifest_check = check_window_manifest(
        args,
        manifest=evidence_dir / "window-manifest.env",
        blockers=blockers,
    )
    sidecar_report["window_manifest_check"].update(manifest_check)
    sidecar_report["blockers"] = list(blockers)
    return sidecar_report


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    source = args.source_log or default_source_log(args.instance)
    source_path, blockers = resolve_source(source, allow_live_log_read=args.allow_live_log_read)
    evidence_dir, evidence_blockers = resolve_evidence_dir(args.evidence_dir)
    blockers.extend(evidence_blockers)
    json_output = validate_json_output_path(args, evidence_dir)
    deferred_output_blockers = list(json_output["blockers"])
    fresh_window_start, fresh_window_end, fresh_window_blockers = parse_fresh_window(args)
    blockers.extend(fresh_window_blockers)
    now_utc = parse_utc_timestamp(args.now_utc) if isinstance(args.now_utc, str) else None
    if args.now_utc and now_utc is None:
        blockers.append("now_utc_invalid")
    target = evidence_dir / "Obelisk.log"
    target_status = path_status(target)
    if target_status.protected:
        blockers.append(f"target_under_protected_server_root:{target_status.resolved}")

    data = b""
    window_readiness = (
        "blocked_missing_fresh_window"
        if any(blocker.endswith("_required") for blocker in fresh_window_blockers)
        else "blocked_invalid_fresh_window"
        if fresh_window_blockers
        else "blocked_before_source_analysis"
    )
    analysis: dict[str, Any] = initial_analysis(args, copy_readiness=window_readiness)
    source_log_safety: dict[str, Any] = copied_log_safety_state("")
    source_input: dict[str, Any] = source_input_state("")
    if not blockers:
        data = source_path.read_bytes()
        log_text = data.decode("utf-8", errors="replace")
        source_input = source_input_state(log_text)
        source_log_safety = copied_log_safety_state(log_text)
        blockers.extend(source_input["blockers"])
        blockers.extend(source_log_safety["blockers"])
        if source_input["accepted"]:
            analysis = analyze_log_text(
                log_text,
                args.expected_binary_sha256,
                fresh_window_start=fresh_window_start,
                fresh_window_end=fresh_window_end,
                fresh_window_start_utc=args.fresh_window_start_utc,
                fresh_window_end_utc=args.fresh_window_end_utc,
            )
            if not analysis["ready_to_copy"]:
                blockers.append(str(analysis["copy_readiness"]))
                exact_blockers = analysis.get("exact_copied_runtime_triplet", {}).get("blockers", [])
                if isinstance(exact_blockers, list):
                    blockers.extend(str(blocker) for blocker in exact_blockers)

    blockers.extend(deferred_output_blockers)

    existing_target_sha: str | None = None
    if target_status.resolved.exists():
        existing_target_sha = sha256_file(target_status.resolved)
        source_sha = sha256_bytes(data) if data else None
        if source_sha == existing_target_sha:
            blockers.append("target_obelisk_log_already_present_same_sha")
        elif not args.overwrite:
            blockers.append(f"target_obelisk_log_already_exists:{target_status.resolved}")

    if args.execute and not args.allow_evidence_dir_write:
        blockers.append("evidence_dir_write_requires_explicit_flag")

    request_context: dict[str, Any] | None = None
    sidecar_precheck: dict[str, Any] = {
        "required_for_execute": True,
        "accepted": False,
        "blockers": [],
    }
    if args.execute and not blockers:
        precheck_blockers: list[str] = []
        if not args.allow_post_window_sidecar_generation:
            precheck_blockers.append("post_window_sidecar_generation_requires_explicit_flag")
        if not path_status(evidence_dir).approved_offline_workspace:
            precheck_blockers.append("evidence_dir_not_approved_offline_workspace_for_post_window_sidecars")
        run_id = run_id_from_evidence_dir(evidence_dir, precheck_blockers)
        request = parse_request_context(
            evidence_dir,
            expected_run_id=run_id,
            expected_instance=args.instance,
            expected_window_start_utc=args.fresh_window_start_utc,
            expected_window_end_utc=args.fresh_window_end_utc,
            blockers=precheck_blockers,
        )
        if request is not None:
            request_context = request
            for required_name in (
                "observer-window.env",
                "operator-approval-request.md",
                "operator-approval-receipt.json",
            ):
                required_path = evidence_dir / required_name
                if not required_path.is_file():
                    precheck_blockers.append(f"{required_name}_missing:{required_path}")
            preflight_pre_payload = load_json_sidecar(
                evidence_dir / "preflight-pre.json",
                label="preflight_pre",
                blockers=precheck_blockers,
            )
            validate_preflight_payload(
                preflight_pre_payload,
                label="preflight_pre",
                expected_mode="observer-window",
                request=request,
                evidence_dir=evidence_dir,
                copied_log=target_status.resolved,
                expected_binary_sha256=args.expected_binary_sha256,
                blockers=precheck_blockers,
            )
        blockers.extend(precheck_blockers)
        sidecar_precheck = {
            "required_for_execute": True,
            "accepted": not precheck_blockers,
            "blockers": precheck_blockers,
        }

    copied = False
    post_window_sidecars: dict[str, Any] = {
        "requested": args.allow_post_window_sidecar_generation,
        **FALSE_FLAGS,
        "exact_copied_runtime_triplet": analysis.get("exact_copied_runtime_triplet"),
        "ready": False,
        "blockers": [],
    }
    if args.execute and not blockers:
        copy_log(source_path, target_status.resolved, data)
        copied = True
        post_window_sidecars = generate_post_window_sidecars(
            args,
            evidence_dir=evidence_dir,
            target_log=target_status.resolved,
            analysis=analysis,
            blockers=blockers,
        )
        post_window_sidecars["ready"] = (
            bool(post_window_sidecars.get("window_manifest", {}).get("written"))
            and bool(post_window_sidecars.get("window_manifest_check", {}).get("ready"))
            and not post_window_sidecars.get("blockers")
        )

    ready_to_copy = bool(analysis.get("ready_to_copy")) and not any(
        blocker.startswith("live_log_read_requires")
        or blocker.startswith("source_log_missing")
        or blocker.startswith("evidence_dir_")
        or blocker.startswith("target_under_")
        for blocker in blockers
    )
    source_log_not_ready = observer_only_no_role_window_state(
        args.instance,
        analysis,
        player_presence_context=source_log_safety.get("player_presence_context", {}),
        now=now_utc,
    )
    for source_blocker in source_log_not_ready.get("blockers", []):
        if source_blocker == "player_present_but_no_lifecycle_roles" and source_blocker not in blockers:
            blockers.append(source_blocker)
    ready_log_evidence_split = ready_log_evidence_split_state(analysis, source_log_safety)
    artifact_bindings = copied_artifact_binding_report(evidence_dir)
    return {
        "schema": SCHEMA,
        "status": (
            "copied"
            if copied and post_window_sidecars.get("ready")
            else "copied_sidecars_blocked"
            if copied
            else "execute_blocked"
            if args.execute and blockers
            else "dry_run_ready"
            if ready_to_copy and not blockers
            else "blocked"
        ),
        "ready": False,
        **FALSE_FLAGS,
        "instance": args.instance,
        "source_log": str(source_path),
        "evidence_dir": str(evidence_dir),
        "target_log": str(target_status.resolved),
        "execute_requested": args.execute,
        "allow_live_log_read": args.allow_live_log_read,
        "allow_evidence_dir_write": args.allow_evidence_dir_write,
        "allow_post_window_sidecar_generation": args.allow_post_window_sidecar_generation,
        "allow_post_window_preflight_live_read": args.allow_post_window_preflight_live_read,
        "overwrite": args.overwrite,
        "json_output": json_output,
        "fresh_window_start_utc": args.fresh_window_start_utc,
        "fresh_window_end_utc": args.fresh_window_end_utc,
        "now_utc": source_log_not_ready.get("now_utc"),
        "ready_to_copy": ready_to_copy and not blockers,
        "copy_readiness": analysis.get("copy_readiness", "blocked_before_source_analysis"),
        "copied": copied,
        "post_window_sidecars_ready": bool(post_window_sidecars.get("ready")),
        "sidecar_precheck": sidecar_precheck,
        "post_window_sidecars": post_window_sidecars,
        "next_action_commands": next_action_commands(
            args,
            source_path=source_path,
            evidence_dir=evidence_dir,
            target_log=target_status.resolved,
            request=request_context,
            ready_to_copy=ready_to_copy and not blockers,
            copied=copied,
            post_window_sidecars=post_window_sidecars,
            blockers=blockers,
        ),
        "source_sha256": sha256_bytes(data) if data else None,
        "target_existing_sha256": existing_target_sha,
        "target_copied_sha256": sha256_file(target_status.resolved) if copied else None,
        "artifact_hash_path_bindings": artifact_bindings,
        "copied_artifact_bindings": artifact_bindings,
        "copied_log_hash_path_binding": artifact_bindings["copied_log"],
        "sibling_sidecar_hash_path_bindings": artifact_bindings["sibling_sidecars"],
        "bundle_input_artifact_hash_path_bindings": artifact_bindings["bundle_input_artifacts"],
        "copied_log_hash_path_bound": artifact_bindings["copied_log_hash_path_bound"],
        "sibling_sidecars_hash_path_bound": artifact_bindings[
            "sibling_sidecars_hash_path_bound"
        ],
        "bundle_input_artifacts_hash_path_bound": artifact_bindings[
            "bundle_input_artifacts_hash_path_bound"
        ],
        "complete_sibling_set_hash_path_bound": artifact_bindings[
            "complete_sibling_set_hash_path_bound"
        ],
        "artifact_hash_path_bindings_count_as_approved_runtime_evidence": False,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "approved_runtime_evidence_checker_required": APPROVED_RUNTIME_EVIDENCE_CHECKER,
        "copied_artifacts_count_as_approved_runtime_evidence_until_checker_accepts": False,
        "source_log_not_ready": source_log_not_ready,
        "source_log_not_ready_classification": source_log_not_ready["classification"],
        "source_log_not_ready_reason": source_log_not_ready["source_log_not_ready_reason"],
        "observer_only_no_role_window": source_log_not_ready,
        "observer_only_no_role_window_detected": (
            source_log_not_ready["observer_only_no_role_window_detected"]
        ),
        "observer_only_no_role_window_state": source_log_not_ready["window_state"],
        "active_observer_only_no_role_window": (
            source_log_not_ready["active_observer_only_no_role_window"]
        ),
        "post_window_observer_only_no_role_window": (
            source_log_not_ready["post_window_observer_only_no_role_window"]
        ),
        "post_window_closure_action": source_log_not_ready["post_window_closure_action"],
        "source_input": source_input,
        "source_log_safety": source_log_safety,
        "analysis": analysis,
        "ready_log_evidence_split": ready_log_evidence_split,
        "roles_present": analysis.get("roles_present", []),
        "missing_roles": analysis.get("missing_roles", list(REQUIRED_LIFECYCLE_EVENT_ROLES)),
        "blockers": blockers,
        "non_claims": [
            "ready-log copy is operational copy readiness only",
            "copied Obelisk.log is still not approved runtime evidence until sibling-set bundle checkers accept it",
            "this helper does not start, stop, restart, send Discord, edit markers/env, publish, or claim SDK readiness",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    write_json_report(report, args)
    if args.execute and (not report["copied"] or not report["post_window_sidecars_ready"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
