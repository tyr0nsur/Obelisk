#!/usr/bin/env python3
"""Tests for check_player_identity_public_contract_readiness.py."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_public_contract_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import manifest as approved_manifest
from test_check_player_identity_identifier_redaction_evidence import evidence as redaction_manifest
import check_player_identity_public_contract_readiness as checker


class PlayerIdentityPublicContractReadinessTests(unittest.TestCase):
    def normalize_runtime_manifest_paths(self, runtime: dict) -> dict:
        return copy.deepcopy(runtime)

    def run_checker(
        self,
        decisions: dict,
        runtime: dict,
        *args: str,
        redaction: dict | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            redaction_args = []
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            runtime_path.write_text(json.dumps(self.normalize_runtime_manifest_paths(runtime)), encoding="utf-8")
            if redaction is not None:
                redaction_path = root / "identifier-redaction.json"
                redaction_path.write_text(json.dumps(redaction), encoding="utf-8")
                redaction_args = ["--identifier-redaction-evidence", str(redaction_path)]
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    *redaction_args,
                    "--json",
                    *args,
                ],
                check=False,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
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
        self.assertTrue(report["public_header_scan"]["readable"])
        self.assertEqual(report["public_header_scan"]["detected_player_identity_tokens"], [])
        self.assertEqual(report["required_tests_before_public_header"]["covered_for_contract_review_only"], ["runtime.evidence_intake"])
        self.assertIn("abi.layout", report["required_tests_before_public_header"]["remaining_missing"])
        self.assertIn("privacy.identifier_redaction", report["remaining_blockers"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate")
        self.assertNotEqual(report["next_blocker"], "public_readiness")
        self.assertEqual(report["blockers"], [])
        self.assertFalse(report["identifier_redaction_evidence"]["provided"])
        self.assertFalse(report["identifier_redaction_evidence"]["accepted_for_contract_review"])

    def test_accepts_identifier_redaction_evidence_for_contract_review_only(self) -> None:
        result = self.run_checker(self.decisions(), approved_manifest(), redaction=redaction_manifest())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertEqual(
            report["resolved_inputs"],
            ["runtime.lifecycle_evidence", "privacy.identifier_redaction"],
        )
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertIn("privacy.identifier_redaction", report["remaining_blockers"])
        self.assertTrue(report["identifier_redaction_evidence"]["provided"])
        self.assertTrue(report["identifier_redaction_evidence"]["accepted_for_contract_review"])
        self.assertFalse(report["identifier_redaction_evidence"]["promotion_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["public_sdk_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["runtime_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["public_header_allowed"])

    def test_rejects_identifier_redaction_evidence_that_overclaims_or_fails_validation(self) -> None:
        redaction = redaction_manifest()
        redaction["public_sdk_ready"] = True
        redaction["sample_logs"][0]["message"] = "free form sanitized log"

        result = self.run_checker(self.decisions(), approved_manifest(), redaction=redaction, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identifier_redaction_evidence_not_accepted", report["blockers"])
        self.assertIn("identifier_redaction_evidence_public_sdk_ready_not_false", report["blockers"])
        self.assertEqual(report["next_blocker"], "player_identity_public_contract_gate_not_accepted")

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
        self.assertEqual(
            set(candidate["candidate_event_kind_mask"]),
            {"session_start", "session_start_rejected", "session_end"},
        )
        self.assertIn("process_local", candidate["candidate_scope_flags"])
        self.assertIn("stale_generation", candidate["candidate_state_flags"])
        self.assertIn("server_restart", candidate["candidate_invalidation_reason_flags"])
        self.assertIn("no_lookup", candidate["candidate_contract_flags"])
        self.assertIn(
            "event_sequence is assigned once per copied source lifecycle event",
            candidate["sequence_policy"],
        )
        self.assertIn(
            "event_sequence is not a per-plugin delivery counter",
            candidate["sequence_policy"],
        )
        self.assertIn(
            "server_process_epoch invalidates process-local principal handles after restart",
            candidate["server_process_epoch_policy"],
        )

        result = self.run_checker(decisions, approved_manifest())
        report = json.loads(result.stdout)
        self.assertEqual(report["blockers"], [])
        self.assertEqual(
            report["private_candidate_contract"]["path"],
            "docs/research/2026-06-01-player-identity-private-candidate-contract.json",
        )
        self.assertEqual(report["private_candidate_contract"]["artifact_status"], "candidate_only")
        self.assertEqual(report["private_candidate_contract"]["visibility"], "private_planning_contract")
        self.assertTrue(report["private_candidate_contract"]["candidate_only"])
        self.assertFalse(report["private_candidate_contract"]["public_header_allowed"])

    def test_rejects_private_candidate_contract_path_rerouted_to_public_docs(self) -> None:
        decisions = self.decisions()
        decisions["private_candidate_contract"] = "docs/player_identity_private_candidate_contract.json"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_contract_path_mismatch", report["blockers"])

    def test_rejects_private_candidate_contract_missing_stable_principal_non_claim(self) -> None:
        decisions = self.decisions()
        private_contract = json.loads(
            (REPO_ROOT / "docs/research/2026-06-01-player-identity-private-candidate-contract.json").read_text(
                encoding="utf-8"
            )
        )
        private_contract["non_claims"].remove("This artifact does not claim stable principal identity.")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_path = root / "private-candidate.json"
            private_path.write_text(json.dumps(private_contract), encoding="utf-8")
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--private-candidate-contract",
                    str(private_path),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    "--json",
                ],
                check=False,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_non_claims_missing", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "private_candidate_non_claims_missing"
        )
        self.assertIn("This artifact does not claim stable principal identity.", detail["missing"])

    def test_rejects_private_candidate_contract_missing_stale_handle_fail_closed_rule(self) -> None:
        decisions = self.decisions()
        private_contract = json.loads(
            (REPO_ROOT / "docs/research/2026-06-01-player-identity-private-candidate-contract.json").read_text(
                encoding="utf-8"
            )
        )
        private_contract["candidate_stale_handle_fail_closed_semantics"].remove(
            "stale handles never resolve to a different player"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_path = root / "private-candidate.json"
            private_path.write_text(json.dumps(private_contract), encoding="utf-8")
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--private-candidate-contract",
                    str(private_path),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    "--json",
                ],
                check=False,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_stale_handle_fail_closed_semantics_missing", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "private_candidate_stale_handle_fail_closed_semantics_missing"
        )
        self.assertIn("stale handles never resolve to a different player", detail["missing"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

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

    def test_rejects_decision_gate_rerouted_to_public_readiness(self) -> None:
        decisions = self.decisions()
        gate = decisions["decision_gate"]
        gate["id"] = "public_readiness"
        gate["status"] = "ready"
        gate["current_decision"] = "approved runtime evidence accepted; next blocker is public readiness"
        gate["allowed_now"].append("public readiness")
        gate["forbidden_now"].remove("player lookup API")

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["next_blocker"], "player_identity_public_contract_gate_not_accepted")
        for blocker in (
            "decision_gate_id_mismatch",
            "decision_gate_status_mismatch",
            "decision_gate_current_decision_mismatch",
            "decision_gate_allowed_now_mismatch",
            "decision_gate_forbidden_now_mismatch",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_unmanifested_player_identity_tokens_in_public_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "ObeliskApi.h"
            header.write_text(
                "\n".join(
                    [
                        "#pragma once",
                        "#define OBELISK_API_CAPABILITY_PLAYER_IDENTITY (1ull << 12)",
                        "typedef struct ObeliskPlayerPrincipalEvent {",
                        "    uint64_t principal_handle;",
                        "} ObeliskPlayerPrincipalEvent;",
                        "typedef uint64_t ObeliskPlayerId;",
                        "typedef uint64_t ObeliskPlayerHandle;",
                        "uint64_t (*RegisterPlayerIdentityEventWithOwnerTokenHandle)(uint64_t ownerToken);",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--public-header",
                str(header),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_header_contains_unmanifested_player_identity_tokens", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "public_header_contains_unmanifested_player_identity_tokens"
        )
        detected = {item["token"] for item in detail["detected_tokens"]}
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_IDENTITY", detected)
        self.assertIn("ObeliskPlayerPrincipalEvent", detected)
        self.assertIn("principal_handle", detected)
        self.assertIn("ObeliskPlayerId", detected)
        self.assertIn("ObeliskPlayerHandle", detected)
        self.assertIn("RegisterPlayerIdentityEventWithOwnerTokenHandle", detected)

    def test_public_header_scan_ignores_comments_strings_and_existing_no_identity_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "ObeliskApi.h"
            header.write_text(
                "\n".join(
                    [
                        "#pragma once",
                        "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY (1ull << 1)",
                        "// ObeliskPlayerPrincipalEvent is not a public symbol here.",
                        "static const char* label = \"RegisterPlayerIdentityEventWithOwnerTokenHandle\";",
                    ]
                ),
                encoding="utf-8",
            )

            detected = checker.public_header_identity_tokens(header)

        self.assertEqual(detected, [])

    def test_rejects_fake_public_header_path_even_without_identity_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "ObeliskApi.h"
            header.write_text("/* no player identity ABI */\n", encoding="utf-8")
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--public-header",
                str(header),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_path_mismatch", report["blockers"])
        self.assertIn("decisions_public_header_not_scanned_header", report["blockers"])

    def test_rejects_public_header_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "ObeliskApi.h"
            target.write_text("/* no player identity ABI */\n", encoding="utf-8")
            link = root / "ObeliskApi-link.h"
            link.symlink_to(target)
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--public-header",
                str(link),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_path_rejected", report["blockers"])

    def test_rejects_decisions_symlink_component_with_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            decisions_path.write_text(json.dumps(self.decisions()), encoding="utf-8")
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            link = root / "decisions-link.json"
            link.symlink_to(decisions_path)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(link),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    "--json",
                ],
                check=False,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertIn("decisions_path_rejected", report["blockers"])

    def test_rejects_private_candidate_contract_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "private-candidate.json"
            target.write_text(
                (REPO_ROOT / "docs/research/2026-06-01-player-identity-private-candidate-contract.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            link = root / "private-candidate-link.json"
            link.symlink_to(target)
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--private-candidate-contract",
                str(link),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_contract_path_rejected", report["blockers"])

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

    def test_rejects_candidate_lookup_persistence_scope_and_private_identity_fields(self) -> None:
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
                "persistent_principal_handle",
                "cluster_stable_principal_handle",
                "cross_process_principal_handle",
                "cross_map_principal_handle",
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
            "persistent",
            "cluster",
            "cross_process",
            "cross_map",
        ):
            with self.subTest(token=token):
                self.assertIn(token, detail["forbidden"])

    def test_rejects_candidate_process_local_non_persistent_requirements_removed(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["required_payload_properties"].remove(
            "principal handles are process-local and non-persistent"
        )
        candidate["candidate_registration_shape_or_equivalent"].remove(
            "registration handles are process-local and non-persistent"
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_required_payload_properties_missing", report["blockers"])
        self.assertIn("candidate_owner_token_cleanup_requirements_missing", report["blockers"])
        payload_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_required_payload_properties_missing"
        )
        self.assertIn(
            "principal handles are process-local and non-persistent",
            payload_detail["missing"],
        )
        registration_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_owner_token_cleanup_requirements_missing"
        )
        self.assertIn(
            "registration handles are process-local and non-persistent",
            registration_detail["missing"],
        )

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

    def test_rejects_candidate_masks_flags_and_sequence_policy_weakened(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_event_kind_mask"].remove("session_end")
        candidate["candidate_scope_flags"].remove("process_local")
        candidate["candidate_state_flags"].remove("stale_generation")
        candidate["candidate_invalidation_reason_flags"].remove("server_restart")
        candidate["candidate_contract_flags"].remove("no_lookup")
        candidate["sequence_policy"].remove(
            "event_sequence is not a per-plugin delivery counter"
        )
        candidate["server_process_epoch_policy"].remove(
            "server_process_epoch invalidates process-local principal handles after restart"
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "candidate_event_kind_mask_missing",
            "candidate_scope_flags_missing",
            "candidate_state_flags_missing",
            "candidate_invalidation_reason_flags_missing",
            "candidate_contract_flags_missing",
            "candidate_sequence_policy_missing",
            "candidate_server_process_epoch_policy_missing",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

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

    def test_rejects_missing_or_weakened_identifier_redaction_intake(self) -> None:
        decisions = self.decisions()
        decisions["identifier_redaction_evidence_intake"]["public_sdk_ready"] = True
        decisions["identifier_redaction_evidence_intake"]["required_checker"] = "scripts/other.py"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identifier_redaction_evidence_intake_checker_mismatch", report["blockers"])
        self.assertIn("identifier_redaction_evidence_intake_public_sdk_ready_not_false", report["blockers"])

        decisions = self.decisions()
        decisions.pop("identifier_redaction_evidence_intake")
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identifier_redaction_evidence_intake_missing", report["blockers"])

    def test_approved_runtime_report_must_route_to_identity_public_contract_gate(self) -> None:
        original_build_report = checker.approved_evidence.build_report

        def wrong_next_blocker(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["next_blocker"] = "runtime_ready"
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}), mock.patch.object(
                checker.approved_evidence,
                "build_report",
                side_effect=wrong_next_blocker,
            ):
                checker.approved_runtime_report(runtime_path, blockers)

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["approved_runtime_evidence_next_blocker_mismatch"],
        )

    def test_approved_runtime_report_must_not_overclaim_public_readiness(self) -> None:
        original_build_report = checker.approved_evidence.build_report

        def overclaiming_report(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["public_sdk_ready"] = True
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}), mock.patch.object(
                checker.approved_evidence,
                "build_report",
                side_effect=overclaiming_report,
            ):
                checker.approved_runtime_report(runtime_path, blockers)

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["approved_runtime_evidence_public_sdk_ready_not_false"],
        )

    def test_approved_runtime_report_must_not_overclaim_public_header_allowed(self) -> None:
        original_build_report = checker.approved_evidence.build_report

        def overclaiming_report(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["public_header_allowed"] = True
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}), mock.patch.object(
                checker.approved_evidence,
                "build_report",
                side_effect=overclaiming_report,
            ):
                checker.approved_runtime_report(runtime_path, blockers)

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["approved_runtime_evidence_public_header_allowed_not_false"],
        )

    def test_approved_runtime_report_accumulates_route_and_public_overclaims(self) -> None:
        original_build_report = checker.approved_evidence.build_report

        def mismatched_and_overclaiming_report(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["next_blocker"] = "runtime_ready"
            report["promotion_ready"] = True
            report["runtime_ready"] = True
            report["public_header_allowed"] = True
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}), mock.patch.object(
                checker.approved_evidence,
                "build_report",
                side_effect=mismatched_and_overclaiming_report,
            ):
                checker.approved_runtime_report(runtime_path, blockers)

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            [
                "approved_runtime_evidence_next_blocker_mismatch",
                "approved_runtime_evidence_promotion_ready_not_false",
                "approved_runtime_evidence_runtime_ready_not_false",
                "approved_runtime_evidence_public_header_allowed_not_false",
            ],
        )

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
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
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

    def test_rejects_runtime_evidence_sufficiency_or_nonclaim_weakened(self) -> None:
        decisions = self.decisions()
        decisions["approved_runtime_evidence_not_sufficient"]["why"].remove(
            "runtime evidence does not prove process-local scope, cross-instance isolation, or cluster identity semantics"
        )
        decisions["approved_runtime_evidence_not_sufficient"]["minimum_additional_gates"].remove(
            "cross-instance/process-local scope decision resolved"
        )
        decisions["non_claims"].remove(
            "This manifest does not make approved runtime evidence sufficient by itself."
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_not_sufficient_why_missing", report["blockers"])
        self.assertIn("approved_runtime_evidence_not_sufficient_minimum_gates_missing", report["blockers"])
        self.assertIn("non_claims_missing_required", report["blockers"])

    def test_rejects_required_before_public_header_contract_weakened(self) -> None:
        decisions = self.decisions()
        requirements = {
            item["id"]: item
            for item in decisions["required_before_public_header"]
        }
        requirements["privacy.public_identifier_form"]["must_not_expose"].remove("SteamID")
        requirements["privacy.public_identifier_form"]["required_properties"].remove(
            "generation-bearing or otherwise invalidation-aware"
        )
        requirements["privacy.redacted_identifier_fields"]["must_redact"].remove("platform account ids")
        requirements["privacy.logging_and_storage_policy"]["default_policy"] = "log opaque identity for audit"
        requirements["lifetime.principal_scope"]["allowed_scopes"].append("cluster-stable")
        requirements["lifetime.principal_scope"]["forbidden_until_separate_promotion"].remove("cluster-stable")
        requirements["lifetime.principal_scope"]["required_fields"].remove("principal_generation")
        requirements["lifetime.invalidation_events"]["required_behavior"].remove("stale principal fails closed")
        requirements["lifetime.reconnect_duplicate_stale_policy"]["required_policy"].remove(
            "stale handles never resolve to a different player"
        )
        requirements["abi.capability_bits"]["required_behavior"].remove("missing capability fails closed")
        requirements["abi.owner_token_registration"]["required_behavior"].remove("nonzero plugin_owner_token required")
        requirements["abi.owner_token_registration"]["required_behavior"].remove(
            "registration handles are not persisted or shared across server processes"
        )
        requirements["separation.no_commands_permissions_persistence"]["forbidden_in_identity_contract"].remove(
            "storage/persistence"
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "privacy_public_identifier_form_missing_forbidden_terms",
            "privacy_public_identifier_form_missing_required_properties",
            "privacy_redacted_identifier_fields_missing_redactions",
            "privacy_logging_storage_default_policy_mismatch",
            "lifetime_principal_scope_forbidden_scope_allowed",
            "lifetime_principal_scope_missing_forbidden_scopes",
            "lifetime_principal_scope_missing_required_fields",
            "lifetime_invalidation_behavior_missing",
            "lifetime_reconnect_duplicate_stale_policy_missing",
            "abi_capability_bits_missing_fail_closed_behavior",
            "abi_owner_token_registration_missing_fail_closed_behavior",
            "separation_forbidden_downstream_surfaces_missing",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

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

    def test_rejects_pre_header_required_coverage_weakened(self) -> None:
        decisions = self.decisions()
        tests = {
            item["id"]: item
            for item in decisions["required_tests_before_public_header"]
        }
        tests["sdk.consumer"]["required_coverage"].remove(
            "consumer treats principal handles and registration handles as process-local and non-persistent"
        )
        tests["lifecycle.owner_cleanup"]["required_coverage"].remove(
            "plugin unload drains in-flight callbacks"
        )
        tests["identity.fail_closed"]["required_coverage"].remove(
            "cross-instance or cross-process handle reuse fails closed"
        )
        tests["runtime.evidence_intake"]["required_coverage"].remove(
            "approved runtime evidence cannot set promotion_ready, public_sdk_ready, runtime_ready, or public_header_allowed"
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_test_coverage_missing", report["blockers"])
        coverage_blockers = [
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "required_test_coverage_missing"
        ]
        self.assertEqual(len(coverage_blockers), 4)

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
