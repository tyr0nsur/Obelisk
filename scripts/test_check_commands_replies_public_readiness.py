#!/usr/bin/env python3
"""Tests for check_commands_replies_public_readiness.py."""

from __future__ import annotations

import hashlib
import json
import importlib.util
import re
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
CERTIFICATE_TEMP_PARENT = REPO_ROOT / "tests" / "core"
CERTIFICATE_TEMP_PREFIX = "CommandsRepliesCert"
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

    def bind_certificate_artifact(self, root: Path, name: str, payload: dict) -> dict[str, str]:
        path = root / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def repo_artifact_binding(self, path: Path, schema: str) -> dict[str, str]:
        return {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "schema": schema,
        }

    def identity_contract_review_record(self, surface_hash: str) -> dict:
        response_readiness = READINESS.response_path_readiness
        record = {
            "schema": response_readiness.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
            "artifact_id": response_readiness.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
            "surface": READINESS.DEPENDENCY_CHAIN[0],
            "active_after_resolved_input": response_readiness.PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT,
            "review_status": "reviewed",
            "accepted_for_contract_review": True,
            "next_blocker": response_readiness.PUBLIC_HEADER_ROUTE_BLOCKER,
            "reviewed_surface_record_sha256": surface_hash,
            "resolved_decision_keys": list(
                response_readiness.REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS
            ),
        }
        for key in response_readiness.REQUIRED_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS:
            record[key] = False
        record.update(response_readiness.REQUIRED_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS)
        return record

    def mutate_bound_certificate_payload(self, binding: dict[str, str], updates: dict) -> None:
        path = REPO_ROOT / binding["path"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.update(updates)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    def inline_promotion_certificate(self, surface: dict, surface_id: str) -> dict:
        spec = READINESS.PROMOTION_CERTIFICATE_SPECS[surface_id]
        certificate_key = spec["certificate_key"]
        surface_hash = READINESS.surface_record_sha256(surface, certificate_key)
        evidence = {
            "reviewed_surface_record_sha256": surface_hash,
            "reviewed_artifact_hash": surface_hash,
        }
        if surface_id == READINESS.DEPENDENCY_CHAIN[0]:
            response_readiness = READINESS.response_path_readiness
            review = self.identity_contract_review_record(surface_hash)
            runtime_binding_digest = hashlib.sha256(
                b"unit-test-commands-replies-identity-runtime-binding"
            ).hexdigest()
            evidence.update(
                {
                    "promotion_evidence_kind": (
                        response_readiness.PLAYER_IDENTITY_CERTIFICATE_PROMOTION_EVIDENCE_KIND
                    ),
                    "approved_runtime_evidence": {
                        "schema": response_readiness.PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA,
                        "result": "approved runtime principal lifecycle evidence",
                        "next_blocker": READINESS.IDENTITY_CONTRACT_ROUTE_BLOCKER,
                    },
                    "identity_public_contract_decision_record": review,
                    "identity_public_contract_decision_record_sha256": (
                        response_readiness.canonical_json_sha256(review)
                    ),
                    "identity_public_contract_decision_record_runtime_binding": {
                        "schema": (
                            response_readiness.PLAYER_IDENTITY_DECISION_RUNTIME_BINDING_DIGEST_SCHEMA
                        ),
                        "policy": response_readiness.PLAYER_IDENTITY_DECISION_RUNTIME_BINDING_DIGEST_POLICY,
                        "decision_record_approved_runtime_evidence_binding_sha256": (
                            runtime_binding_digest
                        ),
                        "approved_runtime_evidence_binding_sha256": runtime_binding_digest,
                    },
                }
            )
        return {
            "schema": spec["schema"],
            "surface_id": surface_id,
            "promotion_status": "promoted",
            "v1_dependency_chain": list(READINESS.DEPENDENCY_CHAIN),
            "v1_dependency_chain_position": spec["chain_position"],
            "required_by_surface": spec["required_by_surface"],
            "required_by_v1_dependency_chain_position": spec["required_by_chain_position"],
            "required_reviewed_artifact_hash": READINESS.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH,
            "reviewed_artifact_hash_policy": (
                READINESS.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY
            ),
            "missing_mismatched_or_stale_certificate_counts": False,
            "evidence": evidence,
        }

    def promote_surface_with_certificate(self, root: Path, surfaces: dict, surface_id: str) -> dict:
        surface = next(item for item in surfaces["surfaces"] if item["id"] == surface_id)
        spec = READINESS.PROMOTION_CERTIFICATE_SPECS[surface_id]
        certificate_key = spec["certificate_key"]
        surface["status"] = "promoted"
        evidence = surface.setdefault("evidence", {})
        evidence.pop(certificate_key, None)
        certificate = self.inline_promotion_certificate(surface, surface_id)
        if surface_id == READINESS.DEPENDENCY_CHAIN[1]:
            identity_surface = next(
                (
                    item
                    for item in surfaces["surfaces"]
                    if item.get("id") == READINESS.DEPENDENCY_CHAIN[0]
                ),
                None,
            )
            identity_evidence = (
                identity_surface.get("evidence")
                if isinstance(identity_surface, dict)
                else None
            )
            identity_binding = (
                identity_evidence.get("player_identity_promotion_certificate")
                if isinstance(identity_evidence, dict)
                else None
            )
            if isinstance(identity_binding, dict):
                response_readiness = READINESS.response_path_readiness
                input_bindings = {
                    "public_sdk_surfaces": self.repo_artifact_binding(
                        SURFACES,
                        READINESS.SURFACES_SCHEMA,
                    ),
                    "permissions_admin_surface_record_sha256": (
                        READINESS.surface_record_sha256(surface, certificate_key)
                    ),
                    "player_identity_surface_record_sha256": (
                        READINESS.surface_record_sha256(
                            identity_surface,
                            "player_identity_promotion_certificate",
                        )
                    ),
                    "player_identity_promotion_certificate": deepcopy(identity_binding),
                    "permissions_admin_public_contract_decisions": self.repo_artifact_binding(
                        REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json",
                        response_readiness.PERMISSIONS_ADMIN_PUBLIC_CONTRACT_DECISIONS_SCHEMA,
                    ),
                    "permissions_admin_query_failclosed_contract": self.repo_artifact_binding(
                        REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json",
                        response_readiness.PERMISSIONS_ADMIN_QUERY_FAILCLOSED_CONTRACT_SCHEMA,
                    ),
                    "permissions_admin_public_readiness_report_sha256": "a" * 64,
                    "query_failclosed_contract_report_sha256": "b" * 64,
                }
                certificate["input_bindings"] = input_bindings
                certificate["evidence"]["input_binding_sha256"] = (
                    response_readiness.canonical_json_sha256(input_bindings)
                )
        if surface_id == READINESS.RESPONSE_PATH_SURFACE:
            for upstream_surface_id in (
                READINESS.DEPENDENCY_CHAIN[0],
                READINESS.DEPENDENCY_CHAIN[1],
            ):
                upstream_surface = next(
                    (
                        item
                        for item in surfaces["surfaces"]
                        if item.get("id") == upstream_surface_id
                    ),
                    None,
                )
                upstream_spec = READINESS.PROMOTION_CERTIFICATE_SPECS[upstream_surface_id]
                upstream_evidence = (
                    upstream_surface.get("evidence")
                    if isinstance(upstream_surface, dict)
                    else None
                )
                upstream_binding = (
                    upstream_evidence.get(upstream_spec["certificate_key"])
                    if isinstance(upstream_evidence, dict)
                    else None
                )
                if isinstance(upstream_binding, dict):
                    certificate.setdefault("input_bindings", {})[
                        upstream_spec["certificate_key"]
                    ] = deepcopy(upstream_binding)
        evidence[certificate_key] = self.bind_certificate_artifact(
            root,
            f"{certificate_key}.json",
            certificate,
        )
        if surface_id not in surfaces.get("promoted_surfaces", []):
            surfaces.setdefault("promoted_surfaces", []).append(surface_id)
        return surface

    def assert_public_runtime_v1_flags_false(self, report: dict) -> None:
        for key in (
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "public_or_runtime_accounting_allowed",
            "public_readiness_ready",
            "public_header_allowed",
            "public_abi_ready",
            "runtime_ready",
            "candidate_capture_counts_toward_public_sdk",
            "candidate_capture_counts_toward_runtime",
            "candidate_capture_counts_toward_v1_completion",
            "candidate_capture_counts_toward_complete_sdk_claim",
            "candidate_capture_counts_toward_p0_dependency_chain_claim",
            "candidate_capture_public_or_runtime_accounting_allowed",
            "command_support_ready",
            "accepted_runtime_evidence",
            "approved_runtime_evidence",
        ):
            self.assertFalse(report[key], key)
        self.assertEqual(0, report["candidate_capture_progress_contribution"])

    def make_surfaces_with_accepted_runtime_evidence(self) -> dict:
        surfaces = self.load_surfaces()
        for surface in surfaces["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["evidence"]["accepted_runtime_evidence"] = {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                    "result": "approved runtime principal lifecycle evidence",
                    "next_blocker": "identity_public_contract_gate_missing",
                    "approved_runtime_evidence_binding_required": True,
                    "approved_runtime_evidence_binding": {
                        "schema": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
                        "accepted_for_contract_review": True,
                        "resolved_input": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT,
                        "next_blocker": "identity_public_contract_gate_missing",
                        "binding_scope": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE,
                        "non_claim": (
                            "Fixture binding is route metadata only; it does not unlock public "
                            "header, public API/ABI/SDK, downstream P0, runtime readiness, or v1 completion."
                        ),
                        **{key: False for key in READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS},
                    },
                }
                surface["blockers"] = [
                    blocker
                    for blocker in surface["blockers"]
                    if blocker != "No approved runtime principal lifecycle evidence."
                ]
        return surfaces

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

    def write_response_report(
        self,
        root: Path,
        *,
        current_route_blocker: str = "approved_runtime_evidence_missing",
        surfaces_path: Path | None = None,
    ) -> Path:
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
        response_decisions_path = READINESS.response_path_readiness.DEFAULT_DECISIONS
        if current_route_blocker == "identity_public_contract_gate_missing":
            response_decisions = json.loads(response_decisions_path.read_text(encoding="utf-8"))
            accounting_lock = response_decisions.get("accounting_lock")
            if isinstance(accounting_lock, dict):
                accounting_lock["current_route_blocker"] = "identity_public_contract_gate_missing"
                accounting_lock["remaining_route_blockers"] = ["identity_public_contract_gate_missing"]
            response_decisions_path = root / "command_chat_response_public_contract_decisions.json"
            response_decisions_path.write_text(json.dumps(response_decisions), encoding="utf-8")
        response_report = READINESS.response_path_readiness.build_report(
            root,
            readiness_path,
            response_decisions_path,
            READINESS.response_path_readiness.DEFAULT_PUBLIC_HEADER,
            surfaces_path if surfaces_path is not None else READINESS.response_path_readiness.DEFAULT_SURFACES,
            current_route_blocker=current_route_blocker,
        )
        report_path = root / "command-chat-response-public-readiness.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
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
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ],
            report["blocked_behind_surfaces"],
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
                "obelisk.command-chat-response-path-promotion-certificate.v1",
            ],
            [
                item["certificate_schema"]
                for item in report["future_public_abi"]["requires"]
                if "certificate_schema" in item
            ],
        )
        self.assertIn(
            "isolated_runtime_command_dispatch_evidence",
            report["future_public_abi"]["requires"][-1]["required_evidence"],
        )
        self.assertEqual(
            "commands_replies_promotion_certificate",
            report["first_missing_terminal_artifact"],
        )
        self.assertEqual(
            "obelisk.commands-replies-promotion-certificate.v1",
            report["first_missing_terminal_artifact_schema"],
        )
        self.assertEqual(
            "command_response_promotion_certificate",
            report["first_missing_terminal_artifact_required_prior_certificate"],
        )
        self.assertFalse(report["terminal_artifact_shortcuts_count"])
        self.assertEqual(
            "commands_replies_promotion_certificate",
            report["terminal_promotion_required_artifact"]["certificate_key"],
        )
        self.assertEqual(
            "command_response_promotion_certificate",
            report["terminal_promotion_required_artifact"]["required_prior_certificate_key"],
        )
        self.assertFalse(
            report["terminal_promotion_required_artifact"][
                "package_shape_status_beta_offline_shortcuts_count"
            ]
        )
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertEqual("candidate_only_non_counting", report["candidate_capture_classification"])
        self.assertEqual(
            "candidate_only_non_counting",
            report["candidate_capture_guardrail"]["classification"],
        )
        self.assertEqual(
            "approved_runtime_evidence_missing",
            report["candidate_capture_guardrail"]["requires_player_principal_runtime_blocker"],
        )
        self.assertIn("commands/replies command candidates", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn(
            "chat/RCON/broadcast/send source alias probes",
            report["candidate_capture_guardrail"]["capture_inputs"],
        )
        self.assertIn("beta capture plans", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("passive logs", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("post-runtime planning metadata", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("response bridge candidates", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertFalse(report["candidate_capture_guardrail"]["counts_toward_public_sdk"])
        self.assertFalse(report["candidate_capture_guardrail"]["approved_runtime_evidence"])
        self.assertFalse(report["candidate_capture_guardrail"]["command_support_ready"])
        self.assertEqual(
            "produce_approved_runtime_principal_lifecycle_evidence",
            report["next_route_action"],
        )
        self.assertEqual(
            "approved_runtime_principal_lifecycle_evidence",
            report["next_route_blocked_until"],
        )
        self.assertEqual(
            "identity_public_contract_gate_missing",
            report["next_route_blocker_after_runtime_evidence"],
        )
        self.assertEqual("obelisk.command_chat_response_path.v1", report["next_required_surface"])
        self.assertEqual(
            {
                "surface": "obelisk.command_chat_response_path.v1",
                "schema": "obelisk.command-chat-response-path-promotion-certificate.v1",
                "promotion_status": "promoted",
                "v1_dependency_chain_position": 3,
                "required_by_surface": "obelisk.commands_replies.v1",
                "required_by_v1_dependency_chain_position": 4,
                "required_after": "obelisk.permissions_admin.v1",
                "non_counting_until_present": True,
            },
            report["next_required_artifact"],
        )
        self.assertEqual(
            "command_chat_response_path_promotion_certificate",
            report["command_response_promotion_gate"]["blocked_until"],
        )
        self.assertFalse(
            report["command_response_promotion_gate"][
                "commands_replies_can_advance_before_command_response_promotion"
            ]
        )
        self.assertEqual(
            READINESS.RESPONSE_PATH_REPORT_HANDOFF_REQUIREMENT,
            report["response_path_handoff_required"],
        )
        self.assertFalse(report["response_path_report_implicit_synthesis_allowed"])
        self.assertFalse(report["response_path_report_summary_shortcut_allowed"])
        diagnostic = report["post_command_response_blocker_diagnostic"]
        self.assertEqual(
            "obelisk.commands-replies-post-command-response-blocker-diagnostic.v1",
            diagnostic["schema"],
        )
        self.assertTrue(diagnostic["planning_only"])
        self.assertTrue(diagnostic["non_evidence"])
        self.assertTrue(diagnostic["non_authorizing"])
        self.assertEqual("obelisk.commands_replies.v1", diagnostic["surface"])
        self.assertEqual(
            "obelisk.command_chat_response_path.v1",
            diagnostic["requires_prior_surface"],
        )
        self.assertEqual(
            "obelisk.command-chat-response-path-promotion-certificate.v1",
            diagnostic["requires_prior_certificate_schema"],
        )
        self.assertEqual(
            "copied_command_payload_public_abi_contract",
            diagnostic["next_blocker_after_command_chat_response_path"],
        )
        self.assertEqual(
            "define_copied_command_payload_public_abi_contract",
            diagnostic["next_action_after_command_chat_response_path"],
        )
        self.assertIn(
            "copied_command_abi_layout_tests",
            diagnostic["required_test_artifacts_before_promotion"],
        )
        self.assertIn("public CallProcessEvent", diagnostic["forbidden_unlocks"])
        for key in (
            "accepted_for_evidence",
            "counts_as_evidence",
            "counts_toward_public_sdk",
            "counts_toward_p0_dependency_chain_claim",
            "public_reply_or_send_chat_abi_allowed",
            "public_send_chat_api_allowed",
            "public_broadcast_api_allowed",
            "public_notices_api_allowed",
            "public_call_process_event_allowed",
            "runtime_delivery_allowed",
            "stable_sdk_ready",
            "public_readiness_ready",
            "runtime_ready",
        ):
            self.assertFalse(diagnostic[key], key)
        self.assertEqual(
            "obelisk.commands-replies-downstream-chain-gate.v1",
            report["downstream_chain_gate"]["schema"],
        )
        self.assertEqual(
            [
                "promote_command_chat_response_path_first",
                "define_commands_replies_public_abi_after_response_path",
                "prove_commands_replies_runtime_dispatch_after_abi_contract",
                "issue_commands_replies_promotion_certificate",
            ],
            [item["id"] for item in report["downstream_blockers"]],
        )
        self.assertIn(
            "package_shape",
            report["downstream_chain_gate"]["non_counting_artifact_classes"],
        )
        self.assertIn(
            "status_report",
            report["downstream_chain_gate"]["non_counting_artifact_classes"],
        )
        self.assertIn(
            "post_runtime_planning_metadata",
            report["downstream_chain_gate"]["non_counting_artifact_classes"],
        )
        self.assertIn(
            "chat_rcon_broadcast_send_source_alias",
            report["downstream_chain_gate"]["non_counting_artifact_classes"],
        )
        self.assertIn(
            "isolated_runtime_command_dispatch_evidence",
            report["downstream_blockers"][2]["required_evidence"],
        )
        self.assertEqual(
            READINESS.POST_RESPONSE_ABI_EVIDENCE_GUARDRAIL,
            report["post_response_abi_evidence_guardrail"],
        )
        self.assertIn(
            "response/send/broadcast readiness aliases cannot count without valid upstream promotion certificates",
            report["post_response_abi_evidence_guardrail"]["required_fail_closed_guardrails"],
        )
        self.assertIn(
            "post-runtime planning metadata and chat/RCON/broadcast/send-source aliases cannot count without valid upstream promotion certificates",
            report["post_response_abi_evidence_guardrail"]["required_fail_closed_guardrails"],
        )
        self.assertIn(
            "current command_chat_response_path promotion certificate must be path-and-sha-bound to the current upstream surface record; stale/current surface-record mismatches fail closed",
            report["post_response_abi_evidence_guardrail"]["required_fail_closed_guardrails"],
        )
        self.assertFalse(report["post_response_abi_evidence_guardrail"]["certificate_metadata_counts_as_promotion"])
        self.assertFalse(report["post_response_abi_evidence_guardrail"]["response_send_broadcast_aliases_count_as_promotion"])
        for item in report["downstream_blockers"]:
            self.assertTrue(item["planning_metadata_only"])
            self.assertTrue(item["blocked"])
            self.assertFalse(item["satisfied"])
            self.assertFalse(item["counts_as_downstream_progress"])
            self.assertFalse(item["counts_toward_public_sdk"])
            self.assertFalse(item["counts_toward_runtime"])
            self.assertFalse(item["counts_toward_v1_completion"])
            self.assertEqual(0, item["downstream_progress_contribution"])
            self.assertIn("notice_bundle", item["artifact_classes_not_progress"])
        self.assertEqual(
            [
                "current_route_lock_next_action",
                "command_response_promotion_required_before_commands_replies",
                "commands_replies_promotion_package_after_response_path",
            ],
            [item["id"] for item in report["next_action_sequence"]],
        )
        for item in report["next_action_sequence"]:
            self.assertTrue(item["planning_metadata_only"])
            self.assertFalse(item["counts_toward_public_sdk"])
            self.assertFalse(item["counts_toward_runtime"])
            self.assertFalse(item["counts_toward_v1_completion"])
            self.assertFalse(item["counts_toward_p0_dependency_chain_claim"])
            self.assertEqual(0, item["p0_dependency_chain_claim_progress_contribution"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])
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

    def test_rejects_identity_contract_route_blocker_before_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_response_report(
                root,
                current_route_blocker="identity_public_contract_gate_missing",
            )
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
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("response_path_report_not_accepted_for_planning", report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertEqual("review_identity_public_contract_gate", report["next_route_action"])
        self.assertEqual("reviewed_identity_public_contract", report["next_route_blocked_until"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertFalse(report["public_response_path_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_accepts_identity_contract_route_blocker_after_runtime_evidence_without_unlocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            decisions = self.load_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            decisions_path, surfaces_path, header_path = self.write_inputs(
                root,
                decisions=decisions,
                surfaces=surfaces,
            )
            report_path = self.write_response_report(
                root,
                current_route_blocker="identity_public_contract_gate_missing",
                surfaces_path=surfaces_path,
            )
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual([], report["blockers"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ],
            report["blocked_behind_surfaces"],
        )
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["identity_public_contract_gate_missing_unlock_allowed"])
        self.assertEqual("obelisk.command_chat_response_path.v1", report["next_required_surface"])
        self.assertFalse(
            report["command_response_promotion_gate"][
                "commands_replies_can_advance_before_command_response_promotion"
            ]
        )
        self.assertEqual(
            [
                "promote_command_chat_response_path_first",
                "define_commands_replies_public_abi_after_response_path",
                "prove_commands_replies_runtime_dispatch_after_abi_contract",
                "issue_commands_replies_promotion_certificate",
            ],
            [item["id"] for item in report["downstream_blockers"]],
        )
        for item in report["downstream_blockers"]:
            self.assertTrue(item["planning_metadata_only"], item)
            self.assertTrue(item["blocked"], item)
            self.assertFalse(item["satisfied"], item)
            self.assertFalse(item["counts_toward_public_sdk"], item)
            self.assertFalse(item["counts_toward_runtime"], item)
            self.assertFalse(item["counts_toward_v1_completion"], item)
            self.assertEqual(0, item["downstream_progress_contribution"], item)
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertFalse(report["public_response_path_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_runtime_evidence_context_without_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            identity = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            identity["evidence"].pop("accepted_runtime_evidence", None)
            identity["evidence"]["accepted_runtime_evidence_context"] = {
                "status": "accepted",
                "next_blocker": "identity_public_contract_gate_missing",
            }
            decisions = self.load_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            decisions_path, surfaces_path, header_path = self.write_inputs(
                root,
                decisions=decisions,
                surfaces=surfaces,
            )
            report_path = self.write_response_report(
                root,
                current_route_blocker="identity_public_contract_gate_missing",
                surfaces_path=surfaces_path,
            )
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_bare_accepted_runtime_evidence_without_canonical_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            identity = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            accepted = identity["evidence"]["accepted_runtime_evidence"]
            accepted.pop("approved_runtime_evidence_binding_required", None)
            accepted.pop("approved_runtime_evidence_binding", None)
            decisions = self.load_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            decisions_path, surfaces_path, header_path = self.write_inputs(
                root,
                decisions=decisions,
                surfaces=surfaces,
            )
            report_path = self.write_response_report(
                root,
                current_route_blocker="identity_public_contract_gate_missing",
                surfaces_path=surfaces_path,
            )
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assertIn(
            "player_identity_accepted_runtime_evidence_binding_required_missing",
            report["blockers"],
        )
        self.assertIn(
            "player_identity_accepted_runtime_evidence_binding_missing_or_not_object",
            report["blockers"],
        )
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_runtime_evidence_alias_sources_as_parent_transition(self) -> None:
        alias_sources = (
            "approved_runtime_evidence_placeholder",
            "approved_runtime_placeholder",
            "passive_status",
            "beta_capture_pack",
            "beta_notice_state",
            "command_response_alias",
            "copied_log_status",
            "diagnostic_planning_artifact",
            "package_shape",
            "runtime_principal_lifecycle_start_end_evidence",
            "public_readiness",
        )
        for source in alias_sources:
            with self.subTest(source=source):
                surfaces = self.make_surfaces_with_accepted_runtime_evidence()
                identity = next(
                    surface
                    for surface in surfaces["surfaces"]
                    if surface["id"] == "obelisk.player_identity.v1"
                )
                identity["evidence"]["accepted_runtime_evidence"]["source"] = source
                blockers: list[dict] = []

                self.assertFalse(READINESS.player_identity_has_approved_runtime_evidence(identity))
                READINESS.validate_player_identity_accepted_runtime_evidence(
                    identity,
                    blockers,
                    label="$.surfaces.player_identity",
                )
                self.assertIn(
                    "player_identity_accepted_runtime_evidence_non_authorizing_context",
                    [blocker["reason"] for blocker in blockers],
                )

    def test_rejects_command_candidate_capture_route_blocker_bypass_without_player_principal_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            commands_surface = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.commands_replies.v1"
            )
            commands_surface.setdefault("evidence", {})["commands_replies_candidate_capture"] = {
                "status": "accepted",
                "current_route_blocker": "identity_public_contract_gate_missing",
                "claim": "command candidate unlocks public command router",
            }
            decisions = self.load_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            decisions_path, surfaces_path, header_path = self.write_inputs(
                root,
                decisions=decisions,
                surfaces=surfaces,
            )
            report_path = self.write_response_report(
                root,
                current_route_blocker="identity_public_contract_gate_missing",
                surfaces_path=surfaces_path,
            )
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assertIn("response_path_report_not_accepted_for_planning", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("non_evidence_artifact_credit_overclaim", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_identity_promotion_without_permissions_admin_promotion(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            decisions_path, surfaces_path, header_path = self.write_inputs(root, surfaces=surfaces)
            report_path = self.write_response_report(root, surfaces_path=surfaces_path)
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
            )

        self.assertFalse(report["valid"])
        self.assertIn("permissions_admin_dependency_not_promoted", report["blockers"])
        self.assertNotIn("player_identity_evidence_not_approved", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_permissions_admin_promotion_before_player_identity(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
            decisions_path, surfaces_path, header_path = self.write_inputs(root, surfaces=surfaces)
            report_path = self.write_response_report(root, surfaces_path=surfaces_path)
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
            )

        self.assertFalse(report["valid"])
        self.assertIn("permissions_admin_promoted_before_player_identity", report["blockers"])
        self.assertIn("response_path_report_not_accepted_for_planning", report["blockers"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_inline_promotion_certificate_without_hash_bound_artifact(self) -> None:
        expected_evidence_blockers = {
            "obelisk.player_identity.v1": "player_identity_evidence_not_approved",
            "obelisk.permissions_admin.v1": "permissions_admin_evidence_not_approved",
            "obelisk.command_chat_response_path.v1": "command_chat_response_evidence_not_approved",
        }
        for surface_id, spec in READINESS.PROMOTION_CERTIFICATE_SPECS.items():
            with self.subTest(surface_id=surface_id):
                surfaces = self.load_surfaces()
                surface = next(
                    item for item in surfaces["surfaces"] if item["id"] == surface_id
                )
                surface["status"] = "promoted"
                surface.setdefault("evidence", {})[spec["certificate_key"]] = (
                    self.inline_promotion_certificate(surface, surface_id)
                )

                blockers: list[dict[str, object]] = []
                READINESS.validate_surfaces(surfaces, blockers)

                reasons = [item["reason"] for item in blockers]
                self.assertIn(
                    f"{spec['certificate_key']}_inline_certificate_not_hash_bound",
                    reasons,
                )
                self.assertIn(expected_evidence_blockers[surface_id], reasons)

    def test_rejects_plain_inline_and_unbound_planning_promotion_certificate_metadata(self) -> None:
        def plain_status(surface: dict, surface_id: str, spec: dict) -> dict:
            return {"promotion_status": "promoted"}

        def inline_certificate(surface: dict, surface_id: str, spec: dict) -> dict:
            return self.inline_promotion_certificate(surface, surface_id)

        def path_only(surface: dict, surface_id: str, spec: dict) -> dict:
            return {"path": f"docs/{spec['certificate_key']}.json"}

        def sha_only(surface: dict, surface_id: str, spec: dict) -> dict:
            return {"sha256": "a" * 64}

        def missing_artifact_hash(surface: dict, surface_id: str, spec: dict) -> dict:
            return {
                "path": f"docs/{spec['certificate_key']}.missing.json",
                "sha256": "a" * 64,
            }

        cases = {
            "plain_status": plain_status,
            "inline_certificate": inline_certificate,
            "path_only": path_only,
            "sha_only": sha_only,
            "missing_artifact_hash": missing_artifact_hash,
        }
        for surface_id, spec in READINESS.PROMOTION_CERTIFICATE_SPECS.items():
            for case_name, make_metadata in cases.items():
                with self.subTest(surface_id=surface_id, case=case_name):
                    surfaces = self.load_surfaces()
                    surface_index, surface = next(
                        (index, item)
                        for index, item in enumerate(surfaces["surfaces"])
                        if item["id"] == surface_id
                    )
                    surface.setdefault("evidence", {})[spec["certificate_key"]] = make_metadata(
                        surface,
                        surface_id,
                        spec,
                    )

                    blockers: list[dict[str, object]] = []
                    READINESS.validate_surfaces(surfaces, blockers)

                    self.assertIn(
                        (
                            "promotion_certificate_metadata_missing_required_upstream_certificates",
                            f"$.surfaces.surfaces[{surface_index}].evidence.{spec['certificate_key']}",
                        ),
                        {(item["reason"], item["label"]) for item in blockers},
                    )

    def test_rejects_schema_only_and_builder_report_promotion_certificate_metadata(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "metadata": {
                    "plain_player_identity_promotion_certificate": (
                        READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
                    ),
                    "plain_permissions_admin_promotion_certificate": (
                        READINESS.PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA
                    ),
                    "plain_command_response_promotion_certificate": (
                        READINESS.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA
                    ),
                    "schema_only_player_identity_certificate": {
                        "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                    },
                    "schema_only_command_response_certificate": {
                        "schema": READINESS.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
                    },
                    "schema_only_commands_replies_certificate": {
                        "schema": READINESS.COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA,
                    },
                    "player_identity_certificate_builder_report": {
                        "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
                        "identity_surface_certificate_binding_valid": True,
                        "player_identity_promotion_certificate": {
                            "path": "docs/research/player-identity-promotion-certificate.json",
                            "sha256": "0" * 64,
                        },
                        "promotion_status": "promoted",
                        "sdk_progress": 1,
                    },
                    "command_response_certificate_builder_report": {
                        "schema": READINESS.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
                        "certificate_binding": {
                            "path": "docs/research/command-response-promotion-certificate.json",
                            "sha256": "0" * 64,
                        },
                        "promotion_status": "promoted",
                        "sdk_progress": 1,
                    },
                    "commands_replies_certificate_builder_report": {
                        "schema": READINESS.COMMANDS_REPLIES_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
                        "certificate_binding": {
                            "path": "docs/research/commands-replies-promotion-certificate.json",
                            "sha256": "0" * 64,
                        },
                        "promotion_status": "promoted",
                        "sdk_progress": 1,
                    },
                    "required_identity_promotion_certificate": {
                        "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                    },
                }
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.metadata.plain_player_identity_promotion_certificate",
            "$.metadata.plain_permissions_admin_promotion_certificate",
            "$.metadata.plain_command_response_promotion_certificate",
            "$.metadata.schema_only_player_identity_certificate",
            "$.metadata.schema_only_command_response_certificate",
            "$.metadata.schema_only_commands_replies_certificate",
            "$.metadata.player_identity_certificate_builder_report",
            "$.metadata.command_response_certificate_builder_report",
            "$.metadata.commands_replies_certificate_builder_report",
        ):
            with self.subTest(label=label):
                self.assertIn(
                    (
                        "promotion_certificate_metadata_missing_required_upstream_certificates",
                        label,
                    ),
                    paths,
                )
        self.assertNotIn(
            (
                "promotion_certificate_metadata_missing_required_upstream_certificates",
                "$.metadata.required_identity_promotion_certificate",
            ),
            paths,
        )

    def test_accepts_hash_bound_planning_promotion_certificate_binding_shape_as_metadata(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            for surface_id, spec in READINESS.PROMOTION_CERTIFICATE_SPECS.items():
                with self.subTest(surface_id=surface_id):
                    surfaces = self.load_surfaces()
                    surface = next(
                        item for item in surfaces["surfaces"] if item["id"] == surface_id
                    )
                    surface.setdefault("evidence", {})[spec["certificate_key"]] = (
                        self.bind_certificate_artifact(
                            root,
                            f"{spec['certificate_key']}-planning.json",
                            {
                                "schema": spec["schema"],
                                "surface_id": surface_id,
                                "promotion_status": "promoted",
                            },
                        )
                    )

                    blockers: list[dict[str, object]] = []
                    READINESS.validate_surfaces(surfaces, blockers)

                    self.assertNotIn(
                        "promotion_certificate_metadata_missing_required_upstream_certificates",
                        [item["reason"] for item in blockers],
                    )

    def test_rejects_upstream_certificate_binding_paths_and_extra_alias_fields(self) -> None:
        cases = (
            ("absolute_path", lambda binding: str((REPO_ROOT / binding["path"]).resolve()), "command_response_promotion_certificate_path_invalid"),
            ("parent_relative_path", lambda binding: f"../{binding['path']}", "command_response_promotion_certificate_path_invalid"),
            ("extra_status", None, "command_response_promotion_certificate_binding_keys_mismatch"),
        )
        for case_name, path_value, expected_reason in cases:
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory(
                    dir=CERTIFICATE_TEMP_PARENT,
                    prefix=CERTIFICATE_TEMP_PREFIX,
                ) as temp_dir:
                    root = Path(temp_dir)
                    surfaces = self.load_surfaces()
                    self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
                    self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
                    response = self.promote_surface_with_certificate(
                        root,
                        surfaces,
                        "obelisk.command_chat_response_path.v1",
                    )
                    binding = response["evidence"]["command_response_promotion_certificate"]
                    if path_value is None:
                        binding["status"] = "ready"
                    else:
                        binding["path"] = path_value(binding)

                    blockers: list[dict[str, object]] = []
                    READINESS.validate_surfaces(surfaces, blockers)

                reasons = [item["reason"] for item in blockers]
                self.assertIn(expected_reason, reasons)
                self.assertIn("command_chat_response_evidence_not_approved", reasons)

    def test_rejects_hash_bound_upstream_certificate_payload_builder_report(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
            response = self.promote_surface_with_certificate(
                root,
                surfaces,
                "obelisk.command_chat_response_path.v1",
            )
            binding = response["evidence"]["command_response_promotion_certificate"]
            self.mutate_bound_certificate_payload(
                binding,
                {
                    "certificate_builder_report": {
                        "schema": READINESS.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
                        "certificate_written": True,
                        "certificate_binding": deepcopy(binding),
                    }
                },
            )

            blockers: list[dict[str, object]] = []
            READINESS.validate_surfaces(surfaces, blockers)

        reasons = [item["reason"] for item in blockers]
        self.assertIn(
            "command_response_promotion_certificate_builder_report_not_certificate",
            reasons,
        )
        self.assertIn("command_chat_response_evidence_not_approved", reasons)

    def test_rejects_hash_bound_upstream_certificate_payload_status_beta_and_header_aliases(self) -> None:
        cases = (
            "status_report_ready",
            "beta_capture_pack_ready",
            "public_header_allowed",
        )
        for alias_key in cases:
            with self.subTest(alias_key=alias_key):
                with tempfile.TemporaryDirectory(
                    dir=CERTIFICATE_TEMP_PARENT,
                    prefix=CERTIFICATE_TEMP_PREFIX,
                ) as temp_dir:
                    root = Path(temp_dir)
                    surfaces = self.load_surfaces()
                    self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
                    self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
                    response = self.promote_surface_with_certificate(
                        root,
                        surfaces,
                        "obelisk.command_chat_response_path.v1",
                    )
                    binding = response["evidence"]["command_response_promotion_certificate"]
                    self.mutate_bound_certificate_payload(binding, {alias_key: True})

                    blockers: list[dict[str, object]] = []
                    READINESS.validate_surfaces(surfaces, blockers)

                reasons = [item["reason"] for item in blockers]
                self.assertIn(
                    "command_response_promotion_certificate_payload_public_surface_overclaim",
                    reasons,
                )
                self.assertIn("command_chat_response_evidence_not_approved", reasons)

    def test_rejects_commands_replies_direct_upstream_certificate_shortcuts(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            commands = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.commands_replies.v1"
            )
            evidence = commands.setdefault("evidence", {})
            evidence["player_identity_promotion_certificate"] = self.bind_certificate_artifact(
                root,
                "direct-player-identity-promotion-certificate.json",
                {
                    "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                },
            )
            evidence["permissions_admin_promotion_certificate"] = self.bind_certificate_artifact(
                root,
                "direct-permissions-admin-promotion-certificate.json",
                {
                    "schema": READINESS.PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
                    "surface_id": "obelisk.permissions_admin.v1",
                    "promotion_status": "promoted",
                },
            )
            evidence["promotion_certificate_builder_report"] = {
                "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA,
                "identity_surface_certificate_binding_valid": True,
                "player_identity_promotion_certificate": evidence[
                    "player_identity_promotion_certificate"
                ],
                "promotion_status": "promoted",
            }

            blockers: list[dict[str, object]] = []
            READINESS.validate_surfaces(surfaces, blockers)

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(
            (
                "commands_replies_direct_player_identity_promotion_certificate_shortcut",
                "$.surfaces.surfaces[commands_replies].evidence.player_identity_promotion_certificate",
            ),
            paths,
        )
        self.assertIn(
            (
                "commands_replies_permissions_admin_certificate_without_command_response_certificate",
                "$.surfaces.surfaces[commands_replies].evidence.permissions_admin_promotion_certificate",
            ),
            paths,
        )
        self.assertTrue(
            any(
                reason == "promotion_certificate_metadata_missing_required_upstream_certificates"
                and label.endswith(".evidence.promotion_certificate_builder_report")
                for reason, label in paths
            ),
            paths,
        )

    def test_rejects_commands_replies_terminal_certificate_binding_as_non_counting_metadata(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            commands = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.commands_replies.v1"
            )
            commands.setdefault("evidence", {})["commands_replies_promotion_certificate"] = (
                self.bind_certificate_artifact(
                    root,
                    "commands-replies-terminal-certificate.json",
                    {
                        "schema": READINESS.COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA,
                        "surface_id": READINESS.SURFACE,
                        "promotion_status": "promoted",
                        "status_report_ready": True,
                        "evidence": {
                            "runtime_window_ready": True,
                            "package_shape_artifact": {
                                "artifact_class": "package_shape",
                                "status": "ready",
                            },
                        },
                    },
                )
            )

            blockers: list[dict[str, object]] = []
            READINESS.validate_surfaces(surfaces, blockers)

        reasons = [item["reason"] for item in blockers]
        self.assertIn(
            "commands_replies_promotion_certificate_terminal_artifact_non_counting",
            reasons,
        )
        self.assertIn(
            "commands_replies_promotion_certificate_payload_public_surface_overclaim",
            reasons,
        )
        self.assertIn(
            "commands_replies_promotion_certificate_payload_non_evidence_artifact_credit_overclaim",
            reasons,
        )

    def test_accepts_promoted_identity_and_permissions_without_unlocking_commands_replies(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
            decisions_path, surfaces_path, header_path = self.write_inputs(root, surfaces=surfaces)
            report_path = self.write_response_report(root, surfaces_path=surfaces_path)
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
            )

        self.assertTrue(report["valid"])
        self.assertEqual([], report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_player_identity_runtime_evidence_alias_that_skips_identity_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            identity = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            identity["evidence"]["accepted_runtime_evidence"]["acceptedRuntimeEvidenceReady"] = True
            identity["evidence"]["accepted_runtime_evidence"]["claim"] = (
                "accepted runtime evidence unlocks commands/replies"
            )
            decisions = self.load_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            decisions_path, surfaces_path, header_path = self.write_inputs(
                root,
                decisions=decisions,
                surfaces=surfaces,
            )
            report_path = self.write_response_report(
                root,
                current_route_blocker="identity_public_contract_gate_missing",
                surfaces_path=surfaces_path,
            )
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertIn(
            "player_identity_accepted_runtime_evidence_alias_skips_identity_public_contract_gate",
            report["blockers"],
        )
        self.assertFalse(report["counts_toward_public_sdk"])

    def test_rejects_player_identity_runtime_evidence_child_pass_supplied_surface_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            identity = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            accepted_runtime_evidence = identity["evidence"]["accepted_runtime_evidence"]
            accepted_runtime_evidence["childPass"] = True
            accepted_runtime_evidence["supplied_surfaces"] = [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
            ]
            accepted_runtime_evidence["note"] = (
                "supplied surfaces readiness passes the identity public contract gate"
            )
            decisions = self.load_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            decisions_path, surfaces_path, header_path = self.write_inputs(
                root,
                decisions=decisions,
                surfaces=surfaces,
            )
            report_path = self.write_response_report(
                root,
                current_route_blocker="identity_public_contract_gate_missing",
                surfaces_path=surfaces_path,
            )
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertIn(
            "player_identity_accepted_runtime_evidence_alias_skips_identity_public_contract_gate",
            report["blockers"],
        )
        self.assertIn(
            "player_identity_accepted_runtime_evidence_non_authorizing_context",
            report["blockers"],
        )
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_stale_runtime_route_after_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            decisions_path, surfaces_path, header_path = self.write_inputs(root, surfaces=surfaces)
            report_path = self.write_response_report(root, surfaces_path=surfaces_path)
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("current_route_blocker_stale_after_approved_runtime_evidence", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_stale_after_approved_runtime_evidence", report["blockers"])
        self.assertIn(
            "accounting_lock_remaining_route_blocker_stale_after_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertFalse(report["public_response_path_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_accepts_post_runtime_identity_parent_lock_with_persisted_runtime_decision_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            decisions_path, surfaces_path, header_path = self.write_inputs(root, surfaces=surfaces)
            report_path = self.write_response_report(
                root,
                current_route_blocker="identity_public_contract_gate_missing",
                surfaces_path=surfaces_path,
            )
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual([], report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ],
            report["blocked_behind_surfaces"],
        )
        self.assertFalse(report["identity_public_contract_gate_missing_unlock_allowed"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertFalse(report["public_response_path_allowed"])
        self.assertFalse(
            report["command_response_promotion_gate"][
                "commands_replies_can_advance_before_command_response_promotion"
            ]
        )
        self.assertEqual(
            [
                "promote_command_chat_response_path_first",
                "define_commands_replies_public_abi_after_response_path",
                "prove_commands_replies_runtime_dispatch_after_abi_contract",
                "issue_commands_replies_promotion_certificate",
            ],
            [item["id"] for item in report["downstream_blockers"]],
        )
        self.assertEqual(
            "identity_public_contract_gate_missing",
            report["candidate_capture_guardrail"]["current_route_blocker"],
        )
        self.assertFalse(report["candidate_capture_guardrail"]["approved_runtime_evidence"])
        self.assertFalse(report["candidate_capture_guardrail"]["command_support_ready"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_accounting_lock_identity_route_before_runtime_evidence(self) -> None:
        decisions = self.load_decisions()
        decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
        decisions["accounting_lock"]["remaining_route_blockers"] = ["identity_public_contract_gate_missing"]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decisions_path, surfaces_path, header_path = self.write_inputs(root, decisions=decisions)
            report_path = self.write_response_report(root)
            report = READINESS.build_report(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                public_header_path=header_path,
                response_path_report_path=report_path,
                response_path_root=root,
                response_path_readiness=root / "command-chat-response-route-planning-readiness.json",
                response_path_report_root=root,
            )

        self.assertFalse(report["valid"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_remaining_route_blocker_out_of_order", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
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

    def test_blocker_container_does_not_hide_positive_command_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "blockers": [
                    "command router is ready",
                    "send-chat API ready remains blocked",
                ],
                "promotion_requires": [
                    "command router must be promoted before release",
                ],
            },
            blockers,
        )

        self.assertEqual(
            [("positive_public_surface_claim", "$.blockers[0]")],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_nested_route_readiness_and_runtime_authorization_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "acceptedRuntimeEvidenceReady": True,
                    "broadcastReady": True,
                    "commandRouteReady": True,
                    "commandsUnlocked": True,
                    "moderationReady": True,
                    "permissionsAdminRouteReady": True,
                    "publicBridgeAbiAllowed": True,
                    "publicHeaderReady": True,
                    "publicReplyAbiReady": True,
                    "publicResponseAbiAllowed": True,
                    "publicResponsePathReady": True,
                    "publicSdk": True,
                    "replyPathReady": True,
                    "responseHeaderAllowed": True,
                    "runtimeApproval": True,
                    "runtimeApprovalGranted": True,
                    "runtimeWorkAuthorized": True,
                    "sendChatReady": True,
                    "serverOperationsAuthorized": True,
                }
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.secondary_report.acceptedRuntimeEvidenceReady"),
                ("public_surface_overclaim", "$.secondary_report.broadcastReady"),
                ("public_surface_overclaim", "$.secondary_report.commandRouteReady"),
                ("public_surface_overclaim", "$.secondary_report.commandsUnlocked"),
                ("public_surface_overclaim", "$.secondary_report.moderationReady"),
                ("public_surface_overclaim", "$.secondary_report.permissionsAdminRouteReady"),
                ("public_surface_overclaim", "$.secondary_report.publicBridgeAbiAllowed"),
                ("public_surface_overclaim", "$.secondary_report.publicHeaderReady"),
                ("public_surface_overclaim", "$.secondary_report.publicReplyAbiReady"),
                ("public_surface_overclaim", "$.secondary_report.publicResponseAbiAllowed"),
                ("public_surface_overclaim", "$.secondary_report.publicResponsePathReady"),
                (
                    "route_or_runtime_readiness_alias_missing_upstream_certificates",
                    "$.secondary_report.publicResponsePathReady",
                ),
                ("public_surface_overclaim", "$.secondary_report.publicSdk"),
                ("public_surface_overclaim", "$.secondary_report.replyPathReady"),
                (
                    "route_or_runtime_readiness_alias_missing_upstream_certificates",
                    "$.secondary_report.replyPathReady",
                ),
                ("public_surface_overclaim", "$.secondary_report.responseHeaderAllowed"),
                ("public_surface_overclaim", "$.secondary_report.runtimeApproval"),
                ("public_surface_overclaim", "$.secondary_report.runtimeApprovalGranted"),
                ("public_surface_overclaim", "$.secondary_report.runtimeWorkAuthorized"),
                ("public_surface_overclaim", "$.secondary_report.sendChatReady"),
                ("public_surface_overclaim", "$.secondary_report.serverOperationsAuthorized"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_downstream_identity_permission_capability_and_route_gate_claims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "adminAuthorityReady": True,
                    "identityPublicContractReviewed": True,
                    "permissionHeaderAllowed": True,
                    "permissionsQueryReady": True,
                    "playerIdentityPromotionCertificateReady": True,
                    "publicCapabilityAdvertised": True,
                    "publicContractReady": True,
                    "routeGateUnlocked": True,
                },
                "claims": [
                    "accepted runtime evidence is accepted",
                    "identity public contract is reviewed",
                    "permission header allowed",
                    "permissions query ready",
                    "public ABI is ready",
                    "public capability is advertised",
                    "route gate opened for commands/replies",
                    "ready route gate",
                ],
            },
            blockers,
        )

        reasons = [item["reason"] for item in blockers]
        self.assertEqual(8, reasons.count("public_surface_overclaim"))
        self.assertEqual(8, reasons.count("positive_public_surface_claim"))

    def test_rejects_reviewed_identity_contract_and_runtime_evidence_key_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "reviewedIdentityPublicContract": True,
                    "reviewedIdentityPublicContractReady": True,
                    "reviewedPlayerIdentityPublicContractReady": True,
                    "identityPublicContractGatePassed": True,
                    "identityPublicContractGateResolved": True,
                    "playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin": True,
                    "playerIdentityEvidenceAccepted": True,
                    "identityContractReviewComplete": True,
                },
                "split_claims": [
                    {"field": "reviewedIdentityPublicContractReady", "state": "reviewed"},
                    {"claim": "identityPublicContractGatePassed", "value": "passed"},
                    {"name": "playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin", "enabled": "yes"},
                ],
                "notes": [
                    "reviewed identity public contract unlocks commands/replies",
                    "identity public contract gate passed so replies are ready",
                    "player identity runtime evidence unlocks permissions/admin",
                    "accepted runtime evidence remains normalized only to identity_public_contract_gate_missing",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.reviewedIdentityPublicContract",
            "$.aliases.reviewedIdentityPublicContractReady",
            "$.aliases.reviewedPlayerIdentityPublicContractReady",
            "$.aliases.identityPublicContractGatePassed",
            "$.aliases.identityPublicContractGateResolved",
            "$.aliases.playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin",
            "$.aliases.playerIdentityEvidenceAccepted",
            "$.aliases.identityContractReviewComplete",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.aliases.reviewedIdentityPublicContract",
            "$.aliases.reviewedIdentityPublicContractReady",
            "$.aliases.reviewedPlayerIdentityPublicContractReady",
            "$.aliases.identityPublicContractGatePassed",
            "$.aliases.identityPublicContractGateResolved",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.notes[0]",
            "$.notes[1]",
        ):
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(3):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[3]"), paths)

    def test_rejects_broad_accept_promote_and_progress_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "commandsRepliesAccepted": True,
                    "commandsRepliesPromoted": {"status": "ready"},
                    "commandParserPromoted": True,
                    "commandResponseAccepted": True,
                    "sendChatPromoted": "ready",
                    "routePromoted": True,
                    "publicRuntimeReadinessPromoted": True,
                    "v1CompletionProgressContribution": "25%",
                    "p0DependencyChainProgressContribution": 1,
                    "promotedSurfaceTotal": 1,
                    "promoted_surfaces_total": "1/4",
                    "surfacePromotionTotal": 1,
                    "promotedSurfaceTotalZero": "0/4",
                    "progress": "1/2",
                    "runtimeEvidenceReady": True,
                },
                "split_claims": [
                    {"field": "commandsRepliesAccepted", "status": "accepted"},
                    {"name": "commandParserPromoted", "value": {"state": "ready"}},
                    {"key": "v1CompletionProgress", "value": "10%"},
                    {"field": "commandResponseAccepted", "status": "blocked"},
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.secondary_report.commandsRepliesAccepted",
            "$.secondary_report.commandsRepliesPromoted",
            "$.secondary_report.commandParserPromoted",
            "$.secondary_report.commandResponseAccepted",
            "$.secondary_report.sendChatPromoted",
            "$.secondary_report.routePromoted",
            "$.secondary_report.publicRuntimeReadinessPromoted",
            "$.secondary_report.v1CompletionProgressContribution",
            "$.secondary_report.p0DependencyChainProgressContribution",
            "$.secondary_report.promotedSurfaceTotal",
            "$.secondary_report.promoted_surfaces_total",
            "$.secondary_report.surfacePromotionTotal",
            "$.secondary_report.progress",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        self.assertNotIn(("public_surface_overclaim", "$.secondary_report.promotedSurfaceTotalZero"), paths)
        self.assertNotIn(("public_surface_overclaim", "$.secondary_report.runtimeEvidenceReady"), paths)
        self.assertNotIn(("public_surface_overclaim", "$.split_claims[3]"), paths)

    def test_rejects_next_action_passive_notice_and_status_shortcut_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "nextActionReady": True,
                    "machineNextActionCompleted": True,
                    "nextActionSequenceProgressReady": True,
                    "passiveStatusReady": True,
                    "noticeStatusReady": True,
                    "statusReportReady": True,
                    "statusSnapshotAccepted": True,
                    "statusUpdateReady": True,
                },
                "next_action_sequence": {"status": "completed"},
                "status_report": {"status": "ready", "progress": "1/4"},
                "split_claims": [
                    {"field": "next_action_ready", "status": "ready"},
                    {"name": "status_report_counts_toward_p0", "value": 1},
                ],
                "claims": [
                    "next action completed makes commands/replies ready",
                    "status report accepted counts toward P0 progress",
                    "passive status is ready for public send-chat API",
                    "notice status sent unlocks replies",
                    "next action metadata remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.nextActionReady",
            "$.aliases.machineNextActionCompleted",
            "$.aliases.nextActionSequenceProgressReady",
            "$.aliases.passiveStatusReady",
            "$.aliases.noticeStatusReady",
            "$.aliases.statusReportReady",
            "$.aliases.statusSnapshotAccepted",
            "$.aliases.statusUpdateReady",
            "$.next_action_sequence",
            "$.status_report",
            "$.status_report.progress",
            "$.split_claims[0]",
            "$.split_claims[1]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.aliases.nextActionReady",
            "$.aliases.passiveStatusReady",
            "$.aliases.noticeStatusReady",
            "$.aliases.statusReportReady",
            "$.split_claims[0]",
        ):
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(4):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[4]"), paths)

    def test_rejects_runtime_window_artifacts_and_reply_send_broadcast_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "runtimeWindowReady": True,
                    "replySendBroadcastReady": True,
                    "replySendBroadcastAliasReady": True,
                    "responseSendBroadcastReady": True,
                    "publicReplySendBroadcastReady": True,
                },
                "runtime_window_manifest": {"status": "ready"},
                "window_report": {"progress": "1/2"},
                "window_status": {"result": "accepted"},
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.runtimeWindowReady",
            "$.aliases.replySendBroadcastReady",
            "$.aliases.replySendBroadcastAliasReady",
            "$.aliases.responseSendBroadcastReady",
            "$.aliases.publicReplySendBroadcastReady",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.runtime_window_manifest.status",
            "$.window_report.progress",
            "$.window_status.result",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)

    def test_rejects_beta_plan_passive_log_and_command_candidate_positive_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "beta_capture_plan": {"progress": "1/2"},
                "passive_runtime_log": {"status": "accepted"},
                "commands_replies_candidate": {"readiness": "ready"},
                "debug_capture": {
                    "claim": "commands_replies_candidate",
                    "status": "accepted",
                },
                "claims": [
                    "beta capture plan makes commands/replies ready",
                    "passive log accepted counts toward SDK/P0 progress",
                    "command candidate capture unlocks public command router",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.beta_capture_plan.progress"), paths)
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.passive_runtime_log.status"), paths)
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.commands_replies_candidate.readiness"), paths)
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.debug_capture"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[0]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[1]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[2]"), paths)

    def test_rejects_diagnostic_copied_placeholder_beta_and_command_response_alias_credit(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "diagnostic_planning_artifact": {"status": "ready"},
                "copied_log_status": {"status": "ready", "progress": "1/4"},
                "approved_runtime_placeholder": {"status": "approved"},
                "approved_runtime_evidence_placeholder": {"state": "ready"},
                "beta_notice_state": {"state": "sent"},
                "command_response_alias": {"status": "ready"},
                "command_chat_response_alias": {"ready": True},
                "split_claims": [
                    {"field": "copiedLogStatusReady", "status": "ready"},
                    {"name": "approvedRuntimePlaceholder", "value": "approved"},
                    {"claim": "command_response_alias", "status": "ready"},
                ],
                "claims": [
                    "diagnostic planning artifact is ready for command replies",
                    "copied-log status counts toward P0 progress",
                    "approved-runtime placeholder is sufficient for commands/replies readiness",
                    "beta notice state sent unlocks replies",
                    "command response alias makes send-chat ready",
                    "command response alias remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.diagnostic_planning_artifact",
            "$.diagnostic_planning_artifact.status",
            "$.copied_log_status",
            "$.copied_log_status.status",
            "$.copied_log_status.progress",
            "$.approved_runtime_placeholder",
            "$.approved_runtime_placeholder.status",
            "$.approved_runtime_evidence_placeholder",
            "$.approved_runtime_evidence_placeholder.state",
            "$.beta_notice_state",
            "$.beta_notice_state.state",
            "$.command_response_alias",
            "$.command_response_alias.status",
            "$.command_chat_response_alias",
            "$.command_chat_response_alias.ready",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        for label in (
            "$.diagnostic_planning_artifact",
            "$.copied_log_status",
            "$.approved_runtime_placeholder",
            "$.approved_runtime_evidence_placeholder",
            "$.beta_notice_state",
            "$.command_response_alias",
            "$.command_chat_response_alias",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(5):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", f"$.claims[{index}]"),
                paths,
            )
        self.assertNotIn(("positive_public_surface_claim", "$.claims[5]"), paths)

    def test_rejects_non_evidence_artifact_metadata_credit(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "metadata": {
                    "package": {"artifact_class": "package_shape", "status": "ready"},
                    "beta": {"source_kind": "beta_notice", "counts_toward_runtime": True},
                    "passive": {"kind": "passive_monitor", "progress": "1/4"},
                    "no_users": {"artifact_type": "no-users status", "state": "supported"},
                    "diagnostic": {"report_kind": "diagnostic candidate", "readiness": "accepted"},
                    "post_runtime": {"artifact_kind": "post_runtime_planning_metadata", "status": "ready"},
                    "source_alias": {"source": "chat/RCON/broadcast/send-source alias", "status": "ready"},
                    "non_evidence_artifacts": [
                        {"artifact_class": "passive_monitor", "status": False}
                    ],
                }
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.metadata.package.status",
            "$.metadata.beta.counts_toward_runtime",
            "$.metadata.passive.progress",
            "$.metadata.no_users.state",
            "$.metadata.diagnostic.readiness",
            "$.metadata.post_runtime.status",
            "$.metadata.source_alias.status",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertNotIn(
            ("non_evidence_artifact_credit_overclaim", "$.metadata.non_evidence_artifacts[0].status"),
            paths,
        )

    def test_rejects_missing_response_path_report(self) -> None:
        result = self.run_checker("--json", check=False)
        report = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_required", report["blockers"])
        self.assertIsNone(report["response_path_report_path"])
        self.assertFalse(report["response_path_report_implicit_synthesis_allowed"])
        self.assertFalse(report["response_path_report_summary_shortcut_allowed"])

    def test_rejects_summary_response_path_report_as_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_summary_response_report(root)
            result = self.run_checker(
                *self.response_path_args(report_path, root),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_source_artifacts_missing", report["blockers"])
        self.assertIn("response_path_report_not_revalidatable_handoff", report["blockers"])
        self.assertIn("response_path_report_source_artifact_hashes_missing", report["blockers"])
        self.assertFalse(report["response_path_report_implicit_synthesis_allowed"])
        self.assertFalse(report["response_path_report_summary_shortcut_allowed"])

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

    def test_rejects_command_response_promotion_without_current_identity_and_permissions(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(
                root,
                surfaces,
                "obelisk.command_chat_response_path.v1",
            )

            blockers: list[dict[str, object]] = []
            READINESS.validate_surfaces(surfaces, blockers)

        reasons = [item["reason"] for item in blockers]
        self.assertIn("command_chat_response_evidence_not_approved", reasons)
        self.assertIn("command_chat_response_promoted_before_player_identity", reasons)
        self.assertIn("command_chat_response_promoted_before_permissions_admin", reasons)

    def test_accepts_valid_command_response_promotion_certificate_as_prerequisite_metadata(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
            self.promote_surface_with_certificate(root, surfaces, "obelisk.command_chat_response_path.v1")

            blockers: list[dict[str, object]] = []
            READINESS.validate_surfaces(surfaces, blockers)

        reasons = [item["reason"] for item in blockers]
        self.assertNotIn("command_chat_response_evidence_not_approved", reasons)
        self.assertNotIn("response_path_planning_evidence_treated_as_promoted", reasons)
        self.assertNotIn("command_chat_response_manifest_promotion_without_evidence", reasons)
        self.assertEqual([], reasons)

    def test_rejects_hash_bound_upstream_certificates_missing_current_internals(self) -> None:
        cases = (
            (
                "identity_runtime_evidence",
                "obelisk.player_identity.v1",
                ["obelisk.player_identity.v1"],
                "player_identity_promotion_certificate",
                lambda certificate: certificate["evidence"].pop(
                    "approved_runtime_evidence",
                    None,
                ),
                "player_identity_promotion_certificate_approved_runtime_evidence_mismatch",
                "player_identity_evidence_not_approved",
            ),
            (
                "permissions_input_bindings",
                "obelisk.permissions_admin.v1",
                ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"],
                "permissions_admin_promotion_certificate",
                lambda certificate: certificate["input_bindings"].pop(
                    "permissions_admin_query_failclosed_contract",
                    None,
                ),
                "permissions_admin_promotion_certificate_input_bindings_keys_mismatch",
                "permissions_admin_evidence_not_approved",
            ),
        )
        for (
            case_name,
            target_surface_id,
            chain,
            certificate_key,
            mutate,
            expected_reason,
            evidence_reason,
        ) in cases:
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory(
                    dir=CERTIFICATE_TEMP_PARENT,
                    prefix=CERTIFICATE_TEMP_PREFIX,
                ) as temp_dir:
                    root = Path(temp_dir)
                    surfaces = self.load_surfaces()
                    for promoted_surface_id in chain:
                        self.promote_surface_with_certificate(
                            root,
                            surfaces,
                            promoted_surface_id,
                        )
                    surface = next(
                        item
                        for item in surfaces["surfaces"]
                        if item["id"] == target_surface_id
                    )
                    binding = surface["evidence"][certificate_key]
                    certificate_path = REPO_ROOT / binding["path"]
                    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
                    mutate(certificate)
                    certificate_path.write_text(
                        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    binding["sha256"] = hashlib.sha256(certificate_path.read_bytes()).hexdigest()

                    blockers: list[dict[str, object]] = []
                    READINESS.validate_surfaces(surfaces, blockers)

                reasons = [item["reason"] for item in blockers]
                self.assertIn(expected_reason, reasons)
                self.assertIn(evidence_reason, reasons)

    def test_rejects_upstream_certificate_not_bound_to_current_prior_certificate(self) -> None:
        cases = (
            (
                "permissions_admin_identity",
                ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"],
                "obelisk.permissions_admin.v1",
                "permissions_admin_promotion_certificate",
                "player_identity_promotion_certificate",
                "permissions_admin_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
                "permissions_admin_evidence_not_approved",
            ),
            (
                "command_response_permissions",
                [
                    "obelisk.player_identity.v1",
                    "obelisk.permissions_admin.v1",
                    "obelisk.command_chat_response_path.v1",
                ],
                "obelisk.command_chat_response_path.v1",
                "command_response_promotion_certificate",
                "permissions_admin_promotion_certificate",
                "command_response_promotion_certificate_current_permissions_admin_certificate_binding_missing_or_mismatch",
                "command_chat_response_evidence_not_approved",
            ),
        )
        for case_name, chain, target_surface_id, certificate_key, stale_binding_key, expected_reason, evidence_reason in cases:
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory(
                    dir=CERTIFICATE_TEMP_PARENT,
                    prefix=CERTIFICATE_TEMP_PREFIX,
                ) as temp_dir:
                    root = Path(temp_dir)
                    surfaces = self.load_surfaces()
                    for surface_id in chain:
                        self.promote_surface_with_certificate(root, surfaces, surface_id)
                    target_surface = next(
                        item for item in surfaces["surfaces"] if item["id"] == target_surface_id
                    )
                    binding = target_surface["evidence"][certificate_key]
                    certificate_path = REPO_ROOT / binding["path"]
                    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
                    certificate["input_bindings"][stale_binding_key]["sha256"] = "0" * 64
                    certificate_path.write_text(
                        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    binding["sha256"] = hashlib.sha256(certificate_path.read_bytes()).hexdigest()

                    blockers: list[dict[str, object]] = []
                    READINESS.validate_surfaces(surfaces, blockers)

                reasons = [item["reason"] for item in blockers]
                self.assertIn(expected_reason, reasons)
                self.assertIn(evidence_reason, reasons)

    def test_rejects_command_response_certificate_evidence_only_upstream_summaries(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
            response = self.promote_surface_with_certificate(
                root,
                surfaces,
                "obelisk.command_chat_response_path.v1",
            )
            binding = response["evidence"]["command_response_promotion_certificate"]
            certificate_path = REPO_ROOT / binding["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            input_bindings = certificate.pop("input_bindings")
            certificate["evidence"]["player_identity_promotion_certificate"] = dict(
                input_bindings["player_identity_promotion_certificate"]
            )
            certificate["evidence"]["permissions_admin_promotion_certificate"] = dict(
                input_bindings["permissions_admin_promotion_certificate"]
            )
            certificate_path.write_text(
                json.dumps(certificate, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            binding["sha256"] = hashlib.sha256(certificate_path.read_bytes()).hexdigest()

            blockers: list[dict[str, object]] = []
            READINESS.validate_surfaces(surfaces, blockers)

        reasons = [item["reason"] for item in blockers]
        self.assertIn("command_response_promotion_certificate_input_bindings_missing", reasons)
        self.assertIn(
            "command_response_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
            reasons,
        )
        self.assertIn(
            "command_response_promotion_certificate_current_permissions_admin_certificate_binding_missing_or_mismatch",
            reasons,
        )
        self.assertIn("command_chat_response_evidence_not_approved", reasons)

    def test_rejects_stale_path_sha_bound_promotion_certificate_payloads(self) -> None:
        cases = (
            ("obelisk.player_identity.v1", "player_identity_promotion_certificate"),
            ("obelisk.permissions_admin.v1", "permissions_admin_promotion_certificate"),
            ("obelisk.command_chat_response_path.v1", "command_response_promotion_certificate"),
        )
        chain = [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
        ]
        for surface_id, certificate_key in cases:
            with self.subTest(surface_id=surface_id):
                with tempfile.TemporaryDirectory(
                    dir=CERTIFICATE_TEMP_PARENT,
                    prefix=CERTIFICATE_TEMP_PREFIX,
                ) as temp_dir:
                    root = Path(temp_dir)
                    surfaces = self.load_surfaces()
                    for promoted_surface_id in chain[: chain.index(surface_id) + 1]:
                        self.promote_surface_with_certificate(
                            root,
                            surfaces,
                            promoted_surface_id,
                        )
                    surface = next(
                        item for item in surfaces["surfaces"] if item["id"] == surface_id
                    )
                    surface.setdefault("evidence", {})["unit_test_post_certificate_marker"] = (
                        "non_authorizing_marker"
                    )

                    blockers: list[dict[str, object]] = []
                    READINESS.validate_surfaces(surfaces, blockers)

                self.assertIn(
                    f"{certificate_key}_surface_record_sha256_mismatch",
                    [item["reason"] for item in blockers],
                )

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
            + "\n#define OBELISK_API_CAPABILITY_COMMANDS (1ull << 45)\n"
            + "#define OBELISK_API_CAPABILITY_CHAT_COMMANDS (1ull << 46)\n"
            + "#define OBELISK_API_CAPABILITY_COMMAND_RESPONSE (1ull << 47)\n"
            + "#define OBELISK_API_CAPABILITY_CHAT_RESPONSE (1ull << 48)\n"
            + "#define OBELISK_API_CAPABILITY_CHAT_REPLY (1ull << 49)\n"
            + "\n#define OBELISK_API_CAPABILITY_COMMAND_ROUTER (1ull << 50)\n"
            + "#define OBELISK_API_CAPABILITY_BROADCAST (1ull << 51)\n"
            + "#define OBELISK_API_CAPABILITY_MODERATION (1ull << 52)\n"
            + "#define OBELISK_API_CAPABILITY_COMMAND_REPLY (1ull << 53)\n"
            + "#define OBELISK_API_CAPABILITY_COMMAND_REPLIES (1ull << 54)\n"
            + "#define OBELISK_API_CAPABILITY_COMMANDS_REPLIES (1ull << 55)\n"
            + "#define OBELISK_API_CAPABILITY_CHAT_REPLIES (1ull << 56)\n"
            + "#define OBELISK_API_CAPABILITY_SEND_CHAT (1ull << 57)\n"
            + "#define OBELISK_API_CAPABILITY_NOTICES (1ull << 58)\n"
            + "#define OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_RESPONSE (1ull << 59)\n"
            + "#define OBELISK_COMMAND_ABI_VERSION 1u\n"
            + "#define OBELISK_COMMANDS_ABI_VERSION 1u\n"
            + "#define OBELISK_CHAT_COMMAND_ABI_VERSION 1u\n"
            + "#define OBELISK_CHAT_COMMANDS_ABI_VERSION 1u\n"
            + "#define OBELISK_COMMAND_RESPONSE_ABI_VERSION 1u\n"
            + "#define OBELISK_CHAT_RESPONSE_ABI_VERSION 1u\n"
            + "#define OBELISK_COMMAND_REPLY_ABI_VERSION 1u\n"
            + "#define OBELISK_CHAT_REPLY_ABI_VERSION 1u\n"
            + "#define OBELISK_COMMANDS_REPLIES_ABI_VERSION 1u\n"
            + "#define OBELISK_COMMAND_ROUTER_ABI_VERSION 1u\n"
            + "typedef struct ObeliskCommandChatResponse ObeliskCommandChatResponse;\n"
            + "typedef struct ObeliskCommandResponse ObeliskCommandResponse;\n"
            + "typedef struct ObeliskChatResponse ObeliskChatResponse;\n"
            + "typedef struct ObeliskCommandParser { uint32_t struct_size; } ObeliskCommandParser;\n"
            + "typedef struct ObeliskBroadcast { uint32_t struct_size; } ObeliskBroadcast;\n"
            + "typedef struct ObeliskModeration { uint32_t struct_size; } ObeliskModeration;\n"
            + "typedef struct ObeliskRawFStringCommand ObeliskRawFStringCommand;\n"
            + "typedef struct ObeliskProcessEventResponseShortcut ObeliskProcessEventResponseShortcut;\n"
            + "typedef struct ObeliskCallProcessEventResponseShortcut ObeliskCallProcessEventResponseShortcut;\n"
            + "typedef void (*RegisterCommandReply)(uint64_t ownerToken);\n"
            + "typedef void (*UnregisterCommandReply)(uint64_t ownerToken);\n"
            + "typedef void (*ReplyToCommand)(uint64_t ownerToken);\n"
            + "typedef void (*ReplyToCommandWithOwnerToken)(uint64_t ownerToken);\n"
            + "typedef void (*SendChat)(const char* message);\n"
            + "typedef void (*BroadcastNotice)(const char* message);\n"
            + "typedef void (*SendNotice)(const char* message);\n"
            + "typedef void (*ModerateChat)(uint64_t ownerToken);\n"
            + "typedef void (*RawProcessEventCommandReply)(void* params);\n"
            + "typedef void (*CallProcessEventShortcut)(void* caller);\n"
            + "typedef void (*CallProcessEventResponseShortcut)(void* caller);\n"
            + "typedef void (*CallProcessEventChatResponse)(void* caller);\n"
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
        self.assertIn("OBELISK_API_CAPABILITY_COMMANDS", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_CHAT_COMMANDS", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_RESPONSE", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_CHAT_RESPONSE", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_CHAT_REPLY", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_ROUTER", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_BROADCAST", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_MODERATION", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_REPLY", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_REPLIES", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMANDS_REPLIES", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_CHAT_REPLIES", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_SEND_CHAT", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_NOTICES", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_RESPONSE", detail["symbols"])
        self.assertIn("OBELISK_COMMAND_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_COMMANDS_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_CHAT_COMMAND_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_CHAT_COMMANDS_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_COMMAND_RESPONSE_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_CHAT_RESPONSE_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_COMMAND_REPLY_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_CHAT_REPLY_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_COMMANDS_REPLIES_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_COMMAND_ROUTER_ABI_VERSION", detail["symbols"])
        self.assertIn("ObeliskCommandChatResponse", detail["symbols"])
        self.assertIn("ObeliskCommandResponse", detail["symbols"])
        self.assertIn("ObeliskChatResponse", detail["symbols"])
        self.assertIn("ObeliskCommandParser", detail["symbols"])
        self.assertIn("ObeliskBroadcast", detail["symbols"])
        self.assertIn("ObeliskModeration", detail["symbols"])
        self.assertIn("ObeliskRawFStringCommand", detail["symbols"])
        self.assertIn("ObeliskProcessEventResponseShortcut", detail["symbols"])
        self.assertIn("ObeliskCallProcessEventResponseShortcut", detail["symbols"])
        self.assertIn("RegisterCommandReply", detail["symbols"])
        self.assertIn("UnregisterCommandReply", detail["symbols"])
        self.assertIn("ReplyToCommand", detail["symbols"])
        self.assertIn("ReplyToCommandWithOwnerToken", detail["symbols"])
        self.assertIn("SendChat", detail["symbols"])
        self.assertIn("BroadcastNotice", detail["symbols"])
        self.assertIn("SendNotice", detail["symbols"])
        self.assertIn("ModerateChat", detail["symbols"])
        self.assertIn("RawProcessEventCommandReply", detail["symbols"])
        self.assertIn("CallProcessEventShortcut", detail["symbols"])
        self.assertIn("CallProcessEventResponseShortcut", detail["symbols"])
        self.assertIn("CallProcessEventChatResponse", detail["symbols"])

    def test_public_header_forbidden_tokens_cover_response_path_and_c_abi_aliases(self) -> None:
        response_path_tokens = set(
            READINESS.response_path_readiness.REQUIRED_PUBLIC_HEADER_FORBIDDEN_TOKENS
        )
        command_guard_block = (
            (REPO_ROOT / "tests" / "abi" / "CAbiLayoutTests.c")
            .read_text(encoding="utf-8")
            .split("#if defined(OBELISK_API_CAPABILITY_COMMANDS)", 1)[1]
            .split('#error "Public command response/reply ABI', 1)[0]
        )
        c_abi_tokens = set(re.findall(r"defined\((OBELISK_[A-Z0-9_]+)\)", command_guard_block))

        forbidden_tokens = set(READINESS.REQUIRED_HEADER_ABSENT_TOKENS)
        self.assertEqual([], sorted(response_path_tokens - forbidden_tokens))
        self.assertEqual([], sorted(c_abi_tokens - forbidden_tokens))

    def test_public_header_scan_ignores_comments_and_identifier_supersets(self) -> None:
        header = (
            "/* OBELISK_API_CAPABILITY_COMMAND_REPLY and ObeliskCommandResponse remain blocked. */\n"
            "// CallProcessEventResponseShortcut stays absent until promotion.\n"
            "typedef struct MyObeliskCommandResponseSuffix MyObeliskCommandResponseSuffix;\n"
            "void ReplyToCommandForTestsOnly(void);\n"
            "void CallProcessEventResponseShortcutForTestsOnly(void);\n"
            "#define OBELISK_API_CAPABILITY_COMMAND_REPLY_EXTRA 1\n"
            "#define OBELISK_COMMAND_REPLY_ABI_VERSION_EXTRA 1\n"
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
        self.assertNotIn("public_header_forbidden_symbols_present", report["blockers"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])

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

    def test_rejects_nested_moderation_broadcast_aliases_and_claims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "publicBroadcastApiAllowed": True,
                    "publicNoticeAbiAllowed": True,
                    "moderationApiAllowed": True,
                    "claims": [
                        "broadcast/notices API is ready",
                        "moderation authority is supported",
                    ],
                },
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.secondary_report.publicBroadcastApiAllowed"),
                ("public_surface_overclaim", "$.secondary_report.publicNoticeAbiAllowed"),
                ("public_surface_overclaim", "$.secondary_report.moderationApiAllowed"),
                ("positive_public_surface_claim", "$.secondary_report.claims[0]"),
                ("positive_public_surface_claim", "$.secondary_report.claims[1]"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_runtime_evidence_route_raw_p0_and_live_ops_bypass_claims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "acceptedRuntimeEvidenceOnly": True,
                    "routeBlockerBypassed": True,
                    "rawFStringShortcutReady": True,
                    "callProcessEventShortcutAllowed": True,
                    "p0ProgressReady": True,
                    "sdkP0ProgressReady": True,
                    "liveOpsAuthorized": True,
                    "liveOpsApprovalGranted": True,
                },
                "claims": [
                    "accepted runtime evidence alone is enough",
                    "route blocker bypasses are enabled",
                    "raw FString shortcut is ready",
                    "CallProcessEvent shortcuts are available",
                    "SDK/P0 progress is complete",
                    "live-ops approval is granted",
                    "route blocker bypass remains blocked",
                ],
                "non_claims": [
                    "accepted-runtime-evidence-only is enough",
                    "live-ops authorization remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.acceptedRuntimeEvidenceOnly",
            "$.aliases.routeBlockerBypassed",
            "$.aliases.rawFStringShortcutReady",
            "$.aliases.callProcessEventShortcutAllowed",
            "$.aliases.p0ProgressReady",
            "$.aliases.sdkP0ProgressReady",
            "$.aliases.liveOpsAuthorized",
            "$.aliases.liveOpsApprovalGranted",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for index in range(6):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[6]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.non_claims[0]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.non_claims[1]"), paths)

    def test_rejects_identity_public_contract_review_progress_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "identity_public_contract_decision_record_reviewed": True,
                    "identity_public_contract_decision_record_hash_current": True,
                    "identity_public_contract_decision_record_contract_review_only": True,
                    "reviewed_hash_current_contract_review_only": True,
                },
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.identity_public_contract_decision_record_reviewed",
            "$.aliases.identity_public_contract_decision_record_hash_current",
            "$.aliases.identity_public_contract_decision_record_contract_review_only",
            "$.aliases.reviewed_hash_current_contract_review_only",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)

    def test_rejects_scoped_release_statement_route_credit_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "scopedReleaseStatementReady": True,
                    "scoped_release_statement_counts_toward_complete_sdk_claim": True,
                    "scoped_release_statement_outcomes_satisfy_completion": True,
                },
                "split_claims": [
                    {"claim": "scoped_release_statement_ready", "value": "ready"},
                ],
                "notes": [
                    "scoped release statement unlocks v1 completion",
                    "scoped release statement counts toward public SDK",
                    "scoped release statements cannot unlock commands/replies",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.scopedReleaseStatementReady",
            "$.aliases.scoped_release_statement_counts_toward_complete_sdk_claim",
            "$.aliases.scoped_release_statement_outcomes_satisfy_completion",
            "$.split_claims[0]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        self.assertIn(("positive_public_surface_claim", "$.notes[0]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.notes[1]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[2]"), paths)

    def test_terminal_route_package_status_support_aliases_need_upstream_certificates(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "terminalCertificateReady": True,
                    "packageShapeEvidenceReady": True,
                    "responseStatusReportAccepted": True,
                    "routeClearedForPublicSendChatAbi": True,
                    "bridgeReady": True,
                    "supportTierReportReady": True,
                    "scopedStatementReady": True,
                },
                "split_claims": [
                    {"field": "terminal_certificate_metadata", "status": "accepted"},
                    {"field": "route_cleared", "value": "ready"},
                    {"field": "scoped_statement_counts_toward_completion", "value": True},
                ],
                "notes": [
                    "terminal certificate metadata is accepted",
                    "package shape evidence is ready",
                    "response status report accepted means route cleared",
                    "bridge-ready support tier report is supported",
                    "scoped statement counts toward complete SDK claim",
                    "terminal certificate remains blocked until upstream certificates",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.terminalCertificateReady",
            "$.aliases.packageShapeEvidenceReady",
            "$.aliases.responseStatusReportAccepted",
            "$.aliases.routeClearedForPublicSendChatAbi",
            "$.aliases.bridgeReady",
            "$.aliases.supportTierReportReady",
            "$.aliases.scopedStatementReady",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.notes[0]",
            "$.notes[1]",
            "$.notes[2]",
            "$.notes[3]",
            "$.notes[4]",
        ):
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", label),
                paths,
            )
        self.assertNotIn(
            (
                "route_or_runtime_readiness_alias_missing_upstream_certificates",
                "$.notes[5]",
            ),
            paths,
        )
        certificate_detail = next(
            item
            for item in blockers
            if item["reason"] == "route_or_runtime_readiness_alias_missing_upstream_certificates"
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
                "obelisk.command-chat-response-path-promotion-certificate.v1",
            ],
            certificate_detail["required_certificate_schemas"],
        )

    def test_rejects_package_shape_runtime_simulation_and_planning_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "acceptedRuntimeSimulationReady": True,
                "accepted_runtime_simulation": {"status": "accepted"},
                "activation_precondition_report": {"status": "ready"},
                "beta_notice_action_report": {"status": "accepted"},
                "bridge_report": {"progress": "1/4", "status": "ready"},
                "notice_action_report": {"status": "accepted"},
                "precondition_artifact": {"progress": "1/3"},
                "support_tier_report": {"status": "supported"},
                "supportTierReadinessReady": True,
                "supportTierPackageReady": True,
                "support_tier_package_shape": {"status": "supported"},
                "packageShapeAccepted": True,
                "public_contract_record_package": {"status": "accepted"},
                "request_pack_public_contract_record": {"status": "accepted"},
                "commandPlanningReady": True,
                "command_planning_package": {"status": "ready"},
                "command_response_planning_package": {"status": "ready"},
                "copied_intent_package_shape": {"status": "ready"},
                "route_snapshot": {"status": "accepted"},
                "source_marker": "public_sdk_ready",
                "source_status": "supported",
                "source_marker_pair": {
                    "source_marker": "generic_command_planning_package",
                    "status": "accepted",
                },
                "source_marker_list_pair": {
                    "source_markers": ["route_snapshot"],
                    "source_state": "ready",
                },
                "source_provenance_route_snapshot": {
                    "source_provenance": "route_snapshot",
                    "status": "accepted",
                },
                "source_provenance_accepted_runtime": {
                    "source_provenance": "accepted_runtime_evidence_only",
                    "source_status": "ready",
                },
                "source_provenance_reviewed_contract_metadata": {
                    "source_provenance": "reviewed_hash_current_contract_review_only",
                    "state": "reviewed",
                },
                "aliases": [
                    {"field": "bridge_report", "status": "ready"},
                    {"field": "support_tier_report", "status": "supported"},
                    {"field": "activation_precondition_report", "status": "ready"},
                    {"field": "notice_action_report", "status": "accepted"},
                    {"field": "support_tier_package_shape", "status": "supported"},
                    {"field": "accepted_runtime_simulation", "status": "accepted"},
                    {"field": "command_planning_package", "status": "ready"},
                    {"field": "route_snapshot", "status": "accepted"},
                ],
                "notes": [
                    "bridge report is ready",
                    "activation precondition report is ready",
                    "beta notice action report is accepted",
                    "support tier report is supported",
                    "support tier package shape is supported",
                    "accepted runtime simulation is accepted",
                    "package shape unlocks commands/replies",
                    "command planning is ready",
                    "route snapshot is accepted",
                    "support tier package shape remains blocked",
                    "command planning remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.acceptedRuntimeSimulationReady",
            "$.accepted_runtime_simulation",
            "$.activation_precondition_report",
            "$.beta_notice_action_report",
            "$.bridge_report",
            "$.notice_action_report",
            "$.precondition_artifact.progress",
            "$.support_tier_report",
            "$.supportTierReadinessReady",
            "$.supportTierPackageReady",
            "$.support_tier_package_shape",
            "$.packageShapeAccepted",
            "$.public_contract_record_package",
            "$.request_pack_public_contract_record",
            "$.commandPlanningReady",
            "$.command_planning_package",
            "$.command_response_planning_package",
            "$.copied_intent_package_shape",
            "$.route_snapshot",
            "$.source_marker",
            "$.source_status",
            "$.source_marker_pair",
            "$.source_marker_pair.status",
            "$.source_marker_list_pair",
            "$.source_marker_list_pair.source_state",
            "$.source_provenance_route_snapshot",
            "$.source_provenance_route_snapshot.status",
            "$.source_provenance_accepted_runtime",
            "$.source_provenance_accepted_runtime.source_status",
            "$.source_provenance_reviewed_contract_metadata.state",
            "$.aliases[0]",
            "$.aliases[1]",
            "$.aliases[2]",
            "$.aliases[3]",
            "$.aliases[4]",
            "$.aliases[5]",
            "$.aliases[6]",
            "$.aliases[7]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for index in range(9):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[9]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[10]"), paths)

    def test_rejects_downstream_route_shortcut_status_and_source_ready_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "sourceReady": True,
                "source_status_ready": True,
                "chatSourceReady": True,
                "rconSourceReady": True,
                "broadcastSourceReady": True,
                "sendSourceReady": True,
                "sendSourceStatusReady": True,
                "identity_public_contract_gate_missing": {
                    "source_ready": True,
                    "ready": True,
                    "status": "ready",
                },
                "response_bridge_candidate": {
                    "status": "ready",
                    "counts_toward_public_sdk": True,
                    "p0_dependency_chain_progress_contribution": 1,
                },
                "public_reachability_status": {"source_ready": True, "status": "reachable"},
                "rcon_status": {"source_ready": True, "status": "ready"},
                "broadcast_status": {"ready": True, "status": "enabled"},
                "send_status": {"source_ready": True, "status": "ready"},
                "source_kind_status_probe": {"source_kind": "rcon", "status": "ready"},
                "source_kind_chat_ready_probe": {"source_kind": "chat", "ready": True},
                "reply_channel_status_probe": {"reply_channel": "rcon", "status": "ready"},
                "send_channel_ready_probe": {"send_channel": "server_console", "is_ready": True},
                "status_metadata_probe": {"channel": "broadcast", "status": "sent"},
                "delivery_source_metadata": {"transport": "send_chat", "source_status": "delivered"},
                "transport_result_probe": {"transport": "broadcast", "result": "delivered"},
                "package_support_plugin": {
                    "plugin_hub_support_ready": True,
                    "support_tier_ready": True,
                },
                "split_claims": [
                    {"field": "identity_public_contract_gate_missing", "source_ready": True},
                    {"field": "public_reachability", "ready": True},
                    {"field": "rcon_route", "status": "ready"},
                    {"field": "broadcast_status", "status": "enabled"},
                    {"field": "send_source", "status": "ready"},
                    {"field": "sendSourceStatusReady", "source_status": "sent"},
                    {"field": "package_shape_support", "source_ready": True},
                    {"field": "plugin_hub_package_shape", "ready": True},
                ],
                "claims": [
                    "Plugin Hub stable SDK is public",
                    "commands/replies command candidate counts toward SDK/P0 progress",
                    "send source is ready",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.sourceReady",
            "$.source_status_ready",
            "$.chatSourceReady",
            "$.rconSourceReady",
            "$.broadcastSourceReady",
            "$.sendSourceReady",
            "$.sendSourceStatusReady",
            "$.identity_public_contract_gate_missing",
            "$.response_bridge_candidate.counts_toward_public_sdk",
            "$.response_bridge_candidate.p0_dependency_chain_progress_contribution",
            "$.public_reachability_status",
            "$.rcon_status",
            "$.broadcast_status",
            "$.send_status",
            "$.source_kind_status_probe",
            "$.source_kind_status_probe.status",
            "$.source_kind_chat_ready_probe",
            "$.source_kind_chat_ready_probe.ready",
            "$.reply_channel_status_probe",
            "$.reply_channel_status_probe.status",
            "$.send_channel_ready_probe",
            "$.send_channel_ready_probe.is_ready",
            "$.status_metadata_probe.status",
            "$.delivery_source_metadata.source_status",
            "$.transport_result_probe",
            "$.transport_result_probe.result",
            "$.split_claims[5]",
            "$.package_support_plugin.plugin_hub_support_ready",
            "$.package_support_plugin.support_tier_ready",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.split_claims[3]",
            "$.split_claims[4]",
            "$.split_claims[6]",
            "$.split_claims[7]",
        ):
            with self.subTest(label=label):
                self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.public_reachability_status.source_ready",
            "$.response_bridge_candidate",
            "$.response_bridge_candidate.status",
            "$.response_bridge_candidate.counts_toward_public_sdk",
            "$.response_bridge_candidate.p0_dependency_chain_progress_contribution",
            "$.rcon_status.source_ready",
            "$.source_kind_status_probe.status",
            "$.source_kind_chat_ready_probe.ready",
            "$.reply_channel_status_probe.status",
            "$.send_channel_ready_probe.is_ready",
            "$.status_metadata_probe",
            "$.status_metadata_probe.status",
            "$.delivery_source_metadata.source_status",
            "$.transport_result_probe.result",
        ):
            with self.subTest(label=label):
                self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[0]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[1]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[2]"), paths)

    def test_rejects_multi_surface_beta_capture_pack_plan_p0_credit(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "multiSurfaceBetaCapturePackReady": True,
                "multi_surface_beta_capture_plan": {
                    "status": "accepted",
                    "counts_toward_p0_dependency_chain_claim": True,
                    "progress": "1/4",
                },
                "source_provenance_pack": {
                    "source_provenance": "multi_surface_beta_capture_pack",
                    "source_status": "ready",
                },
                "claims": [
                    "multi-surface beta capture pack accepted as public SDK evidence",
                    "multi-surface beta capture plan counts toward P0 progress",
                    "multi-surface beta capture plan remains candidate-only and non-counting",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.multiSurfaceBetaCapturePackReady",
            "$.multi_surface_beta_capture_plan",
            "$.multi_surface_beta_capture_plan.counts_toward_p0_dependency_chain_claim",
            "$.multi_surface_beta_capture_plan.progress",
            "$.source_provenance_pack.source_status",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.multiSurfaceBetaCapturePackReady",
            "$.multi_surface_beta_capture_plan",
            "$.multi_surface_beta_capture_plan.status",
            "$.multi_surface_beta_capture_plan.counts_toward_p0_dependency_chain_claim",
            "$.multi_surface_beta_capture_plan.progress",
            "$.source_provenance_pack.source_status",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[0]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[1]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[2]"), paths)
        certificate_detail = next(
            item
            for item in blockers
            if item["reason"] == "route_or_runtime_readiness_alias_missing_upstream_certificates"
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
                "obelisk.command-chat-response-path-promotion-certificate.v1",
            ],
            certificate_detail["required_certificate_schemas"],
        )

    def test_promotion_requirement_text_does_not_unlock_runtime_evidence(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "v1_decision_contract": {
                    "promotion_requires": [
                        (
                            "approved runtime evidence bound to the copied runtime-observer "
                            "log source hash and output_artifact_identity.artifact_sha256"
                        )
                    ]
                }
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertNotIn(
            (
                "positive_public_surface_claim",
                "$.v1_decision_contract.promotion_requires[0]",
            ),
            paths,
        )

    def test_non_evidence_artifact_inventory_strings_are_not_credit_but_structured_credit_is_rejected(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "non_evidence_artifacts": [
                    "next-action runner/planner artifacts",
                    "runtime status reports",
                    "package-shape/support-tier artifacts",
                    {"artifact_kind": "status_report", "status": "ready"},
                    {"artifact": "notice_status_artifact", "readiness": "ready"},
                    {"artifact_class": "package_shape", "counts_toward_public_sdk": True},
                ]
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.non_evidence_artifacts[0]",
            "$.non_evidence_artifacts[1]",
            "$.non_evidence_artifacts[2]",
        ):
            self.assertNotIn(("positive_public_surface_claim", label), paths)
        for label in (
            "$.non_evidence_artifacts[3]",
            "$.non_evidence_artifacts[4]",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertIn(
            ("non_evidence_artifact_credit_overclaim", "$.non_evidence_artifacts[5].counts_toward_public_sdk"),
            paths,
        )
        self.assertIn(
            ("public_surface_overclaim", "$.non_evidence_artifacts[5].counts_toward_public_sdk"),
            paths,
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

    def test_rejects_final_authz_response_path_shortcut_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "finalGateReady": True,
                    "authzReady": True,
                    "responsePathComplete": True,
                    "commandsRepliesFinalReady": True,
                },
                "split_claims": [
                    {"field": "finalGateReady", "status": "ready"},
                    {"field": "authzReady", "value": True},
                    {"field": "responsePathComplete", "state": "complete"},
                ],
                "notes": [
                    "final gate ready now",
                    "authz ready now",
                    "response path complete now",
                    "response path remains blocked until predecessor certificates",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.finalGateReady",
            "$.aliases.authzReady",
            "$.aliases.responsePathComplete",
            "$.aliases.commandsRepliesFinalReady",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(3):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), paths)
            self.assertIn(
                (
                    "route_or_runtime_readiness_alias_missing_upstream_certificates",
                    f"$.notes[{index}]",
                ),
                paths,
            )
        self.assertNotIn(("positive_public_surface_claim", "$.notes[3]"), paths)

    def test_rejects_public_abi_identity_lookup_handle_wording(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "notes": [
                    "public ABI exposes player lookup handles before ResourceHandle promotion",
                    "public ABI does not expose player lookup handles before ResourceHandle promotion",
                ]
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("public_abi_identity_lookup_handle_claim", "$.notes[0]"), paths)
        self.assertNotIn(("public_abi_identity_lookup_handle_claim", "$.notes[1]"), paths)

    def test_rejects_nested_route_and_accounting_alias_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "routeReady": True,
                    "public-route-ready": True,
                    "counts_toward_public_sdk": True,
                    "counts_toward_runtime": True,
                    "counts_toward_v1_completion": True,
                    "public_or_runtime_accounting_allowed": True,
                    "stableClaimAllowed": True,
                    "v1_completion_ready": True,
                    "promotedSurfaceCount": 1,
                    "promoted_surfaces_count": "1/4",
                    "surfacePromotionCount": 1,
                    "promotedSurfaceCountZero": "0/4",
                }
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.secondary_report.routeReady"),
                ("public_surface_overclaim", "$.secondary_report.public-route-ready"),
                ("public_surface_overclaim", "$.secondary_report.counts_toward_public_sdk"),
                ("public_surface_overclaim", "$.secondary_report.counts_toward_runtime"),
                ("public_surface_overclaim", "$.secondary_report.counts_toward_v1_completion"),
                ("public_surface_overclaim", "$.secondary_report.public_or_runtime_accounting_allowed"),
                ("public_surface_overclaim", "$.secondary_report.stableClaimAllowed"),
                ("public_surface_overclaim", "$.secondary_report.v1_completion_ready"),
                ("public_surface_overclaim", "$.secondary_report.promotedSurfaceCount"),
                ("public_surface_overclaim", "$.secondary_report.promoted_surfaces_count"),
                ("public_surface_overclaim", "$.secondary_report.surfacePromotionCount"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_collect_overclaims_rejects_split_key_value_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "claims": [
                    {"key": "commandsRepliesReady", "value": True},
                    {"field": "public-send-chat-abi-allowed", "state": "ready"},
                    {"name": "routeGateUnlocked", "enabled": "yes"},
                    {"key": "commandsRepliesReady", "value": False},
                ]
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("public_surface_overclaim", "$.claims[0]"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[1]"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[2]"), paths)
        self.assertNotIn(("public_surface_overclaim", "$.claims[3]"), paths)

    def test_rejects_planning_layout_and_route_accepted_reply_send_chat_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "planningLayoutPublicReplyOrSendChatAbiReady": True,
                    "routeAcceptedAsPublicReplyAbi": True,
                    "routeAcceptedAsPublicReplyAbiReady": True,
                    "routeAccepted": True,
                    "publicRuntimeReadinessReady": True,
                    "planning_layout_accepted": True,
                },
                "claims": [
                    {"field": "planning-layout-public-send-chat-abi-ready", "state": "ready"},
                    {"name": "routeAcceptedForPublicReplyOrSendChatAbi", "enabled": "yes"},
                    {"name": "routeAcceptedForPublicRuntimeReadiness", "enabled": "yes"},
                    "planning_layout_public_reply_or_send_chat_abi_ready",
                    "route accepted as public send-chat ABI ready",
                    "route accepted remains blocked",
                ],
                "non_claims": [
                    "route accepted as public runtime readiness",
                    "route accepted remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("public_surface_overclaim", "$.aliases.planningLayoutPublicReplyOrSendChatAbiReady"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.routeAcceptedAsPublicReplyAbi"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.aliases.routeAcceptedAsPublicReplyAbiReady"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.routeAccepted"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.aliases.publicRuntimeReadinessReady"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.planning_layout_accepted"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[0]"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[1]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[2]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[3]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[4]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[4]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[5]"), paths)
        self.assertNotIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[5]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.non_claims[0]"), paths)
        self.assertNotIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.non_claims[1]"), paths)
        certificate_detail = next(
            item
            for item in blockers
            if item["reason"] == "route_or_runtime_readiness_alias_missing_upstream_certificates"
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
                "obelisk.command-chat-response-path-promotion-certificate.v1",
            ],
            certificate_detail["required_certificate_schemas"],
        )

    def test_rejects_nested_runtime_readiness_alias_values(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "publicRuntimeReady": {"state": {"ready": True}},
                    "runtimeReadinessAccepted": {"status": {"verified": "yes"}},
                    "identityPublicContractGateMissingAllowsSendChat": {
                        "review": {"ready": True}
                    },
                },
                "claims": [
                    {
                        "field": "public_runtime_readiness_accepted",
                        "value": {"nested": {"status": "ready"}},
                    }
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.publicRuntimeReady",
            "$.aliases.runtimeReadinessAccepted",
            "$.aliases.identityPublicContractGateMissingAllowsSendChat",
            "$.claims[0]",
        ):
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", label),
                paths,
            )
        self.assertIn(
            ("public_surface_overclaim", "$.aliases.identityPublicContractGateMissingAllowsSendChat"),
            paths,
        )

    def test_rejects_response_send_broadcast_aliases_and_certificate_metadata_without_upstream_certificates(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "publicResponseSendBroadcastReady": True,
                    "routeAcceptedAsPublicSendChatAbiReady": True,
                    "identityPublicContractGateMissingAllowsBroadcast": True,
                },
                "metadata": {
                    "fake_player_identity_certificate": {
                        "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "evidence": {"reviewed_artifact_hash": "a" * 64},
                    },
                    "fake_permissions_admin_certificate": {
                        "certificate_schema": READINESS.PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
                        "status": "promoted",
                        "counts_toward_public_sdk": True,
                    },
                    "fake_command_response_certificate": {
                        "schema": READINESS.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
                        "surface_id": "obelisk.command_chat_response_path.v1",
                        "promotion_status": "promoted",
                        "evidence": {"reviewed_surface_record_sha256": "b" * 64},
                    },
                },
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.publicResponseSendBroadcastReady",
            "$.aliases.routeAcceptedAsPublicSendChatAbiReady",
            "$.aliases.identityPublicContractGateMissingAllowsBroadcast",
        ):
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", label),
                paths,
            )
        for label in (
            "$.metadata.fake_player_identity_certificate",
            "$.metadata.fake_permissions_admin_certificate",
            "$.metadata.fake_command_response_certificate",
        ):
            self.assertIn(
                ("promotion_certificate_metadata_missing_required_upstream_certificates", label),
                paths,
            )
        certificate_detail = next(
            item
            for item in blockers
            if item["reason"] == "promotion_certificate_metadata_missing_required_upstream_certificates"
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
                "obelisk.command-chat-response-path-promotion-certificate.v1",
            ],
            certificate_detail["required_upstream_certificate_schemas"],
        )

    def test_path_like_fields_do_not_create_public_surface_text_claims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "surfaces_path": "/tmp/obelisk/public-sdk-surfaces-route-context.json",
                "response_path_root": "/tmp/command-chat-response-public-readiness",
                "notes": "route accepted as public send-chat ABI ready",
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertNotIn(("positive_public_surface_claim", "$.surfaces_path"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.response_path_root"), paths)
        self.assertIn(("positive_public_surface_claim", "$.notes"), paths)

    def test_rejects_unlocked_public_abi_reply_send_chat_claim_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "publicAbiUnlocked": True,
                    "publicReplyAbiUnlocked": True,
                    "replyUnlocked": True,
                    "sendChatApiUnlocked": True,
                },
                "claims": [
                    "public_abi_unlocked",
                    "reply_abi_unlocked",
                    "send_chat_api_unlocked",
                    "publicReplyOrSendChatAbiUnlocked",
                    "send_chat_api_unlocked remains blocked",
                ],
            },
            blockers,
        )

        self.assertEqual(4, [item["reason"] for item in blockers].count("public_surface_overclaim"))
        self.assertEqual(4, [item["reason"] for item in blockers].count("positive_public_surface_claim"))
        self.assertNotIn(("positive_public_surface_claim", "$.claims[4]"), [(item["reason"], item["label"]) for item in blockers])

    def test_rejects_activation_notice_reachability_request_and_identity_gate_unlock_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "activationPreconditionsMet": True,
                    "betaNoticeSent": True,
                    "discordSent": True,
                    "publicReachabilityReady": True,
                    "requestCheckReady": True,
                    "requestPackReady": True,
                    "identityPublicContractGateMissingAllowsSendChat": True,
                },
                "claims": [
                    {"field": "identity_public_contract_gate_missing_allows_broadcast", "state": "ready"},
                    "activation preconditions met make send-chat API ready",
                    "beta notice sent makes replies ready",
                    "public reachability is reachable so broadcast API is enabled",
                    "request checks passed make command replies public",
                    "identity_public_contract_gate_missing unlocks chat/send/broadcast APIs",
                    "identity_public_contract_gate_missing remains blocked until permissions/admin promotion",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.activationPreconditionsMet",
            "$.aliases.betaNoticeSent",
            "$.aliases.discordSent",
            "$.aliases.publicReachabilityReady",
            "$.aliases.requestCheckReady",
            "$.aliases.requestPackReady",
            "$.aliases.identityPublicContractGateMissingAllowsSendChat",
            "$.claims[0]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(1, 6):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[5]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[6]"), paths)
        self.assertNotIn(
            ("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[6]"),
            paths,
        )

    def test_rejects_child_pass_supplied_surfaces_and_readiness_gate_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "identityPublicContractGateMissingChildPass": True,
                    "childPass": True,
                    "suppliedSurfacesReady": True,
                    "supplied_surfaces": [
                        "obelisk.player_identity.v1",
                        "obelisk.permissions_admin.v1",
                    ],
                    "readinessAlias": {"state": "ready"},
                    "blockedChildPass": "blocked",
                },
                "split_claims": [
                    {"field": "childPass", "status": "passed"},
                    {"name": "suppliedSurfaces", "value": ["obelisk.player_identity.v1"]},
                    {"claim": "readinessAlias", "state": "ready"},
                    {"field": "childPass", "status": "blocked"},
                ],
                "claims": [
                    "child pass makes commands/replies ready",
                    "supplied surfaces readiness passes the identity public contract gate",
                    "readiness alias unlocks reply/send-chat ABI",
                    "child pass remains blocked by identity public contract gate",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.identityPublicContractGateMissingChildPass",
            "$.aliases.childPass",
            "$.aliases.suppliedSurfacesReady",
            "$.aliases.supplied_surfaces",
            "$.aliases.readinessAlias",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        self.assertNotIn(("public_surface_overclaim", "$.aliases.blockedChildPass"), paths)
        self.assertNotIn(("public_surface_overclaim", "$.split_claims[3]"), paths)
        for index in range(3):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", f"$.claims[{index}]"),
                paths,
            )
        self.assertNotIn(("positive_public_surface_claim", "$.claims[3]"), paths)
        self.assertNotIn(
            ("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[3]"),
            paths,
        )

    def test_rejects_response_bridge_passive_seed_and_copied_intent_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "responseBridgeReady": True,
                    "commandPrincipalAuthzResponseBridgeReady": True,
                    "passiveEvidenceReady": True,
                    "passiveChatEvidenceReady": True,
                    "copiedResponseIntentPlanningReady": True,
                    "copiedResponseIntentReady": True,
                    "localRoutingSeedReady": True,
                    "localChatSeedReady": True,
                    "chatSeedReady": True,
                },
                "split_claims": [
                    {"name": "responseBridgeReady", "isReady": True},
                    {"claim": "passiveEvidenceReady", "result": "accepted"},
                    {"field": "copiedResponseIntentPlanningReady", "outcome": "promoted"},
                    {"key": "localRoutingSeedReady", "verdict": "ready"},
                    {"name": "responseBridgeReady", "isReady": False},
                ],
                "claims": [
                    "response bridge planning is ready",
                    "copied response intent planning is accepted for public runtime readiness",
                    "passive evidence is sufficient for reply/send-chat ABI",
                    "local routing seed unlocks commands/replies",
                    "local chat seeds are ready for public send-chat API",
                    "response bridge planning remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.responseBridgeReady",
            "$.aliases.commandPrincipalAuthzResponseBridgeReady",
            "$.aliases.passiveEvidenceReady",
            "$.aliases.passiveChatEvidenceReady",
            "$.aliases.copiedResponseIntentPlanningReady",
            "$.aliases.copiedResponseIntentReady",
            "$.aliases.localRoutingSeedReady",
            "$.aliases.localChatSeedReady",
            "$.aliases.chatSeedReady",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.split_claims[3]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        self.assertNotIn(("public_surface_overclaim", "$.split_claims[4]"), paths)
        for index in range(5):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[5]"), paths)

    def test_rejects_notice_route_snapshot_and_bundle_positive_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "notice_bundle": {"status": "delivered"},
                "notices_package": {"state": "complete"},
                "route_snapshot": {"result": "accepted"},
                "route_bundle": {"status": "ready"},
                "route_snapshot_bundle": {"outcome": "sent"},
                "claims": [
                    {"field": "notice_bundle", "delivered": True},
                    {"name": "route_snapshot_bundle", "complete": True},
                    "notice bundle delivered makes commands/replies ready",
                    "route snapshot bundle complete unlocks public runtime readiness",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.notice_bundle",
            "$.notices_package",
            "$.route_snapshot",
            "$.route_bundle",
            "$.route_snapshot_bundle",
            "$.claims[0]",
            "$.claims[1]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[2]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[3]"), paths)

    def test_rejects_positive_aliases_inside_post_response_diagnostics(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "post_command_response_blocker_diagnostic": {
                    "publicSdkReady": True,
                    "stableSdkReady": True,
                    "p0ProgressReady": True,
                    "replyApiUnlocked": True,
                    "sendChatApiUnlocked": True,
                    "source": "diagnostic_candidate",
                    "status": "ready",
                    "claim": "post response diagnostic makes replies ready",
                }
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.post_command_response_blocker_diagnostic.publicSdkReady",
            "$.post_command_response_blocker_diagnostic.stableSdkReady",
            "$.post_command_response_blocker_diagnostic.p0ProgressReady",
            "$.post_command_response_blocker_diagnostic.replyApiUnlocked",
            "$.post_command_response_blocker_diagnostic.sendChatApiUnlocked",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        self.assertIn(
            (
                "non_evidence_artifact_credit_overclaim",
                "$.post_command_response_blocker_diagnostic.status",
            ),
            paths,
        )

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

    def test_rejects_downstream_chain_gate_progress_and_artifact_drift(self) -> None:
        decisions = self.load_decisions()
        gate = decisions["downstream_chain_gate"]
        gate["non_counting_artifact_classes"].remove("package_shape")
        sequence = gate["post_command_response_required_sequence"]
        sequence[0]["id"], sequence[1]["id"] = sequence[1]["id"], sequence[0]["id"]
        sequence[0]["counts_as_downstream_progress"] = True
        sequence[0]["counts_toward_v1_completion"] = True
        sequence[0]["downstream_progress_contribution"] = 1
        sequence[0]["artifact_classes_not_progress"].remove("status_report")
        sequence[0]["source_provenance"] = "status_report"
        sequence[0]["source_status"] = "ready"
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
        self.assertIn("downstream_chain_gate_sequence_mismatch", report["blockers"])
        self.assertIn("downstream_chain_gate_non_counting_artifacts_missing", report["blockers"])
        self.assertIn("downstream_chain_gate_blocker_false_field_not_false", report["blockers"])
        self.assertIn("downstream_chain_gate_blocker_zero_field_not_zero", report["blockers"])
        self.assertIn("downstream_chain_gate_blocker_non_counting_artifacts_missing", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])

    def test_rejects_missing_post_response_abi_evidence_guardrail(self) -> None:
        decisions = self.load_decisions()
        decisions.pop("post_response_abi_evidence_guardrail")
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
        self.assertIn("post_response_abi_evidence_guardrail_mismatch", report["blockers"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])

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
        self.assertIn("response_path_report_not_revalidatable_handoff", report["blockers"])
        self.assertIn("response_path_report_source_artifact_hashes_missing", report["blockers"])

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

    def test_overclaim_scan_rejects_source_zero_start_end_transfer_and_rcon_aliases(self) -> None:
        blockers: list[dict] = []
        payload = {
            "source_overclaim_total_flag_count": 0,
            "status": "ready",
            "start_end_only_evidence": {"status": "ready"},
            "transfer_baccept_candidate": {"status": "ready"},
            "rcon_command_candidate": {"status": "ready"},
        }

        READINESS.collect_overclaims(payload, blockers, "$.unit")
        reasons = [blocker["reason"] for blocker in blockers]

        self.assertIn("source_overclaim_zero_status_alias_overclaim", reasons)
        self.assertIn("non_evidence_artifact_credit_overclaim", reasons)
        self.assertIn("public_surface_overclaim", reasons)


if __name__ == "__main__":
    unittest.main()
