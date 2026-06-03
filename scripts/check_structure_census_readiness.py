#!/usr/bin/env python3
"""Read-only readiness check for the internal Structure aggregate/census lane."""

from __future__ import annotations

import argparse
import hashlib
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
DEFAULT_SECOND_SOURCE_READINESS = Path(
    "/servidor/ark/workspace-offline/"
    "structure-aggregate-census-planning-second-source-bool-tail-20260530-offline-regenerated/"
    "structure-aggregate-census-planning-readiness.json"
)
DEFAULT_SECOND_SOURCE_READINESS_SHA256 = "bba7a2023a77c297069d06c7350ed8804b0fad0ecdf41945889119bfce5d785e"
REPORT_SCHEMA = "obelisk.structure-census-readiness-check.v1"
POLICY_SCHEMA = "obelisk.structure-aggregate-census-policy-slice.v1"
SECOND_SOURCE_READINESS_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
INPUT_TARGET_SET = "structure-aggregate-census-planning"
OUTPUT_TARGET_SET = "structure-aggregate-census-policy-slice"
TARGET_READINESS_STATUSES = (
    "candidate",
    "fixture-backed",
    "second-source-missing",
    "second-source-accepted",
    "blocked",
)
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
REPORT_NON_CLAIMS = [
    "candidate readiness is internal planning evidence only",
    "no public StructureEvents",
    "no public Structure SDK or structure census public ABI",
    "no identity/lookup",
    "no mutation",
    "no return override",
    "no enforcement",
    "does not promote StructureEvents, Structure SDK, structure census public ABI, identity, lookup, ownership, mutation, return override, runtime hooks, enforcement, or ResourceHandle",
    "does not promote build placement, no-collision, or IsAllowedToBuild policy",
    "does not claim v1 completion or production readiness",
    "does not replace player identity, privacy, lifecycle, SDK consumer, public ABI, second-source, or live-ops promotion gates",
]
CANDIDATE_ONLY_MISSING_PUBLIC_GATES = [
    "public_structure_sdk",
    "structure_identity",
    "build_policy",
    "runtime_wiring",
    "promotion_gate",
]
STRUCTURE_CENSUS_ALLOWED_BOUNDARY_PREFIXES = (
    "$.non_claims",
    "$.safety_summary.explicitly_excluded",
)
STRUCTURE_CENSUS_FORBIDDEN_TRUE_KEYS = {
    "build_placement_policy_ready",
    "build_policy_ready",
    "collision_policy_ready",
    "enforcement_allowed",
    "enforcement_ready",
    "mutation_allowed",
    "mutation_ready",
    "no_collision_policy_ready",
    "ownership_ready",
    "placement_policy_ready",
    "public_structure_sdk_ready",
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
STRUCTURE_CENSUS_FORBIDDEN_READY_DOMAINS = {
    "abi",
    "build",
    "buildpolicy",
    "callback",
    "completion",
    "event",
    "events",
    "promotion",
    "promote",
    "promoted",
    "public",
    "sdk",
    "structure",
    "structureevents",
    "structuresdk",
    "v1",
}
STRUCTURE_CENSUS_READY_TERMS = {
    "accepted",
    "complete",
    "completion",
    "done",
    "promoted",
    "promotion",
    "readiness",
    "ready",
    "released",
}
STRUCTURE_CENSUS_NEGATED_TRUE_KEY_PREFIXES = (
    "must_block_",
    "must_remain_",
    "no_",
    "not_",
)
STRUCTURE_CENSUS_FORBIDDEN_CLAIM_PHRASES = {
    "build placement": "build_placement_policy",
    "build policy": "build_policy",
    "collision policy": "no_collision_policy",
    "enforcement allowed": "enforcement",
    "enforcement ready": "enforcement",
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
STRUCTURE_CENSUS_FORBIDDEN_STRING_DOMAINS = {
    "public sdk": "public_structure_sdk",
    "public structure sdk": "public_structure_sdk",
    "structure sdk": "public_structure_sdk",
    "structure events": "public_structureevents_sdk",
    "structureevents": "public_structureevents_sdk",
    "structureevents sdk": "public_structureevents_sdk",
    "public abi": "public_abi",
    "public sdk gate": "public_structure_sdk",
    "promotion gate": "promotion_gate",
}
STRUCTURE_CENSUS_POSITIVE_STRING_RE = re.compile(
    r"(?:\baccepted\b|\bpromoted\b|\breleased\b|\bcomplete\b|\bdone\b|"
    r"\bpublic[-_\s]+ready\b|\bready\b)",
    re.IGNORECASE,
)
STRUCTURE_CENSUS_SECOND_SOURCE_POSITIVE_CLAIM_RE = re.compile(
    r"(?:\bready\b|\breadiness\b|\ballowed\b|\benabled\b|\bpromoted\b|"
    r"\bpublic\s+sdk\b|\bv1\s+(?:complete|completion|done|ready)\b|"
    r"\bruntime\s+hooks?\s+ready\b)",
    re.IGNORECASE,
)


def is_negative_boundary_statement(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("does not", "do not", "no ", "not "))


def normalized_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return separated.casefold().replace("-", "_").replace(" ", "_")


def key_tokens(value: object) -> set[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value))
    return {token for token in re.split(r"[^A-Za-z0-9]+", spaced.casefold()) if token}


def compact_key_text(value: object) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value))
    return "".join(token for token in re.split(r"[^A-Za-z0-9]+", spaced.casefold()) if token)


