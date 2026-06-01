#!/usr/bin/env python3
"""Offline guardrail for lifecycle-ops and gameplay-tick public contract blockers.

Acceptance means the candidate-only planning state is internally consistent. It does
not promote either surface, open the public C ABI, or prove runtime readiness.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIFECYCLE_DECISIONS = ROOT / "docs" / "lifecycle_ops_recovery_public_contract_decisions.json"
DEFAULT_TICK_DECISIONS = ROOT / "docs" / "gameplay_tick_callbacks_public_contract_decisions.json"
DEFAULT_SURFACES = ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_HEADER = ROOT / "include" / "obelisk" / "ObeliskApi.h"

LIFECYCLE_SURFACE = "obelisk.lifecycle_ops_recovery.v1"
TICK_SURFACE = "obelisk.gameplay_tick_callbacks.v1"
FOUNDATION_SURFACE = "obelisk.lifecycle_config_logging.v1"
TIMERS_SURFACE = "obelisk.process_local_timers.v1"

FALSE_TOP_LEVEL_KEYS = (
    "public_header_allowed",
)
EMPTY_TOP_LEVEL_LISTS = (
    "public_header_symbols_now",
    "public_capability_bits_now",
    "public_callback_abi_now",
)

LIFECYCLE_REQUIRED_IDS = {
    "separation.foundation_not_ops_recovery",
    "abi.no_public_symbols_now",
    "lifecycle.hot_reload_quiescence",
    "ops.operator_reload_ingress",
    "recovery.multi_instance_restart_state",
    "crash.watchdog_policy",
    "evidence.sdk_integration_coverage",
    "release.explicit_post_v1_or_excluded",
}
TICK_REQUIRED_IDS = {
    "separation.process_local_timers_not_gameplay_tick",
    "abi.no_public_symbols_now",
    "tick.cadence_budget_threading",
    "lifecycle.owner_scoped_callback_cleanup",
    "payload.copied_no_ue_internals",
    "evidence.sdk_consumer_coverage",
    "release.explicit_post_v1_or_excluded",
}

LIFECYCLE_FORBIDDEN = {
    "plugin watchdog API",
    "plugin crash recovery API",
    "hot plugin reload API",
    "Obelisk hot reload API",
    "process restart orchestration API",
    "server recovery API",
    "operator reload command API",
    "detached-worker ingress API",
    "restart-state recovery API",
}
TICK_FORBIDDEN = {
    "server tick callback API",
    "UE gameplay tick callback API",
    "module tick callback API",
    "per-frame hook API",
    "gameplay timer API",
    "server tick cadence claim",
    "UE tick budget claim",
}
LIFECYCLE_FOUNDATION_EXCLUSIONS = {
    "hot reload of Obelisk itself",
    "hot plugin reload",
    "plugin watchdog/crash recovery",
    "process restart orchestration",
    "server recovery API",
    "operator reload commands",
    "detached worker ingress without shutdown proof",
}
TICK_SURFACE_EXCLUSIONS = {
    "server tick callback API",
    "UE gameplay tick callback API",
    "module tick callback API",
    "per-frame hook API",
    "gameplay timers",
}
TIMER_SURFACE_EXCLUSIONS = {
    "server tick callbacks",
    "UE gameplay tick callbacks",
    "module tick callbacks",
    "per-frame hook callbacks",
}

LIFECYCLE_HEADER_TOKENS = {
    "OBELISK_API_CAPABILITY_LIFECYCLE_OPS_RECOVERY",
    "OBELISK_API_CAPABILITY_PLUGIN_WATCHDOG",
    "OBELISK_API_CAPABILITY_HOT_RELOAD",
    "OBELISK_API_CAPABILITY_OPERATOR_RELOAD",
    "ObeliskPluginWatchdog",
    "ObeliskPluginRecovery",
    "ObeliskHotReload",
    "ObeliskOperatorReload",
    "RegisterPluginWatchdogWithOwnerTokenHandle",
    "RegisterOperatorReloadWithOwnerTokenHandle",
    "RestartServerWithOwnerToken",
    "RecoverPluginWithOwnerToken",
}
TICK_HEADER_TOKENS = {
    "OBELISK_API_CAPABILITY_GAMEPLAY_TICK_CALLBACKS",
    "OBELISK_API_CAPABILITY_SERVER_TICK",
    "OBELISK_API_CAPABILITY_MODULE_TICK",
    "ObeliskGameplayTickCallback",
    "ObeliskServerTickCallback",
    "ObeliskModuleTickCallback",
    "RegisterGameplayTickWithOwnerTokenHandle",
    "RegisterServerTickWithOwnerTokenHandle",
    "RegisterModuleTickWithOwnerTokenHandle",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lifecycle-decisions", type=Path, default=DEFAULT_LIFECYCLE_DECISIONS)
    parser.add_argument("--tick-decisions", type=Path, default=DEFAULT_TICK_DECISIONS)
    parser.add_argument("--surfaces", type=Path, default=DEFAULT_SURFACES)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_HEADER)
    parser.add_argument("--promote", action="store_true", help="always fails closed")
    parser.add_argument("--public-readiness", action="store_true", help="always fails closed")
    parser.add_argument("--runtime-readiness", action="store_true", help="always fails closed")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    return parser.parse_args(argv)


def load_json(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{label}: unable to load JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, [f"{label}: top-level JSON must be an object"]
    return payload, []


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def validate_decisions(
    payload: dict[str, Any],
    *,
    label: str,
    schema: str,
    surface: str,
    required_ids: set[str],
    forbidden_terms: set[str],
    separation_key: str,
    separation_source_key: str,
    separation_source: str,
    separation_list_key: str,
    extra_empty_lists: tuple[str, ...] = (),
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != schema:
        errors.append(f"{label}: schema must be {schema}")
    if payload.get("surface") != surface:
        errors.append(f"{label}: surface must be {surface}")
    if payload.get("status") != "blocked":
        errors.append(f"{label}: status must remain blocked")
    if payload.get("planning_stage") != "v1_completion_blocker":
        errors.append(f"{label}: planning_stage must remain v1_completion_blocker")
    if payload.get("artifact_status") != "candidate_only":
        errors.append(f"{label}: artifact_status must remain candidate_only")
    if payload.get("readiness_classification") != "planning_only":
        errors.append(f"{label}: readiness_classification must remain planning_only")
    for key in FALSE_TOP_LEVEL_KEYS:
        if payload.get(key) is not False:
            errors.append(f"{label}: {key} must remain false")
    for key in EMPTY_TOP_LEVEL_LISTS + extra_empty_lists:
        if payload.get(key) != []:
            errors.append(f"{label}: {key} must remain an empty list")

    forbidden = set(string_list(payload.get("forbidden_public_contract")))
    missing_forbidden = forbidden_terms - forbidden
    if missing_forbidden:
        errors.append(f"{label}: forbidden_public_contract missing {sorted(missing_forbidden)}")

    requirements = payload.get("required_before_public_header")
    if not isinstance(requirements, list):
        errors.append(f"{label}: required_before_public_header must be a list")
    else:
        observed_ids = {item.get("id") for item in requirements if isinstance(item, dict)}
        if observed_ids != required_ids:
            errors.append(
                f"{label}: required_before_public_header ids mismatch "
                f"expected={sorted(required_ids)} observed={sorted(str(item) for item in observed_ids)}"
            )
        for index, item in enumerate(requirements):
            if not isinstance(item, dict):
                errors.append(f"{label}: required_before_public_header[{index}] must be an object")
                continue
            if item.get("status") == "resolved":
                errors.append(f"{label}: required_before_public_header[{index}] is resolved before promotion")

    separation = payload.get(separation_key)
    if not isinstance(separation, dict):
        errors.append(f"{label}: {separation_key} must be an object")
    else:
        if separation.get(separation_source_key) != separation_source:
            errors.append(f"{label}: {separation_key}.{separation_source_key} must be {separation_source}")
        missing_separation = forbidden_terms - set(string_list(separation.get(separation_list_key)))
        if missing_separation:
            errors.append(f"{label}: {separation_key}.{separation_list_key} missing {sorted(missing_separation)}")

    return errors


def validate_surfaces(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    raw_surfaces = manifest.get("surfaces")
    if not isinstance(raw_surfaces, list):
        return ["surfaces: $.surfaces must be a list"]
    surfaces = {
        surface.get("id"): surface
        for surface in raw_surfaces
        if isinstance(surface, dict) and isinstance(surface.get("id"), str)
    }

    for surface_id in (LIFECYCLE_SURFACE, TICK_SURFACE):
        surface = surfaces.get(surface_id)
        if surface is None:
            errors.append(f"surfaces: missing {surface_id}")
            continue
        if surface.get("status") != "post-v1":
            errors.append(f"surfaces: {surface_id} status must remain post-v1")
        if surface.get("public_contract") != []:
            errors.append(f"surfaces: {surface_id} public_contract must remain empty")
        if surface_id not in set(string_list(manifest.get("v1_sdk_completion_blockers"))):
            errors.append(f"surfaces: {surface_id} must remain in v1_sdk_completion_blockers")
        if surface_id not in set(string_list(manifest.get("post_v1_or_excluded_surfaces"))):
            errors.append(f"surfaces: {surface_id} must remain in post_v1_or_excluded_surfaces")
        contract = surface.get("v1_decision_contract")
        if not isinstance(contract, dict):
            errors.append(f"surfaces: {surface_id} v1_decision_contract must be an object")
        else:
            if contract.get("current_decision") != "blocked_until_promoted_or_explicitly_excluded":
                errors.append(f"surfaces: {surface_id} current_decision must remain blocked_until_promoted_or_explicitly_excluded")
            if contract.get("must_remain_without_public_contract_until_promotion") is not True:
                errors.append(f"surfaces: {surface_id} must remain without public contract until promotion")

    lifecycle = surfaces.get(LIFECYCLE_SURFACE, {})
    missing_lifecycle_exclusions = LIFECYCLE_FORBIDDEN - set(string_list(lifecycle.get("exclusions")))
    if missing_lifecycle_exclusions:
        errors.append(f"surfaces: lifecycle exclusions missing {sorted(missing_lifecycle_exclusions)}")
    if not set(string_list(lifecycle.get("blockers"))):
        errors.append("surfaces: lifecycle blockers must remain documented")

    tick = surfaces.get(TICK_SURFACE, {})
    missing_tick_exclusions = TICK_SURFACE_EXCLUSIONS - set(string_list(tick.get("exclusions")))
    if missing_tick_exclusions:
        errors.append(f"surfaces: tick exclusions missing {sorted(missing_tick_exclusions)}")
    if "Process-local timers are not server tick, UE gameplay tick, or module tick callbacks." not in string_list(tick.get("blockers")):
        errors.append("surfaces: tick blockers must state process-local timers are not gameplay/server tick callbacks")

    foundation = surfaces.get(FOUNDATION_SURFACE)
    if not isinstance(foundation, dict):
        errors.append(f"surfaces: missing {FOUNDATION_SURFACE}")
    else:
        missing = LIFECYCLE_FOUNDATION_EXCLUSIONS - set(string_list(foundation.get("exclusions")))
        if missing:
            errors.append(f"surfaces: lifecycle foundation exclusions missing {sorted(missing)}")

    timers = surfaces.get(TIMERS_SURFACE)
    if not isinstance(timers, dict):
        errors.append(f"surfaces: missing {TIMERS_SURFACE}")
    else:
        if timers.get("status") != "promoted":
            errors.append("surfaces: process-local timers must remain promoted foundation")
        missing = TIMER_SURFACE_EXCLUSIONS - set(string_list(timers.get("exclusions")))
        if missing:
            errors.append(f"surfaces: timer exclusions missing {sorted(missing)}")

    return errors


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def validate_header(path: Path) -> list[str]:
    try:
        text = strip_c_comments(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"header: unable to read public header: {exc}"]
    errors: list[str] = []
    for surface, tokens in (
        (LIFECYCLE_SURFACE, LIFECYCLE_HEADER_TOKENS),
        (TICK_SURFACE, TICK_HEADER_TOKENS),
    ):
        present = sorted(token for token in tokens if token in text)
        if present:
            errors.append(f"header: blocked {surface} public symbols present: {present}")
    return errors


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    errors: list[str] = []
    if args.promote:
        errors.append("--promote is fail-closed for lifecycle/tick planning contracts")
    if args.public_readiness:
        errors.append("--public-readiness is fail-closed for lifecycle/tick planning contracts")
    if args.runtime_readiness:
        errors.append("--runtime-readiness is fail-closed for lifecycle/tick planning contracts")

    lifecycle, lifecycle_errors = load_json(args.lifecycle_decisions, "lifecycle decisions")
    tick, tick_errors = load_json(args.tick_decisions, "tick decisions")
    surfaces, surfaces_errors = load_json(args.surfaces, "public SDK surfaces")
    errors.extend(lifecycle_errors)
    errors.extend(tick_errors)
    errors.extend(surfaces_errors)

    if lifecycle is not None:
        errors.extend(
            validate_decisions(
                lifecycle,
                label="lifecycle decisions",
                schema="obelisk.lifecycle-ops-recovery-public-contract-decisions.v1",
                surface=LIFECYCLE_SURFACE,
                required_ids=LIFECYCLE_REQUIRED_IDS,
                forbidden_terms=LIFECYCLE_FORBIDDEN,
                separation_key="separation_contract",
                separation_source_key="promoted_foundation_surface",
                separation_source=FOUNDATION_SURFACE,
                separation_list_key="not_satisfied_by_foundation",
                extra_empty_lists=("public_ops_api_now",),
            )
        )
    if tick is not None:
        errors.extend(
            validate_decisions(
                tick,
                label="tick decisions",
                schema="obelisk.gameplay-tick-callbacks-public-contract-decisions.v1",
                surface=TICK_SURFACE,
                required_ids=TICK_REQUIRED_IDS,
                forbidden_terms=TICK_FORBIDDEN,
                separation_key="separation_contract",
                separation_source_key="promoted_timer_surface",
                separation_source=TIMERS_SURFACE,
                separation_list_key="not_satisfied_by_process_local_timers",
            )
        )
    if surfaces is not None:
        errors.extend(validate_surfaces(surfaces))
    errors.extend(validate_header(args.public_header))

    return {
        "schema": "obelisk.lifecycle-tick-public-contract-check.v1",
        "ok": not errors,
        "candidate_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "surfaces": [LIFECYCLE_SURFACE, TICK_SURFACE],
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["ok"]:
        print("lifecycle/tick public contract planning guardrail valid")
    else:
        print("lifecycle/tick public contract planning guardrail invalid", file=sys.stderr)
        for error in report["errors"]:
            print(f"- {error}", file=sys.stderr)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
