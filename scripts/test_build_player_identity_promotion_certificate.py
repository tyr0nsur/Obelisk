#!/usr/bin/env python3
"""Tests for build_player_identity_promotion_certificate.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BUILDER = SCRIPT_DIR / "build_player_identity_promotion_certificate.py"
DECISION_BUILDER = SCRIPT_DIR / "build_player_identity_public_contract_decision_record.py"
STRICT_APPROVED_RUNTIME_CHECKER = (
    SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
)
PERMISSIONS_CHECKER = SCRIPT_DIR / "check_permissions_admin_public_readiness.py"
PERMISSIONS_DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (  # noqa: E402
    SAFE_OFFLINE_WORKSPACE,
    manifest as approved_runtime_manifest,
    safe_test_env as approved_runtime_safe_test_env,
)

os.environ.update(approved_runtime_safe_test_env())

import build_player_identity_promotion_certificate as certificate_builder  # noqa: E402


class BuildPlayerIdentityPromotionCertificateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._repo_tempdirs: list[Path] = []
        self.patch_runtime_checker_roots()

    def tearDown(self) -> None:
        for path in reversed(self._repo_tempdirs):
            shutil.rmtree(path, ignore_errors=True)

    def patch_runtime_checker_roots(self) -> None:
        certificate_builder.approved_runtime_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (
            SAFE_OFFLINE_WORKSPACE,
        )
        certificate_builder.approved_runtime_checker.window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (
            SAFE_OFFLINE_WORKSPACE,
        )

    def repo_tempdir(self) -> Path:
        path = Path(
            tempfile.mkdtemp(
                prefix="PlayerIdentityPromotionBuilder",
                dir=REPO_ROOT / "tests" / "core",
            )
        )
        self._repo_tempdirs.append(path)
        return path

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_permissions_decisions_with_route_blocker(self, root: Path, blocker: str) -> Path:
        decisions = json.loads(PERMISSIONS_DECISIONS.read_text(encoding="utf-8"))
        decisions["accounting_lock"]["current_route_blocker"] = blocker
        decisions["accounting_lock"]["remaining_route_blockers"] = [blocker]
        path = root / "permissions-admin-decisions.json"
        self.write_json(path, decisions)
        return path

    def strict_report_for(self, runtime_path: Path) -> dict:
        env = os.environ.copy()
        env.update(approved_runtime_safe_test_env())
        result = subprocess.run(
            [
                sys.executable,
                str(STRICT_APPROVED_RUNTIME_CHECKER),
                "--json",
                str(runtime_path),
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def write_reviewed_decision_record(
        self,
        temp_dir: Path,
        *,
        runtime_manifest: dict | None = None,
        strict_report: dict | None = None,
    ) -> tuple[Path, Path]:
        runtime_path = temp_dir / "approved-runtime-principal-lifecycle-evidence.json"
        strict_report_path = temp_dir / "approved-runtime-principal-lifecycle-evidence.check.json"
        decision_record_path = (
            self.repo_tempdir()
            / "reviewed-identity-public-contract-decision-record.json"
        )
        self.write_json(runtime_path, runtime_manifest or approved_runtime_manifest())
        self.write_json(strict_report_path, strict_report or self.strict_report_for(runtime_path))
        env = os.environ.copy()
        env.update(approved_runtime_safe_test_env())
        result = subprocess.run(
            [
                sys.executable,
                str(DECISION_BUILDER),
                "--approved-runtime-evidence",
                str(runtime_path),
                "--strict-approved-runtime-check-report",
                str(strict_report_path),
                "--output",
                str(decision_record_path),
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return runtime_path, decision_record_path

    def run_builder(
        self,
        *,
        runtime_path: Path,
        decision_record_path: Path,
        output_parent: Path | None = None,
        output_certificate: Path | None = None,
        expect_returncode: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
        parent = output_parent or self.repo_tempdir()
        certificate = output_certificate or parent / "player-identity-promotion-certificate.json"
        surfaces = parent / "public-sdk-surfaces.with-player-identity-certificate.json"
        env = os.environ.copy()
        env.update(approved_runtime_safe_test_env())
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--approved-runtime-evidence",
                str(runtime_path),
                "--identity-public-contract-decision-record",
                str(decision_record_path),
                "--output-certificate",
                str(certificate),
                "--output-surfaces",
                str(surfaces),
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, expect_returncode, result.stderr)
        return result, certificate, surfaces

    def test_builds_hash_bound_certificate_consumed_by_permissions_admin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_path, decision_record_path = self.write_reviewed_decision_record(Path(temp_dir))
            result, certificate, surfaces = self.run_builder(
                runtime_path=runtime_path,
                decision_record_path=decision_record_path,
            )

        report = json.loads(result.stdout)
        self.assertEqual(
            report["schema"],
            "obelisk.player-identity-promotion-certificate-build-report.v1",
        )
        self.assertNotIn("promotion_status", report)
        self.assertTrue(report["identity_surface_certificate_binding_valid"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(
            report["post_runtime_bridge_constraints"],
            certificate_builder.POST_RUNTIME_BRIDGE_CONSTRAINTS,
        )

        certificate_payload = json.loads(certificate.read_text(encoding="utf-8"))
        self.assertEqual(certificate_payload["promotion_status"], "promoted")
        self.assertEqual(
            certificate_payload["post_runtime_bridge_constraints"],
            certificate_builder.POST_RUNTIME_BRIDGE_CONSTRAINTS,
        )
        self.assertEqual(
            certificate_payload["evidence"]["post_runtime_bridge_constraints"],
            certificate_builder.POST_RUNTIME_BRIDGE_CONSTRAINTS,
        )
        self.assertFalse(
            certificate_payload["post_runtime_bridge_constraints"][
                "public_header_gate_missing_after_runtime_evidence"
            ]
        )
        self.assertFalse(
            certificate_payload["post_runtime_bridge_constraints"]["terminal_certificate"]
        )
        self.assertEqual(certificate_payload["post_runtime_bridge_constraints"]["sdk_progress"], 0)
        self.assertEqual(certificate_payload["post_runtime_bridge_constraints"]["p0_progress"], 0)
        self.assertEqual(
            certificate_payload["evidence"]["promotion_evidence_kind"],
            "player_identity_promotion_certificate",
        )
        decision_record_payload = json.loads(decision_record_path.read_text(encoding="utf-8"))
        decision_record_artifact = certificate_payload["evidence"][
            "identity_public_contract_decision_record_artifact"
        ]
        self.assertEqual(
            decision_record_artifact["schema"],
            certificate_builder.DECISION_RECORD_ARTIFACT_BINDING_SCHEMA,
        )
        self.assertEqual(
            decision_record_artifact["policy"],
            certificate_builder.DECISION_RECORD_ARTIFACT_BINDING_POLICY,
        )
        self.assertNotIn("path", decision_record_artifact)
        self.assertEqual(
            decision_record_artifact["sha256"],
            certificate_builder.sha256_file(decision_record_path),
        )
        self.assertEqual(
            decision_record_artifact["canonical_payload_sha256"],
            certificate_builder.permissions_readiness.canonical_json_sha256(
                decision_record_payload
            ),
        )
        self.assertEqual(
            certificate_payload["evidence"][
                "identity_public_contract_decision_record_payload_sha256"
            ],
            decision_record_artifact["canonical_payload_sha256"],
        )
        runtime_binding = certificate_payload["evidence"][
            "identity_public_contract_decision_record_runtime_binding"
        ]
        self.assertEqual(
            runtime_binding["schema"],
            certificate_builder.DECISION_RUNTIME_BINDING_DIGEST_SCHEMA,
        )
        self.assertEqual(
            runtime_binding["policy"],
            certificate_builder.DECISION_RUNTIME_BINDING_DIGEST_POLICY,
        )
        self.assertEqual(
            runtime_binding["decision_record_approved_runtime_evidence_binding_sha256"],
            runtime_binding["approved_runtime_evidence_binding_sha256"],
        )
        decisions_path = self.write_permissions_decisions_with_route_blocker(
            surfaces.parent,
            "public_header_gate_missing",
        )

        checked = subprocess.run(
            [
                sys.executable,
                str(PERMISSIONS_CHECKER),
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces),
                "--current-route-blocker",
                "public_header_gate_missing",
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        permissions_report = json.loads(checked.stdout)
        self.assertTrue(permissions_report["next_steps"]["identity_contract_certificate_observed"])
        self.assertTrue(
            permissions_report["identity_input_diagnostics"][
                "identity_public_contract_certificate_observed"
            ]
        )
        self.assertFalse(permissions_report["public_sdk_ready"])
        self.assertFalse(permissions_report["runtime_ready"])

        surfaces_payload = json.loads(surfaces.read_text(encoding="utf-8"))
        identity_surface = next(
            surface
            for surface in surfaces_payload["surfaces"]
            if surface["id"] == certificate_builder.IDENTITY_SURFACE
        )
        self.assertEqual(
            identity_surface["post_runtime_bridge_constraints"],
            certificate_builder.POST_RUNTIME_BRIDGE_CONSTRAINTS,
        )
        self.assertEqual(
            identity_surface["evidence"]["post_runtime_bridge_constraints"],
            certificate_builder.POST_RUNTIME_BRIDGE_CONSTRAINTS,
        )

    def test_rejects_invalid_decision_record_before_writing_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            decision_record = json.loads(decision_record_path.read_text(encoding="utf-8"))
            decision_record["accepted_for_contract_review"] = False
            self.write_json(decision_record_path, decision_record)
            result, certificate, surfaces = self.run_builder(
                runtime_path=runtime_path,
                decision_record_path=decision_record_path,
                expect_returncode=1,
            )

        self.assertIn("identity public-contract decision record failed validation", result.stderr)
        self.assertFalse(certificate.exists())
        self.assertFalse(surfaces.exists())

    def test_rejects_decision_record_bound_to_different_runtime_evidence_before_writing_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            future_runtime = approved_runtime_manifest(standing_launch_authority=True)
            future_runtime_path = temp_path / "future-approved-runtime-principal-lifecycle-evidence.json"
            self.write_json(future_runtime_path, future_runtime)

            result, certificate, surfaces = self.run_builder(
                runtime_path=future_runtime_path,
                decision_record_path=decision_record_path,
                expect_returncode=1,
            )

        self.assertIn("not hash-bound to --approved-runtime-evidence", result.stderr)
        self.assertFalse(certificate.exists())
        self.assertFalse(surfaces.exists())

    def test_rejects_decision_record_bound_to_duplicate_runtime_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            duplicate_runtime_path = temp_path / "current-approved-runtime-principal-lifecycle-evidence.json"
            duplicate_runtime_path.write_text(runtime_path.read_text(encoding="utf-8"), encoding="utf-8")

            result, certificate, surfaces = self.run_builder(
                runtime_path=duplicate_runtime_path,
                decision_record_path=decision_record_path,
                expect_returncode=1,
            )

        self.assertIn("manifest ref does not match --approved-runtime-evidence", result.stderr)
        self.assertFalse(certificate.exists())
        self.assertFalse(surfaces.exists())

    def test_rejects_schema_current_but_unaccepted_runtime_evidence_before_writing_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            runtime_payload["runtime_evidence_ready"] = False
            runtime_payload["promotion_gate"]["runtime_evidence_ready"] = False
            self.write_json(runtime_path, runtime_payload)
            result, certificate, surfaces = self.run_builder(
                runtime_path=runtime_path,
                decision_record_path=decision_record_path,
                expect_returncode=1,
            )

        self.assertIn("failed strict approved-runtime checker", result.stderr)
        self.assertIn("runtime_evidence_ready_not_true", result.stderr)
        self.assertFalse(certificate.exists())
        self.assertFalse(surfaces.exists())

    def test_direct_build_rejects_runtime_payload_stale_against_current_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            decision_record = json.loads(decision_record_path.read_text(encoding="utf-8"))
            surfaces = json.loads(certificate_builder.SURFACES.read_text(encoding="utf-8"))
            _promoted, identity_surface = (
                certificate_builder.promote_identity_surface_for_certificate(
                    surfaces=surfaces,
                    approved_runtime_evidence=runtime_payload,
                )
            )

            current_runtime_payload = dict(runtime_payload)
            current_runtime_payload["runtime_evidence_ready"] = False
            self.write_json(runtime_path, current_runtime_payload)

            with self.assertRaisesRegex(
                SystemExit,
                "--approved-runtime-evidence payload is stale or mismatched",
            ):
                certificate_builder.build_certificate(
                    identity_surface=identity_surface,
                    approved_runtime_evidence=runtime_payload,
                    approved_runtime_path=runtime_path,
                    decision_record=decision_record,
                    decision_record_path=decision_record_path,
                )

    def test_direct_build_rejects_decision_record_payload_stale_against_current_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            decision_record = json.loads(decision_record_path.read_text(encoding="utf-8"))
            surfaces = json.loads(certificate_builder.SURFACES.read_text(encoding="utf-8"))
            _promoted, identity_surface = (
                certificate_builder.promote_identity_surface_for_certificate(
                    surfaces=surfaces,
                    approved_runtime_evidence=runtime_payload,
                )
            )

            current_decision_record = dict(decision_record)
            current_decision_record["accepted_for_contract_review"] = False
            self.write_json(decision_record_path, current_decision_record)

            with self.assertRaisesRegex(
                SystemExit,
                "--identity-public-contract-decision-record payload is stale or mismatched",
            ):
                certificate_builder.build_certificate(
                    identity_surface=identity_surface,
                    approved_runtime_evidence=runtime_payload,
                    approved_runtime_path=runtime_path,
                    decision_record=decision_record,
                    decision_record_path=decision_record_path,
                )

    def test_rejects_non_approved_runtime_schema_before_writing_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            self.write_json(runtime_path, {"schema": "obelisk.runtime-window-plan.v1"})
            result, certificate, surfaces = self.run_builder(
                runtime_path=runtime_path,
                decision_record_path=decision_record_path,
                expect_returncode=1,
            )

        self.assertIn("--approved-runtime-evidence schema mismatch", result.stderr)
        self.assertFalse(certificate.exists())
        self.assertFalse(surfaces.exists())

    def test_rejects_certificate_output_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            result, certificate, surfaces = self.run_builder(
                runtime_path=runtime_path,
                decision_record_path=decision_record_path,
                output_parent=temp_path,
                output_certificate=temp_path / "outside-repo-certificate.json",
                expect_returncode=1,
            )

        self.assertIn("--output-certificate must be under the Obelisk repo root", result.stderr)
        self.assertFalse(certificate.exists())
        self.assertFalse(surfaces.exists())

    def test_rejects_output_parent_that_is_file_before_writing_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_path, decision_record_path = self.write_reviewed_decision_record(Path(temp_dir))
            root = self.repo_tempdir()
            parent_file = root / "not-a-directory"
            parent_file.write_text("not a directory\n", encoding="utf-8")

            result, certificate, surfaces = self.run_builder(
                runtime_path=runtime_path,
                decision_record_path=decision_record_path,
                output_parent=root,
                output_certificate=parent_file / "certificate.json",
                expect_returncode=1,
            )

        self.assertIn("--output-certificate parent could not be created", result.stderr)
        self.assertFalse(certificate.exists())
        self.assertFalse(surfaces.exists())

    def test_direct_build_rejects_missing_surface_bridge_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            decision_record = json.loads(decision_record_path.read_text(encoding="utf-8"))
            surfaces = json.loads(certificate_builder.SURFACES.read_text(encoding="utf-8"))
            _promoted, identity_surface = (
                certificate_builder.promote_identity_surface_for_certificate(
                    surfaces=surfaces,
                    approved_runtime_evidence=runtime_payload,
                )
            )
            identity_surface.pop("post_runtime_bridge_constraints")

            with self.assertRaisesRegex(
                SystemExit,
                "post-runtime bridge constraints mismatch",
            ):
                certificate_builder.build_certificate(
                    identity_surface=identity_surface,
                    approved_runtime_evidence=runtime_payload,
                    approved_runtime_path=runtime_path,
                    decision_record=decision_record,
                    decision_record_path=decision_record_path,
                )

    def test_direct_build_requires_current_decision_record_file_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_path, decision_record_path = self.write_reviewed_decision_record(temp_path)
            runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            decision_record = json.loads(decision_record_path.read_text(encoding="utf-8"))
            surfaces = json.loads(certificate_builder.SURFACES.read_text(encoding="utf-8"))
            _promoted, identity_surface = (
                certificate_builder.promote_identity_surface_for_certificate(
                    surfaces=surfaces,
                    approved_runtime_evidence=runtime_payload,
                )
            )

            with self.assertRaisesRegex(
                SystemExit,
                "requires a current --identity-public-contract-decision-record file binding",
            ):
                certificate_builder.build_certificate(
                    identity_surface=identity_surface,
                    approved_runtime_evidence=runtime_payload,
                    approved_runtime_path=runtime_path,
                    decision_record=decision_record,
                    decision_record_path=None,
                )


if __name__ == "__main__":
    unittest.main()
