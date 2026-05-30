#!/usr/bin/env python3
"""Offline tests for build_static_global_promotion_evidence.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_static_global_promotion_evidence  # noqa: E402

SCRIPT = ["python3", "scripts/build_static_global_promotion_evidence.py"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def static_artifact_kind(path: Path) -> str:
    if "program" in path.name:
        return "readelf_programs"
    if "section" in path.name:
        return "readelf_sections"
    return "objdump"


def write_static_artifact_provenance(path: Path, binary: Path) -> None:
    artifact_kind = static_artifact_kind(path)
    provenance = {
        "schema": build_static_global_promotion_evidence.STATIC_ARTIFACT_PROVENANCE_SCHEMA,
        "verified": True,
        "artifact_kind": artifact_kind,
        "producer": build_static_global_promotion_evidence.PROVENANCE_PRODUCER,
        "binary_sha256": sha256_file(binary),
        "artifact_sha256": sha256_file(path),
        "command": f"offline fixture generated {path.name}",
        "tool": build_static_global_promotion_evidence.EXPECTED_ARTIFACT_TOOLS[artifact_kind],
    }
    Path(f"{path}.provenance.json").write_text(json.dumps(provenance), encoding="utf-8")


def recompute_artifact_sha256(payload: dict[str, object]) -> str:
    identity = dict(payload["artifact_identity"])
    identity_without_hash = {
        "artifact_kind": identity["artifact_kind"],
        "capture_id": identity["capture_id"],
        "evidence_pack_id": identity["evidence_pack_id"],
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": build_static_global_promotion_evidence.canonical_static_report(payload),
    }
    return hashlib.sha256(build_static_global_promotion_evidence.canonical_json_bytes(material)).hexdigest()


def write_minimal_static_inputs(root: Path) -> tuple[Path, Path, Path, Path]:
    binary = root / "ShooterGameServer"
    binary.write_bytes(b"static evidence binary")
    programs = root / "programs.txt"
    programs.write_text(
        "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
        "0x3000000 0x3000000 R E 0x200000\n"
        "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
        "0x100000 0x100000 RW  0x200000\n",
        encoding="utf-8",
    )
    sections = root / "sections.txt"
    sections.write_text(
        "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
        "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
        encoding="utf-8",
    )
    objdump = root / "objdump.txt"
    objdump.write_text(
        """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  40101e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  401025: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
        encoding="utf-8",
    )
    return binary, programs, sections, objdump


