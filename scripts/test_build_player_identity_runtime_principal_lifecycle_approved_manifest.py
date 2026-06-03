#!/usr/bin/env python3
"""Tests for build_player_identity_runtime_principal_lifecycle_approved_manifest.py."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
BUILDER = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
WINDOW_CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_window_manifest.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
WINDOW_START = (datetime.now(timezone.utc) - timedelta(minutes=20)).replace(microsecond=0)
WINDOW_END = WINDOW_START + timedelta(minutes=10)
RUN_ID = WINDOW_START.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
OFFLINE_WORKSPACE = Path("/servidor/ark/workspace-offline")
TEST_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=SCRIPT_DIR.parents[0],
    text=True,
).strip()

from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    APPROVAL_TEXT,
    AUTHORIZATION_FLAGS,
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


def write_sidecar(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        "non_claim": "preflight only; not runtime approval, not approved runtime evidence, and not permission to touch servers",
    }
    return json.dumps(payload, sort_keys=True) + "\n"


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


class BuildApprovedRuntimePrincipalLifecycleManifestTests(unittest.TestCase):
    def temp_offline_workspace(self) -> tempfile.TemporaryDirectory[str]:
        if not OFFLINE_WORKSPACE.is_dir():
            self.skipTest(f"approved offline workspace missing: {OFFLINE_WORKSPACE}")
        return tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=OFFLINE_WORKSPACE)

    def write_summary(self, temp_dir: Path) -> Path:
        log_path = temp_dir / "live-validation-logs" / RUN_ID / "Obelisk.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ANALYZER), "--obelisk-commit", TEST_COMMIT, str(log_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        summary_path = temp_dir / "runtime-summary.json"
        summary_path.write_text(result.stdout, encoding="utf-8")
        return summary_path

    def write_window_check(self, temp_dir: Path, summary_path: Path) -> Path:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        source = summary["evidence"]["sources"][0]
        manifest_path = temp_dir / "live-validation-logs" / RUN_ID / "window-manifest.env"
        sidecar_dir = manifest_path.parent
        request_pack = sidecar_dir / "window-request.json"
        observer_env = sidecar_dir / "observer-window.env"
        operator_request = sidecar_dir / "operator-approval-request.md"
        operator_approval_receipt = sidecar_dir / "operator-approval-receipt.json"
        preflight_pre = manifest_path.parent / "preflight-pre.json"
        preflight_post = manifest_path.parent / "preflight-post.json"
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
            "run_id": RUN_ID,
            "status": "candidate_only_request_pack",
            "approval_required": APPROVAL_TEXT,
            "prepared_at_utc": (WINDOW_START - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ark_binary_sha256": SHA,
            "server_binary_path": EXPECTED_SERVER_BINARY_PATH,
            "obelisk_commit": summary["evidence"]["obelisk_commit"],
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            "approved_window": {
                "start_utc": WINDOW_START.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_utc": WINDOW_END.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "restart_expectation": "restart",
            "final_posture": "stable",
            "authorization_flags": dict(AUTHORIZATION_FLAGS),
            "user_policy": "no_regular_users",
            "notice_path": "not_applicable",
            "copied_evidence_dir": str(Path(source["path"]).parent),
            "copied_log_path": source["path"],
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
        request_payload["post_window_replay_contract"] = post_window_replay_contract(request_payload)
        request_payload["operator_live_ops_brief"] = operator_live_ops_brief(
            request_payload,
            observer_env_lines,
        )
        request_pack_sha256 = write_sidecar(
            request_pack,
            json.dumps(request_payload, sort_keys=True) + "\n",
        )
        observer_env_sha256 = write_sidecar(
            observer_env,
            "\n".join(observer_env_lines) + "\n",
        )
        write_sidecar(
            operator_request,
            markdown_request(request_payload, observer_env_lines),
        )
        operator_approval_receipt_sha256 = write_sidecar(
            operator_approval_receipt,
            json.dumps(
                operator_approval_receipt_payload(
                    request_payload,
                    request_json_path=request_pack,
                    request_md_path=operator_request,
                    env_path=observer_env,
                    operator_approved=True,
                    operator_reference="test-current-turn-approval",
                    approved_at_utc=(WINDOW_START - timedelta(minutes=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
                sort_keys=True,
            )
            + "\n",
        )
        preflight_pre_sha256 = write_sidecar(
            preflight_pre,
            preflight_payload(
                mode="observer-window",
                instance="arkserver2",
                run_id=RUN_ID,
                map_name="TheIsland",
                window_manifest_path=manifest_path,
                copied_log_path=Path(source["path"]),
                env_file=observer_env,
                env_sha256=observer_env_sha256,
                checked_at_utc=(WINDOW_START + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        preflight_post_sha256 = write_sidecar(
            preflight_post,
            preflight_payload(
                mode="stable",
                instance="arkserver2",
                run_id=RUN_ID,
                map_name="TheIsland",
                window_manifest_path=manifest_path,
                copied_log_path=Path(source["path"]),
                checked_at_utc=WINDOW_END.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        manifest_path.write_text(
            "\n".join(
                [
                    f"run_id={RUN_ID}",
                    f"obelisk_commit={summary['evidence']['obelisk_commit']}",
                    "target=arkserver2/TheIsland",
                    "approval=current-turn operator-approved runtime window, not standing approval",
                    f"approved_window_start_utc={WINDOW_START.strftime('%Y-%m-%dT%H:%M:%SZ')}",
                    f"approved_window_end_utc={WINDOW_END.strftime('%Y-%m-%dT%H:%M:%SZ')}",
                    f"actual_capture_start_utc={(WINDOW_START + timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')}",
                    f"actual_capture_end_utc={(WINDOW_START + timedelta(minutes=9)).strftime('%Y-%m-%dT%H:%M:%SZ')}",
                    f"copied_log_path={source['path']}",
                    f"copied_log_sha256={source['sha256']}",
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
                    f"rollback_start_utc={(WINDOW_START + timedelta(minutes=9)).strftime('%Y-%m-%dT%H:%M:%SZ')}",
                    f"rollback_end_utc={WINDOW_END.strftime('%Y-%m-%dT%H:%M:%SZ')}",
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
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        result = subprocess.run(
            [sys.executable, str(WINDOW_CHECKER), "--json", "--post-window-replay", str(manifest_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        check_path = temp_dir / "window.check.json"
        check_path.write_text(result.stdout, encoding="utf-8")
        return check_path

    def run_builder(
        self,
        source_summary: Path,
        window_check: Path,
        output: Path,
        *,
        reviewed_by: str = "runtime-reviewer",
        review_note: str = "consume-only lifecycle evidence reviewed",
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        return subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--source-summary",
                str(source_summary),
                "--window-manifest-check",
                str(window_check),
                "--output",
                str(output),
                "--reviewed-by",
                reviewed_by,
                "--review-note",
                review_note,
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def run_checker(self, manifest: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        return subprocess.run(
            [sys.executable, str(CHECKER), str(manifest), "--json", *extra_args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def test_builds_manifest_that_passes_existing_consume_checker(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            manifest_path = temp_dir / "approved-manifest.json"

            result = self.run_builder(summary_path, window_check, manifest_path)
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["schema"],
                "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
            )
            self.assertEqual(manifest["approval"]["reviewed_by"], "runtime-reviewer")
            self.assertEqual(
                manifest["approval"]["review_note"],
                "consume-only lifecycle evidence reviewed",
            )
            self.assertTrue(manifest["operational_window"]["operational_window_manifest_ready"])
            self.assertEqual(
                manifest["operational_window"]["rollback"]["delta"],
                "removed_observer_env_and_markers_preserved_disable_plugins",
            )
            self.assertEqual(manifest["operational_window"]["log_budget"], "10")
            self.assertIn(
                "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
                manifest["operational_window"]["non_claims"],
            )
            self.assertFalse(manifest["approval"]["server_operations_authorized_by_this_manifest"])
            self.assertFalse(manifest["promotion_ready"])

            checker = self.run_checker(manifest_path)
            self.assertEqual(checker.returncode, 0, checker.stderr)
            report = json.loads(checker.stdout)
            self.assertTrue(report["ready"])
            self.assertTrue(report["runtime_evidence_ready"])
            self.assertFalse(report["promotion_ready"])
            self.assertEqual(
                report["observed_runtime_cases"],
                ["observer_enable", "session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
            )

    def test_rejects_window_manifest_check_not_generated_in_post_window_replay_mode(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            payload = json.loads(window_check.read_text(encoding="utf-8"))
            payload["post_window_replay"] = False
            window_check.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            manifest_path = temp_dir / "approved-manifest.json"

            result = self.run_builder(summary_path, window_check, manifest_path)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--window-manifest-check must be generated with --post-window-replay", result.stderr)
            self.assertFalse(manifest_path.exists())

    def test_rejects_source_summary_with_broad_process_event_trace_lines(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["runtime"]["broad_process_event_trace_lines"] = 1
            summary_path.write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")
            manifest_path = temp_dir / "approved-manifest.json"

            result = self.run_builder(summary_path, window_check, manifest_path)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must not include broad ProcessEvent detour trace lines", result.stderr)
            self.assertFalse(manifest_path.exists())

    def test_rejects_generated_manifest_that_fails_consume_checker(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["modules"]["player_principal_lifecycle"].pop("observed_event_cases")
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            manifest_path = temp_dir / "approved-manifest.json"

            result = self.run_builder(summary_path, window_check, manifest_path)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("generated approved manifest failed consume checker", result.stderr)
            self.assertIn("runtime_summary_observed_event_cases_missing", result.stderr)
            self.assertFalse(manifest_path.exists())

    def test_generated_manifest_still_fails_closed_for_promote_mode(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            manifest_path = temp_dir / "approved-manifest.json"
            summary_path = self.write_summary(temp_dir)
            result = self.run_builder(summary_path, self.write_window_check(temp_dir, summary_path), manifest_path)
            self.assertEqual(result.returncode, 0, result.stderr)

            checker = self.run_checker(manifest_path, "--promote")
            self.assertNotEqual(checker.returncode, 0)
            report = json.loads(checker.stdout)
            self.assertIn("promote_blocked_until_identity_public_contract_gate", report["blockers"])
            self.assertTrue(report["runtime_evidence_ready"])
            self.assertFalse(report["promotion_ready"])

    def test_rejects_protected_source_summary_path_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "manifest.json"
            result = self.run_builder(
                Path("/servidor/ark/obelisk/logs/runtime-summary.json"),
                Path(temp) / "window.check.json",
                output,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--source-summary must not read from protected server root", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_protected_output_path_before_writing(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            output = Path("/servidor/ark/obelisk/approved-manifest.json")

            result = self.run_builder(summary_path, window_check, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output must not write under protected server root", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_symlinked_source_summary_before_reading(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            summary_link = temp_dir / "runtime-summary-link.json"
            summary_link.symlink_to(summary_path)
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_link, window_check, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--source-summary must not be a symlink", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_symlinked_output_before_writing(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            target = temp_dir / "target.json"
            target.write_text("preserve me\n", encoding="utf-8")
            output_link = temp_dir / "approved-manifest-link.json"
            output_link.symlink_to(target)

            result = self.run_builder(summary_path, window_check, output_link)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output must not be a symlink", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve me\n")

    def test_rejects_summary_generated_with_server_paths_allowed(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["evidence"]["server_paths_allowed"] = True
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            window_check = self.write_window_check(temp_dir, summary_path)
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_path, window_check, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("generated without --allow-server-path", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_summary_with_protected_inner_source_path(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["evidence"]["sources"][0]["path"] = "/servidor/ark/obelisk/logs/live.log"
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_path, window_check, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must point to copied/offline evidence", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_summary_or_window_check_outside_approved_offline_workspace(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["evidence"]["sources"][0]["path"] = f"/tmp/live-validation-logs/{RUN_ID}/Obelisk.log"
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_path, window_check, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must point under /servidor/ark/workspace-offline", result.stderr)
            self.assertFalse(output.exists())

        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            window = json.loads(window_check.read_text(encoding="utf-8"))
            window["copied_log"]["path_status"] = "unprotected_offline"
            window_check.write_text(json.dumps(window), encoding="utf-8")
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_path, window_check, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("copied_log.path_status must be approved_offline_workspace", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_summary_with_multiple_sources(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            window_check = self.write_window_check(temp_dir, summary_path)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["evidence"]["sources"].append(dict(summary["evidence"]["sources"][0]))
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_path, window_check, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("sources must contain exactly one copied/offline log", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_summary_with_mixed_observer_modules(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["modules"]["chat"] = {
                "accepted_count": 0,
                "functions": {},
            }
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            window_check = self.write_window_check(temp_dir, summary_path)
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_path, window_check, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("modules must contain only player_principal_lifecycle", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_review_text_that_would_trip_privacy_gate(self) -> None:
        with self.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            output = temp_dir / "manifest.json"
            result = self.run_builder(
                self.write_summary(temp_dir),
                temp_dir / "window.check.json",
                output,
                review_note="reviewed raw_params details",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("identity/UE-internal terms", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
