#!/usr/bin/env python3
"""Tests for check_command_copied_response_intent_planning.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_copied_response_intent_planning.py"
QUERY_CHECKER = SCRIPT_DIR / "check_permissions_admin_query_failclosed_contract.py"
DECISIONS = REPO_ROOT / "docs" / "command_copied_response_intent_planning_decisions.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
CANONICAL_QUERY_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"


def write_json(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def emit_query_manifest(root: Path) -> Path:
    path = root / "permissions-query.json"
    subprocess.run(
        [sys.executable, str(QUERY_CHECKER), "--emit-template", str(path)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return path


def run_checker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


class CommandCopiedResponseIntentPlanningTests(unittest.TestCase):
    def test_accepts_planning_only_intent_with_query_failclosed_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            query_manifest = emit_query_manifest(Path(tmp))

            result = run_checker("--query-failclosed-artifact", str(query_manifest))
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(
            report["query_failclosed_artifact_schema"],
            "obelisk.permissions-admin-query-failclosed-contract.v1",
        )
        self.assertTrue(report["permission_query_crosswalk_checked"])
        self.assertIn("plugin_owner_token", report["intent_fields"])
        self.assertIn("policy_source_id", report["intent_fields"])
        self.assertIn("redaction_flags", report["intent_fields"])

    def test_accepts_canonical_query_failclosed_manifest_for_crosswalk(self) -> None:
        result = run_checker("--query-failclosed-artifact", str(CANONICAL_QUERY_CONTRACT))
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["permission_query_crosswalk_checked"])
        self.assertEqual(
            report["query_failclosed_artifact_schema"],
            "obelisk.permissions-admin-query-failclosed-contract.v1",
        )
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_missing_query_failclosed_artifact(self) -> None:
        result = run_checker(check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("query_failclosed_artifact_missing", report["blockers"])
        self.assertIn("response_intent_accepts_without_query_failclosed_planning", report["blockers"])
        self.assertFalse(report["permission_query_crosswalk_checked"])

    def test_accepts_query_failclosed_consume_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            query_report_path = root / "permissions-query.check.json"
            query_report = subprocess.run(
                [sys.executable, str(QUERY_CHECKER), str(query_manifest), "--json"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            query_report_path.write_text(query_report.stdout, encoding="utf-8")

            result = run_checker("--query-failclosed-artifact", str(query_report_path))
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual(
            report["query_failclosed_artifact_schema"],
            "obelisk.permissions-admin-query-failclosed-contract-check.v1",
        )
        self.assertTrue(report["permission_query_crosswalk_checked"])

    def test_rejects_public_or_runtime_overclaims_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["public_header_allowed"] = True
            payload["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_COMMAND_COPIED_RESPONSE_INTENT"]
            payload["runtime_delivery_allowed"] = True
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker(
                "--decisions",
                str(decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])
        self.assertIn("runtime_delivery_allowed_not_false", report["blockers"])

    def test_rejects_route_sdk_reply_and_credit_alias_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["alias_claims"] = {
                "routeReady": True,
                "canonical-route-gate-ready": True,
                "publicHeaderReady": True,
                "replyAbiReady": True,
                "replyReady": True,
                "sendChatReady": True,
                "commandRouterReady": True,
                "stableClaimAllowed": True,
                "v1SdkComplete": True,
                "sdkCompletionCredit": "claimed",
                "accounting_credit": "earned",
            }
            payload["positive_claims"] = [
                "canonical route gate is ready",
                "public header is ready",
                "reply API is ready",
                "send-chat API is live",
                "v1 SDK is complete",
                "SDK completion credit is earned",
                "stable SDK is validated",
            ]
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker(
                "--decisions",
                str(decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_or_runtime_alias_overclaim", report["blockers"])
        self.assertIn("accounting_credit_alias_overclaim", report["blockers"])
        self.assertIn("positive_public_response_claim", report["blockers"])

    def test_rejects_nested_public_runtime_and_v1_readiness_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["dependency_rollup"] = {
                "nested": {
                    "publicSdkReady": True,
                    "publicAbiReady": True,
                    "runtimeReady": True,
                    "runtimeReadinessAllowed": True,
                    "runtimeReadinessReady": True,
                    "countsTowardPublicSdk": True,
                    "countsTowardRuntime": True,
                    "countsTowardV1Completion": True,
                    "publicOrRuntimeAccountingAllowed": True,
                    "v1CompletionReady": True,
                    "v1_0_stable_ready": True,
                }
            }
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker(
                "--decisions",
                str(decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_or_runtime_alias_overclaim", report["blockers"])
        labels = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_or_runtime_alias_overclaim"
        }
        self.assertIn("$.decisions.dependency_rollup.nested.publicSdkReady", labels)
        self.assertIn("$.decisions.dependency_rollup.nested.runtimeReady", labels)
        self.assertIn("$.decisions.dependency_rollup.nested.v1CompletionReady", labels)

    def test_rejects_nested_dependency_source_positive_claims_without_alias_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            command_response = json.loads(
                (REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json").read_text(
                    encoding="utf-8"
                )
            )
            command_response["source_summary"] = {
                "nested": [
                    {
                        "summary": "public SDK is ready for reply API delivery",
                    }
                ]
            }
            command_response_decisions = write_json(root, "command-response.json", command_response)

            result = run_checker(
                "--command-response-decisions",
                str(command_response_decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("dependency_positive_public_response_claim", report["blockers"])
        blocker = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "dependency_positive_public_response_claim"
        )
        self.assertEqual(blocker["source"], "command_response")
        self.assertEqual(blocker["label"], "$.command_response.source_summary.nested[0].summary")

    def test_rejects_missing_intent_provenance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["intent_field_vocabulary"] = [
                field
                for field in payload["intent_field_vocabulary"]
                if field not in {"permission_policy_epoch", "policy_source_id"}
            ]
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker(
                "--decisions",
                str(decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("intent_field_vocabulary_mismatch", report["blockers"])

    def test_rejects_permission_query_crosswalk_field_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            for mapping in payload["permission_query_dependency_crosswalk"]["source_to_intent_fields"]:
                if mapping["source"] == "principal_generation":
                    mapping["intent"] = "principal_handle"
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker(
                "--decisions",
                str(decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permission_query_dependency_crosswalk_mapping_mismatch", report["blockers"])

    def test_rejects_permission_query_crosswalk_policy_epoch_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["permission_query_dependency_crosswalk"]["source_to_intent_fields"] = [
                mapping
                for mapping in payload["permission_query_dependency_crosswalk"]["source_to_intent_fields"]
                if mapping["source"] != "policy_epoch"
            ]
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker(
                "--decisions",
                str(decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permission_query_dependency_crosswalk_mapping_mismatch", report["blockers"])

    def test_rejects_permission_query_crosswalk_deny_unknown_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            for policy in payload["permission_query_dependency_crosswalk"]["decision_to_intent_policy"]:
                if policy["query_decision"] == "deny":
                    policy["response_intent_allowed_after_future_promotion"] = True
                if policy["query_decision"] == "unknown":
                    policy["fail_closed"] = False
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker(
                "--decisions",
                str(decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permission_query_dependency_crosswalk_decision_policy_field_mismatch", report["blockers"])

    def test_rejects_permission_query_crosswalk_principal_provenance_policy_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["permission_query_dependency_crosswalk"]["principal_provenance_policy"][
                "plugin_supplied_principal_tuple_allowed"
            ] = True
            payload["permission_query_dependency_crosswalk"]["principal_provenance_policy"][
                "server_process_epoch_mismatch_result"
            ] = "allow"
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker(
                "--decisions",
                str(decisions),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permission_query_dependency_crosswalk_principal_provenance_policy_mismatch", report["blockers"])

    def test_rejects_query_artifact_missing_crosswalk_source_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(query_manifest.read_text(encoding="utf-8"))
            payload["decision_contract"]["provenance_fields"].remove("policy_source_generation")
            write_json(root, "permissions-query.json", payload)

            result = run_checker("--query-failclosed-artifact", str(query_manifest), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_failclosed_manifest_invalid", report["blockers"])
        self.assertIn("permission_query_crosswalk_source_field_missing_from_artifact", report["blockers"])

    def test_rejects_query_artifact_missing_crosswalk_fail_closed_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            payload = json.loads(query_manifest.read_text(encoding="utf-8"))
            payload["fail_closed_cases"] = [
                case
                for case in payload["fail_closed_cases"]
                if case["case"] != "authority_generation_mismatch"
            ]
            write_json(root, "permissions-query.json", payload)

            result = run_checker("--query-failclosed-artifact", str(query_manifest), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_failclosed_manifest_invalid", report["blockers"])
        self.assertIn("permission_query_crosswalk_fail_closed_cases_missing_from_artifact", report["blockers"])

    def test_rejects_public_header_symbol_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            query_manifest = emit_query_manifest(root)
            header = root / "ObeliskApi.h"
            header.write_text(
                HEADER.read_text(encoding="utf-8")
                + "\n#define OBELISK_API_CAPABILITY_COMMAND_COPIED_RESPONSE_INTENT (1ull << 60)\n"
                + "struct ObeliskCommandCopiedResponseIntent {};\n",
                encoding="utf-8",
            )

            result = run_checker(
                "--public-header",
                str(header),
                "--query-failclosed-artifact",
                str(query_manifest),
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_contains_command_response_intent_symbol", report["blockers"])


if __name__ == "__main__":
    unittest.main()
