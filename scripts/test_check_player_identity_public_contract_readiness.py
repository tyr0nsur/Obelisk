#!/usr/bin/env python3
"""Tests for check_player_identity_public_contract_readiness.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_public_contract_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import manifest as approved_manifest


class PlayerIdentityPublicContractReadinessTests(unittest.TestCase):
    def run_checker(self, decisions: dict, runtime: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    "--json",
                    *args,
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def test_accepts_runtime_evidence_for_contract_review_only(self) -> None:
        result = self.run_checker(self.decisions(), approved_manifest())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertEqual(report["resolved_inputs"], ["runtime.lifecycle_evidence"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertIn("privacy.identifier_redaction", report["remaining_blockers"])
        self.assertEqual(report["blockers"], [])

    def test_blocks_promote_public_and_runtime_modes(self) -> None:
        for flag, blocker in (
            ("--promote", "promote_blocked_until_player_identity_public_contract_promotion"),
            ("--public-readiness", "public_readiness_blocked_until_player_identity_public_contract_promotion"),
            ("--runtime-readiness", "runtime_readiness_blocked_until_player_identity_public_contract_promotion"),
        ):
            with self.subTest(flag=flag):
                result = self.run_checker(self.decisions(), approved_manifest(), flag, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(blocker, report["blockers"])
                self.assertTrue(report["accepted_for_contract_review"])
                self.assertFalse(report["promotion_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_public_abi_openings(self) -> None:
        decisions = self.decisions()
        decisions["public_header_allowed"] = True
        decisions["public_header_symbols_now"] = ["RegisterPlayerIdentity"]
        decisions["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
        decisions["public_callback_abi_now"] = ["ObeliskPlayerPrincipalCallback"]
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])
        self.assertIn("public_callback_abi_now_not_empty", report["blockers"])

    def test_rejects_missing_runtime_evidence_or_decision_intake(self) -> None:
        decisions = self.decisions()
        decisions.pop("approved_runtime_evidence_intake")
        runtime = approved_manifest()
        runtime["public_sdk_ready"] = True
        result = self.run_checker(decisions, runtime, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_intake_missing", report["blockers"])
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])

    def test_rejects_forbidden_contract_terms_removed(self) -> None:
        decisions = self.decisions()
        decisions["forbidden_public_contract"] = ["lookup"]
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])

    def test_header_still_has_no_player_identity_public_symbols(self) -> None:
        header = HEADER.read_text(encoding="utf-8")
        for token in (
            "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
            "ObeliskPlayerPrincipal",
            "RegisterPlayerIdentity",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, header)


if __name__ == "__main__":
    unittest.main()
