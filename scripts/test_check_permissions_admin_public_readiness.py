#!/usr/bin/env python3
"""Tests for check_permissions_admin_public_readiness.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_permissions_admin_public_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
QUERY_CHECKER = SCRIPT_DIR / "check_permissions_admin_query_failclosed_contract.py"


def run_checker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def write_json(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class PermissionsAdminPublicReadinessTests(unittest.TestCase):
    def test_accepts_current_permissions_admin_as_planning_only(self) -> None:
        result = run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["dependency"], "obelisk.player_identity.v1")

    def test_accepts_candidate_query_failclosed_manifest_and_report_only_as_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "permissions-query.json"
            subprocess.run(
                [sys.executable, str(QUERY_CHECKER), "--emit-template", str(manifest_path)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            result = run_checker("--query-failclosed-artifact", str(manifest_path))
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                report["query_failclosed_artifact_schema"],
                "obelisk.permissions-admin-query-failclosed-contract.v1",
            )
            self.assertFalse(report["public_sdk_ready"])

            report_path = root / "permissions-query-report.json"
            query_report = subprocess.run(
                [sys.executable, str(QUERY_CHECKER), str(manifest_path), "--json"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            report_path.write_text(query_report.stdout, encoding="utf-8")
            result = run_checker("--query-failclosed-artifact", str(report_path))
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                report["query_failclosed_artifact_schema"],
                "obelisk.permissions-admin-query-failclosed-contract-check.v1",
            )

    def test_rejects_public_contract_and_header_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["public_header_allowed"] = True
            decisions["public_cache_abi_allowed"] = True
            decisions["public_header_symbols_now"] = ["ObeliskPermissionQuery"]
            decisions_path = write_json(root, "decisions.json", decisions)

            header_path = root / "ObeliskApi.h"
            header_path.write_text(HEADER.read_text(encoding="utf-8") + "\nstruct ObeliskPermissionQuery {};\n")

            result = run_checker("--decisions", str(decisions_path), "--public-header", str(header_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_cache_abi_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_header_contains_permissions_admin_symbol", report["blockers"])

    def test_rejects_expanded_post_identity_allowed_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["allowed_public_surface_after_player_identity"].append("admin mutation actions")
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "allowed_public_surface_after_player_identity_not_exact_query_only",
            report["blockers"],
        )

    def test_rejects_surface_promoted_before_player_identity_or_public_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskPermissionQuery"]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permissions_admin_surface_status_unexpected", report["blockers"])
        self.assertIn("permissions_admin_public_contract_not_empty", report["blockers"])
        self.assertIn("permissions_admin_promoted_before_player_identity", report["blockers"])

    def test_rejects_query_failclosed_artifact_readiness_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = {
                "schema": "obelisk.permissions-admin-query-failclosed-contract-check.v1",
                "mode": "consume",
                "ready": True,
                "promotion_ready": True,
                "public_sdk_ready": True,
                "runtime_ready": True,
            }
            artifact_path = write_json(root, "query-report.json", artifact)

            result = run_checker("--query-failclosed-artifact", str(artifact_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_failclosed_artifact_promotion_ready_not_false", report["blockers"])
        self.assertIn("query_failclosed_artifact_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("query_failclosed_artifact_runtime_ready_not_false", report["blockers"])

    def test_rejects_query_failclosed_manifest_that_only_matches_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = {
                "schema": "obelisk.permissions-admin-query-failclosed-contract.v1",
                "artifact_status": "candidate_only",
                "promotion_ready": False,
                "public_header_allowed": False,
                "public_cache_abi_allowed": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
            }
            artifact_path = write_json(root, "query-manifest.json", artifact)

            result = run_checker("--query-failclosed-artifact", str(artifact_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_failclosed_manifest_contract_invalid", report["blockers"])

    def test_rejects_permission_query_abi_boundary_properties_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            abi = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "abi.permission_query_identity_fields"
            )
            abi["required_properties"].remove("owner-token scoped call")
            abi["required_properties"].remove("no UE pointers or raw params")
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_text_boundary_properties_missing", report["blockers"])


if __name__ == "__main__":
    unittest.main()
