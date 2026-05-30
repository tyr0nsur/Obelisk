#!/usr/bin/env python3
"""Tests for normalize_artifact_pack.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import normalize_artifact_pack as tool  # noqa: E402

SCRIPT = ["python3", "scripts/normalize_artifact_pack.py"]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class NormalizeArtifactPackTests(unittest.TestCase):
    def run_tool(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*SCRIPT, *args],
            cwd=REPO_ROOT,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_builds_relative_manifest_and_sha256sums(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = Path(temp_dir) / "item-return-only-policy-slice-20260530T072255Z"
            pack.mkdir()
            (pack / "consume-gate.json").write_text('{"mode":"consume"}\n', encoding="utf-8")
            (pack / "promote-gate.json").write_text('{"mode":"promote"}\n', encoding="utf-8")
            (pack / "nested").mkdir()
            (pack / "nested" / "report.json").write_text('{"schema":"fixture"}\n', encoding="utf-8")

            result = self.run_tool(str(pack), "--json")

            summary = json.loads(result.stdout)
            self.assertEqual(3, summary["file_count"])
            manifest_path = pack / tool.MANIFEST_NAME
            sha256sums_path = pack / tool.SHA256SUMS_NAME
            manifest_bytes = manifest_path.read_bytes()
            manifest = json.loads(manifest_bytes)
            self.assertEqual(tool.SCHEMA, manifest["schema"])
            self.assertEqual(pack.name, manifest["artifact_id"])
            self.assertEqual("2026-05-30T07:22:55Z", manifest["generated_utc"])
            self.assertEqual(
                ["consume-gate.json", "nested/report.json", "promote-gate.json"],
                [entry["path"] for entry in manifest["files"]],
            )
            self.assertTrue(all(not entry["path"].startswith("/") for entry in manifest["files"]))
            self.assertEqual(
                [
                    f"{sha256_bytes(manifest_bytes)}  {tool.MANIFEST_NAME}",
                    f"{manifest['files'][0]['sha256']}  consume-gate.json",
                    f"{manifest['files'][1]['sha256']}  nested/report.json",
                    f"{manifest['files'][2]['sha256']}  promote-gate.json",
                ],
                sha256sums_path.read_text(encoding="utf-8").splitlines(),
            )
            self.run_tool(str(pack), "--check")

    def test_does_not_rewrite_report_or_gate_json_internals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = Path(temp_dir) / "mission-copied-bool-policy-slice"
            pack.mkdir()
            consume = pack / "consume-gate.json"
            report = pack / "mission-copied-bool-policy-slice.json"
            promote = pack / "promote-gate.json"
            consume_text = '{ "mode" : "consume", "keep" : [3,2,1] }\n'
            report_text = '{\n  "schema": "fixture",\n  "spacing": "preserved"\n}\n'
            promote_text = '{"mode":"promote","blocked":true}\n'
            consume.write_text(consume_text, encoding="utf-8")
            report.write_text(report_text, encoding="utf-8")
            promote.write_text(promote_text, encoding="utf-8")

            self.run_tool(
                str(pack),
                "--artifact-id",
                "mission-copied-bool-policy-slice",
                "--generated-utc",
                "2026-05-30T07:29:12Z",
            )

            self.assertEqual(consume_text, consume.read_text(encoding="utf-8"))
            self.assertEqual(report_text, report.read_text(encoding="utf-8"))
            self.assertEqual(promote_text, promote.read_text(encoding="utf-8"))

    def test_check_mode_rejects_drift_without_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = Path(temp_dir) / "transfer-baccept-only-policy-slice"
            pack.mkdir()
            payload = pack / "transfer-baccept-only-policy-slice.json"
            payload.write_text('{"before":true}\n', encoding="utf-8")
            self.run_tool(
                str(pack),
                "--artifact-id",
                "transfer-baccept-only-policy-slice",
                "--generated-utc",
                "2026-05-30T07:33:08Z",
            )
            payload.write_text('{"after":true}\n', encoding="utf-8")

            result = self.run_tool(str(pack), "--check", check=False)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("artifact-pack.manifest.json is not normalized", result.stderr)

    def test_rejects_symlinked_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            pack.mkdir()
            (pack / "consume-gate.json").write_text("{}\n", encoding="utf-8")
            outside = root / "outside-manifest.json"
            outside.write_text("do not replace\n", encoding="utf-8")
            (pack / tool.MANIFEST_NAME).symlink_to(outside)

            result = self.run_tool(str(pack), check=False)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("refusing to overwrite symlinked pack output", result.stderr)
            self.assertEqual("do not replace\n", outside.read_text(encoding="utf-8"))

    def test_rejects_symlinked_pack_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            pack.mkdir()
            target = root / "report.json"
            target.write_text("{}\n", encoding="utf-8")
            (pack / "report.json").symlink_to(target)

            result = self.run_tool(str(pack), check=False)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("refusing to normalize pack containing symlink", result.stderr)


if __name__ == "__main__":
    unittest.main()
