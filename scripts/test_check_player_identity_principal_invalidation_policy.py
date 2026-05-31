#!/usr/bin/env python3
"""Tests for check_player_identity_principal_invalidation_policy.py."""

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
SCRIPT = SCRIPT_DIR / "check_player_identity_principal_invalidation_policy.py"


def manifest() -> dict:
    rejected_sources = [
        "SteamID",
        "EOSID",
        "UniqueNetId",
        "PlayerID",
        "PlayerDataID",
        "PlayerName",
        "IPAddress",
        "TribeID",
        "ResourceHandle",
        "GObjects",
        "FNames",
        "UObjectPointer",
    ]
    return {
        "schema": "obelisk.players-identity-principal-invalidation-policy.v1",
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "lifecycle_layout_source": {
            "status": "candidate_layout_consumable",
            "accepted_layout_only": True,
            "start_anchor": "ShooterGameMode.HandleNewPlayer",
            "end_anchor": "ShooterGameMode.OnLogout",
            "principal_invalidation_evidence": "candidate_policy_only",
        },
        "principal": {
            "kind": "copied_opaque_principal",
            "copied": True,
            "ownership": "obelisk_owned_copy",
            "public_identity": "opaque_principal_only",
            "reversible": False,
            "stable_across_processes": False,
            "real_identity_source": None,
            "fields": [
                {
                    "name": "principal",
                    "type": "opaque_bytes",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "opaque_principal",
                },
                {
                    "name": "generation",
                    "type": "uint64",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "state",
                    "type": "enum",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "scope_flags",
                    "type": "uint64_flags",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "privacy_class",
                    "type": "enum",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
            ],
        },
        "generation": {
            "field": "generation",
            "zero_invalid": True,
            "increments_on": [
                "session_start",
                "logout_or_disconnect_invalidation",
                "reconnect_after_invalidation",
                "transfer_or_download_edge",
                "duplicate_or_conflicting_identity",
                "server_restart",
                "plugin_reload",
            ],
        },
        "state": {
            "field": "state",
            "allowed": ["unknown", "active", "invalidated"],
            "fail_closed_states": ["unknown", "invalidated"],
        },
        "scope_flags": {
            "field": "scope_flags",
            "allowed_flags": ["process_local", "session_local", "not_cross_cluster"],
            "forbidden_flags": ["persistent", "cross_process", "cross_cluster"],
        },
        "privacy_class": {
            "field": "privacy_class",
            "allowed": ["opaque_principal", "internal_sensitive", "redacted"],
            "public_value": "opaque_principal",
        },
        "invalidation_cases": [
            {
                "case": "logout_or_disconnect",
                "trigger": "ShooterGameMode.OnLogout",
                "generation_action": "increment_or_retire",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "reconnect_after_invalidation",
                "trigger": "new_session_after_invalidated_principal",
                "generation_action": "allocate_new_generation",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "transfer_or_download_edge",
                "trigger": "transfer_download_without_promoted_identity_continuity",
                "generation_action": "retire_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "stale_controller_or_player_state",
                "trigger": "controller_or_player_state_replaced",
                "generation_action": "invalidate_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "duplicate_or_conflicting_identity",
                "trigger": "conflicting_candidate_identity_evidence",
                "generation_action": "invalidate_conflict_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "server_restart",
                "trigger": "process_restart_boundary",
                "generation_action": "invalidate_all_prior_generations",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "plugin_reload",
                "trigger": "plugin_owner_cleanup_or_reload",
                "generation_action": "deny_cached_plugin_values",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "trigger": "unsupported_or_malformed_identity_input",
                "generation_action": "clear_output_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
        ],
        "negative_consumer_rules": [
            {
                "rule": "no_real_identity_public",
                "forbids": [
                    "SteamID",
                    "EOSID",
                    "UniqueNetId",
                    "PlayerID",
                    "PlayerDataID",
                    "PlayerName",
                    "IPAddress",
                    "TribeID",
                ],
                "fail_closed": True,
            },
            {
                "rule": "no_ue_pointer_or_handle_identity",
                "forbids": ["ResourceHandle", "GObjects", "FNames", "UObjectPointer"],
                "fail_closed": True,
            },
            {
                "rule": "no_lookup_or_persistence_from_principal",
                "forbids": ["lookup", "persistent_identity", "cross_process_identity"],
                "fail_closed": True,
            },
            {
                "rule": "no_return_override_or_mutation_authority",
                "forbids": ["return_override", "mutation"],
                "fail_closed": True,
            },
            {
                "rule": "no_commands_or_permissions_claims",
                "forbids": ["commands", "permissions"],
                "fail_closed": True,
            },
            {
                "rule": "fail_closed_on_invalid_or_stale",
                "forbids": ["fallback_to_real_id", "best_effort_lookup"],
                "fail_closed": True,
            },
        ],
        "rejected_public_identity_sources": rejected_sources,
        "evidence_policy": {
            "accepted_evidence_class": "candidate_policy_only",
            "malformed_evidence_result": "deny",
            "unsupported_evidence_result": "deny",
            "fail_closed": True,
        },
        "runtime_evidence": {
            "status": "not_approved",
            "approved": False,
            "required_for": ["promote", "public_readiness", "runtime_readiness"],
        },
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "approved_runtime_evidence_missing",
                "principal_invalidation_semantics_unresolved",
                "candidate_only_policy",
            ],
        },
        "safety_summary": {
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": [
                "real_player_ids",
                "steam_ids",
                "eos_ids",
                "player_names",
                "ip_addresses",
                "tribe_ids",
                "ue_pointers",
                "ResourceHandle",
                "GObjects",
                "FNames",
                "lookup",
                "mutation",
                "return_override",
                "commands",
                "permissions",
                "persistence",
                "public_sdk",
                "runtime_readiness",
            ],
        },
        "non_claims": [
            "candidate-only principal invalidation policy",
            "does not expose real player identifiers, Steam/EOS, names, IPs, or tribe ids",
            "does not expose UE pointers, ResourceHandle, GObjects, FNames, lookup, mutation, or persistence",
            "does not expose return override, commands, permissions, moderation, or admin authority",
            "promote, public SDK readiness, and runtime readiness require separately approved runtime evidence",
        ],
    }


