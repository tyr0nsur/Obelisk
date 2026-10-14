#!/usr/bin/env python3
"""Read-only readiness check for the internal Mission copied-bool lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import build_redacted_ufunction_signatures as redacted_ufunction_signatures
import validate_offline_artifact_gate as offline_gate
from reflection_target_sets import NON_AUTHORIZING_READY_DOES_NOT_SATISFY, NON_AUTHORIZING_READY_SCOPE
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/mission-copied-bool-tail-policy-slice-20260530T090211Z"
)
DEFAULT_MANIFEST_NAME = "mission-copied-bool-policy-slice.json"
EXPECTED_MANIFEST_SHA256 = "f56a191aaecbd52d042efd81423d4a86f4e5a29674660aab9d65bbf496416945"
REPORT_SCHEMA = "obelisk.mission-copied-bool-readiness-check.v1"
ATTESTATION_SCHEMA = "obelisk.mission-copied-bool-offline-attestation.v1"
POLICY_SCHEMA = "obelisk.mission-copied-bool-policy-slice.v1"
INPUT_TARGET_SET = "mission-compact-intake"
OUTPUT_TARGET_SET = "mission-copied-bool-policy-slice"
FIXTURE_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
MISSION_HOOK_SOURCE = "hooks/ProcessEventMissionReflection.cpp"
PUBLIC_API_HEADER = Path("include/obelisk/ObeliskApi.h")
PUBLIC_GAMEPLAY_EVENTS_DOC = Path("docs/public_gameplay_events.json")
PLUGIN_MANAGER_SOURCE = Path("core/PluginManager.cpp")
PLUGIN_MANAGER_GUARDRAIL_TEST = Path("scripts/test_plugin_manager_guardrails.py")
MISSION_COPIED_BOOL_DISPATCHER = "MissionCopiedBoolEventDispatcher"
MISSION_COPIED_BOOL_OWNER_CLEANUP = (
    "MissionCopiedBoolEventDispatcher::Get().UnregisterCallbacksForOwner(owner)"
)
EXPECTED_INPUT_TARGETS = {
    "MissionType.AddPlayerToMission",
    "MissionType.BPAllowPlayerToLeaveMission",
    "MissionType.BPOnPlayerRemovedFromMission",
    "MissionType.GetPlayerUsableItems",
}
EXPECTED_COPIED_TARGETS = {
    "MissionType.AddPlayerToMission",
    "MissionType.BPAllowPlayerToLeaveMission",
    "MissionType.BPOnPlayerRemovedFromMission",
}
EXPECTED_COPIED_FIELDS = {
    "MissionType.AddPlayerToMission.bForceAdd",
    "MissionType.AddPlayerToMission.ReturnValue",
    "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
    "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
    "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
}
EXPECTED_REDACTED_FIELDS = {
    "MissionType.AddPlayerToMission.PlayerCharacter",
    "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn",
    "MissionType.BPOnPlayerRemovedFromMission.Player",
    "MissionType.BPOnPlayerRemovedFromMission.Controller",
    "MissionType.GetPlayerUsableItems.Character",
    "MissionType.GetPlayerUsableItems.OutItemIDs",
}
REQUIRED_NON_CLAIM_TOKENS = (
    "does not expose UE pointers",
    "does not promote public SDK callbacks",
    "does not promote runtime hook wiring",
    "does not copy player/controller/character object refs",
)
CURRENT_SDK_BLOCKER = "approved_runtime_evidence_missing"
BETA_CAPTURE_STATUS = "future_capture_targets_only"
BETA_CAPTURE_TARGET_STATUS = "future_capture_target"
BETA_CAPTURE_GATE = "dedicated_beta_capture_check_required"
BETA_CAPTURE_SURFACE = "mission_copied_bool"
BETA_CAPTURE_FALSE_OR_ZERO_FIELDS = (
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_ready",
    "beta_capture_ready",
    "candidate_capture_evidence_ready",
    "candidate_capture_ready",
    "clears_approved_runtime_evidence_missing",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "complete_sdk_ready",
    "counts_as_approved_runtime_evidence",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "debug_capture_ready",
    "dependency_chain_completion_ready",
    "mission_sdk_ready",
    "mutation_authority_ready",
    "mutation_ready",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_ready",
    "p0_ready",
    "player_principal_replacement_ready",
    "player_principal_runtime_evidence_ready",
    "public_sdk_ready",
    "replaces_player_principal_evidence",
    "resource_handle_ready",
    "return_override_ready",
    "return_value_override_ready",
    "runtime_capture_ready",
    "runtime_evidence_ready",
    "runtime_ready",
    "sdk_progress",
    "sdk_progress_contribution",
    "sdk_ready",
    "v1_completion",
    "v1_completion_contribution",
    "v1_completion_ready",
)
BETA_CAPTURE_ARTIFACT_KEYS = {
    "beta_capture",
    "beta_capture_pack",
    "beta_capture_plan",
    "beta_capture_prep",
    "candidate_beta_capture_pack",
    "candidate_beta_capture_plan",
    "capture_pack",
    "capture_plan",
    "multi_surface_beta_capture",
    "multi_surface_beta_capture_pack",
    "multi_surface_beta_capture_plan",
}
FORBIDDEN_COPIED_RE = re.compile(
    r"(?:PlayerCharacter|PlayerPawn|Controller|OutItemIDs|GetPlayerUsableItems|identity|"
    r"lookup|mutation|object_refs|public_sdk|resource_handle|return_override|runtime|ue_pointer)",
    re.IGNORECASE,
)
FORBIDDEN_TRUE_READY_KEYS = {
    "candidate_capture_evidence_ready",
    "candidate_capture_ready",
    "candidate_debug_capture_ready",
    "capture_evidence_ready",
    "capture_ready",
    "debug_capture_evidence_ready",
    "debug_capture_ready",
    "dispatcher_ready",
    "mission_payload_decoding_ready",
    "mission_sdk_ready",
    "mutation_ready",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_ready",
    "beta_capture_ready",
    "clears_approved_runtime_evidence_missing",
    "complete_sdk_ready",
    "counts_as_approved_runtime_evidence",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "debug_capture_ready",
    "dependency_chain_completion_ready",
    "mutation_authority_ready",
    "p0_dependency_chain_accounted",
    "p0_dependency_chain_complete",
    "p0_dependency_chain_ready",
    "p0_ready",
    "player_principal_replacement_ready",
    "player_principal_runtime_evidence_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_mission_sdk_ready",
    "public_runtime_ready",
    "public_sdk_ready",
    "replaces_player_principal_evidence",
    "resource_handle_ready",
    "resourcehandle_ready",
    "return_override_ready",
    "return_value_override_ready",
    "runtime_capture_ready",
    "runtime_evidence_ready",
    "runtime_hook_ready",
    "runtime_hooks_ready",
    "runtime_ready",
    "v1_complete",
    "v1_completion",
    "v1_ready",
} | offline_gate.MISSION_COPIED_BOOL_FORBIDDEN_TRUE_READY_KEYS
ALLOWED_OVERCLAIM_TEXT_PREFIXES = ("$.non_claims", "$.safety_summary.explicitly_excluded")
AFFIRMATIVE_OVERCLAIM_CONTEXT_RE = re.compile(
    r"\b(?:ready|readiness|available|availability|supported|support|enabled|promoted|promotion|"
    r"supports?|enables?|promotes?|exposes?|publishes?|authorizes?|validates?|claims?|proves?|"
    r"counts?|credits?|included|exposed|exposure|complete|completion|stable|allowed|unblocked|unlocked)\b",
    re.IGNORECASE,
)
NEGATED_OR_EXCLUDED_CONTEXT_RE = re.compile(
    r"\b(?:blocked|does\s+not|do\s+not|excluded|explicitly\s+excluded|is\s+not|must\s+not|no|not|"
    r"without)\b",
    re.IGNORECASE,
)
ALLOWED_PREFIX_CLAIM_SUBJECT_RE = re.compile(
    r"\b(?:"
    r"approved[_ -]?runtime[_ -]?evidence|"
    r"(?:public[_ -]?)?(?:mission|module)[_ -]?(?:sdk|api)|"
    r"public[_ -]?(?:abi|api|callback|descriptor|sdk)|"
    r"mission[_ -]?(?:callback|descriptor|event|identity)|"
    r"player[_ -]?identity|"
    r"player[_ -]?principal(?:[_ -]?lifecycle)?[_ -]?evidence|"
    r"object[_ -]?identity|"
    r"identity|lookup|mutation|"
    r"p0[_ -]?dependency[_ -]?chain|"
    r"resource[_ -]?handle|ResourceHandle|"
    r"return[_ -]?(?:value[_ -]?)?override|"
    r"runtime[_ -]?(?:evidence|hook|hooks|callback|callbacks|observer|ready|readiness|support|capture|wiring|validation)"
    r")\b",
    re.IGNORECASE,
)
CANDIDATE_CAPTURE_PROMOTION_RE = re.compile(
    r"\b(?:(?:multi[_ -]?surface\s+)?(?:beta|candidate|debug|candidate/debug)[_ -]?captures?|"
    r"(?:multi[_ -]?surface\s+)?(?:beta|candidate|debug)[_ -]?capture[_ -]?(?:pack|plan|artifact|bundle)s?)\s+"
    r"(?:(?:is|are)\s+(?:accepted|approved|available|enabled|evidence|progress|promoted|ready|runtime|supported|validated)|"
    r"(?:counts?|credits?)\s+(?:toward|for)|"
    r"(?:clears?|enables?|promotes?|replaces?|satisfies?|supports?|unlocks?|unblocks?|authorizes?|validates?))\b",
    re.IGNORECASE,
)
POSITIVE_PROGRESS_RATIO_RE = re.compile(r"^\s*[1-9][0-9]*\s*/\s*[1-9][0-9]*\s*$")
MISSION_CANDIDATE_FORBIDDEN_CLAIM_PHRASES = {
    "abi ready": "public_abi",
    "allows mutation": "mutation",
    "allows return override": "return_override",
    "authority promoted": "authority",
    "authority ready": "authority",
    "authoritative identity": "authority_identity",
    "candidate capture is evidence": "candidate_capture",
    "candidate capture is progress": "candidate_capture",
    "candidate capture is ready": "candidate_capture",
    "candidate capture ready": "candidate_capture",
    "approved runtime evidence accepted": "approved_runtime_evidence",
    "approved runtime evidence present": "approved_runtime_evidence",
    "approved runtime evidence ready": "approved_runtime_evidence",
    "beta capture is evidence": "candidate_capture",
    "beta capture is progress": "candidate_capture",
    "beta capture is ready": "candidate_capture",
    "beta capture pack is evidence": "candidate_capture",
    "beta capture plan is evidence": "candidate_capture",
    "clears approved_runtime_evidence_missing": "approved_runtime_evidence",
    "c abi ready": "public_abi",
    "counts toward p0 dependency chain": "p0_dependency_chain",
    "debug capture is evidence": "candidate_capture",
    "debug capture is progress": "candidate_capture",
    "debug capture is ready": "candidate_capture",
    "debug capture ready": "candidate_capture",
    "enables mutation": "mutation",
    "enables resource handle": "resource_handle",
    "enables resourcehandle": "resource_handle",
    "enables return override": "return_override",
    "enables runtime support": "runtime_ready",
    "hook wiring ready": "runtime_hooks",
    "identity promoted": "identity",
    "identity ready": "identity",
    "multi-surface beta capture is evidence": "candidate_capture",
    "multi surface beta capture is evidence": "candidate_capture",
    "mission authority": "authority",
    "mission identity": "identity",
    "mission sdk": "mission_sdk",
    "mission sdk allowed": "mission_sdk",
    "mission sdk unblocked": "mission_sdk",
    "mission sdk unlocked": "mission_sdk",
    "mutation enabled": "mutation",
    "mutation authority": "mutation",
    "mutation path": "mutation",
    "mutation ready": "mutation",
    "mutation supported": "mutation",
    "object identity": "identity",
    "player authority": "authority",
    "player identity": "identity",
    "player principal evidence replaced": "player_principal_evidence",
    "player-principal evidence replaced": "player_principal_evidence",
    "replaces player principal evidence": "player_principal_evidence",
    "replaces player principal lifecycle evidence": "player_principal_evidence",
    "replaces player-principal evidence": "player_principal_evidence",
    "replaces player-principal lifecycle evidence": "player_principal_evidence",
    "public abi": "public_abi",
    "public sdk allowed": "public_sdk",
    "public sdk unblocked": "public_sdk",
    "public sdk unlocked": "public_sdk",
    "return override enabled": "return_override",
    "return override ready": "return_override",
    "return override supported": "return_override",
    "return value override": "return_override",
    "return value override enabled": "return_override",
    "return value override ready": "return_override",
    "return overrides": "return_override",
    "runtime evidence accepted": "approved_runtime_evidence",
    "runtime evidence present": "approved_runtime_evidence",
    "runtime evidence ready": "approved_runtime_evidence",
    "runtime hook ready": "runtime_hooks",
    "runtime hooks enabled": "runtime_hooks",
    "runtime hooks ready": "runtime_hooks",
    "runtime support active": "runtime_ready",
    "runtime support enabled": "runtime_ready",
    "runtime support unblocked": "runtime_ready",
    "runtime support unlocked": "runtime_ready",
    "runtime support ready": "runtime_ready",
    "runtime support supported": "runtime_ready",
    "umbrella leaf promoted": "umbrella_leaf_promotion",
    "umbrella leaf promotion": "umbrella_leaf_promotion",
    "p0 dependency chain complete": "p0_dependency_chain",
    "p0 dependency chain ready": "p0_dependency_chain",
    "v1 complete": "v1_completion",
    "v1 completion": "v1_completion",
    "v1 completion allowed": "v1_completion",
    "v1 completion unblocked": "v1_completion",
    "v1 completion unlocked": "v1_completion",
    "v1 done": "v1_completion",
    "v1 ready": "v1_completion",
    "v1 support active": "v1_completion",
    "v1 support enabled": "v1_completion",
    "v1 support unblocked": "v1_completion",
    "v1 support unlocked": "v1_completion",
    "v1 support ready": "v1_completion",
    "v1 support supported": "v1_completion",
    "version 1 complete": "v1_completion",
}
FORBIDDEN_SUPPORT_STATUS_KEYS = {
    "public_sdk_support",
    "runtime_support",
    "runtime_v1_support",
    "stable_sdk_support",
    "support_tier",
    "support_tier_status",
    "v1_sdk_support",
    "v1_support",
}
SOURCE_READINESS_ALIAS_KEYS = {
    "approved_runtime_evidence",
    "approved_runtime_evidence_status",
    "source_accepted",
    "source_available",
    "source_label",
    "source_labels",
    "source_marker",
    "source_markers",
    "source_readiness",
    "source_ready",
    "source_stable",
    "source_status",
    "source_support",
    "source_tier",
    "source_validated",
    "source_validation",
    "runtime_evidence",
    "runtime_evidence_status",
    "player_principal_runtime_evidence",
    "player_principal_runtime_evidence_status",
}
POSITIVE_SOURCE_STATUS_VALUES = {
    "accepted",
    "active",
        "approved",
        "available",
        "allowed",
        "complete",
        "completed",
        "enabled",
    "passed",
    "promoted",
    "public",
    "public_ready",
    "ready",
    "release_ready",
    "release_supported",
    "runtime",
    "runtime_ready",
    "sdk_ready",
    "stable",
    "stable_ready",
        "supported",
        "true",
        "unblocked",
        "unlocked",
        "validated",
        "v1_ready",
    }
CONTEXTUAL_READINESS_STATUS_KEYS = {
    "accepted",
    "active",
    "approved",
    "allowed",
    "complete",
    "enabled",
    "outcome",
    "passed",
    "promoted",
    "readiness",
    "ready",
    "result",
    "stable",
    "state",
    "status",
    "unblocked",
    "unlocked",
    "validated",
}
CONTEXTUAL_READINESS_PROGRESS_KEYS = {
    "claim_progress",
    "count",
    "counts",
    "counting",
    "credit",
    "credits",
    "claim_credit",
    "claim_credits",
    "completion_credit",
    "completion_credits",
    "completion_contribution",
    "completion_percent",
    "completion_progress",
    "completion_ratio",
    "contribution",
    "percent",
    "progress",
    "progress_contribution",
    "progress_ratio",
    "ratio",
    "surface_count",
}
CONTEXTUAL_READINESS_KEY_RE = re.compile(
    r"(?:approved[_-]?runtime[_-]?evidence|beta|public|sdk|api|abi|module|callback|descriptor|"
    r"capability|runtime|capture|pack|plan|multi[_-]?surface|live[_-]?ops|source|v1|p0|"
    r"complete|completion|dependency[_-]?chain|stable|promotion|resource[_-]?handle|"
    r"return[_-]?(?:value[_-]?)?override|identity|lookup|mutation|player[_-]?principal|principal|support|tier)",
    re.IGNORECASE,
)
CONTEXTUAL_READINESS_CONTAINER_KEYS = {
    "beta_capture",
    "beta_capture_pack",
    "beta_capture_plan",
    "beta_capture_prep",
    "capture_pack",
    "capture_plan",
    "candidate",
    "multi_surface_beta_capture",
    "multi_surface_beta_capture_pack",
    "multi_surface_beta_capture_plan",
    "package_shape",
    "plugin_hub",
    "public_sdk",
    "readiness",
    "runtime",
    "support_tier",
    "target_set",
    "v1",
}
AFFIRMATIVE_SUPPORT_STATUS_RE = re.compile(
    r"\b(?:active|available|allowed|enabled|promoted|published|ready|release[-_\s]+supported|"
    r"stable|supported|unblocked|unlocked)\b",
    re.IGNORECASE,
)
PUBLIC_MISSION_C_API_RE = re.compile(
    r"\b(?:(?:Register|Unregister)Mission[A-Za-z0-9_]*|"
    r"OBELISK_[A-Z0-9_]*MISSION[A-Z0-9_]*|"
    r"Obelisk[A-Za-z0-9_]*Mission[A-Za-z0-9_]*|"
    r"Mission[A-Za-z0-9_]*(?:Event|Descriptor|Callback|Resource|Policy)[A-Za-z0-9_]*)\b"
)
PLUGIN_MANAGER_MISSION_WIRING_RE = re.compile(
    r"\b(?:(?:Plugin)?(?:Register|Unregister|Describe|Dispatch)Mission[A-Za-z0-9_]*|"
    r"OBELISK_[A-Z0-9_]*MISSION[A-Z0-9_]*|"
    r"Obelisk[A-Za-z0-9_]*Mission[A-Za-z0-9_]*|"
    r"Mission[A-Za-z0-9_]*(?:Event|Descriptor|Callback|Resource|Policy)[A-Za-z0-9_]*)\b|"
    r"MissionCopiedBoolEventDispatcher::Get\(\)\.(?!UnregisterCallbacksForOwner\b)[A-Za-z_][A-Za-z0-9_]*"
)
PUBLIC_MISSION_DOC_RE = re.compile(
    r"\bmission\b|\bMission[A-Za-z0-9_]*\b|\bOBELISK_[A-Z0-9_]*MISSION[A-Z0-9_]*\b"
)
NEGATIVE_MISSION_DOC_KEYS = {
    "blocked",
    "blocked_public_contract",
    "explicitly_excluded",
    "exclusions",
    "guardrails",
    "non_claim",
    "non_claims",
    "not_promoted",
    "not_promoted_surfaces",
}
RUNTIME_SHARED_CMAKE_TARGETS = {
    "obelisk",
    "obelisk_runtime",
    "obelisk_shared",
    "runtime",
    "shared",
}
REPORT_FORBIDDEN_TRUE_READY_KEYS = FORBIDDEN_TRUE_READY_KEYS | {
    "identity_ready",
    "lookup_ready",
    "promotion_ready",
    "runtime_observer_approved",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Mission copied-bool candidate readiness without promoting a public SDK."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Offline artifact root.")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Mission copied-bool policy-slice manifest. Defaults to --root/mission-copied-bool-policy-slice.json.",
    )
    parser.add_argument(
        "--expected-manifest-sha256",
        default=EXPECTED_MANIFEST_SHA256,
        help="Expected direct manifest SHA256. Defaults to the reviewed durable artifact.",
    )
    parser.add_argument(
        "--skip-artifact-gates",
        action="store_true",
        help="Skip consume/promote gate subprocesses for hermetic policy-fixture tests.",
    )
    parser.add_argument(
        "--fixture-boundary-only",
        action="store_true",
        help=(
            "Validate only the repo fixture-regenerated Mission copied-bool boundary; "
            "does not inspect --root/--manifest or claim attestation/public/runtime readiness."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def read_text_file(path: Path, blockers: list[dict[str, Any]], label: str) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        append_blocker(blockers, "frontier_file_unreadable", label=label, path=str(path), detail=str(exc))
        return None


def strip_cmake_comments(text: str) -> str:
    stripped_lines: list[str] = []
    for line in text.splitlines():
        in_quote = False
        escaped = False
        kept: list[str] = []
        for char in line:
            if escaped:
                kept.append(char)
                escaped = False
                continue
            if char == "\\":
                kept.append(char)
                escaped = True
                continue
            if char == '"':
                in_quote = not in_quote
                kept.append(char)
                continue
            if char == "#" and not in_quote:
                break
            kept.append(char)
        stripped_lines.append("".join(kept))
    return "\n".join(stripped_lines)


def iter_cmake_commands(text: str) -> list[tuple[str, str]]:
    commands: list[tuple[str, str]] = []
    cleaned = strip_cmake_comments(text)
    index = 0
    while index < len(cleaned):
        match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", cleaned[index:])
        if not match:
            break
        name = match.group(1)
        body_start = index + match.end()
        cursor = body_start
        depth = 1
        in_quote = False
        escaped = False
        while cursor < len(cleaned):
            char = cleaned[cursor]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_quote = not in_quote
            elif not in_quote and char == "(":
                depth += 1
            elif not in_quote and char == ")":
                depth -= 1
                if depth == 0:
                    commands.append((name.casefold(), cleaned[body_start:cursor]))
                    cursor += 1
                    break
            cursor += 1
        index = cursor
    return commands


def split_cmake_args(body: str) -> list[str]:
    return [arg.strip('"') for arg in re.findall(r'"[^"]*"|\S+', body)]


def cmake_arg_matches_source(arg: str, source: str) -> bool:
    normalized = arg.replace("\\", "/").strip('"')
    return normalized == source or normalized.endswith(f"/{source}")


def is_runtime_or_shared_target(command: str, args: list[str]) -> bool:
    if not args:
        return False
    target = args[0].casefold()
    if target in RUNTIME_SHARED_CMAKE_TARGETS:
        return True
    if target.endswith("_runtime") or target.endswith("_shared"):
        return True
    if command == "add_library" and len(args) > 1 and args[1].upper() == "SHARED":
        return True
    return False


IGNORED_CMAKE_PATH_PARTS = frozenset((".git", "build", "local", "__pycache__", ".pytest_cache"))


def candidate_cmake_files(repo_root: Path) -> list[Path]:
    candidates = {repo_root / "CMakeLists.txt"}
    for pattern in ("**/CMakeLists.txt", "**/*.cmake"):
        for path in repo_root.glob(pattern):
            relative_parts = path.relative_to(repo_root).parts
            if any(part in IGNORED_CMAKE_PATH_PARTS for part in relative_parts):
                continue
            candidates.add(path)
    return sorted(candidates)


def validate_cmake_mission_hook_boundary(repo_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    blocker_count_before = len(blockers)
    cmake_paths = candidate_cmake_files(repo_root)
    checked_targets: list[str] = []
    checked_files: list[str] = []
    for cmake_path in cmake_paths:
        text = read_text_file(cmake_path, blockers, str(cmake_path.relative_to(repo_root)))
        if text is None:
            continue
        checked_files.append(str(cmake_path))
        for command, body in iter_cmake_commands(text):
            if command not in {"add_library", "add_executable", "target_sources"}:
                continue
            args = split_cmake_args(body)
            if not args or not any(cmake_arg_matches_source(arg, MISSION_HOOK_SOURCE) for arg in args[1:]):
                continue
            target = args[0]
            checked_targets.append(target)
            if is_runtime_or_shared_target(command, args):
                append_blocker(
                    blockers,
                    "mission_hook_in_runtime_or_shared_target",
                    path=str(cmake_path),
                    command=command,
                    target=target,
                    source=MISSION_HOOK_SOURCE,
                )
    return {
        "status": "accepted" if len(blockers) == blocker_count_before else "blocked",
        "paths": checked_files,
        "mission_hook_targets": sorted(set(checked_targets)),
    }


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def extract_braced_body_after(text: str, start: int) -> str | None:
    body_start = text.find("{", start)
    if body_start == -1:
        return None
    depth = 0
    in_string = False
    in_char = False
    escaped = False
    for index in range(body_start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if in_string:
            if char == '"':
                in_string = False
            continue
        if in_char:
            if char == "'":
                in_char = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "'":
            in_char = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[body_start + 1:index]
    return None


def extract_plugin_manager_unregister_body(text: str) -> str | None:
    match = re.search(r"\bbool\s+PluginManager::UnregisterPluginCallbacks\s*\(", text)
    if match is None:
        return None
    return extract_braced_body_after(text, match.end())


def validate_public_api_header_mission_boundary(repo_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    header_path = repo_root / PUBLIC_API_HEADER
    text = read_text_file(header_path, blockers, str(PUBLIC_API_HEADER))
    if text is None:
        return {"status": "blocked", "path": str(header_path)}

    matches = sorted(set(PUBLIC_MISSION_C_API_RE.findall(strip_c_comments(text))))
    for symbol in matches:
        append_blocker(
            blockers,
            "public_mission_sdk_symbol_in_api_header",
            path=str(header_path),
            symbol=symbol,
        )
    return {"status": "accepted" if not matches else "blocked", "path": str(header_path), "matches": matches}


def plugin_manager_guardrail_exception_mentions_mission_dispatcher(text: str) -> bool:
    match = re.search(
        r"\bCOPIED_DISPATCHER_CLEANUP_EXCEPTIONS\s*=\s*\{(?P<body>.*?)\n\}",
        text,
        re.DOTALL,
    )
    return match is not None and MISSION_COPIED_BOOL_DISPATCHER in match.group("body")


def validate_mission_public_frontier_owner_cleanup(
    repo_root: Path,
    blockers: list[dict[str, Any]],
    *,
    public_api_matches: list[str],
    public_gameplay_event_matches: list[dict[str, str]],
) -> dict[str, Any]:
    blocker_count_before = len(blockers)
    plugin_manager_path = repo_root / PLUGIN_MANAGER_SOURCE
    plugin_manager_text = read_text_file(plugin_manager_path, blockers, str(PLUGIN_MANAGER_SOURCE))
    if plugin_manager_text is None:
        return {
            "status": "blocked",
            "path": str(plugin_manager_path),
            "public_frontier_detected": bool(public_api_matches or public_gameplay_event_matches),
            "plugin_manager_wiring_matches": [],
            "owner_cleanup_present": False,
            "owner_cleanup_guardrail_present": False,
        }

    stripped_plugin_manager = strip_c_comments(plugin_manager_text)
    plugin_manager_wiring_matches = sorted(
        {match.group(0) for match in PLUGIN_MANAGER_MISSION_WIRING_RE.finditer(stripped_plugin_manager)}
    )
    for symbol in plugin_manager_wiring_matches:
        append_blocker(
            blockers,
            "mission_plugin_facing_wiring_in_plugin_manager",
            path=str(plugin_manager_path),
            symbol=symbol,
        )

    cleanup_body = extract_plugin_manager_unregister_body(stripped_plugin_manager)
    cleanup_body_found = cleanup_body is not None
    owner_cleanup_present = cleanup_body_found and MISSION_COPIED_BOOL_OWNER_CLEANUP in cleanup_body
    public_frontier_detected = bool(
        public_api_matches or public_gameplay_event_matches or plugin_manager_wiring_matches
    )

    guardrail_text: str | None = None
    owner_cleanup_guardrail_present = False
    stale_internal_exception = False
    if public_frontier_detected:
        if not cleanup_body_found:
            append_blocker(
                blockers,
                "plugin_manager_unregister_callbacks_unparseable",
                path=str(plugin_manager_path),
            )
        if not owner_cleanup_present:
            append_blocker(
                blockers,
                "mission_public_frontier_missing_plugin_manager_owner_cleanup",
                path=str(plugin_manager_path),
                required=MISSION_COPIED_BOOL_OWNER_CLEANUP,
                public_api_matches=public_api_matches,
                public_gameplay_event_matches=public_gameplay_event_matches,
                plugin_manager_wiring_matches=plugin_manager_wiring_matches,
            )

        guardrail_path = repo_root / PLUGIN_MANAGER_GUARDRAIL_TEST
        guardrail_text = read_text_file(guardrail_path, blockers, str(PLUGIN_MANAGER_GUARDRAIL_TEST))
        if guardrail_text is not None:
            owner_cleanup_guardrail_present = MISSION_COPIED_BOOL_OWNER_CLEANUP in guardrail_text
            stale_internal_exception = plugin_manager_guardrail_exception_mentions_mission_dispatcher(guardrail_text)
        if not owner_cleanup_guardrail_present:
            append_blocker(
                blockers,
                "mission_public_frontier_missing_owner_cleanup_guardrail",
                path=str(guardrail_path),
                required=MISSION_COPIED_BOOL_OWNER_CLEANUP,
            )
        if stale_internal_exception:
            append_blocker(
                blockers,
                "mission_public_frontier_still_internal_test_only_cleanup_exception",
                path=str(guardrail_path),
                dispatcher=MISSION_COPIED_BOOL_DISPATCHER,
            )

    return {
        "status": "accepted" if len(blockers) == blocker_count_before else "blocked",
        "path": str(plugin_manager_path),
        "public_frontier_detected": public_frontier_detected,
        "plugin_manager_wiring_matches": plugin_manager_wiring_matches,
        "owner_cleanup_required": public_frontier_detected,
        "owner_cleanup_present": owner_cleanup_present,
        "owner_cleanup_guardrail_present": owner_cleanup_guardrail_present,
        "stale_internal_test_only_exception": stale_internal_exception,
    }


def collect_json_mission_doc_matches(value: Any, path: str = "$") -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            key_normalized = normalize_claim_key(key)
            if key_normalized in NEGATIVE_MISSION_DOC_KEYS or key_normalized.startswith("not_promoted"):
                continue
            if isinstance(key, str) and PUBLIC_MISSION_DOC_RE.search(key):
                matches.append({"path": child_path, "value": key})
            matches.extend(collect_json_mission_doc_matches(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(collect_json_mission_doc_matches(child, f"{path}[{index}]"))
    elif isinstance(value, str) and PUBLIC_MISSION_DOC_RE.search(value):
        matches.append({"path": path, "value": value})
    return matches


def validate_public_gameplay_events_mission_boundary(repo_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    doc_path = repo_root / PUBLIC_GAMEPLAY_EVENTS_DOC
    text = read_text_file(doc_path, blockers, str(PUBLIC_GAMEPLAY_EVENTS_DOC))
    if text is None:
        return {"status": "blocked", "path": str(doc_path)}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "public_gameplay_events_json_malformed", path=str(doc_path), detail=str(exc))
        return {"status": "blocked", "path": str(doc_path)}

    matches = collect_json_mission_doc_matches(parsed)
    for match in matches:
        append_blocker(
            blockers,
            "public_mission_gameplay_event_or_descriptor",
            path=str(doc_path),
            field=match["path"],
            value=match["value"],
        )
    return {"status": "accepted" if not matches else "blocked", "path": str(doc_path), "matches": matches}


def validate_offline_repo_frontier(repo_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    frontier_blockers_before = len(blockers)
    cmake = validate_cmake_mission_hook_boundary(repo_root, blockers)
    api_header = validate_public_api_header_mission_boundary(repo_root, blockers)
    public_gameplay_events = validate_public_gameplay_events_mission_boundary(repo_root, blockers)
    owner_cleanup = validate_mission_public_frontier_owner_cleanup(
        repo_root,
        blockers,
        public_api_matches=api_header.get("matches", []),
        public_gameplay_event_matches=public_gameplay_events.get("matches", []),
    )
    return {
        "status": "accepted" if len(blockers) == frontier_blockers_before else "blocked",
        "mission_internal_test_only": len(blockers) == frontier_blockers_before,
        "cmake": cmake,
        "api_header": api_header,
        "public_gameplay_events": public_gameplay_events,
        "mission_public_frontier_owner_cleanup": owner_cleanup,
    }


def validate_report_readiness_frontier(value: Any, blockers: list[dict[str, Any]], path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if child is True and key in REPORT_FORBIDDEN_TRUE_READY_KEYS:
                append_blocker(blockers, "report_public_runtime_readiness_overclaim", field=child_path)
            validate_report_readiness_frontier(child, blockers, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_report_readiness_frontier(child, blockers, f"{path}[{index}]")


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


def read_policy(manifest: Path, blockers: list[dict[str, Any]], expected_sha256: str) -> dict[str, Any] | None:
    try:
        content = manifest.read_bytes()
        manifest_sha256 = hashlib.sha256(content).hexdigest()
        parsed = json.loads(content.decode("utf-8"))
    except OSError as exc:
        append_blocker(blockers, "manifest_unreadable", path=str(manifest), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "manifest_malformed", path=str(manifest), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        append_blocker(blockers, "manifest_not_object", path=str(manifest))
        return None
    if manifest_sha256 != expected_sha256:
        append_blocker(
            blockers,
            "manifest_sha256_mismatch",
            expected=expected_sha256,
            value=manifest_sha256,
        )
    parsed["_obelisk_manifest_sha256"] = manifest_sha256
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


def field_target(field: str) -> str:
    return field.rsplit(".", 1)[0]


def build_beta_capture_prep() -> dict[str, Any]:
    targets: list[dict[str, Any]] = []
    for target in sorted(EXPECTED_INPUT_TARGETS):
        targets.append(
            {
                "target": target,
                "surface": BETA_CAPTURE_SURFACE,
                "target_set": INPUT_TARGET_SET,
                "status": BETA_CAPTURE_TARGET_STATUS,
                "source_evidence": "candidate_only_mission_copied_bool_policy_slice",
                "capture_gate": BETA_CAPTURE_GATE,
                "approved_runtime_evidence_ready": False,
                "clears_approved_runtime_evidence_missing": False,
                "player_principal_runtime_evidence_ready": False,
                "replaces_player_principal_evidence": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "runtime_capture_ready": False,
                "sdk_ready": False,
                "sdk_progress": 0,
                "p0_dependency_chain_ready": False,
                "counts_toward_p0_dependency_chain_claim": False,
                "copied_bool_fields": sorted(field for field in EXPECTED_COPIED_FIELDS if field_target(field) == target),
                "redacted_fields": sorted(field for field in EXPECTED_REDACTED_FIELDS if field_target(field) == target),
                "recognition_only": target not in EXPECTED_COPIED_TARGETS,
            }
        )
    return {
        "status": BETA_CAPTURE_STATUS,
        "surface": BETA_CAPTURE_SURFACE,
        "target_set": INPUT_TARGET_SET,
        "source_evidence": "candidate_only_mission_copied_bool_policy_slice",
        "capture_gate": BETA_CAPTURE_GATE,
        "multi_surface_plan_role": "mission_copied_bool_surface_candidate_prep_only",
        "approved_runtime_evidence_ready": False,
        "runtime_evidence_ready": False,
        "clears_approved_runtime_evidence_missing": False,
        "approved_runtime_evidence_missing_cleared": False,
        "player_principal_runtime_evidence_ready": False,
        "replaces_player_principal_evidence": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "debug_capture_ready": False,
        "sdk_ready": False,
        "sdk_progress": 0,
        "p0_dependency_chain_ready": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "targets": targets,
        "non_claims": [
            "future beta/debug capture target planning only",
            "dedicated beta capture acceptance check is required before runtime use",
            "does not clear approved_runtime_evidence_missing",
            "does not replace player-principal lifecycle evidence",
        ],
    }


def validate_beta_capture_entry(entry: Any, blockers: list[dict[str, Any]], path: str) -> str | None:
    if not isinstance(entry, dict):
        append_blocker(blockers, "beta_capture_target_malformed", path=path)
        return None
    target = entry.get("target")
    if not isinstance(target, str) or target not in EXPECTED_INPUT_TARGETS:
        append_blocker(blockers, "beta_capture_target_mismatch", path=f"{path}.target", target=target)
    if entry.get("surface") not in {BETA_CAPTURE_SURFACE, "multi_surface", None}:
        append_blocker(blockers, "beta_capture_surface_mismatch", path=f"{path}.surface", value=entry.get("surface"))
    status = entry.get("status")
    if status not in {BETA_CAPTURE_TARGET_STATUS, BETA_CAPTURE_STATUS, "candidate-only", "candidate-prep", "candidate_prep", None}:
        append_blocker(blockers, "beta_capture_target_status_mismatch", path=f"{path}.status", value=status)
    if entry.get("capture_gate") not in {BETA_CAPTURE_GATE, None}:
        append_blocker(blockers, "beta_capture_gate_mismatch", path=f"{path}.capture_gate", value=entry.get("capture_gate"))
    for key in BETA_CAPTURE_FALSE_OR_ZERO_FIELDS:
        if key in entry and not claim_value_is_false_or_zero(entry.get(key)):
            append_blocker(
                blockers,
                "beta_capture_readiness_overclaim",
                path=f"{path}.{key}",
                value=entry.get(key),
            )
    return target if isinstance(target, str) else None


def validate_beta_capture_artifact(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        append_blocker(blockers, "beta_capture_artifact_malformed", path=path)
        return
    status = value.get("status")
    if status not in {BETA_CAPTURE_STATUS, "candidate-only", "candidate-prep", "candidate_prep", "future_capture_plan_only"}:
        append_blocker(blockers, "beta_capture_artifact_status_mismatch", path=f"{path}.status", value=status)
    if value.get("surface") not in {BETA_CAPTURE_SURFACE, "multi_surface", None}:
        append_blocker(blockers, "beta_capture_artifact_surface_mismatch", path=f"{path}.surface", value=value.get("surface"))
    if value.get("capture_gate") not in {BETA_CAPTURE_GATE, None}:
        append_blocker(blockers, "beta_capture_artifact_gate_mismatch", path=f"{path}.capture_gate", value=value.get("capture_gate"))
    for key in BETA_CAPTURE_FALSE_OR_ZERO_FIELDS:
        if key in value and not claim_value_is_false_or_zero(value.get(key)):
            append_blocker(blockers, "beta_capture_readiness_overclaim", path=f"{path}.{key}", value=value.get(key))
    targets = value.get("targets")
    if targets is None:
        return
    if not isinstance(targets, list):
        append_blocker(blockers, "beta_capture_targets_malformed", path=f"{path}.targets")
        return
    for index, entry in enumerate(targets):
        validate_beta_capture_entry(entry, blockers, f"{path}.targets[{index}]")


def validate_generated_from(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    generated_from = policy.get("generated_from")
    if not isinstance(generated_from, dict):
        append_blocker(blockers, "generated_from_missing")
        return {}
    if generated_from.get("snapshot_schema") != "obelisk.ufunction-chain.snapshot.v1":
        append_blocker(blockers, "snapshot_schema_mismatch", value=generated_from.get("snapshot_schema"))
    snapshots = generated_from.get("input_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 4:
        append_blocker(
            blockers,
            "input_snapshot_count_mismatch",
            expected=4,
            value=len(snapshots) if isinstance(snapshots, list) else None,
        )
        return {}

    sources: dict[str, dict[str, str]] = {}
    targets: set[str] = set()
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            append_blocker(blockers, "input_snapshot_entry_invalid", index=index)
            continue
        snapshot_id = snapshot.get("id")
        snapshot_sha256 = snapshot.get("sha256")
        target = snapshot.get("target")
        if not isinstance(snapshot_id, str) or not snapshot_id:
            append_blocker(blockers, "input_snapshot_id_invalid", index=index)
            continue
        if snapshot_id in sources:
            append_blocker(blockers, "input_snapshot_id_duplicate", index=index, snapshot_id=snapshot_id)
        if not isinstance(snapshot_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256):
            append_blocker(blockers, "input_snapshot_sha256_invalid", index=index, snapshot_id=snapshot_id)
            continue
        if not isinstance(target, str) or target not in EXPECTED_INPUT_TARGETS:
            append_blocker(blockers, "input_snapshot_target_invalid", index=index, snapshot_id=snapshot_id, target=target)
            continue
        sources[snapshot_id] = {"sha256": snapshot_sha256, "target": target}
        targets.add(target)
    if targets != EXPECTED_INPUT_TARGETS:
        append_blocker(
            blockers,
            "input_snapshot_targets_mismatch",
            missing=sorted(EXPECTED_INPUT_TARGETS - targets),
            unexpected=sorted(targets - EXPECTED_INPUT_TARGETS),
        )
    return sources


def validate_source_snapshot(
    entry: dict[str, Any],
    *,
    index: int,
    field_key: str,
    reason_prefix: str,
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    source_snapshot = entry.get("source_snapshot")
    source_snapshot_sha256 = entry.get("source_snapshot_sha256")
    if not isinstance(source_snapshot, str) or source_snapshot not in sources:
        append_blocker(blockers, f"{reason_prefix}_source_snapshot_unknown", index=index, field=entry.get(field_key))
        return
    source = sources[source_snapshot]
    if source_snapshot_sha256 != source["sha256"]:
        append_blocker(
            blockers,
            f"{reason_prefix}_source_snapshot_sha256_mismatch",
            index=index,
            field=entry.get(field_key),
            expected=source["sha256"],
            value=source_snapshot_sha256,
        )
    if entry.get("target") != source["target"]:
        append_blocker(
            blockers,
            f"{reason_prefix}_source_snapshot_target_mismatch",
            index=index,
            field=entry.get(field_key),
            expected=source["target"],
            value=entry.get("target"),
        )


def validate_copied_bool_entries(
    policy: dict[str, Any],
    copied_fields: set[str],
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    entries = policy.get("copied_bools")
    if not isinstance(entries, list):
        append_blocker(blockers, "copied_bools_missing")
        return
    if len(entries) != 5:
        append_blocker(blockers, "copied_bool_count_mismatch", expected=5, value=len(entries))

    entry_fields: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            append_blocker(blockers, "copied_bool_entry_not_object", index=index)
            continue
        copied_field = entry.get("copied_field")
        if isinstance(copied_field, str):
            entry_fields.add(copied_field)
        if copied_field not in copied_fields:
            append_blocker(blockers, "copied_bool_entry_field_unexpected", index=index, copied_field=copied_field)
        required_values = {
            "type": "bool",
            "property_class": "BoolProperty",
            "evidence_status": "copied-mission-bool-only",
            "bool_field_size": 1,
            "bool_byte_offset": 0,
            "byte_mask": "0x01",
            "field_mask": "0xff",
            "native_bool": False,
        }
        for key, expected in required_values.items():
            if entry.get(key) != expected:
                append_blocker(
                    blockers,
                    "copied_bool_entry_metadata_mismatch",
                    index=index,
                    copied_field=copied_field,
                    field=key,
                    expected=expected,
                    value=entry.get(key),
                )
        validate_source_snapshot(
            entry,
            index=index,
            field_key="copied_field",
            reason_prefix="copied_bool_entry",
            sources=sources,
            blockers=blockers,
        )
    if entry_fields != copied_fields:
        append_blocker(
            blockers,
            "copied_bool_entry_coverage_mismatch",
            missing=sorted(copied_fields - entry_fields),
            unexpected=sorted(entry_fields - copied_fields),
        )


def validate_redacted_source_entries(
    policy: dict[str, Any],
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    entries = policy.get("redacted_mission_fields")
    if not isinstance(entries, list):
        append_blocker(blockers, "redacted_mission_fields_missing")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            append_blocker(blockers, "redacted_mission_field_entry_not_object", index=index)
            continue
        validate_source_snapshot(
            entry,
            index=index,
            field_key="redacted_field",
            reason_prefix="redacted_mission_field",
            sources=sources,
            blockers=blockers,
        )


def allowed_prefix_claim_is_negated_or_excluded(text: str, start: int, end: int) -> bool:
    clause_start = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start)) + 1
    clause_end_candidates = [
        index for index in (text.find(".", end), text.find("\n", end), text.find(";", end)) if index != -1
    ]
    clause_end = min(clause_end_candidates) if clause_end_candidates else len(text)
    clause = text[clause_start:clause_end]
    return bool(NEGATED_OR_EXCLUDED_CONTEXT_RE.search(clause))


def collect_allowed_prefix_affirmative_overclaims(policy: dict[str, Any]) -> list[tuple[str, str, str]]:
    overclaims: list[tuple[str, str, str]] = []
    for trail, raw_value in offline_gate.collect_string_fields(policy):
        if not any(trail.startswith(prefix) for prefix in ALLOWED_OVERCLAIM_TEXT_PREFIXES):
            continue
        for subject in ALLOWED_PREFIX_CLAIM_SUBJECT_RE.finditer(raw_value):
            window_start = max(0, subject.start() - 56)
            window_end = min(len(raw_value), subject.end() + 56)
            window = raw_value[window_start:window_end]
            if not AFFIRMATIVE_OVERCLAIM_CONTEXT_RE.search(window):
                continue
            if allowed_prefix_claim_is_negated_or_excluded(raw_value, subject.start(), subject.end()):
                continue
            overclaims.append((trail, raw_value, subject.group(0)))
            break
    return overclaims


def normalize_claim_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return separated.casefold().replace("-", "_").replace(" ", "_")


def normalize_trail_leaf_key(trail: str) -> str:
    leaf = trail.rsplit(".", 1)[-1]
    leaf = re.sub(r"\[\d+\]$", "", leaf)
    return normalize_claim_key(leaf)


def positive_source_alias_value(value: str) -> bool:
    normalized = normalize_claim_key(value)
    return normalized in POSITIVE_SOURCE_STATUS_VALUES or normalized.endswith("_ready")


def positive_numeric_claim(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def positive_progress_claim(value: Any) -> bool:
    return positive_numeric_claim(value) or (
        isinstance(value, str) and POSITIVE_PROGRESS_RATIO_RE.fullmatch(value) is not None
    )


def claim_value_is_false_or_zero(value: Any) -> bool:
    return value is False or value is None or value == 0


def positive_contextual_readiness_value(value: Any) -> bool:
    if value is True:
        return True
    if positive_numeric_claim(value):
        return True
    if not isinstance(value, str):
        return False
    return positive_source_alias_value(value)


def contextual_readiness_key(normalized_key: str) -> bool:
    if normalized_key in {
        "accepted_for_internal_planning",
        "copied_bool_count",
        "redacted_field_count",
    }:
        return False
    return normalized_key in CONTEXTUAL_READINESS_CONTAINER_KEYS or bool(
        CONTEXTUAL_READINESS_KEY_RE.search(normalized_key)
    )


def contextual_readiness_progress_key(normalized_key: str) -> bool:
    return normalized_key in CONTEXTUAL_READINESS_PROGRESS_KEYS or any(
        normalized_key.endswith(f"_{key}") for key in CONTEXTUAL_READINESS_PROGRESS_KEYS
    )


def collect_contextual_readiness_object_overclaims(
    value: Any,
    *,
    trail: str = "$",
    claim_context: bool = False,
) -> list[tuple[str, str]]:
    overclaims: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            normalized_key = normalize_claim_key(key)
            child_context = claim_context or contextual_readiness_key(normalized_key)
            if (
                child_context
                and normalized_key in CONTEXTUAL_READINESS_STATUS_KEYS
                and positive_contextual_readiness_value(child)
            ):
                overclaims.append((child_trail, normalized_key))
            elif (
                child_context
                and contextual_readiness_progress_key(normalized_key)
                and positive_progress_claim(child)
            ):
                overclaims.append((child_trail, normalized_key))
            if isinstance(child, (dict, list)):
                overclaims.extend(
                    collect_contextual_readiness_object_overclaims(
                        child,
                        trail=child_trail,
                        claim_context=child_context,
                    )
                )
        return overclaims
    if isinstance(value, list):
        for index, child in enumerate(value):
            overclaims.extend(
                collect_contextual_readiness_object_overclaims(
                    child,
                    trail=f"{trail}[{index}]",
                    claim_context=claim_context,
                )
            )
        return overclaims
    if claim_context and (value is True or (isinstance(value, str) and positive_source_alias_value(value))):
        overclaims.append((trail, "value"))
    return overclaims


def validate_internal_only_boundaries(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    gate_blockers = offline_gate.validate_mission_copied_bool_policy_slice_manifest(
        policy,
        label="mission-copied-bool-readiness",
        mode="consume",
    )
    for blocker in gate_blockers:
        if not isinstance(blocker, dict):
            append_blocker(blockers, "offline_artifact_gate_blocker_unparseable", value=blocker)
            continue
        reason = blocker.get("reason")
        append_blocker(
            blockers,
            reason if isinstance(reason, str) else "offline_artifact_gate_blocker_missing_reason",
            source="offline_artifact_gate",
            label=blocker.get("label"),
            expected=blocker.get("expected"),
            recorded=blocker.get("recorded"),
        )

    for trail, _ in offline_gate.collect_ready_overclaims(policy):
        append_blocker(blockers, "readiness_overclaim", field=trail)
    for trail, claim in collect_contextual_readiness_object_overclaims(policy):
        append_blocker(blockers, "mission_candidate_claim_overclaim", field=trail, claim=claim)
    for trail, value in offline_gate.collect_bool_fields(policy):
        key = normalize_trail_leaf_key(trail)
        if key == "not_artifact_gate" and value is False:
            append_blocker(blockers, "not_artifact_gate_contradiction", field=trail)
        if key == "consume_only" and value is False:
            append_blocker(blockers, "consume_only_not_true", field=trail)
        if value is True and key in SOURCE_READINESS_ALIAS_KEYS:
            append_blocker(blockers, "mission_candidate_claim_overclaim", field=trail, claim=key)
        if value is True and key in FORBIDDEN_TRUE_READY_KEYS:
            append_blocker(blockers, "runtime_public_readiness_overclaim", field=trail)
    for trail, _, reason in offline_gate.collect_candidate_public_overclaims(
        policy,
        allowed_prefixes=ALLOWED_OVERCLAIM_TEXT_PREFIXES,
    ):
        append_blocker(blockers, "runtime_public_claim_overclaim", field=trail, claim=reason)
    for trail, raw_value in offline_gate.collect_string_fields(policy):
        for match in CANDIDATE_CAPTURE_PROMOTION_RE.finditer(raw_value):
            append_blocker(
                blockers,
                "mission_candidate_capture_overclaim",
                field=trail,
                claim=match.group(0),
            )
        if any(trail.startswith(prefix) for prefix in ALLOWED_OVERCLAIM_TEXT_PREFIXES):
            continue
        key = normalize_trail_leaf_key(trail)
        if key in SOURCE_READINESS_ALIAS_KEYS and positive_source_alias_value(raw_value):
            append_blocker(blockers, "mission_candidate_claim_overclaim", field=trail, claim=key)
        if key in FORBIDDEN_SUPPORT_STATUS_KEYS and AFFIRMATIVE_SUPPORT_STATUS_RE.search(raw_value):
            append_blocker(blockers, "mission_candidate_claim_overclaim", field=trail, claim=key)
        text = raw_value.casefold()
        for needle, reason in MISSION_CANDIDATE_FORBIDDEN_CLAIM_PHRASES.items():
            if needle in text:
                append_blocker(blockers, "mission_candidate_claim_overclaim", field=trail, claim=reason)
    for trail, raw_value, claim in collect_allowed_prefix_affirmative_overclaims(policy):
        append_blocker(
            blockers,
            "mission_allowed_prefix_affirmative_overclaim",
            field=trail,
            claim=claim,
            value=raw_value,
        )


def validate_policy(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if policy.get("schema") != POLICY_SCHEMA:
        append_blocker(blockers, "schema_mismatch", value=policy.get("schema"))
    if policy.get("input_target_set") != INPUT_TARGET_SET:
        append_blocker(blockers, "input_target_set_mismatch", value=policy.get("input_target_set"))
    if policy.get("output_target_set") != OUTPUT_TARGET_SET:
        append_blocker(blockers, "output_target_set_mismatch", value=policy.get("output_target_set"))
    if policy.get("policy_status") != "evidence-only":
        append_blocker(blockers, "policy_status_not_evidence_only", value=policy.get("policy_status"))
    if policy.get("snapshot_root") != "redacted":
        append_blocker(blockers, "snapshot_root_not_redacted", value=policy.get("snapshot_root"))
    if policy.get("missing_targets") != []:
        append_blocker(blockers, "missing_targets_present", value=policy.get("missing_targets"))

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
    copied_targets = require_set(
        blockers,
        reason="copied_target_coverage_mismatch",
        actual=coverage.get("copied_targets"),
        expected=EXPECTED_COPIED_TARGETS,
    )
    copied_fields = require_set(
        blockers,
        reason="copied_field_coverage_mismatch",
        actual=coverage.get("copied_fields"),
        expected=EXPECTED_COPIED_FIELDS,
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

    if "MissionType.GetPlayerUsableItems" in copied_targets:
        append_blocker(blockers, "get_player_usable_items_copied_target_not_allowed")
    if any(field.startswith("MissionType.GetPlayerUsableItems.") for field in copied_fields):
        append_blocker(blockers, "get_player_usable_items_copied_field_not_allowed")

    sources = validate_generated_from(policy, blockers)
    validate_copied_bool_entries(policy, copied_fields, sources, blockers)
    validate_redacted_source_entries(policy, sources, blockers)

    safety_summary = policy.get("safety_summary")
    if not isinstance(safety_summary, dict):
        append_blocker(blockers, "safety_summary_missing")
    else:
        required_safety = {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": False,
            "copied_bool_count": len(EXPECTED_COPIED_FIELDS),
            "redacted_field_count": len(EXPECTED_REDACTED_FIELDS),
        }
        for key, expected in required_safety.items():
            if safety_summary.get(key) != expected:
                append_blocker(
                    blockers,
                    "safety_summary_mismatch",
                    field=key,
                    expected=expected,
                    value=safety_summary.get(key),
                )

    non_claims = policy.get("non_claims")
    if not isinstance(non_claims, list):
        append_blocker(blockers, "non_claims_missing")
        non_claims_text = ""
    else:
        non_claims_text = "\n".join(str(item) for item in non_claims)
    for token in REQUIRED_NON_CLAIM_TOKENS:
        if token not in non_claims_text:
            append_blocker(blockers, "required_non_claim_missing", token=token)

    for beta_key in BETA_CAPTURE_ARTIFACT_KEYS:
        if beta_key in policy and isinstance(policy.get(beta_key), dict):
            validate_beta_capture_artifact(policy.get(beta_key), blockers, path=f"$.{beta_key}")

    validate_internal_only_boundaries(policy, blockers)

    return {
        "input_targets": sorted(input_targets),
        "copied_targets": sorted(copied_targets),
        "copied_fields": sorted(copied_fields),
        "redacted_fields": sorted(redacted_fields),
        "copied_bool_count": len(policy.get("copied_bools", [])) if isinstance(policy.get("copied_bools"), list) else 0,
        "redacted_field_count": (
            len(policy.get("redacted_mission_fields", []))
            if isinstance(policy.get("redacted_mission_fields"), list)
            else 0
        ),
        "get_player_usable_items_recognition_only": (
            "MissionType.GetPlayerUsableItems" in input_targets
            and "MissionType.GetPlayerUsableItems" not in copied_targets
            and not any(field.startswith("MissionType.GetPlayerUsableItems.") for field in copied_fields)
            and {
                "MissionType.GetPlayerUsableItems.Character",
                "MissionType.GetPlayerUsableItems.OutItemIDs",
            }.issubset(redacted_fields)
        ),
    }


def validate_regenerated_fixture_policy(blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        policy = redacted_ufunction_signatures.build_mission_copied_bool_policy_slice(
            snapshot_root=FIXTURE_SNAPSHOT_ROOT,
        )
    except SystemExit as exc:
        append_blocker(blockers, "fixture_policy_regeneration_failed", detail=str(exc))
        return {"status": "blocked", "blocker": str(exc)}

    fixture_blockers: list[dict[str, Any]] = []
    summary = validate_policy(policy, fixture_blockers)
    if fixture_blockers:
        blockers.extend(
            {
                "reason": "fixture_policy_regeneration_boundary_drift",
                "source_reason": blocker.get("reason"),
                "detail": blocker,
            }
            for blocker in fixture_blockers
        )
    policy_sha256 = hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "status": "accepted" if not fixture_blockers else "blocked",
        "schema": policy.get("schema"),
        "policy_sha256": policy_sha256,
        "snapshot_root": "tests/fixtures/ufunction_snapshots",
        "summary": summary,
        **false_readiness_flags(),
    }


def build_attestation(
    *,
    ready: bool,
    policy: dict[str, Any] | None,
    expected_manifest_sha256: str,
    summary: dict[str, Any],
    consume_gate: dict[str, Any],
    promote_gate: dict[str, Any],
    fixture_regeneration: dict[str, Any],
    repo_frontier: dict[str, Any],
) -> dict[str, Any]:
    promote_reasons = set(promote_gate.get("blocker_reasons") or [])
    consume_proven = consume_gate.get("status") == "accepted" and consume_gate.get("returncode") == 0
    promote_block_proven = (
        promote_gate.get("status") == "blocked"
        and promote_gate.get("returncode") not in (None, 0)
        and {
            "promote_mode_mission_copied_bool_policy_slice_evidence_only",
            "promote_mode_manifest_has_non_claims",
        }.issubset(promote_reasons)
    )
    fixture_proven = fixture_regeneration.get("status") == "accepted"
    repo_frontier_proven = repo_frontier.get("status") == "accepted"
    actual_manifest_sha256 = policy.get("_obelisk_manifest_sha256") if isinstance(policy, dict) else None
    reviewed_hash_pinned = (
        expected_manifest_sha256 == EXPECTED_MANIFEST_SHA256
        and actual_manifest_sha256 == EXPECTED_MANIFEST_SHA256
    )
    frontier_proven = (
        summary.get("copied_targets") == sorted(EXPECTED_COPIED_TARGETS)
        and summary.get("copied_fields") == sorted(EXPECTED_COPIED_FIELDS)
        and summary.get("redacted_fields") == sorted(EXPECTED_REDACTED_FIELDS)
        and summary.get("copied_bool_count") == len(EXPECTED_COPIED_FIELDS)
        and summary.get("redacted_field_count") == len(EXPECTED_REDACTED_FIELDS)
        and summary.get("get_player_usable_items_recognition_only") is True
    )
    attestation_ready = (
        ready
        and reviewed_hash_pinned
        and consume_proven
        and promote_block_proven
        and fixture_proven
        and repo_frontier_proven
        and frontier_proven
    )
    return {
        "schema": ATTESTATION_SCHEMA,
        "status": "attested" if attestation_ready else "not_attested",
        "attestation_ready": attestation_ready,
        "consume_only": True,
        "internal_reusable_evidence_only": True,
        "current_sdk_blocker": CURRENT_SDK_BLOCKER,
        "next_blocker": CURRENT_SDK_BLOCKER,
        "remaining_blockers": [CURRENT_SDK_BLOCKER],
        "reviewed_direct_policy_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "expected_manifest_sha256": expected_manifest_sha256,
        "actual_manifest_sha256": actual_manifest_sha256,
        "reviewed_hash_pinned": reviewed_hash_pinned,
        "consume_gate_proven": consume_proven,
        "promote_block_proven": promote_block_proven,
        "fixture_policy_regeneration_proven": fixture_proven,
        "repo_public_runtime_frontier_proven": repo_frontier_proven,
        "frontier_proven": frontier_proven,
        "frontier": {
            "input_target_count": len(summary.get("input_targets", [])),
            "copied_target_count": len(summary.get("copied_targets", [])),
            "copied_bool_count": summary.get("copied_bool_count"),
            "redacted_field_count": summary.get("redacted_field_count"),
            "copied_targets": summary.get("copied_targets", []),
            "copied_fields": summary.get("copied_fields", []),
            "redacted_fields": summary.get("redacted_fields", []),
            "get_player_usable_items_recognition_only": summary.get(
                "get_player_usable_items_recognition_only", False
            ),
        },
        "fixture_policy_regeneration": fixture_regeneration,
        **false_readiness_flags(),
    }


def false_readiness_flags() -> dict[str, bool | int]:
    return {
        "mission_sdk_ready": False,
        "sdk_ready": False,
        "sdk_progress": 0,
        "sdk_progress_contribution": 0,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_observer_approved": False,
        "runtime_ready": False,
        "runtime_evidence_ready": False,
        "runtime_capture_ready": False,
        "approved_runtime_evidence_ready": False,
        "player_principal_runtime_evidence_ready": False,
        "clears_approved_runtime_evidence_missing": False,
        "approved_runtime_evidence_missing_cleared": False,
        "counts_as_approved_runtime_evidence": False,
        "replaces_player_principal_evidence": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "mutation_authority_ready": False,
        "promotion_ready": False,
        "resource_handle_ready": False,
        "return_override_ready": False,
        "return_value_override_ready": False,
        "candidate_capture_evidence_ready": False,
        "debug_capture_evidence_ready": False,
        "candidate_capture_progress_contribution": 0,
        "complete_sdk_ready": False,
        "stable_claim_allowed": False,
        "counts_toward_complete_sdk_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "complete_sdk_progress_contribution": 0,
        "p0_ready": False,
        "p0_dependency_chain_accounted": False,
        "p0_dependency_chain_ready": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "v1_completion": False,
        "v1_completion_ready": False,
        "v1_completion_contribution": 0,
    }


def build_fixture_boundary_report() -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    fixture_regeneration = validate_regenerated_fixture_policy(blockers)
    ready = not blockers and fixture_regeneration.get("status") == "accepted"
    summary = fixture_regeneration.get("summary") if isinstance(fixture_regeneration.get("summary"), dict) else {}
    report = {
        "schema": REPORT_SCHEMA,
        "mode": "fixture_boundary_only",
        "status": "fixture_boundary_ready" if ready else "blocked",
        "ready": ready,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "fixture_boundary_only": True,
        "fixture_boundary_ready": ready,
        "accepted_for_internal_planning": ready,
        "consume_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "current_sdk_blocker": CURRENT_SDK_BLOCKER,
        "next_blocker": CURRENT_SDK_BLOCKER,
        "remaining_blockers": [CURRENT_SDK_BLOCKER],
        **false_readiness_flags(),
        "beta_capture_prep": build_beta_capture_prep(),
        "root_inspected": False,
        "manifest_inspected": False,
        "artifact_gates_run": False,
        "consume_gate": {"returncode": None, "status": "not_run_fixture_boundary_only"},
        "promote_gate": {"returncode": None, "status": "not_run_fixture_boundary_only", "blocker_reasons": []},
        "fixture_policy_regeneration": fixture_regeneration,
        "repo_public_runtime_frontier": {"status": "not_run_fixture_boundary_only"},
        "attestation": {
            "schema": ATTESTATION_SCHEMA,
            "status": "not_attested",
            "attestation_ready": False,
            "consume_only": True,
            "internal_reusable_evidence_only": True,
            "current_sdk_blocker": CURRENT_SDK_BLOCKER,
            "next_blocker": CURRENT_SDK_BLOCKER,
            "remaining_blockers": [CURRENT_SDK_BLOCKER],
            "reviewed_hash_pinned": False,
            "consume_gate_proven": False,
            "promote_block_proven": False,
            "fixture_policy_regeneration_proven": ready,
            "repo_public_runtime_frontier_proven": False,
            "frontier_proven": False,
            **false_readiness_flags(),
        },
        "summary": summary,
        "blockers": blockers,
        "non_claims": [
            "fixture-boundary mode validates only repo-local regenerated Mission copied-bool fixture policy",
            "fixture-boundary mode does not inspect copied artifact roots or manifests",
            "fixture-boundary mode does not run consume/promote gates or produce offline attestation",
            "candidate/debug captures before checker acceptance are non-evidence and non-progress",
            "beta capture prep is future target planning only and is not approved runtime evidence",
            "mission beta capture prep does not clear approved_runtime_evidence_missing or replace player-principal lifecycle evidence",
            "Mission copied-bool recognizer remains SHA-gated; player/controller/character refs and OutItemIDs arrays are recognition-only",
            "fixture-boundary mode does not promote Mission SDK, runtime readiness, public ABI, public SDK readiness, or v1 completion",
        ],
    }
    report_readiness_blockers: list[dict[str, Any]] = []
    validate_report_readiness_frontier(report, report_readiness_blockers)
    if report_readiness_blockers:
        blockers.extend(report_readiness_blockers)
        report["status"] = "blocked"
        report["ready"] = False
        report["fixture_boundary_ready"] = False
        report["accepted_for_internal_planning"] = False
        report["attestation"]["fixture_policy_regeneration_proven"] = False
        report["blockers"] = blockers
    return report


def build_report(
    root_arg: Path,
    manifest_arg: Path | None,
    expected_manifest_sha256: str,
    skip_artifact_gates: bool = False,
    fixture_boundary_only: bool = False,
) -> dict[str, Any]:
    if fixture_boundary_only:
        return build_fixture_boundary_report()

    blockers: list[dict[str, Any]] = []
    root = safe_path(root_arg, "--root", blockers)
    manifest_path = manifest_arg if manifest_arg is not None else root_arg / DEFAULT_MANIFEST_NAME
    manifest = safe_path(manifest_path, "--manifest", blockers)

    summary: dict[str, Any] = {}
    policy: dict[str, Any] | None = None
    consume_gate: dict[str, Any] = {"returncode": None, "status": None}
    promote_gate: dict[str, Any] = {"returncode": None, "status": None}
    if root is not None and manifest is not None:
        policy = read_policy(manifest, blockers, expected_manifest_sha256)
        if policy is not None:
            summary = validate_policy(policy, blockers)
        if skip_artifact_gates:
            consume_gate = {"returncode": None, "status": "skipped"}
            promote_gate = {"returncode": None, "status": "skipped", "blocker_reasons": []}
        else:
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
                "promote_mode_mission_copied_bool_policy_slice_evidence_only",
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

    fixture_regeneration = validate_regenerated_fixture_policy(blockers)
    repo_frontier = validate_offline_repo_frontier(REPO_ROOT, blockers)
    ready = not blockers
    attestation = build_attestation(
        ready=ready,
        policy=policy,
        expected_manifest_sha256=expected_manifest_sha256,
        summary=summary,
        consume_gate=consume_gate,
        promote_gate=promote_gate,
        fixture_regeneration=fixture_regeneration,
        repo_frontier=repo_frontier,
    )
    report = {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "accepted_for_internal_planning": ready,
        "consume_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "current_sdk_blocker": CURRENT_SDK_BLOCKER,
        "next_blocker": CURRENT_SDK_BLOCKER,
        "remaining_blockers": [CURRENT_SDK_BLOCKER],
        **false_readiness_flags(),
        "beta_capture_prep": build_beta_capture_prep(),
        "root": str(root if root is not None else root_arg),
        "manifest": str(manifest if manifest is not None else manifest_path),
        "expected_manifest_sha256": expected_manifest_sha256,
        "consume_gate": consume_gate,
        "promote_gate": promote_gate,
        "fixture_policy_regeneration": fixture_regeneration,
        "repo_public_runtime_frontier": repo_frontier,
        "attestation": attestation,
        "summary": summary,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is exactly consume-only internal reusable evidence",
            "candidate readiness is internal planning evidence only",
            "candidate/debug captures before checker acceptance are non-evidence and non-progress",
            "beta capture prep is future target planning only and is not approved runtime evidence",
            "mission beta capture prep does not clear approved_runtime_evidence_missing or replace player-principal lifecycle evidence",
            "Mission copied-bool recognizer remains SHA-gated; player/controller/character refs and OutItemIDs arrays are recognition-only",
            "does not promote Mission SDK, runtime Mission callbacks, mission identity, player identity, lookup, arrays, mutation, return override, or ResourceHandle",
            "does not replace owner-token API, plugin cleanup, SDK consumer, public ABI, lifecycle, privacy, or live-ops promotion gates",
        ],
    }
    report_readiness_blockers: list[dict[str, Any]] = []
    validate_report_readiness_frontier(report, report_readiness_blockers)
    if report_readiness_blockers:
        blockers.extend(report_readiness_blockers)
        report["status"] = "blocked"
        report["ready"] = False
        report["accepted_for_internal_planning"] = False
        if isinstance(report.get("attestation"), dict):
            report["attestation"]["status"] = "not_attested"
            report["attestation"]["attestation_ready"] = False
        report["blockers"] = blockers
    return report


def main() -> int:
    args = parse_args()
    report = build_report(
        args.root,
        args.manifest,
        args.expected_manifest_sha256,
        args.skip_artifact_gates,
        args.fixture_boundary_only,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
