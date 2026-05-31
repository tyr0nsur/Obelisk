#!/usr/bin/env python3
"""Tests for check_permissions_admin_query_failclosed_contract.py."""

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
SCRIPT = SCRIPT_DIR / "check_permissions_admin_query_failclosed_contract.py"


def query_field(name: str, field_type: str) -> dict:
    return {
        "name": name,
        "type": field_type,
        "copied": True,
        "source": "obelisk_owned_copy",
        "consumer_visible": True,
    }


def fail_closed_case(name: str) -> dict:
    return {
        "case": name,
        "consumer_result": "deny",
        "fail_closed": True,
        "allow_allowed": False,
    }


def manifest() -> dict:
    return {
        "schema": "obelisk.permissions-admin-query-failclosed-contract.v1",
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "pre_abi": True,
        "public_header_allowed": False,
        "public_cache_abi_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_promotion_allowed": False,
        "query_contract": {
            "kind": "query_only_fail_closed_permission_check",
            "mutation_allowed": False,
            "command_response_allowed": False,
            "public_cache_allowed": False,
            "fields": [
                query_field("plugin_owner_token", "uint64_owner_token"),
                query_field("principal_handle", "uint64_opaque"),
                query_field("principal_generation", "uint64"),
                query_field("principal_scope_flags", "uint64_flags"),
                query_field("action", "copied_bytes"),
                query_field("action_size", "size_t"),
                query_field("resource_scope", "copied_bytes"),
                query_field("resource_scope_size", "size_t"),
                query_field("request_flags", "uint64_flags"),
            ],
        },
        "decision_contract": {
            "results": [
                {"decision": "deny", "fail_closed": True, "requires_provenance": False},
                {"decision": "allow", "fail_closed": False, "requires_provenance": True},
                {"decision": "unknown", "fail_closed": True, "requires_provenance": False},
            ],
            "provenance_fields": [
                "policy_source_id",
                "policy_source_generation",
                "authority_kind",
                "authority_generation",
                "policy_epoch",
            ],
            "allow_without_provenance_allowed": False,
            "unknown_authority_result": "unknown",
        },
        "authority_policy": {
            "recognized_authority_kinds": ["operator-config", "runtime-local"],
            "allow_capable_authority_kinds": ["runtime-local"],
            "allowed_authority_kinds": ["operator-config", "runtime-local"],
            "operator_config_allow_capable": False,
            "plugin_supplied_authority_allowed": False,
            "remote_authority_allowed": False,
            "cross_process_authority_allowed": False,
            "unknown_authority_fails_closed": True,
        },
        "fail_closed_cases": [
            fail_closed_case("stale_principal"),
            fail_closed_case("scope_mismatch"),
            fail_closed_case("missing_principal_generation"),
            fail_closed_case("missing_plugin_owner_token"),
            fail_closed_case("missing_capability"),
            fail_closed_case("rate_limit_exceeded"),
            fail_closed_case("unknown_authority"),
            fail_closed_case("missing_policy_source"),
            fail_closed_case("missing_policy_source_generation"),
            fail_closed_case("policy_source_generation_mismatch"),
            fail_closed_case("missing_policy_epoch"),
            fail_closed_case("missing_authority_generation"),
            fail_closed_case("authority_generation_mismatch"),
            fail_closed_case("plugin_supplied_provenance"),
        ],
        "negative_surface_exclusions": [
            "permission_groups",
            "admin_groups",
            "grants",
            "ban",
            "kick",
            "commands",
            "replies",
            "storage",
            "ue_pointers",
            "ResourceHandle",
            "lookup",
            "mutation",
            "return_override",
        ],
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "candidate_only_pre_abi_contract",
                "public_abi_review_missing",
                "runtime_evidence_missing",
            ],
        },
        "non_claims": [
            "candidate-only pre-ABI permissions/admin query contract",
            "does not add public headers, runtime wiring, public cache ABI, command responses, commands, replies, storage, groups, grants, ban/kick, mutation, lookup, ResourceHandle, UE pointers, or return override",
            "allow decisions require policy provenance and fail closed on missing or unknown authority",
            "promotion, public SDK readiness, and runtime readiness require a separate reviewed ABI and runtime gate",
        ],
    }


