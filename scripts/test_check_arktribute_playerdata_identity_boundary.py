from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("check_arktribute_playerdata_identity_boundary.py")
SPEC = importlib.util.spec_from_file_location("arktribute_boundary_check", MODULE_PATH)
CHECKER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CHECKER)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _readiness() -> dict:
    return {
        "schema": "obelisk.reflection-snapshot-readiness.v1",
        "second_source_status": "compared",
        "target_filters": [
            "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ArkTributePlayerData"
        ],
        "totals": {"targets": 2, "second_source_accepted": 2},
        "not_promoted_surfaces": sorted(CHECKER.EXPECTED_NOT_PROMOTED_SURFACES),
        "promotion_gate": {
            "layout_ready": True,
            "promotion_ready": False,
            "ready_scope": "layout_only",
        },
    }


def _promote_gate() -> dict:
    return {
        "schema": "obelisk.offline-artifact-gate-result.v1",
        "mode": "promote",
        "status": "blocked",
        "blockers": [
            {"reason": "promote_mode_scriptstruct_inventory_candidate_only"},
            {"reason": "promote_mode_manifest_has_non_claims"},
        ],
    }


def _manifest() -> dict:
    return {
        "schema": "obelisk.scriptstruct-inventory-pack.v1",
        "status": "candidate-only",
        "promotion_status": "not_promoted_candidate_only",
        "inputs": {"target_sets": ["transfer-scriptstruct"]},
        "non_claims": [
            "Does not promote a public ScriptStruct SDK.",
            "Does not expose UObject pointers, raw UE params, FName/GObjects indices, object identity, lookup, or ResourceHandle.",
            "Does not authorize mutation, return override, ProcessEvent blocking, or UE call replay.",
        ],
    }


def _property(name: str, expected: dict) -> dict:
    prop = {
        "name": name,
        "class_name": expected["class_name"],
        "offset_internal": expected["offset_internal"],
        "array_dim": expected["array_dim"],
        "status": "candidate",
        "reject_reasons": [],
    }
    if expected["class_name"] == "ArrayProperty":
        prop["array_inner_candidate"] = {
            "inner_property": {"class_name": expected["inner_class_name"]}
        }
    if expected["class_name"] == "BoolProperty":
        for key in (
            "bool_field_size",
            "bool_byte_offset",
            "byte_mask",
            "field_mask",
            "native_bool",
        ):
            prop[key] = expected[key]
    return prop


def _snapshot() -> dict:
    return {
        "schema": "obelisk.scriptstruct-chain.snapshot.v1",
        "evidence": {"status": "candidate-only"},
        "interpretation": {"status": "candidate-only"},
        "targets": [
            {
                "status": "candidate",
                "target": {
                    "outer_name": "PrimalLocalProfile",
                    "name": "ArkTributePlayerData",
                },
                "property_chain": {
                    "status": "candidate",
                    "properties_size": 288,
                    "observed_count": 11,
                    "properties": [
                        _property(name, expected)
                        for name, expected in CHECKER.EXPECTED_SENSITIVE_FIELDS.items()
                    ]
                    + [
                        {
                            "name": "Version",
                            "class_name": "FloatProperty",
                            "offset_internal": 284,
                            "array_dim": 1,
                            "status": "candidate",
                            "reject_reasons": [],
                        }
                    ],
                },
            }
        ],
    }


