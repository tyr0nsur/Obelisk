#!/usr/bin/env python3
"""Combined preflight for the player-identity first-evidence lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

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
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
STATIC_ORIENTATION_SCHEMA_PREFIX = "obelisk.player-identity-static-"
STATIC_ORIENTATION_MANIFEST_TOKENS = (
    "radare2-static-orientation",
    "static-orientation",
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
        default=Path("/home/flowcommunity-ark/obelisk-artifacts"),
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
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short=12", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def reject_player_identity_artifact_root(path: Path, label: str) -> Path:
    """Reject every /servidor/ark root for this preflight, including workspace-offline."""

    reject_symlink_component(path, label)
    expanded = path.expanduser()
    absolute = expanded if expanded.is_absolute() else expanded.absolute()
    protected = PROTECTED_SERVER_ROOT
    resolved_protected = protected.resolve()
    if is_relative_to(absolute, protected):
        raise SystemExit(f"{label} must not read from protected server root {protected}: {absolute}")
    resolved = reject_protected_input_path(path, label)
    if is_relative_to(resolved, resolved_protected):
        raise SystemExit(f"{label} must not read from protected server root {protected}: {resolved}")
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
            "does not read /servidor/ark, attach to processes, execute scanners, or validate runtime state",
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
    if "accepted_lifecycle_anchors_missing" in downstream_blockers:
        return {
            **base,
            "code": "accepted_lifecycle_anchor_evidence_missing",
            "blocked_until": "consume_only_lifecycle_anchor_candidate_artifact",
            "why": "identity first evidence still lacks accepted candidate start/end lifecycle anchors",
        }
    return {
        **base,
        "code": "validate_first_evidence_consume_promote_blocked",
        "blocked_until": "consume_accepted_promote_blocked_first_evidence_artifact",
        "why": "candidate evidence is ready enough for internal planning only; validate it as consume-only and promote-blocked",
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
    staging_command = (
        f"PYTHONDONTWRITEBYTECODE=1 python3 {RAW_LAYOUT_HELPER} "
        f"--binary {staging_binary_arg} "
        "--core <non-protected-core-dump-input> "
        f"--artifact-root {artifact_root_pattern} "
        "--run-id <run-id-suffix> "
        "--mode hardlink"
    )
    if inventory_ready or ready_to_build_core:
        staging_status = "satisfied"
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
        "input_staging": {
            "id": "stage_offline_raw_layout",
            "status": staging_status,
            "ready": False,
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
    try:
        reject_player_identity_artifact_root(args.artifact_root, "--artifact-root")
        artifact_root_rejection = None
    except SystemExit as exc:
        artifact_root_rejection = str(exc)

    if artifact_root_rejection is None:
        inventory_result, inventory_payload = run_json_command(
            [
                str(SCRIPT_DIR / "check_reflection_inventory_pack_readiness.py"),
                "--root",
                str(args.artifact_root),
            ]
        )
    else:
        inventory_result = subprocess.CompletedProcess(
            ["check_reflection_inventory_pack_readiness.py", "--root", str(args.artifact_root)],
            1,
            "",
            artifact_root_rejection,
        )
        inventory_payload = rejected_artifact_root_inventory_payload(
            args.artifact_root,
            artifact_root_rejection,
        )
    coverage_command = [
        str(SCRIPT_DIR / "compare_reflection_snapshots.py"),
        "--base-root",
        str(args.snapshot_root),
        "--target-set",
        PLAYER_IDENTITY_TARGET_SET,
        "--readiness-report",
        "--json",
    ]
    if args.candidate_root:
        coverage_command.extend(["--candidate-root", str(args.candidate_root)])
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
    lifecycle_diagnosis = lifecycle_anchor_diagnosis(first_evidence_payload)
    lifecycle_ready = (
        lifecycle_diagnosis["session_start_accepted"] is True
        and lifecycle_diagnosis["session_end_accepted"] is True
    )
    offline_inputs = bounded_artifact_file_scan(args.artifact_root)

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
    if not lifecycle_ready:
        downstream_blockers.append("accepted_lifecycle_anchors_missing")
    if inventory_ready:
        blockers.extend(downstream_blockers)

    next_step = (
        "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack"
        if not inventory_ready
        else "plan_missing_server_list_players_and_server_kick_player_snapshots"
    )
    if inventory_ready:
        if first_evidence_ready and (second_source_missing or not lifecycle_ready):
            next_step = "produce_distinct_second_source_and_accepted_lifecycle_anchor_evidence"
        elif first_evidence_ready:
            next_step = "validate_players_identity_first_evidence_consume_and_promote_blocked"

    recipe_root_raw = offline_inputs.get("resolved_root")
    if isinstance(recipe_root_raw, str) and offline_inputs.get("status") != "artifact_root_rejected":
        recipe_root = Path(recipe_root_raw)
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
        "obelisk_commit_source": "OBELISK_COMMIT environment variable if set; otherwise current Git HEAD, or unknown when unavailable",
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
    )

    return {
        "schema": REPORT_SCHEMA,
        "status": status,
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "not_artifact_gate": True,
        "promotion_ready": False,
        "artifact_root": str(args.artifact_root),
        "snapshot_root": str(args.snapshot_root),
        "candidate_root": str(args.candidate_root) if args.candidate_root else None,
        "target_set": PLAYER_IDENTITY_TARGET_SET,
        "blockers": blockers,
        "deferred_until_reflection_inventory_ready": [] if inventory_ready else downstream_blockers,
        "primary_blocker": next_blocker.get("code"),
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
            "second_source_missing": second_source_missing,
            "second_source_inconclusive": second_source_inconclusive,
            "second_source_rejected": second_source_rejected,
        },
        "first_evidence": {
            "returncode": first_evidence_result.returncode,
            "ready": first_evidence_ready,
            "schema": first_evidence_payload.get("schema") if first_evidence_payload else None,
            "missing_required_targets": missing_targets,
            "lifecycle_anchors": lifecycle_diagnosis,
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
