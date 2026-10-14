#!/usr/bin/env python3
"""Tests for copy_player_principal_lifecycle_ready_log.py."""

from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "copy_player_principal_lifecycle_ready_log.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
FRESH_WINDOW_START_UTC = "2026-06-06T13:55:00Z"
FRESH_WINDOW_END_UTC = "2026-06-06T14:10:00Z"
DEFAULT_TIMESTAMPS = {
    "enabled": "2026-06-06T13:55:55Z",
    "session_start": "2026-06-06T13:56:10Z",
    "session_start_rejected": "2026-06-06T13:56:20Z",
    "session_end": "2026-06-06T13:56:30Z",
}
SAFE_OFFLINE_WORKSPACE_DIR = tempfile.TemporaryDirectory(prefix="obelisk-copy-ready-safe-workspace-")
SAFE_OFFLINE_WORKSPACE = Path(SAFE_OFFLINE_WORKSPACE_DIR.name)
RUN_ID = "20260606T135500Z-player-principal-lifecycle"
EXPECTED_PREFLIGHT_NON_CLAIM = (
    "preflight only; not runtime approval, not approved runtime evidence, "
    "and not permission to touch servers"
)
EXPECTED_WINDOW_MANIFEST_NON_CLAIMS = [
    "window manifest acceptance is operational posture only",
    "does not promote player identity, lookup, permissions, commands, ResourceHandle, mutation, return override, plugin delivery, public SDK, or runtime readiness",
    "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
]


def tearDownModule() -> None:
    SAFE_OFFLINE_WORKSPACE_DIR.cleanup()


def fresh_window_args() -> tuple[str, ...]:
    return (
        "--fresh-window-start-utc",
        FRESH_WINDOW_START_UTC,
        "--fresh-window-end-utc",
        FRESH_WINDOW_END_UTC,
    )


def prefixed(timestamp: str | None, line: str) -> str:
    if timestamp is None:
        return line
    return f"[{timestamp}] {line}"


