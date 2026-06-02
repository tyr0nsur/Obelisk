#!/usr/bin/env python3
"""Tests for check_player_identity_identifier_redaction_evidence.py."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_identifier_redaction_evidence.py"


def evidence() -> dict:
    return {
        "schema": "obelisk.player-identity-identifier-redaction-evidence.v1",
        "surface": "obelisk.player_identity.v1",
        "sanitized": True,
        "source": "offline-sanitized-snapshot",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "fields": [
            {
                "name": "principal_candidate",
                "source_identifier_class": "platform account ids",
                "field_class": "private-redacted",
                "redacted": True,
                "raw_value_present": False,
            },
            {
                "name": "display_label",
                "source_identifier_class": "player names",
                "field_class": "private-redacted",
                "redacted": True,
                "raw_value_present": False,
            },
            {
                "name": "tribe_affiliation",
                "source_identifier_class": "tribe identifiers",
                "field_class": "private-redacted",
                "redacted": True,
                "raw_value_present": False,
            },
            {
                "name": "remote_endpoint",
                "source_identifier_class": "network addresses",
                "field_class": "forbidden",
                "redacted": True,
                "raw_value_present": False,
            },
            {
                "name": "chat_identity_hint",
                "source_identifier_class": "raw chat text used as identity",
                "field_class": "forbidden",
                "redacted": True,
                "raw_value_present": False,
            },
            {
                "name": "controller_ref",
                "source_identifier_class": "controller/playerstate object references",
                "field_class": "forbidden",
                "redacted": True,
                "raw_value_present": False,
            },
        ],
        "policy": {
            "default": "no raw identity logging or persistence",
            "persistence_allowed": False,
            "raw_identity_logging_allowed": False,
        },
        "sample_logs": [
            {
                "event": "session_start",
                "principal_present": True,
                "redaction_reason_flags": ["platform_account_id_redacted"],
            }
        ],
    }


class PlayerIdentityIdentifierRedactionEvidenceTests(unittest.TestCase):
    def run_checker(self, payload: dict, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "redaction-evidence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--evidence", str(path), "--json"],
                check=False,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_accepts_sanitized_redaction_evidence_for_contract_review_only(self) -> None:
        result = self.run_checker(evidence())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertEqual(report["resolved_inputs"], ["privacy.identifier_redaction"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(report["remaining_blockers"], [])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate")

    def test_rejects_unsanitized_evidence(self) -> None:
        payload = evidence()
        payload["sanitized"] = False

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sanitized_not_true", report["blockers"])
        self.assertFalse(report["ready"])

    def test_rejects_raw_identifier_values_anywhere_in_fields(self) -> None:
        payload = evidence()
        payload["fields"][0]["raw_value"] = "76561198000000000"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("field_contains_raw_identifier_material", report["blockers"])

    def test_rejects_raw_identifier_values_in_sample_logs(self) -> None:
        payload = evidence()
        payload["sample_logs"][0]["message"] = "connected from 10.1.2.3"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sample_logs_contain_raw_identifier_material", report["blockers"])
        self.assertIn("sample_log_keys_unexpected", report["blockers"])

    def test_rejects_free_form_sample_log_text_without_raw_identifier_pattern(self) -> None:
        payload = evidence()
        payload["sample_logs"][0]["message"] = "joined with sanitized identity"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sample_log_keys_unexpected", report["blockers"])

    def test_rejects_unknown_sample_log_redaction_reason_flag(self) -> None:
        payload = evidence()
        payload["sample_logs"][0]["redaction_reason_flags"] = ["display_label_observed"]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sample_log_redaction_reason_flags_unknown", report["blockers"])

    def test_rejects_unknown_sample_log_event(self) -> None:
        payload = evidence()
        payload["sample_logs"][0]["event"] = "player_lookup"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sample_log_event_not_allowed", report["blockers"])

    def test_rejects_missing_required_identifier_class_coverage(self) -> None:
        payload = evidence()
        payload["fields"] = payload["fields"][:-1]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "required_identifier_classes_missing"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_identifier_classes_missing", report["blockers"])
        self.assertEqual(detail["missing"], ["controller/playerstate object references"])

    def test_rejects_redacted_class_with_raw_value_present(self) -> None:
        payload = evidence()
        payload["fields"][0]["raw_value_present"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("redacted_field_raw_value_present_not_false", report["blockers"])

    def test_rejects_readiness_flags_claiming_promotion(self) -> None:
        payload = evidence()
        payload["public_sdk_ready"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_sdk_ready_not_false", report["blockers"])

    def test_rejects_live_server_source(self) -> None:
        payload = evidence()
        payload["source"] = "live-server"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("live_server_source_forbidden", report["blockers"])

    def test_rejects_protected_live_server_input_path(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--evidence", "/servidor/ark/redaction-evidence.json", "--json"],
            check=False,
            env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--evidence must not read from protected server root", result.stderr)

    def test_detects_raw_key_even_without_sensitive_string_pattern(self) -> None:
        payload = evidence()
        payload["fields"][0]["steam_id"] = "redacted"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "field_contains_raw_identifier_material"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("raw_key:steam_id", detail["matches"])


if __name__ == "__main__":
    unittest.main()
