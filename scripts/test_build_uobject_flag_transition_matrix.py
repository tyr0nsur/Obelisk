#!/usr/bin/env python3
"""Tests for the redacted UObject flag transition matrix builder."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "build_uobject_flag_transition_matrix.py"
BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def window_texts() -> dict[str, str]:
    return {
        "weak_publish_from_uobject_1d56970_1d56a30": """
0000000001d56970 <candidate_window>:
1d56970: 8b 47 08              mov    eax,DWORD PTR [rdi+0x8]
1d56973: 8b 4f 0c              mov    ecx,DWORD PTR [rdi+0xc]
""",
        "weak_validity_mode_a30_1d56a30_1d56ae0": """
0000000001d56a30 <candidate_window>:
1d56a30: f6 47 09 01           test   BYTE PTR [rdi+0x9],0x1
1d56a34: 40 84 f6              test   sil,sil
1d56a37: f6 47 09 40           test   BYTE PTR [rdi+0x9],0x40
""",
        "weak_validity_strict_ae0_1d56ae0_1d56b60": """
0000000001d56ae0 <candidate_window>:
1d56ae0: 48 85 ff              test   rdi,rdi
1d56ae3: f6 47 09 01           test   BYTE PTR [rdi+0x9],0x1
1d56ae7: f6 47 09 40           test   BYTE PTR [rdi+0x9],0x40
""",
        "weak_stale_mode_b60_1d56b60_1d56c00": """
0000000001d56b60 <candidate_window>:
1d56b60: f6 47 09 01           test   BYTE PTR [rdi+0x9],0x1
1d56b64: 40 84 f6              test   sil,sil
1d56b67: f6 47 09 40           test   BYTE PTR [rdi+0x9],0x40
""",
        "weak_lookup_strict_c00_1d56c00_1d56c70": """
0000000001d56c00 <candidate_window>:
1d56c00: f6 47 09 01           test   BYTE PTR [rdi+0x9],0x1
1d56c04: f6 47 09 40           test   BYTE PTR [rdi+0x9],0x40
""",
        "weak_lookup_allow4000_c70_1d56c70_1d56d00": """
0000000001d56c70 <candidate_window>:
1d56c70: f6 47 09 01           test   BYTE PTR [rdi+0x9],0x1
1d56c74: 40 84 f6              test   sil,sil
""",
        "weak_lookup_raw_d00_1d56d00_1d56d60": """
0000000001d56d00 <candidate_window>:
1d56d00: 48 8b 05 d9 e9 77 03  mov    rax,QWORD PTR [rip+0x377e9d9] # 595b7e0
1d56d07: 48 8d 04 c8           lea    rax,[rax+rcx*8]
""",
        "weak_refresh_from_object_d60_1d56d60_1d56ed0": """
0000000001d56d60 <candidate_window>:
1d56d60: f6 47 09 01           test   BYTE PTR [rdi+0x9],0x1
1d56d64: e8 07 fc ff ff        call   1d56970 <candidate_window>
""",
        "gc_mark_100_8000_1d18a90_1d18c70": """
0000000001d18a90 <candidate_window>:
1d18b33: 81 4f 08 00 01 00 00  or     DWORD PTR [rdi+0x8],0x100
1d18b3a: 81 ca 00 80 00 00     or     edx,0x8000
1d18b40: 89 57 08              mov    DWORD PTR [rdi+0x8],edx
""",
        "gobjects_4000_skip_mark_2982920_2982b60": """
0000000002982920 <candidate_window>:
2982920: f6 47 09 40           test   BYTE PTR [rdi+0x9],0x40
2982924: 80 4f 09 40           or     BYTE PTR [rdi+0x9],0x40
""",
        "holder_4000_skip_mark_11ee120_11ee270": """
