#!/usr/bin/env python3
"""Tests for the v1 complete-SDK release claim checker."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"
PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"


def complete_excluded_manifest() -> tuple[dict, str]:
    manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
    manifest["v1_completion_required"] = True
    manifest["stable_release_contract"]["claim_allowed"] = True
    manifest["experimental_surfaces"] = []
    manifest["planning_surfaces"] = []
    release_lines = [
        "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
    ]
    for surface in manifest["surfaces"]:
        if surface["status"] == "promoted-experimental-only":
            surface["status"] = "excluded"
            surface["public_contract"] = []
            if surface["id"] not in manifest["post_v1_or_excluded_surfaces"]:
                manifest["post_v1_or_excluded_surfaces"].append(surface["id"])
            release_lines.append(f"{surface['id']}: excluded - experimental seed is not included in v1.")
        if surface["id"] in manifest["v1_sdk_completion_blockers"]:
            surface["status"] = "excluded"
            surface["public_contract"] = []
            if not isinstance(surface.get("v1_decision_contract"), dict):
                exclusions = surface.get("exclusions") if isinstance(surface.get("exclusions"), list) else []
                audit_units = surface.get("audit_units") if isinstance(surface.get("audit_units"), list) else []
                named_exclusions = [
                    str(item)
                    for item in [*exclusions, *audit_units]
                    if isinstance(item, str)
                ]
                required_text = (
                    f"no {', '.join(named_exclusions)} API is included in v1"
                    if named_exclusions
                    else f"no public API for {surface['id']} is included in v1"
                )
                surface["v1_decision_contract"] = {
                    "exclusion_requires": [
                        f"the v1 release statement names {surface['id']} as excluded",
                        f"the v1 release statement states that {required_text}",
                    ]
                }
            if surface["id"] not in manifest["post_v1_or_excluded_surfaces"]:
                manifest["post_v1_or_excluded_surfaces"].append(surface["id"])
            contract = surface.get("v1_decision_contract")
            detail_parts = ["no public API for this surface is included in v1"]
            if isinstance(contract, dict):
                for requirement in contract.get("exclusion_requires", []):
                    marker = "the v1 release statement states that "
                    if isinstance(requirement, str) and requirement.lower().startswith(marker):
                        detail_parts.append(requirement[len(marker) :])
            release_lines.append(f"{surface['id']}: excluded - {'; '.join(detail_parts)}")
    return manifest, "\n".join(release_lines) + "\n"


class PublicSdkV1CompletionCheckTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["python3", str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_current_manifest_fails_closed_for_v1_completion(self) -> None:
        result = self.run_checker("--json", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["schema"], "obelisk.public-sdk-v1-completion-check.v1")
        self.assertFalse(payload["ready"])
        self.assertIn("stable_release_contract_claim_not_allowed", payload["blockers"])
        self.assertIn("v1_completion_required_false", payload["blockers"])
        self.assertIn("promoted_experimental_surfaces_unresolved", payload["blockers"])
        self.assertIn("v1_sdk_completion_blockers_unresolved", payload["blockers"])
        self.assertNotIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["unresolved_completion_blockers"])
        self.assertIn("obelisk.gameplay_policy_event.v1", payload["unresolved_experimental_surfaces"])
        self.assertIn("core-first release readiness", " ".join(payload["non_claims"]))

    def test_complete_minimal_manifest_passes(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            release_statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--json",
            )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["blockers"], [])

    def test_empty_or_truncated_manifest_fails_closed(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": [],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("canonical_surface_id_missing", payload["blockers"])
        self.assertIn("canonical_v1_completion_blocker_missing", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["missing_canonical_surfaces"])
        self.assertIn("obelisk.player_identity.v1", payload["missing_canonical_completion_blockers"])

    def test_release_statement_must_name_non_promoted_blockers(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_negated_or_global_outcome_wording(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1 is intentionally not described here as excluded.\n"
                "Other items may be post-v1.\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_ambiguous_outcome_punctuation(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.player_identity.v1: excluded -",
            "obelisk.player_identity.v1: excluded? actually included -",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["release_statement_missing_blocker_outcomes"])

    def test_release_statement_rejects_negated_contract_substring_in_surface_record(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "planning_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded - it is false that no player identity API is included in v1\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_release_statement_accepts_exact_outcome_with_no_explanatory_text(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += "obelisk.player_identity.v1: excluded - no player identity API is included in v1.\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])

    def test_release_statement_must_satisfy_surface_exclusion_contract(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_non_promoted_public_contract_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.commands_replies.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.commands_replies.v1"],
            "surfaces": [
                {
                    "id": "obelisk.commands_replies.v1",
                    "status": "post-v1",
                    "public_contract": ["RegisterCommand"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertEqual(payload["non_promoted_with_public_contract"], ["obelisk.commands_replies.v1"])

    def test_status_experimental_surface_omitted_from_top_level_list_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": [],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [
                {
                    "id": "obelisk.chat_message.v1",
                    "status": "promoted-experimental-only",
                    "public_contract": ["RegisterChatCallback"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("experimental_surface_list_mismatch", payload["blockers"])
        self.assertIn("promoted_experimental_surfaces_unresolved", payload["blockers"])
        self.assertEqual(payload["experimental_list_mismatches"], ["obelisk.chat_message.v1"])
        self.assertEqual(payload["unresolved_experimental_surfaces"], ["obelisk.chat_message.v1"])

    def test_experimental_surface_exclusion_requires_release_statement_outcome(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = "\n".join(
            line for line in release_statement.splitlines() if "obelisk.chat_message.v1" not in line
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_experimental_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_experimental_outcomes"], ["obelisk.chat_message.v1"])

    def test_docs_only_promotion_evidence_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": ["obelisk.player_identity.v1"],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "promoted",
                    "public_contract": ["ObeliskApi.RegisterPlayerIdentityCallback"],
                    "evidence": {"docs": ["TODO-only-doc.md"]},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_fake_promotion_evidence_path_blocks_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["TODO-not-a-real-test"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_generic_existing_directory_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["tests/sdk_consumer"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_absolute_external_evidence_path_blocks_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["/tmp"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_existing_generic_script_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["scripts/check_release_readiness.sh"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_candidate_only_player_identity_preflight_test_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                    "sdk_consumer_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_new_planning_surface_blocks_v1_claim_until_outcome_is_named(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["surfaces"].append(
            {
                "id": "obelisk.future_unmapped_surface.v1",
                "status": "planning",
                "public_contract": [],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("planning_surfaces_unresolved_for_v1_claim", payload["blockers"])
        self.assertEqual(payload["unresolved_planning_surfaces"], ["obelisk.future_unmapped_surface.v1"])

    def test_top_level_planning_surfaces_block_v1_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["planning_surfaces"] = ["obelisk.player_identity.v1"]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("top_level_planning_surfaces_unresolved_for_v1_claim", payload["blockers"])
        self.assertIn("planning_surface_list_mismatch", payload["blockers"])
        self.assertEqual(payload["top_level_planning_surfaces"], ["obelisk.player_identity.v1"])

    def test_debug_only_surface_cannot_be_promoted(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.debug_raw_process_event.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterRawProcessEvent"]
                surface["evidence"] = {"tests": ["tests/sdk_consumer"]}
                break
        manifest["promoted_surfaces"].append("obelisk.debug_raw_process_event.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("debug_only_surface_promoted", payload["blockers"])
        self.assertEqual(payload["debug_only_promoted_surfaces"], ["obelisk.debug_raw_process_event.v1"])

    def test_non_promoted_completion_blocker_requires_exclusion_contract(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.commands_replies.v1":
                surface.pop("v1_decision_contract", None)
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("completion_blocker_exclusion_contract_missing", payload["blockers"])
        self.assertEqual(payload["missing_completion_blocker_exclusion_contracts"], ["obelisk.commands_replies.v1"])

    def test_release_statement_required_for_v1_completion_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_required_for_v1_completion", payload["blockers"])


if __name__ == "__main__":
    unittest.main()
