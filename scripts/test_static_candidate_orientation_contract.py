#!/usr/bin/env python3
"""Tests for static_candidate_orientation_contract.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from static_candidate_orientation_contract import build_contract, validate_contract


class StaticCandidateOrientationContractTests(unittest.TestCase):
    def valid_contract(self) -> dict:
        return build_contract(
            topic="player_identity",
            binary_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
            target_set="players-identity-lifecycle-intake",
            expected_targets=["ShooterPlayerController.ServerListPlayers"],
            address_convention="non-PIE ELF VMA for this ARK Linux ShooterGameServer binary",
            subjects=[
                {
                    "target": "ShooterPlayerController.ServerListPlayers",
                    "kind": "ufunction_static_orientation",
                    "status": "candidate_only",
                    "registration_vma": "0x1368fa9",
                }
            ],
            non_claims=[
                "does not replace core evidence pack, reflection inventory pack, focal snapshots, second-source evidence, or lifecycle anchors",
                "does not promote public identity, runtime hooks, object lookup, or SDK surface",
                "does not promote permissions or commands",
                "does not promote mutation or return override",
            ],
            blockers=[
                "requires_non_protected_core_evidence_pack",
                "requires_full_reflection_inventory_pack_for_players_identity_lifecycle_intake",
            ],
        )

    def test_valid_candidate_only_contract_passes(self) -> None:
        self.assertEqual(validate_contract(self.valid_contract()), [])

    def test_readiness_overclaim_fails_closed(self) -> None:
        contract = self.valid_contract()
        contract["public_sdk_ready"] = True

        reasons = {blocker["reason"] for blocker in validate_contract(contract)}

        self.assertIn("static_orientation_contract_readiness_overclaim", reasons)

    def test_subject_promotion_token_fails_closed(self) -> None:
        contract = self.valid_contract()
        contract["subjects"][0]["note"] = "ResourceHandle promoted runtime_observed"

        reasons = {blocker["reason"] for blocker in validate_contract(contract)}

        self.assertIn("static_orientation_contract_subject_contains_promotion_token", reasons)

    def test_target_coverage_mismatch_fails_closed(self) -> None:
        contract = self.valid_contract()
        contract["subjects"] = []

        reasons = {blocker["reason"] for blocker in validate_contract(contract)}

        self.assertIn("static_orientation_contract_subjects_missing", reasons)
        self.assertIn("static_orientation_contract_target_coverage_mismatch", reasons)


if __name__ == "__main__":
    unittest.main()
