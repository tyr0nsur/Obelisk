#!/usr/bin/env python3
"""Tests for build_player_identity_public_contract_decision_record.py."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BUILDER = SCRIPT_DIR / "build_player_identity_public_contract_decision_record.py"
CHECKER = SCRIPT_DIR / "check_player_identity_public_contract_decision_record.py"
GAP_REPORT = SCRIPT_DIR / "check_player_identity_public_contract_gap_report.py"
APPROVED_RUNTIME_CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_check_player_identity_public_contract_decision_record import (  # noqa: E402
    strict_approved_runtime_check_report,
)
from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (  # noqa: E402
    manifest as approved_runtime_manifest,
    safe_test_env as approved_runtime_safe_test_env,
)


class BuildPlayerIdentityPublicContractDecisionRecordTests(unittest.TestCase):
    def write_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    def strict_report_for_runtime_path(self, runtime_path: Path, env: dict[str, str]) -> dict:
        result = subprocess.run(
            [sys.executable, str(APPROVED_RUNTIME_CHECKER), str(runtime_path), "--json"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def run_builder(
        self,
        *,
        runtime_manifest: dict | None = None,
        strict_report: dict | None = None,
        expect_returncode: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        temp_path = Path(tempfile.mkdtemp())
        runtime_path = temp_path / "approved-runtime-principal-lifecycle-evidence.json"
        strict_report_path = temp_path / "approved-runtime-principal-lifecycle-evidence.check.json"
        output = temp_path / "reviewed-identity-public-contract-decision-record.json"
        env = os.environ.copy()
        env.update(approved_runtime_safe_test_env())
        manifest_payload = runtime_manifest if runtime_manifest is not None else approved_runtime_manifest()
        self.write_json(runtime_path, manifest_payload)
        if strict_report is None:
            strict_report = (
                self.strict_report_for_runtime_path(runtime_path, env)
                if expect_returncode == 0
                else strict_approved_runtime_check_report()
            )
        self.write_json(strict_report_path, strict_report)
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--approved-runtime-evidence",
                str(runtime_path),
                "--strict-approved-runtime-check-report",
                str(strict_report_path),
                "--output",
                str(output),
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, expect_returncode, result.stderr)
        return result, output

    def test_builds_record_that_passes_decision_record_checker(self) -> None:
        result, output = self.run_builder()
        build_report = json.loads(result.stdout)

        self.assertEqual(build_report["schema"], "obelisk.player-identity-public-contract-decision-record-build-report.v1")
        self.assertTrue(build_report["accepted_for_contract_review"])
        self.assertFalse(build_report["public_sdk_ready"])
        self.assertFalse(build_report["runtime_ready"])
        self.assertEqual(build_report["sdk_progress"], 0)
        self.assertTrue(output.exists())
        record = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("approved_runtime_evidence_manifest_ref", record)
        self.assertEqual(
            record["approved_runtime_evidence_manifest_ref"]["schema"],
            "obelisk.player-identity-public-contract-approved-runtime-evidence-manifest-ref.v1",
        )
        self.assertFalse(record["approved_runtime_evidence_binding"]["public_sdk_ready"])
        self.assertFalse(record["approved_runtime_evidence_binding"]["runtime_ready"])

        checked = subprocess.run(
            [sys.executable, str(CHECKER), "--record", str(output), "--json"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        report = json.loads(checked.stdout)
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertTrue(report["runtime_evidence_binding_valid"])
        self.assertTrue(report["strict_approved_runtime_checker_contract_report_valid"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_generated_record_matches_gap_report_binding_without_promoting_sdk(self) -> None:
        runtime = approved_runtime_manifest()
        _, output = self.run_builder(runtime_manifest=runtime)
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_path = Path(temp_dir) / "approved-runtime-principal-lifecycle-evidence.json"
            self.write_json(runtime_path, runtime)
            env = os.environ.copy()
            env.update(approved_runtime_safe_test_env())
            gap = subprocess.run(
                [
                    sys.executable,
                    str(GAP_REPORT),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    "--identity-public-contract-decision-record",
                    str(output),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
        self.assertEqual(gap.returncode, 0, gap.stderr)
        report = json.loads(gap.stdout)
        record = report["identity_public_contract_decision_record"]
        self.assertTrue(record["accepted_for_contract_review"])
        self.assertTrue(record["runtime_evidence_binding_valid"])
        self.assertTrue(record["bound_to_accepted_runtime_evidence"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_invalid_strict_report_before_writing_record(self) -> None:
        result, output = self.run_builder(
            strict_report={
                **strict_approved_runtime_check_report(),
                "ready": False,
                "runtime_evidence_ready": False,
            },
            expect_returncode=1,
        )

        self.assertIn("strict_approved_runtime_checker_contract_report_ready_not_true", result.stderr)
        self.assertFalse(output.exists())

    def test_rejects_strict_report_not_bound_to_runtime_manifest_before_writing_record(self) -> None:
        temp_path = Path(tempfile.mkdtemp())
        runtime_path = temp_path / "approved-runtime-principal-lifecycle-evidence.json"
        runtime = approved_runtime_manifest()
        self.write_json(runtime_path, runtime)
        env = os.environ.copy()
        env.update(approved_runtime_safe_test_env())
        mismatched_report = copy.deepcopy(self.strict_report_for_runtime_path(runtime_path, env))
        mismatched_report["strict_lifecycle_triplet_selection"]["selected_sequences"] = [101, 102, 103]

        result, output = self.run_builder(
            runtime_manifest=runtime,
            strict_report=mismatched_report,
            expect_returncode=1,
        )

        self.assertIn(
            "strict_approved_runtime_checker_contract_report_runtime_input_mismatch",
            result.stderr,
        )
        self.assertFalse(output.exists())

    def test_rejects_non_runtime_evidence_manifest_schema(self) -> None:
        result, output = self.run_builder(
            runtime_manifest={"schema": "obelisk.runtime-window-plan.v1"},
            expect_returncode=1,
        )

        self.assertIn("--approved-runtime-evidence schema mismatch", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