def has_forbidden_ready_true_claim(key: str, path: str) -> bool:
    normalized = normalized_key(key)
    if normalized.startswith(STRUCTURE_CENSUS_NEGATED_TRUE_KEY_PREFIXES):
        return False
    if normalized == "layout_ready":
        return False
    if normalized in STRUCTURE_CENSUS_FORBIDDEN_TRUE_KEYS:
        return True

    key_token_set = key_tokens(key)
    path_token_set = key_tokens(path)
    compact_key = compact_key_text(key)
    compact_path = compact_key_text(path)
    domain_in_key = bool(key_token_set & STRUCTURE_CENSUS_FORBIDDEN_READY_DOMAINS) or any(
        domain in compact_key for domain in STRUCTURE_CENSUS_FORBIDDEN_READY_DOMAINS if len(domain) > 3
    )
    domain_in_path = bool(path_token_set & STRUCTURE_CENSUS_FORBIDDEN_READY_DOMAINS) or any(
        domain in compact_path for domain in STRUCTURE_CENSUS_FORBIDDEN_READY_DOMAINS if len(domain) > 3
    )
    readiness_in_key = bool(key_token_set & STRUCTURE_CENSUS_READY_TERMS)
    if readiness_in_key and (domain_in_key or domain_in_path):
        return True
    if "ready" in key_token_set and domain_in_path:
        return True
    return False


def has_false_ready_literal(text: str) -> bool:
    return re.search(r"\bready\s*[:=]\s*false\b", text, re.IGNORECASE) is not None


def flexible_phrase_in_text(text: str, phrase: str) -> bool:
    tokens = [token for token in re.split(r"[^A-Za-z0-9]+", phrase) if token]
    if not tokens:
        return False
    pattern = r"(?<![A-Za-z0-9])" + r"[\W_]*".join(re.escape(token) for token in tokens) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def forbidden_string_claim_surface(key: str, path: str, value: str) -> str | None:
    text = value.casefold().strip()
    if is_negative_boundary_statement(text) or has_false_ready_literal(text):
        return None
    normalized = normalized_key(key)
    value_tokens = key_tokens(value)
    key_path_tokens = key_tokens(key) | key_tokens(path)
    value_public_ready = "public" in value_tokens and "ready" in value_tokens
    if normalized == "status" and (value_public_ready or text in {"promoted", "public-ready", "public_ready"}):
        return "status"
    if normalized.endswith("_status"):
        domain_tokens = key_path_tokens & STRUCTURE_CENSUS_FORBIDDEN_READY_DOMAINS
        if domain_tokens and value_tokens & {"accepted", "promoted", "ready", "released"}:
            return "_".join(sorted(domain_tokens))
    if STRUCTURE_CENSUS_POSITIVE_STRING_RE.search(text) is None:
        return None
    for phrase, surface in STRUCTURE_CENSUS_FORBIDDEN_STRING_DOMAINS.items():
        if flexible_phrase_in_text(value, phrase):
            return surface
    return None


