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

        self.assertEqual(chat["fields"]["ChatMessage"]["offsets"], ["0x0"])
        self.assertEqual(chat["fields"]["ChatMessage"]["sizes"], [16])
        self.assertEqual(chat["fields"]["SendMode"]["offsets"], ["0x10"])
        self.assertEqual(chat["fields"]["SendMode"]["has_range"], {"true": 1})
        self.assertEqual(
            chat["reject_reasons"],
            {"chat UFunction outer FName index mismatch": 1},
        )
        self.assertEqual(result["evidence"]["kind"], "runtime-observer-log")
        self.assertFalse(result["evidence"]["server_paths_allowed"])
        self.assertEqual(len(result["evidence"]["sources"]), 1)
        self.assertEqual(result["evidence"]["sources"][0]["line_count"], 15)
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
        self.assertEqual(structure["fields"]["pinCode"]["sensitive"], {"true": 1})
        self.assertEqual(structure["fields"]["pinCode"]["has_range"], {"false": 1})
        self.assertEqual(structure["reject_reasons"], {"bad_parms_size": 1})

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
