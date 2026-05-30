#!/usr/bin/env python3
"""Build a redacted candidate-only UObject flag transition matrix."""

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


SCHEMA = "obelisk.uobject-flag-transition-matrix.v1"
PROVENANCE_SCHEMAS = {
    "obelisk.offline-artifact-provenance.v1",
    "obelisk.static-artifact-provenance.v1",
}
EVIDENCE_KIND = "static_uobject_plus_0x8_flag_transition_candidate"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
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
    "weak_publish_from_uobject_1d56970_1d56a30",
    "weak_validity_mode_a30_1d56a30_1d56ae0",
    "weak_validity_strict_ae0_1d56ae0_1d56b60",
    "weak_stale_mode_b60_1d56b60_1d56c00",
    "weak_lookup_strict_c00_1d56c00_1d56c70",
    "weak_lookup_allow4000_c70_1d56c70_1d56d00",
    "weak_lookup_raw_d00_1d56d00_1d56d60",
    "weak_refresh_from_object_d60_1d56d60_1d56ed0",
    "gc_mark_100_8000_1d18a90_1d18c70",
    "gobjects_4000_skip_mark_2982920_2982b60",
    "holder_4000_skip_mark_11ee120_11ee270",
)

OPTIONAL_WINDOWS = (
    "uobject_4000_set_call_clear_251f970_251f986",
    "uobject_100_clear_1d637c8_1d63888",
)

DWORD_PLUS_8 = r"DWORD PTR \[[^\]\n]+\+0x8\]"
BYTE_PLUS_9 = r"BYTE PTR \[[^\]\n]+\+0x9\]"
FLAG_0X100_TEST = rf"(?:\btest\s+(?:{DWORD_PLUS_8},\s*0x100|{BYTE_PLUS_9},\s*0x1|BYTE PTR \[[^\]\n]+\+0x9\],\s*0x41|[abcd][hl],\s*0x1)\b|\band\s+\w+,\s*0x100\b)"
FLAG_0X4000_TEST = rf"(?:\btest\s+(?:{DWORD_PLUS_8},\s*0x4000|{BYTE_PLUS_9},\s*0x40|BYTE PTR \[[^\]\n]+\+0x9\],\s*0x41|[abcd][hl],\s*0x40)\b|\band\s+\w+,\s*0x4000\b)"

WINDOW_CHECKS = {
    "weak_publish_from_uobject_1d56970_1d56a30": (
        ("uobject_plus_0x8_serial_or_flags_operand", rf"(?:{DWORD_PLUS_8}|DWORD PTR \[[^\]\n]+\+0xc\])"),
    ),
    "weak_validity_mode_a30_1d56a30_1d56ae0": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("tests_0x100", FLAG_0X100_TEST),
        ("mentions_0x4000_mode", rf"(?:0x4000|0x40|sil|esi)"),
    ),
    "weak_validity_strict_ae0_1d56ae0_1d56b60": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("tests_0x100", FLAG_0X100_TEST),
        ("tests_0x4000", FLAG_0X4000_TEST),
        ("preserves_null_edge_case", r"\btest\s+\w+,\s*\w+\b"),
    ),
    "weak_stale_mode_b60_1d56b60_1d56c00": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("tests_0x100", FLAG_0X100_TEST),
        ("mentions_0x4000_mode", rf"(?:0x4000|0x40|sil|esi)"),
    ),
    "weak_lookup_strict_c00_1d56c00_1d56c70": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("tests_0x100", FLAG_0X100_TEST),
        ("tests_0x4000", FLAG_0X4000_TEST),
    ),
    "weak_lookup_allow4000_c70_1d56c70_1d56d00": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("tests_0x100", FLAG_0X100_TEST),
        ("mode_register_controls_0x4000", rf"(?:sil|esi)"),
    ),
    "weak_lookup_raw_d00_1d56d00_1d56d60": (
        ("gobjects_or_index_operand", r"(?:595b7e0|\+0x10|\+0x18|\*8)"),
    ),
    "weak_refresh_from_object_d60_1d56d60_1d56ed0": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("tests_0x100", FLAG_0X100_TEST),
    ),
    "gc_mark_100_8000_1d18a90_1d18c70": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("sets_or_tests_0x100", rf"(?:\bor\s+(?:{DWORD_PLUS_8},\s*0x100|{BYTE_PLUS_9},\s*0x1)\b|\btest\s+[^,\n]+,\s*0x100\b)"),
        ("sets_0x8000_register_then_store", rf"\bor\s+\w+,\s*0x8000\b.*\bmov\s+{DWORD_PLUS_8},\s*\w+"),
    ),
    "gobjects_4000_skip_mark_2982920_2982b60": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("tests_or_sets_0x4000", rf"(?:\btest\s+(?:{DWORD_PLUS_8},\s*0x4000|{BYTE_PLUS_9},\s*0x40)\b|\bor\s+(?:{DWORD_PLUS_8},\s*0x4000|{BYTE_PLUS_9},\s*0x40)\b)"),
    ),
    "holder_4000_skip_mark_11ee120_11ee270": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("tests_or_sets_0x4000", rf"(?:\btest\s+(?:{DWORD_PLUS_8},\s*0x4000|{BYTE_PLUS_9},\s*0x40)\b|\bor\s+(?:{DWORD_PLUS_8},\s*0x4000|{BYTE_PLUS_9},\s*0x40)\b)"),
    ),
    "uobject_4000_set_call_clear_251f970_251f986": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        ("mentions_0x4000", r"(?:0x4000|0x40|0xffffbfff|0xbf)"),
    ),
    "uobject_100_clear_1d637c8_1d63888": (
        ("uobject_plus_0x8_operand", rf"(?:{DWORD_PLUS_8}|{BYTE_PLUS_9})"),
        (
            "clears_0x100_from_uobject_plus_0x8",
            rf"\band\s+(?:{DWORD_PLUS_8},\s*(?:0x0?7fffeff|0xfffffeff)|{BYTE_PLUS_9},\s*0xfe)\b",
        ),
    ),
}

