#!/usr/bin/env python3
"""Tests for validate_chat_mode_coverage_manifest.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import validate_chat_mode_coverage_manifest as validator


SHA = validator.SUPPORTED_BINARY_SHA256
RUN_ID = "20260529T181700Z-chat-mode-coverage"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def analyzer_summary(log_sha: str, modes: list[int]) -> dict:
    return {
        "schema": validator.ANALYZER_SCHEMA,
        "promotion_gate": {"ready": True, "blockers": []},
        "privacy_leak_line_count": 0,
        "source": {"sha256": log_sha},
        "producer_sha256": [SHA],
        "accepted_send_modes": modes,
        "delivery_events": [
            {
                "sequence": index + 1,
                "send_mode": mode,
                "flags": "0x1",
                "message_size": 4,
                "accepted": True,
                "blockers": [],
            }
            for index, mode in enumerate(modes)
        ],
        "send_mode_evidence": [
            {
                "send_mode": mode,
                "send_mode_name": validator.MODE_NAMES[mode],
                "copied_plugin_delivery_observed": mode in modes,
                "route_observer_observed": False,
                "delivery_evidence_status": "copied_plugin_delivery" if mode in modes else "not_observed",
            }
            for mode in range(4)
        ],
    }


def manifest(root: Path, *, modes: list[int] | None = None) -> tuple[Path, dict]:
    selected_modes = [2, 3] if modes is None else modes
    run_dir = root / "live-validation-logs" / RUN_ID
    log = run_dir / "Obelisk.log"
    summary = run_dir / "chat-delivery-summary.json"
    write_text(log, "copied bounded chat delivery log\n")
    log_sha = validator.sha256_file(log)
    write_json(summary, analyzer_summary(log_sha, selected_modes))
    payload = {
        "schema": validator.SCHEMA,
        "run_id": RUN_ID,
        "target": {"instance": "arkserver", "map": "Ragnarok"},
        "approval": {
            "approved": True,
            "window_start_utc": "2026-05-29T18:17:00Z",
            "window_end_utc": "2026-05-29T18:30:00Z",
            "restart_expected": True,
            "rollback_defined": True,
        },
        "notice": {
            "sent": True,
            "path_label": "operator-approved beta-test channel",
            "time_utc": "2026-05-29T18:16:00Z",
            "sanitized_artifact_sha256": "a" * 64,
        },
        "runtime_gates": {
            "expected_sha256": SHA,
            "enabled_env": sorted(validator.EXPECTED_ENV),
            "enabled_markers": sorted(validator.EXPECTED_MARKERS),
            "disabled_marker_removed": "disable-plugins",
            "only_loadable_plugin": "oChatLogger",
        },
        "evidence": {
            "copied_log_path": str(log),
            "copied_log_sha256": log_sha,
            "analyzer_summary_path": str(summary),
            "complete_window_evidence": True,
        },
        "checks": {
            "pre_check": "passed",
            "post_check": "passed",
            "rollback_completed": True,
        },
        "claimed_modes": selected_modes,
        "controlled_sends": [
            {
                "mode": mode,
                "mode_name": validator.MODE_NAMES[mode],
                "precondition": "confirmed",
                "planned_send_time_utc": "2026-05-29T18:20:00Z",
                "observed_send_time_utc": "2026-05-29T18:20:05Z",
                "expected_message_size_bytes": 4,
                "tester_result": "accepted_by_game",
                "correlation": "controlled_quiet_window",
            }
            for mode in selected_modes
        ],
    }
    manifest_path = run_dir / "chat-mode-coverage-manifest.json"
    write_json(manifest_path, payload)
    return manifest_path, payload


class ValidateChatModeCoverageManifestTests(unittest.TestCase):
    def test_accepts_controlled_local_and_alliance_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path, payload = manifest(root)

            result = validator.validate_manifest(payload, manifest_path, workspace_root=root)

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertEqual([2, 3], result["claimed_modes"])

    def test_accepts_full_four_mode_plugin_delivery_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path, payload = manifest(root, modes=[0, 1, 2, 3])

            result = validator.validate_manifest(payload, manifest_path, workspace_root=root)

        self.assertEqual("accepted", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertEqual([0, 1, 2, 3], result["claimed_modes"])

    def test_rejects_route_or_analyzer_missing_plugin_delivery_for_claimed_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path, payload = manifest(root)
            summary_path = Path(payload["evidence"]["analyzer_summary_path"])
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["accepted_send_modes"] = [2]
            summary["delivery_events"] = [event for event in summary["delivery_events"] if event["send_mode"] == 2]
            summary["send_mode_evidence"][3]["route_observer_observed"] = True
            summary["send_mode_evidence"][3]["delivery_evidence_status"] = "route_only_no_plugin_delivery"
            write_json(summary_path, summary)

            result = validator.validate_manifest(payload, manifest_path, workspace_root=root)

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("analyzer_missing_claimed_send_modes", reasons)
        self.assertIn("analyzer_missing_matching_delivery_event", reasons)
        self.assertIn("analyzer_claimed_mode_has_route_observer_evidence", reasons)
        self.assertIn("analyzer_claimed_mode_not_plugin_delivery", reasons)

    def test_rejects_route_observer_summary_mixed_with_plugin_delivery_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path, payload = manifest(root, modes=[0, 1, 2, 3])
            summary_path = Path(payload["evidence"]["analyzer_summary_path"])
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["route_event_count"] = 1
            summary["accepted_route_send_modes"] = [2]
            summary["send_mode_evidence"][2]["route_observer_observed"] = True
            write_json(summary_path, summary)

            result = validator.validate_manifest(payload, manifest_path, workspace_root=root)

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual("blocked", result["status"])
        self.assertIn("analyzer_route_observer_present_in_plugin_delivery_manifest", reasons)
        self.assertIn("analyzer_route_send_modes_present_in_plugin_delivery_manifest", reasons)
        self.assertIn("analyzer_claimed_mode_has_route_observer_evidence", reasons)

    def test_rejects_secret_or_identity_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path, payload = manifest(root)
            payload["notice"]["path_label"] = "https://" + "discord.com/" + "api/webhooks" + "/secret"
            payload["controlled_sends"][0]["correlation"] = "player_name=Alice"

            result = validator.validate_manifest(payload, manifest_path, workspace_root=root)

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertIn("manifest_secret_or_endpoint_string", reasons)
        self.assertIn("manifest_privacy_string", reasons)

    def test_rejects_paths_outside_run_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path, payload = manifest(root)
            other_log = root / "live-validation-logs" / "other-run" / "Obelisk.log"
            write_text(other_log, "wrong run\n")
            payload["evidence"]["copied_log_path"] = str(other_log)
            payload["evidence"]["copied_log_sha256"] = validator.sha256_file(other_log)

            result = validator.validate_manifest(payload, manifest_path, workspace_root=root)

        self.assertIn("copied_log_path_outside_run_workspace", {blocker["reason"] for blocker in result["blockers"]})

    def test_rejects_inconclusive_precondition_for_claimed_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path, payload = manifest(root)
            payload["controlled_sends"][0]["precondition"] = "inconclusive_precondition_missing"

            result = validator.validate_manifest(payload, manifest_path, workspace_root=root)

        self.assertIn(
            "manifest_controlled_send_precondition_not_confirmed",
            {blocker["reason"] for blocker in result["blockers"]},
        )

    def test_cli_returns_three_when_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path, payload = manifest(root)
            payload["checks"]["post_check"] = "failed"
            write_json(manifest_path, payload)

            with redirect_stdout(StringIO()):
                code = validator.main_args([str(manifest_path), "--workspace-root", str(root)])

        self.assertEqual(3, code)


if __name__ == "__main__":
    unittest.main()
