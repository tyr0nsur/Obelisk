#!/usr/bin/env python3
"""Tests for check_commands_replies_public_readiness.py."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_commands_replies_public_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
RESPONSE_TARGETS = [
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
]

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_commands_replies_public_readiness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
READINESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = READINESS
SPEC.loader.exec_module(READINESS)


def response_target_snapshot_payload(target: str) -> dict:
    return {
        "schema": "obelisk.ufunction-chain.snapshot.v1",
        "evidence": {
            "artifact_sha256": "b" * 64,
            "capture_id": "unit-test-commands-replies-response",
            "evidence_pack_id": "unit-test-commands-replies-response-pack",
            "source": "unit-test",
            "status": "candidate-only",
        },
        "targets": [
            {
                "target": {"name": target.rsplit(".", 1)[1]},
                "property_chain": {
                    "properties": [
                        {"name": "UnitTestProperty", "status": "candidate-only"},
                    ]
                },
            }
        ],
    }


class CheckCommandsRepliesPublicReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def load_surfaces(self) -> dict:
        return json.loads(SURFACES.read_text(encoding="utf-8"))

    def write_inputs(
        self,
        root: Path,
        *,
        decisions: dict | None = None,
        surfaces: dict | None = None,
        header: str | None = None,
        temp_header: bool = False,
    ) -> tuple[Path, Path, Path]:
        decisions_path = root / "commands_replies_public_contract_decisions.json"
        surfaces_path = root / "public_sdk_surfaces.json"
        decisions_path.write_text(json.dumps(decisions if decisions is not None else self.load_decisions()), encoding="utf-8")
        surfaces_path.write_text(json.dumps(surfaces if surfaces is not None else self.load_surfaces()), encoding="utf-8")
        if temp_header or header is not None:
            header_path = root / "ObeliskApi.h"
            header_path.write_text(header if header is not None else HEADER.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            header_path = HEADER
        return decisions_path, surfaces_path, header_path

    def make_response_readiness(self, root: Path | None = None) -> dict:
        def target_path(target: str) -> str:
            basename = f"{target.rsplit(':', 1)[1]}.snapshot.json"
            if root is None:
                return f"/offline/{basename}"
            return str(root / "base-snapshots" / basename)

        source_root = str(root) if root is not None else "/offline"
        candidate_root = str(root / "candidate-snapshots") if root is not None else "/offline-candidate"
        return {
            "schema": "obelisk.reflection-snapshot-readiness.v1",
            "evidence_scope": "second_source_layout_evidence_only",
            "gate_mode": "planning_layout_intake",
            "source_root": source_root,
            "producer": {
                "script": "scripts/compare_reflection_snapshots.py",
                "argv": [
                    "scripts/compare_reflection_snapshots.py",
                    "--base-root",
                    source_root,
                    "--candidate-root",
                    candidate_root,
                    "--target-set",
                    "command-chat-response-route-planning",
                    "--readiness-report",
                    "--json",
                ],
                "output_name": "command-chat-response-route-planning-readiness.json",
            },
            "second_source_status": "compared",
            "strict_identity_indices": False,
            "target_sets": ["command-chat-response-route-planning"],
            "target_filters": RESPONSE_TARGETS,
            "totals": {
                "targets": 3,
                "comparable": 3,
                "blocked": 0,
                "second_source_accepted": 3,
                "second_source_inconclusive": 0,
                "second_source_missing": 0,
                "second_source_rejected": 0,
            },
            "modules": [
                {
                    "module": "base-snapshots",
                    "targets": 3,
                    "comparable": 3,
                    "blocked": 0,
                    "second_source": {
                        "accepted": 3,
                        "inconclusive": 0,
                        "missing": 0,
                        "rejected": 0,
                    },
                    "target_details": [
                        {
                            "target": target,
                            "path": target_path(target),
                            "comparable": True,
                            "second_source_status": "accepted",
                            "block_reasons": [],
                        }
                        for target in RESPONSE_TARGETS
                    ],
                }
            ],
            "planning_layout_gate": {
                "ready_scope": "planning_only",
                "layout_ready": True,
                "ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
            },
            "promotion_gate": {
                "ready_scope": "planning_only",
                "layout_ready": True,
                "ready": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [{"reason": "planning_layout_intake_not_promotion_gate"}],
            },
            "target_set_guidance": [
                {
                    "target_set": "command-chat-response-route-planning",
                    "classification": "command_chat_response_route_guidance_only_candidate",
                    "why_blocked": [
                        "planning_guidance_only",
                        "not_release_readiness_target",
                        "public_response_path_blocked",
                        "player_identity_principal_blocked",
                        "permissions_admin_blocked",
                        "command_router_blocked",
                        "runtime_observation_requires_separate_approval",
                    ],
                    "snapshot_prep_checks": [
                        "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
                        "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
                        "sender identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                        "directed recipient identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                        "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
                    ],
                    "non_claim": "does not promote command/chat response path, public reply/send-chat ABI, command router, permissions, player identity, raw FString access, mutation, return override, runtime hooks, or release readiness",
                }
            ],
        }

    def write_response_report(self, root: Path) -> Path:
        snapshot_root = root / "base-snapshots"
        candidate_root = root / "candidate-snapshots"
        snapshot_root.mkdir(parents=True, exist_ok=True)
        candidate_root.mkdir(parents=True, exist_ok=True)
        for target in RESPONSE_TARGETS:
            (snapshot_root / f"{target.rsplit(':', 1)[1]}.snapshot.json").write_text(
                json.dumps(response_target_snapshot_payload(target.rsplit(":", 1)[1])),
                encoding="utf-8",
            )
        readiness_path = root / "command-chat-response-route-planning-readiness.json"
        readiness_path.write_text(json.dumps(self.make_response_readiness(root)), encoding="utf-8")
        response_report = READINESS.response_path_readiness.build_report(
            root,
            readiness_path,
            READINESS.response_path_readiness.DEFAULT_DECISIONS,
            READINESS.response_path_readiness.DEFAULT_PUBLIC_HEADER,
            READINESS.response_path_readiness.DEFAULT_SURFACES,
        )
        report_path = root / "command-chat-response-public-readiness.json"
        report_path.write_text(json.dumps(response_report), encoding="utf-8")
        return report_path

    def write_summary_response_report(self, root: Path) -> Path:
        response_report = {
            "schema": "obelisk.command-chat-response-public-readiness-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "planning_only": True,
            "surface": "obelisk.command_chat_response_path.v1",
            "target_set": "command-chat-response-route-planning",
            "target_filters": RESPONSE_TARGETS,
            "readiness_status": "compared",
            "decisions_status": "blocked",
            "surfaces_status": "planning",
            "public_readiness_ready": False,
            "public_header_allowed": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
            "blockers": [],
        }
        report_path = root / "command-chat-response-public-readiness.json"
        report_path.write_text(json.dumps(response_report), encoding="utf-8")
        return report_path

    def response_path_args(self, report_path: Path, root: Path) -> list[str]:
        return [
            "--response-path-report",
            str(report_path),
            "--response-path-report-root",
            str(report_path.parent),
            "--response-path-root",
            str(root),
            "--response-path-readiness",
            str(root / "command-chat-response-route-planning-readiness.json"),
        ]

    def test_accepts_current_manifests_as_planning_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            result = self.run_checker(
                *self.response_path_args(report_path, root),
                "--json",
            )
        report = json.loads(result.stdout)

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
            report["dependency_chain"],
        )

    def test_rejects_route_blocker_alias_even_when_called_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            report = READINESS.build_report(
                decisions_path=DECISIONS,
                surfaces_path=SURFACES,
                public_header_path=HEADER,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("current_route_blocker_mismatch", report["blockers"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_release_guardrail_public_sdk_or_v1_readiness_overclaim(self) -> None:
        surfaces = self.load_surfaces()
        surfaces["release_guardrails"].append("v1 SDK completion is ready and public runtime readiness is supported.")
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_summary_only_response_path_report_without_source_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = self.write_summary_response_report(Path(temp_dir))
            result = self.run_checker("--response-path-report", str(report_path), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_source_artifacts_missing", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_response_path_report_with_unverifiable_source_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            response_report = json.loads(report_path.read_text(encoding="utf-8"))
            response_report["readiness_path"] = ""
            response_report["decisions_path"] = None
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_unverifiable", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_response_path_report_with_nonexistent_source_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            response_report = json.loads(report_path.read_text(encoding="utf-8"))
            response_report["readiness_path"] = str(root / "missing-readiness.json")
            response_report["decisions_path"] = str(root / "missing-decisions.json")
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_source_artifact_missing_or_unreadable", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_response_path_report_whose_summary_disagrees_with_rebuilt_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            response_report = json.loads(report_path.read_text(encoding="utf-8"))
            response_report["surfaces_status"] = "post-v1"
            response_report["target_filters"] = list(reversed(response_report["target_filters"]))
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_source_artifact_identity_mismatch", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_response_path_report_with_extra_handwritten_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            response_report = json.loads(report_path.read_text(encoding="utf-8"))
            response_report["manual_review_note"] = "source artifacts were checked"
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker(*self.response_path_args(report_path, root), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_source_artifact_identity_mismatch", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "response_path_report_source_artifact_identity_mismatch"
            and item["label"] == "$.response_path_report.manual_review_note"
        )
        self.assertEqual("<absent>", detail["expected"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_response_path_report_with_stale_source_path_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            response_report = json.loads(report_path.read_text(encoding="utf-8"))
            response_report["readiness_path"] = str(
                root / "base-snapshots" / ".." / "command-chat-response-route-planning-readiness.json"
            )
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker(*self.response_path_args(report_path, root), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_readiness_path_metadata_mismatch", report["blockers"])
        self.assertIn("response_path_report_source_artifact_identity_mismatch", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_nested_response_path_report_surface_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            response_report = json.loads(report_path.read_text(encoding="utf-8"))
            response_report["nested"] = {"surface": "public SDK is ready"}
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker(*self.response_path_args(report_path, root), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("positive_public_surface_claim", report["blockers"])
        detail = next(
            item for item in report["blocker_details"] if item["reason"] == "positive_public_surface_claim"
        )
        self.assertEqual("$.response_path_report.nested.surface", detail["label"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_missing_response_path_report(self) -> None:
        result = self.run_checker("--json", check=False)
        report = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_required", report["blockers"])
        self.assertIsNone(report["response_path_report_path"])

    def test_rejects_decision_public_symbols_and_allowed_flags(self) -> None:
        decisions = self.load_decisions()
        decisions["public_header_allowed"] = True
        decisions["public_command_router_allowed"] = True
        decisions["public_reply_or_send_chat_abi_allowed"] = True
        decisions["public_header_symbols_now"] = ["RegisterCommandWithOwnerToken"]
        decisions["public_contract"] = ["RegisterCommandWithOwnerToken"]
        decisions["required_before_public_header"][0]["status"] = "resolved"
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_command_router_allowed_not_false", report["blockers"])
        self.assertIn("public_reply_or_send_chat_abi_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_contract_not_empty", report["blockers"])
        self.assertIn("required_before_public_header_item_not_unresolved", report["blockers"])

    def test_rejects_surface_public_contract_and_dependency_reorder(self) -> None:
        surfaces = self.load_surfaces()
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        commands = by_id["obelisk.commands_replies.v1"]
        commands["status"] = "promoted"
        commands["public_contract"] = ["ObeliskCommandPayload"]
        commands["depends_on"] = [
            "obelisk.command_chat_response_path.v1",
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
        ]
        surfaces["promoted_surfaces"].append("obelisk.commands_replies.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("commands_replies_listed_as_promoted", report["blockers"])
        self.assertIn("commands_replies_status_mismatch", report["blockers"])
        self.assertIn("commands_replies_public_contract_not_empty", report["blockers"])
        self.assertIn("dependency_chain_depends_on_mismatch", report["blockers"])

    def test_rejects_response_path_planning_evidence_promoted_in_surfaces(self) -> None:
        surfaces = self.load_surfaces()
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        by_id["obelisk.command_chat_response_path.v1"]["status"] = "promoted"
        surfaces["promoted_surfaces"].append("obelisk.command_chat_response_path.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_planning_evidence_treated_as_promoted", report["blockers"])
        self.assertIn("command_chat_response_evidence_not_approved", report["blockers"])

    def test_rejects_manifest_only_upstream_dependency_promotion(self) -> None:
        cases = (
            ("obelisk.player_identity.v1", "player_identity_evidence_not_approved"),
            ("obelisk.permissions_admin.v1", "permissions_admin_evidence_not_approved"),
            ("obelisk.command_chat_response_path.v1", "command_chat_response_evidence_not_approved"),
        )
        for surface_id, blocker in cases:
            with self.subTest(surface_id=surface_id):
                surfaces = self.load_surfaces()
                by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
                by_id[surface_id]["status"] = "promoted"
                with tempfile.TemporaryDirectory() as temp_dir:
                    decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
                    result = self.run_checker(
                        "--decisions",
                        str(decisions_path),
                        "--surfaces",
                        str(surfaces_path),
                        "--public-header",
                        str(header_path),
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                self.assertIn(blocker, report["blockers"])

    def test_rejects_promoted_surfaces_manifest_only_upstream_dependencies(self) -> None:
        surfaces = self.load_surfaces()
        surfaces["promoted_surfaces"].extend(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("player_identity_manifest_promotion_without_evidence", report["blockers"])
        self.assertIn("permissions_admin_manifest_promotion_without_evidence", report["blockers"])
        self.assertIn("command_chat_response_manifest_promotion_without_evidence", report["blockers"])

    def test_rejects_promoted_experimental_upstream_dependency_statuses(self) -> None:
        surfaces = self.load_surfaces()
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        by_id["obelisk.player_identity.v1"]["status"] = "promoted-experimental-only"
        by_id["obelisk.permissions_admin.v1"]["status"] = "promoted-experimental-only"
        by_id["obelisk.command_chat_response_path.v1"]["status"] = "promoted-experimental-only"
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
        self.assertIn("command_chat_response_evidence_not_approved", report["blockers"])

    def test_rejects_dependency_sequence_and_required_chain_drift(self) -> None:
        surfaces = self.load_surfaces()
        surfaces["v1_dependency_sequence"] = [
            "obelisk.player_identity.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.commands_replies.v1",
        ]
        surfaces["v1_required_dependency_chain"] = [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("v1_dependency_sequence_mismatch", report["blockers"])
        self.assertIn("dependency_chain_surface_missing_from_required_chain", report["blockers"])

    def test_rejects_public_header_command_reply_and_parser_symbols(self) -> None:
        header = (
            HEADER.read_text(encoding="utf-8")
            + "\n#define OBELISK_API_CAPABILITY_COMMAND_ROUTER (1ull << 50)\n"
            + "typedef struct ObeliskCommandParser { uint32_t struct_size; } ObeliskCommandParser;\n"
            + "typedef void (*ReplyToCommandWithOwnerToken)(uint64_t ownerToken);\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), header=header)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_path_mismatch", report["blockers"])
        self.assertIn("public_header_forbidden_symbols_present", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_forbidden_symbols_present")
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_ROUTER", detail["symbols"])
        self.assertIn("ObeliskCommandParser", detail["symbols"])
        self.assertIn("ReplyToCommandWithOwnerToken", detail["symbols"])

    def test_rejects_public_header_not_canonical_repo_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), temp_header=True)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                "--response-path-report",
                str(self.write_response_report(Path(temp_dir) / "response")),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_path_mismatch", report["blockers"])
        self.assertIn("decisions_public_header_not_scanned_header", report["blockers"])

    def test_rejects_response_path_report_with_fake_public_header_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root / "response")
            response_report = json.loads(report_path.read_text(encoding="utf-8"))
            fake_header = root / "fake-ObeliskApi.h"
            fake_header.write_text(HEADER.read_text(encoding="utf-8"), encoding="utf-8")
            response_report["public_header_path"] = str(fake_header)
            report_path.write_text(json.dumps(response_report), encoding="utf-8")

            result = self.run_checker(
                "--response-path-report",
                str(report_path),
                "--response-path-root",
                str(root / "response"),
                "--response-path-readiness",
                str(root / "response" / "command-chat-response-route-planning-readiness.json"),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_public_header_path_mismatch", report["blockers"])

    def test_rejects_positive_command_router_response_and_arkapi_parser_claims(self) -> None:
        decisions = self.load_decisions()
        decisions["claim"] = "command router is public and ready"
        decisions["arkapi_parser_copy_allowed"] = True
        decisions["public_reply_api"] = True
        decisions["public_send_chat_api"] = True
        decisions["reply_api_allowed"] = True
        decisions["send_chat_api_allowed"] = True
        decisions["runtime_delivery_allowed"] = True
        decisions["public_abi_allowed"] = True
        decisions["runtime_readiness_allowed"] = True
        decisions["v1_completion_evidence"] = True
        decisions["required_before_public_header"][0]["required_behavior"] = ["reply API is public and ready"]
        decisions["notes"] = [
            "ArkApi command parser copied and supported",
            "send-chat is available",
            "reply is supported",
            "router is ready",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])

    def test_mixed_negation_does_not_hide_positive_reply_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims({"note": "command router remains blocked but reply API ready"}, blockers)

        self.assertEqual(["positive_public_surface_claim"], [item["reason"] for item in blockers])

    def test_rejects_public_sdk_runtime_and_v1_completion_free_text_claims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "public_sdk_note": "public SDK readiness is ready",
                "runtime_note": "runtime readiness is available",
                "v1_note": "v1 completion is supported",
            },
            blockers,
        )

        self.assertEqual(
            [
                "positive_public_surface_claim",
                "positive_public_surface_claim",
                "positive_public_surface_claim",
            ],
            [item["reason"] for item in blockers],
        )

    def test_rejects_broad_release_sdk_wording_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "release_notes": [
                    "complete SDK is ready",
                    "full SDK is available",
                    "production SDK is supported",
                    "stable SDK is enabled",
                    "v1.0 stable is public",
                    "release readiness is supported",
                ],
                "aliases": {
                    "completeSdkReady": True,
                    "full-sdk-ready": True,
                    "production sdk ready": True,
                    "stableSdkReady": True,
                    "releaseReadinessReady": True,
                    "v1.0-stable-ready": True,
                },
            },
            blockers,
        )

        reasons = [item["reason"] for item in blockers]
        self.assertEqual(6, reasons.count("positive_public_surface_claim"))
        self.assertEqual(6, reasons.count("public_surface_overclaim"))

    def test_negative_reply_suffix_is_not_positive_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims({"note": "reply API ready remains blocked"}, blockers)

        self.assertEqual([], blockers)

    def test_rejects_missing_runtime_owned_principal_permissions_gate(self) -> None:
        decisions = self.load_decisions()
        gate = decisions["runtime_owned_principal_permissions_gate"]
        gate["runtime_owned_permission_allow_required"] = False
        gate["reply_send_chat_router_claims_allowed"] = True
        gate["required_runtime_owned_inputs"] = [
            item for item in gate["required_runtime_owned_inputs"] if item != "permission_decision"
        ]
        gate["forbidden_authority_sources"] = [
            item for item in gate["forbidden_authority_sources"] if item != "router metadata"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("runtime_owned_principal_permissions_gate_required_true_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_required_false_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_inputs_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_forbidden_sources_missing", report["blockers"])

    def test_rejects_missing_bridge_principal_fail_closed_auth_behaviors(self) -> None:
        decisions = self.load_decisions()
        auth = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "auth.identity_permission_provenance"
        )
        auth["required_behavior"] = [
            behavior
            for behavior in auth["required_behavior"]
            if behavior
            not in {
                "principal tuple source must be runtime-owned player identity observation before any command payload can consume player identity",
                "principal_handle, principal_generation, and principal_scope_flags must appear together in any future command payload that consumes player identity",
                "plugin-supplied principal tuple fails closed",
                "missing principal_handle fails closed",
                "missing principal_scope_flags fails closed",
                "server process epoch mismatch fails closed",
                "permission allow cannot be consumed without policy provenance",
                "permission allow must come from runtime-owned permissions/admin evaluation for the same principal_handle, principal_generation, and principal_scope_flags tuple",
                "reply requests, send-chat requests, and router metadata cannot establish principal identity, permission authority, or policy provenance",
                "reply/send-chat/router planning cannot consume permission allow until promoted permissions/admin returns allow with runtime-owned policy provenance",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("auth_identity_permission_behavior_missing", report["blockers"])
        detail = next(
            item for item in report["blocker_details"] if item["reason"] == "auth_identity_permission_behavior_missing"
        )
        self.assertIn(
            "principal tuple source must be runtime-owned player identity observation before any command payload can consume player identity",
            detail["missing"],
        )
        self.assertIn("plugin-supplied principal tuple fails closed", detail["missing"])
        self.assertIn("missing principal_handle fails closed", detail["missing"])
        self.assertIn("missing principal_scope_flags fails closed", detail["missing"])
        self.assertIn("server process epoch mismatch fails closed", detail["missing"])
        self.assertIn("permission allow cannot be consumed without policy provenance", detail["missing"])
        self.assertIn(
            "permission allow must come from runtime-owned permissions/admin evaluation for the same principal_handle, principal_generation, and principal_scope_flags tuple",
            detail["missing"],
        )
        self.assertIn(
            "reply requests, send-chat requests, and router metadata cannot establish principal identity, permission authority, or policy provenance",
            detail["missing"],
        )
        self.assertIn(
            "reply/send-chat/router planning cannot consume permission allow until promoted permissions/admin returns allow with runtime-owned policy provenance",
            detail["missing"],
        )

    def test_rejects_missing_lifecycle_and_abuse_contract_guards(self) -> None:
        decisions = self.load_decisions()
        decisions["forbidden_public_contract"] = [
            item
            for item in decisions["forbidden_public_contract"]
            if item != "raw ProcessEvent or legacy CallProcessEvent fallback"
        ]
        lifecycle = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "lifecycle.owner_scoped_registration_cleanup"
        )
        lifecycle["required_behavior"] = [
            item
            for item in lifecycle["required_behavior"]
            if item
            not in {
                "future command router, reply/send path, and response shortcuts require owner-scoped lifecycle and unregister cleanup before public ABI",
                "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy command lifecycle cleanup or dispatch drain",
            }
        ]
        abuse = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "abuse.rate_limit_audit_moderation_boundary"
        )
        abuse["required_behavior"] = [
            item
            for item in abuse["required_behavior"]
            if item
            != "command router, reply request, send-chat request, raw ProcessEvent, and legacy CallProcessEvent paths cannot bypass rate-limit, abuse, or sanitized audit gates"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])
        self.assertIn("lifecycle_owner_cleanup_behavior_missing", report["blockers"])
        self.assertIn("abuse_rate_limit_audit_behavior_missing", report["blockers"])

    def test_rejects_missing_migration_vocabulary_guardrail(self) -> None:
        decisions = self.load_decisions()
        decisions.pop("migration_vocabulary_not_compatibility", None)
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("migration_vocabulary_not_compatibility_missing", report["blockers"])

    def test_rejects_incomplete_migration_vocabulary_semantics(self) -> None:
        decisions = self.load_decisions()
        migration = decisions["migration_vocabulary_not_compatibility"]
        migration["allowed_terms"].remove("admin-like command")
        migration["recognized_source_kinds"].remove("server_console")
        migration["registration_semantics"].remove(
            "reply/send-chat/router planning must consume only runtime-owned principal and permissions provenance after separate promotion"
        )
        migration["registration_semantics"].remove("permission denial or unknown result never dispatches a command")
        migration["non_compatibility_claims"].remove("no direct plugin portability claim")
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("migration_vocabulary_allowed_terms_missing", report["blockers"])
        self.assertIn("migration_vocabulary_source_kinds_missing", report["blockers"])
        self.assertIn("migration_vocabulary_registration_semantics_missing", report["blockers"])
        self.assertIn("migration_vocabulary_non_compatibility_missing", report["blockers"])

    def test_rejects_response_path_planning_report_without_expected_root_and_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            result = self.run_checker("--response-path-report", str(report_path), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_expected_root_required", report["blockers"])
        self.assertIn("response_path_report_expected_readiness_required", report["blockers"])
        self.assertFalse(report["valid"])

    def test_accepts_response_path_planning_report_bound_to_expected_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            result = self.run_checker(
                "--response-path-report",
                str(report_path),
                "--response-path-root",
                str(root),
                "--response-path-readiness",
                str(root / "command-chat-response-route-planning-readiness.json"),
                "--json",
            )

        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertFalse(report["counts_toward_public_sdk"])

    def test_rejects_response_path_report_that_counts_despite_identity_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(root)
            response_report = json.loads(report_path.read_text(encoding="utf-8"))
            response_report["dependency_chain_locked"] = False
            response_report["counts_toward_public_sdk"] = True
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker(*self.response_path_args(report_path, root), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_dependency_chain_not_locked", report["blockers"])
        self.assertIn("response_path_report_counts_toward_public_sdk_not_false", report["blockers"])

    def test_rejects_response_path_report_copied_outside_expected_report_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source_root = base / "source-root"
            copied_root = base / "report-copy-dir"
            copied_root.mkdir()
            report_path = self.write_response_report(source_root)
            copied_report = copied_root / report_path.name
            copied_report.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
            result = self.run_checker(
                "--response-path-report",
                str(copied_report),
                "--response-path-root",
                str(source_root),
                "--response-path-readiness",
                str(source_root / "command-chat-response-route-planning-readiness.json"),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("response_path_report_path_mismatch", report["blockers"])

    def test_rejects_response_path_report_bound_to_unexpected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            expected_root = base / "expected-root"
            stale_root = base / "stale-root"
            expected_root.mkdir()
            stale_root.mkdir()
            report_path = self.write_response_report(stale_root)
            result = self.run_checker(
                "--response-path-report",
                str(report_path),
                "--response-path-root",
                str(expected_root),
                "--response-path-readiness",
                str(expected_root / "command-chat-response-route-planning-readiness.json"),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_readiness_root_mismatch", report["blockers"])
        self.assertIn("response_path_report_readiness_path_mismatch", report["blockers"])

    def test_rejects_optional_response_path_minimal_report_schema(self) -> None:
        response_report = {
            "schema": "obelisk.command-chat-response-public-readiness-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "surface": "obelisk.command_chat_response_path.v1",
            "public_readiness_ready": False,
            "public_header_allowed": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "response.json"
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_not_planning_only", report["blockers"])
        self.assertIn("response_path_report_target_set_mismatch", report["blockers"])
        self.assertIn("response_path_report_target_filters_mismatch", report["blockers"])
        self.assertIn("response_path_report_readiness_status_mismatch", report["blockers"])
        self.assertIn("response_path_report_decisions_status_mismatch", report["blockers"])
        self.assertIn("response_path_report_surfaces_status_mismatch", report["blockers"])

    def test_rejects_optional_response_path_minimal_raw_readiness(self) -> None:
        response_readiness = {
            "schema": "obelisk.reflection-snapshot-readiness.v1",
            "planning_layout_gate": {"ready": True},
            "promotion_gate": {"ready": False},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "response-readiness.json"
            report_path.write_text(json.dumps(response_readiness), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_schema_mismatch", report["blockers"])

    def test_rejects_optional_response_path_report_promoted_overclaim(self) -> None:
        response_report = {
            "schema": "obelisk.command-chat-response-public-readiness-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "planning_only": True,
            "surface": "obelisk.command_chat_response_path.v1",
            "target_set": "command-chat-response-route-planning",
            "target_filters": RESPONSE_TARGETS,
            "readiness_status": "compared",
            "decisions_status": "blocked",
            "surfaces_status": "planning",
            "public_readiness_ready": True,
            "public_header_allowed": False,
            "promotion_ready": True,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
            "readiness_path": "/offline/command-chat-response-route-planning-readiness.json",
            "decisions_path": "/offline/command_chat_response_public_contract_decisions.json",
            "surfaces_path": "/offline/public_sdk_surfaces.json",
            "public_header_path": "/offline/ObeliskApi.h",
            "blockers": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = root / "response.json"
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_public_readiness_ready_not_false", report["blockers"])
        self.assertIn("response_path_report_promotion_ready_not_false", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])

    def test_rejects_json_input_under_protected_server_root(self) -> None:
        result = self.run_checker(
            "--decisions",
            "/servidor/ark/commands_replies_public_contract_decisions.json",
            check=False,
        )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("decisions_path_rejected", report["blockers"])

    def test_rejects_json_input_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path = Path(temp_dir) / "decisions.json"
            decisions_path.write_text(json.dumps(self.load_decisions()), encoding="utf-8")
            link_path = Path(temp_dir) / "decisions-link.json"
            link_path.symlink_to(decisions_path)
            result = self.run_checker("--decisions", str(link_path), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("decisions_path_rejected", report["blockers"])


if __name__ == "__main__":
    unittest.main()
