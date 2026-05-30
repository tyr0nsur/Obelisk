#!/usr/bin/env python3
"""Tests for the redacted UObject flag-policy report builder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import build_uobject_flag_policy_report as builder
import validate_offline_artifact_gate as gate


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "build_uobject_flag_policy_report.py"
CONVERTER = SCRIPT_DIR / "convert_weak_helper_caller_modes.py"
BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def recompute_artifact_sha256(payload: dict[str, object]) -> str:
    identity = dict(payload["artifact_identity"])
    identity_without_hash = {
        "artifact_kind": identity["artifact_kind"],
        "capture_id": identity["capture_id"],
        "evidence_pack_id": identity["evidence_pack_id"],
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": builder.canonical_policy_report(payload),
    }
    return hashlib.sha256(builder.canonical_json_bytes(material)).hexdigest()


def write_source_provenance(path: Path) -> None:
    path.with_name(path.name + ".provenance.json").write_text(
        json.dumps(
            {
                "schema": "obelisk.offline-artifact-provenance.v1",
                "verified": True,
                "binary_sha256": BINARY_SHA256,
                "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )


def weak_helper_ghidra_fixture() -> str:
    c70_callers = "\n".join(
        f"""
=== caller_1d56c70_{caller} 00{caller[2:]}..00{caller[2:]} ===
value = helper_get_maybe_pending_candidate(ptr,1);
MOV ESI,0x1
CALL 0x01d56c70
TEST RAX,RAX
"""
        for caller in ("83a340", "83a720", "83cde0", "9f80f0", "1d299b0", "1d29a20")
    )
    b60_callers = "\n".join(
        f"""
=== caller_1d56b60_{caller} 00{caller[2:]}..00{caller[2:]} ===
cVar1 = helper_is_stale_like_candidate();
cVar2 = helper_is_stale_like_candidate();
MOV ESI,0x0
MOV EDX,0x1
CALL 0x01d56b60
CMP AL,BL
"""
        for caller in ("2355acc", "2355b5c")
    )
    return f"""
=== helper_is_stale_like_candidate 01d56b60..01d56bf4 ===
decompile_completed=true
if ((flags & 0x100) != 0) return true;
if ((param_2 != 0) && ((flags & 0x4000) != 0)) return true;
if (param_3 != 0) return comparison;
01d56b99: TEST AH,0x40
=== helper_get_maybe_pending_candidate 01d56c70..01d56cf4 ===
decompile_completed=true
if ((flags & 0x100) != 0) return 0;
if ((sil == 0) && ((flags & 0x4000) != 0)) return 0;
{c70_callers}
{b60_callers}
"""


def weak_helper_r2_fixture() -> str:
    c70_windows = "\n".join(
        f"""
=== caller_1d56c70_{caller} ===
mov esi, 0x1
call 0x01d56c70
test rax, rax
"""
        for caller in ("83a340", "83a720", "83cde0", "9f80f0", "1d299b0", "1d29a20")
    )
    b60_windows = "\n".join(
        f"""
=== caller_1d56b60_{caller} ===
mov esi, 0x0
mov edx, 0x1
call 0x01d56b60
cmp al, bl
"""
        for caller in ("2355acc", "2355b5c")
    )
    return f"""
0x01d56b60 test ah, 1
0x01d56b70 test ah, 0x40
0x01d56c70 test ah, 1
0x01d56ce3 test dh, 0x40
{c70_windows}
{b60_windows}
"""


def weak_helper_counts_fixture() -> str:
    return """
