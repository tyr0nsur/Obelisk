#!/usr/bin/env python3
"""Tests for check_player_identity_runtime_principal_lifecycle_approved_evidence.py."""

from __future__ import annotations

import copy
import hashlib
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
RUN_ID = "20260601T120000Z-player-principal-lifecycle"
OFFLINE_WORKSPACE = Path("/servidor/ark/workspace-offline")


def temp_offline_workspace() -> tempfile.TemporaryDirectory[str]:
    if not OFFLINE_WORKSPACE.is_dir():
        raise unittest.SkipTest(f"approved offline workspace missing: {OFFLINE_WORKSPACE}")
    return tempfile.TemporaryDirectory(prefix="obelisk-test-player-principal-", dir=OFFLINE_WORKSPACE)


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
    with temp_offline_workspace() as tmp:
        log_path = Path(tmp) / "live-validation-logs" / RUN_ID / "Obelisk.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
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
    summary = analyzer_summary()
    source = summary["evidence"]["sources"][0]
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
        "operational_window": {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1",
            "ready": True,
            "operational_window_manifest_ready": True,
            "run_id": RUN_ID,
            "obelisk_commit": summary["evidence"]["obelisk_commit"],
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            "copied_log": {"path": source["path"], "path_status": "unprotected_offline", "sha256": source["sha256"]},
            "posture": {
                "pre_check": "passed",
                "post_check": "passed",
                "pre_posture": "stable",
                "post_posture": "stable",
                "plugins_disabled": True,
                "scanner_disabled": True,
                "dispatch_limit": "0",
                "wrapper_profile": "observer-debug",
                "observer_exclusivity": "player_principal_lifecycle_only",
                "debug_escape_markers": "absent",
                "callback_escape_markers": "absent",
                "native_exec_disabled": True,
                "ptrace_disabled": True,
                "single_module_summary": "player_principal_lifecycle",
            },
            "rollback": {
                "completed": True,
                "observer_env_survived": False,
                "observer_marker_survived": False,
            },
            "claims": {"delivery_claim": "none", "principal_claim": "none"},
            "user_policy": "no_regular_users",
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "source_summary": summary,
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
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
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
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["promotion_ready"])
        self.assertTrue(report["runtime_evidence_ready"])

    def test_public_and_runtime_readiness_modes_block_even_when_runtime_evidence_is_accepted(self) -> None:
        for flag, blocker in (
            ("--public-readiness", "public_readiness_blocked_until_identity_public_contract_gate"),
            ("--runtime-readiness", "runtime_readiness_blocked_until_identity_public_contract_gate"),
        ):
            with self.subTest(flag=flag):
                result = self.run_checker(manifest(), flag, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(blocker, report["blockers"])
                self.assertTrue(report["approved_runtime_evidence_present"])
                self.assertTrue(report["runtime_evidence_ready"])
                self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
                self.assertFalse(report["promotion_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_quality_blockers_from_analyzer_summary(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["blockers"] = ["runtime_observer_evidence_only", "malformed_observer_lines"]
        module["malformed_observer_lines"] = 1
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])

    def test_rejects_events_before_safe_gate_counter_from_analyzer_summary(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["blockers"] = ["runtime_observer_evidence_only", "player_principal_event_before_safe_gate"]
        module["event_before_gate_lines"] = 1
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_quality_blockers_present", report["blockers"])
        self.assertIn("runtime_summary_quality_counter_nonzero", report["blockers"])

    def test_rejects_aggregated_values_without_complete_observed_event_cases(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module.pop("observed_event_cases")
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_cases_missing", report["blockers"])

    def test_rejects_mismatched_complete_observed_event_case(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["observed_event_cases"][1]["copied_bool_values"] = ["1", "0"]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_required_observed_event_cases_missing", report["blockers"])

    def test_rejects_out_of_order_observed_lifecycle_cases(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        cases = module["observed_event_cases"]
        module["observed_event_cases"] = [
            {**cases[2], "sequence": 1},
            {**cases[0], "sequence": 2},
            {**cases[1], "sequence": 3},
        ]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_case_order_mismatch", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_extra_lifecycle_detail_values(self) -> None:
        payload = manifest()
        details = payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]
        details["principal_action"].append("public_lookup_enabled")
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_detail_values_unexpected", report["blockers"])

    def test_rejects_extra_lifecycle_detail_keys(self) -> None:
        payload = manifest()
        details = payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]
        details["redacted_fields_extra"] = ["SteamId"]
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_detail_keys_unexpected", report["blockers"])

    def test_rejects_extra_observed_lifecycle_case(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["observed_event_cases"].append(
            {
                "sequence": 4,
                "target": "ShooterGameMode.HandleNewPlayer",
                "role": "session_start_promoted",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "1"],
                "principal_action": "candidate_created",
            }
        )
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_case_unexpected", report["blockers"])

    def test_rejects_duplicate_observed_lifecycle_case(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        duplicate = copy.deepcopy(module["observed_event_cases"][0])
        duplicate["sequence"] = 4
        module["observed_event_cases"].append(duplicate)
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_case_unexpected", report["blockers"])

    def test_rejects_extra_observed_lifecycle_case_keys(self) -> None:
        payload = manifest()
        module = payload["source_summary"]["modules"]["player_principal_lifecycle"]
        module["observed_event_cases"][0]["raw_params"] = "redacted"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_summary_observed_event_case_keys_unexpected", report["blockers"])

    def test_rejects_extra_privacy_boundary_keys(self) -> None:
        payload = manifest()
        payload["privacy_boundary"]["steamid"] = "redacted"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("privacy_boundary_keys_unexpected", report["blockers"])
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

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

    def test_rejects_extended_private_identity_terms_from_current_notes(self) -> None:
        payload = manifest()
        payload["source_summary"]["modules"]["player_principal_lifecycle"]["functions"][
            "ShooterGameMode.HandleNewPlayer"
        ]["details"]["permission_state"] = ["admin"]
        payload["consumer_boundary_cases"][0]["chat_text"] = "redacted"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

    def test_rejects_positive_capability_claim_inside_extra_non_claims(self) -> None:
        payload = manifest()
        payload["non_claims"].append("public player identity ready with command reply support")
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_live_server_source_paths_in_wrapped_summary(self) -> None:
        payload = manifest()
        payload["source_summary"]["evidence"]["sources"][0]["path"] = "/servidor/ark/obelisk/logs/live.log"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_source_path_not_copied_or_offline", report["blockers"])

    def test_rejects_multiple_runtime_summary_sources(self) -> None:
        payload = manifest()
        payload["source_summary"]["evidence"]["sources"].append(
            dict(payload["source_summary"]["evidence"]["sources"][0])
        )
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_summary_sources_not_exactly_one", report["blockers"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_not_accepted")

    def test_rejects_operational_window_mismatch(self) -> None:
        payload = manifest()
        payload["operational_window"]["copied_log"]["sha256"] = hashlib.sha256(b"other").hexdigest()
        payload["operational_window"]["obelisk_commit"] = "other-commit"
        payload["operational_window"]["posture"]["dispatch_limit"] = "1"
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_copied_log_sha256_mismatch", report["blockers"])
        self.assertIn("operational_window_obelisk_commit_mismatch", report["blockers"])
        self.assertIn("operational_window_posture_mismatch", report["blockers"])

    def test_rejects_operational_window_log_path_outside_live_validation_run_shape(self) -> None:
        payload = manifest()
        source_path = Path(payload["source_summary"]["evidence"]["sources"][0]["path"])
        wrong_path = source_path.parent.parent.parent / RUN_ID / "Obelisk.log"
        payload["source_summary"]["evidence"]["sources"][0]["path"] = str(wrong_path)
        payload["operational_window"]["copied_log"]["path"] = str(wrong_path)
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operational_window_copied_log_path_not_live_validation_run_log", report["blockers"])

    def test_rejects_nested_operational_window_and_approval_overclaim_keys(self) -> None:
        payload = manifest()
        payload["approval"]["server_restart_authorized_by_this_manifest"] = True
        payload["operational_window"]["runtime_work_authorized"] = True
        payload["operational_window"]["posture"]["plugin_delivery_ready"] = True
        payload["operational_window"]["rollback"]["manual_followup_required"] = True
        payload["operational_window"]["claims"]["runtime_ready_claim"] = "ready"
        payload["consumer_boundary_cases"][0]["lookup_token_usable"] = True
        payload["promotion_gate"]["public_contract_ready"] = True
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approval_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_posture_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_rollback_keys_unexpected", report["blockers"])
        self.assertIn("operational_window_claims_keys_unexpected", report["blockers"])
        self.assertIn("consumer_boundary_case_keys_unexpected", report["blockers"])
        self.assertIn("promotion_gate_keys_unexpected", report["blockers"])

    def test_rejects_identity_or_ue_leakage_inside_operational_window(self) -> None:
        payload = manifest()
        payload["operational_window"]["steamid"] = "76561198000000000"
        payload["operational_window"]["raw_params"] = {"uobject": "0x1234"}
        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_identity_or_ue_internal_leakage", report["blockers"])

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
