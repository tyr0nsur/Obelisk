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


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
BUILDER = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
WINDOW_MANIFEST_CHECKER = SCRIPT_DIR / "check_player_principal_lifecycle_window_manifest.py"
WINDOW_REQUEST_CHECKER = SCRIPT_DIR / "check_player_principal_lifecycle_window_request.py"
OFFLINE_GATE = SCRIPT_DIR / "validate_offline_artifact_gate.py"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
EXPECTED_COPIED_LOG_PARENT = "live-validation-logs"
EXPECTED_RUNTIME_LOG_POSTURE = {
    "loaded_native_ld_preload": True,
    "process_event_candidate_count": 1,
    "process_event_hook_installed": True,
    "process_event_hook_patch_size": 18,
    "reflection_scanner_disabled": True,
    "plugins_disabled": True,
}
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$")


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
    parser.add_argument("--evidence-dir", type=Path, help="live-validation-logs/<run-id> directory to classify.")
    parser.add_argument("--copied-log", type=Path, help="Copied/sanitized Obelisk log.")
    parser.add_argument("--window-manifest", type=Path, help="Approved operational window manifest.")
    parser.add_argument("--output-dir", type=Path, help="Bundle output directory.")
    parser.add_argument("--obelisk-commit", help="Reviewed Obelisk commit recorded in evidence.")
    parser.add_argument("--reviewed-by", help="Reviewer token/name for the approved manifest.")
    parser.add_argument("--review-note", help="Short consume-only review note.")
    return parser.parse_args()


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


def require_false_readiness_flags(payload: dict[str, Any], label: str) -> None:
    for key in (
        "promotion_ready",
        "public_header_allowed",
        "public_sdk_ready",
        "public_abi_ready",
        "v1_completion_ready",
        "runtime_ready",
    ):
        if payload.get(key, False) is not False:
            raise SystemExit(f"{label} overclaims {key}")
    for key in ("public_capability_bits_now", "public_callback_abi_now"):
        if payload.get(key, []) != []:
            raise SystemExit(f"{label} overclaims {key}")
    require_no_truthy_readiness_alias_keys(payload, label)


