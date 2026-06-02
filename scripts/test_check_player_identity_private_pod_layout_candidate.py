#!/usr/bin/env python3
"""Tests for check_player_identity_private_pod_layout_candidate.py."""

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
SCRIPT = SCRIPT_DIR / "check_player_identity_private_pod_layout_candidate.py"
MANIFEST = REPO_ROOT / "docs" / "research" / "player-identity-planning-sources" / "player-identity-private-pod-layout-candidate.json"
DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"


class PlayerIdentityPrivatePodLayoutCandidateTests(unittest.TestCase):
    def manifest(self) -> dict:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def run_checker(self, payload: dict | None = None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "candidate-layout.json"
            path.write_text(json.dumps(payload if payload is not None else self.manifest()), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json"],
                cwd=REPO_ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_current_private_layout_candidate_for_review_only(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertEqual(report["resolved_input"], "abi.public_pod_contract.private_layout_candidate")
        self.assertTrue(report["candidate_only"])
        self.assertFalse(report["layout_candidate_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(report["event_payload"]["struct_size"], 80)
        self.assertEqual(report["event_payload"]["alignment"], 8)
        self.assertEqual(report["descriptor"]["struct_size"], 48)
        self.assertEqual(report["descriptor"]["alignment"], 8)
        self.assertEqual(report["blockers"], [])

        decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
        tests = {item["id"]: item for item in decisions["required_tests_before_public_header"]}
        self.assertEqual(tests["abi.layout"]["status"], "missing")

    def test_rejects_public_or_runtime_overclaim(self) -> None:
        payload = self.manifest()
        payload["promotion_ready"] = True
        payload["public_sdk_ready"] = True
        payload["runtime_ready"] = True
        payload["public_header_allowed"] = True
        payload["public_header_symbols_now"] = ["ObeliskPlayerPrincipalEvent"]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])

    def test_rejects_layout_offset_size_or_order_drift(self) -> None:
        payload = self.manifest()
        payload["event_payload_layout"]["struct_size"] = 88
        payload["event_payload_layout"]["fields"][2]["offset"] = 16
        payload["descriptor_layout"]["fields"] = list(reversed(payload["descriptor_layout"]["fields"]))

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event_payload_layout_struct_size_mismatch", report["blockers"])
        self.assertIn("event_payload_layout_fields_mismatch", report["blockers"])
        self.assertIn("descriptor_layout_fields_mismatch", report["blockers"])
        self.assertIn("descriptor_layout_version_size_not_front_loaded", report["blockers"])

    def test_rejects_missing_reserved_zero_requirement(self) -> None:
        payload = self.manifest()
        reserved = payload["event_payload_layout"]["fields"][-1]
        self.assertEqual(reserved["name"], "reserved")
        reserved.pop("zero_required")

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event_payload_layout_reserved_zero_required_missing", report["blockers"])

    def test_rejects_positive_forbidden_identity_or_authority_terms(self) -> None:
        payload = self.manifest()
        leaked = copy.deepcopy(payload["event_payload_layout"]["fields"][2])
        leaked["name"] = "SteamID"
        payload["event_payload_layout"]["fields"].append(leaked)

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event_payload_layout_fields_mismatch", report["blockers"])
        self.assertIn("forbidden_public_term_exposure", report["blockers"])

    def test_rejects_private_contract_field_mismatch(self) -> None:
        payload = self.manifest()
        payload["event_payload_layout"]["fields"] = [
            field for field in payload["event_payload_layout"]["fields"] if field["name"] != "principal_generation"
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event_payload_layout_fields_mismatch", report["blockers"])
        self.assertIn("event_layout_private_contract_fields_mismatch", report["blockers"])


if __name__ == "__main__":
    unittest.main()
