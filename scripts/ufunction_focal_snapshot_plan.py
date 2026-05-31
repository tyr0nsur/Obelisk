#!/usr/bin/env python3
"""Candidate-only focal UFunction snapshot planning helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from snapshot_evidence_pack import safe_component


SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
PLAN_SCHEMA = "obelisk.ufunction-focal-snapshot-plan.v1"
PYTHON_COMMAND = "python3"
INSPECTOR_SCRIPT = "scripts/inspect_core_ufunctions.py"


def repo_commit(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def parse_exact_target(target: str) -> tuple[str, str, str]:
    schema_part, separator, short_target = target.partition(":")
    if separator:
        if schema_part != SNAPSHOT_SCHEMA:
            raise SystemExit(f"--plan-target only supports {SNAPSHOT_SCHEMA}: {target}")
    else:
        short_target = target
    outer, dot, name = short_target.rpartition(".")
    if not dot or not outer or not name:
        raise SystemExit(f"--plan-target must be an exact Outer.Name target: {target}")
    return SNAPSHOT_SCHEMA, outer, name


def plan_output_filename(outer: str, name: str) -> str:
    return safe_component(f"{outer.replace('/', '_')}.{name}.snapshot.json", "plan-target-output")


def focal_snapshot_plan(
    functions: list[dict[str, object]],
    *,
    requested_targets: list[str],
    core: Path,
    gobjects: int,
    fname_root_slot: int,
    binary_sha: str,
    core_sha: str,
    capture_id: str,
    evidence_pack_id: str,
    max_object_scan: int,
    fname_root_ready: bool,
    fname_root_blockers: list[str],
    artifact_identity_source: str,
    repo_root: Path,
) -> dict[str, object]:
    inventory_by_key: dict[str, list[dict[str, object]]] = {}
    for item in functions:
        outer = item.get("outer_name")
        name = item.get("name")
        if isinstance(outer, str) and isinstance(name, str) and outer and name:
            inventory_by_key.setdefault(f"{outer}.{name}", []).append(item)

    obelisk_commit = repo_commit(repo_root)
    command_cwd = str(repo_root)
    command_env = {"PYTHONDONTWRITEBYTECODE": "1"}
    records: list[dict[str, object]] = []
    commands: list[dict[str, object]] = []
    blockers: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw_target in requested_targets:
        schema, outer, name = parse_exact_target(raw_target)
        target = f"{outer}.{name}"
        if target in seen:
            raise SystemExit(f"duplicate --plan-target: {target}")
        seen.add(target)
        matches = inventory_by_key.get(target, [])
        if not fname_root_ready:
            status = "blocked"
            blocker = "fname_root_not_ready"
        elif not matches:
            status = "blocked"
            blocker = "missing_inventory_target"
        elif len(matches) > 1:
            status = "blocked"
            blocker = "ambiguous_inventory_target"
        else:
            status = "planned"
            blocker = None

        record: dict[str, object] = {
            "target": f"{schema}:{target}",
            "short_target": target,
            "inventory_status": "present" if len(matches) == 1 else "missing" if not matches else "ambiguous",
            "inventory_match_count": len(matches),
            "status": status,
            "promotion_status": "not_promoted_candidate_only",
            "snapshot_output_hint": f"<non-protected-review-output>/{plan_output_filename(outer, name)}",
            "snapshot_command_cwd": command_cwd,
            "snapshot_command_env": command_env,
            "redaction_review": [
                "review placement structs, location vectors, rotation values, player/controller context, object refs, arrays, and raw params before any copied payload",
                "keep non-scalar or identity-bearing fields redacted or recognition-only unless separately promoted",
            ],
            "non_claims": [
                "does not add a target set or fixture",
                "does not promote StructureEvents, build-policy SDK, runtime hooks, mutation, or return override",
            ],
        }
        if blocker is not None:
            record["blocker"] = blocker
            blocker_record: dict[str, object] = {"target": f"{schema}:{target}", "reason": blocker}
            if blocker == "fname_root_not_ready":
                blocker_record["fname_root_blockers"] = fname_root_blockers
            blockers.append(blocker_record)
        else:
            command = [
                PYTHON_COMMAND,
                INSPECTOR_SCRIPT,
                "--core",
                str(core),
                "--gobjects",
                hex(gobjects),
                "--fname-root-slot",
                hex(fname_root_slot),
                "--outer-exact",
                outer,
                "--name-exact",
                name,
                "--max-object-scan",
                str(max_object_scan),
                "--inspection-mode",
                "ufunction",
                "--snapshot-json",
                "--evidence-ark-sha256",
                binary_sha,
                "--evidence-artifact-sha256",
                core_sha,
                "--evidence-artifact-kind",
                "offline_core",
                "--evidence-capture-id",
                capture_id,
                "--evidence-pack-id",
                evidence_pack_id,
                "--evidence-obelisk-commit",
                obelisk_commit,
            ]
            record["snapshot_command"] = command
            commands.append(
                {
                    "target": f"{schema}:{target}",
                    "cwd": command_cwd,
                    "env": command_env,
                    "argv": command,
                }
            )
        records.append(record)

    return {
        "schema": PLAN_SCHEMA,
        "requested_count": len(requested_targets),
        "planned_command_count": len(commands),
        "blocked_count": len(blockers),
        "core": str(core),
        "gobjects": hex(gobjects),
        "fname_root_slot": hex(fname_root_slot),
        "inventory_source": "unfiltered_redacted_functions",
        "fname_root_readiness": {"ready": fname_root_ready, "blockers": fname_root_blockers},
        "artifact_identity": {
            "artifact_kind": "offline_core",
            "artifact_sha256": core_sha,
            "capture_id": capture_id,
            "evidence_pack_id": evidence_pack_id,
            "source": artifact_identity_source,
        },
        "binary": {"sha256": binary_sha},
        "targets": records,
        "snapshot_commands": commands,
        "blockers": blockers,
        "promotion_status": "not_promoted_candidate_only",
    }
