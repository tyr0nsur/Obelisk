#!/usr/bin/env python3
"""Tests for evaluate_resource_handle_revalidation.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import evaluate_resource_handle_revalidation as evaluator


def assert_fail_closed_resource_handle_contract(testcase: unittest.TestCase, payload: dict[str, object]) -> None:
    testcase.assertIs(payload["promotion_ready"], False)
    testcase.assertIs(payload["public_resource_handle_ready"], False)
    testcase.assertIs(payload["post_callback_resource_handle_ready"], False)
    testcase.assertIs(payload["uobject_flags_validity_semantics_proven"], False)
    testcase.assertEqual(payload["non_claims"], list(evaluator.RESOURCE_HANDLE_NON_CLAIMS))
    testcase.assertEqual(
        payload["lifetime_blocker_summary"]["blockers"],
        list(evaluator.RESOURCE_HANDLE_LIFETIME_BLOCKERS),
    )
    testcase.assertTrue(set(evaluator.RESOURCE_HANDLE_LIFETIME_BLOCKERS).issubset(set(payload["blockers"])))
    testcase.assertEqual(payload["promotion_gate"]["ready"], False)
    testcase.assertEqual(payload["promotion_gate"]["blockers"], payload["blockers"])


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reconciliation_report(
    *,
    serial_values: list[object],
    sha256: str | None = None,
    artifact_identity_sha256: str | None = None,
    artifact_identity_override: dict[str, object] | None = None,
) -> dict[str, object]:
    samples: list[dict[str, object]] = []
    for number, serial_value in enumerate(serial_values):
        samples.append(
            {
                "label": f"sensitive_label_{number}",
                "index": 25447 + number,
                "status": "candidate-uobject",
                "fuobject_item": "0x1111222233334444",
                "object": "0x5555666677778888",
                "item_dword_0x8": serial_value,
                "item_dword_0xc": 42424242,
                "item_qword_0x8": "0x9999aaaabbbbcccc",
                "object_name": "ServerChat",
                "class_name": "Function",
                "outer_name": "/Script/CoreUObject",
                "membership": {"passes": True, "target": {"index": 25447, "fuobject_item": "0xabab"}},
            }
        )

    payload: dict[str, object] = {
        "schema": evaluator.GOBJECTS_RECONCILIATION_SCHEMA,
        "core": "/servidor/ark/workspace-offline/example/core",
        "inputs": {
            "gobjects_candidate": "0x595b7e0",
            "fname_root_slot": "0x5956f30",
            "sample_indices": [{"label": "chat", "index": 25447}],
        },
        "samples": samples,
        "summary": {
            "sample_count": len(samples),
            "accepted_count": len(samples),
            "rejected_count": 0,
            "membership_pass_count": len(samples),
        },
    }
    if sha256 is not None:
        payload["artifact"] = {"sha256": sha256}
    if artifact_identity_sha256 is not None:
        payload["artifact_identity"] = {
            "artifact_kind": "core",
            "artifact_sha256": artifact_identity_sha256,
            "capture_id": "capture-a",
            "evidence_pack_id": "pack-a",
        }
    if artifact_identity_override is not None:
        payload["artifact_identity"] = artifact_identity_override
    return payload


def static_evidence(
    *,
    coherent: bool,
    sha256: str | None = None,
    artifact_identity_sha256: str | None = None,
    artifact_identity_override: dict[str, object] | None = None,
) -> dict[str, object]:
    blockers = [] if coherent else [evaluator.BLOCKER_MISSING_COHERENT_WINDOW]
    payload: dict[str, object] = {
        "schema": evaluator.STATIC_GLOBAL_EVIDENCE_SCHEMA,
        "binary": {"sha256": sha256} if sha256 is not None else {},
        "candidates": [
            {
                "kind": "gobjects",
                "label": "gobjects",
                "address": "0x595b7e0",
                "static_contract": {
                    "satisfied": coherent,
                    "blockers": blockers,
                    "coherent_window": {"redacted_fixture": True} if coherent else None,
                },
            }
        ],
        "promotion_gate": {"ready": False, "blockers": []},
    }
    if artifact_identity_sha256 is not None:
        payload["artifact_identity"] = {
            "artifact_kind": "objdump",
            "artifact_sha256": artifact_identity_sha256,
            "capture_id": "capture-b",
            "evidence_pack_id": "pack-b",
        }
    if artifact_identity_override is not None:
        payload["artifact_identity"] = artifact_identity_override
    return payload


class ResourceHandleRevalidationEvaluatorTests(unittest.TestCase):
    def test_fail_closed_with_current_style_zero_serials_and_missing_static_evidence(self) -> None:
        report = reconciliation_report(serial_values=[0, 0, 0])

        payload = evaluator.build_evaluation([report], None)

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertEqual(payload["reconciliation_summary"]["accepted_sample_count"], 3)
        self.assertEqual(payload["reconciliation_summary"]["serial_candidate_zero_count"], 3)
        self.assertEqual(payload["reconciliation_summary"]["serial_candidate_nonzero_count"], 0)
        self.assertIn(evaluator.BLOCKER_ZERO_OR_MISSING_SERIAL, payload["blockers"])
        self.assertIn(evaluator.BLOCKER_UOBJECT_FLAGS, payload["blockers"])
        self.assertIn(evaluator.BLOCKER_MISSING_COHERENT_WINDOW, payload["blockers"])
        self.assertNotIn("required", payload["artifact_identity"])
        self.assertNotIn("required_artifact_identity_present", payload["evidence_checks"])
        self.assertNotIn(evaluator.BLOCKER_MISSING_ARTIFACT_IDENTITY, payload["blockers"])

    def test_require_artifact_identity_adds_blocker_for_anonymous_reports(self) -> None:
        report = reconciliation_report(serial_values=[17, 23])
        payload = evaluator.build_evaluation(
            [report],
            static_evidence(coherent=True),
            require_artifact_identity=True,
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertTrue(payload["artifact_identity"]["required"])
        self.assertEqual(payload["artifact_identity"]["hash_count"], 0)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 2)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 0)
        self.assertIn(evaluator.BLOCKER_MISSING_ARTIFACT_IDENTITY, payload["blockers"])

    def test_require_artifact_identity_rejects_bare_hashes_without_complete_identity(self) -> None:
        report = reconciliation_report(serial_values=[17, 23], sha256="a" * 64)
        payload = evaluator.build_evaluation(
            [report],
            static_evidence(coherent=True, sha256="b" * 64),
            require_artifact_identity=True,
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertEqual(payload["artifact_identity"]["hash_count"], 2)
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 0)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 2)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 0)
        self.assertIn(evaluator.BLOCKER_MISSING_ARTIFACT_IDENTITY, payload["blockers"])

    def test_require_artifact_identity_adds_blocker_for_invalid_identity(self) -> None:
        invalid_values = (
            {"artifact_sha256": "A" * 64},
            {"capture_id": "../bad"},
            {"capture_id": "bad/path"},
            {"evidence_pack_id": ""},
        )
        for override in invalid_values:
            with self.subTest(override=override):
                report = reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64)
                artifact_identity = report["artifact_identity"]
                assert isinstance(artifact_identity, dict)
                artifact_identity.update(override)

                payload = evaluator.build_evaluation(
                    [report],
                    static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
                    require_artifact_identity=True,
                )

                self.assertFalse(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
                self.assertEqual(payload["artifact_identity"]["complete_input_count"], 1)
                self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 0)
                self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 1)
                self.assertIn(evaluator.BLOCKER_INVALID_ARTIFACT_IDENTITY, payload["blockers"])

    def test_require_artifact_identity_accepts_complete_identity_without_changing_lifetime_blocker(self) -> None:
        report = reconciliation_report(serial_values=[17, 23], artifact_identity_sha256="a" * 64)
        payload = evaluator.build_evaluation(
            [report],
            static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
            require_artifact_identity=True,
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertTrue(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertEqual(payload["artifact_identity"]["hash_count"], 2)
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 2)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 0)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 0)
        self.assertNotIn(evaluator.BLOCKER_MISSING_ARTIFACT_IDENTITY, payload["blockers"])
        self.assertIn(evaluator.BLOCKER_UOBJECT_FLAGS, payload["blockers"])

    def test_cli_output_is_redacted_and_keeps_only_counts_and_hashes(self) -> None:
        artifact_hash = "a" * 64
        binary_hash = "b" * 64
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reconciliation = root / "reconciliation.json"
            static = root / "static.json"
            output = root / "resource-handle-readiness.json"
            write_json(reconciliation, reconciliation_report(serial_values=[0], artifact_identity_sha256=artifact_hash))
            write_json(static, static_evidence(coherent=False, artifact_identity_sha256=binary_hash))

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                    "--reconciliation",
                    str(reconciliation),
                    "--static-global-evidence",
                    str(static),
                    "--require-artifact-identity",
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            text = output.read_text(encoding="utf-8")
            payload = json.loads(text)

        self.assertEqual(payload["artifact_identity"]["hashes"], [artifact_hash, binary_hash])
        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertTrue(payload["artifact_identity"]["required"])
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 2)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 0)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 0)
        for forbidden in (
            "0x",
            "ServerChat",
            "Function",
            "CoreUObject",
            "/servidor/ark",
            "25447",
            "42424242",
            "fname",
            "class_name",
            "outer_name",
            "fuobject_item",
        ):
            self.assertNotIn(forbidden, text)

    def test_cli_rejects_protected_reconciliation_path_before_open(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                "--reconciliation",
                "/servidor/ark/obelisk/dumps/gobjects-reconciliation.json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--reconciliation must not read from protected server root", result.stderr)

    def test_synthetic_stronger_evidence_still_keeps_post_callback_resource_handle_blocked(self) -> None:
        report = reconciliation_report(serial_values=[17, 23])
        payload = evaluator.build_evaluation([report], static_evidence(coherent=True))

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertTrue(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertNotIn(evaluator.BLOCKER_ZERO_OR_MISSING_SERIAL, payload["blockers"])
        self.assertNotIn(evaluator.BLOCKER_MISSING_COHERENT_WINDOW, payload["blockers"])
        self.assertIn(evaluator.BLOCKER_UOBJECT_FLAGS, payload["blockers"])
        self.assertTrue(set(evaluator.RESOURCE_HANDLE_LIFETIME_BLOCKERS).issubset(set(payload["blockers"])))


if __name__ == "__main__":
    unittest.main()
