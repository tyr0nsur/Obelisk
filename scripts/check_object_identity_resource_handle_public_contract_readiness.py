#!/usr/bin/env python3
"""Validate that object identity and ResourceHandle stay blocked from the public SDK."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component  # noqa: E402


REPORT_SCHEMA = "obelisk.object-identity-resource-handle-public-contract-readiness-check.v1"
DECISIONS_SCHEMA = "obelisk.object-identity-resource-handle-public-contract-decisions.v1"
SURFACE_ID = "obelisk.object_identity_resource_handle.v1"
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "object_identity_resource_handle_public_contract_decisions.json"
DEFAULT_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_EVENTS = REPO_ROOT / "docs" / "public_gameplay_events.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REQUIRED_FALSE_KEYS = (
    "public_header_allowed",
    "public_contract_allowed",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_resource_handle_ready",
    "post_callback_resource_handle_ready",
    "serialPolicyReady",
    "resourceLookupReady",
    "postCallbackHandleReady",
    "objectIdentityReady",
    "runtimeSampleReady",
    "runtimeRejectedObjectSamplesReady",
    "lookupPrivacyReady",
    "lifetimeSemanticsReady",
    "resourceHandleLifetimeSemanticsReady",
    "offline_artifacts_unlock_public_lookup_identity_runtime_sdk",
)
REQUIRED_STRICT_NEXT_BLOCKER = (
    "runtime rejected object samples, runtime serial reuse/wraparound semantics, "
    "lookup privacy, and ResourceHandle lifetime semantics under future approved "
    "live-ops brief"
)
REQUIRED_OFFLINE_ARTIFACT_POLICY = "candidate-only"
REQUIRED_PUBLIC_PROMOTION_BLOCKERS = (
    "runtime rejected object samples",
    "runtime serial reuse/wraparound semantics",
    "lookup privacy boundary",
    "ResourceHandle lifetime semantics",
)
REQUIRED_NEXT_EVIDENCE = (
    *REQUIRED_PUBLIC_PROMOTION_BLOCKERS,
    "post-callback lookup safety and fail-closed handle invalidation",
)
REQUIRED_SURFACE_NEXT_EVIDENCE = (
    "runtime object negative samples",
    "runtime serial reuse/wraparound semantics",
    "post-callback lookup safety and fail-closed handle invalidation",
)
REQUIRED_DESCRIPTOR_FLAGS = (
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
)
REQUIRED_NON_CLAIMS = (
    "no public ResourceHandle ABI",
    "no public object identity ABI",
    "no public object lookup ABI",
    "no post-callback object correlation",
    "no public lookup privacy model",
    "no public ResourceHandle lifetime semantics",
    "runtime rejected object samples remain missing",
    "serial reuse and wraparound semantics remain missing",
    "candidate-only serial-policy artifacts do not imply readiness",
    "offline zero-serial cohorts do not imply runtime readiness",
    "copied resource_kind descriptors do not imply lookup or identity",
    "scoped release statements do not authorize public ResourceHandle readiness",
    "runtime evidence authorization and status aliases do not imply readiness",
    "category-only resource_kind metadata is not identity",
    "copied events do not imply object identity",
)
FORBIDDEN_HEADER_SYMBOL_RE = re.compile(
    r"\b(?:"
    r"OBELISK_API_CAPABILITY_(?:RESOURCE_HANDLE|OBJECT_IDENTITY|OBJECT_LOOKUP)|"
    r"OBELISK_[A-Z0-9_]*(?:RESOURCE_HANDLE|OBJECT_IDENTITY|OBJECT_LOOKUP)[A-Z0-9_]*|"
    r"Obelisk(?:ResourceHandle|ObjectIdentity|ObjectLookup)[A-Za-z0-9_]*|"
    r"(?:Resolve|Lookup)[A-Za-z0-9_]*(?:Resource|Object|UObject)|"
    r"UObject|FName|GObjects"
    r")\b"
)
FORBIDDEN_PUBLIC_EVENT_TERMS = (
    "ObeliskResourceHandle",
    "ObeliskObjectIdentity",
    "ObeliskObjectLookup",
    "OBELISK_API_CAPABILITY_RESOURCE_HANDLE",
    "post-callback object handle API is included",
    "object lookup API is included",
)
FORBIDDEN_TRUE_KEYS = (
    "promotion_ready",
    "public_abi_ready",
    "public_sdk_ready",
    "release_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "v1_sdk_ready",
    "object_identity_ready",
    "post_callback_resource_handle_ready",
    "postCallbackHandleReady",
    "public_object_identity_ready",
    "public_object_lookup_ready",
    "public_resource_handle_ready",
    "resourceLookupReady",
    "resource_handle_ready",
    "runtime_rejected_object_samples_ready",
    "runtimeRejectedObjectSamplesReady",
    "runtime_object_negative_samples_ready",
    "runtimeSampleReady",
    "serial_reuse_ready",
    "serial_wraparound_ready",
    "serialPolicyReady",
    "lookup_privacy_ready",
    "lookupPrivacyReady",
    "lookup_privacy_boundary_ready",
    "lookupPrivacyBoundaryReady",
    "privacy_boundary_ready",
    "privacyBoundaryReady",
    "public_lookup_privacy_ready",
    "publicLookupPrivacyReady",
    "lifetime_semantics_ready",
    "lifetimeSemanticsReady",
    "resource_handle_lifetime_semantics_ready",
    "resourceHandleLifetimeSemanticsReady",
    "resource_handle_lifetime_ready",
    "resourceHandleLifetimeReady",
    "handle_lifetime_ready",
    "handleLifetimeReady",
    "objectIdentityReady",
    "post_callback_lookup_safety_ready",
    "post_callback_object_validity_ready",
    "post_callback_validity_ready",
)
FORBIDDEN_READY_VALUE_KEYS = {
    "object_identity",
    "object_lookup",
    "resource_handle",
    "ResourceHandle",
}
FORBIDDEN_ALIAS_SUBJECT_RE = re.compile(
    r"(?:resource_?handle|resourcehandle|resource_?lookup|object_?identity|object_?lookup|object_?handle|"
    r"public_?handle|public_?lookup|sdk_?progress|complete_?sdk|v1_?completion|"
    r"package_?shape|installed_?sdk(?:_?package_?shape)?|cmake_?package|find_?package|"
    r"side_?(?:lane|channel)|planning_?manifest|identity_?owner_?token|owner_?token_?identity|"
    r"route_?accept(?:ance|ed)?|"
    r"package_?support|package_?label|support_?tier|support_?label|support_?status|"
    r"candidate_?only|serial_?policy_?artifact|offline_?artifact|resource_?kind_?descriptor|"
    r"copied_?resource_?kind|copied_?descriptor|scoped_?release|release_?statement|"
    r"runtime_?evidence|evidence_?authori[sz]ation|runtime_?authori[sz]ation|authori[sz]ation_?status|"
    r"runtime_?object|public_?gobjects|gobjects|static_?globals?|strict_?serial|serial_?policy|"
    r"serial_?scan|serial_?reuse|serial_?wraparound|zero_?serial|runtime_?status|runtime_?rejection|runtime_?samples?|"
    r"slot_?reuse|stale_?handle|cross_?frame_?lookup|post_?callback_?lookup|"
    r"post_?callback_?(?:object_?)?validity|callback_?scope|post_?callback_?handle|"
    r"post_?callback_?rejection|source_?helper|flag_?reports?|uobject_?flags?|caller_?rows?|"
    r"lookup_?privacy|privacy_?boundary|"
    r"privacy_?redaction|owner_?scoped_?lookup|owner_?token_?lookup|lookup_?cleanup|"
    r"lifetime_?semantics|resource_?handle_?lifetime|resource_?lifetime|handle_?lifetime|"
    r"invalidation_?semantics|"
    r"weak_?helper|future_?runtime_?observation|runtime_?observation|wraparound)",
    re.IGNORECASE,
)
FORBIDDEN_ALIAS_CONTEXT_RE = re.compile(
    r"(?:public|runtime|v1|sdk|abi|release|promot|ready|readiness|enabled|allowed|available|"
    r"accepted|acceptance|approved|authori[sz]ed|authori[sz]ation|progress|validated|"
    r"status|support|tier|label|"
    r"post_?callback|lookup|identity|samples?|safety|policy|proven|complete|completion|satisfied|"
    r"stable|supported|included|blockers?|gates?)",
    re.IGNORECASE,
)
SURFACE_FORBIDDEN_TERM_RE = re.compile(
    r"(?:resourcehandle|resource[_ -]?handle|resource[_ -]?lookup|object[_ -]?identity|object[_ -]?lookup|"
    r"public[_ -]?handle|public[_ -]?lookup|sdk[_ -]?progress|complete[_ -]?sdk(?:[_ -]?readiness)?|"
    r"package[_ -]?shape|"
    r"installed[_ -]?sdk(?:[_ -]?package[_ -]?shape)?|cmake[_ -]?package|find[_ -]?package|"
    r"side[_ -]?(?:lane|channel)|planning[_ -]?manifest|"
    r"identity[_ -]?owner[_ -]?token|owner[_ -]?token[_ -]?identity|"
    r"route[_ -]?(?:acceptance|accepted)|approved[_ -]?runtime[_ -]?samples?|"
    r"package[_ -]?support|package[_ -]?label|support[_ -]?tier|support[_ -]?label|support[_ -]?status|"
    r"candidate[_ -]?only|serial[_ -]?policy[_ -]?artifact|offline[_ -]?artifact|"
    r"resource[_ -]?kind(?:[_ -]?descriptor)?|copied[_ -]?resource[_ -]?kind|copied[_ -]?descriptor|"
    r"scoped[_ -]?release|release[_ -]?statement|runtime[_ -]?evidence|"
    r"evidence[_ -]?authori[sz]ation|runtime[_ -]?authori[sz]ation|authori[sz]ation[_ -]?status|"
    r"public[_ -]?gobjects|gobjects|static[_ -]?globals?|strict[_ -]?serial|serial[_ -]?policy|"
    r"serial[_ -]?scan|serial[_ -]?reuse|serial[_ -]?wraparound|zero[_ -]?serial|"
    r"runtime[_ -]?status|runtime[_ -]?rejection[_ -]?samples?|"
    r"slot[_ -]?reuse|stale[_ -]?handle|cross[_ -]?frame[_ -]?lookup|"
    r"post[_ -]?callback[_ -]?(?:lookup|(?:object[_ -]?)?validity|safety)|"
    r"post[_ -]?callback[_ -]?rejection[_ -]?contracts?|source[_ -]?helper[_ -]?flags?|"
    r"flag[_ -]?reports?|uobject[_ -]?flags?|caller[_ -]?rows?|"
    r"lookup[_ -]?privacy|privacy[_ -]?boundary|privacy[_ -]?redaction|"
    r"owner[_ -]?scoped[_ -]?lookup|owner[_ -]?token[_ -]?lookup|lookup[_ -]?cleanup|"
    r"lifetime[_ -]?semantics|resource[_ -]?handle[_ -]?lifetime|resource[_ -]?lifetime|"
    r"handle[_ -]?lifetime|invalidation[_ -]?semantics|"
    r"weak[_ -]?helper|future[_ -]?runtime[_ -]?observation|runtime[_ -]?observation[_ -]?plans?|"
    r"post[_ -]?callback[_ -]?object[_ -]?(?:correlation|handle|identity)|"
    r"(?:structure|item|inventory|dino|tribe|buff|mission|transfer|economy|mobility|area[_ -]?policy)[_ -]?handle)",
    re.IGNORECASE,
)
SURFACE_POSITIVE_CLAIM_RE = re.compile(
    r"(?:public[_ -]?sdk|ready|readiness|allowed|available|enabled|included|"
    r"includes?|ships?|part[_ -]?of[_ -]?v1|promoted|promotion|supported|stable|accepted|"
    r"complete|completion|satisf(?:y|ies|ied)|prove[ns]?|lookup[_ -]?api|handle[_ -]?api|"
    r"cleared|resolved|unblocked|unlock(?:s|ed)?|passed|approved|authori[sz]ed|validated|progress)",
    re.IGNORECASE,
)
DESCRIPTOR_SURFACE_IDS = frozenset(
    (
        "obelisk.descriptors.v1",
        "obelisk.resource_kind_descriptors.v1",
        "obelisk.gameplay_policy_event_descriptors.v1",
    )
)
DESCRIPTOR_FORBIDDEN_PUBLIC_CONTRACT_RE = re.compile(
    r"(?:"
    r"\bObelisk(?:ResourceHandle|ObjectIdentity|ObjectLookup)[A-Za-z0-9_]*\b|"
    r"\bOBELISK_API_CAPABILITY_(?:RESOURCE_HANDLE|OBJECT_IDENTITY|OBJECT_LOOKUP)\b|"
    r"\b(?:resourcehandle|resource[_ -]?handle|resource[_ -]?lookup|object[_ -]?identity|object[_ -]?lookup|"
    r"post[_ -]?callback[_ -]?object[_ -]?(?:correlation|handle|identity))\b"
    r")",
    re.IGNORECASE,
)
SURFACE_NEGATED_CLAIM_RE = re.compile(
    r"(?:\bno\b|\bnot\b|must[_ -]?not|cannot|blocked|excluded|post[_ -]?v1|"
    r"without|not[_ -]?included|does[_ -]?not|do[_ -]?not)",
    re.IGNORECASE,
)
SURFACE_UNBLOCKING_NEGATION_RE = re.compile(
    r"(?:not|no[_ -]?longer)\s+(?:blocked|excluded|post[_ -]?v1|deferred)|"
    r"(?:blocked|excluded|post[_ -]?v1)\s*[:=]\s*false",
    re.IGNORECASE,
)
PUBLIC_CONTRACT_FIELD_KEYS = frozenset(
    (
        "public_contract",
        "public_contracts",
        "sdk_contract",
        "sdk_contracts",
        "public_api_contract",
        "public_abi_contract",
        "capability",
        "capabilities",
    )
)
DECISIONS_TEXT_CLAIM_EXEMPT_KEYS = frozenset(("strict_next_blocker",))
SHORTCUT_STATUS_VALUE_EXEMPT_KEYS = frozenset(("release_claim", "strict_next_blocker"))
SHORTCUT_ARTIFACT_FAMILY_PATTERNS = (
    (
        "candidate_serial_policy_artifact",
        re.compile(
            r"(?:candidate(?:_only)?_.*serial_policy|serial_policy_.*candidate|"
            r"serial_policy(?:_artifact|_candidate)?|strict_serial_policy|"
            r"serial_(?:reuse|wraparound)_policy)"
        ),
    ),
    (
        "offline_zero_serial_cohort",
        re.compile(
            r"(?:offline_.*zero_serial|zero_serial_.*offline|"
            r"zero_serial(?:_samples?|_cohorts?|_artifact|_policy)?)"
        ),
    ),
    (
        "copied_resource_kind_descriptor",
        re.compile(
            r"(?:(?:copied|copy|category_only).*resource_kind|"
            r"resource_kind.*(?:copied|copy|descriptor|metadata|category_only)|"
            r"resource_kind_descriptor|copied_descriptor|copied_event_resource_categor(?:y|ies))"
        ),
    ),
    (
        "offline_artifact_gate_acceptance",
        re.compile(
            r"(?:offline_.*artifact_.*gate|artifact_.*gate|gate_.*offline_.*artifact|"
            r"consume_.*gate|gate_.*consume)"
        ),
    ),
    (
        "scoped_release_statement",
        re.compile(
            r"(?:scoped_.*release|release_.*statement|non_complete_.*release|"
            r"complete_sdk_release_statement|scoped_statement|release_scope|release_claim(?:_accounting)?)"
        ),
    ),
    (
        "runtime_evidence_authorization_status",
        re.compile(
            r"(?:runtime_.*evidence|evidence_.*runtime|runtime_.*authori[sz]|authori[sz].*runtime|"
            r"evidence_.*authori[sz]|authori[sz].*evidence|runtime_capture|isolated_runtime_capture|"
            r"approved_runtime_samples?|runtime_samples?_authori[sz]ation|runtime_status_alias|"
            r"runtime_rejected_object_samples|runtime_object_negative_samples)"
        ),
    ),
)
SHORTCUT_PROMOTION_ALIAS_KEY_RE = re.compile(
    r"(?:^|_)(?:"
    r"status|support_tier|ready|readiness|accepted|acceptance|approved|approval|"
    r"authorized|authorization|allowed|enabled|available|promoted|promotion|validated|"
    r"complete|completion|claim_allowed|evidence_complete|promotion_evidence_complete|"
    r"public_promotion_evidence_counting_allowed|complete_sdk_counting_allowed|"
    r"counts_toward_public_promotion|counts_toward_complete_sdk_claim|"
    r"accepted_public_promotion_evidence_count|public_promotion_evidence_count|"
    r"accepted_evidence_count|sdk_progress|complete_sdk_progress|v1_completion_progress|"
    r"v1_completion_required|release_ready|runtime_ready|public_sdk_ready|public_abi_ready|"
    r"lookup_ready|identity_ready|handle_ready"
    r")(?:_|$)"
)
SHORTCUT_POSITIVE_VALUE_RE = re.compile(
    r"(?:^|_)(?:accepted|approved|authorized|available|cleared|complete|enabled|included|"
    r"passed|promoted|proven|ready|resolved|satisfied|stable|supported|unblocked|"
    r"unlocked|validated|yes|true)(?:_|$)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--surfaces", type=Path, default=DEFAULT_SURFACES)
    parser.add_argument("--public-events", type=Path, default=DEFAULT_PUBLIC_EVENTS)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def safe_input_path(path: Path, label: str) -> Path:
    reject_symlink_component(path, label)
    return reject_protected_input_path(path, label)


def load_json(path: Path, label: str) -> Any:
    resolved = safe_input_path(path, label)
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise SystemExit(f"{label} is unreadable: {exc}") from exc


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//.*", "", text)
    return text


def positive_claim(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.casefold() in {
            "accepted",
            "allowed",
            "approved",
            "authorized",
            "available",
            "complete",
            "enabled",
            "included",
            "live",
            "promoted",
            "proven",
            "cleared",
            "resolved",
            "ready",
            "satisfied",
            "stable",
            "supported",
            "true",
            "unblocked",
            "unlocked",
            "passed",
            "validated",
            "yes",
        }
    return False


def normalized_claim_key(key: str) -> str:
    key = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return re.sub(r"[^a-zA-Z0-9]+", "_", key).strip("_").casefold()


def forbidden_positive_alias_key(key: str) -> bool:
    normalized = normalized_claim_key(key)
    return bool(FORBIDDEN_ALIAS_SUBJECT_RE.search(normalized) and FORBIDDEN_ALIAS_CONTEXT_RE.search(normalized))


def primitive_context_value(value: Any) -> str:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return ""


def shortcut_artifact_family(trail: str, key: str, value: Any, *, include_value: bool = True) -> str | None:
    parts = (trail, key, primitive_context_value(value)) if include_value else (trail, key)
    context = normalized_claim_key(" ".join(parts))
    for family, pattern in SHORTCUT_ARTIFACT_FAMILY_PATTERNS:
        if pattern.search(context):
            return family
    return None


def shortcut_promotion_alias_key(key: str) -> bool:
    return SHORTCUT_PROMOTION_ALIAS_KEY_RE.search(normalized_claim_key(key)) is not None


def positive_shortcut_claim(value: Any) -> bool:
    if positive_claim(value):
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    if isinstance(value, str):
        return SHORTCUT_POSITIVE_VALUE_RE.search(normalized_claim_key(value)) is not None
    return False


def walk_shortcut_artifact_claims(
    value: Any,
    blockers: list[str],
    trail: str,
    blocker_prefix: str,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            family = shortcut_artifact_family(trail, key_text, child)
            family_from_path = shortcut_artifact_family(trail, key_text, child, include_value=False)
            shortcut_status_value = (
                family_from_path is not None
                and normalized_claim_key(key_text) not in SHORTCUT_STATUS_VALUE_EXEMPT_KEYS
                and isinstance(child, str)
                and positive_shortcut_claim(child)
            )
            if family and (
                (shortcut_promotion_alias_key(key_text) and positive_shortcut_claim(child))
                or shortcut_status_value
            ):
                blockers.append(f"{blocker_prefix}:{family}:{trail}.{key_text}")
            walk_shortcut_artifact_claims(child, blockers, f"{trail}.{key_text}", blocker_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_shortcut_artifact_claims(child, blockers, f"{trail}[{index}]", blocker_prefix)


def walk_claims(value: Any, blockers: list[str], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_TRUE_KEYS and positive_claim(child):
                blockers.append(f"forbidden_positive_resource_handle_claim:{trail}.{key}")
            if key in FORBIDDEN_READY_VALUE_KEYS and positive_claim(child):
                blockers.append(f"forbidden_positive_resource_handle_claim:{trail}.{key}")
            if forbidden_positive_alias_key(str(key)) and positive_claim(child):
                blockers.append(f"forbidden_positive_resource_handle_claim:{trail}.{key}")
            walk_claims(child, blockers, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_claims(child, blockers, f"{trail}[{index}]")


def positive_surface_text_claim(text: str) -> bool:
    if not SURFACE_FORBIDDEN_TERM_RE.search(text):
        return False
    if not SURFACE_POSITIVE_CLAIM_RE.search(text):
        return False
    if SURFACE_NEGATED_CLAIM_RE.search(text) and not SURFACE_UNBLOCKING_NEGATION_RE.search(text):
        return False
    return True


def walk_text_claims(value: Any, blockers: list[str], trail: str, blocker_prefix: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            walk_text_claims(child, blockers, f"{trail}.{key}", blocker_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_text_claims(child, blockers, f"{trail}[{index}]", blocker_prefix)
    elif isinstance(value, str):
        for clause_index, clause in enumerate(re.split(r"[.;\n]+", value)):
            normalized = clause.strip()
            if normalized and positive_surface_text_claim(normalized):
                blockers.append(f"{blocker_prefix}:{trail}[clause:{clause_index}]")


def walk_surface_text_claims(value: Any, blockers: list[str], trail: str) -> None:
    walk_text_claims(value, blockers, trail, "surface_positive_resource_handle_claim")


def walk_decisions_text_claims(value: Any, blockers: list[str], trail: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text in DECISIONS_TEXT_CLAIM_EXEMPT_KEYS:
                continue
            walk_decisions_text_claims(child, blockers, f"{trail}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_decisions_text_claims(child, blockers, f"{trail}[{index}]")
    elif isinstance(value, str):
        for clause_index, clause in enumerate(re.split(r"[.;\n]+", value)):
            normalized = clause.strip()
            if normalized and positive_surface_text_claim(normalized):
                blockers.append(f"decisions_positive_resource_handle_claim:{trail}[clause:{clause_index}]")


def walk_public_event_text_claims(value: Any, blockers: list[str], trail: str) -> None:
    walk_text_claims(value, blockers, trail, "public_events_positive_resource_handle_claim")


def value_contains_forbidden_public_contract(value: Any) -> bool:
    if isinstance(value, str):
        return DESCRIPTOR_FORBIDDEN_PUBLIC_CONTRACT_RE.search(value) is not None
    if isinstance(value, dict):
        return any(value_contains_forbidden_public_contract(child) for child in value.values())
    if isinstance(value, list):
        return any(value_contains_forbidden_public_contract(child) for child in value)
    return False


def walk_public_contract_fields(value: Any, blockers: list[str], trail: str, blocker_prefix: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if (
                normalized_claim_key(key_text) in PUBLIC_CONTRACT_FIELD_KEYS
                and value_contains_forbidden_public_contract(child)
            ):
                blockers.append(f"{blocker_prefix}:{trail}.{key_text}")
            walk_public_contract_fields(child, blockers, f"{trail}.{key_text}", blocker_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_public_contract_fields(child, blockers, f"{trail}[{index}]", blocker_prefix)


def surface_entry(surfaces: Any, blockers: list[str]) -> dict[str, Any] | None:
    entries = surfaces.get("surfaces") if isinstance(surfaces, dict) else None
    if not isinstance(entries, list):
        blockers.append("public_sdk_surfaces_missing_surfaces_list")
        return None
    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("id") == SURFACE_ID]
    if len(matches) != 1:
        blockers.append("object_identity_resource_handle_surface_missing_or_duplicate")
        return None
    return matches[0]


def build_next_evidence_contract() -> dict[str, Any]:
    return {
        "status": "planning-only-not-approval",
        "required_future_evidence": list(REQUIRED_NEXT_EVIDENCE),
        "offline_artifacts_policy": REQUIRED_OFFLINE_ARTIFACT_POLICY,
        "counts_toward_public_promotion": False,
        "counts_toward_complete_sdk_claim": False,
        "non_claim": (
            "Next evidence fields document the future ResourceHandle blocker only; "
            "they do not approve lookup, lookup privacy, lifetime semantics, mutation, "
            "cross-event identity, persistent object identity, post-callback validity, "
            "runtime work, or public SDK readiness."
        ),
    }


def build_missing_evidence_report() -> dict[str, Any]:
    return {
        "status": "blocked",
        "accepted_public_promotion_evidence_count": 0,
        "counts_toward_public_promotion": False,
        "counts_toward_complete_sdk_claim": False,
        "candidate_artifacts_policy": REQUIRED_OFFLINE_ARTIFACT_POLICY,
        "missing_evidence": [
            {
                "id": "runtime_object_negative_samples",
                "ready": False,
                "counts_toward_public_promotion": False,
                "requires": [
                    "approved isolated runtime capture or equivalent independent validation path",
                    "rejected object-present rows with bounded copied reason categories",
                    "artifact identity bound to binary hash, Obelisk commit, capture id, and evidence pack id",
                ],
                "not_sufficient": [
                    "offline zero-serial cohorts",
                    "static GObjects/FUObjectItem scans",
                    "source helper flag polarity",
                ],
            },
            {
                "id": "serial_reuse_wraparound_semantics",
                "ready": False,
                "counts_toward_public_promotion": False,
                "requires": [
                    "slot reuse behavior for stale {index, serial} pairs",
                    "serial mismatch rejection and zero-serial rejection policy",
                    "wraparound-unknown handling that rejects instead of resolving public handles",
                    "same-frame nonzero-match rows scoped to candidate frame-local use only",
                ],
                "not_sufficient": [
                    "nonzero serial samples from copied cores",
                    "a strict serial policy without runtime reuse or wraparound semantics",
                ],
            },
            {
                "id": "lookup_privacy_boundary",
                "ready": False,
                "counts_toward_public_promotion": False,
                "requires": [
                    "owner-token and plugin-scope privacy rule before any public lookup path can exist",
                    "redacted, non-enumerating failure categories that do not leak raw UObject, FName, or GObjects state",
                    "proof that category-only resource_kind metadata cannot be used as object discovery or lookup input",
                ],
                "not_sufficient": [
                    "operator-only notes or release wording",
                    "static object/global scans",
                    "copied event resource categories",
                ],
            },
            {
                "id": "resource_handle_lifetime_semantics",
                "ready": False,
                "counts_toward_public_promotion": False,
                "requires": [
                    "callback-local versus post-callback lifetime rule for every UObject-backed handle",
                    "fail-closed invalidation after object destruction, serial mismatch, callback return, and plugin unload",
                    "owner-token scoped cleanup model with no persistent or cross-process handle reuse",
                ],
                "not_sufficient": [
                    "same-frame raw pointer observations",
                    "nonzero serial samples without stale-handle rejection semantics",
                    "copied payload ownership for scalar events",
                ],
            },
            {
                "id": "post_callback_lookup_safety",
                "ready": False,
                "counts_toward_public_promotion": False,
                "requires": [
                    "callback-local versus post-callback validity rule for UObject-backed handles",
                    "fail-closed lookup for stale, destroyed, flag-rejected, serial-mismatched, and out-of-range handles",
                    "owner-token scoped cleanup after callback return and plugin unload",
                    "public ABI tests proving no raw UObject, FName, GObjects, mutation, or return override exposure",
                ],
                "not_sufficient": [
                    "copied event payloads",
                    "category-only resource_kind descriptors",
                    "callback-local raw pointer observations",
                ],
            },
        ],
    }


def validate_next_evidence_contract(contract: dict[str, Any], blockers: list[str]) -> None:
    next_contract = contract.get("next_evidence_contract")
    if not isinstance(next_contract, dict):
        blockers.append("surface_next_evidence_contract_missing")
        return
    if next_contract.get("status") != "planning-only-not-approval":
        blockers.append("surface_next_evidence_contract_status_not_planning_only")
    required = next_contract.get("required_future_evidence")
    if not isinstance(required, list):
        blockers.append("surface_next_evidence_contract_required_future_evidence_missing")
    else:
        missing = [item for item in REQUIRED_SURFACE_NEXT_EVIDENCE if item not in required]
        if missing:
            blockers.append("surface_next_evidence_contract_required_future_evidence_incomplete")
    if next_contract.get("offline_artifacts_policy") != REQUIRED_OFFLINE_ARTIFACT_POLICY:
        blockers.append("surface_next_evidence_contract_offline_artifacts_policy_not_candidate_only")
    if next_contract.get("counts_toward_public_promotion") is not False:
        blockers.append("surface_next_evidence_contract_counts_toward_public_promotion_not_false")
    if next_contract.get("counts_toward_complete_sdk_claim") is not False:
        blockers.append("surface_next_evidence_contract_counts_toward_complete_sdk_claim_not_false")
    non_claim = str(next_contract.get("non_claim", ""))
    required_non_claim_terms = (
        "does not approve lookup",
        "persistent object identity",
        "post-callback validity",
        "public SDK readiness",
    )
    if not all(term in non_claim for term in required_non_claim_terms):
        blockers.append("surface_next_evidence_contract_non_claim_incomplete")


def validate_decisions(decisions: Any, blockers: list[str]) -> None:
    if not isinstance(decisions, dict):
        blockers.append("decisions_not_object")
        return
    if decisions.get("schema") != DECISIONS_SCHEMA:
        blockers.append("decisions_schema_mismatch")
    if decisions.get("surface_id") != SURFACE_ID:
        blockers.append("decisions_surface_id_mismatch")
    if decisions.get("status") != "blocked":
        blockers.append("decisions_status_not_blocked")
    if decisions.get("support_tier") != "blocked":
        blockers.append("decisions_support_tier_not_blocked")
    for key in REQUIRED_FALSE_KEYS:
        if decisions.get(key) is not False:
            blockers.append(f"{key}_not_false")
    if decisions.get("required_public_sdk_surface_status") != "post-v1":
        blockers.append("required_public_sdk_surface_status_not_post_v1")
    if decisions.get("required_public_sdk_surface_support_tier") != "blocked":
        blockers.append("required_public_sdk_surface_support_tier_not_blocked")
    if decisions.get("required_public_contract") != []:
        blockers.append("required_public_contract_not_empty")
    if decisions.get("strict_next_blocker") != REQUIRED_STRICT_NEXT_BLOCKER:
        blockers.append("strict_next_blocker_not_runtime_samples_serial_privacy_lifetime")
    if decisions.get("offline_serial_post_callback_artifacts") != REQUIRED_OFFLINE_ARTIFACT_POLICY:
        blockers.append("offline_serial_post_callback_artifacts_not_candidate_only")
    promotion_blockers = decisions.get("required_public_promotion_blockers")
    if not isinstance(promotion_blockers, list):
        blockers.append("required_public_promotion_blockers_missing")
    else:
        missing = [item for item in REQUIRED_PUBLIC_PROMOTION_BLOCKERS if item not in promotion_blockers]
        if missing:
            blockers.append("required_public_promotion_blockers_incomplete")
    flags = decisions.get("required_resource_kind_descriptor_flags")
    if not isinstance(flags, list) or set(REQUIRED_DESCRIPTOR_FLAGS) - set(flags):
        blockers.append("required_resource_kind_descriptor_flags_missing")
    non_claims = decisions.get("non_claims")
    if not isinstance(non_claims, list):
        blockers.append("non_claims_missing")
    else:
        missing = [claim for claim in REQUIRED_NON_CLAIMS if claim not in non_claims]
        if missing:
            blockers.append("required_non_claims_missing")
    walk_claims(decisions, blockers, "$.decisions")
    walk_decisions_text_claims(decisions, blockers, "$.decisions")
    walk_shortcut_artifact_claims(
        decisions,
        blockers,
        "$.decisions",
        "decisions_shortcut_artifact_public_readiness_claim",
    )
    walk_public_contract_fields(
        decisions,
        blockers,
        "$.decisions",
        "decisions_forbidden_public_contract_field",
    )


def validate_surface(surfaces: Any, blockers: list[str]) -> None:
    entry = surface_entry(surfaces, blockers)
    if entry is None:
        return
    if entry.get("status") != "post-v1":
        blockers.append("surface_status_not_post_v1")
    if entry.get("support_tier") != "blocked":
        blockers.append("surface_support_tier_not_blocked")
    if entry.get("public_contract") != []:
        blockers.append("surface_public_contract_not_empty")
    contract = entry.get("v1_decision_contract")
    if not isinstance(contract, dict):
        blockers.append("surface_v1_decision_contract_missing")
    else:
        if contract.get("must_remain_without_public_contract_until_promotion") is not True:
            blockers.append("surface_must_remain_without_public_contract_missing")
        validate_next_evidence_contract(contract, blockers)
    blockers_text = "\n".join(str(item) for item in entry.get("blockers", []))
    if "No dedicated tested checker" in blockers_text:
        blockers.append("surface_blockers_still_say_dedicated_checker_missing")
    required_terms = ("ResourceHandle", "object identity", "lookup", "post-callback")
    evidence_text = json.dumps(entry.get("evidence", {}), sort_keys=True)
    for term in required_terms:
        if term not in blockers_text and term not in evidence_text:
            blockers.append(f"surface_missing_boundary_term:{term}")
    walk_claims(entry, blockers, f"$.surfaces[{SURFACE_ID}]")
    walk_surface_text_claims(entry, blockers, f"$.surfaces[{SURFACE_ID}]")
    walk_shortcut_artifact_claims(
        entry,
        blockers,
        f"$.surfaces[{SURFACE_ID}]",
        "surface_shortcut_artifact_public_readiness_claim",
    )
    walk_public_contract_fields(
        entry,
        blockers,
        f"$.surfaces[{SURFACE_ID}]",
        "surface_forbidden_public_contract_field",
    )


def validate_promoted_descriptor_surfaces(surfaces: Any, blockers: list[str]) -> None:
    entries = surfaces.get("surfaces") if isinstance(surfaces, dict) else None
    if not isinstance(entries, list):
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        surface_id = entry.get("id")
        is_descriptor_surface = surface_id in DESCRIPTOR_SURFACE_IDS or (
            entry.get("status") == "promoted"
            and entry.get("category") == "metadata"
            and "descriptor" in str(entry.get("public_name", "")).casefold()
        )
        if not is_descriptor_surface:
            continue
        walk_public_contract_fields(
            entry,
            blockers,
            f"$.surfaces[{index}]",
            "surface_forbidden_public_contract_field",
        )
        for key in ("public_contract", "capabilities", "public_name"):
            value = entry.get(key)
            for item_index, item in enumerate(value if isinstance(value, list) else [value]):
                if isinstance(item, str) and DESCRIPTOR_FORBIDDEN_PUBLIC_CONTRACT_RE.search(item):
                    blockers.append(
                        "promoted_descriptor_surface_forbidden_public_contract:"
                        f"$.surfaces[{index}].{key}[{item_index}]"
                    )
        walk_surface_text_claims(entry.get("evidence", {}), blockers, f"$.surfaces[{index}].evidence")


def validate_public_events(events: Any, blockers: list[str]) -> None:
    text = json.dumps(events, sort_keys=True)
    for term in FORBIDDEN_PUBLIC_EVENT_TERMS:
        if term in text:
            blockers.append(f"public_events_forbidden_term:{term}")
    walk_claims(events, blockers)
    walk_public_event_text_claims(events, blockers, "$.public_events")
    walk_shortcut_artifact_claims(
        events,
        blockers,
        "$.public_events",
        "public_events_shortcut_artifact_public_readiness_claim",
    )
    walk_public_contract_fields(
        events,
        blockers,
        "$.public_events",
        "public_events_forbidden_public_contract_field",
    )
    if isinstance(events, dict):
        metadata_surfaces = events.get("metadata_surfaces")
        resource_surface = None
        if isinstance(metadata_surfaces, list):
            for item in metadata_surfaces:
                if isinstance(item, dict) and item.get("surface_id") == "obelisk.resource_kind_descriptors.v1":
                    resource_surface = item
                    break
        if resource_surface is None:
            blockers.append("resource_kind_descriptor_surface_missing")
        else:
            flags = resource_surface.get("flags")
            if not isinstance(flags, list) or set(REQUIRED_DESCRIPTOR_FLAGS) - set(flags):
                blockers.append("resource_kind_descriptor_flags_missing")
            fields = resource_surface.get("descriptor_fields")
            if not isinstance(fields, list):
                blockers.append("resource_kind_descriptor_fields_missing")
            else:
                forbidden_fields = {"identity", "object_identity", "lookup", "handle", "resource_handle"}
                if forbidden_fields & set(fields):
                    blockers.append("resource_kind_descriptor_identity_or_lookup_field_present")


def validate_header(path: Path, blockers: list[str]) -> None:
    resolved = safe_input_path(path, "--public-header")
    try:
        header = strip_c_comments(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"--public-header is unreadable: {exc}") from exc
    matches = sorted(set(FORBIDDEN_HEADER_SYMBOL_RE.findall(header)))
    if matches:
        blockers.append("public_header_contains_object_identity_or_resource_handle_symbol")
    for flag in REQUIRED_DESCRIPTOR_FLAGS:
        if flag not in header:
            blockers.append(f"public_header_missing_descriptor_flag:{flag}")
    descriptor_match = re.search(r"typedef\s+struct\s+ObeliskResourceKindDescriptor\s*\{(?P<body>.*?)\}", header, re.DOTALL)
    if descriptor_match is None:
        blockers.append("public_header_missing_resource_kind_descriptor")
    else:
        body = descriptor_match.group("body")
        if re.search(r"\b(?:identity|object_identity|lookup|handle|resource_handle)\b", body, re.IGNORECASE):
            blockers.append("public_header_resource_kind_descriptor_has_identity_lookup_or_handle_field")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[str] = []
    decisions = load_json(args.decisions, "--decisions")
    surfaces = load_json(args.surfaces, "--surfaces")
    events = load_json(args.public_events, "--public-events")

    validate_decisions(decisions, blockers)
    validate_surface(surfaces, blockers)
    validate_promoted_descriptor_surfaces(surfaces, blockers)
    validate_public_events(events, blockers)
    validate_header(args.public_header, blockers)
    valid = not blockers
    missing_evidence_report = build_missing_evidence_report()

    return {
        "schema": REPORT_SCHEMA,
        "surface_id": SURFACE_ID,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_resource_handle_ready": False,
        "post_callback_resource_handle_ready": False,
        "serialPolicyReady": False,
        "resourceLookupReady": False,
        "postCallbackHandleReady": False,
        "objectIdentityReady": False,
        "runtimeSampleReady": False,
        "runtimeRejectedObjectSamplesReady": False,
        "lookupPrivacyReady": False,
        "lifetimeSemanticsReady": False,
        "resourceHandleLifetimeSemanticsReady": False,
        "runtime_object_negative_samples_ready": False,
        "runtime_rejected_object_samples_ready": False,
        "serial_reuse_ready": False,
        "serial_wraparound_ready": False,
        "lookup_privacy_ready": False,
        "lifetime_semantics_ready": False,
        "resource_handle_lifetime_semantics_ready": False,
        "post_callback_lookup_safety_ready": False,
        "post_callback_object_validity_ready": False,
        "post_callback_validity_ready": False,
        "public_promotion_evidence_counting_allowed": False,
        "complete_sdk_counting_allowed": False,
        "accepted_public_promotion_evidence_count": 0,
        "strict_next_blocker": REQUIRED_STRICT_NEXT_BLOCKER,
        "offline_serial_post_callback_artifacts": REQUIRED_OFFLINE_ARTIFACT_POLICY,
        "offline_artifacts_unlock_public_lookup_identity_runtime_sdk": False,
        "next_evidence_contract": build_next_evidence_contract(),
        "public_promotion_blocker_contract": {
            "status": "blocked",
            "required_before_public_lookup": True,
            "counts_toward_public_promotion": False,
            "counts_toward_complete_sdk_claim": False,
            "required_public_promotion_blockers": list(REQUIRED_PUBLIC_PROMOTION_BLOCKERS),
        },
        "public_promotion_missing_evidence": missing_evidence_report,
        "serial_reuse_wraparound_evidence": missing_evidence_report["missing_evidence"][1],
        "lookup_privacy_evidence": missing_evidence_report["missing_evidence"][2],
        "resource_handle_lifetime_semantics_evidence": missing_evidence_report["missing_evidence"][3],
        "post_callback_lookup_safety_evidence": missing_evidence_report["missing_evidence"][4],
        "minimum_runtime_evidence_pair": {
            "required_before_public_promotion": True,
            "counts_toward_public_promotion": False,
            "schemas": [
                "obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1",
                "obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1",
            ],
            "required_policy": [
                "paired manifests must name each other",
                "promotion_evidence_complete must remain false until public review promotes the contract",
                "cross-frame and post-callback lookup must reject until a public validity rule exists",
                "lookup privacy and ResourceHandle lifetime semantics remain separate public-promotion blockers",
            ],
        },
        "blockers": sorted(set(blockers)),
        "non_claim": (
            "ResourceHandle and object identity remain post-v1/blocked; copied events and "
            "category-only resource_kind metadata do not imply lookup, lookup privacy, "
            "identity, lifetime semantics, persistent handles, post-callback object "
            "correlation, mutation, return override, runtime readiness, public SDK "
            "readiness, or v1 completion."
        ),
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
