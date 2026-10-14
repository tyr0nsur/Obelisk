#!/usr/bin/env python3
"""Offline tests for analyze_runtime_observer_log.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = REPO_ROOT / "scripts" / "analyze_runtime_observer_log.py"


class RuntimeObserverLogAnalyzerTests(unittest.TestCase):
    def run_analyzer(self, lines: list[str], *extra_args: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ANALYZER), *extra_args, str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def run_analyzer_files(
        self,
        sources: list[list[str]],
        *extra_args: str,
        expect_returncode: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = []
            for index, lines in enumerate(sources):
                path = Path(temp_dir) / f"Obelisk-{index}.log"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                paths.append(str(path))
            result = subprocess.run(
                [sys.executable, str(ANALYZER), *extra_args, *paths],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, expect_returncode, result.stderr)
            return result

    def assert_payload_omits_fragments(
        self,
        payload: object,
        fragments: list[str],
    ) -> None:
        serialized = json.dumps(payload, sort_keys=True)
        for fragment in fragments:
            self.assertNotIn(fragment, serialized)

    def test_summarizes_chat_runtime_observer_evidence(self) -> None:
        result = self.run_analyzer(
            [
                "[06:41:13] [info]  Obelisk Runtime Loaded Native (LD_PRELOAD)",
                "[06:41:13] [info] ProcessEvent vtable-derived pattern candidates found: 1",
                "[06:41:13] [info] ProcessEvent candidate[0] = 0x1d34e20",
                "[06:41:13] [info] Found ProcessEvent at address: 0x1d34e20",
                "[06:41:13] [info] ProcessEvent absolute x64 hook installed successfully. "
                "patch_size=18 trampoline=0x767c6aaa4000",
                "[06:41:13] [info] ReflectionScanner disabled. "
                "Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.",
                "[06:41:13] [warning] Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.",
                "[06:41:37] [warning] Experimental chat reflection enabled for ShooterGameServer SHA256 "
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520.",
                "[07:19:58] [info] Reflected chat ProcessEvent #1 function=ServerSendChatMessage "
                "fname_index=2697 params=0x208069410 fields=2 metadata_only=false",
                "[07:19:58] [info] Reflected chat ServerSendChatMessage send_mode=0 "
                "send_mode_name=GlobalChat send_mode_known=true",
                "[07:19:58] [info] Reflected chat field ChatMessage offset=0x0 size=16 has_range=true",
                "[07:19:58] [info] Reflected chat field SendMode offset=0x10 size=1 has_range=true",
                "[07:19:58] [info] Reflected chat rejected #1 fname_index=1865 function=0x767c4fa03800 "
                "reason=chat UFunction outer FName index mismatch",
                "[07:20:03] [info] Reflected chat ProcessEvent #2 function=ServerSendChatMessage "
                "fname_index=2697 params=0x208069410 fields=2 metadata_only=false",
                "[07:20:03] [info] Reflected chat ServerSendChatMessage send_mode=1 "
                "send_mode_name=GlobalTribeChat send_mode_known=true",
                "[07:20:03] [info] Reflected chat field ChatMessage offset=0x0 size=16 has_range=true",
                "[07:20:03] [info] Reflected chat field SendMode offset=0x10 size=1 has_range=true",
            ]
        )

        modules = result["modules"]
        self.assertEqual(result["schema"], "obelisk.runtime-observer-log-summary.v1")
        self.assertEqual(result["review_scope"], "runtime_observer_evidence_summary")
        self.assertEqual(result["readiness_gate"], "none")
        self.assertEqual(
            result["promotion_gate"]["gate_type"],
            "runtime_observer_observational_only",
        )
        runtime = result["runtime"]
        self.assertTrue(runtime["loaded_native_ld_preload"])
        self.assertEqual(runtime["process_event_candidate_count"], 1)
        self.assertEqual(
            runtime["process_event_candidates"],
            [{"index": 0, "address": "0x1d34e20"}],
        )
        self.assertEqual(runtime["process_event_address"], "0x1d34e20")
        self.assertTrue(runtime["process_event_hook_installed"])
        self.assertEqual(runtime["process_event_hook_patch_size"], 18)
        self.assertEqual(runtime["broad_process_event_trace_lines"], 0)
        self.assertTrue(runtime["reflection_scanner_disabled"])
        self.assertTrue(runtime["plugins_disabled"])
        self.assertIn("chat", modules)
        chat = modules["chat"]
        self.assertEqual(chat["accepted_count"], 2)
        self.assertEqual(chat["rejected_count"], 1)
        self.assertEqual(chat["metadata_only_count"], 0)
        self.assertEqual(chat["evidence_status"], "observational")
        self.assertEqual(chat["blockers"], ["runtime_observer_evidence_only"])
        self.assertEqual(
            chat["gate_sha256"],
            ["7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"],
        )

        function = chat["functions"]["ServerSendChatMessage"]
        self.assertEqual(function["accepted"], 2)
        self.assertEqual(function["fname_indices"], [2697])
        self.assertEqual(function["field_counts"], [2])
        self.assertEqual(function["details"]["send_mode"], [0, 1])
        self.assertEqual(function["details"]["send_mode_name"], ["GlobalChat", "GlobalTribeChat"])
        self.assertEqual(function["details"]["send_mode_known"], ["true"])
        self.assertEqual(function["fields"]["ChatMessage"]["offsets"], ["0x0"])
        self.assertEqual(function["fields"]["ChatMessage"]["sizes"], [16])
        self.assertEqual(function["fields"]["SendMode"]["offsets"], ["0x10"])
        self.assertEqual(function["fields"]["SendMode"]["has_range"], {"true": 2})

        self.assertEqual(chat["fields"]["ChatMessage"]["offsets"], ["0x0"])
        self.assertEqual(chat["fields"]["ChatMessage"]["sizes"], [16])
        self.assertEqual(chat["fields"]["SendMode"]["offsets"], ["0x10"])
        self.assertEqual(chat["fields"]["SendMode"]["has_range"], {"true": 2})
        self.assertEqual(
            chat["reject_reasons"],
            {"chat UFunction outer FName index mismatch": 1},
        )
        self.assertEqual(result["evidence"]["kind"], "runtime-observer-log")
        self.assertFalse(result["evidence"]["server_paths_allowed"])
        self.assertEqual(len(result["evidence"]["sources"]), 1)
        self.assertEqual(result["evidence"]["sources"][0]["line_count"], 17)
        self.assertRegex(result["evidence"]["sources"][0]["sha256"], r"^[a-f0-9]{64}$")
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_summarizes_non_chat_module_shapes(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental structure reflection enabled for ShooterGameServer SHA256 "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
                "[info] Reflected structure ProcessEvent #1 function=VerifyPinCode "
                "fname_index=7636 outer_fname_index=7617 fields=2",
                "[info] Reflected structure field pinCode offset=0x0 size=4 sensitive=true has_range=false",
                "[info] Reflected structure field ReturnValue offset=0x4 size=1 sensitive=false has_range=true",
                "[info] Reflected structure rejected #2 fname_index=7636 reason=bad_parms_size",
            ]
        )

        structure = result["modules"]["structure"]
        self.assertEqual(structure["accepted_count"], 1)
        self.assertEqual(structure["blockers"], ["runtime_observer_evidence_only"])
        self.assertEqual(structure["functions"]["VerifyPinCode"]["outer_fname_indices"], [7617])
        self.assertEqual(
            structure["functions"]["VerifyPinCode"]["fields"]["pinCode"]["offsets"],
            ["0x0"],
        )
        self.assertEqual(
            structure["functions"]["VerifyPinCode"]["fields"]["ReturnValue"]["sizes"],
            [1],
        )
        self.assertEqual(structure["fields"]["pinCode"]["sensitive"], {"true": 1})
        self.assertEqual(structure["fields"]["pinCode"]["has_range"], {"false": 1})
        self.assertEqual(structure["reject_reasons"], {"bad_parms_size": 1})

    def test_summarizes_item_return_event_producer(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental item return event producer enabled for ShooterGameServer SHA256 "
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520.",
                "[info] Reflected item return dispatched #1 function=AllowEquipItem "
                "fname_index=6250 callbacks=1 field_mask=ReturnValue",
                "[info] Reflected item return dispatched #2 function=CanRepair "
                "fname_index=6251 callbacks=2 field_mask=ReturnValue",
                "[info] Reflected item return rejected #1 fname_index=9999 reason=non-item function",
            ]
        )

        item_return = result["modules"]["item_return"]
        self.assertEqual(item_return["accepted_count"], 2)
        self.assertEqual(item_return["rejected_count"], 1)
        self.assertEqual(item_return["blockers"], ["runtime_observer_evidence_only"])
        self.assertEqual(
            item_return["gate_sha256"],
            ["7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"],
        )
        self.assertEqual(item_return["functions"]["AllowEquipItem"]["fname_indices"], [6250])
        self.assertEqual(item_return["functions"]["AllowEquipItem"]["details"]["callbacks"], [1])
        self.assertEqual(
            item_return["functions"]["AllowEquipItem"]["details"]["field_mask"],
            ["ReturnValue"],
        )
        self.assertEqual(item_return["functions"]["CanRepair"]["details"]["callbacks"], [2])
        self.assertEqual(item_return["reject_reasons"], {"non-item function": 1})

    def test_summarizes_player_principal_lifecycle_observer_lines(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 2)
        self.assertEqual(module["observer_gate_count"], 1)
        self.assertEqual(module["blockers"], ["runtime_observer_evidence_only"])
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertEqual(module["approved_runtime_evidence_blocker"], "approved_runtime_evidence_missing")
        self.assertTrue(module["observer_enabled"])
        self.assertTrue(module["accepted_or_rejected_observer_lines_present"])
        self.assertEqual(module["accepted_lifecycle_event_roles"], ["session_start", "session_end"])
        self.assertTrue(module["accepted_lifecycle_role_set_present"])
        self.assertEqual(module["missing_lifecycle_event_roles"], ["session_start_rejected"])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertFalse(module["diagnostic_lines_present"])
        self.assertFalse(module["passive_monitor_metadata_present"])
        self.assertFalse(module["diagnostic_or_passive_only_non_evidence"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(module["copied_log_evidence_review_state"], "copied_log_incomplete_or_blocked")
        strict_summary = module["strict_lifecycle_triplet_candidate_summary"]
        self.assertEqual(strict_summary["status"], "blocked_missing_lifecycle_roles")
        self.assertFalse(strict_summary["candidate_ready_for_bundle_preflight"])
        self.assertFalse(strict_summary["approved_runtime_evidence"])
        self.assertFalse(strict_summary["runtime_evidence_ready"])
        self.assertEqual(
            strict_summary["missing_event_roles"],
            ["session_start_rejected"],
        )
        self.assertEqual(
            strict_summary["strict_rejected_start_expected_shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            strict_summary["approval_authority"],
            "downstream_bundle_checker_only",
        )
        self.assertIn(
            "required_lifecycle_event_roles_missing",
            module["non_evidence_reasons"],
        )
        self.assertEqual(
            module["observed_event_cases"],
            [
                {
                    "sequence": 1,
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "role": "session_start",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": ["1", "1"],
                    "principal_action": "candidate_created",
                    "apply_status": "session_start_created",
                    "correlation_status": "not_applicable",
                },
                {
                    "sequence": 2,
                    "target": "ShooterGameMode.OnLogout",
                    "role": "session_end",
                    "copied_bool_fields": [],
                    "copied_bool_values": [],
                    "principal_action": "candidate_invalidated",
                    "apply_status": "session_end_invalidated",
                    "correlation_status": "matched",
                },
            ],
        )
        self.assertEqual(
            module["gate_sha256"],
            ["7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"],
        )
        self.assertEqual(module["functions"]["observer_gate"]["details"]["dispatch_limit"], [0])
        self.assertEqual(module["functions"]["observer_gate"]["details"]["limit"], [10])
        start = module["functions"]["ShooterGameMode.HandleNewPlayer"]
        self.assertEqual(start["accepted"], 1)
        self.assertEqual(start["details"]["role"], ["session_start"])
        self.assertEqual(start["details"]["principal_action"], ["candidate_created"])
        self.assertEqual(start["details"]["principal_id_logged"], ["false"])
        self.assertEqual(start["details"]["principal_generation_logged"], ["false"])
        self.assertEqual(start["details"]["redacted_count"], [3])
        end = module["functions"]["ShooterGameMode.OnLogout"]
        self.assertEqual(end["details"]["role"], ["session_end"])
        self.assertEqual(end["details"]["principal_action"], ["candidate_invalidated"])

    def test_rejects_superseded_handle_new_player_rejected_start_triplet(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 2)
        self.assertEqual(
            module["accepted_lifecycle_event_roles"],
            ["session_start", "session_end"],
        )
        self.assertEqual(module["missing_lifecycle_event_roles"], ["session_start_rejected"])
        self.assertTrue(module["observer_enabled"])
        self.assertTrue(module["accepted_lifecycle_role_set_present"])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertEqual(module["observer_gate_count"], 1)
        self.assertEqual(module["diagnostic_candidate_count"], 0)
        self.assertEqual(module["malformed_observer_lines"], 1)
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {"superseded_handle_new_player_rejected_start_non_evidence": 1},
        )
        self.assertFalse(module["diagnostic_lines_present"])
        self.assertFalse(module["passive_monitor_metadata_present"])
        self.assertFalse(module["diagnostic_or_passive_only_non_evidence"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(module["copied_log_evidence_review_state"], "copied_log_incomplete_or_blocked")
        self.assertFalse(module["diagnostic_only_non_evidence"])
        self.assertIn("malformed_observer_lines", module["blockers"])
        self.assertIn("required_lifecycle_event_roles_missing", module["non_evidence_reasons"])
        self.assertFalse(result["ready"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertIn(
            "copied-log readiness fields are not runtime readiness or approval",
            result["non_claims"],
        )
        serialized = json.dumps(result, sort_keys=True)
        for forbidden_key in (
            "public_sdk_ready",
            "runtime_ready",
            "sdk_p0_progress",
            "plugin_hub_ready",
            "publication_authority",
        ):
            self.assertNotIn(f'"{forbidden_key}"', serialized)
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertEqual(module["approved_runtime_evidence_blocker"], "approved_runtime_evidence_missing")

    def test_accepts_check_join_in_progress_rejected_start_observer_event(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 3)
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertEqual(
            module["accepted_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(module["missing_lifecycle_event_roles"], [])
        self.assertTrue(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertTrue(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertTrue(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(
            [case["target"] for case in module["observed_event_cases"]],
            [
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.OnLogout",
            ],
        )
        self.assertEqual(
            module["observed_event_cases"][1],
            {
                "sequence": 2,
                "target": "ShooterGameMode.CheckJoinInProgress",
                "role": "session_start_rejected",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "principal_action": "none",
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
        )
        check_join = module["functions"]["ShooterGameMode.CheckJoinInProgress"]
        self.assertEqual(check_join["accepted"], 1)
        self.assertEqual(check_join["details"]["role"], ["session_start_rejected"])
        self.assertEqual(check_join["details"]["copied_bool_values"], ["1,0"])
        self.assertEqual(check_join["details"]["redacted_count"], [1])
        self.assertEqual(check_join["details"]["redacted_fields"], ["NewPlayer"])
        self.assertEqual(check_join["details"]["principal_action"], ["none"])
        self.assertEqual(check_join["details"]["apply_status"], ["session_start_rejected_noop"])
        self.assertEqual(check_join["details"]["correlation_status"], ["not_applicable"])
        self.assertEqual(module["redacted_detail_keys"], {})
        self.assertEqual(result["readiness_gate"], "none")
        self.assertFalse(result["ready"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["promotion_gate"]["ready"])
        self.assertEqual(
            result["readiness_boundary"]["approval_authority"],
            "downstream_bundle_checker_only",
        )
        self.assertFalse(
            result["readiness_boundary"][
                "copied_log_ready_signal_can_promote_runtime_readiness"
            ]
        )
        self.assertFalse(
            result["readiness_boundary"][
                "copied_log_ready_signal_can_promote_public_sdk_readiness"
            ]
        )
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertEqual(module["copied_log_ready_signal"]["state"], "copied_log_ready_not_approved")
        self.assertEqual(
            module["copied_log_ready_signal"]["approval_authority"],
            "downstream_bundle_checker_only",
        )
        self.assertFalse(module["copied_log_ready_signal"]["approved_runtime_evidence"])
        self.assertFalse(module["copied_log_ready_signal"]["runtime_evidence_ready"])
        self.assertFalse(module["copied_log_ready_signal"]["can_promote_runtime_readiness"])
        self.assertFalse(module["copied_log_ready_signal"]["can_promote_public_sdk_readiness"])
        strict_summary = module["strict_lifecycle_triplet_candidate_summary"]
        self.assertEqual(strict_summary["status"], "candidate_ready_for_bundle_preflight")
        self.assertTrue(strict_summary["candidate_ready_for_bundle_preflight"])
        self.assertFalse(strict_summary["approved_runtime_evidence"])
        self.assertFalse(strict_summary["runtime_evidence_ready"])
        self.assertEqual(strict_summary["accepted_event_roles"], [
            "session_start",
            "session_start_rejected",
            "session_end",
        ])
        self.assertEqual(strict_summary["missing_event_roles"], [])
        self.assertEqual(strict_summary["quality_blockers"], [])
        self.assertEqual(strict_summary["accepted_exact_check_join_observer_event_count"], 1)
        self.assertTrue(strict_summary["required_exact_check_join_observer_event_present"])
        self.assertEqual(
            strict_summary["next_action"],
            "run_approved_runtime_principal_lifecycle_bundle_preflight",
        )
        self.assertEqual(module["invalid_lifecycle_event_evidence_classification"], "none")
        self.assertEqual(module["invalid_lifecycle_event_non_evidence_count"], 0)
        self.assertEqual(module["invalid_lifecycle_event_non_evidence_reasons"], {})
        split = module["player_principal_lifecycle_event_split_summary"]
        self.assertEqual(split["class_counts"]["accepted_observer_event"], 3)
        self.assertEqual(split["class_counts"]["missing_exact_check_join_in_progress_1_0"], 0)
        self.assertEqual(split["accepted_exact_check_join_observer_event_count"], 1)
        self.assertTrue(split["required_exact_check_join_observer_event_present"])
        self.assertFalse(split["missing_exact_check_join_in_progress_1_0"])
        self.assertFalse(split["approved_runtime_evidence"])
        self.assertFalse(split["runtime_evidence_ready"])

    def test_blocks_ambiguous_duplicate_check_join_rejected_start_before_preflight(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=4 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 4)
        self.assertEqual(module["missing_lifecycle_event_roles"], [])
        self.assertTrue(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(module["copied_log_evidence_review_state"], "copied_log_incomplete_or_blocked")
        strict_summary = module["strict_lifecycle_triplet_candidate_summary"]
        self.assertEqual(strict_summary["status"], "blocked_strict_lifecycle_triplet_ambiguous")
        self.assertFalse(strict_summary["candidate_ready_for_bundle_preflight"])
        self.assertEqual(
            strict_summary["next_action"],
            "capture_one_clean_observer_window_with_exactly_one_rejected_start",
        )
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])

    def test_summarizes_player_principal_lifecycle_event_split_patterns(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[warning] PlayerPrincipalLifecycleDiagnostic route-sampling enabled "
                "sample_limit=500 params_logged=false identity_logged=false "
                "evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=1 "
                "fname_index=9999 fname_number=0 post_original=true "
                "accepted_lifecycle_target=false reflection_probe=false "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.CheckJoinInProgress fname_index=1845 post_original=true "
                "accepted_lifecycle_target=true reflection_status=matched copy_status=rejected "
                "diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue "
                "copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created "
                "correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated "
                "correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_unresolved_noop "
                "correlation_status=missing principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        split = module["player_principal_lifecycle_event_split_summary"]
        classes = {entry["code"]: entry for entry in split["classes"]}

        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertFalse(split["approved_runtime_evidence"])
        self.assertFalse(split["runtime_evidence_ready"])

        self.assertFalse(split["ready"])
        self.assertEqual(split["readiness_gate"], "none")
        self.assertEqual(
            split["class_counts"],
            {
                "accepted_observer_event": 2,
                "copy_status_rejected": 1,
                "diagnostic_route_sample": 1,
                "diagnostic_candidate": 1,
                "session_end_unresolved_noop_missing": 1,
                "missing_exact_check_join_in_progress_1_0": 1,
            },
        )
        self.assertEqual(classes["accepted_observer_event"]["label"], "accepted observer event")
        self.assertEqual(classes["copy_status_rejected"]["label"], "copy_status=rejected")
        self.assertEqual(classes["diagnostic_route_sample"]["label"], "diagnostic route sample")
        self.assertEqual(classes["diagnostic_candidate"]["label"], "diagnostic candidate")
        self.assertEqual(
            classes["session_end_unresolved_noop_missing"]["label"],
            "session_end_unresolved_noop/missing",
        )
        self.assertEqual(
            classes["missing_exact_check_join_in_progress_1_0"]["label"],
            "missing exact CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            split["observer_event_counts"],
            {
                "accepted_observer_event": 2,
                "rejected_or_non_evidence_observer_event": 1,
            },
        )
        self.assertEqual(split["diagnostic_candidate_total_count"], 2)
        self.assertEqual(split["diagnostic_candidate_without_copy_status_count"], 1)
        self.assertEqual(split["copy_status_counts"], {"rejected": 1})
        self.assertEqual(module["diagnostic_candidate_copy_status_counts"], {"rejected": 1})
        self.assertEqual(split["diagnostic_route_sample_count"], 1)
        self.assertEqual(split["session_end_unresolved_noop_missing_count"], 1)
        self.assertEqual(split["accepted_exact_check_join_observer_event_count"], 0)
        self.assertFalse(split["required_exact_check_join_observer_event_present"])
        self.assertTrue(split["missing_exact_check_join_in_progress_1_0"])
        self.assertEqual(split["diagnostic_exact_check_join_shape_candidate_count"], 1)
        self.assertEqual(split["strict_required_shape"], "ShooterGameMode.CheckJoinInProgress(1,0)")
        self.assertFalse(split["can_satisfy_lifecycle_role"])
        self.assertFalse(split["can_satisfy_complete_triplet"])
        self.assertFalse(split["can_promote_runtime_readiness"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {"session_end_unresolved_noop_outcome": 1},
        )

    def test_accepts_exact_lifecycle_triplet_with_gapped_increasing_sequences(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=4 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(
            [case["sequence"] for case in module["observed_event_cases"]],
            [1, 3, 4],
        )
        self.assertEqual(module["sequence_quality_violations"], 0)
        self.assertTrue(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertTrue(module["complete_lifecycle_event_triplet_candidate_present"])
        strict_summary = module["strict_lifecycle_triplet_candidate_summary"]
        self.assertEqual(strict_summary["status"], "candidate_ready_for_bundle_preflight")
        self.assertTrue(strict_summary["candidate_ready_for_bundle_preflight"])
        self.assertEqual(strict_summary["quality_blockers"], [])
        self.assertFalse(strict_summary["approved_runtime_evidence"])
        self.assertFalse(strict_summary["runtime_evidence_ready"])

    def test_rejects_non_evidence_check_join_in_progress_observer_material(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        result = self.run_analyzer(
            [
                gate,
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=candidate_created "
                "apply_status=session_start_created correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,0 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=4 "
                "target=ShooterGameMode.CheckJoinInProgress fname_index=1845 post_original=true "
                "accepted_lifecycle_target=false reflection_status=matched "
                "diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue "
                "copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=5 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=6 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=7 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "apply_status=session_start_rejected_noop principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=8 role=session_start "
                "target=GameMode.K2_PostLogin post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=NewPlayer "
                "principal_action=candidate_created apply_status=session_start_created "
                "correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=9 role=session_start "
                "target=ShooterGameMode.OnStartNewPlayer__DelegateSignature post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=candidate_created "
                "apply_status=session_start_created correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=10 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=PlayerData principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["accepted_lifecycle_event_roles"], [])
        self.assertEqual(
            module["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(module["diagnostic_candidate_count"], 1)
        self.assertEqual(
            module["diagnostic_candidate_target_counts"],
            {"ShooterGameMode.CheckJoinInProgress": 1},
        )
        self.assertEqual(module["malformed_observer_lines"], 9)
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {
                "malformed_lifecycle_event": 2,
                "old_format_session_start_rejected_without_status_proof": 3,
                "target_role_mismatch": 1,
                "unsupported_check_join_in_progress_bool_tuple": 2,
                "unsafe_or_unapproved_fields": 1,
            },
        )
        self.assertTrue(module["observer_enabled"])
        self.assertFalse(module["accepted_lifecycle_role_set_present"])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertTrue(module["diagnostic_lines_present"])
        self.assertFalse(module["diagnostic_or_passive_only_non_evidence"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertIn("malformed_observer_lines", module["blockers"])
        self.assertIn("player_principal_diagnostic_candidates_non_evidence", module["blockers"])
        self.assertFalse(result["approved_runtime_evidence"])

    def test_classifies_invalid_rejected_start_shapes_as_diagnostic_non_evidence(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        result = self.run_analyzer(
            [
                gate,
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,0 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(
            module["copied_log_ready_signal"]["state"],
            "copied_log_incomplete_or_blocked",
        )
        self.assertFalse(module["copied_log_ready_signal"]["can_promote_runtime_readiness"])
        self.assertFalse(module["copied_log_ready_signal"]["can_promote_public_sdk_readiness"])
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {
                "old_format_session_start_rejected_without_status_proof": 1,
                "unsupported_check_join_in_progress_bool_tuple": 2,
            },
        )
        self.assertEqual(
            module["invalid_lifecycle_event_evidence_classification"],
            "diagnostic_lifecycle_event_non_evidence",
        )
        self.assertEqual(module["invalid_lifecycle_event_non_evidence_count"], 3)
        self.assertEqual(
            module["invalid_lifecycle_event_non_evidence_reasons"],
            module["unsafe_lifecycle_event_reasons"],
        )
        self.assertIn("invalid_lifecycle_event_shapes_non_evidence", module["non_evidence_reasons"])
        self.assertIn("malformed_observer_lines_non_evidence", module["non_evidence_reasons"])
        self.assertFalse(result["readiness_boundary"]["approved_runtime_evidence"])
        self.assertFalse(result["readiness_boundary"]["runtime_evidence_ready"])

    def test_rejects_unsupported_check_join_in_progress_bool_tuple_between_valid_roles(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 2)
        self.assertEqual(module["malformed_observer_lines"], 1)
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {"unsupported_check_join_in_progress_bool_tuple": 1},
        )
        self.assertEqual(module["accepted_lifecycle_event_roles"], ["session_start", "session_end"])
        self.assertEqual(module["missing_lifecycle_event_roles"], ["session_start_rejected"])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(
            module["observed_event_cases"],
            [
                {
                    "sequence": 1,
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "role": "session_start",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": ["1", "1"],
                    "principal_action": "candidate_created",
                    "apply_status": "session_start_created",
                    "correlation_status": "not_applicable",
                },
                {
                    "sequence": 3,
                    "target": "ShooterGameMode.OnLogout",
                    "role": "session_end",
                    "copied_bool_fields": [],
                    "copied_bool_values": [],
                    "principal_action": "candidate_invalidated",
                    "apply_status": "session_end_invalidated",
                    "correlation_status": "matched",
                },
            ],
        )
        self.assertIn("malformed_observer_lines", module["blockers"])
        self.assertIn("required_lifecycle_event_roles_missing", module["non_evidence_reasons"])

    def test_rejects_check_join_in_progress_copied_bool_field_order_between_valid_roles(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=ReturnValue,bIsFromLogin copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 2)
        self.assertEqual(module["malformed_observer_lines"], 1)
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {"check_join_in_progress_copied_bool_fields_order_mismatch": 1},
        )
        self.assertEqual(module["accepted_lifecycle_event_roles"], ["session_start", "session_end"])
        self.assertEqual(module["missing_lifecycle_event_roles"], ["session_start_rejected"])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertIn("invalid_lifecycle_event_shapes_non_evidence", module["non_evidence_reasons"])

    def test_rejects_exact_lifecycle_triplet_when_roles_are_out_of_order(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_start_rejected "
                "target=ShooterGameMode.CheckJoinInProgress post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=1 redacted_fields=NewPlayer principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 3)
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertEqual(
            module["accepted_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(module["missing_lifecycle_event_roles"], [])
        self.assertTrue(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        strict_summary = module["strict_lifecycle_triplet_candidate_summary"]
        self.assertEqual(strict_summary["status"], "blocked_strict_lifecycle_triplet_order_mismatch")
        self.assertFalse(strict_summary["candidate_ready_for_bundle_preflight"])
        self.assertEqual(
            strict_summary["next_action"],
            "capture_lifecycle_roles_in_session_start_rejected_session_end_order",
        )
        self.assertIn(
            "strict_lifecycle_triplet_order_mismatch_non_evidence",
            module["non_evidence_reasons"],
        )
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])

    def test_reports_player_principal_lifecycle_gate_only_as_non_evidence(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        result = self.run_analyzer([gate])
        module = result["modules"]["player_principal_lifecycle"]

        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["observer_gate_count"], 1)
        self.assertTrue(module["observer_enabled"])
        self.assertFalse(module["accepted_or_rejected_observer_lines_present"])
        self.assertTrue(module["observer_gate_only_non_evidence"])
        self.assertFalse(module["diagnostic_only_non_evidence"])
        self.assertFalse(module["diagnostic_lines_present"])
        self.assertFalse(module["passive_monitor_metadata_present"])
        self.assertFalse(module["passive_only_non_evidence"])
        self.assertFalse(module["diagnostic_or_passive_only_non_evidence"])
        self.assertEqual(module["accepted_lifecycle_event_roles"], [])
        self.assertFalse(module["accepted_lifecycle_role_set_present"])
        self.assertEqual(
            module["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(module["copied_log_evidence_review_state"], "copied_log_incomplete_or_blocked")
        self.assertEqual(
            module["blockers"],
            ["runtime_observer_evidence_only", "no_accepted_or_rejected_observer_lines"],
        )
        self.assertIn("observer_gate_only_lifecycle_non_evidence", module["non_evidence_reasons"])
        self.assertIn("required_lifecycle_event_roles_missing", module["non_evidence_reasons"])

        failed = self.run_analyzer_files(
            [[gate]],
            "--fail-on-quality-blockers",
            expect_returncode=1,
        )
        self.assertIn("no_accepted_or_rejected_observer_lines", failed.stderr)

    def test_reports_player_principal_lifecycle_diagnostic_candidates_as_non_evidence(self) -> None:
        diagnostic_enabled = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
            "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
            "identity_logged=false evidence_claim=none principal_claim=none."
        )
        diagnostic_non_target = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
            "target=ShooterGameMode.CheckJoinInProgress fname_index=1234 post_original=true "
            "accepted_lifecycle_target=false params_logged=false identity_logged=false "
            "evidence_claim=none."
        )
        diagnostic_rejected_start = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
            "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
            "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
            "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
            "evidence_claim=none."
        )
        diagnostic_rejected_end = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=3 "
            "target=ShooterGameMode.OnLogout fname_index=9012 post_original=true "
            "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
            "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
            "evidence_claim=none."
        )
        diagnostic_copy_rejected = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=4 "
            "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
            "accepted_lifecycle_target=true reflection_status=matched copy_status=rejected "
            "params_logged=false identity_logged=false evidence_claim=none."
        )
        diagnostic_check_join_copy_rejected = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=5 "
            "target=ShooterGameMode.CheckJoinInProgress fname_index=1845 post_original=true "
            "accepted_lifecycle_target=true reflection_status=matched copy_status=rejected "
            "diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue "
            "copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer "
            "params_logged=false identity_logged=false evidence_claim=none."
        )
        diagnostic_only = self.run_analyzer(
            [
                diagnostic_enabled,
                diagnostic_non_target,
                diagnostic_rejected_start,
                diagnostic_rejected_end,
                diagnostic_copy_rejected,
                diagnostic_check_join_copy_rejected,
            ]
        )
        diagnostic_module = diagnostic_only["modules"]["player_principal_lifecycle"]
        self.assertFalse(diagnostic_only["approved_runtime_evidence"])
        self.assertFalse(diagnostic_module["approved_runtime_evidence"])
        self.assertFalse(diagnostic_module["runtime_evidence_ready"])
        self.assertEqual(diagnostic_module["accepted_count"], 0)
        self.assertEqual(diagnostic_module["rejected_count"], 0)
        self.assertEqual(diagnostic_module["metadata_only_count"], 0)
        self.assertEqual(diagnostic_module["diagnostic_candidate_count"], 5)
        self.assertEqual(diagnostic_module["diagnostic_candidate_max_sequence"], 5)
        self.assertEqual(diagnostic_module["diagnostic_log_limits"], [10])
        self.assertFalse(diagnostic_module["diagnostic_log_budget_reached"])
        self.assertFalse(diagnostic_module["observer_enabled"])
        self.assertFalse(diagnostic_module["accepted_or_rejected_observer_lines_present"])
        self.assertTrue(diagnostic_module["diagnostic_lines_present"])
        self.assertFalse(diagnostic_module["passive_monitor_metadata_present"])
        self.assertTrue(diagnostic_module["diagnostic_only_non_evidence"])
        self.assertTrue(diagnostic_module["diagnostic_or_passive_only_non_evidence"])
        self.assertFalse(diagnostic_module["passive_only_non_evidence"])
        self.assertEqual(diagnostic_module["accepted_lifecycle_event_roles"], [])
        self.assertFalse(diagnostic_module["accepted_lifecycle_role_set_present"])
        self.assertEqual(
            diagnostic_module["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertFalse(diagnostic_module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(diagnostic_module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(
            diagnostic_module["copied_log_evidence_review_state"],
            "copied_log_incomplete_or_blocked",
        )
        self.assertIn("diagnostic_candidates_non_evidence", diagnostic_module["non_evidence_reasons"])
        self.assertIn(
            "required_lifecycle_event_roles_missing",
            diagnostic_module["non_evidence_reasons"],
        )
        self.assertEqual(diagnostic_module["malformed_observer_lines"], 0)
        self.assertEqual(
            diagnostic_module["diagnostic_candidate_target_counts"],
            {
                "ShooterGameMode.CheckJoinInProgress": 2,
                "ShooterGameMode.HandleNewPlayer": 2,
                "ShooterGameMode.OnLogout": 1,
            },
        )
        self.assertEqual(
            diagnostic_module["diagnostic_candidate_reason_counts"],
            {"property_chain_cycle_detected": 2},
        )
        self.assertEqual(
            diagnostic_module["diagnostic_candidate_read_status_counts"],
            {"implausible": 2},
        )
        self.assertEqual(diagnostic_only["readiness_gate"], "none")
        self.assertFalse(diagnostic_only["promotion_gate"]["ready"])
        self.assertIn("no_accepted_or_rejected_observer_lines", diagnostic_module["blockers"])
        self.assertIn(
            "player_principal_diagnostic_candidates_non_evidence",
            diagnostic_module["blockers"],
        )

        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                diagnostic_enabled,
                diagnostic_rejected_start,
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 2)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 1)
        self.assertEqual(module["diagnostic_candidate_max_sequence"], 2)
        self.assertEqual(module["diagnostic_log_limits"], [10])
        self.assertFalse(module["diagnostic_log_budget_reached"])
        self.assertTrue(module["observer_enabled"])
        self.assertTrue(module["accepted_or_rejected_observer_lines_present"])
        self.assertTrue(module["diagnostic_lines_present"])
        self.assertFalse(module["passive_monitor_metadata_present"])
        self.assertFalse(module["diagnostic_only_non_evidence"])
        self.assertFalse(module["diagnostic_or_passive_only_non_evidence"])
        self.assertEqual(
            module["diagnostic_candidate_target_counts"],
            {"ShooterGameMode.HandleNewPlayer": 1},
        )
        self.assertEqual(
            module["diagnostic_candidate_reason_counts"],
            {"property_chain_cycle_detected": 1},
        )
        self.assertEqual(module["diagnostic_candidate_read_status_counts"], {"implausible": 1})
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertEqual(
            [case["sequence"] for case in module["observed_event_cases"]],
            [1, 2],
        )
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertEqual(module["accepted_lifecycle_event_roles"], ["session_start", "session_end"])
        self.assertTrue(module["accepted_lifecycle_role_set_present"])
        self.assertEqual(module["missing_lifecycle_event_roles"], ["session_start_rejected"])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertIn(
            "player_principal_diagnostic_candidates_non_evidence",
            module["blockers"],
        )

    def test_reports_player_principal_lifecycle_function_fname_near_miss_as_non_evidence(self) -> None:
        reason = (
            "lifecycle_function_FName_near_miss_expected_name_index_2170_"
            "observed_name_index_2670_target_ShooterGameMode.HandleNewPlayer_metadata_only_true"
        )
        diagnostic_enabled = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
            "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
            "identity_logged=false evidence_claim=none principal_claim=none."
        )
        near_miss_enabled = (
            "[warning] PlayerPrincipalLifecycleDiagnostic function-FName near-miss logging enabled "
            "scan_limit=10000 params_logged=false identity_logged=false "
            "evidence_claim=none principal_claim=none."
        )
        result = self.run_analyzer(
            [
                diagnostic_enabled,
                near_miss_enabled,
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2670 post_original=true "
                "accepted_lifecycle_target=false reflection_status=matched read_status=ok "
                f"reason={reason} diagnostic_shape=FunctionFNameNearMiss "
                "params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )
        module = result["modules"]["player_principal_lifecycle"]
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 1)
        self.assertEqual(module["diagnostic_near_miss_scan_limits"], [10000])
        self.assertEqual(module["diagnostic_candidate_target_counts"], {"ShooterGameMode.HandleNewPlayer": 1})
        self.assertEqual(module["diagnostic_candidate_read_status_counts"], {"ok": 1})
        self.assertEqual(module["diagnostic_candidate_reason_counts"], {reason: 1})
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertIn("diagnostic_candidates_non_evidence", module["non_evidence_reasons"])
        self.assertIn("required_lifecycle_event_roles_missing", module["non_evidence_reasons"])
        self.assertIn("player_principal_diagnostic_candidates_non_evidence", module["blockers"])
        self.assert_payload_omits_fragments(result, ["0x1234"])

        unsafe = self.run_analyzer(
            [
                diagnostic_enabled,
                near_miss_enabled,
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2670 post_original=true "
                "accepted_lifecycle_target=true reflection_status=matched read_status=ok "
                f"reason={reason} diagnostic_shape=FunctionFNameNearMiss "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2670 post_original=true "
                "accepted_lifecycle_target=false reflection_status=matched read_status=ok "
                f"reason={reason} diagnostic_shape=FunctionFNameNearMiss params=0x1234 "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=3 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2670 post_original=true "
                "accepted_lifecycle_target=false reflection_status=matched read_status=ok "
                f"reason={reason} diagnostic_shape=FunctionFNameNearMiss "
                "params_logged=false identity_logged=true evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=4 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2670 post_original=true "
                "accepted_lifecycle_target=false reflection_status=matched read_status=ok "
                f"reason={reason} diagnostic_shape=FunctionFNameNearMiss "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=5 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2670 post_original=true "
                "accepted_lifecycle_target=false reflection_status=matched read_status=ok "
                f"reason={reason} diagnostic_shape=FunctionFNameNearMiss "
                "params_logged=false identity_logged=false evidence_claim=runtime.",
            ]
        )
        unsafe_module = unsafe["modules"]["player_principal_lifecycle"]
        self.assertFalse(unsafe["approved_runtime_evidence"])
        self.assertFalse(unsafe_module["approved_runtime_evidence"])
        self.assertEqual(unsafe_module["accepted_count"], 0)
        self.assertEqual(unsafe_module["diagnostic_candidate_count"], 0)
        self.assertEqual(unsafe_module["diagnostic_near_miss_scan_limits"], [10000])
        self.assertEqual(unsafe_module["malformed_observer_lines"], 5)
        self.assertEqual(unsafe_module["diagnostic_candidate_target_counts"], {})
        self.assertIn("malformed_observer_lines", unsafe_module["blockers"])
        self.assert_payload_omits_fragments(unsafe, ["0x1234"])

    def test_reports_player_principal_lifecycle_route_samples_as_non_evidence(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] PlayerPrincipalLifecycleDiagnostic route-sampling enabled "
                "sample_limit=500 params_logged=false identity_logged=false "
                "evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=1 "
                "fname_index=9999 fname_number=0 post_original=true "
                "accepted_lifecycle_target=false reflection_probe=false "
                "params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )
        module = result["modules"]["player_principal_lifecycle"]

        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 0)
        self.assertEqual(module["diagnostic_route_sample_count"], 1)
        self.assertEqual(module["diagnostic_route_sample_max_sequence"], 1)
        self.assertEqual(module["diagnostic_route_sample_limits"], [500])
        self.assertFalse(module["diagnostic_route_sample_budget_reached"])
        self.assertEqual(module["diagnostic_route_sample_fname_index_counts"], {"9999": 1})
        self.assertEqual(module["diagnostic_route_sample_fname_indices"], [9999])
        self.assertEqual(module["diagnostic_route_sample_latest"]["sequence"], 1)
        self.assertEqual(module["diagnostic_route_sample_latest"]["fname_index"], 9999)
        self.assertEqual(module["diagnostic_route_sample_latest"]["fname_number"], 0)
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertTrue(module["diagnostic_lines_present"])
        self.assertTrue(module["diagnostic_only_non_evidence"])
        self.assertTrue(module["diagnostic_or_passive_only_non_evidence"])
        self.assertFalse(module["observer_gate_only_non_evidence"])
        self.assertEqual(module["accepted_lifecycle_event_roles"], [])
        self.assertEqual(
            module["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertIn("diagnostic_candidates_non_evidence", module["non_evidence_reasons"])
        self.assertIn("diagnostic_route_sample_non_evidence", module["non_evidence_reasons"])
        self.assertIn("player_principal_diagnostic_candidates_non_evidence", module["blockers"])
        self.assertIn("player_principal_route_samples_non_evidence", module["blockers"])
        self.assertIn(
            {
                "code": "diagnostic_route_sample_non_evidence",
                "count": 2,
                "sample_count": 1,
                "limit_count": 1,
                "can_promote": False,
                "can_satisfy_lifecycle_role": False,
                "can_satisfy_complete_triplet": False,
            },
            module["diagnostic_candidate_guardrails"],
        )

        unsafe = self.run_analyzer(
            [
                "[warning] PlayerPrincipalLifecycleDiagnostic route-sampling enabled "
                "sample_limit=500 params_logged=false identity_logged=false "
                "evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=1 "
                "fname_index=9999 post_original=true accepted_lifecycle_target=false "
                "reflection_probe=false params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=2 "
                "fname_index=9999 fname_number=0 post_original=false "
                "accepted_lifecycle_target=false reflection_probe=false "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=3 "
                "fname_index=9999 fname_number=0 post_original=true "
                "accepted_lifecycle_target=true reflection_probe=false "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=4 "
                "fname_index=9999 fname_number=0 post_original=true "
                "accepted_lifecycle_target=false reflection_probe=true "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=5 "
                "fname_index=9999 fname_number=0 post_original=true "
                "accepted_lifecycle_target=false reflection_probe=false "
                "params_logged=true identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=6 "
                "fname_index=9999 fname_number=0 post_original=true "
                "accepted_lifecycle_target=false reflection_probe=false "
                "params_logged=false identity_logged=true evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic route-sample sequence=7 "
                "fname_index=9999 fname_number=0 post_original=true "
                "accepted_lifecycle_target=false reflection_probe=false "
                "params_logged=false identity_logged=false evidence_claim=runtime.",
            ]
        )
        unsafe_module = unsafe["modules"]["player_principal_lifecycle"]
        self.assertFalse(unsafe["approved_runtime_evidence"])
        self.assertFalse(unsafe_module["approved_runtime_evidence"])
        self.assertEqual(unsafe_module["accepted_count"], 0)
        self.assertEqual(unsafe_module["diagnostic_route_sample_count"], 0)
        self.assertEqual(unsafe_module["diagnostic_route_sample_limits"], [500])
        self.assertEqual(unsafe_module["malformed_observer_lines"], 7)
        self.assertIn("malformed_observer_lines", unsafe_module["blockers"])

    def test_reports_player_principal_lifecycle_diagnostic_budget_pressure_as_non_evidence(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
                "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
                "identity_logged=false evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=10 "
                "target=ShooterGameMode.OnLogout fname_index=9012 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
                "evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 1)
        self.assertEqual(module["diagnostic_candidate_max_sequence"], 10)
        self.assertEqual(module["diagnostic_log_limits"], [10])
        self.assertTrue(module["diagnostic_log_budget_reached"])
        self.assertTrue(module["diagnostic_only_non_evidence"])
        self.assertEqual(result["readiness_gate"], "none")
        self.assertFalse(result["promotion_gate"]["ready"])
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])

    def test_reports_latest_player_principal_observer_line_without_raw_text(self) -> None:
        result = self.run_analyzer(
            [
                "[07:00:01] [info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
                "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
                "identity_logged=false evidence_claim=none principal_claim=none.",
                "[07:00:02] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=10 "
                "target=ShooterGameMode.OnLogout fname_index=9012 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
                "evidence_claim=none.",
            ]
        )

        latest = result["modules"]["player_principal_lifecycle"]["latest_observer_line"]
        self.assertEqual(
            latest,
            {
                "source_index": 0,
                "line_number": 2,
                "timestamp_prefix": "07:00:02",
                "kind": "diagnostic_candidate",
            },
        )
        self.assertNotIn("target", latest)
        self.assertNotIn("reason", latest)

    def test_accepts_richer_safe_player_principal_lifecycle_diagnostic_reason_tokens(self) -> None:
        reason = (
            "lifecycle_property_FName_mismatch_expected_name_index_22961_observed_count_5"
            "_prop_0_name_index_28411_prop_0_number_0_prop_0_offset_0_prop_0_size_8"
            "_prop_0_class_name_index_5_prop_3_bool_field_mask_255"
        )
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={reason} params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property.metadata:unsupported-layout params_logged=false identity_logged=false "
                "evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 2)
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertEqual(
            module["diagnostic_candidate_reason_counts"],
            {
                reason: 1,
                "property.metadata:unsupported-layout": 1,
            },
        )
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])

    def test_summarizes_exact_lifecycle_property_fname_mismatch_chain_as_diagnostic_only(self) -> None:
        rich_reason = (
            "lifecycle_property_FName_mismatch_expected_name_index_28411_observed_count_5"
            "_prop_0_name_index_28416_prop_0_number_0_prop_0_class_name_index_5"
            "_prop_1_name_index_21314_prop_1_number_0_prop_1_class_name_index_5"
            "_prop_2_name_index_22968_prop_2_number_0_prop_2_class_name_index_5"
            "_prop_3_name_index_28516_prop_3_number_0_prop_3_class_name_index_5"
            "_prop_4_name_index_17724_prop_4_number_0_prop_4_class_name_index_5"
        )
        compact_reason = (
            "lifecycle_property_FName_mismatch_expected_28411_observed_"
            "28416_21314_22968_28516_17724"
        )
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
                "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
                "identity_logged=false evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={rich_reason} params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={compact_reason} params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(result["readiness_gate"], "none")
        self.assertFalse(result["promotion_gate"]["ready"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["diagnostic_candidate_count"], 2)
        self.assertEqual(module["diagnostic_candidate_max_sequence"], 2)
        self.assertEqual(module["diagnostic_log_limits"], [10])
        self.assertFalse(module["diagnostic_log_budget_reached"])
        self.assertTrue(module["diagnostic_only_non_evidence"])
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertEqual(module["accepted_lifecycle_event_roles"], [])
        self.assertEqual(
            module["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertIn("diagnostic_candidates_non_evidence", module["non_evidence_reasons"])
        self.assertIn(
            "diagnostic_lifecycle_property_fname_mismatch_non_evidence",
            module["non_evidence_reasons"],
        )
        self.assertIn(
            "required_lifecycle_event_roles_missing",
            module["non_evidence_reasons"],
        )
        self.assertEqual(
            module["diagnostic_candidate_reason_counts"],
            {
                compact_reason: 1,
                rich_reason: 1,
            },
        )
        self.assertEqual(module["diagnostic_candidate_read_status_counts"], {"implausible": 2})
        self.assertEqual(
            module["diagnostic_candidate_lifecycle_property_fname_mismatches"],
            [
                {
                    "summary": "expected_28411_observed_28416_21314_22968_28516_17724",
                    "expected_name_index": 28411,
                    "observed_count": 5,
                    "observed_name_indices": [28416, 21314, 22968, 28516, 17724],
                    "count": 2,
                    "target_counts": {"ShooterGameMode.HandleNewPlayer": 2},
                    "read_status_counts": {"implausible": 2},
                    "fname_indices": [2170],
                    "first_sequence": 1,
                    "latest_sequence": 2,
                    "latest_occurrence": {
                        "source_index": 0,
                        "line_number": 4,
                        "timestamp_prefix": None,
                        "target": "ShooterGameMode.HandleNewPlayer",
                    },
                    "evidence_claim": "none",
                    "evidence_classification": (
                        "diagnostic_lifecycle_property_fname_mismatch_non_evidence"
                    ),
                    "approved_runtime_evidence": False,
                    "runtime_evidence_ready": False,
                    "readiness_gate": "none",
                    "reason_counts": {
                        compact_reason: 1,
                        rich_reason: 1,
                    },
                },
            ],
        )
        self.assertEqual(
            module["diagnostic_lifecycle_property_fname_mismatch_summary"],
            {
                "count": 2,
                "evidence_claim": "none",
                "evidence_classification": (
                    "diagnostic_lifecycle_property_fname_mismatch_non_evidence"
                ),
                "approved_runtime_evidence": False,
                "runtime_evidence_ready": False,
                "readiness_gate": "none",
                "patterns": [
                    {
                        "summary": (
                            "expected_28411_observed_28416_21314_22968_28516_17724"
                        ),
                        "expected_name_index": 28411,
                        "observed_count": 5,
                        "observed_name_indices": [28416, 21314, 22968, 28516, 17724],
                        "count": 2,
                        "target_counts": {"ShooterGameMode.HandleNewPlayer": 2},
                        "read_status_counts": {"implausible": 2},
                        "fname_indices": [2170],
                        "latest_sequence": 2,
                    },
                ],
            },
        )
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])

    def test_reports_compact_property_fname_chain_fields_as_diagnostic_metadata_only(
        self,
    ) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
                "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
                "identity_logged=false evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=matched read_status=ok "
                "expected_property_name_indices=28411.21307.22961.28509.17716 "
                "observed_property_fname_chain=28418,21314,22968,28516,17724 "
                "params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertFalse(result["promotion_gate"]["ready"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertEqual(result["readiness_gate"], "none")
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["accepted_lifecycle_event_roles"], [])
        self.assertFalse(module["accepted_lifecycle_role_set_present"])
        self.assertEqual(
            module["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertTrue(module["diagnostic_lines_present"])
        self.assertTrue(module["diagnostic_only_non_evidence"])
        self.assertEqual(module["diagnostic_candidate_count"], 1)
        self.assertEqual(module["diagnostic_candidate_max_sequence"], 1)
        self.assertEqual(module["diagnostic_candidate_reason_counts"], {})
        self.assertEqual(module["diagnostic_candidate_read_status_counts"], {"ok": 1})
        self.assertEqual(module["diagnostic_candidate_lifecycle_property_fname_mismatches"], [])
        self.assertEqual(module["diagnostic_lifecycle_property_fname_mismatch_summary"]["count"], 0)

        metadata = module["diagnostic_candidate_property_fname_chain_metadata"]
        self.assertEqual(metadata["count"], 2)
        self.assertEqual(metadata["chain_count"], 2)
        self.assertEqual(metadata["evidence_classification"], "diagnostic_property_fname_chain_non_evidence")
        self.assertFalse(metadata["approved_runtime_evidence"])
        self.assertFalse(metadata["runtime_evidence_ready"])
        self.assertFalse(metadata["can_satisfy_lifecycle_role"])
        self.assertFalse(metadata["can_satisfy_complete_triplet"])
        self.assertEqual(
            metadata["entries"],
            [
                {
                    "field": "expected_property_fname_chain",
                    "chain_kind": "expected",
                    "source_keys": ["expected_property_name_indices"],
                    "complete_chain_summary": True,
                    "name_index_count": 5,
                    "name_indices": [28411, 21307, 22961, 28509, 17716],
                    "count": 1,
                    "target_counts": {"ShooterGameMode.HandleNewPlayer": 1},
                    "read_status_counts": {"ok": 1},
                    "fname_indices": [2170],
                    "first_sequence": 1,
                    "latest_sequence": 1,
                    "latest_occurrence": {
                        "source_index": 0,
                        "line_number": 3,
                        "timestamp_prefix": None,
                        "target": "ShooterGameMode.HandleNewPlayer",
                    },
                    "evidence_claim": "none",
                    "evidence_classification": "diagnostic_property_fname_chain_non_evidence",
                    "approved_runtime_evidence": False,
                    "runtime_evidence_ready": False,
                    "readiness_gate": "none",
                    "can_satisfy_lifecycle_role": False,
                    "can_satisfy_complete_triplet": False,
                },
                {
                    "field": "observed_property_fname_chain",
                    "chain_kind": "observed",
                    "source_keys": ["observed_property_fname_chain"],
                    "complete_chain_summary": True,
                    "name_index_count": 5,
                    "name_indices": [28418, 21314, 22968, 28516, 17724],
                    "count": 1,
                    "target_counts": {"ShooterGameMode.HandleNewPlayer": 1},
                    "read_status_counts": {"ok": 1},
                    "fname_indices": [2170],
                    "first_sequence": 1,
                    "latest_sequence": 1,
                    "latest_occurrence": {
                        "source_index": 0,
                        "line_number": 3,
                        "timestamp_prefix": None,
                        "target": "ShooterGameMode.HandleNewPlayer",
                    },
                    "evidence_claim": "none",
                    "evidence_classification": "diagnostic_property_fname_chain_non_evidence",
                    "approved_runtime_evidence": False,
                    "runtime_evidence_ready": False,
                    "readiness_gate": "none",
                    "can_satisfy_lifecycle_role": False,
                    "can_satisfy_complete_triplet": False,
                },
            ],
        )
        self.assertIn("diagnostic_property_fname_chain_non_evidence", module["non_evidence_reasons"])
        self.assertIn("diagnostic_candidates_non_evidence", module["non_evidence_reasons"])
        self.assertIn("required_lifecycle_event_roles_missing", module["non_evidence_reasons"])
        self.assertIn("player_principal_diagnostic_candidates_non_evidence", module["blockers"])
        self.assertIn(
            {
                "code": "diagnostic_property_fname_chain_non_evidence",
                "count": 2,
                "can_promote": False,
                "can_satisfy_lifecycle_role": False,
                "can_satisfy_complete_triplet": False,
            },
            module["diagnostic_candidate_guardrails"],
        )

    def test_reports_sanitized_reason_property_fname_chain_as_diagnostic_metadata_only(
        self,
    ) -> None:
        reason = (
            "lifecycle_property_FName_mismatch_expected_name_index_17716"
            "_cause_unapproved_observed_property_FName"
            "_observed_property_fname_chain_28422_21318_22972_28520_17727"
            "_position_4_observed_count_5_prop_0_name_index_28422_truncated"
        )
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
                "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
                "identity_logged=false evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={reason} params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 1)
        self.assertEqual(module["diagnostic_candidate_reason_counts"], {reason: 1})

        metadata = module["diagnostic_candidate_property_fname_chain_metadata"]
        self.assertEqual(metadata["count"], 1)
        self.assertEqual(metadata["chain_count"], 1)
        self.assertEqual(metadata["entries"][0]["field"], "observed_property_fname_chain")
        self.assertEqual(metadata["entries"][0]["source_keys"], ["reason.observed_property_fname_chain"])
        self.assertEqual(metadata["entries"][0]["name_indices"], [28422, 21318, 22972, 28520, 17727])
        self.assertFalse(metadata["entries"][0]["approved_runtime_evidence"])
        self.assertFalse(metadata["entries"][0]["can_satisfy_complete_triplet"])

        mismatches = module["diagnostic_candidate_lifecycle_property_fname_mismatches"]
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["expected_name_index"], 17716)
        self.assertEqual(mismatches[0]["observed_count"], 5)
        self.assertEqual(mismatches[0]["observed_name_indices"], [28422, 21318, 22972, 28520, 17727])
        self.assertFalse(mismatches[0]["approved_runtime_evidence"])
        self.assertFalse(mismatches[0]["runtime_evidence_ready"])
        self.assertEqual(
            module["diagnostic_lifecycle_property_fname_mismatch_summary"]["count"],
            1,
        )
        self.assertIn("diagnostic_property_fname_chain_non_evidence", module["non_evidence_reasons"])
        self.assertIn(
            "diagnostic_lifecycle_property_fname_mismatch_non_evidence",
            module["non_evidence_reasons"],
        )

    def test_rejects_malformed_property_fname_chain_diagnostic_fields(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=matched read_status=ok "
                "observed_property_fname_chain=28418.PlayerName "
                "params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 0)
        self.assertEqual(module["diagnostic_candidate_property_fname_chain_metadata"]["count"], 0)
        self.assertEqual(module["diagnostic_candidate_property_fname_chain_metadata"]["entries"], [])
        self.assertEqual(module["malformed_observer_lines"], 1)
        self.assertIn("malformed_observer_lines", module["blockers"])
        self.assert_payload_omits_fragments(result, ["PlayerName"])

    def test_summarizes_ragnarok_lifecycle_property_fname_mismatches_by_target_as_diagnostic_only(
        self,
    ) -> None:
        handle_new_player_reason = (
            "lifecycle_property_FName_mismatch_expected_name_index_28411_observed_count_5"
            "_prop_0_name_index_28416_prop_0_number_0_prop_0_class_name_index_5"
            "_prop_1_name_index_21312_prop_1_number_0_prop_1_class_name_index_5"
            "_prop_2_name_index_22966_prop_2_number_0_prop_2_class_name_index_5"
            "_prop_3_name_index_28514_prop_3_number_0_prop_3_class_name_index_5"
            "_prop_4_name_index_17722_prop_4_number_0_prop_4_class_name_index_5"
        )
        post_restart_handle_new_player_reason = (
            "lifecycle_property_FName_mismatch_expected_name_index_28411_observed_count_5"
            "_prop_0_name_index_28419_prop_0_number_0_prop_0_class_name_index_5"
            "_prop_1_name_index_21315_prop_1_number_0_prop_1_class_name_index_5"
            "_prop_2_name_index_22969_prop_2_number_0_prop_2_class_name_index_5"
            "_prop_3_name_index_28517_prop_3_number_0_prop_3_class_name_index_5"
            "_truncated"
        )
        check_join_reason = (
            "lifecycle_property_FName_mismatch_expected_28513_observed_28514_28416_17723"
        )
        onlogout_reason = "lifecycle_property_FName_mismatch_expected_17724_observed_28548"
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
                "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
                "identity_logged=false evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={handle_new_player_reason} params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.CheckJoinInProgress fname_index=1845 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={check_join_reason} params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=3 "
                "target=ShooterGameMode.OnLogout fname_index=2171 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={onlogout_reason} params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=4 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={post_restart_handle_new_player_reason} "
                "params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(result["readiness_gate"], "none")
        self.assertFalse(result["ready"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["promotion_gate"]["ready"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["diagnostic_candidate_count"], 4)
        self.assertTrue(module["diagnostic_only_non_evidence"])
        self.assertTrue(module["diagnostic_or_passive_only_non_evidence"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertEqual(
            module["diagnostic_candidate_target_counts"],
            {
                "ShooterGameMode.CheckJoinInProgress": 1,
                "ShooterGameMode.HandleNewPlayer": 2,
                "ShooterGameMode.OnLogout": 1,
            },
        )
        self.assertEqual(
            module["diagnostic_candidate_reason_counts"],
            {
                check_join_reason: 1,
                handle_new_player_reason: 1,
                onlogout_reason: 1,
                post_restart_handle_new_player_reason: 1,
            },
        )
        self.assertIn(
            "diagnostic_lifecycle_property_fname_mismatch_non_evidence",
            module["non_evidence_reasons"],
        )
        self.assertIn("player_principal_diagnostic_candidates_non_evidence", module["blockers"])

        compact_summary = module["diagnostic_lifecycle_property_fname_mismatch_summary"]
        self.assertEqual(compact_summary["count"], 4)
        self.assertEqual(
            compact_summary["evidence_classification"],
            "diagnostic_lifecycle_property_fname_mismatch_non_evidence",
        )
        self.assertFalse(compact_summary["approved_runtime_evidence"])
        self.assertFalse(compact_summary["runtime_evidence_ready"])
        self.assertEqual(compact_summary["readiness_gate"], "none")
        compact_patterns = {
            pattern["summary"]: pattern
            for pattern in compact_summary["patterns"]
        }
        self.assertEqual(
            compact_patterns[
                "expected_28411_observed_28416_21312_22966_28514_17722"
            ]["observed_name_indices"],
            [28416, 21312, 22966, 28514, 17722],
        )
        self.assertEqual(
            compact_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["observed_name_indices"],
            [28419, 21315, 22969, 28517],
        )
        self.assertEqual(
            compact_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["observed_count"],
            5,
        )
        self.assertEqual(
            compact_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["observed_present_count"],
            4,
        )
        self.assertFalse(
            compact_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["observed_name_indices_complete"]
        )
        self.assertTrue(
            compact_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["truncated"]
        )
        self.assertEqual(
            compact_patterns[
                "expected_28513_observed_28514_28416_17723"
            ]["observed_name_indices"],
            [28514, 28416, 17723],
        )
        self.assertEqual(
            compact_patterns["expected_17724_observed_28548"]["observed_name_indices"],
            [28548],
        )

        target_summary = module[
            "diagnostic_lifecycle_property_fname_mismatch_target_summary"
        ]
        self.assertEqual(target_summary["count"], 4)
        self.assertEqual(target_summary["target_count"], 3)
        self.assertEqual(
            target_summary["evidence_classification"],
            "diagnostic_lifecycle_property_fname_mismatch_non_evidence",
        )
        self.assertFalse(target_summary["approved_runtime_evidence"])
        self.assertFalse(target_summary["runtime_evidence_ready"])
        self.assertEqual(target_summary["readiness_gate"], "none")
        targets = {target["target"]: target for target in target_summary["targets"]}
        handle_new_player_patterns = {
            pattern["summary"]: pattern
            for pattern in targets["ShooterGameMode.HandleNewPlayer"]["patterns"]
        }
        self.assertEqual(targets["ShooterGameMode.HandleNewPlayer"]["count"], 2)
        self.assertEqual(targets["ShooterGameMode.HandleNewPlayer"]["pattern_count"], 2)
        self.assertEqual(
            handle_new_player_patterns[
                "expected_28411_observed_28416_21312_22966_28514_17722"
            ]["observed_name_indices"],
            [28416, 21312, 22966, 28514, 17722],
        )
        self.assertEqual(
            handle_new_player_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["observed_name_indices"],
            [28419, 21315, 22969, 28517],
        )
        self.assertEqual(
            handle_new_player_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["observed_count"],
            5,
        )
        self.assertEqual(
            handle_new_player_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["observed_present_count"],
            4,
        )
        self.assertFalse(
            handle_new_player_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["observed_name_indices_complete"]
        )
        self.assertTrue(
            handle_new_player_patterns[
                "expected_28411_observed_28419_21315_22969_28517"
            ]["truncated"]
        )
        self.assertEqual(
            targets["ShooterGameMode.CheckJoinInProgress"]["patterns"][0][
                "observed_name_indices"
            ],
            [28514, 28416, 17723],
        )
        self.assertEqual(
            targets["ShooterGameMode.OnLogout"]["patterns"][0]["observed_name_indices"],
            [28548],
        )
        for target_name in (
            "ShooterGameMode.CheckJoinInProgress",
            "ShooterGameMode.OnLogout",
        ):
            target = targets[target_name]
            self.assertEqual(target["count"], 1)
            self.assertEqual(target["pattern_count"], 1)
            pattern = target["patterns"][0]
            self.assertEqual(pattern["count"], 1)
            self.assertEqual(pattern["read_status_counts"], {"implausible": 1})
        for pattern in handle_new_player_patterns.values():
            self.assertEqual(pattern["count"], 1)
            self.assertEqual(pattern["read_status_counts"], {"implausible": 1})

    def test_multisource_lifecycle_diagnostic_mismatch_stays_non_evidence(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        diagnostic_enabled = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
            "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
            "identity_logged=false evidence_claim=none principal_claim=none."
        )
        reason = (
            "lifecycle_property_FName_mismatch_expected_28411_observed_"
            "28418_21314_22968_28516_17724"
        )
        diagnostic = (
            "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=10 "
            "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
            "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
            f"reason={reason} params_logged=false identity_logged=false evidence_claim=none."
        )
        result = self.run_analyzer_files([[gate, diagnostic_enabled, diagnostic], [gate]])
        payload = json.loads(result.stdout)
        module = payload["modules"]["player_principal_lifecycle"]

        self.assertFalse(payload["approved_runtime_evidence"])
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertEqual(module["source_indices"], [0, 1])
        self.assertFalse(module["source_merge_explicit"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 1)
        self.assertTrue(module["diagnostic_only_non_evidence"])
        self.assertFalse(module["observer_gate_only_non_evidence"])
        self.assertEqual(
            module["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertIn("multiple_sources_same_module", module["blockers"])
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])
        self.assertIn("player_principal_diagnostic_candidates_non_evidence", module["blockers"])
        self.assertIn("player_principal_observer_gate_count_mismatch", module["blockers"])
        self.assertIn("multiple_sources_same_module", module["non_evidence_reasons"])
        self.assertIn("diagnostic_candidates_non_evidence", module["non_evidence_reasons"])
        self.assertIn(
            "diagnostic_lifecycle_property_fname_mismatch_non_evidence",
            module["non_evidence_reasons"],
        )
        self.assertIn("required_lifecycle_event_roles_missing", module["non_evidence_reasons"])
        self.assertEqual(
            module["diagnostic_candidate_lifecycle_property_fname_mismatches"],
            [
                {
                    "summary": "expected_28411_observed_28418_21314_22968_28516_17724",
                    "expected_name_index": 28411,
                    "observed_count": 5,
                    "observed_name_indices": [28418, 21314, 22968, 28516, 17724],
                    "count": 1,
                    "target_counts": {"ShooterGameMode.HandleNewPlayer": 1},
                    "read_status_counts": {"implausible": 1},
                    "fname_indices": [2170],
                    "first_sequence": 10,
                    "latest_sequence": 10,
                    "latest_occurrence": {
                        "source_index": 0,
                        "line_number": 3,
                        "timestamp_prefix": None,
                        "target": "ShooterGameMode.HandleNewPlayer",
                    },
                    "evidence_claim": "none",
                    "evidence_classification": (
                        "diagnostic_lifecycle_property_fname_mismatch_non_evidence"
                    ),
                    "approved_runtime_evidence": False,
                    "runtime_evidence_ready": False,
                    "readiness_gate": "none",
                    "reason_counts": {reason: 1},
                },
            ],
        )
        self.assertEqual(
            module["diagnostic_lifecycle_property_fname_mismatch_summary"],
            {
                "count": 1,
                "evidence_claim": "none",
                "evidence_classification": (
                    "diagnostic_lifecycle_property_fname_mismatch_non_evidence"
                ),
                "approved_runtime_evidence": False,
                "runtime_evidence_ready": False,
                "readiness_gate": "none",
                "patterns": [
                    {
                        "summary": "expected_28411_observed_28418_21314_22968_28516_17724",
                        "expected_name_index": 28411,
                        "observed_count": 5,
                        "observed_name_indices": [28418, 21314, 22968, 28516, 17724],
                        "count": 1,
                        "target_counts": {"ShooterGameMode.HandleNewPlayer": 1},
                        "read_status_counts": {"implausible": 1},
                        "fname_indices": [2170],
                        "latest_sequence": 10,
                    },
                ],
            },
        )

        failed = self.run_analyzer_files(
            [[gate, diagnostic_enabled, diagnostic], [gate]],
            "--fail-on-quality-blockers",
            expect_returncode=1,
        )
        self.assertIn("multiple_sources_same_module", failed.stderr)
        self.assertIn("player_principal_diagnostic_candidates_non_evidence", failed.stderr)

    def test_reports_lifecycle_property_fname_drift_as_diagnostic_only(self) -> None:
        drift_reason = (
            "lifecycle_property_FName_drift_unresolved_shape_exact_1_copy_scope_none"
            "_function_name_index_2170_outer_name_index_9619_drift_count_1"
            "_drift_0_position_0_drift_0_expected_name_index_28411"
            "_drift_0_observed_name_index_28418_drift_0_delta_7"
        )
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
                "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
                "identity_logged=false evidence_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={drift_reason} params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.OnLogout fname_index=2171 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={drift_reason} params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(result["readiness_gate"], "none")
        self.assertFalse(result["promotion_gate"]["ready"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["diagnostic_candidate_count"], 2)
        self.assertEqual(module["diagnostic_candidate_reason_counts"], {drift_reason: 2})
        self.assertEqual(module["diagnostic_candidate_read_status_counts"], {"implausible": 2})
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])

    def test_summarizes_latest_onlogout_rejected_drift_as_diagnostic_only(self) -> None:
        handle_new_player_drift = (
            "lifecycle_property_FName_drift_unresolved_shape_exact_1_copy_scope_none"
            "_function_name_index_2170_outer_name_index_9619_drift_count_1"
            "_drift_0_position_0_drift_0_expected_name_index_28411"
            "_drift_0_observed_name_index_28418_drift_0_delta_7"
        )
        onlogout_drift = (
            "lifecycle_property_FName_drift_unresolved_shape_exact_1_copy_scope_none"
            "_function_name_index_2171_outer_name_index_9619_drift_count_1"
            "_drift_0_position_0_drift_0_expected_name_index_17724"
            "_drift_0_observed_name_index_17731_drift_0_delta_7"
        )
        result = self.run_analyzer(
            [
                "[15:02:00] [info] PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
                "target_set=players-lifecycle-anchor-candidates limit=10 params_logged=false "
                "identity_logged=false evidence_claim=none principal_claim=none.",
                "[15:02:01] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={handle_new_player_drift} params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[15:03:37] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.OnLogout fname_index=2171 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                f"reason={onlogout_drift} params_logged=false identity_logged=false "
                "evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertEqual(result["readiness_gate"], "none")
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 2)
        self.assertEqual(module["diagnostic_candidate_rejected_drift_count"], 2)
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertEqual(
            module["diagnostic_candidate_rejected_drift_target_counts"],
            {
                "ShooterGameMode.HandleNewPlayer": 1,
                "ShooterGameMode.OnLogout": 1,
            },
        )
        latest = module["diagnostic_candidate_latest_rejected_drift_by_target"][
            "ShooterGameMode.OnLogout"
        ]
        self.assertEqual(latest["timestamp_prefix"], "15:03:37")
        self.assertEqual(latest["sequence"], 2)
        self.assertEqual(latest["target"], "ShooterGameMode.OnLogout")
        self.assertEqual(latest["reflection_status"], "rejected")
        self.assertEqual(latest["evidence_claim"], "none")
        self.assertFalse(latest["approved_runtime_evidence"])
        self.assertFalse(latest["ready"])
        self.assertEqual(latest["readiness_gate"], "none")
        self.assertEqual(latest["reason_kind"], "lifecycle_property_FName_drift")
        self.assertEqual(latest["function_name_index"], 2171)
        self.assertEqual(latest["outer_name_index"], 9619)
        self.assertEqual(latest["drift_count"], 1)
        self.assertEqual(
            latest["drifts"],
            [
                {
                    "index": 0,
                    "position": 0,
                    "expected_name_index": 17724,
                    "observed_name_index": 17731,
                    "delta": 7,
                }
            ],
        )
        self.assertNotIn("params_logged", latest)
        self.assertNotIn("identity_logged", latest)
        self.assertNotIn("raw_params", latest)
        self.assertIn("diagnostic_rejected_drift_non_evidence", module["non_evidence_reasons"])
        self.assertIn("diagnostic_rejected_drift_non_evidence", module["blockers"])
        self.assertIn(
            {
                "code": "diagnostic_rejected_drift_non_evidence",
                "count": 2,
                "can_promote": False,
                "required_next_step": (
                    "compare distinct sanitized lifecycle snapshot roots before "
                    "another approved runtime-evidence attempt"
                ),
            },
            module["diagnostic_candidate_guardrails"],
        )

    def test_accepts_check_join_in_progress_diagnostic_shape_as_non_evidence(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.CheckJoinInProgress fname_index=1845 post_original=true "
                "accepted_lifecycle_target=false reflection_status=matched "
                "diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue "
                "copied_bool_values=0,1 redacted_count=1 redacted_fields=NewPlayer "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.CheckJoinInProgress fname_index=1845 post_original=true "
                "accepted_lifecycle_target=true reflection_status=matched copy_status=rejected "
                "diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue "
                "copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer "
                "params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 2)
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertEqual(
            module["diagnostic_candidate_target_counts"],
            {"ShooterGameMode.CheckJoinInProgress": 2},
        )
        summary = module["diagnostic_check_join_in_progress_summary"]
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["strict_required_shape"], "ShooterGameMode.CheckJoinInProgress(1,0)")
        self.assertEqual(summary["strict_shape_candidate_count"], 1)
        self.assertEqual(summary["strict_shape_copy_rejected_count"], 1)
        self.assertEqual(
            summary["shape_counts"],
            {
                "ShooterGameMode.CheckJoinInProgress(0,1)": 1,
                "ShooterGameMode.CheckJoinInProgress(1,0)": 1,
            },
        )
        self.assertFalse(summary["can_satisfy_session_start_rejected_anchor"])
        self.assertEqual(summary["required_observer_event_role"], "session_start_rejected")
        self.assertEqual(
            summary["required_observer_event_shape"],
            {
                "target": "ShooterGameMode.CheckJoinInProgress",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "redacted_fields": ["NewPlayer"],
            },
        )
        latest = summary["latest_strict_shape_candidate"]
        self.assertEqual(latest["sequence"], 2)
        self.assertEqual(latest["strict_shape"], "ShooterGameMode.CheckJoinInProgress(1,0)")
        self.assertEqual(latest["copy_status"], "rejected")
        self.assertFalse(latest["approved_runtime_evidence"])
        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(module["runtime_evidence_ready"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])
        self.assertIn("player_principal_diagnostic_candidates_non_evidence", module["blockers"])
        self.assertIn(
            "player_principal_diagnostic_check_join_in_progress_non_evidence",
            module["blockers"],
        )
        self.assertIn(
            "diagnostic_check_join_in_progress_non_evidence",
            module["non_evidence_reasons"],
        )
        self.assertIn(
            {
                "code": "diagnostic_check_join_in_progress_non_evidence",
                "count": 2,
                "can_promote": False,
                "required_runtime_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
            },
            module["diagnostic_candidate_guardrails"],
        )

    def test_rejects_malformed_check_join_in_progress_diagnostic_shapes(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        defaults = {
            "accepted_lifecycle_target": "false",
            "copied_bool_fields": "bIsFromLogin,ReturnValue",
            "copied_bool_values": "0,1",
            "redacted_count": "1",
            "redacted_fields": "NewPlayer",
            "target": "ShooterGameMode.CheckJoinInProgress",
            "copy_status": "",
        }
        cases = {
            "malformed copied bool value": {"copied_bool_values": "0,2"},
            "missing copied bool value": {"copied_bool_values": "0"},
            "wrong copied field order": {"copied_bool_fields": "ReturnValue,bIsFromLogin"},
            "wrong redacted field": {"redacted_fields": "PlayerData"},
            "accepted lifecycle target without copy_status": {"accepted_lifecycle_target": "true"},
            "nonaccepted target with copy_status": {"copy_status": "copy_status=rejected "},
            "other target": {"target": "ShooterGameMode.HandleNewPlayer"},
        }

        for label, overrides in cases.items():
            with self.subTest(label=label):
                values = {**defaults, **overrides}
                result = self.run_analyzer(
                    [
                        gate,
                        "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                        f"target={values['target']} fname_index=1845 post_original=true "
                        f"accepted_lifecycle_target={values['accepted_lifecycle_target']} "
                        f"reflection_status=matched {values['copy_status']}"
                        "diagnostic_shape=CheckJoinInProgress "
                        f"copied_bool_fields={values['copied_bool_fields']} "
                        f"copied_bool_values={values['copied_bool_values']} "
                        f"redacted_count={values['redacted_count']} "
                        f"redacted_fields={values['redacted_fields']} "
                        "params_logged=false identity_logged=false evidence_claim=none.",
                    ]
                )

                module = result["modules"]["player_principal_lifecycle"]
                self.assertEqual(module["accepted_count"], 0)
                self.assertEqual(module["rejected_count"], 0)
                self.assertEqual(module["diagnostic_candidate_count"], 0)
                self.assertEqual(module["diagnostic_candidate_target_counts"], {})
                self.assertEqual(module["malformed_observer_lines"], 1)
                self.assertIn("malformed_observer_lines", module["blockers"])

    def test_accepts_k2_post_login_diagnostic_shape_as_non_evidence(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=GameMode.K2_PostLogin fname_index=4943 post_original=true "
                "accepted_lifecycle_target=false reflection_status=matched "
                "diagnostic_shape=K2_PostLogin redacted_count=1 redacted_fields=NewPlayer "
                "params_logged=false identity_logged=false evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 1)
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertEqual(
            module["diagnostic_candidate_target_counts"],
            {"GameMode.K2_PostLogin": 1},
        )
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])

    def test_rejects_malformed_k2_post_login_diagnostic_shapes(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        defaults = {
            "accepted_lifecycle_target": "false",
            "target": "GameMode.K2_PostLogin",
            "redacted_count": "1",
            "redacted_fields": "NewPlayer",
            "extra": "",
        }
        cases = {
            "copied bool payload": {
                "extra": "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
            },
            "wrong redacted field": {"redacted_fields": "PlayerData"},
            "accepted lifecycle target": {"accepted_lifecycle_target": "true"},
            "other target": {"target": "ShooterGameMode.HandleNewPlayer"},
            "missing redacted fields": {"redacted_count": "", "redacted_fields": ""},
        }

        for label, overrides in cases.items():
            with self.subTest(label=label):
                values = {**defaults, **overrides}
                redacted = ""
                if values["redacted_count"]:
                    redacted = (
                        f"redacted_count={values['redacted_count']} "
                        f"redacted_fields={values['redacted_fields']} "
                    )
                result = self.run_analyzer(
                    [
                        gate,
                        "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                        f"target={values['target']} fname_index=4943 post_original=true "
                        f"accepted_lifecycle_target={values['accepted_lifecycle_target']} "
                        "reflection_status=matched diagnostic_shape=K2_PostLogin "
                        f"{redacted}{values['extra']}"
                        "params_logged=false identity_logged=false evidence_claim=none.",
                    ]
                )

                module = result["modules"]["player_principal_lifecycle"]
                self.assertEqual(module["accepted_count"], 0)
                self.assertEqual(module["rejected_count"], 0)
                self.assertEqual(module["diagnostic_candidate_count"], 0)
                self.assertEqual(module["diagnostic_candidate_target_counts"], {})
                self.assertEqual(module["malformed_observer_lines"], 1)
                self.assertIn("malformed_observer_lines", module["blockers"])

    def test_flags_unsafe_player_principal_lifecycle_diagnostic_candidates(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=1 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
                "evidence_claim=runtime.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=2 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property_chain_cycle_detected params=0x1234 params_logged=false "
                "identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=3 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=steamid_123 params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=4 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property_chain_cycle_detected params_logged=false identity_logged=true "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=5 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property.offset:0x10 params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=6 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property.metadata:PlayerName params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=7 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property/metadata params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=8 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=steam_id_123 params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=9 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=player_id_123 params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=10 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=unique_net_id_123 params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=11 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=resource_handle_abc params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=12 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=tribe_id_1 params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=13 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=ip_address_1 params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=14 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=lifecycle_property_class_object_index_mismatch params_logged=false "
                "identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=15 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=null_UFunction_pointer params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=16 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property_range_exceeds_params params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=17 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=matched "
                "diagnostic_shape=CheckJoinInProgress copied_bool_fields=bIsFromLogin,ReturnValue "
                "copied_bool_values=1,1 redacted_count=1 redacted_fields=NewPlayer "
                "params_logged=false identity_logged=false evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=18 "
                "target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true "
                "accepted_lifecycle_target=true reflection_status=matched role=session_start "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created params_logged=false identity_logged=false "
                "evidence_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["diagnostic_candidate_count"], 0)
        self.assertEqual(module["diagnostic_candidate_target_counts"], {})
        self.assertEqual(module["diagnostic_candidate_reason_counts"], {})
        self.assertEqual(module["diagnostic_candidate_read_status_counts"], {})
        self.assertEqual(module["malformed_observer_lines"], 18)
        self.assertIn("malformed_observer_lines", module["blockers"])

    def test_rejects_superseded_handle_new_player_rejected_start_observer_lines(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,0 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observer_gate_count"], 1)
        self.assertEqual(module["malformed_observer_lines"], 3)
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {"superseded_handle_new_player_rejected_start_non_evidence": 3},
        )
        self.assertIn("malformed_observer_lines", module["blockers"])

    def test_flags_duplicate_player_principal_lifecycle_observer_gate(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        result = self.run_analyzer(
            [
                gate,
                gate,
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["observer_gate_count"], 2)
        self.assertIn("player_principal_observer_gate_count_mismatch", module["blockers"])

    def test_flags_malformed_player_principal_lifecycle_lines(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true raw_pointer=0x1234",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["malformed_observer_lines"], 1)
        self.assertIn("missing_experimental_gate", module["blockers"])
        self.assertIn("malformed_observer_lines", module["blockers"])

    def test_flags_unsafe_player_principal_lifecycle_gate_claims(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=1 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=delivered principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=0 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=11 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["malformed_observer_lines"], 4)
        self.assertEqual(module["gate_sha256"], [])
        self.assertIn("malformed_observer_lines", module["blockers"])

    def test_flags_player_principal_lifecycle_sequence_quality_violations(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=2 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 1)
        self.assertEqual(
            [case["sequence"] for case in module["observed_event_cases"]],
            [1],
        )
        self.assertEqual(module["sequence_quality_violations"], 2)
        self.assertEqual(module["timestamp_quality_violations"], 0)
        self.assertIn("sequence_quality_violation", module["blockers"])

    def test_flags_player_principal_lifecycle_timestamp_regressions(self) -> None:
        result = self.run_analyzer(
            [
                "[07:00:00] [info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[07:00:01] [info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[07:00:00] [info] PlayerPrincipalLifecycleObserver event sequence=2 "
                "role=session_start_rejected target=ShooterGameMode.HandleNewPlayer "
                "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
                "copied_bool_values=0,1 redacted_count=3 "
                "redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=none "
                "apply_status=session_start_rejected_noop correlation_status=not_applicable "
                "principal_id_logged=false principal_generation_logged=false delivery_claim=none.",
                "[07:00:02] [info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 2)
        self.assertEqual(
            [case["role"] for case in module["observed_event_cases"]],
            ["session_start", "session_end"],
        )
        self.assertEqual(module["sequence_quality_violations"], 0)
        self.assertEqual(module["timestamp_quality_violations"], 0)
        self.assertEqual(module["malformed_observer_lines"], 1)
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {"superseded_handle_new_player_rejected_start_non_evidence": 1},
        )
        self.assertIn("malformed_observer_lines", module["blockers"])

    def test_rejects_generic_reflected_player_principal_lifecycle_lines_as_non_evidence(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental player_principal_lifecycle reflection enabled for "
                "ShooterGameServer SHA256 "
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520.",
                "[info] Reflected player_principal_lifecycle ProcessEvent #1 "
                "function=ShooterGameMode.HandleNewPlayer fname_index=5678 fields=0 "
                "metadata_only=false",
                "[info] Reflected player_principal_lifecycle rejected #2 fname_index=5678 "
                "function=ShooterGameMode.HandleNewPlayer reason=session_start",
                "[info] Reflected player_principal_lifecycle ShooterGameMode.HandleNewPlayer "
                "role=session_start principal_action=candidate_created",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["gate_sha256"], [])
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["non_observer_lifecycle_lines"], 4)
        self.assertEqual(module["passive_monitor_metadata_lines"], 0)
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertIn("player_principal_non_observer_lifecycle_lines", module["blockers"])
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])

    def test_passive_monitor_lifecycle_transcript_lines_are_non_evidence(self) -> None:
        gate = (
            "[07:00:00] [info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        start = (
            "[07:00:01] [info] PlayerPrincipalLifecycleObserver event sequence=1 "
            "role=session_start target=ShooterGameMode.HandleNewPlayer post_original=true "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
            "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
            "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
        rejected = (
            "[07:00:02] [info] PlayerPrincipalLifecycleObserver event sequence=2 "
            "role=session_start_rejected target=ShooterGameMode.HandleNewPlayer "
            "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
            "copied_bool_values=0,1 redacted_count=3 "
            "redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=none "
            "apply_status=session_start_rejected_noop correlation_status=not_applicable "
            "principal_id_logged=false principal_generation_logged=false delivery_claim=none."
        )
        end = (
            "[07:00:03] [info] PlayerPrincipalLifecycleObserver event sequence=3 "
            "role=session_end target=ShooterGameMode.OnLogout post_original=true "
            "copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting "
            "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
        diagnostic = (
            "[07:00:04] [info] PlayerPrincipalLifecycleDiagnostic candidate sequence=4 "
            "target=ShooterGameMode.HandleNewPlayer fname_index=5678 post_original=true "
            "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
            "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
            "evidence_claim=none."
        )
        lines = [
            "tick utc=2026-06-04T05:00:00Z",
            "query instance=arkserver map=Ragnarok query_port=27015 status=ok players=1/70",
            "query_warning instance=arkserver rc=20 details_fallback=disabled "
            "map=Ragnarok query_port=27015 note=PlayerPrincipalLifecycleObserver_event",
            "linuxgsm_skipped instance=arkserver commands=monitor,details reason=passive_path "
            "map=Ragnarok query_port=27015",
            "observer_tail instance=arkserver status=matched lines=5 scan_lines=200 limit=10",
            f"observer instance=arkserver {gate}",
            f"observer instance=arkserver {start}",
            f"observer instance=arkserver {rejected}",
            f"observer instance=arkserver {end}",
            f"observer instance=arkserver {diagnostic}",
            "passive_snapshot_captured output_dir=/tmp/passive detected_instances=arkserver summary='{}'",
        ]
        result = self.run_analyzer(lines)

        self.assertFalse(result["approved_runtime_evidence"])
        self.assertEqual(result["runtime"]["passive_monitor_metadata_lines"], 11)
        module = result["modules"]["player_principal_lifecycle"]
        self.assertFalse(module["approved_runtime_evidence"])
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["rejected_count"], 0)
        self.assertEqual(module["metadata_only_count"], 0)
        self.assertEqual(module["observer_gate_count"], 0)
        self.assertFalse(module["observer_enabled"])
        self.assertFalse(module["accepted_or_rejected_observer_lines_present"])
        self.assertEqual(module["diagnostic_candidate_count"], 0)
        self.assertFalse(module["diagnostic_lines_present"])
        self.assertTrue(module["passive_monitor_metadata_present"])
        self.assertTrue(module["passive_only_non_evidence"])
        self.assertTrue(module["diagnostic_or_passive_only_non_evidence"])
        self.assertEqual(module["observed_event_cases"], [])
        self.assertFalse(module["accepted_lifecycle_role_set_present"])
        self.assertEqual(
            module["missing_lifecycle_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(module["copied_log_evidence_review_state"], "copied_log_incomplete_or_blocked")
        self.assertEqual(module["passive_monitor_metadata_lines"], 6)
        self.assertEqual(module["non_observer_lifecycle_lines"], 0)
        self.assertEqual(module["malformed_observer_lines"], 0)
        self.assertEqual(
            module["latest_observer_line"],
            {
                "source_index": 0,
                "line_number": 10,
                "timestamp_prefix": None,
                "kind": "passive_monitor_metadata",
            },
        )
        self.assertIn("player_principal_passive_monitor_metadata_lines", module["blockers"])
        self.assertIn("no_accepted_or_rejected_observer_lines", module["blockers"])
        self.assertIn("passive_monitor_metadata_non_evidence", module["non_evidence_reasons"])
        self.assertIn("required_lifecycle_event_roles_missing", module["non_evidence_reasons"])

        failed = self.run_analyzer_files(
            [lines],
            "--fail-on-quality-blockers",
            expect_returncode=1,
        )
        self.assertIn("passive_monitor_metadata_lines=11", failed.stderr)

    def test_passive_monitor_exact_lifecycle_triplet_remains_non_evidence(self) -> None:
        gate = (
            "[07:00:00] [info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        start = (
            "[07:00:01] [info] PlayerPrincipalLifecycleObserver event sequence=1 "
            "role=session_start target=ShooterGameMode.HandleNewPlayer post_original=true "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
            "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
            "principal_action=candidate_created apply_status=session_start_created "
            "correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
        rejected = (
            "[07:00:02] [info] PlayerPrincipalLifecycleObserver event sequence=2 "
            "role=session_start_rejected target=ShooterGameMode.CheckJoinInProgress "
            "post_original=true copied_bool_fields=bIsFromLogin,ReturnValue "
            "copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer "
            "principal_action=none apply_status=session_start_rejected_noop "
            "correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
        end = (
            "[07:00:03] [info] PlayerPrincipalLifecycleObserver event sequence=3 "
            "role=session_end target=ShooterGameMode.OnLogout post_original=true "
            "copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting "
            "principal_action=candidate_invalidated apply_status=session_end_invalidated "
            "correlation_status=matched principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none."
        )
        result = self.run_analyzer(
            [
                f"observer instance=arkserver {gate}",
                f"observer instance=arkserver {start}",
                f"observer instance=arkserver {rejected}",
                f"observer instance=arkserver {end}",
            ]
        )

        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertEqual(result["runtime"]["passive_monitor_metadata_lines"], 4)
        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observer_gate_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["accepted_lifecycle_event_roles"], [])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertTrue(module["passive_only_non_evidence"])
        self.assertIn("player_principal_passive_monitor_metadata_lines", module["blockers"])
        self.assertIn("passive_monitor_metadata_non_evidence", module["non_evidence_reasons"])

    def test_rcon_runtime_window_and_notice_lines_are_passive_non_evidence(self) -> None:
        lines = [
            "rcon_listplayers instance=arkserver map=Ragnarok query_port=27015 "
            "rcon_port=27020 status=ok players_current=1 target_key=arkserver:Ragnarok:27015 "
            "presence_detected=true detection_source=rcon_listplayers_redacted "
            "rcon_output_redacted=true",
            "player_presence_context instance=arkserver map=Ragnarok query_signal=zero "
            "rcon_signal=present observer_signal=unavailable_no_log",
            "runtime_window_plan status=planned approved_runtime_evidence=false",
            "player_notice_action status=prepared player_notice_counts_as_approved_runtime_evidence=false",
            "beta_notice_sent status=confirmed approved_runtime_evidence=false",
        ]
        result = self.run_analyzer(lines)

        self.assertFalse(result["approved_runtime_evidence"])
        self.assertFalse(result["runtime_evidence_ready"])
        self.assertEqual(result["runtime"]["passive_monitor_metadata_lines"], len(lines))
        self.assertEqual(result["modules"], {})

    def test_generated_reports_and_status_sidecars_are_not_log_evidence(self) -> None:
        schemas = [
            "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1",
            "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
            "obelisk.player-principal-lifecycle-ready-log-copy.v1",
            "obelisk.player-principal-lifecycle-runtime-evidence-status.v1",
            "obelisk.sdk-status-report.v1",
        ]

        for schema in schemas:
            with self.subTest(schema=schema):
                result = self.run_analyzer(
                    [
                        json.dumps(
                            {
                                "schema": schema,
                                "ready": True,
                                "approved_runtime_evidence": True,
                                "runtime_evidence_ready": True,
                                "embedded_line": (
                                    "PlayerPrincipalLifecycleObserver event sequence=1 "
                                    "role=session_start target=ShooterGameMode.HandleNewPlayer"
                                ),
                            },
                            sort_keys=True,
                        )
                    ]
                )

                self.assertFalse(result["approved_runtime_evidence"])
                self.assertFalse(result["runtime_evidence_ready"])
                module = result["modules"].get("player_principal_lifecycle")
                if module is not None:
                    self.assertEqual(module["accepted_count"], 0)
                    self.assertEqual(module["observed_event_cases"], [])
                    self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
                    self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])

    def test_flags_player_principal_lifecycle_events_before_safe_gate(self) -> None:
        lines = [
            "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
            "target=ShooterGameMode.HandleNewPlayer post_original=true "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
            "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
            "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none.",
            "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
            "target=ShooterGameMode.HandleNewPlayer post_original=true "
            "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
            "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
            "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
            "delivery_claim=none.",
            "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
            "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
            "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
            "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
            "principal_generation_logged=false delivery_claim=none.",
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none.",
        ]
        result = self.run_analyzer(lines)
        module = result["modules"]["player_principal_lifecycle"]

        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["event_before_gate_lines"], 3)
        self.assertIn("player_principal_event_before_safe_gate", module["blockers"])

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(ANALYZER), "--fail-on-quality-blockers", str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(failed.returncode, 1)
        self.assertIn("player_principal_event_before_safe_gate", failed.stderr)

    def test_flags_old_format_player_principal_lifecycle_lines_without_status_proof(self) -> None:
        lines = [
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
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
        result = self.run_analyzer(lines)
        module = result["modules"]["player_principal_lifecycle"]

        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["malformed_observer_lines"], 3)
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {
                "old_format_session_start_without_status_proof": 1,
                "old_format_session_start_rejected_without_status_proof": 1,
                "old_format_session_end_without_status_proof": 1,
            },
        )
        self.assertIn("malformed_observer_lines", module["blockers"])

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(ANALYZER), "--fail-on-quality-blockers", str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(failed.returncode, 1)
        self.assertIn("malformed_observer_lines", failed.stderr)

    def test_flags_unsafe_player_principal_lifecycle_event_semantics(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=false "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true "
                "copied_bool_fields=Exiting copied_bool_values=1 redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=4 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=5 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,bIsFromLogin copied_bool_values=1,0 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=6 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting,steamid "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=7 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_unresolved_noop correlation_status=missing principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=8 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_duplicate_noop correlation_status=duplicate principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=9 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_stale_noop correlation_status=stale principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=10 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=missing principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["malformed_observer_lines"], 10)
        self.assertIn("malformed_observer_lines", module["blockers"])

    def test_rejects_unsafe_session_end_outcomes_as_non_evidence(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        cases = [
            ("session_end_unresolved_noop", "unresolved"),
            ("session_end_unresolved_noop", "missing"),
            ("session_end_duplicate_noop", "duplicate"),
            ("session_end_stale_noop", "stale"),
            ("unsupported_observation", "unresolved"),
            ("registry_failure", "missing"),
            ("session_end_invalidated", "missing"),
            ("session_end_invalidated", "duplicate"),
            ("session_end_invalidated", "stale"),
            ("session_end_invalidated", "unresolved"),
        ]
        lines = [gate]
        for sequence, (apply_status, correlation_status) in enumerate(cases, start=1):
            lines.append(
                f"[info] PlayerPrincipalLifecycleObserver event sequence={sequence} "
                "role=session_end target=ShooterGameMode.OnLogout post_original=true "
                "copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                f"principal_action=candidate_invalidated apply_status={apply_status} "
                f"correlation_status={correlation_status} principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none."
            )

        result = self.run_analyzer(lines)
        module = result["modules"]["player_principal_lifecycle"]

        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["accepted_lifecycle_event_roles"], [])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertEqual(module["malformed_observer_lines"], len(cases))
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {
                "registry_failure_outcome": 1,
                "session_end_correlation_status_duplicate": 1,
                "session_end_correlation_status_missing": 1,
                "session_end_correlation_status_stale": 1,
                "session_end_correlation_status_unresolved": 1,
                "session_end_duplicate_noop_outcome": 1,
                "session_end_stale_noop_outcome": 1,
                "session_end_unresolved_noop_outcome": 2,
                "unsupported_observation_outcome": 1,
            },
        )
        self.assertIn("malformed_observer_lines", module["blockers"])

    def test_rejects_unsafe_session_start_status_proofs_as_non_evidence(self) -> None:
        gate = (
            "[info] PlayerPrincipalLifecycleObserver enabled "
            "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
            "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
            "delivery_claim=none principal_claim=none."
        )
        cases = [
            ("session_start", "1,1", "candidate_created", "session_start_created", "matched"),
            ("session_start", "1,1", "candidate_created", "session_start_rejected_noop", "not_applicable"),
            ("session_start", "1,1", "candidate_created", "session_start_allocation_failed", "missing"),
            ("session_start_rejected", "0,1", "none", "session_start_rejected_noop", "matched"),
            ("session_start_rejected", "0,1", "none", "session_start_created", "not_applicable"),
        ]
        lines = [gate]
        for sequence, (
            role,
            copied_bool_values,
            principal_action,
            apply_status,
            correlation_status,
        ) in enumerate(cases, start=1):
            lines.append(
                f"[info] PlayerPrincipalLifecycleObserver event sequence={sequence} "
                f"role={role} target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue "
                f"copied_bool_values={copied_bool_values} redacted_count=3 "
                "redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                f"principal_action={principal_action} apply_status={apply_status} "
                f"correlation_status={correlation_status} principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none."
            )

        result = self.run_analyzer(lines)
        module = result["modules"]["player_principal_lifecycle"]

        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["accepted_lifecycle_event_roles"], [])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertEqual(module["malformed_observer_lines"], len(cases))
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {"apply_or_correlation_status_mismatch": len(cases)},
        )
        self.assertIn("malformed_observer_lines", module["blockers"])

    def test_lifecycle_triplet_fails_closed_when_diagnostics_or_unsafe_lines_are_present(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleDiagnostic candidate sequence=4 "
                "target=ShooterGameMode.OnLogout fname_index=9012 post_original=true "
                "accepted_lifecycle_target=true reflection_status=rejected read_status=implausible "
                "reason=property_chain_cycle_detected params_logged=false identity_logged=false "
                "evidence_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=5 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_duplicate_noop correlation_status=duplicate principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 2)
        self.assertEqual(
            module["accepted_lifecycle_event_roles"],
            ["session_start", "session_end"],
        )
        self.assertTrue(module["accepted_lifecycle_role_set_present"])
        self.assertFalse(module["complete_accepted_lifecycle_role_triplet_present"])
        self.assertFalse(module["complete_lifecycle_event_triplet_candidate_present"])
        self.assertTrue(module["diagnostic_lines_present"])
        self.assertFalse(module["diagnostic_or_passive_only_non_evidence"])
        self.assertFalse(module["copied_log_ready_but_not_approved_evidence"])
        self.assertEqual(module["copied_log_evidence_review_state"], "copied_log_incomplete_or_blocked")
        self.assertIn(
            "player_principal_diagnostic_candidates_non_evidence",
            module["lifecycle_role_triplet_quality_blockers"],
        )
        self.assertIn(
            "malformed_observer_lines",
            module["lifecycle_role_triplet_quality_blockers"],
        )
        strict_summary = module["strict_lifecycle_triplet_candidate_summary"]
        self.assertEqual(strict_summary["status"], "blocked_missing_lifecycle_roles")
        self.assertFalse(strict_summary["candidate_ready_for_bundle_preflight"])
        self.assertFalse(strict_summary["approved_runtime_evidence"])
        self.assertEqual(strict_summary["missing_event_roles"], ["session_start_rejected"])
        self.assertIn(
            "player_principal_diagnostic_candidates_non_evidence",
            strict_summary["quality_blockers"],
        )
        self.assertIn("malformed_observer_lines", strict_summary["quality_blockers"])
        self.assertEqual(
            module["unsafe_lifecycle_event_reasons"],
            {
                "session_end_duplicate_noop_outcome": 1,
                "superseded_handle_new_player_rejected_start_non_evidence": 1,
            },
        )

    def test_lifecycle_malformed_identity_details_do_not_reach_output(self) -> None:
        result = self.run_analyzer(
            [
                "[info] PlayerPrincipalLifecycleObserver enabled "
                "binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 "
                "target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 "
                "delivery_claim=none principal_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated apply_status=session_end_invalidated "
                "correlation_status=matched principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none player_name=SurvivorAlice steamid=76561198000000000 "
                "ip_address=203.0.113.44 raw_text=secret-player-message.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["observed_event_cases"], [])
        self.assertEqual(module["malformed_observer_lines"], 1)
        self.assert_payload_omits_fragments(
            result,
            [
                "SurvivorAlice",
                "76561198000000000",
                "203.0.113.44",
                "secret-player-message",
                "player_name",
                "steamid",
                "raw_text",
            ],
        )

    def test_keeps_same_field_name_layouts_separate_by_function(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
                "[info] Reflected inventory ProcessEvent #1 function=CanUse "
                "fname_index=6252 outer_fname_index=6231 fields=1",
                "[info] Reflected inventory field ReturnValue offset=0x4 size=1 has_range=true",
                "[info] Reflected inventory ProcessEvent #2 function=CanEquip "
                "fname_index=7001 outer_fname_index=6231 fields=1",
                "[info] Reflected inventory field ReturnValue offset=0x8 size=4 has_range=true",
            ]
        )

        inventory = result["modules"]["inventory"]
        self.assertEqual(inventory["fields"]["ReturnValue"]["offsets"], ["0x4", "0x8"])
        self.assertEqual(
            inventory["functions"]["CanUse"]["fields"]["ReturnValue"]["offsets"],
            ["0x4"],
        )
        self.assertEqual(
            inventory["functions"]["CanUse"]["fields"]["ReturnValue"]["sizes"],
            [1],
        )
        self.assertEqual(
            inventory["functions"]["CanEquip"]["fields"]["ReturnValue"]["offsets"],
            ["0x8"],
        )
        self.assertEqual(
            inventory["functions"]["CanEquip"]["fields"]["ReturnValue"]["sizes"],
            [4],
        )

    def test_records_commit_override(self) -> None:
        result = self.run_analyzer(
            [
                "[info] Reflected inventory ProcessEvent #1 function=CanUse "
                "fname_index=6252 outer_fname_index=6231 fields=2",
            ],
            "--obelisk-commit",
            "test-commit",
        )

        self.assertEqual(result["evidence"]["obelisk_commit"], "test-commit")

    def test_blocks_missing_gate_mixed_sha_and_malformed_lines(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
                "1111111111111111111111111111111111111111111111111111111111111111.",
                "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
                "2222222222222222222222222222222222222222222222222222222222222222.",
                "prefix garbage Reflected inventory ProcessEvent #1 function=CanUse "
                "fname_index=6252 outer_fname_index=6231 fields=2",
                "[info] Reflected structure ProcessEvent #1 function=VerifyPinCode "
                "fname_index=7636 outer_fname_index=7617 fields=2",
            ]
        )

        inventory = result["modules"]["inventory"]
        self.assertEqual(inventory["accepted_count"], 0)
        self.assertEqual(inventory["malformed_observer_lines"], 1)
        self.assertIn("mixed_binary_sha256", inventory["blockers"])
        self.assertIn("malformed_observer_lines", inventory["blockers"])

        structure = result["modules"]["structure"]
        self.assertEqual(structure["accepted_count"], 1)
        self.assertIn("missing_experimental_gate", structure["blockers"])

    def test_redacts_unapproved_detail_keys(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental chat reflection enabled for ShooterGameServer SHA256 "
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520.",
                "[info] Reflected chat ServerSendChatMessage send_mode=0 send_mode_name=GlobalChat "
                "send_mode_known=true text=\"player message\" player_id=123",
            ]
        )

        function = result["modules"]["chat"]["functions"]["ServerSendChatMessage"]
        self.assertEqual(function["details"]["send_mode"], [0])
        self.assertEqual(function["details"]["send_mode_name"], ["GlobalChat"])
        self.assertNotIn("text", function["details"])
        self.assertNotIn("player_id", function["details"])
        self.assertEqual(
            result["modules"]["chat"]["redacted_detail_keys"],
            {"identity_like_detail": 1, "raw_player_text_detail": 1},
        )
        self.assert_payload_omits_fragments(result, ["player message", "player_id"])
        self.assertIn(
            "redacted_sensitive_or_unapproved_details",
            result["modules"]["chat"]["blockers"],
        )

    def test_refuses_live_server_paths_by_default(self) -> None:
        live_path = Path("/servidor/ark/obelisk/logs/test-live-observer.log")
        result = subprocess.run(
            [sys.executable, str(ANALYZER), str(live_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to read live server path", result.stderr)

    def test_allows_offline_workspace_path_past_live_server_guard(self) -> None:
        offline_path = Path("/servidor/ark/workspace-offline/__missing_observer_policy_test__.log")
        result = subprocess.run(
            [sys.executable, str(ANALYZER), str(offline_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("log does not exist", result.stderr)
        self.assertNotIn("refusing to read live server path", result.stderr)

    def test_fail_on_quality_blockers_allows_clean_observational_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text(
                "\n".join(
                    [
                        "[warning] Experimental structure reflection enabled for ShooterGameServer SHA256 "
                        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
                        "[info] Reflected structure ProcessEvent #1 function=VerifyPinCode "
                        "fname_index=7636 outer_fname_index=7617 fields=2",
                        "[info] Reflected structure field pinCode offset=0x0 size=4 has_range=true",
                        "[info] Reflected structure field ReturnValue offset=0x4 size=1 has_range=true",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(ANALYZER), "--fail-on-quality-blockers", str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_broad_process_event_trace_lines_block_quality_gate(self) -> None:
        lines = [
            "[warning] Experimental structure reflection enabled for ShooterGameServer SHA256 "
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
            "[info] ProcessEvent detour hit #1 object=0x111 function=0x222 params=0x333 "
            "fname_index=6252 fname_number=0",
            "[info] Reflected structure ProcessEvent #1 function=VerifyPinCode "
            "fname_index=7636 outer_fname_index=7617 fields=2",
            "[info] Reflected structure field pinCode offset=0x0 size=4 has_range=true",
            "[info] Reflected structure field ReturnValue offset=0x4 size=1 has_range=true",
        ]
        result = self.run_analyzer(lines)
        self.assertEqual(result["runtime"]["broad_process_event_trace_lines"], 1)
        self.assertEqual(result["modules"]["structure"]["blockers"], ["runtime_observer_evidence_only"])

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(ANALYZER), "--fail-on-quality-blockers", str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(failed.returncode, 1)
        self.assertIn("broad_process_event_trace_lines=1", failed.stderr)

    def test_gate_only_module_is_quality_blocker(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
            ]
        )

        inventory = result["modules"]["inventory"]
        self.assertIn("no_accepted_or_rejected_observer_lines", inventory["blockers"])

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text(
                "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.\n",
                encoding="utf-8",
            )
            failed = subprocess.run(
                [sys.executable, str(ANALYZER), "--fail-on-quality-blockers", str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(failed.returncode, 1)
        self.assertIn("no_accepted_or_rejected_observer_lines", failed.stderr)

    def test_orphan_field_line_is_quality_blocker(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
                "[info] Reflected inventory field ReturnValue offset=0x0 size=1 has_range=true",
            ]
        )

        inventory = result["modules"]["inventory"]
        self.assertEqual(inventory["orphan_field_lines"], 1)
        self.assertIn("orphan_field_lines", inventory["blockers"])

    def test_field_count_mismatch_blocks_quality_gate(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental structure reflection enabled for ShooterGameServer SHA256 "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
                "[info] Reflected structure ProcessEvent #1 function=VerifyPinCode "
                "fname_index=7636 outer_fname_index=7617 fields=2",
                "[info] Reflected structure field pinCode offset=0x0 size=4 has_range=true",
            ]
        )

        structure = result["modules"]["structure"]
        self.assertEqual(structure["field_count_mismatches"], 1)
        self.assertIn("field_count_mismatch", structure["blockers"])

    def test_extra_field_after_expected_count_is_not_attached_to_previous_function(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
                "[info] Reflected inventory ProcessEvent #1 function=CanUse "
                "fname_index=6252 outer_fname_index=6231 fields=1",
                "[info] Reflected inventory field ReturnValue offset=0x4 size=1 has_range=true",
                "[info] Reflected inventory field ExtraValue offset=0x8 size=4 has_range=true",
            ]
        )

        inventory = result["modules"]["inventory"]
        self.assertEqual(inventory["out_of_order_field_lines"], 1)
        self.assertIn("out_of_order_field_lines", inventory["blockers"])
        self.assertNotIn("ExtraValue", inventory["functions"]["CanUse"]["fields"])

    def test_rejects_same_module_across_multiple_sources_without_explicit_merge(self) -> None:
        first = [
            "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
            "[info] Reflected inventory ProcessEvent #1 function=CanUse "
            "fname_index=6252 outer_fname_index=6231 fields=1",
            "[info] Reflected inventory field ReturnValue offset=0x4 size=1 has_range=true",
        ]
        second = [
            "[warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 "
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.",
            "[info] Reflected inventory ProcessEvent #1 function=CanUse "
            "fname_index=6252 outer_fname_index=6231 fields=1",
            "[info] Reflected inventory field ReturnValue offset=0x8 size=4 has_range=true",
        ]

        failed = self.run_analyzer_files(
            [first, second],
            "--fail-on-quality-blockers",
            expect_returncode=1,
        )
        self.assertIn("multiple_sources_same_module", failed.stderr)

        merged = self.run_analyzer_files(
            [first, second],
            "--merge-module-sources",
            "--fail-on-quality-blockers",
        )
        payload = json.loads(merged.stdout)
        inventory = payload["modules"]["inventory"]
        self.assertTrue(inventory["source_merge_explicit"])
        self.assertEqual(inventory["source_indices"], [0, 1])
        self.assertNotIn("multiple_sources_same_module", inventory["blockers"])

    def test_fail_on_quality_blockers_rejects_malformed_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text(
                "garbage Reflected inventory ProcessEvent #1 function=CanUse "
                "fname_index=6252 outer_fname_index=6231 fields=2\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(ANALYZER), "--fail-on-quality-blockers", str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("quality blockers", result.stderr)
        self.assertIn("inventory", result.stderr)

    def test_fail_on_quality_blockers_rejects_empty_observer_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("[info] unrelated line\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ANALYZER), "--fail-on-quality-blockers", str(log_path)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("no_runtime_observer_evidence", result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["modules"], {})


if __name__ == "__main__":
    unittest.main()