0x1d56b60: 4 direct calls
0x1d56c70: 6 direct calls
"""


def weak_helper_address_sha(address: str) -> str:
    return hashlib.sha256(
        f"obelisk.weak-helper-caller-mode:{BINARY_SHA256}:{address}".encode("ascii")
    ).hexdigest()


def weak_helper_report() -> dict[str, object]:
    sources = {}
    for name, tool, version, digest in (
        ("ghidra_stdout", "ghidra", "12.1", "a" * 64),
        ("r2_windows", "radare2", "5.5.0", "b" * 64),
        ("direct_call_counts", "objdump-or-radare2", "5.5.0", "c" * 64),
    ):
        sources[name] = {
            "artifact_sha256": digest,
            "tool": tool,
            "version": version,
            "provenance": {
                "schema": "obelisk.offline-artifact-provenance.v1",
                "verified": True,
                "binary_sha256": BINARY_SHA256,
                "artifact_sha256": digest,
                "sidecar_sha256": "d" * 64,
                "path_redacted": True,
            },
        }
    return {
        "schema": "obelisk.weak-helper-caller-mode-redacted.v1",
        "status": "accepted_internal_static_evidence",
        "binary": {"sha256": BINARY_SHA256, "path_redacted": True},
        "sources": sources,
        "direct_call_coverage": {
            "0x1d56c70": {"expected": 6, "observed": 6},
        },
        "helpers": {
            "0x1d56c70": {
                "flag_rules": [
                    {"mask": "0x100", "result": "null_always"},
                    {"mask": "0x4000", "result": "null_when_sil_zero"},
                ],
            },
        },
        "builder_contract": {"promotion_gate_ready": False},
        "caller_rows": [
            {
                "helper": "0x1d56c70",
                "helper_address_sha256": weak_helper_address_sha("0x1d56c70"),
                "caller_address_sha256": weak_helper_address_sha(caller),
                "mode_args": {"sil": {"source": "const", "value": 1}},
                "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
                "source_count": 2,
                "evidence": ["ghidra", "radare2"],
                "policy_observation": {
                    "0x100": "null_always",
                    "0x4000": "not_rejected_in_observed_sil_1_callers",
                },
                "claim_level": "static_caller_mode_candidate",
                "path_redacted": True,
                "lifecycle_names": "not_promoted",
            }
            for caller in (
                "0x83a340",
                "0x83a720",
                "0x83cde0",
                "0x9f80f0",
                "0x1d299b0",
                "0x1d29a20",
            )
        ],
    }


def window_texts() -> dict[str, str]:
    return {
        "weak_helper_reject_0x100": """
1d56c81: 39 15 7d 4b c0 03     cmp    DWORD PTR [rip+0x3c04b7d],edx        # 595b804 <g_ue4_tm_api@@UE4+0xd814>
1d56ca2: 48 8b 3d 47 4b c0 03  mov    rdi,QWORD PTR [rip+0x3c04b47]        # 595b7f0 <g_ue4_tm_api@@UE4+0xd800>
1d56ccf: 8b 51 08              mov    edx,DWORD PTR [rcx+0x8]
1d56cd4: 81 e7 00 01 00 00     and    edi,0x100
1d56cda: 75 0e                 jne    1d56cea <helper+0x7a>
1d56cea: 31 c0                 xor    eax,eax
1d56cf3: c3                    ret
""",
        "strict_0x4000_behavior": """
1d56cdc: 40 84 f6              test   sil,sil
1d56ce3: f6 c6 40              test   dh,0x40
1d56ce6: 75 0b                 jne    1d56cf3 <helper+0x83>
1d56cf3: c3                    ret
""",
        "gobjects_backed_0x4000_skip": """
29829a4: 39 05 5a 8e fd 02     cmp    DWORD PTR [rip+0x2fd8e5a],eax        # 595b804 <g_ue4_tm_api@@UE4+0xd814>
29829ca: 48 8b 15 1f 8e fd 02  mov    rdx,QWORD PTR [rip+0x2fd8e1f]        # 595b7f0 <g_ue4_tm_api@@UE4+0xd800>
29829d7: 48 03 04 ca           add    rax,QWORD PTR [rdx+rcx*8]
29829e1: 48 8b 18              mov    rbx,QWORD PTR [rax]
29829ed: f6 43 09 40           test   BYTE PTR [rbx+0x9],0x40
29829f1: 0f 85 a9 01 00 00     jne    2982ba0 <caller+0x280>
""",
        "gc_static_0x100_support": """
