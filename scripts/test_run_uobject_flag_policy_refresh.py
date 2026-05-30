#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import run_uobject_flag_policy_refresh as refresh
import test_build_uobject_flag_policy_report as fixtures


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_uobject_flag_policy_refresh.py"
BINARY_SHA256 = fixtures.BINARY_SHA256
UOBJECT_FLAG_POLICY_ARTIFACT_KIND = "obelisk.uobject-flag-policy-report.v1"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_rich_sidecar(path: Path, *, tool: str = "objdump") -> None:
    path.with_name(path.name + ".provenance.json").write_text(
        json.dumps(
            {
                "schema": "obelisk.static-artifact-provenance.v1",
                "verified": True,
                "binary_sha256": BINARY_SHA256,
                "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "path_redacted": True,
                "command": [tool, "-d", "ShooterGameServer"],
                "tool": tool,
                "tool_version": f"{tool} test-version",
                "start_address": "0x1000",
                "stop_address": "0x1010",
                "source_path": "ShooterGameServer",
                "claim_level": "candidate_internal_static_only",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def write_refresh_inputs(root: Path) -> None:
    ghidra = root / "weak" / "ghidra-headless.stdout"
    r2 = root / "weak" / "r2-weak-helper-caller-modes.txt"
    counts = root / "weak" / "direct-call-counts.txt"
    write_text(ghidra, fixtures.weak_helper_ghidra_fixture())
    write_text(r2, fixtures.weak_helper_r2_fixture())
    write_text(counts, fixtures.weak_helper_counts_fixture())
    write_rich_sidecar(ghidra, tool="ghidra")
    write_rich_sidecar(r2, tool="radare2")
    write_rich_sidecar(counts, tool="objdump")

    window_texts = fixtures.window_texts()
    weak_helper_c70 = """
1d56c81: 39 15 7d 4b c0 03     cmp    DWORD PTR [rip+0x3c04b7d],edx        # 595b804 <g_ue4_tm_api@@UE4+0xd814>
1d56ca2: 48 8b 3d 47 4b c0 03  mov    rdi,QWORD PTR [rip+0x3c04b47]        # 595b7f0 <g_ue4_tm_api@@UE4+0xd800>
1d56ccf: 8b 51 08              mov    edx,DWORD PTR [rcx+0x8]
1d56cd4: 81 e7 00 01 00 00     and    edi,0x100
1d56cda: 75 0e                 jne    1d56cea <helper+0x7a>
1d56cdc: 40 84 f6              test   sil,sil
1d56ce3: f6 c6 40              test   dh,0x40
1d56ce6: 75 0b                 jne    1d56cf3 <helper+0x83>
1d56cea: 31 c0                 xor    eax,eax
1d56cf3: c3                    ret
"""
    for filename, keys in {
        "weak-helper-c70.objdump.txt": ("weak_helper_reject_0x100", "strict_0x4000_behavior"),
        "gobjects-4000-skip.objdump.txt": ("gobjects_backed_0x4000_skip",),
        "gobjects-100-gc-pass.objdump.txt": ("gc_static_0x100_support",),
    }.items():
        path = root / "windows" / filename
        text = weak_helper_c70 if filename == "weak-helper-c70.objdump.txt" else "\n".join(window_texts[key] for key in keys)
        write_text(path, text)
        write_rich_sidecar(path)


class RunUObjectFlagPolicyRefreshTests(unittest.TestCase):
    def run_refresh(
        self,
        input_root: Path,
        output_root: Path,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--input-root",
                str(input_root),
                "--output-root",
                str(output_root),
                "--expected-binary-sha256",
                BINARY_SHA256,
                "--tool-version",
                "ghidra=Ghidra test-version",
                "--tool-version",
                "radare2=radare2 test-version",
                "--tool-version",
                "objdump=GNU objdump test-version",
                *(extra_args or []),
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_runs_rich_preflight_consume_and_blocked_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_root = base / "input"
            output_root = base / "output"
            write_refresh_inputs(input_root)

            result = self.run_refresh(input_root, output_root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "accepted_internal_static_evidence")
            self.assertEqual(payload["promotion_status"], "blocked")
            for output_path in payload["outputs"].values():
                self.assertTrue(Path(output_path).is_file(), output_path)

            consume = json.loads((output_root / "uobject-flag-policy.consume-gate.json").read_text(encoding="utf-8"))
            promote = json.loads((output_root / "uobject-flag-policy.promote-gate.json").read_text(encoding="utf-8"))
            self.assertEqual(consume["status"], "accepted")
            self.assertEqual(promote["status"], "blocked")

    def test_passes_artifact_identity_to_policy_report_builder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            commands: list[list[str]] = []
            original_run_json = refresh.run_json
            original_run_command = refresh.run_command

            def fake_run_json(
                command: list[str],
                *,
                output: Path | None = None,
                allowed_returncodes: set[int] | None = None,
            ) -> dict[str, object]:
                commands.append(command)
                if output is not None:
                    output.write_text("{}\n", encoding="utf-8")
                if "--mode" in command:
                    mode = command[command.index("--mode") + 1]
                    if mode == "consume":
                        return {"status": "accepted"}
                    return {
                        "status": "blocked",
                        "blockers": [{"reason": "promote_mode_uobject_flag_policy_candidate_only"}],
                    }
                return {"status": "accepted"}

            def fake_run_command(command: list[str]) -> None:
                commands.append(command)

            refresh.run_json = fake_run_json
            refresh.run_command = fake_run_command
            try:
                payload = refresh.build_result(
                    Namespace(
                        input_root=base / "input",
                        output_root=base / "output",
                        expected_binary_sha256=BINARY_SHA256,
                        artifact_kind=UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                        capture_id="capture_2026-05-30",
                        evidence_pack_id="evidence-pack.alpha_1",
                        strict_artifact_identity=False,
                        tool_version=[],
                    )
                )
            finally:
                refresh.run_json = original_run_json
                refresh.run_command = original_run_command

        builder_command = next(
            command for command in commands if command[1].endswith("build_uobject_flag_policy_report.py")
        )
        self.assertIn("--artifact-kind", builder_command)
        self.assertIn("--capture-id", builder_command)
        self.assertIn("--evidence-pack-id", builder_command)
        self.assertEqual(builder_command[builder_command.index("--artifact-kind") + 1], UOBJECT_FLAG_POLICY_ARTIFACT_KIND)
        self.assertEqual(
            builder_command[builder_command.index("--capture-id") + 1],
            "capture_2026-05-30",
        )
        self.assertEqual(
            builder_command[builder_command.index("--evidence-pack-id") + 1],
            "evidence-pack.alpha_1",
        )
        self.assertEqual(
            payload["artifact_identity"],
            {
                "artifact_kind": UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                "capture_id": "capture_2026-05-30",
                "evidence_pack_id": "evidence-pack.alpha_1",
            },
        )

    def test_strict_artifact_identity_requires_explicit_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_root = Path(tmp) / "input"
            output_root = Path(tmp) / "output"
            write_refresh_inputs(input_root)

            result = self.run_refresh(input_root, output_root, ["--strict-artifact-identity"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--strict-artifact-identity requires --artifact-kind, --capture-id, and --evidence-pack-id",
            result.stderr,
        )

    def test_strict_artifact_identity_verifies_generated_policy_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            commands: list[list[str]] = []
            original_run_json = refresh.run_json
            original_run_command = refresh.run_command

            def fake_run_json(
                command: list[str],
                *,
                output: Path | None = None,
                allowed_returncodes: set[int] | None = None,
            ) -> dict[str, object]:
                commands.append(command)
                if output is not None:
                    output.write_text("{}\n", encoding="utf-8")
                if "--mode" in command:
                    mode = command[command.index("--mode") + 1]
                    if mode == "consume":
                        return {"status": "accepted"}
                    return {
                        "status": "blocked",
                        "blockers": [{"reason": "promote_mode_uobject_flag_policy_candidate_only"}],
                    }
                return {"status": "accepted"}

            def fake_run_command(command: list[str]) -> None:
                commands.append(command)
                if command[1].endswith("build_uobject_flag_policy_report.py"):
                    output_path = Path(command[command.index("--output") + 1])
                    output_path.write_text(
                        json.dumps(
                            {
                                "schema": "obelisk.uobject-flag-policy-report.v1",
                                "artifact_identity": {
                                    "artifact_kind": UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                                    "artifact_sha256": "f" * 64,
                                    "capture_id": "capture_2026-05-30",
                                    "evidence_pack_id": "evidence-pack.alpha_1",
                                },
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )

            refresh.run_json = fake_run_json
            refresh.run_command = fake_run_command
            try:
                payload = refresh.build_result(
                    Namespace(
                        input_root=base / "input",
                        output_root=base / "output",
                        expected_binary_sha256=BINARY_SHA256,
                        artifact_kind=UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                        capture_id="capture_2026-05-30",
                        evidence_pack_id="evidence-pack.alpha_1",
                        strict_artifact_identity=True,
                        tool_version=[],
                    )
                )
            finally:
                refresh.run_json = original_run_json
                refresh.run_command = original_run_command

        self.assertEqual(
            payload["output_artifact_identity"],
            {
                "artifact_kind": UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                "artifact_sha256": "f" * 64,
                "capture_id": "capture_2026-05-30",
                "evidence_pack_id": "evidence-pack.alpha_1",
            },
        )

    def test_strict_artifact_identity_rejects_missing_generated_policy_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original_run_json = refresh.run_json
            original_run_command = refresh.run_command

            def fake_run_json(
                command: list[str],
                *,
                output: Path | None = None,
                allowed_returncodes: set[int] | None = None,
            ) -> dict[str, object]:
                if output is not None:
                    output.write_text("{}\n", encoding="utf-8")
                if "--mode" in command:
                    return {"status": "accepted"}
                return {"status": "accepted"}

            def fake_run_command(command: list[str]) -> None:
                if command[1].endswith("build_uobject_flag_policy_report.py"):
                    output_path = Path(command[command.index("--output") + 1])
                    output_path.write_text(
                        json.dumps({"schema": "obelisk.uobject-flag-policy-report.v1"}) + "\n",
                        encoding="utf-8",
                    )

            refresh.run_json = fake_run_json
            refresh.run_command = fake_run_command
            try:
                with self.assertRaisesRegex(SystemExit, "missing top-level artifact_identity"):
                    refresh.build_result(
                        Namespace(
                            input_root=base / "input",
                            output_root=base / "output",
                            expected_binary_sha256=BINARY_SHA256,
                            artifact_kind=UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                            capture_id="capture_2026-05-30",
                            evidence_pack_id="evidence-pack.alpha_1",
                            strict_artifact_identity=True,
                            tool_version=[],
                        )
                    )
            finally:
                refresh.run_json = original_run_json
                refresh.run_command = original_run_command

    def test_strict_artifact_identity_rejects_incomplete_generated_policy_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original_run_json = refresh.run_json
            original_run_command = refresh.run_command

            def fake_run_json(
                command: list[str],
                *,
                output: Path | None = None,
                allowed_returncodes: set[int] | None = None,
            ) -> dict[str, object]:
                if output is not None:
                    output.write_text("{}\n", encoding="utf-8")
                if "--mode" in command:
                    return {"status": "accepted"}
                return {"status": "accepted"}

            def fake_run_command(command: list[str]) -> None:
                if command[1].endswith("build_uobject_flag_policy_report.py"):
                    output_path = Path(command[command.index("--output") + 1])
                    output_path.write_text(
                        json.dumps(
                            {
                                "schema": "obelisk.uobject-flag-policy-report.v1",
                                "artifact_identity": {
                                    "artifact_kind": UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                                    "capture_id": "capture_2026-05-30",
                                    "evidence_pack_id": "evidence-pack.alpha_1",
                                },
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )

            refresh.run_json = fake_run_json
            refresh.run_command = fake_run_command
            try:
                with self.assertRaisesRegex(SystemExit, "incomplete artifact_identity artifact_sha256"):
                    refresh.build_result(
                        Namespace(
                            input_root=base / "input",
                            output_root=base / "output",
                            expected_binary_sha256=BINARY_SHA256,
                            artifact_kind=UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                            capture_id="capture_2026-05-30",
                            evidence_pack_id="evidence-pack.alpha_1",
                            strict_artifact_identity=True,
                            tool_version=[],
                        )
                    )
            finally:
                refresh.run_json = original_run_json
                refresh.run_command = original_run_command

    def test_strict_artifact_identity_rejects_generated_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original_run_json = refresh.run_json
            original_run_command = refresh.run_command

            def fake_run_json(
                command: list[str],
                *,
                output: Path | None = None,
                allowed_returncodes: set[int] | None = None,
            ) -> dict[str, object]:
                if output is not None:
                    output.write_text("{}\n", encoding="utf-8")
                if "--mode" in command:
                    return {"status": "accepted"}
                return {"status": "accepted"}

            def fake_run_command(command: list[str]) -> None:
                if command[1].endswith("build_uobject_flag_policy_report.py"):
                    output_path = Path(command[command.index("--output") + 1])
                    output_path.write_text(
                        json.dumps(
                            {
                                "schema": "obelisk.uobject-flag-policy-report.v1",
                                "artifact_identity": {
                                    "artifact_kind": UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                                    "artifact_sha256": "f" * 64,
                                    "capture_id": "wrong-capture",
                                    "evidence_pack_id": "evidence-pack.alpha_1",
                                },
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )

            refresh.run_json = fake_run_json
            refresh.run_command = fake_run_command
            try:
                with self.assertRaisesRegex(SystemExit, "artifact_identity.capture_id mismatch"):
                    refresh.build_result(
                        Namespace(
                            input_root=base / "input",
                            output_root=base / "output",
                            expected_binary_sha256=BINARY_SHA256,
                            artifact_kind=UOBJECT_FLAG_POLICY_ARTIFACT_KIND,
                            capture_id="capture_2026-05-30",
                            evidence_pack_id="evidence-pack.alpha_1",
                            strict_artifact_identity=True,
                            tool_version=[],
                        )
                    )
            finally:
                refresh.run_json = original_run_json
                refresh.run_command = original_run_command

    def test_requires_complete_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_root = Path(tmp) / "input"
            output_root = Path(tmp) / "output"
            write_refresh_inputs(input_root)

            result = self.run_refresh(input_root, output_root, ["--artifact-kind", "offline_core"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "artifact identity must include --artifact-kind, --capture-id, and --evidence-pack-id together",
            result.stderr,
        )

    def test_rejects_unsafe_artifact_identity_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_root = Path(tmp) / "input"
            output_root = Path(tmp) / "output"
            write_refresh_inputs(input_root)

            result = self.run_refresh(input_root, output_root, ["--capture-id", "../bad"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--capture-id must not contain '..'", result.stderr)

    def test_refuses_output_inside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_root = Path(tmp) / "input"
            write_refresh_inputs(input_root)
            output_root = REPO_ROOT / "tmp-uobject-refresh-test-output"

            result = self.run_refresh(input_root, output_root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be inside the repository", result.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_refuses_repo_local_symlink_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_root = Path(tmp) / "input"
            write_refresh_inputs(input_root)
            output_target = Path(tmp) / "outside-output"
            output_root = REPO_ROOT / "tmp-uobject-refresh-symlink-output"
            output_root.unlink(missing_ok=True)
            try:
                output_root.symlink_to(output_target, target_is_directory=True)

                result = self.run_refresh(input_root, output_root)
            finally:
                output_root.unlink(missing_ok=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be inside the repository", result.stderr)

    def test_refuses_input_under_protected_server_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "output"
            input_root = Path("/servidor/ark/obelisk/dumps/not-allowed-uobject-refresh-input")

            result = self.run_refresh(input_root, output_root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not read under protected server root", result.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support required")
    def test_refuses_preexisting_output_leaf_symlink_into_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_root = base / "input"
            output_root = base / "output"
            write_refresh_inputs(input_root)
            output_root.mkdir()
            repo_target = REPO_ROOT / "tmp-uobject-refresh-leaf-target.json"
            repo_target.unlink(missing_ok=True)
            leaf = output_root / "rich-provenance-preflight.json"
            try:
                leaf.symlink_to(repo_target)

                result = self.run_refresh(input_root, output_root)
            finally:
                leaf.unlink(missing_ok=True)
                repo_target.unlink(missing_ok=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be inside the repository", result.stderr)

    def test_refuses_output_under_protected_server_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_root = Path(tmp) / "input"
            write_refresh_inputs(input_root)
            output_root = Path("/servidor/ark/not-allowed-uobject-refresh-test-output")

            result = self.run_refresh(input_root, output_root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not write under protected server root", result.stderr)


if __name__ == "__main__":
    unittest.main()
