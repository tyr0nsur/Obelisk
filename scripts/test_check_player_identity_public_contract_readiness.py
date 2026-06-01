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
    def normalize_runtime_manifest_paths(self, runtime: dict) -> dict:
        payload = copy.deepcopy(runtime)
        safe_path = "/tmp/obelisk-approved-runtime.log"
        payload["operational_window"]["copied_log"]["path"] = safe_path
        payload["source_summary"]["evidence"]["sources"][0]["path"] = safe_path
        return payload

    def run_checker(self, decisions: dict, runtime: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            runtime_path.write_text(json.dumps(self.normalize_runtime_manifest_paths(runtime)), encoding="utf-8")
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
        self.assertEqual(report["required_tests_before_public_header"]["covered_for_contract_review_only"], ["runtime.evidence_intake"])
        self.assertIn("abi.layout", report["required_tests_before_public_header"]["remaining_missing"])
        self.assertIn("privacy.identifier_redaction", report["remaining_blockers"])
        self.assertEqual(report["blockers"], [])

    def test_accepts_candidate_only_pod_abi_shape(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]

        self.assertEqual(candidate["status"], "proposal_only_not_public")
        self.assertTrue(candidate["candidate_only"])
        self.assertFalse(candidate["public_header_allowed"])
        self.assertFalse(candidate["promotion_ready"])
        self.assertFalse(candidate["public_sdk_ready"])
        self.assertFalse(candidate["runtime_ready"])
        self.assertEqual(
            set(candidate["candidate_event_payload_fields_or_equivalent"]),
            {
                "abi_version",
                "struct_size",
                "event_kind",
                "principal_handle",
                "principal_generation",
                "principal_scope_flags",
                "principal_state_flags",
                "invalidation_reason_flags",
                "event_sequence",
                "server_process_epoch",
                "reserved",
            },
        )

        result = self.run_checker(decisions, approved_manifest())
        report = json.loads(result.stdout)
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

    def test_rejects_candidate_public_promotion_or_runtime_claims(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["status"] = "public"
        candidate["candidate_only"] = False
        candidate["public_header_allowed"] = True
        candidate["promotion_ready"] = True
        candidate["runtime_ready"] = True

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_status_not_proposal_only", report["blockers"])
        self.assertIn("candidate_only_not_true", report["blockers"])
        self.assertIn("candidate_public_header_allowed_not_false", report["blockers"])
        self.assertIn("candidate_public_header_allowed_claim_not_false", report["blockers"])
        self.assertIn("candidate_promotion_ready_claim_not_false", report["blockers"])
        self.assertIn("candidate_runtime_ready_claim_not_false", report["blockers"])

    def test_rejects_candidate_missing_required_payload_fields(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_event_payload_fields_or_equivalent"].remove("reserved")
        candidate["candidate_event_payload_fields_or_equivalent"].remove("principal_generation")

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_event_payload_fields_missing", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_event_payload_fields_missing"
        )
        self.assertEqual(detail["missing"], ["principal_generation", "reserved"])

    def test_rejects_candidate_lookup_resolve_get_and_private_identity_fields(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_event_payload_fields_or_equivalent"].extend(
            [
                "lookup_handle",
                "resolve_player_name",
                "get_platform_id",
                "raw_UE_player_pointer",
                "private_identity_token",
                "tribe_id",
                "IP_address",
                "FName_index",
                "GObjects_index",
                "ResourceHandle",
            ]
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_event_payload_fields_forbidden_identity_or_lookup", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_event_payload_fields_forbidden_identity_or_lookup"
        )
        for token in (
            "lookup",
            "resolve",
            "get",
            "raw_ue",
            "private_identity",
            "platform",
            "player_name",
            "tribe",
            "ip",
            "fname_gobjects",
            "resource_handle",
        ):
            with self.subTest(token=token):
                self.assertIn(token, detail["forbidden"])

    def test_rejects_candidate_owner_token_cleanup_requirements_removed(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_registration_shape_or_equivalent"] = [
            "event-kind mask required",
            "opaque uint64 registration handle returned on success",
            "callback payload storage is valid only for the callback",
        ]
        candidate["candidate_capability_policy"] = [
            "capability must be captured in the init-time API table",
            "later marker or env changes cannot widen a plugin's captured capability",
        ]

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_owner_token_cleanup_requirements_missing", report["blockers"])
        self.assertIn("candidate_fail_closed_policy_missing", report["blockers"])
        registration_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_owner_token_cleanup_requirements_missing"
        )
        self.assertIn("nonzero plugin_owner_token required", registration_detail["missing"])
        self.assertIn("plugin init failure removes registrations", registration_detail["missing"])
        self.assertIn("plugin unload removes registrations and drains in-flight callbacks", registration_detail["missing"])
        policy_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_fail_closed_policy_missing"
        )
        self.assertIn("missing or zero owner token fails closed", policy_detail["missing"])

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

    def test_missing_runtime_evidence_path_reports_json_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            missing_runtime_path = root / "missing-approved-runtime.json"
            decisions_path.write_text(json.dumps(self.decisions()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--approved-runtime-evidence",
                    str(missing_runtime_path),
                    "--json",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertIn("approved_runtime_evidence_unreadable", report["blockers"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])

    def test_rejects_forbidden_contract_terms_removed(self) -> None:
        decisions = self.decisions()
        decisions["forbidden_public_contract"] = ["lookup"]
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])

    def test_rejects_pre_header_test_overclaims(self) -> None:
        decisions = self.decisions()
        for item in decisions["required_tests_before_public_header"]:
            if item["id"] == "runtime.evidence_intake":
                item["promotion_ready"] = True
            elif item["id"] == "abi.layout":
                item["status"] = "covered"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract_review_input_test_promotion_ready_not_false", report["blockers"])
        self.assertIn("pre_header_test_marked_ready_without_public_gate", report["blockers"])

    def test_malformed_required_tests_reports_json_blocker(self) -> None:
        decisions = self.decisions()
        decisions["required_tests_before_public_header"] = {}

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_tests_before_public_header_not_list", report["blockers"])
        self.assertIn("required_tests_before_public_header_mismatch", report["blockers"])

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
