#!/usr/bin/env python3
"""Tests for build_command_chat_response_promotion_certificate.py."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BUILDER = SCRIPT_DIR / "build_command_chat_response_promotion_certificate.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_command_chat_response_promotion_certificate as builder  # noqa: E402
import check_command_chat_response_public_readiness as response_readiness  # noqa: E402
import test_check_command_chat_response_public_readiness as response_readiness_tests  # noqa: E402


class BuildCommandChatResponsePromotionCertificateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._repo_tempdirs: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self._repo_tempdirs):
            shutil.rmtree(path, ignore_errors=True)

    def repo_tempdir(self) -> Path:
        path = Path(
            tempfile.mkdtemp(
                prefix="CommandChatResponsePromotionBuilder",
                dir=REPO_ROOT / "tests" / "core",
            )
        )
        self._repo_tempdirs.append(path)
        return path

    @staticmethod
    def helper() -> unittest.TestCase:
        return response_readiness_tests.CheckCommandChatResponsePublicReadinessTests(
            methodName="test_accepts_planning_layout_second_source_but_not_public_readiness"
        )

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def rewrite_bound_certificate(surface: dict, surface_id: str, payload: dict) -> None:
        certificate_key = response_readiness.PROMOTION_CERTIFICATE_SPECS[surface_id][
            "certificate_key"
        ]
        binding = surface["evidence"][certificate_key]
        path = REPO_ROOT / binding["path"]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        binding["sha256"] = report_file_sha256(path)

    def assert_false_zero_report(self, payload: dict) -> None:
        for key in builder.FALSE_KEYS:
            self.assertIn(key, payload)
            self.assertFalse(payload[key], key)
        for key in builder.ZERO_KEYS:
            self.assertIn(key, payload)
            self.assertEqual(0, payload[key], key)

    def write_command_inputs(
        self,
        root: Path,
        *,
        promote_identity: bool = True,
        promote_permissions: bool = True,
    ) -> tuple[dict, Path, Path, Path, Path]:
        helper = self.helper()
        surfaces = helper.load_surfaces()
        if promote_identity:
            helper.promote_surface_with_certificate(
                root,
                surfaces,
                response_readiness.IDENTITY_SURFACE,
            )
        if promote_permissions:
            helper.promote_surface_with_certificate(
                root,
                surfaces,
                response_readiness.PERMISSIONS_SURFACE,
            )
        readiness_path, decisions_path, public_header_path = helper.write_inputs(root)
        surfaces_path = helper.write_surfaces(root, surfaces)
        return surfaces, surfaces_path, readiness_path, decisions_path, public_header_path

    def run_builder(
        self,
        *,
        root: Path,
        surfaces_path: Path,
        readiness_path: Path,
        decisions_path: Path,
        public_header_path: Path,
        output_certificate: Path | None = None,
        extra_args: list[str] | None = None,
        expect_returncode: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        certificate = output_certificate or root / "command-chat-response-certificate.json"
        command = [
            sys.executable,
            str(BUILDER),
            "--root",
            str(root),
            "--readiness",
            str(readiness_path),
            "--command-decisions",
            str(decisions_path),
            "--public-sdk-surfaces",
            str(surfaces_path),
            "--public-header",
            str(public_header_path),
            "--output-certificate",
            str(certificate),
        ]
        if extra_args:
            command.extend(extra_args)
        command.append("--json")
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, expect_returncode, result.stderr)
        return result, certificate

    def bridge_proof_inputs(
        self,
        *,
        decisions_path: Path,
        public_header_path: Path,
    ) -> tuple[dict, dict[str, str]]:
        kwargs = {
            "bridge_decisions_path": builder.bridge_checker.DEFAULT_DECISIONS,
            "command_decisions_path": decisions_path,
            "player_identity_decisions_path": builder.bridge_checker.DEFAULT_PLAYER_IDENTITY,
            "permissions_admin_decisions_path": builder.bridge_checker.DEFAULT_PERMISSIONS_ADMIN,
            "commands_replies_decisions_path": builder.bridge_checker.DEFAULT_COMMANDS_REPLIES,
            "public_header_path": public_header_path,
        }
        return (
            builder.command_principal_authz_response_bridge_proof(**kwargs),
            builder.bridge_source_artifact_hashes(**kwargs),
        )

    def test_builds_blocked_hash_bound_certificate_after_valid_upstream_promotions(self) -> None:
        root = self.repo_tempdir()
        surfaces, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )

        result, certificate = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
        )

        report = json.loads(result.stdout)
        self.assertEqual(
            "obelisk.command-chat-response-path-promotion-certificate-build-report.v1",
            report["schema"],
        )
        self.assertEqual("built", report["status"])
        self.assertEqual([], report["blockers"])
        self.assertTrue(report["command_chat_response_public_readiness_valid"])
        self.assertTrue(
            report["command_chat_response_public_readiness_accepted_for_planning"]
        )
        self.assert_false_zero_report(report)
        self.assertTrue(certificate.exists())
        self.assertEqual(report_file_sha256(certificate), report["certificate_sha256"])
        self.assertEqual(
            {
                "path": str(certificate.relative_to(REPO_ROOT)),
                "sha256": report_file_sha256(certificate),
            },
            report["certificate_binding"],
        )

        payload = json.loads(certificate.read_text(encoding="utf-8"))
        self.assertEqual(
            "obelisk.command-chat-response-path-promotion-certificate.v1",
            payload["schema"],
        )
        self.assertEqual(response_readiness.SURFACE, payload["surface_id"])
        self.assertEqual("blocked_approved_runtime_evidence_missing", payload["promotion_status"])
        self.assertEqual("approved_runtime_evidence_missing", payload["route_blocker_to_use"])
        self.assertEqual(
            response_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH,
            payload["required_reviewed_artifact_hash"],
        )
        self.assertEqual(
            response_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY,
            payload["reviewed_artifact_hash_policy"],
        )
        self.assertFalse(payload["missing_mismatched_or_stale_certificate_counts"])
        self.assert_false_zero_report(payload)
        self.assert_false_zero_report(payload["evidence"])

        response_surface = next(
            item
            for item in surfaces["surfaces"]
            if item["id"] == response_readiness.SURFACE
        )
        expected_surface_hash = response_readiness.surface_record_sha256(
            response_surface,
            builder.CERTIFICATE_KEY,
        )
        self.assertEqual(
            expected_surface_hash,
            payload["evidence"]["reviewed_surface_record_sha256"],
        )
        self.assertEqual(
            expected_surface_hash,
            payload["evidence"]["reviewed_artifact_hash"],
        )
        self.assertEqual(
            report_file_sha256(surfaces_path),
            payload["input_bindings"]["public_sdk_surfaces"]["sha256"],
        )
        self.assertEqual(
            report_file_sha256(readiness_path),
            payload["input_bindings"]["command_chat_response_public_readiness"]["sha256"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate",
            payload["input_bindings"],
        )
        self.assertIn(
            "command_principal_authz_response_bridge_proof",
            payload["input_bindings"],
        )
        self.assertTrue(
            payload["evidence"]["command_principal_authz_response_bridge_proof_validated"]
        )
        self.assertIn(
            "generated certificate reports; reviewed templates; package shape; beta notices stay blocked substitutes",
            payload["evidence"]["required_fail_closed_guardrails"],
        )
        self.assertIn(
            "runtime status and status artifacts stay blocked substitutes",
            payload["evidence"]["required_fail_closed_guardrails"],
        )

    def test_canonicalizes_upstream_certificate_bindings_in_output(self) -> None:
        root = self.repo_tempdir()
        surfaces, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        for surface_id in (
            response_readiness.IDENTITY_SURFACE,
            response_readiness.PERMISSIONS_SURFACE,
        ):
            surface = next(item for item in surfaces["surfaces"] if item["id"] == surface_id)
            certificate_key = response_readiness.PROMOTION_CERTIFICATE_SPECS[surface_id][
                "certificate_key"
            ]
            surface["evidence"][certificate_key]["sha256"] = surface["evidence"][
                certificate_key
            ]["sha256"].upper()
        self.write_json(surfaces_path, surfaces)

        result, certificate = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
        )

        report = json.loads(result.stdout)
        self.assertEqual("built", report["status"])
        payload = json.loads(certificate.read_text(encoding="utf-8"))
        for surface_id in (
            response_readiness.IDENTITY_SURFACE,
            response_readiness.PERMISSIONS_SURFACE,
        ):
            surface = next(item for item in surfaces["surfaces"] if item["id"] == surface_id)
            certificate_key = response_readiness.PROMOTION_CERTIFICATE_SPECS[surface_id][
                "certificate_key"
            ]
            source_binding = surface["evidence"][certificate_key]
            canonical_binding = payload["input_bindings"][certificate_key]
            self.assertEqual(source_binding["path"], canonical_binding["path"])
            self.assertEqual(
                report_file_sha256(REPO_ROOT / source_binding["path"]),
                canonical_binding["sha256"],
            )
            self.assertNotEqual(source_binding["sha256"], canonical_binding["sha256"])
            self.assertFalse(Path(canonical_binding["path"]).is_absolute())

    def test_blocks_certificate_when_bridge_proof_has_public_runtime_alias(self) -> None:
        root = self.repo_tempdir()
        _, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        bridge_decisions = json.loads(
            builder.bridge_checker.DEFAULT_DECISIONS.read_text(encoding="utf-8")
        )
        bridge_decisions["unit_test_bridge_alias"] = {
            "response_bridge_ready": True,
            "package_shape_install_ready": True,
        }
        bridge_decisions_path = root / "command_principal_authz_response_bridge_decisions.json"
        self.write_json(bridge_decisions_path, bridge_decisions)

        result, certificate = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
            output_certificate=root / "blocked-bridge-proof-certificate.json",
            extra_args=["--bridge-decisions", str(bridge_decisions_path)],
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate.exists())
        self.assertFalse(report["command_principal_authz_response_bridge_proof_valid"])
        self.assertIn(
            "command_principal_authz_response_bridge_proof_valid_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "command_principal_authz_response_bridge_proof_child_blocker",
            report["blockers"],
        )

    def test_direct_build_revalidates_upstream_certificates(self) -> None:
        root = self.repo_tempdir()
        surfaces, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        readiness = response_readiness.build_report(
            root,
            readiness_path,
            decisions_path,
            public_header_path,
            surfaces_path,
            current_route_blocker=response_readiness.RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
        self.assertTrue(readiness["accepted_for_planning"])
        permissions = next(
            item
            for item in surfaces["surfaces"]
            if item["id"] == response_readiness.PERMISSIONS_SURFACE
        )
        permissions["evidence"]["permissions_admin_promotion_certificate"]["sha256"] = "0" * 64

        with self.assertRaisesRegex(SystemExit, "inputs failed preflight"):
            builder.build_certificate(
                surfaces=surfaces,
                surfaces_path=surfaces_path,
                readiness_path=readiness_path,
                decisions_path=decisions_path,
                public_header_path=public_header_path,
                readiness=readiness,
            )

    def test_direct_build_revalidates_current_surfaces_after_stale_readiness_report(self) -> None:
        root = self.repo_tempdir()
        surfaces, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        readiness = response_readiness.build_report(
            root,
            readiness_path,
            decisions_path,
            public_header_path,
            surfaces_path,
            current_route_blocker=response_readiness.RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
        self.assertTrue(readiness["accepted_for_planning"])

        response_surface = next(
            item
            for item in surfaces["surfaces"]
            if item["id"] == response_readiness.SURFACE
        )
        response_surface["status"] = "promoted"
        bridge_proof, bridge_hashes = self.bridge_proof_inputs(
            decisions_path=decisions_path,
            public_header_path=public_header_path,
        )

        blockers = builder.preflight_blockers(
            surfaces=surfaces,
            readiness=readiness,
            current_route_blocker=response_readiness.RUNTIME_EVIDENCE_ROUTE_BLOCKER,
            bridge_proof=bridge_proof,
            expected_bridge_source_artifact_hashes=bridge_hashes,
        )
        self.assertIn("status_mismatch", {blocker["reason"] for blocker in blockers})
        self.assertIn(
            "command_chat_response_evidence_not_approved",
            {blocker["reason"] for blocker in blockers},
        )
        with self.assertRaisesRegex(SystemExit, "inputs failed preflight"):
            builder.build_certificate(
                surfaces=surfaces,
                surfaces_path=surfaces_path,
                readiness_path=readiness_path,
                decisions_path=decisions_path,
                public_header_path=public_header_path,
                readiness=readiness,
            )

    def test_direct_build_rejects_stale_readiness_source_artifact_hashes(self) -> None:
        root = self.repo_tempdir()
        surfaces, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        readiness = response_readiness.build_report(
            root,
            readiness_path,
            decisions_path,
            public_header_path,
            surfaces_path,
            current_route_blocker=response_readiness.RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
        self.assertTrue(readiness["accepted_for_planning"])
        decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
        decisions["unit_test_stale_readiness_marker"] = "changed-after-readiness"
        self.write_json(decisions_path, decisions)

        with self.assertRaisesRegex(
            SystemExit,
            "command_chat_response_public_readiness_report_decisions_path_sha256_mismatch",
        ):
            builder.build_certificate(
                surfaces=surfaces,
                surfaces_path=surfaces_path,
                readiness_path=readiness_path,
                decisions_path=decisions_path,
                public_header_path=public_header_path,
                readiness=readiness,
            )

    def test_reports_missing_upstream_promotions_without_writing_certificate(self) -> None:
        root = self.repo_tempdir()
        _, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(
                root,
                promote_identity=False,
                promote_permissions=False,
            )
        )

        result, certificate = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate.exists())
        self.assertIn(
            "player_identity_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assertIn(
            "upstream_identity_permissions_promotions_not_satisfied",
            report["blockers"],
        )
        self.assert_false_zero_report(report)

    def test_blocked_run_does_not_bind_preexisting_output_certificate(self) -> None:
        root = self.repo_tempdir()
        _, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(
                root,
                promote_identity=False,
                promote_permissions=False,
            )
        )
        certificate = root / "preexisting-command-response-certificate.json"
        self.write_json(certificate, {"schema": "obsolete-preexisting-output"})

        result, returned_certificate = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
            output_certificate=certificate,
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual(certificate, returned_certificate)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(certificate.exists())
        self.assertFalse(report["certificate_written"])
        self.assertIsNone(report["certificate_sha256"])
        self.assertIsNone(report["certificate_binding"])
        self.assertIn(
            "player_identity_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)

    def test_reports_stale_permissions_admin_certificate_hash_without_writing(self) -> None:
        root = self.repo_tempdir()
        _, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        surfaces = json.loads(surfaces_path.read_text(encoding="utf-8"))
        permissions = next(
            item
            for item in surfaces["surfaces"]
            if item["id"] == response_readiness.PERMISSIONS_SURFACE
        )
        permissions["evidence"]["permissions_admin_promotion_certificate"]["sha256"] = "0" * 64
        self.write_json(surfaces_path, surfaces)

        result, certificate = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
            output_certificate=root / "blocked-stale-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate.exists())
        self.assertIn(
            "permissions_admin_promotion_certificate_sha256_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)

    def test_reports_identity_certificate_missing_current_review_evidence_without_writing(self) -> None:
        root = self.repo_tempdir()
        surfaces, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        identity = next(
            item
            for item in surfaces["surfaces"]
            if item["id"] == response_readiness.IDENTITY_SURFACE
        )
        certificate_key = "player_identity_promotion_certificate"
        certificate_path = REPO_ROOT / identity["evidence"][certificate_key]["path"]
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        certificate["evidence"].pop(
            "identity_public_contract_decision_record_runtime_binding",
            None,
        )
        self.rewrite_bound_certificate(
            identity,
            response_readiness.IDENTITY_SURFACE,
            certificate,
        )
        self.write_json(surfaces_path, surfaces)

        result, certificate_output = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
            output_certificate=root / "blocked-identity-review-evidence-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate_output.exists())
        self.assertIn(
            "player_identity_promotion_certificate_identity_contract_runtime_binding_missing",
            report["blockers"],
        )
        self.assertIn(
            "player_identity_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)

    def test_reports_permissions_admin_stale_input_binding_without_writing(self) -> None:
        root = self.repo_tempdir()
        surfaces, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        permissions = next(
            item
            for item in surfaces["surfaces"]
            if item["id"] == response_readiness.PERMISSIONS_SURFACE
        )
        certificate_key = "permissions_admin_promotion_certificate"
        certificate_path = REPO_ROOT / permissions["evidence"][certificate_key]["path"]
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        certificate["input_bindings"]["permissions_admin_surface_record_sha256"] = "0" * 64
        self.rewrite_bound_certificate(
            permissions,
            response_readiness.PERMISSIONS_SURFACE,
            certificate,
        )
        self.write_json(surfaces_path, surfaces)

        result, certificate_output = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
            output_certificate=root / "blocked-permissions-input-binding-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate_output.exists())
        self.assertIn(
            "permissions_admin_promotion_certificate_permissions_surface_record_sha256_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_input_binding_sha256_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)

    def test_reports_permissions_admin_certificate_payload_aliases_without_writing(self) -> None:
        root = self.repo_tempdir()
        surfaces, surfaces_path, readiness_path, decisions_path, public_header_path = (
            self.write_command_inputs(root)
        )
        permissions = next(
            item
            for item in surfaces["surfaces"]
            if item["id"] == response_readiness.PERMISSIONS_SURFACE
        )
        certificate_key = "permissions_admin_promotion_certificate"
        certificate_path = REPO_ROOT / permissions["evidence"][certificate_key]["path"]
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        certificate["identity_public_contract_gate_missing_allows_broadcast"] = True
        certificate["commands_replies_shortcut_public_response_allowed"] = True
        certificate["routeClearedForPublicSendChatAbi"] = True
        certificate["terminalCertificateReady"] = True
        certificate["evidence"]["CallProcessEventResponseShortcutAllowed"] = True
        certificate["evidence"]["approved_runtime_evidence"] = {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
            "result": "approved runtime principal lifecycle evidence",
        }
        certificate["evidence"]["response_status_report"] = {"status": "accepted"}
        certificate["evidence"]["beta_window_status"] = {"status": "ready"}
        self.rewrite_bound_certificate(
            permissions,
            response_readiness.PERMISSIONS_SURFACE,
            certificate,
        )
        self.write_json(surfaces_path, surfaces)

        result, certificate_output = self.run_builder(
            root=root,
            surfaces_path=surfaces_path,
            readiness_path=readiness_path,
            decisions_path=decisions_path,
            public_header_path=public_header_path,
            output_certificate=root / "blocked-payload-alias-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate_output.exists())
        self.assertIn(
            "permissions_admin_promotion_certificate_payload_public_surface_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_payload_route_or_runtime_readiness_alias_missing_upstream_certificates",
            report["blockers"],
        )
        blocker_labels = {
            item.get("label")
            for item in report["blocker_details"]
            if item.get("reason")
            == "permissions_admin_promotion_certificate_payload_route_or_runtime_readiness_alias_missing_upstream_certificates"
        }
        self.assertIn(
            "$.surfaces.permissions_admin.evidence.permissions_admin_promotion_certificate.routeClearedForPublicSendChatAbi",
            blocker_labels,
        )
        self.assertIn(
            "$.surfaces.permissions_admin.evidence.permissions_admin_promotion_certificate.terminalCertificateReady",
            blocker_labels,
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_payload_non_evidence_artifact_credit_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_payload_direct_identity_or_runtime_evidence_substitute",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)


def report_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
