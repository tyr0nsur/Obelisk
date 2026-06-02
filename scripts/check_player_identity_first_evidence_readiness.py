#!/usr/bin/env python3
"""Combined preflight for the player-identity first-evidence lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import check_player_identity_lifecycle_anchor_candidates as lifecycle_anchor_candidates
import check_player_identity_principal_invalidation_policy as principal_invalidation_policy
import check_player_identity_public_contract_gap_report as public_contract_gap_report
import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_runtime_principal_lifecycle_evidence
import check_player_identity_runtime_principal_lifecycle_evidence as runtime_principal_lifecycle_evidence
import check_player_principal_lifecycle_window_request as player_principal_lifecycle_window_request
import validate_offline_artifact_gate as offline_artifact_gate
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_SCHEMA = "obelisk.player-identity-first-evidence-readiness.v1"
FIRST_EVIDENCE_SCHEMA = "obelisk.players-identity-first-evidence.v1"
REFLECTION_INVENTORY_PACK_SCHEMA = "obelisk.reflection-inventory-pack.v1"
CORE_DUMP_EVIDENCE_PACK_SCHEMA = "obelisk.core-dump-evidence-pack.v1"
RADARE2_STATIC_ORIENTATION_SCHEMA = "obelisk.radare2-static-orientation-windows.v1"
PLAYER_IDENTITY_TARGET_SET = "players-identity-lifecycle-intake"
MISSING_TARGET_PREFIX = "missing_required_target:"
MAX_DIAGNOSIS_ITEMS = 8
PLAYER_IDENTITY_TARGET_COUNT = 12
EXPECTED_SHOOTERGAME_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
PLAYER_IDENTITY_RAW_RUN_PREFIX = "player-identity-offline-"
REQUIRED_ADMIN_TARGETS = [
    "ShooterPlayerController.ServerKickPlayer",
    "ShooterPlayerController.ServerListPlayers",
]
CORE_EVIDENCE_MANIFEST_PATTERN = (
    "player-identity-offline-<run-id>/core-evidence-pack/manifest.json"
)
REFLECTION_INVENTORY_MANIFEST_PATTERN = (
    "player-identity-offline-<run-id>/reflection-inventory-pack/manifest.json"
)
RAW_LAYOUT_HELPER = "scripts/prepare_player_identity_offline_raw_layout.py"
RAW_INPUT_VALIDATOR = "scripts/validate_player_identity_raw_inputs.py"
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
STATIC_ORIENTATION_SCHEMA_PREFIX = "obelisk.player-identity-static-"
STATIC_ORIENTATION_MANIFEST_TOKENS = (
    "radare2-static-orientation",
    "static-orientation",
)
DEFAULT_ARTIFACT_ROOT = Path("/home/flowcommunity-ark/obelisk-artifacts")
APPROVED_WORKSPACE_FALLBACK_ROOT = Path("/servidor/ark/workspace-offline")
APPROVED_CANDIDATE_ROOT_FALLBACK = (
    APPROVED_WORKSPACE_FALLBACK_ROOT
    / "player-identity-offline-identity-vanilla-gdb-20260529T012853Z"
    / "focal-snapshots"
)
APPROVED_LIFECYCLE_ANCHOR_CANDIDATES_FALLBACK = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-identity-lifecycle-anchor-candidates.json"
)
APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-identity-principal-invalidation-policy.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the read-only player-identity preflight: reflection-inventory pack "
            "readiness, committed fixture coverage, and first-evidence fail-closed build."
        )
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
        help="Non-protected artifact root to scan for reflection inventory packs.",
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
        help="Sanitized UFunction snapshot root used for fixture coverage and first-evidence build.",
    )
    parser.add_argument(
        "--candidate-root",
        type=Path,
        help="Optional distinct sanitized second-source snapshot root for layout comparison.",
    )
    parser.add_argument(
        "--lifecycle-anchor-candidates-manifest",
        type=Path,
        help=(
            "Optional consume-only obelisk.players-identity-lifecycle-anchor-candidates.v1 "
            "manifest. It can satisfy lifecycle anchor evidence only; it cannot promote "
            "identity, runtime readiness, or public SDK readiness."
        ),
    )
    parser.add_argument(
        "--principal-invalidation-policy-manifest",
        type=Path,
        help=(
            "Optional consume-only obelisk.players-identity-principal-invalidation-policy.v1 "
            "manifest. It can satisfy the planning policy precondition only; it cannot "
            "promote identity, runtime readiness, or public SDK readiness."
        ),
    )
    parser.add_argument(
        "--runtime-principal-lifecycle-evidence-manifest",
        type=Path,
        help=(
            "Optional obelisk.players-identity-runtime-principal-lifecycle-evidence.v1 "
            "synthetic/redacted shape fixture. It validates private manifest shape only; "
            "it cannot satisfy approved runtime evidence, runtime readiness, promotion, "
            "or public SDK readiness."
        ),
    )
    parser.add_argument(
        "--approved-runtime-principal-lifecycle-evidence-manifest",
        type=Path,
        help=(
            "Optional obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1 "
            "manifest built from a copied/sanitized runtime observer summary. It can satisfy "
            "the runtime-evidence blocker only; it cannot promote public identity, runtime "
            "readiness, or public SDK readiness."
        ),
    )
    parser.add_argument(
        "--player-principal-lifecycle-window-request",
        type=Path,
        help=(
            "Optional pre-window request pack JSON. This records request-pack readiness only; "
            "it cannot satisfy approved runtime evidence or authorize server operations."
        ),
    )
    parser.add_argument(
        "--player-principal-lifecycle-window-env",
        type=Path,
        help="observer-window.env paired with --player-principal-lifecycle-window-request.",
    )
    parser.add_argument(
        "--player-identity-public-contract-decisions",
        type=Path,
        default=REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json",
        help="Player identity public contract decisions manifest for the offline gap guardrail.",
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=REPO_ROOT / "docs" / "public_sdk_surfaces.json",
        help="Public SDK surfaces manifest for the offline identity gap guardrail.",
    )
    parser.add_argument(
        "--player-identity-private-candidate-contract",
        type=Path,
        default=REPO_ROOT / "docs" / "research" / "2026-06-01-player-identity-private-candidate-contract.json",
        help="Private candidate-only identity contract for the offline gap guardrail.",
    )
    parser.add_argument(
        "--player-identity-identifier-redaction-evidence",
        type=Path,
        default=REPO_ROOT / "docs" / "research" / "2026-06-02-player-identity-identifier-redaction-evidence.json",
        help="Sanitized identifier-redaction evidence consumed as contract-review input only.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h",
        help="Public SDK header for accidental player identity symbol scanning.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Compatibility flag; output is always JSON.",
    )
    return parser.parse_args()


def run_json_command(args: list[str], *, check: bool = False) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]:
    result = subprocess.run(
        [sys.executable, *args],
        check=False,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    payload: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return result, payload


def parse_missing_required_targets(stderr: str) -> list[str]:
    missing: list[str] = []
    for token in stderr.replace(",", " ").split():
        if token.startswith(MISSING_TARGET_PREFIX):
            target = token.removeprefix(MISSING_TARGET_PREFIX)
            if target:
                missing.append(target)
    return sorted(set(missing))


def bounded_values(values: list[Any]) -> dict[str, Any]:
    if len(values) <= MAX_DIAGNOSIS_ITEMS:
        return {"items": values}
    return {
        "items": values[:MAX_DIAGNOSIS_ITEMS],
        "total_count": len(values),
        "omitted_count": len(values) - MAX_DIAGNOSIS_ITEMS,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_obelisk_commit() -> str:
    env_commit = os.environ.get("OBELISK_COMMIT", "").strip()
    if env_commit:
        return env_commit
    return "unknown"


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def reject_player_identity_artifact_root(path: Path, label: str) -> Path:
    """Reject live/protected roots while allowing approved offline workspaces."""

    reject_symlink_component(path, label)
    resolved = reject_protected_input_path(path, label)
    return resolved


def rejected_artifact_root_inventory_payload(root: Path, detail: str) -> dict[str, Any]:
    return {
        "ready": False,
        "accepted_pack": None,
        "manifests_scanned": 0,
        "candidate_packs": [],
        "reasons": [
            {
                "reason": "wrong_target_scope",
                "path": str(root),
                "detail": detail,
            }
        ],
    }


def bounded_artifact_file_scan(root: Path, *, max_depth: int = 6) -> dict[str, Any]:
    try:
        resolved = reject_player_identity_artifact_root(root, "--artifact-root")
    except SystemExit as exc:
        return {
            "status": "artifact_root_rejected",
            "artifact_root_only": True,
            "error": str(exc),
            "server_root_excluded": "/servidor/ark",
            "shooter_game_server_candidates": [],
            "core_like_candidates": [],
            "ready_to_build_core_evidence_pack": False,
        }
    if not resolved.exists():
        return {
            "status": "artifact_root_missing",
            "artifact_root_only": True,
            "resolved_root": str(resolved),
            "server_root_excluded": "/servidor/ark",
            "shooter_game_server_candidates": [],
            "core_like_candidates": [],
            "ready_to_build_core_evidence_pack": False,
        }
    if not resolved.is_dir():
        return {
            "status": "artifact_root_not_directory",
            "artifact_root_only": True,
            "resolved_root": str(resolved),
            "server_root_excluded": "/servidor/ark",
            "shooter_game_server_candidates": [],
            "core_like_candidates": [],
            "ready_to_build_core_evidence_pack": False,
        }

    shooter_candidates: list[dict[str, Any]] = []
    core_candidates: list[dict[str, Any]] = []
    omitted_shooter = 0
    omitted_core = 0
    root_depth = len(resolved.parts)
    for directory, dirnames, filenames in os.walk(resolved, followlinks=False):
        current = Path(directory)
        depth = len(current.parts) - root_depth
        dirnames[:] = [name for name in dirnames if not (current / name).is_symlink()]
        if depth >= max_depth:
            dirnames[:] = []
        for filename in filenames:
            path = current / filename
            if path.is_symlink():
                continue
            lower_name = filename.lower()
            is_shooter = filename == "ShooterGameServer"
            is_core_like = lower_name == "core" or lower_name.startswith("core.") or lower_name.endswith(".core")
            if not is_shooter and not is_core_like:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if is_shooter:
                if len(shooter_candidates) < MAX_DIAGNOSIS_ITEMS:
                    try:
                        digest = sha256_file(path)
                    except OSError as exc:
                        digest = f"unreadable:{exc}"
                    shooter_candidates.append(
                        {
                            "path": str(path),
                            "size_bytes": stat.st_size,
                            "sha256": digest,
                            "matches_current_binary": digest == EXPECTED_SHOOTERGAME_SHA256,
                        }
                    )
                else:
                    omitted_shooter += 1
            if is_core_like:
                if len(core_candidates) < MAX_DIAGNOSIS_ITEMS:
                    core_candidates.append(
                        {
                            "path": str(path),
                            "size_bytes": stat.st_size,
                        }
                    )
                else:
                    omitted_core += 1

    has_matching_binary = any(candidate.get("matches_current_binary") is True for candidate in shooter_candidates)
    has_core_like = bool(core_candidates)
    paired_raw_inputs: list[dict[str, Any]] = []
    rejected_raw_input_pairs: list[dict[str, Any]] = []
    for candidate in shooter_candidates:
        candidate_path = candidate.get("path")
        if candidate.get("matches_current_binary") is not True or not isinstance(candidate_path, str):
            continue
        binary_path = Path(candidate_path)
        if binary_path.parent.name != "raw":
            continue
        run_root = binary_path.parent.parent
        if (
            not run_root.name.startswith(PLAYER_IDENTITY_RAW_RUN_PREFIX)
            or len(run_root.name) == len(PLAYER_IDENTITY_RAW_RUN_PREFIX)
        ):
            if len(rejected_raw_input_pairs) < MAX_DIAGNOSIS_ITEMS:
                rejected_raw_input_pairs.append(
                    {
                        "run_root": str(run_root),
                        "binary": str(binary_path),
                        "reason": "run_root_name_must_start_with_player_identity_offline",
                    }
                )
            continue
        core_path = binary_path.parent / "core"
        try:
            if core_path.exists() and core_path.is_file() and not core_path.is_symlink():
                paired_raw_inputs.append(
                    {
                        "run_root": str(run_root),
                        "binary": str(binary_path),
                        "core": str(core_path),
                    }
                )
        except OSError:
            continue

    has_paired_raw_inputs = bool(paired_raw_inputs)
    if has_paired_raw_inputs:
        status = "offline_binary_and_core_like_inputs_present"
    elif has_matching_binary and has_core_like:
        status = "offline_binary_and_unpaired_core_like_inputs_present"
    elif has_matching_binary:
        status = "offline_binary_present_core_like_input_missing"
    elif shooter_candidates:
        status = "offline_binary_present_hash_mismatch"
    elif has_core_like:
        status = "core_like_input_present_offline_binary_missing"
    else:
        status = "offline_binary_and_core_like_inputs_missing"

    return {
        "status": status,
        "artifact_root_only": True,
        "resolved_root": str(resolved),
        "server_root_excluded": "/servidor/ark",
        "approved_offline_workspace_roots": ["/servidor/ark/workspace-offline"],
        "expected_shooter_game_server_sha256": EXPECTED_SHOOTERGAME_SHA256,
        "shooter_game_server_candidates": shooter_candidates,
        "omitted_shooter_game_server_candidates": omitted_shooter,
        "core_like_candidates": core_candidates,
        "omitted_core_like_candidates": omitted_core,
        "paired_raw_inputs": paired_raw_inputs,
        "rejected_raw_input_pairs": rejected_raw_input_pairs,
        "ready_to_build_core_evidence_pack": has_paired_raw_inputs,
        "non_claims": [
            "file presence only; core-like filenames are not accepted core evidence packs",
            "core and ShooterGameServer must be paired under the same player-identity-offline run raw directory before the core evidence pack step is considered runnable",
            "does not read protected live-server or raw dump roots, attach to processes, execute scanners, or validate runtime state",
        ],
    }


def artifact_root_diagnosis(inventory_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not inventory_payload:
        return {
            "status": "inventory_readiness_output_missing_or_malformed",
            "candidate_pack_count": None,
            "reason_counts": {},
            "next_useful_command": "rerun_check_reflection_inventory_pack_readiness_with_json_stdout",
        }

    candidate_packs = inventory_payload.get("candidate_packs")
    if not isinstance(candidate_packs, list):
        candidate_packs = []
    reasons = inventory_payload.get("reasons")
    if not isinstance(reasons, list):
        reasons = []

    reason_counts: dict[str, int] = {}
    reason_examples: dict[str, dict[str, Any]] = {}
    for reason in reasons:
        if not isinstance(reason, dict):
            continue
        code = reason.get("reason")
        if not isinstance(code, str):
            continue
        reason_counts[code] = reason_counts.get(code, 0) + 1
        if code not in reason_examples:
            example: dict[str, Any] = {}
            if isinstance(reason.get("path"), str):
                example["path"] = reason["path"]
            if isinstance(reason.get("field"), str):
                example["field"] = reason["field"]
            if isinstance(reason.get("detail"), str):
                example["detail"] = reason["detail"]
            scanned_paths = reason.get("scanned_paths")
            if isinstance(scanned_paths, list):
                example["scanned_paths"] = bounded_values(scanned_paths)
            targets = reason.get("targets")
            if isinstance(targets, list):
                example["targets"] = bounded_values(targets)
            if example:
                reason_examples[code] = example

    blocked_candidate_summaries: list[dict[str, Any]] = []
    for pack in candidate_packs[:MAX_DIAGNOSIS_ITEMS]:
        if not isinstance(pack, dict):
            continue
        pack_reasons = pack.get("reasons")
        if not isinstance(pack_reasons, list):
            pack_reasons = []
        fields: list[str] = []
        codes: list[str] = []
        for reason in pack_reasons:
            if not isinstance(reason, dict):
                continue
            code = reason.get("reason")
            field = reason.get("field")
            if isinstance(code, str) and code not in codes:
                codes.append(code)
            if isinstance(field, str) and field not in fields:
                fields.append(field)
        blocked_candidate_summaries.append(
            {
                "manifest": pack.get("manifest"),
                "ready": pack.get("ready"),
                "reason_codes": codes[:MAX_DIAGNOSIS_ITEMS],
                "blocking_fields": fields[:MAX_DIAGNOSIS_ITEMS],
                "matched_targets": pack.get("matched_targets"),
            }
        )

    accepted_pack = inventory_payload.get("accepted_pack")
    if isinstance(accepted_pack, dict):
        status = "accepted_reflection_inventory_pack"
    elif not inventory_payload.get("manifests_scanned"):
        status = "no_manifest_files_found"
    elif not candidate_packs:
        status = "no_obelisk_reflection_inventory_pack_manifests_found"
    elif "missing_core_evidence_pack" in reason_counts:
        status = "reflection_inventory_pack_missing_complete_core_evidence_pack"
    elif "missing_target" in reason_counts:
        status = "reflection_inventory_pack_missing_required_admin_targets"
    elif "wrong_target_scope" in reason_counts:
        status = "reflection_inventory_pack_wrong_scope_or_candidate_status"
    else:
        status = "reflection_inventory_pack_blocked"

    return {
        "status": status,
        "candidate_pack_count": len(candidate_packs),
        "accepted_manifest": accepted_pack.get("manifest") if isinstance(accepted_pack, dict) else None,
        "reason_counts": reason_counts,
        "reason_examples": reason_examples,
        "blocked_candidate_packs": blocked_candidate_summaries,
        "next_useful_command": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_reflection_inventory_pack_readiness.py "
            "--root <artifact-root>"
        ),
    }


def root_has_no_identity_inventory_candidate(inventory_payload: dict[str, Any] | None) -> bool:
    diagnosis = artifact_root_diagnosis(inventory_payload)
    return diagnosis.get("status") in {
        "no_manifest_files_found",
        "no_obelisk_reflection_inventory_pack_manifests_found",
    }


def scan_reflection_inventory_root(root: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None, str | None]:
    try:
        reject_player_identity_artifact_root(root, "--artifact-root")
    except SystemExit as exc:
        return (
            subprocess.CompletedProcess(
                ["check_reflection_inventory_pack_readiness.py", "--root", str(root)],
                1,
                "",
                str(exc),
            ),
            rejected_artifact_root_inventory_payload(root, str(exc)),
            str(exc),
        )
    result, payload = run_json_command(
        [
            str(SCRIPT_DIR / "check_reflection_inventory_pack_readiness.py"),
            "--root",
            str(root),
        ]
    )
    return result, payload, None


def approved_workspace_input_fallbacks(args: argparse.Namespace) -> dict[str, Any]:
    """Select read-only approved workspace inputs when the caller uses defaults.

    These fallbacks do not promote public readiness. They only keep the default
    preflight aligned with already-reviewed offline evidence in the approved workspace.
    Explicit caller inputs always win.
    """

    requested_default_root = getattr(args, "artifact_root", None) == DEFAULT_ARTIFACT_ROOT
    candidate_root = getattr(args, "candidate_root", None)
    lifecycle_manifest = getattr(args, "lifecycle_anchor_candidates_manifest", None)
    principal_manifest = getattr(args, "principal_invalidation_policy_manifest", None)

    result: dict[str, Any] = {
        "candidate_root": candidate_root,
        "lifecycle_anchor_candidates_manifest": lifecycle_manifest,
        "principal_invalidation_policy_manifest": principal_manifest,
        "used": {},
        "non_claims": [
            "approved workspace fallbacks are read-only routing aids",
            "fallback input selection does not promote identity, runtime readiness, public SDK readiness, or v1 completion",
        ],
    }
    if not requested_default_root:
        return result

    if candidate_root is None and APPROVED_CANDIDATE_ROOT_FALLBACK.is_dir():
        result["candidate_root"] = APPROVED_CANDIDATE_ROOT_FALLBACK
        result["used"]["candidate_root"] = str(APPROVED_CANDIDATE_ROOT_FALLBACK)
    if lifecycle_manifest is None and APPROVED_LIFECYCLE_ANCHOR_CANDIDATES_FALLBACK.is_file():
        result["lifecycle_anchor_candidates_manifest"] = APPROVED_LIFECYCLE_ANCHOR_CANDIDATES_FALLBACK
        result["used"]["lifecycle_anchor_candidates_manifest"] = str(APPROVED_LIFECYCLE_ANCHOR_CANDIDATES_FALLBACK)
    if principal_manifest is None and APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK.is_file():
        result["principal_invalidation_policy_manifest"] = APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK
        result["used"]["principal_invalidation_policy_manifest"] = str(APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK)
    return result


def second_source_missing_count(coverage_payload: dict[str, Any] | None) -> int | None:
    if not isinstance(coverage_payload, dict):
        return None
    totals = coverage_payload.get("totals")
    if not isinstance(totals, dict):
        return None
    value = totals.get("second_source_missing")
    return value if isinstance(value, int) else None


def second_source_total(coverage_payload: dict[str, Any] | None, key: str) -> int | None:
    if not isinstance(coverage_payload, dict):
        return None
    totals = coverage_payload.get("totals")
    if not isinstance(totals, dict):
        return None
    value = totals.get(key)
    return value if isinstance(value, int) else None


def second_source_layout_accepted(
    *,
    coverage_payload_valid: bool,
    coverage_targets: Any,
    coverage_comparable: Any,
    coverage_blocked: Any,
    second_source_accepted: int | None,
    second_source_missing: int | None,
    second_source_inconclusive: int | None,
    second_source_rejected: int | None,
) -> bool:
    accepted_count = second_source_accepted
    if (
        accepted_count is None
        and second_source_missing == 0
        and second_source_inconclusive == 0
        and second_source_rejected == 0
        and coverage_comparable == coverage_targets
    ):
        accepted_count = coverage_comparable
    return (
        coverage_payload_valid
        and coverage_targets == PLAYER_IDENTITY_TARGET_COUNT
        and coverage_comparable == PLAYER_IDENTITY_TARGET_COUNT
        and coverage_blocked == 0
        and accepted_count == PLAYER_IDENTITY_TARGET_COUNT
        and second_source_missing == 0
        and second_source_inconclusive == 0
        and second_source_rejected == 0
    )


def coverage_payload_has_required_totals(coverage_payload: dict[str, Any] | None) -> bool:
    if not isinstance(coverage_payload, dict):
        return False
    totals = coverage_payload.get("totals")
    if not isinstance(totals, dict):
        return False
    return all(
        type(totals.get(key)) is int
        for key in (
            "targets",
            "comparable",
            "blocked",
            "second_source_missing",
            "second_source_inconclusive",
            "second_source_rejected",
        )
    )


def build_layout_lifecycle_state(
    *,
    layout_accepted: bool,
    second_source_accepted: int | None,
    second_source_missing: int | None,
    second_source_inconclusive: int | None,
    second_source_rejected: int | None,
    lifecycle_ready: bool,
    principal_invalidation_ready: bool,
    lifecycle_diagnosis: dict[str, Any],
) -> dict[str, Any]:
    lifecycle_invalidation_remains = layout_accepted and (
        not lifecycle_ready or not principal_invalidation_ready
    )
    if layout_accepted and lifecycle_ready and not principal_invalidation_ready:
        status = "lifecycle_anchor_layout_accepted_principal_invalidation_remains"
        statement = "lifecycle anchor layout accepted; principal invalidation remains"
        remaining_work = ["principal_invalidation_semantics"]
    elif lifecycle_invalidation_remains:
        status = "second_source_layout_accepted_lifecycle_invalidation_remains"
        statement = "second-source layout accepted; lifecycle invalidation remains"
        remaining_work = [
            "accepted_lifecycle_anchor_evidence",
            "principal_invalidation_semantics",
        ]
    elif layout_accepted:
        status = "second_source_layout_accepted_candidate_only"
        statement = "second-source layout accepted; candidate-only validation remains"
        remaining_work = []
    else:
        status = "second_source_layout_not_accepted"
        statement = "second-source layout not accepted"
        remaining_work = ["accepted_distinct_second_source_layout"]

    return {
        "status": status,
        "statement": statement,
        "second_source_layout_accepted": layout_accepted,
        "second_source_accepted": second_source_accepted,
        "second_source_missing": second_source_missing,
        "second_source_inconclusive": second_source_inconclusive,
        "second_source_rejected": second_source_rejected,
        "lifecycle_invalidation_remains": lifecycle_invalidation_remains,
        "lifecycle_anchor_ready": lifecycle_ready,
        "principal_invalidation_ready": principal_invalidation_ready,
        "lifecycle_anchor_blockers": (
            lifecycle_diagnosis.get("blockers")
            if isinstance(lifecycle_diagnosis.get("blockers"), list)
            else []
        ),
        "remaining_work": remaining_work,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "non_claims": [
            "layout acceptance is planning-only evidence and does not promote public identity, permissions, commands, lookup, ResourceHandle, mutation, return override, runtime hooks, or SDK surface",
            "lifecycle invalidation still requires a reviewed fail-closed identity/principal policy before public promotion",
        ],
    }


def string_list(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def target_set_coverage_entries(coverage: Any) -> list[dict[str, Any]]:
    if not isinstance(coverage, dict):
        return []
    entries: list[dict[str, Any]] = []
    for key in ("target_sets", "declared_target_sets"):
        raw_entries = coverage.get(key)
        if isinstance(raw_entries, list):
            entries.extend(entry for entry in raw_entries if isinstance(entry, dict))
            if PLAYER_IDENTITY_TARGET_SET in raw_entries:
                entries.append(
                    {
                        "name": PLAYER_IDENTITY_TARGET_SET,
                        "expected_targets": string_list(coverage.get("requested_targets")),
                        "covered_targets": string_list(coverage.get("covered_targets"))
                        or string_list(coverage.get("matched_targets"))
                        or string_list(coverage.get("requested_targets")),
                        "missing_targets": coverage.get("missing_targets", []),
                        "complete": coverage.get("complete", True),
                    }
                )
    if not entries and coverage.get("name") == PLAYER_IDENTITY_TARGET_SET:
        entries.append(coverage)
    return entries


def reflection_inventory_chain_diagnosis(inventory_payload: dict[str, Any] | None) -> dict[str, Any]:
    """Require the complete core-evidence -> full reflection-inventory chain.

    The lower-level inventory readiness checker is still authoritative for reading
    manifests. This wrapper also fails closed if a mocked, stale, or summarized payload
    tries to substitute ScriptStruct inventory, direct-core mode, standalone snapshots,
    static orientation, or a two-function-only inventory for the full identity lane.
    """

    if not isinstance(inventory_payload, dict) or inventory_payload.get("ready") is not True:
        return {"ready": False, "blockers": [], "accepted_manifest": None}

    blockers: list[str] = []
    accepted_pack = inventory_payload.get("accepted_pack")
    if not isinstance(accepted_pack, dict):
        return {
            "ready": False,
            "blockers": ["accepted_reflection_inventory_pack_missing"],
            "accepted_manifest": None,
        }

    if accepted_pack.get("schema") != REFLECTION_INVENTORY_PACK_SCHEMA:
        blockers.append("accepted_pack_schema_not_reflection_inventory")
    if accepted_pack.get("status") != "candidate-only":
        blockers.append("accepted_reflection_inventory_status_not_candidate_only")
    if accepted_pack.get("promotion_status") != "not_promoted_candidate_only":
        blockers.append("accepted_reflection_inventory_promotion_status_mismatch")

    pack_blockers = accepted_pack.get("blockers")
    if pack_blockers not in ([], None):
        blockers.append("accepted_reflection_inventory_blockers_present")

    inputs = accepted_pack.get("inputs")
    if not isinstance(inputs, dict):
        inputs = {}
        blockers.append("accepted_reflection_inventory_inputs_missing")

    evidence_pack_manifest = inputs.get("evidence_pack_manifest")
    if not isinstance(evidence_pack_manifest, str) or not evidence_pack_manifest.endswith("manifest.json"):
        blockers.append("accepted_reflection_inventory_core_evidence_pack_manifest_missing")
    else:
        evidence_pack_path = Path(evidence_pack_manifest)
        evidence_pack_parts = {part.lower() for part in evidence_pack_path.parts}
        if evidence_pack_path.name != "manifest.json" or evidence_pack_path.parent.name != "core-evidence-pack":
            blockers.append("accepted_reflection_inventory_core_evidence_pack_manifest_path_not_core_evidence_pack")
        if any(
            token in part
            for part in evidence_pack_parts
            for token in STATIC_ORIENTATION_MANIFEST_TOKENS
        ):
            blockers.append("accepted_reflection_inventory_static_orientation_manifest_not_core_evidence")
    evidence_pack_schema = inputs.get("evidence_pack_schema")
    if evidence_pack_schema is not None and evidence_pack_schema != CORE_DUMP_EVIDENCE_PACK_SCHEMA:
        blockers.append("accepted_reflection_inventory_core_evidence_pack_schema_mismatch")
    if (
        evidence_pack_schema == RADARE2_STATIC_ORIENTATION_SCHEMA
        or (
            isinstance(evidence_pack_schema, str)
            and evidence_pack_schema.startswith(STATIC_ORIENTATION_SCHEMA_PREFIX)
        )
    ):
        blockers.append("accepted_reflection_inventory_static_orientation_manifest_not_core_evidence")
    evidence_pack_status = inputs.get("evidence_pack_status")
    if evidence_pack_status is not None and evidence_pack_status != "complete":
        blockers.append("accepted_reflection_inventory_core_evidence_pack_not_complete")
    if any(key in inputs for key in ("core", "core_path", "ark_binary", "ark_binary_path")) and not evidence_pack_manifest:
        blockers.append("accepted_reflection_inventory_direct_core_mode_not_allowed")

    target_sets = string_list(inputs.get("target_sets"))
    if target_sets and target_sets != [PLAYER_IDENTITY_TARGET_SET]:
        blockers.append("accepted_reflection_inventory_input_target_set_mismatch")

    coverage = accepted_pack.get("target_set_coverage")
    coverage_entries = target_set_coverage_entries(coverage)
    coverage_entry = next(
        (
            entry
            for entry in coverage_entries
            if entry.get("name") == PLAYER_IDENTITY_TARGET_SET
            or entry.get("target_set") == PLAYER_IDENTITY_TARGET_SET
        ),
        None,
    )
    if not isinstance(coverage_entry, dict):
        blockers.append("accepted_reflection_inventory_target_set_coverage_missing")
        expected_targets: list[str] = []
        covered_targets: list[str] = []
    else:
        expected_targets = (
            string_list(coverage_entry.get("expected_targets"))
            or string_list(coverage_entry.get("targets"))
        )
        covered_targets = (
            string_list(coverage_entry.get("covered_targets"))
            or string_list(coverage_entry.get("matched_targets"))
            or string_list(accepted_pack.get("matched_targets"))
        )
        missing_targets = coverage_entry.get("missing_targets")
        if missing_targets not in ([], None):
            blockers.append("accepted_reflection_inventory_target_set_coverage_incomplete")
        if coverage_entry.get("complete") is False:
            blockers.append("accepted_reflection_inventory_target_set_coverage_incomplete")

    if len(expected_targets) != PLAYER_IDENTITY_TARGET_COUNT:
        blockers.append("accepted_reflection_inventory_not_full_player_identity_target_set")
    if len(set(covered_targets)) != PLAYER_IDENTITY_TARGET_COUNT:
        blockers.append("accepted_reflection_inventory_covered_targets_incomplete")
    for target in REQUIRED_ADMIN_TARGETS:
        if target not in covered_targets:
            blockers.append(f"accepted_reflection_inventory_missing_required_target:{target}")

    summary = accepted_pack.get("summary")
    if isinstance(summary, dict) and summary.get("fname_root_ready") is not True:
        blockers.append("accepted_reflection_inventory_fname_root_not_ready")

    return {
        "ready": not blockers,
        "blockers": sorted(set(blockers)),
        "accepted_manifest": accepted_pack.get("manifest") if isinstance(accepted_pack.get("manifest"), str) else None,
    }


def lifecycle_anchor_diagnosis(first_evidence_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(first_evidence_payload, dict):
        return {
            "session_start_accepted": False,
            "session_end_accepted": False,
            "accepted_start_targets": [],
            "accepted_end_targets": [],
            "blockers": [
                "players_identity_first_evidence_not_buildable",
                "accepted_session_start_anchor_missing",
                "accepted_session_end_anchor_missing",
            ],
        }
    anchors = first_evidence_payload.get("lifecycle_anchors")
    if not isinstance(anchors, dict):
        return {
            "session_start_accepted": False,
            "session_end_accepted": False,
            "accepted_start_targets": [],
            "accepted_end_targets": [],
            "blockers": [
                "lifecycle_anchors_missing_from_first_evidence",
                "accepted_session_start_anchor_missing",
                "accepted_session_end_anchor_missing",
            ],
        }
    blockers = anchors.get("blockers")
    accepted_start_targets = anchors.get("accepted_start_targets")
    accepted_end_targets = anchors.get("accepted_end_targets")
    return {
        "session_start_accepted": anchors.get("session_start_accepted") is True,
        "session_end_accepted": anchors.get("session_end_accepted") is True,
        "accepted_start_targets": accepted_start_targets if isinstance(accepted_start_targets, list) else [],
        "accepted_end_targets": accepted_end_targets if isinstance(accepted_end_targets, list) else [],
        "blockers": blockers if isinstance(blockers, list) else [],
        "source": "players_identity_first_evidence",
        "principal_invalidation_ready": False,
    }


def first_evidence_consume_gate_diagnosis(
    first_evidence_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "mode": "consume",
        "evaluated": False,
        "status": "not_evaluated",
        "ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "blockers": [],
        "blocker_reasons": [],
        "non_claims": [
            "schema-specific consume diagnostic only; does not promote player identity, runtime readiness, public SDK readiness, lookup, ResourceHandle, mutation, or return override",
        ],
    }
    if not isinstance(first_evidence_payload, dict):
        return {**base, "reason": "players_identity_first_evidence_payload_missing_or_malformed"}
    if first_evidence_payload.get("schema") != FIRST_EVIDENCE_SCHEMA:
        return {
            **base,
            "reason": "players_identity_first_evidence_schema_mismatch",
            "recorded_schema": first_evidence_payload.get("schema"),
        }
    required_gate_fields = {
        "artifact_identity",
        "fields",
        "forced_redacted_fields",
        "forbidden_fields",
        "generated_from",
        "non_claims",
        "promotion_gate",
        "safety_summary",
        "target_set_coverage",
        "targets",
    }
    missing_gate_fields = sorted(required_gate_fields.difference(first_evidence_payload))
    if missing_gate_fields:
        return {
            **base,
            "reason": "players_identity_first_evidence_payload_not_full_artifact_shape",
            "missing_gate_fields": missing_gate_fields,
        }

    blockers = offline_artifact_gate.validate_players_identity_first_evidence_manifest(
        first_evidence_payload,
        label="<build_redacted_ufunction_signatures.stdout>",
        mode="consume",
    )
    reasons = [
        blocker["reason"]
        for blocker in blockers
        if isinstance(blocker, dict) and isinstance(blocker.get("reason"), str)
    ]
    return {
        **base,
        "evaluated": True,
        "status": "accepted" if not blockers else "blocked",
        "ready": not blockers,
        "blockers": blockers,
        "blocker_reasons": sorted(set(reasons)),
    }


def lifecycle_anchor_candidate_manifest_diagnosis(path: Path | None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "provided": path is not None,
        "path": str(path) if path is not None else None,
        "ready": False,
        "session_start_accepted": False,
        "session_end_accepted": False,
        "accepted_start_targets": [],
        "accepted_end_targets": [],
        "principal_invalidation_ready": False,
        "blockers": [],
        "source": "players_identity_lifecycle_anchor_candidates",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "non_claims": [
            "consume-only lifecycle anchor layout evidence; does not promote public identity, permissions, commands, lookup, ResourceHandle, mutation, return override, runtime hooks, or SDK surface",
        ],
    }
    if path is None:
        return base

    try:
        payload = lifecycle_anchor_candidates.load_json(path)
    except SystemExit as exc:
        return {**base, "blockers": ["lifecycle_anchor_manifest_unreadable"], "error": str(exc)}

    validation = lifecycle_anchor_candidates.validate_manifest_details(payload, promote=False)
    blockers = [blocker["reason"] for blocker in validation.blockers]
    accepted_start_targets = validation.accepted_by_role.get("session_start", [])
    accepted_end_targets = validation.accepted_by_role.get("session_end", [])
    expected_start = ["ShooterGameMode.HandleNewPlayer"]
    expected_end = ["ShooterGameMode.OnLogout"]
    if accepted_start_targets != expected_start:
        blockers.append("accepted_session_start_anchor_missing")
    if accepted_end_targets != expected_end:
        blockers.append("accepted_session_end_anchor_missing")

    lifecycle_acceptance = payload.get("lifecycle_acceptance")
    lifecycle_blockers = (
        lifecycle_acceptance.get("blockers")
        if isinstance(lifecycle_acceptance, dict) and isinstance(lifecycle_acceptance.get("blockers"), list)
        else []
    )
    principal_invalidation_unresolved = "principal_invalidation_semantics_unresolved" in lifecycle_blockers
    if not principal_invalidation_unresolved:
        blockers.append("principal_invalidation_semantics_overclaim")

    ready = (
        not validation.blockers
        and principal_invalidation_unresolved
        and accepted_start_targets == expected_start
        and accepted_end_targets == expected_end
    )
    artifact_identity = payload.get("artifact_identity")
    source_artifact_ids = (
        string_list(artifact_identity.get("source_artifact_ids"))
        if isinstance(artifact_identity, dict)
        else []
    )
    accepted_anchor_snapshot_sha256_by_target: dict[str, str] = {}
    for anchor in payload.get("candidate_anchors", []):
        if not isinstance(anchor, dict) or anchor.get("accepted") is not True:
            continue
        target = anchor.get("target")
        evidence = anchor.get("evidence")
        source_snapshot_sha256 = (
            evidence.get("source_snapshot_sha256")
            if isinstance(evidence, dict) and isinstance(evidence.get("source_snapshot_sha256"), str)
            else None
        )
        if isinstance(target, str) and source_snapshot_sha256:
            accepted_anchor_snapshot_sha256_by_target[target] = source_snapshot_sha256
    return {
        **base,
        "ready": ready,
        "session_start_accepted": ready,
        "session_end_accepted": ready,
        "accepted_start_targets": accepted_start_targets if ready else [],
        "accepted_end_targets": accepted_end_targets if ready else [],
        "principal_invalidation_ready": False,
        "blockers": sorted(set(blockers)),
        "lifecycle_acceptance_blockers": lifecycle_blockers,
        "artifact_status": payload.get("artifact_status"),
        "readiness_classification": payload.get("readiness_classification"),
        "schema": payload.get("schema"),
        "artifact_identity_source_artifact_ids": source_artifact_ids,
        "accepted_anchor_snapshot_sha256_by_target": accepted_anchor_snapshot_sha256_by_target,
    }


def merge_lifecycle_diagnosis(
    first_evidence_diagnosis: dict[str, Any],
    lifecycle_candidate_diagnosis: dict[str, Any],
) -> dict[str, Any]:
    if lifecycle_candidate_diagnosis.get("ready") is True:
        blockers = [
            item
            for item in string_list(lifecycle_candidate_diagnosis.get("lifecycle_acceptance_blockers"))
            if item != "principal_invalidation_semantics_unresolved"
        ]
        return {
            "session_start_accepted": True,
            "session_end_accepted": True,
            "accepted_start_targets": string_list(lifecycle_candidate_diagnosis.get("accepted_start_targets")),
            "accepted_end_targets": string_list(lifecycle_candidate_diagnosis.get("accepted_end_targets")),
            "blockers": blockers,
            "source": "players_identity_lifecycle_anchor_candidates",
            "principal_invalidation_ready": False,
            "principal_invalidation_blockers": ["principal_invalidation_semantics_unresolved"],
        }
    return first_evidence_diagnosis


def principal_invalidation_policy_diagnosis(path: Path | None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "provided": path is not None,
        "path": str(path) if path is not None else None,
        "ready": False,
        "policy_consume_ready": False,
        "runtime_evidence_ready": False,
        "principal_invalidation_ready": False,
        "blockers": [],
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "non_claims": [
            "consume-only principal invalidation policy; does not promote public identity, permissions, commands, lookup, ResourceHandle, mutation, return override, runtime hooks, or SDK surface",
        ],
    }
    if path is None:
        return base
    try:
        payload = principal_invalidation_policy.load_json(path)
    except SystemExit as exc:
        return {**base, "blockers": ["principal_invalidation_policy_manifest_unreadable"], "error": str(exc)}
    validation = principal_invalidation_policy.validate_manifest(payload, check_mode="consume")
    blockers = [blocker["reason"] for blocker in validation.blockers]
    policy_consume_ready = not blockers
    lifecycle_layout_source = payload.get("lifecycle_layout_source")
    source_binding = (
        lifecycle_layout_source.get("source_binding")
        if isinstance(lifecycle_layout_source, dict) and isinstance(lifecycle_layout_source.get("source_binding"), dict)
        else {}
    )
    return {
        **base,
        "ready": policy_consume_ready,
        "policy_consume_ready": policy_consume_ready,
        "principal_invalidation_ready": policy_consume_ready,
        "runtime_evidence_ready": False,
        "blockers": blockers,
        "principal_fields": validation.principal_fields,
        "invalidation_cases": validation.invalidation_cases,
        "negative_consumer_rules": validation.negative_rules,
        "lifecycle_source_binding": source_binding,
    }


def first_evidence_source_artifact_ids(first_evidence_payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(first_evidence_payload, dict):
        return []
    artifact_identity = first_evidence_payload.get("artifact_identity")
    if not isinstance(artifact_identity, dict):
        return []
    return string_list(artifact_identity.get("source_artifact_ids"))


def first_evidence_snapshot_sha256_by_target(first_evidence_payload: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(first_evidence_payload, dict):
        return {}
    generated_from = first_evidence_payload.get("generated_from")
    input_snapshots = (
        generated_from.get("input_snapshots")
        if isinstance(generated_from, dict) and isinstance(generated_from.get("input_snapshots"), list)
        else []
    )
    result: dict[str, str] = {}
    for snapshot in input_snapshots:
        if not isinstance(snapshot, dict):
            continue
        target = snapshot.get("target")
        sha256 = snapshot.get("sha256")
        if isinstance(target, str) and isinstance(sha256, str):
            result[target] = sha256
    return result


def planning_provenance_blockers(
    *,
    first_evidence_payload: dict[str, Any] | None,
    lifecycle_candidate_diagnosis: dict[str, Any],
    principal_policy_diagnosis: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if lifecycle_candidate_diagnosis.get("ready") is True:
        first_source_ids = first_evidence_source_artifact_ids(first_evidence_payload)
        lifecycle_source_ids = string_list(lifecycle_candidate_diagnosis.get("artifact_identity_source_artifact_ids"))
        if not first_source_ids or lifecycle_source_ids != first_source_ids:
            blockers.append("lifecycle_anchor_source_artifact_identity_mismatch")
        first_snapshot_by_target = first_evidence_snapshot_sha256_by_target(first_evidence_payload)
        lifecycle_snapshot_by_target = lifecycle_candidate_diagnosis.get("accepted_anchor_snapshot_sha256_by_target")
        lifecycle_snapshot_by_target = (
            lifecycle_snapshot_by_target if isinstance(lifecycle_snapshot_by_target, dict) else {}
        )
        for target in ("ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"):
            if target in first_snapshot_by_target and lifecycle_snapshot_by_target.get(target) != first_snapshot_by_target.get(target):
                blockers.append("lifecycle_anchor_source_snapshot_mismatch")
                break

    if principal_policy_diagnosis.get("policy_consume_ready") is True:
        binding = principal_policy_diagnosis.get("lifecycle_source_binding")
        if not isinstance(binding, dict) or not binding:
            blockers.append("principal_policy_lifecycle_source_binding_missing")
        else:
            if binding.get("lifecycle_manifest_schema") != lifecycle_candidate_diagnosis.get("schema"):
                blockers.append("principal_policy_lifecycle_schema_mismatch")
            if binding.get("artifact_identity_source_artifact_ids") != lifecycle_candidate_diagnosis.get(
                "artifact_identity_source_artifact_ids"
            ):
                blockers.append("principal_policy_lifecycle_source_artifact_identity_mismatch")
            if binding.get("accepted_start_targets") != lifecycle_candidate_diagnosis.get("accepted_start_targets"):
                blockers.append("principal_policy_lifecycle_start_targets_mismatch")
            if binding.get("accepted_end_targets") != lifecycle_candidate_diagnosis.get("accepted_end_targets"):
                blockers.append("principal_policy_lifecycle_end_targets_mismatch")
    if blockers:
        return ["lifecycle_anchor_first_evidence_provenance_unbound", *sorted(set(blockers))]
    return []


def planning_provenance_next_action(
    *,
    blockers: list[str],
    lifecycle_anchor_candidates_manifest: Path | None,
    principal_invalidation_policy_manifest: Path | None,
) -> dict[str, Any]:
    active = "lifecycle_anchor_first_evidence_provenance_unbound" in blockers
    required_artifacts: list[dict[str, Any]] = []
    if active:
        if any(blocker.startswith("lifecycle_anchor_") for blocker in blockers):
            required_artifacts.append(
                {
                    "artifact": "lifecycle_anchor_candidates",
                    "schema": "obelisk.players-identity-lifecycle-anchor-candidates.v1",
                    "current_path": (
                        str(lifecycle_anchor_candidates_manifest)
                        if lifecycle_anchor_candidates_manifest
                        else None
                    ),
                    "required_alignment": (
                        "artifact_identity.source_artifact_ids and accepted anchor "
                        "source_snapshot_sha256 values must match the current first-evidence report"
                    ),
                }
            )
        if any(blocker.startswith("principal_policy_") for blocker in blockers):
            required_artifacts.append(
                {
                    "artifact": "principal_invalidation_policy",
                    "schema": "obelisk.players-identity-principal-invalidation-policy.v1",
                    "current_path": (
                        str(principal_invalidation_policy_manifest)
                        if principal_invalidation_policy_manifest
                        else None
                    ),
                    "required_alignment": (
                        "lifecycle_layout_source.source_binding must match the bound lifecycle "
                        "manifest schema, source artifact ids, and accepted start/end anchors"
                    ),
                }
            )
    return {
        "active": active,
        "safe_offline_only": True,
        "recommended_next_step": (
            "regenerate_or_select_lifecycle_and_principal_planning_manifests_bound_to_current_first_evidence"
            if active
            else None
        ),
        "required_artifacts": required_artifacts,
        "verification_command": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate_bound_identity_sources.py "
            "--lifecycle-anchor-candidates-manifest <bound-lifecycle-json> "
            "--principal-invalidation-policy-manifest <bound-principal-json> --json"
            if active
            else None
        ),
        "expected_next_blocker_after_alignment": "approved_runtime_evidence_missing" if active else None,
        "forbidden_shortcuts": [
            "do not hand-edit stale source bindings into readiness",
            "do not reinterpret standalone lifecycle/principal manifests as bound evidence",
            "do not request or run runtime/server capture for this provenance blocker",
            "do not claim public identity, permissions/admin, command response, commands/replies, SDK readiness, or v1 completion",
        ],
        "non_claim": (
            "diagnostic routing only; this does not create evidence, approve runtime capture, "
            "or promote player identity/public SDK readiness"
        ),
    }


def runtime_principal_lifecycle_evidence_manifest_diagnosis(path: Path | None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "provided": path is not None,
        "path": str(path) if path is not None else None,
        "ready": False,
        "shape_accepted_by_this_checker": False,
        "approved_runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "blockers": [],
        "remaining_blockers": ["approved_runtime_evidence_missing"],
        "non_claims": [
            "synthetic/redacted shape fixture only; does not approve runtime evidence, authorize server work, promote public SDK, or publish claims",
        ],
    }
    if path is None:
        return base
    try:
        payload = runtime_principal_lifecycle_evidence.load_json(path)
    except SystemExit as exc:
        return {**base, "blockers": ["runtime_principal_lifecycle_manifest_unreadable"], "error": str(exc)}
    validation = runtime_principal_lifecycle_evidence.validate_manifest(payload, check_mode="consume")
    report = runtime_principal_lifecycle_evidence.build_report(payload, validation, check_mode="consume")
    blockers = [blocker["reason"] for blocker in validation.blockers]
    return {
        **base,
        "ready": not blockers,
        "shape_accepted_by_this_checker": report["shape_accepted_by_this_checker"],
        "blockers": blockers,
        "observed_cases": report["observed_cases"],
        "approved_runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
    }


def approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(path: Path | None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "provided": path is not None,
        "path": str(path) if path is not None else None,
        "ready": False,
        "approved_runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "blockers": [],
        "remaining_blockers": ["approved_runtime_evidence_missing"],
        "non_claims": [
            "approved runtime observer evidence can satisfy only the runtime evidence blocker; it does not promote public SDK, identity lookup, permissions, commands, or release claims",
        ],
    }
    if path is None:
        return base
    try:
        payload = approved_runtime_principal_lifecycle_evidence.load_json(path)
    except SystemExit as exc:
        return {**base, "blockers": ["approved_runtime_principal_lifecycle_manifest_unreadable"], "error": str(exc)}
    validation = approved_runtime_principal_lifecycle_evidence.validate_manifest(payload, check_mode="consume")
    report = approved_runtime_principal_lifecycle_evidence.build_report(payload, validation, check_mode="consume")
    blockers = [blocker["reason"] for blocker in validation.blockers]
    if not validation.blockers:
        if report.get("approved_runtime_evidence_present") is not True:
            blockers.append("approved_runtime_report_evidence_present_not_true")
        if report.get("runtime_evidence_ready") is not True:
            blockers.append("approved_runtime_report_runtime_evidence_ready_not_true")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
            if report.get(key) is not False:
                blockers.append(f"approved_runtime_report_{key}_not_false")
        if report.get("next_blocker") != "identity_public_contract_gate_missing":
            blockers.append("approved_runtime_report_next_blocker_not_identity_public_contract_gate")
    ready = not blockers
    return {
        **base,
        "ready": ready,
        "approved_runtime_evidence_present": ready,
        "runtime_evidence_ready": ready,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "remaining_blockers": [] if ready else ["approved_runtime_evidence_missing"],
        "blockers": blockers,
        "observed_runtime_cases": report["observed_runtime_cases"],
        "consumer_cases": report["consumer_cases"],
    }


def player_principal_lifecycle_window_request_diagnosis(
    request_path: Path | None,
    env_path: Path | None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "provided": request_path is not None or env_path is not None,
        "request_path": str(request_path) if request_path is not None else None,
        "env_path": str(env_path) if env_path is not None else None,
        "ready": False,
        "request_pack_ready": False,
        "bundle_inputs_ready": False,
        "request_pack_is_runtime_evidence": False,
        "operator_current_turn_runtime_window_approval_required": False,
        "approved_runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "blockers": [],
        "remaining_blockers": ["approved_runtime_evidence_missing"],
        "next_required_runtime_artifacts": [],
        "non_claims": [
            "pre-window request-pack diagnosis only; does not authorize server operations, runtime capture, Discord, GitHub publication, public SDK readiness, or v1 completion",
        ],
    }
    if request_path is None and env_path is None:
        return base
    blockers: list[str] = []
    if request_path is None:
        blockers.append("player_principal_lifecycle_window_request_missing")
    if env_path is None:
        blockers.append("player_principal_lifecycle_window_env_missing")
    if blockers:
        return {**base, "blockers": blockers}
    try:
        payload = player_principal_lifecycle_window_request.read_json(request_path)
        env_blockers: list[dict[str, Any]] = []
        env = player_principal_lifecycle_window_request.read_env(env_path, env_blockers)
    except SystemExit as exc:
        return {**base, "blockers": ["player_principal_lifecycle_window_request_unreadable"], "error": str(exc)}
    operator_request_path = request_path.parent / "operator-approval-request.md"
    operator_request_markdown = player_principal_lifecycle_window_request.read_text_sidecar(
        operator_request_path,
        "operator_request",
        env_blockers,
    )
    validation = player_principal_lifecycle_window_request.validate_payload(payload, env)
    report = player_principal_lifecycle_window_request.build_report(validation)
    validation.blockers[:0] = env_blockers
    operator_request_verified = player_principal_lifecycle_window_request.validate_operator_request_markdown(
        payload,
        env,
        operator_request_markdown,
        validation.blockers,
    )
    report = player_principal_lifecycle_window_request.build_report(
        validation,
        operator_request_verified=operator_request_verified,
    )
    blockers = [blocker["reason"] for blocker in validation.blockers]
    ready = not blockers and report.get("request_pack_ready") is True and operator_request_verified
    return {
        **base,
        "ready": ready,
        "request_pack_ready": ready,
        "bundle_inputs_ready": False,
        "operator_current_turn_runtime_window_approval_required": ready,
        "blockers": blockers,
        "operator_request_path": str(operator_request_path),
        "operator_request_verified": operator_request_verified,
        "next_blocker": report.get("next_blocker"),
        "target": report.get("target"),
        "run_id": report.get("run_id"),
        "next_required_runtime_artifacts": [
            {
                "artifact": "copied_obelisk_log",
                "path": payload.get("copied_log_path"),
                "required_for": "offline_runtime_principal_lifecycle_bundle_builder_input",
                "satisfies_approved_runtime_evidence": False,
            },
            {
                "artifact": "checked_window_manifest_env",
                "path": payload.get("window_manifest_path"),
                "required_for": "offline_runtime_principal_lifecycle_bundle_builder_input",
                "satisfies_approved_runtime_evidence": False,
            },
            {
                "artifact": "approved_runtime_principal_lifecycle_evidence_manifest",
                "path": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                "required_for": "approved_runtime_evidence_missing",
                "satisfies_approved_runtime_evidence": True,
            },
        ] if ready else [],
    }


def runtime_principal_lifecycle_evidence_requirements() -> dict[str, Any]:
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence.requirements.v1",
        "status": "missing",
        "approval_required": True,
        "accepted_by_this_preflight": False,
        "required_for": ["promote", "public_readiness", "runtime_readiness"],
        "minimum_required_runtime_observations": [
            {
                "case": "session_start_anchor",
                "target": "ShooterGameMode.HandleNewPlayer",
                "required_signal": "copied_principal_lifecycle_state_created_or_refreshed",
                "required_role": "session_start",
                "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "required_copied_bool_values": ["1", "1"],
                "required_copied_fields": ["bIsFromLogin", "ReturnValue"],
                "required_order": 1,
            },
            {
                "case": "session_start_rejected_anchor",
                "target": "ShooterGameMode.HandleNewPlayer",
                "required_signal": "copied_principal_lifecycle_state_not_created_for_rejected_start",
                "required_role": "session_start_rejected",
                "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "required_copied_bool_values": ["0", "1"],
                "required_copied_fields": ["bIsFromLogin", "ReturnValue"],
                "required_order": 2,
            },
            {
                "case": "session_end_anchor",
                "target": "ShooterGameMode.OnLogout",
                "required_signal": "copied_principal_lifecycle_state_invalidated",
                "required_role": "session_end",
                "required_copied_bool_fields": [],
                "required_copied_bool_values": [],
                "required_copied_fields": [],
                "required_order": 3,
            },
        ],
        "required_consumer_boundary_assertions": [
            {
                "case": "stale_after_logout",
                "target": "post_logout_consumer_check",
                "required_signal": "stale_or_missing_generation_denies_without_lookup",
                "required_role": "none",
                "runtime_observed": False,
                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                "required_copied_bool_fields": [],
                "required_copied_bool_values": [],
                "required_copied_fields": ["generation_state"],
                "required_order": 1,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "target": "principal_consumer_boundary",
                "required_signal": "fail_closed_deny",
                "required_role": "none",
                "runtime_observed": False,
                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                "required_copied_bool_fields": [],
                "required_copied_bool_values": [],
                "required_copied_fields": [],
                "required_order": 2,
            },
        ],
        "privacy_boundary": [
            "copied opaque principal state only",
            "no Steam/EOS ids, player names, IP-like values, tribe ids, raw UE pointers, FNames, GObjects, raw params, or persistent lookup keys",
        ],
        "approval_boundary": {
            "approved_runtime_evidence_present": False,
            "runtime_work_authorized_by_this_report": False,
            "server_operations_authorized_by_this_report": False,
            "publication_authorized_by_this_report": False,
            "separate_operator_approval_required_before": [
                "server access or player-facing evidence windows",
                "debug attachment, ptrace, gcore, or runtime scanners",
                "server starts, stops, restarts, or marker changes",
                "Discord/community/beta-test notices",
                "GitHub publication, tags, pushes, or release claims",
            ],
        },
        "insufficient_evidence": [
            "offline layout comparison alone",
            "candidate lifecycle layout anchors alone",
            "principal invalidation policy manifest alone",
            "raw ProcessEvent traces without copied privacy boundary",
            "admin/listing UFunctions",
            "any positive claim based on names, platform ids, UE pointers, GObjects, FNames, ResourceHandle, lookup, mutation, or return override",
        ],
        "non_claims": [
            "requirements only; does not execute runtime work, approve a server window, promote identity, or add public SDK surface",
        ],
    }


def player_identity_public_contract_gap_diagnosis(
    *,
    decisions: Path,
    surfaces: Path,
    private_candidate_contract: Path,
    identifier_redaction_evidence: Path,
    principal_invalidation_policy_manifest: Path | None,
    public_header: Path,
) -> dict[str, Any]:
    blockers: list[str] = []
    report_blockers: list[dict[str, Any]] = []
    decisions_payload = public_contract_gap_report.load_json(decisions, "decisions", report_blockers)
    surfaces_payload = public_contract_gap_report.load_json(surfaces, "surfaces", report_blockers)
    candidate_payload = public_contract_gap_report.load_json(
        private_candidate_contract,
        "private_candidate_contract",
        report_blockers,
    )
    if decisions_payload:
        public_contract_gap_report.validate_decisions(decisions_payload, report_blockers)
    surface = (
        public_contract_gap_report.validate_surfaces(surfaces_payload, report_blockers)
        if surfaces_payload
        else {}
    )
    if candidate_payload:
        public_contract_gap_report.validate_private_candidate(candidate_payload, report_blockers)
    redaction_diagnosis = public_contract_gap_report.validate_identifier_redaction_evidence(
        identifier_redaction_evidence,
        report_blockers,
    )
    principal_policy_gap_report = public_contract_gap_report.validate_principal_invalidation_policy(
        principal_invalidation_policy_manifest or APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK,
        report_blockers,
    )
    header_scan = public_contract_gap_report.scan_public_header(public_header, report_blockers)
    args = argparse.Namespace(
        decisions=decisions,
        surfaces=surfaces,
        private_candidate_contract=private_candidate_contract,
        identifier_redaction_evidence=identifier_redaction_evidence,
        principal_invalidation_policy=principal_invalidation_policy_manifest or APPROVED_PRINCIPAL_INVALIDATION_POLICY_FALLBACK,
        public_header=public_header,
    )
    report = public_contract_gap_report.build_report(
        args,
        report_blockers,
        decisions_payload,
        surface,
        header_scan,
        candidate_payload,
        redaction_diagnosis,
        principal_policy_gap_report,
    )

    if report.get("schema") != public_contract_gap_report.SCHEMA:
        blockers.append("player_identity_public_contract_gap_report_schema_mismatch")
    if report.get("guardrail_passed") is not True:
        blockers.append("player_identity_public_contract_gap_guardrail_not_passed")
    if report.get("status") != "blocked":
        blockers.append("player_identity_public_contract_gap_status_not_blocked")
    allowed_primary_gaps = {
        public_contract_gap_report.PRIMARY_OFFLINE_GAP,
        public_contract_gap_report.PRIMARY_OFFLINE_GAP_AFTER_IDENTIFIER_REDACTION,
    }
    if report.get("primary_offline_gap") not in allowed_primary_gaps:
        blockers.append("player_identity_public_contract_gap_primary_gap_mismatch")
    if report.get("runtime_evidence_missing") is not True:
        blockers.append("player_identity_public_contract_gap_runtime_evidence_missing_not_true")
    for key in ("accepted_for_contract_review", "promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
        if report.get(key) is not False:
            blockers.append(f"player_identity_public_contract_gap_{key}_not_false")
    ready = not blockers
    return {
        "provided": True,
        "returncode": 0 if report.get("guardrail_passed") is True else 1,
        "ready": ready,
        "guardrail_passed": report.get("guardrail_passed") is True,
        "status": report.get("status"),
        "primary_offline_gap": report.get("primary_offline_gap"),
        "contract_review_inputs_resolved": report.get("contract_review_inputs_resolved", []),
        "identifier_redaction_evidence": report.get("identifier_redaction_evidence", {}),
        "principal_invalidation_policy": report.get("principal_invalidation_policy", {}),
        "runtime_evidence_missing": report.get("runtime_evidence_missing"),
        "accepted_for_contract_review": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "blockers": blockers,
        "report_blockers": report.get("blockers", []),
        "surface_manifest": report.get("surface_manifest", {}),
        "non_claims": [
            "identity public-contract gap report is an offline guardrail only; it does not satisfy approved runtime evidence or public identity promotion",
        ],
    }


def first_matching_binary_path(offline_inputs: dict[str, Any]) -> str | None:
    candidates = offline_inputs.get("shooter_game_server_candidates")
    if not isinstance(candidates, list):
        return None
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("matches_current_binary") is True and isinstance(candidate.get("path"), str):
            return candidate["path"]
    return None


def unambiguous_core_like_path(offline_inputs: dict[str, Any]) -> str | None:
    candidates = offline_inputs.get("core_like_candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        return None
    if offline_inputs.get("omitted_core_like_candidates") not in (None, 0):
        return None
    candidate = candidates[0]
    if not isinstance(candidate, dict) or not isinstance(candidate.get("path"), str):
        return None
    return candidate["path"]


def next_actionable_blocker(
    *,
    inventory_ready: bool,
    inventory_payload_ready: bool,
    inventory_chain: dict[str, Any],
    downstream_blockers: list[str],
    offline_inputs: dict[str, Any],
    raw_binary_pattern: Path,
    raw_core_pattern: Path,
    core_manifest_pattern: Path,
    reflection_inventory_pattern: Path,
    next_operator_recipe: dict[str, Any],
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "not_artifact_gate": True,
    }
    if inventory_payload_ready and not inventory_ready:
        return {
            **base,
            "code": "accepted_reflection_inventory_chain_incomplete",
            "blocked_until": "accepted_reflection_inventory_pack_chained_to_complete_core_evidence_pack",
            "why": "a lower-level readiness payload reported ready, but the identity chain guard rejected it",
            "chain_blockers": inventory_chain.get("blockers") if isinstance(inventory_chain.get("blockers"), list) else [],
            "next_required_artifact": {
                "schema": REFLECTION_INVENTORY_PACK_SCHEMA,
                "path_pattern": str(reflection_inventory_pattern),
            },
        }
    if not inventory_ready:
        offline_status = offline_inputs.get("status")
        matching_binary_path = first_matching_binary_path(offline_inputs)
        if offline_status == "offline_binary_present_core_like_input_missing":
            return {
                **base,
                "code": "non_protected_core_input_missing",
                "blocked_until": "non_protected_core_dump_input",
                "why": "the artifact root has a matching offline ShooterGameServer, but no core-like input to package",
                "available_binary": matching_binary_path,
                "missing_input_path_pattern": str(raw_core_pattern),
                "next_required_artifact": {
                    "schema": CORE_DUMP_EVIDENCE_PACK_SCHEMA,
                    "path_pattern": str(core_manifest_pattern),
                },
                "next_command_after_input": next_operator_recipe["build_core_evidence_pack"],
            }
        if offline_status == "offline_binary_and_unpaired_core_like_inputs_present":
            return {
                **base,
                "code": "paired_non_protected_raw_inputs_missing",
                "blocked_until": "paired_non_protected_shooter_game_server_and_core_dump_input",
                "why": "the artifact root has a matching ShooterGameServer and a core-like input, but they are not paired under the same player-identity-offline run raw directory",
                "missing_input_path_patterns": [str(raw_binary_pattern), str(raw_core_pattern)],
                "next_required_artifact": {
                    "schema": CORE_DUMP_EVIDENCE_PACK_SCHEMA,
                    "path_pattern": str(core_manifest_pattern),
                },
            }
        if offline_status == "core_like_input_present_offline_binary_missing":
            return {
                **base,
                "code": "matching_offline_binary_missing",
                "blocked_until": "matching_non_protected_shooter_game_server_input",
                "why": "the artifact root has a core-like input, but no matching offline ShooterGameServer for this binary hash",
                "missing_input_path_pattern": str(raw_binary_pattern),
                "expected_shooter_game_server_sha256": EXPECTED_SHOOTERGAME_SHA256,
                "next_required_artifact": {
                    "schema": CORE_DUMP_EVIDENCE_PACK_SCHEMA,
                    "path_pattern": str(core_manifest_pattern),
                },
            }
        if offline_status == "offline_binary_present_hash_mismatch":
            return {
                **base,
                "code": "matching_offline_binary_hash_mismatch",
                "blocked_until": "matching_non_protected_shooter_game_server_input",
                "why": "ShooterGameServer candidates were found, but none match the current reviewed binary hash",
                "missing_input_path_pattern": str(raw_binary_pattern),
                "expected_shooter_game_server_sha256": EXPECTED_SHOOTERGAME_SHA256,
                "next_required_artifact": {
                    "schema": CORE_DUMP_EVIDENCE_PACK_SCHEMA,
                    "path_pattern": str(core_manifest_pattern),
                },
            }
        if offline_status == "offline_binary_and_core_like_inputs_present":
            return {
                **base,
                "code": "core_evidence_pack_not_built_or_not_accepted",
                "blocked_until": "complete_core_evidence_pack",
                "why": "binary and core-like files are present under the artifact root, but no complete core evidence pack is accepted",
                "next_required_artifact": {
                    "schema": CORE_DUMP_EVIDENCE_PACK_SCHEMA,
                    "path_pattern": str(core_manifest_pattern),
                },
                "exact_next_command": next_operator_recipe["build_core_evidence_pack"],
            }
        return {
            **base,
            "code": "offline_binary_and_core_input_missing",
            "blocked_until": "non_protected_offline_binary_and_core_inputs",
            "why": "no accepted reflection inventory exists and the artifact root does not yet contain enough offline inputs to package core evidence",
            "missing_input_path_patterns": [str(raw_binary_pattern), str(raw_core_pattern)],
            "expected_shooter_game_server_sha256": EXPECTED_SHOOTERGAME_SHA256,
            "next_required_artifact": {
                "schema": CORE_DUMP_EVIDENCE_PACK_SCHEMA,
                "path_pattern": str(core_manifest_pattern),
            },
        }

    if "fixture_coverage_incomplete" in downstream_blockers:
        return {
            **base,
            "code": "admin_focal_snapshots_pending",
            "blocked_until": "sanitized_server_list_players_and_server_kick_player_snapshots",
            "why": "the reflection inventory chain is accepted, but fixture coverage still lacks the two admin snapshots",
            "exact_next_command": next_operator_recipe["plan_admin_focal_snapshots"],
        }
    if "second_source_evidence_missing" in downstream_blockers or "second_source_evidence_not_accepted" in downstream_blockers:
        return {
            **base,
            "code": "distinct_second_source_evidence_missing_or_not_accepted",
            "blocked_until": "accepted_distinct_second_source_snapshot_comparison",
            "why": "first-source fixtures are present enough to continue, but second-source evidence is not accepted",
        }
    if "players_identity_first_evidence_consume_gate_blocked" in downstream_blockers:
        return {
            **base,
            "code": "players_identity_first_evidence_consume_gate_blocked",
            "blocked_until": "validate_offline_artifact_gate_consume_accepts_players_identity_first_evidence",
            "why": "the first-evidence builder emitted candidate JSON, but the offline artifact consume gate rejected it",
        }
    if "lifecycle_anchor_first_evidence_provenance_unbound" in downstream_blockers:
        return {
            **base,
            "code": "lifecycle_anchor_first_evidence_provenance_unbound",
            "blocked_until": "bound_lifecycle_anchor_and_principal_policy_sources",
            "why": "standalone lifecycle/principal planning artifacts must prove they come from the same first-evidence source artifacts before advancing to runtime evidence",
        }
    if "accepted_lifecycle_anchors_missing" in downstream_blockers:
        return {
            **base,
            "code": "accepted_lifecycle_anchor_evidence_missing",
            "blocked_until": "consume_only_lifecycle_anchor_candidate_artifact",
            "why": "identity first evidence still lacks accepted candidate start/end lifecycle anchors",
        }
    if "principal_invalidation_semantics_unresolved" in downstream_blockers:
        return {
            **base,
            "code": "principal_invalidation_semantics_unresolved",
            "blocked_until": "reviewed_fail_closed_principal_invalidation_policy",
            "why": "lifecycle anchor layout evidence is present, but public identity still lacks reviewed principal invalidation semantics",
        }
    if "identity_public_contract_gap_report_invalid" in downstream_blockers:
        return {
            **base,
            "code": "identity_public_contract_gap_report_invalid",
            "blocked_until": "blocked_identity_public_contract_gap_guardrail_restored",
            "why": "the offline public-contract gap guardrail must keep player identity blocked, private, and non-promotional before runtime evidence can route to contract review",
        }
    if "approved_runtime_evidence_missing" in downstream_blockers:
        return {
            **base,
            "code": "approved_runtime_evidence_missing",
            "blocked_until": "approved_runtime_principal_lifecycle_evidence",
            "why": "principal invalidation policy is consumable for planning, but public identity still lacks approved runtime evidence",
            "next_required_evidence": runtime_principal_lifecycle_evidence_requirements(),
        }
    if "identity_public_contract_gate_missing" in downstream_blockers:
        return {
            **base,
            "code": "identity_public_contract_gate_missing",
            "blocked_until": "reviewed_identity_public_contract",
            "why": "runtime evidence is accepted for the player-principal lane, but public identity still requires the reviewed public contract gate",
            "decision_manifest": "docs/player_identity_public_contract_decisions.json",
            "required_public_contract_gates": [
                "approved runtime evidence remains necessary but not sufficient",
                "copied opaque principal POD ABI reviewed",
                "named player identity capability reviewed",
                "owner-token registration and unregister lifecycle reviewed",
                "process-local non-persistent handle scope reviewed",
                "ABI layout tests passing",
                "installed SDK consumer tests passing",
                "public docs preserve lookup, persistence, permissions/admin, commands, mutation, return override, and cross-process non-claims",
            ],
        }
    return {
        **base,
        "code": "identity_public_contract_gate",
        "blocked_until": "reviewed_identity_public_contract",
        "why": "runtime evidence is accepted for the player-principal lane, but public identity still requires the reviewed public contract gate",
        "decision_manifest": "docs/player_identity_public_contract_decisions.json",
        "required_public_contract_gates": [
            "approved runtime evidence remains necessary but not sufficient",
            "copied opaque principal POD ABI reviewed",
            "named player identity capability reviewed",
            "owner-token registration and unregister lifecycle reviewed",
            "process-local non-persistent handle scope reviewed",
            "ABI layout tests passing",
            "installed SDK consumer tests passing",
            "public docs preserve lookup, persistence, permissions/admin, commands, mutation, return override, and cross-process non-claims",
        ],
    }


def build_operator_next_commands(
    *,
    inventory_ready: bool,
    offline_inputs: dict[str, Any],
    next_blocker: dict[str, Any],
    raw_binary_pattern: Path,
    raw_core_pattern: Path,
    core_manifest_pattern: Path,
    reflection_inventory_pattern: Path,
    next_operator_recipe: dict[str, Any],
) -> dict[str, Any]:
    """Compact machine-readable view of the operator recipe.

    This is derived from existing gates only. It does not decide readiness.
    """

    offline_status = offline_inputs.get("status")
    matching_binary_path = first_matching_binary_path(offline_inputs)
    unpaired_core_like_path = unambiguous_core_like_path(offline_inputs)
    artifact_root_pattern = raw_binary_pattern.parent.parent.parent
    core_like_candidates = offline_inputs.get("core_like_candidates")
    core_like_present = isinstance(core_like_candidates, list) and bool(core_like_candidates)
    omitted_core_like = offline_inputs.get("omitted_core_like_candidates")
    if isinstance(omitted_core_like, int) and omitted_core_like > 0:
        core_like_present = True

    missing_inputs: list[str] = []
    next_input_preparation_action = "none"
    if not inventory_ready:
        if offline_status in (
            "offline_binary_and_core_like_inputs_missing",
            "artifact_root_rejected",
            "artifact_root_missing",
            "artifact_root_not_directory",
        ):
            missing_inputs = [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ]
            next_input_preparation_action = "stage_matching_binary_and_core_under_same_player_identity_raw_dir"
        elif offline_status == "offline_binary_present_core_like_input_missing":
            missing_inputs = ["non_protected_core_dump_input"]
            next_input_preparation_action = "stage_core_next_to_matching_binary_under_same_player_identity_raw_dir"
        elif offline_status == "offline_binary_and_unpaired_core_like_inputs_present":
            missing_inputs = ["paired_non_protected_raw_binary_and_core"]
            next_input_preparation_action = "restage_binary_and_core_as_siblings_under_same_player_identity_raw_dir"
        elif offline_status in (
            "core_like_input_present_offline_binary_missing",
            "offline_binary_present_hash_mismatch",
        ):
            missing_inputs = ["matching_non_protected_shooter_game_server"]
            next_input_preparation_action = "stage_matching_binary_next_to_core_under_same_player_identity_raw_dir"

    ready_to_build_core = (
        not inventory_ready
        and offline_inputs.get("ready_to_build_core_evidence_pack") is True
    )
    ready_to_plan_admin = (
        inventory_ready
        and next_blocker.get("code") == "admin_focal_snapshots_pending"
    )
    staging_binary_arg = matching_binary_path or "<matching-non-protected-ShooterGameServer>"
    staging_core_arg = unpaired_core_like_path or "<non-protected-core-dump-input>"
    staged_run_root = artifact_root_pattern / f"{PLAYER_IDENTITY_RAW_RUN_PREFIX}<run-id-suffix>"
    staging_command_argv = [
        "python3",
        RAW_LAYOUT_HELPER,
        "--binary",
        staging_binary_arg,
        "--core",
        staging_core_arg,
        "--artifact-root",
        str(artifact_root_pattern),
        "--run-id",
        "<run-id-suffix>",
        "--mode",
        "hardlink",
    ]
    staging_command = "PYTHONDONTWRITEBYTECODE=1 " + shlex.join(staging_command_argv)
    validation_command_argv = [
        "python3",
        RAW_INPUT_VALIDATOR,
        "--root",
        str(staged_run_root),
    ]
    validation_command = "PYTHONDONTWRITEBYTECODE=1 " + shlex.join(validation_command_argv)
    if inventory_ready or ready_to_build_core:
        staging_status = "satisfied"
        staging_blocked_until = None
    elif (
        matching_binary_path is not None
        and unpaired_core_like_path is not None
        and offline_status == "offline_binary_and_unpaired_core_like_inputs_present"
    ):
        staging_status = "ready"
        staging_blocked_until = None
    elif matching_binary_path is not None and offline_status == "offline_binary_present_core_like_input_missing":
        staging_status = "blocked"
        staging_blocked_until = "non_protected_core_dump_input"
    else:
        staging_status = "blocked"
        staging_blocked_until = next_blocker.get("blocked_until")

    def command_step(
        *,
        step_id: str,
        command: str,
        ready: bool,
        blocked_until: str | None,
        produces_schema: str | None = None,
        produces_path_pattern: Path | None = None,
        requires: list[str] | None = None,
    ) -> dict[str, Any]:
        if ready:
            status = "ready"
        elif blocked_until is None:
            status = "satisfied"
        else:
            status = "blocked"
        step: dict[str, Any] = {
            "id": step_id,
            "status": status,
            "ready": ready,
            "blocked_until": blocked_until,
            "requires": requires or [],
            "command": command,
        }
        if produces_schema and produces_path_pattern:
            step["produces"] = {
                "schema": produces_schema,
                "path_pattern": str(produces_path_pattern),
            }
        return step

    sequence = [
        command_step(
            step_id="build_core_evidence_pack",
            ready=ready_to_build_core,
            blocked_until=None if ready_to_build_core or inventory_ready else next_blocker.get("blocked_until"),
            requires=[
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
            produces_schema=CORE_DUMP_EVIDENCE_PACK_SCHEMA,
            produces_path_pattern=core_manifest_pattern,
            command=next_operator_recipe["build_core_evidence_pack"],
        ),
        command_step(
            step_id="build_reflection_inventory_pack",
            ready=False,
            blocked_until=None if inventory_ready else "complete_core_evidence_pack",
            requires=["complete_core_evidence_pack"],
            produces_schema=REFLECTION_INVENTORY_PACK_SCHEMA,
            produces_path_pattern=reflection_inventory_pattern,
            command=next_operator_recipe["build_reflection_inventory_pack"],
        ),
        command_step(
            step_id="check_reflection_inventory_pack",
            ready=False,
            blocked_until=None if inventory_ready else "reflection_inventory_pack_built",
            requires=["reflection_inventory_pack_built"],
            command=next_operator_recipe["check_reflection_inventory_pack"],
        ),
        command_step(
            step_id="plan_admin_focal_snapshots",
            ready=ready_to_plan_admin,
            blocked_until=None if ready_to_plan_admin else (
                None if inventory_ready else "accepted_reflection_inventory_pack"
            ),
            requires=[
                "accepted_reflection_inventory_pack",
                "ShooterPlayerController.ServerListPlayers",
                "ShooterPlayerController.ServerKickPlayer",
            ],
            command=next_operator_recipe["plan_admin_focal_snapshots"],
        ),
    ]

    return {
        "current_blocker": next_blocker.get("code"),
        "blocked_until": next_blocker.get("blocked_until"),
        "runnable_now": [step["id"] for step in sequence if step["ready"] is True],
        "missing_inputs": missing_inputs,
        "inputs": {
            "matching_non_protected_shooter_game_server": {
                "path_pattern": str(raw_binary_pattern),
                "present": matching_binary_path is not None,
                "accepted_sha256": EXPECTED_SHOOTERGAME_SHA256,
                "matched_path": matching_binary_path,
            },
            "non_protected_core_dump_input": {
                "path_pattern": str(raw_core_pattern),
                "present": core_like_present,
            },
        },
        "input_layout_requirements": {
            "accepted_raw_directory_pattern": str(raw_binary_pattern.parent),
            "binary_filename": raw_binary_pattern.name,
            "core_filename": raw_core_pattern.name,
            "run_directory_prefix": PLAYER_IDENTITY_RAW_RUN_PREFIX,
            "pairing_rule": "ShooterGameServer and core must be regular, non-symlink sibling files under the same raw directory",
            "staging_rule": "copy or hardlink offline inputs into the accepted raw directory before building the core evidence pack",
            "protected_paths_rejected": ["/servidor/ark"],
            "next_input_preparation_action": next_input_preparation_action,
            "non_claims": [
                "layout readiness does not validate core contents",
                "presence of core-like files outside the paired raw directory is not enough",
            ],
        },
        "blocked_input_resolution": {
            "status": (
                "satisfied"
                if not missing_inputs
                else "ready_to_stage"
                if staging_status == "ready"
                else "blocked"
            ),
            "current_blocker": next_blocker.get("code"),
            "next_input_preparation_action": next_input_preparation_action,
            "missing_inputs": missing_inputs,
            "available_matching_binary": matching_binary_path,
            "expected_core_destination": str(raw_core_pattern),
            "expected_raw_directory": str(raw_binary_pattern.parent),
            "core_input_requirements": [
                "explicit non-protected core dump input",
                "regular file, not a symlink",
                "stage as raw/core beside the matching ShooterGameServer before building the core evidence pack",
                "must not be read from or symlink-resolve into /servidor/ark",
            ],
            "validation_command_after_missing_inputs_exist": validation_command,
            "validation_command_argv": validation_command_argv,
            "staging_command_after_missing_inputs_exist": staging_command,
            "staging_command_argv": staging_command_argv,
            "non_claims": [
                "this field is operator guidance only and does not make blocked commands runnable",
                "raw input validation checks path/layout/hash metadata only; it does not accept or promote core evidence",
            ],
        },
        "input_staging": {
            "id": "stage_offline_raw_layout",
            "status": staging_status,
            "ready": staging_status == "ready",
            "blocked_until": staging_blocked_until,
            "explicit_source_inputs_required": [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
            "requires": [
                "matching_non_protected_shooter_game_server",
                "non_protected_core_dump_input",
            ],
            "command": staging_command,
            "command_argv": staging_command_argv,
            "helper": RAW_LAYOUT_HELPER,
            "non_claims": [
                "helper stages existing offline binary and core files only",
                "helper does not create, validate, approve, or promote core dumps",
                "helper does not build or approve core evidence packs",
            ],
        },
        "paired_raw_inputs": (
            offline_inputs.get("paired_raw_inputs")
            if isinstance(offline_inputs.get("paired_raw_inputs"), list)
            else []
        ),
        "ready_to_build_core_evidence_pack": ready_to_build_core,
        "sequence": sequence,
        "non_claims": [
            "derived recipe only; does not execute commands, read cores, write artifacts, or touch servers",
            "ready=true means the command is directly runnable under the current report; ready=false is blocked or already satisfied",
        ],
    }


def compact_count(value: Any) -> int | None:
    return value if type(value) is int else None


def build_progress_signal(
    *,
    status: str,
    ready: bool,
    inventory_ready: bool,
    coverage_targets: Any,
    coverage_comparable: Any,
    coverage_blocked: Any,
    second_source_missing: int | None,
    second_source_inconclusive: int | None,
    second_source_rejected: int | None,
    missing_targets: list[str],
    lifecycle_diagnosis: dict[str, Any],
    next_blocker: dict[str, Any],
    operator_next_commands: dict[str, Any],
    layout_lifecycle_state: dict[str, Any],
) -> dict[str, Any]:
    """Small operator-facing summary derived from the report's existing gates."""

    target_count = compact_count(coverage_targets)
    comparable_count = compact_count(coverage_comparable)
    blocked_count = compact_count(coverage_blocked)
    if target_count is not None and comparable_count is not None:
        fixture_targets = f"{comparable_count}/{target_count}"
    else:
        fixture_targets = "unknown"

    accepted_start_targets = string_list(lifecycle_diagnosis.get("accepted_start_targets"))
    accepted_end_targets = string_list(lifecycle_diagnosis.get("accepted_end_targets"))
    missing_inputs = string_list(operator_next_commands.get("missing_inputs"))
    primary_blocker = next_blocker.get("code") if isinstance(next_blocker.get("code"), str) else "unknown"

    return {
        "status": status,
        "ready": ready,
        "primary_blocker": primary_blocker,
        "statement": layout_lifecycle_state.get("statement"),
        "coverage": {
            "target_set": PLAYER_IDENTITY_TARGET_SET,
            "reflection_inventory_accepted": inventory_ready,
            "fixture_targets": fixture_targets,
            "fixture_blocked_targets": blocked_count,
            "second_source": {
                "missing": second_source_missing,
                "inconclusive": second_source_inconclusive,
                "rejected": second_source_rejected,
            },
        },
        "layout_lifecycle_state": {
            "status": layout_lifecycle_state.get("status"),
            "second_source_layout_accepted": layout_lifecycle_state.get("second_source_layout_accepted"),
            "lifecycle_invalidation_remains": layout_lifecycle_state.get("lifecycle_invalidation_remains"),
            "remaining_work": layout_lifecycle_state.get("remaining_work"),
        },
        "missing": {
            "required_targets": missing_targets,
            "operator_inputs": missing_inputs,
        },
        "accepted_anchors": {
            "session_start": lifecycle_diagnosis.get("session_start_accepted") is True,
            "session_end": lifecycle_diagnosis.get("session_end_accepted") is True,
            "start_targets": accepted_start_targets,
            "end_targets": accepted_end_targets,
        },
        "non_claims": [
            "compact status only; does not promote reflection inventory, lifecycle identity, runtime hooks, public SDK, lookup, ResourceHandle, mutation, or return override",
        ],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_fallbacks = approved_workspace_input_fallbacks(args)
    effective_candidate_root = input_fallbacks["candidate_root"]
    effective_lifecycle_anchor_candidates_manifest = input_fallbacks["lifecycle_anchor_candidates_manifest"]
    effective_principal_invalidation_policy_manifest = input_fallbacks["principal_invalidation_policy_manifest"]
    requested_artifact_root = args.artifact_root
    effective_artifact_root = requested_artifact_root
    inventory_result, inventory_payload, artifact_root_rejection = scan_reflection_inventory_root(requested_artifact_root)
    artifact_root_fallback: dict[str, Any] = {
        "used": False,
        "root": None,
        "reason": None,
        "primary_root": str(requested_artifact_root),
        "primary_diagnosis": artifact_root_diagnosis(inventory_payload),
    }
    if (
        artifact_root_rejection is None
        and requested_artifact_root == DEFAULT_ARTIFACT_ROOT
        and root_has_no_identity_inventory_candidate(inventory_payload)
    ):
        fallback_result, fallback_payload, fallback_rejection = scan_reflection_inventory_root(APPROVED_WORKSPACE_FALLBACK_ROOT)
        if (
            fallback_rejection is None
            and isinstance(fallback_payload, dict)
            and fallback_payload.get("ready") is True
            and isinstance(fallback_payload.get("accepted_pack"), dict)
        ):
            effective_artifact_root = APPROVED_WORKSPACE_FALLBACK_ROOT
            inventory_result = fallback_result
            inventory_payload = fallback_payload
            artifact_root_fallback = {
                **artifact_root_fallback,
                "used": True,
                "root": str(APPROVED_WORKSPACE_FALLBACK_ROOT),
                "reason": "default_root_had_no_reflection_inventory_pack",
                "fallback_diagnosis": artifact_root_diagnosis(fallback_payload),
            }
        else:
            artifact_root_fallback = {
                **artifact_root_fallback,
                "attempted": True,
                "root": str(APPROVED_WORKSPACE_FALLBACK_ROOT),
                "reason": "default_root_had_no_reflection_inventory_pack",
                "fallback_rejected": fallback_rejection,
                "fallback_diagnosis": artifact_root_diagnosis(fallback_payload),
            }
    coverage_command = [
        str(SCRIPT_DIR / "compare_reflection_snapshots.py"),
        "--base-root",
        str(args.snapshot_root),
        "--target-set",
        PLAYER_IDENTITY_TARGET_SET,
        "--readiness-report",
        "--json",
    ]
    if effective_candidate_root:
        coverage_command.extend(["--candidate-root", str(effective_candidate_root)])
    coverage_result, coverage_payload = run_json_command(coverage_command)
    first_evidence_result, first_evidence_payload = run_json_command(
        [
            str(SCRIPT_DIR / "build_redacted_ufunction_signatures.py"),
            "--snapshot-root",
            str(args.snapshot_root),
            "--players-identity-first-evidence",
            "--json",
        ]
    )
    orientation_result, orientation_payload = run_json_command(
        [
            str(SCRIPT_DIR / "check_player_identity_static_orientation.py"),
            "--json",
        ]
    )

    inventory_chain = reflection_inventory_chain_diagnosis(inventory_payload)
    inventory_payload_ready = bool(inventory_payload and inventory_payload.get("ready") is True)
    inventory_ready = inventory_chain["ready"] is True
    orientation_valid = (
        isinstance(orientation_payload, dict)
        and orientation_payload.get("valid") is True
        and orientation_payload.get("accepted_for_orientation") is True
    )
    coverage_totals = coverage_payload.get("totals", {}) if isinstance(coverage_payload, dict) else {}
    coverage_targets = coverage_totals.get("targets")
    coverage_comparable = coverage_totals.get("comparable")
    coverage_blocked = coverage_totals.get("blocked")
    second_source_accepted = second_source_total(coverage_payload, "second_source_accepted")
    second_source_missing = second_source_missing_count(coverage_payload)
    second_source_inconclusive = second_source_total(coverage_payload, "second_source_inconclusive")
    second_source_rejected = second_source_total(coverage_payload, "second_source_rejected")
    coverage_payload_valid = coverage_payload_has_required_totals(coverage_payload)
    first_evidence_payload_valid = (
        isinstance(first_evidence_payload, dict)
        and first_evidence_payload.get("schema") == FIRST_EVIDENCE_SCHEMA
    )
    first_evidence_ready = first_evidence_result.returncode == 0 and first_evidence_payload_valid
    missing_targets = parse_missing_required_targets(first_evidence_result.stderr)
    first_evidence_consume_gate = first_evidence_consume_gate_diagnosis(first_evidence_payload)
    first_evidence_lifecycle_diagnosis = lifecycle_anchor_diagnosis(first_evidence_payload)
    lifecycle_candidate_diagnosis = lifecycle_anchor_candidate_manifest_diagnosis(
        effective_lifecycle_anchor_candidates_manifest
    )
    lifecycle_diagnosis = merge_lifecycle_diagnosis(
        first_evidence_lifecycle_diagnosis,
        lifecycle_candidate_diagnosis,
    )
    principal_policy_diagnosis = principal_invalidation_policy_diagnosis(
        effective_principal_invalidation_policy_manifest
    )
    runtime_evidence_manifest_diagnosis = runtime_principal_lifecycle_evidence_manifest_diagnosis(
        getattr(args, "runtime_principal_lifecycle_evidence_manifest", None)
    )
    approved_runtime_evidence_manifest_diagnosis = approved_runtime_principal_lifecycle_evidence_manifest_diagnosis(
        getattr(args, "approved_runtime_principal_lifecycle_evidence_manifest", None)
    )
    window_request_diagnosis = player_principal_lifecycle_window_request_diagnosis(
        getattr(args, "player_principal_lifecycle_window_request", None),
        getattr(args, "player_principal_lifecycle_window_env", None),
    )
    public_contract_gap_diagnosis = player_identity_public_contract_gap_diagnosis(
        decisions=getattr(
            args,
            "player_identity_public_contract_decisions",
            REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json",
        ),
        surfaces=getattr(args, "public_sdk_surfaces", REPO_ROOT / "docs" / "public_sdk_surfaces.json"),
        private_candidate_contract=getattr(
            args,
            "player_identity_private_candidate_contract",
            REPO_ROOT / "docs" / "research" / "2026-06-01-player-identity-private-candidate-contract.json",
        ),
        identifier_redaction_evidence=getattr(
            args,
            "player_identity_identifier_redaction_evidence",
            REPO_ROOT / "docs" / "research" / "2026-06-02-player-identity-identifier-redaction-evidence.json",
        ),
        principal_invalidation_policy_manifest=effective_principal_invalidation_policy_manifest,
        public_header=getattr(args, "public_header", REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"),
    )
    approved_runtime_evidence_ready = approved_runtime_evidence_manifest_diagnosis.get("runtime_evidence_ready") is True
    runtime_evidence_requirements = runtime_principal_lifecycle_evidence_requirements()
    planning_provenance = planning_provenance_blockers(
        first_evidence_payload=first_evidence_payload,
        lifecycle_candidate_diagnosis=lifecycle_candidate_diagnosis,
        principal_policy_diagnosis=principal_policy_diagnosis,
    )
    planning_provenance_action = planning_provenance_next_action(
        blockers=planning_provenance,
        lifecycle_anchor_candidates_manifest=effective_lifecycle_anchor_candidates_manifest,
        principal_invalidation_policy_manifest=effective_principal_invalidation_policy_manifest,
    )
    lifecycle_ready = (
        lifecycle_diagnosis["session_start_accepted"] is True
        and lifecycle_diagnosis["session_end_accepted"] is True
        and not planning_provenance
    )
    principal_policy_ready = principal_policy_diagnosis.get("policy_consume_ready") is True
    principal_invalidation_ready = (
        lifecycle_diagnosis.get("principal_invalidation_ready") is True
        or (principal_policy_ready and not planning_provenance)
    )
    layout_accepted = second_source_layout_accepted(
        coverage_payload_valid=coverage_payload_valid,
        coverage_targets=coverage_targets,
        coverage_comparable=coverage_comparable,
        coverage_blocked=coverage_blocked,
        second_source_accepted=second_source_accepted,
        second_source_missing=second_source_missing,
        second_source_inconclusive=second_source_inconclusive,
        second_source_rejected=second_source_rejected,
    )
    layout_lifecycle_state = build_layout_lifecycle_state(
        layout_accepted=layout_accepted,
        second_source_accepted=second_source_accepted,
        second_source_missing=second_source_missing,
        second_source_inconclusive=second_source_inconclusive,
        second_source_rejected=second_source_rejected,
        lifecycle_ready=lifecycle_ready,
        principal_invalidation_ready=principal_invalidation_ready,
        lifecycle_diagnosis=lifecycle_diagnosis,
    )
    offline_inputs = bounded_artifact_file_scan(effective_artifact_root)

    downstream_blockers: list[str] = []
    if not inventory_ready:
        blockers = ["missing_reflection_inventory_pack_or_core_evidence_pack"]
        if inventory_payload_ready:
            blockers.append("accepted_reflection_inventory_chain_incomplete")
    else:
        blockers = []
    if coverage_result.returncode != 0 or not coverage_payload_valid or coverage_blocked:
        downstream_blockers.append("fixture_coverage_incomplete")
    if second_source_missing:
        downstream_blockers.append("second_source_evidence_missing")
    if second_source_inconclusive or second_source_rejected:
        downstream_blockers.append("second_source_evidence_not_accepted")
    if not first_evidence_ready:
        downstream_blockers.append("players_identity_first_evidence_not_buildable")
    elif (
        first_evidence_consume_gate.get("evaluated") is True
        and first_evidence_consume_gate.get("ready") is not True
    ):
        downstream_blockers.append("players_identity_first_evidence_consume_gate_blocked")
    if planning_provenance:
        downstream_blockers.append("lifecycle_anchor_first_evidence_provenance_unbound")
    if not lifecycle_ready:
        downstream_blockers.append("accepted_lifecycle_anchors_missing")
    if lifecycle_ready and not principal_invalidation_ready:
        downstream_blockers.append("principal_invalidation_semantics_unresolved")
    if lifecycle_ready and principal_invalidation_ready and not approved_runtime_evidence_ready:
        downstream_blockers.append("approved_runtime_evidence_missing")
    if lifecycle_ready and principal_invalidation_ready and approved_runtime_evidence_ready:
        downstream_blockers.append("identity_public_contract_gate_missing")
    if not public_contract_gap_diagnosis.get("ready"):
        downstream_blockers.append("identity_public_contract_gap_report_invalid")
    if inventory_ready:
        blockers.extend(downstream_blockers)

    next_step = (
        "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack"
        if not inventory_ready
        else "plan_missing_server_list_players_and_server_kick_player_snapshots"
    )
    if inventory_ready:
        if first_evidence_ready and not layout_accepted and not lifecycle_ready:
            next_step = "produce_distinct_second_source_and_accepted_lifecycle_anchor_evidence"
        elif first_evidence_ready and not layout_accepted:
            next_step = "produce_distinct_second_source_layout_evidence"
        elif first_evidence_ready and not lifecycle_ready:
            next_step = "produce_accepted_lifecycle_anchor_and_principal_invalidation_evidence"
        elif first_evidence_ready and not principal_invalidation_ready:
            next_step = "produce_reviewed_principal_invalidation_semantics"
        elif first_evidence_ready and not approved_runtime_evidence_ready:
            next_step = "produce_approved_runtime_principal_lifecycle_evidence"
        elif first_evidence_ready:
            next_step = "prepare_identity_public_contract_review"

    recipe_root_raw = offline_inputs.get("resolved_root")
    if isinstance(recipe_root_raw, str) and offline_inputs.get("status") != "artifact_root_rejected":
        recipe_root = Path(recipe_root_raw)
    elif artifact_root_rejection is None:
        recipe_root = effective_artifact_root
    else:
        recipe_root = Path("<non-protected-artifact-root>")
    core_manifest_pattern = recipe_root / CORE_EVIDENCE_MANIFEST_PATTERN
    reflection_inventory_pattern = recipe_root / REFLECTION_INVENTORY_MANIFEST_PATTERN
    raw_binary_pattern = recipe_root / "player-identity-offline-<run-id>" / "raw" / "ShooterGameServer"
    raw_core_pattern = recipe_root / "player-identity-offline-<run-id>" / "raw" / "core"
    obelisk_commit = detect_obelisk_commit()
    next_operator_recipe = {
        "blocked_until": "accepted_reflection_inventory_pack",
        "obelisk_commit": obelisk_commit,
        "obelisk_commit_source": "OBELISK_COMMIT environment variable if set; otherwise unknown; this checker does not invoke Git",
        "build_core_evidence_pack": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_core_dump_evidence_pack.py "
            f"--binary {raw_binary_pattern} "
            f"--core {raw_core_pattern} "
            f"--output-dir {core_manifest_pattern.parent} "
            f"--obelisk-commit {obelisk_commit} "
            "--no-default-candidates "
            "--no-default-fname-roots "
            "--no-default-fname-indices "
            "--fname-root-slot verified_fname_root_slot=0x5956f30 "
            "--fname-index None=0 "
            "--fname-index ClientMessage=4884 "
            "--fname-index ServerChat=9619 "
            "--fname-index SetActiveMissionDebugFlags=9622 "
            "--gobjects-candidate gobjects=0x595b7e0 "
            "--gobjects-sample-index 0 "
            "--gobjects-sample-index 1 "
            "--gobjects-sample-index 25447"
        ),
        "build_reflection_inventory_pack": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_reflection_inventory_pack.py "
            f"--evidence-pack-manifest {core_manifest_pattern} "
            f"--ark-binary-sha256 {EXPECTED_SHOOTERGAME_SHA256} "
            "--evidence-pack-fname-root-label verified_fname_root_slot "
            "--evidence-pack-gobjects-label gobjects "
            f"--target-set {PLAYER_IDENTITY_TARGET_SET} "
            f"--include-functions --output-dir {reflection_inventory_pattern.parent}"
        ),
        "check_reflection_inventory_pack": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_reflection_inventory_pack_readiness.py "
            f"--root {reflection_inventory_pattern.parent}"
        ),
        "plan_admin_focal_snapshots": (
            "PYTHONDONTWRITEBYTECODE=1 python3 scripts/plan_ufunction_focal_snapshots.py "
            f"--inventory-pack {reflection_inventory_pattern} "
            "--target ShooterPlayerController.ServerListPlayers "
            "--target ShooterPlayerController.ServerKickPlayer "
            "--evidence-obelisk-commit <evidence-pack-obelisk-commit> "
            "--json-out <ignored-output-path>/player-identity-admin-focal-plan.json"
        ),
        "forbidden_next_commands": [
            "do not read from or write to /servidor/ark for this preflight recipe",
            "do not use --target-set players-identity-lifecycle-intake with plan_ufunction_focal_snapshots.py",
            "do not use direct --core mode for players-identity-lifecycle-intake",
            "do not use --skip-core-sha256 or --allow-partial-gdb for player identity evidence packs",
        ],
        "non_claims": [
            "recipe only; this report does not execute commands, read cores, write artifacts, or touch servers",
            "planned admin focal snapshots remain candidate-only and do not promote public identity, permissions, commands, runtime hooks, mutation, lookup, return override, or SDK surface",
        ],
    }
    next_blocker = next_actionable_blocker(
        inventory_ready=inventory_ready,
        inventory_payload_ready=inventory_payload_ready,
        inventory_chain=inventory_chain,
        downstream_blockers=downstream_blockers,
        offline_inputs=offline_inputs,
        raw_binary_pattern=raw_binary_pattern,
        raw_core_pattern=raw_core_pattern,
        core_manifest_pattern=core_manifest_pattern,
        reflection_inventory_pattern=reflection_inventory_pattern,
        next_operator_recipe=next_operator_recipe,
    )
    operator_next_commands = build_operator_next_commands(
        inventory_ready=inventory_ready,
        offline_inputs=offline_inputs,
        next_blocker=next_blocker,
        raw_binary_pattern=raw_binary_pattern,
        raw_core_pattern=raw_core_pattern,
        core_manifest_pattern=core_manifest_pattern,
        reflection_inventory_pattern=reflection_inventory_pattern,
        next_operator_recipe=next_operator_recipe,
    )
    status = "candidate_ready" if not blockers else "blocked"
    ready = not blockers
    progress_signal = build_progress_signal(
        status=status,
        ready=ready,
        inventory_ready=inventory_ready,
        coverage_targets=coverage_targets,
        coverage_comparable=coverage_comparable,
        coverage_blocked=coverage_blocked,
        second_source_missing=second_source_missing,
        second_source_inconclusive=second_source_inconclusive,
        second_source_rejected=second_source_rejected,
        missing_targets=missing_targets,
        lifecycle_diagnosis=lifecycle_diagnosis,
        next_blocker=next_blocker,
        operator_next_commands=operator_next_commands,
        layout_lifecycle_state=layout_lifecycle_state,
    )

    return {
        "schema": REPORT_SCHEMA,
        "status": status,
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "not_artifact_gate": True,
        "promotion_ready": False,
        "artifact_root": str(requested_artifact_root),
        "effective_artifact_root": str(effective_artifact_root),
        "artifact_root_fallback": artifact_root_fallback,
        "input_fallbacks": {
            "used": input_fallbacks["used"],
            "non_claims": input_fallbacks["non_claims"],
        },
        "snapshot_root": str(args.snapshot_root),
        "candidate_root": str(effective_candidate_root) if effective_candidate_root else None,
        "lifecycle_anchor_candidates_manifest": (
            str(effective_lifecycle_anchor_candidates_manifest)
            if effective_lifecycle_anchor_candidates_manifest
            else None
        ),
        "principal_invalidation_policy_manifest": (
            str(effective_principal_invalidation_policy_manifest)
            if effective_principal_invalidation_policy_manifest
            else None
        ),
        "runtime_principal_lifecycle_evidence_manifest": (
            str(getattr(args, "runtime_principal_lifecycle_evidence_manifest", None))
            if getattr(args, "runtime_principal_lifecycle_evidence_manifest", None)
            else None
        ),
        "approved_runtime_principal_lifecycle_evidence_manifest": (
            str(getattr(args, "approved_runtime_principal_lifecycle_evidence_manifest", None))
            if getattr(args, "approved_runtime_principal_lifecycle_evidence_manifest", None)
            else None
        ),
        "player_principal_lifecycle_window_request": (
            str(getattr(args, "player_principal_lifecycle_window_request", None))
            if getattr(args, "player_principal_lifecycle_window_request", None)
            else None
        ),
        "player_principal_lifecycle_window_env": (
            str(getattr(args, "player_principal_lifecycle_window_env", None))
            if getattr(args, "player_principal_lifecycle_window_env", None)
            else None
        ),
        "target_set": PLAYER_IDENTITY_TARGET_SET,
        "blockers": blockers,
        "deferred_until_reflection_inventory_ready": [] if inventory_ready else downstream_blockers,
        "primary_blocker": next_blocker.get("code"),
        "readiness_statement": layout_lifecycle_state["statement"],
        "layout_lifecycle_state": layout_lifecycle_state,
        "progress_signal": progress_signal,
        "next_required_artifacts": [] if inventory_ready else [
            {
                "schema": "obelisk.core-dump-evidence-pack.v1",
                "path_pattern": str(core_manifest_pattern),
                "purpose": "non_protected_complete_core_evidence",
            },
            {
                "schema": "obelisk.reflection-inventory-pack.v1",
                "path_pattern": str(reflection_inventory_pattern),
                "purpose": "reviewed_target_inventory_for_player_identity_lifecycle_intake",
            },
        ],
        "next_actionable_blocker": next_blocker,
        "operator_next_commands": operator_next_commands,
        "next_operator_recipe": next_operator_recipe,
        "artifact_chain": {
            "core_evidence_pack_required": True,
            "reflection_inventory_pack_required": True,
            "core_evidence_pack_manifest_required": True,
            "accepted_reflection_inventory_pack": artifact_root_diagnosis(inventory_payload)["accepted_manifest"],
            "accepted_reflection_inventory_chain": inventory_chain,
            "required_admin_targets": REQUIRED_ADMIN_TARGETS,
            "blocked_before_focal_planning": not inventory_ready,
            "ready_to_plan_admin_snapshots": inventory_ready,
            "offline_inputs": offline_inputs,
        },
        "static_orientation": {
            "returncode": orientation_result.returncode,
            "valid": (
                orientation_payload.get("valid")
                if isinstance(orientation_payload, dict)
                else False
            ),
            "accepted_for_orientation": (
                orientation_payload.get("accepted_for_orientation")
                if isinstance(orientation_payload, dict)
                else False
            ),
            "not_artifact_gate": (
                orientation_payload.get("not_artifact_gate")
                if isinstance(orientation_payload, dict)
                else True
            ),
            "pre_core_evidence_boundary": {
                "useful": orientation_valid,
                "status": (
                    "useful_orientation_blocked_before_core_evidence"
                    if not inventory_ready
                    else "orientation_only_not_downstream_promotion_gate"
                ),
                "blocked": not inventory_ready,
                "blockers": [] if inventory_ready else [
                    "requires_non_protected_core_evidence_pack",
                    "requires_accepted_reflection_inventory_pack_before_admin_focal_planning",
                ],
                "useful_for": [
                    "static_lifecycle_admin_orientation",
                    "future_focal_snapshot_matching_after_inventory_acceptance",
                ],
                "non_claims": [
                    "static orientation does not replace core evidence, reflection inventory, focal snapshots, second-source evidence, or lifecycle anchors",
                    "static orientation does not promote public identity, permissions, commands, runtime hooks, lookup, ResourceHandle, mutation, return override, or SDK surface",
                ],
            },
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": (
                orientation_payload.get("blockers")
                if isinstance(orientation_payload, dict)
                else [{"reason": "static_orientation_check_output_missing_or_malformed"}]
            ),
            "non_claims": (
                orientation_payload.get("non_claims")
                if isinstance(orientation_payload, dict)
                else ["static orientation is candidate-only navigation evidence"]
            ),
        },
        "public_sdk_ready": False,
        "runtime_ready": False,
        "reflection_inventory": {
            "returncode": inventory_result.returncode,
            "ready": inventory_ready,
            "status": inventory_payload.get("status") if inventory_payload else None,
            "manifests_scanned": inventory_payload.get("manifests_scanned") if inventory_payload else None,
            "reason_codes": [
                reason.get("reason")
                for reason in (inventory_payload.get("reasons", []) if inventory_payload else [])
                if isinstance(reason, dict)
            ],
            "chain_validation": inventory_chain,
            "artifact_root_diagnosis": artifact_root_diagnosis(inventory_payload),
        },
        "fixture_coverage": {
            "returncode": coverage_result.returncode,
            "targets": coverage_targets,
            "comparable": coverage_comparable,
            "blocked": coverage_blocked,
            "promotion_ready": (
                coverage_payload.get("promotion_gate", {}).get("promotion_ready")
                if isinstance(coverage_payload, dict)
                else None
            ),
            "second_source_status": coverage_payload.get("second_source_status") if coverage_payload else None,
            "second_source_accepted": second_source_accepted,
            "second_source_missing": second_source_missing,
            "second_source_inconclusive": second_source_inconclusive,
            "second_source_rejected": second_source_rejected,
            "second_source_layout_accepted": layout_accepted,
        },
        "first_evidence": {
            "returncode": first_evidence_result.returncode,
            "ready": first_evidence_ready,
            "schema": first_evidence_payload.get("schema") if first_evidence_payload else None,
            "consume_gate": first_evidence_consume_gate,
            "missing_required_targets": missing_targets,
            "lifecycle_anchors": lifecycle_diagnosis,
            "generated_lifecycle_anchors": first_evidence_lifecycle_diagnosis,
            "lifecycle_anchor_candidates": lifecycle_candidate_diagnosis,
            "principal_invalidation_policy": principal_policy_diagnosis,
            "planning_provenance": {
                "ready": not planning_provenance,
                "blockers": planning_provenance,
                "next_action": planning_provenance_action,
                "non_claim": (
                    "aggregate provenance binding only; does not promote runtime evidence, "
                    "public identity, permissions/admin, commands, SDK readiness, or v1 completion"
                ),
            },
            "runtime_principal_lifecycle_evidence": runtime_evidence_requirements,
            "runtime_principal_lifecycle_evidence_manifest": runtime_evidence_manifest_diagnosis,
            "approved_runtime_principal_lifecycle_evidence_manifest": approved_runtime_evidence_manifest_diagnosis,
            "player_principal_lifecycle_window_request": window_request_diagnosis,
            "public_contract_gap_report": public_contract_gap_diagnosis,
            "stderr": first_evidence_result.stderr.strip(),
        },
        "next_step": next_step,
        "non_claims": [
            "read-only preflight; does not touch servers, execute scanners, write artifacts, or promote public SDK",
            "success here would be candidate-only planning evidence, not public identity, permissions, commands, runtime hooks, mutation, return override, lookup, or ResourceHandle",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