def write_redacted_field_window_evidence(
    path: Path,
    binary_sha256: str,
    *,
    candidate_address: int = 0x595B7E0,
) -> None:
    payload = {
        "schema": build_static_global_promotion_evidence.FUOBJECTARRAY_FIELD_WINDOW_SCHEMA,
        "status": "accepted_internal_static_evidence",
        "binary": {
            "sha256": binary_sha256,
            "path_redacted": True,
        },
        "candidate": {
            "label": "gobjects",
            "kind": "gobjects",
            "address_redacted": True,
            "address_sha256": build_static_global_promotion_evidence.candidate_address_sha256(
                binary_sha256,
                candidate_address,
            ),
        },
        "sources": {
            "ghidra_stdout": {"artifact_sha256": "a" * 64, "tool": "ghidra", "version": "12.1"},
            "r2_windows": {"artifact_sha256": "b" * 64, "tool": "radare2", "version": "5.5.0"},
        },
        "fuobjectarray_window": {
            "same_base_flow": {
                "proven": True,
                "evidence": [
                    "candidate_passed_to_constructor_helper",
                    "same_candidate_registered_with_finalizer",
                    "constructor_writes_relative_fields",
                    "serial_accessors_use_same_field_family",
                ],
            },
            "required_fields": {
                "root": {"present": True, "basis": "candidate_base"},
                "chunks": {"present": True, "relative_offset": "base+0x10"},
                "count": {"present": True, "relative_offset": "base+0x24"},
                "serial": {"present": True, "relative_offset": "base+0x58"},
            },
        },
        "builder_contract": {
            "candidate_static_contract_blocker_to_clear": "missing_gobjects_coherent_field_window",
            "promotion_gate_ready": False,
            "remaining_blockers": ["static_only_evidence"],
            "consumption_scope": "internal_static_research_only",
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class StaticGlobalPromotionEvidenceTests(unittest.TestCase):
    def run_script(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*SCRIPT, *args],
            cwd=REPO_ROOT,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_xref_semantic_roles_from_clear_function_patterns(self) -> None:
        cases = (
            ("BootstrapGObjects", "bootstrap"),
            ("InitObjects", "init"),
            ("ResetObjects", "reset"),
            ("DestroyObjects", "destructor"),
            ("LookupObjects", "lookup"),
        )
        for function_label, expected_role in cases:
            with self.subTest(function_label=function_label):
                semantic = build_static_global_promotion_evidence.classify_xref_semantics(
                    {
                        "function_label": function_label,
                        "target_label": "gobjects.root",
                        "instruction": "mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0",
                    }
                )

                self.assertEqual(semantic["role"], expected_role)
                self.assertEqual(semantic["context"], "gobjects_field")
                self.assertEqual(semantic["field"], "root")

    def test_builds_fail_closed_static_manifest_with_rip_relative_xref(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  40101e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  401025: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
  40102c: bf e0 b7 95 05        mov    edi,0x595b7e0
""",
                encoding="utf-8",
            )
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "obelisk.static-global-promotion-evidence.v1")
            self.assertIn("generated_at_utc", payload)
            self.assertIn("obelisk_commit", payload)
            self.assertEqual(manifest["binary"]["sha256"], payload["binary"]["sha256"])
            self.assertEqual(manifest["artifact_identity"], payload["artifact_identity"])
            self.assertEqual(
                payload["artifact_identity"],
                {
                    "artifact_kind": "obelisk.static-global-promotion-evidence.v1",
                    "capture_id": build_static_global_promotion_evidence.DEFAULT_CAPTURE_ID,
                    "evidence_pack_id": build_static_global_promotion_evidence.DEFAULT_EVIDENCE_PACK_ID,
                    "artifact_sha256": recompute_artifact_sha256(payload),
                },
            )
            self.assertEqual(payload["static_xrefs_sha256"], sha256_file(output_dir / "static-global-xrefs.json"))
            self.assertEqual(
                payload["commands"]["readelf_programs"]["source_sha256"],
                payload["commands"]["readelf_programs"]["copied_sha256"],
            )
            self.assertEqual(
                payload["commands"]["readelf_sections"]["source_sha256"],
                payload["commands"]["readelf_sections"]["copied_sha256"],
            )
            self.assertEqual(
                payload["commands"]["objdump"]["source_sha256"],
                payload["commands"]["objdump"]["copied_sha256"],
            )
            self.assertFalse(payload["promotion_gate"]["ready"])
            self.assertIn("static_only_evidence", {item["reason"] for item in payload["promotion_gate"]["blockers"]})
            self.assertNotIn(
                "unverified_static_artifact_provenance",
                {item["reason"] for item in payload["promotion_gate"]["blockers"]},
            )
            self.assertTrue(payload["commands"]["readelf_programs"]["provenance"]["verified"])
            self.assertTrue(payload["commands"]["readelf_sections"]["provenance"]["verified"])
            self.assertTrue(payload["commands"]["objdump"]["provenance"]["verified"])
            for command_name, artifact_name in (
                ("readelf_programs", "ShooterGameServer.readelf-programs.txt"),
                ("readelf_sections", "ShooterGameServer.readelf-sections.txt"),
                ("objdump", "ShooterGameServer.objdump"),
            ):
                with self.subTest(command_name=command_name):
                    provenance_path = output_dir / f"{artifact_name}.provenance.json"
                    self.assertEqual(payload["commands"][command_name]["output_provenance"], str(provenance_path))
                    output_provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
                    self.assertEqual(output_provenance["binary_sha256"], payload["binary"]["sha256"])
                    self.assertEqual(output_provenance["artifact_sha256"], payload["commands"][command_name]["copied_sha256"])
                    self.assertEqual(output_provenance["source_artifact_sha256"], payload["commands"][command_name]["source_sha256"])
                    self.assertIs(output_provenance["verified"], True)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["label"], "gobjects")
            self.assertEqual(candidate["kind"], "gobjects")
            self.assertEqual(candidate["segment"]["virtual_address"], "0x5900000")
            self.assertEqual(candidate["section"]["name"], ".data")
            self.assertEqual(candidate["xref_count"], 5)
            self.assertEqual(candidate["rip_relative_xref_count"], 4)
            self.assertEqual(candidate["immediate_xref_count"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.root"], 2)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.chunks"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.count"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.serial"], 1)
            self.assertEqual(candidate["target_code_backed_xref_counts"]["gobjects.root"], 1)
            self.assertEqual(candidate["target_code_backed_xref_counts"]["gobjects.chunks"], 1)
            self.assertEqual(candidate["target_code_backed_xref_counts"]["gobjects.count"], 1)
            self.assertEqual(candidate["target_code_backed_xref_counts"]["gobjects.serial"], 1)
            self.assertTrue(candidate["static_contract"]["satisfied"])
            self.assertEqual(candidate["semantic_summary"]["role_counts"], {"lookup": 5})
            self.assertEqual(candidate["semantic_summary"]["contexts"], ["gobjects_field"])
            self.assertEqual(
                candidate["semantic_summary"]["fields"],
                ["chunks", "count", "root", "serial"],
            )
            coherent_window = candidate["static_contract"]["coherent_window"]
            self.assertEqual(coherent_window["role"], "lookup")
            self.assertEqual(coherent_window["role_counts"], {"lookup": 4})
            self.assertEqual(coherent_window["context"], "gobjects_required_field_window")
            self.assertEqual(coherent_window["contexts"], ["gobjects_field"])
            self.assertEqual(coherent_window["fields"], ["root", "chunks", "count", "serial"])
            xrefs = json.loads((output_dir / "static-global-xrefs.json").read_text(encoding="utf-8"))
            root_xref = xrefs["xrefs"]["0x595b7e0"][0]
            self.assertEqual(root_xref["instruction_segment"]["virtual_address"], "0x400000")
            self.assertEqual(root_xref["instruction_segment"]["flags"], "RE")
            self.assertEqual(root_xref["instruction_section"]["name"], ".text")
            self.assertEqual(root_xref["instruction_section"]["flags"], "AX")
            self.assertTrue(root_xref["target_is_rip_relative"])
            self.assertEqual(root_xref["match_kinds"], ["comment_target", "immediate_literal"])
            self.assertEqual(root_xref["semantic"]["role"], "lookup")
            self.assertEqual(root_xref["semantic"]["context"], "gobjects_field")

    def test_copied_static_artifacts_without_provenance_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  40101e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  401025: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            self.assertTrue(payload["candidates"][0]["static_contract"]["satisfied"])
            provenance_blockers = [
                item
                for item in payload["promotion_gate"]["blockers"]
                if item["reason"] == "unverified_static_artifact_provenance"
            ]
            self.assertEqual(
                {item["artifact"] for item in provenance_blockers},
                {"readelf_programs", "readelf_sections", "objdump"},
            )
            self.assertEqual(
                {item["detail"] for item in provenance_blockers},
                {"missing_static_artifact_provenance"},
            )
            output_provenance = json.loads(
                (root / "pack" / "ShooterGameServer.objdump.provenance.json").read_text(encoding="utf-8")
            )
            self.assertIs(output_provenance["verified"], False)
            self.assertEqual(
                output_provenance["source_provenance"]["reason"],
                "missing_static_artifact_provenance",
            )

    def test_builder_outputs_can_be_reused_as_verified_static_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  40101e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  401025: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)

            first_pack = root / "first-pack"
            self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(first_pack),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )
            second = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "second-pack"),
                "--readelf-programs",
                str(first_pack / "ShooterGameServer.readelf-programs.txt"),
                "--readelf-sections",
                str(first_pack / "ShooterGameServer.readelf-sections.txt"),
                "--objdump",
                str(first_pack / "ShooterGameServer.objdump"),
                "--json",
            )

            payload = json.loads(second.stdout)
            self.assertNotIn(
                "unverified_static_artifact_provenance",
                {item["reason"] for item in payload["promotion_gate"]["blockers"]},
            )
            self.assertTrue(payload["commands"]["readelf_programs"]["provenance"]["verified"])
            self.assertTrue(payload["commands"]["readelf_sections"]["provenance"]["verified"])
            self.assertTrue(payload["commands"]["objdump"]["provenance"]["verified"])
            self.assertTrue(payload["candidates"][0]["static_contract"]["satisfied"])

    def test_artifact_identity_is_stable_across_output_paths_and_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)

            base_args = [
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--capture-id",
                "static-capture.alpha",
                "--evidence-pack-id",
                "static-pack.alpha",
                "--json",
            ]
            first = self.run_script(*base_args, "--output-dir", str(root / "pack-a"))
            second = self.run_script(*base_args, "--output-dir", str(root / "nested" / "pack-b"))

            payload_a = json.loads(first.stdout)
            payload_b = json.loads(second.stdout)

        self.assertNotEqual(payload_a["artifacts"]["static_xrefs"], payload_b["artifacts"]["static_xrefs"])
        self.assertEqual(payload_a["artifact_identity"], payload_b["artifact_identity"])
        self.assertEqual(payload_a["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(payload_a))
        self.assertEqual(payload_b["artifact_identity"]["artifact_sha256"], recompute_artifact_sha256(payload_b))

    def test_artifact_identity_changes_when_candidate_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)
            common = [
                "--binary",
                str(binary),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--capture-id",
                "static-capture.alpha",
                "--evidence-pack-id",
                "static-pack.alpha",
                "--json",
            ]
            first = self.run_script(*common, "--candidate", "gobjects=0x595b7e0", "--output-dir", str(root / "pack-a"))
            second = self.run_script(*common, "--candidate", "gobjects=0x595b7f0", "--output-dir", str(root / "pack-b"))

            payload_a = json.loads(first.stdout)
            payload_b = json.loads(second.stdout)

        self.assertNotEqual(
            payload_a["artifact_identity"]["artifact_sha256"],
            payload_b["artifact_identity"]["artifact_sha256"],
        )

    def test_cli_rejects_unsafe_artifact_identity_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--capture-id",
                "../bad",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--capture-id must not contain '..'", result.stderr)

    def test_cli_strict_artifact_identity_rejects_default_ids(self) -> None:
        for flag, explicit_args, expected in (
            (
                "--capture-id",
                ["--evidence-pack-id", "static-pack.alpha"],
                "--strict-artifact-identity requires explicit --capture-id",
            ),
            (
                "--evidence-pack-id",
                ["--capture-id", "static-capture.alpha"],
                "--strict-artifact-identity requires explicit --evidence-pack-id",
            ),
        ):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                binary, programs, sections, objdump = write_minimal_static_inputs(root)
                result = self.run_script(
                    "--binary",
                    str(binary),
                    "--candidate",
                    "gobjects=0x595b7e0",
                    "--output-dir",
                    str(root / "pack"),
                    "--readelf-programs",
                    str(programs),
                    "--readelf-sections",
                    str(sections),
                    "--objdump",
                    str(objdump),
                    *explicit_args,
                    "--strict-artifact-identity",
                    check=False,
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected, result.stderr)
            self.assertIn("placeholder artifact identity is not valid reusable evidence", result.stderr)

    def test_cli_strict_artifact_identity_rejects_placeholder_prefixes(self) -> None:
        for flag, value, expected in (
            ("--capture-id", "unspecified-capture", "--strict-artifact-identity requires explicit --capture-id"),
            (
                "--capture-id",
                "static-global-default-capture-old",
                "--strict-artifact-identity requires explicit --capture-id",
            ),
            (
                "--evidence-pack-id",
                "unspecified-evidence-pack",
                "--strict-artifact-identity requires explicit --evidence-pack-id",
            ),
            (
                "--evidence-pack-id",
                "static-global-default-pack-old",
                "--strict-artifact-identity requires explicit --evidence-pack-id",
            ),
        ):
            with self.subTest(flag=flag, value=value), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                binary, programs, sections, objdump = write_minimal_static_inputs(root)
                result = self.run_script(
                    "--binary",
                    str(binary),
                    "--candidate",
                    "gobjects=0x595b7e0",
                    "--output-dir",
                    str(root / "pack"),
                    "--readelf-programs",
                    str(programs),
                    "--readelf-sections",
                    str(sections),
                    "--objdump",
                    str(objdump),
                    "--capture-id",
                    "static-capture.alpha",
                    "--evidence-pack-id",
                    "static-pack.alpha",
                    flag,
                    value,
                    "--strict-artifact-identity",
                    check=False,
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected, result.stderr)
            self.assertIn("placeholder artifact identity is not valid reusable evidence", result.stderr)

    def test_cli_strict_artifact_identity_allows_explicit_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--capture-id",
                "static-capture.alpha",
                "--evidence-pack-id",
                "static-pack.alpha",
                "--strict-artifact-identity",
                "--json",
            )

            payload = json.loads(result.stdout)

        self.assertEqual(payload["artifact_identity"]["capture_id"], "static-capture.alpha")
        self.assertEqual(payload["artifact_identity"]["evidence_pack_id"], "static-pack.alpha")

    def test_copied_static_artifact_provenance_requires_verified_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
""",
                encoding="utf-8",
            )
            for artifact in (programs, sections, objdump):
                artifact_kind = static_artifact_kind(artifact)
                provenance = {
                    "schema": build_static_global_promotion_evidence.STATIC_ARTIFACT_PROVENANCE_SCHEMA,
                    "artifact_kind": artifact_kind,
                    "producer": build_static_global_promotion_evidence.PROVENANCE_PRODUCER,
                    "binary_sha256": sha256_file(binary),
                    "artifact_sha256": sha256_file(artifact),
                    "tool": build_static_global_promotion_evidence.EXPECTED_ARTIFACT_TOOLS[artifact_kind],
                }
                Path(f"{artifact}.provenance.json").write_text(json.dumps(provenance), encoding="utf-8")

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            blockers = [
                item
                for item in payload["promotion_gate"]["blockers"]
                if item["reason"] == "unverified_static_artifact_provenance"
            ]
            self.assertEqual(
                {item["artifact"] for item in blockers},
                {"readelf_programs", "readelf_sections", "objdump"},
            )
            self.assertEqual({item["detail"] for item in blockers}, {"static_artifact_provenance_not_verified"})

    def test_copied_static_artifact_provenance_rejects_binary_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            other_binary = root / "OtherServer"
            other_binary.write_bytes(b"different binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
""",
                encoding="utf-8",
            )
            write_static_artifact_provenance(programs, other_binary)
            write_static_artifact_provenance(sections, binary)
            write_static_artifact_provenance(objdump, binary)

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            blockers = [
                item
                for item in payload["promotion_gate"]["blockers"]
                if item["reason"] == "unverified_static_artifact_provenance"
            ]
            self.assertEqual(len(blockers), 1)
            self.assertEqual(blockers[0]["artifact"], "readelf_programs")
            self.assertEqual(blockers[0]["detail"], "static_artifact_binary_sha256_mismatch")

    def test_copied_static_artifact_provenance_non_object_is_structured_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)
            Path(f"{objdump}.provenance.json").write_text("[]", encoding="utf-8")

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            blockers = [
                item
                for item in payload["promotion_gate"]["blockers"]
                if item["reason"] == "unverified_static_artifact_provenance"
            ]
            self.assertEqual(len(blockers), 1)
            self.assertEqual(blockers[0]["artifact"], "objdump")
            self.assertEqual(blockers[0]["detail"], "static_artifact_provenance_not_object")
            self.assertEqual(payload["commands"]["objdump"]["provenance"]["recorded_type"], "list")

    def test_copied_static_artifact_provenance_requires_schema_kind_and_producer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)
            legacy_hash_only = {
                "verified": True,
                "binary_sha256": sha256_file(binary),
                "artifact_sha256": sha256_file(objdump),
            }
            Path(f"{objdump}.provenance.json").write_text(json.dumps(legacy_hash_only), encoding="utf-8")

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            blockers = [
                item
                for item in payload["promotion_gate"]["blockers"]
                if item["reason"] == "unverified_static_artifact_provenance"
            ]
            self.assertEqual(len(blockers), 1)
            self.assertEqual(blockers[0]["artifact"], "objdump")
            self.assertEqual(blockers[0]["detail"], "static_artifact_provenance_schema_mismatch")

    def test_copied_static_artifact_provenance_rejects_recursive_protected_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)
            protected_link = root / "protected-source-link"
            protected_link.symlink_to("/servidor/ark/copied.objdump")
            objdump_provenance = json.loads(Path(f"{objdump}.provenance.json").read_text(encoding="utf-8"))
            objdump_provenance["source_provenance"] = {
                "nested": [
                    {
                        "path": str(protected_link),
                    }
                ]
            }
            Path(f"{objdump}.provenance.json").write_text(json.dumps(objdump_provenance), encoding="utf-8")

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            blockers = [
                item
                for item in payload["promotion_gate"]["blockers"]
                if item["reason"] == "unverified_static_artifact_provenance"
            ]
            self.assertEqual(len(blockers), 1)
            self.assertEqual(blockers[0]["artifact"], "objdump")
            self.assertEqual(blockers[0]["detail"], "protected_static_artifact_source_provenance_path")
            provenance = payload["commands"]["objdump"]["provenance"]
            self.assertEqual(provenance["source_provenance_field"], "source_provenance.nested[0].path")
            self.assertEqual(provenance["protected_path"], "/servidor/ark/copied.objdump")

    def test_rejects_symlinked_protected_static_artifact_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
""",
                encoding="utf-8",
            )
            Path(f"{programs}.provenance.json").symlink_to("/servidor/ark/static-artifact.provenance.json")

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("static artifact provenance must not be under /servidor/ark", result.stderr)

    def test_generated_static_artifacts_write_reusable_provenance_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_path = root / "generated.txt"
            binary_sha = "a" * 64

            record = build_static_global_promotion_evidence.copy_or_generate_artifact(
                source=None,
                command=["python3", "-c", "print('generated')"],
                output_path=output_path,
                binary_sha256=binary_sha,
                artifact_kind="objdump",
            )

            provenance_path = Path(f"{output_path}.provenance.json")
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            self.assertEqual(record["output_provenance"], str(provenance_path))
            self.assertEqual(
                provenance["schema"],
                build_static_global_promotion_evidence.STATIC_ARTIFACT_PROVENANCE_SCHEMA,
            )
            self.assertIs(provenance["verified"], True)
            self.assertEqual(provenance["artifact_kind"], "objdump")
            self.assertEqual(provenance["producer"], build_static_global_promotion_evidence.PROVENANCE_PRODUCER)
            self.assertEqual(provenance["binary_sha256"], binary_sha)
            self.assertEqual(provenance["artifact_sha256"], record["stdout_sha256"])
            self.assertEqual(provenance["command"], ["python3", "-c", "print('generated')"])
            self.assertEqual(provenance["tool"], "python3")

    def test_missing_rip_relative_xref_blocks_static_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000001000 <InitObjects>:
  1017: bf e0 b7 95 05        mov    edi,0x595b7e0
""",
                encoding="utf-8",
            )
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertFalse(candidate["static_contract"]["satisfied"])
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                [
                    "missing_rip_relative_xref",
                    "missing_gobjects_code_backed_field_xrefs:gobjects.chunks,gobjects.count,gobjects.root,gobjects.serial",
                ],
            )
            blocker_reasons = {item["reason"] for item in payload["promotion_gate"]["blockers"]}
            self.assertIn("candidate_static_contract_blocked", blocker_reasons)

    def test_gobjects_requires_coherent_field_xrefs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
""",
                encoding="utf-8",
            )
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            blockers = payload["candidates"][0]["static_contract"]["blockers"]
            self.assertEqual(blockers, ["missing_gobjects_code_backed_field_xrefs:gobjects.chunks,gobjects.count,gobjects.serial"])

    def test_gobjects_rejects_split_executable_field_xrefs_without_coherent_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <RootOnly>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
0000000000402500 <ChunksOnly>:
  402510: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
0000000000403a00 <CountOnly>:
  403a10: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
0000000000404f00 <SerialOnly>:
  404f10: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(
                candidate["target_code_backed_xref_counts"],
                {"gobjects.chunks": 1, "gobjects.count": 1, "gobjects.root": 1, "gobjects.serial": 1},
            )
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                ["missing_gobjects_coherent_field_window"],
            )
            self.assertIsNone(candidate["static_contract"]["coherent_window"])
            near_miss = candidate["static_contract"]["near_miss"]
            self.assertEqual(near_miss["context"], "gobjects_required_field_window")
            self.assertEqual(
                near_miss["required_labels"],
                ["gobjects.chunks", "gobjects.count", "gobjects.root", "gobjects.serial"],
            )
            self.assertEqual(near_miss["eligible_xref_count"], 4)
            self.assertEqual(len(near_miss["windows"]), 4)
            self.assertEqual(near_miss["windows"][0]["anchor_start"], "0x401010")
            self.assertEqual(near_miss["windows"][0]["present_required_labels"], ["gobjects.root"])
            self.assertEqual(
                near_miss["windows"][0]["missing_required_labels"],
                ["gobjects.chunks", "gobjects.count", "gobjects.serial"],
            )
            self.assertEqual(near_miss["windows"][0]["reject_reasons"], ["missing_required_labels"])

    def test_redacted_field_window_evidence_clears_only_coherent_window_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <RootOnly>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
