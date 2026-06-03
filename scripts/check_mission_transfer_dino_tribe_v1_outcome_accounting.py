#!/usr/bin/env python3
"""Validate v1 outcome accounting for mission/transfer/dino/tribe/buff.

This is an accounting guardrail, not a promotion checker.  The current repository
state is allowed to remain candidate-only/planning.  A v1 release statement that
uses this umbrella blocker must either exclude the umbrella and name every leaf as
excluded, or rely on a future manifest where every leaf is promoted with concrete
evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from check_tribe_scalar_boundary_readiness import (
    DEFAULT_SNAPSHOT_ROOT as DEFAULT_TRIBE_SCALAR_SNAPSHOT_ROOT,
    EXPECTED_ACCEPTED_FIELDS as TRIBE_EXPECTED_ACCEPTED_FIELDS,
    EXPECTED_REQUIRED_REDACTIONS as TRIBE_EXPECTED_REQUIRED_REDACTIONS,
    REPORT_SCHEMA as TRIBE_SCALAR_BOUNDARY_SCHEMA,
    TARGET_SET as TRIBE_SCALAR_TARGET_SET,
    build_report as build_tribe_scalar_boundary_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_SPLIT_NOTE = REPO_ROOT / "docs" / "research" / "2026-06-01-mission-transfer-dino-tribe-v1-split.md"
REPORT_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1"
SURFACE_ID = "obelisk.mission_transfer_dino_tribe.v1"
REQUIRED_LEAVES = ("mission", "transfer", "dino_policy", "tribe_policy", "buff_status")
MISSION_LEAF_ACCOUNTING_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-mission-leaf-blocker-accounting.v1"
TRIBE_LEAF_ACCOUNTING_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-tribe-leaf-blocker-accounting.v1"
MISSION_REQUIRED_EVIDENCE = ("mission-compact-intake", "mission-copied-bool-policy-slice")
TRIBE_REQUIRED_EVIDENCE = ("tribe-compact-intake",)
MISSION_COPIED_TARGETS = (
    "MissionType.AddPlayerToMission",
    "MissionType.BPAllowPlayerToLeaveMission",
    "MissionType.BPOnPlayerRemovedFromMission",
)
MISSION_RECOGNITION_ONLY_TARGETS = ("MissionType.GetPlayerUsableItems",)
MISSION_COPIED_BOOL_FIELDS = (
    "MissionType.AddPlayerToMission.bForceAdd",
    "MissionType.AddPlayerToMission.ReturnValue",
    "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
    "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
    "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
)
MISSION_REDACTED_RECOGNITION_FIELDS = (
    "MissionType.AddPlayerToMission.PlayerCharacter",
    "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn",
    "MissionType.BPOnPlayerRemovedFromMission.Player",
    "MissionType.BPOnPlayerRemovedFromMission.Controller",
    "MissionType.GetPlayerUsableItems.Character",
    "MissionType.GetPlayerUsableItems.OutItemIDs",
)
TRIBE_PUBLIC_FALSE_KEYS = (
    "public_sdk_ready",
    "public_tribe_sdk_ready",
    "public_abi_ready",
    "runtime_ready",
    "runtime_observer_approved",
    "identity_ready",
    "lookup_ready",
    "mutation_ready",
    "return_override_ready",
    "resource_handle_ready",
    "v1_completion_ready",
    "promotion_ready",
)
MISSION_SPLIT_NOTE_REQUIRED_TOKENS = (
    "mission-copied-bool-policy-slice",
    "promote-mode blocked",
    "MissionType.GetPlayerUsableItems",
    "recognition-only",
) + MISSION_COPIED_TARGETS + MISSION_RECOGNITION_ONLY_TARGETS + MISSION_COPIED_BOOL_FIELDS + MISSION_REDACTED_RECOGNITION_FIELDS
MISSION_CANDIDATE_FORBIDDEN_TRUE_KEYS = {
    "dino_sdk_ready",
    "identity_ready",
    "lookup_ready",
    "mission_sdk_ready",
    "mutation_ready",
    "ownership_ready",
    "promotion_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_dino_sdk_ready",
    "public_buff_sdk_ready",
    "public_mission_sdk_ready",
    "public_sdk_ready",
    "public_transfer_sdk_ready",
    "public_tribe_sdk_ready",
    "resource_handle_ready",
    "return_override_ready",
    "runtime_observer_approved",
    "runtime_hook_ready",
    "runtime_ready",
    "transfer_sdk_ready",
    "tribe_sdk_ready",
    "v1_complete",
    "v1_completion",
    "v1_ready",
}
LEAF_ALIASES = {
    "mission": ("mission",),
    "transfer": ("transfer",),
    "dino_policy": ("dino_policy", "dino policy", "dino"),
    "tribe_policy": ("tribe_policy", "tribe policy", "tribe"),
    "buff_status": ("buff_status", "buff/status", "buff status", "buff"),
}
PROMOTED_LEAF_EVIDENCE_KEYS = ("abi_tests", "sdk_consumer_tests", "second_source_evidence")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
LEAF_MISSING_PUBLIC_GATES = {
    "mission": (
        "public_mission_sdk_abi",
        "runtime_observer_approval",
        "mission_identity_state_reward_authority",
        "dispatcher_lifecycle",
        "installed_sdk_consumer_tests",
        "mutation_return_override_policy",
    ),
    "transfer": (
        "public_transfer_sdk_abi",
        "transfer_payload_ownership",
        "downloaded_character_payload_contract",
        "dino_payload_contract",
        "player_identity",
        "cross_map_state_correlation",
        "ownership_policy",
        "teleport_spawn_authority",
        "runtime_wiring",
        "mutation_return_override_policy",
    ),
    "dino_policy": (
        "public_dino_sdk_abi",
        "dino_player_passenger_identity",
        "lookup_ownership_lifetime",
        "postcall_return_policy",
        "dispatcher_lifecycle",
        "runtime_observation",
        "privacy_contract",
        "resource_handle_policy",
        "mutation_return_override_policy",
    ),
    "tribe_policy": (
        "public_tribe_sdk_abi",
        "tribe_player_identity",
        "permission_semantics",
        "log_string_array_payload_policy",
        "online_list_payload_policy",
        "mission_tag_payload_policy",
        "dispatcher_lifecycle",
        "runtime_observation",
        "privacy_redaction_contract",
        "mutation_return_override_policy",
    ),
    "buff_status": (
        "public_buff_status_sdk_abi",
        "buff_class_object_redaction_contract",
        "copied_payload_policy",
        "lifecycle_stacking_invalidation_semantics",
        "refreshed_compact_evidence",
        "dispatcher_lifecycle",
        "runtime_observation",
        "resource_handle_policy",
        "mutation_return_override_policy",
    ),
}
LEAF_PRIORITY_PROFILES = {
    "mission": {
        "base_score": 80,
        "required_evidence": ("mission-compact-intake", "mission-copied-bool-policy-slice"),
        "reusable_evidence": (
            "focused copied-bool readiness checker",
            "fixture-backed exact Mission metadata",
            "five canonical copied bool fields",
            "recognition-only redaction for object and array fields",
        ),
        "blocking_risk": (
            "runtime observer approval",
            "dispatcher lifecycle",
            "public ABI and SDK consumer coverage",
            "mission/player identity and reward authority",
        ),
        "next_v1_reuse_step": (
            "Harden the internal copied-bool fail-closed contract and keep object, "
            "identity, array, mutation, and return-override claims excluded."
        ),
    },
    "dino_policy": {
        "base_score": 72,
        "required_evidence": ("dino-compact-intake",),
        "reusable_evidence": (
            "focused scalar readiness checker",
            "accepted compact passenger/carry layout evidence",
            "pre-call scalar-only planning path",
            "explicit return-value deferral",
        ),
        "blocking_risk": (
            "dino/player/passenger identity",
            "lookup and lifetime ownership",
            "post-call return semantics",
            "runtime privacy and dispatcher lifecycle",
        ),
        "next_v1_reuse_step": (
            "Reuse the scalar-only redaction model after Mission; keep dino/player "
            "object references and return values recognition-only."
        ),
    },
    "transfer": {
        "base_score": 68,
        "required_evidence": ("transfer-ufunction-intake", "transfer-baccept-only-policy-slice"),
        "reusable_evidence": (
            "focused bAccept copied-bool checker",
            "complete transfer intake provenance",
            "explicit consume-only promote gate",
        ),
        "blocking_risk": (
            "payload ownership",
            "downloaded character and dino payload contracts",
            "player identity and cross-map correlation",
            "teleport/spawn authority",
        ),
        "next_v1_reuse_step": (
            "Reuse only the single copied-bool consume gate; defer transfer payloads, "
            "identity, ownership, cross-map state, teleport/spawn, mutation, and return override."
        ),
    },
    "buff_status": {
        "base_score": 58,
        "required_evidence": ("buff-compact-intake", "buff-breadth-intake"),
        "reusable_evidence": (
            "compact and breadth layout evidence",
            "existing internal recognizer coverage",
            "clear object/class redaction boundary to define",
        ),
        "blocking_risk": (
            "class/object redaction contract",
            "copied payload policy",
            "lifecycle, stacking, and invalidation semantics",
            "fresh compact BoolProperty tail evidence",
        ),
        "next_v1_reuse_step": (
            "Refresh compact evidence before treating Buff as a scalar/status lane; "
            "keep class/object pointers, lifecycle claims, ResourceHandle, mutation, and return override excluded."
        ),
    },
    "tribe_policy": {
        "base_score": 52,
        "required_evidence": ("tribe-compact-intake",),
        "reusable_evidence": (
            "compact layout evidence",
            "permission/log/online-list target vocabulary",
            "candidate split between scalar permission and array/string payload work",
        ),
        "blocking_risk": (
            "tribe/player identity",
            "permission semantics",
            "log, string, and array payload ownership",
            "privacy redaction and runtime observation",
        ),
        "next_v1_reuse_step": (
            "Split any future work into a narrow scalar permission/log-request intake and "
            "a separately blocked array/string payload lane before public discussion."
        ),
    },
}
NEGATIVE_EVIDENCE_RE = re.compile(
    r"\b(?:candidate[- ]?only|consume[- ]?only|planning[- ]?only|not promoted|"
    r"promotion[_ -]?ready\s*[:=]\s*false|public[_ -]?sdk[_ -]?ready\s*[:=]\s*false|"
    r"runtime[_ -]?ready\s*[:=]\s*false)\b",
    re.IGNORECASE,
)
NON_PROMOTIONAL_SCHEMA_KEYS = {"schema", "artifact_schema", "evidence_schema", "report_schema"}
NON_PROMOTIONAL_SCHEMA_TOKENS = {
    "approved_bundle",
    "approved_runtime_bundle",
    "candidate",
    "consume",
    "planning",
    "preflight",
    "readiness",
    "request",
    "window",
    "sidecar",
}
NON_PROMOTIONAL_PATH_MARKERS = (
    "approved_bundle",
    "approved_runtime_bundle",
    "candidate",
    "consume",
    "planning",
    "preflight",
    "readiness",
    "request",
    "window",
    "sidecar",
)
FORBIDDEN_CLAIM_PATTERNS = (
    r"\b(?:Mission|Transfer|Dino|Tribe|Buff(?:/status| status)?|BuffStatus)\s+(?:SDK|API)\b",
    r"\bidentity\b",
    r"\blookup\b",
    r"\bmutation\b",
    r"\breturn[- ]override\b",
    r"\bruntime\s+hook\b",
    r"\bResourceHandle\b",
    r"\bteleport\s*/\s*spawn\b",
    r"\bteleport[- ]spawn\b",
    r"\bteleport\b",
    r"\bspawn\b",
    r"\bownership\s+lookup\b",
    r"\bcross[- ]map\s+correlation\b",
)
FORBIDDEN_CLAIM_RE = re.compile("|".join(f"(?:{pattern})" for pattern in FORBIDDEN_CLAIM_PATTERNS), re.IGNORECASE)
CANDIDATE_READY_CLAIM_PATTERNS = (
    r"\b(?:public\s+SDK|public\s+ABI|runtime|runtime\s+observer|runtime\s+hook|"
    r"v1|v1\s+SDK|promotion|release)\s+(?:ready|readiness|complete|completion)\b",
    r"\b(?:ready|complete)\s+for\s+v1\b",
    r"\bv1(?:\.0)?\s+(?:stable|complete|completion|ready)\b",
)
CANDIDATE_READY_CLAIM_RE = re.compile(
    "|".join(f"(?:{pattern})" for pattern in CANDIDATE_READY_CLAIM_PATTERNS),
    re.IGNORECASE,
)
NEGATOR_RE = re.compile(
    r"\b(?:cannot|does\s+not|do\s+not|is\s+not|are\s+not|"
    r"must\s+not|no|not|without)\b",
    re.IGNORECASE,
)
AFTER_NEGATOR_RE = re.compile(
    r"\b(?:blocked|excluded|not\s+included|post-v1|post v1)\b",
    re.IGNORECASE,
)
NEGATED_EXCLUSION_RE = re.compile(
    r"\b(?:not|no\s+longer)\s+(?:blocked|excluded|omitted|out\s+of\s+scope|post[- ]v1|post\s+v1)\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="docs/public_sdk_surfaces.json path.")
    parser.add_argument("--split-note", type=Path, default=DEFAULT_SPLIT_NOTE, help="Leaf split research note path.")
    parser.add_argument(
        "--tribe-snapshot-root",
        type=Path,
        default=DEFAULT_TRIBE_SCALAR_SNAPSHOT_ROOT,
        help="Sanitized UFunction snapshot root for candidate-only Tribe scalar evidence.",
    )
    parser.add_argument("--release-statement", type=Path, help="Optional reviewed v1 release statement.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(extra)
    blockers.append(item)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"{label}: unreadable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label}: top-level JSON must be an object")
    return payload


def surface_by_id(manifest: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if isinstance(surface, dict) and surface.get("id") == surface_id:
            return surface
    return None


def read_optional(path: Path | None, label: str) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"{label}: unreadable: {exc}") from exc


def leaf_map(surface: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    units = surface.get("leaf_decision_units")
    if not isinstance(units, list):
        add(blockers, "leaf_decision_units_missing", "$.surfaces[mission_transfer_dino_tribe].leaf_decision_units")
        return {}
    leaves: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for index, leaf in enumerate(units):
        if not isinstance(leaf, dict):
            add(blockers, "leaf_decision_unit_not_object", f"$.leaf_decision_units[{index}]")
            continue
        leaf_id = leaf.get("id")
        if not isinstance(leaf_id, str):
            add(blockers, "leaf_decision_unit_id_missing", f"$.leaf_decision_units[{index}].id")
            continue
        if leaf_id in leaves:
            duplicate_ids.append(leaf_id)
        leaves[leaf_id] = leaf
    if duplicate_ids:
        add(blockers, "leaf_decision_units_duplicate", "$.leaf_decision_units", duplicate_ids=sorted(duplicate_ids))
    observed = set(leaves)
    required = set(REQUIRED_LEAVES)
    if observed != required:
        add(
            blockers,
            "leaf_decision_units_mismatch",
            "$.leaf_decision_units",
            expected=list(REQUIRED_LEAVES),
            observed=[leaf_id for leaf_id in REQUIRED_LEAVES if leaf_id in observed]
            + sorted(observed - required),
            missing=sorted(required - observed),
            extra=sorted(observed - required),
        )
    return leaves


def flattened_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        items: list[str] = []
        for child in value.values():
            items.extend(flattened_strings(child))
        return items
    if isinstance(value, list):
        items = []
        for child in value:
            items.extend(flattened_strings(child))
        return items
    return []


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


def public_contract(surface_or_leaf: dict[str, Any]) -> list[str]:
    contract = surface_or_leaf.get("public_contract", [])
    return contract if isinstance(contract, list) else ["<public_contract is not a list>"]


def claim_is_negated(text: str, start: int, end: int) -> bool:
    clause_start = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start)) + 1
    clause_prefix = text[clause_start:start]
    if re.match(r"\s*No\b", clause_prefix, re.IGNORECASE):
        return True
    before = text[max(0, start - 40) : start]
    after = text[end : min(len(text), end + 80)]
    if NEGATED_EXCLUSION_RE.search(after):
        return False
    return bool(NEGATOR_RE.search(before) or AFTER_NEGATOR_RE.search(after))


def forbidden_claims(text: str) -> list[str]:
    claims: list[str] = []
    for match in FORBIDDEN_CLAIM_RE.finditer(text):
        if claim_is_negated(text, match.start(), match.end()):
            continue
        claims.append(match.group(0))
    return claims


def candidate_ready_claims(text: str) -> list[str]:
    claims: list[str] = []
    for match in CANDIDATE_READY_CLAIM_RE.finditer(text):
        if claim_is_negated(text, match.start(), match.end()):
            continue
        claims.append(match.group(0))
    return claims


def outcome_is_negated(text: str, start: int) -> bool:
    clause_start = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start)) + 1
    before = text[clause_start:start]
    return bool(NEGATOR_RE.search(before))


def has_unnegated_alias_outcome(text: str, alias: str, outcome: str) -> bool:
    pattern = re.compile(
        rf"\b{re.escape(alias)}\b.{{0,100}}?\b({re.escape(outcome)})\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        if not outcome_is_negated(text, match.start(1)):
            return True
    return False


def validate_split_note(text: str, blockers: list[dict[str, Any]]) -> None:
    if SURFACE_ID not in text:
        add(blockers, "split_note_surface_missing", "$.split_note")
    for leaf in REQUIRED_LEAVES:
        if leaf not in text:
            add(blockers, "split_note_leaf_missing", "$.split_note", leaf=leaf)
    required_non_claims = (
        "does not promote a public SDK",
        "Public SDK promotion remains blocked for all five leaves",
    )
    for phrase in required_non_claims:
        if phrase not in text:
            add(blockers, "split_note_non_claim_missing", "$.split_note", phrase=phrase)
    for token in MISSION_SPLIT_NOTE_REQUIRED_TOKENS:
        if token not in text:
            add(
                blockers,
                "mission_leaf_accounting_split_note_token_missing",
                "$.split_note.mission_leaf_accounting",
                token=token,
            )


def release_statement_outcome(text: str) -> dict[str, Any]:
    if not text:
        return {
            "present": False,
            "umbrella_excluded": False,
            "leaf_exclusions": {},
            "leaf_promotions": {},
            "forbidden_claims": [],
        }
    surface_line = next((line for line in text.splitlines() if SURFACE_ID in line), "")
    leaf_exclusions = {}
    leaf_promotions = {}
    for leaf, aliases in LEAF_ALIASES.items():
        alias_excluded = False
        alias_promoted = False
        for alias in aliases:
            alias_excluded = alias_excluded or has_unnegated_alias_outcome(text, alias, "excluded")
            alias_promoted = alias_promoted or has_unnegated_alias_outcome(text, alias, "promoted")
        leaf_exclusions[leaf] = alias_excluded
        leaf_promotions[leaf] = alias_promoted
    return {
        "present": True,
        "umbrella_excluded": bool(surface_line) and has_unnegated_alias_outcome(surface_line, SURFACE_ID, "excluded"),
        "leaf_exclusions": leaf_exclusions,
        "leaf_promotions": leaf_promotions,
        "forbidden_claims": sorted(set(forbidden_claims(text))),
    }


def evidence_for_leaf(surface: dict[str, Any], leaf: dict[str, Any]) -> dict[str, Any]:
    evidence = leaf.get("evidence")
    if isinstance(evidence, dict):
        return evidence
    per_leaf = surface.get("promotion_evidence_by_leaf")
    leaf_id = leaf.get("id")
    if isinstance(per_leaf, dict) and isinstance(per_leaf.get(leaf_id), dict):
        return per_leaf[leaf_id]
    return {}


def resolve_evidence_path(raw_path: str, manifest_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    repo_path = REPO_ROOT / path
    if repo_path.exists():
        return repo_path
    return manifest_dir / path


def relative_promoted_evidence_path(raw_path: str) -> Path | None:
    path = Path(raw_path)
    if path.is_absolute() or not raw_path.strip():
        return None
    if any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path


def evidence_path_has_non_promotional_marker(raw_path: str) -> bool:
    relative = relative_promoted_evidence_path(raw_path)
    if relative is None:
        return True
    parts = [part.lower().replace("-", "_") for part in relative.parts]
    for part in parts:
        if "approved_bundle" in part or "approved_runtime_bundle" in part:
            return True
        tokens = {token for token in part.split("_") if token}
        for marker in NON_PROMOTIONAL_PATH_MARKERS:
            if marker in tokens or part.startswith(f"{marker}_") or part.endswith(f"_{marker}"):
                return True
    return False


def evidence_path_is_specific_to_leaf(raw_path: str, leaf_id: str, evidence_key: str) -> bool:
    relative = relative_promoted_evidence_path(raw_path)
    if relative is None:
        return False
    lowered = relative.name.lower()
    leaf_tokens = [token for token in leaf_id.replace("-", "_").split("_") if token]
    key_tokens = [token for token in evidence_key.replace("-", "_").split("_") if token]
    return all(token.lower() in lowered for token in leaf_tokens + key_tokens)


def evidence_has_non_promotional_schema_marker(value: Any, *, parent_key: str | None = None) -> bool:
    normalized_key = parent_key.lower().replace("-", "_") if isinstance(parent_key, str) else None
    if normalized_key in NON_PROMOTIONAL_SCHEMA_KEYS:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
        normalized_text = text.lower().replace("-", "_").replace(" ", "_")
        if "approved_bundle" in normalized_text or "approved_runtime_bundle" in normalized_text:
            return True
        schema_tokens = {token for token in re.split(r"[^a-z0-9]+", text.lower()) if token}
        if schema_tokens & NON_PROMOTIONAL_SCHEMA_TOKENS:
            return True
    if isinstance(value, dict):
        return any(
            evidence_has_non_promotional_schema_marker(child, parent_key=key if isinstance(key, str) else None)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(evidence_has_non_promotional_schema_marker(child, parent_key=parent_key) for child in value)
    return False


def validate_promoted_leaf_gate_report(
    entry: Any,
    *,
    evidence_key: str,
    leaf_id: str,
    label: str,
    manifest_dir: Path,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(entry, dict):
        add(blockers, "promoted_leaf_gate_report_unverified", label, leaf=leaf_id, evidence_key=evidence_key)
        return
    raw_path = entry.get("path")
    expected_sha = entry.get("sha256")
    if not isinstance(raw_path, str) or not raw_path:
        add(blockers, "promoted_leaf_evidence_path_missing", f"{label}.path", leaf=leaf_id, evidence_key=evidence_key)
        return
    if relative_promoted_evidence_path(raw_path) is None:
        add(
            blockers,
            "promoted_leaf_evidence_path_not_repo_relative",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=raw_path,
        )
        return
    if evidence_path_has_non_promotional_marker(raw_path):
        add(
            blockers,
            "promoted_leaf_evidence_path_non_promotional",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=raw_path,
        )
        return
    if not evidence_path_is_specific_to_leaf(raw_path, leaf_id, evidence_key):
        add(
            blockers,
            "promoted_leaf_evidence_path_not_leaf_specific",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=raw_path,
        )
        return
    if not isinstance(expected_sha, str) or SHA256_RE.fullmatch(expected_sha) is None:
        add(
            blockers,
            "promoted_leaf_evidence_sha256_missing",
            f"{label}.sha256",
            leaf=leaf_id,
            evidence_key=evidence_key,
        )
        return
    path = resolve_evidence_path(raw_path, manifest_dir)
    try:
        content = path.read_bytes()
    except OSError as exc:
        add(
            blockers,
            "promoted_leaf_evidence_path_missing",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=str(path),
            detail=str(exc),
        )
        return
    actual_sha = hashlib.sha256(content).hexdigest()
    if actual_sha != expected_sha:
        add(
            blockers,
            "promoted_leaf_evidence_sha256_mismatch",
            f"{label}.sha256",
            leaf=leaf_id,
            evidence_key=evidence_key,
            expected=expected_sha,
            value=actual_sha,
        )
        return
    try:
        report = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        add(
            blockers,
            "promoted_leaf_gate_report_unverified",
            label,
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=str(path),
            detail=str(exc),
        )
        return
    if not isinstance(report, dict):
        add(blockers, "promoted_leaf_gate_report_unverified", label, leaf=leaf_id, evidence_key=evidence_key)
        return
    expected_pairs = {
        "surface": SURFACE_ID,
        "leaf": leaf_id,
        "evidence_kind": evidence_key,
        "status": "promoted",
        "promotion_ready": True,
        "public_sdk_ready": True,
        "runtime_ready": True,
    }
    for key, expected in expected_pairs.items():
        if report.get(key) != expected:
            add(
                blockers,
                "promoted_leaf_gate_report_unverified",
                f"{label}.{key}",
                leaf=leaf_id,
                evidence_key=evidence_key,
                expected=expected,
                value=report.get(key),
            )
    if not isinstance(report.get("schema"), str) or not report["schema"].startswith("obelisk."):
        add(blockers, "promoted_leaf_gate_report_unverified", f"{label}.schema", leaf=leaf_id, evidence_key=evidence_key)
    if evidence_has_non_promotional_schema_marker(report):
        add(
            blockers,
            "promoted_leaf_gate_report_non_promotional_schema",
            f"{label}.schema",
            leaf=leaf_id,
            evidence_key=evidence_key,
        )
    artifact_identity = report.get("artifact_identity")
    if not isinstance(artifact_identity, dict) or not isinstance(artifact_identity.get("sha256"), str):
        add(
            blockers,
            "promoted_leaf_gate_report_unverified",
            f"{label}.artifact_identity",
            leaf=leaf_id,
            evidence_key=evidence_key,
        )
    if evidence_key == "second_source_evidence" and not isinstance(report.get("second_source_provenance"), dict):
        add(
            blockers,
            "promoted_leaf_second_source_provenance_missing",
            f"{label}.second_source_provenance",
            leaf=leaf_id,
            evidence_key=evidence_key,
        )


def validate_promoted_leaf_evidence(
    surface: dict[str, Any],
    leaves: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
    *,
    manifest_dir: Path,
) -> bool:
    all_promoted = bool(leaves) and all(leaf.get("status") == "promoted" for leaf in leaves.values())
    any_promoted = any(leaf.get("status") == "promoted" for leaf in leaves.values())
    if any_promoted and not all_promoted:
        add(blockers, "partial_leaf_promotion_not_allowed", "$.leaf_decision_units")
        return False
    if not all_promoted:
        return False
    blocker_count = len(blockers)
    for leaf_id in REQUIRED_LEAVES:
        leaf = leaves[leaf_id]
        evidence = evidence_for_leaf(surface, leaf)
        label = f"$.leaf_decision_units[{leaf_id}].evidence"
        if not evidence:
            add(blockers, "promoted_leaf_evidence_missing", label, leaf=leaf_id)
            continue
        for key in ("promotion_status", "public_sdk_ready", "promotion_ready", "runtime_ready"):
            expected: Any = "promoted" if key == "promotion_status" else True
            if evidence.get(key) != expected:
                add(blockers, f"promoted_leaf_{key}_mismatch", f"{label}.{key}", leaf=leaf_id)
        for key in PROMOTED_LEAF_EVIDENCE_KEYS:
            values = evidence.get(key)
            if not isinstance(values, list) or not values:
                add(blockers, "promoted_leaf_real_evidence_missing", f"{label}.{key}", leaf=leaf_id)
                continue
            for index, entry in enumerate(values):
                validate_promoted_leaf_gate_report(
                    entry,
                    evidence_key=key,
                    leaf_id=leaf_id,
                    label=f"{label}.{key}[{index}]",
                    manifest_dir=manifest_dir,
                    blockers=blockers,
                )
        joined = "\n".join(flattened_strings(evidence))
        if NEGATIVE_EVIDENCE_RE.search(joined):
            add(blockers, "promoted_leaf_evidence_contains_candidate_only_markers", label, leaf=leaf_id)
    return len(blockers) == blocker_count


def collect_true_ready_overclaims(value: Any, prefix: str = "$") -> list[str]:
    overclaims: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if key in MISSION_CANDIDATE_FORBIDDEN_TRUE_KEYS and child is True:
                overclaims.append(child_path)
            overclaims.extend(collect_true_ready_overclaims(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            overclaims.extend(collect_true_ready_overclaims(child, f"{prefix}[{index}]"))
    return overclaims


def candidate_leaf_evidence_sources(
    surface: dict[str, Any],
    leaf_id: str,
    leaf: dict[str, Any],
) -> list[tuple[dict[str, Any], str]]:
    sources: list[tuple[dict[str, Any], str]] = []
    evidence = leaf.get("evidence")
    if isinstance(evidence, dict):
        sources.append((evidence, f"$.leaf_decision_units[{leaf_id}].evidence"))
    per_leaf = surface.get("promotion_evidence_by_leaf")
    if isinstance(per_leaf, dict) and isinstance(per_leaf.get(leaf_id), dict):
        sources.append((per_leaf[leaf_id], f"$.promotion_evidence_by_leaf[{leaf_id}]"))
    return sources


def validate_candidate_leaf_evidence(
    surface: dict[str, Any],
    leaf_id: str,
    leaf: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    status = leaf.get("status") if isinstance(leaf.get("status"), str) else "missing"
    if status == "promoted":
        return
    for evidence, label in candidate_leaf_evidence_sources(surface, leaf_id, leaf):
        ready_reason = "mission_leaf_candidate_ready_overclaim" if leaf_id == "mission" else "leaf_candidate_ready_overclaim"
        claim_reason = (
            "mission_leaf_candidate_evidence_forbidden_claim"
            if leaf_id == "mission"
            else "leaf_candidate_evidence_forbidden_claim"
        )
        for field in collect_true_ready_overclaims(evidence, label):
            add(blockers, ready_reason, field, leaf=leaf_id)
        claims = forbidden_claims("\n".join(flattened_strings(evidence)))
        for claim in claims:
            add(
                blockers,
                claim_reason,
                label,
                leaf=leaf_id,
                claim=claim,
            )
        ready_claims = candidate_ready_claims("\n".join(flattened_strings(evidence)))
        for claim in ready_claims:
            add(
                blockers,
                ready_reason,
                label,
                leaf=leaf_id,
                claim=claim,
            )


def build_mission_leaf_blocker_accounting(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
) -> dict[str, Any]:
    leaf = leaves.get("mission", {})
    current_evidence = string_list(leaf.get("current_evidence"))
    missing_required_evidence = sorted(set(MISSION_REQUIRED_EVIDENCE) - set(current_evidence))
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    mission_gap = gaps.get("mission") if isinstance(gaps, dict) and isinstance(gaps.get("mission"), dict) else {}

    return {
        "schema": MISSION_LEAF_ACCOUNTING_SCHEMA,
        "leaf": "mission",
        "lane": "mission_copied_bool_policy_slice",
        "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
        "accounting_scope": "candidate-only internal blocker accounting",
        "accepted_for_internal_planning": not missing_required_evidence and leaf.get("status") == "planning",
        "consume_only": True,
        "internal_reusable_evidence_only": True,
        "v1_accounted": bool(mission_gap.get("v1_accounted")),
        "mission_sdk_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_observer_approved": False,
        "runtime_ready": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "promotion_ready": False,
        "return_override_ready": False,
        "v1_completion": False,
        "focused_checker": "scripts/check_mission_copied_bool_readiness.py",
        "input_target_set": "mission-compact-intake",
        "output_target_set": "mission-copied-bool-policy-slice",
        "required_evidence": list(MISSION_REQUIRED_EVIDENCE),
        "current_evidence": current_evidence,
        "missing_required_evidence": missing_required_evidence,
        "copied_bool_boundary": {
            "copied_targets": list(MISSION_COPIED_TARGETS),
            "copied_bool_fields": list(MISSION_COPIED_BOOL_FIELDS),
            "copied_bool_count": len(MISSION_COPIED_BOOL_FIELDS),
        },
        "redaction_boundary": {
            "recognition_only_targets": list(MISSION_RECOGNITION_ONLY_TARGETS),
            "redacted_recognition_fields": list(MISSION_REDACTED_RECOGNITION_FIELDS),
            "forbidden_promotions": [
                "mission identity",
                "player/controller/character identity",
                "item arrays",
                "object pointers",
                "lookup",
                "runtime hook wiring",
                "mutation",
                "return override",
                "ResourceHandle",
            ],
        },
        "remaining_public_gates": string_list(mission_gap.get("missing_public_gates")),
        "outcome": (
            "internal_planning_only"
            if not missing_required_evidence and leaf.get("status") == "planning"
            else "blocked_accounting"
        ),
        "non_claims": [
            "mission leaf accounting is exactly consume-only internal reusable evidence",
            "mission leaf accounting does not promote a public Mission SDK, ABI, callback, or descriptor",
            "mission leaf accounting does not promote runtime hooks, dispatcher wiring, mutation, return override, identity, lookup, arrays, or ResourceHandle",
            "mission leaf accounting does not expand beyond the frozen copied-bool policy slice",
        ],
    }


def validate_tribe_scalar_boundary_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = "$.tribe_leaf_blocker_accounting.scalar_boundary_checker_report"
    if report.get("schema") != TRIBE_SCALAR_BOUNDARY_SCHEMA:
        add(blockers, "tribe_scalar_boundary_schema_mismatch", f"{label}.schema")
    if report.get("target_set") != TRIBE_SCALAR_TARGET_SET:
        add(blockers, "tribe_scalar_boundary_target_set_mismatch", f"{label}.target_set")
    if report.get("accepted_for_internal_planning") is not True:
        add(blockers, "tribe_scalar_boundary_not_internal_planning_ready", f"{label}.accepted_for_internal_planning")
    for key in ("offline_only", "fixture_only", "not_artifact_gate"):
        if report.get(key) is not True:
            add(blockers, "tribe_scalar_boundary_safety_flag_mismatch", f"{label}.{key}", key=key)
    if report.get("blockers"):
        add(
            blockers,
            "tribe_scalar_boundary_checker_blocked",
            f"{label}.blockers",
            checker_blockers=report.get("blockers"),
        )
    for key in TRIBE_PUBLIC_FALSE_KEYS:
        if report.get(key) is not False:
            add(blockers, "tribe_scalar_boundary_public_or_runtime_claim", f"{label}.{key}", key=key)

    summary = report.get("summary")
    if not isinstance(summary, dict):
        add(blockers, "tribe_scalar_boundary_summary_missing", f"{label}.summary")
        return
    accepted_fields = string_list(summary.get("accepted_scalar_fields"))
    missing_accepted = sorted(set(TRIBE_EXPECTED_ACCEPTED_FIELDS) - set(accepted_fields))
    if missing_accepted:
        add(
            blockers,
            "tribe_scalar_boundary_accepted_fields_missing",
            f"{label}.summary.accepted_scalar_fields",
            missing=missing_accepted,
        )
    redacted_fields = string_list(summary.get("redacted_fields"))
    missing_redactions = sorted(set(TRIBE_EXPECTED_REQUIRED_REDACTIONS) - set(redacted_fields))
    if missing_redactions:
        add(
            blockers,
            "tribe_scalar_boundary_required_redactions_missing",
            f"{label}.summary.redacted_fields",
            missing=missing_redactions,
        )


def build_tribe_leaf_blocker_accounting(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    scalar_report: dict[str, Any],
) -> dict[str, Any]:
    leaf = leaves.get("tribe_policy", {})
    current_evidence = string_list(leaf.get("current_evidence"))
    missing_required_evidence = sorted(set(TRIBE_REQUIRED_EVIDENCE) - set(current_evidence))
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    tribe_gap = (
        gaps.get("tribe_policy")
        if isinstance(gaps, dict) and isinstance(gaps.get("tribe_policy"), dict)
        else {}
    )
    summary = scalar_report.get("summary") if isinstance(scalar_report.get("summary"), dict) else {}

    accepted_scalar_fields = string_list(
        summary.get("accepted_scalar_fields") if isinstance(summary, dict) else None
    )
    redacted_fields = string_list(summary.get("redacted_fields") if isinstance(summary, dict) else None)
    optional_controls = summary.get("optional_controls") if isinstance(summary, dict) else None
    control_ready = scalar_report.get("server_request_tribe_log_control_ready")

    return {
        "schema": TRIBE_LEAF_ACCOUNTING_SCHEMA,
        "leaf": "tribe_policy",
        "lane": "tribe_scalar_boundary_candidate",
        "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
        "accounting_scope": "candidate-only internal blocker accounting",
        "accepted_for_internal_planning": (
            not missing_required_evidence
            and leaf.get("status") == "planning"
            and scalar_report.get("accepted_for_internal_planning") is True
            and not scalar_report.get("blockers")
        ),
        "candidate_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "v1_accounted": bool(tribe_gap.get("v1_accounted")),
        "tribe_sdk_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "public_tribe_sdk_ready": False,
        "runtime_observer_approved": False,
        "runtime_ready": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "promotion_ready": False,
        "return_override_ready": False,
        "resource_handle_ready": False,
        "v1_completion": False,
        "focused_checker": "scripts/check_tribe_scalar_boundary_readiness.py",
        "input_target_set": TRIBE_SCALAR_TARGET_SET,
        "required_evidence": list(TRIBE_REQUIRED_EVIDENCE),
        "current_evidence": current_evidence,
        "missing_required_evidence": missing_required_evidence,
        "scalar_boundary": {
            "checker_schema": scalar_report.get("schema"),
            "checker_ready": bool(scalar_report.get("ready")),
            "tribe_scalar_boundary_ready": bool(scalar_report.get("tribe_scalar_boundary_ready")),
            "server_request_tribe_log_control_ready": control_ready,
            "accepted_scalar_fields": accepted_scalar_fields,
            "accepted_scalar_count": len(accepted_scalar_fields),
            "optional_controls": optional_controls if isinstance(optional_controls, list) else [],
        },
        "redaction_boundary": {
            "redacted_fields": redacted_fields,
            "required_redactions": sorted(TRIBE_EXPECTED_REQUIRED_REDACTIONS),
            "forbidden_promotions": [
                "public Tribe SDK",
                "tribe/player identity",
                "membership or permission enforcement contract",
                "tribe log, MOTD, notice, string, or text payloads",
                "online-list and mission-tag arrays",
                "object pointers and UE references",
                "lookup",
                "runtime hook wiring",
                "mutation",
                "return override",
                "ResourceHandle",
            ],
        },
        "remaining_public_gates": string_list(tribe_gap.get("missing_public_gates")),
        "outcome": (
            "internal_planning_only"
            if not missing_required_evidence
            and leaf.get("status") == "planning"
            and scalar_report.get("accepted_for_internal_planning") is True
            and not scalar_report.get("blockers")
            else "blocked_accounting"
        ),
        "non_claims": [
            "tribe leaf accounting is candidate-only internal reusable evidence",
            "tribe leaf accounting does not promote a public Tribe SDK, ABI, callback, descriptor, or v1 completion",
            "tribe leaf accounting does not promote runtime hooks, dispatcher wiring, identity, lookup, arrays, strings, object references, mutation, return override, or ResourceHandle",
            "tribe leaf accounting keeps scalar permission/control evidence separate from blocked array and string payload work",
        ],
    }


def validate_public_contracts(
    surface: dict[str, Any],
    leaves: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
    excluded_route: bool,
) -> None:
    surface_contract = public_contract(surface)
    if excluded_route and surface_contract:
        add(blockers, "excluded_surface_public_contract_not_empty", "$.surface.public_contract")
    for claim in forbidden_claims("\n".join(surface_contract)):
        add(blockers, "public_contract_forbidden_claim", "$.surface.public_contract", claim=claim)
    for leaf_id, leaf in leaves.items():
        contract = public_contract(leaf)
        if excluded_route and contract:
            add(blockers, "excluded_leaf_public_contract_not_empty", f"$.leaf_decision_units[{leaf_id}].public_contract", leaf=leaf_id)
        for claim in forbidden_claims("\n".join(contract)):
            add(blockers, "leaf_public_contract_forbidden_claim", f"$.leaf_decision_units[{leaf_id}].public_contract", leaf=leaf_id, claim=claim)


def leaf_accounted_by(route: str, leaf_id: str, leaf: dict[str, Any], outcome: dict[str, Any]) -> str | None:
    if route == "per_leaf_promoted" and leaf.get("status") == "promoted":
        return "promoted_leaf_evidence"
    if route == "manifest_umbrella_excluded" and leaf.get("status") == "excluded":
        return "manifest_leaf_exclusion"
    if route == "release_statement_umbrella_excluded" and outcome["leaf_exclusions"].get(leaf_id):
        return "release_statement_leaf_exclusion"
    if leaf.get("status") == "excluded":
        return "manifest_leaf_exclusion_pending_acceptance"
    if outcome["leaf_exclusions"].get(leaf_id):
        return "release_statement_leaf_exclusion_pending_acceptance"
    return None


def build_leaf_family_accounting(
    surface: dict[str, Any],
    leaves: dict[str, dict[str, Any]],
    outcome: dict[str, Any],
    route: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    gaps: dict[str, Any] = {}
    missing_leaf_families: list[str] = []
    non_promoted_leaf_families: list[str] = []
    missing_public_gate_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    surface_evidence = surface.get("evidence") if isinstance(surface.get("evidence"), dict) else {}
    planning_target_sets = string_list(surface_evidence.get("planning_target_sets") if isinstance(surface_evidence, dict) else None)

    for leaf_id in REQUIRED_LEAVES:
        leaf = leaves.get(leaf_id, {})
        status = leaf.get("status") if isinstance(leaf.get("status"), str) else "missing"
        status_counts[status] = status_counts.get(status, 0) + 1
        accounted_by = leaf_accounted_by(route, leaf_id, leaf, outcome)
        missing_public_gates = list(LEAF_MISSING_PUBLIC_GATES.get(leaf_id, ()))
        if not accounted_by:
            missing_leaf_families.append(leaf_id)
        if status != "promoted":
            non_promoted_leaf_families.append(leaf_id)
        missing_public_gate_counts[leaf_id] = 0 if accounted_by == "promoted_leaf_evidence" else len(missing_public_gates)
        gaps[leaf_id] = {
            "status": status,
            "v1_accounted": accounted_by is not None,
            "accounted_by": accounted_by,
            "release_statement_excluded": bool(outcome["leaf_exclusions"].get(leaf_id)),
            "release_statement_promoted": bool(outcome["leaf_promotions"].get(leaf_id)),
            "current_evidence": string_list(leaf.get("current_evidence")),
            "current_blocker": leaf.get("current_blocker") if isinstance(leaf.get("current_blocker"), str) else None,
            "allowed_v1_outcome": leaf.get("allowed_v1_outcome") if isinstance(leaf.get("allowed_v1_outcome"), str) else None,
            "missing_public_gates": [] if accounted_by == "promoted_leaf_evidence" else missing_public_gates,
        }

    missing_gate_catalog = sorted(set(REQUIRED_LEAVES) - set(LEAF_MISSING_PUBLIC_GATES))
    if missing_gate_catalog:
        add(blockers, "leaf_family_missing_gate_catalog", "$.checker.leaf_family_accounting", missing=missing_gate_catalog)

    return {
        "mode": route,
        "result": "all_leaf_families_accounted" if not missing_leaf_families else "leaf_families_missing_v1_outcomes",
        "accepted_for_internal_planning": route == "candidate_only" and not blockers,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": route == "per_leaf_promoted" and not blockers,
        "planning_target_sets": planning_target_sets,
        "missing_leaf_families": missing_leaf_families,
        "non_promoted_leaf_families": non_promoted_leaf_families,
        "missing_public_gate_counts": missing_public_gate_counts,
        "status_counts": status_counts,
        "leaf_family_gaps": gaps,
        "guardrail": (
            "candidate-only accounting names missing leaf outcomes and public gates; "
            "it does not promote public SDK, runtime, identity, lookup, mutation, return override, ResourceHandle, or teleport/spawn"
        ),
    }


def validate_leaf_priority_profiles(blockers: list[dict[str, Any]]) -> None:
    observed = set(LEAF_PRIORITY_PROFILES)
    required = set(REQUIRED_LEAVES)
    if observed != required:
        add(
            blockers,
            "leaf_priority_profiles_mismatch",
            "$.checker.leaf_priority_profiles",
            missing=sorted(required - observed),
            extra=sorted(observed - required),
        )
    for leaf_id, profile in LEAF_PRIORITY_PROFILES.items():
        if not isinstance(profile.get("base_score"), int):
            add(blockers, "leaf_priority_base_score_missing", f"$.checker.leaf_priority_profiles[{leaf_id}].base_score")
        for key in ("required_evidence", "reusable_evidence", "blocking_risk"):
            values = profile.get(key)
            if not isinstance(values, tuple) or not all(isinstance(item, str) and item for item in values):
                add(blockers, "leaf_priority_profile_list_invalid", f"$.checker.leaf_priority_profiles[{leaf_id}].{key}")
        if not isinstance(profile.get("next_v1_reuse_step"), str) or not profile["next_v1_reuse_step"]:
            add(blockers, "leaf_priority_next_step_missing", f"$.checker.leaf_priority_profiles[{leaf_id}].next_v1_reuse_step")


def build_leaf_priority(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    validate_leaf_priority_profiles(blockers)
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    if not isinstance(gaps, dict):
        gaps = {}

    ranked: list[dict[str, Any]] = []
    for leaf_id in REQUIRED_LEAVES:
        if leaf_id not in leaves:
            continue
        leaf = leaves[leaf_id]
        profile = LEAF_PRIORITY_PROFILES.get(leaf_id, {})
        current_evidence = string_list(leaf.get("current_evidence"))
        missing_required_evidence = sorted(set(profile.get("required_evidence", ())) - set(current_evidence))
        if missing_required_evidence:
            add(
                blockers,
                "leaf_priority_required_evidence_missing",
                f"$.leaf_decision_units[{leaf_id}].current_evidence",
                leaf=leaf_id,
                missing=missing_required_evidence,
            )
        gap = gaps.get(leaf_id) if isinstance(gaps.get(leaf_id), dict) else {}
        missing_public_gates = string_list(gap.get("missing_public_gates"))
        score = int(profile.get("base_score", 0)) + (2 * len(current_evidence)) - len(missing_public_gates)
        ranked.append(
            {
                "leaf": leaf_id,
                "priority_score": score,
                "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
                "current_evidence": current_evidence,
                "reusable_evidence": list(profile.get("reusable_evidence", ())),
                "blocking_risk": list(profile.get("blocking_risk", ())),
                "missing_public_gate_count": len(missing_public_gates),
                "v1_accounted": bool(gap.get("v1_accounted")),
                "public_sdk_ready": False,
                "runtime_ready": False,
                "promotion_ready": False,
                "next_v1_reuse_step": profile.get("next_v1_reuse_step"),
            }
        )

    ranked.sort(key=lambda item: (-item["priority_score"], REQUIRED_LEAVES.index(item["leaf"])))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    recommended = ranked[0]["leaf"] if ranked else None
    return {
        "schema": "obelisk.mission-transfer-dino-tribe-v1-leaf-priority.v1",
        "recommended_leaf": recommended,
        "recommended_scope": "internal_reusable_evidence_only" if recommended else None,
        "basis": (
            "Scores reward focused copied-scalar/checker evidence and penalize unresolved "
            "public SDK, runtime, identity, lookup, payload, mutation, return-override, "
            "ResourceHandle, and teleport/spawn gates."
        ),
        "ranked_leaves": ranked,
        "non_claims": [
            "leaf priority does not promote a public SDK or runtime observer",
            "leaf priority does not add identity, lookup, mutation, return override, ResourceHandle, teleport/spawn, or payload ownership",
        ],
    }


def build_report(
    manifest_path: Path,
    split_note_path: Path,
    release_statement_path: Path | None = None,
    tribe_snapshot_root: Path = DEFAULT_TRIBE_SCALAR_SNAPSHOT_ROOT,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    manifest = load_json(manifest_path, "manifest")
    split_note = read_optional(split_note_path, "split_note")
    release_statement = read_optional(release_statement_path, "release_statement")
    validate_split_note(split_note, blockers)

    if manifest.get("schema") != "obelisk.public-sdk-surfaces.v1":
        add(blockers, "manifest_schema_mismatch", "$.schema")
    surface = surface_by_id(manifest, SURFACE_ID)
    if surface is None:
        add(blockers, "surface_missing", "$.surfaces")
        surface = {"id": SURFACE_ID, "leaf_decision_units": []}
    leaves = leaf_map(surface, blockers)
    outcome = release_statement_outcome(release_statement)
    for leaf_id in REQUIRED_LEAVES:
        validate_candidate_leaf_evidence(surface, leaf_id, leaves.get(leaf_id, {}), blockers)

    manifest_umbrella_excluded = surface.get("status") == "excluded" and all(
        leaves.get(leaf_id, {}).get("status") == "excluded" for leaf_id in REQUIRED_LEAVES
    )
    statement_umbrella_excluded = outcome["present"] and outcome["umbrella_excluded"] and all(
        outcome["leaf_exclusions"].get(leaf_id) for leaf_id in REQUIRED_LEAVES
    )
    all_promoted = validate_promoted_leaf_evidence(surface, leaves, blockers, manifest_dir=manifest_path.parent)

    if outcome["forbidden_claims"]:
        add(
            blockers,
            "release_statement_forbidden_claims",
            "$.release_statement",
            claims=outcome["forbidden_claims"],
        )
    if outcome["present"] and not statement_umbrella_excluded and not all_promoted:
        missing = [leaf_id for leaf_id in REQUIRED_LEAVES if not outcome["leaf_exclusions"].get(leaf_id)]
        if not outcome["umbrella_excluded"]:
            add(blockers, "release_statement_umbrella_exclusion_missing", "$.release_statement", surface=SURFACE_ID)
        if missing:
            add(blockers, "release_statement_leaf_exclusions_missing", "$.release_statement", missing=missing)
    if surface.get("status") == "excluded" and not manifest_umbrella_excluded:
        add(blockers, "manifest_excluded_route_missing_leaf_exclusions", "$.leaf_decision_units")

    tribe_scalar_boundary_report = build_tribe_scalar_boundary_report(tribe_snapshot_root)
    validate_tribe_scalar_boundary_report(tribe_scalar_boundary_report, blockers)

    excluded_route = manifest_umbrella_excluded or statement_umbrella_excluded
    validate_public_contracts(surface, leaves, blockers, excluded_route=excluded_route)

    if all_promoted:
        route = "per_leaf_promoted"
    elif statement_umbrella_excluded:
        route = "release_statement_umbrella_excluded"
    elif manifest_umbrella_excluded:
        route = "manifest_umbrella_excluded"
    else:
        route = "candidate_only"
    leaf_family_accounting = build_leaf_family_accounting(surface, leaves, outcome, route, blockers)
    leaf_priority = build_leaf_priority(leaves, leaf_family_accounting, blockers)
    mission_leaf_blocker_accounting = build_mission_leaf_blocker_accounting(leaves, leaf_family_accounting)
    tribe_leaf_blocker_accounting = build_tribe_leaf_blocker_accounting(
        leaves,
        leaf_family_accounting,
        tribe_scalar_boundary_report,
    )

    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE_ID,
        "ready": not blockers,
        "accounting_route": route,
        "v1_accounted": route in {"release_statement_umbrella_excluded", "manifest_umbrella_excluded", "per_leaf_promoted"},
        "candidate_only": route == "candidate_only",
        "promotion_ready": all_promoted and not blockers,
        "public_sdk_ready": all_promoted and not blockers,
        "runtime_ready": all_promoted and not blockers,
        "required_leaves": list(REQUIRED_LEAVES),
        "observed_leaves": [leaf_id for leaf_id in REQUIRED_LEAVES if leaf_id in leaves],
        "leaf_statuses": {leaf_id: leaves.get(leaf_id, {}).get("status") for leaf_id in REQUIRED_LEAVES},
        "candidate_only_accounting": leaf_family_accounting,
        "mission_leaf_blocker_accounting": mission_leaf_blocker_accounting,
        "tribe_leaf_blocker_accounting": tribe_leaf_blocker_accounting,
        "leaf_priority": leaf_priority,
        "missing_leaf_families": leaf_family_accounting["missing_leaf_families"],
        "release_statement": outcome,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "candidate-only accounting does not add Mission, Transfer, Dino, Tribe, or Buff APIs",
            "candidate-only accounting does not add identity, lookup, mutation, return override, runtime hook, ResourceHandle, teleport/spawn, ownership lookup, or cross-map correlation",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.manifest, args.split_note, args.release_statement, args.tribe_snapshot_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["ready"]:
        print(f"{SURFACE_ID}: {report['accounting_route']} accounting accepted")
    else:
        for blocker in report["blocker_details"]:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