class PlayerIdentityPrincipalInvalidationPolicyTests(unittest.TestCase):
    def run_checker(self, payload: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json", *args],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_accepts_candidate_only_opaque_principal_policy(self) -> None:
        result = self.run_checker(manifest())
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertEqual(report["mode"], "consume")
        self.assertEqual(
            report["principal_fields"],
            ["generation", "principal", "privacy_class", "scope_flags", "state"],
        )
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["principal_invalidation_ready"])
        self.assertEqual(report["remaining_blockers"], ["principal_invalidation_semantics_unresolved"])

    def test_promote_public_and_runtime_modes_fail_closed(self) -> None:
        for flag, expected in (
            ("--promote", "promote_blocked_without_approved_runtime_evidence"),
            ("--public-readiness", "public_readiness_blocked_without_approved_runtime_evidence"),
            ("--runtime-readiness", "runtime_readiness_blocked_without_approved_runtime_evidence"),
        ):
            with self.subTest(flag=flag):
                result = self.run_checker(manifest(), flag, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, report["blockers"])
                self.assertIn(
                    f"{flag.removeprefix('--').replace('-', '_')}_blocked_principal_invalidation_semantics_unresolved",
                    report["blockers"],
                )
                self.assertIn(
                    "candidate_only_principal_invalidation_policy_not_readiness_evidence",
                    report["blockers"],
                )
                self.assertFalse(report["promotion_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_real_identity_as_public_principal(self) -> None:
        payload = manifest()
        payload["principal"]["public_identity"] = "SteamID"
        payload["principal"]["real_identity_source"] = "SteamID"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("principal_public_identity_not_opaque", report["blockers"])
        self.assertIn("principal_real_identity_source_overclaim", report["blockers"])
        self.assertIn("forbidden_public_identity_source", report["blockers"])

    def test_rejects_ue_pointer_or_resource_handle_identity_fields(self) -> None:
        for field_name in ("ResourceHandle", "FNameIndex", "GObjectsIndex", "UObjectPointer"):
            with self.subTest(field_name=field_name):
                payload = manifest()
                field = copy.deepcopy(payload["principal"]["fields"][0])
                field["name"] = field_name
                payload["principal"]["fields"].append(field)

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn("principal_field_unexpected", report["blockers"])
                self.assertIn("forbidden_public_identity_source", report["blockers"])

    def test_rejects_missing_required_principal_field(self) -> None:
        payload = manifest()
        payload["principal"]["fields"] = [
            field for field in payload["principal"]["fields"] if field["name"] != "generation"
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("principal_fields_missing_required", report["blockers"])

    def test_rejects_missing_minimal_invalidation_case(self) -> None:
        payload = manifest()
        payload["invalidation_cases"] = [
            case for case in payload["invalidation_cases"] if case["case"] != "malformed_or_unsupported_evidence"
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("invalidation_cases_missing_required", report["blockers"])

    def test_rejects_non_fail_closed_invalidation_case(self) -> None:
        payload = manifest()
        payload["invalidation_cases"][0]["fail_closed"] = False
        payload["invalidation_cases"][0]["consumer_result"] = "allow"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("invalidation_case_not_fail_closed", report["blockers"])
        self.assertIn("invalidation_case_consumer_result_not_denied", report["blockers"])

    def test_rejects_missing_negative_consumer_rule_coverage(self) -> None:
        payload = manifest()
        payload["negative_consumer_rules"][0]["forbids"].remove("SteamID")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("negative_consumer_rules_missing_forbidden_identity_sources", report["blockers"])

    def test_rejects_readiness_overclaims_and_approved_runtime_evidence(self) -> None:
        payload = manifest()
        payload["promotion_ready"] = True
        payload["public_sdk_ready"] = True
        payload["runtime_ready"] = True
        payload["runtime_evidence"]["approved"] = True
        payload["runtime_evidence"]["status"] = "approved"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("runtime_evidence_approval_not_supported_by_candidate_checker", report["blockers"])
        self.assertIn("runtime_evidence_status_not_fail_closed", report["blockers"])

    def test_rejects_pointer_coordinate_leakage(self) -> None:
        payload = manifest()
        payload["principal"]["fields"][0]["ue_pointer"] = "0x1234"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("ue_coordinate_or_pointer_leakage", report["blockers"])

    def test_rejects_positive_commands_permissions_lookup_mutation_and_return_override_claims(self) -> None:
        for claim in ("commands", "permissions", "lookup", "mutation", "return_override"):
            with self.subTest(claim=claim):
                payload = manifest()
                payload["principal"][claim] = True

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn("forbidden_public_capability_claim", report["blockers"])

    def test_rejects_missing_fail_closed_evidence_policy(self) -> None:
        payload = manifest()
        payload["evidence_policy"]["malformed_evidence_result"] = "allow"
        payload["evidence_policy"]["unsupported_evidence_result"] = "allow"
        payload["evidence_policy"]["fail_closed"] = False

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("evidence_policy_malformed_not_denied", report["blockers"])
        self.assertIn("evidence_policy_unsupported_not_denied", report["blockers"])
        self.assertIn("evidence_policy_not_fail_closed", report["blockers"])

    def test_rejects_unexpected_top_level_schema_fields(self) -> None:
        payload = manifest()
        payload["public_contract_claim"] = "permissions"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("top_level_fields_unexpected", report["blockers"])
        self.assertIn("forbidden_public_capability_claim", report["blockers"])

    def test_rejects_manifest_under_protected_server_root_before_reading(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "/servidor/ark/obelisk/player-identity-principal-policy.json",
                "--json",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest must not read from protected server root /servidor/ark", result.stderr)

    def test_rejects_symlinked_manifest_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            link = root / "manifest-link.json"
            link.symlink_to(manifest_path)

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(link), "--json"],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest must not be a symlink", result.stderr)


if __name__ == "__main__":
    unittest.main()