FORBIDDEN_COPIED_RE = re.compile(
    r"(?:ForPC|forCharacter|pinCode|VerifyPinCode|enforcement|identity|lookup|mutation|"
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
    parser.add_argument(
        "--second-source-readiness",
        type=Path,
        help=(
            "Offline reflection snapshot readiness JSON for structure-aggregate-census-planning. "
            "Defaults to the hash-pinned approved offline workspace report."
        ),
    )
    parser.add_argument(
        "--no-default-second-source-readiness",
        action="store_true",
        help="Do not consume the default hash-pinned second-source readiness report.",
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


def records_by_target(records: object, field_key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(records, list):
        return grouped
    for record in records:
        if not isinstance(record, dict):
            continue
        target = record.get("target")
        field_name = record.get(field_key)
        source_snapshot = record.get("source_snapshot")
        source_sha = record.get("source_snapshot_sha256")
        if not all(isinstance(value, str) and value for value in (target, field_name, source_snapshot, source_sha)):
            continue
        grouped.setdefault(target, []).append(record)
    return grouped


def target_status(candidate: bool, fixture_backed: bool, second_source_backed: bool, blocked: bool) -> str:
    if blocked:
        return "blocked"
    if not candidate:
        return "blocked"
    if not fixture_backed:
        return "candidate"
    if second_source_backed:
        return "second-source-accepted"
    return "second-source-missing"


def read_second_source_readiness(
    path: Path,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        append_blocker(blockers, "second_source_readiness_unreadable", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "second_source_readiness_malformed", path=str(path), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        append_blocker(blockers, "second_source_readiness_not_object", path=str(path))
        return None
    return parsed


def sha256_file(path: Path, blockers: list[dict[str, Any]]) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        append_blocker(blockers, "second_source_readiness_hash_unreadable", path=str(path), detail=str(exc))
        return None
    return digest.hexdigest()


def iter_named_values(value: object, key_name: str, *, trail: str = "$") -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key == key_name:
                found.append((child_trail, child))
            if isinstance(child, (dict, list)):
                found.extend(iter_named_values(child, key_name, trail=child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.extend(iter_named_values(child, key_name, trail=f"{trail}[{index}]"))
    return found


def validate_second_source_readiness(
    readiness: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    path: Path,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    local_blocker_start = len(blockers)
    observed_sha256 = sha256_file(path, blockers)
    if expected_sha256 is not None and observed_sha256 != expected_sha256:
        append_blocker(
            blockers,
            "second_source_readiness_sha256_mismatch",
            expected=expected_sha256,
            value=observed_sha256,
            path=str(path),
        )
    if readiness.get("schema") != SECOND_SOURCE_READINESS_SCHEMA:
        append_blocker(
            blockers,
            "second_source_readiness_schema_mismatch",
            expected=SECOND_SOURCE_READINESS_SCHEMA,
            value=readiness.get("schema"),
        )
    if readiness.get("gate_mode") != "planning_layout_intake":
        append_blocker(
            blockers,
            "second_source_readiness_gate_mode_mismatch",
            expected="planning_layout_intake",
            value=readiness.get("gate_mode"),
        )
    if readiness.get("second_source_status") != "compared":
        append_blocker(
            blockers,
            "second_source_readiness_status_mismatch",
            expected="compared",
            value=readiness.get("second_source_status"),
        )

    target_sets = readiness.get("target_sets")
    if target_sets != [INPUT_TARGET_SET]:
        append_blocker(
            blockers,
            "second_source_readiness_target_set_mismatch",
            expected=[INPUT_TARGET_SET],
            value=target_sets,
        )

    totals = readiness.get("totals")
    if not isinstance(totals, dict):
        append_blocker(blockers, "second_source_readiness_totals_missing")
        totals = {}
    expected_totals = {
        "targets": 6,
        "comparable": 6,
        "blocked": 0,
        "second_source_accepted": 6,
        "second_source_missing": 0,
        "second_source_rejected": 0,
        "second_source_inconclusive": 0,
    }
    for field, expected in expected_totals.items():
        if totals.get(field) != expected:
            append_blocker(
                blockers,
                "second_source_readiness_total_mismatch",
                field=field,
                expected=expected,
                value=totals.get(field),
            )

    expected_filters = sorted(f"obelisk.ufunction-chain.snapshot.v1:{target}" for target in EXPECTED_INPUT_TARGETS)
    target_filters = readiness.get("target_filters")
    observed_filters = sorted(target_filters) if isinstance(target_filters, list) else []
    if observed_filters != expected_filters:
        append_blocker(
            blockers,
            "second_source_readiness_target_filters_mismatch",
            expected=expected_filters,
            value=target_filters,
        )

    planning_gate = readiness.get("planning_layout_gate")
    if not isinstance(planning_gate, dict):
        append_blocker(blockers, "second_source_readiness_planning_layout_gate_missing")
        planning_gate = {}
    if planning_gate.get("ready") is not True:
        append_blocker(
            blockers,
            "second_source_readiness_planning_layout_gate_not_ready",
            value=planning_gate.get("ready"),
        )
    if planning_gate.get("ready_scope") != "planning_only":
        append_blocker(
            blockers,
            "second_source_readiness_planning_scope_mismatch",
            expected="planning_only",
            value=planning_gate.get("ready_scope"),
        )
    if planning_gate.get("layout_ready") is not True:
        append_blocker(
            blockers,
            "second_source_readiness_planning_layout_not_ready",
            value=planning_gate.get("layout_ready"),
        )
    if planning_gate.get("blockers") != []:
        append_blocker(
            blockers,
            "second_source_readiness_planning_blockers_not_empty",
            value=planning_gate.get("blockers"),
        )

    promotion_gate = readiness.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        append_blocker(blockers, "second_source_readiness_promotion_gate_missing")
        promotion_gate = {}
    if promotion_gate.get("ready") is not False:
        append_blocker(
            blockers,
            "second_source_readiness_promotion_gate_ready_not_false",
            value=promotion_gate.get("ready"),
        )

    validate_second_source_no_core_surface_claims(readiness, blockers)

    for field in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        planning_value = planning_gate.get(field)
        if planning_value is not False:
            append_blocker(
                blockers,
                "second_source_readiness_planning_readiness_flag_not_false",
                field=f"planning_layout_gate.{field}",
                value=planning_value,
            )
        for trail, value in iter_named_values(readiness, field):
            if value is not False:
                append_blocker(
                    blockers,
                    "second_source_readiness_readiness_flag_not_false",
                    field=field,
                    path=trail,
                    value=value,
                )

    accepted = len(blockers) == local_blocker_start
    return {
        "path": str(path),
        "sha256": observed_sha256,
        "expected_sha256": expected_sha256,
        "status": "accepted" if accepted else "blocked",
        "schema": readiness.get("schema"),
        "gate_mode": readiness.get("gate_mode"),
        "target_sets": target_sets if isinstance(target_sets, list) else [],
        "totals": totals,
        "planning_layout_gate": {
            "ready": planning_gate.get("ready"),
            "ready_scope": planning_gate.get("ready_scope"),
            "promotion_ready": planning_gate.get("promotion_ready"),
            "public_sdk_ready": planning_gate.get("public_sdk_ready"),
            "runtime_ready": planning_gate.get("runtime_ready"),
        },
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
    }


def validate_second_source_no_core_surface_claims(
    readiness: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    for trail, value in iter_policy_values(readiness):
        if value is True:
            key = trail.rsplit(".", 1)[-1]
            if has_forbidden_ready_true_claim(key, trail):
                append_blocker(
                    blockers,
                    "second_source_readiness_surface_overclaim",
                    surface=key,
                    path=trail,
                )
        if not isinstance(value, str):
            continue
        text = value.casefold()
        if is_negative_boundary_statement(text):
            continue
        surface = forbidden_string_claim_surface(trail.rsplit(".", 1)[-1], trail, value)
        if surface is not None:
            append_blocker(
                blockers,
                "second_source_readiness_surface_overclaim",
                surface=surface,
                path=trail,
            )
        if STRUCTURE_CENSUS_SECOND_SOURCE_POSITIVE_CLAIM_RE.search(text) is None:
            continue
        for phrase, surface in STRUCTURE_CENSUS_FORBIDDEN_CLAIM_PHRASES.items():
            if flexible_phrase_in_text(value, phrase):
                append_blocker(
                    blockers,
                    "second_source_readiness_surface_overclaim",
                    surface=surface,
                    path=trail,
                )


def build_target_readiness(
    policy: dict[str, Any],
    summary: dict[str, Any],
    blockers: list[dict[str, Any]],
    second_source_summary: dict[str, Any],
) -> dict[str, Any]:
    input_targets = set(summary.get("input_targets", []))
    copied_fields = set(summary.get("copied_fields", []))
    redacted_fields = set(summary.get("redacted_fields", []))
    excluded_fields = set(summary.get("explicitly_excluded_fields", []))
    copied_records = records_by_target(policy.get("copied_fields_permitted"), "copied_field")
    excluded_records = records_by_target(policy.get("explicitly_excluded_fields"), "excluded_field")
    redacted_records = records_by_target(policy.get("redacted_structure_fields"), "redacted_field")
    second_source_backed = second_source_summary.get("status") == "accepted"

    report_blocked = any(blocker.get("reason") in {"input_target_coverage_mismatch"} for blocker in blockers)
    targets: list[dict[str, Any]] = []
    status_counts = {status: 0 for status in TARGET_READINESS_STATUSES}
    for target in sorted(EXPECTED_INPUT_TARGETS):
        target_copied_fields = sorted(field for field in copied_fields if field.startswith(f"{target}."))
        target_redacted_fields = sorted(field for field in redacted_fields if field.startswith(f"{target}."))
        target_excluded_fields = sorted(field for field in excluded_fields if field.startswith(f"{target}."))
        target_records = copied_records.get(target, []) + excluded_records.get(target, [])
        candidate = target in input_targets
        fixture_backed = bool(candidate and target_records)
        target_blockers: list[str] = []
        if not candidate:
            target_blockers.append("target_not_in_input_coverage")
        if report_blocked:
            target_blockers.append("input_target_coverage_blocked")

        status = target_status(candidate, fixture_backed, second_source_backed, bool(target_blockers))
        status_counts[status] += 1
        targets.append(
            {
                "target": target,
                "status": status,
                "candidate": candidate,
                "candidate_status": "candidate" if candidate else "blocked",
                "fixture_status": "fixture-backed" if fixture_backed else "missing",
                "fixture_backed": fixture_backed,
                "second_source_status": "second-source-accepted" if second_source_backed else "second-source-missing",
                "second_source_backed": second_source_backed,
                "copied_fields": target_copied_fields,
                "redacted_fields": target_redacted_fields,
                "explicitly_excluded_fields": target_excluded_fields,
                "fixture_sources": sorted(
                    {
                        f"{record['source_snapshot']}:{record['source_snapshot_sha256']}"
                        for record in target_records
                    }
                ),
                "redaction_fixture_sources": sorted(
                    {
                        f"{record['source_snapshot']}:{record['source_snapshot_sha256']}"
                        for record in redacted_records.get(target, [])
                    }
                ),
                "blockers": target_blockers,
            }
        )

    readiness_status = "second-source-missing"
    if status_counts["blocked"]:
        readiness_status = "blocked"
    elif status_counts["candidate"]:
        readiness_status = "candidate"
    elif status_counts["fixture-backed"]:
        readiness_status = "fixture-backed"
    elif status_counts["second-source-accepted"]:
        readiness_status = "second-source-accepted"

    return {
        "status": readiness_status,
        "allowed_statuses": list(TARGET_READINESS_STATUSES),
        "status_counts": {key: value for key, value in status_counts.items() if value},
        "second_source": {
            "status": "accepted" if second_source_backed else "missing",
            "path": second_source_summary.get("path") if second_source_backed else None,
            "gate_mode": second_source_summary.get("gate_mode") if second_source_backed else None,
            "ready_scope": (
                second_source_summary.get("planning_layout_gate", {}).get("ready_scope")
                if second_source_backed
                else None
            ),
            "totals": second_source_summary.get("totals") if second_source_backed else None,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "required_before": (
                []
                if second_source_backed
                else [
                    "runtime_observation",
                    "internal_event_promotion",
                    "public_sdk",
                    "enforcement",
                ]
            ),
            "reason": (
                "accepted planning-layout second-source accounting only; no runtime, public SDK, mutation, identity, lookup, return override, enforcement, or promotion readiness is implied"
                if second_source_backed
                else "this policy slice contains first-source fixture evidence only; no distinct sanitized artifact identity or strict second-source comparison is present"
            ),
        },
        "targets": targets,
    }


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
            if has_forbidden_ready_true_claim(key, trail):
                append_blocker(blockers, "structure_census_policy_surface_overclaim", surface=key, path=trail)
        if not isinstance(value, str):
            continue
        text = value.casefold()
        if is_negative_boundary_statement(text):
            continue
        surface = forbidden_string_claim_surface(trail.rsplit(".", 1)[-1], trail, value)
        if surface is not None:
            append_blocker(blockers, "structure_census_policy_surface_overclaim", surface=surface, path=trail)
        for phrase, surface in STRUCTURE_CENSUS_FORBIDDEN_CLAIM_PHRASES.items():
            if flexible_phrase_in_text(value, phrase):
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


def build_candidate_only_accounting(
    *,
    ready: bool,
    second_source_summary: dict[str, Any],
) -> dict[str, Any]:
    second_source_accepted = second_source_summary.get("status") == "accepted"
    if not ready:
        result = "blocked"
        reason = "readiness blockers are present; no Structure census accounting outcome is accepted"
        mode = "blocked"
    elif second_source_accepted:
        result = "second-source-accepted-without-public-structure-sdk-identity-build-policy"
        reason = (
            "second-source layout evidence is accepted for internal planning only; "
            "public Structure SDK, identity, build-policy, runtime, and promotion gates remain false"
        )
        mode = "candidate-only"
    else:
        result = "candidate-without-second-source"
        reason = (
            "candidate fixture evidence is accepted for internal planning only; "
            "second-source, public Structure SDK, identity, build-policy, runtime, and promotion gates remain absent"
        )
        mode = "candidate-only"

    return {
        "mode": mode,
        "result": result,
        "second_source_accepted": second_source_accepted,
        "accepted_for_internal_planning": ready,
        "public_sdk_ready": False,
        "public_structure_sdk_ready": False,
        "structure_identity_ready": False,
        "build_policy_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        "missing_public_gates": CANDIDATE_ONLY_MISSING_PUBLIC_GATES,
        "reason": reason,
    }


def build_report(root_arg: Path, manifest_arg: Path | None, second_source_arg: Path | None = None) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    root = safe_path(root_arg, "--root", blockers)
    manifest_path = manifest_arg if manifest_arg is not None else root_arg / DEFAULT_MANIFEST_NAME
    manifest = safe_path(manifest_path, "--manifest", blockers)
    second_source_path = (
        safe_path(second_source_arg, "--second-source-readiness", blockers)
        if second_source_arg is not None
        else None
    )

    summary: dict[str, Any] = {}
    target_readiness: dict[str, Any] = {
        "status": "blocked",
        "allowed_statuses": list(TARGET_READINESS_STATUSES),
        "status_counts": {"blocked": len(EXPECTED_INPUT_TARGETS)},
        "second_source": {"status": "missing"},
        "targets": [],
    }
    second_source_summary: dict[str, Any] = {
        "status": "missing",
        "path": str(second_source_arg) if second_source_arg is not None else None,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
    }
    if second_source_path is not None:
        second_source_payload = read_second_source_readiness(second_source_path, blockers)
        if second_source_payload is not None:
            expected_sha256 = (
                DEFAULT_SECOND_SOURCE_READINESS_SHA256
                if second_source_path == DEFAULT_SECOND_SOURCE_READINESS.resolve()
                else None
            )
            second_source_summary = validate_second_source_readiness(
                second_source_payload,
                blockers,
                path=second_source_path,
                expected_sha256=expected_sha256,
            )
    source_isolation = validate_source_isolation(REPO_ROOT, blockers)
    consume_gate: dict[str, Any] = {"returncode": None, "status": None}
    promote_gate: dict[str, Any] = {"returncode": None, "status": None}
    if root is not None and manifest is not None:
        policy = read_policy(manifest, blockers)
        if policy is not None:
            summary = validate_policy(policy, blockers)
            target_readiness = build_target_readiness(policy, summary, blockers, second_source_summary)
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
    accounting_mode = "candidate-only" if ready else "blocked"
    candidate_only_accounting = build_candidate_only_accounting(
        ready=ready,
        second_source_summary=second_source_summary,
    )
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "outcome": accounting_mode,
        "accounting_mode": accounting_mode,
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "candidate_only_accounting": candidate_only_accounting,
        "not_artifact_gate": True,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        "enforcement_ready": False,
        "offline_only": True,
        "root": str(root if root is not None else root_arg),
        "manifest": str(manifest if manifest is not None else manifest_path),
        "consume_gate": consume_gate,
        "promote_gate": promote_gate,
        "source_isolation": source_isolation,
        "target_readiness": target_readiness,
        "second_source_readiness": second_source_summary,
        "summary": summary,
        "blockers": blockers,
        "non_claim_matrix": {
            "public_structure_events": "not_claimed",
            "public_structure_sdk": "not_claimed",
            "identity_lookup": "not_claimed",
            "mutation": "not_claimed",
            "return_override": "not_claimed",
            "enforcement": "not_claimed",
            "runtime": "not_claimed",
        },
        "non_claims": REPORT_NON_CLAIMS,
    }


def main() -> int:
    args = parse_args()
    if args.no_default_second_source_readiness and args.second_source_readiness is not None:
        raise SystemExit("--no-default-second-source-readiness cannot be combined with --second-source-readiness")
    second_source_readiness = (
        None
        if args.no_default_second_source_readiness
        else args.second_source_readiness or DEFAULT_SECOND_SOURCE_READINESS
    )
    report = build_report(args.root, args.manifest, second_source_readiness)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
