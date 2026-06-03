#!/usr/bin/env python3
"""Tests for check_command_copied_response_intent_lifecycle_planning.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_copied_response_intent_lifecycle_planning.py"
DECISIONS = REPO_ROOT / "docs" / "command_copied_response_intent_lifecycle_planning_decisions.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"


def write_json(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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


class CommandCopiedResponseIntentLifecyclePlanningTests(unittest.TestCase):
    def test_accepts_planning_only_lifecycle_manifest(self) -> None:
        result = run_checker()
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
            report["dependency_chain"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ],
        )
        self.assertEqual(
            report["route_order"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(report["lifecycle_vocabulary"], ["create", "cancel", "drain", "expire", "unload cleanup"])

    def test_rejects_public_or_runtime_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["public_header_allowed"] = True
            payload["runtime_ready"] = True
            payload["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_COMMAND_COPIED_RESPONSE_INTENT_LIFECYCLE"]
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker("--decisions", str(decisions), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])

    def test_rejects_route_sdk_reply_and_credit_alias_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["alias_claims"] = {
                "routeReady": True,
                "canonical-route-gate-ready": True,
                "publicHeaderReady": True,
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
                "reply ABI is ready",
                "send-chat API is live",
                "v1 SDK is complete",
                "SDK completion credit is earned",
                "stable SDK is validated",
            ]
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker("--decisions", str(decisions), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_or_runtime_alias_overclaim", report["blockers"])
        self.assertIn("accounting_credit_alias_overclaim", report["blockers"])
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])

    def test_rejects_dependency_chain_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["depends_on"] = [
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
                "obelisk.command_chat_response_path.v1",
            ]
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker("--decisions", str(decisions), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("depends_on_chain_mismatch", report["blockers"])

    def test_rejects_lifecycle_vocabulary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["lifecycle_vocabulary"] = ["create", "cancel", "drain", "expire"]
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker("--decisions", str(decisions), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("lifecycle_vocabulary_mismatch", report["blockers"])

    def test_rejects_lifecycle_property_without_owner_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["lifecycle_properties"] = [
                item.replace("cancel is owner-scoped and idempotent", "cancel is global and idempotent")
                for item in payload["lifecycle_properties"]
            ]
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker("--decisions", str(decisions), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("lifecycle_properties_missing_required", report["blockers"])
        self.assertIn("lifecycle_term_not_owner_scoped", report["blockers"])

    def test_rejects_forbidden_term_outside_non_claims_forbidden_or_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.loads(DECISIONS.read_text(encoding="utf-8"))
            payload["lifecycle_properties"].append("create enables send-chat delivery")
            decisions = write_json(root, "decisions.json", payload)

            result = run_checker("--decisions", str(decisions), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden_positive_claim_term_outside_allowed_sections", report["blockers"])

    def test_allows_forbidden_terms_in_fail_closed_and_non_claims(self) -> None:
        payload = json.loads(DECISIONS.read_text(encoding="utf-8"))

        self.assertTrue(any("send-chat" in item for item in payload["fail_closed_cases"]))
        self.assertTrue(any("reply ABI" in item for item in payload["fail_closed_cases"]))
        self.assertTrue(any("raw FString" in item for item in payload["fail_closed_cases"]))
        self.assertTrue(any("CallProcessEvent" in item for item in payload["fail_closed_cases"]))
        self.assertTrue(any("public header" in item for item in payload["fail_closed_cases"]))
        self.assertTrue(any("runtime readiness" in item for item in payload["fail_closed_cases"]))

        result = run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])

    def test_rejects_public_header_symbol_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = root / "ObeliskApi.h"
            header.write_text(
                HEADER.read_text(encoding="utf-8")
                + "\n#define OBELISK_API_CAPABILITY_COMMAND_COPIED_RESPONSE_INTENT_LIFECYCLE (1ull << 61)\n"
                + "struct ObeliskCommandCopiedResponseIntentLifecycle {};\n",
                encoding="utf-8",
            )

            result = run_checker("--public-header", str(header), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_contains_lifecycle_symbol", report["blockers"])


if __name__ == "__main__":
    unittest.main()
