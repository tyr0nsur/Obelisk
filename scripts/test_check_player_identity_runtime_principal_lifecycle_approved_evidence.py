#!/usr/bin/env python3
"""Tests for check_player_identity_runtime_principal_lifecycle_approved_evidence.py."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
RUN_ID = "20260601T120000Z-player-principal-lifecycle"
TEST_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=SCRIPT_DIR.parents[0],
    text=True,
).strip()
OFFLINE_WORKSPACE = Path("/servidor/ark/workspace-offline")
SAFE_OFFLINE_WORKSPACE_DIR = tempfile.TemporaryDirectory(prefix="obelisk-safe-offline-workspace-")
SAFE_OFFLINE_WORKSPACE = Path(SAFE_OFFLINE_WORKSPACE_DIR.name)
os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
LIVE_TEMP_DIRS: list[tempfile.TemporaryDirectory[str]] = []
APPROVED_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
WINDOW_NON_CLAIMS = [
    "window manifest acceptance is operational posture only",
    "does not promote player identity, lookup, permissions, commands, ResourceHandle, mutation, return override, plugin delivery, public SDK, or runtime readiness",
    "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
]
OPERATIONAL_WINDOW_FALSE_FLAGS = {
    "promotion_ready": False,
    "public_header_allowed": False,
    "public_abi_ready": False,
    "public_sdk_ready": False,
    "v1_completion_ready": False,
    "runtime_ready": False,
    "stable_claim_allowed": False,
    "request_pack_counts_as_approved_runtime_evidence": False,
    "preflight_counts_as_approved_runtime_evidence": False,
    "window_manifest_counts_as_approved_runtime_evidence": False,
    "completed_receipt_counts_as_approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
}
SERVER_ROOT_WRITE_OPT_IN_ENV = "OBELISK_ALLOW_SERVER_ROOT_WRITES"

from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    APPROVAL_TEXT,
    AUTHORIZATION_FLAGS,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    NON_CLAIMS,
    REQUEST_ROLLBACK_DELTA,
    STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
    WINDOW_MARKERS,
    current_turn_approval_scope,
    deployment_intent,
    direct_join_plan,
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
    request_pack_digest,
    rollback_plan,
    runtime_triplet_contract,
)


SHA = EXPECTED_BINARY_SHA256
LIBOBELISK_SHA = "2" * 64
LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON = (
    "lifecycle_property_FName_mismatch_expected_name_index_28411"
    "_observed_name_indices_28418_21314_22968_28516_17724"
)
LIFECYCLE_PROPERTY_FNAME_DRIFT_REASON = (
    "lifecycle_property_FName_drift_expected_name_index_28411"
    "_observed_name_index_28418_previous_name_index_28411"
)


def safe_test_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop(SERVER_ROOT_WRITE_OPT_IN_ENV, None)
    env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
    env["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
    return env


def add_output_artifact_identity(payload: dict) -> dict:
    run_id = payload["operational_window"]["run_id"]
    evidence_pack_id = f"player-principal-lifecycle-{run_id}"
    identity_without_hash = {
        "artifact_kind": APPROVED_SCHEMA,
        "capture_id": run_id,
        "evidence_pack_id": evidence_pack_id,
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": payload,
    }
    payload["output_artifact_identity"] = {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest(),
    }
    return payload


def load_script_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    script_dir = str(path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    old_allow = os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES")
    old_root = os.environ.get("OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE")
    os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
    os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
    try:
        spec.loader.exec_module(module)
    finally:
        if old_allow is None:
            os.environ.pop("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES", None)
        else:
            os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = old_allow
        if old_root is None:
            os.environ.pop("OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE", None)
        else:
            os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = old_root
    if hasattr(module, "APPROVED_OFFLINE_WORKSPACE_ROOTS"):
        module.APPROVED_OFFLINE_WORKSPACE_ROOTS = (SAFE_OFFLINE_WORKSPACE,)
    if hasattr(module, "window_manifest_checker"):
        module.window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (SAFE_OFFLINE_WORKSPACE,)
    return module


def temp_offline_workspace() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=SAFE_OFFLINE_WORKSPACE)


def retained_temp_offline_workspace() -> tempfile.TemporaryDirectory[str]:
    temp_dir = temp_offline_workspace()
    LIVE_TEMP_DIRS.append(temp_dir)
    return temp_dir


def cleanup_live_temp_dirs() -> None:
    while LIVE_TEMP_DIRS:
        LIVE_TEMP_DIRS.pop().cleanup()


def runtime_log_lines() -> list[str]:
    return [
        "[info]  Obelisk Runtime Loaded Native (LD_PRELOAD)",
        "[info] ProcessEvent vtable-derived pattern candidates found: 1",
        "[info] ProcessEvent candidate[0] = 0x1d34e20",
        "[info] Found ProcessEvent at address: 0x1d34e20",
        "[info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x767c6aaa4000",
        "[info] ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.",
        "[warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.",
        "[2026-06-01T12:01:30Z] [info] PlayerPrincipalLifecycleObserver enabled "
        f"binary_sha256={SHA} "
        "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
        "delivery_claim=none principal_claim=none.",
        "[2026-06-01T12:02:00Z] [info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
        "[2026-06-01T12:03:00Z] [info] PlayerPrincipalLifecycleObserver event sequence=2 "
        "role=session_start_rejected target=ShooterGameMode.CheckJoinInProgress "
        "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
        "copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer "
        "principal_action=none apply_status=session_start_rejected_noop "
        "correlation_status=not_applicable principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
        "[2026-06-01T12:04:00Z] [info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
        "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
        "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
        "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
    ]


def runtime_log_lines_with_check_join_rejected_start() -> list[str]:
    return runtime_log_lines()


def runtime_log_lines_with_handle_new_player_rejected_bool_values(copied_bool_values: str) -> list[str]:
    lines = runtime_log_lines()
    for index, line in enumerate(lines):
        if "sequence=2 role=session_start_rejected" in line:
            lines[index] = (
                "[2026-06-01T12:03:00Z] [info] PlayerPrincipalLifecycleObserver event sequence=2 "
                "role=session_start_rejected target=ShooterGameMode.HandleNewPlayer "
                "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
                f"copied_bool_values={copied_bool_values} "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none apply_status=session_start_rejected_noop "
                "correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none."
            )
            return lines
    raise AssertionError("session_start_rejected fixture line not found")


def diagnostic_candidate_line(
    *,
    sequence: int = 1,
    target: str = "ShooterGameMode.HandleNewPlayer",
    reason: str = "property_chain_cycle_detected",
) -> str:
    return (
        f"[info] PlayerPrincipalLifecycleDiagnostic candidate sequence={sequence} "
        f"target={target} fname_index=2170 post_original=true "
        "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
        f"reason={reason} params_logged=false identity_logged=false evidence_claim=none."
    )


def diagnostic_check_join_in_progress_copied_bool_line(
    *,
    sequence: int = 1,
    copied_bool_values: str = "1,1",
) -> str:
    return (
        f"[info] PlayerPrincipalLifecycleDiagnostic candidate sequence={sequence} "
        "target=ShooterGameMode.CheckJoinInProgress fname_index=2171 post_original=true "
        "accepted_lifecycle_target=true reflection_status=matched "
        "diagnostic_shape=CheckJoinInProgress copy_status=rejected "
        "copied_bool_fields=bIsFromLogin,ReturnValue "
        f"copied_bool_values={copied_bool_values} redacted_count=1 redacted_fields=NewPlayer "
        "params_logged=false identity_logged=false evidence_claim=none."
    )


def diagnostic_compact_chain_line(
    *,
    sequence: int = 1,
    target: str = "ShooterGameMode.HandleNewPlayer",
    role: str = "session_start",
    copied_bool_fields: str = "bIsFromLogin,ReturnValue",
    copied_bool_values: str = "1,1",
    principal_action: str = "candidate_created",
    apply_status: str = "session_start_created",
    correlation_status: str = "not_applicable",
) -> str:
    return (
        f"[info] PlayerPrincipalLifecycleDiagnostic candidate sequence={sequence} "
        f"target={target} fname_index=2170 post_original=true "
        "accepted_lifecycle_target=true reflection_status=matched read_status=ok "
        "diagnostic_shape=FunctionFNameNearMiss "
        "reason=lifecycle_function_FName_near_miss_expected_name_index_2170_observed_name_index_2171 "
        "observed_property_fname_chain=28418_21314_22968 "
        f"role={role} copied_bool_fields={copied_bool_fields} "
        f"copied_bool_values={copied_bool_values} redacted_count=3 "
        "redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        f"principal_action={principal_action} apply_status={apply_status} "
        f"correlation_status={correlation_status} principal_id_logged=false "
        "principal_generation_logged=false params_logged=false identity_logged=false "
        "evidence_claim=none."
    )


def diagnostic_k2_post_login_line(*, sequence: int = 1) -> str:
    return (
        f"[info] PlayerPrincipalLifecycleDiagnostic candidate sequence={sequence} "
        "target=GameMode.K2_PostLogin fname_index=4943 post_original=true "
        "accepted_lifecycle_target=false reflection_status=matched "
        "diagnostic_shape=K2_PostLogin redacted_count=1 redacted_fields=NewPlayer "
        "params_logged=false identity_logged=false evidence_claim=none."
    )


def runtime_log_lines_with_ragnarok_duplicate_start_diagnostic_missing_check_join() -> list[str]:
    lines = [
        line
        for line in runtime_log_lines()
        if " role=session_start_rejected " not in line
    ]
    duplicate_start = lines[8].replace("sequence=1", "sequence=2").replace(
        "[2026-06-01T12:02:00Z]",
        "[2026-06-01T12:03:00Z]",
    )
    diagnostic = (
        "[2026-06-01T12:03:30Z] [info] PlayerPrincipalLifecycleDiagnostic candidate "
        "sequence=4 target=ShooterGameMode.CheckJoinInProgress fname_index=2171 "
        "post_original=true accepted_lifecycle_target=true reflection_status=matched "
        "read_status=ok diagnostic_shape=CheckJoinInProgress copy_status=rejected "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
        "redacted_count=1 redacted_fields=NewPlayer params_logged=false "
        "identity_logged=false evidence_claim=none."
    )
    lines.insert(9, duplicate_start)
    lines.insert(10, diagnostic)
    return lines


def runtime_log_lines_with_duplicate_start_end_context() -> list[str]:
    lines = runtime_log_lines()
    duplicate_start = lines[8].replace("sequence=1", "sequence=2").replace(
        "[2026-06-01T12:02:00Z]",
        "[2026-06-01T12:02:30Z]",
    )
    selected_rejected = lines[9].replace("sequence=2", "sequence=3")
    selected_end = lines[10].replace("sequence=3", "sequence=4")
    duplicate_end = selected_end.replace("sequence=4", "sequence=5").replace(
        "[2026-06-01T12:04:00Z]",
        "[2026-06-01T12:05:00Z]",
    )
    lines[8:11] = [lines[8], duplicate_start, selected_rejected, selected_end, duplicate_end]
    return lines


def runtime_log_lines_with_only_missing_correlation_session_end() -> list[str]:
    return [
        *runtime_log_lines()[:8],
        "[2026-06-01T12:04:00Z] [info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_end "
        "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
        "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
        "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=missing principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
    ]


def fixture_direct_join_plan(payload: dict) -> dict:
    return direct_join_plan(payload)


def runtime_posture_lines_without_lifecycle_observer() -> list[str]:
    return [
        line
        for line in runtime_log_lines()
        if "PlayerPrincipalLifecycleObserver " not in line
    ]


def without_lifecycle_status_proof_fields(line: str) -> str:
    return (
        line.replace(" apply_status=session_start_created correlation_status=not_applicable", "")
        .replace(" apply_status=session_start_rejected_noop correlation_status=not_applicable", "")
        .replace(" apply_status=session_end_invalidated correlation_status=matched", "")
    )


def write_sidecar(path: Path, text: str) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


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
    checked_at_utc: str = "2026-06-01T12:00:00Z",
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
    checked_at_utc: str = "2026-06-01T12:15:00Z",
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


def operational_sidecars(copied_log: Path, *, standing_launch_authority: bool = False) -> dict[str, dict]:
    workspace = copied_log.parents[2]
    live_dir = copied_log.parent
    sidecar_dir = live_dir
    copied_log_sha256 = hashlib.sha256(copied_log.read_bytes()).hexdigest()
    manifest_path = live_dir / "window-manifest.env"
    request_pack_path = sidecar_dir / "window-request.json"
    observer_env_path = sidecar_dir / "observer-window.env"
    operator_request_path = sidecar_dir / "operator-approval-request.md"
    operator_approval_receipt_path = sidecar_dir / "operator-approval-receipt.json"
    preflight_pre_path = live_dir / "preflight-pre.json"
    preflight_post_path = live_dir / "preflight-post.json"
    post_restart_preflight_path = live_dir / "post-restart-preflight.env"
    installed_libobelisk_path = live_dir / "installed-libobelisk.env"
    target = {"instance": "arkserver2", "map": "TheIsland"}
    approved_window = {
        "start_utc": "2026-06-01T12:00:00Z",
        "end_utc": "2026-06-01T12:15:00Z",
    }
    approval_text = STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT if standing_launch_authority else APPROVAL_TEXT
    prepared_at_utc = "2026-06-01T11:55:00Z"
    request_args = type(
        "Args",
        (),
        {
            "instance": "arkserver2",
            "map_name": "TheIsland",
            "binary_sha256": SHA,
            "obelisk_commit": TEST_COMMIT,
            "obelisk_build_artifact": None,
            "obelisk_build_artifact_sha256": None,
            "obelisk_build_artifact_label": None,
        },
    )()
    observer_env_lines = env_lines(request_args)
    request_payload = {
        "schema": "obelisk.player-principal-lifecycle-window-request.v1",
        "status": "candidate_only_request_pack",
        "approval_required": approval_text,
        "prepared_at_utc": prepared_at_utc,
        "target": target,
        "run_id": RUN_ID,
        "ark_binary_sha256": SHA,
        "server_binary_path": EXPECTED_SERVER_BINARY_PATH,
        "obelisk_commit": TEST_COMMIT,
        "planned_obelisk_build_identity": planned_obelisk_build_identity(request_args),
        "approved_window": approved_window,
        "restart_expectation": "restart",
        "final_posture": "stable",
        "diagnostic_candidates_enabled": False,
        "authorization_flags": dict(AUTHORIZATION_FLAGS),
        "user_policy": "no_regular_users",
        "notice_path": "not_applicable",
        "copied_evidence_dir": str(live_dir),
        "copied_log_path": str(copied_log),
        "window_manifest_path": str(manifest_path),
        "observer_env_file": "observer-window.env",
        "marker_set": WINDOW_MARKERS,
        "forbidden_markers": FORBIDDEN_MARKERS,
        "rollback": rollback_plan(target, "operator"),
        "runtime_triplet_contract": runtime_triplet_contract(),
        "non_claims": NON_CLAIMS,
    }
    request_payload["exact_target_scope"] = exact_target_scope(request_payload)
    request_payload["passive_wait_boundary"] = passive_wait_boundary(request_payload)
    request_payload["player_notice_action"] = player_notice_action(request_payload)
    request_payload["player_presence_safety"] = player_presence_safety(request_payload)
    join_plan = fixture_direct_join_plan(request_payload)
    request_payload["direct_join_plan"] = join_plan
    request_payload["post_window_replay_contract"] = post_window_replay_contract(request_payload)
    request_payload["current_turn_approval_scope"] = current_turn_approval_scope(
        request_payload,
        observer_env_lines,
    )
    request_payload["deployment_intent"] = deployment_intent(request_payload)
    request_payload["operator_live_ops_brief"] = operator_live_ops_brief(
        request_payload,
        observer_env_lines,
    )
    markdown_payload = {**request_payload, "direct_join_plan": join_plan}
    request = write_sidecar(
        request_pack_path,
        json.dumps(request_payload, sort_keys=True) + "\n",
    )
    observer_env = write_sidecar(
        observer_env_path,
        "\n".join(observer_env_lines) + "\n",
    )
    write_sidecar(
        operator_request_path,
        markdown_request(markdown_payload, observer_env_lines),
    )
    receipt_payload = operator_approval_receipt_payload(
        markdown_payload,
        request_json_path=request_pack_path,
        request_md_path=operator_request_path,
        env_path=observer_env_path,
        operator_approved=True,
        operator_reference="operator",
        approved_at_utc="2026-06-01T11:56:00Z",
    )
    operator_approval_receipt = write_sidecar(
        operator_approval_receipt_path,
        json.dumps(receipt_payload, sort_keys=True)
        + "\n",
    )
    preflight_pre = write_sidecar(
        preflight_pre_path,
        preflight_payload(
            mode="observer-window",
            instance="arkserver2",
            run_id=RUN_ID,
            map_name="TheIsland",
            window_manifest_path=manifest_path,
            copied_log_path=copied_log,
            env_file=observer_env_path,
            env_sha256=observer_env["sha256"],
            checked_at_utc=approved_window["start_utc"],
        ),
    )
    preflight_post = write_sidecar(
        preflight_post_path,
        preflight_payload(
            mode="stable",
            instance="arkserver2",
            run_id=RUN_ID,
            map_name="TheIsland",
            window_manifest_path=manifest_path,
            copied_log_path=copied_log,
            checked_at_utc="2026-06-01T12:15:00Z",
        ),
    )
    post_restart_preflight = write_sidecar(
        post_restart_preflight_path,
        post_restart_preflight_sidecar_text(
            copied_log=copied_log,
            copied_log_sha256=copied_log_sha256,
        ),
    )
    write_sidecar(
        installed_libobelisk_path,
        installed_libobelisk_sidecar_text(
            copied_log=copied_log,
            copied_log_sha256=copied_log_sha256,
            post_restart_preflight=post_restart_preflight_path,
            post_restart_preflight_sha256=post_restart_preflight["sha256"],
        ),
    )
    manifest = write_sidecar(
        manifest_path,
        "\n".join(
            [
                f"run_id={RUN_ID}",
                f"obelisk_commit={TEST_COMMIT}",
                "target=arkserver2/TheIsland",
                f"approval={approval_text}",
                f"approved_window_start_utc={approved_window['start_utc']}",
                f"approved_window_end_utc={approved_window['end_utc']}",
                "actual_capture_start_utc=2026-06-01T12:01:00Z",
                "actual_capture_end_utc=2026-06-01T12:09:00Z",
                f"copied_log_path={copied_log}",
                f"copied_log_sha256={copied_log_sha256}",
                f"request_pack_path={request_pack_path}",
                f"request_pack_sha256={request['sha256']}",
                f"observer_env_path={observer_env_path}",
                f"observer_env_sha256={observer_env['sha256']}",
                f"operator_approval_receipt_path={operator_approval_receipt_path}",
                f"operator_approval_receipt_sha256={operator_approval_receipt['sha256']}",
                f"preflight_pre_path={preflight_pre_path}",
                f"preflight_pre_sha256={preflight_pre['sha256']}",
                f"preflight_post_path={preflight_post_path}",
                f"preflight_post_sha256={preflight_post['sha256']}",
                "pre_posture=stable",
                "post_posture=stable",
                "pre_check=passed",
                "post_check=passed",
                "rollback_start_utc=2026-06-01T12:09:00Z",
                "rollback_end_utc=2026-06-01T12:15:00Z",
                "rollback_completed=true",
                "rollback_delta=removed_observer_env_and_markers_preserved_disable_plugins",
                "observer_env_survived=false",
                "observer_marker_survived=false",
                "sibling_marker_entries=absent",
                "sibling_observer_env=absent",
                "user_policy=no_regular_users",
                "notice_sent=not_applicable",
                "log_budget=10",
                "plugins_disabled=true",
                "scanner_disabled=true",
                "dispatch_limit=0",
                "wrapper_profile=observer-debug",
                "observer_exclusivity=player_principal_lifecycle_only",
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
    )
    return {
        "manifest": manifest,
        "request_pack": request,
        "observer_env": observer_env,
        "operator_approval_receipt": {
            **operator_approval_receipt,
            "verified": True,
        },
        "preflight": {
            "pre": preflight_pre,
            "post": preflight_post,
        },
    }


def analyzer_summary() -> dict:
    temp_dir = retained_temp_offline_workspace()
    log_path = Path(temp_dir.name) / "live-validation-logs" / RUN_ID / "Obelisk.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ANALYZER), "--obelisk-commit", TEST_COMMIT, str(log_path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **safe_test_env(),
        },
    )
    return json.loads(result.stdout)


def manifest(*, standing_launch_authority: bool = False) -> dict:
    summary = analyzer_summary()
    source = summary["evidence"]["sources"][0]
    sidecars = operational_sidecars(Path(source["path"]), standing_launch_authority=standing_launch_authority)
    approval_text = STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT if standing_launch_authority else APPROVAL_TEXT
    return add_output_artifact_identity({
        "schema": APPROVED_SCHEMA,
        "artifact_status": "approved_runtime_observer_summary",
        "readiness_classification": "runtime_evidence_only",
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "approval": {
            "runtime_evidence_reviewed": True,
            "reviewed_by": "runtime-reviewer",
            "review_note": "consume-only lifecycle evidence reviewed",
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
            "obelisk_commit": summary["evidence"]["obelisk_commit"],
            "approval": approval_text,
            "approved_window": {"start_utc": "2026-06-01T12:00:00Z", "end_utc": "2026-06-01T12:15:00Z"},
            "actual_capture": {"start_utc": "2026-06-01T12:01:00Z", "end_utc": "2026-06-01T12:09:00Z"},
            "rollback_window": {"start_utc": "2026-06-01T12:09:00Z", "end_utc": "2026-06-01T12:15:00Z"},
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            **sidecars,
            "copied_log": {"path": source["path"], "path_status": "approved_offline_workspace", "sha256": source["sha256"]},
            "posture": {
                "pre_check": "passed",
                "post_check": "passed",
                "pre_posture": "stable",
                "post_posture": "stable",
                "plugins_disabled": True,
                "scanner_disabled": True,
                "dispatch_limit": "0",
                "wrapper_profile": "observer-debug",
                "observer_exclusivity": "player_principal_lifecycle_only",
                "sibling_marker_entries": "absent",
                "sibling_observer_env": "absent",
                "debug_escape_markers": "absent",
                "callback_escape_markers": "absent",
                "native_exec_disabled": True,
                "ptrace_disabled": True,
                "single_module_summary": "player_principal_lifecycle",
            },
            "rollback": {
                "completed": True,
                "observer_env_survived": False,
                "observer_marker_survived": False,
                "delta": "removed_observer_env_and_markers_preserved_disable_plugins",
            },
            "log_budget": "10",
            "claims": {"delivery_claim": "none", "principal_claim": "none"},
            "user_policy": "no_regular_users",
            "notice_sent": "not_applicable",
            **OPERATIONAL_WINDOW_FALSE_FLAGS,
            "non_claims": WINDOW_NON_CLAIMS,
        },
        "source_summary": summary,
        "consumer_boundary_cases": [
            {
                "case": "stale_after_logout",
                "result": "fail_closed",
                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                "runtime_observed": False,
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "result": "fail_closed",
                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                "runtime_observed": False,
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
        ],
        "privacy_boundary": {
            "copied_opaque_principal_only": True,
            "redacted_runtime_observer": True,
            "player_identifiers_logged": False,
            "lookup_allowed": False,
            "resource_handle_allowed": False,
            "mutation_allowed": False,
            "return_override_allowed": False,
        },
        "promotion_gate": {
            "runtime_evidence_ready": True,
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "non_claims": [
            "approved runtime observer evidence only",
            "does not promote public player identity, lookup, permissions, commands, moderation, admin authority, mutation, return override, ResourceHandle, or v1 SDK readiness",
            "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, FNames, GObjects, raw params, or persistent lookup keys",
            "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
        ],
    })


def manifest_for_copied_log(copied_log: Path, *, log_lines: list[str] | None = None) -> dict:
    lines = runtime_log_lines() if log_lines is None else log_lines
    analyzer = load_script_module(ANALYZER, "test_player_principal_analyzer")
    summary = analyzer.analyze_lines(lines)
    source_sha256 = hashlib.sha256(copied_log.read_bytes()).hexdigest()
    summary["evidence"] = {
        "kind": "runtime-observer-log",
        "obelisk_commit": TEST_COMMIT,
        "sources": [
            {
                "path": str(copied_log),
                "sha256": source_sha256,
                "line_count": len(lines),
            }
        ],
        "server_paths_allowed": False,
    }
    sidecars = operational_sidecars(copied_log)
    return add_output_artifact_identity({
        "schema": APPROVED_SCHEMA,
        "artifact_status": "approved_runtime_observer_summary",
        "readiness_classification": "runtime_evidence_only",
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "approval": {
            "runtime_evidence_reviewed": True,
            "reviewed_by": "runtime-reviewer",
            "review_note": "consume-only lifecycle evidence reviewed",
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
            "approval": "current-turn operator-approved runtime window, not standing approval",
            "approved_window": {"start_utc": "2026-06-01T12:00:00Z", "end_utc": "2026-06-01T12:15:00Z"},
            "actual_capture": {"start_utc": "2026-06-01T12:01:00Z", "end_utc": "2026-06-01T12:09:00Z"},
            "rollback_window": {"start_utc": "2026-06-01T12:09:00Z", "end_utc": "2026-06-01T12:15:00Z"},
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            **sidecars,
            "copied_log": {"path": str(copied_log), "path_status": "approved_offline_workspace", "sha256": source_sha256},
            "posture": {
                "pre_check": "passed",
                "post_check": "passed",
                "pre_posture": "stable",
                "post_posture": "stable",
                "plugins_disabled": True,
                "scanner_disabled": True,
                "dispatch_limit": "0",
                "wrapper_profile": "observer-debug",
                "observer_exclusivity": "player_principal_lifecycle_only",
                "sibling_marker_entries": "absent",
                "sibling_observer_env": "absent",
                "debug_escape_markers": "absent",
                "callback_escape_markers": "absent",
                "native_exec_disabled": True,
                "ptrace_disabled": True,
                "single_module_summary": "player_principal_lifecycle",
            },
            "rollback": {
                "completed": True,
                "observer_env_survived": False,
                "observer_marker_survived": False,
                "delta": "removed_observer_env_and_markers_preserved_disable_plugins",
            },
            "log_budget": "10",
            "claims": {"delivery_claim": "none", "principal_claim": "none"},
            "user_policy": "no_regular_users",
            "notice_sent": "not_applicable",
            **OPERATIONAL_WINDOW_FALSE_FLAGS,
            "non_claims": WINDOW_NON_CLAIMS,
        },
        "source_summary": summary,
        "consumer_boundary_cases": [
            {
                "case": "stale_after_logout",
                "result": "fail_closed",
                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                "runtime_observed": False,
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "result": "fail_closed",
                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                "runtime_observed": False,
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
        ],
        "privacy_boundary": {
            "copied_opaque_principal_only": True,
            "redacted_runtime_observer": True,
            "player_identifiers_logged": False,
            "lookup_allowed": False,
            "resource_handle_allowed": False,
            "mutation_allowed": False,
            "return_override_allowed": False,
        },
        "promotion_gate": {
            "runtime_evidence_ready": True,
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "non_claims": [
            "approved runtime observer evidence only",
            "does not promote public player identity, lookup, permissions, commands, moderation, admin authority, mutation, return override, ResourceHandle, or v1 SDK readiness",
            "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, FNames, GObjects, raw params, or persistent lookup keys",
            "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
        ],
    })


def blocked_ready_log_copy_payload(
    copied_log: Path,
    *,
    missing_roles: list[str] | tuple[str, ...] = ("session_start", "session_start_rejected", "session_end"),
) -> dict:
    missing_role_list = list(missing_roles)
    roles_present = [
        role
        for role in ("session_start", "session_start_rejected", "session_end")
        if role not in missing_role_list
    ]
    blockers = [
        "blocked_missing_lifecycle_roles",
        *[f"exact_copied_runtime_triplet_missing_{role}" for role in missing_role_list],
    ]
    return {
        "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
        "status": "dry_run_blocked",
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
        "source_log": str(copied_log.parent / "source" / "Obelisk.log"),
        "evidence_dir": str(copied_log.parent),
        "target_log": str(copied_log),
        "execute_requested": False,
        "allow_live_log_read": False,
        "allow_evidence_dir_write": False,
        "overwrite": False,
        "fresh_window_start_utc": "2026-06-01T12:01:00Z",
        "fresh_window_end_utc": "2026-06-01T12:09:00Z",
        "ready_to_copy": False,
        "copy_readiness": "blocked_missing_lifecycle_roles",
        "copied": False,
        "source_sha256": None,
        "target_existing_sha256": None,
        "target_copied_sha256": None,
        "roles_present": roles_present,
        "missing_roles": missing_role_list,
        "blockers": blockers,
        "source_log_safety": {
            "accepted": True,
            "blockers": [],
            "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence": False,
            "passive_context_counts_as_approved_runtime_evidence": False,
        },
        "analysis": {
            "observer_enabled": True,
            "binary_sha256_match": True,
            "roles_present": roles_present,
            "missing_roles": missing_role_list,
            "ready_to_copy": False,
            "copy_readiness": "blocked_missing_lifecycle_roles",
            "fresh_window": {
                "start_utc": "2026-06-01T12:01:00Z",
                "end_utc": "2026-06-01T12:09:00Z",
            },
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
            "this helper does not start, stop, restart, send Discord, edit markers/env, publish, or claim SDK readiness",
        ],
    }


def blocked_player_presence_ready_log_copy_payload(copied_log: Path) -> dict:
    payload = blocked_ready_log_copy_payload(copied_log)
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
    payload["blockers"] = [
        *payload["blockers"],
        "source_log_contains_passive_context_metadata",
        "player_present_but_no_lifecycle_roles",
    ]
    payload["source_log_safety"] = {
        "accepted": False,
        "blockers": ["source_log_contains_passive_context_metadata"],
        "passive_context_line_count": 1,
        "player_presence_context": presence_context,
        "passive_context_counts_as_approved_runtime_evidence": False,
        "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence": False,
    }
    payload["source_log_not_ready"] = source_log_not_ready
    payload["observer_only_no_role_window"] = source_log_not_ready
    payload["observer_only_no_role_window_detected"] = True
    payload["player_present_but_no_lifecycle_roles"] = True
    return payload


def ready_log_copy_payload(copied_log: Path) -> dict:
    roles = ["session_start", "session_start_rejected", "session_end"]
    copied_sha256 = hashlib.sha256(copied_log.read_bytes()).hexdigest()
    accepted_events = {
        "session_start": {
            "role": "session_start",
            "line_number": 9,
            "sequence": 1,
            "target": "ShooterGameMode.HandleNewPlayer",
            "timestamp_prefix": "2026-06-01T12:02:00Z",
            "copied_bool_fields": "bIsFromLogin,ReturnValue",
            "copied_bool_values": "1,1",
            "inside_fresh_window": True,
            "approved_copy_shape_ok": True,
            "apply_status": "session_start_created",
            "correlation_status": "not_applicable",
            "status_proof_ok": True,
        },
        "session_start_rejected": {
            "role": "session_start_rejected",
            "line_number": 10,
            "sequence": 2,
            "target": "ShooterGameMode.CheckJoinInProgress",
            "timestamp_prefix": "2026-06-01T12:03:00Z",
            "copied_bool_fields": "bIsFromLogin,ReturnValue",
            "copied_bool_values": "1,0",
            "inside_fresh_window": True,
            "approved_copy_shape_ok": True,
            "apply_status": "session_start_rejected_noop",
            "correlation_status": "not_applicable",
            "status_proof_ok": True,
        },
        "session_end": {
            "role": "session_end",
            "line_number": 11,
            "sequence": 3,
            "target": "ShooterGameMode.OnLogout",
            "timestamp_prefix": "2026-06-01T12:04:00Z",
            "copied_bool_fields": "",
            "copied_bool_values": "",
            "inside_fresh_window": True,
            "approved_copy_shape_ok": True,
            "apply_status": "session_end_invalidated",
            "correlation_status": "matched",
            "status_proof_ok": True,
        },
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
            "start_utc": "2026-06-01T12:01:00Z",
            "end_utc": "2026-06-01T12:09:00Z",
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
        "source_log": str(copied_log.parent / "source" / "Obelisk.log"),
        "evidence_dir": str(copied_log.parent),
        "target_log": str(copied_log),
        "execute_requested": True,
        "allow_live_log_read": True,
        "allow_evidence_dir_write": True,
        "overwrite": False,
        "fresh_window_start_utc": "2026-06-01T12:01:00Z",
        "fresh_window_end_utc": "2026-06-01T12:09:00Z",
        "ready_to_copy": True,
        "copy_readiness": "ready_complete_role_triplet",
        "copied": True,
        "source_sha256": copied_sha256,
        "target_existing_sha256": None,
        "target_copied_sha256": copied_sha256,
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
        "analysis": analysis,
        "non_claims": [
            "ready-log copy is operational copy readiness only",
            "copied Obelisk.log is still not approved runtime evidence until sibling-set bundle checkers accept it",
            "this helper does not start, stop, restart, send Discord, edit markers/env, publish, or claim SDK readiness",
        ],
    }


def stale_fresh_window_ready_log_copy_payload(copied_log: Path) -> dict:
    payload = ready_log_copy_payload(copied_log)
    payload["fresh_window_start_utc"] = "2026-06-01T12:06:00Z"
    payload["fresh_window_end_utc"] = "2026-06-01T12:09:00Z"
    payload["analysis"]["fresh_window"] = {
        "start_utc": payload["fresh_window_start_utc"],
        "end_utc": payload["fresh_window_end_utc"],
    }
    return payload


class ApprovedRuntimePrincipalLifecycleEvidenceTests(unittest.TestCase):
    def tearDown(self) -> None:
        cleanup_live_temp_dirs()

    def test_safe_test_env_drops_server_root_write_override(self) -> None:
        old_value = os.environ.get(SERVER_ROOT_WRITE_OPT_IN_ENV)
        os.environ[SERVER_ROOT_WRITE_OPT_IN_ENV] = "1"
        try:
            env = safe_test_env()
        finally:
            if old_value is None:
                os.environ.pop(SERVER_ROOT_WRITE_OPT_IN_ENV, None)
            else:
                os.environ[SERVER_ROOT_WRITE_OPT_IN_ENV] = old_value

        self.assertNotIn(SERVER_ROOT_WRITE_OPT_IN_ENV, env)

    def test_request_pack_digest_uses_prepare_helper(self) -> None:
        import prepare_player_principal_lifecycle_window_request as prepare_helper

        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_digest")
        self.assertIs(checker.request_pack_digest, prepare_helper.request_pack_digest)

    def test_operational_window_allowed_keys_are_replayed(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_replay_keys")
        self.assertEqual(
            set(checker.OPERATIONAL_WINDOW_REPLAY_KEYS),
            set(checker.ALLOWED_OPERATIONAL_WINDOW_KEYS),
        )

    def run_checker(self, payload: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approved-runtime-evidence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json", *args],
                check=False,
                env={
                    **safe_test_env(),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def run_checker_file(
        self,
        path: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(path), "--json", *args],
            check=False,
            env={
                **safe_test_env(),
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def assert_runtime_evidence_and_public_readiness_blocked(self, report: dict) -> None:
        self.assertFalse(report["runtime_evidence_ready"])
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)

    def assert_sdk_p0_runtime_public_evidence_blocked(self, report: dict) -> None:
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIsInstance(report["fastest_next_action"], dict)
        self.assertEqual(
            report["fastest_next_action"]["sdk_p0_progress_before_checker_accepted_bundle"],
            "0",
        )

    def assert_public_runtime_v1_complete_sdk_flags_false(self, report: dict) -> None:
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["v1_completion_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["complete_sdk_allowed"])
        self.assertFalse(report["complete_sdk_ready"])
        self.assertEqual(report["sdk_surfaces_promoted_by_this_checker"], 0)
        self.assertEqual(report["p0_surfaces_promoted_by_this_checker"], 0)
        self.assertFalse(report["accepted_runtime_evidence_counts_as_sdk_progress"])
        self.assertFalse(report["accepted_runtime_evidence_counts_as_p0_progress"])
        self.assertTrue(report["post_runtime_contract_gate_required"])
        self.assertEqual(
            report["post_runtime_contract_gate"],
            "identity_public_contract_gate_missing",
        )

    def write_copied_log(self, lines: list[str]) -> Path:
        temp_dir = retained_temp_offline_workspace()
        log_path = Path(temp_dir.name) / "live-validation-logs" / RUN_ID / "Obelisk.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return log_path

    def strict_rejected_start_blocker(self, report: dict) -> dict:
        return next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "runtime_summary_strict_rejected_start_missing"
        )

    def test_accepts_clean_runtime_summary_without_promoting_public_sdk(self) -> None:
        result = self.run_checker(manifest())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["ready_scope"], "runtime_evidence_only")
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["runtime_evidence_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["v1_completion_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["complete_sdk_allowed"])
        self.assertFalse(report["complete_sdk_ready"])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertEqual(report["non_evidence_reasons"], [])
        self.assertEqual(report["artifact_path_issues"], [])
        self.assertEqual(report["remaining_blockers"], [])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertIsNone(report["current_route_blocker"])
        self.assertIsNone(report["next_required_artifact"])
        self.assertIsNone(report["missing_required_artifact"])
        self.assertEqual(report["required_artifact_status"], "accepted")
        self.assertFalse(report["partial_start_end_present"])
        self.assertFalse(report["missing_strict_rejected_start"])
        self.assertEqual(
            report["strict_rejected_start_expected_shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            report["strict_rejected_start_observed_shape"]["shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        proof = report["lifecycle_correlation_proof"]
        self.assertTrue(proof["accepted"])
        self.assertTrue(proof["single_complete_sibling_set"])
        self.assertEqual(proof["run_id"], RUN_ID)
        self.assertEqual(proof["selected_sequences"], [1, 2, 3])
        self.assertEqual(
            proof["selected_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(proof["selected_line_numbers"], [9, 10, 11])
        self.assertEqual(proof["session_end_correlation_status"], "matched")
        self.assertEqual(
            report["consumer_cases"],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )

    def test_accepts_safe_diagnostic_fname_mismatch_target_summary_key(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        self.assertIn(
            "diagnostic_lifecycle_property_fname_mismatch_target_summary",
            module,
        )
        self.assertEqual(
            module["diagnostic_lifecycle_property_fname_mismatch_target_summary"]["evidence_claim"],
            "none",
        )
        self.assertFalse(
            module["diagnostic_lifecycle_property_fname_mismatch_target_summary"][
                "approved_runtime_evidence"
            ]
        )

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["runtime_evidence_ready"])
        self.assertNotIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_rejects_leakage_inside_diagnostic_fname_mismatch_target_summary(self) -> None:
        cases = (
            ("player_name", "SyntheticPlayer"),
            ("ue_pointer", "0x12345678"),
        )
        for key, value in cases:
            with self.subTest(key=key):
                payload = manifest()
                module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
                module["diagnostic_lifecycle_property_fname_mismatch_target_summary"]["targets"] = [
                    {
                        "target": "ShooterGameMode.HandleNewPlayer",
                        key: value,
                    }
                ]
                payload.pop("output_artifact_identity", None)
                add_output_artifact_identity(payload)

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])
                self.assertIn(
                    f"$.source_summary.modules.player_principal_lifecycle."
                    f"diagnostic_lifecycle_property_fname_mismatch_target_summary.targets[0].{key}",
                    [detail["label"] for detail in report["blocker_details"]],
                )

    def test_accepts_check_join_in_progress_rejected_start_runtime_summary_without_promoting_public_sdk(self) -> None:
        lines = runtime_log_lines_with_check_join_rejected_start()
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
        )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertEqual(report["ready_scope"], "runtime_evidence_only")
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["runtime_evidence_ready"])
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertEqual(report["remaining_blockers"], [])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_blocked_ready_log_copy_report_blocks_operational_window_approval(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        report_path = copied_log.parent / "ready-log-copy.json"
        report_path.write_text(
            json.dumps(blocked_ready_log_copy_payload(copied_log), sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertEqual(report["missing_lifecycle_event_roles"], [])
        self.assertIn("operational_window_ready_log_copy_not_ready_to_copy", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "operational_window_ready_log_copy_not_ready_to_copy"
        )
        self.assertEqual(detail["status"], "dry_run_blocked")
        self.assertEqual(detail["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertEqual(detail["roles_present"], [])
        self.assertEqual(
            detail["missing_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertIn("blocked_missing_lifecycle_roles", detail["reported_blockers"])
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)

    def test_player_presence_ready_log_copy_blocker_blocks_operational_window_approval(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        report_path = copied_log.parent / "ready-log-copy.json"
        report_path.write_text(
            json.dumps(blocked_player_presence_ready_log_copy_payload(copied_log), sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("operational_window_ready_log_copy_not_ready_to_copy", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "operational_window_ready_log_copy_not_ready_to_copy"
        )
        self.assertEqual(detail["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertEqual(detail["missing_roles"], ["session_start", "session_start_rejected", "session_end"])
        self.assertIn("player_present_but_no_lifecycle_roles", detail["reported_blockers"])
        self.assertIn("player_present_but_no_lifecycle_roles", detail["source_log_not_ready_blockers"])
        self.assertTrue(detail["observer_only_no_role_window_detected"])
        self.assertTrue(detail["player_present_but_no_lifecycle_roles"])
        self.assertTrue(detail["player_presence_context"]["players_detected"])
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)

    def test_ready_log_copy_report_outside_fresh_window_blocks_operational_window_approval(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        report_path = copied_log.parent / "ready-log-copy.json"
        report_path.write_text(
            json.dumps(stale_fresh_window_ready_log_copy_payload(copied_log), sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_ready_log_copy_copied_log_lifecycle_event_outside_fresh_window",
            report["blockers"],
        )
        self.assertIn(
            "operational_window_ready_log_copy_ready_to_copy_without_accepted_fresh_window_triplet",
            report["blockers"],
        )
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)

    def test_ready_log_copy_report_without_exact_triplet_blocks_operational_window_approval(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        ready_payload = ready_log_copy_payload(copied_log)
        ready_payload["analysis"]["exact_copied_runtime_triplet"] = {
            "accepted": False,
            "status": "missing",
            "blockers": ["exact_copied_runtime_triplet_missing_session_start_rejected"],
            "required_roles": ["session_start", "session_start_rejected", "session_end"],
            "accepted_roles": ["session_start", "session_end"],
            "missing_roles": ["session_start_rejected"],
            "copied_log_only_counts_as_approved_runtime_evidence": False,
            "passive_or_diagnostic_material_counts_as_approved_runtime_evidence": False,
        }
        (copied_log.parent / "ready-log-copy.json").write_text(
            json.dumps(ready_payload, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_ready_log_copy_exact_copied_runtime_triplet_not_accepted",
            report["blockers"],
        )
        self.assertIn(
            "operational_window_ready_log_copy_exact_copied_runtime_triplet_blockers_present",
            report["blockers"],
        )
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)

    def test_ready_log_copy_selected_triplet_drift_blocks_operational_window_approval(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        ready_payload = ready_log_copy_payload(copied_log)
        ready_payload["analysis"]["exact_copied_runtime_triplet"]["selected_sequences"] = [1, 99, 3]
        (copied_log.parent / "ready-log-copy.json").write_text(
            json.dumps(ready_payload, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_ready_log_copy_exact_copied_runtime_triplet_selected_sequences_mismatch",
            report["blockers"],
        )
        self.assertTrue(report["lifecycle_correlation_proof"]["accepted"])
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)

    def test_rejects_handle_new_player_rejected_bool_tuple_aliases(self) -> None:
        for copied_bool_values in ("0,1", "1,0", "0,0"):
            with self.subTest(copied_bool_values=copied_bool_values):
                lines = runtime_log_lines_with_handle_new_player_rejected_bool_values(copied_bool_values)
                log_path = self.write_copied_log(lines)

                result = self.run_checker(
                    manifest_for_copied_log(log_path, log_lines=lines),
                    check=False,
                )
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assert_public_runtime_v1_complete_sdk_flags_false(report)
                self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
                self.assertIn(
                    "source_summary_copied_log_lifecycle_event_unapproved_shape",
                    report["blockers"],
                )
                self.assertIn(
                    "runtime_summary_required_observed_event_cases_missing",
                    report["blockers"],
                )
                self.assertEqual(
                    report["observed_runtime_cases"],
                    ["observer_enable"],
                )

    def test_rejects_check_join_in_progress_rejected_start_unapproved_shape(self) -> None:
        lines = [
            line.replace("copied_bool_values=1,0", "copied_bool_values=0,1")
            if "target=ShooterGameMode.CheckJoinInProgress" in line
            else line
            for line in runtime_log_lines_with_check_join_rejected_start()
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_unapproved_shape",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_required_observed_event_cases_missing",
            report["blockers"],
        )

    def test_reports_partial_start_end_when_rejected_start_is_missing(self) -> None:
        lines = [
            line
            for line in runtime_log_lines()
            if "role=session_start_rejected " not in line
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("runtime_summary_strict_rejected_start_missing", report["blockers"])
        self.assertTrue(report["partial_start_end_present"])
        self.assertTrue(report["missing_strict_rejected_start"])
        self.assertEqual(report["missing_lifecycle_event_roles"], ["session_start_rejected"])
        self.assertIsNone(report["strict_rejected_start_observed_shape"])
        blocker = self.strict_rejected_start_blocker(report)
        self.assertTrue(blocker["partial_start_end_present"])
        self.assertTrue(blocker["missing_strict_rejected_start"])
        self.assertIsNone(blocker["strict_rejected_start_observed_shape"])

    def test_reports_check_join_zero_zero_as_missing_strict_rejected_start(self) -> None:
        lines = [
            line.replace("copied_bool_values=1,0", "copied_bool_values=0,0")
            if "target=ShooterGameMode.CheckJoinInProgress" in line
            else line
            for line in runtime_log_lines_with_check_join_rejected_start()
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("runtime_summary_strict_rejected_start_missing", report["blockers"])
        self.assertIn("source_summary_copied_log_lifecycle_event_unapproved_shape", report["blockers"])
        self.assertTrue(report["partial_start_end_present"])
        self.assertTrue(report["missing_strict_rejected_start"])
        self.assertEqual(
            report["strict_rejected_start_observed_shape"]["shape"],
            "ShooterGameMode.CheckJoinInProgress(0,0)",
        )
        blocker = self.strict_rejected_start_blocker(report)
        self.assertEqual(
            blocker["strict_rejected_start_observed_shape"]["copied_bool_values"],
            ["0", "0"],
        )

    def test_reports_superseded_handle_new_player_zero_one_as_missing_strict_rejected_start(self) -> None:
        lines = runtime_log_lines_with_handle_new_player_rejected_bool_values("0,1")
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("runtime_summary_strict_rejected_start_missing", report["blockers"])
        self.assertIn("source_summary_copied_log_lifecycle_event_unapproved_shape", report["blockers"])
        self.assertTrue(report["partial_start_end_present"])
        self.assertTrue(report["missing_strict_rejected_start"])
        self.assertEqual(
            report["strict_rejected_start_observed_shape"]["shape"],
            "ShooterGameMode.HandleNewPlayer(0,1)",
        )
        blocker = self.strict_rejected_start_blocker(report)
        self.assertEqual(
            blocker["strict_rejected_start_observed_shape"]["target"],
            "ShooterGameMode.HandleNewPlayer",
        )

    def test_rejects_debug_check_join_candidate_as_session_start_rejected_role(self) -> None:
        lines = [
            line
            for line in runtime_log_lines()
            if "role=session_start_rejected " not in line
        ]
        lines.insert(
            -1,
            diagnostic_check_join_in_progress_copied_bool_line(
                sequence=99,
                copied_bool_values="1,0",
            ),
        )
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assert_sdk_p0_runtime_public_evidence_blocked(report)
        self.assertIn("source_summary_copied_log_contains_diagnostic_lifecycle_lines", report["blockers"])
        self.assertIn("source_summary_copied_log_contains_diagnostic_candidates", report["blockers"])
        self.assertIn("runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence", report["blockers"])
        self.assertIn(
            "runtime_summary_check_join_in_progress_diagnostic_context_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_diagnostic_guardrail_not_approved_lifecycle_evidence", report["blockers"])
        self.assertIn("runtime_summary_strict_rejected_start_missing", report["blockers"])
        self.assertTrue(report["partial_start_end_present"])
        self.assertTrue(report["missing_strict_rejected_start"])
        self.assertNotIn("session_start_rejected_anchor", report["observed_runtime_cases"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable"],
        )

    def test_rejects_mixed_check_join_fname_property_drift_even_with_exact_triplet(self) -> None:
        lines = [
            *runtime_log_lines(),
            diagnostic_candidate_line(
                sequence=4,
                target="ShooterGameMode.CheckJoinInProgress",
                reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
            ),
            diagnostic_candidate_line(
                sequence=5,
                target="ShooterGameMode.CheckJoinInProgress",
                reason=LIFECYCLE_PROPERTY_FNAME_DRIFT_REASON,
            ),
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assert_sdk_p0_runtime_public_evidence_blocked(report)
        self.assertTrue(report["strict_lifecycle_triplet_selected"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        self.assertIn("source_summary_copied_log_contains_diagnostic_lifecycle_lines", report["blockers"])
        self.assertIn("source_summary_copied_log_contains_diagnostic_candidates", report["blockers"])
        self.assertIn("runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence", report["blockers"])
        self.assertIn(
            "runtime_summary_lifecycle_property_fname_mismatch_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_lifecycle_property_fname_drift_not_approved_lifecycle_evidence",
            report["blockers"],
        )

    def test_rejects_nonzero_check_join_diagnostic_summary_with_aggregate_counters_zero(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["diagnostic_candidate_count"] = 0
        module["diagnostic_candidate_reason_counts"] = {}
        module["diagnostic_candidate_read_status_counts"] = {}
        module["diagnostic_candidate_target_counts"] = {}
        module["diagnostic_check_join_in_progress_summary"].update(
            {
                "count": 1,
                "shape_counts": {"ShooterGameMode.CheckJoinInProgress(1,0)": 1},
                "copy_status_counts": {"rejected": 1},
                "strict_shape_candidate_count": 1,
                "strict_shape_copy_rejected_count": 1,
                "latest_strict_shape_candidate": {
                    "sequence": 4,
                    "target": "ShooterGameMode.CheckJoinInProgress",
                    "strict_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
                    "evidence_claim": "none",
                    "approved_runtime_evidence": False,
                    "runtime_evidence_ready": False,
                    "readiness_gate": "none",
                },
            }
        )
        module["diagnostic_candidate_guardrails"] = [
            {
                "code": "diagnostic_check_join_in_progress_non_evidence",
                "count": 1,
                "can_promote": False,
                "required_runtime_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
            }
        ]
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assert_sdk_p0_runtime_public_evidence_blocked(report)
        self.assertIn(
            "runtime_summary_check_join_in_progress_diagnostic_context_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_diagnostic_guardrail_not_approved_lifecycle_evidence", report["blockers"])
        self.assertIn("runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence", report["blockers"])

    def test_accepts_standing_launch_authority_receipt_without_promoting_public_sdk(self) -> None:
        result = self.run_checker(manifest(standing_launch_authority=True))
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertEqual(report["ready_scope"], "runtime_evidence_only")
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])

    def test_rejects_approved_intake_readiness_aliases_without_promoting_public_flags(self) -> None:
        cases = (
            ("artifact_status", "sdk_ready", "artifact_status_mismatch"),
            ("artifact_status", "complete", "artifact_status_mismatch"),
            ("readiness_classification", "stable", "readiness_classification_mismatch"),
            ("readiness_classification", "public SDK ready", "readiness_classification_mismatch"),
        )
        for field, value, mismatch in cases:
            with self.subTest(field=field, value=value):
                payload = manifest()
                payload[field] = value
                payload.pop("output_artifact_identity")
                add_output_artifact_identity(payload)

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assert_runtime_evidence_and_public_readiness_blocked(report)
                self.assertIn(mismatch, report["blockers"])
                self.assertIn("approved_evidence_intake_alias_not_allowed", report["blockers"])
                self.assertEqual(report["ready_scope"], "runtime_evidence_only")
                self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_diagnostic_only_evidence_claim_none_never_satisfies_approved_evidence(self) -> None:
        lines = [
            *runtime_posture_lines_without_lifecycle_observer(),
            "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
            "target_set=players-lifecycle-anchor-candidates limit=10 "
            "params_logged=false identity_logged=false evidence_claim=none principal_claim=none.",
            diagnostic_candidate_line(
                sequence=1,
                target="ShooterGameMode.HandleNewPlayer",
                reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
            ),
            diagnostic_candidate_line(
                sequence=2,
                target="ShooterGameMode.OnLogout",
                reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
            ),
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_diagnostic_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_complete_lifecycle_event_triplet_missing",
            report["blockers"],
        )
        self.assertEqual(
            report["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertIn(
            "source_summary_copied_log_diagnostic_only_not_approved_lifecycle_evidence",
            report["non_evidence_reasons"],
        )
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["non_evidence_reasons"],
        )
        self.assertEqual(report["observed_runtime_cases"], [])

    def test_real_event_triplet_only_advances_to_identity_public_contract_gate(self) -> None:
        log_path = self.write_copied_log(runtime_log_lines())

        result = self.run_checker(manifest_for_copied_log(log_path))
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertEqual(report["ready_scope"], "runtime_evidence_only")
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["remaining_blockers"], [])
        self.assert_public_runtime_v1_complete_sdk_flags_false(report)
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertEqual(report["non_evidence_reasons"], [])
        self.assertEqual(report["artifact_path_issues"], [])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_lifecycle_events_without_log_timestamp_window_proof(self) -> None:
        lines = [
            re.sub(r"^\[[^\]]+\]\s+", "", line)
            if "PlayerPrincipalLifecycleObserver event" in line
            else line
            for line in runtime_log_lines()
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("source_summary_copied_log_lifecycle_event_timestamp_missing", report["blockers"])
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_roles_not_in_actual_capture_window",
            report["blockers"],
        )

    def test_rejects_lifecycle_events_without_status_proof_fields(self) -> None:
        lines = [
            without_lifecycle_status_proof_fields(line)
            if "PlayerPrincipalLifecycleObserver event" in line
            else line
            for line in runtime_log_lines()
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_status_proof_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_roles_not_in_actual_capture_window",
            report["blockers"],
        )

    def test_rejects_compact_equivalent_copied_log_event_with_full_shape_overclaim(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        lines = copied_log.read_text(encoding="utf-8").splitlines()
        tampered = [
            line.replace("delivery_claim=none.", "delivery_claim=runtime_evidence.")
            if "role=session_start_rejected" in line
            else line
            for line in lines
        ]
        copied_log.write_text("\n".join(tampered) + "\n", encoding="utf-8")
        tampered_sha = hashlib.sha256(copied_log.read_bytes()).hexdigest()
        payload["source_summary"]["evidence"]["sources"][0]["sha256"] = tampered_sha
        payload["operational_window"]["copied_log"]["sha256"] = tampered_sha
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_full_shape_mismatch",
            report["blockers"],
        )
        mismatch_detail = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "source_summary_copied_log_lifecycle_event_full_shape_mismatch"
        )
        self.assertEqual(
            mismatch_detail["mismatches"]["delivery_claim"]["actual"],
            "runtime_evidence",
        )
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_unapproved_shape",
            report["blockers"],
        )
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_lifecycle_events_outside_actual_capture_window(self) -> None:
        lines = [
            re.sub(r"^\[[^\]]+\]", "[2026-06-01T11:59:00Z]", line)
            if "PlayerPrincipalLifecycleObserver event" in line
            else line
            for line in runtime_log_lines()
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("source_summary_copied_log_lifecycle_event_outside_actual_capture_window", report["blockers"])
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_roles_not_in_actual_capture_window",
            report["blockers"],
        )

    def test_rejects_clock_only_lifecycle_event_timestamps(self) -> None:
        clocks = iter(("[12:02:00]", "[12:03:00]", "[12:04:00]"))
        lines = []
        for line in runtime_log_lines():
            if "PlayerPrincipalLifecycleObserver event" in line:
                lines.append(re.sub(r"^\[[^\]]+\]", next(clocks), line, count=1))
            else:
                lines.append(line)
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("source_summary_copied_log_lifecycle_event_timestamp_not_utc", report["blockers"])
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_roles_not_in_actual_capture_window",
            report["blockers"],
        )

    def test_rejects_non_utc_timezone_lifecycle_event_timestamps(self) -> None:
        lines = [
            re.sub(r"^\[2026-06-01T12:", "[2026-06-01T14:", line, count=1).replace("Z]", "+02:00]", 1)
            if "PlayerPrincipalLifecycleObserver event" in line
            else line
            for line in runtime_log_lines()
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("source_summary_copied_log_lifecycle_event_timestamp_not_utc", report["blockers"])
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_roles_not_in_actual_capture_window",
            report["blockers"],
        )

    def test_strict_selector_selects_duplicate_start_end_context_without_accepting(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_duplicate_context")
        cases = [
            {
                "sequence": 1,
                "target": "ShooterGameMode.HandleNewPlayer",
                "role": "session_start",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "1"],
                "principal_action": "candidate_created",
                "apply_status": "session_start_created",
                "correlation_status": "not_applicable",
            },
            {
                "sequence": 2,
                "target": "ShooterGameMode.HandleNewPlayer",
                "role": "session_start",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "1"],
                "principal_action": "candidate_created",
                "apply_status": "session_start_created",
                "correlation_status": "not_applicable",
            },
            {
                "sequence": 3,
                "target": "ShooterGameMode.CheckJoinInProgress",
                "role": "session_start_rejected",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "principal_action": "none",
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
            {
                "sequence": 4,
                "target": "ShooterGameMode.OnLogout",
                "role": "session_end",
                "copied_bool_fields": [],
                "copied_bool_values": [],
                "principal_action": "candidate_invalidated",
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            },
            {
                "sequence": 5,
                "target": "ShooterGameMode.OnLogout",
                "role": "session_end",
                "copied_bool_fields": [],
                "copied_bool_values": [],
                "principal_action": "candidate_invalidated",
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            },
        ]

        selection = checker.strict_lifecycle_triplet_selection(cases)

        self.assertTrue(selection["selected"])
        self.assertFalse(selection["accepted"])
        self.assertTrue(selection["selected_context_only"])
        self.assertEqual(selection["status"], "selected_with_duplicate_start_end_context")
        self.assertEqual(selection["selected_sequences"], [2, 3, 4])
        self.assertEqual(selection["non_counting_context_event_count"], 2)
        self.assertEqual(selection["non_counting_context_roles"], ["session_start", "session_end"])

    def test_strict_selector_accepts_gapped_increasing_sequences(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_gapped_sequence")
        cases = [
            {
                "sequence": 1,
                "target": "ShooterGameMode.HandleNewPlayer",
                "role": "session_start",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "1"],
                "principal_action": "candidate_created",
                "apply_status": "session_start_created",
                "correlation_status": "not_applicable",
            },
            {
                "sequence": 3,
                "target": "ShooterGameMode.CheckJoinInProgress",
                "role": "session_start_rejected",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "principal_action": "none",
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
            {
                "sequence": 4,
                "target": "ShooterGameMode.OnLogout",
                "role": "session_end",
                "copied_bool_fields": [],
                "copied_bool_values": [],
                "principal_action": "candidate_invalidated",
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            },
        ]

        selection = checker.strict_lifecycle_triplet_selection(cases)

        self.assertTrue(selection["accepted"])
        self.assertEqual(selection["status"], "selected")
        self.assertEqual(selection["selected_sequences"], [1, 3, 4])
        self.assertEqual(
            selection["selected_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(selection["blockers"], [])
        self.assertEqual(selection["candidate_count"], 1)
        self.assertEqual(selection["non_counting_context_event_count"], 0)

    def test_rejects_duplicate_start_end_context_as_non_exact_runtime_evidence(self) -> None:
        lines = runtime_log_lines_with_duplicate_start_end_context()
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("runtime_summary_strict_lifecycle_triplet_not_selected", report["blockers"])
        self.assertIn(
            "source_summary_copied_log_strict_lifecycle_triplet_not_selected",
            report["blockers"],
        )
        selection = report["strict_lifecycle_triplet_selection"]
        self.assertEqual(selection["status"], "selected_with_duplicate_start_end_context")
        self.assertTrue(selection["selected"])
        self.assertFalse(selection["accepted"])
        self.assertTrue(selection["selected_context_only"])
        self.assertEqual(selection["non_counting_context_event_count"], 2)
        self.assertEqual(selection["non_counting_context_roles"], ["session_start", "session_end"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_ragnarok_duplicate_start_diagnostic_missing_check_join_shape(self) -> None:
        lines = runtime_log_lines_with_ragnarok_duplicate_start_diagnostic_missing_check_join()
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("source_summary_copied_log_contains_diagnostic_candidates", report["blockers"])
        self.assertIn(
            "runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_strict_rejected_start_missing", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        self.assertTrue(report["partial_start_end_present"])
        self.assertTrue(report["missing_strict_rejected_start"])
        self.assertEqual(
            report["strict_rejected_start_expected_shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertIsNone(report["strict_rejected_start_observed_shape"])
        self.assertIn(
            "source_summary_copied_log_contains_diagnostic_candidates",
            report["non_evidence_reasons"],
        )

    def test_rejects_missing_complete_lifecycle_triplet_flag(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["complete_lifecycle_event_triplet_candidate_present"] = False
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "runtime_summary_complete_lifecycle_event_triplet_missing",
            report["blockers"],
        )

    def test_rejects_passive_snapshot_manifest_as_approved_runtime_evidence(self) -> None:
        passive_snapshot = {
            "schema": "obelisk.player-principal-passive-snapshot.v1",
            "captured_at_utc": "2026-06-04T05:00:00Z",
            "target_count": 1,
            "targets": [
                {
                    "instance": "arkserver",
                    "map": "Ragnarok",
                    "copy_status": "copied",
                    "approved_runtime_evidence": False,
                    "readiness_gate": "none",
                }
            ],
            "monitor_log": {"copy_status": "copied", "copied_path": "passive-monitor.log"},
            "players": "1/70",
            "player_presence_detected": True,
            "diagnostic_candidates": [
                {
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "reason": LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
                    "accepted_lifecycle_event": False,
                }
            ],
            "approved_runtime_evidence": False,
            "ready": False,
            "readiness_gate": "none",
            "non_claims": ["passive copied-log snapshot only"],
        }

        result = self.run_checker(passive_snapshot, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("passive_snapshot_manifest_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["passive_snapshot_manifest_is_not_approved_runtime_evidence"],
        )
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])

    def test_rejects_passive_snapshot_diff_as_approved_runtime_evidence(self) -> None:
        passive_diff = {
            "schema": "obelisk.player-principal-passive-snapshot-diff.v1",
            "auto_selected_latest_diff": True,
            "classification": "diagnostic_only_non_evidence",
            "approved_runtime_evidence": False,
            "ready": False,
            "base_manifest": "passive-detect-20260604T084705Z-arkserver-3198398/manifest.json",
            "candidate_manifest": "passive-manual-20260604T085119Z-arkserver+arkserver2-3215640/manifest.json",
            "delta": {
                "accepted": 0,
                "diagnostic_candidates": 2,
                "rejected": 0,
            },
            "non_claims": [
                "passive snapshot diff only",
                "does not satisfy approved runtime evidence",
            ],
        }

        result = self.run_checker(passive_diff, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("passive_snapshot_diff_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["passive_snapshot_diff_is_not_approved_runtime_evidence"],
        )
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])

    def test_rejects_window_request_manifest_as_approved_runtime_evidence(self) -> None:
        request_artifact = {
            "schema": "obelisk.player-principal-lifecycle-window-request.v1",
            "status": "candidate_only_request_pack",
            "ready": True,
            "run_id": RUN_ID,
            "request_pack_counts_as_approved_runtime_evidence": True,
        }

        result = self.run_checker(request_artifact, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("window_request_manifest_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["window_request_manifest_is_not_approved_runtime_evidence"],
        )
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])

    def test_rejects_closure_request_manifest_as_approved_runtime_evidence(self) -> None:
        closure_request = {
            "schema": "obelisk.player-principal-lifecycle-evidence-closure-request.v1",
            "status": "accepted",
            "artifact_status": "approved_runtime_observer_summary",
            "readiness_classification": "runtime_evidence_only",
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "next_blocker": "identity_public_contract_gate_missing",
        }

        result = self.run_checker(closure_request, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("closure_request_manifest_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["closure_request_manifest_is_not_approved_runtime_evidence"],
        )
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])

    def test_rejects_runtime_observer_summary_as_direct_approved_runtime_evidence(self) -> None:
        runtime_summary = {
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
        }

        result = self.run_checker(runtime_summary, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("runtime_observer_summary_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["runtime_observer_summary_is_not_approved_runtime_evidence"],
        )
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])

    def test_rejects_multi_surface_beta_capture_plan_as_approved_runtime_evidence(self) -> None:
        plan = {
            "schema": "obelisk.multi-surface-beta-capture-plan.v1",
            "status": "candidate_capture_plan",
            "required_primary_evidence": {
                "surface": "player_principal_lifecycle",
                "strict_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
                "must_be_checker_accepted": True,
            },
            "capture_surfaces": [
                {
                    "id": "player_principal_lifecycle",
                    "candidate_capture_only": True,
                    "requires_checker_acceptance": True,
                    "replaces_player_principal_triplet": False,
                }
            ],
            "non_claim_flags": {
                "candidate_only": True,
                "counts_as_approved_runtime_evidence": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
            },
        }

        result = self.run_checker(plan, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("multi_surface_beta_capture_plan_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["multi_surface_beta_capture_plan_is_not_approved_runtime_evidence"],
        )
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")

    def test_rejects_multi_surface_beta_capture_pack_artifacts_as_approved_runtime_evidence(self) -> None:
        false_flags = {
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "publication_ready": False,
        }
        cases = (
            (
                "pack_manifest",
                {
                    "schema": "obelisk.multi-surface-beta-capture-pack.v1",
                    "status": "candidate_capture_pack",
                    "run_id": "multi-surface-beta-capture-test",
                    "artifact_names": [
                        "checker-command-matrix.json",
                        "manifest.json",
                        "multi-surface-capture-plan.json",
                        "non-claim-manifest.json",
                    ],
                    "non_claim_flags": false_flags,
                    "artifacts": [],
                },
                "multi_surface_beta_capture_pack_is_not_approved_runtime_evidence",
            ),
            (
                "checker_matrix",
                {
                    "schema": "obelisk.multi-surface-beta-capture-checker-matrix.v1",
                    "status": "candidate_only",
                    "primary_checker": {
                        "surface": "player_principal_lifecycle",
                        "strict_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
                    },
                    "surfaces": [
                        {
                            "id": "player_principal_lifecycle",
                            "candidate_capture_only": True,
                            "requires_checker_acceptance": True,
                            "replaces_player_principal_triplet": False,
                            **false_flags,
                        }
                    ],
                },
                "multi_surface_beta_capture_checker_matrix_is_not_approved_runtime_evidence",
            ),
            (
                "non_claim_manifest",
                {
                    "schema": "obelisk.multi-surface-beta-capture-non-claim-manifest.v1",
                    "status": "non_authorizing_candidate_pack",
                    "required_primary_evidence": {
                        "surface": "player_principal_lifecycle",
                        "strict_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
                    },
                    "non_claim_flags": false_flags,
                    "surface_non_claims": [
                        {
                            "id": "player_principal_lifecycle",
                            "candidate_capture_only": True,
                            "requires_checker_acceptance": True,
                            "replaces_player_principal_triplet": False,
                            **false_flags,
                        }
                    ],
                },
                "multi_surface_beta_capture_non_claim_manifest_is_not_approved_runtime_evidence",
            ),
        )
        for name, payload, expected_blocker in cases:
            with self.subTest(name=name):
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertIn("schema_mismatch", report["blockers"])
                self.assertIn(expected_blocker, report["blockers"])
                self.assertEqual(report["non_evidence_reasons"], [expected_blocker])
                self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")

    def test_rejects_principal_start_end_report_as_approved_runtime_evidence(self) -> None:
        start_end_report = {
            "schema": "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1",
            "ready": True,
            "ready_scope": "principal_start_end_runtime_evidence_only",
            "principal_start_end_runtime_evidence_present": True,
            "principal_start_end_runtime_evidence_ready": True,
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "resolved_inputs": ["runtime.lifecycle_start_end_evidence"],
        }

        result = self.run_checker(start_end_report, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertEqual(report["observed_runtime_cases"], [])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("start_end_only_evidence_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["start_end_only_evidence_is_not_approved_runtime_evidence"],
        )

    def test_rejects_public_reachability_manifest_as_approved_runtime_evidence(self) -> None:
        reachability = {
            "schema": "obelisk.player-principal-public-reachability-check.v1",
            "ready": True,
            "public_reachability_ready": True,
            "public_reachability_counts_as_approved_runtime_evidence": True,
            "approved_runtime_evidence_present": True,
        }

        result = self.run_checker(reachability, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("public_reachability_manifest_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["public_reachability_manifest_is_not_approved_runtime_evidence"],
        )
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])

    def test_rejects_passive_activity_triage_as_approved_runtime_evidence(self) -> None:
        triage = {
            "schema": "obelisk.player-principal-passive-activity-triage.v1",
            "classification": "passive_activity_triage_non_evidence",
            "active_targets": ["arkserver:Ragnarok:27015"],
            "candidate_targets_with_complete_observer_event_triplet_candidate": ["arkserver:Ragnarok:27015"],
            "approved_runtime_evidence": True,
            "ready": True,
            "route_ready": True,
        }

        result = self.run_checker(triage, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("passive_activity_triage_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(
            report["non_evidence_reasons"],
            ["passive_activity_triage_is_not_approved_runtime_evidence"],
        )
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])

    def test_rejects_active_status_summaries_as_approved_runtime_evidence(self) -> None:
        cases = (
            (
                "sdk_status_report",
                "obelisk.sdk-status-report.v1",
                "sdk_status_report_is_not_approved_runtime_evidence",
            ),
            (
                "sdk_status_side_lane_summary",
                "obelisk.sdk-status-side-lane-summary.v1",
                "sdk_status_side_lane_summary_is_not_approved_runtime_evidence",
            ),
            (
                "sdk_status_critical_path_summary",
                "obelisk.sdk-status-critical-path-summary.v1",
                "sdk_status_critical_path_summary_is_not_approved_runtime_evidence",
            ),
            (
                "post_evidence_p0_lock_simulation",
                "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1",
                "post_evidence_p0_lock_simulation_is_not_approved_runtime_evidence",
            ),
            (
                "runtime_window_plan",
                "obelisk.player-principal-lifecycle-runtime-window-plan.v1",
                "next_action_plan_is_not_approved_runtime_evidence",
            ),
            (
                "runtime_window_execution",
                "obelisk.player-principal-lifecycle-runtime-window-execution.v1",
                "runtime_window_execution_is_not_approved_runtime_evidence",
            ),
            (
                "runtime_window_post_window_state",
                "obelisk.player-principal-lifecycle-runtime-window-post-window-state.v1",
                "runtime_window_post_window_state_is_not_approved_runtime_evidence",
            ),
            (
                "runtime_evidence_status_report",
                "obelisk.player-principal-lifecycle-runtime-evidence-status.v1",
                "runtime_evidence_status_report_is_not_approved_runtime_evidence",
            ),
            (
                "public_sdk_completion_check",
                "obelisk.public-sdk-v1-completion-check.v1",
                "public_sdk_completion_check_is_not_approved_runtime_evidence",
            ),
            (
                "public_sdk_completion_summary",
                "obelisk.public-sdk-v1-completion-summary.v1",
                "public_sdk_completion_summary_is_not_approved_runtime_evidence",
            ),
            (
                "public_sdk_fastest_next_unblock",
                "obelisk.public-sdk-v1-fastest-next-unblock.v1",
                "public_sdk_fastest_next_unblock_is_not_approved_runtime_evidence",
            ),
            (
                "public_sdk_progress_normalization_trace",
                "obelisk.public-sdk-v1-progress-normalization-trace.v1",
                "public_sdk_progress_normalization_trace_is_not_approved_runtime_evidence",
            ),
            (
                "public_sdk_approved_in_game_evidence_status",
                "obelisk.public-sdk-v1-approved-in-game-evidence-status.v1",
                "public_sdk_approved_in_game_evidence_status_is_not_approved_runtime_evidence",
            ),
            (
                "approved_in_game_evidence_status",
                "obelisk.approved-in-game-evidence-status.v1",
                "approved_in_game_evidence_status_is_not_approved_runtime_evidence",
            ),
            (
                "public_contract_decisions",
                "obelisk.player-identity-public-contract-decisions.v1",
                "contract_review_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "public_contract_decision_record",
                "obelisk.player-identity-public-contract-decision-record.v1",
                "contract_review_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "public_contract_gap_report",
                "obelisk.player-identity-public-contract-gap-report.v1",
                "contract_review_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "passive_target_triplet",
                "obelisk.player-principal-passive-target-triplet-candidate-summary.v1",
                "passive_target_triplet_is_not_approved_runtime_evidence",
            ),
            (
                "passive_monitor_only_summary",
                "obelisk.player-principal-passive-monitor-only-summary.v1",
                "passive_monitor_only_summary_is_not_approved_runtime_evidence",
            ),
            (
                "passive_extended_monitor_triage",
                "obelisk.player-principal-passive-extended-monitor-triage.v1",
                "passive_extended_monitor_triage_is_not_approved_runtime_evidence",
            ),
            (
                "scoped_release_statement",
                "obelisk.scoped-release-statement-outcomes.v1",
                "scoped_release_statement_is_not_approved_runtime_evidence",
            ),
            (
                "installed_sdk_package_shape",
                "obelisk.installed-sdk-package-shape.v1",
                "installed_sdk_package_shape_is_not_approved_runtime_evidence",
            ),
            (
                "generic_player_notice_action",
                "obelisk.player-notice-action.v1",
                "player_notice_action_is_not_approved_runtime_evidence",
            ),
            (
                "beta_notice_authority_boundary",
                "obelisk.player-principal-lifecycle-beta-notice-authority-boundary.v1",
                "beta_notice_authority_boundary_is_not_approved_runtime_evidence",
            ),
            (
                "discord_active_notice_state",
                "obelisk.discord-beta-bridge-active-notice.v1",
                "discord_bridge_state_is_not_approved_runtime_evidence",
            ),
            (
                "ready_log_copy",
                "obelisk.player-principal-lifecycle-ready-log-copy.v1",
                "ready_log_copy_is_not_approved_runtime_evidence",
            ),
        )
        for name, schema, expected_blocker in cases:
            with self.subTest(name=name):
                active_status_summary = {
                    "schema": schema,
                    "status_report_only": True,
                    "active_player_principal_paths": {
                        "ragnarok": {
                            "path_status": "active_ragnarok_complete_passive_triplet_needs_approved_bundle",
                            "approved_bundle_required": True,
                        }
                    },
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "public_sdk_ready": True,
                    "runtime_ready": True,
                }

                result = self.run_checker(active_status_summary, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertIn("schema_mismatch", report["blockers"])
                self.assertIn(expected_blocker, report["blockers"])
                self.assertEqual(report["non_evidence_reasons"], [expected_blocker])
                self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])

    def test_rejects_blocked_status_report_with_zero_source_overclaim_count(self) -> None:
        status_report = {
            "schema": "obelisk.sdk-status-report.v1",
            "status_report_only": True,
            "status": "blocked",
            "ready": False,
            "current_route_blocker": "approved_runtime_evidence_missing",
            "source_overclaim_total_flag_count": 0,
            "source_overclaim_summary": {
                "total": 0,
                "readiness_flags": [],
                "count_flags": [],
            },
            "approved_runtime_evidence_present": False,
            "runtime_evidence_ready": False,
            "complete_sdk_progress_ratio": "0/12",
            "p0_dependency_chain_progress_ratio": "0/4",
        }

        result = self.run_checker(status_report, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("sdk_status_report_is_not_approved_runtime_evidence", report["blockers"])
        self.assertEqual(report["non_evidence_reasons"], ["sdk_status_report_is_not_approved_runtime_evidence"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")

    def test_rejects_unknown_non_evidence_alias_schemas_and_names_required_bundle(self) -> None:
        cases = (
            (
                "next_action_plan",
                "obelisk.player-principal-lifecycle-next-action-plan.v1",
                "next_action_plan_schema_is_not_approved_runtime_evidence",
            ),
            (
                "progress_normalization_trace",
                "obelisk.public-sdk-progress-normalization-trace-snapshot.v1",
                "progress_or_source_overclaim_trace_is_not_approved_runtime_evidence",
            ),
            (
                "source_bound_fname_drift_manifest",
                "obelisk.player-principal-source-bound-fname-drift-manifest.v1",
                "source_bound_drift_manifest_is_not_approved_runtime_evidence",
            ),
            (
                "passive_triplet",
                "obelisk.player-principal-passive-complete-triplet-rollup.v1",
                "passive_or_triplet_schema_is_not_approved_runtime_evidence",
            ),
            (
                "notice_action",
                "obelisk.player-principal-notice-action-summary.v1",
                "notice_action_schema_is_not_approved_runtime_evidence",
            ),
            (
                "public_reachability",
                "obelisk.player-principal-public-query-reachability.v1",
                "public_reachability_schema_is_not_approved_runtime_evidence",
            ),
            (
                "status_summary",
                "obelisk.player-principal-route-status-summary.v1",
                "status_summary_schema_is_not_approved_runtime_evidence",
            ),
            (
                "release_readiness_pass",
                "obelisk.release-readiness-pass-output.v1",
                "release_readiness_schema_is_not_approved_runtime_evidence",
            ),
            (
                "package_shape_install",
                "obelisk.package-shape-install-success.v1",
                "package_shape_or_install_schema_is_not_approved_runtime_evidence",
            ),
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
                "generated_approved_bundle",
                "obelisk.generated-approved-bundle.v1",
                "generated_artifact_or_bundle_schema_is_not_approved_runtime_evidence",
            ),
            (
                "historical_candidate",
                "obelisk.historical-theisland-candidate-path.v1",
                "historical_or_candidate_schema_is_not_approved_runtime_evidence",
            ),
            (
                "future_multi_surface_beta_capture_pack",
                "obelisk.future-multi-surface-beta-capture-pack.v1",
                "multi_surface_beta_capture_schema_is_not_approved_runtime_evidence",
            ),
            (
                "candidate_queue",
                "obelisk.player-principal-candidate-queue.v1",
                "candidate_queue_schema_is_not_approved_runtime_evidence",
            ),
            (
                "debug_capture",
                "obelisk.player-principal-debug-capture-bundle.v1",
                "debug_capture_schema_is_not_approved_runtime_evidence",
            ),
            (
                "start_end_only",
                "obelisk.player-principal-start-end-only-artifact.v1",
                "start_end_only_schema_is_not_approved_runtime_evidence",
            ),
            (
                "checkjoin_candidate",
                "obelisk.player-principal-checkjoininprogress-candidate-acceptance.v1",
                "rejected_start_candidate_schema_is_not_approved_runtime_evidence",
            ),
            (
                "checkjoin_bool_order",
                "obelisk.player-principal-checkjoin-bool-order.v1",
                "rejected_start_candidate_schema_is_not_approved_runtime_evidence",
            ),
            (
                "session_start_rejected_offline",
                "obelisk.player-principal-session-start-rejected-offline-acceptance.v1",
                "rejected_start_candidate_schema_is_not_approved_runtime_evidence",
            ),
            (
                "request_pack_alias",
                "obelisk.player-principal-lifecycle-request-pack-ready.v1",
                "request_pack_or_approval_sidecar_schema_is_not_approved_runtime_evidence",
            ),
            (
                "standing_launch_authority_alias",
                "obelisk.player-principal-lifecycle-standing-launch-authority-artifact.v1",
                "approval_or_standing_authority_schema_is_not_approved_runtime_evidence",
            ),
            (
                "copied_log_status_alias",
                "obelisk.player-principal-lifecycle-copied-log-status.v1",
                "copied_status_or_report_schema_is_not_approved_runtime_evidence",
            ),
            (
                "window_manifest_alias",
                "obelisk.player-principal-lifecycle-window-manifest-candidate.v1",
                "window_manifest_alias_schema_is_not_approved_runtime_evidence",
            ),
            (
                "contract_review_alias",
                "obelisk.player-identity-public-contract-review-alias.v1",
                "contract_review_artifact_schema_is_not_approved_runtime_evidence",
            ),
        )
        for name, schema, expected_blocker in cases:
            with self.subTest(name=name):
                result = self.run_checker(
                    {
                        "schema": schema,
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                        "ready": True,
                    },
                    check=False,
                )
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertIn("schema_mismatch", report["blockers"])
                self.assertIn(expected_blocker, report["blockers"])
                self.assertIn(expected_blocker, report["non_evidence_reasons"])
                self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
                self.assertEqual(
                    report["next_required_artifact"],
                    "approved_runtime_principal_lifecycle_evidence_bundle",
                )
                self.assertEqual(
                    report["missing_required_artifact"],
                    "approved_runtime_principal_lifecycle_evidence_bundle",
                )
                self.assertEqual(report["required_artifact_status"], "missing_or_not_accepted")
                action = report["fastest_next_action"]
                self.assertEqual(
                    action["action"],
                    "create_checker_accepted_approved_runtime_principal_lifecycle_evidence_bundle",
                )
                self.assertEqual(action["current_route_blocker"], "approved_runtime_evidence_missing")
                self.assertEqual(action["sdk_p0_progress_before_checker_accepted_bundle"], "0")
                self.assertEqual(
                    [case["role"] for case in action["required_copied_log_lifecycle_sequence"]],
                    ["session_start", "session_start_rejected", "session_end"],
                )
                self.assertEqual(
                    action["required_copied_log_lifecycle_sequence"][1]["shape"],
                    "ShooterGameMode.CheckJoinInProgress(1,0)",
                )
                self.assertEqual(
                    action["required_copied_log_lifecycle_sequence"][2]["safe_status_proof"],
                    {
                        "apply_status": "session_end_invalidated",
                        "correlation_status": "matched",
                    },
                )
                self.assertIn("operator-approval-receipt.json", action["required_sibling_sidecars"])

    def test_rejects_historical_candidate_input_path_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "historical-theisland-candidate-status.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.unclassified-artifact.v1",
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker_file(path, check=False)

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn(
            "input_path_historical_or_candidate_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "input_path_status_summary_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "input_path_historical_or_candidate_is_not_approved_runtime_evidence",
            report["non_evidence_reasons"],
        )
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            report["missing_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )

    def test_rejects_handoff_and_cleanup_input_path_aliases(self) -> None:
        cases = (
            ("compact-context-checkpoint.json", "input_path_handoff_or_cleanup_checkpoint_is_not_approved_runtime_evidence"),
            (".codex-cleanup-report.json", "input_path_handoff_or_cleanup_checkpoint_is_not_approved_runtime_evidence"),
            ("package-shape-install-success.json", "input_path_package_shape_or_install_is_not_approved_runtime_evidence"),
            ("progress-normalization-trace.json", "input_path_progress_or_source_overclaim_trace_is_not_approved_runtime_evidence"),
            ("source-bound-fname-drift-manifest.json", "input_path_source_bound_drift_manifest_is_not_approved_runtime_evidence"),
            ("generated-approved-bundle.json", "input_path_generated_artifact_or_bundle_is_not_approved_runtime_evidence"),
            ("next-action-plan.json", "input_path_next_action_plan_is_not_approved_runtime_evidence"),
            ("request-pack-ready.json", "input_path_request_pack_or_approval_sidecar_is_not_approved_runtime_evidence"),
            ("window-manifest-candidate.json", "input_path_window_manifest_alias_is_not_approved_runtime_evidence"),
            (
                "reviewed-identity-public-contract-decision-record.json",
                "input_path_contract_review_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "multi-surface-beta-capture-candidate-queue.json",
                "input_path_multi_surface_beta_capture_is_not_approved_runtime_evidence",
            ),
            ("manifest.json", "input_path_candidate_manifest_artifact_is_not_approved_runtime_evidence"),
            (
                "checker-command-matrix.json",
                "input_path_multi_surface_beta_capture_checker_matrix_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "non-claim-manifest.json",
                "input_path_multi_surface_beta_capture_non_claim_manifest_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "multi-surface-capture-plan.json",
                "input_path_multi_surface_beta_capture_plan_artifact_is_not_approved_runtime_evidence",
            ),
            ("player-principal-debug-capture-bundle.json", "input_path_debug_capture_is_not_approved_runtime_evidence"),
            ("principal-start-end-evidence.check.json", "input_path_start_end_only_is_not_approved_runtime_evidence"),
            (
                "checkjoininprogress-offline-acceptance.json",
                "input_path_rejected_start_candidate_is_not_approved_runtime_evidence",
            ),
            (
                "checkjoin-bool-order.json",
                "input_path_rejected_start_candidate_is_not_approved_runtime_evidence",
            ),
        )
        for filename, expected_blocker in cases:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / filename
                    path.write_text(
                        json.dumps(
                            {
                                "schema": "obelisk.unclassified-artifact.v1",
                                "approved_runtime_evidence_present": True,
                                "runtime_evidence_ready": True,
                            }
                        ),
                        encoding="utf-8",
                    )

                    result = self.run_checker_file(path, check=False)
                    report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_blocker, report["blockers"])
                self.assertIn(expected_blocker, report["non_evidence_reasons"])
                self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")

    def test_rejects_non_evidence_input_path_aliases_even_with_approved_schema(self) -> None:
        cases = (
            (
                "passive-snapshot-status.json",
                (
                    "input_path_passive_or_triplet_is_not_approved_runtime_evidence",
                    "input_path_status_summary_is_not_approved_runtime_evidence",
                ),
            ),
            (
                "principal-start-end-evidence.check.json",
                ("input_path_start_end_only_is_not_approved_runtime_evidence",),
            ),
            (
                "sdk-status-report.json",
                ("input_path_status_summary_is_not_approved_runtime_evidence",),
            ),
            (
                "generated-operator-approval-receipt.json",
                ("input_path_approval_or_standing_authority_is_not_approved_runtime_evidence",),
            ),
            (
                "checkjoin-bool-order.json",
                ("input_path_rejected_start_candidate_is_not_approved_runtime_evidence",),
            ),
        )
        for filename, expected_blockers in cases:
            with self.subTest(filename=filename):
                payload = manifest()
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / filename
                    path.write_text(json.dumps(payload), encoding="utf-8")

                    result = self.run_checker_file(path, check=False)
                    report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assert_runtime_evidence_and_public_readiness_blocked(report)
                self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
                self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
                self.assertEqual(
                    report["observed_runtime_cases"],
                    ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
                )
                for expected_blocker in expected_blockers:
                    self.assertIn(expected_blocker, report["blockers"])
                    self.assertIn(expected_blocker, report["non_evidence_reasons"])

    def test_rejects_snapshot_on_detect_copied_log_wrapped_as_approved_bundle(self) -> None:
        lines = [
            *runtime_log_lines(),
            "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
            "target_set=players-lifecycle-anchor-candidates limit=10 "
            "params_logged=false identity_logged=false evidence_claim=none principal_claim=none.",
            diagnostic_check_join_in_progress_copied_bool_line(sequence=99),
        ]
        temp_dir = retained_temp_offline_workspace()
        log_path = Path(temp_dir.name) / "passive-snapshot-on-detect" / RUN_ID / "arkserver-Ragnarok-Obelisk.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "operational_window_copied_log_path_not_live_validation_run_log",
            report["blockers"],
        )
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_passive_monitor_log_file_as_manifest_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            monitor_log = Path(tmp) / "passive-monitor.log"
            monitor_log.write_text(
                "\n".join(
                    [
                        "tick utc=2026-06-04T05:00:00Z",
                        "query instance=arkserver map=Ragnarok query_port=27015 status=ok players=0/70",
                        "observer_tail instance=arkserver status=no_matching_lines scan_lines=200 limit=10",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_checker_file(monitor_log, check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid JSON", result.stderr)

    def test_rejects_passive_monitor_tail_as_copied_lifecycle_evidence(self) -> None:
        monitor_lines = [
            "tick utc=2026-06-04T05:00:00Z",
            "query instance=arkserver map=Ragnarok query_port=27015 status=ok players=1/70",
            "player_presence_detected instance=arkserver map=Ragnarok",
            "observer_tail instance=arkserver status=matched lines=1 scan_lines=200 limit=10",
            "observer instance=arkserver [info] PlayerPrincipalLifecycleObserver enabled "
            f"binary_sha256={SHA} target_set=players-lifecycle-anchor-candidates limit=10 "
            "dispatch_limit=0 delivery_claim=none principal_claim=none.",
        ]
        log_path = self.write_copied_log(monitor_lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=monitor_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("runtime_summary_observer_gate_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertEqual(report["observed_runtime_cases"], [])

    def test_rejects_passive_monitor_metadata_even_with_complete_lifecycle_events(self) -> None:
        lines = [
            "tick utc=2026-06-04T05:00:00Z",
            "query instance=arkserver map=Ragnarok query_port=27015 status=ok players=1/70",
            "player_presence_detected instance=arkserver map=Ragnarok",
            "observer_tail instance=arkserver status=matched lines=3 scan_lines=200 limit=10",
            *runtime_log_lines(),
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_contains_passive_monitor_metadata",
            report["blockers"],
        )
        self.assertIn(
            "source_summary_copied_log_contains_passive_monitor_metadata",
            report["non_evidence_reasons"],
        )
        self.assertNotIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

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
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_contains_passive_monitor_metadata",
            report["blockers"],
        )
        self.assertIn(
            "source_summary_copied_log_contains_passive_monitor_metadata",
            report["non_evidence_reasons"],
        )
        self.assertNotIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_unsafe_player_text_retained_in_copied_log(self) -> None:
        lines = [
            *runtime_log_lines(),
            "[2026-06-01T12:05:00Z] [warning] copied diagnostic retained "
            "player_name=ExamplePlayer chat_text=private-message steam_id=76561198000000000",
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_contains_unsafe_player_text",
            report["blockers"],
        )
        self.assertIn(
            "source_summary_copied_log_contains_unsafe_player_text",
            report["non_evidence_reasons"],
        )
        blocker = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "source_summary_copied_log_contains_unsafe_player_text"
        )
        self.assertEqual(blocker["unsafe_player_text_line_count"], 1)
        self.assertEqual(
            blocker["unsafe_player_text_lines"][0]["unsafe_keys"],
            ["chat_text", "player_name", "steam_id"],
        )
        blocker_json = json.dumps(blocker, sort_keys=True)
        self.assertNotIn("ExamplePlayer", blocker_json)
        self.assertNotIn("private-message", blocker_json)
        self.assertNotIn("76561198000000000", blocker_json)

    def test_rejects_passive_monitor_session_and_warning_metadata_with_complete_lifecycle_events(self) -> None:
        metadata_lines = [
            (
                "passive_monitor_session utc=2026-06-04T05:00:00Z pid=1234 ppid=1 "
                "session_id=passive-test targets=arkserver:Ragnarok target_count=1 interval=60 "
                "once=true linger_after_detect=0 snapshot_output_root=none snapshot_monitor_log=none "
                "replacement_status=none_reported active_monitor_policy=metadata_only_never_signal_stop_or_replace "
                "process_control=none"
            ),
            (
                "query_warning instance=arkserver rc=1 details_fallback=disabled "
                "map=Ragnarok query_port=27015 target_key=arkserver:Ragnarok:27015 "
                "detection_source=gamedig_ase_query"
            ),
            (
                "linuxgsm_skipped instance=arkserver commands=monitor,details reason=passive_path "
                "map=Ragnarok query_port=27015 target_key=arkserver:Ragnarok:27015"
            ),
            (
                "rcon_listplayers instance=arkserver map=Ragnarok query_port=27015 "
                "rcon_port=27020 status=ok players_current=1 target_key=arkserver:Ragnarok:27015 "
                "presence_detected=true detection_source=rcon_listplayers_redacted "
                "rcon_output_redacted=true"
            ),
            (
                "player_presence_context instance=arkserver map=Ragnarok target_key=arkserver:Ragnarok:27015 "
                "presence_detected=true query_signal=zero rcon_signal=present observer_signal=unavailable_no_log"
            ),
            "runtime_window_plan status=planned approved_runtime_evidence=false",
            "player_notice_action status=prepared player_notice_counts_as_approved_runtime_evidence=false",
            "beta_notice_sent status=confirmed approved_runtime_evidence=false",
        ]
        for metadata_line in metadata_lines:
            with self.subTest(metadata_line=metadata_line.split(" ", 1)[0]):
                lines = [metadata_line, *runtime_log_lines()]
                log_path = self.write_copied_log(lines)

                result = self.run_checker(
                    manifest_for_copied_log(log_path, log_lines=lines),
                    check=False,
                )
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assert_runtime_evidence_and_public_readiness_blocked(report)
                self.assertIn(
                    "source_summary_copied_log_contains_passive_monitor_metadata",
                    report["blockers"],
                )
                self.assertNotIn("source_summary_not_derived_from_copied_log", report["blockers"])
                self.assertEqual(
                    report["observed_runtime_cases"],
                    ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
                )

    def test_rejects_observer_gate_only_log_as_approved_lifecycle_evidence(self) -> None:
        gate_only_lines = [
            line
            for line in runtime_log_lines()
            if "PlayerPrincipalLifecycleObserver event " not in line
        ]
        log_path = self.write_copied_log(gate_only_lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=gate_only_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "runtime_summary_observer_gate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        self.assertEqual(report["observed_runtime_cases"], ["observer_enable"])

    def test_rejects_query_player_presence_only_bundle_as_approved_lifecycle_evidence(self) -> None:
        query_presence_lines = [
            *runtime_posture_lines_without_lifecycle_observer(),
            "query instance=arkserver map=Ragnarok query_port=27015 status=ok players=1/70",
            "player_presence_detected instance=arkserver map=Ragnarok",
            "observer_tail instance=arkserver status=no_matching_lines scan_lines=200 limit=10",
        ]
        log_path = self.write_copied_log(query_presence_lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=query_presence_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("player_principal_lifecycle_module_missing", report["blockers"])
        self.assertNotIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(report["observed_runtime_cases"], [])

    def test_rejects_observer_gate_presence_and_diagnostics_without_lifecycle_events(self) -> None:
        lines = [
            line
            for line in runtime_log_lines()
            if "PlayerPrincipalLifecycleObserver event " not in line
        ]
        lines.extend(
            [
                "query instance=arkserver map=Ragnarok query_port=27015 status=ok players=1/70",
                "player_presence_detected instance=arkserver map=Ragnarok",
                diagnostic_candidate_line(
                    sequence=1,
                    target="ShooterGameMode.HandleNewPlayer",
                    reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
                ),
                diagnostic_candidate_line(
                    sequence=2,
                    target="ShooterGameMode.OnLogout",
                    reason=LIFECYCLE_PROPERTY_FNAME_DRIFT_REASON,
                ),
            ]
        )
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_diagnostic_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])
        self.assertEqual(report["observed_runtime_cases"], ["observer_enable"])

    def test_rejects_partial_session_lifecycle_event_bundles(self) -> None:
        cases = {
            "session_start": ["observer_enable"],
            "session_start_rejected": ["observer_enable"],
            "session_end": ["observer_enable"],
        }
        for omitted_role, observed_cases in cases.items():
            with self.subTest(omitted_role=omitted_role):
                partial_lines = [
                    line
                    for line in runtime_log_lines()
                    if f"role={omitted_role} " not in line
                ]
                log_path = self.write_copied_log(partial_lines)

                result = self.run_checker(
                    manifest_for_copied_log(log_path, log_lines=partial_lines),
                    check=False,
                )
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assert_runtime_evidence_and_public_readiness_blocked(report)
                self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
                self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
                self.assertIn(
                    "source_summary_copied_log_lifecycle_event_roles_not_in_actual_capture_window",
                    report["blockers"],
                )
                self.assertNotIn("source_summary_not_derived_from_copied_log", report["blockers"])
                self.assertEqual(report["observed_runtime_cases"], observed_cases)

    def test_rejects_old_format_lifecycle_lines_without_status_proof_fields(self) -> None:
        lines = [without_lifecycle_status_proof_fields(line) for line in runtime_log_lines()]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_complete_lifecycle_event_triplet_missing", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        self.assertNotIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(report["observed_runtime_cases"], ["observer_enable"])

    def test_rejects_old_format_lifecycle_line_mixed_with_complete_lifecycle_events(self) -> None:
        old_session_end = without_lifecycle_status_proof_fields(runtime_log_lines()[-1]).replace(
            "sequence=3",
            "sequence=4",
        )
        lines = [*runtime_log_lines(), old_session_end]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])
        self.assertNotIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_status_proof_mutated_copied_log_lifecycle_event(self) -> None:
        lines = [
            line.replace(
                "apply_status=session_end_invalidated correlation_status=matched",
                "apply_status=session_end_unresolved_noop correlation_status=missing",
            )
            for line in runtime_log_lines()
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        self.assertNotIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable"],
        )

    def test_reports_session_end_missing_correlation_only_next_action_without_evidence_claim(self) -> None:
        lines = runtime_log_lines_with_only_missing_correlation_session_end()
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        diagnostics = report["session_end_missing_correlation_diagnostics"]
        self.assertEqual(
            diagnostics["classification"],
            "session_end_missing_correlation_only_non_evidence",
        )
        self.assertEqual(diagnostics["roles_present"], ["session_end"])
        self.assertEqual(
            diagnostics["missing_accepted_lifecycle_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertFalse(diagnostics["approved_runtime_evidence"])
        self.assertFalse(diagnostics["counts_as_approved_runtime_evidence"])
        action_diagnostics = report["fastest_next_action"]["session_end_missing_correlation_diagnostics"]
        self.assertEqual(action_diagnostics["copied_log_material"], "session_end_only_without_matched_correlation")
        self.assertEqual(
            action_diagnostics["required_next_material"]["required_session_end_status_proof"],
            {
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            },
        )
        self.assertFalse(
            action_diagnostics["required_next_material"][
                "session_end_correlation_status_missing_counts_as_evidence"
            ]
        )

    def test_rejects_runtime_diagnostic_candidate_mixed_with_complete_lifecycle_events(self) -> None:
        diagnostic = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=99 "
            "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
            "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
            "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
            "evidence_claim=none."
        )
        lines = [*runtime_log_lines(), diagnostic]
        log_path = self.write_copied_log(lines)
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("source_summary_copied_log_contains_diagnostic_candidates", report["blockers"])
        self.assertIn("runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_diagnostic_compact_chain_line_mixed_with_complete_lifecycle_events(self) -> None:
        diagnostic = diagnostic_compact_chain_line(sequence=99)
        lines = [*runtime_log_lines(), diagnostic]
        log_path = self.write_copied_log(lines)
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_contains_diagnostic_lifecycle_lines",
            report["blockers"],
        )
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])
        self.assertIn(
            "source_summary_copied_log_contains_diagnostic_lifecycle_lines",
            report["non_evidence_reasons"],
        )
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_diagnostic_compact_chain_triplet_as_lifecycle_evidence(self) -> None:
        lines = [
            line
            for line in runtime_log_lines()
            if "PlayerPrincipalLifecycleObserver event " not in line
        ]
        lines.extend(
            [
                diagnostic_compact_chain_line(sequence=1),
                diagnostic_compact_chain_line(
                    sequence=2,
                    target="ShooterGameMode.CheckJoinInProgress",
                    role="session_start_rejected",
                    copied_bool_values="1,0",
                    principal_action="none",
                    apply_status="session_start_rejected_noop",
                    correlation_status="not_applicable",
                ),
                diagnostic_compact_chain_line(
                    sequence=3,
                    target="ShooterGameMode.OnLogout",
                    role="session_end",
                    copied_bool_fields="none",
                    copied_bool_values="none",
                    principal_action="candidate_invalidated",
                    apply_status="session_end_invalidated",
                    correlation_status="matched",
                ),
            ]
        )
        log_path = self.write_copied_log(lines)
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_contains_diagnostic_lifecycle_lines",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        self.assertIn(
            "source_summary_copied_log_lifecycle_event_roles_not_in_actual_capture_window",
            report["blockers"],
        )
        self.assertEqual(
            report["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(report["observed_runtime_cases"], ["observer_enable"])
        diagnostic_detail = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "source_summary_copied_log_contains_diagnostic_lifecycle_lines"
        )
        self.assertEqual(diagnostic_detail["diagnostic_lifecycle_line_count"], 3)

    def test_lifecycle_property_fname_drift_diagnostic_does_not_unlock_with_real_events(self) -> None:
        diagnostic = diagnostic_candidate_line(
            sequence=99,
            reason=LIFECYCLE_PROPERTY_FNAME_DRIFT_REASON,
        )
        lines = [*runtime_log_lines(), diagnostic]
        log_path = self.write_copied_log(lines)
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertIn("source_summary_copied_log_contains_diagnostic_candidates", report["blockers"])
        self.assertIn("runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_rejects_check_join_in_progress_copied_bool_diagnostic_mixed_with_complete_events(self) -> None:
        diagnostic = diagnostic_check_join_in_progress_copied_bool_line(sequence=99)
        lines = [*runtime_log_lines(), diagnostic]
        log_path = self.write_copied_log(lines)
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("source_summary_copied_log_contains_diagnostic_candidates", report["blockers"])
        self.assertIn("runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_k2_post_login_diagnostic_mixed_with_complete_events(self) -> None:
        diagnostic = diagnostic_k2_post_login_line(sequence=99)
        lines = [*runtime_log_lines(), diagnostic]
        log_path = self.write_copied_log(lines)
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("source_summary_copied_log_contains_diagnostic_candidates", report["blockers"])
        self.assertIn("runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_wrapped_summary_with_diagnostic_only_functions_spliced_in(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["functions"]["GameMode.K2_PostLogin"] = {
            "accepted": 1,
            "metadata_only": 0,
            "fname_indices": [4943],
            "outer_fname_indices": [],
            "field_counts": [0],
            "details": {"diagnostic_shape": ["K2_PostLogin"]},
            "fields": {},
        }
        module["functions"]["ShooterGameMode.CheckJoinInProgress"] = {
            "accepted": 2,
            "metadata_only": 0,
            "fname_indices": [2171],
            "outer_fname_indices": [],
            "field_counts": [0],
            "details": {
                "diagnostic_shape": ["CheckJoinInProgress"],
                "copied_bool_fields": ["bIsFromLogin,ReturnValue"],
                "copied_bool_values": ["0,1", "1,1"],
            },
            "fields": {},
        }
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("runtime_summary_functions_unexpected", report["blockers"])
        self.assertIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_only_check_join_in_progress_copied_bool_diagnostic_as_approved_evidence(self) -> None:
        diagnostic_only_lines = [
            line
            for line in runtime_log_lines()
            if "PlayerPrincipalLifecycleObserver event " not in line
        ]
        diagnostic_only_lines.extend(
            [
                diagnostic_check_join_in_progress_copied_bool_line(sequence=1, copied_bool_values="1,1"),
                diagnostic_check_join_in_progress_copied_bool_line(sequence=2, copied_bool_values="0,1"),
            ]
        )
        log_path = self.write_copied_log(diagnostic_only_lines)
        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=diagnostic_only_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "runtime_summary_check_join_in_progress_diagnostic_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])

    def test_rejects_only_k2_post_login_diagnostic_as_approved_evidence(self) -> None:
        diagnostic_only_lines = [
            line
            for line in runtime_log_lines()
            if "PlayerPrincipalLifecycleObserver event " not in line
        ]
        diagnostic_only_lines.extend(
            [
                diagnostic_k2_post_login_line(sequence=1),
                diagnostic_k2_post_login_line(sequence=2),
            ]
        )
        log_path = self.write_copied_log(diagnostic_only_lines)
        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=diagnostic_only_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])

    def test_rejects_copied_log_with_only_diagnostic_candidate_lines(self) -> None:
        lines = [
            *runtime_posture_lines_without_lifecycle_observer(),
            diagnostic_candidate_line(sequence=1),
            diagnostic_candidate_line(
                sequence=2,
                target="ShooterGameMode.OnLogout",
                reason="property.metadata:unsupported-layout",
            ),
        ]
        log_path = self.write_copied_log(lines)
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_not_accepted"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)

    def test_rejects_richer_lifecycle_property_fname_mismatch_diagnostic_as_approved_evidence(self) -> None:
        diagnostic_only_lines = [
            line
            for line in runtime_log_lines()
            if "PlayerPrincipalLifecycleObserver event " not in line
        ]
        diagnostic_only_lines.extend(
            [
                diagnostic_candidate_line(
                    sequence=1,
                    target="ShooterGameMode.HandleNewPlayer",
                    reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
                ),
                diagnostic_candidate_line(
                    sequence=2,
                    target="ShooterGameMode.OnLogout",
                    reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
                ),
            ]
        )
        log_path = self.write_copied_log(diagnostic_only_lines)
        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=diagnostic_only_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_diagnostic_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])

    def test_rejects_ragnarok_presence_with_only_handle_new_player_fname_mismatch_diagnostics(self) -> None:
        diagnostic_only_lines = [
            *runtime_posture_lines_without_lifecycle_observer(),
            "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
            "target_set=players-lifecycle-anchor-candidates limit=10 "
            "params_logged=false identity_logged=false evidence_claim=none principal_claim=none.",
            "query instance=arkserver map=Ragnarok query_port=27015 status=ok players=1/70",
            "player_presence_detected instance=arkserver map=Ragnarok",
            diagnostic_candidate_line(
                sequence=1,
                target="ShooterGameMode.HandleNewPlayer",
                reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
            ),
            diagnostic_candidate_line(
                sequence=2,
                target="ShooterGameMode.HandleNewPlayer",
                reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
            ),
        ]
        log_path = self.write_copied_log(diagnostic_only_lines)
        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=diagnostic_only_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_diagnostic_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        self.assertEqual(report["observed_runtime_cases"], [])

        diagnostic_blocker = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence"
        )
        self.assertEqual(diagnostic_blocker["observed_lifecycle_event_count"], 0)
        self.assertEqual(
            diagnostic_blocker["diagnostic_reason_counts"],
            {LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON: 2},
        )

    def test_rejects_lifecycle_property_fname_drift_diagnostic_as_approved_evidence(self) -> None:
        diagnostic_only_lines = [
            line
            for line in runtime_log_lines()
            if "PlayerPrincipalLifecycleObserver event " not in line
        ]
        diagnostic_only_lines.extend(
            [
                diagnostic_candidate_line(
                    sequence=1,
                    target="ShooterGameMode.HandleNewPlayer",
                    reason=LIFECYCLE_PROPERTY_FNAME_DRIFT_REASON,
                ),
                diagnostic_candidate_line(
                    sequence=2,
                    target="ShooterGameMode.OnLogout",
                    reason=LIFECYCLE_PROPERTY_FNAME_DRIFT_REASON,
                ),
            ]
        )
        log_path = self.write_copied_log(diagnostic_only_lines)
        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=diagnostic_only_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_diagnostic_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        diagnostic_blocker = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence"
        )
        self.assertEqual(
            diagnostic_blocker["diagnostic_reason_counts"],
            {LIFECYCLE_PROPERTY_FNAME_DRIFT_REASON: 2},
        )

    def test_rejects_wrapped_summary_over_diagnostic_only_copied_log_that_mimics_required_cases(self) -> None:
        diagnostic_only_lines = [
            *runtime_posture_lines_without_lifecycle_observer(),
            diagnostic_k2_post_login_line(sequence=1),
            diagnostic_check_join_in_progress_copied_bool_line(sequence=2, copied_bool_values="1,1"),
            diagnostic_check_join_in_progress_copied_bool_line(sequence=3, copied_bool_values="0,1"),
            diagnostic_candidate_line(
                sequence=4,
                target="ShooterGameMode.HandleNewPlayer",
                reason=LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON,
            ),
        ]
        log_path = self.write_copied_log(diagnostic_only_lines)
        payload = manifest_for_copied_log(log_path, log_lines=runtime_log_lines())

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_diagnostic_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_diagnostic_request_pack_as_approved_runtime_evidence(self) -> None:
        payload = manifest()
        request_artifact = payload["operational_window"]["request_pack"]
        request_path = Path(request_artifact["path"])
        request_pack = json.loads(request_path.read_text(encoding="utf-8"))
        request_pack["diagnostic_candidates_enabled"] = True
        request_path.write_text(json.dumps(request_pack, sort_keys=True) + "\n", encoding="utf-8")
        request_artifact["sha256"] = hashlib.sha256(request_path.read_bytes()).hexdigest()

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_request_pack_diagnostic_candidates_not_allowed", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])

    def test_rejects_runtime_diagnostic_candidate_as_approved_evidence(self) -> None:
        diagnostic_only_lines = [
            line
            for line in runtime_log_lines()
            if "PlayerPrincipalLifecycleObserver event " not in line
        ]
        diagnostic_only_lines.append(diagnostic_candidate_line(sequence=1))
        log_path = self.write_copied_log(diagnostic_only_lines)
        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=diagnostic_only_lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])
        self.assertNotIn("runtime_summary_quality_counter_nonzero", report["blockers"])

    def test_rejects_metadata_only_runtime_summary_as_approved_evidence(self) -> None:
        lines = [
            *runtime_posture_lines_without_lifecycle_observer(),
            "[info] Reflected player_principal_lifecycle ProcessEvent #1 "
            "function=ShooterGameMode.HandleNewPlayer fname_index=2170 fields=0 metadata_only=true",
        ]
        log_path = self.write_copied_log(lines)
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "runtime_summary_metadata_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assert_runtime_evidence_and_public_readiness_blocked(report)

    def test_rejects_manifest_with_only_diagnostic_reason_fields(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["accepted_count"] = 0
        module["observed_event_cases"] = []
        module["diagnostic_candidate_count"] = 0
        module["diagnostic_candidate_target_counts"] = {}
        module["diagnostic_candidate_reason_counts"] = {"property_chain_cycle_detected": 1}
        module["diagnostic_candidate_read_status_counts"] = {}
        module["functions"] = {
            "observer_gate": module["functions"]["observer_gate"],
        }
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        self.assert_runtime_evidence_and_public_readiness_blocked(report)

    def test_rejects_runtime_summary_readiness_gate_overclaim(self) -> None:
        payload = manifest()
        payload["source_summary"]["readiness_gate"] = "public_readiness"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_readiness_gate_mismatch", report["blockers"])
        self.assertIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_runtime_summary_promotion_gate_overclaim(self) -> None:
        payload = manifest()
        payload["source_summary"]["promotion_gate"] = {
            "gate_type": "runtime_observer_promoted",
            "ready": True,
            "blockers": [],
            "public_sdk_ready": True,
        }
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_promotion_gate_keys_unexpected", report["blockers"])
        self.assertIn("source_summary_promotion_gate_gate_type_mismatch", report["blockers"])
        self.assertIn("source_summary_promotion_gate_ready_mismatch", report["blockers"])
        self.assertIn("source_summary_promotion_gate_blockers_mismatch", report["blockers"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_operational_window_allowed_false_flag_overclaims(self) -> None:
        for key in OPERATIONAL_WINDOW_FALSE_FLAGS:
            with self.subTest(key=key):
                payload = manifest()
                payload["operational_window"][key] = True
                payload = add_output_artifact_identity(payload)

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"operational_window_{key}_not_false", report["blockers"])
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_runtime_summary_commit_that_is_not_current_head(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_current_head")
        payload = manifest()

        with mock.patch.object(checker, "current_obelisk_commit", return_value="f" * 40):
            validation = checker.validate_manifest(payload, check_mode="consume")

        self.assertIn(
            "source_summary_obelisk_commit_not_current_head",
            [blocker["reason"] for blocker in validation.blockers],
        )
        self.assertIn(
            "operational_window_obelisk_commit_not_current_head",
            [blocker["reason"] for blocker in validation.blockers],
        )

    def test_rejects_runtime_summary_process_event_candidate_address_drift(self) -> None:
        lines = [
            line.replace("ProcessEvent candidate[0] = 0x1d34e20", "ProcessEvent candidate[0] = 0x1d34e21")
            for line in runtime_log_lines()
        ]
        temp_dir = retained_temp_offline_workspace()
        log_path = Path(temp_dir.name) / "live-validation-logs" / RUN_ID / "Obelisk.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_runtime_posture_mismatch", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_runtime_summary_process_event_found_address_drift(self) -> None:
        lines = [
            line.replace("Found ProcessEvent at address: 0x1d34e20", "Found ProcessEvent at address: 0x1d34e21")
            for line in runtime_log_lines()
        ]
        temp_dir = retained_temp_offline_workspace()
        log_path = Path(temp_dir.name) / "live-validation-logs" / RUN_ID / "Obelisk.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_runtime_posture_mismatch", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_historical_false_process_event_anchor(self) -> None:
        lines = [
            line.replace("ProcessEvent candidate[0] = 0x1d34e20", "ProcessEvent candidate[0] = 0x1d11cb0")
                .replace("Found ProcessEvent at address: 0x1d34e20", "Found ProcessEvent at address: 0x1d11cb0")
            for line in runtime_log_lines()
        ]
        temp_dir = retained_temp_offline_workspace()
        log_path = Path(temp_dir.name) / "live-validation-logs" / RUN_ID / "Obelisk.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = self.run_checker(manifest_for_copied_log(log_path, log_lines=lines), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_runtime_posture_mismatch", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_synthetic_shape_fixture_as_approved_runtime_evidence(self) -> None:
        payload = {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1",
            "artifact_status": "synthetic_redacted_fixture",
            "readiness_classification": "shape_only_private_fixture",
            "approved_runtime_evidence_present": False,
            "runtime_evidence_ready": False,
        }
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema_mismatch", report["blockers"])
        self.assertIn("synthetic_shape_fixture_is_not_approved_runtime_evidence", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def rewrite_sidecar_and_refresh_identity(self, payload: dict, artifact: dict, text: str) -> None:
        path = Path(artifact["path"])
        path.write_text(text, encoding="utf-8")
        artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        payload.pop("output_artifact_identity", None)
        add_output_artifact_identity(payload)

    def rewrite_receipt_and_manifest_sha(
        self,
        payload: dict,
        mutate_receipt,
    ) -> None:
        receipt_artifact = payload["operational_window"]["operator_approval_receipt"]
        receipt_path = Path(receipt_artifact["path"])
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        mutate_receipt(receipt)
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
        receipt_artifact["sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

        manifest_artifact = payload["operational_window"]["manifest"]
        manifest_path = Path(manifest_artifact["path"])
        manifest_lines = []
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("operator_approval_receipt_sha256="):
                manifest_lines.append(f"operator_approval_receipt_sha256={receipt_artifact['sha256']}")
            else:
                manifest_lines.append(line)
        manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        manifest_artifact["sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

        payload.pop("output_artifact_identity", None)
        add_output_artifact_identity(payload)

    def test_operational_window_replay_delegates_manifest_post_window_mode(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_replay_post_window")
        window = {"manifest": {"path": "/tmp/window-manifest.env"}}
        replay_projection = {key: window.get(key) for key in checker.OPERATIONAL_WINDOW_REPLAY_KEYS}
        validation = checker.window_manifest_checker.Validation(
            blockers=[],
            target=None,
            user_policy=None,
            copied_log_status=None,
        )

        with (
            mock.patch.object(checker.window_manifest_checker, "load_manifest", return_value={"run_id": RUN_ID}),
            mock.patch.object(
                checker.window_manifest_checker,
                "validate_manifest",
                return_value=validation,
            ) as validate,
            mock.patch.object(
                checker.window_manifest_checker,
                "build_report",
                return_value=replay_projection,
            ) as build,
        ):
            blockers: list[dict] = []
            checker.replay_operational_window_manifest(window, blockers)

        self.assertEqual([], blockers)
        self.assertTrue(validate.call_args.kwargs["post_window_replay"])
        self.assertTrue(build.call_args.kwargs["post_window_replay"])

    def test_operational_window_replay_preserves_mixed_or_duplicate_request_blockers(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_replay_blockers")
        for request_blockers in (
            ["approved_window_expired", "operator_request_markdown_mismatch"],
            ["approved_window_expired", "approved_window_expired"],
        ):
            with self.subTest(request_blockers=request_blockers):
                window = {"manifest": {"path": "/tmp/window-manifest.env"}}
                replay_projection = {key: window.get(key) for key in checker.OPERATIONAL_WINDOW_REPLAY_KEYS}
                validation = checker.window_manifest_checker.Validation(
                    blockers=[
                        {
                            "reason": "request_pack_window_request_check_failed",
                            "label": "request_pack_path",
                            "request_check_blockers": request_blockers,
                        }
                    ],
                    target=None,
                    user_policy=None,
                    copied_log_status=None,
                )

                with (
                    mock.patch.object(
                        checker.window_manifest_checker,
                        "load_manifest",
                        return_value={"run_id": RUN_ID},
                    ),
                    mock.patch.object(
                        checker.window_manifest_checker,
                        "validate_manifest",
                        return_value=validation,
                    ),
                    mock.patch.object(
                        checker.window_manifest_checker,
                        "build_report",
                        return_value=replay_projection,
                    ),
                ):
                    blockers: list[dict] = []
                    checker.replay_operational_window_manifest(window, blockers)

                self.assertEqual(
                    ["operational_window_manifest_check_failed"],
                    [blocker["reason"] for blocker in blockers],
                )
                self.assertEqual(["request_pack_window_request_check_failed"], blockers[0]["replay_blockers"])
                self.assertEqual(
                    request_blockers,
                    blockers[0]["replay_blocker_details"][0]["request_check_blockers"],
                )

    def test_rejects_mutated_window_manifest_even_when_embedded_sha_is_updated(self) -> None:
        payload = manifest()
        manifest_path = Path(payload["operational_window"]["manifest"]["path"])
        mutated = manifest_path.read_text(encoding="utf-8").replace("dispatch_limit=0\n", "dispatch_limit=1\n")
        self.rewrite_sidecar_and_refresh_identity(payload, payload["operational_window"]["manifest"], mutated)
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_manifest_check_failed", report["blockers"])
        self.assertIn("operational_window_manifest_replay_mismatch", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_mutated_request_env_or_preflight_sidecar_even_when_embedded_sha_is_updated(self) -> None:
        cases = (
            (
                "request_pack",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda path: path.read_text(encoding="utf-8").replace('"map": "TheIsland"', '"map": "Ragnarok"'),
                "operational_window_request_pack_target_mismatch",
            ),
            (
                "observer_env",
                lambda payload: payload["operational_window"]["observer_env"],
                lambda path: path.read_text(encoding="utf-8").replace(
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0\n",
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=1\n",
                ),
                "operational_window_observer_env_value_mismatch",
            ),
            (
                "preflight_pre",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda path: path.read_text(encoding="utf-8").replace(
                    '"mode": "observer-window"',
                    '"mode": "stable"',
                ),
                "operational_window_preflight_mode_mismatch",
            ),
            (
                "preflight_post",
                lambda payload: payload["operational_window"]["preflight"]["post"],
                lambda path: path.read_text(encoding="utf-8").replace(
                    '"mode": "stable"',
                    '"mode": "observer-window"',
                ),
                "operational_window_preflight_mode_mismatch",
            ),
            (
                "preflight_non_claim",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda path: path.read_text(encoding="utf-8").replace(
                    "not approved runtime evidence, ",
                    "",
                ),
                "operational_window_preflight_non_claim_mismatch",
            ),
        )
        for name, artifact_for_payload, mutate, expected_blocker in cases:
            with self.subTest(sidecar=name):
                payload = manifest()
                artifact = artifact_for_payload(payload)
                path = Path(artifact["path"])
                self.rewrite_sidecar_and_refresh_identity(payload, artifact, mutate(path))
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_blocker, report["blockers"])
                self.assertIn("operational_window_manifest_check_failed", report["blockers"])
                self.assertIn("operational_window_manifest_replay_mismatch", report["blockers"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_public_reachability_json_swapped_into_operational_sidecar(self) -> None:
        cases = (
            (
                "request_pack",
                lambda payload: payload["operational_window"]["request_pack"],
                "operational_window_request_pack_public_reachability_sidecar_not_approved_runtime_evidence",
            ),
            (
                "preflight_pre",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                "operational_window_preflight_pre_path_public_reachability_sidecar_not_approved_runtime_evidence",
            ),
            (
                "operator_receipt",
                lambda payload: payload["operational_window"]["operator_approval_receipt"],
                "operational_window_operator_approval_receipt_public_reachability_sidecar_not_approved_runtime_evidence",
            ),
        )
        public_reachability = json.dumps(
            {
                "schema": "obelisk.player-principal-public-reachability-check.v1",
                "ready": True,
                "public_reachability_ready": True,
                "public_reachability_counts_as_approved_runtime_evidence": True,
            },
            sort_keys=True,
        ) + "\n"
        for name, artifact_for_payload, expected_blocker in cases:
            with self.subTest(sidecar=name):
                payload = manifest()
                artifact = artifact_for_payload(payload)
                self.rewrite_sidecar_and_refresh_identity(payload, artifact, public_reachability)

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_blocker, report["blockers"])
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_active_or_passive_summary_json_swapped_into_operational_sidecar(self) -> None:
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
                "operational_window_request_pack_passive_activity_triage_sidecar_not_approved_runtime_evidence",
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
                "operational_window_request_pack_sdk_status_report_sidecar_not_approved_runtime_evidence",
            ),
        )
        for name, sidecar_payload, expected_blocker in cases:
            with self.subTest(sidecar=name):
                payload = manifest()
                artifact = payload["operational_window"]["request_pack"]
                self.rewrite_sidecar_and_refresh_identity(
                    payload,
                    artifact,
                    json.dumps(sidecar_payload, sort_keys=True) + "\n",
                )

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_blocker, report["blockers"])
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_notice_action_or_status_report_json_swapped_into_operational_sidecar(self) -> None:
        cases = (
            (
                "player_notice_action",
                {
                    "schema": "obelisk.player-principal-lifecycle-player-notice-action.v1",
                    "required": True,
                    "notice_path": "discord-beta-testers",
                    "counts_as_approved_runtime_evidence": False,
                },
                "operational_window_request_pack_player_notice_action_sidecar_not_approved_runtime_evidence",
            ),
            (
                "discord_active_notice_state",
                {
                    "schema": "obelisk.discord-beta-bridge-active-notice.v1",
                    "status": "active",
                    "discord_sent": True,
                    "counts_as_approved_runtime_evidence": False,
                },
                "operational_window_request_pack_discord_bridge_state_sidecar_not_approved_runtime_evidence",
            ),
            (
                "window_request_check",
                {
                    "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
                    "ready": True,
                    "request_pack_ready": True,
                    "approved_runtime_evidence_ready": False,
                },
                "operational_window_request_pack_window_request_check_sidecar_not_approved_runtime_evidence",
            ),
            (
                "runtime_window_plan",
                {
                    "schema": "obelisk.player-principal-lifecycle-runtime-window-plan.v1",
                    "ready": True,
                    "next_actions": [{"id": "run_bundle_builder"}],
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "operational_window_request_pack_next_action_plan_sidecar_not_approved_runtime_evidence",
            ),
            (
                "runtime_evidence_status_report",
                {
                    "schema": "obelisk.player-principal-lifecycle-runtime-evidence-status.v1",
                    "status": "closure_inputs_complete_bundle_checker_required",
                    "next_actions": [{"id": "run_bundle_builder"}],
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "operational_window_request_pack_runtime_evidence_status_report_sidecar_not_approved_runtime_evidence",
            ),
            (
                "passive_monitor_only_summary",
                {
                    "schema": "obelisk.player-principal-passive-monitor-only-summary.v1",
                    "classification": "monitor_only_non_evidence",
                    "passive_monitor_activity_summary": {},
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "operational_window_request_pack_passive_monitor_only_summary_sidecar_not_approved_runtime_evidence",
            ),
            (
                "approved_runtime_manifest",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
                "operational_window_request_pack_approved_runtime_manifest_sidecar_not_checked_bundle_output",
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
                "operational_window_request_pack_public_sdk_completion_check_sidecar_not_approved_runtime_evidence",
            ),
            (
                "public_sdk_completion_summary",
                {
                    "schema": "obelisk.public-sdk-v1-completion-summary.v1",
                    "status": "blocked",
                    "ready": False,
                    "sdk_completion": {"status": "blocked", "progress_ratio": "0/12"},
                },
                "operational_window_request_pack_public_sdk_completion_summary_sidecar_not_approved_runtime_evidence",
            ),
            (
                "approved_in_game_evidence_status",
                {
                    "schema": "obelisk.approved-in-game-evidence-status.v1",
                    "approved_runtime_evidence_ready": False,
                    "sdk": {"promoted": 0, "total": 12},
                },
                "operational_window_request_pack_approved_in_game_evidence_status_sidecar_not_approved_runtime_evidence",
            ),
            (
                "multi_surface_beta_capture_plan",
                {
                    "schema": "obelisk.multi-surface-beta-capture-plan.v1",
                    "status": "candidate_capture_plan",
                    "required_primary_evidence": {
                        "strict_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
                        "must_be_checker_accepted": True,
                    },
                    "capture_surfaces": [
                        {
                            "id": "player_principal_lifecycle",
                            "candidate_capture_only": True,
                            "requires_checker_acceptance": True,
                            "replaces_player_principal_triplet": False,
                        }
                    ],
                    "non_claim_flags": {
                        "candidate_only": True,
                        "counts_as_approved_runtime_evidence": False,
                        "runtime_ready": False,
                    },
                },
                "operational_window_request_pack_multi_surface_beta_capture_plan_sidecar_not_approved_runtime_evidence",
            ),
            (
                "principal_start_end_report",
                {
                    "schema": "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1",
                    "ready": True,
                    "ready_scope": "principal_start_end_runtime_evidence_only",
                    "principal_start_end_runtime_evidence_present": True,
                    "principal_start_end_runtime_evidence_ready": True,
                    "approved_runtime_evidence_present": False,
                    "approved_runtime_evidence_ready": False,
                    "runtime_ready": False,
                    "public_sdk_ready": False,
                },
                "operational_window_request_pack_start_end_only_evidence_sidecar_not_approved_runtime_evidence",
            ),
            (
                "future_debug_capture",
                {
                    "schema": "obelisk.player-principal-debug-capture-bundle.v1",
                    "status": "candidate_debug_capture",
                    "debug_capture_evidence_ready": False,
                    "candidate_debug_capture_ready": False,
                    "session_start_rejected_role_satisfied": False,
                    "counts_as_approved_runtime_evidence": False,
                },
                "operational_window_request_pack_debug_capture_schema_is_not_approved_runtime_evidence",
            ),
        )
        for name, sidecar_payload, expected_blocker in cases:
            with self.subTest(sidecar=name):
                payload = manifest()
                artifact = payload["operational_window"]["request_pack"]
                self.rewrite_sidecar_and_refresh_identity(
                    payload,
                    artifact,
                    json.dumps(sidecar_payload, sort_keys=True) + "\n",
                )

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_blocker, report["blockers"])
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_request_pack_with_partial_replay_provenance(self) -> None:
        payload = manifest()
        request_artifact = payload["operational_window"]["request_pack"]
        request_path = Path(request_artifact["path"])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request.pop("post_window_replay_contract")
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            request_artifact,
            json.dumps(request, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_request_pack_post_window_replay_contract_missing", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_request_pack_replay_contract_missing_required_sidecar_paths(self) -> None:
        cases = (
            (
                "operator_request",
                "operator_approval_request_path",
                "operational_window_request_pack_replay_contract_operator_approval_request_path_mismatch",
            ),
            (
                "copied_log",
                "copied_log_path",
                "operational_window_request_pack_replay_contract_copied_log_path_mismatch",
            ),
        )
        for name, sidecar_key, expected_blocker in cases:
            with self.subTest(name=name):
                payload = manifest()
                request_artifact = payload["operational_window"]["request_pack"]
                request_path = Path(request_artifact["path"])
                request = json.loads(request_path.read_text(encoding="utf-8"))
                request["post_window_replay_contract"]["sidecars"].pop(sidecar_key)
                self.rewrite_sidecar_and_refresh_identity(
                    payload,
                    request_artifact,
                    json.dumps(request, sort_keys=True) + "\n",
                )

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_blocker, report["blockers"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_request_pack_replay_contract_unexpected_sidecar_path(self) -> None:
        payload = manifest()
        request_artifact = payload["operational_window"]["request_pack"]
        request_path = Path(request_artifact["path"])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["post_window_replay_contract"]["sidecars"]["stale_bundle_path"] = str(
            request_path.parent / "stale-approved-bundle.json"
        )
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            request_artifact,
            json.dumps(request, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_request_pack_replay_contract_unexpected_sidecar", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_beta_request_pack_without_real_notice_contract(self) -> None:
        payload = manifest()
        payload["operational_window"]["user_policy"] = "operator_approved_beta_users"
        payload["operational_window"]["notice_sent"] = "true"
        request_artifact = payload["operational_window"]["request_pack"]
        request_path = Path(request_artifact["path"])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["user_policy"] = "operator_approved_beta_users"
        request["notice_path"] = "not_applicable"
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            request_artifact,
            json.dumps(request, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_request_pack_notice_path_mismatch", report["blockers"])
        self.assertIn("operational_window_request_pack_player_notice_action_notice_path_mismatch", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])

    def test_rejects_stray_confirmed_beta_notice_for_no_regular_users_window(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        stray_notice = copied_log.parent / "beta-notice.confirmed.json"
        stray_notice.write_text(
            json.dumps(
                {
                    "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
                    "mode": "confirmed_send",
                    "ready": True,
                    "discord_sent": True,
                    "notice_path": "discord-beta-testers",
                    "counts_as_approved_runtime_evidence": False,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_unexpected_json_sidecar_notice_prep_sidecar_not_approved_runtime_evidence",
            report["blockers"],
        )

    def test_rejects_sidecar_public_sdk_or_runtime_readiness_overclaim(self) -> None:
        cases = (
            (
                "request_public_sdk_ready",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"public_sdk_ready": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "request_public_runtime_v1_ready",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"public_runtime_v1_ready": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "request_stable_camel_case",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"stableClaimAllowed": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "receipt_stable_release_contract",
                lambda payload: payload["operational_window"]["operator_approval_receipt"],
                lambda sidecar: sidecar.update({"stable_release_contract_claim_allowed": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "preflight_stable_claim_text",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"note": "stable SDK claim is allowed"}),
                "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
            ),
            (
                "preflight_approved_runtime_evidence_text",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"nested": {"note": "preflight counts as approved runtime evidence"}}),
                "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
            ),
            (
                "preflight_server_restart_authorized_key",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"server_restart_authorized": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_live_log_reads_authorized_key",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"live_log_reads_authorized": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "preflight_public_ready_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"publicReady": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_identity_ready_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"nested": {"identityReady": True}}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_permissions_unlocked_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"permissionsUnlocked": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_command_route_ready_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"commandRouteReady": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_counts_toward_sdk_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"countsTowardSdk": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_route_support_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"routeSupport": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_sdk_accounting_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"sdkAccountingReady": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_sdk_complete_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"sdkComplete": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_p0_accounting_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"p0AccountingCountsAsPromotedSurface": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "request_counts_as_runtime_evidence",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"counts_as_runtime_evidence": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "request_counts_as_sdk_progress",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"counts_as_sdk_progress": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "request_counts_as_p0_progress",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"counts_as_p0_progress": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "request_clears_approved_runtime_evidence_missing",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"clears_approved_runtime_evidence_missing": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "request_stable_sdk_ready",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"stable_sdk_ready": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "request_plugin_hub_ready",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"plugin_hub_ready": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "request_publication_ready",
                lambda payload: payload["operational_window"]["request_pack"],
                lambda sidecar: sidecar.update({"publication_ready": True}),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "preflight_readiness_status_stable_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"readiness_status": "stable"}),
                "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
            ),
            (
                "preflight_sdk_status_stable_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"sdk_status": "sdk_stable"}),
                "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
            ),
            (
                "preflight_completion_status_complete_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"completion_status": "complete"}),
                "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
            ),
            (
                "preflight_public_identity_available_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"publicIdentityAvailable": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_runtime_accepted_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"runtimeAccepted": True}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_public_reachability_counts_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update(
                    {"public_reachability_counts_as_approved_runtime_evidence": True}
                ),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "preflight_public_reachability_dotted_counts_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update(
                    {"public.reachability.counts.as.approved.runtime.evidence": True}
                ),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "preflight_runtime_window_request_output_counts_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update(
                    {"runtime_window_request_output_counts_as_approved_runtime_evidence": True}
                ),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "preflight_planning_artifact_counts_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update(
                    {"planning_artifact_counts_as_approved_runtime_evidence": True}
                ),
                "operational_window_sidecar_readiness_flag_overclaim",
            ),
            (
                "preflight_support_package_positive_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"supportPackage": "approved"}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
            (
                "preflight_package_label_runtime_evidence_alias",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda sidecar: sidecar.update({"package_label": "runtime evidence accepted"}),
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            ),
        )
        for name, artifact_for_payload, mutate, expected in cases:
            with self.subTest(name=name):
                payload = manifest()
                artifact = artifact_for_payload(payload)
                sidecar_path = Path(artifact["path"])
                sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
                mutate(sidecar)
                self.rewrite_sidecar_and_refresh_identity(
                    payload,
                    artifact,
                    json.dumps(sidecar, sort_keys=True) + "\n",
                )

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, report["blockers"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_nested_sidecar_non_claim_positive_claim(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_nested_non_claim")
        blockers: list[dict] = []

        checker.validate_no_sidecar_overclaims(
            {
                "operator_completion": {
                    "non_claims": [
                        "public SDK ready",
                    ],
                },
            },
            "$.operational_window.operator_approval_receipt.path",
            blockers,
        )

        self.assertIn(
            "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
            [blocker["reason"] for blocker in blockers],
        )

    def test_rejects_nested_sidecar_runtime_evidence_bundle_aliases(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_nested_bundle_aliases")
        cases = (
            ("evidence_approved", {"evidence": {"approved": True}}),
            ("runtime_observed", {"runtime": {"observed": True}}),
            ("player_session_accepted", {"playerSessions": [{"accepted": True}]}),
            ("lifecycle_proof_validated", {"lifecycle": {"proof": {"status": "validated"}}}),
            ("bundle_ready", {"bundle": {"ready": True}}),
            ("sidecar_complete", {"sidecar": {"complete": True}}),
            ("artifact_status_accepted", {"artifact": {"status": "accepted"}}),
        )
        for name, sidecar in cases:
            with self.subTest(name=name):
                blockers: list[dict] = []

                checker.validate_no_sidecar_overclaims(
                    sidecar,
                    "$.operational_window.preflight.pre.path",
                    blockers,
                )

                self.assertTrue(
                    {
                        "operational_window_sidecar_authorization_or_readiness_key_overclaim",
                        "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
                    }
                    & {blocker["reason"] for blocker in blockers}
                )

    def test_rejects_operator_receipt_verified_flag_not_true(self) -> None:
        payload = manifest()
        payload["operational_window"]["operator_approval_receipt"]["verified"] = False
        payload.pop("output_artifact_identity", None)
        add_output_artifact_identity(payload)
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_operator_approval_receipt_verified_not_true", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_operator_receipt_payload_edit_without_manifest_sha_refresh(self) -> None:
        payload = manifest()
        receipt_artifact = payload["operational_window"]["operator_approval_receipt"]
        receipt_path = Path(receipt_artifact["path"])
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["operator_reference"] = "edited-after-manifest"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_artifact_sha256_mismatch", report["blockers"])
        self.assertIn("operational_window_manifest_check_failed", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_operator_receipt_binding_and_non_authorization_drift_after_sha_refresh(self) -> None:
        cases = (
            (
                "request_artifact",
                lambda receipt: receipt["bound_artifacts"]["window_request_json"].update({"sha256": "0" * 64}),
                "operational_window_operator_approval_receipt_window_request_json_artifact_mismatch",
            ),
            (
                "operator_request_sidecar_artifact",
                lambda receipt: receipt["bound_artifacts"]["operator_approval_request_md"].update({"sha256": "0" * 64}),
                "operational_window_operator_approval_receipt_operator_approval_request_md_artifact_mismatch",
            ),
            (
                "manifest_path",
                lambda receipt: receipt["bound_request_pack"].update({"window_manifest_path": "/tmp/window-manifest.env"}),
                "operational_window_operator_approval_receipt_bound_request_window_manifest_path_mismatch",
            ),
            (
                "copied_log_path",
                lambda receipt: receipt["bound_request_pack"].update({"copied_log_path": "/tmp/Obelisk.log"}),
                "operational_window_operator_approval_receipt_bound_request_copied_log_path_mismatch",
            ),
            (
                "request_artifact_path",
                lambda receipt: receipt["bound_artifacts"]["window_request_json"].update(
                    {"path": receipt["bound_artifacts"]["observer_window_env"]["path"]}
                ),
                "operational_window_operator_approval_receipt_window_request_json_artifact_mismatch",
            ),
            (
                "non_authorization_flag",
                lambda receipt: receipt["non_authorization_flags"].update({"runtime_ready": True}),
                "operational_window_operator_approval_receipt_runtime_ready_not_false",
            ),
            (
                "route_ready_non_authorization_flag",
                lambda receipt: receipt["non_authorization_flags"].update({"route_ready": True}),
                "operational_window_operator_approval_receipt_route_ready_not_false",
            ),
            (
                "sdk_accounting_non_authorization_flag",
                lambda receipt: receipt["non_authorization_flags"].update(
                    {"sdk_accounting_counts_as_completed_surface": True}
                ),
                "operational_window_operator_approval_receipt_sdk_accounting_counts_as_completed_surface_not_false",
            ),
            (
                "p0_accounting_non_authorization_flag",
                lambda receipt: receipt["non_authorization_flags"].update(
                    {"p0_accounting_counts_as_promoted_surface": True}
                ),
                "operational_window_operator_approval_receipt_p0_accounting_counts_as_promoted_surface_not_false",
            ),
            (
                "p0_accounting_zero_alias",
                lambda receipt: receipt["non_authorization_flags"].update(
                    {"p0_accounting_counts_as_promoted_surface": 0}
                ),
                "operational_window_operator_approval_receipt_p0_accounting_counts_as_promoted_surface_not_false",
            ),
        )
        for name, mutate, blocker in cases:
            with self.subTest(name=name):
                payload = manifest()
                self.rewrite_receipt_and_manifest_sha(payload, mutate)
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(blocker, report["blockers"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_request_pack_missing_player_presence_safety_after_sha_refresh(self) -> None:
        payload = manifest()
        request_artifact = payload["operational_window"]["request_pack"]
        request_path = Path(request_artifact["path"])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request.pop("player_presence_safety")
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            request_artifact,
            json.dumps(request, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_request_pack_player_presence_safety_missing", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_receipt_bound_request_missing_player_presence_safety_after_sha_refresh(self) -> None:
        payload = manifest()
        self.rewrite_receipt_and_manifest_sha(
            payload,
            lambda receipt: receipt["bound_request_pack"].pop("player_presence_safety"),
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "operational_window_operator_approval_receipt_bound_request_player_presence_safety_missing",
            report["blockers"],
        )
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_generated_operator_receipt_even_when_hashes_are_refreshed(self) -> None:
        payload = manifest()

        def mark_generated_template(receipt: dict) -> None:
            receipt["status"] = "generated_template"
            receipt["receipt_completed"] = False
            receipt["operator_current_turn_approval_recorded"] = False
            receipt["operator_completion"] = {
                "approval_recorded_at_utc": None,
                "approved_by_role": None,
                "approval_source": None,
                "attestation": None,
            }

        self.rewrite_receipt_and_manifest_sha(payload, mark_generated_template)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_operator_approval_receipt_status_not_completed", report["blockers"])
        self.assertIn("operational_window_operator_approval_receipt_receipt_completed_not_true", report["blockers"])
        self.assertIn(
            "operational_window_operator_approval_receipt_operator_current_turn_approval_recorded_not_true",
            report["blockers"],
        )
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_standing_authority_receipt_with_current_turn_contradiction(self) -> None:
        payload = manifest(standing_launch_authority=True)
        self.rewrite_receipt_and_manifest_sha(
            payload,
            lambda receipt: receipt.update({"operator_current_turn_approval_recorded": True}),
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "operational_window_operator_approval_receipt_current_turn_approval_not_false_for_standing_authority",
            report["blockers"],
        )
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_future_completed_operator_receipt(self) -> None:
        payload = manifest()
        future_approval = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
        self.rewrite_receipt_and_manifest_sha(
            payload,
            lambda receipt: receipt["operator_completion"].update(
                {"approval_recorded_at_utc": future_approval.strftime("%Y-%m-%dT%H:%M:%SZ")}
            ),
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "operational_window_operator_approval_receipt_approved_at_utc_in_future",
            report["blockers"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_operator_receipt_incomplete_role_after_sha_refresh(self) -> None:
        payload = manifest()
        self.rewrite_receipt_and_manifest_sha(
            payload,
            lambda receipt: receipt["operator_completion"].update(
                {"approved_by_role": "test-current-turn-approval"}
            ),
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "operational_window_operator_approval_receipt_approved_by_role_unapproved",
            report["blockers"],
        )
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])

    def test_rejects_operator_receipt_window_request_alias_runtime_evidence_claim(self) -> None:
        payload = manifest()
        self.rewrite_receipt_and_manifest_sha(
            payload,
            lambda receipt: receipt["operator_completion"].update(
                {"approved_by_role": "window request counts as approved runtime evidence"}
            ),
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_future_post_window_operational_window(self) -> None:
        payload = manifest()
        future_start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
        payload["operational_window"]["approved_window"] = {
            "start_utc": future_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_utc": (future_start + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        payload["operational_window"]["actual_capture"] = {
            "start_utc": (future_start + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_utc": (future_start + timedelta(minutes=9)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        payload["operational_window"]["rollback_window"] = {
            "start_utc": (future_start + timedelta(minutes=9)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_utc": (future_start + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        payload.pop("output_artifact_identity", None)
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_approved_window_ends_in_future", report["blockers"])
        self.assertIn("operational_window_actual_capture_ends_in_future", report["blockers"])
        self.assertIn("operational_window_rollback_window_ends_in_future", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_future_preflight_sidecar_checked_at(self) -> None:
        payload = manifest()
        artifact = payload["operational_window"]["preflight"]["post"]
        sidecar_path = Path(artifact["path"])
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        future_checked_at = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
        sidecar["checked_at_utc"] = future_checked_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            artifact,
            json.dumps(sidecar, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_preflight_checked_at_utc_in_future", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_observer_enable_outside_actual_capture_window(self) -> None:
        lines = [
            line.replace("[2026-06-01T12:01:30Z]", "[2026-06-01T12:00:30Z]")
            if "PlayerPrincipalLifecycleObserver enabled " in line
            else line
            for line in runtime_log_lines()
        ]
        log_path = self.write_copied_log(lines)

        result = self.run_checker(
            manifest_for_copied_log(log_path, log_lines=lines),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn(
            "source_summary_copied_log_observer_enable_outside_actual_capture_window",
            report["blockers"],
        )

    def test_rejects_semantically_invalid_preflight_timestamp_without_traceback(self) -> None:
        payload = manifest()
        artifact = payload["operational_window"]["preflight"]["post"]
        sidecar_path = Path(artifact["path"])
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["checked_at_utc"] = "2026-99-99T99:99:99Z"
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            artifact,
            json.dumps(sidecar, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual("", result.stderr)
        self.assertIn("operational_window_preflight_checked_at_utc_invalid", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_operational_window_artifact_does_not_hash_protected_path(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_protected_sidecar")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected_root = root / "server"
            offline_root = root / "workspace-offline"
            protected_root.mkdir()
            offline_root.mkdir()
            artifact_path = protected_root / RUN_ID / "window-manifest.json"
            artifact = {"path": str(artifact_path), "sha256": "a" * 64}
            blockers: list[dict] = []

            with mock.patch.object(checker, "SERVER_ROOT", protected_root), mock.patch.object(
                checker,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (offline_root,),
            ), mock.patch.object(checker, "sha256_file", side_effect=AssertionError("sha256_file should not run")):
                checker.validate_operational_window_artifact(
                    artifact,
                    "$.operational_window.manifest",
                    blockers,
                    run_id=RUN_ID,
                    expected_name="window-manifest.json",
                )

        self.assertIn(
            "operational_window_artifact_path_not_copied_or_offline",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertNotIn(
            "operational_window_artifact_file_missing",
            [blocker["reason"] for blocker in blockers],
        )

    def test_operational_window_artifact_does_not_hash_symlinked_path(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_symlink_sidecar")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected_root = root / "server"
            offline_root = root / "workspace-offline"
            protected_target = protected_root / RUN_ID
            approved_link = offline_root / RUN_ID
            protected_target.mkdir(parents=True)
            offline_root.mkdir()
            approved_link.symlink_to(protected_target)
            artifact_path = approved_link / "window-manifest.json"
            artifact = {"path": str(artifact_path), "sha256": "a" * 64}
            blockers: list[dict] = []

            with mock.patch.object(checker, "SERVER_ROOT", protected_root), mock.patch.object(
                checker,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (offline_root,),
            ), mock.patch.object(checker, "sha256_file", side_effect=AssertionError("sha256_file should not run")):
                checker.validate_operational_window_artifact(
                    artifact,
                    "$.operational_window.manifest",
                    blockers,
                    run_id=RUN_ID,
                    expected_name="window-manifest.json",
                )

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("operational_window_artifact_path_symlink_component", reasons)
        self.assertIn("operational_window_artifact_path_not_copied_or_offline", reasons)
        self.assertNotIn("operational_window_artifact_file_missing", reasons)

    def test_load_json_artifact_reports_protected_sidecar_without_reading(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_read_protected_sidecar")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected_root = root / "server"
            offline_root = root / "workspace-offline"
            protected_root.mkdir()
            offline_root.mkdir()
            artifact_path = protected_root / RUN_ID / "window-request.json"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text("{}", encoding="utf-8")
            blockers: list[dict] = []

            with mock.patch.object(checker, "SERVER_ROOT", protected_root), mock.patch.object(
                checker,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                (offline_root,),
            ):
                payload = checker.load_json_artifact(
                    {"path": str(artifact_path), "sha256": "a" * 64},
                    "$.operational_window.request_pack.path",
                    blockers,
                )

        self.assertIsNone(payload)
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("operational_window_artifact_path_not_copied_or_offline", reasons)
        self.assertNotIn("operational_window_json_artifact_invalid", reasons)

    def test_load_text_artifact_reports_symlinked_sidecar_without_reading(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_read_symlinked_sidecar")
        old_roots = checker.APPROVED_OFFLINE_WORKSPACE_ROOTS
        with tempfile.TemporaryDirectory() as tmp:
            offline_root = Path(tmp)
            copied_log_dir = offline_root / "live-validation-logs" / RUN_ID
            copied_log_dir.mkdir(parents=True)
            real_env = copied_log_dir / "observer-window.real.env"
            linked_env = copied_log_dir / "observer-window.env"
            real_env.write_text("OBELISK_INSTANCE_ID=arkserver\n", encoding="utf-8")
            linked_env.symlink_to(real_env)
            blockers: list[dict] = []
            checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (offline_root,)
            try:
                text = checker.load_text_artifact(
                    {"path": "observer-window.env", "sha256": "a" * 64},
                    "$.operational_window.observer_env.path",
                    blockers,
                    base_dir=copied_log_dir,
                )
            finally:
                checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = old_roots

        self.assertIsNone(text)
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("operational_window_artifact_path_symlink_component", reasons)
        self.assertNotIn("operational_window_text_artifact_unreadable", reasons)

    def test_operational_window_artifact_resolves_relative_path_against_copied_log_sibling_dir(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_relative_sidecar")
        old_roots = checker.APPROVED_OFFLINE_WORKSPACE_ROOTS
        with tempfile.TemporaryDirectory() as tmp:
            offline_root = Path(tmp)
            copied_log_dir = offline_root / "live-validation-logs" / RUN_ID
            cwd_dir = offline_root / "cwd"
            copied_log_dir.mkdir(parents=True)
            cwd_dir.mkdir()
            expected_path = copied_log_dir / "window-request.json"
            cwd_path = cwd_dir / "window-request.json"
            expected_path.write_text("expected sidecar\n", encoding="utf-8")
            cwd_path.write_text("wrong cwd sidecar\n", encoding="utf-8")
            artifact = {
                "path": "window-request.json",
                "sha256": hashlib.sha256(expected_path.read_bytes()).hexdigest(),
            }
            blockers: list[dict] = []
            old_cwd = Path.cwd()
            checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (offline_root,)
            os.chdir(cwd_dir)
            try:
                checker.validate_operational_window_artifact(
                    artifact,
                    "$.operational_window.request_pack",
                    blockers,
                    run_id=RUN_ID,
                    expected_name="window-request.json",
                    base_dir=copied_log_dir,
                )
            finally:
                os.chdir(old_cwd)
                checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = old_roots

        self.assertEqual([], blockers)

    def test_rejects_relative_sidecar_path_outside_exact_copied_log_sibling_set(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_relative_sidecar_set")
        old_roots = checker.APPROVED_OFFLINE_WORKSPACE_ROOTS
        with tempfile.TemporaryDirectory() as tmp:
            offline_root = Path(tmp)
            copied_log_dir = offline_root / "live-validation-logs" / RUN_ID
            alias_dir = offline_root / "live-validation-logs" / "sidecar-aliases" / RUN_ID
            copied_log_dir.mkdir(parents=True)
            alias_dir.mkdir(parents=True)
            copied_log = copied_log_dir / "Obelisk.log"
            sidecar = alias_dir / "window-request.json"
            copied_log.write_text("copied log\n", encoding="utf-8")
            sidecar.write_text("request sidecar\n", encoding="utf-8")
            window = {
                "copied_log": {
                    "path": str(copied_log),
                    "path_status": "approved_offline_workspace",
                    "sha256": hashlib.sha256(copied_log.read_bytes()).hexdigest(),
                },
                "request_pack": {
                    "path": f"../sidecar-aliases/{RUN_ID}/window-request.json",
                    "sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
                },
            }
            blockers: list[dict] = []
            checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (offline_root,)
            try:
                checker.validate_operational_window_sibling_set(window, blockers)
            finally:
                checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = old_roots

        self.assertIn(
            "operational_window_sidecar_not_exact_copied_log_sibling",
            {blocker["reason"] for blocker in blockers},
        )

    def test_rejects_expired_request_pack_when_markdown_drift_is_also_present(self) -> None:
        payload = manifest()
        request_pack = Path(payload["operational_window"]["request_pack"]["path"])
        operator_request = request_pack.parent / "operator-approval-request.md"
        operator_request.write_text(
            operator_request.read_text(encoding="utf-8").replace("dispatch limit=0", "dispatch limit=1"),
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_manifest_check_failed", report["blockers"])
        self.assertIn("operational_window_manifest_replay_mismatch", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_validate_manifest_recomputes_copied_log_sha(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker")
        old_env = os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES")
        old_root = os.environ.get("OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE")
        os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
        with temp_offline_workspace() as tmp:
            copied_log = Path(tmp) / "live-validation-logs" / RUN_ID / "Obelisk.log"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            try:
                payload = manifest_for_copied_log(copied_log)
                accepted = checker.validate_manifest(payload, check_mode="consume")
                self.assertEqual([], accepted.blockers)

                payload["source_summary"]["evidence"]["sources"][0]["sha256"] = hashlib.sha256(b"other").hexdigest()
                payload["operational_window"]["copied_log"]["sha256"] = payload["source_summary"]["evidence"]["sources"][0]["sha256"]
                rejected = checker.validate_manifest(payload, check_mode="consume")
            finally:
                if old_env is None:
                    os.environ.pop("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES", None)
                else:
                    os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = old_env
                if old_root is None:
                    os.environ.pop("OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE", None)
                else:
                    os.environ["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = old_root

        self.assertIn(
            "source_summary_source_sha256_mismatch",
            {blocker["reason"] for blocker in rejected.blockers},
        )

    def test_rejects_broad_process_event_trace_lines_in_source_summary(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_broad_trace")
        old_env = os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES")
        os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        with temp_offline_workspace() as tmp:
            copied_log = Path(tmp) / "live-validation-logs" / RUN_ID / "Obelisk.log"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            lines = runtime_log_lines()
            lines.insert(
                5,
                "[info] ProcessEvent detour hit #1 object=0x111 function=0x222 params=0x333 "
                "fname_index=6252 fname_number=0",
            )
            copied_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
            try:
                payload = manifest_for_copied_log(copied_log, log_lines=lines)
                rejected = checker.validate_manifest(payload, check_mode="consume")
            finally:
                if old_env is None:
                    os.environ.pop("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES", None)
                else:
                    os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = old_env

        self.assertIn(
            "source_summary_runtime_posture_mismatch",
            {blocker["reason"] for blocker in rejected.blockers},
        )
        self.assertIn(
            "$.source_summary.runtime.broad_process_event_trace_lines",
            {blocker.get("label") for blocker in rejected.blockers},
        )

    def test_rejects_symlinked_operational_copied_log_run_id_alias(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_symlink")
        old_roots = checker.APPROVED_OFFLINE_WORKSPACE_ROOTS
        actual_run_id = "20260601T121500Z-player-principal-lifecycle"
        with tempfile.TemporaryDirectory() as tmp:
            offline_root = Path(tmp)
            actual_log = offline_root / "live-validation-logs" / actual_run_id / "Obelisk.log"
            claimed_log = offline_root / "live-validation-logs" / RUN_ID / "Obelisk.log"
            actual_log.parent.mkdir(parents=True, exist_ok=True)
            claimed_log.parent.mkdir(parents=True, exist_ok=True)
            actual_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            claimed_log.symlink_to(actual_log)
            checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (offline_root,)
            try:
                payload = manifest_for_copied_log(actual_log)
                payload["operational_window"]["copied_log"]["path"] = str(claimed_log)
                payload.pop("output_artifact_identity")
                add_output_artifact_identity(payload)
                rejected = checker.validate_manifest(payload, check_mode="consume")
            finally:
                checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = old_roots

        self.assertIn(
            "operational_window_copied_log_path_symlink_component",
            {blocker["reason"] for blocker in rejected.blockers},
        )

    def test_source_summary_source_path_symlink_does_not_hash_or_reanalyze(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_source_symlink")
        old_roots = checker.APPROVED_OFFLINE_WORKSPACE_ROOTS
        with tempfile.TemporaryDirectory() as tmp:
            offline_root = Path(tmp)
            copied_log = offline_root / "live-validation-logs" / RUN_ID / "Obelisk.log"
            source_link = offline_root / "live-validation-logs" / RUN_ID / "source-link.log"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
            source_link.symlink_to(copied_log)
            payload = manifest_for_copied_log(copied_log)
            summary = payload["source_summary"]
            summary["evidence"]["sources"][0]["path"] = str(source_link)
            blockers: list[dict] = []
            checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (offline_root,)
            try:
                with mock.patch.object(
                    checker,
                    "sha256_file",
                    side_effect=AssertionError("sha256_file should not run for symlinked source_summary path"),
                ):
                    observed = checker.validate_runtime_summary(summary, blockers)
            finally:
                checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = old_roots

        self.assertEqual(
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
            observed,
        )
        self.assertIn(
            "source_summary_source_path_symlink_component",
            {blocker["reason"] for blocker in blockers},
        )
        self.assertNotIn(
            "source_summary_not_derived_from_copied_log",
            {blocker["reason"] for blocker in blockers},
        )

    def test_rejects_fabricated_summary_even_when_source_log_sha_matches(self) -> None:
        with temp_offline_workspace() as temp:
            copied_log = Path(temp) / "live-validation-logs" / RUN_ID / "Obelisk.log"
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("unrelated copied log without lifecycle observer evidence\n", encoding="utf-8")
            payload = manifest_for_copied_log(copied_log)
            result = self.run_checker(payload, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_requires_complete_output_artifact_identity(self) -> None:
        payload = manifest()
        payload.pop("output_artifact_identity")
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("top_level_fields_missing_required", report["blockers"])
        self.assertIn("output_artifact_identity_invalid", report["blockers"])

    def test_rejects_wrong_or_stale_output_artifact_identity(self) -> None:
        payload = manifest()
        payload["output_artifact_identity"]["artifact_kind"] = "obelisk.wrong-kind.v1"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output_artifact_identity_invalid", report["blockers"])

        payload = manifest()
        payload["output_artifact_identity"]["capture_id"] = "other-run"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output_artifact_identity_capture_id_mismatch", report["blockers"])
        self.assertIn("output_artifact_identity_hash_mismatch", report["blockers"])

        payload = manifest()
        payload["approval"]["review_note"] = "changed after identity hash"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output_artifact_identity_hash_mismatch", report["blockers"])

    def test_promote_mode_blocks_even_when_runtime_evidence_is_accepted(self) -> None:
        result = self.run_checker(manifest(), "--promote", check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("promote_blocked_until_identity_public_contract_gate", report["blockers"])
        self.assertEqual(report["remaining_blockers"], [])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["promotion_ready"])
        self.assertTrue(report["runtime_evidence_ready"])

    def test_public_and_runtime_readiness_modes_block_even_when_runtime_evidence_is_accepted(self) -> None:
        for flag, blocker in (
            ("--public-readiness", "public_readiness_blocked_until_identity_public_contract_gate"),
            ("--runtime-readiness", "runtime_readiness_blocked_until_identity_public_contract_gate"),
        ):
            with self.subTest(flag=flag):
                result = self.run_checker(manifest(), flag, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(blocker, report["blockers"])
                self.assertTrue(report["approved_runtime_evidence_present"])
                self.assertTrue(report["runtime_evidence_ready"])
                self.assertEqual(report["remaining_blockers"], [])
                self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
                self.assertFalse(report["promotion_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_quality_blockers_from_analyzer_summary(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["blockers"] = ["runtime_observer_evidence_only", "malformed_observer_lines"]
        module["malformed_observer_lines"] = 1
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])

    def test_rejects_events_before_safe_gate_counter_from_analyzer_summary(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["blockers"] = ["runtime_observer_evidence_only", "player_principal_event_before_safe_gate"]
        module["event_before_gate_lines"] = 1
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])

    def test_rejects_accepted_event_count_that_exceeds_exact_lifecycle_cases(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["accepted_count"] = 4
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_accepted_event_count_mismatch", report["blockers"])

    def test_rejects_missing_or_duplicate_observer_gate_count(self) -> None:
        for count in (0, 2):
            with self.subTest(count=count):
                payload = manifest()
                module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
                module["observer_gate_count"] = count
                if count == 2:
                    module["blockers"] = [
                        "runtime_observer_evidence_only",
                        "player_principal_observer_gate_count_mismatch",
                    ]
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("runtime_summary_observer_gate_count_mismatch", report["blockers"])

    def test_rejects_aggregated_values_without_complete_observed_event_cases(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module.pop("observed_event_cases")
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_cases_missing", report["blockers"])

    def test_rejects_mismatched_complete_observed_event_case(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["observed_event_cases"][1]["copied_bool_values"] = ["1", "1"]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])

    def test_rejects_mismatched_observed_event_status_proof_fields(self) -> None:
        cases = (
            ("apply_status", 2, "session_end_unresolved_noop"),
            ("correlation_status", 2, "missing"),
        )
        for key, value_index, value in cases:
            with self.subTest(key=key):
                payload = manifest()
                module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
                module["observed_event_cases"][value_index][key] = value
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "runtime_summary_required_observed_event_cases_missing",
                    report["blockers"],
                )
                self.assertFalse(report["approved_runtime_evidence_present"])

    def test_rejects_out_of_order_observed_lifecycle_cases(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        cases = module["observed_event_cases"]
        module["observed_event_cases"] = [
            {**cases[2], "sequence": 1},
            {**cases[0], "sequence": 2},
            {**cases[1], "sequence": 3},
        ]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_case_order_mismatch", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_extra_lifecycle_detail_values(self) -> None:
        payload = manifest()
        details = payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]
        details["principal_action"].append("public_lookup_enabled")
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_detail_values_unexpected", report["blockers"])

    def test_rejects_mismatched_lifecycle_detail_status_values(self) -> None:
        cases = (
            ("apply_status", ["session_end_unresolved_noop"]),
            ("correlation_status", ["missing"]),
        )
        for key, value in cases:
            with self.subTest(key=key):
                payload = manifest()
                details = payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
                    "ShooterGameMode.OnLogout"
                ]["details"]
                details[key] = value
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("runtime_summary_detail_values_missing", report["blockers"])
                self.assertFalse(report["approved_runtime_evidence_present"])

    def test_rejects_extra_lifecycle_detail_keys(self) -> None:
        payload = manifest()
        details = payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]
        details["redacted_fields_extra"] = ["SteamId"]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_detail_keys_unexpected", report["blockers"])

    def test_rejects_extra_observed_lifecycle_case(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["observed_event_cases"].append(
            {
                "sequence": 4,
                "target": "ShooterGameMode.HandleNewPlayer",
                "role": "session_start_promoted",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "1"],
                "principal_action": "candidate_created",
            }
        )
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_case_unexpected", report["blockers"])

    def test_rejects_duplicate_rejected_start_observed_lifecycle_case(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        duplicate = copy.deepcopy(module["observed_event_cases"][1])
        duplicate["sequence"] = 4
        module["observed_event_cases"].append(duplicate)
        module["accepted_count"] = 4
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_strict_lifecycle_triplet_not_selected", report["blockers"])

    def test_rejects_zero_count_function_fname_near_miss_diagnostic_maps(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["diagnostic_candidate_count"] = 0
        module["diagnostic_candidate_reason_counts"] = {"FunctionFNameNearMiss": 1}
        module["diagnostic_candidate_read_status_counts"] = {"ok": 1}
        module["diagnostic_candidate_target_counts"] = {
            "ShooterGameMode.CheckJoinInProgress": 1,
        }
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence",
            report["blockers"],
        )
        diagnostic_details = [
            detail for detail in report["blocker_details"]
            if detail["reason"] == "runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence"
        ]
        self.assertEqual(diagnostic_details[0]["diagnostic_candidate_count"], 0)
        self.assertEqual(
            diagnostic_details[0]["diagnostic_reason_counts"],
            {"FunctionFNameNearMiss": 1},
        )

    def test_rejects_extra_observed_lifecycle_case_keys(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["observed_event_cases"][0]["raw_params"] = "redacted"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_case_keys_unexpected", report["blockers"])

    def test_rejects_extra_privacy_boundary_keys(self) -> None:
        payload = manifest()
        payload["privacy_boundary"]["steamid"] = "redacted"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("privacy_boundary_keys_unexpected", report["blockers"])
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_rejects_public_readiness_and_identity_leak_overclaims(self) -> None:
        payload = manifest()
        payload["public_sdk_ready"] = True
        payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]["steamid"] = ["76561198000000000"]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_requires_explicit_no_public_contract_surface(self) -> None:
        cases = (
            ("public_header_allowed", None, "top_level_fields_missing_required"),
            ("public_abi_ready", None, "top_level_fields_missing_required"),
            ("v1_completion_ready", None, "top_level_fields_missing_required"),
            ("public_capability_bits_now", None, "top_level_fields_missing_required"),
            ("public_callback_abi_now", None, "top_level_fields_missing_required"),
            ("public_header_allowed", True, "public_header_allowed_not_false"),
            ("public_abi_ready", True, "public_abi_ready_not_false"),
            ("v1_completion_ready", True, "v1_completion_ready_not_false"),
            ("public_capability_bits_now", ["player_identity"], "public_capability_bits_now_not_empty"),
            ("public_callback_abi_now", ["on_player_identity"], "public_callback_abi_now_not_empty"),
        )
        for key, value, blocker in cases:
            with self.subTest(key=key, value=value):
                payload = manifest()
                if value is None:
                    payload.pop(key)
                else:
                    payload[key] = value
                payload.pop("output_artifact_identity")
                add_output_artifact_identity(payload)
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(blocker, report["blockers"])

    def test_rejects_extended_private_identity_terms_from_current_notes(self) -> None:
        payload = manifest()
        payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]["permission_state"] = ["admin"]
        payload["consumer_boundary_cases"][0]["chat_text"] = "redacted"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_rejects_positive_capability_claim_inside_extra_non_claims(self) -> None:
        payload = manifest()
        payload["non_claims"].append("public player identity ready with command reply support")
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_accepts_runtime_observer_analyzer_non_claims_and_triplet_metadata(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]

        self.assertIn("complete_lifecycle_event_triplet_candidate_present", module)
        self.assertIn("accepted_lifecycle_role_set_present", module)
        self.assertIn("complete_accepted_lifecycle_role_triplet_present", module)
        self.assertIn(
            "does not promote player identity, runtime readiness, public SDK readiness, or v1 completion",
            payload["source_summary"]["non_claims"],
        )

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])
        self.assertNotIn("forbidden_public_capability_or_readiness_claim", report["blockers"])
        self.assertNotIn("forbidden_lifecycle_role_alias_claim", report["blockers"])

    def test_allows_internal_event_split_summary_counts_without_role_alias_claim(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        split_summary = module["player_principal_lifecycle_event_split_summary"]
        split_summary["accepted_exact_check_join_observer_event_count"] = 1
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("forbidden_lifecycle_role_alias_claim", report["blockers"])

    def test_rejects_source_summary_lifecycle_role_alias_claim(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["role_alias"] = {
            "alias": "session_start_rejected",
            "target": "ShooterGameMode.CheckJoinInProgress",
            "counts_as_role": True,
        }
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_lifecycle_role_alias_claim", report["blockers"])
        self.assertIn(
            "$.source_summary.modules.player_principal_lifecycle.role_alias",
            [detail.get("label") for detail in report["blocker_details"]],
        )

    def test_rejects_identity_or_ue_internal_leakage_inside_event_split_summary(self) -> None:
        for key, value in (
            ("player_name", "SyntheticPlayer"),
            ("ue_pointer", "0x12345678"),
            ("raw_params", {"uobject": "0x1234"}),
        ):
            with self.subTest(key=key):
                payload = manifest()
                module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
                module["player_principal_lifecycle_event_split_summary"][key] = value
                payload.pop("output_artifact_identity")
                add_output_artifact_identity(payload)

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_rejects_identity_or_ue_internal_leakage_inside_strict_triplet_candidate_summary(self) -> None:
        for key, value in (
            ("player_name", "SyntheticPlayer"),
            ("ue_pointer", "0x12345678"),
            ("raw_params", {"uobject": "0x1234"}),
        ):
            with self.subTest(key=key):
                payload = manifest()
                module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
                module["strict_lifecycle_triplet_candidate_summary"]["unsafe_nested"] = {
                    key: value,
                }
                payload.pop("output_artifact_identity", None)
                add_output_artifact_identity(payload)

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])
                self.assertIn(
                    f"$.source_summary.modules.player_principal_lifecycle."
                    f"strict_lifecycle_triplet_candidate_summary.unsafe_nested.{key}",
                    [detail["label"] for detail in report["blocker_details"]],
                )

    def test_rejects_lifecycle_metadata_positive_alias_outside_runtime_summary_module(self) -> None:
        payload = manifest()
        payload["source_summary"]["accepted_lifecycle_role_set_present"] = True
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_not_derived_from_copied_log", report["blockers"])

    def test_rejects_positive_claim_inside_runtime_observer_extra_non_claim(self) -> None:
        payload = manifest()
        payload["source_summary"]["non_claims"].append(
            "does not promote identity; runtime readiness is ready"
        )
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_public_capability_claim_after_unrelated_negative_clause(self) -> None:
        for claim in (
            ("non_claims", "not blocking public SDK ready"),
            ("review_note", "does not promote identity; public SDK ready"),
            ("review_note", "does not promote identity and public SDK ready"),
            ("non_claims", "does not authorize commands but runtime ready"),
            ("non_claims", "does not authorize commands while public SDK ready"),
            ("review_note", "does not promote identity however public\tSDK\tready"),
            ("review_note", "does not promote identity then runtime   ready"),
            ("review_note", "request pack counts as approved runtime evidence"),
        ):
            with self.subTest(claim=claim):
                payload = manifest()
                if claim[0] == "non_claims":
                    payload["non_claims"].append(claim[1])
                else:
                    payload["approval"]["review_note"] = claim[1]
                payload.pop("output_artifact_identity")
                add_output_artifact_identity(payload)
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_missing_or_empty_review_provenance(self) -> None:
        for key, value in (
            ("reviewed_by", None),
            ("review_note", None),
            ("reviewed_by", "   "),
            ("review_note", ""),
        ):
            with self.subTest(key=key, value=value):
                payload = manifest()
                if value is None:
                    payload["approval"].pop(key)
                else:
                    payload["approval"][key] = value
                payload.pop("output_artifact_identity")
                add_output_artifact_identity(payload)
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"approval_{key}_missing_or_empty", report["blockers"])

    def test_rejects_identity_or_ue_terms_in_review_provenance_even_when_negated(self) -> None:
        for key, value in (
            ("review_note", "does not expose Steam IDs"),
            ("reviewed_by", "raw_params reviewer"),
        ):
            with self.subTest(key=key):
                payload = manifest()
                payload["approval"][key] = value
                payload.pop("output_artifact_identity")
                add_output_artifact_identity(payload)
                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"approval_{key}_forbidden_identity_or_ue_text", report["blockers"])

    def test_rejects_live_server_source_paths_in_wrapped_summary(self) -> None:
        payload = manifest()
        payload["source_summary"]["evidence"]["sources"][0]["path"] = "/servidor/ark/obelisk/logs/live.log"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_source_path_not_copied_or_offline", report["blockers"])

    def test_rejects_runtime_summary_or_window_paths_outside_approved_offline_workspace(self) -> None:
        payload = manifest()
        outside_path = f"/tmp/live-validation-logs/{RUN_ID}/Obelisk.log"
        payload["source_summary"]["evidence"]["sources"][0]["path"] = outside_path
        payload["operational_window"]["copied_log"]["path"] = outside_path
        payload["operational_window"]["copied_log"]["path_status"] = "unprotected_offline"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_source_path_not_approved_offline_workspace", report["blockers"])
        self.assertIn("operational_window_copied_log_path_status_mismatch", report["blockers"])
        self.assertIn("operational_window_copied_log_path_not_approved_offline_workspace", report["blockers"])

    def test_rejects_multiple_runtime_summary_sources(self) -> None:
        payload = manifest()
        payload["source_summary"]["evidence"]["sources"].append(
            dict(payload["source_summary"]["evidence"]["sources"][0])
        )
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_sources_not_exactly_one", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_extra_runtime_summary_source_provenance_fields(self) -> None:
        payload = manifest()
        payload["source_summary"]["evidence"]["sources"][0]["original_live_path"] = (
            "/servidor/ark/ShooterGame/Saved/Logs/Obelisk.log"
        )
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_source_keys_unexpected", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_operational_window_mismatch(self) -> None:
        payload = manifest()
        payload["operational_window"]["copied_log"]["sha256"] = hashlib.sha256(b"other").hexdigest()
        payload["operational_window"]["obelisk_commit"] = "other-commit"
        payload["operational_window"]["approval"] = "standing approval"
        payload["operational_window"]["approved_window"]["start_utc"] = "not-utc"
        payload["operational_window"]["notice_sent"] = "maybe"
        payload["operational_window"]["posture"]["dispatch_limit"] = "1"
        payload["operational_window"]["log_budget"] = "11"
        payload["operational_window"]["non_claims"] = ["window manifest acceptance is operational posture only"]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_copied_log_sha256_mismatch", report["blockers"])
        self.assertIn("operational_window_obelisk_commit_mismatch", report["blockers"])
        self.assertIn("operational_window_approval_mismatch", report["blockers"])
        self.assertIn("operational_window_approved_window_start_utc_invalid", report["blockers"])
        self.assertIn("operational_window_notice_sent_invalid", report["blockers"])
        self.assertIn("operational_window_posture_mismatch", report["blockers"])
        self.assertIn("operational_window_log_budget_mismatch", report["blockers"])
        self.assertIn("operational_window_non_claims_mismatch", report["blockers"])
        self.assertIn("operational_window_manifest_replay_mismatch", report["blockers"])

    def test_rejects_stale_window_manifest_sha_before_identity_gate(self) -> None:
        payload = manifest()
        manifest_path = Path(payload["operational_window"]["manifest"]["path"])
        payload["operational_window"]["manifest"]["sha256"] = hashlib.sha256(
            b"stale-window-manifest"
        ).hexdigest()
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("operational_window_artifact_sha256_mismatch", report["blockers"])
        self.assertIn("operational_window_manifest_replay_mismatch", report["blockers"])
        sha_detail = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "operational_window_artifact_sha256_mismatch"
            and detail["label"] == "$.operational_window.manifest.sha256"
        )
        self.assertEqual(sha_detail["path"], str(manifest_path))
        self.assertIn(
            {
                "reason": "operational_window_artifact_sha256_mismatch",
                "label": "$.operational_window.manifest.sha256",
                "expected": payload["operational_window"]["manifest"]["sha256"],
                "actual": sha_detail["actual"],
                "path": str(manifest_path),
            },
            report["artifact_path_issues"],
        )

    def test_rejects_missing_required_sibling_artifact_with_exact_path(self) -> None:
        payload = manifest()
        observer_env_path = Path(payload["operational_window"]["observer_env"]["path"])
        observer_env_path.unlink()

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("operational_window_required_sibling_artifact_missing", report["blockers"])
        self.assertIn("operational_window_artifact_file_missing", report["blockers"])
        sibling_detail = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "operational_window_required_sibling_artifact_missing"
            and detail["label"] == "$.operational_window.observer_env.path"
        )
        self.assertEqual(sibling_detail["expected"], str(observer_env_path))
        file_detail = next(
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "operational_window_artifact_file_missing"
            and detail["label"] == "$.operational_window.observer_env.path"
        )
        self.assertEqual(file_detail["expected"], str(observer_env_path))
        self.assertEqual(file_detail["path"], str(observer_env_path))
        self.assertIn(
            {
                "reason": "operational_window_required_sibling_artifact_missing",
                "label": "$.operational_window.observer_env.path",
                "expected": str(observer_env_path),
            },
            report["artifact_path_issues"],
        )
        self.assertIn(
            {
                "reason": "operational_window_artifact_file_missing",
                "label": "$.operational_window.observer_env.path",
                "expected": str(observer_env_path),
                "path": str(observer_env_path),
            },
            report["artifact_path_issues"],
        )

    def test_rejects_missing_post_restart_preflight_when_installed_runtime_replaced(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        post_restart = copied_log.parent / "post-restart-preflight.env"
        post_restart.unlink()

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("operational_window_post_restart_preflight_sidecar_missing", report["blockers"])
        self.assertIn(
            {
                "reason": "operational_window_post_restart_preflight_sidecar_missing",
                "label": "$.operational_window.post_restart_preflight.path",
                "expected": str(post_restart),
            },
            report["artifact_path_issues"],
        )

    def test_rejects_post_restart_preflight_overclaim_flags(self) -> None:
        cases = (
            (
                "runtime_evidence_ready",
                "runtime_evidence_ready=false",
                "runtime_evidence_ready=true",
                "operational_window_post_restart_preflight_sidecar_runtime_evidence_ready_not_false",
            ),
            (
                "post_restart_counts_as_evidence",
                "post_restart_preflight_counts_as_approved_runtime_evidence=false",
                "post_restart_preflight_counts_as_approved_runtime_evidence=true",
                "operational_window_post_restart_preflight_sidecar_post_restart_preflight_counts_as_approved_runtime_evidence_not_false",
            ),
        )
        for name, old, new, expected_blocker in cases:
            with self.subTest(name=name):
                payload = manifest()
                copied_log = Path(payload["operational_window"]["copied_log"]["path"])
                post_restart = copied_log.parent / "post-restart-preflight.env"
                post_restart.write_text(
                    post_restart.read_text(encoding="utf-8").replace(old, new),
                    encoding="utf-8",
                )

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assert_runtime_evidence_and_public_readiness_blocked(report)
                self.assertIn(expected_blocker, report["blockers"])

    def test_rejects_stale_or_deleted_installed_libobelisk_replacement_sidecar(self) -> None:
        cases = (
            (
                "stale_copied_log_sha",
                lambda text, sha: text.replace(
                    f"copied_log_sha256={sha}",
                    f"copied_log_sha256={'3' * 64}",
                ),
                "operational_window_installed_libobelisk_sidecar_copied_log_sha256_mismatch",
            ),
            (
                "deleted_libobelisk_mapping",
                lambda text, _sha: text.replace(
                    "deleted_libobelisk_mapping_present=false",
                    "deleted_libobelisk_mapping_present=true",
                ),
                "operational_window_installed_libobelisk_sidecar_deleted_libobelisk_mapping_present",
            ),
        )
        for name, mutate, expected_blocker in cases:
            with self.subTest(name=name):
                payload = manifest()
                copied_log = Path(payload["operational_window"]["copied_log"]["path"])
                sidecar = copied_log.parent / "installed-libobelisk.env"
                original = sidecar.read_text(encoding="utf-8")
                sidecar.write_text(
                    mutate(original, payload["operational_window"]["copied_log"]["sha256"]),
                    encoding="utf-8",
                )

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assert_runtime_evidence_and_public_readiness_blocked(report)
                self.assertIn(expected_blocker, report["blockers"])

    def test_rejects_missing_window_manifest_sibling_artifact_with_exact_path(self) -> None:
        payload = manifest()
        manifest_path = Path(payload["operational_window"]["manifest"]["path"])
        manifest_path.unlink()

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("operational_window_required_sibling_artifact_missing", report["blockers"])
        self.assertIn("operational_window_artifact_file_missing", report["blockers"])
        self.assertIn("operational_window_manifest_check_failed", report["blockers"])
        self.assertIn(
            {
                "reason": "operational_window_required_sibling_artifact_missing",
                "label": "$.operational_window.manifest.path",
                "expected": str(manifest_path),
            },
            report["artifact_path_issues"],
        )

    def test_rejects_missing_copied_obelisk_log_file_with_exact_path(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        copied_log.unlink()

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("source_summary_source_file_missing", report["blockers"])
        self.assertIn(
            {
                "reason": "source_summary_source_file_missing",
                "label": "$.source_summary.evidence.sources[0].path",
                "expected": str(copied_log),
                "path": str(copied_log),
            },
            report["artifact_path_issues"],
        )

    def test_rejects_preflight_post_alias_when_canonical_sibling_is_missing(self) -> None:
        payload = manifest()
        preflight_post = payload["operational_window"]["preflight"]["post"]
        original = Path(preflight_post["path"])
        alternate = original.parent.parent / "sidecar-aliases" / RUN_ID / "preflight-post.json"
        alternate.parent.mkdir(parents=True, exist_ok=True)
        alternate.write_bytes(original.read_bytes())
        original.unlink()
        preflight_post["path"] = str(alternate)
        preflight_post["sha256"] = hashlib.sha256(alternate.read_bytes()).hexdigest()
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertIn("operational_window_required_sibling_artifact_missing", report["blockers"])
        self.assertIn("operational_window_sidecar_not_exact_copied_log_sibling", report["blockers"])
        self.assertIn("operational_window_manifest_replay_mismatch", report["blockers"])
        self.assertIn(
            {
                "reason": "operational_window_required_sibling_artifact_missing",
                "label": "$.operational_window.preflight.post.path",
                "expected": str(original),
            },
            report["artifact_path_issues"],
        )

    def test_rejects_stale_copied_log_sha_before_identity_gate(self) -> None:
        payload = manifest()
        stale_sha = hashlib.sha256(b"stale-copied-log").hexdigest()
        payload["source_summary"]["evidence"]["sources"][0]["sha256"] = stale_sha
        payload["operational_window"]["copied_log"]["sha256"] = stale_sha
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assert_runtime_evidence_and_public_readiness_blocked(report)
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("source_summary_source_sha256_mismatch", report["blockers"])
        self.assertIn("source_summary_not_derived_from_copied_log", report["blockers"])
        self.assertIn("operational_window_manifest_replay_mismatch", report["blockers"])

    def test_rejects_operational_window_log_path_outside_live_validation_run_shape(self) -> None:
        payload = manifest()
        source_path = Path(payload["source_summary"]["evidence"]["sources"][0]["path"])
        wrong_path = source_path.parent.parent.parent / RUN_ID / "Obelisk.log"
        payload["source_summary"]["evidence"]["sources"][0]["path"] = str(wrong_path)
        payload["operational_window"]["copied_log"]["path"] = str(wrong_path)
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_copied_log_path_not_live_validation_run_log", report["blockers"])

    def test_rejects_source_summary_path_drift_from_operational_copied_log(self) -> None:
        payload = manifest()
        source = payload["source_summary"]["evidence"]["sources"][0]
        source_path = Path(source["path"])
        alias_path = source_path.parent.parent / "source-aliases" / RUN_ID / "Obelisk.log"
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        alias_path.write_bytes(source_path.read_bytes())
        source["path"] = str(alias_path)
        source["sha256"] = hashlib.sha256(alias_path.read_bytes()).hexdigest()
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_copied_log_path_mismatch", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_missing_source_summary_source_path_without_local_alias_resolution(self) -> None:
        payload = manifest()
        payload["source_summary"]["evidence"]["sources"][0].pop("path")
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_source_path_not_copied_or_offline", report["blockers"])
        self.assertIn("operational_window_source_summary_source_path_missing", report["blockers"])

    def test_rejects_sidecar_alias_not_exact_copied_log_sibling(self) -> None:
        payload = manifest()
        request_artifact = payload["operational_window"]["request_pack"]
        original_path = Path(request_artifact["path"])
        alias_path = original_path.parent.parent / "sidecar-aliases" / RUN_ID / "window-request.json"
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        alias_path.write_bytes(original_path.read_bytes())
        request_artifact["path"] = str(alias_path)
        request_artifact["sha256"] = hashlib.sha256(alias_path.read_bytes()).hexdigest()
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_sidecar_not_exact_copied_log_sibling", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_lifecycle_property_fname_drift_diagnostic_does_not_bypass_sibling_set(self) -> None:
        diagnostic = diagnostic_candidate_line(
            sequence=99,
            reason=LIFECYCLE_PROPERTY_FNAME_DRIFT_REASON,
        )
        lines = [*runtime_log_lines(), diagnostic]
        log_path = self.write_copied_log(lines)
        payload = manifest_for_copied_log(log_path, log_lines=lines)
        request_artifact = payload["operational_window"]["request_pack"]
        original_path = Path(request_artifact["path"])
        alias_path = original_path.parent.parent / "sidecar-aliases" / RUN_ID / "window-request.json"
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        alias_path.write_bytes(original_path.read_bytes())
        request_artifact["path"] = str(alias_path)
        request_artifact["sha256"] = hashlib.sha256(alias_path.read_bytes()).hexdigest()
        payload.pop("output_artifact_identity")
        add_output_artifact_identity(payload)

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn("operational_window_sidecar_not_exact_copied_log_sibling", report["blockers"])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )

    def test_rejects_window_request_run_id_drift_even_when_artifact_sha_is_refreshed(self) -> None:
        payload = manifest()
        request_artifact = payload["operational_window"]["request_pack"]
        request_path = Path(request_artifact["path"])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["run_id"] = "20260601T121500Z-player-principal-lifecycle"
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            request_artifact,
            json.dumps(request, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_request_pack_run_id_mismatch", report["blockers"])
        self.assertIn("operational_window_manifest_check_failed", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_split_readiness_alias_in_bound_request_sidecar(self) -> None:
        payload = manifest()
        request_artifact = payload["operational_window"]["request_pack"]
        request_path = Path(request_artifact["path"])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["audit_alias"] = {
            "claim": "public_sdk_ready",
            "status": "ready",
        }
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            request_artifact,
            json.dumps(request, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_sidecar_authorization_or_readiness_key_overclaim",
            report["blockers"],
        )
        self.assertIn("operational_window_manifest_check_failed", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_nested_approved_manifest_schema_duplicate_without_positive_flags(self) -> None:
        payload = manifest()
        payload["source_summary"]["evidence"]["audit"] = [
            {
                "schema": APPROVED_SCHEMA,
                "approved_runtime_evidence_present": False,
                "runtime_evidence_ready": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
            }
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertIn("nested_approved_runtime_manifest_schema_duplicate", report["blockers"])
        self.assertIn(
            "$.source_summary.evidence.audit[0].schema",
            [detail["label"] for detail in report["blocker_details"]],
        )

    def test_rejects_unexpected_json_sidecar_with_mixed_valid_invalid_evidence_array(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        sidecar = copied_log.parent / "stale-public-reachability-status.json"
        sidecar.write_text(
            json.dumps(
                {
                    "schema": "obelisk.player-principal-public-reachability-check.v1",
                    "entries": [
                        {"approved_runtime_evidence_present": False},
                        {"approved_runtime_evidence_present": True},
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_unexpected_json_sidecar_public_reachability_sidecar_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "operational_window_sidecar_readiness_flag_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "$.entries[1].approved_runtime_evidence_present",
            [detail.get("key_path") for detail in report["blocker_details"]],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_copied_status_sidecar_with_zero_source_overclaim_alias(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        sidecar = copied_log.parent / "copied-log-status.json"
        sidecar.write_text(
            json.dumps(
                {
                    "schema": "obelisk.player-principal-lifecycle-copied-log-status.v1",
                    "status": "blocked",
                    "source_overclaim_total_flag_count": 0,
                    "source_overclaim_summary": {"total": 0},
                    "approved_runtime_evidence_ready": False,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_unexpected_json_sidecar_copied_status_or_report_schema_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "operational_window_sidecar_source_overclaim_alias_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_unclassified_future_capture_sidecar_by_path_alias(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        sidecar = copied_log.parent / "multi-surface-beta-capture-candidate-queue.json"
        sidecar.write_text(
            json.dumps(
                {
                    "schema": "obelisk.unclassified-artifact.v1",
                    "status": "candidate_capture_plan",
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "replaces_player_principal_triplet": True,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_unexpected_json_sidecar_input_path_multi_surface_beta_capture_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "operational_window_unexpected_json_sidecar_input_path_candidate_queue_is_not_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn("operational_window_sidecar_readiness_flag_overclaim", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_multi_surface_beta_capture_pack_sidecars_by_schema_and_name(self) -> None:
        false_flags = {
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "publication_ready": False,
        }
        cases = (
            (
                "manifest.json",
                {
                    "schema": "obelisk.multi-surface-beta-capture-pack.v1",
                    "status": "candidate_capture_pack",
                    "artifact_names": [
                        "checker-command-matrix.json",
                        "manifest.json",
                        "multi-surface-capture-plan.json",
                        "non-claim-manifest.json",
                    ],
                    "non_claim_flags": false_flags,
                },
                "operational_window_unexpected_json_sidecar_multi_surface_beta_capture_pack_sidecar_not_approved_runtime_evidence",
                "operational_window_unexpected_json_sidecar_input_path_candidate_manifest_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "checker-command-matrix.json",
                {
                    "schema": "obelisk.multi-surface-beta-capture-checker-matrix.v1",
                    "status": "candidate_only",
                    "surfaces": [
                        {
                            "id": "player_principal_lifecycle",
                            "candidate_capture_only": True,
                            "requires_checker_acceptance": True,
                            "replaces_player_principal_triplet": False,
                            **false_flags,
                        }
                    ],
                },
                "operational_window_unexpected_json_sidecar_multi_surface_beta_capture_checker_matrix_sidecar_not_approved_runtime_evidence",
                "operational_window_unexpected_json_sidecar_input_path_multi_surface_beta_capture_checker_matrix_artifact_is_not_approved_runtime_evidence",
            ),
            (
                "non-claim-manifest.json",
                {
                    "schema": "obelisk.multi-surface-beta-capture-non-claim-manifest.v1",
                    "status": "non_authorizing_candidate_pack",
                    "surface_non_claims": [
                        {
                            "id": "player_principal_lifecycle",
                            "candidate_capture_only": True,
                            "requires_checker_acceptance": True,
                            "replaces_player_principal_triplet": False,
                            **false_flags,
                        }
                    ],
                },
                "operational_window_unexpected_json_sidecar_multi_surface_beta_capture_non_claim_manifest_sidecar_not_approved_runtime_evidence",
                "operational_window_unexpected_json_sidecar_input_path_multi_surface_beta_capture_non_claim_manifest_artifact_is_not_approved_runtime_evidence",
            ),
        )
        for filename, sidecar_payload, expected_schema_blocker, expected_name_blocker in cases:
            with self.subTest(filename=filename):
                payload = manifest()
                copied_log = Path(payload["operational_window"]["copied_log"]["path"])
                sidecar = copied_log.parent / filename
                sidecar.write_text(json.dumps(sidecar_payload, sort_keys=True) + "\n", encoding="utf-8")

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertIn(expected_schema_blocker, report["blockers"])
                self.assertIn(expected_name_blocker, report["blockers"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_stale_approved_bundle_duplicate_sidecar_beside_valid_report(self) -> None:
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        stale = copied_log.parent / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.stale.json"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale_payload = copy.deepcopy(payload)
        stale_payload["operational_window"]["run_id"] = "20260601T121500Z-player-principal-lifecycle"
        stale_payload["operational_window"]["target"] = {"instance": "arkserver3", "map": "Genesis2"}
        stale_payload["operational_window"]["copied_log"]["sha256"] = hashlib.sha256(b"stale-log").hexdigest()
        stale.write_text(json.dumps(stale_payload, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "operational_window_unexpected_approved_bundle_json_sidecar_approved_runtime_manifest_sidecar_not_checked_bundle_output",
            report["blockers"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_stale_generated_runtime_summary_sidecar_beside_valid_report(self) -> None:
        cases = (
            (
                "path_drift",
                lambda summary, copied_log: summary["evidence"]["sources"][0].update(
                    {
                        "path": str(
                            copied_log.parent.parent
                            / "20260601T121500Z-player-principal-lifecycle"
                            / "Obelisk.log"
                        )
                    }
                ),
                "approved_bundle_generated_sidecar_source_log_mismatch",
            ),
            (
                "sha_drift",
                lambda summary, _copied_log: summary["evidence"]["sources"][0].update(
                    {"sha256": hashlib.sha256(b"stale-generated-summary").hexdigest()}
                ),
                "approved_bundle_generated_sidecar_source_log_sha256_mismatch",
            ),
        )
        for name, mutate, expected_blocker in cases:
            with self.subTest(name=name):
                payload = manifest()
                copied_log = Path(payload["operational_window"]["copied_log"]["path"])
                bundle_dir = copied_log.parent / "approved-bundle"
                bundle_dir.mkdir(parents=True, exist_ok=True)
                stale_summary = copy.deepcopy(payload["source_summary"])
                mutate(stale_summary, copied_log)
                (bundle_dir / "runtime-observer-summary.json").write_text(
                    json.dumps(stale_summary, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(report["approved_runtime_evidence_present"])
                self.assertFalse(report["runtime_evidence_ready"])
                self.assertIn(expected_blocker, report["blockers"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_expected_generated_bundle_report_sidecar_current_turn_overclaim(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_generated_bundle")
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        bundle_dir = copied_log.parent / "approved-bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_report_path = bundle_dir / "evidence-bundle-report.json"
        bundle_report = {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
            "status": "accepted",
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "remaining_blockers": [],
            "next_blocker": "identity_public_contract_gate_missing",
            "current_route_blocker": None,
            "required_artifact_status": "accepted",
            "source_log": str(copied_log),
            "approved_bundle_path": str(bundle_dir / "approved-runtime-principal-lifecycle-evidence.json"),
            "operational_window": {"run_id": payload["operational_window"]["run_id"]},
            "bundle_report_counts_as_approved_runtime_evidence": False,
            "current_turn_runtime_authorized": False,
        }
        bundle_report["bundle_report_identity"] = checker.expected_bundle_report_identity(bundle_report)
        bundle_report_path.write_text(json.dumps(bundle_report, sort_keys=True) + "\n", encoding="utf-8")

        accepted = self.run_checker(payload)
        accepted_report = json.loads(accepted.stdout)
        self.assertTrue(accepted_report["approved_runtime_evidence_present"])
        self.assertEqual(accepted_report["next_blocker"], "identity_public_contract_gate_missing")

        bundle_report["current_turn_runtime_authorized"] = True
        bundle_report["bundle_report_identity"] = checker.expected_bundle_report_identity(bundle_report)
        bundle_report_path.write_text(json.dumps(bundle_report, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "approved_bundle_generated_sidecar_false_flag_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "$.current_turn_runtime_authorized",
            [detail.get("key_path") for detail in report["blocker_details"]],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_expected_generated_bundle_report_sidecar_acceptance_alias(self) -> None:
        checker = load_script_module(SCRIPT, "test_player_principal_approved_checker_generated_acceptance_alias")
        payload = manifest()
        copied_log = Path(payload["operational_window"]["copied_log"]["path"])
        bundle_dir = copied_log.parent / "approved-bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle_report_path = bundle_dir / "evidence-bundle-report.json"
        bundle_report = {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
            "status": "accepted",
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "remaining_blockers": [],
            "next_blocker": "identity_public_contract_gate_missing",
            "current_route_blocker": None,
            "required_artifact_status": "accepted",
            "source_log": str(copied_log),
            "approved_bundle_path": str(bundle_dir / "approved-runtime-principal-lifecycle-evidence.json"),
            "operational_window": {"run_id": payload["operational_window"]["run_id"]},
            "bundle_report_counts_as_approved_runtime_evidence": False,
            "runtimeEvidenceAcceptance": True,
        }
        bundle_report["bundle_report_identity"] = checker.expected_bundle_report_identity(bundle_report)
        bundle_report_path.write_text(json.dumps(bundle_report, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertIn(
            "approved_bundle_generated_sidecar_authorization_or_readiness_alias_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "$.runtimeEvidenceAcceptance",
            [detail.get("key_path") for detail in report["blocker_details"]],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_nested_operational_window_and_approval_overclaim_keys(self) -> None:
        payload = manifest()
        payload["approval"]["server_restart_authorized_by_this_manifest"] = True
        payload["operational_window"]["runtime_work_authorized"] = True
        payload["operational_window"]["copied_log"]["uobject_pointer"] = "redacted"
        payload["operational_window"]["posture"]["plugin_delivery_ready"] = True
        payload["operational_window"]["rollback"]["manual_followup_required"] = True
        payload["operational_window"]["claims"]["runtime_ready_claim"] = "ready"
        payload["consumer_boundary_cases"][0]["lookup_token_usable"] = True
        payload["promotion_gate"]["public_contract_ready"] = True
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approval_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_copied_log_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_posture_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_rollback_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_claims_keys_unexpected", report["blockers"])
        self.assertIn("consumer_boundary_case_keys_unexpected", report["blockers"])
        self.assertIn("promotion_gate_keys_unexpected", report["blockers"])

    def test_rejects_operational_window_rollback_delta_drift(self) -> None:
        payload = manifest()
        payload["operational_window"]["rollback"]["delta"] = "removed_observer_markers_only"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_rollback_delta_mismatch", report["blockers"])

    def test_rejects_identity_or_ue_leakage_inside_operational_window(self) -> None:
        payload = manifest()
        payload["operational_window"]["steamid"] = "76561198000000000"
        payload["operational_window"]["raw_params"] = {"uobject": "0x1234"}
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_rejects_mixed_observer_modules(self) -> None:
        payload = manifest()
        payload["source_summary"]["modules"]["chat"] = {
            "accepted_count": 0,
            "functions": {},
        }
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_unexpected_modules_present", report["blockers"])

    def test_rejects_missing_rejected_start_or_fail_closed_consumer_case(self) -> None:
        payload = copy.deepcopy(manifest())
        details = payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.CheckJoinInProgress"
        ]["details"]
        details["role"] = []
        payload["consumer_boundary_cases"] = payload["consumer_boundary_cases"][:1]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_detail_values_missing", report["blockers"])
        self.assertIn("consumer_boundary_cases_missing", report["blockers"])

    def test_rejects_consumer_boundary_case_that_claims_runtime_observation(self) -> None:
        payload = copy.deepcopy(manifest())
        payload["consumer_boundary_cases"][0]["runtime_observed"] = True
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("consumer_boundary_runtime_observed_not_false", report["blockers"])

    def test_rejects_consumer_boundary_case_without_assertion_provenance(self) -> None:
        payload = copy.deepcopy(manifest())
        payload["consumer_boundary_cases"][0].pop("provenance")
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("consumer_boundary_case_provenance_mismatch", report["blockers"])


if __name__ == "__main__":
    unittest.main()