class PermissionsAdminQueryFailClosedContractTests(unittest.TestCase):
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

    def test_accepts_candidate_only_pre_abi_query_contract(self) -> None:
        result = self.run_checker(manifest())
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertEqual(report["mode"], "consume")
        self.assertTrue(report["candidate_only"])
        self.assertTrue(report["pre_abi"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_cache_abi_allowed"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(
            report["query_fields"],
            [
                "action",
                "action_size",
                "plugin_owner_token",
                "principal_generation",
                "principal_handle",
                "principal_scope_flags",
                "request_flags",
                "resource_scope",
                "resource_scope_size",
            ],
        )
        self.assertEqual(report["decisions"], ["allow", "deny", "unknown"])
        self.assertEqual(
            report["provenance_fields"],
            [
                "authority_generation",
                "authority_kind",
                "policy_epoch",
                "policy_source_generation",
                "policy_source_id",
            ],
        )
        self.assertEqual(report["recognized_authority_kinds"], ["operator-config", "runtime-local"])
        self.assertEqual(report["allow_capable_authority_kinds"], ["runtime-local"])
        self.assertEqual(
            report["fail_closed_cases"],
            [
                "authority_generation_mismatch",
                "missing_authority_generation",
                "missing_capability",
                "missing_plugin_owner_token",
                "missing_policy_epoch",
                "missing_policy_source",
                "missing_policy_source_generation",
                "missing_principal_generation",
                "plugin_supplied_provenance",
                "policy_source_generation_mismatch",
                "rate_limit_exceeded",
                "scope_mismatch",
                "stale_principal",
                "unknown_authority",
            ],
        )

    def test_promote_public_and_runtime_modes_fail_closed(self) -> None:
        for flag, expected in (
            ("--promote", "promote_blocked_for_candidate_only_pre_abi_contract"),
            ("--public-readiness", "public_readiness_blocked_for_candidate_only_pre_abi_contract"),
            ("--runtime-readiness", "runtime_readiness_blocked_for_candidate_only_pre_abi_contract"),
        ):
            with self.subTest(flag=flag):
                result = self.run_checker(manifest(), flag, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, report["blockers"])
                self.assertIn(
                    "candidate_only_permissions_admin_query_contract_not_readiness_evidence",
                    report["blockers"],
                )
                self.assertFalse(report["promotion_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_public_header_cache_or_runtime_overclaim(self) -> None:
        payload = manifest()
        payload["public_header_allowed"] = True
        payload["public_cache_abi_allowed"] = True
        payload["promotion_ready"] = True
        payload["public_sdk_ready"] = True
        payload["runtime_ready"] = True
        payload["runtime_promotion_allowed"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_cache_abi_allowed_not_false", report["blockers"])
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("runtime_promotion_allowed_not_false", report["blockers"])

    def test_rejects_missing_required_query_fields(self) -> None:
        for field_name in ("plugin_owner_token", "principal_generation", "action_size", "request_flags"):
            with self.subTest(field_name=field_name):
                payload = manifest()
                payload["query_contract"]["fields"] = [
                    field for field in payload["query_contract"]["fields"] if field["name"] != field_name
                ]

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn("query_fields_missing_required", report["blockers"])

    def test_rejects_missing_decision_and_provenance_fields(self) -> None:
        payload = manifest()
        payload["decision_contract"]["results"] = [
            result for result in payload["decision_contract"]["results"] if result["decision"] != "unknown"
        ]
        payload["decision_contract"]["provenance_fields"].remove("policy_epoch")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("decision_results_missing_required", report["blockers"])
        self.assertIn("provenance_fields_missing_required", report["blockers"])

    def test_rejects_allow_without_policy_provenance(self) -> None:
        payload = manifest()
        allow = payload["decision_contract"]["results"][1]
        allow["requires_provenance"] = False
        payload["decision_contract"]["allow_without_provenance_allowed"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("allow_decision_missing_provenance_requirement", report["blockers"])
        self.assertIn("allow_without_provenance_allowed_not_false", report["blockers"])

    def test_rejects_missing_fail_closed_blocker_cases(self) -> None:
        for case_name in (
            "scope_mismatch",
            "missing_policy_source",
            "missing_policy_source_generation",
            "policy_source_generation_mismatch",
            "missing_policy_epoch",
            "missing_authority_generation",
            "authority_generation_mismatch",
            "plugin_supplied_provenance",
        ):
            with self.subTest(case_name=case_name):
                payload = manifest()
                payload["fail_closed_cases"] = [
                    case for case in payload["fail_closed_cases"] if case["case"] != case_name
                ]

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn("fail_closed_cases_missing_required", report["blockers"])

    def test_rejects_non_fail_closed_blocker_case(self) -> None:
        payload = manifest()
        payload["fail_closed_cases"][0]["fail_closed"] = False
        payload["fail_closed_cases"][0]["allow_allowed"] = True
        payload["fail_closed_cases"][0]["consumer_result"] = "allow"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("fail_closed_case_not_fail_closed", report["blockers"])
        self.assertIn("fail_closed_case_allow_not_forbidden", report["blockers"])
        self.assertIn("fail_closed_case_consumer_result_not_denied_or_unknown", report["blockers"])

    def test_rejects_authority_policy_overclaims(self) -> None:
        payload = manifest()
        payload["authority_policy"]["unknown_authority_fails_closed"] = False
        payload["authority_policy"]["plugin_supplied_authority_allowed"] = True
        payload["authority_policy"]["remote_authority_allowed"] = True
        payload["authority_policy"]["cross_process_authority_allowed"] = True
        payload["authority_policy"]["operator_config_allow_capable"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown_authority_not_fail_closed", report["blockers"])
        self.assertIn("authority_plugin_supplied_authority_allowed_not_false", report["blockers"])
        self.assertIn("authority_remote_authority_allowed_not_false", report["blockers"])
        self.assertIn("authority_cross_process_authority_allowed_not_false", report["blockers"])
        self.assertIn("operator_config_allow_capable_not_false", report["blockers"])

    def test_operator_config_can_be_recognized_but_not_allow_capable(self) -> None:
        payload = manifest()
        payload["authority_policy"]["allow_capable_authority_kinds"] = ["runtime-local", "operator-config"]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("authority_allow_capable_kinds_unexpected", report["blockers"])
        self.assertIn("authority_forbidden_allow_capable_kind", report["blockers"])

    def test_rejects_missing_required_authority_kind_sets(self) -> None:
        payload = manifest()
        payload["authority_policy"]["recognized_authority_kinds"].remove("operator-config")
        payload["authority_policy"]["allow_capable_authority_kinds"].remove("runtime-local")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("authority_recognized_kinds_missing_required", report["blockers"])
        self.assertIn("authority_allow_capable_kinds_missing_required", report["blockers"])

    def test_rejects_forbidden_surface_claims_outside_negative_contexts(self) -> None:
        for key, value in (
            ("groups", ["admin"]),
            ("permission_groups", ["admin"]),
            ("admin_groups", ["operator"]),
            ("grant_api", True),
            ("ban_player", True),
            ("kick_player", True),
            ("command_router", "registered"),
            ("reply_api", True),
            ("storage", "sqlite"),
            ("ue_pointers", ["UObject*"]),
            ("ResourceHandle", "public"),
            ("lookup", "resolve principal"),
            ("mutation", "grant permission"),
            ("return_override", True),
        ):
            with self.subTest(key=key):
                payload = manifest()
                payload["future_public_surface"] = {key: value}

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn("forbidden_surface_claim", report["blockers"])

    def test_rejects_nested_readiness_and_promotion_overclaims(self) -> None:
        payload = manifest()
        payload["nested_claim"] = {
            "public_sdk_ready": True,
            "runtime_ready": True,
            "promotion_ready": True,
            "promoted": True,
        }
        payload["claim_text"] = "public SDK ready runtime ready promoted"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_sdk_ready_overclaim", report["blockers"])
        self.assertIn("runtime_ready_overclaim", report["blockers"])
        self.assertIn("promotion_ready_overclaim", report["blockers"])
        self.assertIn("promoted_overclaim", report["blockers"])
        self.assertIn("public_sdk_ready_string_overclaim", report["blockers"])
        self.assertIn("runtime_ready_string_overclaim", report["blockers"])
        self.assertIn("promoted_string_overclaim", report["blockers"])

    def test_rejects_ue_pointer_or_raw_coordinate_leakage(self) -> None:
        for key in ("ue_pointer", "fname_index", "object_address"):
            with self.subTest(key=key):
                payload = manifest()
                payload["query_contract"]["fields"][0] = copy.deepcopy(payload["query_contract"]["fields"][0])
                payload["query_contract"]["fields"][0][key] = "0x1234"

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn("ue_coordinate_or_pointer_leakage", report["blockers"])

    def test_rejects_missing_required_negative_exclusion(self) -> None:
        payload = manifest()
        payload["negative_surface_exclusions"].remove("commands")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("negative_surface_exclusions_missing_required", report["blockers"])

    def test_rejects_manifest_under_protected_server_root_before_reading(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "/servidor/ark/obelisk/permissions-admin-query-contract.json",
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
