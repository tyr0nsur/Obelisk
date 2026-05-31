#!/usr/bin/env python3
"""Tests for the v1 complete-SDK release claim checker."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"


class PublicSdkV1CompletionCheckTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["python3", str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_current_manifest_fails_closed_for_v1_completion(self) -> None:
        result = self.run_checker("--json", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["schema"], "obelisk.public-sdk-v1-completion-check.v1")
        self.assertFalse(payload["ready"])
        self.assertIn("stable_release_contract_claim_not_allowed", payload["blockers"])
        self.assertIn("v1_completion_required_false", payload["blockers"])
        self.assertIn("promoted_experimental_surfaces_unresolved", payload["blockers"])
        self.assertIn("v1_sdk_completion_blockers_unresolved", payload["blockers"])
        self.assertNotIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["unresolved_completion_blockers"])
        self.assertIn("obelisk.gameplay_policy_event.v1", payload["unresolved_experimental_surfaces"])
        self.assertIn("core-first release readiness", " ".join(payload["non_claims"]))

    def test_complete_minimal_manifest_passes(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": ["obelisk.lifecycle_config_logging.v1"],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.lifecycle_config_logging.v1",
                    "status": "promoted",
                    "public_contract": ["ObeliskPlugin_Init"],
                    "evidence": {"abi_tests": ["tests/abi/AbiLayoutTests.cpp"]},
                },
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            release_statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and "
                "docs/public_sdk_surfaces.json. obelisk.player_identity.v1 is excluded.",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--json",
            )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["blockers"], [])

    def test_release_statement_must_name_non_promoted_blockers(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], ["obelisk.player_identity.v1"])

    def test_non_promoted_public_contract_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.commands_replies.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.commands_replies.v1"],
            "surfaces": [
                {
                    "id": "obelisk.commands_replies.v1",
                    "status": "post-v1",
                    "public_contract": ["RegisterCommand"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertEqual(payload["non_promoted_with_public_contract"], ["obelisk.commands_replies.v1"])


if __name__ == "__main__":
    unittest.main()
