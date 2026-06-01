#!/usr/bin/env python3
"""Tests for evaluate_resource_handle_revalidation.py."""

from __future__ import annotations

import json
import hashlib
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
    testcase.assertEqual(
        payload["lifetime_blocker_summary"]["required_runtime_artifact_schemas"],
        list(evaluator.RESOURCE_HANDLE_RUNTIME_EVIDENCE_REQUIREMENTS),
    )
    testcase.assertIs(payload["evidence_checks"]["runtime_rejection_samples_present"], False)
    testcase.assertIs(payload["evidence_checks"]["runtime_serial_semantics_present"], False)
    testcase.assertIs(payload["evidence_checks"]["runtime_resourcehandle_promotion_evidence_complete"], False)
    testcase.assertTrue(set(evaluator.RESOURCE_HANDLE_LIFETIME_BLOCKERS).issubset(set(payload["blockers"])))
    testcase.assertEqual(payload["promotion_gate"]["ready"], False)
    testcase.assertEqual(payload["promotion_gate"]["blockers"], payload["blockers"])


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


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


def uobject_flag_policy_report(
    *,
    include_contract: bool = True,
    promotion_ready: bool = False,
    artifact_identity_sha256: str | None = None,
    artifact_identity_override: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": evaluator.UOBJECT_FLAG_POLICY_REPORT_SCHEMA,
        "evidence_kind": "static_negative_equivalent_candidate",
        "status": "candidate_blocked",
        "binary": {
            "sha256": "c" * 64,
            "path_redacted": True,
        },
        "promotion_ready": promotion_ready,
        "post_callback_resource_handle_ready": False,
        "weak_helper_caller_mode": {
            "schema": "obelisk.weak-helper-caller-mode-redacted.v1",
            "artifact_sha256": "d" * 64,
            "promotion_gate_ready": False,
            "direct_call_coverage": {
                "weak_helper_flag_policy_candidate": {
                    "expected": 6,
                    "observed": 6,
                },
            },
            "flag_rules": [
                {"mask": "0x100", "result": "null_always"},
                {"mask": "0x4000", "result": "null_when_sil_zero"},
            ],
            "caller_rows_summary": {
                "helper": "weak_helper_flag_policy_candidate",
                "row_count": 6,
                "unique_caller_hash_count": 6,
                "source_count": 2,
                "claim_level": "internal_static_caller_mode_candidate",
                "lifecycle_names": "not_promoted",
                "path_redacted": True,
            },
        },
        "windows_summary": {
            "required": [
                "weak_helper_reject_0x100",
                "strict_0x4000_behavior",
                "gobjects_backed_0x4000_skip",
                "gc_static_0x100_support",
            ],
            "observed": [
                {"path_redacted": True, "artifact_sha256": "e" * 64},
                {"path_redacted": True, "artifact_sha256": "f" * 64},
                {"path_redacted": True, "artifact_sha256": "1" * 64},
                {"path_redacted": True, "artifact_sha256": "2" * 64},
            ],
            "all_required_present": True,
            "all_required_patterns_present": True,
        },
        "policy_candidates": [
            {
                "mask": "0x100",
                "candidate": "hard_invalid_static_negative_equivalent",
                "support": [
                    "weak_helper_flag_policy_candidate_null_always",
                    "gc_static_0x100_support",
                ],
                "ue_lifecycle_name": "not_promoted",
            },
            {
                "mask": "0x4000",
                "candidate": "strict_invalid_static_negative_equivalent",
                "support": [
                    "weak_helper_flag_policy_candidate_null_when_mode_zero",
                    "strict_0x4000_behavior",
                    "gobjects_backed_0x4000_skip",
                ],
                "ue_lifecycle_name": "not_promoted",
            },
        ],
        "remaining_blockers": list(evaluator.UOBJECT_FLAG_POLICY_REMAINING_BLOCKERS),
        "non_claims": list(evaluator.UOBJECT_FLAG_POLICY_NON_CLAIMS),
        "redaction": {
            "paths": "redacted",
            "addresses": "redacted",
            "raw_snippets": "omitted",
        },
    }
    if include_contract:
        payload["internal_revalidation_contract"] = json.loads(
            json.dumps(evaluator.INTERNAL_UOBJECT_REVALIDATION_CONTRACT)
        )
    if artifact_identity_sha256 is not None:
        payload["artifact_identity"] = {
            "artifact_kind": "uobject-flag-policy",
            "artifact_sha256": artifact_identity_sha256,
            "capture_id": "capture-policy",
            "evidence_pack_id": "pack-policy",
        }
    if artifact_identity_override is not None:
        payload["artifact_identity"] = artifact_identity_override
    return payload


