#!/usr/bin/env python3
"""Offline tests for run_second_source_core_intake.py."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import run_second_source_core_intake as intake


REPO_ROOT = Path(__file__).resolve().parents[1]


def readiness_report_json(
    *,
    target_sets: list[str] | None = None,
    targets: int = 1,
    ready: bool = True,
    blockers: list[dict[str, object]] | None = None,
) -> str:
    return json.dumps(
        {
            "schema": "obelisk.reflection-snapshot-readiness.v1",
            "gate_mode": "second_source_promotion",
            "evidence_scope": "second_source_layout_evidence_only",
            "not_promoted_surfaces": sorted(intake.REQUIRED_READINESS_NON_PROMOTED_SURFACES),
            "promotion_gate": {
                "ready": ready,
                "ready_scope": "layout_only" if ready else "not_ready",
                "layout_ready": ready,
                "promotion_ready": False,
                "blockers": [] if blockers is None else blockers,
            },
            "target_sets": ["minimal-second-source-intake"] if target_sets is None else target_sets,
            "totals": {"targets": targets},
        }
    ) + "\n"


def gobjects_manifest_json(
    *,
    status: str = "complete",
    gdb_core_failed: bool = False,
    gobjects_address: str = "0x595b7e0",
    fname_root_address: str = "0x1234",
    sample_indices: list[int] | None = None,
) -> str:
    return json.dumps(
        {
            "evidence_status": {
                "status": status,
                "gdb_core_failed": gdb_core_failed,
            },
            "gobjects_candidates": [
                {
                    "label": "gobjects",
                    "address": gobjects_address,
                }
            ],
            "fname_root_slots": [
                {
                    "label": "verified_fname_root_slot",
                    "address": fname_root_address,
                }
            ],
            "gobjects_sample_indices": [0, 1, 25447] if sample_indices is None else sample_indices,
        }
    ) + "\n"


def full_intake_args(pack_dir: Path) -> object:
    root = pack_dir.parent
    return type(
        "Args",
        (),
        {
            "scan_only": False,
            "pack_dir": str(pack_dir),
            "base_root": str(root / "base"),
            "snapshot_root": str(root / "candidate"),
            "target_set": "minimal-second-source-intake",
            "gobjects_candidate": "0x595b7e0",
            "gobjects_sample_index": [],
            "verified_fname_root_slot": "0x1234",
        },
    )()


def snapshot_json(
    target: str,
    *,
    artifact_sha256: str,
    capture_id: str,
    evidence_pack_id: str,
    artifact_kind: str = "offline_core",
) -> str:
    outer, name = target.split(".", 1)
    return json.dumps(
        {
            "schema": intake.UFUNCTION_SCHEMA,
            "evidence": {
                "artifact_kind": artifact_kind,
                "artifact_sha256": artifact_sha256,
                "capture_id": capture_id,
                "evidence_pack_id": evidence_pack_id,
            },
            "targets": [
                {
                    "target": {
                        "outer_name": outer,
                        "name": name,
                    }
                }
            ],
        }
    ) + "\n"


def write_snapshot_identities(
    root: Path,
    *,
    artifact_sha256: str,
    capture_id: str,
    evidence_pack_id: str,
    omit_identity_key: str | None = None,
) -> None:
    module = root / "sdk"
    module.mkdir(parents=True)
    for target in sorted(intake.schema_targets(intake.DEFAULT_TARGET_SET, intake.UFUNCTION_SCHEMA)):
        payload = json.loads(
            snapshot_json(
                target,
                artifact_sha256=artifact_sha256,
                capture_id=capture_id,
                evidence_pack_id=evidence_pack_id,
            )
        )
        if omit_identity_key:
            payload["evidence"].pop(omit_identity_key)
        (module / f"{target}.snapshot.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )


def write_distinct_snapshot_identities(root: Path) -> None:
    write_snapshot_identities(
        root / "base",
        artifact_sha256="1" * 64,
        capture_id="primary-core",
        evidence_pack_id="primary-pack",
    )
    write_snapshot_identities(
        root / "candidate",
        artifact_sha256="2" * 64,
        capture_id="second-core",
        evidence_pack_id="second-pack",
    )


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
        self.assertIn("scripts/scan_core_fname_tables.py", result.stdout)
        self.assertIn("--root-slot 0x1234", result.stdout)
        self.assertIn("--require-exact-root", result.stdout)
        self.assertIn("--json-out /tmp/pack/fname-root-validation/core.fname-root-validation.json", result.stdout)
        self.assertNotIn("--scan-fname-tables", result.stdout)
        self.assertIn("--output-dir /tmp/pack/gobjects-sampling", result.stdout)
        self.assertIn("--no-default-candidates", result.stdout)
        self.assertIn("--no-default-fname-roots", result.stdout)
        self.assertIn("--no-default-indices", result.stdout)
        self.assertIn("--index None=0", result.stdout)
        self.assertIn("--fname-root-slot verified_fname_root_slot=0x1234", result.stdout)
        self.assertIn("--gobjects-candidate gobjects=0x595b7e0", result.stdout)
        self.assertIn("--gobjects-sample-index 25447", result.stdout)
        self.assertIn("scripts/regenerate_ufunction_snapshots.py", result.stdout)
        self.assertIn("--evidence-pack-manifest /tmp/pack/gobjects-sampling/manifest.json", result.stdout)
        self.assertIn("--target-set minimal-second-source-intake", result.stdout)
        self.assertIn("scripts/compare_reflection_snapshots.py", result.stdout)
        self.assertIn("--readiness-report", result.stdout)
        self.assertIn("--fail-on-readiness-gaps", result.stdout)
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
        self.assertIn("full intake requires these arguments unless --scan-only is used", result.stderr)
        self.assertIn("--verified-fname-root-slot", result.stderr)
        self.assertIn("--gobjects-candidate", result.stderr)

    def test_scan_only_does_not_require_verified_addresses_or_snapshot_root(self) -> None:
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
                "--scan-only",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        self.assertIn("Dry run", result.stdout)
        self.assertIn("scripts/build_core_dump_evidence_pack.py", result.stdout)
        self.assertIn("--scan-fname-tables", result.stdout)
        self.assertNotIn("scripts/regenerate_ufunction_snapshots.py", result.stdout)
        self.assertNotIn("scripts/compare_reflection_snapshots.py", result.stdout)

    def test_scan_only_rejects_full_intake_arguments(self) -> None:
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
                "--scan-only",
                "--gobjects-candidate",
                "0x595b7e0",
                "--gobjects-sample-index",
                "7",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--scan-only cannot be combined with full-intake arguments", result.stderr)
        self.assertIn("--gobjects-candidate", result.stderr)
        self.assertIn("--gobjects-sample-index", result.stderr)

    def test_json_plan_emits_structured_review_artifact(self) -> None:
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
                "--json-plan",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        plan = json.loads(result.stdout)
        self.assertEqual(plan["schema"], "obelisk.second-source-core-intake-plan.v1")
        self.assertEqual(plan["mode"], "full-intake")
        self.assertFalse(plan["execute"])
        self.assertEqual(
            plan["phase_order"],
            [
                "fname_root_validation",
                "gobjects_sampling",
                "ufunction_snapshot_regeneration",
                "snapshot_comparison",
            ],
        )
        self.assertEqual(len(plan["commands"]), 4)
        self.assertEqual(
            plan["phase_order"],
            [command["phase"] for command in plan["commands"]],
        )
        self.assertEqual(plan["commands"][0]["phase"], "fname_root_validation")
        self.assertEqual(plan["commands"][-1]["phase"], "snapshot_comparison")
        self.assertIsNone(plan["phase_output_dirs"]["fname_table_scan"])
        self.assertEqual(plan["phase_output_dirs"]["fname_root_validation"], "/tmp/pack/fname-root-validation")
        self.assertEqual(plan["phase_output_dirs"]["gobjects_sampling"], "/tmp/pack/gobjects-sampling")
        self.assertEqual(plan["phase_output_dirs"]["snapshot_comparison"], "/tmp/pack/snapshot-comparison")
        self.assertEqual(plan["comparison_report"], "/tmp/pack/snapshot-comparison/readiness-report.json")
        commands_by_phase = {
            command["phase"]: command["argv"] for command in plan["commands"]
        }
        validation_command = commands_by_phase["fname_root_validation"]
        sampling_command = commands_by_phase["gobjects_sampling"]
        self.assertIn("scripts/scan_core_fname_tables.py", validation_command)
        self.assertIn("--root-slot", validation_command)
        self.assertIn("--require-exact-root", validation_command)
        self.assertIn("--json-out", validation_command)
        self.assertIn("/tmp/pack/fname-root-validation/core.fname-root-validation.json", validation_command)
        self.assertNotIn("--scan-fname-tables", validation_command)
        self.assertIn("--no-default-candidates", sampling_command)
        self.assertIn("--no-default-fname-roots", sampling_command)
        self.assertNotIn("--no-default-fname-indices", sampling_command)
        self.assertIn("--readiness-report", plan["commands"][-1]["argv"])
        self.assertIn("--fail-on-readiness-gaps", plan["commands"][-1]["argv"])
        self.assertIn("/tmp/pack/gobjects-sampling/manifest.json", commands_by_phase["ufunction_snapshot_regeneration"])
        self.assertTrue(
            any(
                "reviewed artifact-specific FName root" in gate
                for gate in plan["review_gates"]
            )
        )
        self.assertTrue(
            any(
                "GObjects sampling manifest must be complete" in gate
                for gate in plan["review_gates"]
            )
        )
        self.assertTrue(
            any(
                "protected server input/output paths are rejected" in gate
                for gate in plan["review_gates"]
            )
        )
        self.assertIn(
            "offline independent core artifact from the same ARK binary",
            plan["required_artifact_inputs"],
        )
        self.assertIn(
            "capture_id distinct from the primary-core capture",
            plan["required_artifact_inputs"],
        )
        self.assertIn(
            "evidence_pack_id distinct from the primary-core evidence pack",
            plan["required_artifact_inputs"],
        )
        self.assertIn(
            "artifact_kind recorded for both primary and candidate snapshot roots",
            plan["required_artifact_inputs"],
        )
        self.assertIn(
            "artifact_sha256 distinct from the primary-core artifact",
            plan["required_artifact_inputs"],
        )
        self.assertIn(
            "missing or partial sanitized artifact identity on either root: artifact_kind, artifact_sha256, capture_id, and evidence_pack_id are all required",
            plan["promotion_blockers"],
        )
        self.assertIn(
            "matching or reused primary-core artifact_sha256, capture_id, or evidence_pack_id",
            plan["promotion_blockers"],
        )
        self.assertIn(
            "dry-run or scan-only JSON plan treated as accepted FName or UFunction evidence",
            plan["promotion_blockers"],
        )
        self.assertIn(
            "FName table scan artifact treated as accepted FName evidence or layout promotion",
            plan["promotion_blockers"],
        )
        self.assertIn(
            "direct FName root validation missing, failed, or only partially matched",
            plan["promotion_blockers"],
        )
        self.assertIn(
            "GObjects sampling manifest missing, partial, or mismatched against the executed command inputs",
            plan["promotion_blockers"],
        )
        self.assertIn(
            "snapshot comparison readiness JSON missing from the executed intake pack",
            plan["promotion_blockers"],
        )
        self.assertIn(
            "promotion_gate.ready is not true in the readiness report",
            plan["promotion_blockers"],
        )
        self.assertEqual(plan["inputs"]["gobjects_candidate"], "0x595b7e0")

    def test_json_plan_rejects_execute(self) -> None:
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
                "--json-plan",
                "--execute",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--json-plan is a dry-run review artifact", result.stderr)

    def test_scan_only_json_plan_omits_full_intake_inputs(self) -> None:
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
                "--scan-only",
                "--json-plan",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        plan = json.loads(result.stdout)
        self.assertEqual(plan["mode"], "scan-only")
        self.assertEqual(plan["phase_order"], ["fname_table_scan"])
        self.assertEqual(len(plan["commands"]), 1)
        self.assertEqual(
            plan["phase_order"],
            [command["phase"] for command in plan["commands"]],
        )
        self.assertIsNone(plan["inputs"]["snapshot_root"])
        self.assertIsNone(plan["inputs"]["target_set"])
        self.assertIsNone(plan["inputs"]["base_root"])
        self.assertEqual(plan["phase_output_dirs"]["fname_table_scan"], "/tmp/pack/fname-scan")
        self.assertIsNone(plan["phase_output_dirs"]["fname_root_validation"])
        self.assertIsNone(plan["phase_output_dirs"]["gobjects_sampling"])
        self.assertIsNone(plan["phase_output_dirs"]["snapshot_comparison"])
        self.assertIsNone(plan["comparison_report"])
        self.assertEqual(plan["inputs"]["gobjects_sample_indices"], [])
        self.assertEqual(
            plan["inputs"]["fname_indices"],
            ["None=0", "ClientMessage=4884", "ServerChat=9619", "SetActiveMissionDebugFlags=9622"],
        )
        self.assertIn(
            "artifact-specific FName root derived from this core before full intake",
            plan["required_artifact_inputs"],
        )
        self.assertIn(
            "artifact_kind recorded for both primary and candidate snapshot roots",
            plan["required_artifact_inputs"],
        )
        self.assertIn(
            "dry-run or scan-only JSON plan treated as accepted FName or UFunction evidence",
            plan["promotion_blockers"],
        )
        self.assertIn(
            "missing or reused primary-core FName root assumptions",
            plan["promotion_blockers"],
        )
        command = plan["commands"][0]["argv"]
        self.assertIn("/tmp/pack/fname-scan", command)
        self.assertIn("--no-default-candidates", command)
        self.assertIn("--no-default-fname-roots", command)
        self.assertIn("--no-default-fname-indices", command)
        self.assertNotIn("--fname-root-slot", command)
        self.assertNotIn("--gobjects-candidate", command)

    def test_custom_target_and_extra_clues_preserve_required_fname_clues(self) -> None:
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
                "ExtraClue=7777",
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

        self.assertIn("--index None=0", result.stdout)
        self.assertIn("ClientMessage=4884", result.stdout)
        self.assertIn("ServerChat=9619", result.stdout)
        self.assertIn("SetActiveMissionDebugFlags=9622", result.stdout)
        self.assertIn("ExtraClue=7777", result.stdout)
        self.assertIn("--gobjects-sample-index 7", result.stdout)
        self.assertNotIn("--gobjects-sample-index 25447", result.stdout)
        self.assertIn("--target-set structure-observer-intake", result.stdout)

        plan = json.loads(
            subprocess.run(
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
                    "ExtraClue=7777",
                    "--gobjects-sample-index",
                    "7",
                    "--target-set",
                    "structure-observer-intake",
                    "--json-plan",
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout
        )
        self.assertEqual(
            plan["inputs"]["fname_indices"],
            [
                "None=0",
                "ClientMessage=4884",
                "ServerChat=9619",
                "SetActiveMissionDebugFlags=9622",
                "ExtraClue=7777",
            ],
        )

    def test_rejects_custom_fname_clue_that_duplicates_required_label(self) -> None:
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
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--fname-index duplicates required FName clue: None", result.stderr)

    def test_execute_requires_existing_binary_and_core(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/run_second_source_core_intake.py",
                "--binary",
                "/tmp/missing-ShooterGameServer",
                "--core",
                "/tmp/missing-second.core",
                "--pack-dir",
                "/tmp/pack",
                "--snapshot-root",
                "/tmp/snapshots",
                "--verified-fname-root-slot",
                "0x1234",
                "--gobjects-candidate",
                "0x595b7e0",
                "--execute",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--binary must exist before --execute", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_execute_rejects_unignored_in_repo_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            core = Path(temp_dir) / "second.core"
            binary.write_bytes(b"binary")
            core.write_bytes(b"core")

            result = subprocess.run(
                [
                    "python3",
                    "scripts/run_second_source_core_intake.py",
                    "--binary",
                    str(binary),
                    "--core",
                    str(core),
                    "--pack-dir",
                    "docs/not-ignored-pack",
                    "--snapshot-root",
                    "/tmp/snapshots",
                    "--verified-fname-root-slot",
                    "0x1234",
                    "--gobjects-candidate",
                    "0x595b7e0",
                    "--execute",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--pack-dir is inside the repository but is not ignored by Git", result.stderr)

    def test_rejects_protected_server_output_roots_even_for_dry_run(self) -> None:
        for protected_path in ("/servidor/ark", "/servidor/ark/obelisk/second-source-pack"):
            with self.subTest(protected_path=protected_path):
                result = subprocess.run(
                    [
                        "python3",
                        "scripts/run_second_source_core_intake.py",
                        "--binary",
                        "/tmp/ShooterGameServer",
                        "--core",
                        "/tmp/second.core",
                        "--pack-dir",
                        protected_path,
                        "--scan-only",
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("--pack-dir must not write under protected server root /servidor/ark", result.stderr)

    def test_rejects_protected_server_input_roots_even_for_dry_run(self) -> None:
        for label, protected_path in (
            ("--binary", "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer"),
            ("--core", "/servidor/ark/serverfiles/core"),
        ):
            with self.subTest(label=label):
                args = [
                    "python3",
                    "scripts/run_second_source_core_intake.py",
                    "--binary",
                    "/tmp/ShooterGameServer",
                    "--core",
                    "/tmp/second.core",
                    "--pack-dir",
                    "/tmp/pack",
                    "--scan-only",
                ]
                index = args.index(label)
                args[index + 1] = protected_path
                result = subprocess.run(
                    args,
                    cwd=REPO_ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    f"{label} must not read from protected server root /servidor/ark",
                    result.stderr,
                )

    def test_rejects_server_dump_artifact_root_for_dry_run(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/run_second_source_core_intake.py",
                "--binary",
                "/servidor/ark/obelisk/dumps/second-source/raw/ShooterGameServer",
                "--core",
                "/servidor/ark/obelisk/dumps/second-source/raw/core",
                "--pack-dir",
                "/servidor/ark/obelisk/dumps/second-source/intake/pack",
                "--scan-only",
                "--json-plan",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--binary must not read from protected server root /servidor/ark", result.stderr)

    def test_allows_paths_that_only_share_protected_prefix_text(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "scripts/run_second_source_core_intake.py",
                "--binary",
                "/tmp/ShooterGameServer",
                "--core",
                "/tmp/second.core",
                "--pack-dir",
                "/servidor/ark-not-live/pack",
                "--scan-only",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        self.assertIn("/servidor/ark-not-live/pack", result.stdout)

    def test_rejects_symlink_textually_under_protected_root_even_when_resolved_outside(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            protected = temp_root / "protected"
            outside = temp_root / "outside"
            protected.mkdir()
            outside.mkdir()
            linked = protected / "outward-link"
            linked.symlink_to(outside)

            with mock.patch.object(intake, "PROTECTED_OUTPUT_ROOTS", (protected,)):
                with self.assertRaises(SystemExit) as output_error:
                    intake.reject_protected_output_path(str(linked / "pack"), "--pack-dir")
                with self.assertRaises(SystemExit) as input_error:
                    intake.reject_protected_input_path(str(linked / "core"), "--core")

        self.assertIn("--pack-dir must not write under protected server root", str(output_error.exception))
        self.assertIn("--core must not read from protected server root", str(input_error.exception))

    def test_rejects_symlink_resolving_under_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            protected = temp_root / "protected"
            outside = temp_root / "outside"
            protected.mkdir()
            outside.mkdir()
            linked = outside / "protected-link"
            linked.symlink_to(protected)

            with mock.patch.object(intake, "PROTECTED_OUTPUT_ROOTS", (protected,)):
                with self.assertRaises(SystemExit) as output_error:
                    intake.reject_protected_output_path(str(linked / "pack"), "--pack-dir")
                with self.assertRaises(SystemExit) as input_error:
                    intake.reject_protected_input_path(str(linked / "core"), "--core")

        self.assertIn("--pack-dir must not write under protected server root", str(output_error.exception))
        self.assertIn("--core must not read from protected server root", str(input_error.exception))

    def test_allows_approved_offline_workspace_under_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            protected = temp_root / "protected"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)

            with (
                mock.patch.object(intake, "PROTECTED_OUTPUT_ROOTS", (protected,)),
                mock.patch.object(intake, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                intake.reject_protected_input_path(str(workspace / "ShooterGameServer"), "--binary")
                intake.reject_protected_input_path(str(workspace / "core"), "--core")
                intake.reject_protected_output_path(str(workspace / "pack"), "--pack-dir")

    def test_rejects_textually_protected_non_workspace_symlink_to_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            protected = temp_root / "protected"
            workspace = protected / "workspace-offline"
            blocked = protected / "obelisk"
            workspace.mkdir(parents=True)
            blocked.mkdir()
            binary = workspace / "ShooterGameServer"
            binary.write_bytes(b"binary")
            link = blocked / "ShooterGameServer"
            link.symlink_to(binary)

            with (
                mock.patch.object(intake, "PROTECTED_OUTPUT_ROOTS", (protected,)),
                mock.patch.object(intake, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
                self.assertRaises(SystemExit) as raised,
            ):
                intake.reject_protected_input_path(str(link), "--binary")

        self.assertIn("--binary must not read from protected server root", str(raised.exception))

    def test_rejects_protected_snapshot_root_even_for_dry_run(self) -> None:
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
                "/servidor/ark/obelisk/snapshots",
                "--verified-fname-root-slot",
                "0x1234",
                "--gobjects-candidate",
                "0x595b7e0",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--snapshot-root must not write under protected server root /servidor/ark", result.stderr)

    def test_rejects_protected_base_root_even_for_dry_run(self) -> None:
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
                "--base-root",
                "/servidor/ark/obelisk/snapshots",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--base-root must not read from protected server root /servidor/ark", result.stderr)

    def test_rejects_unknown_target_set_before_planning(self) -> None:
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
                "--target-set",
                "missing-target-set",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--target-set must be one of:", result.stderr)
        self.assertIn("minimal-second-source-intake", result.stderr)

    def test_rejects_target_set_without_ufunction_targets(self) -> None:
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
                "--target-set",
                "transfer-scriptstruct",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no UFunction snapshot targets", result.stderr)

    def test_rejects_labeled_verified_artifact_addresses_before_planning(self) -> None:
        for label, option, value in (
            ("--verified-fname-root-slot", "--verified-fname-root-slot", "fname=0x1234"),
            ("--gobjects-candidate", "--gobjects-candidate", "gobjects=0x595b7e0"),
        ):
            with self.subTest(label=label):
                args = [
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
                ]
                args[args.index(option) + 1] = value
                result = subprocess.run(
                    args,
                    cwd=REPO_ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{option} expects a raw address", result.stderr)

    def test_rejects_malformed_intake_clues_before_planning(self) -> None:
        for option, value, expected in (
            ("--fname-index", "BadName=not-an-int", "--fname-index must be an integer/address"),
            ("--fname-index", "=7", "--fname-index label must not be empty"),
            ("--gobjects-sample-index", "-1", "--gobjects-sample-index must be non-negative"),
        ):
            with self.subTest(option=option, value=value):
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
                        option,
                        value,
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_validates_persisted_gobjects_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "manifest.json"
            manifest.write_text(gobjects_manifest_json(), encoding="utf-8")

            intake.require_persisted_gobjects_manifest(
                manifest,
                expected_gobjects_candidate="0x595b7e0",
                expected_sample_indices=["0", "1", "25447"],
                expected_fname_root_slot="0x1234",
            )

    def test_rejects_failed_gobjects_manifest_before_snapshot_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "manifest.json"
            manifest.write_text(
                gobjects_manifest_json(status="partial", gdb_core_failed=True),
                encoding="utf-8",
            )

            with self.assertRaises(intake.ReadinessReportError) as raised:
                intake.require_persisted_gobjects_manifest(
                    manifest,
                    expected_gobjects_candidate="0x595b7e0",
                    expected_sample_indices=["0", "1", "25447"],
                    expected_fname_root_slot="0x1234",
                )

        self.assertIn("evidence_status must be complete", str(raised.exception))

    def test_rejects_readiness_report_with_reduced_non_promoted_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "readiness-report.json"
            payload = json.loads(readiness_report_json())
            payload["not_promoted_surfaces"] = ["mutation", "object_identity", "public_sdk"]
            report.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(intake.ReadinessReportError) as raised:
                intake.require_persisted_readiness_report(
                    report,
                    expected_target_sets=["minimal-second-source-intake"],
                )

        self.assertIn("missing required non-promoted surfaces", str(raised.exception))

    def test_rejects_readiness_report_without_explicit_promotion_ready_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "readiness-report.json"
            payload = json.loads(readiness_report_json())
            del payload["promotion_gate"]["promotion_ready"]
            report.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(intake.ReadinessReportError) as raised:
                intake.require_persisted_readiness_report(
                    report,
                    expected_target_sets=["minimal-second-source-intake"],
                )

        self.assertIn("promotion_gate.promotion_ready must be false", str(raised.exception))

    def test_rejects_gobjects_manifest_that_does_not_match_command_inputs(self) -> None:
        cases = (
            (
                gobjects_manifest_json(gobjects_address="0x595b7e1"),
                "missing expected gobjects candidate",
            ),
            (
                gobjects_manifest_json(fname_root_address="0x1235"),
                "missing expected verified FName root",
            ),
            (
                gobjects_manifest_json(sample_indices=[0, 1]),
                "sample indices do not match command inputs",
            ),
        )
        for manifest_json, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp_dir:
                manifest = Path(temp_dir) / "manifest.json"
                manifest.write_text(manifest_json, encoding="utf-8")

                with self.assertRaises(intake.ReadinessReportError) as raised:
                    intake.require_persisted_gobjects_manifest(
                        manifest,
                        expected_gobjects_candidate="0x595b7e0",
                        expected_sample_indices=["0", "1", "25447"],
                        expected_fname_root_slot="0x1234",
                    )

                self.assertIn(expected, str(raised.exception))

    def test_validates_distinct_snapshot_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_distinct_snapshot_identities(root)

            intake.require_distinct_snapshot_artifact_identities(
                root / "base",
                root / "candidate",
                target_set=intake.DEFAULT_TARGET_SET,
            )

    def test_rejects_snapshot_with_partial_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_snapshot_identities(
                root / "base",
                artifact_sha256="1" * 64,
                capture_id="primary-core",
                evidence_pack_id="primary-pack",
            )
            write_snapshot_identities(
                root / "candidate",
                artifact_sha256="2" * 64,
                capture_id="second-core",
                evidence_pack_id="second-pack",
                omit_identity_key="capture_id",
            )

            with self.assertRaises(intake.ReadinessReportError) as raised:
                intake.require_distinct_snapshot_artifact_identities(
                    root / "base",
                    root / "candidate",
                    target_set=intake.DEFAULT_TARGET_SET,
                )

        self.assertIn("missing evidence artifact identity: capture_id", str(raised.exception))

    def test_rejects_snapshot_with_placeholder_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_snapshot_identities(
                root / "base",
                artifact_sha256="1" * 64,
                capture_id="primary-core",
                evidence_pack_id="primary-pack",
            )
            write_snapshot_identities(
                root / "candidate",
                artifact_sha256="2" * 64,
                capture_id="unspecified-capture",
                evidence_pack_id="static-global-default-pack",
            )

            with self.assertRaises(intake.ReadinessReportError) as raised:
                intake.require_distinct_snapshot_artifact_identities(
                    root / "base",
                    root / "candidate",
                    target_set=intake.DEFAULT_TARGET_SET,
                )

        self.assertIn("invalid capture_id", str(raised.exception))

    def test_rejects_snapshot_that_reuses_base_artifact_identity_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_snapshot_identities(
                root / "base",
                artifact_sha256="1" * 64,
                capture_id="primary-core",
                evidence_pack_id="primary-pack",
            )
            write_snapshot_identities(
                root / "candidate",
                artifact_sha256="1" * 64,
                capture_id="second-core",
                evidence_pack_id="second-pack",
            )

            with self.assertRaises(intake.ReadinessReportError) as raised:
                intake.require_distinct_snapshot_artifact_identities(
                    root / "base",
                    root / "candidate",
                    target_set=intake.DEFAULT_TARGET_SET,
                )

        self.assertIn("candidate reuses base artifact identity field(s): artifact_sha256", str(raised.exception))

    def test_execute_persists_snapshot_comparison_stdout_even_when_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = full_intake_args(root / "pack")
            commands = [
                ["python3", "scan.py"],
                ["python3", "sample.py"],
                ["python3", "regen.py"],
                ["python3", "compare.py", "--target-set", "minimal-second-source-intake"],
            ]
            (root / "pack" / "gobjects-sampling").mkdir(parents=True)
            (root / "pack" / "gobjects-sampling" / "manifest.json").write_text(
                gobjects_manifest_json(),
                encoding="utf-8",
            )
            write_distinct_snapshot_identities(root)
            results = [
                subprocess.CompletedProcess(commands[0], 0),
                subprocess.CompletedProcess(commands[1], 0),
                subprocess.CompletedProcess(commands[2], 0),
                subprocess.CompletedProcess(
                    commands[3],
                    2,
                    stdout='{"promotion_gate":{"ready":false}}\n',
                    stderr="missing_second_source\n",
                ),
            ]

            with mock.patch.object(intake.subprocess, "run", side_effect=results):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    return_code = intake.run_commands(args, commands)

            report = root / "pack" / "snapshot-comparison" / "readiness-report.json"
            stderr = root / "pack" / "snapshot-comparison" / "readiness-report.stderr.txt"
            self.assertEqual(return_code, 2)
            self.assertEqual(report.read_text(encoding="utf-8"), '{"promotion_gate":{"ready":false}}\n')
            self.assertIn("missing_second_source\n", stderr.read_text(encoding="utf-8"))
            self.assertIn(
                "snapshot comparison readiness validation failed",
                stderr.read_text(encoding="utf-8"),
            )

    def test_execute_rejects_minimal_false_success_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = full_intake_args(root / "pack")
            commands = [
                ["python3", "scan.py"],
                ["python3", "sample.py"],
                ["python3", "regen.py"],
                ["python3", "compare.py", "--target-set", "minimal-second-source-intake"],
            ]
            (root / "pack" / "gobjects-sampling").mkdir(parents=True)
            (root / "pack" / "gobjects-sampling" / "manifest.json").write_text(
                gobjects_manifest_json(),
                encoding="utf-8",
            )
            write_distinct_snapshot_identities(root)
            results = [
                subprocess.CompletedProcess(commands[0], 0),
                subprocess.CompletedProcess(commands[1], 0),
                subprocess.CompletedProcess(commands[2], 0),
                subprocess.CompletedProcess(
                    commands[3],
                    0,
                    stdout='{"promotion_gate":{"ready":true}}\n',
                    stderr="",
                ),
            ]

            with mock.patch.object(intake.subprocess, "run", side_effect=results):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    return_code = intake.run_commands(args, commands)

            report = root / "pack" / "snapshot-comparison" / "readiness-report.json"
            stderr = root / "pack" / "snapshot-comparison" / "readiness-report.stderr.txt"
            self.assertEqual(return_code, 1)
            self.assertEqual(report.read_text(encoding="utf-8"), '{"promotion_gate":{"ready":true}}\n')
            self.assertIn(
                "schema must be obelisk.reflection-snapshot-readiness.v1",
                stderr.read_text(encoding="utf-8"),
            )

    def test_execute_persists_snapshot_comparison_stdout_on_valid_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = full_intake_args(root / "pack")
            commands = [
                ["python3", "scan.py"],
                ["python3", "sample.py"],
                ["python3", "regen.py"],
                ["python3", "compare.py", "--target-set", "minimal-second-source-intake"],
            ]
            report_json = readiness_report_json()
            (root / "pack" / "gobjects-sampling").mkdir(parents=True)
            (root / "pack" / "gobjects-sampling" / "manifest.json").write_text(
                gobjects_manifest_json(),
                encoding="utf-8",
            )
            write_distinct_snapshot_identities(root)
            results = [
                subprocess.CompletedProcess(commands[0], 0),
                subprocess.CompletedProcess(commands[1], 0),
                subprocess.CompletedProcess(commands[2], 0),
                subprocess.CompletedProcess(
                    commands[3],
                    0,
                    stdout=report_json,
                    stderr="",
                ),
            ]

            with mock.patch.object(intake.subprocess, "run", side_effect=results):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    return_code = intake.run_commands(args, commands)

            report = root / "pack" / "snapshot-comparison" / "readiness-report.json"
            stderr = root / "pack" / "snapshot-comparison" / "readiness-report.stderr.txt"
            self.assertEqual(return_code, 0)
            self.assertEqual(report.read_text(encoding="utf-8"), report_json)
            self.assertFalse(stderr.exists())

    def test_execute_rejects_success_when_candidate_snapshot_identity_is_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = full_intake_args(root / "pack")
            commands = [
                ["python3", "scan.py"],
                ["python3", "sample.py"],
                ["python3", "regen.py"],
                ["python3", "compare.py", "--target-set", "minimal-second-source-intake"],
            ]
            (root / "pack" / "gobjects-sampling").mkdir(parents=True)
            (root / "pack" / "gobjects-sampling" / "manifest.json").write_text(
                gobjects_manifest_json(),
                encoding="utf-8",
            )
            write_snapshot_identities(
                root / "base",
                artifact_sha256="1" * 64,
                capture_id="primary-core",
                evidence_pack_id="primary-pack",
            )
            write_snapshot_identities(
                root / "candidate",
                artifact_sha256="2" * 64,
                capture_id="second-core",
                evidence_pack_id="second-pack",
                omit_identity_key="evidence_pack_id",
            )
            results = [
                subprocess.CompletedProcess(commands[0], 0),
                subprocess.CompletedProcess(commands[1], 0),
                subprocess.CompletedProcess(commands[2], 0),
                subprocess.CompletedProcess(
                    commands[3],
                    0,
                    stdout=readiness_report_json(),
                    stderr="",
                ),
            ]

            with mock.patch.object(intake.subprocess, "run", side_effect=results):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    return_code = intake.run_commands(args, commands)

            stderr = root / "pack" / "snapshot-comparison" / "readiness-report.stderr.txt"
            self.assertEqual(return_code, 1)
            self.assertIn(
                "snapshot artifact identity validation failed",
                stderr.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "missing evidence artifact identity: evidence_pack_id",
                stderr.read_text(encoding="utf-8"),
            )

    def test_execute_rejects_success_json_missing_command_target_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            args = full_intake_args(root / "pack")
            commands = [
                ["python3", "scan.py"],
                ["python3", "sample.py"],
                ["python3", "regen.py"],
                ["python3", "compare.py", "--target-set", "minimal-second-source-intake"],
            ]
            (root / "pack" / "gobjects-sampling").mkdir(parents=True)
            (root / "pack" / "gobjects-sampling" / "manifest.json").write_text(
                gobjects_manifest_json(),
                encoding="utf-8",
            )
            write_distinct_snapshot_identities(root)
            results = [
                subprocess.CompletedProcess(commands[0], 0),
                subprocess.CompletedProcess(commands[1], 0),
                subprocess.CompletedProcess(commands[2], 0),
                subprocess.CompletedProcess(
                    commands[3],
                    0,
                    stdout=readiness_report_json(target_sets=["structure-observer-intake"]),
                    stderr="",
                ),
            ]

            with mock.patch.object(intake.subprocess, "run", side_effect=results):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    return_code = intake.run_commands(args, commands)

            stderr = root / "pack" / "snapshot-comparison" / "readiness-report.stderr.txt"
            self.assertEqual(return_code, 1)
            self.assertIn(
                "target_sets missing expected command target set(s): minimal-second-source-intake",
                stderr.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
