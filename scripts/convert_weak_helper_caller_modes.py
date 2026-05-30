#!/usr/bin/env python3
"""Convert bounded weak-helper caller-mode probe output into redacted JSON."""

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


SCHEMA = "obelisk.weak-helper-caller-mode-redacted.v1"
SUPPORTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROVENANCE_SCHEMAS = {
    "obelisk.offline-artifact-provenance.v1",
    "obelisk.static-artifact-provenance.v1",
    "obelisk.weak-helper-bundled-artifact-provenance.v1",
}
PATH_KEY_RE = re.compile(r"(?:^|_)(path|file|source|artifact|binary|core|stdout|stderr|copied_to)$")

HELPER_COUNTS = {
    "0x1d56b60": 4,
    "0x1d56c70": 6,
}
C70_CALLERS = (
    "0x83a340",
    "0x83a720",
    "0x83cde0",
    "0x9f80f0",
    "0x1d299b0",
    "0x1d29a20",
)
B60_CALLERS = (
    "0x2355acc",
    "0x2355b5c",
)
CALLER_WINDOW_STARTS = (*C70_CALLERS, *B60_CALLERS)


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


def collect_path_fields(value: object, *, trail: str = "$", path_context: bool = False) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            child_path_context = key_names_path(key)
            if isinstance(child, str) and child_path_context:
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_path_fields(child, trail=child_trail, path_context=child_path_context))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_trail = f"{trail}[{index}]"
            if isinstance(child, str) and path_context:
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_path_fields(child, trail=child_trail, path_context=path_context))
    return found


def validate_provenance(
    path: Path,
    *,
    label: str,
    binary_sha256: str,
    artifact_sha256: str,
) -> dict[str, Any]:
    provenance_path = reject_protected_input_path(
        path.with_name(path.name + ".provenance.json"),
        f"{label} provenance",
    )
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
        "verified": True,
        "binary_sha256": binary_sha256,
        "artifact_sha256": artifact_sha256,
        "sidecar_sha256": sha256_file(provenance_path),
        "path_redacted": True,
    }


