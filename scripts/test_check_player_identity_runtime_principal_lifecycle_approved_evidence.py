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
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
RUN_ID = "20260601T120000Z-player-principal-lifecycle"
TEST_COMMIT = "a" * 40
OFFLINE_WORKSPACE = Path("/servidor/ark/workspace-offline")
LIVE_TEMP_DIRS: list[tempfile.TemporaryDirectory[str]] = []
APPROVED_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"


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


def operational_sidecars(copied_log: Path) -> dict[str, dict]:
    workspace = copied_log.parents[2]
    live_dir = copied_log.parent
    sidecar_dir = workspace / "player-principal-preflight" / RUN_ID
    copied_log_sha256 = hashlib.sha256(copied_log.read_bytes()).hexdigest()
    manifest_path = live_dir / "window-manifest.env"
    request_pack_path = sidecar_dir / "window-request.json"
    observer_env_path = sidecar_dir / "observer-window.env"
    preflight_pre_path = live_dir / "preflight-pre.txt"
    preflight_post_path = live_dir / "preflight-post.txt"
    target = {"instance": "arkserver2", "map": "TheIsland"}
    approved_window = {
        "start_utc": "2026-06-01T12:00:00Z",
        "end_utc": "2026-06-01T12:10:00Z",
    }
    marker_set = [
        "enable-process-event-hook",
        "disable-plugins",
        "allow-observer-debug-window",
        "allow-experimental-observers",
        "enable-player-principal-lifecycle-observer",
    ]
    forbidden_markers = [
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
        "enable-structure-reflection",
        "enable-item-return-events",
    ]
    non_claims = [
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
    request = write_sidecar(
        request_pack_path,
        json.dumps(
            {
                "schema": "obelisk.player-principal-lifecycle-window-request.v1",
                "status": "candidate_only_request_pack",
                "approval_required": "current-turn operator-approved runtime window, not standing approval",
                "target": target,
                "run_id": RUN_ID,
                "ark_binary_sha256": SHA,
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
                "marker_set": marker_set,
                "forbidden_markers": forbidden_markers,
                "rollback": {
                    "owner": "operator",
                    "delta": "remove observer env and markers, preserve stable enable-process-event-hook and disable-plugins",
                },
                "non_claims": non_claims,
            },
            sort_keys=True,
        )
        + "\n",
    )
    observer_env = write_sidecar(
        observer_env_path,
        "\n".join(
            [
                "OBELISK_INSTANCE_ID=arkserver2",
                "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1",
                "OBELISK_DISABLE_PLUGINS=1",
                "OBELISK_WRAPPER_PROFILE=observer-debug",
                "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1",
                f"OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256={SHA}",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0",
                "OBELISK_PE_TRACE_LIMIT=0",
            ]
        )
        + "\n",
    )
    preflight_pre = write_sidecar(
        preflight_pre_path,
        "player_principal_lifecycle_preflight=ok mode=observer-window instance=arkserver2\n",
    )
    preflight_post = write_sidecar(
        preflight_post_path,
        "player_principal_lifecycle_preflight=ok mode=stable instance=arkserver2\n",
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
        "public_sdk_ready": False,
        "runtime_ready": False,
        "approval": {
            "runtime_evidence_reviewed": True,
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
            },
            "claims": {"delivery_claim": "none", "principal_claim": "none"},
            "user_policy": "no_regular_users",
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
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
        "public_sdk_ready": False,
        "runtime_ready": False,
        "approval": {
            "runtime_evidence_reviewed": True,
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
            },
            "claims": {"delivery_claim": "none", "principal_claim": "none"},
            "user_policy": "no_regular_users",
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
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
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["runtime_evidence_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
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
            ),
            (
                "observer_env",
                lambda payload: payload["operational_window"]["observer_env"],
                lambda path: path.read_text(encoding="utf-8").replace(
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0\n",
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=1\n",
                ),
            ),
            (
                "preflight_pre",
                lambda payload: payload["operational_window"]["preflight"]["pre"],
                lambda path: path.read_text(encoding="utf-8").replace(
                    "mode=observer-window",
                    "mode=stable",
                ),
            ),
        )
        for name, artifact_for_payload, mutate in cases:
            with self.subTest(sidecar=name):
                payload = manifest()
                artifact = artifact_for_payload(payload)
                path = Path(artifact["path"])
                self.rewrite_sidecar_and_refresh_identity(payload, artifact, mutate(path))
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
        payload["operational_window"]["posture"]["dispatch_limit"] = "1"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_copied_log_sha256_mismatch", report["blockers"])
        self.assertIn("operational_window_obelisk_commit_mismatch", report["blockers"])
        self.assertIn("operational_window_posture_mismatch", report["blockers"])

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