def lifecycle_log_text(
    *,
    roles: tuple[str, ...] = ("session_start", "session_start_rejected", "session_end"),
    timestamps: dict[str, str | None] | None = None,
    session_start_rejected_target: str = "ShooterGameMode.CheckJoinInProgress",
    session_start_rejected_copied_bool_values: str = "1,0",
) -> str:
    timestamps = DEFAULT_TIMESTAMPS if timestamps is None else timestamps
    lines = [
        prefixed(
            timestamps.get("enabled"),
            "[info] PlayerPrincipalLifecycleObserver enabled "
            f"binary_sha256={SHA} "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none.",
        )
    ]
    if "session_start" in roles:
        lines.append(
            prefixed(
                timestamps.get("session_start"),
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created "
                "correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            )
        )
    if "session_start_rejected" in roles:
        lines.append(
            prefixed(
                timestamps.get("session_start_rejected"),
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                f"target={session_start_rejected_target} post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue "
                f"copied_bool_values={session_start_rejected_copied_bool_values} "
                "redacted_count=1 redacted_fields=NewPlayer "
                "principal_action=none apply_status=session_start_rejected_noop "
                "correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            )
        )
    if "session_end" in roles:
        lines.append(
            prefixed(
                timestamps.get("session_end"),
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true "
                "copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated "
                "correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            )
        )
    return "\n".join(lines) + "\n"


def diagnostic_only_log_text() -> str:
    return "\n".join(
        [
            prefixed(
                DEFAULT_TIMESTAMPS["enabled"],
                "[info] PlayerPrincipalLifecycleObserver enabled "
                f"binary_sha256={SHA} "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
            ),
            prefixed(
                DEFAULT_TIMESTAMPS["session_start"],
                "[info] PlayerPrincipalLifecycleObserver diagnostic target=ShooterGameMode.HandleNewPlayer "
                "diagnostic_only=true player_presence_context=players_detected.",
            ),
            prefixed(
                DEFAULT_TIMESTAMPS["session_start_rejected"],
                "[info] PlayerPrincipalLifecycleObserver diagnostic target=GameMode.K2_PostLogin "
                "diagnostic_only=true player_presence_context=players_detected.",
            ),
        ]
    ) + "\n"


def ragnarok_duplicate_start_diagnostic_missing_check_join_log_text() -> str:
    lines = lifecycle_log_text(roles=("session_start", "session_end")).splitlines()
    duplicate_start = lines[1].replace("sequence=1", "sequence=2").replace(
        DEFAULT_TIMESTAMPS["session_start"],
        DEFAULT_TIMESTAMPS["session_start_rejected"],
    )
    diagnostic = (
        "[2026-06-06T13:56:25Z] [info] PlayerPrincipalLifecycleDiagnostic candidate "
        "sequence=4 target=ShooterGameMode.CheckJoinInProgress fname_index=2171 "
        "post_original=true accepted_lifecycle_target=true reflection_status=matched "
        "read_status=ok diagnostic_shape=CheckJoinInProgress copy_status=rejected "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
        "redacted_count=1 redacted_fields=NewPlayer params_logged=false "
        "identity_logged=false evidence_claim=none."
    )
    lines.insert(2, duplicate_start)
    lines.insert(3, diagnostic)
    return "\n".join(lines) + "\n"


def run_script(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(SAFE_OFFLINE_WORKSPACE)
    env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def preflight_false_values() -> dict[str, bool]:
    return {
        key: False
        for key in (
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
    }


def preflight_payload(
    *,
    mode: str,
    evidence: Path,
    checked_at_utc: str,
) -> dict:
    payload = {
        "schema": "obelisk.player-principal-lifecycle-preflight.v1",
        "ready": True,
        "mode": mode,
        "run_id": RUN_ID,
        "instance": "arkserver3",
        "map": "Genesis2",
        "target": {"instance": "arkserver3", "map": "Genesis2"},
        "window_manifest_path": str(evidence / "window-manifest.env"),
        "copied_log_path": str(evidence / "Obelisk.log"),
        "copied_evidence_dir": str(evidence),
        "server_binary": {
            "path": "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer",
            "sha256": SHA,
        },
        "posture_check": "accepted",
        "offline_only": False,
        "allow_stopped": False,
        "checked_at_utc": checked_at_utc,
        "non_claim": EXPECTED_PREFLIGHT_NON_CLAIM,
    }
    payload.update(preflight_false_values())
    return payload


def manifest_check_false_values() -> dict[str, bool]:
    return {
        key: False
        for key in (
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
    }


def manifest_check_machine_next_step() -> dict:
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-next-step.v1",
        "step": "build_and_check_approved_runtime_principal_lifecycle_evidence_bundle",
        "next_blocker": "approved_runtime_observer_log_summary_and_manifest_missing",
        "next_required_artifact": "approved_runtime_principal_lifecycle_evidence_bundle",
        "required_artifact_status": "missing_or_not_accepted",
        "authorized_by_this_report": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "discord_authorized": False,
        "marker_env_changes_authorized": False,
        "runtime_capture_authorized": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
    }


def manifest_check_payload() -> dict:
    payload = {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1",
        "ready": True,
        "operational_window_manifest_ready": True,
        "next_blocker": "approved_runtime_observer_log_summary_and_manifest_missing",
        "next_required_artifact": "approved_runtime_principal_lifecycle_evidence_bundle",
        "required_artifact_status": "missing_or_not_accepted",
        "machine_next_step": manifest_check_machine_next_step(),
        "claims": {"delivery_claim": "none", "principal_claim": "none"},
        "blockers": [],
        "non_claims": EXPECTED_WINDOW_MANIFEST_NON_CLAIMS,
    }
    payload.update(manifest_check_false_values())
    return payload


def write_ready_sidecars(evidence: Path) -> None:
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "window-request.json").write_text(
        json.dumps(
            {
                "schema": "obelisk.player-principal-lifecycle-window-request.v1",
                "run_id": RUN_ID,
                "target": {"instance": "arkserver3", "map": "Genesis2"},
                "approved_window": {
                    "start_utc": FRESH_WINDOW_START_UTC,
                    "end_utc": FRESH_WINDOW_END_UTC,
                },
                "approval_required": "standing launch authority for exact ObeliskSDK runtime window",
                "obelisk_commit": "b390591f760818c8927d8e762f5703d423a878ae",
                "user_policy": "operator_approved_beta_users",
                "copied_evidence_dir": str(evidence.resolve()),
                "copied_log_path": str((evidence / "Obelisk.log").resolve()),
                "window_manifest_path": str((evidence / "window-manifest.env").resolve()),
                "post_window_replay_contract": {
                    "sidecars": {
                        "request_pack_path": str((evidence / "window-request.json").resolve()),
                        "observer_env_path": str((evidence / "observer-window.env").resolve()),
                        "operator_approval_request_path": str(
                            (evidence / "operator-approval-request.md").resolve()
                        ),
                        "operator_approval_receipt_path": str(
                            (evidence / "operator-approval-receipt.json").resolve()
                        ),
                        "preflight_pre_path": str((evidence / "preflight-pre.json").resolve()),
                        "preflight_post_path": str((evidence / "preflight-post.json").resolve()),
                        "window_manifest_path": str((evidence / "window-manifest.env").resolve()),
                        "copied_log_path": str((evidence / "Obelisk.log").resolve()),
                    }
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence / "observer-window.env").write_text("OBELISK_WRAPPER_PROFILE=observer-debug\n", encoding="utf-8")
    (evidence / "operator-approval-request.md").write_text(
        "Operator approval request for exact player-principal lifecycle observer window.\n",
        encoding="utf-8",
    )
    (evidence / "operator-approval-receipt.json").write_text('{"receipt_completed": true}\n', encoding="utf-8")
    (evidence / "preflight-pre.json").write_text(
        json.dumps(
            preflight_payload(
                mode="observer-window",
                evidence=evidence,
                checked_at_utc="2026-06-06T13:55:30Z",
            ),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_fake_helpers(root: Path, evidence: Path) -> tuple[Path, Path]:
    preflight = root / "fake_preflight.py"
    preflight.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "payload = " + repr(
                    preflight_payload(
                        mode="stable",
                        evidence=evidence,
                        checked_at_utc="2026-06-06T14:00:00Z",
                    )
                ),
                "print(json.dumps(payload, sort_keys=True))",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    preflight.chmod(0o755)
    manifest = root / "fake_manifest.py"
    manifest.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "payload = " + repr(manifest_check_payload()),
                "print(json.dumps(payload, sort_keys=True))",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest.chmod(0o755)
    return preflight, manifest


def write_minimal_ready_manifest_helper(root: Path) -> Path:
    manifest = root / "minimal_manifest.py"
    manifest.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "print(json.dumps({",
                "  'schema': 'obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1',",
                "  'ready': True,",
                "  'operational_window_manifest_ready': True,",
                "  'blockers': [],",
                "}, sort_keys=True))",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest.chmod(0o755)
    return manifest


class CopyPlayerPrincipalLifecycleReadyLogTests(unittest.TestCase):
    def test_dry_run_ready_with_complete_triplet_does_not_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "live" / "Obelisk.log"
            evidence = root / "evidence"
            source.parent.mkdir()
            evidence.mkdir()
            source.write_text(lifecycle_log_text(), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertFalse((evidence / "Obelisk.log").exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["schema"], "obelisk.player-principal-lifecycle-ready-log-copy.v1")
        self.assertEqual(report["status"], "dry_run_ready")
        self.assertTrue(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "ready_complete_role_triplet")
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["missing_roles"], [])
        self.assertEqual(report["analysis"]["missing_roles_with_unapproved_shape"], [])
        self.assertEqual(
            report["analysis"]["accepted_role_events"]["session_start_rejected"]["target"],
            "ShooterGameMode.CheckJoinInProgress",
        )
        self.assertEqual(
            report["analysis"]["accepted_role_events"]["session_start_rejected"]["copied_bool_values"],
            "1,0",
        )
        next_actions = report["next_action_commands"]
        self.assertEqual(
            next_actions["schema"],
            "obelisk.player-principal-lifecycle-ready-log-copy-next-actions.v1",
        )
        self.assertFalse(next_actions["approved_runtime_evidence"])
        self.assertFalse(next_actions["counts_toward_sdk"])
        self.assertFalse(next_actions["server_operations_authorized_by_this_report"])
        self.assertTrue(next_actions["copy_ready_execute"]["available"])
        self.assertIn("--execute", next_actions["copy_ready_execute"]["command"])
        self.assertIn(
            "--allow-post-window-sidecar-generation",
            next_actions["copy_ready_execute"]["command"],
        )
        self.assertEqual(
            next_actions["copy_ready_execute"]["json_output"],
            str(evidence / "ready-log-copy.json"),
        )
        self.assertTrue(next_actions["bundle_preflight"]["available"])
        self.assertIn("--preflight-only", next_actions["bundle_preflight"]["command"])
        self.assertFalse(next_actions["build_approved_bundle"]["available"])
        self.assertIn(
            "post_window_sidecars_not_ready",
            next_actions["build_approved_bundle"]["blockers"],
        )

    def test_non_evidence_json_report_source_blocks_copy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sdk-status.json"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.sdk-status-report.v1",
                        "status": "blocked",
                        "approved_runtime_evidence": False,
                        "current_route_blocker": "approved_runtime_evidence_missing",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_before_source_analysis")
        self.assertEqual(report["source_input"]["classification"], "non_evidence_json_report")
        self.assertEqual(report["source_input"]["schema"], "obelisk.sdk-status-report.v1")
        self.assertIn("source_log_is_sdk_status_report_not_obelisk_log", report["blockers"])
        self.assertIn("source_log_is_not_copied_obelisk_log_text", report["blockers"])
        self.assertFalse(report["source_input"]["source_input_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["copied_artifacts_count_as_approved_runtime_evidence_until_checker_accepts"])

    def test_watcher_monitor_json_context_blocks_copy_and_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "watcher-context.json"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-lifecycle-watcher-context.v1",
                        "status": "players_detected",
                        "players_current": 2,
                        "approved_runtime_evidence": True,
                        "counts_toward_sdk": True,
                        "counts_toward_p0_dependency_chain": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertFalse(report["copied"])
        self.assertEqual(report["source_input"]["classification"], "non_evidence_json_report")
        self.assertEqual(
            report["source_input"]["schema"],
            "obelisk.player-principal-lifecycle-watcher-context.v1",
        )
        self.assertIn("source_log_is_watcher_monitor_context_not_obelisk_log", report["blockers"])
        self.assertIn("source_log_is_not_copied_obelisk_log_text", report["blockers"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["counts_as_sdk_evidence"])
        self.assertFalse(report["counts_toward_sdk"])
        self.assertFalse(report["counts_toward_p0_dependency_chain"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_json_output_under_protected_server_root_is_reported_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text(), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json-output",
                "/servidor/ark/obelisk/logs/ready-log-copy.json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["json_output"]["accepted"])
        self.assertTrue(
            any(blocker.startswith("json_output_under_protected_server_root:") for blocker in report["blockers"])
        )
        self.assertFalse(report["ready_to_copy"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_passive_context_metadata_blocks_copy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                "\n".join(
                    [
                        "rcon_listplayers instance=arkserver3 map=Genesis2 query_port=27017 "
                        "rcon_port=27022 status=ok players_current=1 target_key=arkserver3:Genesis2:27017 "
                        "presence_detected=true detection_source=rcon_listplayers_redacted "
                        "rcon_output_redacted=true",
                        "runtime_window_plan status=planned approved_runtime_evidence=false",
                        "player_notice_action status=prepared "
                        "player_notice_counts_as_approved_runtime_evidence=false",
                        lifecycle_log_text().rstrip(),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "ready_complete_role_triplet")
        self.assertIn("source_log_contains_passive_context_metadata", report["blockers"])
        self.assertEqual(report["source_log_safety"]["passive_context_line_count"], 3)
        self.assertEqual(report["source_log_safety"]["unsafe_player_text_line_count"], 0)
        self.assertFalse(report["source_log_safety"]["passive_context_counts_as_approved_runtime_evidence"])

    def test_timestamp_prefixed_passive_context_metadata_blocks_copy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                "\n".join(
                    [
                        "[2026-06-06T13:55:30Z] tick utc=2026-06-06T13:55:30Z",
                        "[2026-06-06T13:55:31Z] query instance=arkserver3 map=Genesis2 "
                        "query_port=27017 status=ok players=1/70",
                        "[2026-06-06T13:55:32Z] player_presence_detected "
                        "instance=arkserver3 map=Genesis2",
                        lifecycle_log_text().rstrip(),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "ready_complete_role_triplet")
        self.assertIn("source_log_contains_passive_context_metadata", report["blockers"])
        self.assertEqual(report["source_log_safety"]["passive_context_line_count"], 3)
        self.assertFalse(report["source_log_safety"]["passive_context_counts_as_approved_runtime_evidence"])

    def test_lifecycle_diagnostic_check_join_line_blocks_copy_readiness(self) -> None:
        diagnostic = (
            "[2026-06-06T13:56:30Z] [info] PlayerPrincipalLifecycleDiagnostic candidate "
            "sequence=4 target=ShooterGameMode.CheckJoinInProgress fname_index=2171 "
            "post_original=true accepted_lifecycle_target=true reflection_status=matched "
            "read_status=ok diagnostic_shape=CheckJoinInProgress copy_status=rejected "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
            "redacted_count=1 redacted_fields=NewPlayer params_logged=false "
            "identity_logged=false evidence_claim=none."
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text() + diagnostic + "\n", encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "ready_complete_role_triplet")
        self.assertIn("source_log_contains_lifecycle_diagnostic_lines", report["blockers"])
        self.assertEqual(report["source_log_safety"]["lifecycle_diagnostic_line_count"], 1)
        self.assertFalse(
            report["source_log_safety"][
                "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence"
            ]
        )

    def test_handle_new_player_rejected_start_line_blocks_copy_readiness(self) -> None:
        rejected_start = (
            "[2026-06-06T13:56:30Z] [info] PlayerPrincipalLifecycleObserver event "
            "sequence=4 role=session_start_rejected target=ShooterGameMode.HandleNewPlayer "
            "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
            "copied_bool_values=0,1 redacted_count=3 "
            "redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=none "
            "apply_status=session_start_rejected_noop correlation_status=not_applicable "
            "principal_id_logged=false principal_generation_logged=false delivery_claim=none."
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text() + rejected_start + "\n", encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_diagnostic_or_rejected_lifecycle_lines")
        self.assertIn("blocked_diagnostic_or_rejected_lifecycle_lines", report["blockers"])
        self.assertEqual(report["roles_present"], ["session_start", "session_start_rejected", "session_end"])
        rejected_events = report["analysis"]["rejected_or_incomplete_role_events"]
        self.assertTrue(
            any(
                event["role"] == "session_start_rejected"
                and event["target"] == "ShooterGameMode.HandleNewPlayer"
                for event in rejected_events
            )
        )

    def test_unexpected_observer_module_blocks_copy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                lifecycle_log_text()
                + "[2026-06-06T13:56:30Z] [info] Reflected chat ProcessEvent #1 "
                "function=ServerSendChatMessage fname_index=99 fields=0\n",
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertIn("source_log_contains_unexpected_observer_modules", report["blockers"])
        self.assertEqual(report["source_log_safety"]["unexpected_observer_modules"], ["chat"])

    def test_duplicate_start_end_context_inside_fresh_window_blocks_ready_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            lines = lifecycle_log_text().splitlines()
            duplicate_start = lines[1].replace("sequence=1", "sequence=2").replace(
                DEFAULT_TIMESTAMPS["session_start"],
                "2026-06-06T13:56:15Z",
            )
            lines[2] = lines[2].replace("sequence=2", "sequence=3")
            lines[3] = lines[3].replace("sequence=3", "sequence=4")
            duplicate_end = lines[3].replace("sequence=4", "sequence=5").replace(
                DEFAULT_TIMESTAMPS["session_end"],
                "2026-06-06T13:56:40Z",
            )
            lines.insert(2, duplicate_start)
            lines.append(duplicate_end)
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_lifecycle_triplet_order_mismatch")
        self.assertEqual(report["roles_present"], ["session_start", "session_start_rejected", "session_end"])
        self.assertEqual(report["missing_roles"], [])
        self.assertEqual(report["analysis"]["duplicate_accepted_role_event_count"], 2)
        self.assertEqual(report["analysis"]["duplicate_accepted_roles"], ["session_start", "session_end"])
        self.assertEqual(
            report["analysis"]["exact_copied_runtime_triplet"]["status"],
            "selected_with_duplicate_start_end_context",
        )
        self.assertEqual(
            report["analysis"]["exact_copied_runtime_triplet"]["blockers"],
            [
                "exact_copied_runtime_triplet_selection_status_not_exact",
                "exact_copied_runtime_triplet_candidate_count_not_one",
                "exact_copied_runtime_triplet_non_counting_context_present",
                "exact_copied_runtime_triplet_not_selected",
            ],
        )
        self.assertEqual(
            report["blockers"],
            [
                "blocked_lifecycle_triplet_order_mismatch",
                "exact_copied_runtime_triplet_selection_status_not_exact",
                "exact_copied_runtime_triplet_candidate_count_not_one",
                "exact_copied_runtime_triplet_non_counting_context_present",
                "exact_copied_runtime_triplet_not_selected",
            ],
        )
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_ragnarok_duplicate_start_diagnostic_missing_check_join_shape_blocks_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                ragnarok_duplicate_start_diagnostic_missing_check_join_log_text(),
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertFalse(report["copied"])
        self.assertEqual(report["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertEqual(report["roles_present"], ["session_start", "session_end"])
        self.assertEqual(report["missing_roles"], ["session_start_rejected"])
        self.assertIn("source_log_contains_lifecycle_diagnostic_lines", report["blockers"])
        self.assertIn("blocked_missing_lifecycle_roles", report["blockers"])
        self.assertIn("exact_copied_runtime_triplet_missing_session_start_rejected", report["blockers"])
        self.assertNotIn("exact_copied_runtime_triplet_missing_session_start", report["blockers"])
        self.assertNotIn("exact_copied_runtime_triplet_missing_session_end", report["blockers"])
        self.assertEqual(report["analysis"]["duplicate_accepted_roles"], ["session_start"])
        self.assertEqual(report["source_log_safety"]["lifecycle_diagnostic_line_count"], 1)
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(
            report["source_log_safety"][
                "diagnostic_or_unexpected_observer_lines_count_as_approved_runtime_evidence"
            ]
        )

    def test_theisland_observer_enable_only_post_window_reports_no_role_closure_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text(roles=()), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver2",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--now-utc",
                "2026-06-06T14:20:00Z",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertFalse(report["copied"])
        self.assertEqual(report["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertEqual(report["roles_present"], [])
        self.assertEqual(
            report["missing_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertTrue(report["observer_only_no_role_window_detected"])
        self.assertFalse(report["active_observer_only_no_role_window"])
        self.assertTrue(report["post_window_observer_only_no_role_window"])
        self.assertEqual(report["observer_only_no_role_window_state"], "post_window")
        self.assertEqual(
            report["source_log_not_ready_classification"],
            "observer_enabled_no_lifecycle_roles_post_window",
        )
        self.assertEqual(
            report["post_window_closure_action"],
            "close_observer_only_no_role_window_as_non_evidence",
        )
        no_role = report["source_log_not_ready"]
        self.assertEqual(
            no_role["classification"],
            "observer_enabled_no_lifecycle_roles_post_window",
        )
        self.assertTrue(no_role["observer_only_no_role_window_detected"])
        self.assertFalse(no_role["active_observer_only_no_role_window"])
        self.assertTrue(no_role["post_window_observer_only_no_role_window"])
        self.assertEqual(no_role["window_state"], "post_window")
        self.assertEqual(no_role["target_hint"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertEqual(
            no_role["post_window_closure_action"],
            "close_observer_only_no_role_window_as_non_evidence",
        )
        self.assertTrue(no_role["copied_log_available_for_closure"])
        self.assertTrue(no_role["copied_log_available_for_non_evidence_closure"])
        self.assertFalse(no_role["copied_log_available_for_evidence_closure"])
        self.assertTrue(no_role["expired_no_evidence"])
        self.assertFalse(no_role["accepted_ready"])
        self.assertFalse(no_role["accepted_ready_for_evidence_closure"])
        self.assertIn(
            "treat the observer-enable-only window as closed non-evidence",
            no_role["manual_offline_next_steps"],
        )
        self.assertFalse(no_role["ready_to_copy"])
        self.assertFalse(no_role["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_player_presence_with_observer_enable_only_adds_non_evidence_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                "\n".join(
                    [
                        "[2026-06-06T13:55:50Z] player_presence_detected "
                        "instance=arkserver2 map=TheIsland players_current=1 "
                        "presence_detected=true target_key=arkserver2:TheIsland:27016",
                        lifecycle_log_text(roles=()).rstrip(),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver2",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--now-utc",
                "2026-06-06T14:20:00Z",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertIn("blocked_missing_lifecycle_roles", report["blockers"])
        self.assertIn("player_present_but_no_lifecycle_roles", report["blockers"])
        self.assertIn("source_log_contains_passive_context_metadata", report["blockers"])
        no_role = report["source_log_not_ready"]
        self.assertTrue(no_role["observer_only_no_role_window_detected"])
        self.assertTrue(no_role["player_present_but_no_lifecycle_roles"])
        self.assertIn("player_present_but_no_lifecycle_roles", no_role["blockers"])
        presence = no_role["player_presence_context"]
        self.assertEqual(presence["classification"], "players_detected_operator_context_non_evidence")
        self.assertTrue(presence["players_detected"])
        self.assertEqual(presence["targets"], ["arkserver2:TheIsland:27016"])
        self.assertFalse(presence["player_presence_context_counts_as_approved_runtime_evidence"])
        self.assertFalse(no_role["player_presence_context_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertIn(
            "player_present_but_no_lifecycle_roles",
            report["next_action_commands"]["copy_ready_execute"]["blockers"],
        )

    def test_theisland_observer_enable_only_active_window_does_not_report_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text(roles=()), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver2",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--now-utc",
                "2026-06-06T14:00:00Z",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertTrue(report["active_observer_only_no_role_window"])
        self.assertEqual(report["observer_only_no_role_window_state"], "in_progress")
        self.assertEqual(
            report["source_log_not_ready_classification"],
            "observer_enabled_no_lifecycle_roles_window_in_progress",
        )
        self.assertIsNone(report["post_window_closure_action"])
        self.assertNotIn(
            "close_observer_only_no_role_window_as_non_evidence",
            json.dumps(report, sort_keys=True),
        )
        no_role = report["source_log_not_ready"]
        self.assertEqual(
            no_role["classification"],
            "observer_enabled_no_lifecycle_roles_window_in_progress",
        )
        self.assertTrue(no_role["observer_only_no_role_window_detected"])
        self.assertTrue(no_role["active_observer_only_no_role_window"])
        self.assertFalse(no_role["post_window_observer_only_no_role_window"])
        self.assertEqual(no_role["window_state"], "in_progress")
        self.assertIsNone(no_role["post_window_closure_action"])
        self.assertFalse(no_role["copied_log_available_for_closure"])
        self.assertIn(
            "keep the observer-enable-only window open until fresh_window_end_utc",
            no_role["manual_offline_next_steps"],
        )
        self.assertIn(
            "rerun the dry-run against the fresh source log if lifecycle events arrive before the window ends",
            no_role["manual_offline_next_steps"],
        )
        self.assertNotIn(
            "treat the observer-enable-only window as closed non-evidence",
            no_role["manual_offline_next_steps"],
        )
        self.assertFalse(no_role["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_unordered_triplet_blocks_copy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            lines = lifecycle_log_text().splitlines()
            lines[2], lines[3] = lines[3], lines[2]
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_lifecycle_triplet_order_mismatch")
        self.assertEqual(report["roles_present"], ["session_start", "session_start_rejected", "session_end"])
        self.assertEqual(report["missing_roles"], [])
        order = report["analysis"]["lifecycle_triplet_order"]
        self.assertEqual(order["status"], "mismatch")
        self.assertEqual(
            order["observed_roles_by_line"],
            ["session_start", "session_end", "session_start_rejected"],
        )
        self.assertIn("accepted_lifecycle_role_line_order_mismatch", order["blockers"])
        self.assertIn("blocked_lifecycle_triplet_order_mismatch", report["blockers"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_historical_accepted_events_block_copy_readiness_even_with_fresh_triplet(self) -> None:
        historical_timestamps = {
            **DEFAULT_TIMESTAMPS,
            "enabled": "2026-06-06T13:40:00Z",
            "session_start": "2026-06-06T13:40:01Z",
            "session_start_rejected": "2026-06-06T13:40:02Z",
            "session_end": "2026-06-06T13:40:03Z",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                lifecycle_log_text(timestamps=historical_timestamps) + lifecycle_log_text(),
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_lifecycle_events_outside_fresh_window")
        self.assertEqual(report["roles_present"], ["session_start", "session_start_rejected", "session_end"])
        self.assertEqual(report["missing_roles"], [])
        self.assertEqual(report["analysis"]["historical_accepted_role_event_count"], 3)
        self.assertEqual(
            report["analysis"]["historical_roles_present"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertIn("blocked_lifecycle_events_outside_fresh_window", report["blockers"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_fresh_window_is_required_before_copy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text(), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_missing_fresh_window")
        self.assertIn("fresh_window_start_utc_required", report["blockers"])
        self.assertIn("fresh_window_end_utc_required", report["blockers"])

    def test_diagnostic_only_target_lines_do_not_satisfy_copy_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(diagnostic_only_log_text(), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertEqual(report["roles_present"], [])
        self.assertEqual(report["missing_roles"], ["session_start", "session_start_rejected", "session_end"])
        self.assertEqual(report["analysis"]["accepted_role_events"], {})
        self.assertEqual(report["analysis"]["rejected_or_incomplete_role_event_count"], 0)
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_execute_requires_explicit_evidence_write_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text(), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertIn("evidence_dir_write_requires_explicit_flag", report["blockers"])

    def test_execute_blocks_without_post_window_sidecar_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            text = lifecycle_log_text()
            source.write_text(text, encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertFalse((evidence / "Obelisk.log").exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertFalse(report["copied"])
        self.assertIn("post_window_sidecar_generation_requires_explicit_flag", report["blockers"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_execute_blocks_json_output_not_bound_to_evidence_report_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obelisk-test-copy-ready-", dir=SAFE_OFFLINE_WORKSPACE) as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "live-validation-logs" / RUN_ID
            source.write_text(lifecycle_log_text(), encoding="utf-8")
            unbound_report = root / "ready-log-copy.json"

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--allow-post-window-sidecar-generation",
                "--json-output",
                str(unbound_report),
            )
            report = json.loads(result.stdout)

            self.assertFalse((evidence / "Obelisk.log").exists())
            self.assertFalse(unbound_report.exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertFalse(report["copied"])
        self.assertFalse(report["json_output"]["accepted"])
        self.assertEqual(
            report["json_output"]["expected_execute_report_path"],
            str((evidence / "ready-log-copy.json").resolve()),
        )
        self.assertTrue(
            any(
                blocker.startswith("json_output_not_bound_to_evidence_dir_ready_log_copy_report:")
                for blocker in report["blockers"]
            )
        )
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_execute_copies_and_generates_post_window_sidecars(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obelisk-test-copy-ready-", dir=SAFE_OFFLINE_WORKSPACE) as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "live-validation-logs" / RUN_ID
            text = lifecycle_log_text()
            source.write_text(text, encoding="utf-8")
            write_ready_sidecars(evidence)
            preflight, manifest = write_fake_helpers(root, evidence)

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--allow-post-window-sidecar-generation",
                "--allow-post-window-preflight-live-read",
                "--preflight-helper",
                str(preflight),
                "--window-manifest-helper",
                str(manifest),
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertEqual((evidence / "Obelisk.log").read_text(encoding="utf-8"), text)
            self.assertTrue((evidence / "preflight-post.json").is_file())
            self.assertTrue((evidence / "window-manifest.env").is_file())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "copied")
        self.assertTrue(report["copied"])
        self.assertTrue(report["post_window_sidecars_ready"])
        self.assertTrue(report["sidecar_precheck"]["accepted"])
        self.assertTrue(report["post_window_sidecars"]["window_manifest"]["written"])
        self.assertTrue(report["post_window_sidecars"]["window_manifest_check"]["ready"])
        self.assertTrue(report["post_window_sidecars"]["exact_copied_runtime_triplet"]["accepted"])
        self.assertEqual(
            report["post_window_sidecars"]["window_manifest_check"]["report_next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertFalse(
            report["post_window_sidecars"]["window_manifest_check"]["report_false_flags"]["runtime_ready"]
        )
        self.assertFalse(
            report["post_window_sidecars"]["window_manifest_check"]["machine_next_step_false_flags"][
                "approved_runtime_evidence"
            ]
        )
        self.assertIsNotNone(report["target_copied_sha256"])
        bindings = report["artifact_hash_path_bindings"]
        self.assertTrue(bindings["copied_log_hash_path_bound"])
        self.assertTrue(bindings["bundle_input_artifacts_hash_path_bound"])
        self.assertFalse(bindings["complete_sibling_set_hash_path_bound"])
        self.assertEqual(
            bindings["copied_log"]["sha256"],
            report["target_copied_sha256"],
        )
        self.assertEqual(
            bindings["copied_log"]["resolved_path"],
            str((evidence / "Obelisk.log").resolve()),
        )
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            bindings["missing_hash_path_bindings"],
        )
        self.assertFalse(report["artifact_hash_path_bindings_count_as_approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["post_window_sidecars"]["approved_runtime_evidence"])
        self.assertFalse(report["post_window_sidecars"]["post_window_sidecars_count_as_approved_runtime_evidence"])
        next_actions = report["next_action_commands"]
        self.assertFalse(next_actions["approved_runtime_evidence_ready"])
        self.assertFalse(next_actions["counts_toward_p0_dependency_chain"])
        self.assertFalse(next_actions["discord_sent_by_this_report"])
        self.assertFalse(next_actions["copy_ready_execute"]["available"])
        self.assertTrue(next_actions["bundle_preflight"]["available"])
        self.assertTrue(next_actions["build_approved_bundle"]["available"])
        self.assertEqual(next_actions["build_approved_bundle"]["blockers"], [])
        self.assertTrue(next_actions["build_approved_bundle"]["command_metadata_resolved"])
        self.assertIsNotNone(next_actions["build_approved_bundle"]["command"])
        self.assertIn(
            str(evidence / "approved-bundle"),
            next_actions["build_approved_bundle"]["command_template"],
        )
        self.assertNotIn(
            "<window-manifest-obelisk_commit>",
            next_actions["build_approved_bundle"]["command_template"],
        )
        self.assertIn(
            "b390591f760818c8927d8e762f5703d423a878ae",
            next_actions["build_approved_bundle"]["command_template"],
        )
        self.assertTrue(next_actions["check_approved_bundle"]["available"])
        self.assertEqual(
            next_actions["check_approved_bundle"]["manifest"],
            str(
                evidence
                / "approved-bundle"
                / "approved-runtime-principal-lifecycle-evidence.json"
            ),
        )
        pipeline = next_actions["evidence_pipeline_command_sequence"]
        self.assertEqual(
            pipeline["ordered_step_ids"],
            [
                "analyze_runtime_observer_log",
                "strict_lifecycle_triplet_selector",
                "bundle_preflight",
                "approved_runtime_evidence_checker",
            ],
        )
        commands = {item["id"]: item["command_text_not_executed"] for item in pipeline["commands"]}
        self.assertIn("scripts/analyze_runtime_observer_log.py", commands["analyze_runtime_observer_log"])
        self.assertNotIn("<window-manifest-obelisk_commit>", commands["analyze_runtime_observer_log"])
        self.assertIn("b390591f760818c8927d8e762f5703d423a878ae", commands["analyze_runtime_observer_log"])
        self.assertIn(
            "scripts/build_player_identity_runtime_principal_lifecycle_approved_manifest.py",
            commands["strict_lifecycle_triplet_selector"],
        )
        self.assertNotIn("<reviewer>", commands["strict_lifecycle_triplet_selector"])
        self.assertNotIn("<consume-only-review-note>", commands["strict_lifecycle_triplet_selector"])
        self.assertIn("--preflight-only", commands["bundle_preflight"])
        self.assertTrue(pipeline["direct_bundle_builder_command_available"])
        self.assertIsNotNone(pipeline["direct_bundle_builder_command"])
        self.assertFalse(
            pipeline["bundle_command_metadata"]["metadata_counts_as_approved_runtime_evidence"]
        )
        self.assertIn(
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            commands["approved_runtime_evidence_checker"],
        )
        self.assertFalse(pipeline["restart_recommended"])
        self.assertFalse(pipeline["raw_player_text_or_identity_allowed"])
        self.assertFalse(pipeline["authorization"]["server_operations_authorized_by_this_report"])
        self.assertFalse(pipeline["evidence"]["counts_as_approved_runtime_evidence"])

    def test_execute_blocks_when_window_request_copied_log_path_mismatches_evidence_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obelisk-test-copy-ready-", dir=SAFE_OFFLINE_WORKSPACE) as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "live-validation-logs" / RUN_ID
            source.write_text(lifecycle_log_text(), encoding="utf-8")
            write_ready_sidecars(evidence)
            payload = json.loads((evidence / "window-request.json").read_text(encoding="utf-8"))
            payload["copied_log_path"] = str((root / "other-run" / "Obelisk.log").resolve())
            (evidence / "window-request.json").write_text(
                json.dumps(payload, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            preflight, manifest = write_fake_helpers(root, evidence)

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--allow-post-window-sidecar-generation",
                "--allow-post-window-preflight-live-read",
                "--preflight-helper",
                str(preflight),
                "--window-manifest-helper",
                str(manifest),
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertFalse((evidence / "Obelisk.log").exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertFalse(report["copied"])
        self.assertFalse(report["sidecar_precheck"]["accepted"])
        self.assertIn("window_request_copied_log_path_mismatch", report["blockers"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_execute_blocks_when_preflight_pre_binary_path_mismatches_expected_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obelisk-test-copy-ready-", dir=SAFE_OFFLINE_WORKSPACE) as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "live-validation-logs" / RUN_ID
            source.write_text(lifecycle_log_text(), encoding="utf-8")
            write_ready_sidecars(evidence)
            payload = json.loads((evidence / "preflight-pre.json").read_text(encoding="utf-8"))
            payload["server_binary"]["path"] = "/tmp/not-the-live-server-binary"
            (evidence / "preflight-pre.json").write_text(
                json.dumps(payload, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            preflight, manifest = write_fake_helpers(root, evidence)

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--allow-post-window-sidecar-generation",
                "--allow-post-window-preflight-live-read",
                "--preflight-helper",
                str(preflight),
                "--window-manifest-helper",
                str(manifest),
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertFalse((evidence / "Obelisk.log").exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertFalse(report["copied"])
        self.assertFalse(report["sidecar_precheck"]["accepted"])
        self.assertIn("preflight_pre_binary_path_mismatch", report["blockers"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_execute_blocks_sidecar_ready_when_manifest_checker_omits_non_claim_flags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obelisk-test-copy-ready-", dir=SAFE_OFFLINE_WORKSPACE) as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "live-validation-logs" / RUN_ID
            text = lifecycle_log_text()
            source.write_text(text, encoding="utf-8")
            write_ready_sidecars(evidence)
            preflight, _manifest = write_fake_helpers(root, evidence)
            manifest = write_minimal_ready_manifest_helper(root)

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--allow-post-window-sidecar-generation",
                "--allow-post-window-preflight-live-read",
                "--preflight-helper",
                str(preflight),
                "--window-manifest-helper",
                str(manifest),
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertEqual((evidence / "Obelisk.log").read_text(encoding="utf-8"), text)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "copied_sidecars_blocked")
        self.assertTrue(report["copied"])
        self.assertFalse(report["post_window_sidecars_ready"])
        self.assertFalse(report["post_window_sidecars"]["window_manifest_check"]["ready"])
        self.assertIn("window_manifest_check_runtime_ready_not_false", report["blockers"])
        self.assertIn(
            "window_manifest_check_next_required_artifact_not_evidence_bundle",
            report["blockers"],
        )
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["post_window_sidecars"]["checker_ready_counts_as_approved_runtime_evidence"])

    def test_execute_blocks_when_preflight_pre_sidecar_is_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obelisk-test-copy-ready-", dir=SAFE_OFFLINE_WORKSPACE) as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "live-validation-logs" / RUN_ID
            source.write_text(lifecycle_log_text(), encoding="utf-8")
            write_ready_sidecars(evidence)
            (evidence / "preflight-pre.json").unlink()
            preflight, manifest = write_fake_helpers(root, evidence)

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--allow-post-window-sidecar-generation",
                "--allow-post-window-preflight-live-read",
                "--preflight-helper",
                str(preflight),
                "--window-manifest-helper",
                str(manifest),
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertFalse((evidence / "Obelisk.log").exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertFalse(report["copied"])
        self.assertIn("preflight_pre_missing", "\n".join(report["blockers"]))
        self.assertTrue(report["analysis"]["exact_copied_runtime_triplet"]["accepted"])
        next_actions = report["next_action_commands"]
        self.assertFalse(next_actions["copy_ready_execute"]["available"])
        self.assertTrue(next_actions["bundle_preflight"]["available"])
        self.assertIn("--preflight-only", next_actions["bundle_preflight"]["command"])
        self.assertFalse(next_actions["build_approved_bundle"]["available"])
        self.assertFalse(next_actions["check_approved_bundle"]["available"])
        self.assertEqual(
            next_actions["build_approved_bundle"]["blockers"],
            next_actions["check_approved_bundle"]["blockers"],
        )
        self.assertIn("copied_log_not_written", next_actions["build_approved_bundle"]["blockers"])
        self.assertIn("post_window_sidecars_not_ready", next_actions["build_approved_bundle"]["blockers"])
        self.assertTrue(
            any(
                blocker.startswith("preflight_pre_missing:")
                for blocker in next_actions["build_approved_bundle"]["blockers"]
            )
        )

    def test_execute_blocks_when_preflight_pre_non_claim_is_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obelisk-test-copy-ready-", dir=SAFE_OFFLINE_WORKSPACE) as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "live-validation-logs" / RUN_ID
            source.write_text(lifecycle_log_text(), encoding="utf-8")
            write_ready_sidecars(evidence)
            payload = json.loads((evidence / "preflight-pre.json").read_text(encoding="utf-8"))
            payload.pop("non_claim")
            (evidence / "preflight-pre.json").write_text(
                json.dumps(payload, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            preflight, manifest = write_fake_helpers(root, evidence)

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--allow-post-window-sidecar-generation",
                "--allow-post-window-preflight-live-read",
                "--preflight-helper",
                str(preflight),
                "--window-manifest-helper",
                str(manifest),
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertFalse((evidence / "Obelisk.log").exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertFalse(report["copied"])
        self.assertFalse(report["sidecar_precheck"]["accepted"])
        self.assertIn("preflight_pre_non_claim_mismatch", report["blockers"])

    def test_partial_roles_block_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text(roles=("session_start",)), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["copy_readiness"], "blocked_missing_lifecycle_roles")
        self.assertEqual(
            report["missing_roles"],
            ["session_start_rejected", "session_end"],
        )
        self.assertTrue(report["analysis"]["partial_accepted_lifecycle_role_set"])
        self.assertFalse(report["analysis"]["partial_accepted_lifecycle_roles_count_as_ready_to_copy"])
        self.assertFalse(report["analysis"]["partial_accepted_lifecycle_roles_count_as_approved_runtime_evidence"])
        self.assertFalse(report["analysis"]["diagnostic_or_rejected_lifecycle_lines_count_as_ready_to_copy"])
        self.assertFalse(report["analysis"]["diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence"])
        self.assertFalse(report["analysis"]["diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress"])
        self.assertIn("blocked_missing_lifecycle_roles", report["blockers"])

    def test_start_end_only_material_flags_missing_exact_triplet_and_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                lifecycle_log_text(roles=("session_start", "session_end")),
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_missing_lifecycle_roles")
        exact_triplet = report["analysis"]["exact_copied_runtime_triplet"]
        self.assertFalse(exact_triplet["accepted"])
        self.assertTrue(exact_triplet["start_end_only_detected"])
        self.assertEqual(exact_triplet["accepted_roles"], ["session_start", "session_end"])
        self.assertEqual(exact_triplet["missing_roles"], ["session_start_rejected"])
        self.assertIn(
            "exact_copied_runtime_triplet_missing_session_start_rejected",
            exact_triplet["blockers"],
        )
        self.assertNotIn(
            "exact_copied_runtime_triplet_missing_session_start",
            exact_triplet["blockers"],
        )
        self.assertNotIn(
            "exact_copied_runtime_triplet_missing_session_end",
            exact_triplet["blockers"],
        )
        self.assertIn(
            "exact_copied_runtime_triplet_missing_session_start_rejected",
            report["blockers"],
        )
        self.assertNotIn(
            "exact_copied_runtime_triplet_missing_session_start",
            report["blockers"],
        )
        self.assertNotIn(
            "exact_copied_runtime_triplet_missing_session_end",
            report["blockers"],
        )
        self.assertEqual(
            exact_triplet["required_rejected_start_shape"]["target"],
            "ShooterGameMode.CheckJoinInProgress",
        )
        self.assertEqual(exact_triplet["required_rejected_start_shape"]["copied_bool_values"], "1,0")
        split = report["ready_log_evidence_split"]
        self.assertEqual(
            split["schema"],
            "obelisk.player-principal-lifecycle-ready-log-copy-evidence-split.v1",
        )
        self.assertEqual(
            split["classification"],
            "start_end_only_missing_exact_check_join_in_progress_1_0",
        )
        self.assertEqual(split["accepted_observer_event_roles"], ["session_start", "session_end"])
        self.assertEqual(split["missing_exact_roles"], ["session_start_rejected"])
        self.assertTrue(split["missing_exact_check_join_in_progress_1_0"])
        self.assertEqual(split["next_required_role"], "session_start_rejected")
        self.assertEqual(
            split["next_required_observer_event"]["target"],
            "ShooterGameMode.CheckJoinInProgress",
        )
        self.assertEqual(split["next_required_observer_event"]["copied_bool_values"], "1,0")
        self.assertFalse(split["copy_ready_split_counts_as_approved_runtime_evidence"])
        self.assertFalse(split["partial_roles_count_as_sdk_or_p0_progress"])
        self.assertFalse(report["start_end_only_counts_as_approved_runtime_evidence"])
        self.assertFalse(exact_triplet["start_end_only_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["copied_log_only_counts_as_approved_runtime_evidence"])

    def test_handle_new_player_rejected_bool_tuple_aliases_do_not_satisfy_rejected_role(self) -> None:
        for copied_bool_values in ("0,1", "1,0", "0,0"):
            with self.subTest(copied_bool_values=copied_bool_values):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    source = root / "Obelisk.log"
                    evidence = root / "evidence"
                    evidence.mkdir()
                    source.write_text(
                        lifecycle_log_text(
                            session_start_rejected_target="ShooterGameMode.HandleNewPlayer",
                            session_start_rejected_copied_bool_values=copied_bool_values,
                        ),
                        encoding="utf-8",
                    )

                    result = run_script(
                        "--instance",
                        "arkserver3",
                        "--source-log",
                        str(source),
                        "--evidence-dir",
                        str(evidence),
                        *fresh_window_args(),
                        "--json",
                    )
                    report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(report["status"], "blocked")
                self.assertFalse(report["ready_to_copy"])
                self.assertEqual(report["copy_readiness"], "blocked_diagnostic_or_rejected_lifecycle_lines")
                self.assertIn("blocked_diagnostic_or_rejected_lifecycle_lines", report["blockers"])
                self.assertEqual(report["roles_present"], ["session_start", "session_end"])
                self.assertEqual(report["missing_roles"], ["session_start_rejected"])
                self.assertEqual(
                    report["analysis"]["missing_roles_with_unapproved_shape"],
                    ["session_start_rejected"],
                )
                rejected_events = report["analysis"]["rejected_or_incomplete_role_events"]
                rejected_start = next(
                    event for event in rejected_events if event["role"] == "session_start_rejected"
                )
                self.assertEqual(rejected_start["target"], "ShooterGameMode.HandleNewPlayer")
                self.assertIn("target", rejected_start["approved_copy_shape_mismatches"])
                split = report["ready_log_evidence_split"]
                self.assertEqual(split["classification"], "observer_events_seen_but_shape_unapproved")
                self.assertTrue(split["missing_exact_check_join_in_progress_1_0"])
                self.assertEqual(split["check_join_in_progress_candidate_count"], 0)
                self.assertEqual(split["unapproved_shape_roles"], ["session_start_rejected"])
                self.assertFalse(split["diagnostic_or_rejected_material_counts_as_approved_runtime_evidence"])

    def test_check_join_in_progress_rejected_start_requires_approved_bool_tuple(self) -> None:
        for copied_bool_values in ("1,1", "0,1", "0,0"):
            with self.subTest(copied_bool_values=copied_bool_values):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    source = root / "Obelisk.log"
                    evidence = root / "evidence"
                    evidence.mkdir()
                    source.write_text(
                        lifecycle_log_text(
                            session_start_rejected_copied_bool_values=copied_bool_values,
                        ),
                        encoding="utf-8",
                    )

                    result = run_script(
                        "--instance",
                        "arkserver3",
                        "--source-log",
                        str(source),
                        "--evidence-dir",
                        str(evidence),
                        *fresh_window_args(),
                        "--json",
                    )
                    report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(report["status"], "blocked")
                self.assertFalse(report["ready_to_copy"])
                self.assertEqual(report["copy_readiness"], "blocked_diagnostic_or_rejected_lifecycle_lines")
                self.assertIn("blocked_diagnostic_or_rejected_lifecycle_lines", report["blockers"])
                self.assertEqual(report["roles_present"], ["session_start", "session_end"])
                self.assertEqual(report["missing_roles"], ["session_start_rejected"])
                self.assertEqual(
                    report["analysis"]["missing_roles_with_unapproved_shape"],
                    ["session_start_rejected"],
                )
                rejected_events = report["analysis"]["rejected_or_incomplete_role_events"]
                rejected_start = next(
                    event for event in rejected_events if event["role"] == "session_start_rejected"
                )
                self.assertEqual(rejected_start["target"], "ShooterGameMode.CheckJoinInProgress")
                self.assertIn("copied_bool_values", rejected_start["approved_copy_shape_mismatches"])
                split = report["ready_log_evidence_split"]
                self.assertEqual(
                    split["classification"],
                    "check_join_in_progress_candidate_not_approved_exact_1_0",
                )
                self.assertTrue(split["missing_exact_check_join_in_progress_1_0"])
                self.assertEqual(split["check_join_in_progress_candidate_count"], 1)
                self.assertEqual(split["next_required_observer_event"]["copied_bool_values"], "1,0")
                self.assertFalse(split["diagnostic_or_rejected_material_counts_as_approved_runtime_evidence"])

    def test_unsafe_principal_logging_fields_block_copy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                lifecycle_log_text().replace(
                    "principal_id_logged=false",
                    "principal_id_logged=true",
                ),
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_diagnostic_or_rejected_lifecycle_lines")
        self.assertIn("blocked_diagnostic_or_rejected_lifecycle_lines", report["blockers"])
        self.assertEqual(
            report["missing_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(
            report["analysis"]["missing_roles_with_unapproved_shape"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertTrue(
            all(
                "principal_id_logged" in event["approved_copy_shape_mismatches"]
                for event in report["analysis"]["rejected_or_incomplete_role_events"]
            )
        )
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_unsafe_copied_player_text_blocks_copy_without_value_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                lifecycle_log_text()
                + "[2026-06-06T13:56:40Z] [warning] retained diagnostic "
                "player_name=ExamplePlayer chat_text=private-message "
                "steam_id=76561198000000000\n",
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertIn("source_log_contains_unsafe_player_text", report["blockers"])
        self.assertEqual(report["source_log_safety"]["unsafe_player_text_line_count"], 1)
        self.assertEqual(
            report["source_log_safety"]["unsafe_player_text_lines"][0]["unsafe_keys"],
            ["chat_text", "player_name", "steam_id"],
        )
        report_text = json.dumps(report, sort_keys=True)
        self.assertNotIn("ExamplePlayer", report_text)
        self.assertNotIn("private-message", report_text)
        self.assertNotIn("76561198000000000", report_text)
        self.assertFalse(report["source_log_safety"]["unsafe_player_text_counts_as_approved_runtime_evidence"])

    def test_onlogout_correlation_drift_blocks_copy_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                lifecycle_log_text().replace(
                    "correlation_status=matched principal_id_logged=false",
                    "correlation_status=unmatched principal_id_logged=false",
                ),
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_diagnostic_or_rejected_lifecycle_lines")
        self.assertIn("blocked_diagnostic_or_rejected_lifecycle_lines", report["blockers"])
        self.assertEqual(report["roles_present"], ["session_start", "session_start_rejected"])
        self.assertEqual(report["missing_roles"], ["session_end"])
        self.assertTrue(report["analysis"]["partial_accepted_lifecycle_role_set"])
        self.assertEqual(report["analysis"]["missing_roles_with_unapproved_shape"], ["session_end"])
        rejected_events = report["analysis"]["rejected_or_incomplete_role_events"]
        rejected_end = next(event for event in rejected_events if event["role"] == "session_end")
        self.assertEqual(rejected_end["target"], "ShooterGameMode.OnLogout")
        self.assertIn("correlation_status", rejected_end["approved_copy_shape_mismatches"])
        self.assertFalse(report["analysis"]["diagnostic_or_rejected_lifecycle_lines_count_as_ready_to_copy"])
        self.assertFalse(report["analysis"]["diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence"])
        self.assertFalse(report["analysis"]["diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_mixed_local_timestamp_observer_lines_block_copy_readiness(self) -> None:
        local_timestamps = {
            "enabled": "13:40:00",
            "session_start": "13:40:01",
            "session_start_rejected": "13:40:02",
            "session_end": "13:40:03",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                lifecycle_log_text(timestamps=local_timestamps) + lifecycle_log_text(),
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--execute",
                "--allow-evidence-dir-write",
                "--json",
            )
            report = json.loads(result.stdout)

            self.assertFalse((evidence / "Obelisk.log").exists())

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["status"], "execute_blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_observer_lifecycle_timestamp_not_utc")
        self.assertIn("blocked_observer_lifecycle_timestamp_not_utc", report["blockers"])
        self.assertGreater(report["analysis"]["timestamp_violation_count"], 0)

    def test_relevant_observer_lines_without_utc_iso_prefix_block_copy_readiness(self) -> None:
        no_timestamp = {key: None for key in DEFAULT_TIMESTAMPS}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(lifecycle_log_text(timestamps=no_timestamp), encoding="utf-8")

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_observer_lifecycle_timestamp_not_utc")
        self.assertIn("blocked_observer_lifecycle_timestamp_not_utc", report["blockers"])
        self.assertEqual(report["analysis"]["timestamp_violation_count"], 4)

    def test_historical_triplet_outside_fresh_window_does_not_satisfy_roles(self) -> None:
        historical_event_timestamps = {
            **DEFAULT_TIMESTAMPS,
            "session_start": "2026-06-06T13:40:01Z",
            "session_start_rejected": "2026-06-06T13:40:02Z",
            "session_end": "2026-06-06T13:40:03Z",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "Obelisk.log"
            evidence = root / "evidence"
            evidence.mkdir()
            source.write_text(
                lifecycle_log_text(timestamps=historical_event_timestamps),
                encoding="utf-8",
            )

            result = run_script(
                "--instance",
                "arkserver3",
                "--source-log",
                str(source),
                "--evidence-dir",
                str(evidence),
                *fresh_window_args(),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["ready_to_copy"])
        self.assertEqual(report["copy_readiness"], "blocked_lifecycle_roles_outside_fresh_window")
        self.assertEqual(report["roles_present"], [])
        self.assertEqual(
            report["missing_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(
            report["analysis"]["historical_roles_present"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertIn("blocked_lifecycle_roles_outside_fresh_window", report["blockers"])


if __name__ == "__main__":
    unittest.main()
