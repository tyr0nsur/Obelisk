#!/usr/bin/env python3
"""Tests for check_player_identity_runtime_principal_lifecycle_approved_evidence.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def runtime_log_lines() -> list[str]:
    return [
        "[info]  Obelisk Runtime Loaded Native (LD_PRELOAD)",
        "[info] ProcessEvent vtable-derived pattern candidates found: 1",
        "[info] ProcessEvent candidate[0] = 0x1d34e20",
        "[info] Found ProcessEvent at address: 0x1d34e20",
        "[info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x767c6aaa4000",
        "[info] ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.",
        "[warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.",
        f"[info] PlayerPrincipalLifecycleObserver enabled binary_sha256={SHA} "
        "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
        "delivery_claim=none principal_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=candidate_created principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
        "target=ShooterGameMode.HandleNewPlayer post_original=true "
        "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
        "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
        "principal_action=none principal_id_logged=false principal_generation_logged=false "
        "delivery_claim=none.",
        "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
        "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
        "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
        "principal_action=candidate_invalidated principal_id_logged=false "
        "principal_generation_logged=false delivery_claim=none.",
    ]


def analyzer_summary() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "Obelisk.log"
        log_path.write_text("\n".join(runtime_log_lines()) + "\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ANALYZER), "--obelisk-commit", "test-commit", str(log_path)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return json.loads(result.stdout)


def manifest() -> dict:
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "artifact_status": "approved_runtime_observer_summary",
        "readiness_classification": "runtime_evidence_only",
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "approval": {
            "runtime_evidence_reviewed": True,
            "runtime_work_authorized_by_this_manifest": False,
            "server_operations_authorized_by_this_manifest": False,
            "publication_authorized_by_this_manifest": False,
            "discord_authorized_by_this_manifest": False,
        },
        "source_summary": analyzer_summary(),
        "consumer_boundary_cases": [
            {
                "case": "stale_after_logout",
                "result": "fail_closed",
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "result": "fail_closed",
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
        ],
        "privacy_boundary": {
            "copied_opaque_principal_only": True,
            "redacted_runtime_observer": True,
            "player_identifiers_logged": False,
            "lookup_allowed": False,
            "resource_handle_allowed": False,
            "mutation_allowed": False,
            "return_override_allowed": False,
        },
        "promotion_gate": {
            "runtime_evidence_ready": True,
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "non_claims": [
            "approved runtime observer evidence only",
            "does not promote public player identity, lookup, permissions, commands, moderation, admin authority, mutation, return override, ResourceHandle, or v1 SDK readiness",
            "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, FNames, GObjects, raw params, or persistent lookup keys",
            "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
        ],
    }


class ApprovedRuntimePrincipalLifecycleEvidenceTests(unittest.TestCase):
    def run_checker(self, payload: dict, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approved-runtime-evidence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--json", *args],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_accepts_clean_runtime_summary_without_promoting_public_sdk(self) -> None:
        result = self.run_checker(manifest())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["approved_runtime_evidence_present"])
        self.assertTrue(report["runtime_evidence_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["remaining_blockers"], [])
        self.assertEqual(
            report["observed_runtime_cases"],
            ["session_start_anchor", "session_start_rejected_anchor", "session_end_anchor"],
        )
        self.assertEqual(
            report["consumer_cases"],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )

    def test_promote_mode_blocks_even_when_runtime_evidence_is_accepted(self) -> None:
        result = self.run_checker(manifest(), "--promote", check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("promote_blocked_until_identity_public_contract_gate", report["blockers"])
        self.assertFalse(report["promotion_ready"])
        self.assertTrue(report["runtime_evidence_ready"])

    def test_rejects_quality_blockers_from_analyzer_summary(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["blockers"] = ["runtime_observer_evidence_only", "malformed_observer_lines"]
        module["malformed_observer_lines"] = 1
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])

    def test_rejects_public_readiness_and_identity_leak_overclaims(self) -> None:
        payload = manifest()
        payload["public_sdk_ready"] = True
        payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]["steamid"] = ["76561198000000000"]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_rejects_live_server_source_paths_in_wrapped_summary(self) -> None:
        payload = manifest()
        payload["source_summary"]["evidence"]["sources"][0]["path"] = "/servidor/ark/obelisk/logs/live.log"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_source_path_not_copied_or_offline", report["blockers"])

    def test_rejects_mixed_observer_modules(self) -> None:
        payload = manifest()
        payload["source_summary"]["modules"]["chat"] = {
            "accepted_count": 0,
            "functions": {},
        }
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_unexpected_modules_present", report["blockers"])

    def test_rejects_missing_rejected_start_or_fail_closed_consumer_case(self) -> None:
        payload = copy.deepcopy(manifest())
        details = payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]
        details["role"] = ["session_start"]
        payload["consumer_boundary_cases"] = payload["consumer_boundary_cases"][:1]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_detail_values_missing", report["blockers"])
        self.assertIn("consumer_boundary_cases_missing", report["blockers"])


if __name__ == "__main__":
    unittest.main()
