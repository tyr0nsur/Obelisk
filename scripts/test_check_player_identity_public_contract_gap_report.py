#!/usr/bin/env python3
"""Tests for check_player_identity_public_contract_gap_report.py."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_public_contract_gap_report.py"
DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
PRIVATE_CANDIDATE = REPO_ROOT / "docs" / "research" / "2026-06-01-player-identity-private-candidate-contract.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

SPEC = importlib.util.spec_from_file_location("player_identity_gap_report_checker", SCRIPT)
assert SPEC is not None
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checker)


class PlayerIdentityPublicContractGapReportTests(unittest.TestCase):
    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def load_surfaces(self) -> dict:
        return json.loads(SURFACES.read_text(encoding="utf-8"))

    def load_private_candidate(self) -> dict:
        return json.loads(PRIVATE_CANDIDATE.read_text(encoding="utf-8"))

    def player_identity_surface(self, surfaces: dict) -> dict:
        return next(item for item in surfaces["surfaces"] if item["id"] == checker.SURFACE)

    def run_checker(
        self,
        decisions: dict | None = None,
        surfaces: dict | None = None,
        candidate: dict | None = None,
        header_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            decisions_path = root / "decisions.json"
            surfaces_path = root / "surfaces.json"
            candidate_path = root / "private-candidate.json"
            header_path = root / "ObeliskApi.h"

            decisions_path.write_text(json.dumps(decisions if decisions is not None else self.load_decisions()), encoding="utf-8")
            surfaces_path.write_text(json.dumps(surfaces if surfaces is not None else self.load_surfaces()), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate if candidate is not None else self.load_private_candidate()), encoding="utf-8")
            header_path.write_text(header_text if header_text is not None else HEADER.read_text(encoding="utf-8"), encoding="utf-8")

            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--surfaces",
                    str(surfaces_path),
                    "--private-candidate-contract",
                    str(candidate_path),
                    "--public-header",
                    str(header_path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_accepts_current_blocked_state_without_runtime_evidence(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], checker.SCHEMA)
        self.assertEqual(report["surface"], checker.SURFACE)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["guardrail_passed"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(report["primary_offline_gap"], "privacy.identifier_redaction")
        self.assertTrue(report["runtime_evidence_missing"])
        self.assertEqual(report["surface_manifest"]["status"], "planning")
        self.assertEqual(report["surface_manifest"]["public_contract"], [])
        self.assertEqual(
            self.player_identity_surface(self.load_surfaces())["v1_decision_contract"]["decision_manifest"],
            "docs/player_identity_public_contract_decisions.json",
        )
        self.assertEqual(report["public_header_scan"]["detected_player_identity_tokens"], [])
        self.assertEqual(report["blockers"], [])

    def test_rejects_readiness_flags_that_become_true(self) -> None:
        decisions = self.load_decisions()
        surfaces = self.load_surfaces()
        candidate = self.load_private_candidate()
        decisions["public_header_allowed"] = True
        decisions["approved_runtime_evidence_intake"]["promotion_ready"] = True
        decisions["proposed_public_pod_abi_candidate"]["runtime_ready"] = True
        self.player_identity_surface(surfaces)["evidence"]["candidate_policy_artifacts"][0]["public_sdk_ready"] = True
        candidate["runtime_ready"] = True

        result = self.run_checker(decisions=decisions, surfaces=surfaces, candidate=candidate)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_public_header_allowed_not_false", report["blockers"])
        self.assertIn("readiness_flag_not_false", report["blockers"])
        labels = {detail["label"] for detail in report["blocker_details"] if detail["reason"] == "readiness_flag_not_false"}
        self.assertIn("$.approved_runtime_evidence_intake.promotion_ready", labels)
        self.assertIn("$.proposed_public_pod_abi_candidate.runtime_ready", labels)
        self.assertIn("$.evidence.candidate_policy_artifacts[0].public_sdk_ready", labels)
        self.assertIn("$.runtime_ready", labels)

    def test_rejects_missing_runtime_and_privacy_promotion_blockers(self) -> None:
        decisions = self.load_decisions()
        decisions["promotion_blockers"] = [
            item
            for item in decisions["promotion_blockers"]
            if item["id"] not in {"runtime.lifecycle_evidence", "privacy.identifier_redaction"}
        ]

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_required_promotion_blockers_missing", report["blockers"])
        detail = next(
            item for item in report["blocker_details"] if item["reason"] == "decisions_required_promotion_blockers_missing"
        )
        self.assertEqual(["privacy.identifier_redaction", "runtime.lifecycle_evidence"], detail["missing"])

    def test_rejects_missing_privacy_required_before_public_header_items(self) -> None:
        decisions = self.load_decisions()
        decisions["required_before_public_header"] = [
            item
            for item in decisions["required_before_public_header"]
            if item["id"] != "privacy.logging_and_storage_policy"
        ]

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_required_privacy_public_header_blockers_missing", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "decisions_required_privacy_public_header_blockers_missing"
        )
        self.assertEqual(["privacy.logging_and_storage_policy"], detail["missing"])

    def test_rejects_privacy_required_before_public_header_marked_resolved(self) -> None:
        decisions = self.load_decisions()
        for item in decisions["required_before_public_header"]:
            if item["id"] == "privacy.public_identifier_form":
                item["status"] = "resolved"

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_required_privacy_public_header_blocker_not_unresolved", report["blockers"])

    def test_rejects_surface_promotion_or_public_contract(self) -> None:
        surfaces = self.load_surfaces()
        surface = self.player_identity_surface(surfaces)
        surface["status"] = "promoted"
        surface["public_contract"] = ["ObeliskRegisterPlayerIdentityCallback"]
        surfaces["planning_surfaces"].remove(checker.SURFACE)
        surfaces["promoted_surfaces"].append(checker.SURFACE)

        result = self.run_checker(surfaces=surfaces)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("player_identity_surface_status_not_planning", report["blockers"])
        self.assertIn("player_identity_surface_public_contract_not_empty", report["blockers"])
        self.assertIn("player_identity_missing_from_planning_surfaces", report["blockers"])
        self.assertIn("player_identity_in_non_planning_surface_list", report["blockers"])

    def test_rejects_identity_or_principal_symbols_in_public_header(self) -> None:
        header = "\n".join(
            [
                "#pragma once",
                "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY (1ull << 1)",
                "// ObeliskPlayerPrincipalEvent in a comment is ignored.",
                "static const char* ignored = \"RegisterPlayerIdentity\";",
                "#define OBELISK_API_CAPABILITY_PLAYER_IDENTITY (1ull << 12)",
                "typedef struct ObeliskPlayerPrincipalEvent { uint64_t principal_handle; } ObeliskPlayerPrincipalEvent;",
                "typedef uint64_t ObeliskPlayerIdentityHandle;",
            ]
        )

        result = self.run_checker(header_text=header)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_identity_or_principal_symbols_detected", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_identity_or_principal_symbols_detected")
        detected = {item["token"] for item in detail["detected_tokens"]}
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_IDENTITY", detected)
        self.assertIn("ObeliskPlayerPrincipalEvent", detected)
        self.assertIn("principal_handle", detected)
        self.assertIn("ObeliskPlayerIdentityHandle", detected)
        self.assertNotIn("OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY", detected)

    def test_rejects_forbidden_positive_identity_exposure_in_private_candidate(self) -> None:
        candidate = self.load_private_candidate()
        candidate["candidate_event_payload_fields_or_equivalent"].extend(
            [
                "steam_id",
                "EOS_account_id",
                "UniqueNetId",
                "PlayerDataID",
                "player_name",
                "tribe_id",
                "IP_address",
                "UE_pointer",
                "FName_index",
                "GObjects_index",
                "ResourceHandle",
                "lookup_handle",
                "persistent_identity",
                "mutation_token",
                "return_override_policy",
            ]
        )

        result = self.run_checker(candidate=candidate)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_forbidden_public_identity_exposure", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "private_candidate_forbidden_public_identity_exposure")
        terms = {item["term"] for item in detail["exposures"]}
        self.assertEqual(
            terms,
            {
                "steam_id",
                "eos",
                "unique_net_id",
                "player_data_id",
                "player_name",
                "tribe",
                "ip_or_network_address",
                "ue_pointer",
                "fname_gobjects",
                "resource_handle",
                "lookup",
                "persistence",
                "mutation",
                "return_override",
            },
        )

    def test_forbidden_negative_non_claims_remain_allowed(self) -> None:
        candidate = copy.deepcopy(self.load_private_candidate())

        self.assertEqual(checker.candidate_exposures(candidate), [])
        result = self.run_checker(candidate=candidate)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, report["blocker_details"])
        self.assertEqual(report["blockers"], [])


if __name__ == "__main__":
    unittest.main()