WINDOW_GROUPS = {
    "predicate_windows": (
        "weak_validity_mode_a30_1d56a30_1d56ae0",
        "weak_validity_strict_ae0_1d56ae0_1d56b60",
        "weak_stale_mode_b60_1d56b60_1d56c00",
        "weak_lookup_strict_c00_1d56c00_1d56c70",
        "weak_lookup_allow4000_c70_1d56c70_1d56d00",
    ),
    "caller_mode_windows": (
        "weak_publish_from_uobject_1d56970_1d56a30",
        "weak_lookup_raw_d00_1d56d00_1d56d60",
        "weak_refresh_from_object_d60_1d56d60_1d56ed0",
    ),
    "mutation_windows": (
        "gc_mark_100_8000_1d18a90_1d18c70",
        "gobjects_4000_skip_mark_2982920_2982b60",
        "holder_4000_skip_mark_11ee120_11ee270",
        "uobject_4000_set_call_clear_251f970_251f986",
        "uobject_100_clear_1d637c8_1d63888",
    ),
}

NON_CLAIMS = (
    "does_not_promote_runtime_offsets",
    "does_not_claim_resource_handle_identity",
    "does_not_claim_post_callback_object_lifetime",
    "does_not_assign_public_lifecycle_names",
    "does_not_claim_mutation_or_return_override_safety",
)