def require_no_truthy_readiness_alias_keys(value: Any, label: str, trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                child not in (False, None, [], {})
                and approved_evidence_checker.contains_unnegated_positive_capability_claim(str(key))
            ):
                raise SystemExit(f"{label} overclaims readiness alias {child_trail}")
            require_no_truthy_readiness_alias_keys(child, label, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            require_no_truthy_readiness_alias_keys(child, label, f"{trail}[{index}]")


def require_consume_only_check_report(payload: dict[str, Any], label: str) -> None:
    if payload.get("ready") is not True:
        raise SystemExit(f"{label} did not accept consume-only runtime evidence")
    if payload.get("approved_runtime_evidence_present") is not True:
        raise SystemExit(f"{label} did not preserve approved runtime evidence presence")
    if payload.get("runtime_evidence_ready") is not True:
        raise SystemExit(f"{label} did not preserve runtime evidence readiness")
    require_false_readiness_flags(payload, label)
    if payload.get("next_blocker") != "identity_public_contract_gate_missing":
        raise SystemExit(f"{label} did not route to the identity public contract gate")


def require_negative_readiness_report(payload: dict[str, Any], label: str, expected_blocker: str) -> None:
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
        "exit_code": None,
        "schema": None,
        "stderr": "",
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
    exit_code, payload, stderr = run_json_check(
        [
            sys.executable,
            str(WINDOW_MANIFEST_CHECKER),
            "--json",
            "--post-window-replay",
            str(window_manifest["path"]),
        ]
    )
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
        state["checker_ready"] = payload.get("ready") is True
        state["ready"] = (
            exit_code == 0
            and payload.get("ready") is True
            and payload.get("approved_runtime_evidence_present") is True
            and payload.get("runtime_evidence_ready") is True
            and payload.get("promotion_ready") is False
            and payload.get("public_header_allowed", False) is False
            and payload.get("public_sdk_ready") is False
            and payload.get("public_abi_ready", False) is False
            and payload.get("v1_completion_ready", False) is False
            and payload.get("runtime_ready") is False
            and payload.get("public_capability_bits_now", []) == []
            and payload.get("public_callback_abi_now", []) == []
        )
        state["blockers"] = payload.get("blockers", [])
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
        add_blocker(
            blockers,
            "approved_runtime_manifest_check_failed",
            "approved_runtime_manifest",
            exit_code=exit_code,
            approved_runtime_check_blockers=state.get("blockers", []),
        )
    return state


def next_required_preflight_artifacts(
    copied_log: dict[str, Any],
    window_manifest: dict[str, Any],
    request_pack: dict[str, Any],
    observer_env: dict[str, Any],
    preflight_pre: dict[str, Any],
    preflight_post: dict[str, Any],
    approved_bundle: dict[str, Any],
    approved_bundle_check: dict[str, Any],
) -> list[dict[str, Any]]:
    operator_request = dict(request_pack)
    request_path = request_pack.get("path")
    if isinstance(request_path, str):
        operator_request["path"] = str(Path(request_path).with_name("operator-approval-request.md"))
    operator_request["exists"] = (
        isinstance(operator_request.get("path"), str) and Path(operator_request["path"]).is_file()
    )
    required = [
        (
            "copied_obelisk_log",
            copied_log,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
        ),
        (
            "checked_window_manifest_env",
            window_manifest,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
        ),
        (
            "window_request_json",
            request_pack,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
        ),
        (
            "observer_window_env",
            observer_env,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
        ),
        (
            "operator_approval_request_md",
            operator_request,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
        ),
        (
            "operator_approval_receipt",
            approved_bundle.get("operator_approval_receipt", {}),
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
        ),
        (
            "preflight_pre_json",
            preflight_pre,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
        ),
        (
            "preflight_post_json",
            preflight_post,
            "offline_runtime_principal_lifecycle_bundle_builder_input",
            False,
        ),
        (
            "approved_runtime_principal_lifecycle_evidence_manifest",
            approved_bundle,
            "approved_runtime_evidence_missing",
            bool(approved_bundle_check.get("ready")),
        ),
    ]
    artifacts: list[dict[str, Any]] = []
    for artifact, state, required_for, satisfies_approved_runtime_evidence in required:
        artifacts.append(
            {
                "artifact": artifact,
                "path": state.get("path"),
                "present": state.get("exists") is True,
                "required_for": required_for,
                "satisfies_approved_runtime_evidence": satisfies_approved_runtime_evidence,
            }
        )
    return artifacts


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
    request_pack_ready = (
        request_pack["exists"]
        and observer_env["exists"]
        and operator_approval_receipt["exists"]
        and preflight_pre["exists"]
        and preflight_post["exists"]
        and request_check["ready"]
        and window_check["ready"]
    )
    bundle_inputs_ready = copied_log_and_window_manifest_ready and request_pack_ready
    approved_bundle["operator_approval_receipt"] = operator_approval_receipt
    ready = bool(bundle_inputs_ready and not (approved_bundle["exists"] and not approved_bundle_check["ready"]))
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle-preflight.v1",
        "ready": ready,
        "ready_scope": "bundle_builder_inputs_only",
        "copied_log_and_window_manifest_ready": bool(copied_log_and_window_manifest_ready),
        "bundle_inputs_ready": bool(bundle_inputs_ready),
        "request_pack_ready": bool(request_pack_ready),
        "request_pack_is_runtime_evidence": False,
        "approved_runtime_manifest_present": bool(approved_bundle["exists"]),
        "approved_runtime_evidence_present": bool(approved_bundle_check["ready"]),
        "approved_runtime_evidence_ready": bool(approved_bundle_check["ready"]),
        "preflight_counts_as_approved_runtime_evidence": False,
        "completed_receipt_counts_as_approved_runtime_evidence": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "next_blocker": (
            "identity_public_contract_gate_missing"
            if approved_bundle_check["ready"]
            else "approved_runtime_evidence_not_accepted"
            if approved_bundle["exists"]
            else
            "run_offline_evidence_bundle_builder"
            if bundle_inputs_ready and not approved_bundle["exists"]
            else "checked_post_window_replay_sidecars_required"
            if copied_log_and_window_manifest_ready
            else "copied_log_and_window_manifest_required"
        ),
        "run_id": run_id,
        "evidence_dir": str(resolved),
        "inputs": {
            "copied_log": copied_log,
            "window_manifest": window_manifest,
            "window_manifest_check": window_check,
            "request_pack": request_pack,
            "observer_env": observer_env,
            "operator_approval_receipt": operator_approval_receipt,
            "request_pack_check": request_check,
            "preflight_pre": preflight_pre,
            "preflight_post": preflight_post,
            "approved_runtime_manifest": approved_bundle,
            "approved_runtime_manifest_check": approved_bundle_check,
        },
        "next_required_artifacts": next_required_preflight_artifacts(
            copied_log,
            window_manifest,
            request_pack,
            observer_env,
            preflight_pre,
            preflight_post,
            approved_bundle,
            approved_bundle_check,
        ),
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
    window_path = Path(str(copied.get("path", ""))).expanduser().resolve()
    requested_path = copied_log.expanduser().resolve()
    if window_path != requested_path:
        raise SystemExit("window manifest copied_log.path does not match --copied-log")
    evidence = summary.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or not sources or not isinstance(sources[0], dict):
        raise SystemExit("runtime observer summary missing evidence.sources[0]")
    source = sources[0]
    source_path = Path(str(source.get("path", ""))).expanduser().resolve()
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


def main() -> int:
    args = parse_args()
    if args.preflight_only:
        if args.evidence_dir is None:
            raise SystemExit("--evidence-dir is required with --preflight-only")
        report = classify_preflight_evidence_dir(args.evidence_dir)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ready"] else 1
    for name in ("copied_log", "window_manifest", "output_dir", "obelisk_commit", "reviewed_by", "review_note"):
        if getattr(args, name) is None:
            raise SystemExit(f"--{name.replace('_', '-')} is required unless --preflight-only is used")
    if not is_reviewed_obelisk_commit(args.obelisk_commit):
        raise SystemExit("--obelisk-commit must be a reviewed 40-character lowercase Git SHA")
    copied_log = require_approved_copied_log(args.copied_log)
    window_manifest = require_exact_sibling_window_manifest(args.window_manifest, copied_log)
    output_dir = args.output_dir.expanduser()
    reject_symlink_component(output_dir, "--output-dir")
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
        run_command(
            [
                sys.executable,
                str(WINDOW_MANIFEST_CHECKER),
                "--json",
                "--post-window-replay",
                str(window_manifest),
            ],
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
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "source_log": str(copied_log),
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
    report["bundle_report_identity"] = report_identity(report)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
