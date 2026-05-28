#!/usr/bin/env python3
"""Offline tests for run_second_source_core_intake.py."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class RunSecondSourceCoreIntakeTests(unittest.TestCase):
    def test_default_mode_prints_offline_plan(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/run_second_source_core_intake.py",
                "--binary",
                "/tmp/ShooterGameServer",
                "--core",
                "/tmp/second.core",
                "--pack-dir",
                "/tmp/pack",
                "--snapshot-root",
                "/tmp/snapshots",
                "--verified-fname-root-slot",
                "0x1234",
                "--gobjects-candidate",
                "0x595b7e0",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        self.assertIn("Dry run", result.stdout)
        self.assertIn("scripts/build_core_dump_evidence_pack.py", result.stdout)
        self.assertIn("--scan-fname-tables", result.stdout)
        self.assertIn("--no-default-fname-indices", result.stdout)
        self.assertIn("--fname-index None=0", result.stdout)
        self.assertIn("--fname-root-slot verified_fname_root_slot=0x1234", result.stdout)
        self.assertIn("--gobjects-candidate gobjects=0x595b7e0", result.stdout)
        self.assertIn("--gobjects-sample-index 25447", result.stdout)
        self.assertIn("scripts/regenerate_ufunction_snapshots.py", result.stdout)
        self.assertIn("--target-set minimal-second-source-intake", result.stdout)
        self.assertIn("scripts/compare_reflection_snapshots.py", result.stdout)
        command_lines = result.stdout.splitlines()[1:]
        self.assertTrue(command_lines)
        self.assertTrue(all("--execute" not in line for line in command_lines))

    def test_requires_explicit_verified_artifact_addresses(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/run_second_source_core_intake.py",
                "--binary",
                "/tmp/ShooterGameServer",
                "--core",
                "/tmp/second.core",
                "--pack-dir",
                "/tmp/pack",
                "--snapshot-root",
                "/tmp/snapshots",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--verified-fname-root-slot", result.stderr)
        self.assertIn("--gobjects-candidate", result.stderr)

    def test_custom_target_and_clues_are_preserved(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/run_second_source_core_intake.py",
                "--binary",
                "/tmp/ShooterGameServer",
                "--core",
                "/tmp/second.core",
                "--pack-dir",
                "/tmp/pack",
                "--snapshot-root",
                "/tmp/snapshots",
                "--verified-fname-root-slot",
                "0x1234",
                "--gobjects-candidate",
                "0x595b7e0",
                "--fname-index",
                "None=0",
                "--gobjects-sample-index",
                "7",
                "--target-set",
                "structure-observer-intake",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        self.assertIn("--fname-index None=0", result.stdout)
        self.assertNotIn("ClientMessage=4884", result.stdout)
        self.assertIn("--gobjects-sample-index 7", result.stdout)
        self.assertNotIn("--gobjects-sample-index 25447", result.stdout)
        self.assertIn("--target-set structure-observer-intake", result.stdout)


if __name__ == "__main__":
    unittest.main()
