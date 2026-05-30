#!/usr/bin/env python3
"""Tests for build_gobjects_two_core_manifest.py."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from artifact_identity import canonical_json_bytes  # noqa: E402
import validate_offline_artifact_gate as gate  # noqa: E402

SCRIPT = SCRIPT_DIR / "build_gobjects_two_core_manifest.py"
BINARY_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def write_report(path: Path, core: Path, *, gobjects: str = "0x595b7e0") -> None:
    samples = [
        {"label": "package", "index": 0},
        {"label": "server_chat", "index": 25447},
    ]
    payload = {
        "schema": "obelisk.gobjects-sample-reconciliation.v1",
        "core": str(core),
        "inputs": {
            "gobjects_candidate": gobjects,
            "fname_root_slot": "0x5956f30",
            "sample_indices": samples,
        },
        "summary": {
            "sample_count": 2,
            "accepted_count": 2,
            "rejected_count": 0,
            "membership_pass_count": 2,
            "promotion_status": "internal-only-single-artifact",
        },
        "samples": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def recompute_artifact_sha256(payload: dict[str, object]) -> str:
    identity = dict(payload["artifact_identity"])
    identity_without_hash = {
        "artifact_kind": identity["artifact_kind"],
        "capture_id": identity["capture_id"],
        "evidence_pack_id": identity["evidence_pack_id"],
    }
    manifest_without_identity = {key: value for key, value in payload.items() if key != "artifact_identity"}
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "artifact_identity": identity_without_hash,
                "report": manifest_without_identity,
            }
        )
    ).hexdigest()


def gate_args(*, root: Path, protected_root: Path, manifest: Path) -> argparse.Namespace:
    return argparse.Namespace(
        root=root,
        protected_root=protected_root,
        manifest=[manifest],
        artifact=[],
        expected_binary_sha256=BINARY_SHA,
        mode="consume",
        strict_target_set_coverage=False,
        json=True,
    )


class GObjectsTwoCoreManifestTests(unittest.TestCase):
    def test_builds_manifest_from_matching_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core_a = root / "core-a"
            core_b = root / "core-b"
            core_a.write_text("primary", encoding="utf-8")
            core_b.write_text("second", encoding="utf-8")
            report_a = root / "primary.json"
            report_b = root / "second.json"
            write_report(report_a, core_a)
            write_report(report_b, core_b)
            output = root / "manifest.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--binary-sha256",
                    BINARY_SHA,
                    "--report",
                    f"primary={report_a}",
                    "--report",
                    f"second={report_b}",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], "obelisk.gobjects-two-core-manifest.v1")
            self.assertTrue(manifest["ufunction_inventory_input_ready"])
            self.assertFalse(manifest["public_gobjects_promotion_ready"])
            self.assertEqual(manifest["core_count"], 2)
            self.assertEqual(manifest["sample_set"][1], {"label": "server_chat", "index": 25447})
            self.assertRegex(manifest["cores"][0]["core_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                manifest["artifact_identity"],
                {
                    "artifact_kind": "obelisk.gobjects-two-core-manifest.v1",
                    "artifact_sha256": recompute_artifact_sha256(manifest),
                    "capture_id": "gobjects-two-core-capture",
                    "evidence_pack_id": "gobjects-two-core-pack",
                },
            )

    def test_cli_manifest_passes_offline_artifact_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            protected = Path(temp_dir) / "server"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            core_a = workspace / "core-a"
            core_b = workspace / "core-b"
            core_a.write_text("primary", encoding="utf-8")
            core_b.write_text("second", encoding="utf-8")
            report_a = workspace / "primary.json"
            report_b = workspace / "second.json"
            write_report(report_a, core_a)
            write_report(report_b, core_b)
            output = workspace / "manifest.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--binary-sha256",
                    BINARY_SHA,
                    "--report",
                    f"primary={report_a}",
                    "--report",
                    f"second={report_b}",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(manifest))

            gate_result = gate.build_result(gate_args(root=workspace, protected_root=protected, manifest=output))

        self.assertEqual(gate_result["status"], "accepted")
        self.assertEqual(gate_result["blockers"], [])

    def test_rejects_mismatched_gobjects_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            core.write_text("core", encoding="utf-8")
            report_a = root / "primary.json"
            report_b = root / "second.json"
            write_report(report_a, core)
            write_report(report_b, core, gobjects="0x1234")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--binary-sha256",
                    BINARY_SHA,
                    "--report",
                    f"primary={report_a}",
                    "--report",
                    f"second={report_b}",
                    "--output",
                    str(root / "manifest.json"),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("same gobjects_candidate", result.stderr)

    def test_rejects_unaccepted_report_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            core.write_text("core", encoding="utf-8")
            report_a = root / "primary.json"
            report_b = root / "second.json"
            write_report(report_a, core)
            write_report(report_b, core)
            payload = json.loads(report_b.read_text(encoding="utf-8"))
            payload["summary"]["rejected_count"] = 1
            report_b.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--binary-sha256",
                    BINARY_SHA,
                    "--report",
                    f"primary={report_a}",
                    "--report",
                    f"second={report_b}",
                    "--output",
                    str(root / "manifest.json"),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("rejected_count expected 0", result.stderr)


if __name__ == "__main__":
    unittest.main()
