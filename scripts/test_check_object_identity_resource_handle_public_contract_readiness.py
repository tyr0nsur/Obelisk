#!/usr/bin/env python3
"""Tests for check_object_identity_resource_handle_public_contract_readiness.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_object_identity_resource_handle_public_contract_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "object_identity_resource_handle_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
PUBLIC_EVENTS = REPO_ROOT / "docs" / "public_gameplay_events.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"


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


def write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class ObjectIdentityResourceHandlePublicContractReadinessTests(unittest.TestCase):
    def test_current_contract_is_valid_planning_only_blocked(self) -> None:
        result = run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_resource_handle_ready"])
        self.assertFalse(report["post_callback_resource_handle_ready"])
        self.assertFalse(report["serialPolicyReady"])
        self.assertFalse(report["resourceLookupReady"])
        self.assertFalse(report["postCallbackHandleReady"])
        self.assertFalse(report["objectIdentityReady"])
        self.assertFalse(report["runtimeSampleReady"])
        self.assertFalse(report["runtimeRejectedObjectSamplesReady"])
        self.assertFalse(report["lookupPrivacyReady"])
        self.assertFalse(report["lifetimeSemanticsReady"])
        self.assertFalse(report["resourceHandleLifetimeSemanticsReady"])
        self.assertEqual(
            report["strict_next_blocker"],
            "runtime rejected object samples, runtime serial reuse/wraparound semantics, "
            "lookup privacy, and ResourceHandle lifetime semantics under future approved "
            "live-ops brief",
        )
        self.assertEqual(report["offline_serial_post_callback_artifacts"], "candidate-only")
        self.assertFalse(report["offline_artifacts_unlock_public_lookup_identity_runtime_sdk"])
        self.assertFalse(report["runtime_object_negative_samples_ready"])
        self.assertFalse(report["runtime_rejected_object_samples_ready"])
        self.assertFalse(report["serial_reuse_ready"])
        self.assertFalse(report["serial_wraparound_ready"])
        self.assertFalse(report["lookup_privacy_ready"])
        self.assertFalse(report["lifetime_semantics_ready"])
        self.assertFalse(report["resource_handle_lifetime_semantics_ready"])
        self.assertFalse(report["post_callback_lookup_safety_ready"])
        self.assertFalse(report["post_callback_object_validity_ready"])
        self.assertFalse(report["post_callback_validity_ready"])
        self.assertFalse(report["public_promotion_evidence_counting_allowed"])
        self.assertFalse(report["complete_sdk_counting_allowed"])
        self.assertEqual(report["accepted_public_promotion_evidence_count"], 0)

        next_evidence_contract = report["next_evidence_contract"]
        self.assertEqual(next_evidence_contract["status"], "planning-only-not-approval")
        self.assertEqual(next_evidence_contract["offline_artifacts_policy"], "candidate-only")
        self.assertFalse(next_evidence_contract["counts_toward_public_promotion"])
        self.assertFalse(next_evidence_contract["counts_toward_complete_sdk_claim"])
        self.assertEqual(
            next_evidence_contract["required_future_evidence"],
            [
                "runtime rejected object samples",
                "runtime serial reuse/wraparound semantics",
                "lookup privacy boundary",
                "ResourceHandle lifetime semantics",
                "post-callback lookup safety and fail-closed handle invalidation",
            ],
        )
        blocker_contract = report["public_promotion_blocker_contract"]
        self.assertEqual(blocker_contract["status"], "blocked")
        self.assertTrue(blocker_contract["required_before_public_lookup"])
        self.assertFalse(blocker_contract["counts_toward_public_promotion"])
        self.assertEqual(
            blocker_contract["required_public_promotion_blockers"],
            [
                "runtime rejected object samples",
                "runtime serial reuse/wraparound semantics",
                "lookup privacy boundary",
                "ResourceHandle lifetime semantics",
            ],
        )

        missing = report["public_promotion_missing_evidence"]
        self.assertEqual(missing["status"], "blocked")
        self.assertEqual(missing["accepted_public_promotion_evidence_count"], 0)
        self.assertFalse(missing["counts_toward_public_promotion"])
        self.assertFalse(missing["counts_toward_complete_sdk_claim"])
        self.assertEqual(
            [item["id"] for item in missing["missing_evidence"]],
            [
                "runtime_object_negative_samples",
                "serial_reuse_wraparound_semantics",
                "lookup_privacy_boundary",
                "resource_handle_lifetime_semantics",
                "post_callback_lookup_safety",
            ],
        )
        serial_evidence = report["serial_reuse_wraparound_evidence"]
        self.assertFalse(serial_evidence["ready"])
        self.assertIn(
            "wraparound-unknown handling that rejects instead of resolving public handles",
            serial_evidence["requires"],
        )
        lookup_privacy_evidence = report["lookup_privacy_evidence"]
        self.assertFalse(lookup_privacy_evidence["ready"])
        self.assertIn(
            "redacted, non-enumerating failure categories that do not leak raw UObject, FName, or GObjects state",
            lookup_privacy_evidence["requires"],
        )
        lifetime_evidence = report["resource_handle_lifetime_semantics_evidence"]
        self.assertFalse(lifetime_evidence["ready"])
        self.assertIn(
            "fail-closed invalidation after object destruction, serial mismatch, callback return, and plugin unload",
            lifetime_evidence["requires"],
        )
        post_callback_evidence = report["post_callback_lookup_safety_evidence"]
        self.assertFalse(post_callback_evidence["ready"])
        self.assertIn(
            "owner-token scoped cleanup after callback return and plugin unload",
            post_callback_evidence["requires"],
        )
        self.assertEqual(
            report["minimum_runtime_evidence_pair"]["schemas"],
            [
                "obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1",
                "obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1",
            ],
        )

    def test_rejects_decisions_that_enable_public_resource_handles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["public_header_allowed"] = True
            decisions["public_resource_handle_ready"] = True
            decisions["required_public_contract"] = ["ObeliskResourceHandle"]
            decisions["serialPolicyReady"] = True
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_resource_handle_ready_not_false", report["blockers"])
        self.assertIn("required_public_contract_not_empty", report["blockers"])
        self.assertIn("serialPolicyReady_not_false", report["blockers"])

    def test_rejects_decisions_with_missing_strict_runtime_blocker_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["strict_next_blocker"] = "offline serial policy accepted"
            decisions["offline_serial_post_callback_artifacts"] = "promoted"
            decisions["offline_artifacts_unlock_public_lookup_identity_runtime_sdk"] = True
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("strict_next_blocker_not_runtime_samples_serial_privacy_lifetime", report["blockers"])
        self.assertIn("offline_serial_post_callback_artifacts_not_candidate_only", report["blockers"])
        self.assertIn("offline_artifacts_unlock_public_lookup_identity_runtime_sdk_not_false", report["blockers"])

    def test_rejects_decisions_that_mark_runtime_privacy_or_lifetime_blockers_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["runtimeRejectedObjectSamplesReady"] = True
            decisions["lookupPrivacyReady"] = True
            decisions["lifetimeSemanticsReady"] = True
            decisions["resourceHandleLifetimeSemanticsReady"] = True
            decisions["required_public_promotion_blockers"] = [
                "runtime rejected object samples",
                "runtime serial reuse/wraparound semantics",
            ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("runtimeRejectedObjectSamplesReady_not_false", report["blockers"])
        self.assertIn("lookupPrivacyReady_not_false", report["blockers"])
        self.assertIn("lifetimeSemanticsReady_not_false", report["blockers"])
        self.assertIn("resourceHandleLifetimeSemanticsReady_not_false", report["blockers"])
        self.assertIn("required_public_promotion_blockers_incomplete", report["blockers"])

    def test_rejects_lookup_privacy_and_lifetime_readiness_aliases_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = (
                "Lookup privacy is approved and lifetime semantics are ready for public lookup."
            )
            decisions["metadata"] = {
                "lookupPrivacyBoundaryReady": True,
                "publicLookupPrivacyReady": True,
                "ownerScopedLookupPrivacyReady": "approved",
                "resourceHandleLifetimeReady": True,
                "handleLifetimeReady": "supported",
                "invalidationSemanticsReady": "validated",
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        for key in (
            "lookupPrivacyBoundaryReady",
            "publicLookupPrivacyReady",
            "ownerScopedLookupPrivacyReady",
            "resourceHandleLifetimeReady",
            "handleLifetimeReady",
            "invalidationSemanticsReady",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_positive_resource_handle_claim_in_decisions_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = (
                "ResourceHandle ready for public SDK lookup and post-callback object correlation."
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_resource_handle_ships_claim_in_decisions_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = (
                "v1 ships ResourceHandle object identity for post-callback object correlation."
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_unblocking_resource_handle_readiness_text_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = "ResourceHandle is not blocked and public SDK ready for v1 lookup."
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_nested_public_contract_field_for_resource_handle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["metadata"] = {
                "public_contract": ["ObeliskResourceHandle"],
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "decisions_forbidden_public_contract_field:$.decisions.metadata.public_contract",
            report["blockers"],
        )

    def test_rejects_positive_resource_handle_metadata_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["metadata"] = {
                "resource_handle": "ready",
                "public_object_lookup_ready": True,
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "forbidden_positive_resource_handle_claim:$.decisions.metadata.resource_handle",
            report["blockers"],
        )
        self.assertIn(
            "forbidden_positive_resource_handle_claim:$.decisions.metadata.public_object_lookup_ready",
            report["blockers"],
        )

    def test_rejects_generic_readiness_metadata_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["metadata"] = {
                "public_sdk_ready": True,
                "runtime_ready": True,
                "promotion_ready": True,
                "v1_sdk_ready": True,
                "release_ready": True,
                "public_abi_ready": True,
                "stable_claim_allowed": True,
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        for key in (
            "public_sdk_ready",
            "runtime_ready",
            "promotion_ready",
            "v1_sdk_ready",
            "release_ready",
            "public_abi_ready",
            "stable_claim_allowed",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_public_runtime_v1_alias_metadata_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["metadata"] = {
                "publicResourceHandleReady": True,
                "publicResourceLookupReady": True,
                "runtime_resource_handle_enabled": "yes",
                "v1ObjectLookupPromoted": "promoted",
                "runtimeObjectSamplesPresent": True,
                "serialReuseWraparoundSafetyProven": True,
                "serialPolicyReady": True,
                "resourceLookupReady": True,
                "postCallbackHandleReady": True,
                "objectIdentityReady": True,
                "runtimeSampleReady": True,
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        for key in (
            "publicResourceHandleReady",
            "publicResourceLookupReady",
            "runtime_resource_handle_enabled",
            "v1ObjectLookupPromoted",
            "runtimeObjectSamplesPresent",
            "serialReuseWraparoundSafetyProven",
            "serialPolicyReady",
            "resourceLookupReady",
            "postCallbackHandleReady",
            "objectIdentityReady",
            "runtimeSampleReady",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_post_callback_lookup_and_serial_wraparound_claims_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = (
                "Post-callback lookup safety is validated and serial wraparound policy is ready "
                "for public lookup."
            )
            decisions["metadata"] = {
                "runtimeObjectNegativeSamplesReady": True,
                "serialReuseReady": True,
                "serialWraparoundReady": True,
                "postCallbackLookupSafetyReady": True,
                "postCallbackObjectValidityReady": True,
                "slotReuseSafetyReady": True,
                "crossFrameLookupReady": True,
                "staleHandleSafetyReady": True,
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        for key in (
            "runtimeObjectNegativeSamplesReady",
            "serialReuseReady",
            "serialWraparoundReady",
            "postCallbackLookupSafetyReady",
            "postCallbackObjectValidityReady",
            "slotReuseSafetyReady",
            "crossFrameLookupReady",
            "staleHandleSafetyReady",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_evidence_category_readiness_claims_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claims"] = [
                "Zero-serial samples and strict serial policy prove public SDK readiness.",
                "Future runtime observation plan makes v1 completion supported.",
            ]
            decisions["metadata"] = {
                "strictSerialPolicyPublicSdkReady": True,
                "zeroSerialSamplesRuntimeReady": "satisfied",
                "publicGObjectsReady": "supported",
                "futureRuntimeObservationPlanV1Complete": True,
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        for key in (
            "strictSerialPolicyPublicSdkReady",
            "zeroSerialSamplesRuntimeReady",
            "publicGObjectsReady",
            "futureRuntimeObservationPlanV1Complete",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_candidate_serial_policy_and_offline_zero_serial_shortcut_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["metadata"] = {
                "candidate_only_serial_policy_artifact": {
                    "status": "approved-runtime-only",
                    "counts_toward_public_promotion": True,
                    "accepted_public_promotion_evidence_count": 1,
                },
                "offline_zero_serial_cohort": {
                    "authorization_status": "authorized",
                    "runtime_ready": True,
                },
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "decisions_shortcut_artifact_public_readiness_claim:candidate_serial_policy_artifact:"
            "$.decisions.metadata.candidate_only_serial_policy_artifact.status",
            report["blockers"],
        )
        self.assertIn(
            "decisions_shortcut_artifact_public_readiness_claim:candidate_serial_policy_artifact:"
            "$.decisions.metadata.candidate_only_serial_policy_artifact.counts_toward_public_promotion",
            report["blockers"],
        )
        self.assertIn(
            "decisions_shortcut_artifact_public_readiness_claim:candidate_serial_policy_artifact:"
            "$.decisions.metadata.candidate_only_serial_policy_artifact.accepted_public_promotion_evidence_count",
            report["blockers"],
        )
        self.assertIn(
            "decisions_shortcut_artifact_public_readiness_claim:offline_zero_serial_cohort:"
            "$.decisions.metadata.offline_zero_serial_cohort.authorization_status",
            report["blockers"],
        )
        self.assertIn(
            "decisions_shortcut_artifact_public_readiness_claim:offline_zero_serial_cohort:"
            "$.decisions.metadata.offline_zero_serial_cohort.runtime_ready",
            report["blockers"],
        )

    def test_rejects_resource_handle_blocker_clearance_claims_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = "ResourceHandle blockers cleared."
            decisions["metadata"] = {
                "resourceHandleBlockers": "cleared",
                "objectIdentityGate": "passed",
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        for key in ("resourceHandleBlockers", "objectIdentityGate"):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_runtime_sample_route_and_sdk_progress_claims_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = (
                "Route acceptance makes public lookup and SDK progress ready for complete SDK readiness."
            )
            decisions["metadata"] = {
                "approvedRuntimeSamplesReady": True,
                "routeAcceptanceReady": True,
                "sdkProgress": "accepted",
                "completeSdkReadiness": "ready",
                "publicLookupReady": True,
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        for key in (
            "approvedRuntimeSamplesReady",
            "routeAcceptanceReady",
            "sdkProgress",
            "completeSdkReadiness",
            "publicLookupReady",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_package_shape_side_lane_planning_and_owner_token_handle_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = (
                "Package-shape side-lane planning manifest unlocks v1 completion "
                "for public handle readiness."
            )
            decisions["metadata"] = {
                "packageShapeReady": True,
                "sideLaneReady": "ready",
                "planningManifestReady": "approved",
                "identityOwnerTokenReady": "supported",
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        for key in (
            "packageShapeReady",
            "sideLaneReady",
            "planningManifestReady",
            "identityOwnerTokenReady",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_gate_serial_flag_caller_support_and_runtime_status_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["metadata"] = {
                "offline_artifact_gate": {
                    "status": "accepted",
                    "support_tier": "supported",
                },
                "serialScanStatus": "accepted",
                "uobjectFlagReportStatus": "approved",
                "weakHelperCallerRowsStatus": "validated",
                "packageSupportLabel": "supported",
                "runtimeStatus": "ready",
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "decisions_shortcut_artifact_public_readiness_claim:offline_artifact_gate_acceptance:"
            "$.decisions.metadata.offline_artifact_gate.status",
            report["blockers"],
        )
        self.assertIn(
            "decisions_shortcut_artifact_public_readiness_claim:offline_artifact_gate_acceptance:"
            "$.decisions.metadata.offline_artifact_gate.support_tier",
            report["blockers"],
        )
        for key in (
            "serialScanStatus",
            "uobjectFlagReportStatus",
            "weakHelperCallerRowsStatus",
            "packageSupportLabel",
            "runtimeStatus",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.decisions.metadata.{key}",
                report["blockers"],
            )

    def test_rejects_public_sdk_surface_promotion_or_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "stable"
                    surface["public_contract"] = ["ObeliskResourceHandle"]
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("surface_status_not_post_v1", report["blockers"])
        self.assertIn("surface_support_tier_not_blocked", report["blockers"])
        self.assertIn("surface_public_contract_not_empty", report["blockers"])

    def test_rejects_positive_resource_handle_claim_in_surface_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["evidence"]["claim"] = (
                        "ResourceHandle ready for public SDK lookup and post-callback object correlation"
                    )
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("surface_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_resource_handle_ships_claim_in_surface_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["evidence"]["claim"] = (
                        "v1 ships ResourceHandle object identity for post-callback object correlation."
                    )
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("surface_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_promoted_descriptor_surface_resource_handle_contract_and_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.descriptors.v1":
                    surface["public_contract"].append("ObeliskResourceHandle")
                    surface["evidence"]["claim"] = (
                        "Descriptor metadata now includes public resource lookup API readiness."
                    )
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("promoted_descriptor_surface_forbidden_public_contract:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        self.assertTrue(
            any(
                blocker.startswith("surface_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_surface_next_evidence_contract_that_drops_post_callback_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    contract = surface["v1_decision_contract"]["next_evidence_contract"]
                    contract["required_future_evidence"] = [
                        "runtime object negative samples",
                        "runtime serial reuse/wraparound semantics",
                    ]
                    contract["counts_toward_public_promotion"] = True
                    contract["counts_toward_complete_sdk_claim"] = True
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "surface_next_evidence_contract_required_future_evidence_incomplete",
            report["blockers"],
        )
        self.assertIn(
            "surface_next_evidence_contract_counts_toward_public_promotion_not_false",
            report["blockers"],
        )
        self.assertIn(
            "surface_next_evidence_contract_counts_toward_complete_sdk_claim_not_false",
            report["blockers"],
        )

    def test_rejects_positive_resource_handle_metadata_in_surface_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["resource_handle_ready"] = True
                    surface["object_lookup"] = "ready"
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "forbidden_positive_resource_handle_claim:"
            "$.surfaces[obelisk.object_identity_resource_handle.v1].resource_handle_ready",
            report["blockers"],
        )
        self.assertIn(
            "forbidden_positive_resource_handle_claim:"
            "$.surfaces[obelisk.object_identity_resource_handle.v1].object_lookup",
            report["blockers"],
        )

    def test_rejects_generic_readiness_metadata_in_surface_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["metadata"] = {
                        "public_sdk_ready": True,
                        "runtime_ready": True,
                        "promotion_ready": True,
                        "v1_sdk_ready": True,
                        "release_ready": True,
                        "public_abi_ready": True,
                        "stable_claim_allowed": True,
                    }
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        for key in (
            "public_sdk_ready",
            "runtime_ready",
            "promotion_ready",
            "v1_sdk_ready",
            "release_ready",
            "public_abi_ready",
            "stable_claim_allowed",
        ):
            self.assertIn(
                "forbidden_positive_resource_handle_claim:"
                f"$.surfaces[obelisk.object_identity_resource_handle.v1].metadata.{key}",
                report["blockers"],
            )

    def test_rejects_public_runtime_v1_alias_metadata_in_surface_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["metadata"] = {
                        "publicResourceHandleReady": True,
                        "publicResourceLookupReady": True,
                        "runtime_resource_handle_enabled": "yes",
                        "v1ObjectLookupPromoted": "promoted",
                        "runtimeObjectSamplesPresent": True,
                        "serialReuseWraparoundSafetyProven": True,
                        "serialPolicyReady": True,
                        "resourceLookupReady": True,
                        "postCallbackHandleReady": True,
                        "objectIdentityReady": True,
                        "runtimeSampleReady": True,
                    }
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        for key in (
            "publicResourceHandleReady",
            "publicResourceLookupReady",
            "runtime_resource_handle_enabled",
            "v1ObjectLookupPromoted",
            "runtimeObjectSamplesPresent",
            "serialReuseWraparoundSafetyProven",
            "serialPolicyReady",
            "resourceLookupReady",
            "postCallbackHandleReady",
            "objectIdentityReady",
            "runtimeSampleReady",
        ):
            self.assertIn(
                "forbidden_positive_resource_handle_claim:"
                f"$.surfaces[obelisk.object_identity_resource_handle.v1].metadata.{key}",
                report["blockers"],
            )

    def test_rejects_static_global_and_helper_flag_surface_readiness_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["evidence"]["claim"] = (
                        "Static globals and source helper flags establish post-callback safety "
                        "and promotion readiness."
                    )
                    surface["metadata"] = {
                        "sourceHelperFlagsPostCallbackSafetyProven": True,
                        "runtimeRejectionSamplesLookupReady": True,
                    }
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("surface_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        for key in (
            "sourceHelperFlagsPostCallbackSafetyProven",
            "runtimeRejectionSamplesLookupReady",
        ):
            self.assertIn(
                "forbidden_positive_resource_handle_claim:"
                f"$.surfaces[obelisk.object_identity_resource_handle.v1].metadata.{key}",
                report["blockers"],
            )

    def test_rejects_lookup_privacy_and_lifetime_surface_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["evidence"]["claim"] = (
                        "Lookup privacy is approved and lifetime semantics are ready for public lookup."
                    )
                    surface["metadata"] = {
                        "lookupPrivacyBoundaryReady": True,
                        "publicLookupPrivacyReady": True,
                        "resourceHandleLifetimeReady": True,
                        "invalidationSemanticsReady": "validated",
                    }
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("surface_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        for key in (
            "lookupPrivacyBoundaryReady",
            "publicLookupPrivacyReady",
            "resourceHandleLifetimeReady",
            "invalidationSemanticsReady",
        ):
            self.assertIn(
                "forbidden_positive_resource_handle_claim:"
                f"$.surfaces[obelisk.object_identity_resource_handle.v1].metadata.{key}",
                report["blockers"],
            )

    def test_rejects_scoped_release_and_runtime_evidence_status_shortcuts_in_surface_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["metadata"] = {
                        "scoped_release_statement": {
                            "status": "accepted",
                            "claim_allowed": True,
                        },
                        "runtime_evidence": {
                            "authorization_status": "approved-runtime-evidence",
                            "public_promotion_evidence_counting_allowed": True,
                        },
                    }
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "surface_shortcut_artifact_public_readiness_claim:scoped_release_statement:"
            "$.surfaces[obelisk.object_identity_resource_handle.v1].metadata."
            "scoped_release_statement.status",
            report["blockers"],
        )
        self.assertIn(
            "surface_shortcut_artifact_public_readiness_claim:scoped_release_statement:"
            "$.surfaces[obelisk.object_identity_resource_handle.v1].metadata."
            "scoped_release_statement.claim_allowed",
            report["blockers"],
        )
        self.assertIn(
            "surface_shortcut_artifact_public_readiness_claim:runtime_evidence_authorization_status:"
            "$.surfaces[obelisk.object_identity_resource_handle.v1].metadata."
            "runtime_evidence.authorization_status",
            report["blockers"],
        )
        self.assertIn(
            "surface_shortcut_artifact_public_readiness_claim:runtime_evidence_authorization_status:"
            "$.surfaces[obelisk.object_identity_resource_handle.v1].metadata."
            "runtime_evidence.public_promotion_evidence_counting_allowed",
            report["blockers"],
        )

    def test_rejects_public_header_resource_handle_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header_path = root / "ObeliskApi.h"
            header_path.write_text(
                HEADER.read_text(encoding="utf-8")
                + "\ntypedef struct ObeliskResourceHandle { uint64_t id; } ObeliskResourceHandle;\n"
                + "bool ResolveResource(ObeliskResourceHandle handle, void** out);\n",
                encoding="utf-8",
            )

            result = run_checker("--public-header", str(header_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_contains_object_identity_or_resource_handle_symbol", report["blockers"])

    def test_header_scan_ignores_comments_and_resource_kind_supersets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header_path = root / "ObeliskApi.h"
            header_path.write_text(
                "/* ObeliskResourceHandle, UObject, FName, GObjects remain blocked. */\n"
                "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY (1ull << 0)\n"
                "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY (1ull << 1)\n"
                "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP (1ull << 2)\n"
                "typedef struct ObeliskResourceKindDescriptor {\n"
                "  uint32_t resource_kind;\n"
                "  uint64_t flags;\n"
                "} ObeliskResourceKindDescriptor;\n",
                encoding="utf-8",
            )

            result = run_checker("--public-header", str(header_path))
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])

    def test_rejects_public_events_that_turn_resource_kind_into_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = json.loads(PUBLIC_EVENTS.read_text(encoding="utf-8"))
            events["metadata_surfaces"][0]["descriptor_fields"].append("resource_handle")
            events["metadata_surfaces"][0]["resource_handle_ready"] = True
            events_path = write_json(root, "events.json", events)

            result = run_checker("--public-events", str(events_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("resource_kind_descriptor_identity_or_lookup_field_present", report["blockers"])
        self.assertIn(
            "forbidden_positive_resource_handle_claim:$.metadata_surfaces[0].resource_handle_ready",
            report["blockers"],
        )

    def test_rejects_public_events_copied_resource_kind_descriptor_shortcut_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = json.loads(PUBLIC_EVENTS.read_text(encoding="utf-8"))
            events["metadata_surfaces"][0]["copied_resource_kind_descriptor_evidence"] = {
                "status": "approved",
                "counts_toward_public_promotion": True,
            }
            events_path = write_json(root, "events.json", events)

            result = run_checker("--public-events", str(events_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "public_events_shortcut_artifact_public_readiness_claim:copied_resource_kind_descriptor:"
            "$.public_events.metadata_surfaces[0].copied_resource_kind_descriptor_evidence.status",
            report["blockers"],
        )
        self.assertIn(
            "public_events_shortcut_artifact_public_readiness_claim:copied_resource_kind_descriptor:"
            "$.public_events.metadata_surfaces[0].copied_resource_kind_descriptor_evidence."
            "counts_toward_public_promotion",
            report["blockers"],
        )

    def test_rejects_nested_public_event_resource_handle_lookup_readiness_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = json.loads(PUBLIC_EVENTS.read_text(encoding="utf-8"))
            events["nested_claim"] = {
                "notes": [
                    "ResourceHandle lookup is ready for the public SDK.",
                ]
            }
            events_path = write_json(root, "events.json", events)

            result = run_checker("--public-events", str(events_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("public_events_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_public_runtime_v1_alias_metadata_in_public_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = json.loads(PUBLIC_EVENTS.read_text(encoding="utf-8"))
            events["metadata_surfaces"][0]["publicResourceHandleReady"] = True
            events["metadata_surfaces"][0]["publicResourceLookupReady"] = True
            events["metadata_surfaces"][0]["runtime_resource_handle_enabled"] = "yes"
            events["metadata_surfaces"][0]["v1ObjectLookupPromoted"] = "promoted"
            events["metadata_surfaces"][0]["runtimeObjectSamplesPresent"] = True
            events["metadata_surfaces"][0]["serialReuseWraparoundSafetyProven"] = True
            events["metadata_surfaces"][0]["serialPolicyReady"] = True
            events["metadata_surfaces"][0]["resourceLookupReady"] = True
            events["metadata_surfaces"][0]["postCallbackHandleReady"] = True
            events["metadata_surfaces"][0]["objectIdentityReady"] = True
            events["metadata_surfaces"][0]["runtimeSampleReady"] = True
            events_path = write_json(root, "events.json", events)

            result = run_checker("--public-events", str(events_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        for key in (
            "publicResourceHandleReady",
            "publicResourceLookupReady",
            "runtime_resource_handle_enabled",
            "v1ObjectLookupPromoted",
            "runtimeObjectSamplesPresent",
            "serialReuseWraparoundSafetyProven",
            "serialPolicyReady",
            "resourceLookupReady",
            "postCallbackHandleReady",
            "objectIdentityReady",
            "runtimeSampleReady",
        ):
            self.assertIn(
                f"forbidden_positive_resource_handle_claim:$.metadata_surfaces[0].{key}",
                report["blockers"],
            )

    def test_rejects_public_event_gobjects_and_runtime_observation_readiness_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = json.loads(PUBLIC_EVENTS.read_text(encoding="utf-8"))
            events["metadata_surfaces"][0]["claim"] = (
                "Public GObjects lookup is included after future runtime observation completion."
            )
            events["metadata_surfaces"][0]["publicGObjectsReady"] = True
            events_path = write_json(root, "events.json", events)

            result = run_checker("--public-events", str(events_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("public_events_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        self.assertIn(
            "forbidden_positive_resource_handle_claim:$.metadata_surfaces[0].publicGObjectsReady",
            report["blockers"],
        )

    def test_rejects_symlinked_input_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "decisions.json"
            real.write_text(DECISIONS.read_text(encoding="utf-8"), encoding="utf-8")
            link = root / "decisions-link.json"
            link.symlink_to(real)

            result = run_checker("--decisions", str(link), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)


if __name__ == "__main__":
    unittest.main()