def zero_serial_negative_samples_report(
    *,
    artifact_identity: bool = True,
    artifact_identity_sha256: str | None = None,
    schema: str | None = None,
    promotion_ready: bool = False,
    public_resource_handle_ready: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": schema or evaluator.ZERO_SERIAL_NEGATIVE_SAMPLES_SCHEMA,
        "status": "candidate_blocked",
        "evidence_kind": "internal_offline_zero_serial_negative_samples",
        "deterministic_negative_cohort": True,
        "sources": [
            {
                "source_label": "vanilla",
                "core_path_redacted": True,
                "core_sha256": "1" * 64,
                "core_sha256_verified": True,
                "metadata": {
                    "gobjects": "0x595b7e0",
                    "fname_root_slot": "0x5956f30",
                    "fname_table": "0x5a94660",
                    "chunks": "0x1111222233334444",
                    "object_count": 50835,
                    "anchor_index": 50834,
                    "max_scan_index": 50834,
                    "name_resolution": "enabled",
                },
                "scan_totals": {
                    "indices_scanned": 50835,
                    "nonnull_items_seen": 50835,
                    "candidate_uobjects_seen": 50835,
                },
                "zero_serial_negative_samples": [
                    {
                        "index": 0,
                        "address": "0x5555666677778888",
                        "class_name": "Package",
                        "name": "/Script/CoreUObject",
                        "flags": 0,
                        "fuobject_item": "0x1111222233334444",
                        "item_dword_0x8": 0,
                        "item_dword_0xC": 0,
                        "internal_index": 0,
                        "internal_index_matches": True,
                        "membership": "candidate-uobject",
                        "membership_pass": True,
                    }
                ],
                "positive_anchor": {
                    "index": 50834,
                    "address": "0x9999aaaabbbbcccc",
                    "class_name": "LinkerLoad",
                    "name": "LinkerLoad",
                    "flags": 0,
                    "fuobject_item": "0x1111222233335555",
                    "item_dword_0x8": 1001,
                    "item_dword_0xC": 116,
                    "internal_index": 50834,
                    "internal_index_matches": True,
                    "membership": "candidate-uobject",
                    "membership_pass": True,
                },
                "deterministic_negative_cohort": True,
                "blockers": [],
            }
        ],
        "serial_candidate_field": {
            "offset": "FUObjectItem+0x8",
            "width": "uint32",
            "accepted_positive_anchor": "index 50834 nonzero serial",
        },
        "non_claims": list(evaluator.ZERO_SERIAL_NEGATIVE_SAMPLE_NON_CLAIMS),
        "promotion_ready": promotion_ready,
        "public_resource_handle_ready": public_resource_handle_ready,
        "post_callback_resource_handle_ready": False,
        "promotion_gate": {
            "ready": False,
            "blockers": ["candidate_only_zero_serial_negative_samples"],
        },
    }
    if artifact_identity:
        identity_without_hash = {
            "artifact_kind": evaluator.ZERO_SERIAL_NEGATIVE_SAMPLES_SCHEMA,
            "capture_id": "zero-serial-capture",
            "evidence_pack_id": "zero-serial-pack",
        }
        expected_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "artifact_identity": identity_without_hash,
                    "report": evaluator.zero_serial_negative_samples_canonical_report(payload),
                }
            )
        ).hexdigest()
        payload["output_artifact_identity"] = {
            **identity_without_hash,
            "artifact_sha256": artifact_identity_sha256 or expected_hash,
        }
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
            {"artifact_kind": "unspecified-core"},
            {"capture_id": "../bad"},
            {"capture_id": "bad/path"},
            {"evidence_pack_id": ""},
            {"capture_id": "unspecified-capture"},
            {"evidence_pack_id": "unspecified-evidence-pack"},
            {"artifact_kind": "static-global-default-kind"},
            {"capture_id": "static-global-default-capture"},
            {"evidence_pack_id": "static-global-default-pack"},
            {"artifact_kind": "bad/kind"},
            {"artifact_kind": "bad\\kind"},
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

    def test_require_artifact_identity_rejects_static_default_identity_on_static_evidence(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64)],
            static_evidence(
                coherent=True,
                artifact_identity_override={
                    "artifact_kind": "objdump",
                    "artifact_sha256": "b" * 64,
                    "capture_id": "static-global-default-capture",
                    "evidence_pack_id": "pack-b",
                },
            ),
            require_artifact_identity=True,
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 1)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 0)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 1)
        self.assertIn(evaluator.BLOCKER_INVALID_ARTIFACT_IDENTITY, payload["blockers"])

    def test_require_artifact_identity_rejects_identity_with_extra_fields(self) -> None:
        report = reconciliation_report(
            serial_values=[17],
            artifact_identity_override={
                "artifact_kind": "core",
                "artifact_sha256": "a" * 64,
                "capture_id": "capture-a",
                "evidence_pack_id": "pack-a",
                "extra": "not-allowed",
            },
        )
        payload = evaluator.build_evaluation(
            [report],
            static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
            require_artifact_identity=True,
        )

        assert_fail_closed_resource_handle_contract(self, payload)
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

    def test_cli_can_emit_output_artifact_identity_without_promoting_resourcehandle(self) -> None:
        artifact_hash = "a" * 64
        binary_hash = "b" * 64
        policy_hash = "c" * 64
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reconciliation = root / "reconciliation.json"
            static = root / "static.json"
            policy = root / "uobject-flag-policy.json"
            output = root / "resource-handle-readiness.json"
            write_json(reconciliation, reconciliation_report(serial_values=[17], artifact_identity_sha256=artifact_hash))
            write_json(static, static_evidence(coherent=True, artifact_identity_sha256=binary_hash))
            write_json(policy, uobject_flag_policy_report(artifact_identity_sha256=policy_hash))

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                    "--reconciliation",
                    str(reconciliation),
                    "--static-global-evidence",
                    str(static),
                    "--uobject-flag-policy",
                    str(policy),
                    "--require-artifact-identity",
                    "--require-output-artifact-identity",
                    "--artifact-kind",
                    "obelisk.resource-handle-revalidation-evaluator.v1",
                    "--capture-id",
                    "resourcehandle-eval-test",
                    "--evidence-pack-id",
                    "resourcehandle-eval-pack",
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            text = output.read_text(encoding="utf-8")
            payload = json.loads(text)

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertEqual(
            payload["output_artifact_identity"]["artifact_kind"],
            "obelisk.resource-handle-revalidation-evaluator.v1",
        )
        self.assertEqual(payload["output_artifact_identity"]["capture_id"], "resourcehandle-eval-test")
        self.assertEqual(payload["output_artifact_identity"]["evidence_pack_id"], "resourcehandle-eval-pack")
        self.assertRegex(payload["output_artifact_identity"]["artifact_sha256"], r"^[0-9a-f]{64}$")
        report_without_identity = dict(payload)
        output_identity = dict(report_without_identity.pop("output_artifact_identity"))
        identity_without_hash = {
            key: output_identity[key]
            for key in ("artifact_kind", "capture_id", "evidence_pack_id")
        }
        expected_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "artifact_identity": identity_without_hash,
                    "report": report_without_identity,
                }
            )
        ).hexdigest()
        self.assertEqual(output_identity["artifact_sha256"], expected_hash)
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 3)
        self.assertFalse(payload["public_resource_handle_ready"])
        self.assertFalse(payload["post_callback_resource_handle_ready"])
        for forbidden in (
            "0x1111222233334444",
            "0x5555666677778888",
            "ServerChat",
            "Function",
            "CoreUObject",
            "/servidor/ark",
            "25447",
            "42424242",
            "fuobject_item",
            "class_name",
            "outer_name",
        ):
            self.assertNotIn(forbidden, text)

    def test_cli_rejects_partial_output_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reconciliation = root / "reconciliation.json"
            output = root / "resource-handle-readiness.json"
            write_json(reconciliation, reconciliation_report(serial_values=[17]))

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                    "--reconciliation",
                    str(reconciliation),
                    "--require-output-artifact-identity",
                    "--artifact-kind",
                    "obelisk.resource-handle-revalidation-evaluator.v1",
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--require-output-artifact-identity requires", result.stderr)

    def test_cli_rejects_placeholder_output_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reconciliation = root / "reconciliation.json"
            output = root / "resource-handle-readiness.json"
            write_json(reconciliation, reconciliation_report(serial_values=[17]))

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                    "--reconciliation",
                    str(reconciliation),
                    "--artifact-kind",
                    "obelisk.resource-handle-revalidation-evaluator.v1",
                    "--capture-id",
                    "unspecified-capture",
                    "--evidence-pack-id",
                    "pack",
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--capture-id must be a safe artifact id", result.stderr)

    def test_cli_rejects_wrong_output_artifact_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reconciliation = root / "reconciliation.json"
            output = root / "resource-handle-readiness.json"
            write_json(reconciliation, reconciliation_report(serial_values=[17]))

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                    "--reconciliation",
                    str(reconciliation),
                    "--artifact-kind",
                    "obelisk.other-artifact.v1",
                    "--capture-id",
                    "capture",
                    "--evidence-pack-id",
                    "pack",
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"--artifact-kind must be {evaluator.SCHEMA}", result.stderr)

    def test_uobject_flag_policy_emits_internal_candidate_without_promoting_resourcehandle(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17, 23])],
            static_evidence(coherent=True),
            uobject_flag_policy=uobject_flag_policy_report(),
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertTrue(payload["evidence_checks"]["internal_uobject_revalidation_candidate_present"])
        self.assertFalse(payload["uobject_flags_validity_semantics_proven"])
        self.assertIn(evaluator.BLOCKER_UOBJECT_FLAGS, payload["blockers"])
        self.assertNotIn(evaluator.BLOCKER_INVALID_UOBJECT_FLAG_POLICY_CANDIDATE, payload["blockers"])
        candidate = payload["internal_uobject_revalidation_candidate"]
        self.assertTrue(candidate["accepted"])
        self.assertEqual(candidate["contract_source"], "embedded")
        self.assertEqual(candidate["candidate"], evaluator.INTERNAL_UOBJECT_REVALIDATION_CONTRACT)
        self.assertEqual(candidate["policy_candidate_masks"], ["0x100", "0x4000"])
        self.assertEqual(candidate["evidence_summary"]["windows"]["observed_count"], 4)
        self.assertEqual(candidate["source_promotion_ready"], False)
        self.assertEqual(candidate["source_post_callback_resource_handle_ready"], False)

    def test_uobject_flag_policy_can_derive_internal_candidate_from_current_durable_artifact_shape(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17])],
            static_evidence(coherent=True),
            uobject_flag_policy=uobject_flag_policy_report(include_contract=False),
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        candidate = payload["internal_uobject_revalidation_candidate"]
        self.assertTrue(candidate["accepted"])
        self.assertEqual(candidate["contract_source"], "derived_from_policy_candidates")
        self.assertEqual(candidate["candidate"]["post_callback_lookup"], "rejected")
        self.assertEqual(candidate["candidate"]["public_api"], "not_promoted")

    def test_invalid_uobject_flag_policy_keeps_internal_candidate_fail_closed(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17])],
            static_evidence(coherent=True),
            uobject_flag_policy=uobject_flag_policy_report(promotion_ready=True),
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["internal_uobject_revalidation_candidate_present"])
        self.assertIn(evaluator.BLOCKER_INVALID_UOBJECT_FLAG_POLICY_CANDIDATE, payload["blockers"])
        candidate = payload["internal_uobject_revalidation_candidate"]
        self.assertFalse(candidate["accepted"])
        self.assertIn("uobject_flag_policy_promotion_ready_overclaim", candidate["issues"])

    def test_require_artifact_identity_blocks_policy_without_top_level_identity(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64)],
            static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
            require_artifact_identity=True,
            uobject_flag_policy=uobject_flag_policy_report(),
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertFalse(payload["evidence_checks"]["internal_uobject_revalidation_candidate_present"])
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 2)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 1)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 0)
        self.assertIn(evaluator.BLOCKER_MISSING_ARTIFACT_IDENTITY, payload["blockers"])
        candidate = payload["internal_uobject_revalidation_candidate"]
        self.assertFalse(candidate["accepted"])
        self.assertIn(evaluator.BLOCKER_MISSING_ARTIFACT_IDENTITY, candidate["issues"])

    def test_require_artifact_identity_blocks_policy_with_invalid_top_level_identity(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64)],
            static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
            require_artifact_identity=True,
            uobject_flag_policy=uobject_flag_policy_report(
                artifact_identity_override={
                    "artifact_kind": "uobject-flag-policy",
                    "artifact_sha256": "C" * 64,
                    "capture_id": "capture-policy",
                    "evidence_pack_id": "pack-policy",
                }
            ),
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertFalse(payload["evidence_checks"]["internal_uobject_revalidation_candidate_present"])
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 2)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 0)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 1)
        self.assertIn(evaluator.BLOCKER_INVALID_ARTIFACT_IDENTITY, payload["blockers"])
        candidate = payload["internal_uobject_revalidation_candidate"]
        self.assertFalse(candidate["accepted"])
        self.assertIn(evaluator.BLOCKER_INVALID_ARTIFACT_IDENTITY, candidate["issues"])

    def test_require_artifact_identity_blocks_policy_with_static_default_identity(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64)],
            static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
            require_artifact_identity=True,
            uobject_flag_policy=uobject_flag_policy_report(
                artifact_identity_override={
                    "artifact_kind": "uobject-flag-policy",
                    "artifact_sha256": "c" * 64,
                    "capture_id": "capture-policy",
                    "evidence_pack_id": "static-global-default-pack",
                }
            ),
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertFalse(payload["evidence_checks"]["internal_uobject_revalidation_candidate_present"])
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 2)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 0)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 1)
        self.assertIn(evaluator.BLOCKER_INVALID_ARTIFACT_IDENTITY, payload["blockers"])
        candidate = payload["internal_uobject_revalidation_candidate"]
        self.assertFalse(candidate["accepted"])
        self.assertIn(evaluator.BLOCKER_INVALID_ARTIFACT_IDENTITY, candidate["issues"])

    def test_require_artifact_identity_counts_complete_policy_identity_without_public_promotion(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64)],
            static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
            require_artifact_identity=True,
            uobject_flag_policy=uobject_flag_policy_report(artifact_identity_sha256="c" * 64),
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertTrue(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertTrue(payload["evidence_checks"]["internal_uobject_revalidation_candidate_present"])
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 3)
        self.assertEqual(payload["artifact_identity"]["missing_or_partial_input_count"], 0)
        self.assertEqual(payload["artifact_identity"]["invalid_input_count"], 0)
        self.assertNotIn(evaluator.BLOCKER_MISSING_ARTIFACT_IDENTITY, payload["blockers"])
        self.assertNotIn(evaluator.BLOCKER_INVALID_ARTIFACT_IDENTITY, payload["blockers"])
        self.assertFalse(payload["public_resource_handle_ready"])
        self.assertFalse(payload["post_callback_resource_handle_ready"])
        self.assertTrue(payload["internal_uobject_revalidation_candidate"]["accepted"])

    def test_cli_uobject_flag_policy_output_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reconciliation = root / "reconciliation.json"
            static = root / "static.json"
            policy = root / "uobject-flag-policy.json"
            output = root / "resource-handle-readiness.json"
            write_json(reconciliation, reconciliation_report(serial_values=[17]))
            write_json(static, static_evidence(coherent=True))
            write_json(policy, uobject_flag_policy_report(include_contract=False))

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                    "--reconciliation",
                    str(reconciliation),
                    "--static-global-evidence",
                    str(static),
                    "--uobject-flag-policy",
                    str(policy),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            text = output.read_text(encoding="utf-8")
            payload = json.loads(text)

        candidate = payload["internal_uobject_revalidation_candidate"]
        self.assertTrue(candidate["accepted"])
        self.assertEqual(candidate["contract_source"], "derived_from_policy_candidates")
        for forbidden in (
            "0x1111222233334444",
            "0x5555666677778888",
            "ServerChat",
            "Function",
            "CoreUObject",
            "/servidor/ark",
            "25447",
            "42424242",
            "fuobject_item",
            "class_name",
            "outer_name",
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

    def test_runtime_artifact_requirements_keep_offline_serial_policy_from_unblocking_resourcehandle(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64)],
            static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
            require_artifact_identity=True,
            uobject_flag_policy=uobject_flag_policy_report(artifact_identity_sha256="c" * 64),
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertTrue(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertTrue(payload["evidence_checks"]["internal_uobject_revalidation_candidate_present"])
        self.assertFalse(payload["evidence_checks"]["runtime_rejection_samples_present"])
        self.assertFalse(payload["evidence_checks"]["runtime_serial_semantics_present"])
        self.assertFalse(payload["evidence_checks"]["runtime_resourcehandle_promotion_evidence_complete"])
        self.assertIn("no_rejected_runtime_object_samples", payload["blockers"])
        self.assertIn("no_serial_reuse_or_wraparound_policy", payload["blockers"])
        self.assertEqual(
            payload["lifetime_blocker_summary"]["required_runtime_artifact_schemas"],
            [
                {
                    "schema": evaluator.RUNTIME_REJECTION_SAMPLES_SCHEMA,
                    "blocker": "no_rejected_runtime_object_samples",
                    "present": False,
                },
                {
                    "schema": evaluator.RUNTIME_SERIAL_SEMANTICS_SCHEMA,
                    "blocker": "no_serial_reuse_or_wraparound_policy",
                    "present": False,
                },
            ],
        )

    def test_zero_serial_negative_samples_are_reported_but_do_not_satisfy_runtime_blockers(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64)],
            static_evidence(coherent=True, artifact_identity_sha256="b" * 64),
            require_artifact_identity=True,
            uobject_flag_policy=uobject_flag_policy_report(artifact_identity_sha256="c" * 64),
            zero_serial_negative_samples=[zero_serial_negative_samples_report()],
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertTrue(payload["evidence_checks"]["offline_zero_serial_negative_samples_present"])
        self.assertTrue(payload["evidence_checks"]["offline_zero_serial_negative_samples_accepted"])
        self.assertFalse(payload["evidence_checks"]["zero_serial_negative_samples_satisfy_runtime_rejection_samples"])
        self.assertFalse(payload["evidence_checks"]["zero_serial_negative_samples_satisfy_runtime_serial_semantics"])
        self.assertFalse(payload["evidence_checks"]["runtime_rejection_samples_present"])
        self.assertFalse(payload["evidence_checks"]["runtime_serial_semantics_present"])
        self.assertIn("no_rejected_runtime_object_samples", payload["blockers"])
        self.assertIn("no_serial_reuse_or_wraparound_policy", payload["blockers"])
        self.assertNotIn(evaluator.BLOCKER_INVALID_ZERO_SERIAL_NEGATIVE_SAMPLES, payload["blockers"])
        self.assertEqual(payload["artifact_identity"]["complete_input_count"], 4)
        summary = payload["offline_zero_serial_negative_samples_summary"]
        self.assertEqual(summary["accepted_report_count"], 1)
        self.assertEqual(summary["zero_serial_sample_count"], 1)
        self.assertEqual(summary["positive_anchor_count"], 1)
        self.assertEqual(
            summary["does_not_satisfy_runtime_requirements"],
            list(evaluator.ZERO_SERIAL_RUNTIME_NON_SUBSTITUTIONS),
        )
        self.assertEqual(
            payload["lifetime_blocker_summary"]["offline_zero_serial_negative_samples_do_not_satisfy"],
            list(evaluator.ZERO_SERIAL_RUNTIME_NON_SUBSTITUTIONS),
        )

    def test_zero_serial_negative_samples_wrong_schema_is_invalid_and_not_runtime_evidence(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17])],
            static_evidence(coherent=True),
            zero_serial_negative_samples=[
                zero_serial_negative_samples_report(schema=evaluator.RUNTIME_REJECTION_SAMPLES_SCHEMA)
            ],
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["offline_zero_serial_negative_samples_accepted"])
        self.assertFalse(payload["evidence_checks"]["runtime_rejection_samples_present"])
        self.assertFalse(payload["evidence_checks"]["runtime_serial_semantics_present"])
        self.assertIn(evaluator.BLOCKER_INVALID_ZERO_SERIAL_NEGATIVE_SAMPLES, payload["blockers"])
        report_summary = payload["offline_zero_serial_negative_samples_summary"]["reports"][0]
        self.assertFalse(report_summary["accepted"])
        self.assertIn("zero_serial_negative_samples_schema_mismatch", report_summary["issues"])
        self.assertIn("no_rejected_runtime_object_samples", payload["blockers"])

    def test_zero_serial_negative_samples_rejects_mixed_runtime_fields(self) -> None:
        report = zero_serial_negative_samples_report()
        report["rows"] = [
            {
                "row_id": "runtime-like-row",
                "decision": "reject",
                "reject_reason": "zero_serial",
            }
        ]

        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17])],
            static_evidence(coherent=True),
            zero_serial_negative_samples=[report],
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["offline_zero_serial_negative_samples_accepted"])
        self.assertFalse(payload["evidence_checks"]["runtime_rejection_samples_present"])
        self.assertIn(evaluator.BLOCKER_INVALID_ZERO_SERIAL_NEGATIVE_SAMPLES, payload["blockers"])
        report_summary = payload["offline_zero_serial_negative_samples_summary"]["reports"][0]
        self.assertIn("zero_serial_negative_samples_unexpected_top_level_field", report_summary["issues"])
        self.assertIn("no_rejected_runtime_object_samples", payload["blockers"])

    def test_zero_serial_negative_samples_overclaim_is_invalid_and_fail_closed(self) -> None:
        payload = evaluator.build_evaluation(
            [reconciliation_report(serial_values=[17])],
            static_evidence(coherent=True),
            zero_serial_negative_samples=[
                zero_serial_negative_samples_report(
                    promotion_ready=True,
                    public_resource_handle_ready=True,
                )
            ],
        )

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertFalse(payload["evidence_checks"]["offline_zero_serial_negative_samples_accepted"])
        self.assertIn(evaluator.BLOCKER_INVALID_ZERO_SERIAL_NEGATIVE_SAMPLES, payload["blockers"])
        report_summary = payload["offline_zero_serial_negative_samples_summary"]["reports"][0]
        self.assertIn("zero_serial_negative_samples_promotion_ready_overclaim", report_summary["issues"])
        self.assertIn("zero_serial_negative_samples_public_resourcehandle_overclaim", report_summary["issues"])

    def test_cli_zero_serial_negative_samples_output_is_redacted_and_runtime_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reconciliation = root / "reconciliation.json"
            static = root / "static.json"
            zero_serial = root / "zero-serial.json"
            output = root / "resource-handle-readiness.json"
            write_json(reconciliation, reconciliation_report(serial_values=[17], artifact_identity_sha256="a" * 64))
            write_json(static, static_evidence(coherent=True, artifact_identity_sha256="b" * 64))
            write_json(zero_serial, zero_serial_negative_samples_report())

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                    "--reconciliation",
                    str(reconciliation),
                    "--static-global-evidence",
                    str(static),
                    "--zero-serial-negative-samples",
                    str(zero_serial),
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

        assert_fail_closed_resource_handle_contract(self, payload)
        self.assertTrue(payload["evidence_checks"]["offline_zero_serial_negative_samples_accepted"])
        self.assertFalse(payload["evidence_checks"]["runtime_rejection_samples_present"])
        self.assertFalse(payload["evidence_checks"]["runtime_serial_semantics_present"])
        for forbidden in (
            "0x5555666677778888",
            "0x9999aaaabbbbcccc",
            "Package",
            "LinkerLoad",
            "CoreUObject",
            "/Script",
            "50834",
            "1001",
            "fuobject_item",
            "fname_root_slot",
            "class_name",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
