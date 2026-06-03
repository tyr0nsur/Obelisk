#!/usr/bin/env python3
"""Run the route gate with transient bound player-identity planning inputs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import bind_player_identity_planning_sources as binder
import build_redacted_ufunction_signatures
import check_command_permission_route_gate as route_gate
from protected_paths import reject_protected_input_path, reject_protected_output_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_SCHEMA = "obelisk.command-permission-route-gate-bound-identity-sources-check.v1"
ROUTE_GATE_SCHEMA = "obelisk.command-permission-route-gate-check.v1"
NON_CLAIMS = [
    "transient bound route gate check only",
    "no runtime or server operation was performed",
    "no ARK process was started, stopped, restarted, attached, or observed",
    "no public player identity is promoted",
    "no permissions/admin, command response, or commands/replies surface is promoted",
    "no public SDK, public ABI, release, or v1 completion readiness is claimed",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=build_redacted_ufunction_signatures.DEFAULT_SNAPSHOT_ROOT,
        help="Sanitized snapshot root used to build transient player-identity first evidence.",
    )
    parser.add_argument(
        "--lifecycle-anchor-candidates-manifest",
        "--lifecycle-anchor-candidates",
        dest="lifecycle_anchor_candidates",
        type=Path,
        required=True,
        help="Consume-only lifecycle-anchor candidates manifest to bind transiently.",
    )
    parser.add_argument(
        "--principal-invalidation-policy-manifest",
        "--principal-invalidation-policy",
        dest="principal_invalidation_policy",
        type=Path,
        required=True,
        help="Consume-only principal invalidation policy manifest to bind transiently.",
    )
    parser.add_argument(
        "--approved-runtime-principal-lifecycle-evidence-manifest",
        type=Path,
        help=(
            "Optional approved runtime-principal lifecycle evidence manifest forwarded "
            "to the route gate. It may clear only approved_runtime_evidence_missing and "
            "must leave the route locked at identity_public_contract_gate_missing."
        ),
    )
    parser.add_argument(
        "--candidate-root",
        type=Path,
        help="Optional distinct second-source candidate root forwarded to the route gate identity checker.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Optional artifact root forwarded to the route gate identity checker.",
    )
    parser.add_argument(
        "--query-failclosed-artifact",
        type=Path,
        default=route_gate.DEFAULT_QUERY_CONTRACT,
        help="Permissions/admin query fail-closed artifact forwarded to the route gate.",
    )
    parser.add_argument(
        "--player-identity-decisions",
        type=Path,
        default=route_gate.DEFAULT_PLAYER_IDENTITY_DECISIONS,
        help="Player identity decisions manifest forwarded to the route gate.",
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=route_gate.DEFAULT_PUBLIC_SDK_SURFACES,
        help="Public SDK surfaces manifest forwarded to the route gate.",
    )
    parser.add_argument(
        "--player-identity-private-candidate-contract",
        type=Path,
        default=route_gate.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
        help="Private candidate identity contract forwarded to the route gate.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=route_gate.DEFAULT_PUBLIC_HEADER,
        help="Public C ABI header forwarded to the route gate.",
    )
    parser.add_argument(
        "--command-response-root",
        type=Path,
        help="Optional command/chat response second-source planning root forwarded to the route gate.",
    )
    parser.add_argument(
        "--command-response-readiness",
        type=Path,
        help="Optional command/chat response readiness JSON forwarded to the route gate.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def resolve_manifest_pair(args: argparse.Namespace) -> tuple[Path, Path]:
    lifecycle = args.lifecycle_anchor_candidates
    principal = args.principal_invalidation_policy
    assert lifecycle is not None and principal is not None
    if not lifecycle.is_file():
        raise SystemExit(f"lifecycle-anchor candidates manifest is missing: {lifecycle}")
    if not principal.is_file():
        raise SystemExit(f"principal invalidation policy manifest is missing: {principal}")
    return lifecycle, principal


def safe_snapshot_root(path: Path) -> Path:
    reject_symlink_component(path, "snapshot-root")
    resolved = reject_protected_input_path(path, "snapshot-root")
    if not resolved.is_dir():
        raise SystemExit(f"snapshot-root is not a directory: {resolved}")
    return resolved


def safe_optional_input_path(path: Path | None, label: str) -> Path | None:
    if path is None:
        return None
    reject_symlink_component(path, label)
    resolved = reject_protected_input_path(path, label)
    return resolved


def check_approved_runtime_evidence_manifest(path: Path, temp_root: Path) -> tuple[bool, dict[str, Any] | None, int, str, str | None]:
    argv = [
        sys.executable,
        str(SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"),
        str(path),
        "--json",
    ]
    env = os.environ.copy()
    env.update({"TMPDIR": str(temp_root), "TEMP": str(temp_root), "TMP": str(temp_root)})
    result = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    parse_error = None
    report = None
    try:
        loaded = json.loads(result.stdout)
        if isinstance(loaded, dict):
            report = loaded
        else:
            parse_error = "stdout_json_not_object"
    except json.JSONDecodeError as exc:
        parse_error = f"stdout_json_decode_error: {exc}"
    accepted = (
        result.returncode == 0
        and parse_error is None
        and isinstance(report, dict)
        and report.get("ready") is True
        and report.get("approved_runtime_evidence_present") is True
        and report.get("runtime_evidence_ready") is True
        and report.get("next_blocker") == "identity_public_contract_gate_missing"
        and report.get("promotion_ready") is False
        and report.get("public_sdk_ready") is False
        and report.get("public_abi_ready") is False
        and report.get("runtime_ready") is False
        and report.get("v1_completion_ready") is False
    )
    return accepted, report, result.returncode, result.stderr.strip(), parse_error


def write_json(path: Path, payload: dict[str, Any]) -> None:
    binder.atomic_write_json(path, payload)


def build_transient_binding(
    *,
    snapshot_root: Path,
    lifecycle_manifest: Path,
    principal_manifest: Path,
    temp_root: Path,
) -> tuple[dict[str, Any], Path, Path]:
    first_evidence = build_redacted_ufunction_signatures.build_players_identity_first_evidence(
        snapshot_root=snapshot_root
    )
    first_path = temp_root / "players-identity-first-evidence.json"
    write_json(first_path, first_evidence)

    lifecycle, lifecycle_path = binder.load_json(lifecycle_manifest, "lifecycle-anchor-candidates")
    principal, principal_path = binder.load_json(principal_manifest, "principal-invalidation-policy")
    binder.validate_inputs(first_evidence=first_evidence, lifecycle=lifecycle, principal=principal)
    lifecycle_snapshot_root_binding = binder.validate_lifecycle_anchor_snapshot_root(
        lifecycle=lifecycle,
        snapshot_root=snapshot_root,
    )

    output_dir = binder.prepare_output_dir(temp_root / "bound")
    lifecycle_output = output_dir / binder.LIFECYCLE_OUTPUT_NAME
    principal_output = output_dir / binder.PRINCIPAL_OUTPUT_NAME
    report_output = output_dir / binder.REPORT_OUTPUT_NAME

    bound_lifecycle = binder.bind_lifecycle_to_first_evidence(lifecycle, first_evidence)
    lifecycle_blockers = binder.lifecycle_anchor_candidates.validate_manifest(bound_lifecycle, promote=False)
    if lifecycle_blockers:
        raise SystemExit(
            "bound lifecycle-anchor candidates failed validation: "
            + json.dumps(binder.validation_reasons(lifecycle_blockers), sort_keys=True)
        )
    bound_principal = binder.bind_principal_to_lifecycle(principal, bound_lifecycle)
    principal_blockers = binder.principal_invalidation_policy.validate_manifest(
        bound_principal,
        check_mode="consume",
    ).blockers
    if principal_blockers:
        raise SystemExit(
            "bound principal invalidation policy failed validation: "
            + json.dumps(binder.validation_reasons(principal_blockers), sort_keys=True)
        )

    write_json(lifecycle_output, bound_lifecycle)
    write_json(principal_output, bound_principal)
    binding_report = binder.build_report(
        first_path=first_path,
        lifecycle_path=lifecycle_path,
        principal_path=principal_path,
        first_evidence=first_evidence,
        lifecycle_output=lifecycle_output,
        principal_output=principal_output,
        bound_lifecycle=bound_lifecycle,
        bound_principal=bound_principal,
    )
    write_json(report_output, binding_report)
    return binding_report, lifecycle_output, principal_output, lifecycle_snapshot_root_binding


def run_route_gate(
    args: argparse.Namespace,
    *,
    lifecycle_output: Path,
    principal_output: Path,
    temp_root: Path,
    approved_runtime: Path | None,
) -> tuple[int, dict[str, Any] | None, str, str | None]:
    query_failclosed_artifact = safe_optional_input_path(args.query_failclosed_artifact, "query-failclosed-artifact")
    player_identity_decisions = safe_optional_input_path(args.player_identity_decisions, "player-identity-decisions")
    public_sdk_surfaces = safe_optional_input_path(args.public_sdk_surfaces, "public-sdk-surfaces")
    private_candidate_contract = safe_optional_input_path(
        args.player_identity_private_candidate_contract,
        "player-identity-private-candidate-contract",
    )
    public_header = safe_optional_input_path(args.public_header, "public-header")
    command_response_root = safe_optional_input_path(args.command_response_root, "command-response-root")
    command_response_readiness = safe_optional_input_path(args.command_response_readiness, "command-response-readiness")
    argv = [
        sys.executable,
        str(SCRIPT_DIR / "check_command_permission_route_gate.py"),
        "--query-failclosed-artifact",
        str(query_failclosed_artifact),
        "--player-identity-decisions",
        str(player_identity_decisions),
        "--public-sdk-surfaces",
        str(public_sdk_surfaces),
        "--player-identity-private-candidate-contract",
        str(private_candidate_contract),
        "--public-header",
        str(public_header),
        "--player-identity-snapshot-root",
        str(args.snapshot_root),
        "--lifecycle-anchor-candidates-manifest",
        str(lifecycle_output),
        "--principal-invalidation-policy-manifest",
        str(principal_output),
        "--json",
    ]
    candidate_root = safe_optional_input_path(args.candidate_root, "candidate-root")
    artifact_root = safe_optional_input_path(args.artifact_root, "artifact-root")
    if candidate_root is not None:
        argv.extend(["--player-identity-candidate-root", str(candidate_root)])
    if artifact_root is not None:
        argv.extend(["--player-identity-artifact-root", str(artifact_root)])
    if command_response_root is not None:
        argv.extend(["--command-response-root", str(command_response_root)])
    if command_response_readiness is not None:
        argv.extend(["--command-response-readiness", str(command_response_readiness)])
    if approved_runtime is not None:
        argv.extend(["--approved-runtime-principal-lifecycle-evidence-manifest", str(approved_runtime)])
    env = os.environ.copy()
    env.update({"TMPDIR": str(temp_root), "TEMP": str(temp_root), "TMP": str(temp_root)})
    result = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    parse_error = None
    report = None
    try:
        loaded = json.loads(result.stdout)
        if isinstance(loaded, dict):
            report = loaded
        else:
            parse_error = "stdout_json_not_object"
    except json.JSONDecodeError as exc:
        parse_error = f"stdout_json_decode_error: {exc}"
    return result.returncode, report, result.stderr.strip(), parse_error


def route_manifest_path_matches(manifest: dict[str, Any], expected_path: Path) -> bool:
    expected = str(expected_path.resolve())
    return (
        manifest.get("expected_resolved_path") == expected
        and manifest.get("observed_resolved_path") == expected
    )


def approved_runtime_evidence_diagnosis_matches_path(diagnosis: dict[str, Any], expected_path: Path) -> bool:
    expected = str(expected_path.resolve())
    observed = diagnosis.get("path")
    if not isinstance(observed, str) or observed != expected:
        return False
    return str(Path(observed).resolve()) == expected


def approved_runtime_evidence_diagnosis_ready(diagnosis: dict[str, Any]) -> bool:
    return (
        diagnosis.get("ready") is True
        and diagnosis.get("approved_runtime_evidence_present") is True
        and diagnosis.get("runtime_evidence_ready") is True
        and diagnosis.get("remaining_blockers") == []
        and diagnosis.get("promotion_ready") is False
        and diagnosis.get("public_sdk_ready") is False
        and diagnosis.get("public_abi_ready") is False
        and diagnosis.get("runtime_ready") is False
        and diagnosis.get("v1_completion_ready") is False
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    snapshot_root = safe_snapshot_root(args.snapshot_root)
    args.snapshot_root = snapshot_root
    lifecycle_manifest, principal_manifest = resolve_manifest_pair(args)
    approved_runtime = safe_optional_input_path(
        getattr(args, "approved_runtime_principal_lifecycle_evidence_manifest", None),
        "approved-runtime-principal-lifecycle-evidence-manifest",
    )
    with tempfile.TemporaryDirectory(prefix="obelisk-bound-player-identity-route-") as temp_dir:
        temp_root = Path(temp_dir)
        reject_symlink_component(temp_root, "temp-root")
        reject_protected_output_path(temp_root, "temp-root")
        approved_runtime_evidence_check = None
        approved_runtime_accepted = False
        if approved_runtime is not None:
            (
                approved_runtime_accepted,
                approved_runtime_report,
                approved_runtime_returncode,
                approved_runtime_stderr,
                approved_runtime_parse_error,
            ) = check_approved_runtime_evidence_manifest(approved_runtime, temp_root)
            approved_runtime_evidence_check = {
                "accepted": approved_runtime_accepted,
                "returncode": approved_runtime_returncode,
                "stderr": approved_runtime_stderr,
                "parse_error": approved_runtime_parse_error,
                "report": approved_runtime_report,
            }
        accepted_approved_runtime = approved_runtime if approved_runtime_accepted else None
        expected_blocker = (
            "identity_public_contract_gate_missing"
            if accepted_approved_runtime is not None
            else "approved_runtime_evidence_missing"
        )
        expected_blocked_until = (
            ["reviewed_identity_public_contract"]
            if accepted_approved_runtime is not None
            else ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"]
        )
        (
            binding_report,
            lifecycle_output,
            principal_output,
            lifecycle_snapshot_root_binding,
        ) = build_transient_binding(
            snapshot_root=snapshot_root,
            lifecycle_manifest=lifecycle_manifest,
            principal_manifest=principal_manifest,
            temp_root=temp_root,
        )
        route_returncode, route_report, route_stderr, route_parse_error = run_route_gate(
            args,
            lifecycle_output=lifecycle_output,
            principal_output=principal_output,
            temp_root=temp_root,
            approved_runtime=accepted_approved_runtime,
        )

    blockers: list[str] = []
    if approved_runtime is not None and not approved_runtime_accepted:
        blockers.append("approved_runtime_evidence_not_accepted")
    if binding_report.get("ready") is not True:
        blockers.append("identity_planning_binding_not_ready")
    if route_returncode != 0:
        blockers.append("route_gate_exit_code_unexpected")
    if route_parse_error is not None:
        blockers.append("route_gate_output_invalid")
    if route_report is None:
        blockers.append("route_gate_report_missing")
    else:
        phase = route_report.get("critical_path_phase")
        route_lock = route_report.get("route_lock")
        current_blocker = phase.get("current_blocker") if isinstance(phase, dict) else None
        source_checker_primary_blocker = phase.get("source_checker_primary_blocker") if isinstance(phase, dict) else None
        source_checker_status = phase.get("source_checker_status") if isinstance(phase, dict) else None
        source_checker_ready = phase.get("source_checker_ready") if isinstance(phase, dict) else None
        source_checker_internal_planning = (
            phase.get("source_checker_accepted_for_internal_planning") if isinstance(phase, dict) else None
        )
        manifest_sources = phase.get("source_checker_manifest_sources") if isinstance(phase, dict) else None
        approved_runtime_diagnosis = (
            phase.get("source_checker_approved_runtime_evidence_manifest") if isinstance(phase, dict) else None
        )
        route_public_or_runtime_claims = route_gate.collect_public_or_runtime_claims(
            route_report,
            include_text_claims=False,
        )
        if route_report.get("schema") != ROUTE_GATE_SCHEMA:
            blockers.append("route_gate_schema_mismatch")
        if route_report.get("valid") is not True or route_report.get("accepted_for_planning") is not True:
            blockers.append("route_gate_not_accepted_for_planning")
        if route_report.get("planning_only") is not True:
            blockers.append("route_gate_not_planning_only")
        if route_report.get("blockers"):
            blockers.append("route_gate_blockers_not_empty")
        for key in ("promotion_ready", "public_sdk_ready", "public_abi_ready", "runtime_ready", "public_header_allowed"):
            if route_report.get(key) is not False:
                blockers.append(f"route_gate_{key}_overclaim")
        if route_public_or_runtime_claims:
            blockers.append("route_gate_public_or_runtime_claims_overclaim")
        if current_blocker != expected_blocker:
            blockers.append("route_gate_bound_identity_blocker_unexpected")
        if current_blocker is None:
            blockers.append("route_gate_bound_identity_current_blocker_missing")
        if source_checker_primary_blocker != expected_blocker:
            blockers.append("route_gate_bound_identity_primary_blocker_unexpected")
        if source_checker_status != "blocked":
            blockers.append("route_gate_identity_readiness_status_unexpected")
        if source_checker_ready is not False:
            blockers.append("route_gate_identity_readiness_ready_flag_overclaim")
        if source_checker_internal_planning is not False:
            blockers.append("route_gate_identity_readiness_internal_planning_overclaim")
        if accepted_approved_runtime is not None:
            if not isinstance(approved_runtime_diagnosis, dict):
                blockers.append("route_gate_approved_runtime_evidence_manifest_missing")
            else:
                if not approved_runtime_evidence_diagnosis_ready(approved_runtime_diagnosis):
                    blockers.append("route_gate_approved_runtime_evidence_not_ready")
                if not approved_runtime_evidence_diagnosis_matches_path(
                    approved_runtime_diagnosis,
                    accepted_approved_runtime,
                ):
                    blockers.append("route_gate_approved_runtime_evidence_path_alias")
        elif isinstance(approved_runtime_diagnosis, dict) and approved_runtime_evidence_diagnosis_ready(
            approved_runtime_diagnosis
        ):
            blockers.append("route_gate_approved_runtime_evidence_unexpected")
        if not isinstance(manifest_sources, dict):
            blockers.append("route_gate_bound_identity_manifest_sources_missing")
        else:
            if manifest_sources.get("mode") != "cli_bound":
                blockers.append("route_gate_bound_identity_manifest_source_mode_unexpected")
            if manifest_sources.get("expected_manifests_received") is not True:
                blockers.append("route_gate_bound_identity_expected_manifests_missing")
            manifests = manifest_sources.get("manifests")
            if not isinstance(manifests, dict):
                blockers.append("route_gate_bound_identity_manifest_details_missing")
            else:
                expected_bound_paths = {
                    "lifecycle_anchor_candidates": lifecycle_output,
                    "principal_invalidation_policy": principal_output,
                }
                for key in ("lifecycle_anchor_candidates", "principal_invalidation_policy"):
                    manifest = manifests.get(key)
                    if not isinstance(manifest, dict) or manifest.get("source") != "cli_bound":
                        blockers.append(f"route_gate_bound_identity_{key}_source_unexpected")
                    elif manifest.get("matched") is not True:
                        blockers.append(f"route_gate_bound_identity_{key}_path_mismatch")
                    elif not route_manifest_path_matches(manifest, expected_bound_paths[key]):
                        blockers.append(f"route_gate_bound_identity_{key}_canonical_path_mismatch")
        if not isinstance(route_lock, dict) or route_lock.get("locked") is not True:
            blockers.append("route_gate_lock_unexpected")
        if not isinstance(route_lock, dict) or route_lock.get("blocked_until") != expected_blocked_until:
            blockers.append("route_gate_lock_blocked_until_unexpected")

    critical_path_phase = (
        route_report.get("critical_path_phase")
        if isinstance(route_report, dict) and isinstance(route_report.get("critical_path_phase"), dict)
        else {}
    )
    route_lock = (
        route_report.get("route_lock")
        if isinstance(route_report, dict) and isinstance(route_report.get("route_lock"), dict)
        else {}
    )
    return {
        "schema": REPORT_SCHEMA,
        "valid": not blockers,
        "accepted_for_planning": not blockers,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "blockers": blockers,
        "inputs": {
            "snapshot_root": str(snapshot_root),
            "lifecycle_anchor_candidates_manifest": str(lifecycle_manifest),
            "principal_invalidation_policy_manifest": str(principal_manifest),
            "approved_runtime_principal_lifecycle_evidence_manifest": (
                str(approved_runtime) if approved_runtime is not None else None
            ),
        },
        "approved_runtime_evidence_check": approved_runtime_evidence_check,
        "critical_path_phase": critical_path_phase,
        "route_lock": route_lock,
        "binding_report": binding_report,
        "lifecycle_snapshot_root_binding": lifecycle_snapshot_root_binding,
        "route_gate": {
            "returncode": route_returncode,
            "stderr": route_stderr,
            "parse_error": route_parse_error,
            "report": route_report,
            "public_or_runtime_claims": (
                route_gate.collect_public_or_runtime_claims(route_report, include_text_claims=False)
                if isinstance(route_report, dict)
                else []
            ),
        },
        "non_claims": NON_CLAIMS,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
