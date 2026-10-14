#!/usr/bin/env python3
"""Tests for build_commands_replies_promotion_certificate.py."""

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
BUILDER = SCRIPT_DIR / "build_commands_replies_promotion_certificate.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_commands_replies_promotion_certificate as builder  # noqa: E402
import check_commands_replies_public_readiness as commands_readiness  # noqa: E402
import test_check_commands_replies_public_readiness as readiness_tests  # noqa: E402


class BuildCommandsRepliesPromotionCertificateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._repo_tempdirs: list[Path] = []

    def tearDown(self) -> None:
        for path in reversed(self._repo_tempdirs):
            shutil.rmtree(path, ignore_errors=True)

    def repo_tempdir(self) -> Path:
        path = Path(
            tempfile.mkdtemp(
                prefix="CommandsRepliesPromotionBuilder",
                dir=REPO_ROOT / "tests" / "core",
            )
        )
        self._repo_tempdirs.append(path)
        return path

    @staticmethod
    def helper() -> readiness_tests.CheckCommandsRepliesPublicReadinessTests:
        return readiness_tests.CheckCommandsRepliesPublicReadinessTests(
            methodName="test_accepts_current_manifests_as_planning_only"
        )

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def mutate_bound_certificate_payload(binding: dict[str, str], updates: dict) -> None:
        path = REPO_ROOT / binding["path"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.update(updates)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    def assert_false_zero_report(self, payload: dict) -> None:
        for key in builder.FALSE_KEYS:
            self.assertIn(key, payload)
            self.assertFalse(payload[key], key)
        for key in builder.ZERO_KEYS:
            self.assertIn(key, payload)
            self.assertEqual(0, payload[key], key)

    def assert_non_counting_gate(self, payload: dict) -> None:
        self.assertTrue(payload["missing_non_counting"])
        self.assertEqual(
            "commands_replies_promotion_certificate",
            payload["missing_non_counting_artifact"],
        )
        self.assertEqual(
            commands_readiness.SURFACE,
            payload["missing_non_counting_surface"],
        )
        self.assertEqual(
            commands_readiness.RESPONSE_PATH_SURFACE,
            payload["missing_non_counting_required_after_surface"],
        )
        self.assertTrue(payload["non_counting_until_present"])
        self.assertEqual(
            commands_readiness.POST_COMMAND_RESPONSE_BLOCKER,
            payload["route_gate_non_counting_blocker"],
        )
        self.assertEqual(
            "commands_replies.public_abi_and_runtime_dispatch_evidence",
            payload["route_gate_non_counting_blocker_label"],
        )
        self.assertEqual(
            commands_readiness.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
            payload["required_prior_certificate_schema"],
        )
        self.assertEqual(
            "command_response_promotion_certificate",
            payload["required_prior_certificate_key"],
        )
        self.assertEqual(
            commands_readiness.COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA,
            payload["required_terminal_artifact_schema"],
        )
        self.assertEqual(
            "commands_replies_promotion_certificate",
            payload["first_missing_terminal_artifact"],
        )
        self.assertEqual(
            commands_readiness.COMMANDS_REPLIES_PROMOTION_REQUIRED_ARTIFACT[
                "required_evidence"
            ],
            payload["required_before_counting"],
        )
        self.assertFalse(payload["manifest_promoted_but_non_counting"])
        self.assertEqual(0, payload["sdk_p0_progress_contribution"])
        self.assertEqual(0, payload["p0_dependency_chain_progress_contribution"])
        self.assertFalse(payload["terminal_artifact_shortcuts_count"])
        self.assertIn(
            f"route_gate_blocker:{commands_readiness.POST_COMMAND_RESPONSE_BLOCKER}",
            payload["non_counting_reasons"],
        )
        self.assertIn("runtime_evidence_missing", payload["non_counting_reasons"])

    def write_readiness_inputs(self, root: Path) -> tuple[Path, Path, Path, Path]:
        helper = self.helper()
        decisions_path, surfaces_path, public_header_path = helper.write_inputs(root)
        response_report_path = helper.write_response_report(
            root,
            surfaces_path=surfaces_path,
        )
        return decisions_path, surfaces_path, public_header_path, response_report_path

    def write_upstream_surfaces(
        self,
        root: Path,
        *,
        promote_response: bool = True,
    ) -> tuple[dict, Path]:
        helper = self.helper()
        surfaces = helper.load_surfaces()
        helper.promote_surface_with_certificate(
            root,
            surfaces,
            commands_readiness.DEPENDENCY_CHAIN[0],
        )
        helper.promote_surface_with_certificate(
            root,
            surfaces,
            commands_readiness.DEPENDENCY_CHAIN[1],
        )
        if promote_response:
            helper.promote_surface_with_certificate(
                root,
                surfaces,
                commands_readiness.RESPONSE_PATH_SURFACE,
            )
        path = root / "upstream-public-sdk-surfaces.json"
        self.write_json(path, surfaces)
        return surfaces, path

    def run_builder(
        self,
        *,
        root: Path,
        decisions_path: Path,
        surfaces_path: Path,
        public_header_path: Path,
        response_report_path: Path,
        upstream_surfaces_path: Path,
        output_certificate: Path | None = None,
        expect_returncode: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        certificate = output_certificate or root / "commands-replies-certificate.json"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--decisions",
                str(decisions_path),
                "--public-sdk-surfaces",
                str(surfaces_path),
                "--upstream-public-sdk-surfaces",
                str(upstream_surfaces_path),
                "--public-header",
                str(public_header_path),
                "--response-path-report",
                str(response_report_path),
                "--response-path-root",
                str(root),
                "--response-path-readiness",
                str(root / "command-chat-response-route-planning-readiness.json"),
                "--response-path-report-root",
                str(root),
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

    def test_builds_blocked_hash_bound_certificate_after_valid_command_response(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
        )

        report = json.loads(result.stdout)
        self.assertEqual(
            "obelisk.commands-replies-promotion-certificate-build-report.v1",
            report["schema"],
        )
        self.assertEqual("built", report["status"])
        self.assertEqual([], report["blockers"])
        self.assertTrue(report["certificate_written"])
        self.assertEqual(str(certificate.relative_to(REPO_ROOT)), report["certificate_path"])
        self.assertTrue(report["commands_replies_public_readiness_valid"])
        self.assertTrue(report["commands_replies_public_readiness_accepted_for_planning"])
        self.assertTrue(report["upstream_command_response_promotion_certificate_valid"])
        self.assertTrue(report["upstream_promotion_chain_valid"])
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)
        self.assert_non_counting_gate(report["non_counting_route_gate"])
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
            "obelisk.commands-replies-promotion-certificate.v1",
            payload["schema"],
        )
        self.assertEqual(commands_readiness.SURFACE, payload["surface_id"])
        self.assertEqual(
            "blocked_copied_command_payload_public_abi_contract",
            payload["promotion_status"],
        )
        self.assertEqual(
            "copied_command_payload_public_abi_contract",
            payload["route_blocker_to_use"],
        )
        self.assertEqual(
            commands_readiness.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
            payload["required_prior_certificate_schema"],
        )
        self.assertEqual(
            commands_readiness.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH,
            payload["required_reviewed_artifact_hash"],
        )
        self.assertFalse(payload["missing_mismatched_or_stale_certificate_counts"])
        self.assert_false_zero_report(payload)
        self.assert_false_zero_report(payload["evidence"])
        self.assert_non_counting_gate(payload)
        self.assert_non_counting_gate(payload["evidence"])
        self.assert_non_counting_gate(payload["non_counting_route_gate"])
        self.assert_non_counting_gate(payload["unresolved_technical_blocker"])

        readiness_surfaces = json.loads(surfaces_path.read_text(encoding="utf-8"))
        commands_surface = next(
            item
            for item in readiness_surfaces["surfaces"]
            if item["id"] == commands_readiness.SURFACE
        )
        expected_surface_hash = commands_readiness.surface_record_sha256(
            commands_surface,
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
            report_file_sha256(upstream_surfaces_path),
            payload["input_bindings"]["upstream_public_sdk_surfaces"]["sha256"],
        )
        self.assertEqual(
            payload["input_bindings"]["current_command_response_surface_contract_sha256"],
            payload["input_bindings"]["upstream_command_response_surface_contract_sha256"],
        )
        self.assertIn(
            "command_response_promotion_certificate",
            payload["input_bindings"],
        )
        self.assertIn(
            "player_identity_promotion_certificate",
            payload["input_bindings"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate",
            payload["input_bindings"],
        )

        response_surface = next(
            item
            for item in upstream_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        self.assertEqual(
            response_surface["evidence"]["command_response_promotion_certificate"],
            payload["input_bindings"]["command_response_promotion_certificate"],
        )

    def test_canonicalizes_upstream_certificate_bindings_in_output(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        response_surface = next(
            item
            for item in upstream_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        response_binding = response_surface["evidence"]["command_response_promotion_certificate"]
        response_binding["sha256"] = response_binding["sha256"].upper()
        self.write_json(upstream_surfaces_path, upstream_surfaces)

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
        )

        report = json.loads(result.stdout)
        self.assertEqual("built", report["status"])
        payload = json.loads(certificate.read_text(encoding="utf-8"))
        canonical_binding = payload["input_bindings"]["command_response_promotion_certificate"]
        self.assertEqual(response_binding["path"], canonical_binding["path"])
        self.assertEqual(
            report_file_sha256(REPO_ROOT / response_binding["path"]),
            canonical_binding["sha256"],
        )
        self.assertNotEqual(response_binding["sha256"], canonical_binding["sha256"])
        self.assertFalse(Path(canonical_binding["path"]).is_absolute())

    def test_direct_build_rejects_current_but_unaccepted_readiness_report(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        readiness_surfaces = json.loads(surfaces_path.read_text(encoding="utf-8"))
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        readiness = commands_readiness.build_report(
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_path_report_path=response_report_path,
            response_path_root=root,
            response_path_readiness=(
                root / "command-chat-response-route-planning-readiness.json"
            ),
            response_path_report_root=root,
            current_route_blocker=commands_readiness.RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
        self.assertTrue(readiness["valid"])
        readiness["accepted_for_planning"] = False

        with self.assertRaisesRegex(SystemExit, "inputs failed preflight"):
            builder.build_certificate(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                upstream_surfaces_path=upstream_surfaces_path,
                public_header_path=public_header_path,
                response_path_report_path=response_report_path,
                response_path_readiness=(
                    root / "command-chat-response-route-planning-readiness.json"
                ),
                readiness=readiness,
                readiness_surfaces=readiness_surfaces,
                upstream_surfaces=upstream_surfaces,
            )

    def test_direct_build_rejects_stale_readiness_source_artifact_hashes(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        readiness_surfaces = json.loads(surfaces_path.read_text(encoding="utf-8"))
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        response_path_readiness = root / "command-chat-response-route-planning-readiness.json"
        readiness = commands_readiness.build_report(
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_path_report_path=response_report_path,
            response_path_root=root,
            response_path_readiness=response_path_readiness,
            response_path_report_root=root,
            current_route_blocker=commands_readiness.RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
        self.assertTrue(readiness["accepted_for_planning"])
        decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
        decisions["unit_test_stale_readiness_marker"] = "changed-after-readiness"
        self.write_json(decisions_path, decisions)

        with self.assertRaisesRegex(
            SystemExit,
            "commands_replies_public_readiness_report_decisions_path_sha256_mismatch",
        ):
            builder.build_certificate(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                upstream_surfaces_path=upstream_surfaces_path,
                public_header_path=public_header_path,
                response_path_report_path=response_report_path,
                response_path_readiness=response_path_readiness,
                readiness=readiness,
                readiness_surfaces=readiness_surfaces,
                upstream_surfaces=upstream_surfaces,
            )

    def test_reports_missing_command_response_certificate_without_writing(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        _, upstream_surfaces_path = self.write_upstream_surfaces(
            root,
            promote_response=False,
        )

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(report["certificate_written"])
        self.assertIsNone(report["certificate_sha256"])
        self.assertIsNone(report["certificate_binding"])
        self.assertFalse(certificate.exists())
        self.assertFalse(report["upstream_command_response_promotion_certificate_valid"])
        self.assertFalse(report["upstream_promotion_chain_valid"])
        self.assertIn(
            "command_response_promotion_certificate_surface_not_promoted",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)
        self.assert_non_counting_gate(report["non_counting_route_gate"])

    def test_reports_stale_command_response_certificate_hash_without_writing(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        response_surface = next(
            item
            for item in upstream_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        response_surface["evidence"]["command_response_promotion_certificate"]["sha256"] = "0" * 64
        self.write_json(upstream_surfaces_path, upstream_surfaces)

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-stale-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(report["certificate_written"])
        self.assertIsNone(report["certificate_sha256"])
        self.assertIsNone(report["certificate_binding"])
        self.assertFalse(certificate.exists())
        self.assertFalse(report["upstream_command_response_promotion_certificate_valid"])
        self.assertFalse(report["upstream_promotion_chain_valid"])
        self.assertIn(
            "command_response_promotion_certificate_sha256_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)
        self.assert_non_counting_gate(report["non_counting_route_gate"])

    def test_reports_upstream_response_certificate_not_bound_to_current_surface_without_writing(self) -> None:
        root = self.repo_tempdir()
        helper = self.helper()
        current_surfaces = helper.load_surfaces()
        current_response = next(
            item
            for item in current_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        current_response["unit_test_current_surface_contract_revision"] = (
            "blocked-current-revision"
        )
        decisions_path, surfaces_path, public_header_path = helper.write_inputs(
            root,
            surfaces=current_surfaces,
        )
        response_report_path = helper.write_response_report(
            root,
            surfaces_path=surfaces_path,
        )
        _, upstream_surfaces_path = self.write_upstream_surfaces(root)

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-current-surface-mismatch.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate.exists())
        self.assertFalse(report["certificate_written"])
        self.assertIn(
            "command_response_promotion_certificate_current_surface_record_mismatch",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)

    def test_rejects_invalid_upstream_command_response_certificate_binding_without_writing(self) -> None:
        cases = (
            ("absolute_path", lambda binding: str((REPO_ROOT / binding["path"]).resolve()), "command_response_promotion_certificate_path_invalid"),
            ("parent_relative_path", lambda binding: f"../{binding['path']}", "command_response_promotion_certificate_path_invalid"),
            ("extra_status", None, "command_response_promotion_certificate_binding_keys_mismatch"),
        )
        for case_name, path_value, expected_reason in cases:
            with self.subTest(case=case_name):
                root = self.repo_tempdir()
                decisions_path, surfaces_path, public_header_path, response_report_path = (
                    self.write_readiness_inputs(root)
                )
                upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
                response_surface = next(
                    item
                    for item in upstream_surfaces["surfaces"]
                    if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
                )
                binding = response_surface["evidence"]["command_response_promotion_certificate"]
                if path_value is None:
                    binding["status"] = "ready"
                else:
                    binding["path"] = path_value(binding)
                self.write_json(upstream_surfaces_path, upstream_surfaces)

                result, certificate = self.run_builder(
                    root=root,
                    decisions_path=decisions_path,
                    surfaces_path=surfaces_path,
                    public_header_path=public_header_path,
                    response_report_path=response_report_path,
                    upstream_surfaces_path=upstream_surfaces_path,
                    output_certificate=root / f"blocked-{case_name}.json",
                    expect_returncode=1,
                )

                report = json.loads(result.stdout)
                self.assertEqual("blocked", report["status"])
                self.assertFalse(certificate.exists())
                self.assertFalse(report["certificate_written"])
                self.assertIn(expected_reason, report["blockers"])
                self.assertIn(
                    "command_response_promotion_certificate_missing_or_invalid",
                    report["blockers"],
                )
                self.assert_false_zero_report(report)
                self.assert_non_counting_gate(report)

    def test_rejects_upstream_command_response_certificate_builder_report_payload_without_writing(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        response_surface = next(
            item
            for item in upstream_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        binding = response_surface["evidence"]["command_response_promotion_certificate"]
        self.mutate_bound_certificate_payload(
            binding,
            {
                "certificate_builder_report": {
                    "schema": "obelisk.command-chat-response-path-promotion-certificate-build-report.v1",
                    "certificate_written": True,
                    "certificate_binding": dict(binding),
                }
            },
        )
        self.write_json(upstream_surfaces_path, upstream_surfaces)

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-builder-report-payload.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate.exists())
        self.assertFalse(report["certificate_written"])
        self.assertIn(
            "command_response_promotion_certificate_builder_report_not_certificate",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)

    def test_rejects_upstream_command_response_certificate_status_beta_header_alias_payload_without_writing(self) -> None:
        cases = (
            (
                "status_report_ready",
                {"status_report_ready": True},
                "command_response_promotion_certificate_payload_public_surface_overclaim",
            ),
            (
                "beta_capture_pack_ready",
                {"beta_capture_pack_ready": True},
                "command_response_promotion_certificate_payload_public_surface_overclaim",
            ),
            (
                "public_header_allowed",
                {"public_header_allowed": True},
                "command_response_promotion_certificate_payload_public_surface_overclaim",
            ),
            (
                "route_gate_ready",
                {"route_gate_ready": True},
                "command_response_promotion_certificate_payload_public_surface_overclaim",
            ),
            (
                "route_cleared_for_public_send_chat_abi",
                {"routeClearedForPublicSendChatAbi": True},
                "command_response_promotion_certificate_payload_route_or_runtime_readiness_alias_missing_upstream_certificates",
            ),
            (
                "terminal_certificate_ready",
                {"terminalCertificateReady": True},
                "command_response_promotion_certificate_payload_route_or_runtime_readiness_alias_missing_upstream_certificates",
            ),
            (
                "response_status_report_accepted",
                {"response_status_report": {"status": "accepted"}},
                "command_response_promotion_certificate_payload_route_or_runtime_readiness_alias_missing_upstream_certificates",
            ),
            (
                "package_shape_artifact",
                {
                    "package_shape_artifact": {
                        "artifact_class": "package_shape",
                        "status": "ready",
                    },
                },
                "command_response_promotion_certificate_payload_non_evidence_artifact_credit_overclaim",
            ),
        )
        for alias_key, updates, expected_blocker in cases:
            with self.subTest(alias_key=alias_key):
                root = self.repo_tempdir()
                decisions_path, surfaces_path, public_header_path, response_report_path = (
                    self.write_readiness_inputs(root)
                )
                upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
                response_surface = next(
                    item
                    for item in upstream_surfaces["surfaces"]
                    if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
                )
                binding = response_surface["evidence"]["command_response_promotion_certificate"]
                self.mutate_bound_certificate_payload(binding, updates)
                self.write_json(upstream_surfaces_path, upstream_surfaces)

                result, certificate = self.run_builder(
                    root=root,
                    decisions_path=decisions_path,
                    surfaces_path=surfaces_path,
                    public_header_path=public_header_path,
                    response_report_path=response_report_path,
                    upstream_surfaces_path=upstream_surfaces_path,
                    output_certificate=root / f"blocked-{alias_key}.json",
                    expect_returncode=1,
                )

                report = json.loads(result.stdout)
                self.assertEqual("blocked", report["status"])
                self.assertFalse(certificate.exists())
                self.assertFalse(report["certificate_written"])
                self.assertIn(expected_blocker, report["blockers"])
                self.assertIn(
                    "command_response_promotion_certificate_missing_or_invalid",
                    report["blockers"],
                )
                self.assert_false_zero_report(report)
                self.assert_non_counting_gate(report)

    def test_reports_stale_identity_or_permissions_certificate_without_writing(self) -> None:
        cases = (
            (
                commands_readiness.DEPENDENCY_CHAIN[0],
                "player_identity_promotion_certificate_surface_record_sha256_mismatch",
                "player_identity_promotion_certificate_missing_or_invalid",
            ),
            (
                commands_readiness.DEPENDENCY_CHAIN[1],
                "permissions_admin_promotion_certificate_surface_record_sha256_mismatch",
                "permissions_admin_promotion_certificate_missing_or_invalid",
            ),
        )
        for surface_id, stale_blocker, invalid_blocker in cases:
            with self.subTest(surface_id=surface_id):
                root = self.repo_tempdir()
                decisions_path, surfaces_path, public_header_path, response_report_path = (
                    self.write_readiness_inputs(root)
                )
                upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
                surface = next(
                    item for item in upstream_surfaces["surfaces"] if item["id"] == surface_id
                )
                surface.setdefault("evidence", {})["unit_test_post_certificate_marker"] = (
                    "non_authorizing_marker"
                )
                self.write_json(upstream_surfaces_path, upstream_surfaces)

                result, certificate = self.run_builder(
                    root=root,
                    decisions_path=decisions_path,
                    surfaces_path=surfaces_path,
                    public_header_path=public_header_path,
                    response_report_path=response_report_path,
                    upstream_surfaces_path=upstream_surfaces_path,
                    output_certificate=root / f"blocked-{surface_id.rsplit('.', 1)[1]}.json",
                    expect_returncode=1,
                )

                report = json.loads(result.stdout)
                self.assertEqual("blocked", report["status"])
                self.assertFalse(report["certificate_written"])
                self.assertIsNone(report["certificate_sha256"])
                self.assertIsNone(report["certificate_binding"])
                self.assertFalse(certificate.exists())
                self.assertFalse(report["upstream_promotion_chain_valid"])
                self.assertIn(stale_blocker, report["blockers"])
                self.assertIn(invalid_blocker, report["blockers"])
                self.assert_false_zero_report(report)
                self.assert_non_counting_gate(report)

    def test_reports_hash_bound_upstream_certificate_missing_current_internals_without_writing(self) -> None:
        cases = (
            (
                commands_readiness.DEPENDENCY_CHAIN[0],
                "player_identity_promotion_certificate",
                lambda certificate: certificate["evidence"].pop(
                    "approved_runtime_evidence",
                    None,
                ),
                "player_identity_promotion_certificate_approved_runtime_evidence_mismatch",
                "player_identity_promotion_certificate_missing_or_invalid",
            ),
            (
                commands_readiness.DEPENDENCY_CHAIN[1],
                "permissions_admin_promotion_certificate",
                lambda certificate: certificate["input_bindings"].pop(
                    "permissions_admin_query_failclosed_contract",
                    None,
                ),
                "permissions_admin_promotion_certificate_input_bindings_keys_mismatch",
                "permissions_admin_promotion_certificate_missing_or_invalid",
            ),
        )
        for surface_id, certificate_key, mutate, expected_reason, invalid_reason in cases:
            with self.subTest(surface_id=surface_id):
                root = self.repo_tempdir()
                decisions_path, surfaces_path, public_header_path, response_report_path = (
                    self.write_readiness_inputs(root)
                )
                upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
                surface = next(
                    item for item in upstream_surfaces["surfaces"] if item["id"] == surface_id
                )
                binding = surface["evidence"][certificate_key]
                certificate_path = REPO_ROOT / binding["path"]
                certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
                mutate(certificate)
                certificate_path.write_text(
                    json.dumps(certificate, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                binding["sha256"] = hashlib.sha256(certificate_path.read_bytes()).hexdigest()
                self.write_json(upstream_surfaces_path, upstream_surfaces)

                result, certificate_output = self.run_builder(
                    root=root,
                    decisions_path=decisions_path,
                    surfaces_path=surfaces_path,
                    public_header_path=public_header_path,
                    response_report_path=response_report_path,
                    upstream_surfaces_path=upstream_surfaces_path,
                    output_certificate=root / f"blocked-{certificate_key}-internals.json",
                    expect_returncode=1,
                )

                report = json.loads(result.stdout)
                self.assertEqual("blocked", report["status"])
                self.assertFalse(certificate_output.exists())
                self.assertFalse(report["certificate_written"])
                self.assertFalse(report["upstream_promotion_chain_valid"])
                self.assertIn(expected_reason, report["blockers"])
                self.assertIn(invalid_reason, report["blockers"])
                self.assert_false_zero_report(report)
                self.assert_non_counting_gate(report)

    def test_reports_command_response_certificate_bound_to_stale_permissions_certificate_without_writing(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        response_surface = next(
            item
            for item in upstream_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        binding = response_surface["evidence"]["command_response_promotion_certificate"]
        certificate_path = REPO_ROOT / binding["path"]
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        certificate["input_bindings"]["permissions_admin_promotion_certificate"]["sha256"] = "0" * 64
        certificate_path.write_text(
            json.dumps(certificate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        binding["sha256"] = hashlib.sha256(certificate_path.read_bytes()).hexdigest()
        self.write_json(upstream_surfaces_path, upstream_surfaces)

        result, certificate_output = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-stale-upstream-binding.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(report["certificate_written"])
        self.assertFalse(certificate_output.exists())
        self.assertFalse(report["upstream_command_response_promotion_certificate_valid"])
        self.assertFalse(report["upstream_promotion_chain_valid"])
        self.assertIn(
            "command_response_promotion_certificate_current_permissions_admin_certificate_binding_missing_or_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)

    def test_reports_command_response_certificate_evidence_only_upstream_summaries_without_writing(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        response_surface = next(
            item
            for item in upstream_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        binding = response_surface["evidence"]["command_response_promotion_certificate"]
        certificate_path = REPO_ROOT / binding["path"]
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        input_bindings = certificate.pop("input_bindings")
        certificate["evidence"]["player_identity_promotion_certificate"] = dict(
            input_bindings["player_identity_promotion_certificate"]
        )
        certificate["evidence"]["permissions_admin_promotion_certificate"] = dict(
            input_bindings["permissions_admin_promotion_certificate"]
        )
        certificate_path.write_text(
            json.dumps(certificate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        binding["sha256"] = hashlib.sha256(certificate_path.read_bytes()).hexdigest()
        self.write_json(upstream_surfaces_path, upstream_surfaces)

        result, certificate_output = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-evidence-only-upstream-summaries.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(report["certificate_written"])
        self.assertFalse(certificate_output.exists())
        self.assertFalse(report["upstream_command_response_promotion_certificate_valid"])
        self.assertFalse(report["upstream_promotion_chain_valid"])
        self.assertIn(
            "command_response_promotion_certificate_input_bindings_missing",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_current_permissions_admin_certificate_binding_missing_or_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)

    def test_rejects_summary_only_response_path_report_without_writing(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, _response_report_path = (
            self.write_readiness_inputs(root)
        )
        _, upstream_surfaces_path = self.write_upstream_surfaces(root)
        response_report_path = self.helper().write_summary_response_report(root)

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-summary-only-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(report["certificate_written"])
        self.assertIsNone(report["certificate_sha256"])
        self.assertIsNone(report["certificate_binding"])
        self.assertFalse(certificate.exists())
        self.assertFalse(report["commands_replies_public_readiness_valid"])
        self.assertIn("response_path_report_source_artifacts_missing", report["blockers"])
        self.assertIn(
            "commands_replies_readiness_not_accepted_for_planning",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)

    def test_rejects_inline_command_response_certificate_without_writing(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        helper = self.helper()
        response_surface = next(
            item
            for item in upstream_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        response_surface["evidence"]["command_response_promotion_certificate"] = (
            helper.inline_promotion_certificate(
                response_surface,
                commands_readiness.RESPONSE_PATH_SURFACE,
            )
        )
        self.write_json(upstream_surfaces_path, upstream_surfaces)

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-inline-certificate.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate.exists())
        self.assertFalse(report["certificate_written"])
        self.assertIn(
            "command_response_promotion_certificate_inline_certificate_not_hash_bound",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)

    def test_rejects_upstream_builder_report_shortcut_without_writing(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        upstream_surfaces, upstream_surfaces_path = self.write_upstream_surfaces(root)
        response_surface = next(
            item
            for item in upstream_surfaces["surfaces"]
            if item["id"] == commands_readiness.RESPONSE_PATH_SURFACE
        )
        response_surface["evidence"]["promotion_certificate_builder_report"] = {
            "schema": "obelisk.command-chat-response-path-promotion-certificate-build-report.v1",
            "certificate_binding": response_surface["evidence"][
                "command_response_promotion_certificate"
            ],
            "promotion_status": "promoted",
            "sdk_progress": 1,
        }
        self.write_json(upstream_surfaces_path, upstream_surfaces)

        result, certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
            output_certificate=root / "blocked-builder-report-shortcut.json",
            expect_returncode=1,
        )

        report = json.loads(result.stdout)
        self.assertEqual("blocked", report["status"])
        self.assertFalse(certificate.exists())
        self.assertFalse(report["certificate_written"])
        self.assertIn(
            "promotion_certificate_metadata_missing_required_upstream_certificates",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assertTrue(
            any(
                detail["reason"]
                == "promotion_certificate_metadata_missing_required_upstream_certificates"
                and detail["label"].endswith(".evidence.promotion_certificate_builder_report")
                for detail in report["blocker_details"]
            ),
            report["blocker_details"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)

    def test_blocked_run_does_not_bind_preexisting_output_certificate(self) -> None:
        root = self.repo_tempdir()
        decisions_path, surfaces_path, public_header_path, response_report_path = (
            self.write_readiness_inputs(root)
        )
        _, upstream_surfaces_path = self.write_upstream_surfaces(
            root,
            promote_response=False,
        )
        certificate = root / "preexisting-certificate.json"
        certificate.write_text(
            json.dumps({"schema": builder.CERTIFICATE_SCHEMA}) + "\n",
            encoding="utf-8",
        )

        result, returned_certificate = self.run_builder(
            root=root,
            decisions_path=decisions_path,
            surfaces_path=surfaces_path,
            public_header_path=public_header_path,
            response_report_path=response_report_path,
            upstream_surfaces_path=upstream_surfaces_path,
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
            "command_response_promotion_certificate_missing_or_invalid",
            report["blockers"],
        )
        self.assert_false_zero_report(report)
        self.assert_non_counting_gate(report)


def report_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
