#!/usr/bin/env python3
"""Tests for passive player-principal snapshot manifest diffs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "summarize_player_principal_passive_snapshots.py"
CAPTURE_SCRIPT = REPO_ROOT / "scripts" / "capture_player_principal_passive_snapshot.py"
REQUIRED_OBSERVER_EVENT_ROLES = ("session_start", "session_start_rejected", "session_end")


def observer_event_triage(
    *,
    accepted: int,
    rejected: int,
    diagnostic_candidates: int,
    accepted_roles: list[str] | None = None,
) -> dict[str, object]:
    roles = [
        role
        for role in REQUIRED_OBSERVER_EVENT_ROLES
        if role in set(accepted_roles or [])
    ]
    missing_roles = [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role not in roles]
    complete_triplet = accepted > 0 and not missing_roles
    if complete_triplet:
        classification = "complete_accepted_observer_event_triplet_candidate_non_evidence"
    elif accepted > 0:
        classification = "partial_accepted_observer_event_triplet_candidate_non_evidence"
    elif rejected > 0:
        classification = "rejected_observer_event_lines_non_evidence"
    elif diagnostic_candidates > 0:
        classification = "diagnostic_only_lines_non_evidence"
    else:
        classification = "no_player_principal_observer_lines_non_evidence"
    return {
        "schema": "obelisk.player-principal-passive-observer-event-triage.v1",
        "accepted_observer_event_triplet_candidate_count": accepted,
        "rejected_observer_event_line_count": rejected,
        "diagnostic_only_line_count": diagnostic_candidates,
        "contains_accepted_observer_event_triplet_candidates": accepted > 0,
        "contains_diagnostic_only_lines": diagnostic_candidates > 0,
        "accepted_observer_event_roles": roles,
        "missing_observer_event_triplet_roles": missing_roles,
        "complete_observer_event_triplet_candidate_present": complete_triplet,
        "classification": classification,
        "evidence_classification": "passive_snapshot_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
    }


def rejected_drift(
    *,
    target: str = "ShooterGameMode.OnLogout",
    timestamp_prefix: str = "15:03:37",
    sequence: int = 7,
    fname_index: int = 2171,
) -> dict[str, object]:
    reason = (
        "lifecycle_property_FName_drift_unresolved_shape_exact_1_copy_scope_none"
        f"_function_name_index_{fname_index}_outer_name_index_9619_drift_count_1"
        "_drift_0_position_0_drift_0_expected_name_index_17724"
        "_drift_0_observed_name_index_17731_drift_0_delta_7"
    )
    return {
        "target": target,
        "sequence": sequence,
        "line_number": 84,
        "timestamp_prefix": timestamp_prefix,
        "fname_index": fname_index,
        "reflection_status": "rejected",
        "read_status": "implausible",
        "reason": reason,
        "reason_kind": "lifecycle_property_FName_drift",
        "function_name_index": fname_index,
        "outer_name_index": 9619,
        "drift_count": 1,
        "drifts": [
            {
                "index": 0,
                "position": 0,
                "expected_name_index": 17724,
                "observed_name_index": 17731,
                "delta": 7,
            }
        ],
        "evidence_claim": "none",
        "evidence_classification": "diagnostic_rejected_drift_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
    }


def passive_manifest(
    *,
    diagnostic_candidates: int,
    accepted: int = 0,
    rejected: int = 0,
    max_sequence: int | None = None,
    log_budget_reached: bool | None = None,
    presence_detected: bool = False,
    players_current: int = 0,
    latest_observer_line: dict[str, object] | None = None,
    accepted_roles: list[str] | None = None,
    instance: str = "arkserver",
    game_map: str = "Ragnarok",
    query_port: str = "27015",
    latest_rejected_drift_by_lifecycle_target: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    if max_sequence is None and diagnostic_candidates > 0:
        max_sequence = diagnostic_candidates
    if log_budget_reached is None:
        log_budget_reached = max_sequence is not None and max_sequence >= 10
    diagnostic_only_non_evidence = accepted == 0 and rejected == 0 and diagnostic_candidates > 0
    target_key = f"{instance}:{game_map}:{query_port}" if query_port else f"{instance}:{game_map}"
    latest_rejected_drift_by_lifecycle_target = latest_rejected_drift_by_lifecycle_target or {}
    rejected_drift_target_counts = {
        target: 1 for target in latest_rejected_drift_by_lifecycle_target
    }
    rejected_drift_count = sum(rejected_drift_target_counts.values())
    event_triage = observer_event_triage(
        accepted=accepted,
        rejected=rejected,
        diagnostic_candidates=diagnostic_candidates,
        accepted_roles=accepted_roles,
    )
    return {
        "schema": "obelisk.player-principal-passive-snapshot.v1",
        "captured_at_utc": "2026-06-04T08:10:42Z",
        "target_count": 1,
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
        "evidence_classification": "passive_snapshot_non_evidence",
        "all_logs_copied": True,
        "non_claims": [
            "passive copied-log snapshot only",
            "approved_runtime_evidence remains false",
            "diagnostic candidate lines remain non-evidence until approved evidence checkers accept a copied sibling-set bundle",
        ],
        "passive_wait_metadata": {
            "schema": "obelisk.player-principal-passive-wait-metadata.v1",
            "wait_scope": "metadata_only",
            "observer_tail_scope": "per_target",
            "observer_tail_by_target": {
                target_key: {
                    "target_key": target_key,
                    "status": "matched" if diagnostic_candidates or accepted else "no_matching_lines",
                    "tail_scope": "per_target",
                    "linger_active": presence_detected,
                    "process_control": "none",
                    "approved_runtime_evidence": False,
                    "ready": False,
                    "readiness_gate": "none",
                }
            }
            if query_port
            else {},
            "observer_tail_by_alias": {},
            "linger_by_target": {
                target_key: [
                    {
                        "event": "player_presence_linger_start",
                        "target_keys": [target_key],
                        "process_control": "none",
                        "approved_runtime_evidence": False,
                        "ready": False,
                        "readiness_gate": "none",
                    }
                ]
            }
            if presence_detected and query_port
            else {},
            "linger_events": [],
            "process_control": "none",
            "approved_runtime_evidence": False,
            "ready": False,
            "readiness_gate": "none",
            "evidence_classification": "passive_wait_metadata_non_evidence",
        },
        "targets": [
            {
                "target_key": target_key,
                "instance": instance,
                "map": game_map,
                "query_port": query_port,
                "copy_status": "copied",
                "approved_runtime_evidence": False,
                "ready": False,
                "readiness_gate": "none",
                "counts": {
                    "accepted": accepted,
                    "rejected": rejected,
                    "diagnostic_candidates": diagnostic_candidates,
                },
                "diagnostics": {
                    "candidate_count": diagnostic_candidates,
                    "max_sequence": max_sequence,
                    "log_limits": [10] if diagnostic_candidates > 0 else [],
                    "log_budget_reached": log_budget_reached,
                    "only_non_evidence": diagnostic_only_non_evidence,
                    "latest_observer_line": latest_observer_line,
                    "classification": (
                        "diagnostic_only_non_evidence"
                        if diagnostic_only_non_evidence
                        else "passive_snapshot_non_evidence"
                    ),
                    "observer_event_triage": event_triage,
                    "accepted_observer_event_triplet_candidate_count": accepted,
                    "complete_observer_event_triplet_candidate_present": event_triage[
                        "complete_observer_event_triplet_candidate_present"
                    ],
                    "event_triplet_classification": event_triage["classification"],
                    "rejected_drift_count": rejected_drift_count,
                    "rejected_drift_target_counts": rejected_drift_target_counts,
                    "latest_rejected_drift_by_lifecycle_target": latest_rejected_drift_by_lifecycle_target,
                    "contains_rejected_drift": rejected_drift_count > 0,
                    "rejected_drift_evidence_classification": "diagnostic_rejected_drift_non_evidence",
                },
                "observer_event_triage": event_triage,
                "query_state": {
                    "target_key": target_key,
                    "target_key_kind": "exact" if query_port else "alias",
                    "instance": instance,
                    "map": game_map,
                    "query_port": query_port,
                    "status": "ok",
                    "current_map": game_map,
                    "players": f"{players_current}/70",
                    "players_current": players_current,
                    "players_max": 70,
                    "last_query_utc": "2026-06-04T08:10:42Z",
                    "presence_detected": presence_detected,
                    "last_presence_detected_utc": (
                        "2026-06-04T08:10:42Z" if presence_detected else None
                    ),
                },
                "diagnostic_only_non_evidence": diagnostic_only_non_evidence,
            }
        ],
    }


def run_summary(base: Path, candidate: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(base), str(candidate)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def run_latest(snapshot_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--latest", "--json", str(snapshot_root)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def run_latest_with_monitor(
    snapshot_root: Path,
    monitor_log: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--latest",
            "--json",
            "--monitor-log",
            str(monitor_log),
            str(snapshot_root),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def run_latest_diff(snapshot_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--latest-diff", "--json", str(snapshot_root)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def player_principal_event_line(role: str, sequence: int) -> str:
    timestamp = f"07:00:{sequence + 1:02d}"
    if role == "session_end":
        return (
            f"[{timestamp}] [warning] PlayerPrincipalLifecycleObserver event "
            f"sequence={sequence} role=session_end target=ShooterGameMode.OnLogout "
            "post_original=true copied_bool_fields= copied_bool_values= "
            "redacted_count=1 redacted_fields=Exiting "
            "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
    if role == "session_start_rejected":
        return (
            f"[{timestamp}] [warning] PlayerPrincipalLifecycleObserver event "
            f"sequence={sequence} role=session_start_rejected target=ShooterGameMode.CheckJoinInProgress "
            "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
            "copied_bool_values=1,0 redacted_count=1 "
            "redacted_fields=NewPlayer "
            "principal_action=none apply_status=session_start_rejected_noop "
            "correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
    return (
        f"[{timestamp}] [warning] PlayerPrincipalLifecycleObserver event "
        f"sequence={sequence} role={role} target=ShooterGameMode.HandleNewPlayer "
        "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
        "copied_bool_values=1,1 redacted_count=3 "
        "redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=candidate_created apply_status=session_start_created "
        "correlation_status=not_applicable principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none."
    )


def write_genesis2_monitor_only_log(
    path: Path,
    *,
    roles: list[str] | None = None,
    players_current: int = 0,
    diagnostic_only_lines: int = 0,
    ready_overclaim: bool = False,
) -> None:
    roles = roles or []
    role_text = ",".join(roles) if roles else "none"
    complete_triplet = all(role in roles for role in REQUIRED_OBSERVER_EVENT_ROLES)
    if complete_triplet:
        classification = "complete_accepted_observer_event_triplet_candidate_non_evidence"
    elif roles:
        classification = "partial_accepted_observer_event_triplet_candidate_non_evidence"
    elif diagnostic_only_lines:
        classification = "diagnostic_only_lines_non_evidence"
    else:
        classification = "no_player_principal_observer_lines_non_evidence"
    ready_value = "true" if ready_overclaim else "false"
    readiness_gate = "approved_runtime_bundle" if ready_overclaim else "none"
    path.write_text(
        "\n".join(
            [
                "passive_monitor_session utc=2026-06-06T05:10:57Z pid=3261082 "
                "ppid=1 session_id=genesis2-empty-root tmux_session=obelisk_passive_monitor "
                "tmux_pane=%1 targets=arkserver3:Genesis2:27017 target_count=1 "
                "interval=10 once=false linger_after_detect=900 "
                "snapshot_output_root=/tmp/snapshots snapshot_monitor_log=/tmp/monitor.log "
                "replacement_status=none_reported replaced_monitor_pid=none "
                "active_monitor_pid=none replacement_requested=false "
                "old_monitor_action=not_performed_by_passive_monitor replacement_note=none "
                "replacement_policy=never_signal_stop_or_replace_existing_monitor "
                "active_monitor_policy=metadata_only_never_signal_stop_or_replace "
                "process_control=none",
                "tick utc=2026-06-06T05:10:57Z",
                "query instance=arkserver3 map=Genesis2 query_port=27017 status=ok "
                f"current_map=Genesis2 players={players_current}/70 name=Genesis2 "
                "target_key=arkserver3:Genesis2:27017 "
                f"players_current={players_current} players_max=70 "
                f"presence_detected={str(players_current > 0).lower()} "
                "detection_source=gamedig_ase_query",
                "observer_tail instance=arkserver3 status=matched "
                f"lines={1 + len(roles) + diagnostic_only_lines} scan_lines=200 "
                "limit=10 map=Genesis2 query_port=27017 "
                "target_key=arkserver3:Genesis2:27017 observer_gate_lines=1 "
                f"accepted_observer_event_triplet_candidate_lines={len(roles)} "
                f"diagnostic_only_lines={diagnostic_only_lines} "
                f"event_roles={role_text} "
                f"complete_triplet_candidate={str(complete_triplet).lower()} "
                f"classification={classification} tail_scope=per_target "
                "process_control=none evidence_classification=passive_tail_non_evidence "
                f"approved_runtime_evidence={ready_value} ready={ready_value} "
                f"runtime_evidence_ready={ready_value} readiness_gate={readiness_gate}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def capture_genesis2_passive_fixture(
    tmp_path: Path,
    *,
    roles: list[str],
) -> tuple[subprocess.CompletedProcess[str], Path]:
    log_root = tmp_path / "logs"
    output_dir = tmp_path / "snapshot"
    monitor_log = tmp_path / "passive-monitor.log"
    instance_dir = log_root / "arkserver3"
    instance_dir.mkdir(parents=True)
    instance_dir.joinpath("Obelisk.log").write_text(
        "\n".join(
            [
                "[07:00:00] [info] Obelisk Runtime Loaded Native (LD_PRELOAD)",
                "[07:00:00] [warning] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 "
                "dispatch_limit=0 delivery_claim=none principal_claim=none.",
                *[
                    player_principal_event_line(role, sequence)
                    for sequence, role in enumerate(roles, start=1)
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    role_text = ",".join(roles) if roles else "none"
    complete_triplet = all(role in roles for role in REQUIRED_OBSERVER_EVENT_ROLES)
    monitor_log.write_text(
        "\n".join(
            [
                "passive_monitor_session utc=2026-06-04T16:00:00Z pid=3261082 "
                "ppid=1 session_id=genesis2-fixture tmux_session=obelisk_passive_monitor "
                "tmux_pane=%1 targets=arkserver3:Genesis2:27017 target_count=1 "
                "interval=10 once=true linger_after_detect=0 "
                "snapshot_output_root=/tmp/snapshots snapshot_monitor_log=/tmp/monitor.log "
                "replacement_status=none_reported replaced_monitor_pid=none "
                "active_monitor_pid=none replacement_requested=false "
                "old_monitor_action=not_performed_by_passive_monitor replacement_note=none "
                "replacement_policy=never_signal_stop_or_replace_existing_monitor "
                "active_monitor_policy=metadata_only_never_signal_stop_or_replace "
                "process_control=none",
                "tick utc=2026-06-04T16:00:05Z",
                "query instance=arkserver3 map=Genesis2 query_port=27017 status=ok "
                "current_map=Genesis2 players=1/70 name=Genesis2 "
                "target_key=arkserver3:Genesis2:27017 players_current=1 players_max=70 "
                "presence_detected=true detection_source=gamedig_ase_query",
                "observer_tail instance=arkserver3 status=matched "
                f"lines={len(roles) + 1} scan_lines=200 limit=10 map=Genesis2 "
                "query_port=27017 target_key=arkserver3:Genesis2:27017 "
                "observer_gate_lines=1 "
                f"accepted_observer_event_triplet_candidate_lines={len(roles)} "
                "diagnostic_only_lines=0 "
                f"event_roles={role_text} complete_triplet_candidate={str(complete_triplet).lower()} "
                f"classification={'complete_accepted_observer_event_triplet_candidate_non_evidence' if complete_triplet else 'partial_accepted_observer_event_triplet_candidate_non_evidence'} "
                "tail_scope=per_target process_control=none "
                "evidence_classification=passive_tail_non_evidence "
                "approved_runtime_evidence=false ready=false readiness_gate=none",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(CAPTURE_SCRIPT),
            "--log-root",
            str(log_root),
            "--output-dir",
            str(output_dir),
            "--monitor-log",
            str(monitor_log),
            "--target",
            "arkserver3:Genesis2:27017",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    return result, output_dir


class SummarizePassiveSnapshotTests(unittest.TestCase):
    def test_latest_monitor_only_empty_snapshot_root_reports_no_detections_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            snapshot_root = tmp_path / "snapshots"
            snapshot_root.mkdir()
            monitor_log = tmp_path / "monitor.log"
            write_genesis2_monitor_only_log(monitor_log)

            result = run_latest_with_monitor(snapshot_root, monitor_log)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            target_key = "arkserver3:Genesis2:27017"
            self.assertEqual(
                report["schema"],
                "obelisk.player-principal-passive-monitor-only-summary.v1",
            )
            self.assertEqual(report["snapshot_status"], "no_snapshots_found")
            self.assertEqual(report["snapshot_count"], 0)
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertFalse(report["route_ready"])
            activity = report["passive_monitor_activity_summary"]
            self.assertEqual(activity["snapshot_status"], "no_snapshots_found")
            self.assertEqual(
                activity["classification"],
                "no_snapshots_no_passive_detections_no_complete_triplets_non_evidence",
            )
            self.assertEqual(activity["observer_enabled_targets"], [target_key])
            self.assertEqual(activity["passive_detection_targets"], [])
            self.assertEqual(activity["complete_observer_event_triplet_targets"], [])
            self.assertEqual(activity["players_current_by_target"], {target_key: 0})
            self.assertFalse(activity["approved_runtime_evidence"])
            self.assertFalse(activity["ready"])
            closure = report["passive_closure_summary"]
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
                "zero_players_gate_only_no_progress_no_readiness_non_evidence",
            )
            self.assertEqual(
                closure["source_root_role"],
                "passive_monitor_root_operational_context_only",
            )
            self.assertEqual(closure["source_run_id"], "snapshots")
            self.assertTrue(closure["invalid_run_id_root"])
            self.assertFalse(closure["valid_closure_root"])
            self.assertFalse(closure["source_root_valid_for_closure"])
            self.assertFalse(closure["closure_root_valid_for_player_principal_lifecycle"])
            self.assertFalse(closure["runtime_evidence_ready"])
            self.assertEqual(closure["sdk_progress"], 0)
            self.assertEqual(closure["p0_progress"], 0)
            self.assertEqual(closure["zero_player_targets"], [target_key])
            self.assertEqual(closure["observer_gate_only_targets"], [target_key])
            self.assertIn("invalid_run_id_root_non_evidence", closure["closure_reasons"])
            self.assertIn("zero_players_non_evidence", closure["closure_reasons"])
            self.assertIn("observer_gate_only_non_evidence", closure["closure_reasons"])
            summary = report["passive_server_activity_summary"]
            self.assertEqual(summary["active_targets"], [target_key])
            self.assertFalse(summary["players_detected"])
            self.assertEqual(summary["players_current_by_target"], {target_key: 0})
            triplet = summary["player_principal_triplet_candidates_by_target"][target_key]
            self.assertEqual(triplet["roles_seen"], [])
            self.assertEqual(
                triplet["missing_roles"],
                ["session_start", "session_start_rejected", "session_end"],
            )
            self.assertFalse(triplet["complete_triplet_candidate"])
            self.assertFalse(triplet["approved_runtime_evidence"])
            self.assertFalse(triplet["ready"])

    def test_latest_monitor_only_corrects_superseded_rejected_start_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            snapshot_root = tmp_path / "snapshots"
            snapshot_root.mkdir()
            monitor_log = tmp_path / "monitor-theisland.log"
            target_key = "arkserver2:TheIsland:27016"
            observer_prefix = (
                "observer instance=arkserver2 map=TheIsland query_port=27016 "
                f"target_key={target_key} process_control=none "
                "evidence_classification=passive_tail_non_evidence "
                "approved_runtime_evidence=false ready=false readiness_gate=none "
            )
            monitor_log.write_text(
                "\n".join(
                    [
                        "passive_monitor_session utc=2026-06-04T05:00:00Z pid=3261082 "
                        f"ppid=1 session_id=test-session targets={target_key} target_count=1 "
                        "interval=10 once=true linger_after_detect=0 process_control=none",
                        "tick utc=2026-06-04T05:00:00Z",
                        "observer_tail instance=arkserver2 status=matched lines=5 scan_lines=200 "
                        "limit=10 map=TheIsland query_port=27016 "
                        f"target_key={target_key} observer_gate_lines=1 "
                        "accepted_observer_event_triplet_candidate_lines=3 diagnostic_only_lines=1 "
                        "event_roles=session_start,session_start_rejected,session_end "
                        "complete_triplet_candidate=true "
                        "classification=complete_accepted_observer_event_triplet_candidate_non_evidence "
                        "tail_scope=per_target process_control=none "
                        "evidence_classification=passive_tail_non_evidence "
                        "approved_runtime_evidence=false ready=false readiness_gate=none",
                        observer_prefix
                        + "[05:13:17] [warning] PlayerPrincipalLifecycleObserver enabled "
                        "binary_sha256=test target_set=players-lifecycle-anchor-candidates "
                        "limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.",
                        observer_prefix
                        + "[05:20:01] [warning] PlayerPrincipalLifecycleObserver event "
                        "sequence=1 role=session_start target=ShooterGameMode.HandleNewPlayer "
                        "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
                        "copied_bool_values=1,1 redacted_count=3 "
                        "redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                        "principal_action=candidate_created apply_status=session_start_created "
                        "correlation_status=not_applicable principal_id_logged=false "
                        "principal_generation_logged=false delivery_claim=none.",
                        observer_prefix
                        + "[05:20:02] [warning] PlayerPrincipalLifecycleObserver event "
                        "sequence=2 role=session_start_rejected target=ShooterGameMode.HandleNewPlayer "
                        "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
                        "copied_bool_values=0,1 redacted_count=3 "
                        "redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=none "
                        "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                        "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                        observer_prefix
                        + "[05:20:03] [info] PlayerPrincipalLifecycleDiagnostic candidate "
                        "sequence=3 target=ShooterGameMode.CheckJoinInProgress fname_index=1845 "
                        "post_original=true accepted_lifecycle_target=false reflection_status=matched "
                        "diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue "
                        "copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer "
                        "params_logged=false identity_logged=false evidence_claim=none.",
                        observer_prefix
                        + "[05:20:04] [warning] PlayerPrincipalLifecycleObserver event "
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

            result = run_latest_with_monitor(snapshot_root, monitor_log)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            tail = report["monitor"]["observer_tail_by_target"][target_key]
            self.assertEqual(tail["event_roles"], ["session_start", "session_end"])
            self.assertEqual(
                tail["raw_event_roles"],
                ["session_start", "session_start_rejected", "session_end"],
            )
            self.assertEqual(tail["accepted_observer_event_triplet_candidate_lines"], 2)
            self.assertEqual(tail["rejected_observer_event_line_count"], 1)
            self.assertEqual(tail["superseded_handle_new_player_rejected_start_lines"], 1)
            self.assertEqual(tail["diagnostic_only_lines"], 1)
            self.assertFalse(tail["complete_triplet_candidate"])
            triage = report["latest_observer_event_triage"]
            self.assertEqual(
                triage["accepted_observer_event_roles"],
                ["session_start", "session_end"],
            )
            self.assertEqual(triage["missing_observer_event_triplet_roles"], ["session_start_rejected"])
            self.assertFalse(triage["complete_observer_event_triplet_candidate_present"])
            self.assertEqual(
                triage["classification"],
                "partial_accepted_observer_event_triplet_candidate_non_evidence",
            )
            summary = report["passive_server_activity_summary"]
            triplet = summary["player_principal_triplet_candidates_by_target"][target_key]
            self.assertEqual(triplet["roles_seen"], ["session_start", "session_end"])
            self.assertFalse(triplet["complete_triplet_candidate"])
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])

    def test_latest_reports_newest_snapshot_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            older = tmp_path / "passive-detect-older" / "manifest.json"
            newer = tmp_path / "passive-detect-newer" / "manifest.json"
            older.parent.mkdir()
            newer.parent.mkdir()
            older.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            newer.write_text(json.dumps(passive_manifest(diagnostic_candidates=17)), encoding="utf-8")
            os.utime(older, (1_000_000_000, 1_000_000_000))
            os.utime(newer, (1_000_000_100, 1_000_000_100))

            result = run_latest(tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(
                report["schema"],
                "obelisk.player-principal-passive-snapshot-latest.v1",
            )
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertEqual(report["readiness_gate"], "none")
            self.assertEqual(report["latest"]["snapshot_id"], "passive-detect-newer")
            self.assertEqual(report["latest"]["counts"]["diagnostic_candidates"], 17)
            self.assertTrue(report["latest"]["diagnostics"]["log_budget_reached"])
            self.assertEqual(report["latest"]["passive_wait_metadata"]["process_control"], "none")
            self.assertIn(
                "arkserver:Ragnarok:27015",
                report["latest"]["passive_wait_metadata"]["observer_tail_by_target"],
            )
            self.assertEqual(
                report["latest_observer_event_triage"]["classification"],
                "diagnostic_only_lines_non_evidence",
            )
            self.assertFalse(report["latest_observer_event_triage"]["approved_runtime_evidence"])
            self.assertFalse(report["latest_observer_event_triage"]["ready"])
            self.assertEqual(report["latest_observer_event_triage"]["readiness_gate"], "none")
            self.assertFalse(
                report["latest_observer_event_triage"][
                    "contains_accepted_observer_event_triplet_candidates"
                ]
            )
            self.assertTrue(
                report["latest_observer_event_triage"]["contains_diagnostic_only_lines"]
            )
            closure = report["passive_closure_summary"]
            self.assertEqual(
                closure["closure_classification"],
                "diagnostic_only_observer_lines_no_progress_no_readiness_non_evidence",
            )
            self.assertEqual(closure["diagnostic_only_targets"], ["arkserver:Ragnarok:27015"])
            self.assertFalse(closure["runtime_evidence_ready"])
            self.assertEqual(closure["sdk_progress"], 0)
            self.assertEqual(closure["p0_progress"], 0)
            self.assertIn("diagnostic candidate deltas remain non-evidence", report["non_claims"])

    def test_latest_surfaces_complete_accepted_triplet_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            latest = tmp_path / "passive-detect-triplet" / "manifest.json"
            latest.parent.mkdir()
            latest.write_text(
                json.dumps(
                    passive_manifest(
                        diagnostic_candidates=0,
                        accepted=3,
                        accepted_roles=[
                            "session_start",
                            "session_start_rejected",
                            "session_end",
                        ],
                    )
                ),
                encoding="utf-8",
            )

            result = run_latest(tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            triage = report["latest_observer_event_triage"]
            self.assertEqual(
                triage["classification"],
                "complete_accepted_observer_event_triplet_candidate_non_evidence",
            )
            self.assertEqual(triage["accepted_observer_event_triplet_candidate_count"], 3)
            self.assertEqual(
                triage["accepted_observer_event_roles"],
                ["session_start", "session_start_rejected", "session_end"],
            )
            self.assertTrue(triage["complete_observer_event_triplet_candidate_present"])
            self.assertFalse(triage["approved_runtime_evidence"])
            self.assertFalse(triage["ready"])
            self.assertEqual(triage["readiness_gate"], "none")
            self.assertEqual(report["classification"], "passive_snapshot_non_evidence")

    def test_latest_complete_triplet_summary_remains_non_evidence_non_counting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            latest = tmp_path / "passive-detect-triplet-focused" / "manifest.json"
            latest.parent.mkdir()
            latest.write_text(
                json.dumps(
                    passive_manifest(
                        diagnostic_candidates=0,
                        accepted=3,
                        accepted_roles=[
                            "session_start",
                            "session_start_rejected",
                            "session_end",
                        ],
                        presence_detected=True,
                        players_current=1,
                    )
                ),
                encoding="utf-8",
            )

            result = run_latest(tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            target_key = "arkserver:Ragnarok:27015"
            summary = report["passive_server_activity_summary"]
            self.assertEqual(
                summary["targets_with_complete_player_principal_triplet_candidate"],
                [target_key],
            )
            triplet = summary["player_principal_triplet_candidates_by_target"][target_key]
            self.assertTrue(triplet["complete_triplet_candidate"])
            self.assertEqual(
                triplet["classification"],
                "complete_accepted_observer_event_triplet_candidate_non_evidence",
            )
            self.assertFalse(triplet["approved_runtime_evidence"])
            self.assertFalse(triplet["ready"])
            self.assertFalse(triplet["route_ready"])
            actionability = report["passive_actionability"]
            self.assertEqual(
                actionability["priority"],
                "accepted_observer_event_triplet_candidate",
            )
            self.assertEqual(actionability["process_control"], "none")
            self.assertFalse(actionability["approved_runtime_evidence"])
            self.assertFalse(actionability["ready"])
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertFalse(report["route_ready"])
            self.assertIn(
                "accepted observer event triplet candidates remain passive non-evidence until approved evidence checkers accept a copied sibling-set bundle",
                report["non_claims"],
            )

    def test_latest_reports_genesis2_partial_triplet_by_exact_target_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            capture_result, snapshot_root = capture_genesis2_passive_fixture(
                Path(tmp),
                roles=["session_start", "session_start_rejected"],
            )
            self.assertEqual(
                capture_result.returncode,
                0,
                capture_result.stderr + capture_result.stdout,
            )

            result = run_latest(snapshot_root)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            target_key = "arkserver3:Genesis2:27017"
            summary = report["passive_server_activity_summary"]
            triplet = summary["player_principal_triplet_candidates_by_target"][target_key]
            self.assertEqual(triplet["roles_seen"], ["session_start", "session_start_rejected"])
            self.assertEqual(triplet["missing_roles"], ["session_end"])
            self.assertFalse(triplet["complete_triplet_candidate"])
            self.assertEqual(
                triplet["last_event_times"],
                {
                    "session_start": "2026-06-04T16:00:05Z",
                    "session_start_rejected": "2026-06-04T16:00:05Z",
                },
            )
            self.assertFalse(triplet["approved_runtime_evidence"])
            self.assertFalse(triplet["ready"])
            self.assertFalse(triplet["route_ready"])
            self.assertEqual(triplet["readiness_gate"], "none")
            self.assertFalse(summary["approved_runtime_evidence"])
            self.assertFalse(summary["ready"])
            self.assertFalse(summary["route_ready"])
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertFalse(report["route_ready"])
            closure = report["passive_closure_summary"]
            self.assertEqual(
                closure["closure_classification"],
                "partial_observer_event_roles_no_progress_no_readiness_non_evidence",
            )
            self.assertEqual(closure["partial_observer_event_role_targets"], [target_key])
            self.assertEqual(
                closure["missing_observer_event_roles_by_target"],
                {target_key: ["session_end"]},
            )
            self.assertFalse(closure["valid_closure_root"])
            self.assertFalse(closure["runtime_evidence_ready"])
            self.assertEqual(closure["sdk_progress"], 0)
            self.assertEqual(closure["p0_progress"], 0)

    def test_latest_reports_genesis2_complete_triplet_candidate_by_exact_target_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            capture_result, snapshot_root = capture_genesis2_passive_fixture(
                Path(tmp),
                roles=["session_start", "session_start_rejected", "session_end"],
            )
            self.assertEqual(
                capture_result.returncode,
                0,
                capture_result.stderr + capture_result.stdout,
            )

            result = run_latest(snapshot_root)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            target_key = "arkserver3:Genesis2:27017"
            summary = report["passive_server_activity_summary"]
            triplet = summary["player_principal_triplet_candidates_by_target"][target_key]
            self.assertEqual(
                triplet["roles_seen"],
                ["session_start", "session_start_rejected", "session_end"],
            )
            self.assertEqual(triplet["missing_roles"], [])
            self.assertTrue(triplet["complete_triplet_candidate"])
            self.assertEqual(
                triplet["last_event_times"],
                {
                    "session_start": "2026-06-04T16:00:05Z",
                    "session_start_rejected": "2026-06-04T16:00:05Z",
                    "session_end": "2026-06-04T16:00:05Z",
                },
            )
            self.assertEqual(
                summary["targets_with_complete_player_principal_triplet_candidate"],
                [target_key],
            )
            self.assertFalse(triplet["approved_runtime_evidence"])
            self.assertFalse(triplet["ready"])
            self.assertFalse(triplet["route_ready"])
            self.assertEqual(triplet["readiness_gate"], "none")
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertFalse(report["route_ready"])

    def test_latest_actionability_prioritizes_accepted_triplet_over_rejected_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            latest = tmp_path / "passive-detect-triplet-and-drift" / "manifest.json"
            latest.parent.mkdir()
            latest.write_text(
                json.dumps(
                    passive_manifest(
                        diagnostic_candidates=1,
                        accepted=3,
                        accepted_roles=[
                            "session_start",
                            "session_start_rejected",
                            "session_end",
                        ],
                        presence_detected=True,
                        players_current=1,
                        latest_rejected_drift_by_lifecycle_target={
                            "ShooterGameMode.HandleNewPlayer": rejected_drift(
                                target="ShooterGameMode.HandleNewPlayer",
                                sequence=8,
                                fname_index=1773,
                            )
                        },
                    )
                ),
                encoding="utf-8",
            )

            result = run_latest(tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            actionability = report["passive_actionability"]
            self.assertEqual(
                actionability["schema"],
                "obelisk.player-principal-passive-actionability.v1",
            )
            self.assertEqual(
                actionability["priority"],
                "accepted_observer_event_triplet_candidate",
            )
            self.assertEqual(actionability["runner_priority_rank"], 10)
            self.assertEqual(
                actionability["runner_focus"],
                "complete_triplet_candidate_request_preflight",
            )
            self.assertEqual(
                actionability["reason_kind"],
                "complete_accepted_observer_event_triplet_candidate_present",
            )
            self.assertEqual(
                actionability["next_reason"],
                "complete_accepted_observer_event_triplet_candidate_present_non_evidence",
            )
            self.assertEqual(actionability["targets"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                actionability["targets_with_players_detected"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(
                actionability["complete_observer_event_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(actionability["process_control"], "none")
            self.assertFalse(actionability["approved_runtime_evidence"])
            self.assertFalse(actionability["ready"])
            self.assertEqual(actionability["readiness_gate"], "none")
            runner_hint = actionability["runner_action_hints"][0]
            self.assertEqual(
                runner_hint["schema"],
                "obelisk.player-principal-passive-runner-action-hint.v1",
            )
            self.assertEqual(runner_hint["order"], 1)
            self.assertEqual(
                runner_hint["id"],
                "prepare_fresh_operator_approved_evidence_request_from_triplet_candidate",
            )
            self.assertEqual(runner_hint["target_keys"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                runner_hint["complete_observer_event_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(runner_hint["process_control"], "none")
            self.assertFalse(runner_hint["approved_runtime_evidence"])
            self.assertFalse(runner_hint["ready"])
            self.assertEqual(
                actionability["evidence_classification"],
                "passive_actionability_non_evidence",
            )

    def test_latest_surfaces_dual_server_activity_summary_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            latest = tmp_path / "passive-detect-dual-active" / "manifest.json"
            latest.parent.mkdir()
            manifest = passive_manifest(
                diagnostic_candidates=1,
                max_sequence=6,
                presence_detected=True,
                players_current=2,
                latest_rejected_drift_by_lifecycle_target={
                    "ShooterGameMode.HandleNewPlayer": rejected_drift(
                        target="ShooterGameMode.HandleNewPlayer",
                        timestamp_prefix="15:02:31",
                        sequence=6,
                        fname_index=1773,
                    )
                },
            )
            second = passive_manifest(
                diagnostic_candidates=1,
                max_sequence=7,
                presence_detected=True,
                players_current=1,
                instance="arkserver2",
                game_map="TheIsland",
                query_port="27016",
                latest_rejected_drift_by_lifecycle_target={
                    "ShooterGameMode.OnLogout": rejected_drift()
                },
            )["targets"][0]
            manifest["targets"].append(second)
            manifest["target_count"] = 2
            latest.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_latest(tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            summary = report["passive_server_activity_summary"]
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
            self.assertEqual(summary["players_current_known_total"], 3)
            self.assertEqual(
                summary["players_current_by_target"],
                {
                    "arkserver:Ragnarok:27015": 2,
                    "arkserver2:TheIsland:27016": 1,
                },
            )
            self.assertEqual(
                summary["targets_with_players_detected"],
                ["arkserver2:TheIsland:27016", "arkserver:Ragnarok:27015"],
            )
            handle_reason = summary["latest_rejected_drift_reason_by_lifecycle_target"][
                "ShooterGameMode.HandleNewPlayer"
            ]["arkserver:Ragnarok:27015"]
            logout_reason = summary["latest_rejected_drift_reason_by_lifecycle_target"][
                "ShooterGameMode.OnLogout"
            ]["arkserver2:TheIsland:27016"]
            self.assertEqual(handle_reason["target"], "ShooterGameMode.HandleNewPlayer")
            self.assertEqual(handle_reason["reason_kind"], "lifecycle_property_FName_drift")
            self.assertFalse(handle_reason["approved_runtime_evidence"])
            self.assertEqual(handle_reason["process_control"], "none")
            self.assertEqual(logout_reason["target"], "ShooterGameMode.OnLogout")
            self.assertEqual(logout_reason["reason_kind"], "lifecycle_property_FName_drift")
            self.assertEqual(
                report["latest"]["passive_server_activity_summary"]["players_current_known_total"],
                3,
            )
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

    def test_latest_rejects_empty_snapshot_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_latest(Path(tmp))

            self.assertEqual(result.returncode, 2)
            self.assertIn("contains no manifest.json", result.stderr)

    def test_latest_rejects_forged_passive_snapshot_ready_progress_and_closure_root_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            latest = tmp_path / "passive-detect-forged" / "manifest.json"
            latest.parent.mkdir()
            manifest = passive_manifest(diagnostic_candidates=0)
            manifest["runtime_evidence_ready"] = True
            manifest["targets"][0]["sdk_progress"] = 1
            manifest["passive_closure_summary"] = {
                "schema": "obelisk.player-principal-passive-closure-summary.v1",
                "runtime_evidence_ready": True,
                "valid_closure_root": True,
                "source_root_valid_for_closure": True,
                "sdk_progress": 1,
                "p0_progress": 1,
                "approved_runtime_evidence": False,
                "ready": False,
                "route_ready": False,
                "readiness_gate": "none",
                "evidence_classification": "passive_closure_non_evidence",
                "process_control": "none",
            }
            latest.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_latest(tmp_path)

            self.assertEqual(result.returncode, 2)
            self.assertIn("forbidden_passive_claim:$.runtime_evidence_ready", result.stderr)
            self.assertIn(
                "forbidden_passive_progress_claim:$.targets[0].sdk_progress",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_claim:$.passive_closure_summary.runtime_evidence_ready",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_claim:$.passive_closure_summary.valid_closure_root",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_claim:$.passive_closure_summary.source_root_valid_for_closure",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_progress_claim:$.passive_closure_summary.sdk_progress",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_progress_claim:$.passive_closure_summary.p0_progress",
                result.stderr,
            )

    def test_latest_diff_compares_two_newest_snapshots_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            oldest = tmp_path / "passive-detect-oldest" / "manifest.json"
            older = tmp_path / "passive-detect-older" / "manifest.json"
            newest = tmp_path / "passive-detect-newest" / "manifest.json"
            for path in (oldest, older, newest):
                path.parent.mkdir()
            oldest.write_text(json.dumps(passive_manifest(diagnostic_candidates=1)), encoding="utf-8")
            older.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            newest.write_text(json.dumps(passive_manifest(diagnostic_candidates=9)), encoding="utf-8")
            os.utime(oldest, (1_000_000_000, 1_000_000_000))
            os.utime(older, (1_000_000_100, 1_000_000_100))
            os.utime(newest, (1_000_000_200, 1_000_000_200))

            result = run_latest_diff(tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(report["schema"], "obelisk.player-principal-passive-snapshot-diff.v1")
            self.assertTrue(report["auto_selected_latest_diff"])
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertEqual(report["base"]["snapshot_id"], "passive-detect-older")
            self.assertEqual(report["candidate"]["snapshot_id"], "passive-detect-newest")
            self.assertEqual(report["global_delta"]["diagnostic_candidates"], 6)
            self.assertEqual(report["global_delta"]["accepted"], 0)
            self.assertEqual(report["global_delta"]["rejected"], 0)
            self.assertEqual(report["classification"], "diagnostic_only_non_evidence")
            self.assertEqual(
                report["candidate_observer_event_triage"]["classification"],
                "diagnostic_only_lines_non_evidence",
            )

    def test_latest_diff_actionability_surfaces_unchanged_rejected_fname_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "passive-detect-base" / "manifest.json"
            candidate = tmp_path / "passive-detect-candidate" / "manifest.json"
            base.parent.mkdir()
            candidate.parent.mkdir()
            manifest = passive_manifest(
                diagnostic_candidates=1,
                max_sequence=7,
                presence_detected=True,
                players_current=1,
                latest_rejected_drift_by_lifecycle_target={
                    "ShooterGameMode.OnLogout": rejected_drift()
                },
            )
            base.write_text(json.dumps(manifest), encoding="utf-8")
            candidate.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], "unchanged_non_evidence")
            self.assertEqual(report["global_delta"]["diagnostic_candidates"], 0)
            actionability = report["passive_actionability"]
            self.assertEqual(
                actionability["priority"],
                "rejected_lifecycle_property_FName_drift",
            )
            self.assertEqual(
                actionability["reason_kind"],
                "repeated_lifecycle_property_FName_drift_unchanged",
            )
            self.assertEqual(
                actionability["next_reason"],
                "repeated_lifecycle_property_FName_drift_unchanged_non_evidence",
            )
            self.assertEqual(actionability["runner_priority_rank"], 20)
            self.assertEqual(
                actionability["runner_focus"],
                "rejected_lifecycle_property_fname_drift",
            )
            self.assertEqual(actionability["classification_context"], "unchanged_non_evidence")
            self.assertEqual(actionability["targets"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                actionability["targets_with_players_detected"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(
                actionability["lifecycle_targets"],
                ["ShooterGameMode.OnLogout"],
            )
            self.assertEqual(actionability["process_control"], "none")
            self.assertFalse(actionability["approved_runtime_evidence"])
            self.assertFalse(actionability["ready"])
            self.assertEqual(actionability["readiness_gate"], "none")
            self.assertEqual(
                actionability["forbidden_followup_scope"],
                "no_process_control_no_linuxgsm_monitor_details_no_evidence_claims",
            )
            runner_hint = actionability["runner_action_hints"][0]
            self.assertEqual(
                runner_hint["id"],
                "carry_rejected_fname_drift_to_offline_reflection_review",
            )
            self.assertEqual(runner_hint["target_keys"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                runner_hint["lifecycle_targets"],
                ["ShooterGameMode.OnLogout"],
            )
            self.assertEqual(runner_hint["process_control"], "none")
            self.assertFalse(runner_hint["approved_runtime_evidence"])
            self.assertFalse(runner_hint["ready"])

    def test_latest_diff_actionability_reports_repeated_diagnostics_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "passive-detect-base" / "manifest.json"
            candidate = tmp_path / "passive-detect-candidate" / "manifest.json"
            base.parent.mkdir()
            candidate.parent.mkdir()
            manifest = passive_manifest(diagnostic_candidates=9, max_sequence=9)
            base.write_text(json.dumps(manifest), encoding="utf-8")
            candidate.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(report["classification"], "unchanged_non_evidence")
            actionability = report["passive_actionability"]
            self.assertEqual(actionability["priority"], "repeated_diagnostics_only")
            self.assertEqual(
                actionability["reason_kind"],
                "repeated_diagnostic_candidates_unchanged",
            )
            self.assertEqual(
                actionability["next_reason"],
                "repeated_diagnostic_candidates_without_accepted_events_or_rejected_drift_unchanged_non_evidence",
            )
            self.assertEqual(actionability["targets"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                actionability["diagnostic_only_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(actionability["process_control"], "none")
            self.assertFalse(actionability["approved_runtime_evidence"])
            self.assertFalse(actionability["ready"])
            self.assertEqual(actionability["readiness_gate"], "none")

    def test_latest_diff_rejects_single_snapshot_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            only = Path(tmp) / "passive-detect-only" / "manifest.json"
            only.parent.mkdir()
            only.write_text(json.dumps(passive_manifest(diagnostic_candidates=1)), encoding="utf-8")

            result = run_latest_diff(Path(tmp))

            self.assertEqual(result.returncode, 2)
            self.assertIn("requires at least two manifest.json", result.stderr)

    def test_reports_diagnostic_only_delta_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "passive-detect-base" / "manifest.json"
            candidate = tmp_path / "passive-detect-candidate" / "manifest.json"
            base.parent.mkdir()
            candidate.parent.mkdir()
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(passive_manifest(diagnostic_candidates=9)), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(report["schema"], "obelisk.player-principal-passive-snapshot-diff.v1")
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertTrue(report["all_deltas_diagnostic_only"])
            self.assertEqual(report["classification"], "diagnostic_only_non_evidence")
            self.assertEqual(report["global_delta"]["accepted"], 0)
            self.assertEqual(report["global_delta"]["rejected"], 0)
            self.assertEqual(report["global_delta"]["diagnostic_candidates"], 6)
            self.assertEqual(report["global_diagnostics"]["base_max_sequence"], 3)
            self.assertEqual(report["global_diagnostics"]["candidate_max_sequence"], 9)
            self.assertEqual(report["global_diagnostics"]["max_sequence_delta"], 6)
            self.assertFalse(report["global_diagnostics"]["candidate_log_budget_reached"])
            self.assertEqual(report["global_diagnostics"]["diagnostic_only_non_evidence_targets"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(report["target_deltas"][0]["target"], "arkserver:Ragnarok:27015")
            self.assertEqual(report["target_deltas"][0]["classification"], "diagnostic_only_non_evidence")
            self.assertEqual(report["target_deltas"][0]["diagnostics"]["base_max_sequence"], 3)
            self.assertEqual(report["target_deltas"][0]["diagnostics"]["candidate_max_sequence"], 9)
            self.assertEqual(report["target_deltas"][0]["diagnostics"]["max_sequence_delta"], 6)
            self.assertFalse(report["target_deltas"][0]["diagnostics"]["candidate_log_budget_reached"])
            self.assertTrue(report["target_deltas"][0]["diagnostics"]["diagnostic_only_non_evidence"])
            self.assertIn("diagnostic candidate deltas remain non-evidence", report["non_claims"])

    def test_reports_accepted_triplet_delta_as_unapproved_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "passive-detect-base" / "manifest.json"
            candidate = tmp_path / "passive-detect-candidate" / "manifest.json"
            base.parent.mkdir()
            candidate.parent.mkdir()
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=0)), encoding="utf-8")
            candidate.write_text(
                json.dumps(
                    passive_manifest(
                        diagnostic_candidates=0,
                        accepted=3,
                        accepted_roles=[
                            "session_start",
                            "session_start_rejected",
                            "session_end",
                        ],
                        presence_detected=True,
                        players_current=1,
                    )
                ),
                encoding="utf-8",
            )

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertEqual(report["readiness_gate"], "none")
            self.assertFalse(report["all_deltas_diagnostic_only"])
            self.assertEqual(
                report["classification"],
                "accepted_observer_event_triplet_candidate_delta_non_evidence_unapproved",
            )
            candidate_triage = report["candidate_observer_event_triage"]
            self.assertEqual(
                candidate_triage["classification"],
                "complete_accepted_observer_event_triplet_candidate_non_evidence",
            )
            self.assertTrue(
                candidate_triage["complete_observer_event_triplet_candidate_present"]
            )
            self.assertFalse(candidate_triage["approved_runtime_evidence"])
            self.assertFalse(candidate_triage["ready"])
            target_delta = report["target_deltas"][0]
            self.assertEqual(
                target_delta["classification"],
                "accepted_observer_event_triplet_candidate_delta_non_evidence_unapproved",
            )
            self.assertEqual(
                target_delta["diagnostics"][
                    "accepted_observer_event_triplet_candidate_delta"
                ],
                3,
            )
            self.assertTrue(
                target_delta["diagnostics"][
                    "candidate_complete_observer_event_triplet_candidate_present"
                ]
            )
            triage = report["passive_activity_triage"]
            self.assertEqual(
                triage[
                    "candidate_targets_with_complete_observer_event_triplet_candidate"
                ],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(
                triage[
                    "targets_with_presence_and_accepted_observer_event_triplet_candidates"
                ],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertFalse(triage["approved_runtime_evidence"])
            self.assertFalse(triage["ready"])

    def test_reports_passive_activity_triage_for_new_presence_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "passive-detect-base" / "manifest.json"
            candidate = tmp_path / "passive-detect-candidate" / "manifest.json"
            latest_observer_line = {
                "source_index": 0,
                "line_number": 84,
                "timestamp_prefix": "08:55:01",
                "kind": "diagnostic_candidate",
            }
            base.parent.mkdir()
            candidate.parent.mkdir()
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=0)), encoding="utf-8")
            candidate.write_text(
                json.dumps(
                    passive_manifest(
                        diagnostic_candidates=4,
                        max_sequence=4,
                        presence_detected=True,
                        players_current=2,
                        latest_observer_line=latest_observer_line,
                    )
                ),
                encoding="utf-8",
            )

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            triage = report["passive_activity_triage"]
            self.assertEqual(
                triage["schema"],
                "obelisk.player-principal-passive-activity-triage.v1",
            )
            self.assertEqual(triage["query_state_key"], "target_key")
            self.assertEqual(triage["classification"], "passive_activity_triage_non_evidence")
            self.assertFalse(triage["approved_runtime_evidence"])
            self.assertFalse(triage["ready"])
            self.assertEqual(triage["readiness_gate"], "none")
            self.assertEqual(triage["active_targets"], ["arkserver:Ragnarok:27015"])
            self.assertEqual(
                triage["new_presence_detected_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(
                triage["new_diagnostic_candidate_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(
                triage["max_sequence_advanced_targets"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(
                triage["targets_with_presence_and_new_diagnostics"],
                ["arkserver:Ragnarok:27015"],
            )
            self.assertEqual(
                triage["new_diagnostic_candidates_by_target"],
                {"arkserver:Ragnarok:27015": 4},
            )
            self.assertEqual(
                triage["max_sequence_delta_by_target"],
                {"arkserver:Ragnarok:27015": None},
            )
            self.assertEqual(
                triage["candidate_players_current_by_target"],
                {"arkserver:Ragnarok:27015": 2},
            )
            self.assertEqual(
                triage["candidate_latest_observer_lines_by_new_diagnostic_target"][
                    "arkserver:Ragnarok:27015"
                ]["kind"],
                "diagnostic_candidate",
            )
            self.assertIn(
                "passive activity triage fields remain non-evidence diagnostic pointers only",
                report["non_claims"],
            )

    def test_reports_theisland_onlogout_rejected_drift_after_presence_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base" / "manifest.json"
            candidate = tmp_path / "candidate" / "manifest.json"
            base.parent.mkdir()
            candidate.parent.mkdir()
            base.write_text(
                json.dumps(
                    passive_manifest(
                        diagnostic_candidates=0,
                        instance="arkserver2",
                        game_map="TheIsland",
                        query_port="27016",
                    )
                ),
                encoding="utf-8",
            )
            candidate.write_text(
                json.dumps(
                    passive_manifest(
                        diagnostic_candidates=1,
                        max_sequence=7,
                        presence_detected=True,
                        players_current=1,
                        latest_observer_line={
                            "source_index": 0,
                            "line_number": 84,
                            "timestamp_prefix": "15:03:37",
                            "kind": "diagnostic_candidate",
                        },
                        instance="arkserver2",
                        game_map="TheIsland",
                        query_port="27016",
                        latest_rejected_drift_by_lifecycle_target={
                            "ShooterGameMode.OnLogout": rejected_drift()
                        },
                    )
                ),
                encoding="utf-8",
            )

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            target_key = "arkserver2:TheIsland:27016"
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertEqual(report["readiness_gate"], "none")
            self.assertEqual(report["global_delta"]["accepted"], 0)
            self.assertEqual(report["global_delta"]["rejected"], 0)
            self.assertEqual(report["global_delta"]["diagnostic_candidates"], 1)
            self.assertEqual(report["classification"], "diagnostic_only_non_evidence")
            self.assertEqual(
                report["candidate"]["diagnostics"]["rejected_drift_targets"],
                [target_key],
            )
            drift = report["candidate"]["diagnostics"][
                "latest_rejected_drift_by_snapshot_target"
            ][target_key]["ShooterGameMode.OnLogout"]
            self.assertEqual(drift["timestamp_prefix"], "15:03:37")
            self.assertEqual(drift["target"], "ShooterGameMode.OnLogout")
            self.assertEqual(drift["reflection_status"], "rejected")
            self.assertEqual(drift["evidence_claim"], "none")
            self.assertFalse(drift["approved_runtime_evidence"])
            self.assertFalse(drift["ready"])
            self.assertEqual(drift["readiness_gate"], "none")
            target_delta = report["target_deltas"][0]
            self.assertEqual(target_delta["target"], target_key)
            self.assertEqual(target_delta["diagnostics"]["candidate_rejected_drift_count"], 1)
            self.assertFalse(
                target_delta["diagnostics"]["candidate_observer_event_triage"][
                    "complete_observer_event_triplet_candidate_present"
                ]
            )
            triage = report["passive_activity_triage"]
            self.assertEqual(triage["active_targets"], [target_key])
            self.assertEqual(triage["new_presence_detected_targets"], [target_key])
            self.assertEqual(triage["candidate_targets_with_rejected_drift"], [target_key])
            self.assertEqual(triage["targets_with_presence_and_rejected_drift"], [target_key])
            self.assertEqual(
                triage["candidate_latest_rejected_drift_by_target"][target_key][
                    "ShooterGameMode.OnLogout"
                ]["timestamp_prefix"],
                "15:03:37",
            )
            self.assertFalse(triage["approved_runtime_evidence"])
            self.assertFalse(triage["ready"])
            self.assertEqual(triage["readiness_gate"], "none")
            activity_summary = report["candidate_passive_server_activity_summary"]
            self.assertFalse(activity_summary["approved_runtime_evidence"])
            self.assertFalse(activity_summary["ready"])
            self.assertEqual(activity_summary["readiness_gate"], "none")
            self.assertEqual(activity_summary["process_control"], "none")
            self.assertFalse(activity_summary["both_servers_active"])
            self.assertTrue(activity_summary["players_detected"])
            self.assertEqual(activity_summary["players_current_known_total"], 1)
            self.assertEqual(
                activity_summary["latest_rejected_drift_reason_by_lifecycle_target"][
                    "ShooterGameMode.OnLogout"
                ][target_key]["reason_kind"],
                "lifecycle_property_FName_drift",
            )

    def test_reports_candidate_diagnostic_budget_pressure_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base" / "manifest.json"
            candidate = tmp_path / "candidate" / "manifest.json"
            base.parent.mkdir()
            candidate.parent.mkdir()
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=9)), encoding="utf-8")
            candidate.write_text(
                json.dumps(passive_manifest(diagnostic_candidates=17, max_sequence=17)),
                encoding="utf-8",
            )

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertEqual(report["readiness_gate"], "none")
            self.assertEqual(report["classification"], "diagnostic_only_non_evidence")
            self.assertEqual(report["global_delta"]["diagnostic_candidates"], 8)
            self.assertEqual(report["global_diagnostics"]["candidate_max_sequence"], 17)
            self.assertEqual(report["global_diagnostics"]["max_sequence_delta"], 8)
            self.assertTrue(report["global_diagnostics"]["candidate_log_budget_reached"])
            self.assertTrue(report["target_deltas"][0]["diagnostics"]["candidate_log_budget_reached"])

    def test_uses_nested_analyzer_diagnostics_when_manifest_diagnostics_are_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base" / "manifest.json"
            candidate = tmp_path / "candidate" / "manifest.json"
            base.parent.mkdir()
            candidate.parent.mkdir()
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate_manifest = passive_manifest(diagnostic_candidates=17)
            target = candidate_manifest["targets"][0]
            target["diagnostics"] = {
                "candidate_count": 17,
                "max_sequence": None,
                "log_limits": [],
                "log_budget_reached": False,
                "only_non_evidence": True,
                "classification": "diagnostic_only_non_evidence",
            }
            target["query_state"] = {
                "instance": "arkserver",
                "map": "Ragnarok",
                "query_port": "27015",
                "status": "ok",
                "current_map": "Ragnarok",
                "players": "1/70",
                "players_current": 1,
                "players_max": 70,
                "last_query_utc": "2026-06-04T08:47:05Z",
                "presence_detected": True,
                "last_presence_detected_utc": "2026-06-04T08:47:05Z",
            }
            target["analyzer"] = {
                "summary": {
                    "modules": {
                        "player_principal_lifecycle": {
                            "accepted_count": 0,
                            "rejected_count": 0,
                            "diagnostic_candidate_count": 17,
                            "diagnostic_candidate_max_sequence": 10,
                            "diagnostic_log_limits": [10],
                            "diagnostic_log_budget_reached": True,
                            "diagnostic_only_non_evidence": True,
                            "latest_observer_line": {
                                "source_index": 0,
                                "line_number": 42,
                                "timestamp_prefix": "08:47:05",
                                "kind": "diagnostic_candidate",
                            },
                        }
                    }
                }
            }
            candidate_manifest["query_state_by_instance"] = {
                "arkserver": target["query_state"],
            }
            candidate.write_text(json.dumps(candidate_manifest), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertEqual(report["candidate"]["diagnostics"]["candidate_count"], 17)
            self.assertEqual(report["candidate"]["diagnostics"]["max_sequence"], 10)
            self.assertEqual(report["candidate"]["diagnostics"]["log_limits"], [10])
            self.assertTrue(report["candidate"]["diagnostics"]["log_budget_reached"])
            self.assertEqual(report["global_diagnostics"]["candidate_max_sequence"], 10)
            self.assertTrue(report["global_diagnostics"]["candidate_log_budget_reached"])
            self.assertEqual(
                report["target_deltas"][0]["diagnostics"]["candidate_latest_observer_line"][
                    "line_number"
                ],
                42,
            )
            self.assertEqual(
                report["target_deltas"][0]["query_state"]["candidate"]["players_current"],
                1,
            )
            self.assertTrue(
                report["candidate"]["query_state_by_target"]["arkserver:Ragnarok:27015"][
                    "presence_detected"
                ]
            )
            self.assertEqual(report["classification"], "diagnostic_only_non_evidence")

    def test_alias_query_state_presence_is_metadata_only_not_activity_triage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base" / "manifest.json"
            candidate = tmp_path / "candidate" / "manifest.json"
            base.parent.mkdir()
            candidate.parent.mkdir()
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=0)), encoding="utf-8")
            candidate_manifest = passive_manifest(diagnostic_candidates=4)
            target = candidate_manifest["targets"][0]
            alias_state = {
                "target_key": "arkserver:Ragnarok",
                "target_key_kind": "alias",
                "alias_target_key": "arkserver:Ragnarok",
                "exact_target_key": "arkserver:Ragnarok:27015",
                "instance": "arkserver",
                "map": "Ragnarok",
                "query_port": "",
                "status": "alias_presence_detected_without_exact_query_state_metadata_only",
                "players_current": 1,
                "players_max": 70,
                "presence_detected": True,
                "last_presence_detected_utc": "2026-06-04T11:30:21Z",
                "approved_runtime_evidence": False,
                "ready": False,
            }
            target["query_state"] = alias_state
            candidate_manifest["query_state_by_target"] = {"arkserver:Ragnarok": alias_state}
            candidate_manifest["query_state_by_alias"] = {"arkserver:Ragnarok": alias_state}
            candidate.write_text(json.dumps(candidate_manifest), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            triage = report["passive_activity_triage"]
            self.assertEqual(triage["active_targets"], [])
            self.assertEqual(triage["new_presence_detected_targets"], [])
            self.assertEqual(triage["targets_with_presence_and_new_diagnostics"], [])
            self.assertEqual(report["candidate"]["query_state_by_target"]["arkserver:Ragnarok:27015"]["status"], "not_reported")
            self.assertFalse(
                report["candidate"]["query_state_by_target"]["arkserver:Ragnarok:27015"][
                    "presence_detected"
                ]
            )
            self.assertEqual(
                report["candidate"]["query_state_by_alias_metadata_only"]["arkserver:Ragnarok"][
                    "evidence_classification"
                ],
                "passive_alias_presence_metadata_non_evidence",
            )
            self.assertFalse(report["candidate"]["approved_runtime_evidence"])
            self.assertFalse(report["candidate"]["ready"])

    def test_latest_legacy_blank_port_alias_stays_out_of_query_state_by_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            latest = tmp_path / "passive-detect-legacy-alias" / "manifest.json"
            latest.parent.mkdir()
            manifest = passive_manifest(diagnostic_candidates=4)
            target = manifest["targets"][0]
            alias_state = {
                "target_key": "arkserver:Ragnarok",
                "instance": "arkserver",
                "map": "Ragnarok",
                "query_port": "",
                "status": "presence_detected_without_query_state",
                "players_current": 1,
                "players_max": 70,
                "presence_detected": True,
                "last_presence_detected_utc": "2026-06-04T11:30:21Z",
                "approved_runtime_evidence": False,
                "ready": False,
            }
            target["query_port"] = ""
            target["target_key"] = "arkserver:Ragnarok"
            target["query_state"] = alias_state
            manifest["query_state_by_target"] = {"arkserver:Ragnarok": alias_state}
            latest.write_text(json.dumps(manifest), encoding="utf-8")

            result = run_latest(tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertNotIn("arkserver:Ragnarok", report["latest"]["query_state_by_target"])
            self.assertEqual(report["latest"]["query_state_by_target"], {})
            self.assertIn(
                "arkserver:Ragnarok",
                report["latest"]["query_state_by_alias_metadata_only"],
            )
            self.assertFalse(
                report["latest"]["query_state_by_alias_metadata_only"]["arkserver:Ragnarok"][
                    "query_presence_eligible"
                ]
            )
            self.assertEqual(
                report["latest"]["query_state_by_alias_metadata_only"]["arkserver:Ragnarok"][
                    "evidence_classification"
                ],
                "passive_alias_presence_metadata_non_evidence",
            )

    def test_rejects_manifest_that_claims_approved_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["approved_runtime_evidence"] = True
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn("approved_runtime_evidence_not_false", result.stderr)

    def test_rejects_target_readiness_gate_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["targets"][0]["readiness_gate"] = "approved_runtime_bundle"
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn("target_0_readiness_gate_not_none", result.stderr)

    def test_rejects_nested_observer_triage_approval_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["targets"][0]["observer_event_triage"]["approved_runtime_evidence"] = True
            bad["targets"][0]["diagnostics"]["observer_event_triage"][
                "readiness_gate"
            ] = "approved_runtime_bundle"
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "target_0_observer_event_triage_approved_runtime_evidence_not_false",
                result.stderr,
            )
            self.assertIn(
                "target_0_diagnostics_observer_event_triage_readiness_gate_not_none",
                result.stderr,
            )

    def test_rejects_deep_nested_latest_observer_line_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            latest_observer_line = {
                "source_index": 0,
                "line_number": 84,
                "timestamp_prefix": "08:55:01",
                "kind": "diagnostic_candidate",
                "claim": {
                    "approved_runtime_evidence": True,
                    "counts_toward_sdk": True,
                    "complete_sdk_progress_contribution": 1,
                },
            }
            bad["targets"][0]["diagnostics"]["latest_observer_line"] = latest_observer_line
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].diagnostics.latest_observer_line.claim.approved_runtime_evidence",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].diagnostics.latest_observer_line.claim.counts_toward_sdk",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_progress_claim:$.targets[0].diagnostics.latest_observer_line.claim.complete_sdk_progress_contribution",
                result.stderr,
            )

    def test_rejects_deep_nested_query_state_authorization_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["targets"][0]["query_state"]["followup"] = {
                "server_operations_authorized": True,
                "runtime_capture_authorized": True,
                "readiness_gate": "approved_runtime_bundle",
                "process_control": "restart",
            }
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].query_state.followup.server_operations_authorized",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].query_state.followup.runtime_capture_authorized",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_readiness_gate:$.targets[0].query_state.followup.readiness_gate",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_process_control:$.targets[0].query_state.followup.process_control",
                result.stderr,
            )

    def test_rejects_camelcase_passive_authorization_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["targets"][0]["query_state"]["followup"] = {
                "serverOperationsAuthorized": True,
                "runtimeCaptureAuthorized": True,
                "readinessGate": "approved_runtime_bundle",
                "processControl": "restart",
            }
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].query_state.followup.serverOperationsAuthorized",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].query_state.followup.runtimeCaptureAuthorized",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_readiness_gate:$.targets[0].query_state.followup.readinessGate",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_process_control:$.targets[0].query_state.followup.processControl",
                result.stderr,
            )

    def test_rejects_split_passive_claim_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["targets"][0]["diagnostics"]["latest_observer_line"] = {
                "claim_rows": [
                    {"field": "publicSdkReady", "state": "ready"},
                    {"name": "completeSdkProgressContribution", "value": 1},
                ]
            }
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].diagnostics.latest_observer_line.claim_rows[0]",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_progress_claim:$.targets[0].diagnostics.latest_observer_line.claim_rows[1]",
                result.stderr,
            )

    def test_rejects_source_overclaim_ready_aliases_and_normalizes_monitor_ready_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["targets"][0]["diagnostics"]["source_overclaim_rows"] = [
                {"alias": "approvedRuntimeEvidenceReady", "state": "ready"},
                {"name": "publicSdkReady", "value": "accepted"},
            ]
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].diagnostics.source_overclaim_rows[0]",
                result.stderr,
            )
            self.assertIn(
                "forbidden_passive_claim:$.targets[0].diagnostics.source_overclaim_rows[1]",
                result.stderr,
            )

            snapshot_root = tmp_path / "empty-snapshots"
            snapshot_root.mkdir()
            monitor_log = tmp_path / "monitor-overclaim.log"
            write_genesis2_monitor_only_log(
                monitor_log,
                roles=["session_start"],
                players_current=1,
                ready_overclaim=True,
            )

            monitor_result = run_latest_with_monitor(snapshot_root, monitor_log)

            self.assertEqual(
                monitor_result.returncode,
                0,
                monitor_result.stderr + monitor_result.stdout,
            )
            report = json.loads(monitor_result.stdout)
            target_key = "arkserver3:Genesis2:27017"
            tail = report["monitor"]["observer_tail_by_target"][target_key]
            self.assertFalse(tail["approved_runtime_evidence"])
            self.assertFalse(tail["ready"])
            self.assertEqual(tail["readiness_gate"], "none")
            self.assertFalse(report["approved_runtime_evidence"])
            self.assertFalse(report["ready"])
            self.assertFalse(report["route_ready"])
            activity = report["passive_monitor_activity_summary"]
            self.assertEqual(activity["passive_detection_targets"], [target_key])
            self.assertEqual(activity["complete_observer_event_triplet_targets"], [])
            self.assertFalse(activity["approved_runtime_evidence"])
            self.assertFalse(activity["ready"])

    def test_rejects_passive_server_activity_process_control_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["passive_server_activity_summary"] = {
                "approved_runtime_evidence": False,
                "ready": False,
                "readiness_gate": "none",
                "process_control": "terminate",
            }
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "passive_server_activity_summary_process_control_not_none",
                result.stderr,
            )

    def test_rejects_passive_wait_metadata_process_control_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["passive_wait_metadata"]["process_control"] = "restart"
            bad["passive_wait_metadata"]["observer_tail_by_target"]["arkserver:Ragnarok:27015"][
                "process_control"
            ] = "restart"
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "passive_wait_metadata_process_control_not_none",
                result.stderr,
            )
            self.assertIn(
                "passive_wait_metadata_observer_tail_by_target_arkserver:Ragnarok:27015_process_control_not_none",
                result.stderr,
            )

    def test_rejects_non_passive_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.json"
            candidate = tmp_path / "candidate.json"
            bad = deepcopy(passive_manifest(diagnostic_candidates=9))
            bad["schema"] = "obelisk.runtime-evidence-bundle.v1"
            base.write_text(json.dumps(passive_manifest(diagnostic_candidates=3)), encoding="utf-8")
            candidate.write_text(json.dumps(bad), encoding="utf-8")

            result = run_summary(base, candidate)

            self.assertEqual(result.returncode, 2)
            self.assertIn("schema_not_passive_snapshot", result.stderr)


if __name__ == "__main__":
    unittest.main()