0000000000402500 <ChunksOnly>:
  402510: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
0000000000403a00 <CountOnly>:
  403a10: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
0000000000404f00 <SerialOnly>:
  404f10: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )
            for artifact in (programs, sections, objdump):
                write_static_artifact_provenance(artifact, binary)
            field_window = root / "fuobjectarray-field-window.json"
            write_redacted_field_window_evidence(field_window, sha256_file(binary))

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--fuobjectarray-field-window-evidence",
                str(field_window),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["static_contract"]["blockers"], [])
            self.assertTrue(candidate["static_contract"]["satisfied"])
            self.assertEqual(
                candidate["static_contract"]["redacted_field_window_evidence"]["clears_blocker"],
                "missing_gobjects_coherent_field_window",
            )
            self.assertFalse(payload["promotion_gate"]["ready"])
            self.assertEqual(
                {item["reason"] for item in payload["promotion_gate"]["blockers"]},
                {"static_only_evidence"},
            )

    def test_redacted_field_window_evidence_rejects_binary_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            field_window = root / "fuobjectarray-field-window.json"
            write_redacted_field_window_evidence(field_window, "0" * 64)

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--fuobjectarray-field-window-evidence",
                str(field_window),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("field-window evidence binary SHA256 mismatch", result.stderr)

    def test_redacted_field_window_evidence_rejects_candidate_address_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            field_window = root / "fuobjectarray-field-window.json"
            write_redacted_field_window_evidence(
                field_window,
                sha256_file(binary),
                candidate_address=0x595B7F0,
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--fuobjectarray-field-window-evidence",
                str(field_window),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("field-window evidence candidate address hash mismatch", result.stderr)

    def test_gobjects_semantics_do_not_weaken_split_window_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <BootstrapGObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
0000000000403000 <ResetGObjects>:
  403010: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  403017: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["semantic_summary"]["role_counts"], {"bootstrap": 2, "reset": 2})
            self.assertEqual(
                candidate["target_code_backed_xref_counts"],
                {"gobjects.chunks": 1, "gobjects.count": 1, "gobjects.root": 1, "gobjects.serial": 1},
            )
            self.assertEqual(candidate["static_contract"]["blockers"], ["missing_gobjects_coherent_field_window"])
            self.assertIsNone(candidate["static_contract"]["coherent_window"])
            self.assertFalse(payload["promotion_gate"]["ready"])
            self.assertIn(
                "candidate_static_contract_blocked",
                {item["reason"] for item in payload["promotion_gate"]["blockers"]},
            )

    def test_gobjects_near_miss_reports_closest_rejected_windows_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <RootChunksCount>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  40101e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
