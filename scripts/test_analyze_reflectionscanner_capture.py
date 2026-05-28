#!/usr/bin/env python3
"""Offline tests for analyze_reflectionscanner_capture.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = REPO_ROOT / "scripts" / "analyze_reflectionscanner_capture.py"
EVIDENCE_PACK_BUILDER = REPO_ROOT / "scripts" / "build_reflection_evidence_pack.py"


def fname_probe(
    *,
    target: str = "candidate",
    source_global: str = "0x600000",
    table: str = "0x7f0000001000",
    matched: int = 3,
    matched_max: int = 3,
    num_elements: int = 10000,
    num_chunks: int = 1,
    none: str = "None",
    client_message: str = "ClientMessage",
    server_chat: str = "ServerChat",
) -> str:
    return (
        f"[ReflectionScanner] {target} FName indirect-table probe: "
        f"source_global={source_global} table={table} score=8/8 readable_clues=3/3 "
        f"matched_clues={matched}/{matched_max} "
        f"num_elements={num_elements} num_chunks={num_chunks} "
        f"none='{none}' client_message='{client_message}' "
        f"server_chat='{server_chat}'"
    )


def fname_reject(
    *,
    target: str = "candidate",
    source_global: str = "0x600000",
    table: str = "0x7f0000001000",
    reason: str = "unreadable_chunk_pointer",
    readable: int = 0,
    readable_max: int = 3,
    matched: int = 0,
    matched_max: int = 3,
    num_elements: int = 10000,
    num_chunks: int = 1,
    none: str = "",
    client_message: str = "",
    server_chat: str = "",
) -> str:
    return (
        f"[ReflectionScanner] {target} FName indirect-table reject: "
        f"source_global={source_global} table={table} reason={reason} "
        f"readable_clues={readable}/{readable_max} matched_clues={matched}/{matched_max} "
        f"num_elements={num_elements} num_chunks={num_chunks} "
        f"none='{none}' client_message='{client_message}' "
        f"server_chat='{server_chat}'"
    )


def static_fname_root_probe(
    *,
    slot: str = "0x5956f30",
    table: str = "0x7f0000001000",
    matched: int = 3,
    matched_max: int = 3,
    header_index_ok: int = 3,
    header_index_ok_max: int = 3,
    num_elements: int = 10000,
    num_chunks: int = 1,
    none: str = "None",
    client_message: str = "ClientMessage",
    server_chat: str = "ServerChat",
) -> str:
    return (
        "[ReflectionScanner] StaticFNameRoot FName static-root probe: "
        f"slot={slot} table={table} score=9/9 readable_clues=3/3 "
        f"matched_clues={matched}/{matched_max} "
        f"header_index_ok={header_index_ok}/{header_index_ok_max} "
        f"num_elements={num_elements} num_chunks={num_chunks} "
        f"none='{none}' client_message='{client_message}' "
        f"server_chat='{server_chat}'"
    )


def static_fname_root_reject(
    *,
    slot: str = "0x5956f30",
    table: str = "0x0",
    reason: str = "null_table",
    readable: int = 0,
    readable_max: int = 3,
    matched: int = 0,
    matched_max: int = 3,
    header_index_ok: int = 0,
    header_index_ok_max: int = 3,
    num_elements: int = 0,
    num_chunks: int = 0,
    none: str = "",
    client_message: str = "",
    server_chat: str = "",
) -> str:
    return (
        "[ReflectionScanner] StaticFNameRoot FName static-root reject: "
        f"slot={slot} table={table} reason={reason} "
        f"readable_clues={readable}/{readable_max} matched_clues={matched}/{matched_max} "
        f"header_index_ok={header_index_ok}/{header_index_ok_max} "
        f"num_elements={num_elements} num_chunks={num_chunks} "
        f"none='{none}' client_message='{client_message}' "
        f"server_chat='{server_chat}'"
    )


def static_fname_root_sample(
    *,
    slot: str = "0x5956f30",
    table: str = "0x7f0000001000",
    target: str = "ServerChat",
    source_global: str | None = None,
    object: str = "0x7f0000002000",
    index: int = 9622,
    header_index_ok: bool = True,
    name: str = "ServerChat",
    status: str = "match",
    reason: str = "exact_name",
    num_elements: int | None = None,
    num_chunks: int | None = None,
) -> str:
    header_text = "true" if header_index_ok else "false"
    source_text = f"source_global={source_global} " if source_global else ""
    counts_text = (
        f" num_elements={num_elements} num_chunks={num_chunks}"
        if num_elements is not None and num_chunks is not None
        else ""
    )
    return (
        "[ReflectionScanner] StaticFNameRoot FName sample: "
        f"slot={slot} table={table} target={target} {source_text}object={object} "
        f"index={index} header_index_ok={header_text} name='{name}' "
        f"status={status} reason={reason}{counts_text}"
    )


class ReflectionScannerAnalyzerStrictTests(unittest.TestCase):
    def run_analyzer(
        self,
        lines: list[str],
        *extra_args: str,
        objdump_text: str | None = None,
        binary_text: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            args = [sys.executable, str(ANALYZER), *extra_args]
            if objdump_text is not None:
                objdump_path = Path(temp_dir) / "ShooterGameServer.objdump"
                objdump_path.write_text(objdump_text, encoding="utf-8")
                args.extend(["--objdump-xrefs", str(objdump_path)])
            if binary_text is not None:
                binary_path = Path(temp_dir) / "ShooterGameServer"
                binary_path.write_bytes(binary_text)
                args.extend(["--binary", str(binary_path)])
            args.append(str(log_path))
            return subprocess.run(
                args,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_single_exact_hit_fails_strict(self) -> None:
        result = self.run_analyzer([fname_probe()], "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 1", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 0", result.stdout)
        self.assertIn("status=rejected", result.stdout)
        self.assertIn("single-source evidence only", result.stdout)

    def test_repeated_exact_hit_passes_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 2", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 2", result.stdout)
        self.assertIn("distinct_globals=2", result.stdout)
        self.assertIn("status=research-candidate", result.stdout)
        self.assertIn("repeat-confirmed exact clue match", result.stdout)

    def test_duplicate_exact_hit_fails_strict(self) -> None:
        result = self.run_analyzer([fname_probe(), fname_probe()], "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 2", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 0", result.stdout)
        self.assertIn("table_seen=2", result.stdout)

    def test_repeated_exact_hit_by_distinct_target_passes_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(target="ServerChat"),
                fname_probe(target="ClientMessage"),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 2", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 2", result.stdout)
        self.assertIn("distinct_targets=2", result.stdout)

    def test_reject_marker_fails_strict_even_with_repeated_hit(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
                "[LegacyPlugin] discovery enabled in this copied log",
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reject markers:", result.stdout)
        self.assertIn("[LegacyPlugin]", result.stdout)

    def test_bad_counts_fail_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(num_elements=9622),
                fname_probe(num_elements=9622),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName exact candidates: 0", result.stdout)
        self.assertIn("FName repeat-confirmed candidates: 0", result.stdout)
        self.assertIn("no plausible element/chunk count", result.stdout)

    def test_json_summarizes_gname_table_candidates(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
                fname_probe(
                    table="0x7f0000002000",
                    none="None",
                    client_message="ServerChat",
                    server_chat="ClientMessage",
                ),
            ],
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["evidence_pack"]["status"], "research-candidate")
        self.assertEqual(summary["evidence_pack"]["gname_table_candidate_count"], 1)
        tables = {
            item["table"]: item
            for item in summary["gname_table_candidates"]
        }
        self.assertEqual(tables["0x7f0000001000"]["status"], "research-candidate")
        self.assertEqual(tables["0x7f0000001000"]["research_candidate_count"], 2)
        self.assertEqual(tables["0x7f0000002000"]["status"], "rejected")
        self.assertIn("preview mismatch observed", tables["0x7f0000002000"]["reason"])
        gate = summary["evidence_pack"]["promotion_gate"]
        self.assertEqual(gate["gate_type"], "reflectionscanner_evidence_pack_v1")
        self.assertFalse(gate["ready"])
        self.assertEqual(gate["promotable"], {"gnames": False, "gobjects": False})
        blocker_reasons = {blocker["reason"] for blocker in gate["blockers"]}
        self.assertIn("reflectionscanner_research_candidate_only", blocker_reasons)
        self.assertIn("needs_second_isolated_capture_or_static_path", blocker_reasons)
        self.assertIn("gobjects_not_validated_by_reflectionscanner_pack", blocker_reasons)
        self.assertIn("non_actionable_static_xrefs", blocker_reasons)
        self.assertNotIn("no_repeat_confirmed_gnames_candidate", blocker_reasons)

    def test_json_summarizes_fname_rejects(self) -> None:
        result = self.run_analyzer(
            [
                fname_reject(reason="unreadable_chunk_pointer"),
                fname_reject(source_global="0x600008", reason="preview_mismatch"),
                fname_reject(source_global="0x600010", reason="preview_mismatch"),
            ],
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["evidence_pack"]["status"], "inconclusive")
        self.assertEqual(summary["evidence_pack"]["fname_probe_count"], 0)
        self.assertEqual(summary["evidence_pack"]["fname_reject_count"], 3)
        self.assertEqual(
            summary["evidence_pack"]["fname_reject_reason_counts"],
            {"preview_mismatch": 2, "unreadable_chunk_pointer": 1},
        )
        self.assertEqual(summary["fname_rejects"][0]["reason"], "unreadable_chunk_pointer")
        self.assertEqual(summary["fname_rejects"][1]["source_global"], "0x600008")

    def test_json_groups_fname_rejects_by_target_source_and_reason(self) -> None:
        result = self.run_analyzer(
            [
                fname_reject(
                    target="ServerChat",
                    source_global="0x600000",
                    reason="preview_mismatch",
                    matched=1,
                    num_elements=12000,
                ),
                fname_reject(
                    target="ServerChat",
                    source_global="0x600000",
                    table="0x7f0000002000",
                    reason="preview_mismatch",
                    matched=2,
                    num_elements=13000,
                ),
                fname_reject(
                    target="ClientMessage",
                    source_global="0x600008",
                    reason="implausible_num_elements",
                    num_elements=5,
                ),
            ],
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        groups = {
            (item["target"], item["source_global"], item["reason"]): item
            for item in summary["fname_reject_groups"]
        }
        server_chat_group = groups[
            ("ServerChat", "0x600000", "preview_mismatch")
        ]
        self.assertEqual(server_chat_group["count"], 2)
        self.assertEqual(
            server_chat_group["tables"],
            ["0x7f0000001000", "0x7f0000002000"],
        )
        self.assertEqual(server_chat_group["best_matched_clues"], 2)
        self.assertEqual(server_chat_group["best_num_elements"], 13000)
        self.assertEqual(
            groups[
                ("ClientMessage", "0x600008", "implausible_num_elements")
            ]["count"],
            1,
        )

    def test_human_output_reports_fname_reject_groups(self) -> None:
        result = self.run_analyzer(
            [
                fname_reject(reason="preview_mismatch"),
                fname_reject(table="0x7f0000002000", reason="preview_mismatch"),
            ],
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FName reject groups:", result.stdout)
        self.assertIn(
            "target=candidate source_global=0x600000 reason=preview_mismatch "
            "count=2",
            result.stdout,
        )

    def test_fname_rejects_do_not_satisfy_strict(self) -> None:
        result = self.run_analyzer(
            [
                fname_reject(reason="preview_mismatch"),
                fname_reject(source_global="0x600008", reason="preview_mismatch"),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FName probes: 0", result.stdout)
        self.assertIn("FName rejects: 2", result.stdout)
        self.assertIn("preview_mismatch: 2", result.stdout)

    def test_json_summarizes_static_fname_root_probe_and_reject(self) -> None:
        result = self.run_analyzer(
            [
                static_fname_root_probe(),
                static_fname_root_reject(
                    slot="0x5956f38",
                    reason="unreadable_table_header",
                ),
            ],
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        evidence_pack = summary["evidence_pack"]
        self.assertEqual(evidence_pack["status"], "inconclusive")
        self.assertEqual(evidence_pack["static_fname_root_probe_count"], 1)
        self.assertEqual(evidence_pack["static_fname_root_reject_count"], 1)
        self.assertEqual(evidence_pack["static_fname_root_candidate_count"], 1)
        self.assertEqual(
            evidence_pack["static_fname_root_reject_reason_counts"],
            {"unreadable_table_header": 1},
        )
        probe = summary["static_fname_root_probes"][0]
        self.assertEqual(probe["slot"], "0x5956f30")
        self.assertTrue(probe["research_candidate"])
        self.assertTrue(probe["valid_header_indices"])
        self.assertEqual(probe["header_index_ok"], 3)
        self.assertEqual(summary["static_fname_root_rejects"][0]["slot"], "0x5956f38")

    def test_static_fname_root_candidate_fails_strict_but_reports_candidate(self) -> None:
        result = self.run_analyzer([static_fname_root_probe()], "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Static FName root probes: 1", result.stdout)
        self.assertIn("Static FName root candidates: 1", result.stdout)
        self.assertIn("slot=0x5956f30", result.stdout)

    def test_current_static_fname_root_core_shape_fails_strict_but_reports_candidate(self) -> None:
        result = self.run_analyzer(
            [
                static_fname_root_probe(
                    table="0x2ae5c660",
                    num_elements=0x4516E,
                    num_chunks=0x12,
                )
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Static FName root candidates: 1", result.stdout)
        self.assertIn("slot=0x5956f30", result.stdout)
        self.assertIn("elements=282990", result.stdout)
        self.assertIn("chunks=18", result.stdout)

    def test_static_fname_root_bad_counts_fail_strict(self) -> None:
        result = self.run_analyzer(
            [static_fname_root_probe(num_elements=10, num_chunks=0)],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Static FName root probes: 1", result.stdout)
        self.assertIn("Static FName root candidates: 0", result.stdout)
        self.assertIn("weak or rejected static FName root probes:", result.stdout)

    def test_static_fname_root_header_index_failure_fails_strict(self) -> None:
        result = self.run_analyzer(
            [static_fname_root_probe(header_index_ok=2)],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Static FName root candidates: 0", result.stdout)
        self.assertIn("header_index_ok=2/3", result.stdout)

    def test_static_fname_root_rejects_do_not_satisfy_strict(self) -> None:
        result = self.run_analyzer([static_fname_root_reject()], "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Static FName root rejects: 1", result.stdout)
        self.assertIn("Static FName root reject reasons:", result.stdout)
        self.assertIn("null_table: 1", result.stdout)

    def test_json_summarizes_static_fname_root_samples(self) -> None:
        result = self.run_analyzer(
            [
                static_fname_root_sample(target="ServerChat", reason="exact_name"),
                static_fname_root_sample(
                    target="ClientMessage",
                    source_global="0x600000",
                    index=9619,
                    name="ServerChat",
                    status="mismatch",
                    reason="name_mismatch",
                    num_elements=12000,
                    num_chunks=1,
                ),
                static_fname_root_sample(
                    target="Foo",
                    index=42,
                    header_index_ok=False,
                    name="",
                    status="reject",
                    reason="unreadable_entry",
                ),
            ],
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        evidence_pack = summary["evidence_pack"]
        self.assertEqual(evidence_pack["status"], "inconclusive")
        self.assertEqual(evidence_pack["static_fname_root_sample_count"], 3)
        self.assertEqual(
            evidence_pack["static_fname_root_sample_status_counts"],
            {"match": 1, "mismatch": 1, "reject": 1},
        )
        self.assertEqual(
            evidence_pack["static_fname_root_sample_reason_counts"],
            {"exact_name": 1, "name_mismatch": 1, "unreadable_entry": 1},
        )
        self.assertEqual(
            evidence_pack["static_fname_root_sample_target_counts"],
            {"ClientMessage": 1, "Foo": 1, "ServerChat": 1},
        )
        sample = summary["static_fname_root_samples"][2]
        self.assertEqual(sample["target"], "Foo")
        self.assertFalse(sample["header_index_ok"])
        self.assertEqual(
            summary["static_fname_root_samples"][1]["source_global"], "0x600000"
        )
        self.assertEqual(summary["static_fname_root_samples"][1]["num_elements"], 12000)

    def test_human_output_reports_static_fname_root_samples(self) -> None:
        result = self.run_analyzer(
            [
                static_fname_root_sample(target="ServerChat"),
                static_fname_root_sample(
                    target="ClientMessage",
                    status="mismatch",
                    reason="name_mismatch",
                ),
            ],
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Static FName root samples: 2", result.stdout)
        self.assertIn("Static FName root sample summary:", result.stdout)
        self.assertIn("- match: 1", result.stdout)
        self.assertIn("- mismatch: 1", result.stdout)
        self.assertIn("- name_mismatch: 1", result.stdout)
        self.assertIn("target=ClientMessage", result.stdout)

    def test_static_fname_root_samples_do_not_satisfy_strict(self) -> None:
        result = self.run_analyzer(
            [
                static_fname_root_sample(target="ServerChat"),
                static_fname_root_sample(target="ClientMessage", index=9619),
            ],
            "--strict",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Static FName root samples: 2", result.stdout)
        self.assertIn("Static FName root candidates: 0", result.stdout)

    def test_json_annotates_static_xrefs_from_objdump_text(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
            ],
            "--json",
            objdump_text="""