REMAINING_BLOCKERS = (
    "static_objdump_windows_only",
    "no_runtime_object_samples",
    "no_second_source_lifecycle_semantics",
    "no_public_resource_handle_contract",
    "no_post_callback_lifetime_contract",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def parse_window(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--window must be NAME=PATH")
    raw_name, raw_path = value.split("=", 1)
    name = raw_name.strip()
    if not WINDOW_NAME_RE.fullmatch(name):
        raise argparse.ArgumentTypeError(f"unsafe window name: {name}")
    if not raw_path:
        raise argparse.ArgumentTypeError("--window path must not be empty")
    return name, Path(raw_path)


def validate_objdump_window_text(text: str) -> list[str]:
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

    if len(addresses) < 2:
        blockers.append("too_few_objdump_instruction_lines")
    if any(next_addr <= current for current, next_addr in zip(addresses, addresses[1:])):
        blockers.append("instruction_addresses_not_strictly_increasing")
    if addresses and addresses[-1] - addresses[0] > MAX_CONNECTED_WINDOW_BYTES:
        blockers.append("instruction_window_too_wide")
    if stray_lines:
        blockers.append("non_objdump_text_lines:" + "|".join(str(line) for line in stray_lines[:5]))
    return blockers


def matched_patterns(window_name: str, text: str) -> tuple[list[str], list[str]]:
    matched: list[str] = []
    missing: list[str] = []
    for label, pattern in WINDOW_CHECKS[window_name]:
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            matched.append(label)
        else:
            missing.append(label)
    return matched, missing


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
    ordered_windows = list(REQUIRED_WINDOWS) + [name for name in OPTIONAL_WINDOWS if name in by_name]
    for name in ordered_windows:
        path = reject_protected_input_path(by_name[name], f"--window {name}")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError as exc:
            raise SystemExit(f"--window {name} does not exist") from exc
        except OSError as exc:
            raise SystemExit(f"--window {name} is unreadable: {exc}") from exc

        structure_blockers = validate_objdump_window_text(text)
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


def semantic_entry(mask: str, *, predicate_windows: list[str], mutation_windows: list[str]) -> dict[str, Any]:
    return {
        "candidate_only": True,
        "public_lifecycle_name_assigned": False,
        "promotion_ready": False,
        "uobject_field": "+0x8",
        "mask": mask,
        "predicate_windows": predicate_windows,
        "mutation_windows": mutation_windows,
        "remaining_blocker": "candidate_requires_independent_lifecycle_validation",
    }


def grouped_windows(observed: list[dict[str, Any]]) -> dict[str, list[str]]:
    observed_names = {entry["name"] for entry in observed}
    groups: dict[str, list[str]] = {}
    for group_name, names in WINDOW_GROUPS.items():
        groups[group_name] = [name for name in names if name in observed_names]
    return groups


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    if not SHA256_RE.fullmatch(args.binary_sha256):
        raise SystemExit("--binary-sha256 must be a lowercase SHA256")

    window_summaries = read_and_validate_windows(args.window or [], binary_sha256=args.binary_sha256)
    window_groups = grouped_windows(window_summaries)
    observed_names = {entry["name"] for entry in window_summaries}
    mutation_windows_0x100 = ["gc_mark_100_8000_1d18a90_1d18c70"]
    if "uobject_100_clear_1d637c8_1d63888" in observed_names:
        mutation_windows_0x100.append("uobject_100_clear_1d637c8_1d63888")
    mutation_windows_0x4000 = [
        "gobjects_4000_skip_mark_2982920_2982b60",
        "holder_4000_skip_mark_11ee120_11ee270",
    ]
    if "uobject_4000_set_call_clear_251f970_251f986" in observed_names:
        mutation_windows_0x4000.append("uobject_4000_set_call_clear_251f970_251f986")

    return {
        "schema": SCHEMA,
        "evidence_kind": EVIDENCE_KIND,
        "status": "candidate_blocked",
        "binary": {
            "sha256": args.binary_sha256,
            "path_redacted": True,
        },
        "builder_contract": {
            "input_kind": "precut_objdump_windows",
            "matrix_kind": "semantic_helper_windows",
            "fail_closed": True,
            "requires_live_server": False,
            "promotion_ready": False,
            "resource_handle_claim": False,
            "public_lifecycle_names_assigned": False,
        },
        "windows_summary": {
            "required": list(REQUIRED_WINDOWS),
            "optional": list(OPTIONAL_WINDOWS),
            "observed": window_summaries,
            "all_required_present": True,
            "all_required_patterns_present": True,
            "groups": window_groups,
        },
        "transition_matrix": {
            "0x100": semantic_entry(
                "0x100",
                predicate_windows=[
                    "weak_validity_mode_a30_1d56a30_1d56ae0",
                    "weak_validity_strict_ae0_1d56ae0_1d56b60",
                    "weak_stale_mode_b60_1d56b60_1d56c00",
                    "weak_lookup_strict_c00_1d56c00_1d56c70",
                    "weak_lookup_allow4000_c70_1d56c70_1d56d00",
                    "weak_refresh_from_object_d60_1d56d60_1d56ed0",
                ],
                mutation_windows=mutation_windows_0x100,
            ),
            "0x4000": semantic_entry(
                "0x4000",
                predicate_windows=[
                    "weak_validity_mode_a30_1d56a30_1d56ae0",
                    "weak_validity_strict_ae0_1d56ae0_1d56b60",
                    "weak_stale_mode_b60_1d56b60_1d56c00",
                    "weak_lookup_strict_c00_1d56c00_1d56c70",
                    "weak_lookup_allow4000_c70_1d56c70_1d56d00",
                ],
                mutation_windows=mutation_windows_0x4000,
            ),
            "0x8000": semantic_entry(
                "0x8000",
                predicate_windows=[],
                mutation_windows=["gc_mark_100_8000_1d18a90_1d18c70"],
            ),
        },
        "non_claims": list(NON_CLAIMS),
        "remaining_blockers": list(REMAINING_BLOCKERS),
        "redaction": {
            "paths": "redacted",
            "raw_snippets": "omitted",
            "public_lifecycle_names": "omitted",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--window", action="append", type=parse_window, default=[])
    parser.add_argument("--output", type=Path, required=True)
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
