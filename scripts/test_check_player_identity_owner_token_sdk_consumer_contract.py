#!/usr/bin/env python3
"""Tests for check_player_identity_owner_token_sdk_consumer_contract.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_owner_token_sdk_consumer_contract.py"
MANIFEST = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "player-identity-owner-token-sdk-consumer-contract.json"
)
PUBLIC_ABI_PREFLIGHT = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "player-identity-public-abi-preflight-candidate.json"
)


class PlayerIdentityOwnerTokenSdkConsumerContractTests(unittest.TestCase):
    def manifest(self) -> dict:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def preflight(self) -> dict:
        return json.loads(PUBLIC_ABI_PREFLIGHT.read_text(encoding="utf-8"))

    def run_checker(
        self,
        payload: dict | None = None,
        *,
        preflight_payload: dict | None = None,
        public_header_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "owner-token-sdk-consumer.json"
            path.write_text(json.dumps(payload if payload is not None else self.manifest()), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(path), "--json"]
            if preflight_payload is not None:
                preflight_path = root / "public-abi-preflight.json"
                preflight_path.write_text(json.dumps(preflight_payload), encoding="utf-8")
                command.extend(["--public-abi-preflight-candidate", str(preflight_path)])
            if public_header_text is not None:
                header = root / "ObeliskApi.h"
                header.write_text(public_header_text, encoding="utf-8")
                command.extend(["--public-header", str(header)])
            return subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_current_contract_as_candidate_only(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["candidate_only"])
        self.assertTrue(report["accepted_for_candidate_review"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertIn("abi.layout", report["required_before_promotion"])
        self.assertIn("sdk.consumer", report["required_before_promotion"])
        self.assertIn("lifecycle.owner_cleanup", report["required_before_promotion"])
        self.assertIn("separation.downstream_surfaces", report["required_before_promotion"])
        self.assertIn("v1_completion", report["does_not_resolve"])
        self.assertEqual(report["abi_layout"]["event_payload_summary"]["struct_size"], 80)
        self.assertEqual(report["abi_layout"]["descriptor_summary"]["struct_size"], 48)
        self.assertFalse(report["downstream_separation"]["consumption_allowed_now"])
        self.assertTrue(report["public_abi_preflight_candidate"]["accepted_for_candidate_review"])
        self.assertEqual(report["blockers"], [])

    def test_rejects_public_sdk_runtime_or_v1_overclaim(self) -> None:
        payload = self.manifest()
        payload["accepted_for_contract_review"] = True
        payload["promotion_ready"] = True
        payload["public_sdk_ready"] = True
        payload["runtime_ready"] = True
        payload["public_header_allowed"] = True
        payload["public_abi_ready"] = True
        payload["v1_completion_evidence"] = True
        payload["public_sdk_v1_completion_claim"] = True
        payload["public_header_symbols_now"] = ["ObeliskPlayerPrincipalEvent"]
        payload["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
        payload["public_callback_abi_now"] = ["RegisterPlayerIdentityCallbackWithOwnerToken"]
        payload["downstream_separation"]["consumption_allowed_now"] = True

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accepted_for_contract_review_not_false", report["blockers"])
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_abi_ready_not_false", report["blockers"])
        self.assertIn("v1_completion_evidence_not_false", report["blockers"])
        self.assertIn("public_sdk_v1_completion_claim_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])
        self.assertIn("public_callback_abi_now_not_empty", report["blockers"])
        self.assertIn("downstream_separation_consumption_allowed_now_not_false", report["blockers"])

    def test_rejects_contract_drift_and_public_preflight_drift(self) -> None:
        payload = self.manifest()
        payload["abi_layout"]["event_payload_summary"]["struct_size"] = 88
        payload["sdk_consumer"]["required_checks"] = payload["sdk_consumer"]["required_checks"][:-1]
        payload["lifecycle_owner_cleanup"]["status"] = "complete"
        payload["downstream_separation"]["must_remain_blocked"].remove("permissions_admin")

        preflight = self.preflight()
        preflight["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]

        result = self.run_checker(
            payload,
            preflight_payload=preflight,
            public_header_text="typedef struct ObeliskPlayerPrincipalEvent { int x; } ObeliskPlayerPrincipalEvent;\n",
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("abi_layout_event_payload_preflight_drift", report["blockers"])
        self.assertIn("required_checks_missing_required", report["blockers"])
        self.assertIn("lifecycle_owner_cleanup_status_mismatch", report["blockers"])
        self.assertIn("must_remain_blocked_missing_required", report["blockers"])
        self.assertIn("public_abi_preflight_candidate_not_accepted", report["blockers"])
        preflight_blockers = report["public_abi_preflight_candidate"]["blockers"]
        self.assertIn("public_capability_bits_now_not_empty", preflight_blockers)
        self.assertIn("public_header_identity_or_principal_symbols_detected", preflight_blockers)


if __name__ == "__main__":
    unittest.main()