0000000000403000 <ChunksCountOnly>:
  403010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  403017: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
0000000000405000 <SerialOnly>:
  405010: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(
                candidate["target_code_backed_xref_counts"],
                {"gobjects.chunks": 2, "gobjects.count": 2, "gobjects.root": 1, "gobjects.serial": 1},
            )
            self.assertEqual(candidate["static_contract"]["blockers"], ["missing_gobjects_coherent_field_window"])
            near_miss = candidate["static_contract"]["near_miss"]
            self.assertEqual(near_miss["eligible_xref_count"], 3)
            self.assertEqual(len(near_miss["windows"]), 1)
            self.assertEqual(near_miss["windows"][0]["anchor_start"], "0x401010")
            self.assertEqual(
                near_miss["windows"][0]["present_required_labels"],
                ["gobjects.chunks", "gobjects.count", "gobjects.root"],
            )
            self.assertEqual(near_miss["windows"][0]["missing_required_labels"], ["gobjects.serial"])

    def test_gobjects_reports_split_field_windows_without_satisfying_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <RootChunksCount>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  40101e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
0000000000403000 <ChunksCountSerial>:
  403010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  403017: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  40301e: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            self.assertFalse(payload["promotion_gate"]["ready"])
            candidate = payload["candidates"][0]
            self.assertFalse(candidate["static_contract"]["satisfied"])
            self.assertEqual(candidate["static_contract"]["blockers"], ["missing_gobjects_coherent_field_window"])
            self.assertIsNone(candidate["static_contract"]["coherent_window"])
            split_evidence = candidate["static_contract"]["split_evidence"]
            self.assertEqual(split_evidence["context"], "gobjects_split_required_field_windows")
            self.assertEqual(split_evidence["status"], "split_near_miss")
            self.assertIs(split_evidence["coherent_contract_satisfied"], False)
            self.assertEqual(split_evidence["does_not_satisfy"], "missing_gobjects_coherent_field_window")
            root_cluster = split_evidence["root_chunks_count"]
            self.assertEqual(
                root_cluster["required_present_labels"],
                ["gobjects.chunks", "gobjects.count", "gobjects.root"],
            )
            self.assertEqual(root_cluster["required_missing_labels"], ["gobjects.serial"])
            self.assertEqual(root_cluster["window_count"], 1)
            self.assertEqual(root_cluster["windows"][0]["anchor_start"], "0x401010")
            serial_cluster = split_evidence["chunks_count_serial"]
            self.assertEqual(
                serial_cluster["required_present_labels"],
                ["gobjects.chunks", "gobjects.count", "gobjects.serial"],
            )
            self.assertEqual(serial_cluster["required_missing_labels"], ["gobjects.root"])
            self.assertEqual(serial_cluster["window_count"], 1)
            self.assertEqual(serial_cluster["windows"][0]["anchor_start"], "0x403010")

    def test_gobjects_rejects_coherent_window_crossing_known_functions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <RootAndChunks>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
