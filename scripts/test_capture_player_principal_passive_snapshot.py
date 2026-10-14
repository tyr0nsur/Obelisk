#!/usr/bin/env python3
"""Tests for passive player-principal snapshot capture."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "capture_player_principal_passive_snapshot.py"


class CapturePlayerPrincipalPassiveSnapshotTests(unittest.TestCase):
    def run_capture(
        self,
        *,
        tmp_path: Path,
        output_dir: Path,
        log_root: Path,
        extra_args: list[str] | None = None,
        env: dict[str, str] | None = None,
        targets: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        target_args = [
            item
            for target in (targets or ["arkserver:Ragnarok:27015", "arkserver2:TheIsland:27016"])
            for item in ("--target", target)
        ]
        command = [
            sys.executable,
            str(SCRIPT),
            "--log-root",
            str(log_root),
            "--output-dir",
            str(output_dir),
            *target_args,
            *(extra_args or []),
        ]
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=merged_env,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

    def load_capture_module(self):
        scripts_dir = str(REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        spec = importlib.util.spec_from_file_location("capture_player_principal_passive_snapshot", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_monitor_metadata_corrects_superseded_rejected_start_from_observer_transcript(self) -> None:
        module = self.load_capture_module()
        with tempfile.TemporaryDirectory() as tmp:
            monitor_log = Path(tmp) / "passive-monitor.log"
            monitor_log.write_text(
                "\n".join(
                    [
                        "passive_monitor_session utc=2026-06-04T05:00:00Z pid=3261082 "
                        "ppid=1 session_id=test-session tmux_session=obelisk_passive_monitor "
                        "tmux_pane=%1 targets=arkserver2:TheIsland:27016 target_count=1 "
                        "interval=10 once=true linger_after_detect=0 process_control=none",
                        "tick utc=2026-06-04T05:00:00Z",
                        "observer_tail instance=arkserver2 status=matched lines=5 scan_lines=200 "
                        "limit=10 map=TheIsland query_port=27016 "
                        "target_key=arkserver2:TheIsland:27016 observer_gate_lines=1 "
                        "accepted_observer_event_triplet_candidate_lines=3 diagnostic_only_lines=1 "
                        "event_roles=session_start,session_start_rejected,session_end "
                        "complete_triplet_candidate=true "
                        "classification=complete_accepted_observer_event_triplet_candidate_non_evidence "
                        "tail_scope=per_target process_control=none "
                        "evidence_classification=passive_tail_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none",
                        "observer instance=arkserver2 map=TheIsland query_port=27016 "
                        "target_key=arkserver2:TheIsland:27016 process_control=none "
                        "evidence_classification=passive_tail_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none "
                        "[05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled "
                        "binary_sha256=test target_set=players-lifecycle-anchor-candidates "
                        "limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.",
                        "observer instance=arkserver2 map=TheIsland query_port=27016 "
                        "target_key=arkserver2:TheIsland:27016 process_control=none "
                        "evidence_classification=passive_tail_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none "
                        "[05:20:01] [warning] PlayerPrincipalLifecycleObserver event "
                        "sequence=1 role=session_start target=ShooterGameMode.HandleNewPlayer "
                        "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
                        "copied_bool_values=1,1 redacted_count=3 "
                        "redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                        "principal_action=candidate_created apply_status=session_start_created "
                        "correlation_status=not_applicable principal_id_logged=false "
                        "principal_generation_logged=false delivery_claim=none.",
                        "observer instance=arkserver2 map=TheIsland query_port=27016 "
                        "target_key=arkserver2:TheIsland:27016 process_control=none "
                        "evidence_classification=passive_tail_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none "
                        "[05:20:02] [warning] PlayerPrincipalLifecycleObserver event "
                        "sequence=2 role=session_start_rejected target=ShooterGameMode.HandleNewPlayer "
                        "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
                        "copied_bool_values=0,1 redacted_count=3 "
                        "redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=none "
                        "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                        "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                        "observer instance=arkserver2 map=TheIsland query_port=27016 "
                        "target_key=arkserver2:TheIsland:27016 process_control=none "
                        "evidence_classification=passive_tail_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none "
                        "[05:20:03] [info] PlayerPrincipalLifecycleDiagnostic candidate "
                        "sequence=3 target=ShooterGameMode.CheckJoinInProgress fname_index=1845 "
                        "post_original=true accepted_lifecycle_target=false reflection_status=matched "
                        "diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue "
                        "copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer "
                        "params_logged=false identity_logged=false evidence_claim=none.",
                        "observer instance=arkserver2 map=TheIsland query_port=27016 "
                        "target_key=arkserver2:TheIsland:27016 process_control=none "
                        "evidence_classification=passive_tail_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none "
                        "[05:20:04] [warning] PlayerPrincipalLifecycleObserver event "
                        "sequence=4 role=session_end target=ShooterGameMode.OnLogout post_original=true "
                        "copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                        "principal_action=candidate_invalidated apply_status=session_end_invalidated "
                        "correlation_status=matched principal_id_logged=false "
                        "principal_generation_logged=false delivery_claim=none.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            metadata = module.parse_monitor_log_metadata(monitor_log)

        tail = metadata["observer_tail_by_target"]["arkserver2:TheIsland:27016"]
        self.assertEqual(tail["raw_observer_event_lines"], 3)
        self.assertEqual(tail["accepted_observer_event_triplet_candidate_lines"], 2)
        self.assertEqual(tail["rejected_observer_event_line_count"], 1)
        self.assertEqual(tail["check_join_rejected_start_candidate_lines"], 0)
        self.assertEqual(tail["superseded_handle_new_player_rejected_start_lines"], 1)
        self.assertEqual(tail["diagnostic_only_lines"], 1)
        self.assertEqual(
            tail["raw_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(tail["event_roles"], ["session_start", "session_end"])
        self.assertFalse(tail["complete_triplet_candidate"])
        self.assertEqual(
            tail["classification"],
            "partial_accepted_observer_event_triplet_candidate_non_evidence",
        )
        self.assertEqual(tail["observer_event_role_policy"], "accepted_safe_observer_events_only")
        self.assertFalse(tail["approved_runtime_evidence"])
        self.assertFalse(tail["ready"])

    def write_logs(
        self,
        log_root: Path,
        *,
        accepted_event: bool = False,
        accepted_triplet: bool = False,
        handle_newplayer_drift: bool = False,
        theisland_onlogout_drift: bool = False,
    ) -> None:
        for instance in ("arkserver", "arkserver2"):
            instance_dir = log_root / instance
            instance_dir.mkdir(parents=True)
            diagnostic_tail = ""
            if instance == "arkserver":
                if handle_newplayer_drift:
                    drift_reason = (
                        "lifecycle_property_FName_drift_unresolved_shape_exact_1_copy_scope_none"
                        "_function_name_index_1773_outer_name_index_9619_drift_count_1"
                        "_drift_0_position_0_drift_0_expected_name_index_17724"
                        "_drift_0_observed_name_index_17730_drift_0_delta_6"
                    )
                    diagnostic_tail = (
                        "[15:02:31] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=6 "
                        "target=ShooterGameMode.HandleNewPlayer fname_index=1773 post_original=true "
                        "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                        f"reason={drift_reason} params_logged=false identity_logged=false "
                        "evidence_claim=none.\n"
                    )
                elif accepted_event:
                    accepted_start = (
                        "[07:00:02] [warning] PlayerPrincipalLifecycleObserver event sequence=1 "
                        "role=session_start target=ShooterGameMode.HandleNewPlayer "
                        "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
                        "copied_bool_values=1,1 redacted_count=3 "
                        "redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                        "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                        "principal_generation_logged=false delivery_claim=none.\n"
                    )
                    accepted_rejected = (
                        "[07:00:03] [warning] PlayerPrincipalLifecycleObserver event sequence=2 "
                        "role=session_start_rejected target=ShooterGameMode.CheckJoinInProgress "
                        "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
                        "copied_bool_values=1,0 redacted_count=1 "
                        "redacted_fields=NewPlayer "
                        "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false "
                        "principal_generation_logged=false delivery_claim=none.\n"
                    )
                    accepted_end = (
                        "[07:00:04] [warning] PlayerPrincipalLifecycleObserver event sequence=3 "
                        "role=session_end target=ShooterGameMode.OnLogout "
                        "post_original=true copied_bool_fields= copied_bool_values= "
                        "redacted_count=1 redacted_fields=Exiting "
                        "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                        "principal_generation_logged=false delivery_claim=none.\n"
                    )
                    diagnostic_tail = accepted_start
                    if accepted_triplet:
                        diagnostic_tail += accepted_rejected + accepted_end
                else:
                    diagnostic_tail = (
                        "[07:00:02] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=10 "
                        "target=ShooterGameMode.OnLogout fname_index=9012 post_original=true "
                        "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                        "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
                        "evidence_claim=none.\n"
                    )
            elif instance == "arkserver2" and theisland_onlogout_drift:
                drift_reason = (
                    "lifecycle_property_FName_drift_unresolved_shape_exact_1_copy_scope_none"
                    "_function_name_index_2171_outer_name_index_9619_drift_count_1"
                    "_drift_0_position_0_drift_0_expected_name_index_17724"
                    "_drift_0_observed_name_index_17731_drift_0_delta_7"
                )
                diagnostic_tail = (
                    "[15:03:37] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=7 "
                    "target=ShooterGameMode.OnLogout fname_index=2171 post_original=true "
                    "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                    f"reason={drift_reason} params_logged=false identity_logged=false "
                    "evidence_claim=none.\n"
                )
            instance_dir.joinpath("Obelisk.log").write_text(
                textwrap.dedent(
                    """\
                    [07:00:00] [info] Obelisk Runtime Loaded Native (LD_PRELOAD)
                    [07:00:00] [info] ProcessEvent vtable-derived pattern candidates found: 1
                    [07:00:00] [info] ProcessEvent candidate[0] = 0x1d34e20
                    [07:00:00] [info] Found ProcessEvent at address: 0x1d34e20
                    [07:00:00] [info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x7000
                    [07:00:00] [info] ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 and enable-reflection-scanner marker to run the experimental scanner.
                    [07:00:00] [warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.
                    [07:00:01] [warning] PlayerPrincipalLifecycleObserver enabled binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
                    [07:00:01] [warning] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false identity_logged=false evidence_claim=none principal_claim=none.
                    """
                )
                + diagnostic_tail,
                encoding="utf-8",
            )

    def test_copies_logs_and_writes_non_claim_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            output_dir = tmp_path / "snapshot"
            monitor_log = tmp_path / "monitor.log"
            self.write_logs(log_root)
            monitor_log.write_text(
                "\n".join(
                    [
                        "passive_monitor_session utc=2026-06-04T05:00:00Z pid=3261082 "
                        "ppid=1 session_id=test-session tmux_session=obelisk_passive_monitor "
                        "tmux_pane=%1 targets=arkserver:Ragnarok:27015,arkserver2:TheIsland:27016 "
                        "target_count=2 interval=10 once=false linger_after_detect=900 "
                        "snapshot_output_root=/tmp/snapshots snapshot_monitor_log=/tmp/monitor.log "
                        "replacement_status=none_reported replaced_monitor_pid=none "
                        "active_monitor_pid=none replacement_requested=false "
                        "old_monitor_action=not_performed_by_passive_monitor replacement_note=none "
                        "replacement_policy=never_signal_stop_or_replace_existing_monitor "
                        "active_monitor_policy=metadata_only_never_signal_stop_or_replace "
                        "process_control=none",
                        "tick utc=2026-06-04T05:00:00Z",
                        "query instance=arkserver map=Ragnarok query_port=27015 status=ok "
                        "current_map=Ragnarok players=1/70 name=Ragnarok "
                        "target_key=arkserver:Ragnarok:27015 players_current=1 players_max=70 "
                        "presence_detected=true detection_source=gamedig_ase_query",
                        "player_presence_detected instance=arkserver map=Ragnarok query_port=27015 "
                        "target_key=arkserver:Ragnarok:27015 detection_source=gamedig_ase_query",
                        "observer_tail instance=arkserver status=matched lines=2 scan_lines=200 "
                        "limit=10 map=Ragnarok query_port=27015 "
                        "target_key=arkserver:Ragnarok:27015 observer_gate_lines=1 "
                        "accepted_observer_event_triplet_candidate_lines=0 diagnostic_only_lines=1 "
                        "event_roles=none complete_triplet_candidate=false "
                        "classification=diagnostic_only_lines_non_evidence tail_scope=per_target "
                        "linger_after_detect=900 linger_active=true "
                        "linger_until_utc=2026-06-04T05:15:00Z process_control=none "
                        "evidence_classification=passive_tail_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none",
                        "player_presence_linger_start seconds=900 "
                        "until_utc=2026-06-04T05:15:00Z detected_instances=arkserver "
                        "observer_tail=per_target target_keys=arkserver:Ragnarok:27015 "
                        "process_control=none evidence_classification=passive_linger_metadata_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none",
                        "passive_snapshot_captured output_dir=/tmp/snapshots/passive-detect-test "
                        "detected_instances=arkserver detected_target_keys=arkserver:Ragnarok:27015 "
                        "snapshot_sequence=1 snapshot_target_count=1 "
                        "snapshot_trigger_policy=per_target_new_detection summary={} "
                        "process_control=none evidence_classification=passive_snapshot_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none",
                        "query instance=arkserver2 map=TheIsland query_port=27016 status=ok "
                        "current_map=TheIsland players=0/70 name=TheIsland "
                        "target_key=arkserver2:TheIsland:27016 players_current=0 players_max=70 "
                        "presence_detected=false detection_source=gamedig_ase_query",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=output_dir,
                log_root=log_root,
                extra_args=["--monitor-log", str(monitor_log)],
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads(output_dir.joinpath("manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], "obelisk.player-principal-passive-snapshot.v1")
            self.assertFalse(manifest["ready"])
            self.assertEqual(manifest["source_kind"], "passive_snapshot")
            self.assertEqual(manifest["ready_scope"], "passive_snapshot_only")
            self.assertFalse(manifest["approved_runtime_evidence"])
            self.assertEqual(manifest["approved_evidence_claim"], "none")
            self.assertEqual(manifest["evidence_classification"], "passive_snapshot_non_evidence")
            self.assertEqual(
                manifest["promotion_blockers"],
                ["passive_snapshot_not_approved_runtime_evidence"],
            )
            self.assertTrue(manifest["all_logs_copied"])
            self.assertEqual(manifest["target_count"], 2)
            self.assertIn("approved_runtime_evidence remains false", manifest["non_claims"])
            self.assertIn("public SDK readiness", " ".join(manifest["non_claims"]))
            self.assertIn("organic detection metadata only", " ".join(manifest["non_claims"]))
            self.assertIn("copied sibling-set bundle", " ".join(manifest["non_claims"]))
            self.assertEqual(manifest["diagnostics"]["candidate_count"], 1)
            self.assertEqual(manifest["diagnostics"]["max_sequence"], 10)
            self.assertEqual(manifest["diagnostics"]["log_limits"], [10])
            self.assertTrue(manifest["diagnostics"]["log_budget_reached"])
            self.assertEqual(
                manifest["diagnostics"]["observer_event_triage"]["classification"],
                "diagnostic_only_lines_non_evidence",
            )
            self.assertFalse(
                manifest["diagnostics"]["observer_event_triage"][
                    "approved_runtime_evidence"
                ]
            )
            self.assertFalse(manifest["diagnostics"]["observer_event_triage"]["ready"])
            self.assertEqual(
                manifest["diagnostics"]["observer_event_triage"]["readiness_gate"],
                "none",
            )
            self.assertFalse(
                manifest["diagnostics"]["observer_event_triage"][
                    "contains_accepted_observer_event_triplet_candidates"
                ]
            )
            self.assertTrue(
                manifest["diagnostics"]["observer_event_triage"][
                    "contains_diagnostic_only_lines"
                ]
            )
            self.assertEqual(
                manifest["diagnostics"]["diagnostic_only_non_evidence_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            actionability = manifest["passive_actionability"]
            self.assertEqual(
                actionability["schema"],
                "obelisk.player-principal-passive-actionability.v1",
            )
            self.assertEqual(actionability["priority"], "repeated_diagnostics_only")
            self.assertEqual(actionability["runner_priority_rank"], 40)
            self.assertEqual(actionability["runner_focus"], "diagnostic_candidate_count_tracking")
            self.assertEqual(actionability["targets"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                actionability["targets_with_players_detected"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertFalse(actionability["approved_runtime_evidence"])
            self.assertFalse(actionability["ready"])
            self.assertFalse(actionability["route_ready"])
            self.assertEqual(actionability["process_control"], "none")
            runner_hint = actionability["runner_action_hints"][0]
            self.assertEqual(
                runner_hint["id"],
                "compare_passive_diagnostic_counts_before_request",
            )
            self.assertEqual(runner_hint["target_keys"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(runner_hint["process_control"], "none")
            self.assertFalse(runner_hint["approved_runtime_evidence"])
            self.assertFalse(runner_hint["ready"])
            closure = manifest["passive_closure_summary"]
            self.assertEqual(
                closure["schema"],
                "obelisk.player-principal-passive-closure-summary.v1",
            )
            self.assertEqual(
                closure["closure_status"],
                "closed_non_evidence_no_progress_no_readiness",
            )
            self.assertEqual(
                closure["closure_classification"],
                "diagnostic_only_observer_lines_no_progress_no_readiness_non_evidence",
            )
            self.assertFalse(closure["valid_closure_root"])
            self.assertFalse(closure["source_root_valid_for_closure"])
            self.assertFalse(closure["runtime_evidence_ready"])
            self.assertEqual(closure["sdk_progress"], 0)
            self.assertEqual(closure["p0_progress"], 0)
            self.assertEqual(closure["diagnostic_only_targets"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                manifest["diagnostics"]["latest_observer_lines_by_target"]["arkserver:Ragnarok:27015"][
                    "timestamp_prefix"
                ],
                "07:00:02",
            )
            monitor_metadata = manifest["monitor_log"]["metadata"]
            self.assertEqual(monitor_metadata["session"]["pid"], 3261082)
            self.assertEqual(monitor_metadata["session"]["session_id"], "test-session")
            self.assertEqual(monitor_metadata["session"]["target_count"], 2)
            self.assertEqual(
                monitor_metadata["session"]["active_monitor_policy"],
                "metadata_only_never_signal_stop_or_replace",
            )
            self.assertEqual(monitor_metadata["replacement"]["status"], "none_reported")
            self.assertEqual(
                monitor_metadata["replacement"]["replacement_policy"],
                "never_signal_stop_or_replace_existing_monitor",
            )
            self.assertFalse(monitor_metadata["replacement"]["replacement_requested"])
            self.assertEqual(monitor_metadata["replacement"]["process_control"], "none")
            self.assertEqual(monitor_metadata["latest_tick_utc"], "2026-06-04T05:00:00Z")
            self.assertEqual(
                monitor_metadata["query_state_by_instance"]["arkserver"]["players_current"],
                1,
            )
            self.assertEqual(
                monitor_metadata["query_state_by_target"]["arkserver:Ragnarok:27015"][
                    "players_current"
                ],
                1,
            )
            observer_tail = monitor_metadata["observer_tail_by_target"][
                "arkserver:Ragnarok:27015"
            ]
            self.assertEqual(observer_tail["target_key"], "arkserver:Ragnarok:27015")
            self.assertEqual(observer_tail["tail_scope"], "per_target")
            self.assertTrue(observer_tail["linger_active"])
            self.assertEqual(observer_tail["process_control"], "none")
            self.assertFalse(observer_tail["approved_runtime_evidence"])
            linger_events = monitor_metadata["linger_by_target"]["arkserver:Ragnarok:27015"]
            self.assertEqual(linger_events[0]["event"], "player_presence_linger_start")
            self.assertEqual(linger_events[0]["target_keys"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(linger_events[0]["process_control"], "none")
            self.assertFalse(linger_events[0]["approved_runtime_evidence"])
            snapshot_event = monitor_metadata["snapshot_events"][0]
            self.assertEqual(snapshot_event["event"], "passive_snapshot_captured")
            self.assertEqual(snapshot_event["snapshot_sequence"], 1)
            self.assertEqual(snapshot_event["snapshot_target_count"], 1)
            self.assertEqual(
                snapshot_event["snapshot_trigger_policy"],
                "per_target_new_detection",
            )
            self.assertEqual(
                snapshot_event["detected_target_keys"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(snapshot_event["process_control"], "none")
            self.assertFalse(snapshot_event["approved_runtime_evidence"])
            wait_metadata = manifest["passive_wait_metadata"]
            self.assertEqual(wait_metadata["process_control"], "none")
            self.assertIn("arkserver:Ragnarok:27015", wait_metadata["observer_tail_by_target"])
            self.assertIn("arkserver:Ragnarok:27015", wait_metadata["linger_by_target"])
            self.assertTrue(
                monitor_metadata["query_state_by_instance"]["arkserver"]["presence_detected"]
            )
            self.assertEqual(
                manifest["query_state_by_instance"]["arkserver2"]["players_current"],
                0,
            )
            self.assertEqual(
                manifest["query_state_by_target"]["arkserver2:TheIsland:27016"][
                    "players_current"
                ],
                0,
            )
            self.assertEqual(
                manifest["organic_detection"]["schema"],
                "obelisk.passive-organic-player-detection.v1",
            )
            self.assertEqual(
                manifest["organic_detection"]["detected_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertFalse(manifest["organic_detection"]["approved_runtime_evidence"])
            for target in manifest["targets"]:
                self.assertIn("target_key", target)
                self.assertEqual(target["source_kind"], "passive_snapshot")
                self.assertEqual(target["ready_scope"], "passive_snapshot_only")
                self.assertEqual(target["copy_status"], "copied")
                self.assertEqual(target["counts"]["accepted"], 0)
                self.assertEqual(target["counts"]["rejected"], 0)
                self.assertEqual(target["readiness_gate"], "none")
                self.assertFalse(target["approved_runtime_evidence"])
                self.assertEqual(target["approved_evidence_claim"], "none")
                self.assertFalse(target["ready"])
                self.assertEqual(target["evidence_classification"], "passive_snapshot_non_evidence")
                self.assertEqual(
                    target["promotion_blockers"],
                    ["passive_snapshot_not_approved_runtime_evidence"],
                )
                if target["instance"] == "arkserver":
                    self.assertEqual(target["target_key"], "arkserver:Ragnarok:27015")
                    self.assertEqual(target["counts"]["diagnostic_candidates"], 1)
                    self.assertEqual(target["diagnostics"]["max_sequence"], 10)
                    self.assertTrue(target["diagnostics"]["log_budget_reached"])
                    self.assertTrue(target["diagnostic_only_non_evidence"])
                    self.assertEqual(target["diagnostics"]["classification"], "diagnostic_only_non_evidence")
                    self.assertEqual(
                        target["observer_event_triage"]["classification"],
                        "diagnostic_only_lines_non_evidence",
                    )
                    self.assertFalse(target["observer_event_triage"]["approved_runtime_evidence"])
                    self.assertFalse(target["observer_event_triage"]["ready"])
                    self.assertEqual(target["query_state"]["players_current"], 1)
                    self.assertTrue(target["query_state"]["presence_detected"])
                    self.assertEqual(
                        target["diagnostics"]["latest_observer_line"]["kind"],
                        "diagnostic_candidate",
                    )
                else:
                    self.assertEqual(target["target_key"], "arkserver2:TheIsland:27016")
                    self.assertEqual(target["counts"]["diagnostic_candidates"], 0)
                    self.assertIsNone(target["diagnostics"]["max_sequence"])
                    self.assertFalse(target["diagnostics"]["log_budget_reached"])
                    self.assertFalse(target["diagnostic_only_non_evidence"])
                    self.assertEqual(
                        target["observer_event_triage"]["classification"],
                        "no_player_principal_observer_lines_non_evidence",
                    )
                    self.assertEqual(target["query_state"]["players_current"], 0)
            self.assertEqual(manifest["monitor_log"]["copy_status"], "copied")

    def test_accepted_observer_lines_remain_passive_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            output_dir = tmp_path / "snapshot"
            self.write_logs(log_root, accepted_event=True, accepted_triplet=True)

            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=output_dir,
                log_root=log_root,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads(output_dir.joinpath("manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["approved_runtime_evidence"])
            self.assertFalse(manifest["ready"])
            self.assertEqual(manifest["evidence_classification"], "passive_snapshot_non_evidence")
            self.assertEqual(manifest["source_kind"], "passive_snapshot")
            self.assertEqual(manifest["ready_scope"], "passive_snapshot_only")
            arkserver = next(
                target for target in manifest["targets"] if target["instance"] == "arkserver"
            )
            self.assertEqual(arkserver["counts"]["accepted"], 3)
            self.assertEqual(arkserver["counts"]["diagnostic_candidates"], 0)
            self.assertFalse(arkserver["approved_runtime_evidence"])
            self.assertFalse(arkserver["ready"])
            self.assertEqual(arkserver["evidence_classification"], "passive_snapshot_non_evidence")
            self.assertEqual(arkserver["approved_evidence_claim"], "none")
            self.assertEqual(
                arkserver["promotion_blockers"],
                ["passive_snapshot_not_approved_runtime_evidence"],
            )
            triage = arkserver["observer_event_triage"]
            self.assertEqual(
                triage["classification"],
                "complete_accepted_observer_event_triplet_candidate_non_evidence",
            )
            self.assertEqual(
                triage["accepted_observer_event_triplet_candidate_count"],
                3,
            )
            self.assertTrue(triage["contains_accepted_observer_event_triplet_candidates"])
            self.assertFalse(triage["contains_diagnostic_only_lines"])
            self.assertEqual(
                triage["accepted_observer_event_roles"],
                ["session_start", "session_start_rejected", "session_end"],
            )
            self.assertTrue(triage["complete_observer_event_triplet_candidate_present"])
            self.assertFalse(triage["approved_runtime_evidence"])
            self.assertFalse(triage["ready"])
            self.assertEqual(triage["readiness_gate"], "none")
            self.assertEqual(
                manifest["diagnostics"]["observer_event_triage"]["classification"],
                "complete_accepted_observer_event_triplet_candidate_non_evidence",
            )
            self.assertEqual(
                manifest["diagnostics"]["observer_event_triage"][
                    "targets_with_complete_observer_event_triplet_candidate"
                ],
                ["arkserver:Ragnarok:27015"],
            )
            actionability = manifest["passive_actionability"]
            self.assertEqual(
                actionability["priority"],
                "accepted_observer_event_triplet_candidate",
            )
            self.assertEqual(actionability["runner_priority_rank"], 10)
            self.assertEqual(
                actionability["reason_kind"],
                "complete_accepted_observer_event_triplet_candidate_present",
            )
            self.assertEqual(actionability["targets"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                actionability["complete_observer_event_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertFalse(actionability["approved_runtime_evidence"])
            self.assertFalse(actionability["ready"])
            self.assertFalse(actionability["route_ready"])
            runner_hint = actionability["runner_action_hints"][0]
            self.assertEqual(
                runner_hint["id"],
                "prepare_fresh_operator_approved_evidence_request_from_triplet_candidate",
            )
            self.assertEqual(
                runner_hint["focus"],
                "complete_triplet_candidate_request_preflight",
            )
            self.assertEqual(runner_hint["process_control"], "none")
            self.assertFalse(runner_hint["approved_runtime_evidence"])
            self.assertFalse(runner_hint["ready"])

    def test_alias_presence_metadata_does_not_override_exact_query_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            output_dir = tmp_path / "snapshot"
            monitor_log = tmp_path / "monitor.log"
            self.write_logs(log_root)
            monitor_log.write_text(
                "\n".join(
                    [
                        "passive_monitor_session utc=2026-06-04T11:30:21Z pid=3261082 "
                        "ppid=1 session_id=test-session tmux_session=obelisk_passive_monitor "
                        "tmux_pane=%1 targets=arkserver:Ragnarok:27015,arkserver2:TheIsland:27016 "
                        "target_count=2 interval=10 once=false linger_after_detect=900 "
                        "snapshot_output_root=/tmp/snapshots snapshot_monitor_log=/tmp/monitor.log "
                        "replacement_status=active_monitor_reported_metadata_only replaced_monitor_pid=3261082 "
                        "active_monitor_pid=3261082 replacement_requested=false "
                        "old_monitor_action=not_performed_by_passive_monitor replacement_note=none "
                        "replacement_policy=never_signal_stop_or_replace_existing_monitor "
                        "active_monitor_policy=metadata_only_never_signal_stop_or_replace "
                        "process_control=none",
                        "tick utc=2026-06-04T11:30:21Z",
                        "query instance=arkserver2 map=TheIsland query_port=27016 status=ok "
                        "current_map=TheIsland players=0/70 name=TheIsland "
                        "target_key=arkserver2:TheIsland:27016 players_current=0 players_max=70 "
                        "presence_detected=false detection_source=gamedig_ase_query",
                        "player_presence_detected instance=arkserver2 map=TheIsland "
                        "target_key=arkserver2:TheIsland detection_source=gamedig_ase_query",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=output_dir,
                log_root=log_root,
                extra_args=["--monitor-log", str(monitor_log)],
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads(output_dir.joinpath("manifest.json").read_text(encoding="utf-8"))
            monitor_metadata = manifest["monitor_log"]["metadata"]
            self.assertIn("arkserver2:TheIsland:27016", monitor_metadata["query_state_by_target"])
            self.assertNotIn("arkserver2:TheIsland", monitor_metadata["query_state_by_target"])
            self.assertIn("arkserver2:TheIsland", monitor_metadata["query_state_by_alias"])
            self.assertEqual(
                monitor_metadata["query_state_by_alias"]["arkserver2:TheIsland"][
                    "target_key_kind"
                ],
                "alias",
            )
            self.assertFalse(
                monitor_metadata["query_state_by_alias"]["arkserver2:TheIsland"][
                    "approved_runtime_evidence"
                ]
            )
            self.assertNotIn("arkserver2:TheIsland", manifest["query_state_by_target"])
            self.assertEqual(
                manifest["query_state_by_target"]["arkserver2:TheIsland:27016"][
                    "players_current"
                ],
                0,
            )
            self.assertFalse(
                manifest["query_state_by_target"]["arkserver2:TheIsland:27016"][
                    "presence_detected"
                ]
            )
            self.assertIn("arkserver2:TheIsland", manifest["query_state_by_alias"])
            self.assertEqual(
                manifest["organic_detection"]["alias_presence_metadata_only_targets"],
                ["arkserver2:TheIsland"],
            )
            self.assertEqual(manifest["organic_detection"]["detected_targets"], [])
            arkserver2 = next(
                target for target in manifest["targets"] if target["instance"] == "arkserver2"
            )
            self.assertEqual(arkserver2["query_state"]["target_key_kind"], "exact")
            self.assertEqual(arkserver2["query_state"]["players_current"], 0)
            self.assertFalse(arkserver2["query_state"]["presence_detected"])

    def test_theisland_onlogout_rejected_drift_after_presence_stays_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            output_dir = tmp_path / "snapshot"
            monitor_log = tmp_path / "monitor.log"
            self.write_logs(log_root, theisland_onlogout_drift=True)
            monitor_log.write_text(
                "\n".join(
                    [
                        "passive_monitor_session utc=2026-06-04T13:03:37Z pid=3261082 "
                        "ppid=1 session_id=test-session tmux_session=obelisk_passive_monitor "
                        "tmux_pane=%1 targets=arkserver:Ragnarok:27015,arkserver2:TheIsland:27016 "
                        "target_count=2 interval=10 once=false linger_after_detect=900 "
                        "snapshot_output_root=/tmp/snapshots snapshot_monitor_log=/tmp/monitor.log "
                        "replacement_status=none_reported replaced_monitor_pid=none "
                        "active_monitor_pid=none replacement_requested=false "
                        "old_monitor_action=not_performed_by_passive_monitor replacement_note=none "
                        "replacement_policy=never_signal_stop_or_replace_existing_monitor "
                        "active_monitor_policy=metadata_only_never_signal_stop_or_replace "
                        "process_control=none",
                        "tick utc=2026-06-04T13:03:37Z",
                        "query instance=arkserver2 map=TheIsland query_port=27016 status=ok "
                        "current_map=TheIsland players=1/70 name=TheIsland "
                        "target_key=arkserver2:TheIsland:27016 players_current=1 players_max=70 "
                        "presence_detected=true detection_source=gamedig_ase_query",
                        "player_presence_detected instance=arkserver2 map=TheIsland query_port=27016 "
                        "target_key=arkserver2:TheIsland:27016 detection_source=gamedig_ase_query",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=output_dir,
                log_root=log_root,
                extra_args=["--monitor-log", str(monitor_log)],
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads(output_dir.joinpath("manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["approved_runtime_evidence"])
            self.assertFalse(manifest["ready"])
            self.assertEqual(manifest["readiness_gate"], "none")
            self.assertEqual(manifest["monitor_log"]["metadata"]["process_control"], "none")
            self.assertEqual(
                manifest["monitor_log"]["metadata"]["replacement"]["process_control"],
                "none",
            )
            self.assertEqual(
                manifest["organic_detection"]["detected_targets"],
                ["arkserver2:TheIsland:27016"],
            )
            self.assertEqual(
                manifest["diagnostics"]["rejected_drift_targets"],
                ["arkserver2:TheIsland:27016"],
            )
            arkserver2 = next(
                target for target in manifest["targets"] if target["instance"] == "arkserver2"
            )
            self.assertEqual(arkserver2["target_key"], "arkserver2:TheIsland:27016")
            self.assertEqual(arkserver2["counts"]["accepted"], 0)
            self.assertEqual(arkserver2["counts"]["rejected"], 0)
            self.assertEqual(arkserver2["counts"]["diagnostic_candidates"], 1)
            self.assertFalse(arkserver2["approved_runtime_evidence"])
            self.assertFalse(arkserver2["ready"])
            self.assertEqual(arkserver2["readiness_gate"], "none")
            self.assertTrue(arkserver2["query_state"]["presence_detected"])
            self.assertEqual(arkserver2["query_state"]["players_current"], 1)
            self.assertFalse(
                arkserver2["observer_event_triage"][
                    "contains_accepted_observer_event_triplet_candidates"
                ]
            )
            self.assertFalse(
                arkserver2["observer_event_triage"][
                    "complete_observer_event_triplet_candidate_present"
                ]
            )
            self.assertTrue(arkserver2["diagnostics"]["contains_rejected_drift"])
            drift = arkserver2["diagnostics"]["latest_rejected_drift_by_lifecycle_target"][
                "ShooterGameMode.OnLogout"
            ]
            self.assertEqual(drift["timestamp_prefix"], "15:03:37")
            self.assertEqual(drift["target"], "ShooterGameMode.OnLogout")
            self.assertEqual(drift["reflection_status"], "rejected")
            self.assertEqual(drift["evidence_claim"], "none")
            self.assertFalse(drift["approved_runtime_evidence"])
            self.assertFalse(drift["ready"])
            self.assertEqual(drift["readiness_gate"], "none")
            self.assertNotIn("params_logged", drift)
            self.assertNotIn("identity_logged", drift)
            self.assertNotIn("raw_params", drift)

    def test_dual_server_activity_summary_is_sanitized_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            output_dir = tmp_path / "snapshot"
            monitor_log = tmp_path / "monitor.log"
            self.write_logs(
                log_root,
                handle_newplayer_drift=True,
                theisland_onlogout_drift=True,
            )
            monitor_log.write_text(
                "\n".join(
                    [
                        "passive_monitor_session utc=2026-06-04T15:02:31Z pid=3261082 "
                        "ppid=1 session_id=test-session tmux_session=obelisk_passive_monitor "
                        "tmux_pane=%1 targets=arkserver:Ragnarok:27015,arkserver2:TheIsland:27016 "
                        "target_count=2 interval=10 once=false linger_after_detect=900 "
                        "snapshot_output_root=/tmp/snapshots snapshot_monitor_log=/tmp/monitor.log "
                        "replacement_status=none_reported replaced_monitor_pid=none "
                        "active_monitor_pid=none replacement_requested=false "
                        "old_monitor_action=not_performed_by_passive_monitor replacement_note=none "
                        "replacement_policy=never_signal_stop_or_replace_existing_monitor "
                        "active_monitor_policy=metadata_only_never_signal_stop_or_replace "
                        "process_control=none",
                        "tick utc=2026-06-04T15:02:31Z",
                        "query instance=arkserver map=Ragnarok query_port=27015 status=ok "
                        "current_map=Ragnarok players=2/70 name=Ragnarok "
                        "target_key=arkserver:Ragnarok:27015 players_current=2 players_max=70 "
                        "presence_detected=true detection_source=gamedig_ase_query",
                        "player_presence_detected instance=arkserver map=Ragnarok query_port=27015 "
                        "target_key=arkserver:Ragnarok:27015 detection_source=gamedig_ase_query",
                        "query instance=arkserver2 map=TheIsland query_port=27016 status=ok "
                        "current_map=TheIsland players=1/70 name=TheIsland "
                        "target_key=arkserver2:TheIsland:27016 players_current=1 players_max=70 "
                        "presence_detected=true detection_source=gamedig_ase_query",
                        "player_presence_detected instance=arkserver2 map=TheIsland query_port=27016 "
                        "target_key=arkserver2:TheIsland:27016 detection_source=gamedig_ase_query",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=output_dir,
                log_root=log_root,
                extra_args=["--monitor-log", str(monitor_log)],
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads(output_dir.joinpath("manifest.json").read_text(encoding="utf-8"))
            summary = manifest["passive_server_activity_summary"]
            self.assertEqual(
                summary["schema"],
                "obelisk.player-principal-passive-server-activity-summary.v1",
            )
            self.assertFalse(summary["approved_runtime_evidence"])
            self.assertFalse(summary["ready"])
            self.assertEqual(summary["readiness_gate"], "none")
            self.assertEqual(summary["process_control"], "none")
            self.assertTrue(summary["both_servers_active"])
            self.assertTrue(summary["all_expected_servers_active"])
            self.assertEqual(
                summary["active_targets"],
                ["arkserver2:TheIsland:27016", "arkserver:Ragnarok:27015"],
            )
            self.assertTrue(summary["players_detected"])
            self.assertEqual(summary["players_current_known_total"], 3)
            self.assertEqual(
                summary["players_current_by_target"],
                {
                    "arkserver:Ragnarok:27015": 2,
                    "arkserver2:TheIsland:27016": 1,
                },
            )
            handle_reason = summary["latest_rejected_drift_reason_by_lifecycle_target"][
                "ShooterGameMode.HandleNewPlayer"
            ]["arkserver:Ragnarok:27015"]
            logout_reason = summary["latest_rejected_drift_reason_by_lifecycle_target"][
                "ShooterGameMode.OnLogout"
            ]["arkserver2:TheIsland:27016"]
            self.assertEqual(handle_reason["target"], "ShooterGameMode.HandleNewPlayer")
            self.assertEqual(handle_reason["reason_kind"], "lifecycle_property_FName_drift")
            self.assertEqual(handle_reason["process_control"], "none")
            self.assertFalse(handle_reason["approved_runtime_evidence"])
            self.assertEqual(logout_reason["target"], "ShooterGameMode.OnLogout")
            self.assertEqual(logout_reason["reason_kind"], "lifecycle_property_FName_drift")
            serialized = json.dumps(summary, sort_keys=True).lower()
            for forbidden in (
                "steamid",
                "eosid",
                "playername",
                "playerid",
                "ipaddress",
                "rawpointer",
                "pointer",
                "params_logged",
                "identity_logged",
                "raw_params",
            ):
                self.assertNotIn(forbidden, serialized)

    def test_monitor_process_control_metadata_is_forced_to_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            output_dir = tmp_path / "snapshot"
            monitor_log = tmp_path / "monitor.log"
            self.write_logs(log_root)
            monitor_log.write_text(
                "passive_monitor_session utc=2026-06-04T12:00:00Z pid=100 "
                "ppid=1 session_id=test-session tmux_session=none tmux_pane=none "
                "targets=arkserver:Ragnarok:27015 target_count=1 interval=10 once=true "
                "linger_after_detect=0 snapshot_output_root=none snapshot_monitor_log=none "
                "replacement_status=explicit_replacement_requested_metadata_only "
                "replaced_monitor_pid=200 active_monitor_pid=200 replacement_requested=true "
                "old_monitor_action=not_performed_by_passive_monitor replacement_note=test "
                "replacement_policy=never_signal_stop_or_replace_existing_monitor "
                "active_monitor_policy=metadata_only_never_signal_stop_or_replace "
                "process_control=terminate\n",
                encoding="utf-8",
            )

            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=output_dir,
                log_root=log_root,
                extra_args=["--monitor-log", str(monitor_log)],
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads(output_dir.joinpath("manifest.json").read_text(encoding="utf-8"))
            metadata = manifest["monitor_log"]["metadata"]
            self.assertEqual(metadata["process_control"], "none")
            self.assertEqual(metadata["reported_process_control"], "terminate")
            self.assertEqual(metadata["session"]["process_control"], "none")
            self.assertEqual(metadata["session"]["reported_process_control"], "terminate")
            self.assertEqual(metadata["replacement"]["process_control"], "none")
            self.assertEqual(metadata["replacement"]["reported_process_control"], "terminate")
            self.assertEqual(
                metadata["replacement"]["process_control_policy"],
                "passive_metadata_only_never_signal_stop_or_replace",
            )

    def test_direct_portless_target_query_state_is_alias_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            output_dir = tmp_path / "snapshot"
            instance_dir = log_root / "customserver"
            instance_dir.mkdir(parents=True)
            instance_dir.joinpath("Obelisk.log").write_text(
                "[07:00:00] [info] Obelisk Runtime Loaded Native (LD_PRELOAD)\n",
                encoding="utf-8",
            )

            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=output_dir,
                log_root=log_root,
                targets=["customserver:Aberration"],
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads(output_dir.joinpath("manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["query_state_by_target"], {})
            self.assertIn("customserver:Aberration", manifest["query_state_by_alias"])
            alias_state = manifest["query_state_by_alias"]["customserver:Aberration"]
            self.assertEqual(alias_state["target_key_kind"], "alias")
            self.assertTrue(alias_state["alias_presence_metadata_only"])
            self.assertFalse(alias_state["query_presence_eligible"])
            self.assertEqual(
                alias_state["evidence_classification"],
                "passive_alias_presence_metadata_non_evidence",
            )
            self.assertFalse(alias_state["approved_runtime_evidence"])
            self.assertFalse(alias_state["ready"])
            self.assertEqual(alias_state["readiness_gate"], "none")
            target = manifest["targets"][0]
            self.assertEqual(target["query_state"]["target_key_kind"], "alias")
            self.assertTrue(target["query_state"]["alias_presence_metadata_only"])
            self.assertNotIn("customserver:Aberration", manifest["organic_detection"]["detected_targets"])

    def test_analyzer_summary_sanitizer_keeps_passive_snapshot_non_evidence(self) -> None:
        module = self.load_capture_module()
        sanitized = module.sanitize_analyzer_summary_for_passive_snapshot(
            {
                "approved_runtime_evidence": True,
                "ready": True,
                "runtime_evidence_ready": True,
                "readiness_gate": "approved_runtime_bundle",
                "modules": {
                    "player_principal_lifecycle": {
                        "accepted_count": 3,
                        "approved_runtime_evidence": True,
                        "ready": True,
                        "runtime_evidence_ready": True,
                    }
                },
            }
        )

        self.assertFalse(sanitized["approved_runtime_evidence"])
        self.assertFalse(sanitized["ready"])
        self.assertFalse(sanitized["runtime_evidence_ready"])
        self.assertEqual(sanitized["readiness_gate"], "none")
        lifecycle = sanitized["modules"]["player_principal_lifecycle"]
        self.assertEqual(lifecycle["accepted_count"], 3)
        self.assertFalse(lifecycle["approved_runtime_evidence"])
        self.assertFalse(lifecycle["ready"])
        self.assertFalse(lifecycle["runtime_evidence_ready"])

    def test_rejects_live_server_log_root_without_explicit_allow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capture(
                tmp_path=Path(tmp),
                output_dir=Path(tmp) / "snapshot",
                log_root=Path("/servidor/ark/obelisk/logs"),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("refuses live server path without --allow-server-path", result.stderr)

    def test_rejects_protected_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            self.write_logs(log_root)
            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=Path("/servidor/ark/serverfiles/passive-snapshot"),
                log_root=log_root,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("must not write under protected server root", result.stderr)

    def test_rejects_symlinked_protected_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            link = tmp_path / "server-link"
            self.write_logs(log_root)
            link.symlink_to("/servidor/ark/obelisk")
            result = self.run_capture(
                tmp_path=tmp_path,
                output_dir=link / "passive-snapshot",
                log_root=log_root,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("must not be a symlink", result.stderr)

    def test_rejects_unsafe_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_root = tmp_path / "logs"
            output_dir = tmp_path / "snapshot"
            self.write_logs(log_root)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--log-root",
                    str(log_root),
                    "--output-dir",
                    str(output_dir),
                    "--target",
                    "../arkserver:Ragnarok",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("unsafe instance", result.stderr)


if __name__ == "__main__":
    unittest.main()
