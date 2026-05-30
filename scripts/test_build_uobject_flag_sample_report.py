#!/usr/bin/env python3
"""Tests for build_uobject_flag_sample_report.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "build_uobject_flag_sample_report.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transition_matrix_payload(*, sha: str = SHA) -> dict:
    return {
        "schema": "obelisk.uobject-flag-transition-matrix.v1",
        "status": "candidate_blocked",
        "binary": {"sha256": sha, "path_redacted": True},
        "builder_contract": {"promotion_ready": False, "resource_handle_claim": False},
        "transition_matrix": {
            "0x100": {
                "uobject_field": "+0x8",
                "predicate_windows": ["weak_lookup_strict_c00_1d56c00_1d56c70"],
                "mutation_windows": ["gc_mark_100_8000_1d18a90_1d18c70"],
                "promotion_ready": False,
                "public_lifecycle_name_assigned": False,
            },
            "0x4000": {
                "uobject_field": "+0x8",
                "predicate_windows": ["weak_lookup_strict_c00_1d56c00_1d56c70"],
                "mutation_windows": ["gobjects_4000_skip_mark_2982920_2982b60"],
                "promotion_ready": False,
                "public_lifecycle_name_assigned": False,
            },
            "0x8000": {
                "uobject_field": "+0x8",
                "predicate_windows": [],
                "mutation_windows": ["gc_mark_100_8000_1d18a90_1d18c70"],
                "promotion_ready": False,
                "public_lifecycle_name_assigned": False,
            },
        },
    }


def policy_payload(*, sha: str = SHA) -> dict:
    return {
        "schema": "obelisk.uobject-flag-policy-report.v1",
        "status": "candidate_blocked",
        "promotion_ready": False,
        "post_callback_resource_handle_ready": False,
        "binary": {"sha256": sha, "path_redacted": True},
        "policy_candidates": [
            {"mask": "0x100", "support": ["weak_helper_1d56c70_null_always"], "ue_lifecycle_name": "not_promoted"},
            {"mask": "0x4000", "support": ["weak_helper_1d56c70_null_when_sil_zero"], "ue_lifecycle_name": "not_promoted"},
            {"mask": "0x8000", "support": ["gc_mark_100_8000"], "ue_lifecycle_name": "not_promoted"},
        ],
    }


class BuildUObjectFlagSampleReportTests(unittest.TestCase):
    def run_builder(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def write_inputs(self, root: Path, matrix: dict | None = None, policy: dict | None = None) -> tuple[Path, Path]:
        matrix_path = root / "matrix.json"
        policy_path = root / "policy.json"
        write_json(matrix_path, transition_matrix_payload() if matrix is None else matrix)
        write_json(policy_path, policy_payload() if policy is None else policy)
        return matrix_path, policy_path

    def write_consume_gate(
        self,
        path: Path,
        *,
        source_path: Path,
        source_schema: str,
        status: str = "accepted",
        mode: str = "consume",
        blockers: list[dict] | None = None,
        binary_sha256: str = SHA,
        source_sha256: str | None = None,
    ) -> Path:
        write_json(
            path,
            {
                "schema": "obelisk.offline-artifact-gate-result.v1",
                "status": status,
                "mode": mode,
                "binary_sha256": binary_sha256,
                "manifests": [
                    {
                        "schema": source_schema,
                        "sha256": source_sha256 or sha256_file(source_path),
                    }
                ],
                "artifacts": [],
                "blockers": [] if blockers is None else blockers,
            },
        )
        return path

    def builder_args(self, matrix: Path, policy: Path, matrix_gate: Path, policy_gate: Path) -> list[str]:
        return [
            "--input",
            str(matrix),
            "--consume-gate",
            str(matrix_gate),
            "--input",
            str(policy),
            "--consume-gate",
            str(policy_gate),
        ]

    def write_inputs_and_gates(self, root: Path) -> tuple[Path, Path, Path, Path]:
        matrix, policy = self.write_inputs(root)
        matrix_gate = self.write_consume_gate(
            root / "matrix-gate.json",
            source_path=matrix,
            source_schema="obelisk.uobject-flag-transition-matrix.v1",
        )
        policy_gate = self.write_consume_gate(
            root / "policy-gate.json",
            source_path=policy,
            source_schema="obelisk.uobject-flag-policy-report.v1",
        )
        return matrix, policy, matrix_gate, policy_gate

    def test_emits_candidate_blocked_redacted_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix, policy, matrix_gate, policy_gate = self.write_inputs_and_gates(root)
            result = self.run_builder(*self.builder_args(matrix, policy, matrix_gate, policy_gate))

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.uobject-flag-sample-report.v1")
        self.assertEqual(payload["status"], "candidate_blocked")
        self.assertIs(False, payload["promotion_ready"])
        self.assertIs(False, payload["resource_handle_claim"])
        self.assertIs(False, payload["post_callback_resource_handle_ready"])
        self.assertEqual(payload["binary"], {"sha256": SHA, "path_redacted": True})
        self.assertEqual([sample["mask"] for sample in payload["flag_samples"]], ["0x100", "0x4000", "0x8000"])
        self.assertTrue(all(sample["public_lifecycle_name_assigned"] is False for sample in payload["flag_samples"]))
        self.assertTrue(all(sample["promotion_ready"] is False for sample in payload["flag_samples"]))
        self.assertTrue(all(source["path_redacted"] is True for source in payload["source_artifacts"]))
        self.assertTrue(all(source["consume_gate"]["status"] == "accepted" for source in payload["source_artifacts"]))
        self.assertTrue(all(source["consume_gate"]["mode"] == "consume" for source in payload["source_artifacts"]))
        self.assertNotIn(str(root), result.stdout)
        self.assertIn("does_not_promote_resourcehandle", payload["non_claims"])
        self.assertIn("no_rejected_runtime_object_samples", payload["remaining_blockers"])

    def test_rejects_unknown_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix, policy = self.write_inputs(root, matrix={"schema": "unknown", "status": "candidate_blocked"})
            matrix_gate = self.write_consume_gate(
                root / "matrix-gate.json",
                source_path=matrix,
                source_schema="unknown",
            )
            policy_gate = self.write_consume_gate(
                root / "policy-gate.json",
                source_path=policy,
                source_schema="obelisk.uobject-flag-policy-report.v1",
            )
            result = self.run_builder(*self.builder_args(matrix, policy, matrix_gate, policy_gate), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported input schema", result.stderr)

    def test_rejects_promotion_ready_or_non_candidate_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix_payload = transition_matrix_payload()
            matrix_payload["status"] = "accepted"
            matrix, policy = self.write_inputs(root, matrix=matrix_payload)
            matrix_gate = self.write_consume_gate(
                root / "matrix-gate.json",
                source_path=matrix,
                source_schema="obelisk.uobject-flag-transition-matrix.v1",
            )
            policy_gate = self.write_consume_gate(
                root / "policy-gate.json",
                source_path=policy,
                source_schema="obelisk.uobject-flag-policy-report.v1",
            )
            result = self.run_builder(*self.builder_args(matrix, policy, matrix_gate, policy_gate), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status=candidate_blocked", result.stderr)

    def test_rejects_mixed_binary_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix, policy = self.write_inputs(root, policy=policy_payload(sha="a" * 64))
            matrix_gate = self.write_consume_gate(
                root / "matrix-gate.json",
                source_path=matrix,
                source_schema="obelisk.uobject-flag-transition-matrix.v1",
            )
            policy_gate = self.write_consume_gate(
                root / "policy-gate.json",
                source_path=policy,
                source_schema="obelisk.uobject-flag-policy-report.v1",
                binary_sha256="a" * 64,
            )
            result = self.run_builder(*self.builder_args(matrix, policy, matrix_gate, policy_gate), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("same binary.sha256", result.stderr)

    def test_rejects_policy_only_complete_masks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_path = root / "policy.json"
            write_json(policy_path, policy_payload())
            policy_gate = self.write_consume_gate(
                root / "policy-gate.json",
                source_path=policy_path,
                source_schema="obelisk.uobject-flag-policy-report.v1",
            )
            result = self.run_builder("--input", str(policy_path), "--consume-gate", str(policy_gate), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required source schema coverage", result.stderr)

    def test_rejects_matrix_only_when_policy_source_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix_path = root / "matrix.json"
            write_json(matrix_path, transition_matrix_payload())
            matrix_gate = self.write_consume_gate(
                root / "matrix-gate.json",
                source_path=matrix_path,
                source_schema="obelisk.uobject-flag-transition-matrix.v1",
            )
            result = self.run_builder("--input", str(matrix_path), "--consume-gate", str(matrix_gate), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required source schema coverage", result.stderr)

    def test_rejects_non_hex_binary_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix, policy = self.write_inputs(root, matrix=transition_matrix_payload(sha="z" * 64))
            matrix_gate = self.write_consume_gate(
                root / "matrix-gate.json",
                source_path=matrix,
                source_schema="obelisk.uobject-flag-transition-matrix.v1",
                binary_sha256="z" * 64,
            )
            policy_gate = self.write_consume_gate(
                root / "policy-gate.json",
                source_path=policy,
                source_schema="obelisk.uobject-flag-policy-report.v1",
            )
            result = self.run_builder(*self.builder_args(matrix, policy, matrix_gate, policy_gate), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("binary.sha256", result.stderr)

    def test_rejects_public_lifecycle_name_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy = policy_payload()
            policy["policy_candidates"][0]["ue_lifecycle_name"] = "RF_TagGarbageTemp"
            matrix, policy_path = self.write_inputs(root, policy=policy)
            matrix_gate = self.write_consume_gate(
                root / "matrix-gate.json",
                source_path=matrix,
                source_schema="obelisk.uobject-flag-transition-matrix.v1",
            )
            policy_gate = self.write_consume_gate(
                root / "policy-gate.json",
                source_path=policy_path,
                source_schema="obelisk.uobject-flag-policy-report.v1",
            )
            result = self.run_builder(*self.builder_args(matrix, policy_path, matrix_gate, policy_gate), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public lifecycle", result.stderr)

    def test_rejects_missing_consume_gate_for_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix, policy, matrix_gate, _policy_gate = self.write_inputs_and_gates(root)
            result = self.run_builder("--input", str(matrix), "--consume-gate", str(matrix_gate), "--input", str(policy), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--consume-gate count must match --input count", result.stderr)

    def test_rejects_blocked_or_mismatched_consume_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix, policy = self.write_inputs(root)
            matrix_gate = self.write_consume_gate(
                root / "matrix-gate.json",
                source_path=matrix,
                source_schema="obelisk.uobject-flag-transition-matrix.v1",
                status="blocked",
                mode="promote",
                blockers=[{"reason": "test"}],
                source_sha256="0" * 64,
            )
            policy_gate = self.write_consume_gate(
                root / "policy-gate.json",
                source_path=policy,
                source_schema="obelisk.uobject-flag-policy-report.v1",
            )
            result = self.run_builder(*self.builder_args(matrix, policy, matrix_gate, policy_gate), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("consume_gate_status_not_accepted", result.stderr)
        self.assertIn("consume_gate_mode_not_consume", result.stderr)
        self.assertIn("consume_gate_has_blockers", result.stderr)
        self.assertIn("consume_gate_artifact_sha256_mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
