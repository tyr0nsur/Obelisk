#!/usr/bin/env python3
"""Validate command/chat response public-readiness stays planning-only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = Path(
    "/servidor/ark/workspace-offline/"
    "command-chat-response-route-planning-distinct-second-source-20260601"
)
DEFAULT_READINESS_NAME = "command-chat-response-route-planning-readiness.json"
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"

REPORT_SCHEMA = "obelisk.command-chat-response-public-readiness-check.v1"
READINESS_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
DECISIONS_SCHEMA = "obelisk.command-chat-response-public-contract-decisions.v1"
SURFACE = "obelisk.command_chat_response_path.v1"
TARGET_SET = "command-chat-response-route-planning"
TARGETS = frozenset(
    (
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
        "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
    )
)
REQUIRED_DECISION_IDS = frozenset(
    (
        "dependency.promoted_player_identity",
        "dependency.promoted_permissions_admin",
        "abi.copied_response_payload",
        "abi.capability_and_owner_token",
        "lifecycle.owner_scoped_unregister_and_drain",
        "privacy.redaction_and_targeting",
        "abuse.rate_limit_and_audit",
        "separation.no_commands_router_or_moderation",
        "evidence.layout_runtime_sdk_coverage",
        "evidence.response_target_set_snapshot_second_source",
    )
)
REQUIRED_FORBIDDEN_PUBLIC_CONTRACT = frozenset(
    (
        "reply API",
        "send-chat API",
        "principal or permission claims from command text",
        "principal or permission claims from operator config",
        "player lookup",
        "mutation",
        "return override",
    )
)
REQUIRED_GUIDANCE_BLOCKERS = frozenset(
    (
        "planning_guidance_only",
        "not_release_readiness_target",
        "public_response_path_blocked",
        "player_identity_principal_blocked",
        "permissions_admin_blocked",
        "command_router_blocked",
        "runtime_observation_requires_separate_approval",
    )
)
FALSE_ONLY_KEYS = frozenset(
    (
        "command_router",
        "identity_ready",
        "permission_admin_contract",
        "permission_ready",
        "permissions_admin_ready",
        "permissions_ready",
        "player_identity_contract",
        "player_identity_ready",
        "principal_identity_ready",
        "promotion_ready",
        "public_abi_ready",
        "public_command_router",
        "public_header_allowed",
        "public_header_ready",
        "public_headers_ready",
        "public_reply_api",
        "public_response_path_ready",
        "public_sdk_ready",
        "public_send_chat_api",
        "reply_api",
        "router_ready",
        "runtime_command_router",
        "runtime_ready",
        "send_chat_api",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "block",
    "forbid",
    "guidance",
    "negative",
    "non_claim",
    "not_promoted",
    "not_sufficient",
    "required",
    "snapshot_prep_checks",
    "why_blocked",
)
POSITIVE_SURFACE_RE = re.compile(
    r"\b("
    r"public\s+headers?|"
    r"reply\s+api|replies\s+api|send[- ]?chat\s+api|"
    r"command\s+router|"
    r"player\s+identity|principal\s+identity|permissions?(?:/admin)?"
    r")\b.{0,80}\b(allowed|available|enabled|established|promoted|public|ready)\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(blocked|cannot|candidate|does\s+not|fail[s-]?closed|forbidden|not|planning|require[sd]?|until)\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Second-source planning layout root.")
    parser.add_argument(
        "--readiness",
        type=Path,
        help=f"Readiness JSON. Defaults to --root/{DEFAULT_READINESS_NAME}.",
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        default=DEFAULT_DECISIONS,
        help="Command/chat response public contract decisions JSON.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(details)
    blockers.append(item)


def safe_load_json(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"${label}", path=str(path), detail=str(exc))
        return None
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"${label}", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"${label}", path=str(path), detail=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", f"${label}", path=str(path))
        return None
    return payload


def strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def string_set(value: Any) -> set[str]:
    return set(strings(value))


def normalized_key(key: Any) -> str:
    return str(key).casefold().replace("-", "_").replace(" ", "_")


def negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


def collect_surface_overclaims(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if normalized_key(key) in FALSE_ONLY_KEYS and child is not False:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            collect_surface_overclaims(child, blockers, child_trail)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_surface_overclaims(child, blockers, f"{trail}[{index}]")
        return
    if not isinstance(value, str) or negative_context(trail):
        return
    if POSITIVE_SURFACE_RE.search(value) and NEGATED_CLAIM_RE.search(value) is None:
        add(blockers, "positive_public_surface_claim", trail, value=value)


def require_false(mapping: dict[str, Any], key: str, label: str, blockers: list[dict[str, Any]]) -> None:
    if mapping.get(key) is not False:
        add(blockers, f"{key}_not_false", f"{label}.{key}", value=mapping.get(key))


def require_equal(
    mapping: dict[str, Any],
    key: str,
    expected: Any,
    label: str,
    blockers: list[dict[str, Any]],
) -> None:
    if mapping.get(key) != expected:
        add(blockers, f"{key}_mismatch", f"{label}.{key}", expected=expected, value=mapping.get(key))


def validate_gate(
    gate: Any,
    *,
    label: str,
    expected_ready: bool,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(gate, dict):
        add(blockers, f"{label.strip('$.')}_missing", label)
        return
    require_equal(gate, "ready_scope", "planning_only", label, blockers)
    require_equal(gate, "layout_ready", True, label, blockers)
    require_equal(gate, "ready", expected_ready, label, blockers)
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if key in gate:
            require_false(gate, key, label, blockers)


def validate_readiness(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    require_equal(payload, "schema", READINESS_SCHEMA, "$.readiness", blockers)
    require_equal(payload, "evidence_scope", "second_source_layout_evidence_only", "$.readiness", blockers)
    require_equal(payload, "gate_mode", "planning_layout_intake", "$.readiness", blockers)
    require_equal(payload, "second_source_status", "compared", "$.readiness", blockers)
    require_equal(payload, "strict_identity_indices", False, "$.readiness", blockers)
    if string_set(payload.get("target_sets")) != {TARGET_SET}:
        add(blockers, "target_sets_mismatch", "$.readiness.target_sets", expected=[TARGET_SET], value=payload.get("target_sets"))
    if string_set(payload.get("target_filters")) != TARGETS:
        add(
            blockers,
            "target_filters_mismatch",
            "$.readiness.target_filters",
            expected=sorted(TARGETS),
            value=payload.get("target_filters"),
        )

    totals = payload.get("totals")
    if not isinstance(totals, dict):
        add(blockers, "totals_missing", "$.readiness.totals")
    else:
        for key, expected in (
            ("targets", 3),
            ("comparable", 3),
            ("blocked", 0),
            ("second_source_accepted", 3),
            ("second_source_inconclusive", 0),
            ("second_source_missing", 0),
            ("second_source_rejected", 0),
        ):
            require_equal(totals, key, expected, "$.readiness.totals", blockers)

    modules = payload.get("modules")
    if not isinstance(modules, list) or len(modules) != 1 or not isinstance(modules[0], dict):
        add(blockers, "modules_mismatch", "$.readiness.modules")
    else:
        module = modules[0]
        require_equal(module, "module", "base-snapshots", "$.readiness.modules[0]", blockers)
        require_equal(module, "targets", 3, "$.readiness.modules[0]", blockers)
        require_equal(module, "comparable", 3, "$.readiness.modules[0]", blockers)
        require_equal(module, "blocked", 0, "$.readiness.modules[0]", blockers)
        second_source = module.get("second_source")
        if not isinstance(second_source, dict):
            add(blockers, "module_second_source_missing", "$.readiness.modules[0].second_source")
        else:
            for key, expected in (("accepted", 3), ("inconclusive", 0), ("missing", 0), ("rejected", 0)):
                require_equal(second_source, key, expected, "$.readiness.modules[0].second_source", blockers)
        details = module.get("target_details")
        if not isinstance(details, list) or len(details) != 3:
            add(blockers, "target_details_mismatch", "$.readiness.modules[0].target_details")
        else:
            detail_targets = set()
            for index, detail in enumerate(details):
                label = f"$.readiness.modules[0].target_details[{index}]"
                if not isinstance(detail, dict):
                    add(blockers, "target_detail_invalid", label)
                    continue
                detail_targets.add(detail.get("target"))
                require_equal(detail, "comparable", True, label, blockers)
                require_equal(detail, "second_source_status", "accepted", label, blockers)
                if detail.get("block_reasons") != []:
                    add(blockers, "target_detail_block_reasons_not_empty", f"{label}.block_reasons")
            if detail_targets != TARGETS:
                add(blockers, "target_detail_targets_mismatch", "$.readiness.modules[0].target_details")

    validate_gate(payload.get("planning_layout_gate"), label="$.readiness.planning_layout_gate", expected_ready=True, blockers=blockers)
    validate_gate(payload.get("promotion_gate"), label="$.readiness.promotion_gate", expected_ready=False, blockers=blockers)
    promotion_gate = payload.get("promotion_gate")
    if isinstance(promotion_gate, dict):
        reasons = {
            item.get("reason")
            for item in promotion_gate.get("blockers", [])
            if isinstance(item, dict) and isinstance(item.get("reason"), str)
        }
        if "planning_layout_intake_not_promotion_gate" not in reasons:
            add(blockers, "promotion_gate_blocker_missing", "$.readiness.promotion_gate.blockers")

    guidance = payload.get("target_set_guidance")
    if not isinstance(guidance, list) or len(guidance) != 1 or not isinstance(guidance[0], dict):
        add(blockers, "target_set_guidance_missing", "$.readiness.target_set_guidance")
    else:
        item = guidance[0]
        label = "$.readiness.target_set_guidance[0]"
        require_equal(item, "target_set", TARGET_SET, label, blockers)
        require_equal(item, "classification", "command_chat_response_route_guidance_only_candidate", label, blockers)
        blockers_seen = string_set(item.get("why_blocked"))
        if not REQUIRED_GUIDANCE_BLOCKERS.issubset(blockers_seen):
            add(
                blockers,
                "target_set_guidance_missing_blockers",
                f"{label}.why_blocked",
                missing=sorted(REQUIRED_GUIDANCE_BLOCKERS - blockers_seen),
            )

    collect_surface_overclaims(payload, blockers, "$.readiness")


def validate_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    require_equal(payload, "schema", DECISIONS_SCHEMA, "$.decisions", blockers)
    require_equal(payload, "surface", SURFACE, "$.decisions", blockers)
    require_equal(payload, "status", "blocked", "$.decisions", blockers)
    require_false(payload, "public_header_allowed", "$.decisions", blockers)
    require_false(payload, "legacy_call_process_event_public_response_allowed", "$.decisions", blockers)
    if payload.get("public_header_symbols_now") != []:
        add(blockers, "public_header_symbols_now_not_empty", "$.decisions.public_header_symbols_now", value=payload.get("public_header_symbols_now"))

    forbidden = string_set(payload.get("forbidden_public_contract"))
    if not REQUIRED_FORBIDDEN_PUBLIC_CONTRACT.issubset(forbidden):
        add(
            blockers,
            "forbidden_public_contract_missing_required",
            "$.decisions.forbidden_public_contract",
            missing=sorted(REQUIRED_FORBIDDEN_PUBLIC_CONTRACT - forbidden),
        )

    requirements = payload.get("required_before_public_header")
    if not isinstance(requirements, list):
        add(blockers, "required_before_public_header_not_list", "$.decisions.required_before_public_header")
        collect_surface_overclaims(payload, blockers, "$.decisions")
        return

    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(requirements):
        label = f"$.decisions.required_before_public_header[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            add(blockers, "required_before_public_header_item_invalid", label)
            continue
        by_id[item["id"]] = item
        if item.get("status") != "unresolved":
            add(blockers, "required_before_public_header_item_not_unresolved", f"{label}.status", id=item["id"], value=item.get("status"))

    if set(by_id) != REQUIRED_DECISION_IDS:
        add(
            blockers,
            "required_before_public_header_ids_mismatch",
            "$.decisions.required_before_public_header",
            missing=sorted(REQUIRED_DECISION_IDS - set(by_id)),
            unexpected=sorted(set(by_id) - REQUIRED_DECISION_IDS),
        )

    identity = by_id.get("dependency.promoted_player_identity", {})
    behaviors = string_set(identity.get("required_behavior"))
    for required in (
        "command text cannot establish principal identity",
        "operator config enables surfaces only and cannot establish principal identity",
        "response delivery never creates identity or permission claims",
    ):
        if required not in behaviors:
            add(blockers, "identity_dependency_behavior_missing", "$.decisions.required_before_public_header", behavior=required)

    separation = by_id.get("separation.no_commands_router_or_moderation", {})
    exclusions = string_set(separation.get("required_exclusions"))
    for required in ("command router", "command registration API", "moderation API"):
        if required not in exclusions:
            add(blockers, "separation_exclusion_missing", "$.decisions.required_before_public_header", exclusion=required)

    evidence = by_id.get("evidence.response_target_set_snapshot_second_source", {})
    if string_set(evidence.get("required_targets")) != TARGETS:
        add(blockers, "decision_response_targets_mismatch", "$.decisions.required_before_public_header", value=evidence.get("required_targets"))

    collect_surface_overclaims(payload, blockers, "$.decisions")


def build_report(readiness_path: Path, decisions_path: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    readiness = safe_load_json(readiness_path, "readiness", blockers)
    decisions = safe_load_json(decisions_path, "decisions", blockers)
    if readiness is not None:
        validate_readiness(readiness, blockers)
    if decisions is not None:
        validate_decisions(decisions, blockers)

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "valid": valid,
        "accepted_for_planning": valid,
        "planning_only": valid,
        "public_readiness_ready": False,
        "public_header_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "surface": SURFACE,
        "target_set": TARGET_SET,
        "target_filters": sorted(TARGETS),
        "readiness_path": str(readiness_path),
        "decisions_path": str(decisions_path),
        "readiness_status": readiness.get("second_source_status") if isinstance(readiness, dict) else None,
        "decisions_status": decisions.get("status") if isinstance(decisions, dict) else None,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
    }


def main() -> int:
    args = parse_args()
    readiness_path = args.readiness if args.readiness is not None else args.root / DEFAULT_READINESS_NAME
    report = build_report(readiness_path, args.decisions)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