0000000000410000 <.text>:
  410010: 48 89 1d e9 ff 1e 00    mov    %rbx,0x1effe9(%rip)        # 0x600000
  410020: 48 8b 05 e1 ff 1e 00    mov    0x1effe1(%rip),%rax        # 0x600008
  410030: 48 8b 05 d9 ff 1e 00    mov    0x1effd9(%rip),%rax        # 0x600010
""",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(len(summary["static_xrefs"]["0x600000"]), 1)
        self.assertEqual(summary["static_xrefs"]["0x600000"][0]["access"], "store")
        self.assertEqual(len(summary["static_xrefs"]["0x600008"]), 1)
        self.assertEqual(summary["static_xrefs"]["0x600008"][0]["access"], "load")
        self.assertEqual(
            summary["evidence_pack"]["static_xref_access_counts"],
            {"load": 1, "store": 1},
        )
        self.assertNotIn("0x600010", summary["static_xrefs"])
        gate = summary["evidence_pack"]["promotion_gate"]
        self.assertFalse(gate["ready"])
        blocker_reasons = {blocker["reason"] for blocker in gate["blockers"]}
        self.assertIn("needs_second_isolated_capture_or_static_path", blocker_reasons)
        self.assertIn("gobjects_not_validated_by_reflectionscanner_pack", blocker_reasons)
        self.assertNotIn("non_actionable_static_xrefs", blocker_reasons)

    def test_json_promotion_gate_reports_no_repeat_confirmed_gnames_candidate(self) -> None:
        result = self.run_analyzer([fname_probe()], "--json")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        gate = summary["evidence_pack"]["promotion_gate"]
        self.assertFalse(gate["ready"])
        blocker_reasons = {blocker["reason"] for blocker in gate["blockers"]}
        self.assertIn("no_repeat_confirmed_gnames_candidate", blocker_reasons)
        self.assertTrue(
            gate["conditional_blockers"]["no_repeat_confirmed_gnames_candidate"]
        )

    def test_json_promotion_gate_reports_reject_markers_present(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
                "[NativeExecProbe] installed in copied log",
            ],
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        gate = summary["evidence_pack"]["promotion_gate"]
        self.assertFalse(gate["ready"])
        blocker_reasons = {blocker["reason"] for blocker in gate["blockers"]}
        self.assertIn("reject_markers_present", blocker_reasons)
        self.assertEqual(gate["conditional_blockers"]["reject_markers_present"], 1)

    def test_json_classifies_intel_static_xref_access(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
            ],
            "--json",
            objdump_text="""
