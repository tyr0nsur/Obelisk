#!/usr/bin/env python3
"""Tests for check_command_chat_response_public_readiness.py."""

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
SCRIPT = SCRIPT_DIR / "check_command_chat_response_public_readiness.py"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_command_chat_response_public_readiness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
READINESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = READINESS
SPEC.loader.exec_module(READINESS)


TARGETS = [
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
]


def target_snapshot_payload(target: str) -> dict:
    return {
        "schema": "obelisk.ufunction-chain.snapshot.v1",
        "evidence": {
            "artifact_sha256": "a" * 64,
            "capture_id": "unit-test-command-response",
            "evidence_pack_id": "unit-test-command-response-pack",
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


class CheckCommandChatResponsePublicReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def make_readiness(self, root: Path | None = None) -> dict:
        def target_path(target: str) -> str:
            basename = f"{target.rsplit(':', 1)[1]}.snapshot.json"
            if root is None:
                return f"/offline/{basename}"
            return str(root / "base-snapshots" / basename)

        source_root = str(root) if root is not None else "/offline"
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
                    "--target-set",
                    "command-chat-response-route-planning",
                    "--readiness-report",
                    "--json",
                ],
                "output_name": "command-chat-response-route-planning-readiness.json",
            },
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
                            "path": target_path(target),
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
                "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish principal identity",
                "generic chat routing cannot establish principal identity",
                "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish principal identity or roadmap priority",
                "commands/replies planning cannot bypass identity promotion",
            ]},
            {"id": "dependency.promoted_permissions_admin", "status": "unresolved", "required_behavior": [
                "permissions/admin must be promoted before any reply, send-chat, broadcast, or moderation delivery is public",
                "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish permissions or admin authority",
                "generic chat routing cannot establish permissions or admin authority",
                "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish permissions, targeting, command authority, moderation authority, or roadmap priority",
                "commands/replies planning cannot bypass permissions/admin promotion",
                "runtime-owned permissions/admin allow for the same runtime-owned principal tuple is required before any reply, send-chat, broadcast, moderation, or router response path is public",
            ]},
            {"id": "abi.copied_response_payload", "status": "unresolved"},
            {"id": "abi.capability_and_owner_token", "status": "unresolved", "required_behavior": [
                "captured post-init debug CallProcessEvent tables do not authorize response delivery",
                "minimal ChatMessageEvent registration does not authorize response delivery",
                "generic chat routing does not authorize response delivery",
                "raw ProcessEvent callbacks do not authorize response delivery",
                "static thunk orientation does not authorize response delivery",
            ]},
            {"id": "lifecycle.owner_scoped_unregister_and_drain", "status": "unresolved", "required_behavior": [
                "owner unregister cancels pending responses for that plugin owner",
                "plugin init failure cleans up registered response handles before dlclose",
                "plugin unload waits for in-flight response callbacks or fails closed without dlclose",
                "future reply/send-chat/router response paths require owner-scoped lifecycle and unregister cleanup before public ABI",
                "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy response unregister cleanup or drain",
                "response callbacks cannot outlive copied payload storage",
                "server shutdown does not call into unmapped plugin code",
            ]},
            {"id": "privacy.redaction_and_targeting", "status": "unresolved", "required_behavior": [
                "principal tuple source must be runtime-owned player identity observation before any directed response target is public",
                "principal_handle, principal_generation, and principal_scope_flags must appear together before response targeting can consume player identity",
                "plugin-supplied principal tuple fails closed",
                "command-supplied principal tuple fails closed",
                "operator-supplied principal tuple fails closed",
                "missing principal provenance fails closed",
                "server process epoch mismatch fails closed",
                "permission allow cannot be consumed without policy provenance",
                "runtime-owned principal tuple must be paired with runtime-owned permission provenance before reply/send-chat/router planning can become public",
                "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
                "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
                "sender identity remains redacted and does not expose player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                "directed recipient identity remains redacted and does not expose player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
            ]},
            {"id": "abuse.rate_limit_and_audit", "status": "unresolved", "required_behavior": [
                "response attempts are rate-limited per plugin owner token",
                "reply/send-chat/router response attempts require rate-limit and sanitized audit checks per plugin owner token before delivery",
                "burst exhaustion drops or rejects the response, never bypasses permission checks",
                "raw ProcessEvent and legacy CallProcessEvent fallback cannot bypass response abuse or audit gates",
                "malformed UTF-8 or oversize messages fail closed",
                "audit records are sanitized and do not expose raw UE internals",
                "operator controls can disable response delivery without disabling passive chat intake",
            ]},
            {"id": "separation.no_commands_router_or_moderation", "status": "unresolved", "required_exclusions": [
                "command router",
                "command registration API",
                "commands/replies shortcut before identity and permissions/admin",
                "public response path through ChatMessageEvent",
                "public response path through generic chat routing",
                "public response path through raw ProcessEvent",
                "public response path through static thunk orientation",
                "reply/send-chat/broadcast/moderation through legacy CallProcessEvent",
                "reply/send-chat/router claims before promotion",
                "moderation API",
            ], "v1_sequence_gate": [
                "minimal ChatMessageEvent remains passive input and cannot route replies/send-chat/broadcast/moderation",
                "generic chat routing cannot bypass promoted identity and permissions/admin",
                "chat intake is observation only and cannot become identity, permission, command authority, moderation authority, targeting, or roadmap priority",
                "raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot bypass identity and permissions/admin",
            ]},
            {
                "id": "evidence.layout_runtime_sdk_coverage",
                "status": "unresolved",
                "not_sufficient": [
                    "static thunk orientation",
                    "candidate vtable slots",
                    "minimal ChatMessageEvent callback registration",
                    "passive ChatMessageEvent parsing",
                    "generic chat routing",
                    "commands/replies planning status",
                    "legacy CallProcessEvent debug gate",
                    "raw ProcessEvent callbacks",
                ],
            },
            {"id": "evidence.response_target_set_snapshot_second_source", "status": "unresolved", "required_targets": TARGETS, "not_sufficient": [
                "static thunk orientation",
                "minimal ChatMessageEvent callback registration",
                "generic chat routing",
                "raw ProcessEvent callbacks",
                "legacy CallProcessEvent debug gate",
            ]},
        ]
        return {
            "schema": "obelisk.command-chat-response-public-contract-decisions.v1",
            "surface": "obelisk.command_chat_response_path.v1",
            "status": "blocked",
            "public_header_allowed": False,
            "public_header": "include/obelisk/ObeliskApi.h",
            "public_header_symbols_now": [],
            "legacy_call_process_event_public_response_allowed": False,
            "minimal_chat_message_event_public_response_allowed": False,
            "generic_chat_routing_public_response_allowed": False,
            "raw_process_event_public_response_allowed": False,
            "static_thunk_orientation_public_response_allowed": False,
            "commands_replies_shortcut_public_response_allowed": False,
            "runtime_owned_principal_permissions_gate": {
                "planning_only": True,
                "runtime_owned_principal_required": True,
                "runtime_owned_permission_allow_required": True,
                "same_principal_tuple_required": True,
                "permission_policy_provenance_required": True,
                "reply_send_chat_router_claims_allowed": False,
                "public_abi_allowed": False,
                "runtime_delivery_allowed": False,
                "required_runtime_owned_inputs": [
                    "principal_handle",
                    "principal_generation",
                    "principal_scope_flags",
                    "server_process_epoch",
                    "permission_decision",
                    "permission_policy_epoch",
                    "policy_source_id",
                    "policy_source_generation",
                    "authority_kind",
                    "authority_generation",
                ],
                "forbidden_authority_sources": [
                    "plugin input",
                    "command text",
                    "operator config",
                    "reply request",
                    "send-chat request",
                    "router metadata",
                    "passive ChatMessageEvent",
                    "raw ProcessEvent",
                    "legacy CallProcessEvent",
                    "static thunk orientation",
                ],
            },
            "forbidden_public_contract": [
                "public CallProcessEvent response path",
                "public minimal ChatMessageEvent response path",
                "public generic chat routing response path",
                "public raw ProcessEvent response path",
                "raw ProcessEvent or legacy CallProcessEvent fallback",
                "public static thunk orientation response path",
                "public commands/replies response shortcut before promoted identity and permissions/admin",
                "reply API",
                "send-chat API",
                "reply/send-chat/router claims before promotion",
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

    def write_inputs(
        self,
        root: Path,
        readiness: dict | None = None,
        decisions: dict | None = None,
        *,
        temp_header: bool = False,
    ) -> tuple[Path, Path, Path]:
        snapshot_root = root / "base-snapshots"
        snapshot_root.mkdir(parents=True, exist_ok=True)
        for target in TARGETS:
            (snapshot_root / f"{target.rsplit(':', 1)[1]}.snapshot.json").write_text(
                json.dumps(target_snapshot_payload(target.rsplit(":", 1)[1])),
                encoding="utf-8",
            )
        readiness_path = root / "command-chat-response-route-planning-readiness.json"
        decisions_path = root / "command_chat_response_public_contract_decisions.json"
        effective_readiness = deepcopy(readiness) if readiness is not None else self.make_readiness(root)
        if effective_readiness.get("source_root") in (None, "/offline"):
            effective_readiness["source_root"] = str(root)
        effective_readiness.setdefault(
            "producer",
            {
                "script": "scripts/compare_reflection_snapshots.py",
                "argv": [
                    "scripts/compare_reflection_snapshots.py",
                    "--base-root",
                    effective_readiness["source_root"],
                    "--target-set",
                    "command-chat-response-route-planning",
                    "--readiness-report",
                    "--json",
                ],
                "output_name": "command-chat-response-route-planning-readiness.json",
            },
        )
        producer = effective_readiness.get("producer")
        if isinstance(producer, dict) and isinstance(producer.get("argv"), list):
            producer["argv"] = [
                effective_readiness["source_root"] if item == "/offline" else item
                for item in producer["argv"]
            ]
        readiness_path.write_text(json.dumps(effective_readiness), encoding="utf-8")
        decisions_path.write_text(json.dumps(decisions if decisions is not None else self.make_decisions()), encoding="utf-8")
        if temp_header:
            public_header_path = root / "ObeliskApi.h"
            public_header_path.write_text("/* minimal public header without response-path ABI */\n", encoding="utf-8")
        else:
            public_header_path = READINESS.DEFAULT_PUBLIC_HEADER
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
        self.assertTrue(report["dependency_chain_locked"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertEqual([], report["blockers"])
        self.assertEqual(sorted(TARGETS), report["target_filters"])

    def test_default_root_is_repo_local_and_provenance_bound(self) -> None:
        self.assertTrue(READINESS.DEFAULT_ROOT.is_relative_to(REPO_ROOT))
        self.assertNotIn("/servidor/ark", str(READINESS.DEFAULT_ROOT))

        result = self.run_checker("--json")
        report = json.loads(result.stdout)

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(str(READINESS.DEFAULT_ROOT.resolve()), report["readiness_root"])
        self.assertEqual([], report["blockers"])

    def test_rejects_readiness_without_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir))
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            readiness.pop("source_root")
            readiness.pop("producer")
            readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("readiness_provenance_missing", report["blockers"])
        self.assertIn("readiness_producer_missing", report["blockers"])

    def test_default_root_readiness_still_requires_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            readiness.pop("source_root")
            readiness.pop("producer")
            readiness_path.write_text(json.dumps(readiness), encoding="utf-8")

            old_default_root = READINESS.DEFAULT_ROOT
            try:
                READINESS.DEFAULT_ROOT = root
                report = READINESS.build_report(
                    root,
                    readiness_path,
                    decisions_path,
                    public_header_path,
                    SURFACES,
                )
            finally:
                READINESS.DEFAULT_ROOT = old_default_root

        self.assertFalse(report["valid"])
        self.assertIn("readiness_provenance_missing", report["blockers"])
        self.assertIn("readiness_producer_missing", report["blockers"])

    def test_rejects_readiness_source_root_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stale_root = root / "stale-root"
            stale_root.mkdir()
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            readiness["source_root"] = str(stale_root)
            readiness["producer"]["argv"] = [
                str(stale_root) if item == str(root) else item
                for item in readiness["producer"]["argv"]
            ]
            readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("readiness_source_root_mismatch", report["blockers"])

    def test_rejects_placeholder_target_snapshot_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            first_snapshot = root / "base-snapshots" / "ShooterPlayerController.ClientChatMessage.snapshot.json"
            first_snapshot.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.ufunction-chain.snapshot.v1",
                        "status": "fixture-placeholder",
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("target_snapshot_placeholder", report["blockers"])
        self.assertIn("target_snapshot_evidence_missing", report["blockers"])
        self.assertIn("target_snapshot_targets_invalid", report["blockers"])

    def test_rejects_readiness_not_bound_to_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            expected_root = base / "expected-root"
            stale_root = base / "stale-root"
            expected_root.mkdir()
            stale_root.mkdir()
            readiness_path, decisions_path, public_header_path = self.write_inputs(stale_root)
            result = self.run_checker(
                "--root",
                str(expected_root),
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("readiness_path_not_bound_to_root", report["blockers"])
        self.assertIn("target_detail_path_root_mismatch", report["blockers"])

    def test_rejects_readiness_public_runtime_and_promotion_overclaims(self) -> None:
        readiness = self.make_readiness()
        readiness["planning_layout_gate"]["promotion_ready"] = True
        readiness["promotion_gate"]["ready"] = True
        readiness["target_set_guidance"][0]["reply_api"] = True
        readiness["target_set_guidance"][0]["public_readiness_ready"] = True
        readiness["target_set_guidance"][0]["public_response_path_allowed"] = True
        readiness["target_set_guidance"][0]["public_reply_or_send_chat_abi_allowed"] = True
        readiness["target_set_guidance"][0]["reply_api_allowed"] = True
        readiness["target_set_guidance"][0]["send_chat_api_allowed"] = True
        readiness["target_set_guidance"][0]["runtime_delivery_allowed"] = True
        readiness["target_set_guidance"][0]["required_behavior"] = ["reply API is public and ready"]
        readiness["claim"] = "reply API is public and ready"
        readiness["generic_chat_claim"] = "generic chat routing is public and ready"
        readiness["send_chat_claim"] = "send-chat is available"
        readiness["router_claim"] = "router is supported"
        readiness["live_claim"] = "command response path is live"
        readiness["endpoint_claim"] = "reply endpoint is live"
        readiness["operational_claim"] = "send chat API is operational"
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

    def test_mixed_negation_does_not_hide_positive_send_chat_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {"note": "reply API remains blocked but send-chat API is operational"},
            blockers,
        )

        self.assertEqual(["positive_public_surface_claim"], [item["reason"] for item in blockers])

    def test_negative_reply_suffix_is_not_positive_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims({"note": "reply API ready remains blocked"}, blockers)

        self.assertEqual([], blockers)

    def test_nested_runtime_and_supported_router_claims_are_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "nested_report": {
                    "structured_evidence": [
                        {"runtime_claim": "runtime delivery is ready"},
                        {"router_claim": "command router is supported"},
                    ],
                },
            },
            blockers,
        )

        self.assertEqual(
            ["positive_public_surface_claim", "positive_public_surface_claim"],
            [item["reason"] for item in blockers],
        )
        self.assertEqual(
            [
                "$.nested_report.structured_evidence[0].runtime_claim",
                "$.nested_report.structured_evidence[1].router_claim",
            ],
            [item["label"] for item in blockers],
        )

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
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, temp_header=True)
            public_header_path.write_text(
                "typedef struct ObeliskCommandChatResponse ObeliskCommandChatResponse;\n"
                "typedef struct ObeliskChatRouter ObeliskChatRouter;\n"
                "void RegisterCommandChatResponse(void);\n"
                "void RegisterChatRouter(void);\n"
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
        self.assertIn("ObeliskChatRouter", detail["symbols"])
        self.assertIn("RegisterCommandChatResponse", detail["symbols"])
        self.assertIn("RegisterChatRouter", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH", detail["symbols"])

    def test_public_header_scan_ignores_comments_and_identifier_supersets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, temp_header=True)
            public_header_path.write_text(
                "/* ObeliskCommandChatResponse and RegisterCommandChatResponse stay blocked. */\n"
                "// OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH remains absent.\n"
                "typedef struct MyObeliskCommandChatResponseSuffix MyObeliskCommandChatResponseSuffix;\n"
                "void RegisterCommandChatResponseForTestsOnly(void);\n"
                "#define OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH_EXTRA 1\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("public_header_path_mismatch", report["blockers"])
        self.assertNotIn("public_header_forbidden_symbols_present", report["blockers"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_public_header_not_canonical_repo_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, temp_header=True)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_path_mismatch", report["blockers"])
        self.assertIn("decisions_public_header_not_scanned_header", report["blockers"])

    def test_rejects_decision_public_header_path_mismatch(self) -> None:
        decisions = self.make_decisions()
        decisions["public_header"] = "include/obelisk/OtherApi.h"
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("decisions_public_header_mismatch", report["blockers"])
        self.assertIn("decisions_public_header_not_scanned_header", report["blockers"])

    def test_rejects_explicit_surface_claim_fields(self) -> None:
        for field in (
            "send_chat_api",
            "command_router",
            "chat_routing",
            "generic_chat_routing_public_response_allowed",
            "player_identity_ready",
            "permissions_ready",
            "public_header_ready",
            "public_reply_abi_allowed",
            "public_send_chat_abi_allowed",
            "reply_allowed",
            "send_chat_allowed",
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
            item
            for item in privacy["required_behavior"]
            if not item.startswith("raw FString storage/data")
            and not item.startswith("principal tuple source must be runtime-owned")
            and item != "plugin-supplied principal tuple fails closed"
            and item != "permission allow cannot be consumed without policy provenance"
            and item != (
                "runtime-owned principal tuple must be paired with runtime-owned permission provenance "
                "before reply/send-chat/router planning can become public"
            )
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
        detail = next(
            item for item in report["blocker_details"] if item["reason"] == "privacy_redaction_behavior_missing"
        )
        self.assertIn(
            "principal tuple source must be runtime-owned player identity observation before any directed response target is public",
            detail["missing"],
        )
        self.assertIn("plugin-supplied principal tuple fails closed", detail["missing"])
        self.assertIn("permission allow cannot be consumed without policy provenance", detail["missing"])
        self.assertIn(
            "runtime-owned principal tuple must be paired with runtime-owned permission provenance before reply/send-chat/router planning can become public",
            detail["missing"],
        )

    def test_rejects_missing_runtime_owned_principal_permissions_gate(self) -> None:
        decisions = self.make_decisions()
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
        self.assertIn("runtime_owned_principal_permissions_gate_required_true_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_required_false_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_inputs_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_forbidden_sources_missing", report["blockers"])

    def test_rejects_missing_response_lifecycle_and_abuse_guards(self) -> None:
        decisions = self.make_decisions()
        decisions["forbidden_public_contract"] = [
            item
            for item in decisions["forbidden_public_contract"]
            if item != "raw ProcessEvent or legacy CallProcessEvent fallback"
        ]
        lifecycle = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "lifecycle.owner_scoped_unregister_and_drain"
        )
        lifecycle["required_behavior"] = [
            item
            for item in lifecycle["required_behavior"]
            if item
            not in {
                "future reply/send-chat/router response paths require owner-scoped lifecycle and unregister cleanup before public ABI",
                "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy response unregister cleanup or drain",
            }
        ]
        abuse = next(
            item for item in decisions["required_before_public_header"] if item["id"] == "abuse.rate_limit_and_audit"
        )
        abuse["required_behavior"] = [
            item
            for item in abuse["required_behavior"]
            if item
            not in {
                "reply/send-chat/router response attempts require rate-limit and sanitized audit checks per plugin owner token before delivery",
                "raw ProcessEvent and legacy CallProcessEvent fallback cannot bypass response abuse or audit gates",
            }
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
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])
        self.assertIn("lifecycle_owner_unregister_behavior_missing", report["blockers"])
        self.assertIn("abuse_rate_limit_audit_behavior_missing", report["blockers"])

    def test_rejects_missing_not_sufficient_shortcut_evidence(self) -> None:
        decisions = self.make_decisions()
        evidence = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "evidence.layout_runtime_sdk_coverage"
        )
        evidence["not_sufficient"] = [
            "candidate vtable slots",
            "raw ProcessEvent callbacks",
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
        self.assertIn("evidence_not_sufficient_missing_required", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "evidence_not_sufficient_missing_required"
        )
        self.assertIn("passive ChatMessageEvent parsing", detail["missing"])
        self.assertIn("minimal ChatMessageEvent callback registration", detail["missing"])
        self.assertIn("generic chat routing", detail["missing"])
        self.assertIn("static thunk orientation", detail["missing"])
        self.assertIn("legacy CallProcessEvent debug gate", detail["missing"])

    def test_rejects_missing_generic_chat_routing_separation(self) -> None:
        decisions = self.make_decisions()
        decisions["generic_chat_routing_public_response_allowed"] = True
        decisions["forbidden_public_contract"] = [
            item for item in decisions["forbidden_public_contract"] if item != "public generic chat routing response path"
        ]
        capability = next(
            item for item in decisions["required_before_public_header"] if item["id"] == "abi.capability_and_owner_token"
        )
        capability["required_behavior"] = [
            item for item in capability["required_behavior"] if item != "generic chat routing does not authorize response delivery"
        ]
        separation = next(
            item for item in decisions["required_before_public_header"] if item["id"] == "separation.no_commands_router_or_moderation"
        )
        separation["v1_sequence_gate"] = [
            item for item in separation["v1_sequence_gate"] if item != "generic chat routing cannot bypass promoted identity and permissions/admin"
        ]
        separation["required_exclusions"] = [
            item for item in separation["required_exclusions"] if item != "public response path through generic chat routing"
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
        self.assertIn("generic_chat_routing_public_response_allowed_not_false", report["blockers"])
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])
        self.assertIn("capability_behavior_missing", report["blockers"])
        self.assertIn("separation_sequence_gate_missing", report["blockers"])
        self.assertIn("separation_exclusion_missing", report["blockers"])

    def test_rejects_missing_generic_chat_routing_identity_permission_dependency(self) -> None:
        decisions = self.make_decisions()
        identity = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "dependency.promoted_player_identity"
        )
        permissions = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "dependency.promoted_permissions_admin"
        )
        identity["required_behavior"] = [
            item
            for item in identity["required_behavior"]
            if item != "generic chat routing cannot establish principal identity"
        ]
        permissions["required_behavior"] = [
            item
            for item in permissions["required_behavior"]
            if item != "generic chat routing cannot establish permissions or admin authority"
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
        self.assertIn("identity_dependency_behavior_missing", report["blockers"])
        self.assertIn("permissions_dependency_behavior_missing", report["blockers"])
        detail_behaviors = {
            item["behavior"]
            for item in report["blocker_details"]
            if item["reason"] in {"identity_dependency_behavior_missing", "permissions_dependency_behavior_missing"}
        }
        self.assertIn("generic chat routing cannot establish principal identity", detail_behaviors)
        self.assertIn("generic chat routing cannot establish permissions or admin authority", detail_behaviors)

    def test_rejects_missing_chat_intake_is_not_authority_guardrails(self) -> None:
        decisions = self.make_decisions()
        identity = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "dependency.promoted_player_identity"
        )
        permissions = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "dependency.promoted_permissions_admin"
        )
        separation = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "separation.no_commands_router_or_moderation"
        )
        identity["required_behavior"] = [
            item
            for item in identity["required_behavior"]
            if item != "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish principal identity or roadmap priority"
        ]
        permissions["required_behavior"] = [
            item
            for item in permissions["required_behavior"]
            if item != "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish permissions, targeting, command authority, moderation authority, or roadmap priority"
        ]
        separation["v1_sequence_gate"] = [
            item
            for item in separation["v1_sequence_gate"]
            if item != "chat intake is observation only and cannot become identity, permission, command authority, moderation authority, targeting, or roadmap priority"
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
        self.assertIn("identity_dependency_behavior_missing", report["blockers"])
        self.assertIn("permissions_dependency_behavior_missing", report["blockers"])
        self.assertIn("separation_sequence_gate_missing", report["blockers"])

    def test_rejects_response_target_shortcut_evidence_gap(self) -> None:
        decisions = self.make_decisions()
        evidence = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "evidence.response_target_set_snapshot_second_source"
        )
        evidence["not_sufficient"] = [
            item
            for item in evidence["not_sufficient"]
            if item not in {"generic chat routing", "static thunk orientation"}
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
        self.assertIn("response_target_not_sufficient_missing", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "response_target_not_sufficient_missing"
        )
        self.assertIn("generic chat routing", detail["missing"])
        self.assertIn("static thunk orientation", detail["missing"])

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

    def test_rejects_manifest_only_upstream_dependency_promotion(self) -> None:
        cases = (
            ("obelisk.player_identity.v1", "player_identity_evidence_not_approved"),
            ("obelisk.permissions_admin.v1", "permissions_admin_evidence_not_approved"),
        )
        for surface_id, blocker in cases:
            with self.subTest(surface_id=surface_id):
                surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
                for surface in surfaces["surfaces"]:
                    if surface["id"] == surface_id:
                        surface["status"] = "promoted"
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
                self.assertIn(blocker, report["blockers"])

    def test_rejects_promoted_surfaces_manifest_only_upstream_dependencies(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        surfaces["promoted_surfaces"].extend(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
            ]
        )
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
        self.assertIn("player_identity_manifest_promotion_without_evidence", report["blockers"])
        self.assertIn("permissions_admin_manifest_promotion_without_evidence", report["blockers"])

    def test_rejects_promoted_experimental_upstream_dependency_statuses(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        for surface in surfaces["surfaces"]:
            if surface["id"] in {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}:
                surface["status"] = "promoted-experimental-only"
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
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])


if __name__ == "__main__":
    unittest.main()
