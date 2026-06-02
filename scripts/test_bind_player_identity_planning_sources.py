#!/usr/bin/env python3
"""Tests for bind_player_identity_planning_sources.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "bind_player_identity_planning_sources.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_first_evidence_readiness as first_evidence_checker
from test_check_player_identity_first_evidence_readiness import (
    CheckPlayerIdentityFirstEvidenceReadinessTests,
)
from test_check_player_identity_lifecycle_anchor_candidates import accepted_lifecycle_anchor_manifest
from test_check_player_identity_principal_invalidation_policy import manifest as principal_policy_manifest
from test_validate_offline_artifact_gate import players_identity_first_evidence_manifest


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


class BindPlayerIdentityPlanningSourcesTests(unittest.TestCase):
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

    def test_binds_outputs_and_route_reaches_runtime_evidence_blocker(self) -> None:
        ok = subprocess.CompletedProcess(["mock"], 0, "", "")
        first_evidence = players_identity_first_evidence_manifest()

        def fake_run_json_command(args: list[str], *, check: bool = False):
            command = " ".join(args)
            if "check_reflection_inventory_pack_readiness.py" in command:
                return ok, CheckPlayerIdentityFirstEvidenceReadinessTests().accepted_inventory_payload()
            if "compare_reflection_snapshots.py" in command:
                return ok, {
                    "totals": {
                        "targets": 12,
                        "comparable": 12,
                        "blocked": 0,
                        "second_source_accepted": 12,
                        "second_source_missing": 0,
                        "second_source_inconclusive": 0,
                        "second_source_rejected": 0,
                    },
                    "promotion_gate": {"layout_ready": True, "promotion_ready": False},
                    "second_source_status": "compared",
                }
            if "build_redacted_ufunction_signatures.py" in command:
                return ok, first_evidence
            if "check_player_identity_static_orientation.py" in command:
                return ok, {
                    "valid": True,
                    "accepted_for_orientation": True,
                    "not_artifact_gate": True,
                    "blockers": [],
                    "non_claims": ["candidate-only navigation evidence"],
                }
            self.fail(f"unexpected command: {command}")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_path = root / "first-evidence.json"
            lifecycle_path = root / "lifecycle.json"
            principal_path = root / "principal.json"
            output_dir = root / "bound"
            write_json(first_path, first_evidence)
            write_json(lifecycle_path, accepted_lifecycle_anchor_manifest())
            write_json(principal_path, principal_policy_manifest())

            result = self.run_tool(
                [
                    "--first-evidence",
                    str(first_path),
                    "--lifecycle-anchor-candidates",
                    str(lifecycle_path),
                    "--principal-invalidation-policy",
                    str(principal_path),
                    "--output-dir",
                    str(output_dir),
                    "--json",
                ]
            )
            report = json.loads(result.stdout)
            lifecycle_output = output_dir / "players-identity-lifecycle-anchor-candidates.json"
            principal_output = output_dir / "players-identity-principal-invalidation-policy.json"

            self.assertEqual(result.returncode, 0)
            self.assertTrue(report["ready"])
            self.assertTrue(report["planning_only"])
            self.assertFalse(report["promotion_ready"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            bound_lifecycle = json.loads(lifecycle_output.read_text(encoding="utf-8"))
            bound_principal = json.loads(principal_output.read_text(encoding="utf-8"))
            self.assertEqual(
                bound_lifecycle["artifact_identity"]["source_artifact_ids"],
                first_evidence["artifact_identity"]["source_artifact_ids"],
            )
            self.assertEqual(
                bound_principal["lifecycle_layout_source"]["source_binding"]["artifact_identity_source_artifact_ids"],
                bound_lifecycle["artifact_identity"]["source_artifact_ids"],
            )

            args = SimpleNamespace(
                artifact_root=Path("/tmp/player-identity-artifacts"),
                snapshot_root=Path("/tmp/player-identity-snapshots"),
                candidate_root=Path("/tmp/player-identity-second-source"),
                lifecycle_anchor_candidates_manifest=lifecycle_output,
                principal_invalidation_policy_manifest=principal_output,
                runtime_principal_lifecycle_evidence_manifest=None,
                approved_runtime_principal_lifecycle_evidence_manifest=None,
            )
            with (
                mock.patch.object(first_evidence_checker, "run_json_command", side_effect=fake_run_json_command),
                mock.patch.object(
                    first_evidence_checker,
                    "bounded_artifact_file_scan",
                    return_value={"ready_to_build_core_evidence_pack": False},
                ),
            ):
                route_report = first_evidence_checker.build_report(args)

        self.assertFalse(route_report["ready"])
        self.assertFalse(route_report["accepted_for_internal_planning"])
        self.assertFalse(route_report["promotion_ready"])
        self.assertFalse(route_report["public_sdk_ready"])
        self.assertFalse(route_report["runtime_ready"])
        self.assertEqual(route_report["primary_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(["approved_runtime_evidence_missing"], route_report["blockers"])
        self.assertNotIn("lifecycle_anchor_first_evidence_provenance_unbound", route_report["blockers"])

    def test_rejects_invalid_first_evidence_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_evidence = players_identity_first_evidence_manifest(public_sdk_ready=True)
            first_path = root / "first-evidence.json"
            lifecycle_path = root / "lifecycle.json"
            principal_path = root / "principal.json"
            output_dir = root / "bound"
            write_json(first_path, first_evidence)
            write_json(lifecycle_path, accepted_lifecycle_anchor_manifest())
            write_json(principal_path, principal_policy_manifest())

            result = self.run_tool(
                [
                    "--first-evidence",
                    str(first_path),
                    "--lifecycle-anchor-candidates",
                    str(lifecycle_path),
                    "--principal-invalidation-policy",
                    str(principal_path),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
            )
            self.assertFalse(output_dir.exists())

        self.assertEqual(result.returncode, 1)
        self.assertIn("players_identity_first_evidence_public_sdk_ready_not_false", result.stderr)

    def test_rejects_protected_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_path = root / "first-evidence.json"
            lifecycle_path = root / "lifecycle.json"
            principal_path = root / "principal.json"
            write_json(first_path, players_identity_first_evidence_manifest())
            write_json(lifecycle_path, accepted_lifecycle_anchor_manifest())
            write_json(principal_path, principal_policy_manifest())

            result = self.run_tool(
                [
                    "--first-evidence",
                    str(first_path),
                    "--lifecycle-anchor-candidates",
                    str(lifecycle_path),
                    "--principal-invalidation-policy",
                    str(principal_path),
                    "--output-dir",
                    "/servidor/ark/player-identity-bound-output",
                ],
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("must not write under protected server root", result.stderr)


if __name__ == "__main__":
    unittest.main()
