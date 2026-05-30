#!/usr/bin/env python3
"""Validate required provenance sidecars for the UObject flag-policy route."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import validate_offline_artifact_gate as gate  # noqa: E402
from build_uobject_flag_policy_report import REQUIRED_WINDOWS as POLICY_WINDOWS  # noqa: E402
from build_uobject_flag_policy_report import WINDOW_CHECKS, parse_window  # noqa: E402
from convert_weak_helper_caller_modes import PROVENANCE_SCHEMAS as WEAK_HELPER_PROVENANCE_SCHEMAS  # noqa: E402


SCHEMA = "obelisk.uobject-flag-policy-provenance-inputs.v1"
POLICY_WINDOW_PROVENANCE_SCHEMAS = {
    "obelisk.offline-artifact-provenance.v1",
    "obelisk.static-artifact-provenance.v1",
}
RICH_PROVENANCE_FIELDS = (
    "command",
    "tool",
    "tool_version",
    "start_address",
    "stop_address",
    "source_path",
)
HEX_ADDRESS_RE = re.compile(r"^(?:0x)?[0-9a-f]+$", re.IGNORECASE)
WEAK_HELPER_INPUT_FLAGS = (
    ("ghidra_stdout", "--ghidra-stdout"),
    ("r2_windows", "--r2-windows"),
    ("direct_call_counts", "--direct-call-counts"),
)


def sidecar_path_for(path: Path) -> Path:
    return path.with_name(path.name + ".provenance.json")


def validate_provenance_path_fields(
    payload: dict[str, Any],
    *,
    sidecar_path: Path,
    label: str,
    workspace_root: Path,
    protected_root: Path,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for trail, raw_path in gate.collect_path_fields(payload):
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = sidecar_path.parent / candidate
        blockers.extend(
            gate.path_blockers(
                candidate,
                label=f"{label}:provenance:{trail}",
                workspace_root=workspace_root,
                protected_root=protected_root,
                require_workspace=False,
            )
        )
    return blockers


def parse_address_field(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and HEX_ADDRESS_RE.fullmatch(value.strip()):
        return int(value, 16)
    return None


def command_tokens(command: object) -> list[str] | None:
    if isinstance(command, list) and command and all(isinstance(part, str) and part for part in command):
        return command
    return None


def command_path_candidates(token: str) -> list[str]:
    candidates = [token]
    if "=" in token:
        candidates.append(token.split("=", 1)[1])
    if token.startswith("@") and len(token) > 1:
        candidates.append(token[1:])
    return candidates


def validate_command_path_tokens(
    command: list[str],
    *,
    label: str,
    sidecar_path: Path,
    workspace_root: Path,
    protected_root: Path,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for index, token in enumerate(command):
        checked: set[str] = set()
        for raw_candidate in command_path_candidates(token):
            if raw_candidate in checked:
                continue
            checked.add(raw_candidate)
            if "/" not in raw_candidate and not raw_candidate.startswith("~"):
                continue
            candidate = Path(raw_candidate)
            if not candidate.is_absolute():
                candidate = sidecar_path.parent / candidate
            blockers.extend(
                gate.path_blockers(
                    candidate,
                    label=f"{label}:provenance.command[{index}]",
                    workspace_root=workspace_root,
                    protected_root=protected_root,
                    require_workspace=False,
                )
            )
    return blockers


def validate_rich_provenance_fields(
    payload: dict[str, Any],
    *,
    sidecar_path: Path,
    label: str,
    workspace_root: Path,
    protected_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"required_fields": list(RICH_PROVENANCE_FIELDS)}

    for field in RICH_PROVENANCE_FIELDS:
        if field not in payload:
            blockers.append({"reason": "provenance_rich_field_missing", "label": f"{label}:provenance.{field}"})

    command = command_tokens(payload.get("command"))
    if command is None:
        blockers.append({"reason": "provenance_command_invalid", "label": f"{label}:provenance.command"})
    else:
        summary["command"] = command
        blockers.extend(
            validate_command_path_tokens(
                command,
                label=label,
                sidecar_path=sidecar_path,
                workspace_root=workspace_root,
                protected_root=protected_root,
            )
        )

    tool = payload.get("tool")
    if not isinstance(tool, str) or not tool:
        blockers.append({"reason": "provenance_tool_invalid", "label": f"{label}:provenance.tool"})
    else:
        summary["tool"] = tool
        if command is not None and Path(command[0]).name != tool:
            blockers.append(
                {
                    "reason": "provenance_tool_command_mismatch",
                    "label": f"{label}:provenance.tool",
                    "recorded_tool": tool,
                    "command_tool": Path(command[0]).name,
                }
            )

    tool_version = payload.get("tool_version")
    if not isinstance(tool_version, str) or not tool_version:
        blockers.append({"reason": "provenance_tool_version_invalid", "label": f"{label}:provenance.tool_version"})
    else:
        summary["tool_version"] = tool_version

    source_path = payload.get("source_path")
    if not isinstance(source_path, str) or not source_path:
        blockers.append({"reason": "provenance_source_path_invalid", "label": f"{label}:provenance.source_path"})
    else:
        source_candidate = Path(source_path)
        if not source_candidate.is_absolute():
            source_candidate = sidecar_path.parent / source_candidate
        source_state = gate.path_state(source_candidate, workspace_root=workspace_root, protected_root=protected_root)
        summary["source_path"] = source_path
        summary["source_resolved_path"] = source_state["resolved"]

    start_address = parse_address_field(payload.get("start_address"))
    stop_address = parse_address_field(payload.get("stop_address"))
    if start_address is None:
        blockers.append({"reason": "provenance_start_address_invalid", "label": f"{label}:provenance.start_address"})
    if stop_address is None:
        blockers.append({"reason": "provenance_stop_address_invalid", "label": f"{label}:provenance.stop_address"})
    if start_address is not None and stop_address is not None:
        summary["start_address"] = hex(start_address)
        summary["stop_address"] = hex(stop_address)
        if stop_address <= start_address:
            blockers.append(
                {
                    "reason": "provenance_address_range_invalid",
                    "label": f"{label}:provenance.start_address-stop_address",
                    "start_address": hex(start_address),
                    "stop_address": hex(stop_address),
                }
            )

    summary["verified"] = not blockers
    return summary, blockers


def validate_artifact_sidecar(
    *,
    label: str,
    path: Path,
    expected_binary_sha256: str,
    allowed_schemas: set[str],
    workspace_root: Path,
    protected_root: Path,
    require_under_root: bool,
    require_rich_provenance: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blockers = gate.path_blockers(
        path,
        label=label,
        workspace_root=workspace_root,
        protected_root=protected_root,
        require_workspace=require_under_root,
    )
    state = gate.path_state(path, workspace_root=workspace_root, protected_root=protected_root)
    resolved = Path(state["resolved"])
    sidecar_path = sidecar_path_for(resolved)
    record: dict[str, Any] = {
        "label": label,
        "path": str(path),
        "resolved_path": str(resolved),
        "sidecar_path": str(sidecar_path),
        "artifact_sha256": None,
        "sidecar_verified": False,
    }
    if blockers:
        return record, blockers
    if not resolved.is_file():
        return record, [{"reason": "artifact_not_file", "label": label, "path": str(path)}]

    artifact_sha256 = gate.sha256_file(resolved)
    record["artifact_sha256"] = artifact_sha256
    sidecar_blockers = gate.path_blockers(
        sidecar_path,
        label=f"{label}:provenance",
        workspace_root=workspace_root,
        protected_root=protected_root,
        require_workspace=require_under_root,
    )
    if sidecar_blockers:
        return record, sidecar_blockers
    if not sidecar_path.is_file():
        return record, [{"reason": "missing_provenance_sidecar", "label": label, "path": str(sidecar_path)}]

    payload, load_blockers = gate.load_json(sidecar_path)
    if payload is None:
        return record, load_blockers

    blockers.extend(
        validate_provenance_path_fields(
            payload,
            sidecar_path=sidecar_path,
            label=label,
            workspace_root=workspace_root,
            protected_root=protected_root,
        )
    )
    schema = payload.get("schema")
    if schema not in allowed_schemas:
        blockers.append({"reason": "provenance_schema_mismatch", "label": f"{label}:provenance.schema", "recorded_schema": schema})
    if payload.get("verified") is not True:
        blockers.append({"reason": "provenance_not_verified", "label": f"{label}:provenance.verified"})
    if payload.get("binary_sha256") != expected_binary_sha256:
        blockers.append(
            {
                "reason": "provenance_binary_sha256_mismatch",
                "label": f"{label}:provenance.binary_sha256",
                "expected_binary_sha256": expected_binary_sha256,
                "recorded_binary_sha256": payload.get("binary_sha256"),
            }
        )
    if payload.get("artifact_sha256") != artifact_sha256:
        blockers.append(
            {
                "reason": "provenance_artifact_sha256_mismatch",
                "label": f"{label}:provenance.artifact_sha256",
                "expected_artifact_sha256": artifact_sha256,
                "recorded_artifact_sha256": payload.get("artifact_sha256"),
            }
        )
    if require_rich_provenance:
        rich_summary, rich_blockers = validate_rich_provenance_fields(
            payload,
            sidecar_path=sidecar_path,
            label=label,
            workspace_root=workspace_root,
            protected_root=protected_root,
        )
        record["rich_provenance"] = rich_summary
        blockers.extend(rich_blockers)

    record.update(
        {
            "sidecar_verified": not blockers,
            "sidecar_schema": schema,
            "sidecar_sha256": gate.sha256_file(sidecar_path),
        }
    )
    return record, blockers


def window_paths(windows: list[tuple[str, Path]]) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    by_name: dict[str, Path] = {}
    for name, path in windows:
        if name not in WINDOW_CHECKS:
            blockers.append({"reason": "unknown_window_name", "label": f"--window {name}", "recorded": name})
            continue
        if name in by_name:
            blockers.append({"reason": "duplicate_window_name", "label": f"--window {name}", "recorded": name})
            continue
        by_name[name] = path
    for name in POLICY_WINDOWS:
        if name not in by_name:
            blockers.append({"reason": "missing_required_window_argument", "label": f"--window {name}"})
    return by_name, blockers


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    require_rich_provenance = bool(getattr(args, "require_rich_provenance", False))
    if gate.SHA256_RE.fullmatch(args.expected_binary_sha256 or "") is None:
        blockers.append({"reason": "expected_binary_sha256_invalid", "label": "--expected-binary-sha256"})

    weak_inputs = (
        ("ghidra_stdout", args.ghidra_stdout),
        ("r2_windows", args.r2_windows),
        ("direct_call_counts", args.direct_call_counts),
    )
    for name, path in weak_inputs:
        label = f"weak_helper.{name}"
        record, sidecar_blockers = validate_artifact_sidecar(
            label=label,
            path=path,
            expected_binary_sha256=args.expected_binary_sha256,
            allowed_schemas=set(WEAK_HELPER_PROVENANCE_SCHEMAS),
            workspace_root=args.root,
            protected_root=args.protected_root,
            require_under_root=args.require_under_root,
            require_rich_provenance=require_rich_provenance,
        )
        records.append(record)
        blockers.extend(sidecar_blockers)

    by_name, window_blockers = window_paths(args.window or [])
    blockers.extend(window_blockers)
    for name in POLICY_WINDOWS:
        path = by_name.get(name)
        if path is None:
            continue
        record, sidecar_blockers = validate_artifact_sidecar(
            label=f"uobject_policy_window.{name}",
            path=path,
            expected_binary_sha256=args.expected_binary_sha256,
            allowed_schemas=POLICY_WINDOW_PROVENANCE_SCHEMAS,
            workspace_root=args.root,
            protected_root=args.protected_root,
            require_under_root=args.require_under_root,
            require_rich_provenance=require_rich_provenance,
        )
        records.append(record)
        blockers.extend(sidecar_blockers)

    return {
        "schema": SCHEMA,
        "status": "accepted" if not blockers else "blocked",
        "route": "weak-helper caller-mode -> uobject flag-policy",
        "expected_binary_sha256": args.expected_binary_sha256,
        "required_inputs": [name for name, _ in WEAK_HELPER_INPUT_FLAGS] + list(POLICY_WINDOWS),
        "rich_provenance_required": require_rich_provenance,
        "records": records,
        "blockers": blockers,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=gate.DEFAULT_WORKSPACE_ROOT, help="Approved offline workspace root.")
    parser.add_argument("--protected-root", type=Path, default=gate.SERVER_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--require-under-root", action="store_true", help="Require every input and sidecar to live under --root.")
    parser.add_argument(
        "--require-rich-provenance",
        action="store_true",
        help="Require command/tool/version/source/range metadata in every provenance sidecar.",
    )
    parser.add_argument("--expected-binary-sha256", required=True)
    parser.add_argument("--ghidra-stdout", type=Path, required=True)
    parser.add_argument("--r2-windows", type=Path, required=True)
    parser.add_argument("--direct-call-counts", type=Path, required=True)
    parser.add_argument("--window", action="append", type=parse_window, default=[], metavar="NAME=PATH")
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']} route={result['route']} blockers={len(result['blockers'])}")
        for record in result["records"]:
            print(f"- {record['label']}: {record['sidecar_path']}")
        for blocker in result["blockers"]:
            print(f"  blocker {blocker['reason']}: {blocker.get('label') or blocker.get('path') or ''}")
    return 0 if result["status"] == "accepted" else 2


if __name__ == "__main__":
    raise SystemExit(main())
