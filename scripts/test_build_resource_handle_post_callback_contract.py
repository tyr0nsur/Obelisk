#!/usr/bin/env python3
"""Tests for build_resource_handle_post_callback_contract.py."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import build_resource_handle_post_callback_contract as builder


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


class ResourceHandlePostCallbackContractBuilderTests(unittest.TestCase):
    def test_builds_fail_closed_internal_contract(self) -> None:
        payload = builder.build_contract(
            source_revalidation(),
            capture_id="post-callback-test",
            evidence_pack_id="post-callback-pack",
        )

        self.assertEqual(payload["schema"], builder.SCHEMA)
        self.assertEqual(payload["output_artifact_identity"]["artifact_kind"], builder.SCHEMA)
        self.assertRegex(payload["output_artifact_identity"]["artifact_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(payload["contract"]["subject"], "InternalUObjectRevalidationCandidate")
        self.assertEqual(payload["contract"]["post_callback_lookup"], "rejected")
        self.assertEqual(payload["contract"]["post_callback_behavior"]["lookup_attempt"], "fail_closed")
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_resource_handle_ready"])
        self.assertFalse(payload["post_callback_resource_handle_ready"])
        self.assertFalse(payload["post_callback_lookup_ready"])
        self.assertEqual(payload["promotion_gate"]["ready"], False)
        self.assertIn("candidate_only_post_callback_rejection_contract", payload["promotion_gate"]["blockers"])

    def test_rejects_source_without_output_identity(self) -> None:
        source = source_revalidation()
        source.pop("output_artifact_identity")

        with self.assertRaises(SystemExit):
            builder.build_contract(source, capture_id="post-callback-test", evidence_pack_id="post-callback-pack")

    def test_rejects_source_post_callback_overclaim(self) -> None:
        source = source_revalidation()
        source["post_callback_resource_handle_ready"] = True

        with self.assertRaises(SystemExit):
            builder.build_contract(source, capture_id="post-callback-test", evidence_pack_id="post-callback-pack")

    def test_rejects_source_public_runtime_v1_alias_overclaims(self) -> None:
        for key, value in (
            ("publicResourceHandleReady", True),
            ("publicResourceLookupReady", True),
            ("runtime_resource_handle_enabled", "yes"),
            ("stableClaimAllowed", True),
            ("v1ObjectLookupPromoted", "promoted"),
            ("runtimeObjectSamplesPresent", True),
        ):
            with self.subTest(key=key):
                source = source_revalidation()
                source["alias_claims"] = {key: value}

                with self.assertRaises(SystemExit):
                    builder.build_contract(source, capture_id="post-callback-test", evidence_pack_id="post-callback-pack")


if __name__ == "__main__":
    unittest.main()
