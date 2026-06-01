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
                "principal_action=candidate_created principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 2)
        self.assertEqual(module["blockers"], ["runtime_observer_evidence_only"])
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
                },
                {
                    "sequence": 2,
                    "target": "ShooterGameMode.OnLogout",
                    "role": "session_end",
                    "copied_bool_fields": [],
                    "copied_bool_values": [],
                    "principal_action": "candidate_invalidated",
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

    def test_accepts_safe_player_principal_lifecycle_rejections(self) -> None:
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
                "principal_action=none principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,0 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 3)
        self.assertNotIn("malformed_observer_lines", module["blockers"])

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
                "principal_action=candidate_created principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=1 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 3)
        self.assertEqual(module["sequence_quality_violations"], 2)
        self.assertIn("sequence_quality_violation", module["blockers"])

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
                "principal_action=candidate_created principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=2 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=3 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true "
                "copied_bool_fields=Exiting copied_bool_values=1 redacted_count=1 redacted_fields=Exiting "
                "principal_action=candidate_invalidated principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=4 role=session_start "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=0,1 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=candidate_created principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=5 role=session_start_rejected "
                "target=ShooterGameMode.HandleNewPlayer post_original=true "
                "copied_bool_fields=bIsFromLogin,bIsFromLogin copied_bool_values=1,0 "
                "redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter "
                "principal_action=none principal_id_logged=false principal_generation_logged=false "
                "delivery_claim=none.",
                "[info] PlayerPrincipalLifecycleObserver event sequence=6 role=session_end "
                "target=ShooterGameMode.OnLogout post_original=true copied_bool_fields= "
                "copied_bool_values= redacted_count=1 redacted_fields=Exiting,steamid "
                "principal_action=candidate_invalidated principal_id_logged=false "
                "principal_generation_logged=false delivery_claim=none.",
            ]
        )

        module = result["modules"]["player_principal_lifecycle"]
        self.assertEqual(module["accepted_count"], 0)
        self.assertEqual(module["malformed_observer_lines"], 6)
        self.assertIn("malformed_observer_lines", module["blockers"])

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
            {"player_id": 1, "text": 1},
        )
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