00000000011ee120 <candidate_window>:
11ee120: f6 47 09 40           test   BYTE PTR [rdi+0x9],0x40
11ee124: 80 4f 09 40           or     BYTE PTR [rdi+0x9],0x40
""",
    }


class BuildUObjectFlagTransitionMatrixTests(unittest.TestCase):
    def run_builder(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def write_windows(
        self,
        root: Path,
        *,
        windows: dict[str, str] | None = None,
        write_provenance: bool = True,
    ) -> dict[str, Path]:
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
        return paths

    def builder_args(self, windows: dict[str, Path], output: Path) -> list[str]:
        args = [
            "--binary-sha256",
            BINARY_SHA256,
            "--output",
            str(output),
        ]
        for name, path in windows.items():
            args.extend(["--window", f"{name}={path}"])
        return args

    def test_emits_candidate_only_redacted_transition_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output))

            self.assertEqual(result.stdout, "")
            payload = json.loads(output.read_text(encoding="utf-8"))

        rendered = json.dumps(payload)
        self.assertEqual(payload["schema"], "obelisk.uobject-flag-transition-matrix.v1")
        self.assertEqual(payload["status"], "candidate_blocked")
        self.assertEqual(payload["builder_contract"]["matrix_kind"], "semantic_helper_windows")
        self.assertIs(payload["builder_contract"]["promotion_ready"], False)
        self.assertIs(payload["builder_contract"]["requires_live_server"], False)
        self.assertIs(payload["builder_contract"]["resource_handle_claim"], False)
        self.assertIs(payload["builder_contract"]["public_lifecycle_names_assigned"], False)
        self.assertEqual(sorted(payload["transition_matrix"]), ["0x100", "0x4000", "0x8000"])
        self.assertEqual(len(payload["windows_summary"]["observed"]), 11)
        first_window = payload["windows_summary"]["observed"][0]
        self.assertEqual(
            first_window["provenance"]["schema"],
            "obelisk.offline-artifact-provenance.v1",
        )
        self.assertEqual(first_window["provenance"]["binary_sha256"], BINARY_SHA256)
        self.assertEqual(first_window["provenance"]["artifact_sha256"], first_window["artifact_sha256"])
        self.assertRegex(first_window["provenance"]["sidecar_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn(
            "weak_stale_mode_b60_1d56b60_1d56c00",
            payload["windows_summary"]["groups"]["predicate_windows"],
        )
        self.assertEqual(
            payload["transition_matrix"]["0x8000"]["mutation_windows"],
            ["gc_mark_100_8000_1d18a90_1d18c70"],
        )
        self.assertNotIn(str(root), rendered)
        self.assertNotIn("ResourceHandle", rendered)
        self.assertNotIn("pending", rendered.lower())
        self.assertNotIn("rootset", rendered.lower())

    def test_fails_closed_when_required_window_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            texts = window_texts()
            del texts["weak_stale_mode_b60_1d56b60_1d56c00"]
            windows = self.write_windows(root, windows=texts)
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required --window entries", result.stderr)
            self.assertIn("weak_stale_mode_b60_1d56b60_1d56c00", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_on_unknown_window_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            unknown = root / "unknown.txt"
            unknown.write_text(next(iter(window_texts().values())), encoding="utf-8")
            windows["annotated_0x100"] = unknown
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown --window entries", result.stderr)
            self.assertIn("annotated_0x100", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_window_lacks_required_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            texts = window_texts()
            texts["weak_lookup_strict_c00_1d56c00_1d56c70"] = """
