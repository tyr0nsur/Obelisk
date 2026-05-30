#!/usr/bin/env python3
"""Build a redacted static UObject flag-policy candidate report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import reject_protected_input_path, reject_protected_output_path  # noqa: E402


SCHEMA = "obelisk.uobject-flag-policy-report.v1"
WEAK_HELPER_SCHEMA = "obelisk.weak-helper-caller-mode-redacted.v1"
PROVENANCE_SCHEMAS = {
    "obelisk.offline-artifact-provenance.v1",
    "obelisk.static-artifact-provenance.v1",
}
EVIDENCE_KIND = "static_negative_equivalent_candidate"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PATH_KEY_RE = re.compile(r"(?:^|_)(path|file|source|artifact|binary|core|stdout|stderr|copied_to)$")
WINDOW_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
OBJDUMP_INSTRUCTION_RE = re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2}\s+)+\s+\S+", re.IGNORECASE)
OBJDUMP_SYMBOL_RE = re.compile(r"^\s*[0-9a-f]+\s+<[^>]+>:\s*$", re.IGNORECASE)
OBJDUMP_HEADER_RE = re.compile(r"^\S.*:\s+file format\s+\S+\s*$", re.IGNORECASE)
OBJDUMP_SECTION_RE = re.compile(r"^\s*Disassembly of section \S+:\s*$")
OBJDUMP_ADDRESS_BYTE_CONTINUATION_RE = re.compile(r"^\s*[0-9a-f]+:\s+(?:[0-9a-f]{2}\s+)+$", re.IGNORECASE)
OBJDUMP_BYTE_CONTINUATION_RE = re.compile(r"^\s*(?:[0-9a-f]{2}\s+)+$", re.IGNORECASE)
MAX_CONNECTED_WINDOW_BYTES = 0x1000

REQUIRED_WINDOWS = (
    "weak_helper_reject_0x100",
    "strict_0x4000_behavior",
    "gobjects_backed_0x4000_skip",
    "gc_static_0x100_support",
)

PUBLIC_HELPER_ID = "weak_helper_flag_policy_candidate"

WINDOW_ALIASES = {
    "weak_helper_0x100_reject": "weak_helper_reject_0x100",
    "weak_helper_reject_0x100_window": "weak_helper_reject_0x100",
    "strict_0x4000": "strict_0x4000_behavior",
    "strict_0x4000_behavior_window": "strict_0x4000_behavior",
    "gobjects_backed_0x4000_skip_window": "gobjects_backed_0x4000_skip",
    "gobjects_0x4000_skip": "gobjects_backed_0x4000_skip",
    "gc_static_0x100_support_window": "gc_static_0x100_support",
    "static_gc_0x100_support": "gc_static_0x100_support",
}

WINDOW_CHECKS = {
    "weak_helper_reject_0x100": (
        ("gobjects_count_ref", r"#\s*595b804\b"),
        ("gobjects_chunk_ref", r"#\s*595b7f0\b"),
        ("uobject_flags_load", r"\bmov\s+edx,\s*DWORD PTR \[rcx\+0x8\]"),
        ("mask_0x100", r"\band\s+edi,\s*0x100\b"),
        ("null_return_branch", r"\bjne\s+1d56cea\b[\s\S]{0,1600}\bxor\s+eax,\s*eax\b[\s\S]{0,1600}\bret\b"),
    ),
    "strict_0x4000_behavior": (
        ("strict_mode_guard", r"\btest\s+sil,\s*sil\b"),
        ("mask_0x4000", r"\btest\s+dh,\s*0x40\b"),
        ("null_return_branch", r"\btest\s+dh,\s*0x40\b[\s\S]{0,640}\bjne\s+1d56cf3\b[\s\S]{0,640}\bret\b"),
    ),
    "gobjects_backed_0x4000_skip": (
        ("gobjects_count_ref", r"#\s*595b804\b"),
        ("gobjects_chunk_ref", r"#\s*595b7f0\b"),
        ("fuobjectitem_load", r"\badd\s+rax,\s*QWORD PTR \[rdx\+rcx\*8\]"),
        ("uobject_load", r"\bmov\s+rbx,\s*QWORD PTR \[rax\]"),
        ("mask_0x4000", r"\btest\s+BYTE PTR \[rbx\+0x9\],\s*0x40\b"),
        ("skip_branch", r"\btest\s+BYTE PTR \[rbx\+0x9\],\s*0x40\b[\s\S]{0,120}\bjne\s+2982ba0\b"),
    ),
    "gc_static_0x100_support": (
        ("gc_window_start", r"\b0000000001d18a90\b"),
        ("gobjects_count_ref", r"#\s*595b804\b"),
        ("gobjects_chunk_ref", r"#\s*595b7f0\b"),
        ("fuobjectitem_iteration", r"\bmov\s+rdi,\s*QWORD PTR \[rcx\+rsi\*8\]"),
        ("uobject_load", r"\bmov\s+rdi,\s*QWORD PTR \[rdi\]"),
        ("set_0x100", r"\bor\s+DWORD PTR \[rdi\+0x8\],\s*0x100\b"),
    ),
}

NON_CLAIMS = (
    "does_not_promote_resourcehandle",
    "does_not_promote_post_callback_lookup",
    "does_not_claim_mutation_or_return_override_safety",
    "does_not_assign_public_ue_lifecycle_flag_names",
    "does_not_prove_public_sdk_object_identity",
    "does_not_replace_rejected_runtime_object_samples",
)

REMAINING_BLOCKERS = (
    "static_only_evidence",
    "no_rejected_runtime_object_samples",
    "no_named_lifecycle_semantics",
    "public_resourcehandle_policy_missing",
    "post_callback_lifetime_policy_unproven",
)

CALLER_ROW_KEYS = {
    "helper",
    "helper_address_sha256",
    "caller_address_sha256",
    "mode_args",
    "return_use",
    "source_count",
    "evidence",
    "policy_observation",
    "claim_level",
    "path_redacted",
    "lifecycle_names",
}

WEAK_HELPER_SOURCE_KEYS = {"ghidra_stdout", "r2_windows", "direct_call_counts"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_safe_id(value: str, field_name: str) -> str:
    if not value:
        raise argparse.ArgumentTypeError(f"{field_name} must not be empty")
    if ".." in value:
        raise argparse.ArgumentTypeError(f"{field_name} must not contain '..'")
    if "/" in value or "\\" in value:
        raise argparse.ArgumentTypeError(f"{field_name} must not contain path separators")
    if SAFE_ID_RE.fullmatch(value) is None:
        raise argparse.ArgumentTypeError(
            f"{field_name} must be 1-128 characters of ASCII letters, digits, '.', '_', or '-' "
            "and start with a letter or digit"
        )
    return value


def parse_artifact_kind(value: str) -> str:
    return validate_safe_id(value, "--artifact-kind")


def parse_capture_id(value: str) -> str:
    return validate_safe_id(value, "--capture-id")


def parse_evidence_pack_id(value: str) -> str:
    return validate_safe_id(value, "--evidence-pack-id")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} does not exist") from exc
    except OSError as exc:
        raise SystemExit(f"{label} is unreadable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return payload


def key_names_path(key: object) -> bool:
    text = str(key).casefold()
    return bool(PATH_KEY_RE.search(text)) or text.endswith("_path") or text.endswith("_file")


def collect_path_fields(value: object, *, trail: str = "$") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if isinstance(child, str) and key_names_path(key):
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_path_fields(child, trail=child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.extend(collect_path_fields(child, trail=f"{trail}[{index}]"))
    return found


def normalize_window_name(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_")
    return WINDOW_ALIASES.get(normalized, normalized)


def parse_window(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--window must be NAME=PATH")
    raw_name, raw_path = value.split("=", 1)
    raw_name = raw_name.strip()
    if not WINDOW_NAME_RE.fullmatch(raw_name):
        raise argparse.ArgumentTypeError(f"unsafe window name: {raw_name}")
    if not raw_path:
        raise argparse.ArgumentTypeError("--window path must not be empty")
    return normalize_window_name(raw_name), Path(raw_path)


def matched_patterns(window_name: str, text: str) -> tuple[list[str], list[str]]:
    matched: list[str] = []
    missing: list[str] = []
    for label, pattern in WINDOW_CHECKS[window_name]:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matched.append(label)
        else:
            missing.append(label)
    return matched, missing


def validate_objdump_window_text(window_name: str, text: str) -> list[str]:
    blockers: list[str] = []
    addresses: list[int] = []
    stray_lines: list[int] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = OBJDUMP_INSTRUCTION_RE.match(line)
        if match:
            addresses.append(int(match.group(1), 16))
            continue
        if (
            OBJDUMP_SYMBOL_RE.match(line)
            or OBJDUMP_HEADER_RE.match(line)
            or OBJDUMP_SECTION_RE.match(line)
            or OBJDUMP_ADDRESS_BYTE_CONTINUATION_RE.match(line)
            or OBJDUMP_BYTE_CONTINUATION_RE.match(line)
            or line.strip() == "..."
        ):
            continue
        stray_lines.append(line_number)

    if len(addresses) < 3:
        blockers.append("too_few_objdump_instruction_lines")
    if any(next_addr <= current for current, next_addr in zip(addresses, addresses[1:])):
        blockers.append("instruction_addresses_not_strictly_increasing")
    if addresses and addresses[-1] - addresses[0] > MAX_CONNECTED_WINDOW_BYTES:
        blockers.append("instruction_window_too_wide")
    if stray_lines:
        preview = "|".join(str(line_number) for line_number in stray_lines[:5])
        blockers.append(f"non_objdump_text_lines:{preview}")
    return blockers


def validate_window_provenance(path: Path, *, artifact_sha256: str, binary_sha256: str, label: str) -> dict[str, Any]:
    provenance_path = reject_protected_input_path(path.with_name(path.name + ".provenance.json"), f"{label} provenance")
    payload = load_json(provenance_path, f"{label} provenance")
    blockers: list[str] = []
    if payload.get("schema") not in PROVENANCE_SCHEMAS:
        blockers.append("provenance_schema_mismatch")
    if payload.get("verified") is not True:
        blockers.append("provenance_not_verified")
    if payload.get("binary_sha256") != binary_sha256:
        blockers.append("provenance_binary_sha256_mismatch")
    if payload.get("artifact_sha256") != artifact_sha256:
        blockers.append("provenance_artifact_sha256_mismatch")
    for trail, raw_path in collect_path_fields(payload):
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = provenance_path.parent / candidate
        try:
            reject_protected_input_path(candidate, f"{label} provenance {trail}")
        except SystemExit:
            blockers.append(f"provenance_protected_path_field:{trail}")
    if blockers:
        raise SystemExit(f"{label} provenance incomplete: {','.join(blockers)}")
    return {
        "schema": payload.get("schema"),
        "binary_sha256": binary_sha256,
        "artifact_sha256": artifact_sha256,
        "sidecar_sha256": sha256_file(provenance_path),
        "verified": True,
        "path_redacted": True,
    }


def validate_weak_helper_sources(payload: dict[str, Any], binary_sha256: str) -> list[str]:
    blockers: list[str] = []
    sources = payload.get("sources")
    if not isinstance(sources, dict) or set(sources) != WEAK_HELPER_SOURCE_KEYS:
        return ["weak_helper_sources_missing_or_unexpected"]
    for source_name in sorted(WEAK_HELPER_SOURCE_KEYS):
        source = sources.get(source_name)
        if not isinstance(source, dict):
            blockers.append(f"weak_helper_source_not_object:{source_name}")
            continue
        artifact_sha = source.get("artifact_sha256")
        if not isinstance(artifact_sha, str) or SHA256_RE.fullmatch(artifact_sha) is None:
            blockers.append(f"weak_helper_source_artifact_sha256_invalid:{source_name}")
        if not isinstance(source.get("tool"), str) or not source["tool"]:
            blockers.append(f"weak_helper_source_tool_missing:{source_name}")
        if not isinstance(source.get("version"), str) or not source["version"]:
            blockers.append(f"weak_helper_source_version_missing:{source_name}")
        provenance = source.get("provenance")
        if not isinstance(provenance, dict):
            blockers.append(f"weak_helper_source_provenance_missing:{source_name}")
            continue
        if provenance.get("verified") is not True:
            blockers.append(f"weak_helper_source_provenance_not_verified:{source_name}")
        if provenance.get("path_redacted") is not True:
            blockers.append(f"weak_helper_source_provenance_path_not_redacted:{source_name}")
        if provenance.get("binary_sha256") != binary_sha256:
            blockers.append(f"weak_helper_source_provenance_binary_mismatch:{source_name}")
        if provenance.get("artifact_sha256") != artifact_sha:
            blockers.append(f"weak_helper_source_provenance_artifact_mismatch:{source_name}")
        if not isinstance(provenance.get("sidecar_sha256"), str) or SHA256_RE.fullmatch(provenance["sidecar_sha256"]) is None:
            blockers.append(f"weak_helper_source_provenance_sidecar_sha256_invalid:{source_name}")
    return blockers


def validate_weak_helper_report(payload: dict[str, Any], binary_sha256: str) -> dict[str, Any]:
    blockers: list[str] = []
    if payload.get("schema") != WEAK_HELPER_SCHEMA:
        blockers.append("invalid_weak_helper_schema")
    if payload.get("status") != "accepted_internal_static_evidence":
        blockers.append("weak_helper_status_not_accepted_internal_static_evidence")
    blockers.extend(validate_weak_helper_sources(payload, binary_sha256))
    binary = payload.get("binary")
    if not isinstance(binary, dict) or binary.get("sha256") != binary_sha256:
        blockers.append("weak_helper_binary_sha256_mismatch")

    contract = payload.get("builder_contract")
    if not isinstance(contract, dict) or contract.get("promotion_gate_ready") is not False:
        blockers.append("weak_helper_promotion_gate_not_false")

    helpers = payload.get("helpers")
    c70 = helpers.get("0x1d56c70") if isinstance(helpers, dict) else None
    if not isinstance(c70, dict):
        blockers.append("missing_weak_helper_1d56c70")
    else:
        rules = c70.get("flag_rules")
        if not isinstance(rules, list):
            rules = []
        rule_map = {rule.get("mask"): rule.get("result") for rule in rules if isinstance(rule, dict)}
        if rule_map.get("0x100") != "null_always":
            blockers.append("missing_weak_helper_0x100_null_always_rule")
        if rule_map.get("0x4000") != "null_when_sil_zero":
            blockers.append("missing_weak_helper_0x4000_mode_rule")

    coverage = payload.get("direct_call_coverage")
    c70_coverage = coverage.get("0x1d56c70") if isinstance(coverage, dict) else None
    c70_expected = c70_coverage.get("expected") if isinstance(c70_coverage, dict) else None
    c70_observed = c70_coverage.get("observed") if isinstance(c70_coverage, dict) else None
    if (
        not isinstance(c70_expected, int)
        or isinstance(c70_expected, bool)
        or not isinstance(c70_observed, int)
        or isinstance(c70_observed, bool)
        or c70_observed != c70_expected
        or c70_expected <= 0
    ):
        blockers.append("weak_helper_1d56c70_direct_call_coverage_incomplete")

    caller_rows_summary: dict[str, Any] | None = None
    caller_rows_sha256: str | None = None
    caller_rows = payload.get("caller_rows")
    if not isinstance(caller_rows, list) or len(caller_rows) != c70_expected:
        blockers.append("weak_helper_caller_rows_count_mismatch")
    else:
        caller_hashes: set[str] = set()
        normalized_rows: list[dict[str, Any]] = []
        expected_helper_sha = hashlib.sha256(
            f"obelisk.weak-helper-caller-mode:{binary_sha256}:0x1d56c70".encode("ascii")
        ).hexdigest()
        for row in caller_rows:
            if not isinstance(row, dict):
                blockers.append("weak_helper_caller_row_not_object")
                continue
            if set(row) != CALLER_ROW_KEYS:
                blockers.append("weak_helper_caller_row_unexpected_fields")
            if row.get("helper") != "0x1d56c70":
                blockers.append("weak_helper_caller_row_helper_mismatch")
            if row.get("helper_address_sha256") != expected_helper_sha:
                blockers.append("weak_helper_caller_row_helper_sha256_mismatch")
            caller_sha = row.get("caller_address_sha256")
            if not isinstance(caller_sha, str) or SHA256_RE.fullmatch(caller_sha) is None:
                blockers.append("weak_helper_caller_row_sha256_invalid")
            else:
                caller_hashes.add(caller_sha)
            if row.get("mode_args") != {"sil": {"source": "const", "value": 1}}:
                blockers.append("weak_helper_caller_row_mode_args_mismatch")
            if row.get("return_use") != {"register": "rax", "nonzero_path": "kept_or_valid"}:
                blockers.append("weak_helper_caller_row_return_use_mismatch")
            if row.get("policy_observation") != {
                "0x100": "null_always",
                "0x4000": "not_rejected_in_observed_sil_1_callers",
            }:
                blockers.append("weak_helper_caller_row_policy_observation_mismatch")
            if row.get("source_count") != 2 or row.get("evidence") != ["ghidra", "radare2"]:
                blockers.append("weak_helper_caller_row_source_evidence_mismatch")
            if row.get("claim_level") != "static_caller_mode_candidate":
                blockers.append("weak_helper_caller_row_claim_level_mismatch")
            if row.get("path_redacted") is not True or row.get("lifecycle_names") != "not_promoted":
                blockers.append("weak_helper_caller_row_boundary_mismatch")
            normalized_rows.append(
                {
                    "helper": row.get("helper"),
                    "helper_address_sha256": row.get("helper_address_sha256"),
                    "caller_address_sha256": caller_sha,
                    "mode_args": row.get("mode_args"),
                    "return_use": row.get("return_use"),
                    "source_count": row.get("source_count"),
                    "evidence": row.get("evidence"),
                    "policy_observation": row.get("policy_observation"),
                    "claim_level": row.get("claim_level"),
                    "path_redacted": row.get("path_redacted"),
                    "lifecycle_names": row.get("lifecycle_names"),
                }
            )
        if len(caller_hashes) != c70_expected:
            blockers.append("weak_helper_caller_rows_unique_count_mismatch")
        caller_rows_sha256 = hashlib.sha256(
            json.dumps(
                sorted(normalized_rows, key=lambda value: str(value.get("caller_address_sha256"))),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        caller_rows_summary = {
            "helper": PUBLIC_HELPER_ID,
            "row_count": len(caller_rows),
            "unique_caller_hash_count": len(caller_hashes),
            "mode_args": {"sil": {"source": "const", "value": 1}},
            "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
            "source_count": 2,
            "evidence": ["ghidra", "radare2"],
            "policy_observation": {
                "0x100": "null_always",
                "0x4000": "not_rejected_in_observed_sil_1_callers",
            },
            "claim_level": "internal_static_caller_mode_candidate",
            "lifecycle_names": "not_promoted",
            "path_redacted": True,
            "caller_rows_sha256": caller_rows_sha256,
        }

    if blockers:
        raise SystemExit(f"weak-helper caller-mode report incomplete: {','.join(blockers)}")

    summary = {
        "schema": payload.get("schema"),
        "artifact_sha256": None,
        "promotion_gate_ready": False,
        "direct_call_coverage": {
            PUBLIC_HELPER_ID: {
                "expected": c70_expected,
                "observed": c70_observed,
            },
        },
        "flag_rules": [
            {"mask": "0x100", "result": "null_always"},
            {"mask": "0x4000", "result": "null_when_sil_zero"},
        ],
    }
    if caller_rows_summary is not None:
        summary["caller_rows_summary"] = caller_rows_summary
    return summary


def read_and_validate_windows(windows: list[tuple[str, Path]], *, binary_sha256: str) -> list[dict[str, Any]]:
    by_name: dict[str, Path] = {}
    unknown: list[str] = []
    for name, path in windows:
        if name not in WINDOW_CHECKS:
            unknown.append(name)
            continue
        if name in by_name:
            raise SystemExit(f"duplicate --window for required name: {name}")
        by_name[name] = path

    if unknown:
        raise SystemExit(f"unknown --window entries: {','.join(sorted(unknown))}")

    missing_windows = [name for name in REQUIRED_WINDOWS if name not in by_name]
    if missing_windows:
        raise SystemExit(f"missing required --window entries: {','.join(missing_windows)}")

    summaries: list[dict[str, Any]] = []
    blockers: list[str] = []
    for name in REQUIRED_WINDOWS:
        path = reject_protected_input_path(by_name[name], f"--window {name}")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError as exc:
            raise SystemExit(f"--window {name} does not exist") from exc
        except OSError as exc:
            raise SystemExit(f"--window {name} is unreadable: {exc}") from exc

        structure_blockers = validate_objdump_window_text(name, text)
        if structure_blockers:
            blockers.append(f"{name}:{'|'.join(structure_blockers)}")
        matched, missing = matched_patterns(name, text)
        if missing:
            blockers.append(f"{name}:{'|'.join(missing)}")
        artifact_sha256 = sha256_file(path)
        summaries.append(
            {
                "name": name,
                "artifact_sha256": artifact_sha256,
                "byte_count": len(text.encode("utf-8")),
                "matched_patterns": matched,
                "path_redacted": True,
                "provenance": validate_window_provenance(
                    path,
                    artifact_sha256=artifact_sha256,
                    binary_sha256=binary_sha256,
                    label=f"--window {name}",
                ),
            }
        )

    if blockers:
        raise SystemExit(f"window evidence incomplete: {','.join(blockers)}")
    return summaries


def canonical_policy_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": report.get("schema"),
        "evidence_kind": report.get("evidence_kind"),
        "status": report.get("status"),
        "binary": report.get("binary"),
        "promotion_ready": report.get("promotion_ready"),
        "post_callback_resource_handle_ready": report.get("post_callback_resource_handle_ready"),
        "weak_helper_caller_mode": report.get("weak_helper_caller_mode"),
        "windows_summary": report.get("windows_summary"),
        "policy_candidates": report.get("policy_candidates"),
        "internal_revalidation_contract": report.get("internal_revalidation_contract"),
        "remaining_blockers": report.get("remaining_blockers"),
        "non_claims": report.get("non_claims"),
        "redaction": report.get("redaction"),
    }


def build_artifact_identity(
    *,
    artifact_kind: str,
    capture_id: str,
    evidence_pack_id: str,
    report: dict[str, Any],
) -> dict[str, str]:
    identity_without_hash = {
        "artifact_kind": validate_safe_id(artifact_kind, "artifact_kind"),
        "capture_id": validate_safe_id(capture_id, "capture_id"),
        "evidence_pack_id": validate_safe_id(evidence_pack_id, "evidence_pack_id"),
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": canonical_policy_report(report),
    }
    return {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(canonical_json_bytes(material)).hexdigest(),
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    if not SHA256_RE.fullmatch(args.binary_sha256):
        raise SystemExit("--binary-sha256 must be a lowercase SHA256")

    weak_helper_path = reject_protected_input_path(args.weak_helper_caller_mode, "--weak-helper-caller-mode")
    weak_helper_payload = load_json(weak_helper_path, "--weak-helper-caller-mode")
    weak_helper_summary = validate_weak_helper_report(weak_helper_payload, args.binary_sha256)
    weak_helper_artifact_sha256 = sha256_file(weak_helper_path)
    weak_helper_summary["artifact_sha256"] = weak_helper_artifact_sha256
    if "caller_rows_summary" in weak_helper_summary:
        weak_helper_summary["caller_rows_source"] = {
            "schema": WEAK_HELPER_SCHEMA,
            "source_artifact_sha256": weak_helper_artifact_sha256,
            "binary_sha256": args.binary_sha256,
            "caller_rows_sha256": weak_helper_summary["caller_rows_summary"]["caller_rows_sha256"],
            "path_redacted": True,
        }
    window_summaries = read_and_validate_windows(args.window or [], binary_sha256=args.binary_sha256)

    report = {
        "schema": SCHEMA,
        "evidence_kind": EVIDENCE_KIND,
        "status": "candidate_blocked",
        "binary": {
            "sha256": args.binary_sha256,
            "path_redacted": True,
        },
        "promotion_ready": False,
        "post_callback_resource_handle_ready": False,
        "weak_helper_caller_mode": weak_helper_summary,
        "windows_summary": {
            "required": list(REQUIRED_WINDOWS),
            "observed": window_summaries,
            "all_required_present": True,
            "all_required_patterns_present": True,
        },
        "policy_candidates": [
            {
                "mask": "0x100",
                "candidate": "hard_invalid_static_negative_equivalent",
                "support": [
                    "weak_helper_flag_policy_candidate_null_always",
                    "gc_static_0x100_support",
                ],
                "ue_lifecycle_name": "not_promoted",
            },
            {
                "mask": "0x4000",
                "candidate": "strict_invalid_static_negative_equivalent",
                "support": [
                    "weak_helper_flag_policy_candidate_null_when_mode_zero",
                    "strict_0x4000_behavior",
                    "gobjects_backed_0x4000_skip",
                ],
                "ue_lifecycle_name": "not_promoted",
            },
        ],
        "internal_revalidation_contract": {
            "name": "InternalUObjectRevalidationCandidate",
            "lifetime": "frame_local_only",
            "post_callback_lookup": "rejected",
            "flag_policy": {
                "0x100": "reject",
                "0x4000": "reject_by_default",
            },
            "output": "copied_bool_or_obelisk_owned_data_only",
            "public_api": "not_promoted",
        },
        "remaining_blockers": list(REMAINING_BLOCKERS),
        "non_claims": list(NON_CLAIMS),
        "redaction": {
            "paths": "redacted",
            "addresses": "redacted",
            "raw_snippets": "omitted",
        },
    }
    return {
        "artifact_identity": build_artifact_identity(
            artifact_kind=args.artifact_kind,
            capture_id=args.capture_id,
            evidence_pack_id=args.evidence_pack_id,
            report=report,
        ),
        **report,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--weak-helper-caller-mode", type=Path, required=True)
    parser.add_argument("--window", action="append", type=parse_window, default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--artifact-kind",
        type=parse_artifact_kind,
        default=SCHEMA,
        help="Safe artifact kind to include in artifact_identity.",
    )
    parser.add_argument(
        "--capture-id",
        type=parse_capture_id,
        default="uobject-flag-policy-capture",
        help="Safe capture identifier to include in artifact_identity.",
    )
    parser.add_argument(
        "--evidence-pack-id",
        type=parse_evidence_pack_id,
        default="uobject-flag-policy-pack",
        help="Safe evidence pack identifier to include in artifact_identity.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = reject_protected_output_path(args.output, "--output")
    payload = build_payload(args)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
