#!/usr/bin/env python3
"""Tests for build_resource_handle_serial_policy.py."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys
from types import SimpleNamespace

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import build_resource_handle_serial_policy as builder


def source_revalidation() -> dict[str, object]:
    return {
        "schema": builder.RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
        "output_artifact_identity": {
            "artifact_kind": builder.RESOURCE_HANDLE_REVALIDATION_EVALUATOR_SCHEMA,
            "artifact_sha256": "a" * 64,
            "capture_id": "source-capture",
            "evidence_pack_id": "source-pack",
        },
        "artifact_identity": {
            "required": True,
            "hash_count": 2,
            "hashes": ["b" * 64, "c" * 64],
            "complete_input_count": 3,
            "missing_or_partial_input_count": 0,
            "invalid_input_count": 0,
        },
        "reconciliation_summary": {
            "sample_count": 44,
            "accepted_sample_count": 44,
            "rejected_sample_count": 0,
            "membership_pass_count": 44,
            "serial_candidate_zero_count": 0,
            "serial_candidate_nonzero_count": 44,
            "serial_candidate_missing_count": 0,
        },
        "evidence_checks": {
            "serial_reuse_or_wraparound_policy_present": False,
        },
        "promotion_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "internal_uobject_revalidation_candidate": {
            "schema": builder.INTERNAL_UOBJECT_REVALIDATION_CANDIDATE_SCHEMA,
            "accepted": True,
            "candidate_level": "internal_static_candidate",
            "binary_sha256": "d" * 64,
            "source_post_callback_resource_handle_ready": False,
            "candidate": builder.INTERNAL_UOBJECT_REVALIDATION_CONTRACT,
        },
    }


class ResourceHandleSerialPolicyBuilderTests(unittest.TestCase):
    def test_builds_candidate_only_fail_closed_policy(self) -> None:
        payload = builder.build_policy(
            source_revalidation(),
            capture_id="serial-policy-test",
            evidence_pack_id="serial-policy-pack",
        )

        self.assertEqual(payload["schema"], builder.SCHEMA)
        self.assertEqual(payload["output_artifact_identity"]["artifact_kind"], builder.SCHEMA)
        self.assertRegex(payload["output_artifact_identity"]["artifact_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(payload["serial_policy"]["subject"], "InternalUObjectRevalidationCandidate")
        self.assertEqual(payload["serial_policy"]["fail_closed_rules"]["zero_serial"], "reject")
        self.assertEqual(payload["serial_policy"]["fail_closed_rules"]["serial_mismatch"], "reject")
        self.assertEqual(payload["serial_policy"]["fail_closed_rules"]["wraparound_unknown"], "reject")
        self.assertEqual(payload["serial_policy"]["fail_closed_rules"]["slot_reuse_without_fresh_serial"], "reject")
        self.assertTrue(payload["contract_checks"]["serial_reuse_or_wraparound_policy_present"])
        self.assertFalse(payload["contract_checks"]["serial_reuse_or_wraparound_safety_proven"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_resource_handle_ready"])
        self.assertFalse(payload["post_callback_resource_handle_ready"])
        self.assertEqual(payload["promotion_gate"]["ready"], False)
        self.assertIn("candidate_only_serial_reuse_wraparound_policy", payload["promotion_gate"]["blockers"])

    def test_canonical_cases_fail_closed_except_fresh_frame_local_match(self) -> None:
        payload = builder.build_policy(
            source_revalidation(),
            capture_id="serial-policy-test",
            evidence_pack_id="serial-policy-pack",
        )
        cases = {case["case"]: case for case in payload["decision_cases"]}

        for case_name in (
            "zero_serial",
            "serial_mismatch",
            "wraparound_unknown",
            "slot_reuse_without_fresh_serial",
            "post_callback_attempt",
        ):
            with self.subTest(case=case_name):
                self.assertEqual(cases[case_name]["decision"], "reject")
                self.assertTrue(cases[case_name]["fail_closed"])

        self.assertIn("zero_serial", cases["zero_serial"]["reasons"])
        self.assertIn("serial_mismatch", cases["serial_mismatch"]["reasons"])
        self.assertIn("wraparound_unknown", cases["wraparound_unknown"]["reasons"])
        self.assertIn("slot_reuse_without_fresh_serial", cases["slot_reuse_without_fresh_serial"]["reasons"])
        self.assertEqual(cases["fresh_nonzero_match_same_frame"]["decision"], "allow_candidate_frame_local_only")

    def test_rejects_source_with_zero_serial_candidates(self) -> None:
        source = source_revalidation()
        source["reconciliation_summary"]["serial_candidate_zero_count"] = 1  # type: ignore[index]

        with self.assertRaises(SystemExit):
            builder.build_policy(source, capture_id="serial-policy-test", evidence_pack_id="serial-policy-pack")

    def test_rejects_source_that_already_claims_policy(self) -> None:
        source = source_revalidation()
        source["evidence_checks"]["serial_reuse_or_wraparound_policy_present"] = True  # type: ignore[index]

        with self.assertRaises(SystemExit):
            builder.build_policy(source, capture_id="serial-policy-test", evidence_pack_id="serial-policy-pack")

    def test_rejects_source_public_handle_overclaim(self) -> None:
        source = source_revalidation()
        source["public_resource_handle_ready"] = True

        with self.assertRaises(SystemExit):
            builder.build_policy(source, capture_id="serial-policy-test", evidence_pack_id="serial-policy-pack")

    def test_rejects_source_public_runtime_v1_alias_overclaims(self) -> None:
        for key, value in (
            ("publicResourceHandleReady", True),
            ("publicResourceLookupReady", True),
            ("runtime_resource_handle_enabled", "yes"),
            ("stableClaimAllowed", True),
            ("v1ResourceHandlePromoted", "promoted"),
            ("serialReuseWraparoundSafetyProven", True),
        ):
            with self.subTest(key=key):
                source = source_revalidation()
                source["alias_claims"] = {key: value}

                with self.assertRaises(SystemExit):
                    builder.build_policy(source, capture_id="serial-policy-test", evidence_pack_id="serial-policy-pack")

    def test_rejects_source_text_and_public_contract_overclaims(self) -> None:
        source = source_revalidation()
        source["metadata"] = {
            "claim": "ResourceHandle is not blocked and public SDK ready for v1 lookup.",
            "public_contract": ["ObeliskResourceHandle"],
        }

        with self.assertRaises(SystemExit):
            builder.build_policy(source, capture_id="serial-policy-test", evidence_pack_id="serial-policy-pack")

    def test_rejects_malformed_source_counts_cleanly(self) -> None:
        source = source_revalidation()
        source["reconciliation_summary"]["serial_candidate_nonzero_count"] = True  # type: ignore[index]

        with self.assertRaises(SystemExit):
            builder.build_policy(source, capture_id="serial-policy-test", evidence_pack_id="serial-policy-pack")

    def test_rejects_unsafe_capture_and_evidence_pack_ids(self) -> None:
        with self.assertRaises(SystemExit):
            builder.validate_safe_identity_args(
                SimpleNamespace(capture_id="../bad", evidence_pack_id="serial-policy-pack")
            )

        with self.assertRaises(SystemExit):
            builder.validate_safe_identity_args(
                SimpleNamespace(capture_id="serial-policy-test", evidence_pack_id="/bad")
            )

    def test_cli_path_guards_reject_protected_server_paths(self) -> None:
        with self.assertRaises(SystemExit):
            builder.reject_protected_input_path(Path("/servidor/ark/live-resourcehandle.json"), "--revalidation")

        with self.assertRaises(SystemExit):
            builder.reject_protected_output_path(Path("/servidor/ark/live-policy.json"), "--output")


if __name__ == "__main__":
    unittest.main()