0000000000410000 <.text>:
  410010: 48 89 1d e9 ff 1e 00    mov    QWORD PTR [rip+0x1effe9],rbx        # 0x600000
  410020: 48 8b 05 e1 ff 1e 00    mov    rax,QWORD PTR [rip+0x1effe1]        # 0x600008
  410028: 48 8d 05 d1 ff 1e 00    lea    rax,[rip+0x1effd1]                 # 0x600008
""",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["static_xrefs"]["0x600000"][0]["access"], "store")
        self.assertEqual(summary["static_xrefs"]["0x600008"][0]["access"], "load")
        self.assertEqual(summary["static_xrefs"]["0x600008"][1]["access"], "address")
        self.assertEqual(
            summary["evidence_pack"]["static_xref_access_counts"],
            {"address": 1, "load": 1, "store": 1},
        )

    def test_human_output_reports_static_xrefs(self) -> None:
        result = self.run_analyzer(
            [fname_probe(source_global="0x600000")],
            objdump_text=(
                "  410010: 48 89 1d e9 ff 1e 00    "
                "mov    %rbx,0x1effe9(%rip)        # 0x600000\n"
            ),
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("static xrefs:", result.stdout)
        self.assertIn("0x600000: 1 reference(s)", result.stdout)
        self.assertIn("0x410010", result.stdout)
        self.assertIn("access=store", result.stdout)

    def test_json_includes_evidence_pack_binary_metadata(self) -> None:
        result = self.run_analyzer(
            [
                fname_probe(source_global="0x600000"),
                fname_probe(source_global="0x600008"),
            ],
            "--json",
            "--obelisk-commit",
            "test-commit",
            binary_text=b"offline-test-binary",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        evidence_pack = summary["evidence_pack"]
        self.assertEqual(evidence_pack["obelisk_commit"], "test-commit")
        self.assertEqual(evidence_pack["binary"]["size_bytes"], 19)
        self.assertEqual(
            evidence_pack["binary"]["sha256"],
            "d936ee81753955ccd696878ea4beb9cf69db467d7c6e5fdc2ffd001c81b641e6",
        )
        gate = evidence_pack["promotion_gate"]
        self.assertFalse(gate["ready"])
        self.assertEqual(gate["scope"], "research_candidate_only")
        self.assertEqual(gate["promotable"], {"gnames": False, "gobjects": False})
        blocker_reasons = {blocker["reason"] for blocker in gate["blockers"]}
        self.assertIn("missing_objdump_xrefs", blocker_reasons)
        self.assertNotIn("missing_binary_metadata", blocker_reasons)


class ReflectionEvidencePackBuilderTests(unittest.TestCase):
    def test_builds_offline_pack_from_copied_log_and_local_elf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            log_path = temp_path / "Obelisk.log"
            output_dir = temp_path / "pack"
            log_path.write_text(
                "[ReflectionScanner] disabled for offline builder test\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(EVIDENCE_PACK_BUILDER),
                    "--binary",
                    sys.executable,
                    "--output-dir",
                    str(output_dir),
                    "--obelisk-commit",
                    "test-commit",
                    str(log_path),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((output_dir / "ShooterGameServer.sha256.txt").is_file())
            self.assertTrue((output_dir / "ShooterGameServer.readelf-header.txt").is_file())
            self.assertTrue((output_dir / "ShooterGameServer.objdump").is_file())
            self.assertTrue((output_dir / "logs" / "Obelisk.log").is_file())

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            analyzer = json.loads(
                (output_dir / "analyzer-evidence.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["binary"]["path"], str(Path(sys.executable).resolve()))
            self.assertEqual(analyzer["evidence_pack"]["obelisk_commit"], "test-commit")
            self.assertEqual(analyzer["evidence_pack"]["status"], "inconclusive")
            self.assertEqual(
                analyzer["evidence_pack"]["logs"],
                [str(output_dir / "logs" / "Obelisk.log")],
            )
            self.assertEqual(
                manifest["promotion_gate"],
                analyzer["evidence_pack"]["promotion_gate"],
            )
            self.assertFalse(manifest["promotion_gate"]["ready"])
            self.assertEqual(
                manifest["promotion_gate"]["promotable"],
                {"gnames": False, "gobjects": False},
            )
            blocker_reasons = {
                blocker["reason"] for blocker in manifest["promotion_gate"]["blockers"]
            }
            self.assertIn("no_repeat_confirmed_gnames_candidate", blocker_reasons)
            self.assertIn("gobjects_not_validated_by_reflectionscanner_pack", blocker_reasons)

    def test_refuses_to_write_under_server_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "Obelisk.log"
            log_path.write_text("offline test\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(EVIDENCE_PACK_BUILDER),
                    "--binary",
                    sys.executable,
                    "--output-dir",
                    "/servidor/ark/obelisk-evidence-test",
                    str(log_path),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("refusing to write evidence artifacts", result.stderr)


if __name__ == "__main__":
    unittest.main()
