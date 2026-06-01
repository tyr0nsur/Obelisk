#!/usr/bin/env python3
"""Tests for check_command_chat_response_public_readiness.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_chat_response_public_readiness.py"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"


TARGETS = [
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
]


class CheckCommandChatResponsePublicReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def make_readiness(self) -> dict:
        return {
            "schema": "obelisk.reflection-snapshot-readiness.v1",
            "evidence_scope": "second_source_layout_evidence_only",
            "gate_mode": "planning_layout_intake",
            "modules": [
                {
                    "block_reasons": {},
                    "blocked": 0,
                    "comparable": 3,
                    "module": "base-snapshots",
                    "schema": "ufunction",
                    "second_source": {
                        "accepted": 3,
                        "inconclusive": 0,
                        "missing": 0,
                        "rejected": 0,
                    },
                    "target_details": [
                        {
                            "block_reasons": [],
                            "comparable": True,
                            "path": f"/offline/{target.rsplit(':', 1)[1]}.snapshot.json",
                            "second_source_status": "accepted",
                            "target": target,
                        }
                        for target in TARGETS
                    ],
                    "targets": 3,
                }
            ],
            "non_claims": [
                "accepted second-source readiness is layout evidence only",
                "does not promote public SDK, Mission SDK, Transfer SDK, Structure SDK, StructureEvents, Inventory SDK, Items SDK, object identity, lookup, mutation, return override, ResourceHandle, or runtime hooks",
            ],
            "not_promoted_surfaces": ["public_sdk", "raw_params", "runtime_hooks"],
            "planning_layout_gate": {
                "blockers": [],
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "ready": True,
                "ready_scope": "planning_only",
                "runtime_ready": False,
            },
            "promotion_gate": {
                "blockers": [{"count": 1, "reason": "planning_layout_intake_not_promotion_gate"}],
                "layout_ready": True,
                "promotion_ready": False,
                "ready": False,
                "ready_scope": "planning_only",
            },
            "second_source_status": "compared",
            "strict_identity_indices": False,
            "target_filters": TARGETS,
            "target_set_guidance": [
                {
                    "classification": "command_chat_response_route_guidance_only_candidate",
                    "next_offline_input": "generate focal snapshots for response-path targets",
                    "non_claim": "does not promote command/chat response path, public reply/send-chat ABI, command router, permissions, player identity, raw FString access, mutation, return override, runtime hooks, or release readiness",
                    "snapshot_prep_checks": [
                        "keep reply API, send-chat API, broadcast/notices, moderation, command router, permission checks, mutation, and return override blocked",
                        "require promoted player identity/principal and permissions/admin before any public response path is considered",
                        "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
                        "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
                        "sender identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                        "directed recipient identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                        "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
                    ],
                    "target_set": "command-chat-response-route-planning",
                    "why_blocked": [
                        "planning_guidance_only",
                        "not_release_readiness_target",
                        "public_response_path_blocked",
                        "player_identity_principal_blocked",
                        "permissions_admin_blocked",
                        "command_router_blocked",
                        "runtime_observation_requires_separate_approval",
                    ],
                }
            ],
            "target_sets": ["command-chat-response-route-planning"],
            "totals": {
                "blocked": 0,
                "comparable": 3,
                "second_source_accepted": 3,
                "second_source_inconclusive": 0,
                "second_source_missing": 0,
                "second_source_rejected": 0,
                "targets": 3,
            },
        }

    def make_decisions(self) -> dict:
        required = [
            {"id": "dependency.promoted_player_identity", "status": "unresolved", "required_behavior": [
                "runtime observation establishes principal identity before command/chat response can consume it",
                "command text cannot establish principal identity",
                "operator config enables surfaces only and cannot establish principal identity",
                "response delivery never creates identity or permission claims",
            ]},
            {"id": "dependency.promoted_permissions_admin", "status": "unresolved"},
            {"id": "abi.copied_response_payload", "status": "unresolved"},
            {"id": "abi.capability_and_owner_token", "status": "unresolved"},
            {"id": "lifecycle.owner_scoped_unregister_and_drain", "status": "unresolved"},
            {"id": "privacy.redaction_and_targeting", "status": "unresolved", "required_behavior": [
                "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
                "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
                "sender identity remains redacted and does not expose player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                "directed recipient identity remains redacted and does not expose player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
            ]},
            {"id": "abuse.rate_limit_and_audit", "status": "unresolved"},
            {"id": "separation.no_commands_router_or_moderation", "status": "unresolved", "required_exclusions": [
                "command router",
                "command registration API",
                "moderation API",
            ]},
            {"id": "evidence.layout_runtime_sdk_coverage", "status": "unresolved"},
            {"id": "evidence.response_target_set_snapshot_second_source", "status": "unresolved", "required_targets": TARGETS},
        ]
        return {
            "schema": "obelisk.command-chat-response-public-contract-decisions.v1",
            "surface": "obelisk.command_chat_response_path.v1",
            "status": "blocked",
            "public_header_allowed": False,
            "public_header": "include/obelisk/ObeliskApi.h",
            "public_header_symbols_now": [],
            "legacy_call_process_event_public_response_allowed": False,
            "forbidden_public_contract": [
                "public CallProcessEvent response path",
                "reply API",
                "send-chat API",
                "broadcast/notices API",
                "moderation API",
                "raw UE pointers",
                "raw ProcessEvent params",
                "raw FString storage",
                "UObject pointers",
                "UFunction pointers",
                "FName/GObjects indices",
                "direct native-call wrappers",
                "principal or permission claims from command text",
                "principal or permission claims from operator config",
                "player lookup",
                "mutation",
                "return override",
            ],
            "required_before_public_header": required,
        }

    def write_inputs(self, root: Path, readiness: dict | None = None, decisions: dict | None = None) -> tuple[Path, Path, Path]:
        readiness_path = root / "command-chat-response-route-planning-readiness.json"
        decisions_path = root / "command_chat_response_public_contract_decisions.json"
        public_header_path = root / "ObeliskApi.h"
        readiness_path.write_text(json.dumps(readiness if readiness is not None else self.make_readiness()), encoding="utf-8")
        decisions_path.write_text(json.dumps(decisions if decisions is not None else self.make_decisions()), encoding="utf-8")
        public_header_path.write_text("/* minimal public header without response-path ABI */\n", encoding="utf-8")
        return readiness_path, decisions_path, public_header_path

    def test_accepts_planning_layout_second_source_but_not_public_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir))
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
            )

        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual([], report["blockers"])
        self.assertEqual(sorted(TARGETS), report["target_filters"])

    def test_rejects_readiness_public_runtime_and_promotion_overclaims(self) -> None:
        readiness = self.make_readiness()
        readiness["planning_layout_gate"]["promotion_ready"] = True
        readiness["promotion_gate"]["ready"] = True
        readiness["target_set_guidance"][0]["reply_api"] = True
        readiness["claim"] = "reply API is public and ready"
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), readiness=readiness)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("ready_mismatch", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_decision_public_header_overclaims(self) -> None:
        decisions = self.make_decisions()
        decisions["status"] = "promoted"
        decisions["public_header_allowed"] = True
        decisions["public_header_symbols_now"] = ["RegisterCommandChatResponse"]
        decisions["required_before_public_header"][0]["status"] = "resolved"
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("status_mismatch", report["blockers"])
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("required_before_public_header_item_not_unresolved", report["blockers"])

    def test_rejects_response_path_symbols_in_public_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            public_header_path.write_text(
                "typedef struct ObeliskCommandChatResponse ObeliskCommandChatResponse;\n"
                "void RegisterCommandChatResponse(void);\n"
                "#define OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH 0x80000000u\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_forbidden_symbols_present", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_forbidden_symbols_present")
        self.assertIn("ObeliskCommandChatResponse", detail["symbols"])
        self.assertIn("RegisterCommandChatResponse", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH", detail["symbols"])

    def test_rejects_explicit_surface_claim_fields(self) -> None:
        for field in (
            "send_chat_api",
            "command_router",
            "player_identity_ready",
            "permissions_ready",
            "public_header_ready",
        ):
            with self.subTest(field=field):
                readiness = self.make_readiness()
                readiness[field] = True
                with tempfile.TemporaryDirectory() as temp_dir:
                    readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), readiness=readiness)
                    result = self.run_checker(
                        "--readiness",
                        str(readiness_path),
                        "--decisions",
                        str(decisions_path),
                        "--public-header",
                        str(public_header_path),
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                self.assertIn("public_surface_overclaim", report["blockers"])

    def test_rejects_non_matching_target_set_and_missing_second_source(self) -> None:
        readiness = deepcopy(self.make_readiness())
        readiness["target_sets"] = ["chat-intake"]
        readiness["totals"]["second_source_missing"] = 1
        readiness["modules"][0]["target_details"][0]["second_source_status"] = "missing"
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), readiness=readiness)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("target_sets_mismatch", report["blockers"])
        self.assertIn("second_source_missing_mismatch", report["blockers"])
        self.assertIn("second_source_status_mismatch", report["blockers"])

    def test_rejects_missing_response_redaction_guidance(self) -> None:
        cases = (
            "ClientChatMessage.Chat",
            "raw FString storage/data",
            "sender identity remains redacted",
            "directed recipient identity remains redacted",
            "future targeting must use only a promoted copied principal handle/generation",
        )
        for phrase in cases:
            with self.subTest(phrase=phrase):
                readiness = self.make_readiness()
                readiness["target_set_guidance"][0]["snapshot_prep_checks"] = [
                    check
                    for check in readiness["target_set_guidance"][0]["snapshot_prep_checks"]
                    if phrase not in check
                ]
                with tempfile.TemporaryDirectory() as temp_dir:
                    readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), readiness=readiness)
                    result = self.run_checker(
                        "--readiness",
                        str(readiness_path),
                        "--decisions",
                        str(decisions_path),
                        "--public-header",
                        str(public_header_path),
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                self.assertIn("target_set_guidance_missing_redaction_checks", report["blockers"])

    def test_rejects_missing_privacy_decision_behavior(self) -> None:
        decisions = self.make_decisions()
        privacy = next(item for item in decisions["required_before_public_header"] if item["id"] == "privacy.redaction_and_targeting")
        privacy["required_behavior"] = [
            item for item in privacy["required_behavior"] if not item.startswith("raw FString storage/data")
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("privacy_redaction_behavior_missing", report["blockers"])

    def test_rejects_missing_call_process_event_and_native_wrapper_forbidden_contracts(self) -> None:
        decisions = self.make_decisions()
        decisions["forbidden_public_contract"] = [
            item
            for item in decisions["forbidden_public_contract"]
            if item
            not in {
                "public CallProcessEvent response path",
                "direct native-call wrappers",
                "broadcast/notices API",
                "moderation API",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])

    def test_rejects_surface_manifest_response_path_overclaim(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        response = next(item for item in surfaces["surfaces"] if item["id"] == "obelisk.command_chat_response_path.v1")
        response["status"] = "promoted"
        response["public_abi"] = True
        response["adds_obelisk_api"] = True
        response["public_contract"] = ["ObeliskCommandChatResponse"]
        response["depends_on"] = ["obelisk.player_identity.v1"]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = root / "public_sdk_surfaces.json"
            surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--surfaces",
                str(surfaces_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("status_mismatch", report["blockers"])
        self.assertIn("public_abi_not_false", report["blockers"])
        self.assertIn("adds_obelisk_api_not_false", report["blockers"])
        self.assertIn("command_chat_response_surface_public_contract_not_empty", report["blockers"])
        self.assertIn("command_chat_response_surface_dependencies_mismatch", report["blockers"])


if __name__ == "__main__":
    unittest.main()
