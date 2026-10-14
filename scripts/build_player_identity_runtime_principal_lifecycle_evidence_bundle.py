#!/usr/bin/env python3
"""Build the offline approved player-principal lifecycle evidence bundle.

This helper starts from an already copied/sanitized Obelisk log. It does not read live
server logs, does not start servers, and does not promote public player identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import protected_paths
import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_evidence_checker
from player_principal_commit_validation import is_reviewed_obelisk_commit
from snapshot_evidence_pack import reject_protected_output_path, reject_symlink_component


window_manifest_checker = approved_evidence_checker.window_manifest_checker
SCRIPT_DIR = Path(__file__).resolve().parent
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
BUILDER = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
WINDOW_MANIFEST_CHECKER = SCRIPT_DIR / "check_player_principal_lifecycle_window_manifest.py"
WINDOW_REQUEST_CHECKER = SCRIPT_DIR / "check_player_principal_lifecycle_window_request.py"
OFFLINE_GATE = SCRIPT_DIR / "validate_offline_artifact_gate.py"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = protected_paths.approved_offline_workspace_roots()
EXPECTED_COPIED_LOG_PARENT = "live-validation-logs"
APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH = (
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
)
EXPECTED_APPROVED_BUNDLE_GENERATED_JSON_OUTPUTS = frozenset(
    (
        "runtime-observer-summary.json",
        "player-principal-lifecycle-window-manifest.check.json",
        "approved-runtime-principal-lifecycle-evidence.check.json",
        "approved-runtime-principal-lifecycle-evidence.promote-check.json",
        "approved-runtime-principal-lifecycle-evidence.public-readiness-check.json",
        "approved-runtime-principal-lifecycle-evidence.runtime-readiness-check.json",
        "approved-runtime-principal-lifecycle-evidence.consume-gate.json",
        "evidence-bundle-report.json",
    )
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_SIBLING_ARTIFACTS = (
    ("window_request_json", "window-request.json", "request_pack_path", "request_pack_sha256"),
    ("observer_window_env", "observer-window.env", "observer_env_path", "observer_env_sha256"),
    ("operator_approval_request_md", "operator-approval-request.md", None, None),
    (
        "operator_approval_receipt_json",
        "operator-approval-receipt.json",
        "operator_approval_receipt_path",
        "operator_approval_receipt_sha256",
    ),
    ("preflight_pre_json", "preflight-pre.json", "preflight_pre_path", "preflight_pre_sha256"),
    ("preflight_post_json", "preflight-post.json", "preflight_post_path", "preflight_post_sha256"),
    ("window_manifest_env", "window-manifest.env", None, None),
    ("copied_obelisk_log", "Obelisk.log", "copied_log_path", "copied_log_sha256"),
)
NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS = dict(
    approved_evidence_checker.NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS
)
PREACTIVATION_EXECUTOR_SCHEMA_RE = re.compile(
    r"(?:pre[._-]?activation|activation[._-]?preconditions?|executor)",
    re.IGNORECASE,
)
PREACTIVATION_EXECUTOR_SCHEMA_REASON = (
    "preactivation_or_executor_artifact_is_not_approved_runtime_evidence"
)
EXPECTED_TOP_LEVEL_JSON_SIDECARS = frozenset(
    (
        "window-request.json",
        "operator-approval-receipt.json",
        "preflight-pre.json",
        "preflight-post.json",
        approved_evidence_checker.READY_LOG_COPY_FILENAME,
    )
)
EXPECTED_RUNTIME_LOG_POSTURE = {
    "loaded_native_ld_preload": True,
    "process_event_candidate_count": 1,
    "process_event_hook_installed": True,
    "process_event_hook_patch_size": 18,
    "reflection_scanner_disabled": True,
    "plugins_disabled": True,
}
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$")
PREFLIGHT_REQUIRED_FALSE_AUTHORIZATION_FLAGS = frozenset(
    getattr(
        approved_evidence_checker.window_manifest_checker,
        "PREFLIGHT_REQUIRED_FALSE_AUTHORIZATION_FLAGS",
        frozenset(),
    )
)
APPROVED_REJECTED_START_TRIPLET_ALTERNATIVE = "check_join_in_progress_rejected_start"
STRICT_REJECTED_START_DIAGNOSTIC_KEYS = (
    "partial_start_end_present",
    "missing_strict_rejected_start",
    "strict_rejected_start_expected_shape",
    "strict_rejected_start_observed_shape",
)
OBSERVED_TRIPLET_CASE_KEYS = (
    "sequence",
    "target",
    "role",
    "copied_bool_fields",
    "copied_bool_values",
    "principal_action",
    "apply_status",
    "correlation_status",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_obelisk_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=SCRIPT_DIR.parents[0],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"^[0-9a-f]{40}$", commit) is None:
        return None
    return commit


def artifact(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": sha256_file(path)}


def report_identity(report: dict[str, Any]) -> dict[str, str]:
    identity = {
        "artifact_kind": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
        "capture_id": str(report.get("operational_window", {}).get("run_id")),
        "evidence_pack_id": f"player-principal-lifecycle-bundle-{report.get('operational_window', {}).get('run_id')}",
    }
    material = {
        "artifact_identity": identity,
        "report": report,
    }
    return {
        **identity,
        "artifact_sha256": hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true", help="Classify evidence-dir inputs without writing a bundle.")
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help=(
            "live-validation-logs/<run-id> directory to classify or build from. In "
            "build mode this derives --copied-log, --window-manifest, --output-dir, "
            "and --obelisk-commit from the checked sibling set."
        ),
    )
    parser.add_argument("--copied-log", type=Path, help="Copied/sanitized Obelisk log.")
    parser.add_argument("--window-manifest", type=Path, help="Approved operational window manifest.")
    parser.add_argument("--output-dir", type=Path, help="Bundle output directory.")
    parser.add_argument("--obelisk-commit", help="Reviewed Obelisk commit recorded in evidence.")
    parser.add_argument("--reviewed-by", help="Reviewer token/name for the approved manifest.")
    parser.add_argument("--review-note", help="Short consume-only review note.")
    return parser.parse_args()


def path_arg_conflicts(current: Path | None, expected: Path) -> bool:
    return current is not None and current.expanduser().resolve() != expected.expanduser().resolve()


def apply_evidence_dir_build_defaults(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.evidence_dir is None or args.preflight_only:
        return None
    report = classify_preflight_evidence_dir(args.evidence_dir)
    if report.get("bundle_inputs_ready") is not True:
        blockers = report.get("blockers", [])
        detail = ", ".join(str(blocker) for blocker in blockers[:8])
        raise SystemExit(f"--evidence-dir bundle inputs are not ready: {detail}")

    inputs = report.get("inputs", {})
    copied_log = Path(inputs.get("copied_log", {}).get("path", ""))
    window_manifest = Path(inputs.get("window_manifest", {}).get("path", ""))
    output_dir = Path(str(report.get("approved_bundle_path", ""))).parent
    obelisk_commit = inputs.get("obelisk_commit_binding", {}).get("window_manifest_obelisk_commit")
    if not copied_log.is_file() or not window_manifest.is_file() or not isinstance(obelisk_commit, str):
        raise SystemExit("--evidence-dir preflight did not expose complete builder inputs")

    derived_paths = {
        "copied_log": copied_log,
        "window_manifest": window_manifest,
        "output_dir": output_dir,
    }
    for name, expected in derived_paths.items():
        current = getattr(args, name)
        if path_arg_conflicts(current, expected):
            raise SystemExit(
                f"--{name.replace('_', '-')} conflicts with --evidence-dir derived path: "
                f"expected {expected}, got {current}"
            )
        setattr(args, name, expected)
    if args.obelisk_commit is not None and args.obelisk_commit != obelisk_commit:
        raise SystemExit(
            "--obelisk-commit conflicts with --evidence-dir derived commit: "
            f"expected {obelisk_commit}, got {args.obelisk_commit}"
        )
    args.obelisk_commit = obelisk_commit
    if args.reviewed_by is None:
        args.reviewed_by = "runtime-reviewer"
    if args.review_note is None:
        args.review_note = (
            "bounded redacted lifecycle observer summary accepted for consume-only review"
        )
    return report


def run_command(command: list[str], *, stdout_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    if stdout_path is None:
        return subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    with stdout_path.open("w", encoding="utf-8") as stdout:
        result = subprocess.run(command, check=False, text=True, stdout=stdout, stderr=subprocess.PIPE)
    if result.returncode != 0 and not result.stderr.strip():
        try:
            result.stderr = stdout_path.read_text(encoding="utf-8")
        except OSError:
            pass
    return result


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise SystemExit(f"{label} failed with exit {result.returncode}: {stderr}")


def require_expected_failure(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode == 0:
        raise SystemExit(f"{label} unexpectedly passed; evidence bundle overclaims readiness")


def build_window_manifest_replay_report(window_manifest: Path) -> dict[str, Any]:
    old_request_keys = window_manifest_checker.EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS
    old_receipt_keys = window_manifest_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS
    try:
        window_manifest_checker.EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS = (
            old_request_keys | {"direct_join_plan"}
        )
        window_manifest_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS = (
            old_receipt_keys | {"direct_join_plan"}
        )
        fields = window_manifest_checker.load_manifest(window_manifest)
        validation = window_manifest_checker.validate_manifest(
            fields,
            window_manifest,
            post_window_replay=True,
        )
        return window_manifest_checker.build_report(
            fields,
            validation,
            window_manifest,
            post_window_replay=True,
        )
    finally:
        window_manifest_checker.EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS = old_request_keys
        window_manifest_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS = old_receipt_keys


def run_window_manifest_replay_check(
    window_manifest: Path,
    *,
    stdout_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        report = build_window_manifest_replay_report(window_manifest)
    except Exception as exc:  # pragma: no cover - converted to subprocess-compatible failure.
        return subprocess.CompletedProcess(
            [str(WINDOW_MANIFEST_CHECKER), "--json", "--post-window-replay", str(window_manifest)],
            1,
            "",
            str(exc),
        )
    stdout = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if stdout_path is not None:
        stdout_path.write_text(stdout, encoding="utf-8")
    return subprocess.CompletedProcess(
        [str(WINDOW_MANIFEST_CHECKER), "--json", "--post-window-replay", str(window_manifest)],
        0 if report.get("blockers") in (None, []) else 1,
        stdout if stdout_path is None else "",
        "" if report.get("blockers") in (None, []) else stdout,
    )


def require_false_readiness_flags(payload: dict[str, Any], label: str) -> None:
    for key in (
        "server_operations_authorized",
        "runtime_work_authorized",
        "runtime_capture_authorized",
        "live_ops_authorized",
        "reads_live_logs",
        "live_log_read_authorized",
        "live_log_reads_authorized",
        "live_server_log_reads_authorized",
        "publication_authorized",
        "promotion_ready",
        "public_header_allowed",
        "public_sdk_ready",
        "public_abi_ready",
        "v1_completion_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "route_ready",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
        "request_pack_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "copy_report_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "bundle_report_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "request_output_counts_as_approved_runtime_evidence",
        "window_request_counts_as_approved_runtime_evidence",
        "window_request_output_counts_as_approved_runtime_evidence",
        "runtime_window_request_counts_as_approved_runtime_evidence",
        "runtime_window_request_output_counts_as_approved_runtime_evidence",
        "passive_complete_triplets_count_as_approved_runtime_evidence",
        "passive_complete_triplet_counts_as_evidence",
        "passive_snapshots_as_evidence",
        "passive_snapshots_count_as_evidence",
        "passive_snapshot_rollup_counts_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
        "public_reachability_ready",
        "public_reachability_satisfies_runtime_evidence",
        "completion_status_counts_as_approved_runtime_evidence",
        "status_report_counts_as_approved_runtime_evidence",
        "planning_artifact_counts_as_approved_runtime_evidence",
        "planning_snapshot_counts_as_approved_runtime_evidence",
        "activation_preconditions_counts_as_approved_runtime_evidence",
        "player_notice_action_counts_as_approved_runtime_evidence",
        "guarded_beta_notice_action_counts_as_approved_runtime_evidence",
    ):
        if payload.get(key, False) is not False:
            raise SystemExit(f"{label} overclaims {key}")
    for key in ("public_capability_bits_now", "public_callback_abi_now"):
        if payload.get(key, []) != []:
            raise SystemExit(f"{label} overclaims {key}")
    require_no_truthy_readiness_alias_keys(payload, label)


def false_readiness_flag_violation(payload: dict[str, Any], label: str) -> str | None:
    try:
        require_false_readiness_flags(payload, label)
    except SystemExit as exc:
        return str(exc)
    return None


def allowed_internal_triplet_selection_status(trail: str, value: Any) -> bool:
    if trail == "$.post_runtime_contract_gate_required":
        return value is True
    if trail == "$.post_runtime_contract_gate":
        return value == approved_evidence_checker.NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE
    if trail == "$.strict_lifecycle_triplet_selection.accepted":
        return isinstance(value, bool)
    if trail == "$.strict_lifecycle_triplet_selection.status":
        return value in {
            "accepted",
            "invalid_input",
            "missing",
            "incomplete",
            "blocked",
        }
    if trail.startswith("$.lifecycle_correlation_proof"):
        allowed_bool_suffixes = (
            ".accepted",
            ".single_complete_sibling_set",
            ".matched_selected_sequences",
            ".matched_selected_roles",
            ".matched_selected_cases",
            ".selection.accepted",
            ".selection.selected",
        )
        if trail.endswith(allowed_bool_suffixes):
            return isinstance(value, bool)
        if trail.endswith(".selection.status"):
            return value in {
                "selected",
                "invalid_input",
                "missing",
                "incomplete",
                "blocked",
            }
    return False


def require_no_truthy_readiness_alias_keys(value: Any, label: str, trail: str = "$") -> None:
    if trail == "$.blocker_details" or trail.startswith("$.blocker_details["):
        return
    if isinstance(value, dict):
        if trail != "$.strict_lifecycle_triplet_selection" and approved_evidence_checker.split_guardrail_alias_claim(value):
            raise SystemExit(f"{label} overclaims readiness alias {trail}")
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if allowed_internal_triplet_selection_status(child_trail, child):
                continue
            if (
                child not in (False, None, [], {})
                and approved_evidence_checker.contains_unnegated_positive_capability_claim(str(key))
            ):
                raise SystemExit(f"{label} overclaims readiness alias {child_trail}")
            if (
                approved_evidence_checker.guardrail_alias_key_is_forbidden(key)
                and approved_evidence_checker.guardrail_alias_value_is_positive(child)
            ):
                raise SystemExit(f"{label} overclaims readiness alias {child_trail}")
            if approved_evidence_checker.guardrail_path_context_implies_positive_claim(key, child, trail):
                raise SystemExit(f"{label} overclaims readiness alias {child_trail}")
            if (
                approved_evidence_checker.normalized_guardrail_alias_key(key)
                in approved_evidence_checker.GENERIC_STATUS_ALIAS_KEYS
                and approved_evidence_checker.guardrail_alias_value_is_positive(child)
            ):
                raise SystemExit(f"{label} overclaims readiness alias {child_trail}")
            require_no_truthy_readiness_alias_keys(child, label, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            require_no_truthy_readiness_alias_keys(child, label, f"{trail}[{index}]")


def require_consume_only_check_report(payload: dict[str, Any], label: str) -> None:
    if payload.get("schema") != approved_evidence_checker.REPORT_SCHEMA:
        raise SystemExit(f"{label} schema mismatch")
    if payload.get("mode") != "consume":
        raise SystemExit(f"{label} mode mismatch")
    if payload.get("ready_scope") != "runtime_evidence_only":
        raise SystemExit(f"{label} ready_scope mismatch")
    if payload.get("ready") is not True:
        raise SystemExit(f"{label} did not accept consume-only runtime evidence")
    if payload.get("approved_runtime_evidence_present") is not True:
        raise SystemExit(f"{label} did not preserve approved runtime evidence presence")
    if payload.get("runtime_evidence_ready") is not True:
        raise SystemExit(f"{label} did not preserve runtime evidence readiness")
    require_false_readiness_flags(payload, label)
    if payload.get("blockers") != []:
        raise SystemExit(f"{label} reported blockers despite ready consume-only evidence")
    if payload.get("remaining_blockers") != []:
        raise SystemExit(f"{label} reported remaining blockers despite ready consume-only evidence")
    if payload.get("next_blocker") != "identity_public_contract_gate_missing":
        raise SystemExit(f"{label} did not route to the identity public contract gate")


def require_negative_readiness_report(payload: dict[str, Any], label: str, expected_blocker: str) -> None:
    expected_mode = expected_blocker.removesuffix("_blocked_until_identity_public_contract_gate")
    if payload.get("schema") != approved_evidence_checker.REPORT_SCHEMA:
        raise SystemExit(f"{label} schema mismatch")
    if payload.get("mode") != expected_mode:
        raise SystemExit(f"{label} mode mismatch")
    if payload.get("ready_scope") != "runtime_evidence_only":
        raise SystemExit(f"{label} ready_scope mismatch")
    if payload.get("ready") is not False:
        raise SystemExit(f"{label} did not fail closed")
    if payload.get("approved_runtime_evidence_present") is not True:
        raise SystemExit(f"{label} lost consume-only runtime evidence acceptance")
    if payload.get("runtime_evidence_ready") is not True:
        raise SystemExit(f"{label} lost runtime evidence readiness")
    require_false_readiness_flags(payload, label)
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or expected_blocker not in blockers:
        raise SystemExit(f"{label} failed for an unexpected blocker")
    remaining_blockers = payload.get("remaining_blockers", [])
    if (
        payload.get("approved_runtime_evidence_present") is True
        and payload.get("runtime_evidence_ready") is True
        and remaining_blockers not in (None, [])
    ):
        raise SystemExit(f"{label} carried runtime evidence blockers despite accepted evidence")
    if payload.get("next_blocker") != "identity_public_contract_gate_missing":
        raise SystemExit(f"{label} did not preserve the identity public contract gate blocker")


def require_approved_copied_log(path: Path) -> Path:
    reject_symlink_component(path, "--copied-log")
    status = protected_paths.protected_path_status(
        path.expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        raise SystemExit(f"--copied-log must be an offline copy, not a live server path: {status.resolved}")
    if not status.approved_offline_workspace:
        raise SystemExit("--copied-log must be under /servidor/ark/workspace-offline")
    if not status.resolved.is_file():
        raise SystemExit(f"--copied-log does not exist: {status.resolved}")
    if len(status.resolved.parts) < 3 or status.resolved.parts[-3] != EXPECTED_COPIED_LOG_PARENT:
        raise SystemExit("--copied-log must be live-validation-logs/<run-id>/Obelisk.log")
    if status.resolved.parts[-1] != "Obelisk.log":
        raise SystemExit("--copied-log must be live-validation-logs/<run-id>/Obelisk.log")
    return status.resolved


def require_exact_sibling_window_manifest(path: Path, copied_log: Path) -> Path:
    reject_symlink_component(path, "--window-manifest")
    status = protected_paths.protected_path_status(
        path.expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        raise SystemExit(f"--window-manifest must be an offline copy, not a live server path: {status.resolved}")
    if not status.approved_offline_workspace:
        raise SystemExit("--window-manifest must be under /servidor/ark/workspace-offline")
    expected = copied_log.parent / "window-manifest.env"
    if status.resolved != expected:
        raise SystemExit(
            "--window-manifest must be the exact sibling window-manifest.env beside --copied-log: "
            f"expected {expected}, got {status.resolved}"
        )
    if not status.resolved.is_file():
        raise SystemExit(f"--window-manifest does not exist: {status.resolved}")
    return status.resolved


def add_blocker(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def file_state(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    reject_symlink_component(path, label)
    status = protected_paths.protected_path_status(
        path.expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    state = {
        "path": str(status.resolved),
        "exists": status.resolved.is_file(),
        "approved_offline_workspace": status.approved_offline_workspace,
        "protected": status.protected,
        "sha256": None,
    }
    if status.protected:
        add_blocker(blockers, f"{label}_under_protected_server_root", label, path=str(status.resolved))
    if not status.approved_offline_workspace:
        add_blocker(blockers, f"{label}_not_approved_offline_workspace", label, path=str(status.resolved))
    if not status.resolved.is_file():
        add_blocker(blockers, f"{label}_missing", label, path=str(status.resolved))
    elif not status.protected and status.approved_offline_workspace:
        state["sha256"] = sha256_file(status.resolved)
    return state


def offline_readable_file_state(state: dict[str, Any]) -> bool:
    return (
        state.get("exists") is True
        and state.get("approved_offline_workspace") is not False
        and state.get("protected") is not True
    )


def unprotected_existing_file_state(state: dict[str, Any]) -> bool:
    return state.get("exists") is True and state.get("protected") is not True


def run_json_check(command: list[str]) -> tuple[int, dict[str, Any] | None, str]:
    result = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    payload: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    return result.returncode, payload, result.stderr.strip()


def request_pack_check_state(
    request_pack: dict[str, Any],
    observer_env: dict[str, Any],
    operator_approval_receipt: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "checked": False,
        "ready": False,
        "checker_ready": False,
        "exit_code": None,
        "schema": None,
        "stderr": "",
        "blockers": [],
    }
    if not request_pack["exists"] or not observer_env["exists"]:
        return state
    if not offline_readable_file_state(request_pack) or not offline_readable_file_state(observer_env):
        return state
    command = [
        sys.executable,
        str(WINDOW_REQUEST_CHECKER),
        "--json",
        str(request_pack["path"]),
        "--env-file",
        str(observer_env["path"]),
        "--post-window-replay",
    ]
    if offline_readable_file_state(operator_approval_receipt):
        command.extend(["--operator-approval-receipt", str(operator_approval_receipt["path"])])
    state["checked"] = True
    exit_code, payload, stderr = run_json_check(command)
    state["exit_code"] = exit_code
    state["stderr"] = stderr
    if isinstance(payload, dict):
        state["schema"] = payload.get("schema")
        state["checker_ready"] = payload.get("ready") is True
        state["blockers"] = payload.get("blockers", [])
        state["next_blocker"] = payload.get("next_blocker")
        state["post_window_replay"] = payload.get("post_window_replay") is True
        state["post_window_replay_expiry_tolerated"] = (
            payload.get("post_window_replay_expiry_tolerated") is True
        )
        state["ready"] = (
            exit_code == 0
            and payload.get("ready") is True
            and payload.get("request_pack_ready") is True
            and state["post_window_replay"]
            and state["post_window_replay_expiry_tolerated"]
        )
    if not state["ready"]:
        add_blocker(
            blockers,
            "request_pack_check_failed",
            "request_pack",
            exit_code=exit_code,
            request_check_blockers=state.get("blockers", []),
        )
    return state


def window_manifest_check_state(window_manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    state: dict[str, Any] = {
        "checked": False,
        "ready": False,
        "exit_code": None,
        "schema": None,
        "stderr": "",
    }
    if not window_manifest["exists"]:
        return state
    if not offline_readable_file_state(window_manifest):
        return state
    state["checked"] = True
    result = run_window_manifest_replay_check(Path(str(window_manifest["path"])))
    exit_code = result.returncode
    stderr = result.stderr.strip()
    payload: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    state["exit_code"] = exit_code
    state["stderr"] = stderr
    if isinstance(payload, dict):
        state["schema"] = payload.get("schema")
        state["checker_ready"] = payload.get("ready") is True
        operator_receipt = payload.get("operator_approval_receipt")
        state["ready"] = (
            exit_code == 0
            and payload.get("ready") is True
            and payload.get("operational_window_manifest_ready") is True
            and payload.get("post_window_replay") is True
            and isinstance(operator_receipt, dict)
            and operator_receipt.get("verified") is True
            and payload.get("blockers", []) == []
            and payload.get("remaining_blockers", []) == []
        )
        state["blockers"] = payload.get("blockers", [])
        state["next_blocker"] = payload.get("next_blocker")
    if not state["ready"]:
        add_blocker(
            blockers,
            "window_manifest_check_failed",
            "window_manifest",
            exit_code=exit_code,
            window_manifest_check_blockers=state.get("blockers", []),
        )
    return state


def approved_runtime_manifest_check_state(
    approved_bundle: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    expected_run_id: str | None = None,
    expected_copied_log_path: Path | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "checked": False,
        "ready": False,
        "exit_code": None,
        "schema": None,
        "stderr": "",
        "next_blocker": None,
    }
    if not approved_bundle["exists"]:
        return state
    if not offline_readable_file_state(approved_bundle):
        return state
    state["checked"] = True
    exit_code, payload, stderr = run_json_check(
        [
            sys.executable,
            str(CHECKER),
            "--json",
            str(approved_bundle["path"]),
        ]
    )
    state["exit_code"] = exit_code
    state["stderr"] = stderr
    if isinstance(payload, dict):
        state["schema"] = payload.get("schema")
        state["mode"] = payload.get("mode")
        state["ready_scope"] = payload.get("ready_scope")
        state["checker_ready"] = payload.get("ready") is True
        for key in STRICT_REJECTED_START_DIAGNOSTIC_KEYS:
            state[key] = payload.get(key)
        missing_roles = payload.get("missing_lifecycle_event_roles")
        state["missing_lifecycle_event_roles"] = (
            list(missing_roles)
            if isinstance(missing_roles, list) and all(isinstance(role, str) for role in missing_roles)
            else []
        )
        strict_selection = payload.get("strict_lifecycle_triplet_selection")
        state["strict_lifecycle_triplet_selection"] = (
            strict_selection if isinstance(strict_selection, dict) else {}
        )
        session_end_missing_correlation = payload.get(
            "session_end_missing_correlation_diagnostics"
        )
        state["session_end_missing_correlation_diagnostics"] = (
            session_end_missing_correlation
            if isinstance(session_end_missing_correlation, dict)
            else None
        )
        readiness_overclaim = false_readiness_flag_violation(
            payload,
            "approved runtime manifest check",
        )
        payload_blockers = payload.get("blockers", [])
        if not isinstance(payload_blockers, list):
            payload_blockers = []
        state["blockers"] = list(payload_blockers)
        if readiness_overclaim is not None:
            state["blockers"].append("approved_runtime_manifest_check_readiness_overclaim")
            state["readiness_overclaim"] = readiness_overclaim
        state["ready"] = (
            exit_code == 0
            and payload.get("schema") == approved_evidence_checker.REPORT_SCHEMA
            and payload.get("mode") == "consume"
            and payload.get("ready_scope") == "runtime_evidence_only"
            and payload.get("ready") is True
            and payload.get("approved_runtime_evidence_present") is True
            and payload.get("runtime_evidence_ready") is True
            and payload.get("promotion_ready") is False
            and payload.get("public_header_allowed", False) is False
            and payload.get("public_sdk_ready") is False
            and payload.get("public_abi_ready", False) is False
            and payload.get("v1_completion_ready", False) is False
            and payload.get("runtime_ready") is False
            and readiness_overclaim is None
            and payload.get("public_capability_bits_now", []) == []
            and payload.get("public_callback_abi_now", []) == []
            and payload_blockers == []
            and payload.get("remaining_blockers") == []
            and payload.get("next_blocker") == "identity_public_contract_gate_missing"
        )
        state["next_blocker"] = payload.get("next_blocker")
    if state["ready"] and (expected_run_id is not None or expected_copied_log_path is not None):
        try:
            manifest_payload = load_json(Path(approved_bundle["path"]))
        except (OSError, json.JSONDecodeError) as exc:
            add_blocker(
                blockers,
                "approved_runtime_manifest_binding_unreadable",
                "approved_runtime_manifest",
                detail=str(exc),
            )
            state["ready"] = False
        else:
            operational_window = manifest_payload.get("operational_window")
            if not isinstance(operational_window, dict):
                add_blocker(
                    blockers,
                    "approved_runtime_manifest_operational_window_missing",
                    "approved_runtime_manifest",
                )
                state["ready"] = False
            else:
                state["run_id"] = operational_window.get("run_id")
                copied_log = operational_window.get("copied_log")
                copied_log_path = copied_log.get("path") if isinstance(copied_log, dict) else None
                state["copied_log_path"] = copied_log_path
                if expected_run_id is not None and operational_window.get("run_id") != expected_run_id:
                    add_blocker(
                        blockers,
                        "approved_runtime_manifest_run_id_mismatch",
                        "approved_runtime_manifest",
                        expected=expected_run_id,
                        actual=operational_window.get("run_id"),
                    )
                    state["ready"] = False
                if expected_copied_log_path is not None:
                    expected_copied_log = str(expected_copied_log_path.expanduser().resolve())
                    actual_copied_log = (
                        str(Path(copied_log_path).expanduser().resolve())
                        if isinstance(copied_log_path, str) and copied_log_path
                        else None
                    )
                    if actual_copied_log != expected_copied_log:
                        add_blocker(
                            blockers,
                            "approved_runtime_manifest_copied_log_path_mismatch",
                            "approved_runtime_manifest",
                            expected=expected_copied_log,
                            actual=actual_copied_log,
                        )
                        state["ready"] = False
    if not state["ready"]:
        diagnostic_extra = {
            key: state[key]
            for key in STRICT_REJECTED_START_DIAGNOSTIC_KEYS
            if key in state
        }
        add_blocker(
            blockers,
            "approved_runtime_manifest_check_failed",
            "approved_runtime_manifest",
            exit_code=exit_code,
            approved_runtime_check_blockers=state.get("blockers", []),
            **diagnostic_extra,
        )
    return state


def next_required_preflight_artifacts(
    copied_log: dict[str, Any],
    window_manifest: dict[str, Any],
    request_pack: dict[str, Any],
    observer_env: dict[str, Any],
    operator_request: dict[str, Any],
    operator_approval_receipt: dict[str, Any],
    preflight_pre: dict[str, Any],
    preflight_post: dict[str, Any],
    approved_bundle: dict[str, Any],
    approved_bundle_check: dict[str, Any],
) -> list[dict[str, Any]]:
    required = [
        (
            "copied_obelisk_log",
            "Obelisk.log",
            copied_log,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
            None,
        ),
        (
            "checked_window_manifest_env",
            "window-manifest.env",
            window_manifest,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
            None,
        ),
        (
            "window_request_json",
            "window-request.json",
            request_pack,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
            None,
        ),
        (
            "observer_window_env",
            "observer-window.env",
            observer_env,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
            None,
        ),
        (
            "operator_approval_request_md",
            "operator-approval-request.md",
            operator_request,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
            None,
        ),
        (
            "operator_approval_receipt",
            "operator-approval-receipt.json",
            operator_approval_receipt,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
            None,
        ),
        (
            "preflight_pre_json",
            "preflight-pre.json",
            preflight_pre,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
            None,
        ),
        (
            "preflight_post_json",
            "preflight-post.json",
            preflight_post,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
            None,
        ),
        (
            "approved_runtime_principal_lifecycle_evidence_manifest",
            APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
            approved_bundle,
            "approved_runtime_evidence_missing",
            bool(approved_bundle_check.get("ready")),
            bool(approved_bundle_check.get("ready")) if approved_bundle.get("exists") is True else None,
        ),
    ]
    artifacts: list[dict[str, Any]] = []
    for (
        artifact,
        relative_path,
        state,
        required_for,
        satisfies_approved_runtime_evidence,
        checker_ready,
    ) in required:
        status = preflight_artifact_status(
            state,
            checker_ready=checker_ready,
            accepted_as_approved_runtime_evidence=satisfies_approved_runtime_evidence,
        )
        artifacts.append(
            {
                "artifact": artifact,
                "relative_path": relative_path,
                "path": state.get("path"),
                "present": state.get("exists") is True,
                "status": status,
                "missing_blocker": f"{artifact}_missing" if status == "missing" else None,
                "required_for": required_for,
                "required_before_approved_bundle_builder": (
                    relative_path != APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH
                ),
                "required_to_accept_approved_runtime_evidence": True,
                "counts_as_approved_runtime_evidence_before_checker_acceptance": False,
                "satisfies_approved_runtime_evidence": satisfies_approved_runtime_evidence,
            }
        )
    return artifacts


def preflight_artifact_status(
    state: dict[str, Any],
    *,
    checker_ready: bool | None = None,
    accepted_as_approved_runtime_evidence: bool = False,
) -> str:
    if state.get("exists") is not True:
        return "missing"
    if state.get("protected") is True:
        return "blocked_protected_server_root"
    if state.get("approved_offline_workspace") is False:
        return "blocked_not_approved_offline_workspace"
    if checker_ready is False:
        return "present_but_checker_failed"
    if accepted_as_approved_runtime_evidence:
        return "accepted_by_approved_runtime_evidence_checker"
    return "present"


def operator_request_sidecar_state(
    request_pack: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    request_path = request_pack.get("path")
    if not isinstance(request_path, str) or not request_path:
        add_blocker(blockers, "operator_request_path_unavailable", "operator_request")
        return {
            "path": None,
            "exists": False,
            "approved_offline_workspace": False,
            "protected": False,
            "sha256": None,
        }
    return file_state(Path(request_path).with_name("operator-approval-request.md"), "operator_request", blockers)


def copy_readiness_context(state: dict[str, Any]) -> dict[str, Any]:
    analysis = state.get("analysis", {})
    session_end_missing_correlation = (
        approved_evidence_checker.session_end_missing_correlation_diagnostics_from_module(
            analysis if isinstance(analysis, dict) else None
        )
    )
    return {
        "report_present": state.get("exists") is True,
        "report_checked": state.get("checked") is True,
        "report_accepted": state.get("accepted") is True,
        "copy_readiness": state.get("copy_readiness", "not_provided"),
        "ready_to_copy": state.get("ready_to_copy") is True,
        "roles_present": state.get("roles_present", []),
        "missing_roles": state.get("missing_roles", []),
        "analysis": analysis,
        "session_end_missing_correlation_diagnostics": session_end_missing_correlation,
        "reported_blockers": state.get("reported_blockers", []),
        "source_log_safety": state.get("source_log_safety", {}),
        "source_log_not_ready": state.get("source_log_not_ready", {}),
        "source_log_not_ready_reason": state.get("source_log_not_ready_reason"),
        "source_log_not_ready_blockers": state.get("source_log_not_ready_blockers", []),
        "observer_only_no_role_window_detected": (
            state.get("observer_only_no_role_window_detected") is True
        ),
        "player_present_but_no_lifecycle_roles": (
            state.get("player_present_but_no_lifecycle_roles") is True
        ),
        "player_presence_context": state.get("player_presence_context", {}),
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "copy_report_counts_as_approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "blockers": state.get("blockers", []),
    }


def observer_no_lifecycle_role_diagnostics_from_copy_context(
    context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(context, dict):
        return None
    missing_roles = context.get("missing_roles")
    roles_present = context.get("roles_present")
    if not isinstance(missing_roles, list) or not isinstance(roles_present, list):
        return None
    no_lifecycle_roles = (
        roles_present == []
        and missing_roles == list(approved_evidence_checker.READY_LOG_COPY_REQUIRED_ROLES)
    )
    if (
        not no_lifecycle_roles
        and context.get("observer_only_no_role_window_detected") is not True
        and context.get("player_present_but_no_lifecycle_roles") is not True
    ):
        return None
    return {
        "observer_only_no_role_window_detected": (
            context.get("observer_only_no_role_window_detected") is True
        ),
        "player_present_but_no_lifecycle_roles": (
            context.get("player_present_but_no_lifecycle_roles") is True
        ),
        "source_log_not_ready_reason": context.get("source_log_not_ready_reason"),
        "source_log_not_ready_blockers": context.get("source_log_not_ready_blockers", []),
        "roles_present": roles_present,
        "missing_roles": missing_roles,
        "copy_readiness": context.get("copy_readiness", "not_provided"),
        "reported_blockers": context.get("reported_blockers", []),
        "player_presence_context": context.get("player_presence_context", {}),
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
    }


def read_manifest_fields(path: Path, blockers: list[dict[str, Any]]) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        add_blocker(blockers, "window_manifest_unreadable", "window_manifest", detail=str(exc))
        return fields
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            add_blocker(blockers, "window_manifest_line_not_key_value", "window_manifest", line=line_number)
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            add_blocker(
                blockers,
                "window_manifest_key_unsafe",
                "window_manifest",
                line=line_number,
                key=key,
            )
            continue
        if key in fields:
            add_blocker(
                blockers,
                "window_manifest_duplicate_key",
                "window_manifest",
                line=line_number,
                key=key,
            )
            continue
        fields[key] = value
    return fields


def path_from_manifest(
    fields: dict[str, str],
    manifest_path: Path,
    key: str,
    fallback: Path,
    blockers: list[dict[str, Any]],
) -> Path:
    value = fields.get(key)
    if not value:
        add_blocker(blockers, f"{key}_missing", key)
        return fallback
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return manifest_path.parent / path


def copied_log_manifest_binding_ready(
    copied_log: dict[str, Any],
    manifest_path: Path,
    manifest_fields: dict[str, str],
    blockers: list[dict[str, Any]],
) -> bool:
    expected_path_text = copied_log.get("path")
    expected_sha256 = copied_log.get("sha256")
    if not isinstance(expected_path_text, str) or not expected_path_text:
        return False

    ready = True
    expected_path = Path(expected_path_text).expanduser().resolve()
    manifest_copied_log_path = path_from_manifest(
        manifest_fields,
        manifest_path,
        "copied_log_path",
        expected_path,
        blockers,
    )
    manifest_resolved = manifest_copied_log_path.expanduser().resolve()
    if manifest_resolved != expected_path:
        add_blocker(
            blockers,
            "copied_log_manifest_path_mismatch",
            "copied_log_path",
            expected=str(expected_path),
            actual=str(manifest_resolved),
        )
        ready = False

    manifest_sha256 = manifest_fields.get("copied_log_sha256")
    if not isinstance(manifest_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) is None:
        add_blocker(
            blockers,
            "copied_log_manifest_sha256_invalid",
            "copied_log_sha256",
            expected=expected_sha256,
            actual=manifest_sha256,
        )
        return False
    if manifest_sha256 != expected_sha256:
        add_blocker(
            blockers,
            "copied_log_manifest_sha256_mismatch",
            "copied_log_sha256",
            expected=expected_sha256,
            actual=manifest_sha256,
        )
        ready = False
    return ready


def manifest_relative_path(value: str, manifest_path: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return manifest_path.parent / path


def sibling_artifact_state(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    symlink = protected_paths.first_symlink_component(path)
    status = protected_paths.protected_path_status(
        path.expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    state: dict[str, Any] = {
        "path": str(status.resolved),
        "exists": status.resolved.is_file(),
        "approved_offline_workspace": status.approved_offline_workspace,
        "protected": status.protected,
        "symlink": str(symlink) if symlink is not None else None,
        "sha256": None,
        "size_bytes": None,
    }
    if symlink is not None:
        add_blocker(blockers, f"{label}_symlink_component", label, path=str(symlink))
    if status.protected:
        add_blocker(blockers, f"{label}_under_protected_server_root", label, path=str(status.resolved))
    if not status.approved_offline_workspace:
        add_blocker(blockers, f"{label}_not_approved_offline_workspace", label, path=str(status.resolved))
    if not status.resolved.is_file():
        add_blocker(blockers, f"{label}_missing", label, path=str(status.resolved))
    elif symlink is None and not status.protected and status.approved_offline_workspace:
        data = status.resolved.read_bytes()
        state["sha256"] = hashlib.sha256(data).hexdigest()
        state["size_bytes"] = len(data)
    return state


def check_manifest_declared_path(
    *,
    fields: dict[str, str],
    manifest_path: Path,
    path_key: str,
    expected_path: Path,
    blockers: list[dict[str, Any]],
) -> None:
    value = fields.get(path_key)
    if not value:
        add_blocker(blockers, f"{path_key}_missing", path_key)
        return
    declared = manifest_relative_path(value, manifest_path)
    symlink = protected_paths.first_symlink_component(declared)
    if symlink is not None:
        add_blocker(blockers, f"{path_key}_symlink_component", path_key, path=str(symlink))
    status = protected_paths.protected_path_status(
        declared,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        add_blocker(blockers, f"{path_key}_under_protected_server_root", path_key, path=str(status.resolved))
    if not status.approved_offline_workspace:
        add_blocker(blockers, f"{path_key}_not_approved_offline_workspace", path_key, path=str(status.resolved))
    if status.resolved != expected_path.expanduser().resolve():
        add_blocker(
            blockers,
            f"{path_key}_not_exact_sibling_path",
            path_key,
            expected=str(expected_path.expanduser().resolve()),
            actual=str(status.resolved),
        )


def check_manifest_declared_sha(
    *,
    fields: dict[str, str],
    sha_key: str,
    expected_sha256: str | None,
    blockers: list[dict[str, Any]],
) -> None:
    value = fields.get(sha_key)
    if not value:
        add_blocker(blockers, f"{sha_key}_missing", sha_key)
        return
    if SHA256_RE.fullmatch(value) is None:
        add_blocker(blockers, f"{sha_key}_invalid", sha_key, actual=value)
        return
    if value == "0" * 64:
        add_blocker(blockers, f"{sha_key}_placeholder", sha_key)
        return
    if expected_sha256 is not None and value != expected_sha256:
        add_blocker(
            blockers,
            f"{sha_key}_mismatch",
            sha_key,
            expected=expected_sha256,
            actual=value,
        )


def window_manifest_commit_binding_state(
    fields: dict[str, str],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    initial_blocker_count = len(blockers)
    current_commit = current_obelisk_commit()
    manifest_commit = fields.get("obelisk_commit")
    if current_commit is None:
        add_blocker(blockers, "current_obelisk_commit_unavailable", "obelisk_commit")
    if manifest_commit is None:
        add_blocker(blockers, "window_manifest_obelisk_commit_missing", "obelisk_commit")
    elif not is_reviewed_obelisk_commit(manifest_commit):
        add_blocker(
            blockers,
            "window_manifest_obelisk_commit_invalid",
            "obelisk_commit",
            actual=manifest_commit,
        )
    elif current_commit is not None and manifest_commit != current_commit:
        add_blocker(
            blockers,
            "window_manifest_obelisk_commit_not_current_head",
            "obelisk_commit",
            expected=current_commit,
            actual=manifest_commit,
        )
    return {
        "ready": len(blockers) == initial_blocker_count,
        "current_obelisk_commit": current_commit,
        "window_manifest_obelisk_commit": manifest_commit,
        "blockers": [
            blocker["reason"]
            for blocker in blockers[initial_blocker_count:]
        ],
        "blocker_details": blockers[initial_blocker_count:],
        "non_claim": "window manifest commit binding only; does not approve runtime evidence",
    }


def load_sibling_json(state: dict[str, Any], label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    if (
        state.get("exists") is not True
        or state.get("approved_offline_workspace") is not True
        or state.get("protected") is True
        or state.get("symlink") is not None
    ):
        return None
    try:
        payload = json.loads(Path(str(state["path"])).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add_blocker(blockers, f"{label}_json_invalid", label, detail=str(exc))
        return None
    except OSError as exc:
        add_blocker(blockers, f"{label}_unreadable", label, detail=str(exc))
        return None
    if not isinstance(payload, dict):
        add_blocker(blockers, f"{label}_not_object", label)
        return None
    return payload


def expected_bound_artifact(state: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(state.get("path"), str) or not isinstance(state.get("sha256"), str):
        return None
    if not isinstance(state.get("size_bytes"), int):
        return None
    return {
        "path": state["path"],
        "sha256": state["sha256"],
        "size_bytes": state["size_bytes"],
    }


def add_non_evidence_schema_blocker(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    reason_prefix: str,
    label: str,
) -> None:
    schema = payload.get("schema")
    if not isinstance(schema, str):
        return
    if (
        schema == approved_evidence_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCHEMA
        and reason_prefix == "operator_approval_receipt_json"
    ):
        return
    reason = NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS.get(schema)
    if reason is None:
        reason = approved_evidence_checker.non_approved_runtime_evidence_schema_alias_reason(schema)
    if reason is None and PREACTIVATION_EXECUTOR_SCHEMA_RE.search(schema):
        reason = PREACTIVATION_EXECUTOR_SCHEMA_REASON
    if reason is None:
        return
    add_blocker(blockers, f"{reason_prefix}_{reason}", label, schema=schema)


def json_claim_path(parent: str, child: object) -> str:
    key = str(child)
    return f"{parent}.{key}" if parent else key


def normalized_claim_key(key: object) -> str:
    return approved_evidence_checker.normalized_guardrail_alias_key(key)


NEGATIVE_SIDECAR_TOKENS = frozenset(
    (
        "blocked",
        "candidate",
        "false",
        "missing",
        "no",
        "non",
        "none",
        "not",
        "only",
        "refused",
        "rejected",
        "required",
        "requires",
        "unsupported",
    )
)
POSITIVE_SIDECAR_TOKENS = frozenset(
    (
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "available",
        "complete",
        "completed",
        "enabled",
        "present",
        "ready",
        "sent",
        "supported",
        "true",
        "unlocked",
        "validated",
        "yes",
    )
)


def sidecar_alias_tokens(value: object) -> set[str]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return {token for token in re.split(r"[^A-Za-z0-9]+", separated.casefold()) if token}


def negative_json_sidecar_context(key: object, value: Any) -> bool:
    key_tokens = sidecar_alias_tokens(key)
    if key_tokens & {
        "blocker",
        "blocked",
        "missing",
        "must",
        "no",
        "non",
        "not",
        "required",
        "requires",
    }:
        return True
    if isinstance(value, str):
        value_tokens = sidecar_alias_tokens(value)
        if value_tokens & NEGATIVE_SIDECAR_TOKENS and not (value_tokens & POSITIVE_SIDECAR_TOKENS):
            return True
        if {"not", "authorized"}.issubset(value_tokens):
            return True
        if {"request", "only"}.issubset(value_tokens) and "authorized" in value_tokens:
            return True
    return False


def check_json_sidecar_overclaims(
    value: Any,
    label: str,
    blockers: list[dict[str, Any]],
    *,
    trail: str = "$",
) -> None:
    forbidden_flag_keys = {
        normalized_claim_key(key)
        for key in approved_evidence_checker.FORBIDDEN_POSITIVE_FLAG_KEYS
    }
    if isinstance(value, dict):
        if trail != "$" and value.get("schema") == approved_evidence_checker.SCHEMA:
            add_blocker(
                blockers,
                "json_sidecar_nested_approved_runtime_manifest_schema",
                label,
                key_path=f"{trail}.schema",
                schema=approved_evidence_checker.SCHEMA,
            )
        if approved_evidence_checker.split_guardrail_alias_claim(value):
            add_blocker(
                blockers,
                "json_sidecar_authorization_or_readiness_key_overclaim",
                label,
                key_path=trail,
                actual=value,
            )
        for key, child in value.items():
            child_trail = json_claim_path(trail, key)
            if approved_evidence_checker.source_overclaim_alias_key_is_forbidden(key):
                add_blocker(
                    blockers,
                    "json_sidecar_source_overclaim_alias_is_not_approved_runtime_evidence",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if approved_evidence_checker.lifecycle_role_alias_claim_is_forbidden(key, child):
                add_blocker(
                    blockers,
                    "json_sidecar_lifecycle_role_alias_is_not_approved_runtime_evidence",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if negative_json_sidecar_context(key, child):
                if isinstance(child, (dict, list)):
                    check_json_sidecar_overclaims(child, label, blockers, trail=child_trail)
                continue
            if normalized_claim_key(key) in forbidden_flag_keys and child is not False:
                add_blocker(
                    blockers,
                    "json_sidecar_readiness_flag_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if (
                child not in (False, None, [], {})
                and approved_evidence_checker.contains_unnegated_positive_capability_claim(str(key))
            ):
                add_blocker(
                    blockers,
                    "json_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if (
                approved_evidence_checker.guardrail_alias_key_is_forbidden(key)
                and approved_evidence_checker.guardrail_alias_value_is_positive(child)
            ):
                add_blocker(
                    blockers,
                    "json_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if (
                approved_evidence_checker.guardrail_acceptance_alias_key_is_forbidden(key, trail)
                and approved_evidence_checker.guardrail_alias_value_is_positive(child)
            ):
                add_blocker(
                    blockers,
                    "json_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if approved_evidence_checker.guardrail_path_context_implies_positive_claim(key, child, trail):
                add_blocker(
                    blockers,
                    "json_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if (
                approved_evidence_checker.normalized_guardrail_alias_key(key)
                in approved_evidence_checker.GENERIC_STATUS_ALIAS_KEYS
                and approved_evidence_checker.guardrail_alias_value_is_positive(child)
            ):
                add_blocker(
                    blockers,
                    "json_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if key in ("public_capability_bits_now", "public_callback_abi_now") and child != []:
                add_blocker(
                    blockers,
                    "json_sidecar_public_surface_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            check_json_sidecar_overclaims(child, label, blockers, trail=child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_json_sidecar_overclaims(child, label, blockers, trail=f"{trail}[{index}]")
    elif (
        isinstance(value, str)
        and value not in approved_evidence_checker.ALLOWED_POSITIVE_MATCH_NON_CLAIMS
        and (
            approved_evidence_checker.contains_unnegated_positive_capability_claim(value)
            or (
                approved_evidence_checker.is_readiness_alias_context(trail)
                and approved_evidence_checker.is_forbidden_readiness_alias(value)
            )
        )
    ):
        add_blocker(
            blockers,
            "json_sidecar_authorization_or_readiness_text_overclaim",
            label,
            key_path=trail,
            value=value,
        )


def check_known_non_evidence_json_sidecar(
    state: dict[str, Any],
    label: str,
    blockers: list[dict[str, Any]],
) -> None:
    if (
        state.get("exists") is not True
        or state.get("approved_offline_workspace") is not True
        or state.get("protected") is True
        or state.get("symlink") is not None
    ):
        return
    try:
        payload = json.loads(Path(str(state["path"])).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(payload, dict):
        return
    add_non_evidence_schema_blocker(
        payload,
        blockers,
        reason_prefix=label,
        label=label,
    )
    check_json_sidecar_overclaims(payload, label, blockers)
    if label in {"preflight_pre_json", "preflight_post_json"}:
        for key in sorted(PREFLIGHT_REQUIRED_FALSE_AUTHORIZATION_FLAGS):
            if payload.get(key) is not False:
                add_blocker(
                    blockers,
                    f"{label}_{key}_not_false",
                    label,
                    expected=False,
                    actual=payload.get(key),
            )


def add_non_evidence_input_path_alias_blockers(
    path: Path,
    blockers: list[dict[str, Any]],
    *,
    reason_prefix: str,
    label: str,
    schema: str | None = None,
) -> None:
    for path_reason in approved_evidence_checker.non_approved_runtime_evidence_input_path_alias_reasons(path):
        add_blocker(
            blockers,
            f"{reason_prefix}_{path_reason}",
            label,
            path=str(path),
            schema=schema,
        )


def check_unexpected_non_evidence_json_sidecars(
    directory: Path,
    blockers: list[dict[str, Any]],
) -> None:
    try:
        entries = list(directory.iterdir())
    except FileNotFoundError:
        return
    except OSError as exc:
        add_blocker(blockers, "evidence_dir_unreadable_for_sidecar_scan", "evidence_dir", detail=str(exc))
        return
    for entry in sorted(entries):
        if entry.name in EXPECTED_TOP_LEVEL_JSON_SIDECARS or entry.name == "window-manifest.env":
            continue
        if entry.name == "approved-bundle" or entry.suffix.casefold() != ".json":
            continue
        if not entry.is_file() and not entry.is_symlink():
            continue
        state = sibling_artifact_state(entry, f"unexpected_json_sidecar.{entry.name}", blockers)
        if (
            state.get("exists") is not True
            or state.get("approved_offline_workspace") is not True
            or state.get("protected") is True
            or state.get("symlink") is not None
        ):
            continue
        try:
            payload = json.loads(entry.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        schema = payload.get("schema")
        reason = NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS.get(schema) if isinstance(schema, str) else None
        if reason is None and isinstance(schema, str):
            reason = approved_evidence_checker.non_approved_runtime_evidence_schema_alias_reason(schema)
        if reason is None and isinstance(schema, str) and PREACTIVATION_EXECUTOR_SCHEMA_RE.search(schema):
            reason = PREACTIVATION_EXECUTOR_SCHEMA_REASON
        label = f"unexpected_json_sidecar.{entry.name}"
        if reason is not None:
            add_blocker(
                blockers,
                f"unexpected_json_sidecar_{reason}",
                label,
                path=str(entry),
                schema=schema,
            )
        elif isinstance(schema, str):
            add_blocker(
                blockers,
                "unexpected_json_sidecar_schema_not_bound_to_checked_sibling_set",
                label,
                path=str(entry),
                schema=schema,
            )
        add_non_evidence_input_path_alias_blockers(
            entry,
            blockers,
            reason_prefix="unexpected_json_sidecar",
            label=label,
            schema=schema if isinstance(schema, str) else None,
        )
        check_json_sidecar_overclaims(payload, label, blockers)


def check_unexpected_approved_bundle_json_sidecars(
    directory: Path,
    blockers: list[dict[str, Any]],
) -> None:
    try:
        entries = list(directory.iterdir())
    except FileNotFoundError:
        return
    except NotADirectoryError:
        add_blocker(blockers, "approved_bundle_path_not_directory", "approved_bundle", path=str(directory))
        return
    except OSError as exc:
        add_blocker(blockers, "approved_bundle_unreadable_for_sidecar_scan", "approved_bundle", detail=str(exc))
        return
    expected_source_log = directory.parent / "Obelisk.log"
    expected_approved_bundle_path = directory / "approved-runtime-principal-lifecycle-evidence.json"
    expected_run_id = directory.parent.name
    for entry in sorted(entries):
        if entry.name == "approved-runtime-principal-lifecycle-evidence.json":
            continue
        if entry.name in EXPECTED_APPROVED_BUNDLE_GENERATED_JSON_OUTPUTS:
            state = sibling_artifact_state(
                entry,
                f"approved_bundle_generated_json_sidecar.{entry.name}",
                blockers,
            )
            if (
                state.get("exists") is not True
                or state.get("approved_offline_workspace") is not True
                or state.get("protected") is True
                or state.get("symlink") is not None
            ):
                continue
            if state.get("size_bytes") == 0:
                continue
            label = f"approved_bundle_generated_json_sidecar.{entry.name}"
            try:
                payload = json.loads(entry.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                add_blocker(blockers, "approved_bundle_generated_sidecar_json_invalid", label, detail=str(exc))
                continue
            except OSError as exc:
                add_blocker(blockers, "approved_bundle_generated_sidecar_unreadable", label, detail=str(exc))
                continue
            if not isinstance(payload, dict):
                add_blocker(blockers, "approved_bundle_generated_sidecar_json_not_object", label)
                continue
            for blocker in approved_evidence_checker.generated_bundle_sidecar_blockers(
                payload,
                entry.name,
                label,
                expected_run_id=expected_run_id,
                expected_source_log=str(expected_source_log),
                expected_approved_bundle_path=str(expected_approved_bundle_path),
            ):
                extra = {
                    key: value
                    for key, value in blocker.items()
                    if key not in {"reason", "label"}
                }
                add_blocker(blockers, blocker["reason"], blocker["label"], **extra)
            continue
        if entry.suffix.casefold() != ".json":
            continue
        if not entry.is_file() and not entry.is_symlink():
            continue
        state = sibling_artifact_state(
            entry,
            f"unexpected_approved_bundle_json_sidecar.{entry.name}",
            blockers,
        )
        if (
            state.get("exists") is not True
            or state.get("approved_offline_workspace") is not True
            or state.get("protected") is True
            or state.get("symlink") is not None
        ):
            continue
        label = f"unexpected_approved_bundle_json_sidecar.{entry.name}"
        add_blocker(
            blockers,
            "unexpected_approved_bundle_json_sidecar_not_exact_relative_path",
            label,
            path=str(entry),
            expected=APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        )
        try:
            payload = json.loads(entry.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add_blocker(blockers, "unexpected_approved_bundle_json_sidecar_json_invalid", label, detail=str(exc))
            continue
        except OSError as exc:
            add_blocker(blockers, "unexpected_approved_bundle_json_sidecar_unreadable", label, detail=str(exc))
            continue
        if not isinstance(payload, dict):
            add_blocker(blockers, "unexpected_approved_bundle_json_sidecar_not_object", label)
            continue
        schema = payload.get("schema")
        reason = NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS.get(schema) if isinstance(schema, str) else None
        if reason is None and isinstance(schema, str):
            reason = approved_evidence_checker.non_approved_runtime_evidence_schema_alias_reason(schema)
        if reason is None and isinstance(schema, str) and PREACTIVATION_EXECUTOR_SCHEMA_RE.search(schema):
            reason = PREACTIVATION_EXECUTOR_SCHEMA_REASON
        if reason is not None:
            add_blocker(
                blockers,
                f"unexpected_approved_bundle_json_sidecar_{reason}",
                label,
                path=str(entry),
                schema=schema,
            )
        elif isinstance(schema, str):
            add_blocker(
                blockers,
                "unexpected_approved_bundle_json_sidecar_schema_not_bound_to_checked_sibling_set",
                label,
                path=str(entry),
                schema=schema,
            )
        add_non_evidence_input_path_alias_blockers(
            entry,
            blockers,
            reason_prefix="unexpected_approved_bundle_json_sidecar",
            label=label,
            schema=schema if isinstance(schema, str) else None,
        )
        check_json_sidecar_overclaims(payload, label, blockers)



def check_completed_receipt(
    artifacts: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> None:
    receipt = artifacts["operator_approval_receipt_json"]
    if Path(str(receipt.get("path", ""))).name.endswith(".template.json"):
        add_blocker(
            blockers,
            "operator_approval_receipt_json_template_path",
            "operator_approval_receipt_json",
            path=receipt.get("path"),
        )
    payload = load_sibling_json(receipt, "operator_approval_receipt_json", blockers)
    if payload is None:
        return
    add_non_evidence_schema_blocker(
        payload,
        blockers,
        reason_prefix="operator_approval_receipt_json",
        label="operator_approval_receipt_json",
    )
    check_json_sidecar_overclaims(payload, "operator_approval_receipt_json", blockers)
    if payload.get("status") == "generated_template":
        add_blocker(
            blockers,
            "operator_approval_receipt_generated_template_not_completed_receipt",
            "operator_approval_receipt_json",
        )
    if payload.get("status") != "completed_operator_receipt":
        add_blocker(
            blockers,
            "operator_approval_receipt_status_not_completed",
            "operator_approval_receipt_json",
            actual=payload.get("status"),
        )
    if payload.get("receipt_completed") is not True:
        add_blocker(blockers, "operator_approval_receipt_receipt_completed_not_true", "operator_approval_receipt_json")
    completion = payload.get("operator_completion")
    if not isinstance(completion, dict):
        add_blocker(
            blockers,
            "operator_approval_receipt_operator_completion_missing",
            "operator_approval_receipt_json",
        )
        completion = {}
    approval_source = completion.get("approval_source")
    if approval_source not in (
        approved_evidence_checker.APPROVAL_SOURCE_CURRENT_TURN,
        approved_evidence_checker.APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    ):
        add_blocker(
            blockers,
            "operator_approval_receipt_approval_source_mismatch",
            "operator_approval_receipt_json",
            actual=approval_source,
        )
    standing_receipt = approval_source == approved_evidence_checker.APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
    if standing_receipt:
        if payload.get("operator_current_turn_approval_recorded") is not False:
            add_blocker(
                blockers,
                "operator_approval_receipt_current_turn_approval_not_false_for_standing_authority",
                "operator_approval_receipt_json",
            )
        if payload.get("standing_launch_authority_recorded") is not True:
            add_blocker(
                blockers,
                "operator_approval_receipt_standing_launch_authority_not_recorded",
                "operator_approval_receipt_json",
            )
        if payload.get("standing_launch_authority_satisfies_operator_approval") is not True:
            add_blocker(
                blockers,
                "operator_approval_receipt_standing_launch_authority_not_bound",
                "operator_approval_receipt_json",
            )
    else:
        if payload.get("operator_current_turn_approval_recorded") is not True:
            add_blocker(
                blockers,
                "operator_approval_receipt_current_turn_approval_not_recorded",
                "operator_approval_receipt_json",
            )
        if payload.get("standing_launch_authority_recorded") is not False:
            add_blocker(
                blockers,
                "operator_approval_receipt_standing_launch_authority_not_false_for_current_turn",
                "operator_approval_receipt_json",
            )
        if payload.get("standing_launch_authority_satisfies_operator_approval") is not False:
            add_blocker(
                blockers,
                "operator_approval_receipt_standing_launch_authority_bound_for_current_turn",
                "operator_approval_receipt_json",
            )
    expected_attestation = (
        approved_evidence_checker.APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
        if standing_receipt
        else approved_evidence_checker.APPROVAL_ATTESTATION_CURRENT_TURN
    )
    if completion.get("attestation") != expected_attestation:
        add_blocker(
            blockers,
            "operator_approval_receipt_attestation_mismatch",
            "operator_approval_receipt_json",
            actual=completion.get("attestation"),
        )
    scope = payload.get("approval_scope")
    if not isinstance(scope, dict):
        add_blocker(blockers, "operator_approval_receipt_scope_missing", "operator_approval_receipt_json")
        scope = {}
    if standing_receipt:
        if scope.get("standing_approval") is not True:
            add_blocker(
                blockers,
                "operator_approval_receipt_scope_standing_approval_not_true",
                "operator_approval_receipt_json",
            )
    elif scope.get("standing_approval") is not False:
        add_blocker(
            blockers,
            "operator_approval_receipt_scope_standing_approval_not_false",
            "operator_approval_receipt_json",
        )
    request_payload = load_sibling_json(artifacts["window_request_json"], "window_request_json", blockers)
    bound_request = payload.get("bound_request_pack")
    if not isinstance(bound_request, dict):
        add_blocker(blockers, "operator_approval_receipt_bound_request_pack_missing", "operator_approval_receipt_json")
    elif isinstance(request_payload, dict):
        for key in (
            "run_id",
            "obelisk_commit",
            "target",
            "approved_window",
            "user_policy",
            "copied_evidence_dir",
            "copied_log_path",
            "window_manifest_path",
        ):
            expected = request_payload.get(key)
            if expected is not None and bound_request.get(key) != expected:
                add_blocker(
                    blockers,
                    f"operator_approval_receipt_bound_request_{key}_mismatch",
                    "operator_approval_receipt_json",
                    expected=expected,
                    actual=bound_request.get(key),
                )
    flags = payload.get("non_authorization_flags")
    if not isinstance(flags, dict):
        add_blocker(blockers, "operator_approval_receipt_non_authorization_flags_missing", "operator_approval_receipt_json")
    else:
        for key, value in sorted(flags.items()):
            if value is not False:
                add_blocker(
                    blockers,
                    f"operator_approval_receipt_{key}_not_false",
                    "operator_approval_receipt_json",
                    actual=value,
                )
    bound = payload.get("bound_artifacts")
    if not isinstance(bound, dict):
        add_blocker(blockers, "operator_approval_receipt_bound_artifacts_missing", "operator_approval_receipt_json")
        return
    for bound_key, artifact_key in (
        ("window_request_json", "window_request_json"),
        ("observer_window_env", "observer_window_env"),
        ("operator_approval_request_md", "operator_approval_request_md"),
    ):
        expected = expected_bound_artifact(artifacts[artifact_key])
        if expected is None:
            continue
        actual = bound.get(bound_key)
        if actual != expected:
            add_blocker(
                blockers,
                f"operator_approval_receipt_{bound_key}_artifact_mismatch",
                "operator_approval_receipt_json",
                expected=expected,
                actual=actual,
            )


def checked_sibling_set_state(
    copied_log: Path,
    window_manifest: Path,
    manifest_fields: dict[str, str],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    initial_blocker_count = len(blockers)
    expected_dir = copied_log.parent
    commit_binding = window_manifest_commit_binding_state(manifest_fields, blockers)
    artifacts: dict[str, dict[str, Any]] = {}
    for label, filename, path_key, sha_key in REQUIRED_SIBLING_ARTIFACTS:
        expected_path = expected_dir / filename
        if label == "copied_obelisk_log":
            expected_path = copied_log
        elif label == "window_manifest_env":
            expected_path = window_manifest
        state = sibling_artifact_state(expected_path, label, blockers)
        artifacts[label] = state
        if path_key is not None:
            check_manifest_declared_path(
                fields=manifest_fields,
                manifest_path=window_manifest,
                path_key=path_key,
                expected_path=expected_path,
                blockers=blockers,
            )
        if sha_key is not None:
            check_manifest_declared_sha(
                fields=manifest_fields,
                sha_key=sha_key,
                expected_sha256=state.get("sha256") if isinstance(state.get("sha256"), str) else None,
                blockers=blockers,
            )
    for label in ("window_request_json", "preflight_pre_json", "preflight_post_json"):
        check_known_non_evidence_json_sidecar(artifacts[label], label, blockers)
    ready_log_copy = approved_evidence_checker.ready_log_copy_report_state(
        expected_dir / approved_evidence_checker.READY_LOG_COPY_FILENAME,
        copied_log,
        label="ready_log_copy",
        reason_prefix="ready_log_copy",
    )
    blockers.extend(ready_log_copy["blocker_details"])
    if (
        ready_log_copy.get("exists")
        and ready_log_copy.get("ready_to_copy") is not True
    ):
        add_blocker(
            blockers,
            "ready_log_copy_not_ready_to_copy",
            "ready_log_copy",
            copy_readiness=str(ready_log_copy.get("copy_readiness", "not_provided")),
            roles_present=ready_log_copy.get("roles_present", []),
            missing_roles=ready_log_copy.get("missing_roles", []),
            reported_blockers=ready_log_copy.get("reported_blockers", []),
            source_log_not_ready_reason=ready_log_copy.get("source_log_not_ready_reason"),
            source_log_not_ready_blockers=ready_log_copy.get("source_log_not_ready_blockers", []),
            observer_only_no_role_window_detected=ready_log_copy.get("observer_only_no_role_window_detected") is True,
            player_present_but_no_lifecycle_roles=ready_log_copy.get("player_present_but_no_lifecycle_roles") is True,
            player_presence_context=ready_log_copy.get("player_presence_context", {}),
        )
    check_unexpected_non_evidence_json_sidecars(expected_dir, blockers)
    check_unexpected_approved_bundle_json_sidecars(expected_dir / "approved-bundle", blockers)
    check_completed_receipt(artifacts, blockers)
    replacement_sidecars = approved_evidence_checker.validate_runtime_replacement_sidecar_files(
        expected_dir,
        copied_log_path=copied_log,
        copied_log_sha256=str(artifacts["copied_obelisk_log"].get("sha256") or ""),
        run_id=manifest_fields.get("run_id"),
        blockers=blockers,
    )
    return {
        "ready": len(blockers) == initial_blocker_count and all(
            artifact.get("sha256") for artifact in artifacts.values()
        ),
        "directory": str(expected_dir),
        "artifacts": artifacts,
        "obelisk_commit_binding": commit_binding,
        "runtime_replacement_sidecars": replacement_sidecars,
        "ready_log_copy": ready_log_copy,
        "copy_readiness_context": copy_readiness_context(ready_log_copy),
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "non_claim": "checked sibling set only; does not authorize runtime work or public/player identity readiness",
    }


def require_checked_sibling_set(
    copied_log: Path,
    window_manifest: Path,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    manifest_fields = read_manifest_fields(window_manifest, blockers)
    state = checked_sibling_set_state(copied_log, window_manifest, manifest_fields, blockers)
    if blockers or not state["ready"]:
        reasons = ", ".join(blocker["reason"] for blocker in blockers)
        raise SystemExit(f"checked sibling set failed: {reasons}")
    return state


def classify_preflight_evidence_dir(evidence_dir: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    reject_symlink_component(evidence_dir, "--evidence-dir")
    status = protected_paths.protected_path_status(
        evidence_dir.expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    resolved = status.resolved
    if status.protected:
        add_blocker(blockers, "evidence_dir_under_protected_server_root", "--evidence-dir", path=str(resolved))
    if not status.approved_offline_workspace:
        add_blocker(blockers, "evidence_dir_not_approved_offline_workspace", "--evidence-dir", path=str(resolved))
    if not resolved.is_dir():
        add_blocker(blockers, "evidence_dir_missing", "--evidence-dir", path=str(resolved))
    if len(resolved.parts) < 2 or resolved.parts[-2] != EXPECTED_COPIED_LOG_PARENT:
        add_blocker(
            blockers,
            "evidence_dir_not_live_validation_logs_run",
            "--evidence-dir",
            expected=f"{EXPECTED_COPIED_LOG_PARENT}/<run-id>",
            path=str(resolved),
        )
    run_id = resolved.name
    if not RUN_ID_RE.fullmatch(run_id):
        add_blocker(blockers, "evidence_dir_run_id_invalid", "--evidence-dir", run_id=run_id)

    copied_log = file_state(resolved / "Obelisk.log", "copied_log", blockers)
    window_manifest = file_state(resolved / "window-manifest.env", "window_manifest", blockers)
    manifest_fields: dict[str, str] = {}
    window_manifest_path = Path(window_manifest["path"])
    window_manifest_readable = offline_readable_file_state(window_manifest)
    if window_manifest_readable:
        manifest_fields = read_manifest_fields(window_manifest_path, blockers)
    def sidecar_path(key: str, fallback: Path) -> Path:
        if window_manifest_readable:
            return path_from_manifest(manifest_fields, window_manifest_path, key, fallback, blockers)
        return fallback

    request_pack = file_state(
        sidecar_path(
            "request_pack_path",
            resolved / "window-request.json",
        ),
        "request_pack",
        blockers,
    )
    operator_request = operator_request_sidecar_state(request_pack, blockers)
    observer_env = file_state(
        sidecar_path(
            "observer_env_path",
            resolved / "observer-window.env",
        ),
        "observer_env",
        blockers,
    )
    preflight_pre = file_state(
        sidecar_path(
            "preflight_pre_path",
            resolved / "preflight-pre.json",
        ),
        "preflight_pre",
        blockers,
    )
    preflight_post = file_state(
        sidecar_path(
            "preflight_post_path",
            resolved / "preflight-post.json",
        ),
        "preflight_post",
        blockers,
    )
    operator_approval_receipt = file_state(
        sidecar_path(
            "operator_approval_receipt_path",
            resolved / "operator-approval-receipt.json",
        ),
        "operator_approval_receipt",
        blockers,
    )
    request_check = request_pack_check_state(request_pack, observer_env, operator_approval_receipt, blockers)
    window_check = window_manifest_check_state(window_manifest, blockers)

    bundle_manifest = resolved / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
    approved_bundle = file_state(bundle_manifest, "approved_runtime_manifest", blockers)
    approved_bundle_check = approved_runtime_manifest_check_state(
        approved_bundle,
        blockers,
        expected_run_id=run_id,
        expected_copied_log_path=resolved / "Obelisk.log",
    )
    copied_log_and_window_manifest_ready = (
        copied_log["exists"]
        and window_manifest["exists"]
        and copied_log["approved_offline_workspace"]
        and window_manifest["approved_offline_workspace"]
        and not copied_log["protected"]
        and not window_manifest["protected"]
    )
    copied_log_and_window_manifest_files_present = copied_log_and_window_manifest_ready
    if copied_log_and_window_manifest_ready:
        copied_log_and_window_manifest_ready = (
            window_manifest_readable
            and copied_log_manifest_binding_ready(
                copied_log,
                window_manifest_path,
                manifest_fields,
                blockers,
            )
        )
    sibling_set = checked_sibling_set_state(resolved / "Obelisk.log", resolved / "window-manifest.env", manifest_fields, blockers)
    obelisk_commit_binding = sibling_set.get("obelisk_commit_binding", {})
    obelisk_commit_binding_ready = obelisk_commit_binding.get("ready") is True
    operator_request_ready = offline_readable_file_state(operator_request)
    request_pack_ready = (
        request_pack["exists"]
        and observer_env["exists"]
        and operator_request_ready
        and operator_approval_receipt["exists"]
        and preflight_pre["exists"]
        and preflight_post["exists"]
        and request_check["ready"]
        and window_check["ready"]
    )
    bundle_inputs_ready = (
        copied_log_and_window_manifest_ready
        and obelisk_commit_binding_ready
        and request_pack_ready
        and sibling_set["ready"]
    )
    approved_runtime_evidence_accepted = bool(approved_bundle_check["ready"] and sibling_set["ready"])
    approved_bundle_check_for_checklist = {
        **approved_bundle_check,
        "ready": approved_runtime_evidence_accepted,
    }
    ready = bool(bundle_inputs_ready and not (approved_bundle["exists"] and not approved_runtime_evidence_accepted))
    approved_bundle_checklist = next_required_preflight_artifacts(
        copied_log,
        window_manifest,
        request_pack,
        observer_env,
        operator_request,
        operator_approval_receipt,
        preflight_pre,
        preflight_post,
        approved_bundle,
        approved_bundle_check_for_checklist,
    )
    copy_readiness = copy_readiness_context(sibling_set.get("ready_log_copy", {}))
    observer_no_role_diagnostics = observer_no_lifecycle_role_diagnostics_from_copy_context(
        copy_readiness,
    )
    session_end_missing_correlation_diagnostics = (
        approved_bundle_check.get("session_end_missing_correlation_diagnostics")
        if isinstance(approved_bundle_check.get("session_end_missing_correlation_diagnostics"), dict)
        else copy_readiness.get("session_end_missing_correlation_diagnostics")
    )
    if not isinstance(session_end_missing_correlation_diagnostics, dict):
        session_end_missing_correlation_diagnostics = None
    fastest_next_action = None if approved_runtime_evidence_accepted else (
        approved_evidence_checker.approved_runtime_evidence_missing_next_action(
            {
                key: approved_bundle_check.get(key)
                for key in STRICT_REJECTED_START_DIAGNOSTIC_KEYS
            },
            observer_no_role_diagnostics,
            session_end_missing_correlation_diagnostics,
        )
    )
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle-preflight.v1",
        "ready": ready,
        "ready_scope": "bundle_builder_inputs_only",
        "copied_log_and_window_manifest_files_present": bool(copied_log_and_window_manifest_files_present),
        "copied_log_and_window_manifest_ready": bool(copied_log_and_window_manifest_ready),
        "bundle_inputs_ready": bool(bundle_inputs_ready),
        "request_pack_ready": bool(request_pack_ready),
        "operator_request_ready": bool(operator_request_ready),
        "request_pack_is_runtime_evidence": False,
        "request_pack_counts_as_approved_runtime_evidence": False,
        "observer_env_counts_as_approved_runtime_evidence": False,
        "operator_request_counts_as_approved_runtime_evidence": False,
        "copied_log_metadata_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "copy_report_counts_as_approved_runtime_evidence": False,
        "window_manifest_counts_as_approved_runtime_evidence": False,
        "bundle_output_counts_as_approved_runtime_evidence": False,
        "approved_runtime_manifest_present": bool(approved_bundle["exists"]),
        "approved_runtime_evidence_present": approved_runtime_evidence_accepted,
        "approved_runtime_evidence_ready": approved_runtime_evidence_accepted,
        "current_route_blocker": (
            None
            if approved_runtime_evidence_accepted
            else approved_evidence_checker.APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER
        ),
        "partial_start_end_present": approved_bundle_check.get("partial_start_end_present") is True,
        "missing_strict_rejected_start": approved_bundle_check.get("missing_strict_rejected_start") is True,
        "missing_lifecycle_event_roles": approved_bundle_check.get("missing_lifecycle_event_roles", []),
        "session_end_missing_correlation_diagnostics": (
            session_end_missing_correlation_diagnostics
        ),
        "strict_lifecycle_triplet_selection": approved_bundle_check.get(
            "strict_lifecycle_triplet_selection",
            {},
        ),
        "strict_rejected_start_expected_shape": approved_bundle_check.get(
            "strict_rejected_start_expected_shape",
            approved_evidence_checker.STRICT_REJECTED_START_EXPECTED_SHAPE,
        ),
        "strict_rejected_start_observed_shape": approved_bundle_check.get(
            "strict_rejected_start_observed_shape",
        ),
        "preflight_counts_as_approved_runtime_evidence": False,
        "completed_receipt_counts_as_approved_runtime_evidence": False,
        "dry_run_success_counts_as_approved_runtime_evidence": False,
        "historical_target_names_authorize_runtime": False,
        "marker_env_readiness_counts_as_approved_runtime_evidence": False,
        "player_notice_counts_as_approved_runtime_evidence": False,
        "public_reachability_counts_as_approved_runtime_evidence": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "route_ready": False,
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "next_blocker": (
            "identity_public_contract_gate_missing"
            if approved_runtime_evidence_accepted
            else "approved_runtime_evidence_not_accepted"
            if approved_bundle["exists"]
            else "window_manifest_obelisk_commit_must_match_current_head"
            if copied_log_and_window_manifest_files_present and not obelisk_commit_binding_ready
            else
            "run_offline_evidence_bundle_builder"
            if bundle_inputs_ready and not approved_bundle["exists"]
            else "checked_post_window_replay_sidecars_required"
            if copied_log_and_window_manifest_ready
            else "copied_log_and_window_manifest_binding_required"
            if copied_log_and_window_manifest_files_present
            else "copied_log_and_window_manifest_required"
        ),
        "run_id": run_id,
        "evidence_dir": str(resolved),
        "fastest_next_action": fastest_next_action,
        "approved_bundle_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "approved_bundle_path": str(bundle_manifest),
        "approved_bundle_checklist": approved_bundle_checklist,
        "inputs": {
            "copied_log": copied_log,
            "ready_log_copy": sibling_set.get("ready_log_copy"),
            "window_manifest": window_manifest,
            "window_manifest_check": window_check,
            "request_pack": request_pack,
            "observer_env": observer_env,
            "operator_request": operator_request,
            "operator_approval_receipt": operator_approval_receipt,
            "request_pack_check": request_check,
            "preflight_pre": preflight_pre,
            "preflight_post": preflight_post,
            "checked_sibling_set": sibling_set,
            "obelisk_commit_binding": obelisk_commit_binding,
            "runtime_replacement_sidecars": sibling_set.get("runtime_replacement_sidecars"),
            "approved_runtime_manifest": approved_bundle,
            "approved_runtime_manifest_check": approved_bundle_check,
        },
        "next_required_artifacts": approved_bundle_checklist,
        "copy_readiness_context": copy_readiness,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "preflight-only filesystem classification; does not analyze logs, build approved evidence, authorize runtime capture, or promote player identity",
            "request-pack readiness is preparation only and does not satisfy approved runtime evidence",
            "bundle_inputs_ready requires the copied log, checked window manifest, completed receipt, preflight sidecars, and checked post-window replay request pack; it does not mean approved runtime evidence already exists",
        ],
    }


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return payload


def require_window_matches_summary(window: dict[str, Any], summary: dict[str, Any], copied_log: Path) -> None:
    if window.get("schema") != "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1":
        raise SystemExit("window manifest check schema mismatch")
    if window.get("ready") is not True or window.get("operational_window_manifest_ready") is not True:
        raise SystemExit("window manifest check is not ready")
    if window.get("post_window_replay") is not True:
        raise SystemExit("window manifest check did not validate post-window replay")
    if window.get("blockers") not in (None, []) or window.get("remaining_blockers") not in (None, []):
        raise SystemExit("window manifest check reported blockers despite ready status")
    copied = window.get("copied_log")
    if not isinstance(copied, dict):
        raise SystemExit("window manifest check missing copied_log")
    copied_path_text = copied.get("path")
    if not isinstance(copied_path_text, str) or not copied_path_text:
        raise SystemExit("window manifest check copied_log.path missing")
    window_path = Path(copied_path_text).expanduser().resolve()
    requested_path = copied_log.expanduser().resolve()
    if window_path != requested_path:
        raise SystemExit("window manifest copied_log.path does not match --copied-log")
    evidence = summary.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or not sources or not isinstance(sources[0], dict):
        raise SystemExit("runtime observer summary missing evidence.sources[0]")
    source = sources[0]
    source_path_text = source.get("path")
    if not isinstance(source_path_text, str) or not source_path_text:
        raise SystemExit("runtime observer summary source path missing")
    source_path = Path(source_path_text).expanduser().resolve()
    if source_path != requested_path:
        raise SystemExit("runtime observer summary source path does not match --copied-log")
    if copied.get("sha256") != source.get("sha256"):
        raise SystemExit("window manifest copied_log.sha256 does not match runtime observer summary")
    evidence_commit = evidence.get("obelisk_commit") if isinstance(evidence, dict) else None
    if not is_reviewed_obelisk_commit(evidence_commit):
        raise SystemExit("runtime observer summary obelisk_commit must be a reviewed 40-character lowercase Git SHA")
    if not is_reviewed_obelisk_commit(window.get("obelisk_commit")):
        raise SystemExit("window manifest obelisk_commit must be a reviewed 40-character lowercase Git SHA")
    if window.get("obelisk_commit") != evidence_commit:
        raise SystemExit("window manifest obelisk_commit does not match runtime observer summary")
    current_commit = current_obelisk_commit()
    if current_commit is None:
        raise SystemExit("current Obelisk repo HEAD could not be resolved for runtime evidence review")
    if evidence_commit != current_commit:
        raise SystemExit("runtime observer summary obelisk_commit does not match current repo HEAD")
    receipt = window.get("operator_approval_receipt")
    if not isinstance(receipt, dict) or receipt.get("verified") is not True:
        raise SystemExit("window manifest check missing verified operator approval receipt")
    modules = summary.get("modules")
    principal = modules.get("player_principal_lifecycle") if isinstance(modules, dict) else None
    functions = principal.get("functions") if isinstance(principal, dict) else None
    gate = functions.get("observer_gate") if isinstance(functions, dict) else None
    details = gate.get("details") if isinstance(gate, dict) else None
    gate_limits = details.get("limit") if isinstance(details, dict) else None
    if gate_limits != [10]:
        raise SystemExit("runtime observer summary gate limit does not match exact first-window log budget")


def player_principal_lifecycle_module(summary: dict[str, Any]) -> dict[str, Any]:
    modules = summary.get("modules")
    module = modules.get("player_principal_lifecycle") if isinstance(modules, dict) else None
    if not isinstance(module, dict):
        raise SystemExit("runtime observer summary missing player_principal_lifecycle module")
    return module


def observed_lifecycle_event_triplet(summary: dict[str, Any]) -> list[dict[str, Any]]:
    module = player_principal_lifecycle_module(summary)
    cases = module.get("observed_event_cases")
    if not isinstance(cases, list):
        return []
    selection = approved_evidence_checker.strict_lifecycle_triplet_selection(cases)
    selected_indices = set(selection.get("selected_indices", []))
    triplet: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        if isinstance(case, dict):
            if selected_indices and index not in selected_indices:
                continue
            triplet.append({key: case.get(key) for key in OBSERVED_TRIPLET_CASE_KEYS if key in case})
    return triplet


def require_check_join_rejected_start_triplet(summary: dict[str, Any]) -> None:
    module = player_principal_lifecycle_module(summary)
    if approved_evidence_checker.diagnostic_material_present(module):
        raise SystemExit("runtime observer summary diagnostic candidates are not approved runtime evidence")
    selection = approved_evidence_checker.strict_lifecycle_triplet_selection(
        module.get("observed_event_cases")
    )
    if not approved_evidence_checker.strict_lifecycle_triplet_is_exact(selection):
        raise SystemExit(
            "runtime observer summary must contain exactly one approved "
            "CheckJoinInProgress rejected-start lifecycle triplet"
        )
    alternative = approved_evidence_checker.matching_observed_event_alternative(
        module.get("observed_event_cases")
    )
    if (
        not isinstance(alternative, dict)
        or alternative.get("id") != APPROVED_REJECTED_START_TRIPLET_ALTERNATIVE
    ):
        raise SystemExit(
            "runtime observer summary must match approved CheckJoinInProgress "
            "rejected-start lifecycle triplet"
        )
    if module.get("complete_lifecycle_event_triplet_candidate_present") is not True:
        raise SystemExit("runtime observer summary missing complete lifecycle triplet candidate")
    if module.get("complete_accepted_lifecycle_role_triplet_present") is not True:
        raise SystemExit("runtime observer summary missing complete accepted lifecycle role triplet")


def require_runtime_lifecycle_correlation_proof(
    summary: dict[str, Any],
    window: dict[str, Any],
    copied_log: Path,
) -> dict[str, Any]:
    actual_capture = window.get("actual_capture")
    if not isinstance(actual_capture, dict):
        raise SystemExit("window manifest check missing actual_capture for lifecycle correlation proof")
    timestamps: dict[str, Any] = {}
    for key in ("start_utc", "end_utc"):
        value = actual_capture.get(key)
        parsed = approved_evidence_checker.parse_utc_timestamp(value) if isinstance(value, str) else None
        if parsed is None:
            raise SystemExit(f"window manifest check actual_capture.{key} invalid for lifecycle correlation proof")
        timestamps[key] = parsed

    blockers: list[dict[str, Any]] = []
    try:
        copied_lines = copied_log.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SystemExit(f"copied log unreadable for lifecycle correlation proof: {exc}") from exc
    copied_log_proof = approved_evidence_checker.validate_copied_log_lifecycle_events_inside_capture_window(
        copied_lines,
        actual_capture=timestamps,
        blockers=blockers,
    )
    proof = approved_evidence_checker.validate_lifecycle_correlation_proof(
        summary=summary,
        window=window,
        copied_log_proof=copied_log_proof,
        blockers=blockers,
    )
    if blockers or proof.get("accepted") is not True:
        reasons = ", ".join(blocker["reason"] for blocker in blockers[:8])
        if not reasons:
            reasons = "runtime_lifecycle_correlation_proof_missing"
        raise SystemExit(f"runtime lifecycle correlation proof failed: {reasons}")
    return proof


def require_runtime_log_posture(summary: dict[str, Any], window: dict[str, Any]) -> None:
    runtime = summary.get("runtime")
    if not isinstance(runtime, dict):
        raise SystemExit("runtime observer summary missing runtime posture")
    for key, expected in EXPECTED_RUNTIME_LOG_POSTURE.items():
        if runtime.get(key) != expected:
            raise SystemExit(
                f"runtime observer summary {key} does not match approved copied-log posture"
            )

    posture = window.get("posture")
    if not isinstance(posture, dict):
        raise SystemExit("window manifest check missing posture")
    posture_pairs = {
        "plugins_disabled": ("plugins_disabled", True),
        "scanner_disabled": ("reflection_scanner_disabled", True),
    }
    for window_key, (runtime_key, expected) in posture_pairs.items():
        if posture.get(window_key) != expected or runtime.get(runtime_key) != expected:
            raise SystemExit(
                f"window manifest posture {window_key} does not match copied runtime log posture"
            )


def require_window_check_matches_sibling_set(window: dict[str, Any], sibling_set: dict[str, Any]) -> None:
    artifacts = sibling_set.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SystemExit("checked sibling set missing artifacts")
    preflight = window.get("preflight")
    if not isinstance(preflight, dict):
        preflight = {}
    comparisons = (
        ("copied_obelisk_log", window.get("copied_log")),
        ("window_manifest_env", window.get("manifest")),
        ("window_request_json", window.get("request_pack")),
        ("observer_window_env", window.get("observer_env")),
        ("operator_approval_receipt_json", window.get("operator_approval_receipt")),
        ("preflight_pre_json", preflight.get("pre")),
        ("preflight_post_json", preflight.get("post")),
    )
    for artifact_key, checked in comparisons:
        expected = artifacts.get(artifact_key)
        if not isinstance(expected, dict) or not isinstance(checked, dict):
            raise SystemExit(f"window manifest check missing checked sibling artifact {artifact_key}")
        expected_path = expected.get("path")
        checked_path = checked.get("path")
        if not isinstance(expected_path, str) or not isinstance(checked_path, str):
            raise SystemExit(f"window manifest check sibling artifact {artifact_key} path missing")
        if Path(checked_path).expanduser().resolve() != Path(expected_path).expanduser().resolve():
            raise SystemExit(f"window manifest check sibling artifact {artifact_key} path mismatch")
        if checked.get("sha256") != expected.get("sha256"):
            raise SystemExit(f"window manifest check sibling artifact {artifact_key} sha256 mismatch")


def require_bundle_report_non_authorizing(report: dict[str, Any]) -> None:
    if report.get("next_blocker") != approved_evidence_checker.NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE:
        raise SystemExit("evidence bundle report did not route to the identity public contract gate")
    if report.get("current_route_blocker") is not None:
        raise SystemExit("evidence bundle report overclaims a current route blocker after accepted evidence")
    if report.get("remaining_blockers") != []:
        raise SystemExit("evidence bundle report carried runtime evidence blockers despite accepted evidence")
    if report.get("next_required_artifact") is not None:
        raise SystemExit("evidence bundle report overclaims a required artifact after accepted evidence")
    if report.get("missing_required_artifact") is not None:
        raise SystemExit("evidence bundle report overclaims a missing artifact after accepted evidence")
    if report.get("required_artifact_status") != "accepted":
        raise SystemExit("evidence bundle report did not mark the required artifact accepted")
    for key in (
        "server_operations_authorized",
        "runtime_work_authorized",
        "promotion_ready",
        "public_header_allowed",
        "public_sdk_ready",
        "public_abi_ready",
        "v1_completion_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "route_ready",
        "request_pack_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "copy_report_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "bundle_report_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
    ):
        if report.get(key) is not False:
            raise SystemExit(f"evidence bundle report overclaims {key}")
    for key in ("public_capability_bits_now", "public_callback_abi_now"):
        if report.get(key) != []:
            raise SystemExit(f"evidence bundle report overclaims {key}")
    negative = report.get("negative_readiness_checks")
    if not isinstance(negative, dict) or any(value is not False for value in negative.values()):
        raise SystemExit("evidence bundle report overclaims negative readiness checks")
    sibling_set = report.get("input_sibling_set")
    if isinstance(sibling_set, dict):
        for key in (
            "server_operations_authorized",
            "runtime_work_authorized",
            "public_sdk_ready",
            "runtime_ready",
            "promotion_ready",
            "sdk_accounting_counts_as_completed_surface",
            "p0_accounting_counts_as_promoted_surface",
        ):
            if sibling_set.get(key) is not False:
                raise SystemExit(f"checked sibling set overclaims {key}")


def main() -> int:
    args = parse_args()
    if args.preflight_only:
        if args.evidence_dir is None:
            raise SystemExit("--evidence-dir is required with --preflight-only")
        report = classify_preflight_evidence_dir(args.evidence_dir)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ready"] else 1
    apply_evidence_dir_build_defaults(args)
    for name in ("copied_log", "window_manifest", "output_dir", "obelisk_commit", "reviewed_by", "review_note"):
        if getattr(args, name) is None:
            raise SystemExit(
                f"--{name.replace('_', '-')} is required unless --preflight-only "
                "or --evidence-dir build mode is used"
            )
    if not is_reviewed_obelisk_commit(args.obelisk_commit):
        raise SystemExit("--obelisk-commit must be a reviewed 40-character lowercase Git SHA")
    copied_log = require_approved_copied_log(args.copied_log)
    window_manifest = require_exact_sibling_window_manifest(args.window_manifest, copied_log)
    sibling_set = require_checked_sibling_set(copied_log, window_manifest)
    command_commit = sibling_set.get("obelisk_commit_binding", {}).get("window_manifest_obelisk_commit")
    if args.obelisk_commit != command_commit:
        raise SystemExit(
            "--obelisk-commit must match window-manifest.env obelisk_commit and current repo HEAD: "
            f"expected {command_commit}, got {args.obelisk_commit}"
        )
    output_dir = args.output_dir.expanduser()
    reject_symlink_component(output_dir, "--output-dir")
    protected_paths.reject_server_root_write_without_opt_in(output_dir, "--output-dir", protected_root=SERVER_ROOT)
    output_dir = reject_protected_output_path(output_dir, "--output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "runtime-observer-summary.json"
    window_check_path = output_dir / "player-principal-lifecycle-window-manifest.check.json"
    manifest_path = output_dir / "approved-runtime-principal-lifecycle-evidence.json"
    check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.check.json"
    promote_check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.promote-check.json"
    public_check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.public-readiness-check.json"
    runtime_check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.runtime-readiness-check.json"
    gate_path = output_dir / "approved-runtime-principal-lifecycle-evidence.consume-gate.json"
    report_path = output_dir / "evidence-bundle-report.json"

    require_success(
        run_window_manifest_replay_check(
            window_manifest,
            stdout_path=window_check_path,
        ),
        "check player principal lifecycle window manifest",
    )
    require_success(
        run_command(
            [
                sys.executable,
                str(ANALYZER),
                "--obelisk-commit",
                args.obelisk_commit,
                "--fail-on-quality-blockers",
                str(copied_log),
            ],
            stdout_path=summary_path,
        ),
        "analyze_runtime_observer_log",
    )
    window_check = load_json(window_check_path)
    summary = load_json(summary_path)
    require_window_matches_summary(window_check, summary, copied_log)
    require_runtime_log_posture(summary, window_check)
    require_window_check_matches_sibling_set(window_check, sibling_set)
    require_check_join_rejected_start_triplet(summary)
    lifecycle_correlation_proof = require_runtime_lifecycle_correlation_proof(
        summary,
        window_check,
        copied_log,
    )
    require_success(
        run_command(
            [
                sys.executable,
                str(BUILDER),
                "--source-summary",
                str(summary_path),
                "--window-manifest-check",
                str(window_check_path),
                "--output",
                str(manifest_path),
                "--reviewed-by",
                args.reviewed_by,
                "--review-note",
                args.review_note,
            ]
        ),
        "build approved runtime principal lifecycle manifest",
    )
    require_success(
        run_command(
            [
                sys.executable,
                str(CHECKER),
                "--json",
                str(manifest_path),
            ],
            stdout_path=check_path,
        ),
        "check approved runtime principal lifecycle evidence",
    )
    negative_checks = (
        ("promote", "--promote", promote_check_path),
        ("public-readiness", "--public-readiness", public_check_path),
        ("runtime-readiness", "--runtime-readiness", runtime_check_path),
    )
    for label, flag, path in negative_checks:
        require_expected_failure(
            run_command(
                [
                    sys.executable,
                    str(CHECKER),
                    "--json",
                    flag,
                    str(manifest_path),
                ],
                stdout_path=path,
            ),
            f"check approved runtime principal lifecycle evidence {label}",
        )
    require_success(
        run_command(
            [
                sys.executable,
                str(OFFLINE_GATE),
                "--root",
                str(output_dir),
                "--mode",
                "consume",
                "--json",
                "--manifest",
                str(manifest_path),
            ],
            stdout_path=gate_path,
        ),
        "validate offline artifact consume gate",
    )

    check = load_json(check_path)
    promote_check = load_json(promote_check_path)
    public_check = load_json(public_check_path)
    runtime_check = load_json(runtime_check_path)
    gate = load_json(gate_path)
    require_consume_only_check_report(check, "consume approved runtime principal lifecycle evidence check")
    require_negative_readiness_report(
        promote_check,
        "promote approved runtime principal lifecycle evidence check",
        "promote_blocked_until_identity_public_contract_gate",
    )
    require_negative_readiness_report(
        public_check,
        "public-readiness approved runtime principal lifecycle evidence check",
        "public_readiness_blocked_until_identity_public_contract_gate",
    )
    require_negative_readiness_report(
        runtime_check,
        "runtime-readiness approved runtime principal lifecycle evidence check",
        "runtime_readiness_blocked_until_identity_public_contract_gate",
    )
    report = {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
        "status": "accepted",
        "ready_scope": "runtime_evidence_only",
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "route_ready": False,
        "remaining_blockers": [],
        "next_blocker": approved_evidence_checker.NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE,
        "current_route_blocker": None,
        "next_required_artifact": None,
        "missing_required_artifact": None,
        "required_artifact_status": "accepted",
        "request_pack_counts_as_approved_runtime_evidence": False,
        "observer_env_counts_as_approved_runtime_evidence": False,
        "operator_request_counts_as_approved_runtime_evidence": False,
        "copied_log_metadata_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "copy_report_counts_as_approved_runtime_evidence": False,
        "preflight_counts_as_approved_runtime_evidence": False,
        "window_manifest_counts_as_approved_runtime_evidence": False,
        "completed_receipt_counts_as_approved_runtime_evidence": False,
        "bundle_report_counts_as_approved_runtime_evidence": False,
        "dry_run_success_counts_as_approved_runtime_evidence": False,
        "historical_target_names_authorize_runtime": False,
        "marker_env_readiness_counts_as_approved_runtime_evidence": False,
        "player_notice_counts_as_approved_runtime_evidence": False,
        "public_reachability_counts_as_approved_runtime_evidence": False,
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "source_log": str(copied_log),
        "approved_bundle_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "approved_bundle_path": str(manifest_path),
        "input_sibling_set": sibling_set,
        "copy_readiness_context": sibling_set.get("copy_readiness_context"),
        "operational_window": {
            "check": str(window_check_path),
            "copied_log_sha256": window_check.get("copied_log", {}).get("sha256"),
            "manifest_ready": window_check.get("operational_window_manifest_ready"),
            "obelisk_commit": window_check.get("obelisk_commit"),
            "run_id": window_check.get("run_id"),
            "target": window_check.get("target"),
            "log_budget": window_check.get("log_budget"),
            "non_claims": window_check.get("non_claims"),
        },
        "outputs": {
            "summary": artifact(summary_path),
            "window_manifest_check": artifact(window_check_path),
            "manifest": artifact(manifest_path),
            "check": artifact(check_path),
            "promote_check": artifact(promote_check_path),
            "public_readiness_check": artifact(public_check_path),
            "runtime_readiness_check": artifact(runtime_check_path),
            "consume_gate": artifact(gate_path),
        },
        "summary_modules": sorted(summary.get("modules", {}).keys()),
        "observed_runtime_cases": check.get("observed_runtime_cases", []),
        "observed_lifecycle_event_triplet_alternative": APPROVED_REJECTED_START_TRIPLET_ALTERNATIVE,
        "observed_lifecycle_event_triplet": observed_lifecycle_event_triplet(summary),
        "strict_lifecycle_triplet_selection": check.get("strict_lifecycle_triplet_selection", {}),
        "lifecycle_correlation_proof": lifecycle_correlation_proof,
        "strict_lifecycle_triplet_non_counting_context_event_count": check.get(
            "strict_lifecycle_triplet_non_counting_context_event_count",
            0,
        ),
        "strict_lifecycle_triplet_non_counting_context_roles": check.get(
            "strict_lifecycle_triplet_non_counting_context_roles",
            [],
        ),
        "negative_readiness_checks": {
            "promote_ready": promote_check.get("ready"),
            "public_readiness_ready": public_check.get("ready"),
            "runtime_readiness_ready": runtime_check.get("ready"),
        },
        "consume_gate_status": gate.get("status"),
        "non_claim": (
            "offline consume bundle only; does not authorize server operations, Discord, "
            "GitHub publication, public identity, permissions, commands, runtime readiness, "
            "or v1 SDK completion"
        ),
    }
    require_bundle_report_non_authorizing(report)
    report["bundle_report_identity"] = report_identity(report)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