def _artifact_tree(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    _write_json(root / CHECKER.READINESS_REL, _readiness())
    _write_json(root / CHECKER.PROMOTE_GATE_REL, _promote_gate())
    _write_json(root / CHECKER.MANIFEST_REL, _manifest())
    _write_json(root / CHECKER.SNAPSHOT_REL, _snapshot())
    return root


def _result_codes(result: dict) -> set[str]:
    return {blocker["code"] for blocker in result["blockers"]}


class BoundaryCheckerTests(unittest.TestCase):
    def test_boundary_artifacts_pass_when_layout_only_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _artifact_tree(Path(temp_dir))

            result = CHECKER.validate_artifacts(root, enforce_allowed_root=False)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["blockers"], [])

    def test_transfer_readiness_must_remain_layout_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _artifact_tree(Path(temp_dir))
            readiness = _readiness()
            readiness["promotion_gate"]["ready_scope"] = "public_sdk"
            _write_json(root / CHECKER.READINESS_REL, readiness)

            result = CHECKER.validate_artifacts(root, enforce_allowed_root=False)

        self.assertIn("readiness_not_layout_only", _result_codes(result))

    def test_promote_gate_must_stay_blocked_with_expected_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _artifact_tree(Path(temp_dir))
            promote_gate = _promote_gate()
            promote_gate["status"] = "accepted"
            promote_gate["blockers"] = []
            _write_json(root / CHECKER.PROMOTE_GATE_REL, promote_gate)

            result = CHECKER.validate_artifacts(root, enforce_allowed_root=False)

        codes = _result_codes(result)
        self.assertIn("promote_gate_not_blocked", codes)
        self.assertIn("promote_gate_missing_expected_blockers", codes)

    def test_snapshot_schema_and_status_must_be_candidate_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _artifact_tree(Path(temp_dir))
            snapshot = _snapshot()
            snapshot["schema"] = "unexpected"
            snapshot["evidence"]["status"] = "promoted"
            _write_json(root / CHECKER.SNAPSHOT_REL, snapshot)

            result = CHECKER.validate_artifacts(root, enforce_allowed_root=False)

        codes = _result_codes(result)
        self.assertIn("invalid_snapshot_schema", codes)
        self.assertIn("snapshot_not_candidate_only", codes)

    def test_sensitive_fields_must_remain_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _artifact_tree(Path(temp_dir))
            snapshot = _snapshot()
            properties = snapshot["targets"][0]["property_chain"]["properties"]
            snapshot["targets"][0]["property_chain"]["properties"] = [
                prop for prop in properties if prop["name"] != "PlayerName"
            ]
            _write_json(root / CHECKER.SNAPSHOT_REL, snapshot)

            result = CHECKER.validate_artifacts(root, enforce_allowed_root=False)

        self.assertIn(
            {"code": "missing_sensitive_field", "detail": "PlayerName"},
            result["blockers"],
        )

    def test_manifest_cannot_claim_public_or_runtime_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _artifact_tree(Path(temp_dir))
            manifest = _manifest()
            manifest["promotion_status"] = "promoted_public_sdk"
            manifest["non_claims"] = []
            _write_json(root / CHECKER.MANIFEST_REL, manifest)

            result = CHECKER.validate_artifacts(root, enforce_allowed_root=False)

        codes = _result_codes(result)
        self.assertIn("manifest_promoted_or_public", codes)
        self.assertIn("manifest_missing_non_claim", codes)

    def test_missing_artifacts_report_exact_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = CHECKER.validate_artifacts(
                Path(temp_dir) / "empty", enforce_allowed_root=False
            )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(
            result["blockers"],
            [
                {"code": "missing_artifact", "detail": str(CHECKER.READINESS_REL)},
                {"code": "missing_artifact", "detail": str(CHECKER.PROMOTE_GATE_REL)},
                {"code": "missing_artifact", "detail": str(CHECKER.MANIFEST_REL)},
                {"code": "missing_artifact", "detail": str(CHECKER.SNAPSHOT_REL)},
            ],
        )

    def test_bool_tail_metadata_is_sensitive_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _artifact_tree(Path(temp_dir))
            snapshot = copy.deepcopy(_snapshot())
            for prop in snapshot["targets"][0]["property_chain"]["properties"]:
                if prop["name"] == "bWithItems":
                    prop["field_mask"] = "0x1"
            _write_json(root / CHECKER.SNAPSHOT_REL, snapshot)

            result = CHECKER.validate_artifacts(root, enforce_allowed_root=False)

        self.assertIn("bool_tail_metadata_mismatch", _result_codes(result))


if __name__ == "__main__":
    unittest.main()