def parse_tool_version(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("tool version must be NAME=VERSION")
    name, version = value.split("=", 1)
    name = name.strip()
    version = version.strip()
    if not name or not version:
        raise argparse.ArgumentTypeError("tool version name and value must not be empty")
    return name, version


def normalize(text: str) -> str:
    return text.lower().replace(" ", "")


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    compact = normalize(text)
    return any(needle.lower() in lowered or needle.lower().replace(" ", "") in compact for needle in needles)


def section(text: str, label: str) -> str:
    marker = f"=== {label} "
    start = text.find(marker)
    if start < 0:
        return ""
    next_start = text.find("\n=== ", start + len(marker))
    if next_start < 0:
        return text[start:]
    return text[start:next_start]


def caller_section(text: str, caller: str) -> str:
    label = caller[2:]
    for prefix in ("caller_1d56c70_", "caller_1d56b60_"):
        found = section(text, f"{prefix}{label}")
        if found:
            return found
    return raw_address_section(text, caller, CALLER_WINDOW_STARTS)


def raw_address_section(text: str, address: str, window_starts: tuple[str, ...]) -> str:
    address_body = address[2:].lower()
    needles = (address.lower(), "0x0" + address_body, "0x00" + address_body)
    lowered = text.lower()
    start = -1
    for needle in needles:
        pos = lowered.find(needle)
        if pos >= 0 and (start < 0 or pos < start):
            start = pos
    if start < 0:
        return ""
    next_start = len(text)
    for other in window_starts:
        if other == address:
            continue
        other_body = other[2:].lower()
        for other_needle in (other.lower(), "0x0" + other_body, "0x00" + other_body):
            pos = lowered.find(other_needle, start + 1)
            if pos >= 0:
                next_start = min(next_start, pos)
    return text[start:next_start]


def helper_raw_section(text: str, helper: str) -> str:
    found = raw_address_section(text, helper, ("0x1d56b60", "0x1d56c70", *CALLER_WINDOW_STARTS))
    if found:
        return found
    return ""


def redacted_address_sha256(binary_sha256: str, address: str) -> str:
    material = f"obelisk.weak-helper-caller-mode:{binary_sha256}:{address.lower()}"
    return hashlib.sha256(material.encode("ascii")).hexdigest()


def c70_caller_rows(binary_sha256: str) -> list[dict[str, Any]]:
    return [
        {
            "helper": "0x1d56c70",
            "helper_address_sha256": redacted_address_sha256(binary_sha256, "0x1d56c70"),
            "caller_address_sha256": redacted_address_sha256(binary_sha256, caller),
            "mode_args": {"sil": {"source": "const", "value": 1}},
            "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
            "source_count": 2,
            "evidence": ["ghidra", "radare2"],
            "policy_observation": {
                "0x100": "null_always",
                "0x4000": "not_rejected_in_observed_sil_1_callers",
            },
            "claim_level": "static_caller_mode_candidate",
            "path_redacted": True,
            "lifecycle_names": "not_promoted",
        }
        for caller in C70_CALLERS
    ]


def parse_direct_call_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in text.splitlines():
        matches = re.findall(r"0x?1d56(?:b60|c70)|1d56(?:b60|c70)", line.lower())
        if not matches:
            continue
        number_match = re.search(r"(?<!0x)\b([0-9]+)\b\s*(?:direct\s*calls?)?$", line.lower())
        if number_match is None:
            number_match = re.search(r"(?:count|observed)\s*[:=]\s*([0-9]+)", line.lower())
        if number_match is None:
            continue
        address = matches[0]
        if not address.startswith("0x"):
            address = "0x" + address
        counts[address] = int(number_match.group(1))
    return counts


def all_c70_callers_have_mode_one(ghidra_text: str, r2_text: str) -> bool:
    for caller in C70_CALLERS:
        ghidra_source = caller_section(ghidra_text, caller)
        r2_source = caller_section(r2_text, caller)
        if not ghidra_source or not r2_source:
            return False
        if not contains_any(ghidra_source, ("helper_get_maybe_pending_candidate", "func_0x01d56c70")):
            return False
        if not contains_any(ghidra_source, (",1)", ", 1)", "param_2=1")):
            return False
        if not contains_any(r2_source, ("0x1d56c70", "0x01d56c70")):
            return False
        if not contains_any(r2_source, ("esi,0x1", "esi = 1", "mov esi, 1", "mov esi,0x1")):
            return False
        if not contains_any(r2_source, ("test rax,rax", "test rax, rax")):
            return False
    return True


def all_b60_callers_are_pairwise_mode(ghidra_text: str, r2_text: str) -> bool:
    for caller in B60_CALLERS:
        ghidra_source = caller_section(ghidra_text, caller)
        r2_source = caller_section(r2_text, caller)
        if not ghidra_source or not r2_source:
            return False
        if not contains_any(ghidra_source, ("helper_is_stale_like_candidate", "func_0x01d56b60")):
            return False
        if not contains_any(r2_source, ("0x1d56b60", "0x01d56b60")):
            return False
        if not contains_any(r2_source, ("xor esi,esi", "xor esi, esi", "mov esi, 0", "mov esi,0")):
            return False
        if not contains_any(r2_source, ("edx,0x1", "edx = 1", "mov edx, 1", "mov edx,0x1")):
            return False
        if not contains_any(r2_source, ("cmp", "xor", "pairwise", "compare")):
            return False
    return True


def required_evidence(ghidra_text: str, r2_text: str, counts_text: str) -> tuple[dict[str, bool], list[str]]:
    stale = section(ghidra_text, "helper_is_stale_like_candidate")
    maybe = section(ghidra_text, "helper_get_maybe_pending_candidate")
    counts = parse_direct_call_counts(counts_text)
    facts = {
        "stale_helper_window_present": bool(stale),
        "maybe_pending_helper_window_present": bool(maybe),
        "direct_call_count_1d56b60_complete": counts.get("0x1d56b60") == HELPER_COUNTS["0x1d56b60"],
        "direct_call_count_1d56c70_complete": counts.get("0x1d56c70") == HELPER_COUNTS["0x1d56c70"],
        "maybe_pending_ghidra_mode_logic": (
            bool(maybe)
            and contains_any(maybe, ("0x100", "0x0100", "test ah,0x1"))
            and contains_any(maybe, ("0x4000", "test dh,0x40"))
            and contains_any(maybe, ("sil", "esi", "param_2"))
        ),
        "stale_ghidra_pairwise_mode_logic": (
            bool(stale)
            and contains_any(stale, ("0x100", "0x0100", "test ah,0x1"))
            and contains_any(stale, ("0x4000", "test ah,0x40"))
            and contains_any(stale, ("sil", "esi", "param_2"))
            and contains_any(stale, ("dl", "edx", "param_3"))
        ),
        "r2_has_maybe_pending_flag_logic": (
            contains_any(helper_raw_section(r2_text, "0x1d56c70"), ("0x1d56c70", "0x01d56c70"))
            and contains_any(helper_raw_section(r2_text, "0x1d56c70"), ("0x100", "0x0100", "test ah, 1", "test ah,0x1"))
            and contains_any(helper_raw_section(r2_text, "0x1d56c70"), ("0x4000", "test dh, 0x40", "test dh,0x40"))
        ),
        "r2_has_stale_flag_logic": (
            contains_any(helper_raw_section(r2_text, "0x1d56b60"), ("0x1d56b60", "0x01d56b60"))
            and contains_any(helper_raw_section(r2_text, "0x1d56b60"), ("0x100", "0x0100", "test ah, 1", "test ah,0x1"))
            and contains_any(helper_raw_section(r2_text, "0x1d56b60"), ("0x4000", "test ah, 0x40", "test ah,0x40", "test ch, 0x40", "test ch,0x40"))
        ),
        "all_c70_callers_set_allow4000_and_use_nonnull": all_c70_callers_have_mode_one(ghidra_text, r2_text),
        "b60_callers_are_pairwise_not_validity": all_b60_callers_are_pairwise_mode(ghidra_text, r2_text),
    }
    blockers = [name for name, present in facts.items() if not present]
    return facts, blockers


def source_entry(
    path: Path,
    *,
    label: str,
    tool: str,
    version: str,
    binary_sha256: str,
) -> dict[str, Any]:
    artifact_sha256 = sha256_file(path)
    return {
        "artifact_sha256": artifact_sha256,
        "tool": tool,
        "version": version,
        "provenance": validate_provenance(
            path,
            label=label,
            binary_sha256=binary_sha256,
            artifact_sha256=artifact_sha256,
        ),
    }


def build_payload(args: argparse.Namespace) -> dict[str, object]:
    ghidra_path = reject_protected_input_path(args.ghidra_stdout, "--ghidra-stdout")
    r2_path = reject_protected_input_path(args.r2_windows, "--r2-windows")
    counts_path = reject_protected_input_path(args.direct_call_counts, "--direct-call-counts")
    if not SHA256_RE.fullmatch(args.binary_sha256):
        raise SystemExit("--binary-sha256 must be a lowercase SHA256")
    if args.binary_sha256 != SUPPORTED_BINARY_SHA256:
        raise SystemExit(f"--binary-sha256 is unsupported for this probe: {args.binary_sha256}")

    ghidra_text = ghidra_path.read_text(encoding="utf-8", errors="replace")
    r2_text = r2_path.read_text(encoding="utf-8", errors="replace")
    counts_text = counts_path.read_text(encoding="utf-8", errors="replace")
    facts, blockers = required_evidence(ghidra_text, r2_text, counts_text)
    if blockers:
        raise SystemExit(f"weak-helper caller-mode probe incomplete: {','.join(blockers)}")

    versions = dict(args.tool_version or [])
    return {
        "schema": SCHEMA,
        "status": "accepted_internal_static_evidence",
        "binary": {
            "sha256": args.binary_sha256,
            "path_redacted": True,
        },
        "sources": {
            "ghidra_stdout": source_entry(
                ghidra_path,
                label="--ghidra-stdout",
                tool="ghidra",
                version=versions.get("ghidra", "unknown"),
                binary_sha256=args.binary_sha256,
            ),
            "r2_windows": source_entry(
                r2_path,
                label="--r2-windows",
                tool="radare2",
                version=versions.get("radare2", "unknown"),
                binary_sha256=args.binary_sha256,
            ),
            "direct_call_counts": source_entry(
                counts_path,
                label="--direct-call-counts",
                tool="objdump-or-radare2",
                version=versions.get("objdump", versions.get("radare2", "unknown")),
                binary_sha256=args.binary_sha256,
            ),
        },
        "direct_call_coverage": {
            "0x1d56b60": {"expected": 4, "observed": 4},
            "0x1d56c70": {"expected": 6, "observed": 6},
        },
        "helpers": {
            "0x1d56c70": {
                "address_sha256": redacted_address_sha256(args.binary_sha256, "0x1d56c70"),
                "return_kind": "uobject_pointer_or_null",
                "mode_args": ["sil"],
                "flag_rules": [
                    {"mask": "0x100", "result": "null_always"},
                    {"mask": "0x4000", "result": "null_when_sil_zero"},
                ],
                "ue_flag_names": "not_promoted",
            },
            "0x1d56b60": {
                "address_sha256": redacted_address_sha256(args.binary_sha256, "0x1d56b60"),
                "return_kind": "boolean_like",
                "mode_args": ["sil", "dl"],
                "observed_direct_caller_mode": {"sil": 0, "dl": 1},
                "caller_mode_note": "observed callers use comparison mode, not flag-validity mode",
                "ue_flag_names": "not_promoted",
            },
        },
        "callers": [
            {
                "helper": "0x1d56c70",
                "caller_window_count": len(C70_CALLERS),
                "mode_args": {"sil": {"source": "const", "value": 1}},
                "return_use": {"register": "rax", "nonzero_path": "kept_or_valid"},
            },
            {
                "helper": "0x1d56b60",
                "caller_window_count": len(B60_CALLERS),
                "mode_args": {
                    "sil": {"source": "const", "value": 0},
                    "dl": {"source": "const", "value": 1},
                },
                "return_use": {"kind": "pairwise_boolean_comparison"},
            },
        ],
        "caller_rows": c70_caller_rows(args.binary_sha256),
        "required_evidence": sorted(name for name, present in facts.items() if present),
        "builder_contract": {
            "promotion_gate_ready": False,
            "consumption_scope": "internal_static_research_only",
            "remaining_blockers": [
                "static_only_evidence",
                "no_named_lifecycle_semantics",
                "no_rejected_runtime_object_samples",
                "public_resourcehandle_policy_missing",
            ],
            "not_promoted": [
                "ResourceHandle",
                "post-callback lookup",
                "mutation",
                "return override",
                "UE lifecycle flag names",
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ghidra-stdout", type=Path, required=True)
    parser.add_argument("--r2-windows", type=Path, required=True)
    parser.add_argument("--direct-call-counts", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--tool-version", action="append", type=parse_tool_version, default=[])
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = reject_protected_output_path(args.output, "--output") if args.output else None
    payload = build_payload(args)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