0000000001d18a90 <gc_window>:
1d18ada: 8b 05 24 2d c4 03     mov    eax,DWORD PTR [rip+0x3c42d24]        # 595b804 <g_ue4_tm_api@@UE4+0xd814>
1d18ae5: 48 8b 0d 04 2d c4 03  mov    rcx,QWORD PTR [rip+0x3c42d04]        # 595b7f0 <g_ue4_tm_api@@UE4+0xd800>
1d18b16: 48 8b 3c f1           mov    rdi,QWORD PTR [rcx+rsi*8]
1d18b33: 48 8b 3f              mov    rdi,QWORD PTR [rdi]
1d18b36: 81 4f 08 00 01 00 00  or     DWORD PTR [rdi+0x8],0x100
""",
    }


class BuildUObjectFlagPolicyReportTests(unittest.TestCase):
    def run_builder(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_converter(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CONVERTER), *args],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def write_inputs(
        self,
        root: Path,
        *,
        windows: dict[str, str] | None = None,
        write_provenance: bool = True,
    ) -> tuple[Path, dict[str, Path]]:
        root.mkdir(parents=True, exist_ok=True)
        weak_helper = root / "weak-helper.json"
        weak_helper.write_text(json.dumps(weak_helper_report()), encoding="utf-8")
        paths: dict[str, Path] = {}
        for name, text in (windows if windows is not None else window_texts()).items():
            path = root / f"{name}.txt"
            path.write_text(text, encoding="utf-8")
            if write_provenance:
                provenance = {
                    "schema": "obelisk.offline-artifact-provenance.v1",
                    "verified": True,
                    "binary_sha256": BINARY_SHA256,
                    "artifact_sha256": sha256_text(text),
                }
                path.with_name(path.name + ".provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
            paths[name] = path
        return weak_helper, paths

    def builder_args(self, weak_helper: Path, windows: dict[str, Path], output: Path) -> list[str]:
        args = [
            "--binary-sha256",
            BINARY_SHA256,
            "--weak-helper-caller-mode",
            str(weak_helper),
            "--output",
            str(output),
        ]
        for name, path in windows.items():
            args.extend(["--window", f"{name}={path}"])
        return args

    def gate_args(self, *, root: Path, protected_root: Path, manifest: Path, mode: str = "consume") -> argparse.Namespace:
        return argparse.Namespace(
            root=root,
            protected_root=protected_root,
            manifest=[manifest],
            artifact=[],
            expected_binary_sha256=BINARY_SHA256,
            mode=mode,
            strict_target_set_coverage=False,
            json=True,
        )

    def test_emits_redacted_static_negative_candidate_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root)
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output))

            self.assertEqual(result.stdout, "")
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema"], "obelisk.uobject-flag-policy-report.v1")
        self.assertEqual(
            set(payload["artifact_identity"]),
            {"artifact_kind", "artifact_sha256", "capture_id", "evidence_pack_id"},
        )
        self.assertEqual(payload["artifact_identity"]["artifact_kind"], "obelisk.uobject-flag-policy-report.v1")
        self.assertEqual(payload["artifact_identity"]["capture_id"], "uobject-flag-policy-capture")
        self.assertEqual(payload["artifact_identity"]["evidence_pack_id"], "uobject-flag-policy-pack")
        self.assertEqual(payload["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(payload))
        self.assertEqual(payload["evidence_kind"], "static_negative_equivalent_candidate")
        self.assertIs(payload["promotion_ready"], False)
        self.assertIs(payload["post_callback_resource_handle_ready"], False)
        self.assertEqual(payload["status"], "candidate_blocked")
        self.assertEqual(len(payload["windows_summary"]["observed"]), 4)
        self.assertEqual(payload["weak_helper_caller_mode"]["direct_call_coverage"]["weak_helper_flag_policy_candidate"], {"expected": 6, "observed": 6})
        self.assertEqual(payload["weak_helper_caller_mode"]["caller_rows_summary"]["helper"], "weak_helper_flag_policy_candidate")
        self.assertEqual(payload["weak_helper_caller_mode"]["caller_rows_summary"]["row_count"], 6)
        self.assertEqual(payload["weak_helper_caller_mode"]["caller_rows_summary"]["unique_caller_hash_count"], 6)
        self.assertRegex(payload["weak_helper_caller_mode"]["caller_rows_summary"]["caller_rows_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            payload["weak_helper_caller_mode"]["caller_rows_summary"]["policy_observation"],
            {"0x100": "null_always", "0x4000": "not_rejected_in_observed_sil_1_callers"},
        )
        self.assertEqual(
            payload["weak_helper_caller_mode"]["caller_rows_source"]["source_artifact_sha256"],
            payload["weak_helper_caller_mode"]["artifact_sha256"],
        )
        self.assertEqual(
            payload["weak_helper_caller_mode"]["caller_rows_source"]["caller_rows_sha256"],
            payload["weak_helper_caller_mode"]["caller_rows_summary"]["caller_rows_sha256"],
        )
        self.assertEqual(payload["weak_helper_caller_mode"]["caller_rows_summary"]["lifecycle_names"], "not_promoted")
        for window in payload["windows_summary"]["observed"]:
            self.assertEqual(
                set(window["matched_patterns"]),
                gate.REQUIRED_UOBJECT_FLAG_POLICY_WINDOW_PATTERNS[window["name"]],
            )
            self.assertEqual(window["provenance"]["binary_sha256"], BINARY_SHA256)
            self.assertEqual(window["provenance"]["artifact_sha256"], window["artifact_sha256"])
            self.assertRegex(window["provenance"]["sidecar_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("does_not_promote_resourcehandle", payload["non_claims"])
        self.assertIn("no_rejected_runtime_object_samples", payload["remaining_blockers"])
        self.assertEqual(
            payload["internal_revalidation_contract"],
            {
                "name": "InternalUObjectRevalidationCandidate",
                "lifetime": "frame_local_only",
                "post_callback_lookup": "rejected",
                "flag_policy": {
                    "0x100": "reject",
                    "0x4000": "reject_by_default",
                },
                "output": "copied_bool_or_obelisk_owned_data_only",
                "public_api": "not_promoted",
            },
        )
        self.assertEqual(payload["redaction"]["addresses"], "redacted")
        self.assertNotIn(str(root), json.dumps(payload))
        self.assertNotIn("pending-kill", json.dumps(payload).lower())
        for address in ("0x83a340", "0x83a720", "0x83cde0", "0x9f80f0", "0x1d299b0", "0x1d29a20", "0x1d56c70"):
            self.assertNotIn(address, json.dumps(payload))

    def test_artifact_identity_is_stable_across_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root / "inputs")
            args = self.builder_args(weak_helper, windows, root / "report-a.json")
            args.extend(
                [
                    "--artifact-kind",
                    "obelisk.uobject-flag-policy-report.v1",
                    "--capture-id",
                    "capture.alpha",
                    "--evidence-pack-id",
                    "pack.alpha",
                ]
            )
            self.run_builder(*args)
            args_b = self.builder_args(weak_helper, windows, root / "nested" / "report-b.json")
            args_b.extend(
                [
                    "--artifact-kind",
                    "obelisk.uobject-flag-policy-report.v1",
                    "--capture-id",
                    "capture.alpha",
                    "--evidence-pack-id",
                    "pack.alpha",
                ]
            )
            self.run_builder(*args_b)
            payload_a = json.loads((root / "report-a.json").read_text(encoding="utf-8"))
            payload_b = json.loads((root / "nested" / "report-b.json").read_text(encoding="utf-8"))

        self.assertEqual(payload_a["artifact_identity"], payload_b["artifact_identity"])
        self.assertEqual(payload_a["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(payload_a))
        self.assertEqual(payload_b["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(payload_b))

    def test_artifact_identity_changes_when_window_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root / "inputs-a")
            self.run_builder(*self.builder_args(weak_helper, windows, root / "report-a.json"))
            texts = window_texts()
            texts["weak_helper_reject_0x100"] = texts["weak_helper_reject_0x100"].replace(
                "1d56cf3: c3                    ret",
                "1d56cf4: c3                    ret",
            )
            weak_helper_b, windows_b = self.write_inputs(root / "inputs-b", windows=texts)
            self.run_builder(*self.builder_args(weak_helper_b, windows_b, root / "report-b.json"))
            payload_a = json.loads((root / "report-a.json").read_text(encoding="utf-8"))
            payload_b = json.loads((root / "report-b.json").read_text(encoding="utf-8"))

        self.assertNotEqual(
            payload_a["artifact_identity"]["artifact_sha256"],
            payload_b["artifact_identity"]["artifact_sha256"],
        )

    def test_cli_rejects_unsafe_artifact_identity_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root)
            result = self.run_builder(
                *self.builder_args(weak_helper, windows, root / "report.json"),
                "--capture-id",
                "../bad",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--capture-id must not contain '..'", result.stderr)

    def test_converter_builder_output_is_consumable_candidate_and_promote_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            protected = Path(temp_dir) / "server"
            workspace = protected / "workspace-offline"
            source_root = workspace / "sources"
            source_root.mkdir(parents=True)
            ghidra = source_root / "ghidra.txt"
            r2 = source_root / "r2.txt"
            counts = source_root / "counts.txt"
            ghidra.write_text(weak_helper_ghidra_fixture(), encoding="utf-8")
            r2.write_text(weak_helper_r2_fixture(), encoding="utf-8")
            counts.write_text(weak_helper_counts_fixture(), encoding="utf-8")
            for path in (ghidra, r2, counts):
                write_source_provenance(path)

            weak_helper = workspace / "weak-helper-caller-mode.json"
            self.run_converter(
                "--ghidra-stdout",
                str(ghidra),
                "--r2-windows",
                str(r2),
                "--direct-call-counts",
                str(counts),
                "--binary-sha256",
                BINARY_SHA256,
                "--output",
                str(weak_helper),
            )
            _, windows = self.write_inputs(workspace / "windows")
            report = workspace / "uobject-flag-policy.redacted.json"
            self.run_builder(*self.builder_args(weak_helper, windows, report))

            consume = gate.build_result(
                self.gate_args(root=workspace, protected_root=protected, manifest=report)
            )
            promote = gate.build_result(
                self.gate_args(root=workspace, protected_root=protected, manifest=report, mode="promote")
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual("accepted", consume["status"])
        self.assertEqual([], consume["blockers"])
        self.assertEqual("blocked", promote["status"])
        self.assertIn(
            "promote_mode_uobject_flag_policy_candidate_only",
            {blocker["reason"] for blocker in promote["blockers"]},
        )
        self.assertEqual(payload["status"], "candidate_blocked")
        self.assertIs(payload["promotion_ready"], False)
        self.assertIs(payload["post_callback_resource_handle_ready"], False)
        self.assertIn("does_not_promote_resourcehandle", payload["non_claims"])
        self.assertIn("public_resourcehandle_policy_missing", payload["remaining_blockers"])
        self.assertEqual(
            payload["weak_helper_caller_mode"]["caller_rows_source"]["source_artifact_sha256"],
            payload["weak_helper_caller_mode"]["artifact_sha256"],
        )
        self.assertNotIn("0x1d56c70", json.dumps(payload))

    def test_fails_closed_when_required_window_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            texts = window_texts()
            del texts["gc_static_0x100_support"]
            weak_helper, windows = self.write_inputs(root, windows=texts)
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required --window entries", result.stderr)
        self.assertIn("gc_static_0x100_support", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_window_lacks_required_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            texts = window_texts()
            texts["gobjects_backed_0x4000_skip"] = "test BYTE PTR [object+0x9],0x40 ; skip\n"
            weak_helper, windows = self.write_inputs(root, windows=texts)
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("window evidence incomplete", result.stderr)
        self.assertIn("gobjects_backed_0x4000_skip:gobjects_count_ref", result.stderr)
        self.assertIn("fuobjectitem_load", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_on_disconnected_token_soup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            texts = window_texts()
            texts["weak_helper_reject_0x100"] = """
