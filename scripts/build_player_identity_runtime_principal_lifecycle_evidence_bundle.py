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
from player_principal_commit_validation import is_reviewed_obelisk_commit
from snapshot_evidence_pack import reject_protected_output_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
BUILDER = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
WINDOW_MANIFEST_CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_window_manifest.py"
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
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if payload.get(key) is not False:
            raise SystemExit(f"{label} overclaims {key}")


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
    else:
        state["sha256"] = sha256_file(status.resolved)
    return state


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
    state["checked"] = True
    exit_code, payload, stderr = run_json_check(
        [
            sys.executable,
            str(WINDOW_REQUEST_CHECKER),
            "--json",
            str(request_pack["path"]),
            "--env-file",
            str(observer_env["path"]),
        ]
    )
    state["exit_code"] = exit_code
    state["stderr"] = stderr
    if isinstance(payload, dict):
        state["schema"] = payload.get("schema")
        state["ready"] = payload.get("ready") is True and payload.get("request_pack_ready") is True
        state["blockers"] = payload.get("blockers", [])
        state["next_blocker"] = payload.get("next_blocker")
    if not state["ready"]:
        add_blocker(
            blockers,
            "request_pack_check_failed",
            "request_pack",
            exit_code=exit_code,
            request_check_blockers=state.get("blockers", []),
        )
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
    request_pack = file_state(resolved / "sidecars" / run_id / "window-request.json", "request_pack", blockers)
    observer_env = file_state(resolved / "sidecars" / run_id / "observer-window.env", "observer_env", blockers)
    preflight_pre = file_state(resolved / "sidecars" / run_id / "preflight-pre.txt", "preflight_pre", blockers)
    preflight_post = file_state(resolved / "sidecars" / run_id / "preflight-post.txt", "preflight_post", blockers)
    request_check = request_pack_check_state(request_pack, observer_env, blockers)

    bundle_manifest = resolved / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
    approved_bundle = file_state(bundle_manifest, "approved_runtime_manifest", blockers)
    input_ready = (
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
        and preflight_pre["exists"]
        and preflight_post["exists"]
        and request_check["ready"]
    )
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle-preflight.v1",
        "ready": bool(input_ready),
        "bundle_inputs_ready": bool(input_ready),
        "request_pack_ready": bool(request_pack_ready),
        "approved_runtime_manifest_present": bool(approved_bundle["exists"]),
        "next_blocker": (
            "run_offline_evidence_bundle_builder"
            if input_ready and not approved_bundle["exists"]
            else "copied_log_and_window_manifest_required"
        ),
        "run_id": run_id,
        "evidence_dir": str(resolved),
        "inputs": {
            "copied_log": copied_log,
            "window_manifest": window_manifest,
            "request_pack": request_pack,
            "observer_env": observer_env,
            "request_pack_check": request_check,
            "preflight_pre": preflight_pre,
            "preflight_post": preflight_post,
            "approved_runtime_manifest": approved_bundle,
        },
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "preflight-only filesystem classification; does not analyze logs, build approved evidence, authorize runtime capture, or promote player identity",
            "request-pack readiness is preparation only and does not satisfy approved runtime evidence",
            "ready means the offline bundle builder has the copied inputs it needs; it does not mean approved runtime evidence already exists",
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
                str(args.window_manifest),
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
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "source_log": str(copied_log),
        "operational_window": {
            "check": str(window_check_path),
            "copied_log_sha256": window_check.get("copied_log", {}).get("sha256"),
            "manifest_ready": window_check.get("operational_window_manifest_ready"),
            "obelisk_commit": window_check.get("obelisk_commit"),
            "run_id": window_check.get("run_id"),
            "target": window_check.get("target"),
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
