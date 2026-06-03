#!/usr/bin/env python3
"""Tests for check_permissions_admin_query_failclosed_contract.py."""

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
SCRIPT = SCRIPT_DIR / "check_permissions_admin_query_failclosed_contract.py"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_permissions_admin_query_failclosed_contract", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


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
        "consumer_result": "unknown" if name == "unknown_authority" else "deny",
        "fail_closed": True,
        "allow_allowed": False,
    }


def reason_flag(name: str, bit_index: int) -> dict:
    return {
        "name": name,
        "case": name,
        "bit_index": bit_index,
        "fail_closed": True,
        "allow_allowed": False,
        "consumer_result": "unknown" if name == "unknown_authority" else "deny",
    }


def manifest() -> dict:
    fail_closed_names = [
        "stale_principal",
        "scope_mismatch",
        "process_mismatch",
        "missing_principal",
        "missing_runtime_principal_identity",
        "command_text_principal_claim",
        "command_text_permission_claim",
        "operator_config_principal_claim",
        "operator_config_permission_claim",
        "operator_config_allow_capability_claim",
        "missing_action",
        "malformed_action_size",
        "action_size_exceeds_max",
        "malformed_resource_scope_size",
        "resource_scope_size_exceeds_max",
        "missing_principal_handle",
        "missing_principal_generation",
        "missing_principal_scope_flags",
        "missing_principal_provenance",
        "principal_generation_mismatch",
        "plugin_supplied_principal_tuple",
        "server_process_epoch_mismatch",
        "unsupported_principal_scope_flags",
        "missing_plugin_owner_token",
        "zero_plugin_owner_token",
        "unknown_plugin_owner_token",
        "unloading_plugin_owner_token",
        "missing_capability",
        "rate_limit_exceeded",
        "unknown_authority",
        "missing_authority_kind",
        "missing_policy_source",
        "missing_policy_source_generation",
        "policy_source_generation_mismatch",
        "missing_policy_epoch",
        "missing_authority_generation",
        "authority_generation_mismatch",
        "plugin_supplied_provenance",
        "command_text_policy_provenance_claim",
        "operator_config_policy_provenance_claim",
    ]
    return {
        "schema": "obelisk.permissions-admin-query-failclosed-contract.v1",
        "artifact_identity": {
            "artifact_kind": "obelisk.permissions-admin-query-failclosed-contract.v1",
            "artifact_status": "candidate_only_pre_abi_contract",
            "dependency_surface": "obelisk.player_identity.v1",
        },
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
            "decision_fields": ["decision", "reason_flags"],
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
        "fail_closed_reason_flags": {
            "classification": "internal_candidate_only",
            "encoding": "uint64_flags",
            "source": "obelisk_internal_query_evaluator",
            "public_header_allowed": False,
            "public_cache_abi_allowed": False,
            "plugin_supplied_flags_allowed": False,
            "operator_config_flags_allowed": False,
            "command_text_flags_allowed": False,
            "allow_requires_zero_reason_flags": True,
            "deny_unknown_require_nonzero_reason_flags": True,
            "unknown_authority_result": "unknown",
            "runtime_ready": False,
            "flags": [reason_flag(name, bit_index) for bit_index, name in enumerate(fail_closed_names)],
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
        "principal_runtime_identity_policy": {
            "config_enables_surface_only": True,
            "runtime_observation_establishes_identity": True,
            "runtime_principal_required_for_permission_authority": True,
            "command_text_principal_claim_allowed": False,
            "operator_config_principal_claim_allowed": False,
            "command_text_permission_claim_allowed": False,
            "operator_config_permission_claim_allowed": False,
        },
        "principal_provenance_policy": {
            "principal_tuple_source": "runtime_owned_player_identity_observation",
            "plugin_supplied_principal_tuple_allowed": False,
            "command_supplied_principal_tuple_allowed": False,
            "operator_config_supplied_principal_tuple_allowed": False,
            "principal_tuple_provenance_required_before_allow": True,
            "principal_generation_provenance_required_before_allow": True,
            "principal_scope_provenance_required_before_allow": True,
            "server_process_epoch_required_before_allow": True,
            "missing_principal_provenance_result": "deny",
            "stale_principal_result": "deny",
            "principal_generation_mismatch_result": "deny",
            "scope_mismatch_result": "deny",
            "process_mismatch_result": "deny",
            "server_process_epoch_mismatch_result": "deny",
            "unsupported_principal_scope_flags_result": "deny",
            "plugin_supplied_principal_tuple_result": "deny",
            "public_abi_field_allowed": False,
            "runtime_ready": False,
        },
        "owner_token_policy": {
            "owner_token_source": "runtime_assigned_plugin_owner_token",
            "nonzero_owner_token_required_before_policy_evaluation": True,
            "live_owner_required_before_policy_evaluation": True,
            "owner_token_validation_precedes_policy_evaluation": True,
            "owner_token_validation_before_rate_budget": True,
            "owner_token_validation_before_candidate_cache_read": True,
            "unknown_owner_token_result": "deny",
            "unloading_owner_token_result": "deny",
            "zero_owner_token_result": "deny",
            "missing_owner_token_result": "deny",
            "owner_cleanup_invalidates_query_budget": True,
            "owner_cleanup_invalidates_candidate_cache": True,
            "plugin_supplied_owner_identity_allowed": False,
            "public_abi_field_allowed": False,
            "runtime_ready": False,
        },
        "policy_provenance_policy": {
            "policy_provenance_source": "runtime_owned_policy_evaluator",
            "policy_source_id_required_before_allow": True,
            "policy_source_generation_required_before_allow": True,
            "authority_kind_required_before_allow": True,
            "authority_generation_required_before_allow": True,
            "policy_epoch_required_before_allow": True,
            "plugin_supplied_policy_provenance_allowed": False,
            "command_text_policy_provenance_claim_allowed": False,
            "operator_config_policy_provenance_claim_allowed": False,
            "operator_config_allow_provenance_allowed": False,
            "missing_policy_source_result": "deny",
            "missing_policy_source_generation_result": "deny",
            "policy_source_generation_mismatch_result": "deny",
            "missing_authority_kind_result": "deny",
            "missing_authority_generation_result": "deny",
            "authority_generation_mismatch_result": "deny",
            "missing_policy_epoch_result": "deny",
            "unknown_authority_result": "unknown",
            "plugin_supplied_policy_provenance_result": "deny",
            "public_abi_field_allowed": False,
            "runtime_ready": False,
        },
        "dependency_context": {
            "upstream_surface": "obelisk.player_identity.v1",
            "upstream_surface_status": "planning_only",
            "required_lifecycle_anchor_schema": "obelisk.players-identity-lifecycle-anchor-candidates.v1",
            "required_principal_invalidation_schema": "obelisk.players-identity-principal-invalidation-policy.v1",
            "required_runtime_evidence_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
            "public_identity_required_before_promotion": True,
            "public_identity_promoted": False,
            "permissions_admin_public_abi_promoted": False,
            "command_response_dependency_promoted": False,
        },
        "query_text_policy": {
            "action_required": True,
            "action_max_bytes": 128,
            "resource_scope_required": False,
            "resource_scope_max_bytes": 256,
            "bytes_are_copied": True,
            "utf8_decoding_required_before_allow": False,
            "command_parser_claim_allowed": False,
        },
        "abuse_policy": {
            "rate_limited_per_plugin_owner_token": True,
            "budget_cleanup_on_plugin_owner_cleanup": True,
            "burst_exhaustion_result": "deny_or_unknown",
            "malformed_query_observable": True,
            "audit_records_redacted": True,
            "audit_exposes_ue_pointers_raw_params_or_secret_policy": False,
            "state_public_cache_abi": False,
            "process_local_owner_scoped": True,
        },
        "sequence_gate": {
            "player_identity_required_before_permission_query": True,
            "query_result_provenance_required_before_command_response": True,
            "command_response_dependency_promoted": False,
            "command_response_contract_required_before_commands_replies": True,
            "commands_replies_admin_mutation_storage_operator_ingress_allowed": False,
            "query_result_contains_command_or_reply_handle": False,
        },
        "fail_closed_cases": [fail_closed_case(name) for name in fail_closed_names],
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
            "command text and operator config cannot establish principal identity or permission claims before runtime principal observation",
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
                "plugin_owner_token",
                "principal_handle",
                "principal_generation",
                "principal_scope_flags",
                "action",
                "action_size",
                "resource_scope",
                "resource_scope_size",
                "request_flags",
            ],
        )
        self.assertEqual(report["decisions"], ["deny", "allow", "unknown"])
        self.assertEqual(report["decision_fields"], ["decision", "reason_flags"])
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
            list(CHECKER.REQUIRED_FAIL_CLOSED_CASE_SEQUENCE),
        )
        self.assertEqual(report["reason_flags"], report["fail_closed_cases"])

    def test_emits_canonical_candidate_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "permissions-admin-query-template.json"
            subprocess.run(
                [sys.executable, str(SCRIPT), "--emit-template", str(path)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = self.run_checker(payload)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertTrue(report["candidate_only"])
        self.assertTrue(report["pre_abi"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["mode"], "consume")

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

    def test_rejects_missing_or_weakened_artifact_identity_dependency_context(self) -> None:
        payload = manifest()
        payload.pop("artifact_identity")
        payload["dependency_context"]["public_identity_promoted"] = True
        payload["dependency_context"]["required_runtime_evidence_schema"] = (
            "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1"
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("artifact_identity_missing", report["blockers"])
        self.assertIn("dependency_context_public_identity_promoted_invalid", report["blockers"])
        self.assertIn("dependency_context_required_runtime_evidence_schema_invalid", report["blockers"])

    def test_rejects_missing_required_query_fields(self) -> None:
        for field_name in ("plugin_owner_token", "principal_generation", "action", "action_size", "request_flags"):
            with self.subTest(field_name=field_name):
                payload = manifest()
                payload["query_contract"]["fields"] = [
                    field for field in payload["query_contract"]["fields"] if field["name"] != field_name
                ]

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn("query_fields_missing_required", report["blockers"])

    def test_rejects_reordered_or_duplicate_query_fields(self) -> None:
        payload = manifest()
        fields = payload["query_contract"]["fields"]
        fields.append(copy.deepcopy(fields[1]))
        fields.append(fields.pop(0))

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_fields_duplicate", report["blockers"])
        self.assertIn("query_fields_sequence_mismatch", report["blockers"])

    def test_rejects_malformed_action_and_action_size_field_types(self) -> None:
        payload = manifest()
        for field in payload["query_contract"]["fields"]:
            if field["name"] == "action":
                field["type"] = "string"
            if field["name"] == "action_size":
                field["type"] = "uint32"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_field_type_mismatch", report["blockers"])

    def test_rejects_reordered_or_duplicate_decision_fields_and_results(self) -> None:
        payload = manifest()
        payload["decision_contract"]["decision_fields"] = ["reason_flags", "decision", "decision"]
        payload["decision_contract"]["results"].append(copy.deepcopy(payload["decision_contract"]["results"][0]))
        payload["decision_contract"]["results"].append(payload["decision_contract"]["results"].pop(0))

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("decision_fields_duplicate", report["blockers"])
        self.assertIn("decision_fields_sequence_mismatch", report["blockers"])
        self.assertIn("decision_results_duplicate", report["blockers"])
        self.assertIn("decision_results_sequence_mismatch", report["blockers"])

    def test_rejects_missing_decision_field_and_provenance_fields(self) -> None:
        payload = manifest()
        payload["decision_contract"]["decision_fields"].remove("reason_flags")
        payload["decision_contract"]["results"] = [
            result for result in payload["decision_contract"]["results"] if result["decision"] != "unknown"
        ]
        payload["decision_contract"]["provenance_fields"].remove("policy_epoch")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("decision_fields_missing_required", report["blockers"])
        self.assertIn("decision_results_missing_required", report["blockers"])
        self.assertIn("provenance_fields_missing_required", report["blockers"])

    def test_rejects_missing_or_public_reason_flags_contract(self) -> None:
        payload = manifest()
        payload.pop("fail_closed_reason_flags")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("reason_flags_contract_missing", report["blockers"])

        payload = manifest()
        payload["fail_closed_reason_flags"]["public_header_allowed"] = True
        payload["fail_closed_reason_flags"]["public_cache_abi_allowed"] = True
        payload["fail_closed_reason_flags"]["runtime_ready"] = True
        payload["fail_closed_reason_flags"]["plugin_supplied_flags_allowed"] = True
        payload["fail_closed_reason_flags"]["operator_config_flags_allowed"] = True
        payload["fail_closed_reason_flags"]["command_text_flags_allowed"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("reason_flags_public_header_allowed_invalid", report["blockers"])
        self.assertIn("reason_flags_public_cache_abi_allowed_invalid", report["blockers"])
        self.assertIn("reason_flags_runtime_ready_invalid", report["blockers"])
        self.assertIn("reason_flags_plugin_supplied_flags_allowed_invalid", report["blockers"])
        self.assertIn("reason_flags_operator_config_flags_allowed_invalid", report["blockers"])
        self.assertIn("reason_flags_command_text_flags_allowed_invalid", report["blockers"])

    def test_rejects_incomplete_or_malformed_reason_flags(self) -> None:
        payload = manifest()
        payload["fail_closed_reason_flags"]["flags"] = [
            flag for flag in payload["fail_closed_reason_flags"]["flags"] if flag["name"] != "scope_mismatch"
        ]
        payload["fail_closed_reason_flags"]["flags"][0]["bit_index"] = 2
        payload["fail_closed_reason_flags"]["flags"][1]["consumer_result"] = "allow"
        payload["fail_closed_reason_flags"]["flags"][2]["allow_allowed"] = True
        payload["fail_closed_reason_flags"]["flags"][3]["fail_closed"] = False

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("reason_flags_missing_required", report["blockers"])
        self.assertIn("reason_flag_bit_index_duplicate", report["blockers"])
        self.assertIn("reason_flag_bit_index_sequence_mismatch", report["blockers"])
        self.assertIn("reason_flag_consumer_result_not_denied_or_unknown", report["blockers"])
        self.assertIn("reason_flag_allow_not_forbidden", report["blockers"])
        self.assertIn("reason_flag_not_fail_closed", report["blockers"])

    def test_rejects_duplicate_or_reordered_fail_closed_cases(self) -> None:
        payload = manifest()
        payload["fail_closed_cases"].append(copy.deepcopy(payload["fail_closed_cases"][0]))
        payload["fail_closed_cases"].append(payload["fail_closed_cases"].pop(0))

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("fail_closed_cases_duplicate", report["blockers"])
        self.assertIn("fail_closed_cases_sequence_mismatch", report["blockers"])

    def test_rejects_reason_flag_name_order_and_bit_name_drift(self) -> None:
        payload = manifest()
        flags = payload["fail_closed_reason_flags"]["flags"]
        flags[0], flags[1] = flags[1], flags[0]
        flags[2]["bit_index"], flags[3]["bit_index"] = flags[3]["bit_index"], flags[2]["bit_index"]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("reason_flags_sequence_mismatch", report["blockers"])
        self.assertIn("reason_flag_bit_index_name_mismatch", report["blockers"])

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
            "process_mismatch",
            "missing_principal",
            "missing_runtime_principal_identity",
            "command_text_principal_claim",
            "command_text_permission_claim",
            "operator_config_principal_claim",
            "operator_config_permission_claim",
            "operator_config_allow_capability_claim",
            "missing_action",
            "malformed_action_size",
            "action_size_exceeds_max",
            "malformed_resource_scope_size",
            "resource_scope_size_exceeds_max",
            "missing_principal_handle",
            "missing_principal_scope_flags",
            "missing_principal_provenance",
            "unsupported_principal_scope_flags",
            "plugin_supplied_principal_tuple",
            "server_process_epoch_mismatch",
            "zero_plugin_owner_token",
            "unknown_plugin_owner_token",
            "unloading_plugin_owner_token",
            "missing_policy_source",
            "missing_policy_source_generation",
            "policy_source_generation_mismatch",
            "missing_policy_epoch",
            "missing_authority_kind",
            "missing_authority_generation",
            "authority_generation_mismatch",
            "command_text_policy_provenance_claim",
            "plugin_supplied_provenance",
            "operator_config_policy_provenance_claim",
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

    def test_rejects_fail_closed_case_and_reason_flag_result_drift(self) -> None:
        payload = manifest()
        for case in payload["fail_closed_cases"]:
            if case["case"] == "unknown_authority":
                case["consumer_result"] = "deny"
        for flag in payload["fail_closed_reason_flags"]["flags"]:
            if flag["name"] == "unknown_authority":
                flag["consumer_result"] = "deny"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("fail_closed_case_consumer_result_mismatch", report["blockers"])
        self.assertIn("reason_flag_consumer_result_mismatch", report["blockers"])

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

    def test_rejects_missing_or_weakened_principal_runtime_identity_policy(self) -> None:
        payload = manifest()
        payload.pop("principal_runtime_identity_policy")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("principal_runtime_identity_policy_missing", report["blockers"])

        payload = manifest()
        payload["principal_runtime_identity_policy"]["runtime_observation_establishes_identity"] = False
        payload["principal_runtime_identity_policy"]["command_text_principal_claim_allowed"] = True
        payload["principal_runtime_identity_policy"]["operator_config_permission_claim_allowed"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "principal_runtime_identity_policy_runtime_observation_establishes_identity_invalid",
            report["blockers"],
        )
        self.assertIn(
            "principal_runtime_identity_policy_command_text_principal_claim_allowed_invalid",
            report["blockers"],
        )
        self.assertIn(
            "principal_runtime_identity_policy_operator_config_permission_claim_allowed_invalid",
            report["blockers"],
        )

    def test_rejects_missing_or_weakened_principal_provenance_policy(self) -> None:
        payload = manifest()
        payload.pop("principal_provenance_policy")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("principal_provenance_policy_missing", report["blockers"])

        payload = manifest()
        payload["principal_provenance_policy"]["plugin_supplied_principal_tuple_allowed"] = True
        payload["principal_provenance_policy"]["principal_generation_provenance_required_before_allow"] = False
        payload["principal_provenance_policy"]["server_process_epoch_mismatch_result"] = "allow"
        payload["principal_provenance_policy"]["public_abi_field_allowed"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "principal_provenance_policy_plugin_supplied_principal_tuple_allowed_invalid",
            report["blockers"],
        )
        self.assertIn(
            "principal_provenance_policy_principal_generation_provenance_required_before_allow_invalid",
            report["blockers"],
        )
        self.assertIn("principal_provenance_policy_server_process_epoch_mismatch_result_invalid", report["blockers"])
        self.assertIn("principal_provenance_policy_public_abi_field_allowed_invalid", report["blockers"])

    def test_rejects_principal_provenance_fail_closed_result_drift(self) -> None:
        payload = manifest()
        payload["principal_provenance_policy"].pop("missing_principal_provenance_result")
        payload["principal_provenance_policy"]["principal_tuple_provenance_required_before_allow"] = False
        payload["principal_provenance_policy"]["stale_principal_result"] = "allow"
        payload["principal_provenance_policy"]["scope_mismatch_result"] = "unknown"
        payload["principal_provenance_policy"]["process_mismatch_result"] = "allow"
        payload["principal_provenance_policy"]["plugin_supplied_principal_tuple_result"] = "allow"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("principal_provenance_policy_fields_mismatch", report["blockers"])
        self.assertIn(
            "principal_provenance_policy_principal_tuple_provenance_required_before_allow_invalid",
            report["blockers"],
        )
        self.assertIn("principal_provenance_policy_missing_principal_provenance_result_invalid", report["blockers"])
        self.assertIn("principal_provenance_policy_stale_principal_result_invalid", report["blockers"])
        self.assertIn("principal_provenance_policy_scope_mismatch_result_invalid", report["blockers"])
        self.assertIn("principal_provenance_policy_process_mismatch_result_invalid", report["blockers"])
        self.assertIn("principal_provenance_policy_plugin_supplied_principal_tuple_result_invalid", report["blockers"])

    def test_rejects_missing_or_weakened_owner_token_policy(self) -> None:
        payload = manifest()
        payload.pop("owner_token_policy")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("owner_token_policy_missing", report["blockers"])

        payload = manifest()
        payload["owner_token_policy"]["owner_token_validation_precedes_policy_evaluation"] = False
        payload["owner_token_policy"]["owner_token_validation_before_rate_budget"] = False
        payload["owner_token_policy"]["unknown_owner_token_result"] = "allow"
        payload["owner_token_policy"]["plugin_supplied_owner_identity_allowed"] = True
        payload["owner_token_policy"]["public_abi_field_allowed"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("owner_token_policy_owner_token_validation_precedes_policy_evaluation_invalid", report["blockers"])
        self.assertIn("owner_token_policy_owner_token_validation_before_rate_budget_invalid", report["blockers"])
        self.assertIn("owner_token_policy_unknown_owner_token_result_invalid", report["blockers"])
        self.assertIn("owner_token_policy_plugin_supplied_owner_identity_allowed_invalid", report["blockers"])
        self.assertIn("owner_token_policy_public_abi_field_allowed_invalid", report["blockers"])

    def test_rejects_missing_or_weakened_policy_provenance_policy(self) -> None:
        payload = manifest()
        payload.pop("policy_provenance_policy")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("policy_provenance_policy_missing", report["blockers"])

        payload = manifest()
        payload["policy_provenance_policy"]["policy_epoch_required_before_allow"] = False
        payload["policy_provenance_policy"]["plugin_supplied_policy_provenance_allowed"] = True
        payload["policy_provenance_policy"]["command_text_policy_provenance_claim_allowed"] = True
        payload["policy_provenance_policy"]["operator_config_allow_provenance_allowed"] = True
        payload["policy_provenance_policy"]["missing_policy_epoch_result"] = "allow"
        payload["policy_provenance_policy"]["unknown_authority_result"] = "allow"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("policy_provenance_policy_policy_epoch_required_before_allow_invalid", report["blockers"])
        self.assertIn("policy_provenance_policy_plugin_supplied_policy_provenance_allowed_invalid", report["blockers"])
        self.assertIn(
            "policy_provenance_policy_command_text_policy_provenance_claim_allowed_invalid",
            report["blockers"],
        )
        self.assertIn("policy_provenance_policy_operator_config_allow_provenance_allowed_invalid", report["blockers"])
        self.assertIn("policy_provenance_policy_missing_policy_epoch_result_invalid", report["blockers"])
        self.assertIn("policy_provenance_policy_unknown_authority_result_invalid", report["blockers"])

    def test_rejects_missing_or_weakened_query_text_policy(self) -> None:
        payload = manifest()
        payload.pop("query_text_policy")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_text_policy_missing", report["blockers"])

        payload = manifest()
        payload["query_text_policy"]["action_max_bytes"] = 4096
        payload["query_text_policy"]["resource_scope_required"] = True
        payload["query_text_policy"]["command_parser_claim_allowed"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_text_policy_action_max_bytes_invalid", report["blockers"])
        self.assertIn("query_text_policy_resource_scope_required_invalid", report["blockers"])
        self.assertIn("query_text_policy_command_parser_claim_allowed_invalid", report["blockers"])

    def test_rejects_missing_or_weakened_abuse_policy(self) -> None:
        payload = manifest()
        payload.pop("abuse_policy")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("abuse_policy_missing", report["blockers"])

        payload = manifest()
        payload["abuse_policy"]["state_public_cache_abi"] = True
        payload["abuse_policy"]["audit_exposes_ue_pointers_raw_params_or_secret_policy"] = True
        payload["abuse_policy"]["burst_exhaustion_result"] = "allow"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("abuse_policy_state_public_cache_abi_invalid", report["blockers"])
        self.assertIn("abuse_policy_audit_exposes_ue_pointers_raw_params_or_secret_policy_invalid", report["blockers"])
        self.assertIn("abuse_policy_burst_exhaustion_result_invalid", report["blockers"])

    def test_rejects_missing_or_weakened_sequence_gate(self) -> None:
        payload = manifest()
        payload.pop("sequence_gate")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("sequence_gate_missing", report["blockers"])

        payload = manifest()
        payload["sequence_gate"]["command_response_dependency_promoted"] = True
        payload["sequence_gate"]["query_result_contains_command_or_reply_handle"] = True
        payload["sequence_gate"]["commands_replies_admin_mutation_storage_operator_ingress_allowed"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("sequence_gate_command_response_dependency_promoted_invalid", report["blockers"])
        self.assertIn("sequence_gate_query_result_contains_command_or_reply_handle_invalid", report["blockers"])
        self.assertIn(
            "sequence_gate_commands_replies_admin_mutation_storage_operator_ingress_allowed_invalid",
            report["blockers"],
        )

    def test_rejects_principal_or_permission_claim_sources_before_runtime_identity(self) -> None:
        for key, value in (
            ("principal_source", "command_text"),
            ("principalSource", "command text"),
            ("principal-source", {"source": "operator-config"}),
            ("identity_claim_source", "operator-config"),
            ("permission_claim_source", ["operator config"]),
            ("authority_claim_source", {"source": "command text"}),
            ("authorityClaimSource", {"source": "operator config"}),
        ):
            with self.subTest(key=key):
                payload = manifest()
                payload["future_claim"] = {key: value}

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertEqual(result.returncode, 1)
                self.assertIn("pre_runtime_principal_or_permission_claim_source", report["blockers"])

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

    def test_rejects_nested_stable_and_v1_completion_overclaims(self) -> None:
        payload = manifest()
        payload["nested_claim"] = {
            "stable_claim_allowed": True,
            "v1_completion_ready": True,
        }
        payload["claim_text"] = "stable claim allowed; v1 completion ready"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("stable_claim_allowed_overclaim", report["blockers"])
        self.assertIn("v1_completion_ready_overclaim", report["blockers"])
        self.assertIn("stable_claim_allowed_string_overclaim", report["blockers"])
        self.assertIn("v1_completion_ready_string_overclaim", report["blockers"])

    def test_rejects_camel_hyphen_space_readiness_aliases_and_positive_texts(self) -> None:
        payload = manifest()
        payload["nested_claim"] = {
            "publicReplyAbiReady": True,
            "public-response-path-ready": True,
            "send chat ready": True,
            "publicAbiReady": True,
            "runtimeReady": True,
            "permissions-admin-ready": True,
            "commandRouterAllowed": True,
            "publicBridgeAbiAllowed": True,
            "public response abi allowed": True,
        }
        payload["claim_texts"] = [
            "public ABI is ready",
            "permissions/admin is public and ready",
            "reply endpoint is live",
            "command response path is live",
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        for blocker in (
            "public_reply_abi_ready_overclaim",
            "public_response_path_ready_overclaim",
            "send_chat_ready_overclaim",
            "public_abi_ready_overclaim",
            "runtime_ready_overclaim",
            "permissions_admin_ready_overclaim",
            "command_router_allowed_overclaim",
            "public_bridge_abi_allowed_overclaim",
            "public_response_abi_allowed_overclaim",
            "public_abi_ready_string_overclaim",
            "permissions_admin_ready_string_overclaim",
            "public_reply_abi_ready_string_overclaim",
            "public_response_path_ready_string_overclaim",
        ):
            self.assertIn(blocker, report["blockers"])

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
