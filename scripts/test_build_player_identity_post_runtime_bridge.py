#!/usr/bin/env python3
"""Tests for build_player_identity_post_runtime_bridge.py."""

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
BRIDGE = SCRIPT_DIR / "build_player_identity_post_runtime_bridge.py"
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

import test_build_player_identity_runtime_principal_lifecycle_evidence_bundle as bundle_test  # noqa: E402
import build_player_identity_post_runtime_bridge as bridge_builder  # noqa: E402


class BuildPlayerIdentityPostRuntimeBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._repo_tempdirs: list[Path] = []
        self.patch_runtime_checker_roots()

    def tearDown(self) -> None:
        for path in reversed(self._repo_tempdirs):
            shutil.rmtree(path, ignore_errors=True)

    def patch_runtime_checker_roots(self) -> None:
        for module in (
            bridge_builder.certificate_builder.approved_runtime_checker,
            bridge_builder.decision_builder.approved_runtime_checker,
        ):
            module.APPROVED_OFFLINE_WORKSPACE_ROOTS = (SAFE_OFFLINE_WORKSPACE,)
            module.window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = (
                SAFE_OFFLINE_WORKSPACE,
            )

    def repo_tempdir(self) -> Path:
        path = Path(
            tempfile.mkdtemp(
                prefix="PlayerIdentityPostRuntimeBridge",
                dir=REPO_ROOT / "tests" / "core",
            )
        )
        self._repo_tempdirs.append(path)
        return path

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def bridge_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(approved_runtime_safe_test_env())
        return env

    def bundle_bridge_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"
        env["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(bundle_test.SAFE_OFFLINE_WORKSPACE)
        return env

    def write_permissions_decisions_with_route_blocker(self, root: Path, blocker: str) -> Path:
        decisions = json.loads(PERMISSIONS_DECISIONS.read_text(encoding="utf-8"))
        decisions["accounting_lock"]["current_route_blocker"] = blocker
        decisions["accounting_lock"]["remaining_route_blockers"] = [blocker]
        path = root / "permissions-admin-decisions.json"
        self.write_json(path, decisions)
        return path

    def run_bridge(
        self,
        *args: str,
        expect_returncode: int = 0,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(BRIDGE), *args, "--json"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env or self.bridge_env(),
            check=False,
        )
        self.assertEqual(result.returncode, expect_returncode, result.stderr)
        return result

    def strict_report_for(self, runtime_path: Path) -> dict:
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
            env=self.bridge_env(),
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def write_runtime_inputs(self, root: Path) -> tuple[Path, Path]:
        runtime_path = root / "approved-runtime-principal-lifecycle-evidence.json"
        strict_report_path = root / "approved-runtime-principal-lifecycle-evidence.check.json"
        self.write_json(runtime_path, approved_runtime_manifest())
        self.write_json(strict_report_path, self.strict_report_for(runtime_path))
        return runtime_path, strict_report_path

    def test_builds_decision_certificate_and_surfaces_from_explicit_runtime_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            runtime_path, strict_report_path = self.write_runtime_inputs(temp_dir)
            output_dir = self.repo_tempdir()

            result = self.run_bridge(
                "--approved-runtime-evidence",
                str(runtime_path),
                "--strict-approved-runtime-check-report",
                str(strict_report_path),
                "--output-dir",
                str(output_dir),
            )

        report = json.loads(result.stdout)
        self.assertEqual(
            report["schema"],
            "obelisk.player-identity-post-runtime-bridge-build-report.v1",
        )
        self.assertEqual(report["status"], "built")
        self.assertNotIn("promotion_status", report)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)
        self.assertEqual(
            report["bridge_binding_checks"],
            {
                "certificate_bound_to_full_decision_record_artifact": True,
                "certificate_bound_to_decision_record_summary": True,
                "certificate_bound_to_decision_record_approved_runtime_binding": True,
                "certificate_post_runtime_bridge_constraints": True,
                "decision_record_accepted_for_contract_review": True,
                "decision_record_bound_to_approved_runtime_evidence": True,
                "decision_record_bound_to_strict_report": True,
                "strict_report_replayed": True,
            },
        )

        artifacts = report["generated_artifacts"]
        decision_record = Path(artifacts["decision_record"]["path"])
        certificate = Path(artifacts["player_identity_certificate"]["path"])
        surfaces = Path(artifacts["surfaces"]["path"])
        for path in (decision_record, certificate, surfaces):
            self.assertTrue(path.is_file(), path)

        certificate_payload = json.loads(certificate.read_text(encoding="utf-8"))
        self.assertEqual(certificate_payload["promotion_status"], "promoted")
        self.assertEqual(
            certificate_payload["post_runtime_bridge_constraints"],
            bridge_builder.certificate_builder.POST_RUNTIME_BRIDGE_CONSTRAINTS,
        )
        self.assertEqual(
            certificate_payload["evidence"]["post_runtime_bridge_constraints"],
            bridge_builder.certificate_builder.POST_RUNTIME_BRIDGE_CONSTRAINTS,
        )
        decision_record_payload = json.loads(decision_record.read_text(encoding="utf-8"))
        decision_record_artifact = certificate_payload["evidence"][
            "identity_public_contract_decision_record_artifact"
        ]
        self.assertEqual(
            decision_record_artifact["schema"],
            bridge_builder.certificate_builder.DECISION_RECORD_ARTIFACT_BINDING_SCHEMA,
        )
        self.assertNotIn("path", decision_record_artifact)
        self.assertEqual(
            decision_record_artifact["sha256"],
            bridge_builder.sha256_file(decision_record),
        )
        self.assertEqual(
            certificate_payload["evidence"][
                "identity_public_contract_decision_record_payload_sha256"
            ],
            bridge_builder.permissions_readiness.canonical_json_sha256(
                decision_record_payload
            ),
        )
        self.assertEqual(
            report["post_runtime_bridge_constraints"],
            bridge_builder.certificate_builder.POST_RUNTIME_BRIDGE_CONSTRAINTS,
        )
        runtime_binding = certificate_payload["evidence"][
            "identity_public_contract_decision_record_runtime_binding"
        ]
        self.assertEqual(
            runtime_binding["schema"],
            bridge_builder.certificate_builder.DECISION_RUNTIME_BINDING_DIGEST_SCHEMA,
        )
        self.assertEqual(
            runtime_binding["policy"],
            bridge_builder.certificate_builder.DECISION_RUNTIME_BINDING_DIGEST_POLICY,
        )
        self.assertEqual(
            runtime_binding["decision_record_approved_runtime_evidence_binding_sha256"],
            runtime_binding["approved_runtime_evidence_binding_sha256"],
        )
        decisions = self.write_permissions_decisions_with_route_blocker(
            output_dir,
            "public_header_gate_missing",
        )
        checked = subprocess.run(
            [
                sys.executable,
                str(PERMISSIONS_CHECKER),
                "--decisions",
                str(decisions),
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
        self.assertFalse(permissions_report["public_sdk_ready"])
        self.assertFalse(permissions_report["runtime_ready"])

    def test_builds_from_checked_evidence_dir(self) -> None:
        helper = bundle_test.BuildRuntimePrincipalLifecycleEvidenceBundleTests()
        with helper.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = bundle_test.copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(bundle_test.runtime_log_lines()) + "\n", encoding="utf-8")
            window_manifest = helper.write_window_manifest(temp_dir, copied_log)
            bundle = helper.run_bundle(
                copied_log,
                copied_log.parent / "approved-bundle",
                window_manifest=window_manifest,
            )
            self.assertEqual(bundle.returncode, 0, bundle.stderr)
            output_dir = self.repo_tempdir()

            result = self.run_bridge(
                "--evidence-dir",
                str(copied_log.parent),
                "--output-dir",
                str(output_dir),
                env=self.bundle_bridge_env(),
            )

        report = json.loads(result.stdout)
        self.assertTrue(Path(report["generated_artifacts"]["decision_record"]["path"]).is_file())
        self.assertTrue(Path(report["generated_artifacts"]["player_identity_certificate"]["path"]).is_file())
        self.assertTrue(Path(report["generated_artifacts"]["surfaces"]["path"]).is_file())
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_unaccepted_evidence_dir_before_writing_outputs(self) -> None:
        helper = bundle_test.BuildRuntimePrincipalLifecycleEvidenceBundleTests()
        with helper.temp_offline_workspace() as temp:
            temp_dir = Path(temp)
            copied_log = bundle_test.copied_log_path(temp_dir)
            copied_log.parent.mkdir(parents=True, exist_ok=True)
            copied_log.write_text("\n".join(bundle_test.runtime_log_lines()) + "\n", encoding="utf-8")
            helper.write_window_manifest(temp_dir, copied_log)
            output_dir = self.repo_tempdir()
            result = self.run_bridge(
                "--evidence-dir",
                str(copied_log.parent),
                "--output-dir",
                str(output_dir),
                expect_returncode=1,
                env=self.bundle_bridge_env(),
            )

        self.assertIn("checker-accepted approved runtime evidence", result.stderr)
        self.assertFalse((output_dir / "reviewed-identity-public-contract-decision-record.json").exists())
        self.assertFalse((output_dir / "player-identity-promotion-certificate.json").exists())

    def test_rejects_output_dir_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            runtime_path, strict_report_path = self.write_runtime_inputs(temp_dir)
            result = self.run_bridge(
                "--approved-runtime-evidence",
                str(runtime_path),
                "--strict-approved-runtime-check-report",
                str(strict_report_path),
                "--output-dir",
                str(temp_dir / "outside-repo"),
                expect_returncode=1,
            )

        self.assertIn("--output-dir must be under the Obelisk repo root", result.stderr)

    def test_rejects_stale_strict_checker_report_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            runtime_path, strict_report_path = self.write_runtime_inputs(temp_dir)
            strict_report = json.loads(strict_report_path.read_text(encoding="utf-8"))
            strict_report["consumer_boundary_assertions"] = []
            self.write_json(strict_report_path, strict_report)
            output_dir = self.repo_tempdir()

            result = self.run_bridge(
                "--approved-runtime-evidence",
                str(runtime_path),
                "--strict-approved-runtime-check-report",
                str(strict_report_path),
                "--output-dir",
                str(output_dir),
                expect_returncode=1,
            )

        self.assertIn("stale or not bound", result.stderr)
        self.assertFalse((output_dir / "reviewed-identity-public-contract-decision-record.json").exists())
        self.assertFalse((output_dir / "player-identity-promotion-certificate.json").exists())

    def test_rejects_approved_runtime_artifact_identity_drift_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_dir = Path(temp)
            runtime_path, strict_report_path = self.write_runtime_inputs(temp_dir)
            approved_runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            approved_runtime["output_artifact_identity"]["artifact_sha256"] = "0" * 64
            self.write_json(runtime_path, approved_runtime)
            output_dir = self.repo_tempdir()

            result = self.run_bridge(
                "--approved-runtime-evidence",
                str(runtime_path),
                "--strict-approved-runtime-check-report",
                str(strict_report_path),
                "--output-dir",
                str(output_dir),
                expect_returncode=1,
            )

        self.assertIn("failed strict checker replay", result.stderr)
        self.assertFalse((output_dir / "reviewed-identity-public-contract-decision-record.json").exists())
        self.assertFalse((output_dir / "player-identity-promotion-certificate.json").exists())

    def built_bridge_payloads(self, root: Path) -> tuple[Path, Path, Path, dict, dict]:
        runtime_path, strict_report_path = self.write_runtime_inputs(root)
        output_dir = self.repo_tempdir()
        self.run_bridge(
            "--approved-runtime-evidence",
            str(runtime_path),
            "--strict-approved-runtime-check-report",
            str(strict_report_path),
            "--output-dir",
            str(output_dir),
        )
        decision_record = json.loads(
            (output_dir / "reviewed-identity-public-contract-decision-record.json").read_text(
                encoding="utf-8"
            )
        )
        certificate = json.loads(
            (output_dir / "player-identity-promotion-certificate.json").read_text(
                encoding="utf-8"
            )
        )
        return (
            runtime_path,
            strict_report_path,
            output_dir / "reviewed-identity-public-contract-decision-record.json",
            decision_record,
            certificate,
        )

    def test_rejects_generated_decision_record_runtime_binding_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                Path(temp)
            )
            decision_record["approved_runtime_evidence_binding"]["artifact_sha256"] = "0" * 64

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn("approved runtime evidence binding mismatch", str(raised.exception))

    def test_rejects_generated_decision_record_copied_log_binding_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, _decision_record_path, decision_record, _certificate = self.built_bridge_payloads(
                Path(temp)
            )
            approved_runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            strict_report = json.loads(strict_report_path.read_text(encoding="utf-8"))
            decision_record["approved_runtime_evidence_binding"]["copied_log_sha256"] = "0" * 64

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_decision_record_bridge_binding(
                    approved_runtime=approved_runtime,
                    strict_report=strict_report,
                    strict_report_path=strict_report_path,
                    decision_record=decision_record,
                )

        self.assertIn("approved runtime evidence binding mismatch", str(raised.exception))
        self.assertIn("copied_log_sha256", str(raised.exception))

    def test_rejects_generated_chain_with_hash_current_stale_strict_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                Path(temp)
            )
            strict_report = json.loads(strict_report_path.read_text(encoding="utf-8"))
            strict_report["consumer_boundary_assertions"] = []
            self.write_json(strict_report_path, strict_report)
            decision_record["strict_approved_runtime_checker_contract_report"]["sha256"] = (
                bridge_builder.sha256_file(strict_report_path)
            )

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn(
            "strict_approved_runtime_checker_contract_report_runtime_input_mismatch",
            str(raised.exception),
        )

    def test_rejects_generated_decision_record_duplicate_manifest_ref_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                temp_path
            )
            duplicate_runtime_path = temp_path / "duplicate-approved-runtime-principal-lifecycle-evidence.json"
            duplicate_runtime_path.write_text(runtime_path.read_text(encoding="utf-8"), encoding="utf-8")
            decision_record["approved_runtime_evidence_manifest_ref"]["path"] = str(
                duplicate_runtime_path
            )
            decision_record["approved_runtime_evidence_manifest_ref"]["sha256"] = (
                bridge_builder.sha256_file(duplicate_runtime_path)
            )

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn(
            "manifest ref does not match --approved-runtime-evidence",
            str(raised.exception),
        )

    def test_rejects_generated_certificate_decision_summary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                Path(temp)
            )
            certificate["evidence"]["identity_public_contract_decision_record"][
                "resolved_decision_keys"
            ] = []

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn("decision record summary mismatch", str(raised.exception))

    def test_rejects_generated_certificate_summary_only_decision_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                Path(temp)
            )
            certificate["evidence"].pop("identity_public_contract_decision_record_artifact")
            certificate["evidence"].pop(
                "identity_public_contract_decision_record_payload_sha256",
                None,
            )

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn("missing full decision record artifact binding", str(raised.exception))

    def test_rejects_generated_certificate_full_decision_record_artifact_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                Path(temp)
            )
            certificate["evidence"]["identity_public_contract_decision_record_artifact"][
                "sha256"
            ] = "0" * 64

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn("full decision record artifact binding mismatch", str(raised.exception))

    def test_rejects_generated_certificate_runtime_binding_digest_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                Path(temp)
            )
            certificate["evidence"]["identity_public_contract_decision_record_runtime_binding"][
                "approved_runtime_evidence_binding_sha256"
            ] = "0" * 64

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn("runtime binding digest mismatch", str(raised.exception))

    def test_rejects_generated_certificate_terminal_alias_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                Path(temp)
            )
            certificate["post_runtime_bridge_constraints"]["terminal_certificate"] = True
            certificate["evidence"]["post_runtime_bridge_constraints"][
                "public_header_gate_missing_after_runtime_evidence"
            ] = True

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn("post-runtime bridge constraints mismatch", str(raised.exception))
        self.assertIn("terminal_certificate", str(raised.exception))

    def test_rejects_generated_certificate_package_support_beta_status_alias_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_path, strict_report_path, decision_record_path, decision_record, certificate = self.built_bridge_payloads(
                Path(temp)
            )
            certificate["post_runtime_bridge_constraints"]["support_tier_ready"] = True
            certificate["evidence"]["post_runtime_bridge_constraints"]["package_shape_ready"] = True
            certificate["evidence"]["post_runtime_bridge_constraints"]["beta_notice_ready"] = True
            certificate["evidence"]["post_runtime_bridge_constraints"]["status_report_ready"] = True

            with self.assertRaises(SystemExit) as raised:
                bridge_builder.validate_generated_bridge_bindings(
                    approved_runtime_path=runtime_path,
                    strict_report_path=strict_report_path,
                    decision_record_path=decision_record_path,
                    decision_record=decision_record,
                    certificate=certificate,
                )

        self.assertIn("post-runtime bridge constraints mismatch", str(raised.exception))
        self.assertIn("support_tier_ready", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
