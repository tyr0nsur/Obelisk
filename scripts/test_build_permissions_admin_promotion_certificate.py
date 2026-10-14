#!/usr/bin/env python3
"""Tests for build_permissions_admin_promotion_certificate.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BUILDER = SCRIPT_DIR / "build_permissions_admin_promotion_certificate.py"
PERMISSIONS_DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
QUERY_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
QUERY_CHECKER = SCRIPT_DIR / "check_permissions_admin_query_failclosed_contract.py"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_permissions_admin_promotion_certificate as builder  # noqa: E402
try:  # noqa: E402
    from scripts.test_check_permissions_admin_public_readiness import (
        promote_identity_surface_for_permissions_tests,
        write_identity_promotion_certificate as write_identity_promotion_certificate_binding,
    )
except ModuleNotFoundError:  # noqa: E402
    from test_check_permissions_admin_public_readiness import (
        promote_identity_surface_for_permissions_tests,
        write_identity_promotion_certificate as write_identity_promotion_certificate_binding,
    )


class BuildPermissionsAdminPromotionCertificateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._repo_tempdirs: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self._repo_tempdirs):
            shutil.rmtree(path, ignore_errors=True)

    def repo_tempdir(self) -> Path:
        path = Path(
            tempfile.mkdtemp(
                prefix="PermissionsAdminPromotionBuilder",
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

    def write_surfaces_with_identity_certificate(self, root: Path) -> Path:
        payload = json.loads(SURFACES.read_text(encoding="utf-8"))
        identity_surface = promote_identity_surface_for_permissions_tests(payload)
        identity_surface["evidence"]["player_identity_promotion_certificate"] = (
            write_identity_promotion_certificate_binding(root, identity_surface)
        )
        surfaces = root / "public-sdk-surfaces.with-player-identity-certificate.json"
        self.write_json(surfaces, payload)
        return surfaces

    def write_surfaces_with_identity_certificate_binding(
        self,
        root: Path,
        binding: dict[str, str],
    ) -> Path:
        payload = json.loads(SURFACES.read_text(encoding="utf-8"))
        identity_surface = promote_identity_surface_for_permissions_tests(payload)
        identity_surface["evidence"]["player_identity_promotion_certificate"] = binding
        surfaces = root / "public-sdk-surfaces.with-custom-player-identity-certificate.json"
        self.write_json(surfaces, payload)
        return surfaces

    def run_builder(
        self,
        *,
        surfaces: Path,
        decisions: Path,
        query_contract: Path = QUERY_CONTRACT,
        output_certificate: Path | None = None,
        expect_returncode: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        certificate = output_certificate or surfaces.parent / "permissions-admin-certificate.json"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--public-sdk-surfaces",
                str(surfaces),
                "--permissions-decisions",
                str(decisions),
                "--query-failclosed-contract",
                str(query_contract),
                "--output-certificate",
                str(certificate),
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, expect_returncode, result.stderr)
        return result, certificate

    def test_builds_hash_bound_non_authorizing_certificate_after_identity_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(surfaces=surfaces, decisions=decisions)

        report = json.loads(result.stdout)
        self.assertEqual(
            report["schema"],
            "obelisk.permissions-admin-promotion-certificate-build-report.v1",
        )
        self.assertEqual(report["status"], "built")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)
        self.assertTrue(certificate.exists())

        payload = json.loads(certificate.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "obelisk.permissions-admin-promotion-certificate.v1")
        self.assertEqual(payload["surface_id"], "obelisk.permissions_admin.v1")
        self.assertEqual(payload["promotion_status"], "blocked_public_header_gate_missing")
        self.assertEqual(payload["route_blocker_to_use"], "public_header_gate_missing")
        self.assertEqual(
            payload["unresolved_technical_blocker"]["reason"],
            "public_header_gate_missing",
        )
        self.assertFalse(payload["public_header_allowed"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["counts_toward_permissions_admin"])
        self.assertFalse(payload["permissions_admin_unlock_allowed"])
        self.assertFalse(payload["evidence"]["counts_toward_permissions_admin"])
        self.assertFalse(payload["evidence"]["permissions_admin_unlock_allowed"])
        self.assertEqual(payload["sdk_progress"], 0)
        self.assertEqual(payload["p0_progress"], 0)
        self.assertEqual(
            payload["input_bindings"]["permissions_admin_query_failclosed_contract"]["sha256"],
            report_file_sha256(QUERY_CONTRACT),
        )
        self.assertEqual(
            payload["input_bindings"]["permissions_admin_public_contract_decisions"]["sha256"],
            report_file_sha256(decisions),
        )
        self.assertEqual(
            payload["input_bindings"]["public_sdk_surfaces"]["sha256"],
            report_file_sha256(surfaces),
        )

    def test_canonicalizes_current_identity_certificate_binding_in_output(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        surfaces_payload = json.loads(surfaces.read_text(encoding="utf-8"))
        identity_surface = next(
            surface
            for surface in surfaces_payload["surfaces"]
            if surface["id"] == "obelisk.player_identity.v1"
        )
        binding = identity_surface["evidence"]["player_identity_promotion_certificate"]
        binding["sha256"] = binding["sha256"].upper()
        self.write_json(surfaces, surfaces_payload)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(surfaces=surfaces, decisions=decisions)

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "built")
        payload = json.loads(certificate.read_text(encoding="utf-8"))
        canonical_binding = payload["input_bindings"][
            "player_identity_promotion_certificate"
        ]
        self.assertEqual(binding["path"], canonical_binding["path"])
        self.assertEqual(
            report_file_sha256(REPO_ROOT / binding["path"]),
            canonical_binding["sha256"],
        )
        self.assertNotEqual(binding["sha256"], canonical_binding["sha256"])
        self.assertFalse(Path(canonical_binding["path"]).is_absolute())

    def test_reports_missing_identity_certificate_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn("player_identity_promotion_certificate_missing_or_invalid", report["blockers"])
        self.assertIn("current_route_blocker_before_identity_public_contract_review", report["blockers"])
        self.assertIn("permissions_admin_readiness_not_accepted_for_planning", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        labels = {detail["label"] for detail in report["blocker_details"]}
        self.assertIn(
            "$.surfaces[player_identity].evidence.player_identity_promotion_certificate",
            labels,
        )

    def test_blocked_run_does_not_hash_preexisting_output_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )
        certificate = root / "preexisting-permissions-admin-certificate.json"
        self.write_json(certificate, {"schema": "obsolete-preexisting-output"})

        result, returned_certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            output_certificate=certificate,
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(certificate, returned_certificate)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(certificate.exists())
        self.assertFalse(report["certificate_written"])
        self.assertIsNone(report["certificate_sha256"])
        self.assertIn("player_identity_promotion_certificate_missing_or_invalid", report["blockers"])

    def test_reports_stale_permissions_decisions_route_lock_after_identity_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=PERMISSIONS_DECISIONS,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn(
            "accounting_lock_route_blocker_stale_after_identity_public_contract_review",
            report["blockers"],
        )
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["p0_progress"], 0)

    def test_reports_stale_upstream_identity_certificate_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        payload = json.loads(surfaces.read_text(encoding="utf-8"))
        identity_surface = next(
            surface
            for surface in payload["surfaces"]
            if surface["id"] == "obelisk.player_identity.v1"
        )
        identity_surface["public_fields"].append("stale_certificate_test_field")
        self.write_json(surfaces, payload)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn(
            "player_identity_promotion_certificate_stale_or_mismatched_upstream_surface",
            report["blockers"],
        )
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_reports_hash_unbound_upstream_identity_certificate_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        payload = json.loads(surfaces.read_text(encoding="utf-8"))
        identity_surface = next(
            surface
            for surface in payload["surfaces"]
            if surface["id"] == "obelisk.player_identity.v1"
        )
        binding = identity_surface["evidence"]["player_identity_promotion_certificate"]
        certificate_path = REPO_ROOT / binding["path"]
        certificate_payload = json.loads(certificate_path.read_text(encoding="utf-8"))
        certificate_payload["evidence"]["reviewed_artifact_hash"] = "1" * 64
        self.write_json(certificate_path, certificate_payload)
        binding["sha256"] = report_file_sha256(certificate_path)
        self.write_json(surfaces, payload)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn("player_identity_promotion_certificate_hash_unbound", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_reports_identity_certificate_binding_alias_keys_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        payload = json.loads(surfaces.read_text(encoding="utf-8"))
        identity_surface = next(
            surface
            for surface in payload["surfaces"]
            if surface["id"] == "obelisk.player_identity.v1"
        )
        identity_surface["evidence"]["player_identity_promotion_certificate"][
            "promotion_status"
        ] = "promoted"
        self.write_json(surfaces, payload)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn(
            "player_identity_promotion_certificate_binding_keys_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "player_identity_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_reports_bare_promotion_aliases_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        payload = json.loads(surfaces.read_text(encoding="utf-8"))
        permissions = next(
            surface
            for surface in payload["surfaces"]
            if surface["id"] == "obelisk.permissions_admin.v1"
        )
        permissions["scope_b_aliases"] = {
            "ready": True,
            "runtimeReady": True,
            "approvedRuntimeEvidence": True,
            "publicSdk": True,
            "stableSdk": True,
            "completeSdk": True,
            "P0": True,
            "supportTier": {"status": "supported"},
            "PluginHub": {"status": "ready"},
            "packageShape": {"status": "ready"},
            "beta": {"status": "ready"},
            "Discord": {"status": "sent"},
            "passiveSnapshot": {"status": "ready"},
            "scopedReleaseStatement": True,
        }
        self.write_json(surfaces, payload)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("generic_readiness_or_progress_alias_overclaim", report["blockers"])
        labels = {detail["label"] for detail in report["blocker_details"]}
        for suffix in (
            ".scope_b_aliases.P0",
            ".scope_b_aliases.beta",
            ".scope_b_aliases.Discord",
            ".scope_b_aliases.scopedReleaseStatement",
        ):
            self.assertTrue(any(label.endswith(suffix) for label in labels), labels)
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_direct_build_revalidates_current_surfaces_after_stale_readiness_report(self) -> None:
        root = self.repo_tempdir()
        surfaces_path = self.write_surfaces_with_identity_certificate(root)
        decisions_path = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )
        query_report = builder.query_validation_report(
            json.loads(QUERY_CONTRACT.read_text(encoding="utf-8"))
        )
        readiness = builder.readiness_report(
            surfaces_path=surfaces_path,
            decisions_path=decisions_path,
            query_path=QUERY_CONTRACT,
            current_route_blocker="public_header_gate_missing",
        )
        self.assertTrue(readiness["accepted_for_planning"])

        current_surfaces = json.loads(surfaces_path.read_text(encoding="utf-8"))
        permissions_surface = next(
            surface
            for surface in current_surfaces["surfaces"]
            if surface["id"] == "obelisk.permissions_admin.v1"
        )
        permissions_surface["status"] = "promoted"

        blockers = builder.preflight_blockers(
            surfaces=current_surfaces,
            query_report=query_report,
            readiness=readiness,
        )
        self.assertIn(
            "permissions_admin_surface_status_unexpected",
            {blocker["reason"] for blocker in blockers},
        )
        with self.assertRaisesRegex(SystemExit, "inputs failed preflight"):
            builder.build_certificate(
                surfaces=current_surfaces,
                surfaces_path=surfaces_path,
                decisions_path=decisions_path,
                query_path=QUERY_CONTRACT,
                query_report=query_report,
                readiness=readiness,
            )

    def test_reports_invalid_query_contract_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )
        query_payload = json.loads(QUERY_CONTRACT.read_text(encoding="utf-8"))
        query_payload["promotion_ready"] = True
        query_path = root / "invalid-query-contract.json"
        self.write_json(query_path, query_payload)

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            query_contract=query_path,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn("query_failclosed_contract_invalid", report["blockers"])
        self.assertIn("query_failclosed_artifact_promotion_ready_not_false", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["sdk_progress"], 0)

    def test_reports_stale_query_contract_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )
        query_payload = json.loads(QUERY_CONTRACT.read_text(encoding="utf-8"))
        query_payload["non_claim"] = "local stale copy for currentness regression test only"
        query_path = root / "stale-query-contract.json"
        self.write_json(query_path, query_payload)

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            query_contract=query_path,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn(
            "permissions_admin_query_failclosed_contract_not_current",
            report["blockers"],
        )
        self.assertNotIn("query_failclosed_contract_invalid", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["sdk_progress"], 0)

    def test_reports_query_checker_report_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )
        query_report_path = root / "permissions-query-report.json"
        query_report = subprocess.run(
            [sys.executable, str(QUERY_CHECKER), str(QUERY_CONTRACT), "--json"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        query_report_path.write_text(query_report.stdout, encoding="utf-8")

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            query_contract=query_report_path,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn("query_failclosed_contract_invalid", report["blockers"])
        self.assertIn("query_failclosed_report_not_accepted_as_artifact", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["sdk_progress"], 0)

    def test_reports_identity_certificate_build_report_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        identity_build_report = root / "player-identity-certificate-build-report.json"
        self.write_json(
            identity_build_report,
            {
                "schema": "obelisk.player-identity-promotion-certificate-build-report.v1",
                "status": "built",
                "certificate_artifact_schema": "obelisk.player-identity-promotion-certificate.v1",
                "identity_surface_certificate_binding_valid": True,
                "ready": False,
                "promotion_ready": False,
                "public_header_allowed": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "sdk_progress": 0,
                "p0_progress": 0,
            },
        )
        surfaces = self.write_surfaces_with_identity_certificate_binding(
            root,
            {
                "path": str(identity_build_report.relative_to(REPO_ROOT)),
                "sha256": report_file_sha256(identity_build_report),
            },
        )
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn("player_identity_promotion_certificate_build_report_not_certificate", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_evidence_missing", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["sdk_progress"], 0)

    def test_reports_generated_template_upstream_identity_certificate_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        surfaces = self.write_surfaces_with_identity_certificate(root)
        payload = json.loads(surfaces.read_text(encoding="utf-8"))
        identity_surface = next(
            surface
            for surface in payload["surfaces"]
            if surface["id"] == "obelisk.player_identity.v1"
        )
        binding = identity_surface["evidence"]["player_identity_promotion_certificate"]
        certificate_path = REPO_ROOT / binding["path"]
        certificate_payload = json.loads(certificate_path.read_text(encoding="utf-8"))
        certificate_payload["generated_from_template"] = True
        certificate_payload["evidence"]["reviewed_identity_public_contract_decision_record_template_only"] = True
        self.write_json(certificate_path, certificate_payload)
        binding["sha256"] = report_file_sha256(certificate_path)
        self.write_json(surfaces, payload)
        decisions = self.write_permissions_decisions_with_route_blocker(
            root,
            "public_header_gate_missing",
        )

        result, certificate = self.run_builder(
            surfaces=surfaces,
            decisions=decisions,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(certificate.exists())
        self.assertIn(
            "player_identity_promotion_certificate_generated_or_template_artifact",
            report["blockers"],
        )
        self.assertIn(
            "player_identity_promotion_certificate_reviewed_template_only",
            report["blockers"],
        )
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)


def report_file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
