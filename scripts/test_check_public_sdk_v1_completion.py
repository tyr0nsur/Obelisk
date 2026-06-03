#!/usr/bin/env python3
"""Tests for the v1 complete-SDK release claim checker."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_public_sdk_v1_completion import (
    SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER,
    blocker_guidance,
    command_permission_route_gate_public_or_runtime_claims,
    permissions_admin_structured_promotion_evidence_missing,
    player_identity_structured_promotion_evidence_missing,
    release_statement_satisfies_exclusion_contract,
    secondary_report_completion_claims_without_blocker,
    surface_has_promotion_evidence,
)
import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_runtime_principal_lifecycle_evidence
from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (
    manifest as approved_runtime_principal_lifecycle_manifest,
)

SCRIPT = REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"
PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
SCOPED_RELEASE_STATEMENT_TEMPLATE = (
    REPO_ROOT / "release" / "v1" / "public-sdk" / "scoped-release-statement-template.md"
)
PROMOTED_SURFACE_TEST_EXECUTION_ARTIFACT_SCHEMA = (
    "obelisk.promoted-surface-test-execution-artifact.v1"
)
PROMOTED_SURFACE_TEST_EXECUTION_PRODUCER = "obelisk.promoted-surface-test-execution-runner.v1"
PROMOTED_SURFACE_TEST_EXECUTION_CHECKER = "scripts/check_public_sdk_v1_completion.py"
PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
EXPERIMENTAL_EXCLUSION_DETAILS = {
    "obelisk.gameplay_policy_event.v1": "GameplayPolicyEvent is not included in v1.",
    "obelisk.chat_message.v1": "ChatMessageEvent is not included in v1.",
    "obelisk.chat.local_routing.v1": "chat routing is not included in v1.",
    "obelisk.inventory_item_copied_signals.v1": "inventory copied signals are not included in v1.",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_artifact_hashes(**paths: Path) -> dict[str, str]:
    return {key: sha256_file(path) for key, path in paths.items()}


def write_source_bound_command_response_report(
    root: Path,
    *,
    surfaces_path: Path = PUBLIC_SDK_SURFACES,
    public_header_path: Path = PUBLIC_HEADER,
) -> tuple[Path, Path]:
    readiness = root / "command-chat-response-route-planning-readiness.json"
    readiness.write_text(
        json.dumps(
            {
                "source_root": str(root),
                "producer": {
                    "script": "scripts/compare_reflection_snapshots.py",
                    "output_name": "command-chat-response-route-planning-readiness.json",
                    "argv": [
                        "scripts/compare_reflection_snapshots.py",
                        "--target-set",
                        "command-chat-response-route-planning",
                        "--readiness-report",
                        str(readiness),
                        "--json",
                    ],
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    response_report_root = root / "command-chat-response-public-readiness"
    response_report_root.mkdir(exist_ok=True)
    response_report = response_report_root / "command-chat-response-public-readiness.json"
    response_report.write_text(
        json.dumps(
            {
                "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                "readiness_root": str(root),
                "readiness_path": str(readiness),
                "decisions_path": str(REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"),
                "surfaces_path": str(surfaces_path),
                "public_header_path": str(public_header_path),
                "source_artifact_hashes": source_artifact_hashes(
                    readiness_path=readiness,
                    decisions_path=REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json",
                    surfaces_path=surfaces_path,
                    public_header_path=public_header_path,
                ),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return response_report_root, response_report


def current_repo_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def write_executed_test_artifact(
    path: Path,
    surface_id: str,
    *,
    command: str | None = None,
    argv: list[str] | None = None,
    public_sdk_surfaces: Path = PUBLIC_SDK_SURFACES,
    public_header: Path = PUBLIC_HEADER,
) -> str:
    def binding_path_text(input_path: Path) -> str:
        try:
            return str(input_path.resolve().relative_to(REPO_ROOT))
        except ValueError:
            return str(input_path.resolve())

    payload: dict[str, object] = {
        "schema": PROMOTED_SURFACE_TEST_EXECUTION_ARTIFACT_SCHEMA,
        "surface_id": surface_id,
        "producer": PROMOTED_SURFACE_TEST_EXECUTION_PRODUCER,
        "checker": PROMOTED_SURFACE_TEST_EXECUTION_CHECKER,
        "produced_at_utc": "2026-06-02T00:00:00+00:00",
        "obelisk_commit": current_repo_head(),
        "exit_code": 0,
        "output_sha256": "0" * 64,
        "inputs": {
            "public_sdk_surfaces": {
                "path": binding_path_text(public_sdk_surfaces),
                "sha256": sha256_file(public_sdk_surfaces),
            },
            "public_header": {
                "path": binding_path_text(public_header),
                "sha256": sha256_file(public_header),
            },
        },
    }
    if argv is not None:
        payload["argv"] = argv
    else:
        payload["command"] = command or f"python3 -m unittest {surface_id}"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return str(path.relative_to(REPO_ROOT))


def inline_executed_test_report(surface_id: str, abi_path: Path, sdk_path: Path) -> dict[str, object]:
    return {
        "schema": "obelisk.promoted-surface-test-execution.v1",
        "surface_id": surface_id,
        "abi_tests": [
            {
                "path": str(abi_path.relative_to(REPO_ROOT)),
                "command": f"python3 -m unittest {surface_id}.abi",
                "status": "passed",
            }
        ],
        "sdk_consumer_tests": [
            {
                "path": str(sdk_path.relative_to(REPO_ROOT)),
                "command": f"cmake --build {surface_id}.sdk_consumer",
                "status": "passed",
            }
        ],
    }


def complete_excluded_manifest() -> tuple[dict, str]:
    manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
    manifest["v1_completion_required"] = True
    manifest["stable_release_contract"]["claim_allowed"] = True
    manifest["experimental_surfaces"] = []
    manifest["planning_surfaces"] = []
    release_lines = [
        "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
    ]
    for surface in manifest["surfaces"]:
        if surface["status"] == "promoted-experimental-only":
            surface["status"] = "excluded"
            surface["public_contract"] = []
            if surface["id"] not in manifest["post_v1_or_excluded_surfaces"]:
                manifest["post_v1_or_excluded_surfaces"].append(surface["id"])
            detail = EXPERIMENTAL_EXCLUSION_DETAILS.get(surface["id"], "experimental seed is not included in v1.")
            release_lines.append(f"{surface['id']}: excluded - {detail}")
        if surface["id"] in manifest["v1_sdk_completion_blockers"]:
            surface["status"] = "excluded"
            surface["public_contract"] = []
            if surface["id"] == "obelisk.mission_transfer_dino_tribe.v1":
                for leaf in surface.get("leaf_decision_units", []):
                    if isinstance(leaf, dict):
                        leaf["status"] = "excluded"
                        leaf["public_contract"] = []
            if not isinstance(surface.get("v1_decision_contract"), dict):
                exclusions = surface.get("exclusions") if isinstance(surface.get("exclusions"), list) else []
                audit_units = surface.get("audit_units") if isinstance(surface.get("audit_units"), list) else []
                named_exclusions = [
                    str(item)
                    for item in [*exclusions, *audit_units]
                    if isinstance(item, str)
                ]
                required_text = (
                    f"no {', '.join(named_exclusions)} API is included in v1"
                    if named_exclusions
                    else f"no public API for {surface['id']} is included in v1"
                )
                surface["v1_decision_contract"] = {
                    "exclusion_requires": [
                        f"the v1 release statement names {surface['id']} as excluded",
                        f"the v1 release statement states that {required_text}",
                    ]
                }
            if surface["id"] not in manifest["post_v1_or_excluded_surfaces"]:
                manifest["post_v1_or_excluded_surfaces"].append(surface["id"])
            contract = surface.get("v1_decision_contract")
            detail_parts = ["no public API for this surface is included in v1"]
            if isinstance(contract, dict):
                for requirement in contract.get("exclusion_requires", []):
                    marker = "the v1 release statement states that "
                    if isinstance(requirement, str) and requirement.lower().startswith(marker):
                        detail_parts.append(requirement[len(marker) :])
            if surface["id"] == "obelisk.mission_transfer_dino_tribe.v1":
                detail_parts.append(
                    "mission excluded; transfer excluded; dino_policy excluded; "
                    "tribe_policy excluded; buff_status excluded"
                )
            release_lines.append(f"{surface['id']}: excluded - {'; '.join(detail_parts)}")
    return manifest, "\n".join(release_lines) + "\n"


class PublicSdkV1CompletionCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_test_workspace_prefixes = os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES")
        os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = "1"

    def tearDown(self) -> None:
        if self._old_test_workspace_prefixes is None:
            os.environ.pop("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES", None)
        else:
            os.environ["OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"] = self._old_test_workspace_prefixes

    def run_checker(
        self,
        *args: str,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        run_env = os.environ.copy()
        if env is not None:
            run_env.update(env)
        result = subprocess.run(
            ["python3", str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            env=run_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def route_gate_override_env(self) -> dict[str, str]:
        return {"OBELISK_SDK_COMPLETION_ALLOW_ROUTE_GATE_OVERRIDE_FOR_TESTS": "1"}

    def write_approved_runtime_manifest_binding(self, path: Path) -> dict[str, str]:
        data = json.dumps(approved_runtime_principal_lifecycle_manifest(), sort_keys=True).encode("utf-8")
        path.write_bytes(data)
        return {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def write_approved_runtime_evidence_artifacts(self, manifest_path: Path, report_path: Path) -> dict[str, str]:
        manifest_payload = approved_runtime_principal_lifecycle_manifest()
        data = json.dumps(manifest_payload, sort_keys=True).encode("utf-8")
        manifest_path.write_bytes(data)
        validation = approved_runtime_principal_lifecycle_evidence.validate_manifest(
            manifest_payload,
            check_mode="consume",
        )
        report = approved_runtime_principal_lifecycle_evidence.build_report(
            manifest_payload,
            validation,
            check_mode="consume",
        )
        report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
        return {
            "approved_runtime_evidence_manifest": {
                "path": str(manifest_path.relative_to(REPO_ROOT)),
                "sha256": hashlib.sha256(data).hexdigest(),
            },
            "approved_runtime_evidence_report": str(report_path.relative_to(REPO_ROOT)),
        }

    def identity_structured_missing_for_contract_report(self, contract_payload: dict[str, object]) -> list[str]:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            root = Path(core_dir)
            runtime_manifest = root / "approved-runtime-principal-lifecycle-evidence.json"
            runtime_report = root / "player_identity_approved_runtime_report.json"
            contract_report = root / "player_identity_public_contract_readiness_report.json"
            executed_report = root / "player_identity_executed_tests.json"
            runtime_artifacts = self.write_approved_runtime_evidence_artifacts(runtime_manifest, runtime_report)
            contract_report.write_text(json.dumps(contract_payload), encoding="utf-8")
            executed_report_path = write_executed_test_artifact(
                executed_report,
                "obelisk.player_identity.v1",
                argv=["python3", "-m", "unittest", "player_identity_promotion"],
            )
            return player_identity_structured_promotion_evidence_missing(
                {
                    **runtime_artifacts,
                    "public_contract_readiness_report": str(contract_report.relative_to(REPO_ROOT)),
                    "executed_test_report": executed_report_path,
                }
            )

    def player_identity_contract_gate_inputs(self) -> list[dict[str, object]]:
        return [
            {
                "id": "runtime.lifecycle_evidence",
                "status": "unresolved",
                "review_inputs": ["runtime.lifecycle_evidence"],
                "remaining_promotion_inputs": [],
                "promotion_blocker_resolved": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "v1_completion_evidence": False,
                "non_claim": "Accepted runtime lifecycle evidence is a contract-review input only.",
            },
            {
                "id": "privacy.identifier_redaction",
                "status": "unresolved",
                "review_inputs": ["privacy.identifier_redaction"],
                "remaining_promotion_inputs": [
                    "privacy.public_identifier_form",
                    "privacy.redacted_identifier_fields",
                    "privacy.logging_and_storage_policy",
                ],
                "promotion_blocker_resolved": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "v1_completion_evidence": False,
                "non_claim": "Identifier-redaction evidence is sanitized contract-review input only.",
            },
            {
                "id": "lifetime.generation_scope_invalidation",
                "status": "unresolved",
                "review_inputs": ["lifetime.generation_scope_invalidation.candidate_policy"],
                "remaining_promotion_inputs": [
                    "lifetime.principal_scope",
                    "lifetime.invalidation_events",
                    "lifetime.reconnect_duplicate_stale_policy",
                ],
                "promotion_blocker_resolved": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "v1_completion_evidence": False,
                "non_claim": "Candidate invalidation-policy acceptance is review input only.",
            },
            {
                "id": "abi.public_pod_contract",
                "status": "unresolved",
                "review_inputs": [
                    "abi.public_pod_contract.private_layout_candidate",
                    "abi.public_pod_contract.public_abi_preflight_candidate",
                ],
                "remaining_promotion_inputs": [
                    "abi.payload_shape",
                    "abi.capability_bits",
                    "abi.append_only_layout_tests",
                    "abi.layout",
                    "sdk.consumer",
                ],
                "promotion_blocker_resolved": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "v1_completion_evidence": False,
                "non_claim": "Private POD layout and public ABI preflight candidates are offline review inputs only.",
            },
            {
                "id": "lifecycle.owner_cleanup",
                "status": "unresolved",
                "review_inputs": ["lifecycle.owner_cleanup.owner_token_sdk_consumer_contract"],
                "remaining_promotion_inputs": [
                    "abi.owner_token_registration",
                    "lifecycle.owner_cleanup.runtime_tests",
                ],
                "promotion_blocker_resolved": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "v1_completion_evidence": False,
                "non_claim": "Owner-token SDK consumer contract evidence is candidate-only review input.",
            },
            {
                "id": "separation.downstream_surfaces",
                "status": "unresolved",
                "review_inputs": ["separation.no_commands_permissions_persistence"],
                "remaining_promotion_inputs": [
                    "permissions_admin_contract_blocker",
                    "command_chat_response_contract_blocker",
                    "commands_replies_contract_blocker",
                    "player_lookup_exclusion_review",
                    "storage_persistence_exclusion_review",
                ],
                "promotion_blocker_resolved": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "v1_completion_evidence": False,
                "non_claim": "Identity promotion cannot unlock downstream surfaces.",
            },
        ]

    def write_player_identity_structured_promotion_artifacts(self, root: Path) -> dict[str, str]:
        runtime_manifest = root / "approved-runtime-principal-lifecycle-evidence.json"
        runtime_report = root / "player_identity_approved_runtime_report.json"
        contract_report = root / "player_identity_public_contract_readiness_report.json"
        executed_report = root / "player_identity_executed_tests.json"
        runtime_artifacts = self.write_approved_runtime_evidence_artifacts(runtime_manifest, runtime_report)
        contract_report.write_text(
            json.dumps(
                {
                    "schema": "obelisk.player-identity-public-contract-readiness-check.v1",
                    "ready": True,
                    "ready_scope": "contract_review_input_only",
                    "surface": "obelisk.player_identity.v1",
                    "accepted_for_contract_review": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "public_contract_allowed": False,
                    "public_header_allowed": False,
                    "public_header_symbols_now": [],
                    "public_capability_bits_now": [],
                    "public_callback_abi_now": [],
                    "next_blocker": "identity_public_contract_gate_missing",
                    "blockers": [],
                    "resolved_inputs": ["runtime.lifecycle_evidence"],
                    "contract_gate_inputs": self.player_identity_contract_gate_inputs(),
                    "remaining_blockers": [
                        "runtime.lifecycle_evidence",
                        "privacy.identifier_redaction",
                        "lifetime.generation_scope_invalidation",
                        "abi.public_pod_contract",
                        "lifecycle.owner_cleanup",
                        "separation.downstream_surfaces",
                    ],
                    "private_candidate_contract": {
                        "candidate_only": True,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "public_header_allowed": False,
                    },
                    "private_pod_layout_candidate": {
                        "candidate_only": True,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                    },
                    "approved_runtime_evidence": {
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        executed_report_path = write_executed_test_artifact(
            executed_report,
            "obelisk.player_identity.v1",
            argv=["python3", "-m", "unittest", "player_identity_promotion"],
        )
        return {
            **runtime_artifacts,
            "public_contract_readiness_report": str(contract_report.relative_to(REPO_ROOT)),
            "executed_test_report": executed_report_path,
        }

    def write_player_identity_promotion_certificate(
        self,
        path: Path,
        identity_artifacts: dict[str, str],
        **overrides: object,
    ) -> dict[str, str]:
        payload: dict[str, object] = {
            "schema": "obelisk.player-identity-promotion-certificate.v1",
            "surface_id": "obelisk.player_identity.v1",
            "promotion_status": "promoted",
            "v1_dependency_chain": [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
            "v1_dependency_chain_position": 1,
            "required_by_surface": "obelisk.permissions_admin.v1",
            "required_by_v1_dependency_chain_position": 2,
            "evidence": identity_artifacts,
        }
        payload.update(overrides)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        relative = str(path.relative_to(REPO_ROOT))
        return {
            "path": relative,
            "sha256": sha256_file(REPO_ROOT / relative),
        }

    def write_dependency_promotion_certificate(
        self,
        path: Path,
        *,
        schema: str,
        surface_id: str,
        position: int,
        required_by_surface: str,
        required_by_position: int,
        evidence: dict[str, object],
        **overrides: object,
    ) -> dict[str, str]:
        payload: dict[str, object] = {
            "schema": schema,
            "surface_id": surface_id,
            "promotion_status": "promoted",
            "v1_dependency_chain": [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
            "v1_dependency_chain_position": position,
            "required_by_surface": required_by_surface,
            "required_by_v1_dependency_chain_position": required_by_position,
            "evidence": evidence,
        }
        payload.update(overrides)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        relative = str(path.relative_to(REPO_ROOT))
        return {
            "path": relative,
            "sha256": sha256_file(REPO_ROOT / relative),
        }

    def write_permissions_admin_promotion_certificate(
        self,
        path: Path,
        permissions_artifacts: dict[str, object],
        **overrides: object,
    ) -> dict[str, str]:
        return self.write_dependency_promotion_certificate(
            path,
            schema="obelisk.permissions-admin-promotion-certificate.v1",
            surface_id="obelisk.permissions_admin.v1",
            position=2,
            required_by_surface="obelisk.command_chat_response_path.v1",
            required_by_position=3,
            evidence=permissions_artifacts,
            **overrides,
        )

    def write_command_response_promotion_certificate(
        self,
        path: Path,
        command_response_artifacts: dict[str, object],
        **overrides: object,
    ) -> dict[str, str]:
        return self.write_dependency_promotion_certificate(
            path,
            schema="obelisk.command-chat-response-path-promotion-certificate.v1",
            surface_id="obelisk.command_chat_response_path.v1",
            position=3,
            required_by_surface="obelisk.commands_replies.v1",
            required_by_position=4,
            evidence=command_response_artifacts,
            **overrides,
        )

    def write_permissions_admin_structured_promotion_artifacts(self, root: Path) -> dict[str, str]:
        query_report = root / "permissions_admin_query_failclosed_report.json"
        readiness_report = root / "permissions_admin_public_readiness_report.json"
        executed_report = root / "permissions_admin_executed_tests.json"
        query_report.write_text(
            json.dumps(
                {
                    "schema": "obelisk.permissions-admin-query-failclosed-contract-check.v1",
                    "input_schema": "obelisk.permissions-admin-query-failclosed-contract.v1",
                    "mode": "consume",
                    "ready": True,
                    "valid": True,
                    "candidate_only": True,
                    "pre_abi": True,
                    "public_header_allowed": False,
                    "public_cache_abi_allowed": False,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "blockers": [],
                }
            ),
            encoding="utf-8",
        )
        readiness_report.write_text(
            json.dumps(
                {
                    "schema": "obelisk.permissions-admin-public-readiness-check.v1",
                    "surface": "obelisk.permissions_admin.v1",
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_abi_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "dependency": "obelisk.player_identity.v1",
                    "query_failclosed_artifact_schema": "obelisk.permissions-admin-query-failclosed-contract.v1",
                    "blockers": [],
                }
            ),
            encoding="utf-8",
        )
        executed_report_path = write_executed_test_artifact(
            executed_report,
            "obelisk.permissions_admin.v1",
            argv=["python3", "-m", "unittest", "permissions_admin_promotion"],
        )
        return {
            "query_failclosed_report": str(query_report.relative_to(REPO_ROOT)),
            "public_readiness_report": str(readiness_report.relative_to(REPO_ROOT)),
            "executed_test_report": executed_report_path,
        }

    def write_fake_route_gate(self, path: Path, **overrides: object) -> Path:
        payload = {
            "schema": "obelisk.command-permission-route-gate-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "planning_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "public_or_runtime_accounting_allowed": False,
            "critical_path_phase": {
                "current_blocker": "approved_runtime_evidence_missing",
                "source_checker_primary_blocker": "approved_runtime_evidence_missing",
                "source_checker_next_blocker": None,
                "source_checker_status": "blocked",
                "source_checker_ready": False,
                "source_checker_accepted_for_internal_planning": False,
            },
            "route_lock": {
                "locked": True,
                "blocked_until": [
                    "approved_runtime_principal_lifecycle_evidence",
                    "reviewed_identity_public_contract",
                ],
            },
            "checks": [],
            "blockers": [],
        }
        for key, value in overrides.items():
            if key == "critical_path_phase" and isinstance(value, dict):
                payload["critical_path_phase"].update(value)
            elif key == "route_lock" and isinstance(value, dict):
                payload["route_lock"].update(value)
            else:
                payload[key] = value
        path.write_text(
            f"print({json.dumps(json.dumps(payload, sort_keys=True))})\n",
            encoding="utf-8",
        )
        return path

    def write_fake_resource_handle_checker(self, path: Path, **overrides: object) -> Path:
        payload = {
            "schema": "obelisk.object-identity-resource-handle-public-contract-readiness-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "planning_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_resource_handle_ready": False,
            "post_callback_resource_handle_ready": False,
            "blockers": [],
        }
        payload.update(overrides)
        path.write_text(
            f"print({json.dumps(json.dumps(payload, sort_keys=True))})\n",
            encoding="utf-8",
        )
        return path

    def write_fake_inventory_copied_signals_checker(self, path: Path, **overrides: object) -> Path:
        summary = {
            "allowed_signal_count": 5,
            "resource_kind_contract": "category-only metadata",
            "public_sdk_ready": False,
            "v1_completion_ready": False,
        }
        if isinstance(overrides.get("summary"), dict):
            summary.update(overrides.pop("summary"))  # type: ignore[arg-type]
        payload = {
            "schema": "obelisk.inventory-item-copied-signals-stability-check.v1",
            "ready": True,
            "surface": "obelisk.inventory_item_copied_signals.v1",
            "summary": summary,
            "blockers": [],
        }
        payload.update(overrides)
        path.write_text(
            f"print({json.dumps(json.dumps(payload, sort_keys=True))})\n",
            encoding="utf-8",
        )
        return path

    def write_fake_mission_accounting_checker(self, path: Path, payload: dict[str, object] | str) -> Path:
        if isinstance(payload, str):
            path.write_text(f"print({json.dumps(payload)})\n", encoding="utf-8")
        else:
            path.write_text(f"print({json.dumps(json.dumps(payload, sort_keys=True))})\n", encoding="utf-8")
        return path

    def write_fake_structure_census_checker(self, path: Path, **overrides: object) -> Path:
        accounting = {
            "mode": "candidate-only",
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "build_policy_ready": False,
            "public_structure_sdk_ready": False,
            "structure_identity_ready": False,
            "missing_public_gates": ["public-abi", "runtime-evidence"],
        }
        if isinstance(overrides.get("candidate_only_accounting"), dict):
            accounting.update(overrides.pop("candidate_only_accounting"))  # type: ignore[arg-type]
        payload = {
            "schema": "obelisk.structure-census-readiness-check.v1",
            "ready": True,
            "status": "candidate_ready",
            "outcome": "candidate-only",
            "accounting_mode": "candidate-only",
            "accepted_for_internal_planning": True,
            "offline_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "enforcement_ready": False,
            "candidate_only_accounting": accounting,
            "target_readiness": {"status": "second-source-accepted"},
            "blockers": [],
        }
        payload.update(overrides)
        path.write_text(
            f"print({json.dumps(json.dumps(payload, sort_keys=True))})\n",
            encoding="utf-8",
        )
        return path

    def write_fake_structure_build_policy_checker(self, path: Path, **overrides: object) -> Path:
        readiness_flags = {
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "enforcement_ready": False,
        }
        if isinstance(overrides.get("readiness_flags"), dict):
            readiness_flags.update(overrides.pop("readiness_flags"))  # type: ignore[arg-type]
        payload = {
            "schema": "obelisk.structure-build-policy-offline-intake-check.v1",
            "target_set": "structure_build_policy",
            "status": "accepted_for_offline_planning",
            "ready": True,
            "accepted_for_offline_planning": True,
            "planning_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "enforcement_ready": False,
            "readiness_flags": readiness_flags,
            "expected_status": "candidate",
            "blockers": [],
        }
        payload.update(overrides)
        path.write_text(
            f"print({json.dumps(json.dumps(payload, sort_keys=True))})\n",
            encoding="utf-8",
        )
        return path

    def test_secondary_report_scanner_rejects_completion_claims_without_blocker(self) -> None:
        for key in (
            "complete_sdk_ready",
            "complete_sdk_blockers_promoted_count",
            "complete_sdk_blockers_promoted_for_claim_count",
            "complete_sdk_blockers_promoted_for_claim_ratio",
            "complete_sdk_claim_progress_percent",
            "complete_sdk_claim_progress_ratio",
            "complete_sdk_allowed",
            "complete_sdk_progress_percent",
            "complete_sdk_progress_ratio",
            "full_api_supported",
            "p0_chain_promoted_count",
            "p0_chain_promoted_ratio",
            "p0_dependency_chain_promoted_for_claim_count",
            "p0_dependency_chain_promoted_for_claim_ratio",
            "package_shape_release_ready",
            "promoted_for_claim_ratio",
            "production_ready",
            "public_package_available",
            "public_abi_ready",
            "public_abi_available",
            "rc_ready",
            "release_candidate_ready",
            "release_package_ready",
            "release_ready",
            "release_grade",
            "release_grade_ready",
            "releaseGrade",
            "route_ready",
            "route_readiness_ready",
            "public_route_ready",
            "runtime_v1_ready",
            "sdk_ready",
            "sdkReady",
            "stable_sdk_allowed",
            "stable_v1_sdk",
            "stable_ready",
            "v1_stable_sdk",
            "v1_sdk_stable",
            "v1StableSdk",
            "v1_completion_ready",
            "stable_claim_allowed",
            "public_sdk_ready",
            "promotion_ready",
            "production_grade",
            "production_grade_ready",
            "productionGrade",
            "runtime_ready",
            "api_ready",
            "apiReady",
            "support_ready",
            "supportReady",
            "sdk_completion_progress_percent",
            "sdk_completion_progress_ratio",
            "v1_completion_progress_percent",
            "v1_completion_progress_ratio",
        ):
            with self.subTest(key=key):
                payload = {
                    "schema": "obelisk.secondary-report.v1",
                    "blockers": [],
                    "nested": [{"claim": {key: True}}],
                }

                claims = secondary_report_completion_claims_without_blocker(payload)

                self.assertEqual(claims, [f"nested[0].claim.{key}"])

    def test_secondary_report_scanner_rejects_numeric_completion_progress_without_blocker(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": [],
            "progress": {
                "complete_sdk_claim_progress_percent": 25,
                "complete_sdk_progress_percent": "25%",
                "promoted_for_claim_ratio": "1/12",
            },
            "zero_progress": {
                "complete_sdk_blockers_promoted_for_claim_count": 0,
                "p0_dependency_chain_promoted_for_claim_ratio": "0/4",
            },
        }

        self.assertEqual(
            secondary_report_completion_claims_without_blocker(payload),
            [
                "progress.complete_sdk_claim_progress_percent",
                "progress.complete_sdk_progress_percent",
                "progress.promoted_for_claim_ratio",
            ],
        )

    def test_secondary_report_scanner_rejects_structured_completion_aliases(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": [],
            "public_sdk": {"ready": True},
            "public_route": {"ready": True},
            "route": {"ready": True},
            "runtime": {"ready": "yes"},
            "stable_claim": {"allowed": True},
            "v1_completion": {"progress_ratio": "1/12"},
            "p0_dependency_chain": {"promoted_for_claim_count": 1},
        }

        self.assertEqual(
            secondary_report_completion_claims_without_blocker(payload),
            [
                "p0_dependency_chain.promoted_for_claim_count",
                "public_route.ready",
                "public_sdk.ready",
                "route.ready",
                "runtime.ready",
                "stable_claim.allowed",
                "v1_completion.progress_ratio",
            ],
        )

    def test_secondary_report_scanner_allows_positive_claim_when_report_has_blocker(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": ["public_sdk_gate_missing"],
            "nested": {"stable_claim_allowed": True},
        }

        self.assertEqual(secondary_report_completion_claims_without_blocker(payload), [])

    def test_secondary_report_scanner_rejects_nested_report_claim_without_nested_blocker(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": ["parent_report_blocked"],
            "nested_report": {
                "schema": "obelisk.nested-secondary-report.v1",
                "blockers": [],
                "stable_claim_allowed": True,
            },
        }

        self.assertEqual(
            secondary_report_completion_claims_without_blocker(payload),
            ["nested_report.stable_claim_allowed"],
        )

    def test_secondary_report_scanner_rejects_named_child_report_without_schema_or_blocker(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": ["parent_report_blocked"],
            "downstream_readiness_report": {
                "public_sdk": {"ready": True},
                "runtime": {"ready": True},
                "v1_completion": {"ready": True},
            },
            "summary": {
                "stable_claim": {"allowed": "yes"},
            },
            "nested": {"stable_claim_allowed": True},
        }

        self.assertEqual(
            secondary_report_completion_claims_without_blocker(payload),
            [
                "downstream_readiness_report.public_sdk.ready",
                "downstream_readiness_report.runtime.ready",
                "downstream_readiness_report.v1_completion.ready",
                "summary.stable_claim.allowed",
            ],
        )

    def test_secondary_report_scanner_rejects_secondary_records_without_local_blockers(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": ["parent_report_blocked"],
            "dependency_certificate": {"stable_claim_allowed": True},
            "manifest_record": {"public_sdk_ready": True},
            "release_statement": {"v1_stable_sdk": True},
            "side_lane_summary_section": {"support_ready": True},
        }

        self.assertEqual(
            secondary_report_completion_claims_without_blocker(payload),
            [
                "dependency_certificate.stable_claim_allowed",
                "manifest_record.public_sdk_ready",
                "release_statement.v1_stable_sdk",
                "side_lane_summary_section.support_ready",
            ],
        )

    def test_secondary_report_scanner_rejects_split_section_name_readiness_claims(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": [],
            "sections": [
                {"name": "Stable SDK", "status": "ready"},
                {"title": "Runtime readiness", "state": "available"},
                {"heading": "Installed SDK package", "result": "published"},
                {"label": "SDK support tier", "support_tier": "release-supported seed"},
            ],
        }

        self.assertEqual(
            secondary_report_completion_claims_without_blocker(payload),
            [
                "sections[0].status",
                "sections[1].state",
                "sections[2].result",
                "sections[3].support_tier",
            ],
        )

    def test_secondary_report_scanner_rejects_standalone_support_tier_claims(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": [],
            "route_side_lane_report": {
                "support_tier": "release-supported copied principal",
                "status": "release-supported seed",
            },
            "side_lane_summary": {
                "declared_support_tier": "release-supported seed",
            },
            "candidate_summary": {
                "support_tier": "candidate-only",
                "status": "candidate_ready",
            },
        }

        self.assertEqual(
            secondary_report_completion_claims_without_blocker(payload),
            [
                "route_side_lane_report.status",
                "route_side_lane_report.support_tier",
                "side_lane_summary.declared_support_tier",
            ],
        )

    def test_secondary_report_scanner_rejects_status_ready_under_completion_context(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": [],
            "sdk_release": {"status": "ready"},
            "public_route_report": {"state": "available"},
            "side_lane_report": {"status": "ready"},
            "candidate_summary": {"status": "ready"},
        }

        self.assertEqual(
            secondary_report_completion_claims_without_blocker(payload),
            [
                "public_route_report.state",
                "sdk_release.status",
            ],
        )

    def test_secondary_report_scanner_allows_split_section_claim_when_report_has_blocker(self) -> None:
        payload = {
            "schema": "obelisk.secondary-report.v1",
            "blockers": ["sdk_completion_gate_missing"],
            "sections": [
                {"name": "Stable SDK", "status": "ready", "blockers": ["stable_claim_blocked"]},
                {
                    "heading": "Installed SDK package",
                    "result": "published",
                    "blockers": ["package_publication_blocked"],
                },
            ],
        }

        self.assertEqual(secondary_report_completion_claims_without_blocker(payload), [])

    def test_route_gate_claim_scanner_rejects_structured_public_runtime_aliases(self) -> None:
        payload = {
            "schema": "obelisk.command-permission-route-gate-check.v1",
            "blockers": [],
            "public_sdk": {"ready": True},
            "public_route": {"ready": True},
            "route": {"ready": True},
            "runtime": {"ready": "ready"},
            "counts_toward": {
                "public_sdk": True,
                "runtime": True,
                "v1_completion": True,
            },
            "stable_claim": {"allowed": True},
        }

        self.assertEqual(
            command_permission_route_gate_public_or_runtime_claims(payload),
            [
                "counts_toward.public_sdk",
                "counts_toward.runtime",
                "counts_toward.v1_completion",
                "public_route.ready",
                "public_sdk.ready",
                "route.ready",
                "runtime.ready",
                "stable_claim.allowed",
            ],
        )

    def test_completion_gate_rejects_secondary_package_and_rc_claim_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            checker_path = self.write_fake_resource_handle_checker(
                Path(temp_dir) / "fake_resource_handle.py",
                nested={
                    "release_package_ready": True,
                    "release_candidate_ready": "ready",
                    "stable_sdk_allowed": True,
                },
            )
            result = self.run_checker(
                "--object-identity-resource-handle-readiness",
                str(checker_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER, payload["blockers"])
        self.assertEqual(
            payload["object_identity_resource_handle_readiness"]["completion_claims_without_blocker"],
            [
                "nested.release_candidate_ready",
                "nested.release_package_ready",
                "nested.stable_sdk_allowed",
            ],
        )
        self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_secondary_stable_claim_without_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            checker_path = self.write_fake_resource_handle_checker(
                Path(temp_dir) / "fake_resource_handle.py",
                nested={"stable_claim_allowed": True},
            )
            result = self.run_checker(
                "--object-identity-resource-handle-readiness",
                str(checker_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER, payload["blockers"])
        self.assertEqual(
            payload["object_identity_resource_handle_readiness"]["completion_claims_without_blocker"],
            ["nested.stable_claim_allowed"],
        )
        self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_nested_secondary_report_stable_claim_without_nested_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            checker_path = self.write_fake_resource_handle_checker(
                Path(temp_dir) / "fake_resource_handle.py",
                blockers=["parent_report_blocked"],
                nested_report={
                    "schema": "obelisk.nested-secondary-report.v1",
                    "blockers": [],
                    "stable_claim_allowed": True,
                },
            )
            result = self.run_checker(
                "--object-identity-resource-handle-readiness",
                str(checker_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn(SECONDARY_REPORT_COMPLETION_CLAIM_WITHOUT_BLOCKER, payload["blockers"])
        self.assertEqual(
            payload["object_identity_resource_handle_readiness"]["completion_claims_without_blocker"],
            ["nested_report.stable_claim_allowed"],
        )
        self.assertFalse(payload["stable_claim_allowed"])

    def test_inventory_copied_signals_contract_decision_manifest_is_required(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        surface_id = "obelisk.inventory_item_copied_signals.v1"
        filename = "inventory_item_copied_signals_public_contract_decisions.json"
        self.assertEqual(module.REQUIRED_PUBLIC_CONTRACT_DECISION_MANIFESTS[surface_id], filename)
        bridge_surface_id = "obelisk.command_principal_authz_response_bridge.v1"
        bridge_filename = "command_principal_authz_response_bridge_decisions.json"
        self.assertEqual(module.REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS[bridge_surface_id], bridge_filename)
        lifecycle_surface_id = "obelisk.command_copied_response_intent_lifecycle.planning.v1"
        lifecycle_filename = "command_copied_response_intent_lifecycle_planning_decisions.json"
        self.assertEqual(
            module.REQUIRED_PLANNING_GUARDRAIL_DECISION_MANIFESTS[lifecycle_surface_id],
            lifecycle_filename,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_dir = Path(temp_dir) / "docs"
            decisions_dir.mkdir()
            original_default = module.DEFAULT_CONTRACT_DECISIONS_DIR
            module.DEFAULT_CONTRACT_DECISIONS_DIR = decisions_dir
            try:
                missing = module.missing_required_contract_decision_manifests(decisions_dir)
                self.assertEqual(missing[surface_id], filename)
                self.assertEqual(missing[bridge_surface_id], bridge_filename)
                self.assertEqual(missing[lifecycle_surface_id], lifecycle_filename)

                (decisions_dir / filename).write_text(
                    json.dumps(
                        {
                            "surface": surface_id,
                            "decision": "copied_signal_only",
                            "public_header_allowed": True,
                            "blocked_public_contract": {
                                "standalone_inventory_sdk_allowed": False,
                                "standalone_items_sdk_allowed": False,
                                "forbidden_terms": [
                                    "lookup",
                                    "mutation",
                                    "return override",
                                ],
                            },
                            "v1_completion_contract": {
                                "claim_effect": "does_not_complete_v1_sdk",
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                missing = module.missing_required_contract_decision_manifests(decisions_dir)
                self.assertNotIn(surface_id, missing)
                self.assertIn(lifecycle_surface_id, missing)
                self.assertIn(bridge_surface_id, missing)

                (decisions_dir / lifecycle_filename).write_text(
                    json.dumps(
                        {
                            "surface": lifecycle_surface_id,
                            "status": "blocked",
                            "public_header_allowed": False,
                            "public_header_symbols_now": [],
                        }
                    ),
                    encoding="utf-8",
                )
                missing = module.missing_required_contract_decision_manifests(decisions_dir)
                self.assertNotIn(lifecycle_surface_id, missing)
                self.assertIn(bridge_surface_id, missing)

                (decisions_dir / bridge_filename).write_text(
                    json.dumps(
                        {
                            "surface": bridge_surface_id,
                            "status": "blocked",
                            "public_header_allowed": False,
                            "public_header_symbols_now": [],
                        }
                    ),
                    encoding="utf-8",
                )
                missing = module.missing_required_contract_decision_manifests(decisions_dir)
                self.assertNotIn(bridge_surface_id, missing)
            finally:
                module.DEFAULT_CONTRACT_DECISIONS_DIR = original_default

    def test_non_default_contract_decisions_dir_still_requires_manifests(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_dir = Path(temp_dir) / "custom-decisions"
            decisions_dir.mkdir()

            missing = module.missing_required_contract_decision_manifests(decisions_dir)

        self.assertEqual(
            missing,
            {
                **module.REQUIRED_PUBLIC_CONTRACT_DECISION_MANIFESTS,
                **module.REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS,
                **module.REQUIRED_PLANNING_GUARDRAIL_DECISION_MANIFESTS,
            },
        )

    def test_completion_gate_passes_selected_manifest_and_header_to_route_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manifest_path = temp_path / "custom-public-sdk-surfaces.json"
            header_path = temp_path / "CustomObeliskApi.h"
            route_gate_path = temp_path / "fake_route_gate.py"
            manifest_path.write_text(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            route_gate_path.write_text(
                "import json\n"
                "import sys\n"
                f"expected_manifest = {str(manifest_path)!r}\n"
                f"expected_header = {str(header_path)!r}\n"
                "argv = sys.argv[1:]\n"
                "ok = (\n"
                "    '--public-sdk-surfaces' in argv\n"
                "    and argv[argv.index('--public-sdk-surfaces') + 1] == expected_manifest\n"
                "    and '--public-header' in argv\n"
                "    and argv[argv.index('--public-header') + 1] == expected_header\n"
                "    and '--json' in argv\n"
                ")\n"
                "payload = {\n"
                "    'schema': 'obelisk.command-permission-route-gate-check.v1',\n"
                "    'valid': ok,\n"
                "    'accepted_for_planning': True,\n"
                "    'planning_only': True,\n"
                "    'promotion_ready': False,\n"
                "    'public_sdk_ready': False,\n"
                "    'public_abi_ready': False,\n"
                "    'runtime_ready': False,\n"
                "    'public_header_allowed': False,\n"
                "    'counts_toward_public_sdk': False,\n"
                "    'counts_toward_runtime': False,\n"
                "    'counts_toward_v1_completion': False,\n"
                "    'public_or_runtime_accounting_allowed': False,\n"
                "    'critical_path_phase': {\n"
                "        'current_blocker': 'approved_runtime_evidence_missing',\n"
                "        'source_checker_primary_blocker': 'approved_runtime_evidence_missing',\n"
                "        'source_checker_next_blocker': None,\n"
                "        'source_checker_status': 'blocked',\n"
                "        'source_checker_ready': False,\n"
                "        'source_checker_accepted_for_internal_planning': False,\n"
                "    },\n"
                "    'route_lock': {\n"
                "        'locked': True,\n"
                "        'blocked_until': [\n"
                "            'approved_runtime_principal_lifecycle_evidence',\n"
                "            'reviewed_identity_public_contract',\n"
                "        ],\n"
                "    },\n"
                "    'checks': [],\n"
                "    'blockers': [] if ok else ['argv_mismatch'],\n"
                "}\n"
                "print(json.dumps(payload, sort_keys=True))\n"
                "sys.exit(0 if ok else 1)\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertNotIn("command_permission_route_gate_invalid", payload["blockers"])
        self.assertNotIn("command_permission_route_gate_blockers_not_empty", payload["blockers"])
        self.assertTrue(payload["command_permission_route_gate"]["valid"])

    def test_completion_gate_rejects_identity_public_contract_blocker_without_runtime_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(
                Path(temp_dir) / "fake_route_gate.py",
                critical_path_phase={
                    "current_blocker": "identity_public_contract_gate_missing",
                    "source_checker_primary_blocker": "identity_public_contract_gate_missing",
                    "source_checker_next_blocker": None,
                    "source_checker_status": "blocked",
                    "source_checker_ready": False,
                    "source_checker_accepted_for_internal_planning": False,
                },
                route_lock={
                    "locked": True,
                    "blocked_until": ["reviewed_identity_public_contract"],
                },
            )
            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        route_gate = payload["command_permission_route_gate"]
        progress = payload["v1_sdk_progress"]

        self.assertEqual(result.returncode, 1)
        self.assertFalse(route_gate["completion_gate_accepted"])
        self.assertIn("command_permission_route_gate_default_blocker_mismatch", payload["blockers"])
        self.assertIn("command_permission_route_gate_default_source_blocker_mismatch", payload["blockers"])
        self.assertIn(
            "command_permission_route_gate_default_lock_blocked_until_unexpected",
            payload["blockers"],
        )
        self.assertEqual(route_gate["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(route_gate["source_checker_primary_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(route_gate["route_lock_blocked_until"], ["reviewed_identity_public_contract"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["stable_release_contract_claim_allowed"])
        self.assertEqual(progress["completion_blockers_promoted_count"], 0)
        self.assertEqual(progress["p0_chain_promoted_count"], 0)
        self.assertEqual(progress["complete_sdk_claim_progress_percent"], 0)
        self.assertEqual(progress["route_gate_non_counting_blockers"], [])
        self.assertEqual(progress["route_gate_non_counting_surfaces"], [])
        self.assertEqual(progress["p0_manifest_promoted_non_counting"], [])
        sections = payload["v1_sdk_report_sections"]
        self.assertEqual(
            sections["runtime_required_blockers"]["route_gate_current_blockers"],
            ["identity_public_contract_gate_missing"],
        )
        self.assertEqual(
            sections["next_v1_work"]["route_gate_current_blockers"],
            ["identity_public_contract_gate_missing"],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["next_v1_work"]["recommended_next_action"],
            (
                "review the player identity public contract before any public identity, "
                "permissions/admin, command response, or commands/replies ABI; approved copied "
                "runtime principal lifecycle evidence is only a contract-review input"
            ),
        )
        self.assertNotIn(
            "produce approved runtime principal lifecycle evidence",
            payload["v1_sdk_report_sections"]["next_v1_work"]["recommended_next_action"],
        )
        for row in payload["v1_sdk_blocker_outcomes"]:
            if row["surface"] in payload["v1_required_dependency_chain"]:
                self.assertFalse(row["route_gate_claim_satisfied"], row)
                self.assertTrue(row["unresolved_for_complete_sdk_claim"], row)

    def test_completion_gate_accepts_identity_public_contract_blocker_with_approved_runtime_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(
                Path(temp_dir) / "fake_route_gate.py",
                critical_path_phase={
                    "current_blocker": "identity_public_contract_gate_missing",
                    "source_checker_primary_blocker": "identity_public_contract_gate_missing",
                    "source_checker_next_blocker": None,
                    "source_checker_status": "blocked",
                    "source_checker_ready": False,
                    "source_checker_accepted_for_internal_planning": False,
                },
                route_lock={
                    "locked": True,
                    "blocked_until": ["reviewed_identity_public_contract"],
                },
                checks=[
                    {
                        "name": "player_identity_public_contract_gap",
                        "argv": [
                            "check_player_identity_public_contract_gap_report.py",
                            "--approved-runtime-evidence",
                            str(Path(temp_dir) / "approved-runtime-principal-lifecycle.json"),
                        ],
                    }
                ],
            )
            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        route_gate = payload["command_permission_route_gate"]
        progress = payload["v1_sdk_progress"]

        self.assertEqual(result.returncode, 1)
        self.assertTrue(route_gate["completion_gate_accepted"])
        self.assertEqual(route_gate["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(route_gate["source_checker_primary_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(route_gate["route_lock_blocked_until"], ["reviewed_identity_public_contract"])
        self.assertFalse(route_gate["counts_toward_public_sdk"])
        self.assertFalse(route_gate["counts_toward_runtime"])
        self.assertFalse(route_gate["counts_toward_v1_completion"])
        self.assertFalse(route_gate["public_or_runtime_accounting_allowed"])
        self.assertNotIn("command_permission_route_gate_default_blocker_mismatch", payload["blockers"])
        self.assertNotIn("command_permission_route_gate_default_source_blocker_mismatch", payload["blockers"])
        self.assertNotIn("command_permission_route_gate_default_lock_blocked_until_unexpected", payload["blockers"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["stable_release_contract_claim_allowed"])
        self.assertEqual(progress["completion_blockers_promoted_count"], 0)
        self.assertEqual(progress["p0_chain_promoted_count"], 0)
        self.assertEqual(progress["complete_sdk_claim_progress_percent"], 0)
        self.assertEqual(
            payload["v1_sdk_report_sections"]["runtime_required_blockers"]["route_gate_current_blockers"],
            ["identity_public_contract_gate_missing"],
        )

    def test_completion_gate_binds_executed_test_artifacts_to_selected_manifest_and_header(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="ActiveManifestBinding") as core_dir:
            root = Path(core_dir)
            evidence = self.write_player_identity_structured_promotion_artifacts(root)
            manifest_path = root / "custom-public-sdk-surfaces.json"
            header_path = root / "CustomObeliskApi.h"
            header_path.write_text("#pragma once\n#define OBELISK_CUSTOM_HEADER 1\n", encoding="utf-8")
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["evidence"] = evidence
                    break
            if "obelisk.player_identity.v1" not in manifest["promoted_surfaces"]:
                manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            if "obelisk.player_identity.v1" in manifest["planning_surfaces"]:
                manifest["planning_surfaces"].remove("obelisk.player_identity.v1")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            build_policy_checker = self.write_fake_structure_build_policy_checker(
                root / "fake_structure_build_policy.py"
            )

            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--structure-build-policy-offline-intake",
                str(build_policy_checker),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        missing = payload["promoted_surfaces_missing_structured_evidence"]["obelisk.player_identity.v1"]
        self.assertIn("promoted_surface_structured_evidence_missing", payload["blockers"])
        self.assertIn("executed_test_report:inputs.public_sdk_surfaces_path_invalid", missing)
        self.assertIn("executed_test_report:inputs.public_sdk_surfaces_sha256_mismatch", missing)
        self.assertIn("executed_test_report:inputs.public_header_path_invalid", missing)
        self.assertIn("executed_test_report:inputs.public_header_sha256_mismatch", missing)
        self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_non_default_route_gate_without_test_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(Path(temp_dir) / "fake_route_gate.py")

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_override_not_allowed", payload["blockers"])
        self.assertFalse(payload["command_permission_route_gate"]["override_allowed"])

    def test_current_manifest_fails_closed_for_v1_completion(self) -> None:
        result = self.run_checker("--json", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["schema"], "obelisk.public-sdk-v1-completion-check.v1")
        self.assertFalse(payload["ready"])
        self.assertIn("stable_release_contract_claim_not_allowed", payload["blockers"])
        self.assertIn("v1_completion_required_false", payload["blockers"])
        self.assertIn("promoted_experimental_surfaces_unresolved", payload["blockers"])
        self.assertIn("v1_sdk_completion_blockers_unresolved", payload["blockers"])
        self.assertNotIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        self.assertEqual(payload["blocked_public_contract_header_symbols"], {})
        self.assertNotIn("required_public_contract_decision_manifest_missing", payload["blockers"])
        self.assertEqual(payload["missing_required_public_contract_decision_manifests"], {})
        self.assertNotIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["unresolved_completion_blockers"])
        self.assertIn("obelisk.gameplay_policy_event.v1", payload["unresolved_experimental_surfaces"])
        inventory_stability = payload["inventory_copied_signals_stability"]
        self.assertEqual(
            inventory_stability["schema"],
            "obelisk.inventory-item-copied-signals-stability-check.v1",
        )
        self.assertTrue(inventory_stability["ready"])
        self.assertEqual(inventory_stability["allowed_signal_count"], 5)
        self.assertEqual(inventory_stability["resource_kind_contract"], "category-only metadata")
        self.assertFalse(inventory_stability["public_sdk_ready"])
        self.assertFalse(inventory_stability["v1_completion_ready"])
        self.assertNotIn("inventory_copied_signals_stability_invalid", payload["blockers"])
        resource_handle_readiness = payload["object_identity_resource_handle_readiness"]
        self.assertEqual(
            resource_handle_readiness["schema"],
            "obelisk.object-identity-resource-handle-public-contract-readiness-check.v1",
        )
        self.assertTrue(resource_handle_readiness["valid"])
        self.assertTrue(resource_handle_readiness["accepted_for_planning"])
        self.assertTrue(resource_handle_readiness["planning_only"])
        self.assertFalse(resource_handle_readiness["promotion_ready"])
        self.assertFalse(resource_handle_readiness["public_sdk_ready"])
        self.assertFalse(resource_handle_readiness["runtime_ready"])
        self.assertFalse(resource_handle_readiness["public_resource_handle_ready"])
        self.assertFalse(resource_handle_readiness["post_callback_resource_handle_ready"])
        self.assertEqual(resource_handle_readiness["public_or_runtime_claims"], [])
        self.assertEqual(resource_handle_readiness["blockers"], [])
        self.assertNotIn("object_identity_resource_handle_readiness_invalid", payload["blockers"])
        self.assertNotIn("object_identity_resource_handle_public_or_runtime_claims", payload["blockers"])
        mission_accounting = payload["mission_transfer_dino_tribe_outcome_accounting"]
        self.assertEqual(
            mission_accounting["schema"],
            "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1",
        )
        self.assertEqual(mission_accounting["surface"], "obelisk.mission_transfer_dino_tribe.v1")
        self.assertTrue(mission_accounting["ready"])
        self.assertEqual(mission_accounting["accounting_route"], "candidate_only")
        self.assertTrue(mission_accounting["candidate_only"])
        self.assertFalse(mission_accounting["v1_accounted"])
        self.assertFalse(mission_accounting["promotion_ready"])
        self.assertFalse(mission_accounting["public_sdk_ready"])
        self.assertFalse(mission_accounting["runtime_ready"])
        self.assertEqual(
            set(mission_accounting["missing_leaf_families"]),
            {"mission", "transfer", "dino_policy", "tribe_policy", "buff_status"},
        )
        self.assertNotIn("mission_transfer_dino_tribe_outcome_accounting_invalid", payload["blockers"])
        structure_census = payload["structure_census_readiness"]
        self.assertEqual(structure_census["schema"], "obelisk.structure-census-readiness-check.v1")
        self.assertTrue(structure_census["ready"])
        self.assertEqual(structure_census["status"], "candidate_ready")
        self.assertEqual(structure_census["accounting_mode"], "candidate-only")
        self.assertTrue(structure_census["accepted_for_internal_planning"])
        self.assertTrue(structure_census["offline_only"])
        self.assertFalse(structure_census["promotion_ready"])
        self.assertFalse(structure_census["public_sdk_ready"])
        self.assertFalse(structure_census["runtime_ready"])
        self.assertFalse(structure_census["enforcement_ready"])
        self.assertEqual(structure_census["second_source_status"], "accepted")
        self.assertNotIn("structure_census_readiness_invalid", payload["blockers"])
        structure_build_policy = payload["structure_build_policy_offline_intake"]
        self.assertEqual(
            structure_build_policy["schema"],
            "obelisk.structure-build-policy-offline-intake-check.v1",
        )
        self.assertTrue(structure_build_policy["ready"])
        self.assertEqual(structure_build_policy["status"], "accepted_planning_only")
        self.assertTrue(structure_build_policy["planning_only"])
        self.assertFalse(structure_build_policy["promotion_ready"])
        self.assertFalse(structure_build_policy["public_sdk_ready"])
        self.assertFalse(structure_build_policy["runtime_ready"])
        self.assertFalse(structure_build_policy["enforcement_ready"])
        self.assertEqual(structure_build_policy["blockers"], [])
        self.assertNotIn("structure_build_policy_offline_intake_invalid", payload["blockers"])
        self.assertNotIn("structure_build_policy_offline_intake_blockers_not_empty", payload["blockers"])
        route_gate = payload["command_permission_route_gate"]
        self.assertEqual(route_gate["current_blocker"], "approved_runtime_evidence_missing")
        self.assertFalse(route_gate["counts_toward_public_sdk"])
        self.assertFalse(route_gate["counts_toward_runtime"])
        self.assertFalse(route_gate["counts_toward_v1_completion"])
        self.assertFalse(route_gate["public_or_runtime_accounting_allowed"])
        self.assertEqual(
            route_gate["source_checker_primary_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            route_gate["route_lock_blocked_until"],
            ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"],
        )
        progress = payload["v1_sdk_progress"]
        self.assertEqual(progress["completion_blocker_total"], 12)
        self.assertEqual(progress["completion_blockers_promoted_count"], 0)
        self.assertEqual(progress["p0_chain_total"], 4)
        self.assertEqual(progress["p0_chain_promoted_count"], 0)
        self.assertEqual(progress["complete_sdk_claim_progress_percent"], 0)
        self.assertNotIn(
            "obelisk.permissions_admin.v1",
            progress["completion_blockers_with_post_v1_or_excluded_outcome"],
        )
        self.assertIn(
            "bookkeeping only",
            progress["completion_blockers_with_post_v1_or_excluded_outcome_note"],
        )
        self.assertEqual(
            progress["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
            progress["completion_blockers_with_post_v1_or_excluded_outcome"],
        )
        self.assertEqual(
            progress["completion_blockers_with_release_statement_post_v1_or_excluded_outcome"],
            [],
        )
        self.assertEqual(
            progress["completion_blockers_with_release_statement_post_v1_or_excluded_outcome_count"],
            0,
        )
        self.assertIn("obelisk.player_identity.v1", progress["completion_blockers_without_manifest_outcome"])
        self.assertEqual(progress["completion_blockers_without_manifest_outcome_count"], 5)
        self.assertGreaterEqual(progress["unresolved_completion_blocker_count"], 5)
        self.assertFalse(progress["stable_claim_allowed"])
        self.assertIn("status accounting", progress["outcome_accounting_note"])
        self.assertIn("never contribute percentage", progress["outcome_accounting_note"])
        self.assertIn("accounting only", progress["non_claim"])
        self.assertIn("core-first release readiness", " ".join(payload["non_claims"]))
        self.assertEqual(progress["manifest_outcome_missing_count"], 5)
        self.assertEqual(progress["release_statement_outcome_missing_count"], 7)
        self.assertEqual(progress["dependency_chain_remaining_count"], 4)
        self.assertEqual(payload["v1_sdk_blocker_outcome_summary"]["total"], 12)
        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"]["manifest_outcome_missing"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
                "obelisk.mission_transfer_dino_tribe.v1",
            ],
        )

        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"]["release_statement_outcome_missing"],
            [
                "obelisk.inventory_items_mutation.v1",
                "obelisk.object_identity_resource_handle.v1",
                "obelisk.structure_census.v1",
                "obelisk.lifecycle_ops_recovery.v1",
                "obelisk.player_services_economy_mobility.v1",
                "obelisk.operator_ingress_storage.v1",
                "obelisk.gameplay_tick_callbacks.v1",
            ],
        )
        blocker_rows = payload["v1_sdk_blocker_outcomes"]
        self.assertEqual(len(blocker_rows), 12)
        self.assertTrue(all(row["unresolved_for_complete_sdk_claim"] for row in blocker_rows))
        self.assertTrue(all("non_claim" in row for row in blocker_rows))
        self.assertEqual(blocker_rows[0]["surface"], "obelisk.player_identity.v1")
        self.assertIsNone(blocker_rows[0]["manifest_outcome"])
        self.assertIn("priority dependency-chain blocker", blocker_rows[0]["next_action"])
        self.assertEqual(blocker_rows[1]["surface"], "obelisk.permissions_admin.v1")
        self.assertIsNone(blocker_rows[1]["manifest_outcome"])
        self.assertIsNone(blocker_rows[1]["release_statement_outcome"])
        self.assertFalse(blocker_rows[1]["release_statement_contract_satisfied"])
        sections = payload["v1_sdk_report_sections"]
        self.assertEqual(
            set(sections),
            {
                "no_live_progress",
                "release_statement_bookkeeping",
                "promoted_demand_gaps",
                "active_side_lane_review",
                "runtime_required_blockers",
                "next_v1_work",
            },
        )
        self.assertFalse(sections["no_live_progress"]["live_server_required_for_this_report"])
        self.assertFalse(sections["no_live_progress"]["stable_claim_allowed"])
        self.assertIn("no-live inventory/package-shape progress", sections["no_live_progress"]["non_claim"])
        self.assertEqual(
            sections["release_statement_bookkeeping"]["manifest_post_v1_or_excluded_outcomes"],
            progress["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
        )
        self.assertEqual(
            sections["release_statement_bookkeeping"]["release_statement_post_v1_or_excluded_outcomes"],
            [],
        )
        self.assertEqual(
            sections["release_statement_bookkeeping"]["missing_blocker_outcomes"],
            payload["release_statement_missing_blocker_outcomes"],
        )
        self.assertIn("bookkeeping alone never approves", sections["release_statement_bookkeeping"]["non_claim"])
        self.assertEqual(
            sections["runtime_required_blockers"]["route_gate_current_blockers"],
            ["approved_runtime_evidence_missing"],
        )
        self.assertEqual(
            sections["next_v1_work"]["route_gate_current_blockers"],
            ["approved_runtime_evidence_missing"],
        )
        self.assertEqual(payload["player_identity_request_pack_non_evidence_terms_missing"], [])
        self.assertEqual(
            sections["promoted_demand_gaps"]["minimum_promoted_demand_family_gaps"],
            payload["minimum_promoted_demand_family_gaps"],
        )
        self.assertFalse(
            sections["promoted_demand_gaps"]["all_minimum_demand_families_promoted_or_equivalent"]
        )
        self.assertTrue(sections["promoted_demand_gaps"]["claim_blocker_active"])
        self.assertIn(
            "Excluded/post-v1 outcomes do not satisfy",
            sections["promoted_demand_gaps"]["non_claim"],
        )
        expected_active_side_lanes = [
            "obelisk.lifecycle_ops_recovery.v1",
            "obelisk.player_services_economy_mobility.v1",
            "obelisk.operator_ingress_storage.v1",
            "obelisk.gameplay_tick_callbacks.v1",
        ]
        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"]["active_side_lane_review_blockers"],
            expected_active_side_lanes,
        )
        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"][
                "active_side_lane_review_manifest_post_v1_or_excluded"
            ],
            expected_active_side_lanes,
        )
        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"][
                "active_side_lane_review_release_statement_post_v1_or_excluded"
            ],
            [],
        )
        self.assertEqual(
            progress["active_side_lane_review_promoted_for_claim_count"],
            0,
        )
        self.assertEqual(
            progress["active_side_lane_review_remaining_for_claim_count"],
            4,
        )
        self.assertEqual(
            progress["active_side_lane_review_remaining_for_claim"],
            expected_active_side_lanes,
        )
        self.assertEqual(
            sections["active_side_lane_review"]["promoted_for_claim_count"],
            0,
        )
        self.assertEqual(
            sections["active_side_lane_review"]["remaining_for_claim"],
            expected_active_side_lanes,
        )
        self.assertFalse(sections["active_side_lane_review"]["stable_claim_allowed"])
        self.assertIn("non-claim accounting", sections["active_side_lane_review"]["non_claim"])
        self.assertEqual(
            sections["runtime_required_blockers"]["manifest_outcome_missing"],
            payload["v1_sdk_blocker_outcome_summary"]["manifest_outcome_missing"],
        )
        self.assertEqual(
            sections["runtime_required_blockers"]["dependency_chain_remaining"],
            payload["v1_sdk_blocker_outcome_summary"]["dependency_chain_remaining"],
        )
        self.assertIn(
            "v1_sdk_completion_blockers_unresolved",
            sections["runtime_required_blockers"]["blocker_codes"],
        )
        self.assertEqual(
            sections["next_v1_work"]["critical_path"],
            payload["v1_sdk_blocker_outcome_summary"]["dependency_chain_remaining"],
        )
        self.assertEqual(
            sections["next_v1_work"]["product_decision_required"],
            payload["v1_sdk_blocker_outcome_summary"]["manifest_outcome_missing"],
        )
        self.assertEqual(
            sections["next_v1_work"]["release_statement_bookkeeping_required"],
            payload["release_statement_missing_blocker_outcomes"],
        )
        self.assertIn(
            "approved copied runtime principal lifecycle evidence",
            sections["next_v1_work"]["recommended_next_action"],
        )
        self.assertNotIn("supply bound", sections["next_v1_work"]["recommended_next_action"])
        self.assertIn("prioritizes work only", sections["next_v1_work"]["non_claim"])

    def test_inventory_copied_signal_stability_checker_is_required(self) -> None:
        result = self.run_checker(
            "--inventory-copied-signals-stability",
            "/tmp/obelisk-missing-inventory-copied-signals-checker.py",
            "--json",
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("inventory_copied_signals_stability_output_invalid", payload["blockers"])
        self.assertEqual(
            payload["inventory_copied_signals_stability"]["path"],
            "/tmp/obelisk-missing-inventory-copied-signals-checker.py",
        )
        self.assertEqual(payload["inventory_copied_signals_stability"]["exit_code"], 2)

    def test_completion_gate_rejects_inventory_copied_signal_overclaims(self) -> None:
        cases = (
            ({"summary": {"public_sdk_ready": True}}, "inventory_copied_signals_public_sdk_ready_not_false"),
            ({"summary": {"v1_completion_ready": True}}, "inventory_copied_signals_v1_completion_ready_not_false"),
            ({"summary": {"public_abi_ready": True}}, "inventory_copied_signals_public_or_runtime_claims"),
            ({"summary": {"stable_claim_allowed": True}}, "inventory_copied_signals_public_or_runtime_claims"),
            ({"stable_claim_allowed": True}, "inventory_copied_signals_public_or_runtime_claims"),
            ({"blockers": ["copied_signal_boundary_failed"]}, "inventory_copied_signals_stability_blockers_not_empty"),
        )
        for overrides, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_inventory_copied_signals_checker(
                        Path(temp_dir) / "fake_inventory_copied_signals.py",
                        **overrides,
                    )
                    result = self.run_checker(
                        "--inventory-copied-signals-stability",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, payload["blockers"])
                self.assertFalse(payload["stable_claim_allowed"])

    def test_resource_handle_readiness_checker_is_required(self) -> None:
        result = self.run_checker(
            "--object-identity-resource-handle-readiness",
            "/tmp/obelisk-missing-resource-handle-readiness-checker.py",
            "--json",
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("object_identity_resource_handle_readiness_output_invalid", payload["blockers"])
        self.assertEqual(
            payload["object_identity_resource_handle_readiness"]["path"],
            "/tmp/obelisk-missing-resource-handle-readiness-checker.py",
        )
        self.assertEqual(payload["object_identity_resource_handle_readiness"]["exit_code"], 2)

    def test_mission_transfer_dino_tribe_accounting_checker_is_required(self) -> None:
        result = self.run_checker(
            "--mission-transfer-dino-tribe-outcome-accounting",
            "/tmp/obelisk-missing-mission-transfer-dino-tribe-checker.py",
            "--json",
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("mission_transfer_dino_tribe_outcome_accounting_output_invalid", payload["blockers"])
        self.assertEqual(
            payload["mission_transfer_dino_tribe_outcome_accounting"]["path"],
            "/tmp/obelisk-missing-mission-transfer-dino-tribe-checker.py",
        )
        self.assertEqual(payload["mission_transfer_dino_tribe_outcome_accounting"]["exit_code"], 2)

    def test_structure_census_readiness_checker_is_required(self) -> None:
        result = self.run_checker(
            "--structure-census-readiness",
            "/tmp/obelisk-missing-structure-census-readiness-checker.py",
            "--json",
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("structure_census_readiness_output_invalid", payload["blockers"])
        self.assertEqual(
            payload["structure_census_readiness"]["path"],
            "/tmp/obelisk-missing-structure-census-readiness-checker.py",
        )
        self.assertEqual(payload["structure_census_readiness"]["exit_code"], 2)

    def test_structure_build_policy_offline_intake_checker_is_required(self) -> None:
        result = self.run_checker(
            "--structure-build-policy-offline-intake",
            "/tmp/obelisk-missing-structure-build-policy-offline-intake-checker.py",
            "--json",
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("structure_build_policy_offline_intake_output_invalid", payload["blockers"])
        self.assertEqual(
            payload["structure_build_policy_offline_intake"]["path"],
            "/tmp/obelisk-missing-structure-build-policy-offline-intake-checker.py",
        )
        self.assertEqual(payload["structure_build_policy_offline_intake"]["exit_code"], 2)

    def test_completion_gate_rejects_structure_census_public_runtime_overclaims(self) -> None:
        cases = (
            ("promotion_ready", True, "structure_census_promotion_ready_not_false"),
            ("public_sdk_ready", True, "structure_census_public_sdk_ready_not_false"),
            ("runtime_ready", True, "structure_census_runtime_ready_not_false"),
            ("enforcement_ready", True, "structure_census_enforcement_ready_not_false"),
            ("public_abi_ready", True, "structure_census_public_or_runtime_claims"),
            ("v1_completion_ready", True, "structure_census_public_or_runtime_claims"),
            ("stable_claim_allowed", True, "structure_census_public_or_runtime_claims"),
            (
                "candidate_only_accounting",
                {"public_structure_sdk_ready": True},
                "structure_census_accounting_public_structure_sdk_ready_not_false",
            ),
            (
                "candidate_only_accounting",
                {"public_abi_ready": True},
                "structure_census_public_or_runtime_claims",
            ),
            (
                "second_source_readiness",
                {"stable_claim_allowed": True},
                "structure_census_public_or_runtime_claims",
            ),
        )
        for key, value, expected in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_structure_census_checker(
                        Path(temp_dir) / "fake_structure_census.py",
                        **{key: value},
                    )
                    result = self.run_checker(
                        "--structure-census-readiness",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, payload["blockers"])
                self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_structure_census_invalid_or_blocking_report(self) -> None:
        cases = (
            ({"schema": "wrong-schema"}, "structure_census_readiness_schema_mismatch"),
            ({"ready": False}, "structure_census_readiness_invalid"),
            ({"accepted_for_internal_planning": False}, "structure_census_readiness_not_offline_planning"),
            ({"offline_only": False}, "structure_census_readiness_not_offline_planning"),
            ({"blockers": ["structure_public_gate_missing"]}, "structure_census_readiness_blockers_not_empty"),
        )
        for overrides, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_structure_census_checker(
                        Path(temp_dir) / "fake_structure_census.py",
                        **overrides,
                    )
                    result = self.run_checker(
                        "--structure-census-readiness",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, payload["blockers"])
                self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_structure_build_policy_public_runtime_overclaims(self) -> None:
        cases = (
            ("promotion_ready", True, "structure_build_policy_promotion_ready_not_false"),
            ("public_sdk_ready", True, "structure_build_policy_public_sdk_ready_not_false"),
            ("runtime_ready", True, "structure_build_policy_runtime_ready_not_false"),
            ("enforcement_ready", True, "structure_build_policy_enforcement_ready_not_false"),
            ("public_abi_ready", True, "structure_build_policy_public_or_runtime_claims"),
            ("v1_completion_ready", True, "structure_build_policy_public_or_runtime_claims"),
            ("stable_claim_allowed", True, "structure_build_policy_public_or_runtime_claims"),
            (
                "readiness_flags",
                {"public_sdk_ready": True},
                "structure_build_policy_readiness_flags_public_sdk_ready_not_false",
            ),
            (
                "readiness_flags",
                {"v1_completion_ready": True},
                "structure_build_policy_public_or_runtime_claims",
            ),
            (
                "summary",
                {"stable_claim_allowed": True},
                "structure_build_policy_public_or_runtime_claims",
            ),
        )
        for key, value, expected in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_structure_build_policy_checker(
                        Path(temp_dir) / "fake_structure_build_policy.py",
                        **{key: value},
                    )
                    result = self.run_checker(
                        "--structure-build-policy-offline-intake",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, payload["blockers"])
                self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_structure_build_policy_invalid_or_blocking_report(self) -> None:
        cases = (
            ({"schema": "wrong-schema"}, "structure_build_policy_offline_intake_schema_mismatch"),
            ({"ready": False}, "structure_build_policy_offline_intake_invalid"),
            ({"planning_only": False}, "structure_build_policy_offline_intake_not_planning_only"),
            (
                {"blockers": ["forbidden_string_claim"]},
                "structure_build_policy_offline_intake_blockers_not_empty",
            ),
        )
        for overrides, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_structure_build_policy_checker(
                        Path(temp_dir) / "fake_structure_build_policy.py",
                        **overrides,
                    )
                    result = self.run_checker(
                        "--structure-build-policy-offline-intake",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, payload["blockers"])
                self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_mission_accounting_public_runtime_overclaims(self) -> None:
        base = {
            "schema": "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1",
            "surface": "obelisk.mission_transfer_dino_tribe.v1",
            "ready": True,
            "accounting_route": "candidate_only",
            "candidate_only": True,
            "v1_accounted": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "required_leaves": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "observed_leaves": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "missing_leaf_families": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "blockers": [],
        }
        cases = (
            ("promotion_ready", "mission_transfer_dino_tribe_promotion_ready_not_false"),
            ("public_sdk_ready", "mission_transfer_dino_tribe_public_sdk_ready_not_false"),
            ("runtime_ready", "mission_transfer_dino_tribe_runtime_ready_not_false"),
            ("public_abi_ready", "mission_transfer_dino_tribe_public_or_runtime_claims"),
            ("v1_completion_ready", "mission_transfer_dino_tribe_public_or_runtime_claims"),
            ("stable_claim_allowed", "mission_transfer_dino_tribe_public_or_runtime_claims"),
            ("summary", "mission_transfer_dino_tribe_public_or_runtime_claims"),
        )
        for key, expected in cases:
            with self.subTest(key=key):
                payload = dict(base)
                payload[key] = {"stable_claim_allowed": True} if key == "summary" else True
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_mission_accounting_checker(
                        Path(temp_dir) / "fake_mission_accounting.py",
                        payload,
                    )
                    result = self.run_checker(
                        "--mission-transfer-dino-tribe-outcome-accounting",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, report["blockers"])
                self.assertFalse(report["stable_claim_allowed"])

    def test_completion_gate_rejects_fake_mission_per_leaf_promoted_summary_without_manifest_evidence(self) -> None:
        payload = {
            "schema": "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1",
            "surface": "obelisk.mission_transfer_dino_tribe.v1",
            "ready": True,
            "accounting_route": "per_leaf_promoted",
            "candidate_only": False,
            "v1_accounted": True,
            "promotion_ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "required_leaves": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "observed_leaves": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "missing_leaf_families": [],
            "blockers": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            checker_path = self.write_fake_mission_accounting_checker(
                Path(temp_dir) / "fake_mission_accounting.py",
                payload,
            )
            result = self.run_checker(
                "--mission-transfer-dino-tribe-outcome-accounting",
                str(checker_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "mission_transfer_dino_tribe_per_leaf_promotion_evidence_unverified",
            report["blockers"],
        )
        self.assertFalse(
            report["mission_transfer_dino_tribe_outcome_accounting"][
                "manifest_leaf_promotion_evidence_verified"
            ]
        )
        self.assertFalse(report["stable_claim_allowed"])

    def test_completion_gate_rejects_mission_per_leaf_promoted_public_header_overclaims(self) -> None:
        payload = {
            "schema": "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1",
            "surface": "obelisk.mission_transfer_dino_tribe.v1",
            "ready": True,
            "accounting_route": "per_leaf_promoted",
            "candidate_only": False,
            "v1_accounted": True,
            "promotion_ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "public_header_allowed": True,
            "public_header_ready": True,
            "claim": "public header is ready",
            "required_leaves": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "observed_leaves": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "missing_leaf_families": [],
            "blockers": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            checker_path = self.write_fake_mission_accounting_checker(
                Path(temp_dir) / "fake_mission_accounting.py",
                payload,
            )
            result = self.run_checker(
                "--mission-transfer-dino-tribe-outcome-accounting",
                str(checker_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("mission_transfer_dino_tribe_public_or_runtime_claims", report["blockers"])
        self.assertIn(
            "mission_transfer_dino_tribe_per_leaf_promotion_evidence_unverified",
            report["blockers"],
        )
        self.assertFalse(report["stable_claim_allowed"])

    def test_completion_gate_rejects_mission_accounting_invalid_or_incomplete_report(self) -> None:
        base = {
            "schema": "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1",
            "surface": "obelisk.mission_transfer_dino_tribe.v1",
            "ready": True,
            "accounting_route": "candidate_only",
            "candidate_only": True,
            "v1_accounted": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "required_leaves": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "observed_leaves": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "missing_leaf_families": ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
            "blockers": [],
        }
        cases = (
            ("not json", "mission_transfer_dino_tribe_outcome_accounting_output_invalid"),
            ({**base, "schema": "wrong-schema"}, "mission_transfer_dino_tribe_outcome_accounting_schema_mismatch"),
            ({**base, "surface": "wrong-surface"}, "mission_transfer_dino_tribe_outcome_accounting_surface_mismatch"),
            ({**base, "ready": False}, "mission_transfer_dino_tribe_outcome_accounting_invalid"),
            ({**base, "blockers": ["release_statement_leaf_exclusions_missing"]}, "mission_transfer_dino_tribe_outcome_accounting_blockers_not_empty"),
            ({**base, "observed_leaves": ["mission"]}, "mission_transfer_dino_tribe_observed_leaves_mismatch"),
            ({**base, "candidate_only": False}, "mission_transfer_dino_tribe_candidate_only_accounting_mismatch"),
        )
        for fake_payload, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_mission_accounting_checker(
                        Path(temp_dir) / "fake_mission_accounting.py",
                        fake_payload,
                    )
                    result = self.run_checker(
                        "--mission-transfer-dino-tribe-outcome-accounting",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, report["blockers"])
                self.assertFalse(report["stable_claim_allowed"])

    def test_completion_gate_rejects_resource_handle_public_runtime_promotion_overclaims(self) -> None:
        cases = (
            ("promotion_ready", True, "object_identity_resource_handle_promotion_ready_not_false"),
            ("public_sdk_ready", True, "object_identity_resource_handle_public_sdk_ready_not_false"),
            ("runtime_ready", True, "object_identity_resource_handle_runtime_ready_not_false"),
            (
                "public_resource_handle_ready",
                True,
                "object_identity_resource_handle_public_resource_handle_ready_not_false",
            ),
            (
                "post_callback_resource_handle_ready",
                True,
                "object_identity_resource_handle_post_callback_resource_handle_ready_not_false",
            ),
            ("public_abi_ready", True, "object_identity_resource_handle_public_or_runtime_claims"),
            ("public_header_allowed", "ready", "object_identity_resource_handle_public_or_runtime_claims"),
        )
        for key, value, expected in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_resource_handle_checker(
                        Path(temp_dir) / "fake_resource_handle_checker.py",
                        **{key: value},
                    )

                    result = self.run_checker(
                        "--object-identity-resource-handle-readiness",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, payload["blockers"])
                self.assertIn("object_identity_resource_handle_public_or_runtime_claims", payload["blockers"])
                self.assertIn(key, payload["object_identity_resource_handle_readiness"]["public_or_runtime_claims"])
                self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_resource_handle_checker_invalid_or_blocking_report(self) -> None:
        cases = (
            (
                {"schema": "wrong-schema"},
                "object_identity_resource_handle_readiness_schema_mismatch",
            ),
            (
                {"valid": False},
                "object_identity_resource_handle_readiness_invalid",
            ),
            (
                {"accepted_for_planning": False},
                "object_identity_resource_handle_readiness_not_planning_only",
            ),
            (
                {"planning_only": False},
                "object_identity_resource_handle_readiness_not_planning_only",
            ),
            (
                {"blockers": ["surface_status_not_post_v1"]},
                "object_identity_resource_handle_readiness_blockers_not_empty",
            ),
        )
        for overrides, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as temp_dir:
                    checker_path = self.write_fake_resource_handle_checker(
                        Path(temp_dir) / "fake_resource_handle_checker.py",
                        **overrides,
                    )

                    result = self.run_checker(
                        "--object-identity-resource-handle-readiness",
                        str(checker_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, payload["blockers"])
                self.assertFalse(payload["stable_claim_allowed"])

    def test_missing_p0_dependency_chain_blocker_reports_specific_mismatch(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        p0_chain = [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ]
        manifest["v1_dependency_sequence"] = list(p0_chain)
        manifest["v1_required_dependency_chain"] = list(p0_chain)
        manifest["v1_sdk_completion_blockers"] = [
            surface_id
            for surface_id in manifest["v1_sdk_completion_blockers"]
            if surface_id != "obelisk.command_chat_response_path.v1"
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertIn(
            "v1_required_dependency_chain_missing_from_completion_blockers",
            payload["blockers"],
        )
        self.assertIn("canonical_v1_completion_blocker_missing", payload["blockers"])
        self.assertEqual(
            payload["missing_v1_required_dependency_chain_completion_blockers"],
            ["obelisk.command_chat_response_path.v1"],
        )
        self.assertEqual(payload["v1_required_dependency_chain"], p0_chain)
        self.assertEqual(payload["v1_dependency_sequence"], p0_chain)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_total"], 4)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["dependency_chain_remaining_count"], 4)
        self.assertIn(
            "obelisk.command_chat_response_path.v1",
            payload["v1_sdk_blocker_outcome_summary"]["dependency_chain_remaining"],
        )
        self.assertIn(
            "obelisk.command_chat_response_path.v1",
            payload["v1_sdk_report_sections"]["next_v1_work"]["critical_path"],
        )
        self.assertIn(
            "obelisk.command_chat_response_path.v1",
            payload["unpromoted_required_dependency_chain"],
        )
        self.assertFalse(payload["v1_sdk_progress"]["stable_claim_allowed"])

    def test_missing_canonical_non_p0_completion_blocker_still_counts_in_accounting(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        omitted = "obelisk.operator_ingress_storage.v1"
        manifest["v1_sdk_completion_blockers"] = [
            surface_id
            for surface_id in manifest["v1_sdk_completion_blockers"]
            if surface_id != omitted
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("canonical_v1_completion_blocker_missing", payload["blockers"])
        self.assertIn(omitted, payload["missing_canonical_completion_blockers"])
        self.assertEqual(payload["v1_sdk_progress"]["completion_blocker_total"], 12)
        self.assertIn(omitted, [row["surface"] for row in payload["v1_sdk_blocker_outcomes"]])

    def test_player_identity_manifest_must_keep_request_pack_non_evidence_boundary(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["blockers"] = [
                    item
                    for item in surface.get("blockers", [])
                    if "Prepared request packs" not in item
                ]
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_request_pack_non_evidence_manifest_terms_missing", payload["blockers"])
        self.assertIn("prepared_at_utc", payload["player_identity_request_pack_non_evidence_terms_missing"])
        self.assertIn("observer env files", payload["player_identity_request_pack_non_evidence_terms_missing"])
        self.assertIn(
            "do not satisfy approved runtime principal lifecycle evidence",
            payload["player_identity_request_pack_non_evidence_terms_missing"],
        )
        self.assertIn("public identity promotion", payload["player_identity_request_pack_non_evidence_terms_missing"])
        self.assertIn("public ABI/SDK readiness", payload["player_identity_request_pack_non_evidence_terms_missing"])
        self.assertIn("runtime readiness", payload["player_identity_request_pack_non_evidence_terms_missing"])

    def test_human_output_names_actionable_v1_blocker_details(self) -> None:
        result = self.run_checker(check=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("The stable v1 SDK claim remains disabled", result.stdout)
        self.assertIn("12-blocker outcome accounting: 5 need manifest outcomes; 7 need release-statement outcomes", result.stdout)
        self.assertIn("High-demand v1 completion blockers are still unresolved", result.stdout)
        self.assertIn("obelisk.player_identity.v1", result.stdout)
        self.assertIn("Experimental copied-data seeds still need an explicit v1 outcome", result.stdout)
        self.assertIn("obelisk.chat_message.v1", result.stdout)
        self.assertIn("P0 route gate: approved_runtime_evidence_missing", result.stdout)
        self.assertIn("approved_runtime_principal_lifecycle_evidence", result.stdout)
        self.assertIn("reviewed_identity_public_contract", result.stdout)
        self.assertIn("High-demand v1 completion blockers are still unresolved", result.stdout)
        self.assertIn("Use --json for the full machine-readable report.", result.stdout)

    def test_completion_gate_rejects_route_gate_public_or_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = Path(temp_dir) / "fake_route_gate.py"
            route_gate_path.write_text(
                "import json\n"
                "print(json.dumps({\n"
                "    'schema': 'obelisk.command-permission-route-gate-check.v1',\n"
                "    'valid': True,\n"
                "    'accepted_for_planning': True,\n"
                "    'planning_only': True,\n"
                "    'promotion_ready': False,\n"
                "    'public_sdk_ready': False,\n"
                "    'public_abi_ready': False,\n"
                "    'runtime_ready': False,\n"
                "    'public_header_allowed': False,\n"
                "    'counts_toward_public_sdk': False,\n"
                "    'counts_toward_runtime': False,\n"
                "    'counts_toward_v1_completion': False,\n"
                "    'public_or_runtime_accounting_allowed': False,\n"
                "    'checks': [{\n"
                "        'name': 'command_chat_response_public_readiness',\n"
                "        'public_or_runtime_claims': ['reply_api_allowed'],\n"
                "        'runtime_delivery_allowed': True,\n"
                "        'notes': ['reply API is public and ready']\n"
                "    }, {\n"
                "        'name': 'commands_replies_public_readiness',\n"
                "        'non_claim': 'reply API is not public, not ready, and must remain blocked'\n"
                "    }],\n"
                "    'blockers': []\n"
                "} ))\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_public_or_runtime_claims", payload["blockers"])
        route_gate = payload["command_permission_route_gate"]
        self.assertIn(
            "checks[0].public_or_runtime_claims:reply_api_allowed",
            route_gate["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].runtime_delivery_allowed",
            route_gate["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].notes[0]:positive_text_claim",
            route_gate["public_or_runtime_claims"],
        )
        self.assertNotIn(
            "checks[1].non_claim:positive_text_claim",
            route_gate["public_or_runtime_claims"],
        )
        self.assertFalse(payload["stable_claim_allowed"])

    def test_route_gate_claim_scanner_ignores_argv_path_metadata(self) -> None:
        report = {
            "checks": [
                {
                    "argv": [
                        "check_commands_replies_public_readiness.py",
                        "--response-path-report",
                        "/tmp/command-chat-response-public-readiness/command-chat-response-public-readiness.json",
                        "--response-path-report-root",
                        "/tmp/command-chat-response-public-readiness",
                    ],
                    "public_or_runtime_claims": [],
                }
            ]
        }

        self.assertEqual(command_permission_route_gate_public_or_runtime_claims(report), [])

    def test_completion_gate_rejects_route_gate_schema_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = Path(temp_dir) / "fake_route_gate.py"
            route_gate_path.write_text(
                "import json\n"
                "print(json.dumps({\n"
                "    'schema': 'wrong-schema',\n"
                "    'valid': True,\n"
                "    'accepted_for_planning': True,\n"
                "    'planning_only': True,\n"
                "    'promotion_ready': False,\n"
                "    'public_sdk_ready': False,\n"
                "    'public_abi_ready': False,\n"
                "    'runtime_ready': False,\n"
                "    'public_header_allowed': False,\n"
                "    'counts_toward_public_sdk': False,\n"
                "    'counts_toward_runtime': False,\n"
                "    'counts_toward_v1_completion': False,\n"
                "    'public_or_runtime_accounting_allowed': False,\n"
                "    'blockers': []\n"
                "} ))\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_schema_mismatch", payload["blockers"])

    def test_completion_gate_rejects_route_gate_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = Path(temp_dir) / "fake_route_gate.py"
            route_gate_path.write_text("print('not json')\n", encoding="utf-8")

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_output_invalid", payload["blockers"])
        self.assertIn("stdout_json_decode_error", payload["command_permission_route_gate"]["parse_error"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertEqual(0, payload["v1_sdk_progress"]["completion_blockers_promoted_count"])
        self.assertEqual(0, payload["v1_sdk_progress"]["p0_chain_promoted_count"])

    def test_completion_gate_rejects_route_gate_nonempty_blockers_even_when_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(
                Path(temp_dir) / "fake_route_gate.py",
                blockers=["critical_path_identity_readiness_ready_flag_overclaim"],
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_blockers_not_empty", payload["blockers"])

    def test_completion_gate_rejects_route_gate_unlocked_route_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(
                Path(temp_dir) / "fake_route_gate.py",
                route_lock={"locked": False},
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_lock_unexpected", payload["blockers"])

    def test_completion_gate_rejects_route_gate_unlocked_ready_overclaim_without_p0_route_credit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(
                Path(temp_dir) / "fake_route_gate.py",
                accepted_for_planning=True,
                planning_only=False,
                promotion_ready=True,
                public_sdk_ready=True,
                public_abi_ready=True,
                runtime_ready=True,
                public_header_allowed=True,
                counts_toward_public_sdk=True,
                counts_toward_runtime=True,
                counts_toward_v1_completion=True,
                public_or_runtime_accounting_allowed=True,
                critical_path_phase={
                    "current_blocker": None,
                    "source_checker_primary_blocker": None,
                    "source_checker_status": "ready",
                    "source_checker_ready": True,
                    "source_checker_accepted_for_internal_planning": True,
                },
                route_lock={"locked": False, "blocked_until": []},
                blockers=[],
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        p0_rows = [
            row
            for row in payload["v1_sdk_blocker_outcomes"]
            if row["surface"] in {
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            }
        ]

        self.assertEqual(result.returncode, 1)
        for blocker in (
            "command_permission_route_gate_not_planning_only",
            "command_permission_route_gate_promotion_ready_not_false",
            "command_permission_route_gate_public_sdk_ready_not_false",
            "command_permission_route_gate_public_abi_ready_not_false",
            "command_permission_route_gate_runtime_ready_not_false",
            "command_permission_route_gate_public_header_allowed_not_false",
            "command_permission_route_gate_counts_toward_public_sdk_not_false",
            "command_permission_route_gate_counts_toward_runtime_not_false",
            "command_permission_route_gate_counts_toward_v1_completion_not_false",
            "command_permission_route_gate_public_or_runtime_accounting_allowed_not_false",
            "command_permission_route_gate_lock_unexpected",
            "command_permission_route_gate_default_blocker_mismatch",
            "command_permission_route_gate_default_source_blocker_mismatch",
            "command_permission_route_gate_source_status_unexpected",
            "command_permission_route_gate_source_ready_overclaim",
            "command_permission_route_gate_source_internal_planning_overclaim",
            "command_permission_route_gate_default_lock_blocked_until_unexpected",
            "command_permission_route_gate_public_or_runtime_claims",
        ):
            self.assertIn(blocker, payload["blockers"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertEqual(4, len(p0_rows))
        for row in p0_rows:
            self.assertFalse(row["route_gate_claim_satisfied"], row)
            self.assertFalse(row["counts_toward_complete_sdk_claim"], row)
        self.assertEqual(0, payload["v1_sdk_progress"]["p0_chain_promoted_count"])
        self.assertFalse(payload["command_permission_route_gate"]["completion_gate_accepted"])
        self.assertIn(
            "command_permission_route_gate_not_planning_only",
            payload["command_permission_route_gate"]["completion_gate_blockers"],
        )

    def test_completion_gate_rejects_route_gate_accounting_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(
                Path(temp_dir) / "fake_route_gate.py",
                counts_toward_public_sdk=True,
                counts_toward_runtime=True,
                counts_toward_v1_completion=True,
                public_or_runtime_accounting_allowed=True,
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        for blocker in (
            "command_permission_route_gate_counts_toward_public_sdk_not_false",
            "command_permission_route_gate_counts_toward_runtime_not_false",
            "command_permission_route_gate_counts_toward_v1_completion_not_false",
            "command_permission_route_gate_public_or_runtime_accounting_allowed_not_false",
            "command_permission_route_gate_public_or_runtime_claims",
        ):
            self.assertIn(blocker, payload["blockers"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["command_permission_route_gate"]["completion_gate_accepted"])

    def test_completion_gate_rejects_route_gate_wrong_default_blocked_until(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(
                Path(temp_dir) / "fake_route_gate.py",
                route_lock={"blocked_until": ["reviewed_identity_public_contract"]},
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_default_lock_blocked_until_unexpected", payload["blockers"])

    def test_completion_gate_rejects_route_gate_source_checker_ready_overclaim(self) -> None:
        cases = (
            (
                {"source_checker_ready": True},
                "command_permission_route_gate_source_ready_overclaim",
            ),
            (
                {"source_checker_status": "ready"},
                "command_permission_route_gate_source_status_unexpected",
            ),
            (
                {"source_checker_accepted_for_internal_planning": True},
                "command_permission_route_gate_source_internal_planning_overclaim",
            ),
        )
        for phase_overrides, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as temp_dir:
                    route_gate_path = self.write_fake_route_gate(
                        Path(temp_dir) / "fake_route_gate.py",
                        critical_path_phase=phase_overrides,
                    )

                    result = self.run_checker(
                        "--command-permission-route-gate",
                        str(route_gate_path),
                        "--json",
                        env=self.route_gate_override_env(),
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, payload["blockers"])

    def test_completion_gate_rejects_route_gate_stale_source_checker_next_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = self.write_fake_route_gate(
                Path(temp_dir) / "fake_route_gate.py",
                critical_path_phase={"source_checker_next_blocker": "identity_public_contract_gate_missing"},
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_default_source_next_blocker_unexpected", payload["blockers"])

    def test_completion_gate_rejects_lifecycle_route_gate_missing_source_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = Path(temp_dir) / "fake_route_gate.py"
            route_gate_path.write_text(
                "import json\n"
                "print(json.dumps({\n"
                "    'schema': 'obelisk.command-permission-route-gate-check.v1',\n"
                "    'valid': True,\n"
                "    'accepted_for_planning': True,\n"
                "    'planning_only': True,\n"
                "    'promotion_ready': False,\n"
                "    'public_sdk_ready': False,\n"
                "    'public_abi_ready': False,\n"
                "    'runtime_ready': False,\n"
                "    'public_header_allowed': False,\n"
                "    'counts_toward_public_sdk': False,\n"
                "    'counts_toward_runtime': False,\n"
                "    'counts_toward_v1_completion': False,\n"
                "    'public_or_runtime_accounting_allowed': False,\n"
                "    'critical_path_phase': {\n"
                "        'current_blocker': 'lifecycle_anchor_first_evidence_provenance_unbound',\n"
                "        'source_checker_primary_blocker': 'lifecycle_anchor_first_evidence_provenance_unbound'\n"
                "    },\n"
                "    'route_lock': {\n"
                "        'blocked_until': ['bound_lifecycle_anchor_and_principal_policy_sources', 'reviewed_identity_public_contract']\n"
                "    },\n"
                "    'checks': [],\n"
                "    'blockers': []\n"
                "} ))\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("command_permission_route_gate_default_blocker_mismatch", payload["blockers"])
        self.assertNotIn("command_permission_route_gate_default_source_blocker_mismatch", payload["blockers"])
        self.assertIn("command_permission_route_gate_source_status_unexpected", payload["blockers"])
        self.assertIn("command_permission_route_gate_lock_unexpected", payload["blockers"])
        route_gate = payload["command_permission_route_gate"]
        self.assertEqual(route_gate["current_blocker"], "lifecycle_anchor_first_evidence_provenance_unbound")
        self.assertEqual(
            route_gate["source_checker_primary_blocker"],
            "lifecycle_anchor_first_evidence_provenance_unbound",
        )
        self.assertEqual(
            route_gate["route_lock_blocked_until"],
            ["bound_lifecycle_anchor_and_principal_policy_sources", "reviewed_identity_public_contract"],
        )

    def test_route_gate_claim_scanner_rejects_public_command_reply_aliases(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        claims = module.command_permission_route_gate_public_or_runtime_claims(
            {
                "schema": "obelisk.command-permission-route-gate-check.v1",
                "valid": True,
                "accepted_for_planning": True,
                "planning_only": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_sdk": True,
                "public_abi_ready": False,
                "public_abi_available": True,
                "runtime_ready": False,
                "runtime_v1_ready": True,
                "public_header_allowed": False,
                "public_header_ready": True,
                "complete_sdk_ready": True,
                "full_api_supported": True,
                "production_support_ready": True,
                "stable_sdk_allowed": "ready",
                "public_api_allowed": "allowed",
                "counts_toward_public_sdk": True,
                "countsTowardRuntime": True,
                "counts_toward_v1_completion": True,
                "public_or_runtime_accounting_allowed": True,
                "routeReady": True,
                "route_readiness_ready": True,
                "publicRouteReady": True,
                "permissionsAdminRouteReady": True,
                "checks": [
                    {
                        "name": "commands_replies_public_readiness",
                        "public_response_path_ready": True,
                        "public_command_router_allowed": True,
                        "public_reply_or_send_chat_abi_allowed": True,
                        "public_reply_api": True,
                        "public_send_chat_api": True,
                        "public_reply_abi_allowed": True,
                        "public_send_chat_abi_allowed": "ready",
                        "public_abi_available": "available",
                        "send_chat_ready": True,
                        "public-reply-api": True,
                        "publicSendChatApi": True,
                        "reply_send_chat_router_claims_allowed": True,
                        "public_abi_allowed": "ready",
                        "permissions_admin_ready": True,
                        "permissions_admin_route_ready": True,
                        "public_route_ready": True,
                        "route_ready": True,
                        "route_readiness_ready": True,
                        "permissions_ready": True,
                        "permission_ready": True,
                        "operator_approval_granted": True,
                        "runtime_approval": True,
                        "runtime_approval_granted": True,
                        "runtime_work_authorized": True,
                        "runtime_v1_ready": "yes",
                        "server_operations_authorized": True,
                        "approved_runtime_evidence_source": "operator_receipt",
                        "runtimeEvidenceSource": "request-pack",
                        "evidence_source": {"source": "live-validation-sidecar"},
                        "authz_principal_source": ["players_identity_runtime_principal_lifecycle_evidence"],
                        "reply_allowed": 1,
                        "send_chat_allowed": "true",
                        "notes": [
                            "route readiness is ready",
                            "public route is ready",
                            "send-chat ABI is public and ready",
                            "command routing is public and ready",
                            "permissions/admin is public and ready",
                            "replies API is public and ready",
                            "command response path is live",
                            "reply endpoint is live",
                            "send chat API is operational",
                            "stable SDK is ready",
                            "complete SDK is ready",
                            "production SDK is supported",
                            "SDK is stable",
                            "API is production ready",
                            "planning-only report says stable SDK is ready",
                            "runtime work is authorized",
                            "server operations are authorized",
                            "operator approval is granted",
                            "runtime approval is granted",
                            "stable SDK remains blocked",
                            "route gate remains blocked. public SDK is ready",
                            {
                                "non_claims": [
                                    "public SDK readiness remains blocked",
                                    "v1 completion ready is not satisfied",
                                ]
                            },
                        ],
                    }
                ],
            }
        )

        self.assertIn("checks[0].public_command_router_allowed", claims)
        self.assertIn("checks[0].public_response_path_ready", claims)
        self.assertIn("checks[0].public_reply_or_send_chat_abi_allowed", claims)
        self.assertIn("checks[0].public_reply_api", claims)
        self.assertIn("checks[0].public_send_chat_api", claims)
        self.assertIn("checks[0].public_reply_abi_allowed", claims)
        self.assertIn("checks[0].public_send_chat_abi_allowed", claims)
        self.assertIn("checks[0].public_abi_available", claims)
        self.assertIn("checks[0].send_chat_ready", claims)
        self.assertIn("checks[0].public-reply-api", claims)
        self.assertIn("checks[0].publicSendChatApi", claims)
        self.assertIn("checks[0].reply_send_chat_router_claims_allowed", claims)
        self.assertIn("checks[0].public_abi_allowed", claims)
        self.assertIn("checks[0].permissions_admin_ready", claims)
        self.assertIn("checks[0].permissions_admin_route_ready", claims)
        self.assertIn("checks[0].public_route_ready", claims)
        self.assertIn("checks[0].route_ready", claims)
        self.assertIn("checks[0].route_readiness_ready", claims)
        self.assertIn("checks[0].permissions_ready", claims)
        self.assertIn("checks[0].permission_ready", claims)
        self.assertIn("checks[0].operator_approval_granted", claims)
        self.assertIn("checks[0].runtime_approval", claims)
        self.assertIn("checks[0].runtime_approval_granted", claims)
        self.assertIn("checks[0].runtime_work_authorized", claims)
        self.assertIn("checks[0].runtime_v1_ready", claims)
        self.assertIn("checks[0].server_operations_authorized", claims)
        self.assertIn("checks[0].approved_runtime_evidence_source", claims)
        self.assertIn("checks[0].runtimeEvidenceSource", claims)
        self.assertIn("checks[0].evidence_source", claims)
        self.assertIn("checks[0].authz_principal_source", claims)
        self.assertIn("checks[0].reply_allowed", claims)
        self.assertIn("checks[0].send_chat_allowed", claims)
        self.assertIn("checks[0].notes[0]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[1]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[2]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[3]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[4]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[5]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[6]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[7]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[8]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[9]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[10]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[11]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[12]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[13]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[14]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[15]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[16]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[17]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[18]:positive_text_claim", claims)
        self.assertNotIn("checks[0].notes[19]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[20]:positive_text_claim", claims)
        self.assertNotIn("checks[0].notes[21].non_claims[0]:positive_text_claim", claims)
        self.assertNotIn("checks[0].notes[21].non_claims[1]:positive_text_claim", claims)
        self.assertIn("complete_sdk_ready", claims)
        self.assertIn("full_api_supported", claims)
        self.assertIn("production_support_ready", claims)
        self.assertIn("stable_sdk_allowed", claims)
        self.assertIn("public_api_allowed", claims)
        self.assertIn("public_abi_available", claims)
        self.assertIn("runtime_v1_ready", claims)
        self.assertIn("counts_toward_public_sdk", claims)
        self.assertIn("countsTowardRuntime", claims)
        self.assertIn("counts_toward_v1_completion", claims)
        self.assertIn("public_or_runtime_accounting_allowed", claims)
        self.assertIn("routeReady", claims)
        self.assertIn("route_readiness_ready", claims)
        self.assertIn("publicRouteReady", claims)
        self.assertIn("permissionsAdminRouteReady", claims)

    def test_completion_gate_rejects_route_gate_alias_claims_without_claims_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = Path(temp_dir) / "fake_route_gate.py"
            route_gate_path.write_text(
                "import json\n"
                "print(json.dumps({\n"
                "    'schema': 'obelisk.command-permission-route-gate-check.v1',\n"
                "    'valid': True,\n"
                "    'accepted_for_planning': True,\n"
                "    'planning_only': True,\n"
                "    'promotion_ready': False,\n"
                "    'public_sdk_ready': False,\n"
                "    'public_abi_ready': False,\n"
                "    'runtime_ready': False,\n"
                "    'public_header_allowed': False,\n"
                "    'counts_toward_public_sdk': False,\n"
                "    'counts_toward_runtime': False,\n"
                "    'counts_toward_v1_completion': False,\n"
                "    'public_or_runtime_accounting_allowed': False,\n"
                "    'checks': [{\n"
                "        'name': 'commands_replies_public_readiness',\n"
                "        'public_command_router_allowed': True,\n"
                "        'public_reply_or_send_chat_abi_allowed': True,\n"
                "        'public_reply_api': 'ready',\n"
                "        'public_send_chat_api': 'ready',\n"
                "        'reply_allowed': 1,\n"
                "        'send_chat_allowed': 'true'\n"
                "    }],\n"
                "    'blockers': []\n"
                "} ))\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                env=self.route_gate_override_env(),
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_public_or_runtime_claims", payload["blockers"])
        claims = payload["command_permission_route_gate"]["public_or_runtime_claims"]
        self.assertIn("checks[0].public_command_router_allowed", claims)
        self.assertIn("checks[0].public_reply_or_send_chat_abi_allowed", claims)
        self.assertFalse(payload["stable_claim_allowed"])

    def test_blocked_contract_decisions_detect_untracked_public_header_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskPlayerIdentity {\n"
                "    uint32_t abi_version;\n"
                "    uint64_t principal_handle;\n"
                "} ObeliskPlayerIdentity;\n"
                "typedef struct ObeliskOpaque* ObeliskPlayerHandle;\n"
                "typedef void* ObeliskPermissionHandle;\n"
                "typedef ObeliskResourceKind ObeliskPlayerKind;\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterPlayerIdentityWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "player_identity_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-identity-public-contract-decisions.v1",
                        "surface": "obelisk.player_identity.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift = next(iter(payload["blocked_public_contract_header_symbols"].values()))
        self.assertEqual(drift["surface"], "obelisk.player_identity.v1")
        self.assertIn("ObeliskPlayerIdentity", drift["undeclared_symbols"])
        self.assertIn("RegisterPlayerIdentityWithOwnerTokenHandle", drift["undeclared_symbols"])
        self.assertIn("principal_handle", drift["undeclared_symbols"])

    def test_blocked_permissions_contract_detects_public_reason_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef uint64_t ObeliskPermissionReasonFlags;\n"
                "#define OBELISK_PERMISSION_REASON_DENY 1\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t reason_flags;\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "permissions_admin_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.permissions-admin-public-contract-decisions.v1",
                        "surface": "obelisk.permissions_admin.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift = next(
            item
            for item in payload["blocked_public_contract_header_symbols"].values()
            if item["surface"] == "obelisk.permissions_admin.v1"
        )
        self.assertIn("ObeliskPermissionReasonFlags", drift["undeclared_symbols"])
        self.assertIn("OBELISK_PERMISSION_REASON_DENY", drift["undeclared_symbols"])
        self.assertIn("reason_flags", drift["undeclared_symbols"])

    def test_blocked_contract_symbol_drift_ignores_existing_chat_message_rc_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskChatMessageEvent { uint32_t abi_version; } ObeliskChatMessageEvent;\n"
                "typedef void (*ObeliskChatMessageEventCallback)(const ObeliskChatMessageEvent* event, void* user_data);\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterChatMessageEventWithOwnerTokenHandle)(uint64_t ownerToken, ObeliskChatMessageEventCallback callback, void* userData);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "command_chat_response_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-contract-decisions.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertNotIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        self.assertEqual(payload["blocked_public_contract_header_symbols"], {})

    def test_blocked_commands_replies_contract_detects_command_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskCommandPayload { uint32_t abi_version; } ObeliskCommandPayload;\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterCommandWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "commands_replies_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.commands-replies-public-contract-decisions.v1",
                        "surface": "obelisk.commands_replies.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift = next(iter(payload["blocked_public_contract_header_symbols"].values()))
        self.assertEqual(drift["surface"], "obelisk.commands_replies.v1")
        self.assertIn("ObeliskCommandPayload", drift["undeclared_symbols"])
        self.assertIn("RegisterCommandWithOwnerTokenHandle", drift["undeclared_symbols"])

    def test_route_guardrail_contract_detects_forbidden_token_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#define OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE 0x80000000u\n"
                "typedef struct ObeliskCommandPrincipalAuthzResponseBridge { unsigned abi_version; } ObeliskCommandPrincipalAuthzResponseBridge;\n",
                encoding="utf-8",
            )
            (decisions_dir / "command_principal_authz_response_bridge_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-principal-authz-response-bridge-decisions.v1",
                        "surface": "obelisk.command_principal_authz_response_bridge.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                        "public_header_forbidden_tokens": [
                            "OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE",
                            "ObeliskCommandPrincipalAuthzResponseBridge",
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift = next(iter(payload["blocked_public_contract_header_symbols"].values()))
        self.assertEqual(drift["surface"], "obelisk.command_principal_authz_response_bridge.v1")
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE", drift["undeclared_symbols"])
        self.assertIn("ObeliskCommandPrincipalAuthzResponseBridge", drift["undeclared_symbols"])

    def test_blocked_contract_symbols_are_not_reported_when_contract_lists_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterCommandResponseWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "command_chat_response_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-contract-decisions.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": ["RegisterCommandResponseWithOwnerTokenHandle"],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertNotIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        self.assertEqual(payload["blocked_public_contract_header_symbols"], {})

    def test_manifest_blocked_side_lane_contracts_detect_public_header_symbols(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            manifest_path = temp_path / "public_sdk_surfaces.json"
            release_statement_path = temp_path / "RELEASE_STATEMENT.md"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskStructureCensus { uint32_t abi_version; } ObeliskStructureCensus;\n"
                "typedef struct ObeliskDinoSdk { uint32_t abi_version; } ObeliskDinoSdk;\n"
                "typedef struct ObeliskInventoryMutation { uint32_t abi_version; } ObeliskInventoryMutation;\n"
                "typedef struct ObeliskObjectIdentity { uint32_t abi_version; } ObeliskObjectIdentity;\n"
                "typedef struct ObeliskEconomyApi { uint32_t abi_version; } ObeliskEconomyApi;\n"
                "typedef struct ObeliskRCONIngress { uint32_t abi_version; } ObeliskRCONIngress;\n"
                "typedef struct ObeliskPluginWatchdog { uint32_t abi_version; } ObeliskPluginWatchdog;\n"
                "typedef struct ObeliskGameplayTickCallback { uint32_t abi_version; } ObeliskGameplayTickCallback;\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterStructureCensusWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterMissionWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*GiveItemWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterResourceHandleWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterEconomyWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterOperatorReloadWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterPluginWatchdogWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterGameplayTickWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")

            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift_by_surface = {
            drift["surface"]: drift["undeclared_symbols"]
            for drift in payload["blocked_public_contract_header_symbols"].values()
        }
        self.assertIn("ObeliskStructureCensus", drift_by_surface["obelisk.structure_census.v1"])
        self.assertIn("RegisterMissionWithOwnerTokenHandle", drift_by_surface["obelisk.mission_transfer_dino_tribe.v1"])
        self.assertIn("GiveItemWithOwnerTokenHandle", drift_by_surface["obelisk.inventory_items_mutation.v1"])
        self.assertIn("ObeliskObjectIdentity", drift_by_surface["obelisk.object_identity_resource_handle.v1"])
        self.assertIn(
            "RegisterResourceHandleWithOwnerTokenHandle",
            drift_by_surface["obelisk.object_identity_resource_handle.v1"],
        )
        self.assertIn("RegisterEconomyWithOwnerTokenHandle", drift_by_surface["obelisk.player_services_economy_mobility.v1"])
        self.assertIn("ObeliskRCONIngress", drift_by_surface["obelisk.operator_ingress_storage.v1"])
        self.assertIn("ObeliskPluginWatchdog", drift_by_surface["obelisk.lifecycle_ops_recovery.v1"])
        self.assertIn("RegisterGameplayTickWithOwnerTokenHandle", drift_by_surface["obelisk.gameplay_tick_callbacks.v1"])

    def test_current_manifest_reports_exact_unresolved_v1_surface_groups(self) -> None:
        result = self.run_checker("--json", check=False)
        payload = json.loads(result.stdout)
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        gameplay = surfaces["obelisk.mission_transfer_dino_tribe.v1"]

        self.assertEqual(
            payload["unresolved_completion_blockers"],
            [
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
                "obelisk.mission_transfer_dino_tribe.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
            ],
        )
        self.assertEqual(
            [leaf["id"] for leaf in gameplay["leaf_decision_units"]],
            ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
        )
        self.assertTrue(gameplay["v1_decision_contract"]["leaf_split_reviewed"])
        self.assertEqual({leaf["status"] for leaf in gameplay["leaf_decision_units"]}, {"planning"})
        self.assertEqual(
            payload["unresolved_experimental_surfaces"],
            [
                "obelisk.chat.local_routing.v1",
                "obelisk.chat_message.v1",
                "obelisk.gameplay_policy_event.v1",
                "obelisk.inventory_item_copied_signals.v1",
            ],
        )
        self.assertEqual(
            payload["release_statement_missing_blocker_outcomes"],
            [
                "obelisk.gameplay_tick_callbacks.v1",
                "obelisk.inventory_items_mutation.v1",
                "obelisk.lifecycle_ops_recovery.v1",
                "obelisk.object_identity_resource_handle.v1",
                "obelisk.operator_ingress_storage.v1",
                "obelisk.player_services_economy_mobility.v1",
                "obelisk.structure_census.v1",
            ],
        )
        self.assertEqual(payload["promoted_surfaces_with_unresolved_dependencies"], {})
        self.assertEqual(payload["promoted_surfaces_without_evidence"], [])
        self.assertEqual(payload["promoted_blockers_without_evidence"], [])

    def test_mission_transfer_dino_tribe_promotion_requires_all_leaf_units_promoted(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        surface_id = "obelisk.mission_transfer_dino_tribe.v1"
        for surface in manifest["surfaces"]:
            if surface["id"] == surface_id:
                surface["status"] = "promoted"
                surface["public_contract"] = ["Mission copied policy callback"]
                surface["evidence"] = {
                    "surface_id": surface_id,
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/MissionCopiedBoolEventDispatcherTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/SdkConsumerFixture.cpp"],
                }
                for leaf in surface["leaf_decision_units"]:
                    leaf["status"] = "promoted" if leaf["id"] == "mission" else "planning"
                break
        manifest["promoted_surfaces"].append(surface_id)
        manifest["post_v1_or_excluded_surfaces"] = [
            item for item in manifest["post_v1_or_excluded_surfaces"] if item != surface_id
        ]
        release_lines = []
        for line in release_statement.splitlines():
            if line.startswith(f"{surface_id}:"):
                release_lines.append(f"{surface_id}: promoted - mission copied policy callback reviewed.")
            else:
                release_lines.append(line)
        release_statement = "\n".join(release_lines) + "\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        outcome = next(row for row in payload["v1_sdk_blocker_outcomes"] if row["surface"] == surface_id)
        self.assertFalse(outcome["promotion_evidence_satisfied"])
        self.assertFalse(outcome["counts_toward_complete_sdk_claim"])
        self.assertIn(surface_id, payload["promoted_blockers_without_evidence"])

    def test_mission_transfer_dino_tribe_promotion_requires_per_leaf_evidence(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        surface_id = "obelisk.mission_transfer_dino_tribe.v1"
        for surface in manifest["surfaces"]:
            if surface["id"] == surface_id:
                surface["status"] = "promoted"
                surface["public_contract"] = ["Mission copied policy callback"]
                surface["evidence"] = {
                    "surface_id": surface_id,
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/MissionCopiedBoolEventDispatcherTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/SdkConsumerFixture.cpp"],
                }
                for leaf in surface["leaf_decision_units"]:
                    leaf["status"] = "promoted"
                break
        manifest["promoted_surfaces"].append(surface_id)
        manifest["post_v1_or_excluded_surfaces"] = [
            item for item in manifest["post_v1_or_excluded_surfaces"] if item != surface_id
        ]
        release_statement = "\n".join(
            (
                f"{surface_id}: promoted - all leaf units reviewed."
                if line.startswith(f"{surface_id}:")
                else line
            )
            for line in release_statement.splitlines()
        ) + "\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        outcome = next(row for row in payload["v1_sdk_blocker_outcomes"] if row["surface"] == surface_id)
        self.assertFalse(outcome["promotion_evidence_satisfied"])
        self.assertFalse(outcome["counts_toward_complete_sdk_claim"])
        self.assertIn(surface_id, payload["promoted_blockers_without_evidence"])

    def mission_transfer_promoted_surface_with_leaf_evidence(
        self,
        core_root: Path,
        sdk_root: Path,
        *,
        leaf_overrides: dict[str, dict[str, object]] | None = None,
        use_promotion_evidence_by_leaf: bool = False,
    ) -> dict[str, object]:
        surface_id = "obelisk.mission_transfer_dino_tribe.v1"
        leaf_ids = ("mission", "transfer", "dino_policy", "tribe_policy", "buff_status")
        leaf_overrides = leaf_overrides or {}
        evidence_by_leaf: dict[str, dict[str, object]] = {}
        for leaf_id in leaf_ids:
            abi_path = core_root / f"MissionTransferDinoTribe_{leaf_id}_PromotionTests.cpp"
            sdk_path = sdk_root / f"mission_transfer_dino_tribe_{leaf_id}_promotion.c"
            second_source_path = core_root / "docs" / "research" / f"mission_transfer_dino_tribe_{leaf_id}_second_source.json"
            abi_path.parent.mkdir(parents=True, exist_ok=True)
            sdk_path.parent.mkdir(parents=True, exist_ok=True)
            second_source_path.parent.mkdir(parents=True, exist_ok=True)
            abi_path.write_text("// ABI promotion fixture\n", encoding="utf-8")
            sdk_path.write_text("/* SDK promotion fixture */\n", encoding="utf-8")
            second_source_path.write_text("{}\n", encoding="utf-8")
            evidence = {
                "promotion_status": "promoted",
                "promotion_ready": True,
                "public_sdk_ready": True,
                "runtime_ready": True,
                "abi_tests": [str(abi_path.relative_to(REPO_ROOT))],
                "sdk_consumer_tests": [str(sdk_path.relative_to(REPO_ROOT))],
                "second_source_evidence": [str(second_source_path.relative_to(REPO_ROOT))],
            }
            evidence.update(leaf_overrides.get(leaf_id, {}))
            evidence_by_leaf[leaf_id] = evidence

        leaf_units = [{"id": leaf_id, "status": "promoted"} for leaf_id in leaf_ids]
        if not use_promotion_evidence_by_leaf:
            for leaf in leaf_units:
                leaf["evidence"] = evidence_by_leaf[leaf["id"]]  # type: ignore[index]
        return {
            "id": surface_id,
            "status": "promoted",
            "evidence": {
                "surface_id": surface_id,
                "promotion_status": "promoted",
                "public_sdk_ready": True,
                "abi_tests": [str((core_root / "MissionTransferDinoTribe_surface_PromotionTests.cpp").relative_to(REPO_ROOT))],
                "sdk_consumer_tests": [str((sdk_root / "mission_transfer_dino_tribe_surface_promotion.c").relative_to(REPO_ROOT))],
            },
            "leaf_decision_units": leaf_units,
            "promotion_evidence_by_leaf": evidence_by_leaf if use_promotion_evidence_by_leaf else {},
        }

    def test_mission_transfer_dino_tribe_leaf_promotion_evidence_requires_strict_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="MissionLeafEvidence") as core_dir, tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "sdk_consumer", prefix="MissionLeafEvidence") as sdk_dir:
            core_root = Path(core_dir)
            sdk_root = Path(sdk_dir)
            surface_abi = core_root / "MissionTransferDinoTribe_surface_PromotionTests.cpp"
            surface_sdk = sdk_root / "mission_transfer_dino_tribe_surface_promotion.c"
            surface_abi.parent.mkdir(parents=True, exist_ok=True)
            surface_sdk.parent.mkdir(parents=True, exist_ok=True)
            surface_abi.write_text("// surface ABI fixture\n", encoding="utf-8")
            surface_sdk.write_text("/* surface SDK fixture */\n", encoding="utf-8")

            valid_surface = self.mission_transfer_promoted_surface_with_leaf_evidence(core_root, sdk_root)
            missing_path_surface = self.mission_transfer_promoted_surface_with_leaf_evidence(
                core_root,
                sdk_root,
                leaf_overrides={
                    "transfer": {
                        "abi_tests": ["tests/core/MissionTransferDinoTribe_transfer_missing.cpp"],
                    }
                },
            )
            generic_path_surface = self.mission_transfer_promoted_surface_with_leaf_evidence(
                core_root,
                sdk_root,
                leaf_overrides={
                    "dino_policy": {
                        "abi_tests": [str(surface_abi.relative_to(REPO_ROOT))],
                    }
                },
            )

            self.assertTrue(surface_has_promotion_evidence(valid_surface))
            self.assertFalse(surface_has_promotion_evidence(missing_path_surface))
            self.assertFalse(surface_has_promotion_evidence(generic_path_surface))

    def test_mission_transfer_dino_tribe_leaf_promotion_rejects_non_promotional_sidecars(self) -> None:
        cases = (
            {"ready_scope": "operator_receipt_only"},
            {"source_kind": "operator_receipt"},
            {"schema": "obelisk.live-ops-sidecar.v1"},
            {"candidate_only": True},
        )
        for override in cases:
            with self.subTest(override=override):
                with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="MissionLeafSidecar") as core_dir, tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "sdk_consumer", prefix="MissionLeafSidecar") as sdk_dir:
                    core_root = Path(core_dir)
                    sdk_root = Path(sdk_dir)
                    surface_abi = core_root / "MissionTransferDinoTribe_surface_PromotionTests.cpp"
                    surface_sdk = sdk_root / "mission_transfer_dino_tribe_surface_promotion.c"
                    surface_abi.parent.mkdir(parents=True, exist_ok=True)
                    surface_sdk.parent.mkdir(parents=True, exist_ok=True)
                    surface_abi.write_text("// surface ABI fixture\n", encoding="utf-8")
                    surface_sdk.write_text("/* surface SDK fixture */\n", encoding="utf-8")
                    surface = self.mission_transfer_promoted_surface_with_leaf_evidence(
                        core_root,
                        sdk_root,
                        leaf_overrides={"mission": override},
                        use_promotion_evidence_by_leaf=True,
                    )

                    self.assertFalse(surface_has_promotion_evidence(surface))

    def test_scoped_release_statement_template_passes_statement_scope_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            build_policy_checker = self.write_fake_structure_build_policy_checker(
                Path(temp_dir) / "fake_structure_build_policy.py"
            )
            result = self.run_checker(
                "--release-statement",
                str(SCOPED_RELEASE_STATEMENT_TEMPLATE),
                "--structure-build-policy-offline-intake",
                str(build_policy_checker),
                "--validate-release-statement-scope",
                "--json",
            )
        payload = json.loads(result.stdout)

        self.assertFalse(payload["ready"])
        self.assertTrue(payload["scoped_release_statement"]["ready"])
        self.assertFalse(payload["scoped_release_statement"]["stable_v1_sdk_claim_allowed"])
        self.assertEqual(
            payload["v1_sdk_progress"]["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
            [
                "obelisk.gameplay_tick_callbacks.v1",
                "obelisk.inventory_items_mutation.v1",
                "obelisk.lifecycle_ops_recovery.v1",
                "obelisk.object_identity_resource_handle.v1",
                "obelisk.operator_ingress_storage.v1",
                "obelisk.player_services_economy_mobility.v1",
                "obelisk.structure_census.v1",
            ],
        )
        self.assertEqual(
            payload["v1_sdk_progress"]["completion_blockers_with_release_statement_post_v1_or_excluded_outcome"],
            payload["v1_sdk_progress"]["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["release_statement_bookkeeping"][
                "release_statement_post_v1_or_excluded_outcomes"
            ],
            payload["v1_sdk_report_sections"]["release_statement_bookkeeping"][
                "manifest_post_v1_or_excluded_outcomes"
            ],
        )
        expected_active_side_lanes = [
            "obelisk.lifecycle_ops_recovery.v1",
            "obelisk.player_services_economy_mobility.v1",
            "obelisk.operator_ingress_storage.v1",
            "obelisk.gameplay_tick_callbacks.v1",
        ]
        self.assertEqual(
            payload["v1_sdk_progress"]["active_side_lane_review_blockers"],
            expected_active_side_lanes,
        )
        self.assertEqual(
            payload["v1_sdk_progress"][
                "active_side_lane_review_manifest_post_v1_or_excluded"
            ],
            expected_active_side_lanes,
        )
        self.assertEqual(
            payload["v1_sdk_progress"][
                "active_side_lane_review_release_statement_post_v1_or_excluded"
            ],
            expected_active_side_lanes,
        )
        self.assertEqual(
            payload["v1_sdk_progress"]["active_side_lane_review_promoted_for_claim_count"],
            0,
        )
        self.assertEqual(
            payload["v1_sdk_progress"]["active_side_lane_review_remaining_for_claim_count"],
            4,
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["active_side_lane_review"][
                "release_statement_post_v1_or_excluded"
            ],
            expected_active_side_lanes,
        )
        self.assertIn(
            "do not promote",
            payload["v1_sdk_progress"]["active_side_lane_review_non_claim"],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["release_statement_bookkeeping"][
                "missing_blocker_outcomes"
            ],
            [],
        )
        self.assertFalse(payload["v1_sdk_report_sections"]["no_live_progress"]["stable_claim_allowed"])
        self.assertEqual(payload["v1_sdk_blocker_outcome_summary"]["manifest_outcome_missing_count"], 5)
        self.assertEqual(payload["v1_sdk_blocker_outcome_summary"]["release_statement_outcome_missing_count"], 0)
        outcome_by_surface = {
            row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]
        }
        for surface in (
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ):
            with self.subTest(surface=surface):
                self.assertIsNone(outcome_by_surface[surface]["release_statement_outcome"])
                self.assertEqual(
                    outcome_by_surface[surface]["next_action"],
                    "priority dependency-chain blocker: promote with evidence; excluded/post-v1 cannot satisfy complete SDK",
                )
        self.assertFalse(
            outcome_by_surface["obelisk.permissions_admin.v1"][
                "release_statement_contract_satisfied"
            ]
        )
        self.assertIsNone(outcome_by_surface["obelisk.player_identity.v1"]["manifest_outcome"])
        self.assertFalse(
            outcome_by_surface["obelisk.player_identity.v1"][
                "release_statement_contract_satisfied"
            ]
        )
        self.assertFalse(payload["v1_sdk_progress"]["stable_claim_allowed"])
        self.assertNotIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], [])
        self.assertIn("stable_release_contract_claim_not_allowed", payload["blockers"])
        self.assertIn("top_level_planning_surfaces_unresolved_for_v1_claim", payload["blockers"])

        full_gate = self.run_checker(
            "--release-statement",
            str(SCOPED_RELEASE_STATEMENT_TEMPLATE),
            "--json",
            check=False,
        )
        full_payload = json.loads(full_gate.stdout)
        self.assertEqual(full_gate.returncode, 1)
        self.assertFalse(full_payload["ready"])
        self.assertIn("v1_completion_required_false", full_payload["blockers"])

    def test_scoped_release_statement_rejects_alternate_non_complete_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            build_policy_checker = self.write_fake_structure_build_policy_checker(
                Path(temp_dir) / "fake_structure_build_policy.py"
            )
            statement = SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8").replace(
                "obelisk.inventory_items_mutation.v1: post-v1 -",
                "obelisk.inventory_items_mutation.v1: excluded -",
            )
            statement_path.write_text(statement, encoding="utf-8")

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--structure-build-policy-offline-intake",
                str(build_policy_checker),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        row = next(
            row
            for row in payload["v1_sdk_blocker_outcomes"]
            if row["surface"] == "obelisk.inventory_items_mutation.v1"
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertEqual(
            payload["scoped_release_statement"]["blocking_report_blockers"],
            ["release_statement_missing_non_promoted_blocker_outcomes"],
        )
        self.assertEqual(row["manifest_outcome"], "post-v1")
        self.assertEqual(row["release_statement_outcome"], "excluded")
        self.assertFalse(row["release_statement_outcome_matches_manifest"])
        self.assertEqual(row["required_release_statement_outcomes"], ["excluded", "post-v1"])
        self.assertFalse(row["release_statement_contract_satisfied"])
        self.assertFalse(row["counts_toward_complete_sdk_claim"])
        self.assertEqual(
            payload["release_statement_missing_blocker_outcomes"],
            ["obelisk.inventory_items_mutation.v1"],
        )
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertIn("v1_completion_required_false", payload["blockers"])

    def test_structure_excluded_outcome_is_bookkeeping_only_and_requires_exact_wording(self) -> None:
        surface_id = "obelisk.structure_census.v1"
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        for surface in manifest["surfaces"]:
            if surface["id"] == surface_id:
                surface["status"] = "excluded"
                surface["public_contract"] = []
                break
        manifest["planning_surfaces"] = [
            item for item in manifest["planning_surfaces"] if item != surface_id
        ]
        if surface_id not in manifest["post_v1_or_excluded_surfaces"]:
            manifest["post_v1_or_excluded_surfaces"].append(surface_id)

        exact_structure_exclusion = (
            f"{surface_id}: excluded - no StructureEvents SDK, structure census, "
            "structure identity, structure lookup, build placement policy, "
            "no-collision policy, or ownership lookup API is included in v1.\n"
        )
        exact_statement = (
            "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
            f"{exact_structure_exclusion}"
            "The complete SDK is ready.\n"
            "The full SDK is ready.\n"
            "The production SDK is ready.\n"
        )
        imprecise_statement = (
            "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
            f"{surface_id}: excluded - no StructureEvents SDK, structure census, "
            "structure identity, structure lookup, or build-policy API is included in v1.\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            exact_statement_path = Path(temp_dir) / "EXACT_RELEASE_STATEMENT.md"
            imprecise_statement_path = Path(temp_dir) / "IMPRECISE_RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            exact_statement_path.write_text(exact_statement, encoding="utf-8")
            imprecise_statement_path.write_text(imprecise_statement, encoding="utf-8")

            exact_result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(exact_statement_path),
                "--json",
                check=False,
            )
            imprecise_result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(imprecise_statement_path),
                "--json",
                check=False,
            )

        exact_payload = json.loads(exact_result.stdout)
        self.assertEqual(exact_result.returncode, 1)
        self.assertFalse(exact_payload["stable_claim_allowed"])
        self.assertFalse(exact_payload["v1_sdk_progress"]["stable_claim_allowed"])
        self.assertIn("release_statement_forbidden_broad_claims", exact_payload["blockers"])
        forbidden_claims = "\n".join(exact_payload["release_statement_forbidden_broad_claims"])
        for claim in ("complete SDK", "full SDK", "production SDK"):
            with self.subTest(claim=claim):
                self.assertIn(claim, forbidden_claims)
        self.assertEqual(exact_payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)
        self.assertEqual(
            exact_payload["v1_sdk_progress"]["p0_chain_scoped_non_complete_outcome_count"],
            0,
        )
        self.assertIn(
            surface_id,
            exact_payload["v1_sdk_progress"]["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
        )
        self.assertIn(
            surface_id,
            exact_payload["v1_sdk_progress"][
                "completion_blockers_with_release_statement_post_v1_or_excluded_outcome"
            ],
        )
        exact_row = next(
            row for row in exact_payload["v1_sdk_blocker_outcomes"] if row["surface"] == surface_id
        )
        self.assertFalse(exact_row["is_p0_dependency_chain"])
        self.assertEqual(exact_row["manifest_outcome"], "excluded")
        self.assertEqual(exact_row["release_statement_outcome"], "excluded")
        self.assertTrue(exact_row["release_statement_contract_satisfied"])
        self.assertFalse(exact_row["counts_toward_complete_sdk_claim"])
        self.assertTrue(exact_row["unresolved_for_complete_sdk_claim"])

        imprecise_payload = json.loads(imprecise_result.stdout)
        self.assertEqual(imprecise_result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", imprecise_payload["blockers"])
        self.assertEqual(imprecise_payload["release_statement_missing_exclusion_contracts"], [surface_id])
        self.assertNotIn(
            surface_id,
            imprecise_payload["v1_sdk_progress"][
                "completion_blockers_with_release_statement_post_v1_or_excluded_outcome"
            ],
        )
        imprecise_row = next(
            row for row in imprecise_payload["v1_sdk_blocker_outcomes"] if row["surface"] == surface_id
        )
        self.assertEqual(imprecise_row["release_statement_outcome"], "excluded")
        self.assertFalse(imprecise_row["release_statement_contract_satisfied"])
        self.assertFalse(imprecise_row["counts_toward_complete_sdk_claim"])

    def test_scoped_release_statement_scope_rejects_broad_v1_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "Inventory SDK is ready in v1.\n"
                + "SDK is stable.\n"
                + "API is production ready.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )

    def test_scoped_release_statement_scope_rejects_v1_surface_verb_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "v1 supports commands/replies.\n"
                + "Obelisk v1 ships commands/replies.\n"
                + "ResourceHandle is in v1.\n"
                + "v1 exposes player identity.\n"
                + "Plugin Hub opens for v1 packages.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "v1 supports commands/replies.",
            "Obelisk v1 ships commands/replies.",
            "ResourceHandle is in v1.",
            "v1 exposes player identity.",
            "Plugin Hub opens for v1 packages.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_scoped_release_statement_scope_rejects_active_release_verbs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "Obelisk SDK v1 ships today.\n"
                + "The complete SDK ships today.\n"
                + "The stable SDK launches today.\n"
                + "Obelisk SDK v1 is generally available.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        self.assertGreaterEqual(len(payload["release_statement_forbidden_broad_claims"]), 4)

    def test_scoped_release_statement_scope_rejects_ga_abbreviation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "Obelisk SDK v1 is GA.\n"
                + "Obelisk SDK v1 reaches GA today.\n"
                + "The v1 SDK is GA for plugin authors.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        self.assertIn("Obelisk SDK v1 is GA.", forbidden_claims)
        self.assertIn("Obelisk SDK v1 reaches GA today.", forbidden_claims)
        self.assertIn("The v1 SDK is GA for plugin authors.", forbidden_claims)

    def test_scoped_release_statement_scope_rejects_public_doc_broad_claim_variants(self) -> None:
        claims = [
            "SDK v1.0: stable.",
            "The complete-SDK is available.",
            "The GA SDK is published.",
            "The 1.0 stable SDK is ready.",
            "The stable public SDK is available.",
            "Obelisk v1.0 is stable.",
            "The public SDK is production.",
            "The SDK v1 is production.",
            "Blocked: The complete SDK is ready.",
            "Excluded surfaces: Inventory SDK is ready in v1.",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "\n".join(claims)
                + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertIn(claim, forbidden_claims)

    def test_scoped_release_statement_scope_rejects_production_grade_sdk_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "The production-grade SDK is available for v1 plugin authors.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )

    def test_scoped_release_statement_scope_rejects_bare_complete_full_stable_production_sdk_claims(self) -> None:
        claims = [
            "This is the complete SDK for plugin authors.",
            "This is the full SDK for plugin authors.",
            "This is the stable SDK for plugin authors.",
            "This is the production SDK for plugin authors.",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "\n".join(claims)
                + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertIn(claim, forbidden_claims)

    def test_scoped_release_statement_scope_rejects_unrelated_negator_complete_sdk_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "This is not just a runtime RC and the complete SDK is ready.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        self.assertIn(
            "This is not just a runtime RC and the complete SDK is ready.",
            "\n".join(payload["release_statement_forbidden_broad_claims"]),
        )

    def test_scoped_release_statement_scope_rejects_comma_detached_negated_broad_claim(self) -> None:
        claims = [
            "This is not a v1 stable claim, the complete SDK ships.",
            "This is not complete SDK, full SDK is ready.",
            "This is not a stable release, SDK v1 ships today.",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "\n".join(claims)
                + "\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertIn(claim, forbidden_claims)

    def test_scoped_release_statement_scope_allows_comma_separated_no_api_exclusion_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            build_policy_checker = self.write_fake_structure_build_policy_checker(
                Path(temp_dir) / "fake_structure_build_policy.py"
            )
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "obelisk.commands_replies.v1: excluded - no public command SDK/router, "
                "console command API, RCON command API, admin command API, player command API, "
                "chat replies, send-chat, broadcast/notices API, or moderation API is included in v1.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--structure-build-policy-offline-intake",
                str(build_policy_checker),
                "--validate-release-statement-scope",
                "--json",
            )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["scoped_release_statement"]["ready"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_scoped_release_statement_scope_rejects_affirmative_not_only_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "Not only is Inventory SDK ready for v1, command response is ready too.\n"
                + "Not merely is the complete SDK ready, it is stable.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        self.assertIn("Not only is Inventory SDK ready for v1", forbidden_claims)
        self.assertIn("Not merely is the complete SDK ready", forbidden_claims)

    def test_scoped_release_statement_scope_rejects_v1_stable_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "This is a v1.0 stable release.\n"
                + "This statement authorizes v1 stable wording.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        self.assertIn("This is a v1.0 stable release.", forbidden_claims)
        self.assertIn("This statement authorizes v1 stable wording.", forbidden_claims)

    def test_scoped_release_statement_scope_allows_negated_v1_stable_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            build_policy_checker = self.write_fake_structure_build_policy_checker(
                Path(temp_dir) / "fake_structure_build_policy.py"
            )
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "v1 stable remains blocked until the full gate passes.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--structure-build-policy-offline-intake",
                str(build_policy_checker),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["scoped_release_statement"]["ready"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], [])
        self.assertIn("v1_completion_required_false", payload["blockers"])

    def test_complete_claim_rejects_all_excluded_blockers_as_scoped_only(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            release_statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            build_policy_checker = self.write_fake_structure_build_policy_checker(
                Path(temp_dir) / "fake_structure_build_policy.py"
            )
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--json",
                check=False,
            )
            scoped_result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--structure-build-policy-offline-intake",
                str(build_policy_checker),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertTrue(payload["stable_release_contract_claim_allowed"])
        self.assertEqual(payload["installed_sdk_package_shape_guardrail_drift"], [])
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertIn("p0_dependency_chain_outcomes_scoped_non_complete_only", payload["blockers"])
        self.assertEqual(
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(payload["p0_dependency_chain_scoped_non_complete_outcome_count"], 4)
        self.assertEqual(
            payload["minimum_promoted_demand_family_gaps"],
            payload["minimum_promoted_demand_families"],
        )
        self.assertFalse(payload["v1_sdk_progress"]["stable_claim_allowed"])
        self.assertTrue(payload["v1_sdk_progress"]["stable_release_contract_claim_allowed"])
        self.assertEqual(payload["v1_sdk_progress"]["completion_blockers_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_scoped_non_complete_outcome_count"], 4)
        self.assertEqual(
            payload["v1_sdk_progress"]["p0_chain_scoped_non_complete_outcomes"],
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
        )
        self.assertIn(
            "do not increase p0_chain_promoted_count",
            payload["v1_sdk_progress"]["p0_chain_scoped_non_complete_note"],
        )
        self.assertEqual(payload["v1_sdk_progress"]["complete_sdk_claim_progress_percent"], 0)
        outcome_by_surface = {row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]}
        identity_outcome = outcome_by_surface["obelisk.player_identity.v1"]
        self.assertTrue(identity_outcome["is_p0_dependency_chain"])
        self.assertTrue(identity_outcome["scoped_non_complete_outcome_only"])
        self.assertFalse(identity_outcome["counts_toward_complete_sdk_claim"])
        self.assertTrue(identity_outcome["unresolved_for_complete_sdk_claim"])
        self.assertIn("scoped non-complete outcome only", identity_outcome["next_action"])
        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"]["p0_scoped_non_complete_outcomes"],
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["release_statement_bookkeeping"][
                "p0_scoped_non_complete_outcomes"
            ],
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["runtime_required_blockers"][
                "p0_scoped_non_complete_outcomes"
            ],
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
        )
        scoped_payload = json.loads(scoped_result.stdout)
        self.assertFalse(scoped_payload["ready"])
        self.assertFalse(scoped_payload["scoped_release_statement"]["ready"])
        self.assertFalse(scoped_payload["scoped_release_statement"]["stable_v1_sdk_claim_allowed"])
        self.assertIn(
            "complete_sdk_claim_requires_promoted_demand_families",
            scoped_payload["scoped_release_statement"]["allowed_remaining_blockers"],
        )
        self.assertIn(
            "p0_dependency_chain_outcomes_scoped_non_complete_only",
            scoped_payload["scoped_release_statement"]["allowed_remaining_blockers"],
        )
        self.assertEqual(
            scoped_payload["scoped_release_statement"]["blocking_report_blockers"],
            [
                "object_identity_resource_handle_readiness_blockers_not_empty",
                "object_identity_resource_handle_readiness_invalid",
                "object_identity_resource_handle_readiness_not_planning_only",
            ],
        )

    def test_minimum_promoted_demand_family_rejects_unreviewed_synthetic_equivalent(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        blocker_id = "obelisk.inventory_items_mutation.v1"
        equivalent_id = "obelisk.inventory_items_mutation_equivalent.v1"
        surfaces_by_id = {
            surface_id: {"id": surface_id, "status": "promoted"}
            for surface_id in module.CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
        }
        surfaces_by_id[blocker_id] = {"id": blocker_id, "status": "excluded"}
        surfaces_by_id[equivalent_id] = {
            "id": equivalent_id,
            "status": "promoted",
            "v1_completion_equivalent_for": [blocker_id],
            "evidence": {"tests": ["tests/sdk_consumer"]},
        }
        stable_contract = {
            "promoted_demand_family_equivalents": {
                blocker_id: equivalent_id,
            }
        }

        gaps, satisfied_by = module.complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract,
        )

        self.assertEqual(module.REVIEWED_V1_COMPLETION_EQUIVALENTS, {})
        self.assertFalse(module.reviewed_completion_equivalent_allowed(blocker_id, equivalent_id))
        self.assertTrue(module.surface_declares_completion_equivalent(surfaces_by_id[equivalent_id], blocker_id))
        self.assertIn(blocker_id, gaps)
        self.assertNotIn(blocker_id, satisfied_by)

    def test_minimum_promoted_demand_family_rejects_foundation_package_shape_equivalent(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        blocker_id = "obelisk.inventory_items_mutation.v1"
        equivalent_id = "obelisk.plugin_hub_foundation_package_shape_equivalent.v1"
        surfaces_by_id = {
            surface_id: {"id": surface_id, "status": "promoted"}
            for surface_id in module.CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
        }
        surfaces_by_id[blocker_id] = {"id": blocker_id, "status": "excluded"}
        surfaces_by_id[equivalent_id] = {
            "id": equivalent_id,
            "status": "promoted",
            "v1_completion_equivalent_for": [blocker_id],
            "evidence": {
                "tests": ["tests/sdk_consumer"],
                "schemas": ["obelisk.plugin-hub-foundation-package-shape.v1"],
            },
        }
        stable_contract = {
            "promoted_demand_family_equivalents": {
                blocker_id: equivalent_id,
            }
        }

        gaps, satisfied_by = module.complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract,
        )

        self.assertFalse(module.reviewed_completion_equivalent_allowed(blocker_id, equivalent_id))
        self.assertIn(blocker_id, gaps)
        self.assertNotIn(blocker_id, satisfied_by)

    def test_minimum_promoted_demand_family_rejects_p0_equivalent(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        blocker_id = "obelisk.player_identity.v1"
        equivalent_id = "obelisk.player_identity_equivalent.v1"
        surfaces_by_id = {
            surface_id: {"id": surface_id, "status": "promoted"}
            for surface_id in module.CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
        }
        surfaces_by_id[blocker_id] = {"id": blocker_id, "status": "excluded"}
        surfaces_by_id[equivalent_id] = {
            "id": equivalent_id,
            "status": "promoted",
            "v1_completion_equivalent_for": [blocker_id],
            "evidence": {"tests": ["tests/sdk_consumer"]},
        }
        stable_contract = {
            "promoted_demand_family_equivalents": {
                blocker_id: equivalent_id,
            }
        }

        gaps, satisfied_by = module.complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract,
        )

        self.assertIn(blocker_id, gaps)
        self.assertNotIn(blocker_id, satisfied_by)

    def test_minimum_promoted_demand_family_ignores_completion_equivalent_alias(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        blocker_id = "obelisk.inventory_items_mutation.v1"
        equivalent_id = "obelisk.inventory_items_mutation_alias_equivalent.v1"
        surfaces_by_id = {
            surface_id: {"id": surface_id, "status": "promoted"}
            for surface_id in module.CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
        }
        surfaces_by_id[blocker_id] = {"id": blocker_id, "status": "excluded"}
        surfaces_by_id[equivalent_id] = {
            "id": equivalent_id,
            "status": "promoted",
            "completion_equivalent_for": [blocker_id],
            "evidence": {"tests": ["tests/sdk_consumer"]},
        }
        stable_contract = {
            "promoted_demand_family_equivalents": {
                blocker_id: equivalent_id,
            }
        }

        gaps, satisfied_by = module.complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract,
        )

        self.assertFalse(module.surface_declares_completion_equivalent(surfaces_by_id[equivalent_id], blocker_id))
        self.assertIn(blocker_id, gaps)
        self.assertNotIn(blocker_id, satisfied_by)

    def test_promoted_experimental_only_gameplay_policy_event_cannot_count_as_completion_evidence(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        blocker_id = "obelisk.inventory_items_mutation.v1"
        equivalent_id = "obelisk.gameplay_policy_event.v1"
        gameplay_policy_event = {
            "id": equivalent_id,
            "status": "promoted-experimental-only",
            "v1_completion_equivalent_for": [blocker_id],
            "evidence": {
                "surface_id": equivalent_id,
                "promotion_status": "promoted",
                "public_sdk_ready": True,
                "abi_tests": ["tests/core/StructureEventDispatcherTests.cpp"],
                "sdk_consumer_tests": ["tests/sdk_consumer/CAbiPlugin.c"],
            },
        }
        surfaces_by_id = {
            surface_id: {"id": surface_id, "status": "promoted"}
            for surface_id in module.CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
        }
        surfaces_by_id[blocker_id] = {"id": blocker_id, "status": "excluded"}
        surfaces_by_id[equivalent_id] = gameplay_policy_event
        stable_contract = {
            "promoted_demand_family_equivalents": {
                blocker_id: equivalent_id,
            }
        }

        gaps, satisfied_by = module.complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract,
        )

        self.assertFalse(module.surface_has_promotion_evidence(gameplay_policy_event))
        self.assertIn(blocker_id, gaps)
        self.assertNotIn(blocker_id, satisfied_by)

    def test_empty_or_truncated_manifest_fails_closed(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": [],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("canonical_surface_id_missing", payload["blockers"])
        self.assertIn("canonical_v1_completion_blocker_missing", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["missing_canonical_surfaces"])
        self.assertIn("obelisk.player_identity.v1", payload["missing_canonical_completion_blockers"])

    def test_stable_release_contract_must_keep_canonical_claim_boundaries(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        manifest["stable_release_contract"]["claim_requires"] = [
            item
            for item in manifest["stable_release_contract"]["claim_requires"]
            if "promoted-experimental-only" not in item
        ]
        manifest["stable_release_contract"]["not_sufficient"] = [
            item
            for item in manifest["stable_release_contract"]["not_sufficient"]
            if item != "Foundation/Plugin Hub seed package shape"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            release_statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("stable_release_contract_claim_requires_incomplete", payload["blockers"])
        self.assertIn("stable_release_contract_not_sufficient_incomplete", payload["blockers"])
        self.assertEqual(
            payload["stable_release_contract_missing_claim_requires"],
            ["no promoted-experimental-only surface remains unresolved"],
        )
        self.assertEqual(
            payload["stable_release_contract_missing_not_sufficient"],
            ["Foundation/Plugin Hub seed package shape"],
        )

    def test_stable_release_contract_rejects_ambiguous_demand_family_equivalent_text(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        canonical = (
            "non-P0 minimum promoted demand families are promoted or satisfied by explicit "
            "v1_completion_equivalent_for records before complete/full/production SDK wording; "
            "no demand-family equivalent or legacy completion alias may satisfy a P0 dependency-chain surface"
        )
        legacy = (
            "minimum promoted demand families are promoted or satisfied by explicit completion "
            "equivalents before complete/full/production SDK wording"
        )
        manifest["stable_release_contract"]["claim_requires"] = [
            legacy if item == canonical else item
            for item in manifest["stable_release_contract"]["claim_requires"]
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            release_statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("stable_release_contract_claim_requires_incomplete", payload["blockers"])
        self.assertIn(canonical, payload["stable_release_contract_missing_claim_requires"])

    def test_installed_sdk_package_shape_must_remain_non_claim_evidence(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["installed_sdk_package_shape"]["status"] = "plugin-hub-seed-ready"
        manifest["installed_sdk_package_shape"]["not_sufficient_for"] = [
            item
            for item in manifest["installed_sdk_package_shape"]["not_sufficient_for"]
            if item
            not in {
                "Plugin Hub seed/package publication",
                "release package readiness or public package availability",
            }
        ]
        manifest["installed_sdk_package_shape"]["release_package_ready"] = True
        manifest["installed_sdk_package_shape"]["public_package_published"] = "published"
        manifest["installed_sdk_package_shape"]["release_package_available"] = True
        manifest["installed_sdk_package_shape"]["sdk_package_ready"] = "ready"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("installed_sdk_package_shape_guardrail_incomplete", payload["blockers"])
        self.assertIn("status", payload["installed_sdk_package_shape_guardrail_drift"])
        self.assertIn(
            "not_sufficient_for:Plugin Hub seed/package publication",
            payload["installed_sdk_package_shape_guardrail_drift"],
        )
        self.assertIn(
            "not_sufficient_for:release package readiness or public package availability",
            payload["installed_sdk_package_shape_guardrail_drift"],
        )
        self.assertIn(
            "positive_claim:release_package_ready",
            payload["installed_sdk_package_shape_guardrail_drift"],
        )
        self.assertIn(
            "positive_claim:public_package_published",
            payload["installed_sdk_package_shape_guardrail_drift"],
        )
        self.assertIn(
            "positive_claim:release_package_available",
            payload["installed_sdk_package_shape_guardrail_drift"],
        )
        self.assertIn(
            "positive_claim:sdk_package_ready",
            payload["installed_sdk_package_shape_guardrail_drift"],
        )

    def test_installed_sdk_package_shape_canonical_files_are_required(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["installed_sdk_package_shape"]["installed_files"].append(
            "lib/cmake/Obelisk/PluginHubTargets.cmake"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("installed_sdk_package_shape_guardrail_incomplete", payload["blockers"])
        self.assertIn("installed_files", payload["installed_sdk_package_shape_guardrail_drift"])

    def test_release_statement_must_name_non_promoted_blockers(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_negated_or_global_outcome_wording(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1 is intentionally not described here as excluded.\n"
                "Other items may be post-v1.\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_ambiguous_outcome_punctuation(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.player_identity.v1: excluded -",
            "obelisk.player_identity.v1: excluded? actually included -",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["release_statement_missing_blocker_outcomes"])

    def test_release_statement_rejects_negated_contract_substring_in_surface_record(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "planning_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded - it is false that no player identity API is included in v1\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_not_the_case_negation(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "planning_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded - it is not the case that "
                "no player identity API is included in v1\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_contradictory_exception_after_required_text(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "planning_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded - no player identity API is included in v1; "
                "except player identity is included in v1 for admins.\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_complete_sdk_claim_after_excluded_blocker_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = "\n".join(
            (
                line + "; Inventory SDK is a complete SDK for v1 plugin authors."
                if line.startswith("obelisk.inventory_items_mutation.v1: excluded -")
                else line
            )
            for line in release_statement.splitlines()
        ) + "\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "obelisk.inventory_items_mutation.v1",
            payload["release_statement_missing_exclusion_contracts"],
        )

    def test_release_statement_rejects_available_support_claim_after_post_v1_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.commands_replies.v1":
                surface["status"] = "post-v1"
                break
        release_statement = "\n".join(
            (
                line.replace("obelisk.commands_replies.v1: excluded -", "obelisk.commands_replies.v1: post-v1 -")
                + "; command router support is available in v1."
                if line.startswith("obelisk.commands_replies.v1: excluded -")
                else line
            )
            for line in release_statement.splitlines()
        ) + "\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn("obelisk.commands_replies.v1", payload["release_statement_missing_exclusion_contracts"])

    def test_release_statement_rejects_global_complete_sdk_claim_for_excluded_blocker(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += "Release summary: Inventory SDK is a complete SDK for v1 plugin authors.\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "obelisk.inventory_items_mutation.v1",
            payload["release_statement_missing_exclusion_contracts"],
        )

    def test_release_statement_rejects_ready_claims_for_inventory_items_and_plugin_hub(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Inventory SDK is ready in v1.\n"
            "Items SDK is ready in v1.\n"
            "Obelisk SDK v1 is ready.\n"
            "Obelisk SDK v1 is production ready.\n"
            "Plugin Hub completion is ready for v1.\n"
            "Plugin Hub is complete for v1 plugin authors.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Inventory SDK is ready in v1.",
            "Items SDK is ready in v1.",
            "Obelisk SDK v1 is ready.",
            "Obelisk SDK v1 is production ready.",
            "Plugin Hub completion is ready for v1.",
            "Plugin Hub is complete for v1 plugin authors.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_allows_negated_inventory_items_and_plugin_hub_claims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Inventory SDK is not ready in v1.\n"
            "Items SDK is not ready in v1.\n"
            "Plugin Hub completion remains blocked for v1.\n"
            "Plugin Hub is not complete for v1 plugin authors.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_release_statement_allows_plugin_hub_post_sdk_deferred_wording(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Plugin Hub post-SDK-complete planning remains parked.\n"
            "Plugin Hub seed/package publication remains post-SDK.\n"
            "Plugin Hub work resumes after SDK completion.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_release_statement_rejects_plugin_hub_publication_and_scope_overclaims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Plugin Hub is included in v1.\n"
            "Plugin Hub API is public.\n"
            "Plugin Hub package is published for v1.\n"
            "Plugin Hub publication is in release scope.\n"
            "Stable SDK includes Plugin Hub.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Plugin Hub is included in v1.",
            "Plugin Hub API is public.",
            "Plugin Hub package is published for v1.",
            "Plugin Hub publication is in release scope.",
            "Stable SDK includes Plugin Hub.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_rejects_identity_permissions_command_mission_buff_claims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Player identity SDK is ready in v1.\n"
            "Permissions/admin SDK is supported in v1.\n"
            "Command response API is available in v1.\n"
            "Commands/replies API is included in v1.\n"
            "Mission SDK is ready in v1.\n"
            "Buff SDK is supported in v1.\n"
            "Buff/status SDK is included in v1.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Player identity SDK is ready in v1.",
            "Permissions/admin SDK is supported in v1.",
            "Command response API is available in v1.",
            "Commands/replies API is included in v1.",
            "Mission SDK is ready in v1.",
            "Buff SDK is supported in v1.",
            "Buff/status SDK is included in v1.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_rejects_v1_includes_blocked_surface_claims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "v1 includes player identity.\n"
            "v1 includes command replies.\n"
            "v1 includes ResourceHandle/object lookup.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["v1_sdk_progress"]["stable_claim_allowed"])
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "v1 includes player identity.",
            "v1 includes command replies.",
            "v1 includes ResourceHandle/object lookup.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_allows_negated_identity_permissions_command_mission_buff_boundaries(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Player identity SDK is not ready in v1.\n"
            "Permissions/admin SDK remains blocked in v1.\n"
            "Command response API is not available in v1.\n"
            "Commands/replies API is not included in v1.\n"
            "Mission SDK is not ready in v1.\n"
            "Buff SDK is not supported in v1.\n"
            "Buff/status SDK is not included in v1.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_release_statement_rejects_non_promotional_evidence_as_v1_claim_basis(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Candidate evidence proves a complete SDK for v1 plugin authors.\n"
            "Static orientation readiness makes the public SDK ready.\n"
            "Consume-only planning evidence validates v1.0 stable.\n"
            "Foundation package shape support is production-ready SDK support.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Candidate evidence proves a complete SDK for v1 plugin authors.",
            "Static orientation readiness makes the public SDK ready.",
            "Consume-only planning evidence validates v1.0 stable.",
            "Foundation package shape support is production-ready SDK support.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_rejects_installed_sdk_package_readiness_claims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "The installed SDK package is ready for public use.\n"
            "The SDK package is available for plugin authors.\n"
            "The public SDK package is published.\n"
            "The release package reaches GA today.\n"
            "The SDK support tier is release-supported seed.\n"
            "Package shape declares support_tier=release-supported seed.\n"
            "The installed SDK package is package-shape evidence only, not release package readiness.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["installed_sdk_package_shape_guardrail_drift"], [])
        self.assertFalse(payload["stable_claim_allowed"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "The installed SDK package is ready for public use.",
            "The SDK package is available for plugin authors.",
            "The public SDK package is published.",
            "The release package reaches GA today.",
            "The SDK support tier is release-supported seed.",
            "Package shape declares support_tier=release-supported seed.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)
        self.assertNotIn("package-shape evidence only", forbidden_claims)

    def test_release_statement_rejects_without_prefixed_affirmative_claims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Without promotion, Inventory SDK is ready in v1.\n"
            "Without promoted dependencies, command router support is available in v1.\n"
            "Without evidence, Candidate evidence proves a complete SDK for v1 plugin authors.\n"
            "Blocked by missing evidence the stable SDK is ready.\n"
            "v1.0 stable is blocked but ready.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Without promotion, Inventory SDK is ready in v1.",
            "Without evidence, Candidate evidence proves a complete SDK for v1 plugin authors.",
            "Blocked by missing evidence the stable SDK is ready.",
            "v1.0 stable is blocked but ready.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "obelisk.commands_replies.v1",
            payload["release_statement_missing_exclusion_contracts"],
        )

    def test_release_statement_allows_negated_non_promotional_evidence_boundaries(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Candidate evidence does not prove a complete SDK for v1 plugin authors.\n"
            "Static orientation readiness is not public SDK readiness.\n"
            "Consume-only planning evidence does not validate v1.0 stable.\n"
            "Foundation package shape support is not production-ready SDK support.\n"
            "Without promoted demand families, no complete SDK claim is allowed.\n"
            "The stable SDK remains blocked.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_release_statement_rejects_blocked_claim_inside_other_surface_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.chat_message.v1: excluded - ChatMessageEvent is not included in v1.",
            "obelisk.chat_message.v1: excluded - ChatMessageEvent is not included in v1; chat replies are included in v1.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn("obelisk.commands_replies.v1", payload["release_statement_missing_exclusion_contracts"])

    def test_release_statement_rejects_side_lane_claim_inside_other_surface_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.inventory_item_copied_signals.v1: excluded - inventory copied signals are not included in v1.",
            "obelisk.inventory_item_copied_signals.v1: excluded - inventory copied signals are not included in v1; Mission SDK is included in v1.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "obelisk.mission_transfer_dino_tribe.v1",
            payload["release_statement_missing_exclusion_contracts"],
        )

    def test_release_statement_umbrella_mission_exclusion_requires_leaf_outcomes(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "; mission excluded; transfer excluded; dino_policy excluded; tribe_policy excluded; buff_status excluded",
            "",
        )
        surface = next(
            surface
            for surface in manifest["surfaces"]
            if surface["id"] == "obelisk.mission_transfer_dino_tribe.v1"
        )
        for leaf in surface["leaf_decision_units"]:
            leaf["status"] = "planning"

        self.assertFalse(release_statement_satisfies_exclusion_contract(release_statement, surface))
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("mission_transfer_dino_tribe_outcome_accounting_invalid", payload["blockers"])
        self.assertIn("mission_transfer_dino_tribe_outcome_accounting_blockers_not_empty", payload["blockers"])
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "release_statement_leaf_exclusions_missing",
            payload["mission_transfer_dino_tribe_outcome_accounting"]["blockers"],
        )
        self.assertFalse(payload["mission_transfer_dino_tribe_outcome_accounting"]["v1_accounted"])

    def test_release_statement_rejects_duplicate_or_mixed_surface_records(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "obelisk.player_identity.v1: post-v1 - contradictory duplicate record for the same surface.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_duplicate_or_mixed_surface_records", payload["blockers"])
        self.assertEqual(payload["release_statement_duplicate_or_mixed_records"], ["obelisk.player_identity.v1"])

    def test_release_statement_accepts_exact_outcome_with_no_explanatory_text(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.player_identity.v1: excluded - no public API for this surface is included in v1; "
            "no player identity/principal, player lookup, cross-instance identity, session lifecycle, "
            "permissions/admin, commands/replies, economy/mobility, mutation, return override, "
            "ResourceHandle, UE pointer, raw params, or UObject identity API is included in v1\n",
            "obelisk.player_identity.v1: excluded - no player identity/principal, player lookup, "
            "cross-instance identity, session lifecycle, permissions/admin, commands/replies, "
            "economy/mobility, mutation, return override, ResourceHandle, UE pointer, raw params, "
            "or UObject identity API is included in v1\n",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])

    def test_release_statement_must_satisfy_surface_exclusion_contract(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_non_promoted_public_contract_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.commands_replies.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.commands_replies.v1"],
            "surfaces": [
                {
                    "id": "obelisk.commands_replies.v1",
                    "status": "post-v1",
                    "public_contract": ["RegisterCommand"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertEqual(payload["non_promoted_with_public_contract"], ["obelisk.commands_replies.v1"])

    def test_non_promoted_public_abi_blocks_claim_even_with_promoted_dependencies(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] in {
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
            }:
                surface["status"] = "promoted"
                surface["public_contract"] = [f"{surface['id']}.placeholder"]
                surface["evidence"] = {
                    "surface_id": surface["id"],
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/abi/player_identity_placeholder"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_placeholder"],
                    "terms": [
                        "obelisk.core-dump-evidence-pack.v1",
                        "obelisk.reflection-inventory-pack.v1",
                        "ServerListPlayers",
                        "ServerKickPlayer",
                    ],
                }
            if surface["id"] == "obelisk.command_chat_response_path.v1":
                surface["public_abi"] = True
        manifest["promoted_surfaces"].extend(
            ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"]
        )
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id
            not in {
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("non_promoted_surface_has_public_abi", payload["blockers"])
        self.assertEqual(
            payload["non_promoted_with_public_abi"],
            ["obelisk.command_chat_response_path.v1"],
        )

    def test_status_experimental_surface_omitted_from_top_level_list_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": [],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [
                {
                    "id": "obelisk.chat_message.v1",
                    "status": "promoted-experimental-only",
                    "public_contract": ["RegisterChatCallback"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("experimental_surface_list_mismatch", payload["blockers"])
        self.assertIn("promoted_experimental_surfaces_unresolved", payload["blockers"])
        self.assertEqual(payload["experimental_list_mismatches"], ["obelisk.chat_message.v1"])
        self.assertEqual(payload["unresolved_experimental_surfaces"], ["obelisk.chat_message.v1"])

    def test_experimental_surface_exclusion_requires_release_statement_outcome(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = "\n".join(
            line for line in release_statement.splitlines() if "obelisk.chat_message.v1" not in line
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_experimental_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_experimental_outcomes"], ["obelisk.chat_message.v1"])

    def test_experimental_surface_exclusion_requires_specific_surface_terms(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.chat_message.v1: excluded - ChatMessageEvent is not included in v1.",
            "obelisk.chat_message.v1: excluded - later.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_experimental_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_experimental_outcomes"], ["obelisk.chat_message.v1"])

    def test_completion_blocker_status_must_match_required_release_outcome(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.structure_census.v1":
                surface["status"] = "post-v1"
                break
        manifest["post_v1_or_excluded_surfaces"].append("obelisk.structure_census.v1")
        release_statement = release_statement.replace(
            "obelisk.structure_census.v1: excluded -",
            "obelisk.structure_census.v1: post-v1 -",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.structure_census.v1"])

    def test_docs_only_promotion_evidence_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": ["obelisk.player_identity.v1"],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "promoted",
                    "public_contract": ["ObeliskApi.RegisterPlayerIdentityCallback"],
                    "evidence": {"docs": ["TODO-only-doc.md"]},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_fake_promotion_evidence_path_blocks_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["TODO-not-a-real-test"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_generic_existing_directory_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["tests/sdk_consumer"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_absolute_external_evidence_path_blocks_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["/tmp"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_existing_generic_script_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["scripts/check_release_readiness.sh"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_plugin_hub_package_shape_evidence_does_not_promote_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPluginHubFoundation",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_plugin_hub_foundation",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPluginHubFoundationTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_plugin_hub_foundation_plugin.c"
            core_test.write_text("// Plugin Hub package shape placeholder\n", encoding="utf-8")
            sdk_test.write_text("// Plugin Hub package shape consumer placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "schemas": ["obelisk.plugin-hub-foundation-package-shape.v1"],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_core_first_and_copied_seed_terms_do_not_promote_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity SDK placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "runtime/core-first RC readiness",
                            "GameplayPolicyEvent, ChatMessageEvent, and inventory item copied-signal seeds",
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_player_identity_requires_runtime_privacy_abi_and_sdk_evidence_terms(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity SDK placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_required_evidence_terms_missing", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_missing_required_evidence_terms"]["obelisk.player_identity.v1"],
            [
                "accepted login/logout lifecycle ordering and principal invalidation semantics",
                "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                "approved runtime principal lifecycle evidence",
                "principal privacy, invalidation, and cross-instance semantics",
            ],
        )

    def test_player_identity_required_terms_do_not_replace_structured_promotion_evidence(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity SDK placeholder\n", encoding="utf-8")
            manifest, release_statement = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            release_statement = "\n".join(
                (
                    "obelisk.player_identity.v1: promoted - reviewed ABI and SDK evidence."
                    if line.startswith("obelisk.player_identity.v1:")
                    else line
                )
                for line in release_statement.splitlines()
            ) + "\n"
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            statement_path = Path(core_dir) / "RELEASE_STATEMENT.md"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertNotIn("promoted_surface_required_evidence_terms_missing", payload["blockers"])
        self.assertIn("promoted_surface_structured_evidence_missing", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_missing_structured_evidence"]["obelisk.player_identity.v1"],
            [
                "approved_runtime_evidence_manifest:missing",
                "approved_runtime_evidence_report:missing",
                "executed_test_report:missing",
                "public_contract_readiness_report:missing",
            ],
        )

    def test_identity_structured_contract_report_must_keep_public_contract_blocker(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            root = Path(core_dir)
            runtime_manifest = root / "approved-runtime-principal-lifecycle-evidence.json"
            runtime_report = root / "player_identity_approved_runtime_report.json"
            contract_report = root / "player_identity_public_contract_readiness_report.json"
            executed_report = root / "player_identity_executed_tests.json"
            runtime_manifest_binding = self.write_approved_runtime_manifest_binding(runtime_manifest)
            runtime_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                        "ready_scope": "runtime_evidence_only",
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "next_blocker": "identity_public_contract_gate_missing",
                    }
                ),
                encoding="utf-8",
            )
            contract_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-identity-public-contract-readiness-check.v1",
                        "ready_scope": "contract_review_input_only",
                        "surface": "obelisk.player_identity.v1",
                        "accepted_for_contract_review": True,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "public_header_allowed": False,
                        "approved_runtime_evidence": {
                            "approved_runtime_evidence_present": True,
                            "runtime_evidence_ready": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            executed_report_path = write_executed_test_artifact(
                executed_report,
                "obelisk.player_identity.v1",
                argv=["python3", "-m", "unittest", "player_identity_promotion"],
            )
            missing = player_identity_structured_promotion_evidence_missing(
                {
                    "approved_runtime_evidence_manifest": runtime_manifest_binding,
                    "approved_runtime_evidence_report": str(runtime_report.relative_to(REPO_ROOT)),
                    "public_contract_readiness_report": str(contract_report.relative_to(REPO_ROOT)),
                    "executed_test_report": executed_report_path,
                }
            )

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)

    def test_bundle_builder_ready_scope_does_not_count_as_promotion_evidence(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity SDK placeholder\n", encoding="utf-8")

            promoted = surface_has_promotion_evidence(
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "promoted",
                    "evidence": {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "ready_scope": "bundle_builder_inputs_only",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                    },
                }
            )

        self.assertFalse(promoted)

    def test_live_ops_sidecars_do_not_count_as_promotion_evidence(self) -> None:
        base_evidence = {
            "surface_id": "obelisk.player_identity.v1",
            "promotion_status": "promoted",
            "public_sdk_ready": True,
            "abi_tests": ["tests/core/player_identity_promotion.cpp"],
            "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_promotion.c"],
        }
        cases = (
            {
                **base_evidence,
                "ready_scope": "request_pack_only",
            },
            {
                **base_evidence,
                "ready_scope": "request_pack",
            },
            {
                **base_evidence,
                "ready_scope": "operator_approval_receipt_only",
            },
            {
                **base_evidence,
                "ready_scope": "operator_approval_receipt",
            },
            {
                **base_evidence,
                "ready_scope": "operator_receipt_only",
            },
            {
                **base_evidence,
                "ready_scope": "operator_receipt",
            },
            {
                **base_evidence,
                "ready_scope": "preflight_only",
            },
            {
                **base_evidence,
                "ready_scope": "preflight",
            },
            {
                **base_evidence,
                "ready_scope": "post_window_replay_only",
            },
            {
                **base_evidence,
                "ready_scope": "runtime_replay_fixture",
            },
            {
                **base_evidence,
                "ready_scope": "window_manifest_only",
            },
            {
                **base_evidence,
                "ready_scope": "window_manifest",
            },
            {
                **base_evidence,
                "ready_scope": "live_validation_sidecar_only",
            },
            {
                **base_evidence,
                "ready_scope": "live_validation_sidecar",
            },
            {
                **base_evidence,
                "ready_scope": "live_ops_sidecar_only",
            },
            {
                **base_evidence,
                "ready_scope": "live_ops_sidecar",
            },
            {
                **base_evidence,
                "ready_scope": "placeholder_provenance",
            },
            {
                **base_evidence,
                "sidecars": [
                    {
                        "schema": "obelisk.player-principal-lifecycle-preflight.v1",
                        "ready": True,
                        "server_operations_authorized": False,
                        "runtime_work_authorized": False,
                        "runtime_ready": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "v1_completion_ready": False,
                    },
                    {
                        "schema": "obelisk.player-principal-lifecycle-window-request.v1",
                        "prepared_at_utc": "2026-06-02T00:00:00+00:00",
                    },
                    {
                        "schema": "obelisk.operator-approval-receipt.v1",
                        "server_operations_authorized_by_template": False,
                    },
                    {
                        "schema": "obelisk.operator-receipt.v1",
                        "source_kind": "operator_receipt",
                    },
                    {
                        "schema": "obelisk.live-ops-sidecar.v1",
                        "evidence_kind": "live_ops_sidecar",
                    },
                ],
            },
            {
                **base_evidence,
                "source_kind": "live-ops",
            },
            {
                **base_evidence,
                "evidence_kind": "live-validation-sidecar",
            },
            {
                **base_evidence,
                "schemas": ["obelisk.player-identity-approved-bundle.v1"],
            },
            {
                **base_evidence,
                "schemas": ["obelisk.placeholder-provenance.v1"],
            },
            {
                **base_evidence,
                "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1",
            },
            {
                **base_evidence,
                "schemas": ["obelisk.players-identity-runtime-principal-lifecycle-evidence.v1"],
            },
            {
                **base_evidence,
                "schemas": ["obelisk.player-identity-approved-runtime-replay-fixture.v1"],
            },
            {
                **base_evidence,
                "source_kind": "runtime-principal-lifecycle-evidence",
            },
            {
                **base_evidence,
                "source_kind": "post-window-runtime-replay",
            },
            {
                **base_evidence,
                "abi_tests": ["tests/core/player_identity_approved_bundle.cpp"],
                "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_approved_bundle.c"],
            },
            {
                **base_evidence,
                "abi_tests": ["tests/core/player_identity_runtime_replay.cpp"],
                "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_runtime_replay.c"],
            },
            {
                **base_evidence,
                "abi_tests": ["tests/core/player_identity_placeholder_provenance.cpp"],
                "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_placeholder_provenance.c"],
            },
        )
        for evidence in cases:
            with self.subTest(evidence=evidence):
                promoted = surface_has_promotion_evidence(
                    {
                        "id": "obelisk.player_identity.v1",
                        "status": "promoted",
                        "evidence": evidence,
                    }
                )
                self.assertFalse(promoted)

    def test_player_identity_structured_promotion_requires_runtime_evidence_ready_scope(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            runtime_path = REPO_ROOT / artifacts["approved_runtime_evidence_report"]
            runtime_report = json.loads(runtime_path.read_text(encoding="utf-8"))
            runtime_report["ready_scope"] = "bundle_builder_inputs_only"
            runtime_path.write_text(json.dumps(runtime_report, sort_keys=True), encoding="utf-8")

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("approved_runtime_evidence_report:fields_invalid", missing)

    def test_player_identity_structured_promotion_requires_contract_review_ready_scope(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            contract_path = REPO_ROOT / artifacts["public_contract_readiness_report"]
            contract_report = json.loads(contract_path.read_text(encoding="utf-8"))
            contract_report["ready_scope"] = "bundle_builder_inputs_only"
            contract_path.write_text(json.dumps(contract_report, sort_keys=True), encoding="utf-8")

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)

    def test_player_identity_structured_promotion_rejects_source_less_runtime_report(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            artifacts.pop("approved_runtime_evidence_manifest")

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("approved_runtime_evidence_manifest:missing", missing)

    def test_player_identity_structured_promotion_rejects_runtime_manifest_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            binding = dict(artifacts["approved_runtime_evidence_manifest"])
            binding["sha256"] = "0" * 64
            artifacts["approved_runtime_evidence_manifest"] = binding

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("approved_runtime_evidence_manifest:sha256_mismatch", missing)

    def test_identity_structured_contract_report_rejects_public_surface_openings(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            contract_path = REPO_ROOT / artifacts["public_contract_readiness_report"]
            contract_report = json.loads(contract_path.read_text(encoding="utf-8"))
            contract_report["public_contract_allowed"] = True
            contract_report["public_header_symbols_now"] = ["ObeliskPlayerPrincipalEvent"]
            contract_report["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
            contract_report["public_callback_abi_now"] = ["ObeliskPlayerPrincipalCallback"]
            contract_path.write_text(json.dumps(contract_report, sort_keys=True), encoding="utf-8")

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)

    def test_identity_structured_contract_report_with_redaction_input_still_does_not_count_for_promotion(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            contract_path = REPO_ROOT / artifacts["public_contract_readiness_report"]
            contract_report = json.loads(contract_path.read_text(encoding="utf-8"))
            contract_report["resolved_inputs"] = [
                "runtime.lifecycle_evidence",
                "privacy.identifier_redaction",
            ]
            contract_path.write_text(json.dumps(contract_report, sort_keys=True), encoding="utf-8")

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)
        self.assertIn("public_contract_readiness_report:promotion_blockers_remaining", missing)
        self.assertIn("public_contract_readiness_report:private_candidate_contract_candidate_only", missing)

    def test_identity_structured_contract_report_requires_contract_gate_inputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            contract_path = REPO_ROOT / artifacts["public_contract_readiness_report"]
            contract_report = json.loads(contract_path.read_text(encoding="utf-8"))
            contract_report.pop("contract_gate_inputs")
            contract_path.write_text(json.dumps(contract_report, sort_keys=True), encoding="utf-8")

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)
        self.assertIn("public_contract_readiness_report:contract_gate_inputs_invalid", missing)

    def test_identity_structured_contract_report_rejects_contract_gate_input_overclaims(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            contract_path = REPO_ROOT / artifacts["public_contract_readiness_report"]
            contract_report = json.loads(contract_path.read_text(encoding="utf-8"))
            contract_report["contract_gate_inputs"][1]["promotion_ready"] = True
            contract_report["contract_gate_inputs"][1]["v1_completion_evidence"] = True
            contract_path.write_text(json.dumps(contract_report, sort_keys=True), encoding="utf-8")

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)
        self.assertIn("public_contract_readiness_report:contract_gate_inputs_invalid", missing)
        self.assertIn("public_contract_readiness_report:public_or_runtime_claim_without_blocker", missing)

    def test_identity_structured_contract_report_rejects_nested_overclaims(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests" / "core", prefix="PlayerIdentityEvidence") as core_dir:
            artifacts = self.write_player_identity_structured_promotion_artifacts(Path(core_dir))
            contract_path = REPO_ROOT / artifacts["public_contract_readiness_report"]
            contract_report = json.loads(contract_path.read_text(encoding="utf-8"))
            contract_report["nested_claims"] = {
                "public_sdk_ready": True,
                "stable_claim_allowed": True,
            }
            contract_path.write_text(json.dumps(contract_report, sort_keys=True), encoding="utf-8")

            missing = player_identity_structured_promotion_evidence_missing(artifacts)

        self.assertIn("public_contract_readiness_report:public_or_runtime_claim_without_blocker", missing)
        self.assertIn("public_contract_readiness_report:completion_claim_without_blocker", missing)
        self.assertNotIn("public_contract_readiness_report:contract_gate_inputs_invalid", missing)

    def test_identity_structured_contract_report_rejects_legacy_next_blocker_alias(self) -> None:
        missing = self.identity_structured_missing_for_contract_report(
            {
                "schema": "obelisk.player-identity-public-contract-readiness-check.v1",
                "ready": True,
                "ready_scope": "contract_review_input_only",
                "surface": "obelisk.player_identity.v1",
                "accepted_for_contract_review": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_contract_allowed": False,
                "public_header_allowed": False,
                "public_header_symbols_now": [],
                "public_capability_bits_now": [],
                "public_callback_abi_now": [],
                "next_blocker": "identity_public_contract_gate",
                "blockers": [],
                "resolved_inputs": ["runtime.lifecycle_evidence"],
                "remaining_blockers": [
                    "runtime.lifecycle_evidence",
                    "privacy.identifier_redaction",
                    "lifetime.generation_scope_invalidation",
                    "abi.public_pod_contract",
                    "lifecycle.owner_cleanup",
                    "separation.downstream_surfaces",
                ],
                "approved_runtime_evidence": {
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
            }
        )

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)

    def test_identity_structured_contract_report_must_keep_full_blocker_set(self) -> None:
        missing = self.identity_structured_missing_for_contract_report(
            {
                "schema": "obelisk.player-identity-public-contract-readiness-check.v1",
                "surface": "obelisk.player_identity.v1",
                "accepted_for_contract_review": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "next_blocker": "identity_public_contract_gate_missing",
                "blockers": [],
                "resolved_inputs": ["runtime.lifecycle_evidence"],
                "remaining_blockers": ["privacy.identifier_redaction"],
                "approved_runtime_evidence": {
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
            }
        )

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)

    def test_identity_structured_contract_report_must_have_no_checker_blockers(self) -> None:
        missing = self.identity_structured_missing_for_contract_report(
            {
                "schema": "obelisk.player-identity-public-contract-readiness-check.v1",
                "surface": "obelisk.player_identity.v1",
                "accepted_for_contract_review": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "next_blocker": "identity_public_contract_gate_missing",
                "blockers": ["public_header_allowed_not_false"],
                "resolved_inputs": ["runtime.lifecycle_evidence"],
                "remaining_blockers": [
                    "runtime.lifecycle_evidence",
                    "privacy.identifier_redaction",
                    "lifetime.generation_scope_invalidation",
                    "abi.public_pod_contract",
                    "lifecycle.owner_cleanup",
                    "separation.downstream_surfaces",
                ],
                "approved_runtime_evidence": {
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                },
            }
        )

        self.assertIn("public_contract_readiness_report:fields_invalid", missing)
        self.assertIn("public_contract_readiness_report:promotion_blockers_remaining", missing)

    def test_candidate_only_player_identity_preflight_test_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                    "sdk_consumer_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_private_pod_layout_candidate_report_does_not_promote_identity_abi_tests(self) -> None:
        manifest, _ = complete_excluded_manifest()
        private_layout = "docs/research/player-identity-planning-sources/player-identity-private-pod-layout-candidate.json"
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": [private_layout],
                    "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_promotion_plugin.c"],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_static_orientation_report_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["docs/research/2026-05-31-player-identity-static-target-orientation.json"],
                    "sdk_consumer_tests": [
                        "docs/research/2026-05-31-player-identity-static-target-orientation.json"
                    ],
                    "schemas": [
                        "obelisk.player-identity-static-orientation-check.v1",
                        "obelisk.player-identity-static-admin-thunks-check.v1",
                        "obelisk.static-candidate-orientation-contract.v1",
                    ],
                    "terms": [
                        "obelisk.core-dump-evidence-pack.v1",
                        "obelisk.reflection-inventory-pack.v1",
                        "ServerListPlayers",
                        "ServerKickPlayer",
                    ],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.player_identity.v1"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_static_orientation_named_tests_do_not_promote_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityStaticOrientation",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_static_orientation",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityAdminThunksTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_admin_thunks_plugin.c"
            core_test.write_text("// candidate-only player identity admin thunks test\n", encoding="utf-8")
            sdk_test.write_text("// candidate-only player identity admin thunks consumer\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_static_orientation_schema_does_not_promote_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI test placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity consumer placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "schemas": [
                            "obelisk.player-identity-static-orientation-check.v1",
                            "obelisk.player-identity-static-admin-thunks-check.v1",
                            "obelisk.static-candidate-orientation-contract.v1",
                        ],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_lifecycle_anchor_and_principal_policy_schemas_do_not_promote_player_identity(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI test placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity consumer placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "runtime_ready": True,
                        "schemas": [
                            "obelisk.players-identity-lifecycle-anchor-candidates.v1",
                            "obelisk.players-identity-principal-invalidation-policy.v1",
                        ],
                        "blockers": ["approved_runtime_evidence_missing"],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_lifecycle_anchor_report_alone_does_not_promote_player_identity(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI test placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity consumer placeholder\n", encoding="utf-8")

            promoted = surface_has_promotion_evidence(
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "promoted",
                    "evidence": {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "runtime_ready": True,
                        "schema": "obelisk.players-identity-lifecycle-anchor-candidates.v1",
                    },
                }
            )

        self.assertFalse(promoted)

    def test_lifecycle_anchor_scope_does_not_count_as_generic_promotion_evidence(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="StructureCensusPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="structure_census_promotion",
            ) as sdk_dir,
        ):
            abi_test = Path(core_dir) / "StructureCensusPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "structure_census_promotion_plugin.c"
            abi_test.write_text("// promoted structure census ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted structure census SDK placeholder\n", encoding="utf-8")
            base_surface = {
                "id": "obelisk.structure_census.v1",
                "status": "promoted",
                "public_contract": ["ObeliskApi.RegisterStructureCensusCallback"],
                "evidence": {
                    "surface_id": "obelisk.structure_census.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                    "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                },
            }
            self.assertTrue(surface_has_promotion_evidence(base_surface))

            for key, value in (
                ("ready_scope", "lifecycle_anchor_only"),
                ("source_scope", "lifecycle-anchor-candidates"),
                ("schema", "obelisk.players-identity-lifecycle-anchor-candidates.v1"),
            ):
                with self.subTest(scope_key=key):
                    surface = json.loads(json.dumps(base_surface))
                    surface["evidence"][key] = value
                    self.assertFalse(surface_has_promotion_evidence(surface))

    def test_principal_invalidation_policy_schema_does_not_promote_permissions_readiness(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as identity_core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as identity_sdk_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PermissionsAdminPromotion",
            ) as permissions_core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="permissions_admin_promotion",
            ) as permissions_sdk_dir,
        ):
            identity_core_test = Path(identity_core_dir) / "PlayerIdentityPromotionTests.cpp"
            identity_sdk_test = Path(identity_sdk_dir) / "player_identity_promotion_plugin.c"
            permissions_core_test = Path(permissions_core_dir) / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = Path(permissions_sdk_dir) / "permissions_admin_promotion_plugin.c"
            for path in (identity_core_test, identity_sdk_test, permissions_core_test, permissions_sdk_test):
                path.write_text("// synthetic promotion evidence fixture\n", encoding="utf-8")

            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(identity_core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(identity_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPermissionsAdminQuery"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "schemas": ["obelisk.players-identity-principal-invalidation-policy.v1"],
                        "terms": [
                            "query-only fail-closed permission checks over copied principals",
                            "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                            "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                            "promoted copied principal semantics",
                        ],
                    }
            manifest["promoted_surfaces"].extend(
                ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"]
            )
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}
            ]
            manifest_path = Path(identity_core_dir) / "public_sdk_surfaces.json"
            header_path = Path(identity_core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.permissions_admin.v1"])

    def test_promoted_completion_blocker_requires_valid_abi_and_sdk_consumer_evidence(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.structure_census.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterStructureCensusCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.structure_census.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/StructureAggregateCensusTests.cpp"],
                    "sdk_consumer_tests": ["TODO-missing-sdk-consumer-test"],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.structure_census.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.structure_census.v1"])

    def test_promotion_evidence_rejects_non_evidence_scope_aliases(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="StructureCensusPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="structure_census_promotion",
            ) as sdk_dir,
        ):
            abi_test = Path(core_dir) / "StructureCensusPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "structure_census_promotion_plugin.c"
            abi_test.write_text("// promoted structure census ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted structure census SDK placeholder\n", encoding="utf-8")
            base_surface = {
                "id": "obelisk.structure_census.v1",
                "status": "promoted",
                "public_contract": ["ObeliskApi.RegisterStructureCensusCallback"],
                "evidence": {
                    "surface_id": "obelisk.structure_census.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                    "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                },
            }
            self.assertTrue(surface_has_promotion_evidence(base_surface))

            cases = (
                ("evidence_scope", "request_pack_only"),
                ("claim_scope", "preflight-only"),
                ("artifactScope", "window_manifest_only"),
                ("validation_scope", "operator-approval-receipt-only"),
                ("source_scope", "runtime-replay-fixture-only"),
                ("ready_scope", "post-window-replay"),
            )
            for key, value in cases:
                with self.subTest(scope_key=key):
                    surface = json.loads(json.dumps(base_surface))
                    surface["evidence"][key] = value
                    self.assertFalse(surface_has_promotion_evidence(surface))

    def test_promotion_evidence_rejects_camel_case_non_promotional_source_markers(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="StructureCensusPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="structure_census_promotion",
            ) as sdk_dir,
        ):
            abi_test = Path(core_dir) / "StructureCensusPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "structure_census_promotion_plugin.c"
            abi_test.write_text("// promoted structure census ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted structure census SDK placeholder\n", encoding="utf-8")
            base_surface = {
                "id": "obelisk.structure_census.v1",
                "status": "promoted",
                "public_contract": ["ObeliskApi.RegisterStructureCensusCallback"],
                "evidence": {
                    "surface_id": "obelisk.structure_census.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                    "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                },
            }
            self.assertTrue(surface_has_promotion_evidence(base_surface))

            cases = (
                ("sourceKind", "request_pack"),
                ("sourceKind", "approvedRuntime"),
                ("sourceKind", "approved-runtime"),
                ("sourceKind", "approved_runtime_principal_lifecycle_evidence"),
                ("sourceKind", "runtime_lifecycle_evidence"),
                ("evidenceKind", "identityContract"),
                ("evidenceKind", "identity-contract"),
                ("evidenceKind", "identity_public_contract_gate_missing"),
                ("sourceTargetSets", ["preflight"]),
                ("evidenceKinds", ["live_ops_sidecar"]),
                ("evidenceKinds", ["approved-runtime-evidence"]),
                ("sourceKinds", [{"kind": "identity-contract"}]),
            )
            for key, value in cases:
                with self.subTest(marker_key=key):
                    surface = json.loads(json.dumps(base_surface))
                    surface["evidence"][key] = value
                    self.assertFalse(surface_has_promotion_evidence(surface))

    def test_promoted_completion_blocker_rejects_core_test_as_sdk_consumer_evidence(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.structure_census.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterStructureCensusCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.structure_census.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/StructureAggregateCensusTests.cpp"],
                    "sdk_consumer_tests": ["tests/core/StructureAggregateCensusTests.cpp"],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.structure_census.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.structure_census.v1"])

    def test_descriptor_catalog_contract_does_not_promote_module_completion_blockers(self) -> None:
        cases = (
            (
                "obelisk.inventory_items_mutation.v1",
                "tests/core/InventoryPolicyEventDispatcherTests.cpp",
                "ObeliskApi.DescribeResourceKind",
            ),
            (
                "obelisk.structure_census.v1",
                "tests/core/StructureEventDispatcherTests.cpp",
                "ObeliskApi.DescribeGameplayPolicyEventKind",
            ),
            (
                "obelisk.mission_transfer_dino_tribe.v1",
                "tests/core/MissionCopiedBoolEventDispatcherTests.cpp",
                "ObeliskResourceKindDescriptor",
            ),
        )
        for surface_id, abi_test, descriptor_contract in cases:
            with self.subTest(surface=surface_id):
                manifest, _ = complete_excluded_manifest()
                for surface in manifest["surfaces"]:
                    if surface["id"] == surface_id:
                        surface["status"] = "promoted"
                        surface["public_contract"] = [descriptor_contract]
                        surface["evidence"] = {
                            "surface_id": surface_id,
                            "promotion_status": "promoted",
                            "public_sdk_ready": True,
                            "abi_tests": [abi_test],
                            "sdk_consumer_tests": [
                                "tests/sdk_installed_consumer/descriptor_catalog_plugin.cpp"
                            ],
                        }
                        break
                manifest["promoted_surfaces"].append(surface_id)
                manifest["post_v1_or_excluded_surfaces"] = [
                    item for item in manifest["post_v1_or_excluded_surfaces"] if item != surface_id
                ]
                with tempfile.TemporaryDirectory() as temp_dir:
                    manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
                self.assertIn(surface_id, payload["promoted_blockers_without_evidence"])

    def test_item_return_only_readiness_does_not_promote_inventory_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="InventoryItemMutationPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="inventory_item_mutation_promotion",
            ) as sdk_dir,
        ):
            abi_test = Path(core_dir) / "InventoryItemMutationPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "inventory_item_mutation_plugin.c"
            abi_test.write_text("// promoted inventory item mutation ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted inventory item mutation SDK placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.inventory_items_mutation.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterInventoryItemMutationCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.inventory_items_mutation.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "schemas": ["obelisk.item-return-only-policy-slice.v1"],
                        "release_readiness_target_sets": ["item-return-only-policy-slice"],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.inventory_items_mutation.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                item for item in manifest["post_v1_or_excluded_surfaces"] if item != "obelisk.inventory_items_mutation.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertIn("obelisk.inventory_items_mutation.v1", payload["promoted_blockers_without_evidence"])

    def test_copied_signal_and_descriptor_paths_do_not_promote_inventory_completion_blocker(self) -> None:
        cases = (
            "InventoryPolicyEventDispatcher",
            "InventoryItemReturnEventDispatcher",
            "InventoryDescriptorCatalog",
        )
        for case_name in cases:
            with self.subTest(case=case_name):
                with (
                    tempfile.TemporaryDirectory(
                        dir=REPO_ROOT / "tests" / "core",
                        prefix=case_name,
                    ) as core_dir,
                    tempfile.TemporaryDirectory(
                        dir=REPO_ROOT / "tests" / "sdk_consumer",
                        prefix=case_name,
                    ) as sdk_dir,
                ):
                    abi_test = Path(core_dir) / f"{case_name}Tests.cpp"
                    sdk_test = Path(sdk_dir) / f"{case_name}Plugin.c"
                    abi_test.write_text(
                        "// copied signal or descriptor evidence placeholder\n",
                        encoding="utf-8",
                    )
                    sdk_test.write_text(
                        "// copied signal or descriptor SDK consumer placeholder\n",
                        encoding="utf-8",
                    )
                    manifest, _ = complete_excluded_manifest()
                    for surface in manifest["surfaces"]:
                        if surface["id"] == "obelisk.inventory_items_mutation.v1":
                            surface["status"] = "promoted"
                            surface["public_contract"] = [
                                "ObeliskApi.RegisterInventoryItemMutationCallback"
                            ]
                            surface["evidence"] = {
                                "surface_id": "obelisk.inventory_items_mutation.v1",
                                "promotion_status": "promoted",
                                "public_sdk_ready": True,
                                "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                                "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                            }
                            break
                    manifest["promoted_surfaces"].append("obelisk.inventory_items_mutation.v1")
                    manifest["post_v1_or_excluded_surfaces"] = [
                        item
                        for item in manifest["post_v1_or_excluded_surfaces"]
                        if item != "obelisk.inventory_items_mutation.v1"
                    ]
                    manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
                self.assertIn(
                    "obelisk.inventory_items_mutation.v1",
                    payload["promoted_blockers_without_evidence"],
                )

    def test_descriptor_catalog_path_does_not_promote_inventory_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="InventoryMutationPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="inventory_descriptor_catalog_promotion",
            ) as sdk_dir,
        ):
            abi_test = Path(core_dir) / "InventoryMutationPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "inventory_descriptor_catalog_plugin.c"
            abi_test.write_text("// promoted inventory mutation ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// inventory descriptor catalog SDK placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.inventory_items_mutation.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterInventoryItemMutationCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.inventory_items_mutation.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.inventory_items_mutation.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                item for item in manifest["post_v1_or_excluded_surfaces"] if item != "obelisk.inventory_items_mutation.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertIn("obelisk.inventory_items_mutation.v1", payload["promoted_blockers_without_evidence"])

    def test_duplicate_surface_id_blocks_v1_claim(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        duplicate = {
            "id": "obelisk.player_identity.v1",
            "status": "planning",
            "public_contract": ["ObeliskApi.RegisterPlayerIdentityCallback"],
        }
        for index, surface in enumerate(manifest["surfaces"]):
            if surface["id"] == "obelisk.player_identity.v1":
                manifest["surfaces"].insert(index, duplicate)
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate_surface_id", payload["blockers"])
        self.assertEqual(payload["duplicate_surface_ids"], ["obelisk.player_identity.v1"])

    def test_duplicate_v1_completion_blocker_blocks_progress_accounting(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        manifest["v1_sdk_completion_blockers"].append("obelisk.player_identity.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate_v1_sdk_completion_blocker", payload["blockers"])
        self.assertEqual(payload["duplicate_v1_sdk_completion_blockers"], ["obelisk.player_identity.v1"])
        progress = payload["v1_sdk_progress"]
        self.assertEqual(progress["completion_blocker_total"], 12)
        self.assertEqual(progress["completion_blockers_promoted_count"], 0)
        self.assertEqual(progress["p0_chain_promoted_count"], 0)

    def test_promoted_experimental_surface_requires_structured_surface_specific_evidence(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.chat_message.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterChatEventWithOwnerTokenHandle"]
                surface["evidence"] = {"tests": ["tests/sdk_consumer"]}
                break
        manifest["promoted_surfaces"].append("obelisk.chat_message.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_surfaces_without_evidence"], ["obelisk.chat_message.v1"])

    def test_promoted_experimental_surface_still_requires_release_statement_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.chat_message.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterChatEventWithOwnerTokenHandle"]
                surface["evidence"] = {
                    "surface_id": "obelisk.chat_message.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/ChatEventDispatcherTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/CAbiPlugin.c"],
                }
                break
        if "obelisk.chat_message.v1" not in manifest["promoted_surfaces"]:
            manifest["promoted_surfaces"].append("obelisk.chat_message.v1")
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.chat_message.v1"
        ]
        release_statement = "\n".join(
            line for line in release_statement.splitlines() if "obelisk.chat_message.v1" not in line
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_experimental_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_experimental_outcomes"], ["obelisk.chat_message.v1"])

    def test_release_statement_parser_accepts_promoted_surface_record(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        record = module.release_statement_surface_record(
            "obelisk.chat_message.v1: promoted - reviewed ABI and SDK evidence.\n",
            "obelisk.chat_message.v1",
            "promoted",
        )

        self.assertEqual(record, "obelisk.chat_message.v1: promoted - reviewed ABI and SDK evidence.")
        self.assertIsNone(
            module.release_statement_surface_record(
                "obelisk.chat_message.v1: promoted\n",
                "obelisk.chat_message.v1",
                "promoted",
            )
        )
        self.assertIsNone(
            module.release_statement_surface_record(
                "obelisk.chat_message.v1 - promoted - reviewed ABI and SDK evidence.\n",
                "obelisk.chat_message.v1",
                "promoted",
            )
        )
        self.assertTrue(
            module.release_statement_duplicate_or_mixed_records(
                "obelisk.chat_message.v1: promoted - reviewed ABI and SDK evidence.\n"
                "obelisk.chat_message.v1 - promoted - duplicate alternate record.\n",
                "obelisk.chat_message.v1",
            )
        )

    def test_release_statement_rejects_bare_promoted_record_for_promoted_surface(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": ["obelisk.player_identity.v1"],
            "experimental_surfaces": [],
            "planning_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "promoted",
                    "public_contract": ["ObeliskApi.RegisterPlayerIdentityCallback"],
                    "evidence": {
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: promoted\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], ["obelisk.player_identity.v1"])
        self.assertIsNone(payload["v1_sdk_blocker_outcomes"][0]["release_statement_outcome"])

    def test_release_statement_outcome_must_match_manifest_non_promoted_status(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.inventory_items_mutation.v1":
                surface["status"] = "post-v1"
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(
            payload["release_statement_missing_blocker_outcomes"],
            ["obelisk.inventory_items_mutation.v1"],
        )
        self.assertNotIn("release_statement_missing_exclusion_contract", payload["blockers"])
        outcome_by_surface = {
            row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]
        }
        inventory = outcome_by_surface["obelisk.inventory_items_mutation.v1"]
        self.assertEqual(inventory["manifest_outcome"], "post-v1")
        self.assertEqual(inventory["release_statement_outcome"], "excluded")
        self.assertFalse(inventory["release_statement_outcome_matches_manifest"])
        self.assertFalse(inventory["release_statement_contract_satisfied"])
        self.assertFalse(inventory["counts_toward_complete_sdk_claim"])
        self.assertEqual(payload["v1_sdk_progress"]["completion_blockers_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)

    def test_release_statement_rejects_mixed_alternate_promoted_surface_records(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += "obelisk.player_identity.v1 - promoted - duplicate alternate record.\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_duplicate_or_mixed_surface_records", payload["blockers"])
        self.assertEqual(payload["release_statement_duplicate_or_mixed_records"], ["obelisk.player_identity.v1"])

    def test_new_planning_surface_blocks_v1_claim_until_outcome_is_named(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["surfaces"].append(
            {
                "id": "obelisk.future_unmapped_surface.v1",
                "status": "planning",
                "public_contract": [],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("planning_surfaces_unresolved_for_v1_claim", payload["blockers"])
        self.assertEqual(payload["unresolved_planning_surfaces"], ["obelisk.future_unmapped_surface.v1"])

    def test_top_level_planning_surfaces_block_v1_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["planning_surfaces"] = ["obelisk.player_identity.v1"]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("top_level_planning_surfaces_unresolved_for_v1_claim", payload["blockers"])
        self.assertIn("planning_surface_list_mismatch", payload["blockers"])
        self.assertEqual(payload["top_level_planning_surfaces"], ["obelisk.player_identity.v1"])

    def test_post_v1_or_excluded_surface_list_must_match_surface_statuses(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["post_v1_or_excluded_surfaces"].remove("obelisk.commands_replies.v1")
        manifest["post_v1_or_excluded_surfaces"].append("obelisk.descriptors.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("post_v1_or_excluded_surface_list_mismatch", payload["blockers"])
        self.assertEqual(
            payload["post_v1_or_excluded_list_mismatches"],
            ["obelisk.commands_replies.v1", "obelisk.descriptors.v1"],
        )

    def test_debug_only_surface_cannot_be_promoted(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.debug_raw_process_event.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterRawProcessEvent"]
                surface["evidence"] = {"tests": ["tests/sdk_consumer"]}
                break
        manifest["promoted_surfaces"].append("obelisk.debug_raw_process_event.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("debug_only_surface_promoted", payload["blockers"])
        self.assertEqual(payload["debug_only_promoted_surfaces"], ["obelisk.debug_raw_process_event.v1"])

    def test_non_promoted_completion_blocker_requires_exclusion_contract(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.commands_replies.v1":
                surface.pop("v1_decision_contract", None)
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("completion_blocker_exclusion_contract_missing", payload["blockers"])
        self.assertEqual(payload["missing_completion_blocker_exclusion_contracts"], ["obelisk.commands_replies.v1"])

    def test_public_abi_dependency_chain_blocks_until_identity_dependencies_promoted(self) -> None:
        cases = {
            "obelisk.permissions_admin.v1": ["obelisk.player_identity.v1"],
            "obelisk.command_chat_response_path.v1": [
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
            ],
            "obelisk.commands_replies.v1": [
                "obelisk.command_chat_response_path.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
            ],
        }
        for surface_id, expected_dependencies in cases.items():
            with self.subTest(surface=surface_id):
                manifest, release_statement = complete_excluded_manifest()
                for surface in manifest["surfaces"]:
                    if surface["id"] == surface_id:
                        surface["public_abi"] = True
                        break
                with tempfile.TemporaryDirectory() as temp_dir:
                    manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
                    statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    statement_path.write_text(release_statement, encoding="utf-8")
                    result = self.run_checker(
                        "--manifest",
                        str(manifest_path),
                        "--release-statement",
                        str(statement_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("promoted_surface_dependency_unresolved", payload["blockers"])
                self.assertEqual(
                    payload["promoted_surfaces_with_unresolved_dependencies"],
                    {surface_id: expected_dependencies},
                )

    def test_dependency_declarations_block_permissions_and_commands_sequence_drift(self) -> None:
        cases = {
            "obelisk.permissions_admin.v1": ["obelisk.player_identity.v1"],
            "obelisk.commands_replies.v1": ["obelisk.command_chat_response_path.v1"],
            "obelisk.player_services_economy_mobility.v1": [
                "obelisk.command_chat_response_path.v1",
            ],
        }
        for surface_id, removed_dependencies in cases.items():
            with self.subTest(surface=surface_id):
                manifest, release_statement = complete_excluded_manifest()
                for surface in manifest["surfaces"]:
                    if surface["id"] == surface_id:
                        surface["depends_on"] = [
                            dependency
                            for dependency in surface.get("depends_on", [])
                            if dependency not in removed_dependencies
                        ]
                        break

                with tempfile.TemporaryDirectory() as temp_dir:
                    manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
                    statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    statement_path.write_text(release_statement, encoding="utf-8")
                    result = self.run_checker(
                        "--manifest",
                        str(manifest_path),
                        "--release-statement",
                        str(statement_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("required_surface_dependency_declaration_missing", payload["blockers"])
                self.assertEqual(
                    payload["surfaces_missing_required_dependency_declarations"],
                    {surface_id: removed_dependencies},
                )

    def test_v1_dependency_sequence_blocks_reordering_before_completion_claim(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        manifest["v1_dependency_sequence"] = [
            "obelisk.permissions_admin.v1",
            "obelisk.player_identity.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ]
        manifest["v1_sdk_completion_blockers"] = [
            "obelisk.permissions_admin.v1",
            "obelisk.player_identity.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
            *[
                surface_id
                for surface_id in manifest["v1_sdk_completion_blockers"]
                if surface_id
                not in {
                    "obelisk.player_identity.v1",
                    "obelisk.permissions_admin.v1",
                    "obelisk.command_chat_response_path.v1",
                    "obelisk.commands_replies.v1",
                }
            ],
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("v1_dependency_sequence_mismatch", payload["blockers"])
        self.assertEqual(
            payload["v1_dependency_sequence_expected"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(
            payload["v1_dependency_sequence_mismatches"],
            ["v1_dependency_sequence", "v1_sdk_completion_blockers"],
        )

    def test_permissions_admin_public_cache_api_contract_blocks_until_player_identity_promoted(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "planning"
                surface["public_contract"] = []
            if surface["id"] == "obelisk.permissions_admin.v1":
                surface["public_abi"] = True
                surface["public_contract"] = [
                    "ObeliskApi.CheckPermissionWithCopiedPrincipal",
                    "ObeliskApi.CheckPermissionCachedWithCopiedPrincipal",
                    "ObeliskPermissionCacheEntry",
                    "ObeliskPermissionsAdminContractV1",
                ]
                surface["public_permission_cache_contract"] = "policy_epoch_generation_scope_keyed"
        manifest["planning_surfaces"] = ["obelisk.player_identity.v1"]
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.player_identity.v1"
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("promoted_surface_dependency_unresolved", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_with_unresolved_dependencies"],
            {"obelisk.permissions_admin.v1": ["obelisk.player_identity.v1"]},
        )
        self.assertIn("non_promoted_surface_has_public_abi", payload["blockers"])
        self.assertEqual(payload["non_promoted_with_public_abi"], ["obelisk.permissions_admin.v1"])
        self.assertIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertIn("obelisk.permissions_admin.v1", payload["non_promoted_with_public_contract"])

    def test_promoted_permissions_admin_requires_semantic_evidence_terms(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PermissionsAdminPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="permissions_admin_promotion",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            identity_abi_test = core_path / "PlayerIdentityPromotionTests.cpp"
            identity_sdk_test = sdk_path / "player_identity_promotion_plugin.c"
            permissions_abi_test = core_path / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = sdk_path / "permissions_admin_promotion_plugin.c"
            identity_abi_test.write_text("// promoted player identity ABI placeholder\n", encoding="utf-8")
            identity_sdk_test.write_text("// promoted player identity SDK placeholder\n", encoding="utf-8")
            permissions_abi_test.write_text("// promoted permissions admin ABI placeholder\n", encoding="utf-8")
            permissions_sdk_test.write_text("// promoted permissions admin SDK placeholder\n", encoding="utf-8")

            manifest, release_statement = complete_excluded_manifest()
            promoted_ids = {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(identity_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(identity_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.CheckPermissionWithCopiedPrincipal"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "terms": ["nominal permissions/admin ABI and SDK consumer tests"],
                    }
            for surface_id in promoted_ids:
                if surface_id not in manifest["promoted_surfaces"]:
                    manifest["promoted_surfaces"].append(surface_id)
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in promoted_ids
            ]
            release_statement = "\n".join(
                (
                    f"{surface_id}: promoted - reviewed ABI and SDK evidence."
                    if surface_id in promoted_ids
                    else line
                )
                for line in release_statement.splitlines()
                for surface_id in [line.split(":", 1)[0]]
            ) + "\n"
            manifest_path = core_path / "public_sdk_surfaces.json"
            statement_path = core_path / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertNotIn("promoted_surface_dependency_unresolved", payload["blockers"])
        self.assertIn("promoted_surface_required_evidence_terms_missing", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_missing_required_evidence_terms"],
            {
                "obelisk.permissions_admin.v1": [
                    "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                    "promoted copied principal semantics",
                    "query-only fail-closed permission checks over copied principals",
                    "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                ]
            },
        )

    def test_permissions_admin_required_terms_do_not_replace_structured_promotion_evidence(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PermissionsAdminPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="permissions_admin_promotion",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            identity_abi_test = core_path / "PlayerIdentityPromotionTests.cpp"
            identity_sdk_test = sdk_path / "player_identity_promotion_plugin.c"
            permissions_abi_test = core_path / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = sdk_path / "permissions_admin_promotion_plugin.c"
            identity_runtime_manifest = core_path / "approved-runtime-principal-lifecycle-evidence.json"
            identity_runtime_report = core_path / "player_identity_approved_runtime_report.json"
            identity_contract_report = core_path / "player_identity_public_contract_readiness_report.json"
            identity_executed_report = core_path / "player_identity_executed_tests.json"
            for path in (identity_abi_test, identity_sdk_test, permissions_abi_test, permissions_sdk_test):
                path.write_text("// synthetic promotion evidence fixture\n", encoding="utf-8")
            identity_runtime_manifest_binding = self.write_approved_runtime_manifest_binding(identity_runtime_manifest)
            identity_runtime_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "next_blocker": "identity_public_contract_gate_missing",
                    }
                ),
                encoding="utf-8",
            )
            identity_contract_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-identity-public-contract-readiness-check.v1",
                        "ready": True,
                        "ready_scope": "contract_review_input_only",
                        "surface": "obelisk.player_identity.v1",
                        "accepted_for_contract_review": True,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "public_contract_allowed": False,
                        "public_header_allowed": False,
                        "public_header_symbols_now": [],
                        "public_capability_bits_now": [],
                        "public_callback_abi_now": [],
                        "next_blocker": "identity_public_contract_gate_missing",
                        "blockers": [],
                        "resolved_inputs": ["runtime.lifecycle_evidence"],
                        "remaining_blockers": [
                            "runtime.lifecycle_evidence",
                            "privacy.identifier_redaction",
                            "lifetime.generation_scope_invalidation",
                            "abi.public_pod_contract",
                            "lifecycle.owner_cleanup",
                            "separation.downstream_surfaces",
                        ],
                        "approved_runtime_evidence": {
                            "approved_runtime_evidence_present": True,
                            "runtime_evidence_ready": True,
                        },
                        "private_candidate_contract": {
                            "candidate_only": True,
                            "promotion_ready": False,
                            "public_sdk_ready": False,
                            "public_header_allowed": False,
                        },
                        "private_pod_layout_candidate": {
                            "candidate_only": True,
                            "promotion_ready": False,
                            "public_sdk_ready": False,
                            "public_header_allowed": False,
                            "public_abi_ready": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            identity_executed_report_path = str(identity_executed_report.relative_to(REPO_ROOT))

            manifest, release_statement = complete_excluded_manifest()
            promoted_ids = {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(identity_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(identity_sdk_test.relative_to(REPO_ROOT))],
                        "approved_runtime_evidence_manifest": identity_runtime_manifest_binding,
                        "approved_runtime_evidence_report": str(identity_runtime_report.relative_to(REPO_ROOT)),
                        "public_contract_readiness_report": str(identity_contract_report.relative_to(REPO_ROOT)),
                        "executed_test_report": identity_executed_report_path,
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.CheckPermissionWithCopiedPrincipal"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "query-only fail-closed permission checks over copied principals",
                            "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                            "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                            "promoted copied principal semantics",
                        ],
                    }
            for surface_id in promoted_ids:
                if surface_id not in manifest["promoted_surfaces"]:
                    manifest["promoted_surfaces"].append(surface_id)
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in promoted_ids
            ]
            release_statement = "\n".join(
                (
                    f"{surface_id}: promoted - reviewed ABI and SDK evidence."
                    if surface_id in promoted_ids
                    else line
                )
                for line in release_statement.splitlines()
                for surface_id in [line.split(":", 1)[0]]
            ) + "\n"
            manifest_path = core_path / "public_sdk_surfaces.json"
            statement_path = core_path / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            identity_executed_report_path = write_executed_test_artifact(
                identity_executed_report,
                "obelisk.player_identity.v1",
                argv=["python3", "-m", "unittest", "player_identity_promotion"],
                public_sdk_surfaces=manifest_path,
            )
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["evidence"]["executed_test_report"] = identity_executed_report_path
                    break
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertNotIn("promoted_surface_required_evidence_terms_missing", payload["blockers"])
        self.assertIn("promoted_surface_structured_evidence_missing", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_missing_structured_evidence"]["obelisk.permissions_admin.v1"],
            [
                "executed_test_report:missing",
                "player_identity_promotion_certificate:missing",
                "public_readiness_report:missing",
                "query_failclosed_report:missing",
            ],
        )

    def test_promoted_command_response_requires_semantic_evidence_terms(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="CommandChatResponsePromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="command_chat_response_promotion",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            identity_abi_test = core_path / "PlayerIdentityPromotionTests.cpp"
            identity_sdk_test = sdk_path / "player_identity_promotion_plugin.c"
            permissions_abi_test = core_path / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = sdk_path / "permissions_admin_promotion_plugin.c"
            response_abi_test = core_path / "CommandChatResponsePromotionTests.cpp"
            response_sdk_test = sdk_path / "command_chat_response_promotion_plugin.c"
            for path in (
                identity_abi_test,
                identity_sdk_test,
                permissions_abi_test,
                permissions_sdk_test,
                response_abi_test,
                response_sdk_test,
            ):
                path.write_text("// synthetic promotion evidence fixture\n", encoding="utf-8")

            manifest, release_statement = complete_excluded_manifest()
            promoted_ids = {
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            }
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(identity_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(identity_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.CheckPermissionWithCopiedPrincipal"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "query-only fail-closed permission checks over copied principals",
                            "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                            "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                            "promoted copied principal semantics",
                        ],
                    }
                if surface["id"] == "obelisk.command_chat_response_path.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterCommandChatResponsePath"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.command_chat_response_path.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(response_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(response_sdk_test.relative_to(REPO_ROOT))],
                        "terms": ["nominal command/chat response ABI and SDK consumer tests"],
                    }
            for surface_id in promoted_ids:
                if surface_id not in manifest["promoted_surfaces"]:
                    manifest["promoted_surfaces"].append(surface_id)
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in promoted_ids
            ]
            release_statement = "\n".join(
                (
                    f"{surface_id}: promoted - reviewed ABI and SDK evidence."
                    if surface_id in promoted_ids
                    else line
                )
                for line in release_statement.splitlines()
                for surface_id in [line.split(":", 1)[0]]
            ) + "\n"
            manifest_path = core_path / "public_sdk_surfaces.json"
            statement_path = core_path / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertNotIn("promoted_surface_dependency_unresolved", payload["blockers"])
        self.assertIn("promoted_surface_required_evidence_terms_missing", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_missing_required_evidence_terms"],
            {
                "obelisk.command_chat_response_path.v1": [
                    "copied append-only response ABI with capability gates and owner-scoped cleanup",
                    "no raw UE pointer, raw ProcessEvent parameter, or raw FString response API",
                    "privacy, redaction, rate-limit, abuse, audit, and cross-instance routing semantics for command/chat responses",
                    "promoted permission/authority checks for directed responses",
                    "promoted player identity/principal semantics",
                ]
            },
        )

    def test_command_response_required_terms_do_not_replace_structured_promotion_evidence(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="CommandChatResponsePromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="command_chat_response_promotion",
            ) as sdk_dir,
        ):
            abi_test = Path(core_dir) / "CommandChatResponsePromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "command_chat_response_promotion_plugin.c"
            abi_test.write_text("// promoted command response ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted command response SDK placeholder\n", encoding="utf-8")
            surface = {
                "id": "obelisk.command_chat_response_path.v1",
                "status": "promoted",
                "evidence": {
                    "surface_id": "obelisk.command_chat_response_path.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                    "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                    "terms": [
                        "promoted player identity/principal semantics",
                        "promoted permission/authority checks for directed responses",
                        "copied append-only response ABI with capability gates and owner-scoped cleanup",
                        "privacy, redaction, rate-limit, abuse, audit, and cross-instance routing semantics for command/chat responses",
                        "no raw UE pointer, raw ProcessEvent parameter, or raw FString response API",
                    ],
                },
            }
            missing = module.surface_missing_structured_promotion_evidence(surface)
            rows = module.completion_blocker_outcome_rows(
                ["obelisk.command_chat_response_path.v1"],
                {"obelisk.command_chat_response_path.v1": surface},
                set(),
                "obelisk.command_chat_response_path.v1: promoted - reviewed ABI and SDK evidence.\n",
            )

        self.assertEqual(
            missing,
            [
                "permissions_admin_promotion_certificate:missing",
                "permissions_admin_player_identity_promotion_certificate:missing",
                "permissions_admin_query_failclosed_report:missing",
                "permissions_admin_public_readiness_report:missing",
                "permissions_admin_executed_test_report:missing",
                "public_readiness_report:missing",
                "executed_test_report:missing",
            ],
        )
        self.assertTrue(rows[0]["promotion_evidence_satisfied"])
        self.assertTrue(rows[0]["required_promotion_evidence_terms_satisfied"])
        self.assertFalse(rows[0]["structured_promotion_evidence_satisfied"])
        self.assertFalse(rows[0]["counts_toward_complete_sdk_claim"])

    def test_p0_row_does_not_count_while_route_gate_identity_locked(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        original_surface_has_promotion_evidence = module.surface_has_promotion_evidence
        original_missing_required = module.surface_missing_required_promotion_evidence
        original_missing_structured = module.surface_missing_structured_promotion_evidence
        try:
            module.surface_has_promotion_evidence = lambda surface: True
            module.surface_missing_required_promotion_evidence = lambda surface: []
            module.surface_missing_structured_promotion_evidence = (
                lambda surface, manifest_path=PUBLIC_SDK_SURFACES, public_header_path=PUBLIC_HEADER: []
            )

            surface = {
                "id": "obelisk.player_identity.v1",
                "status": "promoted",
                "evidence": {},
            }

            def row_for_route_gate(route_gate: dict[str, object]) -> dict[str, object]:
                return module.completion_blocker_outcome_rows(
                    ["obelisk.player_identity.v1"],
                    {"obelisk.player_identity.v1": surface},
                    set(),
                    "obelisk.player_identity.v1: promoted - reviewed ABI and SDK evidence.\n",
                    route_gate,
                )[0]

            blocked_rows = [
                row_for_route_gate(
                    {
                        "valid": True,
                        "planning_only": True,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "route_lock_locked": True,
                        "current_blocker": blocker,
                        "blockers": [],
                    }
                )
                for blocker in (
                    "lifecycle_anchor_first_evidence_provenance_unbound",
                    "approved_runtime_evidence_missing",
                    "identity_public_contract_gate_missing",
                )
            ]
            planning_only_accepted_row = row_for_route_gate(
                {
                    "completion_gate_accepted": True,
                    "valid": True,
                    "planning_only": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "route_lock_locked": True,
                    "current_blocker": "approved_runtime_evidence_missing",
                    "operator_approval_receipt_verified": True,
                    "blockers": [],
                }
            )
            nested_raw_report_row = row_for_route_gate(
                {
                    "schema": "obelisk.command-permission-route-gate-check.v1",
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "critical_path_phase": {
                        "current_blocker": "approved_runtime_evidence_missing",
                        "source_checker_primary_blocker": "approved_runtime_evidence_missing",
                        "source_checker_status": "blocked",
                        "source_checker_ready": False,
                    },
                    "route_lock": {
                        "locked": True,
                        "blocked_until": [
                            "approved_runtime_principal_lifecycle_evidence",
                            "reviewed_identity_public_contract",
                        ],
                    },
                    "blockers": [],
                }
            )
            unlocked_row = row_for_route_gate(
                {
                    "valid": True,
                    "planning_only": False,
                    "promotion_ready": True,
                    "public_sdk_ready": True,
                    "runtime_ready": True,
                    "route_lock_locked": False,
                    "current_blocker": None,
                    "blockers": [],
                    "completion_gate_accepted": True,
                }
            )
        finally:
            module.surface_has_promotion_evidence = original_surface_has_promotion_evidence
            module.surface_missing_required_promotion_evidence = original_missing_required
            module.surface_missing_structured_promotion_evidence = original_missing_structured

        for row in blocked_rows:
            self.assertTrue(row["promotion_evidence_satisfied"])
            self.assertTrue(row["structured_promotion_evidence_satisfied"])
            self.assertFalse(row["route_gate_claim_satisfied"])
            self.assertTrue(row["manifest_promoted_but_non_counting"])
            self.assertEqual(row["route_gate_non_counting_blocker"], row["route_gate_current_blocker"])
            self.assertIn(
                f"route_gate_blocker:{row['route_gate_current_blocker']}",
                row["non_counting_reasons"],
            )
            self.assertFalse(row["counts_toward_complete_sdk_claim"])
        self.assertTrue(planning_only_accepted_row["is_p0_dependency_chain"])
        self.assertFalse(planning_only_accepted_row["route_gate_claim_satisfied"])
        self.assertTrue(planning_only_accepted_row["manifest_promoted_but_non_counting"])
        self.assertEqual(
            planning_only_accepted_row["route_gate_non_counting_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertFalse(planning_only_accepted_row["counts_toward_complete_sdk_claim"])
        self.assertEqual(
            nested_raw_report_row["route_gate_current_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            nested_raw_report_row["route_gate_non_counting_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertIn(
            "route_gate_blocker:approved_runtime_evidence_missing",
            nested_raw_report_row["non_counting_reasons"],
        )
        self.assertFalse(nested_raw_report_row["counts_toward_complete_sdk_claim"])
        self.assertFalse(unlocked_row["route_gate_claim_satisfied"])
        self.assertTrue(unlocked_row["manifest_promoted_but_non_counting"])
        self.assertFalse(unlocked_row["counts_toward_complete_sdk_claim"])

    def test_p0_row_reads_canonical_current_route_blocker_from_route_gate_summary(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        original_surface_has_promotion_evidence = module.surface_has_promotion_evidence
        original_missing_required = module.surface_missing_required_promotion_evidence
        original_missing_structured = module.surface_missing_structured_promotion_evidence
        try:
            module.surface_has_promotion_evidence = lambda surface: True
            module.surface_missing_required_promotion_evidence = lambda surface: []
            module.surface_missing_structured_promotion_evidence = (
                lambda surface, manifest_path=PUBLIC_SDK_SURFACES, public_header_path=PUBLIC_HEADER: []
            )

            row = module.completion_blocker_outcome_rows(
                ["obelisk.player_identity.v1"],
                {
                    "obelisk.player_identity.v1": {
                        "id": "obelisk.player_identity.v1",
                        "status": "promoted",
                        "evidence": {},
                    }
                },
                set(),
                "obelisk.player_identity.v1: promoted - reviewed ABI and SDK evidence.\n",
                {
                    "schema": "obelisk.command-permission-route-gate-check.v1",
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "current_route_blocker": "identity_public_contract_gate_missing",
                    "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                    "public_or_runtime_accounting_allowed": False,
                    "blockers": [],
                },
            )[0]
        finally:
            module.surface_has_promotion_evidence = original_surface_has_promotion_evidence
            module.surface_missing_required_promotion_evidence = original_missing_required
            module.surface_missing_structured_promotion_evidence = original_missing_structured

        self.assertEqual(row["route_gate_current_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(row["route_gate_claim_satisfied"])
        self.assertEqual(row["route_gate_non_counting_blocker"], "identity_public_contract_gate_missing")
        self.assertIn("route_gate_blocker:identity_public_contract_gate_missing", row["non_counting_reasons"])
        self.assertFalse(row["counts_toward_complete_sdk_claim"])

    def test_mixed_p0_non_counting_reasons_are_visible(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        original_surface_has_promotion_evidence = module.surface_has_promotion_evidence
        original_missing_required = module.surface_missing_required_promotion_evidence
        original_missing_structured = module.surface_missing_structured_promotion_evidence
        try:
            module.surface_has_promotion_evidence = lambda surface: surface.get("status") == "promoted"
            module.surface_missing_required_promotion_evidence = lambda surface: []
            module.surface_missing_structured_promotion_evidence = (
                lambda surface, manifest_path=PUBLIC_SDK_SURFACES, public_header_path=PUBLIC_HEADER: []
            )

            surfaces = {
                "obelisk.player_identity.v1": {
                    "id": "obelisk.player_identity.v1",
                    "status": "promoted",
                    "evidence": {},
                },
                "obelisk.permissions_admin.v1": {
                    "id": "obelisk.permissions_admin.v1",
                    "status": "excluded",
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.permissions_admin.v1 as excluded",
                            "the v1 release statement states that no permissions/admin API is included in v1",
                        ],
                    },
                },
                "obelisk.command_chat_response_path.v1": {
                    "id": "obelisk.command_chat_response_path.v1",
                    "status": "post-v1",
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.command_chat_response_path.v1 as post-v1",
                            "the v1 release statement states that no command response API is included in v1",
                        ],
                    },
                },
                "obelisk.commands_replies.v1": {
                    "id": "obelisk.commands_replies.v1",
                    "status": "planning",
                },
            }
            release_statement = "\n".join(
                [
                    "obelisk.player_identity.v1: promoted - reviewed ABI and SDK evidence.",
                    (
                        "obelisk.permissions_admin.v1: excluded - no permissions/admin API "
                        "is included in v1."
                    ),
                    (
                        "obelisk.command_chat_response_path.v1: post-v1 - no command response "
                        "API is included in v1."
                    ),
                ]
            )
            rows = module.completion_blocker_outcome_rows(
                [
                    "obelisk.player_identity.v1",
                    "obelisk.permissions_admin.v1",
                    "obelisk.command_chat_response_path.v1",
                    "obelisk.commands_replies.v1",
                ],
                surfaces,
                {
                    "obelisk.permissions_admin.v1",
                    "obelisk.command_chat_response_path.v1",
                },
                release_statement,
                {
                    "valid": True,
                    "planning_only": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "route_lock_locked": True,
                    "current_blocker": "identity_public_contract_gate_missing",
                    "blockers": [],
                },
            )
        finally:
            module.surface_has_promotion_evidence = original_surface_has_promotion_evidence
            module.surface_missing_required_promotion_evidence = original_missing_required
            module.surface_missing_structured_promotion_evidence = original_missing_structured

        by_surface = {row["surface"]: row for row in rows}
        promoted_locked = by_surface["obelisk.player_identity.v1"]
        excluded = by_surface["obelisk.permissions_admin.v1"]
        post_v1 = by_surface["obelisk.command_chat_response_path.v1"]
        planning = by_surface["obelisk.commands_replies.v1"]
        summary = module.completion_blocker_outcome_summary(rows)

        self.assertTrue(promoted_locked["manifest_promoted_but_non_counting"])
        self.assertEqual(
            promoted_locked["route_gate_non_counting_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertIn(
            "route_gate_blocker:identity_public_contract_gate_missing",
            promoted_locked["non_counting_reasons"],
        )
        self.assertIn("identity public contract", promoted_locked["next_action"])
        self.assertTrue(excluded["scoped_non_complete_outcome_only"])
        self.assertTrue(excluded["release_statement_scoped_non_complete_bookkeeping"])
        self.assertIn("p0_scoped_non_complete_outcome", excluded["non_counting_reasons"])
        self.assertTrue(post_v1["scoped_non_complete_outcome_only"])
        self.assertTrue(post_v1["release_statement_scoped_non_complete_bookkeeping"])
        self.assertIn("p0_scoped_non_complete_outcome", post_v1["non_counting_reasons"])
        self.assertIsNone(planning["manifest_outcome"])
        self.assertIn("manifest_promoted_outcome_missing", planning["non_counting_reasons"])
        self.assertEqual(
            summary["manifest_promoted_but_non_counting"],
            ["obelisk.player_identity.v1"],
        )
        self.assertEqual(
            summary["p0_manifest_promoted_non_counting"],
            ["obelisk.player_identity.v1"],
        )
        self.assertEqual(
            summary["release_statement_scoped_non_complete_bookkeeping"],
            ["obelisk.permissions_admin.v1", "obelisk.command_chat_response_path.v1"],
        )
        self.assertEqual(
            summary["p0_release_statement_scoped_non_complete_outcomes"],
            ["obelisk.permissions_admin.v1", "obelisk.command_chat_response_path.v1"],
        )
        self.assertEqual(
            summary["route_gate_non_counting_surfaces"],
            ["obelisk.player_identity.v1"],
        )
        self.assertEqual(
            summary["route_gate_non_counting_blockers"],
            ["identity_public_contract_gate_missing"],
        )

    def test_route_gate_locked_guidance_points_to_runtime_evidence_not_closed_binding(self) -> None:
        guidance = "\n".join(
            blocker_guidance(
                {
                    "p0_dependency_chain_route_gate_locked_surfaces": [
                        "obelisk.player_identity.v1",
                    ],
                },
                "p0_dependency_chain_route_gate_locked",
            )
        )

        self.assertIn("approved runtime principal lifecycle evidence", guidance)
        self.assertIn("reviewed identity public contract", guidance)
        self.assertNotIn("bind lifecycle", guidance)
        self.assertNotIn("supply bound", guidance)

    def test_commands_replies_requires_response_path_semantic_evidence_terms(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        missing_terms = module.surface_missing_required_promotion_evidence(
            {
                "id": "obelisk.commands_replies.v1",
                "status": "promoted",
                "evidence": {
                    "terms": [
                        "promoted player identity/principal semantics",
                        "promoted permission/authority model",
                        "nominal command router ABI and SDK consumer tests",
                    ],
                },
            }
        )

        self.assertEqual(
            missing_terms,
            [
                "obelisk.command_chat_response_path.v1 dependency resolved through its own future promotion gate for replies/send-chat",
                "command lifecycle, abuse, rate-limit, and moderation boundaries",
                "copied append-only command/reply ABI with capability gates, owner-scoped cleanup, and SDK consumer tests",
            ],
        )

    def test_commands_replies_required_terms_do_not_replace_structured_promotion_evidence(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        missing = module.surface_missing_structured_promotion_evidence(
            {
                "id": "obelisk.commands_replies.v1",
                "status": "promoted",
                "evidence": {
                    "surface_id": "obelisk.commands_replies.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/CommandsRepliesPromotionTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/commands_replies_promotion_plugin.c"],
                    "terms": [
                        "promoted player identity/principal semantics",
                        "promoted permission/authority model",
                        "obelisk.command_chat_response_path.v1 dependency resolved through its own future promotion gate for replies/send-chat",
                        "copied append-only command/reply ABI with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        "command lifecycle, abuse, rate-limit, and moderation boundaries",
                    ],
                },
            }
        )

        self.assertEqual(
            missing,
            [
                "command_response_promotion_certificate:missing",
                "command_response_permissions_admin_promotion_certificate:missing",
                "command_response_permissions_admin_player_identity_promotion_certificate:missing",
                "command_response_permissions_admin_query_failclosed_report:missing",
                "command_response_permissions_admin_public_readiness_report:missing",
                "command_response_permissions_admin_executed_test_report:missing",
                "command_response_public_readiness_report:missing",
                "command_response_executed_test_report:missing",
                "public_readiness_report:missing",
                "executed_test_report:missing",
            ],
        )

    def test_inline_executed_reports_do_not_satisfy_p0_structured_evidence(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        surfaces = (
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        )
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="InlineExecutedReport",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="inline_executed_report",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            for surface_id in surfaces:
                abi_test = core_path / f"{surface_id.removeprefix('obelisk.').removesuffix('.v1')}_abi.cpp"
                sdk_test = sdk_path / f"{surface_id.removeprefix('obelisk.').removesuffix('.v1')}_plugin.c"
                abi_test.write_text("// inline report fixture\n", encoding="utf-8")
                sdk_test.write_text("// inline report fixture\n", encoding="utf-8")

                missing = module.executed_test_report_missing(
                    {
                        "executed_test_report": inline_executed_test_report(
                            surface_id,
                            abi_test,
                            sdk_test,
                        )
                    },
                    surface_id,
                )

                self.assertEqual(missing, ["executed_test_report:missing"])

    def test_repo_relative_executed_test_artifact_satisfies_subcheck(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="ExecutedReportArtifact",
        ) as core_dir:
            artifact = Path(core_dir) / "permissions_admin_executed_tests.json"
            artifact_path = write_executed_test_artifact(
                artifact,
                "obelisk.permissions_admin.v1",
                argv=["python3", "-m", "unittest", "permissions_admin_promotion"],
            )

            missing = module.executed_test_report_missing(
                {"executed_test_report": artifact_path},
                "obelisk.permissions_admin.v1",
            )

        self.assertEqual(missing, [])

    def test_executed_test_artifact_command_must_match_surface(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="ExecutedReportCommandSurface",
        ) as core_dir:
            artifact = Path(core_dir) / "permissions_admin_executed_tests.json"
            artifact_path = write_executed_test_artifact(
                artifact,
                "obelisk.permissions_admin.v1",
                command="python3 -m unittest unrelated_green_suite",
            )

            missing = module.executed_test_report_missing(
                {"executed_test_report": artifact_path},
                "obelisk.permissions_admin.v1",
            )

        self.assertIn("executed_test_report:command_surface_mismatch", missing)

    def test_executed_test_artifact_must_match_active_manifest_and_header_bindings(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="ExecutedReportActiveInputs",
        ) as core_dir:
            root = Path(core_dir)
            manifest_path = root / "custom-public-sdk-surfaces.json"
            header_path = root / "CustomObeliskApi.h"
            stale_artifact = root / "stale_permissions_admin_executed_tests.json"
            active_artifact = root / "active_permissions_admin_executed_tests.json"
            manifest_path.write_text(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"), encoding="utf-8")
            header_path.write_text("#pragma once\n#define OBELISK_CUSTOM_HEADER 1\n", encoding="utf-8")
            stale_artifact_path = write_executed_test_artifact(
                stale_artifact,
                "obelisk.permissions_admin.v1",
                argv=["python3", "-m", "unittest", "permissions_admin_promotion"],
            )
            active_artifact_path = write_executed_test_artifact(
                active_artifact,
                "obelisk.permissions_admin.v1",
                argv=["python3", "-m", "unittest", "permissions_admin_promotion"],
                public_sdk_surfaces=manifest_path,
                public_header=header_path,
            )

            stale_missing = module.executed_test_report_missing(
                {"executed_test_report": stale_artifact_path},
                "obelisk.permissions_admin.v1",
                manifest_path,
                header_path,
            )
            active_missing = module.executed_test_report_missing(
                {"executed_test_report": active_artifact_path},
                "obelisk.permissions_admin.v1",
                manifest_path,
                header_path,
            )

        self.assertIn("executed_test_report:inputs.public_sdk_surfaces_path_invalid", stale_missing)
        self.assertIn("executed_test_report:inputs.public_header_path_invalid", stale_missing)
        self.assertEqual(active_missing, [])

    def test_readiness_source_artifacts_must_match_active_manifest_and_header(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="ReadinessActiveInputs",
        ) as core_dir:
            root = Path(core_dir)
            manifest_path = root / "custom-public-sdk-surfaces.json"
            header_path = root / "CustomObeliskApi.h"
            manifest_path.write_text(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"), encoding="utf-8")
            header_path.write_text("#pragma once\n#define OBELISK_CUSTOM_HEADER 1\n", encoding="utf-8")
            response_path_report_root, response_path_report = write_source_bound_command_response_report(
                root,
                surfaces_path=manifest_path,
                public_header_path=header_path,
            )
            stale_report = {
                "decisions_path": str(
                    REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
                ),
                "surfaces_path": str(PUBLIC_SDK_SURFACES),
                "public_header_path": str(PUBLIC_HEADER),
                "response_path_report_path": str(response_path_report),
                "response_path_report_root": str(response_path_report_root),
                "source_artifact_hashes": source_artifact_hashes(
                    decisions_path=REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json",
                    surfaces_path=PUBLIC_SDK_SURFACES,
                    public_header_path=PUBLIC_HEADER,
                    response_path_report_path=response_path_report,
                ),
            }
            active_report = {
                **stale_report,
                "surfaces_path": str(manifest_path),
                "public_header_path": str(header_path),
                "source_artifact_hashes": source_artifact_hashes(
                    decisions_path=REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json",
                    surfaces_path=manifest_path,
                    public_header_path=header_path,
                    response_path_report_path=response_path_report,
                ),
            }

            stale_missing = module.commands_replies_public_readiness_source_artifacts_missing(
                stale_report,
                "public_readiness_report",
                manifest_path,
                header_path,
            )
            active_missing = module.commands_replies_public_readiness_source_artifacts_missing(
                active_report,
                "public_readiness_report",
                manifest_path,
                header_path,
            )

        self.assertIn("public_readiness_report:surfaces_path_mismatch", stale_missing)
        self.assertIn("public_readiness_report:public_header_path_mismatch", stale_missing)
        self.assertEqual(active_missing, [])

    def test_command_response_source_artifacts_require_current_hashes(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandResponseSourceHashes",
        ) as core_dir:
            root = Path(core_dir)
            readiness = root / "command-chat-response-route-planning-readiness.json"
            readiness.write_text(
                json.dumps(
                    {
                        "source_root": str(root),
                        "producer": {
                            "script": "scripts/compare_reflection_snapshots.py",
                            "output_name": "command-chat-response-route-planning-readiness.json",
                            "argv": [
                                "scripts/compare_reflection_snapshots.py",
                                "--target-set",
                                "command-chat-response-route-planning",
                                "--readiness-report",
                                str(readiness),
                                "--json",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = {
                "readiness_root": str(root),
                "readiness_path": str(readiness),
                "decisions_path": str(REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"),
                "surfaces_path": str(PUBLIC_SDK_SURFACES),
                "public_header_path": str(PUBLIC_HEADER),
                "source_artifact_hashes": source_artifact_hashes(
                    readiness_path=readiness,
                    decisions_path=REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json",
                    surfaces_path=PUBLIC_SDK_SURFACES,
                    public_header_path=PUBLIC_HEADER,
                ),
            }
            current_missing = module.command_response_public_readiness_source_artifacts_missing(
                report,
                "public_readiness_report",
            )
            report["source_artifact_hashes"]["readiness_path"] = "0" * 64
            stale_missing = module.command_response_public_readiness_source_artifacts_missing(
                report,
                "public_readiness_report",
            )

        self.assertEqual(current_missing, [])
        self.assertIn(
            "public_readiness_report:readiness_path:source_artifact_sha256_mismatch",
            stale_missing,
        )

    def test_commands_replies_source_artifacts_require_response_report_hash(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandsRepliesSourceHashes",
        ) as core_dir:
            root = Path(core_dir)
            response_report_root, response_report = write_source_bound_command_response_report(root)
            report = {
                "decisions_path": str(REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"),
                "surfaces_path": str(PUBLIC_SDK_SURFACES),
                "public_header_path": str(PUBLIC_HEADER),
                "response_path_report_path": str(response_report),
                "response_path_report_root": str(response_report_root),
                "source_artifact_hashes": source_artifact_hashes(
                    decisions_path=REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json",
                    surfaces_path=PUBLIC_SDK_SURFACES,
                    public_header_path=PUBLIC_HEADER,
                    response_path_report_path=response_report,
                ),
            }
            current_missing = module.commands_replies_public_readiness_source_artifacts_missing(
                report,
                "public_readiness_report",
            )
            response_report.write_text('{"changed": true}', encoding="utf-8")
            stale_missing = module.commands_replies_public_readiness_source_artifacts_missing(
                report,
                "public_readiness_report",
            )

        self.assertEqual(current_missing, [])
        self.assertIn(
            "public_readiness_report:response_path_report_path:source_artifact_sha256_mismatch",
            stale_missing,
        )

    def test_commands_replies_source_artifacts_revalidate_nested_response_report_hashes(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandsRepliesNestedResponseHashes",
        ) as core_dir:
            root = Path(core_dir)
            response_report_root, response_report = write_source_bound_command_response_report(root)
            response_payload = json.loads(response_report.read_text(encoding="utf-8"))
            response_payload["source_artifact_hashes"]["readiness_path"] = "0" * 64
            response_report.write_text(json.dumps(response_payload, sort_keys=True), encoding="utf-8")
            report = {
                "decisions_path": str(REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"),
                "surfaces_path": str(PUBLIC_SDK_SURFACES),
                "public_header_path": str(PUBLIC_HEADER),
                "response_path_report_path": str(response_report),
                "response_path_report_root": str(response_report_root),
                "source_artifact_hashes": source_artifact_hashes(
                    decisions_path=REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json",
                    surfaces_path=PUBLIC_SDK_SURFACES,
                    public_header_path=PUBLIC_HEADER,
                    response_path_report_path=response_report,
                ),
            }

            stale_missing = module.commands_replies_public_readiness_source_artifacts_missing(
                report,
                "public_readiness_report",
            )

        self.assertIn(
            "public_readiness_report:response_path_report:readiness_path:source_artifact_sha256_mismatch",
            stale_missing,
        )

    def test_command_response_dependency_certificate_must_match_active_permissions_surface(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandResponseDependencyCertificate",
        ) as core_dir:
            root = Path(core_dir)
            permissions_evidence = self.write_permissions_admin_structured_promotion_artifacts(root)
            certificate = self.write_permissions_admin_promotion_certificate(
                root / "permissions_admin_promotion_certificate.json",
                permissions_evidence,
            )
            manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["evidence"] = {"different_reviewed_dependency": True}
                    break
            manifest_path = root / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            original_dependency = module.permissions_admin_structured_promotion_evidence_missing
            try:
                module.permissions_admin_structured_promotion_evidence_missing = lambda *_args, **_kwargs: []
                missing = module.permissions_admin_promotion_certificate_missing(
                    {"permissions_admin_promotion_certificate": certificate},
                    manifest_path,
                )
            finally:
                module.permissions_admin_structured_promotion_evidence_missing = original_dependency

        self.assertIn("permissions_admin_promotion_certificate:surface_record_sha256_mismatch", missing)

    def test_commands_replies_dependency_certificate_must_match_active_response_surface(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandsRepliesDependencyCertificate",
        ) as core_dir:
            root = Path(core_dir)
            command_response_evidence: dict[str, object] = {
                "public_readiness_report": "tests/core/unused_command_response_readiness.json",
                "executed_test_report": "tests/core/unused_command_response_tests.json",
            }
            certificate = self.write_command_response_promotion_certificate(
                root / "command_response_promotion_certificate.json",
                command_response_evidence,
            )
            manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.command_chat_response_path.v1":
                    surface["status"] = "promoted"
                    surface["evidence"] = {"different_reviewed_dependency": True}
                    break
            manifest_path = root / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            original_dependency = module.command_response_structured_promotion_evidence_missing
            try:
                module.command_response_structured_promotion_evidence_missing = lambda *_args, **_kwargs: []
                missing = module.command_response_promotion_certificate_missing(
                    {"command_response_promotion_certificate": certificate},
                    manifest_path,
                )
            finally:
                module.command_response_structured_promotion_evidence_missing = original_dependency

        self.assertIn("command_response_promotion_certificate:surface_record_sha256_mismatch", missing)

    def test_permissions_admin_structured_promotion_requires_identity_promotion_certificate(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="PermissionsAdminCertificate",
        ) as core_dir:
            evidence = self.write_permissions_admin_structured_promotion_artifacts(Path(core_dir))

            missing = permissions_admin_structured_promotion_evidence_missing(evidence)

        self.assertEqual(
            missing,
            ["player_identity_promotion_certificate:missing"],
        )

    def test_permissions_admin_structured_promotion_rejects_planning_only_reports_after_dependency(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="PermissionsAdminPlanningOnly",
        ) as core_dir:
            evidence = self.write_permissions_admin_structured_promotion_artifacts(Path(core_dir))
            original_dependency = module.player_identity_promotion_certificate_missing
            try:
                module.player_identity_promotion_certificate_missing = lambda *_args, **_kwargs: []
                missing = module.permissions_admin_structured_promotion_evidence_missing(evidence)
            finally:
                module.player_identity_promotion_certificate_missing = original_dependency

        self.assertIn("query_failclosed_report:not_promoted_evidence", missing)
        self.assertIn("public_readiness_report:not_promoted_evidence", missing)

    def test_permissions_admin_structured_promotion_rejects_nested_report_overclaims(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="PermissionsAdminReportClaims",
        ) as core_dir:
            root = Path(core_dir)
            evidence = self.write_permissions_admin_structured_promotion_artifacts(root)
            query_report_path = REPO_ROOT / evidence["query_failclosed_report"]
            readiness_report_path = REPO_ROOT / evidence["public_readiness_report"]
            query_report = json.loads(query_report_path.read_text(encoding="utf-8"))
            readiness_report = json.loads(readiness_report_path.read_text(encoding="utf-8"))
            query_report["nested_claims"] = {"stable_claim_allowed": True}
            readiness_report["nested_claims"] = {
                "public_sdk_ready": True,
                "v1_completion_ready": True,
            }
            query_report_path.write_text(json.dumps(query_report), encoding="utf-8")
            readiness_report_path.write_text(json.dumps(readiness_report), encoding="utf-8")

            original_dependency = module.player_identity_promotion_certificate_missing
            try:
                module.player_identity_promotion_certificate_missing = lambda *_args, **_kwargs: []
                missing = module.permissions_admin_structured_promotion_evidence_missing(evidence)
            finally:
                module.player_identity_promotion_certificate_missing = original_dependency

        self.assertIn("query_failclosed_report:completion_claim_without_blocker", missing)
        self.assertIn("public_readiness_report:public_or_runtime_claim_without_blocker", missing)
        self.assertIn("public_readiness_report:completion_claim_without_blocker", missing)
        self.assertIn("query_failclosed_report:not_promoted_evidence", missing)
        self.assertIn("public_readiness_report:not_promoted_evidence", missing)

    def test_permissions_admin_structured_promotion_rejects_identity_certificate_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="PermissionsAdminCertificate",
        ) as core_dir:
            root = Path(core_dir)
            identity_artifacts = self.write_player_identity_structured_promotion_artifacts(root)
            permissions_evidence = self.write_permissions_admin_structured_promotion_artifacts(root)
            certificate_path = root / "player_identity_promotion_certificate.json"
            certificate = self.write_player_identity_promotion_certificate(
                certificate_path,
                identity_artifacts,
            )
            permissions_evidence["player_identity_promotion_certificate"] = certificate
            valid_missing = permissions_admin_structured_promotion_evidence_missing(permissions_evidence)

            bad_surface_certificate = self.write_player_identity_promotion_certificate(
                certificate_path,
                identity_artifacts,
                required_by_surface="obelisk.command_chat_response_path.v1",
            )
            permissions_evidence["player_identity_promotion_certificate"] = bad_surface_certificate
            bad_surface_missing = permissions_admin_structured_promotion_evidence_missing(permissions_evidence)

            payload = json.loads(certificate_path.read_text(encoding="utf-8"))
            payload["required_by_surface"] = "obelisk.permissions_admin.v1"
            certificate_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            permissions_evidence["player_identity_promotion_certificate"] = {
                "path": str(certificate_path.relative_to(REPO_ROOT)),
                "sha256": "f" * 64,
            }
            bad_hash_missing = permissions_admin_structured_promotion_evidence_missing(permissions_evidence)

        self.assertEqual(
            valid_missing,
            [
                "player_identity_promotion_certificate:surface_record_missing_or_unpromoted",
                "player_identity_public_contract_readiness_report:promotion_blockers_remaining",
                "player_identity_public_contract_readiness_report:private_candidate_contract_candidate_only",
                "player_identity_public_contract_readiness_report:private_candidate_contract_promotion_ready_false",
                "player_identity_public_contract_readiness_report:private_candidate_contract_public_sdk_ready_false",
                "player_identity_public_contract_readiness_report:private_candidate_contract_public_header_allowed_false",
                "player_identity_public_contract_readiness_report:private_pod_layout_candidate_candidate_only",
                "player_identity_public_contract_readiness_report:private_pod_layout_candidate_promotion_ready_false",
                "player_identity_public_contract_readiness_report:private_pod_layout_candidate_public_sdk_ready_false",
                "player_identity_public_contract_readiness_report:private_pod_layout_candidate_public_header_allowed_false",
                "player_identity_public_contract_readiness_report:private_pod_layout_candidate_public_abi_ready_false",
            ],
        )
        self.assertIn("player_identity_promotion_certificate:fields_invalid", bad_surface_missing)
        self.assertIn(
            "player_identity_promotion_certificate:sha256_mismatch",
            bad_hash_missing,
        )

    def test_permissions_admin_certificate_must_match_active_identity_surface_record(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="PermissionsAdminCertificateSurface",
        ) as core_dir:
            root = Path(core_dir)
            identity_artifacts = self.write_player_identity_structured_promotion_artifacts(root)
            permissions_evidence = self.write_permissions_admin_structured_promotion_artifacts(root)
            certificate_path = root / "player_identity_promotion_certificate.json"
            permissions_evidence["player_identity_promotion_certificate"] = (
                self.write_player_identity_promotion_certificate(
                    certificate_path,
                    identity_artifacts,
                )
            )
            manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["evidence"] = identity_artifacts
                    break
            manifest_path = root / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            missing = permissions_admin_structured_promotion_evidence_missing(
                permissions_evidence,
                manifest_path,
            )

        self.assertIn("player_identity_promotion_certificate:surface_record_sha256_mismatch", missing)

    def test_p0_executed_test_artifact_missing_canonical_provenance_is_rejected(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="ExecutedReportMissingProvenance",
        ) as core_dir:
            artifact = Path(core_dir) / "player_identity_executed_tests.json"
            artifact_path = write_executed_test_artifact(
                artifact,
                "obelisk.player_identity.v1",
                argv=["python3", "-m", "unittest", "player_identity_promotion"],
            )
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            for key in ("producer", "checker", "produced_at_utc"):
                payload.pop(key)
            artifact.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

            missing = module.executed_test_report_missing(
                {"executed_test_report": artifact_path},
                "obelisk.player_identity.v1",
            )

        self.assertEqual(
            missing,
            [
                "executed_test_report:producer_invalid",
                "executed_test_report:checker_invalid",
                "executed_test_report:produced_at_utc_invalid",
            ],
        )

    def test_p0_executed_test_artifact_missing_input_bindings_is_rejected(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="ExecutedReportMissingInputs",
        ) as core_dir:
            artifact = Path(core_dir) / "permissions_admin_executed_tests.json"
            artifact_path = write_executed_test_artifact(
                artifact,
                "obelisk.permissions_admin.v1",
                argv=["python3", "-m", "unittest", "permissions_admin_promotion"],
            )
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            payload.pop("inputs")
            artifact.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

            missing = module.executed_test_report_missing(
                {"executed_test_report": artifact_path},
                "obelisk.permissions_admin.v1",
            )

        self.assertEqual(missing, ["executed_test_report:inputs_missing"])

    def test_p0_executed_test_artifact_malformed_output_hash_is_rejected(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        cases = (
            (
                {"output_sha256": "not-a-sha256"},
                ["executed_test_report:output_or_provenance_hash_invalid:output_sha256"],
            ),
            (
                {"output": {"sha256": "f" * 63}},
                ["executed_test_report:output_or_provenance_hash_invalid:output.sha256"],
            ),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                with tempfile.TemporaryDirectory(
                    dir=REPO_ROOT / "tests" / "core",
                    prefix="ExecutedReportMalformedHash",
                ) as core_dir:
                    artifact = Path(core_dir) / "permissions_admin_executed_tests.json"
                    artifact_path = write_executed_test_artifact(
                        artifact,
                        "obelisk.permissions_admin.v1",
                        argv=["python3", "-m", "unittest", "permissions_admin_promotion"],
                    )
                    payload = json.loads(artifact.read_text(encoding="utf-8"))
                    payload.pop("output_sha256")
                    payload.update(overrides)
                    artifact.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

                    missing = module.executed_test_report_missing(
                        {"executed_test_report": artifact_path},
                        "obelisk.permissions_admin.v1",
                    )

                self.assertEqual(missing, expected)

    def test_commands_replies_rejects_planning_response_report_without_permissions_admin_promotion(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="CommandsRepliesPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="commands_replies_promotion",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            response_abi = core_path / "CommandChatResponsePromotionTests.cpp"
            response_sdk = sdk_path / "command_chat_response_promotion_plugin.c"
            replies_abi = core_path / "CommandsRepliesPromotionTests.cpp"
            replies_sdk = sdk_path / "commands_replies_promotion_plugin.c"
            response_executed_report = core_path / "command_response_executed_tests.json"
            replies_executed_report = core_path / "commands_replies_executed_tests.json"
            for path in (response_abi, response_sdk, replies_abi, replies_sdk):
                path.write_text("// synthetic executed promotion fixture\n", encoding="utf-8")
            response_readiness = core_path / "command-chat-response-route-planning-readiness.json"
            response_readiness.write_text(
                json.dumps(
                    {
                        "source_root": str(core_path),
                        "producer": {
                            "script": "scripts/compare_reflection_snapshots.py",
                            "output_name": "command-chat-response-route-planning-readiness.json",
                            "argv": [
                                "scripts/compare_reflection_snapshots.py",
                                "--target-set",
                                "command-chat-response-route-planning",
                                "--readiness-report",
                                str(response_readiness),
                                "--json",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            response_report_root = core_path / "command-chat-response-public-readiness"
            response_report_root.mkdir()
            response_report = response_report_root / "command-chat-response-public-readiness.json"
            response_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "target_set": "command-chat-response-route-planning",
                        "readiness_status": "compared",
                        "decisions_status": "blocked",
                        "surfaces_status": "planning",
                        "readiness_root": str(core_path),
                        "readiness_path": str(response_readiness),
                        "decisions_path": str(
                            REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
                        ),
                        "surfaces_path": str(PUBLIC_SDK_SURFACES),
                        "public_header_path": str(PUBLIC_HEADER),
                        "source_artifact_hashes": source_artifact_hashes(
                            readiness_path=response_readiness,
                            decisions_path=REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json",
                            surfaces_path=PUBLIC_SDK_SURFACES,
                            public_header_path=PUBLIC_HEADER,
                        ),
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            replies_report = core_path / "commands_replies_public_readiness.json"
            replies_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.commands-replies-public-readiness-check.v1",
                        "surface": "obelisk.commands_replies.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                        "public_command_router_allowed": False,
                        "public_reply_or_send_chat_abi_allowed": False,
                        "public_response_path_allowed": False,
                        "decisions_status": "blocked",
                        "commands_replies_surface_status": "planning",
                        "dependency_chain": [
                            "obelisk.player_identity.v1",
                            "obelisk.permissions_admin.v1",
                            "obelisk.command_chat_response_path.v1",
                        ],
                        "decisions_path": str(
                            REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
                        ),
                        "surfaces_path": str(PUBLIC_SDK_SURFACES),
                        "public_header_path": str(PUBLIC_HEADER),
                        "response_path_report_path": str(response_report),
                        "response_path_report_root": str(response_report_root),
                        "source_artifact_hashes": source_artifact_hashes(
                            decisions_path=REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json",
                            surfaces_path=PUBLIC_SDK_SURFACES,
                            public_header_path=PUBLIC_HEADER,
                            response_path_report_path=response_report,
                        ),
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            response_executed = write_executed_test_artifact(
                response_executed_report,
                "obelisk.command_chat_response_path.v1",
                command="python3 -m unittest command_response_promotion",
            )
            replies_executed = write_executed_test_artifact(
                replies_executed_report,
                "obelisk.commands_replies.v1",
                argv=["cmake", "--build", "commands_replies_sdk_consumer"],
            )

            missing = module.surface_missing_structured_promotion_evidence(
                {
                    "id": "obelisk.commands_replies.v1",
                    "status": "promoted",
                    "evidence": {
                        "public_readiness_report": str(replies_report.relative_to(REPO_ROOT)),
                        "command_response_promotion_evidence": {
                            "public_readiness_report": str(response_report.relative_to(REPO_ROOT)),
                            "executed_test_report": response_executed,
                        },
                        "executed_test_report": replies_executed,
                    },
                }
            )

        self.assertEqual(
            missing,
            [
                "command_response_promotion_certificate:missing",
                "command_response_permissions_admin_promotion_certificate:missing",
                "command_response_permissions_admin_player_identity_promotion_certificate:missing",
                "command_response_permissions_admin_query_failclosed_report:missing",
                "command_response_permissions_admin_public_readiness_report:missing",
                "command_response_permissions_admin_executed_test_report:missing",
            ],
        )

    def test_command_response_rejects_public_readiness_without_permissions_admin_promotion(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandResponsePermissionsDependency",
        ) as core_dir:
            root = Path(core_dir)
            response_readiness = root / "command-chat-response-route-planning-readiness.json"
            response_readiness.write_text(
                json.dumps(
                    {
                        "source_root": str(root),
                        "producer": {
                            "script": "scripts/compare_reflection_snapshots.py",
                            "output_name": "command-chat-response-route-planning-readiness.json",
                            "argv": [
                                "scripts/compare_reflection_snapshots.py",
                                "--target-set",
                                "command-chat-response-route-planning",
                                "--readiness-report",
                                str(response_readiness),
                                "--json",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            response_report_root = root / "command-chat-response-public-readiness"
            response_report_root.mkdir()
            response_report = response_report_root / "command-chat-response-public-readiness.json"
            response_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "target_set": "command-chat-response-route-planning",
                        "readiness_status": "compared",
                        "decisions_status": "blocked",
                        "surfaces_status": "planning",
                        "readiness_root": str(root),
                        "readiness_path": str(response_readiness),
                        "decisions_path": str(
                            REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
                        ),
                        "surfaces_path": str(PUBLIC_SDK_SURFACES),
                        "public_header_path": str(PUBLIC_HEADER),
                        "source_artifact_hashes": source_artifact_hashes(
                            readiness_path=response_readiness,
                            decisions_path=REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json",
                            surfaces_path=PUBLIC_SDK_SURFACES,
                            public_header_path=PUBLIC_HEADER,
                        ),
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            response_executed = write_executed_test_artifact(
                root / "command_response_executed_tests.json",
                "obelisk.command_chat_response_path.v1",
                command="python3 -m unittest command_response_promotion",
            )

            missing = module.surface_missing_structured_promotion_evidence(
                {
                    "id": "obelisk.command_chat_response_path.v1",
                    "status": "promoted",
                    "evidence": {
                        "public_readiness_report": str(response_report.relative_to(REPO_ROOT)),
                        "executed_test_report": response_executed,
                    },
                }
            )

        self.assertEqual(
            missing,
            [
                "permissions_admin_promotion_certificate:missing",
                "permissions_admin_player_identity_promotion_certificate:missing",
                "permissions_admin_query_failclosed_report:missing",
                "permissions_admin_public_readiness_report:missing",
                "permissions_admin_executed_test_report:missing",
            ],
        )

    def test_commands_replies_nested_command_response_executed_tests_use_active_inputs(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandsRepliesNestedActiveInputs",
        ) as core_dir:
            root = Path(core_dir)
            manifest_path = root / "custom-public-sdk-surfaces.json"
            header_path = root / "CustomObeliskApi.h"
            manifest_path.write_text(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"), encoding="utf-8")
            header_path.write_text("#pragma once\n#define OBELISK_CUSTOM_HEADER 1\n", encoding="utf-8")
            response_readiness = root / "command-chat-response-route-planning-readiness.json"
            response_readiness.write_text(
                json.dumps(
                    {
                        "source_root": str(root),
                        "producer": {
                            "script": "scripts/compare_reflection_snapshots.py",
                            "output_name": "command-chat-response-route-planning-readiness.json",
                            "argv": [
                                "scripts/compare_reflection_snapshots.py",
                                "--target-set",
                                "command-chat-response-route-planning",
                                "--readiness-report",
                                str(response_readiness),
                                "--json",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            response_report_root = root / "command-chat-response-public-readiness"
            response_report_root.mkdir()
            response_report = response_report_root / "command-chat-response-public-readiness.json"
            response_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "target_set": "command-chat-response-route-planning",
                        "readiness_status": "compared",
                        "decisions_status": "blocked",
                        "surfaces_status": "planning",
                        "readiness_root": str(root),
                        "readiness_path": str(response_readiness),
                        "decisions_path": str(
                            REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
                        ),
                        "surfaces_path": str(manifest_path),
                        "public_header_path": str(header_path),
                        "source_artifact_hashes": source_artifact_hashes(
                            readiness_path=response_readiness,
                            decisions_path=REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json",
                            surfaces_path=manifest_path,
                            public_header_path=header_path,
                        ),
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            replies_report = root / "commands_replies_public_readiness.json"
            replies_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.commands-replies-public-readiness-check.v1",
                        "surface": "obelisk.commands_replies.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                        "public_command_router_allowed": False,
                        "public_reply_or_send_chat_abi_allowed": False,
                        "public_response_path_allowed": False,
                        "decisions_status": "blocked",
                        "commands_replies_surface_status": "planning",
                        "dependency_chain": [
                            "obelisk.player_identity.v1",
                            "obelisk.permissions_admin.v1",
                            "obelisk.command_chat_response_path.v1",
                        ],
                        "decisions_path": str(
                            REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
                        ),
                        "surfaces_path": str(manifest_path),
                        "public_header_path": str(header_path),
                        "response_path_report_path": str(response_report),
                        "response_path_report_root": str(response_report_root),
                        "source_artifact_hashes": source_artifact_hashes(
                            decisions_path=REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json",
                            surfaces_path=manifest_path,
                            public_header_path=header_path,
                            response_path_report_path=response_report,
                        ),
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            response_executed = write_executed_test_artifact(
                root / "command_response_executed_tests.json",
                "obelisk.command_chat_response_path.v1",
                command="python3 -m unittest command_response_promotion",
            )
            replies_executed = write_executed_test_artifact(
                root / "commands_replies_executed_tests.json",
                "obelisk.commands_replies.v1",
                argv=["cmake", "--build", "commands_replies_sdk_consumer"],
                public_sdk_surfaces=manifest_path,
                public_header=header_path,
            )

            missing = module.commands_replies_structured_promotion_evidence_missing(
                {
                    "public_readiness_report": str(replies_report.relative_to(REPO_ROOT)),
                    "command_response_promotion_evidence": {
                        "public_readiness_report": str(response_report.relative_to(REPO_ROOT)),
                        "executed_test_report": response_executed,
                    },
                    "executed_test_report": replies_executed,
                },
                manifest_path,
                header_path,
            )

        self.assertIn(
            "command_response_executed_test_report:inputs.public_sdk_surfaces_path_invalid",
            missing,
        )
        self.assertIn(
            "command_response_executed_test_report:inputs.public_header_path_invalid",
            missing,
        )
        self.assertNotIn("executed_test_report:inputs.public_sdk_surfaces_path_invalid", missing)
        self.assertNotIn("executed_test_report:inputs.public_header_path_invalid", missing)

    def test_command_response_structured_promotion_rejects_summary_only_readiness_report(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="CommandResponseSummaryOnly",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="command_response_summary_only",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            (core_path / "CommandChatResponsePromotionTests.cpp").write_text(
                "// synthetic executed promotion fixture\n",
                encoding="utf-8",
            )
            (sdk_path / "command_chat_response_promotion_plugin.c").write_text(
                "// synthetic executed promotion fixture\n",
                encoding="utf-8",
            )
            response_report = core_path / "command_response_public_readiness.json"
            response_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "target_set": "command-chat-response-route-planning",
                        "readiness_status": "compared",
                        "decisions_status": "blocked",
                        "surfaces_status": "planning",
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            response_executed = write_executed_test_artifact(
                core_path / "command_response_executed_tests.json",
                "obelisk.command_chat_response_path.v1",
                command="python3 -m unittest command_response_promotion",
            )

            missing = module.surface_missing_structured_promotion_evidence(
                {
                    "id": "obelisk.command_chat_response_path.v1",
                    "status": "promoted",
                    "evidence": {
                        "public_readiness_report": str(response_report.relative_to(REPO_ROOT)),
                        "executed_test_report": response_executed,
                    },
                }
            )

        self.assertIn("public_readiness_report:readiness_path:source_artifact_missing", missing)
        self.assertIn("public_readiness_report:decisions_path:source_artifact_missing", missing)
        self.assertIn("public_readiness_report:surfaces_path:source_artifact_missing", missing)
        self.assertIn("public_readiness_report:public_header_path:source_artifact_missing", missing)

    def test_command_response_structured_promotion_rejects_planning_only_readiness_after_dependency(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandResponsePlanningOnly",
        ) as core_dir:
            core_path = Path(core_dir)
            response_report = core_path / "command_response_public_readiness.json"
            response_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "target_set": "command-chat-response-route-planning",
                        "readiness_status": "compared",
                        "decisions_status": "blocked",
                        "surfaces_status": "planning",
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            response_executed_path = core_path / "command_response_executed_tests.json"
            response_executed_path.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.promoted-surface-test-execution-artifact.v1",
                        "surface_id": "obelisk.command_chat_response_path.v1",
                        "producer": "obelisk.promoted-surface-test-execution-runner.v1",
                        "checker": "scripts/check_public_sdk_v1_completion.py",
                        "produced_at_utc": "2026-06-02T00:00:00+00:00",
                        "obelisk_commit": "0" * 40,
                        "exit_code": 0,
                        "output_sha256": "0" * 64,
                        "command": "python3 -m unittest command_response_promotion",
                        "inputs": {
                            "public_sdk_surfaces": {
                                "path": str(PUBLIC_SDK_SURFACES.relative_to(REPO_ROOT)),
                                "sha256": sha256_file(PUBLIC_SDK_SURFACES),
                            },
                            "public_header": {
                                "path": str(PUBLIC_HEADER.relative_to(REPO_ROOT)),
                                "sha256": sha256_file(PUBLIC_HEADER),
                            },
                        },
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            response_executed = str(response_executed_path.relative_to(REPO_ROOT))
            original_dependency = module.permissions_admin_structured_promotion_evidence_missing
            original_certificate_dependency = module.permissions_admin_promotion_certificate_missing
            original_current_head = module.current_repo_head
            try:
                module.permissions_admin_structured_promotion_evidence_missing = lambda *_args, **_kwargs: []
                module.permissions_admin_promotion_certificate_missing = lambda *_args, **_kwargs: []
                module.current_repo_head = lambda: "0" * 40
                missing = module.command_response_structured_promotion_evidence_missing(
                    {
                        "public_readiness_report": str(response_report.relative_to(REPO_ROOT)),
                        "executed_test_report": response_executed,
                    }
                )
            finally:
                module.permissions_admin_structured_promotion_evidence_missing = original_dependency
                module.permissions_admin_promotion_certificate_missing = original_certificate_dependency
                module.current_repo_head = original_current_head

        self.assertEqual(missing, ["public_readiness_report:not_promoted_evidence"])

    def test_command_response_structured_promotion_rejects_nested_readiness_overclaims(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandResponseReportClaims",
        ) as core_dir:
            core_path = Path(core_dir)
            response_report = core_path / "command_response_public_readiness.json"
            response_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "target_set": "command-chat-response-route-planning",
                        "readiness_status": "compared",
                        "decisions_status": "blocked",
                        "surfaces_status": "planning",
                        "nested_public_contract_report": {
                            "public_sdk_ready": True,
                            "v1_completion_ready": True,
                        },
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            response_executed = write_executed_test_artifact(
                core_path / "command_response_executed_tests.json",
                "obelisk.command_chat_response_path.v1",
                command="python3 -m unittest command_response_promotion",
            )
            original_dependency = module.permissions_admin_structured_promotion_evidence_missing
            original_certificate_dependency = module.permissions_admin_promotion_certificate_missing
            try:
                module.permissions_admin_structured_promotion_evidence_missing = lambda *_args, **_kwargs: []
                module.permissions_admin_promotion_certificate_missing = lambda *_args, **_kwargs: []
                missing = module.command_response_structured_promotion_evidence_missing(
                    {
                        "public_readiness_report": str(response_report.relative_to(REPO_ROOT)),
                        "executed_test_report": response_executed,
                    }
                )
            finally:
                module.permissions_admin_structured_promotion_evidence_missing = original_dependency
                module.permissions_admin_promotion_certificate_missing = original_certificate_dependency

        self.assertIn("public_readiness_report:public_or_runtime_claim_without_blocker", missing)
        self.assertIn("public_readiness_report:completion_claim_without_blocker", missing)
        self.assertIn("public_readiness_report:not_promoted_evidence", missing)

    def test_commands_replies_structured_promotion_rejects_summary_only_readiness_report(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="CommandsRepliesSummaryOnly",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="commands_replies_summary_only",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            for path in (
                core_path / "CommandChatResponsePromotionTests.cpp",
                sdk_path / "command_chat_response_promotion_plugin.c",
                core_path / "CommandsRepliesPromotionTests.cpp",
                sdk_path / "commands_replies_promotion_plugin.c",
            ):
                path.write_text("// synthetic executed promotion fixture\n", encoding="utf-8")
            response_readiness = core_path / "command-chat-response-route-planning-readiness.json"
            response_readiness.write_text(
                json.dumps(
                    {
                        "source_root": str(core_path),
                        "producer": {
                            "script": "scripts/compare_reflection_snapshots.py",
                            "output_name": "command-chat-response-route-planning-readiness.json",
                            "argv": [
                                "scripts/compare_reflection_snapshots.py",
                                "--target-set",
                                "command-chat-response-route-planning",
                                "--readiness-report",
                                str(response_readiness),
                                "--json",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            response_report = core_path / "command_response_public_readiness.json"
            response_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                        "target_set": "command-chat-response-route-planning",
                        "readiness_status": "compared",
                        "decisions_status": "blocked",
                        "surfaces_status": "planning",
                        "readiness_root": str(core_path),
                        "readiness_path": str(response_readiness),
                        "decisions_path": str(
                            REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
                        ),
                        "surfaces_path": str(PUBLIC_SDK_SURFACES),
                        "public_header_path": str(PUBLIC_HEADER),
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            replies_report = core_path / "commands_replies_public_readiness.json"
            replies_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.commands-replies-public-readiness-check.v1",
                        "surface": "obelisk.commands_replies.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                        "public_command_router_allowed": False,
                        "public_reply_or_send_chat_abi_allowed": False,
                        "public_response_path_allowed": False,
                        "decisions_status": "blocked",
                        "commands_replies_surface_status": "planning",
                        "dependency_chain": [
                            "obelisk.player_identity.v1",
                            "obelisk.permissions_admin.v1",
                            "obelisk.command_chat_response_path.v1",
                        ],
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            response_executed = write_executed_test_artifact(
                core_path / "command_response_executed_tests.json",
                "obelisk.command_chat_response_path.v1",
                command="python3 -m unittest command_response_promotion",
            )
            replies_executed = write_executed_test_artifact(
                core_path / "commands_replies_executed_tests.json",
                "obelisk.commands_replies.v1",
                argv=["cmake", "--build", "commands_replies_sdk_consumer"],
            )

            missing = module.surface_missing_structured_promotion_evidence(
                {
                    "id": "obelisk.commands_replies.v1",
                    "status": "promoted",
                    "evidence": {
                        "public_readiness_report": str(replies_report.relative_to(REPO_ROOT)),
                        "command_response_promotion_evidence": {
                            "public_readiness_report": str(response_report.relative_to(REPO_ROOT)),
                            "executed_test_report": response_executed,
                        },
                        "executed_test_report": replies_executed,
                    },
                }
            )

        self.assertIn("public_readiness_report:decisions_path:source_artifact_missing", missing)
        self.assertIn("public_readiness_report:surfaces_path:source_artifact_missing", missing)
        self.assertIn("public_readiness_report:public_header_path:source_artifact_missing", missing)

    def test_commands_replies_structured_promotion_rejects_planning_only_readiness_after_dependency(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandsRepliesPlanningOnly",
        ) as core_dir:
            core_path = Path(core_dir)
            replies_report = core_path / "commands_replies_public_readiness.json"
            replies_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.commands-replies-public-readiness-check.v1",
                        "surface": "obelisk.commands_replies.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                        "public_command_router_allowed": False,
                        "public_reply_or_send_chat_abi_allowed": False,
                        "public_response_path_allowed": False,
                        "decisions_status": "blocked",
                        "commands_replies_surface_status": "planning",
                        "dependency_chain": [
                            "obelisk.player_identity.v1",
                            "obelisk.permissions_admin.v1",
                            "obelisk.command_chat_response_path.v1",
                        ],
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            replies_executed_path = core_path / "commands_replies_executed_tests.json"
            replies_executed_path.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.promoted-surface-test-execution-artifact.v1",
                        "surface_id": "obelisk.commands_replies.v1",
                        "producer": "obelisk.promoted-surface-test-execution-runner.v1",
                        "checker": "scripts/check_public_sdk_v1_completion.py",
                        "produced_at_utc": "2026-06-02T00:00:00+00:00",
                        "obelisk_commit": "0" * 40,
                        "exit_code": 0,
                        "output_sha256": "0" * 64,
                        "argv": ["cmake", "--build", "commands_replies_sdk_consumer"],
                        "inputs": {
                            "public_sdk_surfaces": {
                                "path": str(PUBLIC_SDK_SURFACES.relative_to(REPO_ROOT)),
                                "sha256": sha256_file(PUBLIC_SDK_SURFACES),
                            },
                            "public_header": {
                                "path": str(PUBLIC_HEADER.relative_to(REPO_ROOT)),
                                "sha256": sha256_file(PUBLIC_HEADER),
                            },
                        },
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            replies_executed = str(replies_executed_path.relative_to(REPO_ROOT))
            original_dependency = module.command_response_structured_promotion_evidence_missing
            original_certificate_dependency = module.command_response_promotion_certificate_missing
            original_current_head = module.current_repo_head
            try:
                module.command_response_structured_promotion_evidence_missing = lambda *_args, **_kwargs: []
                module.command_response_promotion_certificate_missing = lambda *_args, **_kwargs: []
                module.current_repo_head = lambda: "0" * 40
                missing = module.commands_replies_structured_promotion_evidence_missing(
                    {
                        "public_readiness_report": str(replies_report.relative_to(REPO_ROOT)),
                        "executed_test_report": replies_executed,
                    }
                )
            finally:
                module.command_response_structured_promotion_evidence_missing = original_dependency
                module.command_response_promotion_certificate_missing = original_certificate_dependency
                module.current_repo_head = original_current_head

        self.assertEqual(missing, ["public_readiness_report:not_promoted_evidence"])

    def test_commands_replies_structured_promotion_rejects_nested_readiness_overclaims(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "tests" / "core",
            prefix="CommandsRepliesReportClaims",
        ) as core_dir:
            core_path = Path(core_dir)
            replies_report = core_path / "commands_replies_public_readiness.json"
            replies_report.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.commands-replies-public-readiness-check.v1",
                        "surface": "obelisk.commands_replies.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "public_readiness_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                        "public_command_router_allowed": False,
                        "public_reply_or_send_chat_abi_allowed": False,
                        "public_response_path_allowed": False,
                        "decisions_status": "blocked",
                        "commands_replies_surface_status": "planning",
                        "dependency_chain": [
                            "obelisk.player_identity.v1",
                            "obelisk.permissions_admin.v1",
                            "obelisk.command_chat_response_path.v1",
                        ],
                        "nested_response_path_report": {
                            "runtime_ready": "ready",
                            "stable_claim_allowed": "yes",
                        },
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            replies_executed = write_executed_test_artifact(
                core_path / "commands_replies_executed_tests.json",
                "obelisk.commands_replies.v1",
                argv=["cmake", "--build", "commands_replies_sdk_consumer"],
            )
            original_dependency = module.command_response_structured_promotion_evidence_missing
            original_certificate_dependency = module.command_response_promotion_certificate_missing
            try:
                module.command_response_structured_promotion_evidence_missing = lambda *_args, **_kwargs: []
                module.command_response_promotion_certificate_missing = lambda *_args, **_kwargs: []
                missing = module.commands_replies_structured_promotion_evidence_missing(
                    {
                        "public_readiness_report": str(replies_report.relative_to(REPO_ROOT)),
                        "executed_test_report": replies_executed,
                    }
                )
            finally:
                module.command_response_structured_promotion_evidence_missing = original_dependency
                module.command_response_promotion_certificate_missing = original_certificate_dependency

        self.assertIn("public_readiness_report:public_or_runtime_claim_without_blocker", missing)
        self.assertIn("public_readiness_report:completion_claim_without_blocker", missing)
        self.assertIn("public_readiness_report:not_promoted_evidence", missing)

    def test_dependency_chain_accounting_keeps_invalid_promoted_identity_visible(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                    "sdk_consumer_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                }
                break
        if "obelisk.player_identity.v1" not in manifest["promoted_surfaces"]:
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.player_identity.v1"
        ]
        release_statement = "\n".join(
            (
                "obelisk.player_identity.v1: promoted - reviewed ABI and SDK evidence."
                if line.startswith("obelisk.player_identity.v1:")
                else line
            )
            for line in release_statement.splitlines()
        ) + "\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertIn(
            "obelisk.player_identity.v1",
            payload["v1_sdk_blocker_outcome_summary"]["dependency_chain_remaining"],
        )
        self.assertEqual(
            payload["unpromoted_required_dependency_chain"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(payload["v1_sdk_progress"]["completion_blockers_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["complete_sdk_claim_progress_percent"], 0)
        self.assertNotIn(
            "obelisk.player_identity.v1",
            payload["v1_sdk_progress"]["completion_blockers_with_promoted_outcome"],
        )
        self.assertIn(
            "obelisk.player_identity.v1",
            payload["v1_sdk_progress"]["completion_blockers_with_manifest_promoted_status"],
        )
        outcome_by_surface = {
            row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]
        }
        self.assertTrue(
            outcome_by_surface["obelisk.player_identity.v1"]["unresolved_for_complete_sdk_claim"]
        )

    def test_p0_progress_does_not_count_surface_when_promoted_dependency_lacks_evidence(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PermissionsAdminPromotion",
            ) as permissions_core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="permissions_admin_promotion",
            ) as permissions_sdk_dir,
        ):
            permissions_core_test = Path(permissions_core_dir) / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = Path(permissions_sdk_dir) / "permissions_admin_promotion_plugin.c"
            permissions_core_test.write_text("// promoted permissions admin ABI placeholder\n", encoding="utf-8")
            permissions_sdk_test.write_text("// promoted permissions admin SDK placeholder\n", encoding="utf-8")

            manifest, release_statement = complete_excluded_manifest()
            promoted_ids = {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                        "sdk_consumer_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.CheckPermissionWithCopiedPrincipal"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "query-only fail-closed permission checks over copied principals",
                            "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                            "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                            "promoted copied principal semantics",
                        ],
                    }
            for surface_id in promoted_ids:
                if surface_id not in manifest["promoted_surfaces"]:
                    manifest["promoted_surfaces"].append(surface_id)
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in promoted_ids
            ]
            release_statement = "\n".join(
                (
                    f"{surface_id}: promoted - reviewed ABI and SDK evidence."
                    if surface_id in promoted_ids
                    else line
                )
                for line in release_statement.splitlines()
                for surface_id in [line.split(":", 1)[0]]
            ) + "\n"

            manifest_path = Path(permissions_core_dir) / "public_sdk_surfaces.json"
            statement_path = Path(permissions_core_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        progress = payload["v1_sdk_progress"]
        self.assertEqual(progress["completion_blockers_promoted_count"], 0)
        self.assertEqual(progress["p0_chain_promoted_count"], 0)
        self.assertEqual(progress["complete_sdk_claim_progress_percent"], 0)
        outcome_by_surface = {
            row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]
        }
        self.assertFalse(outcome_by_surface["obelisk.player_identity.v1"]["promotion_evidence_satisfied"])
        self.assertFalse(outcome_by_surface["obelisk.permissions_admin.v1"]["dependency_claims_satisfied"])
        self.assertFalse(outcome_by_surface["obelisk.permissions_admin.v1"]["counts_toward_complete_sdk_claim"])

    def test_planning_completion_blocker_requires_exclusion_contract(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["v1_completion_required"] = False
        manifest["stable_release_contract"]["claim_allowed"] = False
        manifest["planning_surfaces"] = ["obelisk.player_identity.v1"]
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.player_identity.v1"
        ]
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "planning"
                surface.pop("v1_decision_contract", None)
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("completion_blocker_exclusion_contract_missing", payload["blockers"])
        self.assertIn("v1_sdk_completion_blockers_unresolved", payload["blockers"])
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertEqual(payload["missing_completion_blocker_exclusion_contracts"], ["obelisk.player_identity.v1"])
        self.assertEqual(payload["unresolved_completion_blockers"], ["obelisk.player_identity.v1"])

    def test_release_statement_required_for_v1_completion_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_required_for_v1_completion", payload["blockers"])


if __name__ == "__main__":
    unittest.main()
