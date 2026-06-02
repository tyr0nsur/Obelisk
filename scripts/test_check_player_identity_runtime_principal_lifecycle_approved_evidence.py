#!/usr/bin/env python3
"""Tests for check_player_identity_runtime_principal_lifecycle_approved_evidence.py."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
RUN_ID = "20260601T120000Z-player-principal-lifecycle"
TEST_COMMIT = "a" * 40
OFFLINE_WORKSPACE = Path("/servidor/ark/workspace-offline")
LIVE_TEMP_DIRS: list[tempfile.TemporaryDirectory[str]] = []
APPROVED_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
WINDOW_NON_CLAIMS = [
    "window manifest acceptance is operational posture only",
    "does not promote player identity, lookup, permissions, commands, ResourceHandle, mutation, return override, plugin delivery, public SDK, or runtime readiness",
    "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
]

from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    APPROVAL_TEXT,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    NON_CLAIMS,
    WINDOW_MARKERS,
    env_lines,
    markdown_request,
    operator_approval_receipt_payload,
    operator_live_ops_brief,
    post_window_replay_contract,
)


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
    spec.loader.exec_module(module)
    return module


def temp_offline_workspace() -> tempfile.TemporaryDirectory[str]:
    if not OFFLINE_WORKSPACE.is_dir():
        raise unittest.SkipTest(f"approved offline workspace missing: {OFFLINE_WORKSPACE}")
    return tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=OFFLINE_WORKSPACE)


def runtime_log_lines() -> list[str]:
    return [
        "[info]  Obelisk Runtime Loaded Native (LD_PRELOAD)",
        "[info] ProcessEvent vtable-derived pattern candidates found: 1",
        "[info] ProcessEvent candidate[0] = 0x1d34e20",
        "[info] Found ProcessEvent at address: 0x1d34e20",
        "[info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x767c6aaa4000",
        "[info] ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.",
        "[warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.",
        f"[info] PlayerPrincipalLifecycleObserver enabled binary_sha256={SHA} "
        "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
        "delivery_claim=none principal_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=candidate_created principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=none principal_id_logged=false principal_generation_logged=false "
        "delivery_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
        "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
        "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
        "principal_action=candidate_invalidated principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
    ]


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
        "marker_dir": f"/servidor/ark/obelisk/state/instances/{instance}",
        "offline_only": False,
        "allow_stopped": False,
        "checked_at_utc": checked_at_utc,
        "posture_check": "accepted",
        "non_claim": "preflight only; not runtime approval and not permission to touch servers",
    }
    return json.dumps(payload, sort_keys=True) + "\n"


def operational_sidecars(copied_log: Path) -> dict[str, dict]:
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
    target = {"instance": "arkserver2", "map": "TheIsland"}
    approved_window = {
        "start_utc": "2026-06-01T12:00:00Z",
        "end_utc": "2026-06-01T12:10:00Z",
    }
    prepared_at_utc = "2026-06-01T11:55:00Z"
    request_args = type(
        "Args",
        (),
        {
            "instance": "arkserver2",
            "map_name": "TheIsland",
            "binary_sha256": SHA,
        },
    )()
    observer_env_lines = env_lines(request_args)
    request_payload = {
        "schema": "obelisk.player-principal-lifecycle-window-request.v1",
        "status": "candidate_only_request_pack",
        "approval_required": APPROVAL_TEXT,
        "prepared_at_utc": prepared_at_utc,
        "target": target,
        "run_id": RUN_ID,
        "ark_binary_sha256": SHA,
        "server_binary_path": EXPECTED_SERVER_BINARY_PATH,
        "obelisk_commit": TEST_COMMIT,
        "approved_window": approved_window,
        "restart_expectation": "restart",
        "final_posture": "stable",
        "user_policy": "no_regular_users",
        "notice_path": "not_applicable",
        "copied_evidence_dir": str(live_dir),
        "copied_log_path": str(copied_log),
        "window_manifest_path": str(manifest_path),
        "observer_env_file": "observer-window.env",
        "marker_set": WINDOW_MARKERS,
        "forbidden_markers": FORBIDDEN_MARKERS,
        "rollback": {
            "owner": "operator",
            "delta": "remove observer env and markers, preserve stable enable-process-event-hook and disable-plugins",
        },
        "non_claims": NON_CLAIMS,
    }
    request_payload["operator_live_ops_brief"] = operator_live_ops_brief(
        request_payload,
        observer_env_lines,
    )
    request_payload["post_window_replay_contract"] = post_window_replay_contract(request_payload)
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
        markdown_request(request_payload, observer_env_lines),
    )
    operator_approval_receipt = write_sidecar(
        operator_approval_receipt_path,
        json.dumps(
            operator_approval_receipt_payload(
                request_payload,
                request_json_path=request_pack_path,
                request_md_path=operator_request_path,
                env_path=observer_env_path,
                operator_approved=True,
                operator_reference="test-current-turn-approval",
                approved_at_utc="2026-06-01T11:56:00Z",
            ),
            sort_keys=True,
        )
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
            checked_at_utc="2026-06-01T12:10:00Z",
        ),
    )
    manifest = write_sidecar(
        manifest_path,
        "\n".join(
            [
                f"run_id={RUN_ID}",
                f"obelisk_commit={TEST_COMMIT}",
                "target=arkserver2/TheIsland",
                "approval=current-turn operator-approved runtime window, not standing approval",
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
                "rollback_end_utc=2026-06-01T12:10:00Z",
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
    temp_dir = temp_offline_workspace()
    LIVE_TEMP_DIRS.append(temp_dir)
    log_path = Path(temp_dir.name) / "live-validation-logs" / RUN_ID / "Obelisk.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ANALYZER), "--obelisk-commit", TEST_COMMIT, str(log_path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(result.stdout)


def manifest() -> dict:
    summary = analyzer_summary()
    source = summary["evidence"]["sources"][0]
    sidecars = operational_sidecars(Path(source["path"]))
    return add_output_artifact_identity({
        "schema": APPROVED_SCHEMA,
        "artifact_status": "approved_runtime_observer_summary",
        "readiness_classification": "runtime_evidence_only",
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_allowed": False,
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
            "approval": "current-turn operator-approved runtime window, not standing approval",
            "approved_window": {"start_utc": "2026-06-01T12:00:00Z", "end_utc": "2026-06-01T12:10:00Z"},
            "actual_capture": {"start_utc": "2026-06-01T12:01:00Z", "end_utc": "2026-06-01T12:09:00Z"},
            "rollback_window": {"start_utc": "2026-06-01T12:09:00Z", "end_utc": "2026-06-01T12:10:00Z"},
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
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
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


def manifest_for_copied_log(copied_log: Path) -> dict:
    analyzer = load_script_module(ANALYZER, "test_player_principal_analyzer")
    summary = analyzer.analyze_lines(runtime_log_lines())
    source_sha256 = hashlib.sha256(copied_log.read_bytes()).hexdigest()
    summary["evidence"] = {
        "kind": "runtime-observer-log",
        "obelisk_commit": TEST_COMMIT,
        "sources": [
            {
                "path": str(copied_log),
                "sha256": source_sha256,
                "line_count": len(runtime_log_lines()),
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
            "approved_window": {"start_utc": "2026-06-01T12:00:00Z", "end_utc": "2026-06-01T12:10:00Z"},
            "actual_capture": {"start_utc": "2026-06-01T12:01:00Z", "end_utc": "2026-06-01T12:09:00Z"},
            "rollback_window": {"start_utc": "2026-06-01T12:09:00Z", "end_utc": "2026-06-01T12:10:00Z"},
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
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
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


class ApprovedRuntimePrincipalLifecycleEvidenceTests(unittest.TestCase):
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
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

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
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertEqual(report["remaining_blockers"], [])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            report["observed_runtime_cases"],
            ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        self.assertEqual(
            report["consumer_cases"],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )

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

    def test_rejects_sidecar_public_sdk_or_runtime_readiness_overclaim(self) -> None:
        payload = manifest()
        request_artifact = payload["operational_window"]["request_pack"]
        request_path = Path(request_artifact["path"])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["public_sdk_ready"] = True
        self.rewrite_sidecar_and_refresh_identity(
            payload,
            request_artifact,
            json.dumps(request, sort_keys=True) + "\n",
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_sidecar_readiness_flag_overclaim", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

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
        os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
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

        self.assertIn(
            "source_summary_source_sha256_mismatch",
            {blocker["reason"] for blocker in rejected.blockers},
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
        module["observed_event_cases"][1]["copied_bool_values"] = ["1", "0"]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])

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

    def test_rejects_duplicate_observed_lifecycle_case(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        duplicate = copy.deepcopy(module["observed_event_cases"][0])
        duplicate["sequence"] = 4
        module["observed_event_cases"].append(duplicate)
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_case_unexpected", report["blockers"])

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
            ("v1_completion_ready", None, "top_level_fields_missing_required"),
            ("public_capability_bits_now", None, "top_level_fields_missing_required"),
            ("public_callback_abi_now", None, "top_level_fields_missing_required"),
            ("public_header_allowed", True, "public_header_allowed_not_false"),
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

    def test_rejects_public_capability_claim_after_unrelated_negative_clause(self) -> None:
        for claim in (
            ("non_claims", "not blocking public SDK ready"),
            ("review_note", "does not promote identity; public SDK ready"),
            ("review_note", "does not promote identity and public SDK ready"),
            ("non_claims", "does not authorize commands but runtime ready"),
            ("non_claims", "does not authorize commands while public SDK ready"),
            ("review_note", "does not promote identity however public\tSDK\tready"),
            ("review_note", "does not promote identity then runtime   ready"),
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
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]
        details["role"] = ["session_start"]
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
