#!/usr/bin/env python3
"""Tests for report_player_principal_lifecycle_runtime_evidence_status.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import report_player_principal_lifecycle_runtime_evidence_status as status_report


SCRIPT = SCRIPT_DIR / "report_player_principal_lifecycle_runtime_evidence_status.py"
RUN_ID = "20260606T051057Z-player-principal-lifecycle"
TRIPLET_BY_ROLE = {
    str(case["role"]): case
    for case in status_report.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def notice_sidecar_payload(notice: dict[str, object]) -> dict[str, object]:
    return {
        "schema": status_report.NOTICE_ACTION_ARTIFACT_SCHEMA,
        "mode": notice.get("mode"),
        "ready": notice.get("ready"),
        "target": notice.get("target"),
        "run_id": notice.get("run_id"),
        "notice_path": notice.get("notice_path"),
        "request_json": notice.get("request_json"),
        "notice_report_sha256": status_report.canonical_json_sha256(notice),
        "notice_report": notice,
        "artifact_contains_full_sanitized_notice_report": True,
        "sidecar_required_for_confirmed_send_consumption": True,
        "stdout_only_confirmation_accepted": False,
        "secret_or_webhook_output_allowed": False,
        "discord_send_performed_by_artifact_write": False,
        **status_report.SIDECAR_NON_EVIDENCE_FLAGS,
        "non_authorization": (
            "notice preparation only; dry-run output and confirmed-send helper results are "
            "notice-action metadata only. This report does not grant Discord authorization, "
            "standing launch authority or current-turn approval, server operations, marker/env "
            "changes, starts, restarts, runtime capture, approved runtime evidence, public "
            "readiness, SDK completion, activation, or P0 progress"
        ),
    }


def jsonable_triplet_case(case: dict[str, object]) -> dict[str, object]:
    return {
        "label": case["label"],
        "role": case["role"],
        "target": case["target"],
        "post_original": case["post_original"],
        "copied_bool_fields": list(case["copied_bool_fields"]),
        "copied_bool_values": list(case["copied_bool_values"]),
        "redacted_count": case["redacted_count"],
        "redacted_fields": list(case["redacted_fields"]),
        "apply_status": case["apply_status"],
        "principal_action": case["principal_action"],
        "correlation_status": case["correlation_status"],
        "principal_id_logged": case["principal_id_logged"],
        "principal_generation_logged": case["principal_generation_logged"],
        "delivery_claim": case["delivery_claim"],
    }


def exact_triplet_state(missing_roles: list[str] | None = None) -> dict[str, object]:
    missing = set(missing_roles or [])
    matched = [
        {
            **jsonable_triplet_case(TRIPLET_BY_ROLE[role]),
            "accepted_as_lifecycle_role": True,
        }
        for role in status_report.REQUIRED_LIFECYCLE_ROLES
        if role not in missing
    ]
    missing_cases = [
        jsonable_triplet_case(TRIPLET_BY_ROLE[role])
        for role in status_report.REQUIRED_LIFECYCLE_ROLES
        if role in missing
    ]
    return {
        "roles_required": list(status_report.REQUIRED_LIFECYCLE_ROLES),
        "required_copied_lifecycle_event_triplet": status_report.required_copied_lifecycle_event_triplet(),
        "required_copied_lifecycle_event_triplet_labels": list(
            status_report.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "roles_seen": [
            role for role in status_report.REQUIRED_LIFECYCLE_ROLES if role not in missing
        ],
        "missing_roles": list(missing_roles or []),
        "matched_copied_lifecycle_event_triplet": matched,
        "missing_copied_lifecycle_event_triplet": missing_cases,
        "missing_copied_lifecycle_event_triplet_labels": [
            str(case["label"]) for case in missing_cases
        ],
        "copied_lifecycle_triplet_match_failures": [],
        "complete_triplet_candidate": not missing,
        "exact_copied_lifecycle_event_triplet_complete": not missing,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
    }


def closure_payload(
    *,
    invalid_sidecars: list[str] | None = None,
    missing_roles: list[str] | None = None,
    missing_artifacts: list[str] | None = None,
    missing_siblings: list[str] | None = None,
    ready: bool = False,
    run_id: str = RUN_ID,
    evidence_dir: str | None = None,
    evidence_source_blockers: list[dict[str, object]] | None = None,
    machine_next_actions: list[dict[str, object]] | None = None,
    bundle_command_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    exact_state = exact_triplet_state(missing_roles or [])
    evidence_dir_value = evidence_dir or f"/tmp/{run_id}"
    payload = {
        "schema": "obelisk.player-principal-lifecycle-evidence-closure-request.v1",
        "status": "closure_inputs_complete" if ready else "non_ready_missing_required_artifacts_and_lifecycle_roles",
        "closure_case": "closure_inputs_complete_no_readiness" if ready else "active_genesis2_triplet_incomplete",
        "run_id": run_id,
        "evidence_dir": evidence_dir_value,
        "approved_bundle_path": f"{evidence_dir_value}/approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        "ready": ready,
        "required_copied_lifecycle_event_triplet": status_report.required_copied_lifecycle_event_triplet(),
        "required_copied_lifecycle_event_triplet_labels": list(
            status_report.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "lifecycle_event_role_state": exact_state,
        "exact_copied_lifecycle_event_triplet_complete": exact_state[
            "exact_copied_lifecycle_event_triplet_complete"
        ],
        "missing_copied_lifecycle_event_triplet": exact_state[
            "missing_copied_lifecycle_event_triplet"
        ],
        "missing_copied_lifecycle_event_triplet_labels": exact_state[
            "missing_copied_lifecycle_event_triplet_labels"
        ],
        "invalid_sidecars": invalid_sidecars or [],
        "sidecar_validation_blockers": [],
        "evidence_source_blockers": evidence_source_blockers or [],
        "input_blockers": [],
        "missing_required_artifacts": missing_artifacts or [],
        "missing_siblings": missing_siblings or [],
        "missing_lifecycle_event_roles": missing_roles or [],
        "exact_missing_operations": [
            {"artifact": item} for item in [*(missing_artifacts or []), *(missing_roles or [])]
        ],
        "machine_next_actions_schema": "obelisk.player-principal-lifecycle-closure-machine-next-actions.v1",
        "machine_next_actions": machine_next_actions or [],
    }
    if bundle_command_metadata:
        payload["bundle_command_metadata"] = bundle_command_metadata
    return payload


def passive_payload(
    *,
    complete_targets: list[str] | None = None,
    players_current: int = 0,
) -> dict[str, object]:
    target = "arkserver3:Genesis2:27017"
    return {
        "schema": "obelisk.player-principal-passive-monitor-only-summary.v1",
        "classification": "no_snapshots_no_passive_detections_no_complete_triplets_non_evidence",
        "snapshot_count": 0,
        "snapshot_status": "no_snapshots_found",
        "ready": False,
        "approved_runtime_evidence": False,
        "monitor": {"latest_tick_utc": "2026-06-06T06:00:00Z"},
        "passive_monitor_activity_summary": {
            "observer_enabled_targets": [target],
            "players_current_by_target": {target: players_current},
            "complete_observer_event_triplet_targets": complete_targets or [],
            "targets_with_players_detected": [target] if players_current else [],
        },
    }


def route_gate_payload() -> dict[str, object]:
    return {
        "schema": "obelisk.command-permission-route-gate-check.v1",
        "valid": True,
        "planning_only": True,
        "route_blocked": True,
        "current_route_blocker": "approved_runtime_evidence_missing",
        "runtime_ready": False,
        "public_sdk_ready": False,
        "promotion_ready": False,
    }


def start_end_split_payload(*, include_overclaim_alias: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": status_report.PLAYER_PRINCIPAL_START_END_EVIDENCE_SCHEMA,
        "source_summary_path": "/tmp/principal-start-end-evidence.check.json",
        "source_schema": "obelisk.runtime-observer-log-summary.v1",
        "status": "accepted_for_contract_review",
        "ready": True,
        "ready_scope": "principal_start_end_runtime_evidence_only",
        "accepted_for_contract_review": True,
        "principal_start_end_runtime_evidence_present": True,
        "principal_start_end_runtime_evidence_ready": True,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "resolved_inputs": ["runtime.lifecycle_start_end_evidence"],
        "remaining_runtime_inputs": [
            "runtime.lifecycle_rejected_start_evidence",
            "approved_runtime_principal_lifecycle_evidence_bundle",
        ],
        "does_not_resolve": [
            "runtime.lifecycle_rejected_start_evidence",
            "approved_runtime_principal_lifecycle_evidence_bundle",
        ],
        "current_route_blocker": "approved_runtime_evidence_missing",
        "strict_route_blocked": True,
        "next_review_blocker": "approved_runtime_evidence_missing",
        "strict_approved_runtime_evidence_blockers": [
            "missing_exact_CheckJoinInProgress_1_0_session_start_rejected"
        ],
        "approved_runtime_evidence_blockers": [
            "missing_exact_CheckJoinInProgress_1_0_session_start_rejected"
        ],
        "contract_review_input_counts_as_approved_runtime_evidence": False,
        "observed_runtime_cases": [
            "observer_enable",
            "session_start_anchor",
            "session_end_anchor",
        ],
        "unresolved_runtime_cases": [
            "session_start_rejected_anchor",
            "exact_CheckJoinInProgress_1_0_session_start_rejected",
        ],
        "diagnostic_coverage": {
            "check_join_in_progress_diagnostic_count": 0,
            "diagnostic_candidates_count_as_evidence": False,
            "session_start_rejected_explicitly_missing": True,
        },
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "sdk_progress": 0,
        "p0_progress": 0,
        "blockers": [],
    }
    if include_overclaim_alias:
        payload["audit_alias"] = {
            "claim": "public_sdk_ready",
            "status": "ready",
        }
    return payload


def copy_ready_window_payload(
    *,
    window_state: str,
    roles_present: list[str],
    missing_roles: list[str],
    copy_readiness: str = "blocked_missing_lifecycle_roles",
    accepted_count: int | None = None,
    rejected_count: int = 0,
) -> dict[str, object]:
    is_active = window_state == "in_progress"
    is_post = window_state == "post_window"
    accepted = len(roles_present) if accepted_count is None else accepted_count
    return {
        "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
        "status": "blocked",
        "ready": False,
        "ready_to_copy": False,
        "copied": False,
        "copy_readiness": copy_readiness,
        "source_log": "/tmp/player-principal-window/Obelisk.log",
        "target_log": "/tmp/player-principal-window/copied/Obelisk.log",
        "roles_present": roles_present,
        "missing_roles": missing_roles,
        "source_log_not_ready": {
            "schema": "obelisk.player-principal-lifecycle-source-log-not-ready.v1",
            "classification": (
                "observer_enabled_lifecycle_window_in_progress"
                if is_active
                else "observer_enabled_lifecycle_post_window"
            ),
            "window_state": window_state,
            "fresh_window": {
                "start_utc": "2026-06-06T10:00:00Z",
                "end_utc": "2026-06-06T10:15:00Z",
            },
            "target_hint": {"instance": "arkserver2", "map": "TheIsland"},
            "observer_enabled": True,
            "observer_enable_in_fresh_window": True,
            "observer_only_no_role_window_detected": not roles_present,
            "active_observer_only_no_role_window": is_active and not roles_present,
            "post_window_observer_only_no_role_window": is_post and not roles_present,
            "manual_offline_next_steps": [
                "keep waiting" if is_active else "classify as non-evidence",
            ],
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        },
        "analysis": {
            "roles_present": roles_present,
            "missing_roles": missing_roles,
            "accepted_lifecycle_event_count": accepted,
            "rejected_or_incomplete_role_event_count": rejected_count,
            "rejected_or_incomplete_role_events": [
                {"role": "session_start", "reason": "diagnostic_only"}
            ]
            if rejected_count
            else [],
            "exact_copied_runtime_triplet": {
                "accepted": False,
                "missing_roles": missing_roles,
                "blockers": ["exact_copied_runtime_triplet_missing"],
            },
            "diagnostic_or_rejected_lifecycle_lines_count_as_ready_to_copy": False,
            "diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence": False,
        },
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
    }


def copy_ready_session_end_missing_correlation_payload(*, window_state: str) -> dict[str, object]:
    payload = copy_ready_window_payload(
        window_state=window_state,
        roles_present=["session_end"],
        missing_roles=["session_start", "session_start_rejected", "session_end"],
        copy_readiness="blocked_diagnostic_or_rejected_lifecycle_lines",
        accepted_count=0,
        rejected_count=1,
    )
    payload["blockers"] = ["session_end_missing_correlation_only"]
    payload["analysis"] = {
        **payload["analysis"],
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
    }
    payload["source_log_not_ready"] = {
        **payload["source_log_not_ready"],
        "observer_only_no_role_window_detected": False,
        "active_observer_only_no_role_window": False,
        "post_window_observer_only_no_role_window": False,
    }
    return payload


def copy_ready_rejected_start_unresolved_end_missing_start_payload(
    *,
    window_state: str,
) -> dict[str, object]:
    payload = copy_ready_window_payload(
        window_state=window_state,
        roles_present=["session_start_rejected"],
        missing_roles=["session_start", "session_end"],
        copy_readiness="blocked_missing_lifecycle_roles",
        accepted_count=1,
        rejected_count=1,
    )
    payload["ready_to_copy"] = True
    payload["copied"] = True
    payload["analysis"] = {
        **payload["analysis"],
        "roles_present": ["session_start_rejected"],
        "missing_roles": ["session_start", "session_end"],
        "accepted_lifecycle_event_count": 1,
        "rejected_or_incomplete_role_event_count": 1,
        "rejected_or_incomplete_role_events": [
            {
                "role": "session_end",
                "reason": "session_end_correlation_status_missing",
                "counts_as_approved_runtime_evidence": False,
            }
        ],
        "unsafe_lifecycle_event_reasons": {
            "session_end_correlation_status_missing": 1,
        },
        "invalid_lifecycle_event_non_evidence_reasons": {
            "session_end_correlation_status_missing": 1,
        },
        "exact_copied_runtime_triplet": {
            "accepted": False,
            "missing_roles": ["session_start", "session_end"],
            "blockers": [
                "session_start_missing",
                "session_end_missing_matched_correlation",
            ],
        },
    }
    return payload


class RuntimeEvidenceStatusTests(unittest.TestCase):
    def assert_no_readiness_or_progress_claims(self, context: dict[str, object]) -> None:
        for key in (
            "approved_runtime_evidence",
            "approved_runtime_evidence_present",
            "approved_runtime_evidence_ready",
            "counts_as_approved_runtime_evidence",
            "counts_as_runtime_evidence",
            "counts_as_sdk_evidence",
            "runtime_ready",
            "public_sdk_ready",
            "promotion_ready",
            "v1_completion_ready",
            "stable_sdk_ready",
            "grants_readiness_claims",
            "counts_toward_sdk",
            "counts_toward_v1_completion",
            "counts_toward_complete_sdk_claim_now",
            "counts_toward_p0_dependency_chain",
            "counts_toward_p0_dependency_chain_claim_now",
        ):
            if key in context:
                self.assertFalse(context[key], key)
        for key in ("sdk_progress", "p0_progress"):
            if key in context:
                self.assertEqual(context[key], 0, key)

    def run_script(
        self,
        closure: dict[str, object],
        passive: dict[str, object] | None = None,
        route_gate: dict[str, object] | None = None,
        standing_authority: bool = True,
        monitor_log: str | None = None,
        confirmed_beta_notice: dict[str, object] | None = None,
        copy_ready: dict[str, object] | None = None,
        player_principal_evidence_split: dict[str, object] | None = None,
        confirmed_beta_notice_as_sidecar: bool = False,
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            closure_path = tmp_path / "closure.json"
            route_path = tmp_path / "route.json"
            write_json(closure_path, closure)
            write_json(route_path, route_gate or route_gate_payload())
            args = [
                sys.executable,
                str(SCRIPT),
                "--closure-json",
                str(closure_path),
                "--route-gate-json",
                str(route_path),
            ]
            if standing_authority:
                args.append("--recorded-standing-debug-authority")
            if passive is not None:
                passive_path = tmp_path / "passive.json"
                write_json(passive_path, passive)
                args.extend(["--passive-summary-json", str(passive_path)])
            if monitor_log is not None:
                monitor_path = tmp_path / "post-reboot-monitor.log"
                monitor_path.write_text(monitor_log, encoding="utf-8")
                args.extend(["--post-reboot-monitor-log", str(monitor_path)])
            if confirmed_beta_notice is not None:
                if confirmed_beta_notice_as_sidecar:
                    notice_path = tmp_path / "beta-notice.confirmed.sidecar.json"
                    write_json(notice_path, notice_sidecar_payload(confirmed_beta_notice))
                else:
                    notice_path = tmp_path / "beta-notice.confirmed.json"
                    write_json(notice_path, confirmed_beta_notice)
                args.extend(["--confirmed-beta-notice-json", str(notice_path)])
            if copy_ready is not None:
                copy_ready_path = tmp_path / "copy-ready.json"
                write_json(copy_ready_path, copy_ready)
                args.extend(["--copy-ready-json", str(copy_ready_path)])
            if player_principal_evidence_split is not None:
                split_path = tmp_path / "player-principal-evidence-split.json"
                write_json(split_path, player_principal_evidence_split)
                args.extend(["--player-principal-evidence-split-json", str(split_path)])
            result = subprocess.run(
                args,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        return json.loads(result.stdout)

    def test_reports_post_reboot_monitor_latest_tick_and_query_status_as_context_only(self) -> None:
        monitor_log = "\n".join(
            [
                "tick utc=2026-06-06T08:00:00Z",
                "query instance=arkserver3 map=Genesis2 query_port=27017 status=ok "
                "current_map=Genesis2 players=0/70 target_key=arkserver3:Genesis2:27017 "
                "players_current=0 players_max=70 presence_detected=false "
                "detection_source=gamedig_ase_query",
                "tick utc=2026-06-06T08:05:00Z",
                "query instance=arkserver3 map=Genesis2 query_port=27017 status=ok "
                "current_map=Genesis2 players=2/70 target_key=arkserver3:Genesis2:27017 "
                "players_current=2 players_max=70 presence_detected=true "
                "detection_source=gamedig_ase_query",
                "query instance=arkserver map=Ragnarok query_port=27015 status=ok "
                "current_map=Ragnarok players=1/70 target_key=arkserver:Ragnarok:27015 "
                "players_current=1 players_max=70 presence_detected=true "
                "detection_source=gamedig_ase_query",
                "query instance=arkserver2 map=TheIsland query_port=27016 status=ok "
                "current_map=TheIsland players=0/70 target_key=arkserver2:TheIsland:27016 "
                "players_current=0 players_max=70 presence_detected=false "
                "detection_source=gamedig_ase_query",
                "",
            ]
        )

        report = self.run_script(
            closure_payload(missing_roles=["session_end"]),
            monitor_log=monitor_log,
        )

        monitor = report["post_reboot_passive_monitor"]
        self.assertTrue(monitor["present"])
        self.assertEqual(monitor["monitor_latest_tick_utc"], "2026-06-06T08:05:00Z")
        genesis = monitor["query_status_by_target"]["arkserver3:Genesis2:27017"]
        self.assertEqual(genesis["status"], "ok")
        self.assertEqual(genesis["players_current"], 2)
        self.assertTrue(genesis["presence_detected"])
        self.assertTrue(genesis["allowed_current_runtime_context_target"])
        self.assertFalse(genesis["treat_as_approved_runtime_evidence"])
        self.assertFalse(genesis["counts_as_runtime_evidence"])
        the_island = monitor["query_status_by_target"]["arkserver2:TheIsland:27016"]
        self.assertTrue(the_island["allowed_current_runtime_context_target"])
        self.assertFalse(the_island["treat_as_approved_runtime_evidence"])
        self.assertFalse(the_island["counts_as_runtime_evidence"])
        self.assertEqual(
            the_island["classification"],
            "approved_target_operator_context_non_evidence",
        )
        ragnarok = monitor["query_status_by_target"]["arkserver:Ragnarok:27015"]
        self.assertTrue(ragnarok["allowed_current_runtime_context_target"])
        self.assertTrue(ragnarok["ragnarok_auxiliary_diagnostic_non_evidence"])
        self.assertEqual(
            ragnarok["classification"],
            "ragnarok_auxiliary_target_diagnostic_non_evidence",
        )
        self.assertFalse(ragnarok["accepted_copied_sibling_bundle_present"])
        self.assertFalse(monitor["approved_runtime_evidence"])
        self.assertFalse(monitor["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])
        summary_context = report["operator_action_summary"]["operator_context_inputs"]
        self.assertTrue(summary_context["post_reboot_passive_monitor_log_supplied"])
        self.assertEqual(summary_context["monitor_latest_tick_utc"], "2026-06-06T08:05:00Z")
        self.assertEqual(
            summary_context["monitor_query_targets"],
            ["arkserver2:TheIsland:27016", "arkserver3:Genesis2:27017", "arkserver:Ragnarok:27015"],
        )
        self.assertFalse(summary_context["counts_as_runtime_evidence"])

    def test_post_reboot_monitor_rcon_presence_overrides_gamedig_zero_as_context_only(self) -> None:
        monitor_log = "\n".join(
            [
                "tick utc=2026-06-06T08:00:00Z",
                "query instance=arkserver map=Ragnarok query_port=27015 status=ok "
                "current_map=Ragnarok players=0/70 target_key=arkserver:Ragnarok:27015 "
                "players_current=0 players_max=70 presence_detected=false "
                "detection_source=gamedig_ase_query",
                "rcon_listplayers instance=arkserver map=Ragnarok query_port=27015 "
                "rcon_port=27020 status=ok players_current=2 "
                "target_key=arkserver:Ragnarok:27015 presence_detected=true "
                "detection_source=rcon_listplayers_redacted rcon_output_redacted=true",
                "",
            ]
        )

        report = self.run_script(
            closure_payload(missing_roles=["session_start_rejected"]),
            monitor_log=monitor_log,
        )

        monitor = report["post_reboot_passive_monitor"]
        query = monitor["query_status_by_target"]["arkserver:Ragnarok:27015"]
        rcon = monitor["rcon_status_by_target"]["arkserver:Ragnarok:27015"]
        self.assertEqual(query["players_current"], 0)
        self.assertEqual(query["detection_source"], "gamedig_ase_query")
        self.assertEqual(rcon["players_current"], 2)
        self.assertEqual(rcon["rcon_port"], "27020")
        self.assertTrue(rcon["rcon_output_redacted"])
        self.assertFalse(rcon["counts_as_runtime_evidence"])
        discrepancy = monitor["trusted_source_discrepancies_by_target"][
            "arkserver:Ragnarok:27015"
        ]
        self.assertEqual(
            discrepancy["classification"],
            "rcon_present_query_zero_trusted_source_discrepancy_non_evidence",
        )
        self.assertEqual(
            discrepancy["discrepant_sources"],
            ["gamedig_ase_query_zero", "rcon_listplayers_redacted_present"],
        )
        self.assertFalse(discrepancy["counts_as_approved_runtime_evidence"])
        self.assertFalse(discrepancy["authorizes_server_operations"])

        availability = report["runtime_player_availability"]
        self.assertEqual(
            availability["classification"],
            "players_detected_operator_context_non_evidence",
        )
        self.assertEqual(
            availability["known_player_counts_by_target"],
            {"arkserver:Ragnarok:27015": 2},
        )
        self.assertEqual(
            availability["targets_with_players_detected"],
            ["arkserver:Ragnarok:27015"],
        )
        self.assertTrue(availability["players_detected"])
        self.assertTrue(availability["source_discrepancy_detected"])
        self.assertEqual(
            availability["discrepant_sources_by_target"],
            {
                "arkserver:Ragnarok:27015": [
                    "gamedig_ase_query_zero",
                    "rcon_listplayers_redacted_present",
                ],
            },
        )
        self.assertEqual(
            availability["source_discrepancy_classification"],
            "trusted_source_discrepancy_non_evidence",
        )
        self.assertFalse(availability["source_discrepancy_counts_as_approved_runtime_evidence"])
        self.assertFalse(availability["source_discrepancy_authorizes_server_operations"])
        self.assertFalse(availability["approved_runtime_evidence"])
        self.assertFalse(availability["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])

        summary_context = report["operator_action_summary"]["operator_context_inputs"]
        self.assertEqual(summary_context["monitor_query_targets"], ["arkserver:Ragnarok:27015"])
        self.assertEqual(summary_context["monitor_rcon_targets"], ["arkserver:Ragnarok:27015"])
        self.assertFalse(summary_context["counts_as_runtime_evidence"])

    def test_post_reboot_monitor_positive_query_is_not_cleared_by_rcon_zero(self) -> None:
        monitor_log = "\n".join(
            [
                "tick utc=2026-06-06T08:00:00Z",
                "query instance=arkserver2 map=TheIsland query_port=27016 status=ok "
                "current_map=TheIsland players=1/70 target_key=arkserver2:TheIsland:27016 "
                "players_current=1 players_max=70 presence_detected=true "
                "detection_source=gamedig_ase_query",
                "rcon_listplayers instance=arkserver2 map=TheIsland query_port=27016 "
                "rcon_port=27021 status=ok players_current=0 "
                "target_key=arkserver2:TheIsland:27016 presence_detected=false "
                "detection_source=rcon_listplayers_redacted rcon_output_redacted=true",
                "",
            ]
        )

        report = self.run_script(
            closure_payload(missing_roles=["session_end"]),
            monitor_log=monitor_log,
        )

        availability = report["runtime_player_availability"]
        self.assertEqual(
            availability["known_player_counts_by_target"],
            {"arkserver2:TheIsland:27016": 1},
        )
        self.assertEqual(
            availability["targets_with_players_detected"],
            ["arkserver2:TheIsland:27016"],
        )
        self.assertTrue(availability["players_detected"])
        self.assertFalse(availability["approved_runtime_evidence"])

    def test_player_presence_context_is_reported_as_non_evidence(self) -> None:
        report = self.run_script(
            closure_payload(missing_roles=["session_end"]),
            passive_payload(players_current=2),
        )

        context = report["player_presence_context"]
        self.assertEqual(context["classification"], "players_detected_operator_context_non_evidence")
        self.assertEqual(context["targets_with_players_detected"], ["arkserver3:Genesis2:27017"])
        self.assertTrue(context["players_detected"])
        self.assertFalse(context["counts_as_approved_runtime_evidence"])
        self.assertFalse(context["authorizes_runtime_capture"])
        self.assertFalse(report["approved_runtime_evidence"])
        summary_context = report["operator_action_summary"]["operator_context_inputs"]
        self.assertEqual(
            summary_context["player_presence_context"]["classification"],
            "players_detected_operator_context_non_evidence",
        )
        self.assertFalse(summary_context["player_presence_context_counts_as_approved_runtime_evidence"])
        action_context = report["next_actions"][0]["non_evidence_context"]
        self.assertFalse(
            action_context[
                "diagnostic_only_handle_new_player_or_k2_post_login_lines_count_as_evidence"
            ]
        )
        self.assertFalse(action_context["player_presence_context_counts_as_approved_runtime_evidence"])
        self.assertFalse(
            report["machine_next_actions"][0]["non_evidence_context"][
                "player_presence_context_counts_as_approved_runtime_evidence"
            ]
        )

    def test_reports_confirmed_beta_notice_completion_and_standing_authority_as_context_only(self) -> None:
        notice = {
            "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
            "ready": True,
            "mode": "confirmed_send",
            "discord_sent": True,
            "send_helper_returncode_zero": True,
            "target": {"instance": "arkserver3", "map": "Genesis2"},
            "run_id": RUN_ID,
            "notice_path": "discord://obelisk-beta-testers",
            "standing_launch_authority_recorded": True,
            "standing_launch_authority_satisfies_notice_scope": True,
            "notice_action_covered_by_standing_launch_authority": True,
            "guarded_beta_notice_action": {
                "real_beta_test_notice_action_completed": True,
                "standing_launch_authority_recorded": True,
                "standing_launch_authority_satisfies_notice_scope": True,
                "notice_action_covered_by_standing_launch_authority": True,
                "counts_as_approved_runtime_evidence": True,
                "server_operations_authorized": True,
            },
            "confirmed_send_authorizes_activation": True,
            "confirmed_send_authorizes_runtime_capture": True,
            "confirmed_send_authorizes_server_operations": True,
            "approved_runtime_evidence": True,
            "runtime_ready": True,
            "public_sdk_ready": True,
        }

        report = self.run_script(
            closure_payload(missing_artifacts=["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"]),
            confirmed_beta_notice=notice,
        )

        beta_notice = report["confirmed_beta_notice"]
        self.assertTrue(beta_notice["present"])
        self.assertTrue(beta_notice["schema_matches_beta_notice_report"])
        self.assertEqual(beta_notice["mode"], "confirmed_send")
        self.assertTrue(beta_notice["completed"])
        self.assertEqual(beta_notice["completion_status"], "confirmed_beta_notice_completed")
        self.assertTrue(beta_notice["standing_launch_authority_recorded"])
        self.assertTrue(beta_notice["standing_launch_authority_satisfies_notice_scope"])
        self.assertTrue(beta_notice["notice_action_covered_by_standing_launch_authority"])
        self.assertFalse(beta_notice["confirmed_send_authorizes_activation"])
        self.assertFalse(beta_notice["confirmed_send_authorizes_runtime_capture"])
        self.assertFalse(beta_notice["confirmed_send_authorizes_server_operations"])
        self.assertFalse(beta_notice["approved_runtime_evidence"])
        self.assertFalse(beta_notice["counts_as_runtime_evidence"])
        self.assertFalse(beta_notice["runtime_ready"])
        self.assertFalse(beta_notice["public_sdk_ready"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        summary_context = report["operator_action_summary"]["operator_context_inputs"]
        self.assertTrue(summary_context["confirmed_beta_notice_json_supplied"])
        self.assertTrue(summary_context["confirmed_beta_notice_completed"])
        self.assertTrue(summary_context["confirmed_beta_notice_standing_launch_authority_recorded"])
        self.assertFalse(summary_context["approved_runtime_evidence"])

    def test_reports_confirmed_beta_notice_sidecar_completion_as_context_only(self) -> None:
        notice = {
            "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
            "ready": True,
            "mode": "confirmed_send",
            "discord_sent": True,
            "send_helper_returncode_zero": True,
            "request_json": {"path": "/tmp/window-request.json", "sha256": "1" * 64},
            "target": {"instance": "arkserver3", "map": "Genesis2"},
            "run_id": RUN_ID,
            "notice_path": "discord://obelisk-beta-testers",
            "standing_launch_authority_recorded": True,
            "standing_launch_authority_satisfies_notice_scope": True,
            "notice_action_covered_by_standing_launch_authority": True,
            "guarded_beta_notice_action": {
                "real_beta_test_notice_action_completed": True,
                "standing_launch_authority_recorded": True,
                "standing_launch_authority_satisfies_notice_scope": True,
                "notice_action_covered_by_standing_launch_authority": True,
            },
            "approved_runtime_evidence": True,
            "runtime_ready": True,
        }

        report = self.run_script(
            closure_payload(missing_artifacts=["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"]),
            confirmed_beta_notice=notice,
            confirmed_beta_notice_as_sidecar=True,
        )

        beta_notice = report["confirmed_beta_notice"]
        self.assertTrue(beta_notice["present"])
        self.assertTrue(beta_notice["source_is_notice_action_sidecar"])
        self.assertTrue(beta_notice["sidecar_valid_for_context"])
        self.assertEqual(beta_notice["sidecar_validation_blockers"], [])
        self.assertTrue(beta_notice["completed"])
        self.assertFalse(beta_notice["accepted_as_activation_notice"])
        self.assertFalse(beta_notice["approved_runtime_evidence"])
        self.assertFalse(beta_notice["runtime_ready"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_reports_copy_ready_json_as_context_only(self) -> None:
        copy_ready = {
            "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
            "status": "copied",
            "copy_readiness": "ready_complete_role_triplet",
            "ready_to_copy": True,
            "copied": True,
            "roles_present": ["session_start", "session_start_rejected", "session_end"],
            "missing_roles": [],
            "blockers": [],
            "source_log": "/servidor/ark/obelisk/logs/arkserver3/Obelisk.log",
            "target_log": "/servidor/ark/workspace-offline/live-validation-logs/run/Obelisk.log",
            "approved_runtime_evidence": True,
            "runtime_ready": True,
            "public_sdk_ready": True,
        }

        report = self.run_script(
            closure_payload(missing_artifacts=["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"]),
            copy_ready=copy_ready,
        )

        context = report["copy_ready_log"]
        self.assertTrue(context["present"])
        self.assertEqual(context["status"], "copied")
        self.assertEqual(context["copy_readiness"], "ready_complete_role_triplet")
        self.assertTrue(context["ready_to_copy_source_value"])
        self.assertTrue(context["copied_source_value"])
        self.assertFalse(context["ready_to_copy"])
        self.assertFalse(context["copied"])
        self.assertFalse(context["approved_runtime_evidence"])
        self.assertFalse(context["runtime_ready"])
        self.assertFalse(context["public_sdk_ready"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        summary_context = report["operator_action_summary"]["operator_context_inputs"]
        self.assertTrue(summary_context["copy_ready_json_supplied"])
        self.assertEqual(summary_context["copy_ready_status"], "copied")
        self.assertEqual(summary_context["copy_readiness"], "ready_complete_role_triplet")
        self.assertTrue(summary_context["copy_ready_helper_copied_source_value"])
        self.assertFalse(summary_context["approved_runtime_evidence"])
        self.assertTrue(report["operator_action_summary"]["resume_context"]["copy_ready_context_present"])

    def test_copy_ready_source_present_and_candidate_pack_aliases_are_non_evidence(self) -> None:
        copy_ready = {
            "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
            "status": "copied",
            "copy_readiness": "ready_complete_role_triplet",
            "ready_to_copy": True,
            "copied": True,
            "source_present": True,
            "candidate_pack_present": True,
            "source_input": {
                "source_kind": "candidate_runtime_log",
                "status": "accepted_candidate_log_path",
            },
            "roles_present": list(status_report.REQUIRED_LIFECYCLE_ROLES),
            "missing_roles": [],
            "source_log": "/tmp/player-principal-window/Obelisk.log",
            "target_log": "/tmp/player-principal-window/copied/Obelisk.log",
            "analysis": {
                "exact_copied_runtime_triplet": {"accepted": True},
                "accepted_lifecycle_event_count": 3,
            },
            "approved_runtime_evidence": True,
            "counts_as_approved_runtime_evidence": True,
            "runtime_ready": True,
            "sdk_progress": 12,
            "p0_progress": 4,
        }

        report = self.run_script(
            closure_payload(
                ready=True,
                missing_artifacts=["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"],
            ),
            copy_ready=copy_ready,
        )

        context = report["copy_ready_log"]
        self.assertTrue(context["source_present_alias_detected"])
        self.assertTrue(context["candidate_pack_alias_detected"])
        self.assertIn("$.source_present", context["source_present_alias_paths"])
        self.assertIn("$.candidate_pack_present", context["candidate_pack_alias_paths"])
        self.assertIn("$.source_input.status", context["candidate_pack_alias_paths"])
        self.assertFalse(context["source_present_aliases_count_as_approved_runtime_evidence"])
        self.assertFalse(context["candidate_pack_aliases_count_as_approved_runtime_evidence"])
        self.assertFalse(context["approved_runtime_evidence"])
        self.assertEqual(context["sdk_progress"], 0)
        self.assertEqual(context["p0_progress"], 0)

        boundary = report["runtime_window_lifecycle"]["copy_ready_source_boundary"]
        self.assertEqual(
            boundary["classification"],
            "candidate_pack_copy_ready_source_only_non_evidence",
        )
        self.assertTrue(boundary["source_only_non_evidence"])
        self.assertFalse(boundary["candidate_pack_alias_counts_as_approved_runtime_evidence"])

        material = report["runtime_evidence_acceptance_boundary"]["material_classes"][
            "source_present_aliases"
        ]
        self.assertTrue(material["present"])
        self.assertIn("non_evidence", material["classification"])
        self.assertTrue(material["candidate_pack_alias_is_source_only"])
        self.assertFalse(material["source_present_alias_counts_as_evidence"])
        self.assertFalse(material["candidate_pack_alias_counts_as_evidence"])
        self.assert_no_readiness_or_progress_claims(material)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_load_or_run_closure_forwards_post_reboot_context_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            monitor_log = tmp_path / "post-reboot-monitor.log"
            notice_json = tmp_path / "beta-notice.confirmed.json"
            evidence_dir = tmp_path / RUN_ID
            captured: dict[str, object] = {}

            args = argparse.Namespace(
                closure_json=None,
                evidence_dir=evidence_dir,
                instance="arkserver3",
                map_name="Genesis2",
                query_port="27017",
                notice_path="discord__obelisk-beta-testers",
                post_reboot_monitor_log=monitor_log,
                confirmed_beta_notice_json=notice_json,
                the_island_off=True,
                two_server_cap_preserved=True,
                future_window_needs_players=True,
            )

            original_run_json_command = status_report.run_json_command

            def fake_run_json_command(
                argv: list[str], *, allow_nonzero: bool = False
            ) -> tuple[dict[str, object], int, str]:
                captured["argv"] = argv
                captured["allow_nonzero"] = allow_nonzero
                return closure_payload(), 0, ""

            status_report.run_json_command = fake_run_json_command
            try:
                _payload, returncode = status_report.load_or_run_closure(args)
            finally:
                status_report.run_json_command = original_run_json_command

            argv = captured["argv"]
            self.assertEqual(returncode, 0)
            self.assertIs(captured["allow_nonzero"], True)
            self.assertIn("--post-reboot-monitor-log", argv)
            self.assertIn(str(monitor_log), argv)
            self.assertIn("--confirmed-beta-notice-json", argv)
            self.assertIn(str(notice_json), argv)
            self.assertIn("--the-island-off", argv)
            self.assertIn("--two-server-cap-preserved", argv)
            self.assertIn("--future-window-needs-players", argv)

    def test_reports_missing_roles_and_artifacts_without_readiness_claim(self) -> None:
        report = self.run_script(
            closure_payload(
                missing_roles=["session_start", "session_start_rejected", "session_end"],
                missing_artifacts=[
                    "window-manifest.env",
                    "preflight-post.json",
                    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                ],
            ),
            passive_payload(players_current=0),
        )

        self.assertEqual(report["schema"], status_report.SCHEMA)
        self.assertEqual(report["status"], "blocked_missing_lifecycle_roles")
        self.assertFalse(report["ready"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertEqual(report["route_gate"]["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["passive"]["players_current_by_target"], {"arkserver3:Genesis2:27017": 0})
        availability = report["runtime_player_availability"]
        self.assertEqual(
            availability["classification"],
            "no_players_currently_detected_wait_for_testers_non_evidence",
        )
        self.assertTrue(availability["no_players_currently_detected"])
        self.assertFalse(availability["players_detected"])
        self.assertFalse(availability["activates_runtime_window"])
        self.assertFalse(availability["authorizes_runtime_capture"])
        self.assertFalse(availability["approved_runtime_evidence"])
        self.assertFalse(availability["counts_as_runtime_evidence"])
        summary = report["operator_action_summary"]
        self.assertEqual(
            summary["operator_context_inputs"]["player_availability_classification"],
            "no_players_currently_detected_wait_for_testers_non_evidence",
        )
        self.assertTrue(summary["operator_context_inputs"]["no_players_currently_detected"])
        self.assertEqual(summary["run_id"], RUN_ID)
        self.assertIn("recorded standing debug authority", summary["headline"])
        current_blockers = summary["blocking_inputs"]["current_live_diagnostic_blockers"]
        self.assertEqual(
            current_blockers["classification"],
            "source_bound_drift_blockers_non_evidence",
        )
        self.assertTrue(current_blockers["source_bound_blocker"])
        self.assertEqual(
            current_blockers["current_source_bound_route_blocker"],
            "source_bound_drift_blocks_accepted_lifecycle_events",
        )
        self.assertFalse(current_blockers["blind_wait_recommended"])
        self.assertFalse(current_blockers["restart_recommended"])
        self.assertFalse(current_blockers["wait_or_restart_or_logout_instruction_allowed"])
        self.assertFalse(current_blockers["logout_or_reconnect_instruction_allowed"])
        self.assertFalse(current_blockers["counts_as_approved_runtime_evidence"])
        self.assertEqual(current_blockers["sdk_progress"], 0)
        self.assertEqual(
            summary["blocking_inputs"]["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(
            summary["blocking_inputs"]["missing_required_artifacts"],
            [
                "window-manifest.env",
                "preflight-post.json",
                "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            ],
        )
        self.assertTrue(summary["recorded_standing_debug_authority"]["recorded"])
        self.assertFalse(summary["recorded_standing_debug_authority"]["authorized_by_this_report"])
        self.assertFalse(summary["recorded_standing_debug_authority"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(summary["recorded_standing_debug_authority"]["grants_readiness_claims"])
        self.assertEqual(
            [action["action"] for action in summary["actions_allowed_under_recorded_standing_debug_authority"]],
            [
                "continue_exact_player_principal_lifecycle_runtime_observation_for_missing_roles",
                "complete_checked_sibling_artifacts_for_same_run",
            ],
        )
        self.assertEqual(
            [action["action"] for action in report["next_actions"]],
            ["wait_for_or_capture_missing_lifecycle_roles", "produce_checked_sibling_artifacts"],
        )

    def test_invalid_sidecars_are_prioritized_before_missing_artifacts(self) -> None:
        report = self.run_script(
            closure_payload(
                invalid_sidecars=["operator-approval-receipt.template.json"],
                missing_artifacts=["window-manifest.env"],
            )
        )

        self.assertEqual(report["status"], "blocked_invalid_sidecars")
        self.assertEqual(report["next_actions"][0]["action"], "fix_invalid_sidecars")
        self.assertEqual(report["next_actions"][0]["items"], ["operator-approval-receipt.template.json"])
        self.assertFalse(report["next_actions"][0]["authorized_by_this_report"])

    def test_names_critical_missing_artifact_blockers_and_synthesizes_fastest_route(self) -> None:
        bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        report = self.run_script(
            closure_payload(
                ready=True,
                missing_siblings=["Obelisk.log"],
                missing_artifacts=["window-manifest.env", "preflight-post.json", bundle],
            ),
            passive_payload(complete_targets=["arkserver3:Genesis2:27017"]),
        )

        self.assertEqual(report["status"], "blocked_missing_required_artifacts")
        self.assertFalse(report["closure"]["ready"])
        artifact_state = report["runtime_evidence_artifact_blockers"]
        self.assertEqual(artifact_state["first_missing_artifact"], "Obelisk.log")
        self.assertEqual(artifact_state["first_blocker_reason"], "copied_obelisk_log_missing")
        self.assertEqual(
            artifact_state["missing_artifact_reasons"],
            [
                "copied_obelisk_log_missing",
                "window_manifest_env_missing",
                "preflight_post_json_missing",
                "approved_runtime_principal_lifecycle_evidence_json_missing",
            ],
        )
        self.assertEqual(
            [
                entry["artifact"]
                for entry in artifact_state[
                    "fastest_exact_path_from_fresh_copied_lifecycle_window"
                ]
            ],
            ["Obelisk.log", "window-manifest.env", "preflight-post.json", bundle],
        )
        self.assertFalse(artifact_state["approved_runtime_principal_lifecycle_evidence_bundle_ready"])
        self.assertEqual(
            report["operator_action_summary"]["blocking_inputs"][
                "first_missing_artifact_blocker_reason"
            ],
            "copied_obelisk_log_missing",
        )
        self.assertEqual(len(report["machine_next_actions"]), 4)
        first_action = report["machine_next_actions"][0]
        self.assertEqual(first_action["action"], "copy_ready_player_principal_lifecycle_obelisk_log")
        self.assertEqual(first_action["missing_artifact_blocker_reason"], "copied_obelisk_log_missing")
        self.assertEqual(first_action["required_script"], "scripts/copy_player_principal_lifecycle_ready_log.py")
        self.assertEqual(first_action["command_status"], "NOT PROVIDED")
        self.assertFalse(first_action["runner_command_available"])
        self.assertFalse(first_action["approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)
        fast_path = report["runtime_evidence_fast_path"]
        self.assertEqual(
            fast_path["schema"],
            status_report.RUNTIME_EVIDENCE_FAST_PATH_SCHEMA,
        )
        self.assertEqual(
            fast_path["first_blocking_category"],
            "missing_required_runtime_evidence_artifact",
        )
        self.assertEqual(fast_path["first_missing_artifact"], "Obelisk.log")
        self.assertEqual(fast_path["first_action"], "copy_ready_player_principal_lifecycle_obelisk_log")
        self.assertEqual(fast_path["first_action_side_effect_domain"], "live_log_copy")
        self.assertTrue(fast_path["first_manual_or_live_step_required"])
        self.assertTrue(fast_path["live_step_required_before_first_offline_helper"])
        self.assertFalse(fast_path["first_structured_offline_helper_available"])
        self.assertFalse(fast_path["approved_runtime_evidence"])
        self.assertEqual(fast_path["sdk_progress"], 0)
        self.assertEqual(fast_path["p0_progress"], 0)
        self.assertEqual(
            [stage.get("artifact") for stage in fast_path["sequence"] if stage["stage"] == "required_runtime_evidence_artifact"],
            ["Obelisk.log", "window-manifest.env", "preflight-post.json", bundle],
        )

    def test_complete_closure_still_requires_bundle_checker(self) -> None:
        report = self.run_script(closure_payload(ready=True), passive_payload(complete_targets=["arkserver3:Genesis2:27017"]))

        self.assertEqual(report["status"], "closure_inputs_complete_bundle_checker_required")
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["closure"]["ready"])
        self.assertTrue(report["closure"]["ready_for_checker"])
        self.assertEqual(report["next_actions"][0]["action"], "run_approved_runtime_evidence_bundle_checker")
        self.assertFalse(report["next_actions"][0]["authorized_by_this_report"])
        self.assertEqual(
            report["machine_next_actions"][0]["action"],
            "run_approved_runtime_evidence_checker_on_copied_manifest",
        )
        self.assertIn(
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            report["machine_next_actions"][0]["command_text_not_executed"],
        )
        self.assertEqual(
            report["machine_next_actions"][0]["command_text_not_executed"],
            (
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py "
                f"/tmp/{RUN_ID}/approved-bundle/approved-runtime-principal-lifecycle-evidence.json --json"
            ),
        )
        self.assertTrue(report["machine_next_actions"][0]["runner_command_available"])
        self.assertEqual(
            report["machine_next_actions"][0]["runner_command"],
            {
                "argv": [
                    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                    f"/tmp/{RUN_ID}/approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                    "--json",
                ],
                "execution_mode": "no_shell_offline_helper",
            },
        )
        self.assertTrue(report["machine_next_actions"][0]["machine_executable"])
        self.assertFalse(report["machine_next_actions"][0]["writes_under_evidence_dir"])
        self.assertEqual(
            report["machine_next_actions"][0]["exact_checkjoininprogress_route_wording"],
            status_report.CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        )
        self.assertTrue(report["first_machine_next_action"]["runner_command_available"])
        self.assertEqual(
            report["first_machine_next_action"]["structured_argv"],
            [
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                f"/tmp/{RUN_ID}/approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                "--json",
            ],
        )
        self.assertFalse(report["machine_next_actions"][0]["approved_runtime_evidence"])
        self.assertFalse(report["machine_next_actions"][0]["approved_runtime_evidence_accepted_by_checker"])
        fast_path = report["runtime_evidence_fast_path"]
        self.assertEqual(fast_path["first_blocking_category"], "approved_bundle_checker_required")
        acceptance = report["runtime_evidence_acceptance_state"]
        self.assertEqual(
            acceptance["classification"],
            "accepted_ready_for_checker_not_checker_accepted",
        )
        self.assertTrue(acceptance["accepted_ready_for_checker"])
        self.assertFalse(acceptance["checker_accepted_ready"])
        self.assertFalse(acceptance["expired_no_evidence"])
        self.assertFalse(acceptance["counts_as_approved_runtime_evidence"])
        self.assertEqual(
            fast_path["runtime_evidence_acceptance_state"],
            acceptance,
        )
        self.assertEqual(
            fast_path["first_action"],
            "run_approved_runtime_evidence_checker_on_copied_manifest",
        )
        self.assertTrue(fast_path["first_structured_offline_helper_available"])
        self.assertFalse(fast_path["first_manual_or_live_step_required"])
        self.assertFalse(fast_path["live_step_required_before_first_offline_helper"])
        self.assertEqual(
            fast_path["first_structured_offline_helper_argv"],
            [
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                f"/tmp/{RUN_ID}/approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                "--json",
            ],
        )
        self.assertFalse(fast_path["approved_runtime_evidence"])
        self.assertEqual(fast_path["sdk_progress"], 0)
        self.assertEqual(
            report["operator_action_summary"]["actions_allowed_under_recorded_standing_debug_authority"][0]["action"],
            "run_approved_runtime_evidence_checker_on_completed_sibling_set",
        )
        self.assertFalse(
            report["operator_action_summary"]["evidence_readiness_claims"][
                "counts_as_approved_runtime_evidence"
            ]
        )
        checker_boundary = report["runtime_evidence_acceptance_boundary"]["material_classes"][
            "checker_accepted_approved_evidence"
        ]
        self.assertEqual(checker_boundary["required_checker"], status_report.BUNDLE_CHECKER_SCRIPT)
        self.assertTrue(checker_boundary["required_checker_script_available"])

    def test_acceptance_boundary_keeps_non_evidence_material_out_of_checker_claim(self) -> None:
        report = self.run_script(
            closure_payload(missing_roles=["session_start_rejected"]),
            passive_payload(players_current=1),
            player_principal_evidence_split=start_end_split_payload(),
        )

        boundary = report["runtime_evidence_acceptance_boundary"]
        self.assertEqual(
            boundary["schema"],
            status_report.RUNTIME_EVIDENCE_ACCEPTANCE_BOUNDARY_SCHEMA,
        )
        self.assertEqual(boundary["status"], "blocked_approved_runtime_evidence_missing")
        self.assertEqual(boundary["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertFalse(boundary["accepted_checker_report_supplied_to_status_report"])
        self.assertFalse(boundary["status_report_sets_sdk_or_p0_progress"])
        self.assertFalse(boundary["status_report_sets_readiness"])
        self.assertFalse(boundary["readiness_claims_set_by_status_report"])
        self.assertEqual(
            boundary["exact_checkjoininprogress_route_wording"],
            status_report.CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        )
        for text in (
            "CheckJoinInProgress(1,0)",
            "ShooterGameMode.CheckJoinInProgress",
            "copied_bool_values=1,0",
            "session_start_rejected",
        ):
            self.assertIn(text, boundary["exact_checkjoininprogress_route_wording"])

        material_classes = boundary["material_classes"]
        self.assertTrue(material_classes["diagnostic"]["present"])
        self.assertTrue(material_classes["passive"]["present"])
        self.assertTrue(material_classes["runtime_start_end"]["present"])
        self.assertTrue(material_classes["context_only"]["present"])
        self.assertFalse(material_classes["checker_accepted_approved_evidence"]["present"])
        self.assertEqual(
            material_classes["checker_accepted_approved_evidence"]["required_checker"],
            "checker_accepted_bundle_required",
        )
        self.assertFalse(
            material_classes["checker_accepted_approved_evidence"][
                "required_checker_script_available"
            ]
        )
        for name in (
            "diagnostic",
            "passive",
            "runtime_start_end",
            "context_only",
            "checker_accepted_approved_evidence",
        ):
            with self.subTest(material_class=name):
                self.assert_no_readiness_or_progress_claims(material_classes[name])

        split_rejected_start = report["player_principal_evidence_split"]["components"][
            "session_start_rejected"
        ]
        self.assertEqual(
            split_rejected_start["exact_route_wording"],
            status_report.CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        )
        self.assertEqual(
            report["route_gate"]["approved_runtime_evidence_missing_route_wording"],
            status_report.CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        )
        self.assertEqual(
            report["machine_next_actions"][0]["exact_checkjoininprogress_route_wording"],
            status_report.CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        )
        self.assert_no_readiness_or_progress_claims(boundary)
        self.assert_no_readiness_or_progress_claims(report)

    def test_acceptance_boundary_explicitly_classifies_non_evidence_material_until_checker_accepts_sibling_set(self) -> None:
        bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        notice = {
            "schema": status_report.CONFIRMED_BETA_NOTICE_SCHEMA,
            "ready": True,
            "mode": "confirmed_send",
            "discord_sent": True,
            "target": {"instance": "arkserver3", "map": "Genesis2"},
            "run_id": RUN_ID,
            "notice_path": "discord://obelisk-beta-testers",
            "standing_launch_authority_recorded": True,
            "standing_launch_authority_satisfies_notice_scope": True,
            "notice_action_covered_by_standing_launch_authority": True,
            "approved_runtime_evidence": True,
            "runtime_ready": True,
        }
        copy_ready = {
            "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
            "status": "copied",
            "copy_readiness": "ready_complete_role_triplet",
            "ready_to_copy": True,
            "copied": True,
            "roles_present": list(status_report.REQUIRED_LIFECYCLE_ROLES),
            "missing_roles": [],
            "source_log": "/tmp/player-principal-window/Obelisk.log",
            "target_log": "/tmp/player-principal-window/copied/Obelisk.log",
            "analysis": {
                "exact_copied_runtime_triplet": {"accepted": True},
                "accepted_lifecycle_event_count": 3,
            },
            "approved_runtime_evidence": True,
            "counts_as_approved_runtime_evidence": True,
            "runtime_ready": True,
        }

        report = self.run_script(
            closure_payload(
                ready=True,
                missing_artifacts=["window-manifest.env", "preflight-post.json", bundle],
                missing_siblings=["window-request.json", "observer-window.env"],
            ),
            passive_payload(complete_targets=["arkserver3:Genesis2:27017"]),
            confirmed_beta_notice=notice,
            copy_ready=copy_ready,
            player_principal_evidence_split=start_end_split_payload(),
        )

        boundary = report["runtime_evidence_acceptance_boundary"]
        material_classes = boundary["material_classes"]
        expected_sibling_set = list(status_report.APPROVED_RUNTIME_EVIDENCE_EXACT_SIBLING_SET)
        explicit_non_evidence_classes = (
            "start_end_only",
            "diagnostic_triplets",
            "beta_notices",
            "request_window_artifacts",
            "copied_log_presence",
        )
        for name in explicit_non_evidence_classes:
            with self.subTest(material_class=name):
                material = material_classes[name]
                self.assertTrue(material["present"])
                self.assertIn("non_evidence", material["classification"])
                self.assertTrue(material["accepted_bundle_checker_required_before_evidence"])
                self.assertTrue(
                    material["only_counts_after_approved_bundle_checker_accepts_exact_sibling_set"]
                )
                self.assertFalse(material["approved_bundle_checker_accepts_exact_sibling_set"])
                self.assertFalse(material["exact_sibling_set_accepted_by_checker"])
                self.assertEqual(
                    material["required_checker"],
                    "approved_bundle_checker_acceptance_required",
                )
                self.assertEqual(material["required_exact_sibling_set"], expected_sibling_set)
                self.assertFalse(material["approved_runtime_evidence"])
                self.assertFalse(material["counts_as_approved_runtime_evidence"])
                self.assert_no_readiness_or_progress_claims(material)

        self.assertEqual(material_classes["start_end_only"]["roles"], ["session_start", "session_end"])
        self.assertTrue(material_classes["diagnostic_triplets"]["passive_complete_triplet_targets"])
        self.assertTrue(material_classes["diagnostic_triplets"]["copy_ready_exact_triplet_source_value"])
        self.assertTrue(material_classes["beta_notices"]["completed"])
        self.assertFalse(material_classes["beta_notices"]["discord_send_or_notice_completion_counts_as_evidence"])
        self.assertEqual(
            set(material_classes["request_window_artifacts"]["missing_request_window_artifacts"]),
            {"window-manifest.env", "preflight-post.json", "window-request.json", "observer-window.env"},
        )
        self.assertTrue(material_classes["copied_log_presence"]["copy_ready_copied_source_value"])
        self.assertFalse(material_classes["copied_log_presence"]["copied_log_presence_counts_as_evidence"])
        for name in explicit_non_evidence_classes:
            self.assertIn(name, boundary["non_evidence_material_classes"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_stale_passive_complete_role_triplet_remains_non_evidence(self) -> None:
        copy_ready = copy_ready_window_payload(
            window_state="post_window",
            roles_present=list(status_report.REQUIRED_LIFECYCLE_ROLES),
            missing_roles=[],
            copy_readiness="ready_complete_role_triplet",
            accepted_count=3,
        )
        source_dir = "/tmp/live-validation-logs/20260607T071833Z-postpatch-ragnarok-theisland-monitor"
        copy_ready.update(
            {
                "status": "blocked",
                "ready_to_copy": True,
                "copied": True,
                "source_log": f"{source_dir}/Obelisk.log",
                "target_log": f"{source_dir}/copied/Obelisk.log",
                "source_looks_like_passive_monitor_root": True,
                "source_root_stale": True,
                "source_root_valid_for_closure": False,
                "passive_monitor_root_accepted_as_closure_evidence_dir": False,
                "approved_runtime_evidence": True,
                "counts_as_approved_runtime_evidence": True,
            }
        )
        copy_ready["source_log_not_ready"] = {
            **copy_ready["source_log_not_ready"],
            "classification": "stale_passive_complete_role_triplet_non_evidence",
            "source_evidence_dir": source_dir,
            "source_root_role": "post_reboot_passive_monitor_root",
            "source_looks_like_passive_monitor_root": True,
            "source_root_stale": True,
            "source_root_valid_for_closure": False,
            "passive_monitor_root_accepted_as_closure_evidence_dir": False,
            "observer_only_no_role_window_detected": False,
            "post_window_observer_only_no_role_window": False,
        }
        copy_ready["analysis"] = {
            **copy_ready["analysis"],
            "exact_copied_runtime_triplet": {
                "accepted": True,
                "source": "stale_passive_status_report",
            },
        }

        report = self.run_script(
            closure_payload(ready=True),
            passive_payload(complete_targets=["arkserver3:Genesis2:27017"]),
            copy_ready=copy_ready,
        )

        self.assertEqual(
            report["status"],
            "blocked_stale_passive_complete_role_triplet_non_evidence",
        )
        self.assertFalse(report["closure"]["ready"])
        self.assertTrue(report["closure"]["source_ready_conflicts_with_blockers"])
        lifecycle = report["runtime_window_lifecycle"]
        self.assertEqual(
            lifecycle["classification"],
            "stale_or_passive_complete_role_triplet_non_evidence_prepare_fresh_player_backed_window",
        )
        self.assertTrue(lifecycle["stale_or_passive_complete_role_triplet_non_evidence"])
        self.assertTrue(lifecycle["exact_copied_lifecycle_event_triplet_complete"])
        self.assertFalse(lifecycle["exact_copied_lifecycle_event_triplet_usable_for_checker"])
        self.assertFalse(lifecycle["copy_bundle_commands_allowed"])
        selector = report["strict_triplet_selector"]
        self.assertEqual(
            selector["selector_result"],
            "rejected_stale_or_passive_complete_role_triplet_non_evidence",
        )
        self.assertFalse(selector["strict_triplet_usable_for_checker"])
        self.assertEqual(
            selector["next_safe_action"],
            "classify_stale_passive_complete_role_triplet_as_non_evidence",
        )
        action = report["machine_next_actions"][0]
        self.assertEqual(
            action["action"],
            "classify_stale_passive_complete_role_triplet_as_non_evidence",
        )
        self.assertEqual(
            action["action_kind"],
            "stale_passive_complete_role_triplet_non_evidence",
        )
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertFalse(action["runner_command_available"])
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])
        serialized_actions = json.dumps(report["machine_next_actions"], sort_keys=True)
        self.assertNotIn("check_player_identity_runtime_principal_lifecycle_approved_evidence.py", serialized_actions)
        self.assertNotIn("build_player_identity_runtime_principal_lifecycle_evidence_bundle.py", serialized_actions)

    def test_missing_bundle_only_synthesizes_read_only_preflight_and_build_blockers(self) -> None:
        bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        evidence_dir = f"/tmp/{RUN_ID}"
        report = self.run_script(
            closure_payload(
                ready=True,
                evidence_dir=evidence_dir,
                missing_artifacts=[bundle],
            )
        )

        self.assertEqual(report["status"], "blocked_missing_required_artifacts")
        self.assertFalse(report["closure"]["ready"])
        self.assertEqual(len(report["machine_next_actions"]), 1)
        action = report["machine_next_actions"][0]
        self.assertEqual(
            action["action"],
            "build_approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(action["artifact"], bundle)
        self.assertEqual(action["command_semantics"], "read_only_bundle_input_preflight")
        self.assertEqual(action["command_status"], "NOT EXECUTED")
        self.assertEqual(
            action["command_text_not_executed"],
            (
                "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py "
                f"--preflight-only --evidence-dir {evidence_dir}"
            ),
        )
        self.assertTrue(action["runner_command_available"])
        self.assertTrue(action["machine_executable"])
        self.assertFalse(action["command_writes_under_evidence_dir"])
        self.assertEqual(
            action["runner_command"]["argv"],
            [
                "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
                "--preflight-only",
                "--evidence-dir",
                evidence_dir,
            ],
        )
        self.assertFalse(action["direct_bundle_builder_command_available"])
        self.assertEqual(
            action["direct_bundle_builder_command_blockers"],
            [
                "bundle_command_obelisk_commit_from_window_manifest_required",
                "reviewed_by_required_for_direct_bundle_command",
                "review_note_required_for_direct_bundle_command",
            ],
        )
        direct_template = action["direct_bundle_builder_command_template"]
        self.assertEqual(
            direct_template["argv"],
            [
                "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
                "--copied-log",
                f"{evidence_dir}/Obelisk.log",
                "--window-manifest",
                f"{evidence_dir}/window-manifest.env",
                "--output-dir",
                f"{evidence_dir}/approved-bundle",
                "--obelisk-commit",
                "<window-manifest-obelisk_commit>",
                "--reviewed-by",
                "<reviewer>",
                "--review-note",
                "<consume-only-review-note>",
            ],
        )
        self.assertTrue(direct_template["path_arguments_resolved"])
        self.assertEqual(
            action["checker_command_after_bundle_template"]["argv"],
            [
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                f"{evidence_dir}/{bundle}",
                "--json",
            ],
        )
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])

    def test_missing_approved_bundle_action_emits_direct_command_when_review_metadata_present(self) -> None:
        bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        evidence_dir = f"/tmp/{RUN_ID}"
        commit = "0123456789abcdef0123456789abcdef01234567"
        report = self.run_script(
            closure_payload(
                ready=True,
                evidence_dir=evidence_dir,
                missing_artifacts=[bundle],
                bundle_command_metadata={
                    "obelisk_commit": commit,
                    "reviewed_by": "status-test",
                    "review_note": "consume-only",
                },
            )
        )

        action = report["machine_next_actions"][0]
        self.assertTrue(action["direct_bundle_builder_command_available"])
        self.assertEqual(action["direct_bundle_builder_command_blockers"], [])
        self.assertFalse(
            action["direct_bundle_builder_command_metadata"][
                "metadata_counts_as_approved_runtime_evidence"
            ]
        )
        direct = action["direct_bundle_builder_command"]
        self.assertIsNotNone(direct)
        self.assertEqual(
            direct["argv"],
            [
                "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
                "--copied-log",
                f"{evidence_dir}/Obelisk.log",
                "--window-manifest",
                f"{evidence_dir}/window-manifest.env",
                "--output-dir",
                f"{evidence_dir}/approved-bundle",
                "--obelisk-commit",
                commit,
                "--reviewed-by",
                "status-test",
                "--review-note",
                "consume-only",
            ],
        )
        self.assertNotIn(
            "<window-manifest-obelisk_commit>",
            direct["command_text_not_executed"],
        )
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])

    def test_ready_closure_without_exact_triplet_state_cannot_route_checker(self) -> None:
        closure = closure_payload(ready=True)
        closure.pop("lifecycle_event_role_state")
        closure.pop("exact_copied_lifecycle_event_triplet_complete")
        closure.pop("missing_copied_lifecycle_event_triplet")
        closure.pop("missing_copied_lifecycle_event_triplet_labels")

        report = self.run_script(
            closure,
            passive_payload(complete_targets=["arkserver3:Genesis2:27017"]),
        )

        self.assertEqual(report["status"], "blocked_missing_exact_copied_lifecycle_triplet")
        self.assertFalse(report["closure"]["ready"])
        self.assertTrue(report["closure"]["source_ready_conflicts_with_blockers"])
        self.assertFalse(report["closure_consistency"]["ready_for_checker"])
        self.assertEqual(
            report["closure"]["missing_copied_lifecycle_event_triplet_labels"],
            list(status_report.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
        )
        self.assertEqual(
            report["next_actions"][0]["action"],
            "rerun_closure_request_with_exact_copied_triplet_match",
        )
        self.assertEqual(
            report["machine_next_actions"][0]["action"],
            "rerun_closure_request_with_exact_copied_triplet_match",
        )
        self.assertNotIn(
            "approved_evidence.py",
            str(report["exact_next_command"].get("command_text_not_executed")),
        )
        self.assertFalse(report["exact_next_command"]["runner_command_available"])
        self.assertIsNone(report["exact_next_command"]["runner_command"])
        self.assertIsNone(report["exact_next_command"]["structured_argv"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])

    def test_ready_closure_with_triplet_missing_safe_fields_cannot_route_checker(self) -> None:
        closure = closure_payload(ready=True)
        role_state = closure["lifecycle_event_role_state"]
        assert isinstance(role_state, dict)
        matched = role_state["matched_copied_lifecycle_event_triplet"]
        assert isinstance(matched, list)
        for observed in matched:
            assert isinstance(observed, dict)
            observed.pop("principal_id_logged", None)

        report = self.run_script(
            closure,
            passive_payload(complete_targets=["arkserver3:Genesis2:27017"]),
        )

        self.assertEqual(report["status"], "blocked_missing_exact_copied_lifecycle_triplet")
        self.assertFalse(report["closure"]["ready"])
        self.assertTrue(report["closure"]["source_ready_conflicts_with_blockers"])
        self.assertFalse(report["closure_consistency"]["ready_for_checker"])
        self.assertEqual(
            report["closure"]["missing_copied_lifecycle_event_triplet_labels"],
            list(status_report.REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
        )
        self.assertEqual(
            report["machine_next_actions"][0]["action"],
            "rerun_closure_request_with_exact_copied_triplet_match",
        )
        self.assertNotIn(
            "approved_evidence.py",
            str(report["exact_next_command"].get("command_text_not_executed")),
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])

    def test_closure_machine_next_actions_are_normalized_for_status_routing(self) -> None:
        closure = closure_payload(
            missing_roles=["session_end"],
            machine_next_actions=[
                {
                    "action_id": "closure.missing:lifecycle-role_session_end",
                    "action": "continue_or_request_passive_wait_for_missing_lifecycle_role",
                    "artifact": "lifecycle-role/session_end",
                    "role": "session_end",
                    "command_status": "NOT EXECUTED",
                    "command_text_not_executed": "scripts/monitor_ark_player_presence_passive.sh --interval 10 arkserver3:Genesis2:27017",
                    "approved_runtime_evidence": True,
                    "runtime_ready": True,
                    "counts_as_approved_runtime_evidence": True,
                }
            ],
        )

        report = self.run_script(closure, passive_payload(players_current=1))

        self.assertEqual(report["status"], "blocked_missing_lifecycle_roles")
        action = report["machine_next_actions"][0]
        self.assertEqual(action["action"], "continue_or_request_passive_wait_for_missing_lifecycle_role")
        self.assertEqual(action["role"], "session_end")
        self.assertIn("monitor_ark_player_presence_passive.sh", action["command_text_not_executed"])
        self.assertEqual(action["status_report_source"], "closure.machine_next_actions")
        self.assertTrue(action["selected_by_status_report"])
        self.assertFalse(action["accepted_by_status_report"])
        self.assertEqual(
            action["accepted_by_status_report_reason"],
            "routing_only_closure_action_not_evidence_acceptance",
        )
        self.assertFalse(action["partial_lifecycle_roles_count_as_complete_closure_material"])
        self.assertFalse(action["diagnostic_or_rejected_lifecycle_lines_count_as_complete_closure_material"])
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(action["runtime_ready"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["closure"]["machine_next_actions"][0]["approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_consumes_player_principal_start_end_split_as_non_counting_next_action(self) -> None:
        report = self.run_script(
            closure_payload(missing_roles=["session_start_rejected"]),
            passive_payload(players_current=1),
            player_principal_evidence_split=start_end_split_payload(),
        )

        split = report["player_principal_evidence_split"]
        self.assertTrue(split["present"])
        self.assertEqual(
            split["classification"],
            "start_end_contract_input_present_rejected_start_missing_non_evidence",
        )
        self.assertTrue(split["start_end_contract_input_accepted"])
        self.assertTrue(split["session_start_rejected_missing"])
        self.assertIn(
            "runtime.lifecycle_rejected_start_evidence_missing",
            split["blockers"],
        )
        self.assertFalse(split["approved_runtime_evidence"])
        self.assertFalse(split["counts_as_approved_runtime_evidence"])

        action = report["machine_next_actions"][0]
        self.assertEqual(
            action["action"],
            "supply_exact_checkjoininprogress_session_start_rejected_for_strict_triplet",
        )
        self.assertEqual(
            action["action_kind"],
            "player_principal_evidence_split_missing_rejected_start",
        )
        self.assertEqual(action["role"], "session_start_rejected")
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertFalse(action["runner_command_available"])
        self.assertFalse(action["machine_executable"])
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])

    def test_player_principal_split_alias_overclaim_is_reported_without_readiness(self) -> None:
        report = self.run_script(
            closure_payload(missing_roles=["session_start_rejected"]),
            player_principal_evidence_split=start_end_split_payload(include_overclaim_alias=True),
        )

        split = report["player_principal_evidence_split"]
        self.assertTrue(split["present"])
        self.assertEqual(
            split["classification"],
            "player_principal_evidence_split_overclaim_blocked_non_evidence",
        )
        self.assertEqual(split["positive_alias_claim_paths"], ["$.audit_alias"])
        self.assertIn(
            "player_principal_evidence_split_positive_alias_claim",
            split["blockers"],
        )
        self.assertEqual(
            report["machine_next_actions"][0]["action"],
            "review_player_principal_evidence_split_overclaim_aliases_offline",
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["public_sdk_ready"])

    def test_player_principal_split_direct_alias_overclaims_are_blocked(self) -> None:
        split_payload = start_end_split_payload()
        split_payload["approvedRuntimeEvidenceReady"] = True
        split_payload["publicSdkReady"] = True
        split_payload["runtimeReady"] = True
        split_payload["sdkProgress"] = 1
        split_payload["p0Progress"] = "1/4"
        split_payload["analysis"] = {
            "countsAsApprovedRuntimeEvidence": True,
            "startEndOnlyCountsAsApprovedRuntimeEvidence": "ready",
            "completeSdkProgressRatio": "1/12",
        }

        report = self.run_script(
            closure_payload(missing_roles=["session_start_rejected"]),
            player_principal_evidence_split=split_payload,
        )

        split = report["player_principal_evidence_split"]
        self.assertTrue(split["present"])
        self.assertTrue(split["start_end_contract_input_accepted"])
        self.assertEqual(
            split["classification"],
            "player_principal_evidence_split_overclaim_blocked_non_evidence",
        )
        self.assertIn(
            "player_principal_evidence_split_positive_alias_claim",
            split["blockers"],
        )
        self.assertIn(
            "player_principal_evidence_split_direct_alias_overclaim",
            split["blockers"],
        )
        self.assertIn("$.approvedRuntimeEvidenceReady", split["direct_positive_alias_claim_paths"])
        self.assertIn("$.publicSdkReady", split["direct_positive_alias_claim_paths"])
        self.assertIn("$.runtimeReady", split["direct_positive_alias_claim_paths"])
        self.assertIn(
            "$.analysis.countsAsApprovedRuntimeEvidence",
            split["direct_positive_alias_claim_paths"],
        )
        self.assertIn("$.sdkProgress", split["direct_progress_alias_claim_paths"])
        self.assertIn("$.p0Progress", split["direct_progress_alias_claim_paths"])
        self.assertIn(
            "$.analysis.completeSdkProgressRatio",
            split["direct_progress_alias_claim_paths"],
        )
        self.assertEqual(
            report["machine_next_actions"][0]["action"],
            "review_player_principal_evidence_split_overclaim_aliases_offline",
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_player_principal_split_lifecycle_role_alias_overclaim_is_reported(self) -> None:
        split_payload = start_end_split_payload()
        split_payload["role_alias"] = {
            "alias": "session_start_rejected",
            "target": "ShooterGameMode.CheckJoinInProgress",
            "counts_as_role": True,
        }

        report = self.run_script(
            closure_payload(missing_roles=["session_start_rejected"]),
            player_principal_evidence_split=split_payload,
        )

        split = report["player_principal_evidence_split"]
        self.assertEqual(
            split["classification"],
            "player_principal_evidence_split_overclaim_blocked_non_evidence",
        )
        self.assertIn(
            "player_principal_evidence_split_lifecycle_role_alias_claim",
            split["blockers"],
        )
        self.assertIn("$.role_alias", split["lifecycle_role_alias_claim_paths"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_split_status_only_runs_without_closure_or_evidence_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            split_path = tmp_path / "split.json"
            route_path = tmp_path / "route.json"
            output_path = tmp_path / "runtime-status.json"
            write_json(split_path, start_end_split_payload())
            write_json(route_path, route_gate_payload())

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--player-principal-evidence-split-json",
                    str(split_path),
                    "--recorded-standing-debug-authority",
                    "--standing-debug-authority-reference",
                    "CURRENT.md",
                    "--standing-debug-authority-source",
                    "handoff",
                    "--route-gate-json",
                    str(route_path),
                    "--json-output",
                    str(output_path),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output_path.exists())
            report = json.loads(result.stdout)
            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(written["schema"], status_report.SCHEMA)
        self.assertEqual(
            report["closure"]["schema"],
            status_report.STATUS_ONLY_CLOSURE_CONTEXT_SCHEMA,
        )
        self.assertEqual(report["status"], "blocked_invalid_closure_report_schema")
        split = report["player_principal_evidence_split"]
        self.assertTrue(split["present"])
        self.assertEqual(
            split["classification"],
            "start_end_contract_input_present_rejected_start_missing_non_evidence",
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_invalid_passive_monitor_root_routes_to_closure_compatible_staging_not_checker(self) -> None:
        source_dir = "/tmp/live-validation-logs/20260607T071833Z-postpatch-ragnarok-theisland-monitor"
        closure_dir = "/tmp/live-validation-logs/20260607T071833Z-player-principal-lifecycle"
        guidance = {
            "schema": "obelisk.player-principal-lifecycle-closure-compatible-copy-guidance.v1",
            "source_evidence_dir": source_dir,
            "source_run_id": "20260607T071833Z-postpatch-ragnarok-theisland-monitor",
            "source_looks_like_passive_monitor_root": True,
            "suggested_closure_run_id": "20260607T071833Z-player-principal-lifecycle",
            "suggested_closure_evidence_dir": closure_dir,
            "suggested_valid_closure_run_id": "20260607T071833Z-player-principal-lifecycle",
            "suggested_valid_closure_evidence_dir": closure_dir,
            "passive_monitor_root_must_not_be_used_as_closure_evidence_dir": True,
            "passive_monitor_root_accepted_as_closure_evidence_dir": False,
            "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
            "counts_as_approved_runtime_evidence": False,
        }
        closure = closure_payload(
            ready=True,
            evidence_dir=source_dir,
            evidence_source_blockers=[
                {
                    "reason": "invalid_player_principal_lifecycle_run_id",
                    "path": source_dir,
                    "source_looks_like_passive_monitor_root": True,
                    "closure_compatible_copy_guidance": guidance,
                    "counts_as_approved_runtime_evidence": False,
                }
            ],
            machine_next_actions=[
                {
                    "action_id": "closure.missing:invalid_source",
                    "action": "stage_closure_compatible_player_principal_lifecycle_evidence_root",
                    "action_kind": "invalid_evidence_source",
                    "missing_kind": "invalid_evidence_source",
                    "artifact": source_dir,
                    "items": [source_dir],
                    "source_evidence_dir": source_dir,
                    "closure_compatible_evidence_dir": closure_dir,
                    "evidence_dir": closure_dir,
                    "closure_compatible_copy_guidance": guidance,
                    "command_text_not_executed": (
                        "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py "
                        f"--evidence-dir {closure_dir} --format json"
                    ),
                    "requires_operator_authority_before_execution": True,
                    "operator_authority_source_required": "fresh_current_turn_operator_message",
                    "requires_current_turn_operator_approval": True,
                    "requires_fresh_current_turn_operator_approval": True,
                    "standing_launch_authority_covers_target_run": False,
                    "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
                    "explicit_execution_write_flags_required": True,
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": True,
                    "runtime_ready": True,
                }
            ],
        )

        report = self.run_script(closure, passive_payload(complete_targets=["arkserver3:Genesis2:27017"]))

        self.assertEqual(report["status"], "blocked_invalid_evidence_source")
        self.assertFalse(report["closure"]["ready"])
        self.assertEqual(report["next_actions"][0]["action"], "stage_closure_compatible_player_principal_lifecycle_evidence_root")
        self.assertEqual(report["next_actions"][0]["source_evidence_dir"], source_dir)
        self.assertEqual(report["next_actions"][0]["closure_compatible_evidence_dir"], closure_dir)
        self.assertFalse(report["next_actions"][0]["passive_monitor_root_accepted_as_closure_evidence_dir"])
        self.assertEqual(report["machine_next_actions"][0]["action"], "stage_closure_compatible_player_principal_lifecycle_evidence_root")
        self.assertEqual(report["machine_next_actions"][0]["action_kind"], "invalid_evidence_source")
        self.assertEqual(report["machine_next_actions"][0]["source_evidence_dir"], source_dir)
        self.assertEqual(report["machine_next_actions"][0]["closure_compatible_evidence_dir"], closure_dir)
        self.assertEqual(report["machine_next_actions"][0]["suggested_valid_closure_evidence_dir"], closure_dir)
        self.assertEqual(report["machine_next_actions"][0]["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", report["machine_next_actions"][0])
        self.assertFalse(
            report["machine_next_actions"][0]["machine_action_suggested_for_invalid_passive_root"]
        )
        self.assertFalse(report["machine_next_actions"][0]["machine_executable"])
        self.assertFalse(report["machine_next_actions"][0]["runner_command_available"])
        self.assertFalse(report["machine_next_actions"][0]["approved_runtime_evidence"])
        self.assertFalse(report["machine_next_actions"][0]["runtime_ready"])
        self.assertNotIn("approved_runtime_evidence_checker", str(report["machine_next_actions"][0]))
        self.assertEqual(
            report["operator_action_summary"]["actions_allowed_under_recorded_standing_debug_authority"],
            [],
        )
        self.assertFalse(report["approved_runtime_evidence"])

    def test_invalid_passive_monitor_root_with_zero_players_stays_manual_staging_only(self) -> None:
        source_dir = "/tmp/live-validation-logs/20260607T071833Z-postpatch-ragnarok-theisland-monitor"
        closure_dir = "/tmp/live-validation-logs/20260607T071833Z-player-principal-lifecycle"
        guidance = {
            "schema": "obelisk.player-principal-lifecycle-closure-compatible-copy-guidance.v1",
            "source_evidence_dir": source_dir,
            "source_root_role": "source_evidence_root_supplied_to_closure_helper",
            "source_run_id": "20260607T071833Z-postpatch-ragnarok-theisland-monitor",
            "source_looks_like_passive_monitor_root": True,
            "suggested_valid_closure_run_id": "20260607T071833Z-player-principal-lifecycle",
            "suggested_valid_closure_evidence_dir": closure_dir,
            "suggested_valid_closure_root_role": "suggested_valid_closure_root_for_manual_staging",
            "passive_monitor_root_must_not_be_used_as_closure_evidence_dir": True,
            "passive_monitor_root_accepted_as_closure_evidence_dir": False,
            "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
            "counts_as_approved_runtime_evidence": False,
        }
        stale_machine_action = {
            "action_id": "closure.missing:invalid_source",
            "action": "stage_closure_compatible_player_principal_lifecycle_evidence_root",
            "action_kind": "invalid_evidence_source",
            "missing_kind": "invalid_evidence_source",
            "artifact": source_dir,
            "items": [source_dir],
            "source_evidence_dir": source_dir,
            "invalid_source_evidence_dir": source_dir,
            "closure_compatible_evidence_dir": closure_dir,
            "suggested_valid_closure_evidence_dir": closure_dir,
            "closure_compatible_copy_guidance": guidance,
            "command_status": "NOT EXECUTED",
            "command_text_not_executed": (
                "scripts/monitor_ark_player_presence_passive.sh --interval 10 "
                "--linger-after-detect 900 --no-details arkserver3:Genesis2:27017"
            ),
            "requires_operator_authority_before_execution": True,
            "operator_authority_source_required": "fresh_current_turn_operator_message",
            "requires_current_turn_operator_approval": True,
            "requires_fresh_current_turn_operator_approval": True,
            "authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": True,
            "runtime_ready": True,
        }
        closure = closure_payload(
            ready=True,
            evidence_dir=source_dir,
            missing_roles=["session_start", "session_start_rejected", "session_end"],
            missing_artifacts=[
                "window-manifest.env",
                "preflight-post.json",
                "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            ],
            evidence_source_blockers=[
                {
                    "reason": "invalid_player_principal_lifecycle_run_id",
                    "path": source_dir,
                    "source_looks_like_passive_monitor_root": True,
                    "closure_compatible_copy_guidance": guidance,
                    "counts_as_approved_runtime_evidence": False,
                }
            ],
            machine_next_actions=[stale_machine_action],
        )

        report = self.run_script(closure, passive_payload(players_current=0))

        self.assertEqual(report["status"], "blocked_invalid_evidence_source")
        self.assertFalse(report["closure"]["ready"])
        self.assertEqual(
            report["runtime_player_availability"]["classification"],
            "no_players_currently_detected_wait_for_testers_non_evidence",
        )
        self.assertTrue(report["runtime_player_availability"]["no_players_currently_detected"])
        self.assertFalse(report["runtime_player_availability"]["approved_runtime_evidence"])
        self.assertEqual(len(report["next_actions"]), 1)
        self.assertEqual(
            report["next_actions"][0]["action"],
            "stage_closure_compatible_player_principal_lifecycle_evidence_root",
        )
        self.assertFalse(report["next_actions"][0]["machine_action_suggested_for_invalid_passive_root"])
        self.assertEqual(len(report["machine_next_actions"]), 1)
        action = report["machine_next_actions"][0]
        self.assertEqual(action["action_kind"], "invalid_evidence_source")
        self.assertEqual(action["source_evidence_dir"], source_dir)
        self.assertEqual(action["suggested_valid_closure_evidence_dir"], closure_dir)
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", action)
        self.assertFalse(action["machine_action_suggested_for_invalid_passive_root"])
        self.assertFalse(action["machine_executable"])
        self.assertFalse(action["runner_command_available"])
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(action["runtime_ready"])
        self.assertEqual(
            report["operator_action_summary"]["actions_allowed_under_recorded_standing_debug_authority"],
            [],
        )
        serialized = json.dumps(report, sort_keys=True)
        self.assertNotIn("monitor_ark_player_presence_passive.sh", serialized)
        self.assertNotIn("approved_runtime_evidence_checker", serialized)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_conflicting_ready_closure_missing_role_uses_exact_missing_role_command(self) -> None:
        closure = closure_payload(
            ready=True,
            missing_roles=["session_end"],
            machine_next_actions=[
                {
                    "action_id": "closure.checker:stale",
                    "action": "run_approved_runtime_evidence_checker_on_copied_manifest",
                    "action_kind": "checker",
                    "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                    "command_status": "NOT EXECUTED",
                    "command_text_not_executed": (
                        "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py "
                        "--json /tmp/stale/approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
                    ),
                    "approved_runtime_evidence": True,
                    "runtime_ready": True,
                },
                {
                    "action_id": "closure.missing:lifecycle-role_session_end",
                    "action": "continue_or_request_passive_wait_for_missing_lifecycle_role",
                    "action_kind": "lifecycle_event_role",
                    "artifact": "lifecycle-role/session_end",
                    "role": "session_end",
                    "command_status": "NOT EXECUTED",
                    "command_text_not_executed": (
                        "scripts/monitor_ark_player_presence_passive.sh --interval 10 "
                        "--linger-after-detect 900 --no-details arkserver3:Genesis2:27017"
                    ),
                    "approved_runtime_evidence": True,
                    "counts_as_approved_runtime_evidence": True,
                },
            ],
        )

        report = self.run_script(
            closure,
            passive_payload(complete_targets=["arkserver3:Genesis2:27017"], players_current=1),
        )

        self.assertEqual(report["status"], "blocked_missing_lifecycle_roles")
        self.assertFalse(report["closure"]["ready"])
        self.assertTrue(report["closure"]["source_ready_conflicts_with_blockers"])
        self.assertTrue(report["closure"]["source_claims_ignored_for_status"])
        self.assertTrue(report["closure_consistency"]["source_ready_conflicts_with_blockers"])
        self.assertFalse(report["closure_consistency"]["ready_for_checker"])
        self.assertEqual(
            report["closure_consistency"]["blocking_inputs"]["missing_lifecycle_event_roles"],
            ["session_end"],
        )
        self.assertEqual(len(report["machine_next_actions"]), 1)
        action = report["machine_next_actions"][0]
        self.assertEqual(
            action["action"],
            "continue_or_request_passive_wait_for_missing_lifecycle_role",
        )
        self.assertEqual(action["role"], "session_end")
        self.assertIn("monitor_ark_player_presence_passive.sh", action["command_text_not_executed"])
        self.assertFalse(action["approved_runtime_evidence"])
        self.assertFalse(action["runtime_ready"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["first_machine_next_action"]["action_id"], action["action_id"])
        self.assertTrue(report["exact_next_command"]["exact_command_available"])
        self.assertNotIn("approved_evidence.py", report["exact_next_command"]["command_text_not_executed"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])

    def test_conflicting_ready_copied_log_only_closure_uses_bundle_command_not_checker(self) -> None:
        bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        closure = closure_payload(
            ready=True,
            missing_artifacts=[bundle],
            machine_next_actions=[
                {
                    "action_id": "closure.checker:stale",
                    "action": "run_approved_runtime_evidence_checker_on_copied_manifest",
                    "action_kind": "checker",
                    "artifact": bundle,
                    "command_status": "NOT EXECUTED",
                    "command_text_not_executed": (
                        "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py "
                        "--json /tmp/stale/approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
                    ),
                },
                {
                    "action_id": "closure.missing:approved-bundle_approved-runtime-principal-lifecycle-evidence.json",
                    "action": "build_approved_runtime_principal_lifecycle_evidence_bundle",
                    "action_kind": "missing_artifact",
                    "artifact": bundle,
                    "items": [bundle],
                    "command_status": "NOT EXECUTED",
                    "command_text_not_executed": (
                        "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py "
                        "--copied-log /tmp/run/Obelisk.log --window-manifest /tmp/run/window-manifest.env "
                        "--output-dir /tmp/run/approved-bundle --obelisk-commit reviewed --reviewed-by reviewer "
                        "--review-note consume-only"
                    ),
                    "approved_runtime_evidence": True,
                    "runtime_ready": True,
                },
            ],
        )
        copy_ready = {
            "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
            "status": "copied",
            "copy_readiness": "ready_complete_role_triplet",
            "ready_to_copy": True,
            "copied": True,
            "roles_present": ["session_start", "session_start_rejected", "session_end"],
            "missing_roles": [],
            "approved_runtime_evidence": True,
        }

        report = self.run_script(closure, copy_ready=copy_ready)

        self.assertEqual(report["status"], "blocked_missing_required_artifacts")
        self.assertFalse(report["closure"]["ready"])
        self.assertTrue(report["closure"]["source_ready_conflicts_with_blockers"])
        self.assertTrue(report["copy_ready_log"]["copied_source_value"])
        self.assertFalse(report["copy_ready_log"]["copied"])
        self.assertFalse(report["copy_ready_log"]["approved_runtime_evidence"])
        action = report["machine_next_actions"][0]
        self.assertEqual(action["action"], "build_approved_runtime_principal_lifecycle_evidence_bundle")
        self.assertIn("build_player_identity_runtime_principal_lifecycle_evidence_bundle.py", action["command_text_not_executed"])
        self.assertEqual(report["exact_next_command"]["action"], action["action"])
        self.assertTrue(report["exact_next_command"]["exact_command_available"])
        self.assertNotIn("approved_evidence.py", report["exact_next_command"]["command_text_not_executed"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_rejects_passive_notice_status_shortcut_json_as_closure_input(self) -> None:
        cases = (
            "obelisk.player-principal-passive-shortcut.v1",
            "obelisk.player-principal-lifecycle-beta-notice-shortcut.v1",
            "obelisk.player-principal-lifecycle-status-shortcut.v1",
            "obelisk.player-principal-lifecycle-watcher-context.v1",
        )
        for schema in cases:
            with self.subTest(schema=schema):
                report = self.run_script(
                    {
                        "schema": schema,
                        "status": "accepted",
                        "ready": True,
                        "approved_runtime_evidence": True,
                    },
                    passive_payload(complete_targets=["arkserver3:Genesis2:27017"]),
                )

                self.assertEqual(report["status"], "blocked_invalid_closure_report_schema")
                self.assertFalse(report["approved_runtime_evidence"])
                self.assertFalse(report["closure"]["schema_valid"])
                self.assertFalse(report["closure"]["ready"])
                self.assertFalse(report["closure"]["approved_runtime_evidence"])
                self.assertTrue(report["closure"]["source_report_claims"]["ready"])
                self.assertTrue(report["closure"]["source_report_claims"]["approved_runtime_evidence"])
                self.assertTrue(report["closure"]["source_claims_ignored_for_status"])
                self.assertEqual(report["closure"]["schema_blocker"]["schema"], schema)
                self.assertEqual(
                    report["next_actions"][0]["action"],
                    "rerun_closure_request_with_exact_closure_helper",
                )
                machine_action = report["machine_next_actions"][0]
                self.assertEqual(machine_action["action_kind"], "invalid_closure_schema")
                self.assertEqual(machine_action["required_script"], "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py")
                self.assertFalse(machine_action["approved_runtime_evidence"])
                self.assertFalse(machine_action["counts_as_approved_runtime_evidence"])

    def test_source_positive_passive_flags_do_not_become_status_claims(self) -> None:
        passive = passive_payload(complete_targets=["arkserver3:Genesis2:27017"], players_current=1)
        passive["approved_runtime_evidence"] = True
        passive["ready"] = True
        route_gate = route_gate_payload()
        route_gate["runtime_ready"] = True
        route_gate["public_sdk_ready"] = True
        route_gate["promotion_ready"] = True
        report = self.run_script(
            closure_payload(
                missing_roles=["session_start"],
                missing_artifacts=["window-manifest.env"],
            ),
            passive,
            route_gate=route_gate,
        )

        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["passive"]["approved_runtime_evidence"])
        self.assertFalse(report["passive"]["ready"])
        self.assertFalse(report["passive"]["counts_as_approved_runtime_evidence"])
        self.assertTrue(report["passive"]["source_report_claims"]["approved_runtime_evidence"])
        self.assertTrue(report["passive"]["source_report_claims"]["ready"])
        self.assertTrue(report["passive"]["source_claims_ignored_for_status"])
        self.assertFalse(report["route_gate"]["runtime_ready"])
        self.assertFalse(report["route_gate"]["public_sdk_ready"])
        self.assertFalse(report["route_gate"]["promotion_ready"])
        self.assertTrue(report["route_gate"]["source_report_claims"]["runtime_ready"])
        self.assertTrue(report["route_gate"]["source_report_claims"]["public_sdk_ready"])
        self.assertTrue(report["route_gate"]["source_report_claims"]["promotion_ready"])
        self.assertTrue(report["route_gate"]["source_claims_ignored_for_status"])
        self.assertTrue(
            all(
                value is False
                for value in report["operator_action_summary"]["evidence_readiness_claims"].values()
            )
        )

    def test_operator_actions_allowed_by_standing_authority_stay_no_claims(self) -> None:
        report = self.run_script(
            closure_payload(
                missing_roles=["session_start", "session_start_rejected", "session_end"],
                missing_artifacts=["preflight-post.json"],
            ),
            passive_payload(players_current=1),
        )

        summary = report["operator_action_summary"]
        for action in summary["actions_allowed_under_recorded_standing_debug_authority"]:
            self.assertTrue(action["allowed_under_recorded_standing_debug_authority"])
            self.assertFalse(action["authorized_by_this_report"])
            self.assertFalse(action["server_operations_authorized_by_this_report"])
            self.assertFalse(action["runtime_work_authorized_by_this_report"])
            self.assertFalse(action["marker_env_changes_authorized_by_this_report"])
            self.assertFalse(action["workspace_writes_authorized_by_this_report"])
            self.assertFalse(action["creates_sidecars_by_this_report"])
            self.assertFalse(action["counts_as_approved_runtime_evidence"])
            self.assertFalse(action["counts_as_runtime_evidence"])
            self.assertFalse(action["counts_as_sdk_evidence"])
            self.assertFalse(action["grants_readiness_claims"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["workspace_writes_authorized"])
        self.assertFalse(report["marker_env_changes_authorized"])

    def test_unknown_player_counts_are_wait_state_not_evidence(self) -> None:
        monitor_log = "\n".join(
            [
                "tick utc=2026-06-06T08:00:00Z",
                "query instance=arkserver3 map=Genesis2 query_port=27017 status=warning "
                "target_key=arkserver3:Genesis2:27017 presence_detected=false "
                "detection_source=gamedig_ase_query",
                "",
            ]
        )

        report = self.run_script(
            closure_payload(missing_roles=["session_end"]),
            monitor_log=monitor_log,
        )

        availability = report["runtime_player_availability"]
        self.assertEqual(
            availability["classification"],
            "player_count_unknown_wait_for_clear_signal_non_evidence",
        )
        self.assertEqual(
            availability["unknown_player_count_targets"],
            ["arkserver3:Genesis2:27017"],
        )
        self.assertTrue(availability["unknown_player_context"])
        self.assertFalse(availability["no_players_currently_detected"])
        self.assertFalse(availability["no_users_confirmed"])
        self.assertFalse(availability["players_detected"])
        self.assertFalse(availability["approved_runtime_evidence"])
        self.assertFalse(availability["counts_as_approved_runtime_evidence"])
        self.assertFalse(availability["runtime_ready"])

    def test_gamedig_zero_with_rcon_timeout_is_unknown_not_confirmed_empty(self) -> None:
        monitor_log = "\n".join(
            [
                "tick utc=2026-06-06T08:00:00Z",
                "query instance=arkserver3 map=Genesis2 query_port=27017 status=ok "
                "current_map=Genesis2 players=0/70 target_key=arkserver3:Genesis2:27017 "
                "players_current=0 players_max=70 presence_detected=false "
                "detection_source=gamedig_ase_query",
                "rcon_listplayers instance=arkserver3 map=Genesis2 query_port=27017 "
                "rcon_port=27022 status=timeout rc=1 error=timeout "
                "target_key=arkserver3:Genesis2:27017 presence_detected=false "
                "detection_source=rcon_listplayers_redacted rcon_output_redacted=true",
                "",
            ]
        )

        report = self.run_script(
            closure_payload(missing_roles=["session_end"]),
            monitor_log=monitor_log,
        )

        availability = report["runtime_player_availability"]
        self.assertEqual(
            availability["classification"],
            "player_count_unknown_wait_for_clear_signal_non_evidence",
        )
        self.assertEqual(
            availability["known_zero_player_targets"],
            ["arkserver3:Genesis2:27017"],
        )
        self.assertEqual(
            availability["unknown_player_count_targets"],
            ["arkserver3:Genesis2:27017"],
        )
        self.assertTrue(availability["unknown_player_context"])
        self.assertFalse(availability["no_players_currently_detected"])
        self.assertFalse(availability["no_users_confirmed"])
        self.assertFalse(availability["players_detected"])
        summary_context = report["operator_action_summary"]["operator_context_inputs"]
        self.assertFalse(summary_context["no_players_currently_detected"])
        self.assertEqual(
            summary_context["player_availability_classification"],
            "player_count_unknown_wait_for_clear_signal_non_evidence",
        )
        self.assertFalse(report["approved_runtime_evidence"])

    def test_expired_observer_gate_only_window_closes_non_evidence_without_copy_bundle_commands(self) -> None:
        bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        closure = closure_payload(
            ready=True,
            missing_roles=["session_start", "session_end"],
            missing_artifacts=[bundle],
            machine_next_actions=[
                {
                    "action_id": "closure.missing:approved-bundle",
                    "action": "build_approved_runtime_principal_lifecycle_evidence_bundle",
                    "action_kind": "missing_artifact",
                    "artifact": bundle,
                    "items": [bundle],
                    "command_status": "NOT EXECUTED",
                    "command_text_not_executed": (
                        "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py "
                        "--copied-log /tmp/window/Obelisk.log --window-manifest /tmp/window/window-manifest.env "
                        "--output-dir /tmp/window/approved-bundle --obelisk-commit reviewed "
                        "--reviewed-by reviewer --review-note consume-only"
                    ),
                    "approved_runtime_evidence": True,
                    "runtime_ready": True,
                }
            ],
        )

        report = self.run_script(
            closure,
            copy_ready=copy_ready_window_payload(
                window_state="post_window",
                roles_present=["session_start_rejected"],
                missing_roles=["session_start", "session_end"],
            ),
        )

        self.assertEqual(
            report["status"],
            "blocked_expired_runtime_window_non_evidence_prepare_fresh_player_backed_window",
        )
        lifecycle = report["runtime_window_lifecycle"]
        self.assertEqual(
            lifecycle["classification"],
            "expired_runtime_window_non_evidence_prepare_fresh_player_backed_window",
        )
        self.assertTrue(lifecycle["observer_gate_only"])
        self.assertTrue(lifecycle["close_or_classify_as_non_evidence"])
        self.assertTrue(lifecycle["expired_no_evidence"])
        self.assertFalse(lifecycle["accepted_ready_for_checker"])
        self.assertTrue(report["expired_runtime_window_non_evidence"])
        acceptance = report["runtime_evidence_acceptance_state"]
        self.assertEqual(acceptance["classification"], "expired_window_no_evidence")
        self.assertTrue(acceptance["expired_no_evidence"])
        self.assertFalse(acceptance["accepted_ready_for_checker"])
        self.assertFalse(acceptance["checker_accepted_ready"])
        self.assertFalse(acceptance["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["active_runtime_window_waiting_for_exact_triplet"])
        self.assertTrue(report["copy_bundle_commands_suppressed_until_exact_triplet"])
        action = report["machine_next_actions"][0]
        self.assertEqual(action["action"], "close_expired_player_principal_lifecycle_window_as_non_evidence")
        self.assertEqual(action["action_kind"], "expired_runtime_window_non_evidence_closure")
        self.assertTrue(action["prepare_fresh_player_backed_window_required"])
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", action)
        self.assertFalse(action["runner_command_available"])
        self.assertEqual(
            action["next_player_backed_window"]["diagnostic_candidates"],
            "disabled",
        )
        serialized = json.dumps(report, sort_keys=True)
        self.assertNotIn("build_player_identity_runtime_principal_lifecycle_evidence_bundle.py", serialized)
        self.assertNotIn("check_player_identity_runtime_principal_lifecycle_approved_evidence.py", serialized)
        self.assertNotIn("copy_player_principal_lifecycle_ready_log.py", serialized)
        self.assertFalse(report["approved_runtime_evidence"])

    def test_expired_diagnostic_only_window_routes_non_evidence_without_bundle_command(self) -> None:
        closure = closure_payload(
            ready=True,
            missing_roles=["session_start", "session_start_rejected", "session_end"],
            machine_next_actions=[
                {
                    "action_id": "closure.checker:stale",
                    "action": "run_approved_runtime_evidence_checker_on_copied_manifest",
                    "action_kind": "checker",
                    "command_status": "NOT EXECUTED",
                    "command_text_not_executed": (
                        "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py "
                        "--json /tmp/stale/approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
                    ),
                }
            ],
        )

        report = self.run_script(
            closure,
            copy_ready=copy_ready_window_payload(
                window_state="post_window",
                roles_present=[],
                missing_roles=["session_start", "session_start_rejected", "session_end"],
                copy_readiness="blocked_diagnostic_or_rejected_lifecycle_lines",
                accepted_count=0,
                rejected_count=2,
            ),
        )

        self.assertEqual(
            report["status"],
            "blocked_expired_runtime_window_non_evidence_prepare_fresh_player_backed_window",
        )
        lifecycle = report["runtime_window_lifecycle"]
        self.assertTrue(lifecycle["diagnostic_only_lifecycle_lines"])
        self.assertTrue(lifecycle["close_or_classify_as_non_evidence"])
        action = report["machine_next_actions"][0]
        self.assertEqual(action["action_kind"], "expired_runtime_window_non_evidence_closure")
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", action)
        self.assertNotIn("approved_evidence.py", json.dumps(report, sort_keys=True))
        self.assertFalse(report["approved_runtime_evidence"])

    def test_active_observer_gate_window_stays_waiting_not_closure_ready(self) -> None:
        report = self.run_script(
            closure_payload(
                missing_roles=["session_start", "session_end"],
                missing_artifacts=["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"],
            ),
            copy_ready=copy_ready_window_payload(
                window_state="in_progress",
                roles_present=["session_start_rejected"],
                missing_roles=["session_start", "session_end"],
            ),
        )

        self.assertEqual(
            report["status"],
            "blocked_active_runtime_window_waiting_for_exact_copied_triplet",
        )
        lifecycle = report["runtime_window_lifecycle"]
        self.assertEqual(
            lifecycle["classification"],
            "active_runtime_window_waiting_for_exact_copied_triplet_or_window_end",
        )
        self.assertTrue(lifecycle["active_waiting_not_closure_ready"])
        self.assertFalse(lifecycle["close_or_classify_as_non_evidence"])
        self.assertFalse(report["expired_runtime_window_non_evidence"])
        self.assertTrue(report["active_runtime_window_waiting_for_exact_triplet"])
        action = report["machine_next_actions"][0]
        self.assertEqual(
            action["action"],
            "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end",
        )
        self.assertEqual(action["action_kind"], "active_runtime_window_waiting_for_exact_triplet")
        self.assertTrue(action["source_bound_blocker"])
        self.assertEqual(
            action["source_bound_blocker_kind"],
            "active_window_missing_exact_triplet_or_source_drift",
        )
        self.assertFalse(action["blind_wait_recommended"])
        self.assertFalse(action["restart_recommended"])
        self.assertFalse(action["wait_or_restart_or_logout_instruction_allowed"])
        self.assertFalse(action["logout_or_reconnect_instruction_allowed"])
        self.assertTrue(action["active_window_not_closure_ready"])
        self.assertFalse(action["prepare_fresh_player_backed_window_required"])
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", action)
        self.assertNotIn("build_player_identity_runtime_principal_lifecycle_evidence_bundle.py", json.dumps(report, sort_keys=True))
        self.assertFalse(report["approved_runtime_evidence"])

    def test_active_session_end_missing_correlation_window_reports_exact_blocker_without_evidence_claim(self) -> None:
        report = self.run_script(
            closure_payload(
                missing_roles=["session_start", "session_start_rejected", "session_end"],
                missing_artifacts=["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"],
            ),
            copy_ready=copy_ready_session_end_missing_correlation_payload(
                window_state="in_progress",
            ),
        )

        self.assertEqual(
            report["status"],
            "blocked_active_runtime_window_waiting_for_exact_copied_triplet",
        )
        lifecycle = report["runtime_window_lifecycle"]
        self.assertEqual(
            lifecycle["classification"],
            "active_runtime_window_session_end_missing_correlation_wait_for_matched_triplet_or_end",
        )
        self.assertTrue(lifecycle["session_end_missing_correlation_only"])
        diagnostics = lifecycle["session_end_missing_correlation_diagnostics"]
        self.assertEqual(
            diagnostics["classification"],
            "session_end_missing_correlation_only_non_evidence",
        )
        self.assertEqual(diagnostics["roles_present"], ["session_end"])
        self.assertFalse(diagnostics["counts_as_approved_runtime_evidence"])
        action = report["machine_next_actions"][0]
        self.assertEqual(action["action_kind"], "active_runtime_window_waiting_for_exact_triplet")
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertFalse(action["runner_command_available"])
        self.assertFalse(action["wait_or_restart_or_logout_instruction_allowed"])
        self.assertFalse(action["logout_or_reconnect_instruction_allowed"])
        action_context = action["non_evidence_context"]
        self.assertFalse(action_context["session_end_missing_correlation_counts_as_approved_runtime_evidence"])
        self.assertEqual(
            action_context["session_end_missing_correlation_diagnostics"][
                "required_next_material"
            ]["required_session_end_status_proof"],
            {
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            },
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertNotIn("build_player_identity_runtime_principal_lifecycle_evidence_bundle.py", json.dumps(report, sort_keys=True))

    def test_partial_rejected_start_unresolved_end_targets_exact_triplet_bundle_non_evidence(self) -> None:
        bundle = "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
        notice = {
            "schema": status_report.CONFIRMED_BETA_NOTICE_SCHEMA,
            "ready": True,
            "mode": "dry_run",
            "discord_sent": False,
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            "run_id": RUN_ID,
            "notice_path": "discord://obelisk-beta-testers",
            "approved_runtime_evidence": True,
            "runtime_ready": True,
        }

        report = self.run_script(
            closure_payload(
                missing_roles=["session_start", "session_end"],
                missing_artifacts=[bundle],
            ),
            copy_ready=copy_ready_rejected_start_unresolved_end_missing_start_payload(
                window_state="in_progress",
            ),
            confirmed_beta_notice=notice,
        )

        self.assertEqual(
            report["status"],
            "blocked_active_runtime_window_waiting_for_exact_copied_triplet",
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertTrue(report["copy_ready_log"]["copied_source_value"])
        self.assertFalse(report["copy_ready_log"]["copied"])
        self.assertFalse(report["confirmed_beta_notice"]["completed"])
        route = report["exact_triplet_bundle_route"]
        self.assertEqual(
            route["schema"],
            status_report.EXACT_TRIPLET_BUNDLE_ROUTE_SCHEMA,
        )
        self.assertEqual(route["next_action_target"], "exact_copied_lifecycle_triplet_bundle")
        self.assertEqual(route["accepted_lifecycle_event_roles"], ["session_start_rejected"])
        self.assertEqual(route["missing_lifecycle_event_roles"], ["session_start", "session_end"])
        self.assertEqual(route["first_missing_role"], "session_start")
        self.assertEqual(
            route["first_missing_runtime_evidence_path"],
            "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        )
        self.assertFalse(route["partial_lifecycle_material_counts_as_approved_runtime_evidence"])
        self.assertFalse(route["copied_log_presence_counts_as_approved_runtime_evidence"])
        self.assertFalse(route["direct_discord_send_counts_as_approved_runtime_evidence"])
        self.assertFalse(route["active_notice_state_counts_as_approved_runtime_evidence"])
        self.assertFalse(route["diagnostic_samples_count_as_approved_runtime_evidence"])
        action = report["machine_next_actions"][0]
        self.assertEqual(action["action_kind"], "active_runtime_window_waiting_for_exact_triplet")
        self.assertEqual(action["next_action_target"], "exact_copied_lifecycle_triplet_bundle")
        self.assertEqual(
            action["first_missing_runtime_evidence_path"],
            "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        )
        self.assertEqual(
            action["exact_triplet_bundle_route"]["missing_lifecycle_event_roles"],
            ["session_start", "session_end"],
        )
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertFalse(action["runner_command_available"])
        self.assertFalse(action["partial_lifecycle_material_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["copied_log_presence_counts_as_approved_runtime_evidence"])
        serialized = json.dumps(report, sort_keys=True)
        for forbidden in (
            "copy_player_principal_lifecycle_ready_log.py",
            "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
            "check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            "send_discord_embed.py",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_active_observer_only_no_role_window_stays_wait_state_without_copy_bundle_commands(self) -> None:
        report = self.run_script(
            closure_payload(
                missing_roles=["session_start", "session_start_rejected", "session_end"],
                missing_artifacts=["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"],
            ),
            copy_ready=copy_ready_window_payload(
                window_state="in_progress",
                roles_present=[],
                missing_roles=["session_start", "session_start_rejected", "session_end"],
            ),
        )

        self.assertEqual(
            report["status"],
            "blocked_active_runtime_window_waiting_for_exact_copied_triplet",
        )
        lifecycle = report["runtime_window_lifecycle"]
        self.assertTrue(lifecycle["observer_only_no_role_window"])
        self.assertTrue(lifecycle["active_waiting_not_closure_ready"])
        self.assertFalse(lifecycle["close_or_classify_as_non_evidence"])
        self.assertFalse(lifecycle["copy_bundle_commands_allowed"])
        action = report["machine_next_actions"][0]
        self.assertEqual(
            action["action"],
            "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end",
        )
        self.assertEqual(action["command_status"], "NOT PROVIDED")
        self.assertNotIn("command_text_not_executed", action)
        self.assertTrue(action["source_bound_blocker"])
        self.assertTrue(action["route_to_drift_or_source_bound_blocker"])
        self.assertFalse(action["blind_wait_recommended"])
        self.assertFalse(action["wait_or_restart_or_logout_instruction_allowed"])
        self.assertFalse(action["logout_or_reconnect_instruction_allowed"])
        self.assertTrue(action["active_window_not_closure_ready"])
        serialized = json.dumps(report, sort_keys=True)
        for forbidden in (
            "copy_player_principal_lifecycle_ready_log.py",
            "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
            "check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_passive_player_counts_never_add_sdk_or_p0_progress(self) -> None:
        passive = passive_payload(players_current=3)
        passive["approved_runtime_evidence"] = True
        passive["ready"] = True
        passive["counts_toward_sdk"] = True
        passive["counts_toward_p0_dependency_chain"] = True
        monitor_log = "\n".join(
            [
                "tick utc=2026-06-06T08:00:00Z",
                "query instance=arkserver3 map=Genesis2 query_port=27017 status=ok "
                "current_map=Genesis2 players=3/70 target_key=arkserver3:Genesis2:27017 "
                "players_current=3 players_max=70 presence_detected=true "
                "detection_source=gamedig_ase_query",
                "",
            ]
        )

        report = self.run_script(
            closure_payload(missing_roles=["session_end"]),
            passive,
            monitor_log=monitor_log,
        )

        contexts = [
            report,
            report["passive"],
            report["runtime_player_availability"],
            report["player_presence_context"],
            report["operator_action_summary"]["operator_context_inputs"],
            report["post_reboot_passive_monitor"],
            report["post_reboot_passive_monitor"]["query_status_by_target"][
                "arkserver3:Genesis2:27017"
            ],
        ]
        for context in contexts:
            with self.subTest(context=context.get("classification") or context.get("schema") or "report"):
                self.assertFalse(context["counts_toward_sdk"])
                self.assertFalse(context["counts_toward_p0_dependency_chain"])
                self.assertFalse(context["counts_toward_p0_dependency_chain_claim_now"])
                self.assertEqual(context["sdk_progress"], 0)
                self.assertEqual(context["p0_progress"], 0)
        self.assertTrue(report["passive"]["source_claims_ignored_for_status"])
        self.assertTrue(report["runtime_player_availability"]["players_detected"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_json_output_under_server_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            closure_path = Path(tmp) / "closure.json"
            route_path = Path(tmp) / "route.json"
            write_json(closure_path, closure_payload())
            write_json(route_path, route_gate_payload())
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--closure-json",
                    str(closure_path),
                    "--route-gate-json",
                    str(route_path),
                    "--json-output",
                    "/servidor/ark/blocked.json",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--json-output must not write under /servidor/ark", result.stderr)


if __name__ == "__main__":
    unittest.main()
