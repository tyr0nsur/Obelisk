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
    def run_analyzer(self, lines: list[str]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ANALYZER), str(log_path)],
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
        self.assertIn("chat", modules)
        chat = modules["chat"]
        self.assertEqual(chat["accepted_count"], 2)
        self.assertEqual(chat["rejected_count"], 1)
        self.assertEqual(chat["metadata_only_count"], 0)
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
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_summarizes_non_chat_module_shapes(self) -> None:
        result = self.run_analyzer(
            [
                "[warning] Experimental structure reflection enabled for ShooterGameServer SHA256 abc123abc123abc1.",
                "[info] Reflected structure ProcessEvent #1 function=VerifyPinCode "
                "fname_index=7636 outer_fname_index=7617 fields=2",
                "[info] Reflected structure field pinCode offset=0x0 size=4 sensitive=true has_range=false",
                "[info] Reflected structure field ReturnValue offset=0x4 size=1 sensitive=false has_range=true",
                "[info] Reflected structure rejected #2 fname_index=7636 reason=bad_parms_size",
            ]
        )

        structure = result["modules"]["structure"]
        self.assertEqual(structure["accepted_count"], 1)
        self.assertEqual(structure["functions"]["VerifyPinCode"]["outer_fname_indices"], [7617])
        self.assertEqual(structure["fields"]["pinCode"]["sensitive"], {"true": 1})
        self.assertEqual(structure["fields"]["pinCode"]["has_range"], {"false": 1})
        self.assertEqual(structure["reject_reasons"], {"bad_parms_size": 1})


if __name__ == "__main__":
    unittest.main()
