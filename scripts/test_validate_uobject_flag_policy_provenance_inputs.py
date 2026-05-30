#!/usr/bin/env python3
"""Tests for validate_uobject_flag_policy_provenance_inputs.py."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_uobject_flag_policy_provenance_inputs as validator


BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_sidecar(path: Path, *, binary_sha256: str = BINARY_SHA256, **overrides: object) -> Path:
    payload = {
        "schema": "obelisk.offline-artifact-provenance.v1",
        "verified": True,
        "binary_sha256": binary_sha256,
        "artifact_sha256": validator.gate.sha256_file(path),
    }
    payload.update(overrides)
    sidecar = validator.sidecar_path_for(path)
    sidecar.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return sidecar


class ValidateUObjectFlagPolicyProvenanceInputsTests(unittest.TestCase):
    def make_args(
        self,
        *,
        workspace: Path,
        protected: Path,
        weak_inputs: dict[str, Path],
        windows: dict[str, Path],
        require_rich_provenance: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            root=workspace,
            protected_root=protected,
            require_under_root=True,
            require_rich_provenance=require_rich_provenance,
            expected_binary_sha256=BINARY_SHA256,
            ghidra_stdout=weak_inputs["ghidra_stdout"],
            r2_windows=weak_inputs["r2_windows"],
            direct_call_counts=weak_inputs["direct_call_counts"],
            window=list(windows.items()),
            json=True,
        )

    def rich_provenance(self, path: Path) -> dict[str, object]:
        return {
            "command": ["objdump", "-d", path.name],
            "tool": "objdump",
            "tool_version": "GNU objdump test-version",
            "start_address": "0x1000",
            "stop_address": "0x1010",
            "source_path": path.name,
        }

    def write_route_inputs(
        self,
        workspace: Path,
        *,
        rich_provenance: bool = False,
    ) -> tuple[dict[str, Path], dict[str, Path]]:
        weak_inputs = {
            "ghidra_stdout": workspace / "weak-helper" / "ghidra-headless.stdout",
            "r2_windows": workspace / "weak-helper" / "r2-weak-helper-caller-modes.txt",
            "direct_call_counts": workspace / "weak-helper" / "direct-call-counts.txt",
        }
        for name, path in weak_inputs.items():
            write_text(path, f"{name}\n")
            write_sidecar(path, **(self.rich_provenance(path) if rich_provenance else {}))

        windows = {
            name: workspace / "uobject-policy" / f"{name}.objdump.txt"
            for name in validator.POLICY_WINDOWS
        }
        for name, path in windows.items():
            write_text(path, f"{name}\n")
            write_sidecar(path, **(self.rich_provenance(path) if rich_provenance else {}))
        return weak_inputs, windows

    def test_accepts_verified_sidecars_for_route_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            weak_inputs, windows = self.write_route_inputs(workspace)

            result = validator.build_result(
                self.make_args(workspace=workspace, protected=protected, weak_inputs=weak_inputs, windows=windows)
            )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(len(result["records"]), 7)
        self.assertTrue(all(record["sidecar_verified"] for record in result["records"]))

    def test_accepts_rich_provenance_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            weak_inputs, windows = self.write_route_inputs(workspace, rich_provenance=True)

            result = validator.build_result(
                self.make_args(
                    workspace=workspace,
                    protected=protected,
                    weak_inputs=weak_inputs,
                    windows=windows,
                    require_rich_provenance=True,
                )
            )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["blockers"], [])
        self.assertTrue(all(record["rich_provenance"]["verified"] for record in result["records"]))

    def test_blocks_minimal_sidecars_only_when_rich_provenance_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            weak_inputs, windows = self.write_route_inputs(workspace)

            result = validator.build_result(
                self.make_args(
                    workspace=workspace,
                    protected=protected,
                    weak_inputs=weak_inputs,
                    windows=windows,
                    require_rich_provenance=True,
                )
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual(result["status"], "blocked")
        self.assertIn("provenance_rich_field_missing", reasons)
        self.assertIn("provenance_command_invalid", reasons)

    def test_blocks_malformed_rich_provenance_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            weak_inputs, windows = self.write_route_inputs(workspace, rich_provenance=True)
            sidecar = validator.sidecar_path_for(weak_inputs["ghidra_stdout"])
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            payload["command"] = ["objdump", str(protected / "live" / "raw.objdump.txt")]
            payload["stop_address"] = "0x1000"
            sidecar.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            result = validator.build_result(
                self.make_args(
                    workspace=workspace,
                    protected=protected,
                    weak_inputs=weak_inputs,
                    windows=windows,
                    require_rich_provenance=True,
                )
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual(result["status"], "blocked")
        self.assertIn("path_text_under_protected_root", reasons)
        self.assertIn("path_resolves_under_protected_root", reasons)
        self.assertIn("provenance_address_range_invalid", reasons)

    def test_blocks_embedded_protected_paths_in_rich_provenance_command_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            weak_inputs, windows = self.write_route_inputs(workspace, rich_provenance=True)
            sidecar = validator.sidecar_path_for(weak_inputs["r2_windows"])
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            payload["command"] = [
                "objdump",
                "--input=" + str(protected / "live" / "raw.objdump.txt"),
            ]
            sidecar.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            result = validator.build_result(
                self.make_args(
                    workspace=workspace,
                    protected=protected,
                    weak_inputs=weak_inputs,
                    windows=windows,
                    require_rich_provenance=True,
                )
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual(result["status"], "blocked")
        self.assertIn("path_text_under_protected_root", reasons)
        self.assertIn("path_resolves_under_protected_root", reasons)

    def test_reports_missing_and_mismatched_sidecars_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            weak_inputs, windows = self.write_route_inputs(workspace)
            missing_window = windows["weak_helper_reject_0x100"]
            missing_sidecar = validator.sidecar_path_for(missing_window)
            missing_sidecar.unlink()
            r2_sidecar = validator.sidecar_path_for(weak_inputs["r2_windows"])
            r2_payload = json.loads(r2_sidecar.read_text(encoding="utf-8"))
            r2_payload["artifact_sha256"] = "0" * 64
            r2_sidecar.write_text(json.dumps(r2_payload) + "\n", encoding="utf-8")

            result = validator.build_result(
                self.make_args(workspace=workspace, protected=protected, weak_inputs=weak_inputs, windows=windows)
            )

            self.assertFalse(missing_sidecar.exists())

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual(result["status"], "blocked")
        self.assertIn("missing_provenance_sidecar", reasons)
        self.assertIn("provenance_artifact_sha256_mismatch", reasons)

    def test_blocks_relative_provenance_path_that_resolves_under_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            weak_inputs, windows = self.write_route_inputs(workspace)
            ghidra_sidecar = validator.sidecar_path_for(weak_inputs["ghidra_stdout"])
            payload = json.loads(ghidra_sidecar.read_text(encoding="utf-8"))
            payload["source_path"] = "../../live/raw-ghidra.stdout"
            ghidra_sidecar.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            result = validator.build_result(
                self.make_args(workspace=workspace, protected=protected, weak_inputs=weak_inputs, windows=windows)
            )

        reasons = {blocker["reason"] for blocker in result["blockers"]}
        self.assertEqual(result["status"], "blocked")
        self.assertIn("path_resolves_under_protected_root", reasons)


if __name__ == "__main__":
    unittest.main()
