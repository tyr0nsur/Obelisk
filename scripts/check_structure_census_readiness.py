#!/usr/bin/env python3
"""Read-only readiness check for the internal Structure aggregate/census lane."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/structure-aggregate-census-policy-slice-20260531T034715Z"
)
DEFAULT_MANIFEST_NAME = "structure-aggregate-census-policy-slice.json"
REPORT_SCHEMA = "obelisk.structure-census-readiness-check.v1"
POLICY_SCHEMA = "obelisk.structure-aggregate-census-policy-slice.v1"
INPUT_TARGET_SET = "structure-aggregate-census-planning"
OUTPUT_TARGET_SET = "structure-aggregate-census-policy-slice"
EXPECTED_INPUT_TARGETS = {
    "PrimalStructure.AllowStructureAccess",
    "PrimalStructure.IsAllowedToDemolish",
    "PrimalStructure.SetVariant",
    "PrimalStructureItemContainer.AllowToggleActivation",
    "PrimalStructureItemContainer.VerifyPinCode",
    "PrimalStructureSeating.CanSeat",
}
EXPECTED_COPIED_FIELDS = {
    "PrimalStructure.AllowStructureAccess.ReturnValue",
    "PrimalStructure.IsAllowedToDemolish.ReturnValue",
    "PrimalStructure.SetVariant.VariantIndex",
    "PrimalStructure.SetVariant.bForceSet",
    "PrimalStructure.SetVariant.ReturnValue",
    "PrimalStructureItemContainer.AllowToggleActivation.ReturnValue",
    "PrimalStructureSeating.CanSeat.bForce",
    "PrimalStructureSeating.CanSeat.ReturnValue",
}
EXPECTED_EXCLUDED_FIELDS = {
    "PrimalStructureItemContainer.VerifyPinCode.pinCode",
    "PrimalStructureItemContainer.VerifyPinCode.ReturnValue",
}
EXPECTED_REDACTED_FIELDS = {
    "PrimalStructure.AllowStructureAccess.ForPC",
    "PrimalStructure.IsAllowedToDemolish.ForPC",
    "PrimalStructureItemContainer.AllowToggleActivation.ForPC",
    "PrimalStructureSeating.CanSeat.ForPC",
    "PrimalStructureSeating.CanSeat.forCharacter",
}
REQUIRED_NON_CLAIM_TOKENS = (
    "does not expose UE pointers",
    "does not promote public SDK callbacks",
    "does not promote runtime hook wiring",
    "does not copy VerifyPinCode.pinCode or VerifyPinCode.ReturnValue",
)
STRUCTURE_CENSUS_ALLOWED_BOUNDARY_PREFIXES = (
    "$.non_claims",
    "$.safety_summary.explicitly_excluded",
)
STRUCTURE_CENSUS_FORBIDDEN_TRUE_KEYS = {
    "build_placement_policy_ready",
    "build_policy_ready",
    "collision_policy_ready",
    "mutation_allowed",
    "mutation_ready",
    "no_collision_policy_ready",
    "ownership_ready",
    "placement_policy_ready",
    "return_override_allowed",
    "return_override_ready",
    "runtime_hook_ready",
    "runtime_hooks_ready",
    "structure_identity_ready",
    "structure_lookup_ready",
    "structure_ownership_ready",
    "v1_complete",
    "v1_completion",
    "v1_ready",
}
STRUCTURE_CENSUS_FORBIDDEN_CLAIM_PHRASES = {
    "build placement": "build_placement_policy",
    "build policy": "build_policy",
    "collision policy": "no_collision_policy",
    "isallowedtobuild": "build_policy",
    "mutation allowed": "mutation",
    "mutation ready": "mutation",
    "no collision": "no_collision_policy",
    "no-collision": "no_collision_policy",
    "owner identity": "structure_ownership",
    "owner lookup": "structure_ownership",
    "ownership lookup": "structure_ownership",
    "placement policy": "build_placement_policy",
    "processevent hook": "runtime_hooks",
    "return override allowed": "return_override",
    "return override ready": "return_override",
    "runtime hook": "runtime_hooks",
    "runtime hooks": "runtime_hooks",
    "structure identity": "structure_identity",
    "structure lookup": "structure_lookup",
    "structure ownership": "structure_ownership",
    "structureevents sdk": "public_structureevents_sdk",
    "v1 complete": "v1_completion",
    "v1 completion": "v1_completion",
    "v1 done": "v1_completion",
    "v1 ready": "v1_completion",
}


def is_negative_boundary_statement(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("does not", "do not", "not "))


FORBIDDEN_COPIED_RE = re.compile(
    r"(?:ForPC|forCharacter|pinCode|VerifyPinCode|identity|lookup|mutation|"
    r"object_refs|public_sdk|resource_handle|return_override|runtime|ue_pointer)",
    re.IGNORECASE,
)
STRUCTURE_CENSUS_WIRING_TOKEN_RE = re.compile(r"\bStructureAggregateCensus(?:\.h)?\b")
STRUCTURE_CENSUS_BLOCKED_SOURCE_PREFIXES = (
    "hooks/",
    "include/obelisk/",
    "loader/",
    "plugins/",
    "runtime/",
)
STRUCTURE_CENSUS_BLOCKED_SOURCE_PATHS = {
    "core/EventManager.cpp",
    "core/EventManager.h",
    "core/PluginManager.cpp",
    "core/PluginManager.h",
}
SOURCE_SCAN_SUFFIXES = {".cpp", ".h", ".hpp", ".c", ".cc", ".cxx"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Structure aggregate/census candidate readiness without promoting a public SDK."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Offline artifact root.")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Structure aggregate/census policy-slice manifest. Defaults to --root/structure-aggregate-census-policy-slice.json.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def safe_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        append_blocker(blockers, "path_rejected", label=label, path=str(path), detail=str(exc))
        return None


def run_gate(root: Path, manifest: Path, mode: str) -> tuple[int, dict[str, Any] | None, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "validate_offline_artifact_gate.py"),
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--mode",
            mode,
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
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
    return result.returncode, payload, result.stderr.strip()


def read_policy(manifest: Path, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        parsed = json.loads(manifest.read_text(encoding="utf-8"))
    except OSError as exc:
        append_blocker(blockers, "manifest_unreadable", path=str(manifest), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "manifest_malformed", path=str(manifest), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        append_blocker(blockers, "manifest_not_object", path=str(manifest))
        return None
    return parsed


def require_set(
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    actual: Any,
    expected: set[str],
) -> set[str]:
    actual_set = set(actual) if isinstance(actual, list) and all(isinstance(item, str) for item in actual) else set()
    if actual_set != expected:
        append_blocker(
            blockers,
            reason,
            missing=sorted(expected - actual_set),
            unexpected=sorted(actual_set - expected),
        )
    return actual_set


def iter_policy_values(value: object, *, trail: str = "$") -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if isinstance(child, (dict, list)):
                found.extend(iter_policy_values(child, trail=child_trail))
            else:
                found.append((child_trail, child))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_trail = f"{trail}[{index}]"
            if isinstance(child, (dict, list)):
                found.extend(iter_policy_values(child, trail=child_trail))
            else:
                found.append((child_trail, child))
    return found


def validate_no_core_surface_claims(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    for trail, value in iter_policy_values(policy):
        if value is True:
            key = trail.rsplit(".", 1)[-1]
            if key in STRUCTURE_CENSUS_FORBIDDEN_TRUE_KEYS:
                append_blocker(blockers, "structure_census_policy_surface_overclaim", surface=key, path=trail)
        if not isinstance(value, str):
            continue
        text = value.casefold()
        if any(trail.startswith(prefix) for prefix in STRUCTURE_CENSUS_ALLOWED_BOUNDARY_PREFIXES) and is_negative_boundary_statement(text):
            continue
        for phrase, surface in STRUCTURE_CENSUS_FORBIDDEN_CLAIM_PHRASES.items():
            if phrase in text:
                append_blocker(blockers, "structure_census_policy_surface_overclaim", surface=surface, path=trail)


def validate_policy(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if policy.get("schema") != POLICY_SCHEMA:
        append_blocker(blockers, "schema_mismatch", value=policy.get("schema"))
    if policy.get("input_target_set") != INPUT_TARGET_SET:
        append_blocker(blockers, "input_target_set_mismatch", value=policy.get("input_target_set"))
    if policy.get("output_target_set") != OUTPUT_TARGET_SET:
        append_blocker(blockers, "output_target_set_mismatch", value=policy.get("output_target_set"))
    if policy.get("policy_status") != "evidence-only":
        append_blocker(blockers, "policy_status_not_evidence_only", value=policy.get("policy_status"))
    if policy.get("consume_only") is not True:
        append_blocker(blockers, "consume_only_not_true", value=policy.get("consume_only"))

    coverage = policy.get("coverage")
    if not isinstance(coverage, dict):
        append_blocker(blockers, "coverage_missing")
        coverage = {}
    input_targets = require_set(
        blockers,
        reason="input_target_coverage_mismatch",
        actual=coverage.get("input_targets"),
        expected=EXPECTED_INPUT_TARGETS,
    )
    copied_fields = require_set(
        blockers,
        reason="copied_field_coverage_mismatch",
        actual=coverage.get("copied_fields_permitted"),
        expected=EXPECTED_COPIED_FIELDS,
    )
    excluded_fields = require_set(
        blockers,
        reason="explicit_exclusion_coverage_mismatch",
        actual=coverage.get("explicitly_excluded_fields"),
        expected=EXPECTED_EXCLUDED_FIELDS,
    )
    redacted_fields = require_set(
        blockers,
        reason="redacted_field_coverage_mismatch",
        actual=coverage.get("redacted_fields"),
        expected=EXPECTED_REDACTED_FIELDS,
    )
    if coverage.get("status") != "complete":
        append_blocker(blockers, "coverage_status_not_complete", value=coverage.get("status"))

    for copied_field in copied_fields:
        if FORBIDDEN_COPIED_RE.search(copied_field):
            append_blocker(blockers, "forbidden_copied_field", copied_field=copied_field)

    counters = policy.get("approved_counters")
    if not isinstance(counters, dict):
        append_blocker(blockers, "approved_counters_missing")
        counters = {}
    expected_counts = {
        "input_target_count": 6,
        "copied_field_count": 8,
        "copied_bool_count": 7,
        "copied_int32_count": 1,
        "redacted_field_count": 5,
        "explicitly_excluded_field_count": 2,
    }
    for key, expected in expected_counts.items():
        if counters.get(key) != expected:
            append_blocker(blockers, "approved_counter_mismatch", field=key, expected=expected, value=counters.get(key))

    safety = policy.get("safety_summary")
    if not isinstance(safety, dict):
        append_blocker(blockers, "safety_summary_missing")
        safety = {}
    if safety.get("artifact_status") != "evidence_only":
        append_blocker(blockers, "safety_artifact_status_invalid", value=safety.get("artifact_status"))
    if safety.get("consume_only") is not True:
        append_blocker(blockers, "safety_consume_only_not_true", value=safety.get("consume_only"))
    if safety.get("promotion_ready") is not False:
        append_blocker(blockers, "safety_promotion_ready_not_false", value=safety.get("promotion_ready"))
    if safety.get("intended_use") != "offline_review_only":
        append_blocker(blockers, "safety_intended_use_invalid", value=safety.get("intended_use"))

    non_claims = policy.get("non_claims")
    if not isinstance(non_claims, list):
        append_blocker(blockers, "non_claims_missing")
        non_claims_text = ""
    else:
        non_claims_text = "\n".join(str(item) for item in non_claims)
    for token in REQUIRED_NON_CLAIM_TOKENS:
        if token not in non_claims_text:
            append_blocker(blockers, "required_non_claim_missing", token=token)
    validate_no_core_surface_claims(policy, blockers)

    return {
        "input_targets": sorted(input_targets),
        "copied_fields": sorted(copied_fields),
        "redacted_fields": sorted(redacted_fields),
        "explicitly_excluded_fields": sorted(excluded_fields),
        "approved_counters": counters,
    }


def is_blocked_structure_census_wiring_path(relative_path: str) -> bool:
    return (
        relative_path in STRUCTURE_CENSUS_BLOCKED_SOURCE_PATHS
        or any(relative_path.startswith(prefix) for prefix in STRUCTURE_CENSUS_BLOCKED_SOURCE_PREFIXES)
    )


def validate_source_isolation(repo_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    scanned = 0
    violations: list[str] = []
    for path in repo_root.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SCAN_SUFFIXES:
            continue
        try:
            relative = path.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        if relative.startswith(("build/", "local/", ".git/")):
            continue
        if not is_blocked_structure_census_wiring_path(relative):
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            append_blocker(blockers, "structure_census_source_scan_failed", path=relative, detail=str(exc))
            continue
        if STRUCTURE_CENSUS_WIRING_TOKEN_RE.search(text):
            violations.append(relative)

    if violations:
        append_blocker(
            blockers,
            "structure_census_runtime_wiring_detected",
            paths=sorted(violations),
        )

    return {
        "status": "isolated" if not violations else "blocked",
        "blocked_prefixes": list(STRUCTURE_CENSUS_BLOCKED_SOURCE_PREFIXES),
        "blocked_paths": sorted(STRUCTURE_CENSUS_BLOCKED_SOURCE_PATHS),
        "scanned_blocked_source_files": scanned,
        "violations": sorted(violations),
    }


def build_report(root_arg: Path, manifest_arg: Path | None) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    root = safe_path(root_arg, "--root", blockers)
    manifest_path = manifest_arg if manifest_arg is not None else root_arg / DEFAULT_MANIFEST_NAME
    manifest = safe_path(manifest_path, "--manifest", blockers)

    summary: dict[str, Any] = {}
    source_isolation = validate_source_isolation(REPO_ROOT, blockers)
    consume_gate: dict[str, Any] = {"returncode": None, "status": None}
    promote_gate: dict[str, Any] = {"returncode": None, "status": None}
    if root is not None and manifest is not None:
        policy = read_policy(manifest, blockers)
        if policy is not None:
            summary = validate_policy(policy, blockers)
        consume_rc, consume_payload, consume_stderr = run_gate(root, manifest, "consume")
        consume_gate = {
            "returncode": consume_rc,
            "status": consume_payload.get("status") if isinstance(consume_payload, dict) else None,
            "stderr": consume_stderr,
        }
        if consume_rc != 0 or consume_gate["status"] != "accepted":
            append_blocker(blockers, "consume_gate_not_accepted", returncode=consume_rc, status=consume_gate["status"])
        promote_rc, promote_payload, promote_stderr = run_gate(root, manifest, "promote")
        promote_blockers = (
            promote_payload.get("blockers")
            if isinstance(promote_payload, dict) and isinstance(promote_payload.get("blockers"), list)
            else []
        )
        promote_reasons = sorted(
            blocker.get("reason")
            for blocker in promote_blockers
            if isinstance(blocker, dict) and isinstance(blocker.get("reason"), str)
        )
        promote_gate = {
            "returncode": promote_rc,
            "status": promote_payload.get("status") if isinstance(promote_payload, dict) else None,
            "blocker_reasons": promote_reasons,
            "stderr": promote_stderr,
        }
        required_promote_reasons = {
            "promote_mode_structure_aggregate_census_policy_slice_consume_only",
            "promote_mode_manifest_has_non_claims",
        }
        if promote_rc == 0 or promote_gate["status"] != "blocked":
            append_blocker(blockers, "promote_gate_not_blocked", returncode=promote_rc, status=promote_gate["status"])
        if not required_promote_reasons.issubset(set(promote_reasons)):
            append_blocker(
                blockers,
                "promote_gate_missing_required_blockers",
                missing=sorted(required_promote_reasons - set(promote_reasons)),
            )

    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "not_artifact_gate": True,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        "root": str(root if root is not None else root_arg),
        "manifest": str(manifest if manifest is not None else manifest_path),
        "consume_gate": consume_gate,
        "promote_gate": promote_gate,
        "source_isolation": source_isolation,
        "summary": summary,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is internal planning evidence only",
            "does not promote StructureEvents, Structure SDK, structure census public ABI, identity, lookup, ownership, mutation, return override, runtime hooks, or ResourceHandle",
            "does not promote build placement, no-collision, or IsAllowedToBuild policy",
            "does not claim v1 completion or production readiness",
            "does not replace player identity, privacy, lifecycle, SDK consumer, public ABI, or live-ops promotion gates",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.root, args.manifest)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