29829e0: 48 8b 18              mov    rbx,QWORD PTR [rax]
29829e3: 90                    nop
"""
            windows = self.write_windows(root, windows=texts)
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("window evidence incomplete", result.stderr)
            self.assertIn("weak_lookup_strict_c00_1d56c00_1d56c70", result.stderr)
            self.assertIn("tests_0x100", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root, write_provenance=False)
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--window weak_publish_from_uobject_1d56970_1d56a30 provenance does not exist", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_schema_is_wrong(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            first_path = windows["weak_publish_from_uobject_1d56970_1d56a30"]
            provenance_path = first_path.with_name(first_path.name + ".provenance.json")
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
            payload["schema"] = "wrong.schema"
            provenance_path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("provenance_schema_mismatch", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_binary_sha_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            first_path = windows["weak_publish_from_uobject_1d56970_1d56a30"]
            provenance_path = first_path.with_name(first_path.name + ".provenance.json")
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
            payload["binary_sha256"] = "0" * 64
            provenance_path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("provenance_binary_sha256_mismatch", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_contains_protected_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            first_path = windows["weak_publish_from_uobject_1d56970_1d56a30"]
            provenance_path = first_path.with_name(first_path.name + ".provenance.json")
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
            payload["source_path"] = "/servidor/ark/obelisk/dumps/raw-window.txt"
            provenance_path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("provenance_protected_path_field:$.source_path", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_when_window_provenance_contains_relative_protected_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            first_path = windows["weak_publish_from_uobject_1d56970_1d56a30"]
            provenance_path = first_path.with_name(first_path.name + ".provenance.json")
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
            payload["source_path"] = os.path.relpath(
                "/servidor/ark/obelisk/dumps/raw-window.txt",
                start=provenance_path.parent,
            )
            provenance_path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("provenance_protected_path_field:$.source_path", result.stderr)
            self.assertFalse(output.exists())

    def test_fails_closed_on_narrative_token_soup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            texts = window_texts()
            texts["weak_publish_from_uobject_1d56970_1d56a30"] = """
this prose copies the token or DWORD PTR [rdi+0x8],0x100
but it is not an objdump instruction window.
"""
            windows = self.write_windows(root, windows=texts)
            output = root / "matrix.json"
            result = self.run_builder(*self.builder_args(windows, output), check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("window evidence incomplete", result.stderr)
            self.assertIn("weak_publish_from_uobject_1d56970_1d56a30", result.stderr)
            self.assertIn("non_objdump_text_lines", result.stderr)
            self.assertFalse(output.exists())

    def test_accepts_static_artifact_provenance_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            first_path = windows["weak_publish_from_uobject_1d56970_1d56a30"]
            provenance_path = first_path.with_name(first_path.name + ".provenance.json")
            payload = json.loads(provenance_path.read_text(encoding="utf-8"))
            payload["schema"] = "obelisk.static-artifact-provenance.v1"
            provenance_path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "matrix.json"
            self.run_builder(*self.builder_args(windows, output))

            matrix = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(matrix["windows_summary"]["observed"][0]["name"], first_path.stem)

    def test_optional_supplemental_clear_window_is_not_required_but_is_grouped_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            texts = window_texts()
            texts["uobject_100_clear_1d637c8_1d63888"] = """
0000000001d637c8 <candidate_window>:
1d637c8: 81 67 08 ff fe ff 07  and    DWORD PTR [rdi+0x8],0x7fffeff
1d637cf: 48 89 f8              mov    rax,rdi
"""
            windows = self.write_windows(root, windows=texts)
            output = root / "matrix.json"
            self.run_builder(*self.builder_args(windows, output))

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn(
                "uobject_100_clear_1d637c8_1d63888",
                payload["windows_summary"]["groups"]["mutation_windows"],
            )
            self.assertIn(
                "uobject_100_clear_1d637c8_1d63888",
                payload["transition_matrix"]["0x100"]["mutation_windows"],
            )

    def test_optional_supplemental_clear_window_is_not_cited_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            output = root / "matrix.json"
            self.run_builder(*self.builder_args(windows, output))

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn(
                "uobject_100_clear_1d637c8_1d63888",
                payload["transition_matrix"]["0x100"]["mutation_windows"],
            )

    def test_rejects_protected_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            windows = self.write_windows(root)
            result = self.run_builder(
                *self.builder_args(windows, Path("/servidor/ark/obelisk/flag-matrix.json")),
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--output must not write under protected server root", result.stderr)


if __name__ == "__main__":
    unittest.main()
