#!/usr/bin/env python3
"""Tests for check_player_identity_runtime_principal_lifecycle_evidence.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_evidence.py"


def manifest() -> dict:
    approval_gates = [
        "server access or player-facing evidence windows",
        "debug attachment, ptrace, gcore, or runtime scanners",
        "server starts, stops, restarts, or marker changes",
        "Discord/community/beta-test notices",
        "GitHub publication, tags, pushes, or release claims",
    ]
    redacted_fields = [
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
        "raw_params",
    ]
    observations = [
        ("session_start_anchor", "ShooterGameMode.HandleNewPlayer", ["bIsFromLogin", "ReturnValue"]),
        ("session_end_anchor", "ShooterGameMode.OnLogout", []),
        ("stale_after_logout", "post_logout_consumer_check", ["generation_state"]),
        ("malformed_or_unsupported_evidence", "principal_consumer_boundary", []),
    ]
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1",
        "artifact_status": "synthetic_redacted_fixture",
        "readiness_classification": "shape_only_private_fixture",
        "synthetic_fixture": True,
        "private_manifest": True,
        "redacted": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "approval": {
            "approved_runtime_evidence_present": False,
            "runtime_work_authorized_by_this_manifest": False,
            "server_operations_authorized_by_this_manifest": False,
            "publication_authorized_by_this_manifest": False,
            "separate_operator_approval_required_before": approval_gates,
        },
        "observations": [
            {
                "case": case,
                "target": target,
                "synthetic": True,
                "redacted": True,
                "runtime_observed": False,
                "result": "shape_only",
                "consumer_result": "deny_or_invalidate_only",
                "copied_fields": copied_fields,
                "raw_payload_retained": False,
            }
            for case, target, copied_fields in observations
        ],
        "privacy_boundary": {
            "copied_opaque_principal_only": True,
            "redacted_fields": redacted_fields,
            "lookup_allowed": False,
            "resource_handle_allowed": False,
            "mutation_allowed": False,
            "return_override_allowed": False,
        },
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "approved_runtime_evidence_missing",
                "synthetic_shape_fixture_not_runtime_evidence",
            ],
        },
        "non_claims": [
            "synthetic/redacted shape fixture only",
            "does not approve runtime evidence or server observations",
            "does not expose real player identifiers, names, IPs, tribe ids, UE pointers, FNames, GObjects, raw params, lookup, ResourceHandle, mutation, or return override",
            "does not promote public SDK, permissions, commands, moderation, or admin authority",
        ],
    }


class RuntimePrincipalLifecycleEvidenceTests(unittest.TestCase):
    def run_checker(self, payload: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json", *args],
                check=check,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_shape_fixture_without_promoting_runtime_or_sdk(self) -> None:
        result = self.run_checker(manifest())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["shape_accepted_by_this_checker"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(
            set(report["observed_cases"]),
            {
                "session_start_anchor",
                "session_end_anchor",
                "stale_after_logout",
                "malformed_or_unsupported_evidence",
            },
        )

    def test_promote_mode_blocks_shape_fixture(self) -> None:
        result = self.run_checker(manifest(), "--promote", check=False)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("promote_blocked_without_approved_runtime_evidence", report["blockers"])
        self.assertIn("synthetic_shape_fixture_not_readiness_evidence", report["blockers"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_identity_or_pointer_leakage(self) -> None:
        payload = manifest()
        payload["observations"][0]["SteamID"] = "76561198000000000"
        result = self.run_checker(payload, check=False)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("forbidden_public_identity_source", report["blockers"])

    def test_rejects_coordinate_fields_and_readiness_overclaims(self) -> None:
        payload = manifest()
        payload["runtime_ready"] = True
        payload["observations"][0]["uobject_address"] = "0x1234"
        result = self.run_checker(payload, check=False)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("ue_coordinate_or_pointer_leakage", report["blockers"])

    def test_rejects_missing_fail_closed_cases(self) -> None:
        payload = copy.deepcopy(manifest())
        payload["observations"] = payload["observations"][:2]
        result = self.run_checker(payload, check=False)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("observations_missing_required_cases", report["blockers"])

    def test_rejects_raw_logs_and_dump_paths_as_manifest_evidence(self) -> None:
        payload = manifest()
        payload["raw_log_path"] = "/tmp/obelisk-runtime.log"
        result = self.run_checker(payload, check=False)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("ue_coordinate_or_pointer_leakage", report["blockers"])


if __name__ == "__main__":
    unittest.main()
