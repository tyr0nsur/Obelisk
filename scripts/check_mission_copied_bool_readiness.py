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
FORBIDDEN_COPIED_RE = re.compile(
    r"(?:PlayerCharacter|PlayerPawn|Controller|OutItemIDs|GetPlayerUsableItems|identity|"
    r"lookup|mutation|object_refs|public_sdk|resource_handle|return_override|runtime|ue_pointer)",
    re.IGNORECASE,
)
FORBIDDEN_TRUE_READY_KEYS = {
    "dispatcher_ready",
    "mission_payload_decoding_ready",
    "mission_sdk_ready",
    "mutation_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_mission_sdk_ready",
    "public_sdk_ready",
    "return_override_ready",
    "runtime_hook_ready",
    "runtime_hooks_ready",
    "runtime_ready",
    "v1_complete",
    "v1_completion",
    "v1_ready",
} | offline_gate.MISSION_COPIED_BOOL_FORBIDDEN_TRUE_READY_KEYS
ALLOWED_OVERCLAIM_TEXT_PREFIXES = ("$.non_claims", "$.safety_summary.explicitly_excluded")
MISSION_CANDIDATE_FORBIDDEN_CLAIM_PHRASES = {
    "abi ready": "public_abi",
    "allows mutation": "mutation",
    "allows return override": "return_override",
    "authority promoted": "authority",
    "authority ready": "authority",
    "authoritative identity": "authority_identity",
    "c abi ready": "public_abi",
    "hook wiring ready": "runtime_hooks",
    "identity promoted": "identity",
    "identity ready": "identity",
    "mission authority": "authority",
    "mission identity": "identity",
    "mission sdk": "mission_sdk",
    "mutation enabled": "mutation",
    "mutation path": "mutation",
    "mutation ready": "mutation",
    "mutation supported": "mutation",
    "object identity": "identity",
    "player authority": "authority",
    "player identity": "identity",
    "public abi": "public_abi",
    "return override enabled": "return_override",
    "return override ready": "return_override",
    "return override supported": "return_override",
    "return overrides": "return_override",
    "runtime hook ready": "runtime_hooks",
    "runtime hooks enabled": "runtime_hooks",
    "runtime hooks ready": "runtime_hooks",
    "v1 complete": "v1_completion",
    "v1 completion": "v1_completion",
    "v1 done": "v1_completion",
    "v1 ready": "v1_completion",
    "version 1 complete": "v1_completion",
}
PUBLIC_MISSION_C_API_RE = re.compile(
    r"\b(?:OBELISK_[A-Z0-9_]*MISSION[A-Z0-9_]*|"
    r"Obelisk[A-Za-z0-9_]*Mission[A-Za-z0-9_]*|"
    r"Mission[A-Za-z0-9_]*(?:Event|Descriptor|Callback|Resource|Policy)[A-Za-z0-9_]*)\b"
)
PUBLIC_MISSION_DOC_RE = re.compile(
    r"\bmission\b|\bMission[A-Za-z0-9_]*\b|\bOBELISK_[A-Z0-9_]*MISSION[A-Z0-9_]*\b"
)
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


def collect_json_mission_doc_matches(value: Any, path: str = "$") -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
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
    return {
        "status": "accepted" if len(blockers) == frontier_blockers_before else "blocked",
        "mission_internal_test_only": len(blockers) == frontier_blockers_before,
        "cmake": cmake,
        "api_header": api_header,
        "public_gameplay_events": public_gameplay_events,
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
    for trail, value in offline_gate.collect_bool_fields(policy):
        key = trail.rsplit(".", 1)[-1]
        if key == "not_artifact_gate" and value is False:
            append_blocker(blockers, "not_artifact_gate_contradiction", field=trail)
        if key == "consume_only" and value is False:
            append_blocker(blockers, "consume_only_not_true", field=trail)
        if value is True and key in FORBIDDEN_TRUE_READY_KEYS:
            append_blocker(blockers, "runtime_public_readiness_overclaim", field=trail)
    for trail, _, reason in offline_gate.collect_candidate_public_overclaims(
        policy,
        allowed_prefixes=ALLOWED_OVERCLAIM_TEXT_PREFIXES,
    ):
        append_blocker(blockers, "runtime_public_claim_overclaim", field=trail, claim=reason)
    for trail, raw_value in offline_gate.collect_string_fields(policy):
        if any(trail.startswith(prefix) for prefix in ALLOWED_OVERCLAIM_TEXT_PREFIXES):
            continue
        text = raw_value.casefold()
        for needle, reason in MISSION_CANDIDATE_FORBIDDEN_CLAIM_PHRASES.items():
            if needle in text:
                append_blocker(blockers, "mission_candidate_claim_overclaim", field=trail, claim=reason)


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
        "public_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        "v1_completion": False,
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
    }


def build_report(
    root_arg: Path, manifest_arg: Path | None, expected_manifest_sha256: str, skip_artifact_gates: bool = False
) -> dict[str, Any]:
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
        "accepted_for_internal_planning": ready,
        "consume_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
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
    report = build_report(args.root, args.manifest, args.expected_manifest_sha256, args.skip_artifact_gates)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
