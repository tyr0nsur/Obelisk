#!/usr/bin/env python3
"""Tests for build_player_identity_planning_source_manifests.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "build_player_identity_planning_source_manifests.py"
STATIC_LIFECYCLE_REPORT = (
    REPO_ROOT
    / "docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json"
)


def current_static_lifecycle_report_sha256() -> str:
    return hashlib.sha256(STATIC_LIFECYCLE_REPORT.read_bytes()).hexdigest()


class BuildPlayerIdentityPlanningSourceManifestsTests(unittest.TestCase):
    def run_tool(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"tool failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def assert_planning_generation_binds_static_lifecycle_report(
        self,
        result: subprocess.CompletedProcess[str],
        *,
        expected_mode: str | None = None,
    ) -> None:
        self.assertEqual(0, result.returncode)
        payload = json.loads(result.stdout)

        self.assertEqual("obelisk.player-identity-planning-source-manifests-build-report.v1", payload["schema"])
        if expected_mode is not None:
            self.assertEqual(expected_mode, payload["mode"])
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["accepted_for_planning"])
        self.assertTrue(payload["planning_only"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["server_operations_authorized"])
        self.assertFalse(payload["runtime_work_authorized"])
        static_report_sha256 = current_static_lifecycle_report_sha256()
        if "binding_report" in payload:
            lifecycle = payload["binding_report"]["planning_provenance"]["lifecycle_anchor_candidates"]
            self.assertTrue(lifecycle["static_anchor_provenance_bound"])
            self.assertEqual(lifecycle["blockers"], [])
            self.assertEqual(
                {
                    "ShooterGameMode.HandleNewPlayer": "static_accepted",
                    "ShooterGameMode.OnLogout": "static_accepted",
                },
                lifecycle["accepted_anchor_corroboration_status_by_target"],
            )
            self.assertEqual(
                {
                    "ShooterGameMode.HandleNewPlayer": static_report_sha256,
                    "ShooterGameMode.OnLogout": static_report_sha256,
                },
                lifecycle["accepted_anchor_static_report_sha256_by_target"],
            )
            self.assertEqual(payload["binding_report"]["blockers"], [])
        else:
            self.assertTrue(payload["generated_report_valid"])
            self.assertEqual(payload["blockers"], [])

    def write_blocked_static_report(self, path: Path) -> None:
        report = json.loads(
            (REPO_ROOT / "docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json").read_text(
                encoding="utf-8"
            )
        )
        report["ready"] = False
        report["accepted_for_lifecycle_anchor_binding"] = False
        path.write_text(json.dumps(report), encoding="utf-8")

    def write_static_report(self, path: Path, mutate) -> None:
        report = json.loads(
            (REPO_ROOT / "docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json").read_text(
                encoding="utf-8"
            )
        )
        mutate(report)
        path.write_text(json.dumps(report), encoding="utf-8")

    def test_build_binds_static_lifecycle_anchor_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "planning"
            result = self.run_tool(["--output-dir", str(output_dir), "--json"])
            lifecycle = json.loads((output_dir / "players-identity-lifecycle-anchor-candidates.json").read_text(encoding="utf-8"))

        self.assert_planning_generation_binds_static_lifecycle_report(result)
        self.assertIn(
            "capture_id:base-identity-core",
            lifecycle["artifact_identity"]["source_artifact_ids"],
        )
        for anchor in lifecycle["candidate_anchors"]:
            if anchor["target"] in {"ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"}:
                self.assertEqual(anchor["corroboration"]["status"], "static_accepted")
                self.assertEqual(
                    anchor["corroboration"]["static_report_sha256"],
                    current_static_lifecycle_report_sha256(),
                )

    def test_build_fails_closed_when_static_lifecycle_report_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"
            self.write_blocked_static_report(static_report)
            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report is not accepted", result.stderr)

    def test_build_rejects_static_lifecycle_report_snapshot_sha_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                report["accepted_targets"][0]["source_snapshot_sha256"] = "0" * 64

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report source snapshot SHA mismatch", result.stderr)

    def test_build_rejects_static_lifecycle_report_artifact_status_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                report["artifact_status"] = "promoted"

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report artifact_status mismatch", result.stderr)

    def test_build_rejects_static_lifecycle_report_source_id_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                report["artifact_identity"]["source_artifact_ids"] = ["capture_id:base-identity-core"]

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report source_artifact_ids invalid", result.stderr)

    def test_build_rejects_static_lifecycle_report_duplicate_source_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                report["artifact_identity"]["source_artifact_ids"].extend(
                    list(report["artifact_identity"]["source_artifact_ids"])
                )

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report source_artifact_ids duplicate", result.stderr)

    def test_build_rejects_static_lifecycle_report_duplicate_source_snapshot_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                report["accepted_targets"][1]["source_snapshot_sha256"] = report["accepted_targets"][0][
                    "source_snapshot_sha256"
                ]

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report source snapshot SHA duplicate", result.stderr)

    def test_build_rejects_static_lifecycle_report_layout_summary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                report["accepted_targets"][0]["property_order"] = ["NewPlayer"]

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report property_order mismatch", result.stderr)

    def test_build_rejects_static_lifecycle_report_static_orientation_schema_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                report["static_orientation"]["schema"] = "obelisk.stale-static-shortcut.v1"

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report static_orientation schema mismatch", result.stderr)

    def test_build_rejects_admin_target_as_lifecycle_static_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                admin_target = dict(report["accepted_targets"][0])
                admin_target["target"] = "ShooterPlayerController.ServerListPlayers"
                report["accepted_targets"].append(admin_target)

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("admin target as lifecycle anchor", result.stderr)
        self.assertIn("ServerListPlayers/ServerKickPlayer are admin targets, not lifecycle anchors", result.stderr)

    def test_verify_existing_dir_accepts_committed_static_lifecycle_provenance(self) -> None:
        result = self.run_tool(
            [
                "--verify-existing-dir",
                str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                "--json",
            ],
        )

        self.assert_planning_generation_binds_static_lifecycle_report(result, expected_mode="verify_existing")
        payload = json.loads(result.stdout)
        self.assertTrue(
            payload["checked_optional_outputs"]["players-lifecycle-anchor-candidates-all-six-planning-gap.json"]["valid"]
        )
        self.assertTrue(
            payload["checked_optional_outputs"][
                "players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json"
            ]["valid"]
        )

    def test_verify_existing_dir_detects_stale_lifecycle_manifest_after_static_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            stale_path = existing / "players-identity-lifecycle-anchor-candidates.json"
            stale = json.loads(stale_path.read_text(encoding="utf-8"))
            stale["candidate_anchors"] = []
            stale_path.write_text(json.dumps(stale, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertIn("stale_or_mismatched_planning_manifest", [entry["reason"] for entry in payload["blockers"]])

    def test_verify_existing_dir_rejects_promotional_all_six_planning_gap_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            gap_path = existing / "players-lifecycle-anchor-candidates-all-six-planning-gap.json"
            gap = json.loads(gap_path.read_text(encoding="utf-8"))
            gap["promotion_gate"]["blockers"] = [
                blocker
                for blocker in gap["promotion_gate"]["blockers"]
                if blocker != "approved_runtime_evidence_missing"
            ]
            gap["promotion_gate"]["runtime_ready"] = True
            gap["durable_all_six_comparison"]["provided"] = True
            gap["durable_all_six_comparison"]["accepted"] = True
            gap["durable_all_six_comparison"]["reason"] = "accepted_second_source"
            gap["historical_scratch_comparison"]["durable"] = True
            gap["approved_runtime_evidence_present"] = True
            gap["runtime_evidence_ready"] = True
            gap["non_claims"] = [
                claim for claim in gap["non_claims"] if claim != "does not clear approved_runtime_evidence_missing"
            ]
            gap_path.write_text(json.dumps(gap, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertFalse(
            payload["checked_optional_outputs"]["players-lifecycle-anchor-candidates-all-six-planning-gap.json"]["valid"]
        )
        details = {
            entry.get("detail")
            for entry in payload["blockers"]
            if entry.get("reason") == "all_six_planning_gap_artifact_invalid"
        }
        self.assertIn("all_six_planning_gap_approved_runtime_evidence_missing_not_preserved", details)
        self.assertIn("all_six_planning_gap_runtime_ready_must_be_false", details)
        self.assertIn("all_six_planning_gap_durable_all_six_comparison_must_not_be_accepted", details)
        self.assertIn("all_six_planning_gap_historical_scratch_comparison_must_not_be_durable", details)
        self.assertIn("all_six_planning_gap_non_claims_missing", details)
        self.assertIn("all_six_planning_gap_promotional_true_field", details)

    def test_verify_existing_dir_rejects_stale_all_six_fixture_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            gap_path = existing / "players-lifecycle-anchor-candidates-all-six-planning-gap.json"
            gap = json.loads(gap_path.read_text(encoding="utf-8"))
            handle_new_player = next(
                entry
                for entry in gap["base_fixture_targets"]
                if entry["target"] == "ShooterGameMode.HandleNewPlayer"
            )
            handle_new_player["base_fixture_sha256"] = "0" * 64
            handle_new_player["property_order"] = ["NewPlayer"]
            gap_path.write_text(json.dumps(gap, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertFalse(
            payload["checked_optional_outputs"]["players-lifecycle-anchor-candidates-all-six-planning-gap.json"]["valid"]
        )
        details = {
            entry.get("detail")
            for entry in payload["blockers"]
            if entry.get("reason") == "all_six_planning_gap_artifact_invalid"
        }
        self.assertIn("all_six_planning_gap_base_fixture_sha256_mismatch", details)
        self.assertIn("all_six_planning_gap_property_order_mismatch", details)

    def test_verify_existing_dir_rejects_stale_fname_mismatch_fixture_expectation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            mismatch_path = existing / "players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json"
            mismatch = json.loads(mismatch_path.read_text(encoding="utf-8"))
            mismatch["fixture_expected_name_indices"][0] = 28422
            mismatch["fixture_property_order"] = ["NewPlayer"]
            mismatch_path.write_text(json.dumps(mismatch, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertFalse(
            payload["checked_optional_outputs"][
                "players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json"
            ]["valid"]
        )
        details = {
            entry.get("detail")
            for entry in payload["blockers"]
            if entry.get("reason") == "fname_mismatch_artifact_invalid"
        }
        self.assertIn("fname_mismatch_fixture_expected_name_indices_mismatch", details)
        self.assertIn("fname_mismatch_fixture_property_order_mismatch", details)

    def test_verify_existing_dir_rejects_unbound_fname_context_delta_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            mismatch_path = existing / "players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json"
            mismatch = json.loads(mismatch_path.read_text(encoding="utf-8"))
            latest = mismatch["latest_unbound_passive_diagnostic_context"]
            latest["observations"][0]["expected_name_index"] = 28422
            latest["observations"][1]["delta"] = 12
            mismatch_path.write_text(json.dumps(mismatch, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        details = {
            entry.get("detail")
            for entry in payload["blockers"]
            if entry.get("reason") == "fname_mismatch_artifact_invalid"
        }
        self.assertIn("fname_mismatch_latest_unbound_observation_expected_index_mismatch", details)
        self.assertIn("fname_mismatch_latest_unbound_observation_delta_mismatch", details)

    def test_verify_existing_dir_rejects_promotional_fname_mismatch_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            mismatch_path = existing / "players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json"
            mismatch = json.loads(mismatch_path.read_text(encoding="utf-8"))
            mismatch["second_source_layout_evidence"] = True
            mismatch["promotion_ready"] = True
            mismatch["latest_unbound_passive_diagnostic_context"]["approved_runtime_evidence"] = True
            mismatch["latest_unbound_passive_diagnostic_context"]["observations"][0][
                "source_bound_to_repo_artifact"
            ] = True
            mismatch_path.write_text(json.dumps(mismatch, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        details = {
            entry.get("detail")
            for entry in payload["blockers"]
            if entry.get("reason") == "fname_mismatch_artifact_invalid"
        }
        self.assertIn("fname_mismatch_second_source_layout_evidence_mismatch", details)
        self.assertIn("fname_mismatch_promotion_ready_mismatch", details)
        self.assertIn("fname_mismatch_latest_unbound_context_promotional_claim", details)
        self.assertIn("fname_mismatch_latest_unbound_observation_source_bound_overclaim", details)
        self.assertIn("fname_mismatch_promotional_true_field", details)

    def test_verify_existing_dir_rejects_all_six_triplet_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            gap_path = existing / "players-lifecycle-anchor-candidates-all-six-planning-gap.json"
            gap = json.loads(gap_path.read_text(encoding="utf-8"))
            gap["operational_consolidation"]["approved_triplet_sources"]["targets"] = [
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.OnLogout",
            ]
            gap["operational_consolidation"]["approved_triplet_sources"]["k2_postlogin_status"] = (
                "accepted_lifecycle_target"
            )
            for entry in gap["base_fixture_targets"]:
                if entry["target"] == "GameMode.K2_PostLogin":
                    entry["current_approved_triplet_source"] = True
                    entry["chronology_only_non_anchor"] = False
            gap["current_approved_triplet_sources"]["accepted_targets"] = [
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.OnLogout",
            ]
            gap["current_approved_triplet_sources"]["all_six_planning_gap_evidence_status"] = "second_source_evidence"
            gap_path.write_text(json.dumps(gap, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertFalse(
            payload["checked_optional_outputs"]["players-lifecycle-anchor-candidates-all-six-planning-gap.json"]["valid"]
        )
        details = {
            entry.get("detail")
            for entry in payload["blockers"]
            if entry.get("reason") == "all_six_planning_gap_artifact_invalid"
        }
        self.assertIn("all_six_planning_gap_targets_mismatch", details)
        self.assertIn("all_six_planning_gap_k2_postlogin_status_mismatch", details)
        self.assertIn("all_six_planning_gap_triplet_source_target_flags_mismatch", details)
        self.assertIn("all_six_planning_gap_k2_postlogin_not_chronology_only", details)
        self.assertIn("all_six_planning_gap_current_triplet_accepted_targets_mismatch", details)
        self.assertIn("all_six_planning_gap_current_triplet_all_six_status_mismatch", details)

    def test_verify_existing_dir_rejects_all_six_exact_rejected_start_role_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            gap_path = existing / "players-lifecycle-anchor-candidates-all-six-planning-gap.json"
            gap = json.loads(gap_path.read_text(encoding="utf-8"))
            gap["operational_consolidation"]["approved_triplet_sources"]["exact_rejected_start_role_policy"][
                "target"
            ] = "ShooterGameMode.HandleNewPlayer"
            gap["operational_consolidation"]["durable_lifecycle_anchor_roles"][0][
                "can_source_session_start_rejected"
            ] = True
            gap["operational_consolidation"]["observer_only_alternative"]["target"] = (
                "ShooterGameMode.HandleNewPlayer"
            )
            gap["operational_consolidation"]["observer_only_alternative"]["required_copied_bool_values"] = [
                "0",
                "1",
            ]
            for entry in gap["base_fixture_targets"]:
                if entry["target"] == "ShooterGameMode.HandleNewPlayer":
                    entry["current_rejected_start_observer_alternative"] = True
                if entry["target"] == "ShooterGameMode.CheckJoinInProgress":
                    entry["current_rejected_start_observer_alternative"] = False
            gap["current_durable_source_bound_lifecycle_anchor_evidence"][
                "observer_only_rejected_start_alternatives"
            ][0]["target"] = "ShooterGameMode.HandleNewPlayer"
            gap["current_approved_triplet_sources"]["exact_rejected_start_role_policy"][
                "disallowed_substitutes"
            ] = ["passive snapshots"]
            gap_path.write_text(json.dumps(gap, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertFalse(
            payload["checked_optional_outputs"]["players-lifecycle-anchor-candidates-all-six-planning-gap.json"]["valid"]
        )
        details = {
            entry.get("detail")
            for entry in payload["blockers"]
            if entry.get("reason") == "all_six_planning_gap_artifact_invalid"
        }
        self.assertIn("all_six_planning_gap_exact_rejected_start_role_policy_mismatch", details)
        self.assertIn("all_six_planning_gap_handle_new_player_rejected_start_role_not_disallowed", details)
        self.assertIn("all_six_planning_gap_observer_only_target_mismatch", details)
        self.assertIn("all_six_planning_gap_observer_only_required_copied_bool_values_mismatch", details)
        self.assertIn("all_six_planning_gap_handle_new_player_rejected_start_observer_not_allowed", details)
        self.assertIn("all_six_planning_gap_checkjoin_rejected_start_observer_missing", details)
        self.assertIn("all_six_planning_gap_current_observer_rejected_start_sources_mismatch", details)

    def test_verify_existing_dir_rejects_all_six_accepted_target_meaning_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            gap_path = existing / "players-lifecycle-anchor-candidates-all-six-planning-gap.json"
            gap = json.loads(gap_path.read_text(encoding="utf-8"))
            gap["operational_consolidation"]["approved_triplet_sources"]["targets_meaning"] = (
                "accepted lifecycle anchors"
            )
            gap["historical_scratch_comparison"]["accepted_targets_meaning"] = (
                "accepted durable second-source targets"
            )
            gap["current_durable_source_bound_lifecycle_anchor_evidence"]["accepted_targets_meaning"] = (
                "approved runtime triplet evidence"
            )
            gap["current_approved_triplet_sources"]["accepted_targets_meaning"] = (
                "approved runtime evidence"
            )
            gap_path.write_text(json.dumps(gap, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertFalse(
            payload["checked_optional_outputs"]["players-lifecycle-anchor-candidates-all-six-planning-gap.json"]["valid"]
        )
        details = {
            entry.get("detail")
            for entry in payload["blockers"]
            if entry.get("reason") == "all_six_planning_gap_artifact_invalid"
        }
        self.assertIn("all_six_planning_gap_targets_meaning_mismatch", details)
        self.assertIn("all_six_planning_gap_historical_scratch_accepted_targets_meaning_mismatch", details)
        self.assertIn("all_six_planning_gap_current_durable_anchor_accepted_targets_meaning_mismatch", details)
        self.assertIn("all_six_planning_gap_current_triplet_accepted_targets_meaning_mismatch", details)

    def test_rejects_protected_output_dir_before_writing(self) -> None:
        result = self.run_tool(
            ["--output-dir", "/servidor/ark/player-identity-planning-source-manifests"],
            check=False,
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("must not write under protected server root", result.stderr)

    def test_rejects_symlink_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)

            result = self.run_tool(["--output-dir", str(link)], check=False)

        self.assertEqual(1, result.returncode)
        self.assertIn("output-dir must not be a symlink", result.stderr)

    def test_rejects_missing_focal_lifecycle_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot_root = root / "snapshots"
            subprocess.run(
                ["cp", "-a", str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"), str(snapshot_root)],
                check=True,
            )
            manifest_path = snapshot_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["targets"] = [
                target
                for target in manifest["targets"]
                if f"{target.get('outer')}.{target.get('name')}" != "ShooterGameMode.OnLogout"
            ]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_tool(
                ["--snapshot-root", str(snapshot_root), "--output-dir", str(root / "out")],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("snapshot manifest does not contain required lifecycle target", result.stderr)

    def test_rejects_duplicate_focal_lifecycle_snapshot_manifest_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot_root = root / "snapshots"
            subprocess.run(
                ["cp", "-a", str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"), str(snapshot_root)],
                check=True,
            )
            manifest_path = snapshot_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for target in manifest["targets"]:
                if f"{target.get('outer')}.{target.get('name')}" == "ShooterGameMode.HandleNewPlayer":
                    manifest["targets"].append(dict(target))
                    break
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_tool(
                ["--snapshot-root", str(snapshot_root), "--output-dir", str(root / "out")],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate snapshot manifest target: ShooterGameMode.HandleNewPlayer", result.stderr)

    def test_rejects_snapshot_manifest_path_outside_snapshot_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot_root = root / "snapshots"
            subprocess.run(
                ["cp", "-a", str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"), str(snapshot_root)],
                check=True,
            )
            manifest_path = snapshot_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for target in manifest["targets"]:
                if f"{target.get('outer')}.{target.get('name')}" == "ShooterGameMode.HandleNewPlayer":
                    target["module"] = "../../../outside"
                    break
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_tool(
                ["--snapshot-root", str(snapshot_root), "--output-dir", str(root / "out")],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("resolves outside snapshot-root", result.stderr)


if __name__ == "__main__":
    unittest.main()
