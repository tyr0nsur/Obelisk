#!/usr/bin/env python3
"""Tests for check_mission_transfer_dino_tribe_v1_outcome_accounting.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_mission_transfer_dino_tribe_v1_outcome_accounting.py"
MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
SPLIT_NOTE = REPO_ROOT / "docs" / "research" / "2026-06-01-mission-transfer-dino-tribe-v1-split.md"
SURFACE_ID = "obelisk.mission_transfer_dino_tribe.v1"
REQUIRED_LEAVES = ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"]


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def surface(manifest: dict) -> dict:
    return next(item for item in manifest["surfaces"] if item["id"] == SURFACE_ID)


def excluded_release_statement() -> str:
    return (
        "Reviewed against docs/public_sdk_surfaces.json.\n"
        f"{SURFACE_ID}: excluded - mission excluded; transfer excluded; "
        "dino_policy excluded; tribe_policy excluded; buff_status excluded. "
        "No Mission SDK, Transfer SDK, Dino SDK, Tribe SDK, Buff/status SDK, "
        "teleport/spawn API, ownership lookup, ResourceHandle, mutation, return override, "
        "runtime hook, identity, lookup, or cross-map correlation API is included in v1.\n"
    )


class MissionTransferDinoTribeOutcomeAccountingTests(unittest.TestCase):
    def run_checker(
        self,
        manifest: dict | None = None,
        statement: str | None = None,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "public_sdk_surfaces.json"
            statement_path = root / "release-statement.md"
            manifest_path.write_text(json.dumps(manifest if manifest is not None else load_manifest()), encoding="utf-8")
            args = [
                sys.executable,
                str(SCRIPT),
                "--manifest",
                str(manifest_path),
                "--split-note",
                str(SPLIT_NOTE),
                "--json",
            ]
            if statement is not None:
                statement_path.write_text(statement, encoding="utf-8")
                args.extend(["--release-statement", str(statement_path)])
            result = subprocess.run(
                args,
                cwd=REPO_ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_current_manifest_accepts_candidate_only_accounting(self) -> None:
        result = self.run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1")
        self.assertTrue(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertTrue(report["candidate_only"])
        self.assertEqual(report["required_leaves"], REQUIRED_LEAVES)
        self.assertEqual(report["observed_leaves"], REQUIRED_LEAVES)
        self.assertEqual(set(report["leaf_statuses"].values()), {"planning"})
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["blockers"], [])

    def test_release_statement_accepts_umbrella_excluded_with_all_leaf_exclusions(self) -> None:
        result = self.run_checker(statement=excluded_release_statement())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["accounting_route"], "release_statement_umbrella_excluded")
        self.assertTrue(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(report["release_statement"]["forbidden_claims"], [])
        self.assertTrue(all(report["release_statement"]["leaf_exclusions"].values()))

    def test_release_statement_rejects_missing_leaf_exclusion(self) -> None:
        statement = excluded_release_statement().replace("buff_status excluded. ", "")
        result = self.run_checker(statement=statement, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_leaf_exclusions_missing", report["blockers"])
        details = [item for item in report["blocker_details"] if item["reason"] == "release_statement_leaf_exclusions_missing"]
        self.assertEqual(details[0]["missing"], ["buff_status"])

    def test_release_statement_rejects_affirmative_forbidden_claims(self) -> None:
        statement = (
            f"{SURFACE_ID}: excluded - mission excluded; transfer excluded; "
            "dino_policy excluded; tribe_policy excluded; buff_status excluded. "
            "Mission SDK is included in v1. ResourceHandle lookup is available. "
            "The runtime hook supports cross-map correlation.\n"
        )
        result = self.run_checker(statement=statement, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_claims", report["blockers"])
        claims = report["release_statement"]["forbidden_claims"]
        self.assertIn("Mission SDK", claims)
        self.assertIn("ResourceHandle", claims)
        self.assertIn("runtime hook", claims)
        self.assertIn("cross-map correlation", claims)

    def test_excluded_manifest_route_rejects_public_contract(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["status"] = "excluded"
        gameplay["public_contract"] = ["Mission API"]
        for leaf in gameplay["leaf_decision_units"]:
            leaf["status"] = "excluded"
        gameplay["leaf_decision_units"][0]["public_contract"] = ["mission identity lookup"]

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("excluded_surface_public_contract_not_empty", report["blockers"])
        self.assertIn("excluded_leaf_public_contract_not_empty", report["blockers"])
        self.assertIn("public_contract_forbidden_claim", report["blockers"])
        self.assertIn("leaf_public_contract_forbidden_claim", report["blockers"])

    def test_future_per_leaf_promoted_route_requires_real_evidence(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["status"] = "promoted"
        for leaf in gameplay["leaf_decision_units"]:
            leaf["status"] = "promoted"
            leaf["public_contract"] = [f"Copied {leaf['id']} policy event"]
            leaf["evidence"] = {
                "promotion_status": "promoted",
                "public_sdk_ready": True,
                "promotion_ready": True,
                "runtime_ready": True,
                "abi_tests": [f"tests/abi/{leaf['id']}_abi_tests.cpp"],
                "sdk_consumer_tests": [f"tests/sdk_consumer/{leaf['id']}_consumer.c"],
                "second_source_evidence": [f"docs/research/{leaf['id']}-accepted-second-source.md"],
            }

        result = self.run_checker(manifest=manifest)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["accounting_route"], "per_leaf_promoted")
        self.assertTrue(report["promotion_ready"])
        self.assertTrue(report["public_sdk_ready"])
        self.assertTrue(report["runtime_ready"])

    def test_future_per_leaf_promoted_route_rejects_missing_or_candidate_evidence(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["status"] = "promoted"
        for leaf in gameplay["leaf_decision_units"]:
            leaf["status"] = "promoted"
            leaf["evidence"] = {
                "promotion_status": "promoted",
                "public_sdk_ready": True,
                "promotion_ready": True,
                "runtime_ready": True,
                "abi_tests": [f"tests/abi/{leaf['id']}_abi_tests.cpp"],
                "sdk_consumer_tests": [f"tests/sdk_consumer/{leaf['id']}_consumer.c"],
                "second_source_evidence": [f"docs/research/{leaf['id']}-accepted-second-source.md"],
            }
        gameplay["leaf_decision_units"][0]["evidence"].pop("second_source_evidence")
        gameplay["leaf_decision_units"][1]["evidence"]["notes"] = "candidate-only intake is not promoted"

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_leaf_real_evidence_missing", report["blockers"])
        self.assertIn("promoted_leaf_evidence_contains_candidate_only_markers", report["blockers"])

    def test_manifest_rejects_missing_required_leaf(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["leaf_decision_units"] = [
            leaf for leaf in gameplay["leaf_decision_units"] if leaf["id"] != "tribe_policy"
        ]

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_decision_units_mismatch", report["blockers"])


if __name__ == "__main__":
    unittest.main()
