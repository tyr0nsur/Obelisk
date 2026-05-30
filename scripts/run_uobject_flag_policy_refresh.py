#!/usr/bin/env python3
"""Run the rich-provenance UObject flag-policy refresh pipeline."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import validate_offline_artifact_gate as gate  # noqa: E402


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
REQUIRED_WEAK_INPUTS = {
    "ghidra_stdout": Path("weak/ghidra-headless.stdout"),
    "r2_windows": Path("weak/r2-weak-helper-caller-modes.txt"),
    "direct_call_counts": Path("weak/direct-call-counts.txt"),
}
REQUIRED_WINDOWS = {
    "weak_helper_reject_0x100": Path("windows/weak-helper-c70.objdump.txt"),
    "strict_0x4000_behavior": Path("windows/weak-helper-c70.objdump.txt"),
    "gobjects_backed_0x4000_skip": Path("windows/gobjects-4000-skip.objdump.txt"),
    "gc_static_0x100_support": Path("windows/gobjects-100-gc-pass.objdump.txt"),
}


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def parse_safe_id(value: str, field_name: str) -> str:
    if ".." in value:
        raise argparse.ArgumentTypeError(f"{field_name} must not contain '..'")
    if "/" in value or "\\" in value:
        raise argparse.ArgumentTypeError(f"{field_name} must not contain path separators")
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            f"{field_name} must be 1-128 characters of ASCII letters, digits, '.', '_', or '-' "
            "and start with a letter or digit"
        )
    return value


def parse_artifact_kind(value: str) -> str:
    return parse_safe_id(value, "--artifact-kind")


def parse_capture_id(value: str) -> str:
    return parse_safe_id(value, "--capture-id")


def parse_evidence_pack_id(value: str) -> str:
    return parse_safe_id(value, "--evidence-pack-id")


def artifact_identity(args: argparse.Namespace) -> dict[str, str] | None:
    values = {
        "artifact_kind": args.artifact_kind,
        "capture_id": args.capture_id,
        "evidence_pack_id": args.evidence_pack_id,
    }
    if not any(value is not None for value in values.values()):
        return None
    if not all(value is not None for value in values.values()):
        raise SystemExit(
            "artifact identity must include --artifact-kind, --capture-id, and --evidence-pack-id together"
        )
    return {key: value for key, value in values.items() if value is not None}


def append_artifact_identity_args(command: list[str], identity: dict[str, str] | None) -> None:
    if identity is None:
        return
    command.extend(
        [
            "--artifact-kind",
            identity["artifact_kind"],
            "--capture-id",
            identity["capture_id"],
            "--evidence-pack-id",
            identity["evidence_pack_id"],
        ]
    )


def reject_repo_output(path: Path) -> None:
    direct = path.expanduser().absolute()
    resolved = path.expanduser().resolve(strict=False)
    if is_relative_to(direct, REPO_ROOT):
        raise SystemExit(f"--output-root must not be inside the repository: {direct}")
    if is_relative_to(resolved, REPO_ROOT):
        raise SystemExit(f"--output-root must not be inside the repository: {resolved}")


def reject_protected_input_root(path: Path) -> None:
    state = gate.path_state(path, workspace_root=gate.DEFAULT_WORKSPACE_ROOT, protected_root=gate.SERVER_ROOT)
    if state["direct_under_protected"] and not state["direct_under_workspace"]:
        raise SystemExit(f"--input-root must not read under protected server root: {state['direct']}")
    if state["resolved_under_protected"] and not state["resolved_under_workspace"]:
        raise SystemExit(f"--input-root must not resolve under protected server root: {state['resolved']}")


def reject_protected_output(path: Path) -> None:
    state = gate.path_state(path, workspace_root=gate.DEFAULT_WORKSPACE_ROOT, protected_root=gate.SERVER_ROOT)
    if state["direct_under_protected"] and not state["direct_under_workspace"]:
        raise SystemExit(f"--output-root must not write under protected server root: {state['direct']}")
    if state["resolved_under_protected"] and not state["resolved_under_workspace"]:
        raise SystemExit(f"--output-root must not resolve under protected server root: {state['resolved']}")


def reject_output_file(path: Path) -> None:
    reject_repo_output(path)
    reject_protected_output(path)


def run_json(command: list[str], *, output: Path | None = None, allowed_returncodes: set[int] | None = None) -> dict[str, Any]:
    allowed = allowed_returncodes or {0}
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode not in allowed:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(command)}\n{detail}")
    if output is not None:
        reject_output_file(output)
        output.write_text(result.stdout, encoding="utf-8")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"command did not emit JSON: {' '.join(command)}: {exc}") from exc


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(command)}\n{detail}")


def assert_safe_output_files(paths: list[Path]) -> None:
    for path in paths:
        reject_output_file(path)


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    identity = artifact_identity(args)
    input_root = args.input_root.expanduser().resolve(strict=False)
    output_root = args.output_root.expanduser().resolve(strict=False)
    reject_protected_input_root(args.input_root)
    reject_repo_output(args.output_root)
    reject_protected_output(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    weak_paths = {name: input_root / relative for name, relative in REQUIRED_WEAK_INPUTS.items()}
    window_paths = {name: input_root / relative for name, relative in REQUIRED_WINDOWS.items()}

    preflight_output = output_root / "rich-provenance-preflight.json"
    weak_helper_output = output_root / "weak-helper-caller-mode.redacted.json"
    policy_output = output_root / "uobject-flag-policy.redacted.json"
    consume_output = output_root / "uobject-flag-policy.consume-gate.json"
    promote_output = output_root / "uobject-flag-policy.promote-gate.json"
    assert_safe_output_files(
        [
            preflight_output,
            weak_helper_output,
            policy_output,
            consume_output,
            promote_output,
        ]
    )

    preflight_command = [
        sys.executable,
        str(SCRIPT_DIR / "validate_uobject_flag_policy_provenance_inputs.py"),
        "--root",
        str(input_root),
        "--require-under-root",
        "--require-rich-provenance",
        "--expected-binary-sha256",
        args.expected_binary_sha256,
        "--ghidra-stdout",
        str(weak_paths["ghidra_stdout"]),
        "--r2-windows",
        str(weak_paths["r2_windows"]),
        "--direct-call-counts",
        str(weak_paths["direct_call_counts"]),
        "--json",
    ]
    for label, path in window_paths.items():
        preflight_command.extend(["--window", f"{label}={path}"])
    preflight = run_json(preflight_command, output=preflight_output)
    if preflight.get("status") != "accepted":
        raise SystemExit(f"rich provenance preflight blocked; inspect {preflight_output}")

    converter_command = [
        sys.executable,
        str(SCRIPT_DIR / "convert_weak_helper_caller_modes.py"),
        "--ghidra-stdout",
        str(weak_paths["ghidra_stdout"]),
        "--r2-windows",
        str(weak_paths["r2_windows"]),
        "--direct-call-counts",
        str(weak_paths["direct_call_counts"]),
        "--binary-sha256",
        args.expected_binary_sha256,
        "--output",
        str(weak_helper_output),
    ]
    for tool_version in args.tool_version:
        converter_command.extend(["--tool-version", tool_version])
    run_command(converter_command)

    builder_command = [
        sys.executable,
        str(SCRIPT_DIR / "build_uobject_flag_policy_report.py"),
        "--binary-sha256",
        args.expected_binary_sha256,
        "--weak-helper-caller-mode",
        str(weak_helper_output),
        "--output",
        str(policy_output),
    ]
    append_artifact_identity_args(builder_command, identity)
    for label, path in window_paths.items():
        builder_command.extend(["--window", f"{label}={path}"])
    run_command(builder_command)

    consume = run_json(
        [
            sys.executable,
            str(SCRIPT_DIR / "validate_offline_artifact_gate.py"),
            "--root",
            str(output_root),
            "--manifest",
            str(policy_output),
            "--expected-binary-sha256",
            args.expected_binary_sha256,
            "--mode",
            "consume",
            "--json",
        ],
        output=consume_output,
    )
    promote = run_json(
        [
            sys.executable,
            str(SCRIPT_DIR / "validate_offline_artifact_gate.py"),
            "--root",
            str(output_root),
            "--manifest",
            str(policy_output),
            "--expected-binary-sha256",
            args.expected_binary_sha256,
            "--mode",
            "promote",
            "--json",
        ],
        output=promote_output,
        allowed_returncodes={0, 3},
    )

    if consume.get("status") != "accepted":
        raise SystemExit(f"consume gate blocked; inspect {consume_output}")
    if promote.get("status") != "blocked":
        raise SystemExit(f"promote gate unexpectedly accepted; inspect {promote_output}")
    promote_reasons = {
        blocker.get("reason")
        for blocker in promote.get("blockers", [])
        if isinstance(blocker, dict) and isinstance(blocker.get("reason"), str)
    }
    if "promote_mode_uobject_flag_policy_candidate_only" not in promote_reasons:
        raise SystemExit(f"promote gate did not include candidate-only blocker; inspect {promote_output}")

    result = {
        "schema": "obelisk.uobject-flag-policy-refresh-run.v1",
        "status": "accepted_internal_static_evidence",
        "promotion_status": "blocked",
        "expected_binary_sha256": args.expected_binary_sha256,
        "input_root": str(input_root),
        "output_root": str(output_root),
        "outputs": {
            "rich_provenance_preflight": str(preflight_output),
            "weak_helper_caller_mode": str(weak_helper_output),
            "uobject_flag_policy": str(policy_output),
            "consume_gate": str(consume_output),
            "promote_gate": str(promote_output),
        },
        "non_claims": [
            "internal static evidence only",
            "does not promote ResourceHandle, object identity, lookup, mutation, return override, or lifecycle names",
        ],
    }
    if identity is not None:
        result["artifact_identity"] = identity
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-binary-sha256", required=True)
    parser.add_argument("--artifact-kind", type=parse_artifact_kind)
    parser.add_argument("--capture-id", type=parse_capture_id)
    parser.add_argument("--evidence-pack-id", type=parse_evidence_pack_id)
    parser.add_argument("--tool-version", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    result = build_result(parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
