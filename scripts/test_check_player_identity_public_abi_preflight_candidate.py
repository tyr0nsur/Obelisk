#!/usr/bin/env python3
"""Tests for check_player_identity_public_abi_preflight_candidate.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_public_abi_preflight_candidate.py"
MANIFEST = REPO_ROOT / "docs" / "research" / "player-identity-planning-sources" / "player-identity-public-abi-preflight-candidate.json"
IDENTIFIER_REDACTION = REPO_ROOT / "docs" / "research" / "2026-06-02-player-identity-identifier-redaction-evidence.json"
PRINCIPAL_INVALIDATION = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-identity-principal-invalidation-policy.json"
)


class PlayerIdentityPublicAbiPreflightCandidateTests(unittest.TestCase):
    def manifest(self) -> dict:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def run_checker(
        self,
        payload: dict | None = None,
        *,
        public_header_text: str | None = None,
        identifier_redaction_payload: dict | None = None,
        principal_invalidation_payload: dict | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "public-abi-preflight.json"
            path.write_text(json.dumps(payload if payload is not None else self.manifest()), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(path), "--json"]
            if public_header_text is not None:
                header = root / "ObeliskApi.h"
                header.write_text(public_header_text, encoding="utf-8")
                command.extend(["--public-header", str(header)])
            if identifier_redaction_payload is not None:
                evidence = root / "identifier-redaction.json"
                evidence.write_text(json.dumps(identifier_redaction_payload), encoding="utf-8")
                command.extend(["--identifier-redaction-evidence", str(evidence)])
            if principal_invalidation_payload is not None:
                policy = root / "principal-invalidation.json"
                policy.write_text(json.dumps(principal_invalidation_payload), encoding="utf-8")
                command.extend(["--principal-invalidation-policy", str(policy)])
            return subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_current_preflight_as_blocked_candidate_only(self) -> None:
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
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertEqual(report["event_payload"]["struct_size"], 80)
        self.assertEqual(report["descriptor"]["struct_size"], 48)
        self.assertIn("runtime.lifecycle_evidence", report["required_before_public_abi"])
        self.assertIn("abi.layout", report["required_before_public_abi"])
        self.assertIn("sdk.consumer", report["required_before_public_abi"])
        self.assertIn("nonzero plugin_owner_token required", report["required_owner_token_lifecycle"])
        self.assertIn("missing capability fails closed", report["required_capability_policy"])
        self.assertEqual(report["sdk_consumer_contract"]["source"], "derived_compatibility_stub")
        self.assertTrue(report["sdk_consumer_contract"]["candidate_only"])
        self.assertTrue(report["sdk_consumer_contract"]["accepted_for_candidate_review"])
        self.assertFalse(report["sdk_consumer_contract"]["accepted_for_contract_review"])
        self.assertFalse(report["sdk_consumer_contract"]["public_sdk_ready"])
        self.assertIn(
            "consumer checks struct_size before reading identity payload or descriptor fields",
            report["sdk_consumer_contract"]["required_behavior"],
        )
        self.assertIn(
            "consumer treats registration handles as process-local and non-persistent",
            report["sdk_consumer_contract"]["required_behavior"],
        )
        self.assertIn("lifecycle.owner_cleanup", report["sdk_consumer_contract"]["does_not_resolve"])
        self.assertIn("v1_completion", report["does_not_resolve"])
        self.assertEqual(report["blockers"], [])

    def test_rejects_public_or_runtime_overclaim(self) -> None:
        payload = self.manifest()
        payload["promotion_ready"] = True
        payload["public_sdk_ready"] = True
        payload["runtime_ready"] = True
        payload["public_header_allowed"] = True
        payload["public_abi_ready"] = True
        payload["v1_completion_evidence"] = True
        payload["public_header_symbols_now"] = ["ObeliskPlayerPrincipalEvent"]
        payload["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_abi_ready_not_false", report["blockers"])
        self.assertIn("v1_completion_evidence_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])

    def test_rejects_sdk_consumer_contract_overclaim_or_weakened_rules(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer_contract"] = {
            "status": "ready",
            "candidate_only": False,
            "accepted_for_contract_review": True,
            "promotion_ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "public_header_allowed": True,
            "public_abi_ready": True,
            "v1_completion_evidence": True,
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "public_capability_bits_now": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
            "public_callback_abi_now": ["ObeliskPlayerPrincipalCallback"],
            "required_behavior": [
                "consumer checks the captured capability bit before registering identity callbacks",
            ],
            "does_not_resolve": ["sdk.consumer"],
        }

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sdk_consumer_contract_status_mismatch", report["blockers"])
        self.assertIn("sdk_consumer_contract_candidate_only_not_true", report["blockers"])
        self.assertIn("sdk_consumer_contract_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("sdk_consumer_contract_public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("sdk_consumer_contract_required_behavior_missing", report["blockers"])
        self.assertIn("sdk_consumer_contract_does_not_resolve_missing", report["blockers"])
        self.assertFalse(report["sdk_consumer_contract"]["public_sdk_ready"])

    def test_rejects_missing_runtime_owner_or_capability_requirements(self) -> None:
        payload = self.manifest()
        payload["required_before_public_abi"].remove("runtime.lifecycle_evidence")
        payload["does_not_resolve"].remove("runtime.lifecycle_evidence")
        payload["required_capability_policy"] = ["missing capability fails closed"]
        payload["required_owner_token_lifecycle"] = ["nonzero plugin_owner_token required"]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_before_public_abi_missing_required", report["blockers"])
        self.assertIn("does_not_resolve_missing_required", report["blockers"])
        self.assertIn("required_capability_policy_missing_required", report["blockers"])
        self.assertIn("required_owner_token_lifecycle_missing_required", report["blockers"])

    def test_rejects_public_header_identity_symbol(self) -> None:
        result = self.run_checker(
            public_header_text="\n".join(
                [
                    "typedef struct ObeliskPlayerPrincipalEvent { int x; } ObeliskPlayerPrincipalEvent;",
                    "#define OBELISK_API_CAPABILITY_PLAYER_SESSION (1ull << 13)",
                    "typedef struct ObeliskPlayerSession { uint64_t x; } ObeliskPlayerSession;",
                    "typedef void (*ObeliskPlayerLifecycleCallback)(void* userData);",
                    "uint64_t (*RegisterPlayerLoginWithOwnerToken)(uint64_t ownerToken);",
                    "uint64_t (*RegisterPlayerLogoutWithOwnerToken)(uint64_t ownerToken);",
                    "typedef struct ObeliskPlayerConnectEvent { uint64_t x; } ObeliskPlayerConnectEvent;",
                    "typedef struct ObeliskPlayerDisconnectEvent { uint64_t x; } ObeliskPlayerDisconnectEvent;",
                    "typedef struct ObeliskPlayerJoinEvent { uint64_t x; } ObeliskPlayerJoinEvent;",
                    "typedef struct ObeliskPlayerLeaveEvent { uint64_t x; } ObeliskPlayerLeaveEvent;",
                ]
            )
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_identity_or_principal_symbols_detected", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_identity_or_principal_symbols_detected")
        detected = {item["token"] for item in detail["detected"]}
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_SESSION", detected)
        self.assertIn("ObeliskPlayerSession", detected)
        self.assertIn("ObeliskPlayerLifecycleCallback", detected)
        self.assertIn("RegisterPlayerLoginWithOwnerToken", detected)
        self.assertIn("RegisterPlayerLogoutWithOwnerToken", detected)
        self.assertIn("ObeliskPlayerConnectEvent", detected)
        self.assertIn("ObeliskPlayerDisconnectEvent", detected)
        self.assertIn("ObeliskPlayerJoinEvent", detected)
        self.assertIn("ObeliskPlayerLeaveEvent", detected)

    def test_rejects_private_layout_summary_drift(self) -> None:
        payload = self.manifest()
        payload["event_payload"]["struct_size"] = 88
        payload["descriptor"]["fields"] = list(reversed(payload["descriptor"]["fields"]))

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event_payload_private_layout_mismatch", report["blockers"])
        self.assertIn("descriptor_fields_private_layout_mismatch", report["blockers"])

    def test_rejects_claimed_redaction_input_when_redaction_checker_blocks(self) -> None:
        redaction = json.loads(IDENTIFIER_REDACTION.read_text(encoding="utf-8"))
        redaction["sanitized"] = False

        result = self.run_checker(identifier_redaction_payload=redaction)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identifier_redaction_evidence_not_accepted", report["blockers"])
        self.assertIn("claimed_contract_review_input_not_accepted", report["blockers"])
        self.assertFalse(report["identifier_redaction_evidence"]["accepted_for_contract_review"])
        self.assertIn("sanitized_not_true", report["identifier_redaction_evidence"]["blockers"])

    def test_rejects_claimed_principal_input_when_policy_checker_blocks(self) -> None:
        principal = json.loads(PRINCIPAL_INVALIDATION.read_text(encoding="utf-8"))
        principal["promotion_ready"] = True

        result = self.run_checker(principal_invalidation_payload=principal)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("principal_invalidation_policy_not_accepted", report["blockers"])
        self.assertIn("claimed_contract_review_input_not_accepted", report["blockers"])
        self.assertFalse(report["principal_invalidation_policy"]["ready"])
        self.assertIn("promotion_ready_not_false", report["principal_invalidation_policy"]["blockers"])


if __name__ == "__main__":
    unittest.main()