000000000040101e <CountAndSerial>:
  40101e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  401025: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(
                candidate["target_code_backed_xref_counts"],
                {"gobjects.chunks": 1, "gobjects.count": 1, "gobjects.root": 1, "gobjects.serial": 1},
            )
            self.assertEqual(candidate["static_contract"]["blockers"], ["mixed_function_window"])
            self.assertIsNone(candidate["static_contract"]["coherent_window"])

    def test_gobjects_rejects_immediate_only_field_xrefs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: bf f0 b7 95 05        mov    edi,0x595b7f0
  40101c: bf 04 b8 95 05        mov    edi,0x595b804
""",
                encoding="utf-8",
            )
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["target_xref_counts"]["gobjects.chunks"], 1)
            self.assertNotIn("gobjects.chunks", candidate["target_code_backed_xref_counts"])
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                ["missing_gobjects_code_backed_field_xrefs:gobjects.chunks,gobjects.count,gobjects.serial"],
            )

    def test_gobjects_rejects_same_instruction_immediate_field_piggyback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0 0x595b7f0 0x595b804 0x595b838
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["target_xref_counts"]["gobjects.root"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.chunks"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.count"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.serial"], 1)
            self.assertEqual(candidate["target_code_backed_xref_counts"], {"gobjects.root": 1})
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                ["missing_gobjects_code_backed_field_xrefs:gobjects.chunks,gobjects.count,gobjects.serial"],
            )

    def test_gobjects_rejects_oversized_group_even_when_required_prefix_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            targets = [0x595B7E0, 0x595B7F0, 0x595B804, 0x595B838]
            lines = ["0000000000401000 <DenseLookup>:"]
            for index in range(64):
                address = 0x401000 + (index * 7)
                target = targets[index % len(targets)]
                lines.append(
                    f"  {address:x}: 48 8b 05 00 00 00 00  "
                    f"mov    rax,QWORD PTR [rip+0x1]        # 0x{target:x}"
                )
            objdump = root / "objdump.txt"
            objdump.write_text("\n".join(lines), encoding="utf-8")

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(
                candidate["target_code_backed_xref_counts"],
                {"gobjects.chunks": 16, "gobjects.count": 16, "gobjects.root": 16, "gobjects.serial": 16},
            )
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                ["missing_gobjects_coherent_field_window"],
            )
            self.assertIsNone(candidate["static_contract"]["coherent_window"])
            near_miss = candidate["static_contract"]["near_miss"]
            self.assertEqual(near_miss["eligible_xref_count"], 64)
            self.assertEqual(len(near_miss["windows"]), 1)
            self.assertEqual(near_miss["windows"][0]["missing_required_labels"], [])
            self.assertEqual(near_miss["windows"][0]["reject_reasons"], ["oversized_anchor_window"])
            self.assertTrue(near_miss["windows"][0]["oversized"])

    def test_gobjects_rejects_rip_relative_xrefs_outside_executable_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000005901000 <BadDataRange>:
  590010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  590017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  59001e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  590025: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["rip_relative_xref_count"], 4)
            self.assertEqual(candidate["target_code_backed_xref_counts"], {})
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                ["missing_gobjects_code_backed_field_xrefs:gobjects.chunks,gobjects.count,gobjects.root,gobjects.serial"],
            )

    def test_gobjects_rejects_rip_relative_field_xrefs_without_instruction_elf_membership(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <MissingElfRange>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
  401017: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x2]        # 0x595b7f0
  40101e: 39 3d 00 00 00 00     cmp    DWORD PTR [rip+0x3],edi        # 0x595b804
  401025: f0 0f c1 05 00 00 00  lock xadd DWORD PTR [rip+0x4],eax     # 0x595b838
""",
                encoding="utf-8",
            )
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["target_xref_counts"]["gobjects.root"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.chunks"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.count"], 1)
            self.assertEqual(candidate["target_xref_counts"]["gobjects.serial"], 1)
            self.assertEqual(candidate["target_code_backed_xref_counts"], {})
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                ["missing_gobjects_code_backed_field_xrefs:gobjects.chunks,gobjects.count,gobjects.root,gobjects.serial"],
            )

    def test_fname_root_candidate_requires_root_slot_xref(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000402000 <InitNames>:
  402000: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x5956f30
""",
                encoding="utf-8",
            )
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gnames=0x5956f30",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            self.assertFalse(payload["promotion_gate"]["ready"])
            self.assertIn("static_only_evidence", {item["reason"] for item in payload["promotion_gate"]["blockers"]})
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["kind"], "fname_root")
            self.assertEqual(candidate["target_xref_counts"], {"gnames.root_slot": 1})
            self.assertEqual(candidate["target_code_backed_xref_counts"], {"gnames.root_slot": 1})
            self.assertTrue(candidate["static_contract"]["satisfied"])

    def test_fname_root_rejects_same_instruction_immediate_root_slot_piggyback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000402000 <InitNames>:
  402000: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x400010 0x5956f30
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gnames=0x5956f30",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["target_xref_counts"], {"gnames.root_slot": 1})
            self.assertEqual(candidate["target_code_backed_xref_counts"], {})
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                ["missing_rip_relative_xref", "missing_fname_root_slot_xref"],
            )

    def test_gobjects_alias_does_not_bypass_field_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gu_objects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            candidate = payload["candidates"][0]
            self.assertEqual(candidate["kind"], "gobjects")
            self.assertEqual(
                candidate["static_contract"]["blockers"],
                ["missing_gobjects_code_backed_field_xrefs:gu_objects.chunks,gu_objects.count,gu_objects.serial"],
            )

    def test_unknown_candidate_kind_fails_closed_unless_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            rejected = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "objects=0x595b7e0",
                "--output-dir",
                str(root / "pack"),
                check=False,
            )

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("unsupported candidate kind for label objects", rejected.stderr)

    def test_explicit_candidate_kind_allows_ambiguous_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            programs = root / "programs.txt"
            programs.write_text(
                "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 "
                "0x3000000 0x3000000 R E 0x200000\n"
                "  LOAD           0x3000000 0x0000000005900000 0x0000000005900000 "
                "0x100000 0x100000 RW  0x200000\n",
                encoding="utf-8",
            )
            sections = root / "sections.txt"
            sections.write_text(
                "  [ 1] .text PROGBITS 0000000000400000 000000 03000000 00 AX 0 0 16\n"
                "  [ 2] .data PROGBITS 0000000005900000 3000000 00100000 00 WA 0 0 8\n",
                encoding="utf-8",
            )
            objdump = root / "objdump.txt"
            objdump.write_text(
                """
0000000000401000 <LookupObjects>:
  401010: 48 8b 05 00 00 00 00  mov    rax,QWORD PTR [rip+0x1]        # 0x595b7e0
""",
                encoding="utf-8",
            )

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "objects=0x595b7e0",
                "--candidate-kind",
                "objects=gobjects",
                "--output-dir",
                str(root / "pack"),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                "--json",
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["candidates"][0]["kind"], "gobjects")

    def test_rejects_candidate_kind_for_unknown_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--candidate-kind",
                "other=gobjects",
                "--output-dir",
                str(root / "pack"),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("candidate kind supplied for unknown label: other", result.stderr)

    def test_rejects_duplicate_candidate_address(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "first=0x595b7e0",
                "--candidate",
                "second=0x595b7e0",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(root / "missing-programs.txt"),
                "--readelf-sections",
                str(root / "missing-sections.txt"),
                "--objdump",
                str(root / "missing-objdump.txt"),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate candidate address: 0x595b7e0", result.stderr)

    def test_rejects_duplicate_candidate_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            output_dir = root / "pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--candidate",
                "gobjects=0x595c000",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(root / "missing-programs.txt"),
                "--readelf-sections",
                str(root / "missing-sections.txt"),
                "--objdump",
                str(root / "missing-objdump.txt"),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate candidate label: gobjects", result.stderr)

    def test_rejects_protected_server_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                "/servidor/ark/static-pack",
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output-dir must not be under /servidor/ark", result.stderr)

    def test_rejects_symlinked_protected_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            output_dir = root / "static-pack"
            output_dir.symlink_to("/servidor/ark/static-pack")
            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(output_dir),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output-dir must not be under /servidor/ark", result.stderr)

    def test_rejects_textually_protected_path_even_when_symlink_resolves_outside(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected_root = root / "protected"
            outside = root / "outside"
            protected_root.mkdir()
            outside.mkdir()
            outward_link = protected_root / "outward-link"
            outward_link.symlink_to(outside)

            with mock.patch.object(build_static_global_promotion_evidence, "PROTECTED_SERVER_ROOT", protected_root):
                with self.assertRaisesRegex(SystemExit, "--objdump must not be under"):
                    build_static_global_promotion_evidence.reject_protected_path(
                        outward_link / "copied.objdump",
                        "--objdump",
                    )

    def test_allows_approved_offline_workspace_under_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected_root = root / "protected"
            workspace = protected_root / "workspace-offline"
            workspace.mkdir(parents=True)

            with (
                mock.patch.object(build_static_global_promotion_evidence, "PROTECTED_SERVER_ROOT", protected_root),
                mock.patch.object(
                    build_static_global_promotion_evidence,
                    "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                    (workspace,),
                ),
            ):
                build_static_global_promotion_evidence.reject_protected_path(workspace / "ShooterGameServer", "--binary")
                build_static_global_promotion_evidence.reject_protected_path(workspace / "pack", "--output-dir")

    def test_rejects_protected_input_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            protected_cases = (
                ("--binary", "/servidor/ark/ShooterGameServer"),
                ("--readelf-programs", "/servidor/ark/readelf-programs.txt"),
                ("--readelf-sections", "/servidor/ark/readelf-sections.txt"),
                ("--objdump", "/servidor/ark/ShooterGameServer.objdump"),
            )
            for option, protected_path in protected_cases:
                with self.subTest(option=option):
                    args = [
                        "--binary",
                        str(binary),
                        "--candidate",
                        "gobjects=0x595b7e0",
                        "--output-dir",
                        str(root / "pack"),
                    ]
                    if option == "--binary":
                        args[1] = protected_path
                    else:
                        args.extend([option, protected_path])
                    result = self.run_script(*args, check=False)

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"{option} must not be under /servidor/ark", result.stderr)

    def test_rejects_unignored_in_repo_output_dir_before_static_artifact_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary, programs, sections, objdump = write_minimal_static_inputs(root)
            output_dir = REPO_ROOT / "docs" / "static-global-pack"

            result = self.run_script(
                "--binary",
                str(binary),
                "--candidate",
                "gobjects=0x595b7e0",
                "--output-dir",
                str(output_dir),
                "--readelf-programs",
                str(programs),
                "--readelf-sections",
                str(sections),
                "--objdump",
                str(objdump),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output-dir is inside the repository but is not ignored by Git", result.stderr)
            self.assertFalse(output_dir.exists())

    def test_rejects_symlinked_protected_input_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            link_cases = (
                ("--binary", "ShooterGameServer.link", "/servidor/ark/ShooterGameServer"),
                ("--readelf-programs", "programs.link", "/servidor/ark/readelf-programs.txt"),
                ("--readelf-sections", "sections.link", "/servidor/ark/readelf-sections.txt"),
                ("--objdump", "objdump.link", "/servidor/ark/ShooterGameServer.objdump"),
            )
            for option, link_name, target in link_cases:
                with self.subTest(option=option):
                    link = root / link_name
                    link.symlink_to(target)
                    args = [
                        "--binary",
                        str(binary),
                        "--candidate",
                        "gobjects=0x595b7e0",
                        "--output-dir",
                        str(root / "pack"),
                    ]
                    if option == "--binary":
                        args[1] = str(link)
                    else:
                        args.extend([option, str(link)])
                    result = self.run_script(*args, check=False)

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"{option} must not be under /servidor/ark", result.stderr)

    def test_protected_optional_input_rejection_precedes_candidate_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"static evidence binary")
            for option, protected_path in (
                ("--readelf-programs", "/servidor/ark/readelf-programs.txt"),
                ("--readelf-sections", "/servidor/ark/readelf-sections.txt"),
                ("--objdump", "/servidor/ark/ShooterGameServer.objdump"),
            ):
                with self.subTest(option=option):
                    result = self.run_script(
                        "--binary",
                        str(binary),
                        "--candidate",
                        "ambiguous=0x595b7e0",
                        "--output-dir",
                        str(root / "pack"),
                        option,
                        protected_path,
                        check=False,
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"{option} must not be under /servidor/ark", result.stderr)
                    self.assertNotIn("unsupported candidate kind", result.stderr)


if __name__ == "__main__":
    unittest.main()