prose copies every regex token: # 595b804 and # 595b7f0.
it also says mov edx,DWORD PTR [rcx+0x8], and edi,0x100,
then jne 1d56cea followed by xor eax,eax and ret,
but it is not a connected objdump instruction window.
"""
            weak_helper, windows = self.write_inputs(root, windows=texts)
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("window evidence incomplete", result.stderr)
        self.assertIn("weak_helper_reject_0x100", result.stderr)
        self.assertIn("non_objdump_text_lines", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_weak_helper_rule_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, windows = self.write_inputs(root)
            weak_helper = root / "weak-helper-invalid.json"
            payload = weak_helper_report()
            payload["helpers"] = {"0x1d56c70": {"flag_rules": [{"mask": "0x100", "result": "null_always"}]}}
            weak_helper.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_weak_helper_0x4000_mode_rule", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_weak_helper_sources_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, windows = self.write_inputs(root)
            weak_helper = root / "weak-helper-invalid.json"
            payload = weak_helper_report()
            del payload["sources"]
            weak_helper.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("weak_helper_sources_missing_or_unexpected", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_weak_helper_status_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, windows = self.write_inputs(root)
            weak_helper = root / "weak-helper-invalid.json"
            payload = weak_helper_report()
            payload["status"] = "draft"
            weak_helper.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("weak_helper_status_not_accepted_internal_static_evidence", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_caller_rows_are_incoherent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, windows = self.write_inputs(root)
            weak_helper = root / "weak-helper-invalid.json"
            payload = weak_helper_report()
            payload["caller_rows"][0]["caller_address_sha256"] = payload["caller_rows"][1]["caller_address_sha256"]
            weak_helper.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("weak_helper_caller_rows_unique_count_mismatch", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_caller_rows_carry_extra_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, windows = self.write_inputs(root)
            weak_helper = root / "weak-helper-invalid.json"
            payload = weak_helper_report()
            payload["caller_rows"][0]["source_path"] = "/tmp/raw-ghidra.txt"
            weak_helper.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("weak_helper_caller_row_unexpected_fields", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_on_legacy_redacted_weak_helper_aggregate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, windows = self.write_inputs(root)
            weak_helper = root / "weak-helper-legacy.json"
            payload = weak_helper_report()
            del payload["caller_rows"]
            payload["callers"] = [
                {
                    "helper": "0x1d56c70",
                    "caller_window_count": 6,
                    "mode_args": {"sil": {"source": "const", "value": 1}},
                    "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
                },
                {
                    "helper": "0x1d56b60",
                    "caller_window_count": 2,
                    "mode_args": {"sil": {"source": "const", "value": 0}, "dl": {"source": "const", "value": 1}},
                    "return_use": {"kind": "pairwise_boolean_comparison"},
                },
            ]
            for source in payload["sources"].values():
                source.pop("provenance")
            weak_helper.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("weak_helper_source_provenance_missing:direct_call_counts", result.stderr)
        self.assertIn("weak_helper_caller_rows_count_mismatch", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_on_unknown_window_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root)
            unknown = root / "unknown.txt"
            text = next(iter(window_texts().values()))
            unknown.write_text(text, encoding="utf-8")
            unknown.with_name(unknown.name + ".provenance.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.offline-artifact-provenance.v1",
                        "verified": True,
                        "binary_sha256": BINARY_SHA256,
                        "artifact_sha256": sha256_text(text),
                    }
                ),
                encoding="utf-8",
            )
            windows["annotated_0x100"] = unknown
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown --window entries", result.stderr)
        self.assertIn("annotated_0x100", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root, write_provenance=False)
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--window weak_helper_reject_0x100 provenance does not exist", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root)
            first_path = windows["weak_helper_reject_0x100"]
            provenance_path = first_path.with_name(first_path.name + ".provenance.json")
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
            payload["verified"] = False
            provenance_path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provenance_not_verified", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_hashes_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root)
            first_path = windows["weak_helper_reject_0x100"]
            provenance_path = first_path.with_name(first_path.name + ".provenance.json")
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
            payload["binary_sha256"] = "0" * 64
            payload["artifact_sha256"] = "1" * 64
            provenance_path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provenance_binary_sha256_mismatch", result.stderr)
        self.assertIn("provenance_artifact_sha256_mismatch", result.stderr)
        self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_contains_relative_protected_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root)
            first_path = windows["weak_helper_reject_0x100"]
            provenance_path = first_path.with_name(first_path.name + ".provenance.json")
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
            payload["source_path"] = os.path.relpath(
                "/servidor/ark/obelisk/dumps/raw-window.txt",
                start=provenance_path.parent,
            )
            provenance_path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "report.json"
            result = self.run_builder(*self.builder_args(weak_helper, windows, output), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provenance_protected_path_field:$.source_path", result.stderr)
        self.assertFalse(output.exists())

    def test_accepts_hyphenated_window_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            weak_helper, windows = self.write_inputs(root)
            output = root / "report.json"
            args = [
                "--binary-sha256",
                BINARY_SHA256,
                "--weak-helper-caller-mode",
                str(weak_helper),
                "--output",
                str(output),
                "--window",
                f"weak-helper-reject-0x100-window={windows['weak_helper_reject_0x100']}",
                "--window",
                f"strict-0x4000-behavior-window={windows['strict_0x4000_behavior']}",
                "--window",
                f"gobjects-backed-0x4000-skip-window={windows['gobjects_backed_0x4000_skip']}",
                "--window",
                f"gc-static-0x100-support-window={windows['gc_static_0x100_support']}",
            ]
            self.run_builder(*args)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(payload["windows_summary"]["all_required_present"])


if __name__ == "__main__":
    unittest.main()
