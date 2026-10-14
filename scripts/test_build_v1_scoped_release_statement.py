#!/usr/bin/env python3
"""Tests for the scoped non-complete v1 release-statement builder."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_v1_scoped_release_statement as builder
from check_public_sdk_v1_completion import (
    CANONICAL_EXPERIMENTAL_SURFACE_IDS,
    CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN,
    release_statement_forbidden_broad_claims,
    scoped_release_statement_required_outcome_records,
)


class BuildV1ScopedReleaseStatementTests(unittest.TestCase):
    def load_manifest(self) -> dict[str, object]:
        return builder.load_manifest(REPO_ROOT / "docs" / "public_sdk_surfaces.json")

    @staticmethod
    def statement_surface_ids(statement: str) -> set[str]:
        return {
            line.split(":", 1)[0]
            for line in statement.splitlines()
            if line and not line.startswith("#")
        }

    @staticmethod
    def statement_surface_order(statement: str) -> list[str]:
        return [
            line.split(":", 1)[0]
            for line in statement.splitlines()
            if line and not line.startswith("#")
        ]

    def test_builds_only_non_p0_non_experimental_scoped_completion_blocker_rows(self) -> None:
        manifest = self.load_manifest()
        statement = builder.build_statement(manifest)
        expected_records = scoped_release_statement_required_outcome_records(
            manifest["v1_sdk_completion_blockers"],
            builder.surfaces_by_id(manifest),
            set(manifest["post_v1_or_excluded_surfaces"]),
        )
        expected = [record["surface"] for record in expected_records]

        emitted = self.statement_surface_ids(statement)
        self.assertEqual(set(expected), emitted)
        self.assertEqual(expected, self.statement_surface_order(statement))
        self.assertFalse(emitted & set(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN))
        self.assertFalse(emitted & set(CANONICAL_EXPERIMENTAL_SURFACE_IDS))
        self.assertEqual([], release_statement_forbidden_broad_claims(statement))
        self.assertIn("do not authorize stable/full/production SDK wording", statement)
        self.assertIn("observer-event triage do not count toward this statement", statement)
        self.assertIn(
            "Post-reboot passive monitor context and confirmed beta notices are operator context only",
            statement,
        )
        self.assertIn(
            "Offline hardening, reviewed decision records, generated certificate reports",
            statement,
        )
        self.assertIn("they do not count toward this statement, SDK/P0 progress", statement)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", statement)
        self.assertIn(f"Scoped outcome rows: {len(expected)}; non-claim bookkeeping only", statement)
        self.assertIn(
            f"Required scoped non-promoted blocker outcomes listed: {len(expected)}/{len(expected)}",
            statement,
        )
        self.assertIn(
            "Completion progress from this statement: 0/12; P0 dependency-chain progress remains "
            "0/4 with obelisk.player_identity.v1 blocked first",
            statement,
        )
        self.assertIn(
            "Current route blocker remains approved_runtime_evidence_missing; next required "
            "artifact is approved_runtime_principal_lifecycle_evidence_bundle.",
            statement,
        )
        self.assertIn(
            "No Plugin Hub readiness/publication, support-tier activation, public module availability, "
            "or package-shape/public package readiness is authorized.",
            statement,
        )

    def test_structured_outcome_payload_preserves_non_claim_bookkeeping(self) -> None:
        manifest = self.load_manifest()
        payload = builder.build_outcome_payload(manifest)
        outcomes = payload["outcomes"]

        self.assertEqual(payload["schema"], "obelisk.scoped-release-statement-outcomes.v1")
        self.assertEqual(payload["blocker"], "release_statement_missing_non_promoted_blocker_outcomes")
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["stable_sdk_claim_allowed"])
        self.assertFalse(payload["complete_sdk_claim_allowed"])
        self.assertFalse(payload["complete_sdk_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertEqual(payload["completion_progress_count"], 0)
        self.assertEqual(payload["completion_progress_total"], len(manifest["v1_sdk_completion_blockers"]))
        self.assertEqual(payload["completion_progress_ratio"], "0/12")
        self.assertFalse(payload["scoped_release_statement_counts_toward_complete_sdk_claim"])
        self.assertEqual(payload["complete_sdk_claim_progress_contribution"], 0)
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(payload["counts_toward_v1_completion"])
        self.assertEqual(payload["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(payload["p0_dependency_chain_progress_contribution"], 0)
        self.assertEqual(payload["p0_dependency_chain_current_promoted_count"], 0)
        self.assertEqual(payload["p0_dependency_chain_required_count"], 4)
        self.assertEqual(payload["p0_dependency_chain_current_progress_ratio"], "0/4")
        self.assertEqual(payload["p0_dependency_chain_first_blocker"], "obelisk.player_identity.v1")
        self.assertTrue(payload["p0_dependency_chain_blocked"])
        self.assertEqual(payload["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(payload["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(
            payload["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            payload["missing_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertFalse(payload["approved_runtime_evidence_accepted"])
        self.assertFalse(payload["approved_runtime_principal_lifecycle_evidence_bundle_accepted"])
        self.assertFalse(payload["evidence_bundle_accepted"])
        self.assertEqual(payload["v1_completion_contribution"], 0)
        self.assertTrue(payload["required_outcome_bookkeeping_only"])
        self.assertFalse(payload["required_outcome_counts_as_progress"])
        self.assertEqual(payload["required_outcome_progress_contribution"], 0)
        self.assertFalse(payload["required_outcomes_listed_counts_toward_completion"])
        self.assertEqual(payload["required_outcomes_listed_completion_progress_contribution"], 0)
        self.assertFalse(payload["non_p0_bookkeeping_counts_toward_completion"])
        self.assertEqual(payload["non_p0_bookkeeping_progress_contribution"], 0)
        for key in builder.SCOPED_RELEASE_STATEMENT_PUBLIC_NON_CLAIM_FLAGS:
            with self.subTest(payload_non_claim=key):
                self.assertFalse(payload[key])
        for key, expected in builder.SCOPED_RELEASE_STATEMENT_ZERO_PROGRESS_FLAGS.items():
            with self.subTest(payload_zero_progress=key):
                self.assertEqual(payload[key], expected)
        self.assertEqual(payload["required_outcome_count"], payload["outcome_count"])
        self.assertEqual(payload["required_outcomes_listed"], payload["outcome_count"])
        self.assertEqual(
            payload["required_outcome_surfaces"],
            [row["surface"] for row in outcomes],
        )
        self.assertFalse(payload["approved_runtime_evidence"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["route_ready"])
        self.assertFalse(payload["blocker_resolved"])
        self.assertFalse(payload["side_lane_promoted"])
        self.assertFalse(payload["structure_build_policy_ready"])
        self.assertFalse(payload["active_notice_sent"])
        self.assertFalse(payload["active_notice_counts_toward_complete_sdk_claim"])
        self.assertFalse(payload["passive_activity_triage_counts_toward_release"])
        self.assertFalse(payload["observer_event_triage_counts_toward_release"])
        self.assertFalse(payload["passive_snapshot_counts_toward_public_sdk"])
        self.assertEqual(payload["outcome_count"], len(outcomes))
        self.assertIn("do not authorize stable/full/production SDK wording", payload["statement"])
        self.assertIn("observer-event triage do not count toward this statement", payload["statement"])
        for row in outcomes:
            with self.subTest(surface=row["surface"]):
                self.assertIn(row["outcome"], {"post-v1", "excluded"})
                self.assertEqual(
                    row["blocker"],
                    "release_statement_missing_non_promoted_blocker_outcomes",
                )
                self.assertFalse(row["approved_runtime_evidence"])
                self.assertFalse(row["stable_claim_allowed"])
                self.assertFalse(row["route_ready"])
                self.assertFalse(row["blocker_resolved"])
                self.assertFalse(row["side_lane_promoted"])
                self.assertFalse(row["structure_build_policy_ready"])
                self.assertFalse(row["active_notice_sent"])
                self.assertFalse(row["active_notice_counts_toward_complete_sdk_claim"])
                self.assertFalse(row["stable_sdk_claim_allowed"])
                self.assertFalse(row["complete_sdk_claim_allowed"])
                self.assertFalse(row["complete_sdk_ready"])
                self.assertFalse(row["v1_completion_ready"])
                self.assertFalse(row["public_sdk_ready"])
                self.assertFalse(row["runtime_ready"])
                self.assertFalse(row["scoped_release_statement_counts_toward_complete_sdk_claim"])
                self.assertEqual(row["scoped_release_statement_claim_progress_contribution"], 0)
                self.assertFalse(row["counts_toward_public_sdk"])
                self.assertFalse(row["counts_toward_runtime"])
                self.assertFalse(row["counts_toward_v1_completion"])
                self.assertFalse(row["counts_toward_complete_sdk_claim"])
                self.assertFalse(row["counts_toward_p0_dependency_chain"])
                self.assertFalse(row["counts_toward_p0_dependency_chain_claim"])
                self.assertEqual(row["p0_dependency_chain_claim_progress_contribution"], 0)
                self.assertEqual(row["p0_dependency_chain_progress_contribution"], 0)
                self.assertEqual(row["p0_dependency_chain_first_blocker"], "obelisk.player_identity.v1")
                self.assertEqual(row["current_route_blocker"], "approved_runtime_evidence_missing")
                self.assertEqual(row["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
                self.assertEqual(
                    row["next_required_artifact"],
                    "approved_runtime_principal_lifecycle_evidence_bundle",
                )
                self.assertEqual(
                    row["missing_required_artifact"],
                    "approved_runtime_principal_lifecycle_evidence_bundle",
                )
                self.assertFalse(row["approved_runtime_evidence_accepted"])
                self.assertFalse(row["approved_runtime_principal_lifecycle_evidence_bundle_accepted"])
                self.assertFalse(row["evidence_bundle_accepted"])
                self.assertEqual(row["v1_completion_contribution"], 0)
                self.assertTrue(row["required_outcome_bookkeeping_only"])
                self.assertFalse(row["required_outcome_counts_as_progress"])
                self.assertEqual(row["required_outcome_progress_contribution"], 0)
                self.assertFalse(row["required_outcomes_listed_counts_toward_completion"])
                self.assertEqual(row["required_outcomes_listed_completion_progress_contribution"], 0)
                self.assertFalse(row["non_p0_bookkeeping_counts_toward_completion"])
                self.assertEqual(row["non_p0_bookkeeping_progress_contribution"], 0)
                for key in builder.SCOPED_RELEASE_STATEMENT_PUBLIC_NON_CLAIM_FLAGS:
                    self.assertFalse(row[key])
                for key, expected in builder.SCOPED_RELEASE_STATEMENT_ZERO_PROGRESS_FLAGS.items():
                    self.assertEqual(row[key], expected)
                self.assertFalse(row["passive_activity_triage_counts_toward_release"])
                self.assertFalse(row["observer_event_triage_counts_toward_release"])
                self.assertFalse(row["passive_snapshot_counts_toward_public_sdk"])
                self.assertIn("bookkeeping only", row["non_claim"])
                self.assertEqual(
                    row["line"],
                    f"{row['surface']}: {row['outcome']} - {row['detail']}",
                )
                self.assertIn(row["line"], payload["statement"])

    def test_durable_scoped_statement_matches_generated_non_claim_statement(self) -> None:
        manifest = self.load_manifest()
        generated = builder.build_statement(manifest)
        durable = (REPO_ROOT / "docs" / "SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(generated, durable)
        self.assertEqual([], release_statement_forbidden_broad_claims(durable))
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", durable)
        self.assertIn("non-claim bookkeeping only", durable)
        self.assertIn("Required scoped non-promoted blocker outcomes listed: 8/8", durable)
        self.assertIn("Completion progress from this statement: 0/12", durable)
        self.assertIn("P0 dependency-chain progress remains 0/4", durable)
        self.assertIn("obelisk.player_identity.v1 blocked first", durable)
        self.assertIn("approved_runtime_evidence_missing", durable)
        self.assertIn("approved_runtime_principal_lifecycle_evidence_bundle", durable)
        self.assertIn("No Plugin Hub readiness/publication", durable)
        self.assertIn("package-shape/public package readiness is authorized", durable)
        self.assertIn("do not authorize stable/full/production SDK wording", durable)
        self.assertIn("observer-event triage do not count toward this statement", durable)
        self.assertIn(
            "Post-reboot passive monitor context and confirmed beta notices are operator context only",
            durable,
        )
        self.assertIn(
            "Offline hardening, reviewed decision records, generated certificate reports",
            durable,
        )

    def test_p0_status_drift_still_reports_zero_claim_progress_without_runtime_bundle(self) -> None:
        manifest = copy.deepcopy(self.load_manifest())
        for surface in manifest["surfaces"]:
            if surface.get("id") in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN:
                surface["status"] = "promoted"

        payload = builder.build_outcome_payload(manifest)

        self.assertEqual(payload["p0_dependency_chain_manifest_promoted_status_count"], 4)
        self.assertEqual(payload["p0_dependency_chain_current_promoted_count"], 0)
        self.assertEqual(payload["p0_dependency_chain_current_progress_ratio"], "0/4")
        self.assertEqual(payload["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            payload["missing_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )

    def test_rejects_forbidden_scoped_detail_claims(self) -> None:
        manifest = copy.deepcopy(self.load_manifest())
        for surface in manifest["surfaces"]:
            if surface.get("id") == "obelisk.inventory_items_mutation.v1":
                surface["v1_decision_contract"]["exclusion_requires"] = [
                    "the v1 release statement names obelisk.inventory_items_mutation.v1 as post-v1",
                    "the v1 release statement states that production full SDK is included in v1",
                ]
                break

        with self.assertRaisesRegex(ValueError, "forbidden scoped claim"):
            builder.build_statement(manifest)

    def test_rejects_package_hub_module_and_public_package_scoped_detail_claims(self) -> None:
        claim_details = {
            "plugin-hub": "the v1 release statement states that Plugin Hub publication is ready in v1",
            "package-shape": "the v1 release statement states that package-shape readiness is included in v1",
            "public-module": "the v1 release statement states that public module availability is included in v1",
            "public-package": "the v1 release statement states that public package availability is included in v1",
            "public-sdk-readiness": "the v1 release statement states that public SDK readiness is included in v1",
            "active-monitor": "the v1 release statement states that active passive monitor readiness is included in v1",
            "discord-beta-bridge": "the v1 release statement states that Discord beta bridge readiness is included in v1",
            "active-notice": "the v1 release statement states that active notice readiness is included in v1",
            "beta-pack": "the v1 release statement states that beta capture pack readiness is included in v1",
            "side-lane-candidate": "the v1 release statement states that side-lane candidate progress is included in v1",
            "scoped-release-statement": "the v1 release statement states that scoped release statement readiness counts in v1",
        }
        for claim_name, detail in claim_details.items():
            with self.subTest(claim_name=claim_name):
                manifest = copy.deepcopy(self.load_manifest())
                for surface in manifest["surfaces"]:
                    if surface.get("id") == "obelisk.inventory_items_mutation.v1":
                        surface["v1_decision_contract"]["exclusion_requires"] = [
                            "the v1 release statement names obelisk.inventory_items_mutation.v1 as post-v1",
                            detail,
                        ]
                        break

                with self.assertRaisesRegex(ValueError, claim_name):
                    builder.build_statement(manifest)

    def test_rejects_duplicate_scoped_surface_rows(self) -> None:
        manifest = copy.deepcopy(self.load_manifest())
        manifest["post_v1_or_excluded_surfaces"] = [
            *manifest["post_v1_or_excluded_surfaces"],
            "obelisk.inventory_items_mutation.v1",
        ]

        with self.assertRaisesRegex(ValueError, "duplicate surface row"):
            builder.build_statement(manifest)

    def test_rejects_scoped_status_not_allowed_by_exclusion_contract(self) -> None:
        manifest = copy.deepcopy(self.load_manifest())
        for surface in manifest["surfaces"]:
            if surface.get("id") == "obelisk.inventory_items_mutation.v1":
                surface["v1_decision_contract"]["exclusion_requires"] = [
                    "the v1 release statement names obelisk.inventory_items_mutation.v1 as excluded",
                    "the v1 release statement states that no Inventory SDK is included in v1",
                ]
                break

        with self.assertRaisesRegex(ValueError, "is not allowed by exclusion contract outcomes"):
            builder.build_statement(manifest)

    def test_rejects_p0_dependency_chain_rows(self) -> None:
        manifest = copy.deepcopy(self.load_manifest())
        manifest["post_v1_or_excluded_surfaces"] = [
            *manifest["post_v1_or_excluded_surfaces"],
            "obelisk.player_identity.v1",
        ]

        with self.assertRaisesRegex(ValueError, "cannot emit P0 dependency-chain surface"):
            builder.build_statement(manifest)

    def test_rejects_promoted_experimental_rows(self) -> None:
        manifest = copy.deepcopy(self.load_manifest())
        manifest["post_v1_or_excluded_surfaces"] = [
            *manifest["post_v1_or_excluded_surfaces"],
            "obelisk.gameplay_policy_event.v1",
        ]
        manifest["v1_sdk_completion_blockers"] = [
            *manifest["v1_sdk_completion_blockers"],
            "obelisk.gameplay_policy_event.v1",
        ]

        with self.assertRaisesRegex(ValueError, "cannot emit promoted-experimental surface"):
            builder.build_statement(manifest)

    def test_rejects_protected_server_output_path(self) -> None:
        with self.assertRaisesRegex(SystemExit, "must not write under protected server root"):
            builder.write_statement(
                Path("/servidor/ark/serverfiles/scoped-release-statement.md"),
                "# draft\n",
            )

    def test_rejects_symlinked_protected_server_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "live-root"
            link.symlink_to("/servidor/ark/obelisk")

            with self.assertRaisesRegex(SystemExit, "must not write under protected server root"):
                builder.write_statement(link / "scoped-release-statement.md", "# draft\n")


if __name__ == "__main__":
    unittest.main()
