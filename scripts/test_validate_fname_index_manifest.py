#!/usr/bin/env python3
"""Offline tests for validate_fname_index_manifest.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import validate_fname_index_manifest as validator
SCRIPT = ["python3", "scripts/validate_fname_index_manifest.py"]
ARK_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
COMMITTED_FIXTURE = REPO_ROOT / "tests/fixtures/fname_index_manifests/7e7ded49/manifest.json"
VALID_RESEARCH_EVIDENCE = "docs/research/2026-05-27-arkserver-core-fname-evidence.md"
VALID_EVIDENCE_PACK_MANIFEST = "/offline/evidence-packs/core-pack-20260528T120000Z/manifest.json"


class FNameIndexManifestTests(unittest.TestCase):
    def write_manifest(self, root: Path, **overrides: object) -> Path:
        payload: dict[str, object] = {
            "schema": "obelisk.fname-index-manifest.v1",
            "ark_binary_sha256": ARK_SHA,
            "source": "offline_core",
            "evidence_status": "accepted",
            "promotion_evidence": {
                "schema": "obelisk.fname-index-promotion-evidence.v1",
                "status": "accepted",
                "second_source": True,
                "report": "docs/research/2026-05-28-second-source-reversing-gap-matrix.md",
            },
            "names": [
                {
                    "name": "ServerChat",
                    "index": 9619,
                    "number": 0,
                    "evidence": VALID_RESEARCH_EVIDENCE,
                },
                {
                    "name": "ClientMessage",
                    "index": 4884,
                    "number": 0,
                    "evidence": VALID_RESEARCH_EVIDENCE,
                },
            ],
        }
        payload.update(overrides)
        path = root / "fname-manifest.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def run_validator(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*SCRIPT, *args],
            cwd=REPO_ROOT,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_resolves_exact_name_for_matching_binary_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary-sha256",
                ARK_SHA,
                "--resolve-name",
                "ServerChat",
                "--json",
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.fname-index-manifest-validation.v1")
        self.assertEqual(payload["expected_ark_binary_sha256"], ARK_SHA)
        self.assertEqual(payload["generated_for_ark_binary_sha256"], ARK_SHA)
        self.assertEqual(payload["resolved"]["index"], 9619)
        self.assertEqual(payload["resolved"]["name"], "ServerChat")

    def test_non_json_resolution_output_records_generated_binary_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary-sha256",
                ARK_SHA,
                "--resolve-name",
                "ServerChat",
            )

        self.assertEqual(
            result.stdout.splitlines(),
            [
                "ServerChat#0=9619",
                f"generated_for_ark_binary_sha256={ARK_SHA}",
            ],
        )

    def test_can_hash_offline_binary_for_expected_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline ark binary")
            binary_sha = "4b0b6f65046e448fc74d2ed4abcfca981d57b79ddb5f8d5a1f0da2d53336849b"
            manifest = self.write_manifest(root, ark_binary_sha256=binary_sha)
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary",
                str(binary),
                "--resolve-name",
                "ServerChat",
                "--json",
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["expected_ark_binary_sha256"], binary_sha)
        self.assertEqual(payload["resolved"]["index"], 9619)

    def test_rejects_protected_server_binary_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary",
                "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer",
                "--resolve-name",
                "ServerChat",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--ark-binary must not read from protected server root /servidor/ark",
            result.stderr,
        )

    def test_allows_paths_that_only_share_protected_prefix_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary",
                "/servidor/ark-not-live/ShooterGameServer",
                "--resolve-name",
                "ServerChat",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--ark-binary must be a regular file", result.stderr)
        self.assertNotIn("protected server root", result.stderr)

    def test_allows_approved_offline_workspace_path_under_server_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)

            with (
                mock.patch.object(validator, "PROTECTED_INPUT_ROOTS", (protected,)),
                mock.patch.object(validator, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                validator.reject_protected_input_path(workspace / "ShooterGameServer", "--ark-binary")
                validator.reject_protected_input_path(workspace / "manifest.json", "--manifest")

    def test_rejects_symlink_to_protected_server_binary_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self.write_manifest(root)
            link = root / "ShooterGameServer"
            link.symlink_to("/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer")
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary",
                str(link),
                "--resolve-name",
                "ServerChat",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--ark-binary must not read from protected server root /servidor/ark",
            result.stderr,
        )

    def test_rejects_protected_server_manifest_path(self) -> None:
        result = self.run_validator(
            "--manifest",
            "/servidor/ark/obelisk/fname-manifest.json",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--manifest must not read from protected server root /servidor/ark",
            result.stderr,
        )

    def test_rejects_symlink_to_protected_server_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            link = root / "fname-manifest.json"
            link.symlink_to("/servidor/ark/obelisk/fname-manifest.json")
            result = self.run_validator(
                "--manifest",
                str(link),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--manifest must not read from protected server root /servidor/ark",
            result.stderr,
        )

    def test_committed_candidate_fixture_validates_but_default_resolve_rejects_candidate_use(self) -> None:
        validation = self.run_validator(
            "--manifest",
            str(COMMITTED_FIXTURE),
            "--ark-binary-sha256",
            ARK_SHA,
            "--json",
        )
        validation_payload = json.loads(validation.stdout)
        self.assertEqual(validation_payload["evidence_status"], "candidate-only")

        rejected = self.run_validator(
            "--manifest",
            str(COMMITTED_FIXTURE),
            "--ark-binary-sha256",
            ARK_SHA,
            "--resolve-name",
            "ServerChat",
            check=False,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("use --allow-candidate only for explicit internal/debug resolution", rejected.stderr)

        result = self.run_validator(
            "--manifest",
            str(COMMITTED_FIXTURE),
            "--ark-binary-sha256",
            ARK_SHA,
            "--resolve-name",
            "ServerChat",
            "--allow-candidate",
            "--json",
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["evidence_status"], "candidate-only")
        self.assertEqual(payload["resolved"]["index"], 9619)

        require_accepted = self.run_validator(
            "--manifest",
            str(COMMITTED_FIXTURE),
            "--ark-binary-sha256",
            ARK_SHA,
            "--resolve-name",
            "ServerChat",
            "--require-accepted",
            check=False,
        )
        self.assertNotEqual(require_accepted.returncode, 0)
        self.assertIn("accepted evidence is required", require_accepted.stderr)

    def test_rejects_binary_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary-sha256",
                "0" * 64,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match expected binary hash", result.stderr)

    def test_rejects_uppercase_manifest_or_expected_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir), ark_binary_sha256=ARK_SHA.upper())
            result = self.run_validator("--manifest", str(manifest), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest ark_binary_sha256 must be a lowercase SHA256 hex string", result.stderr)

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary-sha256",
                ARK_SHA.upper(),
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expected ark binary SHA256 must be a lowercase SHA256 hex string", result.stderr)

    def test_resolve_name_requires_expected_binary_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--resolve-name",
                "ServerChat",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--resolve-name requires --ark-binary or --ark-binary-sha256", result.stderr)

    def test_rejects_both_binary_and_explicit_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "ShooterGameServer"
            binary.write_bytes(b"offline ark binary")
            manifest = self.write_manifest(root)
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary",
                str(binary),
                "--ark-binary-sha256",
                ARK_SHA,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("use either --ark-binary or --ark-binary-sha256", result.stderr)

    def test_rejects_conflicting_candidate_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--require-accepted",
                "--allow-candidate",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("use either --require-accepted or --allow-candidate", result.stderr)

    def test_require_accepted_rejects_candidate_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(
                Path(temp_dir),
                evidence_status="candidate-only",
                promotion_evidence=None,
            )
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--require-accepted",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accepted evidence is required", result.stderr)

    def test_accepted_manifest_requires_second_source_promotion_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = self.write_manifest(Path(temp_dir), promotion_evidence=None)
            result = self.run_validator("--manifest", str(missing), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("accepted manifests require promotion_evidence object", result.stderr)

        with tempfile.TemporaryDirectory() as temp_dir:
            weak = self.write_manifest(
                Path(temp_dir),
                promotion_evidence={
                    "schema": "obelisk.fname-index-promotion-evidence.v1",
                    "status": "accepted",
                    "second_source": False,
                    "report": "docs/research/weak.md",
                },
            )
            result = self.run_validator("--manifest", str(weak), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("accepted second-source evidence", result.stderr)

        with tempfile.TemporaryDirectory() as temp_dir:
            undated_report = self.write_manifest(
                Path(temp_dir),
                promotion_evidence={
                    "schema": "obelisk.fname-index-promotion-evidence.v1",
                    "status": "accepted",
                    "second_source": True,
                    "report": "docs/research/weak.md",
                },
            )
            result = self.run_validator("--manifest", str(undated_report), check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("promotion_evidence.report must point to a dated docs/research note", result.stderr)

    def test_rejects_duplicate_index_and_identity(self) -> None:
        duplicate_index = [
            {"name": "ServerChat", "index": 9619, "number": 0, "evidence": VALID_RESEARCH_EVIDENCE},
            {"name": "Other", "index": 9619, "number": 0, "evidence": VALID_RESEARCH_EVIDENCE},
        ]
        duplicate_identity = [
            {"name": "ServerChat", "index": 9619, "number": 0, "evidence": VALID_RESEARCH_EVIDENCE},
            {"name": "ServerChat", "index": 9620, "number": 0, "evidence": VALID_RESEARCH_EVIDENCE},
        ]
        for names, expected in (
            (duplicate_index, "duplicate FName index"),
            (duplicate_identity, "duplicate FName identity"),
        ):
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as temp_dir:
                    manifest = self.write_manifest(Path(temp_dir), names=names)
                    result = self.run_validator("--manifest", str(manifest), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_accepted_manifest_requires_entry_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(
                Path(temp_dir),
                names=[{"name": "ServerChat", "index": 9619, "number": 0}],
            )
            result = self.run_validator("--manifest", str(manifest), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence is required for accepted manifests", result.stderr)

    def test_accepted_manifest_requires_structured_entry_evidence_path(self) -> None:
        invalid_names = [
            {"name": "ServerChat", "index": 9619, "number": 0, "evidence": "docs/research/weak.md"},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir), names=invalid_names)
            result = self.run_validator("--manifest", str(manifest), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dated docs/research note or evidence-pack manifest path", result.stderr)

        valid_names = [
            {"name": "ServerChat", "index": 9619, "number": 0, "evidence": VALID_EVIDENCE_PACK_MANIFEST},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir), names=valid_names)
            result = self.run_validator("--manifest", str(manifest), "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(payload["name_count"], 1)

    def test_accepted_manifest_rejects_protected_entry_evidence_manifest_path(self) -> None:
        protected_names = [
            {
                "name": "ServerChat",
                "index": 9619,
                "number": 0,
                "evidence": "/servidor/ark/obelisk/evidence-packs/core-pack/manifest.json",
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir), names=protected_names)
            result = self.run_validator("--manifest", str(manifest), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "manifest names[0].evidence must not read from protected server root /servidor/ark",
            result.stderr,
        )

    def test_accepted_manifest_rejects_symlinked_entry_evidence_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence_root = root / "offline-evidence-pack"
            evidence_root.mkdir()
            link = evidence_root / "manifest.json"
            link.symlink_to("/servidor/ark/obelisk/evidence-packs/core-pack/manifest.json")
            names = [
                {
                    "name": "ServerChat",
                    "index": 9619,
                    "number": 0,
                    "evidence": str(link),
                },
            ]
            manifest = self.write_manifest(root, names=names)
            result = self.run_validator("--manifest", str(manifest), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "manifest names[0].evidence must not read from protected server root /servidor/ark",
            result.stderr,
        )

    def test_rejects_bool_huge_or_numbered_fname_values(self) -> None:
        cases = (
            ([{"name": "ServerChat", "index": True, "number": 0, "evidence": "a.md"}], "index must be a non-negative int32"),
            ([{"name": "ServerChat", "index": 2_147_483_648, "number": 0, "evidence": "a.md"}], "index must be a non-negative int32"),
            ([{"name": "ServerChat", "index": 9619, "number": True, "evidence": "a.md"}], "number must be a non-negative int32"),
            ([{"name": "ServerChat", "index": 9619, "number": 1, "evidence": "a.md"}], "number values other than 0 are not supported"),
        )
        for names, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as temp_dir:
                    manifest = self.write_manifest(Path(temp_dir), names=names)
                    result = self.run_validator("--manifest", str(manifest), check=False)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_missing_name_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = self.write_manifest(Path(temp_dir))
            result = self.run_validator(
                "--manifest",
                str(manifest),
                "--ark-binary-sha256",
                ARK_SHA,
                "--resolve-name",
                "MissingFunction",
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FName not found in manifest", result.stderr)


if __name__ == "__main__":
    unittest.main()
