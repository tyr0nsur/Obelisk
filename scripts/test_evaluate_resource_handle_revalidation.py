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


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reconciliation_report(
    *,
    serial_values: list[object],
    sha256: str | None = None,
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
    return payload


def static_evidence(*, coherent: bool, sha256: str | None = None) -> dict[str, object]:
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
    return payload


class ResourceHandleRevalidationEvaluatorTests(unittest.TestCase):
    def test_fail_closed_with_current_style_zero_serials_and_missing_static_evidence(self) -> None:
        report = reconciliation_report(serial_values=[0, 0, 0])

        payload = evaluator.build_evaluation([report], None)

        self.assertFalse(payload["post_callback_resource_handle_ready"])
        self.assertEqual(payload["reconciliation_summary"]["accepted_sample_count"], 3)
        self.assertEqual(payload["reconciliation_summary"]["serial_candidate_zero_count"], 3)
        self.assertEqual(payload["reconciliation_summary"]["serial_candidate_nonzero_count"], 0)
        self.assertIn(evaluator.BLOCKER_ZERO_OR_MISSING_SERIAL, payload["blockers"])
        self.assertIn(evaluator.BLOCKER_UOBJECT_FLAGS, payload["blockers"])
        self.assertIn(evaluator.BLOCKER_MISSING_COHERENT_WINDOW, payload["blockers"])

    def test_cli_output_is_redacted_and_keeps_only_counts_and_hashes(self) -> None:
        artifact_hash = "a" * 64
        binary_hash = "b" * 64
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reconciliation = root / "reconciliation.json"
            static = root / "static.json"
            output = root / "resource-handle-readiness.json"
            write_json(reconciliation, reconciliation_report(serial_values=[0], sha256=artifact_hash))
            write_json(static, static_evidence(coherent=False, sha256=binary_hash))

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "evaluate_resource_handle_revalidation.py"),
                    "--reconciliation",
                    str(reconciliation),
                    "--static-global-evidence",
                    str(static),
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

        self.assertFalse(payload["post_callback_resource_handle_ready"])
        self.assertTrue(payload["evidence_checks"]["evidence_without_lifetime_flags_ready"])
        self.assertNotIn(evaluator.BLOCKER_ZERO_OR_MISSING_SERIAL, payload["blockers"])
        self.assertNotIn(evaluator.BLOCKER_MISSING_COHERENT_WINDOW, payload["blockers"])
        self.assertEqual(payload["blockers"], [evaluator.BLOCKER_UOBJECT_FLAGS])


if __name__ == "__main__":
    unittest.main()
