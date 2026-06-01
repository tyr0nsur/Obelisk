#!/usr/bin/env python3
"""Tests for build_player_identity_runtime_principal_lifecycle_approved_manifest.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BUILDER = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def runtime_log_lines() -> list[str]:
    return [
        "[info]  Obelisk Runtime Loaded Native (LD_PRELOAD)",
        "[info] ProcessEvent vtable-derived pattern candidates found: 1",
        "[info] ProcessEvent candidate[0] = 0x1d34e20",
        "[info] Found ProcessEvent at address: 0x1d34e20",
        "[info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x767c6aaa4000",
        "[info] ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.",
        "[warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.",
        f"[info] PlayerPrincipalLifecycleObserver enabled binary_sha256={SHA} "
        "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
        "delivery_claim=none principal_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=candidate_created principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=none principal_id_logged=false principal_generation_logged=false "
        "delivery_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
        "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
        "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
        "principal_action=candidate_invalidated principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
    ]


class BuildApprovedRuntimePrincipalLifecycleManifestTests(unittest.TestCase):
    def write_summary(self, temp_dir: Path) -> Path:
        log_path = temp_dir / "Obelisk.log"
        log_path.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ANALYZER), "--obelisk-commit", "test-commit", str(log_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        summary_path = temp_dir / "runtime-summary.json"
        summary_path.write_text(result.stdout, encoding="utf-8")
        return summary_path

    def run_builder(
        self,
        source_summary: Path,
        output: Path,
        *,
        reviewed_by: str = "runtime-reviewer",
        review_note: str = "consume-only lifecycle evidence reviewed",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--source-summary",
                str(source_summary),
                "--output",
                str(output),
                "--reviewed-by",
                reviewed_by,
                "--review-note",
                review_note,
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_checker(self, manifest: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER), str(manifest), "--json", *extra_args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_builds_manifest_that_passes_existing_consume_checker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            manifest_path = temp_dir / "approved-manifest.json"

            result = self.run_builder(summary_path, manifest_path)
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["schema"],
                "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
            )
            self.assertEqual(manifest["approval"]["reviewed_by"], "runtime-reviewer")
            self.assertEqual(
                manifest["approval"]["review_note"],
                "consume-only lifecycle evidence reviewed",
            )
            self.assertFalse(manifest["approval"]["server_operations_authorized_by_this_manifest"])
            self.assertFalse(manifest["promotion_ready"])

            checker = self.run_checker(manifest_path)
            self.assertEqual(checker.returncode, 0, checker.stderr)
            report = json.loads(checker.stdout)
            self.assertTrue(report["ready"])
            self.assertTrue(report["runtime_evidence_ready"])
            self.assertFalse(report["promotion_ready"])
            self.assertEqual(
                report["observed_runtime_cases"],
                ["session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
            )

    def test_generated_manifest_still_fails_closed_for_promote_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            manifest_path = temp_dir / "approved-manifest.json"
            result = self.run_builder(self.write_summary(temp_dir), manifest_path)
            self.assertEqual(result.returncode, 0, result.stderr)

            checker = self.run_checker(manifest_path, "--promote")
            self.assertNotEqual(checker.returncode, 0)
            report = json.loads(checker.stdout)
            self.assertIn("promote_blocked_until_identity_public_contract_gate", report["blockers"])
            self.assertTrue(report["runtime_evidence_ready"])
            self.assertFalse(report["promotion_ready"])

    def test_rejects_protected_source_summary_path_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "manifest.json"
            result = self.run_builder(
                Path("/servidor/ark/obelisk/logs/runtime-summary.json"),
                output,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--source-summary must not read from protected server root", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_summary_generated_with_server_paths_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["evidence"]["server_paths_allowed"] = True
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_path, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("generated without --allow-server-path", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_summary_with_protected_inner_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            summary_path = self.write_summary(temp_dir)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["evidence"]["sources"][0]["path"] = "/servidor/ark/obelisk/logs/live.log"
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            output = temp_dir / "manifest.json"

            result = self.run_builder(summary_path, output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must point to copied/offline evidence", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_review_text_that_would_trip_privacy_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            output = temp_dir / "manifest.json"
            result = self.run_builder(
                self.write_summary(temp_dir),
                output,
                review_note="reviewed raw_params details",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("identity/UE-internal terms", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
